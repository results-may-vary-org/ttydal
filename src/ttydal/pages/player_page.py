"""Player page showing albums, tracks and playback controls."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal

from ttydal.components.player_bar import PlayerBar
from ttydal.components.albums_list import AlbumsList
from ttydal.components.tracks_list import TracksList
from ttydal.player import Player
from ttydal.tidal_client import TidalClient
from ttydal.config import ConfigManager


class PlayerPage(Container):
    """Player page containing all playback UI components."""

    DEFAULT_CSS = """
    PlayerPage {
        width: 1fr;
        height: 1fr;
    }

    PlayerPage Horizontal {
        width: 1fr;
        height: 1fr;
    }
    """

    def __init__(self):
        """Initialize the player page."""
        super().__init__()
        self.player = Player()
        self.tidal = TidalClient()
        self.config = ConfigManager()

    def compose(self) -> ComposeResult:
        """Compose the player page UI."""
        yield PlayerBar()
        with Horizontal():
            yield AlbumsList()
            yield TracksList()

    def on_mount(self) -> None:
        """Initialize page when mounted."""
        player_bar = self.query_one(PlayerBar)
        player_bar.update_quality_display(self.config.quality)

    def on_albums_list_album_selected(
        self, event: AlbumsList.AlbumSelected
    ) -> None:
        """Handle album or playlist selection.

        Args:
            event: Album/playlist selection event
        """
        tracks_list = self.query_one(TracksList)
        tracks_list.load_tracks(event.item_id, event.item_name, event.item_type)

    def on_tracks_list_track_selected(
        self, event: TracksList.TrackSelected
    ) -> None:
        """Handle track selection and start playback.

        Args:
            event: Track selection event
        """
        from ttydal.logger import log
        log("=" * 80)
        log("PlayerPage.on_tracks_list_track_selected() - Message received")
        log(f"  - Track: {event.track_info.get('name', 'Unknown')}")
        log(f"  - Track ID: {event.track_id}")
        log(f"  - Artist: {event.track_info.get('artist', 'Unknown')}")

        log("  - Requesting track URL and metadata from Tidal...")
        track_url, stream_metadata = self.tidal.get_track_url(
            event.track_id,
            self.config.quality
        )

        if track_url and stream_metadata:
            log(f"  - Got track URL, calling player.play()")

            # Add stream metadata to track info
            track_info_with_metadata = event.track_info.copy()
            track_info_with_metadata['stream_metadata'] = stream_metadata

            self.player.play(track_url, track_info_with_metadata)

            # Update player bar with actual stream quality
            player_bar = self.query_one(PlayerBar)
            player_bar.update_stream_quality(stream_metadata)

            # Update album list to show which album/playlist is currently playing
            tracks_list = self.query_one(TracksList)
            if tracks_list.current_item_id:
                log(f"  - Updating album indicator for item: {tracks_list.current_item_id}")
                albums_list = self.query_one(AlbumsList)
                albums_list.set_playing_item(tracks_list.current_item_id)
            log("=" * 80)
        else:
            log(f"  - Failed to get track URL or metadata")
            log("=" * 80)

    def focus_albums(self) -> None:
        """Focus the albums list."""
        albums_list = self.query_one(AlbumsList)
        list_view = albums_list.query_one("#albums-listview")
        list_view.focus()

    def focus_tracks(self) -> None:
        """Focus the tracks list."""
        tracks_list = self.query_one(TracksList)
        list_view = tracks_list.query_one("#tracks-listview")
        list_view.focus()

    def toggle_playback(self) -> None:
        """Toggle play/pause."""
        from ttydal.logger import log
        log("PlayerPage.toggle_playback() called")
        self.player.toggle_pause()

    def seek_backward(self) -> None:
        """Seek backward 10 seconds."""
        self.player.seek(-10)

    def seek_forward(self) -> None:
        """Seek forward 10 seconds."""
        self.player.seek(10)
