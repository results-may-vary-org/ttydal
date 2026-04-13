"""MPRIS2 D-Bus service for ttydal using the mpris_server library.

Runs a GLib event loop in a background daemon thread. The adapter reads
live state from MpvPlaybackEngine; incoming D-Bus commands (play/pause/
next/prev/seek) are forwarded to the engine or navigation callbacks.
Emits D-Bus property changes when mpv fires its pause and time-pos
callbacks.

Architecture
------------
- GLib daemon thread: owns the D-Bus session (server.loop(background=True))
- mpv C thread: fires on_pause_change / on_time_pos_change callbacks
- Textual/asyncio thread: owns UI — calls notify_track_changed()

Signal emission
---------------
Server(events=None) by default — the library's EventAdapter is never wired.
We bypass it entirely and call dbus_emit_changes(server.player, props)
directly. g_dbus_connection_emit_signal() is thread-safe, so calling from
the mpv C thread or the Textual asyncio thread is safe.
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
        self._pending_playstate = False  # set by notify_track_changed, cleared on first position tick

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
                    if engine.mpv is None or engine.mpv.idle_active:
                        return PlayState.STOPPED
                    return PlayState.PAUSED if engine.mpv.pause else PlayState.PLAYING

                def metadata(self) -> dict:
                    track = engine.get_current_track()
                    if not track:
                        return {}
                    track_id = str(track.get("id", "0"))
                    duration_s = track.get("duration", 0)
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

            # mpris_server 0.9.6 bug: METADATA_TYPES maps TRACK_ID to DbusTypes.STRING ('s')
            # but the MPRIS2 spec requires type 'o' (D-Bus object path). KDE Plasma validates
            # this type strictly and silently drops the entire Metadata dict when it's wrong,
            # causing title/artist/cover/position to all disappear. Remove this patch when
            # the library fixes it (track: https://github.com/alexdelorenzo/mpris_server).
            from mpris_server.mpris.metadata import METADATA_TYPES, MetadataEntries
            from mpris_server.base import DbusTypes
            METADATA_TYPES[MetadataEntries.TRACK_ID] = DbusTypes.OBJ

            self._adapter = TidalMprisAdapter()
            self._server = Server(name="ttydal", adapter=self._adapter)
            self._server.loop(background=True)

            # Register engine callbacks to push state changes to D-Bus
            engine.register_callback("on_pause_change", self._on_pause_change)
            engine.register_callback("on_time_pos_change", self._on_time_pos_change)

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
        refresh immediately. Sets _pending_playstate so that _on_time_pos_change
        will re-emit PlaybackStatus once mpv confirms it is actually playing —
        this guards against the race where idle_active hasn't settled yet when
        this method runs (mpv processes loadfile asynchronously).

        Calls dbus_emit_changes() directly — Server.events is None by default
        and we never wire an EventAdapter, so events.on_*() would be a no-op.
        """
        self._pending_playstate = True
        if self._server:
            from mpris_server.base import dbus_emit_changes, ON_TITLE_PROPS, ON_PLAYPAUSE_PROPS
            try:
                dbus_emit_changes(self._server.player, ON_TITLE_PROPS)
                dbus_emit_changes(self._server.player, ON_PLAYPAUSE_PROPS)
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

    def _on_pause_change(self, _paused: bool) -> None:
        """Push playback status change when mpv pauses or resumes."""
        if self._server:
            from mpris_server.base import dbus_emit_changes, ON_PLAYPAUSE_PROPS
            try:
                dbus_emit_changes(self._server.player, ON_PLAYPAUSE_PROPS)
            except Exception as e:
                log(f"MprisService._on_pause_change: {e}")

    def _on_time_pos_change(self, _pos: float) -> None:
        """Re-push Metadata + PlaybackStatus=Playing once mpv confirms it is playing.

        Guards against two problems:
        1. Race condition in notify_track_changed(): mpv processes loadfile
           asynchronously, so idle_active may still be True when it runs,
           emitting PlaybackStatus=Stopped before mpv transitions to Playing.
        2. KDE Plasma may clear its Metadata cache when it sees PlaybackStatus=Stopped,
           so we must re-send Metadata alongside the corrected PlaybackStatus=Playing.
        The flag is cleared immediately to avoid re-emitting on every position tick.
        """
        if self._pending_playstate and self._server:
            self._pending_playstate = False
            from mpris_server.base import dbus_emit_changes, ON_TITLE_PROPS, ON_PLAYPAUSE_PROPS
            try:
                dbus_emit_changes(self._server.player, ON_TITLE_PROPS)     # re-send Metadata
                dbus_emit_changes(self._server.player, ON_PLAYPAUSE_PROPS)  # idle_active=False → Playing
            except Exception as e:
                log(f"MprisService._on_time_pos_change: {e}")
