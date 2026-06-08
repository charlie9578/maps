"""Plotly figure builder for the World Cup teams flight-path map.

Trace layout (indices passed to main.py via ``trace_layout``):

    arcs → clubs → capital dots → capital targets → legend →
    **flag labels → flag targets** (topmost; wins clicks over paths/clubs)

Flight paths are not clickable — only club and capital markers toggle arcs.
"""

from __future__ import annotations

from datetime import date

import plotly.graph_objects as go

from data_processing import DestinationRoute, Team

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

STADIUM_MARKER_SIZE = 8
STADIUM_MARKER_COLOR = "#94a3b8"


def confed_key(confederation: str) -> str:
    for key in CONFED_COLORS:
        if confederation.startswith(key):
            return key
    return "OTHER"


def confed_color(confederation: str) -> str:
    for key, color in CONFED_COLORS.items():
        if confederation.startswith(key):
            return color
    return DEFAULT_COLOR


def _format_dob(iso: str | None) -> str | None:
    if not iso:
        return None
    try:
        d = date.fromisoformat(iso)
    except ValueError:
        return iso
    return f"b. {d.day} {d.strftime('%b %Y')}"


def _player_line_bits(
    no: int | None,
    name: str,
    pos: str,
    dob: str | None,
    age: int | None,
    caps: int | None,
    goals: int | None,
    *,
    club: str | None = None,
) -> str:
    bits: list[str] = []
    if no is not None:
        bits.append(f"#{no}")
    bits.append(name)
    if pos:
        bits.append(pos)
    dob_label = _format_dob(dob)
    if dob_label:
        bits.append(dob_label)
    if age is not None:
        bits.append(f"age {age}")
    if caps is not None:
        bits.append(f"{caps} caps")
    if goals is not None:
        bits.append(f"{goals} goals")
    if club:
        bits.append(club)
    return " · ".join(bits)


def _players_label(
    players: list[tuple[int | None, str, str, str | None, int | None, int | None, int | None]],
) -> str:
    lines = [
        _player_line_bits(no, name, pos, dob, age, caps, goals)
        for no, name, pos, dob, age, caps, goals in players
    ]
    return "<br>".join(lines)


def _squad_label(
    players: list[
        tuple[int | None, str, str, str | None, int | None, int | None, int | None, str]
    ],
) -> str:
    lines = [
        _player_line_bits(no, name, pos, dob, age, caps, goals, club=club)
        for no, name, pos, dob, age, caps, goals, club in players
    ]
    return "<br>".join(lines)


def _clubs_label(clubs: list[str]) -> str:
    return " / ".join(clubs)


def _route_arc_trace_data(
    team: Team,
    route: DestinationRoute,
) -> tuple[list[float | None], list[float | None], list[list[str]]]:
    """One capital → club arc with per-point hover rows."""
    row = [
        _players_label(route.players),
        _clubs_label(route.clubs),
        route.stadium,
        f"{route.club_city}, {route.club_country}",
        f"{route.distance_km:,.0f}",
        team.capital,
        team.nation,
    ]
    customdata = [row for _ in route.arc_lats]
    return list(route.arc_lats), list(route.arc_lons), customdata


def build_route_meta(teams: list[Team], stadium_sites: list[dict]) -> list[dict]:
    """Map each arc trace index to its team and stadium indices (for JS toggling)."""
    site_index = {
        _stadium_key(site["lat"], site["lon"]): idx for idx, site in enumerate(stadium_sites)
    }
    meta: list[dict] = []
    for team_idx, team in enumerate(teams):
        for route in team.routes:
            stadium_idx = site_index[_stadium_key(route.dest_lat, route.dest_lon)]
            meta.append(
                {
                    "team": team_idx,
                    "stadium": stadium_idx,
                    "confed": confed_key(team.confederation),
                }
            )
    return meta


def _stadium_hover_row(site: dict) -> list[str]:
    """Static hover payload for a club marker (all nations at that ground)."""
    squads = sorted(site["squads"], key=lambda sq: sq["nation"])
    clubs_seen: list[str] = []
    for sq in squads:
        for club in sq["club"].split(" / "):
            if club not in clubs_seen:
                clubs_seen.append(club)
    nations_html = "<br><br>".join(
        f"<b>{sq['nation']}</b> (~{sq['distance_km']:,.0f} km to {sq['capital']}):<br>{sq['players']}"
        for sq in squads
    )
    return [
        " / ".join(clubs_seen),
        site["stadium"],
        site["location"],
        nations_html,
    ]


def _stadium_key(lat: float, lon: float) -> tuple[float, float]:
    return round(lat, 4), round(lon, 4)


def aggregate_stadium_sites(teams: list[Team]) -> list[dict]:
    """One entry per stadium location; squads hold per-nation data for JS hover filtering."""
    grouped: dict[tuple[float, float], dict] = {}
    for team_index, team in enumerate(teams):
        for route in team.routes:
            key = _stadium_key(route.dest_lat, route.dest_lon)
            entry = grouped.get(key)
            if entry is None:
                entry = {
                    "lat": route.dest_lat,
                    "lon": route.dest_lon,
                    "stadium": route.stadium,
                    "location": f"{route.club_city}, {route.club_country}",
                    "squads": [],
                    "team_indices": set(),
                }
                grouped[key] = entry
            entry["team_indices"].add(team_index)
            entry["squads"].append(
                {
                    "team": team_index,
                    "nation": team.nation,
                    "capital": team.capital,
                    "distance_km": route.distance_km,
                    "club": _clubs_label(route.clubs),
                    "players": _players_label(route.players),
                }
            )

    sites: list[dict] = []
    for entry in grouped.values():
        sites.append(
            {
                "lat": entry["lat"],
                "lon": entry["lon"],
                "teams": sorted(entry["team_indices"]),
                "stadium": entry["stadium"],
                "location": entry["location"],
                "squads": entry["squads"],
            }
        )
    sites.sort(key=lambda s: (s["lat"], s["lon"]))
    return sites


