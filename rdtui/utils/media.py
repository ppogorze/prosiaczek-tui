"""Media playback utilities."""

import asyncio
from pathlib import Path

VIDEO_EXTS = {".mkv", ".mp4", ".avi", ".mov", ".webm", ".m4v"}


def is_video(name: str) -> bool:
    """Check if a filename is a video file.

    Args:
        name: Filename to check

    Returns:
        True if the file is a video
    """
    return Path(name).suffix.lower() in VIDEO_EXTS


async def run_mpv(mpv_path: str, source: str):
    """Run mpv to play a video.

    Args:
        mpv_path: Path to mpv executable
        source: Video source (file path or URL)

    Returns:
        The subprocess object
    """
    args = [mpv_path, "--force-window=yes", "--idle=no", "--", source]
    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            start_new_session=True,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
    except TypeError:
        # Fallback for older Python versions
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
    return proc

