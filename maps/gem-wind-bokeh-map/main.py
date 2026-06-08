"""Build a static HTML snapshot of the GEM wind map (Bokeh) for GitHub Pages."""

from __future__ import annotations

import argparse
from html import escape
from pathlib import Path

from bokeh.embed import components
from bokeh.resources import CDN

from wind_bokeh import build_layout
from wind_bokeh_charts import assets_table_df
from wind_data import COL, load_data

MAP_DIR = Path(__file__).resolve().parent
DATA_PATH = MAP_DIR / "data" / "Global-Wind-Power-Tracker-February-2026.xlsx"
DEFAULT_OUTPUT = MAP_DIR / "output" / "gem_wind_bokeh_map.html"
TABLE_ROW_LIMIT = 100


def _status_legend_html(status_colors: dict[str, str]) -> str:
    chips = "".join(
        f'<span class="legend-chip">'
        f'<span class="legend-swatch" style="background:{escape(color)}"></span>'
        f"{escape(label)}</span>"
        for label, color in status_colors.items()
    )
    return f"""      <div class="status-legend" aria-label="Map marker colours by status">
{chips}
      </div>"""


def _kpi_cards(total_capacity: float, row_count: int, country_count: int) -> str:
    return f"""    <section class="kpi-row">
      <article class="kpi-card">
        <p class="kpi-value" id="kpi-capacity">{int(round(total_capacity)):,}</p>
        <p class="kpi-label">Total capacity (MW)</p>
      </article>
      <article class="kpi-card">
        <p class="kpi-value" id="kpi-rows">{row_count:,}</p>
        <p class="kpi-label">Wind farm rows</p>
      </article>
      <article class="kpi-card">
        <p class="kpi-value" id="kpi-countries">{country_count:,}</p>
        <p class="kpi-label">Countries / areas</p>
      </article>
    </section>"""


def _format_table_cell(col: str, val: object) -> str:
    if val is None or (isinstance(val, float) and val != val):
        return ""
    if col == "Capacity (MW)":
        return f"{int(round(float(val))):,}"
    if col in ("Latitude", "Longitude"):
        return f"{float(val):.4f}"
    return str(val)


def _assets_table_html(df) -> str:
    table_df = (
        assets_table_df(df)
        .sort_values("Capacity (MW)", ascending=False)
        .head(TABLE_ROW_LIMIT)
    )
    headers = "".join(f"<th>{escape(str(c))}</th>" for c in table_df.columns)
    rows: list[str] = []
    for _, row in table_df.iterrows():
        cells: list[str] = []
        for col, val in row.items():
            text = _format_table_cell(col, val)
            if col == "Wiki URL" and text.startswith("http"):
                cell = f'<a href="{escape(text)}">{escape(text)}</a>'
            else:
                cell = escape(text)
            cells.append(f"<td>{cell}</td>")
        rows.append(f"      <tr>{''.join(cells)}</tr>")
    body = "\n".join(rows)
    note = (
        f"Top {TABLE_ROW_LIMIT} rows by capacity (full dataset). "
        "Click a chart bar to cross-filter the map, charts, and table."
    )
    return f"""    <section class="table-section">
      <h2 class="section-title">Largest entries</h2>
      <p class="section-lead" id="table-note">{escape(note)}</p>
      <div class="table-wrap">
        <table>
          <thead><tr>{headers}</tr></thead>
          <tbody id="assets-tbody">
{body}
          </tbody>
        </table>
      </div>
    </section>"""


