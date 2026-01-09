# ttydal

Tidal in your terminal!

A TUI (Terminal User Interface) music player for Tidal, built with Python.

## Development Setup

### Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) (Python package manager)

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/ttydal.git
   cd ttydal
   ```

### Install Dependencies

```bash
uv sync
```

This will install all dependencies and create a virtual environment.

### Run the Application

```bash
uv run ttydal
```

Or activate the virtual environment and run directly:

```bash
source .venv/bin/activate  # On Linux/macOS
# .venv\Scripts\activate   # On Windows
ttydal
```

## Keybindings

### Main App
- `p` - Switch to Player page
- `c` - Switch to Config page
- `a` - Focus Albums/Playlists list
- `t` - Focus Tracks list
- `space` - Play/Pause (or play selected track when focused on tracks list)
- `shift+left` - Seek backward 10 seconds
- `shift+right` - Seek forward 10 seconds
- `q` - Quit

### Login Modal
When the login modal appears:
- `o` - Open login URL in browser
- `c` - Copy login URL to clipboard
- `l` - Check login status
- `escape` - Close modal

## License

AGPL-3.0-or-later
