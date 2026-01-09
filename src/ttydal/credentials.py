"""Credential manager for ttydal.

Manages secure storage of user credentials using OS keyring.
"""

import keyring


class CredentialManager:
    """Singleton credential manager for secure credential storage."""

    _instance = None
    SERVICE_NAME = "ttydal"

    def __new__(cls):
        """Ensure only one instance exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the credential manager."""
        if self._initialized:
            return
        self._initialized = True

    def store_token(self, token_name: str, token_value: str) -> None:
        """Store a token securely in the OS keyring.

        Args:
            token_name: Name/key for the token
            token_value: The token value to store
        """
        keyring.set_password(self.SERVICE_NAME, token_name, token_value)

    def get_token(self, token_name: str) -> str | None:
        """Retrieve a token from the OS keyring.

        Args:
            token_name: Name/key for the token

        Returns:
            The token value or None if not found
        """
        return keyring.get_password(self.SERVICE_NAME, token_name)

    def delete_token(self, token_name: str) -> None:
        """Delete a token from the OS keyring.

        Args:
            token_name: Name/key for the token
        """
        try:
            keyring.delete_password(self.SERVICE_NAME, token_name)
        except keyring.errors.PasswordDeleteError:
            pass  # Token doesn't exist, ignore

    def has_token(self, token_name: str) -> bool:
        """Check if a token exists.

        Args:
            token_name: Name/key for the token

        Returns:
            True if token exists, False otherwise
        """
        return self.get_token(token_name) is not None
