import { useEffect, useState } from "react";

import {
  fetchTessCandidates,
  fetchTransientDetail,
  fetchTransientReport,
  fetchTransients
} from "./api";
import GalaxyMap from "./components/GalaxyMap";

function readRoute() {
  const pathname = window.location.pathname || "/";
  const parts = pathname.split("/").filter(Boolean);
  if (parts.length === 0) {
    return { page: "home" };
  }
  if (parts[0] === "transients" && parts[1] === "reports") {
    return { page: "report" };
  }
  if (parts[0] === "transients" && parts[1]) {
    return { page: "detail", candidateId: decodeURIComponent(parts[1]) };
  }
  if (parts[0] === "tess") {
    return { page: "tess" };
  }
  if (parts[0] === "galaxy-map") {
    return { page: "galaxy-map" };
  }
  if (parts[0] === "transients") {
    return { page: "feed" };
  }
  return { page: "home" };
}

function setRoute(path) {
  window.history.pushState({}, "", path);
  window.dispatchEvent(new PopStateEvent("popstate"));
}

export function importanceLabel(score, noveltyFlag) {
  if (noveltyFlag && score >= 0.75) {
    return "Priority follow-up";
  }
  if (score >= 0.68) {
    return "High interest";
  }
  if (score >= 0.5) {
    return "Worth watching";
  }
  return "Context only";
}

function metricValue(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "n/a";
  }
  return Number(value).toFixed(digits);
}

function reportDateLabel(runDate) {
  if (!runDate) {
    return "Awaiting first report";
  }
  return runDate;
}

