"""Dash entry point for MAP_NAME. Run from repo root: python maps/MAP_NAME/main.py"""

from __future__ import annotations

from pathlib import Path

import dash_bootstrap_components as dbc
import pandas as pd
from dash import Dash, Input, Output, State, dcc, html
from dash.dash_table import DataTable
from dash.exceptions import PreventUpdate

from data_processing import filter_df, load_data, sorted_unique
from viz import make_detail_scatter, make_summary_bar

MAP_DIR = Path(__file__).resolve().parent
DATA_PATH = MAP_DIR / "data" / "sample.csv"  # TODO: point at your file


def make_app(df: pd.DataFrame) -> Dash:
    categories = sorted_unique(df, "category") if "category" in df.columns else []

    app = Dash(
        __name__,
        external_stylesheets=[dbc.themes.FLATLY],
        title="MAP_NAME",
    )

    app.layout = dbc.Container(
        fluid=True,
        className="app-shell py-3",
        children=[
            html.Div("MAP_NAME", className="app-title h3 mb-0"),
            html.Div("Interactive dashboard template", className="muted mb-3"),
            dbc.Row(
                className="g-3",
                children=[
                    dbc.Col(
                        md=4,
                        lg=3,
                        children=dbc.Card(
                            className="card-tight shadow-sm sticky-sidebar",
                            children=dbc.CardBody(
                                [
                                    html.Div("Filters", className="fw-semibold mb-2"),
                                    dbc.Label("Search", className="mb-1"),
                                    dbc.Input(id="search-text", type="text", value="", placeholder="Search labels…"),
                                    html.Div(className="my-2"),
                                    dbc.Label("Category", className="mb-1"),
                                    dcc.Dropdown(
                                        id="category",
                                        options=[{"label": c, "value": c} for c in categories],
                                        value=[],
                                        multi=True,
                                        placeholder="All categories",
                                    ),
                                    html.Hr(className="my-3"),
                                    html.Div(id="kpi-rows", className="kpi"),
                                ]
                            ),
                        ),
                    ),
                    dbc.Col(
                        md=8,
                        lg=9,
                        children=[
                            dbc.Row(
                                className="g-3 mb-3",
                                children=[
                                    dbc.Col(
                                        dcc.Loading(
                                            type="circle",
                                            children=dcc.Graph(id="summary-bar"),
                                        ),
                                        md=6,
                                    ),
                                    dbc.Col(
                                        dcc.Loading(
                                            type="circle",
                                            children=dcc.Graph(id="detail-scatter"),
                                        ),
                                        md=6,
                                    ),
                                ],
                            ),
                            dbc.Card(
                                className="shadow-sm",
                                children=dbc.CardBody(
                                    [
                                        dbc.Button(
                                            "Download filtered CSV",
                                            id="download-csv-btn",
                                            color="primary",
                                            className="mb-2",
                                        ),
                                        dcc.Download(id="download-csv"),
                                        dcc.Loading(
                                            type="circle",
                                            children=DataTable(
                                                id="data-table",
                                                page_size=15,
                                                sort_action="native",
                                                filter_action="native",
                                                style_table={"overflowX": "auto"},
                                            ),
                                        ),
                                    ]
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
        Output("category", "value"),
        Input("summary-bar", "clickData"),
        Input("category", "value"),
        prevent_initial_call=True,
    )
    def _crossfilter_category(click_data, current_values):
        if not click_data:
            raise PreventUpdate
        points = click_data.get("points") or []
        if not points:
            raise PreventUpdate
        selected = points[0].get("x")
        if not isinstance(selected, str):
            raise PreventUpdate
        cur = list(current_values or [])
        if len(cur) == 1 and cur[0] == selected:
            return []
        return [selected]

    @app.callback(
        Output("summary-bar", "figure"),
        Output("detail-scatter", "figure"),
        Output("data-table", "data"),
        Output("data-table", "columns"),
        Output("kpi-rows", "children"),
        Output("filtered-store", "data"),
        Input("df-store", "data"),
        Input("category", "value"),
        Input("search-text", "value"),
    )
    def _update(records, category_values, search_text):
        base = pd.DataFrame.from_records(records)
        dff = filter_df(base, categories=category_values or None, search_text=search_text)

        table_data = dff.to_dict("records")
        table_cols = [{"name": c, "id": c} for c in dff.columns]
        kpi = html.Div(
            [
                html.Div(f"{len(dff):,}", className="kpi-value"),
                html.Div("Filtered rows", className="kpi-label"),
            ]
        )

        return (
            make_summary_bar(dff),
            make_detail_scatter(dff),
            table_data,
            table_cols,
            kpi,
            table_data,
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
        return dcc.send_data_frame(df_dl.to_csv, "MAP_NAME-filtered.csv", index=False)

    return app


def main() -> None:
    df = load_data(DATA_PATH)
    app = make_app(df)
    app.run(debug=True, host="127.0.0.1", port=8050)


if __name__ == "__main__":
    main()
