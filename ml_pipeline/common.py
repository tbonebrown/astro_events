from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

import pandas as pd


def require_package(module_name: str, package_name: str | None = None):
    try:
        module = __import__(module_name, fromlist=["*"])
    except ImportError as exc:
        package_label = package_name or module_name
        raise SystemExit(
            f"Missing optional dependency '{package_label}'. Install the ML extras before running this pipeline."
        ) from exc
    return module


def load_manifest(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        frame = pd.read_csv(path)
    elif suffix in {".parquet", ".pq"}:
        frame = pd.read_parquet(path)
    elif suffix == ".json":
        frame = pd.DataFrame(json.loads(path.read_text()))
    else:
        raise SystemExit(f"Unsupported manifest format for {path}. Use CSV, JSON, or Parquet.")
    required = {"image_id", "image_path"}
    missing = required - set(frame.columns)
    if missing:
        raise SystemExit(f"Manifest is missing required columns: {', '.join(sorted(missing))}")
    return frame


@dataclass(slots=True)
class ArtifactPaths:
    output_dir: Path

    @property
    def checkpoint_path(self) -> Path:
        return self.output_dir / "encoder.pt"

    @property
    def config_path(self) -> Path:
        return self.output_dir / "encoder_config.json"

    @property
    def embeddings_path(self) -> Path:
        return self.output_dir / "embeddings.parquet"

    @property
    def map_path(self) -> Path:
        return self.output_dir / "galaxy_map.parquet"

    def ensure(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
