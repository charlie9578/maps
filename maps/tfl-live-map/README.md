# tfl-live-map

Interactive **Dash** dashboard showing the **live (best-available) location of London Underground trains**, derived from the **TfL Unified API arrivals predictions**.

Important limitation: the public API does **not** provide GPS coordinates for Tube trains. Positions are **estimated** by interpolating along the **previous → next** stop on the line route (using cached route sequences with station ids), based on `timeToStation` to the next predicted stop.

**Refresh behaviour:** TfL data is fetched every **30 seconds**. Train markers move smoothly on the map via a **client-side** animation that only updates the train layer (routes, stations, charts, and table do not re-render every tick). Default animation interval is **500 ms**; override with `TFL_ANIMATION_MS` in `.env` if needed.

## Data source (required)

- **Dataset / API**: Transport for London (TfL) Unified API
- **Publisher**: Transport for London
- **Portal**: [https://api-portal.tfl.gov.uk/](https://api-portal.tfl.gov.uk/)
- **Interactive docs (Swagger UI)**: [https://api.tfl.gov.uk/swagger/ui/index.html](https://api.tfl.gov.uk/swagger/ui/index.html)
- **Accessed**: 2026-06-02
- **License / terms**: See the TfL API portal “Terms & Conditions” / “Data use” pages for current terms.

### API endpoints used by this map

| Purpose | Method | Example | Swagger |
|--------|--------|---------|---------|
| **Live train arrivals** (refreshed every 30s) | `GET` | [`/Line/victoria/Arrivals`](https://api.tfl.gov.uk/Line/victoria/Arrivals) | [Line → Arrivals](https://api.tfl.gov.uk/swagger/ui/index.html#!/Line/Line_Arrivals) |
| Line list (tube) | `GET` | [`/Line/Mode/tube`](https://api.tfl.gov.uk/Line/Mode/tube) | [Line → Mode](https://api.tfl.gov.uk/swagger/ui/index.html#!/Line/Line_Modes) |
| Route sequences (tracks; cached) | `GET` | [`/Line/victoria/Route/Sequence/inbound?serviceTypes=Regular`](https://api.tfl.gov.uk/Line/victoria/Route/Sequence/inbound?serviceTypes=Regular) | [Line → Route sequence](https://api.tfl.gov.uk/swagger/ui/index.html#!/Line/Line_RouteSequence) |
| Stop coordinates (cached) | `GET` | [`/StopPoint/Mode/tube`](https://api.tfl.gov.uk/StopPoint/Mode/tube) | [StopPoint → Mode](https://api.tfl.gov.uk/swagger/ui/index.html#!/StopPoint/StopPoint_Modes) |

The **live position estimate** comes from the **Arrivals** response fields `vehicleId`, `naptanId`, `stationName`, `timeToStation`, `direction`, and `towards` — there is no GPS coordinate for trains in this API.

## Run (from repo root)

Install map-only dependencies into the shared `.venv`:

```bash
uv pip install -r maps/tfl-live-map/requirements.txt
```

### TfL API keys (recommended)

The **429 Too Many Requests** error usually means you hit TfL’s anonymous rate limit (50 req/min). With a subscription you get **500 req/min** (“500 R” in the portal).

Per the current [TfL API Portal](https://api-portal.tfl.gov.uk/) home page (June 2026):

> When making an API request, please append the `app_key` as a query parameter to your requests. **Please ignore any references to passing the app_id as this is no longer required.**

So you only need your subscription **Primary key** — there is no separate Application ID to hunt for.

1. Sign in at [TfL API Portal](https://api-portal.tfl.gov.uk/).
2. **Products** → subscribe to the **500 requests per minute** plan (if you have not already).
3. **Profile** → **Subscriptions** → copy the **Primary key** (Show).

#### Provide the key safely (`.env`)

At the **repo root** (next to `README.md`):

```bash
cp .env.example .env
```

Edit `.env` (one line is enough):

```env
TFL_APP_KEY=paste-your-primary-key-here
```

`.env` is gitignored. Keys are loaded via `lib.env.load_repo_env()` (repo-wide helper).

Alternatively (PowerShell, current session only):

```powershell
$env:TFL_APP_KEY="paste-your-primary-key-here"
```

`TFL_APP_ID` is optional legacy support only; leave it unset unless you have an old two-part credential pair.

Start the dashboard (runs until you stop it with Ctrl+C):

```bash
python maps/tfl-live-map/main.py
```

Open the URL printed in the terminal (default `http://127.0.0.1:8051`).

## Notebook

`notebook.ipynb` is for exploration only. **Dash apps are best started from a terminal** (running `main()` inside Jupyter blocks the kernel).

## Dependencies

Uses the shared repo `.venv`. This template expects:

- `dash`, `dash-bootstrap-components`, `plotly`
- `openpyxl` if you read `.xlsx` files with pandas

`python-dotenv` is provided via root `lib/` when using `load_repo_env()`; add to `requirements.txt` only if extracting this map standalone.

## Data

This map calls the TfL API for **live arrivals** (refreshed every 30 seconds).

Static network metadata (tube stop points and line route sequences for drawing tracks) is **cached locally** under `data/`:

| File | Contents |
|------|----------|
| `data/tube_stop_points.json` | Station coordinates (`naptanId`, name, lat/lon) |
| `data/tube_line_routes.json` | All route **branches** per line/direction + line ids |

Stations appear on the map as grey circles; hover for the station name. Line routes include every branch (e.g. Northern line arms), not just the first sequence returned by the API.

On first run (or when cache is missing/stale), these files are fetched from the TfL API and saved. Subsequent startups read from disk — no API calls for static data.

If routes look incomplete after an update, force a refresh:

```env
TFL_REFRESH_CACHE=1
```

**Cache controls** (optional env vars):

```env
TFL_CACHE_MAX_AGE_DAYS=90   # refresh cache after N days (default 90)
TFL_REFRESH_CACHE=1         # force re-download on next run
```

## Code layout

Keep Python modules under **~500 lines** each. Suggested split:

| Module | Role |
|--------|------|
| `main.py` | Dash layout, callbacks, `main()` |
| `data_processing.py` | Load, clean, filter, optional category grouping |
| `viz.py` | Plotly figure builders |

Custom CSS lives in `assets/` (auto-loaded by Dash).

## Outputs

Dashboards usually have no static `output/` artifacts. Use `output/` for exported CSV/PNG if you add export features.

## Shared library

```python
from lib.paths import map_dir

MAP_DIR = map_dir("tfl-live-map")
```

## Standalone repo

1. Copy this entire folder.
2. Merge `requirements.txt` into a `pyproject.toml` (or install with pip).
3. Copy any `lib/` modules you import from.
4. Run `python main.py` from the copied folder.
