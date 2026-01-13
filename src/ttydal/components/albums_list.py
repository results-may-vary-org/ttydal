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
        self.current_playing_item_id = None

    def compose(self) -> ComposeResult:
        """Compose the albums list UI."""
        yield Label("(a)lbums & playlists")
        yield ListView(id="albums-listview")

    def on_mount(self) -> None:
        """Load albums when mounted and auto-select My Tracks."""
        # Delay loading to ensure session is ready
        log("AlbumsList.on_mount() called - scheduling delayed load")
        self.set_timer(0.5, self.delayed_load)

    def delayed_load(self) -> None:
        """Load albums after a delay to ensure session is ready."""
        log("AlbumsList.delayed_load() called")
        # Run loading in a worker - exclusive=True prevents race conditions
        self.run_worker(self._load_albums_async(), exclusive=True)

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
        # Show loading in header
        header = self.query_one(Label)
        header.update("(a)lbums & playlists (loading...)")
        # Clear list immediately (synchronously) to prevent display issues
        list_view = self.query_one("#albums-listview", ListView)
        list_view.remove_children()
        self.albums = []
        log("  - Cleared albums list synchronously using remove_children()")
        # Run loading in a worker - exclusive=True prevents race conditions
        self.run_worker(self._load_albums_async(), exclusive=True)

    async def _load_albums_async(self) -> None:
        """Async worker to load albums without blocking UI."""
        log("AlbumsList._load_albums_async() called")

        # List already cleared synchronously before worker started
        # Add "My Tracks" as first item - get actual favorite track count
        list_view = self.query_one("#albums-listview", ListView)
        log("  - Getting favorite tracks count...")
        favorite_tracks = self.tidal.get_user_favorites()
        fav_count = len(favorite_tracks)
        log(f"  - Found {fav_count} favorite tracks")
        list_view.append(ListItem(Label(f"My Tracks ({fav_count} tracks)")))
        self.albums = [{"id": "favorites", "name": "My Tracks", "type": "favorites", "count": fav_count}]

        # Load user playlists
        log("  - Loading playlists...")
        user_playlists = self.tidal.get_user_playlists()
        for playlist in user_playlists:
            playlist_name = playlist.name
            # Get track count - check for None explicitly to handle 0 correctly
            track_count = getattr(playlist, 'num_tracks', None)
            if track_count is None:
                track_count = '?'
            display_name = f"{playlist_name} ({track_count} tracks)"
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
            # Get track count - check for None explicitly to handle 0 correctly
            track_count = getattr(album, 'num_tracks', None)
            if track_count is None:
                track_count = '?'
            display_name = f"{album_name} ({track_count} tracks)"
            list_view.append(ListItem(Label(display_name)))
            self.albums.append({
                "id": str(album.id),
                "name": album_name,
                "type": "album",
                "count": track_count
            })
        log(f"  - Loaded {len(user_albums)} albums")
        log(f"  - Total items in list: {len(self.albums)}")

        # Update header to remove loading text
        header = self.query_one(Label)
        header.update("(a)lbums & playlists")

        # Update visual indicators (in case we're reloading while something is playing)
        self._update_album_indicators()

        # Auto-select "My Tracks" after loading
        self.set_timer(0.1, self.auto_select_my_tracks)

    def set_playing_item(self, item_id: str) -> None:
        """Mark an album/playlist as currently playing.

        Args:
            item_id: The ID of the album/playlist that's currently playing
        """
        log(f"AlbumsList.set_playing_item({item_id}) called")
        self.current_playing_item_id = item_id
        self._update_album_indicators()

    def _update_album_indicators(self) -> None:
        """Update album list to show '>' indicator for currently playing album/playlist."""
        try:
            list_view = self.query_one("#albums-listview", ListView)
            for idx, list_item in enumerate(list_view.children):
                if idx < len(self.albums):
                    item = self.albums[idx]
                    item_name = item["name"]
                    item_type = item["type"]
                    item_count = item["count"]

                    # Add ">" prefix if this is the currently playing item
                    prefix = "> " if item["id"] == self.current_playing_item_id else "  "

                    # Format display based on type
                    if item_type == "favorites":
                        display_name = f"{prefix} {item_name} ({item_count} tracks)"
                    elif item_type == "playlist":
                        display_name = f"{prefix} {item_name} ({item_count} tracks)"
                    else:  # album
                        display_name = f"{prefix} {item_name} ({item_count} tracks)"

                    label = list_item.query_one(Label)
                    label.update(display_name)
        except Exception as e:
            log(f"  - Error updating album indicators: {e}")

    def action_refresh_albums(self) -> None:
        """Refresh the albums and playlists list (r key action)."""
        log("AlbumsList: Refresh albums action triggered")
        self.load_albums()

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

