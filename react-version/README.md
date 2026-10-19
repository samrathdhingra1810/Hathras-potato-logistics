# Hathras Potato Logistics & Cold Storage Optimization Dashboard

Production analytics and cold-storage capacity planning for potato in Hathras district, Uttar Pradesh.

- **Frontend:** React 18 + Vite 5, Tailwind CSS 3, Recharts, Leaflet (react-leaflet)
- **Backend:** Express API serving the baseline dataset, forecasts and storage simulations; serves the built client in production
- **Shared:** dataset and calculation engines in `shared/`, imported by both server and client

## Run

```bash
npm install
npm run dev        # API on :3001, Vite on :5173 (proxies /api)
npm test           # engine unit tests (node:test)
npm run build && npm start   # production: http://localhost:3001
```

Requires Node 18.18+.

## Modules

| Module | What it does |
|---|---|
| Executive overview | Latest production, cold storage demand (storage share × harvest), YoY growth, yield |
| Production & yield analytics | Area vs output (indexed to 2018-19 = 100, or absolute small multiples), yield trend, data table |
| Forecast | OLS linear trend per metric with a 95% prediction interval for 2024-25 and 2025-26 |
| Capacity planner | Facility and district capacity sliders, market-share coverage, monthly stock-vs-capacity simulation, Feb–Apr deficit alerts |
| Block map | Leaflet map centred on 27.5968° N, 78.0519° E with strain-coloured block markers |

## Data provenance

`shared/dataset.js` separates **supplied data** from **planning assumptions**:

| Item | Status |
|---|---|
| District area / production / yield, 2018-19 → 2023-24 | Supplied in the project brief. Cross-check against UP Directorate of Horticulture or DES district APY releases. |
| 75% share of harvest stored | From the brief; adjustable in the UI |
| District cold storage capacity (950,000 t default) | **Assumption.** Replace with the registered capacity. |
| Monthly intake (Feb 18% / Mar 57% / Apr 25%) and release (May–Nov) profiles | **Assumption** |
| Block production and capacity shares, block HQ coordinates | **Assumption / approximate** |

Assumptions are tagged in the UI so nobody mistakes them for measured figures.

## API

| Method | Path | Returns |
|---|---|---|
| GET | `/api/baseline` | District, series, blocks, default assumptions |
| GET | `/api/production` | Series with YoY changes |
| GET | `/api/forecast?horizon=2` | Forecast rows (1–5 seasons) and model stats |
| POST | `/api/storage/simulate` | `{ productionT, storageRatio, capacityT, alertThreshold }` → monthly simulation |

If the API is unreachable the client falls back to the bundled dataset, so `dist/` also works as a static site.

## Layout

```
server/index.js            Express API + static hosting
shared/dataset.js          Baseline data and assumptions
shared/engine/analytics.js YoY, CAGR, OLS regression, forecasting
shared/engine/storage.js   Demand, coverage, monthly stock simulation, block strain
src/services/              API client with fallback, number formatting
src/hooks/                 Theme and data loading
src/components/ui|charts|layout
src/views/                 Overview, ProductionAnalytics, StoragePlanner, GisView
```
