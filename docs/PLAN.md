# TRAVERSE — Project Plan

**Challenge:** Interplanetary Survival Guide: Martian Map
**Team:** Mango's Gravity
**Build window:** one day (hackathon day)
**Site:** Jezero Crater, Mars (18.4°N, 77.45°E)
**Form factor:** tablet field app carried on EVA

---

## 1. The gap we are filling

NASA already gives us an extraordinary library of Mars data. Mars Trek layers
global imagery, topography and mineral maps. USGS publishes peer-reviewed
geologic maps. Perseverance has returned over a million images.

What does **not** exist is the thing an astronaut needs at 07:00 on EVA morning:

> "Here is the walk. Here is what it costs your suit. Here is what can kill you
> on the way. Here is what we will learn when we get there. Go or no-go?"

The challenge explicitly notes that current tools are built for **regional and
global views**, not the hyperlocal areas astronauts will target. That is the
opening. TRAVERSE is a hyperlocal **decision-support** layer, not another data
viewer.

### Design principle

> Every pixel on the map must either **change the route**, **change the
> go/no-go**, or **change the science plan**. If it does none of those, it is
> decoration and it gets cut.

---

## 2. Mission concept

### EVA-1: "Follow the robot"

Perseverance has spent years proving a safe corridor from the Octavia E. Butler
landing site toward the Jezero delta front. A human crew does not need to
rediscover that corridor from scratch — but they cannot simply copy it either,
because a rover can climb terrain and survive conditions a suited astronaut
cannot.

TRAVERSE takes the **rover's heritage corridor** as a prior, then re-plans it for
a walking human under suit constraints:

- the rover's route is shown as context (proven trafficability);
- the human route is offset/shortcut where slope and roughness allow;
- stations are placed at locations Perseverance actually investigated, so every
  science stop has **ground truth and imagery** before the crew arrives.

This is the strongest available answer to "why here, and why this route."

### Science objectives (ranked)

1. **Delta front stratigraphy** — read the lake-level history recorded in the
   delta foresets. Jezero held a lake ~3.7 Ga; the delta is the primary
   astrobiology target.
2. **Hydrated mineral ground-truthing** — CRISM/OMEGA detect phyllosilicates and
   carbonates from orbit; the crew confirms them at outcrop scale.
3. **Fine-grained unit sampling** — clay-rich mudstones are the best
   biosignature-preservation candidates.
4. **Surface processes / regolith** — dust, abrasion, and active surface change
   between orbital passes and the human visit.

Each objective maps to a **station type**, and each station type maps to a
required instrument and a dwell time. That is how the route becomes a *science*
plan rather than a walk.

### Why Jezero

- Richest combined dataset of any Mars site: CTX at 5 m/px, HiRISE coverage,
  full rover traverse, raw images, in-situ measurements.
- A published **USGS geologic map of Jezero Crater and Nili Planum** with
  queryable unit polygons — a real, citable science layer.
- Strong challenge fit: layered data, human exploration, astrobiology.
- Safe demo story: the audience already knows Perseverance's journey.

---

## 3. Data layers

The challenge asks for at least three data types. TRAVERSE uses **seven**.

| # | Type | Layer | Source | Resolution | Role in the app |
|---|---|---|---|---|---|
| 1 | Optical | CTX mosaic basemap | Esri Astro / NASA CTX | ~5 m/px | Navigation basemap |
| 2 | Optical (ground) | Perseverance Mastcam-Z / Navcam | NASA Mars 2020 raw images | cm–m | Station POV cards |
| 3 | Topographic | MOLA + HRSC blended DEM | NASA Mars Trek ImageServer | 200 m/px | Slope, elevation profile |
| 4 | Geologic | Jezero crater & Nili Planum map | USGS Astrogeology | 1:25k-ish polygons | Unit contacts, station justification |
| 5 | Spectral | Hydrous minerals (CRISM/OMEGA), chlorides (THEMIS) | Mars Trek MapServers | regional | Science target scoring |
| 6 | Thermal | THEMIS thermal / surface temperature context | Mars Trek / THEMIS | regional | EVA thermal window |
| 7 | Atmospheric | REMS/MSL weather + MEDA context | NASA Mars weather API | sol | Current conditions, dust risk |
| 8 | Radiation | MSL RAD surface dose | NASA/JPL published | daily | Dose budget, SPE flag |

**Honest limitation, stated in the UI:** the public global DEM is 200 m/px, so
slope is a *regional* product. TRAVERSE compensates with a 5 m/px **surface
roughness** layer derived from CTX texture, which catches local rock fields and
scarps that the DEM cannot resolve. The UI labels both, and the route cost
combines them. This is a feature, not a hidden flaw: it shows we understand the
resolution limits of our own data.

---

## 4. What the app does

### Mode 1 — PLAN (pre-EVA, habitat tablet)

- Choose science objectives and EVA duration.
- Select heritage stations (Perseverance sols) or tap candidate targets.
- App computes a least-cost route and shows:
  - distance, duration, ascent/descent
  - max sustained slope
  - O₂ / water / battery use vs. reserve
  - radiation dose for the EVA
  - hazard crossings
- **GO / NO-GO** with the specific blocking reason.

### Mode 2 — WALK (on EVA, glove-friendly)

- Large-type next-waypoint card: bearing, distance, terrain warning.
- Layer toggles limited to three: route, hazards, stations.
- Station card: orbital close-up + rover POV image + "what to sample here."
- Off-nominal banner: dust opacity rising, dose threshold, reserve below 25%.

