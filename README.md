# Maps

Geographic and data-visualization map projects sharing one Python virtual environment at the repository root.

Each map lives under `maps/<name>/` with its own README, scripts, notebook, data, and outputs. A map folder should contain everything needed to run that map; you can copy a single map folder into a new repository and follow its README to bootstrap a standalone project.

**Map index:** see **[MAPS.md](MAPS.md)** for a short catalog of maps in this repo.

Shared Python code lives in **`lib/`** (installable as `from lib...`). Maps must not import from sibling map folders.

## Repository layout

```
lib/                    # Shared helpers (import: from lib.paths import map_dir)
maps/
├── _template/          # Scaffold for script/static maps (not published)
├── _template_dash/     # Scaffold for Dash dashboards (not published)
└── <map-name>/
    ├── README.md
    ├── main.py         # Script entry point
    ├── notebook.ipynb  # Notebook entry point (optional)
    ├── requirements.txt   # Map-only packages → installed into root .venv
    ├── data/           # inputs; *.csv gitignored (re-download via main.py)
    └── output/         # generated artifacts (gitignored)
scripts/
├── new_map.py
└── install_map_requirements.py
```

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or `pip` + `venv`

## Shared environment (repo root)

One `.venv` for the whole repo. Map-specific packages still install here—not into per-map environments.

```bash
# uv (recommended)
uv venv
uv sync --extra dev
uv pip install -e .

# or pip
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -e ".[dev]"
```

Register the kernel for notebooks (once per venv):

```bash
python -m ipykernel install --user --name maps --display-name "Maps (.venv)"
```

### Map-specific dependencies

List packages only that map needs in `maps/<map-name>/requirements.txt`, then install into the **root** venv:

```bash
uv pip install -r maps/<map-name>/requirements.txt
# or install every map's requirements:
python scripts/install_map_requirements.py
```

## Create a new map

```bash
python scripts/new_map.py my-map-name
python scripts/new_map.py my-dashboard --type dash   # interactive Dash app
```

Then edit `maps/my-map-name/README.md`, `main.py`, and/or `notebook.ipynb`. If the map has `requirements.txt`, install it before running (kernel **Maps (.venv)** for notebooks).

**Dash maps:** run `python maps/<name>/main.py` from the terminal (Ctrl+C to stop). Keep Python files under ~500 lines; split into `data_processing.py`, `viz.py`, and `main.py` as needed.

## Run a map

From the **repository root** (keeps `lib` imports and paths consistent):

```bash
python maps/<map-name>/main.py
jupyter lab
# open maps/<map-name>/notebook.ipynb
```

## Shared library (`lib/`)

Put reusable functions here when more than one map needs them:

```python
from lib.paths import map_dir, repo_root
from lib.env import load_repo_env  # before reading API keys from os.environ
```

Keep `lib/` small and stable; map-specific logic stays in the map folder.

## API keys (`.env`)

Maps that call external APIs should read secrets from a **repo-root** `.env` file (gitignored):

```bash
cp .env.example .env
# edit .env with your keys
```

Document required variable names in each map’s README and add placeholders to `.env.example` when adding a new provider. See `.cursor/rules/maps-project.mdc` for conventions.

## Adding dependencies

| Scope | Where | Install |
|--------|--------|---------|
| Most maps / tooling | `pyproject.toml` `dependencies` or `dev` | `uv sync --extra dev` |
| One map only | `maps/<name>/requirements.txt` | `uv pip install -r maps/<name>/requirements.txt` |

## Extracting one map to its own repo

1. Copy `maps/<map-name>/` to a new repository.
2. Copy root `pyproject.toml` baseline plus that map’s `requirements.txt` (merge into one `pyproject.toml` or install both).
3. Copy any `lib/` modules the map imports, or inline/vend them.
4. Create a venv and run as documented in the map README.

Maps must not import from other map folders.

## Publishing (GitHub Pages)

Static HTML maps are published from this repo via a **GitHub Actions** workflow (not
“deploy from a branch”). The workflow runs `scripts/build_pages_site.py`, which builds
the dashboard and writes a `site/` folder in CI — that folder is **gitignored** locally
and never committed to `main`.

