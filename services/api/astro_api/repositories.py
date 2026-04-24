from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from astro_api.models import (
    Candidate,
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
