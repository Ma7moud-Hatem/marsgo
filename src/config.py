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
