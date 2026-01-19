"""Config page for application settings."""

from textual.app import ComposeResult
from textual.containers import Container, Vertical, VerticalScroll, Horizontal
from textual.widgets import Label, Button, Select, Switch
from textual.message import Message

from ttydal.config import ConfigManager


class ConfigPage(Container):
    """Configuration page for ttydal settings."""

    # Available Textual built-in themes
    AVAILABLE_THEMES = [
        ("Textual Dark", "textual-dark"),
        ("Textual Light", "textual-light"),
        ("Textual Ansi", "textual-ansi"),
        ("Dracula", "dracula"),
        ("Gruvbox", "gruvbox"),
        ("Catppuccin Mocha", "catppuccin-mocha"),
        ("Catppuccin Latte", "catppuccin-latte"),
        ("Monokai", "monokai"),
        ("Flexoki", "flexoki"),
        ("Nord", "nord"),
        ("Tokyo Night", "tokyo-night"),
        ("Solarized Light", "solarized-light"),
        ("Solarized Dark", "solarized-dark"),
        ("Rose Pine", "rose-pine"),
        ("Rose Pine Moon", "rose-pine-moon"),
        ("Rose Pine Dawn", "rose-pine-dawn"),
        ("Atom One Dark", "atom-one-dark"),
        ("Atom One Light", "atom-one-light"),
    ]

    DEFAULT_CSS = """
    ConfigPage {
        width: 1fr;
        height: 1fr;
        align: center middle;
    }

    ConfigPage VerticalScroll {
        width: 60;
        height: 1fr;
        max-height: 100%;
        background: $panel;
        border: solid $primary;
    }

    ConfigPage Vertical {
        width: 1fr;
        height: auto;
        padding: 2;
    }

    ConfigPage Label {
        width: 1fr;
        margin-bottom: 1;
    }

    ConfigPage Select {
        width: 1fr;
        margin-bottom: 2;
    }

    ConfigPage Button {
        width: 1fr;
        margin-bottom: 1;
    }

    ConfigPage Horizontal {
        width: 1fr;
        height: auto;
        margin-bottom: 2;
        align: left middle;
    }

    ConfigPage Horizontal Label {
        width: auto;
        margin-right: 2;
        margin-bottom: 0;
    }

    ConfigPage Horizontal Switch {
        width: auto;
    }

    ConfigPage .warning-label {
        color: $warning;
        text-style: italic;
        margin-top: 0;
        margin-bottom: 1;
    }
    """

    class QualityChanged(Message):
        """Message sent when quality setting changes."""

        def __init__(self, quality: str) -> None:
            """Initialize quality changed message.

            Args:
                quality: New quality setting
            """
            super().__init__()
            self.quality = quality

    class ThemeChanged(Message):
        """Message sent when theme setting changes."""

        def __init__(self, theme: str) -> None:
            """Initialize theme changed message.

            Args:
                theme: New theme name
            """
            super().__init__()
            self.theme = theme

    class LoginRequested(Message):
        """Message sent when user requests to login to Tidal."""

        pass

    class ClearLogsRequested(Message):
        """Message sent when user requests to clear debug logs."""

        pass

    def __init__(self):
        """Initialize the config page."""
        super().__init__()
        self.config = ConfigManager()

    def compose(self) -> ComposeResult:
        """Compose the config page UI."""
        # Valid theme options - extract just the theme IDs
        valid_theme_ids = [theme_id for _, theme_id in self.AVAILABLE_THEMES]
        theme_value = (
            self.config.theme
            if self.config.theme in valid_theme_ids
            else "rose-pine"
        )

        # Valid quality options
        valid_qualities = ["max", "high", "low"]
        quality_value = (
            self.config.quality
            if self.config.quality in valid_qualities
            else "high"
        )

        with VerticalScroll():
            with Vertical():
                yield Label("[b]Settings[/b]", markup=True)

                yield Label("Theme:")
                yield Select(
                    options=self.AVAILABLE_THEMES, value=theme_value, id="theme-select"
                )

                yield Label("Audio Quality:")
                yield Select(
                    options=[
                        ("Max (Hi-Res Lossless - up to 24bit/192kHz)", "max"),
                        ("High (Lossless - 16bit/44.1kHz)", "high"),
                        ("Low (320kbps AAC)", "low"),
                    ],
                    value=quality_value,
                    id="quality-select",
                )

                with Horizontal():
                    yield Label("Auto-Play Next Track:")
                    yield Switch(value=self.config.auto_play, id="auto-play-switch")

                # Tidal Account section
                yield Label("")
                yield Label("[b]Tidal Account[/b]", markup=True)
                yield Button("Login to Tidal", variant="success", id="login-btn")

                # Debug section
                yield Label("")
                yield Label("[b]Debug[/b]", markup=True)

                with Horizontal():
                    yield Label("Debug Logging:")
                    yield Switch(
                        value=self.config.debug_logging_enabled,
                        id="debug-logging-switch",
                    )
                yield Label(
                    "[i]⚠ Warning: Debug logs can grow large over time. Disable when not needed.[/i]",
                    markup=True,
                    classes="warning-label",
                )

                with Horizontal():
                    yield Label("API Request Logging:")
                    yield Switch(
                        value=self.config.api_logging_enabled, id="api-logging-switch"
                    )
                yield Label(
                    "[i]⚠ Warning: API logs capture full requests/responses and can consume significant disk space.[/i]",
                    markup=True,
                    classes="warning-label",
                )

                yield Button("Clear Debug Logs", variant="warning", id="clear-logs-btn")

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle select value changes - auto-save all settings.

        Args:
            event: Select changed event
        """
        # Theme: preview and save immediately
        if event.select.id == "theme-select" and event.value:
            theme = str(event.value)
            # Apply theme immediately for preview
            self.app.theme = theme
            # Save to config
            self.config.theme = theme
            self.post_message(self.ThemeChanged(theme))

        # Quality: save immediately
        elif event.select.id == "quality-select" and event.value:
            quality = str(event.value)
            self.config.quality = quality
            self.post_message(self.QualityChanged(quality))

    def on_switch_changed(self, event: Switch.Changed) -> None:
        """Handle switch value changes - auto-save all settings.

        Args:
            event: Switch changed event
        """
        # Auto-play: save immediately
        if event.switch.id == "auto-play-switch":
            self.config.auto_play = event.value

        # Debug logging: save immediately
        elif event.switch.id == "debug-logging-switch":
            self.config.debug_logging_enabled = event.value

        # API logging: save immediately
        elif event.switch.id == "api-logging-switch":
            self.config.api_logging_enabled = event.value

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events.

        Args:
            event: Button press event
        """
        if event.button.id == "login-btn":
            self.post_message(self.LoginRequested())
        elif event.button.id == "clear-logs-btn":
            self.post_message(self.ClearLogsRequested())
