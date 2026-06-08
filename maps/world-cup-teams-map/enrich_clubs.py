"""Add missing squad clubs to clubs.json using squad-page Wikipedia links.

Run after fetch_squads.py:
    python maps/world-cup-teams-map/enrich_clubs.py

fetch_squads.py stores each player's ``club_wiki`` title (from the squad table
link on Wikipedia) and writes ``data/club_wiki.json``. This script resolves
those titles to stadium coordinates via Wikipedia/Wikidata (P115 home venue),
falling back to title search only when no link is available. Clubs that cannot
be resolved are listed for manual entry in clubs.json or seed_clubs.py.
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
CLUB_WIKI_JSON = DATA_DIR / "club_wiki.json"

WIKI_API = "https://en.wikipedia.org/w/api.php"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
USER_AGENT = "maps-world-cup-teams/1.0 (educational map; github.com/maps)"
# Space out every Wikipedia API call (each club lookup uses several).
MIN_REQUEST_GAP = 1.0
_last_wiki_request = 0.0


class WikiRateLimitedError(Exception):
    """Raised when Wikipedia returns 429 after retries."""

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
    "TSG Hoffenheim": "Hoffenheim",
    "SK Slavia Prague": "Slavia Prague",
    "AC Sparta Prague": "Sparta Prague",
    "FC Viktoria Plzeň": "Viktoria Plzen",
    "Viktoria Plzeň": "Viktoria Plzen",
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
    "AZ Alkmaar": "AZ",
    "FK Austria Wien": "Austria Wien",
    "Al Qadsiah FC": "Al Qadsiah",
    "FC Lokomotiv Moscow": "Lokomotiv Moscow",
    "FC Dynamo Moscow": "Dynamo Moscow",
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
    "Pumas": "Pumas UNAM",
    "Pumas UNAM": "Pumas UNAM",
    "Navbahor": "Navbahor Namangan",
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


def _api_get(api: str, params: dict, *, retries: int = 5) -> dict:
    global _last_wiki_request
    query = urllib.parse.urlencode({**params, "format": "json"})
    req = urllib.request.Request(
        f"{api}?{query}",
        headers={"User-Agent": USER_AGENT},
    )
    delay = 5.0
    for attempt in range(retries):
        gap = MIN_REQUEST_GAP - (time.monotonic() - _last_wiki_request)
        if gap > 0:
            time.sleep(gap)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                _last_wiki_request = time.monotonic()
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                if attempt < retries - 1:
                    time.sleep(delay)
                    delay *= 2
                    continue
                raise WikiRateLimitedError("Wikipedia API rate limit (429)") from exc
            raise
    raise RuntimeError("Wikipedia API retries exhausted")


def _wiki_get(params: dict, *, retries: int = 5) -> dict:
    return _api_get(WIKI_API, params, retries=retries)


def _wikidata_get(params: dict, *, retries: int = 5) -> dict:
    return _api_get(WIKIDATA_API, params, retries=retries)


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


def wiki_title_from_href(href: str) -> str | None:
    """Decode a /wiki/... href to a Wikipedia page title."""
    if not href.startswith("/wiki/"):
        return None
    slug = urllib.parse.unquote(href.removeprefix("/wiki/").split("#", maxsplit=1)[0])
    return slug.replace("_", " ")


def club_wiki_map(squads: dict) -> dict[str, str]:
    """Canonical club name -> Wikipedia page title (from squad page links)."""
    mapping: dict[str, str] = {}
    for team in squads.get("teams", []):
        for player in team.get("players", []):
            wiki = player.get("club_wiki")
            if not wiki:
                continue
            key = canonical_club(player["club"])
            mapping.setdefault(key, wiki)
    if CLUB_WIKI_JSON.exists():
        file_map = _load_json(CLUB_WIKI_JSON).get("clubs", {})
        for key, wiki in file_map.items():
            mapping.setdefault(canonical_club(key), wiki)
    return mapping


def _wikibase_qid(title: str) -> str | None:
    data = _wiki_get(
        {
            "action": "query",
            "titles": title,
            "prop": "pageprops",
            "ppprop": "wikibase_item",
        }
    )
    for page in data.get("query", {}).get("pages", {}).values():
        return page.get("pageprops", {}).get("wikibase_item")
    return None


def _wd_entity(qid: str) -> dict:
    data = _wikidata_get(
        {"action": "wbgetentities", "ids": qid, "props": "claims|labels"}
    )
    return data.get("entities", {}).get(qid, {})


def _wd_label(entity: dict, *, lang: str = "en") -> str:
    return entity.get("labels", {}).get(lang, {}).get("value", "Unknown")


def _wd_claim_qid(entity: dict, prop: str) -> str | None:
    claims = entity.get("claims", {}).get(prop, [])
    if not claims:
        return None
    value = claims[0]["mainsnak"]["datavalue"]["value"]
    if isinstance(value, dict) and "id" in value:
        return value["id"]
    return None


def _wd_claim_coords(entity: dict) -> tuple[float, float] | None:
    claims = entity.get("claims", {}).get("P625", [])
    if not claims:
        return None
    value = claims[0]["mainsnak"]["datavalue"]["value"]
    return float(value["latitude"]), float(value["longitude"])


def _club_info_from_wikidata(title: str) -> dict | None:
    """Home venue + coordinates via Wikidata (P115/P625) for a Wikipedia title."""
    qid = _wikibase_qid(title)
    if not qid:
        return None
    club = _wd_entity(qid)
    stadium_qid = _wd_claim_qid(club, "P115")
    if not stadium_qid:
        return None
    stadium = _wd_entity(stadium_qid)
    coords = _wd_claim_coords(stadium)
    if coords is None:
        return None
    country_qid = _wd_claim_qid(club, "P17")
    city_qid = _wd_claim_qid(stadium, "P131")
    country = _wd_label(_wd_entity(country_qid)) if country_qid else "Unknown"
    city = _wd_label(_wd_entity(city_qid)) if city_qid else "Unknown"
    lat, lon = coords
    return {
        "stadium": _wd_label(stadium),
        "city": city,
        "country": country,
        "lat": round(lat, 4),
        "lon": round(lon, 4),
    }


def _club_info_from_title(title: str) -> dict | None:
    """Resolve a known Wikipedia page title to stadium metadata."""
    coords = _page_coords(title)
    resolved_title = title
    if coords is None:
        for candidate in (f"{title} Stadium", f"{title} (stadium)"):
            coords = _page_coords(candidate)
            if coords:
                resolved_title = candidate
                break
    if coords is not None:
        city, country = _infer_location(resolved_title)
        lat, lon = coords
        stadium = (
            resolved_title
            if "stadium" in resolved_title.lower()
            else f"{resolved_title} (home)"
        )
        return {
            "stadium": stadium,
            "city": city,
            "country": country,
            "lat": round(lat, 4),
            "lon": round(lon, 4),
        }
    return _club_info_from_wikidata(title)


def lookup_club(label: str, *, wiki_title: str | None = None) -> dict | None:
    """Resolve club label to stadium metadata via Wikipedia."""
    if wiki_title:
        info = _club_info_from_title(wiki_title)
        if info is not None:
            return info

    candidates = [label]
    for suffix in SEARCH_SUFFIXES:
        candidates.append(f"{label} {suffix}")

    for query in candidates:
        title = _search_title(query)
        if not title:
            continue
        info = _club_info_from_title(title)
        if info is not None:
            return info
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

    wiki_map = club_wiki_map(squads)
    missing = missing_club_names(squads, clubs)
    with_wiki = sum(1 for name in missing if name in wiki_map)
    print(f"{len(missing)} clubs to resolve via Wikipedia ({with_wiki} with squad-page links)")

    added = 0
    failed: list[str] = []
    for i, name in enumerate(missing):
        print(f"  [{i + 1}/{len(missing)}] resolving {name}…", flush=True)
        try:
            info = lookup_club(name, wiki_title=wiki_map.get(name))
        except WikiRateLimitedError:
            print(
                f"  rate-limited at {name}; saved {added} new clubs — re-run later to continue",
                flush=True,
            )
            _save_clubs(clubs)
            return
        if info is None:
            failed.append(name)
            print(f"           skip (no coordinates found)", flush=True)
        else:
            clubs[name] = info
            added += 1
            _save_clubs(clubs)
            print(
                f"           + {info['stadium']}, {info['city']}, {info['country']}",
                flush=True,
            )

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
