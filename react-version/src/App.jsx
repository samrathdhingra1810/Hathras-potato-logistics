import { useMemo, useState } from 'react';
import { useBaseline } from './hooks/useBaseline.js';
import { useTheme } from './hooks/useTheme.js';
import { Header } from './components/layout/Header.jsx';
import { StatusBadge } from './components/ui/StatusBadge.jsx';
import { Overview } from './views/Overview.jsx';
import { ProductionAnalytics } from './views/ProductionAnalytics.jsx';
import { StoragePlanner } from './views/StoragePlanner.jsx';
import { GisView } from './views/GisView.jsx';
import { withYoY, forecastSeries, cagr, mean } from '../shared/engine/analytics.js';
import { simulateStorageYear, storageDemand, blockStrain } from '../shared/engine/storage.js';

function Dashboard({ data, theme, toggle }) {
  const series = useMemo(() => withYoY(data.series), [data.series]);
  const forecast = useMemo(() => forecastSeries(data.series, 2), [data.series]);
  const avgYieldKgHa = useMemo(() => mean(data.series.map((r) => r.yieldKgHa)), [data.series]);
  const cagr6 = cagr(series[0].productionT, series.at(-1).productionT, series.length - 1);

  const latest = series.at(-1);
  const seasonOptions = [
    { value: latest.season, label: `${latest.season} actual` },
    ...forecast.rows.map((r) => ({ value: r.season, label: `${r.season} fcst` })),
  ];

  const [season, setSeason] = useState(latest.season);
  const [storageRatio, setStorageRatio] = useState(data.assumptions.storageRatio);
  const [regionalCapacityT, setRegionalCapacityT] = useState(data.assumptions.regionalCapacityT);
  const [facilityCapacityT, setFacilityCapacityT] = useState(10000);
  const [alertThreshold, setAlertThreshold] = useState(0.9);

  const productionT = season === latest.season ? latest.productionT : forecast.rows.find((r) => r.season === season).productionT;
  const demandT = storageDemand(productionT, storageRatio);

  const sim = useMemo(
    () =>
      simulateStorageYear({
        demandT,
        capacityT: regionalCapacityT,
        alertThreshold,
        intakeProfile: data.assumptions.intakeProfile,
        releaseProfile: data.assumptions.releaseProfile,
      }),
    [demandT, regionalCapacityT, alertThreshold, data.assumptions],
  );

  const blocks = useMemo(
    () => blockStrain(data.blocks, { demandT, capacityT: regionalCapacityT, alertThreshold }),
    [data.blocks, demandT, regionalCapacityT, alertThreshold],
  );

  return (
    <div className="min-h-screen bg-page">
      <Header
        theme={theme}
        onToggleTheme={toggle}
        origin={data.origin}
        status={<StatusBadge level={sim.status} label={`Peak ${Math.round(sim.peakUtilisation * 100)}% · ${season}`} />}
      />
      <main className="mx-auto max-w-[1440px] space-y-3 px-4 py-4">
        <div id="overview" className="scroll-mt-20">
          <Overview series={series} storageRatio={storageRatio} cagr6={cagr6} avgYieldKgHa={avgYieldKgHa} />
        </div>
        <div id="analytics" className="scroll-mt-20">
          <ProductionAnalytics series={series} forecast={forecast} avgYieldKgHa={avgYieldKgHa} />
        </div>
        <div id="planner" className="scroll-mt-20">
          <StoragePlanner
            seasonOptions={seasonOptions}
            season={season}
            onSeason={setSeason}
            productionT={productionT}
            storageRatio={storageRatio}
            onStorageRatio={setStorageRatio}
            regionalCapacityT={regionalCapacityT}
            onRegionalCapacity={setRegionalCapacityT}
            facilityCapacityT={facilityCapacityT}
            onFacilityCapacity={setFacilityCapacityT}
            alertThreshold={alertThreshold}
            onAlertThreshold={setAlertThreshold}
            demandT={demandT}
            sim={sim}
          />
        </div>
        <div id="map" className="scroll-mt-20">
          <GisView center={data.district.center} blocks={blocks} theme={theme} season={season} />
        </div>
        <footer className="pb-6 pt-2 text-[11px] leading-relaxed text-ink-muted">
          <p>
            <span className="font-medium text-ink-2">Source:</span> {data.source.label}. {data.source.note}
          </p>
          <p className="mt-1">
            Cold storage capacity, harvest-month intake profile and block-level split are planning assumptions, marked in
            the UI; edit them in <code>shared/dataset.js</code>.
          </p>
        </footer>
      </main>
    </div>
  );
}

export default function App() {
  const { theme, toggle } = useTheme();
  const { data, error, loading } = useBaseline();

  if (loading) {
    return <div className="grid min-h-screen place-items-center bg-page text-sm text-ink-2">Loading baseline…</div>;
  }
  if (error || !data) {
    return (
      <div className="grid min-h-screen place-items-center bg-page text-sm text-ink">
        Could not load the baseline dataset{error ? `: ${error.message}` : ''}.
      </div>
    );
  }
  return <Dashboard data={data} theme={theme} toggle={toggle} />;
}
