"""Entry point for MAP_NAME. Run from repo root: python maps/MAP_NAME/main.py"""

from pathlib import Path

# Optional: from lib.paths import map_dir  # map_dir("MAP_NAME")

MAP_DIR = Path(__file__).resolve().parent
DATA_DIR = MAP_DIR / "data"
OUTPUT_DIR = MAP_DIR / "output"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # TODO: load data from DATA_DIR, write figures to OUTPUT_DIR
    print(f"Map folder: {MAP_DIR}")
    print(f"Data: {DATA_DIR}")
    print(f"Output: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
