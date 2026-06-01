# interactive-owid-map

Interactive choropleth of **territorial CO₂ emissions per capita** by country, styled after the [Our World in Data CO₂ explorer](https://ourworldindata.org/explorers/co2) map view.

- **Year slider** (earliest → latest, with play/pause)
- **Hover** shows country, year, and per-capita emissions; values filled from the prior year are tagged **(est.)**
- **Color scale** fixed across years (98th-percentile cap) so changes over time are comparable

Data: [CO₂ Data Explorer](https://ourworldindata.org/explorers/co2) export — territorial, all fossil emissions, per capita (tonnes CO₂ per person per year). CC BY; cite OWID when publishing.

## Run (from repo root)

```bash
uv pip install -r maps/interactive-owid-map/requirements.txt
python maps/interactive-owid-map/main.py
```

Open `maps/interactive-owid-map/output/co2_per_capita_map.html` in a browser.

Re-download the source CSV:

```bash
python maps/interactive-owid-map/main.py --refresh
```

## Dependencies

Uses the shared repo `.venv`. Map-only: **plotly** (see `requirements.txt`).

```bash
.venv\Scripts\python.exe -m pip install -r maps/interactive-owid-map/requirements.txt
```

In Jupyter, select kernel **Maps (.venv)** so the notebook uses that environment (not system Python).

## Data

On first run, `main.py` downloads the explorer CSV into `data/co2-per-capita-territorial.csv`. Only rows with an ISO country code are mapped. Missing years after a country’s first observation are **forward-filled** from the previous year (shown as **(est.)** in the hover).

## Outputs

- `output/co2_per_capita_map.html` — standalone interactive map (Plotly CDN)

## Notebook

`notebook.ipynb` rebuilds the map from the repo root so `lib.paths` works.

## Standalone repo

1. Copy this folder.
2. Install `pandas`, `plotly`, and map `requirements.txt` into your environment.
3. Run `python main.py` from the map folder (paths use `Path(__file__).parent`).
