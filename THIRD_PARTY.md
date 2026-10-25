# Składniki zewnętrzne i materiały referencyjne

Paczka źródeł zawiera kod projektu, testy i jego dokumentację. Nie zawiera bibliotek systemowych, interpretera Python, pakietu pySerial, sterowników, firmware miernika ani kopii podręczników Fluke.

| Składnik | Rola | Licencja / źródło |
| --- | --- | --- |
| Python i standardowa biblioteka | interpreter, SQLite, JSON, CSV, ctypes, wątki | licencje Python / PSF; https://docs.python.org/3/license.html |
| Tcl/Tk | okna przez tkinter | odrębne liberalne licencje Tcl/Tk; warunki dostarczone z pakietami systemowymi; https://www.tcl-lang.org/software/tcltk/license.html |
| pySerial | port szeregowy | BSD-3-Clause, Chris Liechti i współautorzy; https://github.com/pyserial/pyserial/blob/master/LICENSE.txt |
| Cairo | wygładzanie linii oraz wektorowy eksport PDF (systemowa biblioteka libcairo2) | LGPL 2.1 lub MPL 1.1, zgodnie z dystrybucją biblioteki; https://cairographics.org/ |
| SQLite | silnik plików sesji, przez Python | deklaracja public domain autora; https://www.sqlite.org/copyright.html |

Licencja GPL projektu nie zastępuje licencji tych składników. Przy tworzeniu paczki zawierającej także biblioteki lub interpreter trzeba dołączyć ich właściwe warunki i wymagane materiały źródłowe. Obecna paczka jest dystrybucją kodu projektu; zależności instaluje się oddzielnie.

Implementacja komunikacji powstała na podstawie dokumentacji protokołu Fluke. Nie kopiowano implementacji libsigrok/QtDMM. Rozszerzenie pamięci zbadano także na podstawie N0ury/dmm_util (https://github.com/N0ury/dmm_util) i wcześniejszego fvaleur/dmm_util (https://github.com/fvaleur/dmm_util); komendy i układy binarne zaimplementowano niezależnie, bez importowania ich kodu. Szczegóły i granice potwierdzenia: docs/PAMIEC.md. Testy wykorzystują krótkie przykładowe odpowiedzi ASCII ze specyfikacji, oznaczone w plikach testów. Dokumenty producenta pozostają jego materiałami; nie są objęte licencją GPL projektu.

Źródła protokołu i sprzętu:

- Fluke 289/287 Remote Interface Specification (Fluke, 2007), kopia: https://www.uniteng.com/neildocs/facilities/Fluke289_remote_spec28X.pdf
- Fluke 287/289 Users Manual: https://assets.fluke.com/manuals/287_289_umeng0100.pdf
- Fluke 287/289 Calibration Manual: https://media.fluke.com/b1d069ee-f650-436e-9a3a-b10800c1817d_original%20file.pdf
- Fluke IR189USB: https://www.fluke.com/en/product/accessories/adapters/fluke-ir189usb
- GNU GPL v3: https://www.gnu.org/licenses/gpl-3.0.html

COPYING jest niezmienionym tekstem GPL v3, Copyright (C) 2007 Free Software Foundation, Inc. Licencjonowanie tego projektu jako GPL-3.0-or-later nie oznacza, że jest częścią Projektu GNU.
