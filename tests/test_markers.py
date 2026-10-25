# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Piotr
# This program comes with NO WARRANTY; see COPYING for license terms.
import unittest
from unittest.mock import Mock
from types import SimpleNamespace
from fluke289.markers import Markers
from fluke289.history_gui import HistoryWindow


def sample(t, value, field='LIVE', unit='OHM', segment=1, state='NORMAL'):
    return {'segment':segment,'time':t}, {'id':field,'unit':unit,'value':value,'state':state}

class MarkerTests(unittest.TestCase):
    def test_actual_sample_values_signed_difference_and_copy(self):
        m=Markers(); m.set_scope(1,'LIVE','OHM')
        s,r=sample(100,2100000); m.set_point('A',s,r)
        r['value']=0
        s,r=sample(105,2350000); m.set_point('B',s,r)
        self.assertEqual(m.difference(),(5,250000))
        s,r=sample(98,2000000); m.set_point('B',s,r)
        self.assertEqual(m.difference(),(-2,-100000))
        m.clear(); self.assertIsNone(m.difference())

    def test_scope_change_and_invalid_readings(self):
        m=Markers(); m.set_scope(1,'LIVE','OHM')
        s,r=sample(100,1); m.set_point('A',s,r)
        m.set_scope(1,'LIVE','OHM'); self.assertIn('A',m.points)
        for kwargs in [{'field':'MAXIMUM'},{'unit':'VDC'},{'segment':2},{'state':'OL'}]:
            s,r=sample(105,2,**kwargs)
            with self.assertRaises(ValueError): m.set_point('B',s,r)
        m.set_scope(2,'LIVE','OHM'); self.assertEqual(m.points,{})

    def make_window(self):
        w=HistoryWindow.__new__(HistoryWindow)
        w.markers=Markers(); w.markers.set_scope(1,'LIVE','OHM')
        w.marker_field=Mock(); w.marker_field.get.return_value='LIVE'
        w.unit_var=Mock(); w.unit_var.get.return_value='OHM'
        w.marker_summary=Mock(); w.canvas=Mock(); w.draw=Mock()
        w.display_scale=1e6; w.display_unit='MΩ'
        w.bounds=(124,850,44,300,100,110,2e6,3e6)
        w.points=[]
        for x,t,value in [(200,101,2100000),(650,107,2600000)]:
            s,r=sample(t,value)
            w.points.append((x,100,s,r,'#65dbb2'))
        return w

    def test_click_snaps_to_real_sample_and_overlay_survives_zoom(self):
        w=self.make_window()
        w.pick_marker('A',SimpleNamespace(x=205,y=100))
        w.pick_marker('B',SimpleNamespace(x=645,y=100))
        self.assertEqual(w.markers.difference(),(6,500000))
        w.draw_markers()
        text=w.marker_summary.set.call_args.args[0]
        self.assertIn('0,5 MΩ',text)
        self.assertIn('6 s',text)
        self.assertEqual(w.canvas.create_line.call_count,2)
        w.canvas.reset_mock()
        w.bounds=(124,850,44,300,103,110,2e6,3e6)
        w.draw_markers()
        self.assertEqual(w.canvas.create_line.call_count,1)
        self.assertEqual(w.markers.difference(),(6,500000))

    def test_armed_click_and_marker_drag_do_not_pan(self):
        w=self.make_window(); w.drag_state=None; w.marker_drag=None
        w.markers.pending='A'
        w.begin_pan(SimpleNamespace(x=205,y=100))
        self.assertIn('A',w.markers.points)
        self.assertIsNone(w.drag_state)
        # Position of A at time 101 in current viewport.
        w.begin_pan(SimpleNamespace(x=196.6,y=100))
        self.assertEqual(w.marker_drag,'A')
        w.drag_pan(SimpleNamespace(x=650,y=100))
        self.assertEqual(w.markers.points['A'].time,107)
        self.assertIsNone(w.drag_state)
