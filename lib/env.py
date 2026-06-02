"""Load repo-root environment variables for maps that call external APIs."""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

from lib.paths import repo_root


@lru_cache(maxsize=1)
def load_repo_env() -> bool:
    """Load ``.env`` from the repository root if it exists. Idempotent."""
    env_path = repo_root() / ".env"
    if env_path.is_file():
        load_dotenv(env_path, override=False)
        return True
    return False


def env(name: str, *, default: str | None = None) -> str | None:
    """Read an environment variable after attempting to load repo ``.env``."""
    load_repo_env()
    return os.getenv(name, default)
