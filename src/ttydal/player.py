"""MPV player singleton wrapper for ttydal."""

from typing import Callable

import mpv
from ttydal.logger import log


class Player:
    """Singleton MPV player wrapper."""

    _instance = None

    def __new__(cls):
        """Ensure only one instance exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the MPV player."""
        if self._initialized:
            return

        log("Player.__init__() called")
        log("  - MPV will be lazy-loaded on first use")
        self.mpv = None
        self._current_track = None
        self._callbacks: dict[str, list[Callable]] = {
            "on_track_end": [],
            "on_time_pos_change": []
        }
        self._initialized = True
        log("Player.__init__() completed")

    def _ensure_mpv(self) -> None:
        """Ensure MPV is initialized (lazy loading)."""
        if self.mpv is not None:
            return

        self.mpv = mpv.MPV(video=False, ytdl=False)

        # Register MPV property observers
        @self.mpv.property_observer('time-pos')
        def time_observer(_name, value):
            """Observe playback time position."""
            if value is not None:
                for callback in self._callbacks["on_time_pos_change"]:
                    callback(value)

        @self.mpv.event_callback('end-file')
        def end_file_callback(event):
            """Handle track end event."""
            for callback in self._callbacks["on_track_end"]:
                callback()

    def play(self, url: str, track_info: dict | None = None) -> None:
        """Play a track from URL.

        Args:
            url: The audio URL to play
            track_info: Optional track metadata
        """
        self._ensure_mpv()
        self._current_track = track_info
        self.mpv.play(url)

    def pause(self) -> None:
        """Pause playback."""
        self._ensure_mpv()
        self.mpv.pause = True

    def resume(self) -> None:
        """Resume playback."""
        self._ensure_mpv()
        self.mpv.pause = False

    def toggle_pause(self) -> None:
        """Toggle pause/play."""
        self._ensure_mpv()
        self.mpv.pause = not self.mpv.pause

    def stop(self) -> None:
        """Stop playback."""
        if self.mpv is None:
            return
        self.mpv.stop()

    def seek(self, seconds: float) -> None:
        """Seek relative to current position.

        Args:
            seconds: Number of seconds to seek (positive or negative)
        """
        if self.mpv is None:
            return
        try:
            self.mpv.seek(seconds, reference='relative')
        except Exception:
            pass  # Ignore seek errors

    def is_playing(self) -> bool:
        """Check if player is currently playing.

        Returns:
            True if playing, False otherwise
        """
        if self.mpv is None:
            return False
        return not self.mpv.pause and self.mpv.time_pos is not None

    def get_time_pos(self) -> float:
        """Get current playback position in seconds.

        Returns:
            Current position in seconds or 0.0
        """
        if self.mpv is None:
            return 0.0
        return self.mpv.time_pos or 0.0

    def get_duration(self) -> float:
        """Get track duration in seconds.

        Returns:
            Duration in seconds or 0.0
        """
        if self.mpv is None:
            return 0.0
        return self.mpv.duration or 0.0

    def get_current_track(self) -> dict | None:
        """Get current track information.

        Returns:
            Track info dict or None
        """
        return self._current_track

    def register_callback(self, event: str, callback: Callable) -> None:
        """Register a callback for player events.

        Args:
            event: Event name ('on_track_end' or 'on_time_pos_change')
            callback: Callback function
        """
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    def shutdown(self) -> None:
        """Shutdown the player."""
        log("Player.shutdown() called")
        if self.mpv is None:
            log("  - MPV was never initialized, nothing to shutdown")
            return
        try:
            log("  - Stopping playback...")
            self.mpv.stop()
            log("  - Terminating MPV...")
            self.mpv.terminate()
            log("  - MPV terminated successfully")
        except Exception as e:
            log(f"  - Error during MPV shutdown: {e}")
        finally:
            self.mpv = None
            log("  - MPV reference cleared")
