from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, selectinload

from astro_api.models import (
    Candidate,
    CachedCelestialExplanation,
    CelestialEvent,
    EventVisibility,
    NightlyReport,
    NightlyRun,
    TransientCandidate,
    TransientReport,
    TransientRun,
)


def get_latest_run(session: Session) -> NightlyRun | None:
    return session.scalar(
        select(NightlyRun).order_by(desc(NightlyRun.generated_at)).limit(1)
    )


def list_candidates(
    session: Session,
    sector: int | None = None,
    limit: int = 25,
    offset: int = 0,
    min_score: float | None = None,
) -> list[Candidate]:
    statement = select(Candidate).order_by(Candidate.rank.asc()).limit(limit).offset(offset)
    if sector is not None:
        latest_sector_run = session.scalar(
            select(NightlyRun)
            .where(NightlyRun.sector == sector)
            .order_by(desc(NightlyRun.generated_at))
            .limit(1)
        )
        if latest_sector_run is not None:
            statement = statement.where(Candidate.run_id == latest_sector_run.id)
        else:
            return []
    else:
        latest_run = get_latest_run(session)
        if latest_run is not None:
            statement = statement.where(Candidate.run_id == latest_run.id)
        else:
            return []
    if min_score is not None:
        statement = statement.where(Candidate.anomaly_score >= min_score)
    return list(session.scalars(statement))


def get_candidate(session: Session, candidate_id: str) -> Candidate | None:
    return session.scalar(
        select(Candidate)
        .options(selectinload(Candidate.artifacts))
        .where(Candidate.candidate_id == candidate_id)
    )


def get_latest_report(session: Session) -> NightlyReport | None:
    return session.scalar(
        select(NightlyReport)
        .options(selectinload(NightlyReport.run))
        .order_by(desc(NightlyReport.generated_at))
        .limit(1)
    )


def get_latest_transient_run(session: Session, source_name: str | None = None) -> TransientRun | None:
    statement = select(TransientRun).order_by(desc(TransientRun.generated_at)).limit(1)
    if source_name is not None:
        statement = statement.where(TransientRun.source_name == source_name)
    return session.scalar(statement)


def list_transient_candidates(
    session: Session,
    source_name: str | None = None,
    limit: int = 25,
    offset: int = 0,
    min_score: float | None = None,
    novel_only: bool = False,
) -> list[TransientCandidate]:
    statement = (
        select(TransientCandidate)
        .order_by(TransientCandidate.rank.asc())
        .limit(limit)
        .offset(offset)
    )
    latest_run = get_latest_transient_run(session, source_name=source_name)
    if latest_run is None:
        return []
    statement = statement.where(TransientCandidate.run_id == latest_run.id)
    if min_score is not None:
        statement = statement.where(TransientCandidate.score >= min_score)
    if novel_only:
        statement = statement.where(TransientCandidate.novelty_flag.is_(True))
    return list(session.scalars(statement))


def get_transient_candidate(session: Session, candidate_id: str) -> TransientCandidate | None:
    return session.scalar(
        select(TransientCandidate)
        .options(selectinload(TransientCandidate.artifacts))
        .where(TransientCandidate.candidate_id == candidate_id)
    )


def get_latest_transient_report(session: Session) -> TransientReport | None:
    return session.scalar(
        select(TransientReport)
        .options(selectinload(TransientReport.run))
        .order_by(desc(TransientReport.generated_at))
        .limit(1)
    )


def count_upcoming_celestial_events(session: Session, now: datetime | None = None) -> int:
    current = now or datetime.now(UTC)
    return int(
        session.scalar(
            select(func.count(CelestialEvent.event_id)).where(CelestialEvent.end_time >= current)
        )
        or 0
    )


def upsert_celestial_event(session: Session, payload: dict) -> CelestialEvent:
    event = session.get(CelestialEvent, payload["event_id"])
    if event is None:
        event = CelestialEvent(event_id=payload["event_id"])
        session.add(event)
    for key, value in payload.items():
        setattr(event, key, value)
    return event


def list_celestial_events(
    session: Session,
    *,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    event_type: str | None = None,
) -> list[CelestialEvent]:
    statement = select(CelestialEvent).order_by(CelestialEvent.peak_time.asc())
    if start_time is not None:
        statement = statement.where(CelestialEvent.end_time >= start_time)
    if end_time is not None:
        statement = statement.where(CelestialEvent.start_time <= end_time)
    if event_type is not None:
        statement = statement.where(CelestialEvent.event_type == event_type)
    return list(session.scalars(statement))


def get_celestial_event(session: Session, event_id: str) -> CelestialEvent | None:
    return session.get(CelestialEvent, event_id)


def get_event_visibility_cache(session: Session, event_id: str, region_key: str) -> EventVisibility | None:
    return session.scalar(
        select(EventVisibility)
        .where(EventVisibility.event_id == event_id, EventVisibility.region_key == region_key)
        .limit(1)
    )


def upsert_event_visibility(session: Session, payload: dict) -> EventVisibility:
    row = get_event_visibility_cache(session, payload["event_id"], payload["region_key"])
    if row is None:
        row = EventVisibility(event_id=payload["event_id"], region_key=payload["region_key"])
        session.add(row)
    for key, value in payload.items():
        setattr(row, key, value)
    return row


def get_cached_celestial_copy(
    session: Session,
    *,
    event_id: str,
    latitude: float,
    longitude: float,
    timezone_name: str,
) -> CachedCelestialExplanation | None:
    return session.scalar(
        select(CachedCelestialExplanation)
        .where(
            CachedCelestialExplanation.event_id == event_id,
            CachedCelestialExplanation.latitude == latitude,
            CachedCelestialExplanation.longitude == longitude,
            CachedCelestialExplanation.timezone_name == timezone_name,
        )
        .limit(1)
    )


def save_cached_celestial_copy(session: Session, payload: dict) -> CachedCelestialExplanation:
    row = get_cached_celestial_copy(
        session,
        event_id=payload["event_id"],
        latitude=payload["latitude"],
        longitude=payload["longitude"],
        timezone_name=payload["timezone_name"],
    )
    if row is None:
        row = CachedCelestialExplanation(
            event_id=payload["event_id"],
            latitude=payload["latitude"],
            longitude=payload["longitude"],
            timezone_name=payload["timezone_name"],
        )
        session.add(row)
    for key, value in payload.items():
        setattr(row, key, value)
    return row
