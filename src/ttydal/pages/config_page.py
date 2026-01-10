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
        valid_qualities = ["high", "low"]
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
                        ("High (Lossless)", "high"),
                        ("Low (320k)", "low")
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

                yield Button("Save Settings", variant="primary", id="save-btn")
                yield Label("", id="status-message")

                # Tidal Account section
                yield Label("")
                yield Label("[b]Tidal Account[/b]", markup=True)
                yield Button("Login to Tidal", variant="success", id="login-btn")

                # Debug section
                yield Label("")
                yield Label("[b]Debug[/b]", markup=True)
                yield Button("Clear Debug Logs", variant="warning", id="clear-logs-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events.

        Args:
            event: Button press event
        """
        if event.button.id == "save-btn":
            self.save_settings()
        elif event.button.id == "login-btn":
            self.post_message(self.LoginRequested())
        elif event.button.id == "clear-logs-btn":
            self.post_message(self.ClearLogsRequested())
            # Show confirmation message
            status_label = self.query_one("#status-message", Label)
            status_label.update("[yellow]Debug logs cleared![/yellow]")
            self.set_timer(2.0, lambda: status_label.update(""))

    def save_settings(self) -> None:
        """Save current settings to config."""
        theme_select = self.query_one("#theme-select", Select)
        quality_select = self.query_one("#quality-select", Select)
        auto_play_select = self.query_one("#auto-play-select", Select)
        status_label = self.query_one("#status-message", Label)

        # Save theme
        if theme_select.value:
            theme = str(theme_select.value)
            self.config.theme = theme
            self.post_message(self.ThemeChanged(theme))

        # Save quality
        if quality_select.value:
            quality = str(quality_select.value)
            self.config.quality = quality
            self.post_message(self.QualityChanged(quality))

        # Save auto-play setting
        if auto_play_select.value:
            auto_play = str(auto_play_select.value) == "on"
            self.config.auto_play = auto_play

        status_label.update("[green]Settings saved successfully![/green]")
        self.set_timer(2.0, lambda: status_label.update(""))
