# MarsGo — Jezero Crater Suit-Aware EVA Field Map

> **NASA Space Apps Challenge 2026 — Interplanetary Survival Guide: Martian Map**
> **Team:** Mango's Gravity 🇪🇬

---

## 1. The Problem (المشكلة)

Existing planetary GIS tools such as **JPL Mars Trek** and **USGS Astrogeology maps** are extraordinary libraries of orbital imagery and geologic polygons, while **Mars 2020 Perseverance raw images** capture ground-level reality. However, **none of them answer the operational question an astronaut crew actually faces before stepping out of the airlock**:

- *Can a suited astronaut safely walk this corridor on foot, visit high-priority science stations, and return with sufficient $O_2$, cooling water, battery power, and radiation margin?*

---

## 2. The Solution (الحل)

**Mars Trek is a library of Mars data. MarsGo is the Mission Control briefing room.**

Pick a science objective in Jezero Crater, and **MarsGo** computes a terrain-costed round-trip walking traverse at 10 m grid scale, evaluates every segment against **xEMU Portable Life Support System (PLSS)** consumables and **MSL RAD** radiation baselines, verifies that path smoothing never clips a hazard cell, calculates emergency **Abort / Walk-Back** checkpoints, and issues a transparent **GO / NO-GO** verdict with uncertainty ranges and sensitivity analysis.

---

## 3. Why MarsGo Stands Out (التميّز العلمي والتقني)

| Tool / Platform | What It Does | What It Does Not Do | How MarsGo Solves It |
|---|---|---|---|
| **JPL Mars Trek** | Global/regional orbital layers | Plan a walking EVA or check suit limits | Converts DEM + CTX layers into a 10 m cost surface with A* routing |
| **USGS SIM 3464 Map** | Authoritative Jezero geologic units | Connect geology to walk time or $O_2$ burn | Links point-in-polygon geologic units directly to EVA stations |
| **Rover Raw Imagery** | Ground-level camera frames | Tie POV frames to orbital HiRISE context | Side-by-side **HiRISE (0.6 m/px) + Perseverance POV** station cards |
| **MarsGo (Mission Control)** | **Suit-aware route + Uncertainty + Sensitivity + Abort Walk-Back + Arabic/English UI** | — | Complete offline-capable tablet & mission control cockpit |

### Key Scientific & Engineering Upgrades
1. **Honest Spatial Resolution & Provenance:** Explicitly discloses that the 10 m routing grid interpolates regional slopes from the **200 m/px MOLA/HRSC Blended DEM** (unless a 1 m HiRISE DTM is loaded) and labels CTX luminance variance as **Surface Texture Index (CTX optical proxy)**.
2. **Unified Safety Thresholds (`src/config.py`):** Single source of truth across `terrain.py`, `routing.py`, `suit.py`, and `ui.py` (`slope_nogo_deg = 22.0°`, `slope_warn_deg = 15.0°`, `reserve_frac = 25%`).
3. **Chaikin Path Smoothing with Strict No-Go Verification:** Sub-segments and all 4 bilinear grid neighbors are checked against `cost_surface` after smoothing; if any smoothed segment touches a no-go cell (`NO_GO_COST` or `inf`), the router automatically reverts to the verified raw grid path.
4. **Uncertainty & Sensitivity Analysis:** Reports intervals for walk duration ($\pm 12\%$), $O_2$ consumption ($\pm 10\%$), and radiation dose, plus an interactive **Sensitivity Test** showing whether a $+10\%$ slope perturbation flips the **GO / NO-GO** verdict.
5. **Multi-Mode Routing & Abort Checkpoints:** Compare **Fastest**, **Safest (Min-Slope)**, **Lowest Energy & $O_2$**, and **Balanced** routes side-by-side, inject custom circular **Manual Hazard Zones** on the map, and inspect 8 **Abort / Walk-Back** checkpoints along the route.
6. **Mission Control Dark UI + Bilingual Support (EN / العربية):** Styled with `#0B0F14` dark background, `#121923` surfaces, `#E2623A` Mars orange accent, `#3DDC84` GO / `#FF4D4D` NO-GO pulsing badges, `Space Grotesk` + `JetBrains Mono` typography, tablet **WALK Mode**, one-click judge scenarios, and full **Arabic / English** localization.

---

## 4. Quickstart & Verification (التشغيل والاختبار)

### Local Setup (100% Offline Runtime)

```bash
# 1. Clone repository
git clone https://github.com/Ma7moud-Hatem/marsgo.git
cd marsgo

# 2. Create virtual environment & install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Run unit tests & deployment smoke checks
pytest -v
python scripts/smoke_test.py

# 4. Launch Mission Control UI
streamlit run app.py
```

### Docker Setup (Offline Container)

```bash
docker build -t marsgo .
docker run -p 8501:8501 marsgo
```

---

## 5. Data Sources & Scientific References

- **Topography & DEM:** NASA/JPL Mars Trek MOLA/HRSC Blended DEM (200 m/px native).
- **Optical Basemap & Surface Texture Index:** Esri Astro / Caltech Murray Lab MRO CTX Mosaic (4.83 m/px) & HiRISE close-ups (~0.6 m/px).
- **Geologic Map:** Sun, V.Z., & Stack, K.M. (2020), *Geologic map of Jezero crater and the Nili Planum region, Mars*, USGS Scientific Investigations Map 3464.
- **Radiation Baseline:** Hassler, D.M., et al. (2014), *Mars' Surface Radiation Environment Measured with the Mars Science Laboratory's Curiosity Rover (MSL RAD)*, Science 343(6169), and NASA-STD-3001 career limits.
- **Weather Analog:** NASA MSL REMS (Gale Crater analog snapshot cached offline).
