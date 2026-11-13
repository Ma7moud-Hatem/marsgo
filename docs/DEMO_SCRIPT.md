# Demo Script — 3 minutes

**Setup:** app already running, browser full-screen on the tablet layout,
network off (to prove the cache). Have a backup screen recording.

---

## 0:00 — Hook (20 s)

> "Perseverance has spent five years proving a safe corridor across Jezero
> Crater. When humans arrive, they won't need a map of Mars. They'll need to
> know one thing: **can I walk there and back today?**
>
> This is MarsGo."

Show the map: Jezero at 4.8 m/px, rover path visible, three station pins.

---

## 0:20 — The layers (30 s)

Toggle, one at a time:

1. **CTX optical** — "4.8 metres per pixel. This is the ground truth."
2. **USGS geology** — "A published geologic map of Jezero, queryable, not a
   screenshot."
3. **Slope + no-go terrain** — "Terrain the crew can and cannot cross."
4. **Roughness** — "A 4.8 m/px texture proxy for rocks the 200 m DEM can't see."
5. **CRISM/OMEGA context** — "We ingested the spectral layer too. Inside this
   AOI it returns a null detection — which is itself a science result the crew
   can ground-truth."

> "Seven data types from six NASA missions. But layers are not a plan."

---

## 0:50 — The route (45 s)

Select objective: **Delta front stratigraphy**.
Select stations: **Heritage A, B, C** (Perseverance sols 1042, 1108, 1170).
Press **Plan traverse**.

- Route appears, clearly hugging the rover's proven corridor outbound.
- Call out the rover path: "That's the robot's proven corridor. The cyan line is
  the human route — it uses the corridor, but only where the suit can handle it."

Read the stats:
> "4.1 km round trip, 2 h 57 min, 84 m of ascent, 6.9° sustained slope, peak
> 7.5°. Zero no-go samples on the line."

Point at the return leg:
> "The direct walk home is 1.1 km. The router takes 2.0 km instead, because the
> straight line clips no-go terrain. It is refusing a shortcut a human might
> take."

---

## 1:35 — The verdict (40 s)

Point at the big **GO** badge and the constraint table.

> "Time: 49% of the 6-hour cap. O₂: 27% used, 73% left. Water: 18% used.
> Walk-back reserve: 51%. Dose: 0.088 mSv, 0.01% of the career limit.
> Verdict: GO."

Now drag EVA duration down to 2 hours.

> "Same route, less slack. Now the duration constraint fails first — and the
> tool tells us *which* constraint, not just 'no'. That's the difference between
> a map and a decision tool."

Switch to NO-GO. For a second failure mode, toggle **Dust-storm hold** or
**Solar particle event**.

---

## 2:15 — The station (30 s)

Choose **Station B** in the Station detail panel.

- Orbital HiRISE close-up + Perseverance Mastcam-Z image.
- "Perseverance stood here on sol 1108. The crew sees exactly what the rover saw
  before they take a step."
- Science card: unit name from the USGS map, spectral context, sample priority,
  dwell time.

> "Every stop is ground-truthed before the crew leaves the habitat."

Optional 10 s: toggle **Field mode** to show the glove-friendly next-waypoint
card: `W 259° · 609 m · max slope 1.9°`.

---

## 2:45 — Close (15 s)

> "Mars Trek tells you what Mars looks like.
> MarsGo tells you whether you can walk there and back.
>
> The first Martians won't have streets. They'll have a traverse."

---

## Judge questions — prepared answers

**"Why not just use Mars Trek?"**
Mars Trek is built for regional and global views, as the challenge brief says.
It has no concept of a suit, a reserve, or a walk-back. We consume its data and
add the decision layer.

**"Your DEM is only 200 m/px. How can you route safely?"**
Correct — and the UI says so. That's why we add a 5 m/px roughness layer from
CTX texture and hard no-go thresholds. For flight, we would ingest HiRISE
stereo DTMs; the architecture already supports swapping the DEM.

**"Is the rover path actually walkable?"**
Not necessarily — and that's the point. We use it as a prior, not a mandate. The
human route diverges wherever slope or roughness exceeds suit limits.

**"Where does the radiation number come from?"**
MSL RAD surface GCR, ~0.7 mSv/day. We model EVA dose at 0.03 mSv/h and treat a
solar particle event as an automatic return-to-hab.

**"Could this work at another site?"**
Yes. Change the mission box and point the loader at another site's layers. The
routing and suit models are site-agnostic.

**"What did you build in one day?"**
A working data pipeline, a terrain-costed router, a suit model, and the app.
Everything you saw is running locally from cached NASA data.
