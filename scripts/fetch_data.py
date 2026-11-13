"""Fetch every NASA/USGS layer once and cache it under data/raw.

Run from the repo root:

    .venv/bin/python scripts/fetch_data.py

The runtime app never calls these services; it reads the cache.
"""

from __future__ import annotations

import io
import json
import math
import sys
from pathlib import Path

import numpy as np
import requests
import tifffile
import urllib3
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import (  # noqa: E402
    ASSETS,
    BOX,
    CTX_MAX_Z,
    CTX_URL,
    HIRISE_URL,
    MARS_RADIUS_M,
    RAW,
    RAW_IMAGES_API,
    TREK_DEM,
    TREK_ELLIPSE,
    TREK_MINERALS,
    TREK_TRAVERSE,
    TREK_VIKING,
    TREK_WAYPOINTS,
    USGS_GEOLOGY,
    WEATHER_API,
)

urllib3.disable_warnings()

S = requests.Session()
S.headers.update({"User-Agent": "MarsGo/1.0 (NASA Space Apps hackathon)"})
S.verify = False

RAW.mkdir(parents=True, exist_ok=True)
ASSETS.mkdir(parents=True, exist_ok=True)
(ASSETS / "waypoints").mkdir(parents=True, exist_ok=True)


def log(msg: str) -> None:
    print(f"  {msg}")


def get(url, params=None, timeout=90, tries=3):
    last = None
    for _ in range(tries):
        try:
            r = S.get(url, params=params, timeout=timeout)
            r.raise_for_status()
            return r
        except Exception as exc:  # noqa: BLE001
            last = exc
    raise RuntimeError(f"GET failed: {url} ({last})")


def get_json(url, params=None, timeout=90):
    return get(url, params, timeout=timeout).json()


def save_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, separators=(",", ":")))
    log(f"{path.name}  {path.stat().st_size / 1024:.1f} KB")


# --------------------------------------------------------------------------
# geometry helpers
# --------------------------------------------------------------------------

def haversine(a, b) -> float:
    lon1, lat1 = a
    lon2, lat2 = b
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * MARS_RADIUS_M * math.asin(min(1.0, math.sqrt(h)))


def rdp(points, eps):
    """Ramer-Douglas-Peucker, iterative, works on (lon, lat) tuples."""
    if len(points) < 3:
        return points
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        x1, y1 = points[i]
        x2, y2 = points[j]
        dx, dy = x2 - x1, y2 - y1
        norm = math.hypot(dx, dy)
        best, best_i = -1.0, -1
        for k in range(i + 1, j):
            x, y = points[k]
            if norm == 0:
                dist = math.hypot(x - x1, y - y1)
            else:
                dist = abs(dy * x - dx * y + x2 * y1 - y2 * x1) / norm
            if dist > best:
                best, best_i = dist, k
        if best > eps:
            keep[best_i] = True
            stack.append((i, best_i))
            stack.append((best_i, j))
    return [p for p, k in zip(points, keep) if k]


def round_coords(coords, nd=6):
    return [[round(c[0], nd), round(c[1], nd)] for c in coords]


# --------------------------------------------------------------------------
# 1. rover traverse
# --------------------------------------------------------------------------

def fetch_traverse():
    print("[1/8] Perseverance traverse")
    data = get_json(TREK_TRAVERSE, {
        "where": "1=1", "outFields": "*", "outSR": 4326,
        "returnGeometry": "true", "f": "geojson",
    })
    out = {"type": "FeatureCollection", "features": []}
    for f in data["features"]:
        g = f["geometry"]
        if g["type"] == "LineString":
            segs = [g["coordinates"]]
        else:
            segs = g["coordinates"]
        for seg in segs:
            pts = rdp([(c[0], c[1]) for c in seg], 8e-6)
            if len(pts) < 2:
                continue
            out["features"].append({
                "type": "Feature",
                "properties": {
                    "sol": f["properties"].get("sol"),
                    "length_m": f["properties"].get("length"),
                },
                "geometry": {"type": "LineString", "coordinates": round_coords(pts)},
            })
    save_json(RAW / "traverse.geojson", out)
    return out


# --------------------------------------------------------------------------
# 2. named features + landing ellipse
# --------------------------------------------------------------------------

def fetch_named():
    print("[2/8] Named features and landing ellipse")
    wp = get_json(TREK_WAYPOINTS, {
        "where": "1=1", "outFields": "*", "outSR": 4326, "f": "geojson",
    })
    keep = {"type": "FeatureCollection", "features": []}
    for f in wp["features"]:
        p = f["properties"]
        c = f["geometry"]["coordinates"]
        keep["features"].append({
            "type": "Feature",
            "properties": {"name": p.get("name"), "kind": "region",
                           "source": "NASA Mars Trek"},
            "geometry": {"type": "Point", "coordinates": [c[0], c[1]]},
        })
    save_json(RAW / "waypoints.geojson", keep)

    el = get_json(TREK_ELLIPSE, {
        "where": "1=1", "outFields": "*", "outSR": 4326, "f": "geojson",
    })
    save_json(RAW / "landing_ellipse.geojson", el)


