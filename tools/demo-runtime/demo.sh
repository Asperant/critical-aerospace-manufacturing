#!/usr/bin/env bash
# WP-DOC-004 — presenter-facing control for the real Core/Twin/UI demo slice.
#
# This wrapper deliberately uses a separate Compose project and state directory.
# It reuses infra/compose/compose.yaml and the existing demo-runtime adapters;
# it does not create a second application path or a second source of truth.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${HERE}/../.." && pwd)"
STACK="${ROOT}/infra/compose/stack.sh"
COMPOSE_FILE="${ROOT}/infra/compose/compose.yaml"
STATE_DIR="${CAP_DEMO_STATE_DIR:-${HOME}/.local/state/cap-demo}"
PROJECT="${CAP_DEMO_COMPOSE_PROJECT_NAME:-cap-demo}"
ARTIFACT_DIR="${CAP_DEMO_ARTIFACT_DIR:-${ROOT}/evidence/demo-presentation}"
if [[ -x "${ROOT}/.venv/bin/uv" ]]; then
  PATH="${ROOT}/.venv/bin:${PATH}"
  export PATH
fi
# Keep the isolated demo runnable beside the default cap-platform profile.
# Every value remains overrideable for a shared host with an existing collision.
export CAP_PG_PORT="${CAP_DEMO_PG_PORT:-${CAP_PG_PORT:-25442}}"
export CAP_NATS_PORT="${CAP_DEMO_NATS_PORT:-${CAP_NATS_PORT:-24242}}"
export CAP_NATS_MON_PORT="${CAP_DEMO_NATS_MON_PORT:-${CAP_NATS_MON_PORT:-28242}}"
export CAP_VALKEY_PORT="${CAP_DEMO_VALKEY_PORT:-${CAP_VALKEY_PORT:-26389}}"
export CAP_S3_PORT="${CAP_DEMO_S3_PORT:-${CAP_S3_PORT:-28343}}"
export CAP_SEAWEED_MASTER_PORT="${CAP_DEMO_SEAWEED_MASTER_PORT:-${CAP_SEAWEED_MASTER_PORT:-29343}}"
export CAP_KEYCLOAK_PORT="${CAP_DEMO_KEYCLOAK_PORT:-${CAP_KEYCLOAK_PORT:-28090}}"
export CAP_CORE_PORT="${CAP_DEMO_CORE_PORT:-${CAP_CORE_PORT:-28091}}"
export CAP_UI_PORT="${CAP_DEMO_UI_PORT:-${CAP_UI_PORT:-29090}}"
export CAP_AV_NATS_URL="${CAP_AV_NATS_URL:-nats://127.0.0.1:${CAP_NATS_PORT}}"
export CAP_PLATFORM_STATE_DIR="${STATE_DIR}"
export CAP_COMPOSE_PROJECT_NAME="${PROJECT}"
export CAP_DEMO_ARTIFACT_DIR="${ARTIFACT_DIR}"
export CAP_PLAYWRIGHT_IMAGE="${CAP_DEMO_PLAYWRIGHT_IMAGE:-mcr.microsoft.com/playwright:v1.64.0-noble}"

compose() {
  docker compose -p "${PROJECT}" -f "${COMPOSE_FILE}" "$@"
}

die() {
  echo "FAIL: $*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "missing prerequisite: $1"
}

require_docker() {
  require_command docker
  docker info >/dev/null 2>&1 || die "Docker daemon is unavailable or access was denied"
  docker compose version >/dev/null 2>&1 || die "Docker Compose plugin is unavailable"
}

check_line() {
  local label="$1"
  shift
  if "$@" >/dev/null 2>&1; then
    printf 'PASS  %s\n' "${label}"
    return 0
  fi
  printf 'FAIL  %s\n' "${label}"
  PREFLIGHT_FAILED=1
  return 0
}

service_health() {
  local service="$1" id health state exit_code
  id="$(compose ps -aq "${service}" 2>/dev/null || true)"
  [[ -n "${id}" ]] || return 1
  health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "${id}" 2>/dev/null || true)"
  if [[ "${health}" == healthy ]]; then
    return 0
  fi
  # One-shot migration/seed containers are valid when they exited cleanly.
  if [[ "${service}" == demo-migrate || "${service}" == demo-seed ]]; then
    state="$(docker inspect -f '{{.State.Status}}' "${id}" 2>/dev/null || true)"
    exit_code="$(docker inspect -f '{{.State.ExitCode}}' "${id}" 2>/dev/null || true)"
    [[ "${state}" == exited && "${exit_code}" == 0 ]]
    return $?
  fi
  return 1
}

