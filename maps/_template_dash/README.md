# MAP_NAME

Interactive **Dash** dashboard (filters + charts). Brief description of what this map shows and its data sources.

## Run (from repo root)

Install map-only dependencies into the shared `.venv`:

```bash
uv pip install -r maps/MAP_NAME/requirements.txt
```

Start the dashboard (runs until you stop it with Ctrl+C):

```bash
python maps/MAP_NAME/main.py
```

Open the URL printed in the terminal (default `http://127.0.0.1:8050`).

## Notebook

`notebook.ipynb` is for exploration only. **Dash apps are best started from a terminal** (running `main()` inside Jupyter blocks the kernel).

## Dependencies

Uses the shared repo `.venv`. This template expects:

- `dash`, `dash-bootstrap-components`, `plotly`
- `openpyxl` if you read `.xlsx` files with pandas

## Data

- Place inputs in `data/`.
- **CSV files in `data/` are gitignored** — document URL, license, and filename in this README if downloaded.
- For Excel: add `openpyxl` to `requirements.txt` and document the sheet name in `data_processing.py`.

## Code layout

Keep Python modules under **~500 lines** each. Suggested split:

| Module | Role |
|--------|------|
| `main.py` | Dash layout, callbacks, `main()` |
| `data_processing.py` | Load, clean, filter, optional category grouping |
| `viz.py` | Plotly figure builders |

Custom CSS lives in `assets/` (auto-loaded by Dash).

## Outputs

Dashboards usually have no static `output/` artifacts. Use `output/` for exported CSV/PNG if you add export features.

## Shared library

```python
from lib.paths import map_dir

MAP_DIR = map_dir("MAP_NAME")
```

## Standalone repo

1. Copy this entire folder.
2. Merge `requirements.txt` into a `pyproject.toml` (or install with pip).
3. Copy any `lib/` modules you import from.
4. Run `python main.py` from the copied folder.
