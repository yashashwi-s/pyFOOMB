/**
 * Shared Recharts theming so every chart in the app reads as one system.
 * Palette validated for CVD-safety and contrast against the app's dark
 * card surface (#18181b) with the dataviz-skill validator — assign colors
 * by fixed slot order (CHART_COLORS[i % n]), never re-cycle on filter.
 */
export const CHART_COLORS = [
  "#3987e5", // 1 blue
  "#d95926", // 2 orange
  "#199e70", // 3 aqua
  "#c98500", // 4 yellow
  "#d55181", // 5 magenta
  "#008300", // 6 green
  "#9085e9", // 7 violet
  "#e66767", // 8 red
];

export const CHART_GRID_STROKE = "#27272a";
export const CHART_AXIS_TICK = { fontSize: 10, fill: "#71717a" };
export const CHART_AXIS_LABEL_STYLE = { fontSize: 10, fill: "#71717a" };

export const CHART_TOOLTIP_STYLE: React.CSSProperties = {
  background: "#18181b",
  border: "1px solid #3f3f46",
  borderRadius: 8,
  fontSize: 11,
  padding: "8px 10px",
  boxShadow: "0 4px 16px rgba(0,0,0,0.4)",
};

export const CHART_TOOLTIP_LABEL_STYLE: React.CSSProperties = {
  color: "#fafafa",
  fontWeight: 500,
  marginBottom: 4,
};

export const CHART_TOOLTIP_ITEM_STYLE: React.CSSProperties = {
  color: "#d4d4d8",
};

export const CHART_LEGEND_STYLE: React.CSSProperties = {
  fontSize: 11,
  color: "#a1a1aa",
  paddingTop: 8,
};

/** Format a number for axis ticks / tooltips without excess precision. */
export function formatNumber(v: number | undefined | null): string {
  if (v == null || Number.isNaN(v)) return "—";
  if (v === 0) return "0";
  const abs = Math.abs(v);
  if (abs >= 1000 || abs < 0.001) return v.toExponential(2);
  if (abs >= 100) return v.toFixed(1);
  if (abs >= 1) return v.toFixed(2);
  return v.toFixed(4);
}
