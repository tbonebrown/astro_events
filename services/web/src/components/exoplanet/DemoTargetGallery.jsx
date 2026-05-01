export default function DemoTargetGallery({ targets = [], selectedTarget, onSelect }) {
  return (
    <section className="exoplanet-demo-strip" aria-label="Demo targets">
      {targets.map((target) => (
        <button
          className={`exoplanet-demo-card ${selectedTarget === target.name ? "is-active" : ""}`}
          key={target.target_id}
          onClick={() => onSelect(target)}
        >
          <span>{target.mission}</span>
          <strong>{target.name}</strong>
          <small>{target.known_planet || "Known target"}</small>
        </button>
      ))}
    </section>
  );
}
