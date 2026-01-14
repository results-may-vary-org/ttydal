"""Service layer for ttydal.

This module separates data fetching logic from UI components,
providing clean architecture and better maintainability.
"""

from typing import List, Dict, Any, Optional, Tuple
import asyncio

# Handle tidalapi imports properly - import at runtime to handle older versions
import tidalapi

from ttydal.config import ConfigManager
from ttydal.exceptions import TidalServiceError, DataFetchError
from ttydal.logger import log


class AlbumsService:
    """Service for fetching album and playlist data."""

    def __init__(self, tidal_client):
        """Initialize albums service.

        Args:
            tidal_client: TidalClient instance
        """
        self.tidal = tidal_client

    async def get_favorites_info(self) -> Dict[str, Any]:
        """Get favorites track count and info.

        Returns:
            Dictionary with favorites info
        """
        try:
            loop = asyncio.get_event_loop()
            favorites = await loop.run_in_executor(
                None, lambda: self.tidal.get_session().user.favorites.tracks()
            )
            count = len(list(favorites))
            return {
                "id": "favorites",
                "name": "My Tracks",
                "type": "favorites",
                "count": count,
            }
        except Exception as e:
            log(f"AlbumsService.get_favorites_info error: {e}")
            raise TidalServiceError(str(e), "get favorites info")

    async def get_user_playlists(self) -> List[Dict[str, Any]]:
        """Get user playlists.

        Returns:
            List of playlist dictionaries
        """
        try:
            loop = asyncio.get_event_loop()
            playlists = await loop.run_in_executor(
                None, lambda: self.tidal.get_session().user.playlists()
            )
            result = []
            for playlist in playlists:
                result.append({
                    "id": playlist.id,
                    "name": playlist.name,
                    "type": "playlist",
                    "count": playlist.num_tracks,
                })
            return result
        except Exception as e:
            log(f"AlbumsService.get_user_playlists error: {e}")
            raise TidalServiceError(str(e), "get user playlists")

    async def get_user_albums(self) -> List[Dict[str, Any]]:
        """Get user albums.

        Returns:
            List of album dictionaries
        """
        try:
            loop = asyncio.get_event_loop()
            albums = await loop.run_in_executor(
                None, lambda: self.tidal.get_session().user.favorites.albums()
            )
            result = []
            for album in albums:
                result.append({
                    "id": album.id,
                    "name": f"{album.name} - {album.artist.name}",
                    "type": "album",
                    "count": album.num_tracks,
                })
            return result
        except Exception as e:
            log(f"AlbumsService.get_user_albums error: {e}")
            raise TidalServiceError(str(e), "get user albums")


class TracksService:
    """Service for fetching track data."""

    def __init__(self, tidal_client):
        """Initialize tracks service.

        Args:
            tidal_client: TidalClient instance
        """
        self.tidal = tidal_client
        self.config = ConfigManager()

    async def get_favorites_tracks(self) -> List[Dict[str, Any]]:
        """Get all favorite tracks.

        Returns:
            List of track dictionaries
        """
        try:
            loop = asyncio.get_event_loop()
            favorites = await loop.run_in_executor(
                None, lambda: list(self.tidal.get_session().user.favorites.tracks())
            )

            # Sort by added date if available (newest first)
            if hasattr(favorites[0] if favorites else None, 'user_date_added'):
                favorites.sort(key=lambda t: t.user_date_added if hasattr(t, 'user_date_added') else '', reverse=True)

            result = []
            for idx, track in enumerate(favorites, 1):
                result.append({
                    "id": str(track.id),
                    "name": track.name,
                    "artist": track.artist.name,
                    "album": track.album.name,
                    "duration": track.duration,
                    "index": idx,
                })
            return result
        except Exception as e:
            log(f"TracksService.get_favorites_tracks error: {e}")
            raise TidalServiceError(str(e), "get favorite tracks")

    async def get_playlist_tracks(self, playlist_id: str) -> List[Dict[str, Any]]:
        """Get tracks for a specific playlist.

        Args:
            playlist_id: The playlist ID

        Returns:
            List of track dictionaries
        """
        try:
            loop = asyncio.get_event_loop()
            playlist = await loop.run_in_executor(
                None, lambda: self.tidal.get_session().playlist(playlist_id)
            )
            tracks = await loop.run_in_executor(None, lambda: playlist.tracks())

            result = []
            for idx, track in enumerate(tracks, 1):
                result.append({
                    "id": str(track.id),
                    "name": track.name,
                    "artist": track.artist.name,
                    "album": track.album.name,
                    "duration": track.duration,
                    "index": idx,
                })
            return result
        except Exception as e:
            log(f"TracksService.get_playlist_tracks error: {e}")
            raise TidalServiceError(str(e), "get playlist tracks")

    async def get_album_tracks(self, album_id: str) -> List[Dict[str, Any]]:
        """Get tracks for a specific album.

        Args:
            album_id: The album ID

        Returns:
            List of track dictionaries
        """
        try:
            loop = asyncio.get_event_loop()
            album = await loop.run_in_executor(
                None, lambda: self.tidal.get_session().album(album_id)
            )
            tracks = await loop.run_in_executor(None, lambda: album.tracks())

            result = []
            for idx, track in enumerate(tracks, 1):
                result.append({
                    "id": str(track.id),
                    "name": track.name,
                    "artist": track.artist.name,
                    "album": track.album.name,
                    "duration": track.duration,
                    "index": idx,
                })
            return result
        except Exception as e:
            log(f"TracksService.get_album_tracks error: {e}")
            raise TidalServiceError(str(e), "get album tracks")


# Export services and exceptions
__all__ = ["AlbumsService", "TracksService", "TidalServiceError", "DataFetchError"]
