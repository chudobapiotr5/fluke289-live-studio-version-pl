# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Piotr
# This program comes with NO WARRANTY; see COPYING for license terms.
import queue
import math
import threading
import time
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from serial.tools import list_ports
from .worker import Worker
from .protocol import dial
from .storage import export_csv
from .history import History, load_session
from .history_gui import HistoryWindow
from .mini_chart import MiniChart
from .bargraph import BarGraph
from .minmax import meter_minmax
from .about import AboutWindow
from .memory_gui import MemoryWindow
from .comparison_gui import ComparisonWindow
from .library_gui import LibraryWindow
from .library import remember_recording

BG = '#10151d'
CARD = '#1a2230'
TEXT = '#edf2f7'
MUTED = '#9aaac0'
ACCENT = '#f6c744'
GREEN = '#65dbb2'
AMBER = '#ffc76d'
RED = '#ff657a'

FUNCTION_NAMES = {
    'OHMS': 'Rezystancja', 'OHMS_LOW': 'Rezystancja • 50 Ω',
    'CONTINUITY': 'Ciągłość obwodu', 'CONDUCTANCE': 'Przewodność',
    'CAPACITANCE': 'Pojemność', 'DIODE_TEST': 'Test diody',
    'TEMPERATURE': 'Temperatura', 'V_AC_LOZ': 'Napięcie AC • LoZ',
    'LIMBO': 'Zmiana funkcji',
}
for prefix, name in [('V', 'Napięcie'), ('MV', 'Napięcie • mV'),
                     ('A', 'Prąd • A'), ('MA', 'Prąd • mA'), ('UA', 'Prąd • µA')]:
    for suffix, label in [('AC', 'AC'), ('DC', 'DC'), ('AC_PLUS_DC', 'AC+DC'),
                          ('AC_OVER_DC', 'AC / DC'), ('DC_OVER_AC', 'DC / AC')]:
        FUNCTION_NAMES[prefix+'_'+suffix] = name+' '+label

SECONDARY_NAMES = {'NONE': 'Pomiar podstawowy', 'HERTZ': 'Częstotliwość',
    'DUTY_CYCLE': 'Wypełnienie', 'PULSE_WIDTH': 'Szerokość impulsu',
    'DBM': 'dBm', 'DBV': 'dBV', 'DBM_HERTZ': 'dBm / Hz', 'DBV_HERTZ': 'dBV / Hz',
    'CREST_FACTOR': 'Współczynnik szczytu', 'PEAK_MIN_MAX': 'Peak MIN / MAX'}


from .display import format_reading as pretty_reading


