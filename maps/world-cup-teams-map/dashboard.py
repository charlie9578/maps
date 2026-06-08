"""Assemble and write the World Cup squad statistics dashboard HTML."""

from __future__ import annotations

import statistics
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import plotly.graph_objects as go

from dashboard_data import (
    DASH_BG,
    OFFICIAL_SQUAD_SIZE,
    PAGE_MAX_WIDTH,
    abroad_nations_table_html,
    age_extreme_table_html,
    age_extremes,
    birthday_table_html,
    build_player_rows,
    captain_profiles,
    captains_table_html,
    club_country_counts,
    debutants,
    debutants_table_html,
    caps_leaderboard_table_html,
    leaderboard_table_html,
    nation_caps_summaries,
    position_summaries,
    squad_roster_note_html,
    top_players,
    tournament_birthdays,
    veterans,
    youngest_oldest,
)
from dashboard_viz import (
    build_abroad_by_confed_panel,
    build_age_bands_panel,
    build_age_milestones_panel,
    build_club_countries_treemap,
    build_confed_sankey_panel,
    build_geography_panel,
    build_nation_experience_panel,
    build_records_panel,
    build_top_clubs_panel,
)
from dashboard_captains import build_captain_position_panel, build_captains_panel
from dashboard_records import build_goals_caps_scatter
from data_processing import Team, build_teams, load_clubs, load_squads
from map_embed import MapBundle, prepare_map_bundle

MAP_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = MAP_DIR / "output"
DEFAULT_OUTPUT = OUTPUT_DIR / "world_cup_dashboard.html"


@dataclass(frozen=True)
class DashboardPage:
    slug: str
    filename: str
    label: str
    page_title: str


