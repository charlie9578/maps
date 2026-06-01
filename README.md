# Maps

Geographic and data-visualization map projects sharing one Python virtual environment at the repository root.

Each map lives under `maps/<name>/` with its own README, scripts, notebook, data, and outputs. A map folder should contain everything needed to run that map; you can copy a single map folder into a new repository and follow its README to bootstrap a standalone project.

Shared Python code lives in **`lib/`** (installable as `from lib...`). Maps must not import from sibling map folders.

## Repository layout

```
lib/                    # Shared helpers (import: from lib.paths import map_dir)
maps/
├── _template/          # Scaffold for new maps (not a published map)
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
```

Then edit `maps/my-map-name/README.md`, `main.py`, and/or `notebook.ipynb`. If the map has `requirements.txt`, install it before running the notebook (kernel **Maps (.venv)**).

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
```

Keep `lib/` small and stable; map-specific logic stays in the map folder.

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
