#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
source .venv/bin/activate

export_root="${EXPORTS_DIR:-./exports}"
limit="${GAIA_ALERTS_LIMIT:-100}"

cmd=(
  python3 -m astro_transients.cli
  --limit "${limit}"
  --export-root "${export_root}"
)

if [[ -n "${USE_SYNTHETIC_DATA:-${USE_SYNTHETIC_TRANSIENTS:-}}" ]]; then
  cmd+=(--synthetic)
fi

"${cmd[@]}"
if [[ -n "${NIGHTLY_INGEST_INFERENCE_URL:-}" ]]; then
  LOCAL_INFERENCE_URL="${NIGHTLY_INGEST_INFERENCE_URL}" python3 -m astro_api.cli.ingest_transients --export-dir "${export_root}/transients/latest"
else
  python3 -m astro_api.cli.ingest_transients --export-dir "${export_root}/transients/latest"
fi
