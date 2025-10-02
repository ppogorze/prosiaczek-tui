"""Modal dialog components."""

from typing import Any, Dict
import re

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import Button, Input, Label, Static


class HelpModal(Static):
    """Modal dialog showing keyboard shortcuts help."""

    DEFAULT_CSS = """
    HelpModal {
        background: $panel;
        border: round $primary;
        padding: 1 2;
        width: 80%;
        height: auto;
    }
    """

    class Closed(Message):
        """Message sent when modal is closed."""
        pass

    def compose(self) -> ComposeResult:
        """Compose the help modal UI."""
        yield Label("❓ Pomoc — skróty klawiszowe")
        txt = "\n".join(
            [
                "[b]Strzałki[/b] – nawigacja po liście",
                "[b]spacja[/b] – zaznacz/odznacz wiersz (multi-select)",
                "[b]a[/b] – dodaj plik (🧲)",
                "[b]Ctrl+V[/b] – szybkie wklejenie ze schowka (✨ NOWE!)",
                "[b]f[/b] – filtr w locie (🔎 fuzzy search)",
                "[b]l[/b] – kopiuj link(i) do schowka (🔗)",
                "[b]r[/b] – odśwież (🔄)",
                "[b]x[/b] – usuń zaznaczone lub bieżący (❌)",
                "[b]d[/b] – pobierz zaznaczone lub bieżący (⬇️)",
                "[b]p[/b] – odtwórz w mpv (▶️)",
                "[b]g[/b] – ustawienia (⚙️)",
                "[b]?[/b] – pomoc",
                "[b]q[/b] – wyjście",
            ]
        )
        yield Static(txt)
        yield Button("Zamknij", id="close")

    def on_button_pressed(self, _: Button.Pressed):
        """Handle button press to close modal."""
        self.post_message(self.Closed())
        self.remove()


class InputModal(Static):
    """Modal dialog for text input."""

    class Submitted(Message):
        """Message sent when input is submitted."""

        def __init__(self, value: str):
            """Initialize the message.

            Args:
                value: The submitted input value
            """
            self.value = value
            super().__init__()

    DEFAULT_CSS = """
    InputModal { background: $panel; border: round $success; padding: 1 2; width: 80%; }
    Input { width: 100%; }
    """

    def __init__(self, title: str, placeholder: str = "", password: bool = False):
        """Initialize the input modal.

        Args:
            title: Modal title
            placeholder: Input placeholder text
            password: Whether to mask input as password
        """
        super().__init__()
        self.title = title
        self.placeholder = placeholder
        self.password = password

    def compose(self) -> ComposeResult:
        """Compose the input modal UI."""
        yield Label(self.title)
        yield Input(placeholder=self.placeholder, password=self.password, id="inp")
        yield Horizontal(Button("OK", id="ok"), Button("Anuluj", id="cancel"))

    def on_mount(self):
        """Focus the input field when mounted."""
        self.query_one(Input).focus()

    def on_button_pressed(self, ev: Button.Pressed):
        """Handle button press.

        Args:
            ev: Button pressed event
        """
        if ev.button.id == "ok":
            self.post_message(self.Submitted(self.query_one(Input).value))
            self.remove()
        elif ev.button.id == "cancel":
            self.remove()


