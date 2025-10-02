"""Main application class for Real-Debrid TUI."""

import asyncio
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.reactive import reactive
from textual.widgets import Footer, Header, Input, Log, Tabs

from rdtui.api import Aria2RPC, RDClient
from rdtui.config import DEFAULT_CONFIG, load_config, save_config
from rdtui.models import TorrentRow
from rdtui.ui import HelpModal, InputModal, QueueTable, SettingsModal, TorrentsTable
from rdtui.utils import (
    format_eta,
    format_progress,
    format_size,
    format_speed,
    is_video,
    run_downloader,
    run_mpv,
)

# pyperclip is optional – if missing, show a message
try:
    import pyperclip  # type: ignore
except Exception:
    pyperclip = None  # type: ignore


class RDTUI(App):
    """Main Real-Debrid TUI application."""

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

    # Multi-select and filter
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
        """Compose the application UI."""
        yield Header(show_clock=True)
        with Container():
            # Category tabs
            self.tabs = Tabs("Games", "Movies", "Series", "All", id="tabs")
            yield self.tabs

            # Filter bar (hidden until active)
            self.filter_bar = Horizontal(
                Input(placeholder="Pisz, by filtrować…", id="filter")
            )
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
        """Initialize the application on mount."""
        self.cfg = load_config()
        self.table.add_columns(
            "✓", "🆔 ID", "📄 Nazwa", "📦 Rozmiar", "📈 Postęp", "🗓️ Dodano", "🔖 Status"
        )
        self.table.cursor_type = "row"
        self.table.zebra_stripes = True
        # Queue table columns
        self.queue_table.add_columns(
            "Plik", "Rozmiar", "Status", "Progres", "Prędkość", "ETA", "Katalog"
        )
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
        """Set up the Real-Debrid API client."""
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
        """Initialize aria2 RPC if enabled; autostart if necessary."""
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
                    self.notify(
                        f"Nie udało się uruchomić aria2c RPC: {e}", severity="error"
                    )
                    return
            # Try again
            try:
                await self.aria2.tell_active()
            except Exception as e:
                self.notify(f"Brak połączenia z aria2 RPC: {e}", severity="warning")
                self.aria2 = None

    async def on_unmount(self):
        """Clean up resources on unmount."""
        if self.rd:
            await self.rd.close()
        if self.aria2:
            await self.aria2.close()

    # ---------------- Actions ----------------

    async def action_help(self):
        """Show help modal."""
        self.mount(HelpModal())

    async def action_settings(self):
        """Show settings modal."""
        modal = SettingsModal(self.cfg)
        self.mount(modal)

    async def action_add_magnet(self):
        """Show input modal for adding magnet/torrent/hoster link."""
        if not self.rd:
            self.notify("Brak API key.", severity="warning")
            return
        modal = InputModal(
            "Wklej: magnet / URL do .torrent / link hostera (RD)",
            "magnet:?xt=... lub https://.../plik.torrent lub https://hoster/...",
        )
        self.mount(modal)

    async def action_refresh(self):
        """Refresh the torrents list."""
        if not self.rd:
            return
        try:
            ts = await self.rd.torrents()
            self._all_rows = [TorrentRow.from_info(t) for t in ts]
            # Keep selection only for existing IDs
            self.selected_ids = {
                i for i in self.selected_ids if any(r.id == i for r in self._all_rows)
            }
            self._render_table()
        except Exception as e:
            self.notify(f"Błąd odświeżania: {e}", severity="error")

    def _row_selected_icon(self, tid: str) -> str:
        """Get the selection icon for a row."""
        return "✅" if tid in self.selected_ids else " "

    def _render_table(self):
        """Render the torrents table."""
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
        """Get filtered rows based on category and text filter."""
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
        """Determine the category of a torrent row."""
        name = (r.filename or "").lower()
        # Simple heuristic: "movies" if typical movie pattern, "series" if S01E01/season/episode, else "games"
        if (
            re.search(r"\bS\d{1,2}E\d{1,2}\b", name)
            or "season" in name
            or "episode" in name
        ):
            return "Series"
        # Movies – video file without series pattern
        if is_video(name):
            return "Movies"
        return "Games"

    def on_tabs_tab_activated(self, event):  # type: ignore[override]
        """Handle tab activation."""
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
        """Get selected IDs or current ID if none selected."""
        if self.selected_ids:
            return list(self.selected_ids)
        tid = self._current_tid()
        return [tid] if tid else []

    def _current_tid(self) -> Optional[str]:
        """Get the current torrent ID from the table cursor."""
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
        """Get the current queue GID from the queue table cursor."""
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
        """Toggle selection of current row."""
        tid = self._current_tid()
        if not tid:
            return
        if tid in self.selected_ids:
            self.selected_ids.remove(tid)
        else:
            self.selected_ids.add(tid)
        self._render_table()

    async def action_toggle_filter(self):
        """Toggle filter bar visibility."""
        self.filter_bar.display = not self.filter_bar.display
        if self.filter_bar.display:
            self.query_one("#filter", Input).focus()
        else:
            self.focus_on_table()

    def focus_on_table(self):
        """Focus the torrents table."""
        try:
            self.table.focus()
        except Exception:
            pass

    def focus_on_queue(self):
        """Focus the queue table."""
        try:
            self.queue_table.focus()
        except Exception:
            pass

    async def action_delete(self):
        """Delete selected or current torrents."""
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
        """Collect direct download links for a torrent.

        Returns:
            List of (filename, direct_url) tuples
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
                fname = (
                    unr.get("filename")
                    or item.get("filename")
                    or direct.split("/")[-1]
                )
                out.append((fname, direct))
            except Exception:
                continue
        return out

    async def refresh_queue(self):
        """Refresh the download queue from aria2."""
        if (
            not self.queue_table.display
            or not self.cfg.get("aria2_rpc_enabled", False)
            or not self.aria2
        ):
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
            eta = format_eta(total, comp, speed)
            self.download_tasks[gid] = {
                **self.download_tasks.get(gid, {}),
                "filename": filename,
                "dir": dirpath or self.download_tasks.get(gid, {}).get("dir", ""),
                "status": status,
                "size": format_size(total),
                "progress": format_progress(comp, total),
                "speed": format_speed(speed),
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
        """Open directory of the selected queue item in OS file manager."""
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
                self.notify(
                    "Brak ścieżki katalogu dla pozycji (zadanie jeszcze nie wystartowało?)",
                    severity="warning",
                )
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
        """Remove/cancel current queue item."""
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
        """Pause current queue item."""
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
        """Toggle download queue visibility."""
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
        """Download selected or current torrents."""
        if not self.rd:
            return
        ids = self._selected_or_current_ids()
        if not ids:
            return
        try:
            for tid in ids:
                links = await self._collect_links(tid)
                if not links:
                    self.notify(
                        f"[{tid}] Brak linków – torrent się przetwarza.",
                        severity="warning",
                    )
                    continue
                dl_dir = (
                    Path(self.cfg.get("download_dir", DEFAULT_CONFIG["download_dir"]))
                    / tid
                )
                dl_dir.mkdir(parents=True, exist_ok=True)
                use_rpc = (
                    self.cfg.get("aria2_rpc_enabled", False)
                    and self.aria2 is not None
                )
                if use_rpc:
                    # Add to aria2 queue via RPC
                    for fname, url in links:
                        try:
                            gid = await self.aria2.add_uri(
                                [url], out=fname, dir=str(dl_dir)
                            )  # type: ignore[arg-type]
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
                        asyncio.create_task(
                            run_downloader(
                                self.cfg.get("downloader", "aria2c"),
                                url,
                                dl_dir,
                                filename=fname,
                            )
                        )
            if not use_rpc:
                self.notify("Pobieranie uruchomione w tle ✅")
        except Exception as e:
            self.notify(f"Błąd pobierania: {e}", severity="error")

    async def action_play(self):
        """Play selected or current torrent in mpv."""
        if not self.rd:
            return
        ids = self._selected_or_current_ids()
        if not ids:
            return
        # Play only the first selected/current item
        tid = ids[0]
        try:
            links = await self._collect_links(tid)
            if not links:
                self.notify("Brak linków do odtworzenia.", severity="warning")
                return
            # Prefer video file
            video = None
            for fname, url in links:
                if is_video(fname):
                    video = (fname, url)
                    break
            if not video:
                video = links[0]
            fname, url = video
            # Fire-and-forget launch of mpv on best source (local if exists, otherwise direct URL)
            local_path = (
                Path(self.cfg.get("download_dir", DEFAULT_CONFIG["download_dir"]))
                / tid
                / fname
            )
            src = str(local_path) if local_path.exists() else url
            self.notify(f"Odtwarzanie ▶️ {fname}")
            # Don't await; keep UI responsive
            asyncio.create_task(run_mpv(self.cfg.get("mpv_path", "mpv"), src))
        except Exception as e:
            self.notify(f"Błąd odtwarzania: {e}", severity="error")

    async def action_copy_link(self):
        """Copy download links to clipboard."""
        if not self.rd:
            return
        if pyperclip is None:
            self.notify(
                "Brak biblioteki pyperclip — zainstaluj, aby kopiować linki.",
                severity="warning",
            )
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
                self.notify(
                    "Brak dostępnych linków do skopiowania.", severity="warning"
                )
                return
            pyperclip.copy("\n".join(urls))  # type: ignore
            self.notify(f"Skopiowano {len(urls)} link(ów) do schowka 🔗")
        except Exception as e:
            self.notify(f"Błąd kopiowania: {e}", severity="error")

    async def on_settings_modal_saved(self, msg: SettingsModal.Saved):
        """Handle settings modal save event."""
        self.cfg.update(msg.cfg)
        save_config(self.cfg)
        await self.setup_client()

    async def on_input_modal_submitted(self, msg: InputModal.Submitted):
        """Handle input modal submission for adding magnet/torrent/hoster."""
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
                # Heuristic: URL to .torrent -> upload to RD
                if re.search(r"\.torrent(\?|$)", raw, re.IGNORECASE):
                    self.notify("Dodawanie torrenta z URL…")
                    r = await self.rd.add_torrent_from_url(raw)
                    tid = r.get("id") or r.get("torrent") or r.get("hash") or ""
                    if not tid:
                        self.notify(
                            "Nie udało się utworzyć torrenta (.torrent)",
                            severity="error",
                        )
                        return
                    await self.rd.select_all(tid)
                    self.notify("Wybrano wszystkie pliki. Przetwarzanie w toku… 🔄")
                    await self.action_refresh()
                    return
                # Otherwise: hoster URL -> unrestrict and download
                self.notify("Przetwarzanie linku hostera przez RD…")
                unr = await self.rd.unrestrict_link(raw)
                direct = unr.get("download") or unr.get("link")
                if not direct:
                    err = unr.get("error") or "Brak direct link z RD"
                    self.notify(f"Nie udało się unrestrict: {err}", severity="error")
                    return
                fname = unr.get("filename") or direct.split("/")[-1]
                dl_dir = Path(
                    self.cfg.get(
                        "download_dir", str(Path.home() / "Downloads" / "rdtui")
                    )
                )
                use_rpc = (
                    self.cfg.get("aria2_rpc_enabled", False)
                    and self.aria2 is not None
                )
                if use_rpc:
                    try:
                        gid = await self.aria2.add_uri(
                            [direct], out=fname, dir=str(dl_dir)
                        )  # type: ignore[arg-type]
                        self.download_tasks[gid] = {
                            "tid": None,
                            "filename": fname,
                            "dir": str(dl_dir),
                            "status": "queued",
                            "progress": "0%",
                            "speed": "0 B/s",
                            "eta": "?",
                        }
                        # Ensure queue visible and timer running
                        if not self.queue_table.display:
                            self.queue_table.display = True
                            self.set_interval(2.0, self.refresh_queue, pause=False)
                        self.notify("Dodano do kolejki aria2 ⬇️")
                    except Exception as e:
                        self.notify(f"aria2 addUri error: {e}", severity="error")
                        # Fallback to local download
                        asyncio.create_task(
                            run_downloader(
                                self.cfg.get("downloader", "aria2c"),
                                direct,
                                dl_dir,
                                filename=fname,
                            )
                        )
                        self.notify("Pobieranie uruchomione w tle ✅")
                else:
                    asyncio.create_task(
                        run_downloader(
                            self.cfg.get("downloader", "aria2c"),
                            direct,
                            dl_dir,
                            filename=fname,
                        )
                    )
                    self.notify("Pobieranie uruchomione w tle ✅")
                return

            # 3) Unknown format
            self.notify(
                "Wklej magnet / URL do .torrent / link hostera.", severity="warning"
            )
        except httpx.HTTPStatusError as e:
            # Try to show RD error message
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

    def on_input_changed(self, event: Input.Changed) -> None:  # type: ignore[override]
        """Handle filter input changes."""
        if event.input.id == "filter":
            self.filter_text = event.value
            self._render_table()

    # Global key fallback to ensure actions work even when widgets capture keys
    def on_key(self, event):  # type: ignore[override]
        """Handle global key events."""
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

