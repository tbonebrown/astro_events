from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(slots=True)
class PipelineSettings:
    export_root: Path = Path(os.getenv("EXPORTS_DIR", "./exports"))
    data_dir: Path = Path(os.getenv("DATA_DIR", "./var/data"))
    sync_target: str = os.getenv("SYNC_TARGET", "")
    sync_mode: str = os.getenv("SYNC_MODE", "local")
    gaia_alerts_url: str = os.getenv(
        "GAIA_ALERTS_URL",
        "https://gsaweb.ast.cam.ac.uk/alerts/alertsindex",
    )
    source_name: str = os.getenv("GAIA_SOURCE_NAME", "gaia")
    default_limit: int = int(os.getenv("GAIA_ALERTS_LIMIT", "100"))
    report_top_k: int = int(os.getenv("TRANSIENT_REPORT_TOP_K", "12"))
