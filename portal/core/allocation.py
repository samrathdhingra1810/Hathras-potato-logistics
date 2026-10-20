"""Cost-aware storage redistribution as a linear program (SciPy / HiGHS).

Given supply points (where produce needing cold storage arises, tonnes) and storage
points (capacity, tonnes) with distances between them, decide how much produce from
each supply point goes to each store.

Two-stage (lexicographic) objective, solved exactly with two LPs:
  1. Maximise tonnes stored:          max Σ x_ij
  2. Among those plans, minimise haul: min Σ km_ij · x_ij   s.t. Σ x_ij ≥ stage-1 optimum
Constraints: Σ_j x_ij ≤ demand_i (can't ship more than you have),
             Σ_i x_ij ≤ capacity_j (stores can't overfill),
             x_ij = 0 when km_ij > max_km (optional haul limit), x ≥ 0.
Local storage (i = j) has zero haul.

This is a single-period model of the peak (the whole season's storage demand against
capacity). It needs only demand, capacity and distance. Freight cost is reported only
as tonne-km × a rate the user supplies; no cost figures are assumed.
"""
from __future__ import annotations

from .geo import haversine_km

TOL = 1e-6


def allocate(nodes: list[dict], *, max_km: float | None = None, road_factor: float = 1.0) -> dict:
    """nodes: [{id, name, lat, lng, demand_t, capacity_t}]. Returns flows and summary."""
    try:
        import numpy as np
        from scipy.optimize import linprog
    except ImportError:  # keep the rest of the app working without the solver
        return {"ok": False, "error": "The optimisation solver (SciPy) isn't installed on this server."}

    n = len(nodes)
    km = [[0.0 if i == j else haversine_km(nodes[i], nodes[j]) * road_factor for j in range(n)] for i in range(n)]
    pairs = [(i, j) for i in range(n) for j in range(n) if i == j or max_km is None or km[i][j] <= max_km]
    nv = len(pairs)
    demand = np.array([max(nd["demand_t"], 0.0) for nd in nodes])
    cap = np.array([max(nd["capacity_t"], 0.0) for nd in nodes])

    a_ub = np.zeros((2 * n, nv))
    for k, (i, j) in enumerate(pairs):
        a_ub[i, k] = 1.0        # supply row i
        a_ub[n + j, k] = 1.0    # capacity row j
    b_ub = np.concatenate([demand, cap])
    bounds = [(0, None)] * nv

    s1 = linprog(-np.ones(nv), A_ub=a_ub, b_ub=b_ub, bounds=bounds, method="highs")
    if s1.status != 0:
        return {"ok": False, "error": f"Solver could not find a plan ({s1.message})."}
    best_stored = -s1.fun

    cost = np.array([km[i][j] for i, j in pairs])
    a2 = np.vstack([a_ub, -np.ones((1, nv))])
    b2 = np.concatenate([b_ub, [-(best_stored - max(1e-9 * best_stored, TOL))]])
    s2 = linprog(cost, A_ub=a2, b_ub=b2, bounds=bounds, method="highs")
    if s2.status != 0:
        return {"ok": False, "error": f"Solver could not minimise haul ({s2.message})."}
    x = s2.x

    flows, out_of = [], [0.0] * n
    into = [0.0] * n
    for k, (i, j) in enumerate(pairs):
        t = float(x[k])
        if t <= 0.5:  # ignore sub-half-tonne numerical dust
            continue
        out_of[i] += t
        into[j] += t
        flows.append({"from": nodes[i]["id"], "from_name": nodes[i]["name"], "to": nodes[j]["id"],
                      "to_name": nodes[j]["name"], "tonnes": t, "km": km[i][j], "local": i == j})
    transfers = sorted([f for f in flows if not f["local"]], key=lambda f: -f["tonnes"])
    tonne_km = sum(f["tonnes"] * f["km"] for f in transfers)
    moved = sum(f["tonnes"] for f in transfers)
    local_only = float(sum(min(d, c) for d, c in zip(demand, cap)))
    per_node = [{
        "id": nd["id"], "name": nd["name"], "demand_t": float(demand[i]), "capacity_t": float(cap[i]),
        "stored_here_t": into[i], "shipped_t": out_of[i], "unstored_t": max(float(demand[i]) - out_of[i], 0.0),
        "free_capacity_t": max(float(cap[i]) - into[i], 0.0),
    } for i, nd in enumerate(nodes)]
    return {
        "ok": True,
        "solver": "HiGHS (scipy.optimize.linprog), two-stage lexicographic LP",
        "max_km": max_km, "road_factor": road_factor,
        "demand_t": float(demand.sum()), "capacity_t": float(cap.sum()),
        "stored_t": float(sum(out_of)), "unstored_t": float(demand.sum() - sum(out_of)),
        "local_only_stored_t": local_only, "gain_t": float(sum(out_of)) - local_only,
        "moved_t": moved, "tonne_km": tonne_km, "avg_haul_km": tonne_km / moved if moved else 0.0,
        "transfers": transfers, "nodes": per_node,
    }
