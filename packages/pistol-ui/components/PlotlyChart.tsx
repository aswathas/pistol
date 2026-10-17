"use client";

import { useEffect, useRef } from "react";

declare global {
  interface Window {
    Plotly?: any;
  }
}

export default function PlotlyChart({ spec }: { spec: any }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    const fig = spec?.plotly_fig ?? spec;
    const data = fig?.data ?? [];
    const layout = {
      ...(fig?.layout ?? {}),
      paper_bgcolor: "transparent",
      plot_bgcolor: "transparent",
      font: { color: "#ececf1", family: "Inter, system-ui, sans-serif", size: 11 },
      margin: { l: 50, r: 16, t: 36, b: 32 },
      xaxis: { gridcolor: "#26262e", zerolinecolor: "#26262e", ...(fig?.layout?.xaxis ?? {}) },
      yaxis: { gridcolor: "#26262e", zerolinecolor: "#26262e", ...(fig?.layout?.yaxis ?? {}) },
      hoverlabel: { bgcolor: "#13131a", bordercolor: "#26262e" },
    };
    const render = () => {
      if (window.Plotly) {
        window.Plotly.react(ref.current, data, layout, {
          displayModeBar: false,
          responsive: true,
        });
      }
    };
    if (window.Plotly) render();
    else {
      const t = setInterval(() => {
        if (window.Plotly) {
          clearInterval(t);
          render();
        }
      }, 80);
      return () => clearInterval(t);
    }
  }, [spec]);

  return <div ref={ref} className="w-full h-[380px]" />;
}
