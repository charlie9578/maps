"""Load and filter data for MAP_NAME."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_data(data_path: Path) -> pd.DataFrame:
    """Load map data. Replace with your file format and cleaning logic."""
    if data_path.exists():
        if data_path.suffix.lower() in {".xlsx", ".xls"}:
            return pd.read_excel(data_path, sheet_name=0)
        return pd.read_csv(data_path)

    # Sample rows so the dashboard template runs before you add real data.
    return pd.DataFrame(
        {
            "category": ["A", "A", "B", "B", "C"],
            "value": [10.0, 20.0, 15.0, 25.0, 5.0],
            "label": ["alpha", "beta", "gamma", "delta", "epsilon"],
        }
    )


def normalize_category(raw: str, *, rules: dict[str, list[str]] | None = None) -> str:
    """Map raw labels to grouped categories (optional).

    Example rules: {"cancelled": ["shelved", "cancelled"], "retired": ["retired", "mothballed"]}
    """
    s = (raw or "").strip()
    if not s or not rules:
        return s
    lower = s.casefold()
    for grouped, keywords in rules.items():
        if any(kw in lower for kw in keywords):
            return grouped
    return s


def filter_df(
    df: pd.DataFrame,
    *,
    categories: list[str] | None,
    search_text: str | None,
) -> pd.DataFrame:
    """Apply sidebar filters. Extend with sliders, date ranges, etc."""
    dff = df
    if categories and "category" in dff.columns:
        dff = dff[dff["category"].isin(categories)]
    if search_text and search_text.strip() and "label" in dff.columns:
        q = search_text.strip().casefold()
        dff = dff[dff["label"].astype(str).str.casefold().str.contains(q, na=False)]
    return dff


def sorted_unique(df: pd.DataFrame, col: str) -> list[str]:
    vals = df[col].dropna().astype(str).str.strip()
    vals = vals[vals.ne("")].unique().tolist()
    return sorted(vals, key=lambda x: x.casefold())
