# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Piotr
# This program comes with NO WARRANTY; see COPYING for license terms.
import math
import queue
import base64
from types import SimpleNamespace
from datetime import datetime, timezone
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from .history import valid
from .point_navigation import step_point,elapsed_text
from .viewport import TimeViewport
from .markers import Markers
from .display import format_reading, reading_parts, meter_scale
from .trace_renderer import TraceRenderer, AsyncTraceRenderer

BG, CARD, TEXT, MUTED = '#10151d', '#1a2230', '#edf2f7', '#9aaac0'
COLORS = ['#65dbb2', '#f6c744', '#72b7ff', '#f58baf', '#bd9aff', '#ffa56b']
LABELS = {'LIVE':'Aktualny (LIVE)', 'PRIMARY':'Główny (PRIMARY)', 'MINIMUM':'Minimum z Fluke',
          'MAXIMUM':'Maksimum z Fluke', 'AVERAGE':'Średnia z Fluke', 'SECONDARY':'Dodatkowy',
          'REL_LIVE':'Bieżący REL', 'REL_REFERENCE':'Odniesienie REL'}
UNITS = {'OHM':'Ω', 'SIE':'S', 'CEL':'°C', 'FAR':'°F', 'PCT':'%'}

def axis_scale(values, unit):
    """One engineering prefix for the whole axis; stored values stay in base units."""
    scalable = {'OHM', 'SIE', 'F', 'S', 'Hz', 'V', 'VDC', 'VAC', 'VAC_PLUS_DC',
                'A', 'ADC', 'AAC', 'AAC_PLUS_DC'}
    peak = max((abs(v) for v in values), default=0)
    exponent = max(-12, min(12, 3*math.floor(math.log10(peak)/3))) if peak and unit in scalable else 0
    prefix = {-12:'p', -9:'n', -6:'µ', -3:'m', 0:'', 3:'k', 6:'M', 9:'G', 12:'T'}[exponent]
    symbol = {'VDC':'V DC', 'VAC':'V AC', 'VAC_PLUS_DC':'V AC+DC',
              'ADC':'A DC', 'AAC':'A AC', 'AAC_PLUS_DC':'A AC+DC'}.get(unit, UNITS.get(unit, unit))
    return 10.0**exponent, prefix+symbol


def decimal_text(value, decimals=6):
    if 0 < abs(value) < 1:
        decimals = max(decimals, min(15, math.ceil(-math.log10(abs(value)))+4))
    text = f'{value:.{decimals}f}'.rstrip('0').rstrip('.') if decimals else f'{value:.0f}'
    if text == '-0': text = '0'
    return text.replace('.', ',')


def axis_ticks(low, high, scale):
    rough = (high-low)/4
    power = 10**math.floor(math.log10(rough))
    step = next(n*power for n in (1, 2, 2.5, 5, 10) if n*power >= rough)
    first = math.ceil(low/step)*step
    decimals = max(0, min(12, math.ceil(-math.log10(step/scale))+1))
    return [(first+i*step, decimal_text((first+i*step)/scale, decimals))
            for i in range(8) if first+i*step <= high+step*1e-8]


