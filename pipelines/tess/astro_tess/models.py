from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import numpy as np


@dataclass(slots=True)
class LightCurveSample:
    tic_id: str
    sector: int
    time: np.ndarray
    flux: np.ndarray
    provenance: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CandidateRecord:
    candidate_id: str
    tic_id: str
    sector: int
    run_date: str
    anomaly_score: float
    feature_score: float
    reconstruction_error: float
    rank: int
    variability_hint: str
    top_features: dict[str, float]
    score_breakdown: dict[str, float]
    provenance: dict[str, Any]
    plot_path: str
    explanation: str = ""


@dataclass(slots=True)
class PipelineRunResult:
    run_date: str
    sector: int
    export_dir: str
    candidates: list[CandidateRecord]
    generated_at: datetime

