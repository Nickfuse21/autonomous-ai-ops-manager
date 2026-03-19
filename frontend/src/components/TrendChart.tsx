type TrendChartProps = {
  title: string;
  points: number[];
  colorClass?: "blue" | "green" | "red";
  valueSuffix?: string;
};

function buildPath(points: number[], width: number, height: number): string {
  if (points.length === 0) {
    return "";
  }
  const min = Math.min(...points);
  const max = Math.max(...points);
  const range = Math.max(max - min, 0.0001);
  const stepX = points.length > 1 ? width / (points.length - 1) : width;

  return points
    .map((point, idx) => {
      const x = idx * stepX;
      const y = height - ((point - min) / range) * height;
      return `${idx === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ");
}

export default function TrendChart({ title, points, colorClass = "blue", valueSuffix = "" }: TrendChartProps) {
  const latest = points.length > 0 ? points[points.length - 1] : null;
  const previous = points.length > 1 ? points[points.length - 2] : null;
  const delta = latest !== null && previous !== null ? latest - previous : null;
  const path = buildPath(points, 300, 90);

  return (
    <article className="glass-card section trend-card">
      <div className="trend-head">
        <h3 className="section-title">{title}</h3>
        <span className={`trend-delta ${delta !== null && delta >= 0 ? "trend-up" : "trend-down"}`}>
          {delta === null ? "n/a" : `${delta >= 0 ? "+" : ""}${delta.toFixed(3)}${valueSuffix}`}
        </span>
      </div>
      {points.length < 2 ? (
        <p className="section-desc">Need at least 2 data points.</p>
      ) : (
        <div className="trend-svg-wrap">
          <svg viewBox="0 0 300 90" className={`trend-line trend-${colorClass}`} role="img" aria-label={title}>
            <path d={path} fill="none" strokeWidth="3" />
          </svg>
        </div>
      )}
      <p className="section-desc">
        Latest: {latest === null ? "-" : `${latest.toFixed(3)}${valueSuffix}`} | Samples: {points.length}
      </p>
    </article>
  );
}
