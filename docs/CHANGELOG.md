# Changelog - Real-Debrid TUI

## 🎉 Najnowsze zmiany

### ✅ Funkcja #1: Reactive Watchers (Auto-refresh)
**Data:** 2025-10-02

**Co to robi:**
- Automatyczne odświeżanie tabeli gdy zmienia się filtr (klawisz `f`)
- Automatyczne odświeżanie tabeli gdy zmienia się kategoria (Gry/Filmy/Seriale/Wszystko)
- Nie trzeba już ręcznie odświeżać po zmianie filtra

**Implementacja:**
- Dodano `watch_filter_text()` - watcher dla reactive attribute `filter_text`
- Dodano `watch_active_category()` - watcher dla reactive attribute `active_category`
- Zabezpieczenie: sprawdzamy `hasattr()` i `is_mounted` przed wywołaniem `_render_table()`

**Plik:** `rdtui/app.py` linie 87-96

**Test:**
1. Uruchom aplikację: `python3 -m rdtui`
2. Naciśnij `f` i zacznij pisać - tabela odświeża się automatycznie
3. Przełącz kategorię (Tab) - tabela odświeża się automatycznie

---

### ✅ Funkcja #2: Command Palette (Ctrl+P)
**Data:** 2025-10-02

**Co to robi:**
- Paleta komend jak w VS Code
- Szybkie wyszukiwanie akcji po nazwie
- Pokazuje wszystkie dostępne komendy ze skrótami klawiszowymi
- Filtrowanie w czasie rzeczywistym

**Implementacja:**
- Nowy modal: `CommandPaletteModal` w `rdtui/ui/modals.py`
- Fuzzy search po nazwie akcji, klawiszu i opisie
- Limit 10 wyników na raz
- Zamknięcie: ESC lub przycisk "Zamknij"
- **Fix:** Użyto `with Vertical()` w `compose()` zamiast `mount()` (unikamy MountError)
- **Fix:** `call_later()` dla update listy akcji (unikamy render conflicts)

**Pliki:**
- `rdtui/ui/modals.py` linie 328-437 (nowy modal)
- `rdtui/ui/__init__.py` (export)
- `rdtui/app.py` linie 238-254 (akcja `action_command_palette`)

**Test:**
1. Uruchom aplikację: `python3 -m rdtui`
2. Naciśnij `Ctrl+P`
3. Wpisz np. "pobierz" - pokaże akcję "Pobierz zaznaczone (d)"
4. ESC aby zamknąć

---

### 🐛 Bugfix #1: Duplikaty w tabeli torrentów
**Data:** 2025-10-02

**Problem:**
- Komunikat "The row key already exists" przy starcie aplikacji
- API Real-Debrid czasami zwraca duplikaty torrentów

**Rozwiązanie:**
- Deduplikacja w `action_refresh()` - usuwamy duplikaty po ID przed dodaniem do `_all_rows`
- Dodatkowa ochrona w `_render_table()` - sprawdzamy czy klucz już został dodany
- Try-except przy `add_row()` - ignorujemy błędy duplikatów

**Pliki:**
- `rdtui/app.py` linie 291-315 (deduplikacja w refresh)
- `rdtui/app.py` linie 345-379 (ochrona w render)

---

### 🐛 Bugfix #2: Wiele modali naraz
**Data:** 2025-10-02

**Problem:**
- Można było otworzyć wiele modali jednocześnie (np. kilka palet komend, kilka pomocy)
- Powodowało to zamieszanie w UI

**Rozwiązanie:**
- Dodano flagę `_modal_open` w `RDTUI`
- Sprawdzanie flagi przed otwarciem modala
- Resetowanie flagi gdy modal się zamyka (Message `Closed`)
- Dodano `Closed` message do `HelpModal` i `CommandPaletteModal`

**Pliki:**
- `rdtui/app.py` linie 95, 236-268, 979-988 (flaga i handlery)
- `rdtui/ui/modals.py` (Closed messages)

---

