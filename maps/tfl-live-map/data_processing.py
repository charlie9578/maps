"""TfL API client + transformations for tfl-live-map."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from dotenv import load_dotenv

TFL_BASE_URL = "https://api.tfl.gov.uk"
MAP_DATA_DIR = Path(__file__).resolve().parent / "data"
STOP_POINTS_CACHE = MAP_DATA_DIR / "tube_stop_points.json"
LINE_ROUTES_CACHE = MAP_DATA_DIR / "tube_line_routes.json"
DEFAULT_CACHE_MAX_AGE_DAYS = 90
ROUTES_CACHE_SCHEMA = 3
MIN_ZERO_ETA_ANIM_SECS = 3
# Max lat/lon delta when matching a refreshed segment to a previous train identity.
TRAIN_MATCH_MAX_DEG = 0.08
TRAIN_GROUP_SINGLE = "_single_"
# Min distance (degrees) between concurrent currentLocation reports to treat as separate trains.
SPLIT_MIN_DEG = 0.012

TUBE_LINE_IDS_FALLBACK = [
    "bakerloo",
    "central",
    "circle",
    "district",
    "hammersmith-city",
    "jubilee",
    "metropolitan",
    "northern",
    "piccadilly",
    "victoria",
    "waterloo-city",
]


@dataclass(frozen=True)
class TflAuth:
    app_id: str | None
    app_key: str | None


def _load_env_file() -> None:
    """Load repo-root `.env` if present (gitignored). Idempotent."""
    repo_root = Path(__file__).resolve().parents[2]
    env_path = repo_root / ".env"
    if env_path.is_file():
        load_dotenv(env_path, override=False)


def get_tfl_auth() -> TflAuth:
    """Read TfL credentials from environment variables (optional but recommended).

    As of 2026, TfL's portal only requires ``app_key`` (subscription primary key).
    See https://api-portal.tfl.gov.uk/ — ``app_id`` is legacy and may be omitted.
    """
    _load_env_file()
    # Primary / secondary subscription keys from the API portal Profile → Subscriptions.
    app_key = os.getenv("TFL_APP_KEY") or os.getenv("TFL_PRIMARY_KEY") or None
    # Legacy; only sent if explicitly set (TfL no longer requires app_id).
    app_id = os.getenv("TFL_APP_ID") or None
    return TflAuth(app_id=app_id, app_key=app_key)


def _tfl_get_json(path: str, *, auth: TflAuth, params: dict[str, Any] | None = None) -> Any:
    url = f"{TFL_BASE_URL}{path}"
    q = dict(params or {})
    if auth.app_id:
        q["app_id"] = auth.app_id
    if auth.app_key:
        q["app_key"] = auth.app_key

    resp = requests.get(url, params=q, timeout=30)
    resp.raise_for_status()
    return resp.json()


def list_tube_lines(*, auth: TflAuth) -> list[dict[str, Any]]:
    """Return line objects for Mode=tube."""
    return _tfl_get_json("/Line/Mode/tube", auth=auth)


def _cache_max_age_days() -> int:
    raw = os.getenv("TFL_CACHE_MAX_AGE_DAYS", str(DEFAULT_CACHE_MAX_AGE_DAYS)).strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_CACHE_MAX_AGE_DAYS


def _refresh_cache_requested() -> bool:
    return os.getenv("TFL_REFRESH_CACHE", "").strip().lower() in {"1", "true", "yes"}


def _read_json_cache(path: Path, *, max_age_days: int) -> dict[str, Any] | None:
    if _refresh_cache_requested() or not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        fetched_at = datetime.fromisoformat(str(payload["fetched_at"]))
        if fetched_at.tzinfo is None:
            fetched_at = fetched_at.replace(tzinfo=timezone.utc)
        age = datetime.now(tz=timezone.utc) - fetched_at.astimezone(timezone.utc)
        if age > timedelta(days=max_age_days):
            return None
        return payload
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None


def _write_json_cache(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _fetch_stop_points_from_api(*, auth: TflAuth) -> pd.DataFrame:
    data = _tfl_get_json(
        "/StopPoint/Mode/tube",
        auth=auth,
        params={
            "includeChildren": "false",
            "returnLines": "false",
            "categories": "false",
        },
    )

    points = (data or {}).get("stopPoints") or []
    rows: list[dict[str, Any]] = []
    for sp in points:
        lat = sp.get("lat")
        lon = sp.get("lon")
        naptan_id = sp.get("naptanId") or sp.get("id")
        name = sp.get("commonName") or sp.get("name")
        if lat is None or lon is None or not naptan_id or not name:
            continue
        rows.append(
            {
                "naptanId": str(naptan_id),
                "stationName": str(name),
                "lat": float(lat),
                "lon": float(lon),
            }
        )

    return pd.DataFrame.from_records(rows).drop_duplicates(subset=["naptanId"]).reset_index(drop=True)


def stops_for_map(stop_points: pd.DataFrame) -> pd.DataFrame:
    """One marker per station (TfL may return multiple naptanIds per name)."""
    if stop_points.empty:
        return stop_points
    df = stop_points.copy()
    df["stationName"] = df["stationName"].astype(str)
    return (
        df.groupby("stationName", as_index=False)
        .agg(lat=("lat", "mean"), lon=("lon", "mean"), naptanId=("naptanId", "first"))
        .reset_index(drop=True)
    )


def branch_coords(branch: list[Any]) -> list[tuple[float, float]]:
    """Coords from a route branch (stop dicts or legacy [lat, lon] pairs)."""
    if not branch:
        return []
    if isinstance(branch[0], dict):
        return [(float(s["lat"]), float(s["lon"])) for s in branch if s.get("lat") is not None]
    return [(float(a), float(b)) for a, b in branch]


def _stops_from_stop_list(stop_points: list[dict[str, Any]]) -> list[dict[str, Any]]:
    stops: list[dict[str, Any]] = []
    for sp in stop_points:
        lat = sp.get("lat")
        lon = sp.get("lon")
        naptan_id = sp.get("naptanId") or sp.get("id")
        name = sp.get("commonName") or sp.get("name") or ""
        if lat is None or lon is None or not naptan_id:
            continue
        stops.append(
            {
                "naptanId": str(naptan_id),
                "stationName": str(name),
                "lat": float(lat),
                "lon": float(lon),
            }
        )
    return stops


def _route_coord_keys(routes: dict) -> set[tuple[float, float]]:
    keys: set[tuple[float, float]] = set()
    for dirs in routes.values():
        for branches in dirs.values():
            for branch in branches:
                for lat, lon in branch_coords(branch):
                    keys.add((round(float(lat), 5), round(float(lon), 5)))
    return keys


def stops_on_routes(stop_points: pd.DataFrame, routes: dict) -> pd.DataFrame:
    """Station markers limited to stops that appear on cached route sequences."""
    if stop_points.empty or not routes:
        return stops_for_map(stop_points)
    keys = _route_coord_keys(routes)
    if not keys:
        return stops_for_map(stop_points)
    df = stop_points.copy()
    on_route = [
        (round(float(row["lat"]), 5), round(float(row["lon"]), 5)) in keys for _, row in df.iterrows()
    ]
    return stops_for_map(df.loc[on_route])


def load_stop_points(*, auth: TflAuth, data_dir: Path | None = None) -> pd.DataFrame:
    """Load tube stop points, using a local JSON cache when available."""
    cache_path = (data_dir or MAP_DATA_DIR) / STOP_POINTS_CACHE.name
    max_age = _cache_max_age_days()
    cached = _read_json_cache(cache_path, max_age_days=max_age)
    if cached and isinstance(cached.get("records"), list):
        print(f"Using cached stop points ({cache_path.name}, fetched {cached.get('fetched_at', '?')})")
        return pd.DataFrame.from_records(cached["records"])

    print(f"Fetching stop points from TfL API (will cache to {cache_path.name})…")
    df = _fetch_stop_points_from_api(auth=auth)
    _write_json_cache(
        cache_path,
        {
            "fetched_at": datetime.now(tz=timezone.utc).isoformat(),
            "source": f"{TFL_BASE_URL}/StopPoint/Mode/tube",
            "records": df.to_dict("records"),
        },
    )
    return df


def _coords_from_stop_list(stop_points: list[dict[str, Any]]) -> list[tuple[float, float]]:
    return branch_coords(_stops_from_stop_list(stop_points))


def _fetch_line_route_paths_from_api(
    *,
    auth: TflAuth,
    line_ids: list[str],
    service_types: str = "Regular",
) -> dict[str, dict[str, list[list[dict[str, Any]]]]]:
    """Fetch all route branches per line/direction from the API (with naptan ids)."""
    routes: dict[str, dict[str, list[list[dict[str, Any]]]]] = {}
    for line_id in line_ids:
        routes[line_id] = {}
        for direction in ("inbound", "outbound"):
            branches: list[list[dict[str, Any]]] = []
            try:
                data = _tfl_get_json(
                    f"/Line/{line_id}/Route/Sequence/{direction}",
                    auth=auth,
                    params={"serviceTypes": service_types},
                )
                seqs = (data or {}).get("stopPointSequences") or []
                for seq in seqs:
                    stops = _stops_from_stop_list((seq or {}).get("stopPoint") or [])
                    if stops:
                        branches.append(stops)
            except Exception:
                continue
            if branches:
                routes[line_id][direction] = branches
    return routes


def _routes_to_json(
    routes: dict[str, dict[str, list[list[dict[str, Any]]]]],
) -> dict[str, dict[str, list[list[dict[str, Any]]]]]:
    return routes


def _normalize_direction_branches(raw: list[Any]) -> list[list[Any]]:
    """Support legacy coord-only cache and stop-dict branches."""
    if not raw:
        return []
    first = raw[0]
    if isinstance(first, dict):
        return [raw]
    if isinstance(first, list):
        if first and isinstance(first[0], list):
            return [
                [{"lat": float(a), "lon": float(b), "naptanId": "", "stationName": ""} for a, b in branch]
                for branch in raw
            ]
        if first and isinstance(first[0], (int, float)):
            return [[{"lat": float(a), "lon": float(b), "naptanId": "", "stationName": ""} for a, b in raw]]
    return [branch for branch in raw]


def _routes_from_json(raw: dict[str, dict[str, list[Any]]]) -> dict[str, dict[str, list[list[Any]]]]:
    return {
        line_id: {direction: _normalize_direction_branches(branches_raw) for direction, branches_raw in dirs.items()}
        for line_id, dirs in raw.items()
    }


def load_line_route_paths(
    *,
    auth: TflAuth,
    line_ids: list[str] | None = None,
    data_dir: Path | None = None,
    service_types: str = "Regular",
) -> tuple[dict[str, dict[str, list[list[Any]]]], list[str]]:
    """Load line route polylines and line ids, using a local JSON cache when available."""
    cache_path = (data_dir or MAP_DATA_DIR) / LINE_ROUTES_CACHE.name
    max_age = _cache_max_age_days()
    cached = _read_json_cache(cache_path, max_age_days=max_age)
    if cached and cached.get("schema", 1) >= ROUTES_CACHE_SCHEMA and isinstance(cached.get("routes"), dict):
        cached_line_ids = [str(x) for x in (cached.get("line_ids") or []) if x]
        print(f"Using cached line routes ({cache_path.name}, fetched {cached.get('fetched_at', '?')})")
        return _routes_from_json(cached["routes"]), cached_line_ids or list(TUBE_LINE_IDS_FALLBACK)

    if not line_ids:
        try:
            line_ids = [str(x.get("id")) for x in list_tube_lines(auth=auth) if x.get("id")]
        except Exception:
            line_ids = list(TUBE_LINE_IDS_FALLBACK)

    print(f"Fetching line routes from TfL API (will cache to {cache_path.name})…")
    routes = _fetch_line_route_paths_from_api(auth=auth, line_ids=line_ids, service_types=service_types)
    _write_json_cache(
        cache_path,
        {
            "schema": ROUTES_CACHE_SCHEMA,
            "fetched_at": datetime.now(tz=timezone.utc).isoformat(),
            "source": f"{TFL_BASE_URL}/Line/{{id}}/Route/Sequence/{{direction}}",
            "line_ids": line_ids,
            "routes": _routes_to_json(routes),
        },
    )
    return routes, line_ids


def routes_to_store(routes: dict) -> dict:
    """JSON-serialisable payload for ``dcc.Store``."""
    return {"routes": _routes_to_json(routes)}


def routes_from_store(data: dict) -> dict:
    """Restore routes dict from ``dcc.Store`` payload."""
    if not data:
        return {}
    routes = data.get("routes") if isinstance(data, dict) else None
    if not isinstance(routes, dict):
        return {}
    return _routes_from_json(routes)


def load_static_network(*, auth: TflAuth, data_dir: Path | None = None) -> tuple[pd.DataFrame, dict, list[str]]:
    """Load cached static network metadata (stop points + route polylines)."""
    stop_points = load_stop_points(auth=auth, data_dir=data_dir)
    routes, line_ids = load_line_route_paths(auth=auth, data_dir=data_dir)
    return stop_points, routes, line_ids


def load_live_arrivals(
    *,
    auth: TflAuth,
    line_ids: list[str] | None = None,
    max_lines: int | None = None,
) -> tuple[pd.DataFrame, datetime]:
    """Fetch live arrivals per line.

    Returns:
      (df, fetched_at_utc)
    """
    fetched_at = datetime.now(tz=timezone.utc)

    if not line_ids:
        try:
            line_ids = [str(x.get("id")) for x in list_tube_lines(auth=auth) if x.get("id")]
        except Exception:
            line_ids = list(TUBE_LINE_IDS_FALLBACK)

    if max_lines is not None:
        line_ids = line_ids[: max(0, int(max_lines))]

    rows: list[dict[str, Any]] = []
    for line_id in line_ids:
        try:
            arrivals = _tfl_get_json(f"/Line/{line_id}/Arrivals", auth=auth)
            if not isinstance(arrivals, list):
                continue
        except Exception:
            # One bad line shouldn't kill the dashboard.
            continue

        for a in arrivals:
            vehicle_id = a.get("vehicleId") or a.get("vehicleID")  # be defensive
            naptan_id = a.get("naptanId")
            if not vehicle_id or not naptan_id:
                continue
            rows.append(
                {
                    "vehicleId": str(vehicle_id),
                    "lineId": str(a.get("lineId") or line_id),
                    "lineName": str(a.get("lineName") or ""),
                    "naptanId": str(naptan_id),
                    "stationName": str(a.get("stationName") or ""),
                    "platformName": str(a.get("platformName") or ""),
                    "towards": str(a.get("towards") or ""),
                    "destinationName": str(a.get("destinationName") or ""),
                    "currentLocation": str(a.get("currentLocation") or ""),
                    "direction": str(a.get("direction") or ""),
                    "timeToStation_s": int(a.get("timeToStation") or 0),
                    "expectedArrival": str(a.get("expectedArrival") or ""),
                }
            )

    if not rows:
        return pd.DataFrame(columns=["vehicleId"]), fetched_at

    return pd.DataFrame.from_records(rows), fetched_at


def normalize_direction(direction: str | None) -> str:
    """Map API direction to inbound / outbound / unknown."""
    d = (direction or "").strip().lower()
    if d in {"inbound", "outbound"}:
        return d
    return "unknown"


def current_location_key(current_location: str | None) -> str:
    """Stable key for grouping trains that share a recycled vehicleId."""
    s = re.sub(r"\s+", " ", (current_location or "").strip().casefold())
    return s if s else "unknown"


def _station_name_key(name: str) -> str:
    s = re.sub(r"\s+", " ", (name or "").strip().casefold())
    s = re.sub(r"\s+underground station$", "", s)
    return s


def _build_station_lookup(stop_points: pd.DataFrame) -> dict[str, tuple[float, float]]:
    lookup: dict[str, tuple[float, float]] = {}
    for rec in stop_points.drop_duplicates(subset=["naptanId"]).to_dict("records"):
        key = _station_name_key(str(rec.get("stationName") or ""))
        if key:
            lookup[key] = (float(rec["lat"]), float(rec["lon"]))
    return lookup


def _match_station_coords(fragment: str, lookup: dict[str, tuple[float, float]]) -> tuple[float, float] | None:
    frag = _station_name_key(fragment)
    if not frag:
        return None
    if frag in lookup:
        return lookup[frag]
    best: tuple[float, float] | None = None
    best_len = 0
    for key, coords in lookup.items():
        if frag in key or key in frag:
            if len(key) > best_len:
                best = coords
                best_len = len(key)
    return best


def resolve_coords_from_current_location(
    current_location: str,
    *,
    station_lookup: dict[str, tuple[float, float]],
) -> tuple[float, float] | None:
    """Parse TfL currentLocation text into approximate lat/lon."""
    loc = (current_location or "").strip()
    if not loc:
        return None

    at_match = re.match(r"^At\s+(.+?)(?:\s+Platform\s+\d+)?$", loc, re.IGNORECASE)
    if at_match:
        return _match_station_coords(at_match.group(1), station_lookup)

    between_match = re.match(r"^Between\s+(.+?)\s+and\s+(.+)$", loc, re.IGNORECASE)
    if between_match:
        c0 = _match_station_coords(between_match.group(1), station_lookup)
        c1 = _match_station_coords(between_match.group(2), station_lookup)
        if c0 and c1:
            return ((c0[0] + c1[0]) / 2, (c0[1] + c1[1]) / 2)

    return _match_station_coords(loc, station_lookup)


def _prepare_arrival_rows(arrivals: pd.DataFrame) -> pd.DataFrame:
    """Normalize fields; drop ambiguous direction rows per (lineId, vehicleId)."""
    if arrivals.empty:
        return arrivals

    df = arrivals.copy()
    df["direction_norm"] = df["direction"].map(normalize_direction)
    df["towards_norm"] = df["towards"].astype(str).str.strip().replace("", "unknown")
    df["location_key"] = df["currentLocation"].map(current_location_key)

    parts: list[pd.DataFrame] = []
    for _, group in df.groupby(["lineId", "vehicleId"], sort=False):
        dirs = set(group["direction_norm"])
        known = dirs - {"unknown"}
        if known and "unknown" in dirs:
            group = group[group["direction_norm"] != "unknown"]
        parts.append(group)
    return pd.concat(parts, ignore_index=True) if parts else df.iloc[0:0]


def _assign_train_group(
    arrivals: pd.DataFrame,
    *,
    station_lookup: dict[str, tuple[float, float]],
) -> pd.DataFrame:
    """Split when one vehicleId reports locations that cannot be the same train (far apart)."""
    df = arrivals.copy()
    df["train_group"] = TRAIN_GROUP_SINGLE

    for _, idx in arrivals.groupby(["lineId", "vehicleId"]).groups.items():
        sub = df.loc[idx]
        locs = sub["location_key"].astype(str).unique()
        if len(locs) <= 1:
            continue

        coords: list[tuple[float, float]] = []
        for loc in locs:
            sample = sub[sub["location_key"].astype(str) == loc].iloc[0]
            resolved = resolve_coords_from_current_location(
                str(sample.get("currentLocation") or ""),
                station_lookup=station_lookup,
            )
            if resolved:
                coords.append(resolved)

        if len(coords) < 2:
            continue

        max_sep = 0.0
        for i, c0 in enumerate(coords):
            for c1 in coords[i + 1 :]:
                d = ((c0[0] - c1[0]) ** 2 + (c0[1] - c1[1]) ** 2) ** 0.5
                max_sep = max(max_sep, d)

        if max_sep >= SPLIT_MIN_DEG:
            df.loc[idx, "train_group"] = df.loc[idx, "location_key"]

    return df


def _directions_to_try(direction: str) -> list[str]:
    d = (direction or "").strip().lower()
    if d in {"inbound", "outbound"}:
        return [d]
    return ["inbound", "outbound"]


def _resolve_route_leg(
    routes: dict,
    *,
    line_id: str,
    direction: str,
    next_naptan: str,
    following_naptan: str | None,
    tts1_s: int,
    tts2_s: int | None,
) -> tuple[float, float, float, float, int, str, str] | None:
    """Return (lat0, lon0, lat1, lon1, segment_secs, prev_name, next_name) for the approach leg."""
    line_routes = routes.get(line_id) or {}
    next_naptan = str(next_naptan)
    following_naptan = str(following_naptan) if following_naptan else None

    for dir_name in _directions_to_try(direction):
        for branch in line_routes.get(dir_name) or []:
            if not branch or not isinstance(branch[0], dict):
                continue
            ids = [str(s.get("naptanId") or "") for s in branch if s.get("naptanId")]
            if next_naptan not in ids:
                continue
            idx = ids.index(next_naptan)
            nxt = branch[idx]

            travel: str | None = None
            if following_naptan and following_naptan in ids:
                fidx = ids.index(following_naptan)
                if fidx == idx + 1:
                    travel = "forward"
                elif fidx == idx - 1:
                    travel = "backward"
                else:
                    continue
            elif idx > 0:
                travel = "forward"
            elif idx + 1 < len(branch):
                travel = "backward"
            else:
                travel = "forward"

            if travel == "forward":
                prev_idx = idx - 1 if idx > 0 else idx
            else:
                prev_idx = idx + 1 if idx + 1 < len(branch) else idx

            prev = branch[prev_idx]
            if tts2_s is not None and tts2_s > tts1_s:
                segment_secs = max(30, int(tts2_s - tts1_s), int(tts1_s))
            else:
                segment_secs = max(30, min(600, int(tts1_s) if tts1_s > 0 else 120))

            return (
                float(prev["lat"]),
                float(prev["lon"]),
                float(nxt["lat"]),
                float(nxt["lon"]),
                segment_secs,
                str(prev.get("stationName") or ""),
                str(nxt.get("stationName") or ""),
            )
    return None


def build_vehicle_segments(
    arrivals: pd.DataFrame,
    *,
    stop_points: pd.DataFrame,
    routes: dict,
) -> pd.DataFrame:
    """Build per-vehicle segments along the route: previous stop -> next predicted stop."""
    if arrivals.empty:
        return pd.DataFrame(columns=["vehicleId"])

    sp = stop_points[["naptanId", "lat", "lon", "stationName"]].drop_duplicates(subset=["naptanId"])
    a = arrivals.merge(sp, how="left", on="naptanId", suffixes=("", "_sp"))
    a = a.dropna(subset=["lat", "lon"])
    if a.empty:
        return pd.DataFrame(columns=["vehicleId"])

    a = _prepare_arrival_rows(a)
    if a.empty:
        return pd.DataFrame(columns=["vehicleId"])

    station_lookup = _build_station_lookup(sp)
    a = _assign_train_group(a, station_lookup=station_lookup)

    # Split by location only when the same vehicleId reports multiple places at once.
    train_key = ["lineId", "vehicleId", "train_group"]
    sort_cols = [*train_key, "timeToStation_s"]
    a = a.sort_values(sort_cols, ascending=[True, True, True, True], kind="mergesort")
    a["rank"] = a.groupby(train_key, dropna=False).cumcount() + 1
    next_rows = a[a["rank"] == 1].copy()
    follow_rows = (
        a[a["rank"] == 2][[*train_key, "naptanId", "timeToStation_s"]]
        .rename(columns={"naptanId": "naptanId_2", "timeToStation_s": "tts2_s"})
        .drop_duplicates(subset=train_key)
    )
    merged = next_rows.merge(follow_rows, how="left", on=train_key)

    rows: list[dict[str, Any]] = []
    for rec in merged.to_dict("records"):
        cur_loc = str(rec.get("currentLocation") or "")
        leg = _resolve_route_leg(
            routes,
            line_id=str(rec.get("lineId") or ""),
            direction=str(rec.get("direction_norm") or rec.get("direction") or ""),
            next_naptan=str(rec.get("naptanId") or ""),
            following_naptan=str(rec["naptanId_2"]) if rec.get("naptanId_2") else None,
            tts1_s=int(rec.get("timeToStation_s") or 0),
            tts2_s=int(rec["tts2_s"]) if pd.notna(rec.get("tts2_s")) else None,
        )
        loc_coords = resolve_coords_from_current_location(cur_loc, station_lookup=station_lookup)
        if leg:
            lat0, lon0, lat1, lon1, segment_secs, station_name_0, station_name_1 = leg
            if loc_coords:
                lat0, lon0 = loc_coords
                if cur_loc:
                    station_name_0 = cur_loc
        else:
            lat1 = float(rec["lat"])
            lon1 = float(rec["lon"])
            if loc_coords:
                lat0, lon0 = loc_coords
                station_name_0 = cur_loc or str(rec.get("stationName") or "")
            else:
                lat0, lon0 = lat1, lon1
                station_name_0 = str(rec.get("stationName") or "")
            segment_secs = max(30, int(rec.get("timeToStation_s") or 120))
            station_name_1 = station_name_0

        rows.append(
            {
                "vehicleId": str(rec["vehicleId"]),
                "lineId": str(rec.get("lineId") or ""),
                "lineName": str(rec.get("lineName") or ""),
                "direction": str(rec.get("direction_norm") or normalize_direction(str(rec.get("direction") or ""))),
                "direction_norm": str(rec.get("direction_norm") or "unknown"),
                "towards_norm": str(rec.get("towards_norm") or "unknown"),
                "currentLocation": cur_loc,
                "location_key": str(rec.get("location_key") or ""),
                "naptanId_1": str(rec.get("naptanId") or ""),
                "stationName_0": station_name_0,
                "stationName_1": station_name_1 or str(rec.get("stationName") or ""),
                "platformName_1": str(rec.get("platformName") or ""),
                "towards_1": str(rec.get("towards") or ""),
                "tts1_s": int(rec.get("timeToStation_s") or 0),
                "lat0": lat0,
                "lon0": lon0,
                "lat1": lat1,
                "lon1": lon1,
                "segment_secs": int(segment_secs),
            }
        )

    return pd.DataFrame.from_records(rows)


def _segment_pos(rec: dict[str, Any]) -> tuple[float, float]:
    lat = rec.get("lat0", rec.get("lat1"))
    lon = rec.get("lon0", rec.get("lon1"))
    return float(lat or 0.0), float(lon or 0.0)


def _train_id_parts(train_id: str) -> tuple[str, str, int]:
    line_id, vehicle_id, slot_s = str(train_id).rsplit(":", 2)
    return line_id, vehicle_id, int(slot_s)


def _make_train_id(line_id: str, vehicle_id: str, slot: int) -> str:
    return f"{line_id}:{vehicle_id}:{slot}"


def _match_cost(new_rec: dict[str, Any], prev_rec: dict[str, Any]) -> float:
    """Lower is better. Primary signal is map position; tie-break with route metadata."""
    n_pos = _segment_pos(new_rec)
    p_pos = _segment_pos(prev_rec)
    cost = (n_pos[0] - p_pos[0]) ** 2 + (n_pos[1] - p_pos[1]) ** 2
    if str(new_rec.get("naptanId_1") or "") != str(prev_rec.get("naptanId_1") or ""):
        cost += 0.0004
    if str(new_rec.get("towards_1") or "") != str(prev_rec.get("towards_1") or ""):
        cost += 0.0002
    if str(new_rec.get("direction_norm") or "") != str(prev_rec.get("direction_norm") or ""):
        cost += 0.0001
    return cost


def assign_stable_train_ids(
    segments: pd.DataFrame,
    *,
    previous: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Match refreshed segments to prior train_id so moving trains keep one marker."""
    if segments.empty:
        return segments

    df = segments.copy()
    df["train_id"] = ""
    prev = previous if previous is not None and not previous.empty else pd.DataFrame()
    max_d2 = TRAIN_MATCH_MAX_DEG**2

    for (line_id, vehicle_id), new_group in df.groupby(["lineId", "vehicleId"], sort=False):
        new_idxs = list(new_group.index)
        prev_rows = (
            prev[(prev["lineId"].astype(str) == str(line_id)) & (prev["vehicleId"].astype(str) == str(vehicle_id))]
            if not prev.empty and "train_id" in prev.columns
            else pd.DataFrame()
        )
        prev_records = prev_rows.to_dict("records")

        if not prev_records:
            for slot, idx in enumerate(new_idxs):
                df.at[idx, "train_id"] = _make_train_id(str(line_id), str(vehicle_id), slot)
            continue

        pairs: list[tuple[float, int, int, str]] = []
        for new_idx in new_idxs:
            new_rec = df.loc[new_idx].to_dict()
            for j, prev_rec in enumerate(prev_records):
                cost = _match_cost(new_rec, prev_rec)
                if cost <= max_d2:
                    pid = str(prev_rec.get("train_id") or "")
                    pairs.append((cost, new_idx, j, pid))

        pairs.sort(key=lambda x: x[0])
        used_new: set[int] = set()
        used_prev: set[int] = set()
        for _cost, new_idx, j, pid in pairs:
            if new_idx in used_new or j in used_prev:
                continue
            df.at[new_idx, "train_id"] = pid
            used_new.add(new_idx)
            used_prev.add(j)

        used_slots = {
            _train_id_parts(str(prev_records[j].get("train_id") or ""))[2] for j in used_prev
        }
        for new_idx in new_idxs:
            if new_idx in used_new:
                continue
            for rec in prev_records:
                tid = str(rec.get("train_id") or "")
                if tid:
                    used_slots.add(_train_id_parts(tid)[2])
            slot = 0
            while slot in used_slots:
                slot += 1
            df.at[new_idx, "train_id"] = _make_train_id(str(line_id), str(vehicle_id), slot)
            used_slots.add(slot)

    return df


