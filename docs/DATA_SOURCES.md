# Data Sources — verified

All endpoints below were tested live on **2026-11-13** from this machine.
Status codes are what the server actually returned, not what the docs claim.

> Note: this environment requires `curl -k` for some NASA hosts due to a local
> CA issue. The app itself uses `requests` with retries and local cache.

---

## 1. Mars Trek (NASA JPL)

Base: `https://trek.nasa.gov/mars/`

### Services directory
`https://trek.nasa.gov/mars/trekarcgis/rest/services?f=json` — **200**

Relevant services discovered:

| Service | Type | Use |
|---|---|---|
| `SIM3292_Global_Geology` | MapServer | Global geologic map |
| `perseverance_landing_ellipse` | MapServer | Landing ellipse polygon |
| `Perseverance_Traverse_Path` | MapServer | 673 drive segments, sol-tagged |
| `mars2020_waypoints` | MapServer | 8 named Jezero features |
| `Hydrous_Mineral_Detections_OMEGA_CRISM_clon0` | MapServer | Spectral detections |
| `Chloride_Salt_bearing_Material_THEMIS_clon0` | MapServer | Thermal/spectral |
| `Mars_Viking_MDIM21_ClrMosaic_global_232m` | ImageServer | Global color context |
| `MOLA_blend200ppx_HRSC_DEM_..._200mpp_lzw` | ImageServer | Terrain |
| `MOLA_blend200ppx_HRSC_Shade_..._200mpp_lzw` | ImageServer | Hillshade |

### Confirmed GeoJSON queries

```text
# Rover traverse (673 LineString/MultiLineString features, sol + length)
https://trek.nasa.gov/mars/trekarcgis/rest/services/Perseverance_Traverse_Path/MapServer/0/query?where=1%3D1&outFields=*&outSR=4326&f=geojson

# Landing ellipse polygon
https://trek.nasa.gov/mars/trekarcgis/rest/services/perseverance_landing_ellipse/MapServer/0/query?where=1%3D1&outFields=*&outSR=4326&f=geojson

# 8 named features (Jezero Crater, Western Delta Deposit, Western Breach, ...)
https://trek.nasa.gov/mars/trekarcgis/rest/services/mars2020_waypoints/MapServer/0/query?where=1%3D1&outFields=*&outSR=4326&f=geojson
```

### DEM export (confirmed working)

```text
https://trek.nasa.gov/mars/trekarcgis/rest/services/Mars_MOLA_blend200ppx_HRSC_DEM_clon0dd_200mpp_lzw/ImageServer/exportImage
  ?bbox=77.25,18.40,77.60,18.52
  &bboxSR=4326&imageSR=4326
  &size=1400,480
  &format=tiff&pixelType=S16&f=image
```

Returns a 16-bit TIFF (tested: 1400×480, ~1.4 MB). Pixel size ≈ 200 m/px.

### Elevation profile / distance services

From `https://trek.nasa.gov/mars/jpl/config/config.json`:

- `https://trek.nasa.gov/mars/TrekServices/ws/elevationProfile/calculate`
- `https://trek.nasa.gov/mars/TrekServices/ws/elevationProfile/distance`
- `https://trek.nasa.gov/mars/TrekServices/ws/elevationProfile/multiDEM/interpolated`

Useful for cross-checking our DEM-derived profile.

### Known issue

Mars Trek's *basemap tile cache* paths return **404** for the Viking layer and
the browser console shows failures. Do **not** build the basemap on Mars Trek
tiles. Use Esri Astro CTX (below).

---

## 2. Esri Astro — CTX & HiRISE mosaics

Discovered via ArcGIS Online search. These are NASA data hosted by Esri.

### Global CTX Mosaic of Mars (V01)

`https://astro.arcgis.com/arcgis/rest/services/OnMars/CTX1/MapServer`

- **Tiles verified 200** at z10 and z12 over Jezero.
- Projection: Mars 2000 Sphere, `wkid 104971`, geographic, origin (-180, 90),
  512×512 tiles, levels 0–17.
- z12 resolution ≈ 8.6e-5 °/px ≈ **5.1 m/px**.
- z13/z14 return **400 Bad Request** (service max out below native source res).
- Camera is grayscale (CTX is a black-and-white imager). Basemap will be
  rendered as a high-contrast grayscale layer, optionally tinted.

Tile pattern:

```text
https://astro.arcgis.com/arcgis/rest/services/OnMars/CTX1/MapServer/tile/{z}/{row}/{col}
```

### Mars HiRISE Image Mosaic

`https://astro.arcgis.com/arcgis/rest/services/OnMars/HiRISE/MapServer`

- Metadata **200**; 512×512, levels 0–17.
- **Tiles over Jezero return 404** at z13–15. Treat as unavailable.
- Fallback for close-ups: individual HiRISE browse images from `uahirise.org`
  and Perseverance raw images.

