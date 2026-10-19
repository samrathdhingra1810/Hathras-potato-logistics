import { Bar, BarChart, CartesianGrid, ReferenceArea, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { axisProps, gridProps, ChartTooltip, Legend } from './chartTheme.jsx';
import { fmtAxisTonnes, fmtPct, fmtTonnes } from '../../services/format.js';

/** Monthly stock held vs capacity; overflow (no cold-chain slot) stacks on top. */
export function StorageChart({ months, capacityT, alertThreshold }) {
  const data = months.map((m) => ({ ...m, held: m.stock, unmet: m.overflow > 0 ? m.demandedStock - m.stock : 0 }));
  return (
    <div>
      <Legend
        items={[
          { label: 'Stock in cold storage', color: 'var(--series-1)', kind: 'bar' },
          { label: 'Unmet storage demand', color: 'var(--status-critical)', kind: 'bar' },
          { label: 'Capacity', color: 'var(--ink)' },
          { label: `Alert threshold (${fmtPct(alertThreshold, { digits: 0 })})`, color: 'var(--status-serious)', dashed: true },
        ]}
      />
      <div className="mt-2 h-64">
        <ResponsiveContainer>
          <BarChart data={data} margin={{ top: 12, right: 12, bottom: 0, left: 0 }} barCategoryGap="22%">
            <CartesianGrid {...gridProps} />
            <ReferenceArea x1="Feb" x2="Apr" fill="var(--line)" fillOpacity={0.5} label={{ value: 'Peak harvest', position: 'insideTop', fill: 'var(--ink-muted)', fontSize: 10 }} />
            <XAxis dataKey="month" {...axisProps} />
            <YAxis {...axisProps} tickFormatter={fmtAxisTonnes} width={52} />
            <Tooltip
              cursor={{ fill: 'var(--line)', fillOpacity: 0.4 }}
              content={
                <ChartTooltip
                  rows={(r) => [
                    { label: 'Intake', value: fmtTonnes(r.intake) },
                    { label: 'Release', value: fmtTonnes(r.release) },
                    { label: 'Stock held', value: fmtTonnes(r.held), swatch: 'var(--series-1)' },
                    ...(r.unmet > 0 ? [{ label: 'Unmet demand', value: fmtTonnes(r.unmet), swatch: 'var(--status-critical)' }] : []),
                    { label: 'Utilisation', value: fmtPct(r.utilisation) },
                  ]}
                />
              }
            />
            <Bar dataKey="held" stackId="s" fill="var(--series-1)" stroke="var(--surface)" strokeWidth={1} />
            <Bar dataKey="unmet" stackId="s" fill="var(--status-critical)" radius={[4, 4, 0, 0]} stroke="var(--surface)" strokeWidth={1} />
            <ReferenceLine y={capacityT} stroke="var(--ink)" strokeWidth={1.5} label={{ value: `Capacity ${fmtTonnes(capacityT)}`, position: 'insideTopRight', fill: 'var(--ink-2)', fontSize: 10 }} />
            <ReferenceLine y={capacityT * alertThreshold} stroke="var(--status-serious)" strokeDasharray="5 4" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