class App:
    def __init__(self, root):
        self.root = root
        self.worker = None
        self.library_window = None
        self.memory_window = None
        self.memory_busy = False
        self.history = History()
        self.history_window = None
        self.meter_identity = ''
        self.history_jobs = queue.Queue()
        self.last_sample = None
        self.connection_ready = False
        self.database = None
        self.recording = None
        self.record_pending = False
        self.failure = None
        self.active_interval = .5
        root.title('Fluke 289 • Live Studio')
        root.geometry('1160x900')
        root.minsize(960, 760)
        root.configure(bg=BG)
        root.option_add('*Font', ('DejaVu Sans', 10))
        root.option_add('*TCombobox*Listbox.background', CARD)
        root.option_add('*TCombobox*Listbox.foreground', TEXT)
        root.option_add('*TCombobox*Listbox.selectBackground', '#35445b')
        style = ttk.Style(root)
        style.theme_use('clam')
        style.configure('.', background=BG, foreground=TEXT, font=('DejaVu Sans', 10))
        style.configure('TFrame', background=BG)
        style.configure('TLabel', background=BG, foreground=TEXT)
        style.configure('TButton', background='#2a374a', foreground=TEXT,
                        borderwidth=0, padding=(15, 10), focusthickness=2, focuscolor=ACCENT)
        style.map('TButton', background=[('active', '#3a4d66'), ('disabled', '#222b38')],
                  foreground=[('disabled', '#68768a')])
        style.configure('Accent.TButton', background=ACCENT, foreground='#141a23', font=('DejaVu Sans', 10, 'bold'))
        style.map('Accent.TButton', background=[('active', '#ffdb70'), ('disabled', '#44453b')],
                  foreground=[('disabled', '#92917b')])
        style.configure('TEntry', fieldbackground='#111a26', foreground=TEXT, bordercolor='#35445b', padding=9)
        style.configure('TCombobox', fieldbackground='#111a26', background='#29364a',
                        foreground=TEXT, arrowcolor=TEXT, bordercolor='#35445b', padding=8)
        style.map('TCombobox', fieldbackground=[('readonly', '#111a26')], foreground=[('readonly', TEXT)])
        style.configure('Treeview', background=CARD, fieldbackground=CARD, foreground=TEXT,
                        rowheight=33, borderwidth=0, font=('DejaVu Sans', 10))
        style.configure('Treeview.Heading', background='#253144', foreground=MUTED,
                        relief='flat', padding=(10, 10), font=('DejaVu Sans', 9, 'bold'))
        style.map('Treeview', background=[('selected', '#35445b')], foreground=[('selected', TEXT)])
        style.map('Treeview.Heading', background=[('active', '#35445b')])
        style.configure('Vertical.TScrollbar', background='#35445b', troughcolor=CARD, borderwidth=0, arrowsize=12)

        self.status = tk.StringVar(value='Gotowy do połączenia')
        self.identity = tk.StringVar(value='Podłącz miernik i wybierz port USB')
        self.function = tk.StringVar(value='Oczekiwanie na miernik')
        self.mode = tk.StringVar(value='—')
        self.range = tk.StringVar(value='—')
        self.value = tk.StringVar(value='—')
        self.age = tk.StringVar(value='Brak odczytów')
        self.port = tk.StringVar()
        self.interval = tk.StringVar(value='0.5')
        self.secondary = tk.StringVar(value='Funkcja i podtryb pojawią się po połączeniu')
        self.dial_text = tk.StringVar(value='Położenie pokrętła: —')
        self.raw_info = tk.StringVar(value='Dane protokołu: —')
        self.badge = tk.StringVar(value='●  ROZŁĄCZONO')
        self.attribute = tk.StringVar(value='—')
        self.record_format = tk.StringVar(value='CSV — do arkusza')
        outer = tk.Frame(root, bg=BG)
        outer.pack(fill='both', expand=True, padx=28, pady=22)
        header = tk.Frame(outer, bg=BG)
        header.pack(fill='x', pady=(0,18))
        brand = tk.Frame(header, bg=BG)
        brand.pack(side='left')
        tk.Label(brand, text='FLUKE 289', bg=BG, fg=ACCENT, font=('DejaVu Sans', 23, 'bold')).pack(anchor='w')
        tk.Label(brand, text='LIVE STUDIO   /   Pomiary i rejestracja', bg=BG, fg=MUTED, font=('DejaVu Sans', 10)).pack(anchor='w', pady=(3,0))
        self.badge_label = tk.Label(header, textvariable=self.badge, bg='#263342', fg=MUTED,
                                    padx=16, pady=9, font=('DejaVu Sans', 10, 'bold'))
        self.badge_label.pack(side='right')
        self.rec_label = tk.Label(header, text='●  REC WYŁ.', bg='#202936', fg=MUTED,
                                  padx=14, pady=9, font=('DejaVu Sans', 10, 'bold'))
        self.rec_label.pack(side='right', padx=(0, 10))
        ttk.Button(header,text='O programie',command=lambda:AboutWindow(root)).pack(side='right',padx=10)

        controls = tk.Frame(outer, bg=CARD, padx=18, pady=14)
        controls.pack(fill='x')
        tk.Label(controls, text='PORT MIERNIKA', bg=CARD, fg=MUTED, font=('DejaVu Sans', 8, 'bold')).grid(row=0, column=0, sticky='w', pady=(0,6))
        self.ports = ttk.Combobox(controls, textvariable=self.port, width=26)
        self.ports.grid(row=1, column=0, sticky='ew')
        ttk.Button(controls, text='Odśwież', command=self.refresh).grid(row=1, column=1, padx=(8,20))
        tk.Label(controls, text='ODSTĘP / s', bg=CARD, fg=MUTED, font=('DejaVu Sans', 8, 'bold')).grid(row=0, column=2, sticky='w', pady=(0,6))
        ttk.Entry(controls, textvariable=self.interval, width=6).grid(row=1, column=2, sticky='w')
        self.start_button = ttk.Button(controls, text='Połącz', style='Accent.TButton', command=self.start)
        self.start_button.grid(row=1, column=3, padx=(24,8), sticky='e')
        self.stop_button = ttk.Button(controls, text='Rozłącz', command=self.stop, state='disabled')
        self.stop_button.grid(row=1, column=4)
        controls.columnconfigure(0, weight=1)
        controls.columnconfigure(3, weight=1)

        self.status_label = tk.Label(outer, textvariable=self.status, bg=BG, fg=MUTED, anchor='w', justify='left', wraplength=1030)
        self.status_label.pack(fill='x', pady=(12,12))
        self.content_panes = tk.PanedWindow(
            outer, orient='vertical', bg=BG, borderwidth=0,
            sashwidth=4, sashrelief='flat', sashcursor='sb_v_double_arrow',
            showhandle=False, opaqueresize=True)
        self.content_panes.pack(fill='both', expand=True)
        measurement_area = tk.Frame(self.content_panes, bg=BG)
        readings_area = tk.Frame(self.content_panes, bg=BG)
        self.content_panes.add(measurement_area, minsize=290, stretch='always')
        self.content_panes.add(readings_area, minsize=90, stretch='never')
        measurement = tk.Frame(measurement_area, bg=CARD)
        measurement.pack(fill='both', expand=True)
        measurement.rowconfigure(0,weight=1)
        measurement.columnconfigure(0,weight=1,uniform='measurement_halves')
        measurement.columnconfigure(1,weight=1,uniform='measurement_halves')
        reading_panel=tk.Frame(measurement,bg=CARD)
        reading_panel.grid(row=0,column=0,sticky='nsew',padx=(0,6))
        tk.Frame(reading_panel,bg=ACCENT,width=4).pack(side='left',fill='y')
        body = tk.Frame(reading_panel, bg=CARD, padx=24, pady=18)
        body.pack(side='left',fill='both',expand=True)
        top = tk.Frame(body, bg=CARD)
        top.pack(fill='x')
        tk.Label(top, textvariable=self.function, bg=CARD, fg=TEXT, font=('DejaVu Sans', 16, 'bold')).pack(side='left')
        self.mini_chart=MiniChart(measurement,self.history,self.open_history)
        self.mini_chart.grid(row=0,column=1,sticky='nsew',padx=(6,0),pady=4)
        tk.Label(body, textvariable=self.secondary, bg=CARD, fg=MUTED).pack(anchor='w', pady=(4,0))
        result_row=tk.Frame(body,bg=CARD)
        result_row.pack(fill='x',pady=(14,8))
        self.lightning_icon=tk.Canvas(result_row,width=48,height=66,bg=CARD,highlightthickness=0)
        self.lightning_icon.pack(side='left',padx=(0,10))
        self.lightning_shape=self.lightning_icon.create_polygon(
            28,3,6,36,22,36,13,63,43,26,27,26,
            fill=ACCENT,outline=ACCENT,state='hidden')
        self.value_label = tk.Label(result_row, textvariable=self.value, bg=CARD, fg=GREEN,
                                    font=('DejaVu Sans', 43, 'bold'), anchor='w')
        self.value_label.pack(side='left',fill='x',expand=True)
        self.lightning_note=tk.StringVar(value='Stan ostrzeżenia Fluke: brak aktualnych danych')
        tk.Label(body,textvariable=self.lightning_note,bg=CARD,fg=ACCENT,
                 font=('DejaVu Sans',9),anchor='w',wraplength=650,justify='left').pack(fill='x',pady=(0,4))
        self.bargraph=BarGraph(body)
        self.bargraph.pack(fill='x',pady=(0,8))
        self.minmax_panel=tk.Frame(body,bg=CARD)
        self.minmax_values={}
        self.minmax_times={}
        tk.Label(self.minmax_panel,text='MIN MAX • odczyty z Fluke',bg=CARD,fg=ACCENT,
                 font=('DejaVu Sans',9,'bold')).grid(row=0,column=0,columnspan=3,sticky='w',pady=(4,8))
        for row,(key,label) in enumerate([('MAXIMUM','Maximum'),('AVERAGE','Average'),('MINIMUM','Minimum')],1):
            value=tk.StringVar(value='—'); stamp=tk.StringVar(value='—')
            self.minmax_values[key]=value; self.minmax_times[key]=stamp
            tk.Label(self.minmax_panel,text=label,bg=CARD,fg=MUTED,font=('DejaVu Sans',11)).grid(row=row,column=0,sticky='w',padx=(0,14),pady=5)
            tk.Label(self.minmax_panel,textvariable=value,bg=CARD,fg=TEXT,font=('DejaVu Sans',21,'bold')).grid(row=row,column=1,sticky='w',padx=(0,14),pady=5)
            tk.Label(self.minmax_panel,textvariable=stamp,bg=CARD,fg=MUTED,font=('DejaVu Sans',10)).grid(row=row,column=2,sticky='e',pady=5)
        self.minmax_panel.columnconfigure(1,weight=1)
        tk.Label(self.minmax_panel,text='Czasy od startu MIN MAX według danych miernika',bg=CARD,fg=MUTED,
                 font=('DejaVu Sans',8)).grid(row=4,column=0,columnspan=3,sticky='w',pady=(6,8))
        self.attribute_label=tk.Label(body,textvariable=self.attribute,bg=CARD,fg=AMBER)
        self.attribute_label.pack(anchor='w')
        tk.Label(body, textvariable=self.age, bg=CARD, fg=MUTED, font=('DejaVu Sans', 9)).pack(anchor='w', pady=(6,0))

        info = tk.Frame(measurement_area, bg=BG)
        info.pack(fill='x', pady=12)
        for index, (title, variable) in enumerate([('TRYBY', self.mode), ('ZAKRES', self.range)]):
            card = tk.Frame(info, bg=CARD, padx=18, pady=10)
            card.grid(row=0, column=index, sticky='nsew', padx=(0,6) if index == 0 else (6,0))
            tk.Label(card, text=title, bg=CARD, fg=MUTED, font=('DejaVu Sans', 8, 'bold')).pack(anchor='w')
            tk.Label(card, textvariable=variable, bg=CARD, fg=TEXT, wraplength=460, justify='left').pack(anchor='w', pady=(5,0))
            info.columnconfigure(index, weight=1, uniform='cards')
        table_header = tk.Frame(readings_area, bg=BG)
        table_header.pack(fill='x', pady=(2,8))
        tk.Label(table_header, text='WSZYSTKIE ODCZYTY', bg=BG, fg=MUTED, font=('DejaVu Sans', 9, 'bold')).pack(side='left')
        tk.Label(table_header, text='↕ Złap górną krawędź tabeli i przeciągnij', bg=BG, fg=MUTED, font=('DejaVu Sans', 8)).pack(side='left', padx=14)
        ttk.Button(table_header, text='Wykres i historia', command=self.open_history).pack(side='right')
        ttk.Button(table_header,text='Pamięć Fluke…',command=self.open_memory).pack(side='right',padx=8)
        ttk.Button(table_header,text='Biblioteka pomiarów…',command=self.open_library).pack(side='right',padx=8)
        ttk.Button(table_header,text='Porównaj zapisy…',command=lambda:ComparisonWindow(self.root)).pack(side='right',padx=8)
        ttk.Button(table_header, text='Otwórz pomiary…', command=self.open_session).pack(side='right', padx=8)
        table_frame = tk.Frame(readings_area, bg=CARD)
        table_frame.pack(fill='both', expand=True)
        table_grip = tk.Frame(table_frame, bg='#71829b', height=6, cursor='sb_v_double_arrow')
        table_grip.pack(side='top', fill='x')
        table_grip.bind('<Enter>', lambda e: table_grip.configure(bg=ACCENT))
        table_grip.bind('<Leave>', lambda e: table_grip.configure(bg='#71829b'))
        table_grip.bind('<ButtonPress-1>', self.begin_table_resize)
        table_grip.bind('<B1-Motion>', self.drag_table_resize)
        table_grip.bind('<ButtonRelease-1>', self.end_table_resize)
        self.table_resize_origin = None
        columns = ('id','value','state','attribute','clock')
        self.table = ttk.Treeview(table_frame, columns=columns, show='headings', height=4)
        for c, label, width in zip(columns, ['Pole LCD', 'Wartość', 'Stan', 'Atrybut', 'Czas miernika'], [150,215,105,180,175]):
            self.table.heading(c, text=label, anchor='w')
            self.table.column(c, width=width, minwidth=70, anchor='w')
        scroll = ttk.Scrollbar(table_frame, orient='vertical', command=self.table.yview)
        self.table.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        self.table.pack(side='left', fill='both', expand=True)
        self.table.tag_configure('alternate', background='#1e2939')
        self.table.tag_configure('invalid', foreground=AMBER)

        recorder = tk.Frame(outer, bg=CARD, padx=14, pady=10)
        recorder.pack(fill='x', pady=(12,0))
        tk.Label(recorder, text='ZAPIS NA DYSK', bg=CARD, fg=MUTED, font=('DejaVu Sans', 8, 'bold')).grid(row=0, column=0, sticky='w', padx=(0,14))
        self.format_choice = ttk.Combobox(recorder, textvariable=self.record_format,
            values=['CSV — do arkusza', 'SQLite — pełna sesja'], state='readonly', width=23)
        self.format_choice.grid(row=0, column=1, sticky='w')
        self.record_start = ttk.Button(recorder, text='Rozpocznij zapis…', command=self.start_recording, state='disabled')
        self.record_start.grid(row=0, column=2, padx=8)
        self.record_stop = ttk.Button(recorder, text='Zatrzymaj zapis', command=self.stop_recording, state='disabled')
        self.record_stop.grid(row=0, column=3, sticky='e')
        recorder.columnconfigure(3, weight=1)
        self.timed_recording=tk.BooleanVar(value=False)
        self.duration_fields=[]
        timer=tk.Frame(recorder,bg=CARD); timer.grid(row=1,column=0,columnspan=4,sticky='w',pady=(8,0))
        ttk.Checkbutton(timer,text='Czas nagrania',variable=self.timed_recording).pack(side='left',padx=(0,12))
        for label,maximum,default in [('dni',9999,'0'),('godz.',23,'0'),('min',59,'5'),('sek.',59,'0')]:
            var=tk.StringVar(value=default); self.duration_fields.append(var)
            ttk.Spinbox(timer,from_=0,to=maximum,width=5,textvariable=var).pack(side='left')
            tk.Label(timer,text=label,bg=CARD,fg=MUTED).pack(side='left',padx=(3,10))
        self.timer_text=tk.StringVar(value='Bez limitu czasu')
        tk.Label(timer,textvariable=self.timer_text,bg=CARD,fg=GREEN).pack(side='left',padx=12)
        footer = tk.Frame(outer, bg=BG)
        footer.pack(fill='x', pady=(8,0))
        ttk.Button(footer, text='Starsza baza → CSV…', command=self.export).pack(side='right')
        self.log_label = tk.Label(footer, text='Tylko podgląd • pomiary nie są zapisywane na dysk', bg=BG, fg=MUTED, anchor='w', wraplength=650, justify='left', font=('DejaVu Sans', 9))
        self.log_label.pack(side='left', fill='x', expand=True)
        details = tk.Frame(outer, bg=BG)
        details.pack(fill='x', pady=(10,0))
        tk.Label(details, textvariable=self.identity, bg=BG, fg=MUTED, font=('DejaVu Sans', 8)).pack(anchor='w')
        tk.Label(details, textvariable=self.dial_text, bg=BG, fg=MUTED, font=('DejaVu Sans', 8)).pack(anchor='w')
        tk.Label(details, textvariable=self.raw_info, bg=BG, fg=MUTED, font=('DejaVu Sans', 8)).pack(anchor='w')
        self.refresh()
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.after(100, self.tick)

    def begin_table_resize(self, event):
        _, sash_y = self.content_panes.sash_coord(0)
        self.table_resize_origin = (event.y_root, sash_y)
        return 'break'

    def drag_table_resize(self, event):
        if self.table_resize_origin is not None:
            pointer_y, sash_y = self.table_resize_origin
            new_y = sash_y + event.y_root - pointer_y
            # PanedWindow enforces the minimum heights of both panels.
            self.content_panes.sash_place(0, 0, int(new_y))
        return 'break'

    def end_table_resize(self, event):
        self.drag_table_resize(event)
        self.table_resize_origin = None
        return 'break'

    def open_memory(self):
        if not self.worker or not self.worker.is_alive():
            messagebox.showinfo('Pamięć Fluke','Najpierw połącz miernik.',parent=self.root)
            return
        if self.recording or self.record_pending:
            messagebox.showinfo('Pamięć Fluke','Najpierw zatrzymaj zapis na dysk. Połączenie z miernikiem pozostaw aktywne.',parent=self.root)
            return
        if self.memory_window and not self.memory_window.closed:
            self.memory_window.window.lift()
            return
        if self.memory_busy:
            messagebox.showinfo('Pamięć Fluke','Poczekaj na zakończenie anulowania transferu.',parent=self.root)
            return
        self.memory_window=MemoryWindow(self.root,self.worker)

    def open_library(self):
        if self.library_window and not self.library_window.closed:
            self.library_window.reload();self.library_window.window.lift();return
        try:self.library_window=LibraryWindow(self.root)
        except Exception as error:messagebox.showerror('Biblioteka pomiarów',str(error),parent=self.root)

    def open_history(self):
        if self.history_window and not self.history_window.closed:
            self.history_window.window.lift()
            return
        self.history_window = HistoryWindow(self.root, self.history)

    def open_session(self):
        path = filedialog.askopenfilename(parent=self.root, title='Otwórz pomiary w programie',
            filetypes=[('Sesje Fluke (SQLite / CSV / pamięć JSON)', '*.sqlite3 *.csv *.json'), ('Wszystkie', '*')])
        if not path: return
        self.status.set('Wczytywanie zapisanej sesji… podgląd miernika nadal działa')
        def load():
            try: self.history_jobs.put((path, load_session(path), None))
            except Exception as e: self.history_jobs.put((path, None, str(e)))
        threading.Thread(target=load, daemon=True).start()

    def set_badge(self, text, color=MUTED):
        self.badge.set('●  '+text)
        self.badge_label.config(fg=color)
        self.connection_ready = text.startswith('POŁĄCZONO')
        if not self.connection_ready:
            self.bargraph.disconnect()
            self.update_lightning(None)
            for value in self.minmax_values.values(): value.set('—')
            for stamp in self.minmax_times.values(): stamp.set('brak aktualnych danych')
        self.mini_chart.update_data(self.connection_ready)
        self.update_rec_indicator()

    def update_minmax(self, snapshot):
        rows=meter_minmax(snapshot)
        if rows is None:
            self.minmax_panel.pack_forget()
            self.bargraph.pack(fill='x',pady=(0,8),before=self.attribute_label)
            return
        self.bargraph.pack_forget()
        self.minmax_panel.pack(fill='x',pady=(0,8),before=self.attribute_label)
        for key,label,value,stamp in rows:
            self.minmax_values[key].set(value)
            self.minmax_times[key].set(stamp)

    def update_lightning(self, state):
        if state == 'ON':
            self.lightning_icon.itemconfigure(self.lightning_shape,state='normal')
            self.lightning_note.set('Fluke zgłasza potencjalnie niebezpieczne napięcie')
        elif state == 'OFF':
            self.lightning_icon.itemconfigure(self.lightning_shape,state='hidden')
            self.lightning_note.set('')
        else:
            self.lightning_icon.itemconfigure(self.lightning_shape,state='hidden')
            self.lightning_note.set('Stan ostrzeżenia Fluke: brak aktualnych danych' if state is None
                                    else 'Stan ostrzeżenia Fluke: nieznany ('+str(state)+')')

    def update_rec_indicator(self):
        if not self.recording:
            self.rec_label.config(text='●  REC WYŁ.', fg=MUTED, bg='#202936')
        elif self.connection_ready:
            self.rec_label.config(text='●  REC', fg=RED, bg='#39212b')
        else:
            self.rec_label.config(text='●  REC · PRZERWA', fg=AMBER, bg='#352c24')

    def refresh(self):
        self.ports['values'] = [p.device for p in list_ports.comports()]
        if not self.port.get() and self.ports['values']: self.port.set(self.ports['values'][0])

    def start(self):
        try:
            interval = float(self.interval.get())
            if not 0.2 <= interval <= 3600: raise ValueError()
            if not self.port.get().strip(): raise ValueError()
        except ValueError:
            messagebox.showerror('Ustawienia', 'Wybierz port i odstęp od 0.2 do 3600 sekund.')
            return
        self.recording = None
        self.record_pending = False
        self.log_label.config(text='Tylko podgląd • pomiary nie są zapisywane na dysk', fg=MUTED)
        self.failure = None
        self.active_interval = interval
        self.last_sample = None
        self.value.set('—')
        self.table.delete(*self.table.get_children())
        self.worker = Worker(self.port.get().strip(), interval=interval)
        self.worker.start()
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.record_start.config(state='normal')

    def start_recording(self):
        if not self.worker or not self.worker.is_alive() or self.recording or self.record_pending:
            return
        duration=None
        if self.timed_recording.get():
            try:
                values=[int(v.get()) for v in self.duration_fields]
                if any(v<0 or v>limit for v,limit in zip(values,[9999,23,59,59])): raise ValueError()
                duration=sum(v*factor for v,factor in zip(values,[86400,3600,60,1]))
                if duration<=0: raise ValueError()
            except ValueError:
                messagebox.showerror('Czas nagrania','Podaj dodatni czas: dni 0–9999, godziny 0–23, minuty i sekundy 0–59.',parent=self.root)
                return
        format = 'CSV' if self.record_format.get().startswith('CSV') else 'SQLite'
        extension = '.csv' if format == 'CSV' else '.sqlite3'
        path = filedialog.asksaveasfilename(
            parent=self.root, title='Rozpocznij zapis — '+format,
            initialfile='pomiary_'+datetime.now().strftime('%Y-%m-%d_%H-%M-%S')+extension,
            defaultextension=extension, filetypes=[(format, '*'+extension)])
        if not path:
            return
        if Path(path).suffix.lower() != extension:
            messagebox.showerror('Format pliku', 'Dla formatu '+format+' użyj rozszerzenia '+extension, parent=self.root)
            return
        if Path(path).exists():
            if format == 'CSV':
                messagebox.showerror('Plik już istnieje', 'Wybierz nową nazwę CSV, aby zachować wcześniejsze pomiary.', parent=self.root)
                return
            if not messagebox.askyesno('Istniejąca sesja', 'Dopisać nowe pomiary do tej bazy SQLite?', parent=self.root):
                return
        if not self.worker.is_alive() or self.worker.stop_event.is_set():
            return
        self.record_pending = True
        self.record_start.config(state='disabled')
        self.format_choice.config(state='disabled')
        self.log_label.config(text='Otwieranie pliku…', fg=AMBER)
        self.worker.start_recording(path, format, duration)

    def stop_recording(self):
        if self.worker and not self.record_pending:
            self.record_pending = True
            self.record_stop.config(state='disabled')
            self.log_label.config(text='Kończenie zapisu…', fg=AMBER)
            self.worker.stop_recording()

    def recording_changed(self, data):
        if self.recording and not data:remember_recording(self.recording['path'])
        self.record_pending = False
        self.recording = data
        self.update_rec_indicator()
        alive = bool(self.worker and self.worker.is_alive() and not self.worker.stop_event.is_set())
        self.record_start.config(state='normal' if alive and not data else 'disabled')
        self.record_stop.config(state='normal' if alive and data else 'disabled')
        self.format_choice.config(state='disabled' if data else 'readonly')
        if data:
            if data['format'] == 'SQLite': self.database = data['path']
            self.log_label.config(text='● Zapis '+data['format']+' • '+Path(data['path']).name, fg=GREEN)
        else:
            self.log_label.config(text='Tylko podgląd • zapis wyłączony', fg=MUTED)

    def stop(self):
        if self.worker:
            self.worker.stop_event.set()
            self.stop_button.config(state='disabled')
            self.record_start.config(state='disabled')
            self.record_stop.config(state='disabled')
            self.status.set('Zatrzymywanie…')
            self.set_badge('ZATRZYMYWANIE', AMBER)

    def tick(self):
        deadline=self.recording.get('deadline') if self.recording else None
        if deadline is not None:
            remaining=max(0,math.ceil(deadline-time.monotonic()))
            days,rest=divmod(remaining,86400); hours,rest=divmod(rest,3600); minutes,seconds=divmod(rest,60)
            self.timer_text.set(f'Pozostało: {days} dni {hours:02}:{minutes:02}:{seconds:02}')
        else:
            self.timer_text.set('Zapis bez limitu czasu' if self.recording else 'Zapis wyłączony')
        try:
            path, history, error = self.history_jobs.get_nowait()
            if error:
                messagebox.showerror('Nie udało się otworzyć pomiarów', error, parent=self.root)
            else:
                remember_recording(path)
                HistoryWindow(self.root, history, title='Zapisana sesja • '+Path(path).name, live=False)
        except queue.Empty: pass
        if self.worker:
            for _ in range(100):
                try: kind, data = self.worker.events.get_nowait()
                except queue.Empty: break
                if kind.startswith('memory_'):
                    if kind=='memory_busy':
                        self.memory_busy=data
                        self.record_start.configure(state='disabled' if data else ('normal' if self.worker.is_alive() and not self.worker.stop_event.is_set() else 'disabled'))
                        if data:
                            self.history.gap()
                            self.last_sample=None
                            self.status.set('Odczyt pamięci • LIVE chwilowo wstrzymany')
                            self.value.set('—')
                            self.set_badge('ODCZYT PAMIĘCI', AMBER)
                    if self.memory_window and not self.memory_window.closed:
                        self.memory_window.event(kind,data)
                elif kind == 'snapshot': self.show(data)
                elif kind == 'identity':
                    self.identity.set(data)
                    self.meter_identity = data
                    self.history.gap()
                elif kind == 'recording_finished':
                    self.log_label.config(text=data,fg=GREEN)
                elif kind == 'recording': self.recording_changed(data)
                elif kind == 'recording_error':
                    self.recording_changed(None)
                    self.log_label.config(text=data, fg=AMBER)
                    messagebox.showerror('Błąd zapisu', data, parent=self.root)
                elif kind in {'error','fatal','status'}:
                    self.history.gap()
                    self.status.set(data)
                    self.set_badge('ŁĄCZENIE' if kind == 'status' else 'BRAK DANYCH', AMBER)
                    if kind == 'fatal': self.failure = data
                    self.value.set('—')
                    self.table.delete(*self.table.get_children())
                elif kind == 'stopped':
                    self.history.gap()
                    self.status.set(self.failure or 'Rozłączono')
                    self.set_badge('BŁĄD' if self.failure else 'ROZŁĄCZONO', AMBER if self.failure else MUTED)
                    self.value.set('—')
                    self.start_button.config(state='normal')
                    self.stop_button.config(state='disabled')
                    self.record_start.config(state='disabled')
                    self.record_stop.config(state='disabled')
            if self.last_sample is not None and self.worker.is_alive() and not self.worker.stop_event.is_set():
                seconds = time.monotonic()-self.last_sample
                self.age.set(f'Ostatnia odpowiedź: {seconds:.1f} s temu')
                if seconds > max(3, self.active_interval*2):
                    self.value.set('—')
                    self.set_badge('DANE NIEAKTUALNE', AMBER)
        self.root.after(100, self.tick)

    def show(self, s):
        self.history.add(s.as_dict(), time.time(), self.meter_identity)
        self.bargraph.update_snapshot(s)
        self.update_minmax(s)
        self.last_sample = time.monotonic()
        self.function.set(FUNCTION_NAMES.get(s.primary, s.primary))
        self.secondary.set(('MIN MAX • '+SECONDARY_NAMES.get(s.secondary,s.secondary)) if meter_minmax(s) is not None else SECONDARY_NAMES.get(s.secondary,s.secondary))
        self.dial_text.set('Pokrętło: '+dial(s.primary))
        self.raw_info.set(f'Protokół: {s.primary} / {s.secondary} • symbol napięcia: {s.lightning}')
        self.mode.set(' · '.join(s.modes) if s.modes else 'Pomiar bieżący')
        prefix = {-9:'n', -6:'µ', -3:'m', 0:'', 3:'k', 6:'M'}.get(s.range_multiplier)
        unit = {'OHM':'Ω', 'SIE':'S', 'CEL':'°C', 'FAR':'°F'}.get(s.range_unit, s.range_unit)
        range_text = f'{s.range_number} {prefix}{unit}' if prefix is not None else f'{s.range_number} × 10^{s.range_multiplier} {unit}'
        self.range.set(('Automatyczny' if s.autorange == 'AUTO' else s.autorange)+' · '+range_text)
        primary = next((r for r in s.readings if r.id == 'PRIMARY'), None)
        text = pretty_reading(primary) if primary else 'Brak pola PRIMARY'
        self.value.set(text)
        self.value_label.config(fg=GREEN if primary and primary.valid else AMBER,
                                font=('DejaVu Sans', 43 if len(text) < 24 else 28, 'bold'))
        self.attribute.set(('Atrybut: '+primary.attribute if primary.attribute != 'NONE' else 'Stan: '+primary.state) if primary else 'Brak odczytu głównego')
        self.status.set(('Odczyt aktywny • zapis '+self.recording['format'] if self.recording else 'Odczyt aktywny • tylko podgląd, bez zapisu na dysk') + (' • '+'; '.join(s.warnings) if s.warnings else ''))
        self.set_badge('POŁĄCZONO / ZAPIS' if self.recording else 'POŁĄCZONO / PODGLĄD', GREEN)
        self.update_lightning(s.lightning)
        self.table.delete(*self.table.get_children())
        for i, r in enumerate(s.readings):
            tags = (['alternate'] if i % 2 else []) + ([] if r.valid else ['invalid'])
            self.table.insert('', 'end', values=(r.id, pretty_reading(r), r.state, r.attribute, r.meter_time), tags=tags)

    def export(self):
        src = self.database
        if not src:
            src = filedialog.askopenfilename(
                parent=self.root,
                title='Wybierz wcześniejszą sesję pomiarową (.sqlite3)',
                filetypes=[('Sesja pomiarowa', '*.sqlite3'), ('Wszystkie', '*')])
        if not src:
            return
        source = Path(src)
        dst = filedialog.asksaveasfilename(
            parent=self.root,
            title='Zapisz pomiary jako CSV',
            initialdir=str(source.parent),
            initialfile=source.stem+'.csv',
            defaultextension='.csv',
            filetypes=[('Tabela CSV', '*.csv')])
        if not dst:
            return
        try:
            if self.recording and Path(dst).resolve() == Path(self.recording['path']).resolve():
                raise ValueError('Wybierz inną nazwę: ten plik jest obecnie zapisywany.')
            export_csv(src, dst)
            messagebox.showinfo('Eksport zakończony', 'Zapisano pomiary do pliku:\n'+dst, parent=self.root)
        except Exception as e:
            messagebox.showerror('Nie udało się zapisać CSV', str(e), parent=self.root)

    def close(self):
        if self.worker and self.worker.is_alive():
            self.stop()
            self.root.after(100, self.finish_close)
        else: self.root.destroy()

    def finish_close(self):
        if self.worker.is_alive(): self.root.after(100, self.finish_close)
        else: self.root.destroy()

def main():
    root = tk.Tk()
    App(root)
    root.mainloop()
