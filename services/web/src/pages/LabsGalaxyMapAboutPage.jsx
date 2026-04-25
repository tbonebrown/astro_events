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

export default function LabsGalaxyMapAboutPage() {
  const [manifest, setManifest] = useState(null);

  useEffect(() => {
    fetchGalaxyMapManifest().then(setManifest).catch(() => null);
  }, []);

  return (
    <main className="single-column galaxy-labs-page">
      <LabsNav />
      <section className="panel panel--hero galaxy-labs-copy-hero">
        <p className="eyebrow">Methodology</p>
        <h2>How the Galaxy Embedding Map is built</h2>
        <p className="home-intro__lede">
          This experience is designed as an approachable scientific interface: image cutouts become embeddings, embeddings become map coordinates, and cluster summaries turn that geometry into readable morphology stories.
        </p>
      </section>

      <section className="galaxy-copy-layout">
        {(manifest?.methodology || []).map((step) => (
          <article className="panel galaxy-copy-block" key={step.title}>
            <p className="eyebrow">{step.title}</p>
            <h3>{step.title}</h3>
            <p>{step.detail}</p>
          </article>
        ))}

        <article className="panel galaxy-copy-block">
          <p className="eyebrow">What an embedding means</p>
          <h3>Visual similarity, not a literal sky map</h3>
          <p>
            The map is not plotting RA and Dec. It is plotting similarity in embedding space, so nearby points usually share visual structure such as spiral arms, compact cores, clumpy star-forming regions, or merger signatures.
          </p>
        </article>

        <article className="panel galaxy-copy-block">
          <p className="eyebrow">Why redshift matters</p>
          <h3>A morphology tour across cosmic time</h3>
          <p>
            Higher-redshift galaxies are usually farther away and earlier in cosmic history. That makes the filter panel useful for seeing how smooth, compact, clumpy, or disturbed structures change as we move deeper into the early universe.
          </p>
        </article>
      </section>
    </main>
  );
}
