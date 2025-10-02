#!/usr/bin/env python3
"""
Real-Debrid TUI (Textual-based CLI)

This file is kept for backward compatibility.
The application has been refactored into a modular package structure.

For the new modular code, see the rdtui/ package.

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
    python real_debrid_tui_python_cli.py
    # lub
    python -m rdtui

Uwaga: Real-Debrid API — ustaw token w Ustawieniach (g) lub przez plik konfiguracyjny.

Plik konfiguracyjny:
    Linux/macOS: ~/.config/rdtui/config.json
    Windows: %APPDATA%/rdtui/config.json

Autor: ChatGPT
"""

# Import the refactored application
from rdtui.app import RDTUI


if __name__ == "__main__":
    try:
        RDTUI().run()
    except KeyboardInterrupt:
        pass

