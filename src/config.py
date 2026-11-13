"""Mission constants, thresholds, palettes, and scientific provenance shared across MarsGo."""

from __future__ import annotations

from pathlib import Path
from typing import Any

ROOT: Path = Path(__file__).resolve().parent.parent
DATA: Path = ROOT / "data"
RAW: Path = DATA / "raw"
PROC: Path = DATA / "processed"
ASSETS: Path = ROOT / "assets"

# Mission box around the Perseverance corridor and the Jezero delta front.
# (west, south, east, north) in degrees, planetocentric coordinates.
BOX: dict[str, float] = {"w": 77.27, "s": 18.40, "e": 77.50, "n": 18.53}
BOX_BOUNDS: list[list[float]] = [[BOX["s"], BOX["w"]], [BOX["n"], BOX["e"]]]

MARS_RADIUS_M: float = 3_396_190.0
MARS_GRAVITY_M_S2: float = 3.721

# Resolution disclosure: DEM native resolution vs. routing grid resolution
DEM_NATIVE_RES_M: float = 200.0
CTX_NATIVE_RES_M: float = 4.83
HIRISE_NATIVE_RES_M: float = 0.60
GRID_M: float = 10.0  # routing grid resolution

# Tile endpoints (offline build pipeline only; never called at runtime)
CTX_URL: str = "https://astro.arcgis.com/arcgis/rest/services/OnMars/CTX1/MapServer/tile"
HIRISE_URL: str = "https://astro.arcgis.com/arcgis/rest/services/OnMars/HiRISE/MapServer/tile"
CTX_MAX_Z: int = 12
HIRISE_Z: int = 15

TREK: str = "https://trek.nasa.gov/mars/trekarcgis/rest/services"
TREK_TRAVERSE: str = f"{TREK}/Perseverance_Traverse_Path/MapServer/0/query"
TREK_WAYPOINTS: str = f"{TREK}/mars2020_waypoints/MapServer/0/query"
TREK_ELLIPSE: str = f"{TREK}/perseverance_landing_ellipse/MapServer/0/query"

# Ordered heritage stations along the Jezero traverse
STATION_ORDER: tuple[str, ...] = ("S1", "S2", "S3")

# Unified suit & terrain thresholds (Single Source of Truth)
SUIT: dict[str, float] = {
    "speed_kmh": 1.5,            # Nominal Martian EVA walking speed (km/h)
    "speed_unc_frac": 0.12,      # ±12% walking pace & terrain friction uncertainty
    "eva_cap_h": 6.0,            # Max EVA duration cap (hours)
    "reserve_frac": 0.25,        # Required walk-back consumable reserve (25%)
    "o2_kg": 1.00,               # Primary O2 tank usable capacity (kg) - xEMU PLSS baseline
    "o2_rate_kg_h": 0.09,        # Nominal metabolic O2 consumption (kg/h)
    "o2_unc_frac": 0.10,         # ±10% metabolic O2 rate uncertainty
    "water_l": 2.50,             # Cooling & hydration feedwater capacity (L)
    "water_rate_l_h": 0.15,      # Nominal sublimation/hydration consumption (L/h)
    "battery_h": 8.0,            # PLSS high-density battery endurance (hours)
    "battery_wh": 680.0,         # Equivalent battery energy capacity (Wh)
    "radiation_mSv_h": 0.03,     # Surface GCR dose rate (~0.03 mSv/h, MSL RAD baseline)
    "spe_radiation_mSv_h": 1.50, # Elevated dose rate during active Solar Particle Event (mSv/h)
    "career_limit_mSv": 600.0,   # NASA STD-3001 career effective radiation limit (mSv)
    "dust_tau_limit": 2.0,       # Max optical depth (tau) before visibility/solar abort
    "slope_warn_deg": 15.0,      # Sustained slope warning threshold (degrees)
    "slope_nogo_deg": 22.0,      # Hard impassable slope threshold (degrees) — unified across code & UI
    "rough_warn": 0.25,          # Surface Texture Index warning threshold (CTX proxy)
    "rough_nogo": 0.42,          # Surface Texture Index hard no-go threshold (CTX proxy)
    "climb_penalty_per_deg": 0.06,  # +6% walk duration penalty per degree of uphill grade
    "sensitivity_slope_pct": 10.0,  # Default sensitivity perturbation (+10% slope)
}

