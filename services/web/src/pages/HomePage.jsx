import { useEffect, useMemo, useState, startTransition, useDeferredValue } from "react";
import { getCandidates, getLatestRun } from "../api";
import { CandidateTable } from "../components/CandidateTable";
import { StatCard } from "../components/StatCard";

export function HomePage() {
  const [latestRun, setLatestRun] = useState(null);
  const [candidates, setCandidates] = useState([]);
  const [sector, setSector] = useState("");
  const [minScore, setMinScore] = useState("0");
  const [error, setError] = useState("");
  const deferredMinScore = useDeferredValue(minScore);

  useEffect(() => {
    let ignore = false;
    startTransition(() => {
      Promise.all([getLatestRun(), getCandidates({ limit: 30 })])
        .then(([run, rows]) => {
          if (ignore) return;
          setLatestRun(run);
          setSector(String(run.sector));
          setCandidates(rows);
          setError("");
        })
        .catch((err) => {
          if (!ignore) setError(err.message);
        });
    });
    return () => {
      ignore = true;
    };
  }, []);

  useEffect(() => {
    if (!sector) return;
    let ignore = false;
    startTransition(() => {
      getCandidates({
        sector: Number(sector),
        minScore: Number(deferredMinScore || 0),
        limit: 30,
      })
        .then((rows) => {
          if (!ignore) setCandidates(rows);
        })
        .catch((err) => {
          if (!ignore) setError(err.message);
        });
    });
    return () => {
      ignore = true;
    };
  }, [sector, deferredMinScore]);

  const topScore = useMemo(() => {
    if (candidates.length === 0) return "0.000";
    return Math.max(...candidates.map((row) => row.anomaly_score)).toFixed(3);
  }, [candidates]);

  return (
    <section className="page-grid">
      <div className="stats-grid">
        <StatCard label="Latest sector" value={latestRun?.sector ?? "—"} />
        <StatCard label="Ranked candidates" value={latestRun?.candidate_count ?? "—"} tone="warm" />
        <StatCard label="Top anomaly score" value={topScore} tone="sharp" />
      </div>

      <section className="panel filter-panel">
        <div>
          <p className="eyebrow">Nightly discovery feed</p>
          <h2>Ranked light-curve candidates</h2>
        </div>
        <div className="filters">
          <label>
            Sector
            <input value={sector} onChange={(event) => setSector(event.target.value)} />
          </label>
          <label>
            Minimum score
            <input
              value={minScore}
              onChange={(event) => setMinScore(event.target.value)}
              type="number"
              min="0"
              max="1"
              step="0.05"
            />
          </label>
        </div>
      </section>

      {error ? <div className="panel error-box">{error}</div> : <CandidateTable rows={candidates} />}
    </section>
  );
}

