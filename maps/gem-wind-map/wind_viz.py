from __future__ import annotations

import pandas as pd
import plotly.express as px

from wind_data import COL


def make_map(dff: pd.DataFrame):
    fig = px.scatter_map(
        dff,
        lat=COL.lat,
        lon=COL.lon,
        size=COL.capacity_mw,
        color=COL.status,
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
        size_max=40,
        zoom=1,
        height=650,
        map_style="carto-positron",
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=40, b=0),
        legend_title_text="Status",
        legend=dict(
            orientation="h",
            x=0,
            xanchor="left",
            y=1.02,
            yanchor="bottom",
        ),
    )
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

