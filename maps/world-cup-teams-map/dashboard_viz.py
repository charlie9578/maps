"""Plotly dashboard for World Cup squad statistics."""

from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from club_confed import club_confederation, is_domestic, nation_confederation, normalize_country
from data_processing import Team
from viz import CONFED_COLORS, DEFAULT_COLOR, confed_color

DASH_BG = "#0f172a"
PLOT_BG = "#1e293b"
GRID = "#334155"
TEXT = "#e2e8f0"
MUTED = "#94a3b8"

CONFED_ORDER = ["UEFA", "CONMEBOL", "CONCACAF", "CAF", "AFC", "OFC", "OTHER"]
POS_ORDER = ["GK", "DF", "MF", "FW"]
POS_COLORS = {
    "GK": "#f59e0b",
    "DF": "#2563eb",
    "MF": "#16a34a",
    "FW": "#dc2626",
}


@dataclass(frozen=True)
class PlayerRow:
    nation: str
    nation_confed: str
    name: str
    pos: str
    age: int | None
    caps: int | None
    goals: int | None
    club: str
    club_country: str
    club_confed: str
    domestic: bool
    distance_km: float | None


def build_player_rows(teams: list[Team], clubs: dict[str, dict]) -> list[PlayerRow]:
    """Flatten squads into one row per player with club confederation metadata."""
    rows: list[PlayerRow] = []
    for team in teams:
        n_confed = nation_confederation(team.confederation)
        dist_by_club: dict[str, float] = {}
        for route in team.routes:
            for club_name in route.clubs:
                dist_by_club[club_name] = route.distance_km

        for _no, name, pos, _dob, age, caps, goals, club in team.squad:
            club_meta = clubs.get(club, {})
            club_country = normalize_country(str(club_meta.get("country", "Unknown")))
            rows.append(
                PlayerRow(
                    nation=team.nation,
                    nation_confed=n_confed,
                    name=name,
                    pos=pos or "—",
                    age=age,
                    caps=caps,
                    goals=goals,
                    club=club,
                    club_country=club_country,
                    club_confed=club_confederation(club_country),
                    domestic=is_domestic(team.nation, club_country),
                    distance_km=dist_by_club.get(club),
                )
            )
    return rows


def _confed_color(confed: str) -> str:
    return CONFED_COLORS.get(confed, DEFAULT_COLOR)


def _base_layout(fig: go.Figure, tournament: str, source_accessed: str, *, kpi_line: str) -> None:
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=DASH_BG,
        plot_bgcolor=PLOT_BG,
        font={"color": TEXT, "family": "system-ui, Segoe UI, Roboto, sans-serif", "size": 12},
        title={
            "text": (
                f"<b>{tournament} — squad dashboard</b><br>"
                f"<sup>{kpi_line}<br>"
                f"Data: "
                f'<a href="https://en.wikipedia.org/wiki/2026_FIFA_World_Cup_squads" '
                f'style="color:#93c5fd">Wikipedia squads</a> (accessed {source_accessed})</sup>'
            ),
            "x": 0.01,
            "xanchor": "left",
            "y": 0.98,
        },
        margin={"l": 48, "r": 24, "t": 100, "b": 36},
        height=1280,
        showlegend=False,
    )