def interpolate_positions(
    segments: pd.DataFrame,
    *,
    elapsed_s: float | pd.Series,
    min_zero_eta_secs: int = MIN_ZERO_ETA_ANIM_SECS,
) -> pd.DataFrame:
    """Interpolate train positions toward the next predicted stop using ETA timing."""
    if segments.empty:
        return segments.copy()

    df = segments.copy()
    tts = df["tts1_s"].astype(float)
    duration = tts.where(tts > 0, float(min_zero_eta_secs))
    if isinstance(elapsed_s, pd.Series):
        elapsed = elapsed_s.reindex(df.index).astype(float).clip(lower=0.0)
    else:
        elapsed = float(elapsed_s)
    frac = (elapsed / duration).clip(lower=0.0, upper=1.0)

    df["timeToStation_s"] = (duration * (1.0 - frac)).round().astype(int)
    df["lat"] = (1.0 - frac) * df["lat0"].astype(float) + frac * df["lat1"].astype(float)
    df["lon"] = (1.0 - frac) * df["lon0"].astype(float) + frac * df["lon1"].astype(float)
    return df


def merge_line_segments(
    existing: pd.DataFrame,
    new_line_segments: pd.DataFrame,
    *,
    line_id: str,
) -> pd.DataFrame:
    """Replace segments for one line, keeping all other lines unchanged."""
    if existing.empty:
        return new_line_segments.copy()
    if new_line_segments.empty:
        return existing[existing["lineId"].astype(str) != str(line_id)].copy()
    kept = existing[existing["lineId"].astype(str) != str(line_id)]
    return pd.concat([kept, new_line_segments], ignore_index=True)


def filter_df(
    df: pd.DataFrame,
    *,
    line_ids: list[str] | None,
    search_text: str | None,
) -> pd.DataFrame:
    """Apply sidebar filters. Extend with sliders, date ranges, etc."""
    dff = df
    if line_ids and "lineId" in dff.columns:
        dff = dff[dff["lineId"].isin(line_ids)]
    if search_text and search_text.strip() and "vehicleId" in dff.columns:
        q = search_text.strip().casefold()
        dff = dff[dff["vehicleId"].astype(str).str.casefold().str.contains(q, na=False)]
    return dff


def sorted_unique(df: pd.DataFrame, col: str) -> list[str]:
    vals = df[col].dropna().astype(str).str.strip()
    vals = vals[vals.ne("")].unique().tolist()
    return sorted(vals, key=lambda x: x.casefold())
