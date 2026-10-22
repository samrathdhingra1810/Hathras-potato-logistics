# Uttar Pradesh district potato production, crop year 2022-23 (reference)

**Status:** secondary compilation, **unverified**. Shown on the production analytics page and at
`/api/sources/up-districts` for comparison only. It is **not** merged into ColdFlow's Hathras
series (`portal/core/dataset.py`) and is not used by any forecast, simulation or plan.

## Provenance

| Item | Value |
|---|---|
| Page | "Potato Production in Uttar Pradesh: All 75 Districts" |
| URL | https://indianpotato.com/uttar-pradesh-potato-production-district-wise/ |
| Publisher | Indian Potato (indianpotato.com); "Compiled by the Indian Potato Intelligence team" |
| Published / updated | 2026-08-06 / 2026-08-20 (page metadata) |
| Retrieved | 2026-10-22 (HTML SHA-256 `061bc0af3af850988b57b1ab9cc90b3568120c4b43aaf772f91b2ef9e1f01b55`) |
| Crop year | 2022-23 (stated on the page) |
| Original source | **Not named on the page.** Treat as unverified until matched to DES / UP Horticulture district releases. |
| Extraction | `tools/data/extract_up_district_potato.py` (values copied as published; only Indian digit grouping removed) |

## Columns and units

`crop_year`, `rank` (by production), `district`, `area_ha` (hectares), `production_t` (tonnes),
`yield_t_ha` (tonnes per hectare, as published, 1 decimal), `share_pct` (% of UP production, as published).

## Checks (`portal.core.external_sources.validate_districts`)

| Check | Result |
|---|---|
| Rows / unique districts / duplicates | 75 / 75 / 0 |
| Missing values | 0 |
| Total production | 24,292,433 t (page states "24.3 million tonnes") |
| Shares | sum to 100.04% (rounding in the published column) |
| Area × yield vs production | within 0.18% for every district |

## Discrepancy with ColdFlow (Hathras, 2022-23)

| | Area (ha) | Production (t) | Yield (t/ha) |
|---|---|---|---|
| ColdFlow district series | 54,800 | 1,351,000 | 24.65 |
| This compilation | 50,966 | 1,911,218 | 37.5 |
| Difference | −7.0% | **+41.5%** | **+52.1%** |

The gap is too large to be rounding or a different season label. Neither figure has been changed.
Possible causes: different source releases (provisional vs final), boundary/reclassification
effects the page itself warns about, or an error in either source. Resolve against official
district APY data before relying on either for decisions.

## Limitations

- One crop year only; no time series, so it cannot be used to forecast.
- District names follow the publisher (e.g. "Allahabad (Prayagraj)" style names are given as printed).
- Redistribution: the figures are factual statistics, but the page is a third-party publication;
  credit the source when reusing.
