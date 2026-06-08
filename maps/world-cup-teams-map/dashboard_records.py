"""Records, leaders, and position breakdown charts for the squad dashboard."""

from __future__ import annotations

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from dashboard_data import (
    DASH_BG,
    GRID,
    MUTED,
    NationCapsSummary,
    PLOT_BG,
    POS_COLORS,
    POS_ORDER,
    TEXT,
    PlayerRow,
    add_violin_box,
    confed_color,
    dark_layout,
    nation_caps_summaries,
    player_chart_label,
    position_summaries,
    top_players,
)


def _leaderboard_bar(
    fig: go.Figure,
    players: list[PlayerRow],
    metric: str,
    *,
    row: int,
    col: int,
    color_key,
) -> None:
    ordered = list(reversed(players))
    fig.add_trace(
        go.Bar(
            y=[player_chart_label(r) for r in ordered],
            x=[getattr(r, metric) or 0 for r in ordered],
            orientation="h",
            marker={"color": [color_key(r) for r in ordered], "line": {"width": 0}},
            text=[str(getattr(r, metric) or 0) for r in ordered],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{y}<br>%{x} " + metric + "<br>%{customdata}<extra></extra>",
            customdata=[f"{r.pos} · age {r.age} · {r.club}" for r in ordered],
        ),
        row=row,
        col=col,
    )


def build_records_panel(tournament: str, rows: list[PlayerRow]) -> go.Figure:
    """Top scorers/caps, position breakdowns, and per-position leaders."""
    scorers = top_players(rows, "goals", limit=15)
    cap_leaders = top_players(rows, "caps", limit=15)
    pos_stats = position_summaries(rows)
    pos_active = [p.pos for p in pos_stats]

    fig = make_subplots(
        rows=3,
        cols=2,
        row_heights=[0.34, 0.33, 0.33],
        specs=[
            [{"type": "bar"}, {"type": "bar"}],
            [{"type": "xy"}, {"type": "xy"}],
            [{"type": "bar"}, {"type": "table"}],
        ],
        subplot_titles=(
            "Top international goal scorers",
            "Most international caps",
            "Age by position (violin + box)",
            "Caps by position (violin + box)",
            "Total international goals by position",
            "Position summary (avg age, caps, leading players)",
        ),
        vertical_spacing=0.1,
        horizontal_spacing=0.1,
    )

    _leaderboard_bar(
        fig, scorers, "goals", row=1, col=1,
        color_key=lambda r: POS_COLORS.get(r.pos, "#64748b"),
    )
    _leaderboard_bar(
        fig, cap_leaders, "caps", row=1, col=2,
        color_key=lambda r: POS_COLORS.get(r.pos, "#64748b"),
    )

    add_violin_box(
        fig, rows,
        category_key=lambda r: r.pos, categories=pos_active, y_key=lambda r: r.age,
        colors=POS_COLORS, row=2, col=1, y_title="Age",
    )
    add_violin_box(
        fig, rows,
        category_key=lambda r: r.pos, categories=pos_active, y_key=lambda r: r.caps,
        colors=POS_COLORS, row=2, col=2, y_title="Caps",
    )

    fig.add_trace(
        go.Bar(
            x=[p.pos for p in pos_stats],
            y=[p.total_goals for p in pos_stats],
            marker={"color": [POS_COLORS[p.pos] for p in pos_stats]},
            text=[str(p.total_goals) for p in pos_stats],
            textposition="outside",
            hovertemplate=(
                "%{x}<br>%{y} total goals<br>"
                "top: %{customdata}<extra></extra>"
            ),
            customdata=[f"{p.top_scorer} ({p.top_scorer_goals})" for p in pos_stats],
        ),
        row=3,
        col=1,
    )

    summary_rows = [
        (
            p.pos,
            str(p.count),
            f"{p.avg_age:.1f}" if p.avg_age is not None else "—",
            f"{p.avg_caps:.0f}" if p.avg_caps is not None else "—",
            str(p.total_goals),
            f"{p.top_scorer} ({p.top_scorer_goals})",
            f"{p.most_caps} ({p.most_caps_value})",
        )
        for p in pos_stats
    ]
    fig.add_trace(
        go.Table(
            header={
                "values": ["Pos", "Players", "Avg age", "Avg caps", "Total goals", "Top scorer", "Most caps"],
                "fill_color": PLOT_BG,
                "font": {"color": TEXT, "size": 11},
                "align": "left",
            },
            cells={
                "values": list(zip(*summary_rows, strict=True)) if summary_rows else [["—"] * 7],
                "fill_color": DASH_BG,
                "font": {"color": TEXT, "size": 11},
                "align": "left",
                "height": 28,
            },
        ),
        row=3,
        col=2,
    )

    top_g = scorers[0] if scorers else None
    top_c = cap_leaders[0] if cap_leaders else None
    subtitle = ""
    if top_g and top_c:
        subtitle = (
            f" · top scorer <b>{top_g.name}</b> ({top_g.goals} goals)"
            f" · most caps <b>{top_c.name}</b> ({top_c.caps})"
        )

    dark_layout(
        fig,
        f"{tournament} — records & position breakdown{subtitle}",
        height=1180,
        showlegend=False,
    )
    fig.update_xaxes(title_text="International goals", row=1, col=1, gridcolor=GRID)
    fig.update_xaxes(title_text="International caps", row=1, col=2, gridcolor=GRID)
    fig.update_yaxes(automargin=True, row=1, col=1)
    fig.update_yaxes(automargin=True, row=1, col=2)
    fig.update_yaxes(title_text="Age", range=[16, 44], row=2, col=1)
    fig.update_yaxes(title_text="Caps", row=2, col=2)
    fig.update_xaxes(title_text="Position", row=3, col=1, gridcolor=GRID)
    fig.update_yaxes(title_text="Total goals in squads", row=3, col=1, gridcolor=GRID)

    for ann in fig.layout.annotations:
        if ann.text:
            ann.font = {"size": 12, "color": TEXT}
            ann.xanchor = "left"
            ann.x = 0.01

    return fig