class SettingsModal(Static):
    """Modal dialog for application settings."""

    class Saved(Message):
        """Message sent when settings are saved."""

        def __init__(self, cfg: Dict[str, Any]):
            """Initialize the message.

            Args:
                cfg: The saved configuration dictionary
            """
            self.cfg = cfg
            super().__init__()

    DEFAULT_CSS = """
    SettingsModal { background: $panel; border: round $primary; padding: 1 2; width: 80%; }
    Input { width: 100%; }
    """

    def __init__(self, cfg: Dict[str, Any]):
        """Initialize the settings modal.

        Args:
            cfg: Current configuration dictionary
        """
        super().__init__()
        self.cfg = cfg.copy()

    def compose(self) -> ComposeResult:
        """Compose the settings modal UI."""
        yield Label("⚙️ Ustawienia")
        self.api = Input(
            value=self.cfg.get("api_key", ""),
            placeholder="Real-Debrid API token",
            password=True,
        )
        self.down = Input(
            value=self.cfg.get("downloader", "aria2c"),
            placeholder="Downloader: aria2c/curl/wget",
        )
        self.dir = Input(
            value=self.cfg.get("download_dir", ""),
            placeholder="Katalog pobrań (dla RPC: na zdalnej maszynie)",
        )
        self.mpv = Input(
            value=self.cfg.get("mpv_path", "mpv"), placeholder="Ścieżka do mpv"
        )
        # aria2 RPC
        self.a2_enabled = Input(
            value=str(self.cfg.get("aria2_rpc_enabled", True)).lower(),
            placeholder="aria2 RPC włączone: true/false",
        )
        self.a2_url = Input(
            value=self.cfg.get("aria2_rpc_url", "http://127.0.0.1:6800/jsonrpc"),
            placeholder="aria2 RPC URL: http://host:6800/jsonrpc",
        )
        self.a2_secret = Input(
            value=self.cfg.get("aria2_rpc_secret", ""),
            placeholder="aria2 RPC secret (opcjonalnie)",
        )
        self.a2_autostart = Input(
            value=str(self.cfg.get("aria2_autostart", True)).lower(),
            placeholder="Autostart lokalnego aria2c: true/false",
        )
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
        """Handle button press.

        Args:
            ev: Button pressed event
        """
        if ev.button.id == "save":

            def _pbool(s: str) -> bool:
                """Parse boolean from string."""
                return s.strip().lower() in {"1", "true", "t", "yes", "y", "on"}

            self.cfg.update(
                {
                    "api_key": self.api.value.strip(),
                    "downloader": self.down.value.strip() or "aria2c",
                    "download_dir": self.dir.value.strip(),
                    "mpv_path": self.mpv.value.strip() or "mpv",
                    "aria2_rpc_enabled": _pbool(self.a2_enabled.value),
                    "aria2_rpc_url": self.a2_url.value.strip()
                    or "http://127.0.0.1:6800/jsonrpc",
                    "aria2_rpc_secret": self.a2_secret.value.strip(),
                    "aria2_autostart": _pbool(self.a2_autostart.value),
                }
            )
            self.post_message(self.Saved(self.cfg))
            self.remove()
        else:
            self.remove()


class QuickPasteModal(Static):
    """Modal for quick paste detection with link preview."""

    DEFAULT_CSS = """
    QuickPasteModal {
        background: $panel;
        border: thick $success;
        padding: 1 2;
        width: 70%;
        height: auto;
    }

    QuickPasteModal Label {
        margin: 1 0;
    }

    QuickPasteModal .link-preview {
        background: $surface;
        color: $text;
        padding: 1;
        margin: 1 0;
        border: solid $primary;
    }
    """

    class Confirmed(Message):
        """Message sent when user confirms the paste."""

        def __init__(self, link: str, link_type: str):
            self.link = link
            self.link_type = link_type
            super().__init__()

    def __init__(self, clipboard_content: str):
        super().__init__()
        self.clipboard_content = clipboard_content
        self.link_type = self._detect_link_type(clipboard_content)

    def _detect_link_type(self, content: str) -> str:
        """Detect what type of link this is."""
        content = content.strip()

        if content.startswith("magnet:"):
            return "magnet"
        elif re.match(r"https?://.*\.(torrent)(\?|$)", content, re.IGNORECASE):
            return "torrent_url"
        elif re.match(r"https?://", content):
            # Może być hoster (1fichier, rapidgator, etc.) lub direct link
            return "hoster_or_direct"
        else:
            return "unknown"

    def compose(self) -> ComposeResult:
        """Compose the quick paste modal UI."""
        icon_map = {
            "magnet": "🧲",
            "torrent_url": "📦",
            "hoster_or_direct": "🔗",
            "unknown": "❓"
        }

        type_name_map = {
            "magnet": "Link Magnet",
            "torrent_url": "Plik .torrent (URL)",
            "hoster_or_direct": "Link hostera / Direct link",
            "unknown": "Nieznany typ"
        }

        icon = icon_map.get(self.link_type, "❓")
        type_name = type_name_map.get(self.link_type, "Nieznany")

        yield Label(f"{icon} Wykryto w schowku: {type_name}")

        # Preview linku (skrócony)
        preview = self.clipboard_content[:100]
        if len(self.clipboard_content) > 100:
            preview += "..."

        yield Static(preview, classes="link-preview")

        if self.link_type in ["magnet", "torrent_url", "hoster_or_direct"]:
            # Różne komunikaty w zależności od typu
            if self.link_type == "magnet":
                yield Label("💡 Czy chcesz dodać ten torrent?")
            elif self.link_type == "torrent_url":
                yield Label("💡 Czy chcesz dodać ten plik .torrent?")
            else:  # hoster_or_direct
                yield Label("💡 Czy chcesz przetworzyć ten link przez Real-Debrid?")

            yield Horizontal(
                Button("✅ Tak, dodaj", id="confirm", variant="success"),
                Button("❌ Anuluj", id="cancel", variant="error")
            )
        else:
            yield Label("⚠️ To nie wygląda na prawidłowy link")
            yield Button("Zamknij", id="cancel")

    def on_button_pressed(self, event: Button.Pressed):
        """Handle button press."""
        if event.button.id == "confirm":
            self.post_message(self.Confirmed(self.clipboard_content, self.link_type))
        self.remove()


