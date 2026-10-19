// Data access layer. Prefers the API; falls back to the bundled baseline so the
// dashboard still works as a static build (e.g. deployed without the server).
import * as baseline from '../../shared/dataset.js';

const localBaseline = () => ({
  district: baseline.DISTRICT,
  source: baseline.DATA_SOURCE,
  series: baseline.PRODUCTION_SERIES,
  blocks: baseline.BLOCKS,
  assumptions: {
    storageRatio: baseline.DEFAULT_STORAGE_RATIO,
    regionalCapacityT: baseline.DEFAULT_REGIONAL_CAPACITY_T,
    intakeProfile: baseline.MONTHLY_INTAKE_PROFILE,
    releaseProfile: baseline.MONTHLY_RELEASE_PROFILE,
  },
});

export async function fetchBaseline({ signal } = {}) {
  try {
    const res = await fetch('/api/baseline', { signal });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (!Array.isArray(data?.series) || data.series.length < 3) throw new Error('Malformed baseline');
    return { ...data, origin: 'api' };
  } catch (err) {
    if (err.name === 'AbortError') throw err;
    return { ...localBaseline(), origin: 'bundled' };
  }
}