def build_dashboard(
    tournament: str,
    teams: list[Team],
    clubs: dict[str, dict],
    *,
    source_accessed: str = "2026-06-05",
) -> go.Figure:
    rows = build_player_rows(teams, clubs)
    ages = [r.age for r in rows if r.age is not None]
    caps_vals = [r.caps for r in rows if r.caps is not None]
    distances = [r.distance_km for r in rows if r.distance_km is not None]

    club_counts = Counter(r.club for r in rows)
    pos_counts = Counter(r.pos for r in rows if r.pos in POS_ORDER)
    country_counts = Counter(r.club_country for r in rows if r.club_country != "Unknown")

    domestic_n = sum(1 for r in rows if r.domestic)
    abroad_n = len(rows) - domestic_n

    fig = make_subplots(
        rows=3,
        cols=2,
        column_widths=[0.58, 0.42],
        row_heights=[0.30, 0.38, 0.32],
        specs=[
            [{"type": "bar"}, {"type": "pie"}],
            [{"type": "sankey", "colspan": 2}, None],
            [{"type": "scatter"}, {"type": "bar"}],
        ],
        subplot_titles=(
            "Clubs by World Cup players",
            "Squad by position",
            "Player flow: national confederation → club confederation",
            "",
            "Player age by national confederation",
            "Top club host countries",
        ),
        horizontal_spacing=0.08,
        vertical_spacing=0.09,
    )

    kpi_line = (
        f"<b>{len(rows):,}</b> players · <b>{len(club_counts):,}</b> clubs · "
        f"<b>{statistics.mean(ages):.1f}</b> avg age · "
        f"<b>{100 * abroad_n / len(rows):.0f}%</b> abroad · "
        f"<b>{statistics.mean(caps_vals):.0f}</b> avg caps · "
        f"<b>{statistics.median(distances):,.0f} km</b> median flight distance"
    )

    # Top clubs bar chart.
    top_clubs = club_counts.most_common(25)
    fig.add_trace(
        go.Bar(
            y=[c for c, _ in reversed(top_clubs)],
            x=[n for _, n in reversed(top_clubs)],
            orientation="h",
            marker={"color": "#64748b", "line": {"width": 0}},
            hovertemplate="%{y}<br>%{x} players<extra></extra>",
            name="Clubs",
        ),
        row=1,
        col=1,
    )

    # Position pie.
    fig.add_trace(
        go.Pie(
            labels=[p for p in POS_ORDER if pos_counts[p]],
            values=[pos_counts[p] for p in POS_ORDER if pos_counts[p]],
            marker={"colors": [POS_COLORS[p] for p in POS_ORDER if pos_counts[p]]},
            hole=0.45,
            textinfo="label+percent",
            textfont={"size": 11},
            hovertemplate="%{label}: %{value} players (%{percent})<extra></extra>",
        ),
        row=1,
        col=2,
    )

    # Sankey: nation confed -> club confed.
    flow: dict[tuple[str, str], int] = Counter()
    for r in rows:
        flow[(r.nation_confed, r.club_confed)] += 1
    left_nodes = [c for c in CONFED_ORDER if any(k[0] == c for k in flow)]
    right_nodes = [c for c in CONFED_ORDER if any(k[1] == c for k in flow)]
    node_labels = [f"{c} (national)" for c in left_nodes] + [f"{c} (club)" for c in right_nodes]
    node_colors = [_confed_color(c) for c in left_nodes] + [_confed_color(c) for c in right_nodes]
    left_idx = {c: i for i, c in enumerate(left_nodes)}
    right_idx = {c: i + len(left_nodes) for i, c in enumerate(right_nodes)}
    sources, targets, values = [], [], []
    for (src, tgt), val in sorted(flow.items(), key=lambda x: -x[1]):
        if src in left_idx and tgt in right_idx:
            sources.append(left_idx[src])
            targets.append(right_idx[tgt])
            values.append(val)

    fig.add_trace(
        go.Sankey(
            arrangement="snap",
            node={
                "label": node_labels,
                "color": node_colors,
                "pad": 18,
                "thickness": 16,
                "line": {"color": PLOT_BG, "width": 1},
            },
            link={
                "source": sources,
                "target": targets,
                "value": values,
                "color": "rgba(148, 163, 184, 0.35)",
            },
        ),
        row=2,
        col=1,
    )

    # Age strip plot by national confederation (jittered dots).
    active_confeds = [c for c in CONFED_ORDER if any(r.nation_confed == c for r in rows)]
    confed_x = {c: i for i, c in enumerate(active_confeds)}
    jitter_x, jitter_y, dot_color, hover = [], [], [], []
    for r in rows:
        if r.age is None or r.nation_confed not in confed_x:
            continue
        base = confed_x[r.nation_confed]
        # Deterministic pseudo-jitter from name hash.
        jitter = ((hash(r.name) % 100) - 50) / 120
        jitter_x.append(base + jitter)
        jitter_y.append(r.age)
        dot_color.append(POS_COLORS.get(r.pos, DEFAULT_COLOR))
        hover.append(
            f"{r.name}<br>{r.nation} · {r.pos}<br>age {r.age} · {r.club}<br>{r.club_country}"
        )

    fig.add_trace(
        go.Scatter(
            x=jitter_x,
            y=jitter_y,
            mode="markers",
            marker={
                "size": 7,
                "color": dot_color,
                "opacity": 0.75,
                "line": {"width": 0.5, "color": "#0f172a"},
            },
            text=hover,
            hovertemplate="%{text}<extra></extra>",
            name="Players",
        ),
        row=3,
        col=1,
    )
    for confed in active_confeds:
        if confed not in confed_x:
            continue
        confed_ages = [r.age for r in rows if r.nation_confed == confed and r.age is not None]
        if not confed_ages:
            continue
        fig.add_trace(
            go.Scatter(
                x=[confed_x[confed], confed_x[confed]],
                y=[min(confed_ages), max(confed_ages)],
                mode="lines",
                line={"color": _confed_color(confed), "width": 3},
                opacity=0.35,
                hoverinfo="skip",
                showlegend=False,
            ),
            row=3,
            col=1,
        )

    # Top club host countries.
    top_countries = country_counts.most_common(15)
    fig.add_trace(
        go.Bar(
            x=[c for c, _ in top_countries],
            y=[n for _, n in top_countries],
            marker={"color": [_confed_color(club_confederation(c)) for c, _ in top_countries]},
            hovertemplate="%{x}<br>%{y} players<extra></extra>",
        ),
        row=3,
        col=2,
    )

    _base_layout(fig, tournament, source_accessed, kpi_line=kpi_line)

    # Row 1 bar.
    fig.update_xaxes(title_text="Players", row=1, col=1, gridcolor=GRID, zeroline=False)
    fig.update_yaxes(row=1, col=1, gridcolor=GRID, automargin=True)

    # Age plot.
    fig.update_xaxes(
        tickmode="array",
        tickvals=list(range(len(active_confeds))),
        ticktext=active_confeds,
        title_text="National confederation",
        row=3,
        col=1,
        gridcolor=GRID,
    )
    fig.update_yaxes(title_text="Age (years)", row=3, col=1, gridcolor=GRID, range=[16, 44])

    # Country bar.
    fig.update_xaxes(tickangle=-35, row=3, col=2, gridcolor=GRID)
    fig.update_yaxes(title_text="Players", row=3, col=2, gridcolor=GRID)

    # Subplot title styling.
    for ann in fig.layout.annotations:
        if ann.text and ann.text not in ("", None):
            ann.font = {"size": 13, "color": TEXT}
            ann.xanchor = "left"
            ann.x = 0.01

    return fig


