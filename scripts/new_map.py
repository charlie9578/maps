#!/usr/bin/env python3
"""Scaffold a new self-contained map folder from maps/_template or maps/_template_dash."""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DEFAULT = REPO_ROOT / "maps" / "_template"
TEMPLATE_DASH = REPO_ROOT / "maps" / "_template_dash"
MAPS_DIR = REPO_ROOT / "maps"

VALID_NAME = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a new map from a template.")
    parser.add_argument("name", help="Map folder name (e.g. uk-election-2024)")
    parser.add_argument(
        "--type",
        choices=("default", "dash"),
        default="default",
        help="default: script/notebook map; dash: interactive Dash dashboard",
    )
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

    template = TEMPLATE_DASH if args.type == "dash" else TEMPLATE_DEFAULT
    if not template.is_dir():
        print(f"Template missing: {template}", file=sys.stderr)
        return 1

    shutil.copytree(template, dest)
    for path in dest.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix in {".py", ".md", ".ipynb", ".txt", ".css"}:
            path.write_text(
                path.read_text(encoding="utf-8").replace("MAP_NAME", name),
                encoding="utf-8",
            )

    rel = dest.relative_to(REPO_ROOT)
    print(f"Created {rel} (type={args.type})")
    print("Next: edit README.md, data under data/, and Python modules.")
    req = dest / "requirements.txt"
    if req.read_text(encoding="utf-8").strip():
        print(f"Install map deps: uv pip install -r maps/{name}/requirements.txt")

    if args.type == "dash":
        print("Run dashboard: python maps/{name}/main.py  (Ctrl+C to stop)".format(name=name))
        print("Split large logic across data_processing.py, viz.py, main.py (~500 lines each).")
    else:
        print("Run: python maps/{name}/main.py".format(name=name))
        print("Notebooks: kernel Maps (.venv) (see root README).")

    print("Downloaded CSVs in data/ are gitignored — document URLs in the map README.")
    print("Add a row for this map in MAPS.md.")
    print("External API? Add keys to repo-root .env (see .env.example).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
