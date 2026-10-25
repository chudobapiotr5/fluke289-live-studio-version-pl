# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Piotr
"""CSV pairs and vector PDF reports, using the existing system Cairo library."""
import csv
import ctypes as C
import math
import os
import tempfile
from datetime import datetime,timezone
from pathlib import Path
from . import __version__
from .history import valid
from .trace_renderer import TraceRenderer

NOTICE='Porównanie zgodności zapisów - nie świadectwo kalibracji miernika.'

def timestamp(history,value):
    if getattr(history,'comparison_relative',False):
        sign='-' if value<0 else '';value=abs(value)
        hours,rest=divmod(int(value),3600);minutes,seconds=divmod(rest,60)
        return f'{sign}{hours:02}:{minutes:02}:{seconds:02}.{int((value-int(value))*1000):03}'
    return datetime.fromtimestamp(value,timezone.utc).isoformat(timespec='milliseconds')

def safe_cell(value):
    text=str(value)
    return "'"+text if text.lstrip().startswith(('=','+','-','@')) else text

def atomic_export(path,writer):
    path=Path(path)
    fd,tmp=tempfile.mkstemp(prefix='.'+path.name+'.',suffix='.tmp',dir=path.parent)
    os.close(fd)
    try:
        writer(tmp)
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

def check_destination(history,path):
    target=Path(path).resolve()
    if any(source and target==Path(source).resolve() for source in history.comparison_metadata.get('source_paths',[])):
        raise ValueError('Raport nie może zastąpić pliku pomiarowego. Wybierz inną nazwę.')

def export_csv(history,path):
    check_destination(history,path)
    stats=history.comparison_stats;meta=history.comparison_metadata
    def write(tmp):
        with open(tmp,'w',encoding='utf-8-sig',newline='') as f:
            w=csv.writer(f)
            w.writerow(['pair','time_A','value_A_base','time_B_adjusted','value_B_base','abs_difference_base','signed_B_minus_A_base','time_distance_s','equal_at_common_resolution','unit','file_A','field_A','file_B','field_B','time_mode','shift_B_s','matching_limit_s','raw_meter_time_A','raw_meter_time_B','notice'])
            for i,pair in enumerate(stats['pairs'],1):
                ta,a=pair['a'];tb,b=pair['b']
                w.writerow([i,timestamp(history,ta),repr(a['value']),timestamp(history,tb),repr(b['value']),repr(pair['difference']),repr(b['value']-a['value']),repr(pair['dt']),int(pair['equal']),safe_cell(meta['unit']),safe_cell(meta['file_a']),safe_cell(meta['field_a']),safe_cell(meta['file_b']),safe_cell(meta['field_b']),'relative' if meta['relative'] else 'meter_UTC',meta['shift'],meta['tolerance'],a.get('meter_time',''),b.get('meter_time',''),NOTICE])
    atomic_export(path,write)

class PdfCanvas:
    def __init__(self,path):
        self.lib=TraceRenderer().lib
        for name,args,restype in [
            ('cairo_pdf_surface_create',[C.c_char_p,C.c_double,C.c_double],C.c_void_p),
            ('cairo_select_font_face',[C.c_void_p,C.c_char_p,C.c_int,C.c_int],None),
            ('cairo_set_font_size',[C.c_void_p,C.c_double],None),
            ('cairo_show_text',[C.c_void_p,C.c_char_p],None),
            ('cairo_rectangle',[C.c_void_p,C.c_double,C.c_double,C.c_double,C.c_double],None),
            ('cairo_save',[C.c_void_p],None),('cairo_restore',[C.c_void_p],None),
            ('cairo_clip',[C.c_void_p],None),('cairo_show_page',[C.c_void_p],None),
            ('cairo_surface_finish',[C.c_void_p],None)]:
            fn=getattr(self.lib,name);fn.argtypes=args;fn.restype=restype
        self.surface=self.lib.cairo_pdf_surface_create(os.fsencode(path),842,595)
        self.context=self.lib.cairo_create(self.surface)
        if self.lib.cairo_surface_status(self.surface):self.close();raise OSError('Nie udało się utworzyć PDF.')
    def color(self,rgb):self.lib.cairo_set_source_rgba(self.context,*rgb,1.)
    def text(self,x,y,value,size=10,bold=False,color=(.12,.17,.23)):
        self.color(color);self.lib.cairo_select_font_face(self.context,b'DejaVu Sans',0,int(bold));self.lib.cairo_set_font_size(self.context,size)
        self.lib.cairo_move_to(self.context,x,y);self.lib.cairo_show_text(self.context,str(value).encode('utf-8'))
    def line(self,points,color=(.8,.83,.87),width=1.):
        if len(points)<2:return
        self.color(color);self.lib.cairo_set_line_width(self.context,width)
        self.lib.cairo_move_to(self.context,*points[0])
        for point in points[1:]:self.lib.cairo_line_to(self.context,*point)
        self.lib.cairo_stroke(self.context)
    def close(self):
        if self.context:self.lib.cairo_destroy(self.context);self.context=None
        if self.surface:self.lib.cairo_surface_destroy(self.surface);self.surface=None
    def finish(self):
        self.lib.cairo_show_page(self.context)
        if self.lib.cairo_status(self.context):raise OSError('Błąd rysowania raportu PDF.')
        self.lib.cairo_surface_finish(self.surface)
        if self.lib.cairo_surface_status(self.surface):raise OSError('Błąd zapisu raportu PDF.')

