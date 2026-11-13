"""Presentation helpers: Mission Control header, KPI cards, elevation SVG, station cards, and debrief export."""

from __future__ import annotations

import html
from typing import Any

import numpy as np

from .config import ASSUMPTIONS_LOG, COLORS, DATA_PROVENANCE, GEOLOGY_COLORS, SUIT
from .theme import MISSION_CONTROL_CSS, inject_theme, t

CSS = MISSION_CONTROL_CSS


def inject_css(st_module: Any = None) -> None:
    """Inject Mission Control CSS into Streamlit."""
    if st_module is None:
        import streamlit as st_mod
        st_module = st_mod
    inject_theme(st_module)


def fmt_duration(hours: float) -> str:
    total = max(0, int(round(hours * 60)))
    return f"{total // 60} h {total % 60:02d} m"


def status_icon(status: str) -> str:
    return {"pass": "●", "warn": "▲", "fail": "■"}.get(status, "•")


def mission_header_html(
    verdict: str | None,
    weather_chip: str,
    lang: str = "en",
) -> str:
    """Sticky Mission Control header with mission name, Sol, weather, resolution chips, and pulsing GO/NO-GO badge."""
    verdict_badge_str = ""
    if verdict:
        cls = "go" if verdict == "GO" else "nogo"
        icon = "🟢" if verdict == "GO" else "🔴"
        verdict_badge_str = (
            f'<span class="verdict-pill {cls}">{icon} {html.escape(verdict)}</span>'
        )
    tagline = t("tagline", lang)
    slope_label = "DEM 200m→10m (Est. Slope)" if lang == "en" else "ميل تقديري (DEM 200m→10m)"
    tex_label = "Surface Texture Index (CTX 4.8m)" if lang == "en" else "مؤشر نسيج السطح (CTX 4.8m)"
    return (
        f'<div class="mg-head">'
        f'<div class="mg-brand">'
        f'<div class="name">Mars<span>Go</span></div>'
        f'<div class="tag">{html.escape(tagline)}</div>'
        f'</div>'
        f'<div class="mg-meta">'
        f'{verdict_badge_str}'
        f'{weather_chip}'
        f'<span class="chip">{html.escape(tex_label)}</span>'
        f'<span class="chip warn-chip" title="Interpolated from 200 m/px MOLA/HRSC DEM">'
        f'⚠️ {html.escape(slope_label)}</span>'
        f'</div></div>'
    )


def verdict_badge(verdict: str, reason: str, sensitivity_note: str = "") -> str:
    cls = "go" if verdict == "GO" else "nogo"
    sens_html = (
        f'<div style="margin-top:8px;padding-top:8px;border-top:1px solid var(--line);'
        f'font-size:12px;color:var(--muted)">{html.escape(sensitivity_note)}</div>'
        if sensitivity_note
        else ""
    )
    return (
        f'<div class="verdict {cls}">'
        f'<div class="label">EVA MISSION VERDICT</div>'
        f'<div class="word">{html.escape(verdict)}</div>'
        f'<div class="why">{html.escape(reason)}</div>'
        f'{sens_html}'
        f'</div>'
    )


