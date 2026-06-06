"""Fetch official 2026 World Cup squads from Wikipedia and write squads.json.

Run from repo root:
    python maps/world-cup-teams-map/fetch_squads.py

Requires network access. Extracts club Wikipedia links from the squad tables
and writes data/club_wiki.json. Does not modify clubs.json — run enrich_clubs.py
afterwards, then data_processing.py to list any clubs still missing.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from enrich_clubs import CLUB_WIKI_JSON, canonical_club, wiki_title_from_href

MAP_DIR = Path(__file__).resolve().parent
DATA_DIR = MAP_DIR / "data"
SQUADS_JSON = DATA_DIR / "squads.json"
CLUBS_JSON = DATA_DIR / "clubs.json"

WIKI_URL = "https://en.wikipedia.org/wiki/2026_FIFA_World_Cup_squads"
TOURNAMENT = "2026 FIFA World Cup"
SOURCE = WIKI_URL

# Capital coordinates + confederation for all 48 qualified nations (Group A–L).
NATIONS: dict[str, dict] = {
    "Algeria": {
        "flag": "🇩🇿",
        "confederation": "CAF",
        "capital": "Algiers",
        "lat": 36.7538,
        "lon": 3.0588,
    },
    "Argentina": {
        "flag": "🇦🇷",
        "confederation": "CONMEBOL",
        "capital": "Buenos Aires",
        "lat": -34.6037,
        "lon": -58.3816,
    },
    "Australia": {
        "flag": "🇦🇺",
        "confederation": "AFC",
        "capital": "Canberra",
        "lat": -35.2809,
        "lon": 149.1300,
    },
    "Austria": {
        "flag": "🇦🇹",
        "confederation": "UEFA",
        "capital": "Vienna",
        "lat": 48.2082,
        "lon": 16.3738,
    },
    "Belgium": {
        "flag": "🇧🇪",
        "confederation": "UEFA",
        "capital": "Brussels",
        "lat": 50.8503,
        "lon": 4.3517,
    },
    "Bosnia and Herzegovina": {
        "flag": "🇧🇦",
        "confederation": "UEFA",
        "capital": "Sarajevo",
        "lat": 43.8563,
        "lon": 18.4131,
    },
    "Brazil": {
        "flag": "🇧🇷",
        "confederation": "CONMEBOL",
        "capital": "Brasilia",
        "lat": -15.7939,
        "lon": -47.8828,
    },
    "Canada": {
        "flag": "🇨🇦",
        "confederation": "CONCACAF (host)",
        "capital": "Ottawa",
        "lat": 45.4215,
        "lon": -75.6972,
    },
    "Cape Verde": {
        "flag": "🇨🇻",
        "confederation": "CAF",
        "capital": "Praia",
        "lat": 14.9330,
        "lon": -23.5133,
    },
    "Colombia": {
        "flag": "🇨🇴",
        "confederation": "CONMEBOL",
        "capital": "Bogota",
        "lat": 4.7110,
        "lon": -74.0721,
    },
    "Croatia": {
        "flag": "🇭🇷",
        "confederation": "UEFA",
        "capital": "Zagreb",
        "lat": 45.8150,
        "lon": 15.9819,
    },
    "Curaçao": {
        "flag": "🇨🇼",
        "confederation": "CONCACAF",
        "capital": "Willemstad",
        "lat": 12.1224,
        "lon": -68.8824,
    },
    "Czech Republic": {
        "flag": "🇨🇿",
        "confederation": "UEFA",
        "capital": "Prague",
        "lat": 50.0755,
        "lon": 14.4378,
    },
    "DR Congo": {
        "flag": "🇨🇩",
        "confederation": "CAF",
        "capital": "Kinshasa",
        "lat": -4.4419,
        "lon": 15.2663,
    },
    "Ecuador": {
        "flag": "🇪🇨",
        "confederation": "CONMEBOL",
        "capital": "Quito",
        "lat": -0.1807,
        "lon": -78.4678,
    },
    "Egypt": {
        "flag": "🇪🇬",
        "confederation": "CAF",
        "capital": "Cairo",
        "lat": 30.0444,
        "lon": 31.2357,
    },
    "England": {
        "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
        "confederation": "UEFA",
        "capital": "London",
        "lat": 51.5074,
        "lon": -0.1278,
    },
    "France": {
        "flag": "🇫🇷",
        "confederation": "UEFA",
        "capital": "Paris",
        "lat": 48.8566,
        "lon": 2.3522,
    },
    "Germany": {
        "flag": "🇩🇪",
        "confederation": "UEFA",
        "capital": "Berlin",
        "lat": 52.5200,
        "lon": 13.4050,
    },
    "Ghana": {
        "flag": "🇬🇭",
        "confederation": "CAF",
        "capital": "Accra",
        "lat": 5.6037,
        "lon": -0.1870,
    },
    "Haiti": {
        "flag": "🇭🇹",
        "confederation": "CONCACAF",
        "capital": "Port-au-Prince",
        "lat": 18.5944,
        "lon": -72.3074,
    },
    "Iran": {
        "flag": "🇮🇷",
        "confederation": "AFC",
        "capital": "Tehran",
        "lat": 35.6892,
        "lon": 51.3890,
    },
    "Iraq": {
        "flag": "🇮🇶",
        "confederation": "AFC",
        "capital": "Baghdad",
        "lat": 33.3152,
        "lon": 44.3661,
    },
    "Ivory Coast": {
        "flag": "🇨🇮",
        "confederation": "CAF",
        "capital": "Yamoussoukro",
        "lat": 6.8276,
        "lon": -5.2893,
    },
    "Japan": {
        "flag": "🇯🇵",
        "confederation": "AFC",
        "capital": "Tokyo",
        "lat": 35.6762,
        "lon": 139.6503,
    },
    "Jordan": {
        "flag": "🇯🇴",
        "confederation": "AFC",
        "capital": "Amman",
        "lat": 31.9454,
        "lon": 35.9284,
    },
    "Mexico": {
        "flag": "🇲🇽",
        "confederation": "CONCACAF (host)",
        "capital": "Mexico City",
        "lat": 19.4326,
        "lon": -99.1332,
    },
    "Morocco": {
        "flag": "🇲🇦",
        "confederation": "CAF",
        "capital": "Rabat",
        "lat": 34.0209,
        "lon": -6.8416,
    },
    "Netherlands": {
        "flag": "🇳🇱",
        "confederation": "UEFA",
        "capital": "Amsterdam",
        "lat": 52.3676,
        "lon": 4.9041,
    },
    "New Zealand": {
        "flag": "🇳🇿",
        "confederation": "OFC",
        "capital": "Wellington",
        "lat": -41.2865,
        "lon": 174.7762,
    },
    "Norway": {
        "flag": "🇳🇴",
        "confederation": "UEFA",
        "capital": "Oslo",
        "lat": 59.9139,
        "lon": 10.7522,
    },
    "Panama": {
        "flag": "🇵🇦",
        "confederation": "CONCACAF",
        "capital": "Panama City",
        "lat": 8.9824,
        "lon": -79.5199,
    },
    "Paraguay": {
        "flag": "🇵🇾",
        "confederation": "CONMEBOL",
        "capital": "Asuncion",
        "lat": -25.2637,
        "lon": -57.5759,
    },
    "Portugal": {
        "flag": "🇵🇹",
        "confederation": "UEFA",
        "capital": "Lisbon",
        "lat": 38.7223,
        "lon": -9.1393,
    },
    "Qatar": {
        "flag": "🇶🇦",
        "confederation": "AFC",
        "capital": "Doha",
        "lat": 25.2854,
        "lon": 51.5310,
    },
    "Saudi Arabia": {
        "flag": "🇸🇦",
        "confederation": "AFC",
        "capital": "Riyadh",
        "lat": 24.7136,
        "lon": 46.6753,
    },
    "Scotland": {
        "flag": "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
        "confederation": "UEFA",
        "capital": "Edinburgh",
        "lat": 55.9533,
        "lon": -3.1883,
    },
    "Senegal": {
        "flag": "🇸🇳",
        "confederation": "CAF",
        "capital": "Dakar",
        "lat": 14.7167,
        "lon": -17.4677,
    },
    "South Africa": {
        "flag": "🇿🇦",
        "confederation": "CAF",
        "capital": "Pretoria",
        "lat": -25.7479,
        "lon": 28.2293,
    },
    "South Korea": {
        "flag": "🇰🇷",
        "confederation": "AFC",
        "capital": "Seoul",
        "lat": 37.5665,
        "lon": 126.9780,
    },
    "Spain": {
        "flag": "🇪🇸",
        "confederation": "UEFA",
        "capital": "Madrid",
        "lat": 40.4168,
        "lon": -3.7038,
    },
    "Sweden": {
        "flag": "🇸🇪",
        "confederation": "UEFA",
        "capital": "Stockholm",
        "lat": 59.3293,
        "lon": 18.0686,
    },
    "Switzerland": {
        "flag": "🇨🇭",
        "confederation": "UEFA",
        "capital": "Bern",
        "lat": 46.9480,
        "lon": 7.4474,
    },
    "Tunisia": {
        "flag": "🇹🇳",
        "confederation": "CAF",
        "capital": "Tunis",
        "lat": 36.8065,
        "lon": 10.1815,
    },
    "Turkey": {
        "flag": "🇹🇷",
        "confederation": "UEFA",
        "capital": "Ankara",
        "lat": 39.9334,
        "lon": 32.8597,
    },
    "United States": {
        "flag": "🇺🇸",
        "confederation": "CONCACAF (host)",
        "capital": "Washington, D.C.",
        "lat": 38.9072,
        "lon": -77.0369,
    },
    "Uruguay": {
        "flag": "🇺🇾",
        "confederation": "CONMEBOL",
        "capital": "Montevideo",
        "lat": -34.9011,
        "lon": -56.1645,
    },
    "Uzbekistan": {
        "flag": "🇺🇿",
        "confederation": "AFC",
        "capital": "Tashkent",
        "lat": 41.2995,
        "lon": 69.2401,
    },
}

POS_MAP = {"1": "GK", "2": "DF", "3": "MF", "4": "FW"}
AGE_RE = re.compile(r"\(aged\s+(\d+)\)")
DOB_ISO_RE = re.compile(r"\((\d{4}-\d{2}-\d{2})\)")
DOB_TEXT_RE = re.compile(r"^(.+?)\s*\(aged\s+\d+\)", re.IGNORECASE)
POS_NUM_RE = re.compile(r"^(\d)")


def _cell_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _parse_position(raw: str) -> str:
    match = POS_NUM_RE.match(raw)
    if match:
        return POS_MAP.get(match.group(1), raw[:2].upper())
    upper = raw.upper()
    for code in ("GK", "DF", "MF", "FW"):
        if code in upper:
            return code
    return raw


def _parse_age(dob_cell: str) -> int | None:
    match = AGE_RE.search(dob_cell)
    return int(match.group(1)) if match else None


def _parse_dob(dob_cell: str) -> str | None:
    """Return ISO date (YYYY-MM-DD) from Wikipedia's 'Date of birth (age)' cell."""
    text = _cell_text(dob_cell)
    if not text:
        return None
    iso = DOB_ISO_RE.search(text)
    if iso:
        return iso.group(1)
    text_match = DOB_TEXT_RE.match(text)
    if not text_match:
        return None
    raw = text_match.group(1).strip()
    for fmt in ("%B %d, %Y", "%d %B %Y"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _parse_int(raw: object) -> int | None:
    text = _cell_text(raw)
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def _parse_club_cell(cell) -> tuple[str, str | None]:
    """Club display name and Wikipedia page title from the squad-table club cell."""
    links = [
        anchor
        for anchor in cell.find_all("a", href=True)
        if anchor["href"].startswith("/wiki/")
    ]
    if links:
        club_link = links[-1]
        name = club_link.get_text(strip=True)
        wiki_title = wiki_title_from_href(club_link["href"])
    else:
        name = cell.get_text(" ", strip=True)
        wiki_title = None
    name = re.sub(r"\s*\([^)]*\)\s*$", "", name).strip()
    return canonical_club(name), wiki_title


def _parse_player_row(row) -> dict | None:
    """Parse one squad-table row; return None for header or malformed rows."""
    cells = row.find_all(["td", "th"])
    if len(cells) < 7:
        return None

    name = cells[2].get_text(" ", strip=True)
    name = re.sub(r"\s*\(captain\)\s*$", "", name, flags=re.IGNORECASE).strip()
    if not name:
        return None

    dob_cell = cells[3].get_text(" ", strip=True)
    club, club_wiki = _parse_club_cell(cells[6])
    entry: dict = {
        "name": name,
        "pos": _parse_position(cells[1].get_text(" ", strip=True)),
        "club": club,
    }
    if club_wiki:
        entry["club_wiki"] = club_wiki

    no = _parse_int(cells[0].get_text(" ", strip=True))
    caps = _parse_int(cells[4].get_text(" ", strip=True))
    goals = _parse_int(cells[5].get_text(" ", strip=True))
    dob = _parse_dob(dob_cell)
    age = _parse_age(dob_cell)
    if no is not None:
        entry["no"] = no
    if dob is not None:
        entry["dob"] = dob
    if age is not None:
        entry["age"] = age
    if caps is not None:
        entry["caps"] = caps
    if goals is not None:
        entry["goals"] = goals
    return entry


def fetch_squads_from_wikipedia() -> list[dict]:
    teams: list[dict] = []
    seen: set[str] = set()

    resp = requests.get(WIKI_URL, timeout=60, headers={"User-Agent": "maps-repo/1.0"})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    content = None
    for candidate in soup.find_all("div", class_="mw-parser-output"):
        if candidate.find("h3"):
            content = candidate
            break
    if content is None:
        raise RuntimeError("Could not find Wikipedia article body")

    parsed_nations = 0

    for heading in content.find_all("h3"):
        nation = heading.get_text(strip=True)
        if nation not in NATIONS:
            continue
        table = heading.find_next("table", class_="wikitable")
        if table is None:
            continue
        rows = table.find_all("tr")[1:]
        if len(rows) < 20:
            continue

        players: list[dict] = []
        for row in rows:
            entry = _parse_player_row(row)
            if entry is not None:
                players.append(entry)
        if len(players) < 20:
            continue

        if nation in seen:
            continue
        seen.add(nation)
        parsed_nations += 1
        teams.append({"nation": nation, **NATIONS[nation], "players": players})

    if parsed_nations != 48:
        print(
            f"Warning: expected 48 squad tables, parsed {parsed_nations}",
            file=sys.stderr,
        )

    missing_meta = set(NATIONS) - seen
    if missing_meta:
        raise RuntimeError(f"Missing squads for: {sorted(missing_meta)}")

    teams.sort(key=lambda t: t["nation"])
    return teams


def _build_club_wiki_index(teams: list[dict]) -> dict[str, str]:
    index: dict[str, str] = {}
    for team in teams:
        for player in team["players"]:
            wiki = player.get("club_wiki")
            if wiki:
                index.setdefault(player["club"], wiki)
    return dict(sorted(index.items()))


def write_squads(teams: list[dict]) -> None:
    payload = {
        "_comment": (
            "Official 2026 FIFA World Cup squads (26 players per nation). "
            "Parsed from Wikipedia; club names must match keys in clubs.json. "
            "club_wiki is the linked Wikipedia article title from the squad page. "
            "Age is as of 11 June 2026 (tournament opening day); caps/goals exclude "
            "matches after tournament start, per FIFA/Wikipedia."
        ),
        "tournament": TOURNAMENT,
        "source": SOURCE,
        "source_accessed": "2026-06-05",
        "teams": teams,
    }
    SQUADS_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    wiki_index = _build_club_wiki_index(teams)
    CLUB_WIKI_JSON.write_text(
        json.dumps(
            {
                "_comment": (
                    "Canonical clubs.json keys mapped to Wikipedia article titles "
                    "from the squad page club links. Used by enrich_clubs.py."
                ),
                "source": SOURCE,
                "clubs": wiki_index,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def report_missing_clubs(teams: list[dict]) -> list[tuple[str, str, str]]:
    clubs = json.loads(CLUBS_JSON.read_text(encoding="utf-8"))["clubs"]
    missing: list[tuple[str, str, str]] = []
    for team in teams:
        for player in team["players"]:
            if player["club"] not in clubs:
                missing.append((team["nation"], player["name"], player["club"]))
    return missing


def main() -> None:
    teams = fetch_squads_from_wikipedia()
    write_squads(teams)
    print(f"Wrote {len(teams)} teams to {SQUADS_JSON}")

    missing = report_missing_clubs(teams)
    if missing:
        unique_clubs = sorted({club for _, _, club in missing})
        print(f"\n{len(missing)} player references to {len(unique_clubs)} unknown clubs:")
        for club in unique_clubs:
            n = sum(1 for _, _, c in missing if c == club)
            line = f"  - {club} ({n} players)\n"
            sys.stdout.buffer.write(line.encode("utf-8", errors="replace"))
    else:
        print("All clubs resolve against clubs.json.")


if __name__ == "__main__":
    main()
