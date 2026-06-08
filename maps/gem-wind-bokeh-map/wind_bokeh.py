"""Build the Bokeh layout (tile map + charts) with cross-filtering."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from bokeh.layouts import column, row
from bokeh.models import (
    CDSView,
    ColumnDataSource,
    HoverTool,
    IndexFilter,
    Label,
    Range1d,
    Title,
    WheelZoomTool,
)
from bokeh.plotting import figure

from wind_bokeh_charts import (
    MAP_HEIGHT,
    MAP_WIDTH,
    STATUS_COLORS,
    TEXT_COLOR,
    global_capacity_mapper,
    make_country_bar,
    make_installation_bar,
    make_owner_bar,
    make_status_bar,
    make_top_projects_bar,
    status_color_mapper,
    top_country_names,
    TOP_BAR_RANK,
)
from wind_bokeh_js import owner_json_entries, wire_cross_filter
from wind_data import COL

WEB_MERCATOR_SCALE = 6378137


def _stretch_width(fig) -> None:
    """Let figures share horizontal space in responsive rows."""
    fig.sizing_mode = "stretch_width"


def _scale_width(fig) -> None:
    """Scale proportionally — keeps plot frame aligned with map tiles."""
    fig.sizing_mode = "scale_width"


def _map_ranges(
    x: np.ndarray,
    y: np.ndarray,
    *,
    width: int,
    height: int,
    padding: float = 1.1,
) -> tuple[Range1d, Range1d]:
    """Symmetric ranges centred on data, matched to the figure aspect ratio."""
    cx = (float(x.min()) + float(x.max())) / 2.0
    cy = (float(y.min()) + float(y.max())) / 2.0
    data_w = float(x.max() - x.min()) or 1e6
    data_h = float(y.max() - y.min()) or 1e6
    fig_aspect = width / height

    if data_w / data_h > fig_aspect:
        half_w = data_w * padding / 2.0
        half_h = half_w / fig_aspect
    else:
        half_h = data_h * padding / 2.0
        half_w = half_h * fig_aspect

    return Range1d(cx - half_w, cx + half_w), Range1d(cy - half_h, cy + half_h)


def _lon_to_x(lon: np.ndarray) -> np.ndarray:
    return lon * (math.pi / 180.0) * WEB_MERCATOR_SCALE


def _lat_to_y(lat: np.ndarray) -> np.ndarray:
    return np.log(np.tan((90.0 + lat) * math.pi / 360.0)) * WEB_MERCATOR_SCALE


def _prepare_master_data(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["x"] = _lon_to_x(out[COL.lon].to_numpy(dtype=float))
    out["y"] = _lat_to_y(out[COL.lat].to_numpy(dtype=float))
    max_cap = float(out[COL.capacity_mw].max())
    out["size"] = (4.0 + 28.0 * np.sqrt(out[COL.capacity_mw] / max_cap)).astype(float)
    out["capacity"] = out[COL.capacity_mw].astype(float)
    out["country"] = out[COL.country].astype(str)
    out["installation_type"] = out[COL.installation_type].astype(str)
    out["status"] = out[COL.status].astype(str)
    out["project"] = out[COL.project].astype(str)
    out["project_display"] = out["Project (display)"].astype(str)
    out["operator"] = out[COL.operator].fillna("").astype(str)
    out["owner"] = out[COL.owner].fillna("").astype(str)
    out["wiki"] = out[COL.wiki].fillna("").astype(str)
    out["owner_json"] = out[COL.owner].map(owner_json_entries)
    out["phase"] = out[COL.phase].fillna("").astype(str)
    out["start_year"] = out[COL.start_year].apply(
        lambda v: "" if pd.isna(v) else str(int(v)) if float(v) == int(v) else str(v)
    )
    out["retired_year"] = out[COL.retired_year].apply(
        lambda v: "" if pd.isna(v) else str(int(v)) if float(v) == int(v) else str(v)
    )
    out["lat"] = out[COL.lat].astype(float)
    out["lon"] = out[COL.lon].astype(float)
    return out


def _make_master_source(prepared: pd.DataFrame) -> ColumnDataSource:
    return ColumnDataSource(
        data=dict(
            x=prepared["x"].tolist(),
            y=prepared["y"].tolist(),
            size=prepared["size"].tolist(),
            capacity=prepared["capacity"].tolist(),
            country=prepared["country"].tolist(),
            installation_type=prepared["installation_type"].tolist(),
            status=prepared["status"].tolist(),
            project=prepared["project"].tolist(),
            project_display=prepared["project_display"].tolist(),
            operator=prepared["operator"].tolist(),
            owner=prepared["owner"].tolist(),
            wiki=prepared["wiki"].tolist(),
            owner_json=prepared["owner_json"].tolist(),
            phase=prepared["phase"].tolist(),
            start_year=prepared["start_year"].tolist(),
            retired_year=prepared["retired_year"].tolist(),
            lat=prepared["lat"].tolist(),
            lon=prepared["lon"].tolist(),
        )
    )


def _make_map_figure(
    master: ColumnDataSource,
    index_filter: IndexFilter,
) -> tuple[figure, object, object]:
    """Map uses the shared master source with CDSView filtering (standard Bokeh pattern)."""
    x = np.array(master.data["x"], dtype=float)
    y = np.array(master.data["y"], dtype=float)
    x_range, y_range = _map_ranges(x, y, width=MAP_WIDTH, height=MAP_HEIGHT)

    p = figure(
        width=MAP_WIDTH,
        height=MAP_HEIGHT,
        x_range=x_range,
        y_range=y_range,
        tools="pan,reset",
        toolbar_location="above",
        background_fill_color="#0b1120",
        border_fill_color="#0b1120",
        outline_line_color=None,
        min_border_left=0,
        min_border_right=0,
        min_border_top=40,
        min_border_bottom=0,
    )
    p.title = Title(
        text="Global wind farm locations",
        text_color=TEXT_COLOR,
        text_font_size="15px",
        align="left",
    )
    p.axis.visible = False
    p.xgrid.visible = False
    p.ygrid.visible = False
    p.add_tools(WheelZoomTool())
    p.add_tile("CartoDB Dark Matter", retina=True)

    att = Label(
        x=8,
        y=8,
        x_units="screen",
        y_units="screen",
        text="© OpenStreetMap © CARTO",
        text_font_size="9px",
        text_color="#64748b",
        background_fill_alpha=0,
    )
    p.add_layout(att)

    color_mapper = status_color_mapper()
    fill_color = {"field": "status", "transform": color_mapper}

    # Context layer: all points, faded (visible when a chart filter is active).
    bg_renderer = p.scatter(
        x="x",
        y="y",
        size="size",
        marker="circle",
        fill_color=fill_color,
        line_color="#0b1120",
        line_width=0.4,
        fill_alpha=0.12,
        line_alpha=0.12,
        source=master,
        visible=False,
    )

    # Active layer: subset via IndexFilter on the shared source.
    filtered_view = CDSView(filter=index_filter)
    fg_renderer = p.scatter(
        x="x",
        y="y",
        size="size",
        marker="circle",
        fill_color=fill_color,
        line_color="#0b1120",
        line_width=0.6,
        fill_alpha=0.9,
        source=master,
        view=filtered_view,
    )
    p.add_tools(
        HoverTool(
            renderers=[fg_renderer],
            tooltips=[
                ("Project", "@project_display"),
                ("Country", "@country"),
                ("Capacity (MW)", "@capacity{0,0}"),
                ("Status", "@status"),
                ("Operator", "@operator"),
                ("Owner", "@owner"),
                ("Wiki", "@wiki"),
            ],
        )
    )
    return p, fg_renderer, bg_renderer


def build_layout(df: pd.DataFrame):
    """Return Bokeh layout and the master ColumnDataSource for export."""
    prepared = _prepare_master_data(df)
    master = _make_master_source(prepared)
    row_count = len(prepared)
    index_filter = IndexFilter(indices=list(range(row_count)))

    filter_state = ColumnDataSource(
        data={
            "inst_filter": [""],
            "status_filter": [""],
            "country_filter": [""],
            "owner_filter": [""],
            "project_filter": [""],
        }
    )

    cap_mapper = global_capacity_mapper(float(prepared["capacity"].max()))

    map_fig, map_fg_renderer, map_bg_renderer = _make_map_figure(master, index_filter)

    inst_fig, inst_source, inst_renderer, inst_tap_col = make_installation_bar(df)
    status_fig, status_source, status_renderer, status_tap_col = make_status_bar(df)
    country_fig, country_source, country_renderer, country_tap_col = make_country_bar(df, cap_mapper)
    projects_fig, projects_source, projects_renderer, project_tap_col = make_top_projects_bar(
        df, cap_mapper
    )
    owner_fig, owner_source, owner_renderer, owner_tap_col = make_owner_bar(df, cap_mapper)

    top_countries = top_country_names(df, n=TOP_BAR_RANK)

    wire_cross_filter(
        master=master,
        index_filter=index_filter,
        map_bg_renderer=map_bg_renderer,
        inst_source=inst_source,
        status_source=status_source,
        country_source=country_source,
        projects_source=projects_source,
        owner_source=owner_source,
        filter_state=filter_state,
        inst_renderer=inst_renderer,
        status_renderer=status_renderer,
        country_renderer=country_renderer,
        projects_renderer=projects_renderer,
        owner_renderer=owner_renderer,
        inst_fig=inst_fig,
        status_fig=status_fig,
        country_fig=country_fig,
        projects_fig=projects_fig,
        owner_fig=owner_fig,
        top_countries=top_countries,
        row_count=row_count,
        inst_tap_col=inst_tap_col,
        status_tap_col=status_tap_col,
        country_tap_col=country_tap_col,
        project_tap_col=project_tap_col,
        owner_tap_col=owner_tap_col,
    )

    _scale_width(map_fig)
    for fig in (inst_fig, status_fig, country_fig, projects_fig, owner_fig):
        _stretch_width(fig)

    charts_row1 = row(inst_fig, status_fig, sizing_mode="stretch_width")
    charts_row2 = row(country_fig, projects_fig, sizing_mode="stretch_width")
    charts_block = column(
        charts_row1,
        charts_row2,
        owner_fig,
        sizing_mode="stretch_width",
        spacing=12,
    )
    layout = column(map_fig, charts_block, sizing_mode="stretch_width", spacing=12)
    return layout, master, filter_state, STATUS_COLORS
