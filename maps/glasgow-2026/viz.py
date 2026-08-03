"""The Commonwealth Tartan: a woven view of Glasgow 2026 medals by sport."""

from __future__ import annotations

import base64
import io
import math

import plotly.graph_objects as go
from PIL import Image

from data_processing import MAP_DIR, Team, flag_url, load_sport_medals

MEDAL_COLOURS = {"gold": "#f6c453", "silver": "#d9e1e8", "bronze": "#c77d4a"}
REGION_COLOURS = {
    "Africa": "#ffb0a4", "Americas & Caribbean": "#ffdb57", "Asia": "#caff74",
    "Europe": "#70e2ff", "Oceania": "#d8b4ff",
}
TARTAN_BG = "#d92b78"
REGIONS = {
    "Africa": set("BOT CMR SWZ GAB GHA KEN LES MAW MRI MOZ NAM NGR RWA SEY SLE RSA SHN TZA GAM TOG UGA ZAM".split()),
    "Americas & Caribbean": set("AIA ANT BAR BIZ BER CAN CAY DMA FLK GRN GUY IVB JAM LCA MNT SKN VIN BAH TTO TCA".split()),
    "Asia": set("BAN BRU IND MAS MDV PAK SGP SRI".split()),
    "Europe": set("CYP ENG GIB GGY IOM JEY MLT NIR SCO WAL".split()),
    "Oceania": set("AUS COK FIJ KIR NRU NZL NIU NFK PNG SAM SOL TGA TUV VAN".split()),
}


def region_for(code: str) -> str:
    for region, codes in REGIONS.items():
        if code in codes:
            return region
    raise KeyError(f"No region assigned for {code}")


def _team_hover(team: Team) -> str:
    medal_line = (
        f"<span style='color:{MEDAL_COLOURS['gold']}'>●</span> {team.gold} gold &nbsp;"
        f"<span style='color:{MEDAL_COLOURS['silver']}'>●</span> {team.silver} silver &nbsp;"
        f"<span style='color:{MEDAL_COLOURS['bronze']}'>●</span> {team.bronze} bronze"
        if team.total else "No medals"
    )
    return f"<b>{team.name}</b> · {team.code}<br>{region_for(team.code)}<br>{medal_line}<br><b>{team.total} total</b>"


def _rgba(hex_colour: str, alpha: float) -> str:
    value = hex_colour.removeprefix("#")
    red, green, blue = (int(value[index:index + 2], 16) for index in (0, 2, 4))
    return f"rgba({red},{green},{blue},{alpha})"