def build_goals_caps_panel(tournament: str, rows: list[PlayerRow]) -> go.Figure:
    """Goals vs caps scatter and average age/caps bars by position."""
    pos_stats = position_summaries(rows)
    scatter = [r for r in rows if r.caps is not None and r.goals is not None]

    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=(
            "International goals vs caps (colour = position, size ≈ age)",
            "Average age & caps by position",
        ),
        horizontal_spacing=0.1,
        specs=[[{"type": "xy"}, {"type": "xy"}]],
    )

    for pos in POS_ORDER:
        group = [r for r in scatter if r.pos == pos]
        if not group:
            continue
        fig.add_trace(
            go.Scatter(
                x=[r.caps for r in group],
                y=[r.goals for r in group],
                mode="markers",
                name=pos,
                marker={
                    "size": [8 + (r.age or 20) * 0.15 for r in group],
                    "color": POS_COLORS[pos],
                    "opacity": 0.78,
                    "line": {"width": 0.5, "color": "#0f172a"},
                },
                text=[player_chart_label(r) for r in group],
                customdata=[[r.age, r.club] for r in group],
                hovertemplate=(
                    "%{text}<br>%{y} goals · %{x} caps · age %{customdata[0]}"
                    "<br>%{customdata[1]}<extra></extra>"
                ),
            ),
            row=1,
            col=1,
        )

    fig.add_trace(
        go.Bar(
            x=[p.pos for p in pos_stats],
            y=[p.avg_age or 0 for p in pos_stats],
            name="Avg age",
            marker={"color": "#38bdf8"},
            text=[f"{p.avg_age:.1f}" if p.avg_age else "—" for p in pos_stats],
            textposition="outside",
            offsetgroup="age",
        ),
        row=1,
        col=2,
    )
    fig.add_trace(
        go.Bar(
            x=[p.pos for p in pos_stats],
            y=[p.avg_caps or 0 for p in pos_stats],
            name="Avg caps",
            marker={"color": "#a78bfa"},
            text=[f"{p.avg_caps:.0f}" if p.avg_caps else "—" for p in pos_stats],
            textposition="outside",
            offsetgroup="caps",
        ),
        row=1,
        col=2,
    )

    dark_layout(fig, f"{tournament} — goals, caps & position averages", height=460, showlegend=True)
    fig.update_xaxes(title_text="Caps", row=1, col=1)
    fig.update_yaxes(title_text="Goals", row=1, col=1)
    fig.update_xaxes(title_text="Position", row=1, col=2)
    fig.update_yaxes(title_text="Average", row=1, col=2)
    fig.update_layout(legend={"orientation": "h", "y": 1.12, "x": 0}, barmode="group")
    return fig


