"""Plotly figure builder for the World Cup teams flight-path map.

Trace layout (important: the hover/click JavaScript in main.py relies on it):

    [0 .. N-1]      one "arcs" line trace per team   (hidden by default)
    [N .. 2N-1]     one "destinations" marker trace per team (hidden)
    [2N]            capitals marker trace (visible flags)
    [2N+1]          invisible enlarged targets at capitals (click / hover)
    [2N+2 ..]       confederation legend dummy traces

Clicking a capital, its flight paths, club dots, or the enlarged target toggles
that team (see main.py).
"""

from __future__ import annotations

import plotly.graph_objects as go

from data_processing import Team

# Confederation -> colour (matched by prefix so "CAF (playoff)" etc. still map).
CONFED_COLORS: dict[str, str] = {
    "UEFA": "#2563eb",
    "CONMEBOL": "#f59e0b",
    "CONCACAF": "#16a34a",
    "CAF": "#dc2626",
    "AFC": "#7c3aed",
    "OFC": "#0891b2",
}
DEFAULT_COLOR = "#475569"

OCEAN = "#0b1f3a"
LAND = "#13294b"
COASTLINE = "#2b4a7a"
COUNTRY_LINE = "#1f3a63"


def confed_color(confederation: str) -> str:
    for key, color in CONFED_COLORS.items():
        if confederation.startswith(key):
            return color
    return DEFAULT_COLOR


def _split_antimeridian(
    lats: list[float], lons: list[float]
) -> tuple[list[float | None], list[float | None]]:
    """Insert a None break where an arc wraps across the ±180° meridian.

    Great-circle longitudes returned by atan2 jump from ~+179 to ~-179 when the
    shortest path crosses the antimeridian; without a break Plotly would draw a
    long horizontal streak straight across the map.
    """
    out_lat: list[float | None] = []
    out_lon: list[float | None] = []
    for i, (la, lo) in enumerate(zip(lats, lons, strict=True)):
        if i and abs(lo - lons[i - 1]) > 180:
            out_lat.append(None)
            out_lon.append(None)
        out_lat.append(la)
        out_lon.append(lo)
    return out_lat, out_lon


def _players_label(players: list[tuple[str, str]]) -> str:
    return "<br>".join(f"{name} ({pos})" if pos else name for name, pos in players)


def _clubs_label(clubs: list[str]) -> str:
    return " / ".join(clubs)


def _arc_trace_data(
    team: Team,
) -> tuple[list[float | None], list[float | None], list[list[str] | None]]:
    """Lat/lon polyline plus per-point customdata for arc hover tooltips."""
    lats: list[float | None] = []
    lons: list[float | None] = []
    customdata: list[list[str] | None] = []
    for route in team.routes:
        plats, plons = _split_antimeridian(route.arc_lats, route.arc_lons)
        row = [
            _players_label(route.players),
            _clubs_label(route.clubs),
            route.stadium,
            f"{route.club_city}, {route.club_country}",
            f"{route.distance_km:,.0f}",
            team.capital,
            team.nation,
        ]
        for la, lo in zip(plats, plons, strict=True):
            lats.append(la)
            lons.append(lo)
            customdata.append(row)
        lats.append(None)
        lons.append(None)
        customdata.append(None)
    return lats, lons, customdata


def _destinations(team: Team) -> list[dict]:
    """One marker per destination route (all players at that stadium)."""
    return [
        {
            "lat": route.dest_lat,
            "lon": route.dest_lon,
            "club": _clubs_label(route.clubs),
            "stadium": route.stadium,
            "city": route.club_city,
            "country": route.club_country,
            "distance_km": route.distance_km,
            "players": _players_label(route.players),
        }
        for route in team.routes
    ]


