# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Piotr
# This program comes with NO WARRANTY; see COPYING for license terms.
import csv
from .display import reading_parts, format_reading
import json
import sqlite3
import os
from urllib.parse import quote
from datetime import datetime, timezone

def utcnow(): return datetime.now(timezone.utc).isoformat()

def safe_cell(value):
    # Prevent spreadsheet formula execution from untrusted meter text.
    if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@')):
        return "'"+value
    return value

class Store:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, time TEXT, kind TEXT, data TEXT)')
        self.db.commit()

    def add(self, kind, data):
        with self.db:
            self.db.execute('INSERT INTO events(time,kind,data) VALUES(?,?,?)', (utcnow(), kind, json.dumps(data, ensure_ascii=False, allow_nan=False)))

    def close(self): self.db.close()

CSV_HEADER = ['event_id', 'pc_utc', 'identity', 'primary_function', 'secondary_function', 'modes', 'range_mode', 'range_unit', 'range_number', 'range_multiplier', 'lightning', 'reading_id', 'value_base', 'unit', 'multiplier', 'decimals', 'digits', 'state', 'attribute', 'meter_time_raw', 'display_value', 'display_unit', 'display_text', 'communication_gap']


def csv_rows(eid, timestamp, identity, d, gap=False):
    for r in d['readings']:
        value = r['value'] if r['state'] == 'NORMAL' and abs(r['value']) < 9e37 else ''
        row = [eid, timestamp, identity, d['primary'], d['secondary'], '|'.join(d['modes']), d['autorange'], d['range_unit'], d['range_number'], d['range_multiplier'], d['lightning'], r['id'], value, r['unit'], r['multiplier'], r['decimals'], r['digits'], r['state'], r['attribute'], r['meter_time'], *reading_parts(r), format_reading(r), int(gap)]
        yield [safe_cell(v) for v in row]


class CsvStore:
    """Direct CSV recording: no hidden SQLite or diagnostic files."""
    def __init__(self, path):
        self.file = open(path, 'x', newline='', encoding='utf-8-sig')
        self.identity = ''
        self.number = 0
        self.gap_pending = True
        self.writer = csv.writer(self.file)
        try:
            self.writer.writerow(CSV_HEADER)
            self.file.flush()
        except Exception:
            self.file.close()
            raise

    def add(self, kind, data):
        if kind == 'identity':
            self.identity = data
            self.gap_pending = True
        elif kind == 'error':
            self.gap_pending = True
        elif kind == 'snapshot':
            self.number += 1
            self.writer.writerows(csv_rows(self.number, utcnow(), self.identity, data,self.gap_pending))
            self.gap_pending = False
            self.file.flush()

    def close(self):
        self.file.close()


def export_csv(database, destination):
    if os.path.realpath(database) == os.path.realpath(destination):
        raise ValueError('CSV nie może zastąpić bazy danych')
    db = sqlite3.connect(f'file:{quote(str(database))}?mode=ro', uri=True)
    try:
        with open(destination, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f)
            w.writerow(CSV_HEADER)
            identity = ''
            gap_pending=True
            for eid, timestamp, kind, data in db.execute('SELECT id,time,kind,data FROM events ORDER BY id'):
                d = json.loads(data)
                if kind == 'identity':
                    identity = d;gap_pending=True
                elif kind == 'error':gap_pending=True
                elif kind == 'snapshot':
                    w.writerows(csv_rows(eid, timestamp, identity, d,gap_pending));gap_pending=False
    finally: db.close()
