from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from astro_api.database import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class NightlyRun(Base):
    __tablename__ = "nightly_runs"
    __table_args__ = (UniqueConstraint("run_date", "sector", name="uq_run_date_sector"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_date: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    sector: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="published")
    candidate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    export_dir: Mapped[str] = mapped_column(String(512), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    candidates: Mapped[list["Candidate"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="Candidate.rank",
    )
    reports: Mapped[list["NightlyReport"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )


class Candidate(Base):
    __tablename__ = "candidates"

    candidate_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("nightly_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    tic_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    sector: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    run_date: Mapped[str] = mapped_column(String(32), nullable=False)
    anomaly_score: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    feature_score: Mapped[float] = mapped_column(Float, nullable=False)
    reconstruction_error: Mapped[float] = mapped_column(Float, nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    variability_hint: Mapped[str] = mapped_column(String(128), nullable=False)
    top_features: Mapped[dict] = mapped_column(JSON, nullable=False)
    score_breakdown: Mapped[dict] = mapped_column(JSON, nullable=False)
    provenance: Mapped[dict] = mapped_column(JSON, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False, default="")
    explanation_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    run: Mapped[NightlyRun] = relationship(back_populates="candidates")
    artifacts: Mapped[list["CandidateArtifact"]] = relationship(
        back_populates="candidate",
        cascade="all, delete-orphan",
    )


class CandidateArtifact(Base):
    __tablename__ = "candidate_artifacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("candidates.candidate_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    artifact_type: Mapped[str] = mapped_column(String(32), nullable=False)
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    candidate: Mapped[Candidate] = relationship(back_populates="artifacts")


class NightlyReport(Base):
    __tablename__ = "nightly_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("nightly_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    markdown: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    summary_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    run: Mapped[NightlyRun] = relationship(back_populates="reports")


class TransientRun(Base):
    __tablename__ = "transient_runs"
    __table_args__ = (UniqueConstraint("run_date", "source_name", name="uq_transient_run_date_source"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_date: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source_name: Mapped[str] = mapped_column(String(32), nullable=False, index=True, default="gaia")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="published")
    candidate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    export_dir: Mapped[str] = mapped_column(String(512), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    candidates: Mapped[list["TransientCandidate"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="TransientCandidate.rank",
    )
    reports: Mapped[list["TransientReport"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )


class TransientCandidate(Base):
    __tablename__ = "transient_candidates"

    candidate_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("transient_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_name: Mapped[str] = mapped_column(String(32), nullable=False, default="gaia", index=True)
    external_alert_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    run_date: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    alert_timestamp: Mapped[str] = mapped_column(String(64), nullable=False)
    ra: Mapped[float] = mapped_column(Float, nullable=False)
    dec: Mapped[float] = mapped_column(Float, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    rank: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    score_breakdown: Mapped[dict] = mapped_column(JSON, nullable=False)
    classification_hint: Mapped[str] = mapped_column(String(128), nullable=False)
    novelty_flag: Mapped[bool] = mapped_column(nullable=False, default=False)
    magnitude: Mapped[float] = mapped_column(Float, nullable=False)
    magnitude_change: Mapped[float] = mapped_column(Float, nullable=False)
    sky_region: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    provenance: Mapped[dict] = mapped_column(JSON, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    detail_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    run: Mapped[TransientRun] = relationship(back_populates="candidates")
    artifacts: Mapped[list["TransientArtifact"]] = relationship(
        back_populates="candidate",
        cascade="all, delete-orphan",
    )


class TransientArtifact(Base):
    __tablename__ = "transient_artifacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("transient_candidates.candidate_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    artifact_type: Mapped[str] = mapped_column(String(32), nullable=False)
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    candidate: Mapped[TransientCandidate] = relationship(back_populates="artifacts")


class TransientReport(Base):
    __tablename__ = "transient_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("transient_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    markdown: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    summary_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    run: Mapped[TransientRun] = relationship(back_populates="reports")


class CelestialEvent(Base):
    __tablename__ = "celestial_events"

    event_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    source_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    peak_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    magnitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    region_bounds_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    coordinates_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    observation_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    media_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    source_payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    rarity_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    importance_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    summary_seed: Mapped[str] = mapped_column(Text, nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    visibility_rows: Mapped[list["EventVisibility"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
    )
    cached_explanations: Mapped[list["CachedCelestialExplanation"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
    )


class EventVisibility(Base):
    __tablename__ = "event_visibility"
    __table_args__ = (UniqueConstraint("event_id", "region_key", name="uq_event_visibility_region"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[str] = mapped_column(
        ForeignKey("celestial_events.event_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    region_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    visibility_score: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    best_viewing_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    summary_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    event: Mapped[CelestialEvent] = relationship(back_populates="visibility_rows")


class CachedCelestialExplanation(Base):
    __tablename__ = "cached_explanations"
    __table_args__ = (
        UniqueConstraint(
            "event_id",
            "latitude",
            "longitude",
            "timezone_name",
            name="uq_celestial_copy_location",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[str] = mapped_column(
        ForeignKey("celestial_events.event_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    timezone_name: Mapped[str] = mapped_column(String(64), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    why_interesting: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="fallback")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    event: Mapped[CelestialEvent] = relationship(back_populates="cached_explanations")
