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
    plain_cluster_name: str | None = None
    predicted_class: str
    scientific_label: str | None = None
    simple_label: str | None = None
    morphology: str
    confidence: float
    rarity_score: float
    redshift: float | None = None
    magnitude: float | None = None
    source_field: str | None = None
    instrument: str | None = None
    filter_band: str | None = None
    thumbnail_url: str | None = None
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
    plain_cluster_name: str | None = None
    predicted_class: str
    scientific_label: str | None = None
    simple_label: str | None = None
    x: float
    y: float
    confidence: float
    redshift: float | None = None
    magnitude: float | None = None
    image_url: str


class GalaxyClusterSummaryResponse(BaseModel):
    cluster_id: int
    cluster_name: str
    plain_cluster_name: str | None = None
    count: int
    centroid_x: float
    centroid_y: float
    extent_x: float
    extent_y: float
    avg_rarity: float
    dominant_class: str
    summary: str
    plain_summary: str | None = None
    redshift_min: float | None = None
    redshift_max: float | None = None
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
    observation_source: str | None = None
    observation_program: str | None = None
    source_field: str | None = None
    instrument: str | None = None
    filter_band: str | None = None
    redshift: float
    magnitude: float | None = None
    brightness_score: float | None = None
    lookback_time_gyr: float | None = None
    stellar_mass_log10: float
    star_formation_rate: float
    surface_brightness: float
    feature_tags: list[str]
    morphology_tags: list[str] = []
    data_mode: str | None = None


class GalaxyClusterDetailResponse(BaseModel):
    cluster_id: int
    cluster_name: str
    plain_cluster_name: str | None = None
    count: int
    summary: str
    plain_summary: str | None = None
    dominant_class: str | None = None
    avg_rarity: float | None = None
    centroid_x: float | None = None
    centroid_y: float | None = None
    extent_x: float | None = None
    extent_y: float | None = None
    redshift_min: float | None = None
    redshift_max: float | None = None


class GalaxyDetailResponse(BaseModel):
    image_id: str
    image_url: str
    cluster_id: int
    cluster_name: str
    plain_cluster_name: str | None = None
    predicted_class: str
    scientific_label: str | None = None
    simple_label: str | None = None
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


class GalaxyFilterRangesResponse(BaseModel):
    redshift_min: float
    redshift_max: float
    magnitude_min: float
    magnitude_max: float


class GalaxyStoryStepResponse(BaseModel):
    id: str
    title: str
    body: str


class GalaxyMethodStepResponse(BaseModel):
    title: str
    detail: str


class GalaxyDataSourceResponse(BaseModel):
    label: str
    detail: str


class GalaxyArtifactInfoResponse(BaseModel):
    name: str
    path: str
    description: str


class GalaxyManifestResponse(BaseModel):
    title: str
    subtitle: str
    total_galaxies: int
    data_mode: str
    ranges: GalaxyFilterRangesResponse
    instruments: list[str]
    filter_bands: list[str]
    morphologies: list[str]
    source_fields: list[str]
    clusters: list[GalaxyClusterSummaryResponse]
    story_steps: list[GalaxyStoryStepResponse]
    methodology: list[GalaxyMethodStepResponse]
    data_sources: list[GalaxyDataSourceResponse]
    artifacts: list[GalaxyArtifactInfoResponse]


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


class EventSkyPositionResponse(BaseModel):
    azimuth_deg: float | None = None
    altitude_deg: float | None = None
    direction: str | None = None


class CelestialEventResponse(BaseModel):
    event_id: str
    title: str
    type: str
    start_time: datetime
    end_time: datetime
    peak_time: datetime
    best_viewing_time: datetime
    visibility_score: float
    visibility_label: str
    magnitude: float | None = None
    brightness_score: float
    description: str
    region_applicability: dict
    rarity_score: float
    importance_score: float
    sky_position: EventSkyPositionResponse
    observation_method: str
    duration_minutes: int | float | None = None
    thumbnail: dict
    summary: str
    why_interesting: str = ""
    personalized_rank: float | None = None


class PersonalizedLocationResponse(BaseModel):
    latitude: float
    longitude: float
    timezone: str


class TonightSummaryResponse(BaseModel):
    headline: str
    summary: str
    count: int


class PersonalizedEventsResponse(BaseModel):
    requested_location: PersonalizedLocationResponse
    generated_at: datetime
    tonight_summary: TonightSummaryResponse
    events: list[CelestialEventResponse]


class CelestialExplanationResponse(BaseModel):
    event_id: str
    summary: str
    why_interesting: str
    explanation: str
    source: str
