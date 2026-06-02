"""World Cup teams flight-path map. Run from repo root:

    python maps/world-cup-teams-map/main.py

Plots each qualified nation at its capital city. Click a capital to reveal
curved great-circle "flight paths" to the clubs where that squad's players play.

Data is curated/committed JSON (see README and data/*.json for sourcing).
"""

from __future__ import annotations

import argparse
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
var capIdx = 2 * N;          // visible capital markers
var capHitIdx = 2 * N + 1;   // invisible enlarged capital click targets
var selected = {};

function refresh() {
    var arcIdx = [], arcVis = [], arcHover = [];
    var dstIdx = [], dstVis = [], dstHover = [];
    for (var i = 0; i < N; i++) {
        var on = selected[i] === true;
        arcIdx.push(i);
        arcVis.push(on);
        arcHover.push(on ? "text" : "skip");
        dstIdx.push(N + i);
        dstVis.push(on);
        dstHover.push(on ? "text" : "skip");
    }
    Plotly.restyle(gd, {visible: arcVis, hoverinfo: arcHover}, arcIdx);
    Plotly.restyle(gd, {visible: dstVis, hoverinfo: dstHover}, dstIdx);
}

function teamFromClick(curveNumber, pointNumber) {
    if (curveNumber === capIdx || curveNumber === capHitIdx) {
        return pointNumber;
    }
    if (curveNumber < N) {
        return curveNumber;
    }
    if (curveNumber < 2 * N) {
        return curveNumber - N;
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
    fig = build_figure(tournament, teams)
    post_script = CLICK_SCRIPT.replace("__N__", str(len(teams)))
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
        "Open the HTML: click a capital to show flight paths, "
        "then hover paths or club dots for details; click capital, path, or dot to hide."
    )


if __name__ == "__main__":
    main()
