#!/usr/bin/env bash
# CPU-only Vision smoke path (WP-VIS-008), run by `mfgctl smoke vision`.
# Needs only the locked CI toolchain: no GPU, no containers, no platform services.
set -euo pipefail
cd "$(dirname "$0")/../.."
export PYTHONPATH="services/vision-service/src:packages/artifacts/src:packages/contracts/src${PYTHONPATH:+:$PYTHONPATH}"
exec uv run --project ci --locked python -m vision_service.smoke "$@"
