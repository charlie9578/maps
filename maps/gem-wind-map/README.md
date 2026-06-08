# gem-wind-map

Interactive dashboard of Global Energy Monitor (GEM) wind farms from the **Global Wind Power Tracker (February 2026)** release.

Features:
- Bubble map of wind farms (**size = capacity**, **color = status**)
- Filters (country, status, installation type, capacity, start year)
- “Largest wind farms” table (aggregated by project)
- Capacity breakdowns by installation type and country

## Run (from repo root)

Install map-only dependencies into the shared `.venv`:

```bash
uv pip install -r maps/gem-wind-map/requirements.txt
# or: .venv\Scripts\python.exe -m pip install -r maps/gem-wind-map/requirements.txt
```

**Interactive Dash dashboard** (filters, cross-filtering, CSV export):

```bash
python maps/gem-wind-map/main.py
```

It will print a local URL (default `http://127.0.0.1:8050`).

**Static HTML** (for GitHub Pages or sharing):

```bash
python maps/gem-wind-map/static_site.py
# or: python maps/gem-wind-map/main.py --static
```

Writes `output/gem_wind_map.html`. Published at
[charlie9578.github.io/maps/gem-wind/](https://charlie9578.github.io/maps/gem-wind/).

## Data

Input file (provided locally):
- `data/Global-Wind-Power-Tracker-February-2026.xlsx`

Source / citation:
- Global Energy Monitor, Global Wind Power Tracker, February 2026 release (see the `About` sheet in the workbook for the recommended citation and license details).

## Outputs

This map is a live dashboard (no static output files by default). Generated files (if any) should go under `output/` (gitignored).
