"""Bokeh chart builders and aggregation helpers for GEM wind data."""

from __future__ import annotations

import re
from typing import Any

import pandas as pd
from bokeh.models import (
    CategoricalColorMapper,
    ColumnDataSource,
    FactorRange,
    HoverTool,
    LinearColorMapper,
    NumeralTickFormatter,
    TapTool,
    Title,
)
from bokeh.plotting import figure
from bokeh.transform import factor_cmap

from wind_data import COL

# --- Shared visual theme -----------------------------------------------------

TEXT_COLOR = "#e2e8f0"
MUTED_COLOR = "#94a3b8"
GRID_COLOR = "#1e293b"
BG_COLOR = "rgba(0, 0, 0, 0)"
PLOT_HEIGHT = 360
MAP_WIDTH = 900
MAP_HEIGHT = 480
CHART_COL_WIDTH = 520
TOP_BAR_RANK = 15
CAPACITY_TIP_FMT = "{0,0}"
INTEGER_TICK_FORMATTER = NumeralTickFormatter(format="0,0")

COLORWAY = [
    "#22d3ee",
    "#34d399",
    "#818cf8",
    "#f472b6",
    "#fbbf24",
    "#a78bfa",
    "#2dd4bf",
    "#fb7185",
    "#60a5fa",
    "#facc15",
]

STATUS_COLORS = {
    "operating": "#34d399",
    "construction": "#22d3ee",
    "pre-construction": "#818cf8",
    "announced": "#a78bfa",
    "shelved": "#fbbf24",
    "cancelled": "#f87171",
    "mothballed": "#fb923c",
    "retired": "#94a3b8",
}

STATUS_PALETTE = list(STATUS_COLORS.values())
STATUS_FACTORS = list(STATUS_COLORS.keys())

CAPACITY_SCALE_STOPS: tuple[tuple[float, str], ...] = (
    (0.0, "#0e7490"),
    (0.5, "#22d3ee"),
    (1.0, "#34d399"),
)

OWNER_COL = "Owner"

_OWNER_PCT_RE = re.compile(r"^(?P<name>.*?)(?:\s*\[(?P<pct>\d+(?:\.\d+)?)%\]\s*)?$")


def _tip(field: str, fmt: str = "") -> str:
    """Bokeh tooltip field ref; brace-wrap names that contain spaces or punctuation."""
    return "@{" + field + "}" + fmt


def _apply_capacity_ticks(p: figure, *, axis: str) -> None:
    """Format capacity axis ticks as integers (no scientific notation)."""
    if axis == "x":
        p.xaxis.formatter = INTEGER_TICK_FORMATTER
    else:
        p.yaxis.formatter = INTEGER_TICK_FORMATTER


def _apply_chart_theme(p: figure, *, title: str) -> figure:
    p.background_fill_color = BG_COLOR
    p.border_fill_color = BG_COLOR
    p.outline_line_color = None
    p.title = Title(text=title, text_color=TEXT_COLOR, text_font_size="15px", align="left")
    p.xaxis.axis_line_color = GRID_COLOR
    p.yaxis.axis_line_color = GRID_COLOR
    p.xaxis.major_tick_line_color = GRID_COLOR
    p.yaxis.major_tick_line_color = GRID_COLOR
    p.xaxis.minor_tick_line_color = None
    p.yaxis.minor_tick_line_color = None
    p.xaxis.major_label_text_color = MUTED_COLOR
    p.yaxis.major_label_text_color = MUTED_COLOR
    p.xaxis.axis_label_text_color = MUTED_COLOR
    p.yaxis.axis_label_text_color = MUTED_COLOR
    p.xgrid.grid_line_color = GRID_COLOR
    p.ygrid.grid_line_color = GRID_COLOR
    p.xgrid.grid_line_alpha = 0.35
    p.ygrid.grid_line_alpha = 0.35
    return p


def global_capacity_mapper(capacity_hi: float) -> LinearColorMapper:
    """Fixed-range mapper so bar colours stay stable when filters change."""
    palette = [stop[1] for stop in CAPACITY_SCALE_STOPS]
    hi = capacity_hi if capacity_hi > 0 else 1.0
    return LinearColorMapper(palette=palette, low=0.0, high=hi)


