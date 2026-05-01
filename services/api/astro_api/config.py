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
        os.getenv("GALAXY_MAP_ARTIFACT", "./var/data/galaxy_map/galaxies.parquet")
    )
    galaxy_map_dir: Path = Path(os.getenv("GALAXY_MAP_DIR", "./var/data/galaxy_map"))
    galaxy_map_demo_size: int = int(os.getenv("GALAXY_MAP_DEMO_SIZE", "12500"))
    exoplanet_cache_dir: Path = Path(os.getenv("EXOPLANET_CACHE_DIR", "./var/data/exoplanet"))
    local_inference_url: str = os.getenv("LOCAL_INFERENCE_URL", "http://127.0.0.1:11434/api/generate")
    local_inference_model: str = os.getenv("LOCAL_INFERENCE_MODEL", "astro-explainer")
    local_inference_provider: str = os.getenv("LOCAL_INFERENCE_PROVIDER", "ollama")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "http://127.0.0.1:8080/v1")
    llm_model: str = os.getenv("LLM_MODEL", os.getenv("LOCAL_INFERENCE_MODEL", "astro-explainer"))
    use_gpu_classifier: bool = _env_flag("USE_GPU_CLASSIFIER", "true")
    gpu_device: str = os.getenv("GPU_DEVICE", "cuda:0")
    rocm_device: str = os.getenv("ROCM_DEVICE", "hip:0")
    max_workers: int = int(os.getenv("MAX_WORKERS", "4"))
    nasa_archive_timeout: float = float(os.getenv("NASA_ARCHIVE_TIMEOUT", "8.0"))
    enable_batch_scan: bool = _env_flag("ENABLE_BATCH_SCAN", "true")
    default_sector: int = int(os.getenv("DEFAULT_SECTOR", "58"))
    public_hosts: tuple[str, ...] = _env_hosts("PUBLIC_HOSTS", "ohnita.com,www.ohnita.com")
    force_https: bool = _env_flag("FORCE_HTTPS", "true")
    hsts_enabled: bool = _env_flag("HSTS_ENABLED", "true")
    hsts_max_age: int = int(os.getenv("HSTS_MAX_AGE", "31536000"))
