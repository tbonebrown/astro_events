export default function StoryModeOverlay({ open, steps, onClose }) {
  if (!open) {
    return null;
  }

  return (
    <div className="story-overlay" role="dialog" aria-modal="true" aria-label="Story mode">
      <div className="story-overlay__backdrop" onClick={onClose} />
      <div className="story-overlay__panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Story mode</p>
            <h2>How to read the galaxy map</h2>
          </div>
          <button className="ghost-button" type="button" onClick={onClose}>
            Close
          </button>
        </div>
        <div className="story-overlay__steps">
          {steps.map((step, index) => (
            <article className="story-step" key={step.id}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              <div>
                <h3>{step.title}</h3>
                <p>{step.body}</p>
              </div>
            </article>
          ))}
        </div>
      </div>
    </div>
  );
}
