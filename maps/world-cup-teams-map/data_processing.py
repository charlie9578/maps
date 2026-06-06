"""Load and validate the World Cup teams dataset and build flight-path arcs.

The map plots each qualified nation at its capital city; clicking a capital
reveals great-circle "flight paths" from the capital to each club stadium.

Data lives in two committed JSON files (see README for sourcing + caveats):
  - data/squads.json : nations -> capital + official squad (no, name, pos, dob, age, caps, goals, club)
  - data/clubs.json  : club name -> home stadium + lat/lon

Run from repo root: python maps/world-cup-teams-map/main.py
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

MAP_DIR = Path(__file__).resolve().parent
DATA_DIR = MAP_DIR / "data"
SQUADS_JSON = DATA_DIR / "squads.json"
CLUBS_JSON = DATA_DIR / "clubs.json"

# Points sampled along each route polyline.
ARC_POINTS = 48


@dataclass
class DestinationRoute:
    """One capital -> stadium link (possibly several players at the same club)."""

    dest_lat: float
    dest_lon: float
    clubs: list[str]
    stadium: str
    club_city: str
    club_country: str
    distance_km: float
    players: list[tuple[int | None, str, str, str | None, int | None, int | None, int | None]]
    # (shirt no., name, position, dob ISO, age, caps, goals)
    arc_lats: list[float | None]
    arc_lons: list[float | None]


@dataclass
class Team:
    """A national team anchored at its capital, with outbound flight paths."""

    nation: str
    flag: str
    confederation: str
    capital: str
    lat: float
    lon: float
    routes: list[DestinationRoute] = field(default_factory=list)
    squad: list[
        tuple[int | None, str, str, str | None, int | None, int | None, int | None, str]
    ] = field(default_factory=list)
    # Full official squad (shirt no., name, pos, dob, age, caps, goals, club).

    @property
    def n_players(self) -> int:
        return sum(len(r.players) for r in self.routes)

    @property
    def n_destinations(self) -> int:
        return len(self.routes)


def _load_json(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"Missing data file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_clubs() -> dict[str, dict]:
    """Return {club_name: {stadium, city, country, lat, lon}}."""
    return _load_json(CLUBS_JSON)["clubs"]


def load_squads() -> dict:
    """Return the raw squads payload (tournament label + list of teams)."""
    return _load_json(SQUADS_JSON)


def find_missing_clubs(squads: dict, clubs: dict[str, dict]) -> list[tuple[str, str, str]]:
    """List (nation, player, club) entries whose club is absent from clubs.json."""
    missing: list[tuple[str, str, str]] = []
    for team in squads["teams"]:
        for player in team["players"]:
            if player["club"] not in clubs:
                missing.append((team["nation"], player["name"], player["club"]))
    return missing


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometres between two lat/lon points."""
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def flight_arc(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    n: int = ARC_POINTS,
) -> tuple[list[float | None], list[float | None]]:
    """Great-circle path from capital to stadium, split at the antimeridian."""
    lats, lons = great_circle_arc(lat1, lon1, lat2, lon2, n=n)
    return split_antimeridian_polyline(lats, lons)


def _arc_crosses_antimeridian(lons: list[float]) -> bool:
    """True if consecutive longitude samples jump across the ±180° cut."""
    return any(abs(lons[i] - lons[i - 1]) > 180 for i in range(1, len(lons)))


def great_circle_arc(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    n: int = ARC_POINTS,
    *,
    prefer_long_arc: bool | None = None,
) -> tuple[list[float], list[float]]:
    """Sample ``n`` points along a great circle from (lat1,lon1) to (lat2,lon2).

    Uses spherical linear interpolation (slerp) on unit vectors. By default follows
    the **shorter** great circle. If that path crosses the antimeridian (which makes
    Plotly draw a horizontal wrap across the map), the **long** arc is used instead
    so the line stays on screen.
    """
    phi1, lam1 = math.radians(lat1), math.radians(lon1)
    phi2, lam2 = math.radians(lat2), math.radians(lon2)

    x1, y1, z1 = _to_unit_vector(phi1, lam1)
    x2, y2, z2 = _to_unit_vector(phi2, lam2)

    dot = max(-1.0, min(1.0, x1 * x2 + y1 * y2 + z1 * z2))
    omega_short = math.acos(dot)

    if omega_short < 1e-9:
        return [lat1, lat2], [lon1, lon2]

    if prefer_long_arc is None:
        lats_s, lons_s = _slerp_arc(x1, y1, z1, x2, y2, z2, omega_short, n)
        prefer_long_arc = _arc_crosses_antimeridian(lons_s)

    omega = (2 * math.pi - omega_short) if prefer_long_arc else omega_short
    return _slerp_arc(x1, y1, z1, x2, y2, z2, omega, n)


def _slerp_arc(
    x1: float,
    y1: float,
    z1: float,
    x2: float,
    y2: float,
    z2: float,
    omega: float,
    n: int,
) -> tuple[list[float], list[float]]:
    sin_omega = math.sin(omega)
    lats: list[float] = []
    lons: list[float] = []
    for i in range(n + 1):
        t = i / n
        a = math.sin((1 - t) * omega) / sin_omega
        b = math.sin(t * omega) / sin_omega
        x = a * x1 + b * x2
        y = a * y1 + b * y2
        z = a * z1 + b * z2
        lats.append(math.degrees(math.atan2(z, math.sqrt(x * x + y * y))))
        lons.append(math.degrees(math.atan2(y, x)))
    return lats, lons


