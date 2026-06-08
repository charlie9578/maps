"""Plotly dashboard for World Cup squad statistics."""

from __future__ import annotations

import statistics
from collections import Counter

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
    band_color,
    build_player_rows,
    club_country_counts,
    confed_color,
    dark_layout,
    style_subplot_titles,
    youngest_oldest,
)
from dashboard_captains import build_captains_panel
from dashboard_records import (
    build_goals_caps_scatter,
    build_nation_experience_panel,
    build_records_panel,
)
from data_processing import Team
from viz import DEFAULT_COLOR

PLOT_BG = "#1e293b"


def build_dashboard(
    tournament: str,
    teams: list[Team],
    clubs: dict[str, dict],
    *,
    source_accessed: str = "2026-06-05",
) -> go.Figure:
    rows = build_player_rows(teams, clubs)
    club_counts = Counter(r.club for r in rows)
    pos_counts = Counter(r.pos for r in rows if r.pos in POS_ORDER)

    fig = make_subplots(
        rows=2,
        cols=2,
        column_widths=[0.58, 0.42],
        row_heights=[0.40, 0.60],
        specs=[
            [{"type": "bar"}, {"type": "pie"}],
            [{"type": "sankey", "colspan": 2}, None],
        ],
        subplot_titles=(
            "Clubs supplying the most players",
            "Squad by position",
            "Where squads play: national → club confederation",
            "",
        ),
        horizontal_spacing=0.12,
        vertical_spacing=0.10,
    )

    top_clubs = club_counts.most_common(18)
    top_club_countries = [
        clubs.get(club, {}).get("country", "Unknown") for club, _count in reversed(top_clubs)
    ]
    club_vals = [n for _, n in reversed(top_clubs)]
    max_club = max(club_vals) if club_vals else 1
    fig.add_trace(
        go.Bar(
            y=[c for c, _ in reversed(top_clubs)],
            x=club_vals,
            orientation="h",
            marker={
                "color": club_vals,
                "colorscale": [[0, "#334155"], [0.5, "#64748b"], [1, "#38bdf8"]],
                "cmin": 0,
                "cmax": max_club,
                "line": {"width": 0},
            },
            text=club_vals,
            textposition="outside",
            cliponaxis=False,
            customdata=[
                [country, 100 * value / max(1, len(rows))]
                for country, value in zip(top_club_countries, club_vals, strict=True)
            ],
            hovertemplate="%{y}<br>%{x} players · %{customdata[1]:.1f}% of all squads"
            "<br>%{customdata[0]}<extra></extra>",
        ),
        row=1,
        col=1,
    )

    pos_labels = [p for p in POS_ORDER if pos_counts[p]]
    pos_values = [pos_counts[p] for p in pos_labels]
    fig.add_trace(
        go.Pie(
            labels=pos_labels,
            values=pos_values,
            marker={"colors": [POS_COLORS[p] for p in pos_labels]},
            hole=0.48,
            sort=False,
            textinfo="label+value",
            textfont={"size": 12},
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
    node_labels = [f"{c} · nat." for c in left_nodes] + [f"{c} · club" for c in right_nodes]
    node_colors = [confed_color(c) for c in left_nodes] + [confed_color(c) for c in right_nodes]
    left_idx = {c: i for i, c in enumerate(left_nodes)}
    right_idx = {c: i + len(left_nodes) for i, c in enumerate(right_nodes)}
    sources, targets, values, link_colors = [], [], [], []
    for (src, tgt), val in sorted(flow.items(), key=lambda x: -x[1]):
        if src in left_idx and tgt in right_idx:
            sources.append(left_idx[src])
            targets.append(right_idx[tgt])
            values.append(val)
            hex_c = confed_color(src)
            r, g, b = int(hex_c[1:3], 16), int(hex_c[3:5], 16), int(hex_c[5:7], 16)
            link_colors.append(f"rgba({r},{g},{b},0.42)")

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
                "color": link_colors,
                "hovertemplate": "%{source.label} → %{target.label}<br>%{value} players<extra></extra>",
            },
            textfont={"color": TEXT, "size": 12},
        ),
        row=2,
        col=1,
    )

    _ = source_accessed  # cited in page footer
    abroad_n = sum(1 for r in rows if not r.domestic)
    abroad_pct = round(100 * abroad_n / max(1, len(rows)))
    dark_layout(
        fig,
        f"{tournament} — squad overview · {abroad_pct}% play outside their home federation",
        height=860,
        showlegend=False,
    )
    fig.update_xaxes(title_text="Players", row=1, col=1, gridcolor=GRID, zeroline=False)
    fig.update_yaxes(row=1, col=1, gridcolor=GRID, automargin=True)

    style_subplot_titles(fig, font_size=12)

    if pos_values:
        pie_trace = next((t for t in fig.data if t.type == "pie"), None)
        if pie_trace is not None and pie_trace.domain is not None:
            x0, x1 = pie_trace.domain.x
            y0, y1 = pie_trace.domain.y
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        else:
            cx, cy = 0.815, 0.82
        fig.add_annotation(
            text=f"<b>{sum(pos_values):,}</b><br>players",
            x=cx,
            y=cy,
            xref="paper",
            yref="paper",
            showarrow=False,
            font={"size": 14, "color": TEXT},
            xanchor="center",
            yanchor="middle",
        )

    return fig


