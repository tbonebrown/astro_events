from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


def _env_flag(name: str, default: str = "true") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _env_hosts(name: str, default: str) -> tuple[str, ...]:
    return tuple(host.strip().lower() for host in os.getenv(name, default).split(",") if host.strip())


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
    public_hosts: tuple[str, ...] = _env_hosts("PUBLIC_HOSTS", "ohnita.com,www.ohnita.com")
    force_https: bool = _env_flag("FORCE_HTTPS", "true")
    hsts_enabled: bool = _env_flag("HSTS_ENABLED", "true")
    hsts_max_age: int = int(os.getenv("HSTS_MAX_AGE", "31536000"))
