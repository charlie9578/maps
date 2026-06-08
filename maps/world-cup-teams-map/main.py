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
from viz import build_figure, confed_key

MAP_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = MAP_DIR / "output"
OUTPUT_HTML = OUTPUT_DIR / "world_cup_teams_map.html"
OUTPUT_DASHBOARD = OUTPUT_DIR / "world_cup_dashboard.html"

# Injected after the Plotly chart loads. Trace indices must match viz.py layout.
CLICK_SCRIPT = """
var gd = document.getElementById('{plot_id}');
var R = __R__;
var S = __S__;
var N = __N__;
var ROUTE_META = __ROUTE_META__;
var T = __TRACE_LAYOUT__;
var clubIdx = T.club;
var capIdx = T.cap;
var capHitIdx = T.capHit;
var flagIdx = T.flag;
var flagHitIdx = T.flagHit;
var LEGEND = T.legend;
var CONFED_BY_CURVE = {};
for (var ck in LEGEND) {
    if (Object.prototype.hasOwnProperty.call(LEGEND, ck)) {
        CONFED_BY_CURVE[LEGEND[ck]] = ck;
    }
}
var TEAM_CONFED = __TEAM_CONFED__;
var CONFED_TEAMS = __CONFED_TEAMS__;
var selectedClubs = {};
var selectedTeams = {};
var visibleConfeds = {};
var suppressedTeams = {};
var suppressedClubs = {};

function arcVisible(meta) {
    if (suppressedTeams[meta.team] || suppressedClubs[meta.stadium]) {
        return false;
    }
    if (visibleConfeds[meta.confed]) {
        return true;
    }
    if (selectedTeams[meta.team]) {
        return true;
    }
    if (selectedClubs[meta.stadium]) {
        return true;
    }
    return false;
}

function teamHighlighted(i) {
    if (suppressedTeams[i]) {
        return false;
    }
    if (visibleConfeds[TEAM_CONFED[i]]) {
        return true;
    }
    return selectedTeams[i] === true;
}

function routesVisibleWithoutClubSelection(stadiumIdx) {
    for (var r = 0; r < R; r++) {
        var meta = ROUTE_META[r];
        if (meta.stadium !== stadiumIdx) {
            continue;
        }
        if (suppressedTeams[meta.team]) {
            continue;
        }
        if (visibleConfeds[meta.confed] || selectedTeams[meta.team]) {
            return true;
        }
    }
    return false;
}

function clubHighlighted(i) {
    if (suppressedClubs[i]) {
        return false;
    }
    if (selectedClubs[i]) {
        return true;
    }
    return routesVisibleWithoutClubSelection(i);
}

function refresh() {
    if (R > 0) {
        var arcIdx = [], arcVis = [];
        for (var r = 0; r < R; r++) {
            arcIdx.push(r);
            arcVis.push(arcVisible(ROUTE_META[r]));
        }
        Plotly.restyle(gd, {visible: arcVis}, arcIdx);
    }

    if (S > 0) {
        var clubSizes = [], clubColors = [];
        for (var c = 0; c < S; c++) {
            clubSizes.push(clubHighlighted(c) ? 11 : 8);
            clubColors.push(clubHighlighted(c) ? "#e2e8f0" : "#94a3b8");
        }
        Plotly.restyle(gd, {
            "marker.size": [clubSizes],
            "marker.color": [clubColors]
        }, [clubIdx]);
    }

    if (N > 0) {
        var capSizes = [];
        for (var k = 0; k < N; k++) {
            capSizes.push(teamHighlighted(k) ? 12 : 9);
        }
        Plotly.restyle(gd, {"marker.size": [capSizes]}, [capIdx]);
    }
}

function toggleClub(i) {
    if (routesVisibleWithoutClubSelection(i)) {
        if (suppressedClubs[i]) {
            delete suppressedClubs[i];
        } else {
            suppressedClubs[i] = true;
        }
    } else if (selectedClubs[i]) {
        delete selectedClubs[i];
    } else {
        selectedClubs[i] = true;
    }
    refresh();
}

function toggleTeam(i) {
    if (visibleConfeds[TEAM_CONFED[i]]) {
        if (suppressedTeams[i]) {
            delete suppressedTeams[i];
        } else {
            suppressedTeams[i] = true;
        }
    } else if (selectedTeams[i]) {
        delete selectedTeams[i];
    } else {
        selectedTeams[i] = true;
    }
    refresh();
}

function showAll() {
    selectedClubs = {};
    selectedTeams = {};
    suppressedTeams = {};
    suppressedClubs = {};
    visibleConfeds = {};
    for (var confed in LEGEND) {
        if (Object.prototype.hasOwnProperty.call(LEGEND, confed)) {
            visibleConfeds[confed] = true;
        }
    }
    refresh();
}

function hideAll() {
    selectedClubs = {};
    selectedTeams = {};
    suppressedTeams = {};
    suppressedClubs = {};
    visibleConfeds = {};
    refresh();
}

function toggleConfed(confed) {
    var teams = CONFED_TEAMS[confed] || [];
    if (visibleConfeds[confed]) {
        delete visibleConfeds[confed];
        for (var j = 0; j < teams.length; j++) {
            delete suppressedTeams[teams[j]];
        }
    } else {
        visibleConfeds[confed] = true;
        for (var k = 0; k < teams.length; k++) {
            delete selectedTeams[teams[k]];
            delete suppressedTeams[teams[k]];
        }
    }
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
    var dashLink = document.createElement("a");
    dashLink.href = "world_cup_dashboard.html";
    dashLink.textContent = "Dashboard";
    dashLink.style.cssText =
        "padding:8px 14px;border:1px solid #475569;border-radius:6px;" +
        "background:#1e293b;color:#93c5fd;cursor:pointer;box-shadow:0 1px 4px rgba(0,0,0,.35);" +
        "text-decoration:none;display:inline-block;";
    dashLink.onmouseenter = function () { dashLink.style.background = "#334155"; };
    dashLink.onmouseleave = function () { dashLink.style.background = "#1e293b"; };
    bar.appendChild(dashLink);
    document.body.appendChild(bar);
})();

gd.on('plotly_legendclick', function (ev) {
    var confed = CONFED_BY_CURVE[ev.curveNumber];
    if (!confed) {
        return true;
    }
    toggleConfed(confed);
    return false;
});

gd.on('plotly_legenddoubleclick', function (ev) {
    if (CONFED_BY_CURVE[ev.curveNumber]) {
        return false;
    }
    return true;
});

gd.on('plotly_click', function (ev) {
    var p = ev.points[0];
    var curve = p.curveNumber;
    if (curve === clubIdx) {
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
    team_confeds = [confed_key(t.confederation) for t in teams]
    confed_teams: dict[str, list[int]] = {
        confed: [] for confed in trace_layout["legend"]  # type: ignore[index]
    }
    for team_idx, confed in enumerate(team_confeds):
        if confed in confed_teams:
            confed_teams[confed].append(team_idx)
    post_script = (
        CLICK_SCRIPT.replace("__R__", str(len(route_meta)))
        .replace("__S__", str(len(stadium_sites)))
        .replace("__N__", str(len(teams)))
        .replace("__ROUTE_META__", json.dumps(route_meta))
        .replace("__TRACE_LAYOUT__", json.dumps(trace_layout))
        .replace("__TEAM_CONFED__", json.dumps(team_confeds))
        .replace("__CONFED_TEAMS__", json.dumps(confed_teams))
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
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Also build output/world_cup_dashboard*.html (multi-page squad statistics).",
    )
    parser.add_argument(
        "--dashboard-only",
        action="store_true",
        help="Build only the squad statistics dashboard (skip the map).",
    )
    args = parser.parse_args()

    if args.dashboard_only:
        from dashboard import write_dashboard_site

        paths = write_dashboard_site(OUTPUT_DIR)
        for path in paths:
            print(f"Wrote {path}")
        return

    tournament, teams = build_teams(strict=False)
    path = write_map(args.output)

    total_players = sum(t.n_players for t in teams)
    print(f"Wrote {path}")
    print(f"{tournament}: {len(teams)} teams, {total_players} players plotted.")
    print(
        "Open the HTML: legend toggles confederation paths; capitals/clubs toggle individuals "
        "(or hide them when a group is active); Show all / Hide all (top left)."
    )

    if args.dashboard:
        from dashboard import write_dashboard_site

        for dash_path in write_dashboard_site(OUTPUT_DIR):
            print(f"Wrote {dash_path}")


if __name__ == "__main__":
    main()
