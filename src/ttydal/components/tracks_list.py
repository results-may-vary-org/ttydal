"""Tracks list component for browsing and playing tracks."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import ListItem, ListView, Label
from textual.message import Message

from ttydal.tidal_client import TidalClient
from ttydal.logger import log


class TracksList(Container):
    """Tracks list widget for browsing and selecting tracks."""

    BINDINGS = [
        Binding("space", "play_selected_track", "Play/Pause", show=True, priority=True),
        Binding("r", "refresh_tracks", "Refresh", show=True),
    ]

    DEFAULT_CSS = """
    TracksList {
        width: 1fr;
        height: 1fr;
        border: solid $accent;
    }

    TracksList:focus-within {
        border: solid $primary;
    }

    TracksList Label {
        background: $boost;
        width: 1fr;
        padding: 0 1;
    }

    TracksList ListView {
        height: 1fr;
    }
    """

    class TrackSelected(Message):
        """Message sent when a track is selected."""

        def __init__(self, track_id: str, track_info: dict) -> None:
            """Initialize track selected message.

            Args:
                track_id: The selected track ID
                track_info: Track metadata
            """
            super().__init__()
            self.track_id = track_id
            self.track_info = track_info

    def __init__(self):
        """Initialize the tracks list."""
        super().__init__()
        self.tidal = TidalClient()
        self.tracks = []
        self.current_album_name = ""
        self.current_item_id = None
        self.current_item_type = None

    def compose(self) -> ComposeResult:
        """Compose the tracks list UI."""
        yield Label("Tracks")
        yield ListView(id="tracks-listview")

    def load_tracks(self, item_id: str, item_name: str, item_type: str = "album") -> None:
        """Load ALL tracks for a specific album or playlist.

        Args:
            item_id: The item ID to load tracks from
            item_name: The item name for display
            item_type: Type of item ('album', 'playlist', or 'favorites')
        """
        log(f"TracksList.load_tracks({item_id}, {item_name}, {item_type}) called")
        self.current_album_name = item_name
        self.current_item_id = item_id
        self.current_item_type = item_type

        # Update header to show loading
        header = self.query_one(Label)
        header.update(f"Tracks - {item_name} (Loading...)")

        # Clear the list and start loading in a worker
        list_view = self.query_one("#tracks-listview", ListView)
        list_view.clear()
        self.tracks = []

        # Run the loading in a worker so UI can update
        self.run_worker(self._load_tracks_async(item_id, item_name, item_type), exclusive=False)

    async def _load_tracks_async(self, item_id: str, item_name: str, item_type: str) -> None:
        """Async worker to load tracks without blocking UI.

        Args:
            item_id: The item ID to load tracks from
            item_name: The item name for display
            item_type: Type of item ('album', 'playlist', or 'favorites')
        """
        # Load tracks based on item type
        log(f"  - Loading tracks for type: {item_type}")
        if item_type == "favorites":
            # Load favorite tracks
            tracks_list = self.tidal.get_user_favorites()
        elif item_type == "playlist":
            # Load playlist tracks
            tracks_list = self.tidal.get_playlist_tracks(item_id)
        else:  # album
            # Load album tracks
            tracks_list = self.tidal.get_album_tracks(item_id)

        log(f"  - Retrieved {len(tracks_list)} tracks")

        # Populate ALL tracks
        list_view = self.query_one("#tracks-listview", ListView)
        for idx, track in enumerate(tracks_list, 1):
            track_name = track.name
            artist = track.artist.name if hasattr(track, 'artist') else "Unknown"
            duration = self._format_duration(track.duration)

            list_view.append(
                ListItem(Label(f"{idx}. {track_name} - {artist} ({duration})"))
            )
            self.tracks.append({
                "id": str(track.id),
                "name": track_name,
                "artist": artist,
                "duration": track.duration
            })

        log(f"  - Populated {len(self.tracks)} tracks in UI")

        # Update header to remove loading text
        header = self.query_one(Label)
        header.update(f"Tracks - {item_name}")

    def _format_duration(self, seconds: int) -> str:
        """Format duration in seconds to MM:SS.

        Args:
            seconds: Duration in seconds

        Returns:
            Formatted duration string
        """
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}:{secs:02d}"

    def action_play_selected_track(self) -> None:
        """Play the currently selected track or toggle pause (space key action).

        Behavior:
        - If no track selected: do nothing
        - If selected track is different from playing track: play selected track
        - If selected track is same as playing track: toggle pause
        - If no track is playing: play selected track
        """
        log("TracksList: Space key action triggered")
        list_view = self.query_one("#tracks-listview", ListView)
        index = list_view.index

        if index is None or index >= len(self.tracks):
            log("  - No track selected, toggling pause/play")
            # No track selected, toggle pause on whatever is playing
            from ttydal.player import Player
            player = Player()
            player.toggle_pause()
            return

        selected_track = self.tracks[index]
        log(f"  - Selected track: {selected_track['name']} (ID: {selected_track['id']})")

        # Get currently playing track
        from ttydal.player import Player
        player = Player()
        current_track = player.get_current_track()

        if current_track and current_track.get('id') == selected_track['id']:
            # Same track is selected and playing, toggle pause
            log(f"  - Same track already playing, toggling pause")
            player.toggle_pause()
        else:
            # Different track or no track playing, play the selected track
            if current_track:
                log(f"  - Different track selected (current: {current_track.get('name', 'Unknown')}), playing new track")
            else:
                log(f"  - No track playing, starting playback")
            self.post_message(
                self.TrackSelected(selected_track["id"], selected_track)
            )

    def action_refresh_tracks(self) -> None:
        """Refresh the current tracks list (r key action)."""
        log("TracksList: Refresh tracks action triggered")
        if self.current_item_id and self.current_item_type:
            log(f"  - Reloading tracks for {self.current_album_name}")
            self.load_tracks(
                self.current_item_id,
                self.current_album_name,
                self.current_item_type
            )
        else:
            log("  - No tracks loaded yet, nothing to refresh")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle track selection (Enter key or double-click).

        Always plays the selected track, even if it's already playing.

        Args:
            event: The selection event
        """
        if event.list_view.id == "tracks-listview":
            index = event.list_view.index
            if index is not None and index < len(self.tracks):
                track = self.tracks[index]
                log(f"TracksList: Track selected via Enter/click - {track['name']}")
                log(f"  - Playing/restarting track")
                self.post_message(
                    self.TrackSelected(track["id"], track)
                )