def short(text,limit=100):
    return text if len(text)<=limit else text[:limit-3]+'...'

def export_pdf(history,path):
    check_destination(history,path)
    meta=history.comparison_metadata;stats=history.comparison_stats
    def write(tmp):
        c=PdfCanvas(tmp)
        try:
            c.text(40,38,'Porównanie zapisów A / B',22,True)
            c.text(40,58,f'Fluke 289 Live Studio {__version__} | raport: '+datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),9)
            c.text(40,82,'A: '+short(meta['file_a'],70),10,True,color=(0,.42,.35))
            c.text(40,98,'B: '+short(meta['file_b'],70),10,True,color=(.65,.36,0))
            c.text(40,116,f"Pola: A {meta['field_a']} / B {meta['field_b']} | jednostka bazowa: {meta['unit']}")
            mode='od początku każdej serii' if meta['relative'] else 'czas odczytu Fluke (UTC wg znacznika)'
            c.text(40,133,f"Dopasowanie: {mode} | przesunięcie B: {meta['shift']:g} s | limit: {meta['tolerance']:g} s",9)
            overlap=stats['overlap']
            c.text(40,150,'Wspólny okres: '+(timestamp(history,overlap[0])+' - '+timestamp(history,overlap[1]) if overlap else 'brak'),9)
            left,right,top,bottom=80,798,185,414
            series={'A':[],'B':[]}
            if overlap:
                low,high=overlap
                for s in history.samples:
                    for r in s['data']['readings']:
                        label=r['id'].split(' · ')[0]
                        if label in series and low<=s['time']<=high:series[label].append((s['time'],r,s['gap']))
                values=[r['value'] for points in series.values() for t,r,g in points if valid(r)]
                if values:
                    ymin,ymax=min(values),max(values);pad=max((ymax-ymin)*.08,max(abs(ymin),abs(ymax))*1e-6,1e-12);ymin-=pad;ymax+=pad
                    xmax=max(high,low+.001)
                    def xy(t,v):return left+(t-low)/(xmax-low)*(right-left),bottom-(v-ymin)/(ymax-ymin)*(bottom-top)
                    c.text(left,173,'Wartość ['+meta['unit']+']',9,True)
                    for i in range(5):
                        y=top+i*(bottom-top)/4;v=ymax-i*(ymax-ymin)/4
                        c.line([(left,y),(right,y)]);c.text(40,y+3,f'{v:.6g}',8)
                    for i in range(4):
                        t=low+i*(xmax-low)/3;x=xy(t,ymin)[0]
                        c.line([(x,top),(x,bottom)],(.9,.92,.94),.5)
                        label=timestamp(history,t);label=label if meta['relative'] else label[11:23]
                        c.text(max(40,min(755,x-28)),432,label,8)
                    c.lib.cairo_save(c.context);c.lib.cairo_rectangle(c.context,left,top,right-left,bottom-top);c.lib.cairo_clip(c.context)
                    for label,color in [('A',(0,.48,.39)),('B',(.75,.43,0))]:
                        chunk=[]
                        for t,r,gap in series[label]:
                            if gap or not valid(r):c.line(chunk,color,1.1);chunk=[]
                            if valid(r):chunk.append(xy(t,r['value']))
                        c.line(chunk,color,1.1)
                        for t,r,gap in series[label]:
                            if valid(r):
                                x,y=xy(t,r['value']);c.color(color);c.lib.cairo_arc(c.context,x,y,1.,0,math.tau);c.lib.cairo_fill(c.context)
                    c.lib.cairo_restore(c.context)
                else:c.text(80,285,'Brak poprawnych odczytów we wspólnym okresie.',12)
            else:c.text(80,285,'Brak wspólnego okresu nagrań.',12)
            c.text(80,449,'Cały wspólny okres; linie łączą zapisane punkty. Zoom i ukrycie linii w oknie nie zmieniają raportu.',8)
            if stats['count']:
                c.text(40,475,f"Pary: {stats['count']} | identyczne na wspólnej rozdzielczości: {stats['equal']}",11,True)
                c.text(40,493,f"Średnia |B-A|: {stats['mean']:.6g} {meta['unit']} | największa: {stats['maximum']:.6g} {meta['unit']} | maks. odstęp czasu: {stats['max_dt']:.3f} s",10)
                worst=stats['worst']
                for label,key,y in [('A','a',513),('B','b',528)]:
                    t,r=worst[key];c.text(40,y,f"Największa różnica - {label}: {timestamp(history,t)} | {r['value']:.12g} {meta['unit']}",9)
            else:c.text(40,475,'Brak par spełniających limit dopasowania.',11,True)
            c.text(40,549,'Najbliższe czasy, bez interpolacji i powtórnego użycia punktu. Różne chwile próbkowania mogą dawać różne wartości.',8)
            c.text(40,568,NOTICE,9,True)
            c.finish()
        finally:c.close()
    atomic_export(path,write)
