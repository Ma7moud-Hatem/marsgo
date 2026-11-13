"""Terrain grids: coordinate mapping, cost surface, and profile sampling."""

from __future__ import annotations

import math

import numpy as np

from . import data
from .config import BOX, MARS_RADIUS_M, SUIT

NO_GO_COST = 1.0e6


# --------------------------------------------------------------------------
# coordinate mapping
# --------------------------------------------------------------------------

def grid_shape() -> tuple[int, int]:
    return data.slope().shape


def lonlat_to_rc(lon, lat):
    ny, nx = grid_shape()
    lon = np.asarray(lon, dtype=float)
    lat = np.asarray(lat, dtype=float)
    col = (lon - BOX["w"]) / (BOX["e"] - BOX["w"]) * (nx - 1)
    row = (BOX["n"] - lat) / (BOX["n"] - BOX["s"]) * (ny - 1)
    return row, col


def rc_to_lonlat(row, col):
    ny, nx = grid_shape()
    row = np.asarray(row, dtype=float)
    col = np.asarray(col, dtype=float)
    lon = BOX["w"] + col / (nx - 1) * (BOX["e"] - BOX["w"])
    lat = BOX["n"] - row / (ny - 1) * (BOX["n"] - BOX["s"])
    return lon, lat


def sample_grid(grid: np.ndarray, lon, lat) -> np.ndarray:
    """Bilinear sample. Values outside the box return NaN."""
    ny, nx = grid.shape
    row, col = lonlat_to_rc(lon, lat)
    row = np.atleast_1d(row)
    col = np.atleast_1d(col)
    inside = (row >= 0) & (row <= ny - 1) & (col >= 0) & (col <= nx - 1)

    r = np.clip(row, 0, ny - 1)
    c = np.clip(col, 0, nx - 1)
    r0 = np.floor(r).astype(int)
    c0 = np.floor(c).astype(int)
    r1 = np.minimum(r0 + 1, ny - 1)
    c1 = np.minimum(c0 + 1, nx - 1)
    fr = r - r0
    fc = c - c0

    v = (
        grid[r0, c0] * (1 - fr) * (1 - fc)
        + grid[r0, c1] * (1 - fr) * fc
        + grid[r1, c0] * fr * (1 - fc)
        + grid[r1, c1] * fr * fc
    )
    v = np.where(inside, v, np.nan)
    return v


# --------------------------------------------------------------------------
# distance
# --------------------------------------------------------------------------

def haversine_m(lon1, lat1, lon2, lat2) -> np.ndarray:
    p1 = np.radians(np.asarray(lat1, dtype=float))
    p2 = np.radians(np.asarray(lat2, dtype=float))
    dp = p2 - p1
    dl = np.radians(np.asarray(lon2, dtype=float) - np.asarray(lon1, dtype=float))
    h = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * MARS_RADIUS_M * np.arcsin(np.minimum(1.0, np.sqrt(h)))


def path_length_km(lons, lats) -> float:
    if len(lons) < 2:
        return 0.0
    d = haversine_m(lons[:-1], lats[:-1], lons[1:], lats[1:])
    return float(np.sum(d)) / 1000.0


def bearing_deg(lon1, lat1, lon2, lat2) -> float:
    """Initial great-circle bearing, degrees clockwise from north."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dl) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(x, y)) + 360.0) % 360.0


# --------------------------------------------------------------------------
# cost surface
# --------------------------------------------------------------------------

def cost_surface(manual_hazard: np.ndarray | None = None) -> np.ndarray:
    slope = data.slope()
    rough = data.roughness()

    cost = 1.0
    cost = cost + 3.0 * np.clip(slope / 22.0, 0, 1)
    cost = cost + 2.5 * np.clip(rough, 0, 1)
    cost = cost + 6.0 * (slope > SUIT["slope_warn_deg"])

    no_go = (slope > SUIT["slope_nogo_deg"]) | (rough > SUIT["rough_nogo"])
    if manual_hazard is not None:
        no_go = no_go | manual_hazard
    cost = cost.astype(np.float32)
    cost[no_go] = NO_GO_COST
    return cost


def no_go_mask() -> np.ndarray:
    slope = data.slope()
    rough = data.roughness()
    return (slope > SUIT["slope_nogo_deg"]) | (rough > SUIT["rough_nogo"])


# --------------------------------------------------------------------------
# terrain along a route
# --------------------------------------------------------------------------

def profile(lons, lats) -> dict:
    lons = np.asarray(lons, dtype=float)
    lats = np.asarray(lats, dtype=float)
    elev = sample_grid(data.elevation(), lons, lats)
    slope = sample_grid(data.slope(), lons, lats)
    rough = sample_grid(data.roughness(), lons, lats)

    if len(lons) > 1:
        ds = haversine_m(lons[:-1], lats[:-1], lons[1:], lats[1:])
        de = np.diff(elev)
        grade = np.degrees(np.arctan2(de, np.maximum(ds, 1e-6)))
        # Path is usually ordered outward; keep signed grade for energy cost.
        grade = np.append(grade, 0.0)
    else:
        ds = np.array([])
        grade = np.array([0.0])

    return {
        "lon": lons,
        "lat": lats,
        "elev_m": elev,
        "slope_deg": slope,
        "roughness": rough,
        "segment_m": ds,
        "grade_deg": grade,
    }


def terrain_at(lon: float, lat: float) -> dict:
    return {
        "elevation_m": float(sample_grid(data.elevation(), lon, lat)[0]),
        "slope_deg": float(sample_grid(data.slope(), lon, lat)[0]),
        "roughness": float(sample_grid(data.roughness(), lon, lat)[0]),
    }


def route_terrain_stats(prof: dict) -> dict:
    elev = prof["elev_m"]
    slope = prof["slope_deg"]
    rough = prof["roughness"]
    ds = prof["segment_m"]

    if len(elev) > 1:
        de = np.diff(elev)
        ascent = float(np.nansum(de[de > 0]))
        descent = float(-np.nansum(de[de < 0]))
    else:
        ascent = descent = 0.0

    slope_ok = slope[np.isfinite(slope)]
    rough_ok = rough[np.isfinite(rough)]
    hazard = (
        np.nan_to_num(slope, nan=0.0) > SUIT["slope_nogo_deg"]
    ) | (np.nan_to_num(rough, nan=0.0) > SUIT["rough_nogo"])

    return {
        "distance_km": float(np.nansum(ds)) / 1000.0,
        "ascent_m": ascent,
        "descent_m": descent,
        "slope_p95": float(np.percentile(slope_ok, 95)) if slope_ok.size else 0.0,
        "slope_max": float(np.max(slope_ok)) if slope_ok.size else 0.0,
        "rough_p95": float(np.percentile(rough_ok, 95)) if rough_ok.size else 0.0,
        "hazard_samples": int(hazard.sum()),
        "warn_samples": int((np.nan_to_num(slope, nan=0.0) > SUIT["slope_warn_deg"]).sum()),
        "elev_start_m": float(elev[0]) if len(elev) else 0.0,
        "elev_end_m": float(elev[-1]) if len(elev) else 0.0,
    }
