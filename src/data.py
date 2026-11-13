"""Cached loaders for every local dataset.

The runtime never touches the network. All paths point at the cached files that
``scripts/fetch_data.py`` and ``scripts/build_layers.py`` wrote.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image

from .config import ASSETS, BOX, PROC, RAW


# --------------------------------------------------------------------------
# small file helpers
# --------------------------------------------------------------------------

def _json(path: Path):
    return json.loads(path.read_text())


@lru_cache(maxsize=1)
def meta() -> dict:
    return _json(PROC / "meta.json")


@lru_cache(maxsize=1)
def stations() -> tuple[dict, ...]:
    feats = _json(RAW / "stations.geojson")["features"]
    out = []
    for f in feats:
        lon, lat = f["geometry"]["coordinates"]
        props = dict(f["properties"])
        props.update({"lon": lon, "lat": lat})
        out.append(props)
    return tuple(out)


def station(station_id: str) -> dict | None:
    for s in stations():
        if s["id"] == station_id:
            return s
    return None


@lru_cache(maxsize=1)
def traverse_segments() -> tuple[tuple[tuple[float, float], ...], ...]:
    """Rover traverse as a tuple of (lon, lat) segments for one polyline."""
    feats = _json(RAW / "traverse.geojson")["features"]
    segs = []
    for f in feats:
        pts = tuple((round(c[0], 6), round(c[1], 6))
                    for c in f["geometry"]["coordinates"])
        if len(pts) > 1:
            segs.append(pts)
    return tuple(segs)


@lru_cache(maxsize=1)
def traverse_features() -> tuple[dict, ...]:
    return tuple(_json(RAW / "traverse.geojson")["features"])


@lru_cache(maxsize=1)
def geology() -> dict:
    return _json(RAW / "geology.geojson")


@lru_cache(maxsize=1)
def geology_labels() -> dict:
    return _json(RAW / "geology_labels.geojson")


@lru_cache(maxsize=1)
def waypoints() -> dict:
    return _json(RAW / "waypoints.geojson")


@lru_cache(maxsize=1)
def landing_ellipse() -> dict:
    return _json(RAW / "landing_ellipse.geojson")


@lru_cache(maxsize=1)
def weather() -> dict:
    return _json(RAW / "weather_snapshot.json")


# --------------------------------------------------------------------------
# rasters
# --------------------------------------------------------------------------

@lru_cache(maxsize=1)
def elevation() -> np.ndarray:
    return np.load(PROC / "elevation.npy").astype(np.float32)


@lru_cache(maxsize=1)
def slope() -> np.ndarray:
    return np.load(PROC / "slope.npy").astype(np.float32)


@lru_cache(maxsize=1)
def roughness() -> np.ndarray:
    return np.load(PROC / "roughness.npy").astype(np.float32)


def basemap_path() -> Path:
    return PROC / "basemap_ctx.png"


def overlay_path(name: str) -> Path:
    return PROC / f"overlay_{name}.png"


def closeup_path(station_id: str) -> Path | None:
    p = PROC.parent / "stations" / f"{station_id.lower()}_closeup.png"
    return p if p.exists() else None


def pov_image(station_id: str) -> tuple[Image.Image, dict] | None:
    base = ASSETS / "waypoints"
    for ext in (".jpg", ".jpeg", ".png"):
        p = base / f"{station_id.lower()}{ext}"
        if p.exists() and p.stat().st_size > 5000:
            meta_path = base / f"{station_id.lower()}.json"
            meta = _json(meta_path) if meta_path.exists() else {}
            return Image.open(p), meta
    return None


# --------------------------------------------------------------------------
# geometry helpers
# --------------------------------------------------------------------------

def _point_in_ring(lon: float, lat: float, ring) -> bool:
    """Ray casting for a single linear ring of (lon, lat) pairs."""
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > lat) != (yj > lat)) and (
            lon < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-12) + xi
        ):
            inside = not inside
        j = i
    return inside


def _point_in_polygon(lon: float, lat: float, rings) -> bool:
    if not rings:
        return False
    if not _point_in_ring(lon, lat, rings[0]):
        return False
    return not any(_point_in_ring(lon, lat, hole) for hole in rings[1:])


@lru_cache(maxsize=1)
def _geology_index() -> tuple[tuple[dict, tuple], ...]:
    out = []
    for f in geology()["features"]:
        geom = f["geometry"]
        polys = (
            [geom["coordinates"]] if geom["type"] == "Polygon"
            else geom["coordinates"]
        )
        for rings in polys:
            xs = [p[0] for p in rings[0]]
            ys = [p[1] for p in rings[0]]
            out.append((f["properties"], (min(xs), min(ys), max(xs), max(ys), rings)))
    return tuple(out)


def unit_at(lon: float, lat: float) -> dict | None:
    """Return the USGS geologic unit polygon containing this point."""
    for props, bbox in _geology_index():
        w, s, e, n = bbox[:4]
        if not (w <= lon <= e and s <= lat <= n):
            continue
        if _point_in_polygon(lon, lat, bbox[4]):
            return props
    return None


def nearest_label(lon: float, lat: float, kind: str | None = None) -> dict | None:
    """Closest named Mars Trek feature, used for orientation text."""
    best, best_d = None, float("inf")
    for f in waypoints()["features"]:
        if kind and f["properties"].get("kind") != kind:
            continue
        x, y = f["geometry"]["coordinates"]
        d = (x - lon) ** 2 + (y - lat) ** 2
        if d < best_d:
            best, best_d = f, d
    return best


# --------------------------------------------------------------------------
# misc
# --------------------------------------------------------------------------

def image_stats(path: Path) -> dict:
    arr = np.asarray(Image.open(path).convert("L"), dtype=np.float32)
    return {
        "width": arr.shape[1],
        "height": arr.shape[0],
        "mean": float(arr.mean()),
        "std": float(arr.std()),
        "black_pct": float((arr < 5).mean() * 100),
    }


def mineral_coverage_note() -> str:
    """The OMEGA/CRISM and THEMIS exports are empty inside this AOI."""
    return (
        "No confident hydrated-mineral detection inside the mission box. "
        "The crew samples this unit to ground-truth the orbital null."
    )
