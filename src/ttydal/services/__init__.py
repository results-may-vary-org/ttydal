"""Service layer for ttydal.

This module separates data fetching logic from UI components,
providing clean architecture and better maintainability.
"""

from typing import Any
import asyncio

from ttydal.exceptions import TidalServiceError, DataFetchError
from ttydal.logger import log
from ttydal.services.playback_service import PlaybackService, PlaybackResult
from ttydal.services.tracks_cache import TracksCache


class AlbumsService:
    """Service for fetching album and playlist data."""

    def __init__(self, tidal_client):
        """Initialize albums service.

        Args:
            tidal_client: TidalClient instance
        """
        self.tidal = tidal_client

    async def get_favorites_info(self) -> dict[str, Any]:
        """Get favorites track count and info.

        Returns:
            Dictionary with favorites info
        """
        try:
            favorites = await asyncio.to_thread(self.tidal.get_user_favorites)
            count = len(favorites)
            return {
                "id": "favorites",
                "name": "My Tracks",
                "type": "favorites",
                "count": count,
            }
        except Exception as e:
            log(f"AlbumsService.get_favorites_info error: {e}")
            raise TidalServiceError(str(e), "get favorites info")

    async def get_user_playlists(self) -> list[dict[str, Any]]:
        """Get user playlists.

        Returns:
            List of playlist dictionaries
        """
        try:
            playlists = await asyncio.to_thread(self.tidal.get_user_playlists)
            result = []
            for playlist in playlists:
                result.append(
                    {
                        "id": playlist.id,
                        "name": playlist.name,
                        "type": "playlist",
                        "count": playlist.num_tracks,
                    }
                )
            return result
        except Exception as e:
            log(f"AlbumsService.get_user_playlists error: {e}")
            raise TidalServiceError(str(e), "get user playlists")

    async def get_user_albums(self) -> list[dict[str, Any]]:
        """Get user albums.

        Returns:
            List of album dictionaries
        """
        try:
            albums = await asyncio.to_thread(self.tidal.get_user_albums)
            result = []
            for album in albums:
                result.append(
                    {
                        "id": album.id,
                        "name": f"{album.name} - {album.artist.name}",
                        "type": "album",
                        "count": album.num_tracks,
                    }
                )
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

    def _track_to_dict(self, track, index: int) -> dict[str, Any]:
        """Convert a Tidal track object to a dictionary.

        Args:
            track: Tidal track object
            index: Track index in the list

        Returns:
            Dictionary representation of the track
        """
        return {
            "id": str(track.id),
            "name": track.name,
            "artist": track.artist.name,
            "album": track.album.name,
            "duration": track.duration,
            "index": index,
        }

    async def get_favorites_tracks(self) -> list[dict[str, Any]]:
        """Get all favorite tracks.

        Returns:
            List of track dictionaries
        """
        try:
            # get_user_favorites() already returns sorted by date
            favorites = await asyncio.to_thread(self.tidal.get_user_favorites)
            return [
                self._track_to_dict(track, idx)
                for idx, track in enumerate(favorites, 1)
            ]
        except Exception as e:
            log(f"TracksService.get_favorites_tracks error: {e}")
            raise TidalServiceError(str(e), "get favorite tracks")

    async def get_playlist_tracks(self, playlist_id: str) -> list[dict[str, Any]]:
        """Get tracks for a specific playlist.

        Args:
            playlist_id: The playlist ID

        Returns:
            List of track dictionaries
        """
        try:
            tracks = await asyncio.to_thread(
                self.tidal.get_playlist_tracks, playlist_id
            )
            return [
                self._track_to_dict(track, idx) for idx, track in enumerate(tracks, 1)
            ]
        except Exception as e:
            log(f"TracksService.get_playlist_tracks error: {e}")
            raise TidalServiceError(str(e), "get playlist tracks")

    async def get_album_tracks(self, album_id: str) -> list[dict[str, Any]]:
        """Get tracks for a specific album.

        Args:
            album_id: The album ID

        Returns:
            List of track dictionaries
        """
        try:
            tracks = await asyncio.to_thread(self.tidal.get_album_tracks, album_id)
            return [
                self._track_to_dict(track, idx) for idx, track in enumerate(tracks, 1)
            ]
        except Exception as e:
            log(f"TracksService.get_album_tracks error: {e}")
            raise TidalServiceError(str(e), "get album tracks")


# Export services and exceptions
__all__ = [
    "AlbumsService",
    "TracksService",
    "TracksCache",
    "PlaybackService",
    "PlaybackResult",
    "TidalServiceError",
    "DataFetchError",
]
