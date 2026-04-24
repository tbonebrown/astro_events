import { useEffect, useState, startTransition } from "react";
import { getLatestReport } from "../api";

export function ReportPage() {
  const [report, setReport] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let ignore = false;
    startTransition(() => {
      getLatestReport()
        .then((row) => {
          if (!ignore) setReport(row);
        })
        .catch((err) => {
          if (!ignore) setError(err.message);
        });
    });
    return () => {
      ignore = true;
    };
  }, []);

  if (error) {
    return <div className="panel error-box">{error}</div>;
  }

  if (!report) {
    return <div className="panel">Loading nightly report...</div>;
  }

  return (
    <section className="page-grid">
      <section className="panel">
        <p className="eyebrow">Nightly report</p>
        <h2>{report.title}</h2>
        <p className="lede">
          Generated for sector {report.run.sector} on {report.run.run_date} with model{" "}
          <code>{report.model_name}</code>.
        </p>
      </section>
      <section className="panel report-body">
        <pre>{report.markdown}</pre>
      </section>
    </section>
  );
}

