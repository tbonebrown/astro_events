function formatMetric(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "n/a";
  }
  return Number(value).toFixed(digits);
}

export default function CandidateSummary({ candidates = [] }) {
  return (
    <article className="panel exoplanet-table-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Candidate summary</p>
          <h2>Transit metrics</h2>
        </div>
      </div>
      <div className="exoplanet-table-wrap">
        <table className="exoplanet-table">
          <thead>
            <tr>
              <th>Period</th>
              <th>Depth</th>
              <th>Duration</th>
              <th>SNR</th>
              <th>Confidence</th>
              <th>Archive match</th>
            </tr>
          </thead>
          <tbody>
            {candidates.map((candidate) => (
              <tr key={candidate.candidate_id}>
                <td>{formatMetric(candidate.period_days, 5)} d</td>
                <td>{formatMetric(candidate.depth_ppm, 1)} ppm</td>
                <td>{formatMetric(candidate.duration_hours, 2)} h</td>
                <td>{formatMetric(candidate.snr, 2)}</td>
                <td>
                  <span className="exoplanet-confidence">{candidate.confidence_label}</span>
                  <strong>{formatMetric(candidate.confidence, 1)}</strong>
                </td>
                <td>{candidate.archive_match?.object_name || candidate.archive_match?.status || "no match"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </article>
  );
}
