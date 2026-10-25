# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Piotr
# This program comes with NO WARRANTY; see COPYING for license terms.
import csv
import tempfile
import unittest
from pathlib import Path
from fluke289.history import History, load_session, valid
from fluke289.protocol import parse_qdda
from fluke289.storage import Store, CsvStore
from test_app import SAMPLE, PEAK

class HistoryTests(unittest.TestCase):
    def test_segments_and_bound(self):
        h=History(limit=3)
        a=parse_qdda(SAMPLE).as_dict()
        b=parse_qdda(PEAK).as_dict()
        h.add(a,1)
        h.add(a,2)
        self.assertEqual(len(h.segments()),1)
        h.add(b,3)
        h.add(a,4)
        self.assertEqual(len(h.samples),3)
        self.assertEqual(len(h.segments()),3)
        self.assertEqual(h.view(3,'VAC')[0][1][0]['id'],'LIVE')
        self.assertEqual(h.view(3,'OHM')[0][1],[])

    def test_gap_and_invalid(self):
        h=History()
        a=parse_qdda(SAMPLE).as_dict()
        h.add(a,1)
        h.add(a,2)
        h.gap()
        h.add(a,3)
        self.assertEqual([s['gap'] for s in h.samples],[True,False,True])
        self.assertTrue(valid(a['readings'][0]))
        a['readings'][0]['state']='OL'
        self.assertFalse(valid(a['readings'][0]))

    def test_both_saved_formats_open_inside_app(self):
        with tempfile.TemporaryDirectory() as d:
            for format,cls in [('csv',CsvStore),('sqlite3',Store)]:
                path=Path(d)/('test.'+format)
                store=cls(path)
                store.add('identity','FLUKE 289,V1.41,123')
                store.add('snapshot',parse_qdda(PEAK).as_dict())
                store.add('snapshot',parse_qdda(SAMPLE.replace('NORMAL','OL')).as_dict())
                store.close()
                before=path.read_bytes()
                loaded=load_session(path)
                self.assertEqual(len(loaded.samples),2)
                self.assertEqual(loaded.samples[0]['data']['readings'][2]['id'],'MINIMUM')
                self.assertEqual(loaded.samples[0]['data']['readings'][2]['value'],-.0211)
                self.assertFalse(valid(loaded.samples[1]['data']['readings'][0]))
                self.assertEqual(loaded.samples[0]['identity'],'FLUKE 289,V1.41,123')
                self.assertEqual(before,path.read_bytes())

    def test_bad_input(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'wrong.csv'
            path.write_text('a,b\n1,2\n')
            with self.assertRaises(ValueError): load_session(path)
            path=Path(d)/'missing.sqlite3'
            with self.assertRaises(Exception): load_session(path)
            self.assertFalse(path.exists())

if __name__=='__main__': unittest.main()

class PlotTests(unittest.TestCase):
    def test_plot_does_not_join_across_ol_or_disconnect(self):
        from unittest.mock import Mock
        from fluke289.history_gui import HistoryWindow, COLORS
        h=History()
        for i,state in enumerate(['NORMAL','OL','NORMAL','NORMAL']):
            h.add(parse_qdda(SAMPLE.replace('NORMAL',state)).as_dict(),i+1)
        w=HistoryWindow.__new__(HistoryWindow)
        w.history=h
        w.live=True
        w.selected_segment=1
        w.unit_var=Mock(); w.unit_var.get.return_value='VAC'
        w.span=Mock(); w.span.get.return_value='Cała seria'
        w.series_vars={'LIVE':Mock()}; w.series_vars['LIVE'].get.return_value=True
        w.canvas=Mock(); w.canvas.winfo_width.return_value=900; w.canvas.winfo_height.return_value=300
        w.table=Mock(); w.table.get_children.return_value=[]
        w.note=Mock(); w.summary=Mock()
        w.draw()
        lines=[call for call in w.canvas.create_line.call_args_list if call.kwargs.get('fill')==COLORS[0]]
        self.assertEqual(len(lines),1)
        self.assertEqual(len(lines[0].args),4)
        h.gap()
        h.add(parse_qdda(SAMPLE).as_dict(),5)
        w.canvas.reset_mock()
        w.draw()
        lines=[call for call in w.canvas.create_line.call_args_list if call.kwargs.get('fill')==COLORS[0]]
        self.assertEqual(len(lines),1)
        self.assertEqual(len(lines[0].args),4)

class ChartReadabilityTests(unittest.TestCase):
    def test_engineering_units_and_readable_ticks(self):
        from fluke289.history_gui import axis_scale, decimal_text, axis_ticks
        scale,unit=axis_scale([2740700,2859300],'OHM')
        self.assertEqual((scale,unit),(1e6,'MΩ'))
        self.assertEqual(decimal_text(2750000/scale),'2,75')
        ticks=axis_ticks(2730000,2870000,scale)
        self.assertGreaterEqual(len(ticks),2)
        self.assertEqual(len({label for _,label in ticks}),len(ticks))
        self.assertTrue(all('e' not in label for _,label in ticks))
        self.assertEqual(axis_scale([.005],'VAC'),(.001,'mV AC'))
        self.assertEqual(axis_scale([-2000],'CEL'),(1.,'°C'))
        self.assertEqual(decimal_text(.25/1e6),'0,00000025')

    def test_tooltip_only_near_point_with_time_and_unit(self):
        from unittest.mock import Mock
        from types import SimpleNamespace
        from fluke289.history_gui import HistoryWindow
        w=HistoryWindow.__new__(HistoryWindow)
        w.canvas=Mock()
        w.canvas.bbox.return_value=(0,0,200,65)
        w.bounds=(124,850,44,300,0,1,0,3e6)
        w.display_scale=1e6
        w.display_unit='MΩ'
        w.points=[(800,60,{'time':1000},{'id':'MAXIMUM','value':2750000,'state':'NORMAL','unit':'OHM','multiplier':6,'decimals':2},'#f58baf')]
        w.hover(SimpleNamespace(x=500,y=200))
        w.canvas.create_text.assert_not_called()
        w.hover(SimpleNamespace(x=802,y=61))
        text=w.canvas.create_text.call_args.kwargs['text']
        self.assertIn('Maksimum z Fluke',text)
        self.assertIn('2.75 MΩ',text)
        self.assertIn('Czas:',text)
        x1,y1,x2,y2=w.canvas.create_rectangle.call_args.args
        self.assertGreaterEqual(x1,124)
        self.assertLessEqual(x2,850)
        self.assertGreaterEqual(y1,44)
        self.assertLessEqual(y2,300)
