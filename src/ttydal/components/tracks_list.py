"""Tracks list component for browsing and playing tracks."""

import asyncio
import random

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import ListItem, ListView, Label
from textual.message import Message

from ttydal.services.tidal_client import TidalClient
from ttydal.services import TracksService, TidalServiceError
from ttydal.services.tracks_cache import TracksCache
from ttydal.logger import log
from ttydal.components.cover_art_item import CoverArtItem
from ttydal.keybindings import get_key

_k = lambda action: get_key("tracks_list", action)
_nav = lambda action: get_key("navigation", action)


# Pre-fetch next track URL this many seconds before current track ends
PREFETCH_SECONDS_BEFORE_END = 15


class TracksList(Container):
    """Tracks list widget for browsing and selecting tracks."""

    BINDINGS = [
        Binding(_k("play_selected_track"), "play_selected_track", "Play Track", show=True),
        Binding(_k("refresh_tracks"), "refresh_tracks", "Refresh", show=True),
        Binding(_k("show_art"), "show_art", "Art", show=True),
        Binding(_nav("cursor_down"), "cursor_down", "Down", show=False),
        Binding(_nav("cursor_up"), "cursor_up", "Up", show=False),
        Binding(_nav("cursor_left"), "focus_albums", "Albums", show=False),
    ]

    DEFAULT_CSS = """
    TracksList {
        width: 1fr;
        height: 1fr;
        border: solid $accent;
    }

    TracksList.loading #tracks-listview {
        hatch: cross $primary 40%;
    }

    TracksList:focus-within {
        border: solid $primary;
    }

    TracksList > Label {
        background: $boost;
        width: 1fr;
        padding: 0 1;
    }

    TracksList ListView {
        height: 1fr;
    }

    TracksList ListItem {
        height: 3;
    }

    TracksList ListItem:odd {
        background: $boost;
    }

    TracksList.no-stripes ListItem:odd {
        background: transparent;
    }
    """

    class TrackSelected(Message):
        """Message sent when a track is selected."""

        def __init__(
            self,
            track_id: str,
            track_info: dict,
            prefetched_url: str | None = None,
            prefetched_metadata: dict | None = None,
            prefetched_error_info: dict | None = None,
        ) -> None:
            """Initialize track selected message.

            Args:
                track_id: The selected track ID
                track_info: Track metadata
                prefetched_url: Pre-fetched stream URL (optional, skips API call)
                prefetched_metadata: Pre-fetched stream metadata (optional)
                prefetched_error_info: Pre-fetched error info dict (optional)
            """
            super().__init__()
            self.track_id = track_id
            self.track_info = track_info
            self.prefetched_url = prefetched_url
            self.prefetched_metadata = prefetched_metadata
            self.prefetched_error_info = prefetched_error_info

    def __init__(self):
        """Initialize the tracks list."""
        super().__init__()
        self.tracks_service = TracksService(TidalClient())
        self.tracks = []
        self.current_album_name = ""
        self.current_item_id = None
        self.current_item_type = None
        self.current_playing_index = None
        self._playing_item_id = None  # Album/playlist ID of the currently PLAYING track
        self._track_end_callback_registered = False
        # Shuffle state
        self.shuffled_indices: list[int] = []  # Shuffled order of track indices
        self.shuffle_position: int = 0  # Current position in the shuffled order
        # Active playback playlist (snapshot of tracks when a track was explicitly started)
        self._active_playlist: list = []
        self._active_playlist_item_id: str | None = None
        # Pre-fetch state for next track
        self._prefetched_track_id: str | None = None
        self._prefetched_url: str | None = None
        self._prefetched_metadata: dict | None = None
        self._prefetched_error_info: dict | None = None
        self._prefetch_in_progress: bool = False
        # Stream recovery state
        self._stream_recovery_in_progress: bool = False

    def compose(self) -> ComposeResult:
        """Compose the tracks list UI."""
        yield Label("(t)racks")
        yield ListView(id="tracks-listview")

    def on_mount(self) -> None:
        """Initialize when mounted."""
        from ttydal.config import ConfigManager

        if not ConfigManager().list_striping:
            self.add_class("no-stripes")

        # Register callbacks for track end and time position events
        if not self._track_end_callback_registered:
            from ttydal.services.mpv_playback_engine import MpvPlaybackEngine

            player = MpvPlaybackEngine()
            player.register_callback("on_track_end", self._on_track_end)
            player.register_callback("on_time_pos_change", self._on_time_pos_change)
            player.register_callback("on_stream_error", self._on_stream_error)
            self._track_end_callback_registered = True
            log("TracksList: Registered track end, time position, and stream error callbacks")

    def _on_track_end(self) -> None:
        """Handle track end - play next track if auto-play is enabled."""
        log("=" * 80)
        log("TracksList: Auto-play callback triggered")

        # Check if auto-play is enabled
        from ttydal.config import ConfigManager

        config = ConfigManager()
        if not config.auto_play:
            log("  - Auto-play disabled, doing nothing")
            log("=" * 80)
            return

        # Verify we have an active playlist and a current position
        if self.current_playing_index is None or not self._active_playlist:
            log("  - No active playlist or index, cannot auto-play")
            log("=" * 80)
            return

        # Get next track index (respects shuffle mode)
        next_index = self._get_next_track_index()
        next_track = self._active_playlist[next_index]
        log(
            f"  - Playing next: {next_track['name']} (index {next_index}/{len(self._active_playlist) - 1})"
        )

        # Update state
        self.current_playing_index = next_index
        self._playing_item_id = self._active_playlist_item_id

        # DOM mutations must run on the Textual event-loop thread, not on the mpv
        # callback thread that calls _on_track_end.
        try:
            self.app.call_from_thread(self._update_ui_after_track_end, next_index)
        except Exception as e:
            log(f"  - Error scheduling UI update: {e}")

        # Check if we have pre-fetched data for this track
        prefetched_url = None
        prefetched_metadata = None
        prefetched_error_info = None
        if self._prefetched_track_id == next_track["id"]:
            log("  - Using pre-fetched URL for next track")
            prefetched_url = self._prefetched_url
            prefetched_metadata = self._prefetched_metadata
            prefetched_error_info = self._prefetched_error_info
        else:
            log("  - No pre-fetched data available (will fetch on demand)")

        # Clear pre-fetch state
        self._clear_prefetch_state()

        # Trigger playback with pre-fetched data if available
        self.post_message(
            self.TrackSelected(
                next_track["id"],
                next_track,
                prefetched_url=prefetched_url,
                prefetched_metadata=prefetched_metadata,
                prefetched_error_info=prefetched_error_info,
            )
        )
        log("=" * 80)

    def _update_ui_after_track_end(self, next_index: int) -> None:
        """Update list cursor and indicators after auto-play advances.

        Must be called on the Textual event-loop thread (via call_from_thread).
        """
        try:
            if self.current_item_id == self._active_playlist_item_id:
                list_view = self.query_one("#tracks-listview", ListView)
                list_view.index = next_index
            self._update_track_indicators()
        except Exception as e:
            log(f"  - UI update error: {e}")

    def _on_time_pos_change(self, time_pos: float) -> None:
        """Handle playback time position changes for pre-fetching next track.

        Args:
            time_pos: Current playback position in seconds
        """
        # Skip if already pre-fetched or pre-fetch in progress
        if self._prefetched_track_id is not None or self._prefetch_in_progress:
            return

        # Skip if no active playlist or not playing
        if self.current_playing_index is None or not self._active_playlist:
            return

        # Check if auto-play is enabled (no point pre-fetching if disabled)
        from ttydal.config import ConfigManager

        config = ConfigManager()
        if not config.auto_play:
            return

        # Get track duration from player
        from ttydal.services.mpv_playback_engine import MpvPlaybackEngine

        player = MpvPlaybackEngine()
        duration = player.get_duration()

        # Skip if duration unknown or track too short
        if duration <= 0 or duration < PREFETCH_SECONDS_BEFORE_END + 5:
            return

        # Check if we're within pre-fetch window
        time_remaining = duration - time_pos
        if time_remaining <= PREFETCH_SECONDS_BEFORE_END and time_remaining > 0:
            # run_worker must be called from the Textual event-loop thread, not from
            # the mpv callback thread that calls _on_time_pos_change.
            self._prefetch_in_progress = True
            log(
                f"TracksList: Starting pre-fetch ({time_remaining:.1f}s before track end)"
            )
            try:
                self.app.call_from_thread(
                    self._start_prefetch_worker, config.quality
                )
            except Exception as e:
                log(f"TracksList: Error scheduling pre-fetch: {e}")
                self._prefetch_in_progress = False

    async def _prefetch_next_track(self, quality: str) -> None:
        """Pre-fetch the next track URL in the background.

        Args:
            quality: Quality setting for the track
        """
        try:
            next_index = self._get_next_track_index()
            next_track = self._active_playlist[next_index]

            log(f"TracksList: Pre-fetching URL for: {next_track['name']}")

            tidal_client = TidalClient()
            try:
                # Offload to a thread — get_track_url is a blocking HTTP call.
                # Enforce a timeout so a dead network can't freeze the event loop.
                track_url, stream_metadata, error_info = await asyncio.wait_for(
                    asyncio.get_running_loop().run_in_executor(
                        None,
                        lambda: tidal_client.get_track_url(next_track["id"], quality),
                    ),
                    timeout=12.0,
                )
            except asyncio.TimeoutError:
                log(f"TracksList: Pre-fetch timed out for: {next_track['name']}")
                return

            if track_url:
                self._prefetched_track_id = next_track["id"]
                self._prefetched_url = track_url
                self._prefetched_metadata = stream_metadata
                self._prefetched_error_info = error_info
                log(f"TracksList: Pre-fetch successful for: {next_track['name']}")
            else:
                log(f"TracksList: Pre-fetch failed for: {next_track['name']}")
        except Exception as e:
            log(f"TracksList: Pre-fetch error: {e}")
        finally:
            self._prefetch_in_progress = False

    def _start_prefetch_worker(self, quality: str) -> None:
        """Launch the pre-fetch worker (must run on the Textual event-loop thread)."""
        self.run_worker(self._prefetch_next_track(quality), exclusive=False)

    def _clear_prefetch_state(self) -> None:
        """Clear the pre-fetch state."""
        self._prefetched_track_id = None
        self._prefetched_url = None
        self._prefetched_metadata = None
        self._prefetched_error_info = None
        self._prefetch_in_progress = False

    # ------------------------------------------------------------------
    # Stream error recovery (transparent VPN / network change handling)
    # ------------------------------------------------------------------

    def _on_stream_error(self) -> None:
        """Called from the mpv callback thread on stream error (e.g. VPN drop).

        Saves the playback position and schedules a recovery worker that will
        silently retry until the network is restored, then resumes the track.
        """
        if self._stream_recovery_in_progress:
            return

        from ttydal.services.mpv_playback_engine import MpvPlaybackEngine

        player = MpvPlaybackEngine()
        track = player.get_current_track()
        if not track:
            return

        resume_pos = player.get_last_time_pos()
        log(
            f"TracksList: Stream error — scheduling recovery for "
            f"'{track.get('name')}' at {resume_pos:.1f}s"
        )
        self._stream_recovery_in_progress = True

        try:
            self.app.call_from_thread(
                self._start_stream_recovery, track, resume_pos
            )
        except Exception as e:
            log(f"TracksList: Error scheduling stream recovery: {e}")
            self._stream_recovery_in_progress = False

    def _start_stream_recovery(self, track: dict, resume_pos: float) -> None:
        """Launch the stream recovery worker (must run on the Textual event-loop thread)."""
        from ttydal.components.player_bar import PlayerBar

        try:
            player_bar = self.app.query_one(PlayerBar)
            player_bar.set_reconnecting(True)
        except Exception:
            pass

        self.run_worker(
            self._recover_stream(track, resume_pos),
            exclusive=False,
        )

    async def _recover_stream(self, track: dict, resume_pos: float) -> None:
        """Retry fetching a stream URL until the network comes back.

        Runs every 5 s for the first attempt, then every 10 s for up to ~3 minutes.
        Once a URL is obtained the track is resumed from the saved position.
        """
        from ttydal.config import ConfigManager
        from ttydal.services.mpv_playback_engine import MpvPlaybackEngine
        from ttydal.components.player_bar import PlayerBar

        config = ConfigManager()
        tidal = TidalClient()

        def _get_player_bar():
            try:
                return self.app.query_one(PlayerBar)
            except Exception:
                return None

        try:
            for attempt in range(18):  # 5 s + 17 × 10 s ≈ 3 min total
                await asyncio.sleep(5 if attempt == 0 else 10)

                player = MpvPlaybackEngine()

                # Abort if the user manually started something else
                if player.is_playing():
                    log("TracksList: Recovery aborted — playback already active")
                    return

                log(f"TracksList: Recovery attempt {attempt + 1}…")
                try:
                    # Offload to a thread — get_track_url is a blocking HTTP call.
                    # Enforce a timeout so a dead network can't freeze the event loop.
                    track_url, stream_metadata, _ = await asyncio.wait_for(
                        asyncio.get_running_loop().run_in_executor(
                            None,
                            lambda: tidal.get_track_url(track["id"], config.quality),
                        ),
                        timeout=12.0,
                    )
                except asyncio.TimeoutError:
                    log(f"TracksList: Recovery attempt {attempt + 1} timed out, retrying…")
                    continue

                if track_url:
                    log(
                        f"TracksList: Recovery succeeded — resuming at {resume_pos:.1f}s"
                    )
                    player.play(track_url, track)
                    if resume_pos > 2:
                        await asyncio.sleep(1.5)  # Wait for mpv to start buffering
                        player.seek(resume_pos, reference="absolute")

                    # Update the player bar: show green notice and refresh stream quality
                    player_bar = _get_player_bar()
                    if player_bar:
                        player_bar.set_reconnected()
                        if stream_metadata:
                            player_bar.update_stream_quality(stream_metadata)
                    return

                log(f"TracksList: Recovery attempt {attempt + 1} failed, retrying…")

            log("TracksList: Recovery failed after all attempts")
        finally:
            self._stream_recovery_in_progress = False
            # Running inside an async worker (already on the event loop) — call directly.
            player_bar = _get_player_bar()
            if player_bar:
                player_bar.set_reconnecting(False)

    # ------------------------------------------------------------------
    # Playback-start retry (WiFi reconnect when next track fails to load)
    # ------------------------------------------------------------------

    def start_playback_retry(self, track_id: str, track_info: dict) -> None:
        """Retry starting a track that failed due to network loss.

        Called from PlayerPage when play_track() fails with "Not logged in".
        Must be called on the Textual event-loop thread.
        """
        if self._stream_recovery_in_progress:
            log("TracksList: Playback retry skipped — recovery already in progress")
            return

        log(f"TracksList: Scheduling playback retry for '{track_info.get('name')}'")
        self._stream_recovery_in_progress = True

        from ttydal.components.player_bar import PlayerBar

        try:
            player_bar = self.app.query_one(PlayerBar)
            player_bar.set_reconnecting(True)
        except Exception:
            pass

        self.run_worker(
            self._retry_track_start(track_id, track_info),
            exclusive=False,
        )

    async def _retry_track_start(self, track_id: str, track_info: dict) -> None:
        """Retry fetching and starting a track until the network comes back.

        Runs every 5 s for the first attempt, then every 10 s for up to ~2.5 minutes
        (15 attempts total). On success, posts TrackSelected with the fetched URL so
        PlayerPage handles the full UI update (cover art, vibrant color, stream quality).
        """
        from ttydal.config import ConfigManager
        from ttydal.components.player_bar import PlayerBar

        config = ConfigManager()
        tidal = TidalClient()

        def _get_player_bar():
            try:
                return self.app.query_one(PlayerBar)
            except Exception:
                return None

        try:
            for attempt in range(15):  # 5 s + 14 × 10 s ≈ 2.5 min total
                await asyncio.sleep(5 if attempt == 0 else 10)

                log(f"TracksList: Playback retry attempt {attempt + 1}…")
                try:
                    track_url, stream_metadata, error_info = await asyncio.wait_for(
                        asyncio.get_running_loop().run_in_executor(
                            None,
                            lambda: tidal.get_track_url(track_id, config.quality),
                        ),
                        timeout=12.0,
                    )
                except asyncio.TimeoutError:
                    log(f"TracksList: Playback retry attempt {attempt + 1} timed out, retrying…")
                    continue

                if track_url:
                    log(f"TracksList: Playback retry succeeded for '{track_info.get('name')}'")
                    player_bar = _get_player_bar()
                    if player_bar:
                        player_bar.set_reconnected()
                    # Post with prefetched data — PlayerPage fast path handles player.play()
                    # and all PlayerBar updates (cover art, vibrant color, stream quality).
                    self.post_message(
                        self.TrackSelected(
                            track_id,
                            track_info,
                            prefetched_url=track_url,
                            prefetched_metadata=stream_metadata,
                            prefetched_error_info=error_info,
                        )
                    )
                    return

                log(f"TracksList: Playback retry attempt {attempt + 1} failed, retrying…")

            log(f"TracksList: Playback retry exhausted for '{track_info.get('name')}'")
            self.app.notify(
                f"Could not play '{track_info.get('name', 'Track')}': no network after retries",
                severity="error",
                timeout=10,
            )
        finally:
            self._stream_recovery_in_progress = False
            # Running inside an async worker (already on the event loop) — call directly.
            player_bar = _get_player_bar()
            if player_bar:
                player_bar.set_reconnecting(False)

    def _generate_shuffle_order(self) -> None:
        """Generate a new random shuffle order for the active playlist."""
        if not self._active_playlist:
            self.shuffled_indices = []
            self.shuffle_position = 0
            return

        # Create a list of all indices and shuffle it
        self.shuffled_indices = list(range(len(self._active_playlist)))
        random.shuffle(self.shuffled_indices)

        # If currently playing, put the current track at position 0
        if (
            self.current_playing_index is not None
            and self.current_playing_index in self.shuffled_indices
        ):
            self.shuffled_indices.remove(self.current_playing_index)
            self.shuffled_indices.insert(0, self.current_playing_index)
            self.shuffle_position = 0

        log(
            f"TracksList: Generated shuffle order: {self.shuffled_indices[:5]}... (showing first 5)"
        )

    def _capture_active_playlist(self) -> None:
        """Snapshot current tracks as the active playback playlist."""
        from ttydal.config import ConfigManager

        self._active_playlist = list(self.tracks)
        self._active_playlist_item_id = self.current_item_id
        if ConfigManager().shuffle:
            self._generate_shuffle_order()
        else:
            self.shuffled_indices = []
            self.shuffle_position = 0

    def on_shuffle_changed(self, enabled: bool) -> None:
        """Handle shuffle setting change.

        Args:
            enabled: Whether shuffle is now enabled
        """
        log(f"TracksList: Shuffle changed to {enabled}")
        if enabled:
            self._generate_shuffle_order()
        else:
            self.shuffled_indices = []
            self.shuffle_position = 0

    def _get_next_track_index(self) -> int:
        """Get the next track index, respecting shuffle mode."""
        from ttydal.config import ConfigManager

        config = ConfigManager()

        if config.shuffle and self.shuffled_indices:
            # Find current position in shuffle order
            if self.current_playing_index is not None:
                try:
                    self.shuffle_position = self.shuffled_indices.index(
                        self.current_playing_index
                    )
                except ValueError:
                    self.shuffle_position = 0

            # Move to next position in shuffle order
            next_shuffle_pos = (self.shuffle_position + 1) % len(self.shuffled_indices)
            self.shuffle_position = next_shuffle_pos
            return self.shuffled_indices[next_shuffle_pos]
        else:
            # Normal sequential order
            if self.current_playing_index is None:
                return 0
            return (self.current_playing_index + 1) % len(self._active_playlist)

    def _get_previous_track_index(self) -> int:
        """Get the previous track index, respecting shuffle mode."""
        from ttydal.config import ConfigManager

        config = ConfigManager()

        if config.shuffle and self.shuffled_indices:
            # Find current position in shuffle order
            if self.current_playing_index is not None:
                try:
                    self.shuffle_position = self.shuffled_indices.index(
                        self.current_playing_index
                    )
                except ValueError:
                    self.shuffle_position = 0

            # Move to previous position in shuffle order
            prev_shuffle_pos = (self.shuffle_position - 1) % len(self.shuffled_indices)
            self.shuffle_position = prev_shuffle_pos
            return self.shuffled_indices[prev_shuffle_pos]
        else:
            # Normal sequential order
            if self.current_playing_index is None:
                return len(self._active_playlist) - 1
            return (self.current_playing_index - 1) % len(self._active_playlist)

    def load_tracks(
        self, item_id: str, item_name: str, item_type: str = "album"
    ) -> None:
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

        # Add loading class for visual feedback
        self.add_class("loading")

        # Update header to show loading
        header = self.query_one(Label)
        header.update(f"(t)racks - {item_name} (Loading...)")

        # Clear state immediately
        self.tracks = []

        # Run the loading in a worker so UI can update
        # Use exclusive=True to cancel any previous loading workers
        self.run_worker(
            self._load_tracks_async(item_id, item_name, item_type), exclusive=True
        )

    async def _load_tracks_async(
        self, item_id: str, item_name: str, item_type: str
    ) -> None:
        """Async worker to load tracks without blocking UI.

        Args:
            item_id: The item ID to load tracks from
            item_name: The item name for display
            item_type: Type of item ('album', 'playlist', or 'favorites')
        """
        try:
            # Await clear to ensure old items are fully removed from DOM
            list_view = self.query_one("#tracks-listview", ListView)
            await list_view.clear()

            # Check cache first
            cache = TracksCache()
            cached_tracks = cache.get(item_id)

            if cached_tracks is not None:
                log(f"  - Using cached tracks for {item_id}")
                tracks_list = cached_tracks
            else:
                # Load tracks based on item type
                log(f"  - Loading tracks for type: {item_type}")
                if item_type == "favorites":
                    # Load favorite tracks
                    tracks_list = await self.tracks_service.get_favorites_tracks()
                elif item_type == "playlist":
                    # Load playlist tracks
                    tracks_list = await self.tracks_service.get_playlist_tracks(item_id)
                else:  # album
                    # Load album tracks
                    tracks_list = await self.tracks_service.get_album_tracks(item_id)

                # Store in cache for future use and search
                cache.set(item_id, tracks_list)

            log(f"  - Retrieved {len(tracks_list)} tracks")

            # Build tracks array locally then assign atomically
            new_tracks = []

            for idx, track in enumerate(tracks_list, 1):
                track_name = track["name"]
                artist = track.get("artist", "Unknown")
                duration = self._format_duration(track["duration"])
                cover_url = track.get("cover_url")

                # Get album name from track or use the current item name
                album_name = track.get("album", item_name)

                display_text = f"{idx}. {track_name} - {artist} ({duration})"
                list_view.append(
                    ListItem(CoverArtItem(display_text, cover_url=cover_url))
                )
                new_tracks.append(
                    {
                        "id": str(track["id"]),
                        "name": track_name,
                        "artist": artist,
                        "album": album_name,
                        "duration": track["duration"],
                        "cover_url": cover_url,
                        "index": idx,  # Store 1-indexed track number
                    }
                )

            self.tracks = new_tracks
            log(f"  - Loaded {len(self.tracks)} tracks")

            # Update header to remove loading text
            header = self.query_one(Label)
            header.update(f"(t)racks - {item_name}")

            # Regenerate shuffle order if shuffle is enabled
            from ttydal.config import ConfigManager

            config = ConfigManager()
            if config.shuffle:
                self._generate_shuffle_order()

            # Update visual indicators (in case we're reloading while a track is playing)
            self._update_track_indicators()

            # Select initial track after a small delay to ensure DOM is settled
            if self.tracks:
                self.set_timer(0.1, self._select_initial_track)
        except TidalServiceError as e:
            log(f"TracksList: Service error loading tracks: {e}")
            header = self.query_one(Label)
            header.update(f"(t)racks - {item_name} (error)")
            self.app.notify(e.user_message, severity="error", timeout=5)
        finally:
            # Remove loading class when done (success or error)
            self.remove_class("loading")

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

    def _select_initial_track(self) -> None:
        """Select the appropriate track after loading a playlist.

        If viewing the playlist that's currently playing, select the playing track.
        Otherwise, select the first track.
        """
        try:
            list_view = self.query_one("#tracks-listview", ListView)
            if not self.tracks or len(list_view.children) == 0:
                return

            # If this is the playing playlist, select the playing track
            if (
                self._playing_item_id == self.current_item_id
                and self.current_playing_index is not None
                and self.current_playing_index < len(self.tracks)
            ):
                target = self.current_playing_index
                log(f"TracksList: Selected playing track at index {target}")
            else:
                target = 0
                log("TracksList: Selected first track")

            list_view.index = target
        except Exception as e:
            log(f"TracksList: Failed to select initial track: {e}")

    def _update_track_indicators(self) -> None:
        """Update track list to show '>' indicator for currently playing track."""
        try:
            list_view = self.query_one("#tracks-listview", ListView)
            # Only show indicator if viewing the album that contains the playing track
            show_indicator = self.current_item_id == self._playing_item_id
            for idx, list_item in enumerate(list_view.children):
                if idx < len(self.tracks):
                    track = self.tracks[idx]
                    track_name = track["name"]
                    artist = track["artist"]
                    duration = self._format_duration(track["duration"])
                    track_number = track.get(
                        "index", idx + 1
                    )  # Use stored index or fallback

                    # Add ">" prefix if this is the currently playing track
                    # AND we're viewing the album that contains the playing track
                    prefix = (
                        "> "
                        if show_indicator and idx == self.current_playing_index
                        else "  "
                    )
                    display_text = (
                        f"{prefix}{track_number}. {track_name} - {artist} ({duration})"
                    )

                    # Update the CoverArtItem text
                    try:
                        cover_art_item = list_item.query_one(CoverArtItem)
                        cover_art_item.update_text(display_text)
                    except Exception:
                        # Fallback to Label for backwards compatibility
                        try:
                            label = list_item.query_one(Label)
                            label.update(display_text)
                        except Exception:
                            pass
        except Exception as e:
            log(f"  - Error updating track indicators: {e}")

    def action_play_selected_track(self) -> None:
        """Play the currently selected track or toggle pause (space key action).

        Behavior:
        - If no track selected: do nothing
        - If selected track is different from playing track: play selected track
        - If selected track is same as playing track: toggle pause
        - If no track is playing: play selected track
        """
        log("=" * 80)
        log("TracksList: Space key action triggered")
        list_view = self.query_one("#tracks-listview", ListView)
        index = list_view.index
        log(f"  - ListView index: {index}")
        log(f"  - Total tracks: {len(self.tracks)}")
        log(f"  - Current playing index: {self.current_playing_index}")

        if index is None or index >= len(self.tracks):
            log("  - No track selected, toggling pause/play")
            # No track selected, toggle pause on whatever is playing
            from ttydal.services.mpv_playback_engine import MpvPlaybackEngine

            player = MpvPlaybackEngine()
            player.toggle_pause()
            log("=" * 80)
            return

        selected_track = self.tracks[index]
        log(
            f"  - Selected track: {selected_track['name']} (ID: {selected_track['id']})"
        )

        # Get currently playing track
        from ttydal.services.mpv_playback_engine import MpvPlaybackEngine

        player = MpvPlaybackEngine()
        current_track = player.get_current_track()
        log(
            f"  - Current playing track: {current_track.get('name', 'Unknown') if current_track else 'None'}"
        )
        log(
            f"  - Current playing track ID: {current_track.get('id', 'Unknown') if current_track else 'None'}"
        )

        if current_track and current_track.get("id") == selected_track["id"]:
            # Same track is selected and playing, toggle pause
            log("  - Same track already playing, toggling pause")
            player.toggle_pause()
            log("=" * 80)
        else:
            # Different track or no track playing, play the selected track
            if current_track:
                log(
                    "  - Different track selected (current: {current_track.get('name', 'Unknown')}), playing new track"
                )
            else:
                log("  - No track playing, starting playback")

            # Capture the current album as the active playback playlist
            self._capture_active_playlist()

            # Update current playing index and album
            self.current_playing_index = index
            self._playing_item_id = self.current_item_id
            log(f"  - Updated current playing index to: {index}")

            # Update visual indicators
            self._update_track_indicators()
            log("  - Updated visual indicators")

            log("  - Posting TrackSelected message")
            self.post_message(self.TrackSelected(selected_track["id"], selected_track))
            log("=" * 80)

    def action_refresh_tracks(self) -> None:
        """Refresh the current tracks list (r key action).

        This invalidates the cache entry for this album/playlist to fetch fresh data.
        """
        log("TracksList: Refresh tracks action triggered")
        if self.current_item_id and self.current_item_type:
            # Invalidate cache for this item only (not entire cache)
            TracksCache().invalidate(self.current_item_id)
            log(f"  - Invalidated cache for {self.current_item_id}")
            log(f"  - Reloading tracks for {self.current_album_name}")
            self.load_tracks(
                self.current_item_id, self.current_album_name, self.current_item_type
            )
        else:
            log("  - No tracks loaded yet, nothing to refresh")

    def action_cursor_down(self) -> None:
        """Move cursor down in the list."""
        list_view = self.query_one("#tracks-listview", ListView)
        list_view.action_cursor_down()

    def action_cursor_up(self) -> None:
        """Move cursor up in the list."""
        list_view = self.query_one("#tracks-listview", ListView)
        list_view.action_cursor_up()

    def action_focus_albums(self) -> None:
        """Move focus to albums list."""
        from ttydal.components.albums_list import AlbumsList

        try:
            albums_list = self.app.query_one(AlbumsList)
            list_view = albums_list.query_one("#albums-listview")
            list_view.focus()
        except Exception:
            pass

    def action_show_art(self) -> None:
        """Open cover art modal for the currently highlighted track."""
        list_view = self.query_one("#tracks-listview", ListView)
        index = list_view.index
        if index is None or index >= len(self.tracks):
            return
        cover_url = self.tracks[index].get("cover_url")
        if not cover_url:
            self.app.notify("No cover art available", timeout=2)
            return
        from ttydal.components.cover_art_modal import CoverArtModal
        self.app.push_screen(CoverArtModal(cover_url))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle track selection (Enter key or double-click).

        Always plays the selected track, even if it's already playing.

        Args:
            event: The selection event
        """
        if event.list_view.id == "tracks-listview":
            log("=" * 80)
            log("TracksList: Enter key/double-click action triggered")
            index = event.list_view.index
            log(f"  - ListView index: {index}")
            log(f"  - Total tracks: {len(self.tracks)}")
            log(f"  - Current playing index: {self.current_playing_index}")
            if index is not None and index < len(self.tracks):
                track = self.tracks[index]
                log(f"  - Selected track: {track['name']} (ID: {track['id']})")
                log("  - Playing/restarting track (Enter always plays)")

                # Capture the current album as the active playback playlist
                self._capture_active_playlist()

                # Update current playing index and album for auto-play tracking
                self.current_playing_index = index
                self._playing_item_id = self.current_item_id
                log(f"  - Updated current playing index to: {index}")

                # Update visual indicators
                self._update_track_indicators()
                log("  - Updated visual indicators")

                log("  - Posting TrackSelected message")
                self.post_message(self.TrackSelected(track["id"], track))
                log("=" * 80)

    def play_next_track(self) -> None:
        """Play the next track in the active playlist."""
        if not self._active_playlist:
            return

        next_index = self._get_next_track_index()
        next_track = self._active_playlist[next_index]
        self.current_playing_index = next_index
        self._playing_item_id = self._active_playlist_item_id

        if self.current_item_id == self._active_playlist_item_id:
            list_view = self.query_one("#tracks-listview", ListView)
            list_view.index = next_index
        self._update_track_indicators()
        self.post_message(self.TrackSelected(next_track["id"], next_track))

    def play_previous_track(self) -> None:
        """Play the previous track in the active playlist."""
        if not self._active_playlist:
            return

        prev_index = self._get_previous_track_index()
        prev_track = self._active_playlist[prev_index]
        self.current_playing_index = prev_index
        self._playing_item_id = self._active_playlist_item_id

        if self.current_item_id == self._active_playlist_item_id:
            list_view = self.query_one("#tracks-listview", ListView)
            list_view.index = prev_index
        self._update_track_indicators()
        self.post_message(self.TrackSelected(prev_track["id"], prev_track))
