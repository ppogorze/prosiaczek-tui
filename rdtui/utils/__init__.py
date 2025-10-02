"""Utility functions for Real-Debrid TUI."""

from rdtui.utils.download import run_downloader
from rdtui.utils.formatters import format_eta, format_progress, format_size, format_speed
from rdtui.utils.media import is_video, run_mpv
from rdtui.utils.search import fuzzy_search, highlight_match, simple_fuzzy_score

__all__ = [
    "run_downloader",
    "format_eta",
    "format_progress",
    "format_size",
    "format_speed",
    "is_video",
    "run_mpv",
    "fuzzy_search",
    "highlight_match",
    "simple_fuzzy_score",
]