### 🐛 Bugfix #3: Pobieranie torrentów - 404 not found (NAPRAWIONE!)
**Data:** 2025-10-02

**Problem:**
- Pobieranie torrentów kończyło się błędem 404
- Komunikat: "Pobieranie info dla torrenta ID: 'The Necromancers Tale'" - **używano nazwy pliku zamiast ID!**
- `_current_tid()` zwracało nazwę pliku zamiast ID torrenta
- Błąd "cannot use variable use_rpc" w `action_download()`

**Przyczyna:**
- `_current_tid()` używało starego API Textual 5.x
- W Textual 6.2+ trzeba użyć `coordinate_to_cell_key(cursor_coordinate)` aby dostać klucz wiersza

**Rozwiązanie:**
1. **Naprawiono `_current_tid()`** (linie 466-508):
   - Użyto Textual 6.2+ API: `cursor_coordinate` + `coordinate_to_cell_key()`
   - `coordinate_to_cell_key()` zwraca `CellKey(row_key, column_key)` - NamedTuple
   - `row_key` to obiekt `RowKey` (dziedziczy po `StringKey`)
   - Dostęp do wartości przez `row_key.value` (atrybut `StringKey`)
   - Fallback dla Textual 5.x (jeśli ktoś używa starszej wersji)
   - Usunięto błędny fallback który czytał wartość z kolumny (nazwa pliku)

2. **Naprawiono `action_download()`** (linie 842-910):
   - Przeniesiono `use_rpc` poza pętlę `for tid in ids:`
   - Teraz `use_rpc` jest zawsze zdefiniowane

3. **Dodano szczegółowe logowanie** w `_collect_links()` (linie 634-693):
   - 🔍 Pokazuje ID torrenta przed wywołaniem API
   - 📦 Pokazuje liczbę znalezionych linków
   - ❌ Pokazuje dokładny błąd jeśli `torrent_info()` nie działa
   - ⚠️ Pokazuje błędy unrestrict dla każdego linku

**Pliki:**
- `rdtui/app.py` linie 466-508 (`_current_tid` z Textual 6.2+ API i `row_key.value`)
- `rdtui/app.py` linie 842-910 (`action_download` z naprawionym `use_rpc`)
- `rdtui/app.py` linie 634-693 (`_collect_links` z logowaniem)

**Test:**
1. Zaznacz torrent
2. Naciśnij `d` (pobierz)
3. Sprawdź komunikaty:
   - 🔍 "Pobieranie info dla torrenta ID: ABC123XYZ" (alfanumeryczne ID, NIE nazwa pliku!)
   - 📦 "Znaleziono X linków dla ABC123XYZ"
   - Pobieranie powinno działać!

---

### 🐛 Bugfix #4: Wyszukiwarka zajmuje pół ekranu
**Data:** 2025-10-02

**Problem:**
- Pole wyszukiwania (filter bar) zajmowało pół ekranu zamiast tylko górę
- Fuzzy search był zbyt liberalny (threshold=40)

**Rozwiązanie:**
- Dodano CSS dla `#filter-bar`:
  - `height: auto` - automatyczna wysokość
  - `max-height: 3` - maksymalnie 3 linie
  - `padding: 0 1` - padding dla lepszego wyglądu
- Dodano `id="filter-bar"` do kontenera filtra
- Zwiększono threshold fuzzy search z 40 na 50 (lepsza precyzja)

**Pliki:**
- `rdtui/app.py` linie 52-67 (CSS), 125-131 (filter bar z ID), 424 (threshold)

**Test:**
1. Naciśnij `f` aby otworzyć wyszukiwarkę
2. Pole powinno zajmować tylko górę ekranu (max 3 linie)
3. Wpisz tekst - wyniki powinny być bardziej precyzyjne

---

### 🐛 Bugfix #5: Kursor wraca na górę przy odświeżaniu
**Data:** 2025-10-02