def build_extra_figures(
    tournament: str,
    teams: list[Team],
    clubs: dict[str, dict],
) -> list[tuple[str, go.Figure]]:
    """Additional standalone charts appended below the main dashboard grid."""
    rows = build_player_rows(teams, clubs)
    extras: list[tuple[str, go.Figure]] = []

    # Average squad age by nation.
    nation_ages: dict[str, list[int]] = defaultdict(list)
    for r in rows:
        if r.age is not None:
            nation_ages[r.nation].append(r.age)
    avg_age = sorted(
        ((n, statistics.mean(a)) for n, a in nation_ages.items()),
        key=lambda x: x[1],
        reverse=True,
    )
    fig_age = go.Figure(
        go.Bar(
            y=[n for n, _ in reversed(avg_age)],
            x=[a for _, a in reversed(avg_age)],
            orientation="h",
            marker={"color": [confed_color(next(t.confederation for t in teams if t.nation == n)) for n, _ in reversed(avg_age)]},
            hovertemplate="%{y}<br>avg age %{x:.1f}<extra></extra>",
        )
    )
    fig_age.update_layout(
        title=f"{tournament} — average squad age by nation",
        template="plotly_dark",
        paper_bgcolor=DASH_BG,
        plot_bgcolor=PLOT_BG,
        font={"color": TEXT},
        height=720,
        margin={"l": 120, "r": 24, "t": 56, "b": 40},
        xaxis={"title": "Average age", "gridcolor": GRID},
        yaxis={"gridcolor": GRID, "automargin": True},
    )
    extras.append(("Squad age by nation", fig_age))

    # % abroad by nation.
    abroad_pct: list[tuple[str, float, str]] = []
    by_nation: dict[str, list[PlayerRow]] = defaultdict(list)
    for r in rows:
        by_nation[r.nation].append(r)
    for nation, players in by_nation.items():
        abroad = sum(1 for p in players if not p.domestic)
        abroad_pct.append((nation, 100 * abroad / len(players), players[0].nation_confed))
    abroad_pct.sort(key=lambda x: x[1], reverse=True)

    fig_abroad = go.Figure(
        go.Bar(
            x=[n for n, _, _ in abroad_pct],
            y=[p for _, p, _ in abroad_pct],
            marker={"color": [_confed_color(c) for _, _, c in abroad_pct]},
            hovertemplate="%{x}<br>%{y:.0f}% playing abroad<extra></extra>",
        )
    )
    fig_abroad.update_layout(
        title=f"{tournament} — share of squad playing abroad",
        template="plotly_dark",
        paper_bgcolor=DASH_BG,
        plot_bgcolor=PLOT_BG,
        font={"color": TEXT},
        height=420,
        margin={"l": 48, "r": 24, "t": 56, "b": 100},
        xaxis={"tickangle": -45, "gridcolor": GRID},
        yaxis={"title": "% abroad", "gridcolor": GRID, "range": [0, 105]},
    )
    extras.append(("Playing abroad", fig_abroad))

    # Caps vs age scatter.
    fig_caps = go.Figure(
        go.Scatter(
            x=[r.age for r in rows if r.age is not None and r.caps is not None],
            y=[r.caps for r in rows if r.age is not None and r.caps is not None],
            mode="markers",
            marker={
                "size": 8,
                "color": [_confed_color(r.nation_confed) for r in rows if r.age is not None and r.caps is not None],
                "opacity": 0.7,
            },
            text=[f"{r.name} ({r.nation})" for r in rows if r.age is not None and r.caps is not None],
            hovertemplate="%{text}<br>age %{x} · %{y} caps<extra></extra>",
        )
    )
    fig_caps.update_layout(
        title=f"{tournament} — international caps vs age",
        template="plotly_dark",
        paper_bgcolor=DASH_BG,
        plot_bgcolor=PLOT_BG,
        font={"color": TEXT},
        height=420,
        margin={"l": 48, "r": 24, "t": 56, "b": 48},
        xaxis={"title": "Age", "gridcolor": GRID},
        yaxis={"title": "Caps", "gridcolor": GRID, "type": "log"},
    )
    extras.append(("Caps vs age", fig_caps))

    # Flight distance histogram.
    distances = [r.distance_km for r in rows if r.distance_km is not None]
    fig_dist = go.Figure(
        go.Histogram(
            x=distances,
            nbinsx=30,
            marker={"color": "#64748b"},
            hovertemplate="%{x} km<br>%{y} players<extra></extra>",
        )
    )
    fig_dist.update_layout(
        title=f"{tournament} — capital-to-club distance",
        template="plotly_dark",
        paper_bgcolor=DASH_BG,
        plot_bgcolor=PLOT_BG,
        font={"color": TEXT},
        height=380,
        margin={"l": 48, "r": 24, "t": 56, "b": 48},
        xaxis={"title": "Great-circle distance (km)", "gridcolor": GRID},
        yaxis={"title": "Players", "gridcolor": GRID},
    )
    extras.append(("Flight distances", fig_dist))

    return extras
