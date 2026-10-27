#!/usr/bin/env bash
# WP-PLAT-001 — start/stop the platform runtime from infra/compose/compose.yaml.
# The same script runs in GitHub Actions (t1-integration) and on a developer or
# shared host with Docker, so both use identical images and settings.
#
# Usage: infra/compose/stack.sh up [PROFILE...]|down|reset|env|status|logs|config [PROFILE]|smoke
#   up      create credentials if needed, start the profiles (default: infra) and
#           wait until every service is healthy; prints startup-to-healthy seconds
#   down    stop all services, keep data and credentials
#   reset   stop, delete all data volumes and credentials (fresh start next time)
#   env     print connection settings and credentials as KEY=VALUE lines
#   status  docker compose ps
#   logs    recent logs of all services
#   config  render the definition for a profile (validation, no containers)
#   smoke   REAL checks of the running infra layer (mfgctl smoke platform-infra)
#
# Credentials are generated per machine and kept outside the repository in
# ${CAP_PLATFORM_STATE_DIR:-~/.local/state/cap-platform} with mode 0600:
# credentials.env for this script, postgres.env, keycloak.env and s3.json read by Compose.
# They are never committed and printed only by `env`.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE=(docker compose -f "${HERE}/compose.yaml")
STATE_DIR="${CAP_PLATFORM_STATE_DIR:-${HOME}/.local/state/cap-platform}"
export CAP_PLATFORM_STATE_DIR="${STATE_DIR}"
CREDENTIALS="${STATE_DIR}/credentials.env"
CAP_PG_PORT="${CAP_PG_PORT:-25432}"
CAP_NATS_PORT="${CAP_NATS_PORT:-24222}"
CAP_NATS_MON_PORT="${CAP_NATS_MON_PORT:-28222}"
CAP_VALKEY_PORT="${CAP_VALKEY_PORT:-26379}"
CAP_S3_PORT="${CAP_S3_PORT:-28333}"
CAP_SEAWEED_MASTER_PORT="${CAP_SEAWEED_MASTER_PORT:-29333}"
CAP_KEYCLOAK_PORT="${CAP_KEYCLOAK_PORT:-28080}"
CAP_TEMPORAL_PORT="${CAP_TEMPORAL_PORT:-27233}"
CAP_TEMPORAL_HTTP_PORT="${CAP_TEMPORAL_HTTP_PORT:-27243}"
CAP_TEMPORAL_NAMESPACE="${CAP_TEMPORAL_NAMESPACE:-cap}"
CAP_QDRANT_PORT="${CAP_QDRANT_PORT:-26333}"
CAP_QDRANT_GRPC_PORT="${CAP_QDRANT_GRPC_PORT:-26334}"
CAP_MLFLOW_PORT="${CAP_MLFLOW_PORT:-25000}"
export CAP_PG_PORT CAP_NATS_PORT CAP_NATS_MON_PORT CAP_VALKEY_PORT CAP_S3_PORT \
  CAP_SEAWEED_MASTER_PORT CAP_KEYCLOAK_PORT CAP_TEMPORAL_PORT CAP_TEMPORAL_HTTP_PORT \
  CAP_TEMPORAL_NAMESPACE CAP_QDRANT_PORT CAP_QDRANT_GRPC_PORT CAP_MLFLOW_PORT
PROFILES_ALL=(infra core vision ai planning platform full e2e)

secret() { od -An -N16 -tx1 /dev/urandom | tr -d ' \n'; }

SECRET_VARS=(CAP_POSTGRES_PASSWORD CAP_KEYCLOAK_ADMIN_PASSWORD CAP_S3_ADMIN_SECRET CAP_S3_WRITER_SECRET CAP_S3_READER_SECRET
  CAP_S3_MLFLOW_SECRET CAP_QDRANT_API_KEY CAP_KEYCLOAK_SMOKE_CLIENT_SECRET)
# WP-OBJ-001: least-privilege S3 identities. Access keys are names, not secrets.
S3_ADMIN_KEY=cap-artifacts-admin
S3_WRITER_KEY=cap-artifacts-writer
S3_READER_KEY=cap-artifacts-reader
# WP-PLAT-003: MLflow reads, lists and writes only its own artifact bucket.
S3_MLFLOW_KEY=cap-mlflow
MLFLOW_BUCKET=cap-mlflow-artifacts
ARTIFACT_BUCKETS=(cap-artifacts-rc-b cap-artifacts-rc-c cap-artifacts-rc-d)

