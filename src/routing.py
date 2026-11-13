"""Terrain-costed traverse planner, multi-mode optimizer, and abort/walk-back analyzer.

The router runs on a 10 m grid derived from the 200 m MOLA/HRSC DEM (interpolated
regional slope estimate) and the CTX Surface Texture Index (optical roughness proxy).
Hard no-go cells are impassable; Chaikin/Gaussian smoothed paths are densely verified
against the active cost surface so smoothed segments never cut across no-go cells.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter1d
from skimage.graph import route_through_array

from . import data, terrain
from .config import ROUTE_MODES, SUIT
from .terrain import NO_GO_COST


@dataclass
class RouteResult:
    station_ids: tuple[str, ...]
    speed_kmh: float
    lons: np.ndarray
    lats: np.ndarray
    stats: dict[str, Any]
    legs: list[dict[str, Any]] = field(default_factory=list)
    profile: dict[str, Any] = field(default_factory=dict)
    mode: str = "balanced"
    abort_points: list[dict[str, Any]] = field(default_factory=list)


def _hazard_signature(zones: list[dict[str, float]] | tuple[dict[str, float], ...] | None) -> tuple[tuple[float, float, float], ...]:
    if not zones:
        return ()
    return tuple(
        (
            round(float(z["lon"]), 6),
            round(float(z["lat"]), 6),
            round(float(z.get("radius_m", 150.0)), 1),
        )
        for z in zones
    )


@lru_cache(maxsize=16)
def _cached_cost_and_edt(
    mode: str = "balanced",
    slope_nogo_deg: float = SUIT["slope_nogo_deg"],
    slope_warn_deg: float = SUIT["slope_warn_deg"],
    rough_nogo: float = SUIT["rough_nogo"],
    hazard_sig: tuple[tuple[float, float, float], ...] = (),
) -> tuple[np.ndarray, np.ndarray]:
    """Build and cache (cost_surface, nearest_valid_index) keyed by all active parameters."""
    manual_mask = (
        terrain.build_hazard_mask(
            [{"lon": lon, "lat": lat, "radius_m": rad} for lon, lat, rad in hazard_sig]
        )
        if hazard_sig
        else None
    )
    cost = terrain.cost_surface(
        manual_hazard=manual_mask,
        mode=mode,
        slope_nogo_deg=slope_nogo_deg,
        slope_warn_deg=slope_warn_deg,
        rough_nogo=rough_nogo,
    )
    no_go = (cost >= NO_GO_COST) | ~np.isfinite(cost)
    if not no_go.any():
        idx = np.indices(no_go.shape)
    else:
        idx = distance_transform_edt(no_go, return_distances=False, return_indices=True)
    return cost, idx


def _cost() -> np.ndarray:
    """Default nominal cost surface helper (backwards compatible)."""
    cost, _ = _cached_cost_and_edt()
    return cost


def _valid_rc(
    lon: float,
    lat: float,
    cost: np.ndarray,
    edt_idx: np.ndarray,
) -> tuple[int, int]:
    ny, nx = cost.shape
    row, col = terrain.lonlat_to_rc(lon, lat)
    r = int(np.clip(round(float(row)), 0, ny - 1))
    c = int(np.clip(round(float(col)), 0, nx - 1))
    if cost[r, c] >= NO_GO_COST or not np.isfinite(cost[r, c]):
        r, c = int(edt_idx[0, r, c]), int(edt_idx[1, r, c])
    return r, c


def chaikin_smooth(rows: np.ndarray, cols: np.ndarray, iterations: int = 2) -> tuple[np.ndarray, np.ndarray]:
    """Chaikin corner-cutting subdivision followed by light Gaussian smoothing, preserving endpoints."""
    if len(rows) < 4:
        return rows.astype(float), cols.astype(float)
    pts = np.column_stack([rows.astype(float), cols.astype(float)])
    for _ in range(iterations):
        new_pts = [pts[0]]
        for i in range(len(pts) - 1):
            p0, p1 = pts[i], pts[i + 1]
            new_pts.append(0.75 * p0 + 0.25 * p1)
            new_pts.append(0.25 * p0 + 0.75 * p1)
        new_pts.append(pts[-1])
        pts = np.vstack(new_pts)
    t_old = np.linspace(0.0, 1.0, len(pts))
    t_new = np.linspace(0.0, 1.0, len(rows))
    sr = np.interp(t_new, t_old, pts[:, 0])
    sc = np.interp(t_new, t_old, pts[:, 1])
    sr = gaussian_filter1d(sr, sigma=1.2, mode="nearest")
    sc = gaussian_filter1d(sc, sigma=1.2, mode="nearest")
    sr[0], sc[0] = float(rows[0]), float(cols[0])
    sr[-1], sc[-1] = float(rows[-1]), float(cols[-1])
    return sr, sc


def _path_violates_nogo(
    rows: np.ndarray,
    cols: np.ndarray,
    cost: np.ndarray,
    slope_nogo_deg: float,
    rough_nogo: float,
) -> bool:
    """Densely inspect every sub-segment along (rows, cols) against cost_surface and no-go limits."""
    if len(rows) == 0:
        return False
    ny, nx = cost.shape

    if len(rows) > 1:
        dr = np.diff(rows)
        dc = np.diff(cols)
        seg_len = np.hypot(dr, dc)
        n_sub = max(int(np.ceil(np.sum(seg_len) * 4.0)), len(rows) * 3)
        t_orig = np.linspace(0.0, 1.0, len(rows))
        t_dense = np.linspace(0.0, 1.0, n_sub)
        r_dense = np.interp(t_dense, t_orig, rows)
        c_dense = np.interp(t_dense, t_orig, cols)
    else:
        r_dense = np.asarray(rows, dtype=float)
        c_dense = np.asarray(cols, dtype=float)

    r_int = np.clip(np.round(r_dense).astype(int), 0, ny - 1)
    c_int = np.clip(np.round(c_dense).astype(int), 0, nx - 1)
    cell_costs = cost[r_int, c_int]
    if np.any((cell_costs >= NO_GO_COST) | ~np.isfinite(cell_costs)):
        return True

    r_fl = np.clip(np.floor(r_dense).astype(int), 0, ny - 1)
    c_fl = np.clip(np.floor(c_dense).astype(int), 0, nx - 1)
    r_ce = np.clip(np.ceil(r_dense).astype(int), 0, ny - 1)
    c_ce = np.clip(np.ceil(c_dense).astype(int), 0, nx - 1)
    for rr, cc in ((r_fl, c_fl), (r_fl, c_ce), (r_ce, c_fl), (r_ce, c_ce)):
        c_val = cost[rr, cc]
        if np.any((c_val >= NO_GO_COST) | ~np.isfinite(c_val)):
            return True

    lons, lats = terrain.rc_to_lonlat(r_dense, c_dense)
    sampled_slope = terrain.sample_grid(data.slope(), lons, lats)
    sampled_rough = terrain.sample_grid(data.roughness(), lons, lats)
    if np.any(np.nan_to_num(sampled_slope, nan=0.0) > slope_nogo_deg):
        return True
    if np.any(np.nan_to_num(sampled_rough, nan=0.0) > rough_nogo):
        return True

    return False


def _leg(
    lon1: float,
    lat1: float,
    lon2: float,
    lat2: float,
    cost: np.ndarray,
    edt_idx: np.ndarray,
    slope_nogo_deg: float,
    rough_nogo: float,
) -> dict[str, Any]:
    start = _valid_rc(lon1, lat1, cost, edt_idx)
    end = _valid_rc(lon2, lat2, cost, edt_idx)

    work_cost = np.where(np.isfinite(cost), cost, NO_GO_COST).astype(np.float32)
    path, path_cost = route_through_array(
        work_cost, start, end, fully_connected=True, geometric=True,
    )
    rows = np.array([p[0] for p in path], dtype=float)
    cols = np.array([p[1] for p in path], dtype=float)

    srows, scols = chaikin_smooth(rows, cols)
    if _path_violates_nogo(srows, scols, cost, slope_nogo_deg, rough_nogo):
        lons, lats = terrain.rc_to_lonlat(rows, cols)
    else:
        lons, lats = terrain.rc_to_lonlat(srows, scols)

    prof = terrain.profile(lons, lats)
    length = terrain.path_length_km(lons, lats)
    slope = prof["slope_deg"]
    return {
        "from": (float(lon1), float(lat1)),
        "to": (float(lon2), float(lat2)),
        "lons": np.asarray(lons),
        "lats": np.asarray(lats),
        "distance_km": length,
        "cost": float(path_cost),
        "max_slope": float(np.nanmax(slope)) if len(slope) else 0.0,
        "bearing": terrain.bearing_deg(lon1, lat1, lon2, lat2),
        "profile": prof,
    }


def _duration_h(profile: dict[str, np.ndarray], speed_kmh: float) -> float:
    ds = profile["segment_m"]
    grade = profile["grade_deg"][: len(ds)]
    if len(ds) == 0:
        return 0.0
    uphill = np.maximum(grade, 0.0)
    mult = np.clip(1.0 + SUIT["climb_penalty_per_deg"] * uphill, 1.0, 3.0)
    return float(np.sum((ds / 1000.0) / max(speed_kmh, 0.1) * mult))


def compute_abort_points(
    lons: np.ndarray,
    lats: np.ndarray,
    speed_kmh: float,
    safe_stations: list[dict[str, Any]] | None = None,
    n_checkpoints: int = 8,
) -> list[dict[str, Any]]:
    """Compute Abort / Walk-back analysis from evenly spaced checkpoints along the traverse."""
    if len(lons) < 2:
        return []

    havens = safe_stations if safe_stations else [s for s in data.stations() if s["id"] == "START"]
    if not havens:
        havens = list(data.stations()[:1])

    indices = np.unique(np.linspace(0, len(lons) - 1, min(n_checkpoints, len(lons)), dtype=int))
    cum_d_m = np.concatenate([[0.0], np.cumsum(terrain.haversine_m(lons[:-1], lats[:-1], lons[1:], lats[1:]))])

    abort_list: list[dict[str, Any]] = []
    for idx in indices:
        lon_pt = float(lons[idx])
        lat_pt = float(lats[idx])
        traversed_km = float(cum_d_m[idx]) / 1000.0

        best_haven = havens[0]
        best_dist_m = float("inf")
        for h in havens:
            d_m = float(terrain.haversine_m(lon_pt, lat_pt, h["lon"], h["lat"]))
            eff_d_m = d_m * 1.15
            if eff_d_m < best_dist_m:
                best_dist_m = eff_d_m
                best_haven = h

        walkback_km = best_dist_m / 1000.0
        walkback_h = walkback_km / max(speed_kmh, 0.1)
        brg = terrain.bearing_deg(lon_pt, lat_pt, best_haven["lon"], best_haven["lat"])
        abort_list.append({
            "sample_index": int(idx),
            "lon": lon_pt,
            "lat": lat_pt,
            "traversed_km": round(traversed_km, 2),
            "nearest_haven_id": best_haven["id"],
            "nearest_haven_name": best_haven["name"],
            "walkback_km": round(walkback_km, 2),
            "walkback_h": round(walkback_h, 2),
            "walkback_o2_kg": round(walkback_h * SUIT["o2_rate_kg_h"], 3),
            "bearing_deg": round(brg, 1),
        })
    return abort_list


def plan_route(
    station_ids: tuple[str, ...] | list[str],
    speed_kmh: float = 1.5,
    mode: str = "balanced",
    slope_nogo_deg: float | None = None,
    slope_warn_deg: float | None = None,
    rough_nogo: float | None = None,
    hazard_zones: list[dict[str, float]] | tuple[dict[str, float], ...] | None = None,
) -> RouteResult | None:
    """Plan a complete round-trip EVA traverse from START through ``station_ids`` and back."""
    start = data.station("START")
    if start is None:
        raise RuntimeError("START station missing from data/raw/stations.geojson")

    stops: list[dict[str, Any]] = []
    for sid in station_ids:
        st = data.station(sid)
        if st is None:
            raise KeyError(f"unknown station {sid}")
        stops.append(st)

    if not stops:
        return None

    s_nogo = float(SUIT["slope_nogo_deg"] if slope_nogo_deg is None else slope_nogo_deg)
    s_warn = float(SUIT["slope_warn_deg"] if slope_warn_deg is None else slope_warn_deg)
    r_nogo = float(SUIT["rough_nogo"] if rough_nogo is None else rough_nogo)
    h_sig = _hazard_signature(hazard_zones)

    cost, edt_idx = _cached_cost_and_edt(
        mode=mode,
        slope_nogo_deg=s_nogo,
        slope_warn_deg=s_warn,
        rough_nogo=r_nogo,
        hazard_sig=h_sig,
    )
    manual_mask = (
        terrain.build_hazard_mask(
            [{"lon": lon, "lat": lat, "radius_m": rad} for lon, lat, rad in h_sig],
            shape=cost.shape,
        )
        if h_sig
        else None
    )

    mode_cfg = ROUTE_MODES.get(mode, ROUTE_MODES["balanced"])
    eff_speed_kmh = float(speed_kmh) * float(mode_cfg.get("speed_mult", 1.0))

    lons: list[np.ndarray] = []
    lats: list[np.ndarray] = []
    legs: list[dict[str, Any]] = []
    prev = start
    for stop in stops + [start]:
        leg = _leg(
            prev["lon"],
            prev["lat"],
            stop["lon"],
            stop["lat"],
            cost=cost,
            edt_idx=edt_idx,
            slope_nogo_deg=s_nogo,
            rough_nogo=r_nogo,
        )
        leg["from_id"] = prev["id"]
        leg["to_id"] = stop["id"]
        leg["duration_h"] = _duration_h(leg["profile"], eff_speed_kmh)
        legs.append(leg)
        if lons:
            lons.append(leg["lons"][1:])
            lats.append(leg["lats"][1:])
        else:
            lons.append(leg["lons"])
            lats.append(leg["lats"])
        prev = stop

    all_lons = np.concatenate(lons)
    all_lats = np.concatenate(lats)
    prof = terrain.profile(all_lons, all_lats)
    stats = terrain.route_terrain_stats(
        prof,
        slope_nogo_deg=s_nogo,
        slope_warn_deg=s_warn,
        rough_nogo=r_nogo,
        manual_hazard=manual_mask,
    )

    nom_duration = _duration_h(prof, eff_speed_kmh)
    unc_frac = float(SUIT["speed_unc_frac"])
    stats["duration_h"] = nom_duration
    stats["duration_min_h"] = round(nom_duration * (1.0 - unc_frac), 2)
    stats["duration_max_h"] = round(nom_duration * (1.0 + unc_frac * 1.25), 2)
    stats["speed_kmh"] = float(speed_kmh)
    stats["effective_speed_kmh"] = round(eff_speed_kmh, 2)
    stats["mode"] = mode
    stats["mode_label"] = mode_cfg["label_en"]
    stats["cost"] = float(sum(leg["cost"] for leg in legs))
    stats["hazard_crossings"] = stats["hazard_samples"]

    abort_pts = compute_abort_points(
        all_lons,
        all_lats,
        speed_kmh=eff_speed_kmh,
        safe_stations=[start],
    )
    max_walkback_h = max((p["walkback_h"] for p in abort_pts), default=0.0)
    max_walkback_km = max((p["walkback_km"] for p in abort_pts), default=0.0)
    stats["max_walkback_h"] = max_walkback_h
    stats["max_walkback_km"] = max_walkback_km

    if stats["hazard_crossings"] == 0:
        stats["verdict_note"] = "Route stays strictly on traversable cells."
    else:
        stats["verdict_note"] = (
            f"Route crosses {stats['hazard_crossings']} no-go sample(s)."
        )

    return RouteResult(
        station_ids=tuple(s["id"] for s in stops),
        speed_kmh=float(speed_kmh),
        lons=all_lons,
        lats=all_lats,
        stats=stats,
        legs=legs,
        profile=prof,
        mode=mode,
        abort_points=abort_pts,
    )


def compare_routes(
    station_ids: tuple[str, ...] | list[str],
    speed_kmh: float = 1.5,
    modes: tuple[str, ...] = ("fastest", "safest", "low_energy"),
    slope_nogo_deg: float | None = None,
    hazard_zones: list[dict[str, float]] | tuple[dict[str, float], ...] | None = None,
) -> dict[str, RouteResult]:
    """Compute multiple route modes side-by-side for Compare Mode."""
    out: dict[str, RouteResult] = {}
    for m in modes:
        res = plan_route(
            station_ids,
            speed_kmh=speed_kmh,
            mode=m,
            slope_nogo_deg=slope_nogo_deg,
            hazard_zones=hazard_zones,
        )
        if res is not None:
            out[m] = res
    return out


def route_geojson(route: RouteResult) -> dict[str, Any]:
    return {
        "type": "Feature",
        "properties": {
            "distance_km": round(route.stats["distance_km"], 3),
            "duration_h": round(route.stats["duration_h"], 3),
            "duration_range_h": [route.stats.get("duration_min_h"), route.stats.get("duration_max_h")],
            "mode": route.mode,
            "stations": list(route.station_ids),
        },
        "geometry": {
            "type": "LineString",
            "coordinates": [
                [round(float(x), 6), round(float(y), 6)]
                for x, y in zip(route.lons, route.lats)
            ],
        },
    }
