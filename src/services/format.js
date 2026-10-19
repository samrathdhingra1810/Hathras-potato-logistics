const IN = 'en-US';

/** 1362000 -> "1.36M t"; 21500 -> "21.5k t". */
export function fmtTonnes(t, { compact = true, digits = 2 } = {}) {
  if (t == null || !Number.isFinite(t)) return '—';
  if (!compact) return `${Math.round(t).toLocaleString(IN)} t`;
  const abs = Math.abs(t);
  if (abs >= 1e6) return `${(t / 1e6).toFixed(digits)}M t`;
  if (abs >= 1e3) return `${(t / 1e3).toFixed(abs >= 1e5 ? 0 : 1)}k t`;
  return `${Math.round(t)} t`;
}

export function fmtNumber(n, digits = 0) {
  if (n == null || !Number.isFinite(n)) return '—';
  return n.toLocaleString(IN, { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

export function fmtPct(r, { digits = 1, signed = false } = {}) {
  if (r == null || !Number.isFinite(r)) return '—';
  const s = (r * 100).toFixed(digits);
  return `${signed && r > 0 ? '+' : ''}${s}%`;
}

export function fmtHa(ha) {
  return `${fmtNumber(ha)} ha`;
}

export function fmtAxisTonnes(t) {
  if (Math.abs(t) >= 1e6) return `${(t / 1e6).toFixed(2)}M`;
  if (Math.abs(t) >= 1e3) return `${Math.round(t / 1e3)}k`;
  return String(Math.round(t));
}