def kpi_cards_html(
    route_stats: dict[str, Any],
    suit_eval: dict[str, Any],
    lang: str = "en",
) -> str:
    """Render 6 Mission Control KPI cards with icons, uncertainty ranges, and status borders."""
    dist_km = float(route_stats.get("distance_km", 0.0))
    ascent_m = float(route_stats.get("ascent_m", 0.0))
    dur_h = float(suit_eval.get("duration_h", 0.0))
    dur_min, dur_max = suit_eval.get("duration_range_h", (dur_h * 0.88, dur_h * 1.15))
    o2_min, o2_max = suit_eval.get("o2_range_kg", (0.0, 0.0))
    cons_map = {c["key"]: c for c in suit_eval.get("consumables", [])}
    o2_used = float(cons_map.get("o2", {}).get("used", 0.0))
    o2_cap = float(cons_map.get("o2", {}).get("capacity", 1.0))
    dose = float(suit_eval.get("dose_mSv", 0.0))
    dose_min, dose_max = suit_eval.get("dose_range_mSv", (dose * 0.9, dose * 1.1))
    slope_max = float(route_stats.get("slope_max", 0.0))
    slope_p95 = float(route_stats.get("slope_p95", 0.0))
    reserve_pct = float(suit_eval.get("reserve_left", 0.0)) * 100.0

    c_map = {c["key"]: c["status"] for c in suit_eval.get("constraints", [])}
    st_cls = lambda s: {"pass": "status-go", "warn": "status-warn", "fail": "status-nogo"}.get(s, "status-accent")

    cards = [
        (
            "📏 " + t("kpi_distance", lang),
            f"{dist_km:.2f} km",
            f"↑ {ascent_m:.0f} m climb · {route_stats.get('mode_label', 'Balanced')}",
            "status-accent",
        ),
        (
            "⏱️ " + t("kpi_duration", lang),
            f"{dur_h:.2f} h",
            f"Range: {dur_min:.2f}–{dur_max:.2f} h (±12%)",
            st_cls(c_map.get("duration", "pass")),
        ),
        (
            "🫁 " + t("kpi_o2", lang),
            f"{o2_used:.2f} / {o2_cap:.2f} kg",
            f"Range: {o2_min:.2f}–{o2_max:.2f} kg (±10%)",
            st_cls(c_map.get("reserve", "pass")),
        ),
        (
            "☢️ " + t("kpi_dose", lang),
            f"{dose:.3f} mSv",
            f"Range: {dose_min:.3f}–{dose_max:.3f} mSv (MSL RAD)",
            st_cls(c_map.get("radiation", "pass")),
        ),
        (
            "⛰️ " + t("kpi_slope", lang),
            f"{slope_max:.1f}° max",
            f"p95: {slope_p95:.1f}° (Est. 200m DEM)",
            st_cls(c_map.get("terrain", "pass")),
        ),
        (
            "🛡️ " + t("kpi_reserve", lang),
            f"{reserve_pct:.0f}%",
            f"Max walk-back: {route_stats.get('max_walkback_h', 0.0):.2f} h",
            st_cls(c_map.get("reserve", "pass")),
        ),
    ]

    cells = "".join(
        f'<div class="card {cls}">'
        f'<div class="k"><span>{html.escape(k)}</span></div>'
        f'<div class="v">{html.escape(v)}</div>'
        f'<div class="s">{html.escape(s)}</div>'
        f'</div>'
        for k, v, s, cls in cards
    )
    return f'<div class="grid" style="grid-template-columns:repeat(3,1fr)">{cells}</div>'


def metric_grid(items: list[tuple[str, str, str]], cols: int = 3) -> str:
    cells = "".join(
        f'<div class="card status-accent"><div class="k">{html.escape(k)}</div>'
        f'<div class="v">{html.escape(v)}</div>'
        f'<div class="s">{html.escape(s)}</div></div>'
        for k, v, s in items
    )
    return f'<div class="grid" style="grid-template-columns:repeat({cols},1fr)">{cells}</div>'


def _bar_color(frac: float, reserve_frac: float) -> str:
    limit_frac = 1.0 - reserve_frac
    if frac > limit_frac or frac >= 0.85:
        return COLORS["nogo"]
    if frac >= limit_frac - 0.12 or frac >= 0.68:
        return COLORS["warn"]
    return COLORS["go"]


