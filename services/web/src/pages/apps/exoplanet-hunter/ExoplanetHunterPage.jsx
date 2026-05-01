import { useEffect, useMemo, useState } from "react";

import {
  fetchExoplanetDemoTargets,
  fetchExoplanetResult,
  fetchExoplanetStatus,
  startExoplanetAnalysis
} from "../../../api";
import AIReportPanel from "../../../components/exoplanet/AIReportPanel";
import CandidateSummary from "../../../components/exoplanet/CandidateSummary";
import DemoTargetGallery from "../../../components/exoplanet/DemoTargetGallery";
import FoldedTransitChart from "../../../components/exoplanet/FoldedTransitChart";
import LightCurveChart from "../../../components/exoplanet/LightCurveChart";
import PeriodogramChart from "../../../components/exoplanet/PeriodogramChart";
import TargetSearch from "../../../components/exoplanet/TargetSearch";

const DEFAULT_FORM = {
  target: "Kepler-10",
  mission: "auto",
  period_min_days: 0.5,
  period_max_days: 30,
  duration_min_hours: 1,
  duration_max_hours: 10,
  detrend_method: "savgol"
};

function metric(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "n/a";
  }
  return Number(value).toFixed(digits);
}

function ProcessingTimeline({ status }) {
  const steps =
    status?.steps || [
      { id: "resolve", label: "resolving target", status: "pending" },
      { id: "download", label: "downloading light curve", status: "pending" },
      { id: "clean", label: "cleaning signal", status: "pending" },
      { id: "search", label: "searching transit periods", status: "pending" },
      { id: "fold", label: "folding light curve", status: "pending" },
      { id: "archive", label: "checking archives", status: "pending" },
      { id: "report", label: "generating report", status: "pending" }
    ];

  return (
    <article className="panel exoplanet-timeline">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Processing status</p>
          <h2>{status?.stage || "Ready for a target"}</h2>
        </div>
        <strong>{metric((status?.progress || 0) * 100, 0)}%</strong>
      </div>
      <div className="exoplanet-progress">
        <span style={{ width: `${(status?.progress || 0) * 100}%` }} />
      </div>
      <ol className="exoplanet-steps">
        {steps.map((step) => (
          <li className={`is-${step.status}`} key={step.id}>
            <span />
            {step.label}
          </li>
        ))}
      </ol>
      {status?.error ? <p className="error-copy">{status.error}</p> : null}
    </article>
  );
}

function ResultStats({ result }) {
  const candidate = result?.candidates?.[0];
  return (
    <section className="exoplanet-stat-grid" aria-label="Analysis summary">
      <article>
        <span>Detected period</span>
        <strong>{candidate ? `${metric(candidate.period_days, 5)} d` : "Awaiting signal"}</strong>
      </article>
      <article>
        <span>Transit depth</span>
        <strong>{candidate ? `${metric(candidate.depth_ppm, 1)} ppm` : "n/a"}</strong>
      </article>
      <article>
        <span>Classifier</span>
        <strong>{candidate?.classifier?.label?.replaceAll("_", " ") || "not run"}</strong>
      </article>
      <article>
        <span>Archive lookup</span>
        <strong>{candidate?.archive_match?.object_name || candidate?.archive_match?.status || "pending"}</strong>
      </article>
    </section>
  );
}

