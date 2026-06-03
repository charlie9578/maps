"""World Cup teams flight-path map. Run from repo root:

    python maps/world-cup-teams-map/main.py

Plots each qualified nation at its capital city. Click a capital to reveal
curved great-circle "flight paths" to the clubs where that squad's players play.

Data is curated/committed JSON (see README and data/*.json for sourcing).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from data_processing import build_teams
from viz import build_figure

MAP_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = MAP_DIR / "output"
OUTPUT_HTML = OUTPUT_DIR / "world_cup_teams_map.html"

# Injected after the Plotly chart loads. Trace indices must match viz.py layout.
CLICK_SCRIPT = """
var gd = document.getElementById('{plot_id}');
var N = __N__;
var stadiumIdx = N;            // shared stadium markers
var capIdx = N + 1;            // visible capital markers
var capHitIdx = N + 2;         // invisible enlarged capital click targets
var STADIUMS = __STADIUMS__;
var selected = {};

function refresh() {
    var arcIdx = [], arcVis = [], arcHover = [];
    for (var i = 0; i < N; i++) {
        var on = selected[i] === true;
        arcIdx.push(i);
        arcVis.push(on);
        arcHover.push(on ? "text" : "skip");
    }
    Plotly.restyle(gd, {visible: arcVis, hoverinfo: arcHover}, arcIdx);

    var lat = [], lon = [], cd = [];
    for (var s = 0; s < STADIUMS.length; s++) {
        var site = STADIUMS[s];
        var active = site.squads.filter(function (sq) { return selected[sq.team]; });
        if (active.length === 0) {
            continue;
        }
        active.sort(function (a, b) {
            return a.nation.localeCompare(b.nation);
        });
        var clubsSeen = {};
        var clubs = [];
        active.forEach(function (sq) {
            if (!clubsSeen[sq.club]) {
                clubsSeen[sq.club] = true;
                clubs.push(sq.club);
            }
        });
        clubs = clubs.join(" / ");
        var squadsHtml = active.map(function (sq) {
            var km = Math.round(sq.distance_km).toLocaleString();
            return "<b>" + sq.nation + "</b> (~" + km + " km from " + sq.capital + "):<br>" + sq.players;
        }).join("<br><br>");
        lat.push(site.lat);
        lon.push(site.lon);
        cd.push([clubs, site.stadium, site.location, squadsHtml]);
    }
    Plotly.restyle(gd, {
        lat: [lat],
        lon: [lon],
        customdata: [cd],
        visible: lat.length > 0,
        hoverinfo: lat.length > 0 ? ["text"] : ["skip"]
    }, [stadiumIdx]);
}

function teamFromClick(curveNumber, pointNumber) {
    if (curveNumber === capIdx || curveNumber === capHitIdx) {
        return pointNumber;
    }
    if (curveNumber < N) {
        return curveNumber;
    }
    return null;
}

function toggleTeam(i) {
    if (selected[i]) {
        delete selected[i];
    } else {
        selected[i] = true;
    }
    refresh();
}

function showAll() {
    for (var i = 0; i < N; i++) {
        selected[i] = true;
    }
    refresh();
}

function hideAll() {
    selected = {};
    refresh();
}

(function addToolbar() {
    var bar = document.createElement("div");
    bar.style.cssText =
        "position:fixed;top:12px;left:12px;z-index:10000;display:flex;gap:8px;" +
        "font:14px system-ui,-apple-system,Segoe UI,Roboto,sans-serif;";
    function makeBtn(label, onClick) {
        var btn = document.createElement("button");
        btn.type = "button";
        btn.textContent = label;
        btn.style.cssText =
            "padding:8px 14px;border:1px solid #475569;border-radius:6px;" +
            "background:#1e293b;color:#e2e8f0;cursor:pointer;box-shadow:0 1px 4px rgba(0,0,0,.35);";
        btn.onmouseenter = function () { btn.style.background = "#334155"; };
        btn.onmouseleave = function () { btn.style.background = "#1e293b"; };
        btn.onclick = onClick;
        return btn;
    }
    bar.appendChild(makeBtn("Show all", showAll));
    bar.appendChild(makeBtn("Hide all", hideAll));
    document.body.appendChild(bar);
})();

gd.on('plotly_click', function (ev) {
    var p = ev.points[0];
    var i = teamFromClick(p.curveNumber, p.pointNumber);
    if (i !== null) {
        toggleTeam(i);
    }
});
"""


def write_map(output_path: Path) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    tournament, teams = build_teams(strict=True)
    fig, stadium_sites = build_figure(tournament, teams)
    post_script = (
        CLICK_SCRIPT.replace("__N__", str(len(teams))).replace(
            "__STADIUMS__", json.dumps(stadium_sites)
        )
    )
    fig.write_html(
        output_path,
        include_plotlyjs="cdn",
        full_html=True,
        post_script=post_script,
        config={"displayModeBar": True, "scrollZoom": True, "responsive": True},
    )
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the World Cup teams flight-path map.")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=OUTPUT_HTML,
        help=f"Output HTML path (default: {OUTPUT_HTML.name}).",
    )
    args = parser.parse_args()

    tournament, teams = build_teams(strict=True)
    path = write_map(args.output)

    total_players = sum(t.n_players for t in teams)
    print(f"Wrote {path}")
    print(f"{tournament}: {len(teams)} teams, {total_players} players plotted.")
    print(
        "Open the HTML: click a capital or use Show all / Hide all (top left); "
        "hover paths or club dots for details."
    )


if __name__ == "__main__":
    main()
