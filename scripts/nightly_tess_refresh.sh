#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
source .venv/bin/activate

export_root="${EXPORTS_DIR:-./exports}"
sector="${DEFAULT_SECTOR:-58}"
limit="${NIGHTLY_LIMIT:-50}"
target_file="${TESS_TARGET_FILE:-${TESS_TARGET_OUTPUT:-}}"
use_synthetic="${USE_SYNTHETIC_DATA:-}"

cmd=(
  python3 -m astro_tess.cli
  --sector "${sector}"
  --limit "${limit}"
  --export-root "${export_root}"
)

if [[ -z "${use_synthetic}" && -n "${target_file}" && -f "${target_file}" ]]; then
  if python3 -c "import lightkurve" >/dev/null 2>&1; then
    cmd+=(--tic-target-file "${target_file}")
  else
    echo "lightkurve is unavailable; generating synthetic TESS samples for this refresh."
    use_synthetic=1
  fi
else
  use_synthetic=1
fi

if [[ -n "${use_synthetic}" ]]; then
  cmd+=(--synthetic)
fi

"${cmd[@]}"
if [[ -n "${NIGHTLY_INGEST_INFERENCE_URL:-}" ]]; then
  LOCAL_INFERENCE_URL="${NIGHTLY_INGEST_INFERENCE_URL}" python3 -m astro_api.cli.ingest --export-dir "${export_root}/latest"
else
  python3 -m astro_api.cli.ingest --export-dir "${export_root}/latest"
fi
