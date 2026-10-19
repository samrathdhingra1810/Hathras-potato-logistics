import { useState } from 'react';
import { Card } from '../components/ui/Card.jsx';
import { Segmented } from '../components/ui/Segmented.jsx';
import { IndexedAreaProductionChart, SingleMetricChart, metricFormats } from '../components/charts/TrendChart.jsx';
import { ForecastChart } from '../components/charts/ForecastChart.jsx';
import { fmtAxisTonnes, fmtHa, fmtNumber, fmtPct, fmtTonnes } from '../services/format.js';

function SeriesTable({ series }) {
  return (
    <div className="overflow-x-auto">
      <table className="tabular w-full min-w-[520px] text-left text-xs">
        <thead className="text-ink-muted">
          <tr className="border-b border-line">
            <th className="py-1.5 pr-3 font-medium">Season</th>
            <th className="py-1.5 pr-3 text-right font-medium">Area (ha)</th>
            <th className="py-1.5 pr-3 text-right font-medium">Production (t)</th>
            <th className="py-1.5 pr-3 text-right font-medium">Yield (kg/ha)</th>
            <th className="py-1.5 text-right font-medium">Output YoY</th>
          </tr>
        </thead>
        <tbody className="text-ink">
          {series.map((r) => (
            <tr key={r.season} className="border-b border-line last:border-0">
              <td className="py-1.5 pr-3">{r.season}</td>
              <td className="py-1.5 pr-3 text-right">{fmtNumber(r.areaHa)}</td>
              <td className="py-1.5 pr-3 text-right">{fmtNumber(r.productionT)}</td>
              <td className="py-1.5 pr-3 text-right">{fmtNumber(r.yieldKgHa)}</td>
              <td className="py-1.5 text-right text-ink-2">{fmtPct(r.productionYoY, { signed: true, digits: 2 })}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ProductionAnalytics({ series, forecast, avgYieldKgHa }) {
  const [metric, setMetric] = useState('areaProd');
  const [scale, setScale] = useState('indexed');
  const [showTable, setShowTable] = useState(false);
  const [fcMetric, setFcMetric] = useState('production');

  const fc = forecast.rows;
  const fcCfg =
    fcMetric === 'production'
      ? {
          valueKey: 'productionT',
          lowerKey: 'productionLower',
          upperKey: 'productionUpper',
          format: (v) => fmtTonnes(v, { compact: false }),
          axisFormat: fmtAxisTonnes,
          label: 'Production',
          model: forecast.models.productionT,
          slopeLabel: (s) => `${fmtNumber(s)} t / season`,
        }
      : {
          valueKey: 'yieldKgHa',
          lowerKey: 'yieldLower',
          upperKey: 'yieldUpper',
          format: (v) => `${fmtNumber(v)} kg/ha`,
          axisFormat: (v) => fmtNumber(v),
          label: 'Yield',
          model: forecast.models.yieldKgHa,
          slopeLabel: (s) => `${fmtNumber(s)} kg/ha / season`,
        };

  return (
    <div className="grid grid-cols-1 gap-3 xl:grid-cols-5">
      <Card
        className="xl:col-span-3"
        title="Production & yield analytics"
        subtitle={`District time series, ${series[0].season} – ${series.at(-1).season}`}
        actions={
          <>
            <Segmented
              label="Metric"
              value={metric}
              onChange={setMetric}
              options={[
                { value: 'areaProd', label: 'Area vs output' },
                { value: 'yield', label: 'Yield' },
              ]}
            />
            {metric === 'areaProd' && (
              <Segmented
                label="Scale"
                value={scale}
                onChange={setScale}
                options={[
                  { value: 'indexed', label: 'Indexed' },
                  { value: 'absolute', label: 'Absolute' },
                ]}
              />
            )}
          </>
        }
      >
        {metric === 'areaProd' && scale === 'indexed' && <IndexedAreaProductionChart data={series} />}
        {metric === 'areaProd' && scale === 'absolute' && (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <SingleMetricChart data={series} dataKey="areaHa" color="var(--series-1)" label="Area cultivated (ha)" height="h-60" {...metricFormats.areaHa} />
            <SingleMetricChart data={series} dataKey="productionT" color="var(--series-2)" label="Harvest output (t)" height="h-60" {...metricFormats.productionT} />
          </div>
        )}
        {metric === 'yield' && (
          <SingleMetricChart
            data={series}
            dataKey="yieldKgHa"
            color="var(--series-1)"
            label="Yield (kg/ha)"
            height="h-64"
            reference={{ value: avgYieldKgHa, label: `6-season avg ${fmtNumber(avgYieldKgHa)}` }}
            {...metricFormats.yieldKgHa}
          />
        )}
        <div className="mt-3 border-t border-line pt-2">
          <button type="button" onClick={() => setShowTable((v) => !v)} className="text-xs font-medium text-ink-2 underline-offset-2 hover:text-ink hover:underline" aria-expanded={showTable}>
            {showTable ? 'Hide data table' : 'Show data table'}
          </button>
          {showTable && (
            <div className="mt-2">
              <SeriesTable series={series} />
            </div>
          )}
        </div>
      </Card>

      <Card
        className="xl:col-span-2"
        title="Production forecast"
        subtitle="OLS linear trend on season index, next two seasons"
        actions={
          <Segmented
            label="Forecast metric"
            value={fcMetric}
            onChange={setFcMetric}
            options={[
              { value: 'production', label: 'Production' },
              { value: 'yield', label: 'Yield' },
            ]}
          />
        }
      >
        <ForecastChart actuals={series} forecast={fc} {...fcCfg} />
        <table className="tabular mt-3 w-full text-xs">
          <thead className="text-ink-muted">
            <tr className="border-b border-line text-left">
              <th className="py-1.5 font-medium">Season</th>
              <th className="py-1.5 text-right font-medium">Point</th>
              <th className="py-1.5 text-right font-medium">95% interval</th>
            </tr>
          </thead>
          <tbody>
            {fc.map((r) => (
              <tr key={r.season} className="border-b border-line last:border-0">
                <td className="py-1.5 text-ink">{r.season}</td>
                <td className="py-1.5 text-right font-medium text-ink">{fcCfg.format(r[fcCfg.valueKey])}</td>
                <td className="py-1.5 text-right text-ink-2">
                  {fcCfg.axisFormat(r[fcCfg.lowerKey])} – {fcCfg.axisFormat(r[fcCfg.upperKey])}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <dl className="mt-3 grid grid-cols-3 gap-2 text-xs">
          <div>
            <dt className="text-ink-muted">Trend</dt>
            <dd className="tabular font-medium text-ink">+{fcCfg.slopeLabel(fcCfg.model.slope)}</dd>
          </div>
          <div>
            <dt className="text-ink-muted">R²</dt>
            <dd className="tabular font-medium text-ink">{fcCfg.model.r2.toFixed(3)}</dd>
          </div>
          <div>
            <dt className="text-ink-muted">Implied area 2025-26</dt>
            <dd className="tabular font-medium text-ink">{fmtHa(fc.at(-1).areaHa)}</dd>
          </div>
        </dl>
        <p className="mt-2 text-[11px] text-ink-muted">
          Six data points give a wide interval; treat the band, not the point, as the planning range.
        </p>
      </Card>
    </div>
  );
}
