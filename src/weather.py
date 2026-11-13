"""Atmospheric conditions from the cached MSL REMS snapshot.

REMS is at Gale Crater, so this is an analog station, not Jezero weather. The UI
labels that explicitly alongside MEDA reference context.
"""

from __future__ import annotations

from typing import Any

from . import data


TAU_BY_OPACITY: dict[str, float] = {
    "sunny": 0.5,
    "clear": 0.5,
    "cloudy": 1.2,
    "dusty": 2.6,
    "storm": 4.0,
}


def _f(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def conditions() -> dict[str, Any]:
    """Return structured sol weather telemetry from the offline snapshot."""
    snap = data.weather()
    recent = snap.get("recent") or []
    latest = snap.get("latest") or (recent[-1] if recent else {})
    opacity = str(latest.get("opacity") or "Sunny")
    tau = TAU_BY_OPACITY.get(opacity.strip().lower(), 0.8)

    return {
        "source": snap.get("source", "MSL REMS (Gale Crater analog)"),
        "sol": str(latest.get("sol", "4995")),
        "earth_date": str(latest.get("terrestrial_date", "2026-08-25")),
        "season": str(latest.get("season", "Month 12")),
        "tmin_c": _f(latest.get("min_temp_c"), -71.0),
        "tmax_c": _f(latest.get("max_temp_c"), -5.0),
        "pressure_pa": _f(latest.get("pressure_pa"), 777.0),
        "opacity": opacity,
        "tau_estimate": tau,
        "is_analog": True,
        "recent": recent,
        "note": "Gale Crater analog (MSL REMS) — cached offline.",
    }


def chip_html(w: dict[str, Any]) -> str:
    """Render a compact telemetry chip for the sticky Mission Control header."""
    return (
        f'<span class="chip"><b>Sol {w["sol"]}</b> · '
        f'{w["tmin_c"]:.0f}…{w["tmax_c"]:.0f} °C · '
        f'{w["pressure_pa"]:.0f} Pa · {w["opacity"]} (τ≈{w["tau_estimate"]:.1f})</span>'
    )
