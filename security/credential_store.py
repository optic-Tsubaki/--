"""Keep API keys in the Windows credential store, never in project files."""

from __future__ import annotations

import keyring


class CredentialStore:
    """A small wrapper to make credential storage replaceable and testable."""

    SERVICE_NAME = "StudyPet AI"

    def get_api_key(self, account_name: str) -> str | None:
        return keyring.get_password(self.SERVICE_NAME, account_name)

    def set_api_key(self, account_name: str, api_key: str) -> None:
        if not api_key.strip():
            raise ValueError("API key cannot be empty.")
        keyring.set_password(self.SERVICE_NAME, account_name, api_key)

    def delete_api_key(self, account_name: str) -> None:
        try:
            keyring.delete_password(self.SERVICE_NAME, account_name)
        except keyring.errors.PasswordDeleteError:
            pass
