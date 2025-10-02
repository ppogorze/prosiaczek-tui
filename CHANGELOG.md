# Changelog - Real-Debrid TUI

## Najnowsze zmiany

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

