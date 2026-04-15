"""Player page showing albums, tracks and playback controls."""

import asyncio

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal

from ttydal.components.player_bar import PlayerBar
from ttydal.components.albums_list import AlbumsList
from ttydal.components.tracks_list import TracksList
from ttydal.services.mpv_playback_engine import MpvPlaybackEngine
from ttydal.services.tidal_client import TidalClient
from ttydal.config import ConfigManager
from ttydal.services import PlaybackService
from ttydal.keybindings import get_key

_k = lambda action: get_key("player_page", action)


class PlayerPage(Container):
    """Player page containing all playback UI components."""

    BINDINGS = [
        Binding(_k("toggle_playback"), "toggle_playback", "Play/Pause", show=False),
    ]

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
        self.player = MpvPlaybackEngine()
        self.tidal = TidalClient()
        self.config = ConfigManager()
        self.playback_service = PlaybackService(self.tidal, self.player)

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

        from ttydal.services.mpris_service import MprisService

        self.mpris_service = MprisService(self.player)
        self.mpris_service.start()

        tracks_list = self.query_one(TracksList)
        self.mpris_service.set_navigation_callbacks(
            on_next=tracks_list.play_next_track,
            on_prev=tracks_list.play_previous_track,
        )

    def on_albums_list_album_selected(self, event: AlbumsList.AlbumSelected) -> None:
        """Handle album or playlist selection.

        Args:
            event: Album/playlist selection event
        """
        tracks_list = self.query_one(TracksList)
        tracks_list.load_tracks(event.item_id, event.item_name, event.item_type)

    async def on_tracks_list_track_selected(self, event: TracksList.TrackSelected) -> None:
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
        if event.prefetched_url:
            log("  - Has pre-fetched URL: Yes")

        if event.prefetched_url:
            # Fast path: URL already available, no HTTP needed.
            result = self.playback_service.play_track(
                event.track_id,
                event.track_info,
                self.config.quality,
                fetch_vibrant_color=self.config.vibrant_color,
                prefetched_url=event.prefetched_url,
                prefetched_metadata=event.prefetched_metadata,
                prefetched_error_info=event.prefetched_error_info,
            )
        else:
            # Slow path: must fetch the URL from Tidal — blocking HTTP call.
            # Run in a thread so the event loop stays responsive if the network is down.
            log("  - No pre-fetched URL, fetching from Tidal (in thread)…")
            player_bar = self.query_one(PlayerBar)
            fetch_future = asyncio.get_running_loop().run_in_executor(
                None,
                lambda: self.playback_service.play_track(
                    event.track_id,
                    event.track_info,
                    self.config.quality,
                    fetch_vibrant_color=self.config.vibrant_color,
                ),
            )
            indicator_shown = False
            try:
                # Fast check: if the fetch finishes within 3 s, no indicator needed.
                result = await asyncio.wait_for(asyncio.shield(fetch_future), timeout=3.0)
            except asyncio.TimeoutError:
                # Still waiting — likely a network hiccup. Show the reconnecting notice.
                player_bar.set_reconnecting(True)
                indicator_shown = True
                try:
                    result = await asyncio.wait_for(fetch_future, timeout=12.0)
                except asyncio.TimeoutError:
                    player_bar.set_reconnecting(False)
                    track_name = event.track_info.get("name", "Track")
                    log(f"  - play_track timed out for '{track_name}'")
                    self.app.notify(
                        f"Failed to load '{track_name}': network timeout",
                        severity="error",
                        timeout=10,
                    )
                    log("=" * 80)
                    return
            if indicator_shown:
                if result.success:
                    player_bar.set_reconnected()
                else:
                    player_bar.set_reconnecting(False)

        if result.success:
            # Notify MPRIS so playerctl / system widgets update immediately
            if hasattr(self, "mpris_service"):
                self.mpris_service.notify_track_changed()

            # Update player bar with actual stream quality and cover art
            player_bar = self.query_one(PlayerBar)
            player_bar.update_stream_quality(result.stream_metadata)

            # Update cover art
            cover_url = event.track_info.get("cover_url")
            player_bar.update_cover_art(cover_url)

            # Update vibrant color if enabled
            if self.config.vibrant_color and result.vibrant_color:
                player_bar.update_vibrant_color(result.vibrant_color)
            else:
                player_bar.update_vibrant_color(None)

            # Update album list to show which album/playlist is currently playing
            tracks_list = self.query_one(TracksList)
            playing_item_id = tracks_list._active_playlist_item_id or tracks_list.current_item_id
            if playing_item_id:
                log(
                    f"  - Updating album indicator for item: {playing_item_id}"
                )
                albums_list = self.query_one(AlbumsList)
                albums_list.set_playing_item(playing_item_id)

            # Show notification if quality fallback was applied
            if result.fallback_applied:
                requested = (result.requested_quality or "").upper()
                actual = (result.actual_quality or "").upper()
                track_name = event.track_info.get("name", "Track")
                self.app.notify(
                    f"{track_name}: Not available at {requested} quality, playing at {actual}",
                    severity="warning",
                    timeout=5,
                )
            log("=" * 80)
        else:
            log("  - Failed to get track URL or metadata")

            track_name = event.track_info.get("name", "Track")
            error_msg = result.error_message or "Unknown error"

            # "Not logged in" means is_logged_in() failed — the network is down, not a
            # real logout. Start the retry loop instead of showing a hard error.
            if result.error_message == "Not logged in":
                log("  - Network down (not logged in) — scheduling playback retry…")
                tracks_list = self.query_one(TracksList)
                tracks_list.start_playback_retry(event.track_id, event.track_info)
                log("=" * 80)
                return

            tried_qualities = result.tried_qualities or []
            if tried_qualities:
                qualities_str = ", ".join([q.upper() for q in tried_qualities])
                notification_msg = f"Failed to play '{track_name}': {error_msg} (tried: {qualities_str})"
            else:
                notification_msg = f"Failed to play '{track_name}': {error_msg}"

            self.app.notify(notification_msg, severity="error", timeout=10)
            log("=" * 80)

    def focus_albums(self) -> None:
        """Focus the albums list and select first album if none selected."""
        albums_list = self.query_one(AlbumsList)
        list_view = albums_list.query_one("#albums-listview")
        list_view.focus()
        if list_view.index is None and albums_list.albums:
            list_view.index = 0

    def focus_tracks(self) -> None:
        """Focus the tracks list and select first track."""
        tracks_list = self.query_one(TracksList)
        list_view = tracks_list.query_one("#tracks-listview")
        list_view.focus()
        if tracks_list.tracks and list_view.index is None:
            list_view.index = 0

    def action_toggle_playback(self) -> None:
        """Toggle play/pause (spacebar action at PlayerPage level)."""
        from ttydal.logger import log

        log("PlayerPage.action_toggle_playback() called")
        self.player.toggle_pause()

    def toggle_playback(self) -> None:
        """Toggle play/pause (called from app level)."""
        from ttydal.logger import log

        log("PlayerPage.toggle_playback() called")
        self.player.toggle_pause()

    def seek_backward(self) -> None:
        """Seek backward 10 seconds."""
        self.player.seek(-10)

    def seek_forward(self) -> None:
        """Seek forward 10 seconds."""
        self.player.seek(10)

    def play_next(self) -> None:
        """Play next track."""
        tracks_list = self.query_one(TracksList)
        tracks_list.play_next_track()

    def play_previous(self) -> None:
        """Play previous track."""
        tracks_list = self.query_one(TracksList)
        tracks_list.play_previous_track()

    def on_shuffle_changed(self, enabled: bool) -> None:
        """Handle shuffle setting change.

        Args:
            enabled: Whether shuffle is now enabled
        """
        tracks_list = self.query_one(TracksList)
        tracks_list.on_shuffle_changed(enabled)
