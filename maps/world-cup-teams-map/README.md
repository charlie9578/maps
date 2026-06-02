# world-cup-teams-map

An interactive world map of **2026 FIFA World Cup** nations. Each qualified team
sits at its **capital city**; **click a capital** to reveal curved great-circle
**"flight paths"** out to the **stadiums of the clubs where that squad's players
currently play**.

For example, click **Brazil** (Brasília) to trace a line to **Old Trafford** in
Manchester, because Casemiro plays for Manchester United; click **Argentina**
(Buenos Aires) for a line to **Chase Stadium** in Fort Lauderdale for Lionel
Messi at Inter Miami; and so on.

- **Markers** = national-team capitals, coloured by **confederation** (UEFA,
  CONMEBOL, CONCACAF, CAF, AFC, OFC).
- **Arcs + endpoint dots** = one route per stadium (all players at that club
  share a line; shown only after you click that nation). Paths are **styled
  **great-circle flight paths** to each stadium, with a **short radial fan** at
  the capital (unique departure angle per route) so nearby lines do not stack;
  the rest of each arc follows the realistic great-circle route. **Hover** a path or club dot for every
  player at that destination. **Click the capital again** (or any of its paths or
  club dots) to hide; a larger invisible target around each capital helps clicks
  land near the city. You can open several nations at once to compare.

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
| `data/squads.json` | 48 nations → capital + coordinates, confederation, and a list of key players (`name`, `pos`, `club`). |
| `data/clubs.json`  | Each club → `stadium`, `city`, `country`, `lat`, `lon`. Player `club` values must match a key here. |

`data_processing.py` validates that every player's `club` exists in `clubs.json`
(run it directly to print any missing clubs) and builds the great-circle arcs.
`viz.py` builds the Plotly figure; `main.py` writes the HTML and injects the
click-to-toggle JavaScript.

### Editing / extending the data

1. Add or change players in `data/squads.json` (reference clubs by name).
2. If you reference a new club, add it to `data/clubs.json` with stadium + lat/lon.
3. Re-run `python maps/world-cup-teams-map/data_processing.py` to check for
   missing clubs, then rebuild with `main.py`.

Coordinates only need city/stadium-level precision because the map is global —
being within the right city is visually exact at world scale.

## Data sources & caveats

> **This is an illustrative, curated snapshot — not official squads.** Official
> 2026 World Cup squads had not been announced when this map was built, so each
> nation lists **notable/marquee players** and the club where they were playing
> around the **2025/26 season**. Some qualifiers, players, and clubs are
> editorial best-effort and may differ from the final tournament.

- **National teams, capitals, players → clubs:** compiled from public sources
  (national-team and player articles on [Wikipedia](https://www.wikipedia.org/))
  reflecting the 2025/26 club season.
- **Club stadium coordinates:** stadium articles on Wikipedia and
  **coordinate location** (P625) on [Wikidata](https://www.wikidata.org/) (e.g.
  the [football-stadium SPARQL query](https://query.wikidata.org/)).
- **Tournament:** [2026 FIFA World Cup](https://www.fifa.com/) (USA · Canada ·
  Mexico).
- **Accessed:** 2 June 2026.

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
