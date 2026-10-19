export function KpiCard({ label, value, unit, delta, deltaLabel, foot }) {
  const deltaColor =
    delta == null ? 'var(--ink-2)' : delta > 0 ? 'var(--delta-up)' : delta < 0 ? 'var(--status-critical)' : 'var(--ink-2)';
  const arrow = delta == null ? '' : delta > 0 ? '▲' : delta < 0 ? '▼' : '■';
  return (
    <div className="rounded-lg border border-line bg-surface p-4">
      <p className="text-xs font-medium text-ink-2">{label}</p>
      <p className="mt-1.5 text-2xl font-semibold tracking-tight text-ink">
        {value}
        {unit && <span className="ml-1 text-sm font-medium text-ink-2">{unit}</span>}
      </p>
      {deltaLabel && (
        <p className="mt-1 text-xs font-medium" style={{ color: deltaColor }}>
          <span aria-hidden="true" className="mr-1 text-[10px]">
            {arrow}
          </span>
          {deltaLabel}
        </p>
      )}
      {foot && <p className="mt-1 text-xs text-ink-muted">{foot}</p>}
    </div>
  );
}
