"""Straight-line distances between block HQs (a proxy until road distances are added)."""
from __future__ import annotations

import math


def haversine_km(a: dict, b: dict) -> float:
    r = 6371.0
    p1, p2 = math.radians(a["lat"]), math.radians(b["lat"])
    dp, dl = p2 - p1, math.radians(b["lng"] - a["lng"])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def distance_matrix(blocks: list[dict]) -> dict:
    return {a["id"]: {b["id"]: round(haversine_km(a, b), 1) for b in blocks} for a in blocks}


def nearest_with_headroom(block: dict, blocks: list[dict], limit: int = 3) -> list[dict]:
    """Closest other blocks that have spare capacity, for redirecting produce."""
    spare = [b for b in blocks if b["id"] != block["id"] and b["gap_t"] > 0]
    spare.sort(key=lambda b: haversine_km(block, b))
    return [{"id": b["id"], "name": b["name"], "km": round(haversine_km(block, b), 1), "headroom_t": b["gap_t"]}
            for b in spare[:limit]]
