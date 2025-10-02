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
        """Return a formatted status with icon and color."""
        status_config = {
            "queued": ("⏳", "yellow"),
            "downloading": ("🔽", "cyan bold"),
            "uploading": ("🔼", "blue"),
            "magnet_error": ("⚠️", "orange"),
            "error": ("❌", "red bold"),
            "virus": ("🦠", "magenta bold"),
            "finished": ("✅", "green bold"),
            "waiting_files_selection": ("🧲", "yellow"),
            "compressing": ("📦", "blue"),
            "dead": ("💀", "red"),
        }

        icon, color = status_config.get(self.status, ("🔷", "white"))
        return Text(f"{icon} {self.status}", style=color)

    def pretty_size(self) -> str:
        """Return a human-readable file size."""
        return humanize.naturalsize(self.size, gnu=True)

    def pretty_added(self) -> str:
        """Return a formatted date string."""
        return self.added.strftime("%Y-%m-%d %H:%M") if self.added else "—"

    def pretty_progress(self) -> str:
        """Return a formatted progress percentage."""
        return f"{self.progress:.0f}%"

    def pretty_progress_bar(self) -> Text:
        """Return a visual progress bar with percentage."""
        pct = int(self.progress)

        # 20 bloków = 100%
        filled = int(pct / 5)
        empty = 20 - filled

        # Wybierz kolor na podstawie postępu
        if pct == 100:
            color = "green"
        elif pct >= 75:
            color = "cyan"
        elif pct >= 50:
            color = "yellow"
        elif pct >= 25:
            color = "orange"
        else:
            color = "red"

        # Użyj różnych znaków dla wypełnienia i pustych
        bar = "█" * filled + "░" * empty

        return Text(f"{bar} {pct:3d}%", style=color)

    def pretty_filename(self, max_width: int = 50, selected: bool = False) -> Text:
        """Return filename, truncated or scrolling if selected.

        Args:
            max_width: Maximum width for the filename
            selected: If True and name is long, create scrolling effect
        """
        name = self.filename

        if len(name) <= max_width:
            return Text(name)

        # Jeśli zaznaczony i długi - efekt przewijania (marquee)
        if selected:
            # Użyj czasu do animacji przewijania
            import time
            offset = int(time.time() * 2) % (len(name) + 5)  # Przewijaj co 0.5s

            # Stwórz efekt przewijania z powtórzeniem
            scrolling = name + "  ···  " + name
            visible = scrolling[offset:offset + max_width]

            return Text(visible, style="bold cyan")
        else:
            # Jeśli nie zaznaczony - po prostu utnij z wielokropkiem
            truncated = name[:max_width - 3] + "..."
            return Text(truncated, style="dim")

