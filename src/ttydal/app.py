"""Main TUI application for ttydal."""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, TabbedContent, TabPane

from ttydal.pages.player_page import PlayerPage
from ttydal.pages.config_page import ConfigPage
from ttydal.tidal_client import TidalClient
from ttydal.player import Player
from ttydal.components.player_bar import PlayerBar
from ttydal.components.login_modal import LoginModal
from ttydal.config import ConfigManager
from ttydal.logger import log


class TtydalApp(App):
    """Main ttydal TUI application."""

    CSS = """
    Screen {
        background: $surface;
    }

    TabbedContent {
        height: 1fr;
    }

    TabPane {
        padding: 0;
    }
    """

    BINDINGS = [
        Binding("p", "show_player", "Player", show=True),
        Binding("c", "show_config", "Config", show=True),
        Binding("a", "focus_albums", "Albums", show=True),
        Binding("t", "focus_tracks", "Tracks", show=True),
        Binding("space", "toggle_play", "Play/Pause", show=True),
        Binding("n", "toggle_auto_play", "Auto-Play", show=True),
        Binding("s", "toggle_shuffle", "Shuffle", show=True),
        Binding("shift+left", "seek_backward", "Seek -10s", show=True),
        Binding("shift+right", "seek_forward", "Seek +10s", show=True),
        Binding("P", "play_previous", "Previous", show=True),
        Binding("N", "play_next", "Next", show=True),
        Binding("q", "quit", "Quit", show=True),
    ]

    def __init__(self):
        """Initialize the application."""
        log("TtydalApp.__init__() called")
        super().__init__()
        log("  - super().__init__() completed")

        log("  - Creating TidalClient...")
        self.tidal = TidalClient()
        log("  - TidalClient created")

        log("  - Creating Player...")
        self.player = Player()
        log("  - Player created")

        log("  - Creating ConfigManager...")
        self.config = ConfigManager()
        log(f"  - ConfigManager created, theme={self.config.theme}, quality={self.config.quality}")

        self.current_page = "player"
        log("TtydalApp.__init__() completed")

    def compose(self) -> ComposeResult:
        """Compose the main application UI."""
        log("TtydalApp.compose() called")
        log("  - Creating TabbedContent with PlayerPage and ConfigPage...")

        try:
            with TabbedContent(initial="player-tab"):
                with TabPane("(p)layer", id="player-tab"):
                    log("    - Yielding PlayerPage...")
                    yield PlayerPage()
                    log("    - PlayerPage yielded")
                with TabPane("(c)onfig", id="config-tab"):
                    log("    - Yielding ConfigPage...")
                    yield ConfigPage()
                    log("    - ConfigPage yielded")
            log("  - Yielding Footer...")
            yield Footer()
            log("  - Footer yielded")
            log("TtydalApp.compose() completed")
        except Exception as e:
            log(f"ERROR in compose(): {e}")
            raise

    async def on_mount(self) -> None:
        """Initialize application when mounted."""
        log("TtydalApp.on_mount() called")

        try:
            # Set the theme from config
            log(f"  - Setting theme to: {self.config.theme}")
            self.theme = self.config.theme
            log("  - Theme set successfully")

            # Check if user is logged in
            log("  - Checking if user is logged in...")
            if not self.tidal.load_session():
                log("  - User not logged in, starting login flow in background...")
                # Start login flow in background without blocking
                self.set_timer(0.5, self.start_login_flow)
            else:
                log("  - User already logged in")

            log("TtydalApp.on_mount() completed")
        except Exception as e:
            log(f"ERROR in on_mount(): {e}")
            import traceback
            log(traceback.format_exc())
            raise

    def start_login_flow(self) -> None:
        """Start the login flow with modal."""
        log("Starting login flow with modal...")
        self.login_modal = LoginModal()
        self.push_screen(self.login_modal)
        self.run_worker(self.login_flow(), exclusive=True)

    async def login_flow(self) -> None:
        """Handle Tidal OAuth login flow."""
        log("login_flow() started")

        try:
            log("  - Calling tidal.login()...")
            login_url, code = self.tidal.login()
            log(f"  - Login URL: {login_url}")
            log(f"  - Code: {code}")

            # Update modal with login info
            if hasattr(self, 'login_modal') and self.login_modal:
                self.login_modal.update_login_info(login_url, code)
                # Force a refresh to show the new info
                self.login_modal.refresh(layout=True)

            # Wait for login completion in background
            import asyncio
            log("  - Waiting for user to complete login (no timeout)...")
            check_count = 0
            while True:
                await asyncio.sleep(2)
                check_count += 1

                if self.tidal.complete_login():
                    log("  - Login successful!")
                    if hasattr(self, 'login_modal') and self.login_modal:
                        self.login_modal.update_status("✓ Login successful!")
                        await asyncio.sleep(1)
                        try:
                            self.pop_screen()
                        except Exception:
                            pass

                    self.notify("Login successful!", severity="information")

                    # Reload albums after login
                    try:
                        player_page = self.query_one(PlayerPage)
                        albums_list_widget = player_page.query_one("AlbumsList")
                        if hasattr(albums_list_widget, 'load_albums'):
                            albums_list_widget.load_albums()
                    except Exception as e:
                        log(f"  - Error reloading albums: {e}")
                    return

                # Update status every 10 checks
                if check_count % 10 == 0 and hasattr(self, 'login_modal') and self.login_modal:
                    self.login_modal.update_status(f"Waiting for login... ({check_count * 2}s)")

        except Exception as e:
            log(f"ERROR in login_flow(): {e}")
            import traceback
            log(traceback.format_exc())
            if hasattr(self, 'login_modal') and self.login_modal:
                self.login_modal.update_status(f"Error: {e}")
            self.notify(f"Login error: {e}", severity="error")

    def on_login_modal_check_login(self, message: LoginModal.CheckLogin) -> None:
        """Handle check login button press in modal.

        Args:
            message: Check login message
        """
        log("Manual login check requested")
        if self.tidal.complete_login():
            log("  - Login successful on manual check!")
            if hasattr(self, 'login_modal') and self.login_modal:
                self.login_modal.update_status("✓ Login successful!")
            self.notify("Login successful!", severity="information")

            # Close modal
            try:
                self.pop_screen()
            except Exception:
                pass

            # Reload albums
            try:
                player_page = self.query_one(PlayerPage)
                albums_list_widget = player_page.query_one("AlbumsList")
                if hasattr(albums_list_widget, 'load_albums'):
                    albums_list_widget.load_albums()
            except Exception as e:
                log(f"  - Error reloading albums: {e}")
        else:
            log("  - Login not completed yet")
            if hasattr(self, 'login_modal') and self.login_modal:
                self.login_modal.update_status("Not logged in yet. Please complete the login process.")

    def action_show_player(self) -> None:
        """Switch to player page."""
        tabbed_content = self.query_one(TabbedContent)
        tabbed_content.active = "player-tab"
        self.current_page = "player"

    def action_show_config(self) -> None:
        """Switch to config page."""
        tabbed_content = self.query_one(TabbedContent)
        tabbed_content.active = "config-tab"
        self.current_page = "config"

    def action_focus_albums(self) -> None:
        """Focus albums list on player page."""
        if self.current_page == "player":
            player_page = self.query_one(PlayerPage)
            player_page.focus_albums()

    def action_focus_tracks(self) -> None:
        """Focus tracks list on player page."""
        if self.current_page == "player":
            player_page = self.query_one(PlayerPage)
            player_page.focus_tracks()

    def action_toggle_play(self) -> None:
        """Toggle play/pause or play selected track (smart behavior).

        Behavior:
        - If tracks list is focused: delegate to TracksList (smart play/pause)
        - If tracks list is not focused: toggle pause/play
        """
        log("TtydalApp.action_toggle_play() called")
        if self.current_page == "player":
            # Check if tracks list is focused - if so, let it handle space (smart behavior)
            try:
                focused = self.focused
                # If a ListView inside TracksList has focus, let TracksList handle it
                if focused and focused.id == "tracks-listview":
                    log("  - TracksList focused, delegating to TracksList.action_play_selected_track()")
                    # The binding priority will let TracksList handle it
                    return
            except Exception as e:
                log(f"  - Error checking focus: {e}")

            # Not on tracks list, just toggle pause/play
            log("  - Not on tracks list, toggling pause/play")
            player_page = self.query_one(PlayerPage)
            player_page.toggle_playback()
        else:
            log(f"  - Not on player page (current: {self.current_page})")

    def action_seek_backward(self) -> None:
        """Seek backward 10 seconds."""
        if self.current_page == "player":
            player_page = self.query_one(PlayerPage)
            player_page.seek_backward()

    def action_seek_forward(self) -> None:
        """Seek forward 10 seconds."""
        if self.current_page == "player":
            player_page = self.query_one(PlayerPage)
            player_page.seek_forward()

    def action_toggle_auto_play(self) -> None:
        """Toggle auto-play next track setting."""
        log("TtydalApp.action_toggle_auto_play() called")
        current_state = self.config.auto_play
        new_state = not current_state
        self.config.auto_play = new_state
        log(f"  - Auto-play toggled: {current_state} -> {new_state}")

        # Show notification
        status = "enabled" if new_state else "disabled"
        self.notify(f"Auto-play {status}", severity="information")

    def action_toggle_shuffle(self) -> None:
        """Toggle shuffle playback setting."""
        log("TtydalApp.action_toggle_shuffle() called")
        current_state = self.config.shuffle
        new_state = not current_state
        self.config.shuffle = new_state
        log(f"  - Shuffle toggled: {current_state} -> {new_state}")

        # Notify TracksList to reshuffle if enabling
        if self.current_page == "player":
            player_page = self.query_one(PlayerPage)
            player_page.on_shuffle_changed(new_state)

        # Show notification
        status = "enabled" if new_state else "disabled"
        self.notify(f"Shuffle {status}", severity="information")

    def action_play_next(self) -> None:
        """Play next track."""
        if self.current_page == "player":
            player_page = self.query_one(PlayerPage)
            player_page.play_next()

    def action_play_previous(self) -> None:
        """Play previous track."""
        if self.current_page == "player":
            player_page = self.query_one(PlayerPage)
            player_page.play_previous()

    def on_config_page_theme_changed(
        self, event: ConfigPage.ThemeChanged
    ) -> None:
        """Handle theme setting change.

        Args:
            event: Theme changed event
        """
        # Apply the new theme
        self.theme = event.theme

    def on_config_page_quality_changed(
        self, event: ConfigPage.QualityChanged
    ) -> None:
        """Handle quality setting change.

        Args:
            event: Quality changed event
        """
        # Update player bar display
        player_page = self.query_one(PlayerPage)
        player_bar = player_page.query_one(PlayerBar)
        player_bar.update_quality_display(event.quality)

    def on_config_page_login_requested(
        self, event: ConfigPage.LoginRequested
    ) -> None:
        """Handle login request from config page.

        Args:
            event: Login requested event
        """
        log("Login requested from config page")
        self.start_login_flow()

    def on_config_page_clear_logs_requested(
        self, event: ConfigPage.ClearLogsRequested
    ) -> None:
        """Handle clear logs request from config page.

        Args:
            event: Clear logs requested event
        """
        log("Clear logs requested from config page")
        try:
            from pathlib import Path
            log_file = Path.home() / ".ttydal" / "debug.log"

            if log_file.exists():
                # Clear the log file by truncating it
                with open(log_file, "w") as f:
                    f.write("")
                log("Debug log file cleared successfully")
                self.notify("Debug logs cleared!", severity="information")
            else:
                log("Debug log file does not exist")
                self.notify("No logs to clear", severity="warning")
        except Exception as e:
            log(f"Error clearing logs: {e}")
            self.notify(f"Error clearing logs: {e}", severity="error")

    def on_unmount(self) -> None:
        """Cleanup when application unmounts."""
        log("TtydalApp.on_unmount() called - cleaning up...")
        try:
            log("  - Shutting down player...")
            self.player.shutdown()
            log("  - Player shutdown complete")
        except Exception as e:
            log(f"  - Error during player shutdown: {e}")
        log("TtydalApp.on_unmount() completed")

    async def action_quit(self) -> None:
        """Quit the application cleanly."""
        log("action_quit() called")
        try:
            # Cancel any running workers
            log("  - Cancelling workers...")
            self.workers.cancel_all()
            log("  - Workers cancelled")
        except Exception as e:
            log(f"  - Error cancelling workers: {e}")

        log("  - Calling self.exit()...")
        self.exit()
        log("  - self.exit() returned")
