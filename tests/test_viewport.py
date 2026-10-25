# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Piotr
# This program comes with NO WARRANTY; see COPYING for license terms.
import unittest
from unittest.mock import Mock
from types import SimpleNamespace
from fluke289.viewport import TimeViewport
from fluke289.history_gui import HistoryWindow

class NavigationTests(unittest.TestCase):
    def test_zoom_keeps_cursor_time_and_clamps(self):
        v=TimeViewport(); v.update_domain(100,200)
        a,b=v.zoom((100,200),.25,.5)
        self.assertEqual((a,b),(112.5,162.5))
        self.assertEqual(a+.25*(b-a),125)
        self.assertEqual(v.pan((a,b),-1000),(100,150))
        self.assertEqual(v.pan((a,b),1000),(150,200))
        self.assertEqual(v.zoom((a,b),.5,100),(100,200))

    def test_minimum_width_and_live_eviction(self):
        v=TimeViewport(); v.update_domain(100,200)
        for _ in range(100): v.zoom(v.selection or (100,200),.5,.8)
        self.assertAlmostEqual(v.selection[1]-v.selection[0],.001)
        v.update_domain(180,250)
        self.assertGreaterEqual(v.selection[0],180)
        v.reset(); self.assertIsNone(v.selection)
        v.update_domain(300,300)
        self.assertAlmostEqual(v.domain[1]-v.domain[0],.001)

    def test_linux_wheel_and_drag_handlers(self):
        w=HistoryWindow.__new__(HistoryWindow)
        w.viewport=TimeViewport(); w.viewport.update_domain(100,200)
        w.bounds=(100,900,40,300,100,200,0,1)
        w.follow=Mock(); w.span=Mock(); w.canvas=Mock(); w.draw=Mock()
        w.wheel_zoom(SimpleNamespace(x=500,y=100,num=4,delta=0))
        self.assertEqual(w.viewport.selection,(110,190))
        w.follow.set.assert_called_with(False)
        w.bounds=(100,900,40,300,110,190,0,1)
        w.begin_pan(SimpleNamespace(x=500,y=100))
        w.drag_pan(SimpleNamespace(x=600,y=100))
        self.assertEqual(w.viewport.selection,(100,180))
        w.reset_view()
        self.assertIsNone(w.viewport.selection)
        w.span.set.assert_called_with('Cała seria')

    def test_outside_plot_does_not_zoom(self):
        w=HistoryWindow.__new__(HistoryWindow)
        w.viewport=TimeViewport(); w.viewport.update_domain(100,200)
        w.bounds=(100,900,40,300,100,200,0,1)
        w.wheel_zoom(SimpleNamespace(x=10,y=10,num=4,delta=0))
        self.assertIsNone(w.viewport.selection)

    def test_wheel_burst_accumulates_before_redraw(self):
        w=HistoryWindow.__new__(HistoryWindow)
        w.viewport=TimeViewport(); w.viewport.update_domain(100,200)
        w.bounds=(100,900,40,300,100,200,0,1)
        w.follow=Mock(); w.span=Mock(); w.canvas=Mock(); w.request_draw=Mock()
        # No redraw between events: the second event must use the new selection.
        w.wheel_zoom(SimpleNamespace(x=500,y=100,num=4,delta=0))
        w.wheel_zoom(SimpleNamespace(x=500,y=100,num=4,delta=0))
        self.assertAlmostEqual(w.viewport.selection[1]-w.viewport.selection[0],64)
        w.wheel_zoom(SimpleNamespace(x=500,y=100,num='??',delta=-120))
        self.assertAlmostEqual(w.viewport.selection[1]-w.viewport.selection[0],80)
