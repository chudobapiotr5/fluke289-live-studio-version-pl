# Instrukcja użytkownika — Fluke 289 Live Studio

## 1. Sprzęt i połączenie

Wymagany jest Fluke 289 oraz kabel optyczny obsługujący ten model i udostępniający port szeregowy, np. Fluke IR189USB. Zwykły adapter sieciowy USB IrDA nie jest automatycznie zamiennikiem. Miernik wykonuje pomiary niezależnie; aplikacja odpytuje go o dane ekranu.

Podłącz i zamocuj głowicę, włącz miernik, kliknij „Odśwież” i wybierz port (zwykle `/dev/ttyUSB0`). Możesz ręcznie wpisać ścieżkę `/dev/serial/by-id/...`, stabilniejszą przy ponownym podłączeniu. Ustaw odstęp 0.2–3600 sekund (kropka dziesiętna), kliknij „Połącz”. Domyślny odstęp wynosi 0.5 s; nie gwarantuje identycznej chwili odczytu co LCD. „Rozłącz” zamyka połączenie i kończy aktywny zapis.

Funkcję, podfunkcję, zakres i tryby ustawiasz na Fluke. Program śledzi odpowiedzi miernika i nie przełącza jego funkcji zdalnie. Nie wysyła resetu.

## 2. Odczyt i ostrzeżenia

Duży wynik odpowiada polu PRIMARY. Jednostka, mnożnik i liczba miejsc po przecinku pochodzą z miernika; końcowe zera są zachowywane. LIVE to osobne pole — może różnić się od PRIMARY, np. przy HOLD lub REL. Tabela pokazuje wszystkie otrzymane pola wraz ze stanami i surowym czasem miernika.

OL, OL_MINUS, INVALID, BLANK, DISCHARGE i OPEN_TC nie są zastępowane zwykłą liczbą. Atrybuty takie jak OPEN_CIRCUIT, SHORT_CIRCUIT czy GOOD_DIODE pozostają osobno. Nieznane funkcje/tryby są pokazywane jako surowe nazwy z ostrzeżeniem, bez wymyślania obsługi.

Piorun obok wyniku zapala się wyłącznie na podstawie `lightningBolt=ON` przesłanego przez Fluke. Przy OFF jest ukryty; przy utracie lub nieaktualności danych wyświetlany jest brak aktualnego stanu. Brak ikony nie jest potwierdzeniem bezpiecznego napięcia. Zawsze obowiązują wskazania miernika i instrukcja jego bezpiecznego użytkowania; aplikacja nie jest urządzeniem ochronnym.

## 3. Bargraf i MIN MAX

Bargraf korzysta z aktualnej skali AUTO/MANUAL zgłoszonej przez miernik. Jeżeli zwrócono zgodne pole BARGRAPH, jest źródłem paska. Zwykle używany jest LIVE, co jest jawnie podpisane „z LIVE • odświeżanie USB”. Taki pasek nie ma szybkości wewnętrznego bargrafu LCD. Dla nieobsługiwanej skali lub niezgodnych jednostek wyświetlany jest brak danych zamiast zgadywania.

Po włączeniu MIN MAX na Fluke po lewej pojawia się panel Maximum, Average i Minimum zamiast bargrafu. Wartości i formaty pochodzą z miernika. Czasy są różnicami znacznika danego pola i startu MIN MAX przesłanego przez Fluke. Aplikacja nie liczy zastępczych statystyk z wolniejszych próbek USB. Wyjście z trybu przywraca bargraf; utrata połączenia usuwa nieaktualne wartości.

## 4. Miniwykres na ekranie głównym

Wybierz pole (np. LIVE, PRIMARY, MINIMUM, MAXIMUM lub AVERAGE, jeśli jest dostępne). „AUTO • blokada” pokazuje ostatnią minutę i blokuje ręczne przybliżanie/przesuwanie. Odznacz, aby używać kółka i przeciągania. Ponowne zaznaczenie przywraca automat.

