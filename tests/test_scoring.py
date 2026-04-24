from __future__ import annotations

import numpy as np

from astro_tess.scoring import EnsembleAnomalyScorer


def test_ensemble_scorer_outputs_expected_shapes() -> None:
    rng = np.random.default_rng(11)
    sequences = rng.normal(size=(12, 64))
    features = rng.normal(size=(12, 8))

    scorer = EnsembleAnomalyScorer().fit(sequences, features)
    blended, reconstruction_error, feature_score = scorer.score(sequences, features)

    assert blended.shape == (12,)
    assert reconstruction_error.shape == (12,)
    assert feature_score.shape == (12,)
    assert np.all(blended >= 0.0)
    assert np.all(blended <= 1.0)

