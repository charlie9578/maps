from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class DataColumns:
    country: str = "Country/Area"
    project: str = "Project Name"
    phase: str = "Phase Name"
    project_local_name: str = "Project Name in Local Language / Script"
    other_names: str = "Other Name(s)"
    capacity_mw: str = "Capacity (MW)"
    installation_type: str = "Installation Type"
    status: str = "Status"
    start_year: str = "Start year"
    retired_year: str = "Retired year"
    operator: str = "Operator"
    owner: str = "Owner"
    hydrogen: str = "Hydrogen"
    storage: str = "Associated Storage"
    lat: str = "Latitude"
    lon: str = "Longitude"
    city: str = "City"
    state_province: str = "State/Province"
    region: str = "Region"
    subregion: str = "Subregion"
    wiki: str = "Wiki URL"


COL = DataColumns()


def _to_float(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def normalize_status(status: str) -> str:
    s = (status or "").strip()
    if not s:
        return s
    s_lower = s.casefold()
    if "shelved" in s_lower or "cancelled" in s_lower or "canceled" in s_lower:
        return "cancelled"
    if "mothballed" in s_lower or "retired" in s_lower:
        return "retired"
    return s


def load_data(data_path: Path) -> pd.DataFrame:
    if not data_path.exists():
        raise FileNotFoundError(f"Missing data file: {data_path}")

    df = pd.read_excel(data_path, sheet_name="Data")

    keep = [
        COL.country,
        COL.project,
        COL.phase,
        COL.capacity_mw,
        COL.installation_type,
        COL.status,
        COL.start_year,
        COL.retired_year,
        COL.hydrogen,
        COL.storage,
        COL.lat,
        COL.lon,
        COL.operator,
        COL.owner,
        COL.wiki,
        COL.city,
        COL.state_province,
        COL.subregion,
        COL.region,
    ]
    df = df[keep].copy()

    df[COL.capacity_mw] = _to_float(df[COL.capacity_mw])
    df[COL.lat] = _to_float(df[COL.lat])
    df[COL.lon] = _to_float(df[COL.lon])
    df[COL.start_year] = _to_float(df[COL.start_year])
    df[COL.retired_year] = _to_float(df[COL.retired_year])

    for c in [COL.country, COL.project, COL.phase, COL.installation_type, COL.status]:
        df[c] = df[c].astype("string").fillna("").str.strip()

    df[COL.status] = df[COL.status].map(lambda v: normalize_status(str(v)))

    df = df.dropna(subset=[COL.lat, COL.lon, COL.capacity_mw])
    df = df[df[COL.capacity_mw] > 0]

    df["Project (display)"] = df[COL.project]
    has_phase = df[COL.phase].fillna("").astype(str).str.strip().ne("") & df[COL.phase].ne("<NA>")
    df.loc[has_phase, "Project (display)"] = (
        df.loc[has_phase, COL.project].astype(str) + " — " + df.loc[has_phase, COL.phase].astype(str)
    )

    df["Has hydrogen"] = df[COL.hydrogen].notna() & df[COL.hydrogen].astype("string").str.strip().ne("")
    df["Has storage"] = df[COL.storage].notna() & df[COL.storage].astype("string").str.strip().ne("")

    return df


def sorted_unique(df: pd.DataFrame, col: str) -> list[str]:
    vals = df[col].dropna().astype(str).str.strip()
    vals = vals[vals.ne("")].unique().tolist()
    return sorted(vals, key=lambda x: x.casefold())


def filter_df(
    df: pd.DataFrame,
    *,
    countries: list[str] | None,
    statuses: list[str] | None,
    installation_types: list[str] | None,
    capacity_range: list[float] | None,
    start_year_range: list[float] | None,
    require_hydrogen: bool,
    require_storage: bool,
    search_text: str | None,
) -> pd.DataFrame:
    dff = df

    if countries:
        dff = dff[dff[COL.country].isin(countries)]
    if statuses:
        dff = dff[dff[COL.status].isin(statuses)]
    if installation_types:
        dff = dff[dff[COL.installation_type].isin(installation_types)]

    if capacity_range and len(capacity_range) == 2:
        lo, hi = capacity_range
        dff = dff[(dff[COL.capacity_mw] >= lo) & (dff[COL.capacity_mw] <= hi)]

    if start_year_range and len(start_year_range) == 2:
        lo, hi = start_year_range
        sy = dff[COL.start_year]
        dff = dff[(sy.isna()) | ((sy >= lo) & (sy <= hi))]

    if require_hydrogen:
        dff = dff[dff["Has hydrogen"]]
    if require_storage:
        dff = dff[dff["Has storage"]]

    if search_text and search_text.strip():
        q = search_text.strip().casefold()
        hay = (
            dff[COL.project].astype(str).str.casefold()
            + " "
            + dff[COL.phase].astype(str).str.casefold()
            + " "
            + dff[COL.operator].astype(str).str.casefold()
            + " "
            + dff[COL.owner].astype(str).str.casefold()
        )
        dff = dff[hay.str.contains(q, na=False)]

    return dff

