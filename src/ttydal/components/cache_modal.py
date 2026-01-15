"""Cache info modal showing cache statistics with visual indicators."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Label, Static

from ttydal.services.tracks_cache import TracksCache


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
        height: 15;
        background: $surface;
        keyline: heavy $primary;
        padding: 1;
    }

    #cache-container Label.title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
        text-align: center;
        width: 100%;
    }

    #cache-container Label.stat-label {
        margin-top: 1;
        text-align: center;
        width: 100%;
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

    #legend-container Static {
        width: auto;
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

    def compose(self) -> ComposeResult:
        """Compose the cache modal UI."""
        cache = TracksCache()
        stats = cache.get_stats()

        albums_count = stats["albums_count"]
        tracks_count = stats["tracks_count"]
        max_tracks = stats["max_tracks"]
        ttl_hours = stats["ttl"] // 3600

        icon = "\u26c1"  # ⛁
        icon_states = self._get_icon_states(tracks_count, max_tracks)
        tracks_display = (
            f"{self._format_count(tracks_count)}/{self._format_count(max_tracks)}"
        )

        with Container(id="cache-container"):
            yield Label("Cache Status", classes="title")
            yield Label("Tracks Cached", classes="stat-label")
            with Horizontal(id="visual-bar-container"):
                for state in icon_states:
                    yield Static(icon, classes=state)
                yield Static(f"  {tracks_display}")
            yield Label(f"Albums: {albums_count}", classes="stat-label")
            ttl_label = "hour" if ttl_hours == 1 else "hours"
            yield Label(f"TTL: {ttl_hours} {ttl_label}", classes="stat-label")
            # Legend showing color meanings
            with Horizontal(id="legend-container"):
                yield Static("●", classes="icon-complete")
                yield Static(" complete  ")
                yield Static("●", classes="icon-progress")
                yield Static(" progress  ")
                yield Static("●", classes="icon-pending")
                yield Static(" pending")
            yield Label("Press ESC to close", classes="hint")

    def action_close_modal(self) -> None:
        """Close the cache modal."""
        self.dismiss(None)
