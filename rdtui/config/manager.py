"""Configuration file management."""

import json
import os
import platform
from pathlib import Path
from typing import Any, Dict

APP_NAME = "rdtui"

DEFAULT_CONFIG = {
    "api_key": "",
    "downloader": "aria2c",  # aria2c|curl|wget
    "download_dir": str(Path.home() / "Downloads" / APP_NAME),
    "mpv_path": "mpv",
    # aria2 RPC integration
    "aria2_rpc_enabled": True,
    "aria2_rpc_url": "http://127.0.0.1:6800/jsonrpc",
    "aria2_rpc_secret": "",
    "aria2_autostart": True,
    "download_queue_visible": False,
}


def get_config_dir() -> Path:
    """Get the configuration directory path based on the OS."""
    if platform.system() == "Windows":
        base = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
    else:
        base = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    p = Path(base) / APP_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


CONFIG_PATH = get_config_dir() / "config.json"


def load_config() -> Dict[str, Any]:
    """Load configuration from file, creating default if it doesn't exist."""
    if CONFIG_PATH.exists():
        try:
            return {**DEFAULT_CONFIG, **json.loads(CONFIG_PATH.read_text())}
        except Exception:
            return DEFAULT_CONFIG.copy()
    else:
        CONFIG_PATH.write_text(json.dumps(DEFAULT_CONFIG, indent=2))
        return DEFAULT_CONFIG.copy()


def save_config(cfg: Dict[str, Any]) -> None:
    """Save configuration to file."""
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2))

