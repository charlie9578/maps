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

Static HTML maps can be published from this repo to GitHub Pages. The workflow
builds a `site/` tree and deploys it on every push to `main`.

**Live site:** [charlie9578.github.io/maps](https://charlie9578.github.io/maps/) (after Pages is enabled — see below)

| Path | Content |
|------|---------|
| `/` | Landing page listing published maps |
| `/world-cup-2026/` | 2026 World Cup squad dashboard |

### One-time setup

1. Repo **Settings → Pages → Build and deployment → Source:** GitHub Actions.
2. Push to `main` (or run the **Deploy GitHub Pages** workflow manually).

### Local preview

```bash
python scripts/build_pages_site.py --site-url https://charlie9578.github.io/maps
# open site/index.html in a browser (or serve site/ with any static server)
```

### Adding a map to the site

1. Ensure the map writes self-contained HTML (Plotly/Folium via CDN is fine).
2. Add a build step in `scripts/build_pages_site.py` (`PUBLISHED_MAPS` + publish function).
3. Push to `main` — CI rebuilds and deploys.

Dash dashboards (live server + API) are not suited to static Pages; host those elsewhere or export snapshots.
