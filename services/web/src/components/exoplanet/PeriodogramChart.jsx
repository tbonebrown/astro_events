import { PlotlyPanel, baseLayout } from "./LightCurveChart";

export default function PeriodogramChart({ periodogram }) {
  const traces = periodogram
    ? [
        {
          x: periodogram.period,
          y: periodogram.power,
          type: "scatter",
          mode: "lines",
          name: "BLS power",
          line: { color: "#e9ff7a", width: 2 },
          hovertemplate: "Period %{x:.5f} d<br>Power %{y:.5f}<extra></extra>"
        },
        {
          x: [periodogram.best_period, periodogram.best_period],
          y: [0, Math.max(...periodogram.power, 0)],
          type: "scatter",
          mode: "lines",
          name: "Best period",
          line: { color: "#ff8f6b", width: 2, dash: "dot" },
          hoverinfo: "skip"
        }
      ]
    : [];

  return (
    <PlotlyPanel
      eyebrow="Search"
      title="Box Least Squares periodogram"
      traces={traces}
      layout={{
        ...baseLayout,
        xaxis: { ...baseLayout.xaxis, title: "Period [days]" },
        yaxis: { ...baseLayout.yaxis, title: "BLS power" }
      }}
    />
  );
}
