"""ttydal - Tidal in your terminal!"""

import argparse
import sys
import traceback
from ttydal.config import ConfigManager


def main() -> None:
    """Launch the ttydal TUI application."""
    from ttydal.dirs import config_dir, log_dir

    cfg_dir = config_dir()
    log_path = log_dir() / "debug.log"

    parser = argparse.ArgumentParser(
        prog="ttydal",
        usage="ttydal [-h] [--init-config [--force]] [--debug]",
        description="Tidal in your terminal!",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            f"config:\n"
            f"  Config is stored at {cfg_dir}/config.json\n"
            f"  Run --init-config to create one from defaults\n"
            f"  The app works without a config file (uses bundled defaults)\n"
            f"\n"
            f"logs:\n"
            f"  Debug logs are written to {log_path}\n"
            f"  Enable with --debug or set debug_logging_enabled in config"
        ),
    )
    parser.add_argument(
        "--init-config",
        action="store_true",
        help=f"create default config at {cfg_dir}/config.json",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite existing config (only with --init-config)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="enable debug logging (overrides config)",
    )
    args = parser.parse_args()

    if args.force and not args.init_config:
        parser.error("--force can only be used with --init-config")

    if args.init_config:
        try:
            path = ConfigManager.init_config(force=args.force)
            print(f"Config created at {path}")
        except FileExistsError as e:
            print(e, file=sys.stderr)
            sys.exit(1)
        return

    config = ConfigManager()
    if args.debug:
        config._debug_override = True

    from ttydal.logger import log
    from ttydal.app import TtydalApp

    log("=" * 80)
    log("Starting ttydal application")
    log("=" * 80)

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
                if hasattr(app, "player"):
                    log("  - Final player shutdown check...")
                    app.player.shutdown()
            except Exception as e:
                log(f"  - Error during final cleanup: {e}")
        log("Application exited")
        log("=" * 80)
