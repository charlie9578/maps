"""Assemble and write the World Cup squad statistics dashboard HTML."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import plotly.graph_objects as go

from dashboard_data import (
    DASH_BG,
    abroad_nations_table_html,
    age_extremes,
    birthday_table_html,
    build_player_rows,
    captain_profiles,
    captains_table_html,
    debutants,
    debutants_table_html,
    leaderboard_table_html,
    top_players,
    tournament_birthdays,
    veterans,
)
from dashboard_viz import (
    build_age_experience_panel,
    build_age_milestones_panel,
    build_captains_panel,
    build_dashboard,
    build_geography_panel,
    build_goals_caps_panel,
    build_nation_experience_panel,
    build_proportional_panel,
    build_records_panel,
)
from data_processing import Team, build_teams, load_clubs, load_squads

MAP_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = MAP_DIR / "output"
DEFAULT_OUTPUT = OUTPUT_DIR / "world_cup_dashboard.html"

MAP_HTML = "world_cup_teams_map.html"


@dataclass(frozen=True)
class DashboardPage:
    slug: str
    filename: str
    label: str
    page_title: str


DASHBOARD_PAGES: tuple[DashboardPage, ...] = (
    DashboardPage("overview", "world_cup_dashboard.html", "Overview", "Overview"),
    DashboardPage("records", "world_cup_dashboard_records.html", "Records", "Records"),
    DashboardPage("captains", "world_cup_dashboard_captains.html", "Captains", "Captains"),
    DashboardPage("age", "world_cup_dashboard_age.html", "Age & birthdays", "Age & birthdays"),
    DashboardPage(
        "geography",
        "world_cup_dashboard_geography.html",
        "Geography",
        "Geography & clubs",
    ),
)

def _figure_to_div(fig: go.Figure, *, include_plotlyjs: bool | str = False) -> str:
    return fig.to_html(
        full_html=False,
        include_plotlyjs=include_plotlyjs,
        config={"displayModeBar": True, "responsive": True},
    )


def _page_styles() -> str:
    return f"""
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
      flex-wrap: wrap;
      gap: 8px 12px;
      align-items: center;
      padding: 10px 16px;
      background: rgba(15, 23, 42, 0.92);
      border-bottom: 1px solid #334155;
      backdrop-filter: blur(6px);
    }}
    .top-nav .nav-brand {{
      color: #94a3b8;
      font-size: 14px;
      margin-right: 4px;
    }}
    .top-nav a {{
      color: #93c5fd;
      text-decoration: none;
      font-size: 14px;
    }}
    .top-nav a:hover {{ text-decoration: underline; }}
    .top-nav a.nav-active {{
      color: #e2e8f0;
      font-weight: 600;
      text-decoration: none;
    }}
    .top-nav .nav-sep {{
      color: #475569;
      user-select: none;
    }}
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
    .data-table tbody tr:nth-child(even) td {{ background: rgba(15, 23, 42, 0.35); }}
    .data-table .rank {{
      width: 2.5rem;
      color: #64748b;
      font-variant-numeric: tabular-nums;
      text-align: right;
    }}
    .data-table .delta-pos {{ color: #34d399; }}
    .data-table .delta-neg {{ color: #fb7185; }}
    .data-table tr.row-highlight td {{ background: rgba(251, 191, 36, 0.12); }}
    .data-table tr.row-opening td {{ background: rgba(56, 189, 248, 0.12); }}
    .page-intro {{
      max-width: 1400px;
      margin: 20px auto 8px;
      padding: 16px 20px;
      border: 1px solid #334155;
      border-radius: 10px;
      background: linear-gradient(135deg, rgba(30, 41, 59, 0.95), rgba(15, 23, 42, 0.85));
    }}
    .page-intro h1 {{
      margin: 0 0 8px;
      font-size: 1.35rem;
      font-weight: 600;
      color: #f1f5f9;
    }}
    .page-intro p {{
      margin: 0 0 12px;
      color: #94a3b8;
      font-size: 14px;
      line-height: 1.5;
      max-width: 72ch;
    }}
    .stat-pills {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .stat-pill {{
      padding: 6px 12px;
      border-radius: 999px;
      background: rgba(51, 65, 85, 0.55);
      border: 1px solid #475569;
      font-size: 13px;
      color: #cbd5e1;
    }}
    .stat-pill strong {{ color: #f8fafc; }}
    .chart-block.chart-overview {{
      max-width: none;
      margin-bottom: 0;
    }}
    .chart-block.chart-overview .plotly-graph-div {{
      border-radius: 0;
    }}
    .chart-card .plotly-graph-div {{
      border: 1px solid #334155;
      border-radius: 8px;
      overflow: hidden;
    }}
    .page-footer {{
      max-width: 1400px;
      margin: 32px auto 24px;
      padding: 12px 16px;
      border-top: 1px solid #334155;
      color: #64748b;
      font-size: 12px;
      line-height: 1.6;
    }}
    .page-footer a {{ color: #93c5fd; }}
    """


def _nav_html(tournament: str, active_slug: str) -> str:
    links: list[str] = []
    for page in DASHBOARD_PAGES:
        cls = ' class="nav-active"' if page.slug == active_slug else ""
        links.append(f'<a href="{page.filename}"{cls}>{page.label}</a>')
    dash_links = "\n    <span class=\"nav-sep\">|</span>\n    ".join(links)
    return f"""  <nav class="top-nav">
    <span class="nav-brand">{tournament} squad dashboard</span>
    <span class="nav-sep">|</span>
    {dash_links}
    <span class="nav-sep">|</span>
    <a href="{MAP_HTML}">Flight-path map</a>
  </nav>"""


def _footer_html(source_accessed: str) -> str:
    return f"""  <footer class="page-footer">
    Data source:
    <a href="https://en.wikipedia.org/wiki/2026_FIFA_World_Cup_squads">Wikipedia — 2026 FIFA World Cup squads</a>
    (accessed {source_accessed}).
    Ages as of 11 Jun 2026; caps and goals are pre-tournament international totals.
    Club locations from curated <code>clubs.json</code> (Wikipedia stadium coordinates).
  </footer>"""


def _page_intro(slug: str, tournament: str, rows: list) -> str:
    """Per-page headline, blurb, and quick stats."""
    n_players = len(rows)
    abroad_pct = round(100 * sum(1 for r in rows if not r.domestic) / max(1, n_players))
    youngest, oldest = age_extremes(rows)
    yng = youngest[0] if youngest else None
    old = oldest[0] if oldest else None
    top_g = top_players(rows, "goals", limit=1)
    top_c = top_players(rows, "caps", limit=1)
    ts = top_g[0] if top_g else None
    tc = top_c[0] if top_c else None
    bdays = tournament_birthdays(rows)
    caps = captain_profiles(rows)
    most_capped_caps = sum(1 for p in caps if p.most_capped_on_team)

    intros: dict[str, tuple[str, str, list[str]]] = {
        "overview": (
            "Overview",
            "A high-level picture of all 48 squads: which clubs supply the most players, "
            "how positions break down, where players play relative to their federation, "
            "and age spread by confederation.",
            [
                f"<strong>{n_players:,}</strong> players",
                f"<strong>{abroad_pct}%</strong> abroad",
                f"youngest <strong>{yng.age}</strong> ({yng.nation})" if yng else "",
                f"oldest <strong>{old.age}</strong> ({old.nation})" if old else "",
            ],
        ),
        "records": (
            "Records & leaderboards",
            "International goal and cap leaders, position breakdowns, and squad experience "
            "ranked by nation. Marker size in the scatter plot reflects player age.",
            [
                f"top scorer <strong>{ts.name}</strong> ({ts.goals})" if ts else "",
                f"most caps <strong>{tc.name}</strong> ({tc.caps})" if tc else "",
                f"<strong>{len(veterans(rows))}</strong> with 100+ caps",
                f"<strong>{len(debutants(rows))}</strong> debutants (0 caps)",
            ],
        ),
        "captains": (
            "Captains",
            "How the 48 designated captains compare with their squad mates on age, caps, "
            "goals, position mix, and whether they play abroad.",
            [
                f"<strong>{len(caps)}</strong> captains",
                f"<strong>{most_capped_caps}</strong> are most-capped on team",
                f"<strong>{abroad_pct}%</strong> of all players abroad",
            ],
        ),
        "age": (
            "Age & birthdays",
            "Squad age profiles, youngest and oldest players, and anyone celebrating a "
            "birthday between opening day (11 Jun) and the final (19 Jul 2026).",
            [
                f"<strong>{len(bdays)}</strong> tournament birthdays",
                f"youngest <strong>{yng.name}</strong> ({yng.age})" if yng else "",
                f"oldest <strong>{old.name}</strong> ({old.age})" if old else "",
            ],
        ),
        "geography": (
            "Geography & clubs",
            "Great-circle distances from national capitals to club cities, which nations "
            "export the most players abroad, and proportional views of club host countries.",
            [
                f"<strong>{abroad_pct}%</strong> play abroad",
                f"<strong>{len({r.club_country for r in rows if r.club_country != 'Unknown'})}</strong> club countries",
            ],
        ),
    }
    title, blurb, pills = intros.get(slug, (slug.title(), "", []))
    pill_html = "\n    ".join(
        f'<span class="stat-pill">{p}</span>' for p in pills if p
    )
    return f"""  <header class="page-intro">
    <h1>{tournament} — {title}</h1>
    <p>{blurb}</p>
    <div class="stat-pills">
    {pill_html}
    </div>
  </header>"""


def _page_shell(
    tournament: str,
    *,
    page_title: str,
    active_slug: str,
    body: str,
    source_accessed: str,
    rows: list,
) -> str:
    intro = _page_intro(active_slug, tournament, rows)
    footer = _footer_html(source_accessed)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{tournament} — squad dashboard — {page_title}</title>
  <style>
{_page_styles()}
  </style>
</head>
<body>
{_nav_html(tournament, active_slug)}
{intro}
  {body}
{footer}
</body>
</html>
"""


def _render_figure_section(
    title: str,
    fig: go.Figure,
    *,
    include_plotlyjs: bool | str = False,
    overview: bool = False,
    card: bool = True,
) -> str:
    if overview:
        block_cls = "chart-block chart-overview"
    elif card:
        block_cls = "chart-block chart-card"
    else:
        block_cls = "chart-block"
    title_html = f'<h2 class="section-title">{title}</h2>\n    ' if title else ""
    return (
        f'<section class="{block_cls}">\n'
        f"    {title_html}"
        f"{_figure_to_div(fig, include_plotlyjs=include_plotlyjs)}\n"
        f"</section>"
    )


def _render_table_section(title: str, table_html: str) -> str:
    return (
        f'<section class="chart-block table-section">\n'
        f'    <h2 class="section-title">{title}</h2>\n'
        f"    {table_html}\n"
        f"</section>"
    )


def _build_page_bodies(
    tournament: str,
    teams: list[Team],
    clubs: dict[str, dict],
    *,
    source_accessed: str,
) -> dict[str, str]:
    rows = build_player_rows(teams, clubs)
    main_fig = build_dashboard(tournament, teams, clubs, source_accessed=source_accessed)
    records_fig = build_records_panel(tournament, rows)
    goals_caps_fig = build_goals_caps_panel(tournament, rows)
    nation_experience_fig = build_nation_experience_panel(tournament, rows)
    captains_fig = build_captains_panel(tournament, rows)
    age_milestones_fig = build_age_milestones_panel(tournament, rows)
    age_confed_fig = build_age_experience_panel(tournament, rows)
    proportional_fig = build_proportional_panel(tournament, rows)
    geography_fig = build_geography_panel(tournament, rows)

    leaderboards_html = (
        f'<div class="table-grid">'
        f"{leaderboard_table_html(top_players(rows, 'goals', limit=30), title='Top international goal scorers', metric='goals')}"
        f"{leaderboard_table_html(top_players(rows, 'caps', limit=30), title='Most international caps', metric='caps')}"
        f"{leaderboard_table_html(veterans(rows), title='100+ cap veterans', metric='caps')}"
        f"{debutants_table_html(debutants(rows))}"
        f"</div>"
    )

    overview = _render_figure_section("", main_fig, include_plotlyjs="cdn", overview=True)

    records = "\n".join(
        [
            _render_figure_section("Records & positions", records_fig, include_plotlyjs="cdn"),
            _render_figure_section("Goals & caps", goals_caps_fig),
            _render_figure_section("Squad experience by nation", nation_experience_fig),
            _render_table_section("Full leaderboards", leaderboards_html),
        ]
    )

    captains = "\n".join(
        [
            _render_figure_section(
                "Captains vs squad mates",
                captains_fig,
                include_plotlyjs="cdn",
            ),
            _render_table_section(
                "All 48 captains",
                captains_table_html(captain_profiles(rows)),
            ),
        ]
    )

    age = "\n".join(
        [
            _render_figure_section(
                "Youngest, oldest & birthdays",
                age_milestones_fig,
                include_plotlyjs="cdn",
            ),
            _render_table_section("Birthday list", birthday_table_html(tournament_birthdays(rows))),
            _render_figure_section("Age by confederation", age_confed_fig),
        ]
    )

    geography = "\n".join(
        [
            _render_figure_section("Proportional area", proportional_fig, include_plotlyjs="cdn"),
            _render_figure_section("Geography", geography_fig),
            _render_table_section(
                "Abroad by nation (full ranking)",
                abroad_nations_table_html(rows),
            ),
        ]
    )

    return {
        "overview": overview,
        "records": records,
        "captains": captains,
        "age": age,
        "geography": geography,
    }


def write_dashboard_site(output_dir: Path | None = None) -> list[Path]:
    """Build the multi-page squad dashboard and write standalone HTML files."""
    out = output_dir or OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    squads = load_squads()
    clubs = load_clubs()
    tournament, teams = build_teams(strict=False)
    accessed = squads.get("source_accessed", "2026-06-05")
    rows = build_player_rows(teams, clubs)

    bodies = _build_page_bodies(
        tournament,
        teams,
        clubs,
        source_accessed=accessed,
    )

    written: list[Path] = []
    for page in DASHBOARD_PAGES:
        path = out / page.filename
        html = _page_shell(
            tournament,
            page_title=page.page_title,
            active_slug=page.slug,
            body=bodies[page.slug],
            source_accessed=accessed,
            rows=rows,
        )
        path.write_text(html, encoding="utf-8")
        written.append(path)
    return written


def write_dashboard(output_path: Path | None = None) -> Path:
    """Write all dashboard pages; return the overview HTML path."""
    out_dir = (output_path or DEFAULT_OUTPUT).parent
    paths = write_dashboard_site(out_dir)
    overview = out_dir / "world_cup_dashboard.html"
    if overview in paths:
        return overview
    return paths[0]


def main() -> None:
    paths = write_dashboard_site()
    squads = load_squads()
    tournament = squads.get("tournament", "World Cup")
    n_teams = len(squads.get("teams", []))
    for path in paths:
        print(f"Wrote {path}")
    print(f"{tournament}: dashboard for {n_teams} nations ({len(paths)} pages).")
    print("Open output/world_cup_dashboard.html in a browser (nav links to other pages).")


if __name__ == "__main__":
    main()
