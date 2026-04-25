import GalaxyCard from "./GalaxyCard";

function formatValue(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "n/a";
  }
  return Number(value).toFixed(digits);
}

export default function GalaxyDetailDrawer({
  detail,
  explanation,
  loading,
  loadingExplanation,
  error,
  labelMode = "scientific",
  similarModeActive,
  onSelectGalaxy,
  onFindSimilar,
}) {
  if (loading) {
    return <aside className="panel galaxy-drawer">Loading galaxy detail...</aside>;
  }
  if (error) {
    return <aside className="panel panel--error galaxy-drawer">{error}</aside>;
  }
  if (!detail) {
    return (
      <aside className="panel galaxy-drawer galaxy-drawer--empty">
        <p className="eyebrow">Galaxy detail</p>
        <h3>Select a point to inspect its image, metadata, and nearest visual neighbors.</h3>
        <p>The map is designed to work as both an exploratory tool and a readable story for non-astronomers.</p>
      </aside>
    );
  }

  const title = labelMode === "simple" ? detail.simple_label || detail.predicted_class : detail.scientific_label || detail.predicted_class;
  const clusterName = labelMode === "simple" ? detail.plain_cluster_name || detail.cluster_name : detail.cluster_name;
  const summary = labelMode === "simple" ? detail.cluster_summary.plain_summary || detail.cluster_summary.summary : detail.cluster_summary.summary;

  return (
    <aside className="panel galaxy-drawer">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Selected galaxy</p>
          <h2>{detail.image_id}</h2>
        </div>
        <button className="ghost-button" type="button" onClick={onFindSimilar}>
          {similarModeActive ? "Spotlight on" : "Find similar galaxies"}
        </button>
      </div>

      <div className="galaxy-drawer__hero">
        <img src={detail.image_url} alt={detail.image_id} className="galaxy-drawer__image" />
        <div className="galaxy-detail-chip-stack">
          <span className="galaxy-badge">{title}</span>
          <span className="galaxy-badge galaxy-badge--muted">{clusterName}</span>
          <span className="galaxy-badge galaxy-badge--muted">{detail.metadata.filter_band}</span>
          {detail.rarity_score >= 0.82 ? <span className="galaxy-badge galaxy-badge--hot">Rare object</span> : null}
        </div>
      </div>

      <article className="galaxy-copy-card">
        <p className="eyebrow">Observation</p>
        <h3>{detail.metadata.source_field}</h3>
        <p>
          {detail.metadata.observation_program} using {detail.metadata.instrument} in {detail.metadata.filter_band}.
        </p>
      </article>

      <article className="galaxy-copy-card">
        <p className="eyebrow">AI-assisted explanation</p>
        <p className="galaxy-explanation">
          {loadingExplanation ? "Generating natural-language context..." : explanation || "No explanation available yet."}
        </p>
      </article>

      <article className="galaxy-copy-card">
        <p className="eyebrow">Morphology cluster</p>
        <h3>{clusterName}</h3>
        <p>{summary}</p>
        <dl className="galaxy-meta-grid">
          <div>
            <dt>Estimated redshift</dt>
            <dd>{formatValue(detail.metadata.redshift, 2)}</dd>
          </div>
          <div>
            <dt>Lookback time</dt>
            <dd>{formatValue(detail.metadata.lookback_time_gyr, 1)} Gyr</dd>
          </div>
          <div>
            <dt>Magnitude</dt>
            <dd>{formatValue(detail.metadata.magnitude, 2)}</dd>
          </div>
          <div>
            <dt>Cluster members</dt>
            <dd>{detail.cluster_summary.count.toLocaleString()}</dd>
          </div>
        </dl>
      </article>

      <article className="galaxy-copy-card">
        <p className="eyebrow">Metadata</p>
        <dl className="galaxy-meta-grid">
          <div>
            <dt>Catalog</dt>
            <dd>{detail.metadata.catalog}</dd>
          </div>
          <div>
            <dt>Observation source</dt>
            <dd>{detail.metadata.observation_source}</dd>
          </div>
          <div>
            <dt>RA / Dec</dt>
            <dd>
              {formatValue(detail.coordinates.ra, 3)} / {formatValue(detail.coordinates.dec, 3)}
            </dd>
          </div>
          <div>
            <dt>Surface brightness</dt>
            <dd>{formatValue(detail.metadata.surface_brightness, 2)}</dd>
          </div>
        </dl>
        <div className="galaxy-tag-row">
          {(detail.metadata.morphology_tags || []).map((tag) => (
            <span className="galaxy-tag" key={tag}>
              {tag}
            </span>
          ))}
        </div>
      </article>

      <article className="galaxy-copy-card">
        <p className="eyebrow">Embedding-nearest neighbors</p>
        <h3>Similar galaxies in map space</h3>
        <div className="galaxy-neighbor-stack">
          {(detail.nearest_neighbors || []).map((neighbor) => (
            <GalaxyCard key={neighbor.image_id} galaxy={neighbor} labelMode={labelMode} compact onSelect={onSelectGalaxy} />
          ))}
        </div>
      </article>
    </aside>
  );
}