**Live site (after setup):** [charlie9578.github.io/maps](https://charlie9578.github.io/maps/)

| Path | Content |
|------|---------|
| `/` | Landing page listing published maps |
| `/world-cup-2026/` | 2026 World Cup squad dashboard |
| `/co2-per-capita/` | OWID CO₂ per capita choropleth (year slider) |
| `/osm-solar-malta/` | Malta solar plants (OpenStreetMap / Folium) |
| `/citation-network/` | OpenAlex citation network demo |
| `/gem-wind/` | GEM wind farms static snapshot (map + breakdown charts) |
| `/glasgow-2026/` | Glasgow 2026 Commonwealth Games medal tartan |
| `/world-map/` | Cartopy political world map (PNG) |

**Not on Pages:** `tfl-live-map` is a live Dash app (needs a running server and TfL API key).

### Why “Deploy from a branch” does not work

If **Settings → Pages → Build and deployment → Source** is set to **Branch** (e.g.
“built from the `main` branch”), GitHub serves files **directly from your repo**. This
repo’s `main` branch has Python source and map data, not the built HTML — and `site/` is
gitignored. You would get a blank page, a directory listing, or unrelated files — not the
dashboard.

You need **Source: GitHub Actions** so the **Deploy GitHub Pages** workflow can build
the site and upload it.

### Step-by-step setup

#### 1. Push the workflow to GitHub

Commit and push everything on `main`, including:

- `.github/workflows/deploy-pages.yml`
- `scripts/build_pages_site.py`
- `maps/world-cup-teams-map/assets/share-map.png`

#### 2. Switch Pages source to GitHub Actions

1. Open the **maps** repo on GitHub (not charlie9578.github.io).
2. **Settings** → **Pages** (left sidebar).
3. Under **Build and deployment**, find **Source**.
4. Change the dropdown from **Deploy from a branch** to **GitHub Actions**.

You should no longer see “Branch: main” as the publisher. Instead GitHub will list
workflows that can deploy Pages (including **Deploy GitHub Pages**).

Ignore “Learn how to add a Jekyll theme” — this site is plain static HTML, not Jekyll.

#### 3. Run the deploy workflow

Either:

- **Automatic:** push any commit to `main` (the workflow runs on every push), or
- **Manual:** **Actions** tab → **Deploy GitHub Pages** → **Run workflow** → **Run workflow**

#### 4. Approve the environment (first time only)

The first deploy may pause for approval:

1. **Actions** → click the running **Deploy GitHub Pages** workflow.
2. If you see **Waiting for review** on the **deploy** job, click it and **Review deployments** → **Approve**.

#### 5. Confirm it worked

1. **Actions** → latest **Deploy GitHub Pages** run → both **build** and **deploy** jobs should be green.
2. **Settings → Pages** should show: “Your site is live at **https://charlie9578.github.io/maps/**”
   (exact URL depends on repo name — see below).
3. Open:
   - https://charlie9578.github.io/maps/
   - https://charlie9578.github.io/maps/world-cup-2026/

Deploy can take 1–3 minutes after the workflow finishes.

### URL depends on repo name

For a **project** repo named `maps` under user `charlie9578`:

`https://charlie9578.github.io/maps/`

If your repo has a different name, replace `maps` in the path. The workflow sets this
automatically from `github.repository`.

Your personal site ([charlie9578.github.io](https://charlie9578.github.io/)) is a **separate**
repo — add a link there pointing to `https://charlie9578.github.io/maps/world-cup-2026/`.

### Local preview (before pushing)

```bash
python scripts/build_pages_site.py --site-url https://charlie9578.github.io/maps
# open site/index.html in a browser
```

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Pages still says “built from `main` branch” | Change **Source** to **GitHub Actions** (step 2). |
| Workflow not listed under Actions | Push `.github/workflows/deploy-pages.yml` to `main`. |
| **build** job fails | Open the job log — usually a missing Python dependency; check `requirements.txt`. |
| **deploy** job fails / 404 | Ensure Pages source is **GitHub Actions**, not Branch. Re-run workflow. |
| Old README shows instead of maps | You were on Branch mode; switch to Actions and redeploy. |
| Link preview image missing | `share-map.png` must deploy alongside `index.html` (workflow handles this). |

### Adding more maps later

1. Ensure the map writes self-contained HTML (Plotly/Folium via CDN is fine).
2. Add an entry to `PUBLISHED_MAPS` and a publish function in `scripts/build_pages_site.py`.
3. Push to `main`.

Dash dashboards (live server + API) are not suited to static Pages; host those elsewhere or export snapshots.