def build_figure(tournament: str, teams: list[Team]) -> go.Figure:
    """Assemble the scattergeo figure with per-team arc + destination traces."""
    fig = go.Figure()
    n = len(teams)

    # 1) Arc traces (one per team), hidden until the capital is clicked.
    arc_hover = (
        "<b>%{customdata[1]}</b> — %{customdata[2]}<br>"
        "%{customdata[3]}<br>"
        "%{customdata[0]}<br>"
        "~%{customdata[4]} km from %{customdata[5]} (%{customdata[6]})"
        "<extra></extra>"
    )
    for team in teams:
        color = confed_color(team.confederation)
        lats, lons, customdata = _arc_trace_data(team)
        fig.add_trace(
            go.Scattergeo(
                lat=lats,
                lon=lons,
                mode="lines",
                line=dict(width=2, color=color),
                opacity=0.65,
                customdata=customdata,
                hovertemplate=arc_hover,
                hoverinfo="skip",  # enabled via JS when the team is selected (clicked)
                hoverlabel=dict(bgcolor="#1e293b", font=dict(color="#e2e8f0")),
                visible=False,
                showlegend=False,
                name=f"{team.nation} routes",
            )
        )

    # 2) Destination (club stadium) markers, one trace per team, hidden.
    for team in teams:
        color = confed_color(team.confederation)
        dests = _destinations(team)
        fig.add_trace(
            go.Scattergeo(
                lat=[d["lat"] for d in dests],
                lon=[d["lon"] for d in dests],
                mode="markers",
                marker=dict(
                    size=7,
                    color=color,
                    line=dict(width=1, color="white"),
                    symbol="circle",
                ),
                customdata=[
                    [
                        d["club"],
                        d["stadium"],
                        f"{d['city']}, {d['country']}",
                        "<br>".join(d["players"]),
                        f"{d['distance_km']:,.0f}",
                        team.nation,
                    ]
                    for d in dests
                ],
                hovertemplate=(
                    "<b>%{customdata[0]}</b> — %{customdata[1]}<br>"
                    "%{customdata[2]}<br>"
                    "<b>%{customdata[5]}</b>:<br>%{customdata[3]}<br>"
                    "~%{customdata[4]} km from capital<extra></extra>"
                ),
                hoverinfo="skip",  # enabled via JS when the team is selected (clicked)
                visible=False,
                showlegend=False,
                name=f"{team.nation} clubs",
            )
        )

    cap_customdata = [
        [t.nation, t.capital, t.confederation, t.n_players, t.n_destinations]
        for t in teams
    ]
    cap_hover = (
        "<b>%{customdata[0]}</b> %{text}<br>"
        "Capital: %{customdata[1]}<br>"
        "%{customdata[2]}<br>"
        "%{customdata[3]} players at %{customdata[4]} clubs"
        "<extra>click to show or hide flight paths</extra>"
    )

    # 3) Capitals (visible markers + flag labels).
    fig.add_trace(
        go.Scattergeo(
            lat=[t.lat for t in teams],
            lon=[t.lon for t in teams],
            mode="markers+text",
            text=[t.flag for t in teams],
            textfont=dict(size=15),
            textposition="top center",
            marker=dict(
                size=9,
                color=[confed_color(t.confederation) for t in teams],
                line=dict(width=1.4, color="white"),
                symbol="circle",
            ),
            hoverinfo="skip",
            showlegend=False,
            name="capitals",
        )
    )

    # 4) Invisible enlarged targets so clicks near the capital still register.
    fig.add_trace(
        go.Scattergeo(
            lat=[t.lat for t in teams],
            lon=[t.lon for t in teams],
            mode="markers",
            marker=dict(size=26, color="rgba(0,0,0,0)", line=dict(width=0)),
            customdata=cap_customdata,
            text=[t.flag for t in teams],
            hovertemplate=cap_hover,
            showlegend=False,
            name="capital-targets",
        )
    )

    # Confederation legend (dummy traces so colours are explained).
    for confed, color in CONFED_COLORS.items():
        fig.add_trace(
            go.Scattergeo(
                lat=[None],
                lon=[None],
                mode="markers",
                marker=dict(size=9, color=color),
                name=confed,
                showlegend=True,
                hoverinfo="skip",
            )
        )

    fig.update_geos(
        projection_type="natural earth",
        showland=True,
        landcolor=LAND,
        showocean=True,
        oceancolor=OCEAN,
        showcoastlines=True,
        coastlinecolor=COASTLINE,
        showcountries=True,
        countrycolor=COUNTRY_LINE,
        showframe=False,
        bgcolor="rgba(0,0,0,0)",
        lataxis_range=[-60, 85],
    )
    fig.update_layout(
        title=dict(
            text=(
                f"{tournament} — where the players play<br>"
                "<sup>Click a capital for flight paths · hover paths or clubs for "
                "player &amp; stadium · colour = confederation</sup>"
            ),
            x=0.5,
            xanchor="center",
            font=dict(color="#e2e8f0", size=20),
        ),
        paper_bgcolor="#0b1f3a",
        plot_bgcolor="#0b1f3a",
        font=dict(family="system-ui, -apple-system, Segoe UI, Roboto, sans-serif", color="#cbd5e1"),
        legend=dict(
            title=dict(text="Confederation", font=dict(color="#e2e8f0")),
            orientation="h",
            yanchor="bottom",
            y=-0.04,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(11,31,58,0.6)",
            font=dict(color="#cbd5e1"),
        ),
        margin=dict(l=0, r=0, t=70, b=30),
    )
    return fig
