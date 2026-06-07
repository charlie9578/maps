"""Assemble and write the World Cup squad statistics dashboard HTML."""

from __future__ import annotations

from pathlib import Path

import plotly.graph_objects as go

from dashboard_viz import DASH_BG, build_dashboard, build_extra_figures
from data_processing import build_teams, load_clubs, load_squads

MAP_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = MAP_DIR / "output"
DEFAULT_OUTPUT = OUTPUT_DIR / "world_cup_dashboard.html"


def _figure_to_div(fig: go.Figure, *, include_plotlyjs: bool | str = False) -> str:
    return fig.to_html(
        full_html=False,
        include_plotlyjs=include_plotlyjs,
        config={"displayModeBar": True, "responsive": True},
    )


def write_dashboard(output_path: Path) -> Path:
    """Build a multi-section Plotly dashboard and write standalone HTML."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    squads = load_squads()
    clubs = load_clubs()
    tournament, teams = build_teams(strict=False)
    accessed = squads.get("source_accessed", "2026-06-05")

    main_fig = build_dashboard(tournament, teams, clubs, source_accessed=accessed)
    extras = build_extra_figures(tournament, teams, clubs)

    sections = [_figure_to_div(main_fig, include_plotlyjs="cdn")]
    for _title, fig in extras:
        sections.append(_figure_to_div(fig, include_plotlyjs=False))

    body = "\n".join(f'<section class="chart-block">{html}</section>' for html in sections)
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{tournament} — squad dashboard</title>
  <style>
    html, body {{
      margin: 0;
      background: {DASH_BG};
      color: #e2e8f0;
      font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    }}
    .top-nav {{
      position: sticky;
      top: 0;
      z-index: 1000;
      display: flex;
      gap: 12px;
      align-items: center;
      padding: 10px 16px;
      background: rgba(15, 23, 42, 0.92);
      border-bottom: 1px solid #334155;
      backdrop-filter: blur(6px);
    }}
    .top-nav a {{
      color: #93c5fd;
      text-decoration: none;
      font-size: 14px;
    }}
    .top-nav a:hover {{ text-decoration: underline; }}
    .top-nav span {{ color: #94a3b8; font-size: 14px; }}
    .chart-block {{ margin: 0 auto 8px; max-width: 1400px; }}
    .chart-block .plotly-graph-div {{ margin: 0 auto; }}
  </style>
</head>
<body>
  <nav class="top-nav">
    <span>{tournament} squad dashboard</span>
    <a href="world_cup_teams_map.html">Flight-path map</a>
  </nav>
  {body}
</body>
</html>
"""
    output_path.write_text(page, encoding="utf-8")
    return output_path


def main() -> None:
    path = write_dashboard(DEFAULT_OUTPUT)
    squads = load_squads()
    tournament = squads.get("tournament", "World Cup")
    n_teams = len(squads.get("teams", []))
    print(f"Wrote {path}")
    print(f"{tournament}: dashboard for {n_teams} nations.")
    print("Open output/world_cup_dashboard.html in a browser (link to map in header).")


if __name__ == "__main__":
    main()
