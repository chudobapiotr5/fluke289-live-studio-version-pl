# Diagnostyka i odbiór na fizycznym Fluke 289

## 1. USB i uprawnienia

Sprawdź oznaczenie kabla: IR189USB lub jawnie zgodny odpowiednik. Zapisz producenta, model i wersję adaptera. Wsuń głowicę zgodnie z jej mocowaniem, zapewnij stabilność i osłoń od silnego światła.

```bash
lsusb
ls -l /dev/serial/by-id/
id
./uruchom.sh ports
```

Jeśli USB jest widoczne, ale nie ma portu: sprawdź komunikaty jądra (na części systemów potrzebne sudo):

```bash
sudo dmesg --ctime | tail -60
```

Nie zakładamy konkretnego VID/PID ani układu USB. Zapisz VID/PID, sterownik i port z diagnostyki systemowej. Zwykły odbiornik IrDA może nie działać jako port szeregowy. Nie wgrywaj przypadkowego sterownika Windows do Ubuntu.

Przy „Permission denied” sprawdź grupę urządzenia i członkostwo w `dialout`, a następnie pełne ponowne logowanie. Przy „Device or resource busy” zamknij inne programy korzystające z miernika. Sprawdź:

```bash
fuser /dev/ttyUSB0
systemctl status ModemManager
```

Nie wyłączaj globalnie ModemManager bez sprawdzenia, czy rzeczywiście otwiera ten port i czy jest potrzebny do innych urządzeń.

## 2. Potwierdzenie rzeczywistego modelu i protokołu

Zamknij połączenie w GUI. Włącz Fluke 289 i uruchom:

```bash
./uruchom.sh diagnose /dev/ttyUSB0 --timeout 3 --database odbior.sqlite3
```

Spodziewany przebieg: TX `ID`, RX `0`, RX `FLUKE 289,<firmware>,<numer>`; następnie TX `QDDA`, RX `0` i pojedyncza długa linia danych. Diagnostyka wypisuje pełną odpowiedź i zapisuje ją w SQLite.

- Brak odpowiedzi: sprawdź port, włączenie miernika, głowicę optyczną, przewód i silne światło. Samo wykrycie USB nie potwierdza drogi optycznej.
- Inny model: aplikacja celowo odmawia połączenia.
- ACK 1/2 dla QDDA: zachowaj firmware i surowy log. Nie deklaruj rozpoznawania trybu na podstawie QM.
- ACK 5: urządzenie nie ma danych w danym stanie; wróć do zwykłego ekranu pomiarowego i spróbuj ponownie.
- Ucięte dane: sprawdź mocowanie kabla; zwiększ timeout diagnostyki i odstęp odpytywania. Dołącz surową odpowiedź do zgłoszenia.

## 3. Matryca odbioru pokrętła i menu

Zapisz: wersję Ubuntu, wersję Pythona, model kabla/VID/PID, firmware i numer miernika oraz datę. Nie dopisuj „OK” bez porównania z fizycznym ekranem.

Dla każdej pozycji wykonaj zwykły pomiar, a potem wszystkie dostępne w niej podfunkcje menu:

| Pozycja fizyczna | Co porównać | Wynik do wypełnienia |
| --- | --- | --- |
| LoZ V AC | primary, secondary, jednostka, zakres | — |
| V AC | jak wyżej; dostępne Hz/dB/filtr/crest | — |
| mV AC | jak wyżej | — |
| V DC / AC+DC | dostępne kombinacje AC/DC i pola dodatkowe | — |
| mV DC / temperatura | mV, kombinacje i temperatura | — |
| Ω / ciągłość / przewodność | funkcja, stany zwarcia i rozwarcia | — |
| Dioda / pojemność | funkcja, atrybut, przeciążenie | — |
| A / mA | funkcja i jednostka zgodnie z ekranem | — |
| µA | funkcja i jednostka zgodnie z ekranem | — |
| 50 Ω | funkcja OHMS_LOW | — |

Testy elektryczne wykonuj wyłącznie zgodnie z instrukcją Fluke i z odpowiednim źródłem/testowanym obwodem. Do sprawdzenia samego protokołu nie jest potrzebne niebezpieczne napięcie.

W każdej dostępnej konfiguracji porównaj PRIMARY i LIVE, zakres AUTO/MANUAL, sekundarny odczyt oraz tryby HOLD, AUTO_HOLD, REL, REL %, MIN/MAX/AVG, peak i RECORD, jeśli miernik je udostępnia. Zmieniaj funkcję podczas odpytywania; nie może pozostać poprzednia funkcja po kolejnej poprawnej odpowiedzi. Przy przejściu może wystąpić LIMBO/brak danych.

Pokrętło pokazujemy jako wnioskowanie. Ta procedura ma potwierdzić powiązanie funkcji z fizycznym wyborem na danym firmware; nie tworzy nieistniejącego pola położenia pokrętła w protokole.

## 4. Odporność i dane

1. Połącz miernik; bez uruchamiania zapisu sprawdź oznaczenie PODGLĄD i brak nowego pliku pomiarów. Następnie wybierz CSV lub SQLite i kliknij „Rozpocznij zapis…”; odłącz USB. Okno ma zasygnalizować błąd, usunąć aktualną wartość i zachować dotychczasowe dane.
2. Podłącz ponownie. Przy tej samej stabilnej ścieżce aplikacja ma wykonać nowe ID i wznowić pobieranie. Przerwa nie może zawierać sztucznych próbek.
3. Włącz HOLD. Porównaj PRIMARY i LIVE; zapis ma zachować flagę HOLD.
4. Sprawdź nieprawidłowy stan dostępny bezpiecznie na mierniku, np. otwarty termoelement. CSV ma mieć stan i pustą wartość, bez ogromnej liczby zastępującej pomiar.
5. Zamknij aplikację, uruchom ją ponownie i wyeksportuj bazę. Porównaj kilka dodatnich/ujemnych wartości oraz mV/µA/kΩ z ekranem i surowym logiem.
6. Kliknij „Zatrzymaj zapis”: podgląd ma pozostać aktywny, a plik przestać rosnąć. Rozpocznij nowy zapis w drugim formacie bez rozłączania. Sprawdź też rozłączanie podczas oczekiwania na odpowiedź. Zakończenie powinno nastąpić po ograniczonym czasie transakcji, a port zwolnić się do ponownego użycia.
7. Jeśli testujesz awarię procesu, rób to na osobnej bazie testowej. W trakcie pracy SQLite może używać plików `-wal` i `-shm`; do przeniesienia bazy najpierw zatrzymaj aplikację.

## 5. Pakiet informacji do zgłoszenia

Dołącz wynik `ports`, `diagnose`, firmware, oznaczenie adaptera, fizyczną pozycję pokrętła i nazwę opcji menu oraz bazę testową. Baza zawiera numer seryjny i pomiary — udostępniaj ją świadomie. Nie dołączaj danych z innych sesji.

## Rejestr walidacji dostarczonej wersji

- W środowisku budowania: Ubuntu 26.04.1, Python 3.14, pySerial i tkinter dostępne.
- W pierwotnym środowisku automatycznej implementacji nie było dostępu do fizycznego miernika. Późniejszy odbiór użytkownika na Fluke 289 V1.41 opisuje WALIDACJA.md.
- Wyniki automatyczne: patrz TESTY.txt w katalogu głównym wydania.
- GUI wymaga sesji graficznej; jeśli środowisko testowe jej nie ma, weryfikacja wizualna pozostaje do odbioru na komputerze użytkownika.
- Ubuntu 24.04 / Python 3.12 oraz pełna matryca sprzętowa: do potwierdzenia.
