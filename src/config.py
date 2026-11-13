"""Mission constants shared by the pipeline and the app."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"
PROC = DATA / "processed"
ASSETS = ROOT / "assets"

# Mission box around the Perseverance corridor and the Jezero delta front.
# (west, south, east, north) in degrees, planetographic-ish planetocentric.
BOX = {"w": 77.27, "s": 18.40, "e": 77.50, "n": 18.53}
BOX_BOUNDS = [[BOX["s"], BOX["w"]], [BOX["n"], BOX["e"]]]

MARS_RADIUS_M = 3_396_190.0
GRID_M = 10.0  # route grid resolution

# CTX tile scheme on Esri Astro (Mars 2000 Sphere, geographic)
CTX_URL = "https://astro.arcgis.com/arcgis/rest/services/OnMars/CTX1/MapServer/tile"
HIRISE_URL = "https://astro.arcgis.com/arcgis/rest/services/OnMars/HiRISE/MapServer/tile"
CTX_MAX_Z = 12          # service rejects z13+
HIRISE_Z = 15           # ~0.6 m/px close-ups

TREK = "https://trek.nasa.gov/mars/trekarcgis/rest/services"
TREK_TRAVERSE = f"{TREK}/Perseverance_Traverse_Path/MapServer/0/query"
TREK_WAYPOINTS = f"{TREK}/mars2020_waypoints/MapServer/0/query"
TREK_ELLIPSE = f"{TREK}/perseverance_landing_ellipse/MapServer/0/query"
TREK_DEM = (
    f"{TREK}/Mars_MOLA_blend200ppx_HRSC_DEM_clon0dd_200mpp_lzw/ImageServer/exportImage"
)
TREK_MINERALS = {
    "hydrous": f"{TREK}/Hydrous_Mineral_Detections_OMEGA_CRISM_clon0/MapServer/export",
    "chloride": f"{TREK}/Chloride_Salt_bearing_Material_THEMIS_clon0/MapServer/export",
}
TREK_VIKING = f"{TREK}/Mars_Viking_MDIM21_ClrMosaic_global_232m/ImageServer/exportImage"

USGS_GEOLOGY = (
    "https://services.arcgis.com/v01gqwM5QqNysAAi/arcgis/rest/services/"
    "Jezero_FeatureServiceFromPro/FeatureServer"
)

RAW_IMAGES_API = (
    "https://mars.nasa.gov/rss/api/?feed=raw_images&category=mars2020"
    "&feedtype=json&num=40&sol={sol}"
)
WEATHER_API = "https://mars.nasa.gov/rss/api/?feed=weather&category=msl&feedtype=json"

# UI palette
COLORS = {
    "bg": "#0b0d10",
    "panel": "#14181d",
    "panel2": "#1b2128",
    "line": "#2a3138",
    "text": "#e8e2d9",
    "muted": "#9aa3ad",
    "accent": "#e0653a",
    "route": "#38e1ff",
    "go": "#2ecc71",
    "warn": "#f1c40f",
    "nogo": "#e74c3c",
    "rover": "#8b949e",
}

# Mission objectives. Each one changes the station set, instruments, and the
# sample plan shown on the station card.
OBJECTIVES = {
    "Delta front stratigraphy": {
        "short": "DELTA",
        "question": "Read the lake-level history recorded in the delta foresets.",
        "stations": ["S1", "S2", "S3"],
        "instrument": "Mastcam-Z + hand lens + caching hammer",
        "sample": "Foreset sandstone / siltstone",
        "dwell_min": 45,
        "priority": "PRIMARY",
        "mineral": "Orbital spectroscopy: phyllosilicate-bearing fan material.",
        "why": "The Jezero fan is the strongest astrobiology target in the "
               "mission box. Each foreset is a shoreline snapshot.",
    },
    "Hydrated mineral ground-truthing": {
        "short": "MINERAL",
        "question": "Confirm orbital clay/carbonate signatures at outcrop scale.",
        "stations": ["S1", "S2"],
        "instrument": "PIXL / SHERLOC-class spectrometer + context imager",
        "sample": "Veined / altered bedrock",
        "dwell_min": 60,
        "priority": "PRIMARY",
        "mineral": "CRISM/OMEGA context; no confident detection in this AOI.",
        "why": "Ground truth beats orbital inference. A null detection is still "
               "science: it bounds the orbital detection threshold.",
    },
    "Fine-grained unit sampling": {
        "short": "MUDSTONE",
        "question": "Sample clay-rich mudstone with the best preservation potential.",
        "stations": ["S1", "S3"],
        "instrument": "Sterile scoop + sealed sample tubes",
        "sample": "Clay-rich mudstone",
        "dwell_min": 50,
        "priority": "HIGH",
        "mineral": "Unit is part of the Jezero floor/fan transition.",
        "why": "Fine-grained lacustrine mudstone is the best candidate for "
               "preserved biosignatures.",
    },
    "Surface processes survey": {
        "short": "SURFACE",
        "question": "Measure dust, abrasion, and active surface change.",
        "stations": ["S2", "S3"],
        "instrument": "Imaging + regolith abrasion tools",
        "sample": "Surface regolith / eolian bedform",
        "dwell_min": 35,
        "priority": "SECONDARY",
        "mineral": "Dust and eolian material dominate the surface signal.",
        "why": "Astronauts will change the surface just by walking. Measure it.",
    },
}

# USGS Jezero unit colours. Keys are the map symbols in geology.geojson.
GEOLOGY_COLORS = {
    "NHjf2": "#d98f4e",   # Jezero fan 2
    "Aeb": "#b9a06a",     # Eolian bedform
    "Nue": "#7f9d8a",     # Upper etched
    "su": "#8d99ae",      # Smooth undivided
    "cr": "#a86b6b",      # Crater rim
    "Nle": "#5f8a7b",     # Lower etched
    "Njf": "#6b7b8c",     # Jezero floor
    "Nnp1": "#9a7fa8",    # Nili Planum 1
}

STATION_ORDER = ("S1", "S2", "S3")

# Assumptions, shown in the UI. Not flight rules.
SUIT = {
    "speed_kmh": 1.5,
    "eva_cap_h": 6.0,
    "reserve_frac": 0.25,
    "o2_kg": 1.0,
    "o2_rate_kg_h": 0.09,
    "water_l": 2.5,
    "water_rate_l_h": 0.15,
    "battery_h": 8.0,
    "radiation_mSv_h": 0.03,
    "career_limit_mSv": 600.0,
    "dust_tau_limit": 2.0,
    "slope_warn_deg": 15.0,
    "slope_nogo_deg": 22.0,
    "rough_nogo": 0.985,
}
