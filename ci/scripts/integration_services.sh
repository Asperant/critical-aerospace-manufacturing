#!/usr/bin/env bash
# WP-CICD-001 — real PostgreSQL + NATS JetStream for the integration tier.
# The same script runs in GitHub Actions and on a developer machine with Docker,
# so local and CI integration use identical images and settings (Item 41 §3).
# Usage: ci/scripts/integration_services.sh up|down|env
# Credentials below belong to a throw-away container bound to localhost; they
# are not secrets of any shared environment.
set -euo pipefail

POSTGRES_IMAGE="${CI_POSTGRES_IMAGE:-postgres:16.4-alpine}"
NATS_IMAGE="${CI_NATS_IMAGE:-nats:2.10.22-alpine}"
PG_PORT="${CI_PG_PORT:-55432}"
NATS_PORT="${CI_NATS_PORT:-54222}"
NATS_MON_PORT="${CI_NATS_MON_PORT:-58222}"
PREFIX="${CI_SERVICE_PREFIX:-cap-ci}"

print_env() {
  echo "CI_PG_DSN=postgresql://ci:ci@127.0.0.1:${PG_PORT}/ci"
  echo "CI_NATS_URL=nats://127.0.0.1:${NATS_PORT}"
}

wait_for() {
  local name="$1" check="$2" tries=60
  until eval "$check" >/dev/null 2>&1; do
    tries=$((tries - 1))
    if [[ $tries -le 0 ]]; then
      echo "ERROR: ${name} did not become ready" >&2
      docker logs "${PREFIX}-${name}" >&2 || true
      exit 1
    fi
    sleep 1
  done
  echo "${name} ready"
}

case "${1:-}" in
  up)
    docker run -d --rm --name "${PREFIX}-postgres" \
      -e POSTGRES_USER=ci -e POSTGRES_PASSWORD=ci -e POSTGRES_DB=ci \
      -p "127.0.0.1:${PG_PORT}:5432" "${POSTGRES_IMAGE}" >/dev/null
    docker run -d --rm --name "${PREFIX}-nats" \
      -p "127.0.0.1:${NATS_PORT}:4222" -p "127.0.0.1:${NATS_MON_PORT}:8222" \
      "${NATS_IMAGE}" -js -m 8222 >/dev/null
    wait_for postgres "docker exec ${PREFIX}-postgres pg_isready -U ci -d ci"
    wait_for nats "curl -fsS 'http://127.0.0.1:${NATS_MON_PORT}/healthz?js-enabled-only=true'"
    docker image inspect --format '{{index .RepoDigests 0}}' \
      "${POSTGRES_IMAGE}" "${NATS_IMAGE}"
    print_env
    ;;
  down)
    docker rm -f "${PREFIX}-postgres" "${PREFIX}-nats" >/dev/null 2>&1 || true
    echo "integration services removed"
    ;;
  env)
    print_env
    ;;
  *)
    echo "usage: $0 up|down|env" >&2
    exit 2
    ;;
esac