def _capacity_groupby(dff: pd.DataFrame, by: str | list[str]) -> pd.DataFrame:
    """Sum capacity by one or more group columns (pandas groupby)."""
    return (
        dff.groupby(by, dropna=False)[[COL.capacity_mw]]
        .sum()
        .sort_values(COL.capacity_mw, ascending=False)
    )


def _cds_from_groupby(grouped: pd.DataFrame | pd.Series) -> ColumnDataSource:
    """Wrap a pandas groupby result as a Bokeh ColumnDataSource (idiomatic Bokeh + pandas)."""
    if isinstance(grouped, pd.Series):
        grouped = grouped.reset_index()
    return ColumnDataSource(grouped)


def _country_groupby(dff: pd.DataFrame, n: int = 15) -> pd.DataFrame:
    """Groupby country with top-N + Other bucket."""
    tops = top_country_names(dff, n)
    dfc = dff.copy()
    dfc[COL.country] = dfc[COL.country].where(dfc[COL.country].isin(tops), "Other")
    return _capacity_groupby(dfc, COL.country)


def _split_owners(owner: object) -> list[str]:
    if owner is None:
        return []
    s = str(owner).strip()
    if not s or s == "<NA>" or s.casefold() == "nan":
        return []
    parts = re.split(r"\s*;\s*|\s*,\s*", s)
    return [p.strip() for p in parts if p and p.strip()]


def _parse_owner_shares(owner: object) -> list[tuple[str, float]]:
    parts = _split_owners(owner)
    if not parts:
        return []

    parsed: list[tuple[str, float | None]] = []
    for p in parts:
        m = _OWNER_PCT_RE.match(p)
        if not m:
            parsed.append((p.strip(), None))
            continue
        name = (m.group("name") or "").strip()
        if not name:
            continue
        pct_raw = m.group("pct")
        pct = float(pct_raw) if pct_raw is not None else None
        parsed.append((name, pct))

    if not parsed:
        return []

    with_pct = [(n, p) for n, p in parsed if p is not None]
    without_pct = [n for n, p in parsed if p is None]

    if not with_pct:
        per = 100.0 / len(parsed)
        return [(n, per) for n, _ in parsed]

    used = float(sum(p for _, p in with_pct))
    if without_pct:
        remaining = max(0.0, 100.0 - used)
        per = remaining / len(without_pct) if without_pct else 0.0
        out = [(n, float(p)) for n, p in with_pct] + [(n, per) for n in without_pct]
    else:
        out = [(n, float(p)) for n, p in with_pct]

    total = sum(p for _, p in out)
    if total <= 0:
        return []
    if abs(total - 100.0) > 1e-6:
        out = [(n, p * (100.0 / total)) for n, p in out]
    return out


def breakdown_capacity_by_owner(dff: pd.DataFrame, n: int = TOP_BAR_RANK) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    if len(dff) == 0:
        return pd.DataFrame({OWNER_COL: [], COL.capacity_mw: []})

    for _, r in dff[[COL.capacity_mw, COL.owner]].iterrows():
        cap = float(r[COL.capacity_mw]) if pd.notna(r[COL.capacity_mw]) else 0.0
        if cap <= 0:
            continue
        owners = _parse_owner_shares(r[COL.owner])
        if not owners:
            continue
        for name, pct in owners:
            name_cf = name.casefold().strip()
            if not name_cf or name_cf in {"nan", "<na>", "none", "other"}:
                continue
            rows.append({OWNER_COL: name, COL.capacity_mw: cap * (pct / 100.0)})

    if not rows:
        return pd.DataFrame({OWNER_COL: [], COL.capacity_mw: []})

    return (
        pd.DataFrame(rows)
        .groupby(OWNER_COL, dropna=False)[COL.capacity_mw]
        .sum()
        .sort_values(ascending=False)
        .head(n)
    )


