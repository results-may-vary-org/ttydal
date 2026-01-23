"""Service layer for ttydal.

This module separates data fetching logic from UI components,
providing clean architecture and better maintainability.

Data Structures:
----------------

AlbumDict:
    {
        "id": str,           # Album/playlist ID
        "name": str,         # Album/playlist name (for albums: "Album - Artist")
        "type": str,         # "album", "playlist", or "favorites"
        "count": int,        # Number of tracks
        "cover_url": str | None,  # Cover art URL (80x80 for lists)
    }

TrackDict:
    {
        "id": str,           # Track ID
        "name": str,         # Track name
        "artist": str,       # Artist name
        "album": str,        # Album name
        "duration": int,     # Duration in seconds
        "index": int,        # Track index in list (1-based)
        "cover_url": str | None,  # Cover art URL (80x80 for lists, 320x320 for player)
    }
"""

from typing import TypedDict
import asyncio

from ttydal.exceptions import TidalServiceError, DataFetchError
from ttydal.logger import log
from ttydal.services.playback_service import PlaybackService, PlaybackResult
from ttydal.services.tracks_cache import TracksCache


class AlbumDict(TypedDict, total=False):
    """Type definition for album/playlist data."""

    id: str
    name: str
    type: str  # "album", "playlist", or "favorites"
    count: int
    cover_url: str | None


class TrackDict(TypedDict, total=False):
    """Type definition for track data."""

    id: str
    name: str
    artist: str
    album: str
    duration: int
    index: int
    cover_url: str | None


class AlbumsService:
    """Service for fetching album and playlist data."""

    def __init__(self, tidal_client):
        """Initialize albums service.

        Args:
            tidal_client: TidalClient instance
        """
        self.tidal = tidal_client

    async def get_favorites_info(self) -> AlbumDict:
        """Get favorites track count and info.

        Returns:
            AlbumDict with favorites info
        """
        try:
            favorites = await asyncio.to_thread(self.tidal.get_user_favorites)
            count = len(favorites)
            return {
                "id": "favorites",
                "name": "My Tracks",
                "type": "favorites",
                "count": count,
                "cover_url": None,  # Favorites doesn't have a cover image
            }
        except Exception as e:
            log(f"AlbumsService.get_favorites_info error: {e}")
            raise TidalServiceError(str(e), "get favorites info")

    async def get_user_playlists(self) -> list[AlbumDict]:
        """Get user playlists.

        Returns:
            List of playlist dictionaries (AlbumDict)
        """
        try:
            playlists = await asyncio.to_thread(self.tidal.get_user_playlists)
            result = []
            for playlist in playlists:
                # Get cover art URL (80x80 for list display)
                try:
                    cover_url = playlist.image(80)
                except Exception:
                    cover_url = None
                result.append(
                    {
                        "id": playlist.id,
                        "name": playlist.name,
                        "type": "playlist",
                        "count": playlist.num_tracks,
                        "cover_url": cover_url,
                    }
                )
            return result
        except Exception as e:
            log(f"AlbumsService.get_user_playlists error: {e}")
            raise TidalServiceError(str(e), "get user playlists")

    async def get_user_albums(self) -> list[AlbumDict]:
        """Get user albums.

        Returns:
            List of album dictionaries (AlbumDict)
        """
        try:
            albums = await asyncio.to_thread(self.tidal.get_user_albums)
            result = []
            for album in albums:
                # Get cover art URL (80x80 for list display)
                try:
                    cover_url = album.image(80)
                except Exception:
                    cover_url = None
                result.append(
                    {
                        "id": album.id,
                        "name": f"{album.name} - {album.artist.name}",
                        "type": "album",
                        "count": album.num_tracks,
                        "cover_url": cover_url,
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

    def _track_to_dict(self, track, index: int) -> TrackDict:
        """Convert a Tidal track object to a dictionary.

        Args:
            track: Tidal track object
            index: Track index in the list

        Returns:
            TrackDict representation of the track
        """
        # Get cover art URL from track's album (80x80 for list, can request larger for player)
        try:
            cover_url = track.album.image(80)
        except Exception:
            cover_url = None

        return {
            "id": str(track.id),
            "name": track.name,
            "artist": track.artist.name,
            "album": track.album.name,
            "duration": track.duration,
            "index": index,
            "cover_url": cover_url,
        }

    async def get_favorites_tracks(self) -> list[TrackDict]:
        """Get all favorite tracks.

        Returns:
            List of track dictionaries (TrackDict)
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

    async def get_playlist_tracks(self, playlist_id: str) -> list[TrackDict]:
        """Get tracks for a specific playlist.

        Args:
            playlist_id: The playlist ID

        Returns:
            List of track dictionaries (TrackDict)
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

    async def get_album_tracks(self, album_id: str) -> list[TrackDict]:
        """Get tracks for a specific album.

        Args:
            album_id: The album ID

        Returns:
            List of track dictionaries (TrackDict)
        """
        try:
            tracks = await asyncio.to_thread(self.tidal.get_album_tracks, album_id)
            return [
                self._track_to_dict(track, idx) for idx, track in enumerate(tracks, 1)
            ]
        except Exception as e:
            log(f"TracksService.get_album_tracks error: {e}")
            raise TidalServiceError(str(e), "get album tracks")


# Export services, types, and exceptions
__all__ = [
    "AlbumsService",
    "TracksService",
    "TracksCache",
    "PlaybackService",
    "PlaybackResult",
    "TidalServiceError",
    "DataFetchError",
    "AlbumDict",
    "TrackDict",
]
