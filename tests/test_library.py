# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Piotr
import json
import tempfile
import unittest
from pathlib import Path
from fluke289.library import Library,inspect_recording
from fluke289.storage import CsvStore,Store
from fluke289.protocol import parse_qdda
from test_app import SAMPLE

class LibraryTests(unittest.TestCase):
    def make_csv(self,p):
        store=CsvStore(str(p));snapshot=parse_qdda(SAMPLE).as_dict()
        store.add('snapshot',snapshot);store.add('snapshot',snapshot);store.close()
    def test_index_metadata_duplicate_label_and_remove_preserve_file(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);p=root/'test.csv';self.make_csv(p);before=p.read_bytes()
            lib=Library(root/'index');lib.add(p);lib.add(p)
            rows=lib.entries();self.assertEqual(len(rows),1);self.assertEqual(rows[0]['count'],2)
            self.assertIn('Program',rows[0]['source']);self.assertTrue(rows[0]['units'])
            lib.label(p,'Zasilacz C64');lib.add(p)
            self.assertEqual(lib.entries()[0]['label'],'Zasilacz C64')
            lib.remove([p]);self.assertEqual(lib.entries(),[]);self.assertEqual(p.read_bytes(),before)
    def test_scan_skips_reports_and_recursion_is_optional(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);sub=root/'sub';sub.mkdir();self.make_csv(sub/'test.csv')
            (root/'report.csv').write_text('pair,time_A,value_A\n1,10,20\n')
            lib=Library(root/'index');n,errors=lib.scan(root,False)
            self.assertEqual(n,0);self.assertEqual(len(errors),1)
            n,errors=lib.scan(root,True);self.assertEqual(n,1);self.assertEqual(len(lib.entries()),1)
    def test_sqlite_and_missing_file_kept_in_index(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);p=root/'session.sqlite3';store=Store(str(p))
            store.add('snapshot',parse_qdda(SAMPLE).as_dict());store.close()
            lib=Library(root/'index');meta=lib.add(p)
            self.assertEqual(meta['count'],1);self.assertEqual(meta['source'],'Program SQLite')
            p.unlink();lib.refresh();self.assertEqual(len(lib.entries()),1)
    def test_memory_header_duration_and_source(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'recording.json'
            d={'format':'fluke289-memory-v1','header':{'kind':'recording','primary':'TEMPERATURE','secondary':'NONE','start':100,'end':110},'intervals':[{'end':105,'readings':[{'unit':'CEL'}]},{'end':110,'readings':[{'unit':'CEL'}]}]}
            p.write_text(json.dumps(d));meta=inspect_recording(p)
            self.assertEqual(meta['duration'],10);self.assertEqual(meta['count'],2)
            self.assertEqual(meta['units'],'CEL');self.assertEqual(meta['source'],'Pamięć Fluke')
    def test_changed_file_refresh_updates_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);p=root/'record.csv';self.make_csv(p);lib=Library(root/'index');lib.add(p)
            with p.open('a') as f:f.write('\n')
            meta=lib.add(p);self.assertEqual(meta['size'],p.stat().st_size)
