"""Comprehensive scientific & unit test suite for MarsGo (Stage 4: 20 tests).

Validates:
- Unified thresholds in config.py (no 22° vs 25° mismatch)
- Coordinate mapping round-trip & Mars haversine distance
- Surface Texture Index and DEM interpolation disclosure
- Chaikin path smoothing never crosses inf or NO_GO_COST cells
- Route optimization modes (fastest, safest, low_energy, balanced)
- Manual hazard zone injection and automatic rerouting
- Abort / walk-back checkpoint calculations
- Suit consumables, battery unclamped calculation, uncertainty intervals, and sensitivity (+10% slope)
- Offline data provenance & automated performance targets
"""

from __future__ import annotations

import ast
import math
import time
from pathlib import Path

import numpy as np

from src import config, data, routing, suit, terrain, weather
from src.config import BOX, PERF_TARGETS, ROUTE_MODES, SUIT
from src.terrain import NO_GO_COST


def test_suit_module_has_no_streamlit_imports() -> None:
    """Rule check: suit.py must remain 100% free of Streamlit imports."""
    suit_path = Path(suit.__file__).resolve()
    tree = ast.parse(suit_path.read_text(encoding="utf-8"))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    assert not any("streamlit" in mod for mod in imported), f"Forbidden import in suit.py: {imported}"


def test_unified_slope_thresholds_in_config() -> None:
    """Fix verification: config.py defines a single slope_nogo_deg (22.0°) shared by SuitConfig and terrain."""
    cfg = suit.default_config()
    assert SUIT["slope_nogo_deg"] == 22.0
    assert cfg.slope_nogo_deg == SUIT["slope_nogo_deg"]
    assert cfg.slope_warn_deg == SUIT["slope_warn_deg"]


def test_coordinate_roundtrip_lonlat_rc() -> None:
    """lonlat_to_rc and rc_to_lonlat must invert each other to sub-meter accuracy."""
    lon_in = np.array([BOX["w"], (BOX["w"] + BOX["e"]) / 2.0, BOX["e"]])
    lat_in = np.array([BOX["n"], (BOX["s"] + BOX["n"]) / 2.0, BOX["s"]])
    r, c = terrain.lonlat_to_rc(lon_in, lat_in)
    lon_out, lat_out = terrain.rc_to_lonlat(r, c)
    np.testing.assert_allclose(lon_in, lon_out, atol=1e-6)
    np.testing.assert_allclose(lat_in, lat_out, atol=1e-6)


def test_sample_grid_outside_box_returns_nan() -> None:
    """Points outside the Jezero bounding box must return NaN."""
    grid = data.elevation()
    val = terrain.sample_grid(grid, BOX["w"] - 1.0, BOX["n"] + 1.0)
    assert np.isnan(val[0])


def test_mars_haversine_distance_scale() -> None:
    """1 degree of latitude on Mars (R=3,396,190 m) is ~59.27 km."""
    d_m = float(terrain.haversine_m(77.35, 18.0, 77.35, 19.0))
    assert 59_000.0 <= d_m <= 59_500.0


def test_surface_texture_index_and_slope_disclosure() -> None:
    """terrain_at() must expose surface_texture_index and DEM resolution note."""
    st = data.station("S1")
    assert st is not None
    info = terrain.terrain_at(st["lon"], st["lat"])
    assert "surface_texture_index" in info
    assert info["surface_texture_index"] == info["roughness"]
    assert "200" in str(info["slope_resolution_note"])


def test_cost_surface_marks_nogo_cells() -> None:
    """Cells exceeding slope_nogo_deg or rough_nogo must receive NO_GO_COST."""
    cost = terrain.cost_surface(slope_nogo_deg=22.0)
    mask = terrain.no_go_mask(slope_nogo_deg=22.0)
    assert np.all(cost[mask] >= NO_GO_COST)
    assert np.all(cost[~mask] < NO_GO_COST)


