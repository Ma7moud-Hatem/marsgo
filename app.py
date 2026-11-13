"""MarsGo – Mango's Mars map (Mission Control Edition).

A suit-aware EVA traverse planner for Jezero Crater, built from cached NASA
data. Works 100% offline from cached data/. Run with:

    streamlit run app.py
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

import folium
from folium.plugins import AntPath
import numpy as np
import streamlit as st
from streamlit_folium import st_folium

try:
    from streamlit_tour import st_tour
except Exception:  # noqa: BLE001
    def st_tour(*args: Any, **kwargs: Any) -> None:
        return None

from src import data, routing, suit, terrain, theme, ui, weather
from src.config import (
    BOX,
    COLORS,
    GEOLOGY_COLORS,
    OBJECTIVES,
    ROUTE_MODES,
    SCENARIOS,
    STATION_ORDER,
    SUIT,
)

st.set_page_config(
    page_title="MarsGo – Jezero Mission Control",
    page_icon="🪐",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inject Mission Control theme & CSS
ui.inject_css(st)

# Support st.fragment for isolated UI reruns if available in installed Streamlit version
_fragment = getattr(st, "fragment", lambda fn: fn)

# -----------------------------------------------------------------------------
# session state initialization
# -----------------------------------------------------------------------------

if "first_run" not in st.session_state:
    tour_marker = pathlib.Path(__file__).parent / ".tour_completed"
    st.session_state.first_run = not tour_marker.exists()
if "show_tour" not in st.session_state:
    st.session_state.show_tour = False
if "view_mode" not in st.session_state:
    st.session_state.view_mode = "planner"
if "lang" not in st.session_state:
    st.session_state.lang = "en"
if "field_mode" not in st.session_state:
    st.session_state.field_mode = False
if "walk_leg_idx" not in st.session_state:
    st.session_state.walk_leg_idx = 0
if "hazard_zones" not in st.session_state:
    st.session_state.hazard_zones = []
if "active_scenario" not in st.session_state:
    st.session_state.active_scenario = "nominal"
if "compare_enabled" not in st.session_state:
    st.session_state.compare_enabled = False
if "show_landing" not in st.session_state:
    st.session_state.show_landing = True


# -----------------------------------------------------------------------------
# single unified st.cache_data route cache with explicit key parameters
# -----------------------------------------------------------------------------

@st.cache_data(show_spinner=False, max_entries=32)
def cached_route(
    ids: tuple[str, ...],
    speed_kmh: float,
    mode: str = "balanced",
    slope_nogo_deg: float = SUIT["slope_nogo_deg"],
    slope_warn_deg: float = SUIT["slope_warn_deg"],
    rough_nogo: float = SUIT["rough_nogo"],
    hazard_sig: tuple[tuple[float, float, float], ...] = (),
) -> routing.RouteResult | None:
    zones = [{"lon": lon, "lat": lat, "radius_m": rad} for lon, lat, rad in hazard_sig]
    return routing.plan_route(
        ids,
        speed_kmh=speed_kmh,
        mode=mode,
        slope_nogo_deg=slope_nogo_deg,
        slope_warn_deg=slope_warn_deg,
        rough_nogo=rough_nogo,
        hazard_zones=zones,
    )


# -----------------------------------------------------------------------------
# data loading
# -----------------------------------------------------------------------------

stations = list(data.stations())
station_map = {s["id"]: s for s in stations}
start = station_map.get("START")
w = weather.conditions()


def _apply_scenario(scen_key: str) -> None:
    scen = SCENARIOS[scen_key]
    st.session_state.active_scenario = scen_key
    st.session_state.scen_stations = list(scen["stations"])
    st.session_state.scen_mode = scen["route_mode"]
    st.session_state.scen_cap_h = float(scen["eva_cap_h"])
    st.session_state.scen_speed = float(scen["speed_kmh"])
    st.session_state.scen_reserve = int(scen["reserve_pct"])
    st.session_state.scen_slope_nogo = float(scen["slope_nogo_deg"])
    st.session_state.scen_solar = bool(scen["solar_event"])
    st.session_state.scen_dust = bool(scen["dust_storm"])


# Initialize scenario state defaults once
if "scen_stations" not in st.session_state:
    _apply_scenario("nominal")


# -----------------------------------------------------------------------------
# sidebar controls
# -----------------------------------------------------------------------------

with st.sidebar:
    top_c1, top_c2 = st.columns([2, 1])
    with top_c1:
        st.markdown(
            '<div class="mg-brand" style="margin-bottom:6px">'
            '<div class="name">Mars<span>Go</span></div>'
            '<div class="tag">Mission Control</div></div>',
            unsafe_allow_html=True,
        )
    with top_c2:
        lang_choice = st.selectbox(
            "Language",
            options=["en", "ar"],
            format_func=lambda x: "EN 🇺🇸" if x == "en" else "عربي 🇪🇬",
            label_visibility="collapsed",
            index=0 if st.session_state.lang == "en" else 1,
        )
        st.session_state.lang = lang_choice

    lang = st.session_state.lang

    # One-click scenarios (Stage 6)
    st.markdown(f'<div class="sect">{theme.t("scenarios", lang)}</div>', unsafe_allow_html=True)
    sc_cols = st.columns(2)
    scen_keys = list(SCENARIOS.keys())
    for idx, sk in enumerate(scen_keys):
        lbl = SCENARIOS[sk]["label_ar"] if lang == "ar" else SCENARIOS[sk]["label_en"]
        if sc_cols[idx % 2].button(lbl, key=f"btn_scen_{sk}", use_container_width=True):
            _apply_scenario(sk)
            st.rerun()

    st.caption(
        SCENARIOS[st.session_state.active_scenario][
            "summary_ar" if lang == "ar" else "summary_en"
        ]
    )

    # Science Objective & Heritage Stations
    st.markdown(f'<div class="sect">{theme.t("science_obj", lang)}</div>', unsafe_allow_html=True)
    objective = st.selectbox(
        "Science objective",
        list(OBJECTIVES),
        label_visibility="collapsed",
    )
    obj = OBJECTIVES[objective]
    st.caption(obj.get("question_ar" if lang == "ar" else "question", obj["question"]))

    st.markdown(f'<div class="sect">{theme.t("stations", lang)}</div>', unsafe_allow_html=True)
    station_ids = st.multiselect(
        "Heritage stations",
        options=list(STATION_ORDER),
        default=st.session_state.scen_stations,
        format_func=lambda s: f"{s} · {station_map[s]['name']} (Sol {station_map[s]['sol']})",
        label_visibility="collapsed",
    )

    # Route Optimization Mode (Stage 2: Fastest, Safest, Lowest Energy, Balanced)
    st.markdown(f'<div class="sect">{theme.t("route_mode", lang)}</div>', unsafe_allow_html=True)
    mode_options = list(ROUTE_MODES.keys())
    route_mode = st.selectbox(
        "Route Mode",
        options=mode_options,
        index=mode_options.index(st.session_state.scen_mode)
        if st.session_state.scen_mode in mode_options
        else 0,
        format_func=lambda m: ROUTE_MODES[m]["label_ar" if lang == "ar" else "label_en"],
        label_visibility="collapsed",
    )
    st.caption(ROUTE_MODES[route_mode]["description_ar" if lang == "ar" else "description_en"])

    compare_enabled = st.toggle(
        "Compare all route modes side-by-side" if lang == "en" else "مقارنة المسارات جنباً إلى جنب",
        value=st.session_state.compare_enabled,
    )
    st.session_state.compare_enabled = compare_enabled

    # Adjustable Safety Thresholds (Stage 1)
    st.markdown(f'<div class="sect">{theme.t("safety_limits", lang)}</div>', unsafe_allow_html=True)
    cap_h = st.slider(
        "EVA duration cap (h)" if lang == "en" else "الحد الأقصى لمدة المهمة (ساعة)",
        2.0,
        8.0,
        float(st.session_state.scen_cap_h),
        0.5,
    )
    speed = st.slider(
        "Walk speed (km/h)" if lang == "en" else "سرعة المشي (كم/س)",
        1.0,
        2.0,
        float(st.session_state.scen_speed),
        0.1,
    )
    reserve_pct = st.slider(
        "Walk-back reserve (%)" if lang == "en" else "احتياطي العودة الآمنة (%)",
        10,
        45,
        int(st.session_state.scen_reserve),
        5,
    )
    slope_nogo_deg = st.slider(
        "Max safe slope limit (°)" if lang == "en" else "حد الميل الأقصى المسموح (°)",
        12.0,
        28.0,
        float(st.session_state.scen_slope_nogo),
        1.0,
    )

    # Map Layer Toggles
    st.markdown(f'<div class="sect">{theme.t("map_layers", lang)}</div>', unsafe_allow_html=True)
    show_geology = st.toggle("USGS geologic units", True)
    show_slope = st.toggle("Regional Slope (200m DEM estimate)", False)
    show_rough = st.toggle("Surface Texture Index (CTX proxy)", False)
    show_hazard = st.toggle("No-go terrain & manual hazards", True)
    show_rover = st.toggle("Perseverance actual traverse", True)
    show_ellipse = st.toggle("Landing ellipse", True)
    show_features = st.toggle("Named Mars Trek features", False)

    # Off-Nominal & Emergency Toggles
    st.markdown(f'<div class="sect">{theme.t("off_nominal", lang)}</div>', unsafe_allow_html=True)
    solar_event = st.toggle(
        "Solar particle event (SPE)" if lang == "en" else "عاصفة إشعاعية شمسية (SPE)",
        value=bool(st.session_state.scen_solar),
    )
    dust_storm = st.toggle(
        "Dust-storm hold (τ > 2.0)" if lang == "en" else "عاصفة ترابية (τ > 2.0)",
        value=bool(st.session_state.scen_dust),
    )

    st.divider()
    field_mode = st.toggle(
        theme.t("walk_mode", lang),
        value=st.session_state.field_mode,
    )
    st.session_state.field_mode = field_mode

    if st.button("🔄 Recalculate Traverse", type="primary", use_container_width=True):
        cached_route.clear()


# -----------------------------------------------------------------------------
# route & suit evaluation
# -----------------------------------------------------------------------------

ordered = tuple(s for s in STATION_ORDER if s in station_ids)
hazard_sig = tuple(
    (round(float(z["lon"]), 6), round(float(z["lat"]), 6), round(float(z["radius_m"]), 1))
    for z in st.session_state.hazard_zones
)

route: routing.RouteResult | None = None
result: dict[str, Any] | None = None
route_error: str | None = None

if ordered:
    try:
        route = cached_route(
            ordered,
            float(speed),
            mode=route_mode,
            slope_nogo_deg=float(slope_nogo_deg),
            slope_warn_deg=SUIT["slope_warn_deg"],
            rough_nogo=SUIT["rough_nogo"],
            hazard_sig=hazard_sig,
        )
    except Exception as exc:  # noqa: BLE001
        route_error = str(exc)

cfg = suit.default_config(
    eva_cap_h=float(cap_h),
    speed_kmh=float(speed),
    reserve_frac=reserve_pct / 100.0,
    slope_nogo_deg=float(slope_nogo_deg),
)
if route is not None:
    result = suit.evaluate(
        route.stats,
        cfg,
        w,
        solar_event=solar_event,
        dust_storm=dust_storm,
    )

# -----------------------------------------------------------------------------
# sticky mission control header & landing hero banner
# -----------------------------------------------------------------------------

st.markdown(
    ui.mission_header_html(
        verdict=result["verdict"] if result else None,
        weather_chip=weather.chip_html(w),
        lang=lang,
    ),
    unsafe_allow_html=True,
)

if st.session_state.show_landing:
    with st.container():
        hc1, hc2 = st.columns([5, 1])
        with hc1:
            st.markdown(
                f'<div class="hero-box">'
                f'<div class="hero-title">🪐 MarsGo — Jezero Crater Suit-Aware EVA Field Planner</div>'
                f'<div class="hero-sub">{theme.t("hero_pitch", lang)}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with hc2:
            if st.button(theme.t("start_eva_btn", lang), type="primary", use_container_width=True):
                st.session_state.show_landing = False
                st.rerun()

if not ordered:
    st.warning("Select at least one heritage station in the sidebar to plan the EVA.")
    st.stop()
elif route_error:
    st.error(f"Routing failed: {route_error}")
    st.stop()
elif route is None or result is None:
    st.info("Computing traverse...")
    st.stop()


# -----------------------------------------------------------------------------
# Folium map builder with animated AntPath, custom hazards, and comparison paths
# -----------------------------------------------------------------------------

def build_map(
    primary_route: routing.RouteResult,
    selected_layers: dict[str, bool],
    comp_routes: dict[str, routing.RouteResult] | None = None,
    hazard_zones: list[dict[str, float]] | None = None,
) -> folium.Map:
    center = [(BOX["s"] + BOX["n"]) / 2, (BOX["w"] + BOX["e"]) / 2]
    bounds = [[BOX["s"], BOX["w"]], [BOX["n"], BOX["e"]]]

    m = folium.Map(
        location=center,
        zoom_start=13,
        tiles=None,
        control_scale=True,
        prefer_canvas=True,
        min_zoom=11,
        max_zoom=17,
        max_bounds=True,
        attributionControl=True,
    )
    m.fit_bounds(bounds, padding=(8, 8))
    m.options["maxBounds"] = [
        [BOX["s"] - 0.03, BOX["w"] - 0.05],
        [BOX["n"] + 0.03, BOX["e"] + 0.05],
    ]

    # 1. CTX optical basemap
    if data.basemap_path().exists():
        folium.raster_layers.ImageOverlay(
            image=str(data.basemap_path()),
            bounds=bounds,
            opacity=1.0,
            name="CTX Optical Basemap (4.83 m/px)",
            interactive=False,
            cross_origin=False,
        ).add_to(m)

    # 2. USGS geologic units
    if selected_layers.get("geology"):
        def style_fn(feature: dict[str, Any]) -> dict[str, Any]:
            props = feature.get("properties", {})
            return {
                "fillColor": GEOLOGY_COLORS.get(props.get("symbol"), "#9aa3ad"),
                "fillOpacity": 0.26,
                "color": "#ffffff",
                "weight": 1.0,
                "opacity": 0.45,
            }
        folium.GeoJson(
            data.geology(),
            style_function=style_fn,
            name="USGS Geologic Units (SIM 3464)",
        ).add_to(m)

    # 3. Raster overlays: Slope, Surface Texture Index (roughness proxy), No-Go Hazard
    for key, overlay_name, label in [
        ("slope", "slope", "Regional Slope Estimate (200m DEM)"),
        ("rough", "roughness", "Surface Texture Index (CTX Proxy)"),
        ("hazard", "hazard", "No-Go Hazard Mask"),
    ]:
        if selected_layers.get(key):
            p = data.overlay_path(overlay_name)
            if p.exists():
                folium.raster_layers.ImageOverlay(
                    image=str(p),
                    bounds=bounds,
                    opacity=0.55 if key != "hazard" else 0.65,
                    name=label,
                    interactive=False,
                ).add_to(m)

    # 4. Landing ellipse
    if selected_layers.get("ellipse"):
        folium.GeoJson(
            data.landing_ellipse(),
            name="Mars 2020 Landing Ellipse",
            style_function=lambda _: {
                "color": "#FFB020",
                "weight": 1.5,
                "dashArray": "6, 6",
                "fill": False,
            },
        ).add_to(m)

    # 5. Perseverance actual traverse
    if selected_layers.get("rover"):
        for seg in data.traverse_segments():
            latlons = [[lat, lon] for lon, lat in seg]
            folium.PolyLine(
                latlons,
                color="#FFD54F",
                weight=2.5,
                opacity=0.80,
                dash_array="4, 6",
                tooltip="Perseverance Rover Actual Traverse",
            ).add_to(m)

    # 6. Manual user-drawn hazard zones (Stage 2)
    if hazard_zones:
        for idx, hz in enumerate(hazard_zones):
            folium.Circle(
                location=[hz["lat"], hz["lon"]],
                radius=float(hz.get("radius_m", 150.0)),
                color="#FF4D4D",
                weight=2,
                fill=True,
                fill_color="#FF4D4D",
                fill_opacity=0.42,
                tooltip=f"Manual Hazard Zone #{idx + 1} (r={hz.get('radius_m', 150):.0f} m)",
            ).add_to(m)

    # 7. Comparison routes (if Compare mode active)
    if comp_routes:
        mode_colors = {
            "fastest": "#FFB020",
            "safest": "#3DDC84",
            "low_energy": "#B388FF",
            "balanced": "#38E1FF",
        }
        for m_key, c_route in comp_routes.items():
            if m_key == primary_route.mode:
                continue
            pts = [[float(lat), float(lon)] for lon, lat in zip(c_route.lons, c_route.lats)]
            folium.PolyLine(
                pts,
                color=mode_colors.get(m_key, "#B388FF"),
                weight=3.5,
                opacity=0.75,
                dash_array="6, 6",
                tooltip=f"{ROUTE_MODES[m_key]['label_en']}: {c_route.stats['distance_km']:.2f} km, {c_route.stats['duration_h']:.2f} h",
            ).add_to(m)

    # 8. Primary planned EVA route with progressive AntPath animation (Stage 5)
    route_pts = [[float(lat), float(lon)] for lon, lat in zip(primary_route.lons, primary_route.lats)]
    route_color = COLORS["go"] if (result and result["verdict"] == "GO") else COLORS["nogo"]
    AntPath(
        locations=route_pts,
        color=route_color,
        pulse_color="#FFFFFF",
        weight=5,
        opacity=0.92,
        delay=800,
        dash_array=[12, 24],
        tooltip=f"Planned EVA Traverse ({primary_route.stats['distance_km']:.2f} km)",
    ).add_to(m)

    # 9. Heritage Stations & Forward Base markers
    for st_item in stations:
        sid = st_item["id"]
        is_start = sid == "START"
        is_selected = sid in primary_route.station_ids
        marker_color = "#E2623A" if is_start else ("#3DDC84" if is_selected else "#8A99AD")
        folium.CircleMarker(
            location=[st_item["lat"], st_item["lon"]],
            radius=9 if (is_start or is_selected) else 6,
            color="#0B0F14",
            weight=2,
            fill=True,
            fill_color=marker_color,
            fill_opacity=0.95,
            tooltip=f"{sid} · {st_item['name']} (Sol {st_item['sol']})",
            popup=folium.Popup(
                f"<b>{sid}: {st_item['name']}</b><br>Sol {st_item['sol']}<br>"
                f"Lon {st_item['lon']:.5f}°, Lat {st_item['lat']:.5f}°",
                max_width=240,
            ),
        ).add_to(m)

    # 10. Named Mars Trek features
    if selected_layers.get("features"):
        for feat in data.waypoints().get("features", [])[:25]:
            lon, lat = feat["geometry"]["coordinates"]
            name = feat["properties"].get("name", "Feature")
            folium.CircleMarker(
                location=[lat, lon],
                radius=4,
                color="#38E1FF",
                fill=True,
                tooltip=str(name),
            ).add_to(m)

    return m


# -----------------------------------------------------------------------------
# WALK Mode (Simplified High-Contrast Tablet / Glove UI - Stage 5)
# -----------------------------------------------------------------------------

if st.session_state.field_mode:
    st.markdown(
        ui.verdict_badge(
            result["verdict"],
            result["reason"],
            result["sensitivity"]["summary"],
        ),
        unsafe_allow_html=True,
    )
    legs = route.legs
    idx = min(st.session_state.walk_leg_idx, max(0, len(legs) - 1))
    active_leg = legs[idx]
    next_id = active_leg.get("to_id", "START")
    next_st = station_map.get(next_id, start)

    st.markdown(
        f'<div class="field-card">'
        f'<div class="k">NEXT WAYPOINT · LEG {idx + 1} OF {len(legs)}</div>'
        f'<div class="big">{next_id} · {next_st["name"]}</div>'
        f'<div class="sub">Bearing <b>{active_leg["bearing"]:.0f}°</b> · '
        f'Distance <b>{active_leg["distance_km"]:.2f} km</b> · '
        f'Est. Leg Time <b>{ui.fmt_duration(active_leg["duration_h"])}</b> · '
        f'Max Slope <b>{active_leg["max_slope"]:.1f}°</b></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    wc1, wc2, wc3 = st.columns(3)
    if wc1.button("⬅️ Previous Leg", use_container_width=True, disabled=(idx == 0)):
        st.session_state.walk_leg_idx = max(0, idx - 1)
        st.rerun()
    if wc2.button("➡️ Next Waypoint", type="primary", use_container_width=True, disabled=(idx >= len(legs) - 1)):
        st.session_state.walk_leg_idx = min(len(legs) - 1, idx + 1)
        st.rerun()
    if wc3.button("🚨 Emergency Walk-Back Info", use_container_width=True):
        st.warning(
            f"Immediate Abort to {start['name']}: max distance "
            f"{route.stats['max_walkback_km']:.2f} km ({route.stats['max_walkback_h']:.2f} h)."
        )

    st.markdown(ui.kpi_cards_html(route.stats, result, lang=lang), unsafe_allow_html=True)
    st.markdown(ui.suit_bars(result["consumables"], cfg.reserve_frac), unsafe_allow_html=True)
    st.markdown(ui.footer(), unsafe_allow_html=True)
    st.stop()


# -----------------------------------------------------------------------------
# Top KPI Cards & Verdict Banner (Always Visible in Mission Control)
# -----------------------------------------------------------------------------

top_left, top_right = st.columns([1.15, 2.85])
with top_left:
    st.markdown(
        ui.verdict_badge(
            result["verdict"],
            result["reason"],
            result["sensitivity"]["summary"],
        ),
        unsafe_allow_html=True,
    )
with top_right:
    st.markdown(
        ui.kpi_cards_html(route.stats, result, lang=lang),
        unsafe_allow_html=True,
    )


# -----------------------------------------------------------------------------
# 6 Organized Mission Control Tabs (Stage 5)
# -----------------------------------------------------------------------------

tabs = st.tabs([
    theme.t("tab_map", lang),
    theme.t("tab_route", lang),
    theme.t("tab_suit", lang),
    theme.t("tab_hazards", lang),
    theme.t("tab_science", lang),
    theme.t("tab_assumptions", lang),
])

selected_layers = {
    "geology": show_geology,
    "slope": show_slope,
    "rough": show_rough,
    "hazard": show_hazard,
    "rover": show_rover,
    "ellipse": show_ellipse,
    "features": show_features,
}

comp_routes = (
    routing.compare_routes(
        ordered,
        speed_kmh=float(speed),
        slope_nogo_deg=float(slope_nogo_deg),
        hazard_zones=st.session_state.hazard_zones,
    )
    if st.session_state.compare_enabled
    else None
)

# === TAB 1: MAP & ELEVATION PROFILE ===
with tabs[0]:
    fmap = build_map(
        route,
        selected_layers,
        comp_routes=comp_routes,
        hazard_zones=st.session_state.hazard_zones,
    )
    map_out = st_folium(
        fmap,
        height=490,
        use_container_width=True,
        returned_objects=["last_clicked"],
    )

    # Click-to-add hazard support directly from map click
    if map_out and map_out.get("last_clicked"):
        clk = map_out["last_clicked"]
        clat, clon = float(clk["lat"]), float(clk["lng"])
        t_info = terrain.terrain_at(clon, clat)
        u_info = data.unit_at(clon, clat)
        u_label = f"{u_info['symbol']} ({u_info['name']})" if u_info else "Outside mapped polygons"
        mc1, mc2 = st.columns([3, 1])
        mc1.caption(
            f"📍 Selected Coordinates: **Lon {clon:.5f}°, Lat {clat:.5f}°** · "
            f"Elev **{t_info['elevation_m']:.0f} m** · "
            f"Est. Slope **{t_info['slope_deg']:.1f}°** · "
            f"Surface Texture Index **{t_info['surface_texture_index']:.3f}** · "
            f"Geologic Unit: **{u_label}**"
        )
        if mc2.button("➕ Place 150m Hazard Here", key="add_clk_hazard"):
            st.session_state.hazard_zones.append({"lon": clon, "lat": clat, "radius_m": 150.0})
            cached_route.clear()
            st.rerun()

    # Interactive SVG Elevation Profile directly beneath the map (Stage 2)
    st.markdown(
        ui.elevation_profile_svg(route.profile, route.legs, slope_warn_deg=cfg.slope_warn_deg),
        unsafe_allow_html=True,
    )
    st.markdown(ui.unified_legend_html(), unsafe_allow_html=True)


# === TAB 2: ROUTE INTELLIGENCE & COMPARE MODE ===
with tabs[1]:
    st.markdown("#### 🧭 Multi-Leg Traverse Breakdown")
    leg_rows = []
    for i, lg in enumerate(route.legs, 1):
        leg_rows.append({
            "Leg": f"Leg {i}: {lg.get('from_id', '?')} → {lg.get('to_id', '?')}",
            "Distance (km)": round(lg["distance_km"], 2),
            "Duration (h)": round(lg["duration_h"], 2),
            "Bearing (°)": round(lg["bearing"], 1),
            "Peak Slope (°)": round(lg["max_slope"], 1),
            "Cost": round(lg["cost"], 1),
        })
    st.dataframe(leg_rows, use_container_width=True, hide_index=True)

    st.markdown("#### ⚖️ Side-by-Side Route Mode Comparison (Fastest vs. Safest vs. Lowest Energy)")
    all_comp = comp_routes or routing.compare_routes(
        ordered,
        speed_kmh=float(speed),
        modes=("fastest", "balanced", "safest", "low_energy"),
        slope_nogo_deg=float(slope_nogo_deg),
        hazard_zones=st.session_state.hazard_zones,
    )
    comp_table = []
    for m_key, r_obj in all_comp.items():
        ev = suit.evaluate(r_obj.stats, cfg, w, solar_event=solar_event, dust_storm=dust_storm)
        d_min, d_max = ev["duration_range_h"]
        o2_used = next(c["used"] for c in ev["consumables"] if c["key"] == "o2")
        comp_table.append({
            "Optimization Mode": ROUTE_MODES[m_key]["label_en"],
            "Verdict": ev["verdict"],
            "Distance (km)": round(r_obj.stats["distance_km"], 2),
            "Duration (h)": f"{r_obj.stats['duration_h']:.2f} ({d_min:.2f}–{d_max:.2f})",
            "Climb (m)": round(r_obj.stats["ascent_m"], 1),
            "p95 / Max Slope (°)": f"{r_obj.stats['slope_p95']:.1f}° / {r_obj.stats['slope_max']:.1f}°",
            "O₂ Used (kg)": round(o2_used, 3),
            "Reserve Left (%)": round(ev["reserve_left"] * 100.0, 1),
        })
    st.dataframe(comp_table, use_container_width=True, hide_index=True)


# === TAB 3: SUIT CONSUMABLES, UNCERTAINTY & SENSITIVITY ===
@_fragment
def _render_suit_tab() -> None:
    sc1, sc2 = st.columns([1.15, 1.0])
    with sc1:
        st.markdown('<div class="sect">PLSS Consumables & Walk-Back Reserve</div>', unsafe_allow_html=True)
        st.markdown(ui.suit_bars(result["consumables"], cfg.reserve_frac), unsafe_allow_html=True)

        st.markdown('<div class="sect">Sensitivity Analysis (Slope Perturbation)</div>', unsafe_allow_html=True)
        sens_pct = st.slider(
            "Perturb terrain slope by +X% to test verdict stability",
            0.0,
            30.0,
            10.0,
            5.0,
            key="sens_slider",
        )
        custom_sens = suit.sensitivity_check(
            route.stats,
            cfg,
            w,
            solar_event=solar_event,
            dust_storm=dust_storm,
            slope_delta_pct=float(sens_pct),
        )
        st.info(custom_sens["summary"])

    with sc2:
        st.markdown('<div class="sect">Flight Rule Constraint Checklist</div>', unsafe_allow_html=True)
        st.markdown(ui.checklist(result["constraints"]), unsafe_allow_html=True)


with tabs[2]:
    _render_suit_tab()


# === TAB 4: MANUAL HAZARDS & ABORT / WALK-BACK ANALYSIS ===
with tabs[3]:
    hz_c1, hz_c2 = st.columns([1, 1.3])
    with hz_c1:
        st.markdown("#### 🚧 Draw / Inject Manual Hazard Zone")
        st.caption(
            "Add a custom circular no-go zone (e.g., fresh rockfall, loose dune drift, or "
            "unmapped boulder field) and watch the A* router dynamically reroute around it."
        )
        mid_lon = float(np.mean(route.lons))
        mid_lat = float(np.mean(route.lats))
        h_lon = st.number_input("Hazard Center Longitude (°E)", value=round(mid_lon, 5), format="%.5f")
        h_lat = st.number_input("Hazard Center Latitude (°N)", value=round(mid_lat, 5), format="%.5f")
        h_rad = st.slider("Hazard Radius (m)", 50, 500, 180, 25)

        hb1, hb2 = st.columns(2)
        if hb1.button("➕ Add Hazard & Reroute", type="primary", use_container_width=True):
            st.session_state.hazard_zones.append(
                {"lon": float(h_lon), "lat": float(h_lat), "radius_m": float(h_rad)}
            )
            cached_route.clear()
            st.rerun()
        if hb2.button("🗑️ Clear All Manual Hazards", use_container_width=True):
            st.session_state.hazard_zones = []
            cached_route.clear()
            st.rerun()

        if st.session_state.hazard_zones:
            st.dataframe(st.session_state.hazard_zones, use_container_width=True, hide_index=True)

    with hz_c2:
        st.markdown("#### 🚨 Abort / Walk-Back Safety Checkpoints")
        st.caption(
            "Emergency return distance, bearing, walk time, and O₂ required to reach the nearest "
            "safe haven (Forward Base) from 8 evenly spaced checkpoints along the traverse."
        )
        if route.abort_points:
            st.dataframe(route.abort_points, use_container_width=True, hide_index=True)


# === TAB 5: SCIENCE STATIONS (HiRISE ORBITAL + PERSEVERANCE POV SIDE-BY-SIDE) ===
with tabs[4]:
    st.markdown("#### 🪨 Heritage Science Stations: Orbital HiRISE Context + Rover Ground-Truth POV")
    st.caption(data.mineral_coverage_note())

    for sid in ordered:
        st_meta = station_map[sid]
        unit = data.unit_at(st_meta["lon"], st_meta["lat"])
        t_pt = terrain.terrain_at(st_meta["lon"], st_meta["lat"])
        pov = data.pov_image(sid)
        closeup = data.closeup_path(sid)

        st.markdown('<div class="station-card">', unsafe_allow_html=True)
        st.markdown(ui.station_header(st_meta), unsafe_allow_html=True)
        if unit:
            st.markdown(
                ui.unit_tag(unit.get("symbol", "?"), unit.get("name", "Mapped unit")),
                unsafe_allow_html=True,
            )
        st.caption(
            f"Coordinates: {st_meta['lon']:.5f}°E, {st_meta['lat']:.5f}°N · "
            f"Elev: {t_pt['elevation_m']:.0f} m · "
            f"Est. Slope: {t_pt['slope_deg']:.1f}° · "
            f"Surface Texture Index: {t_pt['surface_texture_index']:.3f}"
        )

        img_c1, img_c2 = st.columns(2)
        with img_c1:
            if closeup and closeup.exists():
                st.image(
                    str(closeup),
                    caption=f"{sid} Orbital HiRISE Close-Up (~0.6 m/px)",
                    use_container_width=True,
                )
        with img_c2:
            if pov:
                pov_img, pov_meta = pov
                st.image(
                    pov_img,
                    caption=f"{sid} Perseverance Ground-Truth POV ({pov_meta.get('instrument', 'Navcam/Mastcam-Z')})",
                    use_container_width=True,
                )
                if pov_meta.get("science_value") or pov_meta.get("caption"):
                    st.markdown(
                        f'<div class="sci">{pov_meta.get("science_value") or pov_meta.get("caption")}</div>',
                        unsafe_allow_html=True,
                    )
        st.markdown("</div>", unsafe_allow_html=True)


# === TAB 6: ASSUMPTIONS, PROVENANCE, DEBRIEF & EXPORT ===
with tabs[5]:
    st.markdown(ui.assumptions_panel_html(), unsafe_allow_html=True)

    st.markdown("#### 📋 Post-EVA Mission Debrief & Briefing Export")
    visited_stations = [station_map[sid] for sid in ordered if sid in station_map]
    debrief = suit.generate_debrief(
        route.stats,
        result,
        visited_stations,
        abort_points=route.abort_points,
    )
    report_md = ui.briefing_report_markdown(debrief, w)

    db_c1, db_c2 = st.columns([2, 1])
    with db_c1:
        st.markdown(report_md)
    with db_c2:
        st.download_button(
            "📥 Download Briefing Report (.md)",
            data=report_md.encode("utf-8"),
            file_name=f"MarsGo_EVA1_Briefing_{result['verdict']}.md",
            mime="text/markdown",
            use_container_width=True,
        )
        st.download_button(
            "📥 Export Route GeoJSON (.geojson)",
            data=json.dumps(routing.route_geojson(route), indent=2).encode("utf-8"),
            file_name="MarsGo_EVA1_Route.geojson",
            mime="application/geo+json",
            use_container_width=True,
        )

st.markdown(ui.footer(), unsafe_allow_html=True)
