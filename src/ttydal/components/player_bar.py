"""Player bar component showing current track and playback progress."""

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Label, ProgressBar

from ttydal.player import Player


class PlayerBar(Container):
    """Player bar widget displaying current track and progress."""

    DEFAULT_CSS = """
    PlayerBar {
        height: 3;
        dock: top;
        background: $panel;
        border-bottom: solid $primary;
    }

    PlayerBar Label {
        width: 1fr;
        content-align: center middle;
    }

    PlayerBar ProgressBar {
        width: 1fr;
    }
    """

    def __init__(self):
        """Initialize the player bar."""
        super().__init__()
        self.player = Player()

    def compose(self) -> ComposeResult:
        """Compose the player bar UI."""
        yield Label("No track playing", id="track-info")
        yield ProgressBar(total=100, show_eta=False, id="progress")
        yield Label("Quality: N/A", id="quality-info")

    def on_mount(self) -> None:
        """Set up update interval when mounted."""
        self.set_interval(0.5, self.update_display)

    def update_display(self) -> None:
        """Update the player bar display."""
        track = self.player.get_current_track()
        progress_bar = self.query_one("#progress", ProgressBar)
        track_label = self.query_one("#track-info", Label)

        if track:
            track_name = track.get("name", "Unknown")
            artist = track.get("artist", "Unknown Artist")
            track_label.update(f"{artist} - {track_name}")

            duration = self.player.get_duration()
            time_pos = self.player.get_time_pos()

            if duration > 0:
                progress_bar.update(total=duration, progress=time_pos)
        else:
            track_label.update("No track playing")
            progress_bar.update(total=100, progress=0)

    def update_quality_display(self, quality: str) -> None:
        """Update quality display.

        Args:
            quality: Current quality setting ('high' or 'low')
        """
        quality_label = self.query_one("#quality-info", Label)
        quality_label.update(f"Quality: {quality.upper()}")
