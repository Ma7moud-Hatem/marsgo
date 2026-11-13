"""Build cached rasters and derived terrain layers for MarsGo."""

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
from PIL import Image, ImageEnhance
from scipy.ndimage import gaussian_filter, uniform_filter, zoom

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import (  # noqa: E402
    BOX, CTX_MAX_Z, CTX_URL, GRID_M, HIRISE_URL, HIRISE_Z, MARS_RADIUS_M,
    PROC, RAW,
)

urllib3.disable_warnings()
S = requests.Session()
S.headers.update({"User-Agent": "MarsGo/1.0 (NASA Space Apps hackathon)"})
S.verify = False

PROC.mkdir(parents=True, exist_ok=True)
(RAW.parent / "stations").mkdir(parents=True, exist_ok=True)

TILE = 512
DEG = math.pi / 180.0


def tile_grid(z: int):
    return 2 ** (z + 1), 2 ** z, 180.0 / 2 ** z


def fetch_tile(url, z, row, col):
    try:
        r = S.get(f"{url}/{z}/{row}/{col}", timeout=45)
        if r.status_code != 200 or not r.content:
            return None
        return Image.open(io.BytesIO(r.content)).convert("L")
    except Exception:  # noqa: BLE001
        return None


def mosaic(url, z, box, max_tiles=400):
    cols, rows, d = tile_grid(z)
    c0 = int(math.floor((box["w"] + 180) / d))
    c1 = int(math.floor((box["e"] + 180) / d))
    r0 = int(math.floor((90 - box["n"]) / d))
    r1 = int(math.floor((90 - box["s"]) / d))
    if (c1 - c0 + 1) * (r1 - r0 + 1) > max_tiles:
        raise ValueError("too many tiles")

    canvas = Image.new("L", ((c1 - c0 + 1) * TILE, (r1 - r0 + 1) * TILE), 0)
    got = 0
    for rr in range(r0, r1 + 1):
        for cc in range(c0, c1 + 1):
            im = fetch_tile(url, z, rr, cc)
            if im is None:
                continue
            canvas.paste(im, ((cc - c0) * TILE, (rr - r0) * TILE))
            got += 1

    lon0 = -180 + c0 * d
    lat0 = 90 - r0 * d
    x0 = int(round((box["w"] - lon0) / d * TILE))
    x1 = int(round((box["e"] - lon0) / d * TILE))
    y0 = int(round((lat0 - box["n"]) / d * TILE))
    y1 = int(round((lat0 - box["s"]) / d * TILE))
    crop = canvas.crop((x0, y0, x1, y1))
    return crop, got, (c1 - c0 + 1) * (r1 - r0 + 1)


def colorize(values, vmin, vmax, stops, alpha_stops=None):
    """Map a 2D array to RGBA using piecewise-linear colour stops."""
    v = np.clip((values - vmin) / max(vmax - vmin, 1e-9), 0, 1)
    h, w = v.shape
    out = np.zeros((h, w, 4), dtype=np.uint8)
    xs = np.array([s[0] for s in stops], dtype=float)
    rs = np.array([s[1][0] for s in stops], dtype=float)
    gs = np.array([s[1][1] for s in stops], dtype=float)
    bs = np.array([s[1][2] for s in stops], dtype=float)
    out[..., 0] = np.interp(v, xs, rs).astype(np.uint8)
    out[..., 1] = np.interp(v, xs, gs).astype(np.uint8)
    out[..., 2] = np.interp(v, xs, bs).astype(np.uint8)
    if alpha_stops:
        ax = np.array([a[0] for a in alpha_stops], dtype=float)
        av = np.array([a[1] for a in alpha_stops], dtype=float)
        out[..., 3] = np.interp(v, ax, av).astype(np.uint8)
    else:
        out[..., 3] = 160
    return out


