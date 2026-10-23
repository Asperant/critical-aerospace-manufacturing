#!/usr/bin/env bash
# WP-OBS-001 — start/stop the observability runtime (Collector + OpenObserve).
# The same script runs in GitHub Actions (t1-integration) and on a developer or
# shared host with Docker, so both use identical images and settings.
#
# Usage: infra/observability/stack.sh up|down|reset|env|status|logs|dashboards
#   up      create credentials if needed, start both services, wait for health
#   down    stop the services, keep stored data and credentials
#   reset   stop, delete stored data and credentials (fresh start next time)
#   env     print O2_URL, OTLP endpoints and credentials as KEY=VALUE lines
#   status  docker compose ps
#   logs    recent logs of both services
#   dashboards  import the versioned dashboards (idempotent; never overwrites)
#
# Credentials are generated per machine and kept outside the repository in
# ${CAP_OBS_STATE_DIR:-$XDG_STATE_HOME/cap-observability} with mode 0600; they are
# never committed and never printed except by `env` (Item 47 §36).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE=(docker compose -f "${HERE}/compose.yaml")
STATE_DIR="${CAP_OBS_STATE_DIR:-${XDG_STATE_HOME:-${HOME}/.local/state}/cap-observability}"
CREDENTIALS="${STATE_DIR}/credentials.env"
O2_HTTP_PORT="${O2_HTTP_PORT:-55080}"
OTLP_GRPC_PORT="${OTLP_GRPC_PORT:-54317}"
OTLP_HTTP_PORT="${OTLP_HTTP_PORT:-54318}"
OTEL_HEALTH_PORT="${OTEL_HEALTH_PORT:-53133}"
CAP_OBS_UID="${CAP_OBS_UID:-$(id -u)}"
CAP_OBS_GID="${CAP_OBS_GID:-$(id -g)}"
export O2_HTTP_PORT OTLP_GRPC_PORT OTLP_HTTP_PORT OTEL_HEALTH_PORT CAP_OBS_UID CAP_OBS_GID

load_credentials() {
  if [[ -z "${O2_ROOT_PASSWORD:-}" && -f "${CREDENTIALS}" ]]; then
    # shellcheck disable=SC1090
    source "${CREDENTIALS}"
  fi
  if [[ -z "${O2_ROOT_PASSWORD:-}" ]]; then
    mkdir -p "${STATE_DIR}"
    chmod 700 "${STATE_DIR}"
    # OpenObserve policy: 8-128 characters with lower, upper, digit and special.
    O2_ROOT_EMAIL="${O2_ROOT_EMAIL:-root@cap.local}"
    O2_ROOT_PASSWORD="Cap-$(od -An -N12 -tx1 /dev/urandom | tr -d ' \n')-O2!"
    umask 077
    printf 'O2_ROOT_EMAIL=%s\nO2_ROOT_PASSWORD=%s\n' \
      "${O2_ROOT_EMAIL}" "${O2_ROOT_PASSWORD}" > "${CREDENTIALS}"
    echo "credentials created in ${CREDENTIALS}" >&2
  fi
  O2_ROOT_EMAIL="${O2_ROOT_EMAIL:-root@cap.local}"
  O2_BASIC_AUTH="$(printf '%s:%s' "${O2_ROOT_EMAIL}" "${O2_ROOT_PASSWORD}" | base64 | tr -d '\n')"
  export O2_ROOT_EMAIL O2_ROOT_PASSWORD O2_BASIC_AUTH
}

mask_in_ci() {
  # GitHub Actions hides these values in every later log line of the job.
  if [[ "${GITHUB_ACTIONS:-}" == "true" ]]; then
    echo "::add-mask::${O2_ROOT_PASSWORD}"
    echo "::add-mask::${O2_BASIC_AUTH}"
  fi
}

wait_for() {
  local name="$1" url="$2" tries=90
  until curl -fsS -o /dev/null "${url}" 2>/dev/null; do
    tries=$((tries - 1))
    if [[ $tries -le 0 ]]; then
      echo "ERROR: ${name} did not become healthy at ${url}" >&2
      "${COMPOSE[@]}" logs --tail 80 "${name}" >&2 || true
      exit 1
    fi
    sleep 1
  done
  echo "${name} healthy"
}

case "${1:-}" in
  up)
    load_credentials
    mask_in_ci
    "${COMPOSE[@]}" up --detach
    wait_for openobserve "http://127.0.0.1:${O2_HTTP_PORT}/healthz"
    wait_for otel-collector "http://127.0.0.1:${OTEL_HEALTH_PORT}/"
    "${COMPOSE[@]}" images --format json 2>/dev/null \
      | python3 -c 'import json,sys; [print(i.get("Repository","")+":"+i.get("Tag",""), i.get("ID","")) for i in json.load(sys.stdin)]' \
      || "${COMPOSE[@]}" images
    ;;
  down)
    load_credentials
    "${COMPOSE[@]}" down
    ;;
  reset)
    load_credentials
    "${COMPOSE[@]}" down --volumes
    rm -f "${CREDENTIALS}"
    echo "observability data and credentials removed"
    ;;
  env)
    load_credentials
    echo "O2_URL=http://127.0.0.1:${O2_HTTP_PORT}"
    echo "OTLP_HTTP_URL=http://127.0.0.1:${OTLP_HTTP_PORT}"
    echo "OTLP_GRPC_URL=http://127.0.0.1:${OTLP_GRPC_PORT}"
    echo "O2_ROOT_EMAIL=${O2_ROOT_EMAIL}"
    echo "O2_ROOT_PASSWORD=${O2_ROOT_PASSWORD}"
    ;;
  status)
    load_credentials
    "${COMPOSE[@]}" ps
    ;;
  logs)
    load_credentials
    "${COMPOSE[@]}" logs --tail 200
    ;;
  dashboards)
    load_credentials
    O2_URL="http://127.0.0.1:${O2_HTTP_PORT}" python3 "${HERE}/dashboards.py" import
    ;;
  *)
    echo "usage: $0 up|down|reset|env|status|logs|dashboards" >&2
    exit 2
    ;;
esac
