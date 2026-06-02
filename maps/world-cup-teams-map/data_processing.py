"""Load and validate the World Cup teams dataset and build flight-path arcs.

The map plots each qualified nation at its capital city; clicking a capital
reveals great-circle "flight paths" from the capital to each club stadium, with
a minimal radial fan at the hub so nearby routes do not overlap.

Data lives in two committed JSON files (see README for sourcing + caveats):
  - data/squads.json : nations -> capital + key players (player -> club name)
  - data/clubs.json  : club name -> home stadium + lat/lon

Run from repo root: python maps/world-cup-teams-map/main.py
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

MAP_DIR = Path(__file__).resolve().parent
DATA_DIR = MAP_DIR / "data"
SQUADS_JSON = DATA_DIR / "squads.json"
CLUBS_JSON = DATA_DIR / "clubs.json"

# Points sampled along each route polyline.
ARC_POINTS = 48

# Minimum departure angle (degrees) between routes from the same capital.
MIN_ROUTE_BEARING_DEG = 4.0

# Cap how far the radial fan stub extends from the capital (degrees, lat/lon plane).
MAX_FAN_STUB_DEG = 0.4


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
    players: list[tuple[str, str]]  # (name, position)
    arc_lats: list[float]
    arc_lons: list[float]


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


def _lon_delta(lon1: float, lon2: float) -> float:
    """Signed shortest eastward delta in degrees."""
    d = lon2 - lon1
    if d > 180:
        d -= 360
    elif d < -180:
        d += 360
    return d


def _bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial bearing from point 1 to point 2 (degrees, 0 = north)."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlam = math.radians(_lon_delta(lon1, lon2))
    y = math.sin(dlam) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlam)
    return math.degrees(math.atan2(y, x)) % 360


def _assign_display_bearings(true_bearings: list[float]) -> list[float]:
    """Assign disjoint departure bearings (degrees) for routes from one capital.

    When true bearings are too close, spreads them evenly while preserving
    circular order so each route owns a unique angular wedge from the capital.
    """
    n = len(true_bearings)
    if n <= 1:
        return true_bearings[:]

    order = sorted(range(n), key=true_bearings.__getitem__)
    unwrapped: list[tuple[int, float]] = []
    acc = true_bearings[order[0]]
    unwrapped.append((order[0], acc))
    for idx in order[1:]:
        b = true_bearings[idx]
        while b < acc - 180:
            b += 360
        while b > acc + 180:
            b -= 360
        acc = b
        unwrapped.append((idx, b))

    values = [u for _, u in unwrapped]
    span = values[-1] - values[0]
    min_sep = max(MIN_ROUTE_BEARING_DEG, min(12.0, 130.0 / n))
    needed = min_sep * (n - 1)

    if span >= needed:
        display_unwrapped = values
    else:
        center = sum(values) / n
        display_unwrapped = [center + (j - (n - 1) / 2) * min_sep for j in range(n)]

    result = [0.0] * n
    for (orig_idx, _), bearing in zip(unwrapped, display_unwrapped, strict=True):
        result[orig_idx] = bearing % 360
    return result


def _fan_stub_length_deg(chord_deg: float, distance_km: float) -> float:
    """Short radial fan from the capital before the great-circle leg."""
    if distance_km < 80:
        frac = 0.16
    elif distance_km < 400:
        frac = 0.09
    else:
        frac = 0.05
    return min(chord_deg * frac, MAX_FAN_STUB_DEG)


def flight_arc(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    *,
    display_bearing_deg: float,
    distance_km: float,
    n: int = ARC_POINTS,
) -> tuple[list[float], list[float]]:
    """Great-circle flight path with a minimal radial fan at the capital.

    1. **Fan stub** — short straight segment along a unique assigned bearing θ′ᵢ
       (routes only meet at the capital).
    2. **Great circle** — slerp arc from the stub tip to the stadium (realistic
       flight path on the map).
    """
    dlon = _lon_delta(lon1, lon2)
    dlat = lat2 - lat1
    chord = math.hypot(dlat, dlon) or 1e-6

    br = math.radians(display_bearing_deg)
    cos_lat = max(0.25, math.cos(math.radians(lat1)))
    ray_dlat = math.cos(br)
    ray_dlon = math.sin(br) / cos_lat
    ray_norm = math.hypot(ray_dlat, ray_dlon) or 1e-6
    ray_dlat /= ray_norm
    ray_dlon /= ray_norm

    stub = _fan_stub_length_deg(chord, distance_km)
    junc_lat = lat1 + stub * ray_dlat
    junc_lon = lon1 + stub * ray_dlon

    fan_pts = max(2, min(5, n // 10))
    gc_lats, gc_lons = great_circle_arc(junc_lat, junc_lon, lat2, lon2, n=n - fan_pts)

    lats: list[float] = []
    lons: list[float] = []
    for i in range(fan_pts + 1):
        s = i / fan_pts if fan_pts else 1.0
        lats.append(lat1 + s * (junc_lat - lat1))
        lons.append(lon1 + s * _lon_delta(lon1, junc_lon))

    # Skip duplicate junction; append great-circle samples.
    lats.extend(gc_lats[1:])
    lons.extend(gc_lons[1:])
    return lats, lons


def great_circle_arc(
    lat1: float, lon1: float, lat2: float, lon2: float, n: int = ARC_POINTS
) -> tuple[list[float], list[float]]:
    """Sample ``n`` points along the great circle from (lat1,lon1) to (lat2,lon2).

    Uses spherical linear interpolation (slerp) of unit vectors so the line
    follows the true shortest path on the globe, which renders as a gentle
    "flight path" curve on a flat map projection.
    """
    phi1, lam1 = math.radians(lat1), math.radians(lon1)
    phi2, lam2 = math.radians(lat2), math.radians(lon2)

    x1, y1, z1 = _to_unit_vector(phi1, lam1)
    x2, y2, z2 = _to_unit_vector(phi2, lam2)

    dot = max(-1.0, min(1.0, x1 * x2 + y1 * y2 + z1 * z2))
    omega = math.acos(dot)

    lats: list[float] = []
    lons: list[float] = []
    if omega < 1e-9:  # Same point (e.g. player at a club in the capital).
        return [lat1, lat2], [lon1, lon2]

    sin_omega = math.sin(omega)
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
            entry["players"].append((player["name"], player.get("pos", "")))

        if not grouped:
            teams.append(team)
            continue

        entries = list(grouped.values())
        true_bearings = [
            _bearing_deg(team.lat, team.lon, e["dest_lat"], e["dest_lon"]) for e in entries
        ]
        display_bearings = _assign_display_bearings(true_bearings)

        for entry, display_bearing in zip(entries, display_bearings, strict=True):
            dist = haversine_km(team.lat, team.lon, entry["dest_lat"], entry["dest_lon"])
            arc_lats, arc_lons = flight_arc(
                team.lat,
                team.lon,
                entry["dest_lat"],
                entry["dest_lon"],
                display_bearing_deg=display_bearing,
                distance_km=dist,
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
        print(f"\n{len(_missing)} missing club reference(s):")
        for nat, pl, club in _missing:
            print(f"  - {nat}: {pl} -> {club}")
    else:
        print("All player clubs resolve against clubs.json.")