# Route optimization profiles (Stage 2: Fast, Safe, Low-Energy)
ROUTE_MODES: dict[str, dict[str, Any]] = {
    "balanced": {
        "label_en": "Balanced (Nominal)",
        "label_ar": "متوازن (قياسي)",
        "w_base": 1.0,
        "w_slope": 3.0,
        "w_rough": 2.5,
        "w_warn": 6.0,
        "speed_mult": 1.0,
        "description_en": "Balances walking distance against moderate slope and surface texture penalties.",
        "description_ar": "يوازن بين مسافة المشي وتجنب المنحدرات ومؤشر خشونة السطح.",
    },
    "fastest": {
        "label_en": "Fastest (Direct)",
        "label_ar": "الأسرع (مباشر)",
        "w_base": 1.4,
        "w_slope": 1.2,
        "w_rough": 1.0,
        "w_warn": 2.5,
        "speed_mult": 1.08,
        "description_en": "Minimizes path length and transit time while still strictly avoiding hard no-go cells.",
        "description_ar": "يقلل المسافة وزمن المشي لأقصى حد مع الالتزام الكامل بتجنب المناطق المحظورة.",
    },
    "safest": {
        "label_en": "Safest (Min-Slope)",
        "label_ar": "الأأمن (أقل ميل)",
        "w_base": 0.8,
        "w_slope": 8.0,
        "w_rough": 6.0,
        "w_warn": 14.0,
        "speed_mult": 0.95,
        "description_en": "Heavily penalizes slopes and rough textures to keep the crew on the flattest corridor.",
        "description_ar": "يفرض عقوبة عالية على الميل والخشونة لإبقاء الرواد في أكثر الممرات استواءً وأماناً.",
    },
    "low_energy": {
        "label_en": "Lowest Energy & O₂",
        "label_ar": "الأقل استهلاكاً للطاقة والأكسجين",
        "w_base": 1.0,
        "w_slope": 5.5,
        "w_rough": 4.0,
        "w_warn": 9.0,
        "speed_mult": 0.98,
        "description_en": "Minimizes cumulative metabolic climb and O₂/battery draw across elevation gradients.",
        "description_ar": "يقلل الجهد الأيضي التراكمي واستهلاك الأكسجين والبطارية عبر تجنب الصعود الحاد.",
    },
}

# Science objectives
OBJECTIVES: dict[str, dict[str, Any]] = {
    "Full corridor (S1 → S2 → S3)": {
        "stations": ["S1", "S2", "S3"],
        "question": "Walk the proven Perseverance corridor from Octavia E. Butler Landing to the western delta front.",
        "question_ar": "سلك الممر المثبت لمركبة Perseverance من موقع الهبوط حتى جبهة الدلتا الغربية.",
    },
    "Crater floor contact (S1 → S2)": {
        "stations": ["S1", "S2"],
        "question": "Sample the fractured crater-floor unit (Cf-fr) and view Kodiak mesa stratigraphy.",
        "question_ar": "جمع عينات من وحدة قاع الفوهة المتصدعة (Cf-fr) ورصد طبقات هضبة Kodiak.",
    },
    "Delta front rapid recon (S3 direct)": {
        "stations": ["S3"],
        "question": "Direct traverse to the delta front boulder conglomerate contact for astrobiology sampling.",
        "question_ar": "مسار مباشر إلى نقطة التماس مع رواسب جبهة الدلتا لأخذ عينات البيولوجيا الفلكية.",
    },
}

