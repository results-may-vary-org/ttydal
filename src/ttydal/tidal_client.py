"""Tidal API client singleton wrapper for ttydal."""

import tidalapi
from tidalapi.session import Session

from ttydal.api_logger import install_api_logger
from ttydal.credentials import CredentialManager
from ttydal.logger import log


class TidalClient:
    """Singleton Tidal API client wrapper."""

    _instance = None

    def __new__(cls):
        """Ensure only one instance exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the Tidal client."""
        if self._initialized:
            return

        log("TidalClient.__init__() called")
        log("  - Installing API logger...")
        install_api_logger()
        log("  - API logger installed")
        log("  - Creating tidalapi.Session()...")
        self.session: Session = tidalapi.Session()
        log("  - Session created")
        log("  - Creating CredentialManager...")
        self.credentials = CredentialManager()
        log("  - CredentialManager created")
        self._initialized = True
        log("TidalClient.__init__() completed")

    def is_logged_in(self) -> bool:
        """Check if user is logged in.

        Returns:
            True if logged in, False otherwise
        """
        return self.session.check_login()

    def login(self) -> tuple[str, str]:
        """Initiate login process.

        Returns:
            Tuple of (login_url, verification_code) for OAuth login
        """
        login, future = self.session.login_oauth()
        return login.verification_uri_complete, login.user_code

    def complete_login(self) -> bool:
        """Complete the OAuth login process.

        Returns:
            True if login successful, False otherwise
        """
        if self.session.check_login():
            # Store session tokens
            token_type = self.session.token_type
            access_token = self.session.access_token
            refresh_token = self.session.refresh_token

            if token_type and access_token:
                self.credentials.store_token("token_type", token_type)
                self.credentials.store_token("access_token", access_token)
                if refresh_token:
                    self.credentials.store_token("refresh_token", refresh_token)
                return True
        return False

    def load_session(self) -> bool:
        """Load session from stored credentials.

        Returns:
            True if session loaded successfully, False otherwise
        """
        log("TidalClient.load_session() called")
        token_type = self.credentials.get_token("token_type")
        access_token = self.credentials.get_token("access_token")
        refresh_token = self.credentials.get_token("refresh_token")

        log(f"  - token_type exists: {token_type is not None}")
        log(f"  - access_token exists: {access_token is not None}")
        log(f"  - refresh_token exists: {refresh_token is not None}")

        if token_type and access_token:
            log("  - Loading OAuth session...")
            self.session.load_oauth_session(token_type, access_token, refresh_token)
            log("  - Checking login status...")
            result = self.session.check_login()
            log(f"  - Login status: {result}")
            return result
        log("  - No credentials found, returning False")
        return False

    def get_user_albums(self) -> list:
        """Get user's favorite albums.

        Returns:
            List of user favorite albums
        """
        log("=" * 60)
        log("API CALL: get_user_albums()")
        log("  Request: session.user.favorites.albums()")
        if not self.is_logged_in():
            log("  Response: Not logged in, returning []")
            log("=" * 60)
            return []
        try:
            albums = list(self.session.user.favorites.albums())
            log(f"  Response: Success - {len(albums)} favorite albums")
            for idx, album in enumerate(albums[:5]):  # Log first 5
                log(
                    f"    [{idx}] {album.name} (ID: {album.id}, tracks: {getattr(album, 'num_tracks', '?')})"
                )
            if len(albums) > 5:
                log(f"    ... and {len(albums) - 5} more")
            log("=" * 60)
            return albums
        except Exception as e:
            log(f"  Response: ERROR - {e}")
            import traceback

            log(traceback.format_exc())
            log("=" * 60)
            return []

    def get_user_playlists(self) -> list:
        """Get user's playlists.

        Returns:
            List of user playlists
        """
        log("=" * 60)
        log("API CALL: get_user_playlists()")
        log("  Request: session.user.playlists()")
        if not self.is_logged_in():
            log("  Response: Not logged in, returning []")
            log("=" * 60)
            return []
        try:
            playlists = list(self.session.user.playlists())
            log(f"  Response: Success - {len(playlists)} playlists")
            for idx, pl in enumerate(playlists[:5]):  # Log first 5
                log(
                    f"    [{idx}] {pl.name} (ID: {pl.id}, tracks: {getattr(pl, 'num_tracks', '?')})"
                )
            if len(playlists) > 5:
                log(f"    ... and {len(playlists) - 5} more")
            log("=" * 60)
            return playlists
        except Exception as e:
            log(f"  Response: ERROR - {e}")
            import traceback

            log(traceback.format_exc())
            log("=" * 60)
            return []

    def get_user_favorites(self) -> list:
        """Get user's favorite tracks using two-step API call with dynamic limit.

        First calls API with limit=999, then checks totalNumberOfItems.
        If total > 999, makes second call with limit=totalNumberOfItems.

        Returns:
            List of favorite tracks
        """
        log("=" * 60)
        log("API CALL: get_user_favorites()")
        if not self.is_logged_in():
            log("  Response: Not logged in, returning []")
            log("=" * 60)
            return []

        try:
            # First call with limit=999
            log("  First API call with limit=999")
            log("  Request: session.user.favorites.tracks(limit=999)")
            first_response = self.session.user.favorites.tracks(limit=999)

            # Check if response has totalNumberOfItems
            total_items = None
            if hasattr(first_response, "totalNumberOfItems"):
                total_items = first_response.totalNumberOfItems

            log(f"  Response metadata: totalNumberOfItems = {total_items}")

            # Determine if we need a second call
            if total_items is not None and total_items > 999:
                log(
                    f"  Total items ({total_items}) > 999, making second call with limit={total_items}"
                )
                log(f"  Request: session.user.favorites.tracks(limit={total_items})")
                second_response = self.session.user.favorites.tracks(limit=total_items)
                tracks = list(second_response)
                log(
                    f"  Response: Success - Retrieved {len(tracks)} favorite tracks (from second call)"
                )
            else:
                log(
                    f"  Total items ({total_items if total_items is not None else 'N/A'}) <= 999, using first response"
                )
                tracks = list(first_response)
                log(
                    f"  Response: Success - Retrieved {len(tracks)} favorite tracks (from first call)"
                )

            # Log sample tracks
            for idx, track in enumerate(tracks[:3]):  # Log first 3
                log(
                    f"    [{idx}] {track.name} by {track.artist.name if hasattr(track, 'artist') else 'Unknown'}"
                )
            if len(tracks) > 3:
                log(f"    ... and {len(tracks) - 3} more")
            log("=" * 60)

            # sort by date
            tracks.sort(key=lambda t: t.user_date_added, reverse=True)
            return tracks

        except Exception as e:
            log(f"  Response: ERROR - {e}")
            import traceback

            log(traceback.format_exc())
            log("=" * 60)
            return []

    def get_album_tracks(self, album_id: str) -> list:
        """Get ALL tracks from an album.

        Args:
            album_id: The album ID

        Returns:
            List of all tracks in the album
        """
        log("=" * 60)
        log(f"API CALL: get_album_tracks(album_id={album_id})")
        log(f"  Request: session.album({album_id}).tracks()")
        if not self.is_logged_in():
            log("  Response: Not logged in, returning []")
            log("=" * 60)
            return []
        try:
            album = self.session.album(album_id)
            log(
                f"  - Album fetched: {album.name if hasattr(album, 'name') else 'Unknown'}"
            )
            # fixme Get all tracks - tidalapi should handle pagination
            tracks = list(album.tracks())
            log(f"  Response: Success - {len(tracks)} tracks from album")
            for idx, track in enumerate(tracks[:3]):  # Log first 3
                log(
                    f"    [{idx}] {track.name} by {track.artist.name if hasattr(track, 'artist') else 'Unknown'}"
                )
            if len(tracks) > 3:
                log(f"    ... and {len(tracks) - 3} more")
            log("=" * 60)
            return tracks
        except Exception as e:
            log(f"  Response: ERROR - {e}")
            import traceback

            log(traceback.format_exc())
            log("=" * 60)
            return []

    def get_playlist_tracks(self, playlist_id: str) -> list:
        """Get ALL tracks from a playlist.

        Args:
            playlist_id: The playlist ID

        Returns:
            List of all tracks in the playlist
        """
        log("=" * 60)
        log(f"API CALL: get_playlist_tracks(playlist_id={playlist_id})")
        log(f"  Request: session.playlist({playlist_id}).tracks()")
        if not self.is_logged_in():
            log("  Response: Not logged in, returning []")
            log("=" * 60)
            return []
        try:
            playlist = self.session.playlist(playlist_id)
            log(
                f"  - Playlist fetched: {playlist.name if hasattr(playlist, 'name') else 'Unknown'}"
            )
            # fixme Get ALL tracks - tidalapi handles pagination automatically
            tracks = list(playlist.tracks())
            log(f"  Response: Success - {len(tracks)} tracks from playlist")
            for idx, track in enumerate(tracks[:3]):  # Log first 3
                log(
                    f"    [{idx}] {track.name} by {track.artist.name if hasattr(track, 'artist') else 'Unknown'}"
                )
            if len(tracks) > 3:
                log(f"    ... and {len(tracks) - 3} more")
            log("=" * 60)
            return tracks
        except Exception as e:
            log(f"  Response: ERROR - {e}")
            import traceback

            log(traceback.format_exc())
            log("=" * 60)
            return []

    def get_track_url(
        self, track_id: str, quality: str = "high"
    ) -> tuple[str | None, dict | None, dict]:
        """Get playback URL and stream metadata for a track with automatic quality fallback.

        Args:
            track_id: The track ID
            quality: Quality setting ('max', 'high', or 'low')

        Returns:
            Tuple of (track_url, stream_metadata, error_info)
            - track_url: Playback URL or None if failed
            - stream_metadata: Contains audio_quality, bit_depth, sample_rate, audio_mode or None
            - error_info: Always present dict with:
                - requested_quality: The quality originally requested
                - actual_quality: The quality actually used (if successful)
                - fallback_applied: Whether we had to fallback to a lower quality
                - error: Error message if completely failed
                - tried_qualities: List of qualities attempted
        """
        log("=" * 60)
        log(f"API CALL: get_track_url(track_id={track_id}, quality={quality})")

        # Define quality fallback order
        quality_order = {
            "max": ["max", "high", "low"],
            "high": ["high", "low"],
            "low": ["low"],
        }

        error_info = {
            "requested_quality": quality,
            "actual_quality": None,
            "fallback_applied": False,
            "error": None,
            "tried_qualities": [],
            "vibrant_color": None,  # Extract from API response
        }

        if not self.is_logged_in():
            error_info["error"] = "Not logged in"
            log("  Response: Not logged in, returning None")
            log("=" * 60)
            return None, None, error_info

        # Get the fallback sequence for the requested quality
        qualities_to_try = quality_order.get(quality, ["high", "low"])
        log(f"  - Quality fallback sequence: {qualities_to_try}")

        # Fetch track - first get raw API response to extract vibrant color
        try:
            log(f"  - Fetching track data for ID {track_id}")
            # Get raw response to extract vibrant color (tidalapi doesn't expose it)
            raw_response = self.session.request.request("GET", f"tracks/{track_id}")
            if raw_response and raw_response.ok:
                raw_data = raw_response.json()
                album_data = raw_data.get("album", {})
                error_info["vibrant_color"] = album_data.get("vibrantColor")
                log(f"  - Extracted vibrant color: {error_info['vibrant_color']}")

            # Now get the track object for playback
            track = self.session.track(track_id)
            log(
                f"  - Track fetched: {track.name if hasattr(track, 'name') else 'Unknown'}"
            )
        except Exception as e:
            error_info["error"] = f"Failed to fetch track: {str(e)}"
            log(f"  Response: ERROR - {error_info['error']}")
            import traceback

            log(traceback.format_exc())
            log("=" * 60)
            return None, None, error_info

        # Try each quality level in order
        last_error = None
        for attempt_quality in qualities_to_try:
            error_info["tried_qualities"].append(attempt_quality)
            log(f"  - Attempting quality: {attempt_quality}")

            try:
                # Set quality on the session config
                if attempt_quality == "max":
                    self.session.config.quality = tidalapi.Quality.hi_res_lossless
                    log(
                        "    - Session quality set to: HI_RES_LOSSLESS (up to 24bit/192kHz)"
                    )
                elif attempt_quality == "high":
                    self.session.config.quality = tidalapi.Quality.high_lossless
                    log("    - Session quality set to: HIGH_LOSSLESS (16bit/44.1kHz)")
                else:  # low
                    self.session.config.quality = tidalapi.Quality.low_320k
                    log("    - Session quality set to: LOW_320K (320kbps AAC)")

                # Get stream - this returns a Stream object with metadata
                log("    - Requesting stream metadata...")
                stream = track.get_stream()

                if not stream:
                    log("    - No stream available at this quality")
                    last_error = "No stream available"
                    continue

                # Extract stream metadata
                stream_metadata = {
                    "audio_quality": getattr(stream, "audio_quality", "Unknown"),
                    "bit_depth": getattr(stream, "bit_depth", None),
                    "sample_rate": getattr(stream, "sample_rate", None),
                    "audio_mode": getattr(stream, "audio_mode", "Unknown"),
                }

                # Get the actual playback URL from track (not stream)
                log("    - Requesting playback URL...")
                stream_url = track.get_url()

                # Success!
                error_info["actual_quality"] = attempt_quality
                error_info["fallback_applied"] = attempt_quality != quality

                log("  Response: Success - Stream obtained")
                log(f"  - Audio quality: {stream_metadata['audio_quality']}")
                log(
                    f"  - Bit depth: {stream_metadata['bit_depth']} bit"
                    if stream_metadata["bit_depth"]
                    else "  - Bit depth: N/A"
                )
                log(
                    f"  - Sample rate: {stream_metadata['sample_rate']} Hz"
                    if stream_metadata["sample_rate"]
                    else "  - Sample rate: N/A"
                )
                log(f"  - Audio mode: {stream_metadata['audio_mode']}")
                log(
                    f"  - URL: {stream_url[:50]}..."
                    if stream_url and len(stream_url) > 50
                    else f"  - URL: {stream_url}"
                )
                if error_info["fallback_applied"]:
                    log(
                        f"  - NOTE: Fallback applied from '{quality}' to '{attempt_quality}'"
                    )
                log("=" * 60)
                return stream_url, stream_metadata, error_info

            except Exception as e:
                error_str = str(e)
                log(f"    - Error at quality '{attempt_quality}': {error_str}")

                # Check if it's a 401 error (unauthorized - track not available at this quality)
                if "401" in error_str or "Unauthorized" in error_str:
                    log(
                        f"    - Track not available at '{attempt_quality}' quality, trying lower quality..."
                    )
                    last_error = f"Not available at {attempt_quality} quality"
                    continue
                else:
                    # Some other error - might be worth trying other qualities
                    log(
                        "    - Unexpected error, but continuing to try other qualities..."
                    )
                    last_error = error_str
                    continue

        # All qualities failed
        error_info["error"] = last_error or "Track not available at any quality"
        log(f"  Response: ERROR - {error_info['error']}")
        log(f"  - Tried qualities: {error_info['tried_qualities']}")
        log("=" * 60)
        return None, None, error_info

    def get_track_vibrant_color(self, track_id: str) -> str | None:
        """Get the vibrant color for a track's album.

        Makes a direct API call to get the track data which includes
        album.vibrantColor that tidalapi doesn't expose.

        Args:
            track_id: The track ID

        Returns:
            Hex color string (e.g., "#f2d869") or None if not available
        """
        log(f"API CALL: get_track_vibrant_color(track_id={track_id})")

        if not self.is_logged_in():
            log("  Response: Not logged in, returning None")
            return None

        try:
            # Use the session's request method to make a direct API call
            response = self.session.request.request("GET", f"tracks/{track_id}")

            if response and response.ok:
                data = response.json()
                album_data = data.get("album", {})
                vibrant_color = album_data.get("vibrantColor")
                log(f"  Response: vibrantColor = {vibrant_color}")
                return vibrant_color
            else:
                log(
                    f"  Response: API call failed - {response.status_code if response else 'No response'}"
                )
                return None

        except Exception as e:
            log(f"  Response: ERROR - {e}")
            return None
