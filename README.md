# Real-Debrid TUI (rdtui)

Tekstowy interfejs do Real-Debrid zbudowany na Textual.

## ✨ Nowe Funkcje (2024)

- 📊 **Wizualny pasek postępu** - Kolorowy pasek zamiast tylko procentów
- 🎨 **Kolorowanie statusów** - Każdy status ma unikalny kolor i ikonę
- 🔍 **Fuzzy search** - Inteligentne wyszukiwanie, działa nawet z literówkami
- 📝 **Przewijanie nazw** - Długie nazwy przewijają się dla zaznaczonego wiersza
- ⚡ **Quick Paste (Ctrl+V)** - Auto-wykrywanie linków ze schowka (magnet, .torrent, hostery)

**Zobacz:** `UX_IMPROVEMENTS.md` dla szczegółów | `QUICK_TEST_GUIDE.md` dla testów

---

## Funkcje
- Lista torrentów z filtrami i kategoriami (Other, Movies, Series, All)
- Dodawanie magnetów i automatyczny wybór plików
- Dodawanie linków do plików .torrent
- Dodawanie hosterów (unrestrict)
- Usuwanie, pobieranie, odtwarzanie (mpv) i kopiowanie linków
- Integracja z aria2c:
  - RPC (autostart opcjonalnie)
  - Kolejka z widokiem: Plik, Rozmiar, Status, Progres, Prędkość, ETA, Katalog
- Ustawienia zapisywane w `~/.config/rdtui/config.json`

## Wymagania
- Python 3.10+
- Pakiety z `requirements.txt`
- (Opcjonalnie) aria2c, mpv, curl/wget

## Instalacja
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Uruchomienie
```bash
# Metoda 1: Jako moduł (zalecane)
python -m rdtui

# Metoda 2: Bezpośrednio
python real_debrid_tui_python_cli.py
```

## Konfiguracja
- W aplikacji: klawisz `g` (Ustawienia)
- Ustaw API token Real-Debrid, downloader, katalog pobrań, ścieżkę do mpv
- aria2c RPC można włączyć/wyłączyć i ustawić sekret/URL

## Skróty klawiszowe (wybrane)
- Strzałki – nawigacja
- spacja – zaznacz/odznacz
- a – dodaj plik
- r – odśwież
- x – usuń
- d – pobierz
- p – odtwórz w mpv
- g – ustawienia
- f – filtr
- l – kopiuj link
- ? – pomoc
- q – wyjście
- k – przełącz widok kolejki

## Kategorie (taby)
- Games – gry i wszystko, co nie pasuje do filmów/seriali (domyślnie pierwsza)
- Movies – pliki wideo bez wzorca serialowego
- Series – wykrywane heurystyką (np. S01E01, "season", "episode")
- All – wszystkie

Uwaga: kategoryzacja oparta na nazwie pliku, to prosta heurystyka.

## Pobieranie przez aria2c
- Jeśli RPC jest włączone i dostępne, linki są dodawane do kolejki aria2c
- Tabela kolejki pokazuje Rozmiar, Progres, Prędkość i ETA

## Diagnostyka
- Komunikaty błędów pojawiają się w pasku powiadomień
- W razie problemów z tokenem RD, sprawdź ustawienia i ważność tokena

## Licencja
MIT

