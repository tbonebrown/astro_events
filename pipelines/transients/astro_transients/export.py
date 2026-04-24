from __future__ import annotations

from dataclasses import asdict
from datetime import timezone
from pathlib import Path
import json

import pandas as pd

from astro_transients.models import PipelineRunResult


def export_run(result: PipelineRunResult, export_root: Path) -> Path:
    timestamp = result.generated_at.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    export_dir = export_root / "transients" / timestamp
    export_dir.mkdir(parents=True, exist_ok=True)

    frame = pd.DataFrame([asdict(candidate) for candidate in result.candidates])
    frame.to_parquet(export_dir / "candidates.parquet", index=False)

    metadata = {
        "run_date": result.run_date,
        "source_name": result.source_name,
        "candidate_count": len(result.candidates),
        "generated_at": result.generated_at.astimezone(timezone.utc).isoformat(),
    }
    with (export_dir / "run_metadata.json").open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2)

    latest_path = export_root / "transients" / "latest"
    if latest_path.exists() or latest_path.is_symlink():
        latest_path.unlink()
    latest_path.symlink_to(export_dir.resolve(), target_is_directory=True)
    return export_dir
