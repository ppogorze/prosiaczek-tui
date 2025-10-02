"""Formatting utilities for displaying data."""

import humanize


def format_size(v: str | int) -> str:
    """Format a size value in bytes to human-readable format.

    Args:
        v: Size in bytes

    Returns:
        Human-readable size string
    """
    try:
        n = int(v)
        return humanize.naturalsize(n, gnu=True)
    except Exception:
        return "?"


def format_progress(completed: str | int, total: str | int) -> str:
    """Format download progress as a percentage.

    Args:
        completed: Bytes completed
        total: Total bytes

    Returns:
        Progress percentage string
    """
    try:
        c = int(completed)
        t = max(1, int(total))
        pct = (c / t) * 100.0
        return f"{pct:.0f}%"
    except Exception:
        return "0%"


def format_speed(v: str | int) -> str:
    """Format download speed to human-readable format.

    Args:
        v: Speed in bytes per second

    Returns:
        Human-readable speed string
    """
    try:
        n = int(v)
        return humanize.naturalsize(n, gnu=True) + "/s"
    except Exception:
        return "0 B/s"


def format_eta(total: int, comp: int, speed: int) -> str:
    """Format estimated time of arrival.

    Args:
        total: Total bytes
        comp: Completed bytes
        speed: Download speed in bytes per second

    Returns:
        ETA string (H:MM:SS or M:SS)
    """
    try:
        remaining = max(0, total - comp)
        if speed <= 0:
            return "∞"
        secs = remaining // max(1, speed)
        # Simple humanized format: H:MM:SS or M:SS
        h = secs // 3600
        m = (secs % 3600) // 60
        s = secs % 60
        if h:
            return f"{h}:{m:02d}:{s:02d}"
        else:
            return f"{m}:{s:02d}"
    except Exception:
        return "?"