def main():
    print("MarsGo layer builder")

    # ---------------------------------------------------------------- basemap
    print("[1/6] CTX mosaic")
    ctx, got, total = mosaic(CTX_URL, CTX_MAX_Z, BOX)
    print(f"  tiles {got}/{total}  size {ctx.size}")
    lum = np.asarray(ctx, dtype=np.float32)
    p2, p98 = np.percentile(lum, [2, 98])
    lum = np.clip((lum - p2) / max(p98 - p2, 1), 0, 1)
    H, W = lum.shape

    width_m = (BOX["e"] - BOX["w"]) * DEG * MARS_RADIUS_M * math.cos(
        math.radians((BOX["s"] + BOX["n"]) / 2))
    height_m = (BOX["n"] - BOX["s"]) * DEG * MARS_RADIUS_M
    print(f"  ground {width_m / 1000:.2f} x {height_m / 1000:.2f} km "
          f"({width_m / W:.2f} m/px)")

    # -------------------------------------------------------------------- DEM
    print("[2/6] terrain")
    elev = tifffile.imread(RAW / "dem.tif").astype(np.float32)
    if elev.shape != (H, W):
        elev = zoom(elev, (H / elev.shape[0], W / elev.shape[1]), order=1)
    elev = gaussian_filter(elev, sigma=2.5)

    dx = width_m / W
    dy = height_m / H
    gy, gx = np.gradient(elev, dy, dx)
    slope = np.degrees(np.arctan(np.hypot(gx, gy)))

    # hillshade for the basemap
    az, alt = math.radians(315), math.radians(45)
    aspect = np.arctan2(-gx, gy)
    hs = (math.sin(alt) * np.cos(np.radians(slope))
          + math.cos(alt) * np.sin(np.radians(slope)) * np.cos(az - aspect))
    hs = np.clip(hs, 0, 1)

    base = np.clip(lum * (0.72 + 0.52 * hs), 0, 1)
    rgb = np.stack([base * 1.05, base * 0.99, base * 0.93], axis=-1)
    base_img = Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8))
    DISPLAY_W = 1700
    base_img = base_img.resize(
        (DISPLAY_W, int(round(DISPLAY_W * H / W))), Image.LANCZOS)
    base_img.save(PROC / "basemap_ctx.png", optimize=True)
    print(f"  basemap_ctx.png  {base_img.size}")

    # ------------------------------------------------------------ roughness
    print("[3/6] surface roughness")
    rough = uniform_filter(lum, size=9)
    rough = uniform_filter(lum * lum, size=9) - rough * rough
    rough = np.sqrt(np.clip(rough, 0, None))
    rough = gaussian_filter(rough, sigma=1.2)
    rp = np.percentile(rough, [50, 90, 97, 99])
    print(f"  roughness p50={rp[0]:.4f} p90={rp[1]:.4f} p97={rp[2]:.4f} p99={rp[3]:.4f}")
    rough_n = np.clip(rough / max(rp[2], 1e-6), 0, 1)
    sp = np.percentile(slope, [50, 90, 97, 99])
    print(f"  slope deg p50={sp[0]:.2f} p90={sp[1]:.2f} p97={sp[2]:.2f} p99={sp[3]:.2f} "
          f"max={slope.max():.2f}")

    # ------------------------------------------------------------- overlays
    print("[4/6] overlays")
    def save_overlay(arr, name, width=1400):
        im = Image.fromarray(arr)
        im = im.resize((width, int(round(width * H / W))), Image.LANCZOS)
        im.save(PROC / name, optimize=True)
        print(f"  {name}  {im.size}  {(PROC / name).stat().st_size / 1024:.0f} KB")

    slope_rgba = colorize(
        slope, 3, 26,
        [(0, (46, 204, 113)), (0.5, (241, 196, 15)), (1, (231, 76, 60))],
        [(0, 0), (0.15, 90), (1, 205)],
    )
    save_overlay(slope_rgba, "overlay_slope.png")

    rough_rgba = colorize(
        rough_n, 0.25, 1.0,
        [(0, (255, 190, 80)), (0.6, (230, 126, 34)), (1, (150, 60, 30))],
        [(0, 0), (0.3, 70), (1, 170)],
    )
    save_overlay(rough_rgba, "overlay_roughness.png")

    no_go = (slope > 22) | (rough_n > 0.985)
    hazard_rgba = np.zeros((H, W, 4), dtype=np.uint8)
    hazard_rgba[no_go] = (231, 60, 45, 205)
    save_overlay(hazard_rgba, "overlay_hazard.png")
    print(f"  no-go cells {no_go.mean() * 100:.1f}%")

    # ------------------------------------------------------------- route grid
    print("[5/6] route grid")
    nx = max(64, int(round(width_m / GRID_M)))
    ny = max(64, int(round(height_m / GRID_M)))
    slope_g = zoom(slope, (ny / H, nx / W), order=1)
    rough_g = zoom(rough_n, (ny / H, nx / W), order=1)
    elev_g = zoom(elev, (ny / H, nx / W), order=1)

    cn = np.clip(slope_g / 25.0, 0, 1)
    cost = 1.0 + 3.0 * cn + 2.5 * np.clip(rough_g, 0, 1)
    cost = cost + 6.0 * (slope_g > 15)
    cost[slope_g > 22] = 1e6
    cost[rough_g > 0.985] = 1e6

    np.save(PROC / "elevation.npy", elev_g.astype(np.float32))
    np.save(PROC / "slope.npy", slope_g.astype(np.float16))
    np.save(PROC / "roughness.npy", rough_g.astype(np.float16))

    meta = {
        "box": BOX,
        "width_m": width_m,
        "height_m": height_m,
        "grid": [nx, ny],
        "grid_m": GRID_M,
        "basemap_px": [W, H],
        "m_per_px": width_m / W,
        "slope_p50": float(sp[0]),
        "slope_p99": float(sp[3]),
        "rough_p97": float(rp[2]),
        "no_go_fraction": float(no_go.mean()),
        "source": "CTX (Esri Astro) + MOLA/HRSC DEM 200 m/px (NASA Mars Trek)",
    }
    (PROC / "meta.json").write_text(json.dumps(meta, indent=1))
    print("  saved elevation/slope/roughness/cost .npy")

    # -------------------------------------------------------- station insets
    print("[6/6] station close-ups")
    stations = json.loads((RAW / "stations.geojson").read_text())["features"]
    for f in stations:
        if f["properties"]["role"] != "station":
            continue
        sid = f["properties"]["id"].lower()
        lon, lat = f["geometry"]["coordinates"]
        half = 0.0065
        sbox = {"w": lon - half, "e": lon + half, "s": lat - half * 0.75,
                "n": lat + half * 0.75}
        try:
            hi, g, t = mosaic(HIRISE_URL, HIRISE_Z, sbox, max_tiles=40)
            if g >= t * 0.5:
                im = ImageEnhance.Contrast(hi).enhance(1.6)
                im.save(RAW.parent / "stations" / f"{sid}_closeup.png")
                print(f"  {sid}: HiRISE {g}/{t} tiles")
                continue
        except Exception as exc:  # noqa: BLE001
            print(f"  {sid}: HiRISE unavailable ({exc})")
        # fallback: crop the CTX basemap around the station
        px = (lon - BOX["w"]) / (BOX["e"] - BOX["w"]) * W
        py = (BOX["n"] - lat) / (BOX["n"] - BOX["s"]) * H
        half_px = int(0.0065 / (BOX["e"] - BOX["w"]) * W)
        crop = Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8)).crop(
            (int(px - half_px), int(py - half_px * 0.75),
             int(px + half_px), int(py + half_px * 0.75)))
        crop = crop.resize((640, 480), Image.LANCZOS)
        crop.save(RAW.parent / "stations" / f"{sid}_closeup.png")
        print(f"  {sid}: CTX fallback")

    print("\nDone. Layers in data/processed, close-ups in data/stations.")


if __name__ == "__main__":
    main()
