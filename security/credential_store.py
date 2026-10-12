"""Keep API keys in the Windows credential store, never in project files."""

from __future__ import annotations

try:
    import keyring
except ImportError:  # Allows the non-AI parts of StudyPet to keep working.
    keyring = None  # type: ignore[assignment]


class CredentialStore:
    """A small wrapper to make credential storage replaceable and testable."""

    SERVICE_NAME = "StudyPet AI"

    @property
    def is_available(self) -> bool:
        return keyring is not None

    def _require_keyring(self) -> None:
        if keyring is None:
            raise RuntimeError("缺少 keyring 组件。请运行 python -m pip install -r requirements.txt。")

    def get_api_key(self, account_name: str) -> str | None:
        self._require_keyring()
        return keyring.get_password(self.SERVICE_NAME, account_name)

    def set_api_key(self, account_name: str, api_key: str) -> None:
        self._require_keyring()
        if not api_key.strip():
            raise ValueError("API key cannot be empty.")
        keyring.set_password(self.SERVICE_NAME, account_name, api_key)

    def delete_api_key(self, account_name: str) -> None:
        self._require_keyring()
        try:
            keyring.delete_password(self.SERVICE_NAME, account_name)
        except keyring.errors.PasswordDeleteError:
            pass