def build_static_html(output_path: Path | None = None) -> Path:
    """Write a self-contained static HTML page for the full GEM wind dataset."""
    out = output_path or DEFAULT_OUTPUT
    out.parent.mkdir(parents=True, exist_ok=True)

    df = load_data(DATA_PATH)
    total_capacity = float(df[COL.capacity_mw].sum())
    row_count = len(df)
    country_count = int(df[COL.country].nunique())

    layout, _master, _filter_state, status_colors = build_layout(df)
    script, div = components(layout)

    table_html = _assets_table_html(df)
    kpi_html = _kpi_cards(total_capacity, row_count, country_count)
    legend_html = _status_legend_html(status_colors)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>GEM wind farms — February 2026 (Bokeh)</title>
  <meta name="description" content="Global Energy Monitor wind farms — Bokeh bubble map sized by capacity, coloured by status."/>
  {CDN.render()}
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet"/>
  <style>
    :root {{
      --page-max: 1680px;
      --gutter: clamp(16px, 2vw, 28px);
      --bg: #0b1120;
      --card: rgba(30, 41, 59, 0.92);
      --border: #334155;
      --text: #e2e8f0;
      --muted: #94a3b8;
      --accent: #34d399;
    }}
    html, body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    }}
    .site-width {{
      max-width: var(--page-max);
      margin: 0 auto;
      padding: 28px var(--gutter) 56px;
      box-sizing: border-box;
    }}
    .hero {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(220px, 320px);
      gap: 20px 28px;
      align-items: end;
      margin-bottom: 24px;
    }}
    @media (max-width: 860px) {{
      .hero {{ grid-template-columns: 1fr; }}
    }}
    .eyebrow {{
      margin: 0 0 6px;
      color: var(--accent);
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: clamp(1.75rem, 3vw, 2.35rem);
      line-height: 1.15;
    }}
    .lead {{ margin: 0; color: var(--muted); max-width: 52ch; }}
    .source {{
      margin: 10px 0 0;
      color: var(--muted);
      font-size: 12px;
      max-width: 60ch;
    }}
    .source a {{ color: #a5f3fc; }}
    .tip {{
      margin: 0;
      padding: 12px 16px;
      border-radius: 12px;
      border: 1px solid rgba(52, 211, 153, 0.25);
      background: rgba(52, 211, 153, 0.1);
      color: #a7f3d0;
      font-size: 13px;
      line-height: 1.45;
    }}
    .kpi-row {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 14px;
      margin-bottom: 20px;
    }}
    @media (max-width: 720px) {{
      .kpi-row {{ grid-template-columns: 1fr; }}
    }}
    .kpi-card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 18px 20px;
    }}
    .kpi-value {{
      margin: 0;
      font-size: clamp(1.5rem, 2.5vw, 2rem);
      font-weight: 800;
      color: #f8fafc;
      font-variant-numeric: tabular-nums;
    }}
    .kpi-label {{
      margin: 6px 0 0;
      color: var(--muted);
      font-size: 13px;
    }}
    .viz-panel {{
      margin-bottom: 28px;
    }}
    .panel-head {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 12px 20px;
      margin-bottom: 12px;
    }}
    .panel-title {{
      margin: 0;
      font-size: 13px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: #cbd5e1;
    }}
    .status-legend {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px 14px;
      justify-content: flex-end;
    }}
    .legend-chip {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 12px;
      color: var(--muted);
      white-space: nowrap;
    }}
    .legend-swatch {{
      width: 10px;
      height: 10px;
      border-radius: 999px;
      flex-shrink: 0;
      box-shadow: 0 0 0 1px rgba(15, 23, 42, 0.8);
    }}
    .chart-card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 12px 10px 6px;
      overflow: hidden;
    }}
    .chart-card .bk-root {{
      margin-inline: auto;
      max-width: 100%;
    }}
    .section-title {{
      margin: 0 0 6px;
      font-size: 13px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: #cbd5e1;
    }}
    .section-lead {{ margin: 0 0 14px; color: var(--muted); font-size: 14px; }}
    .table-section {{
      margin-top: 8px;
    }}
    .table-wrap {{
      overflow: auto;
      max-height: min(70vh, 720px);
      border: 1px solid var(--border);
      border-radius: 14px;
      background: var(--card);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
    }}
    th, td {{
      padding: 10px 12px;
      border-bottom: 1px solid rgba(148, 163, 184, 0.12);
      text-align: left;
      vertical-align: top;
    }}
    th {{
      position: sticky;
      top: 0;
      z-index: 1;
      background: #0f172a;
      color: var(--muted);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      box-shadow: 0 1px 0 var(--border);
    }}
    tr:nth-child(even) td {{ background: rgba(148, 163, 184, 0.05); }}
    td a {{ color: #93c5fd; }}
    footer {{
      margin-top: 36px;
      padding-top: 18px;
      border-top: 1px solid var(--border);
      color: #64748b;
      font-size: 13px;
    }}
    .bk-root {{ color: var(--text); }}
  </style>
</head>
<body>
  <div class="site-width">
    <header class="hero">
      <div>
        <p class="eyebrow">Global Wind Power Tracker</p>
        <h1>Wind farms of the world</h1>
        <p class="lead">February 2026 snapshot · marker size = capacity · colour = status</p>
        <p class="source">
          Data source:
          <a href="https://globalenergymonitor.org/renewables-and-other-power">Global Energy Monitor — Renewables and other power</a>
          (accessed 2026-06-08).
        </p>
      </div>
      <p class="tip">Click a chart bar to cross-filter the map, charts, and table. Click again to clear.</p>
    </header>
{kpi_html}
    <section class="viz-panel">
      <div class="panel-head">
        <h2 class="panel-title">Map &amp; breakdowns</h2>
{legend_html}
      </div>
      <div class="chart-card">
{div}
      </div>
    </section>
{table_html}
    <footer>
      Global Energy Monitor, Global Wind Power Tracker, February 2026 release.
    </footer>
  </div>
{script}
</body>
</html>
"""
    out.write_text(html, encoding="utf-8")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Build static GEM wind map HTML (Bokeh).")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output HTML path (default: {DEFAULT_OUTPUT.name}).",
    )
    args = parser.parse_args()
    path = build_static_html(args.output)
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
