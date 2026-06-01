"""Path helpers for maps and notebooks (run from repository root)."""

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]


def repo_root() -> Path:
    """Absolute path to the repository root."""
    return _REPO_ROOT


def map_dir(name: str) -> Path:
    """Absolute path to maps/<name>/."""
    return _REPO_ROOT / "maps" / name
