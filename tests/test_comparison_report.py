# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Piotr
import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import test_comparison
from fluke289.comparison import choices,compare_histories,comparison_stats
from fluke289.comparison_report import export_csv,export_pdf,atomic_export,NOTICE

class ReportTests(unittest.TestCase):
    def history(self):
        a=test_comparison.ComparisonTests().source();b=test_comparison.ComparisonTests().source()
        h=compare_histories(a,b,choices(a)[0],choices(b)[0]);h.comparison_stats=comparison_stats(h)
        h.comparison_metadata={'file_a':'ąęść.csv','file_b':'=formula.json','field_a':'PRIMARY','field_b':'PRIMARY','unit':'OHM','relative':False,'shift':0,'tolerance':.5}
        return h
    def test_csv_preserves_pairs_settings_and_formula_safe_names(self):
        h=self.history()
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'report.csv';export_csv(h,p)
            with p.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
            self.assertEqual(len(rows),h.comparison_stats['count'])
            self.assertEqual(float(rows[0]['value_A_base']),336.44)
            self.assertEqual(rows[0]['file_A'],'ąęść.csv')
            self.assertTrue(rows[0]['file_B'].startswith("'="))
            self.assertEqual(rows[0]['notice'],NOTICE)
    def test_failed_export_keeps_existing_file(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'saved';p.write_text('keep')
            def broken(tmp):Path(tmp).write_text('partial');raise OSError('failure')
            with self.assertRaises(OSError):atomic_export(p,broken)
            self.assertEqual(p.read_text(),'keep');self.assertEqual(len(list(Path(folder).iterdir())),1)
    def test_pdf_real_cairo_and_no_source_changes(self):
        h=self.history();before=repr(list(h.samples))
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'report.pdf';export_pdf(h,p)
            self.assertTrue(p.read_bytes().startswith(b'%PDF-'))
            self.assertGreater(p.stat().st_size,5000)
        self.assertEqual(repr(list(h.samples)),before)

    def test_csv_settings_and_adjusted_time(self):
        h=self.history();h.comparison_metadata['shift']=5
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'report.csv';export_csv(h,p)
            with p.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
            self.assertEqual(rows[0]['shift_B_s'],'5')
            self.assertEqual(float(rows[0]['raw_meter_time_B']),100)

    def test_pdf_without_overlap_is_explicit(self):
        h=self.history();h.comparison_stats.update(count=0,overlap=None,worst=None,pairs=[])
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'report.pdf';export_pdf(h,p)
            self.assertTrue(p.read_bytes().startswith(b'%PDF-'))

    def test_export_cannot_overwrite_measurement_source(self):
        h=self.history()
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'source.csv';p.write_text('measurement')
            h.comparison_metadata['source_paths']=[str(p)]
            with self.assertRaises(ValueError):export_csv(h,p)
            self.assertEqual(p.read_text(),'measurement')
