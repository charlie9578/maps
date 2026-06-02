# MAP_NAME

Brief description of what this map shows and its data sources.

## Run (from repo root)

```bash
python maps/MAP_NAME/main.py
```

Or open `maps/MAP_NAME/notebook.ipynb` in Jupyter (start `jupyter lab` from the repo root; kernel **Maps (.venv)**).

## Dependencies

Uses the shared repo `.venv`. Map-only packages go in this folder’s `requirements.txt` and install into that same venv:

```bash
uv pip install -r maps/MAP_NAME/requirements.txt
# or: .venv\Scripts\python.exe -m pip install -r maps/MAP_NAME/requirements.txt
```

Example map-only packages: `geopandas`, `folium`, `plotly`.

## Data

- Place inputs in `data/`.
- **CSV files in `data/` are gitignored** — if data is downloaded, document the URL, license, and cached filename in this README; scripts should fetch on first run (see `main.py --refresh` if you add it).
- Small non-CSV fixtures (GeoJSON, etc.) may be committed when reasonable.

## Outputs

Generated files go to `output/` (gitignored). Static maps often use PNG/PDF; interactive maps often write HTML.

For an **interactive Dash dashboard**, scaffold with `python scripts/new_map.py MAP_NAME --type dash` instead of this template.

## Shared library

If you use repo-wide helpers:

```python
from lib.paths import map_dir

MAP_DIR = map_dir("MAP_NAME")
```

## Standalone repo

1. Copy this entire folder.
2. Merge `requirements.txt` into a `pyproject.toml` (or install with pip).
3. Copy any `lib/` modules you import from.
4. Run `python main.py` or the notebook; adjust paths if not using `lib.paths`.