Najazd na obszar wykresu pokazuje najbliższą czasowo rzeczywistą próbkę, jej wartość w formacie Fluke i czas komputera. Nie jest to interpolowany pomiar pomiędzy punktami. Dwuklik otwiera pełną historię. Znane przerwy i nieprawidłowe odczyty przerywają linię. Kolorowe linie są wygładzane wyłącznie graficznie; nie dopasowujemy krzywej ani nie zmieniamy próbek.

Złap górną krawędź tabeli na całej szerokości i przeciągnij: zmiana wysokości tabeli oddaje miejsce wykresowi i panelowi odczytu. Ustawienie nie jest jeszcze zapamiętywane po zamknięciu programu.

## 5. Pełna historia i zoom

„Wykres i historia” otwiera historię zbieraną w pamięci także bez zapisu na dysk. Wybierz serię funkcji/trybu, jednostkę i widoczne pola. Różne jednostki nie są mieszane na jednej osi. Zmiana funkcji, podfunkcji lub flag trybu zaczyna oddzielną serię.

Kółko nad wykresem powiększa oś czasu wokół kursora; przeciąganie lewym przyciskiem przesuwa widok. Dwuklik lub „Cały przebieg” przywraca pełny zakres wybranej serii. Możesz wybrać ostatnią minutę albo pięć minut. Oś wartości dopasowuje się automatycznie do widocznych poprawnych próbek. Minimum ręcznego zakresu czasu to 1 ms — to ograniczenie nawigacji, nie deklaracja rozdzielczości rejestracji.

Ręczna nawigacja wyłącza śledzenie aktualnej funkcji, żeby nowe pomiary nie odciągały od oglądanego fragmentu. Zaznacz „Śledź aktualną funkcję miernika”, jeśli chcesz automatycznie wracać do bieżącej serii. Podsumowanie zakresu widocznych próbek jest statystyką widoku; linie MINIMUM/MAXIMUM/AVERAGE są danymi Fluke.

## 6. Porównanie A/B

Wybierz pole w „PORÓWNANIE A/B”, kliknij „Ustaw A” i wskaż próbkę; powtórz z B. Program wybiera najbliższą czasowo poprawną próbkę wybranego pola, a nie dowolny punkt pomiędzy próbkami. Panel pokazuje A, B, Δt i Δ wartości (B − A). Jeśli B jest wcześniejsze od A, Δt jest ujemne.

Znaczniki można przeciągać. Zwykłe przeciąganie poza ich liniami nadal przesuwa wykres. Esc anuluje wybieranie; „Wyczyść A/B” usuwa oba punkty. Znaczniki pozostają przypięte do próbek podczas zoomu. Punkt poza widokiem pozostaje w panelu, choć jego linia nie jest rysowana. Zmiana pola/funkcji/jednostki usuwa znaczniki. Nie są zapisywane w pliku i znikają po zamknięciu okna.

## 7. Opcjonalny zapis

Połączenie zaczyna się bez zapisu. W sekcji „ZAPIS NA DYSK” wybierz:

- CSV — tabela do przenoszenia danych lub ponownego otwarcia w programie.
- SQLite — pełna sesja z odczytami, identyfikacją, błędami i surową komunikacją.

Kliknij „Rozpocznij zapis…”, wybierz miejsce i nazwę. „Zatrzymaj zapis” zamyka plik bez rozłączania miernika. Potem możesz wybrać inny format lub nowy plik. CSV wymaga nowej nazwy; istniejąca baza SQLite jest rozszerzana po potwierdzeniu. Zapis obejmuje tylko czas, gdy był aktywny — wcześniejszy podgląd nie jest dopisywany wstecz. Nowe połączenie ponownie zaczyna się bez zapisu.

Czerwone REC oznacza otwarty zapis przy aktualnym połączeniu, REC WYŁ. brak zapisu, a REC · PRZERWA brak aktualnych danych przy nadal otwartym pliku. Po odzyskaniu połączenia zapis może być kontynuowany. Błąd dysku wyłącza zapis z komunikatem, pozostawiając podgląd.

## 8. Otwieranie plików i eksport

