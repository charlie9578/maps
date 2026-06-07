"""Captain vs squad-mate comparison charts."""

from __future__ import annotations

import statistics

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from dashboard_data import (
    CAPTAIN_LABEL,
    DASH_BG,
    GRID,
    MATE_LABEL,
    PLOT_BG,
    POS_COLORS,
    POS_ORDER,
    TEXT,
    PlayerRow,
    add_violin_box,
    captain_group,
    captain_profiles,
    dark_layout,
)


def _group_avg(rows: list[PlayerRow], key) -> float | None:
    vals = [key(r) for r in rows if key(r) is not None]
    return statistics.mean(vals) if vals else None


def _position_pcts(rows: list[PlayerRow]) -> dict[str, float]:
    counts = {p: sum(1 for r in rows if r.pos == p) for p in POS_ORDER}
    total = sum(counts.values()) or 1
    return {p: 100 * counts[p] / total for p in POS_ORDER}


def build_captains_panel(tournament: str, rows: list[PlayerRow]) -> go.Figure:
    """Compare captains with the rest of each squad."""
    captains = [r for r in rows if r.is_captain]
    mates = [r for r in rows if not r.is_captain]
    profiles = captain_profiles(rows)
    groups = [CAPTAIN_LABEL, MATE_LABEL]

    cap_avg_age = _group_avg(captains, lambda r: r.age)
    mate_avg_age = _group_avg(mates, lambda r: r.age)
    cap_avg_caps = _group_avg(captains, lambda r: r.caps)
    mate_avg_caps = _group_avg(mates, lambda r: r.caps)
    cap_avg_goals = statistics.mean([r.goals or 0 for r in captains]) if captains else None
    mate_avg_goals = statistics.mean([r.goals or 0 for r in mates]) if mates else None
    cap_abroad = 100 * sum(1 for r in captains if not r.domestic) / len(captains) if captains else 0
    mate_abroad = 100 * sum(1 for r in mates if not r.domestic) / len(mates) if mates else 0
    most_capped_n = sum(1 for p in profiles if p.most_capped_on_team)

    cap_pos = _position_pcts(captains)
    mate_pos = _position_pcts(mates)

    fig = make_subplots(
        rows=3,
        cols=2,
        row_heights=[0.28, 0.36, 0.36],
        specs=[
            [{"type": "bar"}, {"type": "bar"}],
            [{"type": "xy"}, {"type": "xy"}],
            [{"type": "bar"}, {"type": "bar"}],
        ],
        subplot_titles=(
            "Average age, caps & goals",
            "Share playing abroad",
            "Age: captains vs squad mates",
            "Caps: captains vs squad mates",
            "Position mix (% of group)",
            "Captain age vs squad average (by nation)",
        ),
        vertical_spacing=0.11,
        horizontal_spacing=0.1,
    )

    metrics = ["Avg age", "Avg caps", "Avg goals"]
    fig.add_trace(
        go.Bar(
            name=CAPTAIN_LABEL,
            x=metrics,
            y=[cap_avg_age or 0, cap_avg_caps or 0, cap_avg_goals or 0],
            marker={"color": "#fbbf24"},
            text=[
                f"{cap_avg_age:.1f}" if cap_avg_age else "—",
                f"{cap_avg_caps:.0f}" if cap_avg_caps else "—",
                f"{cap_avg_goals:.1f}" if cap_avg_goals else "—",
            ],
            textposition="outside",
            hovertemplate="Captains<br>%{x}: %{y:.1f}<extra></extra>",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Bar(
            name=MATE_LABEL,
            x=metrics,
            y=[mate_avg_age or 0, mate_avg_caps or 0, mate_avg_goals or 0],
            marker={"color": "#64748b"},
            text=[
                f"{mate_avg_age:.1f}" if mate_avg_age else "—",
                f"{mate_avg_caps:.0f}" if mate_avg_caps else "—",
                f"{mate_avg_goals:.1f}" if mate_avg_goals else "—",
            ],
            textposition="outside",
            hovertemplate="Squad mates<br>%{x}: %{y:.1f}<extra></extra>",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Bar(
            x=[CAPTAIN_LABEL, MATE_LABEL],
            y=[cap_abroad, mate_abroad],
            marker={"color": ["#fbbf24", "#64748b"]},
            text=[f"{cap_abroad:.0f}%", f"{mate_abroad:.0f}%"],
            textposition="outside",
            hovertemplate="%{x}<br>%{y:.0f}% abroad<extra></extra>",
            showlegend=False,
        ),
        row=1,
        col=2,
    )

    add_violin_box(
        fig,
        rows,
        category_key=captain_group,
        categories=groups,
        y_key=lambda r: r.age,
        colors={CAPTAIN_LABEL: "#fbbf24", MATE_LABEL: "#64748b"},
        row=2,
        col=1,
        y_title="Age",
    )
    add_violin_box(
        fig,
        rows,
        category_key=captain_group,
        categories=groups,
        y_key=lambda r: r.caps,
        colors={CAPTAIN_LABEL: "#fbbf24", MATE_LABEL: "#64748b"},
        row=2,
        col=2,
        y_title="Caps",
    )

    for pos in POS_ORDER:
        fig.add_trace(
            go.Bar(
                name=pos,
                x=[CAPTAIN_LABEL, MATE_LABEL],
                y=[cap_pos[pos], mate_pos[pos]],
                marker={"color": POS_COLORS[pos]},
                legendgroup=pos,
                showlegend=True,
                hovertemplate=f"{pos}<br>%{{x}}: %{{y:.0f}}%<extra></extra>",
            ),
            row=3,
            col=1,
        )

    delta_sorted = sorted(
        [p for p in profiles if p.age_vs_squad is not None],
        key=lambda p: p.age_vs_squad or 0,
        reverse=True,
    )
    fig.add_trace(
        go.Bar(
            y=[p.nation for p in reversed(delta_sorted)],
            x=[p.age_vs_squad or 0 for p in reversed(delta_sorted)],
            orientation="h",
            marker={
                "color": [
                    "#34d399" if (p.age_vs_squad or 0) >= 0 else "#fb7185"
                    for p in reversed(delta_sorted)
                ]
            },
            text=[f"{p.name} ({p.age_vs_squad:+.1f})" for p in reversed(delta_sorted)],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{y}<br>%{text} years vs squad avg<extra></extra>",
            showlegend=False,
        ),
        row=3,
        col=2,
    )

    subtitle = (
        f" · {most_capped_n}/{len(profiles)} captains are their team's most-capped player"
        if profiles
        else ""
    )
    dark_layout(
        fig,
        f"{tournament} — captains vs squad mates{subtitle}",
        height=1080,
        showlegend=True,
    )
    fig.update_layout(barmode="group", legend={"orientation": "h", "y": 1.04, "x": 0})
    fig.update_yaxes(title_text="Average", row=1, col=1, gridcolor=GRID)
    fig.update_yaxes(title_text="% abroad", range=[0, max(cap_abroad, mate_abroad) + 15], row=1, col=2)
    fig.update_yaxes(title_text="Age", range=[16, 44], row=2, col=1)
    fig.update_yaxes(title_text="Caps", row=2, col=2)
    fig.update_yaxes(title_text="Share of group (%)", row=3, col=1)
    fig.update_xaxes(title_text="Years older (+) or younger (−) than squad avg", row=3, col=2)
    fig.update_yaxes(automargin=True, row=3, col=2)

    for ann in fig.layout.annotations:
        if ann.text:
            ann.font = {"size": 12, "color": TEXT}
            ann.xanchor = "left"
            ann.x = 0.01

    return fig
