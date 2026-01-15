"""Cache info modal showing cache statistics with visual indicators."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Label

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
        height: 12;
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

    #cache-container Label.hint {
        margin-top: 1;
        text-align: center;
        width: 100%;
        color: $text-muted;
    }
    """

    def _render_visual_bar(self, current: int, maximum: int, width: int = 10) -> str:
        """Render a visual bar using database icons.

        Args:
            current: Current number of items
            maximum: Maximum capacity
            width: Number of icons to display

        Returns:
            Formatted string with colored icons
        """
        if maximum == 0:
            return " ".join(["[dim]\u26f6[/dim]"] * width)

        ratio = current / maximum
        filled = int(ratio * width)
        icons = []
        for i in range(width):
            if i < filled:
                icons.append("[green]\u26c1[/green]")
            else:
                icons.append("[dim]\u26f6[/dim]")
        return " ".join(icons)

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

        visual_bar = self._render_visual_bar(tracks_count, max_tracks)
        tracks_display = (
            f"{self._format_count(tracks_count)}/{self._format_count(max_tracks)}"
        )

        with Container(id="cache-container"):
            yield Label("Cache Status", classes="title")
            yield Label("Tracks Cached", classes="stat-label")
            yield Label(f"{visual_bar}  {tracks_display}", classes="visual-bar")
            yield Label(f"Albums: {albums_count}", classes="stat-label")
            ttl_label = "hour" if ttl_hours == 1 else "hours"
            yield Label(f"TTL: {ttl_hours} {ttl_label}", classes="stat-label")
            yield Label("Press ESC to close", classes="hint")

    def action_close_modal(self) -> None:
        """Close the cache modal."""
        self.dismiss(None)