**Problem:**
- Przy odświeżaniu tabeli (co 0.5s lub ręcznie) kursor zawsze wracał na górę listy
- Użytkownik tracił pozycję na której był
- Szczególnie irytujące przy przeglądaniu długiej listy torrentów

**Rozwiązanie:**
- Zapisywanie pozycji kursora przed `_render_table()`:
  - Zapisujemy `cursor_coordinate` (row, column)
  - Zapisujemy `current_row_key` (ID torrenta) aby znaleźć wiersz po kluczu
- Przywracanie pozycji po odświeżeniu:
  - **Preferowane:** Znajdź wiersz po `row_key` i ustaw kursor tam (działa nawet jeśli kolejność się zmieniła)
  - **Fallback:** Ustaw kursor na tym samym indeksie (jeśli wiersz został usunięty, użyj najbliższego)
  - **Default:** Jeśli nic nie działa, ustaw na górę (0, 0)

**Pliki:**
- `rdtui/app.py` linie 373-438 (`_render_table` z zachowaniem pozycji kursora)

**Test:**
1. Przewiń listę torrentów w dół
2. Zaznacz jakiś torrent w środku listy
3. Poczekaj na auto-refresh (lub naciśnij `r`)
4. Kursor powinien pozostać na tym samym torrencie! ✅

---

### ✅ Organizacja dokumentacji
- Wszystkie pliki `.md` przeniesione do katalogu `docs/`
- Lepsza struktura projektu

### ✅ Kategorie po polsku
- `Games` → `Gry`
- `Movies` → `Filmy`
- `Series` → `Seriale`
- `All` → `Wszystko`

### ✅ Statusy po polsku
- `downloading` → "Pobieranie"
- `downloaded/finished` → "Pobrane"
- `error` → "Błąd"
- `queued` → "W kolejce"
- `magnet_error` → "Błąd magnet"
- `waiting_files_selection` → "Wybór plików"
- `compressing` → "Kompresja"
- `uploading` → "Wysyłanie"
- `virus` → "Wirus"
- `dead` → "Martwy"

### ✅ Lepsze UX w menu
**Nowa kolejność opcji:**
1. Podstawowe akcje (Dodaj, Wklej, Odśwież, Szukaj)
2. Operacje na plikach (Zaznacz, Pobierz, Usuń, Kopiuj link)
3. Widoki i ustawienia (Kolejka, Ustawienia, Pomoc)
4. Wyjście (na końcu)

### ✅ Pasek postępu w kolejce pobrań
- Kolorowy wizualny pasek: `████████████░░░░░░░░ 60%`
- Kolory: czerwony → pomarańczowy → żółty → cyan → zielony
- Automatycznie w kolumnie "Progres"

### ✅ Powiadomienia systemowe
- Powiadomienie gdy pobieranie się kończy
- Działa na macOS, Windows i Linux
- Wymaga: `pip install plyer`
- Tytuł: "Pobieranie zakończone"
- Treść: "✅ [nazwa pliku]"

### ✅ Inne poprawki
- Usunięto kolumnę "ID" (niepotrzebna)
- Zwiększono max_width nazwy pliku z 60 na 70
- Poprawiono komunikaty błędów aria2
- Usunięto wyszarzenie długich nazw plików
- Naprawiono scroll i zaznaczenie w tabeli
- Naprawiono skok do góry przy zaznaczaniu (spacja)
- Usunięto opcję "Otwórz lokalizację" z listy torrentów (tylko w kolejce)

---

## Wcześniejsze zmiany

### Refaktoryzacja
- Podział monolitycznego pliku na moduły
- Struktura pakietu `rdtui/`
- Separacja: API, UI, modele, utils

### UX Improvements
- Pasek postępu dla torrentów
- Fuzzy search
- Kolorowanie statusów
- Quick Paste (Ctrl+V)
- Skracanie długich nazw

### Bugfixy
- Auto-odświeżanie usunięte
- Scroll działa poprawnie
- Kolejka wyświetla się w split view
- Kursor nie skacze przy zaznaczaniu

