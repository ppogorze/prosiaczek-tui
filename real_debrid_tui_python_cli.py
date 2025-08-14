#!/usr/bin/env python3
"""
Real-Debrid TUI (Textual-based CLI)

Funkcje:
- Konfiguracja: API key, downloader (aria2c/curl/wget), katalog pobrań, ścieżka do mpv
- Dodawanie magnetów (zawsze wybiera wszystkie pliki w torrencie)
- Lista torrentów z tabelą, ikonki i statusy; nawigacja kursorem góra/dół
- Akcje: [a]dd magnet, [r]efresh, [x] delete (obsługuje wiele zaznaczonych), [d] download, [p] play w mpv (jeśli wideo),
         [g] settings, [f] filtr w locie, [l] kopiuj link(i) do schowka, [?] help, [q] quit, [spacja] zaznacz/odznacz
- Pobieranie plików przez wybrany downloader
- Odtwarzanie przez mpv (lokalnie jeśli już pobrane, albo streaming bezpośrednim linkiem)

Wymagania (pip):
    textual>=0.58.0
    httpx>=0.27.0
    humanize>=4.9.0
    rich>=13.7.0
    python-dateutil>=2.9.0.post0
    pyperclip>=1.8.2  (kopiowanie linków do schowka)

Uruchomienie:
    python rdtui.py

Uwaga: Real-Debrid API — ustaw token w Ustawieniach (g) lub przez plik konfiguracyjny.

Plik konfiguracyjny:
    Linux/macOS: ~/.config/rdtui/config.json
    Windows: %APPDATA%/rdtui/config.json

Autor: ChatGPT
"""
from __future__ import annotations

import asyncio
import json
import os
import platform
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
import humanize
from dateutil import parser as dtparser

from rich.text import Text

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.message import Message
from textual.reactive import reactive

from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Static,
    Log,
    Tabs,
)

# Contextual tables with their own bindings for Footer hints
class TorrentsTable(DataTable):
    BINDINGS = [
        Binding("space", "toggle_select", "Zaznacz", priority=True),
        Binding("a", "add_magnet", "Dodaj plik", priority=True),
        Binding("r", "refresh", "Odśwież", priority=True),
        Binding("x", "delete", "Usuń", priority=True),
        Binding("d", "download", "Pobierz", priority=True),
        Binding("p", "play", "Odtwórz", priority=True),
        Binding("l", "copy_link", "Kopiuj link", priority=True),
        Binding("f", "toggle_filter", "Filtr", priority=True),
    ]

    # Forward actions to App so bindings on this widget work across Textual versions
    async def action_toggle_select(self):
        await self.app.action_toggle_select()

    async def action_add_magnet(self):
        await self.app.action_add_magnet()

    async def action_refresh(self):
        await self.app.action_refresh()

    async def action_delete(self):
        await self.app.action_delete()

    async def action_download(self):
        await self.app.action_download()

    async def action_play(self):
        await self.app.action_play()

    async def action_copy_link(self):
        await self.app.action_copy_link()

    async def action_toggle_filter(self):
        await self.app.action_toggle_filter()

    def on_focus(self, _event):
        try:
            self.app.queue_active = False
        except Exception:
            pass

    def on_mouse_down(self, _event):
        # Ensure the table gets focus on click
        try:
            self.focus()
        except Exception:
            pass


class QueueTable(DataTable):
    BINDINGS = [
        Binding("o", "queue_open_location", "Otwórz lokalizację", priority=True),
        Binding("x", "queue_remove", "Usuń / Anuluj", priority=True),
        Binding("p", "queue_pause", "Pauza", priority=True),
    ]

    async def action_queue_open_location(self):
        await self.app.action_queue_open_location()

    async def action_queue_remove(self):
        await self.app.action_queue_remove()

    async def action_queue_pause(self):
        await self.app.action_queue_pause()

    def on_focus(self, _event):
        try:
            self.app.queue_active = True
        except Exception:
            pass

    def on_mouse_down(self, _event):
        # Ensure the table gets focus on click
        try:
            self.focus()
        except Exception:
            pass

# pyperclip jest opcjonalny – jeśli brak, pokażemy komunikat
try:
    import pyperclip  # type: ignore
except Exception:  # pragma: no cover
    pyperclip = None  # type: ignore

APP_NAME = "rdtui"
API_BASE = "https://api.real-debrid.com/rest/1.0"

# -------------------------- Utils & Config --------------------------

def get_config_dir() -> Path:
    if platform.system() == "Windows":
        base = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
    else:
        base = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    p = Path(base) / APP_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p

CONFIG_PATH = get_config_dir() / "config.json"

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

VIDEO_EXTS = {".mkv", ".mp4", ".avi", ".mov", ".webm", ".m4v"}


def load_config() -> Dict[str, Any]:
    if CONFIG_PATH.exists():
        try:
            return {**DEFAULT_CONFIG, **json.loads(CONFIG_PATH.read_text())}
        except Exception:
            return DEFAULT_CONFIG.copy()
    else:
        CONFIG_PATH.write_text(json.dumps(DEFAULT_CONFIG, indent=2))
        return DEFAULT_CONFIG.copy()


def save_config(cfg: Dict[str, Any]) -> None:
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2))


# -------------------------- RD API Client --------------------------

