"""Extract the UP district potato table (crop year 2022-23) from a saved copy of
https://indianpotato.com/uttar-pradesh-potato-production-district-wise/

Usage:  python -I tools/data/extract_up_district_potato.py <saved.html> <out.csv>

Values are copied as published; only Indian digit grouping (e.g. 19,11,218) is
removed. The script checks the table against itself and prints the results; it
does not fix anything.
"""
import csv
import html
import re
import sys


def num(s):
    s = s.replace(",", "").strip()
    return float(s) if s else None


def main(src, out):
    page = open(src, encoding="utf-8", errors="replace").read()
    text = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", page)))
    crop_year = re.search(r"Crop year (\d{4}-\d{2})", text).group(1)
    published = re.search(r'article:published_time" content="([^"]+)"', page).group(1)[:10]
    modified = re.search(r'article:modified_time" content="([^"]+)"', page).group(1)[:10]
    tables = re.findall(r"<table.*?</table>", page, re.S | re.I)
    assert len(tables) == 1, "expected exactly one table"
    rows = []
    for tr in re.findall(r"<tr.*?</tr>", tables[0], re.S | re.I):
        cells = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", c))).strip()
                 for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", tr, re.S | re.I)]
        if cells and cells[0].isdigit():
            rows.append({"crop_year": crop_year, "rank": int(cells[0]), "district": cells[1],
                         "area_ha": num(cells[2]), "production_t": num(cells[3]),
                         "yield_t_ha": num(cells[4]), "share_pct": num(cells[5])})
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({k: (int(v) if isinstance(v, float) and v.is_integer() and k in ("area_ha", "production_t") else v)
                        for k, v in r.items()})
    total = sum(r["production_t"] for r in rows)
    worst = max(rows, key=lambda r: abs(r["area_ha"] * r["yield_t_ha"] - r["production_t"]) / r["production_t"])
    print(f"crop year {crop_year} | page published {published}, modified {modified}")
    print(f"rows {len(rows)} | districts unique {len({r['district'] for r in rows})} | ranks 1..{max(r['rank'] for r in rows)}")
    print(f"total production {total:,.0f} t | share sum {sum(r['share_pct'] for r in rows):.2f}%")
    print(f"worst area*yield vs production gap: {worst['district']} "
          f"{abs(worst['area_ha'] * worst['yield_t_ha'] - worst['production_t']) / worst['production_t']:.2%}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