# One-click judge scenarios (Stage 6)
SCENARIOS: dict[str, dict[str, Any]] = {
    "nominal": {
        "label_en": "🟢 Nominal EVA-1",
        "label_ar": "🟢 مهمة قياسية (GO)",
        "stations": ["S1", "S2", "S3"],
        "route_mode": "balanced",
        "eva_cap_h": 6.0,
        "speed_kmh": 1.5,
        "reserve_pct": 25,
        "slope_nogo_deg": 22.0,
        "solar_event": False,
        "dust_storm": False,
        "summary_en": "Standard 3-station Jezero traverse under clear skies (τ=0.5) and nominal xEMU reserves.",
        "summary_ar": "مسار قياسي يشمل المحطات الثلاث في أجواء صافية واحتياطي آمن للبدلة.",
    },
    "dust_storm": {
        "label_en": "🟠 Dust Storm Hold (NO-GO)",
        "label_ar": "🟠 عاصفة ترابية (NO-GO)",
        "stations": ["S1", "S2", "S3"],
        "route_mode": "safest",
        "eva_cap_h": 6.0,
        "speed_kmh": 1.3,
        "reserve_pct": 30,
        "slope_nogo_deg": 22.0,
        "solar_event": False,
        "dust_storm": True,
        "summary_en": "Regional dust storm spikes optical depth (τ > 2.0), degrading visibility and triggering NO-GO.",
        "summary_ar": "عاصفة غبارية ترفع العتامة البصرية (τ > 2.0) وتمنع الخروج حفاظاً على سلامة الطاقم.",
    },
    "solar_event": {
        "label_en": "🔴 Solar Particle Event (NO-GO)",
        "label_ar": "🔴 عاصفة إشعاعية شمسية (NO-GO)",
        "stations": ["S1", "S2"],
        "route_mode": "fastest",
        "eva_cap_h": 6.0,
        "speed_kmh": 1.6,
        "reserve_pct": 25,
        "slope_nogo_deg": 22.0,
        "solar_event": True,
        "dust_storm": False,
        "summary_en": "Active SPE elevates surface radiation from 0.03 to 1.50 mSv/h, requiring immediate shelter abort.",
        "summary_ar": "حدث جسيمات شمسية نشط يرفع الإشعاع السطحي إلى 1.50 ملي سيفرت/ساعة ويفرض الإلغاء الفوري.",
    },
    "extended_nogo": {
        "label_en": "⚠️ Extended EVA / Tight Cap (NO-GO)",
        "label_ar": "⚠️ تجاوز حد الأمان والاحتياطي (NO-GO)",
        "stations": ["S1", "S2", "S3"],
        "route_mode": "safest",
        "eva_cap_h": 3.0,
        "speed_kmh": 1.1,
        "reserve_pct": 35,
        "slope_nogo_deg": 18.0,
        "solar_event": False,
        "dust_storm": False,
        "summary_en": "Slow pace (1.1 km/h) with a strict 3.0 h cap and 35% reserve requirement breaches duration & reserve limits.",
        "summary_ar": "سرعة مشي بطيئة مع سقف زمني صارم (3 ساعات) واحتياطي 35% يؤدي لقرار NO-GO بسبب استنزاف الموارد.",
    },
}

# Mission Control Visual Identity Palette (Stage 5)
COLORS: dict[str, str] = {
    "bg": "#0B0F14",
    "surface": "#121923",
    "panel": "#121923",
    "panel2": "#182230",
    "line": "#243040",
    "text": "#ECF2F8",
    "muted": "#8A99AD",
    "accent": "#E2623A",
    "route": "#38E1FF",
    "route_alt": "#B388FF",
    "go": "#3DDC84",
    "warn": "#FFB020",
    "nogo": "#FF4D4D",
}

GEOLOGY_COLORS: dict[str, str] = {
    "Cf-fr": "#b87352",
    "Cf-r": "#d49a6a",
    "Df": "#5ca4a9",
    "Dm": "#84dcc6",
    "Cr": "#9aa3ad",
    "Cs": "#e6c229",
    "Su": "#c97b84",
}

