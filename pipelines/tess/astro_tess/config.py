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
    default_sector: int = int(os.getenv("DEFAULT_SECTOR", "58"))
    default_points: int = 256
    default_limit: int = 50
    plot_dpi: int = 150
    report_top_k: int = 10

