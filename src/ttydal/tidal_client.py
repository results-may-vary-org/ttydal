"""Tidal API client singleton wrapper for ttydal."""

import tidalapi
from tidalapi.session import Session

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
            self.session.load_oauth_session(
                token_type, access_token, refresh_token
            )
            log("  - Checking login status...")
            result = self.session.check_login()
            log(f"  - Login status: {result}")
            return result
        log("  - No credentials found, returning False")
        return False

    def get_user_albums(self) -> list:
        """Get user's albums.

        Returns:
            List of user albums
        """
        log("="*60)
        log("API CALL: get_user_albums()")
        log("  Request: session.user.albums()")
        if not self.is_logged_in():
            log("  Response: Not logged in, returning []")
            log("="*60)
            return []
        try:
            albums = list(self.session.user.albums())
            log(f"  Response: Success - {len(albums)} albums")
            for idx, album in enumerate(albums[:5]):  # Log first 5
                log(f"    [{idx}] {album.name} (ID: {album.id}, tracks: {getattr(album, 'num_tracks', '?')})")
            if len(albums) > 5:
                log(f"    ... and {len(albums) - 5} more")
            log("="*60)
            return albums
        except Exception as e:
            log(f"  Response: ERROR - {e}")
            log("="*60)
            return []

    def get_user_playlists(self) -> list:
        """Get user's playlists.

        Returns:
            List of user playlists
        """
        log("="*60)
        log("API CALL: get_user_playlists()")
        log("  Request: session.user.playlists()")
        if not self.is_logged_in():
            log("  Response: Not logged in, returning []")
            log("="*60)
            return []
        try:
            playlists = list(self.session.user.playlists())
            log(f"  Response: Success - {len(playlists)} playlists")
            for idx, pl in enumerate(playlists[:5]):  # Log first 5
                log(f"    [{idx}] {pl.name} (ID: {pl.id}, tracks: {getattr(pl, 'num_tracks', '?')})")
            if len(playlists) > 5:
                log(f"    ... and {len(playlists) - 5} more")
            log("="*60)
            return playlists
        except Exception as e:
            log(f"  Response: ERROR - {e}")
            log("="*60)
            return []

    def get_user_favorites(self) -> list:
        """Get user's favorite tracks.

        Returns:
            List of favorite tracks
        """
        log("="*60)
        log("API CALL: get_user_favorites()")
        log("  Request: session.user.favorites.tracks()")
        if not self.is_logged_in():
            log("  Response: Not logged in, returning []")
            log("="*60)
            return []
        try:
            tracks = list(self.session.user.favorites.tracks())
            log(f"  Response: Success - {len(tracks)} favorite tracks")
            for idx, track in enumerate(tracks[:3]):  # Log first 3
                log(f"    [{idx}] {track.name} by {track.artist.name if hasattr(track, 'artist') else 'Unknown'}")
            if len(tracks) > 3:
                log(f"    ... and {len(tracks) - 3} more")
            log("="*60)
            return tracks
        except Exception as e:
            log(f"  Response: ERROR - {e}")
            log("="*60)
            return []

    def get_album_tracks(self, album_id: str) -> list:
        """Get ALL tracks from an album.

        Args:
            album_id: The album ID

        Returns:
            List of all tracks in the album
        """
        log("="*60)
        log(f"API CALL: get_album_tracks(album_id={album_id})")
        log(f"  Request: session.album({album_id}).tracks()")
        if not self.is_logged_in():
            log("  Response: Not logged in, returning []")
            log("="*60)
            return []
        try:
            album = self.session.album(album_id)
            log(f"  - Album fetched: {album.name if hasattr(album, 'name') else 'Unknown'}")
            # Get all tracks - tidalapi should handle pagination
            tracks = list(album.tracks())
            log(f"  Response: Success - {len(tracks)} tracks from album")
            for idx, track in enumerate(tracks[:3]):  # Log first 3
                log(f"    [{idx}] {track.name} by {track.artist.name if hasattr(track, 'artist') else 'Unknown'}")
            if len(tracks) > 3:
                log(f"    ... and {len(tracks) - 3} more")
            log("="*60)
            return tracks
        except Exception as e:
            log(f"  Response: ERROR - {e}")
            log("="*60)
            return []

    def get_playlist_tracks(self, playlist_id: str) -> list:
        """Get ALL tracks from a playlist.

        Args:
            playlist_id: The playlist ID

        Returns:
            List of all tracks in the playlist
        """
        log("="*60)
        log(f"API CALL: get_playlist_tracks(playlist_id={playlist_id})")
        log(f"  Request: session.playlist({playlist_id}).tracks()")
        if not self.is_logged_in():
            log("  Response: Not logged in, returning []")
            log("="*60)
            return []
        try:
            playlist = self.session.playlist(playlist_id)
            log(f"  - Playlist fetched: {playlist.name if hasattr(playlist, 'name') else 'Unknown'}")
            # Get ALL tracks - tidalapi handles pagination automatically
            tracks = list(playlist.tracks())
            log(f"  Response: Success - {len(tracks)} tracks from playlist")
            for idx, track in enumerate(tracks[:3]):  # Log first 3
                log(f"    [{idx}] {track.name} by {track.artist.name if hasattr(track, 'artist') else 'Unknown'}")
            if len(tracks) > 3:
                log(f"    ... and {len(tracks) - 3} more")
            log("="*60)
            return tracks
        except Exception as e:
            log(f"  Response: ERROR - {e}")
            import traceback
            log(traceback.format_exc())
            log("="*60)
            return []

    def get_track_url(self, track_id: str, quality: str = "high") -> str | None:
        """Get playback URL for a track.

        Args:
            track_id: The track ID
            quality: Quality setting ('high' or 'low')

        Returns:
            Track URL or None if not available
        """
        if not self.is_logged_in():
            return None

        track = self.session.track(track_id)
        # Map quality to Tidal quality enum
        tidal_quality = tidalapi.Quality.high_lossless if quality == "high" else tidalapi.Quality.low_320k

        try:
            stream = track.get_url(quality=tidal_quality)
            return stream
        except Exception:
            return None
