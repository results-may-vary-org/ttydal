"""Player bar component showing current track and playback progress."""

import re

from textual.app import ComposeResult
from textual.containers import Center, Container, Horizontal, Middle
from textual.widgets import Label, ProgressBar, Static
from textual_image.widget import Image

from ttydal.player import Player
from ttydal.config import ConfigManager
from ttydal.image_cache import ImageCache
from ttydal.logger import log


class PlayerBar(Container):
    """Player bar widget displaying current track and progress."""

    DEFAULT_CSS = """
    PlayerBar {
        height: 5;
        dock: top;
        background: $panel;
    }

    PlayerBar #track-info {
        text-style: bold;
    }

    PlayerBar #player-content {
        width: 1fr;
        height: 100%;
    }

    PlayerBar #cover-art-container {
        width: 10;
        height: 5;
        min-width: 10;
        max-width: 10;
    }

    PlayerBar #cover-art-container Image {
        width: 100%;
        height: 100%;
    }

    PlayerBar #cover-placeholder {
        width: 10;
        height: 5;
        content-align: center middle;
        color: $text-muted;
        hatch: cross $primary 30%;
    }

    PlayerBar #info-container {
        width: 1fr;
        height: 100%;
    }
    """

    def __init__(self):
        """Initialize the player bar."""
        super().__init__()
        self.player = Player()
        self.config = ConfigManager()
        self.quality = "N/A"
        self.stream_metadata = None
        self._current_cover_url: str | None = None
        self._image_widget: Image | None = None
        self._vibrant_color: str | None = None

    def compose(self) -> ComposeResult:
        """Compose the player bar UI."""
        with Horizontal(id="player-content"):
            with Container(id="cover-art-container"):
                yield Static("[No Art]", id="cover-placeholder")
            with Container(id="info-container"):
                with Center():
                    with Middle():
                        with Center():
                            yield Label("Select a track", id="track-info")
                        with Center():
                            yield ProgressBar(total=100, show_eta=False, id="progress")
                        with Center():
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
        audio_quality = self.stream_metadata.get("audio_quality", "Unknown")
        bit_depth = self.stream_metadata.get("bit_depth")
        sample_rate = self.stream_metadata.get("sample_rate")

        # Build quality string
        parts = []

        # Add audio quality name
        if audio_quality != "Unknown":
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

    def _format_status_indicators(self) -> str:
        """Format status indicators for shuffle and auto-play.

        Returns:
            Formatted string with colored status indicators
        """
        indicators = []

        # Shuffle indicator
        if self.config.shuffle:
            indicators.append("[green]⏺[/green] Shuffle")
        else:
            indicators.append("[dim]⏺[/dim] Shuffle")

        # Auto-play indicator
        if self.config.auto_play:
            indicators.append("[green]⏺[/green] Auto")
        else:
            indicators.append("[dim]⏺[/dim] Auto")

        return "  ".join(indicators)

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
            track_text = f"{track_name} by {artist} from {album}"

            # Apply vibrant color if set
            if self._vibrant_color:
                track_label.update(f"[{self._vibrant_color}]{track_text}[/]")
            else:
                track_label.update(track_text)

            duration = self.player.get_duration()
            time_pos = self.player.get_time_pos()

            if duration > 0:
                progress_bar.update(total=duration, progress=time_pos)
                # Show time, quality, and status indicators
                time_str = (
                    f"{self._format_time(time_pos)} / {self._format_time(duration)}"
                )
                quality_str = self._format_quality()
                status_str = self._format_status_indicators()
                time_label.update(f"{time_str}  |  {quality_str}  |  {status_str}")
        else:
            track_label.update("No track playing")
            progress_bar.update(total=100, progress=0)
            quality_str = self._format_quality()
            status_str = self._format_status_indicators()
            time_label.update(f"0:00 / 0:00  |  {quality_str}  |  {status_str}")

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

    def update_vibrant_color(self, color: str | None) -> None:
        """Update the vibrant color for track info text.

        Args:
            color: Hex color string (e.g., "#f2d869") or None to reset
        """
        self._vibrant_color = color
        log(f"PlayerBar: Vibrant color set to {color}")

    def update_cover_art(self, cover_url: str | None) -> None:
        """Update the cover art display.

        Args:
            cover_url: URL of the cover art image, or None to clear
        """
        if cover_url == self._current_cover_url:
            return  # No change needed

        self._current_cover_url = cover_url
        log(f"PlayerBar: Updating cover art: {cover_url}")

        if cover_url:
            # Load the cover art asynchronously
            self.run_worker(self._load_cover_art(cover_url))
        else:
            # Clear cover art - show placeholder
            self._show_placeholder()

    def _get_large_cover_url(self, url: str) -> str:
        """Convert a cover URL to request a larger image size.

        Handles various Tidal URL formats:
        - /80x80.jpg -> /320x320.jpg
        - /80x80 -> /320x320

        Args:
            url: Original cover URL (typically 80x80)

        Returns:
            URL for larger image (320x320)
        """
        # Try to replace dimension pattern (e.g., /80x80 or /160x160)
        large_url = re.sub(r"/\d+x\d+", "/320x320", url)
        if large_url != url:
            return large_url
        # If no pattern found, return original
        return url

    async def _load_cover_art(self, cover_url: str) -> None:
        """Load cover art image asynchronously.

        Args:
            cover_url: URL of the cover art to load
        """
        try:
            cache = ImageCache()
            # Use larger image for player bar (320x320)
            large_url = self._get_large_cover_url(cover_url)
            log(f"PlayerBar: Loading cover art from {large_url}")

            img = await cache.get_image(large_url)

            if img and cover_url == self._current_cover_url:
                # Make sure this is still the current track's cover
                log("PlayerBar: Cover art loaded successfully, displaying")
                self._show_cover_image(img)
            elif not img:
                log(f"PlayerBar: Failed to get image from cache for {large_url}")
            else:
                log("PlayerBar: Cover URL changed while loading, skipping display")
        except Exception as e:
            log(f"PlayerBar: Failed to load cover art: {e}")

    def _show_cover_image(self, img) -> None:
        """Display cover art image.

        Args:
            img: PIL Image to display
        """
        try:
            container = self.query_one("#cover-art-container")

            # Remove existing image widget if present
            if self._image_widget is not None:
                try:
                    self._image_widget.remove()
                except Exception:
                    pass
                self._image_widget = None

            # Remove any placeholder
            try:
                placeholder = container.query_one("#cover-placeholder")
                placeholder.remove()
            except Exception:
                pass

            # Add new image widget (no ID to avoid conflicts)
            self._image_widget = Image(img)
            container.mount(self._image_widget)
        except Exception as e:
            log(f"PlayerBar: Error showing cover image: {e}")

    def _show_placeholder(self) -> None:
        """Show the placeholder when no cover art is available."""
        try:
            container = self.query_one("#cover-art-container")

            # Remove existing image widget if present
            if self._image_widget is not None:
                try:
                    self._image_widget.remove()
                except Exception:
                    pass
                self._image_widget = None

            # Check if placeholder already exists
            try:
                container.query_one("#cover-placeholder")
                return  # Already has placeholder
            except Exception:
                pass

            # Add placeholder
            container.mount(Static("[No Art]", id="cover-placeholder"))
        except Exception as e:
            log(f"PlayerBar: Error showing placeholder: {e}")
