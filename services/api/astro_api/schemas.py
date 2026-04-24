from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CandidateArtifactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    artifact_type: str
    url: str
    metadata_json: dict


class CandidateSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    candidate_id: str
    tic_id: str
    sector: int
    run_date: str
    anomaly_score: float
    feature_score: float
    reconstruction_error: float
    rank: int
    variability_hint: str
    top_features: dict
    score_breakdown: dict
    provenance: dict
    explanation: str
    explanation_status: str


class CandidateDetailResponse(CandidateSummaryResponse):
    artifacts: list[CandidateArtifactResponse]


class NightlyRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_date: str
    sector: int
    status: str
    candidate_count: int
    export_dir: str
    generated_at: datetime


class NightlyReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    markdown: str
    model_name: str
    generated_at: datetime
    summary_json: dict
    run: NightlyRunResponse


class HealthResponse(BaseModel):
    status: str
    environment: str
    latest_run: NightlyRunResponse | None = None


class GalaxyPointResponse(BaseModel):
    image_id: str
    x: float
    y: float
    z: float
    cluster_id: int
    cluster_name: str
    predicted_class: str
    morphology: str
    confidence: float
    rarity_score: float
    is_outlier: bool


class GalaxyBoundsResponse(BaseModel):
    min_x: float
    max_x: float
    min_y: float
    max_y: float
    min_z: float
    max_z: float


class GalaxyListResponse(BaseModel):
    total: int
    returned: int
    visible_clusters: list[int]
    bounds: GalaxyBoundsResponse
    points: list[GalaxyPointResponse]


class GalaxyNeighborResponse(BaseModel):
    image_id: str
    cluster_id: int
    cluster_name: str
    predicted_class: str
    x: float
    y: float
    confidence: float
    image_url: str


class GalaxyClusterSummaryResponse(BaseModel):
    cluster_id: int
    cluster_name: str
    count: int
    centroid_x: float
    centroid_y: float
    extent_x: float
    extent_y: float
    avg_rarity: float
    dominant_class: str
    summary: str
    representatives: list[GalaxyNeighborResponse]


class GalaxyDetailCoordinatesResponse(BaseModel):
    x: float
    y: float
    z: float
    ra: float
    dec: float


class GalaxyMetadataResponse(BaseModel):
    catalog: str
    survey: str
    redshift: float
    stellar_mass_log10: float
    star_formation_rate: float
    surface_brightness: float
    feature_tags: list[str]


class GalaxyClusterDetailResponse(BaseModel):
    cluster_id: int
    cluster_name: str
    count: int
    summary: str
    dominant_class: str | None = None
    avg_rarity: float | None = None
    centroid_x: float | None = None
    centroid_y: float | None = None
    extent_x: float | None = None
    extent_y: float | None = None


class GalaxyDetailResponse(BaseModel):
    image_id: str
    image_url: str
    cluster_id: int
    cluster_name: str
    predicted_class: str
    morphology: str
    confidence: float
    rarity_score: float
    coordinates: GalaxyDetailCoordinatesResponse
    metadata: GalaxyMetadataResponse
    cluster_summary: GalaxyClusterDetailResponse
    nearest_neighbors: list[GalaxyNeighborResponse]


class GalaxyExplanationResponse(BaseModel):
    image_id: str
    explanation: str
    source: str


class TransientArtifactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    artifact_type: str
    url: str
    metadata_json: dict


class TransientCandidateSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    candidate_id: str
    source_name: str
    external_alert_id: str
    run_date: str
    alert_timestamp: str
    ra: float
    dec: float
    score: float
    rank: int
    score_breakdown: dict
    classification_hint: str
    novelty_flag: bool
    magnitude: float
    magnitude_change: float
    sky_region: str
    provenance: dict
    summary: str
    detail_payload: dict


class TransientCandidateDetailResponse(TransientCandidateSummaryResponse):
    artifacts: list[TransientArtifactResponse]


class TransientRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_date: str
    source_name: str
    status: str
    candidate_count: int
    export_dir: str
    generated_at: datetime


class TransientReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    markdown: str
    model_name: str
    generated_at: datetime
    summary_json: dict
    run: TransientRunResponse
