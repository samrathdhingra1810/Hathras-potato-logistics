# NHB cold storage projects sanctioned in Uttar Pradesh, 2000–2012 (historical reference)

**Status:** historical sanction records. Capacity is **as sanctioned under the NHB subsidy scheme**,
not current capacity, occupancy or available space. No contact details and nothing live.
Shown on the block map and at `/api/sources/nhb-cold-storage`. Not used by the storage model;
ColdFlow's district capacity (950,000 t) remains a labelled planning assumption.

## Provenance

| Item | Value |
|---|---|
| Document | NHB, "State: Uttar Pradesh" list of cold storage projects (capital investment subsidy) |
| URL | https://www.nhb.gov.in/doc/UP.pdf |
| Publisher | National Horticulture Board, Government of India |
| File date | HTTP `Last-Modified: 2013-10-08` |
| Retrieved | 2026-10-22 (PDF SHA-256 `7cc6be63fc57e1a7c3af5a687d7a8650fabec5cc9df7d68ff5659d37a30830ba`, 43 pages) |
| Period | sanction dates 2000 to 2012 |
| Extraction | `tools/data/nhb_pdf_lines.swift` (macOS PDFKit: every text line with its position) then `tools/data/parse_nhb_cold_storage.py` (rows rebuilt by serial number and column position) |

## Columns

As printed: `sr` (NHB serial), `pdf_page`, `name`, `category` (Gen/OBC/SC/ST), `address`, `district_raw`,
`unit_type` (New / Expansion / Modernisation …), `bank`, `branch`, `sanctioned_raw`, `capacity_mt_raw`
(metric tonnes), `project_cost_lakh` and subsidy columns (₹ lakh).
Added: `district` (spelling variants and the old name *Maha Maya Nagar* → Hathras; nothing else changed),
`sanctioned_date` (ISO, only when unambiguous), `sanctioned_year`, `capacity_mt` (number, blank if missing),
`block_hint` (Hathras only: the one development block named in the address, else blank), `flags`.

## Checks

| Check | Result |
|---|---|
| Rows | 920, serials 1–920 with no gaps or repeats |
| Hathras records | 58 (one printed as "Maha Maya Nagar", one as "Mahamayan agar") |
| Hathras block named in address | 27 (Sadabad 20, Sasni 4, Sahpau 2, Mursan 1); 31 not identified |
| Hathras sanctioned capacity | 328,217 MT over 55 records with a usable figure |
| Flags (all UP) | date missing 65 · capacity missing 56 · same name listed more than once 48 · day/month order unclear 18 · date unreadable 6 · duplicate row 6 · capacity implausible 2 · date implausible 2 |

Hathras records needing attention (kept as printed, not corrected):
#357 capacity printed **7,221,093 MT** (probably 7,221.093) · #562 date "22/01/207" ·
#913 date "January 4, 1902" · #756 and #793 no date or capacity · #163/#226 and other
New + Expansion pairs describe the same store, so capacities must not simply be added.

## Limitations

- Only projects that applied for and received NHB subsidy are listed; it is **not** a registry of all cold stores.
- Sanctioned capacity may differ from what was built, and stores may have expanded, closed or changed hands since.
- "Hathras" in an address is also the district name, so it never decides the block on its own; such records stay "Not identified".
- Block HQ map markers are approximate; individual stores have no coordinates in the source.
