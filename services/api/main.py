from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from astro_api.config import AppSettings
from astro_api.database import Base, engine, get_session
from astro_api.repositories import (
    get_candidate,
    get_latest_report,
    get_latest_run,
    get_latest_transient_report,
    get_transient_candidate,
    list_candidates,
    list_transient_candidates,
)
from astro_api.services.galaxy_map import GalaxyMapService
from astro_api.services.celestial_events import CelestialEventsService
from astro_api.services.llm import LocalInferenceClient
from astro_api.schemas import (
    CandidateDetailResponse,
    CandidateSummaryResponse,
    CelestialEventResponse,
    CelestialExplanationResponse,
    GalaxyClusterSummaryResponse,
    GalaxyDetailResponse,
    GalaxyExplanationResponse,
    GalaxyListResponse,
    HealthResponse,
    NightlyReportResponse,
    NightlyRunResponse,
    PersonalizedEventsResponse,
    TransientCandidateDetailResponse,
    TransientCandidateSummaryResponse,
    TransientReportResponse,
)


def create_app(
    settings: AppSettings | None = None,
    session_provider: Callable[[], Iterator[Session]] | None = None,
    initialize_database: Callable[[], None] | None = None,
) -> FastAPI:
    settings = settings or AppSettings()
    session_provider = session_provider or get_session
    initialize_database = initialize_database or (lambda: Base.metadata.create_all(bind=engine))
    galaxy_map_service = GalaxyMapService(settings=settings)
    llm_client = LocalInferenceClient(settings=settings)
    celestial_events_service = CelestialEventsService(settings=settings, llm_client=llm_client)

    artifacts_dir = settings.data_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        initialize_database()
        yield

    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.mount("/artifacts", StaticFiles(directory=artifacts_dir), name="artifacts")

    assets_dir = settings.static_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/api/health", response_model=HealthResponse)
    def health(session: Session = Depends(session_provider)) -> HealthResponse:
        latest_run = get_latest_run(session)
        return HealthResponse(
            status="ok",
            environment=settings.app_env,
            latest_run=NightlyRunResponse.model_validate(latest_run) if latest_run else None,
        )

    @app.get("/api/runs/latest", response_model=NightlyRunResponse)
    def latest_run(session: Session = Depends(session_provider)) -> NightlyRunResponse:
        run = get_latest_run(session)
        if run is None:
            raise HTTPException(status_code=404, detail="No runs available.")
        return NightlyRunResponse.model_validate(run)

    @app.get("/api/candidates", response_model=list[CandidateSummaryResponse])
    def candidate_list(
        sector: int | None = None,
        limit: int = 25,
        offset: int = 0,
        min_score: float | None = None,
        session: Session = Depends(session_provider),
    ) -> list[CandidateSummaryResponse]:
        rows = list_candidates(session, sector=sector, limit=limit, offset=offset, min_score=min_score)
        return [CandidateSummaryResponse.model_validate(row) for row in rows]

    @app.get("/api/candidates/{candidate_id}", response_model=CandidateDetailResponse)
    def candidate_detail(
        candidate_id: str,
        session: Session = Depends(session_provider),
    ) -> CandidateDetailResponse:
        candidate = get_candidate(session, candidate_id)
        if candidate is None:
            raise HTTPException(status_code=404, detail="Candidate not found.")
        return CandidateDetailResponse.model_validate(candidate)

    @app.get("/api/reports/latest", response_model=NightlyReportResponse)
    def latest_report(session: Session = Depends(session_provider)) -> NightlyReportResponse:
        report = get_latest_report(session)
        if report is None:
            raise HTTPException(status_code=404, detail="No reports available.")
        return NightlyReportResponse.model_validate(report)

    @app.get("/api/transients", response_model=list[TransientCandidateSummaryResponse])
    def transient_list(
        source_name: str | None = None,
        limit: int = 25,
        offset: int = 0,
        min_score: float | None = None,
        novel_only: bool = False,
        session: Session = Depends(session_provider),
    ) -> list[TransientCandidateSummaryResponse]:
        rows = list_transient_candidates(
            session,
            source_name=source_name,
            limit=limit,
            offset=offset,
            min_score=min_score,
            novel_only=novel_only,
        )
        return [TransientCandidateSummaryResponse.model_validate(row) for row in rows]

    @app.get("/api/transients/{candidate_id}", response_model=TransientCandidateDetailResponse)
    def transient_detail(
        candidate_id: str,
        session: Session = Depends(session_provider),
    ) -> TransientCandidateDetailResponse:
        candidate = get_transient_candidate(session, candidate_id)
        if candidate is None:
            raise HTTPException(status_code=404, detail="Transient candidate not found.")
        return TransientCandidateDetailResponse.model_validate(candidate)

    @app.get("/api/transients/reports/latest", response_model=TransientReportResponse)
    def latest_transient_report(session: Session = Depends(session_provider)) -> TransientReportResponse:
        report = get_latest_transient_report(session)
        if report is None:
            raise HTTPException(status_code=404, detail="No transient reports available.")
        return TransientReportResponse.model_validate(report)

    @app.get("/api/galaxies", response_model=GalaxyListResponse)
    def galaxy_list(
        limit: int = 5_000,
        offset: int = 0,
        min_x: float | None = None,
        max_x: float | None = None,
        min_y: float | None = None,
        max_y: float | None = None,
        cluster_id: int | None = None,
    ) -> GalaxyListResponse:
        payload = galaxy_map_service.list_points(
            limit=max(1, min(limit, 20_000)),
            offset=max(0, offset),
            min_x=min_x,
            max_x=max_x,
            min_y=min_y,
            max_y=max_y,
            cluster_id=cluster_id,
        )
        return GalaxyListResponse.model_validate(payload)

    @app.get("/api/galaxy/{image_id}", response_model=GalaxyDetailResponse)
    def galaxy_detail(image_id: str) -> GalaxyDetailResponse:
        detail = galaxy_map_service.get_detail(image_id)
        if detail is None:
            raise HTTPException(status_code=404, detail="Galaxy not found.")
        return GalaxyDetailResponse.model_validate(detail)

    @app.get("/api/clusters", response_model=list[GalaxyClusterSummaryResponse])
    def galaxy_clusters() -> list[GalaxyClusterSummaryResponse]:
        return [GalaxyClusterSummaryResponse.model_validate(cluster) for cluster in galaxy_map_service.list_clusters()]

    @app.get("/api/explain/{image_id}", response_model=GalaxyExplanationResponse)
    def explain_galaxy(image_id: str) -> GalaxyExplanationResponse:
        explanation = galaxy_map_service.explain_galaxy(image_id, llm_client)
        if explanation is None:
            raise HTTPException(status_code=404, detail="Galaxy not found.")
        return GalaxyExplanationResponse.model_validate(explanation)

    @app.get("/api/events", response_model=list[CelestialEventResponse])
    @app.get("/events", response_model=list[CelestialEventResponse], include_in_schema=False)
    def event_list(
        lat: float | None = None,
        lon: float | None = None,
        timezone: str | None = None,
        start_days: int = 0,
        end_days: int = 30,
        event_type: str | None = None,
        min_visibility: float | None = None,
        session: Session = Depends(session_provider),
    ) -> list[CelestialEventResponse]:
        now = datetime.now(UTC)
        events = celestial_events_service.list_feed(
            session,
            user_lat=lat,
            user_lon=lon,
            timezone_name=timezone,
            start_time=now + timedelta(days=max(0, start_days)),
            end_time=now + timedelta(days=max(1, min(end_days, 30))),
            event_type=event_type,
            min_visibility=min_visibility,
        )
        return [CelestialEventResponse.model_validate(event) for event in events]

    @app.get("/api/events/personalized", response_model=PersonalizedEventsResponse)
    @app.get("/events/personalized", response_model=PersonalizedEventsResponse, include_in_schema=False)
    def personalized_events(
        lat: float,
        lon: float,
        timezone: str,
        days: int = 14,
        event_type: str | None = None,
        min_visibility: float | None = None,
        session: Session = Depends(session_provider),
    ) -> PersonalizedEventsResponse:
        payload = celestial_events_service.personalized_feed(
            session,
            user_lat=lat,
            user_lon=lon,
            timezone_name=timezone,
            days=days,
            event_type=event_type,
            min_visibility=min_visibility,
        )
        return PersonalizedEventsResponse.model_validate(payload)

    @app.get("/api/events/{event_id}", response_model=CelestialEventResponse)
    @app.get("/events/{event_id}", response_model=CelestialEventResponse, include_in_schema=False)
    def event_detail(
        event_id: str,
        lat: float | None = None,
        lon: float | None = None,
        timezone: str | None = None,
        session: Session = Depends(session_provider),
    ) -> CelestialEventResponse:
        detail = celestial_events_service.event_detail(
            session,
            event_id,
            user_lat=lat,
            user_lon=lon,
            timezone_name=timezone,
        )
        if detail is None:
            raise HTTPException(status_code=404, detail="Event not found.")
        return CelestialEventResponse.model_validate(detail)

    @app.get("/api/events/{event_id}/explain", response_model=CelestialExplanationResponse)
    @app.get("/events/{event_id}/explain", response_model=CelestialExplanationResponse, include_in_schema=False)
    def explain_event(
        event_id: str,
        lat: float,
        lon: float,
        timezone: str,
        session: Session = Depends(session_provider),
    ) -> CelestialExplanationResponse:
        detail = celestial_events_service.event_detail(
            session,
            event_id,
            user_lat=lat,
            user_lon=lon,
            timezone_name=timezone,
        )
        if detail is None:
            raise HTTPException(status_code=404, detail="Event not found.")
        explanation = celestial_events_service.get_or_generate_copy(
            session,
            event_id=event_id,
            user_lat=lat,
            user_lon=lon,
            timezone_name=timezone,
        )
        return CelestialExplanationResponse.model_validate(
            {
                "event_id": event_id,
                "summary": explanation["summary"],
                "why_interesting": explanation["why_interesting"],
                "explanation": explanation["explanation"],
                "source": explanation["source"],
            }
        )

    @app.get("/{full_path:path}")
    def frontend(full_path: str) -> FileResponse:
        index_path = settings.static_dir / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        raise HTTPException(status_code=404, detail="Frontend build not found.")

    return app


app = create_app()
