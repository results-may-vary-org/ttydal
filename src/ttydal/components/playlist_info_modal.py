"""Debug info modal — live playback state snapshot for troubleshooting."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Label, Rule

from ttydal.keybindings import get_key

_k = lambda action: get_key("playlist_info_modal", action)


class PlaylistInfoModal(ModalScreen):
    """Modal showing a live snapshot of playback state for debugging."""

    BINDINGS = [
        Binding(_k("close_modal"), "close_modal", "Close", show=True),
        Binding("q", "app.quit", "Quit", show=False),
    ]

    CSS = """
    PlaylistInfoModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.75);
    }

    #debug-outer {
        width: 84;
        height: 90%;
        background: $surface;
        padding: 1 2;
    }

    #debug-scroll {
        width: 1fr;
        height: 1fr;
    }

    #debug-scroll Label.title {
        text-style: bold;
        color: $primary;
        text-align: center;
        width: 100%;
    }

    #debug-scroll Label.section {
        text-style: bold;
        color: $secondary;
        margin-top: 1;
    }

    #debug-scroll Label.row {
        width: 100%;
    }

    #debug-scroll Label.hint {
        margin-top: 1;
        text-align: center;
        width: 100%;
        color: $text-muted;
    }

    #tracks-inner {
        border: solid $secondary;
        height: auto;
        margin-top: 1;
    }

    #tracks-inner Label {
        width: 100%;
    }

    #tracks-inner Label.current-track {
        text-style: bold;
        color: $primary;
    }
    """

    def __init__(self, playlist_info: dict) -> None:
        super().__init__()
        self.playlist_info = playlist_info

    def compose(self) -> ComposeResult:  # noqa: C901
        d = self.playlist_info

        def yn(val: bool) -> str:
            return "YES" if val else "NO"

        def on_off(val: bool) -> str:
            return "ON" if val else "OFF"

        # ---- Engine section --------------------------------------------------
        engine_ok = d.get("engine_initialized", False)
        is_playing = d.get("is_playing", False)
        time_pos = d.get("time_pos", "0:00")
        duration = d.get("duration", "0:00")

        # ---- Config section --------------------------------------------------
        quality = d.get("quality", "?")
        shuffle = d.get("shuffle", False)
        auto_play = d.get("auto_play", True)
        vibrant = d.get("vibrant_color", False)

        # ---- Active playlist section -----------------------------------------
        active_item_id = d.get("active_item_id") or "—"
        current_idx = d.get("current_playing_index")
        tracks = d.get("tracks", [])
        total = len(tracks)

        # ---- Current track section -------------------------------------------
        ct = d.get("current_track") or {}
        ct_name = ct.get("name") or "—"
        ct_artist = ct.get("artist") or "—"
        ct_album = ct.get("album") or "—"
        ct_id = ct.get("id") or "—"
        ct_dur = ct.get("duration", 0) or 0
        ct_cover = ct.get("cover_url") or "—"
        sm = ct.get("stream_metadata") or {}
        ct_quality = sm.get("audio_quality") or sm.get("audioQuality") or "—"
        ct_bitdepth = sm.get("bit_depth") or sm.get("bitDepth") or "—"
        ct_samplerate = sm.get("sample_rate") or sm.get("sampleRate") or "—"

        with Container(id="debug-outer"):
            with ScrollableContainer(id="debug-scroll"):
                yield Label("ttydal — Debug Info", classes="title")
                yield Rule()

                # Engine
                yield Label("Engine", classes="section")
                yield Label(
                    f"  mpv initialized: {yn(engine_ok)}  |  "
                    f"playing: {yn(is_playing)}  |  "
                    f"pos: {time_pos} / {duration}",
                    classes="row",
                )

                # Config
                yield Label("Config", classes="section")
                yield Label(
                    f"  quality: {quality}  |  "
                    f"shuffle: {on_off(shuffle)}  |  "
                    f"auto-play: {on_off(auto_play)}  |  "
                    f"vibrant: {on_off(vibrant)}",
                    classes="row",
                )

                # Active playlist
                yield Label("Active Playlist", classes="section")
                if current_idx is not None and total > 0:
                    active_track = tracks[current_idx] if current_idx < total else {}
                    active_name = active_track.get("name", "?")
                    active_tid = active_track.get("id", "?")
                    pos_label = f"{current_idx + 1}/{total}"
                else:
                    active_name = "—"
                    active_tid = "—"
                    pos_label = f"—/{total}"
                yield Label(f"  item_id: {active_item_id}", classes="row")
                yield Label(
                    f"  position: {pos_label}  |  now: {active_name} ({active_tid})",
                    classes="row",
                )

                # Current track
                yield Label("Current Track", classes="section")
                yield Label(f"  {ct_name} — {ct_artist}", classes="row")
                yield Label(f"  album: {ct_album}  |  id: {ct_id}  |  dur: {ct_dur}s", classes="row")
                yield Label(f"  cover: {ct_cover[:60]}{'…' if len(ct_cover) > 60 else ''}", classes="row")
                yield Label(
                    f"  stream quality: {ct_quality}  |  "
                    f"bit depth: {ct_bitdepth}  |  "
                    f"sample rate: {ct_samplerate}",
                    classes="row",
                )

                # MPRIS / playerctl
                yield Label("MPRIS (playerctl)", classes="section")
                players_out = d.get("playerctl_players", "(not collected)")
                status_out = d.get("playerctl_status", "(not collected)")
                yield Label(
                    f"  players: {players_out}  |  ttydal status: {status_out}",
                    classes="row",
                )
                meta_lines = d.get("playerctl_meta", "(not collected)").splitlines()
                for line in meta_lines:
                    yield Label(f"  {line}", classes="row")

                # Playlist tracks
                yield Label("Active Playlist Tracks", classes="section")
                with Container(id="tracks-inner"):
                    for i, track in enumerate(tracks):
                        name = track.get("name", "Unknown")
                        tid = track.get("id", "?")
                        is_current = i == current_idx
                        prefix = "> " if is_current else "  "
                        label_text = f"{prefix}[{i + 1}] {name}  ({tid})"
                        classes = "current-track" if is_current else ""
                        yield Label(label_text, classes=classes)
                    if not tracks:
                        yield Label("  (no active playlist)")

                yield Label("Press ESC to close", classes="hint")

    def action_close_modal(self) -> None:
        self.dismiss(None)
