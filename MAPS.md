# Map catalog

Short index of maps in this repo. Each folder under `maps/<name>/` is self-contained; see that map’s `README.md` for full run instructions.

**Published demos:** [charlie9578.github.io/maps](https://charlie9578.github.io/maps/) — World Cup · CO₂ · Malta solar · citations · world map

| Map | On Pages? | Type | Summary |
|-----|-----------|------|---------|
| [basic-world-map](maps/basic-world-map/) | [world-map](https://charlie9578.github.io/maps/world-map/) | Static PNG | Political world map (land, ocean, coastlines, borders) via Cartopy / Natural Earth. |
| [interactive-owid-map](maps/interactive-owid-map/) | [co2-per-capita](https://charlie9578.github.io/maps/co2-per-capita/) | Interactive HTML | Choropleth of territorial CO₂ **per capita** from [Our World in Data](https://ourworldindata.org/explorers/co2); year slider, hover tooltips, forward-filled gaps marked **(est.)**. |
| [gem-wind-map](maps/gem-wind-map/) | [gem-wind](https://charlie9578.github.io/maps/gem-wind/) | Interactive HTML | GEM Global Wind Power Tracker (Feb 2026): bubble map (**size=capacity**, **color=status**) + breakdown charts. Static site; run Dash locally for filters. |
| [gem-wind-bokeh-map](maps/gem-wind-bokeh-map/) | [gem-wind-bokeh](https://charlie9578.github.io/maps/gem-wind-bokeh/) | Interactive HTML (Bokeh) | Same GEM wind dataset — Bokeh tile map + breakdown charts with **click-to cross-filter** (CustomJS). |
| [osm-solar-map](maps/osm-solar-map/) | [osm-solar-malta](https://charlie9578.github.io/maps/osm-solar-malta/) | Interactive HTML | Malta solar **plants** from [OpenStreetMap](https://www.openstreetmap.org/) via Overpass (`plant:source=solar`); clustered Folium map. |
| [tfl-live-map](maps/tfl-live-map/) | — | Interactive dashboard | Live (station-based) locations of London Underground trains from the TfL Unified API arrivals feed. |
| [world-cup-teams-map](maps/world-cup-teams-map/) | [world-cup-2026](https://charlie9578.github.io/maps/world-cup-2026/) | Interactive HTML | 2026 World Cup teams at their capitals; click a capital to trace curved "flight paths" to club stadiums where its players play. Companion **squad dashboard** (clubs, Sankey, ages). Curated dataset (Plotly + click JS). |
| [glasgow-2026](maps/glasgow-2026/) | — | Interactive dashboard | All 74 Glasgow 2026 Commonwealth Games teams connected to the host city; route width shows medal volume and exact gold/silver/bronze proportions form the stripes, with neutral paths for no-medal teams. |
| [academic-citations-map](maps/academic-citations-map/) | [citation-network](https://charlie9578.github.io/maps/citation-network/) | Interactive HTML | Citation network around a paper from [OpenAlex](https://openalex.org/): search or work id, expandable depth (refs + citing works), Plotly graph. |

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