http_ok() {
  curl --fail --silent --show-error --max-time 8 "$1" >/dev/null
}

core_health() {
  http_ok "http://127.0.0.1:${CAP_CORE_PORT:-28081}/healthz"
}

keycloak_realm() {
  http_ok "http://127.0.0.1:${CAP_KEYCLOAK_PORT:-28080}/realms/cap-platform"
}

ui_health() {
  http_ok "http://127.0.0.1:${CAP_UI_PORT:-29080}/"
}

bff_health() {
  compose exec -T demo-bff python -c \
    "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8082/healthz', timeout=5)" \
    >/dev/null 2>&1
}

nats_contract() {
  curl --fail --silent --show-error --max-time 8 \
    "http://127.0.0.1:${CAP_NATS_MON_PORT:-28222}/jsz?streams=true&consumers=true" |
    python3 -c '
import json
import sys

body = json.load(sys.stdin)

def objects(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from objects(child)

items = list(objects(body))
streams = [item for item in items if item.get("name") == "CAP_EVENTS"]
consumers = [item for item in items if item.get("name") == "twin-primary"]
assert streams
assert consumers and any(
    item.get("stream_name") == "CAP_EVENTS" for item in consumers
)
'
}

preflight() {
  require_command curl
  require_command python3
  PREFLIGHT_FAILED=0
  echo "Demo preflight (${PROJECT})"
  check_line "Docker daemon" docker info
  check_line "Compose definition" compose --profile core config --quiet
  check_line "PostgreSQL health" service_health postgres
  check_line "NATS/JetStream health" service_health nats
  check_line "NATS stream/consumer" nats_contract
  check_line "Keycloak health" service_health keycloak
  check_line "Keycloak demo realm" keycloak_realm
  check_line "Migrations" service_health demo-migrate
  check_line "Seed scenario" service_health demo-seed
  check_line "Core health" core_health
  check_line "Outbox relay" service_health demo-relay
  check_line "Twin consumer" service_health demo-twin
  check_line "BFF health" bff_health
  check_line "UI availability" ui_health
  if [[ ${PREFLIGHT_FAILED} -ne 0 ]]; then
    return 1
  fi
  echo "PASS  demo runtime is ready"
}

preflight_capture() {
  mkdir -p "${ARTIFACT_DIR}"
  preflight 2>&1 | tee "${ARTIFACT_DIR}/preflight.txt"
}

start() {
  require_docker
  mkdir -p "${STATE_DIR}" "${ARTIFACT_DIR}"
  CAP_PLATFORM_STATE_DIR="${STATE_DIR}" CAP_COMPOSE_PROJECT_NAME="${PROJECT}" \
    "${STACK}" up core
  preflight_capture
}

reset() {
  require_docker
  mkdir -p "${STATE_DIR}" "${ARTIFACT_DIR}"
  # stack.sh reset is safe here because the project name and state directory
  # are demo-specific; it cannot target the default cap-platform project.
  CAP_PLATFORM_STATE_DIR="${STATE_DIR}" CAP_COMPOSE_PROJECT_NAME="${PROJECT}" \
    "${STACK}" reset
  rm -f "${ARTIFACT_DIR}/scenario-context.json" \
    "${ARTIFACT_DIR}/browser-result.json" \
    "${ARTIFACT_DIR}/latest.json" \
    "${ARTIFACT_DIR}/verification.txt" \
    "${ARTIFACT_DIR}/verify-output.txt" \
    "${ARTIFACT_DIR}/preflight.txt" \
    "${ARTIFACT_DIR}/scenario-output.txt" \
    "${ARTIFACT_DIR}/browser-output.txt" \
    "${ARTIFACT_DIR}/browser-initial-output.txt" \
    "${ARTIFACT_DIR}/browser-initial-result.json" \
    "${ARTIFACT_DIR}/browser-initial.png" \
    "${ARTIFACT_DIR}/browser-anomaly.png" \
    "${ARTIFACT_DIR}/browser-final.png"
  echo "PASS: isolated demo state reset (${PROJECT}; ${STATE_DIR})"
}

browser_test() {
  if command -v node >/dev/null 2>&1 && \
    [[ -x "${ROOT}/services/command-center-web/node_modules/.bin/playwright" ]]; then
    ( cd "${ROOT}/services/command-center-web" && \
      CAP_DEMO_ARTIFACT_DIR="${ARTIFACT_DIR}" \
      CAP_DEMO_BROWSER_STAGE="${CAP_DEMO_BROWSER_STAGE:-final}" \
      ./node_modules/.bin/playwright test e2e/demo-runtime.spec.ts \
        --config=playwright.demo.config.ts )
    return
  fi

  require_docker
  echo "INFO: host Node/Playwright unavailable; using ${CAP_PLAYWRIGHT_IMAGE}"
  docker run --rm --network host --user "$(id -u):$(id -g)" \
    -e CAP_PLATFORM_STATE_DIR=/state \
    -e CAP_DEMO_ARTIFACT_DIR=/artifacts \
    -e CAP_DEMO_BROWSER_STAGE="${CAP_DEMO_BROWSER_STAGE:-final}" \
    -e CAP_UI_PORT="${CAP_UI_PORT}" \
    -v "${ROOT}/services/command-center-web:/source:ro" \
    -v "${STATE_DIR}:/state:ro" \
    -v "${ARTIFACT_DIR}:/artifacts" \
    --entrypoint bash "${CAP_PLAYWRIGHT_IMAGE}" -lc '
      set -euo pipefail
      work=/tmp/cap-demo-ui
      rm -rf "$work"
      mkdir -p "$work/e2e"
      cp /source/package.json /source/package-lock.json "$work/"
      cp /source/playwright.demo.config.ts "$work/"
      cp /source/e2e/demo-runtime.spec.ts "$work/e2e/"
      cd "$work"
      npm ci --ignore-scripts --no-audit --no-fund
      npx playwright test e2e/demo-runtime.spec.ts --config=playwright.demo.config.ts
    '
}

scenario() {
  preflight_capture
  run_flow
  if [[ "${CAP_DEMO_SKIP_BROWSER:-0}" != 1 ]]; then
    browser_test 2>&1 | tee "${ARTIFACT_DIR}/browser-output.txt"
  else
    echo "WARN: browser step skipped by CAP_DEMO_SKIP_BROWSER=1; verify will fail closed"
  fi
  verify
}

run_flow() {
  mkdir -p "${ARTIFACT_DIR}"
  require_command uv
  PYTHONPATH="${ROOT}/tools/demo-runtime/src${PYTHONPATH:+:${PYTHONPATH}}" \
    CAP_DEMO_SOURCE_SHA="$(git -C "${ROOT}" rev-parse HEAD)" \
    uv run --project "${ROOT}/ci" --locked python \
      "${HERE}/scripts/demo_flow.py" --output "${ARTIFACT_DIR}/scenario-context.json" \
      2>&1 | tee "${ARTIFACT_DIR}/scenario-output.txt"
}

showcase() {
  preflight_capture
  CAP_DEMO_BROWSER_STAGE=initial browser_test 2>&1 | tee "${ARTIFACT_DIR}/browser-initial-output.txt"
  run_flow
  CAP_DEMO_BROWSER_STAGE=final browser_test 2>&1 | tee "${ARTIFACT_DIR}/browser-output.txt"
  verify
}

verify() {
  require_command uv
  mkdir -p "${ARTIFACT_DIR}"
  PYTHONPATH="${ROOT}/tools/demo-runtime/src${PYTHONPATH:+:${PYTHONPATH}}" \
    CAP_DEMO_SOURCE_SHA="$(git -C "${ROOT}" rev-parse HEAD)" \
    uv run --project "${ROOT}/ci" --locked python \
      "${HERE}/scripts/demo_verify.py" --artifact-dir "${ARTIFACT_DIR}" \
      2>&1 | tee "${ARTIFACT_DIR}/verify-output.txt"
}

status() {
  require_docker
  CAP_PLATFORM_STATE_DIR="${STATE_DIR}" CAP_COMPOSE_PROJECT_NAME="${PROJECT}" \
    "${STACK}" status
}

stop() {
  require_docker
  CAP_PLATFORM_STATE_DIR="${STATE_DIR}" CAP_COMPOSE_PROJECT_NAME="${PROJECT}" \
    "${STACK}" down
  echo "PASS: demo runtime stopped; volumes and credentials retained"
}

usage() {
  cat >&2 <<EOF
Usage: $0 {start|preflight|reset|scenario|showcase|verify|status|stop}

State: ${STATE_DIR}
Compose project: ${PROJECT}
Artifacts: ${ARTIFACT_DIR}
EOF
  exit 2
}

case "${1:-}" in
  start) start ;;
  preflight) preflight_capture ;;
  reset) reset ;;
  scenario) scenario ;;
  showcase) showcase ;;
  verify) verify ;;
  status) status ;;
  stop) stop ;;
  *) usage ;;
esac
