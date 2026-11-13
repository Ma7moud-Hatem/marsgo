"""Suit consumables, radiation, uncertainty intervals, sensitivity analysis, and GO / NO-GO verdict.

Pure scientific domain module: completely free of Streamlit imports.
All thresholds are unified with ``src/config.py`` and grounded in published
references (MSL RAD Hassler et al. 2014; NASA-STD-3001; NASA xEMU PLSS baseline).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from .config import ASSUMPTIONS_LOG, SUIT


@dataclass(frozen=True)
class SuitConfig:
    speed_kmh: float = SUIT["speed_kmh"]
    speed_unc_frac: float = SUIT["speed_unc_frac"]
    eva_cap_h: float = SUIT["eva_cap_h"]
    reserve_frac: float = SUIT["reserve_frac"]
    o2_kg: float = SUIT["o2_kg"]
    o2_rate_kg_h: float = SUIT["o2_rate_kg_h"]
    o2_unc_frac: float = SUIT["o2_unc_frac"]
    water_l: float = SUIT["water_l"]
    water_rate_l_h: float = SUIT["water_rate_l_h"]
    battery_h: float = SUIT["battery_h"]
    radiation_mSv_h: float = SUIT["radiation_mSv_h"]
    spe_radiation_mSv_h: float = SUIT["spe_radiation_mSv_h"]
    career_limit_mSv: float = SUIT["career_limit_mSv"]
    dust_tau_limit: float = SUIT["dust_tau_limit"]
    slope_warn_deg: float = SUIT["slope_warn_deg"]
    slope_nogo_deg: float = SUIT["slope_nogo_deg"]
    rough_warn: float = SUIT["rough_warn"]
    rough_nogo: float = SUIT["rough_nogo"]

    def with_overrides(self, **kwargs: Any) -> "SuitConfig":
        return replace(self, **{k: v for k, v in kwargs.items() if v is not None})


def _constraint(
    key: str,
    label: str,
    status: str,
    value: str,
    limit: str,
    detail: str,
) -> dict[str, str]:
    return {
        "key": key,
        "label": label,
        "status": status,
        "value": value,
        "limit": limit,
        "detail": detail,
    }


def _evaluate_core(
    stats: dict[str, Any],
    cfg: SuitConfig,
    weather: dict[str, Any] | None = None,
    solar_event: bool = False,
    dust_storm: bool = False,
) -> dict[str, Any]:
    """Internal evaluator returning full metrics without recursive sensitivity calls."""
    duration = float(stats["duration_h"])
    dur_min = float(stats.get("duration_min_h", round(duration * (1.0 - cfg.speed_unc_frac), 2)))
    dur_max = float(stats.get("duration_max_h", round(duration * (1.0 + cfg.speed_unc_frac * 1.25), 2)))

    o2_used = duration * cfg.o2_rate_kg_h
    o2_min = dur_min * cfg.o2_rate_kg_h * (1.0 - cfg.o2_unc_frac)
    o2_max = dur_max * cfg.o2_rate_kg_h * (1.0 + cfg.o2_unc_frac)

    water_used = duration * cfg.water_rate_l_h
    water_min = dur_min * cfg.water_rate_l_h * 0.90
    water_max = dur_max * cfg.water_rate_l_h * 1.15

    # Scientific bug fix: do NOT clamp battery_used with min(duration, cfg.battery_h),
    # otherwise battery depletion (>100%) is silently hidden.
    battery_used = duration
    battery_min = dur_min
    battery_max = dur_max

    eff_rad_rate = cfg.spe_radiation_mSv_h if solar_event else cfg.radiation_mSv_h
    dose = duration * eff_rad_rate
    dose_min = dur_min * eff_rad_rate
    dose_max = dur_max * eff_rad_rate

    rows: list[dict[str, Any]] = [
        {
            "key": "o2",
            "label": "O₂ (PLSS Tank)",
            "used": o2_used,
            "used_min": o2_min,
            "used_max": o2_max,
            "capacity": cfg.o2_kg,
            "unit": "kg",
            "decimals": 2,
            "source": "xEMU PLSS Baseline (0.09 kg/h nominal)",
        },
        {
            "key": "water",
            "label": "Cooling & Feedwater",
            "used": water_used,
            "used_min": water_min,
            "used_max": water_max,
            "capacity": cfg.water_l,
            "unit": "L",
            "decimals": 2,
            "source": "SWME Sublimator Loop (0.15 L/h nominal)",
        },
        {
            "key": "battery",
            "label": "PLSS Battery",
            "used": battery_used,
            "used_min": battery_min,
            "used_max": battery_max,
            "capacity": cfg.battery_h,
            "unit": "h",
            "decimals": 2,
            "source": "xEMU High-Energy Li-Ion (8.0 h endurance)",
        },
        {
            "key": "time",
            "label": "EVA Duration",
            "used": duration,
            "used_min": dur_min,
            "used_max": dur_max,
            "capacity": cfg.eva_cap_h,
            "unit": "h",
            "decimals": 2,
            "source": "Flight Rule Duration Cap (+6%/deg uphill penalty)",
        },
    ]
    for r in rows:
        r["frac"] = r["used"] / r["capacity"] if r["capacity"] else 1.0
        r["frac_max"] = r["used_max"] / r["capacity"] if r["capacity"] else 1.0
        r["reserve_frac"] = max(0.0, 1.0 - r["frac"])

    max_used = max(r["frac"] for r in rows)
    reserve_left = max(0.0, 1.0 - max_used)

    tau = None
    if weather:
        tau = weather.get("tau_estimate")
    dust_limit = cfg.dust_tau_limit

    constraints: list[dict[str, str]] = []

    # 1. Solar particle event — hard stop.
    constraints.append(_constraint(
        "solar",
        "Solar particle event",
        "fail" if solar_event else "pass",
        "ACTIVE" if solar_event else "quiet",
        "no event",
        "An SPE forces immediate shelter return; surface dose spikes to ~1.50 mSv/h."
        if solar_event
        else "No SPE reported in the planning window (MSL RAD baseline ~0.03 mSv/h).",
    ))

    # 2. EVA duration vs. the suit cap (including uncertainty range).
    if duration > cfg.eva_cap_h:
        dur_status = "fail"
    elif dur_max > cfg.eva_cap_h or duration > 0.85 * cfg.eva_cap_h:
        dur_status = "warn"
    else:
        dur_status = "pass"
    constraints.append(_constraint(
        "duration",
        "EVA duration",
        dur_status,
        f"{duration:.2f} h ({dur_min:.1f}–{dur_max:.1f} h)",
        f"≤ {cfg.eva_cap_h:.1f} h",
        "Includes ±12% pace uncertainty and +6% time penalty per degree of climb.",
    ))

    # 3. Walk-back reserve (the binding consumable).
    if reserve_left < cfg.reserve_frac:
        res_status = "fail"
    elif reserve_left < cfg.reserve_frac + 0.10:
        res_status = "warn"
    else:
        res_status = "pass"
    binding = max(rows, key=lambda r: r["frac"])
    constraints.append(_constraint(
        "reserve",
        "Walk-back reserve",
        res_status,
        f"{reserve_left * 100:.0f}%",
        f"≥ {cfg.reserve_frac * 100:.0f}%",
        f"Binding consumable: {binding['label']} at {binding['frac'] * 100:.0f}% used.",
    ))

    # 4. Terrain severity actually sampled along the route (Unified threshold cfg.slope_nogo_deg).
    slope_p95 = float(stats.get("slope_p95", 0.0))
    slope_max = float(stats.get("slope_max", 0.0))
    hazards = int(stats.get("hazard_crossings", stats.get("hazard_samples", 0)))
    if hazards > 0 or slope_max > cfg.slope_nogo_deg:
        terr_status = "fail"
        terr_detail = (
            f"{hazards} no-go sample(s) on the line; peak slope {slope_max:.1f}° "
            f"(limit ≤ {cfg.slope_nogo_deg:.0f}°)."
        )
    elif slope_p95 > cfg.slope_warn_deg:
        terr_status = "warn"
        terr_detail = (
            f"Sustained slope {slope_p95:.1f}° exceeds the {cfg.slope_warn_deg:.0f}° comfort limit."
        )
    else:
        terr_status = "pass"
        terr_detail = (
            f"Route avoids mapped no-go cells (peak {slope_max:.1f}° ≤ {cfg.slope_nogo_deg:.0f}°)."
        )
    constraints.append(_constraint(
        "terrain",
        "Terrain & Slope",
        terr_status,
        f"{slope_p95:.1f}° p95 (max {slope_max:.1f}°)",
        f"≤ {cfg.slope_nogo_deg:.0f}° max",
        terr_detail,
    ))

    # 5. Atmospheric opacity.
    if dust_storm:
        dust_status = "fail"
        dust_detail = "Crew-commanded dust-storm hold. Visibility and solar power degrade."
    elif tau is not None and tau > dust_limit:
        dust_status = "fail"
        dust_detail = f"Opacity τ={tau:.1f} exceeds the τ={dust_limit:.1f} limit."
    elif tau is not None and tau > 0.7 * dust_limit:
        dust_status = "warn"
        dust_detail = f"Opacity τ={tau:.1f} is rising but below the limit."
    else:
        dust_status = "pass"
        dust_detail = "Atmosphere within the optical depth limit."
    dust_value = "STORM" if dust_storm else (
        f"τ={tau:.1f}" if tau is not None else "n/a"
    )
    constraints.append(_constraint(
        "dust",
        "Dust opacity",
        dust_status,
        dust_value,
        f"τ ≤ {dust_limit:.1f}",
        dust_detail,
    ))

    # 6. Radiation dose (referenced to MSL RAD & NASA-STD-3001).
    career_frac = dose / cfg.career_limit_mSv if cfg.career_limit_mSv else 0.0
    constraints.append(_constraint(
        "radiation",
        "Radiation dose (MSL RAD)",
        "fail" if solar_event else ("warn" if career_frac > 0.05 else "pass"),
        f"{dose:.3f} mSv ({dose_min:.3f}–{dose_max:.3f})",
        f"{cfg.career_limit_mSv:.0f} mSv career",
        f"{career_frac * 100:.2f}% of NASA-STD-3001 career limit (@ {eff_rad_rate:.2f} mSv/h).",
    ))

    order = ["solar", "duration", "reserve", "terrain", "dust", "radiation"]
    constraints.sort(key=lambda c: order.index(c["key"]))
    fails = [c for c in constraints if c["status"] == "fail"]
    warnings = [c for c in constraints if c["status"] == "warn"]

    if fails:
        first = fails[0]
        verdict = "NO-GO"
        reason = f"{first['label']}: {first['value']} – {first['detail']}"
    else:
        verdict = "GO"
        reason = "All hard constraints pass."
        if warnings:
            reason += f" {len(warnings)} warning(s) to watch."

    return {
        "verdict": verdict,
        "reason": reason,
        "constraints": constraints,
        "consumables": rows,
        "duration_h": duration,
        "duration_range_h": (dur_min, dur_max),
        "o2_range_kg": (round(o2_min, 3), round(o2_max, 3)),
        "water_range_l": (round(water_min, 3), round(water_max, 3)),
        "dose_mSv": dose,
        "dose_range_mSv": (round(dose_min, 4), round(dose_max, 4)),
        "dose_pct_career": career_frac * 100.0,
        "reserve_left": reserve_left,
        "max_used": max_used,
        "warnings": warnings,
        "fails": fails,
        "tau": tau,
    }


def sensitivity_check(
    stats: dict[str, Any],
    cfg: SuitConfig,
    weather: dict[str, Any] | None = None,
    solar_event: bool = False,
    dust_storm: bool = False,
    slope_delta_pct: float = 10.0,
) -> dict[str, Any]:
    """Perturb route slope by +slope_delta_pct (default +10%) and check if GO/NO-GO verdict flips."""
    factor = 1.0 + (slope_delta_pct / 100.0)
    base_eval = _evaluate_core(stats, cfg, weather, solar_event=solar_event, dust_storm=dust_storm)

    s_p95_new = float(stats.get("slope_p95", 0.0)) * factor
    s_max_new = float(stats.get("slope_max", 0.0)) * factor
    dur_base = float(stats["duration_h"])
    extra_dur_factor = 1.0 + (slope_delta_pct / 100.0) * 0.035
    dur_new = dur_base * extra_dur_factor

    perturbed_stats = dict(stats)
    perturbed_stats["slope_p95"] = s_p95_new
    perturbed_stats["slope_max"] = s_max_new
    perturbed_stats["duration_h"] = dur_new
    perturbed_stats["duration_min_h"] = round(dur_new * (1.0 - cfg.speed_unc_frac), 2)
    perturbed_stats["duration_max_h"] = round(dur_new * (1.0 + cfg.speed_unc_frac * 1.25), 2)
    if s_max_new > cfg.slope_nogo_deg:
        perturbed_stats["hazard_crossings"] = max(1, int(stats.get("hazard_crossings", 0)) + 1)

    pert_eval = _evaluate_core(
        perturbed_stats, cfg, weather, solar_event=solar_event, dust_storm=dust_storm,
    )
    verdict_changed = base_eval["verdict"] != pert_eval["verdict"]
    warn_delta = len(pert_eval["warnings"]) - len(base_eval["warnings"])

    if verdict_changed:
        summary = (
            f"⚠️ SENSITIVE: +{slope_delta_pct:.0f}% slope flips verdict from "
            f"{base_eval['verdict']} to {pert_eval['verdict']} "
            f"(peak slope {s_max_new:.1f}°, duration {dur_new:.2f} h)."
        )
    elif warn_delta > 0:
        summary = (
            f"⚡ MARGINAL: +{slope_delta_pct:.0f}% slope keeps {pert_eval['verdict']} "
            f"but adds {warn_delta} warning(s) (peak slope {s_max_new:.1f}°)."
        )
    else:
        summary = (
            f"✅ ROBUST: Verdict remains {pert_eval['verdict']} under +{slope_delta_pct:.0f}% "
            f"slope perturbation (peak {s_max_new:.1f}° ≤ {cfg.slope_nogo_deg:.0f}°, "
            f"reserve {pert_eval['reserve_left'] * 100:.0f}%)."
        )

    return {
        "slope_delta_pct": slope_delta_pct,
        "base_verdict": base_eval["verdict"],
        "perturbed_verdict": pert_eval["verdict"],
        "verdict_flips": verdict_changed,
        "perturbed_slope_max": round(s_max_new, 2),
        "perturbed_slope_p95": round(s_p95_new, 2),
        "perturbed_duration_h": round(dur_new, 2),
        "perturbed_reserve_pct": round(pert_eval["reserve_left"] * 100.0, 1),
        "summary": summary,
    }


def evaluate(
    stats: dict[str, Any],
    cfg: SuitConfig | None = None,
    weather: dict[str, Any] | None = None,
    config_override: SuitConfig | None = None,
    solar_event: bool = False,
    dust_storm: bool = False,
) -> dict[str, Any]:
    """Evaluate a route's statistics against xEMU suit constraints."""
    active_cfg = config_override if isinstance(config_override, SuitConfig) else (cfg or SuitConfig())
    core = _evaluate_core(
        stats,
        active_cfg,
        weather=weather,
        solar_event=solar_event,
        dust_storm=dust_storm,
    )
    core["sensitivity"] = sensitivity_check(
        stats,
        active_cfg,
        weather=weather,
        solar_event=solar_event,
        dust_storm=dust_storm,
        slope_delta_pct=SUIT["sensitivity_slope_pct"],
    )
    core["assumptions"] = ASSUMPTIONS_LOG
    return core


