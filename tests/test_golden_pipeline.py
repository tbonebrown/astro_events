from __future__ import annotations

from pathlib import Path

from astro_tess.config import PipelineSettings
from astro_tess.pipeline import run_nightly


def test_synthetic_pipeline_produces_ranked_export(tmp_path: Path) -> None:
    settings = PipelineSettings(export_root=tmp_path / "exports", sync_target="", sync_mode="local")

    result = run_nightly(sector=58, limit=12, settings=settings, synthetic=True)

    assert len(result.candidates) == 12
    assert result.candidates[0].anomaly_score >= result.candidates[-1].anomaly_score
    assert result.candidates[0].rank == 1
    assert (Path(result.export_dir) / "candidates.parquet").exists()
    assert (Path(result.export_dir) / "run_metadata.json").exists()
    assert (Path(result.export_dir) / "plots").exists()

