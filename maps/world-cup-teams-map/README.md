# world-cup-teams-map

An interactive world map of **2026 FIFA World Cup** nations. Each qualified team
sits at its **capital city** (coloured by confederation). **Club stadiums are
always visible** on the map; **click a club** to reveal curved great-circle
**"flight paths"** out to the **national teams** that squad members will play
for.

For example, click **Brazil** (Brasília) to trace lines to the stadiums of each
squad member's club; click **Argentina** (Buenos Aires) for routes to clubs
across Europe and MLS; and so on. **Hover a club** for every player at that
ground (name, position, **date of birth**, **age**, **caps**, **goals**).
Flight paths are visual only — they do not have hovers.

- **Capital markers** = national-team capitals, coloured by **confederation**
  (UEFA, CONMEBOL, CONCACAF, CAF, AFC, OFC). **Click a capital dot** to draw
  arcs out to that squad's clubs.
- **Club dots** = always visible at each stadium with squad players. **Hover** a
  club for every nation and player at that ground. **Click a club** or **capital**
  to show the same great-circle arc for each linked pair (not two different
  lines). **Clicking a flight path does nothing** — only the markers toggle
  lines.
- If the shortest path would wrap off the map, the longer great-circle leg is used
  so lines stay on screen. **Click again** to hide; invisible enlarged targets
  around clubs and capitals help clicks land. Use **Show all** / **Hide all**
  (top-left buttons) to open or close every path at once.

## Run (from repo root)

```bash
python maps/world-cup-teams-map/main.py
# open output/world_cup_teams_map.html in a browser
```

This writes a self-contained `output/world_cup_teams_map.html` (Plotly via CDN).

## Dependencies

Uses the shared repo `.venv` (`plotly`, `pandas` are already available). No extra
packages are required for the HTML output. `requirements.txt` lists `plotly` for
standalone use.

## Data

Two committed JSON files under `data/` (no network calls at runtime):

| File | Contents |
|------|----------|
| `data/squads.json` | 48 nations → capital + coordinates, confederation, and the **official 26-player squad** (`no`, `name`, `pos`, `dob`, `age`, `caps`, `goals`, `club`). |
| `data/clubs.json`  | Each club → `stadium`, `city`, `country`, `lat`, `lon`. Player `club` values must match a key here. |

`data_processing.py` validates that every player's `club` exists in `clubs.json`
(run it directly to print any missing clubs) and builds the great-circle arcs.
`viz.py` builds the Plotly figure; `main.py` writes the HTML and injects the
click-to-toggle JavaScript.

### Refreshing squad data from Wikipedia

When FIFA publishes squad updates, re-fetch from Wikipedia and enrich club coordinates:

```bash
python maps/world-cup-teams-map/fetch_squads.py
python maps/world-cup-teams-map/seed_clubs.py     # curated coordinates for common clubs
python maps/world-cup-teams-map/enrich_clubs.py   # optional: fill gaps via Wikipedia API
python maps/world-cup-teams-map/data_processing.py  # list any clubs still missing
python maps/world-cup-teams-map/main.py
```

### Editing / extending the data manually

1. Add or change players in `data/squads.json` (reference clubs by name).
2. If you reference a new club, add it to `data/clubs.json` with stadium + lat/lon.
3. Re-run `python maps/world-cup-teams-map/data_processing.py` to check for
   missing clubs, then rebuild with `main.py`.

Coordinates only need city/stadium-level precision because the map is global —
being within the right city is visually exact at world scale.

Players whose club is not yet in `clubs.json` are skipped (no flight path). After
`fetch_squads.py`, run `seed_clubs.py` and optionally `enrich_clubs.py` to improve
coverage; re-run `data_processing.py` to see what is still missing.

## Data sources & caveats

Squads are the **official 26-player lists** published for the tournament (via
FIFA, mirrored on Wikipedia). **Age** is as of **11 June 2026** (opening match
day); **caps** and **goals** exclude matches after the tournament starts. The
**club** shown is where each player last played a competitive match before the
tournament, per FIFA/Wikipedia.

- **Squads (players, positions, ages, clubs):**
  [2026 FIFA World Cup squads](https://en.wikipedia.org/wiki/2026_FIFA_World_Cup_squads)
  on Wikipedia (parsed by `fetch_squads.py`).
- **National team capitals & confederations:** curated metadata in
  `fetch_squads.py` (seat-of-government coordinates).
- **Club stadium coordinates:** `data/clubs.json`, compiled from Wikipedia
  (`enrich_clubs.py`) and prior manual curation; city-level precision is enough
  at world-map scale.
- **Tournament:** [2026 FIFA World Cup](https://www.fifa.com/) (USA · Canada ·
  Mexico).
- **Accessed:** 5 June 2026.

Basemap geometry is Plotly's built-in Natural Earth layer.

## Outputs

`output/world_cup_teams_map.html` (gitignored). Open it in any modern browser.

Note: flag emojis render as flags on macOS/iOS/Android. **England** uses the St
George's cross (🏴󠁧󠁢󠁥󠁮󠁧󠁿), not the UK Union Jack, because home nations enter the World
Cup separately. On Windows, subdivision flags may not render and can fall back to
a short code label.

## Standalone repo

1. Copy this folder.
2. `pip install plotly` (and `pandas` if you extend the loaders).
3. `python main.py`.