s3_actions() {  # s3_actions Read List Write -> "Read:b1","List:b1",... for every artifact bucket
  local out="" b a
  for b in "${ARTIFACT_BUCKETS[@]}"; do for a in "$@"; do out+="${out:+,}\"${a}:${b}\""; done; done
  printf '%s' "$out"
}

load_credentials() {
  if [[ -z "${CAP_POSTGRES_PASSWORD:-}" && -f "${CREDENTIALS}" ]]; then
    # shellcheck disable=SC1090
    source "${CREDENTIALS}"
  fi
  local var changed=0
  for var in "${SECRET_VARS[@]}"; do
    if [[ -z "${!var:-}" ]]; then
      printf -v "$var" '%s' "$(secret)"
      changed=1
    fi
  done
  if [[ $changed -eq 1 ]]; then
    mkdir -p "${STATE_DIR}"
    chmod 700 "${STATE_DIR}"
    ( umask 077
      for var in "${SECRET_VARS[@]}"; do printf '%s=%s\n' "$var" "${!var}"; done > "${CREDENTIALS}" )
    echo "credentials created or completed in ${CREDENTIALS}" >&2
  fi
  export "${SECRET_VARS[@]}"
  # Service files read by Compose (also by `mfgctl up`), regenerated each time.
  local s3_before=""
  [[ -f "${STATE_DIR}/s3.json" ]] && s3_before="$(cat "${STATE_DIR}/s3.json")"
  ( umask 077
    printf 'POSTGRES_PASSWORD=%s\n' "${CAP_POSTGRES_PASSWORD}" > "${STATE_DIR}/postgres.env"
    # WP-PLAT-003: the platform realm's smoke-client secret, resolved by Keycloak on import.
    printf 'KC_BOOTSTRAP_ADMIN_PASSWORD=%s\nCAP_KEYCLOAK_SMOKE_CLIENT_SECRET=%s\n' \
      "${CAP_KEYCLOAK_ADMIN_PASSWORD}" "${CAP_KEYCLOAK_SMOKE_CLIENT_SECRET}" > "${STATE_DIR}/keycloak.env"
    # WP-PLAT-003: Temporal server (POSTGRES_PWD) and its schema job (SQL_PASSWORD).
    printf 'POSTGRES_PWD=%s\nSQL_PASSWORD=%s\n' "${CAP_POSTGRES_PASSWORD}" "${CAP_POSTGRES_PASSWORD}" > "${STATE_DIR}/temporal.env"
    printf 'QDRANT__SERVICE__API_KEY=%s\n' "${CAP_QDRANT_API_KEY}" > "${STATE_DIR}/qdrant.env"
    # MLflow: only the one-shot init job sees the S3 admin identity (bucket creation);
    # the server gets the backend URI and its bucket-scoped identity.
    printf 'CAP_POSTGRES_PASSWORD=%s\nCAP_S3_ADMIN_ACCESS_KEY=%s\nCAP_S3_ADMIN_SECRET_KEY=%s\n' \
      "${CAP_POSTGRES_PASSWORD}" "${S3_ADMIN_KEY}" "${CAP_S3_ADMIN_SECRET}" > "${STATE_DIR}/mlflow-init.env"
    printf 'MLFLOW_BACKEND_STORE_URI=postgresql://cap:%s@postgres:5432/mlflow\nAWS_ACCESS_KEY_ID=%s\nAWS_SECRET_ACCESS_KEY=%s\n' \
      "${CAP_POSTGRES_PASSWORD}" "${S3_MLFLOW_KEY}" "${CAP_S3_MLFLOW_SECRET}" > "${STATE_DIR}/mlflow.env"
    # SeaweedFS S3 identities: with any identity defined, anonymous access is denied.
    # admin creates buckets; writer reads, lists and writes artifacts; reader only reads
    # (it signs the short-lived read capabilities). Mounted read-only into the container.
    printf '{"identities": [%s, %s, %s, %s]}\n' \
      "{\"name\": \"${S3_ADMIN_KEY}\", \"credentials\": [{\"accessKey\": \"${S3_ADMIN_KEY}\", \"secretKey\": \"${CAP_S3_ADMIN_SECRET}\"}], \"actions\": [\"Admin\", \"Read\", \"List\", \"Write\"]}" \
      "{\"name\": \"${S3_WRITER_KEY}\", \"credentials\": [{\"accessKey\": \"${S3_WRITER_KEY}\", \"secretKey\": \"${CAP_S3_WRITER_SECRET}\"}], \"actions\": [$(s3_actions Read List Write)]}" \
      "{\"name\": \"${S3_READER_KEY}\", \"credentials\": [{\"accessKey\": \"${S3_READER_KEY}\", \"secretKey\": \"${CAP_S3_READER_SECRET}\"}], \"actions\": [$(s3_actions Read)]}" \
      "{\"name\": \"${S3_MLFLOW_KEY}\", \"credentials\": [{\"accessKey\": \"${S3_MLFLOW_KEY}\", \"secretKey\": \"${CAP_S3_MLFLOW_SECRET}\"}], \"actions\": [\"Read:${MLFLOW_BUCKET}\", \"List:${MLFLOW_BUCKET}\", \"Write:${MLFLOW_BUCKET}\"]}" \
      > "${STATE_DIR}/s3.json" )
  # SeaweedFS reads s3.json only when it starts: an identity added here (WP-PLAT-003:
  # cap-mlflow) would stay unknown to a running gateway until it restarts.
  S3_IDENTITIES_CHANGED=0
  [[ -n "${s3_before}" && "${s3_before}" != "$(cat "${STATE_DIR}/s3.json")" ]] && S3_IDENTITIES_CHANGED=1
  return 0
}

