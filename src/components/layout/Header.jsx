const NAV = [
  { href: '#overview', label: 'Overview' },
  { href: '#analytics', label: 'Analytics' },
  { href: '#planner', label: 'Capacity planner' },
  { href: '#map', label: 'Block map' },
];

export function Header({ theme, onToggleTheme, origin, status }) {
  return (
    <header className="sticky top-0 z-[1000] border-b border-line bg-surface">
      <div className="mx-auto flex max-w-[1440px] flex-wrap items-center justify-between gap-3 px-4 py-2.5">
        <div className="flex min-w-0 items-center gap-3">
          <div
            aria-hidden="true"
            className="grid h-8 w-8 shrink-0 place-items-center rounded-md text-sm font-bold text-white"
            style={{ background: 'var(--series-1)' }}
          >
            HP
          </div>
          <div className="min-w-0">
            <h1 className="truncate text-sm font-semibold text-ink">Hathras Potato Logistics</h1>
            <p className="truncate text-[11px] text-ink-2">Cold storage optimization · Hathras district, Uttar Pradesh</p>
          </div>
        </div>
        <nav aria-label="Sections" className="order-3 flex w-full gap-1 overflow-x-auto text-xs md:order-none md:w-auto">
          {NAV.map((n) => (
            <a key={n.href} href={n.href} className="whitespace-nowrap rounded px-2.5 py-1 font-medium text-ink-2 hover:bg-line hover:text-ink">
              {n.label}
            </a>
          ))}
        </nav>
        <div className="flex items-center gap-2">
          {status}
          <span className="hidden text-[11px] text-ink-muted sm:inline" title="Where the baseline was loaded from">
            Data: {origin === 'api' ? 'API' : 'bundled'}
          </span>
          <button
            type="button"
            onClick={onToggleTheme}
            className="rounded-md border border-line px-2.5 py-1 text-xs font-medium text-ink-2 hover:bg-line hover:text-ink"
            aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
          >
            {theme === 'dark' ? '☀ Light' : '☾ Dark'}
          </button>
        </div>
      </div>
    </header>
  );
}
