# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Piotr
import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from datetime import datetime,timezone
from fluke289.storage import CsvStore,Store,export_csv
from fluke289.protocol import parse_qdda
from fluke289.history import load_session
from test_app import SAMPLE

class GapTests(unittest.TestCase):
    def test_explicit_gap_survives_csv_even_short_pause(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'new.csv';store=CsvStore(p);snapshot=parse_qdda(SAMPLE).as_dict()
            with patch('fluke289.storage.utcnow',side_effect=['2026-01-01T00:00:00+00:00','2026-01-01T00:00:00.5+00:00','2026-01-01T00:00:01+00:00']):
                store.add('snapshot',snapshot);store.add('snapshot',snapshot)
                store.add('error','timeout');store.add('snapshot',snapshot)
            store.close();h=load_session(p)
            self.assertEqual([s['gap'] for s in h.samples],[True,False,True])
            self.assertEqual(h.samples[-1]['data']['readings'][0]['value'],snapshot['readings'][0]['value'])
    def test_legacy_gap_uses_sampling_cadence(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'old.csv';store=CsvStore(p);snapshot=parse_qdda(SAMPLE).as_dict()
            times=[0,.5,1,1.5,8,8.5]
            for t in times:
                with patch('fluke289.storage.utcnow',return_value=datetime.fromtimestamp(1700000000+t,timezone.utc).isoformat()):store.add('snapshot',snapshot)
            store.close()
            with p.open(encoding='utf-8-sig',newline='') as f:reader=csv.DictReader(f);rows=list(reader);header=[k for k in reader.fieldnames if k!='communication_gap']
            with p.open('w',encoding='utf-8-sig',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=header,extrasaction='ignore');writer.writeheader();writer.writerows(rows)
            h=load_session(p)
            self.assertEqual([s['gap'] for s in h.samples],[True,False,False,False,True,False])
    def test_sqlite_export_preserves_error_marker(self):
        with tempfile.TemporaryDirectory() as folder:
            db=Path(folder)/'session.sqlite3';p=Path(folder)/'export.csv';store=Store(db);snapshot=parse_qdda(SAMPLE).as_dict()
            store.add('snapshot',snapshot);store.add('error','timeout');store.add('snapshot',snapshot);store.close()
            export_csv(db,p);h=load_session(p)
            self.assertEqual([s['gap'] for s in h.samples],[True,True])
