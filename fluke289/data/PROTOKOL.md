# Protokół i granice obsługi

## Transport

Fluke 289 przez zgodny adapter optyczno-szeregowy: 115200 bit/s, 8 danych, brak parzystości, 1 bit stopu, brak kontroli przepływu. To interfejs szeregowy IR, nie połączenie sieciowe IrDA. Jedyny właściciel portu to wątek Worker. Linux otwiera port z blokadą exclusive.

Aplikacja używa wyłącznie ID i QDDA. Transport ma również dozwolone QM do odczytu, lecz nie zastępuje nim QDDA w GUI. Nie wysyła RI/DS/RMP ani innych poleceń zmieniających ustawienia. Polecenie ma zakończenie CR; odpowiedź to ACK zakończone CR i osobna linia danych. Obsługiwane są ACK 0, 1, 2, 5 i jawnie zgłaszane nieznane odpowiedzi. Tolerowane jest CRLF, fragmentacja i puste zakończenia. Transakcja ma limit czasu i długości linii 32768 bajtów.

## Identyfikacja i QDDA

ID musi zwrócić dokładnie model FLUKE 289 oraz pola firmware i numeru seryjnego. Nie deklarujemy obsługi Fluke 287 mimo częściowo wspólnego protokołu.

Dekoder QDDA zachowuje funkcję główną, podfunkcję, auto/manual, jednostkę i zakres, mnożnik, stan pioruna, początek MIN MAX, zmienną liczbę flag trybu i listę odczytów. Każdy odczyt obejmuje ID, wartość bazową, jednostkę, mnożnik wyświetlania, miejsca dziesiętne, liczbę cyfr, stan, atrybut i czas miernika. Liczba pól jest sprawdzana; maksymalnie przyjmujemy 64 tryby i 64 odczyty.

Nieznane nazwy funkcji/podfunkcji/trybu są zachowane. Użytkownik otrzymuje ostrzeżenie; aplikacja nie zgaduje ich znaczenia. Nieprawidłowe liczby, NaN, nieskończoność i niezgodna struktura powodują błąd, a nie próbkę.

## Format i znaczenie odczytów

Wartość jest przekazywana w jednostce bazowej. Format odtwarza się z mnożnika i liczby miejsc dziesiętnych — nie z dowolnego automatycznego prefiksu. Przykład: 0.005029 VAC, mnożnik -3, trzy miejsca po przecinku → 5.029 mVAC. Obliczenia formatu używają Decimal utworzonego z tekstowej reprezentacji liczby; końcowe zera są zachowane. Obraz LCD nie jest przesyłany; znaki jednostek są renderowane tekstowo.

PRIMARY to wynik główny (w tym zatrzymany lub względny). LIVE jest osobnym odczytem bieżącym. MINIMUM/MAXIMUM/AVERAGE pochodzą z miernika i nie są wyliczane z próbek USB. Nieprawidłowy stan lub wartość zastępcza rzędu 9.99999999e37 nie jest rysowana jako zwykła liczba.

Nie ma osobnego pola mechanicznego położenia pokrętła. Etykieta pokrętła jest wnioskowaniem z aktywnej funkcji i jest tak podpisana; LIMBO/nieznana funkcja daje brak ustalenia. Nie rozpoznajemy OFF z samego milczenia portu.

## Bargraf, czas i piorun

Opis QDDA nie gwarantuje bargrafu, mimo wymienienia BARGRAPH wśród możliwych ID. Dlatego obsługujemy zgodny BARGRAPH, jeśli nadejdzie; w przeciwnym razie wizualizujemy LIVE na skali rangeData i podpisujemy źródło. Bez zgodnej jednostki albo znanej liniowej skali nie zgadujemy.

Czas komputera UTC oznacza odbiór/zapis próbki. Znacznik czasu miernika to odrębna liczba z jego zegara. Nie zakładamy synchronizacji zegarów. MIN MAX pokazuje różnice pomiędzy czasem odczytu pola i minMaxStartTime, bez przeliczania na zegar systemu. Nieprawidłowa lub nieobecna podstawa czasu daje „—”.

Ikona pioruna jest sterowana polem ON/OFF miernika, nie lokalnym progiem. Nieaktualne dane są sygnalizowane jako nieznany bieżący stan. Interfejs USB i program nie zastępują wskazań bezpieczeństwa na samym mierniku.

## Błędy i ograniczenia

Po błędzie komunikacji port jest zamykany; próby ponownego połączenia mają rosnącą przerwę do 30 s i ponownie sprawdzają ID. Błędy zapisu wyłączają zapis, pozostawiając podgląd. Dane nie są interpolowane przez przerwy i nie ma sztucznych próbek. Pomiar co 0.5 s nie oznacza rejestracji wszystkich wewnętrznych zmian miernika; prawdziwa częstotliwość zależy także od czasu odpowiedzi.

Nie obsługujemy zdalnego sterowania funkcją, menu, resetów ani obrazu TrendCapture. Eksperymentalny moduł odczytu archiwum z pamięci miernika opisuje PAMIEC.md. Testy i obserwacje nie stanowią kalibracji, certyfikacji pomiarowej ani potwierdzenia wszystkich kombinacji funkcji i firmware. Źródła pierwotne są podane w THIRD_PARTY.md.