DASHBOARD_PAGES: tuple[DashboardPage, ...] = (
    DashboardPage("overview", "world_cup_dashboard.html", "Overview", "Overview"),
    DashboardPage("map", "world_cup_dashboard_map.html", "Flight paths", "Flight paths"),
    DashboardPage("squads", "world_cup_dashboard_squads.html", "Squad stats", "Squad stats"),
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

PLOTLY_CONFIG = {"displayModeBar": False, "responsive": True}


def _figure_to_div(fig: go.Figure, *, include_plotlyjs: bool | str = False) -> str:
    return fig.to_html(
        full_html=False,
        include_plotlyjs=include_plotlyjs,
        config=PLOTLY_CONFIG,
    )


def _page_styles() -> str:
    return f"""
    :root {{
      --page-max-width: {PAGE_MAX_WIDTH}px;
      --page-gutter: 16px;
    }}
    html, body {{
      margin: 0;
      background: {DASH_BG};
      color: #e2e8f0;
      font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    }}
    .site-width {{
      max-width: var(--page-max-width);
      margin-left: auto;
      margin-right: auto;
      padding-left: var(--page-gutter);
      padding-right: var(--page-gutter);
      box-sizing: border-box;
    }}
    .top-nav {{
      position: sticky;
      top: 0;
      z-index: 1000;
      background: rgba(15, 23, 42, 0.94);
      border-bottom: 1px solid #334155;
      backdrop-filter: blur(10px);
      box-shadow: 0 12px 30px rgba(2, 6, 23, 0.22);
    }}
    .top-nav-inner {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px 12px;
      align-items: center;
      padding-top: 12px;
      padding-bottom: 12px;
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
    .section-head {{
      max-width: var(--page-max-width);
      margin: 28px auto 6px;
      padding: 0 var(--page-gutter);
    }}
    .section-title {{
      margin: 0;
      font-size: 15px;
      font-weight: 600;
      color: #cbd5e1;
      letter-spacing: 0.02em;
      text-transform: uppercase;
    }}
    .section-lead {{
      margin: 6px 0 0;
      color: #94a3b8;
      font-size: 14px;
      line-height: 1.55;
      max-width: 72ch;
    }}
    .chart-block {{ margin: 0 auto 16px; max-width: var(--page-max-width); padding: 0 var(--page-gutter); }}
    .chart-row {{
      display: grid;
      gap: 16px;
      max-width: var(--page-max-width);
      margin: 0 auto 16px;
      padding: 0 var(--page-gutter);
    }}
    @media (min-width: 1024px) {{
      .chart-row {{ grid-template-columns: 1fr 1fr; }}
    }}
    .chart-column .section-head {{
      margin: 0 0 6px;
      padding: 0 8px;
    }}
    .chart-row .chart-column .chart-block {{
      margin: 0;
      max-width: none;
      padding: 0;
    }}
    .chart-block .plotly-graph-div {{ margin: 0 auto; width: 100% !important; }}
    .chart-block.chart-card .plotly-graph-div {{
      border: 1px solid #334155;
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 18px 45px rgba(2, 6, 23, 0.22);
    }}
    .chart-block.chart-card .js-plotly-plot .modebar,
    .chart-block.chart-overview .js-plotly-plot .modebar {{
      display: none !important;
    }}
    .table-section {{ max-width: var(--page-max-width); margin: 0 auto 24px; padding: 0 var(--page-gutter); }}
    .table-note {{ color: #94a3b8; font-size: 13px; margin: 0 0 10px; }}
    .table-grid {{
      display: grid;
      gap: 16px;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    }}
    @media (min-width: 1100px) {{
      .table-grid {{ grid-template-columns: 1fr 1fr; }}
    }}
    .table-grid .table-wrap.table-wide {{ grid-column: 1 / -1; }}
    .table-wrap {{
      max-height: 420px;
      overflow: auto;
      border: 1px solid #334155;
      border-radius: 12px;
      background: #1e293b;
      box-shadow: 0 18px 45px rgba(2, 6, 23, 0.22);
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
      font-variant-numeric: tabular-nums;
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
      max-width: var(--page-max-width);
      margin: 22px auto 12px;
      padding: 22px var(--page-gutter);
      border: 1px solid #334155;
      border-radius: 16px;
      background:
        radial-gradient(circle at top right, rgba(56, 189, 248, 0.16), transparent 30%),
        linear-gradient(135deg, rgba(30, 41, 59, 0.98), rgba(15, 23, 42, 0.88));
      box-shadow: 0 22px 55px rgba(2, 6, 23, 0.28);
    }}
    .page-intro h1 {{
      margin: 0 0 8px;
      font-size: clamp(1.6rem, 2.6vw, 2.35rem);
      font-weight: 700;
      color: #f1f5f9;
      letter-spacing: -0.035em;
    }}
    .page-intro p {{
      margin: 0;
      color: #94a3b8;
      font-size: 15px;
      line-height: 1.6;
    }}
    .insight-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px;
      max-width: var(--page-max-width);
      margin: 0 auto 22px;
      padding: 0 var(--page-gutter);
    }}
    .insight-card {{
      border: 1px solid #334155;
      border-radius: 14px;
      padding: 14px 16px;
      background: linear-gradient(180deg, rgba(30, 41, 59, 0.95), rgba(15, 23, 42, 0.78));
      box-shadow: 0 14px 36px rgba(2, 6, 23, 0.20);
    }}
    .insight-kicker {{
      margin: 0 0 7px;
      color: #38bdf8;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    .insight-main {{
      margin: 0;
      color: #f8fafc;
      font-size: 20px;
      font-weight: 700;
      line-height: 1.15;
    }}
    .insight-detail {{
      margin: 7px 0 0;
      color: #94a3b8;
      font-size: 13px;
      line-height: 1.45;
    }}
    .chart-block.chart-overview {{
      margin-bottom: 0;
    }}
    .chart-block.chart-overview .plotly-graph-div {{
      border-radius: 0;
    }}
    .chart-block.chart-map .plotly-graph-div {{
      min-height: 640px;
      border: 1px solid #334155;
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 18px 45px rgba(2, 6, 23, 0.22);
    }}
    .chart-block.chart-map .js-plotly-plot .modebar {{
      display: flex !important;
    }}
    .map-toolbar {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      max-width: var(--page-max-width);
      margin: 0 auto 10px;
      padding: 0 var(--page-gutter);
    }}
    .map-btn {{
      padding: 8px 14px;
      border: 1px solid #475569;
      border-radius: 8px;
      background: #1e293b;
      color: #e2e8f0;
      font: 14px system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
      cursor: pointer;
      box-shadow: 0 1px 4px rgba(0, 0, 0, 0.25);
    }}
    .map-btn:hover {{ background: #334155; }}
    .page-footer {{
      max-width: var(--page-max-width);
      margin: 32px auto 24px;
      padding: 12px var(--page-gutter);
      border-top: 1px solid #334155;
      color: #64748b;
      font-size: 12px;
      line-height: 1.6;
    }}
    .page-footer a {{ color: #93c5fd; }}
    .roster-note {{
      margin: 0 auto 20px;
      padding: 16px 18px;
      border: 1px solid #475569;
      border-radius: 12px;
      background: rgba(30, 41, 59, 0.72);
      color: #94a3b8;
      font-size: 14px;
      line-height: 1.55;
    }}
    .roster-note-title {{
      margin: 0 0 8px;
      color: #cbd5e1;
      font-size: 15px;
      font-weight: 600;
    }}
    .roster-note p {{ margin: 0 0 10px; }}
    .roster-note-foot {{ margin: 10px 0 0; font-size: 13px; color: #64748b; }}
    .roster-note-list {{
      margin: 0;
      padding-left: 1.25rem;
    }}
    .roster-note-list li {{ margin: 6px 0; }}
    .roster-note a {{ color: #93c5fd; }}
    .guide-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 14px;
      max-width: var(--page-max-width);
      margin: 0 auto 24px;
      padding: 0 var(--page-gutter);
    }}
    .guide-card {{
      border: 1px solid #334155;
      border-radius: 14px;
      padding: 16px 18px;
      background: linear-gradient(180deg, rgba(30, 41, 59, 0.95), rgba(15, 23, 42, 0.78));
      box-shadow: 0 14px 36px rgba(2, 6, 23, 0.20);
      display: flex;
      flex-direction: column;
      gap: 8px;
    }}
    .guide-card h3 {{
      margin: 0;
      color: #f1f5f9;
      font-size: 17px;
      font-weight: 700;
      letter-spacing: -0.02em;
    }}
    .guide-stat {{
      margin: 0;
      color: #38bdf8;
      font-size: 22px;
      font-weight: 700;
      line-height: 1.2;
    }}
    .guide-blurb {{
      margin: 0;
      color: #94a3b8;
      font-size: 14px;
      line-height: 1.55;
      flex: 1;
    }}
    .guide-link {{
      margin-top: 4px;
      color: #93c5fd;
      font-size: 14px;
      font-weight: 600;
      text-decoration: none;
    }}
    .guide-link:hover {{ color: #bfdbfe; text-decoration: underline; }}
    """


def _page_href(slug: str) -> str:
    for page in DASHBOARD_PAGES:
        if page.slug == slug:
            return page.filename
    return "#"


def _nav_html(tournament: str, active_slug: str) -> str:
    links: list[str] = []
    for page in DASHBOARD_PAGES:
        cls = ' class="nav-active"' if page.slug == active_slug else ""
        links.append(f'<a href="{page.filename}"{cls}>{page.label}</a>')
    dash_links = "\n    <span class=\"nav-sep\">|</span>\n    ".join(links)
    return f"""  <nav class="top-nav">
    <div class="site-width top-nav-inner">
    <span class="nav-brand">{tournament} squad dashboard</span>
    <span class="nav-sep">|</span>
    {dash_links}
    </div>
  </nav>"""


def _footer_html(source_accessed: str) -> str:
    return f"""  <footer class="page-footer">
    Data source:
    <a href="https://en.wikipedia.org/wiki/2026_FIFA_World_Cup_squads">Wikipedia — 2026 FIFA World Cup squads</a>
    (accessed {source_accessed}).
    Ages as of 11 Jun 2026; caps and goals are pre-tournament international totals.
    Club locations from curated <code>clubs.json</code> (Wikipedia stadium coordinates).
  </footer>"""


def _page_intro(
    slug: str,
    tournament: str,
    rows: list,
    *,
    map_bundle: MapBundle | None = None,
) -> str:
    """Per-page headline and blurb."""
    n_players = len(rows)
    abroad_pct = round(100 * sum(1 for r in rows if not r.domestic) / max(1, n_players))
    bdays = tournament_birthdays(rows)
    top_club_country = club_country_counts(rows).most_common(1)
    top_cc_name, top_cc_n = top_club_country[0] if top_club_country else ("—", 0)
    n_nations = len({r.nation for r in rows})

    intros: dict[str, tuple[str, str]] = {
        "overview": (
            "Overview",
            f"A guide to all {n_players:,} squad players across {n_nations} nations. "
            f"Start here for headline numbers, then follow the themed sections below — "
            f"each links to a deeper page. {abroad_pct}% play outside their home federation.",
        ),
        "squads": (
            "Squad stats",
            f"How all {n_players:,} players break down by position and nation — age and caps distributions "
            "by GK/DF/MF/FW, plus which squads arrive with the most international experience.",
        ),
        "records": (
            "Records & leaderboards",
            "Pre-tournament international goals and caps: every player on the scatter plot, "
            "with scrollable leaderboards for top scorers, cap holders, and uncapped debutants.",
        ),
        "captains": (
            "Captains",
            "Each nation's armband holder compared with the rest of the squad: seniority, scoring burden, "
            "age gap, and how often leadership comes from outside the domestic game.",
        ),
        "age": (
            "Age & birthdays",
            f"Squad ages as of 11 June 2026, from teenage selections to late-career veterans. "
            f"{len(bdays)} players celebrate a birthday during the tournament window.",
        ),
        "geography": (
            "Geography & clubs",
            "Club host countries, capital-to-stadium distances, and which national squads depend most "
            f"on overseas club football. {top_cc_name} alone hosts {top_cc_n} squad members.",
        ),
    }
    if slug == "map" and map_bundle:
        top_club = Counter(r.club for r in rows).most_common(1)
        top_club_line = (
            f" Start with the top clubs chart — {top_club[0][0]} supplies {top_club[0][1]} players — "
            "then click those cities on the map."
            if top_club
            else ""
        )
        intros["map"] = (
            "Flight paths",
            f"Where squads play club football: top supplying clubs and confederation flows, "
            f"then an interactive map of {map_bundle.route_count:,} capital-to-club routes across "
            f"{map_bundle.stadium_count} locations.{top_club_line}",
        )
    title, blurb = intros.get(slug, (slug.title(), ""))
    return f"""  <header class="page-intro">
    <h1>{tournament} — {title}</h1>
    <p>{blurb}</p>
  </header>"""


def _insight_card(kicker: str, main: str, detail: str) -> str:
    return f"""    <article class="insight-card">
      <p class="insight-kicker">{kicker}</p>
      <p class="insight-main">{main}</p>
      <p class="insight-detail">{detail}</p>
    </article>"""


def _guide_card(title: str, stat: str, blurb: str, href: str) -> str:
    return f"""    <article class="guide-card">
      <h3>{title}</h3>
      <p class="guide-stat">{stat}</p>
      <p class="guide-blurb">{blurb}</p>
      <a class="guide-link" href="{href}">Explore →</a>
    </article>"""


def _render_overview_guide(rows: list) -> str:
    """Themed jump sections linking each analysis page."""
    n_players = len(rows)
    abroad_n = sum(1 for r in rows if not r.domestic)
    abroad_pct = round(100 * abroad_n / max(1, n_players))
    top_club = Counter(r.club for r in rows).most_common(1)
    top_host = club_country_counts(rows).most_common(1)
    top_goals = top_players(rows, "goals", limit=1)
    top_caps = top_players(rows, "caps", limit=1)
    ages = [r.age for r in rows if r.age is not None]
    bdays = tournament_birthdays(rows)
    caps = captain_profiles(rows)
    distances = [r.distance_km for r in rows if r.distance_km is not None]
    median_dist = f"{statistics.median(distances):,.0f} km" if distances else "—"
    pos_stats = position_summaries(rows)
    top_pos = max(pos_stats, key=lambda p: p.count) if pos_stats else None

    top_club_stat = f"{top_club[0][0]} · {top_club[0][1]} players" if top_club else "—"
    top_club_blurb = (
        "Named club employers and confederation flows — then click those cities on the interactive map."
        if top_club
        else "Club hotspots and confederation flows on the interactive map."
    )

    cards = [
        (
            "Flight paths",
            top_club_stat,
            f"{abroad_pct}% play abroad. {top_club_blurb}",
            _page_href("map"),
        ),
        (
            "Squad stats",
            f"{top_pos.count} {top_pos.pos}" if top_pos else f"{n_players:,} players",
            "Position breakdown and average international caps by nation.",
            _page_href("squads"),
        ),
        (
            "Records",
            f"{top_goals[0].goals} goals · {top_caps[0].caps} caps"
            if top_goals and top_caps
            else "Goals & caps",
            "Goals vs caps scatter and scrollable leaderboards.",
            _page_href("records"),
        ),
        (
            "Captains",
            f"{len(caps)} armbands",
            f"{sum(1 for p in caps if p.plays_abroad)} captains play abroad; "
            f"compare position mix and per-nation age/caps gaps.",
            _page_href("captains"),
        ),
        (
            "Age & birthdays",
            f"{statistics.median(ages):.1f} yr median" if ages else "Squad ages",
            f"Age profile from teenage picks to veterans; {len(bdays)} players have a birthday during the tournament.",
            _page_href("age"),
        ),
        (
            "Geography & clubs",
            f"{top_host[0][0]} · {top_host[0][1]} players" if top_host else "Club countries",
            f"Host countries, distance from capital to club ({median_dist} median), and abroad share by nation.",
            _page_href("geography"),
        ),
    ]
    return '  <section class="guide-grid">\n' + "\n".join(
        _guide_card(title, stat, blurb, href) for title, stat, blurb, href in cards
    ) + "\n  </section>"


def _page_insights(
    slug: str,
    rows: list,
    *,
    map_bundle: MapBundle | None = None,
) -> str:
    """Small narrative cards that make each page readable before interacting."""
    n_players = len(rows)
    abroad_n = sum(1 for r in rows if not r.domestic)
    abroad_pct = round(100 * abroad_n / max(1, n_players))
    top_goals = top_players(rows, "goals", limit=1)
    top_caps = top_players(rows, "caps", limit=1)
    top_club = Counter(r.club for r in rows).most_common(1)
    top_host = club_country_counts(rows).most_common(1)
    n_nations = len({r.nation for r in rows})
    n_clubs = len({r.club for r in rows})
    n_club_countries = len({r.club_country for r in rows if r.club_country != "Unknown"})
    ages = [r.age for r in rows if r.age is not None]
    distances = [r.distance_km for r in rows if r.distance_km is not None]
    youngest, oldest = age_extremes(rows)
    bdays = tournament_birthdays(rows)
    caps = captain_profiles(rows)
    pos_stats = position_summaries(rows)
    nation_stats = nation_caps_summaries(rows)
    top_pos = max(pos_stats, key=lambda p: p.count) if pos_stats else None
    most_exp_nation = nation_stats[0] if nation_stats else None
    least_exp_nation = nation_stats[-1] if nation_stats else None

    cards_by_slug: dict[str, list[tuple[str, str, str]]] = {
        "overview": [
            (
                "All squads",
                f"{n_players:,} players",
                f"{n_nations} nations · {OFFICIAL_SQUAD_SIZE}-player squads at the expanded World Cup.",
            ),
            (
                "Playing abroad",
                f"{abroad_pct}%",
                f"{abroad_n:,} of {n_players:,} squad members play outside their home federation.",
            ),
            (
                "Club countries",
                f"{n_club_countries} countries",
                f"Squad members are based in {n_club_countries} different countries"
                + (f"; {top_host[0][0]} hosts the most ({top_host[0][1]})." if top_host else "."),
            ),
            (
                "Distinct clubs",
                f"{n_clubs:,} clubs",
                f"Named employers across all squads"
                + (f"; {top_club[0][0]} supplies the most ({top_club[0][1]})." if top_club else "."),
            ),
        ],
        "squads": [
            (
                "Largest line",
                f"{top_pos.pos} · {top_pos.count}" if top_pos else "—",
                "Share of all squad players in each outfield/GK position.",
            ),
            (
                "Most experienced",
                f"{most_exp_nation.nation} · {most_exp_nation.avg_caps:.0f} avg caps"
                if most_exp_nation
                else "—",
                "Nation with the highest average caps per squad member.",
            ),
            (
                "Least experienced",
                f"{least_exp_nation.nation} · {least_exp_nation.avg_caps:.0f} avg caps"
                if least_exp_nation
                else "—",
                "Nation with the lowest average caps per squad member.",
            ),
            (
                "Median caps",
                f"{statistics.median([r.caps for r in rows if r.caps is not None]):.0f}"
                if any(r.caps is not None for r in rows)
                else "—",
                "Typical pre-tournament international caps across all players.",
            ),
        ],
        "records": [
            (
                "Top scorer",
                f"{top_goals[0].goals} goals" if top_goals else "No goals data",
                f"{top_goals[0].name} ({top_goals[0].nation}) leads the field." if top_goals else "",
            ),
            (
                "Most capped",
                f"{top_caps[0].caps} caps" if top_caps else "No caps data",
                f"{top_caps[0].name} ({top_caps[0].nation}) anchors the experience chart." if top_caps else "",
            ),
            ("Centurions", f"{len(veterans(rows))}", "Players with 100+ pre-tournament caps."),
            ("Uncapped", f"{len(debutants(rows))}", "Players entering with zero senior international caps."),
        ],
        "captains": [
            ("Captains", f"{len(caps)}", "One armband holder per nation in the source data."),
            (
                "Most-capped leaders",
                f"{sum(1 for p in caps if p.most_capped_on_team)}",
                "Captains who are also their squad's appearance leader.",
            ),
            (
                "Captains abroad",
                f"{sum(1 for p in caps if p.plays_abroad)}",
                "Armband holders playing outside their national federation.",
            ),
            (
                "Top-scorer captains",
                f"{sum(1 for p in caps if p.top_scorer_on_team)}",
                "Captains who share or hold the squad scoring lead.",
            ),
        ],
        "age": [
            (
                "Median age",
                f"{statistics.median(ages):.1f} years" if ages else "No age data",
                "Squad age on opening day, 11 June 2026.",
            ),
            (
                "Youngest",
                f"{youngest[0].age} years" if youngest else "No age data",
                f"{youngest[0].name} ({youngest[0].nation})." if youngest else "",
            ),
            (
                "Oldest",
                f"{oldest[0].age} years" if oldest else "No age data",
                f"{oldest[0].name} ({oldest[0].nation})." if oldest else "",
            ),
            (
                "Tournament birthdays",
                f"{len(bdays)} players",
                "Turn a year older between the opening match and the final.",
            ),
        ],
        "geography": [
            (
                "Playing abroad",
                f"{abroad_pct}%",
                f"{abroad_n:,} players are based outside their home federation.",
            ),
            (
                "Top host country",
                f"{top_host[0][0]}" if top_host else "No club data",
                f"{top_host[0][1]} squad members play club football there." if top_host else "",
            ),
            (
                "Club countries",
                f"{n_club_countries}",
                "Different countries represented by player club locations.",
            ),
            (
                "Median route",
                f"{statistics.median(distances):,.0f} km" if distances else "No distance data",
                "Capital-to-club great-circle distance across all players.",
            ),
        ],
    }

    if slug == "map":
        if not map_bundle:
            return ""
        cards = [
            (
                "Nations",
                f"{map_bundle.nation_count}",
                "Capitals plotted for each qualified team.",
            ),
            (
                "Flight paths",
                f"{map_bundle.route_count:,}",
                "Capital-to-club great-circle routes (one arc per nation–club pair).",
            ),
            (
                "Club locations",
                f"{map_bundle.stadium_count}",
                "Stadium cities with squad members in the dataset.",
            ),
            (
                "Playing abroad",
                f"{abroad_pct}%",
                f"{abroad_n:,} players based outside their home federation.",
            ),
        ]
    else:
        cards = cards_by_slug.get(slug, [])
    if not cards:
        return ""
    return '  <section class="insight-grid">\n' + "\n".join(
        _insight_card(kicker, main, detail) for kicker, main, detail in cards
    ) + "\n  </section>"


def _page_shell(
    tournament: str,
    *,
    page_title: str,
    active_slug: str,
    body: str,
    source_accessed: str,
    rows: list,
    map_bundle: MapBundle | None = None,
) -> str:
    intro = _page_intro(active_slug, tournament, rows, map_bundle=map_bundle)
    insights = _page_insights(active_slug, rows, map_bundle=map_bundle)
    roster_note = squad_roster_note_html(rows) if active_slug == "overview" else ""
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
{insights}
{roster_note}
  {body}
{footer}
</body>
</html>
"""


def _section_head(title: str, lead: str = "") -> str:
    if not title:
        return ""
    lead_html = f'\n    <p class="section-lead">{lead}</p>' if lead else ""
    return f'<div class="section-head">\n    <h2 class="section-title">{title}</h2>{lead_html}\n  </div>'


def _render_figure_section(
    title: str,
    fig: go.Figure,
    *,
    lead: str = "",
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
    head = _section_head(title, lead)
    return (
        f"{head}\n"
        f'<section class="{block_cls}">\n'
        f"{_figure_to_div(fig, include_plotlyjs=include_plotlyjs)}\n"
        f"</section>"
    )


def _render_chart_column(
    title: str,
    fig: go.Figure,
    *,
    lead: str = "",
    include_plotlyjs: bool | str = False,
) -> str:
    """Side-by-side chart cell: section head + figure card."""
    head = _section_head(title, lead)
    return (
        f'<div class="chart-column">\n'
        f"{head}\n"
        f'<section class="chart-block chart-card">\n'
        f"{_figure_to_div(fig, include_plotlyjs=include_plotlyjs)}\n"
        f"</section>\n"
        f"</div>"
    )


def _render_chart_row(*columns: str) -> str:
    return f'<div class="chart-row">\n{"".join(columns)}\n</div>'


def _render_table_section(title: str, table_html: str, *, lead: str = "") -> str:
    head = _section_head(title, lead)
    return (
        f"{head}\n"
        f'<section class="chart-block table-section">\n'
        f"    {table_html}\n"
        f"</section>"
    )


def _render_map_section(map_bundle: MapBundle) -> str:
    head = _section_head(
        "Interactive map",
        "Great-circle routes from each national capital to club city. "
        "Click clubs and capitals to focus paths; use the legend for confederations.",
    )
    toolbar = """<div class="map-toolbar">
  <button type="button" class="map-btn" onclick="showAll()">Show all</button>
  <button type="button" class="map-btn" onclick="hideAll()">Hide all</button>
</div>"""
    return (
        f"{head}\n"
        f"{toolbar}\n"
        f'<section class="chart-block chart-map">\n'
        f"{map_bundle.div_html}\n"
        f"</section>"
    )


def _build_page_bodies(
    tournament: str,
    teams: list[Team],
    clubs: dict[str, dict],
    *,
    source_accessed: str,
    map_bundle: MapBundle | None = None,
) -> dict[str, str]:
    rows = build_player_rows(teams, clubs)
    top_clubs_fig = build_top_clubs_panel(tournament, rows, clubs)
    sankey_fig = build_confed_sankey_panel(tournament, rows)
    captain_position_fig = build_captain_position_panel(tournament, rows)
    records_fig = build_records_panel(tournament, rows)
    scatter_fig = build_goals_caps_scatter(tournament, rows)
    nation_experience_fig = build_nation_experience_panel(tournament, rows)
    captains_fig = build_captains_panel(tournament, rows)
    age_milestones_fig = build_age_milestones_panel(tournament, rows)
    age_bands_fig = build_age_bands_panel(tournament, rows)
    treemap_fig = build_club_countries_treemap(tournament, rows)
    geography_fig = build_geography_panel(tournament, rows)
    abroad_confed_fig = build_abroad_by_confed_panel(tournament, rows)

    leaderboards_html = (
        f'<div class="table-grid">'
        f"{leaderboard_table_html(top_players(rows, 'goals', limit=30), title='Top international goal scorers', metric='goals')}"
        f"{caps_leaderboard_table_html(rows)}"
        f"{debutants_table_html(debutants(rows))}"
        f"</div>"
    )

    overview = _render_overview_guide(rows)

    squads = "\n".join(
        [
            _render_figure_section(
                "Squad experience by nation",
                nation_experience_fig,
                lead="Average international caps per squad member — most and least experienced nations.",
                include_plotlyjs="cdn",
            ),
            _render_figure_section(
                "Breakdown by position",
                records_fig,
                lead="Age and caps distributions by GK/DF/MF/FW, plus total goals and position leaders.",
            ),
        ]
    )

    records = "\n".join(
        [
            _render_figure_section(
                "Goals vs caps",
                scatter_fig,
                lead="Every player plotted by pre-tournament international record. Marker size reflects age; colour is position.",
                include_plotlyjs="cdn",
            ),
            _render_table_section(
                "Leaderboards",
                leaderboards_html,
                lead="Top scorers, cap leaders (★ = 100+ caps), and uncapped debutants.",
            ),
        ]
    )

    captains = "\n".join(
        [
            _render_figure_section(
                "Position mix",
                captain_position_fig,
                lead="Share of captains vs all squad players at each position (GK / DF / MF / FW).",
                include_plotlyjs="cdn",
            ),
            _render_figure_section(
                "Captains vs squad mates",
                captains_fig,
                lead="Group averages, distributions, and per-nation age/caps gaps versus the rest of the squad.",
            ),
            _render_table_section(
                "Captain profiles",
                captains_table_html(captain_profiles(rows)),
                lead="Δ age and Δ caps exclude the captain when computing squad averages.",
            ),
        ]
    )

    youngest, oldest = youngest_oldest(rows, n=6)
    age_extremes_html = (
        f'<div class="table-grid">'
        f"{age_extreme_table_html(youngest, title='Six youngest', note='Ages on 11 Jun 2026.')}"
        f"{age_extreme_table_html(oldest, title='Six oldest', note='Ages on 11 Jun 2026.')}"
        f"</div>"
    )

    age = "\n".join(
        [
            _render_figure_section(
                "Squad age profile",
                age_milestones_fig,
                lead="One bar per squad age on 11 Jun 2026, with median and min/max markers.",
                include_plotlyjs="cdn",
            ),
            _render_table_section(
                "Youngest & oldest",
                age_extremes_html,
                lead="Six youngest and six oldest squad selections, including ties at the cutoff.",
            ),
            _render_figure_section(
                "Age bands by confederation",
                age_bands_fig,
                lead="Share of each squad in five-year age bands (100% stacked).",
            ),
            _render_table_section(
                "Tournament birthdays",
                birthday_table_html(tournament_birthdays(rows)),
                lead="Players whose birthday falls between the opening match and the final.",
            ),
        ]
    )

    geography = "\n".join(
        [
            _render_figure_section(
                "Club host countries",
                treemap_fig,
                lead="Where squad members play club football, sized by player count and coloured by club confederation.",
                include_plotlyjs="cdn",
            ),
            _render_chart_row(
                _render_chart_column(
                    "Playing abroad",
                    abroad_confed_fig,
                    lead="Domestic vs abroad split within each national confederation.",
                ),
                _render_chart_column(
                    "Flight distances",
                    geography_fig,
                    lead="Great-circle distance from national capital to club city.",
                ),
            ),
            _render_table_section(
                "Playing abroad by nation",
                abroad_nations_table_html(rows),
                lead="All 48 nations ranked by share of the squad playing outside their home federation.",
            ),
        ]
    )

    map_page = "\n".join(
        [
            _render_figure_section(
                "Clubs supplying the most players",
                top_clubs_fig,
                lead="Hotspots to explore on the map below — click a club city to reveal flight paths.",
                include_plotlyjs="cdn",
            ),
            _render_figure_section(
                "National → club confederation",
                sankey_fig,
                lead="How each national federation connects to club confederations worldwide.",
            ),
            _render_map_section(map_bundle) if map_bundle else "",
        ]
    )

    return {
        "overview": overview,
        "map": map_page,
        "squads": squads,
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
    map_bundle = prepare_map_bundle(tournament, teams, include_plotlyjs="cdn", embedded=True)

    bodies = _build_page_bodies(
        tournament,
        teams,
        clubs,
        source_accessed=accessed,
        map_bundle=map_bundle,
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
            map_bundle=map_bundle if page.slug == "map" else None,
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
