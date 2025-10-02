"""Torrent data model."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

import humanize
from dateutil import parser as dtparser
from rich.text import Text


@dataclass
class TorrentRow:
    """Represents a torrent row in the UI table."""

    id: str
    filename: str
    status: str
    progress: float
    added: Optional[datetime]
    size: int

    @classmethod
    def from_info(cls, t: Dict[str, Any]) -> "TorrentRow":
        """Create a TorrentRow from Real-Debrid API response."""
        added = None
        if t.get("added"):
            try:
                added = dtparser.parse(t["added"]).replace(tzinfo=None)
            except Exception:
                added = None
        size = int(t.get("bytes", 0))
        progress = float(t.get("progress", 0))
        status = t.get("status", "unknown")
        return cls(
            id=t.get("id", ""),
            filename=t.get("filename", "(no name)"),
            status=status,
            progress=progress,
            added=added,
            size=size,
        )

    def pretty_status(self) -> Text:
        """Return a formatted status with icon."""
        icon = {
            "queued": "⏳",
            "downloading": "🔽",
            "uploading": "🔼",
            "magnet_error": "⚠️",
            "error": "❌",
            "virus": "🦠",
            "finished": "✅",
            "waiting_files_selection": "🧲",
        }.get(self.status, "🔷")
        return Text(f"{icon} {self.status}")

    def pretty_size(self) -> str:
        """Return a human-readable file size."""
        return humanize.naturalsize(self.size, gnu=True)

    def pretty_added(self) -> str:
        """Return a formatted date string."""
        return self.added.strftime("%Y-%m-%d %H:%M") if self.added else "—"

    def pretty_progress(self) -> str:
        """Return a formatted progress percentage."""
        return f"{self.progress:.0f}%"