„Otwórz pomiary…” otwiera CSV zapisany przez program lub bazę SQLite w osobnym oknie historii, bez modyfikowania pliku i bez zewnętrznych aplikacji. Wczytywanie odbywa się w tle. „Starsza baza → CSV…” konwertuje bazę SQLite do CSV. Bezpośrednio zapisanego CSV nie trzeba eksportować ponownie.

CSV zawiera wartości bazowe i metadane formatu oraz czytelne kolumny display_*. Tę samą próbkę odtwarzamy w tym samym formacie co podczas odbioru. Więcej: FORMATY.md.

## 9. Pamięć, czas i ograniczenia

Historia i import pokazują ostatnie 10 000 próbek. Plik aktywnego zapisu nie ma tego ograniczenia. Bez zapisu historia znika po zamknięciu programu. A/B, wysokość tabeli, port i układ okien nie są obecnie trwale zapamiętywane.

Oś czasu używa zegara komputera; surowe znaczniki miernika są oddzielnymi danymi. Dokładność fizycznego pomiaru zależy od funkcji, zakresu i warunków specyfikacji Fluke. Liczba cyfr, szybkość USB i zoom nie zwiększają dokładności ani liczby próbek. To odpytywanie ekranu, nie oscyloskop. Eksperymentalny odczyt archiwum z pamięci miernika opisuje PAMIEC.md. Nie sterujemy menu urządzenia.

## 10. O programie

Przycisk „O programie” pokazuje autorstwo, współpracę z OpenAI Codex, wersję, datę i identyfikator buildu, raport testów oraz informacje o środowisku. Zakładki udostępniają instrukcję, dokumentację, zmiany i pełny tekst GPL offline. „Kopiuj informacje” kopiuje tylko dane o aplikacji i środowisku — bez pomiarów i numeru seryjnego miernika.

## 11. Pamięć Fluke

Połącz miernik, zakończ ewentualny zapis pliku i kliknij „Pamięć Fluke…”. Najpierw odczytaj listę, potem wybierz zapis i pobierz go. Transfer wstrzymuje LIVE i po zakończeniu oddaje port podglądowi. Kopia JSON jest zapisywana tylko na żądanie. Szczegóły, ograniczenia interpretacji średniej interwałów i procedura pierwszego odbioru: PAMIEC.md.


## Czas nagrania w programie

W sekcji zapisu zaznacz „Czas nagrania” i ustaw dni, godziny, minuty oraz sekundy. Przykład: 0 dni, 0 godzin, 5 minut, 0 sekund. Następnie kliknij „Rozpocznij zapis…” i wybierz plik. Limit jest ustalany przy rozpoczęciu zapisu, po wyborze pliku; zmiana pól podczas nagrania nie zmienia bieżącego limitu. Odznaczenie opcji przed startem oznacza nagranie bez limitu.

Odliczanie pokazuje pozostały czas. Po jego upływie program zamyka plik i pozostawia podgląd LIVE. Możesz też wcześniej kliknąć „Zatrzymaj zapis”. Limit obejmuje czas przerw w komunikacji i nie steruje Recording na samym mierniku. Operacja portu będąca w toku może opóźnić komunikat zakończenia; przed kolejnym zapisem danych sprawdzany jest limit czasu.


## Porównanie dwóch zapisów

Kliknij „Porównaj zapisy…” nad tabelą. Wybierz plik A i B (CSV, SQLite lub kopia pamięci JSON), a następnie serię i pole każdego zapisu, np. PRIMARY w Hz. Jednostki muszą być takie same. „Czas miernika” używa czasów odczytów przesłanych przez Fluke również w CSV; omija różnicę zegara komputera. Jeśli czas miernika jest niedostępny, wybierz „Od początku obu serii”. Ten tryb wyrównuje początki wybranych serii, nie identyfikuje wspólnego zdarzenia.

Przesunięcie B podawaj w sekundach: dodatnie przesuwa B później, ujemne wcześniej. Kliknij „Porównaj na jednym wykresie”. Linie A i B mają osobne kolory i przełączniki; działają zoom, kursor i znaczniki. Nazwy plików i przesunięcie są w tytule wykresu. Aby zmienić dopasowanie, wróć do okna wyboru, zmień przesunięcie i otwórz nowe porównanie. Pliki źródłowe i wartości pozostają bez zmian. Różnice szybkich zmian mogą wynikać z odmiennych chwil próbkowania — nakładanie wykresów nie jest kalibracją.

