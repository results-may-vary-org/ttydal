"""Playback service for managing track playback."""

from dataclasses import dataclass
from typing import Any

from ttydal.logger import log


@dataclass
class PlaybackResult:
    """Result of a playback operation."""

    success: bool
    stream_metadata: dict[str, Any] | None = None
    error_message: str | None = None
    fallback_applied: bool = False
    requested_quality: str | None = None
    actual_quality: str | None = None
    tried_qualities: list[str] | None = None
    vibrant_color: str | None = None  # Album's vibrant color (e.g., "#f2d869")


class PlaybackService:
    """Service for handling track playback operations."""

    def __init__(self, tidal_client, player):
        """Initialize playback service.

        Args:
            tidal_client: TidalClient instance for fetching track URLs
            player: Player instance for audio playback
        """
        self.tidal = tidal_client
        self.player = player

    def play_track(
        self,
        track_id: str,
        track_info: dict[str, Any],
        quality: str = "high",
        fetch_vibrant_color: bool = False,
        prefetched_url: str | None = None,
        prefetched_metadata: dict | None = None,
        prefetched_error_info: dict | None = None,
    ) -> PlaybackResult:
        """Play a track by ID with quality setting.

        Args:
            track_id: The track ID to play
            track_info: Track metadata dictionary (name, artist, etc.)
            quality: Quality setting ('max', 'high', or 'low')
            fetch_vibrant_color: Whether to include the album's vibrant color
            prefetched_url: Pre-fetched stream URL (skips API call if provided)
            prefetched_metadata: Pre-fetched stream metadata
            prefetched_error_info: Pre-fetched error info dict

        Returns:
            PlaybackResult with success status and metadata
        """
        log("=" * 80)
        log("PlaybackService.play_track() called")
        log(f"  - Track: {track_info.get('name', 'Unknown')}")
        log(f"  - Track ID: {track_id}")
        log(f"  - Artist: {track_info.get('artist', 'Unknown')}")
        log(f"  - Requested quality: {quality}")

        # Use pre-fetched data if available, otherwise fetch from Tidal
        if prefetched_url and prefetched_metadata:
            log("  - Using pre-fetched URL (skipping API call)")
            track_url = prefetched_url
            stream_metadata = prefetched_metadata
            error_info = prefetched_error_info or {}
        else:
            log("  - Requesting track URL and metadata from Tidal...")
            track_url, stream_metadata, error_info = self.tidal.get_track_url(
                track_id, quality
            )

        if track_url and stream_metadata:
            log("  - Got track URL, calling player.play()")

            # Add stream metadata to track info
            track_info_with_metadata = track_info.copy()
            track_info_with_metadata["stream_metadata"] = stream_metadata

            # Start playback
            self.player.play(track_url, track_info_with_metadata)

            # Get vibrant color from the same API response (no extra call needed)
            vibrant_color = None
            if fetch_vibrant_color:
                vibrant_color = error_info.get("vibrant_color")
                log(f"  - Vibrant color: {vibrant_color}")

            log("  - Playback started successfully")
            log("=" * 80)

            return PlaybackResult(
                success=True,
                stream_metadata=stream_metadata,
                fallback_applied=error_info.get("fallback_applied", False),
                requested_quality=error_info.get("requested_quality"),
                actual_quality=error_info.get("actual_quality"),
                tried_qualities=error_info.get("tried_qualities"),
                vibrant_color=vibrant_color,
            )

        # Failed to get track URL
        log("  - Failed to get track URL or metadata")
        log("=" * 80)

        return PlaybackResult(
            success=False,
            error_message=error_info.get("error", "Unknown error"),
            requested_quality=error_info.get("requested_quality"),
            tried_qualities=error_info.get("tried_qualities"),
        )
