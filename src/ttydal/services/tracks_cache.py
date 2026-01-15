"""Singleton cache for album/playlist tracks.

Uses TTLCache to store tracks per album/playlist ID.
This allows the search feature to search across all loaded albums.

Note: We don't cache the albums list because:
1. Users rarely reload it after initial load
2. It's a small dataset that loads quickly
3. Changes to favorites/playlists should reflect immediately
"""

from cachetools import TTLCache

from ttydal.logger import log


class TracksCache:
    """Singleton cache for album/playlist tracks.

    Uses TTLCache to store tracks per album/playlist ID.
    This allows the search feature to search across all loaded albums.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        # Cache up to 100 albums, TTL of 1 hour
        self._cache: TTLCache = TTLCache(maxsize=100, ttl=3600)
        self._initialized = True
        log("TracksCache: Initialized with maxsize=100, ttl=3600")

    def get(self, item_id: str) -> list[dict] | None:
        """Get cached tracks for an album/playlist.

        Args:
            item_id: The album/playlist ID

        Returns:
            List of track dictionaries or None if not cached
        """
        return self._cache.get(item_id)

    def set(self, item_id: str, tracks: list[dict]) -> None:
        """Cache tracks for an album/playlist.

        Args:
            item_id: The album/playlist ID
            tracks: List of track dictionaries
        """
        self._cache[item_id] = tracks
        log(f"TracksCache: Cached {len(tracks)} tracks for {item_id}")

    def get_all_tracks(self) -> list[dict]:
        """Get all cached tracks from all albums (for search).

        Returns:
            List of all cached tracks with _cache_album_id added to each
        """
        all_tracks = []
        for item_id, tracks in self._cache.items():
            for track in tracks:
                track_copy = track.copy()
                track_copy["_cache_album_id"] = item_id
                all_tracks.append(track_copy)
        log(f"TracksCache: Retrieved {len(all_tracks)} total tracks from cache")
        return all_tracks

    def invalidate(self, item_id: str) -> None:
        """Remove a specific album/playlist from the cache.

        Args:
            item_id: The album/playlist ID to invalidate
        """
        if item_id in self._cache:
            del self._cache[item_id]
            log(f"TracksCache: Invalidated cache for {item_id}")

    def clear(self) -> None:
        """Clear the entire cache."""
        self._cache.clear()
        log("TracksCache: Cache cleared")
