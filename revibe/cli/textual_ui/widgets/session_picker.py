from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from revibe.core.config import VibeConfig


class SessionPicker:
    """Provides session listing and selection for the /resume command.

    Discovers all saved sessions and provides metadata for display.
    """

    def __init__(self, config: VibeConfig) -> None:
        self.config = config

    def list_sessions(self) -> list[dict[str, Any]]:
        """List all available sessions with metadata.

        Returns:
            List of session dicts with keys: session_id, start_time,
            message_count, filepath, stats_summary
        """
        from revibe.core.config import SessionLoggingConfig

        save_dir = Path(self.config.session_logging.save_dir)
        if not save_dir.exists():
            return []

        prefix = self.config.session_logging.session_prefix
        pattern = f"{prefix}_*.json"
        session_files = sorted(
            save_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True
        )

        sessions: list[dict[str, Any]] = []
        for filepath in session_files:
            session_info = self._read_session_metadata(filepath)
            if session_info:
                sessions.append(session_info)

        return sessions

    def _read_session_metadata(self, filepath: Path) -> dict[str, Any] | None:
        """Read session metadata from a session file."""
        try:
            with filepath.open("r", encoding="utf-8") as f:
                data = json.load(f)

            metadata = data.get("metadata", {})
            messages = data.get("messages", [])

            return {
                "session_id": metadata.get("session_id", filepath.stem),
                "start_time": metadata.get("start_time", "Unknown"),
                "end_time": metadata.get("end_time"),
                "message_count": metadata.get("total_messages", len(messages)),
                "filepath": str(filepath),
                "filename": filepath.name,
                "stats": metadata.get("stats", {}),
                "tools_available": metadata.get("tools_available", []),
                "git_commit": metadata.get("git_commit"),
                "git_branch": metadata.get("git_branch"),
                "username": metadata.get("username"),
            }
        except (json.JSONDecodeError, OSError):
            return None

    def get_session_by_index(self, index: int) -> dict[str, Any] | None:
        """Get session by 0-based index."""
        sessions = self.list_sessions()
        if 0 <= index < len(sessions):
            return sessions[index]
        return None

    def get_session_by_id(self, session_id: str) -> dict[str, Any] | None:
        """Get session by session_id."""
        sessions = self.list_sessions()
        for session in sessions:
            if session["session_id"] == session_id:
                return session
        return None

    def load_session_messages(self, filepath: str) -> list[Any]:
        """Load messages from a session file."""
        from revibe.core.types import LLMMessage

        path = Path(filepath)
        if not path.exists():
            return []

        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)

            messages = [
                LLMMessage.model_validate(msg) for msg in data.get("messages", [])
            ]
            return messages
        except (json.JSONDecodeError, OSError):
            return []
