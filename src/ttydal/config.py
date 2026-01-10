"""Configuration manager for ttydal.

Manages application configuration stored in ~/.ttydal/config.json
"""

import json
from pathlib import Path
from typing import Any
from ttydal.logger import log


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

        log("ConfigManager.__init__() called")
        self.config_dir = Path.home() / ".ttydal"
        self.config_file = self.config_dir / "config.json"
        log(f"  - Config file path: {self.config_file}")
        self._config: dict[str, Any] = {}
        self._load_config()
        self._initialized = True
        log("ConfigManager.__init__() completed")

    def _load_config(self) -> None:
        """Load configuration from file or create default config."""
        log("  - ConfigManager._load_config() called")
        self.config_dir.mkdir(parents=True, exist_ok=True)

        if self.config_file.exists():
            log(f"  - Loading existing config from {self.config_file}")
            with open(self.config_file, "r") as f:
                self._config = json.load(f)
            log(f"  - Config loaded: {self._config}")
        else:
            log("  - No config file found, creating default config")
            # Default configuration
            self._config = {
                "theme": "textual-dark",
                "quality": "high",  # high or low
                "auto_play": True  # auto-play next track when current finishes
            }
            self._save_config()
            log(f"  - Default config created: {self._config}")

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
        if value not in ("high", "low"):
            raise ValueError("Quality must be 'high' or 'low'")
        self.set("quality", value)

    @property
    def auto_play(self) -> bool:
        """Get the auto-play setting."""
        return self.get("auto_play", True)

    @auto_play.setter
    def auto_play(self, value: bool) -> None:
        """Set the auto-play setting."""
        self.set("auto_play", value)