def suit_bars(consumables: list[dict[str, Any]], reserve_frac: float) -> str:
    """Render green → amber → red consumable progress bars with uncertainty range and reserve marker."""
    out = []
    for r in consumables:
        frac = min(1.0, max(0.0, float(r["frac"])))
        pct = frac * 100.0
        reserve_mark = max(0.0, min(100.0, (1.0 - reserve_frac) * 100.0))
        unit = r["unit"]
        dec = r["decimals"]
        reserve_left = max(0.0, 1.0 - frac) * 100.0
        u_min = r.get("used_min", r["used"])
        u_max = r.get("used_max", r["used"])
        color = _bar_color(frac, reserve_frac)
        out.append(
            f'<div class="bar-row">'
            f'<div class="bar-head">'
            f'<span class="lbl">{html.escape(r["label"])}</span>'
            f'<span class="val">{r["used"]:.{dec}f} ({u_min:.{dec}f}–{u_max:.{dec}f}) / '
            f'{r["capacity"]:.{dec}f} {unit} · {reserve_left:.0f}% left</span>'
            f'</div>'
            f'<div class="bar">'
            f'<div class="fill" style="width:{pct:.1f}%;background:{color}"></div>'
            f'<div class="mark" style="left:{reserve_mark:.1f}%" title="Walk-back reserve threshold"></div>'
            f'</div>'
            f'</div>'
        )
    out.append(
        '<div style="font-size:11px;color:var(--muted);margin-top:-2px">'
        "White vertical line = mandatory walk-back reserve limit. Color transitions: "
        '<span style="color:var(--go)">● Safe</span> → '
        '<span style="color:var(--warn)">▲ Warning</span> → '
        '<span style="color:var(--nogo)">■ Reserve Breach</span>.</div>'
    )
    return "".join(out)


def checklist(constraints: list[dict[str, str]]) -> str:
    rows = []
    for c in constraints:
        rows.append(
            f'<div class="check {c["status"]}">'
            f'<div class="ico">{status_icon(c["status"])}</div>'
            f'<div class="body"><div class="top"><span class="nm">{html.escape(c["label"])}</span>'
            f'<span class="vl">{html.escape(str(c["value"]))} (limit {html.escape(str(c["limit"]))})</span></div>'
            f'<div class="dt">{html.escape(c["detail"])}</div></div></div>'
        )
    return "".join(rows)


