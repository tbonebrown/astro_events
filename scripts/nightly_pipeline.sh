#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
source .venv/bin/activate

cmd=(
  python3 -m astro_tess.cli
  --sector "${DEFAULT_SECTOR:-58}"
  --limit "${NIGHTLY_LIMIT:-50}"
)

if [[ -n "${TESS_TARGET_FILE:-}" ]]; then
  cmd+=(--tic-target-file "${TESS_TARGET_FILE}")
fi

if [[ -n "${USE_SYNTHETIC_DATA:-}" ]]; then
  cmd+=(--synthetic)
fi

"${cmd[@]}"