def build_age_by_confed_panel(tournament: str, rows: list[PlayerRow]) -> go.Figure:
    """Age distribution by national confederation."""
    confeds = active_confeds(rows)
    fig = make_subplots(rows=1, cols=1)
    add_violin_box(
        fig,
        rows,
        category_key=lambda r: r.nation_confed,
        categories=confeds,
        y_key=lambda r: r.age,
        colors={c: confed_color(c) for c in confeds},
        row=1,
        col=1,
        y_title="Age (years)",
    )
    dark_layout(fig, f"{tournament} — age by confederation", height=400, showlegend=False)
    fig.update_yaxes(range=[16, 44], gridcolor=GRID)
    return fig


def build_age_bands_panel(tournament: str, rows: list[PlayerRow]) -> go.Figure:
    """Age-band composition by national confederation (100% stacked bars)."""
    confeds = active_confeds(rows)
    fig = go.Figure()

    band_confed: dict[str, dict[str, int]] = {c: {b: 0 for b in AGE_BAND_LABELS} for c in confeds}
    for r in rows:
        band = age_band(r.age)
        if band and r.nation_confed in band_confed:
            band_confed[r.nation_confed][band] += 1

    for i, band in enumerate(AGE_BAND_LABELS):
        pct = [
            100 * band_confed[c][band] / max(1, sum(band_confed[c].values()))
            for c in confeds
        ]
        counts = [band_confed[c][band] for c in confeds]
        fig.add_trace(
            go.Bar(
                x=confeds,
                y=pct,
                name=band,
                marker={"color": band_color(i, alpha=0.88)},
                hovertemplate=f"{band}<br>%{{x}}<br>%{{y:.0f}}% (%{{customdata}} players)<extra></extra>",
                customdata=counts,
            ),
        )

    dark_layout(
        fig,
        f"{tournament} — age bands by confederation",
        height=420,
        showlegend=True,
        legend_below=True,
    )
    fig.update_layout(barmode="stack")
    fig.update_yaxes(title_text="Share of squad (%)", range=[0, 100])
    fig.update_xaxes(title_text="National confederation")
    fig.update_layout(legend_title_text="Age band")
    return fig


def build_caps_by_confed_panel(tournament: str, rows: list[PlayerRow]) -> go.Figure:
    """International caps spread by national confederation."""
    confeds = active_confeds(rows)
    fig = go.Figure()
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
        )
    dark_layout(fig, f"{tournament} — caps by confederation", height=400, showlegend=False)
    fig.update_yaxes(title_text="International caps")
    return fig


