"""Large cover art view modal."""

import re

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Static
from textual_image.widget import Image

from ttydal.services.image_cache import ImageCache
from ttydal.logger import log


class CoverArtModal(ModalScreen):
    """Modal that shows a large version of the current track's cover art.

    Dismissed by pressing Escape, Space, or clicking anywhere.
    """

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("space", "dismiss", "Close"),
    ]

    CSS = """
    CoverArtModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.88);
    }

    #cover-modal-inner {
        width: auto;
        height: auto;
        padding: 1;
        background: transparent;
    }

    #cover-modal-inner Image {
        width: 48;
        height: 24;
    }

    #cover-modal-placeholder {
        width: 48;
        height: 24;
        content-align: center middle;
        color: $text-muted;
    }
    """

    def __init__(self, cover_url: str) -> None:
        super().__init__()
        self._cover_url = cover_url
        self._image_widget: Image | None = None

    def compose(self) -> ComposeResult:
        with Container(id="cover-modal-inner"):
            yield Static("Loading…", id="cover-modal-placeholder")

    def on_mount(self) -> None:
        self.run_worker(self._load_image())

    async def _load_image(self) -> None:
        try:
            cache = ImageCache()
            # Request a larger image than the player bar (640x640 vs 320x320)
            large_url = re.sub(r"/\d+x\d+", "/640x640", self._cover_url)
            log(f"CoverArtModal: Loading {large_url}")
            img = await cache.get_image(large_url)
            if img:
                container = self.query_one("#cover-modal-inner")
                container.query_one("#cover-modal-placeholder").remove()
                self._image_widget = Image(img)
                container.mount(self._image_widget)
            else:
                log("CoverArtModal: Failed to load image")
        except Exception as e:
            log(f"CoverArtModal: Error loading image: {e}")

    def on_click(self) -> None:
        """Close the modal on any click."""
        self.dismiss(None)
