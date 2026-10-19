import express from 'express';
import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import {
  DISTRICT,
  PRODUCTION_SERIES,
  DATA_SOURCE,
  BLOCKS,
  DEFAULT_STORAGE_RATIO,
  DEFAULT_REGIONAL_CAPACITY_T,
  MONTHLY_INTAKE_PROFILE,
  MONTHLY_RELEASE_PROFILE,
} from '../shared/dataset.js';
import { forecastSeries, withYoY } from '../shared/engine/analytics.js';
import { simulateStorageYear, storageDemand } from '../shared/engine/storage.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = Number(process.env.PORT) || 3001;
const app = express();

app.disable('x-powered-by');
app.use(express.json());

app.get('/api/health', (_req, res) => res.json({ ok: true }));

// Everything the dashboard needs in one round trip.
app.get('/api/baseline', (_req, res) => {
  res.json({
    district: DISTRICT,
    source: DATA_SOURCE,
    series: PRODUCTION_SERIES,
    blocks: BLOCKS,
    assumptions: {
      storageRatio: DEFAULT_STORAGE_RATIO,
      regionalCapacityT: DEFAULT_REGIONAL_CAPACITY_T,
      intakeProfile: MONTHLY_INTAKE_PROFILE,
      releaseProfile: MONTHLY_RELEASE_PROFILE,
    },
  });
});

app.get('/api/production', (_req, res) => res.json(withYoY(PRODUCTION_SERIES)));

app.get('/api/forecast', (req, res) => {
  const horizon = Math.min(Math.max(Number(req.query.horizon) || 2, 1), 5);
  res.json(forecastSeries(PRODUCTION_SERIES, horizon));
});

// POST { productionT?, storageRatio?, capacityT?, alertThreshold? } -> storage simulation
app.post('/api/storage/simulate', (req, res) => {
  const body = req.body ?? {};
  const num = (v, fallback, min, max) => {
    const n = Number(v);
    return Number.isFinite(n) && n >= min && n <= max ? n : fallback;
  };
  const productionT = num(body.productionT, PRODUCTION_SERIES.at(-1).productionT, 0, 1e8);
  const storageRatio = num(body.storageRatio, DEFAULT_STORAGE_RATIO, 0, 1);
  const capacityT = num(body.capacityT, DEFAULT_REGIONAL_CAPACITY_T, 0, 1e8);
  const alertThreshold = num(body.alertThreshold, 0.9, 0.5, 1);
  const demandT = storageDemand(productionT, storageRatio);
  res.json({
    demandT,
    capacityT,
    ...simulateStorageYear({
      demandT,
      capacityT,
      alertThreshold,
      intakeProfile: MONTHLY_INTAKE_PROFILE,
      releaseProfile: MONTHLY_RELEASE_PROFILE,
    }),
  });
});

app.use('/api', (_req, res) => res.status(404).json({ error: 'Not found' }));

// In production, serve the built client from /dist.
const dist = path.resolve(__dirname, '../dist');
if (fs.existsSync(dist)) {
  app.use(express.static(dist));
  app.get('*', (_req, res) => res.sendFile(path.join(dist, 'index.html')));
}

app.listen(PORT, () => {
  console.log(`API listening on http://localhost:${PORT}`);
});
