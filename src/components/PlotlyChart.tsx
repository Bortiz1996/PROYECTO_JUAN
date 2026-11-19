import { useEffect, useRef } from "react";
import Plotly from "plotly.js-basic-dist-min";

interface PlotlyChartProps {
  data: Record<string, unknown>[];
  layout: Record<string, unknown>;
}

export function PlotlyChart({ data, layout }: PlotlyChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const mergedLayout: Record<string, unknown> = {
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "#ffffff",
      font: { family: "Arial, sans-serif", color: "#455d6b", size: 12 },
      showlegend: true,
      legend: {
        orientation: "h",
        x: 1,
        y: 1.02,
        xanchor: "right",
        yanchor: "bottom",
        font: { size: 11, color: "#455d6b" },
        bgcolor: "rgba(255,255,255,0.75)",
      },
      ...layout,
      xaxis: {
        gridcolor: "#e6ebee",
        gridwidth: 0.6,
        zeroline: false,
        showline: true,
        linecolor: "#aebbc2",
        linewidth: 0.8,
        ticks: "outside",
        tickcolor: "#aebbc2",
        tickwidth: 0.8,
        ticklen: 3,
        showticklabels: true,
        tickfont: { size: 11, color: "#455d6b" },
        automargin: true,
        ...((layout.xaxis as Record<string, unknown>) || {}),
      },
      yaxis: {
        gridcolor: "#e6ebee",
        gridwidth: 0.6,
        zeroline: false,
        showline: true,
        linecolor: "#aebbc2",
        linewidth: 0.8,
        ticks: "outside",
        tickcolor: "#aebbc2",
        tickwidth: 0.8,
        ticklen: 3,
        showticklabels: true,
        tickfont: { size: 11, color: "#455d6b" },
        automargin: true,
        ...((layout.yaxis as Record<string, unknown>) || {}),
      },
    };

    void Plotly.react(el, data, mergedLayout, {
      displayModeBar: false,
      responsive: true,
    });

    let ro: ResizeObserver | null = null;
    if (typeof ResizeObserver !== "undefined") {
      ro = new ResizeObserver(() => {
        if (containerRef.current) {
          Plotly.Plots.resize(containerRef.current);
        }
      });
      ro.observe(el);
    }

    return () => {
      if (ro) ro.disconnect();
    };
  }, [data, layout]);

  useEffect(() => {
    const el = containerRef.current;
    return () => {
      if (el) Plotly.purge(el);
    };
  }, []);

  return <div ref={containerRef} className="plotly-chart-box" />;
}
