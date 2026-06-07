"""Plotly dashboard for World Cup squad statistics."""

from __future__ import annotations

import statistics
from collections import Counter, defaultdict

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from club_confed import club_confederation
from dashboard_data import (
    AGE_BAND_LABELS,
    CONFED_ORDER,
    DASH_BG,
    GRID,
    MUTED,
    PlayerRow,
    POS_COLORS,
    POS_ORDER,
    TEXT,
    WC_FINAL_DAY,
    WC_OPENING_DAY,
    active_confeds,
    add_violin_box,
    age_band,
    age_extremes,
    band_color,
    build_player_rows,
    club_country_counts,
    confed_color,
    dark_layout,
    format_dob,
    tournament_birthdays,
    top_players,
)
from dashboard_captains import build_captains_panel
from dashboard_records import build_goals_caps_panel, build_records_panel
from data_processing import Team
from viz import DEFAULT_COLOR

PLOT_BG = "#1e293b"


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
    country_counts = club_country_counts(rows)
    abroad_n = sum(1 for r in rows if not r.domestic)

    fig = make_subplots(
        rows=3,
        cols=2,
        column_widths=[0.58, 0.42],
        row_heights=[0.30, 0.38, 0.32],
        specs=[
            [{"type": "bar"}, {"type": "pie"}],
            [{"type": "sankey", "colspan": 2}, None],
            [{"type": "xy"}, {"type": "bar"}],
        ],
        subplot_titles=(
            "Clubs by World Cup players",
            "Squad by position",
            "Player flow: national confederation → club confederation",
            "",
            "Age distribution by national confederation (violin + box)",
            "Top club host countries",
        ),
        horizontal_spacing=0.08,
        vertical_spacing=0.09,
    )

    youngest, oldest = age_extremes(rows)
    yng = youngest[0] if youngest else None
    old = oldest[0] if oldest else None
    age_span = (
        f" · youngest <b>{yng.age}</b> ({yng.name}, {yng.nation})"
        f" · oldest <b>{old.age}</b> ({old.name}, {old.nation})"
        if yng and old
        else ""
    )

    top_scorers = top_players(rows, "goals", limit=1)
    top_caps = top_players(rows, "caps", limit=1)
    ts = top_scorers[0] if top_scorers else None
    tc = top_caps[0] if top_caps else None
    records_note = (
        f" · top scorer <b>{ts.name}</b> ({ts.goals} goals)"
        f" · most caps <b>{tc.name}</b> ({tc.caps})"
        if ts and tc
        else ""
    )

    kpi_line = (
        f"<b>{len(rows):,}</b> players · <b>{len(club_counts):,}</b> clubs · "
        f"<b>{statistics.mean(ages):.1f}</b> avg age · "
        f"<b>{100 * abroad_n / len(rows):.0f}%</b> abroad · "
        f"<b>{statistics.mean(caps_vals):.0f}</b> avg caps · "
        f"<b>{statistics.median(distances):,.0f} km</b> median flight distance"
        f"{age_span}{records_note}"
    )

    top_clubs = club_counts.most_common(25)
    fig.add_trace(
        go.Bar(
            y=[c for c, _ in reversed(top_clubs)],
            x=[n for _, n in reversed(top_clubs)],
            orientation="h",
            marker={"color": "#64748b", "line": {"width": 0}},
            hovertemplate="%{y}<br>%{x} players<extra></extra>",
        ),
        row=1,
        col=1,
    )

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

    flow: dict[tuple[str, str], int] = Counter()
    for r in rows:
        flow[(r.nation_confed, r.club_confed)] += 1
    left_nodes = [c for c in CONFED_ORDER if any(k[0] == c for k in flow)]
    right_nodes = [c for c in CONFED_ORDER if any(k[1] == c for k in flow)]
    node_labels = [f"{c} (national)" for c in left_nodes] + [f"{c} (club)" for c in right_nodes]
    node_colors = [confed_color(c) for c in left_nodes] + [confed_color(c) for c in right_nodes]
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

    confeds = active_confeds(rows)
    add_violin_box(
        fig,
        rows,
        category_key=lambda r: r.nation_confed,
        categories=confeds,
        y_key=lambda r: r.age,
        colors={c: confed_color(c) for c in confeds},
        row=3,
        col=1,
        y_title="Age (years)",
    )

    top_countries = country_counts.most_common(15)
    fig.add_trace(
        go.Bar(
            x=[c for c, _ in top_countries],
            y=[n for _, n in top_countries],
            marker={"color": [confed_color(club_confederation(c)) for c, _ in top_countries]},
            hovertemplate="%{x}<br>%{y} players<extra></extra>",
        ),
        row=3,
        col=2,
    )

    _base_layout(fig, tournament, source_accessed, kpi_line=kpi_line)
    fig.update_xaxes(title_text="Players", row=1, col=1, gridcolor=GRID, zeroline=False)
    fig.update_yaxes(row=1, col=1, gridcolor=GRID, automargin=True)
    fig.update_yaxes(title_text="Age (years)", row=3, col=1, gridcolor=GRID, range=[16, 44])
    fig.update_xaxes(tickangle=-35, row=3, col=2, gridcolor=GRID)
    fig.update_yaxes(title_text="Players", row=3, col=2, gridcolor=GRID)

    for ann in fig.layout.annotations:
        if ann.text:
            ann.font = {"size": 13, "color": TEXT}
            ann.xanchor = "left"
            ann.x = 0.01

    return fig


