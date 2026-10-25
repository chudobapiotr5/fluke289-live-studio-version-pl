# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Piotr
import queue
import threading
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from pathlib import Path
from .history import load_session
from .history_gui import HistoryWindow,BG,TEXT,MUTED
from .comparison import choices,compare_histories,preferred_pair,comparison_stats

class ComparisonWindow:
    def __init__(self,parent,paths=None):
        self.window=tk.Toplevel(parent,bg=BG);self.window.title('Porównanie dwóch zapisów');self.window.geometry('1050x610');self.window.minsize(950,560)
        self.paths=[None,None]
        self.sources=[None,None];self.options=[[],[]];self.boxes=[];self.names=[];self.jobs=queue.Queue();self.closed=False
        self.window.protocol('WM_DELETE_WINDOW',self.close)
        body=tk.Frame(self.window,bg=BG,padx=18,pady=18);body.pack(fill='both',expand=True)
        tk.Label(body,text='Porównanie zapisów A i B',bg=BG,fg=TEXT,font=('DejaVu Sans',16,'bold')).pack(anchor='w')
        for index,label in enumerate(['A','B']):
            row=tk.Frame(body,bg=BG);row.pack(fill='x',pady=10)
            ttk.Button(row,text=f'Wybierz plik {label}…',command=lambda i=index:self.load(i)).pack(side='left')
            name=tk.StringVar(value='Nie wybrano pliku');self.names.append(name)
            tk.Label(row,textvariable=name,bg=BG,fg=MUTED).pack(side='left',padx=12)
            box=ttk.Combobox(body,state='readonly');box.pack(fill='x');self.boxes.append(box)
        row=tk.Frame(body,bg=BG);row.pack(fill='x',pady=12)
        self.mode=tk.StringVar(value='Czas miernika')
        ttk.Combobox(row,textvariable=self.mode,state='readonly',values=['Czas miernika','Od początku obu serii'],width=25).pack(side='left')
        tk.Label(row,text='Przesuń B o sekundy (+ później, − wcześniej):',bg=BG,fg=TEXT).pack(side='left',padx=10)
        self.shift=tk.StringVar(value='0');ttk.Entry(row,textvariable=self.shift,width=12).pack(side='left')
        limit_row=tk.Frame(body,bg=BG);limit_row.pack(fill='x',pady=(0,8))
        tk.Label(limit_row,text='Maksymalny odstęp dopasowanych odczytów [s]:',bg=BG,fg=TEXT).pack(side='left')
        self.tolerance=tk.StringVar(value='0.5')
        ttk.Entry(limit_row,textvariable=self.tolerance,width=10).pack(side='left',padx=8)
        self.feedback=tk.StringVar(value='Najpierw wybierz plik A i plik B przyciskami u góry.')
        tk.Label(body,textvariable=self.feedback,bg=BG,fg=TEXT,wraplength=880,justify='left').pack(fill='x',pady=(0,10))
        self.compare_button=ttk.Button(body,text='Porównaj na jednym wykresie',command=self.show,state='disabled')
        self.compare_button.pack(anchor='w')
        tk.Label(body,text='Wybierz tę samą jednostkę. Dopasowanie od początku wyrównuje początki, nie synchronizuje pomiarów. Pliki pozostają bez zmian.',bg=BG,fg=MUTED,wraplength=880,justify='left').pack(anchor='w',pady=10)
        self.window.after(100,self.poll)
        for index,path in enumerate((paths or [])[:2]):self.load(index,path)

    def load(self,index,path=None):
        if path is None:path=filedialog.askopenfilename(parent=self.window,title='Wybierz zapis '+ 'AB'[index],filetypes=[('Zapisy Fluke','*.csv *.json *.sqlite3'),('Wszystkie','*')])
        if not path:return
        self.names[index].set('Wczytywanie…');self.sources[index]=None;self.boxes[index].set('')
        self.options[index]=[];self.boxes[index]['values']=[]
        self.compare_button.configure(state='disabled')
        self.feedback.set('Wczytywanie pliku '+ 'AB'[index]+'…')
        def work():
            try:self.jobs.put((index,path,load_session(path),None))
            except Exception as error:self.jobs.put((index,path,None,str(error)))
        threading.Thread(target=work,daemon=True).start()

    def poll(self):
        if self.closed:return
        try:
            while True:
                index,path,history,error=self.jobs.get_nowait()
                if error:
                    self.names[index].set('Błąd odczytu');self.feedback.set('Nie udało się wczytać pliku. Wybierz go ponownie.');messagebox.showerror('Porównanie',error,parent=self.window);continue
                self.sources[index]=history;self.paths[index]=str(Path(path).resolve());self.names[index].set(Path(path).name)
                self.options[index]=choices(history)
                self.boxes[index]['values']=[f'Seria {s} · '+{'PRIMARY':'Odczyt główny (PRIMARY)','LIVE':'Odczyt bieżący (LIVE)','MAXIMUM':'Maksimum interwału (MAXIMUM)','MINIMUM':'Minimum interwału (MINIMUM)'}.get(field,field)+f' · {unit}' for s,field,unit in self.options[index]]
                if self.options[index]:
                    preferred=next((i for i,c in enumerate(self.options[index]) if c[1]=='PRIMARY'),0)
                    self.boxes[index].current(preferred)
                self.match_fields()
        except queue.Empty:pass
        self.window.after(100,self.poll)

    def match_fields(self):
        ready=all(h is not None for h in self.sources)
        self.compare_button.configure(state='normal' if ready else 'disabled')
        if not ready:
            self.feedback.set('Wybierz i wczytaj oba pliki A i B, aby dobrać odczyty.')
            return
        pair=preferred_pair(*self.options)
        if pair:
            for index,selection in enumerate(pair):self.boxes[index].current(self.options[index].index(selection))
            self.feedback.set(f'Automatycznie dobrano A: {pair[0][1]} ↔ B: {pair[1][1]} · {pair[0][2]}. Kliknij „Porównaj na jednym wykresie”.')
        else:
            self.feedback.set('Te pliki nie mają wspólnej jednostki pomiaru. Wybierz inną parę plików.')
            self.compare_button.configure(state='disabled')

    def show(self):
        try:
            if any(h is None for h in self.sources):raise ValueError('Wybierz oba pliki i poczekaj na wczytanie.')
            selections=[options[box.current()] for options,box in zip(self.options,self.boxes) if box.current()>=0]
            if len(selections)!=2:raise ValueError('Wybierz pole w obu plikach.')
            shift=float(self.shift.get().replace(',','.'));relative=self.mode.get()!='Czas miernika'
            history=compare_histories(*self.sources,*selections,shift=shift,relative=relative)
            tolerance=float(self.tolerance.get().replace(',','.'))
            history.comparison_stats=comparison_stats(history,tolerance)
            title=f'A: {self.names[0].get()} | B: {self.names[1].get()} | przesunięcie B: {shift:g} s'
            history.comparison_metadata={'source_paths':list(self.paths),'file_a':self.names[0].get(),'file_b':self.names[1].get(),'field_a':selections[0][1],'field_b':selections[1][1],'unit':selections[0][2],'shift':shift,'relative':relative,'tolerance':tolerance}
            history.comparison_description=f'A: {self.names[0].get()} · {selections[0][1]}\nB: {self.names[1].get()} · {selections[1][1]}\n'+('Czas od początku każdej serii' if relative else 'Dopasowanie według czasu odczytu Fluke')+f' · przesunięcie B: {shift:g} s'
            if selections[0][1]!=selections[1][1]:
                history.comparison_description+='\nUwaga: porównujesz różne rodzaje odczytów — np. maksimum interwału z odczytem bieżącym.'
            HistoryWindow(self.window,history,title=title,live=False)
        except (ValueError,KeyError) as error:messagebox.showerror('Porównanie',str(error),parent=self.window)

    def close(self):self.closed=True;self.window.destroy()
