from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from wind_data import COL

# --- Shared visual theme -----------------------------------------------------
# A cohesive dark "analytics command center" look with a renewable-energy
# teal/emerald accent palette, used across every chart and the map.

FONT_FAMILY = "Inter, system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
TEXT_COLOR = "#e2e8f0"
MUTED_COLOR = "#94a3b8"
GRID_COLOR = "rgba(148, 163, 184, 0.12)"

# General categorical palette for non-status charts.
COLORWAY = [
    "#22d3ee",
    "#34d399",
    "#818cf8",
    "#f472b6",
    "#fbbf24",
    "#a78bfa",
    "#2dd4bf",
    "#fb7185",
    "#60a5fa",
    "#facc15",
]

# Sequential gradient for "more = greener/brighter" magnitude charts.
CAPACITY_SCALE = [
    [0.0, "#0e7490"],
    [0.5, "#22d3ee"],
    [1.0, "#34d399"],
]

# Stable, meaningful colors for known project statuses.
STATUS_COLORS = {
    "operating": "#34d399",
    "construction": "#22d3ee",
    "pre-construction": "#818cf8",
    "announced": "#a78bfa",
    "shelved": "#fbbf24",
    "cancelled": "#f87171",
    "mothballed": "#fb923c",
    "retired": "#94a3b8",
}

HOVERLABEL = dict(
    bgcolor="#0f172a",
    bordercolor="rgba(148, 163, 184, 0.25)",
    font=dict(family=FONT_FAMILY, color=TEXT_COLOR, size=12),
)


