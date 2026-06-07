"""Assemble and write the World Cup squad statistics dashboard HTML."""

from __future__ import annotations

from pathlib import Path

import plotly.graph_objects as go

from dashboard_data import (
    DASH_BG,
    birthday_table_html,
    build_player_rows,
    captain_profiles,
    captains_table_html,
    leaderboard_table_html,
    top_players,
    tournament_birthdays,
    veterans,
)
from dashboard_viz import build_dashboard, build_extra_figures
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
    rows = build_player_rows(teams, clubs)
    birthday_html = birthday_table_html(tournament_birthdays(rows))
    scorers_html = leaderboard_table_html(
        top_players(rows, "goals", limit=30),
        title="Top international goal scorers",
        metric="goals",
    )
    caps_html = leaderboard_table_html(
        top_players(rows, "caps", limit=30),
        title="Most international caps",
        metric="caps",
    )
    veterans_html = leaderboard_table_html(
        veterans(rows),
        title="100+ cap veterans",
        metric="caps",
    )
    captains_html = captains_table_html(captain_profiles(rows))

    sections_html: list[str] = []
    sections_html.append(
        f'<section class="chart-block chart-overview">{_figure_to_div(main_fig, include_plotlyjs="cdn")}</section>'
    )
    for i, (title, fig) in enumerate(extras):
        sections_html.append(
            f'<section class="chart-block">'
            f'<h2 class="section-title">{title}</h2>'
            f"{_figure_to_div(fig, include_plotlyjs=False)}"
            f"</section>"
        )
        if title == "Captains vs squad mates":
            sections_html.append(
                f'<section class="chart-block table-section">'
                f'<h2 class="section-title">All 48 captains</h2>'
                f"{captains_html}"
                f"</section>"
            )
        if title == "Records & positions":
            sections_html.append(
                f'<section class="chart-block table-section">'
                f'<h2 class="section-title">Full leaderboards</h2>'
                f'<div class="table-grid">{scorers_html}{caps_html}{veterans_html}</div>'
                f"</section>"
            )
        if title == "Youngest, oldest & birthdays":
            sections_html.append(
                f'<section class="chart-block table-section">'
                f'<h2 class="section-title">Birthday list</h2>'
                f"{birthday_html}"
                f"</section>"
            )

    body = "\n".join(sections_html)
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
    .section-title {{
      max-width: 1400px;
      margin: 24px auto 4px;
      padding: 0 8px;
      font-size: 15px;
      font-weight: 600;
      color: #cbd5e1;
      letter-spacing: 0.02em;
      text-transform: uppercase;
    }}
    .chart-block {{ margin: 0 auto 8px; max-width: 1400px; }}
    .chart-block .plotly-graph-div {{ margin: 0 auto; }}
    .table-section {{ max-width: 1400px; margin: 0 auto 24px; padding: 0 8px; }}
    .table-note {{ color: #94a3b8; font-size: 13px; margin: 0 0 10px; }}
    .table-grid {{
      display: grid;
      gap: 16px;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    }}
    @media (min-width: 1100px) {{
      .table-grid {{ grid-template-columns: 1fr 1fr; }}
      .table-grid .table-wrap:last-child {{ grid-column: 1 / -1; }}
    }}
    .table-wrap {{
      max-height: 420px;
      overflow: auto;
      border: 1px solid #334155;
      border-radius: 8px;
      background: #1e293b;
    }}
    .data-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }}
    .data-table th, .data-table td {{
      padding: 8px 12px;
      text-align: left;
      border-bottom: 1px solid #334155;
    }}
    .data-table th {{
      position: sticky;
      top: 0;
      background: #0f172a;
      color: #cbd5e1;
      font-weight: 600;
    }}
    .data-table tr:hover td {{ background: rgba(51, 65, 85, 0.45); }}
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
