"""Player bar component showing current track and playback progress."""

import re
import time
from datetime import datetime

from textual.app import ComposeResult
from textual.containers import Center, Container, Horizontal, Middle
from textual.widgets import Label, ProgressBar, Static
from textual_image.widget import Image

from ttydal.services.mpv_playback_engine import MpvPlaybackEngine
from ttydal.config import ConfigManager
from ttydal.services.image_cache import ImageCache
from ttydal.logger import log


class CoverArtArea(Container):
    """Cover art container that accepts Tab focus for keyboard navigation."""

    can_focus = True


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
        width: 8;
        height: 5;
        min-width: 8;
        max-width: 8;
        border: solid $accent-darken-2;
    }

    PlayerBar #cover-art-container:focus {
        border: solid $accent;
    }

    PlayerBar #cover-art-container Image {
        width: 100%;
        height: 100%;
    }

    PlayerBar #cover-placeholder {
        width: 8;
        height: 5;
        content-align: center middle;
        color: $text-muted;
        hatch: cross $primary 30%;
    }

    PlayerBar #info-container {
        width: 1fr;
        height: 100%;
    }

    PlayerBar #status-info {
        display: none;
    }
    """

    def __init__(self):
        """Initialize the player bar."""
        super().__init__()
        self.player = MpvPlaybackEngine()
        self.config = ConfigManager()
        self.quality = "N/A"
        self.stream_metadata = None
        self._current_cover_url: str | None = None
        self._image_widget: Image | None = None
        self._vibrant_color: str | None = None
        self._status_visible: bool = False
        self._reconnecting: bool = False
        self._reconnected_at: float | None = None
        self._reconnected_time_str: str | None = None

    def compose(self) -> ComposeResult:
        """Compose the player bar UI."""
        with Horizontal(id="player-content"):
            with CoverArtArea(id="cover-art-container"):
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
                        with Center():
                            yield Label("", id="status-info")

    def on_mount(self) -> None:
        """Set up update interval when mounted."""
        self.set_interval(0.5, self.update_display)

    def on_click(self, event) -> None:
        """Open cover art modal when the cover art area is clicked."""
        # Cover art occupies the leftmost 8 columns of the player bar
        if event.x < 8 and self._current_cover_url:
            from ttydal.components.cover_art_modal import CoverArtModal
            self.app.push_screen(CoverArtModal(self._current_cover_url))

    def on_key(self, event) -> None:
        """Open cover art modal when Enter is pressed on the focused cover art area."""
        if event.key == "enter":
            try:
                if self.query_one("#cover-art-container").has_focus and self._current_cover_url:
                    from ttydal.components.cover_art_modal import CoverArtModal
                    self.app.push_screen(CoverArtModal(self._current_cover_url))
                    event.stop()
            except Exception:
                pass

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

        if self.config.shuffle:
            indicators.append("[green]⏺[/green] Shuffle")
        else:
            indicators.append("[dim]⏺[/dim] Shuffle")

        if self.config.auto_play:
            indicators.append("[green]⏺[/green] Auto")
        else:
            indicators.append("[dim]⏺[/dim] Auto")

        return "  ".join(indicators)

    def _format_quality_short(self) -> str:
        """Abbreviated quality: bit_depth/kHz only, no quality name."""
        if not self.stream_metadata:
            return self.quality.upper() if self.quality else "N/A"

        bit_depth = self.stream_metadata.get("bit_depth")
        sample_rate = self.stream_metadata.get("sample_rate")

        if bit_depth and sample_rate:
            return f"{bit_depth}bit/{sample_rate / 1000:.0f}kHz"
        if sample_rate:
            return f"{sample_rate / 1000:.0f}kHz"

        return self.stream_metadata.get("audio_quality", "N/A") or "N/A"

    def _format_quality_tiny(self) -> str:
        """Minimal quality: just kHz value."""
        if not self.stream_metadata:
            q = self.quality.upper() if self.quality else "N/A"
            return q[:4]

        sample_rate = self.stream_metadata.get("sample_rate")
        if sample_rate:
            return f"{sample_rate / 1000:.0f}kHz"

        q = self.stream_metadata.get("audio_quality", "")
        return (q[:4] if q else "N/A")

    def update_display(self) -> None:
        """Update the player bar display."""
        track = self.player.get_current_track()
        progress_bar = self.query_one("#progress", ProgressBar)
        track_label = self.query_one("#track-info", Label)
        time_label = self.query_one("#time-info", Label)
        status_label = self.query_one("#status-info", Label)

        # Available width for the info container (terminal width minus cover art)
        info_width = max(0, self.size.width - 10)
        is_narrow = info_width < 55

        if track:
            track_name = track.get("name", "Unknown")
            artist = track.get("artist", "Unknown Artist")
            album = track.get("album", "Unknown Album")

            track_text = f"{track_name} by {artist} from {album}"

            # Truncate title if it exceeds available width
            max_title = max(10, info_width - 2)
            if len(track_text) > max_title:
                track_text = track_text[: max(1, max_title - 3)] + "..."

            if self._vibrant_color:
                track_label.update(f"[{self._vibrant_color}]{track_text}[/]")
            else:
                track_label.update(track_text)

            duration = self.player.get_duration()
            time_pos = self.player.get_time_pos()

            if duration > 0:
                progress_bar.update(total=duration, progress=time_pos)
                time_str = f"{self._format_time(time_pos)} / {self._format_time(duration)}"
            else:
                time_str = "0:00 / 0:00"
            self._update_info_labels(
                time_label, status_label, time_str, info_width, is_narrow
            )
        else:
            track_label.update("No track playing")
            progress_bar.update(total=100, progress=0)
            self._update_info_labels(
                time_label, status_label, "0:00 / 0:00", info_width, is_narrow
            )

    def set_reconnecting(self, state: bool) -> None:
        """Show or hide the reconnecting indicator.

        Args:
            state: True while retrying the stream, False when resolved
        """
        self._reconnecting = state
        self.update_display()

    def set_reconnected(self) -> None:
        """Mark recovery as complete — show a 5s green 'reconnected HH:MM' notice."""
        self._reconnecting = False
        self._reconnected_at = time.monotonic()
        self._reconnected_time_str = datetime.now().strftime("%H:%M")
        log(f"PlayerBar: Network recovered at {self._reconnected_time_str}")
        self.update_display()

    def _update_info_labels(
        self,
        time_label: Label,
        status_label: Label,
        time_str: str,
        info_width: int,
        is_narrow: bool,
    ) -> None:
        """Render time/quality/status/network state into the info labels."""
        # --- Network status row (takes priority over shuffle/auto indicators) ---
        network_notice = ""
        if self._reconnecting:
            # Slow flash: bright for 0.75 s, dim for 0.75 s (1.5 s period)
            bright = (time.monotonic() % 1.5) < 0.75
            if bright:
                network_notice = "[yellow]⟳ Reconnecting…[/yellow]"
            else:
                network_notice = "[dim yellow]⟳ Reconnecting…[/dim yellow]"
        elif self._reconnected_at is not None:
            if time.monotonic() - self._reconnected_at < 5:
                network_notice = (
                    f"[green]⏺ reconnected {self._reconnected_time_str}[/green]"
                )
            else:
                self._reconnected_at = None
                self._reconnected_time_str = None

        # Status row content and visibility
        if network_notice:
            status_content = network_notice
            show_status = True
        elif is_narrow:
            # Narrow mode: shuffle/auto indicators overflow onto a second line
            status_content = self._format_status_indicators()
            show_status = True
        else:
            status_content = ""
            show_status = False

        # Only touch display + height when the visibility state actually changes
        if show_status != self._status_visible:
            self._status_visible = show_status
            status_label.display = show_status
            self.styles.height = 6 if show_status else 5

        status_label.update(status_content)

        # --- Time / quality row (always shows shuffle/auto inline when wide) ---
        status_str = self._format_status_indicators()
        if is_narrow:
            time_label.update(f"{time_str}  |  {self._format_quality_tiny()}")
        elif info_width >= 65:
            time_label.update(f"{time_str}  |  {self._format_quality()}  |  {status_str}")
        else:
            time_label.update(f"{time_str}  |  {self._format_quality_short()}  |  {status_str}")

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