def assets_table_df(dff: pd.DataFrame) -> pd.DataFrame:
    cols = [
        COL.country,
        COL.project,
        COL.phase,
        COL.capacity_mw,
        COL.installation_type,
        COL.status,
        COL.start_year,
        COL.retired_year,
        COL.operator,
        COL.owner,
        COL.lat,
        COL.lon,
        COL.wiki,
    ]
    out = dff[cols].copy()
    out.rename(
        columns={
            COL.capacity_mw: "Capacity (MW)",
            COL.installation_type: "Installation Type",
            COL.start_year: "Start year",
            COL.retired_year: "Retired year",
            COL.operator: "Operator",
            COL.owner: "Owner",
            COL.lat: "Latitude",
            COL.lon: "Longitude",
            COL.wiki: "Wiki URL",
            COL.country: "Country/Area",
            COL.project: "Project Name",
            COL.phase: "Phase Name",
            COL.status: "Status",
        },
        inplace=True,
    )
    return out


def top_country_names(dff: pd.DataFrame, n: int = TOP_BAR_RANK) -> list[str]:
    grouped = _capacity_groupby(dff, COL.country)
    return [str(x) for x in grouped.index[:n]]


def make_installation_bar(dff: pd.DataFrame) -> tuple[figure, ColumnDataSource, Any, str]:
    grouped = _capacity_groupby(dff, COL.installation_type)
    source = _cds_from_groupby(grouped)
    factors = [str(x) for x in source.data[COL.installation_type]]
    palette = [COLORWAY[i % len(COLORWAY)] for i in range(len(factors))]

    p = figure(
        x_range=FactorRange(factors=factors),
        height=PLOT_HEIGHT,
        width=CHART_COL_WIDTH,
        tools="",
        toolbar_location=None,
    )
    _apply_chart_theme(p, title="Capacity by installation type")
    _apply_capacity_ticks(p, axis="y")
    p.xaxis.major_label_orientation = 0.8

    renderer = p.vbar(
        x=COL.installation_type,
        top=COL.capacity_mw,
        width=0.7,
        color=factor_cmap(COL.installation_type, palette=palette, factors=factors),
        line_color=None,
        source=source,
    )
    p.add_tools(
        HoverTool(
            renderers=[renderer],
            tooltips=[
                ("Type", _tip(COL.installation_type)),
                ("Capacity (MW)", _tip(COL.capacity_mw, CAPACITY_TIP_FMT)),
            ],
        ),
        TapTool(renderers=[renderer]),
    )
    return p, source, renderer, COL.installation_type


def make_status_bar(dff: pd.DataFrame) -> tuple[figure, ColumnDataSource, Any, str]:
    grouped = _capacity_groupby(dff, COL.status)
    source = _cds_from_groupby(grouped)
    factors = [str(x) for x in source.data[COL.status]]
    palette = [STATUS_COLORS.get(f, "#94a3b8") for f in factors]

    p = figure(
        x_range=FactorRange(factors=factors),
        height=PLOT_HEIGHT,
        width=CHART_COL_WIDTH,
        tools="",
        toolbar_location=None,
    )
    _apply_chart_theme(p, title="Capacity by status")
    _apply_capacity_ticks(p, axis="y")
    p.xaxis.major_label_orientation = 0.8

    renderer = p.vbar(
        x=COL.status,
        top=COL.capacity_mw,
        width=0.7,
        color=factor_cmap(COL.status, palette=palette, factors=factors),
        line_color=None,
        source=source,
    )
    p.add_tools(
        HoverTool(
            renderers=[renderer],
            tooltips=[
                ("Status", _tip(COL.status)),
                ("Capacity (MW)", _tip(COL.capacity_mw, CAPACITY_TIP_FMT)),
            ],
        ),
        TapTool(renderers=[renderer]),
    )
    return p, source, renderer, COL.status


