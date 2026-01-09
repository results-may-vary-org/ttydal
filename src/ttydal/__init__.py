"""ttydal - Tidal in your terminal!"""

import sys
import traceback
from ttydal.logger import log
from ttydal.app import TtydalApp


def main() -> None:
    """Launch the ttydal TUI application."""
    log("="*80)
    log("Starting ttydal application")
    log("="*80)

    app = None
    try:
        log("Creating TtydalApp instance...")
        app = TtydalApp()
        log("TtydalApp instance created successfully")

        log("Starting app.run()...")
        app.run()
        log("App.run() completed normally")
    except KeyboardInterrupt:
        log("Received KeyboardInterrupt (Ctrl+C)")
    except Exception as e:
        log(f"ERROR: Exception caught in main: {e}")
        log(f"Exception type: {type(e).__name__}")
        log("Full traceback:")
        log(traceback.format_exc())

        print(f"Error starting ttydal: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
    finally:
        log("Performing final cleanup...")
        if app is not None:
            try:
                # Ensure player is shutdown
                if hasattr(app, 'player'):
                    log("  - Final player shutdown check...")
                    app.player.shutdown()
            except Exception as e:
                log(f"  - Error during final cleanup: {e}")
        log("Application exited")
        log("="*80)

