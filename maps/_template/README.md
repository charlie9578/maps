# MAP_NAME

Brief description of what this map shows and its data sources.

## Run (from repo root)

```bash
python maps/MAP_NAME/main.py
```

Or open `maps/MAP_NAME/notebook.ipynb` in Jupyter (start `jupyter lab` from the repo root).

## Dependencies

Uses the shared repo `.venv`. Map-only packages go in this folder’s `requirements.txt` and install into that same venv:

```bash
uv pip install -r maps/MAP_NAME/requirements.txt
```

Example map-only packages: `geopandas`, `folium`, `contextily`.

## Data

- Place inputs in `data/`.
- Document any files that must be downloaded separately (URL, license, expected filename).

## Outputs

Generated files go to `output/` (gitignored by default).

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
