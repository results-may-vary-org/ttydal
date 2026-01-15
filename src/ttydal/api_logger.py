"""HTTP API request/response logger for ttydal.

This module intercepts all HTTP requests made by the application and logs
them to a dedicated debug-api.log file with full details.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class APILogger:
    """Singleton HTTP request/response logger."""

    _instance = None
    _original_request = None

    def __new__(cls):
        """Ensure only one instance exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the API logger (lazy - no files created here)."""
        if self._initialized:
            return

        self.log_dir = Path.home() / ".ttydal"
        self.log_file = self.log_dir / "debug-api.log"
        self._file_setup_done = False
        self._initialized = True

    def _is_logging_enabled(self) -> bool:
        """Check if API logging is enabled in config."""
        try:
            from ttydal.config import ConfigManager

            config = ConfigManager()
            return config.api_logging_enabled
        except Exception:
            return False

    def _setup_log_file(self) -> None:
        """Setup the API log file (called lazily on first log)."""
        if self._file_setup_done:
            return

        self.log_dir.mkdir(parents=True, exist_ok=True)

        # ASCII art header
        ascii_art = """
 ______   ______   __  __     _____     ______     __              ______     ______   __
/\\__  _\\ /\\__  _\\ /\\ \\_\\ \\   /\\  __-.  /\\  __ \\   /\\ \\            /\\  __ \\   /\\  == \\ /\\ \\
\\/_/\\ \\/ \\/_/\\ \\/ \\ \\____ \\  \\ \\ \\/\\ \\ \\ \\  __ \\  \\ \\ \\____       \\ \\  __ \\  \\ \\  _-/ \\ \\ \\
   \\ \\_\\    \\ \\_\\  \\/\\_____\\  \\ \\____-  \\ \\_\\ \\_\\  \\ \\_____\\       \\ \\_\\ \\_\\  \\ \\_\\    \\ \\_\\
    \\/_/     \\/_/   \\/_____/   \\/____/   \\/_/\\/_/   \\/_____/        \\/_/\\/_/   \\/_/     \\/_/
