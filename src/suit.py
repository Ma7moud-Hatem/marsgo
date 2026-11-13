"""Suit consumables, radiation, and the GO / NO-GO verdict.

All numbers are planning assumptions for the demo, not flight rules. They are
editable from the sidebar and shown with their units in the UI.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from .config import SUIT


@dataclass(frozen=True)
class SuitConfig:
    speed_kmh: float = SUIT["speed_kmh"]
    eva_cap_h: float = SUIT["eva_cap_h"]
    reserve_frac: float = SUIT["reserve_frac"]
    o2_kg: float = SUIT["o2_kg"]
    o2_rate_kg_h: float = SUIT["o2_rate_kg_h"]
    water_l: float = SUIT["water_l"]
    water_rate_l_h: float = SUIT["water_rate_l_h"]
    battery_h: float = SUIT["battery_h"]
    radiation_mSv_h: float = SUIT["radiation_mSv_h"]
    career_limit_mSv: float = SUIT["career_limit_mSv"]
    dust_tau_limit: float = SUIT["dust_tau_limit"]
    slope_warn_deg: float = SUIT["slope_warn_deg"]
    slope_nogo_deg: float = SUIT["slope_nogo_deg"]

    def with_overrides(self, **kwargs) -> "SuitConfig":
        return replace(self, **{k: v for k, v in kwargs.items() if v is not None})


def _constraint(key, label, status, value, limit, detail):
    return {
        "key": key,
        "label": label,
        "status": status,
        "value": value,
        "limit": limit,
        "detail": detail,
    }


def evaluate(
    stats: dict,
    cfg: SuitConfig,
    weather: dict | None = None,
    solar_event: bool = False,
    dust_storm: bool = False,
) -> dict:
    duration = float(stats["duration_h"])
    o2_used = duration * cfg.o2_rate_kg_h
    water_used = duration * cfg.water_rate_l_h
    battery_used = min(duration, cfg.battery_h)
    dose = duration * cfg.radiation_mSv_h

    rows = [
        {
            "key": "o2",
            "label": "O₂",
            "used": o2_used,
            "capacity": cfg.o2_kg,
            "unit": "kg",
            "decimals": 2,
        },
        {
            "key": "water",
            "label": "Water",
            "used": water_used,
            "capacity": cfg.water_l,
            "unit": "L",
            "decimals": 2,
        },
        {
            "key": "battery",
            "label": "Battery",
            "used": battery_used,
            "capacity": cfg.battery_h,
            "unit": "h",
            "decimals": 1,
        },
        {
            "key": "time",
            "label": "EVA time",
            "used": duration,
            "capacity": cfg.eva_cap_h,
            "unit": "h",
            "decimals": 2,
        },
    ]
    for r in rows:
        r["frac"] = r["used"] / r["capacity"] if r["capacity"] else 1.0
        r["reserve_frac"] = max(0.0, 1.0 - r["frac"])

    max_used = max(r["frac"] for r in rows)
    reserve_left = max(0.0, 1.0 - max_used)

    tau = None
    if weather:
        tau = weather.get("tau_estimate")
    dust_limit = cfg.dust_tau_limit

    constraints = []

    # 1. Solar particle event — hard stop.
    constraints.append(_constraint(
        "solar", "Solar particle event",
        "fail" if solar_event else "pass",
        "ACTIVE" if solar_event else "quiet",
        "no event",
        "An SPE forces return to the habitat; surface dose accumulates too fast."
        if solar_event else "No SPE reported in the planning window.",
    ))

    # 2. EVA duration vs. the suit cap.
    if duration > cfg.eva_cap_h:
        dur_status = "fail"
    elif duration > 0.85 * cfg.eva_cap_h:
        dur_status = "warn"
    else:
        dur_status = "pass"
    constraints.append(_constraint(
        "duration", "EVA duration",
        dur_status, f"{duration:.2f} h", f"≤ {cfg.eva_cap_h:.1f} h",
        "Walk time includes a 6% time penalty per degree of climb.",
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
        "reserve", "Walk-back reserve",
        res_status, f"{reserve_left * 100:.0f}%", f"≥ {cfg.reserve_frac * 100:.0f}%",
        f"Binding consumable: {binding['label']} at {binding['frac'] * 100:.0f}% used.",
    ))

    # 4. Terrain severity actually sampled along the route.
    slope_p95 = float(stats.get("slope_p95", 0.0))
    slope_max = float(stats.get("slope_max", 0.0))
    hazards = int(stats.get("hazard_crossings", stats.get("hazard_samples", 0)))
    if hazards > 0 or slope_max > 25.0:
        terr_status = "fail"
        terr_detail = (
            f"{hazards} no-go sample(s) on the line; peak slope {slope_max:.1f}°."
        )
    elif slope_p95 > cfg.slope_warn_deg:
        terr_status = "warn"
        terr_detail = f"Sustained slope {slope_p95:.1f}° is above the comfort limit."
    else:
        terr_status = "pass"
        terr_detail = "Route avoids the mapped no-go cells."
    constraints.append(_constraint(
        "terrain", "Terrain",
        terr_status, f"{slope_p95:.1f}° sustained", f"≤ {cfg.slope_warn_deg:.0f}°",
        terr_detail,
    ))

    # 5. Atmospheric opacity.
    if dust_storm:
        dust_status = "fail"
        dust_detail = "Crew-commanded dust-storm hold. Visibility and solar power degrade."
    elif tau is not None and tau > dust_limit:
        dust_status = "fail"
        dust_detail = f"Opacity τ≈{tau:.1f} exceeds the τ={dust_limit:.1f} limit."
    elif tau is not None and tau > 0.7 * dust_limit:
        dust_status = "warn"
        dust_detail = f"Opacity τ≈{tau:.1f} is rising but below the limit."
    else:
        dust_status = "pass"
        dust_detail = "Atmosphere within the dust limit."
    dust_value = "STORM" if dust_storm else (
        f"τ≈{tau:.1f}" if tau is not None else "n/a"
    )
    constraints.append(_constraint(
        "dust", "Dust opacity",
        dust_status, dust_value, f"τ ≤ {dust_limit:.1f}",
        dust_detail,
    ))

    # Radiation is tracked but does not fail a single EVA at these rates.
    career_frac = dose / cfg.career_limit_mSv
    constraints.append(_constraint(
        "radiation", "Radiation dose",
        "warn" if career_frac > 0.05 else "pass",
        f"{dose:.3f} mSv", f"{cfg.career_limit_mSv:.0f} mSv career",
        f"{career_frac * 100:.2f}% of the career limit for this EVA.",
    ))

    order = ["solar", "duration", "reserve", "terrain", "dust", "radiation"]
    constraints.sort(key=lambda c: order.index(c["key"]))
    fails = [c for c in constraints if c["status"] == "fail"]
    warnings = [c for c in constraints if c["status"] == "warn"]

    if fails:
        first = fails[0]
        verdict = "NO-GO"
        reason = f"{first['label']}: {first['value']} — {first['detail']}"
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
        "dose_mSv": dose,
        "dose_pct_career": career_frac * 100.0,
        "reserve_left": reserve_left,
        "max_used": max_used,
        "warnings": warnings,
        "fails": fails,
        "tau": tau,
    }


def default_config(**overrides) -> SuitConfig:
    return SuitConfig().with_overrides(**overrides)