function ProjectCard({ eyebrow, title, description, highlights, cta, onOpen }) {
  return (
    <article className="project-card">
      <div className="project-card__copy">
        <p className="eyebrow">{eyebrow}</p>
        <h3>{title}</h3>
        <p>{description}</p>
      </div>
      <ul className="project-card__list">
        {highlights.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
      <button className="ghost-button" onClick={onOpen}>
        {cta}
      </button>
    </article>
  );
}

function CandidateCard({ candidate, onOpen }) {
  return (
    <article className="candidate-card">
      <div className="candidate-card__meta">
        <span className="candidate-card__rank">#{candidate.rank}</span>
        <span className="candidate-card__badge">
          {importanceLabel(candidate.score, candidate.novelty_flag)}
        </span>
      </div>
      <h3>{candidate.external_alert_id}</h3>
      <p className="candidate-card__summary">{candidate.summary}</p>
      <dl className="candidate-card__grid">
        <div>
          <dt>Class</dt>
          <dd>{candidate.classification_hint}</dd>
        </div>
        <div>
          <dt>Score</dt>
          <dd>{metricValue(candidate.score, 3)}</dd>
        </div>
        <div>
          <dt>Delta mag</dt>
          <dd>{metricValue(candidate.magnitude_change, 2)}</dd>
        </div>
        <div>
          <dt>Sky region</dt>
          <dd>{candidate.sky_region}</dd>
        </div>
      </dl>
      <button className="ghost-button" onClick={() => onOpen(candidate.candidate_id)}>
        Open candidate
      </button>
    </article>
  );
}

function HomeView({
  transients,
  transientError,
  loadingTransients,
  report,
  reportError,
  loadingReport,
  tessCandidates,
  tessError,
  loadingTess,
  onOpenRoute
}) {
  const latestTransient = transients[0];

  return (
    <main className="single-column home-layout">
      <section className="panel panel--hero home-intro">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">About Ohnita</p>
            <h2>A place to learn from astronomy data through guided tours and open exploration.</h2>
          </div>
          <button className="ghost-button" onClick={() => onOpenRoute("/transients")}>
            Open live transient feed
          </button>
        </div>
        <p className="home-intro__lede">
          Ohnita is a public astronomy space built for curiosity. Each section offers a different
          way to explore the sky: fast transient updates, readable nightly summaries, unusual TESS
          signals worth a closer look, and a galaxy map for comparing shape and structure.
        </p>
        <div className="snapshot-grid" aria-label="Project snapshot">
          <article className="snapshot-card">
            <span>Projects on site</span>
            <strong>4</strong>
            <p>Four ways to learn, compare, and follow what the sky is doing.</p>
          </article>
          <article className="snapshot-card">
            <span>Transient watchlist</span>
            <strong>{loadingTransients ? "Loading" : transients.length}</strong>
            <p>
              {transientError
                ? transientError
                : latestTransient
                  ? `${latestTransient.external_alert_id} is the current top-ranked alert.`
                  : "Waiting for the next transient ingest."}
            </p>
          </article>
          <article className="snapshot-card">
            <span>Nightly report</span>
            <strong>{loadingReport ? "Loading" : reportDateLabel(report?.run?.run_date)}</strong>
            <p>{reportError || "Plain-language brief generated from the latest scoring run."}</p>
          </article>
          <article className="snapshot-card">
            <span>TESS anomalies</span>
            <strong>{loadingTess ? "Loading" : tessCandidates.length}</strong>
            <p>
              {tessError
                ? tessError
                : "Ranked candidates from the long-horizon light-curve anomaly pipeline."}
            </p>
          </article>
        </div>
      </section>

      <section className="home-section">
        <div className="section-copy">
          <p className="eyebrow">Explore the collection</p>
          <h2>Each section opens a different path into the data.</h2>
          <p>
            You can start with an overview, follow a live signal, or wander into a visual map. The
            cards below are meant to help visitors learn by moving between different views of the
            same astronomy story.
          </p>
        </div>
        <div className="project-grid">
          <ProjectCard
            eyebrow="Live operations"
            title="Transient alert feed"
            description="A Gaia-first watchlist for short-timescale events. Alerts are scored, ranked, and summarized so observers can quickly see what changed and why it might matter."
            highlights={[
              "Nightly ranked candidates with plain-language summaries",
              "Detail pages with score breakdowns and alert metadata",
              "Built for quick triage instead of raw alert firehoses"
            ]}
            cta="Browse transients"
            onOpen={() => onOpenRoute("/transients")}
          />
          <ProjectCard
            eyebrow="Research brief"
            title="Nightly report"
            description="A narrative layer on top of the alert and scoring pipeline. This report turns the latest run into a readable brief for review, handoff, or morning catch-up."
            highlights={[
              "Generated from the most recent ingest and ranking pass",
              "Good for review, sharing, and daily context",
              "Keeps the public site readable even as the data changes"
            ]}
            cta="Read the latest report"
            onOpen={() => onOpenRoute("/transients/reports/latest")}
          />
          <ProjectCard
            eyebrow="Survey mining"
            title="TESS anomaly watchlist"
            description="A longer-horizon view of the sky that highlights light curves with unusual behavior. It is built for slow looking, comparison, and discovery."
            highlights={[
              "Targets unusual variability rather than immediate transient alerts",
              "Offers a different learning path focused on long-term behavior",
              "Acts as the slower-burn discovery companion to the transient feed"
            ]}
            cta="Open the TESS module"
            onOpen={() => onOpenRoute("/tess")}
          />
          <ProjectCard
            eyebrow="Embedding intelligence"
            title="Galaxy Embedding Map"
            description="A morphology atlas for curious browsing. The map places galaxies in learned embedding space so visitors can move through clusters, compare similar systems, and open plain-language explanations."
            highlights={[
              "Embedding scatter map designed for smooth exploration",
              "Cluster zoom, neighbor highlighting, and rare-object surfacing",
              "Click-through detail with image, metadata, and local-LLM copy"
            ]}
            cta="Launch galaxy map"
            onOpen={() => onOpenRoute("/galaxy-map")}
          />
        </div>
      </section>

      <section className="home-detail-grid">
        <article className="panel">
          <p className="eyebrow">Why these experiences belong together</p>
          <h3>Different views of the same scientific story</h3>
          <p>
            The sections are designed to make astronomy more approachable from more than one angle.
            You can move from alerts to summaries to broader pattern-finding without losing the
            thread of what you are learning.
          </p>
          <ul className="detail-list">
            <li>Quick updates when the sky changes</li>
            <li>Readable summaries for slower, more reflective review</li>
            <li>Visual and exploratory tools for pattern-finding across larger datasets</li>
          </ul>
        </article>

        <article className="panel">
          <p className="eyebrow">How to use the site</p>
          <h3>Start with curiosity, then follow what catches your attention.</h3>
          <p>
            Some visitors want a concise nightly summary, while others want to inspect individual
            candidates or wander through structure in the galaxy map. Ohnita is meant to support
            both guided learning and open-ended exploration.
          </p>
          <ul className="detail-list">
            <li>Check the transient feed for what is changing now</li>
            <li>Read the nightly report for context and plain-language takeaways</li>
            <li>Browse TESS candidates when you want unusual long-term behavior</li>
            <li>Explore the galaxy map when you want to compare shapes and neighborhoods</li>
          </ul>
        </article>
      </section>
    </main>
  );
}

function ReportView({ report, loading, error }) {
  if (loading) {
    return <section className="panel">Loading nightly report...</section>;
  }
  if (error) {
    return <section className="panel panel--error">{error}</section>;
  }
  if (!report) {
    return <section className="panel">No transient report has been ingested yet.</section>;
  }
  return (
    <section className="panel report-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Nightly report</p>
          <h2>{report.title}</h2>
        </div>
        <p className="panel-heading__stamp">{report.run.run_date}</p>
      </div>
      <pre className="markdown-block">{report.markdown}</pre>
    </section>
  );
}

function DetailView({ candidate, loading, error }) {
  if (loading) {
    return <section className="panel">Loading transient candidate...</section>;
  }
  if (error) {
    return <section className="panel panel--error">{error}</section>;
  }
  if (!candidate) {
    return <section className="panel">Select a candidate to see the full evidence card.</section>;
  }
  return (
    <section className="detail-layout">
      <article className="panel detail-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Transient alert</p>
            <h2>{candidate.external_alert_id}</h2>
          </div>
          <span className="candidate-card__badge">
            {importanceLabel(candidate.score, candidate.novelty_flag)}
          </span>
        </div>
        <p className="detail-summary">{candidate.summary}</p>
        <dl className="detail-grid">
          <div>
            <dt>Alert time</dt>
            <dd>{candidate.alert_timestamp}</dd>
          </div>
          <div>
            <dt>Coordinates</dt>
            <dd>
              RA {metricValue(candidate.ra, 4)} / Dec {metricValue(candidate.dec, 4)}
            </dd>
          </div>
          <div>
            <dt>Magnitude</dt>
            <dd>{metricValue(candidate.magnitude, 2)}</dd>
          </div>
          <div>
            <dt>Brightness change</dt>
            <dd>{metricValue(candidate.magnitude_change, 2)}</dd>
          </div>
          <div>
            <dt>Classification</dt>
            <dd>{candidate.classification_hint}</dd>
          </div>
          <div>
            <dt>Region</dt>
            <dd>{candidate.sky_region}</dd>
          </div>
        </dl>
      </article>

      <article className="panel why-panel">
        <p className="eyebrow">Why this matters</p>
        <h3>Signal confidence</h3>
        <ul className="score-list">
          {Object.entries(candidate.score_breakdown).map(([key, value]) => (
            <li key={key}>
              <span>{key.replaceAll("_", " ")}</span>
              <strong>{metricValue(value, 3)}</strong>
            </li>
          ))}
        </ul>
        {candidate.detail_payload?.alert_url ? (
          <a
            className="primary-link"
            href={candidate.detail_payload.alert_url}
            target="_blank"
            rel="noreferrer"
          >
            Open Gaia alert page
          </a>
        ) : null}
      </article>
    </section>
  );
}

function TessView({ candidates, loading, error }) {
  if (loading) {
    return <section className="panel">Loading TESS anomalies...</section>;
  }
  if (error) {
    return <section className="panel panel--error">{error}</section>;
  }
  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Existing module</p>
          <h2>TESS anomaly watchlist</h2>
        </div>
      </div>
      <div className="tess-strip">
        {candidates.map((candidate) => (
          <article className="tess-card" key={candidate.candidate_id}>
            <p>{candidate.tic_id}</p>
            <strong>{metricValue(candidate.anomaly_score, 3)}</strong>
            <span>{candidate.variability_hint}</span>
          </article>
        ))}
      </div>
    </section>
  );
}

