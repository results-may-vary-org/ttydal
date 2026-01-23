"""Cache info modal showing cache statistics with visual indicators."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Label, Rule, Static

from ttydal.services.tracks_cache import TracksCache
from ttydal.image_cache import ImageCache


class CacheModal(ModalScreen):
    """Modal screen displaying cache statistics."""

    BINDINGS = [
        Binding("escape", "close_modal", "Close", show=True),
    ]

    CSS = """
    CacheModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }

    #cache-container {
        width: 50;
        height: 20;
        background: $surface;
        padding: 1;
    }

    #cache-container Label.section-title {
        text-style: bold;
        color: $secondary;
        margin-top: 1;
        text-align: center;
        width: 100%;
    }

    #cache-container Label.title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
        text-align: center;
        width: 100%;
    }

    #cache-container Static.stat-label {
        text-align: center;
    }

    #cache-container Label.visual-bar {
        text-align: center;
        width: 100%;
    }

    #cache-container Label.legend {
        text-align: center;
        width: 100%;
        margin-top: 1;
    }

    #cache-container Label.hint {
        margin-top: 1;
        text-align: center;
        width: 100%;
        color: $text-muted;
    }

    /* Theme-aware colors for visual bar icons */
    .icon-complete {
        color: $success;
    }
    .icon-progress {
        color: $warning;
    }
    .icon-pending {
        color: $text-muted;
    }

    #visual-bar-container {
        align: center middle;
        width: 100%;
        height: auto;
    }

    #visual-bar-container Static {
        width: auto;
        min-width: 2;
    }

    #legend-container {
        align: center middle;
        width: 100%;
        height: auto;
        margin-top: 1;
    }
    """

    def _get_icon_states(
        self, current: int, maximum: int, width: int = 10
    ) -> list[str]:
        """Get CSS class names for each icon in the visual bar.

        States:
        - icon-complete: Filled slots (theme $success color)
        - icon-progress: Current slot at boundary (theme $warning color)
        - icon-pending: Empty slots (theme $text-muted color)

        Args:
            current: Current number of items
            maximum: Maximum capacity
            width: Number of icons to display

        Returns:
            List of CSS class names for each icon position
        """
        if maximum == 0:
            return ["icon-pending"] * width

        ratio = current / maximum
        filled_exact = ratio * width
        filled = int(filled_exact)

        states = []
        for i in range(width):
            if i < filled:
                states.append("icon-complete")
            elif i == filled and filled_exact > filled:
                states.append("icon-progress")
            else:
                states.append("icon-pending")
        return states

    def _format_count(self, count: int) -> str:
        """Format large numbers with K suffix."""
        if count >= 1000:
            return f"{count / 1000:.1f}K"
        return str(count)

    def _format_size(self, size_mb: float) -> str:
        """Format size in MB or KB."""
        if size_mb >= 1:
            return f"{size_mb:.1f} MB"
        return f"{size_mb * 1024:.0f} KB"

    def compose(self) -> ComposeResult:
        """Compose the cache modal UI."""
        # Tracks cache stats
        tracks_cache = TracksCache()
        tracks_stats = tracks_cache.get_stats()

        albums_count = tracks_stats["albums_count"]
        tracks_count = tracks_stats["tracks_count"]
        max_tracks = tracks_stats["max_tracks"]
        ttl_hours = tracks_stats["ttl"] // 3600

        # Image cache stats
        image_cache = ImageCache()
        image_stats = image_cache.get_stats()
        image_count = image_stats["count"]
        image_size_mb = image_stats["size_mb"]

        icon = "\u26c1"  # ⛁
        icon_states = self._get_icon_states(tracks_count, max_tracks)
        album_label = "albums" if albums_count > 1 else "album"
        track_label = "tracks" if tracks_count > 1 else "track"
        tracks_display = (
            f"{self._format_count(tracks_count)}/{self._format_count(max_tracks)} {track_label} over {albums_count} {album_label}"
        )

        ttl_label = "hour" if ttl_hours == 1 else "hours"

        with Container(id="cache-container"):
            yield Label("Cache Status", classes="title")
            yield Rule()

            # Tracks cache section
            yield Label(f"Tracks Cache (ttl {ttl_hours} {ttl_label})", classes="section-title")
            with Horizontal(id="visual-bar-container"):
                for state in icon_states:
                    yield Static(icon, classes=state)
            yield Static(f"{tracks_display}", classes="stat-label")
            yield Rule()

            # Image cache section
            yield Label("Cover Art Cache", classes="section-title")
            yield Static(
                f"Images: {image_count}  |  Size: {self._format_size(image_size_mb)}",
                classes="stat-label",
            )
            yield Rule()

            yield Label("Press ESC to close", classes="hint")

    def action_close_modal(self) -> None:
        """Close the cache modal."""
        self.dismiss(None)
