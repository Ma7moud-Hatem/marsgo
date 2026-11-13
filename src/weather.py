"""Atmospheric conditions from the cached MSL REMS snapshot.

REMS is at Gale Crater, so this is an analog station, not Jezero weather. The UI
labels that explicitly.
"""

from __future__ import annotations

from . import data

TAU_BY_OPACITY = {
    "sunny": 0.5,
    "clear": 0.5,
    "cloudy": 1.2,
    "dusty": 2.6,
    "storm": 4.0,
}


def _f(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def conditions() -> dict:
    snap = data.weather()
    recent = snap.get("recent") or []
    latest = snap.get("latest") or (recent[-1] if recent else {})
    opacity = str(latest.get("opacity") or "unknown")
    tau = TAU_BY_OPACITY.get(opacity.strip().lower(), 0.8)

    return {
        "source": snap.get("source", "MSL REMS (Gale Crater analog)"),
        "sol": str(latest.get("sol", "—")),
        "earth_date": latest.get("terrestrial_date", "—"),
        "season": latest.get("season", "—"),
        "tmin_c": _f(latest.get("min_temp_c"), -70.0),
        "tmax_c": _f(latest.get("max_temp_c"), -5.0),
        "pressure_pa": _f(latest.get("pressure_pa"), 780.0),
        "opacity": opacity,
        "tau_estimate": tau,
        "is_analog": True,
        "recent": recent,
        "note": "Gale Crater analog — not a Jezero measurement.",
    }


def chip_html(w: dict) -> str:
    return (
        f'<span class="chip"><b>Sol {w["sol"]}</b> · '
        f'{w["tmin_c"]:.0f}…{w["tmax_c"]:.0f} °C · '
        f'{w["pressure_pa"]:.0f} Pa · {w["opacity"]}</span>'
    )
