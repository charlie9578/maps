"""Academic citation network from OpenAlex. Run from repo root:

    uv pip install -r maps/academic-citations-map/requirements.txt
    python maps/academic-citations-map/main.py --search "Penmanshiel wind farm data" --depth 1
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from data_processing import (
    SmartTrimConfig,
    expand_citation_network,
    normalize_openalex_id,
    pick_work,
    search_works,
)
from viz import build_network_figure

MAP_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = MAP_DIR / "output"
OUTPUT_HTML = OUTPUT_DIR / "citation_network.html"

DEFAULT_SEARCH = "Penmanshiel wind farm data"
DEFAULT_DEPTH = 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build an OpenAlex citation network around a seed paper.",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--search",
        metavar="QUERY",
        help="Search OpenAlex for a paper title (default test query if neither search nor work-id).",
    )
    group.add_argument(
        "--work-id",
        metavar="ID",
        help="Seed OpenAlex work id (e.g. W4393687471 or full URL).",
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=DEFAULT_DEPTH,
        help=f"Hops beyond direct neighbors (0=seed links only; default {DEFAULT_DEPTH}).",
    )
    parser.add_argument(
        "--pick",
        type=int,
        metavar="N",
        help="Index into search results (0-based). Default: highest cited_by_count.",
    )
    parser.add_argument(
        "--list-search",
        action="store_true",
        help="Print search hits and exit (use with --search).",
    )
    parser.add_argument(
        "--max-per-direction",
        type=int,
        default=30,
        metavar="N",
        help="Cap references or citers fetched per work per hop (default 30).",
    )
    parser.add_argument(
        "--no-trim",
        action="store_true",
        help="Keep all fetched papers (default: drop nodes with only one connection after each hop).",
    )
    parser.add_argument(
        "--trim-mode",
        choices=("connections", "smart", "simple"),
        default="connections",
        help="connections: keep seed + top papers by graph degree up to --max-works (default); "
        "smart/simple: per-hop rules then cap.",
    )
    parser.add_argument(
        "--max-works",
        type=int,
        default=100,
        metavar="N",
        help="Max papers in final graph; drop least-connected until at most N (default 100). "
        "Use 0 with --no-trim to disable.",
    )
    parser.add_argument(
        "--min-connections",
        type=int,
        default=2,
        metavar="N",
        help="Simple trim, or hop-1 floor in smart mode (default 2).",
    )
    parser.add_argument(
        "--min-cited-trim",
        type=int,
        default=5,
        metavar="N",
        help="Smart trim: drop hop 2+ degree-2 nodes below this cited_by_count unless high score.",
    )
    parser.add_argument(
        "--no-dedupe",
        action="store_true",
        help="Do not merge duplicate OpenAlex records (same DOI or title+year).",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=OUTPUT_HTML,
        help=f"Output HTML path (default: {OUTPUT_HTML.relative_to(MAP_DIR.parent.parent)}).",
    )
    return parser.parse_args()


def _resolve_seed(args: argparse.Namespace) -> str:
    if args.work_id:
        return normalize_openalex_id(args.work_id)

    query = args.search or DEFAULT_SEARCH
    results = search_works(query)
    if args.list_search:
        for i, work in enumerate(results):
            print(f"{i:2d}  {work.id}  {work.label()}")
        sys.exit(0)

    if len(results) > 1 and args.pick is None:
        print(f"Search '{query}' returned {len(results)} works; using best title match.")
        print("Use --pick N or --list-search to choose another. Top results:")
        for i, work in enumerate(results[:8]):
            print(f"  {i}  {work.id}  {work.label()}")

    work = pick_work(results, pick_index=args.pick, query=query)
    print(f"Seed: {work.id} — {work.display_name}")
    return work.id


def main() -> None:
    args = _parse_args()
    if args.depth < 0:
        print("depth must be >= 0", file=sys.stderr)
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    seed_id = _resolve_seed(args)

    trim = not args.no_trim
    max_works = None if not trim or args.max_works <= 0 else args.max_works
    trim_desc = (
        f", trim={args.trim_mode}, max_works={max_works}"
        if trim
        else ", no trim"
    )
    print(
        f"Expanding network (depth={args.depth}, max_per_direction={args.max_per_direction}"
        f"{trim_desc})…"
    )
    smart_trim = (
        SmartTrimConfig(min_cited_for_low_degree=args.min_cited_trim)
        if trim and args.trim_mode == "smart"
        else None
    )
    network = expand_citation_network(
        seed_id,
        depth=args.depth,
        max_per_direction=args.max_per_direction,
        trim_after_each_hop=trim,
        trim_mode=args.trim_mode,
        min_connections=args.min_connections,
        smart_trim=smart_trim,
        max_works=max_works,
        dedupe=not args.no_dedupe,
    )
    print(f"Nodes: {len(network.nodes)}, edges: {len(network.edges)}")
    for step in network.trim_report.steps:
        print(f"  trim: {step}")
    if network.dedupe_report.merge_count:
        print(f"Merged {network.dedupe_report.merge_count} duplicate OpenAlex record(s):")
        for canonical, aliases in network.dedupe_report.groups().items():
            alias_str = ", ".join(aliases)
            print(f"  {canonical} <- {alias_str}")

    fig = build_network_figure(network)
    out_path = args.output if args.output.is_absolute() else MAP_DIR / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(out_path, include_plotlyjs="cdn")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
