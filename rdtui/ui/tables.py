"""Custom table widgets with contextual bindings."""

from textual.binding import Binding
from textual.widgets import DataTable


class TorrentsTable(DataTable):
    """Table widget for displaying torrents with custom key bindings."""

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
        """Forward toggle_select action to app."""
        await self.app.action_toggle_select()

    async def action_add_magnet(self):
        """Forward add_magnet action to app."""
        await self.app.action_add_magnet()

    async def action_refresh(self):
        """Forward refresh action to app."""
        await self.app.action_refresh()

    async def action_delete(self):
        """Forward delete action to app."""
        await self.app.action_delete()

    async def action_download(self):
        """Forward download action to app."""
        await self.app.action_download()

    async def action_play(self):
        """Forward play action to app."""
        await self.app.action_play()

    async def action_copy_link(self):
        """Forward copy_link action to app."""
        await self.app.action_copy_link()

    async def action_toggle_filter(self):
        """Forward toggle_filter action to app."""
        await self.app.action_toggle_filter()

    def on_focus(self, _event):
        """Handle focus event."""
        try:
            self.app.queue_active = False
        except Exception:
            pass

    def on_mouse_down(self, _event):
        """Ensure the table gets focus on click."""
        try:
            self.focus()
        except Exception:
            pass


class QueueTable(DataTable):
    """Table widget for displaying download queue with custom key bindings."""

    BINDINGS = [
        Binding("o", "queue_open_location", "Otwórz lokalizację", priority=True),
        Binding("x", "queue_remove", "Usuń / Anuluj", priority=True),
        Binding("p", "queue_pause", "Pauza", priority=True),
    ]

    async def action_queue_open_location(self):
        """Forward queue_open_location action to app."""
        await self.app.action_queue_open_location()

    async def action_queue_remove(self):
        """Forward queue_remove action to app."""
        await self.app.action_queue_remove()

    async def action_queue_pause(self):
        """Forward queue_pause action to app."""
        await self.app.action_queue_pause()

    def on_focus(self, _event):
        """Handle focus event."""
        try:
            self.app.queue_active = True
        except Exception:
            pass

    def on_mouse_down(self, _event):
        """Ensure the table gets focus on click."""
        try:
            self.focus()
        except Exception:
            pass