def _asset_uri(filename: str) -> str:
    with Image.open(MAP_DIR / "data" / filename) as source:
        image = source.convert("RGBA")
        bounds = image.getchannel("A").getbbox()
        if bounds:
            image = image.crop(bounds)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG", optimize=True)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def build_figure(raw: dict, teams: list[Team]) -> tuple[go.Figure, dict[str, list[int]], int]:
    sports, sport_medals = load_sport_medals(teams)
    ordered = sorted(teams, key=lambda team: team.name)
    y_by_code = {team.code: len(ordered) - 1 - index for index, team in enumerate(ordered)}
    sport_x = {sport_id: index for index, (sport_id, _, _) in enumerate(sports)}

    fig = go.Figure()
    thread_indices: dict[str, list[int]] = {}

    medal_names = ("gold", "silver", "bronze")
    medal_offsets = {"gold": -0.20, "silver": 0.0, "bronze": 0.20}

    # Each medal is a continuous violin-shaped thread. This complete profile is
    # drawn first, below the country warp; positive crossings are redrawn later.
    teams_bottom_up = list(reversed(ordered))
    for sport_index, (sport_id, sport_name, date_label) in enumerate(sports):
        for medal_index, medal in enumerate(medal_names):
            centre = sport_index + medal_offsets[medal]
            ys = [y_by_code[team.code] for team in teams_bottom_up]
            widths: list[float] = []
            for team in teams_bottom_up:
                count = sport_medals.get((team.code, sport_id), (0, 0, 0))[medal_index]
                widths.append(0.012 if count == 0 else min(0.105, 0.024 + 0.013 * math.sqrt(count)))
            polygon_x = [centre - width for width in widths] + [centre + width for width in reversed(widths)]
            polygon_y = ys + list(reversed(ys))
            fig.add_trace(go.Scatter(
                x=polygon_x, y=polygon_y, mode="lines", fill="toself",
                fillcolor=_rgba(MEDAL_COLOURS[medal], 0.24),
                line={"color": _rgba(MEDAL_COLOURS[medal], 0.48), "width": 1.5, "shape": "spline", "smoothing": 0.75},
                hoverinfo="skip", showlegend=False,
                meta={"kind": "violin-under", "sport": sport_id, "medal": medal},
            ))

    # Equal-width, straight country warp. It covers all zero-value medal crossings.
    for index, team in enumerate(ordered):
        y = y_by_code[team.code]
        xs = [-0.72, 10.58]
        ys = [y, y]
        colour = REGION_COLOURS[region_for(team.code)]
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines", line={"color": colour, "width": 5.5},
            opacity=0.76, hovertemplate=_team_hover(team) + "<extra></extra>",
            showlegend=False, meta={"kind": "thread", "code": team.code, "medallist": bool(team.total)},
        ))
        thread_indices[team.code] = [len(fig.data) - 1]

    # The ISO rail mirrors the flags on the opposite edge and remains clickable.
    fig.add_trace(go.Scatter(
        x=[10.70] * len(ordered), y=[y_by_code[team.code] for team in ordered], mode="markers+text",
        marker={"size": 20, "color": "rgba(0,0,0,0)"},
        text=[team.code for team in ordered], textposition="middle right",
        textfont={"size": 9, "color": "#fff5fa"},
        hovertext=[_team_hover(team) for team in ordered],
        customdata=[[team.code, int(bool(team.total))] for team in ordered],
        hovertemplate="%{hovertext}<extra></extra>", showlegend=False, meta={"kind": "teams"},
    ))
    marker_index = len(fig.data) - 1

    # Only positive portions of each violin return above the country warp. Runs
    # taper into the under-thread, avoiding separate blocks beside the profile.
    for sport_index, (sport_id, _, _) in enumerate(sports):
        for medal_index, medal in enumerate(medal_names):
            centre = sport_index + medal_offsets[medal]
            counts = [sport_medals.get((team.code, sport_id), (0, 0, 0))[medal_index] for team in teams_bottom_up]
            widths = [min(0.105, 0.024 + 0.013 * math.sqrt(count)) if count else 0.012 for count in counts]
            ys = [y_by_code[team.code] for team in teams_bottom_up]
            polygon_x: list[float | None] = []
            polygon_y: list[float | None] = []
            run_start = 0
            while run_start < len(counts):
                if counts[run_start] == 0:
                    run_start += 1
                    continue
                run_end = run_start
                while run_end + 1 < len(counts) and counts[run_end + 1] > 0:
                    run_end += 1
                run_ys = [ys[run_start] - 0.46, *ys[run_start:run_end + 1], ys[run_end] + 0.46]
                run_widths = [0.012, *widths[run_start:run_end + 1], 0.012]
                polygon_x.extend(
                    [centre - width for width in run_widths]
                    + [centre + width for width in reversed(run_widths)]
                    + [None]
                )
                polygon_y.extend(run_ys + list(reversed(run_ys)) + [None])
                run_start = run_end + 1
            fig.add_trace(go.Scatter(
                x=polygon_x, y=polygon_y, mode="lines", fill="toself",
                fillcolor=_rgba(MEDAL_COLOURS[medal], 0.92),
                line={"color": MEDAL_COLOURS[medal], "width": 1.5, "shape": "spline", "smoothing": 0.75},
                hoverinfo="skip", showlegend=False,
                meta={"kind": "violin-over", "sport": sport_id, "medal": medal},
            ))

    # Transparent hit areas retain exact hover and click interaction without
    # adding a second visible medal mark alongside the violins.
    for medal_index, medal in enumerate(medal_names):
        x_values: list[float] = []
        y_values: list[float] = []
        hover: list[str] = []
        customdata: list[list[str | int]] = []
        for team in ordered:
            for sport_id, sport_name, date_label in sports:
                counts = sport_medals.get((team.code, sport_id), (0, 0, 0))
                count = counts[medal_index]
                if not count:
                    continue
                x_values.append(sport_x[sport_id] + medal_offsets[medal])
                y_values.append(y_by_code[team.code])
                hover.append(
                    f"<b>{team.name}</b> · {sport_name}<br>"
                    f"{counts[0]} gold · {counts[1]} silver · {counts[2]} bronze"
                )
                customdata.append([team.code, sport_id, counts[0], counts[1], counts[2]])
        fig.add_trace(go.Scatter(
            x=x_values, y=y_values, mode="markers", name=medal.title(),
            marker={"size": 16, "color": "rgba(0,0,0,0)"}, showlegend=False,
            hovertext=hover, customdata=customdata,
            hovertemplate="%{hovertext}<extra></extra>", meta={"kind": "stitches", "medal": medal},
        ))

    annotations: list[dict] = []
    annotations.extend({
        "x": index, "y": -1.05, "text": f"<b>{sport_name}</b>", "textangle": -45,
        "showarrow": False, "font": {"size": 10, "color": "#dbe7ec"},
        "xanchor": "right", "yanchor": "top",
    } for index, (_, sport_name, _) in enumerate(sports))

    sport_assets = {
        "powerlifting": "FINNIE-POSES-9-16_POWERLIFTING.png",
        "artistic_gymnastics": "FINNIE-POSES-9-16_ARTISTIC-GYMNASTICS.png",
        "swimming": "FINNIE-POSES-9-16_SWIMMING.png",
        "weightlifting": "FINNIE-POSES-9-16_WEIGHTLIFTING.png",
        "athletics": "FINNIE-POSES-9-16_ATHLETICS.png",
        "bowls": "FINNIE-POSES-9-16_BOWLS.png",
        "3x3_basketball": "FINNIE-POSES-9-16_WHEELCHAIR-BASKETBALL.png",
        "cycling": "FINNIE-POSES-9-16_TRACK-CYCLING.png",
        "judo": "FINNIE-POSES-9-16_JUDO.png",
        "boxing": "FINNIE-POSES-9-16_BOXING.png",
        "netball": "FINNIE-POSES-9-16_NETBALL.png",
    }

    for index, (sport_id, sport_name, _) in enumerate(sports):
        if sport_id not in sport_assets:
            annotations.append({
                "x": index, "y": 76.3, "text": f"<b>{sport_name.upper()}</b>", "showarrow": False,
                "font": {"size": 10, "color": "#e9f3f6"}, "bgcolor": "#102a36",
                "bordercolor": "#4e7482", "borderwidth": 1, "borderpad": 7,
            })

    fig.add_trace(go.Scatter(
        x=list(range(len(sports))), y=[76.3] * len(sports), mode="markers",
        marker={"size": 48, "color": "rgba(0,0,0,0)"},
        hovertext=[name for _, name, _ in sports],
        hovertemplate="<b>%{hovertext}</b><extra></extra>", showlegend=False,
        meta={"kind": "sport-icons"},
    ))

    flag_images = [{
        "source": flag_url(team.code), "xref": "x", "yref": "y", "x": -0.98, "y": y_by_code[team.code],
        "sizex": 0.30, "sizey": 0.64, "xanchor": "center", "yanchor": "middle",
        "sizing": "contain", "opacity": 1, "layer": "above",
    } for team in ordered]
    sport_images = [{
        "source": _asset_uri(sport_assets[sport_id]), "xref": "x", "yref": "y",
        "x": index, "y": 76.3, "sizex": 0.68, "sizey": 5.7,
        "xanchor": "center", "yanchor": "middle", "sizing": "contain", "opacity": 1, "layer": "above",
    } for index, (sport_id, _, _) in enumerate(sports) if sport_id in sport_assets]

    fig.update_layout(
        paper_bgcolor="#07151d", plot_bgcolor="#07151d",
        font={"family": "Inter, system-ui, sans-serif", "color": "#dbe7ec"},
        margin={"l": 8, "r": 8, "t": 18, "b": 48}, height=1120,
        xaxis={"range": [-1.22, 11.18], "visible": False, "fixedrange": True},
        yaxis={"range": [-4.2, 79.2], "visible": False, "fixedrange": True},
        shapes=[{
            "type": "rect", "x0": -0.74, "x1": 10.60, "y0": -0.48, "y1": len(ordered) - 0.52,
            "fillcolor": TARTAN_BG, "line": {"color": "#ef5a9b", "width": 1}, "layer": "below",
        }],
        annotations=annotations, images=flag_images + sport_images,
        showlegend=False,
        hovermode="closest",
        hoverlabel={"bgcolor": "#102a36", "bordercolor": "#4e7482", "font": {"color": "white", "size": 13}},
        uirevision="glasgow-2026-tartan", dragmode=False,
    )
    return fig, thread_indices, marker_index
