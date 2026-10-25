# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Piotr
# This program comes with NO WARRANTY; see COPYING for license terms.
"""Small live preview. Acquisition and recording stay outside this widget."""
import base64
import queue
from datetime import datetime
import tkinter as tk
from tkinter import ttk
from .history import valid
from .display import format_reading, meter_scale
from .viewport import TimeViewport
from types import SimpleNamespace
from .history_gui import axis_scale, decimal_text
from .trace_renderer import TraceRenderer, AsyncTraceRenderer

BG='#1a2230'; TEXT='#edf2f7'; MUTED='#9aaac0'; GREEN='#65dbb2'


def preview_samples(history, field, seconds=60):
    if not history.samples: return [], None
    latest=history.samples[-1]
    selected=next((r for r in latest['data']['readings'] if r['id']==field),None)
    if selected is None: return [], None
    unit=selected['unit']
    end=latest['time']
    points=[]
    for s in reversed(history.samples):
        if s['segment']!=latest['segment'] or (seconds is not None and s['time']<end-seconds): break
        r=next((r for r in s['data']['readings'] if r['id']==field and r['unit']==unit),None)
        points.append((s['time'],r['value'] if r and valid(r) else None,s['gap']))
    return list(reversed(points)),unit


class MiniChart(tk.Frame):
    def __init__(self,parent,history,open_history):
        super().__init__(parent,bg=BG,width=380,height=230)
        self.history=history
        self.open_history=open_history
        self.connected=False
        self.version=0
        self.pending=None
        self.image=None
        self.worker=None
        self.closed=False
        self.viewport=TimeViewport()
        self.bounds=None
        self.hover_position=None
        self.drag_origin=None
        self.scope=None
        self.hit_points=[]
        self.auto=tk.BooleanVar(value=True)
        try: self.worker=AsyncTraceRenderer(TraceRenderer())
        except (OSError,AttributeError): pass
        self.field=tk.StringVar(value='LIVE')
        header=tk.Frame(self,bg=BG)
        header.pack(fill='x',padx=12,pady=(12,2))
        tk.Label(header,text='WYKRES NA ŻYWO',bg=BG,fg=MUTED,font=('DejaVu Sans',8,'bold')).pack(side='left')
        self.choice=ttk.Combobox(header,textvariable=self.field,values=['LIVE'],state='readonly',width=12)
        self.choice.pack(side='right')
        self.choice.bind('<<ComboboxSelected>>',lambda e:self.request_draw())
        tk.Checkbutton(header,text='AUTO • blokada',variable=self.auto,command=self.toggle_auto,
            bg=BG,fg=GREEN,selectcolor=BG,activebackground=BG,activeforeground=TEXT,
            font=('DejaVu Sans',8)).pack(side='right',padx=8)
        self.canvas=tk.Canvas(self,bg=BG,height=155,highlightthickness=0,cursor='hand2')
        self.canvas.pack(fill='both',expand=True,padx=10)
        self.canvas.bind('<Configure>',lambda e:self.request_draw())
        self.canvas.bind('<Double-Button-1>',lambda e:self.open_history())
        self.canvas.bind('<Button-4>',self.zoom)
        self.canvas.bind('<Button-5>',self.zoom)
        self.canvas.bind('<MouseWheel>',self.zoom)
        self.canvas.bind('<ButtonPress-1>',self.begin_drag)
        self.canvas.bind('<B1-Motion>',self.drag)
        self.canvas.bind('<ButtonRelease-1>',lambda e:setattr(self,'drag_origin',None))
        self.canvas.bind('<Motion>',self.hover)
        self.canvas.bind('<Leave>',self.leave)
        self.caption=tk.Label(self,text='AUTO: ostatnia minuta • dwuklik: pełny wykres',bg=BG,fg=MUTED,font=('DejaVu Sans',8),anchor='w')
        self.caption.pack(fill='x',padx=12,pady=(2,12))
        self.bind('<Destroy>',self.close,add='+')
        self.after(50,self.poll)

    def toggle_auto(self):
        self.drag_origin=None
        if self.auto.get():
            self.viewport.reset()
        elif self.bounds:
            self.viewport.selection=self.bounds[4:6]
        self.request_draw()

    def zoom(self,event):
        if self.auto.get() or not self.bounds: return 'break'
        left,right,top,bottom,start,end,*_=self.bounds
        if not (left<=event.x<=right and top<=event.y<=bottom): return 'break'
        number=getattr(event,'num',None); delta=getattr(event,'delta',0)
        if number not in (4,5) and not delta: return 'break'
        factor=.8 if number==4 or (number!=5 and delta>0) else 1.25
        self.viewport.zoom(self.viewport.selection or (start,end),(event.x-left)/(right-left),factor)
        self.request_draw()
        return 'break'

    def begin_drag(self,event):
        if self.auto.get() or not self.bounds: return
        left,right,top,bottom,start,end,*_=self.bounds
        if left<=event.x<=right and top<=event.y<=bottom:
            self.drag_origin=(event.x,(start,end),right-left)
            self.leave()

    def drag(self,event):
        if self.auto.get() or not self.drag_origin: return
        x,initial,width=self.drag_origin
        self.viewport.pan(initial,(x-event.x)/width*(initial[1]-initial[0]))
        self.request_draw()
        return 'break'

    def leave(self,event=None):
        self.hover_position=None
        self.canvas.delete('cursor')

    def hover(self,event):
        self.hover_position=(event.x,event.y)
        c=self.canvas; c.delete('cursor')
        if not self.bounds or not self.hit_points: return
        left,right,top,bottom,start,end,low,high,scale,symbol=self.bounds
        if not (left<=event.x<=right and top<=event.y<=bottom): return
        time_at_cursor=start+(event.x-left)/(right-left)*(end-start)
        t,value,gap=min(self.hit_points,key=lambda point:abs(point[0]-time_at_cursor))
        x=left+(t-start)/(end-start)*(right-left)
        c.create_line(x,top,x,bottom,fill=GREEN,dash=(4,4),tags='cursor')
        if value is not None:
            y=bottom-(value-low)/(high-low)*(bottom-top)
            c.create_line(left,y,right,y,fill=GREEN,dash=(4,4),tags='cursor')
            c.create_oval(x-4,y-4,x+4,y+4,fill=BG,outline=GREEN,width=2,tags='cursor')
            record=getattr(self,'hit_readings',{}).get(t)
            reading=format_reading(record) if record else 'Format próbki niedostępny'
        else:
            record=getattr(self,'hit_readings',{}).get(t)
            reading=format_reading(record) if record else 'Brak poprawnego odczytu'
        label=self.field.get()+' • '+reading+'\n'+datetime.fromtimestamp(t).strftime('%H:%M:%S.%f')[:-3]
        item=c.create_text(0,0,text=label,fill=TEXT,anchor='nw',font=('DejaVu Sans',9),width=230,tags='cursor')
        box=c.bbox(item)
        if not box: return
        w,h=box[2]-box[0]+20,box[3]-box[1]+16
        tx=max(left+2,min(event.x+14,right-w)); ty=max(top+2,min(event.y+14,bottom-h))
        c.coords(item,tx+10,ty+8)
        rect=c.create_rectangle(tx,ty,tx+w,ty+h,fill='#10151d',outline=GREEN,tags='cursor')
        c.tag_lower(rect,item)

    def close(self,event):
        if event.widget is not self: return
        self.closed=True
        if self.worker: self.worker.close()

    def update_data(self,connected):
        self.connected=connected
        if self.history.samples:
            ids=[r['id'] for r in self.history.samples[-1]['data']['readings']]
            self.choice['values']=ids
            if self.field.get() not in ids:
                self.field.set('LIVE' if 'LIVE' in ids else ('PRIMARY' if 'PRIMARY' in ids else (ids[0] if ids else '')))
        self.request_draw()

    def request_draw(self):
        if self.pending is None and not self.closed:
            self.pending=self.after(30,self.draw)

    def draw(self):
        self.pending=None
        if self.closed: return
        self.version+=1
        self.canvas.delete('all')
        self.image=None
        self.bounds=None
        self.hit_points=[]
        width,height=max(self.canvas.winfo_width(),240),max(self.canvas.winfo_height(),130)
        if not self.connected:
            self.canvas.create_text(width/2,height/2,text='Oczekiwanie na aktualne pomiary',fill=MUTED)
            return
        full,unit=preview_samples(self.history,self.field.get(),seconds=None)
        if not full: return
        scope=(self.history.samples[-1]['segment'],self.field.get(),unit)
        if scope!=self.scope:
            self.scope=scope
            self.viewport.reset()
        self.viewport.update_domain(full[0][0],full[-1][0])
        if self.auto.get():
            start=max(full[0][0],full[-1][0]-60); end=max(start+.001,full[-1][0])
        else:
            start,end=self.viewport.selection or (max(full[0][0],full[-1][0]-60),max(full[0][0]+.001,full[-1][0]))
            self.viewport.selection=self.viewport.clamp((start,end))
            start,end=self.viewport.selection
        points=[point for point in full if start<=point[0]<=end]
        values=[v for t,v,gap in points if v is not None]
        visible_values=values
        if not values: values=[v for t,v,gap in full if v is not None]
        if not values:
            self.canvas.create_text(width/2,height/2,text='Brak poprawnych wartości • OL / brak danych',fill=MUTED,width=width-30)
            return
        current=next(r for r in self.history.samples[-1]['data']['readings'] if r['id']==self.field.get() and r['unit']==unit)
        scale,symbol=meter_scale(current)
        low,high=min(values),max(values)
        pad=(high-low)*.12 or max(abs(low)*.01,1e-12)
        low-=pad; high+=pad
        left,right,top,bottom=80,width-12,22,height-24
        self.bounds=(left,right,top,bottom,start,end,low,high,scale,symbol)
        self.hit_points=points
        self.hit_readings={sample['time']:r for sample in self.history.samples
            if sample['segment']==self.history.samples[-1]['segment'] and start<=sample['time']<=end
            for r in sample['data']['readings'] if r['id']==self.field.get() and r['unit']==unit}
        self.caption.config(text='AUTO • mysz zablokowana • ostatnia minuta • dwuklik: historia' if self.auto.get() else 'RĘCZNIE • kółko: zoom • przeciągnij: przesuń • dwuklik: historia')
        if not visible_values:
            self.canvas.create_text((left+right)/2,(top+bottom)/2,text='Brak poprawnych próbek w tym fragmencie',fill=MUTED)
        self.canvas.create_text(left,6,text='Wartość ['+symbol+']',fill=MUTED,anchor='w',font=('DejaVu Sans',8))
        for ratio in [0,.5,1]:
            y=bottom-ratio*(bottom-top)
            self.canvas.create_line(left,y,right,y,fill='#293344')
            self.canvas.create_text(left-8,y,text=decimal_text((low+ratio*(high-low))/scale,4),fill=MUTED,anchor='e',font=('DejaVu Sans',8))
        self.canvas.create_text(left,bottom+13,text=datetime.fromtimestamp(start).strftime('%H:%M:%S'),fill=MUTED,anchor='w',font=('DejaVu Sans',8))
        self.canvas.create_text(right,bottom+13,text=datetime.fromtimestamp(end).strftime('%H:%M:%S'),fill=MUTED,anchor='e',font=('DejaVu Sans',8))
        paths=[]; coords=[]; last=None
        for t,value,gap in points:
            if gap or value is None:
                if len(coords)>=4: paths.append((coords,GREEN))
                coords=[]
            if value is None: continue
            x=left+(t-start)/(end-start)*(right-left)
            y=bottom-(value-low)/(high-low)*(bottom-top)
            coords.extend((x,y)); last=(x,y)
        if len(coords)>=4: paths.append((coords,GREEN))
        for path,color in paths:
            self.canvas.create_line(*path,fill=color,width=2,capstyle='round',joinstyle='round',tags='trace')
        dots=[(*last,GREEN)] if last else []
        if last: self.canvas.create_oval(last[0]-3,last[1]-3,last[0]+3,last[1]+3,fill=GREEN,outline='',tags='trace')
        if self.worker: self.worker.submit(self.version,int(width),int(height),paths,dots)
        if self.hover_position:
            self.hover(SimpleNamespace(x=self.hover_position[0],y=self.hover_position[1]))

    def poll(self):
        if self.closed: return
        if self.worker:
            try:
                version,png,error=self.worker.results.get_nowait()
                if error:
                    self.worker.close(); self.worker=None
                elif version==self.version:
                    try:
                        im=tk.PhotoImage(master=self,data=base64.b64encode(png),format='png')
                        self.canvas.delete('trace'); self.image=im
                        self.canvas.create_image(0,0,image=im,anchor='nw',tags='trace')
                        self.canvas.tag_raise('cursor')
                    except tk.TclError:
                        self.worker.close(); self.worker=None
            except queue.Empty: pass
        self.after(50,self.poll)
