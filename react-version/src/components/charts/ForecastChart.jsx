import { Area, CartesianGrid, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { axisProps, gridProps, cursorProps, ChartTooltip, Legend } from './chartTheme.jsx';

/**
 * Actuals (solid) + OLS forecast (dashed) with a 95% prediction-interval band.
 * The forecast line starts at the last actual so the two segments join.
 */
export function ForecastChart({ actuals, forecast, valueKey, lowerKey, upperKey, format, axisFormat, label }) {
  const last = actuals[actuals.length - 1];
  const data = [
    ...actuals.map((r, i) => ({
      season: r.season,
      actual: r[valueKey],
      projected: i === actuals.length - 1 ? r[valueKey] : null,
      band: i === actuals.length - 1 ? [r[valueKey], r[valueKey]] : null,
    })),
    ...forecast.map((r) => ({
      season: r.season,
      actual: null,
      projected: r[valueKey],
      band: [r[lowerKey], r[upperKey]],
      lower: r[lowerKey],
      upper: r[upperKey],
      forecast: true,
    })),
  ];

  return (
    <div>
      <Legend
        items={[
          { label: `Actual ${label.toLowerCase()}`, color: 'var(--series-1)' },
          { label: 'Linear-trend forecast', color: 'var(--series-1)', dashed: true },
          { label: '95% prediction interval', color: 'var(--band-1)', kind: 'band' },
        ]}
      />
      <div className="mt-2 h-64">
        <ResponsiveContainer>
          <ComposedChart data={data} margin={{ top: 12, right: 20, bottom: 0, left: 0 }}>
            <CartesianGrid {...gridProps} />
            <XAxis dataKey="season" {...axisProps} />
            <YAxis {...axisProps} domain={['auto', 'auto']} tickFormatter={axisFormat} width={56} />
            <ReferenceLine
              x={last.season}
              stroke="var(--axis)"
              strokeDasharray="2 3"
              label={{ value: 'Forecast →', position: 'insideTopRight', fill: 'var(--ink-muted)', fontSize: 10 }}
            />
            <Tooltip
              cursor={cursorProps}
              content={
                <ChartTooltip
                  title={(r) => `${r.season}${r.forecast ? ' (forecast)' : ''}`}
                  rows={(r) =>
                    r.forecast
                      ? [
                          { label: 'Projected', value: format(r.projected), swatch: 'var(--series-1)', dashed: true },
                          { label: '95% low', value: format(r.lower) },
                          { label: '95% high', value: format(r.upper) },
                        ]
                      : [{ label: 'Actual', value: format(r.actual), swatch: 'var(--series-1)' }]
                  }
                />
              }
            />
            <Area dataKey="band" stroke="none" fill="var(--band-1)" isAnimationActive={false} activeDot={false} />
            <Line
              dataKey="actual"
              stroke="var(--series-1)"
              strokeWidth={2}
              dot={{ r: 4, fill: 'var(--series-1)', stroke: 'var(--surface)', strokeWidth: 2 }}
              connectNulls={false}
            />
            <Line
              dataKey="projected"
              stroke="var(--series-1)"
              strokeWidth={2}
              strokeDasharray="6 4"
              dot={{ r: 4, fill: 'var(--surface)', stroke: 'var(--series-1)', strokeWidth: 2 }}
              connectNulls={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
