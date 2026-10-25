# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Piotr
"""Persistent, local index of measurement paths; never edits source files."""
import csv
from contextlib import contextmanager
import json
import os
import sqlite3
import threading
from datetime import datetime,timezone
from pathlib import Path

EXTENSIONS={'.csv','.json','.sqlite3'}

def inspect_recording(path):
    p=Path(path).resolve();stat=p.stat()
    units=set();functions=set();first=None;last=None;count=0
    def stamp(value):
        if isinstance(value,str):return datetime.fromisoformat(value).timestamp()
        return float(value)
    def add(t,data):
        nonlocal first,last,count
        t=stamp(t)
        if not 0<=t<=253402214400:raise ValueError('Niepoprawna data pomiaru')
        first=t if first is None else min(first,t);last=t if last is None else max(last,t)
        count+=1
        functions.add(str(data.get('primary',data.get('primary_function',''))))
        units.update(str(r['unit']) for r in data.get('readings',[]) if r.get('unit'))
    if p.suffix.lower()=='.json':
        if stat.st_size>50*1024*1024:raise ValueError('Kopia JSON przekracza 50 MiB')
        with p.open(encoding='utf-8') as f:d=json.load(f)
        if d.get('format')!='fluke289-memory-v1':raise ValueError('To nie jest kopia pomiarów Fluke')
        h=d['header'];source='Pamięć Fluke';clock='Fluke (UTC wg znacznika)'
        functions.add(h['primary']);functions.add(h.get('secondary','NONE'))
        items=d['intervals'] if h['kind']=='recording' else [{'end':h['end'],'readings':h['readings']}]
        for item in items:add(item['end'],dict(primary=h['primary'],readings=item['readings']))
        if h.get('start') is not None:first=stamp(h['start'])
        if h.get('end') is not None:last=stamp(h['end'])
    elif p.suffix.lower()=='.csv':
        source='Program CSV';clock='Komputer (UTC)'
        with p.open(encoding='utf-8-sig',newline='') as f:
            rows=csv.DictReader(f)
            if not {'event_id','pc_utc','primary_function','reading_id','unit','value_base'}<=set(rows.fieldnames or []):raise ValueError('To nie jest zapis pomiarów CSV (raporty porównań są pomijane)')
            previous=None
            for row in rows:
                functions.add(row['primary_function']);units.add(row['unit'])
                if row['event_id']!=previous:
                    add(row['pc_utc'],{});previous=row['event_id']
    elif p.suffix.lower()=='.sqlite3':
        from urllib.parse import quote
        source='Program SQLite';clock='Komputer (UTC)'
        with sqlite3.connect('file:'+quote(str(p))+'?mode=ro',uri=True) as db:
            for t,payload in db.execute("SELECT time,data FROM events WHERE kind='snapshot' ORDER BY id"):
                add(t,json.loads(payload))
    else:raise ValueError('Nieobsługiwany format')
    if not count:raise ValueError('Brak zapisanych pomiarów')
    after=p.stat()
    if (after.st_mtime_ns,after.st_size)!=(stat.st_mtime_ns,stat.st_size):raise ValueError('Plik jest zapisywany; odśwież po zakończeniu nagrania')
    if last<first:raise ValueError('Koniec zapisu jest wcześniejszy niż początek')
    return {'path':str(p),'name':p.stem,'source':source,'clock':clock,'start':first,'end':last,'duration':max(0,last-first),'count':count,'units':', '.join(sorted(units-{''})),'functions':', '.join(sorted(functions-{'','NONE'})),'size':stat.st_size,'mtime':stat.st_mtime_ns}

class Library:
    def __init__(self,directory=None):
        base=Path(directory) if directory else Path(os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local/share')))/'fluke289-live'
        base.mkdir(parents=True,exist_ok=True);self.path=base/'library.sqlite3'
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS recordings (path TEXT PRIMARY KEY, metadata TEXT NOT NULL, label TEXT NOT NULL DEFAULT "")')
            db.execute('CREATE TABLE IF NOT EXISTS folders (path TEXT PRIMARY KEY, recursive INTEGER NOT NULL)')
    @contextmanager
    def connect(self):
        db=sqlite3.connect(self.path,timeout=10)
        try:
            with db:yield db
        finally:db.close()
    def add(self,path):
        p=Path(path).resolve();stat=p.stat()
        with self.connect() as db:row=db.execute('SELECT metadata FROM recordings WHERE path=?',(str(p),)).fetchone()
        if row:
            cached=json.loads(row[0])
            if (cached['mtime'],cached['size'])==(stat.st_mtime_ns,stat.st_size):return cached
        meta=inspect_recording(path)
        with self.connect() as db:db.execute('INSERT INTO recordings(path,metadata) VALUES (?,?) ON CONFLICT(path) DO UPDATE SET metadata=excluded.metadata',(meta['path'],json.dumps(meta,ensure_ascii=False)))
        return meta
    def entries(self):
        with self.connect() as db:rows=db.execute('SELECT metadata,label FROM recordings').fetchall()
        return [dict(json.loads(data),label=label) for data,label in rows]
    def label(self,path,label):
        with self.connect() as db:db.execute('UPDATE recordings SET label=? WHERE path=?',(label.strip(),str(Path(path).resolve())))
    def remove(self,paths):
        with self.connect() as db:db.executemany('DELETE FROM recordings WHERE path=?',[(str(Path(p).resolve()),) for p in paths])
    def scan(self,folder,recursive=False):
        root=Path(folder).resolve()
        if not root.is_dir():raise ValueError('Folder nie istnieje')
        with self.connect() as db:db.execute('INSERT OR REPLACE INTO folders VALUES (?,?)',(str(root),int(recursive)))
        added=0;errors=[]
        if recursive:
            def files():
                for directory,dirs,names in os.walk(root,followlinks=False):
                    dirs[:]=[d for d in dirs if not d.startswith('.') and d not in {'__pycache__','dist','node_modules'}]
                    yield from (Path(directory)/n for n in names)
        else:
            def files():yield from root.iterdir()
        for p in files():
            if not p.is_file() or p.suffix.lower() not in EXTENSIONS or p.resolve()==self.path.resolve():continue
            try:self.add(p);added+=1
            except (OSError,ValueError,KeyError,TypeError,sqlite3.Error) as error:errors.append(p.name+': '+str(error))
        return added,errors
    def refresh(self):
        with self.connect() as db:folders=db.execute('SELECT path,recursive FROM folders').fetchall()
        added=0;errors=[];scanned=set()
        for folder,recursive in folders:
            try:
                n,issues=self.scan(folder,bool(recursive));added+=n;errors.extend(issues);scanned.add(folder)
            except (OSError,ValueError) as error:errors.append(folder+': '+str(error))
        for item in self.entries():
            if not Path(item['path']).is_file():continue
            try:self.add(item['path'])
            except (OSError,ValueError,KeyError,TypeError,sqlite3.Error) as error:errors.append(item['path']+': '+str(error))
        return added,errors

def remember_recording(path):
    """Index in the background; catalog failure never invalidates a saved file."""
    def work():
        try:Library().add(path)
        except Exception:pass
    threading.Thread(target=work,daemon=True).start()
