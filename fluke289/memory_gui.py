# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Piotr
# This program comes with NO WARRANTY; see COPYING for license terms.
import json
from datetime import datetime, timezone
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from .display import format_reading
from .memory import KINDS, to_history
from .history_gui import HistoryWindow
from .library import remember_recording

MEMORY_LIVE_HINT='Na mierniku wyjdź z przeglądania pamięci i wróć do pomiaru LIVE. Potem ponów odczyt w programie.'

BG='#10151d'; CARD='#1a2230'; TEXT='#edf2f7'; MUTED='#9aaac0'

def timestamp_text(value):
    if value is None: return '—'
    try: return datetime.fromtimestamp(value,timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError,OverflowError,OSError): return str(value)

class MemoryWindow:
    def __init__(self,parent,worker):
        self.worker=worker
        self.closed=False; self.busy=False; self.items=[]; self.archive=None; self.identity=''
        self.diagnostics=[]
        self.download_path=None
        self.window=tk.Toplevel(parent,bg=BG)
        self.window.title('Pamięć Fluke 289 • tylko odczyt')
        self.window.geometry('1150x730'); self.window.minsize(900,600)
        self.window.protocol('WM_DELETE_WINDOW',self.close)
        body=tk.Frame(self.window,bg=BG); body.pack(fill='both',expand=True,padx=20,pady=16)
        tk.Label(body,text='Pamięć Fluke 289',bg=BG,fg='#f6c744',font=('DejaVu Sans',20,'bold')).pack(anchor='w')
        tk.Label(body,text='Oryginały pozostają w mierniku. LIVE jest wstrzymany wyłącznie na czas transferu.',bg=BG,fg=MUTED).pack(anchor='w',pady=(4,12))
        tk.Label(body,text=MEMORY_LIVE_HINT,bg=BG,fg='#f6c744',wraplength=850,justify='left').pack(anchor='w',pady=(0,10))
        controls=tk.Frame(body,bg=BG); controls.pack(fill='x')
        self.list_button=ttk.Button(controls,text='Odczytaj listę zapisów',command=self.list_items)
        self.list_button.pack(side='left')
        self.download_button=ttk.Button(controls,text='Pobierz wybrany zapis',command=self.download,state='disabled')
        self.download_button.pack(side='left',padx=8)
        self.cancel_button=ttk.Button(controls,text='Anuluj transfer',command=self.worker.memory_cancel.set,state='disabled')
        self.cancel_button.pack(side='left')
        self.status=tk.StringVar(value='Kliknij „Odczytaj listę zapisów”. Zatrzymaj wcześniej zapis pliku w aplikacji.')
        tk.Label(body,textvariable=self.status,bg=BG,fg=TEXT,wraplength=1050,justify='left').pack(fill='x',pady=12)
        self.progress=ttk.Progressbar(body,mode='determinate'); self.progress.pack(fill='x',pady=(0,10))
        columns=('kind','index','name','start','end','samples')
        self.table=ttk.Treeview(body,columns=columns,show='headings',height=9)
        for col,label,width in zip(columns,['Typ','Nr','Nazwa','Start (UTC wg danych Fluke)','Koniec','Interwały'],[100,45,200,200,180,80]):
            self.table.heading(col,text=label,anchor='w'); self.table.column(col,width=width,anchor='w')
        self.table.pack(fill='both',expand=True)
        self.table.bind('<<TreeviewSelect>>',lambda e:self.update_buttons())
        self.details=tk.Text(body,height=7,bg=CARD,fg=TEXT,wrap='word',relief='flat',padx=10,pady=10)
        self.details.pack(side='bottom',fill='x',pady=10,before=self.table); self.details.configure(state='disabled')
        bottom=tk.Frame(body,bg=BG); bottom.pack(side='bottom',fill='x',before=self.details)
        self.view_button=ttk.Button(bottom,text='Otwórz pobrane dane i wykres',command=self.view,state='disabled')
        self.view_button.pack(side='left')
        self.save_button=ttk.Button(bottom,text='Zapisz pełną kopię…',command=self.save,state='disabled')
        self.save_button.pack(side='left',padx=8)
        ttk.Button(bottom,text='Zapisz diagnostykę…',command=self.save_diagnostics).pack(side='right')

    def update_buttons(self):
        self.list_button.configure(state='disabled' if self.busy else 'normal')
        self.download_button.configure(state='normal' if not self.busy and self.table.selection() else 'disabled')
        self.cancel_button.configure(state='normal' if self.busy else 'disabled')
        for button in [self.view_button,self.save_button]:
            button.configure(state='normal' if self.archive and not self.busy else 'disabled')

    def list_items(self):
        if self.busy: return
        self.busy=True; self.status.set('Odczyt listy… sprawdzanie QSLS i nagłówków zapisów')
        self.progress['value']=0; self.update_buttons()
        self.worker.memory_request('list')

    def download(self):
        selected=self.table.selection()
        if self.busy or not selected: return
        item=self.items[int(selected[0])]
        name=''.join(c if c.isalnum() or c in '-_' else '_' for c in item['name']).strip('_') or 'zapis'
        path=filedialog.asksaveasfilename(parent=self.window,title='Wybierz miejsce zapisu danych z Fluke',initialfile=f'fluke289-{name}.json',defaultextension='.json',filetypes=[('Kopia Fluke JSON','*.json')])
        if not path: return
        self.download_path=path
        self.busy=True; self.status.set('Pobieranie: '+item['name']+' • plik: '+path)
        self.progress['value']=0; self.update_buttons()
        self.worker.memory_request('download',item)

    def event(self,kind,data):
        if self.closed: return
        if kind=='memory_progress':
            done,total=data
            self.progress.configure(maximum=max(1,total),value=done)
            self.status.set(f'Odczyt: {done} / {total}')
        elif kind=='memory_error':
            self.status.set('Nie udało się pobrać: '+data['message']+'\n'+MEMORY_LIVE_HINT)
            self.diagnostics=data.get('diagnostics',[])
        elif kind=='memory_result':
            self.identity=data['identity']
            if data['operation']=='list':
                self.items=data['result']
                self.table.delete(*self.table.get_children())
                for index,item in enumerate(self.items):
                    self.table.insert('','end',iid=str(index),values=(KINDS[item['kind']][0],item['index']+1,item['name'],timestamp_text(item['start']),timestamp_text(item['end']),item.get('sample_count','—')))
                self.status.set(f'Odczytano {len(self.items)} zapisów. Wybierz zapis i kliknij „Pobierz”.' if self.items else 'Pamięć nie zawiera zapisów.')
            else:
                self.archive=data['result']; self.archive['identity']=self.identity
                self.status.set('Pobrano: '+self.archive['header']['name']+' • dane pozostają w pamięci programu do zapisania kopii')
                h=self.archive['header']
                text=f"{h['name']} • {KINDS[h['kind']][0]}\n{h['primary']} / {h['secondary']}\n"
                text+='\n'.join(r['id']+': '+format_reading(r) for r in h['readings'])
                if h['kind']=='recording': text+='\nPobrano interwały: '+str(len(self.archive['intervals']))+'; średnia interwału pozostaje surowym akumulatorem (nie interpretujemy jej bez walidacji).'
                if self.download_path:
                    path=self.download_path; self.download_path=None
                    self.write_archive(path)
                self.details.configure(state='normal'); self.details.delete('1.0','end'); self.details.insert('1.0',text); self.details.configure(state='disabled')
        elif kind=='memory_busy' and not data:
            self.busy=False; self.update_buttons()

    def view(self):
        if not self.archive: return
        history=to_history(self.archive,self.identity)
        if not history.samples:
            messagebox.showinfo('Brak próbek','Ten zapis nie zawiera odczytów z poprawną podstawą czasu.',parent=self.window)
            return
        HistoryWindow(self.window,history,title='Pamięć Fluke • '+self.archive['header']['name'],live=False)

    def save(self):
        if not self.archive: return
        path=filedialog.asksaveasfilename(parent=self.window,title='Zapisz pełną kopię pamięci',initialfile='fluke289-memory.json',defaultextension='.json',filetypes=[('Kopia Fluke JSON','*.json')])
        if path: self.write_archive(path)

    def write_archive(self,path):
        try:
            payload=json.dumps(self.archive,ensure_ascii=False,indent=2,allow_nan=False)
            with open(path,'w',encoding='utf-8') as f: f.write(payload)
        except (OSError,ValueError) as e:
            self.status.set('Nie zapisano pliku. Dane są w pamięci — użyj „Zapisz pełną kopię…”.')
            messagebox.showerror('Zapis kopii',str(e),parent=self.window)
            return False
        remember_recording(path)
        self.status.set('Zapisano pełną kopię: '+str(path))
        return True

    def save_diagnostics(self):
        path=filedialog.asksaveasfilename(parent=self.window,title='Zapisz diagnostykę pamięci',defaultextension='.json')
        if path:
            try:
                with open(path,'w',encoding='utf-8') as f: json.dump({'diagnostics':self.diagnostics},f,ensure_ascii=False,indent=2)
            except OSError as e: messagebox.showerror('Diagnostyka',str(e),parent=self.window)

    def close(self):
        if self.busy: self.worker.memory_cancel.set()
        self.closed=True; self.window.destroy()
