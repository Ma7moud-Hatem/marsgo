"""Mission Control visual theme, CSS architecture, and bilingual UI dictionary for MarsGo.

Palette specification:
- Background: #0B0F14
- Surface / Cards: #121923 (elevated: #182230)
- Primary Accent (Mars Orange): #E2623A
- GO Status: #3DDC84
- NO-GO Status: #FF4D4D
- Warning Status: #FFB020
- Typography: Space Grotesk (headings) + JetBrains Mono (telemetry & numbers)
- Geometry: 12px border-radius, crisp 1px borders (#243040), zero heavy drop-shadows
"""

from __future__ import annotations

from typing import Any

from .config import COLORS

MISSION_CONTROL_CSS: str = f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@500;700;800&family=JetBrains+Mono:wght@400;600;700;800&family=Space+Grotesk:wght@500;600;700;800&display=swap');

    :root {{
        --bg: {COLORS['bg']};
        --surface: {COLORS['surface']};
        --panel: {COLORS['panel']};
        --panel2: {COLORS['panel2']};
        --line: {COLORS['line']};
        --text: {COLORS['text']};
        --muted: {COLORS['muted']};
        --accent: {COLORS['accent']};
        --route: {COLORS['route']};
        --route-alt: {COLORS['route_alt']};
        --go: {COLORS['go']};
        --warn: {COLORS['warn']};
        --nogo: {COLORS['nogo']};
        --radius: 12px;
    }}

    html, body, [class*="css"] {{
        font-family: "Space Grotesk", "Cairo", "Segoe UI", system-ui, -apple-system, sans-serif;
        background-color: var(--bg);
        color: var(--text);
    }}

    .stApp {{
        background: var(--bg);
        color: var(--text);
    }}

    .block-container {{
        padding-top: calc(3.2rem + 0.6rem);
        padding-bottom: 1.5rem;
        max-width: 100%;
    }}

    section[data-testid="stSidebar"] {{
        background: #0D131B;
        border-right: 1px solid var(--line);
    }}
    section[data-testid="stSidebar"] .block-container {{
        padding-top: 1rem;
    }}

    #MainMenu, footer {{ visibility: hidden; }}

    h1, h2, h3, h4 {{
        font-family: "Space Grotesk", "Cairo", sans-serif !important;
        color: var(--text);
        letter-spacing: -0.02em;
    }}

    code, pre, .mono, .v, .val, .vl, .sol-chip {{
        font-family: "JetBrains Mono", monospace !important;
        font-variant-numeric: tabular-nums;
    }}

    .mg-head {{
        position: sticky;
        top: 2.75rem;
        z-index: 95;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        padding: 12px 18px;
        margin-bottom: 14px;
        background: rgba(18, 25, 35, 0.94);
        backdrop-filter: blur(10px);
        border: 1px solid var(--line);
        border-radius: var(--radius);
        flex-wrap: wrap;
    }}

    .mg-brand {{
        display: flex;
        align-items: baseline;
        gap: 12px;
        flex-wrap: wrap;
    }}
    .mg-brand .name {{
        font-family: "Space Grotesk", sans-serif;
        font-size: 28px;
        font-weight: 800;
        letter-spacing: -0.04em;
        color: #FFFFFF;
    }}
    .mg-brand .name span {{
        color: var(--accent);
    }}
    .mg-brand .tag {{
        font-size: 11.5px;
        text-transform: uppercase;
        letter-spacing: 0.14em;
        color: var(--muted);
    }}

    .mg-meta {{
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
    }}

    .chip {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 5px 11px;
        border-radius: 999px;
        border: 1px solid var(--line);
        background: var(--surface);
        color: var(--text);
        font-family: "JetBrains Mono", monospace;
        font-size: 12px;
        white-space: nowrap;
    }}
    .chip b {{ color: #FFFFFF; }}
    .chip.warn-chip {{
        border-color: rgba(255, 176, 32, 0.55);
        color: var(--warn);
    }}

    @keyframes pulse-go {{
        0% {{ box-shadow: 0 0 0 0 rgba(61, 220, 132, 0.45); }}
        70% {{ box-shadow: 0 0 0 10px rgba(61, 220, 132, 0); }}
        100% {{ box-shadow: 0 0 0 0 rgba(61, 220, 132, 0); }}
    }}
    @keyframes pulse-nogo {{
        0% {{ box-shadow: 0 0 0 0 rgba(255, 77, 77, 0.55); }}
        70% {{ box-shadow: 0 0 0 10px rgba(255, 77, 77, 0); }}
        100% {{ box-shadow: 0 0 0 0 rgba(255, 77, 77, 0); }}
    }}

    .verdict-pill {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 6px 16px;
        border-radius: 999px;
        font-family: "JetBrains Mono", monospace;
        font-size: 14px;
        font-weight: 800;
        letter-spacing: 0.08em;
    }}
    .verdict-pill.go {{
        background: rgba(61, 220, 132, 0.14);
        border: 1.5px solid var(--go);
        color: var(--go);
        animation: pulse-go 2.4s infinite;
    }}
    .verdict-pill.nogo {{
        background: rgba(255, 77, 77, 0.16);
        border: 1.5px solid var(--nogo);
        color: var(--nogo);
        animation: pulse-nogo 1.8s infinite;
    }}

    .verdict {{
        border-radius: var(--radius);
        padding: 16px 18px;
        border: 1px solid var(--line);
        background: var(--surface);
        margin-bottom: 12px;
    }}
    .verdict .label {{
        font-size: 11px;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        color: var(--muted);
        margin-bottom: 4px;
    }}
    .verdict .word {{
        font-family: "Space Grotesk", sans-serif;
        font-size: 42px;
        line-height: 1.0;
        font-weight: 800;
        letter-spacing: -0.03em;
    }}
    .verdict .why {{
        margin-top: 8px;
        font-size: 13px;
        line-height: 1.45;
        color: var(--text);
    }}
    .verdict.go {{
        border-color: var(--go);
        animation: pulse-go 3s infinite;
    }}
    .verdict.go .word {{ color: var(--go); }}
    .verdict.nogo {{
        border-color: var(--nogo);
        animation: pulse-nogo 2.2s infinite;
    }}
    .verdict.nogo .word {{ color: var(--nogo); }}
    .verdict.warn {{ border-color: var(--warn); }}
    .verdict.warn .word {{ color: var(--warn); }}

    .grid {{
        display: grid;
        gap: 10px;
        margin-bottom: 12px;
    }}
    .card {{
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: var(--radius);
        padding: 12px 14px;
        transition: border-color 0.2s ease;
    }}
    .card.status-go {{ border-left: 3px solid var(--go); }}
    .card.status-warn {{ border-left: 3px solid var(--warn); }}
    .card.status-nogo {{ border-left: 3px solid var(--nogo); }}
    .card.status-accent {{ border-left: 3px solid var(--accent); }}

    .card .k {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        font-size: 11px;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: var(--muted);
        margin-bottom: 4px;
    }}
    .card .v {{
        font-family: "JetBrains Mono", monospace;
        font-size: 21px;
        font-weight: 700;
        color: #FFFFFF;
        letter-spacing: -0.02em;
    }}
    .card .s {{
        font-family: "JetBrains Mono", monospace;
        font-size: 11px;
        color: var(--muted);
        margin-top: 4px;
    }}

    .sect {{
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        color: var(--accent);
        margin: 14px 0 8px 1px;
    }}

    .bar-row {{ margin: 10px 0 13px 0; }}
    .bar-head {{
        display: flex;
        justify-content: space-between;
        gap: 10px;
        font-size: 12.5px;
        margin-bottom: 5px;
    }}
    .bar-head .lbl {{ font-weight: 600; color: #FFFFFF; }}
    .bar-head .val {{
        color: var(--muted);
        font-family: "JetBrains Mono", monospace;
        font-size: 12px;
    }}
    .bar {{
        position: relative;
        height: 10px;
        border-radius: 999px;
        background: #1B2533;
        border: 1px solid var(--line);
        overflow: hidden;
    }}
    .bar .fill {{
        height: 100%;
        border-radius: 999px;
        transition: width 0.35s ease;
    }}
    .bar .mark {{
        position: absolute;
        top: -2px;
        bottom: -2px;
        width: 2px;
        background: #FFFFFF;
    }}

    .check {{
        display: flex;
        gap: 10px;
        align-items: flex-start;
        padding: 9px 10px;
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: var(--radius);
        margin-bottom: 7px;
    }}
    .check .ico {{
        width: 20px;
        text-align: center;
        font-size: 14px;
        line-height: 1.3;
    }}
    .check .body {{ flex: 1; }}
    .check .top {{
        display: flex;
        justify-content: space-between;
        gap: 8px;
        flex-wrap: wrap;
    }}
    .check .nm {{ font-size: 13px; font-weight: 700; color: #FFFFFF; }}
    .check .vl {{
        font-family: "JetBrains Mono", monospace;
        font-size: 12px;
        color: var(--text);
    }}
    .check .dt {{
        font-size: 11.5px;
        color: var(--muted);
        margin-top: 3px;
        line-height: 1.4;
    }}
    .pass {{ border-left: 3px solid var(--go); }}
    .pass .ico {{ color: var(--go); }}
    .warn {{ border-left: 3px solid var(--warn); }}
    .warn .ico {{ color: var(--warn); }}
    .fail {{ border-left: 3px solid var(--nogo); }}
    .fail .ico {{ color: var(--nogo); }}

    .station-card {{
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: var(--radius);
        padding: 14px 16px;
        margin-bottom: 12px;
    }}
    .station-head {{
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        gap: 10px;
        margin-bottom: 6px;
    }}
    .station-head .t {{ font-size: 17px; font-weight: 700; color: #FFFFFF; }}
    .station-head .sol {{
        font-family: "JetBrains Mono", monospace;
        font-size: 11.5px;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--accent);
        background: rgba(226, 98, 58, 0.14);
        padding: 2px 8px;
        border-radius: 6px;
    }}
    .sci {{ font-size: 12.5px; line-height: 1.5; color: var(--text); }}
    .unit-tag {{
        display: inline-block;
        padding: 2px 8px;
        border-radius: 6px;
        font-family: "JetBrains Mono", monospace;
        font-size: 11px;
        font-weight: 700;
        color: #0B0F14;
        margin-right: 6px;
    }}

    .field-card {{
        border: 1.5px solid var(--accent);
        border-radius: var(--radius);
        padding: 22px 26px;
        background: var(--surface);
        margin-bottom: 12px;
    }}
    .field-card .k {{
        font-size: 12px;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: var(--accent);
    }}
    .field-card .big {{
        font-family: "JetBrains Mono", monospace;
        font-size: 44px;
        font-weight: 800;
        color: #FFFFFF;
        line-height: 1.1;
        margin: 4px 0;
    }}
    .field-card .sub {{
        font-size: 16px;
        color: var(--text);
    }}

    .hero-box {{
        background: linear-gradient(135deg, #121923 0%, #182230 100%);
        border: 1px solid var(--accent);
        border-radius: var(--radius);
        padding: 18px 22px;
        margin-bottom: 14px;
    }}
    .hero-title {{
        font-size: 20px;
        font-weight: 800;
        color: #FFFFFF;
        margin-bottom: 4px;
    }}
    .hero-sub {{
        font-size: 14px;
        color: var(--text);
        line-height: 1.5;
    }}

    .foot {{
        margin-top: 18px;
        padding-top: 12px;
        border-top: 1px solid var(--line);
        font-size: 11px;
        line-height: 1.55;
        color: var(--muted);
    }}
    .foot b {{ color: var(--text); }}

    @media (max-width: 1024px) {{
        .mg-head {{
            position: relative;
            top: 0;
            padding: 10px 12px;
        }}
        .mg-brand .name {{ font-size: 22px; }}
        .grid {{
            grid-template-columns: repeat(2, 1fr) !important;
        }}
        .field-card .big {{ font-size: 32px; }}
    }}
    @media (max-width: 640px) {{
        .grid {{
            grid-template-columns: 1fr !important;
        }}
        .verdict .word {{ font-size: 32px; }}
    }}
</style>
"""


TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "tagline": "Mission Control · EVA-1 · Jezero Crater",
        "hero_pitch": "Mars Trek is a library of Mars data — MarsGo is the briefing room that turns NASA orbital & rover layers into a survivable walking route with a real-time GO / NO-GO verdict.",
        "start_eva_btn": "🚀 Start EVA-1 Mission",
        "walk_mode": "WALK Mode (Tablet / Glove UI)",
        "scenarios": "One-Click Judge Scenarios",
        "route_mode": "Route Optimization Mode",
        "science_obj": "Science Objective",
        "stations": "Heritage Stations",
        "safety_limits": "Safety Thresholds & Suit Limits",
        "map_layers": "GIS Map Layers",
        "off_nominal": "Off-Nominal & Hazards",
        "tab_map": "🗺️ Map & Elevation",
        "tab_route": "🧭 Route & Compare",
        "tab_suit": "👨‍🚀 Suit & Sensitivity",
        "tab_hazards": "⚠️ Hazards & Abort",
        "tab_science": "🪨 Science Stations",
        "tab_assumptions": "📋 Assumptions & Debrief",
        "kpi_distance": "Traverse Distance",
        "kpi_duration": "Est. Walk Duration",
        "kpi_o2": "O₂ Consumption",
        "kpi_dose": "Radiation Dose",
        "kpi_slope": "Max / p95 Slope",
        "kpi_reserve": "Walk-Back Reserve",
        "slope_est_note": "Regional Slope Estimate (200 m/px DEM → 10 m grid)",
        "texture_note": "Surface Texture Index (CTX optical contrast proxy)",
    },
    "ar": {
        "tagline": "غرفة التحكم بالمهمة · النشاط الميداني EVA-1 · فوهة جيزيرو",
        "hero_pitch": "بينما يمثل Mars Trek مكتبة لبيانات المريخ، فإن MarsGo هو غرفة العمليات التي تحول طبقات ناسا المدارية وبيانات المسبار إلى مسار مشي قابل للنجاة مع قرار فوري (GO / NO-GO).",
        "start_eva_btn": "🚀 ابدأ مهمة EVA-1",
        "walk_mode": "وضع المشي الميداني (واجهة التابلت والقفاز)",
        "scenarios": "سيناريوهات التحكيم الجاهزة (بزر واحد)",
        "route_mode": "نمط تحسين المسار",
        "science_obj": "الهدف العلمي للمهمة",
        "stations": "محطات التراث العلمي",
        "safety_limits": "حدود الأمان ومعاملات البدلة",
        "map_layers": "طبقات الخريطة الجغرافية",
        "off_nominal": "حالات الطوارئ والمخاطر",
        "tab_map": "🗺️ الخريطة والارتفاعات",
        "tab_route": "🧭 المسار والمقارنة",
        "tab_suit": "👨‍🚀 البدلة وتحليل الحساسية",
        "tab_hazards": "⚠️ المخاطر والتراجع الآمن",
        "tab_science": "🪨 المحطات العلمية",
        "tab_assumptions": "📋 الافتراضات وملخص المهمة",
        "kpi_distance": "مسافة المسار",
        "kpi_duration": "المدة المقدرة للمشي",
        "kpi_o2": "استهلاك الأكسجين O₂",
        "kpi_dose": "الجرعة الإشعاعية",
        "kpi_slope": "الميل الأقصى / المئين 95",
        "kpi_reserve": "احتياطي العودة الآمنة",
        "slope_est_note": "ميل إقليمي تقديري (نموذج ارتفاعات 200 م/بكسل مستوفى لشبكة 10 م)",
        "texture_note": "مؤشر نسيج السطح (تباين لمعان صور CTX كبديل للخشونة)",
    },
}


def t(key: str, lang: str = "en") -> str:
    """Translate a UI key into English ('en') or Arabic ('ar')."""
    table = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    return table.get(key, TRANSLATIONS["en"].get(key, key))


def inject_theme(st_module: Any) -> None:
    """Inject Mission Control CSS into the Streamlit page."""
    st_module.markdown(MISSION_CONTROL_CSS, unsafe_allow_html=True)
