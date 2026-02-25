"""Keybinding helper utilities for configurable keybindings."""

from textual.binding import Binding
from ttydal.config import ConfigManager


def get_key(component: str, action: str) -> str:
    """Get a keybinding from config.

    Args:
        component: Component name (e.g., "app", "player_page")
        action: Action name (e.g., "show_player", "quit")

    Returns:
        Key binding string
    """
    config = ConfigManager()
    return config.get_keybinding(component, action)


def create_bindings(component: str, binding_specs: list[tuple[str, str, bool]]) -> list[Binding]:
    """Create Binding objects from config for a specific component.

    Args:
        component: Component name (e.g., "app", "player_page")
        binding_specs: List of (action, description, show) tuples

    Returns:
        List of Binding objects with keys from config
    """
    config = ConfigManager()
    bindings = []

    for action, description, show in binding_specs:
        key = config.get_keybinding(component, action)
        if key:
            bindings.append(Binding(key, action, description, show=show))

    return bindings
