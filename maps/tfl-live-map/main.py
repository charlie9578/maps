"""Dash entry point for tfl-live-map. Run from repo root: python maps/tfl-live-map/main.py"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
import time

import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Dash, Input, Output, State, dcc, html
from dash.dash_table import DataTable
from dash.exceptions import PreventUpdate

from data_processing import (
    MIN_ZERO_ETA_ANIM_SECS,
    TRAIN_MATCH_MAX_DEG,
    assign_stable_train_ids,
    build_vehicle_segments,
    filter_df,
    get_tfl_auth,
    interpolate_positions,
    load_live_arrivals,
    merge_line_segments,
    load_static_network,
    routes_from_store,
    routes_to_store,
    sorted_unique,
    stops_on_routes,
)
from viz import LINE_COLORS, make_map_base, make_summary_bar, make_time_to_station_hist

MAP_DIR = Path(__file__).resolve().parent

TFL_API_DOCS_URL = "https://api-portal.tfl.gov.uk/"
TFL_ARRIVALS_DOCS_URL = "https://api.tfl.gov.uk/swagger/ui/index.html#!/Line/Line_Arrivals"
ACCESSED_DATE = "2026-06-02"

# Client-side animation tick (ms). Does not hit the server.
ANIMATION_INTERVAL_MS = int(os.getenv("TFL_ANIMATION_MS", "500"))
# Full network refresh cycle (seconds); each line is fetched in turn over this period.
REFRESH_CYCLE_SECS = int(os.getenv("TFL_REFRESH_CYCLE_SECS", "30"))


def _format_dt_utc(dt: datetime | None) -> str:
    if not dt:
        return "—"
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _to_epoch(dt: datetime) -> float:
    return dt.timestamp()


def _snapshot_positions(
    segments_records: list[dict] | None,
    *,
    fetched_at_epoch: float | None,
    line_ids: list[str] | None,
    search_text: str | None,
) -> pd.DataFrame:
    seg = pd.DataFrame.from_records(segments_records or [])
    if seg.empty:
        return seg
    now = time.time()
    if "fetched_at_epoch" in seg.columns:
        elapsed = (now - seg["fetched_at_epoch"].astype(float)).clip(lower=0.0)
    else:
        elapsed = max(0.0, now - float(fetched_at_epoch or now))
    pos = interpolate_positions(seg, elapsed_s=elapsed)
    return filter_df(pos, line_ids=line_ids or None, search_text=search_text)


def _line_refresh_interval_ms(line_count: int) -> int:
    n = max(1, line_count)
    return max(1000, int(REFRESH_CYCLE_SECS * 1000 / n))


def make_app(
    *,
    stop_points: pd.DataFrame,
    routes: dict,
    initial_segments: pd.DataFrame,
    fetched_at: datetime,
) -> Dash:
    line_options = sorted_unique(initial_segments, "lineId") if "lineId" in initial_segments.columns else []
    all_line_ids = line_options or sorted(routes.keys())
    line_refresh_ms = _line_refresh_interval_ms(len(all_line_ids))
    initial_trains = (
        interpolate_positions(initial_segments, elapsed_s=0.0)
        if not initial_segments.empty
        else initial_segments
    )
    map_figure = make_map_base(
        routes=routes,
        stop_points=stops_on_routes(stop_points, routes),
        trains=initial_trains,
    )

    app = Dash(
        __name__,
        external_stylesheets=[dbc.themes.FLATLY],
        title="tfl-live-map",
    )

    source = html.Div(
        [
            html.Span("Data source: "),
            html.A("TfL Unified API", href=TFL_API_DOCS_URL, target="_blank", rel="noopener noreferrer"),
            html.Span(" · live trains: "),
            html.A(
                "GET /Line/{id}/Arrivals",
                href=TFL_ARRIVALS_DOCS_URL,
                target="_blank",
                rel="noopener noreferrer",
            ),
            html.Span(f" (accessed {ACCESSED_DATE})."),
        ],
        className="muted mb-2",
    )

    app.layout = dbc.Container(
        fluid=True,
        className="app-shell py-3",
        children=[
            html.Div("tfl-live-map", className="app-title h3 mb-0"),
            html.Div(
                "Live Tube trains — estimated positions from TfL predictions (not GPS); markers may jump when IDs recycle.",
                className="muted",
            ),
            source,
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
                                    dbc.Alert(
                                        id="error-alert",
                                        color="warning",
                                        is_open=False,
                                        className="py-2",
                                    ),
                                    html.Div(id="last-updated", className="muted mb-2"),
                                    dbc.Label("Search", className="mb-1"),
                                    dbc.Input(
                                        id="search-text",
                                        type="text",
                                        value="",
                                        placeholder="Vehicle ID contains…",
                                    ),
                                    html.Div(className="my-2"),
                                    dbc.Label("Lines", className="mb-1"),
                                    dcc.Dropdown(
                                        id="line-ids",
                                        options=[{"label": lid, "value": lid} for lid in line_options],
                                        value=line_options,
                                        multi=True,
                                        placeholder="All lines",
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
                                            children=dcc.Graph(id="tts-hist"),
                                        ),
                                        md=6,
                                    ),
                                ],
                            ),
                            dbc.Card(
                                className="shadow-sm mb-3",
                                children=dbc.CardBody(
                                    [
                                        dcc.Graph(
                                            id="live-map",
                                            figure=map_figure,
                                            config={"scrollZoom": True, "displayModeBar": False},
                                        ),
                                    ]
                                ),
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
            dcc.Interval(id="refresh-line", interval=line_refresh_ms, n_intervals=0),
            dcc.Interval(id="tick", interval=ANIMATION_INTERVAL_MS, n_intervals=0),
            dcc.Store(id="all-line-ids", data=all_line_ids),
            dcc.Store(id="refresh-line-index", data=0),
            dcc.Store(id="stop-points-store", data=stop_points.to_dict("records")),
            dcc.Store(id="routes-store", data=routes_to_store(routes)),
            dcc.Store(id="segments-store", data=initial_segments.to_dict("records")),
            dcc.Store(id="fetched-at-store", data=f"Last updated: {_format_dt_utc(fetched_at)}"),
            dcc.Store(id="filtered-store"),
            dcc.Store(id="animation-frame", data=0),
        ],
    )

    line_colors_json = json.dumps(LINE_COLORS)

    app.clientside_callback(
        f"""
        function(n, segments, lineIds, searchText) {{
            const LINE_COLORS = {line_colors_json};
            const MIN_ZERO_ETA = {MIN_ZERO_ETA_ANIM_SECS};
            const HANDOFF_MAX_DEG = {TRAIN_MATCH_MAX_DEG};
            const HANDOFF_MAX_D2 = HANDOFF_MAX_DEG * HANDOFF_MAX_DEG;
            const GHOST_TTL_S = 25;

            function plotDiv(graphId) {{
                const root = document.getElementById(graphId);
                if (!root) return null;
                if (root.data && Array.isArray(root.data)) return root;
                return root.querySelector(".js-plotly-plot") || null;
            }}

            function trainKey(s) {{
                return s.train_id || ((s.lineId || "") + ":" + (s.vehicleId || "") + ":0");
            }}

            function animDuration(tts) {{
                const t = Number(tts) || 0;
                return t <= 0 ? MIN_ZERO_ETA : t;
            }}

            function posAt(state, now) {{
                const duration = animDuration(state.initialTts);
                const elapsed = Math.max(0, now - state.anchorTime);
                const frac = Math.min(1, elapsed / duration);
                return {{
                    lat: (1 - frac) * state.startLat + frac * state.endLat,
                    lon: (1 - frac) * state.startLon + frac * state.endLon,
                    tts: Math.max(0, Math.round(duration - elapsed)),
                    frac,
                }};
            }}

            window.__tflTrainAnim = window.__tflTrainAnim || {{
                trains: {{}},
                lastPos: {{}},
                ghosts: {{}},
            }};
            const anim = window.__tflTrainAnim;
            const now = Date.now() / 1000;

            function segPos(s) {{
                return {{
                    lat: s.lat0 != null ? s.lat0 : s.lat1,
                    lon: s.lon0 != null ? s.lon0 : s.lon1,
                }};
            }}

            function dist2(a, b) {{
                return (a.lat - b.lat) ** 2 + (a.lon - b.lon) ** 2;
            }}

            const lineSet = new Set(lineIds || []);
            const searchQ = (searchText || "").trim().toLowerCase();

            function visibleSegments() {{
                const out = [];
                for (const s of (segments || [])) {{
                    if (lineSet.size && !lineSet.has(s.lineId)) continue;
                    const vid = (s.vehicleId || "").toLowerCase();
                    if (searchQ && !vid.includes(searchQ)) continue;
                    out.push(s);
                }}
                return out;
            }}

            const gd = plotDiv("live-map");
            if (!gd || !gd.data || !Array.isArray(gd.data)) return n;

            const trainIdx = gd.data.findIndex((t) => t.name === "trains");
            if (trainIdx < 0) return n;

            const activeKeys = new Set();
            const visible = visibleSegments();

            for (const s of visible) {{
                activeKeys.add(trainKey(s));
            }}

            // If server train_id changed, hand off animation state from the nearest orphan (same line + vehicleId).
            for (const s of visible) {{
                const key = trainKey(s);
                if (anim.trains[key]) continue;

                const target = segPos(s);
                let bestKey = null;
                let bestD = Infinity;
                for (const [oldKey, state] of Object.entries(anim.trains)) {{
                    if (activeKeys.has(oldKey) || oldKey === key) continue;
                    if (state.lineId !== s.lineId || state.vehicleId !== s.vehicleId) continue;
                    const lp = anim.lastPos[oldKey];
                    if (!lp) continue;
                    const d = dist2(lp, target);
                    if (d < bestD) {{
                        bestD = d;
                        bestKey = oldKey;
                    }}
                }}
                if (bestKey && bestD <= HANDOFF_MAX_D2) {{
                    anim.trains[key] = anim.trains[bestKey];
                    anim.lastPos[key] = anim.lastPos[bestKey];
                    delete anim.trains[bestKey];
                    delete anim.lastPos[bestKey];
                    delete anim.ghosts[bestKey];
                }}
            }}

            for (const s of visible) {{
                const key = trainKey(s);
                const dataTime = Number(s.fetched_at_epoch);
                const hasDataTime = Number.isFinite(dataTime);
                const prev = anim.trains[key];
                const dataRefresh = !prev || (hasDataTime && prev.dataTime !== dataTime);

                if (dataRefresh) {{
                    let startLat;
                    let startLon;
                    if (prev) {{
                        const p = posAt(prev, now);
                        startLat = p.lat;
                        startLon = p.lon;
                    }} else if (anim.lastPos[key]) {{
                        startLat = anim.lastPos[key].lat;
                        startLon = anim.lastPos[key].lon;
                    }} else {{
                        const p = segPos(s);
                        startLat = p.lat;
                        startLon = p.lon;
                    }}

                    anim.trains[key] = {{
                        startLat,
                        startLon,
                        endLat: s.lat1,
                        endLon: s.lon1,
                        anchorTime: now,
                        dataTime: hasDataTime ? dataTime : now,
                        initialTts: Number(s.tts1_s) || 0,
                        nextNaptan: s.naptanId_1 || "",
                        vehicleId: s.vehicleId || "",
                        lineId: s.lineId || "",
                        towards: s.towards_1 || "",
                        station0: s.stationName_0 || "",
                        station1: s.stationName_1 || "",
                        direction: s.direction_norm || s.direction || "unknown",
                        currentLocation: s.currentLocation || "",
                    }};
                }} else if (prev) {{
                    prev.towards = s.towards_1 || prev.towards;
                    prev.station0 = s.stationName_0 || prev.station0;
                    prev.station1 = s.stationName_1 || prev.station1;
                    prev.direction = s.direction_norm || s.direction || prev.direction;
                    prev.currentLocation = s.currentLocation || prev.currentLocation;
                }}
            }}

            for (const key of Object.keys(anim.trains)) {{
                if (!activeKeys.has(key)) {{
                    anim.ghosts[key] = now;
                }} else {{
                    delete anim.ghosts[key];
                }}
            }}
            for (const key of Object.keys(anim.ghosts)) {{
                if (now - anim.ghosts[key] > GHOST_TTL_S) {{
                    delete anim.trains[key];
                    delete anim.lastPos[key];
                    delete anim.ghosts[key];
                }}
            }}

            const lats = [];
            const lons = [];
            const colors = [];
            const custom = [];

            for (const s of (segments || [])) {{
                if (lineSet.size && !lineSet.has(s.lineId)) continue;
                const vid = (s.vehicleId || "").toLowerCase();
                if (searchQ && !vid.includes(searchQ)) continue;

                const key = trainKey(s);
                const state = anim.trains[key];
                if (!state) continue;

                const p = posAt(state, now);
                lats.push(p.lat);
                lons.push(p.lon);
                anim.lastPos[key] = {{ lat: p.lat, lon: p.lon }};
                colors.push(LINE_COLORS[s.lineId] || "#444444");
                custom.push([
                    state.vehicleId,
                    state.lineId,
                    state.towards,
                    state.station0,
                    state.station1,
                    p.tts,
                    Math.max(0, Math.round(now - (state.dataTime || state.anchorTime || now))),
                    state.direction || "unknown",
                    state.currentLocation || "",
                ]);
            }}

            if (!window.Plotly) return n;

            window.Plotly.restyle(
                gd,
                {{
                    lat: [lats],
                    lon: [lons],
                    "marker.color": [colors.length ? colors : "#2563eb"],
                    customdata: [custom],
                }},
                [trainIdx]
            );
            return n;
        }}
        """,
        Output("animation-frame", "data"),
        Input("tick", "n_intervals"),
        Input("segments-store", "data"),
        Input("line-ids", "value"),
        Input("search-text", "value"),
    )

    @app.callback(
        Output("line-ids", "value"),
        Input("summary-bar", "clickData"),
        Input("line-ids", "value"),
        prevent_initial_call=True,
    )
    def _crossfilter_line(click_data, current_values):
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
            return cur
        if selected in cur and len(cur) > 1:
            cur.remove(selected)
            return cur
        return [selected]

    @app.callback(
        Output("segments-store", "data"),
        Output("refresh-line-index", "data"),
        Output("fetched-at-store", "data"),
        Output("error-alert", "children"),
        Output("error-alert", "is_open"),
        Input("refresh-line", "n_intervals"),
        State("refresh-line-index", "data"),
        State("all-line-ids", "data"),
        State("segments-store", "data"),
        State("stop-points-store", "data"),
        State("routes-store", "data"),
        prevent_initial_call=True,
    )
    def _refresh_one_line(_n, line_index, all_line_ids, segments_records, stop_records, routes_data):
        auth = get_tfl_auth()
        line_ids = list(all_line_ids or [])
        if not line_ids:
            raise PreventUpdate

        idx = int(line_index or 0) % len(line_ids)
        line_id = line_ids[idx]

        try:
            arrivals, fetched_at = load_live_arrivals(auth=auth, line_ids=[line_id])
            stop_df = pd.DataFrame.from_records(stop_records or [])
            routes = routes_from_store(routes_data or {})
            new_seg = build_vehicle_segments(arrivals, stop_points=stop_df, routes=routes)
            existing = pd.DataFrame.from_records(segments_records or [])
            prev_line = (
                existing[existing["lineId"].astype(str) == str(line_id)]
                if not existing.empty
                else pd.DataFrame()
            )
            new_seg = assign_stable_train_ids(new_seg, previous=prev_line)
            if not new_seg.empty:
                new_seg = new_seg.copy()
                new_seg["fetched_at_epoch"] = _to_epoch(fetched_at)

            merged = merge_line_segments(existing, new_seg, line_id=line_id)

            status = f"Last updated: {_format_dt_utc(fetched_at)} · {line_id}"
            return (
                merged.to_dict("records"),
                (idx + 1) % len(line_ids),
                status,
                "",
                False,
            )
        except Exception as e:
            return dash.no_update, dash.no_update, dash.no_update, f"Refresh failed ({line_id}): {e}", True

    @app.callback(
        Output("summary-bar", "figure"),
        Output("tts-hist", "figure"),
        Output("data-table", "data"),
        Output("data-table", "columns"),
        Output("kpi-rows", "children"),
        Output("filtered-store", "data"),
        Output("last-updated", "children"),
        Input("segments-store", "data"),
        Input("line-ids", "value"),
        Input("search-text", "value"),
        State("fetched-at-store", "data"),
    )
    def _update_dashboard(segments_records, line_ids, search_text, fetched_at_text):
        dff = _snapshot_positions(
            segments_records,
            fetched_at_epoch=None,
            line_ids=line_ids,
            search_text=search_text,
        )

        table_data = dff.to_dict("records")
        table_cols = [{"name": c, "id": c} for c in dff.columns]
        kpi = html.Div(
            [
                html.Div(f"{len(dff):,}", className="kpi-value"),
                html.Div("Trains (filtered)", className="kpi-label"),
            ]
        )

        return (
            make_summary_bar(dff),
            make_time_to_station_hist(dff),
            table_data,
            table_cols,
            kpi,
            table_data,
            fetched_at_text or "Last updated: —",
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
        return dcc.send_data_frame(df_dl.to_csv, "tfl-live-map-filtered.csv", index=False)

    return app


def main() -> None:
    auth = get_tfl_auth()
    stop_points, routes, line_ids = load_static_network(auth=auth)

    arrivals, fetched_at = load_live_arrivals(auth=auth, line_ids=line_ids)
    initial_segments = build_vehicle_segments(arrivals, stop_points=stop_points, routes=routes)
    initial_segments = assign_stable_train_ids(initial_segments)
    if not initial_segments.empty:
        initial_segments = initial_segments.copy()
        initial_segments["fetched_at_epoch"] = _to_epoch(fetched_at)

    app = make_app(stop_points=stop_points, routes=routes, initial_segments=initial_segments, fetched_at=fetched_at)
    port = int(os.getenv("PORT", "8051"))
    debug = os.getenv("DASH_DEBUG", "").strip().lower() in {"1", "true", "yes"}
    app.run(debug=debug, host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()
