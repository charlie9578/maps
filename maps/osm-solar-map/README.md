# osm-solar-map

Interactive map of **Malta solar plants** tagged in [OpenStreetMap](https://www.openstreetmap.org/), fetched via the [Overpass API](https://wiki.openstreetmap.org/wiki/Overpass_API).

Single-tag query within a Malta + Gozo bounding box:

- `plant:source=solar`

## Run (from repo root)

```bash
uv pip install -r maps/osm-solar-map/requirements.txt
python maps/osm-solar-map/main.py
```

Re-download from Overpass (ignore cache):

```bash
python maps/osm-solar-map/main.py --refresh
```

Or open `maps/osm-solar-map/notebook.ipynb` in Jupyter (kernel **Maps (.venv)**).

## Dependencies

- `requests` — Overpass HTTP client
- `folium` — interactive HTML map (OpenStreetMap tiles)

## Data

- **Source:** [Overpass API](https://overpass-api.de/api/interpreter) (query in `main.py`).
- **Cache:** `data/osm-solar-malta.geojson` (written on first run; use `--refresh` to update).
- **License:** © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors ([ODbL](https://opendatacommons.org/licenses/odbl/)).

Be polite to public Overpass instances: cache locally and avoid hammering `--refresh`.

## Outputs

- `output/osm_solar_malta.html` — clustered markers with popups (name, operator, capacity when tagged).

Note: the basemap uses `CartoDB Positron` tiles to avoid OSM tile-server 403 blocks in embedded HTML.

## Shared library

Not used; paths are local to this folder via `Path(__file__)`.

## Standalone repo

1. Copy this folder.
2. Install `requirements.txt` into your environment.
3. Run `python main.py` from the map folder (or adjust paths).
