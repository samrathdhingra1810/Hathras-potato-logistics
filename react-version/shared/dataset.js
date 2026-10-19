// Baseline dataset shared by the API server and the client-side fallback.
//
// PRODUCTION_SERIES holds the district-level figures supplied for this project.
// Everything else in this file (block split, coordinates, harvest calendar,
// storage defaults) is a planning ASSUMPTION and is flagged as such in the UI.
// Replace those with official block-level / registry data when available.

export const DISTRICT = {
  name: 'Hathras',
  state: 'Uttar Pradesh',
  center: { lat: 27.5968, lng: 78.0519 },
  crop: 'Potato',
};

export const PRODUCTION_SERIES = [
  { season: '2018-19', areaHa: 51200, productionT: 1218000, yieldKgHa: 23789 },
  { season: '2019-20', areaHa: 52450, productionT: 1261000, yieldKgHa: 24041 },
  { season: '2020-21', areaHa: 53100, productionT: 1298000, yieldKgHa: 24444 },
  { season: '2021-22', areaHa: 54000, productionT: 1312000, yieldKgHa: 24296 },
  { season: '2022-23', areaHa: 54800, productionT: 1351000, yieldKgHa: 24653 },
  { season: '2023-24', areaHa: 55200, productionT: 1362000, yieldKgHa: 24673 },
];

export const DATA_SOURCE = {
  label: 'District potato area & production, Hathras (UP), 2018-19 to 2023-24',
  note: 'Figures as supplied in the project brief. Cross-check against the UP Directorate of Horticulture / DES (Ministry of Agriculture) district APY releases before operational use.',
};

// Share of harvest that goes into cold storage (brief: 75%).
export const DEFAULT_STORAGE_RATIO = 0.75;

// ASSUMPTION: aggregate registered cold-storage capacity in the district (tonnes).
// Set this to the figure from the UP Horticulture cold storage registry.
export const DEFAULT_REGIONAL_CAPACITY_T = 950000;

// ASSUMPTION: share of the season's cold-storage intake that arrives in each month.
// Hathras potatoes are dug from late February through March; loading tails into April.
export const MONTHLY_INTAKE_PROFILE = {
  Jan: 0.0,
  Feb: 0.18,
  Mar: 0.57,
  Apr: 0.25,
};

// ASSUMPTION: share of stored stock released each month (May through November).
export const MONTHLY_RELEASE_PROFILE = {
  May: 0.08,
  Jun: 0.12,
  Jul: 0.15,
  Aug: 0.17,
  Sep: 0.18,
  Oct: 0.17,
  Nov: 0.13,
};

// ASSUMPTION: development blocks with approximate HQ coordinates and a modelled
// split of district production and cold-storage capacity. Each share column sums to 1.
export const BLOCKS = [
  { id: 'hathras', name: 'Hathras', lat: 27.5968, lng: 78.0519, productionShare: 0.2, capacityShare: 0.24 },
  { id: 'sasni', name: 'Sasni', lat: 27.703, lng: 78.084, productionShare: 0.17, capacityShare: 0.14 },
  { id: 'sikandra-rao', name: 'Sikandra Rao', lat: 27.6886, lng: 78.381, productionShare: 0.18, capacityShare: 0.13 },
  { id: 'sadabad', name: 'Sadabad', lat: 27.4386, lng: 78.0378, productionShare: 0.17, capacityShare: 0.17 },
  { id: 'mursan', name: 'Mursan', lat: 27.58, lng: 77.946, productionShare: 0.1, capacityShare: 0.12 },
  { id: 'sahpau', name: 'Sahpau', lat: 27.435, lng: 78.145, productionShare: 0.08, capacityShare: 0.1 },
  { id: 'hasayan', name: 'Hasayan', lat: 27.735, lng: 78.285, productionShare: 0.1, capacityShare: 0.1 },
];
