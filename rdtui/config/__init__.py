"""Configuration management for Real-Debrid TUI."""

from rdtui.config.manager import (
    APP_NAME,
    CONFIG_PATH,
    DEFAULT_CONFIG,
    get_config_dir,
    load_config,
    save_config,
)

__all__ = [
    "APP_NAME",
    "CONFIG_PATH",
    "DEFAULT_CONFIG",
    "get_config_dir",
    "load_config",
    "save_config",
]

