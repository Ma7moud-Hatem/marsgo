"""Fast deployment smoke test and automated performance benchmark.

Run from the repo root:

    python scripts/smoke_test.py

No network access is required or performed.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import data, routing, suit, terrain, weather  # noqa: E402
from src.config import BOX, PERF_TARGETS, PROC, RAW, SUIT  # noqa: E402


def check(condition: bool, label: str, detail: str = "") -> None:
    mark = "PASS" if condition else "FAIL"
    print(f"[{mark}] {label}" + (f" - {detail}" if detail else ""))
    if not condition:
        raise SystemExit(1)


def main() -> None:
    print("MarsGo smoke test & scientific audit\n")

    check((PROC / "elevation.npy").exists(), "elevation.npy exists")
    check((PROC / "slope.npy").exists(), "slope.npy exists")
    check((PROC / "roughness.npy").exists(), "roughness.npy exists")
    check((RAW / "geology.geojson").exists(), "geology.geojson exists")
    check((RAW / "stations.geojson").exists(), "stations.geojson exists")

    t0 = time.perf_counter()
    stations = data.load_stations()
    _ = data.elevation()
    _ = data.slope()
    _ = data.roughness()
    load_dt = time.perf_counter() - t0
    check(len(stations) >= 3, "stations loaded", f"{len(stations)} stations")
    check(
        load_dt <= PERF_TARGETS["data_load_s"],
        "data load performance target",
        f"{load_dt:.3f} s <= {PERF_TARGETS['data_load_s']:.2f} s",
    )

    for sid in ["S1", "S2", "S3"]:
        pov = data.load_station_pov(sid)
        check(len(pov) > 0, f"{sid} POV image loaded")
        check(
            pov[0].size[0] >= 800,
            f"{sid} POV resolution",
            f"{pov[0].size[0]}x{pov[0].size[1]}",
        )

    unit = data.unit_at(stations["S3"]["lon"], stations["S3"]["lat"])
    check(
        unit is not None,
        "point-in-polygon geology lookup",
        unit.get("symbol", "?") if unit else "none",
    )

    t1 = time.perf_counter()
    route = routing.plan_route(("S1", "S2", "S3"), 1.5, mode="balanced")
    route_dt = time.perf_counter() - t1
    check(route is not None, "route solves")
    assert route is not None
    check(
        route_dt <= PERF_TARGETS["route_plan_s"],
        "route solve performance target",
        f"{route_dt:.3f} s <= {PERF_TARGETS['route_plan_s']:.2f} s",
    )
    s = route.stats
    check(
        2.0 <= s["distance_km"] <= 8.0,
        "route distance",
        f"{s['distance_km']:.2f} km",
    )
    check(
        s["duration_h"] <= 6.0,
        "route duration",
        f"{s['duration_h']:.2f} h ({s['duration_min_h']:.2f}-{s['duration_max_h']:.2f} h)",
    )
    check(
        s["hazard_crossings"] == 0,
        "route avoids no-go cells",
        f"{s['hazard_crossings']} crossings",
    )
    check(
        len(route.abort_points) >= 4,
        "abort / walk-back checkpoints computed",
        f"{len(route.abort_points)} checkpoints",
    )

    check(
        SUIT["slope_nogo_deg"] == 22.0,
        "unified slope_nogo_deg threshold in config.py",
        f"{SUIT['slope_nogo_deg']} deg",
    )
    w = weather.conditions()
    cfg = suit.default_config()
    t2 = time.perf_counter()
    nominal = suit.evaluate(s, cfg, w)
    eval_dt = time.perf_counter() - t2
    check(nominal["verdict"] == "GO", "nominal verdict", nominal["verdict"])
    check(
        eval_dt <= PERF_TARGETS["suit_eval_s"],
        "suit evaluation performance target",
        f"{eval_dt * 1000:.2f} ms",
    )
    check("sensitivity" in nominal, "sensitivity analysis included", nominal["sensitivity"]["summary"])

    dust = suit.evaluate(s, cfg, w, dust_storm=True)
    check(dust["verdict"] == "NO-GO", "dust-storm verdict", dust["verdict"])

    short = suit.evaluate(s, cfg, w, cfg.with_overrides(eva_cap_h=2.0))
    check(short["verdict"] == "NO-GO", "2 h cap verdict", short["verdict"])

    spe = suit.evaluate(s, cfg, w, solar_event=True)
    check(spe["verdict"] == "NO-GO", "solar-event verdict", spe["verdict"])

    meta = data.meta()
    check(meta["box"] == BOX, "mission box matches config")
    check(meta["grid_m"] == 10.0, "route grid", f"{meta['grid_m']:.0f} m")

    print("\nAll checks passed. App is deployable.")


if __name__ == "__main__":
    main()
