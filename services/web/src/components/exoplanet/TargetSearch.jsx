export default function TargetSearch({ form, loading, onChange, onSubmit }) {
  return (
    <form className="panel exoplanet-search" onSubmit={onSubmit}>
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Target search</p>
          <h2>Search real NASA light curves</h2>
        </div>
        <button className="ghost-button exoplanet-run-button" type="submit" disabled={loading}>
          {loading ? "Analyzing..." : "Run analysis"}
        </button>
      </div>
      <div className="exoplanet-search__grid">
        <label>
          <span>Target</span>
          <input
            value={form.target}
            onChange={(event) => onChange({ target: event.target.value })}
            placeholder="Kepler-10, TIC 150428135, KIC 11904151, RA Dec"
          />
        </label>
        <label>
          <span>Mission</span>
          <select value={form.mission} onChange={(event) => onChange({ mission: event.target.value })}>
            <option value="auto">Auto</option>
            <option value="Kepler">Kepler</option>
            <option value="TESS">TESS</option>
          </select>
        </label>
        <label>
          <span>Minimum period</span>
          <input
            type="number"
            min="0.1"
            step="0.1"
            value={form.period_min_days}
            onChange={(event) => onChange({ period_min_days: Number(event.target.value) })}
          />
        </label>
        <label>
          <span>Maximum period</span>
          <input
            type="number"
            min="0.2"
            step="0.5"
            value={form.period_max_days}
            onChange={(event) => onChange({ period_max_days: Number(event.target.value) })}
          />
        </label>
      </div>
    </form>
  );
}