def build_figure(
    tournament: str,
    teams: list[Team],
    *,
    embedded: bool = False,
) -> tuple[go.Figure, list[dict], list[dict], dict[str, int | dict[str, int]]]:
    """Assemble the scattergeo figure; return sites, route meta, and trace indices."""
    fig = go.Figure()
    stadium_sites = aggregate_stadium_sites(teams)
    route_meta = build_route_meta(teams, stadium_sites)
    trace_idx = 0

    stadium_hover = (
        "<b>%{customdata[0]}</b><br>"
        "%{customdata[1]}<br>"
        "%{customdata[2]}<br><br>"
        "%{customdata[3]}"
        "<extra></extra>"
    )

    # 1) One arc per capital↔club link (shown when either endpoint is selected).
    for team in teams:
        color = confed_color(team.confederation)
        for route in team.routes:
            lats, lons, _customdata = _route_arc_trace_data(team, route)
            fig.add_trace(
                go.Scattergeo(
                    lat=lats,
                    lon=lons,
                    mode="lines",
                    line=dict(width=2, color=color),
                    opacity=0.65,
                    hoverinfo="skip",
                    visible=False,
                    showlegend=False,
                    name=f"{team.nation} → {_clubs_label(route.clubs)}",
                )
            )
            trace_idx += 1

    layout: dict[str, int] = {}
    layout["club"] = trace_idx
    # 2) Club markers (always visible; single trace — a transparent hit layer
    #    duplicated every point and still rendered in Scattergeo).
    fig.add_trace(
        go.Scattergeo(
            lat=[s["lat"] for s in stadium_sites],
            lon=[s["lon"] for s in stadium_sites],
            mode="markers",
            marker=dict(
                size=STADIUM_MARKER_SIZE,
                color=STADIUM_MARKER_COLOR,
                line=dict(width=1, color="white"),
                symbol="circle",
            ),
            customdata=[_stadium_hover_row(s) for s in stadium_sites],
            hovertemplate=stadium_hover,
            hoverlabel=dict(bgcolor="#1e293b", font=dict(color="#e2e8f0")),
            showlegend=False,
            name="clubs",
        )
    )
    trace_idx += 1

    cap_customdata = [
        [
            t.nation,
            t.capital,
            t.confederation,
            t.n_players,
            t.n_destinations,
            _squad_label(t.squad),
        ]
        for t in teams
    ]
    cap_hover = (
        "<b>%{customdata[0]}</b> %{text}<br>"
        "Capital: %{customdata[1]}<br>"
        "%{customdata[2]}<br>"
        "%{customdata[3]} players at %{customdata[4]} clubs<br><br>"
        "<b>Squad</b><br>"
        "%{customdata[5]}"
        "<extra></extra>"
    )

    layout["cap"] = trace_idx
    # Capital dots (confederation colour; flags drawn in a later top layer).
    fig.add_trace(
        go.Scattergeo(
            lat=[t.lat for t in teams],
            lon=[t.lon for t in teams],
            mode="markers",
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
    trace_idx += 1

    layout["capHit"] = trace_idx
    # Invisible enlarged targets at capitals (easier clicks near the dot).
    fig.add_trace(
        go.Scattergeo(
            lat=[t.lat for t in teams],
            lon=[t.lon for t in teams],
            mode="markers",
            marker=dict(size=26, color="rgba(0,0,0,0)", opacity=0, line=dict(width=0)),
            hoverinfo="skip",
            showlegend=False,
            name="capital-targets",
        )
    )
    trace_idx += 1

    layout["legend"] = {}
    for confed, color in CONFED_COLORS.items():
        layout["legend"][confed] = trace_idx
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
        trace_idx += 1

    layout["flag"] = trace_idx
    # Flag labels on the top layer so they trump clubs and flight paths.
    fig.add_trace(
        go.Scattergeo(
            lat=[t.lat for t in teams],
            lon=[t.lon for t in teams],
            mode="text",
            text=[t.flag for t in teams],
            textfont=dict(size=16),
            textposition="top center",
            customdata=cap_customdata,
            hovertemplate=cap_hover,
            hoverlabel=dict(bgcolor="#1e293b", font=dict(color="#e2e8f0")),
            showlegend=False,
            name="flags",
        )
    )
    trace_idx += 1

    layout["flagHit"] = trace_idx
    # Invisible targets over flags (topmost trace — highest click priority).
    fig.add_trace(
        go.Scattergeo(
            lat=[t.lat for t in teams],
            lon=[t.lon for t in teams],
            mode="markers",
            marker=dict(size=30, color="rgba(0,0,0,0)", opacity=0, line=dict(width=0)),
            customdata=cap_customdata,
            text=[t.flag for t in teams],
            hovertemplate=cap_hover,
            showlegend=False,
            name="flag-targets",
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
    if embedded:
        subtitle = (
            "Legend: toggle confederation paths · click clubs and capitals to reveal routes"
        )
    else:
        subtitle = (
            "Legend: toggle confederation paths (click capitals to hide individuals) · "
            "click a club or capital when no group is active · Show/Hide all (top left)"
        )
    fig.update_layout(
        title=dict(
            text=f"{tournament} — where the players play<br><sup>{subtitle}</sup>",
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
    return fig, stadium_sites, route_meta, layout
