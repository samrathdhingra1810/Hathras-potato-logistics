"""Rebuild the NHB Uttar Pradesh cold storage table from positioned PDF lines.

Source: https://www.nhb.gov.in/doc/UP.pdf (NHB capital investment subsidy scheme,
projects sanctioned 2000-2012; file last modified 2013-10-08).

Steps:
  swift tools/data/nhb_pdf_lines.swift UP.pdf lines.tsv
  python -I tools/data/parse_nhb_cold_storage.py lines.tsv out.csv

Rows are rebuilt by assigning each text line to the nearest serial number on the
page (vertically) and to a column by its x position. Values are copied as printed.
Problems are recorded in `flags`; nothing is corrected or filled in.
"""
import csv
import re
import sys
from collections import Counter, defaultdict
from datetime import date

COLS = [("name", 95, 310), ("category", 310, 375), ("address", 375, 500), ("district_raw", 500, 590),
        ("unit_type", 590, 680), ("bank", 680, 790), ("branch", 790, 910), ("sanctioned_raw", 910, 1045),
        ("capacity_mt_raw", 1045, 1140), ("project_cost_lakh", 1140, 1215), ("eligible_subsidy_lakh", 1215, 1295),
        ("advance_subsidy_lakh", 1295, 1385), ("final_subsidy_lakh", 1385, 1470), ("total_subsidy_lakh", 1470, 99999)]

# Spelling variants and the old district name only. Anything else is kept as printed.
DISTRICT_FIX = {
    "maha maya nagar": "Hathras", "mahamaya nagar": "Hathras", "mahamayan agar": "Hathras",
    "shahjahanp ur": "Shahjahanpur", "bulandshah ar": "Bulandshahr", "bulandsahar": "Bulandshahr",
    "buladshahar": "Bulandshahr", "raebareily": "Raebareli", "raibareilly": "Raebareli", "raebareilly": "Raebareli",
    "farukhabad": "Farrukhabad", "badaun": "Budaun",
}
MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                      "september", "october", "november", "december"], 1)}
# Hathras development blocks as they appear in addresses. "Hathras" itself is the
# district name too, so it never decides the block on its own.
BLOCK_WORDS = [("sikandra-rao", r"sikandra\s*rao"), ("sadabad", r"sadabad"), ("sasni", r"sasni"),
               ("sahpau", r"sah[a]?pau"), ("mursan", r"mur[s]?han|mursan"), ("hasayan", r"hasayan")]
YEARS = (1999, 2013)   # the scheme list covers sanctions from 2000 to 2012


def col(x):
    for n, a, b in COLS:
        if a <= x < b:
            return n


def parse_date(s):
    """(iso_date or '', year or '', problem or '')"""
    s = s.strip()
    if not s:
        return "", "", "date_missing"
    m = re.fullmatch(r"([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})", s)
    if m and m.group(1).lower() in MONTHS:
        y, mo, d = int(m.group(3)), MONTHS[m.group(1).lower()], int(m.group(2))
        if not YEARS[0] <= y <= YEARS[1]:
            return "", "", "date_implausible"
        return date(y, mo, d).isoformat(), y, ""
    m = re.fullmatch(r"(\d{1,2})[/.](\d{1,2})[/.](\d{2}|\d{4})", s)
    if m:
        a, b, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        y = y + 2000 if y < 100 else y
        if not YEARS[0] <= y <= YEARS[1]:
            return "", "", "date_implausible"
        if a == b:
            return date(y, a, b).isoformat(), y, ""          # same either way
        if a > 12 and b <= 12:
            return date(y, b, a).isoformat(), y, ""         # DD/MM
        if b > 12 and a <= 12:
            return date(y, a, b).isoformat(), y, ""         # MM/DD
        return "", y, "date_day_month_ambiguous"
    return "", "", "date_unreadable"


def block_hint(address, name):
    text = (address + " " + name).lower()
    hits = []
    for bid, pat in BLOCK_WORDS:
        for m in re.finditer(pat, text):
            if not re.match(r"\s*road", text[m.end():]):     # "Mursan Road, Sadabad" names a road, not a place
                hits.append(bid)
    hits = sorted(set(hits))
    return hits[0] if len(hits) == 1 else ""


