# Walidacja i stan obsługi

## Testy automatyczne

Aktualny wynik, liczbę testów i środowisko podaje TESTY.txt oraz manifest konkretnego buildu. Testy obejmują dekoder i przykłady QDDA, tokeny funkcji/trybów, nieprawidłowe ramki, stany odczytów, port szeregowy na pseudoterminalach Linux, fragmentację, ACK, timeouty, model, reconnect, zapis/awarie dysku, CSV/SQLite, zachowanie cyfr po ponownym otwarciu, historię, zakresy, A/B, bargraf, piorun, MIN MAX, renderowanie i nawigację, czasomierz, bibliotekę, porównania i statystyki, raporty PDF/CSV oraz zachowanie przerw komunikacji.

Testy pseudoterminala i dane syntetyczne nie udają testu fizycznego miernika. GUI sprawdzane automatycznie przez modele danych i atrapy obiektów nie jest równoważne wizualnemu odbiorowi całego okna.

## Potwierdzone przez użytkownika w tej sesji rozwoju

Piotr testował aplikację na fizycznym FLUKE 289 z firmware V1.41 i portem /dev/ttyUSB0. Na dostarczonych zrzutach i w relacji użytkownika potwierdzono:

- połączenie, bieżącą rezystancję, OL, rozpoznawanie funkcji;
- REL i stany/odniesienie, ciągłość i atrybuty rozwarcia/zwarcia;
- odczyty napięcia AC około 230 V, flagę pioruna, zmiany zakresu ręcznego;
- MIN/MAX/AVG z miernika i panel z czasami;
- zapis i otwieranie sesji, miniwykres i historię, zoom oraz regulację tabeli;
- poprawne działanie po usunięciu blokującego renderowania z wątku GUI.

To odbiór użytkowy wybranych zachowań, nie pełna matryca pomiarowa. Nie publikujemy numeru seryjnego w dokumentacji wydania. Typ adaptera USB nie został fizycznie zinwentaryzowany przez autora kodu.

## Odbiór wydania 1.7.0 — 2026-10-25

Wyniki pochodzą z plików, zdjęć i relacji Piotra. Nagrania ani numer seryjny nie są publikowane w paczce. To zgodność danych i odbiór funkcji programu, nie niezależne sprawdzenie dokładności fizycznego pomiaru.

- Pamięć miernika V1.41: lista zapisów, pobranie Recording i pojedynczego Measurement, wybór miejsca kopii JSON i ponowne otwieranie. Przeglądanie pamięci na samym mierniku blokowało odczyt; powrót do LIVE go umożliwiał.
- Temperatura: na zdjęciach i w danych potwierdzono 34,2 °C o 14:28:45 i 22,4 °C o 14:30:32. Poprawiono przypisanie czasu odczytów Recording: każdy punkt używa własnego znacznika. Nie potwierdzono odtworzenia każdej wewnętrznej próbki trendu LCD.
- Hz: potwierdzono 49,969 Hz o 15:06:12, 49,976 Hz o 15:08:00 i 49,996 Hz o 15:09:16. Równoległe zapisy miały MIN/MAX 49,958–50,008 Hz; 218 z 265 najbliższych par zgodnych do 0,001 Hz, największa różnica 0,001 Hz przy odstępach do 0,262 s. To wcześniejsze dopasowanie kierunkowe, nie pomiary jednoczesne.
- VAC: potwierdzono punkty LCD 230,46 V o 15:35:04, 229,79 V o 15:37:33 i 229,73 V o 15:38:48. W kolejnym nagraniu podsumowanie dało 298 par, 232 identyczne na wspólnej rozdzielczości, średnią różnicę około 0,00221477 V, maksymalną 0,01 V i maksymalny odstęp około 0,106 s. Wskazanie najgorszej pary potwierdzono w UI.
- Rezystancja 500 Ω: zgodny odczyt 336,44 Ω. Skoki przy poruszaniu przewodem obecne w obu nagraniach; MIN Recording zachowało 335,45 Ω, minimum PRIMARY/CSV wyniosło 335,79 Ω. USB odpytywane co 0,5 s może ominąć krótkie zdarzenia.
- Potwierdzono automatyczne zakończenie zapisu i pozostawienie LIVE. Odstęp pierwszej i ostatniej próbki nie mierzy dokładności czasomierza.
- Biblioteka: indeksowanie 20 sesji CSV/SQLite/JSON, wybór dwóch plików i przejście do porównania potwierdzono zrzutami. Raport PDF użytkownika wyrenderowano i sprawdzono: czytelny wykres, polskie znaki, jedna strona i zgodne statystyki.
- Przyciski poprzedni/następny, czas względny, tabela wskazanego punktu i podpis bargrafu napięcia przy głównym Hz potwierdzone przez użytkownika.
- Zanik łącza optycznego: w starszym CSV przerwa 6,536 s, brak zer/BLANK/OL i po poprawce widoczna luka. W nowym CSV dwie jawne flagi wznowienia: odstępy 6,569 s i 16,535 s, 76 próbek PRIMARY ze stanem NORMAL i dwie luki w UI. Odstępy obejmują także wykrycie i ponowienia, nie tylko odsunięcie głowicy.
- Wcześniejszy oddzielny test odłączenia USB zawierał przejściowe NORMAL 0 V, BLANK i OL. Ich przyczyny nie ustalono. Powrót łączności był widoczny, lecz tego scenariusza nie uznajemy za w pełni zweryfikowany.

Opóźnienie łącza optycznego/USB nie zostało niezależnie zmierzone. Porównania nie kalibrują miernika; różne chwile próbkowania, zegary i agregację Recording należy uwzględniać oddzielnie.

## Niepotwierdzone lub ograniczone

- Pełna lista funkcji, podfunkcji i ich kombinacji na każdym firmware.
- Odbiór środowiska Ubuntu 24.04: jest celem kompatybilności, ale środowisko automatycznych testów ma inną wersję wskazaną w raporcie.
- Dokładność i kalibracja fizycznych pomiarów: aplikacja zachowuje dane i rozdzielczość z protokołu; nie kalibruje miernika.
- Częstotliwość wewnętrznych próbek i bargrafu LCD: odpytywanie USB nie rejestruje wszystkich szybkich zdarzeń.
- Pełna macierz kategorii pamięci i firmware: wybrane Recording/Measurement potwierdzono; średnia interwału pozostaje surowym akumulatorem (PAMIEC.md).
- Zrzuty potwierdzają wybrane widoki nowych funkcji, lecz nie wykonano pełnego automatycznego odbioru GUI na różnych rozdzielczościach. Środowisko prac nie ma dostępu do ekranu aplikacji.

Przed rozszerzeniem deklarowanej zgodności należy wykonać i udokumentować matrycę z DIAGNOSTYKA.md, podając firmware, system, Python, adapter, ustawienie i wynik. Nie dopisuj „OK” na podstawie samego tokenu w dekoderze.
