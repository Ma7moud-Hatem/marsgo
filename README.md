# MarsGo — Mango's Mars map

> **NASA Space Apps Challenge 2026 — Interplanetary Survival Guide: Martian Map**
> Team: **Mango's Gravity**

MarsGo is a suit-aware tablet field map for the first astronauts on Mars. It does not just
*display* Mars data — it turns layered NASA data into a **route an astronaut can
actually walk**, then tells the crew whether that walk is survivable.

**Mission:** EVA-1, Jezero Crater — follow the corridor Perseverance already
proved, on foot, to the delta front.

---

## The idea in one sentence

Mars Trek is a library of Mars data. **MarsGo is the briefing room**: pick a
science objective, and it produces a terrain-costed traverse with suit limits,
hazard no-go zones, radiation dose, weather, and photo-verified waypoints — plus
a clear **GO / NO-GO** verdict.

## Why this is different

| Existing tool | What it does | What it does not do |
|---|---|---|
| JPL Mars Trek | Global/regional layered map | Plan a walking EVA at 5 m scale |
| USGS geologic maps | Authoritative geology | Connect geology to a route or a suit |
| Rover raw images | Ground-level truth | Tie images to a planned station |
| **MarsGo** | **Suit-aware route + hazards + science stops** | — |

## Core features (MVP today)

1. **Hyperlocal Jezero map** — 4.83 m/px CTX basemap, USGS Jezero geologic map,
   CRISM/OMEGA spectral context (including an explicit null result in this AOI),
   and MOLA/HRSC terrain.
2. **Terrain-costed routing** — least-cost path over slope + surface roughness,
   with hard no-go limits (steep slopes, rough terrain, manual hazards).
3. **Suit & consumable model** — walk time, O₂, water, battery, walk-back reserve.
4. **Radiation + weather** — surface GCR dose budget, cached atmospheric
   conditions, dust and thermal risk windows.
5. **Heritage stations** — waypoints Perseverance actually visited, with sol
   provenance, HiRISE close-ups, and Mastcam-Z point-of-view imagery.
6. **GO / NO-GO panel** — the tool is allowed to say "this EVA is not safe."

## Stack

Python 3.12 · Streamlit · Folium · NumPy · SciPy · scikit-image · Pillow
All NASA data is **pre-fetched and cached** in `data/` so the demo works offline.

## Run it

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open <http://localhost:8501>. No network is used at runtime.

### Docker

```bash
docker build -t marsgo .
docker run --rm -p 8501:8501 marsgo
```

### Verify before deploying

```bash
.venv/bin/python scripts/smoke_test.py
```

## Hosting

The recommended path is **Streamlit Community Cloud** (free, HTTPS, deploys
from this GitHub repo), with Hugging Face Spaces as backup and local
`streamlit run app.py` as the offline guarantee.

See **[`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)** for the full plan, host
comparison, pre-flight checklist, and demo-day runbook.

## Rebuild the data cache

The app reads only cached files. To refresh them from the live NASA/USGS
services:

```bash
.venv/bin/python scripts/fetch_data.py
.venv/bin/python scripts/build_layers.py
```

## Repository map

```
app.py                  Streamlit field app
src/                    terrain, routing, suit model, data, weather, UI
scripts/                one-shot NASA data pipeline + smoke test
data/raw/               cached GeoJSON/JSON from NASA/USGS services
data/processed/         basemap, slope, roughness, hazard rasters
data/stations/          HiRISE station close-ups
assets/waypoints/       Perseverance POV images + sol metadata
docs/PLAN.md            full project & science plan
docs/DATA_SOURCES.md    every endpoint, verified
docs/ARCHITECTURE.md    how the system is built
docs/DEPLOYMENT.md      hosting plan and runbook
docs/ROADMAP.md         hour-by-hour build plan
docs/DEMO_SCRIPT.md     3-minute judging demo
Dockerfile              portable deployment image
.github/workflows/      CI smoke test
```

## Data credits

NASA/JPL Mars Trek · NASA PDS · USGS Astrogeology · Esri Astro (CTX/HiRISE
mosaics) · NASA Mars 2020 Perseverance · NASA MSL/REMS · CRISM/OMEGA/THEMIS
teams. See `docs/DATA_SOURCES.md` for exact services and licenses.
