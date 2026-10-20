# Hathras potato yield & weather indices (reference dataset)

**Status:** reference data for validation and analysis only. It is **not** used by ColdFlow's forecasts, planner, storage calculations or interface, and it is kept separate from the production series in `portal/core/dataset.py`.

## Provenance

| Item | Value |
|---|---|
| Source file | `Combined data sheets.xlsx` from GitHub repository `alsaberACS/Potato_Study` |
| Download URL | https://github.com/alsaberACS/Potato_Study/raw/refs/heads/main/Combined%20data%20sheets.xlsx |
| Downloaded | 2026-10-20 |
| Size / SHA-256 | 74,755 bytes / `1d55d1998083cf82a6539f7663e4320d5bce9ead418c17a2d3d0169a8592fb2c` |
| Sheet used | `Hathrus` (the workbook's spelling of Hathras). Other sheets: Agra, Aligarh, Etawah, Farukkabad, Firozabad, Kannauj |
| Associated paper | *Optimizing potato yield predictions in Uttar Pradesh, India: a comparative analysis of machine learning models*, Scientific Reports (2025), https://www.nature.com/articles/s41598-025-12719-8 (CC BY-NC-ND 4.0) |
| Original sources (per the paper) | Yield: Directorate of Economics and Statistics, Ministry of Agriculture and Farmers Welfare. Weather: NASA POWER, daily, 0.5° × 0.5° grid |
| Repository licence | **None declared** (no LICENSE or README in the repository). Redistribution terms are unclear; confirm with the authors before publishing this file or derived figures. |
| Extraction | `tools/data/extract_hathras_yield.py` (re-runnable on the original file) |

Values are copied unchanged at full precision. The only changes: the header `"\nYield"` is cleaned to `yield_t_ha`, `Time` is renamed `time_index`, and a `season` column is added.

## Year coverage

16 seasons, **2005-06 to 2020-21**. The workbook stores only `Time` = 1…16; the calendar mapping (Time 1 → 2005-06, …, Time 16 → 2020-21) is **inferred** from the paper's statement that the yield series covers "16 years (2005–06 to 2020–21)". The paper does not map the index explicitly.

## Columns

| Column | Meaning | Unit |
|---|---|---|
| `season` | Crop season (inferred from `time_index`, see above) | `YYYY-YY` |
| `time_index` | Original `Time` index from the workbook | 1…16 |
| `yield_t_ha` | District potato yield | **tonnes per hectare** (not total production) |
| `Z{i}0` | Unweighted weather index for variable *i*: Σ over season weeks of the weekly value X<sub>iw</sub> | sum of weekly values (unit of variable *i*) |
| `Z{i}1` | Weighted weather index: Σ<sub>w</sub> r<sub>iw</sub> · X<sub>iw</sub>, where r<sub>iw</sub> = correlation between detrended yield and variable *i* in week *w* | weighted sum; can be negative |
| `Z{i}{i'}0` | Unweighted interaction: Σ<sub>w</sub> X<sub>iw</sub> · X<sub>i'w</sub> | product of the two variables' units |
| `Z{i}{i'}1` | Weighted interaction: Σ<sub>w</sub> r<sub>ii'w</sub> · X<sub>iw</sub> · X<sub>i'w</sub> | weighted; can be negative |

Formulas and the meaning of the last digit (0 = unweighted, 1 = weighted) are from the paper's Methods. Weeks run from the first week of October (sowing) to the last week of January (harvest), as weekly averages of daily NASA POWER data.

**Variable numbers 1–6 are not defined in the workbook or the paper.** The paper lists the six variables as maximum temperature, minimum temperature, rainfall, relative humidity, wind speed and solar radiation. If the numbering follows that order, Z10 ≈ 415–502 and Z20 ≈ 178–238 are consistent with ~17 weekly values of maximum (~27 °C) and minimum (~13 °C) temperature, but this mapping is **unconfirmed**; do not label columns with variable names without the authors' confirmation.

## Validation (run `portal.core.yield_reference.validate`)

| Check | Result |
|---|---|
| Rows / columns | 16 / 45 |
| Missing cells | 0 |
| Duplicate seasons / duplicate rows | 0 / 0 |
| Season format and continuity | All `YYYY-YY`, consecutive 2005-06 → 2020-21 |
| Types | All numeric; some Z columns mix integers and decimals in the source (harmless) |
| Yield range | 21.06 – 32.95 t/ha (inside ColdFlow's 10–50 t/ha plausibility band) |
| Linear trend in yield | −0.14 t/ha per season over 2005-06 → 2020-21 |
| **Identical columns** | `Z460` = `Z560` and `Z461` = `Z561` in every row. These are interactions of different variable pairs (4×6 and 5×6), so they should differ; likely a spreadsheet copy error in the source. |
| Cross-district | `Z60` is identical for Hathras and Firozabad in every season (possibly a shared NASA POWER grid cell or a copy); no other unweighted column is shared with any other district |

## Comparison with ColdFlow's existing data (overlap 2018-19 → 2020-21)

ColdFlow's yield = production ÷ area from `portal/core/dataset.py`. **The two sources disagree substantially; neither has been changed.**

| Season | This dataset (t/ha) | ColdFlow (t/ha) | Difference |
|---|---|---|---|
| 2018-19 | 26.504 | 23.789 | +11.4% |
| 2019-20 | 30.284 | 24.042 | +26.0% |
| 2020-21 | 28.259 | 24.444 | +15.6% |

No alternative year alignment makes them agree (the closest single pair of values is 0.49 t/ha apart), so the gap is not just an off-by-one in the season mapping. Possible causes include different source releases (provisional vs final estimates), different district boundaries, or an error in either source. Resolve against the official DES / UP Horticulture figures before relying on either for decisions.

## Data-leakage assessment for the weighted indices

- The weights r<sub>iw</sub> are correlations between yield and weekly weather. The paper does not say whether they were computed on all 16 seasons or only the training seasons, and its 70/30 train/test split is not described as chronological.
- If the weights were computed on all seasons, every weighted index (`…1` columns) already contains information from the test seasons' yields. Any test-set accuracy built on them would be optimistic (**target leakage**).
- The workbook contains only the finished indices, not weekly weather data, so the weights can't be recomputed without leakage, and leakage can't be confirmed or ruled out from the file.
- Indirect check: if weights were fitted in-sample, weighted indices would usually correlate more strongly with detrended yield than unweighted ones. Here they do so in only 5 of 21 pairs, which is not the pattern in-sample fitting usually produces, but it is not proof either way.
- **Recommendation:** treat the `…1` (weighted) columns as potentially leaky. For any forecasting test, use the unweighted `…0` columns, or rebuild weighted indices inside each training window from raw NASA POWER weekly data.

## Limitations

- Yield only. There is no area or production data, so this dataset can't be converted into production tonnes or merged into ColdFlow's production series.
- 16 seasons is a short history for 42 weather features (more features than seasons); any model using many Z columns will overfit.
- The data ends in 2020-21; ColdFlow's series runs to 2023-24.
- No forecasting improvement from these features has been tested or is claimed.