def main(src, out):
    lines = []
    with open(src, newline="", encoding="utf-8") as f:
        r = csv.reader(f, delimiter="\t")
        next(r)
        for page, x, y, _w, text in r:
            lines.append((int(page), int(x), int(y), text))
    by_page = defaultdict(list)
    for l in lines:
        by_page[l[0]].append(l)
    rows = []
    for page in sorted(by_page):
        pl = by_page[page]
        anchors = [(y, int(m.group(1)), m.group(2), x) for _p, x, y, t in pl
                   if x < 100 and (m := re.match(r"^(\d{1,4})\b\s*(.*)$", t))]
        if not anchors:
            continue
        cells = {a[1]: defaultdict(list) for a in anchors}
        for a in anchors:
            if a[2]:
                cells[a[1]]["name"].append((a[0], a[3], a[2]))
        for _p, x, y, t in pl:
            if (x < 100 and re.match(r"^\d{1,4}\b", t)) or (page == 1 and y > 900):
                continue
            near = min(anchors, key=lambda a: abs(a[0] - y))
            if abs(near[0] - y) <= 40 and col(x):
                cells[near[1]][col(x)].append((y, x, t))
        for a in anchors:
            rec = {"sr": a[1], "pdf_page": page}
            for n, _, _ in COLS:
                rec[n] = " ".join(t for _, _, t in sorted(cells[a[1]].get(n, []), key=lambda v: (-v[0], v[1]))).strip()
            rows.append(rec)

    for r in rows:
        flags = []
        d = r["district_raw"]
        r["district"] = DISTRICT_FIX.get(d.lower(), d)
        if r["district"] != d:
            flags.append("district_name_normalised")
        iso, year, problem = parse_date(r["sanctioned_raw"])
        r["sanctioned_date"], r["sanctioned_year"] = iso, year
        if problem:
            flags.append(problem)
        cap = r["capacity_mt_raw"].replace(",", "")
        if not cap:
            r["capacity_mt"] = ""
            flags.append("capacity_missing")
        else:
            r["capacity_mt"] = float(cap)
            if not 100 <= r["capacity_mt"] <= 50000:     # single-store sanctions in this list are ~1,000-15,000 MT
                flags.append("capacity_implausible")
        r["block_hint"] = block_hint(r["address"], r["name"]) if r["district"] == "Hathras" else ""
        r["flags"] = flags
    key = Counter((re.sub(r"\W", "", r["name"].lower()), r["district"], r["capacity_mt_raw"]) for r in rows)
    names = Counter((re.sub(r"\W|^ms|pvt|ltd|p\b", "", r["name"].lower()), r["district"]) for r in rows)
    for r in rows:
        if key[(re.sub(r"\W", "", r["name"].lower()), r["district"], r["capacity_mt_raw"])] > 1:
            r["flags"].append("duplicate_row")
        if names[(re.sub(r"\W|^ms|pvt|ltd|p\b", "", r["name"].lower()), r["district"])] > 1:
            r["flags"].append("same_name_multiple_records")
        r["flags"] = ";".join(r["flags"])

    fields = ["sr", "pdf_page", "name", "category", "address", "district_raw", "district", "block_hint", "unit_type",
              "bank", "branch", "sanctioned_raw", "sanctioned_date", "sanctioned_year", "capacity_mt_raw", "capacity_mt",
              "project_cost_lakh", "eligible_subsidy_lakh", "advance_subsidy_lakh", "final_subsidy_lakh",
              "total_subsidy_lakh", "flags"]
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    srs = [r["sr"] for r in rows]
    fl = Counter(x for r in rows for x in r["flags"].split(";") if x)
    h = [r for r in rows if r["district"] == "Hathras"]
    print(f"rows {len(rows)} | serials 1..{max(srs)} | gaps {sorted(set(range(1, max(srs) + 1)) - set(srs))} | repeated {len(srs) - len(set(srs))}")
    print("flags:", dict(fl))
    print(f"Hathras rows {len(h)} | with block hint {sum(1 for r in h if r['block_hint'])} | flagged {sum(1 for r in h if r['flags'])}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