def generate_debrief(
    route_stats: dict[str, Any],
    suit_eval: dict[str, Any],
    stations_visited: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    abort_points: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Generate post-EVA Debrief summary."""
    cons_map = {c["key"]: c for c in suit_eval["consumables"]}
    dur_min, dur_max = suit_eval["duration_range_h"]
    return {
        "verdict": suit_eval["verdict"],
        "reason": suit_eval["reason"],
        "stations_count": len(stations_visited),
        "stations_names": [s["name"] for s in stations_visited],
        "distance_km": round(float(route_stats.get("distance_km", 0.0)), 2),
        "ascent_m": round(float(route_stats.get("ascent_m", 0.0)), 1),
        "descent_m": round(float(route_stats.get("descent_m", 0.0)), 1),
        "duration_h": round(float(suit_eval["duration_h"]), 2),
        "duration_range_str": f"{dur_min:.2f} – {dur_max:.2f} h",
        "o2_used_kg": round(float(cons_map["o2"]["used"]), 3),
        "o2_pct": round(float(cons_map["o2"]["frac"]) * 100.0, 1),
        "water_used_l": round(float(cons_map["water"]["used"]), 2),
        "water_pct": round(float(cons_map["water"]["frac"]) * 100.0, 1),
        "battery_pct": round(float(cons_map["battery"]["frac"]) * 100.0, 1),
        "dose_mSv": round(float(suit_eval["dose_mSv"]), 3),
        "reserve_left_pct": round(float(suit_eval["reserve_left"]) * 100.0, 1),
        "max_slope_deg": round(float(route_stats.get("slope_max", 0.0)), 1),
        "hazard_crossings": int(route_stats.get("hazard_crossings", 0)),
        "max_walkback_km": round(float(route_stats.get("max_walkback_km", 0.0)), 2),
        "max_walkback_h": round(float(route_stats.get("max_walkback_h", 0.0)), 2),
        "sensitivity_summary": suit_eval["sensitivity"]["summary"],
        "abort_checkpoints": len(abort_points or []),
    }


def default_config(**overrides: Any) -> SuitConfig:
    return SuitConfig().with_overrides(**overrides)
