# 💡 Sugestie Ulepszeń - Funkcjonalność i UX

## 🎯 Priorytet WYSOKI - Szybkie Wygrane

### 1. **Pasek Postępu dla Torrentów**
**Problem**: Obecnie tylko tekst "45%" - trudno ocenić wizualnie  
**Rozwiązanie**: Dodać kolorowy pasek postępu

```python
# W models/torrent.py
def pretty_progress_bar(self) -> Text:
    """Wizualny pasek postępu."""
    pct = int(self.progress)
    filled = int(pct / 5)  # 20 bloków = 100%
    empty = 20 - filled
    
    bar = "█" * filled + "░" * empty
    color = "green" if pct == 100 else "yellow" if pct > 50 else "red"
    
    return Text(f"{bar} {pct}%", style=color)
```

### 2. **Sortowanie Kolumn**
**Problem**: Brak możliwości sortowania (np. po rozmiarze, dacie)  
**Rozwiązanie**: Kliknięcie na nagłówek sortuje

```python
# Dodać w app.py
BINDINGS = [
    ...
    Binding("s", "toggle_sort", "Sortuj", priority=True),
]

sort_by: str = "added"  # added, size, name, progress
sort_reverse: bool = True

async def action_toggle_sort(self):
    """Cykliczne przełączanie sortowania."""
    options = ["added", "size", "name", "progress", "status"]
    current_idx = options.index(self.sort_by)
    self.sort_by = options[(current_idx + 1) % len(options)]
    self.notify(f"Sortowanie: {self.sort_by}")
    self._render_table()
```

### 3. **Wyszukiwanie Zamiast Filtra**
**Problem**: Filtr jest OK, ale można lepiej  
**Rozwiązanie**: Fuzzy search z podświetlaniem

```python
# Dodać w utils/search.py
from fuzzywuzzy import fuzz  # pip install fuzzywuzzy

def fuzzy_search(query: str, items: List[TorrentRow], threshold: int = 60) -> List[TorrentRow]:
    """Wyszukiwanie rozmyte."""
    results = []
    for item in items:
        score = fuzz.partial_ratio(query.lower(), item.filename.lower())
        if score >= threshold:
            results.append((score, item))
    
    # Sortuj po trafności
    results.sort(reverse=True, key=lambda x: x[0])
    return [item for score, item in results]
```

### 4. **Podgląd Plików w Torrencie**
**Problem**: Nie wiadomo co jest w środku torrenta przed pobraniem  
**Rozwiązanie**: Klawisz [i] pokazuje szczegóły

```python
# Nowy modal w ui/modals.py
class TorrentDetailsModal(Static):
    """Pokazuje pliki w torrencie."""
    
    def __init__(self, torrent_info: Dict[str, Any]):
        super().__init__()
        self.info = torrent_info
    
    def compose(self) -> ComposeResult:
        yield Label(f"📦 {self.info.get('filename', 'Torrent')}")
        
        # Lista plików
        files = self.info.get('files', [])
        tree = Tree("Pliki:")
        for f in files:
            size = humanize.naturalsize(f.get('bytes', 0))
            tree.add_leaf(f"{f.get('path', '?')} ({size})")
        
        yield tree
        yield Button("Zamknij", id="close")
```

### 5. **Statystyki w Nagłówku**
**Problem**: Brak szybkiego przeglądu  
**Rozwiązanie**: Pokaż statystyki w headerze

```python
# W app.py
def _update_stats(self):
    """Aktualizuj statystyki w headerze."""
    total = len(self._all_rows)
    downloading = sum(1 for r in self._all_rows if r.status == "downloading")
    finished = sum(1 for r in self._all_rows if r.status == "finished")
    total_size = sum(r.size for r in self._all_rows)
    
    stats = f"📊 {total} torrentów | ⬇️ {downloading} | ✅ {finished} | 💾 {humanize.naturalsize(total_size)}"
    self.sub_title = stats  # Textual feature
```

## 🎨 Priorytet ŚREDNI - Poprawa UX

### 6. **Kolorowanie Statusów**
**Problem**: Wszystkie statusy wyglądają podobnie  
**Rozwiązanie**: Różne kolory dla różnych statusów

```python
# W models/torrent.py
def pretty_status(self) -> Text:
    status_config = {
        "queued": ("⏳", "yellow"),
        "downloading": ("🔽", "blue"),
        "finished": ("✅", "green"),
        "error": ("❌", "red"),
        "magnet_error": ("⚠️", "orange"),
    }
    
    icon, color = status_config.get(self.status, ("🔷", "white"))
    return Text(f"{icon} {self.status}", style=color)
```

### 7. **Potwierdzenie Przed Usunięciem**
**Problem**: Łatwo przypadkowo usunąć torrent  
**Rozwiązanie**: Modal z potwierdzeniem

```python
# Nowy modal w ui/modals.py
class ConfirmModal(Static):
    """Modal potwierdzenia."""
    
    class Confirmed(Message):
        def __init__(self, confirmed: bool):
            self.confirmed = confirmed
            super().__init__()
    
    def __init__(self, message: str):
        super().__init__()
        self.message = message
    
    def compose(self) -> ComposeResult:
        yield Label(f"⚠️ {self.message}")
        yield Horizontal(
            Button("Tak", id="yes", variant="error"),
            Button("Nie", id="no", variant="primary")
        )
```

