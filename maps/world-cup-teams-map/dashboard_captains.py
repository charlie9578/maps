"""Captain vs squad-mate comparison charts."""

from __future__ import annotations

import statistics
from collections import Counter

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from dashboard_data import (
    CAPTAIN_LABEL,
    GRID,
    MATE_LABEL,
    POS_ORDER,
    PlayerRow,
    add_violin_box,
    captain_group,
    captain_profiles,
    dark_layout,
    make_plotly_table,
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
    limit_each_side: int = 6,
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
    fmt = "{:+.0f}" if value_attr == "caps_vs_squad" else "{:+.1f}"
    # Place the value just past the bar tip; keep the long player name in hover.
    fig.add_trace(
        go.Bar(
            y=[p.nation for p in ordered],
            x=values,
            orientation="h",
            marker={"color": ["#34d399" if v >= 0 else "#fb7185" for v in values]},
            text=[fmt.format(v) for v in values],
            textposition="outside",
            textfont={"size": 11},
            cliponaxis=False,
            customdata=[p.name for p in ordered],
            hovertemplate="%{y} — %{customdata}<br>" + label + ": %{x}<extra></extra>",
            showlegend=False,
        ),
        row=row,
        col=col,
    )
    # Headroom so the outside value labels are not clipped at the plot edge.
    lo = min(values + [0])
    hi = max(values + [0])
    span = (hi - lo) or 1
    fig.update_xaxes(
        title_text=label,
        row=row,
        col=col,
        gridcolor=GRID,
        range=[lo - 0.14 * span, hi + 0.14 * span],
        zeroline=True,
        zerolinecolor="#475569",
    )
    fig.update_yaxes(automargin=True, tickfont={"size": 11}, row=row, col=col)


def build_captain_position_panel(tournament: str, rows: list[PlayerRow]) -> go.Figure:
    """Grouped bars comparing position mix among captains vs all squad players."""
    captains = [r for r in rows if r.is_captain]
    cap_counts = Counter(r.pos for r in captains if r.pos in POS_ORDER)
    squad_counts = Counter(r.pos for r in rows if r.pos in POS_ORDER)
    cap_n = max(1, sum(cap_counts.values()))
    squad_n = max(1, sum(squad_counts.values()))

    cap_pcts = [100 * cap_counts[p] / cap_n for p in POS_ORDER]
    squad_pcts = [100 * squad_counts[p] / squad_n for p in POS_ORDER]
    cap_vals = [cap_counts[p] for p in POS_ORDER]
    squad_vals = [squad_counts[p] for p in POS_ORDER]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name=CAPTAIN_LABEL,
            x=POS_ORDER,
            y=cap_pcts,
            marker={"color": "#fbbf24"},
            text=[f"{v:.0f}%" for v in cap_pcts],
            textposition="outside",
            cliponaxis=False,
            customdata=cap_vals,
            hovertemplate="%{x}<br>" + CAPTAIN_LABEL + ": %{customdata} (%{y:.1f}%)<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            name="All squads",
            x=POS_ORDER,
            y=squad_pcts,
            marker={"color": "#64748b"},
            text=[f"{v:.0f}%" for v in squad_pcts],
            textposition="outside",
            cliponaxis=False,
            customdata=squad_vals,
            hovertemplate="%{x}<br>All squads: %{customdata} (%{y:.1f}%)<extra></extra>",
        )
    )
    dark_layout(
        fig,
        f"{tournament} — position mix: captains vs squads",
        height=400,
        showlegend=True,
        legend_below=True,
    )
    fig.update_layout(barmode="group")
    fig.update_xaxes(title_text="Position")
    fig.update_yaxes(title_text="Share of group (%)", range=[0, max(cap_pcts + squad_pcts) + 12], gridcolor=GRID)
    return fig


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
        make_plotly_table(
            ["Metric", CAPTAIN_LABEL, MATE_LABEL],
            summary_rows,
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
