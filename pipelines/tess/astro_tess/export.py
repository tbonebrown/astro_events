from __future__ import annotations

from dataclasses import asdict
from datetime import timezone
from pathlib import Path
import json
import shutil

import pandas as pd

from astro_tess.models import CandidateRecord, PipelineRunResult


def export_run(result: PipelineRunResult, export_root: Path) -> Path:
    export_dir = Path(result.export_dir) if result.export_dir else export_root / f"sector_{result.sector}" / result.run_date
    export_dir.mkdir(parents=True, exist_ok=True)

    rows = [asdict(candidate) for candidate in result.candidates]
    frame = pd.DataFrame(rows)
    frame.to_parquet(export_dir / "candidates.parquet", index=False)

    metadata = {
        "run_date": result.run_date,
        "sector": result.sector,
        "candidate_count": len(result.candidates),
        "generated_at": result.generated_at.astimezone(timezone.utc).isoformat(),
    }
    with (export_dir / "run_metadata.json").open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2)

    latest_path = export_root / "latest"
    if latest_path.exists() or latest_path.is_symlink():
        if latest_path.is_dir() and not latest_path.is_symlink():
            shutil.rmtree(latest_path)
        else:
            latest_path.unlink()
    latest_path.symlink_to(export_dir.resolve(), target_is_directory=True)
    return export_dir
