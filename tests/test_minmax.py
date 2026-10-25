# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Piotr
# This program comes with NO WARRANTY; see COPYING for license terms.
import unittest
from fluke289.minmax import meter_minmax, elapsed_text
from fluke289.protocol import parse_qdda
from test_app import SAMPLE, PEAK

class MinMaxTests(unittest.TestCase):
    def test_meter_values_order_and_elapsed(self):
        s=parse_qdda(PEAK)
        s.minmax_start=100
        for i,r in enumerate(s.readings): r.meter_time=115+i
        rows=meter_minmax(s)
        self.assertEqual([r[0] for r in rows],['MAXIMUM','AVERAGE','MINIMUM'])
        self.assertEqual(rows[0][2],'30.55 mV')
        self.assertEqual(rows[0][3],'00:00:18')
        # Not recomputed from the USB sample's current LIVE value.
        s.readings[0].value=999
        self.assertEqual(meter_minmax(s),rows)

    def test_normal_mode_missing_fields_and_ol(self):
        s=parse_qdda(SAMPLE)
        self.assertIsNone(meter_minmax(s))
        s.modes=['MIN_MAX_AVG']
        self.assertTrue(all(row[2]=='—' for row in meter_minmax(s)))
        s=parse_qdda(PEAK)
        next(r for r in s.readings if r.id=='MAXIMUM').state='OL'
        self.assertEqual(meter_minmax(s)[0][2],'OL')

    def test_elapsed_not_host_clock(self):
        self.assertEqual(elapsed_text(137.9,100),'00:00:37')
        self.assertEqual(elapsed_text(90061,1),'1 d 01:01:00')
        self.assertEqual(elapsed_text(1,0),'—')
        self.assertEqual(elapsed_text(90,100),'—')
