"""Terrain grids: coordinate mapping, cost surface, manual hazards, and profile sampling.

Scientific disclosures:
- Topographic slope is derived from the 200 m/px MOLA/HRSC Blended DEM resampled to a 10 m
  planning grid (interpolated regional slope estimate unless a 1 m HiRISE DTM is loaded).
- Surface Texture Index (formerly labeled 'roughness') is derived from local luminance contrast
  on the 4.83 m/px MRO CTX mosaic and acts as an optical proxy for boulder/dune texture.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from . import data
from .config import BOX, DEM_NATIVE_RES_M, GRID_M, MARS_RADIUS_M, ROUTE_MODES, SUIT

NO_GO_COST: float = 1.0e6


# -----------------------------------------------------------------------------
# coordinate mapping
# -----------------------------------------------------------------------------

def grid_shape() -> tuple[int, int]:
    """Return (ny, nx) dimensions of the 10 m planning grid."""
    return data.slope().shape


def lonlat_to_rc(lon: float | np.ndarray, lat: float | np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Convert planetocentric (lon, lat) in degrees to fractional grid (row, col)."""
    ny, nx = grid_shape()
    lon_arr = np.asarray(lon, dtype=float)
    lat_arr = np.asarray(lat, dtype=float)
    col = (lon_arr - BOX["w"]) / (BOX["e"] - BOX["w"]) * (nx - 1)
    row = (BOX["n"] - lat_arr) / (BOX["n"] - BOX["s"]) * (ny - 1)
    return row, col


