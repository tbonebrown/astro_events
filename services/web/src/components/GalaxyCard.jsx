export default function GalaxyCard({ galaxy, labelMode = "scientific", onSelect, compact = false }) {
  if (!galaxy) {
    return null;
  }

  const title = labelMode === "simple" ? galaxy.simple_label || galaxy.predicted_class : galaxy.scientific_label || galaxy.predicted_class;
  const cluster = labelMode === "simple" ? galaxy.plain_cluster_name || galaxy.cluster_name : galaxy.cluster_name;

  return (
    <button
      className={`galaxy-card${compact ? " galaxy-card--compact" : ""}`}
      onClick={() => onSelect?.(galaxy.image_id)}
      type="button"
    >
      <img src={galaxy.image_url} alt={galaxy.image_id} className="galaxy-card__image" />
      <div className="galaxy-card__copy">
        <strong>{title}</strong>
        <span>{cluster}</span>
        {galaxy.redshift ? <span>z {Number(galaxy.redshift).toFixed(2)}</span> : null}
      </div>
    </button>
  );
}