def build_club_countries_treemap(tournament: str, rows: list[PlayerRow]) -> go.Figure:
    """Treemap of players by club host country."""
    country_counts = club_country_counts(rows)
    top_countries = country_counts.most_common(25)
    other = sum(country_counts.values()) - sum(n for _, n in top_countries)

    labels = ["All players"] + [c for c, _ in top_countries]
    parents = [""] + ["All players"] * len(top_countries)
    values = [sum(country_counts.values())] + [n for _, n in top_countries]
    colors = [MUTED] + [confed_color(club_confederation(c)) for c, _ in top_countries]
    if other > 0:
        labels.append("Other countries")
        parents.append("All players")
        values.append(other)
        colors.append(DEFAULT_COLOR)

    fig = go.Figure(
        go.Treemap(
            labels=labels,
            parents=parents,
            values=values,
            marker={"colors": colors, "line": {"width": 1, "color": PLOT_BG}},
            branchvalues="total",
            texttemplate="<b>%{label}</b><br>%{value} players<br>%{percentRoot:.1%}",
            textfont={"size": 13},
            hovertemplate="%{label}<br>%{value} players (%{percentRoot:.1%} of total)<extra></extra>",
        )
    )
    dark_layout(fig, f"{tournament} — club host countries (top 25 plus other)", height=540)
    return fig


def build_abroad_by_confed_panel(tournament: str, rows: list[PlayerRow]) -> go.Figure:
    """Domestic vs abroad players within each national confederation."""
    confeds = active_confeds(rows)
    domestic_counts = []
    abroad_counts = []
    domestic_pct = []
    abroad_pct = []
    for confed in confeds:
        group = [r for r in rows if r.nation_confed == confed]
        domestic = sum(1 for r in group if r.domestic)
        abroad = sum(1 for r in group if not r.domestic)
        total = max(1, domestic + abroad)
        domestic_counts.append(domestic)
        abroad_counts.append(abroad)
        domestic_pct.append(100 * domestic / total)
        abroad_pct.append(100 * abroad / total)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=confeds,
            y=domestic_pct,
            name="Domestic",
            marker={"color": "#34d399"},
            text=[f"{v:.0f}%" if v >= 12 else "" for v in domestic_pct],
            textposition="inside",
            customdata=domestic_counts,
            hovertemplate="%{x}<br>Domestic: %{customdata} players (%{y:.0f}%)<extra></extra>",
        ),
    )
    fig.add_trace(
        go.Bar(
            x=confeds,
            y=abroad_pct,
            name="Abroad",
            marker={"color": "#38bdf8"},
            text=[f"{v:.0f}%" if v >= 12 else "" for v in abroad_pct],
            textposition="inside",
            customdata=abroad_counts,
            hovertemplate="%{x}<br>Abroad: %{customdata} players (%{y:.0f}%)<extra></extra>",
        ),
    )
    dark_layout(
        fig,
        f"{tournament} — domestic vs abroad",
        height=400,
        showlegend=True,
        legend_below=True,
    )
    fig.update_layout(barmode="stack")
    fig.update_yaxes(title_text="Share of players", ticksuffix="%", range=[0, 100])
    fig.update_xaxes(title_text="National confederation")
    return fig