### 8. **Historia Pobrań**
**Problem**: Nie wiadomo co było pobrane wcześniej  
**Rozwiązanie**: Zakładka "Historia"

```python
# W config/manager.py
def save_download_history(filename: str, url: str, timestamp: datetime):
    """Zapisz do historii."""
    history_file = get_config_dir() / "history.json"
    history = []
    
    if history_file.exists():
        history = json.loads(history_file.read_text())
    
    history.append({
        "filename": filename,
        "url": url,
        "timestamp": timestamp.isoformat(),
    })
    
    # Zachowaj tylko ostatnie 100
    history = history[-100:]
    history_file.write_text(json.dumps(history, indent=2))
```

### 9. **Skróty do Kategorii**
**Problem**: Trzeba klikać myszką na taby  
**Rozwiązanie**: Klawisze 1-4 przełączają kategorie

```python
# W app.py
BINDINGS = [
    ...
    Binding("1", "category_games", "Games", priority=True),
    Binding("2", "category_movies", "Movies", priority=True),
    Binding("3", "category_series", "Series", priority=True),
    Binding("4", "category_all", "All", priority=True),
]

async def action_category_games(self):
    self.active_category = "Games"
    self._render_table()
```

### 10. **Automatyczne Odświeżanie**
**Problem**: Trzeba ręcznie odświeżać  
**Rozwiązanie**: Auto-refresh co X sekund (opcjonalnie)

```python
# W app.py
async def on_mount(self):
    ...
    # Auto-refresh co 30 sekund jeśli włączone
    if self.cfg.get("auto_refresh", True):
        self.set_interval(30.0, self.action_refresh)
```

## 🚀 Priorytet NISKI - Nice to Have

### 11. **Drag & Drop Plików .torrent**
**Problem**: Trzeba wklejać URL  
**Rozwiązanie**: Przeciągnij plik .torrent na okno

### 12. **Powiadomienia Systemowe**
**Problem**: Nie wiadomo kiedy pobieranie się skończyło  
**Rozwiązanie**: Powiadomienie desktop

```python
# W utils/notifications.py
import subprocess

def notify(title: str, message: str):
    """Wyślij powiadomienie systemowe."""
    if sys.platform == "darwin":
        subprocess.run([
            "osascript", "-e",
            f'display notification "{message}" with title "{title}"'
        ])
    elif sys.platform.startswith("linux"):
        subprocess.run(["notify-send", title, message])
```

### 13. **Eksport Listy Torrentów**
**Problem**: Brak możliwości eksportu  
**Rozwiązanie**: Eksport do CSV/JSON

```python
# W app.py
async def action_export(self):
    """Eksportuj listę do CSV."""
    import csv
    from datetime import datetime
    
    filename = f"torrents_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['ID', 'Nazwa', 'Status', 'Postęp', 'Rozmiar', 'Dodano'])
        
        for row in self._all_rows:
            writer.writerow([
                row.id,
                row.filename,
                row.status,
                f"{row.progress}%",
                row.pretty_size(),
                row.pretty_added()
            ])
    
    self.notify(f"Wyeksportowano do {filename}")
```

### 14. **Motywy Kolorystyczne**
**Problem**: Tylko jeden wygląd  
**Rozwiązanie**: Jasny/ciemny motyw

```python
# W app.py
CSS = """
.dark {
    background: $surface;
    color: $text;
}

.light {
    background: white;
    color: black;
}
"""

async def action_toggle_theme(self):
    """Przełącz motyw."""
    self.dark = not self.dark
```

### 15. **Integracja z Plex/Jellyfin**
**Problem**: Ręczne dodawanie do biblioteki  
**Rozwiązanie**: Automatyczne powiadomienie serwera

```python
# W utils/media_server.py
async def notify_plex(library_path: str):
    """Powiadom Plex o nowych plikach."""
    plex_url = "http://localhost:32400/library/sections/all/refresh"
    async with httpx.AsyncClient() as client:
        await client.get(plex_url)
```

## 🎯 Moje TOP 5 Rekomendacji

Jeśli miałbym wybrać 5 najważniejszych:

1. **Pasek postępu** (#1) - Natychmiastowa poprawa wizualna
2. **Podgląd plików** (#4) - Bardzo przydatne przed pobraniem
3. **Statystyki w nagłówku** (#5) - Szybki przegląd
4. **Potwierdzenie usunięcia** (#7) - Bezpieczeństwo
5. **Auto-refresh** (#10) - Wygoda

## 🛠️ Które Chcesz Zaimplementować?

Mogę dodać dowolne z tych funkcji. Które najbardziej Cię interesują?

Przykładowe kombinacje:
- **Quick Win**: #1, #5, #10 (30 min pracy)
- **Power User**: #2, #4, #8 (2h pracy)
- **Full Package**: Wszystkie z HIGH priority (4h pracy)

Daj znać co Cię interesuje! 🚀

