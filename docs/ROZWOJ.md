# Rozwój, testowanie i wydawanie

## Licencja i współpraca

Kod i dokumentacja projektu: GPL-3.0-or-later. Zachowaj nagłówki copyright/SPDX, COPYING i wskazanie autorstwa. Swoje zmiany opisz i datuj. Przy rozpowszechnianiu zmodyfikowanej wersji przestrzegaj GPL, w tym udostępnienia odpowiedniego kodu źródłowego. Nie usuwaj cudzych warunków licencyjnych ze składników zewnętrznych. Projekt nie ma jeszcze publicznego repozytorium ani automatycznego kanału zgłoszeń.

## Środowisko

Python >=3.12, tkinter, pySerial >=3.5,<4; Cairo jest opcjonalną biblioteką systemową. Standardowa instalacja jest w README. Testy portów pseudoterminalowych wymagają systemu POSIX/Linux. Nie wymagają fizycznego miernika, a emulator jest ograniczony do testów.

## Architektura

- `protocol.py`: dataclasses Snapshot/Reading, walidacja QDDA, tokeny i wnioskowanie pokrętła.
- `transport.py`: wyłączny port, transakcje, timeout/limit, ID i QDDA.
- `worker.py`: jeden właściciel portu i aktywnego zapisu, komendy start/stop zapisu, retry i kolejka GUI.
- `display.py`: format zgodny z mnożnikiem/miejscami dziesiętnymi miernika.
- `storage.py`: SQLite/bezpośredni CSV i eksport.
- `history.py`: ograniczona pamięć i import read-only.
- `gui.py`: ekran główny, sterowanie połączeniem/zapisem i aktualizacja widgetów w wątku Tk.
- `mini_chart.py`: podgląd LIVE na ekranie głównym, AUTO, zoom i dymki.
- `history_gui.py`: pełny wykres, wybór pól, osie, nawigacja i A/B.
- `viewport.py`, `markers.py`: niezależne od Tk modele nawigacji i znaczników.
- `bargraph.py`, `minmax.py`: reprezentacja danych miernika bez wymyślania brakujących statystyk.
- `trace_renderer.py`: Cairo przez ctypes, jeden wątek renderowania i ograniczone kolejki. Wątki renderowania nigdy nie wywołują Tk. Tylko najnowsza klatka trafia do GUI; błędy pozostawiają wykres wektorowy.
- `memory.py`, `memory_gui.py`: eksperymentalny odczyt pamięci, mapy binarne, lista i pobieranie, kopie JSON; ten sam wątek jest jedynym właścicielem portu.
- `about.py`: offline dokumenty i metadane buildu.
- `__main__.py`: GUI i CLI ports/diagnose/export/--version.

Nie zapisuj pomiarów ani surowych ramek podczas samego podglądu. Wyjątkiem jest jawnie wybrany przez użytkownika tryb CLI diagnose. Nie przekazuj obiektów Tk do wątków. Nie wyznaczaj ostrzeżeń bezpieczeństwa na podstawie lokalnego progu. Używaj wyłącznie danych potwierdzonych protokołem.

## Testy i odbiór

```bash
python3 -m unittest discover -s tests -v
```

Testy muszą sprawdzać znaczenie zmian, nie tylko odzwierciedlać implementację. Dla obsługi sprzętu wykonaj osobno DIAGNOSTYKA.md i dopisz wynik do WALIDACJA.md. Nie zmieniaj odbioru „do sprawdzenia” na „OK” na podstawie syntetycznej próbki. Skanowanie źródeł i walidacja metadanych nie oznaczają, że pełne okno było uruchomione na realnym ekranie.

## Build i paczki

```bash
python3 tools/release.py
```

Skrypt:

1. Kopiuje kanoniczną dokumentację z katalogu głównego/docs do zasobów pakietu `fluke289/data`, aby dokumenty działały po instalacji wheel i bez sieci.
2. Uruchamia testy w bieżącym interpreterze i zapisuje raport (łącznie z ostrzeżeniami środowiska).
3. Liczy SHA-256 jawnej listy kodu, testów, dokumentacji i plików pakietowania; wyklucza generowane TESTY.txt i build_info.json, aby nie tworzyć samoodwołania.
4. Zapisuje manifest z wersją, datą UTC, build ID, odciskiem, sumami poszczególnych plików i wynikiem testów.
5. Tworzy archiwum źródeł i plik SHA256SUMS w katalogu dist.

Build ID jest skrótem odcisku, nie podpisem kryptograficznym autora. Zmiana źródeł wymaga ponownego uruchomienia skryptu; samo ręczne edytowanie plików nie aktualizuje manifestu. Czasy testów/data mogą być różne, ale identyczny zestaw plików daje ten sam odcisk źródeł. Skrypt nie publikuje wydania w Internecie.

Opcjonalnie, po odświeżeniu zasobów/manifestu:

```bash
python3 -m pip wheel --no-deps --no-build-isolation . --wheel-dir dist
```

Do wheel potrzebne są zależności budowania z pyproject.toml. `pip install .` również je przygotowuje. Przed dystrybucją sprawdź zawartość paczki: kod, testy, dokumentacja, COPYING i zasoby. Nie dodawaj `.venv`, lokalnych CSV/SQLite/WAL, zdjęć, haseł, kluczy, numerów seryjnych z sesji ani cache. Biblioteki systemowe i pySerial nie są pakowane ze źródłami projektu.

## Plan rozwoju

Niezrealizowane: biblioteka sesji z indeksem, notatki na wykresie, eksport wykresu PNG/PDF i trwałe ustawienia interfejsu. Nie deklaruj tych funkcji w wydaniu, dopóki nie zostaną zaimplementowane i sprawdzone.


## Pakiet Debian/Ubuntu

Po `python3 tools/release.py` uruchom `python3 tools/build_deb.py`. Potrzebne jest systemowe `dpkg-deb`; budowanie nie wymaga roota. Pakiet instaluje kod w `/usr/share/fluke289-live`, launcher w `/usr/bin/fluke289`, plik desktop w `/usr/share/applications` i własną ikonę SVG. Deklaruje zależności dystrybucyjne Python/Tk/pySerial/Cairo; nie pobiera pakietów podczas budowania i nie zawiera środowiska wirtualnego ani danych użytkownika.

Weryfikacja bez instalacji: `dpkg-deb --info dist/*.deb`, rozpakowanie przez `dpkg-deb --extract` do katalogu testowego i uruchomienie `usr/bin/fluke289 --version` z rozpakowanego drzewa. To potwierdza strukturę i importy; nie zastępuje instalacji APT ani wizualnego testu menu aplikacji.