class CommandPaletteModal(Static):
    """Command palette for quick action search (like VS Code)."""

    DEFAULT_CSS = """
    CommandPaletteModal {
        background: $panel;
        border: thick $accent;
        padding: 1 2;
        width: 60;
        height: auto;
        max-height: 25;
    }

    CommandPaletteModal Input {
        margin: 0 0 1 0;
    }

    CommandPaletteModal #actions-list {
        height: auto;
        max-height: 15;
        border: solid $primary;
        padding: 1;
    }

    CommandPaletteModal .action-item {
        padding: 0 1;
    }

    CommandPaletteModal .action-item:hover {
        background: $accent;
    }
    """

    class ActionSelected(Message):
        """Message sent when action is selected."""

        def __init__(self, action: str):
            super().__init__()
            self.action = action

    class Closed(Message):
        """Message sent when modal is closed."""
        pass

    def __init__(self, actions: list[tuple[str, str, str]]):
        """Initialize with available actions.

        Args:
            actions: List of (action_name, key, description) tuples
        """
        super().__init__()
        self.all_actions = actions
        self.filtered_actions = actions

    def compose(self) -> ComposeResult:
        """Compose the command palette UI."""
        yield Label("🔍 Paleta komend (Ctrl+P)")
        yield Input(placeholder="Wpisz nazwę akcji...", id="search")

        # Actions list container - yield children directly
        with Vertical(id="actions-list"):
            for action_name, key, description in self.filtered_actions[:10]:  # Limit to 10
                yield Label(f"[b]{description}[/b] ({key})", classes="action-item")

        yield Horizontal(
            Button("Zamknij [ESC]", id="close", variant="default"),
        )

    def on_input_changed(self, event: Input.Changed):
        """Filter actions based on search input."""
        if event.input.id != "search":
            return

        query = event.value.lower().strip()

        if not query:
            self.filtered_actions = self.all_actions
        else:
            # Simple fuzzy search
            self.filtered_actions = [
                (name, key, desc)
                for name, key, desc in self.all_actions
                if query in desc.lower() or query in key.lower() or query in name.lower()
            ]

        # Update actions list - use call_later to avoid render conflicts
        self.call_later(self._update_actions_list)

    def _update_actions_list(self):
        """Update the actions list display."""
        try:
            actions_list = self.query_one("#actions-list", Vertical)
            actions_list.remove_children()

            for action_name, key, description in self.filtered_actions[:10]:
                actions_list.mount(
                    Label(f"[b]{description}[/b] ({key})", classes="action-item")
                )
        except Exception:
            # Ignore if not mounted yet
            pass

    def on_button_pressed(self, event: Button.Pressed):
        """Handle button press."""
        self.post_message(self.Closed())
        self.remove()

    def on_key(self, event):
        """Handle key press."""
        if event.key == "escape":
            self.post_message(self.Closed())
            self.remove()
            event.prevent_default()

