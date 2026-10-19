// Status is never carried by color alone: each level has an icon glyph and a label.
export const LEVELS = {
  good: { label: 'Adequate', icon: '●', color: 'var(--status-good)' },
  warning: { label: 'Watch', icon: '▲', color: 'var(--status-warning)' },
  serious: { label: 'Strained', icon: '◆', color: 'var(--status-serious)' },
  critical: { label: 'Deficit', icon: '■', color: 'var(--status-critical)' },
};

export function StatusBadge({ level, label }) {
  const l = LEVELS[level] ?? LEVELS.good;
  return (
    <span
      className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border border-line px-2 py-0.5 text-xs font-medium text-ink"
      style={{ background: `color-mix(in srgb, ${l.color} 14%, transparent)` }}
    >
      <span aria-hidden="true" style={{ color: l.color }} className="text-[10px] leading-none">
        {l.icon}
      </span>
      {label ?? l.label}
    </span>
  );
}

export function AssumptionTag({ children = 'Assumption' }) {
  return (
    <span className="inline-flex items-center rounded border border-dashed border-line px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-ink-muted">
      {children}
    </span>
  );
}
