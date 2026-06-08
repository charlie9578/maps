"""Build a static HTML snapshot of the GEM wind map for GitHub Pages."""

from __future__ import annotations

import argparse
from html import escape
from pathlib import Path

import plotly.graph_objects as go
import plotly.io as pio

from wind_data import COL, load_data
from wind_viz import (
    assets_table_df,
    make_country_bar,
    make_installation_pie,
    make_map,
    make_owner_bar,
    make_status_bar,
    make_top_projects_bar,
)

MAP_DIR = Path(__file__).resolve().parent
DATA_PATH = MAP_DIR / "data" / "Global-Wind-Power-Tracker-February-2026.xlsx"
DEFAULT_OUTPUT = MAP_DIR / "output" / "gem_wind_map.html"
PLOTLY_CONFIG = {"displayModeBar": True, "scrollZoom": True, "responsive": True}
TABLE_ROW_LIMIT = 100


def _plotly_cdn_script() -> str:
    snippet = pio.to_html(go.Figure(), include_plotlyjs="cdn", full_html=False)
    start = snippet.find("<script")
    end = snippet.find("</script>") + len("</script>")
    if start < 0 or end <= start:
        msg = "Could not extract Plotly CDN script tag"
        raise RuntimeError(msg)
    return snippet[start:end]


def _figure_div(fig: go.Figure) -> str:
    return fig.to_html(
        full_html=False,
        include_plotlyjs=False,
        config=PLOTLY_CONFIG,
    )


def _kpi_cards(total_capacity: float, row_count: int, country_count: int) -> str:
    return f"""    <section class="kpi-row">
      <article class="kpi-card">
        <p class="kpi-value">{total_capacity:,.0f}</p>
        <p class="kpi-label">Total capacity (MW)</p>
      </article>
      <article class="kpi-card">
        <p class="kpi-value">{row_count:,}</p>
        <p class="kpi-label">Wind farm rows</p>
      </article>
      <article class="kpi-card">
        <p class="kpi-value">{country_count:,}</p>
        <p class="kpi-label">Countries / areas</p>
      </article>
    </section>"""


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
            text = "" if val is None or (isinstance(val, float) and val != val) else str(val)
            if col == "Wiki URL" and text.startswith("http"):
                cell = f'<a href="{escape(text)}">{escape(text)}</a>'
            else:
                cell = escape(text)
            cells.append(f"<td>{cell}</td>")
        rows.append(f"      <tr>{''.join(cells)}</tr>")
    body = "\n".join(rows)
    note = (
        f"Top {TABLE_ROW_LIMIT} rows by capacity (full dataset). "
        "Run the Dash dashboard locally for filters and CSV export."
    )
    return f"""    <section class="table-section">
      <h2 class="section-title">Largest entries</h2>
      <p class="section-lead">{escape(note)}</p>
      <div class="table-wrap">
        <table>
          <thead><tr>{headers}</tr></thead>
          <tbody>
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

    map_div = _figure_div(make_map(df))
    pie_div = _figure_div(make_installation_pie(df))
    status_div = _figure_div(make_status_bar(df))
    country_div = _figure_div(make_country_bar(df))
    projects_div = _figure_div(make_top_projects_bar(df))
    owner_div = _figure_div(make_owner_bar(df))
    table_html = _assets_table_html(df)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>GEM wind farms — February 2026</title>
  <meta name="description" content="Global Energy Monitor wind farms — bubble map sized by capacity, coloured by status."/>
  {_plotly_cdn_script()}
  <style>
    :root {{
      --page-max: 1400px;
      --gutter: 16px;
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
      padding: 24px var(--gutter) 48px;
      box-sizing: border-box;
    }}
    .hero {{
      margin-bottom: 20px;
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
      font-size: clamp(1.6rem, 3vw, 2.2rem);
    }}
    .lead {{ margin: 0; color: var(--muted); }}
    .source {{
      margin: 8px 0 0;
      color: var(--muted);
      font-size: 12px;
    }}
    .source a {{ color: #a5f3fc; }}
    .kpi-row {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }}
    .kpi-card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 16px 18px;
    }}
    .kpi-value {{
      margin: 0;
      font-size: 28px;
      font-weight: 800;
      color: #f8fafc;
    }}
    .kpi-label {{
      margin: 4px 0 0;
      color: var(--muted);
      font-size: 13px;
    }}
    .chart-card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 8px;
      margin-bottom: 16px;
      overflow: hidden;
    }}
    .chart-row {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 16px;
      margin-bottom: 16px;
    }}
    .chart-row .chart-card {{ margin-bottom: 0; }}
    .chart-card .plotly-graph-div {{ margin: 0 auto; width: 100% !important; }}
    .section-title {{
      margin: 28px 0 6px;
      font-size: 15px;
      font-weight: 600;
      color: #cbd5e1;
      text-transform: uppercase;
      letter-spacing: 0.02em;
    }}
    .section-lead {{ margin: 0 0 12px; color: var(--muted); font-size: 14px; }}
    .table-wrap {{
      overflow-x: auto;
      border: 1px solid var(--border);
      border-radius: 12px;
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
      background: rgba(15, 23, 42, 0.6);
      color: var(--muted);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }}
    tr:nth-child(even) td {{ background: rgba(148, 163, 184, 0.05); }}
    td a {{ color: #93c5fd; }}
    footer {{
      margin-top: 32px;
      padding-top: 16px;
      border-top: 1px solid var(--border);
      color: #64748b;
      font-size: 13px;
    }}
  </style>
</head>
<body>
  <div class="site-width">
    <header class="hero">
      <p class="eyebrow">Global Wind Power Tracker</p>
      <h1>Wind farms of the world</h1>
      <p class="lead">February 2026 snapshot · marker size = capacity · colour = status</p>
      <p class="source">
        Data source:
        <a href="https://globalenergymonitor.org/renewables-and-other-power">Global Energy Monitor — Renewables and other power</a>
        (accessed 2026-06-02). Static snapshot — run
        <code>python maps/gem-wind-map/main.py</code> locally for filters and CSV export.
      </p>
    </header>
{_kpi_cards(total_capacity, row_count, country_count)}
    <section class="chart-card chart-map">
{map_div}
    </section>
    <div class="chart-row">
      <section class="chart-card">{pie_div}</section>
      <section class="chart-card">{status_div}</section>
      <section class="chart-card">{country_div}</section>
      <section class="chart-card">{projects_div}</section>
    </div>
    <section class="chart-card">
{owner_div}
    </section>
{table_html}
    <footer>
      Global Energy Monitor, Global Wind Power Tracker, February 2026 release.
    </footer>
  </div>
</body>
</html>
"""
    out.write_text(html, encoding="utf-8")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Build static GEM wind map HTML.")
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
