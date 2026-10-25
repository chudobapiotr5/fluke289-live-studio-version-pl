# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Piotr
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from fluke289.memory_gui import MemoryWindow

class MemorySaveTests(unittest.TestCase):
    def window(self):
        w=MemoryWindow.__new__(MemoryWindow)
        w.archive={'format':'fluke289-memory-v1','header':{'name':'Próba'},'intervals':[]}
        w.status=Mock(); w.window=None
        return w

    def test_chosen_destination_receives_full_archive(self):
        w=self.window()
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'wybrana-kopia.json'
            self.assertTrue(w.write_archive(path))
            self.assertEqual(json.loads(path.read_text()),w.archive)
            self.assertIn(str(path),w.status.set.call_args.args[0])

    def test_failure_keeps_download_for_retry(self):
        w=self.window(); archive=w.archive
        with tempfile.TemporaryDirectory() as folder, patch('fluke289.memory_gui.messagebox.showerror') as error:
            self.assertFalse(w.write_archive(Path(folder)/'missing'/'copy.json'))
            self.assertIs(w.archive,archive)
            error.assert_called_once()

    def test_cancel_destination_does_not_start_transfer(self):
        w=self.window(); w.busy=False; w.table=Mock(); w.table.selection.return_value=['0']
        w.items=[{'name':'MIN MAX 1'}]; w.worker=Mock()
        with patch('fluke289.memory_gui.filedialog.asksaveasfilename',return_value=''):
            w.download()
        w.worker.memory_request.assert_not_called()
        self.assertFalse(w.busy)