def build_age_experience_panel(tournament: str, rows: list[PlayerRow]) -> go.Figure:
    """Age-band composition and caps spread by national confederation."""
    confeds = active_confeds(rows)

    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=(
            "Age bands by national confederation (100% stacked area)",
            "International caps by confederation (box plot)",
        ),
        horizontal_spacing=0.08,
    )

    band_confed: dict[str, dict[str, int]] = {c: {b: 0 for b in AGE_BAND_LABELS} for c in confeds}
    for r in rows:
        band = age_band(r.age)
        if band and r.nation_confed in band_confed:
            band_confed[r.nation_confed][band] += 1

    y_bottom = [0.0] * len(confeds)
    for i, band in enumerate(AGE_BAND_LABELS):
        pct = [
            100 * band_confed[c][band] / max(1, sum(band_confed[c].values()))
            for c in confeds
        ]
        y_top = [y_bottom[j] + pct[j] for j in range(len(confeds))]
        fig.add_trace(
            go.Scatter(
                x=confeds,
                y=y_top,
                mode="lines",
                name=band,
                line={"width": 0.6, "color": band_color(i)},
                fill="tonexty" if i else "tozeroy",
                fillcolor=band_color(i, alpha=0.78),
                hovertemplate=f"{band}<br>%{{x}}<br>%{{customdata:.0f}}% of squad<extra></extra>",
                customdata=pct,
            ),
            row=1,
            col=1,
        )
        y_bottom = y_top

    for confed in confeds:
        caps = [r.caps for r in rows if r.nation_confed == confed and r.caps is not None]
        if not caps:
            continue
        color = confed_color(confed)
        fig.add_trace(
            go.Box(
                x=[confed] * len(caps),
                y=caps,
                marker={"color": color},
                line={"color": color},
                boxpoints="outliers",
                showlegend=False,
                hovertemplate=f"{confed}<br>%{{y}} caps<extra></extra>",
            ),
            row=1,
            col=2,
        )

    dark_layout(fig, f"{tournament} — age & caps by confederation", height=460, showlegend=True)
    fig.update_yaxes(title_text="Share of squad (%)", range=[0, 100], row=1, col=1)
    fig.update_yaxes(title_text="Caps", row=1, col=2)
    fig.update_layout(legend={"title": "Age band", "orientation": "h", "y": 1.12, "x": 0})
    return fig


