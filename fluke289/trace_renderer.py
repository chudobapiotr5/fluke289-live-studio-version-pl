# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Piotr
# This program comes with NO WARRANTY; see COPYING for license terms.
"""Antialiased measurement strokes using Ubuntu's native Cairo library.

Only rasterization changes: no curve fitting, interpolation, or resampling of data.
No extra Python package is required.
"""
import ctypes as C
from ctypes.util import find_library
import math


class TraceRenderer:
    def __init__(self):
        path = find_library('cairo')
        if not path: raise OSError('Brak biblioteki libcairo2')
        self.lib = C.CDLL(path)
        signatures = {
            'cairo_image_surface_create': ([C.c_int,C.c_int,C.c_int],C.c_void_p),
            'cairo_create': ([C.c_void_p],C.c_void_p),
            'cairo_surface_destroy': ([C.c_void_p],None),
            'cairo_destroy': ([C.c_void_p],None),
            'cairo_status': ([C.c_void_p],C.c_int),
            'cairo_surface_status': ([C.c_void_p],C.c_int),
            'cairo_set_antialias': ([C.c_void_p,C.c_int],None),
            'cairo_set_line_cap': ([C.c_void_p,C.c_int],None),
            'cairo_set_line_join': ([C.c_void_p,C.c_int],None),
            'cairo_set_line_width': ([C.c_void_p,C.c_double],None),
            'cairo_set_source_rgba': ([C.c_void_p,C.c_double,C.c_double,C.c_double,C.c_double],None),
            'cairo_move_to': ([C.c_void_p,C.c_double,C.c_double],None),
            'cairo_line_to': ([C.c_void_p,C.c_double,C.c_double],None),
            'cairo_arc': ([C.c_void_p,C.c_double,C.c_double,C.c_double,C.c_double,C.c_double],None),
            'cairo_stroke': ([C.c_void_p],None),
            'cairo_fill': ([C.c_void_p],None),
        }
        for name,(args,result) in signatures.items():
            fn=getattr(self.lib,name)
            fn.argtypes=args; fn.restype=result
        self.callback_type=C.CFUNCTYPE(C.c_int,C.c_void_p,C.POINTER(C.c_ubyte),C.c_uint)
        self.lib.cairo_surface_write_to_png_stream.argtypes=[C.c_void_p,self.callback_type,C.c_void_p]
        self.lib.cairo_surface_write_to_png_stream.restype=C.c_int

    def render(self, width, height, paths, dots=()):
        if not (0<width<=16384 and 0<height<=16384 and width*height<=40000000):
            raise ValueError('Nieprawidłowy rozmiar wykresu')
        lib=self.lib
        surface=lib.cairo_image_surface_create(0,int(width),int(height))
        context=None
        try:
            if lib.cairo_surface_status(surface): raise OSError('Nie udało się utworzyć obrazu wykresu')
            context=lib.cairo_create(surface)
            lib.cairo_set_antialias(context,6)  # CAIRO_ANTIALIAS_BEST
            lib.cairo_set_line_cap(context,1)
            lib.cairo_set_line_join(context,1)
            def color(hexcolor):
                rgb=[int(hexcolor[i:i+2],16)/255 for i in (1,3,5)]
                lib.cairo_set_source_rgba(context,*rgb,1.)
            for coords,hexcolor in paths:
                if len(coords)<4: continue
                color(hexcolor)
                lib.cairo_set_line_width(context,2.4)
                lib.cairo_move_to(context,coords[0],coords[1])
                for i in range(2,len(coords),2): lib.cairo_line_to(context,coords[i],coords[i+1])
                lib.cairo_stroke(context)
            for x,y,hexcolor in dots:
                color(hexcolor)
                lib.cairo_arc(context,x,y,3.,0.,2*math.pi)
                lib.cairo_fill(context)
            if lib.cairo_status(context): raise OSError('Błąd renderowania wykresu')
            chunks=[]
            @self.callback_type
            def write(closure,data,length):
                try: chunks.append(C.string_at(data,length)); return 0
                except Exception: return 11  # CAIRO_STATUS_WRITE_ERROR
            if lib.cairo_surface_write_to_png_stream(surface,write,None):
                raise OSError('Błąd obrazu PNG wykresu')
            return b''.join(chunks)
        finally:
            if context: lib.cairo_destroy(context)
            lib.cairo_surface_destroy(surface)

class AsyncTraceRenderer:
    """One background renderer, at most one pending frame; never calls Tk."""
    def __init__(self, renderer):
        import queue
        import threading
        self.renderer = renderer
        self.jobs = queue.Queue(maxsize=1)
        self.results = queue.Queue(maxsize=1)
        self.stopped = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    @staticmethod
    def replace(queue, item):
        import queue as queues
        try: queue.put_nowait(item)
        except queues.Full:
            try: queue.get_nowait()
            except queues.Empty: pass
            try: queue.put_nowait(item)
            except queues.Full: pass

    def submit(self, version, width, height, paths, dots):
        if not self.stopped.is_set():
            self.replace(self.jobs, (version, width, height, paths, dots))

    def _run(self):
        import queue
        while not self.stopped.is_set():
            try: job = self.jobs.get(timeout=.1)
            except queue.Empty: continue
            version, *args = job
            try: result = (version, self.renderer.render(*args), None)
            except Exception as e: result = (version, None, str(e))
            if not self.stopped.is_set(): self.replace(self.results, result)

    def close(self):
        self.stopped.set()
