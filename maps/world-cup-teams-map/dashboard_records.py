"""Records, leaders, and position breakdown charts for the squad dashboard."""

from __future__ import annotations

import statistics

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
    style_subplot_titles,
)


def build_records_panel(tournament: str, rows: list[PlayerRow]) -> go.Figure:
    """Position breakdowns: age, caps, goals, and summary table."""
    pos_stats = position_summaries(rows)
    pos_active = [p.pos for p in pos_stats]

    fig = make_subplots(
        rows=2,
        cols=2,
        row_heights=[0.55, 0.45],
        specs=[
            [{"type": "xy"}, {"type": "xy"}],
            [{"type": "bar"}, {"type": "table"}],
        ],
        subplot_titles=(
            "Age by position",
            "Caps by position",
            "Total goals by position",
            "Position summary",
        ),
        vertical_spacing=0.14,
        horizontal_spacing=0.12,
    )

    add_violin_box(
        fig, rows,
        category_key=lambda r: r.pos, categories=pos_active, y_key=lambda r: r.age,
        colors=POS_COLORS, row=1, col=1, y_title="Age",
    )
    add_violin_box(
        fig, rows,
        category_key=lambda r: r.pos, categories=pos_active, y_key=lambda r: r.caps,
        colors=POS_COLORS, row=1, col=2, y_title="Caps",
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
        row=2,
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
        row=2,
        col=2,
    )

    dark_layout(
        fig,
        f"{tournament} — position breakdown",
        height=780,
        showlegend=False,
    )
    fig.update_yaxes(title_text="Age", range=[16, 44], row=1, col=1)
    fig.update_yaxes(title_text="Caps", row=1, col=2)
    fig.update_xaxes(title_text="Position", row=2, col=1, gridcolor=GRID)
    fig.update_yaxes(title_text="Total goals in squads", row=2, col=1, gridcolor=GRID)

    style_subplot_titles(fig)

    return fig


def build_goals_caps_scatter(tournament: str, rows: list[PlayerRow]) -> go.Figure:
    """Goals vs caps scatter — colour by position, marker size by age."""
    scatter = [r for r in rows if r.caps is not None and r.goals is not None]
    caps_vals = [r.caps for r in scatter]
    goals_vals = [r.goals for r in scatter]
    median_caps = statistics.median(caps_vals) if caps_vals else 0
    median_goals = statistics.median(goals_vals) if goals_vals else 0
    fig = go.Figure()

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
        )

    if caps_vals:
        fig.add_vline(
            x=median_caps,
            line={"color": "#475569", "width": 1, "dash": "dot"},
            annotation_text=f"Median caps ({median_caps:.0f})",
            annotation_position="top left",
        )
        fig.add_hline(
            y=median_goals,
            line={"color": "#475569", "width": 1, "dash": "dot"},
            annotation_text=f"Median goals ({median_goals:.0f})",
            annotation_position="bottom right",
        )

    dark_layout(
        fig,
        f"{tournament} — goals vs caps",
        height=480,
        showlegend=True,
        legend_below=True,
    )
    fig.update_xaxes(title_text="International caps")
    fig.update_yaxes(title_text="International goals")
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
            f"Most experienced (top {n})",
            f"Least experienced (bottom {n})",
        ),
        horizontal_spacing=0.14,
        specs=[[{"type": "bar"}, {"type": "bar"}]],
    )

    _nation_experience_bar(fig, most, row=1, col=1)
    _nation_experience_bar(fig, least, row=1, col=2)

    top = most[0]
    bottom = least[0]
    dark_layout(
        fig,
        f"{tournament} — squad experience ({top.nation} {top.avg_caps:.1f} avg · "
        f"{bottom.nation} {bottom.avg_caps:.1f} avg)",
        height=max(420, 36 * n + 120),
        showlegend=False,
    )
    fig.update_xaxes(title_text="Average caps per player", row=1, col=1, gridcolor=GRID)
    fig.update_xaxes(title_text="Average caps per player", row=1, col=2, gridcolor=GRID)
    fig.update_yaxes(automargin=True, row=1, col=1)
    fig.update_yaxes(automargin=True, row=1, col=2)

    style_subplot_titles(fig)

    return fig
