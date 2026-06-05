"""Add missing squad clubs to clubs.json using Wikipedia stadium coordinates.

Run after fetch_squads.py:
    python maps/world-cup-teams-map/enrich_clubs.py

Uses the Wikipedia API (network required). Clubs that cannot be resolved are
listed for manual entry in clubs.json.
"""

from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

MAP_DIR = Path(__file__).resolve().parent
DATA_DIR = MAP_DIR / "data"
SQUADS_JSON = DATA_DIR / "squads.json"
CLUBS_JSON = DATA_DIR / "clubs.json"

WIKI_API = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "maps-world-cup-teams/1.0 (educational map; github.com/maps)"

# Wikipedia / FIFA label -> clubs.json key (existing or preferred canonical name).
CLUB_ALIASES: dict[str, str] = {
    "Milan": "AC Milan",
    "Bournemouth": "AFC Bournemouth",
    "FC St. Pauli": "St. Pauli",
    "Al-Ahli": "Al Ahli Saudi",
    "Al-Nassr": "Al Nassr",
    "Al-Hilal": "Al Hilal",
    "Al-Ittihad": "Al Ittihad",
    "Al-Ettifaq": "Al Ettifaq",
    "Al-Duhail": "Al Duhail",
    "Al-Sadd": "Al Sadd",
    "Al-Wakrah": "Al Wakrah",
    "Al-Wehdat": "Al Wehdat",
    "Al-Arabi": "Al Arabi",
    "Al-Qadsiah": "Al Qadsiah",
    "PSV Eindhoven": "PSV",
    "Atlético Madrid": "Atletico Madrid",
    "Atlético Mineiro": "Atletico Mineiro",
    "Club América": "Club America",
    "América": "Club America",
    "C.D. Guadalajara": "Guadalajara",
    "Deportivo Toluca FC": "Toluca",
    "Deportivo Toluca": "Toluca",
    "Atlanta United FC": "Atlanta United",
    "Chicago Fire FC": "Chicago Fire",
    "Los Angeles FC": "Los Angeles FC",
    "Olympique Lyonnais": "Lyon",
    "Olympique Marseille": "Marseille",
    "Bayer 04 Leverkusen": "Bayer Leverkusen",
    "TSG 1899 Hoffenheim": "Hoffenheim",
    "SK Slavia Prague": "Slavia Prague",
    "AC Sparta Prague": "Sparta Prague",
    "FC Viktoria Plzeň": "Viktoria Plzen",
    "RSC Anderlecht": "Anderlecht",
    "Mamelodi Sundowns F.C.": "Mamelodi Sundowns",
    "Orlando Pirates F.C.": "Orlando Pirates",
    "Kaizer Chiefs F.C.": "Kaizer Chiefs",
    "Espérance de Tunis": "Esperance de Tunis",
    "1. FSV Mainz 05": "Mainz 05",
    "FC Midtjylland": "Midtjylland",
    "S.C. Braga": "Braga",
    "Genoa CFC": "Genoa",
    "Fenerbahçe S.K. (football)": "Fenerbahce",
    "Fenerbahçe": "Fenerbahce",
    "Beşiktaş": "Besiktas",
    "PAOK FC": "PAOK",
    "AEK Athens F.C.": "AEK Athens",
    "FC Bayern Munich": "Bayern Munich",
    "Birmingham City F.C.": "Birmingham City",
    "Wolverhampton Wanderers F.C.": "Wolverhampton Wanderers",
    "West Ham United F.C.": "West Ham United",
    "Burnley F.C.": "Burnley",
    "Fulham F.C.": "Fulham",
    "Molde FK": "Molde",
    "Cerro Porteño": "Cerro Porteno",
    "São Paulo FC": "Sao Paulo",
    "São Paulo": "Sao Paulo",
    "Peñarol": "Penarol",
    "León": "Leon",
    "Vancouver Whitecaps FC": "Vancouver Whitecaps",
    "CF Montréal": "CF Montreal",
    "Seattle Sounders FC": "Seattle Sounders",
    "Inter Miami CF": "Inter Miami",
    "New York City FC": "New York City FC",
    "Philadelphia Union": "Philadelphia Union",
    "Columbus Crew": "Columbus Crew",
    "Portland Timbers": "Portland Timbers",
    "Real Salt Lake": "Real Salt Lake",
    "FC Dallas": "FC Dallas",
    "Houston Dynamo FC": "Houston Dynamo",
    "Sporting Kansas City": "Sporting Kansas City",
    "Minnesota United FC": "Minnesota United",
    "St. Louis City SC": "St. Louis City",
    "Nashville SC": "Nashville SC",
    "Orlando City SC": "Orlando City",
    "FC Cincinnati": "FC Cincinnati",
    "New York Red Bulls": "New York Red Bulls",
    "Colorado Rapids": "Colorado Rapids",
    "Antwerp": "Royal Antwerp",
    "Stade Rennais": "Rennes",
    "SC Freiburg": "Freiburg",
    "VfB Stuttgart": "VfB Stuttgart",
    "VfL Wolfsburg": "VfL Wolfsburg",
    "Borussia Mönchengladbach": "Borussia Monchengladbach",
    "Stade Brestois 29": "Brest",
    "Malmö FF": "Malmo FF",
    "Djurgårdens IF": "Djurgardens IF",
    "IFK Göteborg": "IFK Goteborg",
    "Brøndby IF": "Brondby",
    "FC Nordsjælland": "Nordsjaelland",
    "Ferencvárosi TC": "Ferencvaros",
    "Legia Warszawa": "Legia Warsaw",
    "Standard Liège": "Standard Liege",
    "Union Saint-Gilloise": "Union Saint-Gilloise",
    "Hradec Králové": "Hradec Kralove",
    "C.D. Tondela": "Tondela",
    "Zhejiang Professional F.C.": "Zhejiang",
    "Ulsan HD FC": "Ulsan HD",
    "Jeonbuk Hyundai Motors FC": "Jeonbuk Hyundai Motors",
    "Kashima Antlers": "Kashima Antlers",
    "Gangwon FC": "Gangwon FC",
    "Daejeon Hana Citizen": "Daejeon Hana Citizen",
    "Polokwane City F.C.": "Polokwane City",
    "Siwelele F.C.": "Siwelele",
    "Lokomotiv Moscow": "Lokomotiv Moscow",
    "Dynamo Moscow": "Dynamo Moscow",
    "Zenit Saint Petersburg": "Zenit Saint Petersburg",
    "Wrexham A.F.C.": "Wrexham",
    "Queens Park Rangers": "Queens Park Rangers",
    "Stoke City": "Stoke City",
    "Swansea City": "Swansea City",
    "Hull City": "Hull City",
    "Coventry City": "Coventry City",
    "Ipswich Town": "Ipswich Town",
    "Luton Town": "Luton Town",
    "Norwich City": "Norwich City",
    "Watford": "Watford",
    "Charlton Athletic": "Charlton Athletic",
    "Oxford United": "Oxford United",
    "Portsmouth": "Portsmouth",
    "Millwall": "Millwall",
    "Derby County": "Derby County",
    "Blackburn Rovers": "Blackburn Rovers",
    "Preston North End": "Preston North End",
    "Sheffield Wednesday": "Sheffield Wednesday",
    "Barnsley": "Barnsley",
    "Plymouth Argyle": "Plymouth Argyle",
    "Middlesbrough": "Middlesbrough",
    "Sunderland": "Sunderland",
    "Leicester City": "Leicester City",
    "Nottingham Forest": "Nottingham Forest",
    "Crystal Palace": "Crystal Palace",
    "Brentford": "Brentford",
    "AFC Bournemouth": "AFC Bournemouth",
    "Brighton & Hove Albion": "Brighton & Hove Albion",
    "Celta Vigo": "Celta Vigo",
    "Las Palmas": "Las Palmas",
    "Leganés": "Leganes",
    "Alavés": "Alaves",
    "Rayo Vallecano": "Rayo Vallecano",
    "Getafe": "Getafe",
    "Osasuna": "Osasuna",
    "Espanyol": "Espanyol",
    "Real Valladolid": "Real Valladolid",
    "Hellas Verona": "Hellas Verona",
    "Udinese": "Udinese",
    "Cagliari": "Cagliari",
    "Parma": "Parma",
    "Monza": "Monza",
    "Lecce": "Lecce",
    "Venezia": "Venezia",
    "Santos Laguna": "Santos Laguna",
    "Tigres UANL": "Tigres UANL",
    "Pumas UNAM": "Pumas UNAM",
    "Atlas": "Atlas",
    "Tijuana": "Club Tijuana",
    "Club Tijuana": "Club Tijuana",
    "Cruz Azul": "Cruz Azul",
    "Monterrey": "Monterrey",
    "Independiente del Valle": "Independiente del Valle",
    "Barcelona SC": "Barcelona SC",
    "LDU Quito": "LDU Quito",
    "Atletico Nacional": "Atletico Nacional",
    "Athletico Paranaense": "Athletico Paranaense",
    "Fluminense": "Fluminense",
    "Botafogo": "Botafogo",
    "Palmeiras": "Palmeiras",
    "Corinthians": "Corinthians",
    "Flamengo": "Flamengo",
    "Boca Juniors": "Boca Juniors",
    "River Plate": "River Plate",
    "Penarol": "Penarol",
    "Nacional": "Nacional",
    "Olimpia": "Olimpia",
    "Alanyaspor": "Alanyaspor",
    "Konyaspor": "Konyaspor",
    "Kasımpaşa": "Kasimpasa",
    "Trabzonspor": "Trabzonspor",
    "Galatasaray": "Galatasaray",
    "Besiktas": "Besiktas",
    "Hatayspor": "Hatayspor",
    "Al Ain FC": "Al Ain",
    "Al Ain": "Al Ain",
    "Persepolis": "Persepolis",
    "Esteghlal": "Esteghlal",
    "Pakhtakor": "Pakhtakor",
    "Urawa Red Diamonds": "Urawa Red Diamonds",
    "Yokohama F. Marinos": "Yokohama F. Marinos",
    "Kawasaki Frontale": "Kawasaki Frontale",
    "FC Tokyo": "FC Tokyo",
    "Albirex Niigata": "Albirex Niigata",
    "Gamba Osaka": "Gamba Osaka",
    "Cerezo Osaka": "Cerezo Osaka",
    "Sanfrecce Hiroshima": "Sanfrecce Hiroshima",
    "Vissel Kobe": "Vissel Kobe",
    "Nagoya Grampus": "Nagoya Grampus",
    "Kyoto Sanga": "Kyoto Sanga",
    "Auckland FC": "Auckland FC",
    "Melbourne City": "Melbourne City",
    "Melbourne Victory": "Melbourne Victory",
    "Sydney FC": "Sydney FC",
    "Western Sydney Wanderers": "Western Sydney Wanderers",
    "Perth Glory": "Perth Glory",
    "Adelaide United": "Adelaide United",
    "Brisbane Roar": "Brisbane Roar",
    "Wellington Phoenix": "Wellington Phoenix",
    "Central Coast Mariners": "Central Coast Mariners",
    "Macarthur FC": "Macarthur FC",
    "Newcastle Jets": "Newcastle Jets",
    "Western United": "Western United",
    "A-League Men": "Auckland FC",
}

