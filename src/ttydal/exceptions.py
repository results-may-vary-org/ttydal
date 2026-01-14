"""Custom exceptions and error handling for ttydal.

This module provides standardized exception classes and error handling
utilities for consistent error management across the application.
"""

import traceback
from typing import Any, Dict, Optional
from textual.app import App


# Export all exception classes for easy importing
__all__ = [
    "TtydalError",
    "AuthenticationError",
    "NetworkError",
    "DataFetchError",
    "PlaybackError",
    "ConfigurationError",
    "QualityError",
    "TidalServiceError",
    "ErrorHandler",
    "RetryConfig",
]


class TtydalError(Exception):
    """Base exception for all ttydal errors."""

    def __init__(
        self, message: str, user_message: Optional[str] = None, severity: str = "error"
    ):
        """Initialize ttydal error.

        Args:
            message: Technical error message for logging
            user_message: User-friendly message for notifications
            severity: Error severity level ("info", "warning", "error")
        """
        super().__init__(message)
        self.message = message
        self.user_message = user_message or message
        self.severity = severity
        self.traceback = traceback.format_exc()


class AuthenticationError(TtydalError):
    """Raised when authentication fails or user is not logged in."""

    def __init__(self, message: str = "Authentication required"):
        user_message = "Please log in to your Tidal account"
        super().__init__(message, user_message, severity="warning")


class NetworkError(TtydalError):
    """Raised when network operations fail."""

    def __init__(self, message: str, operation: str = "network operation"):
        user_message = f"Network error: {operation}. Please check your connection."
        super().__init__(message, user_message, severity="warning")


class DataFetchError(TtydalError):
    """Raised when data fetching from API fails."""

    def __init__(self, message: str, resource: str = "data"):
        user_message = f"Failed to fetch {resource}. Please try again."
        super().__init__(message, user_message, severity="error")


class TidalServiceError(TtydalError):
    """Raised when Tidal service operations fail."""

    def __init__(self, message: str, operation: str = "service operation"):
        user_message = f"Tidal service error: {operation}. Please try again."
        super().__init__(message, user_message, severity="error")


class PlaybackError(TtydalError):
    """Raised when playback operations fail."""

    def __init__(self, message: str, track_name: Optional[str] = None):
        if track_name:
            user_message = f"Failed to play '{track_name}': {message}"
        else:
            user_message = f"Playback error: {message}"
        super().__init__(message, user_message, severity="error")


class ConfigurationError(TtydalError):
    """Raised when configuration operations fail."""

    def __init__(self, message: str, setting: Optional[str] = None):
        if setting:
            user_message = f"Configuration error for '{setting}': {message}"
        else:
            user_message = f"Configuration error: {message}"
        super().__init__(message, user_message, severity="error")


class QualityError(TtydalError):
    """Raised when audio quality operations fail."""

    def __init__(
        self,
        message: str,
        track_name: Optional[str] = None,
        qualities: Optional[list] = None,
    ):
        if track_name and qualities:
            user_message = f"'{track_name}' not available at requested quality. Tried: {', '.join(qualities)}"
        elif track_name:
            user_message = f"Quality error for '{track_name}': {message}"
        else:
            user_message = f"Audio quality error: {message}"
        super().__init__(message, user_message, severity="warning")


class ErrorHandler:
    """Centralized error handling utilities."""

    @staticmethod
    def log_error(error: Exception, context: str = "") -> None:
        """Log error with context.

        Args:
            error: The exception to log
            context: Additional context information
        """
        import sys

        timestamp = (
            traceback.format_exc().splitlines()[0].split(",")[0].strip()
            if traceback.format_exc()
            else "No timestamp"
        )
        print(f"ERROR in {context}: {error}", file=sys.stderr)

        if isinstance(error, TtydalError):
            print(f"  - User message: {error.user_message}", file=sys.stderr)
            print(f"  - Severity: {error.severity}", file=sys.stderr)
            if hasattr(error, "traceback"):
                print(f"  - Traceback: {error.traceback}", file=sys.stderr)

    @staticmethod
    def handle_error(
        error: Exception, app: App, context: str = "", timeout: int = 5
    ) -> None:
        """Handle error with logging and user notification.

        Args:
            error: The exception to handle
            app: The application instance for notifications
            context: Additional context information
            timeout: Notification timeout in seconds
        """
        # Log the error
        ErrorHandler.log_error(error, context)

        # Show user notification
        if isinstance(error, TtydalError):
            app.notify(error.user_message, severity=error.severity, timeout=timeout)  # type: ignore
        else:
            app.notify(f"Unexpected error: {error}", severity="error", timeout=timeout)  # type: ignore

    @staticmethod
    def safe_execute(
        func, *args, error_context: str = "", default_return: Any = None, **kwargs
    ):
        """Safely execute a function with error handling.

        Args:
            func: Function to execute
            *args: Function arguments
            error_context: Context for error logging
            default_return: Value to return on error
            **kwargs: Function keyword arguments

        Returns:
            Function result or default_return on error
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            ErrorHandler.log_error(e, error_context)
            return default_return

    @staticmethod
    def safe_execute_async(
        func, *args, error_context: str = "", default_return: Any = None, **kwargs
    ):
        """Safely execute an async function with error handling.

        Args:
            func: Async function to execute
            *args: Function arguments
            error_context: Context for error logging
            default_return: Value to return on error
            **kwargs: Function keyword arguments

        Returns:
            Function result or default_return on error
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            ErrorHandler.log_error(e, error_context)
            return default_return

    @staticmethod
    def handle_async_error(error: Exception, context: str = "") -> Dict[str, Any]:
        """Handle error in async context and return error info.

        Args:
            error: The exception to handle
            context: Additional context information

        Returns:
            Dictionary with error information
        """
        ErrorHandler.log_error(error, context)

        if isinstance(error, TtydalError):
            return {
                "error": error.user_message,
                "severity": error.severity,
                "technical": error.message,
            }
        else:
            return {"error": str(error), "severity": "error", "technical": str(error)}


class RetryConfig:
    """Configuration for retry operations."""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        backoff_factor: float = 2.0,
        retry_on: tuple = (NetworkError, DataFetchError),
    ):
        """Initialize retry configuration.

        Args:
            max_attempts: Maximum number of retry attempts
            base_delay: Base delay between retries in seconds
            backoff_factor: Multiplier for exponential backoff
            retry_on: Exception types to retry on
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.backoff_factor = backoff_factor
        self.retry_on = retry_on


async def retry_execute_async(
    func, *args, config: Optional[RetryConfig] = None, error_context: str = "", **kwargs
):
    """Execute async function with retry logic.

    Args:
        func: Async function to execute
        *args: Function arguments
        config: Retry configuration
        error_context: Context for error logging
        **kwargs: Function keyword arguments

    Returns:
        Function result
    """
    if config is None:
        config = RetryConfig()

    last_error = None

    for attempt in range(config.max_attempts):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_error = e

            # Don't retry on exceptions we don't want to retry
            if not isinstance(e, config.retry_on):
                raise e

            # Log retry attempt
            ErrorHandler.log_error(
                e, f"{error_context} (attempt {attempt + 1}/{config.max_attempts})"
            )

            # Wait before next retry with exponential backoff
            if attempt < config.max_attempts - 1:
                import asyncio

                await asyncio.sleep(
                    config.base_delay * (config.backoff_factor**attempt)
                )

    # If we get here, all retries failed
    if last_error:
        raise last_error
