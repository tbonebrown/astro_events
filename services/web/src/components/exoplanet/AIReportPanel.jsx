export default function AIReportPanel({ report }) {
  if (!report) {
    return (
      <article className="panel exoplanet-report">
        <p className="eyebrow">AI report</p>
        <h2>Awaiting analysis</h2>
        <p>The explanation panel will populate after the numerical pipeline finishes.</p>
      </article>
    );
  }

  return (
    <article className="panel exoplanet-report">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">AI-assisted report</p>
          <h2>{report.title}</h2>
        </div>
        <span className="candidate-card__badge">{report.generated_by}</span>
      </div>
      <p className="exoplanet-safety">{report.safety_note}</p>
      <div className="exoplanet-report__sections">
        {report.sections.map((section) => (
          <section key={section.title}>
            <h3>{section.title}</h3>
            <p>{section.body}</p>
          </section>
        ))}
      </div>
    </article>
  );
}
