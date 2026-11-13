"""Fast deployment smoke test.

Run from the repo root:

    .venv/bin/python scripts/smoke_test.py

No network access is required or performed.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import data, routing, suit, weather  # noqa: E402
from src.config import BOX, PROC, RAW  # noqa: E402


def check(condition: bool, label: str, detail: str = "") -> None:
    mark = "PASS" if condition else "FAIL"
    print(f"[{mark}] {label}" + (f" — {detail}" if detail else ""))
    if not condition:
        raise SystemExit(1)


def main() -> None:
    print("MarsGo smoke test\n")

    required = [
        RAW / "stations.geojson",
        RAW / "traverse.geojson",
        RAW / "geology.geojson",
        RAW / "weather_snapshot.json",
        PROC / "basemap_ctx.png",
        PROC / "overlay_hazard.png",
        PROC / "slope.npy",
        PROC / "roughness.npy",
        PROC / "elevation.npy",
        PROC / "meta.json",
    ]
    for path in required:
        check(path.exists() and path.stat().st_size > 0, f"cache {path.name}",
              f"{path.stat().st_size / 1024:.0f} KB" if path.exists() else "missing")

    stations = {s["id"]: s for s in data.stations()}
    check({"START", "S1", "S2", "S3"} <= set(stations), "heritage stations",
          ", ".join(sorted(stations)))

    for sid in ("S1", "S2", "S3"):
        p = data.closeup_path(sid)
        check(p is not None, f"{sid} HiRISE close-up")
        pov = data.pov_image(sid)
        check(pov is not None, f"{sid} Perseverance POV")
        if pov:
            check(pov[0].size[0] >= 800, f"{sid} POV resolution",
                  f"{pov[0].size[0]}x{pov[0].size[1]}")

    unit = data.unit_at(stations["S3"]["lon"], stations["S3"]["lat"])
    check(unit is not None, "point-in-polygon geology lookup",
          unit.get("symbol", "?") if unit else "none")

    route = routing.plan_route(("S1", "S2", "S3"), 1.5)
    check(route is not None, "route solves")
    assert route is not None
    s = route.stats
    check(2.0 <= s["distance_km"] <= 8.0, "route distance",
          f"{s['distance_km']:.2f} km")
    check(s["duration_h"] <= 6.0, "route duration", f"{s['duration_h']:.2f} h")
    check(s["hazard_crossings"] == 0, "route avoids no-go cells",
          f"{s['hazard_crossings']} crossings")

    w = weather.conditions()
    cfg = suit.default_config()
    nominal = suit.evaluate(s, cfg, w)
    check(nominal["verdict"] == "GO", "nominal verdict", nominal["verdict"])

    dust = suit.evaluate(s, cfg, w, dust_storm=True)
    check(dust["verdict"] == "NO-GO", "dust-storm verdict", dust["verdict"])

    short = suit.evaluate(s, cfg.with_overrides(eva_cap_h=2.0), w)
    check(short["verdict"] == "NO-GO", "2 h cap verdict", short["verdict"])

    spe = suit.evaluate(s, cfg, w, solar_event=True)
    check(spe["verdict"] == "NO-GO", "solar-event verdict", spe["verdict"])

    meta = data.meta()
    check(meta["box"] == BOX, "mission box matches config")
    check(meta["grid_m"] == 10.0, "route grid", f"{meta['grid_m']:.0f} m")

    print("\nAll checks passed. App is deployable.")


if __name__ == "__main__":
    main()
