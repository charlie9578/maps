"""Interactive OWID-style CO₂ per-capita choropleth. Run from repo root:

    python maps/interactive-owid-map/main.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

MAP_DIR = Path(__file__).resolve().parent
DATA_DIR = MAP_DIR / "data"
OUTPUT_DIR = MAP_DIR / "output"

OWID_USER_AGENT = "maps-repo/1.0 (educational; https://github.com/maps)"
OWID_CSV_URL = (
    "https://ourworldindata.org/explorers/co2.csv"
    "?v=1&csvType=full&useColumnShortNames=true"
    "&Gas+or+Warming=CO%E2%82%82"
    "&Accounting=Territorial"
    "&Fuel+or+Land+Use+Change=All+fossil+emissions"
    "&Count=Per+capita"
    "&hideControls=false"
)
CACHED_CSV = DATA_DIR / "co2-per-capita-territorial.csv"
OUTPUT_HTML = OUTPUT_DIR / "co2_per_capita_map.html"

# Approximates the sequential blues used on OWID emission maps.
OWID_COLOR_SCALE = [
    [0.0, "#f7fbff"],
    [0.125, "#deebf7"],
    [0.25, "#c6dbef"],
    [0.375, "#9ecae1"],
    [0.5, "#6baed6"],
    [0.625, "#4292c6"],
    [0.75, "#2171b5"],
    [0.875, "#08519c"],
    [1.0, "#08306b"],
]


def load_emissions(*, refresh: bool = False) -> pd.DataFrame:
    """Load territorial CO₂ per capita; download from OWID if missing."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if refresh or not CACHED_CSV.is_file():
        df = pd.read_csv(OWID_CSV_URL, storage_options={"User-Agent": OWID_USER_AGENT})
        df.to_csv(CACHED_CSV, index=False)
    else:
        df = pd.read_csv(CACHED_CSV)

    out = df.rename(
        columns={
            "entity": "country",
            "code": "iso_code",
            "emissions_total_per_capita": "emissions_per_capita",
        }
    )
    # Normalise alternate header casing from cached exports.
    if "Entity" in out.columns:
        out = out.rename(
            columns={
                "Entity": "country",
                "Code": "iso_code",
                "Year": "year",
            }
        )
    if "year" not in out.columns and "Year" in out.columns:
        out = out.rename(columns={"Year": "year"})

    out = out.dropna(subset=["iso_code"])
    out["iso_code"] = out["iso_code"].astype(str)
    out["year"] = out["year"].astype(int)
    out["emissions_per_capita"] = pd.to_numeric(out["emissions_per_capita"], errors="coerce")
    return fill_missing_years(out)


def fill_missing_years(df: pd.DataFrame) -> pd.DataFrame:
    """Expand each country to every year (min–max), forward-fill gaps, flag estimates."""
    year_min = int(df["year"].min())
    year_max = int(df["year"].max())
    all_years = list(range(year_min, year_max + 1))

    chunks: list[pd.DataFrame] = []
    grouped = df.groupby("iso_code", sort=False)
    for iso_code, group in grouped:
        country = group["country"].iloc[0]
        series = (
            group.drop_duplicates("year", keep="last")
            .set_index("year")["emissions_per_capita"]
            .sort_index()
        )
        expanded = series.reindex(all_years)
        had_value = expanded.notna()
        filled = expanded.ffill()
        is_estimated = (~had_value) & filled.notna()

        chunks.append(
            pd.DataFrame(
                {
                    "country": country,
                    "iso_code": iso_code,
                    "year": all_years,
                    "emissions_per_capita": filled,
                    "is_estimated": is_estimated,
                }
            )
        )

    out = pd.concat(chunks, ignore_index=True)
    out = out.dropna(subset=["emissions_per_capita"])
    return out.sort_values(["year", "iso_code"], ascending=[True, True])


def format_per_capita(tonnes: float) -> str:
    """Human-readable per-capita CO₂ (tonnes per person per year)."""
    if tonnes >= 10:
        return f"{tonnes:.2f} tonnes per person"
    if tonnes >= 1:
        return f"{tonnes:.2f} tonnes per person"
    if tonnes >= 0.01:
        return f"{tonnes:.3f} tonnes per person"
    return f"{tonnes:.4f} tonnes per person"


def emissions_hover_label(tonnes: float, *, estimated: bool) -> str:
    label = format_per_capita(tonnes)
    return f"{label} (est.)" if estimated else label


def build_co2_map(df: pd.DataFrame) -> go.Figure:
    """Choropleth with year slider (earliest→latest) and country hover."""
    vmax = float(df["emissions_per_capita"].quantile(0.98))
    years_sorted = sorted(df["year"].unique())

    df = df.copy()
    df["emissions_label"] = [
        emissions_hover_label(v, estimated=e)
        for v, e in zip(df["emissions_per_capita"], df["is_estimated"], strict=True)
    ]

    fig = px.choropleth(
        df,
        locations="iso_code",
        locationmode="ISO-3",
        color="emissions_per_capita",
        hover_name="country",
        custom_data=["emissions_label", "year"],
        animation_frame="year",
        category_orders={"year": years_sorted},
        range_color=(0, vmax),
        color_continuous_scale=OWID_COLOR_SCALE,
        labels={"emissions_per_capita": "CO₂ emissions per capita (tonnes)"},
        title="CO₂ emissions per capita",
    )

    fig.update_traces(
        hovertemplate=(
            "<b>%{hovertext}</b><br>"
            "Year: %{customdata[1]}<br>"
            "CO₂ per capita: %{customdata[0]}<extra></extra>"
        )
    )
    fig.update_geos(
        showframe=False,
        showcoastlines=True,
        coastlinecolor="#9ca3af",
        showland=True,
        landcolor="#f3f4f6",
        showocean=True,
        oceancolor="#ffffff",
        showcountries=True,
        countrycolor="#d1d5db",
        projection_type="natural earth",
    )
    fig.update_layout(
        font_family="system-ui, -apple-system, Segoe UI, Roboto, sans-serif",
        title_x=0.5,
        margin=dict(l=0, r=0, t=60, b=0),
        coloraxis_colorbar=dict(
            title="tonnes per person",
            tickformat=".2f",
        ),
        sliders=[dict(currentvalue=dict(prefix="Year: "))],
    )
    return fig


def write_map(output_path: Path, *, refresh_data: bool = False) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df = load_emissions(refresh=refresh_data)
    fig = build_co2_map(df)
    fig.write_html(
        output_path,
        include_plotlyjs="cdn",
        config={"displayModeBar": True, "scrollZoom": True},
    )
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build interactive OWID-style CO₂ map.")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Re-download emissions CSV from Our World in Data.",
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
    df = load_emissions(refresh=False)
    year_min, year_max = int(df["year"].min()), int(df["year"].max())
    print(f"Wrote {path}")
    print(f"Years {year_min}–{year_max} (slider runs earliest to latest).")
    print("Open in a browser to use the year slider and hover tooltips.")


if __name__ == "__main__":
    main()
