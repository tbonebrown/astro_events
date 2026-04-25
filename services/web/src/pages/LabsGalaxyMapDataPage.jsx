import { useEffect, useState } from "react";

import { fetchGalaxyMapManifest } from "../api";

function navigate(path) {
  window.history.pushState({}, "", path);
  window.dispatchEvent(new PopStateEvent("popstate"));
}

function LabsNav() {
  return (
    <div className="labs-subnav" aria-label="Galaxy map sections">
      <button className="ghost-button" type="button" onClick={() => navigate("/labs/galaxy-map")}>
        Experience
      </button>
      <button className="ghost-button" type="button" onClick={() => navigate("/labs/galaxy-map/about")}>
        Methodology
      </button>
      <button className="ghost-button" type="button" onClick={() => navigate("/labs/galaxy-map/data")}>
        Data
      </button>
    </div>
  );
}

export default function LabsGalaxyMapDataPage() {
  const [manifest, setManifest] = useState(null);

  useEffect(() => {
    fetchGalaxyMapManifest().then(setManifest).catch(() => null);
  }, []);

  return (
    <main className="single-column galaxy-labs-page">
      <LabsNav />
      <section className="panel panel--hero galaxy-labs-copy-hero">
        <p className="eyebrow">Data and limits</p>
        <h2>Artifacts, sources, and swap-in points for real JWST data</h2>
        <p className="home-intro__lede">
          The app is shipped with a self-contained sample so it runs immediately, but the artifact layout is already shaped for a real JWST / MAST ingestion flow.
        </p>
      </section>

      <section className="galaxy-copy-layout">
        <article className="panel galaxy-copy-block">
          <p className="eyebrow">Data sources</p>
          <h3>Current source configuration</h3>
          <div className="galaxy-text-list">
            {(manifest?.data_sources || []).map((source) => (
              <div key={source.label}>
                <strong>{source.label}</strong>
                <p>{source.detail}</p>
              </div>
            ))}
          </div>
        </article>

        <article className="panel galaxy-copy-block">
          <p className="eyebrow">Artifact layout</p>
          <h3>Files used by the frontend and API</h3>
          <div className="galaxy-artifact-list">
            {(manifest?.artifacts || []).map((artifact) => (
              <div key={artifact.name} className="galaxy-artifact-row">
                <strong>{artifact.name}</strong>
                <span>{artifact.path}</span>
                <p>{artifact.description}</p>
              </div>
            ))}
          </div>
        </article>

        <article className="panel galaxy-copy-block">
          <p className="eyebrow">Known limitations</p>
          <h3>What the public demo is and is not claiming</h3>
          <p>
            The shipped sample is deterministic and JWST-inspired so the interface is fully runnable without downloading telescope data during setup. When you swap in a real catalog, the same pages, API routes, and artifact layout continue to work.
          </p>
        </article>
      </section>
    </main>
  );
}
