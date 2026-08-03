"""Load Glasgow 2026 team data and construct great-circle routes to Glasgow."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

MAP_DIR = Path(__file__).resolve().parent
DATA_FILE = MAP_DIR / "data" / "teams.json"
SPORT_MEDALS_FILE = MAP_DIR / "data" / "sport_medals.json"

ISO2 = {
    "AIA":"AI","ANT":"AG","AUS":"AU","BAN":"BD","BAR":"BB","BIZ":"BZ","BER":"BM","BOT":"BW","IVB":"VG","BRU":"BN",
    "CMR":"CM","CAN":"CA","CAY":"KY","COK":"CK","CYP":"CY","DMA":"DM","ENG":"GB","SWZ":"SZ","FLK":"FK","FIJ":"FJ",
    "GAB":"GA","GHA":"GH","GIB":"GI","GRN":"GD","GGY":"GG","GUY":"GY","IND":"IN","IOM":"IM","JAM":"JM","JEY":"JE",
    "KEN":"KE","KIR":"KI","LES":"LS","MAW":"MW","MAS":"MY","MDV":"MV","MLT":"MT","MRI":"MU","MNT":"MS","MOZ":"MZ",
    "NAM":"NA","NRU":"NR","NZL":"NZ","NGR":"NG","NIU":"NU","NFK":"NF","NIR":"GB","PAK":"PK","PNG":"PG","RWA":"RW",
    "LCA":"LC","SAM":"WS","SCO":"GB","SEY":"SC","SLE":"SL","SGP":"SG","SOL":"SB","RSA":"ZA","SRI":"LK","SHN":"SH",
    "SKN":"KN","VIN":"VC","TZA":"TZ","BAH":"BS","GAM":"GM","TOG":"TG","TGA":"TO","TTO":"TT","TCA":"TC","TUV":"TV",
    "UGA":"UG","VAN":"VU","WAL":"GB","ZAM":"ZM"
}

ISO3 = {
    "AIA":"AIA","ANT":"ATG","AUS":"AUS","BAN":"BGD","BAR":"BRB","BIZ":"BLZ","BER":"BMU","BOT":"BWA","IVB":"VGB","BRU":"BRN",
    "CMR":"CMR","CAN":"CAN","CAY":"CYM","COK":"COK","CYP":"CYP","DMA":"DMA","ENG":"GBR","SWZ":"SWZ","FLK":"FLK","FIJ":"FJI",
    "GAB":"GAB","GHA":"GHA","GIB":"GIB","GRN":"GRD","GGY":"GGY","GUY":"GUY","IND":"IND","IOM":"IMN","JAM":"JAM","JEY":"JEY",
    "KEN":"KEN","KIR":"KIR","LES":"LSO","MAW":"MWI","MAS":"MYS","MDV":"MDV","MLT":"MLT","MRI":"MUS","MNT":"MSR","MOZ":"MOZ",
    "NAM":"NAM","NRU":"NRU","NZL":"NZL","NGR":"NGA","NIU":"NIU","NFK":"NFK","NIR":"GBR","PAK":"PAK","PNG":"PNG","RWA":"RWA",
    "LCA":"LCA","SAM":"WSM","SCO":"GBR","SEY":"SYC","SLE":"SLE","SGP":"SGP","SOL":"SLB","RSA":"ZAF","SRI":"LKA","SHN":"SHN",
    "SKN":"KNA","VIN":"VCT","TZA":"TZA","BAH":"BHS","GAM":"GMB","TOG":"TGO","TGA":"TON","TTO":"TTO","TCA":"TCA","TUV":"TUV",
    "UGA":"UGA","VAN":"VUT","WAL":"GBR","ZAM":"ZMB"
}


def flag_for(code: str) -> str:
    subdivisions = {
        "ENG": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
        "SCO": "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
        "WAL": "🏴󠁧󠁢󠁷󠁬󠁳󠁿",
    }
    if code in subdivisions:
        return subdivisions[code]
    return "".join(chr(0x1F1E6 + ord(letter) - ord("A")) for letter in ISO2[code])


def flag_slug(code: str) -> str:
    """Circle Flags identifier, including the four UK home-nation teams."""
    subdivisions = {"ENG": "gb-eng", "NIR": "gb-nir", "SCO": "gb-sct", "WAL": "gb-wls"}
    return subdivisions.get(code, ISO2[code].lower())


def flag_url(code: str) -> str:
    return f"https://hatscripts.github.io/circle-flags/flags/{flag_slug(code)}.svg"


def rectangular_flag_url(code: str) -> str:
    """Rectangular SVG used where the compact circular crop loses detail."""
    return f"https://flagcdn.com/{flag_slug(code)}.svg"


@dataclass(frozen=True)
class Team:
    name: str
    code: str
    city: str
    lat: float
    lon: float
    gold: int
    silver: int
    bronze: int

    @property
    def total(self) -> int:
        return self.gold + self.silver + self.bronze


def load_data() -> tuple[dict, list[Team]]:
    raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    teams = [Team(**row) for row in raw["teams"]]
    codes = [team.code for team in teams]
    if len(teams) != 74:
        raise ValueError(f"Expected 74 teams, found {len(teams)}")
    if len(set(codes)) != len(codes):
        raise ValueError("Team codes must be unique")
    if any(min(team.gold, team.silver, team.bronze) < 0 for team in teams):
        raise ValueError("Medal counts cannot be negative")
    totals = tuple(sum(getattr(team, medal) for team in teams) for medal in ("gold", "silver", "bronze"))
    if totals != (216, 215, 243):
        raise ValueError(f"Unexpected medal totals: {totals}")
    return raw, teams


def load_sport_medals(teams: list[Team]) -> tuple[list[tuple[str, str, str]], dict[tuple[str, str], tuple[int, int, int]]]:
    """Load the official sport report totals and reconcile them to the medal table."""
    raw = json.loads(SPORT_MEDALS_FILE.read_text(encoding="utf-8"))
    sports = [tuple(sport) for sport in raw["sports"]]
    sport_ids = {sport_id for sport_id, _, _ in sports}
    team_by_code = {team.code: team for team in teams}
    medals: dict[tuple[str, str], tuple[int, int, int]] = {}
    for code, sport_id, gold, silver, bronze in raw["rows"]:
        if code not in team_by_code or sport_id not in sport_ids:
            raise ValueError(f"Unknown team/sport in sport medals: {code}/{sport_id}")
        key = (code, sport_id)
        if key in medals:
            raise ValueError(f"Duplicate sport medal row: {code}/{sport_id}")
        medals[key] = (gold, silver, bronze)

    for team in teams:
        totals = tuple(
            sum(medals.get((team.code, sport_id), (0, 0, 0))[index] for sport_id, _, _ in sports)
            for index in range(3)
        )
        if totals != (team.gold, team.silver, team.bronze):
            raise ValueError(f"Sport medals do not reconcile for {team.code}: {totals}")
    return sports, medals


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * radius * math.asin(min(1.0, math.sqrt(a)))


def great_circle_arc(
    lat1: float, lon1: float, lat2: float, lon2: float, *, segments: int
) -> tuple[list[float], list[float]]:
    """Return a great-circle arc that never crosses the map's ±180° seam.

    The shorter leg is preferred. If it crosses the antimeridian, the alternate
    great-circle leg is used so a route remains one continuous on-screen path.
    """
    p1, l1, p2, l2 = map(math.radians, (lat1, lon1, lat2, lon2))
    a = (math.cos(p1) * math.cos(l1), math.cos(p1) * math.sin(l1), math.sin(p1))
    b = (math.cos(p2) * math.cos(l2), math.cos(p2) * math.sin(l2), math.sin(p2))
    omega_short = math.acos(
        max(-1.0, min(1.0, sum(x * y for x, y in zip(a, b, strict=True))))
    )
    if omega_short < 1e-9:
        return [lat1, lat2], [lon1, lon2]

    short_lats, short_lons = _slerp_arc(a, b, omega_short, segments)
    if not _crosses_antimeridian(short_lons):
        return short_lats, short_lons
    return _slerp_arc(a, b, 2 * math.pi - omega_short, segments)


def _slerp_arc(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
    omega: float,
    segments: int,
) -> tuple[list[float], list[float]]:
    sin_omega = math.sin(omega)
    lats: list[float] = []
    lons: list[float] = []
    for index in range(segments + 1):
        fraction = index / segments
        w1 = math.sin((1 - fraction) * omega) / sin_omega
        w2 = math.sin(fraction * omega) / sin_omega
        x, y, z = (w1 * a[i] + w2 * b[i] for i in range(3))
        lats.append(math.degrees(math.atan2(z, math.hypot(x, y))))
        lons.append(math.degrees(math.atan2(y, x)))
    return lats, lons


def _crosses_antimeridian(lons: list[float]) -> bool:
    return any(abs(lons[index] - lons[index - 1]) > 180 for index in range(1, len(lons)))


def split_segments(
    lats: list[float], lons: list[float], labels: list[str]
) -> dict[str, tuple[list[float | None], list[float | None]]]:
    """Group labelled arc segments into Plotly polylines and break at ±180°."""
    grouped: dict[str, tuple[list[float | None], list[float | None]]] = {}
    for index, label in enumerate(labels):
        out_lats, out_lons = grouped.setdefault(label, ([], []))
        if abs(lons[index + 1] - lons[index]) <= 180:
            out_lats.extend((lats[index], lats[index + 1], None))
            out_lons.extend((lons[index], lons[index + 1], None))
    return grouped
