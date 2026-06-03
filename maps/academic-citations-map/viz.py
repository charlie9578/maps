"""Plotly citation-network figure."""

from __future__ import annotations

import networkx as nx
import plotly.graph_objects as go

from data_processing import CitationNetwork, WorkSummary


def _truncate(text: str, max_len: int = 48) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def build_network_figure(network: CitationNetwork) -> go.Figure:
    """Interactive directed graph: arrow A → B means A cites B."""
    graph = nx.DiGraph()
    for node_id, work in network.nodes.items():
        graph.add_node(node_id, label=work.label(), year=work.publication_year)
    for source, target in network.edges:
        if source in network.nodes and target in network.nodes:
            graph.add_edge(source, target)

    if graph.number_of_nodes() == 0:
        return go.Figure().update_layout(title="No works in network")

    seed = network.seed_id
    n_nodes = graph.number_of_nodes()
    # circular_layout avoids scipy (spring/kamada_kawai require it in NetworkX 3.x).
    pos = nx.circular_layout(graph)

    edge_x: list[float | None] = []
    edge_y: list[float | None] = []
    for u, v in graph.edges():
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        line={"width": 0.8, "color": "#888"},
        hoverinfo="none",
        mode="lines",
        name="Cites",
    )

    node_ids = list(graph.nodes())
    node_x = [pos[n][0] for n in node_ids]
    node_y = [pos[n][1] for n in node_ids]
    works: list[WorkSummary] = [network.nodes[n] for n in node_ids]
    colors = ["#c0392b" if n == seed else "#2980b9" for n in node_ids]
    sizes = [22 if n == seed else 14 for n in node_ids]

    hover = [
        f"<b>{_truncate(w.display_name, 120)}</b><br>"
        f"{w.id}<br>"
        f"Year: {w.publication_year or '—'}<br>"
        f"Cited by: {w.cited_by_count}"
        for w in works
    ]

    show_labels = n_nodes <= 40
    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text" if show_labels else "markers",
        text=[_truncate(w.display_name, 36) for w in works] if show_labels else None,
        textposition="top center",
        textfont={"size": 9},
        hovertext=hover,
        hoverinfo="text",
        marker={"color": colors, "size": sizes, "line": {"width": 1, "color": "#fff"}},
        name="Works",
    )

    seed_work = network.nodes[seed]
    title = (
        f"Citation network: {_truncate(seed_work.display_name, 60)}<br>"
        f"<sup>{len(network.nodes)} works · {len(network.edges)} citation links · "
        f"red = seed · arrow = cites</sup>"
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        title=title,
        showlegend=False,
        hovermode="closest",
        margin={"l": 20, "r": 20, "t": 80, "b": 20},
        xaxis={"showgrid": False, "zeroline": False, "showticklabels": False},
        yaxis={"showgrid": False, "zeroline": False, "showticklabels": False},
        plot_bgcolor="#fafafa",
        annotations=[
            {
                "text": (
                    'Data: <a href="https://openalex.org/">OpenAlex</a> '
                    "(accessed 2026-06-03). Edge A→B: A cites B."
                ),
                "showarrow": False,
                "xref": "paper",
                "yref": "paper",
                "x": 0,
                "y": -0.08,
                "xanchor": "left",
                "font": {"size": 10, "color": "#555"},
            }
        ],
    )
    return fig