# --------------------------------------------------------------------------
# 3. USGS geology
# --------------------------------------------------------------------------

def fetch_geology():
    print("[3/8] USGS Jezero geologic map")
    params = {
        "where": "1=1",
        "geometry": f"{BOX['w']},{BOX['s']},{BOX['e']},{BOX['n']}",
        "geometryType": "esriGeometryEnvelope",
        "inSR": 4326,
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "unit,name,symbol,Unit_Description,Unit_Interpretation",
        "outSR": 4326,
        "returnGeometry": "true",
        "geometryPrecision": 5,
        "maxAllowableOffset": 0.0002,
        "f": "geojson",
    }
    data = get_json(f"{USGS_GEOLOGY}/8/query", params)
    save_json(RAW / "geology.geojson", data)

    # Unit annotation points are a nice optional label layer.
    anno = get_json(f"{USGS_GEOLOGY}/4/query", {
        "where": "1=1", "outFields": "*", "outSR": 4326,
        "returnGeometry": "true", "f": "geojson",
    })
    save_json(RAW / "geology_labels.geojson", anno)


# --------------------------------------------------------------------------
# 4. mineral + color context rasters
# --------------------------------------------------------------------------

def fetch_minerals():
    print("[4/8] Spectral detections and color context")
    w, s, e, n = BOX["w"], BOX["s"], BOX["e"], BOX["n"]
    for name, url in TREK_MINERALS.items():
        try:
            r = get(url, {
                "bbox": f"{w},{s},{e},{n}", "bboxSR": 4326, "imageSR": 4326,
                "size": "1600,900", "format": "png32", "transparent": "true",
                "f": "image",
            })
            (RAW / f"minerals_{name}.png").write_bytes(r.content)
            log(f"minerals_{name}.png  {len(r.content) / 1024:.1f} KB")
        except Exception as exc:  # noqa: BLE001
            log(f"skip {name}: {exc}")

    try:
        r = get(TREK_VIKING, {
            "bbox": f"{w},{s},{e},{n}", "bboxSR": 4326, "imageSR": 4326,
            "size": "1200,700", "format": "png32", "f": "image",
        })
        (RAW / "viking_color.png").write_bytes(r.content)
        log(f"viking_color.png  {len(r.content) / 1024:.1f} KB")
    except Exception as exc:  # noqa: BLE001
        log(f"skip viking: {exc}")


# --------------------------------------------------------------------------
# 5. DEM
# --------------------------------------------------------------------------

def fetch_dem():
    print("[5/8] MOLA/HRSC blended DEM")
    w, s, e, n = BOX["w"], BOX["s"], BOX["e"], BOX["n"]
    r = get(TREK_DEM, {
        "bbox": f"{w},{s},{e},{n}", "bboxSR": 4326, "imageSR": 4326,
        "size": "1400,800", "format": "tiff", "pixelType": "S16",
        "noDataInterpretation": "esriNoDataMatchAny",
        "interpolation": "RSP_BilinearInterpolation", "f": "image",
    }, timeout=180)
    path = RAW / "dem.tif"
    path.write_bytes(r.content)
    arr = tifffile.imread(path).astype("float32")
    log(f"dem.tif  {arr.shape}  min={np.nanmin(arr):.0f} m  max={np.nanmax(arr):.0f} m")


# --------------------------------------------------------------------------
# 6. weather
# --------------------------------------------------------------------------

def fetch_weather():
    print("[6/8] MSL REMS weather snapshot")
    raw = get_json(WEATHER_API)
    soles = raw.get("soles", [])
    summary = {"source": "MSL REMS (Gale Crater analog)", "recent": []}
    for row in list(reversed(soles[:7])):
        summary["recent"].append({
            "sol": row.get("sol"),
            "terrestrial_date": row.get("terrestrial_date"),
            "season": row.get("season"),
            "min_temp_c": row.get("min_temp"),
            "max_temp_c": row.get("max_temp"),
            "pressure_pa": row.get("pressure"),
            "wind": row.get("wind_speed"),
            "opacity": row.get("atmo_opacity"),
        })
    if soles:
        summary["latest"] = summary["recent"][-1]
    save_json(RAW / "weather_snapshot.json", summary)


# --------------------------------------------------------------------------
# 7. stations from the rover's final approach
# --------------------------------------------------------------------------