# Search hints when the club name alone is ambiguous on Wikipedia.
SEARCH_SUFFIXES = ("FC", "football club", "stadium")


def _wiki_get(params: dict, *, retries: int = 5) -> dict:
    query = urllib.parse.urlencode({**params, "format": "json"})
    req = urllib.request.Request(
        f"{WIKI_API}?{query}",
        headers={"User-Agent": USER_AGENT},
    )
    delay = 2.0
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < retries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            raise
    raise RuntimeError("Wikipedia API retries exhausted")


def _page_coords(title: str) -> tuple[float, float] | None:
    data = _wiki_get(
        {
            "action": "query",
            "titles": title,
            "prop": "coordinates",
            "colimit": "1",
            "coprop": "primary",
        }
    )
    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        coords = page.get("coordinates")
        if coords:
            return float(coords[0]["lat"]), float(coords[0]["lon"])
    return None


def _search_title(query: str) -> str | None:
    data = _wiki_get(
        {
            "action": "opensearch",
            "search": query,
            "limit": 5,
            "namespace": 0,
        }
    )
    titles = data[1] if len(data) > 1 else []
    if not titles:
        return None
    q_lower = query.lower()
    for title in titles:
        if title.lower().startswith(q_lower) or q_lower in title.lower():
            return title
    return titles[0]


