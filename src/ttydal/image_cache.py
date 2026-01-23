"""Image cache for cover art.

This module provides functionality to download and cache cover art images
from URLs for display in the terminal using textual-image.

Cache is stored in ~/.cache/ttydal/images/ for persistence across sessions.
Images are only loaded when they become visible in the UI (lazy loading).
"""

import asyncio
from io import BytesIO
from pathlib import Path
from typing import Optional
import hashlib
import requests
from PIL import Image as PILImage

from ttydal.logger import log


class ImageCache:
    """Singleton cache for cover art images.

    Downloads images from URLs and caches them locally for efficient reuse.
    Uses PIL to load images which can then be passed to textual-image widgets.

    Cache location: ~/.cache/ttydal/images/
    """

    _instance = None
    _cache_dir: Path
    _memory_cache: dict[str, PILImage.Image]

    def __new__(cls):
        """Ensure only one instance exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the image cache."""
        if self._initialized:
            return

        # Use ~/.cache/ttydal/images/ for persistent cache
        self._cache_dir = Path.home() / ".cache" / "ttydal" / "images"
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._memory_cache = {}
        self._initialized = True
        log(f"ImageCache initialized, cache dir: {self._cache_dir}")

    def _url_to_cache_key(self, url: str) -> str:
        """Convert URL to cache key (hash)."""
        return hashlib.md5(url.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get cache file path for a cache key."""
        return self._cache_dir / f"{cache_key}.jpg"

    def get_image_sync(self, url: str) -> Optional[PILImage.Image]:
        """Get image from URL synchronously.

        Checks memory cache first, then disk cache, then downloads.

        Args:
            url: URL of the image to fetch

        Returns:
            PIL Image or None if failed
        """
        if not url:
            return None

        cache_key = self._url_to_cache_key(url)

        # Check memory cache
        if cache_key in self._memory_cache:
            return self._memory_cache[cache_key]

        # Check disk cache
        cache_path = self._get_cache_path(cache_key)
        if cache_path.exists():
            try:
                img = PILImage.open(cache_path)
                img.load()  # Force load to catch any issues
                self._memory_cache[cache_key] = img
                return img
            except Exception as e:
                log(f"ImageCache: Failed to load cached image: {e}")
                cache_path.unlink(missing_ok=True)

        # Download image
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            img = PILImage.open(BytesIO(response.content))
            img.load()  # Force load to validate

            # Save to disk cache
            img.save(cache_path, "JPEG")

            # Store in memory cache
            self._memory_cache[cache_key] = img
            return img

        except Exception as e:
            log(f"ImageCache: Failed to download image from {url}: {e}")
            return None

    async def get_image(self, url: str) -> Optional[PILImage.Image]:
        """Get image from URL asynchronously.

        Args:
            url: URL of the image to fetch

        Returns:
            PIL Image or None if failed
        """
        if not url:
            return None

        # Run the sync version in a thread pool
        return await asyncio.to_thread(self.get_image_sync, url)

    def clear_memory_cache(self) -> None:
        """Clear the in-memory image cache."""
        self._memory_cache.clear()
        log("ImageCache: Memory cache cleared")

    def clear_all(self) -> None:
        """Clear both memory and disk caches."""
        self._memory_cache.clear()

        # Remove all cached files
        for cache_file in self._cache_dir.glob("*.jpg"):
            cache_file.unlink(missing_ok=True)

        log("ImageCache: All caches cleared")

    def get_stats(self) -> dict:
        """Get cache statistics.

        Returns:
            Dict with:
                - count: Number of cached images on disk
                - size_bytes: Total size of cached images in bytes
                - size_mb: Total size in megabytes (rounded to 2 decimals)
                - memory_count: Number of images in memory cache
        """
        count = 0
        size_bytes = 0

        for cache_file in self._cache_dir.glob("*.jpg"):
            count += 1
            try:
                size_bytes += cache_file.stat().st_size
            except OSError:
                pass

        return {
            "count": count,
            "size_bytes": size_bytes,
            "size_mb": round(size_bytes / (1024 * 1024), 2),
            "memory_count": len(self._memory_cache),
        }
