"""Search modal for fuzzy searching albums and tracks."""

from fuzzysearch import find_near_matches

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Input, ListView, ListItem, Label

from ttydal.logger import log


class SearchResultItem(ListItem):
    """A search result item that stores metadata."""

    def __init__(
        self,
        label: str,
        result_type: str,
        item_id: str,
        item_name: str,
        album_id: str | None = None,
        album_type: str | None = None,
        track_info: dict | None = None,
    ) -> None:
        """Initialize a search result item.

        Args:
            label: Display label for the item
            result_type: Type of result ('album' or 'track')
            item_id: ID of the item
            item_name: Name of the item
            album_id: Album ID (for tracks, the containing album; for albums, same as item_id)
            album_type: Album type ('album', 'playlist', or 'favorites')
            track_info: Track metadata (for tracks only)
        """
        super().__init__()
        self.result_type = result_type
        self.item_id = item_id
        self.item_name = item_name
        self.album_id = album_id
        self.album_type = album_type
        self.track_info = track_info
        self._label = label

    def compose(self) -> ComposeResult:
        """Compose the list item."""
        yield Label(self._label)


class SearchModal(ModalScreen):
    """Modal screen for fuzzy searching albums and tracks."""

    BINDINGS = [
        Binding("escape", "close_modal", "Close", show=True),
        Binding("enter", "select_result", "Go to Album", show=True, priority=True),
        Binding("space", "play_track", "Play Track", show=True, priority=True),
    ]

    CSS = """
    SearchModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }

    #search-container {
        width: 60%;
        height: 70%;
        background: $surface;
        keyline: heavy $primary;
        padding: 1;
    }

    #search-container Label.title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
        text-align: center;
        width: 100%;
    }

    #search-input {
        margin-bottom: 1;
    }

    #results-list {
        height: 1fr;
        border: solid $accent;
    }

    #results-list:focus {
        border: solid $primary;
    }

    #results-list Label {
        width: 100%;
    }

    .no-results {
        text-align: center;
        color: $text-muted;
        padding: 2;
    }
    """

    class AlbumSelected(Message):
        """Message sent when an album is selected from search results."""

        def __init__(self, album_id: str, album_name: str, album_type: str) -> None:
            """Initialize album selected message.

            Args:
                album_id: The selected album ID
                album_name: The selected album name
                album_type: Type of item ('album', 'playlist', or 'favorites')
            """
            super().__init__()
            self.album_id = album_id
            self.album_name = album_name
            self.album_type = album_type

    class TrackSelected(Message):
        """Message sent when a track is selected from search results for playback."""

        def __init__(
            self, track_id: str, track_info: dict, album_id: str, play: bool = True
        ) -> None:
            """Initialize track selected message.

            Args:
                track_id: The selected track ID
                track_info: Track metadata
                album_id: The album containing the track
                play: Whether to play the track (True) or just navigate to it (False)
            """
            super().__init__()
            self.track_id = track_id
            self.track_info = track_info
            self.album_id = album_id
            self.play = play

    def __init__(self, albums: list, tracks: list) -> None:
        """Initialize the search modal.

        Args:
            albums: List of album dictionaries with id, name, type keys
            tracks: List of track dictionaries with id, name, artist, album keys
        """
        super().__init__()
        self.albums = albums
        self.tracks = tracks
        self._current_results: list[dict] = []

    def compose(self) -> ComposeResult:
        """Compose the search modal UI."""
        with Container(id="search-container"):
            yield Label("Search Albums & Tracks", classes="title")
            yield Input(placeholder="Type to search...", id="search-input")
            yield ListView(id="results-list")

    def on_mount(self) -> None:
        """Focus the search input when mounted."""
        search_input = self.query_one("#search-input", Input)
        search_input.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes.

        Args:
            event: Input changed event
        """
        if event.input.id == "search-input":
            query = event.value.strip()
            self._perform_search(query)

    def _perform_search(self, query: str) -> None:
        """Perform fuzzy search and update results.

        Args:
            query: Search query string
        """
        results_list = self.query_one("#results-list", ListView)
        results_list.clear()
        self._current_results = []

        if not query:
            return

        log(f"SearchModal: Searching for '{query}'")

        # Search albums
        album_matches = []
        for album in self.albums:
            album_name = album.get("name", "")
            matches = find_near_matches(query.lower(), album_name.lower(), max_l_dist=2)
            if matches:
                album_matches.append(
                    {
                        "type": "album",
                        "id": album["id"],
                        "name": album_name,
                        "album_type": album.get("type", "album"),
                        "match_start": matches[0].start,
                    }
                )

        # Search tracks
        track_matches = []
        for track in self.tracks:
            track_name = track.get("name", "")
            artist = track.get("artist", "")
            search_text = f"{track_name} {artist}".lower()
            matches = find_near_matches(query.lower(), search_text, max_l_dist=2)
            if matches:
                track_matches.append(
                    {
                        "type": "track",
                        "id": track["id"],
                        "name": track_name,
                        "artist": artist,
                        "album": track.get("album", ""),
                        "album_id": track.get("album_id", ""),
                        "album_type": track.get("album_type", "album"),
                        "track_info": track,
                        "match_start": matches[0].start,
                    }
                )

        # Sort by match position (earlier matches first)
        album_matches.sort(key=lambda x: x["match_start"])
        track_matches.sort(key=lambda x: x["match_start"])

        # Combine results: albums first, then tracks
        all_results = album_matches + track_matches
        log(
            f"SearchModal: Found {len(album_matches)} albums, {len(track_matches)} tracks"
        )

        # Populate results list
        for result in all_results:
            if result["type"] == "album":
                label = f"[Album] {result['name']}"
                item = SearchResultItem(
                    label=label,
                    result_type="album",
                    item_id=result["id"],
                    item_name=result["name"],
                    album_id=result["id"],
                    album_type=result["album_type"],
                )
            else:
                label = f"[Track] {result['name']} - {result['artist']}"
                item = SearchResultItem(
                    label=label,
                    result_type="track",
                    item_id=result["id"],
                    item_name=result["name"],
                    album_id=result["album_id"],
                    album_type=result["album_type"],
                    track_info=result["track_info"],
                )
            results_list.append(item)
            self._current_results.append(result)

        if not all_results:
            results_list.append(
                ListItem(Label("No results found", classes="no-results"))
            )

    def _get_selected_result(self) -> SearchResultItem | None:
        """Get the currently selected search result item.

        Returns:
            The selected SearchResultItem or None
        """
        results_list = self.query_one("#results-list", ListView)
        if results_list.index is None:
            return None

        try:
            selected_item = results_list.children[results_list.index]
            if isinstance(selected_item, SearchResultItem):
                return selected_item
        except (IndexError, TypeError):
            pass

        return None

    def action_close_modal(self) -> None:
        """Close the search modal."""
        log("SearchModal: Closing modal")
        self.dismiss(None)

    def action_select_result(self) -> None:
        """Select the current result and navigate to the album."""
        selected = self._get_selected_result()
        if not selected:
            log("SearchModal: No result selected for Enter action")
            return

        log(f"SearchModal: Enter on {selected.result_type} - {selected.item_name}")

        if selected.result_type == "album":
            # Navigate to the album
            self.post_message(
                self.AlbumSelected(
                    selected.album_id,
                    selected.item_name,
                    selected.album_type or "album",
                )
            )
        else:
            # For tracks, navigate to the track (don't play, just highlight)
            self.post_message(
                self.TrackSelected(
                    selected.item_id,
                    selected.track_info or {},
                    selected.album_id or "",
                    play=False,  # Enter = navigate only, don't play
                )
            )

        self.dismiss(None)

    def action_play_track(self) -> None:
        """Play the selected track (Space key)."""
        selected = self._get_selected_result()
        if not selected:
            log("SearchModal: No result selected for Space action")
            return

        log(f"SearchModal: Space on {selected.result_type} - {selected.item_name}")

        if selected.result_type == "track" and selected.track_info:
            # Play the track
            self.post_message(
                self.TrackSelected(
                    selected.item_id,
                    selected.track_info,
                    selected.album_id or "",
                )
            )
            self.dismiss(None)
        else:
            # For albums, space does nothing
            log("SearchModal: Space pressed on album, ignoring")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle list view selection (double-click or Enter on ListView).

        Args:
            event: The selection event
        """
        if event.list_view.id == "results-list":
            # Trigger the same action as Enter key
            self.action_select_result()
