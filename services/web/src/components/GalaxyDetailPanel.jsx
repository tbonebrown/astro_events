function statValue(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "n/a";
  }
  return Number(value).toFixed(digits);
}

export default function GalaxyDetailPanel({
  detail,
  explanation,
  loading,
  loadingExplanation,
  error,
  onSelectGalaxy,
  onExploreCluster
}) {
  if (loading) {
    return <aside className="panel galaxy-detail-panel">Loading selected galaxy...</aside>;
  }
  if (error) {
    return <aside className="panel panel--error galaxy-detail-panel">{error}</aside>;
  }
  if (!detail) {
    return (
      <aside className="panel galaxy-detail-panel galaxy-detail-panel--empty">
        <p className="eyebrow">Galaxy detail</p>
        <h3>Select a galaxy to inspect its neighborhood.</h3>
        <p>
          Click any point on the map to open its image, metadata, nearest neighbors, and generated
          morphology summary.
        </p>
      </aside>
    );
  }

  return (
    <aside className="panel galaxy-detail-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Selected galaxy</p>
          <h2>{detail.image_id}</h2>
        </div>
        <button className="ghost-button" onClick={() => onExploreCluster(detail.cluster_summary)}>
          Explore cluster
        </button>
      </div>

      <div className="galaxy-detail-media">
        <img src={detail.image_url} alt={detail.image_id} className="galaxy-detail-image" />
        <div className="galaxy-detail-chip-stack">
          <span className="galaxy-badge">{detail.morphology}</span>
          <span className="galaxy-badge galaxy-badge--muted">{detail.cluster_name}</span>
          {detail.rarity_score >= 0.82 ? <span className="galaxy-badge galaxy-badge--hot">Rare object</span> : null}
        </div>
      </div>

      <article className="galaxy-copy-card">
        <p className="eyebrow">LLM interpretation</p>
        <p className="galaxy-explanation">
          {loadingExplanation ? "Generating morphology explanation..." : explanation || "No explanation available yet."}
        </p>
      </article>

      <article className="galaxy-copy-card">
        <p className="eyebrow">Cluster context</p>
        <h3>{detail.cluster_summary.cluster_name}</h3>
        <p>{detail.cluster_summary.summary}</p>
        <dl className="galaxy-meta-grid">
          <div>
            <dt>Members</dt>
            <dd>{detail.cluster_summary.count.toLocaleString()}</dd>
          </div>
          <div>
            <dt>Dominant class</dt>
            <dd>{detail.cluster_summary.dominant_class || detail.predicted_class}</dd>
          </div>
          <div>
            <dt>Confidence</dt>
            <dd>{statValue(detail.confidence, 3)}</dd>
          </div>
          <div>
            <dt>Redshift</dt>
            <dd>{statValue(detail.metadata.redshift, 4)}</dd>
          </div>
        </dl>
      </article>

      <article className="galaxy-copy-card">
        <p className="eyebrow">Metadata</p>
        <dl className="galaxy-meta-grid">
          <div>
            <dt>Survey</dt>
            <dd>{detail.metadata.survey}</dd>
          </div>
          <div>
            <dt>Catalog</dt>
            <dd>{detail.metadata.catalog}</dd>
          </div>
          <div>
            <dt>RA / Dec</dt>
            <dd>
              {statValue(detail.coordinates.ra, 2)} / {statValue(detail.coordinates.dec, 2)}
            </dd>
          </div>
          <div>
            <dt>Stellar mass</dt>
            <dd>{statValue(detail.metadata.stellar_mass_log10, 2)} log10(Msun)</dd>
          </div>
          <div>
            <dt>Star formation</dt>
            <dd>{statValue(detail.metadata.star_formation_rate, 2)} Msun/yr</dd>
          </div>
          <div>
            <dt>Surface brightness</dt>
            <dd>{statValue(detail.metadata.surface_brightness, 2)} mag/arcsec^2</dd>
          </div>
        </dl>
        <div className="galaxy-tag-row">
          {detail.metadata.feature_tags.map((tag) => (
            <span key={tag} className="galaxy-tag">
              {tag}
            </span>
          ))}
        </div>
      </article>

      <article className="galaxy-copy-card">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Nearest neighbors</p>
            <h3>Similar galaxies in embedding space</h3>
          </div>
        </div>
        <div className="galaxy-neighbor-grid">
          {detail.nearest_neighbors.map((neighbor) => (
            <button
              key={neighbor.image_id}
              className="galaxy-neighbor-card"
              onClick={() => onSelectGalaxy(neighbor.image_id)}
            >
              <img src={neighbor.image_url} alt={neighbor.image_id} />
              <strong>{neighbor.predicted_class}</strong>
              <span>{neighbor.cluster_name}</span>
            </button>
          ))}
        </div>
      </article>
    </aside>
  );
}
