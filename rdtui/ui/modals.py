"""Modal dialog components."""

from typing import Any, Dict

from textual.app import ComposeResult
from textual.containers import Horizontal
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

    def compose(self) -> ComposeResult:
        """Compose the help modal UI."""
        yield Label("❓ Pomoc — skróty klawiszowe")
        txt = "\n".join(
            [
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
            ]
        )
        yield Static(txt)
        yield Button("Zamknij", id="close")

    def on_button_pressed(self, _: Button.Pressed):
        """Handle button press to close modal."""
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