# Scientific assumptions & literature citations (Stages 1 & 6)
ASSUMPTIONS_LOG: tuple[dict[str, str], ...] = (
    {
        "parameter": "Surface Radiation (GCR)",
        "value": "0.03 mSv/h (0.64 mSv/sol); Career limit: 600 mSv",
        "source": "MSL RAD (Hassler et al., 2014, Science 343) & NASA-STD-3001",
        "url": "https://www.science.org/doi/10.1126/science.1244797",
        "note": "Measured on Mars surface by Curiosity Radiation Assessment Detector; SPE increases flux >50x.",
    },
    {
        "parameter": "PLSS Consumables (O₂, H₂O, Battery)",
        "value": "1.0 kg O₂ @ 0.09 kg/h; 2.5 L H₂O @ 0.15 L/h; 8.0 h Battery",
        "source": "NASA xEMU / Portable Life Support System Baseline (Ross et al., ICES)",
        "url": "https://ntrs.nasa.gov/",
        "note": "Includes ±10% metabolic rate uncertainty and mandatory walk-back reserve.",
    },
    {
        "parameter": "Topographic Slope & Elevation",
        "value": "MOLA/HRSC Blended DEM (200 m/px) resampled to 10 m routing grid",
        "source": "USGS Astrogeology / NASA Mars Trek MOLA-HRSC DEM v2",
        "url": "https://trek.nasa.gov/mars/",
        "note": "Regional slope is an interpolated estimate at 10 m grid scale unless HiRISE DTM (1 m/px) is loaded.",
    },
    {
        "parameter": "Surface Texture Index (Roughness Proxy)",
        "value": "Local luminance standard deviation on 4.83 m/px CTX mosaic (warn > 0.25, no-go > 0.42)",
        "source": "MRO CTX Global Mosaic (Dickson et al., Caltech Murray Lab / Esri Astro)",
        "url": "https://murray-lab.caltech.edu/CTX/",
        "note": "Explicitly labeled as an optical albedo/texture proxy rather than photogrammetric micro-topography.",
    },
    {
        "parameter": "Geologic Units & Rover Traverse",
        "value": "USGS Jezero Map (SIM 3464) & Mars 2020 Perseverance Traverse",
        "source": "Sun & Stack (2020) USGS SIM 3464; JPL Mars 2020 Localization",
        "url": "https://pubs.usgs.gov/sim/3464/",
        "note": "Authoritative mapped contacts and actual rover waypoints cached locally for offline field execution.",
    },
    {
        "parameter": "Atmospheric Conditions",
        "value": "Sol temperature, pressure (Pa), and optical depth (τ)",
        "source": "MSL REMS (Gale Crater Analog) / MEDA Reference Baseline",
        "url": "https://mars.nasa.gov/msl/spacecraft/instruments/rems/",
        "note": "Explicitly flagged in UI as an analog dataset cached offline.",
    },
)

DATA_PROVENANCE: tuple[dict[str, str], ...] = (
    {
        "layer": "CTX Optical Basemap",
        "resolution": "4.83 m/px",
        "source": "Esri Astro / MRO CTX Murray Lab Mosaic",
        "url": "https://murray-lab.caltech.edu/CTX/",
        "type": "Optical Raster (Cached PNG)",
    },
    {
        "layer": "Elevation & Regional Slope (DEM)",
        "resolution": "200 m/px native → 10 m grid (Interpolated Estimate)",
        "source": "NASA Mars Trek MOLA/HRSC Blended DEM",
        "url": "https://trek.nasa.gov/mars/",
        "type": "Float32 NumPy Raster (elevation.npy, slope.npy)",
    },
    {
        "layer": "Surface Texture Index (Roughness Proxy)",
        "resolution": "10 m grid (from 4.83 m/px CTX luminance variance)",
        "source": "Derived from MRO CTX Optical Contrast",
        "url": "https://trek.nasa.gov/mars/",
        "type": "Float32 NumPy Raster (roughness.npy)",
    },
    {
        "layer": "USGS Jezero Geologic Map",
        "resolution": "1:75,000 vector polygons",
        "source": "USGS Scientific Investigations Map 3464 (Sun & Stack, 2020)",
        "url": "https://pubs.usgs.gov/sim/3464/",
        "type": "GeoJSON Vector (geology.geojson)",
    },
    {
        "layer": "Perseverance Rover Traverse & Stations",
        "resolution": "< 1 m localization",
        "source": "NASA/JPL-Caltech Mars 2020 Mission Data",
        "url": "https://mars.nasa.gov/mars2020/",
        "type": "GeoJSON + Navcam/Mastcam-Z POV Imagery",
    },
    {
        "layer": "Weather Snapshot (Analog)",
        "resolution": "Sol-level telemetry",
        "source": "NASA MSL REMS (Gale Crater Analog)",
        "url": "https://mars.nasa.gov/msl/spacecraft/instruments/rems/",
        "type": "Cached JSON (weather_snapshot.json)",
    },
)

PERF_TARGETS: dict[str, float] = {
    "data_load_s": 0.50,
    "cost_surface_s": 0.35,
    "route_plan_s": 1.20,
    "suit_eval_s": 0.05,
}
