# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Piotr
# This program comes with NO WARRANTY; see COPYING for license terms.
import unittest
from fluke289.history import History
from fluke289.protocol import parse_qdda
from fluke289.mini_chart import preview_samples
from test_app import SAMPLE

class PreviewTests(unittest.TestCase):
    def test_minute_current_segment_and_invalid_values(self):
        h=History()
        for t in [1,40,80]: h.add(parse_qdda(SAMPLE).as_dict(),t)
        h.add(parse_qdda(SAMPLE.replace('NORMAL','OL')).as_dict(),90)
        points,unit=preview_samples(h,'LIVE')
        self.assertEqual([p[0] for p in points],[40,80,90])
        self.assertIsNone(points[-1][1])
        self.assertEqual(unit,'VAC')
        h.add(parse_qdda(SAMPLE.replace('MV_AC','V_DC')).as_dict(),91)
        self.assertEqual(len(preview_samples(h,'LIVE')[0]),1)
        self.assertEqual(preview_samples(h,'ABSENT'),([],None))

    def test_connection_gap_preserved(self):
        h=History()
        h.add(parse_qdda(SAMPLE).as_dict(),1)
        h.gap()
        h.add(parse_qdda(SAMPLE).as_dict(),2)
        self.assertTrue(preview_samples(h,'LIVE')[0][-1][2])

class MiniInteractionTests(unittest.TestCase):
    def test_auto_blocks_zoom_manual_accumulates(self):
        from unittest.mock import Mock
        from types import SimpleNamespace
        from fluke289.mini_chart import MiniChart
        from fluke289.viewport import TimeViewport
        w=MiniChart.__new__(MiniChart)
        w.auto=Mock(); w.auto.get.return_value=True
        w.viewport=TimeViewport(); w.viewport.update_domain(100,200)
        w.bounds=(80,400,22,150,100,200,0,1,1,'Ω')
        w.request_draw=Mock()
        e=SimpleNamespace(x=240,y=90,num=4,delta=0)
        w.zoom(e); self.assertIsNone(w.viewport.selection)
        w.auto.get.return_value=False
        w.zoom(e); w.zoom(e)
        self.assertAlmostEqual(w.viewport.selection[1]-w.viewport.selection[0],64)
        w.auto.get.return_value=True
        w.toggle_auto(); self.assertIsNone(w.viewport.selection)

    def test_tooltip_snaps_by_time_even_far_from_line(self):
        from unittest.mock import Mock
        from types import SimpleNamespace
        from fluke289.mini_chart import MiniChart
        w=MiniChart.__new__(MiniChart)
        w.canvas=Mock(); w.canvas.bbox.return_value=(0,0,130,30)
        w.field=Mock(); w.field.get.return_value='LIVE'
        w.bounds=(80,400,22,200,100,200,0,3e6,1e6,'MΩ')
        w.hit_points=[(150,2.5e6,False)]
        w.hit_readings={150:{'value':2.5e6,'state':'NORMAL','unit':'OHM','multiplier':6,'decimals':4}}
        w.hover(SimpleNamespace(x=240,y=190))
        self.assertIn('2.5000 MΩ',w.canvas.create_text.call_args.kwargs['text'])
