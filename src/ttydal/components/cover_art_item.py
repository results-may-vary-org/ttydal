"""Cover art list item component.

A custom widget that displays a cover art image alongside text for use in ListViews.
Images are loaded lazily - only when the item becomes visible in the viewport.
"""

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Label, Static
from textual_image.widget import Image

from ttydal.image_cache import ImageCache
from ttydal.logger import log


class CoverArtItem(Static):
    """A list item widget with cover art and text.

    Displays a small cover art image on the left with text on the right.
    Used in albums and tracks lists.

    Images are loaded lazily when the item scrolls into view to avoid
    downloading thousands of images at once.
    """

    DEFAULT_CSS = """
    CoverArtItem {
        height: 3;
        width: 1fr;
        padding: 0;
    }

    CoverArtItem Horizontal {
        height: 100%;
        width: 1fr;
    }

    CoverArtItem .cover-image {
        width: 6;
        height: 3;
        min-width: 6;
        max-width: 6;
        hatch: cross $primary 30%;
    }

    CoverArtItem .cover-image.loaded {
        hatch: none;
    }

    CoverArtItem .cover-placeholder {
        width: 6;
        height: 3;
        min-width: 6;
        max-width: 6;
        content-align: center middle;
        color: $text-muted;
        hatch: cross $primary 30%;
    }

    CoverArtItem .item-text {
        width: 1fr;
        height: 100%;
        padding: 0 1;
        content-align: left middle;
    }
    """

    def __init__(
        self,
        text: str,
        cover_url: str | None = None,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize the cover art item.

        Args:
            text: The text to display
            cover_url: URL of the cover art image (optional)
            name: Widget name
            id: Widget ID
            classes: CSS classes
        """
        super().__init__(name=name, id=id, classes=classes)
        self._text = text
        self._cover_url = cover_url
        self._image_widget: Image | None = None
        self._image_loaded = False
        self._load_scheduled = False

    def compose(self) -> ComposeResult:
        """Compose the cover art item UI."""
        with Horizontal():
            if self._cover_url:
                # Create image widget - will be loaded lazily when visible
                self._image_widget = Image(classes="cover-image")
                yield self._image_widget
            else:
                # Placeholder when no cover art
                yield Label("[.]", classes="cover-placeholder")

            yield Label(self._text, classes="item-text")

    def on_show(self) -> None:
        """Called when the widget becomes visible - trigger lazy loading."""
        self._schedule_load()

    def _schedule_load(self) -> None:
        """Schedule image loading if not already done."""
        if (
            self._cover_url
            and self._image_widget
            and not self._image_loaded
            and not self._load_scheduled
        ):
            self._load_scheduled = True
            # Small delay to avoid loading during fast scrolling
            self.set_timer(0.1, self._trigger_load)

    def _trigger_load(self) -> None:
        """Trigger the actual image load."""
        if not self._image_loaded and self._cover_url and self._image_widget:
            self.run_worker(self._load_cover_art())

    async def _load_cover_art(self) -> None:
        """Load cover art image asynchronously."""
        if not self._cover_url or not self._image_widget or self._image_loaded:
            return

        try:
            cache = ImageCache()
            img = await cache.get_image(self._cover_url)
            if img and self._image_widget:
                self._image_widget.image = img
                self._image_widget.add_class("loaded")
                self._image_loaded = True
        except Exception as e:
            log(f"CoverArtItem: Failed to load cover art: {e}")

    def update_text(self, text: str) -> None:
        """Update the text label.

        Args:
            text: New text to display
        """
        self._text = text
        try:
            label = self.query_one(".item-text", Label)
            label.update(text)
        except Exception:
            pass
