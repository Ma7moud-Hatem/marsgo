# Build Roadmap — one day

Assume ~10 focused hours. Times are relative (`H+0` = now). Each block ends with
a **checkpoint you can demo**, not a task you hope finished.

---

## H+0 — Repo and skeleton (30 min)

- [x] `git init`, `.gitignore`, README, docs
- [ ] `requirements.txt`, venv install
- [ ] `src/config.py`, `src/data.py` stubs
- [ ] GitHub repo created and pushed

**Checkpoint:** repo opens on GitHub with the plan visible.

---

## H+1 — Data pipeline (2 h)

`scripts/fetch_data.py`

1. Traverse GeoJSON → simplify → `data/raw/traverse.geojson`
2. Waypoints + landing ellipse → `data/raw/`
3. USGS geologic units clipped to mission box → `data/raw/geology.geojson`
4. Mineral detection layers (CRISM/OMEGA/THEMIS) → `data/raw/minerals.geojson`
5. DEM export → `data/raw/dem.tif`
6. Weather snapshot → `data/raw/weather_snapshot.json`
7. Perseverance POV images for 3 stations → `assets/waypoints/`

**Checkpoint:** `ls data/raw` shows every file; a notebook/CLI prints counts
and bboxes. Nothing is fetched at runtime.

**If time is short:** ship steps 1, 2, 3, 5. Minerals and POV images are
enhancements.

---

## H+3 — Basemap and derived rasters (1.5 h)

`scripts/build_layers.py`

1. Fetch CTX z12 tiles over mission box → stitch → `basemap_ctx.png`
2. Load DEM → resample to route grid → `slope.npy`, `elevation.npy`
3. CTX local std-dev → `roughness.npy`
4. Compose `slope.png`, `roughness.png`, `hazard.png` (transparent overlays)

**Checkpoint:** open the PNGs. The scarp and rough terrain must be visible.
If the slope overlay is noise, the DEM is too coarse — smooth before rendering.

---

## H+4.5 — Route engine (1.5 h)

`src/routing.py`

1. Cost surface from slope + roughness + hard no-go
2. Pairwise `route_through_array`
3. Chain stations, smooth, resample
4. Stats: distance, ascent, max slope, duration at default speed
5. Cache result

**Checkpoint:** CLI prints a route for `start → station A → start` with
distance and max slope. Plot it once with matplotlib to sanity-check.

---

## H+6 — Suit model + verdict (1 h)

`src/suit.py`

1. Time from distance + slope penalty
2. O₂, water, battery, reserve
3. Radiation dose
4. Ordered verdict with blocking reason
5. Unit tests for: nominal, too long, too steep, SPE, low reserve

**Checkpoint:** `pytest` (or a simple assert script) shows 5/5 cases pass.

---

## H+7 — Streamlit app (2 h)

`app.py`

1. Header: mission, sol, weather chip, GO/NO-GO badge
2. Sidebar: objectives, stations, EVA duration, layer toggles
3. Map: basemap + overlays + traverse + route + stations
4. Panels: route stats, suit budget, safety, station card
5. WALK mode: simplified layout, big next-waypoint card

**Checkpoint:** a person who has not seen the code can click through the demo
without help.

---

## H+9 — Polish and rehearsal (1 h)

- Empty/error states
- Loading spinners only where needed
- Footer credits and data disclaimer
- 3× timed run of `docs/DEMO_SCRIPT.md`
- Record a 60 s backup screen capture

**Checkpoint:** demo runs end-to-end twice in a row with no network.

---

## H+10 — Submission (30 min)

- Push final commit
- README screenshots
- Verify repo is public
- Write the submission text from the demo script
- List data credits

---

## Priority if you fall behind

Cut in this order:

1. Debrief mode
2. Mineral layer
3. Manual hazard drawing
4. POV images (replace with orbital crops)
5. Weather panel (keep radiation)
6. Roughness layer (keep slope) — **last resort**, it weakens the safety story

**Never cut:** the route, the GO/NO-GO, and the station cards. Those are the
product.

---

## Definition of done

- [ ] App runs offline from a clean checkout
- [ ] Route visibly avoids at least one hazard
- [ ] NO-GO case demonstrable by extending the EVA
- [ ] Every layer has a source, resolution, and purpose in the UI
- [ ] 3-minute demo rehearsed
- [ ] Repo public with README, docs, and data credits
