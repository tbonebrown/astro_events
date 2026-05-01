import { PlotlyPanel, baseLayout } from "./LightCurveChart";

export default function FoldedTransitChart({ folded }) {
  const traces = folded
    ? [
        {
          x: folded.phase,
          y: folded.flux,
          type: "scattergl",
          mode: "markers",
          name: "Folded flux",
          marker: { color: "#9fffb2", size: 3, opacity: 0.58 },
          hovertemplate: "Phase %{x:.4f}<br>Flux %{y:.6f}<extra></extra>"
        },
        {
          x: folded.model_phase,
          y: folded.model_flux,
          type: "scatter",
          mode: "lines",
          name: "Box transit model",
          line: { color: "#ff8f6b", width: 3 },
          hovertemplate: "Model phase %{x:.4f}<br>Flux %{y:.6f}<extra></extra>"
        }
      ]
    : [];

  return (
    <PlotlyPanel
      eyebrow="Validation"
      title="Phase-folded transit"
      traces={traces}
      layout={{
        ...baseLayout,
        xaxis: { ...baseLayout.xaxis, title: "Orbital phase" },
        yaxis: { ...baseLayout.yaxis, title: "Relative flux" }
      }}
    />
  );
}
