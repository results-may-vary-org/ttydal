"""Configuration manager for ttydal.

Manages application configuration stored in the platform config directory.
Run `ttydal --init-config` to create a config file from bundled defaults.
The app works without a config file (uses bundled defaults in-memory).
"""

import json
import shutil
from importlib import resources
from typing import Any

from ttydal.dirs import config_dir


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

        self.config_dir = config_dir()
        self.config_file = self.config_dir / "config.json"
        self._config: dict[str, Any] = {}
        self._debug_override: bool = False
        self._load_config()
        self._initialized = True

    @staticmethod
    def _get_default_config() -> dict[str, Any]:
        """Load the default configuration from the bundled default_config.json."""
        default_config_file = resources.files("ttydal").joinpath("default_config.json")
        return json.loads(default_config_file.read_text(encoding="utf-8"))

    def _get_default_keybindings(self) -> dict[str, dict[str, str]]:
        """Get default keybindings configuration."""
        return self._get_default_config().get("keybindings", {})

    def _load_config(self) -> None:
        """Load configuration from file, falling back to bundled defaults."""
        self.config_dir.mkdir(parents=True, exist_ok=True)

        if self.config_file.exists():
            with open(self.config_file, "r") as f:
                self._config = json.load(f)
        else:
            # No user config — use bundled defaults (don't write to disk)
            self._config = self._get_default_config()

    @staticmethod
    def init_config(force: bool = False) -> "Path":
        """Copy the bundled default config to the platform config directory.

        Args:
            force: Overwrite existing config if True.

        Returns:
            Path to the created config file.

        Raises:
            FileExistsError: If config already exists and force is False.
        """
        from pathlib import Path
        cfg_dir = config_dir()
        cfg_file = cfg_dir / "config.json"

        if cfg_file.exists() and not force:
            raise FileExistsError(
                f"Config already exists at {cfg_file}. Use --force to overwrite."
            )

        cfg_dir.mkdir(parents=True, exist_ok=True)
        default_config_file = resources.files("ttydal").joinpath("default_config.json")
        shutil.copy2(str(default_config_file), str(cfg_file))
        return cfg_file

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
        return self._debug_override or self.get("debug_logging_enabled", False)

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

    def get_keybinding(self, component: str, action: str) -> str:
        """Get a keybinding for a specific component and action.

        Args:
            component: Component name (e.g., "app", "player_page", "albums_list")
            action: Action name (e.g., "show_player", "toggle_play")

        Returns:
            Key binding string (e.g., "p", "space", "shift+left")
        """
        keybindings = self.get("keybindings", {})
        defaults = self._get_default_keybindings()

        # Get key from user config, fall back to default if not found
        user_key = keybindings.get(component, {}).get(action)
        if user_key is not None:
            return user_key

        # Fall back to default
        return defaults.get(component, {}).get(action, "")