def build_proportional_panel(tournament: str, rows: list[PlayerRow]) -> go.Figure:
    """Treemap and sunburst proportional-area charts."""
    country_counts = club_country_counts(rows)
    top_countries = country_counts.most_common(20)
    other = sum(country_counts.values()) - sum(n for _, n in top_countries)

    treemap_labels = ["All players"] + [c for c, _ in top_countries]
    treemap_parents = [""] + ["All players"] * len(top_countries)
    treemap_values = [sum(country_counts.values())] + [n for _, n in top_countries]
    treemap_colors = [MUTED] + [confed_color(club_confederation(c)) for c, _ in top_countries]
    if other > 0:
        treemap_labels.append("Other countries")
        treemap_parents.append("All players")
        treemap_values.append(other)
        treemap_colors.append(DEFAULT_COLOR)

    sun_ids = ["root"]
    sun_labels = ["Squads"]
    sun_parents: list[str | None] = [""]
    sun_values = [len(rows)]
    sun_colors = [MUTED]

    for confed in active_confeds(rows):
        confed_rows = [r for r in rows if r.nation_confed == confed]
        nat_id = f"nat-{confed}"
        sun_ids.append(nat_id)
        sun_labels.append(confed)
        sun_parents.append("root")
        sun_values.append(len(confed_rows))
        sun_colors.append(confed_color(confed))
        for club_conf in CONFED_ORDER:
            n = sum(1 for r in confed_rows if r.club_confed == club_conf)
            if n:
                sun_ids.append(f"{nat_id}-club-{club_conf}")
                sun_labels.append(club_conf)
                sun_parents.append(nat_id)
                sun_values.append(n)
                sun_colors.append(confed_color(club_conf))

    fig = make_subplots(
        rows=1,
        cols=2,
        specs=[[{"type": "treemap"}, {"type": "sunburst"}]],
        subplot_titles=(
            "Players by club host country (treemap)",
            "National → club confederation (sunburst)",
        ),
        horizontal_spacing=0.06,
    )

    fig.add_trace(
        go.Treemap(
            labels=treemap_labels,
            parents=treemap_parents,
            values=treemap_values,
            marker={"colors": treemap_colors, "line": {"width": 1, "color": PLOT_BG}},
            branchvalues="total",
            textinfo="label+value",
            hovertemplate="%{label}<br>%{value} players<extra></extra>",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Sunburst(
            ids=sun_ids,
            labels=sun_labels,
            parents=sun_parents,
            values=sun_values,
            marker={"colors": sun_colors, "line": {"width": 1, "color": PLOT_BG}},
            branchvalues="total",
            insidetextorientation="radial",
            hovertemplate="%{label}<br>%{value} players (%{percentParent:.1%} of parent)<extra></extra>",
        ),
        row=1,
        col=2,
    )

    dark_layout(fig, f"{tournament} — proportional area views", height=520)
    for ann in fig.layout.annotations:
        if ann.text:
            ann.font = {"size": 13, "color": TEXT}
    return fig


def build_geography_panel(tournament: str, rows: list[PlayerRow]) -> go.Figure:
    """Distance, abroad share, and cumulative flight-distance area."""
    fig = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=(
            "Capital-to-club distance (violin + box)",
            "Share playing abroad by nation",
            "Cumulative player count by distance (area)",
            "Domestic vs abroad split by confederation",
        ),
        vertical_spacing=0.14,
        horizontal_spacing=0.08,
    )

    confeds = active_confeds(rows)
    add_violin_box(
        fig, rows,
        category_key=lambda r: r.nation_confed, categories=confeds, y_key=lambda r: r.distance_km,
        colors={c: confed_color(c) for c in confeds}, row=1, col=1, y_title="Distance (km)",
    )

    abroad_pct: list[tuple[str, float, str]] = []
    by_nation: dict[str, list[PlayerRow]] = defaultdict(list)
    for r in rows:
        by_nation[r.nation].append(r)
    for nation, players in by_nation.items():
        abroad = sum(1 for p in players if not p.domestic)
        abroad_pct.append((nation, 100 * abroad / len(players), players[0].nation_confed))
    abroad_pct.sort(key=lambda x: x[1], reverse=True)

    fig.add_trace(
        go.Bar(
            x=[n for n, _, _ in abroad_pct],
            y=[p for _, p, _ in abroad_pct],
            marker={"color": [confed_color(c) for _, _, c in abroad_pct]},
            hovertemplate="%{x}<br>%{y:.0f}% abroad<extra></extra>",
        ),
        row=1,
        col=2,
    )

    distances = sorted(r.distance_km for r in rows if r.distance_km is not None)
    if distances:
        fig.add_trace(
            go.Scatter(
                x=distances,
                y=list(range(1, len(distances) + 1)),
                mode="lines",
                fill="tozeroy",
                line={"color": "#64748b", "width": 2},
                fillcolor="rgba(100, 116, 139, 0.35)",
                hovertemplate="≤ %{x:,.0f} km<br>%{y} players<extra></extra>",
            ),
            row=2,
            col=1,
        )

    confed_domestic: dict[str, tuple[int, int]] = {}
    for confed in confeds:
        subset = [r for r in rows if r.nation_confed == confed]
        dom = sum(1 for r in subset if r.domestic)
        confed_domestic[confed] = (dom, len(subset) - dom)

    fig.add_trace(
        go.Bar(
            x=list(confed_domestic.keys()),
            y=[v[0] for v in confed_domestic.values()],
            name="Domestic",
            marker={"color": "#34d399"},
            hovertemplate="%{x}<br>%{y} domestic<extra></extra>",
        ),
        row=2,
        col=2,
    )
    fig.add_trace(
        go.Bar(
            x=list(confed_domestic.keys()),
            y=[v[1] for v in confed_domestic.values()],
            name="Abroad",
            marker={"color": "#fb7185"},
            hovertemplate="%{x}<br>%{y} abroad<extra></extra>",
        ),
        row=2,
        col=2,
    )

    dark_layout(fig, f"{tournament} — geography & club location", height=820, showlegend=True)
    fig.update_yaxes(title_text="Distance (km)", row=1, col=1)
    fig.update_xaxes(tickangle=-45, row=1, col=2)
    fig.update_yaxes(title_text="% abroad", range=[0, 105], row=1, col=2)
    fig.update_xaxes(title_text="Distance (km)", row=2, col=1)
    fig.update_yaxes(title_text="Players (cumulative)", row=2, col=1)
    fig.update_yaxes(title_text="Players", row=2, col=2)
    fig.update_layout(barmode="stack", legend={"orientation": "h", "y": 1.04, "x": 0})
    return fig


