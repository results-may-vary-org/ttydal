"""Albums list component for browsing user albums and playlists.

Note: We don't cache the albums list because:
1. Users rarely reload it after initial load
2. It's a small dataset that loads quickly
3. Changes to favorites/playlists should reflect immediately
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import ListItem, ListView, Label
from textual.message import Message

from ttydal.tidal_client import TidalClient
from ttydal.services import AlbumsService, TracksService, TidalServiceError
from ttydal.services.tracks_cache import TracksCache
from ttydal.logger import log
from ttydal.components.cover_art_item import CoverArtItem


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

    AlbumsList.loading #albums-listview {
        hatch: cross $primary 40%;
    }

    AlbumsList:focus-within {
        border: solid $primary;
    }

    AlbumsList > Label {
        background: $boost;
        width: 1fr;
        padding: 0 1;
    }

    AlbumsList ListView {
        height: 1fr;
    }

    AlbumsList ListItem {
        height: 3;
    }

    AlbumsList ListItem:odd {
        background: $boost;
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
        tidal_client = TidalClient()
        self.albums_service = AlbumsService(tidal_client)
        self.tracks_service = TracksService(tidal_client)
        self.albums = []
        self.current_playing_item_id = None
        self._is_initial_load = True
        self._saved_selection_id = None  # For restoring selection after refresh
        self._preload_in_progress = False
        self._trigger_preload_after_refresh = False

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
        # This is the initial load, so auto-select My Tracks afterwards
        self._is_initial_load = True
        # Add loading class for visual feedback
        self.add_class("loading")
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
                    self.albums[0]["id"], self.albums[0]["name"], self.albums[0]["type"]
                )
            )
            log("  - My Tracks auto-selected")

    def _restore_selection(self) -> None:
        """Restore the previously selected album/playlist after refresh."""
        log(f"AlbumsList: Restoring selection to {self._saved_selection_id}")
        if self._saved_selection_id is None:
            return

        list_view = self.query_one("#albums-listview", ListView)
        # Find the index of the saved selection
        for idx, album in enumerate(self.albums):
            if album["id"] == self._saved_selection_id:
                list_view.index = idx
                log(f"  - Selection restored to index {idx}")
                return
        log("  - Could not find saved selection, keeping current position")

    def _start_preload(self) -> None:
        """Start background preloading of all tracks."""
        if self._preload_in_progress:
            return
        self._preload_in_progress = True
        log("AlbumsList: Starting background preload of all tracks")
        self.run_worker(self._preload_all_tracks_async(), exclusive=False)

    async def _preload_all_tracks_async(self) -> None:
        """Background worker to preload tracks for all albums into cache."""
        cache = TracksCache()
        total_loaded = 0
        albums_to_load = list(
            self.albums
        )  # Copy to avoid modification during iteration

        log(f"AlbumsList: Preloading tracks for {len(albums_to_load)} albums")

        for album in albums_to_load:
            item_id = album["id"]
            item_type = album["type"]

            # Skip if already cached
            if cache.get(item_id) is not None:
                log(f"  - {album['name']}: already cached, skipping")
                continue

            try:
                if item_type == "favorites":
                    tracks = await self.tracks_service.get_favorites_tracks()
                elif item_type == "playlist":
                    tracks = await self.tracks_service.get_playlist_tracks(item_id)
                else:  # album
                    tracks = await self.tracks_service.get_album_tracks(item_id)

                cache.set(item_id, tracks)
                total_loaded += len(tracks)
                log(f"  - {album['name']}: cached {len(tracks)} tracks")
            except Exception as e:
                log(f"  - {album['name']}: error loading tracks: {e}")

        self._preload_in_progress = False
        stats = cache.get_stats()
        log(
            f"AlbumsList: Preload complete - {stats['tracks_count']} tracks "
            f"from {stats['albums_count']} albums"
        )

    def load_albums(self) -> None:
        """Load user albums and playlists from Tidal."""
        log("AlbumsList.load_albums() called")
        # This is a refresh, not initial load - preserve current selection
        self._is_initial_load = False
        # Save the current selection to restore after refresh
        list_view = self.query_one("#albums-listview", ListView)
        current_index = list_view.index
        if current_index is not None and current_index < len(self.albums):
            self._saved_selection_id = self.albums[current_index]["id"]
            log(f"  - Saved current selection: {self._saved_selection_id}")
        else:
            self._saved_selection_id = None
        # Add loading class for visual feedback
        self.add_class("loading")
        # Show loading in header
        header = self.query_one(Label)
        header.update("(a)lbums & playlists (loading...)")
        # Clear list immediately (synchronously) to prevent display issues
        list_view.remove_children()
        self.albums = []
        log("  - Cleared albums list synchronously using remove_children()")
        # Run loading in a worker - exclusive=True prevents race conditions
        self.run_worker(self._load_albums_async(), exclusive=True)

    async def _load_albums_async(self) -> None:
        """Async worker to load albums without blocking UI."""
        log("AlbumsList._load_albums_async() called")

        try:
            # List already cleared synchronously before worker started
            # Add "My Tracks" as first item - get actual favorite track count
            list_view = self.query_one("#albums-listview", ListView)
            log("  - Getting favorite tracks count...")
            favorites_info = await self.albums_service.get_favorites_info()
            fav_count = favorites_info["count"]
            log(f"  - Found {fav_count} favorite tracks")
            list_view.append(
                ListItem(
                    CoverArtItem(
                        f"My Tracks ({fav_count} tracks)",
                        cover_url=None,  # Favorites has no cover
                    )
                )
            )
            self.albums = [
                {
                    "id": "favorites",
                    "name": "My Tracks",
                    "type": "favorites",
                    "count": fav_count,
                    "cover_url": None,
                }
            ]

            # Load user playlists
            log("  - Loading playlists...")
            user_playlists = await self.albums_service.get_user_playlists()
            for playlist in user_playlists:
                playlist_name = playlist["name"]
                # Get track count - check for None explicitly to handle 0 correctly
                track_count = playlist.get("count")
                if track_count is None:
                    track_count = "?"
                cover_url = playlist.get("cover_url")
                display_name = f"{playlist_name} ({track_count} tracks)"
                list_view.append(
                    ListItem(CoverArtItem(display_name, cover_url=cover_url))
                )
                self.albums.append(
                    {
                        "id": str(playlist["id"]),
                        "name": playlist_name,
                        "type": "playlist",
                        "count": track_count,
                        "cover_url": cover_url,
                    }
                )
            log(f"  - Loaded {len(user_playlists)} playlists")

            # Load user albums
            log("  - Loading albums...")
            user_albums = await self.albums_service.get_user_albums()
            for album in user_albums:
                album_name = album["name"]
                # Get track count - check for None explicitly to handle 0 correctly
                track_count = album.get("count")
                if track_count is None:
                    track_count = "?"
                cover_url = album.get("cover_url")
                display_name = f"{album_name} ({track_count} tracks)"
                list_view.append(
                    ListItem(CoverArtItem(display_name, cover_url=cover_url))
                )
                self.albums.append(
                    {
                        "id": str(album["id"]),
                        "name": album_name,
                        "type": "album",
                        "count": track_count,
                        "cover_url": cover_url,
                    }
                )
            log(f"  - Loaded {len(user_albums)} albums")
            log(f"  - Total items in list: {len(self.albums)}")

            # Update header to remove loading text
            header = self.query_one(Label)
            header.update("(a)lbums & playlists")

            # Update visual indicators (in case we're reloading while something is playing)
            self._update_album_indicators()

            # Auto-select "My Tracks" only on initial load, restore selection on refresh
            if self._is_initial_load:
                self.set_timer(0.1, self.auto_select_my_tracks)
                # Start background preloading of all tracks for cache
                self.set_timer(0.5, self._start_preload)
            else:
                self.set_timer(0.1, self._restore_selection)
                # Re-preload all tracks after refresh if requested
                if self._trigger_preload_after_refresh:
                    self._trigger_preload_after_refresh = False
                    self.set_timer(0.5, self._start_preload)
        except TidalServiceError as e:
            log(f"AlbumsList: Service error loading albums: {e}")
            header = self.query_one(Label)
            header.update("(a)lbums & playlists (error)")
            self.app.notify(e.user_message, severity="error", timeout=5)
        finally:
            # Remove loading class when done (success or error)
            self.remove_class("loading")

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
                    item_count = item["count"]

                    # Add ">" prefix if this is the currently playing item
                    prefix = (
                        "> " if item["id"] == self.current_playing_item_id else "  "
                    )

                    # Format display (same for all types)
                    display_name = f"{prefix} {item_name} ({item_count} tracks)"

                    # Update the CoverArtItem text
                    try:
                        cover_art_item = list_item.query_one(CoverArtItem)
                        cover_art_item.update_text(display_name)
                    except Exception:
                        # Fallback to Label for backwards compatibility
                        try:
                            label = list_item.query_one(Label)
                            label.update(display_name)
                        except Exception:
                            pass
        except Exception as e:
            log(f"  - Error updating album indicators: {e}")

    def action_refresh_albums(self) -> None:
        """Refresh the albums and playlists list (r key action).

        This clears the tracks cache, reloads albums, and re-preloads all tracks.
        """
        log("AlbumsList: Refresh albums action triggered")
        # Clear the entire tracks cache when refreshing albums
        TracksCache().clear()
        log("  - Cleared tracks cache")
        # Reset preload flag so it will run again after albums load
        self._preload_in_progress = False
        self._trigger_preload_after_refresh = True
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
                log(
                    f"AlbumsList: Item selected - {item['name']} (type: {item['type']})"
                )
                self.post_message(
                    self.AlbumSelected(item["id"], item["name"], item["type"])
                )