def elevation_profile_svg(
    prof: dict[str, np.ndarray],
    legs: list[dict[str, Any]] | None = None,
    slope_warn_deg: float = SUIT["slope_warn_deg"],
) -> str:
    """Render an interactive-style SVG elevation & slope profile chart below the map (Stage 2)."""
    elev = np.asarray(prof.get("elev_m", []), dtype=float)
    slope = np.asarray(prof.get("slope_deg", []), dtype=float)
    cum_km = np.asarray(prof.get("cum_km", []), dtype=float)
    if len(elev) < 2 or len(cum_km) != len(elev):
        return '<div class="card"><div class="s">No elevation profile available.</div></div>'

    valid = np.isfinite(elev)
    if not valid.any():
        return '<div class="card"><div class="s">Elevation data outside bounds.</div></div>'
    elev = np.interp(np.arange(len(elev)), np.flatnonzero(valid), elev[valid])

    w_px, h_px = 860, 185
    pad_l, pad_r, pad_t, pad_b = 58, 24, 24, 34
    plot_w = w_px - pad_l - pad_r
    plot_h = h_px - pad_t - pad_b

    max_km = max(float(cum_km[-1]), 0.01)
    e_min = float(np.min(elev)) - 5.0
    e_max = float(np.max(elev)) + 5.0
    if e_max - e_min < 10.0:
        e_max = e_min + 10.0

    xs = pad_l + (cum_km / max_km) * plot_w
    ys = pad_t + plot_h - ((elev - e_min) / (e_max - e_min)) * plot_h

    pts_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    area_str = f"{pad_l:.1f},{pad_t + plot_h:.1f} " + pts_str + f" {xs[-1]:.1f},{pad_t + plot_h:.1f}"

    warn_circles = []
    for x, y, s in zip(xs[::3], ys[::3], slope[::3]):
        if np.isfinite(s) and s > slope_warn_deg:
            warn_circles.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{COLORS["warn"]}" />'
            )

    station_marks = []
    if legs:
        running_km = 0.0
        for leg in legs[:-1]:
            running_km += float(leg.get("distance_km", 0.0))
            sx = pad_l + (running_km / max_km) * plot_w
            to_id = html.escape(str(leg.get("to_id", "")))
            station_marks.append(
                f'<line x1="{sx:.1f}" y1="{pad_t}" x2="{sx:.1f}" y2="{pad_t + plot_h}" '
                f'stroke="{COLORS["accent"]}" stroke-dasharray="4,4" stroke-width="1.2"/>'
                f'<text x="{sx + 4:.1f}" y="{pad_t + 12}" fill="{COLORS["accent"]}" '
                f'font-family="JetBrains Mono" font-size="10" font-weight="700">{to_id}</text>'
            )

    return f"""
    <div class="card" style="padding:12px 14px;margin-top:8px">
        <div class="k">
            <span>📈 ELEVATION & REGIONAL SLOPE PROFILE (MOLA/HRSC 200 m/px → 10 m GRID)</span>
            <span class="mono">Min {float(np.min(elev)):.0f} m · Max {float(np.max(elev)):.0f} m · Total {max_km:.2f} km</span>
        </div>
        <svg viewBox="0 0 {w_px} {h_px}" width="100%" height="185" style="display:block;overflow:visible">
            <defs>
                <linearGradient id="elevGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="{COLORS['route']}" stop-opacity="0.38"/>
                    <stop offset="100%" stop-color="{COLORS['route']}" stop-opacity="0.02"/>
                </linearGradient>
            </defs>
            <line x1="{pad_l}" y1="{pad_t}" x2="{w_px - pad_r}" y2="{pad_t}" stroke="{COLORS['line']}" stroke-width="1"/>
            <line x1="{pad_l}" y1="{pad_t + plot_h/2:.1f}" x2="{w_px - pad_r}" y2="{pad_t + plot_h/2:.1f}" stroke="{COLORS['line']}" stroke-dasharray="3,3" stroke-width="1"/>
            <line x1="{pad_l}" y1="{pad_t + plot_h}" x2="{w_px - pad_r}" y2="{pad_t + plot_h}" stroke="{COLORS['line']}" stroke-width="1"/>
            <polygon points="{area_str}" fill="url(#elevGrad)" />
            <polyline points="{pts_str}" fill="none" stroke="{COLORS['route']}" stroke-width="2.4" />
            {''.join(warn_circles)}
            {''.join(station_marks)}
            <text x="{pad_l - 6}" y="{pad_t + 4}" text-anchor="end" fill="{COLORS['muted']}" font-family="JetBrains Mono" font-size="10">{e_max:.0f}m</text>
            <text x="{pad_l - 6}" y="{pad_t + plot_h}" text-anchor="end" fill="{COLORS['muted']}" font-family="JetBrains Mono" font-size="10">{e_min:.0f}m</text>
            <text x="{pad_l}" y="{h_px - 8}" fill="{COLORS['muted']}" font-family="JetBrains Mono" font-size="10">0.0 km (START)</text>
            <text x="{w_px - pad_r}" y="{h_px - 8}" text-anchor="end" fill="{COLORS['muted']}" font-family="JetBrains Mono" font-size="10">{max_km:.2f} km (RETURN)</text>
        </svg>
    </div>
    """


def layer_chips(names: list[str]) -> str:
    return '<div class="chips">' + "".join(
        f'<span class="lchip on">{html.escape(n)}</span>' for n in names
    ) + "</div>"


