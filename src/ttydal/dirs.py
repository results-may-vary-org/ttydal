"""Platform-aware directory paths for ttydal.

Provides conventional directory locations per platform:
- Linux: ~/.config/ttydal, ~/.cache/ttydal
- macOS: ~/Library/Application Support/ttydal, ~/Library/Caches/ttydal
- Windows: %APPDATA%/ttydal, %LOCALAPPDATA%/ttydal
"""

import os
import platform
from pathlib import Path

_APP_NAME = "ttydal"


def _system() -> str:
    return platform.system()


def config_dir() -> Path:
    """Return the platform-conventional config directory."""
    system = _system()
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / _APP_NAME
    if system == "Windows":
        return (
            Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
            / _APP_NAME
        )
    return Path.home() / ".config" / _APP_NAME


def cache_dir() -> Path:
    """Return the platform-conventional cache directory."""
    system = _system()
    if system == "Darwin":
        return Path.home() / "Library" / "Caches" / _APP_NAME
    if system == "Windows":
        return (
            Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
            / _APP_NAME
        )
    return Path.home() / ".cache" / _APP_NAME


def log_dir() -> Path:
    """Return the directory for log files (same as config dir)."""
    return config_dir()


def image_cache_dir() -> Path:
    """Return the directory for cached cover art images."""
    return cache_dir() / "images"