### Mode 3 — DEBRIEF (stretch)

- Export the traverse as a GeoJSON + a science log skeleton.

MVP = PLAN + WALK. DEBRIEF only if time allows.

---

## 5. Routing model

### Cost surface

Grid at 5 m/px over the mission box. Per cell:

```
cost = 1.0
     + 3.0 * slope_norm          # energy penalty
     + 2.5 * roughness_norm      # rock / scarp penalty
     + 8.0 * (slope > 15°)       # strong avoidance
     + inf * (slope > 25°)       # hard no-go (suit fall risk)
     + inf * manual_hazard       # crew-marked no-go
```

`slope` comes from the DEM, upsampled to the route grid; `roughness` is local
variance of the CTX basemap (a defensible texture proxy for rock abundance).

### Path

- Ordered station list (start → S1 → S2 → … → start).
- Pairwise least-cost path with `skimage.graph.route_through_array`.
- Optional shortcut pass: if a straight segment is hazard-free and shorter than
  the cost path by >15%, prefer it (walking humans cut corners).
- Smooth the result (Chaikin) and recompute true distance/elevation on the
  smoothed line.

### Why not A* on 200 m DEM alone?

Because a 200 m cell can hide a 20 m scarp. The roughness layer is what makes
the route credible at human scale. This trade-off is stated explicitly in the
UI and in the demo.

---

## 6. Suit and consumable model

All parameters live in `src/suit.py` and are editable in the sidebar. Defaults
are labeled **"planning assumptions (demo)"**, not NASA flight rules.

| Parameter | Default | Basis |
|---|---|---|
| Walk speed, flat | 1.5 km/h | Conservative suited traverse estimate |
| Speed penalty | +6% time per 1° slope | Uphill energy cost |
| EVA duration cap | 8 h | PLSS-class limit |
| Walk-back reserve | 25% | Always keep enough to return |
| O₂ | 1.0 kg capacity, 0.09 kg/h | Representative PLSS budget |
| Water | 2.5 L, 0.15 L/h | Representative |
| Battery | 8 h at nominal load | Representative |
| Radiation | 0.03 mSv/h surface | Derived from MSL RAD ~0.7 mSv/day |
| Career limit | 600 mSv | NASA 2022 standard, conservative |

Outputs: time, reserve %, dose, thermal load, and a pass/fail per constraint.
The app shows **which constraint failed first** — that is the actionable part.

---

## 7. Safety model

Astronaut safety is the first judging criterion, so it gets its own panel:

1. **Terrain** — slope > 25° no-go; 15–25° flagged; roughness hot spots flagged.
2. **Radiation** — EVA dose + cumulative career tracking; solar particle event
   banner forces return-to-hab.
3. **Thermal** — surface temperature and time-of-day; night EVA doubles heater
   load and cuts battery reserve.
4. **Dust** — atmospheric opacity (tau); high tau degrades solar power and
   visibility, and triggers a no-go.
5. **Distance/reserve** — walk-back reserve is a hard constraint, not a warning.
6. **Comms** — line-of-sight to the lander is a stretch goal; if implemented,
   it becomes a route cost term.

---

## 8. Judging alignment

| Criterion | How TRAVERSE scores |
|---|---|
| Use of NASA data | 7 data types, 6+ NASA missions, all real endpoints |
| Science quality | Published USGS Jezero map + CRISM mineralogy + real rover stations |
| Astronaut safety | Hard no-go rules, reserve, radiation, dust, thermal |
| Human-centered design | Glove-friendly WALK mode, GO/NO-GO, next-waypoint card |
| Innovation | Suit-aware routing; tool is allowed to reject the plan |
| Feasibility | Everything runs offline from cached data; no fantasy tech |
| Presentation | One mission, one route, one verdict, photo-verified stops |

**The line we want judges to remember:**
> "Mars Trek tells you what Mars looks like. TRAVERSE tells you whether you can
> walk there and back."

---

## 9. Scope discipline

### Must ship today
- Cached CTX basemap + DEM + geology + minerals
- Rover traverse + heritage stations + POV images
- Least-cost route with slope/roughness
- Suit budget + GO/NO-GO
- Weather + radiation panel
- Working Streamlit tablet UI

### Nice to have
- Manual hazard drawing
- Two-site comparison
- 3D terrain fly-through
- Debrief export
- Comms line-of-sight

### Explicitly out of scope
- Real-time rover control
- Full MEDA archive ingest
- 1 m HiRISE DTM processing
- Multi-user collaboration
- Flight-qualified anything

---

## 10. Risks and mitigations

| Risk | Mitigation |
|---|---|
| ArcGIS tile service changes during demo | All layers pre-cached to PNG/GeoJSON; app reads local files |
| 200 m DEM too coarse | Roughness layer + explicit UI disclosure + manual hazards |
| HiRISE mosaic 404 over Jezero | Use CTX for basemap; use raw rover images for close-ups |
| Route looks arbitrary | Anchor stations to real Perseverance sols; show rover path as prior |
| Streamlit interaction feels clunky | Fixed mission box, few controls, large touch targets |
| Time runs out | Docs + data pipeline + one route are enough for a complete story |

---

## 11. Success definition

At demo time, a judge can:
1. See Jezero at 5 m/px with geology and minerals.
2. Pick a science objective.
3. Watch a route appear that avoids a visible scarp.
4. Read a GO/NO-GO with a specific reason.
5. Open a station and see the actual Perseverance image from that spot.
6. Ask "what if we add 2 km?" and watch the tool say NO-GO.

That is a complete product, not a prototype.
