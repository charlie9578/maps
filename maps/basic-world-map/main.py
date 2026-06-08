"""Entry point for basic-world-map. Run from repo root: python maps/basic-world-map/main.py"""

from pathlib import Path

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt

MAP_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = MAP_DIR / "output"


def draw_world_map(output_path: Path) -> None:
    """Render a simple political world map and save to *output_path*."""
    fig = plt.figure(figsize=(12, 6))
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.Robinson())
    ax.set_global()

    ax.add_feature(cfeature.OCEAN, facecolor="#d4e6f1", zorder=0)
    ax.add_feature(cfeature.LAND, facecolor="#f5f5f0", zorder=1)
    ax.add_feature(cfeature.COASTLINE, linewidth=0.5, edgecolor="#555555", zorder=2)
    ax.add_feature(cfeature.BORDERS, linewidth=0.3, edgecolor="#888888", zorder=2)
    ax.gridlines(
        draw_labels=False,
        linewidth=0.3,
        color="#aaaaaa",
        alpha=0.5,
        linestyle="--",
    )

    fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Render a political world map PNG.")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=OUTPUT_DIR / "world_map.png",
        help="Output PNG path (default: output/world_map.png).",
    )
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    draw_world_map(args.output)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
