# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Piotr
# This program comes with NO WARRANTY; see COPYING for license terms.
import unittest
from fluke289.bargraph import bar_state
from fluke289.protocol import parse_qdda
from test_app import SAMPLE

class BarTests(unittest.TestCase):
    def test_real_scale_and_live_fallback(self):
        s=parse_qdda(SAMPLE)
        s.primary='OHMS'; s.range_unit='OHM'; s.range_number=5; s.range_multiplier=6
        for r in s.readings: r.unit='OHM'; r.value=1273500
        b=bar_state(s)
        self.assertEqual(b.full,5000000)
        self.assertAlmostEqual(b.value/b.full,.2547)
        self.assertIn('LIVE',b.source)
        self.assertFalse(b.signed)

    def test_actual_bargraph_priority_hold_and_errors(self):
        s=parse_qdda(SAMPLE)
        s.readings[0].id='BARGRAPH'
        b=bar_state(s)
        self.assertEqual(b.source,'BARGRAPH z miernika')
        s.readings[0].state='OL'
        self.assertIsNone(bar_state(s).value)
        s.readings[0].id='LIVE'; s.readings[0].state='NORMAL'
        s.readings[1].value=999
        s.modes=['HOLD']
        self.assertEqual(bar_state(s).value,s.readings[0].value)

    def test_signed_and_unsupported(self):
        s=parse_qdda(SAMPLE)
        s.range_unit='VDC'
        for r in s.readings: r.unit='VDC'; r.value=-.01
        self.assertTrue(bar_state(s).signed)
        s.range_unit='Hz'
        self.assertIsNone(bar_state(s))
        s.range_unit='VDC'; s.range_number=0
        self.assertIsNone(bar_state(s))
