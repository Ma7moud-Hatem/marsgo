# Deployment & Hosting Plan

**Goal:** put MarsGo on a public HTTPS URL for judging, with an offline local
fallback that cannot fail because of venue Wi-Fi.

The app is deliberately easy to host:

- **No API keys, no secrets, no database, no user accounts.**
- Every NASA layer is already cached in `data/` and committed to the repo.
- Runtime reads are local file reads only. There is no live NASA request.
- CPU profile is small: ~0.5 vCPU and < 1 GB RAM; the 10 m route solves in
  ~0.3 s and the full page renders in 2–4 s.
- The repo is ~20 MB, well under GitHub and host limits.

---

## 1. Recommended: Streamlit Community Cloud (free)

Best fit for a one-day hackathon: GitHub-native, HTTPS included, redeploys on
every push, and no container or DNS work.

### Steps

1. Confirm the final commit is on `master`:
   ```bash
   git push origin master
   ```
2. Open <https://share.streamlit.io> and sign in with GitHub.
3. **New app** → repository `asaadzx/marsgo` → branch `master` →
   main file `app.py`.
4. In **Advanced settings**, select **Python 3.12**.
5. Deploy. The first build takes roughly **2–5 minutes** because it installs
   SciPy and scikit-image.
6. Open the URL (typically `https://marsgo.streamlit.app`), then test it from
   the actual tablet.

### Why this one

| Need | Streamlit Community Cloud |
|---|---|
| Cost | $0 |
| HTTPS URL | Included |
| Deploy from GitHub | Native |
| Auto-redeploy on push | Yes |
| Secrets/config | None needed |
| Data in repo | Copied at build |
| RAM for SciPy/skimage | Sufficient |
| Custom domain | Not on the free tier |

### Caveats to plan around

- Apps are **public**. That is fine here: all data is public NASA/USGS and the
  app has no user input storage.
- Free apps **sleep after inactivity**. Open the app 10 minutes before judging
  so the container is warm, and keep the tab open.
- Shared CPU can make the first route a second slower. The route cache and
  `@st.cache_data` make repeat clicks instant.
- The free tier can change. Keep the Docker path below as a fallback.

---

## 2. Backup: Hugging Face Spaces (Docker, free)

Good fallback because the repo already has a `Dockerfile` and free CPU/RAM is
generous for SciPy.

1. Create a new **Space** → SDK: **Docker** → blank.
2. Push this repo to the Space, or connect the GitHub repo.
3. The Space README needs this frontmatter (add it only on the Space copy, not
   the main repo):
   ```yaml
   ---
   title: MarsGo
   sdk: docker
   app_port: 8501
   ---
   ```
4. The included `Dockerfile` builds and serves on port 8501.
5. Test the Space URL on the tablet.

Trade-off: a second URL to maintain, but it is independent of Streamlit Cloud
and stays close to the same code.

---

## 3. Always-on options

Use one of these only if the free tiers fail or the demo needs a guaranteed
warm instance.

| Host | Cost | Cold start | Notes |
|---|---|---|---|
| **Fly.io** | Free allowance / usage-based | Scale-to-zero unless pinned | Docker deploy; `fly scale count 1` keeps one machine warm. Custom domains. |
| **Render** | Free web service | ~30–60 s after 15 min idle | 512 MB may be tight for SciPy + map render; test first. |
| **Google Cloud Run** | Free monthly allowance | Scale-to-zero; set min instances = 1 for demo day | Supports WebSockets; container deploy; more setup. |
| **Railway** | Trial credit | Fast | Simple Docker deploy; credit may expire. |
| **VPS (Hetzner/DigitalOcean)** | ~$5/month | None | Docker + Caddy for HTTPS. Most reliable, not free. |

### Fly.io quick path

```bash
fly launch --no-deploy          # accept the existing Dockerfile
fly deploy
fly scale count 1               # keep one machine warm for judging
fly open
```

### Docker anywhere

```bash
docker build -t marsgo .
docker run --rm -p 8501:8501 marsgo
# open http://localhost:8501
```

