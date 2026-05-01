import { useEffect, useRef, useState } from "react";

function PlotlyPanel({ eyebrow, title, traces, layout }) {
  const ref = useRef(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    let plotly = null;
    async function draw() {
      if (!ref.current || !traces?.length) {
        return;
      }
      try {
        const module = await import("plotly.js-dist-min");
        if (!active || !ref.current) {
          return;
        }
        plotly = module.default || module;
        await plotly.newPlot(ref.current, traces, layout, {
          responsive: true,
          displaylogo: false,
          modeBarButtonsToRemove: ["lasso2d", "select2d"]
        });
      } catch (drawError) {
        if (active) {
          setError(drawError.message || "Chart failed to render.");
        }
      }
    }
    draw();
    return () => {
      active = false;
      if (plotly && ref.current) {
        plotly.purge(ref.current);
      }
    };
  }, [traces, layout]);

  return (
    <article className="exoplanet-chart panel">
      <div className="exoplanet-chart__head">
        <p className="eyebrow">{eyebrow}</p>
        <h3>{title}</h3>
      </div>
      {error ? <p className="error-copy">{error}</p> : null}
      <div className="exoplanet-plot" ref={ref} />
    </article>
  );
}

const baseLayout = {
  paper_bgcolor: "rgba(0,0,0,0)",
  plot_bgcolor: "rgba(2,9,17,0.34)",
  font: { color: "#edf7ff", family: "Avenir Next, Segoe UI, sans-serif" },
  margin: { l: 54, r: 20, t: 18, b: 48 },
  xaxis: {
    gridcolor: "rgba(159,220,255,0.12)",
    zerolinecolor: "rgba(159,220,255,0.12)"
  },
  yaxis: {
    gridcolor: "rgba(159,220,255,0.12)",
    zerolinecolor: "rgba(159,220,255,0.12)"
  },
  hovermode: "closest"
};

export default function LightCurveChart({ series, title, eyebrow = "Photometry" }) {
  const traces = series
    ? [
        {
          x: series.time,
          y: series.flux,
          type: "scattergl",
          mode: "markers",
          name: series.label,
          marker: { color: "#8bddff", size: 3, opacity: 0.72 },
          hovertemplate: "Time %{x:.4f} d<br>Flux %{y:.6f}<extra></extra>"
        }
      ]
    : [];

  return (
    <PlotlyPanel
      eyebrow={eyebrow}
      title={title}
      traces={traces}
      layout={{
        ...baseLayout,
        xaxis: { ...baseLayout.xaxis, title: "Time [days]" },
        yaxis: { ...baseLayout.yaxis, title: "Relative flux" }
      }}
    />
  );
}

export { PlotlyPanel, baseLayout };
