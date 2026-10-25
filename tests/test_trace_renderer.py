# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Piotr
# This program comes with NO WARRANTY; see COPYING for license terms.
import io
import struct
import unittest
from fluke289.trace_renderer import TraceRenderer

class TraceTests(unittest.TestCase):
    def test_real_cairo_renders_png(self):
        renderer=TraceRenderer()
        data=renderer.render(300,160,[([12,130,90,112,150,30,280,50],'#65dbb2')],[(280,50,'#65dbb2')])
        self.assertEqual(data[:8],b'\x89PNG\r\n\x1a\n')
        self.assertEqual(struct.unpack('>II',data[16:24]),(300,160))
        self.assertGreater(len(data),300)

    def test_bad_image_size(self):
        renderer=TraceRenderer()
        for width,height in [(0,300),(-2,20),(20000,20),(10000,10000)]:
            with self.assertRaises(ValueError): renderer.render(width,height,[])

class AsyncTraceTests(unittest.TestCase):
    def test_rendering_does_not_block_navigation_and_latest_frame_wins(self):
        import threading
        from fluke289.trace_renderer import AsyncTraceRenderer
        entered=threading.Event(); release=threading.Event()
        class SlowRenderer:
            def render(self,width,height,paths,dots):
                if width==1:
                    entered.set(); release.wait(2)
                return str(width).encode()
        worker=AsyncTraceRenderer(SlowRenderer())
        try:
            worker.submit(1,1,20,[],[])
            self.assertTrue(entered.wait(1))
            for version in range(2,101): worker.submit(version,version,20,[],[])
            self.assertLessEqual(worker.jobs.qsize(),1)
            release.set()
            import time
            deadline=time.monotonic()+2
            result=None
            while time.monotonic()<deadline:
                try: result=worker.results.get(timeout=.1)
                except __import__('queue').Empty: continue
                if result[0]==100: break
            self.assertEqual(result,(100,b'100',None))
        finally:
            release.set(); worker.close(); worker.thread.join(1)
        self.assertFalse(worker.thread.is_alive())

    def test_renderer_error_is_reported_without_thread_crash(self):
        from fluke289.trace_renderer import AsyncTraceRenderer
        class Fails:
            def render(self,*args): raise OSError('render failure')
        worker=AsyncTraceRenderer(Fails())
        try:
            worker.submit(7,10,10,[],[])
            self.assertEqual(worker.results.get(timeout=2),(7,None,'render failure'))
        finally: worker.close(); worker.thread.join(1)