class RDClient:
    def __init__(self, token: str):
        self.token = token
        self._client = httpx.AsyncClient(
            base_url=API_BASE,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        )

    async def close(self):
        await self._client.aclose()

    async def _get(self, path: str, **kwargs):
        r = await self._client.get(path, **kwargs)
        r.raise_for_status()
        return r.json()

    async def _post(self, path: str, data: Dict[str, Any] | None = None):
        r = await self._client.post(path, data=data)
        r.raise_for_status()
        try:
            return r.json()
        except Exception:
            return {}

    async def _delete(self, path: str):
        r = await self._client.delete(path)
        # RD returns 204 No Content on success for delete endpoints
        if r.status_code not in (200, 204):
            r.raise_for_status()
        try:
            return r.json()
        except Exception:
            return {}

    # --- Endpoints ---
    async def user(self) -> Dict[str, Any]:
        return await self._get("/user")

    async def torrents(self) -> List[Dict[str, Any]]:
        return await self._get("/torrents")

    async def torrent_info(self, tid: str) -> Dict[str, Any]:
        return await self._get(f"/torrents/info/{tid}")

    async def add_magnet(self, magnet: str) -> Dict[str, Any]:
        return await self._post("/torrents/addMagnet", data={"magnet": magnet})

    async def select_all(self, tid: str) -> Dict[str, Any]:
        return await self._post(f"/torrents/selectFiles/{tid}", data={"files": "all"})

    async def delete_torrent(self, tid: str) -> Dict[str, Any]:
        # Use DELETE as per RD API docs (returns 204 No Content)
        return await self._delete(f"/torrents/delete/{tid}")

    async def unrestrict_link(self, link: str) -> Dict[str, Any]:
        return await self._post("/unrestrict/link", data={"link": link})

    async def add_torrent_bytes(self, data: bytes, filename: str = "upload.torrent") -> Dict[str, Any]:
        files = {"file": (filename, data, "application/x-bittorrent")}
        r = await self._client.post("/torrents/addTorrent", files=files)
        r.raise_for_status()
        try:
            return r.json()
        except Exception:
            return {}

    async def add_torrent_from_url(self, url: str) -> Dict[str, Any]:
        # Download .torrent and upload to RD
        resp = await self._client.get(url)
        resp.raise_for_status()
        fname = url.split("/")[-1] or "upload.torrent"
        return await self.add_torrent_bytes(resp.content, fname)


# -------------------------- aria2 RPC Client --------------------------

class Aria2RPC:
    def __init__(self, url: str, secret: str | None = None):
        self.url = url
        self.secret = secret or ""
        self._id = 0
        self._client = httpx.AsyncClient(timeout=15.0)

    def _next_id(self) -> int:
        self._id += 1
        return self._id

    def _auth_token(self) -> List[Any]:
        return [f"token:{self.secret}"] if self.secret else []

    async def _call(self, method: str, params: List[Any] | None = None) -> Any:
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
            "params": (self._auth_token() + (params or [])),
        }
        r = await self._client.post(self.url, json=payload)
        r.raise_for_status()
        data = r.json()
        if "error" in data:
            raise RuntimeError(data["error"])  # pragma: no cover
        return data.get("result")

    async def add_uri(self, uris: List[str], out: Optional[str] = None, dir: Optional[str] = None) -> str:
        options: Dict[str, Any] = {}
        if out:
            options["out"] = out
        if dir:
            options["dir"] = dir
        gid = await self._call("aria2.addUri", [uris, options])
        return gid

    async def tell_status(self, gid: str) -> Dict[str, Any]:
        keys = ["status", "totalLength", "completedLength", "downloadSpeed", "errorMessage", "files"]
        return await self._call("aria2.tellStatus", [gid, keys])

    async def tell_active(self) -> List[Dict[str, Any]]:
        keys = ["gid", "status", "totalLength", "completedLength", "downloadSpeed", "files"]
        return await self._call("aria2.tellActive", [keys])

    async def tell_waiting(self, offset: int = 0, num: int = 100) -> List[Dict[str, Any]]:
        keys = ["gid", "status", "totalLength", "completedLength", "downloadSpeed", "files"]
        return await self._call("aria2.tellWaiting", [offset, num, keys])

    async def tell_stopped(self, offset: int = 0, num: int = 100) -> List[Dict[str, Any]]:
        keys = ["gid", "status", "totalLength", "completedLength", "downloadSpeed", "files", "errorMessage"]
        return await self._call("aria2.tellStopped", [offset, num, keys])

    async def pause(self, gid: str) -> Any:
        return await self._call("aria2.pause", [gid])

    async def remove(self, gid: str) -> Any:
        # Try remove running task; if already stopped, remove result
        try:
            return await self._call("aria2.remove", [gid])
        except Exception:
            try:
                return await self._call("aria2.removeDownloadResult", [gid])
            except Exception:
                raise

    async def close(self):
        await self._client.aclose()


# -------------------------- Helper structs --------------------------

@dataclass
class TorrentRow:
    id: str
    filename: str
    status: str
    progress: float
    added: Optional[datetime]
    size: int

    @classmethod
    def from_info(cls, t: Dict[str, Any]) -> "TorrentRow":
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
        return humanize.naturalsize(self.size, gnu=True)

    def pretty_added(self) -> str:
        return self.added.strftime("%Y-%m-%d %H:%M") if self.added else "—"

    def pretty_progress(self) -> str:
        return f"{self.progress:.0f}%"


async def run_downloader(downloader: str, url: str, out_dir: Path, filename: Optional[str] = None):
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


async def run_mpv(mpv_path: str, source: str):
    # Run mpv without blocking the TUI; show window if available
    args = [mpv_path, "--force-window=yes", "--idle=no", "--", source]
    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            start_new_session=True,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
    except TypeError:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
    return proc


def is_video(name: str) -> bool:
    return Path(name).suffix.lower() in VIDEO_EXTS


# -------------------------- Modale / pomoc --------------------------

