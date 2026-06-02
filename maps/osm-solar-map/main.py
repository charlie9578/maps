"""Malta solar installations from OpenStreetMap (Overpass API). Run from repo root:

    python maps/osm-solar-map/main.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import folium
import pandas as pd
import requests
from folium.plugins import MarkerCluster

MAP_DIR = Path(__file__).resolve().parent
DATA_DIR = MAP_DIR / "data"
OUTPUT_DIR = MAP_DIR / "output"

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OSM_USER_AGENT = "maps-repo/1.0 (educational; contact via GitHub maps)"
CACHED_GEOJSON = DATA_DIR / "osm-solar-malta.geojson"
OUTPUT_HTML = OUTPUT_DIR / "osm_solar_malta.html"

# Malta + Gozo bounding box (south, west, north, east).
MALTA_BBOX = (35.78, 14.18, 36.15, 14.72)

OVERPASS_QUERY = f"""
[out:json][timeout:60];
(
  nwr{MALTA_BBOX}["plant:source"="solar"];
);
out center tags;
"""

MALTA_BOUNDS = {"min_lat": 35.78, "max_lat": 36.15, "min_lon": 14.18, "max_lon": 14.72}


def _normalize_frame(frame: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "osm_type",
        "osm_id",
        "lat",
        "lon",
        "name",
        "operator",
        "capacity_mw",
        "power",
    ]
    if frame.empty:
        return pd.DataFrame(columns=columns)
    for col in columns:
        if col not in frame.columns:
            frame[col] = pd.NA
    return frame[columns]


def fetch_overpass(*, refresh: bool = False) -> pd.DataFrame:
    """Download Malta solar features from Overpass or load cached GeoJSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not refresh and CACHED_GEOJSON.is_file():
        return _normalize_frame(
            _geojson_to_frame(json.loads(CACHED_GEOJSON.read_text(encoding="utf-8")))
        )

    response = requests.post(
        OVERPASS_URL,
        data={"data": OVERPASS_QUERY},
        headers={"User-Agent": OSM_USER_AGENT},
        timeout=120,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("remark"):
        raise RuntimeError(f"Overpass error: {payload['remark']}")
    frame = _normalize_frame(_overpass_to_frame(payload.get("elements", [])))
    CACHED_GEOJSON.write_text(
        json.dumps(_frame_to_geojson_dict(frame), indent=2),
        encoding="utf-8",
    )
    return frame


def _overpass_to_frame(elements: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for element in elements:
        tags = element.get("tags") or {}
        if element["type"] == "node":
            lat, lon = element.get("lat"), element.get("lon")
        else:
            center = element.get("center")
            if not center:
                continue
            lat, lon = center.get("lat"), center.get("lon")
        if lat is None or lon is None:
            continue
        rows.append(
            {
                "osm_type": element["type"],
                "osm_id": element["id"],
                "lat": float(lat),
                "lon": float(lon),
                "name": tags.get("name"),
                "operator": tags.get("operator"),
                "capacity_mw": _parse_capacity_mw(tags),
                "power": tags.get("power"),
            }
        )
    return pd.DataFrame(rows)


def _parse_capacity_mw(tags: dict[str, str]) -> float | None:
    for key in ("plant:output:electricity", "generator:output:electricity"):
        raw = tags.get(key)
        if not raw:
            continue
        value = raw.strip().lower().replace(",", "")
        if value.endswith(" mw"):
            try:
                return float(value.removesuffix(" mw"))
            except ValueError:
                continue
        if value.endswith("mw"):
            try:
                return float(value.removesuffix("mw"))
            except ValueError:
                continue
        if value.endswith(" kw"):
            try:
                return float(value.removesuffix(" kw")) / 1000.0
            except ValueError:
                continue
        if value.endswith("kw"):
            try:
                return float(value.removesuffix("kw")) / 1000.0
            except ValueError:
                continue
        try:
            return float(value)
        except ValueError:
            continue
    return None


def _geojson_to_frame(geojson: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for feature in geojson.get("features", []):
        props = feature.get("properties") or {}
        geom = feature.get("geometry") or {}
        coords = geom.get("coordinates")
        if not coords or len(coords) < 2:
            continue
        lon, lat = coords[0], coords[1]
        rows.append({**props, "lat": lat, "lon": lon})
    return pd.DataFrame(rows)


def _frame_to_geojson_dict(frame: pd.DataFrame) -> dict[str, Any]:
    features: list[dict[str, Any]] = []
    for row in frame.to_dict(orient="records"):
        lat = row.pop("lat")
        lon = row.pop("lon")
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {k: v for k, v in row.items() if pd.notna(v)},
            }
        )
    return {"type": "FeatureCollection", "features": features}


def popup_html(row: pd.Series) -> str:
    name = row["name"] if pd.notna(row["name"]) else "Unnamed solar site"
    parts = [f"<b>{name}</b>"]
    parts.append(f"OSM {row['osm_type']}/{row['osm_id']}")
    if pd.notna(row.get("operator")):
        parts.append(f"Operator: {row['operator']}")
    if pd.notna(row.get("capacity_mw")):
        parts.append(f"Capacity: {row['capacity_mw']:.3g} MW")
    if pd.notna(row.get("power")):
        parts.append(f"power={row['power']}")
    return "<br>".join(parts)


def build_solar_map(frame: pd.DataFrame) -> folium.Map:
    """Interactive map of solar features, clustered for performance."""
    m = folium.Map(
        location=[35.94, 14.45],
        zoom_start=11,
        min_zoom=10,
        max_bounds=[
            [MALTA_BOUNDS["min_lat"], MALTA_BOUNDS["min_lon"]],
            [MALTA_BOUNDS["max_lat"], MALTA_BOUNDS["max_lon"]],
        ],
        # Avoid hitting volunteer-run OSM tile servers from embedded HTML.
        tiles="CartoDB Positron",
    )
    cluster = MarkerCluster(name="Solar sites").add_to(m)

    for _, row in frame.iterrows():
        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=6,
            color="#b45309",
            fill=True,
            fill_color="#fbbf24",
            fill_opacity=0.85,
            weight=1,
            popup=folium.Popup(popup_html(row), max_width=320),
        ).add_to(cluster)

    folium.LayerControl().add_to(m)
    title = (
        f"Malta solar plants (OpenStreetMap) — {len(frame):,} features"
        if len(frame)
        else "Malta solar plants (OpenStreetMap) — no features"
    )
    m.get_root().html.add_child(
        folium.Element(
            f'<div style="position:fixed;top:10px;left:50px;z-index:9999;'
            f"background:white;padding:8px 12px;border-radius:4px;"
            f'box-shadow:0 1px 4px rgba(0,0,0,.2);font:14px system-ui,sans-serif;">'
            f"{title}</div>"
        )
    )
    return m


def write_map(output_path: Path, *, refresh_data: bool = False) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    frame = fetch_overpass(refresh=refresh_data)
    folium_map = build_solar_map(frame)
    folium_map.save(output_path)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Malta OSM solar map.")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Re-query the Overpass API (ignores cached GeoJSON).",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=OUTPUT_HTML,
        help=f"Output HTML path (default: {OUTPUT_HTML.name}).",
    )
    args = parser.parse_args()
    path = write_map(args.output, refresh_data=args.refresh)
    frame = fetch_overpass(refresh=False)
    named = int(frame["name"].notna().sum()) if "name" in frame.columns else 0
    print(f"Wrote {path}")
    print(f"Features: {len(frame):,} ({named:,} with a name tag).")
    print(f"Cache: {CACHED_GEOJSON}")
    print("Open the HTML in a browser; data © OpenStreetMap contributors (ODbL).")


if __name__ == "__main__":
    main()
