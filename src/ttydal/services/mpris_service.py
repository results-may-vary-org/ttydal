"""MPRIS2 D-Bus service for ttydal using the mpris_server library.

Runs a GLib event loop in a background daemon thread. The adapter reads
live state from MpvPlaybackEngine; incoming D-Bus commands (play/pause/
next/prev/seek) are forwarded to the engine or navigation callbacks.
Emits D-Bus property changes when mpv fires its pause and playlist-pos
callbacks.

Architecture
------------
- GLib daemon thread: owns the D-Bus session (server.loop(background=True))
- mpv C thread: fires on_pos_change / on_pause_change callbacks
- Textual/asyncio thread: owns UI — never called from here

Thread safety: mpv callbacks call events.on_title() / events.on_playpause()
directly. GLib handles cross-thread signalling internally. D-Bus command
callbacks (play/pause/next/prev) write mpv properties — safe from any thread.
"""

from __future__ import annotations

from typing import Callable

from ttydal.logger import log


class MprisService:
    """Owns the mpris_server Server lifetime and wires engine callbacks.

    Args:
        engine: The singleton MpvPlaybackEngine instance.
    """

    def __init__(self, engine) -> None:
        self._engine = engine
        self._server = None
        self._adapter = None
        self._started = False

    def start(self) -> None:
        """Start the GLib D-Bus loop in a background daemon thread.

        Safe to call more than once — subsequent calls are no-ops.
        """
        if self._started:
            return
        try:
            from mpris_server import Server, MprisAdapter, PlayState
            from ttydal.config import ConfigManager

            engine = self._engine

            class TidalMprisAdapter(MprisAdapter):
                """Bridges MpvPlaybackEngine state to the MPRIS D-Bus interface."""

                # Navigation callables — set via MprisService.set_navigation_callbacks()
                _on_next: Callable | None = None
                _on_prev: Callable | None = None

                def __init__(self) -> None:
                    super().__init__("ttydal")

                # ---- State reads (called from GLib thread) -------------------

                def get_playstate(self) -> PlayState:
                    if engine.mpv is None:
                        return PlayState.STOPPED
                    if engine.mpv.time_pos is None:
                        return PlayState.STOPPED
                    return PlayState.PAUSED if engine.mpv.pause else PlayState.PLAYING

                def metadata(self) -> dict:
                    track = engine.get_current_track()
                    if not track:
                        return {}
                    track_id = str(track.get("id", "0"))
                    duration_s = track.get("duration", 0) or 0
                    return {
                        "mpris:trackid": f"/org/ttydal/track/{track_id}",
                        "mpris:length": int(duration_s * 1_000_000),
                        "mpris:artUrl": track.get("cover_url") or "",
                        "xesam:title": track.get("name") or "",
                        "xesam:artist": [track.get("artist") or ""],
                        "xesam:album": track.get("album") or "",
                        "xesam:url": f"tidal://{track_id}",
                    }

                def get_current_position(self) -> int:
                    return int(engine.get_time_pos() * 1_000_000)

                def can_play(self) -> bool:         return True
                def can_pause(self) -> bool:        return True
                def can_seek(self) -> bool:         return True
                def can_control(self) -> bool:      return True
                def can_go_next(self) -> bool:      return True
                def can_go_previous(self) -> bool:  return True

                def get_shuffle(self) -> bool:
                    return ConfigManager().shuffle

                def is_repeating(self) -> bool:  return False
                def is_playlist(self) -> bool:   return False
                def get_rate(self) -> float:      return 1.0
                def get_volume(self) -> float:    return 1.0

                # ---- Incoming D-Bus commands (called from GLib thread) -------

                def play(self) -> None:
                    engine.resume()

                def pause(self) -> None:
                    engine.pause()

                def resume(self) -> None:
                    engine.resume()

                def stop(self) -> None:
                    engine.stop()

                def playpause(self) -> None:
                    engine.toggle_pause()

                def next(self) -> None:
                    if self._on_next:
                        self._on_next()

                def previous(self) -> None:
                    if self._on_prev:
                        self._on_prev()

                def seek(self, time: int, track_id=None) -> None:
                    """Seek to an absolute position (microseconds)."""
                    current_us = self.get_current_position()
                    delta_s = (time - current_us) / 1_000_000
                    engine.seek(delta_s)

                # ---- RootAdapter ---------------------------------------------

                def quit(self) -> None:
                    pass  # app handles its own quit

                def get_desktop_entry(self) -> str:
                    return ""

            self._adapter = TidalMprisAdapter()
            self._server = Server(name="ttydal", adapter=self._adapter)
            self._server.loop(background=True)

            # Register engine callbacks to push state changes to D-Bus
            engine.register_callback("on_pos_change", self._on_pos_change)
            engine.register_callback("on_pause_change", self._on_pause_change)

            self._started = True
            log("MprisService: started, registered on D-Bus as 'ttydal'")

        except Exception as e:
            log(f"MprisService: failed to start — {e}")

    def set_navigation_callbacks(
        self,
        on_next: Callable,
        on_prev: Callable,
    ) -> None:
        """Wire TracksList navigation so MPRIS next/prev sets _user_navigating.

        Args:
            on_next: Called when D-Bus Next is received (e.g. TracksList.play_next_track).
            on_prev: Called when D-Bus Previous is received.
        """
        if self._adapter is not None:
            self._adapter._on_next = on_next
            self._adapter._on_prev = on_prev

    def notify_track_changed(self) -> None:
        """Push updated metadata and playback status to D-Bus clients.

        Call this after an explicit track selection so widgets and playerctl
        refresh immediately rather than waiting for the next on_pos_change.
        """
        if self._server and self._server.events:
            try:
                self._server.events.on_title()
                self._server.events.on_playpause()
            except Exception as e:
                log(f"MprisService.notify_track_changed: {e}")

    def shutdown(self) -> None:
        """Stop the D-Bus server (daemon thread dies on process exit anyway)."""
        if self._server:
            try:
                self._server.quit()
            except Exception:
                pass
        log("MprisService: stopped")

    # ---- Engine callback handlers (called from mpv C thread) -----------------

    def _on_pos_change(self, _index: int) -> None:
        """Push new metadata and playback state when the playlist position changes."""
        if self._server and self._server.events:
            try:
                self._server.events.on_title()
                self._server.events.on_playpause()
            except Exception as e:
                log(f"MprisService._on_pos_change: {e}")

    def _on_pause_change(self, _paused: bool) -> None:
        """Push playback status change when mpv pauses or resumes."""
        if self._server and self._server.events:
            try:
                self._server.events.on_playpause()
            except Exception as e:
                log(f"MprisService._on_pause_change: {e}")