"""

        # Write session start marker
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"\n{'=' * 100}\n")
            f.write(ascii_art)
            f.write(f"API Logging Session started at {datetime.now().isoformat()}\n")
            f.write(f"{'=' * 100}\n\n")

        self._file_setup_done = True

    def _format_headers(self, headers: dict) -> str:
        """Format headers for logging.

        Args:
            headers: Headers dictionary

        Returns:
            Formatted headers string
        """
        if not headers:
            return "  (no headers)"

        lines = []
        for key, value in headers.items():
            lines.append(f"  {key}: {value}")
        return "\n".join(lines)

    def _format_cookies(self, cookies: Any) -> str:
        """Format cookies for logging.

        Args:
            cookies: Cookies object or dict

        Returns:
            Formatted cookies string
        """
        if not cookies:
            return "  (no cookies)"

        # Handle different cookie types
        if hasattr(cookies, "items"):
            cookie_dict = (
                dict(cookies.items()) if hasattr(cookies, "items") else cookies
            )
        elif hasattr(cookies, "get_dict"):
            cookie_dict = cookies.get_dict()
        else:
            return f"  {cookies}"

        if not cookie_dict:
            return "  (no cookies)"

        lines = []
        for key, value in cookie_dict.items():
            lines.append(f"  {key}: {value}")
        return "\n".join(lines)

    def _format_body(self, body: Any, content_type: str = "") -> str:
        """Format request/response body for logging.

        Args:
            body: Body content (str, bytes, dict, etc.)
            content_type: Content-Type header value

        Returns:
            Formatted body string
        """
        if body is None or body == "":
            return "  (empty body)"

        # Handle bytes
        if isinstance(body, bytes):
            # Try to decode as text
            try:
                body = body.decode("utf-8")
            except UnicodeDecodeError:
                return f"  (binary data, {len(body)} bytes)"

        # Handle dict/list (JSON)
        if isinstance(body, (dict, list)):
            try:
                return "  " + json.dumps(body, indent=2).replace("\n", "\n  ")
            except Exception:
                return f"  {body}"

        # Handle string body
        body_str = str(body)

        # Try to parse as JSON for pretty printing
        if "json" in content_type.lower() or body_str.strip().startswith(("{", "[")):
            try:
                parsed = json.loads(body_str)
                return "  " + json.dumps(parsed, indent=2).replace("\n", "\n  ")
            except Exception:
                pass

        # Return as-is with indentation, NO TRUNCATION
        return "  " + body_str.replace("\n", "\n  ")

    def log_request_response(
        self,
        method: str,
        url: str,
        request_headers: dict,
        request_cookies: Any,
        request_body: Any,
        response_status: int,
        response_headers: dict,
        response_body: Any,
        elapsed_time: float,
    ) -> None:
        """Log a complete HTTP request/response pair.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            request_headers: Request headers dict
            request_cookies: Request cookies
            request_body: Request body content
            response_status: HTTP response status code
            response_headers: Response headers dict
            response_body: Response body content (NOT TRUNCATED)
            elapsed_time: Request duration in seconds
        """
        # Check if API logging is enabled FIRST
        if not self._is_logging_enabled():
            return

        # Setup log file lazily (only if logging is enabled)
        self._setup_log_file()

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        log_entry = []
        log_entry.append(f"\n{'=' * 100}")
        log_entry.append(f"[{timestamp}] HTTP REQUEST/RESPONSE")
        log_entry.append(f"{'=' * 100}")

        # Request section
        log_entry.append("\n>>> REQUEST:")
        log_entry.append(f"Method: {method}")
        log_entry.append(f"URL: {url}")
        log_entry.append("\nHeaders:")
        log_entry.append(self._format_headers(request_headers))
        log_entry.append("\nCookies:")
        log_entry.append(self._format_cookies(request_cookies))
        log_entry.append("\nBody:")

        content_type = (
            request_headers.get("Content-Type", "") if request_headers else ""
        )
        log_entry.append(self._format_body(request_body, content_type))

        # Response section
        log_entry.append("\n<<< RESPONSE:")
        log_entry.append(f"Status: {response_status}")
        log_entry.append(f"Elapsed: {elapsed_time:.3f}s")
        log_entry.append("\nHeaders:")
        log_entry.append(self._format_headers(response_headers))
        log_entry.append("\nBody (FULL CONTENT, NO TRUNCATION):")

        response_content_type = (
            response_headers.get("Content-Type", "") if response_headers else ""
        )
        log_entry.append(self._format_body(response_body, response_content_type))

        log_entry.append(f"\n{'=' * 100}\n")

        # Write to file
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write("\n".join(log_entry))
        except Exception as e:
            # Silently fail - don't disrupt the application
            print(f"[API Logger] Failed to write log: {e}")

    def install(self) -> None:
        """Install HTTP request interceptor.

        This monkey-patches the requests library to intercept all HTTP calls.
        """
        try:
            import requests

            # Store original request method if not already stored
            if APILogger._original_request is None:
                APILogger._original_request = requests.Session.request

            # Create wrapper function
            def logged_request(
                session_self: Any, method: str, url: str, **kwargs: Any
            ) -> Any:
                """Wrapped request method that logs all calls."""
                import time

                # Extract request details
                request_headers = kwargs.get("headers", {})
                request_cookies = kwargs.get("cookies", session_self.cookies)
                request_body = kwargs.get("data") or kwargs.get("json")

                # Make the actual request
                start_time = time.time()
                response = APILogger._original_request(
                    session_self, method, url, **kwargs
                )
                elapsed_time = time.time() - start_time

                # Extract response details
                response_headers = dict(response.headers)
                response_status = response.status_code

                # Get response body - be careful not to consume the stream
                try:
                    # For streaming responses, we can't easily log the full body
                    # without consuming it. Try to get it safely.
                    if hasattr(response, "_content") and response._content is not None:
                        response_body = response._content
                    elif hasattr(response, "text"):
                        response_body = response.text
                    else:
                        response_body = "(streaming response, body not captured)"
                except Exception:
                    response_body = "(could not capture response body)"

                # Log the request/response
                self.log_request_response(
                    method=method.upper(),
                    url=url,
                    request_headers=request_headers,
                    request_cookies=request_cookies,
                    request_body=request_body,
                    response_status=response_status,
                    response_headers=response_headers,
                    response_body=response_body,
                    elapsed_time=elapsed_time,
                )

                return response

            # Patch the Session.request method
            requests.Session.request = logged_request

        except ImportError:
            # requests library not available, skip patching
            pass


# Global logger instance
_api_logger = None


def get_api_logger() -> APILogger:
    """Get the global API logger instance.

    Returns:
        APILogger instance
    """
    global _api_logger
    if _api_logger is None:
        _api_logger = APILogger()
    return _api_logger


def install_api_logger() -> None:
    """Install the API logger to intercept all HTTP requests.

    Call this early in your application startup to ensure all
    HTTP requests are logged.
    """
    logger = get_api_logger()
    logger.install()