function ExportControls({ result }) {
  const reportHtml = useMemo(() => {
    if (!result?.report) {
      return "";
    }
    const sections = result.report.sections
      .map((section) => `<h2>${section.title}</h2><p>${section.body}</p>`)
      .join("");
    return `<!doctype html><html><head><meta charset="utf-8"><title>${result.report.title}</title></head><body><h1>${result.report.title}</h1><p>${result.report.safety_note}</p>${sections}</body></html>`;
  }, [result]);

  function exportHtml() {
    if (!reportHtml) {
      return;
    }
    const blob = new Blob([reportHtml], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${result.target.target_id}-exoplanet-report.html`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="exoplanet-export-row">
      <button className="ghost-button" type="button" disabled={!result} onClick={() => window.print()}>
        Export PDF
      </button>
      <button className="ghost-button" type="button" disabled={!result} onClick={exportHtml}>
        Export HTML
      </button>
    </div>
  );
}

export default function ExoplanetHunterPage() {
  const [demoTargets, setDemoTargets] = useState([]);
  const [form, setForm] = useState(DEFAULT_FORM);
  const [jobId, setJobId] = useState("");
  const [status, setStatus] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchExoplanetDemoTargets()
      .then((targets) => {
        setDemoTargets(targets);
        setError("");
      })
      .catch((demoError) => setError(demoError.message));
  }, []);

  useEffect(() => {
    if (!jobId) {
      return undefined;
    }
    let active = true;
    const interval = window.setInterval(async () => {
      try {
        const nextStatus = await fetchExoplanetStatus(jobId);
        if (!active) {
          return;
        }
        setStatus(nextStatus);
        if (nextStatus.status === "completed") {
          const nextResult = await fetchExoplanetResult(jobId);
          if (active) {
            setResult(nextResult);
            setLoading(false);
            window.clearInterval(interval);
          }
        }
        if (nextStatus.status === "failed") {
          setLoading(false);
          window.clearInterval(interval);
        }
      } catch (pollError) {
        if (active) {
          setError(pollError.message);
          setLoading(false);
          window.clearInterval(interval);
        }
      }
    }, 1200);
    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, [jobId]);

  function updateForm(patch) {
    setForm((current) => ({ ...current, ...patch }));
  }

  function selectDemo(target) {
    setForm((current) => ({
      ...current,
      target: target.name,
      mission: target.mission,
      period_min_days: target.known_period_days && target.known_period_days < 1 ? 0.3 : 0.5,
      period_max_days: target.known_period_days && target.known_period_days > 30 ? Math.ceil(target.known_period_days * 1.15) : 30
    }));
  }

  async function submitAnalysis(event) {
    event.preventDefault();
    setLoading(true);
    setResult(null);
    setError("");
    setStatus(null);
    try {
      const job = await startExoplanetAnalysis(form);
      setJobId(job.job_id);
    } catch (submitError) {
      setError(submitError.message);
      setLoading(false);
    }
  }

  return (
    <main className="single-column exoplanet-page">
      <section className="panel exoplanet-hero">
        <div className="exoplanet-hero__copy">
          <p className="eyebrow">Apps / Exoplanet Hunter</p>
          <h2>Exoplanet Hunter</h2>
          <p>
            Search real NASA light curves for the fingerprints of distant worlds. The numerical
            pipeline runs classical transit detection first, then uses GPU-capable classification
            and a local LLM only to explain the evidence.
          </p>
        </div>
        <ResultStats result={result} />
      </section>

      {error ? <section className="panel panel--error">{error}</section> : null}

      <DemoTargetGallery targets={demoTargets} selectedTarget={form.target} onSelect={selectDemo} />

      <section className="exoplanet-control-grid">
        <TargetSearch form={form} loading={loading} onChange={updateForm} onSubmit={submitAnalysis} />
        <ProcessingTimeline status={status} />
      </section>

      <section className="exoplanet-viz-grid">
        <LightCurveChart series={result?.raw_light_curve} title="Raw light curve" />
        <LightCurveChart series={result?.cleaned_light_curve} title="Cleaned light curve" eyebrow="Detrended" />
        <PeriodogramChart periodogram={result?.periodogram} />
        <FoldedTransitChart folded={result?.folded_curve} />
      </section>

      <CandidateSummary candidates={result?.candidates || []} />

      <section className="exoplanet-report-layout">
        <AIReportPanel report={result?.report} />
        <article className="panel exoplanet-ops">
          <p className="eyebrow">Export and provenance</p>
          <h2>Share the evidence, not a discovery claim.</h2>
          <p>
            Reports preserve the candidate language and include the source, cache status, archive
            lookup, classifier backend, and technical metrics used by the explanation.
          </p>
          <ExportControls result={result} />
          {result?.provenance ? (
            <dl className="exoplanet-provenance">
              <div>
                <dt>Source</dt>
                <dd>{result.provenance.source}</dd>
              </div>
              <div>
                <dt>Mission</dt>
                <dd>{result.provenance.mission}</dd>
              </div>
              <div>
                <dt>Cache</dt>
                <dd>{result.provenance.cache_hit ? "hit" : "stored"}</dd>
              </div>
            </dl>
          ) : null}
        </article>
      </section>
    </main>
  );
}
