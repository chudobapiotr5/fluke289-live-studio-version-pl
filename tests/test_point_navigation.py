# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Piotr
import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from fluke289.point_navigation import elapsed_text,step_point
from fluke289.history_gui import HistoryWindow
from fluke289.history import History

class PointTests(unittest.TestCase):
    def test_steps_are_chronological_without_wrap_or_interpolation(self):
        points=[(3,'c'),(1,'a'),(2,'b')]
        self.assertEqual(step_point(points,None,1),(1,'a'))
        self.assertEqual(step_point(points,1,1),(2,'b'))
        self.assertEqual(step_point(points,2,-1),(1,'a'))
        self.assertEqual(step_point(points,3,1),(3,'c'))
        self.assertEqual(step_point(points,1,-1),(1,'a'))
        self.assertIsNone(step_point([],None,1))
    def test_elapsed_format_minutes_hours_days_and_rounding(self):
        self.assertEqual(elapsed_text(129.654),'02:09.654')
        self.assertEqual(elapsed_text(3661.125),'01:01:01.125')
        self.assertEqual(elapsed_text(86400,False),'24:00:00')
        self.assertEqual(elapsed_text(59.9999),'01:00.000')
    def test_memory_origin_is_header_start_not_first_extremum(self):
        w=HistoryWindow.__new__(HistoryWindow);w.history=History();w.time_source='meter';w.selected_segment=1
        w.history.samples.append({'segment':1,'time':110,'data':{'minmax_start':100}})
        w.elapsed_var=Mock();w.elapsed_var.get.return_value=True
        self.assertEqual(w.time_text(129.654),'00:29.654')
    def test_point_table_displays_selected_snapshot_not_latest(self):
        w=HistoryWindow.__new__(HistoryWindow);w.table=Mock();w.table.get_children.return_value=[]
        w.unit_var=Mock();w.unit_var.get.return_value='VAC';w.time_source='meter'
        r={'id':'PRIMARY','unit':'VAC','value':228.95,'multiplier':0,'decimals':2,'state':'NORMAL','attribute':'NONE'}
        sample={'time':100,'data':{'readings':[r]}}
        w.update_point_table(sample)
        values=w.table.insert.call_args.kwargs['values']
        self.assertEqual(values[1],'PRIMARY');self.assertEqual(values[2],'228.95')
    def test_elapsed_toggle_never_modifies_timestamp(self):
        w=HistoryWindow.__new__(HistoryWindow);w.history=History();w.selected_segment=1;w.time_source='computer'
        w.history.samples.append({'segment':1,'time':100,'data':{}})
        w.elapsed_var=Mock();w.elapsed_var.get.return_value=True
        self.assertEqual(w.time_text(101),'00:01.000')
        self.assertEqual(w.history.samples[0]['time'],100)

    def test_origin_survives_live_history_eviction(self):
        w=HistoryWindow.__new__(HistoryWindow);w.history=History(limit=2);w.time_source='computer'
        data={'primary':'V_AC','secondary':'NONE','modes':[]}
        for stamp in [100,101,102,103]:w.history.add(data,stamp)
        w.selected_segment=w.history.segment
        self.assertEqual(w.elapsed_origin(),100)
