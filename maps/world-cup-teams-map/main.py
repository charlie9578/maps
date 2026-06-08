"""World Cup teams flight-path map and squad dashboard. Run from repo root:

    python maps/world-cup-teams-map/main.py

By default builds the multi-page squad dashboard (including the integrated flight-path
map page). Use --map-only for a standalone full-screen map HTML file.

Data is curated/committed JSON (see README and data/*.json for sourcing).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from data_processing import build_teams, load_squads
from map_embed import write_standalone_map

MAP_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = MAP_DIR / "output"
OUTPUT_HTML = OUTPUT_DIR / "world_cup_teams_map.html"
OUTPUT_DASHBOARD = OUTPUT_DIR / "world_cup_dashboard.html"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the World Cup squad dashboard and/or standalone flight-path map.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=OUTPUT_HTML,
        help=f"Standalone map output path (default: {OUTPUT_HTML.name}).",
    )
    parser.add_argument(
        "--map-only",
        action="store_true",
        help="Build only the standalone flight-path map (skip the dashboard site).",
    )
    parser.add_argument(
        "--dashboard-only",
        action="store_true",
        help="Build only the squad statistics dashboard (includes the map page).",
    )
    args = parser.parse_args()

    if args.map_only and args.dashboard_only:
        parser.error("Choose at most one of --map-only and --dashboard-only.")

    if args.map_only:
        tournament, teams = build_teams(strict=False)
        path = write_standalone_map(args.output, tournament, teams)
        total_players = sum(t.n_players for t in teams)
        print(f"Wrote {path}")
        print(f"{tournament}: {len(teams)} teams, {total_players} players plotted.")
        print(
            "Open the HTML: legend toggles confederation paths; capitals/clubs toggle individuals "
            "(or hide them when a group is active); Show all / Hide all (top left)."
        )
        return

    from dashboard import write_dashboard_site

    paths = write_dashboard_site(OUTPUT_DIR)
    for path in paths:
        print(f"Wrote {path}")

    if not args.dashboard_only:
        tournament, teams = build_teams(strict=False)
        legacy_path = write_standalone_map(args.output, tournament, teams)
        print(f"Wrote {legacy_path} (legacy standalone map)")

    squads = load_squads()
    tournament = squads.get("tournament", "World Cup")
    n_teams = len(squads.get("teams", []))
    print(f"{tournament}: dashboard for {n_teams} nations ({len(paths)} pages).")
    print("Open output/world_cup_dashboard.html — Flight paths is in the nav.")


if __name__ == "__main__":
    main()
