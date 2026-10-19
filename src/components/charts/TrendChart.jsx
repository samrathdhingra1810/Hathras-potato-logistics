import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  LabelList,
} from 'recharts';
import { axisProps, gridProps, cursorProps, ChartTooltip, Legend } from './chartTheme.jsx';
import { fmtAxisTonnes, fmtHa, fmtNumber, fmtPct, fmtTonnes } from '../../services/format.js';

const dot = (color) => ({ r: 4, fill: color, stroke: 'var(--surface)', strokeWidth: 2 });
const activeDot = (color) => ({ r: 5, fill: color, stroke: 'var(--surface)', strokeWidth: 2 });

/** Area vs production on one axis by rebasing both to 2018-19 = 100 (no dual axis). */
export function IndexedAreaProductionChart({ data }) {
  const base = data[0];
  const rows = data.map((r) => ({
    ...r,
    areaIdx: (r.areaHa / base.areaHa) * 100,
    prodIdx: (r.productionT / base.productionT) * 100,
  }));
  const lastIdx = rows.length - 1;
  return (
    <div>
      <Legend
        items={[
          { label: 'Area cultivated (index)', color: 'var(--series-1)' },
          { label: 'Harvest output (index)', color: 'var(--series-2)' },
        ]}
      />
      <div className="mt-2 h-64">
        <ResponsiveContainer>
          <LineChart data={rows} margin={{ top: 16, right: 96, bottom: 0, left: -8 }}>
            <CartesianGrid {...gridProps} />
            <XAxis dataKey="season" {...axisProps} />
            <YAxis {...axisProps} domain={[98, 'auto']} tickFormatter={(v) => v.toFixed(0)} width={44} />
            <ReferenceLine y={100} stroke="var(--axis)" />
            <Tooltip
              cursor={cursorProps}
              content={
                <ChartTooltip
                  rows={(r) => [
                    { label: 'Area', value: fmtHa(r.areaHa), swatch: 'var(--series-1)' },
                    { label: 'Area index', value: r.areaIdx.toFixed(1) },
                    { label: 'Output', value: fmtTonnes(r.productionT, { compact: false }), swatch: 'var(--series-2)' },
                    { label: 'Output index', value: r.prodIdx.toFixed(1) },
                  ]}
                />
              }
            />
            <Line dataKey="areaIdx" stroke="var(--series-1)" strokeWidth={2} dot={dot('var(--series-1)')} activeDot={activeDot('var(--series-1)')} isAnimationActive>
              <LabelList
                dataKey="areaIdx"
                content={({ x, y, index, value }) =>
                  index === lastIdx ? (
                    <text x={x + 8} y={y + 4} fontSize={11} fill="var(--ink-2)">
                      Area {value.toFixed(1)}
                    </text>
                  ) : null
                }
              />
            </Line>
            <Line dataKey="prodIdx" stroke="var(--series-2)" strokeWidth={2} dot={dot('var(--series-2)')} activeDot={activeDot('var(--series-2)')}>
              <LabelList
                dataKey="prodIdx"
                content={({ x, y, index, value }) =>
                  index === lastIdx ? (
                    <text x={x + 8} y={y + 4} fontSize={11} fill="var(--ink-2)">
                      Output {value.toFixed(1)}
                    </text>
                  ) : null
                }
              />
            </Line>
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-1 text-[11px] text-ink-muted">2018-19 = 100. Output rising faster than area means yield gains.</p>
    </div>
  );
}

/** One measure per panel: used for the absolute-units small multiples. */
export function SingleMetricChart({ data, dataKey, color, format, axisFormat, label, height = 'h-44', reference }) {
  return (
    <div>
      <p className="text-xs font-medium text-ink-2">{label}</p>
      <div className={`mt-1 ${height}`}>
        <ResponsiveContainer>
          <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
            <CartesianGrid {...gridProps} />
            <XAxis dataKey="season" {...axisProps} />
            <YAxis {...axisProps} domain={['auto', 'auto']} tickFormatter={axisFormat} width={52} />
            {reference && (
              <ReferenceLine
                y={reference.value}
                stroke="var(--ink-muted)"
                strokeDasharray="4 4"
                label={{ value: reference.label, position: 'insideBottomRight', fill: 'var(--ink-muted)', fontSize: 10 }}
              />
            )}
            <Tooltip
              cursor={cursorProps}
              content={
                <ChartTooltip
                  rows={(r) => {
                    const yoyKey = { areaHa: 'areaYoY', productionT: 'productionYoY', yieldKgHa: 'yieldYoY' }[dataKey];
                    return [
                      { label, value: format(r[dataKey]), swatch: color },
                      { label: 'YoY', value: fmtPct(r[yoyKey], { signed: true }) },
                    ];
                  }}
                />
              }
            />
            <Line dataKey={dataKey} stroke={color} strokeWidth={2} dot={dot(color)} activeDot={activeDot(color)} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export const metricFormats = {
  areaHa: { format: fmtHa, axisFormat: (v) => `${(v / 1000).toFixed(1)}k` },
  productionT: { format: (v) => fmtTonnes(v, { compact: false }), axisFormat: fmtAxisTonnes },
  yieldKgHa: { format: (v) => `${fmtNumber(v)} kg/ha`, axisFormat: (v) => fmtNumber(v) },
};
