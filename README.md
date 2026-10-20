# ColdFlow

Cold storage planning for every harvest. ColdFlow forecasts potato production, simulates cold storage stock against capacity month by month, and flags shortfalls, for the flagship Hathras district dataset or for your own data. Users can create accounts to save plans. Built with Python and Flask; charts use Chart.js and the map uses Leaflet (both loaded from cdnjs, so there is no build step).

## Run locally

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python run.py          # http://127.0.0.1:5000
.venv/bin/python -m unittest discover -s tests -t .   # 56 tests: engine, calculations trace, evaluation, allocation, app
```

## Pages

| Path | Page |
|---|---|
| `/` | ColdFlow landing page |
| `/plan` | Plan with your own data (editable seasons, CSV upload, calendar, share link, save) |
| `/signup`, `/login`, `/dashboard`, `/account` | Accounts, saved plans, profile/password/delete |
| `/hathras` | Hathras district overview |
| `/tools` | Tools overview with headline KPIs |
| `/tools/production` | Area vs output (indexed or absolute), yield trend, season table |
| `/tools/forecast` | OLS trend forecast for the next two seasons with a 95% interval |
| `/tools/planner` | Capacity planner: sliders, deficit alert, monthly stock chart (shareable URL) |
| `/tools/map` | Block strain map and ranking |
| `/data` | Dataset, assumptions, block shares, CSV download, API list |
| `/services`, `/about`, `/privacy`, `/terms` | Product, methodology, legal |

## API

| Endpoint | Returns |
|---|---|
| `GET /api/baseline` | Series with YoY, blocks, assumptions |
| `GET /api/forecast?horizon=2` | Forecast rows (1–5 seasons) and model stats |
| `GET` or `POST /api/scenario` | `season, capacity, ratio, threshold, facility` → full storage simulation and block strain |
| `POST /api/analyse` | Your own data → forecast, simulation and warnings (422 with `errors` if invalid) |
| `GET/POST /api/plans`, `PUT /api/plans/<id>` | Saved plans for the signed-in user (needs `X-CSRF-Token`) |
| `GET /api/allocation` | Redistribution plan for a Hathras scenario (`max_km`, `road_factor`, `rate`) |
| `POST /api/assistant` | `{messages, context}` → assistant reply (`mode`: `ai` or `offline`) |
| `GET /data/production.csv` | District series as CSV |

## Layout

```
portal/__init__.py      App factory, config, error handlers
portal/views_*.py       Pages, JSON API, accounts
portal/db.py            SQLite/Postgres access
portal/security.py      Sessions, CSRF, login_required
portal/core/custom.py   Validation + analysis for user data
portal/core/dataset.py  Supplied data and planning assumptions (edit here)
portal/core/analytics.py  YoY, CAGR, OLS forecast
portal/core/storage.py  Storage demand, monthly simulation, block strain
portal/templates/       Jinja pages (base, home, about, services, data, tools/*)
portal/static/          site.css, site.js, charts.js, planner.js, map.js
api/index.py            Vercel entry point
run.py                  Local dev server
tests/                  unittest suite for the core engine
react-version/          Earlier React/Vite dashboard, kept for reference
```

## Data provenance

The district area, production and yield series (2018-19 to 2023-24) is as supplied in the project brief; cross-check it against UP Directorate of Horticulture or DES releases. District cold storage capacity (950,000 t), the monthly intake and release profiles, and the block split are **planning assumptions**, labelled as such on the site.

## Forecast evaluation

`portal/core/evaluation.py` runs a rolling-origin (expanding-window) evaluation: from every origin with at least 3 training seasons, each model forecasts 1 and 2 seasons ahead using only earlier data. Models: linear trend (headline), damped Holt smoothing, and baselines (naive, drift, historical mean). Metrics: MAE, WAPE, bias (mean and % of actual), skill vs naive. Results are on `/tools/forecast#evaluation`, in the plan page for user data, in the Excel report (Evaluation sheet) and in the assistant's overview tool.

Current Hathras results (6 seasons, 3 one-season-ahead tests, computed by the code, labelled *indicative*): linear trend WAPE 1.22% with +1.22% bias (it over-forecast each recent season); damped smoothing 0.74%; drift 1.39%; naive 1.59%; mean 5.11%. Too few tests to switch the headline model; both forecasts are shown.

## Redistribution optimiser

`portal/core/allocation.py`: two-stage LP with SciPy/HiGHS (maximise tonnes stored, then minimise tonne-km), optional max haul and road factor; `GET /api/allocation`. Runs on the modelled block split and straight-line distances, so it is labelled a demo. Freight cost only with a user-supplied rate.

## Feature notes

- **Import / export:** Excel and CSV templates (`/templates/coldflow-template.xlsx|csv`), `POST /api/import` (CSV or XLSX, including a Settings sheet), `POST /api/export` (Excel report: summary, seasons, both forecasts, monthly storage, blocks, assumptions). PDF via the browser's print.
- **Forecasting:** linear trend plus damped exponential smoothing (Holt), compared on a two-season backtest. ARIMA is deliberately not used: six seasons is too little history.
- **What-ifs:** yield change, new capacity, electricity tariff change, and holding power cost (placeholder ₹7.5/kWh and 9 kWh per tonne-month; editable).
- **Block map:** diverging heatmap by month, click a block for monthly strain and nearest blocks with spare space (straight-line km), distance matrix.
- **Workspaces:** `/workspace/owner|fpo|admin`; signed-in users pick a role and see it on their dashboard.
- **Districts:** `portal/core/districts.py`; only Hathras is loaded. Add a district once you have verified figures.
- **Offline (PWA):** manifest + service worker (`/sw.js`) cache pages and assets; account pages are never cached.
- **Not connected yet (need real data sources):** other districts' baselines, cold storage facility registry, mandi prices, weather, bookings/inventory.

## AI assistant

The ✦ Ask ColdFlow panel (on every page, plus the home page's ask bar and ⌘K palette) calls `POST /api/assistant`. With `GEMINI_API_KEY` set as an environment variable, it uses Google Gemini (`gemini-3.8-flash`; override with `GEMINI_MODEL`) with three function tools that run ColdFlow's own engine: Hathras overview, Hathras what-if scenarios, and analysis of any seasons (including the plan on screen). Without a key it answers common questions from built-in rules and labels itself "Offline help". Requests are capped at 20 per 10 minutes per IP per server instance. Never commit the key; set it in Vercel → Settings → Environment Variables.

## Accounts in production

Locally, accounts use a SQLite file in `instance/`. On Vercel the filesystem doesn't persist, so accounts are **off** until both are set as Vercel environment variables:

- `DATABASE_URL`: a Postgres connection string (e.g. Neon via the Vercel Marketplace, or Supabase). Tables are created automatically.
- `SECRET_KEY`: a long random string that signs session cookies.

Until then, sign-up shows an "Accounts are coming soon" page and everything else works. Password reset by email is not built yet.

## Deploy

`vercel.json` routes every request to the Flask app through `api/index.py`.

```bash
npx vercel deploy --prod
```
