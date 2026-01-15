"""Debug logging utility for ttydal."""

import sys
from datetime import datetime
from pathlib import Path
from typing import Any


class DebugLogger:
    """Singleton debug logger for ttydal.

    Lazy initialization - log files are only created when:
    1. Logging is actually called
    2. Debug logging is enabled in config
    """

    _instance = None

    def __new__(cls):
        """Ensure only one instance exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the debug logger (lazy - no files created here)."""
        if self._initialized:
            return

        self.log_dir = Path.home() / ".ttydal"
        self.log_file = self.log_dir / "debug.log"
        self._file_setup_done = False
        self._initialized = True

    def _is_logging_enabled(self) -> bool:
        """Check if debug logging is enabled in config.

        Returns:
            True if logging is enabled, False otherwise
        """
        try:
            # Import here to avoid circular dependency
            from ttydal.config import ConfigManager

            config = ConfigManager()
            return config.debug_logging_enabled
        except Exception:
            # If config check fails, default to disabled (fail-safe)
            return False

    def _setup_log_file(self) -> None:
        """Setup the log file (called lazily on first log)."""
        if self._file_setup_done:
            return

        self.log_dir.mkdir(parents=True, exist_ok=True)

        # ASCII art header
        ascii_art = """
 ______   ______   __  __     _____     ______     __
/\\__  _\\ /\\__  _\\ /\\ \\_\\ \\   /\\  __-.  /\\  __ \\   /\\ \\
\\/_/\\ \\/ \\/_/\\ \\/ \\ \\____ \\  \\ \\ \\/\\ \\ \\ \\  __ \\  \\ \\ \\____
   \\ \\_\\    \\ \\_\\  \\/\\_____\\  \\ \\____-  \\ \\_\\ \\_\\  \\ \\_____\\
    \\/_/     \\/_/   \\/_____/   \\/____/   \\/_/\\/_/   \\/_____/
"""

        # Write session start marker
        with open(self.log_file, "a") as f:
            f.write(f"\n{'=' * 80}\n")
            f.write(ascii_art)
            f.write(f"Session started at {datetime.now().isoformat()}\n")
            f.write(f"{'=' * 80}\n")

        self._file_setup_done = True

    def log(self, *args: Any, **kwargs: Any) -> None:
        """Log a message to both the file and stderr.

        Args:
            *args: Arguments to log (like print)
            **kwargs: Keyword arguments (like print)
        """
        # Check if debug logging is enabled FIRST
        if not self._is_logging_enabled():
            return

        # Setup log file lazily (only if logging is enabled)
        self._setup_log_file()

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        message = " ".join(str(arg) for arg in args)
        log_line = f"[{timestamp}] {message}\n"

        # Write to file
        try:
            with open(self.log_file, "a") as f:
                f.write(log_line)
        except Exception as e:
            print(f"Failed to write to log: {e}", file=sys.stderr)

        # Also print to stderr for immediate feedback
        print(f"[DEBUG] {message}", file=sys.stderr)


# Global logger instance
_logger = None


def get_logger() -> DebugLogger:
    """Get the global logger instance.

    Returns:
        DebugLogger instance
    """
    global _logger
    if _logger is None:
        _logger = DebugLogger()
    return _logger


def log(*args: Any, **kwargs: Any) -> None:
    """Convenience function to log messages.

    Args:
        *args: Arguments to log
        **kwargs: Keyword arguments
    """
    get_logger().log(*args, **kwargs)