class HistoryWindow:
    def __init__(self, parent, history, title='Historia na żywo • pamięć programu', live=True):
        self.history = history
        self.time_source=getattr(history,'time_source','computer')
        self.live = live
        self.revision = -1
        self.selected_segment = None
        self.series_vars = {}
        self.viewport = TimeViewport()
        self.markers = Markers()
        self.marker_drag = None
        self.drag_state = None
        try: self.trace_renderer = TraceRenderer()
        except (OSError, AttributeError): self.trace_renderer = None
        self.trace_image = None
        self.aa_worker = AsyncTraceRenderer(self.trace_renderer) if self.trace_renderer else None
        self.frame_version = 0
        self.draw_pending = None
        self.window = tk.Toplevel(parent, bg=BG)
        self.window.title(title)
        self.window.geometry('1180x850')
        self.window.minsize(980,740)
        self.window.protocol('WM_DELETE_WINDOW', self.close)
        self.window.bind('<Escape>',self.cancel_marker)
        self.closed = False
        self.segment_var = tk.StringVar()
        self.unit_var = tk.StringVar()
        self.span = tk.StringVar(value='Cała seria')
        self.follow = tk.BooleanVar(value=live)
        self.summary = tk.StringVar(value='Oczekiwanie na próbki…')
        self.note = tk.StringVar(value='')
        self.elapsed_var=tk.BooleanVar(value=False)
        self.point_cursor=None
        self.marker_field = tk.StringVar(value='LIVE')
        self.marker_summary = tk.StringVar(value='A/B: wybierz odczyt, kliknij Ustaw A i wskaż próbkę na wykresie.')
        description=getattr(history,'comparison_description','')
        if description:
            tk.Label(self.window,text=description,bg=BG,fg=TEXT,justify='left',anchor='w',wraplength=1100).pack(fill='x',padx=20,pady=(10,0))
        body = tk.Frame(self.window,bg=BG)
        body.pack(fill='both',expand=True,padx=22,pady=18)
        tk.Label(body,text='Historia i wykres',bg=BG,fg=TEXT,font=('DejaVu Sans',20,'bold')).pack(anchor='w')
        tk.Label(body,text='Wybierz funkcję, jednostkę i pola przesyłane przez miernik.',bg=BG,fg=MUTED).pack(anchor='w',pady=(4,14))
        controls = tk.Frame(body,bg=BG)
        controls.pack(fill='x')
        self.segment_box=ttk.Combobox(controls,textvariable=self.segment_var,state='readonly',width=48)
        self.segment_box.pack(side='left',fill='x',expand=True)
        self.segment_box.bind('<<ComboboxSelected>>',self.change_segment)
        self.unit_box=ttk.Combobox(controls,textvariable=self.unit_var,state='readonly',width=10)
        self.unit_box.pack(side='left',padx=8)
        self.unit_box.bind('<<ComboboxSelected>>',lambda e:self.rebuild_series())
        span=ttk.Combobox(controls,textvariable=self.span,state='readonly',values=['Cała seria','Ostatnia minuta','Ostatnie 5 minut'],width=19)
        span.pack(side='left')
        span.bind('<<ComboboxSelected>>',self.change_span)
        ttk.Button(controls,text='Cały przebieg',command=self.reset_view).pack(side='left',padx=(8,0))
        navigation=tk.Frame(body,bg=BG);navigation.pack(fill='x',pady=(8,0))
        ttk.Checkbutton(navigation,text='Czas od początku nagrania',variable=self.elapsed_var,command=self.draw).pack(side='left',padx=(0,14))
        ttk.Button(navigation,text='◀ Poprzedni punkt',command=lambda:self.navigate_point(-1)).pack(side='left')
        ttk.Button(navigation,text='Następny punkt ▶',command=lambda:self.navigate_point(1)).pack(side='left',padx=8)
        tk.Label(navigation,text='Punkty pola wybranego w liście A/B poniżej',bg=BG,fg=MUTED).pack(side='left',padx=8)
        if live:
            tk.Checkbutton(body,text='Śledź aktualną funkcję miernika',variable=self.follow,
                bg=BG,fg=MUTED,selectcolor=CARD,activebackground=BG,activeforeground=TEXT,
                command=self.refresh).pack(anchor='w',pady=6)
        self.series_frame=tk.Frame(body,bg=BG)
        self.series_frame.pack(fill='x',pady=10)
        marker_bar=tk.Frame(body,bg=BG)
        marker_bar.pack(fill='x',pady=(0,8))
        tk.Label(marker_bar,text='PORÓWNANIE A/B',bg=BG,fg=MUTED,font=('DejaVu Sans',9,'bold')).pack(side='left',padx=(0,12))
        self.marker_box=ttk.Combobox(marker_bar,textvariable=self.marker_field,state='readonly',width=16)
        self.marker_box.pack(side='left',padx=(0,8))
        self.marker_box.bind('<<ComboboxSelected>>',self.change_marker_field)
        ttk.Button(marker_bar,text='Ustaw A',command=lambda:self.arm_marker('A')).pack(side='left',padx=4)
        ttk.Button(marker_bar,text='Ustaw B',command=lambda:self.arm_marker('B')).pack(side='left',padx=4)
        ttk.Button(marker_bar,text='Wyczyść A/B',command=self.clear_markers).pack(side='left',padx=4)
        self.canvas=tk.Canvas(body,bg=CARD,highlightthickness=0,height=300)
        self.canvas.pack(fill='both',expand=True)
        self.canvas.bind('<Configure>',lambda e:self.request_draw())
        self.canvas.bind('<Motion>',self.hover)
        self.canvas.bind('<Left>',lambda e:self.navigate_point(-1))
        self.canvas.bind('<Right>',lambda e:self.navigate_point(1))
        self.canvas.bind('<Button-4>',self.wheel_zoom)
        self.canvas.bind('<Button-5>',self.wheel_zoom)
        self.canvas.bind('<MouseWheel>',self.wheel_zoom)
        self.canvas.bind('<ButtonPress-1>',self.begin_pan)
        self.canvas.bind('<B1-Motion>',self.drag_pan)
        self.canvas.bind('<ButtonRelease-1>',self.end_pan)
        self.canvas.bind('<Double-Button-1>',lambda e:self.reset_view())
        self.hover_position = None
        self.canvas.bind('<Leave>',self.hide_hover)
        tk.Label(body,textvariable=self.marker_summary,bg=BG,fg='#f6c744',anchor='w',justify='left',wraplength=1040).pack(fill='x',pady=(10,0))
        tk.Label(body,textvariable=self.summary,bg=BG,fg=TEXT,anchor='w',justify='left',wraplength=1040).pack(fill='x',pady=10)
        stats=getattr(history,'comparison_stats',None)
        self.show_worst_pair=False
        if stats is not None:
            if stats['count']:
                unit=self.history.samples[0]['data']['readings'][0]['unit']
                low,high=stats['overlap']
                text=f"Cały wspólny okres: {self.time_text(low)} – {self.time_text(high)} · {stats['count']} par · {stats['equal']} identycznych na wspólnej rozdzielczości\nŚrednia |B−A|: {stats['mean']:.6g} {unit} · największa: {stats['maximum']:.6g} {unit} · maks. odstęp czasu: {stats['max_dt']:.3f} s · limit: {stats['tolerance']:g} s"
            else:
                text='Brak dopasowanych par w zadanym limicie czasu.'
            tk.Label(body,text=text+'\nZgodność zapisów, nie dokładność ani kalibracja miernika. Punkty dopasowane najbliższym czasem, bez interpolacji i bez ponownego użycia punktu.',bg=BG,fg=TEXT,justify='left',anchor='w',wraplength=1080).pack(fill='x',pady=(0,6))
            report_bar=tk.Frame(body,bg=BG);report_bar.pack(fill='x',pady=(0,6))
            ttk.Button(report_bar,text='Pokaż parę z największą różnicą',command=self.show_comparison_worst,state='normal' if stats['count'] else 'disabled').pack(side='left')
            export_button=ttk.Menubutton(report_bar,text='Eksportuj raport…');export_button.pack(side='left',padx=10)
            export_menu=tk.Menu(export_button,tearoff=False)
            export_menu.add_command(label='PDF - wykres i podsumowanie',command=lambda:self.export_comparison('pdf'))
            export_menu.add_command(label='CSV - dopasowane pary',command=lambda:self.export_comparison('csv'))
            export_button.configure(menu=export_menu)
        self.table=ttk.Treeview(body,columns=('time','field','value','unit','state'),show='headings',height=5)
        for name,label,width in [('time','Czas odczytu',180),('field','Pole Fluke',140),('value','Wartość',170),('unit','Jednostka',90),('state','Stan / atrybut',260)]:
            self.table.heading(name,text=label,anchor='w')
            self.table.column(name,width=width,anchor='w')
        self.table.pack(fill='x')
        tk.Label(body,textvariable=self.note,bg=BG,fg=MUTED,anchor='w',justify='left',wraplength=1040).pack(fill='x',pady=(8,0))
        self.points=[]
        self.refresh()
        self.window.after(40,self.poll_render)
        self.window.after(500,self.tick)

    def elapsed_origin(self):
        samples=[s for s in self.history.samples if s['segment']==self.selected_segment]
        if not samples:return 0.
        first=getattr(self.history,'segment_starts',{}).get(self.selected_segment,min(s['time'] for s in samples))
        if getattr(self,'time_source','computer')=='meter':
            start=samples[0]['data'].get('minmax_start',0)
            if 0<start<=first:return start
        return first

    def time_text(self,stamp,milliseconds=True):
        if getattr(getattr(self,'history',None),'comparison_relative',False):
            return elapsed_text(stamp,milliseconds)
        option=getattr(self,'elapsed_var',None)
        if option is not None and option.get():return elapsed_text(stamp-self.elapsed_origin(),milliseconds)
        text=self.clock(stamp).strftime('%H:%M:%S.%f' if milliseconds else '%H:%M:%S')
        return text[:-3] if milliseconds else text

    def update_point_table(self,sample):
        self.table.delete(*self.table.get_children())
        unit=self.unit_var.get()
        for r in sample['data']['readings']:
            if r['unit']==unit:
                self.table.insert('','end',values=(self.time_text(sample['time']),r['id'],*reading_parts(r),r['state']+' / '+r['attribute']))

    def navigate_point(self,direction):
        field=self.marker_field.get()
        if field not in self.series_vars:return
        self.follow.set(False);self.series_vars[field].set(True)
        points=[(s['time'],s,r) for s,rs in self.history.view(self.selected_segment,self.unit_var.get()) for r in rs if r['id']==field and valid(r)]
        cursor=getattr(self,'point_cursor',None)
        target=step_point(points,cursor[0] if cursor and cursor[1]==field else None,direction)
        if target is None:return
        t,s,r=target;self.point_cursor=(t,field);self.hover_position=None
        if self.bounds:
            xmin,xmax=self.bounds[4:6]
            if not xmin<=t<=xmax:
                width=xmax-xmin;self.viewport.selection=self.viewport.clamp((t-width/2,t+width/2));self.span.set('Wybrany fragment')
        self.draw()
        self.canvas.focus_set()
        return 'break'

    def clock(self, timestamp):
        return datetime.fromtimestamp(timestamp,timezone.utc if getattr(self,'time_source','computer')=='meter' else None)

    def close(self):
        self.closed=True
        if self.aa_worker: self.aa_worker.close()
        self.window.destroy()

    def tick(self):
        if self.closed: return
        if self.revision != self.history.revision: self.refresh()
        self.window.after(500,self.tick)

    def refresh(self):
        self.revision=self.history.revision
        segments=self.history.segments()
        self.keys=list(segments)
        names=[]
        for key,s in segments.items():
            d=s['data']
            names.append(f"{key}. {d['primary']} / {d['secondary']} · {', '.join(d['modes']) or 'podstawowy'}")
        self.segment_box['values']=names
        if not self.keys:
            self.draw()
            return
        if self.follow.get() or self.selected_segment not in self.keys:
            target=self.keys[-1]
        else: target=self.selected_segment
        changed=target != self.selected_segment
        self.selected_segment=target
        self.segment_box.current(self.keys.index(target))
        units=set(r['unit'] for sample in self.history.samples if sample['segment']==target for r in sample['data']['readings'])
        if changed:
            self.point_cursor=None;self.hide_hover()
            self.viewport.reset()
            self.drag_state=None
        if changed or units != set(self.unit_box['values']): self.rebuild_units()
        else:
            available={r['id'] for s,rs in self.history.view(target,self.unit_var.get()) for r in rs}
            if available != set(self.series_vars): self.rebuild_series()
            else: self.draw()

    def change_segment(self,event=None):
        self.follow.set(False)
        index=self.segment_box.current()
        if index>=0:
            self.selected_segment=self.keys[index]
            self.viewport.reset()
            self.drag_state=None
            self.rebuild_units()

    def rebuild_units(self):
        self.point_cursor=None;self.hide_hover()
        units=list(dict.fromkeys(r['unit'] for s in self.history.samples if s['segment']==self.selected_segment for r in s['data']['readings']))
        self.unit_box['values']=units
        if self.unit_var.get() not in units: self.unit_var.set(units[0] if units else '')
        self.rebuild_series()

    def rebuild_series(self):
        self.point_cursor=None;self.hide_hover()
        old={key:v.get() for key,v in self.series_vars.items()}
        for widget in self.series_frame.winfo_children(): widget.destroy()
        ids=list(dict.fromkeys(r['id'] for s,rs in self.history.view(self.selected_segment,self.unit_var.get()) for r in rs))
        if getattr(self.history,'comparison_description',''):ids.sort()
        self.series_vars={}
        for i,key in enumerate(ids):
            var=tk.BooleanVar(value=old.get(key,(key in {'LIVE','PRIMARY','MINIMUM','MAXIMUM','AVERAGE'} or key.startswith(('A · ','B · ')))))
            self.series_vars[key]=var
            tk.Checkbutton(self.series_frame,text=LABELS.get(key,key),variable=var,command=self.draw,
                bg=BG,fg=COLORS[i%len(COLORS)],selectcolor=CARD,activebackground=BG,
                activeforeground=TEXT).grid(row=i//5,column=i%5,sticky='w',padx=(0,12))
        self.sync_marker_fields(ids)
        self.draw()

    def sync_marker_fields(self, ids):
        self.marker_box['values']=ids
        if self.marker_field.get() not in ids:
            self.marker_field.set('LIVE' if 'LIVE' in ids else (ids[0] if ids else ''))
        self.markers.set_scope(self.selected_segment,self.marker_field.get(),self.unit_var.get())
        self.marker_drag=None

    def change_marker_field(self,event=None):
        self.markers.set_scope(self.selected_segment,self.marker_field.get(),self.unit_var.get())
        self.marker_drag=None
        self.draw()

    def arm_marker(self,name):
        field=self.marker_field.get()
        if field not in self.series_vars:
            self.marker_summary.set('Brak pola odczytu do porównania. Poczekaj na dane miernika.')
            return
        self.markers.set_scope(self.selected_segment,field,self.unit_var.get())
        self.markers.pending=name
        self.series_vars[field].set(True)
        self.canvas.configure(cursor='crosshair')
        self.draw()

    def clear_markers(self):
        self.markers.clear()
        self.marker_drag=None
        self.canvas.configure(cursor='')
        self.draw()

    def pick_marker(self,name,event):
        candidates=[point for point in self.points if point[3]['id']==self.marker_field.get()]
        if not candidates: return
        x,y,s,r,color=min(candidates,key=lambda p:abs(p[0]-event.x))
        self.markers.set_point(name,s,r)
        self.draw()

    def export_comparison(self,kind):
        from .comparison_report import export_pdf,export_csv
        path=filedialog.asksaveasfilename(parent=self.window,title='Eksportuj porównanie - '+kind.upper(),initialfile='porownanie.'+kind,defaultextension='.'+kind,filetypes=[(kind.upper(),'*.'+kind)])
        if not path:return
        if not path.lower().endswith('.'+kind):
            messagebox.showerror('Eksport raportu','Wybierz rozszerzenie .'+kind,parent=self.window);return
        try:
            (export_pdf if kind=='pdf' else export_csv)(self.history,path)
        except Exception as error:
            messagebox.showerror('Eksport raportu','Nie zapisano raportu: '+str(error),parent=self.window)
            return
        messagebox.showinfo('Eksport raportu','Zapisano raport:\n'+path,parent=self.window)

    def show_comparison_worst(self):
        pair=self.history.comparison_stats['worst']
        if not pair:return
        self.show_worst_pair=True
        for var in self.series_vars.values():var.set(True)
        low=min(pair['a'][0],pair['b'][0]);high=max(pair['a'][0],pair['b'][0])
        padding=max(1.,(high-low)*3)
        self.viewport.selection=(low-padding,high+padding)
        self.span.set('Wybrany fragment');self.draw()

    def draw_comparison_worst(self):
        if not getattr(self,'show_worst_pair',False) or not self.bounds:return
        pair=self.history.comparison_stats['worst']
        left,right,top,bottom,xmin,xmax,ymin,ymax=self.bounds
        for label,key,color in [('A','a',COLORS[0]),('B','b',COLORS[1])]:
            t,r=pair[key]
            if not xmin<=t<=xmax:continue
            x=left+(t-xmin)/(xmax-xmin)*(right-left);y=bottom-(r['value']-ymin)/(ymax-ymin)*(bottom-top)
            self.canvas.create_line(x,top,x,bottom,fill=color,dash=(3,3),tags='markers')
            self.canvas.create_oval(x-6,y-6,x+6,y+6,outline=color,width=2,tags='markers')
            self.canvas.create_text(left+10,top+15+(0 if label=='A' else 22),anchor='w',text=f'{label}: {self.time_text(t)} · {format_reading(r)}',fill=color,tags='markers')

    def draw_markers(self):
        if not hasattr(self,'markers'): return
        self.canvas.delete('markers')
        self.draw_comparison_worst()
        parts=[]
        scale=getattr(self,'display_scale',1.)
        unit=getattr(self,'display_unit',UNITS.get(self.unit_var.get(),self.unit_var.get()))
        for name,point in self.markers.points.items():
            stamp=self.time_text(point.time)
            parts.append(f'{name}: {stamp} · {format_reading(point.reading) if point.reading else decimal_text(point.value/scale)+" "+unit}')
            if not self.bounds: continue
            left,right,top,bottom,xmin,xmax,ymin,ymax=self.bounds
            if not xmin<=point.time<=xmax: continue
            x=left+(point.time-xmin)/(xmax-xmin)*(right-left)
            y=bottom-(point.value-ymin)/(ymax-ymin)*(bottom-top)
            color='#f6c744' if name=='A' else '#72b7ff'
            self.canvas.create_line(x,top,x,bottom,fill=color,width=1.5,dash=(6,4),tags='markers')
            self.canvas.create_text(x+7 if x<right-25 else x-7,top+12 if name=='A' else top+32,
                text=name,fill=color,anchor='w' if x<right-25 else 'e',font=('DejaVu Sans',11,'bold'),tags='markers')
            if top<=y<=bottom:
                self.canvas.create_oval(x-6,y-6,x+6,y+6,fill=CARD,outline=color,width=2,tags='markers')
        difference=self.markers.difference()
        if difference:
            dt,dv=difference
            delta=decimal_text(dv/scale)
            if dv>0: delta='+'+delta
            parts.append(f'Δt (B − A): {decimal_text(dt,3)} s   |   Δ (B − A): {delta} {unit}')
        if self.markers.pending:
            parts.append('Wskaż próbkę dla '+self.markers.pending+' • Esc anuluje wybór')
        elif not parts:
            parts.append('A/B: wybierz odczyt, kliknij Ustaw A lub Ustaw B i wskaż próbkę. Znaczniki możesz przeciągać.')
        self.marker_summary.set('   |   '.join(parts))

    def cancel_marker(self,event=None):
        self.markers.pending=None
        self.marker_drag=None
        self.canvas.configure(cursor='')
        self.draw_markers()

    def request_draw(self):
        # Merge bursts of wheel, drag and resize events into one frame.
        if getattr(self,'draw_pending',None) is None:
            self.draw_pending=self.canvas.after(16,self.flush_draw)

    def flush_draw(self):
        self.draw_pending=None
        if not self.closed: self.draw()

    def poll_render(self):
        if self.closed: return
        worker=self.aa_worker
        if worker:
            try:
                version,png,error=worker.results.get_nowait()
                if error:
                    worker.close()
                    self.aa_worker=None
                    self.trace_renderer=None
                elif version==self.frame_version:
                    try:
                        image=tk.PhotoImage(master=self.window,data=base64.b64encode(png),format='png')
                        self.canvas.delete('trace')
                        self.trace_image=image
                        self.canvas.create_image(0,0,image=image,anchor='nw',tags='trace')
                        self.canvas.tag_raise('markers')
                        self.canvas.tag_raise('cursor')
                    except tk.TclError:
                        # Keep the already drawn vector frame on image failure.
                        worker.close()
                        self.aa_worker=None
                        self.trace_renderer=None
            except queue.Empty: pass
        self.window.after(40,self.poll_render)

    def change_span(self,event=None):
        self.viewport.reset()
        self.drag_state=None
        self.draw()

    def reset_view(self):
        self.viewport.reset()
        self.drag_state=None
        self.span.set('Cała seria')
        self.hide_hover()
        self.canvas.configure(cursor='')
        self.draw()

    def wheel_zoom(self,event):
        if not getattr(self,'bounds',None): return 'break'
        left,right,top,bottom,xmin,xmax,*_=self.bounds
        if not (left<=event.x<=right and top<=event.y<=bottom): return 'break'
        number=getattr(event,'num',None)
        delta=getattr(event,'delta',0)
        if number not in (4,5) and not delta: return 'break'
        factor=.8 if number==4 or (number!=5 and delta>0) else 1.25
        self.viewport.zoom(self.viewport.selection or (xmin,xmax),(event.x-left)/(right-left),factor)
        self.follow.set(False)
        self.span.set('Wybrany fragment')
        self.hide_hover()
        self.request_draw()
        return 'break'

    def begin_pan(self,event):
        if not getattr(self,'bounds',None): return
        left,right,top,bottom,xmin,xmax,*_=self.bounds
        if left<=event.x<=right and top<=event.y<=bottom:
            if hasattr(self,'markers'):
                self.canvas.focus_set()
                if self.markers.pending:
                    self.pick_marker(self.markers.pending,event)
                    self.canvas.configure(cursor='')
                    return 'break'
                near=[(abs(left+(point.time-xmin)/(xmax-xmin)*(right-left)-event.x),name)
                      for name,point in self.markers.points.items() if xmin<=point.time<=xmax]
                if near and min(near)[0]<=9:
                    self.marker_drag=min(near)[1]
                    self.canvas.configure(cursor='crosshair')
                    return 'break'
            self.drag_state=(event.x,(xmin,xmax),right-left)
            self.canvas.configure(cursor='fleur')
            self.hide_hover()

    def drag_pan(self,event):
        if getattr(self,'marker_drag',None):
            self.pick_marker(self.marker_drag,event)
            return 'break'
        if self.drag_state is None: return
        x,initial,pixels=self.drag_state
        if abs(event.x-x)<3: return
        self.viewport.pan(initial,(x-event.x)/pixels*(initial[1]-initial[0]))
        self.follow.set(False)
        self.span.set('Wybrany fragment')
        self.request_draw()
        return 'break'

    def end_pan(self,event):
        self.marker_drag=None
        self.drag_state=None
        self.canvas.configure(cursor='')
        self.hover(event)

    def draw(self):
        c=self.canvas
        self.frame_version=getattr(self,'frame_version',0)+1
        c.delete('all')
        self.trace_paths=[]
        self.trace_dots=[]
        self.trace_image=None
        self.points=[]
        self.table.delete(*self.table.get_children())
        if not hasattr(self,'viewport'): self.viewport=TimeViewport()
        self.bounds=None
        full_view=self.history.view(self.selected_segment,self.unit_var.get())
        view=full_view
        if full_view:
            self.viewport.update_domain(full_view[0][0]['time'],full_view[-1][0]['time'])
        if full_view and self.viewport.selection is not None:
            xmin,xmax=self.viewport.selection
            view=[item for item in full_view if xmin<=item[0]['time']<=xmax]
        elif view and self.span.get() in ('Ostatnia minuta','Ostatnie 5 minut'):
            seconds=60 if self.span.get()=='Ostatnia minuta' else 300
            end=view[-1][0]['time']
            view=[item for item in view if item[0]['time']>=end-seconds]
        ids=[key for key,var in self.series_vars.items() if var.get()]
        visible_vals=[r['value'] for s,rs in view for r in rs if r['id'] in ids and valid(r)]
        vals=visible_vals or [r['value'] for s,rs in full_view for r in rs if r['id'] in ids and valid(r)]
        self.note.set(f'{len(self.history.samples)} / {self.history.samples.maxlen} ostatnich próbek w pamięci. '+
            ('Historia ulotna — przetrwa zamknięcie tylko przy włączonym zapisie pliku. ' if self.live else 'Plik otwarto tylko do odczytu. ')+
            'MIN/MAX/AVG na wykresie pochodzą z Fluke; OL i braki przerywają linię.')
        width,height=max(c.winfo_width(),600),max(c.winfo_height(),200)
        left,right,top,bottom=124,width-38,44,height-76
        if not vals or not full_view:
            c.create_text(width/2,height/2,text='Brak poprawnych wartości dla wybranych pól',fill=MUTED)
            self.summary.set('Wybierz serię i pola z poprawnymi odczytami.')
            self.draw_markers()
            return
        if self.viewport.selection is None:
            xmin,xmax=view[0][0]['time'],view[-1][0]['time']
            xmax=max(xmin+.001,xmax)
        ymin,ymax=min(vals),max(vals)
        pad=(ymax-ymin)*.08 or max(abs(ymin)*.01,1e-12)
        ymin-=pad; ymax+=pad
        self.bounds=(left,right,top,bottom,xmin,xmax,ymin,ymax)
        format_records=[r for sample,rs in view for r in rs if r['id'] in ids]
        self.display_scale, unit = meter_scale(format_records[-1]) if format_records else axis_scale(vals,self.unit_var.get())
        self.display_unit = unit
        c.create_text(left,18,text='Wartość ['+unit+']',fill=TEXT,anchor='w',font=('DejaVu Sans',10,'bold'))
        c.create_line(left,top,left,bottom,right,bottom,fill='#71829b',width=1)
        for v,label in axis_ticks(ymin,ymax,self.display_scale):
            y=bottom-(v-ymin)/(ymax-ymin)*(bottom-top)
            c.create_line(left,y,right,y,fill='#293344')
            c.create_line(left-5,y,left,y,fill=MUTED)
            c.create_text(left-12,y,text=label,fill=TEXT,anchor='e',font=('DejaVu Sans',10))
        tick_count=max(2,min(7,int((right-left)/140)))
        for i in range(tick_count):
            x=left+(right-left)*i/(tick_count-1)
            t=xmin+(xmax-xmin)*i/(tick_count-1)
            c.create_line(x,top,x,bottom,fill='#222d3d')
            c.create_line(x,bottom,x,bottom+5,fill=MUTED)
            stamp=self.time_text(t,xmax-xmin<5)
            c.create_text(x,bottom+20,text=stamp,fill=TEXT,
                anchor='w' if i==0 else ('e' if i==tick_count-1 else 'center'),font=('DejaVu Sans',10))
        date=self.clock(xmin).strftime('%d.%m.%Y')
        caption='Czas od początku wybranej serii · z uwzględnieniem przesunięcia B' if getattr(getattr(self,'history',None),'comparison_relative',False) else 'Czas pomiaru · '+('zegar Fluke (UTC wg znacznika)' if getattr(self,'time_source','computer')=='meter' else 'zegar komputera')+' · '+date
        if getattr(self,'elapsed_var',None) is not None and self.elapsed_var.get() and not getattr(self.history,'comparison_relative',False):caption='Czas od początku nagrania · MM:SS / HH:MM:SS'
        c.create_text((left+right)/2,height-16,text=caption,fill=MUTED,font=('DejaVu Sans',10))
        for index,(key,var) in enumerate(self.series_vars.items()):
            if not var.get(): continue
            color=COLORS[index%len(COLORS)]
            coordinates=[]
            last=None
            for sample,rs in view:
                r=next((r for r in rs if r['id']==key),None)
                if not r and getattr(self,'time_source','computer')=='meter': continue
                if sample['gap'] or not r or not valid(r):
                    if len(coordinates)>=4: self.paint_trace(coordinates,color)
                    coordinates=[]
                if not r or not valid(r): continue
                x=left+(sample['time']-xmin)/(xmax-xmin)*(right-left)
                y=bottom-(r['value']-ymin)/(ymax-ymin)*(bottom-top)
                coordinates.extend((x,y))
                last=(x,y)
                self.points.append((x,y,sample,r,color))
            if len(coordinates)>=4: self.paint_trace(coordinates,color)
            if last:
                self.trace_dots.append((*last,color))
                c.create_oval(last[0]-3,last[1]-3,last[0]+3,last[1]+3,fill=color,outline='',tags='trace')
        if getattr(self,'aa_worker',None):
            self.aa_worker.submit(self.frame_version,int(width),int(height),self.trace_paths,self.trace_dots)
        last_s,last_rs=view[-1] if view else ({'time':0}, [])
        for r in last_rs:
            if r['id'] in ids:
                self.table.insert('','end',values=(self.time_text(last_s['time']),r['id'],*reading_parts(r),r['state']+' / '+r['attribute']))
        if visible_vals:
            records=[r for sample,rs in view for r in rs if r['id'] in ids and valid(r)]
            self.summary.set(f'Widoczne próbki: MIN {format_reading(min(records,key=lambda r:r["value"]))}   ·   MAX {format_reading(max(records,key=lambda r:r["value"]))}   |   Kółko: zoom · przeciągnij: przesuń · dwuklik: cały przebieg')
        else:
            self.summary.set('Brak poprawnych próbek w tym fragmencie. Oddal kółkiem lub kliknij „Cały przebieg”.')
        self.draw_markers()
        position=getattr(self,'hover_position',None)
        if position: self.hover(SimpleNamespace(x=position[0],y=position[1]))
        else:
            cursor=getattr(self,'point_cursor',None)
            selected=next((p for p in self.points if cursor and p[2]['time']==cursor[0] and p[3]['id']==cursor[1]),None)
            if selected:
                self.hover(SimpleNamespace(x=selected[0],y=selected[1]))
                self.hover_position=None

    def paint_trace(self, coordinates, color):
        self.trace_paths.append((coordinates,color))
        self.canvas.create_line(*coordinates,fill=color,width=2.4,capstyle='round',joinstyle='round',tags='trace')

    def hide_hover(self,event=None):
        self.hover_position=None
        self.canvas.delete('cursor')

    def hover(self,event):
        self.hover_position=(event.x,event.y)
        c=self.canvas
        c.delete('cursor')
        if not self.points: return
        preferred=self.marker_field.get() if hasattr(self,'marker_field') else None
        x,y,s,r,color=min(self.points,key=lambda p:((p[0]-event.x)**2+(p[1]-event.y)**2,p[3]['id']!=preferred))
        if (x-event.x)**2+(y-event.y)**2 > 24**2: return
        left,right,top,bottom,*_=self.bounds
        c.create_line(x,top,x,bottom,fill=color,dash=(4,4),tags='cursor')
        c.create_line(left,y,right,y,fill=color,dash=(4,4),tags='cursor')
        c.create_oval(x-5,y-5,x+5,y+5,fill=CARD,outline=color,width=2,tags='cursor')
        self.point_cursor=(s['time'],r['id'])
        if hasattr(self,'table'):self.update_point_table(s)
        value=format_reading(r)
        stamp=self.time_text(s['time'])
        # Identical overlapping readings share one tooltip, rather than hiding
        # the other series behind whichever point happened to be first.
        names=list(dict.fromkeys(LABELS.get(p[3]['id'],p[3]['id']) for p in self.points
            if abs(p[0]-x)<.1 and abs(p[1]-y)<.1))
        label=' / '.join(names)+'\n'+value+'\nCzas: '+stamp
        if getattr(self,'elapsed_var',None) is not None and self.elapsed_var.get() and not getattr(self.history,'comparison_relative',False):label+='\nGodzina: '+self.clock(s['time']).strftime('%H:%M:%S.%f')[:-3]
        tip=c.create_text(0,0,text=label,fill=TEXT,anchor='nw',width=300,
                          font=('DejaVu Sans',10),tags='cursor')
        box=c.bbox(tip)
        if not box: return
        tw,th=box[2]-box[0]+24,box[3]-box[1]+20
        tx=min(x+18,right-tw)
        ty=y-th-14 if y-th-14>=top else y+18
        tx=max(left+8,tx)
        ty=max(top+4,min(ty,bottom-th-4))
        c.coords(tip,tx+12,ty+10)
        rect=c.create_rectangle(tx,ty,tx+tw,ty+th,fill='#111a26',outline=color,width=1,tags='cursor')
        c.tag_lower(rect,tip)
