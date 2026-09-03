// Собственные SVG-чарты: бар-чарт, линия, гистограмма. Без внешних библиотек.

export interface BarDatum {
  label: string;
  value: number;
  color?: string;
  hint?: string;
}

interface BarChartProps {
  data: BarDatum[];
  height?: number;
  formatValue?: (v: number) => string;
}

export function BarChart({ data, height = 180, formatValue = (v) => String(v) }: BarChartProps) {
  const max = Math.max(1, ...data.map((d) => d.value));
  const bw = 420 / data.length;
  return (
    <div className="chart">
      <svg viewBox={`0 0 ${data.length * bw + 40} ${height}`} width="100%" height={height} role="img">
        {data.map((d, i) => {
          const h = (d.value / max) * (height - 40);
          const x = 20 + i * bw + bw * 0.15;
          const y = height - 24 - h;
          return (
            <g key={i}>
              <rect
                x={x}
                y={y}
                width={bw * 0.7}
                height={Math.max(2, h)}
                rx={3}
                fill={d.color || 'var(--accent)'}
              >
                <title>{`${d.label}: ${formatValue(d.value)}`}</title>
              </rect>
              <text x={x + bw * 0.35} y={height - 8} className="chart-label" textAnchor="middle">
                {d.label}
              </text>
              <text x={x + bw * 0.35} y={Math.max(14, y - 4)} className="chart-value" textAnchor="middle">
                {formatValue(d.value)}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

export interface LinePoint {
  label: string;
  value: number;
}

interface LineChartProps {
  series: LinePoint[][];
  seriesNames?: string[];
  height?: number;
  formatValue?: (v: number) => string;
}

export function LineChart({ series, seriesNames = [], height = 180, formatValue = (v) => String(v) }: LineChartProps) {
  const all = series.flat();
  const max = Math.max(1, ...all.map((p) => p.value));
  const labels = series.length > 0 ? series[0].map((p) => p.label) : [];
  const n = Math.max(1, labels.length);
  const W = 460;
  const H = height;
  const padL = 36;
  const padB = 24;
  const padT = 12;
  const colors = ['var(--accent)', 'var(--yellow)', 'var(--green)'];
  const px = (i: number) => padL + (i / (n - 1)) * (W - padL - 10);
  const py = (v: number) => padT + (1 - v / max) * (H - padT - padB);

  return (
    <div className="chart">
      {seriesNames.length > 0 && (
        <div className="chart-legend">
          {seriesNames.map((name, i) => (
            <span key={name} className="chart-legend-item">
              <i style={{ background: colors[i % colors.length] }} /> {name}
            </span>
          ))}
        </div>
      )}
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={height} role="img">
        {Array.from({ length: 4 }, (_, i) => {
          const y = padT + (i / 3) * (H - padT - padB);
          return (
            <line key={i} x1={padL} y1={y} x2={W - 10} y2={y} className="chart-grid" />
          );
        })}
        {labels.map((lb, i) => (
          <text key={i} x={px(i)} y={H - 6} className="chart-label" textAnchor="middle">
            {lb}
          </text>
        ))}
        {series.map((points, si) => (
          <g key={si}>
            <polyline
              points={points.map((p, i) => `${px(i)},${py(p.value)}`).join(' ')}
              fill="none"
              stroke={colors[si % colors.length]}
              strokeWidth={2}
            />
            {points.map((p, i) => (
              <circle key={i} cx={px(i)} cy={py(p.value)} r={3} fill={colors[si % colors.length]}>
                <title>{`${p.label}: ${formatValue(p.value)}`}</title>
              </circle>
            ))}
          </g>
        ))}
      </svg>
    </div>
  );
}

// Гистограмма распределения (например, время до оплаты в днях).
export function HistogramChart({ data, height = 160, formatValue = (v) => String(v) }: BarChartProps) {
  return <BarChart data={data} height={height} formatValue={formatValue} />;
}