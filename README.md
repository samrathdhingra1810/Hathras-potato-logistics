# Hathras Potato Logistics

An open information portal for potato production and cold storage planning in Hathras district, Uttar Pradesh. Built with Python and Flask; charts use Chart.js and the map uses Leaflet (both loaded from cdnjs, so there is no build step).

## Run locally

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python run.py          # http://127.0.0.1:5000
.venv/bin/python -m unittest discover -s tests -t .
```

## Pages

| Path | Page |
|---|---|
| `/` | Home: hero snapshot, key numbers, tools, storage outlook, audiences |
| `/tools` | Tools overview with headline KPIs |
| `/tools/production` | Area vs output (indexed or absolute), yield trend, season table |
| `/tools/forecast` | OLS trend forecast for the next two seasons with a 95% interval |
| `/tools/planner` | Capacity planner: sliders, deficit alert, monthly stock chart (shareable URL) |
| `/tools/map` | Block strain map and ranking |
| `/data` | Dataset, assumptions, block shares, CSV download, API list |
| `/services`, `/about` | What the portal offers; methodology and data provenance |

## API

| Endpoint | Returns |
|---|---|
| `GET /api/baseline` | Series with YoY, blocks, assumptions |
| `GET /api/forecast?horizon=2` | Forecast rows (1–5 seasons) and model stats |
| `GET` or `POST /api/scenario` | `season, capacity, ratio, threshold, facility` → full storage simulation and block strain |
| `GET /data/production.csv` | District series as CSV |

## Layout

```
portal/__init__.py      Flask app, routes, API
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

## Deploy

`vercel.json` routes every request to the Flask app through `api/index.py`.

```bash
npx vercel deploy --prod
```
