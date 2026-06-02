from pathlib import Path

import plotly.express as px
from dash import Dash, Input, Output, State, dcc, html
from dash.dash_table import DataTable
from dash.exceptions import PreventUpdate

import pandas as pd

from wind_data import COL, filter_df, load_data, sorted_unique
from wind_viz import (
    assets_table_df,
    breakdown_installation_types,
    breakdown_status,
    breakdown_top_countries,
    make_map,
    top_projects_table,
)

MAP_DIR = Path(__file__).resolve().parent
DATA_PATH = MAP_DIR / "data" / "Global-Wind-Power-Tracker-February-2026.xlsx"


def _extract_pie_label(click_data: dict | None) -> str | None:
    if not click_data:
        return None
    points = click_data.get("points") or []
    if not points:
        return None
    label = points[0].get("label")
    if isinstance(label, str) and label.strip():
        return label.strip()
    return None


def _extract_xy(click_data: dict | None, key: str) -> str | None:
    if not click_data:
        return None
    points = click_data.get("points") or []
    if not points:
        return None
    v = points[0].get(key)
    if isinstance(v, str) and v.strip():
        return v.strip()
    return None


def _toggle_single_selection(current: list[str] | None, selected: str | None) -> list[str]:
    cur = list(current or [])
    if not selected:
        return cur
    if len(cur) == 1 and cur[0] == selected:
        return []
    return [selected]