The container health check hits `/_stcore/health`.

---

## 4. Primary fallback: run it locally

If venue Wi-Fi fails, the app still runs with **no network**:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open `http://localhost:8501` on the tablet browser, or use the laptop and
screen-share. This is the most reliable demo path because every data file is
already on disk.

**Before the demo:** run the app once with Wi-Fi disabled to prove it.

---

## 5. Deployment artifacts in this repo

| File | Purpose |
|---|---|
| `requirements.txt` | Exact tested versions |
| `.streamlit/config.toml` | Dark theme, headless server, telemetry off |
| `Dockerfile` | Portable image for HF Spaces, Fly, Cloud Run, VPS |
| `.dockerignore` | Keeps the image small (no venv, git, DEM TIFF) |
| `scripts/smoke_test.py` | Data + route + GO/NO-GO assertions |
| `.github/workflows/smoke.yml` | CI on every push |

### Smoke test

```bash
.venv/bin/python scripts/smoke_test.py
```

It checks that the cache exists, the basemap and station images are real, the
route solves, the nominal plan is GO, and the dust-storm case is NO-GO.

---

## 6. Pre-deploy checklist

- [ ] `python scripts/smoke_test.py` passes.
- [ ] `streamlit run app.py` works with the network disabled.
- [ ] Route appears, verdict is GO, 3 stations are pinned.
- [ ] Dust-storm toggle produces NO-GO with a specific reason.
- [ ] Field mode shows a large next-waypoint card.
- [ ] Station tabs show HiRISE close-up **and** Perseverance POV.
- [ ] Page usable at a 1280 × 800 tablet viewport.
- [ ] Repo has no file over 100 MB and is public.
- [ ] `data/raw/dem.tif` is absent from git (ignored; not needed at runtime).
- [ ] README has the live URL.

---

## 7. Post-deploy validation

1. `GET https://<app>/_stcore/health` returns `ok`.
2. Page title is **MarsGo — Jezero EVA planner**.
3. The header shows the rover weather chip and the **GO** badge.
4. Route stats: ~4.1 km, ~3 h, ~84 m ascent, 0 hazard samples.
5. Toggle **Dust-storm hold** → badge flips to **NO-GO**.
6. Toggle **Field mode** → next waypoint card appears.
7. Open **Station detail → Rover POV** → Mastcam-Z image loads.
8. Reload twice; no build or data errors in host logs.

---

## 8. Operations

- **Deploy trigger:** push to `master` → Streamlit Cloud / HF rebuild.
- **Logs:** Streamlit Cloud dashboard, or `docker logs`.
- **Health:** `/_stcore/health`.
- **Rollback:** revert the commit and push, or redeploy the previous commit in
  the host dashboard. Data is versioned with the code, so a rollback is complete.
- **Warm-up:** load the app and press **Plan traverse** once before judging.
- **Monitoring:** not needed for a demo; the smoke test is the regression net.

---

## 9. Security and privacy

- No secrets, tokens, credentials, or `.env` files.
- No user accounts and no stored user data.
- All inputs are ephemeral widget state.
- All data is public-domain NASA/USGS or NASA-derived Esri-hosted imagery.
- If a private demo is ever needed, put Cloudflare Access or Streamlit OAuth in
  front of the app; do not add auth code to the app for the hackathon.

---

## 10. Demo-day runbook

| Time | Action |
|---|---|
| T-24 h | Deploy to Streamlit Cloud; run the post-deploy checklist. |
| T-2 h | Push the final commit; confirm auto-redeploy finished. |
| T-30 min | Open the app, plan the traverse, keep the tab warm. |
| T-10 min | Run through GO → NO-GO → field mode → station card once. |
| T-0 | Present from the hosted app. |
| If Wi-Fi fails | Switch to `localhost:8501` (local venv) or the recorded 60 s backup. |

**Decision:** Streamlit Community Cloud is primary; Hugging Face Spaces is the
hot backup; local `streamlit run app.py` is the offline guarantee.
