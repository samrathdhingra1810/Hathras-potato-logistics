"""Extract the Hathras sheet from the Potato_Study workbook into a clean CSV.

Usage:
    .venv/bin/python -I tools/data/extract_hathras_yield.py "<path to Combined data sheets.xlsx>"

Writes portal/data/hathras_yield/hathras_yield_weather_indices.csv. Source values are
copied unchanged (full precision); only the header is cleaned ("\\nYield" -> "Yield")
and a `season` column is added from the paper's stated coverage (16 seasons,
2005-06 to 2020-21), mapping Time 1 -> 2005-06. That mapping is an inference: the
workbook itself stores only the 1..16 index.
"""
import csv
import hashlib
import os
import sys

from openpyxl import load_workbook

SHEET = "Hathrus"            # the workbook's (misspelled) sheet name for Hathras
FIRST_SEASON_START = 2005    # Time 1 = 2005-06 per the paper
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "portal", "data", "hathras_yield",
                   "hathras_yield_weather_indices.csv")


def season_for(time_index: int) -> str:
    start = FIRST_SEASON_START + time_index - 1
    return f"{start}-{(start + 1) % 100:02d}"


def main(path: str) -> None:
    with open(path, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    wb = load_workbook(path, read_only=True, data_only=True)
    rows = [r for r in wb[SHEET].iter_rows(values_only=True) if any(c is not None for c in r)]
    header = [str(h).strip() for h in rows[0]]
    if header[:2] != ["Yield", "Time"]:
        raise SystemExit(f"Unexpected header: {header[:4]}")
    out_header = ["season", "time_index", "yield_t_ha"] + header[2:]
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(out_header)
        for r in rows[1:]:
            t = int(r[1])
            w.writerow([season_for(t), t, repr(float(r[0]))] + [repr(float(v)) if isinstance(v, float) else v for v in r[2:]])
    print(f"wrote {len(rows) - 1} rows x {len(out_header)} cols to {os.path.normpath(OUT)}")
    print(f"source sha256 {digest}")


if __name__ == "__main__":
    main(sys.argv[1])