def unified_legend_html(present_symbols: set[str] | None = None) -> str:
    """Unified layer & geology legend with resolution and data provenance (Stages 5 & 6)."""
    geo_items = []
    for symbol, color in GEOLOGY_COLORS.items():
        if present_symbols and symbol not in present_symbols:
            continue
        geo_items.append(
            f'<span class="chip" style="padding:3px 9px;font-size:11px">'
            f'<span style="display:inline-block;width:10px;height:10px;border-radius:3px;'
            f'background:{color};margin-right:5px"></span>{html.escape(symbol)}</span>'
        )
    prov_rows = "".join(
        f'<tr>'
        f'<td style="padding:5px 8px;border-bottom:1px solid var(--line);color:#fff;font-weight:600">{html.escape(p["layer"])}</td>'
        f'<td class="mono" style="padding:5px 8px;border-bottom:1px solid var(--line);color:var(--accent)">{html.escape(p["resolution"])}</td>'
        f'<td style="padding:5px 8px;border-bottom:1px solid var(--line);color:var(--muted)">'
        f'<a href="{html.escape(p["url"])}" target="_blank" style="color:var(--route);text-decoration:none">{html.escape(p["source"])} ↗</a></td>'
        f'</tr>'
        for p in DATA_PROVENANCE
    )
    return (
        f'<div class="card" style="margin-top:8px">'
        f'<div class="k"><span>🗺️ UNIFIED LAYER LEGEND & DATA PROVENANCE</span></div>'
        f'<div style="display:flex;gap:6px;flex-wrap:wrap;margin:6px 0 10px 0">{"".join(geo_items)}</div>'
        f'<table style="width:100%;border-collapse:collapse;font-size:11.5px">'
        f'<thead><tr style="text-align:left;color:var(--muted)">'
        f'<th style="padding:4px 8px;border-bottom:1px solid var(--line)">Layer</th>'
        f'<th style="padding:4px 8px;border-bottom:1px solid var(--line)">Resolution</th>'
        f'<th style="padding:4px 8px;border-bottom:1px solid var(--line)">Source & Link</th>'
        f'</tr></thead><tbody>{prov_rows}</tbody></table></div>'
    )


def geology_legend(present_symbols: set[str]) -> str:
    items = []
    for symbol, color in GEOLOGY_COLORS.items():
        if present_symbols and symbol not in present_symbols:
            continue
        items.append(
            f'<div class="it"><span class="sw" style="background:{color}"></span>{symbol}</div>'
        )
    return '<div class="legend">' + "".join(items) + "</div>"


def station_header(station: dict[str, Any]) -> str:
    return (
        f'<div class="station-head">'
        f'<span class="t">{html.escape(str(station["id"]))} · {html.escape(str(station["name"]))}</span>'
        f'<span class="sol">Sol {html.escape(str(station["sol"]))}</span>'
        f'</div>'
    )


def unit_tag(symbol: str, name: str) -> str:
    color = GEOLOGY_COLORS.get(symbol, "#9aa3ad")
    return (
        f'<span class="unit-tag" style="background:{color}">{html.escape(symbol)}</span>'
        f'<b>{html.escape(name)}</b>'
    )


def assumptions_panel_html() -> str:
    """Render the dedicated 'Assumptions & Limits' scientific disclosure panel (Stage 1)."""
    rows = "".join(
        f'<tr>'
        f'<td style="padding:8px 10px;border-bottom:1px solid var(--line);font-weight:700;color:#fff">{html.escape(a["parameter"])}</td>'
        f'<td class="mono" style="padding:8px 10px;border-bottom:1px solid var(--line);color:var(--accent)">{html.escape(a["value"])}</td>'
        f'<td style="padding:8px 10px;border-bottom:1px solid var(--line)">'
        f'<a href="{html.escape(a["url"])}" target="_blank" style="color:var(--route);text-decoration:none">{html.escape(a["source"])} ↗</a></td>'
        f'<td style="padding:8px 10px;border-bottom:1px solid var(--line);color:var(--muted)">{html.escape(a["note"])}</td>'
        f'</tr>'
        for a in ASSUMPTIONS_LOG
    )
    return (
        f'<div class="card">'
        f'<div class="k"><span>📚 SCIENTIFIC ASSUMPTIONS, THRESHOLDS & LITERATURE REFERENCES</span></div>'
        f'<table style="width:100%;border-collapse:collapse;font-size:12px;margin-top:6px">'
        f'<thead><tr style="text-align:left;color:var(--muted)">'
        f'<th style="padding:6px 10px;border-bottom:1px solid var(--line)">Parameter</th>'
        f'<th style="padding:6px 10px;border-bottom:1px solid var(--line)">Planning Value</th>'
        f'<th style="padding:6px 10px;border-bottom:1px solid var(--line)">Reference / Source</th>'
        f'<th style="padding:6px 10px;border-bottom:1px solid var(--line)">Operational Caveat</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>'
    )


