"""Utility functions for Real-Debrid TUI."""

from rdtui.utils.download import run_downloader
from rdtui.utils.formatters import format_eta, format_progress, format_size, format_speed
from rdtui.utils.media import is_video, run_mpv

__all__ = [
    "run_downloader",
    "format_eta",
    "format_progress",
    "format_size",
    "format_speed",
    "is_video",
    "run_mpv",
]

