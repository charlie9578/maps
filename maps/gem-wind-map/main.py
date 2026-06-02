from pathlib import Path

import dash_bootstrap_components as dbc
from dash import Dash, Input, Output, State, dcc, html
from dash.dash_table import DataTable
from dash.exceptions import PreventUpdate

import pandas as pd

from wind_data import COL, filter_df, load_data, sorted_unique
from wind_viz import (
    assets_table_df,
    make_country_bar,
    make_installation_pie,
    make_map,
    make_status_bar,
    make_top_projects_bar,
)

GOOGLE_FONTS = "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap"

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


def _kpi_card(value_id: str, label: str):
    return html.Div(
        className="kpi-card kpi",
        children=[
            html.Div(id=value_id, className="kpi-value"),
            html.Div(label, className="kpi-label"),
        ],
    )


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

    app = Dash(
        __name__,
        external_stylesheets=[dbc.themes.DARKLY, GOOGLE_FONTS],
        title="GEM wind farms (Feb 2026)",
    )
    app.title = "GEM wind farms (Feb 2026)"

    app.layout = dbc.Container(
        fluid=True,
        className="app-shell py-3",
        children=[
            html.Div(
                className="app-hero mb-3",
                children=dbc.Row(
                    className="align-items-center g-3",
                    children=[
                        dbc.Col(
                            [
                                html.Span("Global Wind Power Tracker", className="app-eyebrow"),
                                html.Div("Wind farms of the world", className="app-title h2 mb-0"),
                                html.Div(
                                    "February 2026 snapshot  ·  marker size = capacity  ·  color = status",
                                    className="muted",
                                ),
                            ],
                            md=8,
                        ),
                        dbc.Col(
                            html.Div(
                                "Tip: click a slice or bar to cross-filter (click again to clear).",
                                className="tip-pill",
                            ),
                            md=4,
                            className="d-flex justify-content-md-end",
                        ),
                    ],
                ),
            ),
            dbc.Row(
                className="g-3",
                children=[
                    dbc.Col(
                        md=4,
                        lg=3,
                        children=[
                            dbc.Card(
                                className="card-tight shadow-sm sticky-sidebar",
                                children=[
                                    dbc.CardBody(
                                        [
                                            html.Div("Filters", className="section-label mb-3"),
                                            dbc.Label("Search (project / phase / operator / owner)", className="mb-1"),
                                            dbc.Input(id="search-text", type="text", value="", placeholder="e.g. Vestas"),
                                            html.Div(className="my-2"),
                                            dbc.Label("Country/Area", className="mb-1"),
                                            dcc.Dropdown(
                                                id="country",
                                                options=[{"label": c, "value": c} for c in countries],
                                                value=[],
                                                multi=True,
                                                placeholder="All countries",
                                            ),
                                            html.Div(className="my-2"),
                                            dbc.Label("Status", className="mb-1"),
                                            dcc.Dropdown(
                                                id="status",
                                                options=[{"label": s, "value": s} for s in statuses],
                                                value=[],
                                                multi=True,
                                                placeholder="All statuses",
                                            ),
                                            html.Div(className="my-2"),
                                            dbc.Label("Installation Type", className="mb-1"),
                                            dcc.Dropdown(
                                                id="installation-type",
                                                options=[{"label": t, "value": t} for t in installation_types],
                                                value=[],
                                                multi=True,
                                                placeholder="All installation types",
                                            ),
                                            html.Div(className="my-2"),
                                            dbc.Label("Capacity range (MW)", className="mb-1"),
                                            dcc.RangeSlider(
                                                id="capacity-range",
                                                min=cap_min,
                                                max=cap_max,
                                                value=cap_default,
                                                tooltip={"placement": "bottom", "always_visible": False},
                                                allowCross=False,
                                            ),
                                            html.Div(className="my-2"),
                                            dbc.Label("Start year range (blank start year is kept)", className="mb-1"),
                                            dcc.RangeSlider(
                                                id="start-year-range",
                                                min=sy_min,
                                                max=sy_max,
                                                value=sy_default,
                                                step=1,
                                                tooltip={"placement": "bottom", "always_visible": False},
                                                allowCross=False,
                                            ),
                                            html.Div(className="my-2"),
                                            dcc.Checklist(
                                                id="flags",
                                                options=[
                                                    {"label": "Only entries with Hydrogen", "value": "hydrogen"},
                                                    {"label": "Only entries with Associated storage", "value": "storage"},
                                                ],
                                                value=[],
                                            ),
                                            html.Hr(className="my-3"),
                                            html.Div(
                                                id="summary-text",
                                                className="muted",
                                                style={"whiteSpace": "pre-wrap"},
                                            ),
                                        ]
                                    )
                                ],
                            )
                        ],
                    ),
                    dbc.Col(
                        md=8,
                        lg=9,
                        children=[
                            dbc.Row(
                                className="g-3 mb-3",
                                children=[
                                    dbc.Col(_kpi_card("kpi-capacity", "Total capacity (MW)"), md=4),
                                    dbc.Col(_kpi_card("kpi-rows", "Filtered rows"), md=4),
                                    dbc.Col(_kpi_card("kpi-countries", "Countries"), md=4),
                                ],
                            ),
                            dbc.Card(
                                className="mb-3",
                                children=dbc.CardBody(
                                    dcc.Loading(
                                        type="circle",
                                        color="#34d399",
                                        children=dcc.Graph(id="map", config={"displayModeBar": True}),
                                    )
                                ),
                            ),
                            dbc.Card(
                                children=dbc.CardBody(
                                    dcc.Tabs(
                                        value="breakdowns",
                                        className="dash-tabs",
                                        children=[
                                            dcc.Tab(
                                                label="Breakdowns",
                                                value="breakdowns",
                                                children=[
                                                    html.Div(className="pt-2"),
                                                    dbc.Row(
                                                        className="g-3",
                                                        children=[
                                                            dbc.Col(
                                                                dcc.Loading(
                                                                    type="circle",
                                                                    color="#34d399",
                                                                    children=dcc.Graph(id="installation-pie"),
                                                                ),
                                                                md=6,
                                                            ),
                                                            dbc.Col(
                                                                dcc.Loading(
                                                                    type="circle",
                                                                    color="#34d399",
                                                                    children=dcc.Graph(id="status-bar"),
                                                                ),
                                                                md=6,
                                                            ),
                                                            dbc.Col(
                                                                dcc.Loading(
                                                                    type="circle",
                                                                    color="#34d399",
                                                                    children=dcc.Graph(id="country-bar"),
                                                                ),
                                                                md=6,
                                                            ),
                                                            dbc.Col(
                                                                dcc.Loading(
                                                                    type="circle",
                                                                    color="#34d399",
                                                                    children=dcc.Graph(id="top-projects-bar"),
                                                                ),
                                                                md=6,
                                                            ),
                                                        ],
                                                    ),
                                                ],
                                            ),
                                            dcc.Tab(
                                                label="Wind farm list",
                                                value="list",
                                                children=[
                                                    html.Div(className="pt-2"),
                                                    dbc.Row(
                                                        className="align-items-center g-2 mb-2",
                                                        children=[
                                                            dbc.Col(
                                                                html.Div(
                                                                    "Table shows the currently filtered rows (including the Status groupings).",
                                                                    className="muted",
                                                                ),
                                                                md=8,
                                                            ),
                                                            dbc.Col(
                                                                dbc.Button(
                                                                    "Download filtered CSV",
                                                                    id="download-csv-btn",
                                                                    color="primary",
                                                                    className="w-100 w-md-auto",
                                                                ),
                                                                md=4,
                                                            ),
                                                        ],
                                                    ),
                                                    dcc.Download(id="download-csv"),
                                                    dcc.Loading(
                                                        type="circle",
                                                        color="#34d399",
                                                        children=DataTable(
                                                            id="assets-table",
                                                            page_size=20,
                                                            sort_action="native",
                                                            filter_action="native",
                                                            style_as_list_view=True,
                                                            style_table={"overflowX": "auto"},
                                                            style_cell={
                                                                "fontFamily": "inherit",
                                                                "fontSize": 12,
                                                                "padding": "10px 12px",
                                                                "whiteSpace": "normal",
                                                                "height": "auto",
                                                                "maxWidth": "420px",
                                                                "backgroundColor": "transparent",
                                                                "color": "#e2e8f0",
                                                                "border": "none",
                                                                "borderBottom": "1px solid rgba(148, 163, 184, 0.12)",
                                                            },
                                                            style_header={
                                                                "fontWeight": "700",
                                                                "textTransform": "uppercase",
                                                                "fontSize": 11,
                                                                "letterSpacing": "0.06em",
                                                                "backgroundColor": "rgba(15, 23, 42, 0.6)",
                                                                "color": "#94a3b8",
                                                                "border": "none",
                                                                "borderBottom": "1px solid rgba(148, 163, 184, 0.24)",
                                                            },
                                                            style_data_conditional=[
                                                                {
                                                                    "if": {"row_index": "odd"},
                                                                    "backgroundColor": "rgba(148, 163, 184, 0.05)",
                                                                },
                                                                {
                                                                    "if": {"state": "active"},
                                                                    "backgroundColor": "rgba(52, 211, 153, 0.12)",
                                                                    "border": "1px solid rgba(52, 211, 153, 0.4)",
                                                                },
                                                            ],
                                                            style_filter={
                                                                "backgroundColor": "rgba(15, 23, 42, 0.6)",
                                                                "color": "#e2e8f0",
                                                            },
                                                            markdown_options={"link_target": "_blank"},
                                                        ),
                                                    ),
                                                ],
                                            ),
                                        ],
                                    )
                                ),
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
        Output("kpi-capacity", "children"),
        Output("kpi-rows", "children"),
        Output("kpi-countries", "children"),
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
        kpi_capacity = f"{total_capacity:,.0f}"
        kpi_rows = f"{len(dff):,}"
        kpi_countries = f"{countries_n:,}"
        summary = (
            f"Filtered rows: {len(dff):,}\n"
            f"Total capacity (MW): {total_capacity:,.1f}\n"
            f"Countries: {countries_n} | Statuses: {status_n} | Installation types: {installations_n}"
        )

        kpi_capacity_ui = [
            html.Span(kpi_capacity, className="kpi-number"),
            html.Br(),
            html.Span("MW", className="kpi-unit"),
        ]
        kpi_rows_ui = [
            html.Span(kpi_rows, className="kpi-number"),
            html.Br(),
            html.Span("rows", className="kpi-unit"),
        ]
        kpi_countries_ui = [
            html.Span(kpi_countries, className="kpi-number"),
            html.Br(),
            html.Span("countries", className="kpi-unit"),
        ]

        inst_fig = make_installation_pie(dff)
        status_fig = make_status_bar(dff)
        country_fig = make_country_bar(dff)
        top_fig = make_top_projects_bar(dff)

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
            kpi_capacity_ui,
            kpi_rows_ui,
            kpi_countries_ui,
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
