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
        log("TidalClient.get_user_albums() called")
        if not self.is_logged_in():
            log("  - Not logged in, returning empty list")
            return []
        try:
            albums = list(self.session.user.albums())
            log(f"  - Found {len(albums)} albums")
            return albums
        except Exception as e:
            log(f"  - Error getting albums: {e}")
            return []

    def get_user_playlists(self) -> list:
        """Get user's playlists.

        Returns:
            List of user playlists
        """
        log("TidalClient.get_user_playlists() called")
        if not self.is_logged_in():
            log("  - Not logged in, returning empty list")
            return []
        try:
            playlists = list(self.session.user.playlists())
            log(f"  - Found {len(playlists)} playlists")
            return playlists
        except Exception as e:
            log(f"  - Error getting playlists: {e}")
            return []

    def get_user_favorites(self) -> list:
        """Get user's favorite tracks.

        Returns:
            List of favorite tracks
        """
        if not self.is_logged_in():
            return []
        return list(self.session.user.favorites.tracks())

    def get_album_tracks(self, album_id: str) -> list:
        """Get ALL tracks from an album.

        Args:
            album_id: The album ID

        Returns:
            List of all tracks in the album
        """
        log(f"TidalClient.get_album_tracks({album_id}) called")
        if not self.is_logged_in():
            log("  - Not logged in, returning empty list")
            return []
        try:
            album = self.session.album(album_id)
            # Get all tracks - tidalapi should handle pagination
            tracks = list(album.tracks())
            log(f"  - Loaded {len(tracks)} tracks from album")
            return tracks
        except Exception as e:
            log(f"  - Error getting album tracks: {e}")
            return []

    def get_playlist_tracks(self, playlist_id: str) -> list:
        """Get ALL tracks from a playlist.

        Args:
            playlist_id: The playlist ID

        Returns:
            List of all tracks in the playlist
        """
        log(f"TidalClient.get_playlist_tracks({playlist_id}) called")
        if not self.is_logged_in():
            log("  - Not logged in, returning empty list")
            return []
        try:
            playlist = self.session.playlist(playlist_id)
            # Get all tracks - tidalapi should handle pagination
            tracks = list(playlist.tracks())
            log(f"  - Loaded {len(tracks)} tracks from playlist")
            return tracks
        except Exception as e:
            log(f"  - Error getting playlist tracks: {e}")
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
