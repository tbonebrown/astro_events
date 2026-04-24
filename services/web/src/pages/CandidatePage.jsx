import { useEffect, useState, startTransition } from "react";
import { Link, useParams } from "react-router-dom";
import { getCandidate } from "../api";

export function CandidatePage() {
  const { candidateId } = useParams();
  const [candidate, setCandidate] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!candidateId) return;
    let ignore = false;
    startTransition(() => {
      getCandidate(candidateId)
        .then((row) => {
          if (!ignore) {
            setCandidate(row);
            setError("");
          }
        })
        .catch((err) => {
          if (!ignore) setError(err.message);
        });
    });
    return () => {
      ignore = true;
    };
  }, [candidateId]);

  if (error) {
    return <div className="panel error-box">{error}</div>;
  }

  if (!candidate) {
    return <div className="panel">Loading candidate...</div>;
  }

  const plot = candidate.artifacts.find((artifact) => artifact.artifact_type === "light_curve_plot");

  return (
    <section className="page-grid">
      <Link className="back-link" to="/">
        Back to candidates
      </Link>
      <section className="panel detail-hero">
        <div>
          <p className="eyebrow">{candidate.variability_hint}</p>
          <h2>{candidate.candidate_id}</h2>
          <p className="lede">
            TIC {candidate.tic_id} from sector {candidate.sector} ranked #{candidate.rank} with an
            anomaly score of {candidate.anomaly_score.toFixed(3)}.
          </p>
        </div>
        <div className="score-stack">
          <div>
            <span>Feature outlier</span>
            <strong>{candidate.feature_score.toFixed(3)}</strong>
          </div>
          <div>
            <span>Reconstruction</span>
            <strong>{candidate.reconstruction_error.toFixed(3)}</strong>
          </div>
        </div>
      </section>

      <div className="detail-grid">
        <section className="panel">
          <h3>Why it is interesting</h3>
          <p>{candidate.explanation}</p>
        </section>

        <section className="panel">
          <h3>Score breakdown</h3>
          <dl className="definition-grid">
            {Object.entries(candidate.score_breakdown).map(([key, value]) => (
              <div key={key}>
                <dt>{key}</dt>
                <dd>{Number(value).toFixed(4)}</dd>
              </div>
            ))}
          </dl>
        </section>
      </div>

      <div className="detail-grid">
        <section className="panel">
          <h3>Top engineered features</h3>
          <dl className="definition-grid">
            {Object.entries(candidate.top_features).map(([key, value]) => (
              <div key={key}>
                <dt>{key}</dt>
                <dd>{Number(value).toFixed(4)}</dd>
              </div>
            ))}
          </dl>
        </section>

        <section className="panel">
          <h3>Light-curve plot</h3>
          {plot ? (
            <img className="plot-image" src={plot.url} alt={`${candidate.candidate_id} light curve`} />
          ) : (
            <p>No plot artifact is available for this candidate.</p>
          )}
        </section>
      </div>
    </section>
  );
}