def make_app(df: pd.DataFrame) -> Dash:
    countries = sorted_unique(df, COL.country)
    statuses = sorted_unique(df, COL.status)
    installation_types = sorted_unique(df, COL.installation_type)

    cap_min = float(df[COL.capacity_mw].min())
    cap_max = float(df[COL.capacity_mw].max())
    cap_default = [cap_min, cap_max]

    sy = df[COL.start_year].dropna()
    sy_min = float(sy.min()) if len(sy) else 1900.0
    sy_max = float(sy.max()) if len(sy) else 2035.0
    sy_default = [sy_min, sy_max]

    app = Dash(__name__)
    app.title = "GEM wind farms (Feb 2026)"

    app.layout = html.Div(
        style={"fontFamily": "system-ui, -apple-system, Segoe UI, Roboto, Arial", "padding": "12px"},
        children=[
            html.H2("Global Wind Power Tracker — dashboard (Feb 2026)"),
            html.Div(
                "Tip: click a slice/bar in the breakdown charts to cross-filter (click again to clear).",
                style={"color": "#4b5563", "marginBottom": "8px"},
            ),
            html.Div(
                style={"display": "grid", "gridTemplateColumns": "360px 1fr", "gap": "12px", "alignItems": "start"},
                children=[
                    html.Div(
                        style={
                            "border": "1px solid #e5e7eb",
                            "borderRadius": "10px",
                            "padding": "12px",
                            "background": "#fafafa",
                        },
                        children=[
                            html.Div("Filters", style={"fontWeight": 700, "marginBottom": "8px"}),
                            html.Label("Search (project / phase / operator / owner)"),
                            dcc.Input(id="search-text", type="text", value="", style={"width": "100%"}),
                            html.Div(style={"height": "10px"}),
                            html.Label("Country/Area"),
                            dcc.Dropdown(
                                id="country",
                                options=[{"label": c, "value": c} for c in countries],
                                value=[],
                                multi=True,
                                placeholder="All countries",
                            ),
                            html.Div(style={"height": "10px"}),
                            html.Label("Status"),
                            dcc.Dropdown(
                                id="status",
                                options=[{"label": s, "value": s} for s in statuses],
                                value=[],
                                multi=True,
                                placeholder="All statuses",
                            ),
                            html.Div(style={"height": "10px"}),
                            html.Label("Installation Type"),
                            dcc.Dropdown(
                                id="installation-type",
                                options=[{"label": t, "value": t} for t in installation_types],
                                value=[],
                                multi=True,
                                placeholder="All installation types",
                            ),
                            html.Div(style={"height": "10px"}),
                            html.Label("Capacity range (MW)"),
                            dcc.RangeSlider(
                                id="capacity-range",
                                min=cap_min,
                                max=cap_max,
                                value=cap_default,
                                tooltip={"placement": "bottom", "always_visible": False},
                                allowCross=False,
                            ),
                            html.Div(style={"height": "10px"}),
                            html.Label("Start year range (blank start year is kept)"),
                            dcc.RangeSlider(
                                id="start-year-range",
                                min=sy_min,
                                max=sy_max,
                                value=sy_default,
                                step=1,
                                tooltip={"placement": "bottom", "always_visible": False},
                                allowCross=False,
                            ),
                            html.Div(style={"height": "10px"}),
                            dcc.Checklist(
                                id="flags",
                                options=[
                                    {"label": "Only entries with Hydrogen", "value": "hydrogen"},
                                    {"label": "Only entries with Associated storage", "value": "storage"},
                                ],
                                value=[],
                            ),
                            html.Hr(),
                            html.Div(id="summary-text", style={"whiteSpace": "pre-wrap", "fontSize": "13px"}),
                        ],
                    ),
                    html.Div(
                        children=[
                            dcc.Graph(id="map", config={"displayModeBar": True}),
                            dcc.Tabs(
                                value="breakdowns",
                                children=[
                                    dcc.Tab(
                                        label="Breakdowns",
                                        value="breakdowns",
                                        children=[
                                            html.Div(
                                                style={
                                                    "display": "grid",
                                                    "gridTemplateColumns": "1fr 1fr",
                                                    "gap": "12px",
                                                    "paddingTop": "10px",
                                                },
                                                children=[
                                                    dcc.Graph(id="installation-pie"),
                                                    dcc.Graph(id="status-bar"),
                                                    dcc.Graph(id="country-bar"),
                                                    dcc.Graph(id="top-projects-bar"),
                                                ],
                                            )
                                        ],
                                    ),
                                    dcc.Tab(
                                        label="Wind farm list",
                                        value="list",
                                        children=[
                                            html.Div(style={"height": "10px"}),
                                            html.Div(
                                                style={
                                                    "display": "flex",
                                                    "gap": "10px",
                                                    "alignItems": "center",
                                                    "justifyContent": "space-between",
                                                    "flexWrap": "wrap",
                                                },
                                                children=[
                                                    html.Div(
                                                        "Table shows the currently filtered rows. Use the button to download as CSV.",
                                                        style={"color": "#4b5563"},
                                                    ),
                                                    html.Button(
                                                        "Download filtered CSV",
                                                        id="download-csv-btn",
                                                        style={
                                                            "border": "1px solid #d1d5db",
                                                            "background": "white",
                                                            "padding": "8px 10px",
                                                            "borderRadius": "8px",
                                                            "cursor": "pointer",
                                                        },
                                                    ),
                                                ],
                                            ),
                                            dcc.Download(id="download-csv"),
                                            html.Div(style={"height": "10px"}),
                                            DataTable(
                                                id="assets-table",
                                                page_size=20,
                                                sort_action="native",
                                                filter_action="native",
                                                style_table={"overflowX": "auto"},
                                                style_cell={
                                                    "fontFamily": "inherit",
                                                    "fontSize": 12,
                                                    "padding": "6px",
                                                    "whiteSpace": "normal",
                                                    "height": "auto",
                                                    "maxWidth": "420px",
                                                },
                                                style_header={"fontWeight": "bold"},
                                                markdown_options={"link_target": "_blank"},
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
            dcc.Store(id="df-store", data=df.to_dict("records")),
            dcc.Store(id="filtered-store"),
        ],
    )

    @app.callback(
        Output("installation-type", "value"),
        Input("installation-pie", "clickData"),
        # current dropdown selection
        Input("installation-type", "value"),
        prevent_initial_call=True,
    )
    def _crossfilter_installation_type(click_data, current_values):
        selected = _extract_pie_label(click_data)
        if selected is None:
            raise PreventUpdate
        return _toggle_single_selection(current_values, selected)

    @app.callback(
        Output("status", "value"),
        Input("status-bar", "clickData"),
        Input("status", "value"),
        prevent_initial_call=True,
    )
    def _crossfilter_status(click_data, current_values):
        selected = _extract_xy(click_data, "x")
        if selected is None:
            raise PreventUpdate
        return _toggle_single_selection(current_values, selected)

    @app.callback(
        Output("country", "value"),
        Input("country-bar", "clickData"),
        Input("country", "value"),
        prevent_initial_call=True,
    )
    def _crossfilter_country(click_data, current_values):
        selected = _extract_xy(click_data, "x")
        if selected is None:
            raise PreventUpdate
        return _toggle_single_selection(current_values, selected)

    @app.callback(
        Output("map", "figure"),
        Output("summary-text", "children"),
        Output("installation-pie", "figure"),
        Output("status-bar", "figure"),
        Output("country-bar", "figure"),
        Output("top-projects-bar", "figure"),
        Output("assets-table", "data"),
        Output("assets-table", "columns"),
        Output("filtered-store", "data"),
        Input("df-store", "data"),
        Input("country", "value"),
        Input("status", "value"),
        Input("installation-type", "value"),
        Input("capacity-range", "value"),
        Input("start-year-range", "value"),
        Input("flags", "value"),
        Input("search-text", "value"),
    )
    def _update(
        records,
        country_values,
        status_values,
        installation_values,
        capacity_range,
        start_year_range,
        flags,
        search_text,
    ):
        base = pd.DataFrame.from_records(records)
        dff = filter_df(
            base,
            countries=country_values or None,
            statuses=status_values or None,
            installation_types=installation_values or None,
            capacity_range=capacity_range,
            start_year_range=start_year_range,
            require_hydrogen=("hydrogen" in (flags or [])),
            require_storage=("storage" in (flags or [])),
            search_text=search_text,
        )

        map_fig = make_map(dff)

        total_capacity = float(dff[COL.capacity_mw].sum()) if len(dff) else 0.0
        status_n = int(dff[COL.status].nunique()) if len(dff) else 0
        countries_n = int(dff[COL.country].nunique()) if len(dff) else 0
        installations_n = int(dff[COL.installation_type].nunique()) if len(dff) else 0
        summary = (
            f"Filtered rows: {len(dff):,}\n"
            f"Total capacity (MW): {total_capacity:,.1f}\n"
            f"Countries: {countries_n} | Statuses: {status_n} | Installation types: {installations_n}"
        )

        inst = breakdown_installation_types(dff)
        inst_fig = px.pie(inst, names=COL.installation_type, values="Capacity (MW)", title="Capacity by installation type")
        inst_fig.update_layout(margin=dict(l=0, r=0, t=40, b=0))

        stat = breakdown_status(dff)
        status_fig = px.bar(stat, x=COL.status, y="Capacity (MW)", title="Capacity by status")
        status_fig.update_layout(margin=dict(l=0, r=0, t=40, b=0), xaxis_title=None)

        ctry = breakdown_top_countries(dff, n=15)
        country_fig = px.bar(ctry, x=COL.country, y="Capacity (MW)", title="Capacity by country (top 15 + Other)")
        country_fig.update_layout(margin=dict(l=0, r=0, t=40, b=0), xaxis_title=None)

        top_projects = top_projects_table(dff, n=20)
        top_fig = px.bar(
            top_projects.sort_values("Total capacity (MW)", ascending=True),
            x="Total capacity (MW)",
            y=COL.project,
            orientation="h",
            title="Largest wind farms (top 20 projects, summed across phases)",
        )
        top_fig.update_layout(margin=dict(l=0, r=0, t=40, b=0), yaxis_title=None)

        assets = assets_table_df(dff)
        assets_data = assets.to_dict("records")
        assets_cols = []
        for c in assets.columns:
            col = {"name": c, "id": c}
            if c == "Wiki URL":
                col["presentation"] = "markdown"
            assets_cols.append(col)

        return (
            map_fig,
            summary,
            inst_fig,
            status_fig,
            country_fig,
            top_fig,
            assets_data,
            assets_cols,
            assets_data,
        )

    @app.callback(
        Output("download-csv", "data"),
        Input("download-csv-btn", "n_clicks"),
        State("filtered-store", "data"),
        prevent_initial_call=True,
    )
    def _download_csv(n_clicks, filtered_records):
        if not n_clicks:
            raise PreventUpdate
        df_dl = pd.DataFrame.from_records(filtered_records or [])
        return dcc.send_data_frame(df_dl.to_csv, "gem-wind-map-filtered.csv", index=False)

    return app


def main() -> None:
    df = load_data(DATA_PATH)
    app = make_app(df)
    app.run(debug=True, host="127.0.0.1", port=8050)


if __name__ == "__main__":
    main()