def _nation_experience_bar(
    fig: go.Figure,
    nations: list[NationCapsSummary],
    *,
    row: int,
    col: int,
) -> None:
    ordered = list(reversed(nations))
    fig.add_trace(
        go.Bar(
            y=[n.nation for n in ordered],
            x=[n.avg_caps for n in ordered],
            orientation="h",
            marker={"color": [confed_color(n.nation_confed) for n in ordered], "line": {"width": 0}},
            text=[f"{n.avg_caps:.1f}" for n in ordered],
            textposition="outside",
            cliponaxis=False,
            hovertemplate=(
                "%{y}<br>"
                "avg %{x:.1f} caps · median %{customdata[0]:.0f}<br>"
                "total %{customdata[1]:,} · most capped: %{customdata[2]} (%{customdata[3]})"
                "<extra></extra>"
            ),
            customdata=[
                (n.median_caps, n.total_caps, n.most_capped, n.most_capped_value) for n in ordered
            ],
            showlegend=False,
        ),
        row=row,
        col=col,
    )


def build_nation_experience_panel(
    tournament: str,
    rows: list[PlayerRow],
    *,
    limit: int = 10,
) -> go.Figure:
    """Top and bottom nations by average squad caps (international experience)."""
    summaries = nation_caps_summaries(rows)
    if not summaries:
        fig = go.Figure()
        dark_layout(fig, f"{tournament} — squad experience by nation", height=420)
        return fig

    n = min(limit, len(summaries))
    most = summaries[:n]
    least = list(reversed(summaries[-n:]))

    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=(
            f"Most experienced squads (top {n} by avg caps)",
            f"Least experienced squads (bottom {n} by avg caps)",
        ),
        horizontal_spacing=0.12,
        specs=[[{"type": "bar"}, {"type": "bar"}]],
    )

    _nation_experience_bar(fig, most, row=1, col=1)
    _nation_experience_bar(fig, least, row=1, col=2)

    top = most[0]
    bottom = least[0]
    subtitle = (
        f" · highest <b>{top.nation}</b> ({top.avg_caps:.1f} avg)"
        f" · lowest <b>{bottom.nation}</b> ({bottom.avg_caps:.1f} avg)"
    )
    dark_layout(
        fig,
        f"{tournament} — squad experience by nation{subtitle}",
        height=max(420, 36 * n + 120),
        showlegend=False,
    )
    fig.update_xaxes(title_text="Average caps per player", row=1, col=1, gridcolor=GRID)
    fig.update_xaxes(title_text="Average caps per player", row=1, col=2, gridcolor=GRID)
    fig.update_yaxes(automargin=True, row=1, col=1)
    fig.update_yaxes(automargin=True, row=1, col=2)

    for ann in fig.layout.annotations:
        if ann.text:
            ann.font = {"size": 12, "color": TEXT}
            ann.xanchor = "left"
            ann.x = 0.01

    return fig
