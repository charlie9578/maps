#!/usr/bin/env python3
"""Build the GitHub Pages ``site/`` directory from published maps."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from html import escape
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = REPO_ROOT / "site"
MAP_DIR = REPO_ROOT / "maps" / "world-cup-teams-map"
WORLD_CUP_SLUG = "world-cup-2026"


@dataclass(frozen=True)
class PublishedMap:
    slug: str
    title: str
    summary: str
    tags: tuple[str, ...]


PUBLISHED_MAPS: tuple[PublishedMap, ...] = (
    PublishedMap(
        slug=WORLD_CUP_SLUG,
        title="2026 FIFA World Cup squads",
        summary=(
            "Interactive squad dashboard for 48 nations — stats, records, age profiles, "
            "captains, and capital-to-club flight paths."
        ),
        tags=("Plotly", "Football", "2026"),
    ),
)


def build_world_cup(staging: Path, pages_url: str) -> None:
    staging.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            sys.executable,
            str(MAP_DIR / "dashboard.py"),
            "--output-dir",
            str(staging),
            "--pages-url",
            pages_url,
        ],
        check=True,
        cwd=REPO_ROOT,
    )


def publish_world_cup(site_dir: Path, site_url: str) -> None:
    pages_url = f"{site_url.rstrip('/')}/{WORLD_CUP_SLUG}"
    staging = MAP_DIR / "output" / "_pages_staging"
    if staging.exists():
        shutil.rmtree(staging)
    build_world_cup(staging, pages_url)

    dest = site_dir / WORLD_CUP_SLUG
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(staging / "world_cup_dashboard_all.html", dest / "index.html")
    share_src = staging / "share-map.png"
    if share_src.is_file():
        shutil.copy2(share_src, dest / "share-map.png")

    shutil.rmtree(staging)


def write_landing_page(site_dir: Path, site_url: str) -> None:
    cards = []
    for published in PUBLISHED_MAPS:
        tags = "".join(f'<span class="tag">{escape(tag)}</span>' for tag in published.tags)
        cards.append(
            f"""    <article class="map-card">
      <h2><a href="{escape(published.slug)}/">{escape(published.title)}</a></h2>
      <p>{escape(published.summary)}</p>
      <div class="tags">{tags}</div>
      <a class="map-link" href="{escape(published.slug)}/">Open map →</a>
    </article>"""
        )
    site_url_esc = escape(site_url)
    repo = os.environ.get("GITHUB_REPOSITORY", "charlie9578/maps")
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Maps — interactive visualizations</title>
  <meta name="description" content="Interactive geographic and data visualizations from the maps repository."/>
  <meta property="og:type" content="website"/>
  <meta property="og:title" content="Maps — interactive visualizations"/>
  <meta property="og:description" content="Interactive geographic and data visualizations from the maps repository."/>
  <meta property="og:url" content="{site_url_esc}"/>
  <meta name="twitter:card" content="summary"/>
  <style>
    :root {{ font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }}
    body {{
      margin: 0;
      background: #0f172a;
      color: #e2e8f0;
      line-height: 1.5;
    }}
    .site-width {{
      max-width: 920px;
      margin: 0 auto;
      padding: 32px 16px 48px;
      box-sizing: border-box;
    }}
    header {{ margin-bottom: 28px; }}
    h1 {{
      margin: 0 0 8px;
      font-size: clamp(1.8rem, 4vw, 2.4rem);
      color: #f8fafc;
    }}
    .lead {{ margin: 0; color: #94a3b8; font-size: 1.05rem; }}
    .map-grid {{ display: grid; gap: 16px; }}
    .map-card {{
      background: linear-gradient(180deg, rgba(30, 41, 59, 0.95), rgba(15, 23, 42, 0.88));
      border: 1px solid #334155;
      border-radius: 12px;
      padding: 20px 22px;
      box-shadow: 0 14px 36px rgba(2, 6, 23, 0.22);
    }}
    .map-card h2 {{ margin: 0 0 8px; font-size: 1.25rem; }}
    .map-card h2 a {{ color: #f8fafc; text-decoration: none; }}
    .map-card h2 a:hover {{ color: #93c5fd; }}
    .map-card p {{ margin: 0 0 12px; color: #94a3b8; }}
    .tags {{ display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }}
    .tag {{
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: #38bdf8;
      background: rgba(56, 189, 248, 0.12);
      border-radius: 999px;
      padding: 4px 10px;
    }}
    .map-link {{ color: #93c5fd; font-weight: 600; text-decoration: none; }}
    .map-link:hover {{ text-decoration: underline; }}
    footer {{
      margin-top: 36px;
      padding-top: 16px;
      border-top: 1px solid #334155;
      color: #64748b;
      font-size: 14px;
    }}
    footer a {{ color: #93c5fd; }}
  </style>
</head>
<body>
  <div class="site-width">
    <header>
      <h1>Maps</h1>
      <p class="lead">Interactive geographic and data visualizations.</p>
    </header>
    <main class="map-grid">
{chr(10).join(cards)}
    </main>
    <footer>
      Source: <a href="https://github.com/{escape(repo)}">github.com/{escape(repo)}</a>
    </footer>
  </div>
</body>
</html>
"""
    (site_dir / "index.html").write_text(html, encoding="utf-8")


def build_site(output_dir: Path, site_url: str) -> None:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    publish_world_cup(output_dir, site_url)
    write_landing_page(output_dir, site_url)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the GitHub Pages site/ directory.")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=SITE_DIR,
        help=f"Site output directory (default: {SITE_DIR.relative_to(REPO_ROOT)}).",
    )
    parser.add_argument(
        "--site-url",
        required=True,
        metavar="URL",
        help="Public site base URL, e.g. https://charlie9578.github.io/maps",
    )
    args = parser.parse_args()
    site_url = args.site_url.rstrip("/")
    build_site(args.output, site_url)
    print(f"Wrote GitHub Pages site to {args.output}")
    print(f"  Landing: {site_url}/")
    for published in PUBLISHED_MAPS:
        print(f"  {published.title}: {site_url}/{published.slug}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
