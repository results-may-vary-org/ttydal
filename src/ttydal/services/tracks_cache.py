"""Singleton cache for album/playlist tracks.

Uses a custom LRU cache limited by total track count (not album count).
This allows the search feature to search across all loaded albums.

Note: We don't cache the albums list because:
1. Users rarely reload it after initial load
2. It's a small dataset that loads quickly
3. Changes to favorites/playlists should reflect immediately
"""

import threading
import time
from collections import OrderedDict

from ttydal.logger import log


class TracksCache:
    """Singleton cache for album/playlist tracks.

    Uses a custom LRU cache limited by total track count.
    This handles albums with varying sizes (some have 5000+ tracks).
    Thread-safe singleton using double-checked locking.
    """

    _instance = None
    _lock = threading.Lock()

    # Default limits
    DEFAULT_MAX_TRACKS = 50000  # 50k tracks max
    DEFAULT_TTL = 3600  # 1 hour

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:  # Double-checked locking
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, max_tracks: int | None = None, ttl: int | None = None):
        if self._initialized:
            return
        self._cache: OrderedDict[str, list[dict]] = OrderedDict()
        self._timestamps: dict[str, float] = {}  # Track when items were added
        self.max_tracks = max_tracks or self.DEFAULT_MAX_TRACKS
        self.ttl = ttl or self.DEFAULT_TTL
        self._initialized = True
        log(
            f"TracksCache: Initialized with max_tracks={self.max_tracks}, ttl={self.ttl}"
        )

    def _expire_old_entries(self) -> None:
        """Remove entries that have exceeded TTL."""
        now = time.time()
        expired = [
            item_id
            for item_id, timestamp in self._timestamps.items()
            if now - timestamp > self.ttl
        ]
        for item_id in expired:
            self._remove_entry(item_id)
            log(f"TracksCache: Expired {item_id} (TTL exceeded)")

    def _remove_entry(self, item_id: str) -> int:
        """Remove an entry and return the number of tracks removed."""
        if item_id not in self._cache:
            return 0
        track_count = len(self._cache[item_id])
        del self._cache[item_id]
        self._timestamps.pop(item_id, None)
        return track_count

    def _get_total_tracks(self) -> int:
        """Get total number of tracks in cache."""
        return sum(len(tracks) for tracks in self._cache.values())

    def get(self, item_id: str) -> list[dict] | None:
        """Get cached tracks for an album/playlist.

        Args:
            item_id: The album/playlist ID

        Returns:
            List of track dictionaries or None if not cached
        """
        self._expire_old_entries()

        if item_id not in self._cache:
            return None

        # Move to end for LRU (O(1) with OrderedDict)
        self._cache.move_to_end(item_id)

        return self._cache.get(item_id)

    def set(self, item_id: str, tracks: list[dict]) -> None:
        """Cache tracks for an album/playlist.

        Evicts oldest entries (LRU) if adding would exceed max_tracks.

        Args:
            item_id: The album/playlist ID
            tracks: List of track dictionaries
        """
        self._expire_old_entries()

        new_track_count = len(tracks)

        # If this item is already cached, remove it first
        if item_id in self._cache:
            self._remove_entry(item_id)

        # Evict oldest entries until we have room
        current_total = self._get_total_tracks()
        while current_total + new_track_count > self.max_tracks and self._cache:
            # Get oldest entry (first item in OrderedDict)
            oldest_id = next(iter(self._cache))
            evicted_count = self._remove_entry(oldest_id)
            current_total -= evicted_count
            log(f"TracksCache: Evicted {oldest_id} ({evicted_count} tracks) - LRU")

        # Add new entry (appends to end of OrderedDict)
        self._cache[item_id] = tracks
        self._timestamps[item_id] = time.time()
        log(f"TracksCache: Cached {len(tracks)} tracks for {item_id}")

    def get_all_tracks(self) -> list[dict]:
        """Get all cached tracks from all albums (for search).

        Returns:
            List of all cached tracks with _cache_album_id added to each
        """
        self._expire_old_entries()

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
            self._remove_entry(item_id)
            log(f"TracksCache: Invalidated cache for {item_id}")

    def clear(self) -> None:
        """Clear the entire cache."""
        self._cache.clear()
        self._timestamps.clear()
        log("TracksCache: Cache cleared")

    def get_stats(self) -> dict:
        """Get cache statistics.

        Returns:
            Dict with albums_count, tracks_count, max_tracks, ttl
        """
        self._expire_old_entries()
        total_tracks = self._get_total_tracks()
        return {
            "albums_count": len(self._cache),
            "tracks_count": total_tracks,
            "max_tracks": self.max_tracks,
            "ttl": self.ttl,
        }
