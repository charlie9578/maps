#!/usr/bin/env python3
"""Build the GitHub Pages ``site/`` directory from published maps."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from html import escape
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = REPO_ROOT / "site"
MAPS_DIR = REPO_ROOT / "maps"

# Installed in CI before building (see .github/workflows/deploy-pages.yml).
PAGES_REQUIREMENTS: tuple[str, ...] = (
    "maps/world-cup-teams-map/requirements.txt",
    "maps/interactive-owid-map/requirements.txt",
    "maps/osm-solar-map/requirements.txt",
    "maps/academic-citations-map/requirements.txt",
    "maps/basic-world-map/requirements.txt",
)


@dataclass(frozen=True)
class PublishedMap:
    slug: str
    title: str
    summary: str
    tags: tuple[str, ...]
    publish: Callable[[Path, str], None]


@dataclass(frozen=True)
class ScriptMapSpec:
    map_name: str
    script: str
    built_output: str
    script_args: tuple[str, ...] = ()
    dest_filename: str = "index.html"
    extra_outputs: tuple[str, ...] = ()
    png_wrapper: bool = False


def _staging_dir(map_name: str) -> Path:
    return MAPS_DIR / map_name / "output" / "_pages_staging"


def _run_script_map(spec: ScriptMapSpec) -> Path:
    map_dir = MAPS_DIR / spec.map_name
    staging = _staging_dir(spec.map_name)
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=True)

    output_path = staging / spec.built_output
    cmd = [
        sys.executable,
        str(map_dir / spec.script),
        "-o",
        str(output_path),
        *spec.script_args,
    ]
    subprocess.run(cmd, check=True, cwd=REPO_ROOT)
    if not output_path.is_file():
        msg = f"Expected output missing after build: {output_path}"
        raise FileNotFoundError(msg)
    return staging


def _copy_script_output(site_dir: Path, slug: str, staging: Path, spec: ScriptMapSpec) -> None:
    dest = site_dir / slug
    dest.mkdir(parents=True, exist_ok=True)
    built = staging / spec.built_output
    if spec.png_wrapper:
        png_name = spec.built_output
        shutil.copy2(built, dest / png_name)
        _write_png_viewer(dest / "index.html", title=slug, png_file=png_name)
    else:
        shutil.copy2(built, dest / spec.dest_filename)
    for name in spec.extra_outputs:
        extra = staging / name
        if extra.is_file():
            shutil.copy2(extra, dest / name)
    shutil.rmtree(staging)


def _write_png_viewer(path: Path, *, title: str, png_file: str) -> None:
    title_esc = escape(title)
    png_esc = escape(png_file)
    path.write_text(
        f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{title_esc}</title>
  <style>
    body {{
      margin: 0;
      background: #0f172a;
      display: flex;
      justify-content: center;
      padding: 16px;
      box-sizing: border-box;
    }}
    img {{
      max-width: min(1200px, 100%);
      height: auto;
      border-radius: 8px;
      box-shadow: 0 14px 36px rgba(2, 6, 23, 0.35);
    }}
  </style>
</head>
<body>
  <img src="{png_esc}" alt="{title_esc}"/>
</body>
</html>
""",
        encoding="utf-8",
    )


def publish_world_cup(site_dir: Path, site_url: str) -> None:
    slug = "world-cup-2026"
    map_dir = MAPS_DIR / "world-cup-teams-map"
    pages_url = f"{site_url.rstrip('/')}/{slug}"
    staging = _staging_dir("world-cup-teams-map")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            sys.executable,
            str(map_dir / "dashboard.py"),
            "--output-dir",
            str(staging),
            "--pages-url",
            pages_url,
        ],
        check=True,
        cwd=REPO_ROOT,
    )
    dest = site_dir / slug
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(staging / "world_cup_dashboard_all.html", dest / "index.html")
    share_src = staging / "share-map.png"
    if share_src.is_file():
        shutil.copy2(share_src, dest / "share-map.png")
    shutil.rmtree(staging)


def publish_co2(site_dir: Path, _site_url: str) -> None:
    spec = ScriptMapSpec(
        map_name="interactive-owid-map",
        script="main.py",
        built_output="co2_per_capita_map.html",
    )
    staging = _run_script_map(spec)
    _copy_script_output(site_dir, "co2-per-capita", staging, spec)


def publish_osm_solar(site_dir: Path, _site_url: str) -> None:
    spec = ScriptMapSpec(
        map_name="osm-solar-map",
        script="main.py",
        built_output="osm_solar_malta.html",
    )
    staging = _run_script_map(spec)
    _copy_script_output(site_dir, "osm-solar-malta", staging, spec)


def publish_citations(site_dir: Path, _site_url: str) -> None:
    spec = ScriptMapSpec(
        map_name="academic-citations-map",
        script="main.py",
        built_output="citation_network.html",
        script_args=(
            "--search",
            "Penmanshiel wind farm data",
            "--depth",
            "1",
        ),
    )
    staging = _run_script_map(spec)
    _copy_script_output(site_dir, "citation-network", staging, spec)


def publish_world_map(site_dir: Path, _site_url: str) -> None:
    spec = ScriptMapSpec(
        map_name="basic-world-map",
        script="main.py",
        built_output="world_map.png",
        png_wrapper=True,
    )
    staging = _run_script_map(spec)
    dest = site_dir / "world-map"
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(staging / spec.built_output, dest / spec.built_output)
    _write_png_viewer(
        dest / "index.html",
        title="Political world map",
        png_file=spec.built_output,
    )
    shutil.rmtree(staging)


PUBLISHED_MAPS: tuple[PublishedMap, ...] = (
    PublishedMap(
        slug="world-cup-2026",
        title="2026 FIFA World Cup squads",
        summary=(
            "Interactive squad dashboard for 48 nations — stats, records, age profiles, "
            "captains, and capital-to-club flight paths."
        ),
        tags=("Plotly", "Football", "2026"),
        publish=publish_world_cup,
    ),
    PublishedMap(
        slug="co2-per-capita",
        title="CO₂ emissions per capita",
        summary=(
            "Choropleth of territorial CO₂ per person by country, with a year slider — "
            "data from Our World in Data."
        ),
        tags=("Plotly", "Climate", "OWID"),
        publish=publish_co2,
    ),
    PublishedMap(
        slug="osm-solar-malta",
        title="Malta solar plants (OpenStreetMap)",
        summary=(
            "Clustered map of solar power plants in Malta and Gozo from OpenStreetMap "
            "(`plant:source=solar`)."
        ),
        tags=("Folium", "Solar", "OSM"),
        publish=publish_osm_solar,
    ),
    PublishedMap(
        slug="citation-network",
        title="Academic citation network",
        summary=(
            "Interactive citation graph around a seed paper (demo: Penmanshiel wind farm), "
            "built from OpenAlex metadata."
        ),
        tags=("Plotly", "OpenAlex", "Network"),
        publish=publish_citations,
    ),
    PublishedMap(
        slug="world-map",
        title="Political world map",
        summary=(
            "Simple land–ocean map with coastlines and borders — Natural Earth via Cartopy."
        ),
        tags=("Cartopy", "Static"),
        publish=publish_world_map,
    ),
)


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
      · Dash live dashboards (TfL, GEM wind) are not hosted here.
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
    for published in PUBLISHED_MAPS:
        print(f"Building {published.slug}…")
        published.publish(output_dir, site_url)
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
        label = published.title.replace("\u2082", "2")
        print(f"  {label}: {site_url}/{published.slug}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
