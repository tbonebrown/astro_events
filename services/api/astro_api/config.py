from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(slots=True)
class AppSettings:
    app_name: str = os.getenv("APP_NAME", "Astro Event Intelligence")
    app_env: str = os.getenv("APP_ENV", "development")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./var/astro_events.db")
    data_dir: Path = Path(os.getenv("DATA_DIR", "./var/data"))
    exports_dir: Path = Path(os.getenv("EXPORTS_DIR", "./exports"))
    static_dir: Path = Path(os.getenv("STATIC_DIR", "./services/web/dist"))
    galaxy_map_artifact: Path = Path(
        os.getenv("GALAXY_MAP_ARTIFACT", "./var/data/galaxy_map/embeddings.parquet")
    )
    galaxy_map_demo_size: int = int(os.getenv("GALAXY_MAP_DEMO_SIZE", "12500"))
    local_inference_url: str = os.getenv("LOCAL_INFERENCE_URL", "http://127.0.0.1:11434/api/generate")
    local_inference_model: str = os.getenv("LOCAL_INFERENCE_MODEL", "astro-explainer")
    local_inference_provider: str = os.getenv("LOCAL_INFERENCE_PROVIDER", "ollama")
    default_sector: int = int(os.getenv("DEFAULT_SECTOR", "58"))