def briefing_report_markdown(
    debrief: dict[str, Any],
    weather_info: dict[str, Any],
) -> str:
    """Format an exportable EVA Mission Briefing & Debrief Report (Markdown/Print-ready)."""
    stations_str = ", ".join(debrief.get("stations_names", []))
    return f"""# MarsGo — EVA-1 Mission Briefing & Debrief Report
**Team:** Mango's Gravity (NASA Space Apps Challenge 2026)
**Location:** Jezero Crater Western Delta Corridor
**Sol:** {weather_info.get('sol', '4995')} | **Temp:** {weather_info.get('tmin_c', -71):.0f}…{weather_info.get('tmax_c', -5):.0f} °C | **Opacity:** {weather_info.get('opacity', 'Sunny')} (τ={weather_info.get('tau_estimate', 0.5):.1f})

## 1. Mission Verdict: **{debrief['verdict']}**
- **Decision Rationale:** {debrief['reason']}
- **Sensitivity (+10% Slope):** {debrief['sensitivity_summary']}

## 2. Traverse & Terrain Summary
- **Visited Heritage Stations ({debrief['stations_count']}):** {stations_str}
- **Round-Trip Distance:** {debrief['distance_km']:.2f} km
- **Cumulative Climb / Descent:** +{debrief['ascent_m']:.1f} m / -{debrief['descent_m']:.1f} m
- **Estimated Walk Duration:** {debrief['duration_h']:.2f} h (Uncertainty Range: {debrief['duration_range_str']})
- **Peak Slope Encountered:** {debrief['max_slope_deg']:.1f}° (Interpolated from 200 m/px MOLA/HRSC DEM onto 10 m grid)
- **No-Go Cell Crossings:** {debrief['hazard_crossings']}
- **Max Emergency Walk-Back:** {debrief['max_walkback_km']:.2f} km ({debrief['max_walkback_h']:.2f} h to Forward Base)

## 3. xEMU Suit Consumables & Radiation
- **O₂ Used:** {debrief['o2_used_kg']:.3f} kg ({debrief['o2_pct']:.1f}% of 1.00 kg tank)
- **Cooling & Feedwater Used:** {debrief['water_used_l']:.2f} L ({debrief['water_pct']:.1f}% of 2.50 L reservoir)
- **PLSS Battery Used:** {debrief['battery_pct']:.1f}% of 8.0 h endurance
- **Remaining Walk-Back Reserve:** {debrief['reserve_left_pct']:.1f}%
- **Surface Radiation Dose:** {debrief['dose_mSv']:.3f} mSv (MSL RAD baseline ~0.03 mSv/h; NASA-STD-3001 career limit 600 mSv)
"""


def footer() -> str:
    return (
        '<div class="foot">'
        "<b>MarsGo</b> · Mango's Gravity · NASA Space Apps Challenge 2026. "
        "<b>Data Provenance:</b> NASA/JPL Mars Trek (MOLA/HRSC 200 m/px DEM resampled to 10 m routing grid, "
        "Perseverance traverse), Esri Astro / Caltech Murray Lab CTX (4.83 m/px Surface Texture Index proxy) "
        "and HiRISE (0.6 m/px) mosaics, USGS Astrogeology Jezero geologic map (SIM 3464), "
        "NASA Mars 2020 raw Navcam/Mastcam-Z imagery, NASA MSL REMS & RAD (Hassler et al., 2014). "
        "All datasets cached locally in <code>data/</code> for 100% offline execution."
        "</div>"
    )
