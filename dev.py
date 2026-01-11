#!/usr/bin/env python3
"""Development file watcher for ttydal.

Automatically restarts the application when Python files are modified.
"""

import sys
import time
import subprocess
import signal
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class TtydalRestarter(FileSystemEventHandler):
    """File system event handler that restarts ttydal on Python file changes."""

    def __init__(self):
        self.process = None
        self.restart_requested = False
        self.debounce_timer = None

    def start_app(self):
        """Start the ttydal application."""
        if self.process:
            self.stop_app()

        print("\n" + "=" * 60)
        print("Starting ttydal...")
        print("=" * 60 + "\n")

        # Start ttydal through uv run (works with local package)
        self.process = subprocess.Popen(
            ["uv", "run", "ttydal"],
            stdout=sys.stdout,
            stderr=sys.stderr,
        )

    def stop_app(self):
        """Stop the running ttydal application."""
        if self.process:
            print("\n" + "=" * 60)
            print("Stopping ttydal...")
            print("=" * 60 + "\n")

            # Send SIGTERM for graceful shutdown
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                # Force kill if it doesn't stop gracefully
                self.process.kill()
                self.process.wait()

            self.process = None

    def restart_app(self):
        """Restart the ttydal application."""
        self.stop_app()
        time.sleep(0.2)  # Small delay to ensure clean shutdown
        self.start_app()

    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return

        # Only restart for Python files
        if not event.src_path.endswith('.py'):
            return

        # Ignore __pycache__ and .pyc files
        if '__pycache__' in event.src_path or event.src_path.endswith('.pyc'):
            return

        print(f"\nFile changed: {event.src_path}")
        print("Restarting ttydal...\n")

        # Debounce: wait a bit in case multiple files change at once
        if self.debounce_timer:
            self.debounce_timer.cancel()

        import threading
        self.debounce_timer = threading.Timer(0.3, self.restart_app)
        self.debounce_timer.start()


def main():
    """Main entry point for the development watcher."""
    print("\n" + "=" * 60)
    print("ttydal Development Watcher")
    print("=" * 60)
    print("\nWatching for changes in: src/ttydal/")
    print("Press Ctrl+C to stop\n")

    # Create event handler and observer
    event_handler = TtydalRestarter()
    observer = Observer()

    # Watch the src/ttydal directory
    watch_path = Path(__file__).parent / "src" / "ttydal"
    if not watch_path.exists():
        print(f"Error: Directory not found: {watch_path}")
        sys.exit(1)

    observer.schedule(event_handler, str(watch_path), recursive=True)
    observer.start()

    # Start the app initially
    event_handler.start_app()

    try:
        # Keep the watcher running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nShutting down watcher...")
        observer.stop()
        event_handler.stop_app()

    observer.join()
    print("Watcher stopped. Goodbye!")


if __name__ == "__main__":
    main()
