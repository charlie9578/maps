# Map catalog

Short index of maps in this repo. Each folder under `maps/<name>/` is self-contained; see that map’s `README.md` for full run instructions.

| Map | Type | Summary |
|-----|------|---------|
| [basic-world-map](maps/basic-world-map/) | Static PNG | Political world map (land, ocean, coastlines, borders) via Cartopy / Natural Earth. |
| [interactive-owid-map](maps/interactive-owid-map/) | Interactive HTML | Choropleth of territorial CO₂ **per capita** from [Our World in Data](https://ourworldindata.org/explorers/co2); year slider, hover tooltips, forward-filled gaps marked **(est.)**. |
| [gem-wind-map](maps/gem-wind-map/) | Interactive dashboard | GEM Global Wind Power Tracker (Feb 2026): bubble map (**size=capacity**, **color=status**) + filters + largest projects + capacity breakdowns. |
| [osm-solar-map](maps/osm-solar-map/) | Interactive HTML | Malta solar **plants** from [OpenStreetMap](https://www.openstreetmap.org/) via Overpass (`plant:source=solar`); clustered Folium map. |

**Scaffold only (not maps):** [`maps/_template/`](maps/_template/) (default) · [`maps/_template_dash/`](maps/_template_dash/) (Dash dashboard) — `python scripts/new_map.py <name>` or `--type dash`.

## Quick run

From the repo root, after setting up the shared `.venv` (see [README.md](README.md)):

```bash
python maps/basic-world-map/main.py
uv pip install -r maps/interactive-owid-map/requirements.txt   # or pip equivalent
python maps/interactive-owid-map/main.py
uv pip install -r maps/osm-solar-map/requirements.txt
python maps/osm-solar-map/main.py
```

Outputs: `maps/<name>/output/` (gitignored).

## Adding a map

```bash
python scripts/new_map.py my-map-name
python scripts/new_map.py my-dashboard --type dash
```

Then add a row to the table above and document it in `maps/my-map-name/README.md`.
