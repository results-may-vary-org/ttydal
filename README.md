# ttydal

A Terminal User Interface (TUI) music player for Tidal streaming service, built with Python.

## Features

- Browse your favorite albums, playlists, and tracks
- High-quality audio playback with three quality levels:
  - Max: Hi-Res Lossless (up to 24bit/192kHz)
  - High: Lossless (16bit/44.1kHz)
  - Low: AAC 320kbps
- Real-time stream quality verification showing actual bit depth and sample rate
- Auto-play next track with loop support (configurable)
- Visual indicators showing currently playing track and source album/playlist
- Playback controls with seeking support
- Rich player bar displaying track info, artist, album, playback time, and quality metrics
- Multiple theme options for interface customization
- Fully keyboard-driven interface
- Settings auto-save on change

## Requirements

- Python 3.13 or higher
- Active Tidal subscription
- MPV media player (for audio playback)

## Installation

### For Users

```bash
pip install ttydal
```

### For Development

1. Clone the repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/ttydal.git
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

   Or activate the virtual environment:
   ```bash
   source .venv/bin/activate  # Linux/macOS
   # .venv\Scripts\activate   # Windows
   ttydal
   ```

## Getting Started

1. Launch ttydal
2. On first run, you'll see a login modal
3. Press `o` to open the Tidal login URL in your browser
4. Complete the authentication in your browser
5. Press `l` to check login status
6. Once logged in, your favorite albums, playlists, and tracks will load automatically

## Keybindings

### Navigation

- `p` - Switch to Player page
- `c` - Switch to Config page
- `a` - Focus Albums/Playlists list
- `t` - Focus Tracks list
- `up/down` - Navigate through lists
- `enter` - Select item / Play track (always starts from beginning)

### Playback Controls

- `space` - Smart play/pause:
  - When tracks list focused and no track selected: toggle pause/play
  - When tracks list focused and different track selected: play the new track
  - When tracks list focused and same track selected: toggle pause/play
  - When tracks list not focused: toggle pause/play
- `shift+left` - Seek backward 10 seconds
- `shift+right` - Seek forward 10 seconds
- `n` - Toggle auto-play next track on/off
- `r` - Refresh current list

### Login Modal

- `o` - Open login URL in browser
- `c` - Copy login URL to clipboard
- `l` - Check login status
- `escape` - Close modal

### Application

- `q` - Quit application

## Configuration

All settings are accessible via the Config page (press `c`).

### Available Settings

- Theme: Choose from 12 built-in themes (changes preview in real-time)
- Audio Quality: Select Max, High, or Low quality
- Auto-Play: Enable or disable automatic playback of next track

All settings are automatically saved when changed.

## Project Structure

```
ttydal/
├── src/ttydal/
│   ├── components/      # UI components (player bar, track lists, etc.)
│   ├── pages/          # Application pages (player, config)
│   ├── app.py          # Main application
│   ├── player.py       # MPV player wrapper
│   ├── tidal_client.py # Tidal API client
│   ├── config.py       # Configuration manager
│   └── logger.py       # Debug logging
└── README.md
```

## Troubleshooting

### Tracks not loading

Press `r` to refresh the current list.

### Login issues

1. Check your internet connection
2. Ensure you have an active Tidal subscription
3. Try clearing credentials and logging in again

### Debug logs

Debug logs are stored in `~/.ttydal/debug.log`. You can clear them from the Config page.

## License

AGPL-3.0-or-later

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
