"""Configuration manager for ttydal.

Manages application configuration stored in ~/.ttydal/config.json
"""

import json
from pathlib import Path
from typing import Any


class ConfigManager:
    """Singleton configuration manager for ttydal."""

    _instance = None

    def __new__(cls):
        """Ensure only one instance exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the config manager."""
        if self._initialized:
            return

        self.config_dir = Path.home() / ".ttydal"
        self.config_file = self.config_dir / "config.json"
        self._config: dict[str, Any] = {}
        self._load_config()
        self._initialized = True

    def _load_config(self) -> None:
        """Load configuration from file or create default config."""
        self.config_dir.mkdir(parents=True, exist_ok=True)

        if self.config_file.exists():
            with open(self.config_file, "r") as f:
                self._config = json.load(f)
        else:
            # Default configuration
            self._config = {
                "theme": "rose-pine",
                "quality": "high",  # high or low
                "auto_play": True,  # auto-play next track when current finishes
                "debug_logging_enabled": False,  # enable debug logging to ~/.ttydal/debug.log
                "api_logging_enabled": False,  # enable API request/response logging to ~/.ttydal/debug-api.log
            }
            self._save_config()

    def _save_config(self) -> None:
        """Save configuration to file."""
        with open(self.config_file, "w") as f:
            json.dump(self._config, f, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value and save."""
        self._config[key] = value
        self._save_config()

    @property
    def theme(self) -> str:
        """Get the current theme."""
        return self.get("theme", "textual-dark")

    @theme.setter
    def theme(self, value: str) -> None:
        """Set the current theme."""
        self.set("theme", value)

    @property
    def quality(self) -> str:
        """Get the audio quality setting."""
        return self.get("quality", "high")

    @quality.setter
    def quality(self, value: str) -> None:
        """Set the audio quality setting."""
        if value not in ("max", "high", "low"):
            raise ValueError("Quality must be 'max', 'high', or 'low'")
        self.set("quality", value)

    @property
    def auto_play(self) -> bool:
        """Get the auto-play setting."""
        return self.get("auto_play", True)

    @auto_play.setter
    def auto_play(self, value: bool) -> None:
        """Set the auto-play setting."""
        self.set("auto_play", value)

    @property
    def debug_logging_enabled(self) -> bool:
        """Get the debug logging enabled setting."""
        return self.get("debug_logging_enabled", True)

    @debug_logging_enabled.setter
    def debug_logging_enabled(self, value: bool) -> None:
        """Set the debug logging enabled setting."""
        self.set("debug_logging_enabled", value)

    @property
    def api_logging_enabled(self) -> bool:
        """Get the API logging enabled setting."""
        return self.get("api_logging_enabled", True)

    @api_logging_enabled.setter
    def api_logging_enabled(self, value: bool) -> None:
        """Set the API logging enabled setting."""
        self.set("api_logging_enabled", value)

    @property
    def shuffle(self) -> bool:
        """Get the shuffle setting."""
        return self.get("shuffle", False)

    @shuffle.setter
    def shuffle(self, value: bool) -> None:
        """Set the shuffle setting."""
        self.set("shuffle", value)

    @property
    def vibrant_color(self) -> bool:
        """Get the vibrant color setting (colorize player bar with album's vibrant color)."""
        return self.get("vibrant_color", False)

    @vibrant_color.setter
    def vibrant_color(self, value: bool) -> None:
        """Set the vibrant color setting."""
        self.set("vibrant_color", value)
