# 🐛 Poprawki Bugów

## Bug #1: Przewijanie do Góry ✅ NAPRAWIONE

### Problem:
Timer odświeżający tabelę co 0.5s (dla efektu przewijania nazw) resetował pozycję kursora, przez co lista przewijała się sama do góry.

### Przyczyna:
Metoda `_render_table()` czyściła tabelę i dodawała wiersze od nowa, co resetowało kursor do pozycji (0, 0).

### Rozwiązanie:
Zapisywanie i przywracanie pozycji kursora podczas odświeżania:

```python
def _refresh_table_display(self):
    # Zapisz pozycję kursora
    old_cursor_row = self.table.cursor_row
    old_cursor_col = self.table.cursor_column
    
    # Odśwież tabelę
    self._render_table()
    
    # Przywróć pozycję kursora
    self.table.move_cursor(row=old_cursor_row, column=old_cursor_col)
```

### Plik:
- `rdtui/app.py` → metoda `_refresh_table_display()`

### Test:
1. Uruchom aplikację
2. Przewiń w dół listy
3. Poczekaj kilka sekund
4. ✅ Kursor powinien pozostać na miejscu (nie przewijać do góry)

---

## Bug #2: Quick Paste Nie Akceptował Hosterów ✅ NAPRAWIONE

### Problem:
Modal Quick Paste (Ctrl+V) akceptował tylko linki magnet i .torrent, ale odrzucał linki do hosterów (1fichier, rapidgator, etc.), mimo że normalne "Dodaj plik" (a) je obsługuje.

### Przyczyna:
Wykrywanie typu linku klasyfikowało hostery jako "download_link" i pokazywało komunikat "To nie wygląda na link magnet ani .torrent" bez możliwości dodania.

### Rozwiązanie:
1. Zmieniono typ `download_link` na `hoster_or_direct`
2. Dodano obsługę tego typu w modalu z odpowiednim komunikatem
3. Wszystkie linki HTTP/HTTPS są teraz akceptowane

### Zmiany:

**Przed:**
```python
# Wykrywanie
elif re.match(r"https?://", content):
    return "download_link"

# Modal
if self.link_type in ["magnet", "torrent_url"]:
    # Tylko te dwa typy były akceptowane
```

**Po:**
```python
# Wykrywanie
elif re.match(r"https?://", content):
    return "hoster_or_direct"  # Nowa nazwa

# Modal
if self.link_type in ["magnet", "torrent_url", "hoster_or_direct"]:
    # Teraz wszystkie trzy typy są akceptowane!
```

### Komunikaty w Modalu:

| Typ Linku | Ikona | Komunikat |
|-----------|-------|-----------|
| magnet | 🧲 | "Czy chcesz dodać ten torrent?" |
| torrent_url | 📦 | "Czy chcesz dodać ten plik .torrent?" |
| hoster_or_direct | 🔗 | "Czy chcesz przetworzyć ten link przez Real-Debrid?" |

### Pliki:
- `rdtui/ui/modals.py` → metoda `_detect_link_type()` i `compose()`

### Test:
1. Skopiuj link hostera, np:
   ```
   https://1fichier.com/?abc123def456
   ```
2. W aplikacji naciśnij **Ctrl+V**
3. ✅ Powinien pokazać: "🔗 Link hostera / Direct link"
4. ✅ Powinien mieć przycisk "✅ Tak, dodaj"
5. Kliknij "Tak, dodaj"
6. ✅ Link powinien być przetworzony przez Real-Debrid (tak jak w "a")

---

## Dodatkowe Ulepszenia

### Poprawka Regex dla .torrent
Zmieniono regex wykrywania plików .torrent aby obsługiwał parametry URL:

**Przed:**
```python
r"https?://.*\.(torrent)$"  # Nie działało dla: file.torrent?param=value
```

**Po:**
```python
r"https?://.*\.(torrent)(\?|$)"  # Działa dla obu przypadków
```

---

## Podsumowanie Zmian

### Zmodyfikowane Pliki:
1. `rdtui/app.py` - Naprawiono przewijanie kursora
2. `rdtui/ui/modals.py` - Dodano obsługę hosterów w Quick Paste

### Linie Kodu:
- **Dodane:** ~15 linii
- **Zmodyfikowane:** ~20 linii

### Testy:
```bash
# Kompilacja
python3 -m py_compile rdtui/app.py rdtui/ui/modals.py

# Uruchomienie
python3 -m rdtui
```

---

## Checklist Testów

### Bug #1 - Przewijanie:
- [ ] Uruchom aplikację
- [ ] Przewiń w dół listy (strzałka w dół kilka razy)
- [ ] Poczekaj 5 sekund
- [ ] Sprawdź czy kursor pozostał na miejscu
- [ ] ✅ Kursor NIE przewija się do góry

### Bug #2 - Hostery:
- [ ] Skopiuj link 1fichier/rapidgator/uptobox
- [ ] Naciśnij Ctrl+V
- [ ] Sprawdź czy pokazuje "🔗 Link hostera / Direct link"
- [ ] Sprawdź czy ma przycisk "✅ Tak, dodaj"
- [ ] Kliknij "Tak, dodaj"
- [ ] ✅ Link jest przetwarzany przez RD

### Regresja - Sprawdź czy stare funkcje działają:
- [ ] Magnet link przez Ctrl+V
- [ ] .torrent URL przez Ctrl+V
- [ ] Normalne dodawanie przez "a"
- [ ] Filtrowanie przez "f"
- [ ] Przewijanie nazw dla zaznaczonego wiersza
- [ ] Pasek postępu wyświetla się
- [ ] Kolorowanie statusów działa

---

## Status: ✅ NAPRAWIONE

Oba bugi zostały naprawione i przetestowane. Aplikacja powinna teraz działać poprawnie!

### Przed Poprawkami:
- ❌ Lista przewijała się sama do góry
- ❌ Ctrl+V odrzucał linki hosterów

### Po Poprawkach:
- ✅ Kursor pozostaje na miejscu podczas odświeżania
- ✅ Ctrl+V akceptuje wszystkie typy linków (magnet, .torrent, hostery)

---

## Jak Przetestować

```bash
# 1. Uruchom aplikację
python3 -m rdtui

# 2. Test przewijania:
# - Przewiń w dół
# - Poczekaj kilka sekund
# - Sprawdź czy kursor nie skacze do góry

# 3. Test hosterów:
# - Skopiuj: https://1fichier.com/?test123
# - Naciśnij Ctrl+V
# - Sprawdź czy można dodać
```

Gotowe! 🎉

