interface MttrChartProps {
  values: number[];
}

export function MttrChart({ values }: MttrChartProps) {
  const chartValues = values.length > 0 ? values : [90, 75, 40, 15, 3];
  const max = Math.max(...chartValues, 1);
  const width = 420;
  const height = 112;
  const points = chartValues
    .map((value, index) => {
      const x = chartValues.length === 1 ? width / 2 : (index / (chartValues.length - 1)) * width;
      const y = 12 + (1 - value / max) * (height - 32);
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <div className="mttr-chart" aria-label={`MTTR trend: ${chartValues.join(", ")} minutes`}>
      <div className="chart-heading">
        <div>
          <span className="eyebrow">Resolution velocity</span>
          <h3>Mean time to recovery</h3>
        </div>
        <strong>{values.length ? `${values.at(-1)} min` : "Awaiting data"}</strong>
      </div>
      <svg viewBox={`0 0 ${width} ${height}`} role="img">
        <defs>
          <linearGradient id="chart-fill" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0" stopColor="#35e6a5" stopOpacity="0.3" />
            <stop offset="1" stopColor="#35e6a5" stopOpacity="0" />
          </linearGradient>
        </defs>
        {[0, 1, 2].map((line) => (
          <line
            key={line}
            x1="0"
            x2={width}
            y1={16 + line * 36}
            y2={16 + line * 36}
            className="chart-grid"
          />
        ))}
        <polygon points={`0,${height} ${points} ${width},${height}`} fill="url(#chart-fill)" />
        <polyline points={points} className="chart-line" />
        {chartValues.map((value, index) => {
          const [x, y] = points.split(" ")[index].split(",");
          return (
            <g key={`${value}-${index}`}>
              <circle cx={x} cy={y} r="4" className="chart-dot" />
              <text x={x} y={Number(y) - 10} textAnchor="middle" className="chart-label">
                {value}m
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
