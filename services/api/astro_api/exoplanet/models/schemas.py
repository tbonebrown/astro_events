from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class DemoTargetResponse(BaseModel):
    target_id: str
    name: str
    aliases: list[str]
    mission: Literal["Kepler", "TESS"]
    description: str
    ra: float | None = None
    dec: float | None = None
    known_period_days: float | None = None
    known_planet: str | None = None
    expected_depth_ppm: float | None = None


class ExoplanetAnalyzeRequest(BaseModel):
    target: str = Field(default="Kepler-10", min_length=1)
    target_type: Literal["auto", "tic", "kic", "name", "coordinates"] = "auto"
    mission: Literal["auto", "TESS", "Kepler"] = "auto"
    sector_or_quarter: str | None = None
    period_min_days: float = Field(default=0.5, gt=0)
    period_max_days: float = Field(default=30.0, gt=0)
    duration_min_hours: float = Field(default=1.0, gt=0)
    duration_max_hours: float = Field(default=10.0, gt=0)
    detrend_method: Literal["savgol", "median", "none"] = "savgol"
    max_lightcurves: int = Field(default=4, ge=1, le=24)
    force_refresh: bool = False
    run_synchronously: bool = False


class ExoplanetJobResponse(BaseModel):
    job_id: str
    status: Literal["queued", "running", "completed", "failed"]
    cache_hit: bool = False


class ExoplanetStatusResponse(BaseModel):
    job_id: str
    status: Literal["queued", "running", "completed", "failed"]
    stage: str
    progress: float = Field(ge=0, le=1)
    steps: list[dict[str, Any]]
    error: str | None = None


class LightCurveSeries(BaseModel):
    time: list[float]
    flux: list[float]
    label: str


class PeriodogramSeries(BaseModel):
    period: list[float]
    power: list[float]
    best_period: float


class FoldedCurveSeries(BaseModel):
    phase: list[float]
    flux: list[float]
    model_phase: list[float]
    model_flux: list[float]


class ArchiveMatch(BaseModel):
    status: str
    catalog: str | None = None
    object_name: str | None = None
    disposition: str | None = None
    period_days: float | None = None
    period_delta_percent: float | None = None
    source_url: str | None = None
    notes: str


class ClassifierResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    label: str
    probabilities: dict[str, float]
    device: str
    backend: str


class CandidateMetrics(BaseModel):
    candidate_id: str
    target_id: str
    period_days: float
    transit_time: float
    duration_hours: float
    depth_ppm: float
    snr: float
    power: float
    observed_transits: int
    radius_ratio: float
    confidence: float
    confidence_label: str
    archive_match: ArchiveMatch
    classifier: ClassifierResult
    score_breakdown: dict[str, float]


class ReportSection(BaseModel):
    title: str
    body: str


class ExoplanetReportResponse(BaseModel):
    title: str
    generated_by: str
    safety_note: str
    sections: list[ReportSection]
    technical_metrics: dict[str, Any]


class ExoplanetAnalysisResult(BaseModel):
    job_id: str
    target: dict[str, Any]
    request: dict[str, Any]
    provenance: dict[str, Any]
    raw_light_curve: LightCurveSeries
    cleaned_light_curve: LightCurveSeries
    periodogram: PeriodogramSeries
    folded_curve: FoldedCurveSeries
    candidates: list[CandidateMetrics]
    report: ExoplanetReportResponse


class BatchScanRequest(BaseModel):
    targets: list[str] = Field(default_factory=list)
    mission: Literal["auto", "TESS", "Kepler"] = "auto"
    period_min_days: float = 0.5
    period_max_days: float = 30.0


class BatchScanResponse(BaseModel):
    submitted: int
    jobs: list[ExoplanetJobResponse]
