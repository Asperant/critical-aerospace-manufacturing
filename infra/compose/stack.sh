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
# credentials.env for this script, postgres.env and keycloak.env read by Compose.
# They are never committed and printed only by `env`.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE=(docker compose -f "${HERE}/compose.yaml")
STATE_DIR="${CAP_PLATFORM_STATE_DIR:-${HOME}/.local/state/cap-platform}"
export CAP_PLATFORM_STATE_DIR="${STATE_DIR}"
CREDENTIALS="${STATE_DIR}/credentials.env"
CAP_PG_PORT="${CAP_PG_PORT:-56432}"
CAP_NATS_PORT="${CAP_NATS_PORT:-56222}"
CAP_NATS_MON_PORT="${CAP_NATS_MON_PORT:-56822}"
CAP_VALKEY_PORT="${CAP_VALKEY_PORT:-56379}"
CAP_S3_PORT="${CAP_S3_PORT:-56333}"
CAP_SEAWEED_MASTER_PORT="${CAP_SEAWEED_MASTER_PORT:-56933}"
CAP_KEYCLOAK_PORT="${CAP_KEYCLOAK_PORT:-56080}"
export CAP_PG_PORT CAP_NATS_PORT CAP_NATS_MON_PORT CAP_VALKEY_PORT CAP_S3_PORT \
  CAP_SEAWEED_MASTER_PORT CAP_KEYCLOAK_PORT
PROFILES_ALL=(infra core vision ai planning platform full e2e)

secret() { od -An -N16 -tx1 /dev/urandom | tr -d ' \n'; }

load_credentials() {
  if [[ -z "${CAP_POSTGRES_PASSWORD:-}" && -f "${CREDENTIALS}" ]]; then
    # shellcheck disable=SC1090
    source "${CREDENTIALS}"
  fi
  if [[ -z "${CAP_POSTGRES_PASSWORD:-}" || -z "${CAP_KEYCLOAK_ADMIN_PASSWORD:-}" ]]; then
    mkdir -p "${STATE_DIR}"
    chmod 700 "${STATE_DIR}"
    CAP_POSTGRES_PASSWORD="${CAP_POSTGRES_PASSWORD:-$(secret)}"
    CAP_KEYCLOAK_ADMIN_PASSWORD="${CAP_KEYCLOAK_ADMIN_PASSWORD:-$(secret)}"
    umask 077
    printf 'CAP_POSTGRES_PASSWORD=%s\nCAP_KEYCLOAK_ADMIN_PASSWORD=%s\n' \
      "${CAP_POSTGRES_PASSWORD}" "${CAP_KEYCLOAK_ADMIN_PASSWORD}" > "${CREDENTIALS}"
    echo "credentials created in ${CREDENTIALS}" >&2
  fi
  export CAP_POSTGRES_PASSWORD CAP_KEYCLOAK_ADMIN_PASSWORD
  # Service env files read by Compose (also by `mfgctl up`), regenerated each time.
  ( umask 077
    printf 'POSTGRES_PASSWORD=%s\n' "${CAP_POSTGRES_PASSWORD}" > "${STATE_DIR}/postgres.env"
    printf 'KC_BOOTSTRAP_ADMIN_PASSWORD=%s\n' "${CAP_KEYCLOAK_ADMIN_PASSWORD}" > "${STATE_DIR}/keycloak.env" )
}

mask_in_ci() {
  if [[ "${GITHUB_ACTIONS:-}" == "true" ]]; then
    echo "::add-mask::${CAP_POSTGRES_PASSWORD}"
    echo "::add-mask::${CAP_KEYCLOAK_ADMIN_PASSWORD}"
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
    "${COMPOSE[@]}" "${args[@]}" pull --quiet
    started=$(date +%s)
    if ! "${COMPOSE[@]}" "${args[@]}" up --detach --wait --wait-timeout 300; then
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
    echo "CAP_SEAWEED_MASTER_URL=http://127.0.0.1:${CAP_SEAWEED_MASTER_PORT}"
    echo "CAP_KEYCLOAK_URL=http://127.0.0.1:${CAP_KEYCLOAK_PORT}"
    echo "CAP_KEYCLOAK_ADMIN_USER=cap-admin"
    echo "CAP_KEYCLOAK_ADMIN_PASSWORD=${CAP_KEYCLOAK_ADMIN_PASSWORD}"
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
