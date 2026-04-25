import GalaxyCard from "./GalaxyCard";

export default function ClusterSummaryPanel({ clusters, activeClusterId, labelMode = "scientific", onSelectCluster, onSelectGalaxy }) {
  return (
    <section className="panel galaxy-cluster-summary">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Cluster mode</p>
          <h2>Visually similar galaxy families</h2>
        </div>
      </div>
      <div className="galaxy-cluster-grid">
        {clusters.map((cluster) => {
          const title = labelMode === "simple" ? cluster.plain_cluster_name || cluster.cluster_name : cluster.cluster_name;
          const summary = labelMode === "simple" ? cluster.plain_summary || cluster.summary : cluster.summary;
          return (
            <article className={`galaxy-cluster-card${activeClusterId === cluster.cluster_id ? " is-active" : ""}`} key={cluster.cluster_id}>
              <button className="galaxy-cluster-card__button" onClick={() => onSelectCluster(cluster.cluster_id)} type="button">
                <div>
                  <strong>{title}</strong>
                  <span>{cluster.count.toLocaleString()} galaxies</span>
                </div>
                <p>{summary}</p>
              </button>
              <div className="galaxy-cluster-card__reps">
                {cluster.representatives.slice(0, 3).map((galaxy) => (
                  <GalaxyCard
                    key={galaxy.image_id}
                    galaxy={galaxy}
                    labelMode={labelMode}
                    compact
                    onSelect={onSelectGalaxy}
                  />
                ))}
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
