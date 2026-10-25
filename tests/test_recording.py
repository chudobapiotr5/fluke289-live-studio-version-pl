# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Piotr
# This program comes with NO WARRANTY; see COPYING for license terms.
import csv
import queue
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from fluke289.worker import Worker
from fluke289.protocol import parse_qdda
from fluke289.storage import CsvStore
from test_app import SAMPLE


class FakeMeter:
    def __init__(self, *args): pass
    def identify(self): return 'FLUKE 289,V1.41,123'
    def snapshot(self): return parse_qdda(SAMPLE)
    def close(self): pass


def event(worker, expected, timeout=3):
    deadline = time.monotonic()+timeout
    while time.monotonic() < deadline:
        kind, data = worker.events.get(timeout=max(.01, deadline-time.monotonic()))
        if kind == expected: return data
        if kind == 'fatal': raise AssertionError(data)
    raise AssertionError('Brak zdarzenia '+expected)


class RecordingTests(unittest.TestCase):
    def stop(self, w):
        w.stop_event.set()
        w.join(3)
        self.assertFalse(w.is_alive())

    def test_preview_never_opens_measurement_files(self):
        with patch('fluke289.worker.Store') as db, patch('fluke289.worker.CsvStore') as csvstore:
            w = Worker('test', interval=.02, factory=FakeMeter)
            w.start()
            try:
                event(w, 'snapshot')
                event(w, 'snapshot')
            finally: self.stop(w)
            db.assert_not_called()
            csvstore.assert_not_called()

    def test_start_stop_csv_then_sqlite_without_disconnect(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            csvpath, dbpath = folder/'part1.csv', folder/'part2.sqlite3'
            w = Worker('test', interval=.03, factory=FakeMeter)
            w.start()
            try:
                event(w, 'snapshot')
                self.assertEqual(list(folder.iterdir()), [])
                w.start_recording(str(csvpath), 'CSV')
                self.assertEqual(event(w, 'recording')['format'], 'CSV')
                event(w, 'snapshot')
                w.stop_recording()
                self.assertIsNone(event(w, 'recording'))
                size = csvpath.stat().st_size
                event(w, 'snapshot')
                event(w, 'snapshot')
                self.assertEqual(csvpath.stat().st_size, size)
                with csvpath.open(encoding='utf-8-sig') as f:
                    rows = list(csv.DictReader(f))
                self.assertGreaterEqual(len(rows), 2)
                self.assertEqual(rows[0]['identity'], 'FLUKE 289,V1.41,123')
                self.assertEqual(rows[0]['value_base'], '0.005029')
                self.assertFalse(dbpath.exists())
                w.start_recording(str(dbpath), 'SQLite')
                event(w, 'recording')
                event(w, 'snapshot')
                w.stop_recording()
                event(w, 'recording')
                with sqlite3.connect(dbpath) as db:
                    kinds = [r[0] for r in db.execute('SELECT kind FROM events')]
                self.assertIn('identity', kinds)
                self.assertIn('snapshot', kinds)
            finally: self.stop(w)

    def test_file_error_does_not_kill_preview(self):
        with tempfile.TemporaryDirectory() as directory:
            w = Worker('test', interval=.02, factory=FakeMeter)
            w.start()
            try:
                event(w, 'snapshot')
                w.start_recording(str(Path(directory)/'absent'/'a.csv'), 'CSV')
                event(w, 'recording_error')
                event(w, 'snapshot')
                self.assertTrue(w.is_alive())
            finally: self.stop(w)

    def test_csv_never_silently_overwrites_existing_data(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'keep.csv'
            path.write_text('keep me')
            with self.assertRaises(FileExistsError): CsvStore(path)
            self.assertEqual(path.read_text(), 'keep me')

    def test_write_error_stops_only_recording(self):
        class BrokenStore:
            closed = False
            def __init__(self, path): pass
            def add(self, kind, data):
                if kind == 'snapshot': raise OSError('dysk pełny')
            def close(self): BrokenStore.closed = True
        with patch('fluke289.worker.CsvStore', BrokenStore):
            w = Worker('test', interval=.03, factory=FakeMeter)
            w.start()
            try:
                event(w, 'snapshot')
                w.start_recording('test.csv', 'CSV')
                event(w, 'recording')
                self.assertIn('dysk pełny', event(w, 'recording_error'))
                event(w, 'snapshot')
                self.assertIsNone(w.store)
                self.assertTrue(BrokenStore.closed)
            finally: self.stop(w)

    def test_record_stop_responsive_with_long_poll_interval(self):
        with tempfile.TemporaryDirectory() as directory:
            w = Worker('test', interval=3600, factory=FakeMeter)
            w.start()
            try:
                event(w, 'snapshot')
                w.start_recording(str(Path(directory)/'a.csv'), 'CSV')
                event(w, 'recording', timeout=1)
                w.stop_recording()
                self.assertIsNone(event(w, 'recording', timeout=1))
            finally: self.stop(w)

if __name__ == '__main__': unittest.main()
