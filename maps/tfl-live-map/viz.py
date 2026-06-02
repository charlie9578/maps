"""Plotly figures for tfl-live-map."""

from __future__ import annotations

import time

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from data_processing import branch_coords

PLOTLY_TEMPLATE = "plotly_white"
TRAIN_TRACE_NAME = "trains"
STATIONS_TRACE_NAME = "stations"
MAP_UIREVISION = "tfl-live-map"


def style_figure(fig):
    """Shared layout tweaks for dashboard charts."""
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        margin=dict(l=0, r=0, t=40, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


LINE_COLORS = {
    "bakerloo": "#B36305",
    "central": "#E32017",
    "circle": "#FFD300",
    "district": "#00782A",
    "hammersmith-city": "#F3A9BB",
    "jubilee": "#A0A5A9",
    "metropolitan": "#9B0056",
    "northern": "#000000",
    "piccadilly": "#003688",
    "victoria": "#0098D4",
    "waterloo-city": "#95CDBA",
}


def _line_color(line_id: str) -> str:
    return LINE_COLORS.get(line_id, "#444444")


def _line_polylines(dirs: dict) -> tuple[list[float | None], list[float | None]]:
    """Merge all branches/directions into one disconnected polyline (None gaps)."""
    lats: list[float | None] = []
    lons: list[float | None] = []
    for branches in (dirs or {}).values():
        for branch in branches or []:
            coords = branch_coords(branch)
            if not coords:
                continue
            for lat, lon in coords:
                lats.append(float(lat))
                lons.append(float(lon))
            lats.append(None)
            lons.append(None)
    if lats and lats[-1] is None:
        lats.pop()
        lons.pop()
    return lats, lons


def _train_customdata(trains: pd.DataFrame) -> list[list]:
    towards = trains["towards_1"] if "towards_1" in trains.columns else trains.get("towards", pd.Series([""] * len(trains)))
    prev_station = trains.get("stationName_0", pd.Series([""] * len(trains)))
    next_station = (
        trains["stationName_1"]
        if "stationName_1" in trains.columns
        else trains.get("stationName", pd.Series([""] * len(trains)))
    )
    eta = trains["timeToStation_s"] if "timeToStation_s" in trains.columns else trains.get("tts1_s", pd.Series([0] * len(trains)))
    if "fetched_at_epoch" in trains.columns:
        updated_ago = (time.time() - trains["fetched_at_epoch"].astype(float)).round().astype(int).clip(lower=0)
    else:
        updated_ago = pd.Series([0] * len(trains), index=trains.index)
    direction = (
        trains["direction_norm"]
        if "direction_norm" in trains.columns
        else trains.get("direction", pd.Series(["unknown"] * len(trains)))
    )
    current_location = trains.get("currentLocation", pd.Series([""] * len(trains)))
    return [
        [str(vid), str(lid), str(t), str(prev), str(nxt), int(e), int(ago), str(d), str(cl)]
        for vid, lid, t, prev, nxt, e, ago, d, cl in zip(
            trains["vehicleId"].astype(str),
            trains["lineId"].astype(str),
            towards.astype(str),
            prev_station.astype(str),
            next_station.astype(str),
            eta.astype(int),
            updated_ago.astype(int),
            direction.astype(str),
            current_location.astype(str),
        )
    ]


def make_map_base(
    *,
    routes: dict | None = None,
    stop_points: pd.DataFrame | None = None,
    trains: pd.DataFrame | None = None,
) -> go.Figure:
    """Static map: route polylines (one trace per line), stations, trains."""
    fig = go.Figure()

    if routes:
        for line_id, dirs in routes.items():
            lats, lons = _line_polylines(dirs)
            if not lats:
                continue
            fig.add_trace(
                go.Scattermapbox(
                    lat=lats,
                    lon=lons,
                    mode="lines",
                    line=dict(color=_line_color(str(line_id)), width=2),
                    name=str(line_id),
                    hoverinfo="skip",
                    showlegend=False,
                    opacity=0.55,
                )
            )

    if stop_points is not None and not stop_points.empty:
        fig.add_trace(
            go.Scattermapbox(
                lat=stop_points["lat"],
                lon=stop_points["lon"],
                mode="markers",
                name=STATIONS_TRACE_NAME,
                marker=dict(size=6, color="#6b7280", opacity=0.75),
                text=stop_points["stationName"],
                hovertemplate="<b>%{text}</b><extra></extra>",
                showlegend=False,
            )
        )

    train_lats: list[float] = []
    train_lons: list[float] = []
    train_colors: list[str] = []
    train_custom: list[list] = []
    if trains is not None and not trains.empty and {"lat", "lon", "lineId", "vehicleId"}.issubset(trains.columns):
        train_lats = trains["lat"].astype(float).tolist()
        train_lons = trains["lon"].astype(float).tolist()
        train_colors = [_line_color(str(x)) for x in trains["lineId"].astype(str)]
        train_custom = _train_customdata(trains)

    fig.add_trace(
        go.Scattermapbox(
            lat=train_lats,
            lon=train_lons,
            mode="markers",
            name=TRAIN_TRACE_NAME,
            marker=dict(
                size=11,
                color=train_colors if train_colors else "#2563eb",
                opacity=0.95,
            ),
            customdata=train_custom,
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Line: %{customdata[1]}<br>"
                "Direction: %{customdata[7]}<br>"
                "Current: %{customdata[8]}<br>"
                "Towards: %{customdata[2]}<br>"
                "Previous: %{customdata[3]}<br>"
                "Next: %{customdata[4]}<br>"
                "ETA: %{customdata[5]}s<br>"
                "Updated: %{customdata[6]}s ago<br>"
                "<extra></extra>"
            ),
            showlegend=False,
        )
    )

    fig.update_layout(
        title="Live Tube trains (smooth animation, estimated between stops)",
        mapbox_style="carto-positron",
        mapbox_zoom=10,
        mapbox_center=dict(lat=51.5074, lon=-0.1278),
        height=650,
        uirevision=MAP_UIREVISION,
    )
    return style_figure(fig)


def make_summary_bar(dff: pd.DataFrame):
    if dff.empty or "lineId" not in dff.columns:
        fig = px.bar(title="Trains by line")
        return style_figure(fig)

    agg = dff.groupby("lineId", dropna=False).size().reset_index(name="trains")
    agg = agg.sort_values("trains", ascending=False)
    fig = px.bar(
        agg,
        x="lineId",
        y="trains",
        color="lineId",
        color_discrete_map={k: v for k, v in LINE_COLORS.items()},
        title="Trains by line",
    )
    fig.update_layout(xaxis_title=None, showlegend=False)
    return style_figure(fig)


def make_time_to_station_hist(dff: pd.DataFrame):
    if dff.empty or "timeToStation_s" not in dff.columns:
        fig = px.histogram(title="Time-to-station distribution")
        return style_figure(fig)
    fig = px.histogram(
        dff,
        x="timeToStation_s",
        nbins=30,
        title="Time-to-station (seconds) — per train (next arrival)",
    )
    fig.update_layout(xaxis_title=None, yaxis_title=None)
    return style_figure(fig)