def _apply_theme(fig: go.Figure, *, title: str | None = None) -> go.Figure:
    """Apply the shared dark theme to a cartesian / pie chart."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0, 0, 0, 0)",
        plot_bgcolor="rgba(0, 0, 0, 0)",
        colorway=COLORWAY,
        font=dict(family=FONT_FAMILY, color=TEXT_COLOR, size=13),
        margin=dict(l=8, r=8, t=48, b=8),
        hoverlabel=HOVERLABEL,
        legend=dict(font=dict(color=MUTED_COLOR)),
        title=dict(
            text=title,
            x=0.01,
            xanchor="left",
            font=dict(family=FONT_FAMILY, size=15, color=TEXT_COLOR),
        )
        if title
        else None,
    )
    fig.update_xaxes(
        gridcolor=GRID_COLOR,
        zeroline=False,
        color=MUTED_COLOR,
        title_font=dict(color=MUTED_COLOR),
    )
    fig.update_yaxes(
        gridcolor=GRID_COLOR,
        zeroline=False,
        color=MUTED_COLOR,
        title_font=dict(color=MUTED_COLOR),
    )
    return fig


def make_map(dff: pd.DataFrame):
    fig = px.scatter_map(
        dff,
        lat=COL.lat,
        lon=COL.lon,
        size=COL.capacity_mw,
        color=COL.status,
        color_discrete_map=STATUS_COLORS,
        hover_name="Project (display)",
        hover_data={
            COL.country: True,
            COL.installation_type: True,
            COL.capacity_mw: ":.1f",
            COL.start_year: True,
            COL.retired_year: True,
            COL.operator: True,
            COL.owner: True,
            COL.status: True,
            COL.lat: ":.4f",
            COL.lon: ":.4f",
            COL.wiki: True,
        },
        size_max=38,
        zoom=1.3,
        height=620,
        map_style="carto-darkmatter",
    )
    fig.update_layout(
        paper_bgcolor="rgba(0, 0, 0, 0)",
        font=dict(family=FONT_FAMILY, color=TEXT_COLOR, size=13),
        margin=dict(l=0, r=0, t=44, b=0),
        hoverlabel=HOVERLABEL,
        legend_title_text="Status",
        legend=dict(
            orientation="h",
            x=0,
            xanchor="left",
            y=1.03,
            yanchor="bottom",
            font=dict(color=MUTED_COLOR),
            bgcolor="rgba(0, 0, 0, 0)",
        ),
    )
    return fig


def make_installation_pie(dff: pd.DataFrame) -> go.Figure:
    inst = breakdown_installation_types(dff)
    fig = px.pie(
        inst,
        names=COL.installation_type,
        values="Capacity (MW)",
        title="Capacity by installation type",
        hole=0.58,
    )
    fig.update_traces(
        marker=dict(line=dict(color="#0b1120", width=2)),
        textposition="inside",
        textinfo="percent",
        insidetextfont=dict(color="#0b1120", size=13),
    )
    return _apply_theme(fig)


def make_status_bar(dff: pd.DataFrame) -> go.Figure:
    stat = breakdown_status(dff)
    fig = px.bar(
        stat,
        x=COL.status,
        y="Capacity (MW)",
        title="Capacity by status",
        color=COL.status,
        color_discrete_map=STATUS_COLORS,
    )
    fig.update_traces(marker_line_width=0)
    fig.update_layout(showlegend=False)
    fig = _apply_theme(fig)
    fig.update_layout(xaxis_title=None)
    return fig


def make_country_bar(dff: pd.DataFrame) -> go.Figure:
    ctry = breakdown_top_countries(dff, n=15)
    fig = px.bar(
        ctry,
        x=COL.country,
        y="Capacity (MW)",
        title="Capacity by country (top 15 + Other)",
        color="Capacity (MW)",
        color_continuous_scale=CAPACITY_SCALE,
    )
    fig.update_traces(marker_line_width=0)
    fig = _apply_theme(fig)
    fig.update_layout(xaxis_title=None, coloraxis_showscale=False)
    return fig


def make_top_projects_bar(dff: pd.DataFrame) -> go.Figure:
    top_projects = top_projects_table(dff, n=20)
    fig = px.bar(
        top_projects.sort_values("Total capacity (MW)", ascending=True),
        x="Total capacity (MW)",
        y=COL.project,
        orientation="h",
        title="Largest wind farms (top 20 projects, summed across phases)",
        color="Total capacity (MW)",
        color_continuous_scale=CAPACITY_SCALE,
    )
    fig.update_traces(marker_line_width=0)
    fig = _apply_theme(fig)
    fig.update_layout(yaxis_title=None, coloraxis_showscale=False)
    return fig


def top_projects_table(dff: pd.DataFrame, n: int = 50) -> pd.DataFrame:
    g = (
        dff.groupby([COL.country, COL.project], dropna=False)[COL.capacity_mw]
        .sum()
        .reset_index()
        .sort_values(COL.capacity_mw, ascending=False)
        .head(n)
    )
    g.rename(columns={COL.capacity_mw: "Total capacity (MW)"}, inplace=True)
    return g


def assets_table_df(dff: pd.DataFrame) -> pd.DataFrame:
    cols = [
        COL.country,
        COL.project,
        COL.phase,
        COL.capacity_mw,
        COL.installation_type,
        COL.status,
        COL.start_year,
        COL.retired_year,
        COL.operator,
        COL.owner,
        COL.lat,
        COL.lon,
        COL.wiki,
    ]
    out = dff[cols].copy()
    out.rename(
        columns={
            COL.capacity_mw: "Capacity (MW)",
            COL.installation_type: "Installation Type",
            COL.start_year: "Start year",
            COL.retired_year: "Retired year",
            COL.operator: "Operator",
            COL.owner: "Owner",
            COL.lat: "Latitude",
            COL.lon: "Longitude",
            COL.wiki: "Wiki URL",
            COL.country: "Country/Area",
            COL.project: "Project Name",
            COL.phase: "Phase Name",
            COL.status: "Status",
        },
        inplace=True,
    )
    return out


def breakdown_top_countries(dff: pd.DataFrame, n: int = 15) -> pd.DataFrame:
    by = (
        dff.groupby(COL.country, dropna=False)[COL.capacity_mw]
        .sum()
        .reset_index()
        .sort_values(COL.capacity_mw, ascending=False)
    )
    if len(by) <= n:
        by.rename(columns={COL.capacity_mw: "Capacity (MW)"}, inplace=True)
        return by
    top = by.head(n).copy()
    other = pd.DataFrame(
        [{COL.country: "Other", COL.capacity_mw: float(by.iloc[n:][COL.capacity_mw].sum())}]
    )
    out = pd.concat([top, other], ignore_index=True)
    out.rename(columns={COL.capacity_mw: "Capacity (MW)"}, inplace=True)
    return out


def breakdown_installation_types(dff: pd.DataFrame) -> pd.DataFrame:
    by = (
        dff.groupby(COL.installation_type, dropna=False)[COL.capacity_mw]
        .sum()
        .reset_index()
        .sort_values(COL.capacity_mw, ascending=False)
    )
    by.rename(columns={COL.capacity_mw: "Capacity (MW)"}, inplace=True)
    return by


def breakdown_status(dff: pd.DataFrame) -> pd.DataFrame:
    by = (
        dff.groupby(COL.status, dropna=False)[COL.capacity_mw]
        .sum()
        .reset_index()
        .sort_values(COL.capacity_mw, ascending=False)
    )
    by.rename(columns={COL.capacity_mw: "Capacity (MW)"}, inplace=True)
    return by