def build_stations(traverse):
    print("[7/8] Heritage stations from traverse")
    feats = sorted(
        [f for f in traverse["features"] if f["properties"].get("sol") is not None],
        key=lambda f: int(f["properties"]["sol"]),
    )
    # Stitch contiguous runs (a gap > 150 m means the rover was moved / data gap).
    runs, cur, prev = [], [], None
    for f in feats:
        pts = [(c[0], c[1]) for c in f["geometry"]["coordinates"]]
        if not pts:
            continue
        if prev is not None and haversine(prev, pts[0]) > 150:
            if len(cur) > 1:
                runs.append(cur)
            cur = []
        if not cur:
            cur.append((int(f["properties"]["sol"]), pts[0]))
        for p in pts[1:]:
            cur.append((int(f["properties"]["sol"]), p))
        prev = pts[-1]
    if len(cur) > 1:
        runs.append(cur)

    run = max(runs, key=len)
    cum = [0.0]
    for i in range(1, len(run)):
        cum.append(cum[-1] + haversine(run[i - 1][1], run[i][1]))
    total = cum[-1]
    log(f"longest run {total / 1000:.2f} km, sol {run[0][0]} -> {run[-1][0]}")

    def point_at(dist_m):
        """Point at a cumulative distance from the start of the run (metres)."""
        target = max(0.0, min(total, dist_m))
        for i in range(1, len(run)):
            if cum[i] >= target:
                return run[i]
        return run[-1]

    specs = [
        ("START", "Forward base", 4.0),
        ("S1", "Heritage A", 3.0),
        ("S2", "Heritage B", 2.0),
        ("S3", "Delta front", 0.5),
    ]
    feats_out = []
    for sid, name, off in specs:
        sol, (lon, lat) = point_at(total - off * 1000)
        feats_out.append({
            "type": "Feature",
            "properties": {
                "id": sid, "name": name, "sol": sol, "offset_km": off,
                "role": "start" if sid == "START" else "station",
            },
            "geometry": {"type": "Point", "coordinates": [round(lon, 6), round(lat, 6)]},
        })
        log(f"{sid} {name:12} sol {sol:4d}  {lon:.5f},{lat:.5f}")

    save_json(RAW / "stations.geojson", {"type": "FeatureCollection", "features": feats_out})
    return feats_out


# --------------------------------------------------------------------------
# 8. point-of-view images
# --------------------------------------------------------------------------

def fetch_images(stations):
    print("[8/8] Perseverance point-of-view images")
    for st in stations:
        sid = st["properties"]["id"]
        if sid == "START":
            continue
        sol = st["properties"]["sol"]
        try:
            data = get_json(RAW_IMAGES_API.format(sol=sol), timeout=120)
            imgs = [i for i in data.get("images", [])
                    if i.get("image_files", {}).get("large")
                    or i.get("image_files", {}).get("medium")]
            if not imgs:
                log(f"no images for {sid} sol {sol}")
                continue

            def area(i):
                """Rank larger browse frames first (subframes are 128x128)."""
                dim = i.get("extended", {}).get("dimension", "")
                try:
                    w, h = dim.strip("()").split(",")
                    return int(w) * int(h)
                except Exception:  # noqa: BLE001
                    return 0

            def rank(i):
                """Prefer wide-field context cameras over telescopic close-ups."""
                inst = str(i.get("camera", {}).get("instrument", ""))
                if inst.startswith("MCZ"):
                    pref = 3
                elif "NAVCAM" in inst:
                    pref = 2
                elif "HAZCAM" in inst:
                    pref = 1
                else:
                    pref = 0
                return (pref, area(i))

            imgs.sort(key=rank, reverse=True)
            path = None
            pick = None
            for candidate in imgs[:12]:
                url = (candidate["image_files"].get("large")
                       or candidate["image_files"]["medium"])
                try:
                    r = get(url, timeout=120)
                    test = Image.open(io.BytesIO(r.content))
                    if test.size[0] < 500 or len(r.content) < 15000:
                        continue
                    suffix = Path(url).suffix or ".jpg"
                    path = ASSETS / "waypoints" / f"{sid.lower()}{suffix}"
                    path.write_bytes(r.content)
                    pick = candidate
                    break
                except Exception:  # noqa: BLE001
                    continue
            if path is None:
                log(f"no usable image for {sid}")
                continue
            meta = {
                "sol": sol,
                "camera": (pick.get("camera", {}).get("instrument")
                           or pick.get("camera", {}).get("model_type", "unknown")),
                "title": pick.get("title"),
                "caption": (pick.get("caption") or "").strip()[:400],
                "image_id": pick.get("imageid"),
                "source": "NASA/JPL-Caltech Mars 2020 Perseverance raw images",
                "url": url,
            }
            (ASSETS / "waypoints" / f"{sid.lower()}.json").write_text(
                json.dumps(meta, indent=1))
            log(f"{path.name}  sol {sol}  {len(r.content) / 1024:.1f} KB")
        except Exception as exc:  # noqa: BLE001
            log(f"skip {sid}: {exc}")


def main():
    print("MarsGo data pipeline")
    traverse = fetch_traverse()
    fetch_named()
    fetch_geology()
    fetch_minerals()
    fetch_dem()
    fetch_weather()
    stations = build_stations(traverse)
    fetch_images(stations)
    print("\nDone. Cache is in data/raw and assets/waypoints.")


if __name__ == "__main__":
    main()
