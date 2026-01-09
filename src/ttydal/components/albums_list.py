"""Albums list component for browsing user albums and playlists."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import ListItem, ListView, Label
from textual.message import Message

from ttydal.tidal_client import TidalClient
from ttydal.logger import log


class AlbumsList(Container):
    """Albums list widget for browsing user albums."""

    BINDINGS = [
        Binding("r", "refresh_albums", "Refresh", show=True),
    ]

    DEFAULT_CSS = """
    AlbumsList {
        width: 1fr;
        height: 1fr;
        border: solid $accent;
    }

    AlbumsList:focus-within {
        border: solid $primary;
    }

    AlbumsList Label {
        background: $boost;
        width: 1fr;
        padding: 0 1;
    }

    AlbumsList ListView {
        height: 1fr;
    }
    """

    class AlbumSelected(Message):
        """Message sent when an album or playlist is selected."""

        def __init__(self, item_id: str, item_name: str, item_type: str) -> None:
            """Initialize album/playlist selected message.

            Args:
                item_id: The selected item ID
                item_name: The selected item name
                item_type: Type of item ('album', 'playlist', or 'favorites')
            """
            super().__init__()
            self.item_id = item_id
            self.item_name = item_name
            self.item_type = item_type

    def __init__(self):
        """Initialize the albums list."""
        super().__init__()
        self.tidal = TidalClient()
        self.albums = []

    def compose(self) -> ComposeResult:
        """Compose the albums list UI."""
        yield Label("Albums & Playlists")
        yield ListView(id="albums-listview")

    def on_mount(self) -> None:
        """Load albums when mounted and auto-select My Tracks."""
        # Delay loading to ensure session is ready
        log("AlbumsList.on_mount() called - scheduling delayed load")
        self.set_timer(0.5, self.delayed_load)

    def delayed_load(self) -> None:
        """Load albums after a delay to ensure session is ready."""
        log("AlbumsList.delayed_load() called")
        self.load_albums()
        # Auto-select "My Tracks" after loading
        self.set_timer(0.1, self.auto_select_my_tracks)

    def auto_select_my_tracks(self) -> None:
        """Auto-select My Tracks on startup."""
        log("AlbumsList: Auto-selecting My Tracks")
        list_view = self.query_one("#albums-listview", ListView)
        if len(self.albums) > 0:
            list_view.index = 0
            # Trigger selection event
            self.post_message(
                self.AlbumSelected(
                    self.albums[0]["id"],
                    self.albums[0]["name"],
                    self.albums[0]["type"]
                )
            )
            log("  - My Tracks auto-selected")

    def load_albums(self) -> None:
        """Load user albums and playlists from Tidal."""
        log("AlbumsList.load_albums() called")
        list_view = self.query_one("#albums-listview", ListView)
        list_view.clear()

        # Add "My Tracks" as first item
        list_view.append(ListItem(Label("My Tracks")))
        self.albums = [{"id": "favorites", "name": "My Tracks", "type": "favorites", "count": "?"}]

        # Load user playlists
        log("  - Loading playlists...")
        user_playlists = self.tidal.get_user_playlists()
        for playlist in user_playlists:
            playlist_name = playlist.name
            # Try to get track count from playlist object
            track_count = getattr(playlist, 'num_tracks', None) or getattr(playlist, 'numberOfTracks', None) or '?'
            display_name = f"🎵 {playlist_name} ({track_count} tracks)"
            list_view.append(ListItem(Label(display_name)))
            self.albums.append({
                "id": str(playlist.id),
                "name": playlist_name,
                "type": "playlist",
                "count": track_count
            })
        log(f"  - Loaded {len(user_playlists)} playlists")

        # Load user albums
        log("  - Loading albums...")
        user_albums = self.tidal.get_user_albums()
        for album in user_albums:
            album_name = album.name
            # Try to get track count from album object
            track_count = getattr(album, 'num_tracks', None) or getattr(album, 'numberOfTracks', None) or '?'
            display_name = f"💿 {album_name} ({track_count} tracks)"
            list_view.append(ListItem(Label(display_name)))
            self.albums.append({
                "id": str(album.id),
                "name": album_name,
                "type": "album",
                "count": track_count
            })
        log(f"  - Loaded {len(user_albums)} albums")
        log(f"  - Total items in list: {len(self.albums)}")

    def action_refresh_albums(self) -> None:
        """Refresh the albums and playlists list (r key action)."""
        log("AlbumsList: Refresh albums action triggered")
        self.load_albums()
        # Show notification
        self.app.notify("Albums & Playlists refreshed!", severity="information")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle album or playlist selection.

        Args:
            event: The selection event
        """
        if event.list_view.id == "albums-listview":
            index = event.list_view.index
            if index is not None and index < len(self.albums):
                item = self.albums[index]
                log(f"AlbumsList: Item selected - {item['name']} (type: {item['type']})")
                self.post_message(
                    self.AlbumSelected(item["id"], item["name"], item["type"])
                )