def build_geography_panel(tournament: str, rows: list[PlayerRow]) -> go.Figure:
    """Capital-to-club distance by confederation and cumulative distance curve."""
    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=(
            "Capital-to-club distance by confederation",
            "Cumulative share by flight distance",
        ),
        horizontal_spacing=0.12,
    )

    confeds = active_confeds(rows)
    add_violin_box(
        fig, rows,
        category_key=lambda r: r.nation_confed, categories=confeds, y_key=lambda r: r.distance_km,
        colors={c: confed_color(c) for c in confeds}, row=1, col=1, y_title="Distance (km)",
    )

    distances = sorted(r.distance_km for r in rows if r.distance_km is not None)
    if distances:
        median_dist = statistics.median(distances)
        p75_dist = distances[int(0.75 * (len(distances) - 1))]
        max_dist = distances[-1]
        n = len(distances)
        fig.add_trace(
            go.Scatter(
                x=distances,
                y=[100 * i / n for i in range(1, n + 1)],
                mode="lines",
                fill="tozeroy",
                line={"color": "#64748b", "width": 2},
                fillcolor="rgba(100, 116, 139, 0.35)",
                customdata=list(range(1, n + 1)),
                hovertemplate="≤ %{x:,.0f} km<br>%{customdata} players (%{y:.0f}%)<extra></extra>",
            ),
            row=1,
            col=2,
        )
        fig.add_vline(
            x=median_dist,
            line={"color": "#a78bfa", "width": 2, "dash": "dot"},
            annotation_text=f"Median {median_dist:,.0f} km",
            annotation_position="top left",
            annotation_font={"color": "#c4b5fd", "size": 11},
            row=1,
            col=2,
        )
        fig.add_vline(
            x=p75_dist,
            line={"color": "#38bdf8", "width": 1.5, "dash": "dash"},
            annotation_text=f"75th pct {p75_dist:,.0f} km",
            annotation_position="top right",
            annotation_font={"color": "#7dd3fc", "size": 11},
            row=1,
            col=2,
        )
        # Distances cannot be negative — clamp the violin/box axis to start at 0.
        fig.update_yaxes(range=[0, max_dist * 1.05], row=1, col=1)

    dark_layout(fig, f"{tournament} — flight distances", height=460, showlegend=False)
    style_subplot_titles(fig)
    fig.update_yaxes(title_text="Distance (km)", row=1, col=1)
    fig.update_xaxes(title_text="Distance (km)", row=1, col=2)
    fig.update_yaxes(title_text="Share of players (%)", range=[0, 100], row=1, col=2)
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
        ("Goals vs caps", build_goals_caps_scatter(tournament, rows)),
        ("Captains vs squad mates", build_captains_panel(tournament, rows)),
        ("Youngest, oldest & birthdays", build_age_milestones_panel(tournament, rows)),
        ("Age by confederation", build_age_by_confed_panel(tournament, rows)),
        ("Club host countries", build_club_countries_treemap(tournament, rows)),
        ("Geography", build_geography_panel(tournament, rows)),
    ]


def build_age_milestones_panel(tournament: str, rows: list[PlayerRow]) -> go.Figure:
    """Squad age histogram with median, min, and max markers."""
    youngest, oldest = youngest_oldest(rows, n=6)
    ages = [r.age for r in rows if r.age is not None]

    fig = go.Figure()

    if ages:
        median_age = statistics.median(ages)
        age_counts = Counter(ages)
        age_vals = sorted(age_counts)
        fig.add_trace(
            go.Bar(
                x=age_vals,
                y=[age_counts[a] for a in age_vals],
                marker={"color": "#64748b", "line": {"color": "#475569", "width": 0.5}},
                hovertemplate="age %{x}<br>%{y} players<extra></extra>",
            )
        )
        fig.add_vline(
            x=median_age,
            line={"color": "#a78bfa", "width": 2, "dash": "dot"},
            annotation_text=f"Median {median_age:.1f}",
            annotation_position="top right",
            annotation_font={"color": "#c4b5fd", "size": 11},
        )
        if youngest:
            fig.add_vline(
                x=youngest[0].age,
                line={"color": "#38bdf8", "width": 1.5, "dash": "dash"},
                annotation_text=f"Min {youngest[0].age}",
                annotation_position="top left",
                annotation_font={"color": "#7dd3fc", "size": 11},
            )
        if oldest:
            fig.add_vline(
                x=oldest[0].age,
                line={"color": "#fb7185", "width": 1.5, "dash": "dash"},
                annotation_text=f"Max {oldest[0].age}",
                annotation_position="bottom right",
                annotation_font={"color": "#fda4af", "size": 11},
            )

    dark_layout(
        fig,
        f"{tournament} — squad age profile",
        height=380,
        showlegend=False,
    )
    fig.update_xaxes(title_text="Age (years)", dtick=1)
    fig.update_yaxes(title_text="Players")
    return fig
