"""Terrain-costed traverse planner.

The router runs on a 10 m grid derived from the 200 m MOLA/HRSC DEM and the
CTX-texture roughness proxy. Hard no-go cells are impassable; everything else
gets a cost penalty.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter1d
from skimage.graph import route_through_array

from . import data, terrain
from .config import SUIT
from .terrain import NO_GO_COST


@dataclass
class RouteResult:
    station_ids: tuple[str, ...]
    speed_kmh: float
    lons: np.ndarray
    lats: np.ndarray
    stats: dict
    legs: list[dict] = field(default_factory=list)
    profile: dict = field(default_factory=dict)


@lru_cache(maxsize=1)
def _cost() -> np.ndarray:
    return terrain.cost_surface()


@lru_cache(maxsize=1)
def _nearest_valid_index() -> np.ndarray:
    """For every no-go cell, the (row, col) of the nearest traversable cell."""
    no_go = _cost() >= NO_GO_COST
    if not no_go.any():
        idx = np.indices(no_go.shape)
        return idx
    return distance_transform_edt(no_go, return_distances=False, return_indices=True)


def _valid_rc(lon: float, lat: float) -> tuple[int, int]:
    ny, nx = terrain.grid_shape()
    row, col = terrain.lonlat_to_rc(lon, lat)
    r = int(np.clip(round(float(row)), 0, ny - 1))
    c = int(np.clip(round(float(col)), 0, nx - 1))
    cost = _cost()
    if cost[r, c] >= NO_GO_COST:
        idx = _nearest_valid_index()
        r, c = int(idx[0, r, c]), int(idx[1, r, c])
    return r, c


def _smooth_rc(rows: np.ndarray, cols: np.ndarray, sigma: float = 1.6):
    if len(rows) < 5:
        return rows, cols
    sr = gaussian_filter1d(rows.astype(float), sigma=sigma, mode="nearest")
    sc = gaussian_filter1d(cols.astype(float), sigma=sigma, mode="nearest")
    sr[0], sc[0] = rows[0], cols[0]
    sr[-1], sc[-1] = rows[-1], cols[-1]
    return sr, sc


def _leg(lon1: float, lat1: float, lon2: float, lat2: float) -> dict:
    start = _valid_rc(lon1, lat1)
    end = _valid_rc(lon2, lat2)
    path, path_cost = route_through_array(
        _cost(), start, end, fully_connected=True, geometric=True,
    )
    rows = np.array([p[0] for p in path], dtype=float)
    cols = np.array([p[1] for p in path], dtype=float)

    srows, scols = _smooth_rc(rows, cols)
    lons, lats = terrain.rc_to_lonlat(srows, scols)

    # If smoothing pushed the line into a no-go cell, keep the raw grid path.
    sampled = terrain.sample_grid(data.slope(), lons, lats)
    rough = terrain.sample_grid(data.roughness(), lons, lats)
    bad = (
        np.nan_to_num(sampled, nan=0.0) > SUIT["slope_nogo_deg"]
    ) | (np.nan_to_num(rough, nan=0.0) > SUIT["rough_nogo"])
    if bad.any():
        lons, lats = terrain.rc_to_lonlat(rows, cols)

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


def _duration_h(profile: dict, speed_kmh: float) -> float:
    ds = profile["segment_m"]
    grade = profile["grade_deg"][: len(ds)]
    if len(ds) == 0:
        return 0.0
    uphill = np.maximum(grade, 0.0)
    mult = np.clip(1.0 + 0.06 * uphill, 1.0, 3.0)
    return float(np.sum((ds / 1000.0) / speed_kmh * mult))


def plan_route(station_ids: tuple[str, ...], speed_kmh: float = 1.5) -> RouteResult | None:
    start = data.station("START")
    if start is None:
        raise RuntimeError("START station missing from data/raw/stations.geojson")

    stops = []
    for sid in station_ids:
        st = data.station(sid)
        if st is None:
            raise KeyError(f"unknown station {sid}")
        stops.append(st)

    if not stops:
        return None

    lons: list[np.ndarray] = []
    lats: list[np.ndarray] = []
    legs: list[dict] = []
    prev = start
    for stop in stops + [start]:
        leg = _leg(prev["lon"], prev["lat"], stop["lon"], stop["lat"])
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
    stats = terrain.route_terrain_stats(prof)
    stats["duration_h"] = _duration_h(prof, speed_kmh)
    stats["speed_kmh"] = speed_kmh
    stats["cost"] = float(sum(leg["cost"] for leg in legs))
    stats["hazard_crossings"] = stats["hazard_samples"]

    if stats["hazard_crossings"] == 0:
        stats["verdict_note"] = "Route stays on traversable cells."
    else:
        stats["verdict_note"] = (
            f"Route crosses {stats['hazard_crossings']} no-go sample(s)."
        )

    return RouteResult(
        station_ids=tuple(s["id"] for s in stops),
        speed_kmh=speed_kmh,
        lons=all_lons,
        lats=all_lats,
        stats=stats,
        legs=legs,
        profile=prof,
    )


def route_geojson(route: RouteResult) -> dict:
    return {
        "type": "Feature",
        "properties": {
            "distance_km": round(route.stats["distance_km"], 3),
            "duration_h": round(route.stats["duration_h"], 3),
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
