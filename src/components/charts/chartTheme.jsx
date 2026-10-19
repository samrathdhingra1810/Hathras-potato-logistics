// Shared chart chrome: recessive axes/grid in theme tokens, and a themed tooltip.

export const axisProps = {
  stroke: 'var(--axis)',
  tick: { fill: 'var(--ink-muted)', fontSize: 11 },
  tickLine: false,
  axisLine: { stroke: 'var(--axis)' },
};

export const gridProps = {
  stroke: 'var(--line)',
  strokeDasharray: '0',
  vertical: false,
};

export const cursorProps = { stroke: 'var(--ink-muted)', strokeWidth: 1, strokeDasharray: '3 3' };

/**
 * rows: (payload) => [{ label, value, swatch?, dashed? }]
 * Text stays in ink tokens; the swatch beside it carries series identity.
 */
export function ChartTooltip({ active, payload, label, rows, title }) {
  if (!active || !payload?.length) return null;
  const items = rows(payload[0].payload, payload);
  return (
    <div className="min-w-[160px] rounded-md border border-line bg-surface px-3 py-2 text-xs shadow-lg">
      <p className="mb-1 font-semibold text-ink">{title ? title(payload[0].payload, label) : label}</p>
      <ul className="space-y-0.5">
        {items.map((r) => (
          <li key={r.label} className="flex items-center justify-between gap-4">
            <span className="flex items-center gap-1.5 text-ink-2">
              {r.swatch && (
                <span
                  aria-hidden="true"
                  className="inline-block h-0.5 w-3"
                  style={{
                    background: r.dashed ? 'none' : r.swatch,
                    borderTop: r.dashed ? `2px dashed ${r.swatch}` : 'none',
                    height: r.dashed ? 0 : 2,
                  }}
                />
              )}
              {r.label}
            </span>
            <span className="tabular font-medium text-ink">{r.value}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function Legend({ items }) {
  return (
    <ul className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-ink-2">
      {items.map((i) => (
        <li key={i.label} className="flex items-center gap-1.5">
          <span
            aria-hidden="true"
            className="inline-block w-4"
            style={
              i.kind === 'band'
                ? { height: 8, background: i.color, borderRadius: 2 }
                : i.kind === 'bar'
                  ? { height: 8, width: 8, background: i.color, borderRadius: 2 }
                  : { height: 0, borderTop: `2px ${i.dashed ? 'dashed' : 'solid'} ${i.color}` }
            }
          />
          {i.label}
        </li>
      ))}
    </ul>
  );
}
