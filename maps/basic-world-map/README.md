# basic-world-map

A simple political world map (land, ocean, coastlines, country borders) using
[Cartopy](https://scitools.org.uk/cartopy/docs/latest/) and Natural Earth data
bundled with Cartopy.

## Run (from repo root)

```bash
uv pip install -r maps/basic-world-map/requirements.txt
python maps/basic-world-map/main.py
```

Output: `maps/basic-world-map/output/world_map.png`

Or open `maps/basic-world-map/notebook.ipynb` in Jupyter (start `jupyter lab` from the repo root).

## Dependencies

Uses the shared repo `.venv`. This map adds **cartopy** (see `requirements.txt`).

## Data

No local data files — coastlines and borders come from Cartopy’s Natural Earth cache
(downloaded on first run).

## Outputs

Generated files go to `output/` (gitignored by default).

## Standalone repo

1. Copy this entire folder.
2. Add `matplotlib` and `cartopy` to your environment (`requirements.txt` or `pyproject.toml`).
3. Run `python main.py` from the map folder (paths in `main.py` are relative to the script).
