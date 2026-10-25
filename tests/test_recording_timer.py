# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Piotr
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fluke289.worker import Worker

class TimerTests(unittest.TestCase):
    def test_expiry_closes_file_and_keeps_preview_worker_running(self):
        with tempfile.TemporaryDirectory() as folder:
            w=Worker('test')
            with patch('fluke289.worker.time.monotonic',return_value=100):
                w.start_recording(str(Path(folder)/'timer.csv'),'CSV',5); w._commands()
            self.assertEqual(w.record_deadline,105)
            with patch('fluke289.worker.time.monotonic',return_value=104): w._expire_recording()
            self.assertIsNotNone(w.store)
            with patch('fluke289.worker.time.monotonic',return_value=105): w._expire_recording()
            self.assertIsNone(w.store); self.assertIsNone(w.record_deadline)
            self.assertFalse(w.stop_event.is_set())
            self.assertTrue(any(kind=='recording_finished' for kind,data in list(w.events.queue)))

    def test_manual_stop_cancels_deadline_and_restart_without_limit(self):
        with tempfile.TemporaryDirectory() as folder:
            w=Worker('test');w.start_recording(str(Path(folder)/'a.csv'),'CSV',3600);w._commands()
            w.stop_recording();w._commands();self.assertIsNone(w.record_deadline)
            w.start_recording(str(Path(folder)/'b.csv'),'CSV');w._commands()
            self.assertIsNone(w.record_deadline);self.assertIsNotNone(w.store);w._close_store()

    def test_invalid_duration_creates_no_file(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'bad.csv';w=Worker('test');w.start_recording(str(p),'CSV',0);w._commands()
            self.assertFalse(p.exists());self.assertIsNone(w.store)
