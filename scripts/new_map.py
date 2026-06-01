#!/usr/bin/env python3
"""Scaffold a new self-contained map folder from maps/_template."""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = REPO_ROOT / "maps" / "_template"
MAPS_DIR = REPO_ROOT / "maps"

VALID_NAME = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a new map from the template.")
    parser.add_argument("name", help="Map folder name (e.g. uk-election-2024)")
    args = parser.parse_args()
    name = args.name.strip().lower()

    if not VALID_NAME.match(name):
        print(
            "Name must be lowercase letters, numbers, and hyphens; start with a letter.",
            file=sys.stderr,
        )
        return 1
    if name.startswith("_"):
        print("Names cannot start with underscore.", file=sys.stderr)
        return 1

    dest = MAPS_DIR / name
    if dest.exists():
        print(f"Already exists: {dest}", file=sys.stderr)
        return 1
    if not TEMPLATE.is_dir():
        print(f"Template missing: {TEMPLATE}", file=sys.stderr)
        return 1

    shutil.copytree(TEMPLATE, dest)
    for path in dest.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix in {".py", ".md", ".ipynb", ".txt"}:
            path.write_text(
                path.read_text(encoding="utf-8").replace("MAP_NAME", name),
                encoding="utf-8",
            )
    print(f"Created {dest.relative_to(REPO_ROOT)}")
    print("Next: edit README.md, main.py or notebook.ipynb, add data under data/")
    req = dest / "requirements.txt"
    if req.read_text(encoding="utf-8").strip():
        print(f"Install map deps: uv pip install -r maps/{name}/requirements.txt")
    print("Notebooks: use Jupyter kernel Maps (.venv) (see root README).")
    print("Downloaded CSVs in data/ are gitignored — document URLs in the map README.")
    print(f"Add a row for this map in MAPS.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
