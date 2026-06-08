# gem-wind-bokeh-map

Static interactive HTML dashboard of Global Energy Monitor (GEM) wind farms from the **Global Wind Power Tracker (February 2026)** release — built with **Bokeh** (tile map + breakdown charts + client-side cross-filtering).

Features:
- Bubble map of wind farms (**size = capacity**, **color = status**) on Carto dark tiles
- Capacity breakdowns by installation type, status, country, project, and owner
- **Cross-filtering:** click a chart bar to filter the map, charts, KPIs, and table (click again to clear)

## Run (from repo root)

Install map-only dependencies into the shared `.venv`:

```bash
uv pip install -r maps/gem-wind-bokeh-map/requirements.txt
# or: .venv\Scripts\python.exe -m pip install -r maps/gem-wind-bokeh-map/requirements.txt
```

**Build static HTML:**

```bash
python maps/gem-wind-bokeh-map/main.py
# optional: -o path/to/output.html
```

Writes `output/gem_wind_bokeh_map.html`. Published at
[charlie9578.github.io/maps/gem-wind-bokeh/](https://charlie9578.github.io/maps/gem-wind-bokeh/).

For a full filter sidebar and CSV export, use the Plotly/Dash sibling map:
`python maps/gem-wind-map/main.py`.

## Data

Input file (provided locally):
- `data/Global-Wind-Power-Tracker-February-2026.xlsx`

Source / citation:
- Global Energy Monitor, Global Wind Power Tracker, February 2026 release (see the `About` sheet in the workbook for the recommended citation and license details). Accessed 2026-06-08.

## Outputs

Generated files go under `output/` (gitignored).
