#!/usr/bin/env python3
"""Install all maps/*/requirements.txt into the active (root) virtualenv."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MAPS_DIR = REPO_ROOT / "maps"


def find_requirements() -> list[Path]:
    files = sorted(MAPS_DIR.glob("*/requirements.txt"))
    return [f for f in files if f.parent.name != "_template"]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Install every map's requirements.txt into the current environment.",
    )
    parser.add_argument(
        "--map",
        metavar="NAME",
        help="Install only maps/<NAME>/requirements.txt",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands without running them",
    )
    args = parser.parse_args()

    if args.map:
        path = MAPS_DIR / args.map / "requirements.txt"
        if not path.is_file():
            print(f"Not found: {path}", file=sys.stderr)
            return 1
        files = [path]
    else:
        files = find_requirements()

    if not files:
        print("No map requirements.txt files found.")
        return 0

    installer = "uv" if _has_uv() else sys.executable
    for req in files:
        map_name = req.parent.name
        cmd = (
            ["uv", "pip", "install", "-r", str(req)]
            if installer == "uv"
            else [sys.executable, "-m", "pip", "install", "-r", str(req)]
        )
        print(f"{' '.join(cmd)}  # {map_name}")
        if args.dry_run:
            continue
        result = subprocess.run(cmd, cwd=REPO_ROOT)
        if result.returncode != 0:
            return result.returncode

    return 0


def _has_uv() -> bool:
    from shutil import which

    return which("uv") is not None


if __name__ == "__main__":
    raise SystemExit(main())