export default function App() {
  const [route, setRouteState] = useState(readRoute());
  const [transients, setTransients] = useState([]);
  const [transientError, setTransientError] = useState("");
  const [loadingTransients, setLoadingTransients] = useState(true);
  const [selectedTransient, setSelectedTransient] = useState(null);
  const [detailError, setDetailError] = useState("");
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [report, setReport] = useState(null);
  const [reportError, setReportError] = useState("");
  const [loadingReport, setLoadingReport] = useState(true);
  const [tessCandidates, setTessCandidates] = useState([]);
  const [tessError, setTessError] = useState("");
  const [loadingTess, setLoadingTess] = useState(true);

  useEffect(() => {
    const onPopState = () => setRouteState(readRoute());
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  useEffect(() => {
    setLoadingTransients(true);
    fetchTransients()
      .then((data) => {
        setTransients(data);
        setTransientError("");
      })
      .catch((error) => setTransientError(error.message))
      .finally(() => setLoadingTransients(false));

    setLoadingReport(true);
    fetchTransientReport()
      .then((data) => {
        setReport(data);
        setReportError("");
      })
      .catch((error) => setReportError(error.message))
      .finally(() => setLoadingReport(false));

    setLoadingTess(true);
    fetchTessCandidates()
      .then((data) => {
        setTessCandidates(data);
        setTessError("");
      })
      .catch((error) => setTessError(error.message))
      .finally(() => setLoadingTess(false));
  }, []);

  useEffect(() => {
    if (route.page !== "detail" || !route.candidateId) {
      return;
    }
    setLoadingDetail(true);
    fetchTransientDetail(route.candidateId)
      .then((data) => {
        setSelectedTransient(data);
        setDetailError("");
      })
      .catch((error) => setDetailError(error.message))
      .finally(() => setLoadingDetail(false));
  }, [route]);

  return (
    <div className="app-shell">
      <div className="hero-glow hero-glow--one" />
      <div className="hero-glow hero-glow--two" />

      <header className="hero">
        <div className="hero__copy">
          <p className="eyebrow">Ohnita.com</p>
          <h1>A place to learn from the sky through live data and open exploration.</h1>
          <p className="hero__lede">
            Ohnita brings together astronomy observations, explanations, and interactive views so
            visitors can explore what is changing, understand why it matters, and keep following
            their curiosity.
          </p>
        </div>
        <nav className="nav-tabs" aria-label="Primary">
          <button onClick={() => setRoute("/")}>Home</button>
          <button onClick={() => setRoute("/transients")}>Transient feed</button>
          <button onClick={() => setRoute("/transients/reports/latest")}>Nightly report</button>
          <button onClick={() => setRoute("/tess")}>TESS module</button>
          <button onClick={() => setRoute("/galaxy-map")}>Galaxy map</button>
        </nav>
      </header>

      {route.page === "home" ? (
        <HomeView
          transients={transients}
          transientError={transientError}
          loadingTransients={loadingTransients}
          report={report}
          reportError={reportError}
          loadingReport={loadingReport}
          tessCandidates={tessCandidates}
          tessError={tessError}
          loadingTess={loadingTess}
          onOpenRoute={setRoute}
        />
      ) : null}

      {route.page === "feed" ? (
        <main className="page-grid">
          <section className="panel panel--hero">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Tonight's watchlist</p>
                <h2>Transient Alerts</h2>
              </div>
              <button className="ghost-button" onClick={() => setRoute("/transients/reports/latest")}>
                View report
              </button>
            </div>
            {loadingTransients ? <p>Loading latest candidates...</p> : null}
            {transientError ? <p className="error-copy">{transientError}</p> : null}
            <div className="candidate-grid">
              {transients.map((candidate) => (
                <CandidateCard
                  key={candidate.candidate_id}
                  candidate={candidate}
                  onOpen={(candidateId) => setRoute(`/transients/${encodeURIComponent(candidateId)}`)}
                />
              ))}
            </div>
          </section>
          <aside className="side-column">
            <article className="panel">
              <p className="eyebrow">Why this module works</p>
              <h3>High-signal, low-friction value</h3>
              <p>
                The pipeline uses Gaia alerts for immediate real events, your workstation for batch
                scoring, and the existing API plus dashboard stack for publishing ranked results.
              </p>
            </article>
            <ReportView report={report} loading={loadingReport} error={reportError} />
          </aside>
        </main>
      ) : null}

      {route.page === "report" ? (
        <main className="single-column">
          <ReportView report={report} loading={loadingReport} error={reportError} />
        </main>
      ) : null}

      {route.page === "detail" ? (
        <main className="single-column">
          <DetailView candidate={selectedTransient} loading={loadingDetail} error={detailError} />
        </main>
      ) : null}

      {route.page === "tess" ? (
        <main className="single-column">
          <TessView candidates={tessCandidates} loading={loadingTess} error={tessError} />
        </main>
      ) : null}

      {route.page === "galaxy-map" ? <GalaxyMap /> : null}
    </div>
  );
}