### USGS Jezero CTX basemap tiles

`https://tiles.arcgis.com/tiles/v01gqwM5QqNysAAi/arcgis/rest/services/Nili_CTX_Mosaic_Beta01_Feb2018_MTM_tif_NEWTILING5/MapServer`

- `TilesOnly` in Mars Transverse Mercator (`MTM_clon77_5E`).
- `export` returns **404** (tiles only). Would need MTM tile math to use.
- **Not used** in the MVP; CTX1 is simpler and already geographic.

---

## 3. USGS — Jezero Crater & Nili Planum geologic map

**FeatureServer root:**
`https://services.arcgis.com/v01gqwM5QqNysAAi/arcgis/rest/services/Jezero_FeatureServiceFromPro/FeatureServer`

Queryable layers (verified):

| ID | Layer |
|---|---|
| 0 | MapBoundary |
| 1 | Figures |
| 2 | LandingEllipse |
| 3 | CrossSections |
| 4 | Location Features |
| 5 | Geologic Contacts |
| 6 | Linear Features |
| 7 | Surface Features |
| 8 | **Geologic Units** |

Geologic Units fields: `unit`, `name`, `symbol`, `Unit_Description`,
`Additional_Characteristics`, `Unit_Interpretation`, `Shape__Area`.

Query confirmed (GeoJSON, EPSG:4326):

```text
.../FeatureServer/8/query?where=1%3D1&outFields=*&outSR=4326&f=geojson
```

Caveat: polygons are dense. Filter by bbox and simplify before committing to
the repo (target < 2 MB).

Related services:

- Nomenclature tiles:
  `.../JezeroNomenclature_WebTile/MapServer`
- Unit annotation tiles:
  `.../JezeroGeoUnitsAnno_WebTile2/MapServer`

---

## 4. Perseverance raw images (POV cards)

**API (verified 200):**

```text
https://mars.nasa.gov/rss/api/?feed=raw_images&category=mars2020&feedtype=json&num=100
```

Returns `images[]` with `sol`, camera, `image_files.small/medium/full_res`.
Tested response contained sol 2031 Navcam imagery.

Use policy: download a handful of small/medium JPEGs into
`assets/waypoints/` so the demo does not depend on live NASA bandwidth.

Gallery: `https://mars.nasa.gov/mars2020/multimedia/raw-images/`

---

## 5. Atmosphere — MSL REMS weather

**API (verified 200):**

```text
https://mars.nasa.gov/rss/api/?feed=weather&category=msl&feedtype=json
```

Fields include sol keys, min/max/avg air temperature, pressure, wind speed,
wind direction, and atmospheric opacity (`PRE`/`AT`/`HWS`).

Caveat: REMS is at **Gale Crater**, not Jezero. In the app it is labeled
"Gale analog station" unless a Jezero-specific MEDA extract is added. This is
an explicit, visible limitation — not hidden.

Fallback for demo: bundled `data/raw/weather_snapshot.json`.

---

## 6. Radiation — MSL RAD

No simple public JSON feed. Values used in the model are from published MSL RAD
surface results:

- Surface GCR dose rate ≈ **0.7 mSv/day** (≈ 0.03 mSv/h).
- Solar particle events can deliver a large acute dose; the app treats an SPE
  as an automatic return-to-hab.

The app shows the dose as a **model output with cited assumptions**, not as a
live measurement.

---

## 7. Other verified hosts

| Host | Status | Purpose |
|---|---|---|
| `https://www.uahirise.org/` | 200 | HiRISE browse images, DTMs |
| `https://pds-geosciences.wustl.edu/` | 200 | PDS raw data archive |
| `https://themis.asu.edu/` | 200 | THEMIS thermal |
| `https://planetarymaps.usgs.gov/` | 200 | USGS GeoTIFF products |
| `https://trek.nasa.gov/mars/` | 200 | Mars Trek |
| `https://astrogeology-usgs.hub.arcgis.com/pages/interactive-maps-mars` | 200 | USGS Mars map hub |

## 8. Rejected / unusable

| Source | Why |
|---|---|
| Web search API | HTTP 402 in this environment |
| Mars Trek Viking tile cache | 404 |
| Mars Trek `DTEEC_041277...` layer | Wrong location (31°N, 29°W) and empty MapServer |
| ArcGIS `astro.arcgis.com/.../services` listing | 404/000; individual services still work |
| HiRISE mosaic over Jezero | 404 at usable zooms |
| `Jezero_Elevation_Model.IMG` layer package | 141 MB, ArcGIS Pro format, too heavy for today |

## 9. Licensing / attribution

All sources are U.S. Government works or NASA-derived products, generally public
domain. Esri-hosted CTX/HiRISE mosaics are NASA data served by Esri Astro;
credit both. Perseverance images credit NASA/JPL-Caltech. USGS geologic map
credit: USGS Astrogeology Science Center. Include this in the app footer.
