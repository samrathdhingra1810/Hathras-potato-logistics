import { Card } from '../components/ui/Card.jsx';
import { Slider } from '../components/ui/Slider.jsx';
import { Segmented } from '../components/ui/Segmented.jsx';
import { StatusBadge, AssumptionTag, LEVELS } from '../components/ui/StatusBadge.jsx';
import { StorageChart } from '../components/charts/StorageChart.jsx';
import { fmtNumber, fmtPct, fmtTonnes } from '../services/format.js';

function Alert({ sim, demandT, capacityT, alertThreshold, season }) {
  const level = sim.status;
  const l = LEVELS[level];
  let headline;
  let body;
  if (level === 'critical') {
    headline = `Storage deficit in ${sim.deficitMonths.join(', ')} (${season})`;
    body = `Peak-harvest intake exceeds capacity by ${fmtTonnes(sim.totalOverflowT)}. That volume has no cold-chain slot and must be sold at harvest, moved out of district, or held in ambient storage.`;
  } else if (level === 'serious') {
    headline = `Capacity strained in ${sim.alertMonths.join(', ')} (${season})`;
    body = `Peak stock reaches ${fmtPct(sim.peakUtilisation)} of capacity, above the ${fmtPct(alertThreshold, { digits: 0 })} alert threshold. Little headroom for a bumper crop or a late-sowing spike.`;
  } else if (level === 'warning') {
    headline = `Approaching threshold (${season})`;
    body = `Peak utilisation ${fmtPct(sim.peakUtilisation)} in ${sim.peakMonth}. Monitor arrivals through March.`;
  } else {
    headline = `Capacity adequate (${season})`;
    body = `Peak utilisation ${fmtPct(sim.peakUtilisation)} in ${sim.peakMonth}; ${fmtTonnes(capacityT - demandT)} of headroom at peak.`;
  }
  return (
    <div
      role={level === 'critical' || level === 'serious' ? 'alert' : 'status'}
      className="rounded-md border p-3"
      style={{ borderColor: l.color, background: `color-mix(in srgb, ${l.color} 9%, transparent)` }}
    >
      <div className="flex items-start gap-2">
        <span aria-hidden="true" className="mt-0.5 text-xs" style={{ color: l.color }}>
          {l.icon}
        </span>
        <div>
          <p className="text-sm font-semibold text-ink">{headline}</p>
          <p className="mt-0.5 text-xs text-ink-2">{body}</p>
        </div>
      </div>
    </div>
  );
}

export function StoragePlanner({
  seasonOptions,
  season,
  onSeason,
  productionT,
  storageRatio,
  onStorageRatio,
  regionalCapacityT,
  onRegionalCapacity,
  facilityCapacityT,
  onFacilityCapacity,
  alertThreshold,
  onAlertThreshold,
  demandT,
  sim,
}) {
  const coverage = facilityCapacityT / demandT;
  const regionalCoverage = regionalCapacityT / demandT;
  const facilitiesEquivalent = Math.max(demandT - regionalCapacityT, 0) / facilityCapacityT;

  return (
    <Card
      title="Cold storage logistics & capacity planner"
      subtitle="Stock-vs-capacity through the year for the selected season"
      actions={<Segmented label="Season" value={season} onChange={onSeason} options={seasonOptions} />}
    >
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <div className="space-y-4">
          <Slider
            label="Your facility holding capacity"
            value={facilityCapacityT}
            min={1000}
            max={60000}
            step={500}
            onChange={onFacilityCapacity}
            format={(v) => `${fmtNumber(v)} t`}
          />
          <Slider
            label="District cold storage capacity"
            value={regionalCapacityT}
            min={400000}
            max={1600000}
            step={10000}
            onChange={onRegionalCapacity}
            format={(v) => fmtTonnes(v)}
            hint="Default is a placeholder. Set it to the registered capacity from the UP Horticulture cold storage list."
          />
          <Slider
            label="Share of harvest stored"
            value={storageRatio}
            min={0.4}
            max={0.95}
            step={0.01}
            onChange={onStorageRatio}
            format={(v) => fmtPct(v, { digits: 0 })}
          />
          <Slider
            label="Alert threshold (utilisation)"
            value={alertThreshold}
            min={0.7}
            max={1}
            step={0.01}
            onChange={onAlertThreshold}
            format={(v) => fmtPct(v, { digits: 0 })}
          />
          <div className="flex flex-wrap gap-1.5">
            <AssumptionTag>Default capacity is an assumption</AssumptionTag>
            <AssumptionTag>Monthly intake profile is an assumption</AssumptionTag>
          </div>
        </div>

        <div className="space-y-3 lg:col-span-2">
          <Alert sim={sim} demandT={demandT} capacityT={regionalCapacityT} alertThreshold={alertThreshold} season={season} />

          <dl className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {[
              { k: 'Harvest', v: fmtTonnes(productionT), s: season },
              { k: 'Storage demand', v: fmtTonnes(demandT), s: `${fmtPct(storageRatio, { digits: 0 })} of harvest` },
              { k: 'Your facility covers', v: fmtPct(coverage, { digits: 2 }), s: 'of regional demand' },
              {
                k: 'District coverage',
                v: fmtPct(regionalCoverage, { digits: 1 }),
                s:
                  facilitiesEquivalent > 0
                    ? `gap ≈ ${fmtNumber(Math.ceil(facilitiesEquivalent))} facilities your size`
                    : 'demand fully covered',
              },
            ].map((x) => (
              <div key={x.k} className="rounded-md border border-line p-2.5">
                <dt className="text-[11px] text-ink-muted">{x.k}</dt>
                <dd className="tabular mt-0.5 text-base font-semibold text-ink">{x.v}</dd>
                <dd className="text-[11px] text-ink-2">{x.s}</dd>
              </div>
            ))}
          </dl>

          <StorageChart months={sim.months} capacityT={regionalCapacityT} alertThreshold={alertThreshold} />

          <div className="overflow-x-auto">
            <table className="tabular w-full min-w-[480px] text-xs">
              <thead className="text-ink-muted">
                <tr className="border-b border-line text-left">
                  <th className="py-1.5 font-medium">Peak month</th>
                  <th className="py-1.5 text-right font-medium">Intake</th>
                  <th className="py-1.5 text-right font-medium">Stock demanded</th>
                  <th className="py-1.5 text-right font-medium">Utilisation</th>
                  <th className="py-1.5 text-right font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {sim.months
                  .filter((m) => m.peakHarvest)
                  .map((m) => (
                    <tr key={m.month} className="border-b border-line last:border-0">
                      <td className="py-1.5 text-ink">{m.month}</td>
                      <td className="py-1.5 text-right text-ink">{fmtTonnes(m.intake)}</td>
                      <td className="py-1.5 text-right text-ink">{fmtTonnes(m.demandedStock)}</td>
                      <td className="py-1.5 text-right text-ink">{fmtPct(m.utilisation)}</td>
                      <td className="py-1.5 text-right">
                        <StatusBadge level={m.level} />
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </Card>
  );
}
