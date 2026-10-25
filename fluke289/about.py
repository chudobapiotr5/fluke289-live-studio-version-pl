# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Piotr
# This program comes with NO WARRANTY; see COPYING for license terms.
"""Offline release information, documentation and licensing."""
import json
import platform
import sys
import tkinter as tk
from tkinter import ttk
from importlib import metadata, resources
from . import __version__

AUTHOR_CREDIT = 'Software Development, Design & Testing by Piotr'
COOPERATION = 'Powstało we współpracy z OpenAI Codex'
LICENSE_ID = 'GPL-3.0-or-later'


def read_document(name):
    return resources.files('fluke289').joinpath('data', name).read_text(encoding='utf-8')


def build_information():
    try:
        return json.loads(read_document('build_info.json'))
    except (FileNotFoundError, ValueError):
        return {'version': __version__, 'build_id': 'development — brak manifestu',
                'date': 'nieustalona', 'tests': {'status': 'nie uruchomiono w tym buildzie'}}


def info_text():
    build = build_information()
    tests = build.get('tests', {})
    try: serial_version = metadata.version('pyserial')
    except metadata.PackageNotFoundError: serial_version = 'brak'
    return '\n'.join([
        'Fluke 289 Live Studio',
        f'Wersja: {__version__}',
        f'Build: {build["build_id"]}',
        f'Data wydania: {build["date"]}',
        f'Odcisk źródeł SHA-256: {build.get("source_sha256", "brak")}',
        '', AUTHOR_CREDIT, COOPERATION,
        'Copyright (C) 2026 Piotr',
        'Licencja: GNU GPL v3 lub dowolna późniejsza ('+LICENSE_ID+')',
        'Wolno używać, analizować, modyfikować i rozpowszechniać zgodnie z GPL.',
        'Program udostępniany BEZ GWARANCJI; pełne warunki w zakładce Licencja.',
        '',
        f'Testy buildu: {tests.get("count", "—")} • {tests.get("status", "brak danych")}',
        'Środowisko testów: '+build.get('test_environment', 'nieustalone'),
        'Odbiór sprzętowy: wybrane funkcje potwierdził Piotr na Fluke 289 V1.41.',
        'Szczegółowy zakres i ograniczenia: zakładka Walidacja.',
        '',
        'Bieżące środowisko uruchomienia:',
        'Python '+sys.version.split()[0]+' • '+platform.system()+' '+platform.release(),
        'Tcl/Tk '+str(tk.TclVersion)+' / '+str(tk.TkVersion)+' • pySerial '+serial_version,
        '',
        'Niezależny projekt. Nie jest oficjalnym produktem Fluke ani częścią Projektu GNU.',
        'Brak publicznego adresu repozytorium i kontaktu w tym wydaniu.',
        'Nie używaj programu jako potwierdzenia braku niebezpiecznego napięcia.',
    ])


class AboutWindow:
    def __init__(self, parent):
        self.window = tk.Toplevel(parent, bg='#10151d')
        self.window.title('O programie • Fluke 289 Live Studio')
        self.window.geometry('1040x760')
        self.window.minsize(800, 560)
        style = ttk.Style(self.window)
        style.configure('About.TNotebook', background='#10151d', borderwidth=0)
        style.configure('About.TNotebook.Tab', padding=(10, 8), background='#253144', foreground='#edf2f7')
        style.map('About.TNotebook.Tab', background=[('selected', '#f6c744')], foreground=[('selected', '#10151d')])
        heading = tk.Frame(self.window, bg='#10151d')
        heading.pack(fill='x', padx=20, pady=16)
        tk.Label(heading, text='Fluke 289 Live Studio', bg='#10151d', fg='#f6c744',
                 font=('DejaVu Sans', 20, 'bold')).pack(anchor='w')
        tk.Label(heading, text=AUTHOR_CREDIT+'  •  '+COOPERATION, bg='#10151d', fg='#9aaac0',
                 wraplength=980, justify='left').pack(anchor='w', pady=(6, 0))
        book = ttk.Notebook(self.window, style='About.TNotebook')
        book.pack(fill='both', expand=True, padx=20)
        documents = [
            ('Informacje', None), ('Instrukcja', 'UZYTKOWNIK.md'),
            ('Dokumentacja', 'PROTOKOL.md'), ('Testy', 'TESTY.txt'), ('Licencja GNU GPL', 'COPYING')]
        for title, filename in documents:
            pane = tk.Frame(book, bg='#1a2230')
            book.add(pane, text=title)
            choice = None
            if title == 'Dokumentacja':
                names = {
                    'Pamięć Fluke (eksperymentalna)': 'PAMIEC.md', 'Protokół i ograniczenia': 'PROTOKOL.md', 'Formaty plików': 'FORMATY.md',
                    'Diagnostyka': 'DIAGNOSTYKA.md', 'Walidacja i odbiór': 'WALIDACJA.md',
                    'Rozwój i build': 'ROZWOJ.md', 'Autorstwo': 'AUTHORS.md',
                    'Historia zmian': 'CHANGELOG.md', 'Składniki i źródła': 'THIRD_PARTY.md'}
                choice = ttk.Combobox(pane, values=list(names), state='readonly')
                choice.current(0)
                choice.pack(fill='x', padx=16, pady=10)
            content_pane = tk.Frame(pane, bg='#1a2230')
            content_pane.pack(fill='both', expand=True)
            scroll = ttk.Scrollbar(content_pane, orient='vertical')
            scroll.pack(side='right', fill='y')
            text = tk.Text(content_pane, bg='#1a2230', fg='#edf2f7', insertbackground='#edf2f7',
                           relief='flat', wrap='word', padx=18, pady=16,
                           font=('DejaVu Sans', 10), yscrollcommand=scroll.set)
            text.pack(fill='both', expand=True)
            scroll.configure(command=text.yview)
            def set_content(filename, widget=text):
                try: content = info_text() if filename is None else read_document(filename)
                except FileNotFoundError: content = 'Brak dokumentu w tej paczce: '+filename
                widget.configure(state='normal')
                widget.delete('1.0', 'end')
                widget.insert('1.0', content)
                widget.configure(state='disabled')
                widget.yview_moveto(0)
            set_content(filename)
            if choice:
                choice.bind('<<ComboboxSelected>>', lambda event, picker=choice, mapping=names, show=set_content: show(mapping[picker.get()]))
        buttons = tk.Frame(self.window, bg='#10151d')
        buttons.pack(fill='x', padx=20, pady=14)
        ttk.Button(buttons, text='Kopiuj informacje', command=self.copy_info).pack(side='left')
        ttk.Button(buttons, text='Zamknij', command=self.window.destroy).pack(side='right')

    def copy_info(self):
        self.window.clipboard_clear()
        self.window.clipboard_append(info_text())
