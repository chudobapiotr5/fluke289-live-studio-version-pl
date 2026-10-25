# Pamięć Fluke 289 — odczyt eksperymentalny

## Status

Moduł jest zaimplementowany i przetestowany syntetycznie, w tym przez pseudoterminal z rzeczywistym mechanizmem portu szeregowego. Użytkownik potwierdził odczyt listy i pobranie zapisów z fizycznego miernika oraz otwarcie kopii JSON w programie. Zgodność wszystkich wartości z ekranem pamięci miernika wymaga dalszego porównania. Nie deklarujemy potwierdzenia wszystkich struktur na firmware V1.41. Pierwszym odbiorem jest poprawne pobranie listy, potem pojedynczego zapisu i porównanie z ekranem miernika.

Nie dodano żadnej komendy kasowania, resetowania, zmiany nazw, synchronizacji zegara ani zapisu do miernika. Operacje modyfikujące nie znajdują się na białej liście transportu.

## Użycie

1. Włącz miernik i podłącz go przyciskiem „Połącz”. Pozostaw połączenie aktywne. Na samym mierniku wyjdź z przeglądania pamięci i wróć do bieżącego pomiaru LIVE. Użytkownik potwierdził, że podczas przeglądania zapisów na Fluke pobieranie jest niedostępne; po powrocie do LIVE działa.
2. Jeśli aplikacja zapisuje CSV/SQLite, zakończ ten zapis przyciskiem „Zatrzymaj zapis”.
3. Otwórz „Pamięć Fluke…”, a następnie „Odczytaj listę zapisów”. Program odczyta liczniki i nagłówki czterech kategorii: Measurement, MIN MAX, Peak, Recording.
4. Wybierz pozycję i kliknij „Pobierz wybrany zapis”. Przed transferem wybierz folder i nazwę pliku JSON. Anulowanie wyboru nie rozpoczyna pobierania. Po udanym transferze pełna kopia zostanie zapisana we wskazanym miejscu, a komunikat pokaże ścieżkę. Nagłówek jest ponownie sprawdzany, by wykryć zmianę zapisu między wyborem a pobraniem. Dla Recording pobierane są też kolejne interwały.
5. „Otwórz pobrane dane i wykres” pokazuje odczyty w naszym oknie historii. Pojedynczy zapis jest jednym punktem, nie sztucznym przebiegiem. „Zapisz pełną kopię…” tworzy JSON zawierający nagłówek, dane interwałów i surowe bloki w hex.
6. Kopię JSON można później wybrać przez „Otwórz pomiary…”. Jeśli zapis pliku się nie powiedzie, dane pozostają w pamięci okna; użyj „Zapisz pełną kopię…”, aby wybrać inne miejsce. Dolne przyciski pozostają widoczne także w niższym oknie.

LIVE jest wstrzymany tylko podczas transferu. Po jego zakończeniu wraca automatycznie; program nie uruchamia na nowo zapisu plikowego. Anulowanie kończy się między transakcjami — aktualna transakcja ma limit czasu. Nie odłączaj kabla w trakcie, jeśli nie chcesz wywołać błędu odczytu. Kopia jest zapisywana do pliku wybranego przed pobraniem.

Jeżeli firmware odrzuci odczyt w trakcie aktywnego RECORD/MIN MAX/Peak, zakończ ten tryb na mierniku i ponów listę. Aplikacja nie zatrzymuje go komendą zdalną. Nie zmieniaj i nie kasuj zapisów na urządzeniu podczas pobierania.

## Format i ograniczenia

Komendy tylko do odczytu: QSLS, QEMAP (wyłącznie dozwolone mapy), QSMR, QMMSI, QPSI, QRSI i QSRR. Odpowiedzi nagłówków i interwałów są binarne #0. Odczyt wykorzystuje znane długości części stałych, liczbę pól i osobną końcową nazwę; CR wewnątrz liczby binarnej nie kończy bloku. Nie stosujemy arbitralnego zaokrąglania liczb z pamięci.

Mapy kodów funkcji, jednostek i stanów są pobierane z miernika. Nieznane kody pozostają jawnie oznaczone jako UNKNOWN, bez zgadywania ich znaczenia. Wysokie słowa niepotwierdzonych indeksów interwału/licznika próbek są odrzucane, a nie ignorowane. Rozmiary i indeksy mają limity.

Dla Recording pole nazwane AVERAGE w istniejących implementacjach jest akumulatorem wymagającym interpretacji z licznikiem. Do czasu odbioru tego znaczenia na fizycznych danych nie pokazujemy go jako gotowej średniej na wykresie. Jest zachowane bez zmian w `accumulators` oraz `raw_hex` kopii JSON. PRIMARY, MINIMUM i MAXIMUM są prezentowane jako odczyty interwału, o ile ich identyfikatory i jednostki są znane. Nie jest to odtworzenie każdej szybkiej próbki wewnętrznego ADC.

Wykres Recording używa osobnego czasu każdego odczytu PRIMARY/MINIMUM/MAXIMUM z miernika, zamiast przypisywać wszystkie wartości do końca interwału. Kopia zachowuje też początek i koniec interwału. Linie łączą dostępne odczyty; nie odtwarzamy nieudostępnionych próbek wewnętrznych. Oś jest opisana jako zegar Fluke (UTC według znacznika), nie zegar komputera. Nie zakładamy synchronizacji ani ustawienia strefy czasowej miernika. Możliwa jest różnica względem jego lokalnego LCD.

Historia wykresu ma limit ostatnich 10 000 próbek; pełna kopia JSON zawiera wszystkie poprawnie pobrane interwały. Czytnik JSON ma limit 50 MiB. Duży import i lista nagłówków mogą potrwać. Aktualny moduł nie udaje, że zna format spoza zweryfikowanego układu.

## Diagnostyka i odbiór

Przy błędzie użyj „Zapisz diagnostykę…”. Plik zawiera ostatnie komendy i surowe odpowiedzi transferu; mogą w nim być nazwy zapisów oraz pomiary. Sprawdź zawartość przed udostępnieniem. Warto podać firmware, kategorię i etap: lista / nagłówek / numer interwału. Po błędzie struktury połączenie jest odtwarzane przed powrotem do LIVE.

Porównaj pierwszy pobrany Measurement/MIN MAX/Peak z ekranem pamięci Fluke: nazwa, funkcja, wartość, jednostka, miejsca dziesiętne i czas. Dla Recording porównaj liczbę interwałów i kilka pozycji trendu. Nie kasuj oryginału po samym komunikacie „Pobrano”; najpierw porównaj dane i zapisz kopię. Moduł w ogóle nie oferuje kasowania.

## Podstawa implementacji

Rozszerzony układ binarny zbadano na podstawie źródeł autorów otwartych implementacji:

- N0ury/dmm_util, `fluke_28x_dmm_util/dmm_util.py`: https://github.com/N0ury/dmm_util — źródło komend, układów i map; repozytorium deklaruje licencję MIT.
- Fredrik Valeur, dmm_util: https://github.com/fvaleur/dmm_util — wcześniejsza implementacja odczytu pamięci.
- Fluke Users Manual, Using Memory: https://assets.fluke.com/manuals/287_289_umeng0100.pdf — kategorie i sposób zapisu/odczytu z urządzenia.

Kod naszego modułu jest niezależną implementacją formatu, nie importuje ani nie kopiuje biblioteki dmm_util. Nie traktujemy badania tych źródeł jako potwierdzenia sprzętowego tego wydania.
