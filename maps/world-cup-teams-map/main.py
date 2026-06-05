"""World Cup teams flight-path map. Run from repo root:

    python maps/world-cup-teams-map/main.py

Plots each qualified nation at its capital city and every club stadium with
squad players. Click a club or capital to reveal great-circle flight paths.
Each path is drawn once and shared by both click modes.

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
var R = __R__;
var S = __S__;
var N = __N__;
var ROUTE_META = __ROUTE_META__;
var T = __TRACE_LAYOUT__;
var clubIdx = T.club;
var clubHitIdx = T.clubHit;
var capIdx = T.cap;
var capHitIdx = T.capHit;
var flagIdx = T.flag;
var flagHitIdx = T.flagHit;
var selectedClubs = {};
var selectedTeams = {};

function refresh() {
    if (R > 0) {
        var arcIdx = [], arcVis = [];
        for (var r = 0; r < R; r++) {
            var meta = ROUTE_META[r];
            var on = selectedClubs[meta.stadium] === true || selectedTeams[meta.team] === true;
            arcIdx.push(r);
            arcVis.push(on);
        }
        Plotly.restyle(gd, {visible: arcVis}, arcIdx);
    }

    if (S > 0) {
        var clubSizes = [], clubColors = [];
        for (var c = 0; c < S; c++) {
            clubSizes.push(selectedClubs[c] ? 11 : 8);
            clubColors.push(selectedClubs[c] ? "#e2e8f0" : "#94a3b8");
        }
        Plotly.restyle(gd, {
            "marker.size": [clubSizes],
            "marker.color": [clubColors]
        }, [clubIdx]);
    }

    if (N > 0) {
        var capSizes = [];
        for (var k = 0; k < N; k++) {
            capSizes.push(selectedTeams[k] ? 12 : 9);
        }
        Plotly.restyle(gd, {"marker.size": [capSizes]}, [capIdx]);
    }
}

function toggleClub(i) {
    if (selectedClubs[i]) {
        delete selectedClubs[i];
    } else {
        selectedClubs[i] = true;
    }
    refresh();
}

function toggleTeam(i) {
    if (selectedTeams[i]) {
        delete selectedTeams[i];
    } else {
        selectedTeams[i] = true;
    }
    refresh();
}

function showAll() {
    for (var i = 0; i < S; i++) {
        selectedClubs[i] = true;
    }
    for (var t = 0; t < N; t++) {
        selectedTeams[t] = true;
    }
    refresh();
}

function hideAll() {
    selectedClubs = {};
    selectedTeams = {};
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
    var curve = p.curveNumber;
    if (curve === clubIdx || curve === clubHitIdx) {
        toggleClub(p.pointNumber);
    } else if (curve === capIdx || curve === capHitIdx || curve === flagIdx || curve === flagHitIdx) {
        toggleTeam(p.pointNumber);
    }
});
"""


def write_map(output_path: Path) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    tournament, teams = build_teams(strict=False)
    fig, stadium_sites, route_meta, trace_layout = build_figure(tournament, teams)
    post_script = (
        CLICK_SCRIPT.replace("__R__", str(len(route_meta)))
        .replace("__S__", str(len(stadium_sites)))
        .replace("__N__", str(len(teams)))
        .replace("__ROUTE_META__", json.dumps(route_meta))
        .replace("__TRACE_LAYOUT__", json.dumps(trace_layout))
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

    tournament, teams = build_teams(strict=False)
    path = write_map(args.output)

    total_players = sum(t.n_players for t in teams)
    print(f"Wrote {path}")
    print(f"{tournament}: {len(teams)} teams, {total_players} players plotted.")
    print(
        "Open the HTML: click a club or capital for flight paths (not the lines); "
        "use Show all / Hide all (top left)."
    )


if __name__ == "__main__":
    main()
