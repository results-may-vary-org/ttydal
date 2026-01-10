"""Config page for application settings."""

from textual.app import ComposeResult
from textual.containers import Container, Vertical, VerticalScroll
from textual.widgets import Label, Button, Select
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
        theme_value = self.config.theme if self.config.theme in valid_theme_ids else "textual-dark"

        # Valid quality options
        valid_qualities = ["max", "high", "low"]
        quality_value = self.config.quality if self.config.quality in valid_qualities else "high"

        # Auto-play setting
        auto_play_value = "on" if self.config.auto_play else "off"

        with VerticalScroll():
            with Vertical():
                yield Label("[b]Settings[/b]", markup=True)

                yield Label("Theme:")
                yield Select(
                    options=self.AVAILABLE_THEMES,
                    value=theme_value,
                    id="theme-select"
                )

                yield Label("Audio Quality:")
                yield Select(
                    options=[
                        ("Max (Hi-Res Lossless - up to 24bit/192kHz)", "max"),
                        ("High (Lossless - 16bit/44.1kHz)", "high"),
                        ("Low (320kbps AAC)", "low")
                    ],
                    value=quality_value,
                    id="quality-select"
                )

                yield Label("Auto-Play Next Track:")
                yield Select(
                    options=[
                        ("On", "on"),
                        ("Off", "off")
                    ],
                    value=auto_play_value,
                    id="auto-play-select"
                )

                # Tidal Account section
                yield Label("")
                yield Label("[b]Tidal Account[/b]", markup=True)
                yield Button("Login to Tidal", variant="success", id="login-btn")

                # Debug section
                yield Label("")
                yield Label("[b]Debug[/b]", markup=True)
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

        # Auto-play: save immediately
        elif event.select.id == "auto-play-select" and event.value:
            auto_play = str(event.value) == "on"
            self.config.auto_play = auto_play

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events.

        Args:
            event: Button press event
        """
        if event.button.id == "login-btn":
            self.post_message(self.LoginRequested())
        elif event.button.id == "clear-logs-btn":
            self.post_message(self.ClearLogsRequested())