def build_extra_figures(
    tournament: str,
    teams: list[Team],
    clubs: dict[str, dict],
) -> list[tuple[str, go.Figure]]:
    """Additional dashboard sections below the overview grid."""
    rows = build_player_rows(teams, clubs)
    return [
        ("Records & positions", build_records_panel(tournament, rows)),
        ("Goals & caps", build_goals_caps_panel(tournament, rows)),
        ("Captains vs squad mates", build_captains_panel(tournament, rows)),
        ("Youngest, oldest & birthdays", build_age_milestones_panel(tournament, rows)),
        ("Age by confederation", build_age_experience_panel(tournament, rows)),
        ("Proportional area", build_proportional_panel(tournament, rows)),
        ("Geography", build_geography_panel(tournament, rows)),
    ]


def build_age_milestones_panel(tournament: str, rows: list[PlayerRow]) -> go.Figure:
    """Youngest/oldest squads, tournament birthdays, and age-range chart."""
    youngest, oldest = age_extremes(rows)
    birthdays = tournament_birthdays(rows)
    ages = [r.age for r in rows if r.age is not None]

    fig = make_subplots(
        rows=2,
        cols=2,
        row_heights=[0.42, 0.58],
        specs=[
            [{"type": "xy"}, {"type": "table"}],
            [{"type": "xy", "colspan": 2}, None],
        ],
        subplot_titles=(
            "Squad age distribution",
            "Youngest & oldest (as of 11 Jun 2026)",
            "Birthdays by day during the tournament",
            "",
        ),
        vertical_spacing=0.12,
        horizontal_spacing=0.08,
    )

    if ages:
        fig.add_trace(
            go.Histogram(
                x=ages,
                nbinsx=20,
                marker={"color": "#64748b"},
                opacity=0.9,
                hovertemplate="age %{x}<br>%{y} players<extra></extra>",
            ),
            row=1,
            col=1,
        )
        if youngest:
            fig.add_vline(
                x=youngest[0].age,
                line={"color": "#38bdf8", "width": 2, "dash": "dash"},
                annotation_text=f"Youngest ({youngest[0].age})",
                annotation_position="top left",
                row=1,
                col=1,
            )
        if oldest:
            fig.add_vline(
                x=oldest[0].age,
                line={"color": "#fb7185", "width": 2, "dash": "dash"},
                annotation_text=f"Oldest ({oldest[0].age})",
                annotation_position="top right",
                row=1,
                col=1,
            )

    extreme_rows = [
        (
            "Youngest",
            p.name,
            p.nation,
            str(p.age) if p.age is not None else "—",
            format_dob(p.dob),
            p.pos,
            p.club,
        )
        for p in youngest
    ] + [
        (
            "Oldest",
            p.name,
            p.nation,
            str(p.age) if p.age is not None else "—",
            format_dob(p.dob),
            p.pos,
            p.club,
        )
        for p in oldest
    ]
    fig.add_trace(
        go.Table(
            header={
                "values": ["", "Player", "Nation", "Age", "Born", "Pos", "Club"],
                "fill_color": PLOT_BG,
                "font": {"color": TEXT, "size": 12},
                "align": "left",
            },
            cells={
                "values": list(zip(*extreme_rows, strict=True)) if extreme_rows else [["—"] * 7],
                "fill_color": DASH_BG,
                "font": {"color": TEXT, "size": 11},
                "align": "left",
                "height": 28,
            },
        ),
        row=1,
        col=2,
    )

    if birthdays:
        by_day = Counter(b.birthday for b in birthdays)
        day_order = sorted(by_day.items())
        fig.add_trace(
            go.Scatter(
                x=[d.strftime("%d %b") for d, _ in day_order],
                y=[n for _, n in day_order],
                mode="lines+markers",
                fill="tozeroy",
                line={"color": "#a78bfa", "width": 2},
                marker={"size": 8, "color": "#a78bfa"},
                fillcolor="rgba(167, 139, 250, 0.35)",
                hovertemplate="%{x}<br>%{y} player(s)<extra></extra>",
            ),
            row=2,
            col=1,
        )
    else:
        fig.add_annotation(
            text="No player birthdays fall between 11 Jun and 19 Jul 2026.",
            showarrow=False,
            font={"color": MUTED, "size": 13},
            xref="x domain",
            yref="y domain",
            x=0.5,
            y=0.5,
            row=2,
            col=1,
        )

    dark_layout(
        fig,
        f"{tournament} — youngest, oldest & tournament birthdays "
        f"({len(birthdays)} during 11 Jun – 19 Jul 2026)",
        height=680,
        showlegend=False,
    )
    fig.update_xaxes(title_text="Age (years)", row=1, col=1)
    fig.update_yaxes(title_text="Players", row=1, col=1)
    if birthdays:
        fig.update_xaxes(title_text="Date", tickangle=-35, row=2, col=1)
        fig.update_yaxes(title_text="Players with a birthday", row=2, col=1)

    for ann in fig.layout.annotations:
        if ann.text and ("Birthdays" in ann.text or "Squad age" in ann.text or "Youngest" in ann.text):
            ann.font = {"size": 13, "color": TEXT}
            ann.xanchor = "left"
            ann.x = 0.01
    return fig