def split_antimeridian_polyline(
    lats: list[float], lons: list[float]
) -> tuple[list[float | None], list[float | None]]:
    """Break a polyline at the ±180° meridian so map lines do not wrap horizontally."""
    if len(lats) < 2:
        return list(lats), list(lons)

    out_lat: list[float | None] = []
    out_lon: list[float | None] = []
    for i, (la, lo) in enumerate(zip(lats, lons, strict=True)):
        if i and abs(lo - lons[i - 1]) > 180:
            out_lat.append(None)
            out_lon.append(None)
        out_lat.append(la)
        out_lon.append(lo)
    return out_lat, out_lon


def _to_unit_vector(phi: float, lam: float) -> tuple[float, float, float]:
    return (
        math.cos(phi) * math.cos(lam),
        math.cos(phi) * math.sin(lam),
        math.sin(phi),
    )


def build_teams(*, strict: bool = True) -> tuple[str, list[Team]]:
    """Assemble validated Team objects with great-circle flight paths.

    Returns (tournament_label, teams). With ``strict`` (default), raises if any
    referenced club is missing from clubs.json so data problems fail loudly.
    """
    squads = load_squads()
    clubs = load_clubs()

    missing = find_missing_clubs(squads, clubs)
    if missing and strict:
        lines = "\n".join(f"  - {nat}: {pl} -> {club}" for nat, pl, club in missing)
        raise KeyError(
            f"{len(missing)} player(s) reference clubs not in clubs.json:\n{lines}\n"
            "Add the club(s) to data/clubs.json (stadium + lat/lon)."
        )

    teams: list[Team] = []
    for raw in squads["teams"]:
        team = Team(
            nation=raw["nation"],
            flag=raw.get("flag", ""),
            confederation=raw.get("confederation", ""),
            capital=raw["capital"],
            lat=float(raw["lat"]),
            lon=float(raw["lon"]),
        )
        squad_rows: list[
            tuple[int | None, str, str, str | None, int | None, int | None, int | None, str]
        ] = []
        for player in raw["players"]:
            squad_rows.append(
                (
                    player.get("no"),
                    player["name"],
                    player.get("pos", ""),
                    player.get("dob"),
                    player.get("age"),
                    player.get("caps"),
                    player.get("goals"),
                    player["club"],
                )
            )
        squad_rows.sort(key=lambda row: (row[0] is None, row[0] if row[0] is not None else 999))
        team.squad = squad_rows

        grouped: dict[tuple[float, float], dict] = {}
        for player in raw["players"]:
            club = clubs.get(player["club"])
            if club is None:
                continue
            dest_lat = float(club["lat"])
            dest_lon = float(club["lon"])
            key = (round(dest_lat, 4), round(dest_lon, 4))
            entry = grouped.get(key)
            if entry is None:
                entry = {
                    "dest_lat": dest_lat,
                    "dest_lon": dest_lon,
                    "stadium": club["stadium"],
                    "city": club["city"],
                    "country": club["country"],
                    "clubs": [],
                    "players": [],
                }
                grouped[key] = entry
            if player["club"] not in entry["clubs"]:
                entry["clubs"].append(player["club"])
            entry["players"].append(
                (
                    player.get("no"),
                    player["name"],
                    player.get("pos", ""),
                    player.get("dob"),
                    player.get("age"),
                    player.get("caps"),
                    player.get("goals"),
                )
            )

        if not grouped:
            teams.append(team)
            continue

        for entry in grouped.values():
            dist = haversine_km(team.lat, team.lon, entry["dest_lat"], entry["dest_lon"])
            arc_lats, arc_lons = flight_arc(
                team.lat,
                team.lon,
                entry["dest_lat"],
                entry["dest_lon"],
            )
            team.routes.append(
                DestinationRoute(
                    dest_lat=entry["dest_lat"],
                    dest_lon=entry["dest_lon"],
                    clubs=entry["clubs"],
                    stadium=entry["stadium"],
                    club_city=entry["city"],
                    club_country=entry["country"],
                    distance_km=dist,
                    players=entry["players"],
                    arc_lats=arc_lats,
                    arc_lons=arc_lons,
                )
            )
        teams.append(team)

    teams.sort(key=lambda t: t.nation)
    return squads.get("tournament", "World Cup"), teams


if __name__ == "__main__":
    _squads = load_squads()
    _clubs = load_clubs()
    _missing = find_missing_clubs(_squads, _clubs)
    print(f"Teams: {len(_squads['teams'])}  Clubs in catalog: {len(_clubs)}")
    if _missing:
        print(f"\n{len(_missing)} missing club reference(s):", flush=True)
        for nat, pl, club in _missing:
            line = f"  - {nat}: {pl} -> {club}\n"
            sys.stdout.buffer.write(line.encode("utf-8", errors="replace"))
    else:
        print("All player clubs resolve against clubs.json.")