Po wczytaniu obu plików pola są dobierane automatycznie, z pierwszeństwem PRIMARY w tej samej jednostce. Widoczny komunikat podaje wynik. Nie ma osobnego przycisku dobierania; przycisk „Porównaj na jednym wykresie” otwiera wynik. Pola można zmienić ręcznie w listach.


### Podsumowanie porównania

Ustaw maksymalny odstęp czasu dopasowania (domyślnie 0,5 s). Pod wykresem widoczne są wspólny okres, liczba par, liczba zgodnych odczytów na wspólnej, mniej dokładnej rozdzielczości, średnia i największa bezwzględna różnica wartości oraz maksymalny odstęp czasowy. Statystyka obejmuje cały wspólny okres, niezależnie od zoomu i ukrywania linii. Przesunięcie B jest uwzględniane przed dopasowaniem.

Każdy punkt A proponuje najbliższy ważny punkt B w limicie. Propozycje są rozpatrywane od najmniejszego odstępu czasu; punkt B jest używany najwyżej raz. Przy konflikcie propozycja jest pomijana. Dopasowanie jest kierunkowe A do B; zamiana źródeł może zmienić wynik przy różnych częstotliwościach próbkowania. OL i inne nieważne odczyty nie są porównywane; nie interpolujemy ani nie tworzymy brakujących próbek. Brak wspólnego okresu lub par jest jawnie sygnalizowany. Wartości różnic są w jednostkach bazowych osi (np. OHM oznacza Ω), bez zmiany danych źródłowych.

„Pokaż parę z największą różnicą” przybliża tę parę i oznacza wartości oraz czasy A i B. To porównanie zapisów z różnych chwil próbkowania, nie pomiar dokładności ani kalibracja miernika.


### Eksport porównania do PDF i CSV

W oknie wykresu porównania kliknij „Eksportuj raport…” i wybierz PDF albo CSV. Wskaż folder i nazwę pliku. Istniejący plik jest zastępowany dopiero po pomyślnym utworzeniu całego raportu. Pliki pomiarowe nie są zmieniane.

PDF zawiera wykres obu źródeł dla całego wspólnego okresu, nazwy plików (bardzo długie nazwy mogą być skrócone), pola, jednostkę bazową, tryb czasu, przesunięcie B, limit dopasowania, statystyki i czasy/wartości pary o największej różnicy. PDF jest rysowany wektorowo przez systemową bibliotekę Cairo używaną już do wykresów. Aktualny zoom i ukrycie linii nie zmieniają zakresu eksportu. Gdy nie ma wspólnego okresu lub dopasowanych par, raport wyraźnie to opisuje.

CSV (UTF-8 z BOM) zawiera każdą dopasowaną parę, jej wartości w jednostkach bazowych, czasy po dopasowaniu, oryginalne czasy miernika, różnicę bezwzględną i ze znakiem B-A, odstęp czasowy, zgodność na wspólnej rozdzielczości oraz ustawienia porównania i pełne nazwy źródeł. Przy braku par zawiera sam nagłówek. Tekstowe nazwy zaczynające się znakiem formuły są zabezpieczone apostrofem dla arkuszy.

Raport dotyczy zgodności zapisów, nie jest świadectwem kalibracji ani oceną rzeczywistej dokładności miernika. Przed udostępnieniem sprawdź, czy nazwy plików i dane pomiarowe mogą być upublicznione.


## Biblioteka pomiarów

Kliknij „Biblioteka pomiarów…” nad tabelą w oknie głównym. Przy pierwszym użyciu wybierz „Dodaj folder…” i wskaż folder z dotychczasowymi nagraniami, np. folder programu. „Z podfolderami” obejmuje także podkatalogi; domyślnie skanowany jest tylko wskazany folder. „Dodaj pliki…” pozwala wskazać pojedyncze pliki lub wiele plików. Obsługiwane są zapisy CSV programu, SQLite oraz kopie pamięci JSON. Raporty porównań CSV/PDF i inne dokumenty nie są nagraniami i nie trafiają na listę; błędy i pominięte pliki można obejrzeć osobno.

