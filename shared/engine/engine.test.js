import test from 'node:test';
import assert from 'node:assert/strict';
import { PRODUCTION_SERIES, MONTHLY_INTAKE_PROFILE, MONTHLY_RELEASE_PROFILE, BLOCKS } from '../dataset.js';
import { linearRegression, forecastSeries, withYoY, nextSeason, cagr } from './analytics.js';
import { simulateStorageYear, storageDemand, facilityCoverage, blockStrain, strainLevel } from './storage.js';

const sum = (o) => Object.values(o).reduce((a, b) => a + b, 0);

test('dataset yields are consistent with production / area', () => {
  for (const r of PRODUCTION_SERIES) {
    assert.ok(Math.abs((r.productionT * 1000) / r.areaHa - r.yieldKgHa) < 1, r.season);
  }
});

test('assumption profiles and block shares each sum to 1', () => {
  assert.ok(Math.abs(sum(MONTHLY_INTAKE_PROFILE) - 1) < 1e-9);
  assert.ok(Math.abs(sum(MONTHLY_RELEASE_PROFILE) - 1) < 1e-9);
  assert.ok(Math.abs(BLOCKS.reduce((a, b) => a + b.productionShare, 0) - 1) < 1e-9);
  assert.ok(Math.abs(BLOCKS.reduce((a, b) => a + b.capacityShare, 0) - 1) < 1e-9);
});

test('linear regression recovers an exact line', () => {
  const m = linearRegression([0, 1, 2, 3], [5, 7, 9, 11]);
  assert.equal(m.slope, 2);
  assert.equal(m.intercept, 5);
  assert.equal(m.r2, 1);
});

test('production forecast for the next two seasons', () => {
  const { rows, models } = forecastSeries(PRODUCTION_SERIES, 2);
  assert.deepEqual(rows.map((r) => r.season), ['2024-25', '2025-26']);
  // OLS slope over 2018-19..2023-24 is ~28,686 t per season.
  assert.ok(Math.abs(models.productionT.slope - 28685.7) < 1);
  assert.ok(Math.abs(rows[0].productionT - 1400733) < 5);
  assert.ok(rows[0].productionLower < rows[0].productionT && rows[0].productionT < rows[0].productionUpper);
});

test('YoY, CAGR and season stepping', () => {
  const s = withYoY(PRODUCTION_SERIES);
  assert.equal(s[0].productionYoY, null);
  assert.ok(Math.abs(s.at(-1).productionYoY - 11000 / 1351000) < 1e-12);
  assert.equal(nextSeason('2023-24'), '2024-25');
  assert.equal(nextSeason('2098-99'), '2099-00');
  assert.ok(Math.abs(cagr(100, 121, 2) - 0.1) < 1e-12);
});

test('cold storage demand and coverage', () => {
  assert.equal(storageDemand(1362000, 0.75), 1021500);
  assert.equal(facilityCoverage(10215, 1021500), 0.01);
});

test('storage simulation flags a deficit when demand exceeds capacity', () => {
  const sim = simulateStorageYear({
    demandT: 1021500,
    capacityT: 900000,
    intakeProfile: MONTHLY_INTAKE_PROFILE,
    releaseProfile: MONTHLY_RELEASE_PROFILE,
  });
  assert.equal(sim.peakMonth, 'Apr');
  assert.ok(Math.abs(sim.totalOverflowT - 121500) < 1e-6);
  assert.deepEqual(sim.deficitMonths, ['Apr']);
  assert.equal(sim.status, 'critical');
  assert.ok(sim.months.every((m) => m.stock <= 900000 + 1e-6));
});

test('storage simulation with headroom has no deficit', () => {
  const sim = simulateStorageYear({
    demandT: 500000,
    capacityT: 900000,
    intakeProfile: MONTHLY_INTAKE_PROFILE,
    releaseProfile: MONTHLY_RELEASE_PROFILE,
  });
  assert.equal(sim.totalOverflowT, 0);
  assert.equal(sim.status, 'good');
  assert.ok(Math.abs(sim.months.at(-1).stock) < 1e-6);
});

test('block strain and level bands', () => {
  const rows = blockStrain(BLOCKS, { demandT: 1000, capacityT: 1000 });
  const sikandra = rows.find((r) => r.id === 'sikandra-rao');
  assert.ok(Math.abs(sikandra.utilisation - 0.18 / 0.13) < 1e-12);
  assert.equal(sikandra.level, 'critical');
  assert.equal(strainLevel(0.5), 'good');
  assert.equal(strainLevel(0.8), 'warning');
  assert.equal(strainLevel(0.95), 'serious');
});
