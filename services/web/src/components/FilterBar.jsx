const LABEL_MODES = [
  { value: "scientific", label: "Scientific labels" },
  { value: "simple", label: "Simplified labels" },
];

export default function FilterBar({
  manifest,
  filters,
  labelMode,
  onChange,
  onReset,
  onShare,
  onOpenStory,
}) {
  const ranges = manifest?.ranges;

  return (
    <section className="panel galaxy-filter-bar">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Explore the map</p>
          <h2>Filter by structure, distance, and observation program</h2>
        </div>
        <div className="galaxy-filter-bar__actions">
          <button className="ghost-button" type="button" onClick={onOpenStory}>
            Story mode
          </button>
          <button className="ghost-button" type="button" onClick={onShare}>
            Share view
          </button>
          <button className="ghost-button" type="button" onClick={onReset}>
            Reset
          </button>
        </div>
      </div>

      <div className="galaxy-filter-grid">
        <label className="galaxy-filter-control">
          <span>Search galaxy ID</span>
          <input value={filters.search} onChange={(event) => onChange("search", event.target.value)} placeholder="jwst-07-00012" />
        </label>

        <label className="galaxy-filter-control">
          <span>Cluster</span>
          <select value={filters.clusterId} onChange={(event) => onChange("clusterId", event.target.value)}>
            <option value="">All clusters</option>
            {manifest?.clusters?.map((cluster) => (
              <option key={cluster.cluster_id} value={String(cluster.cluster_id)}>
                {cluster.cluster_name}
              </option>
            ))}
          </select>
        </label>

        <label className="galaxy-filter-control">
          <span>Morphology</span>
          <select value={filters.morphology} onChange={(event) => onChange("morphology", event.target.value)}>
            <option value="">All morphologies</option>
            {manifest?.morphologies?.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>

        <label className="galaxy-filter-control">
          <span>Instrument</span>
          <select value={filters.instrument} onChange={(event) => onChange("instrument", event.target.value)}>
            <option value="">All instruments</option>
            {manifest?.instruments?.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>

        <label className="galaxy-filter-control">
          <span>Filter band</span>
          <select value={filters.filterBand} onChange={(event) => onChange("filterBand", event.target.value)}>
            <option value="">All bands</option>
            {manifest?.filter_bands?.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>

        <label className="galaxy-filter-control">
          <span>Source field</span>
          <select value={filters.sourceField} onChange={(event) => onChange("sourceField", event.target.value)}>
            <option value="">All fields</option>
            {manifest?.source_fields?.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>

        <label className="galaxy-filter-control">
          <span>Min redshift</span>
          <input
            type="number"
            min={ranges?.redshift_min ?? 0}
            max={ranges?.redshift_max ?? 20}
            step="0.1"
            value={filters.redshiftMin}
            onChange={(event) => onChange("redshiftMin", event.target.value)}
          />
        </label>

        <label className="galaxy-filter-control">
          <span>Max redshift</span>
          <input
            type="number"
            min={ranges?.redshift_min ?? 0}
            max={ranges?.redshift_max ?? 20}
            step="0.1"
            value={filters.redshiftMax}
            onChange={(event) => onChange("redshiftMax", event.target.value)}
          />
        </label>

        <label className="galaxy-filter-control">
          <span>Max magnitude</span>
          <input
            type="number"
            min={ranges?.magnitude_min ?? 20}
            max={ranges?.magnitude_max ?? 32}
            step="0.1"
            value={filters.magnitudeMax}
            onChange={(event) => onChange("magnitudeMax", event.target.value)}
          />
        </label>

        <div className="galaxy-filter-control">
          <span>Label mode</span>
          <div className="galaxy-toggle-row">
            {LABEL_MODES.map((mode) => (
              <button
                key={mode.value}
                className={`galaxy-toggle${labelMode === mode.value ? " is-active" : ""}`}
                onClick={() => onChange("labelMode", mode.value)}
                type="button"
              >
                {mode.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
