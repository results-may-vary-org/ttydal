"""Player bar component showing current track and playback progress."""

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Label, ProgressBar

from ttydal.player import Player


class PlayerBar(Container):
    """Player bar widget displaying current track and progress."""

    DEFAULT_CSS = """
    PlayerBar {
        height: 4;
        dock: top;
        background: $panel;
        border-bottom: solid $primary;
        padding: 0 1;
    }

    PlayerBar Label {
        width: 1fr;
        content-align: center middle;
    }

    PlayerBar #track-info {
        text-style: bold;
    }

    PlayerBar #time-info {
        height: 1;
    }

    PlayerBar ProgressBar {
        width: 1fr;
    }
    """

    def __init__(self):
        """Initialize the player bar."""
        super().__init__()
        self.player = Player()
        self.quality = "N/A"
        self.stream_metadata = None

    def compose(self) -> ComposeResult:
        """Compose the player bar UI."""
        yield Label("No track playing", id="track-info")
        yield ProgressBar(total=100, show_eta=False, id="progress")
        yield Label("0:00 / 0:00  |  Quality: N/A", id="time-info")

    def on_mount(self) -> None:
        """Set up update interval when mounted."""
        self.set_interval(0.5, self.update_display)

    def _format_time(self, seconds: float) -> str:
        """Format time in seconds to MM:SS.

        Args:
            seconds: Time in seconds

        Returns:
            Formatted time string
        """
        minutes = int(seconds) // 60
        secs = int(seconds) % 60
        return f"{minutes}:{secs:02d}"

    def _format_quality(self) -> str:
        """Format quality information from stream metadata.

        Returns:
            Formatted quality string
        """
        if not self.stream_metadata:
            return self.quality.upper() if self.quality else "N/A"

        # Extract metadata
        audio_quality = self.stream_metadata.get('audio_quality', 'Unknown')
        bit_depth = self.stream_metadata.get('bit_depth')
        sample_rate = self.stream_metadata.get('sample_rate')

        # Build quality string
        parts = []

        # Add audio quality name
        if audio_quality != 'Unknown':
            parts.append(audio_quality)

        # Add bit depth and sample rate if available
        if bit_depth and sample_rate:
            # Convert sample rate to kHz
            sample_rate_khz = sample_rate / 1000
            parts.append(f"{bit_depth}bit/{sample_rate_khz:.1f}kHz")
        elif bit_depth:
            parts.append(f"{bit_depth}bit")
        elif sample_rate:
            sample_rate_khz = sample_rate / 1000
            parts.append(f"{sample_rate_khz:.1f}kHz")

        return " ".join(parts) if parts else "N/A"

    def update_display(self) -> None:
        """Update the player bar display."""
        track = self.player.get_current_track()
        progress_bar = self.query_one("#progress", ProgressBar)
        track_label = self.query_one("#track-info", Label)
        time_label = self.query_one("#time-info", Label)

        if track:
            track_name = track.get("name", "Unknown")
            artist = track.get("artist", "Unknown Artist")
            album = track.get("album", "Unknown Album")

            # Format: "Track by Artist from Album"
            track_label.update(f"{track_name} by {artist} from {album}")

            duration = self.player.get_duration()
            time_pos = self.player.get_time_pos()

            if duration > 0:
                progress_bar.update(total=duration, progress=time_pos)
                # Show time and quality with detailed stream info
                time_str = f"{self._format_time(time_pos)} / {self._format_time(duration)}"
                quality_str = self._format_quality()
                time_label.update(f"{time_str}  |  {quality_str}")
        else:
            track_label.update("No track playing")
            progress_bar.update(total=100, progress=0)
            quality_str = self._format_quality()
            time_label.update(f"0:00 / 0:00  |  {quality_str}")

    def update_quality_display(self, quality: str) -> None:
        """Update quality display.

        Args:
            quality: Current quality setting ('high' or 'low')
        """
        self.quality = quality

    def update_stream_quality(self, stream_metadata: dict) -> None:
        """Update with actual stream quality metadata.

        Args:
            stream_metadata: Dict with audio_quality, bit_depth, sample_rate, audio_mode
        """
        self.stream_metadata = stream_metadata
