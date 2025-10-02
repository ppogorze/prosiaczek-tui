"""Download utilities."""

import asyncio
from pathlib import Path
from typing import Optional


async def run_downloader(
    downloader: str, url: str, out_dir: Path, filename: Optional[str] = None
):
    """Run a downloader to fetch a file.

    Args:
        downloader: Downloader to use (aria2c, curl, or wget)
        url: URL to download
        out_dir: Output directory
        filename: Optional output filename

    Raises:
        ValueError: If downloader is not supported
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    if downloader == "aria2c":
        args = [
            "aria2c",
            "--console-log-level=warn",
            "--summary-interval=0",
            "--download-result=hide",
            "--allow-overwrite=true",
            "--auto-file-renaming=false",
            "--dir",
            str(out_dir),
        ]
        if filename:
            args += ["--out", filename]
        args.append(url)
    elif downloader == "curl":
        out = str(out_dir / (filename or url.split("/")[-1] or "download.bin"))
        args = ["curl", "-sS", "-L", "-o", out, url]
    elif downloader == "wget":
        out = str(out_dir / (filename or url.split("/")[-1] or "download.bin"))
        args = ["wget", "-q", "-O", out, url]
    else:
        raise ValueError("Unsupported downloader")

    proc = await asyncio.create_subprocess_exec(*args)
    await proc.wait()