def test_manual_hazard_mask_blocks_cells() -> None:
    """build_hazard_mask() must set NO_GO_COST inside the specified radius."""
    st = data.station("S1")
    assert st is not None
    mask = terrain.build_hazard_mask([{"lon": st["lon"], "lat": st["lat"], "radius_m": 120.0}])
    assert mask is not None and mask.any()
    cost = terrain.cost_surface(manual_hazard=mask)
    r, c = terrain.lonlat_to_rc(st["lon"], st["lat"])
    assert cost[int(round(float(r))), int(round(float(c)))] >= NO_GO_COST


def test_route_never_crosses_nogo_or_inf_cells() -> None:
    """Critical invariant: planned route must never step on a NO_GO_COST or inf cell."""
    route = routing.plan_route(("S1", "S2", "S3"), speed_kmh=1.5, mode="balanced")
    assert route is not None
    assert route.stats["hazard_crossings"] == 0

    cost = terrain.cost_surface()
    ny, nx = cost.shape
    r, c = terrain.lonlat_to_rc(route.lons, route.lats)
    ri = np.clip(np.round(r).astype(int), 0, ny - 1)
    ci = np.clip(np.round(c).astype(int), 0, nx - 1)
    sampled_costs = cost[ri, ci]
    assert np.all(np.isfinite(sampled_costs))
    assert np.all(sampled_costs < NO_GO_COST)


def test_smoothing_fallback_when_corner_touches_inf_or_nogo() -> None:
    """When a smoothed path clips an inf/NO_GO_COST cell, _path_violates_nogo must return True."""
    ny, nx = terrain.grid_shape()
    synthetic_cost = np.ones((ny, nx), dtype=np.float32)
    synthetic_cost[100, 100] = np.inf
    rows = np.array([99.0, 100.0, 101.0])
    cols = np.array([99.0, 100.0, 101.0])
    assert routing._path_violates_nogo(
        rows, cols, synthetic_cost, SUIT["slope_nogo_deg"], SUIT["rough_nogo"]
    ) is True


def test_three_route_modes_produce_distinct_characteristics() -> None:
    """Stage 2: fastest, safest, and low_energy modes must all solve and respect trade-offs."""
    comp = routing.compare_routes(("S1", "S2", "S3"), speed_kmh=1.5, modes=("fastest", "safest", "low_energy"))
    assert set(comp.keys()) == {"fastest", "safest", "low_energy"}
    for m_key, r in comp.items():
        assert r.stats["hazard_crossings"] == 0, f"Mode {m_key} crossed a hazard!"
    assert comp["fastest"].stats["duration_h"] <= comp["safest"].stats["duration_h"]


def test_manual_hazard_reroutes_cleanly() -> None:
    """Injecting a manual hazard on the midpoint of a route forces a safe detour with 0 crossings."""
    base_route = routing.plan_route(("S1", "S2"), speed_kmh=1.5)
    assert base_route is not None
    mid_idx = len(base_route.lons) // 2
    hz = [{"lon": float(base_route.lons[mid_idx]), "lat": float(base_route.lats[mid_idx]), "radius_m": 150.0}]
    detour = routing.plan_route(("S1", "S2"), speed_kmh=1.5, hazard_zones=hz)
    assert detour is not None
    assert detour.stats["hazard_crossings"] == 0
    assert detour.stats["distance_km"] != base_route.stats["distance_km"]


def test_abort_walkback_points_computed() -> None:
    """Stage 2: route must include abort/walk-back checkpoints with positive distances and bearings."""
    route = routing.plan_route(("S1", "S2", "S3"), speed_kmh=1.5)
    assert route is not None
    assert len(route.abort_points) >= 4
    for pt in route.abort_points:
        assert pt["walkback_km"] >= 0.0
        assert pt["walkback_h"] >= 0.0
        assert 0.0 <= pt["bearing_deg"] < 360.0