def _infer_location(title: str) -> tuple[str, str]:
    """Best-effort city/country from the article lead (infobox fallback)."""
    data = _wiki_get(
        {
            "action": "query",
            "titles": title,
            "prop": "extracts|pageprops",
            "exintro": "1",
            "explaintext": "1",
        }
    )
    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        extract = page.get("extract", "")
        # e.g. "... is a football club based in Manchester, England"
        match = re.search(r"based in ([^.]+)", extract, re.IGNORECASE)
        if match:
            parts = [p.strip() for p in match.group(1).split(",")]
            if len(parts) >= 2:
                return parts[0], parts[-1]
            if parts:
                return parts[0], parts[0]
    return "Unknown", "Unknown"


def lookup_club(label: str) -> dict | None:
    """Resolve club label to stadium metadata via Wikipedia."""
    candidates = [label]
    for suffix in SEARCH_SUFFIXES:
        candidates.append(f"{label} {suffix}")

    for query in candidates:
        title = _search_title(query)
        if not title:
            continue
        coords = _page_coords(title)
        if coords is None:
            # Try "<Club> Stadium" if the club page lacks coordinates.
            stadium_title = _search_title(f"{label} Stadium")
            if stadium_title:
                coords = _page_coords(stadium_title)
                if coords:
                    title = stadium_title
        if coords is None:
            continue
        city, country = _infer_location(title)
        lat, lon = coords
        stadium = title if "stadium" in title.lower() else f"{title} (home)"
        return {
            "stadium": stadium,
            "city": city,
            "country": country,
            "lat": round(lat, 4),
            "lon": round(lon, 4),
        }
    return None


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _save_clubs(clubs: dict[str, dict]) -> None:
    payload = {
        "_comment": (
            "Club -> home stadium + coordinates. Coordinates are city/stadium-level "
            "(good to a few hundred metres), which is more than enough at world-map scale. "
            "Compiled from Wikipedia. See README for sourcing notes."
        ),
        "clubs": dict(sorted(clubs.items())),
    }
    CLUBS_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def canonical_club(raw: str) -> str:
    return CLUB_ALIASES.get(raw, raw)


