from __future__ import annotations

from astro_transients.config import PipelineSettings
from astro_transients.models import GaiaAlert
from astro_transients.pipeline import run_nightly


class DuplicateSource:
    def fetch_alerts(self, limit: int) -> list[GaiaAlert]:
        return [
            GaiaAlert(
                name="Gaia24dup",
                external_alert_id="Gaia24dup",
                observed_at="2026-04-22T02:00:00+00:00",
                published_at="2026-04-22T10:00:00+00:00",
                ra=12.4,
                dec=13.2,
                magnitude=17.4,
                historic_magnitude=19.3,
                historic_scatter=0.2,
                classification="Unknown",
                comment="older record",
            ),
            GaiaAlert(
                name="Gaia24dup",
                external_alert_id="Gaia24dup",
                observed_at="2026-04-22T03:00:00+00:00",
                published_at="2026-04-22T11:00:00+00:00",
                ra=12.4,
                dec=13.2,
                magnitude=16.8,
                historic_magnitude=19.3,
                historic_scatter=0.2,
                classification="Unknown",
                comment="newer record",
            ),
        ]


def test_transient_pipeline_exports_ranked_candidates(tmp_path):
    settings = PipelineSettings(export_root=tmp_path / "exports", data_dir=tmp_path / "var")
    result = run_nightly(limit=10, settings=settings, synthetic=True)

    assert len(result.candidates) == 10
    assert result.candidates[0].rank == 1
    assert result.candidates[0].score >= result.candidates[-1].score
    assert (tmp_path / "exports" / "transients" / "latest").is_symlink()
    assert (tmp_path / "exports" / "transients" / "latest" / "candidates.parquet").exists()


def test_transient_pipeline_deduplicates_by_external_alert_id(tmp_path):
    settings = PipelineSettings(export_root=tmp_path / "exports", data_dir=tmp_path / "var")
    result = run_nightly(limit=5, settings=settings, source=DuplicateSource())

    assert len(result.candidates) == 1
    assert result.candidates[0].external_alert_id == "Gaia24dup"
