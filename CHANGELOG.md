# Historia zmian

## 1.7.0 — 2026-10-25

- Biblioteka pomiarów: lokalny trwały katalog, wyszukiwanie, filtry, sortowanie, własne nazwy i porównywanie zaznaczonych nagrań. Pliki pozostają na swoim miejscu.
- Porównanie CSV/SQLite/JSON: automatyczny dobór PRIMARY, czas miernika lub wyrównanie początków, przesunięcie B i limit dopasowania.
- Podsumowanie porównania: liczba par, zgodność na wspólnej rozdzielczości, średnia/maksymalna różnica, odstępy czasowe i wskazanie najgorszej pary. Wektorowy raport PDF i CSV z wyborem ścieżki oraz ochroną źródeł.
- Czas nagrania w dniach/godzinach/minutach/sekundach, odliczanie i automatyczne zakończenie zapisu z pozostawieniem LIVE.
- Czas względny, przechodzenie między punktami i tabela reagująca na wskazany odczyt.
- Wyrównana skala bargrafu, podziałki pośrednie i podpis jego wielkości/wartości/zakresu, także przy głównym Hz.
- Pamięć Fluke: wybór miejsca kopii przed transferem, widoczne kontrolki i wskazówka powrotu do LIVE na mierniku.
- Recording: własne znaczniki czasu poszczególnych odczytów zamiast końca interwału.
- Jawne oznaczenia przerw komunikacji w nowych CSV i eksporcie SQLite; wykrywanie długich pauz w starszych CSV bez zmiany plików.
- 96 testów automatycznych oraz odbiór użytkowy wybranych pomiarów i funkcji na Fluke 289 V1.41. Zakres potwierdzenia i ograniczenia opisano w docs/WALIDACJA.md; nie jest to kalibracja miernika.

## 1.6.0 — 2026-10-25

- Eksperymentalna pamięć Fluke: lista czterech kategorii, pobieranie zapisów i interwałów, podgląd w programie oraz pełna kopia JSON.
- Komendy pamięci są tylko do odczytu; jeden właściciel portu, pauza LIVE, anulowanie, limity i diagnostyka.
- Przy wydaniu moduł oczekiwał na odbiór fizyczny (wybrane zapisy potwierdzono w 1.7.0); średnia interwału jest zachowana jako nieinterpretowany akumulator.

## 1.5.0 — 2026-10-25

- O programie: autorstwo, współpraca z OpenAI Codex, licencja GPL v3 lub nowsza.
- Identyfikator buildu z odciskiem źródeł i powiązanym raportem testów.
- Pełna dokumentacja offline w paczce i oknie aplikacji, składniki zewnętrzne oraz instrukcja rozwoju.
- Jawna paczka źródeł bez sesji pomiarowych i danych prywatnych.

## Rozwój 1.0–1.4 — 2026-10-25

Zmiany powstawały iteracyjnie w jednej sesji, bez osobnych formalnych wydań dla każdej poprawki:

- Read-only ID/QDDA przez 115200 8N1, walidacja ramek i ponowne łączenie.
- GUI na GNU/Linux i rozpoznawanie funkcji/trybów miernika.
- Oddzielny podgląd i opcjonalny zapis CSV/SQLite, eksport i diagnostyka.
- Ciemny interfejs, wskaźnik REC, historia/import i wykresy.
- Zoom/przesuwanie, czytelne osie i dymki, A/B.
- Miniwykres na ekranie głównym, AUTO/blokada myszy, regulowana tabela.
- Format odczytu zgodny z metadanymi LCD, zachowanie zer po odczycie pliku.
- Bargraf z zakresu/LIVE lub zwróconego BARGRAPH, ikona pioruna z flagi Fluke.
- Automatyczny panel Maximum/Average/Minimum z czasami miernika.
- Poprawka przycięć: renderowanie Cairo przeniesiono do tła; kolejki są ograniczone i stare klatki odrzucane.