def apply_aliases_to_squads(squads: dict) -> None:
    for team in squads["teams"]:
        for player in team["players"]:
            player["club"] = canonical_club(player["club"])


def missing_club_names(squads: dict, clubs: dict[str, dict]) -> list[str]:
    names: set[str] = set()
    for team in squads["teams"]:
        for player in team["players"]:
            key = canonical_club(player["club"])
            if key not in clubs:
                names.add(key)
    return sorted(names)


def main() -> None:
    squads = _load_json(SQUADS_JSON)
    clubs: dict[str, dict] = _load_json(CLUBS_JSON)["clubs"]

    apply_aliases_to_squads(squads)
    SQUADS_JSON.write_text(
        json.dumps(squads, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    missing = missing_club_names(squads, clubs)
    print(f"{len(missing)} clubs to resolve via Wikipedia")

    added = 0
    failed: list[str] = []
    for i, name in enumerate(missing):
        try:
            info = lookup_club(name)
        except urllib.error.HTTPError:
            print(f"  rate-limited at {name}; saving progress and stopping", flush=True)
            _save_clubs(clubs)
            raise
        if info is None:
            failed.append(name)
        else:
            clubs[name] = info
            added += 1
            if added % 10 == 0:
                _save_clubs(clubs)
        if (i + 1) % 20 == 0:
            print(f"  … {i + 1}/{len(missing)} queried, {added} added", flush=True)
        time.sleep(1.2)

    _save_clubs(clubs)
    print(f"Added {added} clubs to {CLUBS_JSON}")
    if failed:
        print(f"\n{len(failed)} clubs still unresolved:")
        for club in failed[:50]:
            print(f"  - {club}", flush=True)
        if len(failed) > 50:
            print(f"  … and {len(failed) - 50} more", flush=True)


if __name__ == "__main__":
    main()