def make_country_bar(
    dff: pd.DataFrame,
    cap_mapper: LinearColorMapper,
) -> tuple[figure, ColumnDataSource, Any, str]:
    grouped = _country_groupby(dff, n=TOP_BAR_RANK).sort_values(COL.capacity_mw, ascending=True).reset_index()
    source = ColumnDataSource(grouped)
    factors = [str(x) for x in source.data[COL.country]]
    height = max(PLOT_HEIGHT, 22 * len(factors) + 120)

    p = figure(
        y_range=FactorRange(factors=factors),
        height=height,
        width=CHART_COL_WIDTH,
        tools="",
        toolbar_location=None,
    )
    _apply_chart_theme(p, title=f"Capacity by country (top {TOP_BAR_RANK} + Other)")
    _apply_capacity_ticks(p, axis="x")

    renderer = p.hbar(
        y=COL.country,
        right=COL.capacity_mw,
        height=0.7,
        color={"field": COL.capacity_mw, "transform": cap_mapper},
        line_color=None,
        source=source,
    )
    p.add_tools(
        HoverTool(
            renderers=[renderer],
            tooltips=[
                ("Country", _tip(COL.country)),
                ("Capacity (MW)", _tip(COL.capacity_mw, CAPACITY_TIP_FMT)),
            ],
        ),
        TapTool(renderers=[renderer]),
    )
    return p, source, renderer, COL.country


def make_top_projects_bar(
    dff: pd.DataFrame,
    cap_mapper: LinearColorMapper,
) -> tuple[figure, ColumnDataSource, Any, str]:
    grouped = (
        dff.groupby([COL.country, COL.project], dropna=False)[[COL.capacity_mw]]
        .sum()
        .sort_values(COL.capacity_mw, ascending=False)
        .head(TOP_BAR_RANK)
        .reset_index()
        .sort_values(COL.capacity_mw, ascending=True)
    )
    source = ColumnDataSource(grouped)
    factors = [str(x) for x in source.data[COL.project]]

    height = max(PLOT_HEIGHT, 22 * len(factors) + 120)
    p = figure(
        y_range=FactorRange(factors=factors),
        height=height,
        width=CHART_COL_WIDTH,
        tools="",
        toolbar_location=None,
    )
    _apply_chart_theme(p, title=f"Largest wind farms (top {TOP_BAR_RANK} projects, summed across phases)")
    _apply_capacity_ticks(p, axis="x")

    renderer = p.hbar(
        y=COL.project,
        right=COL.capacity_mw,
        height=0.7,
        color={"field": COL.capacity_mw, "transform": cap_mapper},
        line_color=None,
        source=source,
    )
    p.add_tools(
        HoverTool(
            renderers=[renderer],
            tooltips=[
                ("Project", _tip(COL.project)),
                ("Country", _tip(COL.country)),
                ("Capacity (MW)", _tip(COL.capacity_mw, CAPACITY_TIP_FMT)),
            ],
        ),
        TapTool(renderers=[renderer]),
    )
    return p, source, renderer, COL.project


def make_owner_bar(
    dff: pd.DataFrame,
    cap_mapper: LinearColorMapper,
) -> tuple[figure, ColumnDataSource, Any, str]:
    grouped = breakdown_capacity_by_owner(dff, n=TOP_BAR_RANK).sort_values(ascending=True)
    source = _cds_from_groupby(grouped)
    factors = [str(x) for x in source.data[OWNER_COL]]
    height = max(PLOT_HEIGHT, 26 * len(factors) + 140) if factors else PLOT_HEIGHT

    p = figure(
        y_range=FactorRange(factors=factors),
        height=height,
        width=CHART_COL_WIDTH * 2 + 48,
        tools="",
        toolbar_location=None,
    )
    _apply_chart_theme(p, title=f"Capacity by owner (share-adjusted, top {TOP_BAR_RANK})")
    _apply_capacity_ticks(p, axis="x")

    renderer = p.hbar(
        y=OWNER_COL,
        right=COL.capacity_mw,
        height=0.7,
        color={"field": COL.capacity_mw, "transform": cap_mapper},
        line_color=None,
        source=source,
    )
    p.add_tools(
        HoverTool(
            renderers=[renderer],
            tooltips=[
                ("Owner", _tip(OWNER_COL)),
                ("Capacity (MW)", _tip(COL.capacity_mw, CAPACITY_TIP_FMT)),
            ],
        ),
        TapTool(renderers=[renderer]),
    )
    return p, source, renderer, OWNER_COL


def status_color_mapper() -> CategoricalColorMapper:
    return CategoricalColorMapper(factors=STATUS_FACTORS, palette=STATUS_PALETTE)