mask_in_ci() {
  if [[ "${GITHUB_ACTIONS:-}" == "true" ]]; then
    local var
    for var in "${SECRET_VARS[@]}"; do echo "::add-mask::${!var}"; done
  fi
}

check_profiles() {
  local p known
  for p in "$@"; do
    known=0
    for k in "${PROFILES_ALL[@]}"; do [[ "$p" == "$k" ]] && known=1; done
    if [[ $known -eq 0 ]]; then
      echo "unknown profile '${p}'; known: ${PROFILES_ALL[*]}" >&2
      exit 2
    fi
  done
}

profile_args() {
  local p
  for p in "$@"; do printf -- '--profile\n%s\n' "$p"; done
}

case "${1:-}" in
  up)
    shift
    profiles=("$@")
    [[ $# -eq 0 ]] && profiles=(infra)
    check_profiles "${profiles[@]}"
    load_credentials
    mask_in_ci
    mapfile -t args < <(profile_args "${profiles[@]}")
    "${COMPOSE[@]}" "${args[@]}" pull --quiet --ignore-buildable
    "${COMPOSE[@]}" "${args[@]}" build --quiet
    if [[ ${S3_IDENTITIES_CHANGED} -eq 1 && -n "$("${COMPOSE[@]}" "${args[@]}" ps -q seaweedfs)" ]]; then
      echo "S3 identities changed: restarting seaweedfs" >&2
      "${COMPOSE[@]}" "${args[@]}" restart seaweedfs
    fi
    started=$(date +%s)
    if ! "${COMPOSE[@]}" "${args[@]}" up --detach --wait --wait-timeout 660; then
      "${COMPOSE[@]}" "${args[@]}" ps >&2 || true
      "${COMPOSE[@]}" "${args[@]}" logs --tail 60 >&2 || true
      echo "ERROR: profile(s) ${profiles[*]} did not become healthy" >&2
      exit 1
    fi
    echo "profiles ${profiles[*]} healthy in $(( $(date +%s) - started )) s (images pre-pulled)"
    "${COMPOSE[@]}" "${args[@]}" images
    ;;
  down)
    load_credentials
    mapfile -t args < <(profile_args "${PROFILES_ALL[@]}")
    "${COMPOSE[@]}" "${args[@]}" down
    ;;
  reset)
    load_credentials
    mapfile -t args < <(profile_args "${PROFILES_ALL[@]}")
    "${COMPOSE[@]}" "${args[@]}" down --volumes
    rm -f "${CREDENTIALS}"
    echo "platform data volumes and credentials removed"
    ;;
  env)
    load_credentials
    echo "CAP_PG_DSN=postgresql://cap:${CAP_POSTGRES_PASSWORD}@127.0.0.1:${CAP_PG_PORT}/cap"
    echo "CAP_NATS_URL=nats://127.0.0.1:${CAP_NATS_PORT}"
    echo "CAP_NATS_MONITOR_URL=http://127.0.0.1:${CAP_NATS_MON_PORT}"
    echo "CAP_VALKEY_URL=redis://127.0.0.1:${CAP_VALKEY_PORT}/0"
    echo "CAP_S3_ENDPOINT=http://127.0.0.1:${CAP_S3_PORT}"
    echo "CAP_S3_ACCESS_KEY=${S3_WRITER_KEY}"
    echo "CAP_S3_SECRET_KEY=${CAP_S3_WRITER_SECRET}"
    echo "CAP_S3_ADMIN_ACCESS_KEY=${S3_ADMIN_KEY}"
    echo "CAP_S3_ADMIN_SECRET_KEY=${CAP_S3_ADMIN_SECRET}"
    echo "CAP_S3_READER_ACCESS_KEY=${S3_READER_KEY}"
    echo "CAP_S3_READER_SECRET_KEY=${CAP_S3_READER_SECRET}"
    echo "CAP_SEAWEED_MASTER_URL=http://127.0.0.1:${CAP_SEAWEED_MASTER_PORT}"
    echo "CAP_KEYCLOAK_URL=http://127.0.0.1:${CAP_KEYCLOAK_PORT}"
    echo "CAP_KEYCLOAK_ADMIN_USER=cap-admin"
    echo "CAP_KEYCLOAK_ADMIN_PASSWORD=${CAP_KEYCLOAK_ADMIN_PASSWORD}"
    echo "CAP_KEYCLOAK_REALM=cap-platform"
    echo "CAP_KEYCLOAK_SMOKE_CLIENT_ID=cap-platform-smoke"
    echo "CAP_KEYCLOAK_SMOKE_CLIENT_SECRET=${CAP_KEYCLOAK_SMOKE_CLIENT_SECRET}"
    echo "CAP_TEMPORAL_ADDRESS=127.0.0.1:${CAP_TEMPORAL_PORT}"
    echo "CAP_TEMPORAL_HTTP_URL=http://127.0.0.1:${CAP_TEMPORAL_HTTP_PORT}"
    echo "CAP_TEMPORAL_NAMESPACE=${CAP_TEMPORAL_NAMESPACE}"
    echo "CAP_QDRANT_URL=http://127.0.0.1:${CAP_QDRANT_PORT}"
    echo "CAP_QDRANT_API_KEY=${CAP_QDRANT_API_KEY}"
    echo "CAP_MLFLOW_URL=http://127.0.0.1:${CAP_MLFLOW_PORT}"
    ;;
  status)
    load_credentials
    mapfile -t args < <(profile_args "${PROFILES_ALL[@]}")
    "${COMPOSE[@]}" "${args[@]}" ps
    ;;
  logs)
    load_credentials
    mapfile -t args < <(profile_args "${PROFILES_ALL[@]}")
    "${COMPOSE[@]}" "${args[@]}" logs --tail 200
    ;;
  config)
    profile="${2:-infra}"
    check_profiles "${profile}"
    "${COMPOSE[@]}" --profile "${profile}" config --quiet
    echo "profile ${profile} renders"
    ;;
  smoke)
    load_credentials
    eval "$("${HERE}/stack.sh" env | sed 's/^/export /')"
    cd "${HERE}/../.."
    PYTHONPATH="${PYTHONPATH:-ci:ci/scripts}" uv run --project ci --locked \
      python -m pytest infra/compose/tests -m integration -q -p pytest_quarantine
    ;;
  *)
    echo "usage: $0 up [PROFILE...]|down|reset|env|status|logs|config [PROFILE]|smoke" >&2
    exit 2
    ;;
esac