def rc_to_lonlat(row: float | np.ndarray, col: float | np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Convert grid (row, col) coordinates back to planetocentric (lon, lat) in degrees."""
    ny, nx = grid_shape()
    row_arr = np.asarray(row, dtype=float)
    col_arr = np.asarray(col, dtype=float)
    lon = BOX["w"] + col_arr / (nx - 1) * (BOX["e"] - BOX["w"])
    lat = BOX["n"] - row_arr / (ny - 1) * (BOX["n"] - BOX["s"])
    return lon, lat


def sample_grid(grid: np.ndarray, lon: float | np.ndarray, lat: float | np.ndarray) -> np.ndarray:
    """Bilinear sample on a 2D raster. Points outside BOX return NaN."""
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
    return np.where(inside, v, np.nan)


# -----------------------------------------------------------------------------
# distance & spherical geometry on Mars
# -----------------------------------------------------------------------------

def haversine_m(
    lon1: float | np.ndarray,
    lat1: float | np.ndarray,
    lon2: float | np.ndarray,
    lat2: float | np.ndarray,
) -> np.ndarray:
    """Great-circle distance in meters on the Mars 2000 sphere (R = 3,396,190 m)."""
    p1 = np.radians(np.asarray(lat1, dtype=float))
    p2 = np.radians(np.asarray(lat2, dtype=float))
    dp = p2 - p1
    dl = np.radians(np.asarray(lon2, dtype=float) - np.asarray(lon1, dtype=float))
    h = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2.0 * MARS_RADIUS_M * np.arcsin(np.minimum(1.0, np.sqrt(h)))


def path_length_km(lons: np.ndarray | list[float], lats: np.ndarray | list[float]) -> float:
    """Total polyline length in kilometers."""
    if len(lons) < 2:
        return 0.0
    d = haversine_m(lons[:-1], lats[:-1], lons[1:], lats[1:])
    return float(np.sum(d)) / 1000.0


def bearing_deg(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Initial great-circle bearing, degrees clockwise from north [0, 360)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dl) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(x, y)) + 360.0) % 360.0


# -----------------------------------------------------------------------------
# manual hazard mask builder & cost surface
# -----------------------------------------------------------------------------

def build_hazard_mask(
    zones: list[dict[str, float]] | tuple[dict[str, float], ...] | None = None,
    shape: tuple[int, int] | None = None,
) -> np.ndarray | None:
    """Rasterize user-defined circular hazard zones [{lon, lat, radius_m}, ...] onto the grid."""
    if not zones:
        return None
    ny, nx = shape if shape is not None else grid_shape()
    mask = np.zeros((ny, nx), dtype=bool)
    rows = np.arange(ny, dtype=np.float32)[:, None]
    cols = np.arange(nx, dtype=np.float32)[None, :]
    for z in zones:
        lon = float(z["lon"])
        lat = float(z["lat"])
        radius_m = max(10.0, float(z.get("radius_m", 150.0)))
        r_center, c_center = lonlat_to_rc(lon, lat)
        radius_cells = radius_m / GRID_M
        dist2 = (rows - float(r_center)) ** 2 + (cols - float(c_center)) ** 2
        mask |= dist2 <= (radius_cells ** 2)
    return mask


def no_go_mask(
    slope_nogo_deg: float | None = None,
    rough_nogo: float | None = None,
    manual_hazard: np.ndarray | None = None,
) -> np.ndarray:
    """Return boolean mask where True indicates an impassable no-go cell."""
    s_limit = float(SUIT["slope_nogo_deg"] if slope_nogo_deg is None else slope_nogo_deg)
    r_limit = float(SUIT["rough_nogo"] if rough_nogo is None else rough_nogo)
    slope = data.slope()
    rough = data.roughness()
    mask = (slope > s_limit) | (rough > r_limit)
    if manual_hazard is not None:
        mask = mask | np.asarray(manual_hazard, dtype=bool)
    return mask


def cost_surface(
    manual_hazard: np.ndarray | None = None,
    mode: str = "balanced",
    slope_nogo_deg: float | None = None,
    slope_warn_deg: float | None = None,
    rough_nogo: float | None = None,
) -> np.ndarray:
    """Compute the 2D traversal cost surface.

    All thresholds default to ``config.SUIT`` so ``terrain.py``, ``routing.py``,
    ``suit.py``, and ``ui.py`` never disagree on hard slope or texture limits.
    When ``manual_hazard`` is None and default balanced parameters are used, a
    pre-computed ``cost_surface.npy`` is used if available.
    """
    s_nogo = float(SUIT["slope_nogo_deg"] if slope_nogo_deg is None else slope_nogo_deg)
    s_warn = float(SUIT["slope_warn_deg"] if slope_warn_deg is None else slope_warn_deg)
    r_nogo = float(SUIT["rough_nogo"] if rough_nogo is None else rough_nogo)

    # Fast path: use cached .npy if nominal defaults are requested
    if (
        manual_hazard is None
        and mode == "balanced"
        and abs(s_nogo - SUIT["slope_nogo_deg"]) < 1e-6
        and abs(s_warn - SUIT["slope_warn_deg"]) < 1e-6
        and abs(r_nogo - SUIT["rough_nogo"]) < 1e-6
    ):
        cached = data.cached_cost_surface()
        if cached is not None and cached.shape == grid_shape():
            return cached.copy()

    weights = ROUTE_MODES.get(mode, ROUTE_MODES["balanced"])
    slope = data.slope()
    rough = data.roughness()

    cost = (
        float(weights["w_base"])
        + float(weights["w_slope"]) * np.clip(slope / max(s_nogo, 1.0), 0.0, 1.0)
        + float(weights["w_rough"]) * np.clip(rough / max(r_nogo, 1e-3), 0.0, 1.0)
        + float(weights["w_warn"]) * (slope > s_warn)
    )

    no_go = no_go_mask(
        slope_nogo_deg=s_nogo,
        rough_nogo=r_nogo,
        manual_hazard=manual_hazard,
    )
    cost = cost.astype(np.float32)
    cost[no_go] = NO_GO_COST
    return cost


# -----------------------------------------------------------------------------
# terrain along a route
# -----------------------------------------------------------------------------

def profile(lons: np.ndarray | list[float], lats: np.ndarray | list[float]) -> dict[str, np.ndarray]:
    """Sample elevation, regional slope, and Surface Texture Index along a path."""
    lons_arr = np.asarray(lons, dtype=float)
    lats_arr = np.asarray(lats, dtype=float)
    elev = sample_grid(data.elevation(), lons_arr, lats_arr)
    slope = sample_grid(data.slope(), lons_arr, lats_arr)
    rough = sample_grid(data.roughness(), lons_arr, lats_arr)

    if len(lons_arr) > 1:
        ds = haversine_m(lons_arr[:-1], lats_arr[:-1], lons_arr[1:], lats_arr[1:])
        de = np.diff(elev)
        grade = np.degrees(np.arctan2(de, np.maximum(ds, 1e-6)))
        grade = np.append(grade, 0.0)
        cum_km = np.concatenate([[0.0], np.cumsum(ds) / 1000.0])
    else:
        ds = np.array([], dtype=float)
        grade = np.array([0.0], dtype=float)
        cum_km = np.zeros(len(lons_arr), dtype=float)

    return {
        "lon": lons_arr,
        "lat": lats_arr,
        "elev_m": elev,
        "slope_deg": slope,
        "roughness": rough,
        "texture_index": rough,
        "segment_m": ds,
        "grade_deg": grade,
        "cum_km": cum_km,
    }


def terrain_at(lon: float, lat: float) -> dict[str, float | str]:
    """Point query returning elevation, estimated slope, and Surface Texture Index."""
    t_idx = float(sample_grid(data.roughness(), lon, lat)[0])
    return {
        "elevation_m": float(sample_grid(data.elevation(), lon, lat)[0]),
        "slope_deg": float(sample_grid(data.slope(), lon, lat)[0]),
        "roughness": t_idx,
        "surface_texture_index": t_idx,
        "slope_resolution_note": f"Interpolated from {DEM_NATIVE_RES_M:.0f} m/px DEM onto {GRID_M:.0f} m grid",
    }


def route_terrain_stats(
    prof: dict[str, np.ndarray],
    slope_nogo_deg: float | None = None,
    slope_warn_deg: float | None = None,
    rough_nogo: float | None = None,
    manual_hazard: np.ndarray | None = None,
) -> dict[str, Any]:
    """Compute aggregate terrain statistics along a sampled route profile."""
    s_nogo = float(SUIT["slope_nogo_deg"] if slope_nogo_deg is None else slope_nogo_deg)
    s_warn = float(SUIT["slope_warn_deg"] if slope_warn_deg is None else slope_warn_deg)
    r_nogo = float(SUIT["rough_nogo"] if rough_nogo is None else rough_nogo)

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
        np.nan_to_num(slope, nan=0.0) > s_nogo
    ) | (np.nan_to_num(rough, nan=0.0) > r_nogo)

    if manual_hazard is not None and len(prof["lon"]) > 0:
        ny, nx = manual_hazard.shape
        r_idx, c_idx = lonlat_to_rc(prof["lon"], prof["lat"])
        r_int = np.clip(np.round(r_idx).astype(int), 0, ny - 1)
        c_int = np.clip(np.round(c_idx).astype(int), 0, nx - 1)
        hazard = hazard | manual_hazard[r_int, c_int]

    return {
        "distance_km": float(np.nansum(ds)) / 1000.0,
        "ascent_m": ascent,
        "descent_m": descent,
        "slope_p95": float(np.percentile(slope_ok, 95)) if slope_ok.size else 0.0,
        "slope_max": float(np.max(slope_ok)) if slope_ok.size else 0.0,
        "rough_p95": float(np.percentile(rough_ok, 95)) if rough_ok.size else 0.0,
        "texture_index_p95": float(np.percentile(rough_ok, 95)) if rough_ok.size else 0.0,
        "hazard_samples": int(hazard.sum()),
        "warn_samples": int((np.nan_to_num(slope, nan=0.0) > s_warn).sum()),
        "elev_start_m": float(elev[0]) if len(elev) else 0.0,
        "elev_end_m": float(elev[-1]) if len(elev) else 0.0,
        "dem_native_res_m": DEM_NATIVE_RES_M,
        "grid_res_m": GRID_M,
        "is_interpolated_slope": True,
    }
