import { Link } from "react-router-dom";

export function CandidateTable({ rows }) {
  return (
    <div className="panel panel-table">
      <table>
        <thead>
          <tr>
            <th>Rank</th>
            <th>Candidate</th>
            <th>Sector</th>
            <th>Score</th>
            <th>Hint</th>
            <th>Top Signal</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.candidate_id}>
              <td>{row.rank}</td>
              <td>
                <Link to={`/candidates/${encodeURIComponent(row.candidate_id)}`}>
                  {row.candidate_id}
                </Link>
              </td>
              <td>{row.sector}</td>
              <td>{row.anomaly_score.toFixed(3)}</td>
              <td>{row.variability_hint}</td>
              <td>{Object.entries(row.top_features)[0]?.[0] ?? "n/a"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

