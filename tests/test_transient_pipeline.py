from __future__ import annotations

from astro_transients.data_sources import _parse_embedded_alerts
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


def test_transient_pipeline_replaces_existing_latest_directory(tmp_path):
    latest_dir = tmp_path / "exports" / "transients" / "latest"
    latest_dir.mkdir(parents=True)
    (latest_dir / "stale.txt").write_text("stale", encoding="utf-8")

    settings = PipelineSettings(export_root=tmp_path / "exports", data_dir=tmp_path / "var")
    run_nightly(limit=3, settings=settings, synthetic=True)

    assert latest_dir.is_symlink()
    assert (latest_dir / "candidates.parquet").exists()
    assert not (latest_dir / "stale.txt").exists()


def test_transient_pipeline_deduplicates_by_external_alert_id(tmp_path):
    settings = PipelineSettings(export_root=tmp_path / "exports", data_dir=tmp_path / "var")
    result = run_nightly(limit=5, settings=settings, source=DuplicateSource())

    assert len(result.candidates) == 1
    assert result.candidates[0].external_alert_id == "Gaia24dup"


def test_transient_source_parses_embedded_gaia_alerts_payload():
    html = """
    <script>
      var alerts = [{
        "name": "Gaia25aeh",
        "tnsid": null,
        "obstime": "2025-01-15 00:59:00",
        "ra": "312.55124",
        "dec": "28.89383",
        "alertMag": "15.86",
        "historicMag": "18.31",
        "historicStdDev": "0.26",
        "classification": "unknown",
        "published": "2025-01-16 17:56:09",
        "comment": "Outburst in candidate eclipsing CV",
        "per_alert": {"link": "/alerts/alert/Gaia25aeh/", "name": "Gaia25aeh"},
        "rvs": false
      }];
    </script>
    """

    alerts = _parse_embedded_alerts(html, "http://gsaweb.ast.cam.ac.uk/alerts/alertsindex")

    assert len(alerts) == 1
    assert alerts[0].external_alert_id == "Gaia25aeh"
    assert alerts[0].magnitude == 15.86
    assert alerts[0].alert_url == "http://gsaweb.ast.cam.ac.uk/alerts/alert/Gaia25aeh/"
