<p align="center">
  <a href="https://github.com/results-may-vary-org/ttydal">
    <img alt="ttydal screenshot" src="assets/ttydalscreen.png"/>
  </a>
</p>
<h1 align="center">ttydal - Tidal in your termial!</h1>

<img alt="Static Badge" src="https://img.shields.io/badge/Still_maintained-Yes_%3A)-green">

## Inspiration

This project is heavily inspired by what [Maxteabag](https://github.com/Maxteabag) have done on is awesome project [sqlit](https://github.com/Maxteabag/sqlit).

## Features

- Browse your favorite albums, playlists, and tracks
- Fuzzy search across all loaded albums and tracks (`/` key)
- High-quality audio playback with three quality levels:
  - Max: Hi-Res Lossless (up to 24bit/192kHz)
  - High: Lossless (16bit/44.1kHz)
  - Low: AAC 320kbps
- Real-time stream quality verification showing actual bit depth and sample rate
- Auto-play next track
- Shuffle mode for randomized playback
- Visual indicators showing currently playing track and source album/playlist
- Playback controls with seeking support
- Smart tracks caching for faster navigation and search
- Player bar displaying track info, artist, album, playback time, and quality metrics
- Multiple theme options for interface customization
- Fully keyboard-driven interface
- Settings auto-save on change
- Cover art display in albums list, tracks list, and player bar
- Image caching for cover art
- Vibrant color mode - colorize player bar text with album's vibrant color
- `new` Configurable keybindings - customize all keyboard shortcuts (see [KEYBINDINGS.md](docs/KEYBINDINGS.md))

*warning: this video contain audio of music, mind your volume*

https://github.com/user-attachments/assets/ea975bea-b8f6-4d1a-a309-ec2d54390c3a

## Requirements

- Python 3.13 or higher
- [uv](https://docs.astral.sh/uv/) for development
- Active Tidal subscription
- MPV media player (for audio playback)

## Installation

### For users

```bash
# pipx (recommend)
pipx install ttydal

# uv
uv tool install ttydal

# pip
pip install ttydal
```

Then use it:
```bash
ttydal
```

### For development

1. Clone the repository:
   ```bash
   git clone https://github.com/results-may-vary-org/ttydal.git
   cd ttydal
   ```

2. Install dependencies using uv:
   ```bash
   uv sync
   ```

3. Run the application:
   ```bash
   uv run ttydal
   ```

4. For development with auto-reload (optional):

   Install watchdog for automatic restart on file changes:
   ```bash
   uv add --dev watchdog
   ```

   Run with the development watcher:
   ```bash
   python dev.py
   ```

   This will automatically restart the application whenever you save changes to Python files.

## Getting started

1. Launch ttydal
2. On first run, you'll see a login modal
3. Press `o` to open the Tidal login URL in your browser
4. Complete the authentication in your browser
5. Press `l` to check login status
6. Once logged in, your favorite albums, playlists, and tracks will load automatically

## Keybindings

All keybindings are configurable. See [KEYBINDINGS.md](docs/KEYBINDINGS.md) for the full reference and instructions on customizing them.

## Flag for `ttydal` cmd

`ttydal --init-config` to create a config file, if not exist, from the default value

`ttydal --init-config --force` to overwrite the existing config file with the default value

`ttydal --debug` enable the log of debug information into the config folder

## Configuration

All settings are accessible via the Config page (press `c`).

### Settings

- **Theme**: choose from 12 built-in themes
- **Audio Quality**: select default quality for your playback (max, high, or low)
- **Auto-Play**: enable or disable automatic playback of next track
- **Shuffle**: enable or disable shuffle mode
- **Debug Logging**: enable or disable debug logging (`debug.log` in config directory)
- **API Logging**: *these logs can contains sensitive data* enable or disable API request/response logging (`debug-api.log` in config directory)

All settings are automatically saved when changed.

## Data directories

ttydal follows platform conventions for config and cache directories:

| Type | Linux | MacOS | Windows |
|---|---|---|---|
| Config & logs | `~/.config/ttydal` | `~/Library/Application Support/ttydal` | `%APPDATA%/ttydal` |
| Image cache | `~/.cache/ttydal/images` | `~/Library/Caches/ttydal/images` | `%LOCALAPPDATA%/ttydal/images` |

## Images cache

Loaded images are cached in the platform cache directory (see above).

## Tracks cache

ttydal uses a caching system for tracks to improve performance and enable smart search.

### How it works

- In-memory cache: tracks are cached in memory (lost on app restart)
- TTL of 1 hour: each cached album/playlist expires after 1 hour
- Max 50,000 tracks: cache is limited by total track count, not album count.
- LRU eviction: when cache is full, oldest entries are evicted first
- Auto-preload: on startup, all albums are automatically preloaded into cache in the background (mostly for the search feature)

### Cache info modal

Press `i` to open the cache info modal and see current cache statistics.

### Cache invalidation

If you make changes to your playlists/favorites on the Tidal website:

- Press `r` on *Albums* list that clears the entire tracks cache and reloads albums
- Press `r` on *Tracks* list that invalidates only the current album/playlist cache and reloads

## Code of conduct, license, authors, changelog, contributing

See the following file :
- [code of conduct](CODE_OF_CONDUCT.md)
- [license](LICENSE)
- [authors](AUTHORS)
- [contributing](CONTRIBUTING.md)
- [changelog](CHANGELOG)
- [security](SECURITY.md)

## Want to participate? Have a bug or a request feature?

Do not hesitate to open a pr or an issue. I reply when I can.

### This project is possible because another cool projects exist

- [sqlit](https://github.com/Maxteabag/sqlit)
- [textual](https://textual.textualize.io/)
- [uv](https://docs.astral.sh/uv/)
- [tidalapi](https://pypi.org/project/tidalapi/)

## Want to support my work?

- [Give me a tips](https://github.com/sponsors/bouteillerAlan)
- [Give a star on github](https://github.com/results-may-vary-org/ttydal)
- Or just participate to the development :D

### Thanks !

