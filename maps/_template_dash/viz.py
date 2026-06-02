"""Plotly figures for MAP_NAME."""

from __future__ import annotations

import pandas as pd
import plotly.express as px

PLOTLY_TEMPLATE = "plotly_white"


def style_figure(fig):
    """Shared layout tweaks for dashboard charts."""
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        margin=dict(l=0, r=0, t=40, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def make_summary_bar(dff: pd.DataFrame):
    if "category" not in dff.columns or "value" not in dff.columns:
        return style_figure(px.bar(title="Add category/value columns"))
    agg = dff.groupby("category", dropna=False)["value"].sum().reset_index()
    fig = px.bar(agg, x="category", y="value", title="Total by category")
    fig.update_layout(xaxis_title=None)
    return style_figure(fig)


def make_detail_scatter(dff: pd.DataFrame):
    if "label" not in dff.columns or "value" not in dff.columns:
        return style_figure(px.scatter(title="Add label/value columns"))
    color = "category" if "category" in dff.columns else None
    fig = px.scatter(
        dff,
        x="label",
        y="value",
        color=color,
        title="Records (template)",
    )
    fig.update_layout(xaxis_title=None, showlegend=bool(color))
    return style_figure(fig)
