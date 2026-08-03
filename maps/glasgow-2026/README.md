# glasgow-2026

An interactive woven dashboard for the **Glasgow 2026 Commonwealth Games**.
Every one of the 74 teams is an equal horizontal strand in alphabetical order.
Each of the eleven sports contains three vertical, violin-shaped medal
threads. Their width follows each country's medal count: zero-value crossings
stay beneath the horizontal country warp, while wins are redrawn above it.
Flags finish the left edge of the pink cloth and three-letter team codes finish
the right.

- Thread colour identifies a broad Commonwealth region for every team,
  regardless of whether it won a medal.
- Gold, silver and bronze always occupy fixed positions at a sport crossing.
  Stitch size encodes the number won.
- Verified SVG flags identify teams on the tartan and in the medal table.
- Hover a metallic stitch for the exact sport result.
- Filter medallists or no-medal teams, search the complete table, or click a
  team, stitch or table row to lift one strand from the cloth.

## Build

From the repository root:

```bash
python maps/glasgow-2026/main.py
```

Open `maps/glasgow-2026/output/glasgow_2026_dashboard.html`. The generated file
loads Plotly, dashboard fonts, and MIT-licensed [Circle Flags](https://github.com/HatScripts/circle-flags)
SVGs from CDNs; the data and interaction code are embedded in the HTML.

## Data

`data/teams.json` is a committed snapshot of the final results, dated **2 August
2026**. Sport-level results derived from the official `C93` reports are stored
in `data/sport_medals.json`. The build checks that every team's sport medals
reconcile to the final table: 216 gold, 215 silver and 243 bronze, or 674 total.
Team-event medals count once, as in the official medal table.

Sources:

- [Official Glasgow 2026 teams](https://www.glasgow2026.com/teams)
- [Official detailed results and medal table](https://www.glasgow2026.com/results/detailed/#/general-medals)
- The official per-sport `C93` medallist reports in this folder
