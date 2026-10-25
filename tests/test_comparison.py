# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Piotr
import copy
import unittest
from fluke289.history import History
from fluke289.comparison import compare_histories,choices

class ComparisonTests(unittest.TestCase):
    def source(self,offset=0,unit='OHM'):
        h=History()
        for t,value in [(100,336.44),(101,336.45)]:
            h.add({'primary':'OHMS','secondary':'NONE','modes':[], 'readings':[{'id':'PRIMARY','unit':unit,'value':value,'meter_time':t+offset,'state':'NORMAL','multiplier':0,'decimals':2}]},t+5000+offset)
        return h
    def test_meter_clock_and_shift_preserve_values_and_sources(self):
        a=self.source();b=self.source(10);before=copy.deepcopy(list(b.samples))
        h=compare_histories(a,b,choices(a)[0],choices(b)[0],-10)
        self.assertEqual([s['time'] for s in h.samples],[100,100,101,101])
        self.assertEqual([s['data']['readings'][0]['value'] for s in h.samples],[336.44,336.44,336.45,336.45])
        self.assertEqual(list(b.samples),before)
    def test_relative_alignment(self):
        a=self.source();b=self.source(30)
        h=compare_histories(a,b,choices(a)[0],choices(b)[0],relative=True)
        self.assertEqual([s['time'] for s in h.samples],[0,0,1,1])
    def test_different_units_rejected(self):
        a=self.source();b=self.source(unit='Hz')
        with self.assertRaises(ValueError):compare_histories(a,b,choices(a)[0],choices(b)[0])
    def test_gap_kept(self):
        a=self.source();b=self.source();a.samples[-1]['gap']=True
        h=compare_histories(a,b,choices(a)[0],choices(b)[0])
        self.assertTrue(any(s['gap'] and s['time']==101 for s in h.samples))

    def test_defaults_match_primary_despite_wire_order(self):
        from fluke289.comparison import preferred_pair
        a=[(1,'LIVE','OHM'),(1,'PRIMARY','OHM')]
        b=[(1,'MAXIMUM','OHM'),(1,'MINIMUM','OHM'),(1,'PRIMARY','OHM')]
        self.assertEqual(preferred_pair(a,b),(a[1],b[2]))

    def test_automatic_match_enables_comparison_after_both_files(self):
        from unittest.mock import Mock
        from fluke289.comparison_gui import ComparisonWindow
        w=ComparisonWindow.__new__(ComparisonWindow)
        w.sources=[None,None];w.options=[[],[]];w.feedback=Mock()
        w.compare_button=Mock();w.boxes=[Mock(),Mock()]
        w.match_fields()
        w.compare_button.configure.assert_called_with(state='disabled')
        self.assertIn('oba pliki',w.feedback.set.call_args.args[0])
        w.sources=[self.source(),self.source()];w.options=[choices(h) for h in w.sources]
        w.match_fields()
        w.compare_button.configure.assert_called_with(state='normal')
        self.assertIn('PRIMARY ↔ B: PRIMARY',w.feedback.set.call_args.args[0])

    def test_summary_exact_shift_and_tolerance(self):
        from fluke289.comparison import comparison_stats
        a=self.source();b=self.source(10)
        h=compare_histories(a,b,choices(a)[0],choices(b)[0],shift=-10)
        stats=comparison_stats(h,.1)
        self.assertEqual(stats['count'],2);self.assertEqual(stats['equal'],2)
        self.assertEqual(stats['maximum'],0);self.assertEqual(stats['max_dt'],0)

    def test_summary_limited_nearest_pair_and_worst(self):
        from fluke289.comparison import comparison_stats
        a=self.source();b=self.source()
        b.samples[-1]['data']['readings'][0]['value']=336.5
        h=compare_histories(a,b,choices(a)[0],choices(b)[0])
        stats=comparison_stats(h)
        self.assertEqual(stats['count'],2);self.assertEqual(stats['equal'],1)
        self.assertAlmostEqual(stats['maximum'],.05)
        self.assertEqual(stats['worst']['a'][0],101)
        with self.assertRaises(ValueError):comparison_stats(h,0)

    def test_summary_never_reuses_point_and_ignores_invalid(self):
        from fluke289.comparison import comparison_stats
        a=self.source();b=self.source()
        a.samples[-1]['data']['readings'][0]['meter_time']=100.1
        b.samples[-1]['data']['readings'][0]['state']='OL'
        h=compare_histories(a,b,choices(a)[0],choices(b)[0])
        stats=comparison_stats(h,.5)
        self.assertEqual(stats['count'],1)

    def test_summary_no_overlap(self):
        from fluke289.comparison import comparison_stats
        a=self.source();b=self.source(100)
        h=compare_histories(a,b,choices(a)[0],choices(b)[0])
        self.assertIsNone(comparison_stats(h)['overlap'])
