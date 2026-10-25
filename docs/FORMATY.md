# Formaty i prywatność danych

## CSV

UTF-8 z BOM, przecinek jako separator, kropka dziesiętna. Wiersz opisuje pojedyncze pole odczytu w jednej próbce; pola LIVE, PRIMARY, MINIMUM itd. mają osobne wiersze. Import w programie wykorzystuje event_id + pc_utc + identity do zgrupowania próbki.

| Grupa kolumn | Znaczenie |
| --- | --- |
| event_id, pc_utc, identity | identyfikator zdarzenia/próbki, UTC komputera, model/firmware/serial |
| primary_function, secondary_function, modes | funkcja, podfunkcja i flagi trybu |
| range_mode, range_unit, range_number, range_multiplier | zakres zgłoszony przez miernik |
| lightning | ON/OFF z miernika |
| reading_id | pole LCD, np. PRIMARY |
| value_base, unit | liczba w jednostkach bazowych i kod jednostki |
| multiplier, decimals, digits | parametry odtworzenia formatu LCD |
| state, attribute | stan odczytu i atrybut |
| meter_time_raw | surowy znacznik zegara miernika |
| display_value, display_unit, display_text | odczyt gotowy do prezentacji, z zachowaniem zer |

Dla nieprawidłowych stanów value_base jest puste. Stan i atrybut pozostają w pliku. CSV nie zawiera surowych ramek ani pełnej historii błędów komunikacji. Wartości bazowe i metadane są źródłem odtwarzania odczytu, także w starszym CSV bez display_*. Dodatkowe kolumny mogą być ignorowane przez starsze wersje czytnika.

Tekst rozpoczynający się znakami mogącymi uruchomić formułę w arkuszu jest poprzedzany apostrofem. Dotyczy to także niektórych tekstowych reprezentacji wartości ujemnych; aplikacja odtwarza liczbę z value_base i metadanych, nie z chronionego display_text. Sam arkusz może automatycznie zmieniać typy i usuwać zera — plik i nasz czytnik zachowują metadane.

Plik jest otwierany wyłącznie jako nowy (tryb x), by nie nadpisać poprzednich danych. Bufor jest opróżniany po każdej próbce, ale nie deklarujemy odporności na awarię zasilania jak dla transakcji SQLite.

## SQLite

Tabela `events(id INTEGER PRIMARY KEY, time TEXT, kind TEXT, data TEXT)` zawiera zdarzenia uporządkowane ID. data to JSON, time to ISO 8601 UTC komputera.

- identity: tekst modelu/firmware/numeru seryjnego;
- wire: kierunek TX/RX i surowa linia ASCII;
- snapshot: komplet rozkodowanej odpowiedzi z listą readings i raw;
- error: opis błędu komunikacji.

Każde zdarzenie jest osobną transakcją. Ustawiono WAL i synchronous=FULL. Podczas pracy mogą istnieć pliki -wal i -shm: przed kopiowaniem bazy zakończ zapis. Nie usuwa się ich ręcznie podczas aktywnej sesji. Aplikacja może dopisywać do istniejącej bazy po decyzji użytkownika.

Czytnik otwiera bazę w trybie read-only. Wczytuje ostatnie 10 000 próbek, zachowując właściwą identyfikację i znane przerwy. Cała baza nadal zawiera wcześniejszy zapis. Nie modyfikujemy oryginalnego pliku przy przeglądaniu.

## Co nie trafia do pliku

A/B, zoom, wysokość tabeli, wybrane linie i notatki użytkownika nie są obecnie zapisywane. Wybór linii na wykresie nie filtruje zapisu: plik otrzymuje wszystkie pola zwrócone przez miernik. Historia bez aktywnego zapisu jest ulotna. Zapis nie obejmuje wstecz okresu samego podglądu.

## Prywatność

Pomiary, identyfikacja miernika i numery seryjne są lokalne. Aplikacja nie ma telemetrii, serwera ani przesyłania danych do chmury. „O programie → Kopiuj informacje” nie dołącza numeru seryjnego ani pomiarów. Diagnostyka i bazy mogą je zawierać. Przed udostępnieniem pliku sprawdź jego zawartość. Skrypt wydania używa jawnej listy plików; nie pakuje sesji, zdjęć, .venv, cache ani lokalnych konfiguracji.


## Zachowanie przerw komunikacji w CSV

Nowe CSV zawierają dodatkową kolumnę `communication_gap`: wartość 1 przy pierwszej próbce sesji, po ponownej identyfikacji oraz przy pierwszej próbce po błędzie komunikacji. Flaga jest powtarzana dla pól tej samej próbki. Nie dodaje się fikcyjnej wartości 0 ani pustej próbki. Eksport SQLite do CSV także przenosi informacje o błędach i wznowieniu.

Starsze CSV bez tej kolumny pozostają obsługiwane. Importer szacuje typowy odstęp z maksymalnie 2000 pierwszych dodatnich odstępów próbek. Pauza dłuższa od maksimum 2 sekund i trzykrotności mediany rozpoczyna nową linię wykresu. To ostrożna heurystyka dla starych plików, nie dokładny zapis momentu utraty łączności; nieregularne próbkowanie i zmiany zegara mogą wpływać na rozpoznanie. Plik źródłowy nie jest zmieniany.
