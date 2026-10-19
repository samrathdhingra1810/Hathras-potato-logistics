// Cold-storage demand, coverage and monthly stock-vs-capacity modelling.

export const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
export const PEAK_HARVEST_MONTHS = ['Feb', 'Mar', 'Apr'];

export function storageDemand(productionT, storageRatio) {
  return productionT * storageRatio;
}

/** Share of regional cold-storage demand that one facility's capacity covers. */
export function facilityCoverage(facilityCapacityT, demandT) {
  if (demandT <= 0) return 0;
  return facilityCapacityT / demandT;
}

/** Severity band for a utilisation ratio (demand or stock / capacity). */
export function strainLevel(utilisation, alertThreshold = 0.9) {
  if (utilisation > 1) return 'critical';
  if (utilisation >= alertThreshold) return 'serious';
  if (utilisation >= alertThreshold - 0.15) return 'warning';
  return 'good';
}

/**
 * Simulates stored stock through the calendar year.
 * Intake is spread by `intakeProfile`, releases by `releaseProfile`; stock that
 * would exceed capacity is recorded as overflow (produce with no cold-chain slot).
 */
export function simulateStorageYear({ demandT, capacityT, intakeProfile, releaseProfile, alertThreshold = 0.9 }) {
  let stock = 0; // constrained by capacity
  let unconstrained = 0; // what the season would hold with unlimited capacity
  let cumulativeOverflow = 0;
  const months = MONTHS.map((month) => {
    const intake = demandT * (intakeProfile[month] ?? 0);
    const room = Math.max(capacityT - stock, 0);
    const accepted = Math.min(intake, room);
    const overflow = intake - accepted;
    cumulativeOverflow += overflow;

    stock += accepted;
    unconstrained += intake;
    const peakStock = stock; // end of loading, before this month's releases
    const demandedStock = unconstrained;

    const scheduled = demandT * (releaseProfile[month] ?? 0);
    const release = Math.min(stock, scheduled);
    stock -= release;
    unconstrained -= Math.min(unconstrained, scheduled);

    const utilisation = capacityT > 0 ? demandedStock / capacityT : Infinity;
    return {
      month,
      intake,
      accepted,
      overflow,
      release,
      stock: peakStock,
      demandedStock,
      cumulativeOverflow,
      utilisation,
      level: strainLevel(utilisation, alertThreshold),
      peakHarvest: PEAK_HARVEST_MONTHS.includes(month),
    };
  });

  const peak = months.reduce((a, b) => (b.demandedStock > a.demandedStock ? b : a));
  const deficitMonths = months.filter((m) => m.overflow > 0);
  const alertMonths = months.filter((m) => m.peakHarvest && m.utilisation >= alertThreshold);

  return {
    months,
    peakMonth: peak.month,
    peakUtilisation: peak.utilisation,
    totalOverflowT: cumulativeOverflow,
    deficitMonths: deficitMonths.map((m) => m.month),
    alertMonths: alertMonths.map((m) => m.month),
    status: strainLevel(peak.utilisation, alertThreshold),
  };
}

/** Splits district demand and capacity across blocks and scores each block's strain. */
export function blockStrain(blocks, { demandT, capacityT, alertThreshold = 0.9 }) {
  return blocks.map((b) => {
    const blockDemand = demandT * b.productionShare;
    const blockCapacity = capacityT * b.capacityShare;
    const utilisation = blockCapacity > 0 ? blockDemand / blockCapacity : Infinity;
    return {
      ...b,
      demandT: blockDemand,
      capacityT: blockCapacity,
      gapT: blockCapacity - blockDemand,
      utilisation,
      level: strainLevel(utilisation, alertThreshold),
    };
  });
}
