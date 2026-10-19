"""Number formatting shared by templates (as Jinja filters) and the API."""
from __future__ import annotations

import math


def _ok(v) -> bool:
    return v is not None and isinstance(v, (int, float)) and math.isfinite(v)


def num(v, digits: int = 0) -> str:
    return f"{v:,.{digits}f}" if _ok(v) else "—"


def tonnes(v, compact: bool = True, digits: int = 2) -> str:
    if not _ok(v):
        return "—"
    if not compact:
        return f"{round(v):,} t"
    a = abs(v)
    if a >= 1e6:
        return f"{v / 1e6:.{digits}f}M t"
    if a >= 1e3:
        return f"{v / 1e3:.{0 if a >= 1e5 else 1}f}k t"
    return f"{round(v)} t"


def pct(v, digits: int = 1, signed: bool = False) -> str:
    if not _ok(v):
        return "—"
    sign = "+" if signed and v > 0 else ""
    return f"{sign}{v * 100:.{digits}f}%"


FILTERS = {"num": num, "tonnes": tonnes, "pct": pct}
