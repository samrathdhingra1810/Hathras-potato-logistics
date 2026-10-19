import { KpiCard } from '../components/ui/KpiCard.jsx';
import { fmtNumber, fmtPct } from '../services/format.js';

export function Overview({ series, storageRatio, cagr6, avgYieldKgHa }) {
  const latest = series.at(-1);
  const prev = series.at(-2);
  const demand = latest.productionT * storageRatio;
  const prevDemand = prev.productionT * storageRatio;

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <KpiCard
        label={`Total regional production · ${latest.season}`}
        value={(latest.productionT / 1e6).toFixed(3)}
        unit="M t"
        delta={latest.productionYoY}
        deltaLabel={`${fmtPct(latest.productionYoY, { signed: true, digits: 2 })} vs ${prev.season}`}
        foot={`${fmtNumber(latest.productionT)} tonnes harvested`}
      />
      <KpiCard
        label="Estimated cold storage demand"
        value={(demand / 1e6).toFixed(4)}
        unit="M t"
        delta={demand - prevDemand}
        deltaLabel={`${demand >= prevDemand ? '+' : '−'}${fmtNumber(Math.abs(demand - prevDemand))} t vs ${prev.season}`}
        foot={`${fmtNumber(demand)} t · ${fmtPct(storageRatio, { digits: 0 })} of harvest`}
      />
      <KpiCard
        label="Harvest growth rate (YoY)"
        value={fmtPct(latest.productionYoY, { digits: 2, signed: true })}
        delta={latest.productionYoY - prev.productionYoY}
        deltaLabel={`from ${fmtPct(prev.productionYoY, { digits: 2, signed: true })} in ${prev.season}`}
        foot={`${fmtPct(cagr6, { digits: 2 })} CAGR since ${series[0].season}`}
      />
      <KpiCard
        label={`Yield efficiency · ${latest.season}`}
        value={(latest.yieldKgHa / 1000).toFixed(2)}
        unit="t/ha"
        delta={latest.yieldYoY}
        deltaLabel={`${fmtPct(latest.yieldYoY, { signed: true, digits: 2 })} YoY`}
        foot={`${(avgYieldKgHa / 1000).toFixed(2)} t/ha six-season average`}
      />
    </div>
  );
}
