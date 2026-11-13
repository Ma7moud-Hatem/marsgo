# Architecture

## 1. Shape of the system

```
                    ┌──────────────────────────────┐
                    │  NASA / USGS / Esri services │
                    └──────────────┬───────────────┘
                                   │  scripts/fetch_data.py
                                   │  (once, today, with retries)
                                   ▼
        ┌──────────────────────────────────────────────────┐
        │ data/raw/          data/processed/               │
        │  traverse.geojson   basemap_ctx.png              │
        │  waypoints.geojson  slope.npy / slope.png        │
        │  geology.geojson    roughness.png                │
        │  minerals.geojson   hazard.npy                   │
        │  dem.tif            stations.geojson             │
        │  weather_snapshot   meta.json                   │
        └──────────────────────┬───────────────────────────┘
                               │  local reads only at runtime
                               ▼
        ┌──────────────────────────────────────────────────┐
        │                  app.py (Streamlit)              │
        │  sidebar controls · map · analysis panels        │
        └───────┬──────────────┬──────────────┬────────────┘
                │              │              │
          src/terrain.py  src/routing.py  src/suit.py
          slope/roughness  least-cost      consumables
          cost surface     path             radiation
                │              │              │
                └──────────────┴──────────────┘
                               ▼
                    Folium map + GO/NO-GO
```

**Design rule:** the runtime never depends on a live NASA request. If the
network dies during judging, the demo still works.

## 2. Why Streamlit + Folium

The team is Python-first and the build window is one day.

- Streamlit gives a credible tablet UI with zero frontend build step.
- Folium/Leaflet gives smooth pan/zoom and image overlays without a custom CRS.
- Raster layers are **pre-rendered PNGs** georeferenced to a fixed lat/lon box,
  so we avoid Mars-projection math in the browser entirely.
- SciPy/scikit-image provide the routing and texture analysis.

Trade-off: Streamlit reruns the script on every control change. Mitigations:
- `@st.cache_data` on all loaders and on route computation.
- Fixed mission bbox, so overlays never need to be re-fetched.
- Keep the widget count low.

## 3. Fixed mission box

All layers share one geographic box around the Perseverance corridor:

```
lon 77.24 → 77.52
lat 18.38 → 18.53
```

At CTX z12 (~4.8 m/px) this is roughly 2,700 × 1,500 px — one cached basemap,
no tile fetching at runtime.

## 4. Terrain pipeline

1. Export DEM for the box at the highest available resolution (200 m source).
2. Upsample to the 10 m route grid with bilinear interpolation.
3. Compute slope in degrees with `numpy.gradient`, accounting for Mars radius
   (3,396,190 m) and latitude scaling in longitude.
4. Compute roughness from the CTX basemap: local standard deviation (e.g. 9×9
   window) normalized to 0–1.
5. Build the cost surface:

```python
cost = 1.0
cost += 3.0 * norm(slope)
cost += 2.5 * norm(roughness)
cost[slope > 15] += 8.0
cost[slope > 22] = np.inf     # mapped no-go (25° is the absolute suit limit)
cost[manual_hazard] = np.inf
```

6. Save `slope.npy`, `roughness.npy`, `elevation.npy` for instant routing and
   profile sampling. The cost surface is rebuilt in-process on first use.

The DEM is coarse; the roughness layer carries the human-scale signal. The UI
states this explicitly on the Terrain panel.

## 5. Routing pipeline

```python
from skimage.graph import route_through_array

path, cost = route_through_array(
    cost_surface,
    start_rc,
    end_rc,
    fully_connected=True,
    geometric=True,
)
```

- Station order is chosen by the user or by a greedy nearest-neighbour pass.
- Each leg is routed independently, then concatenated.
- The concatenated line is smoothed (Chaikin, 2 iterations) and re-sampled.
- True length and elevation gain are computed **after** smoothing.

Route cache key: `(start, tuple(stations), objective, speed, hazard_version)`.
Route results are memoized in-process with `st.cache_data` keyed by
`(station order, speed)`, so repeated demo clicks are instant. A persistent
route cache is intentionally not used at this scale.

## 6. Suit model

Pure functions in `src/suit.py`, no Streamlit imports, fully unit-testable.

```
inputs:  distance_km, ascent_m, descent_m, duration_cap_h,
         speed_kmh, reserve_frac, o2_kg, water_l, battery_h,
         radiation_mSv_per_h, solar_event
outputs: duration_h, o2_used, water_used, battery_used,
         reserve_left, dose_mSv, verdict, blocking_reason
```

Verdict precedence (first failure wins and is surfaced):

1. solar particle event → NO-GO
2. route exceeds duration cap → NO-GO
3. reserve below minimum → NO-GO
4. max slope above limit on any segment → NO-GO
5. dust opacity above threshold → NO-GO
6. otherwise GO, with warnings listed

## 7. Module layout

| File | Responsibility |
|---|---|
| `app.py` | Streamlit layout, state, map assembly |
| `src/config.py` | Mission constants, bbox, paths, colors |
| `src/data.py` | Cached loaders for GeoJSON/PNG/NPY/JSON |
| `src/terrain.py` | DEM → slope, CTX → roughness, cost surface |
| `src/routing.py` | Least-cost path, smoothing, stats |
| `src/suit.py` | Consumables, radiation, verdict |
| `src/weather.py` | Weather snapshot + fallback |
| `src/ui.py` | Panels, station cards, CSS |
| `scripts/fetch_data.py` | One-shot data pipeline |
| `scripts/build_layers.py` | Raster/derived layer builder |

## 8. Performance budget

| Operation | Target |
|---|---|
| App cold start | < 4 s |
| Layer toggle rerun | < 1.5 s |
| Route computation (3 stations) | < 2 s |
| Map HTML size | < 8 MB |

If a layer exceeds budget, downsample the PNG, not the science.

## 9. Failure modes and fallbacks

| Failure | Fallback |
|---|---|
| No network | All runtime reads are local |
| CTX fetch fails | Ship a downsampled basemap in the repo |
| DEM export fails | Slope from synthetic/flat surface + warn in UI |
| Geology query too large | Clip to bbox + simplify geometry |
| Weather API down | `weather_snapshot.json` with timestamp |
| Route grid too big | 20 m grid instead of 10 m |

## 10. What we are deliberately not building

- A tile server (static PNG overlays are enough at this scale)
- A database (files are enough)
- Authentication (single-crew tool)
- 3D globe (Folium 2D is more legible on a tablet)
- Real-time telemetry (out of scope and not needed for the story)
