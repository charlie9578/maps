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
    TEXT,
    PlayerRow,
    add_violin_box,
    captain_group,
    captain_profiles,
    dark_layout,
    style_subplot_titles,
)


def _group_avg(rows: list[PlayerRow], key) -> float | None:
    vals = [key(r) for r in rows if key(r) is not None]
    return statistics.mean(vals) if vals else None


def _delta_bars(
    fig: go.Figure,
    profiles: list,
    *,
    value_attr: str,
    label: str,
    row: int,
    col: int,
    limit_each_side: int = 8,
) -> None:
    sorted_profiles = sorted(
        [p for p in profiles if getattr(p, value_attr) is not None],
        key=lambda p: getattr(p, value_attr) or 0,
        reverse=True,
    )
    if not sorted_profiles:
        return
    if len(sorted_profiles) > limit_each_side * 2:
        selected = sorted_profiles[:limit_each_side] + sorted_profiles[-limit_each_side:]
    else:
        selected = sorted_profiles
    ordered = list(reversed(selected))
    values = [getattr(p, value_attr) or 0 for p in ordered]
    fig.add_trace(
        go.Bar(
            y=[p.nation for p in ordered],
            x=values,
            orientation="h",
            marker={"color": ["#34d399" if v >= 0 else "#fb7185" for v in values]},
            text=[f"{p.name} ({v:+.0f})" if value_attr == "caps_vs_squad" else f"{p.name} ({v:+.1f})"
                  for p, v in zip(ordered, values, strict=True)],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{y}<br>%{text}<extra></extra>",
            showlegend=False,
        ),
        row=row,
        col=col,
    )
    fig.update_xaxes(title_text=label, row=row, col=col, gridcolor=GRID)
    fig.update_yaxes(automargin=True, row=row, col=col)


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

    fig = make_subplots(
        rows=3,
        cols=2,
        row_heights=[0.24, 0.38, 0.38],
        specs=[
            [{"type": "table"}, {"type": "bar"}],
            [{"type": "xy"}, {"type": "xy"}],
            [{"type": "bar"}, {"type": "bar"}],
        ],
        subplot_titles=(
            "Group averages",
            "% playing abroad",
            "Age distribution",
            "Caps distribution",
            "Largest captain age gaps",
            "Largest captain caps gaps",
        ),
        vertical_spacing=0.14,
        horizontal_spacing=0.12,
    )

    summary_rows = [
        (
            "Age (years)",
            f"{cap_avg_age:.1f}" if cap_avg_age else "—",
            f"{mate_avg_age:.1f}" if mate_avg_age else "—",
        ),
        (
            "Caps",
            f"{cap_avg_caps:.0f}" if cap_avg_caps else "—",
            f"{mate_avg_caps:.0f}" if mate_avg_caps else "—",
        ),
        (
            "Goals",
            f"{cap_avg_goals:.1f}" if cap_avg_goals else "—",
            f"{mate_avg_goals:.1f}" if mate_avg_goals else "—",
        ),
    ]
    fig.add_trace(
        go.Table(
            header={
                "values": ["Metric", CAPTAIN_LABEL, MATE_LABEL],
                "fill_color": PLOT_BG,
                "font": {"color": TEXT, "size": 12},
                "align": "left",
            },
            cells={
                "values": list(zip(*summary_rows, strict=True)),
                "fill_color": DASH_BG,
                "font": {"color": TEXT, "size": 12},
                "align": "left",
                "height": 32,
            },
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

    _delta_bars(
        fig, profiles, value_attr="age_vs_squad",
        label="Years older (+) or younger (−)", row=3, col=1,
    )
    _delta_bars(
        fig, profiles, value_attr="caps_vs_squad",
        label="Caps above (+) or below (−) squad avg", row=3, col=2,
    )

    subtitle = (
        f" · {most_capped_n}/{len(profiles)} captains are their team's most-capped player"
        if profiles
        else ""
    )
    dark_layout(
        fig,
        f"{tournament} — captains vs squad mates{subtitle}",
        height=920,
        showlegend=False,
    )
    fig.update_yaxes(title_text="% abroad", range=[0, max(cap_abroad, mate_abroad) + 15], row=1, col=2)
    fig.update_yaxes(title_text="Age", range=[16, 44], row=2, col=1)
    fig.update_yaxes(title_text="Caps", row=2, col=2)

    style_subplot_titles(fig)

    return fig
