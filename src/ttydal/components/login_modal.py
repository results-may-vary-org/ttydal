"""Login modal for Tidal OAuth authentication."""

import webbrowser
import pyperclip

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical, Horizontal
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static

from ttydal.logger import log


class LoginModal(ModalScreen):
    """Modal screen for Tidal OAuth login."""

    BINDINGS = [
        Binding("o", "open_url", "Open URL", show=True),
        Binding("c", "copy_url", "Copy URL", show=True),
        Binding("l", "check_login", "Check Login", show=True),
        Binding("escape", "close_modal", "Close", show=True),
    ]

    CSS = """
    LoginModal {
        align: center middle;
    }

    LoginModal > Container {
        width: 80;
        height: auto;
        background: $panel;
        border: thick $primary;
        padding: 2;
    }

    LoginModal Label {
        width: 1fr;
        text-align: center;
        margin-bottom: 1;
    }

    LoginModal .title {
        text-style: bold;
        color: $primary;
        margin-bottom: 2;
    }

    LoginModal .url {
        background: $surface;
        padding: 1;
        border: solid $accent;
        margin: 1 0;
    }

    LoginModal .code {
        text-style: bold;
        color: $secondary;
        text-align: center;
        padding: 1;
        background: $boost;
        margin: 1 0;
    }

    LoginModal .status {
        margin-top: 2;
        margin-bottom: 1;
        text-align: center;
    }

    LoginModal Button {
        width: 1fr;
        margin-top: 1;
    }

    LoginModal .button-row {
        layout: horizontal;
        width: 1fr;
        height: auto;
        margin-top: 1;
    }

    LoginModal .button-row Button {
        margin: 0 1;
    }

    LoginModal .url-actions {
        layout: horizontal;
        width: 1fr;
        height: auto;
        margin: 1 0;
    }

    LoginModal .url-actions Button {
        width: 1fr;
        margin: 0 1;
    }
    """

    def __init__(
        self,
        login_url: str | None = None,
        code: str | None = None,
        status: str = "Waiting for login..."
    ):
        """Initialize the login modal.

        Args:
            login_url: The OAuth login URL
            code: The verification code
            status: Current status message
        """
        super().__init__()
        self.login_url = login_url
        self.code = code
        self.status_text = status

    def compose(self) -> ComposeResult:
        """Compose the login modal UI."""
        with Container():
            yield Label("Tidal Login Required", classes="title")

            yield Label("Please visit this URL to login:", id="url-label")
            yield Static(
                self.login_url if self.login_url else "Loading...",
                classes="url",
                id="url-display"
            )

            with Horizontal(classes="url-actions"):
                yield Button("🌐 Open in Browser", variant="success", id="open-url-btn")
                yield Button("📋 Copy URL", variant="default", id="copy-url-btn")

            yield Label("Verification Code:", id="code-label")
            yield Static(
                self.code if self.code else "Loading...",
                classes="code",
                id="code-display"
            )

            yield Label(self.status_text, id="status-label", classes="status")

            with Vertical(classes="button-row"):
                yield Button("Check Login Status", variant="primary", id="check-btn")
                yield Button("Close", variant="default", id="close-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses.

        Args:
            event: Button press event
        """
        if event.button.id == "close-btn":
            self.dismiss(False)
        elif event.button.id == "check-btn":
            self.app.post_message(LoginModal.CheckLogin())
        elif event.button.id == "open-url-btn":
            self.open_url_in_browser()
        elif event.button.id == "copy-url-btn":
            self.copy_url_to_clipboard()

    def open_url_in_browser(self) -> None:
        """Open the login URL in the default browser."""
        log("LoginModal: Open URL in browser requested")
        if not self.login_url:
            log("  - URL not available yet")
            self.update_status("❌ URL not available yet")
            return

        try:
            log(f"  - Opening URL: {self.login_url}")
            webbrowser.open(self.login_url)
            log("  - URL opened successfully")
            self.update_status("✓ Opened in browser!")
        except Exception as e:
            log(f"  - Error opening browser: {e}")
            self.update_status(f"❌ Error opening browser: {e}")

    def copy_url_to_clipboard(self) -> None:
        """Copy the login URL to clipboard."""
        log("LoginModal: Copy URL to clipboard requested")
        if not self.login_url:
            log("  - URL not available yet")
            self.update_status("❌ URL not available yet")
            return

        try:
            log(f"  - Copying URL to clipboard: {self.login_url}")
            pyperclip.copy(self.login_url)
            log("  - URL copied successfully")
            self.update_status("✓ URL copied to clipboard!")
        except Exception as e:
            log(f"  - Error copying to clipboard: {e}")
            self.update_status(f"❌ Error copying: {e}")

    def update_status(self, status: str) -> None:
        """Update the status label.

        Args:
            status: New status message
        """
        try:
            status_label = self.query_one("#status-label", Label)
            status_label.update(status)
        except Exception:
            pass

    def update_login_info(self, login_url: str, code: str) -> None:
        """Update login information.

        Args:
            login_url: The OAuth login URL
            code: The verification code
        """
        self.login_url = login_url
        self.code = code

        # Try to update existing widgets
        try:
            # Find and update URL widget
            url_display = self.query_one("#url-display", Static)
            url_display.update(login_url)

            # Find and update code widget
            code_display = self.query_one("#code-display", Static)
            code_display.update(code)
        except Exception as e:
            # Widgets might not be mounted yet
            pass

    def action_open_url(self) -> None:
        """Action to open URL in browser (keyboard shortcut)."""
        self.open_url_in_browser()

    def action_copy_url(self) -> None:
        """Action to copy URL to clipboard (keyboard shortcut)."""
        self.copy_url_to_clipboard()

    def action_check_login(self) -> None:
        """Action to check login status (keyboard shortcut)."""
        self.app.post_message(LoginModal.CheckLogin())

    def action_close_modal(self) -> None:
        """Action to close modal (keyboard shortcut)."""
        self.dismiss(False)

    class CheckLogin(Message):
        """Message to check login status."""
        pass
