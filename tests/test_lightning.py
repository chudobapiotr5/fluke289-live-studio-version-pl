# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Piotr
# This program comes with NO WARRANTY; see COPYING for license terms.
import unittest
from unittest.mock import Mock
from fluke289.gui import App

class LightningTests(unittest.TestCase):
    def test_meter_flag_controls_icon_not_measured_number(self):
        app=App.__new__(App)
        app.lightning_icon=Mock(); app.lightning_shape=1; app.lightning_note=Mock()
        app.update_lightning('ON')
        app.lightning_icon.itemconfigure.assert_called_with(1,state='normal')
        self.assertIn('niebezpieczne napięcie',app.lightning_note.set.call_args.args[0])
        app.update_lightning('OFF')
        app.lightning_icon.itemconfigure.assert_called_with(1,state='hidden')
        app.lightning_note.set.assert_called_with('')
        app.update_lightning(None)
        app.lightning_icon.itemconfigure.assert_called_with(1,state='hidden')
        self.assertIn('brak aktualnych danych',app.lightning_note.set.call_args.args[0])
        app.update_lightning('NEW_FLAG')
        self.assertIn('nieznany',app.lightning_note.set.call_args.args[0])