Lista pokazuje nazwę, datę początku w UTC, funkcję, jednostki, czas trwania, liczbę interwałów/próbek, źródło i stan pliku. Dla kopii Fluke data pochodzi z zegara miernika; dla CSV/SQLite z zegara komputera. Nie należy utożsamiać tych dwóch zegarów. Wpisz nazwę, funkcję, jednostkę lub fragment ścieżki w wyszukiwarkę; można też filtrować źródło. Kliknięcie nagłówka sortuje listę.

Dwuklik lub „Otwórz zaznaczony” otwiera dane i wykres. Zaznacz dwa nagrania z Ctrl i kliknij „Porównaj dwa zaznaczone”: oba pliki zostaną wczytane do istniejącego okna porównania, gdzie można wybrać pola oraz dopasowanie czasu. „Nazwij zapis…” ustawia własną nazwę wyłącznie w bibliotece. „Usuń z listy” usuwa wpis, bez kasowania pliku; ponowne skanowanie folderu może go dodać z powrotem.

Katalog jest zapamiętywany lokalnie w `$XDG_DATA_HOME/fluke289-live/library.sqlite3`, zwykle `~/.local/share/fluke289-live/library.sqlite3`. Zawiera ścieżki, nazwy, podsumowania i wskazane foldery; pliki pomiarowe pozostają na swoim miejscu. Program nie skanuje całego dysku ani folderu domowego. Nowe zakończone nagrania programu, pomyślnie zapisane kopie Fluke i otwierane sesje są dodawane do katalogu w tle. Dotychczasowe nagrania dodaj folderem.

„Odśwież bibliotekę” sprawdza wskazane foldery i znane pliki; niezmienione pliki korzystają z zapamiętanych metadanych. Brak pliku pozostaje oznaczony na liście, aby nie zgubić jego nazwy i lokalizacji. Plik nadal zapisywany może wymagać odświeżenia po końcu nagrania. Indeksowanie nie steruje miernikiem i nie zatrzymuje LIVE.


## Czas od początku i przeglądanie punktów

W oknie historii i wykresu zaznacz „Czas od początku nagrania”, aby zamiast godziny zobaczyć MM:SS, a dla dłuższych nagrań HH:MM:SS. Dymek zachowuje także rzeczywistą godzinę. Zmiana jest wyłącznie prezentacyjna i nie zmienia znaczników pomiaru, dopasowania porównań ani eksportowanych danych. Dla kopii pamięci początek pochodzi z nagłówka Fluke, dla sesji programu z pierwszego zapisanego punktu danej serii. W porównaniu wyrównanym od początku zachowany jest dotychczasowy czas względny obu serii.

Wybierz pole w liście w wierszu A/B i użyj „Poprzedni punkt” lub „Następny punkt”. Przechodzisz między rzeczywistymi poprawnymi odczytami tego pola w aktualnej serii i jednostce, bez interpolowania. Strzałki lewo/prawo działają po ustawieniu fokusu na wykresie. Na początku i końcu przechodzenie nie zapętla się; wyjście poza przybliżony fragment przesuwa widok do wybranego punktu. W podglądzie LIVE przejście do punktu wyłącza śledzenie bieżącej funkcji.

Najechanie na punkt lub przechodzenie przyciskami aktualizuje tabelę pod wykresem: pokazuje odczyty z wskazanej próbki zamiast stale ostatniego pomiaru. Dla pamięci Fluke odczyty MIN/MAX/PRIMARY mogą mieć różne czasy, dlatego wskazana próbka może zawierać tylko jedno pole.

Bargraf pod główną liczbą ma podpis fizycznej wielkości, własną wartość i zakres. Przykład: przy głównym odczycie Hz pasek może pokazywać „Napięcie AC”, ponieważ odzwierciedla osobne pole LIVE napięcia. Podpis źródła BARGRAPH/LIVE pozostaje widoczny.
