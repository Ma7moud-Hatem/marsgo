# Demo Script — 3 minutes

**Setup:** app already running, browser full-screen on the tablet layout,
network off (to prove the cache). Have a backup screen recording.

---

## 0:00 — Hook (20 s)

> "Perseverance has spent five years proving a safe corridor across Jezero
> Crater. When humans arrive, they won't need a map of Mars. They'll need to
> know one thing: **can I walk there and back today?**
>
> This is TRAVERSE."

Show the map: Jezero at 5 m/px, rover path visible, three station pins.

---

## 0:20 — The layers (30 s)

Toggle, one at a time:

1. **CTX optical** — "5 metre per pixel. This is the ground truth."
2. **USGS geology** — "A published geologic map of Jezero, queryable, not a
   screenshot."
3. **CRISM/OMEGA minerals** — "Orbital spectroscopy says clays are here."
4. **Slope + roughness** — "Terrain the crew can and cannot cross."

> "Seven data types from six NASA missions. But layers are not a plan."

---

## 0:50 — The route (45 s)

Select objective: **Delta front stratigraphy**.
Select stations: **Heritage A, B, C** (Perseverance sols).
Press **Plan traverse**.

- Route animates/appears, clearly bending around the scarp.
- Call out the rover path: "That's the robot's proven corridor. The blue line is
  the human route — shorter, but only where the suit can handle it."

Read the stats:
> "4.8 km, 2 h 10 min, 96 m of ascent, max sustained slope 14°."

Point at the hazard layer:
> "The straight line would have crossed a 27° scarp. The router refuses to."

---

## 1:35 — The verdict (40 s)

Point at the big **GO** badge and the constraint table.

> "Time: 63% of the cap. O₂: 54% with a 25% walk-back reserve. Dose: 0.06 mSv,
> 0.01% of the career limit. Verdict: GO."

Now drag EVA duration down to 2 hours.

> "Same route, less slack. Now the reserve constraint fails first — and the tool
> tells us *which* constraint, not just 'no'. That's the difference between a
> map and a decision tool."

Switch to NO-GO.

---

## 2:15 — The station (30 s)

Tap **Station B**.

- Orbital close-up + Perseverance POV image.
- "Perseverance stood here on sol 700. The crew sees exactly what the rover saw
  before they take a step."
- Science card: unit name from the USGS map, mineral signature, sample priority,
  dwell time.

> "Every stop is ground-truthed before the crew leaves the habitat."

---

## 2:45 — Close (15 s)

> "Mars Trek tells you what Mars looks like.
> TRAVERSE tells you whether you can walk there and back.
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
