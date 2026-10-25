# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Piotr
# This program comes with NO WARRANTY; see COPYING for license terms.
"""Bounded in-memory history and read-only session import."""
from collections import deque
from datetime import datetime
import csv
import json
import math
import statistics
import sqlite3
from pathlib import Path

LIMIT = 10000

class History:
    def __init__(self, limit=LIMIT):
        self.samples = deque(maxlen=limit)
        self.segment_starts = {}
        self.segment = 0
        self.previous = None
        self.disconnected = True
        self.revision = 0

    def gap(self):
        self.disconnected = True

    def add(self, data, timestamp, identity=''):
        key = (identity, data['primary'], data['secondary'], tuple(data['modes']), data.get('minmax_start', 0))
        if self.previous != key:
            self.segment += 1
            self.previous = key
        self.segment_starts[self.segment]=min(timestamp,self.segment_starts.get(self.segment,timestamp))
        self.samples.append({'segment': self.segment, 'time': timestamp, 'data': data,
                             'gap': self.disconnected, 'identity': identity})
        self.disconnected = False
        self.revision += 1

    def segments(self):
        return dict((s['segment'], s) for s in self.samples)

    def view(self, segment, unit):
        return [(s, [r for r in s['data']['readings'] if r['unit'] == unit])
                for s in self.samples if s['segment'] == segment]


def valid(r):
    return r['state'] == 'NORMAL' and math.isfinite(r['value']) and abs(r['value']) < 9e37


def load_session(path):
    result = History()
    if Path(path).suffix.lower() == '.json':
        if Path(path).stat().st_size>50*1024*1024: raise ValueError('Kopia pamięci jest większa niż 50 MiB')
        with open(path,encoding='utf-8') as f: archive=json.load(f)
        if archive.get('format')!='fluke289-memory-v1': raise ValueError('Nieznany format kopii pamięci')
        if not isinstance(archive.get('intervals'),list) or len(archive['intervals'])>100000:
            raise ValueError('Niepoprawna liczba interwałów pamięci')
        from .memory import to_history
        result=to_history(archive,archive.get('identity',''))
        if not result.samples: raise ValueError('Kopia nie zawiera odczytów do wykresu')
        return result
    if Path(path).suffix.lower() == '.csv':
        # Old CSVs have no explicit gap flag. Infer only unusually long pauses
        # relative to their own sampling cadence, without inventing values.
        intervals=[];last_key=None;last_stamp=None
        with open(path,newline='',encoding='utf-8-sig') as source:
            probe=csv.DictReader(source)
            if not {'event_id','pc_utc'}<=set(probe.fieldnames or []):raise ValueError('To nie jest CSV zapisany przez Fluke 289 Live Studio')
            legacy='communication_gap' not in (probe.fieldnames or [])
            if legacy:
                for row in probe:
                    key=(row.get('event_id'),row.get('pc_utc'))
                    if key==last_key:continue
                    stamp=datetime.fromisoformat(row['pc_utc']).timestamp();last_key=key
                    if last_stamp is not None and stamp>last_stamp:intervals.append(stamp-last_stamp)
                    last_stamp=stamp
                    if len(intervals)>=2000:break
        pause_limit=max(2.,3*statistics.median(intervals)) if intervals else math.inf
        last_sample_stamp=None
        def append_sample(data,stamp,identity,gap):
            nonlocal last_sample_stamp
            if gap or (legacy and last_sample_stamp is not None and stamp-last_sample_stamp>pause_limit):result.gap()
            result.add(data,stamp,identity);last_sample_stamp=stamp
        with open(path, newline='', encoding='utf-8-sig') as f:
            rows = csv.DictReader(f)
            required = {'event_id','pc_utc','identity','primary_function','secondary_function','modes','reading_id','value_base','unit','state','attribute','multiplier','decimals','digits','meter_time_raw'}
            if not required.issubset(rows.fieldnames or []):
                raise ValueError('To nie jest CSV zapisany przez Fluke 289 Live Studio')
            previous = None
            data = None
            for row in rows:
                key = (row['event_id'], row['pc_utc'], row['identity'])
                if key != previous:
                    if data is not None: append_sample(data, stamp, identity,gap)
                    previous = key
                    stamp = datetime.fromisoformat(row['pc_utc']).timestamp()
                    identity = row['identity']
                    gap=row.get('communication_gap','').strip().lower() in {'1','true','yes'}
                    data = {'primary': row['primary_function'].lstrip("'"), 'secondary': row['secondary_function'],
                            'modes': row['modes'].split('|') if row['modes'] else [], 'readings': []}
                value = float(row['value_base']) if row['value_base'] else 9.99999999e37
                if not math.isfinite(value): raise ValueError('Niepoprawna liczba w CSV')
                data['readings'].append({'id': row['reading_id'], 'value': value, 'unit': row['unit'],
                    'state': row['state'], 'attribute': row['attribute'], 'multiplier': int(row['multiplier']),
                    'decimals': int(row['decimals']), 'digits': int(row['digits']), 'meter_time': float(row['meter_time_raw'])})
            if data is not None: append_sample(data, stamp, identity,gap)
    else:
        # Open read-only: browsing a session never creates or edits it.
        db = sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro', uri=True)
        try:
            first = db.execute("SELECT id FROM events WHERE kind='snapshot' ORDER BY id DESC LIMIT 1 OFFSET ?", (LIMIT-1,)).fetchone()
            start = first[0] if first else 0
            ident = db.execute("SELECT data FROM events WHERE kind='identity' AND id < ? ORDER BY id DESC LIMIT 1", (start,)).fetchone()
            identity = json.loads(ident[0]) if ident else ''
            for stamp, kind, payload in db.execute('SELECT time,kind,data FROM events WHERE id>=? ORDER BY id', (start,)):
                if kind == 'identity':
                    identity = json.loads(payload)
                    result.gap()
                elif kind == 'error': result.gap()
                elif kind == 'snapshot':
                    data = json.loads(payload)
                    # Keep raw units and state; reject corrupt numeric data.
                    for r in data['readings']:
                        if not math.isfinite(r['value']): raise ValueError('Niepoprawna liczba w sesji')
                    result.add(data, datetime.fromisoformat(stamp).timestamp(), identity)
        finally: db.close()
    if not result.samples: raise ValueError('Plik nie zawiera próbek pomiarowych')
    return result
