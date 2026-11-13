"""Cached loaders for every local dataset.

The runtime never touches the network. All paths point at the cached files that
``scripts/fetch_data.py`` and ``scripts/build_layers.py`` wrote.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from .config import ASSETS, DATA_PROVENANCE, PROC, RAW


# -----------------------------------------------------------------------------
# small file helpers
# -----------------------------------------------------------------------------

def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def meta() -> dict[str, Any]:
    return _json(PROC / "meta.json")


@lru_cache(maxsize=1)
def stations() -> tuple[dict[str, Any], ...]:
    """Return tuple of station dicts (ordered with START and S1..S3)."""
    feats = _json(RAW / "stations.geojson")["features"]
    out: list[dict[str, Any]] = []
    for f in feats:
        lon, lat = f["geometry"]["coordinates"]
        props = dict(f["properties"])
        props.update({"lon": float(lon), "lat": float(lat)})
        out.append(props)
    return tuple(out)


@lru_cache(maxsize=1)
def load_stations() -> dict[str, dict[str, Any]]:
    """Return dictionary mapping station ID (e.g. 'START', 'S1') to station metadata."""
    return {s["id"]: s for s in stations()}


def station(station_id: str) -> dict[str, Any] | None:
    """Lookup a single station by ID."""
    return load_stations().get(station_id)


@lru_cache(maxsize=1)
def traverse_segments() -> tuple[tuple[tuple[float, float], ...], ...]:
    """Rover traverse as a tuple of (lon, lat) segments for one polyline."""
    feats = _json(RAW / "traverse.geojson")["features"]
    segs: list[tuple[tuple[float, float], ...]] = []
    for f in feats:
        geom = f.get("geometry", {})
        coords = geom.get("coordinates", [])
        if geom.get("type") == "MultiLineString":
            for line in coords:
                pts = tuple((round(float(c[0]), 6), round(float(c[1]), 6)) for c in line)
                if len(pts) > 1:
                    segs.append(pts)
        else:
            pts = tuple((round(float(c[0]), 6), round(float(c[1]), 6)) for c in coords)
            if len(pts) > 1:
                segs.append(pts)
    return tuple(segs)


@lru_cache(maxsize=1)
def traverse_features() -> tuple[dict[str, Any], ...]:
    return tuple(_json(RAW / "traverse.geojson")["features"])


@lru_cache(maxsize=1)
def geology() -> dict[str, Any]:
    return _json(RAW / "geology.geojson")


@lru_cache(maxsize=1)
def geology_labels() -> dict[str, Any]:
    return _json(RAW / "geology_labels.geojson")


@lru_cache(maxsize=1)
def waypoints() -> dict[str, Any]:
    return _json(RAW / "waypoints.geojson")


@lru_cache(maxsize=1)
def landing_ellipse() -> dict[str, Any]:
    return _json(RAW / "landing_ellipse.geojson")


@lru_cache(maxsize=1)
def weather() -> dict[str, Any]:
    return _json(RAW / "weather_snapshot.json")


# -----------------------------------------------------------------------------
# rasters
# -----------------------------------------------------------------------------

@lru_cache(maxsize=1)
def elevation() -> np.ndarray:
    return np.load(PROC / "elevation.npy").astype(np.float32)


@lru_cache(maxsize=1)
def slope() -> np.ndarray:
    return np.load(PROC / "slope.npy").astype(np.float32)


@lru_cache(maxsize=1)
def roughness() -> np.ndarray:
    """Load the CTX-derived Surface Texture Index (optical roughness proxy)."""
    return np.load(PROC / "roughness.npy").astype(np.float32)


@lru_cache(maxsize=1)
def cached_cost_surface() -> np.ndarray | None:
    """Load pre-computed nominal cost_surface.npy if present on disk."""
    path = PROC / "cost_surface.npy"
    if path.exists():
        return np.load(path).astype(np.float32)
    return None


def basemap_path() -> Path:
    return PROC / "basemap_ctx.png"


def overlay_path(name: str) -> Path:
    return PROC / f"overlay_{name}.png"


def closeup_path(station_id: str) -> Path | None:
    p = PROC.parent / "stations" / f"{station_id.lower()}_closeup.png"
    return p if p.exists() else None


def pov_image(station_id: str) -> tuple[Image.Image, dict[str, Any]] | None:
    """Return (PIL.Image, metadata_dict) for a given station ID."""
    base = ASSETS / "waypoints"
    for ext in (".jpg", ".jpeg", ".png"):
        p = base / f"{station_id.lower()}{ext}"
        if p.exists() and p.stat().st_size > 1000:
            meta_path = base / f"{station_id.lower()}.json"
            m = _json(meta_path) if meta_path.exists() else {}
            return Image.open(p), m
    return None


def load_station_pov(station_id: str) -> tuple[Image.Image, dict[str, Any]] | tuple[()]:
    """Compatibility helper used by smoke_test.py and station cards."""
    res = pov_image(station_id)
    return res if res is not None else ()


# -----------------------------------------------------------------------------
# geometry helpers
# -----------------------------------------------------------------------------

def _point_in_ring(lon: float, lat: float, ring: list[list[float]]) -> bool:
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


def _point_in_polygon(lon: float, lat: float, rings: list[list[list[float]]]) -> bool:
    if not rings:
        return False
    if not _point_in_ring(lon, lat, rings[0]):
        return False
    return not any(_point_in_ring(lon, lat, hole) for hole in rings[1:])


@lru_cache(maxsize=1)
def _geology_index() -> tuple[tuple[dict[str, Any], tuple[Any, ...]], ...]:
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


def unit_at(lon: float, lat: float) -> dict[str, Any] | None:
    """Return the USGS geologic unit polygon containing this point."""
    for props, bbox in _geology_index():
        w, s, e, n = bbox[:4]
        if not (w <= lon <= e and s <= lat <= n):
            continue
        if _point_in_polygon(lon, lat, bbox[4]):
            return props
    return None


def nearest_label(lon: float, lat: float, kind: str | None = None) -> dict[str, Any] | None:
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


# -----------------------------------------------------------------------------
# misc & provenance
# -----------------------------------------------------------------------------

def image_stats(path: Path) -> dict[str, float | int]:
    arr = np.asarray(Image.open(path).convert("L"), dtype=np.float32)
    return {
        "width": int(arr.shape[1]),
        "height": int(arr.shape[0]),
        "mean": float(arr.mean()),
        "std": float(arr.std()),
        "black_pct": float((arr < 5).mean() * 100),
    }


def mineral_coverage_note() -> str:
    """The OMEGA/CRISM and THEMIS exports are empty inside this AOI."""
    return (
        "No confident hydrated-mineral detection inside the mission box at orbital scale. "
        "The crew samples this unit in-situ to ground-truth the orbital null."
    )


def provenance_records() -> tuple[dict[str, str], ...]:
    """Return structured data provenance records for every GIS layer."""
    return DATA_PROVENANCE
