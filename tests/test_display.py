# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Piotr
# This program comes with NO WARRANTY; see COPYING for license terms.
import csv
import tempfile
import unittest
from pathlib import Path
from fluke289.display import format_reading
from fluke289.history import load_session
from fluke289.storage import CsvStore, Store, export_csv
from fluke289.protocol import parse_qdda
from test_app import SAMPLE

class ExactDisplayTests(unittest.TestCase):
    def test_meter_decimals_prefix_and_trailing_zeros(self):
        r={'value':1.9062,'state':'NORMAL','unit':'VDC','multiplier':0,'decimals':4}
        self.assertEqual(format_reading(r),'1.9062 VDC')
        r['value']=1.9
        self.assertEqual(format_reading(r),'1.9000 VDC')
        r.update(value=2500000,unit='OHM',multiplier=6)
        self.assertEqual(format_reading(r),'2.5000 MΩ')
        r.update(value=-.000023,unit='VDC',multiplier=-3,decimals=3)
        self.assertEqual(format_reading(r),'-0.023 mVDC')
        r['state']='OL'
        self.assertEqual(format_reading(r),'OL')

    def test_identical_live_csv_sqlite_and_export_readback(self):
        snapshot=parse_qdda(SAMPLE)
        expected=[format_reading(r) for r in snapshot.readings]
        with tempfile.TemporaryDirectory() as d:
            for ext,cls in [('csv',CsvStore),('sqlite3',Store)]:
                path=Path(d)/('session.'+ext)
                store=cls(path); store.add('snapshot',snapshot.as_dict()); store.close()
                records=load_session(path).samples[-1]['data']['readings']
                self.assertEqual([format_reading(r) for r in records],expected)
            exported=Path(d)/'export.csv'
            export_csv(Path(d)/'session.sqlite3',exported)
            records=load_session(exported).samples[-1]['data']['readings']
            self.assertEqual([format_reading(r) for r in records],expected)
            with exported.open(encoding='utf-8-sig') as f:
                rows=list(csv.DictReader(f))
            self.assertEqual([r['display_text'] for r in rows],expected)