def test_nominal_suit_evaluation_is_go() -> None:
    """Nominal S1->S2->S3 route under default config and weather must return GO."""
    route = routing.plan_route(("S1", "S2", "S3"), speed_kmh=1.5)
    assert route is not None
    res = suit.evaluate(route.stats, suit.default_config(), weather.conditions())
    assert res["verdict"] == "GO"
    assert res["duration_range_h"][0] < res["duration_h"] < res["duration_range_h"][1]


def test_battery_depletion_is_not_clamped() -> None:
    """Fix verification: if duration exceeds battery_h, battery fraction must exceed 1.0 and trigger NO-GO."""
    fake_stats = {
        "duration_h": 9.5,
        "slope_p95": 4.0,
        "slope_max": 8.0,
        "hazard_crossings": 0,
    }
    cfg = suit.default_config(eva_cap_h=12.0, o2_kg=5.0, water_l=10.0, battery_h=8.0)
    res = suit.evaluate(fake_stats, cfg, weather.conditions())
    batt_row = next(r for r in res["consumables"] if r["key"] == "battery")
    assert math.isclose(batt_row["used"], 9.5, rel_tol=1e-5)
    assert batt_row["frac"] > 1.0
    assert res["verdict"] == "NO-GO"


def test_unified_slope_limit_triggers_nogo_above_22_deg() -> None:
    """Fix verification: a route with peak slope 23.5° (> 22.0° config limit) must fail terrain check."""
    steep_stats = {
        "duration_h": 3.0,
        "slope_p95": 14.0,
        "slope_max": 23.5,
        "hazard_crossings": 0,
    }
    res = suit.evaluate(steep_stats, suit.default_config(), weather.conditions())
    assert res["verdict"] == "NO-GO"
    terr_c = next(c for c in res["constraints"] if c["key"] == "terrain")
    assert terr_c["status"] == "fail"


def test_sensitivity_analysis_detects_borderline_slope_flip() -> None:
    """Stage 1: if peak slope is 20.5°, a +10% slope increase (22.55° > 22.0°) must flip GO to NO-GO."""
    borderline_stats = {
        "duration_h": 3.2,
        "slope_p95": 13.0,
        "slope_max": 20.5,
        "hazard_crossings": 0,
    }
    sens = suit.sensitivity_check(borderline_stats, suit.default_config(), slope_delta_pct=10.0)
    assert sens["base_verdict"] == "GO"
    assert sens["perturbed_verdict"] == "NO-GO"
    assert sens["verdict_flips"] is True


def test_solar_event_and_dust_storm_trigger_nogo() -> None:
    """Off-nominal SPE and dust storm flags must force NO-GO and increase radiation dose on SPE."""
    route = routing.plan_route(("S1", "S2"), speed_kmh=1.5)
    assert route is not None
    cfg = suit.default_config()
    w = weather.conditions()
    nom = suit.evaluate(route.stats, cfg, w)
    spe = suit.evaluate(route.stats, cfg, w, solar_event=True)
    dust = suit.evaluate(route.stats, cfg, w, dust_storm=True)
    assert spe["verdict"] == "NO-GO"
    assert dust["verdict"] == "NO-GO"
    assert spe["dose_mSv"] > nom["dose_mSv"] * 10.0


def test_debrief_generation_and_provenance() -> None:
    """Stage 6: generate_debrief() and provenance_records() return complete structured data."""
    route = routing.plan_route(("S1", "S2"), speed_kmh=1.5)
    assert route is not None
    res = suit.evaluate(route.stats, suit.default_config(), weather.conditions())
    sts = [data.station("S1"), data.station("S2")]
    debrief = suit.generate_debrief(route.stats, res, [s for s in sts if s], route.abort_points)
    assert debrief["verdict"] == "GO"
    assert debrief["stations_count"] == 2
    assert len(data.provenance_records()) >= 5


def test_performance_targets_met() -> None:
    """Stage 3: verify automated performance targets from config.PERF_TARGETS."""
    t0 = time.perf_counter()
    _ = terrain.cost_surface()
    cost_dt = time.perf_counter() - t0
    assert cost_dt <= PERF_TARGETS["cost_surface_s"]