class HelpModal(Static):
    DEFAULT_CSS = """
    HelpModal {
        background: $panel;
        border: round $primary;
        padding: 1 2;
        width: 80%;
        height: auto;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("❓ Pomoc — skróty klawiszowe")
        txt = "\n".join([
            "[b]Strzałki[/b] – nawigacja po liście",
            "[b]spacja[/b] – zaznacz/odznacz wiersz (multi-select)",
            "[b]a[/b] – dodaj plik (🧲)",
            "[b]f[/b] – filtr w locie (🔎)",
            "[b]l[/b] – kopiuj link(i) do schowka (🔗)",
            "[b]r[/b] – odśwież (🔄)",
            "[b]x[/b] – usuń zaznaczone lub bieżący (❌)",
            "[b]d[/b] – pobierz zaznaczone lub bieżący (⬇️)",
            "[b]p[/b] – odtwórz w mpv (▶️)",
            "[b]g[/b] – ustawienia (⚙️)",
            "[b]?[/b] – pomoc",
            "[b]q[/b] – wyjście",
        ])
        yield Static(txt)
        yield Button("Zamknij", id="close")

    def on_button_pressed(self, _: Button.Pressed):
        self.remove()


class InputModal(Static):
    class Submitted(Message):
        def __init__(self, value: str):
            self.value = value
            super().__init__()

    DEFAULT_CSS = """
    InputModal { background: $panel; border: round $success; padding: 1 2; width: 80%; }
    Input { width: 100%; }
    """

    def __init__(self, title: str, placeholder: str = "", password: bool = False):
        super().__init__()
        self.title = title
        self.placeholder = placeholder
        self.password = password

    def compose(self) -> ComposeResult:
        yield Label(self.title)
        yield Input(placeholder=self.placeholder, password=self.password, id="inp")
        yield Horizontal(Button("OK", id="ok"), Button("Anuluj", id="cancel"))

    def on_mount(self):
        self.query_one(Input).focus()

    def on_button_pressed(self, ev: Button.Pressed):
        if ev.button.id == "ok":
            self.post_message(self.Submitted(self.query_one(Input).value))
            self.remove()
        elif ev.button.id == "cancel":
            self.remove()


class SettingsModal(Static):
    class Saved(Message):
        def __init__(self, cfg: Dict[str, Any]):
            self.cfg = cfg
            super().__init__()

    DEFAULT_CSS = """
    SettingsModal { background: $panel; border: round $primary; padding: 1 2; width: 80%; }
    Input { width: 100%; }
    """

    def __init__(self, cfg: Dict[str, Any]):
        super().__init__()
        self.cfg = cfg.copy()

    def compose(self) -> ComposeResult:
        yield Label("⚙️ Ustawienia")
        self.api = Input(value=self.cfg.get("api_key", ""), placeholder="Real-Debrid API token", password=True)
        self.down = Input(value=self.cfg.get("downloader", "aria2c"), placeholder="Downloader: aria2c/curl/wget")
        self.dir = Input(value=self.cfg.get("download_dir", ""), placeholder="Katalog pobrań (dla RPC: na zdalnej maszynie)")
        self.mpv = Input(value=self.cfg.get("mpv_path", "mpv"), placeholder="Ścieżka do mpv")
        # aria2 RPC
        self.a2_enabled = Input(value=str(self.cfg.get("aria2_rpc_enabled", True)).lower(), placeholder="aria2 RPC włączone: true/false")
        self.a2_url = Input(value=self.cfg.get("aria2_rpc_url", "http://127.0.0.1:6800/jsonrpc"), placeholder="aria2 RPC URL: http://host:6800/jsonrpc")
        self.a2_secret = Input(value=self.cfg.get("aria2_rpc_secret", ""), placeholder="aria2 RPC secret (opcjonalnie)")
        self.a2_autostart = Input(value=str(self.cfg.get("aria2_autostart", True)).lower(), placeholder="Autostart lokalnego aria2c: true/false")
        # layout
        yield Label("API key:")
        yield self.api
        yield Label("Downloader:")
        yield self.down
        yield Label("Katalog pobrań:")
        yield self.dir
        yield Label("mpv:")
        yield self.mpv
        yield Label("aria2 RPC włączone:")
        yield self.a2_enabled
        yield Label("aria2 RPC URL:")
        yield self.a2_url
        yield Label("aria2 RPC secret:")
        yield self.a2_secret
        yield Label("Autostart lokalnego aria2c:")
        yield self.a2_autostart
        yield Horizontal(Button("Zapisz", id="save"), Button("Anuluj", id="cancel"))

    def on_button_pressed(self, ev: Button.Pressed):
        if ev.button.id == "save":
            def _pbool(s: str) -> bool:
                return s.strip().lower() in {"1", "true", "t", "yes", "y", "on"}
            self.cfg.update(
                {
                    "api_key": self.api.value.strip(),
                    "downloader": self.down.value.strip() or "aria2c",
                    "download_dir": self.dir.value.strip(),
                    "mpv_path": self.mpv.value.strip() or "mpv",
                    "aria2_rpc_enabled": _pbool(self.a2_enabled.value),
                    "aria2_rpc_url": self.a2_url.value.strip() or "http://127.0.0.1:6800/jsonrpc",
                    "aria2_rpc_secret": self.a2_secret.value.strip(),
                    "aria2_autostart": _pbool(self.a2_autostart.value),
                }
            )
            self.post_message(self.Saved(self.cfg))
            self.remove()
        else:
            self.remove()


# -------------------------- Main App --------------------------

class RDTUI(App):
    CSS_PATH = None
    BINDINGS = [
        # Global + routing keys
        Binding("g", "settings", "Ustawienia", priority=True),
        Binding("?", "help", "Pomoc", priority=True),
        Binding("q", "quit", "Wyjście", priority=True),
        Binding("k", "toggle_queue", "Kolejka pobrań", priority=True),
        # Route keys to appropriate context
        Binding("o", "key_o", "Otwórz lokalizację", priority=True),
        Binding("x", "key_x", "Usuń / Anuluj", priority=True),
        Binding("p", "key_p", "Odtwórz/Pauza", priority=True),
        Binding("a", "add_magnet", "Dodaj plik", priority=True),
        Binding("r", "refresh", "Odśwież", priority=True),
        Binding("d", "download", "Pobierz", priority=True),
        Binding("l", "copy_link", "Kopiuj link", priority=True),
        Binding("f", "toggle_filter", "Filtr", priority=True),
        Binding("space", "toggle_select", "Zaznacz", priority=True),
    ]

    rd: Optional[RDClient] = None
    cfg: Dict[str, Any] = {}
    status_text: reactive[str] = reactive("Gotowy.")

    # Multi-select i filtr
    selected_ids: set[str] = set()
    filter_text: reactive[str] = reactive("")
    active_category: reactive[str] = reactive("All")  # Tabs: Games, Movies, Series, All
    _all_rows: List[TorrentRow] = []

    # UI state flags
    queue_active: reactive[bool] = reactive(False)

    # aria2 RPC and queue
    aria2: Optional[Aria2RPC] = None
    download_tasks: Dict[str, Dict[str, Any]] = {}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container():
            # Taby kategorii
            self.tabs = Tabs("Games", "Movies", "Series", "All", id="tabs")
            yield self.tabs

            # Pasek filtra (ukryty dopóki nie aktywny)
            self.filter_bar = Horizontal(Input(placeholder="Pisz, by filtrować…", id="filter"))
            self.filter_bar.display = False
            yield self.filter_bar

            self.table = TorrentsTable(id="tbl")
            yield self.table

            # Download queue table (hidden by default)
            self.queue_table = QueueTable(id="queue")
            self.queue_table.display = self.cfg.get("download_queue_visible", False)
            yield self.queue_table

            self.log_widget = Log(id="log")
            self.log_widget.display = False
            yield self.log_widget
        yield Footer()

    async def on_mount(self):
        self.cfg = load_config()
        self.table.add_columns("✓", "🆔 ID", "📄 Nazwa", "📦 Rozmiar", "📈 Postęp", "🗓️ Dodano", "🔖 Status")
        self.table.cursor_type = "row"
        self.table.zebra_stripes = True
        # Queue table columns
        self.queue_table.add_columns("Plik", "Rozmiar", "Status", "Progres", "Prędkość", "ETA", "Katalog")
        self.queue_table.cursor_type = "row"
        self.queue_table.zebra_stripes = True
        try:
            self.queue_table.show_cursor = True
        except Exception:
            pass
        self.table.focus()
        await self.setup_client()
        await self.setup_aria2()
        await self.action_refresh()
        # periodic refresh of aria2 queue
        self.set_interval(2.0, self.refresh_queue, pause=not self.queue_table.display)

    async def setup_client(self):
        token = self.cfg.get("api_key", "")
        if not token:
            self.notify("Ustaw API key w [g] Ustawieniach.", severity="warning")
            return
        if self.rd:
            await self.rd.close()
        self.rd = RDClient(token)
        try:
            u = await self.rd.user()
            self.notify(f"Zalogowano jako {u.get('username','?')} ✅")
        except Exception as e:
            self.notify(f"Błąd autoryzacji: {e}", severity="error")

    async def setup_aria2(self):
        # Initialize aria2 RPC if enabled; autostart if necessary
        if not self.cfg.get("aria2_rpc_enabled", False):
            return
        url = self.cfg.get("aria2_rpc_url", "http://127.0.0.1:6800/jsonrpc")
        secret = self.cfg.get("aria2_rpc_secret", "")
        self.aria2 = Aria2RPC(url, secret or None)
        # Try a quick call to detect availability
        try:
            await self.aria2.tell_active()
        except Exception:
            # Autostart if configured
            if self.cfg.get("aria2_autostart", True):
                try:
                    # Start aria2c with RPC enabled in background
                    args = [
                        "aria2c",
                        "--enable-rpc",
                        "--rpc-listen-all=false",
                        "--rpc-allow-origin-all=true",
                        f"--rpc-listen-port={6800}",
                    ]
                    if secret:
                        args.append(f"--rpc-secret={secret}")
                    await asyncio.create_subprocess_exec(
                        *args,
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL,
                        start_new_session=True,
                    )
                    # Give it a moment to start
                    await asyncio.sleep(0.6)
                except Exception as e:
                    self.notify(f"Nie udało się uruchomić aria2c RPC: {e}", severity="error")
                    return
            # Try again
            try:
                await self.aria2.tell_active()
            except Exception as e:
                self.notify(f"Brak połączenia z aria2 RPC: {e}", severity="warning")
                self.aria2 = None

    async def on_unmount(self):
        if self.rd:
            await self.rd.close()
        if self.aria2:
            await self.aria2.close()

    # ---------------- Actions ----------------

    async def action_help(self):
        self.mount(HelpModal())

    async def action_settings(self):
        modal = SettingsModal(self.cfg)
        self.mount(modal)

    async def action_add_magnet(self):
        if not self.rd:
            self.notify("Brak API key.", severity="warning")
            return
        modal = InputModal("Wklej: magnet / URL do .torrent / link hostera (RD)", "magnet:?xt=... lub https://.../plik.torrent lub https://hoster/...")
        self.mount(modal)

    async def action_refresh(self):
        if not self.rd:
            return
        try:
            ts = await self.rd.torrents()
            self._all_rows = [TorrentRow.from_info(t) for t in ts]
            # zachowaj selekcję tylko dla istniejących ID
            self.selected_ids = {i for i in self.selected_ids if any(r.id == i for r in self._all_rows)}
            self._render_table()
        except Exception as e:
            self.notify(f"Błąd odświeżania: {e}", severity="error")

    def _row_selected_icon(self, tid: str) -> str:
        return "✅" if tid in self.selected_ids else " "

    def _render_table(self):
        self.table.clear()
        rows = self._filtered_rows()
        # sort: newest first
        rows.sort(key=lambda r: r.added or datetime.fromtimestamp(0), reverse=True)
        for row in rows:
            self.table.add_row(
                self._row_selected_icon(row.id),
                row.id,
                row.filename,
                row.pretty_size(),
                row.pretty_progress(),
                row.pretty_added(),
                row.pretty_status(),
                key=row.id,
            )
        if rows:
            try:
                self.table.cursor_coordinate = (0, 0)
            except Exception:
                pass

    def _filtered_rows(self) -> List[TorrentRow]:
        rows = list(self._all_rows)
        # Category filter
        cat = (self.active_category or "All").lower()
        if cat != "all":
            rows = [r for r in rows if self._row_category(r).lower() == cat]
        # Text filter
        if not self.filter_text:
            return rows
        q = self.filter_text.lower().strip()
        out: List[TorrentRow] = []
        for r in rows:
            hay = f"{r.filename} {r.status}".lower()
            if q in hay:
                out.append(r)
        return out

    def _row_category(self, r: TorrentRow) -> str:
        name = (r.filename or "").lower()
        # Prosta heurystyka: "movies" jeśli typowy wzorzec filmu, "series" jeśli S01E01/season/episode, inaczej "other"
        if re.search(r"\bS\d{1,2}E\d{1,2}\b", name) or "season" in name or "episode" in name:
            return "Series"
        # Filmy – plik wideo i brak wzorca serialowego
        if is_video(name):
            return "Movies"
        return "Games"

    def on_tabs_tab_activated(self, event):  # type: ignore[override]
        try:
            label = getattr(event, "tab", None) or getattr(event, "label", None)
            # Textual >=0.58 emits object with .tab.label, older may pass string
            if hasattr(label, "label"):
                label = label.label
            if not label:
                return
            self.active_category = str(label)
            self._render_table()
        except Exception:
            pass

    def _selected_or_current_ids(self) -> List[str]:
        if self.selected_ids:
            return list(self.selected_ids)
        tid = self._current_tid()
        return [tid] if tid else []

    def _current_tid(self) -> Optional[str]:
        # If there are no rows, bail out
        try:
            if getattr(self.table, "row_count", 0) == 0:
                return None
        except Exception:
            pass
        # Try to get a direct cursor row key (Textual 5.x)
        try:
            row_key = getattr(self.table, "cursor_row_key")
            if row_key is not None:
                return str(row_key)
        except Exception:
            pass
        # Try to get a cursor cell where the first element may be the row key
        try:
            cursor_cell = getattr(self.table, "cursor_cell")
            if cursor_cell is not None:
                row_key = cursor_cell[0]
                if row_key is not None:
                    return str(row_key)
        except Exception:
            pass
        # Fallback to cursor row index then resolve to a key
        row_index = None
        try:
            row_index = getattr(self.table, "cursor_row")
        except Exception:
            row_index = None
        if row_index is None:
            # As an absolute fallback, assume first row
            row_index = 0
        # 1) Preferred: get_row_at(index).key
        try:
            row = self.table.get_row_at(row_index)
            key = getattr(row, "key", None)
            if key is not None:
                return str(key)
        except Exception:
            pass
        # 2) Newer API: get_row(index).key
        try:
            row = self.table.get_row(row_index)
            key = getattr(row, "key", None)
            if key is not None:
                return str(key)
        except Exception:
            pass
        # 3) Access internal row_keys list/tuple
        try:
            keys = getattr(self.table, "row_keys", None)
            if keys is not None:
                return str(keys[row_index])
        except Exception:
            pass
        # 4) Last resort: read value from the ID column (index 1)
        try:
            cell = self.table.get_cell_at((row_index, 1))
            if cell is not None:
                return str(cell)
        except Exception:
            pass
        return None

    def _current_gid(self) -> Optional[str]:
        # Robustly get the current queue row key (gid) across Textual versions
        try:
            if getattr(self.queue_table, "row_count", 0) == 0:
                return None
        except Exception:
            pass
        # direct cursor row key
        try:
            row_key = getattr(self.queue_table, "cursor_row_key")
            if row_key is not None:
                return str(row_key)
        except Exception:
            pass
        # cursor row index
        try:
            row_index = getattr(self.queue_table, "cursor_row")
        except Exception:
            row_index = 0
        if row_index is None:
            row_index = 0
        # Try get_row_at(index).key (newer) but guard when it returns a list
        try:
            row = self.queue_table.get_row_at(row_index)
            key = getattr(row, "key", None)
            if key is not None:
                return str(key)
        except Exception:
            pass
        # Try get_row(index).key
        try:
            row = self.queue_table.get_row(row_index)
            key = getattr(row, "key", None)
            if key is not None:
                return str(key)
        except Exception:
            pass
        # Access row_keys
        try:
            keys = getattr(self.queue_table, "row_keys", None)
            if keys is not None:
                return str(keys[row_index])
        except Exception:
            pass
        # Fallback: first key from tasks if any
        try:
            if self.download_tasks:
                return str(sorted(self.download_tasks.keys())[0])
        except Exception:
            pass
        return None

    async def action_toggle_select(self):
        tid = self._current_tid()
        if not tid:
            return
        if tid in self.selected_ids:
            self.selected_ids.remove(tid)
        else:
            self.selected_ids.add(tid)
        self._render_table()

    async def action_toggle_filter(self):
        # pokaż/ukryj pasek filtra; focus na Input
        self.filter_bar.display = not self.filter_bar.display
        if self.filter_bar.display:
            self.query_one("#filter", Input).focus()
        else:
            # ukrycie nie czyści filtra — zostawiamy świadomie
            self.focus_on_table()

    # Global key fallback to ensure actions work even when widgets capture keys
    def on_key(self, event):  # type: ignore[override]
        try:
            focused = self.focused
        except Exception:
            focused = None
        key = getattr(event, "key", None)
        ch = getattr(event, "character", None)
        handled = False

        # If focus is in filter input: ESC closes, others pass-through
        if isinstance(focused, Input) and getattr(focused, "id", "") == "filter":
            if key == "escape" or ch == "\x1b":
                handled = True
                asyncio.create_task(self.action_toggle_filter())
            # don't hijack other keys while typing filter
            if handled:
                try:
                    event.stop()
                except Exception:
                    pass
            return

        # If queue is visible, route o/x/p to queue actions
        if self.queue_table.display:
            if key == "o" or ch == "o":
                handled = True
                asyncio.create_task(self.action_queue_open_location())
            elif key == "x" or ch == "x":
                handled = True
                asyncio.create_task(self.action_queue_remove())
            elif key == "p" or ch == "p":
                handled = True
                asyncio.create_task(self.action_queue_pause())
        else:
            # Default (torrents list) hotkeys
            if key in {"space"} or ch == " ":
                handled = True
                asyncio.create_task(self.action_toggle_select())
            elif key == "d" or ch == "d":
                handled = True
                asyncio.create_task(self.action_download())
            elif key == "l" or ch == "l":
                handled = True
                asyncio.create_task(self.action_copy_link())
            elif key == "f" or ch == "f":
                handled = True
                asyncio.create_task(self.action_toggle_filter())
            elif key == "x" or ch == "x":
                handled = True
                asyncio.create_task(self.action_delete())
            elif key == "p" or ch == "p":
                handled = True
                asyncio.create_task(self.action_play())
            elif key == "a" or ch == "a":
                handled = True
                asyncio.create_task(self.action_add_magnet())
            elif key == "r" or ch == "r":
                handled = True
                asyncio.create_task(self.action_refresh())
            elif key == "g" or ch == "g":
                handled = True
                asyncio.create_task(self.action_settings())
            elif key == "?" or ch == "?":
                handled = True
                asyncio.create_task(self.action_help())
            elif key == "q" or ch == "q":
                handled = True
                self.exit()
            elif key == "k" or ch == "k":
                handled = True
                asyncio.create_task(self.action_toggle_queue())
        if handled:
            try:
                event.stop()
            except Exception:
                pass

    def focus_on_table(self):
        try:
            self.table.focus()
        except Exception:
            pass

    def focus_on_queue(self):
        try:
            self.queue_table.focus()
        except Exception:
            pass

    async def action_delete(self):
        if not self.rd:
            return
        ids = self._selected_or_current_ids()
        if not ids:
            return
        try:
            for tid in ids:
                await self.rd.delete_torrent(tid)
            if len(ids) > 1:
                self.notify(f"Usunięto {len(ids)} pozycji ❌")
            else:
                self.notify("Usunięto ❌")
            self.selected_ids.clear()
            await self.action_refresh()
        except Exception as e:
            self.notify(f"Błąd usuwania: {e}", severity="error")

    async def _collect_links(self, tid: str) -> List[Tuple[str, str]]:
        """Return list of (filename, direct_url) prepared via unrestrict/link.
        We always pass links through unrestrict to ensure they are truly direct.
        """
        assert self.rd is not None
        info = await self.rd.torrent_info(tid)
        links = info.get("links") or []
        out: List[Tuple[str, str]] = []
        # 1) Prefer links list; unrestrict every link for a real direct URL and filename
        for url in links:
            try:
                unr = await self.rd.unrestrict_link(url)
                direct = unr.get("download") or unr.get("link") or url
                # Some RD responses include content-disposition header in a separate field; fallback to URL tail
                fname = unr.get("filename") or url.split("/")[-1]
                out.append((fname, direct))
            except Exception:
                # If unrestrict fails, still return the original
                out.append((url.split("/")[-1], url))
        if out:
            return out
        # 2) Fallback: unrestrict original host links (if present)
        origs = info.get("original", []) or []
        for item in origs:
            lnk = item.get("link") or item.get("download")
            if not lnk:
                continue
            try:
                unr = await self.rd.unrestrict_link(lnk)
                direct = unr.get("download") or unr.get("link") or lnk
                fname = unr.get("filename") or item.get("filename") or direct.split("/")[-1]
                out.append((fname, direct))
            except Exception:
                continue
        return out

    # Queue UI helpers
    def _format_size(self, v: str | int) -> str:
        try:
            n = int(v)
            return humanize.naturalsize(n, gnu=True)
        except Exception:
            return "?"

    def _format_progress(self, completed: str | int, total: str | int) -> str:
        try:
            c = int(completed)
            t = max(1, int(total))
            pct = (c / t) * 100.0
            return f"{pct:.0f}%"
        except Exception:
            return "0%"

    def _format_speed(self, v: str | int) -> str:
        try:
            n = int(v)
            return humanize.naturalsize(n, gnu=True) + "/s"
        except Exception:
            return "0 B/s"

    def _format_eta(self, total: int, comp: int, speed: int) -> str:
        try:
            remaining = max(0, total - comp)
            if speed <= 0:
                return "∞"
            secs = remaining // max(1, speed)
            # simple humanized format: H:MM:SS or M:SS
            h = secs // 3600
            m = (secs % 3600) // 60
            s = secs % 60
            if h:
                return f"{h}:{m:02d}:{s:02d}"
            else:
                return f"{m}:{s:02d}"
        except Exception:
            return "?"

    async def refresh_queue(self):
        if not self.queue_table.display or not self.cfg.get("aria2_rpc_enabled", False) or not self.aria2:
            return
        # Build a fresh view of tasks by asking aria2
        try:
            active = await self.aria2.tell_active()
            waiting = await self.aria2.tell_waiting(0, 100)
            stopped = await self.aria2.tell_stopped(0, 100)
            items = active + waiting + stopped
        except Exception as e:
            self.notify(f"Błąd odświeżania kolejki: {e}", severity="error")
            return

        # Update internal tasks dict with results
        for it in items:
            gid = it.get("gid")
            if not gid:
                continue
            files = it.get("files") or []
            path = files[0]["path"] if files and files[0].get("path") else None
            dirpath = os.path.dirname(path) if path else None
            filename = os.path.basename(path) if path else "?"
            status = it.get("status", "?")
            total = int(it.get("totalLength", 0) or 0)
            comp = int(it.get("completedLength", 0) or 0)
            speed = int(it.get("downloadSpeed", 0) or 0)
            eta = self._format_eta(total, comp, speed)
            self.download_tasks[gid] = {
                **self.download_tasks.get(gid, {}),
                "filename": filename,
                "dir": dirpath or self.download_tasks.get(gid, {}).get("dir", ""),
                "status": status,
                "size": self._format_size(total),
                "progress": self._format_progress(comp, total),
                "speed": self._format_speed(speed),
                "eta": eta,
            }

        # Render table (stable order for nicer UI)
        self.queue_table.clear()
        for gid in sorted(self.download_tasks.keys()):
            info = self.download_tasks[gid]
            self.queue_table.add_row(
                info.get("filename", gid),
                info.get("size", "?"),
                info.get("status", "?"),
                info.get("progress", "0%"),
                info.get("speed", "0 B/s"),
                info.get("eta", "?"),
                info.get("dir", ""),
                key=gid,
            )
        # Ensure a visible row selection for key actions
        try:
            if getattr(self.queue_table, "row_count", 0) > 0:
                self.queue_table.cursor_coordinate = (0, 0)
        except Exception:
            pass

    async def action_queue_open_location(self):
        # Open directory of the selected queue item in OS file manager
        try:
            if not self.queue_table.row_count:
                self.notify("Kolejka pobrań jest pusta.", severity="warning")
                return
            gid = self._current_gid()
            if not gid:
                self.notify("Brak zaznaczonej pozycji w kolejce.", severity="warning")
                return
            info = self.download_tasks.get(gid, {})
            path = info.get("dir")
            if not path:
                self.notify("Brak ścieżki katalogu dla pozycji (zadanie jeszcze nie wystartowało?)", severity="warning")
                return
            if sys.platform == "darwin":
                await asyncio.create_subprocess_exec("open", path)
            elif sys.platform.startswith("linux"):
                await asyncio.create_subprocess_exec("xdg-open", path)
            elif sys.platform.startswith("win"):
                await asyncio.create_subprocess_exec("explorer", path)
        except Exception as e:
            self.notify(f"Nie udało się otworzyć katalogu: {e}", severity="error")

    async def action_queue_remove(self):
        # Remove/cancel current queue item
        if not self.aria2:
            return
        try:
            if not self.queue_table.row_count:
                self.notify("Kolejka pobrań jest pusta.", severity="warning")
                return
            gid = self._current_gid()
            if not gid:
                self.notify("Brak zaznaczonej pozycji w kolejce.", severity="warning")
                return
            try:
                await self.aria2.remove(gid)
            finally:
                self.download_tasks.pop(gid, None)
                await self.refresh_queue()
        except Exception as e:
            self.notify(f"Błąd anulowania: {e}", severity="error")

    async def action_queue_pause(self):
        # Pause current queue item
        if not self.aria2:
            return
        try:
            if not self.queue_table.row_count:
                self.notify("Kolejka pobrań jest pusta.", severity="warning")
                return
            gid = self._current_gid()
            if not gid:
                self.notify("Brak zaznaczonej pozycji w kolejce.", severity="warning")
                return
            await self.aria2.pause(gid)
            await self.refresh_queue()
        except Exception as e:
            self.notify(f"Błąd pauzy: {e}", severity="error")

    async def action_toggle_queue(self):
        self.queue_table.display = not self.queue_table.display
        if self.queue_table.display:
            # resume timer and focus queue table
            self.set_interval(2.0, self.refresh_queue, pause=False)
            self.queue_active = True
            await self.refresh_queue()
            self.focus_on_queue()
        else:
            # pause timer and focus torrents list
            self.set_interval(2.0, self.refresh_queue, pause=True)
            self.queue_active = False
            self.focus_on_table()

    async def action_download(self):
        if not self.rd:
            return
        ids = self._selected_or_current_ids()
        if not ids:
            return
        try:
            for tid in ids:
                links = await self._collect_links(tid)
                if not links:
                    self.notify(f"[{tid}] Brak linków – torrent się przetwarza.", severity="warning")
                    continue
                dl_dir = Path(self.cfg.get("download_dir", DEFAULT_CONFIG["download_dir"])) / tid
                dl_dir.mkdir(parents=True, exist_ok=True)
                use_rpc = self.cfg.get("aria2_rpc_enabled", False) and self.aria2 is not None
                if use_rpc:
                    # Add to aria2 queue via RPC
                    for fname, url in links:
                        try:
                            gid = await self.aria2.add_uri([url], out=fname, dir=str(dl_dir))  # type: ignore[arg-type]
                            self.download_tasks[gid] = {
                                "tid": tid,
                                "filename": fname,
                                "dir": str(dl_dir),
                                "status": "queued",
                                "progress": "0%",
                                "speed": "0 B/s",
                                "eta": "?",
                            }
                        except Exception as e:
                            self.notify(f"aria2 addUri error: {e}", severity="error")
                    self.notify(f"Dodano do kolejki {len(links)} plików → aria2 ⬇️")
                    # Ensure queue visible and timer running
                    if not self.queue_table.display:
                        self.queue_table.display = True
                        self.set_interval(2.0, self.refresh_queue, pause=False)
                else:
                    # Fallback: run downloader in background tasks
                    self.notify(f"Pobieranie {len(links)} plików do {dl_dir}… ⬇️")
                    for fname, url in links:
                        asyncio.create_task(run_downloader(self.cfg.get("downloader", "aria2c"), url, dl_dir, filename=fname))
            if not use_rpc:
                self.notify("Pobieranie uruchomione w tle ✅")
        except Exception as e:
            self.notify(f"Błąd pobierania: {e}", severity="error")

    async def action_play(self):
        if not self.rd:
            return
        ids = self._selected_or_current_ids()
        if not ids:
            return
        # odtwórz tylko pierwszą zaznaczoną/bieżącą pozycję
        tid = ids[0]
        try:
            links = await self._collect_links(tid)
            if not links:
                self.notify("Brak linków do odtworzenia.", severity="warning")
                return
            # preferuj plik wideo
            video = None
            for fname, url in links:
                if is_video(fname):
                    video = (fname, url)
                    break
            if not video:
                video = links[0]
            fname, url = video
            # Fire-and-forget launch of mpv on a best source (local if exists, otherwise direct URL)
            local_path = Path(self.cfg.get("download_dir", DEFAULT_CONFIG["download_dir"])) / tid / fname
            src = str(local_path) if local_path.exists() else url
            self.notify(f"Odtwarzanie ▶️ {fname}")
            # Don't await; keep UI responsive
            asyncio.create_task(run_mpv(self.cfg.get("mpv_path", "mpv"), src))
        except Exception as e:
            self.notify(f"Błąd odtwarzania: {e}", severity="error")

    async def action_copy_link(self):
        if not self.rd:
            return
        if pyperclip is None:
            self.notify("Brak biblioteki pyperclip — zainstaluj, aby kopiować linki.", severity="warning")
            return
        ids = self._selected_or_current_ids()
        if not ids:
            return
        try:
            urls: List[str] = []
            for tid in ids:
                links = await self._collect_links(tid)
                urls.extend([url for _, url in links])
            if not urls:
                self.notify("Brak dostępnych linków do skopiowania.", severity="warning")
                return
            pyperclip.copy("\n".join(urls))  # type: ignore
            self.notify(f"Skopiowano {len(urls)} link(ów) do schowka 🔗")
            # If queue is visible and aria2 available, offer quick-add (optional UX)
        except Exception as e:
            self.notify(f"Błąd kopiowania: {e}", severity="error")

    async def on_settings_modal_saved(self, msg: SettingsModal.Saved):
        self.cfg.update(msg.cfg)
        save_config(self.cfg)
        await self.setup_client()

    async def on_input_modal_submitted(self, msg: InputModal.Submitted):
        """Obsługa potwierdzenia z InputModal – dodanie magnet/.torrent/hoster."""
        if not self.rd:
            self.notify("Brak API key.", severity="warning")
            return
        raw = (msg.value or "").strip()
        try:
            # 1) Magnet
            if raw.startswith("magnet:"):
                self.notify("Dodawanie magnetu…")
                r = await self.rd.add_magnet(raw)
                tid = r.get("id") or r.get("torrent") or r.get("hash") or ""
                if not tid:
                    self.notify("Nie udało się utworzyć torrenta", severity="error")
                    return
                await self.rd.select_all(tid)
                self.notify("Wybrano wszystkie pliki. Przetwarzanie w toku… 🔄")
                await self.action_refresh()
                return

            # 2) HTTP(S) URL: .torrent or hoster
            if raw.startswith("http://") or raw.startswith("https://"):
                # Heurystyka: URL do .torrent -> upload do RD
                if re.search(r"\.torrent(\?|$)", raw, re.IGNORECASE):
                    self.notify("Dodawanie torrenta z URL…")
                    r = await self.rd.add_torrent_from_url(raw)
                    tid = r.get("id") or r.get("torrent") or r.get("hash") or ""
                    if not tid:
                        self.notify("Nie udało się utworzyć torrenta (.torrent)", severity="error")
                        return
                    await self.rd.select_all(tid)
                    self.notify("Wybrano wszystkie pliki. Przetwarzanie w toku… 🔄")
                    await self.action_refresh()
                    return
                # Inaczej: hoster URL -> unrestrict i pobieraj
                self.notify("Przetwarzanie linku hostera przez RD…")
                unr = await self.rd.unrestrict_link(raw)
                direct = unr.get("download") or unr.get("link")
                if not direct:
                    err = unr.get("error") or "Brak direct link z RD"
                    self.notify(f"Nie udało się unrestrict: {err}", severity="error")
                    return
                fname = unr.get("filename") or direct.split("/")[-1]
                dl_dir = Path(self.cfg.get("download_dir", str(Path.home() / "Downloads" / APP_NAME)))
                use_rpc = self.cfg.get("aria2_rpc_enabled", False) and self.aria2 is not None
                if use_rpc:
                    try:
                        gid = await self.aria2.add_uri([direct], out=fname, dir=str(dl_dir))  # type: ignore[arg-type]
                        self.download_tasks[gid] = {
                            "tid": None,
                            "filename": fname,
                            "dir": str(dl_dir),
                            "status": "queued",
                            "progress": "0%",
                            "speed": "0 B/s",
                            "eta": "?",
                        }
                        # Upewnij się, że kolejka widoczna i timer działa
                        if not self.queue_table.display:
                            self.queue_table.display = True
                            self.set_interval(2.0, self.refresh_queue, pause=False)
                        self.notify("Dodano do kolejki aria2 ⬇️")
                    except Exception as e:
                        self.notify(f"aria2 addUri error: {e}", severity="error")
                        # Fallback do lokalnego pobierania
                        asyncio.create_task(run_downloader(self.cfg.get("downloader", "aria2c"), direct, dl_dir, filename=fname))
                        self.notify("Pobieranie uruchomione w tle ✅")
                else:
                    asyncio.create_task(run_downloader(self.cfg.get("downloader", "aria2c"), direct, dl_dir, filename=fname))
                    self.notify("Pobieranie uruchomione w tle ✅")
                return

            # 3) Nieznany format
            self.notify("Wklej magnet / URL do .torrent / link hostera.", severity="warning")
        except httpx.HTTPStatusError as e:
            # Spróbuj pokazać komunikat RD
            try:
                data = e.response.json()
                msg = data.get("error")
                code = data.get("error_code")
                if msg:
                    self.notify(f"Błąd RD: {msg} (code {code})", severity="error")
                    return
            except Exception:
                pass
            self.notify(f"HTTP {e.response.status_code}: {e}", severity="error")
        except Exception as e:
            self.notify(f"Błąd dodawania: {e}", severity="error")

    # --- Zdarzenia z paska filtra ---
    def on_input_changed(self, event: Input.Changed) -> None:  # type: ignore[override]
        if event.input.id == "filter":
            self.filter_text = event.value
            self._render_table()


if __name__ == "__main__":
    try:
        RDTUI().run()
    except KeyboardInterrupt:
        pass