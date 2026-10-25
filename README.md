# Fluke 289 Live Studio 1.7.0 — PL version

**Język interfejsu: polski. / Interface language: Polish.**

Wolne oprogramowanie do współpracy z fizycznym Fluke 289 na GNU/Linux: podgląd odczytów, bargraf, automatyczny widok MIN MAX, wykresy, zoom, znaczniki A/B, zapis CSV/SQLite z czasomierzem, pobieranie pamięci Fluke, biblioteka pomiarów i porównanie nagrań z raportem PDF/CSV. Niezależny projekt; nie jest produktem ani oficjalnym oprogramowaniem Fluke.

**Licencja: GNU GPL v3 lub nowsza (`GPL-3.0-or-later`).** Pełny tekst: [COPYING](COPYING). Możesz używać, analizować, modyfikować i rozpowszechniać program zgodnie z licencją. Program jest udostępniany bez gwarancji. Sam projekt nie jest częścią Projektu GNU.

## Instalator DEB i ikona w menu

Pakiet `fluke289-live_1.7.0-1_all.deb` instaluje program systemowo i dodaje ikonę **Fluke 289 Live Studio** do menu aplikacji. Otwórz plik w systemowym instalatorze pakietów i wybierz instalację. Jeśli Twoje środowisko nie obsługuje instalacji dwuklikiem, w folderze pobranego pliku użyj:

```bash
sudo apt install ./fluke289-live_1.7.0-1_all.deb
```

APT dobierze systemowe zależności: Python 3.12 lub nowszy, Tk, pySerial i Cairo. Pierwsza instalacja może wymagać dostępu do repozytoriów Ubuntu/Debiana. Pakiet jest przeznaczony dla systemów spełniających te zależności, w tym Ubuntu 24.04 i nowszych. Nie ma w nim `.venv`, nagrań ani sterowników Windows. Po instalacji uruchamiaj z menu; terminal nie jest potrzebny do codziennej pracy. Sam program zawsze uruchamiaj jako zwykły użytkownik, nie przez sudo.

DEB nie usuwa wcześniejszego folderu ze źródłami i pomiarami. Biblioteka korzysta z tego samego katalogu danych użytkownika. Jeśli port wymaga grupy `dialout`, zastosuj instrukcję poniżej. Do aktualizacji zainstaluj nowszy DEB. Usunięcie pakietu nie usuwa Twoich plików pomiarowych ani katalogu biblioteki. Tworzenie pakietu opisano w docs/ROZWOJ.md. Instalacja systemowa i uruchomienie z menu wymagają odbioru na komputerze użytkownika; podczas budowania wykonujemy test rozpakowanej paczki bez instalacji.

## Szybkie uruchomienie ze źródeł na Ubuntu 24.04

Z katalogu projektu:

```bash
sudo apt update
sudo apt install python3-venv python3-tk libcairo2
python3 -m venv .venv
.venv/bin/python -m pip install .
./uruchom.sh
```

Podłącz zgodny adapter optyczny (np. IR189USB), włącz miernik, wybierz port i kliknij **Połącz**. Domyślnie działa sam podgląd; zapis na dysk włączasz osobno. Przy kolejnych uruchomieniach wystarczy `./uruchom.sh`.

Jeżeli port wymaga członkostwa w `dialout`:

```bash
sudo usermod -aG dialout "$USER"
```

Po zmianie grupy wyloguj się z całej sesji i zaloguj ponownie. Nie uruchamiaj programu jako root.

## Aktualizacja

Zakończ zapis i zamknij program. Zachowaj kopię swoich nagrań. Nową paczkę rozpakuj do osobnego folderu i wykonaj instalację opisaną powyżej; nie kopiuj starej `.venv`. Wersja 1.7.0 czyta wcześniejsze CSV/SQLite i kopie pamięci JSON. Biblioteka zapamiętuje ścieżki plików w katalogu danych użytkownika; po przeniesieniu nagrań dodaj ich nowy folder.

Jeśli korzystasz bezpośrednio z aktualizowanych źródeł w tym folderze, wystarczy ponownie uruchomić `./uruchom.sh`. Wersję i build sprawdzisz w „O programie”. Program nie aktualizuje się przez internet.

## Dokumentacja

- [Instrukcja użytkownika](docs/UZYTKOWNIK.md) — ekran główny, bargraf, MIN MAX, historia, A/B, zapis i eksport.
- [Protokół i ograniczenia](docs/PROTOKOL.md) — potwierdzone dane Fluke, format odczytu, stany i czasy.
- [Odczyt pamięci Fluke (eksperymentalny)](docs/PAMIEC.md) — lista zapisów, pobieranie i pełna kopia.
- [Formaty plików](docs/FORMATY.md) — CSV, SQLite i odtwarzanie odczytów.
- [Diagnostyka i odbiór sprzętowy](docs/DIAGNOSTYKA.md).
- [Dokumentacja programistyczna](docs/ROZWOJ.md) — architektura, testy, przygotowanie buildu i paczek.
- [Walidacja](docs/WALIDACJA.md) — co sprawdzono automatycznie, co potwierdził użytkownik i czego jeszcze nie zweryfikowano.
- [Autorstwo i współpraca](AUTHORS.md), [historia zmian](CHANGELOG.md), [składniki zewnętrzne](THIRD_PARTY.md).
- [Raport testów](TESTY.txt), [manifest buildu](fluke289/data/build_info.json).

W programie otwórz **O programie**. Dokumentacja, licencja, autorstwo, build i wynik testów są dostępne także offline w tym oknie.

## Narzędzia tekstowe

```bash
./uruchom.sh ports
./uruchom.sh diagnose /dev/ttyUSB0 --database diagnostyka.sqlite3
./uruchom.sh export pomiary.sqlite3 pomiary.csv
./uruchom.sh --version
.venv/bin/python -m unittest discover -s tests -v
```

Diagnostyka jawnie zapisuje log do wskazanej bazy. Zwykłe połączenie w GUI nie tworzy plików pomiarowych, dopóki sam nie włączysz zapisu. Pliki mogą zawierać numer seryjny miernika i pomiary; paczka źródeł nie zawiera sesji użytkownika ani środowiska `.venv`.

Bieżący kod i dokumentacja są przygotowane do udostępnienia, ale nie zostały automatycznie opublikowane w żadnym publicznym repozytorium.
