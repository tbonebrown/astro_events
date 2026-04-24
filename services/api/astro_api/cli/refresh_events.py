from __future__ import annotations

from sqlalchemy.orm import Session

from astro_api.config import AppSettings
from astro_api.database import Base, SessionLocal, engine
from astro_api.services.celestial_events import CelestialEventsService
from astro_api.services.llm import LocalInferenceClient


def main() -> int:
    settings = AppSettings()
    Base.metadata.create_all(bind=engine)
    service = CelestialEventsService(settings=settings, llm_client=LocalInferenceClient(settings=settings))
    with SessionLocal() as session:
        assert isinstance(session, Session)
        service.ensure_catalog(session, horizon_days=45)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
