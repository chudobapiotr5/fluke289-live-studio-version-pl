# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Piotr
# This program comes with NO WARRANTY; see COPYING for license terms.
"""Range-based bar graph; never claims LCD bargraph data when unavailable."""
import math
import tkinter as tk
from dataclasses import dataclass
from .display import PREFIX, UNITS

@dataclass(frozen=True)
class BarState:
    full: float
    multiplier: int
    unit: str
    signed: bool
    value: float | None
    status: str
    source: str
    autorange: str


def bar_state(snapshot):
    # A range in Hz, dB, temperature, etc. needs function-specific treatment.
    # Until that is verified, do not manufacture a linear LCD equivalent.
    supported={'OHM','SIE','VDC','VAC','V','ADC','AAC','A','VAC_PLUS_DC','AAC_PLUS_DC'}
    if snapshot.range_unit not in supported or snapshot.range_multiplier not in PREFIX:
        return None
    full=snapshot.range_number * 10.**snapshot.range_multiplier
    if not math.isfinite(full) or full<=0: return None
    reading=next((r for r in snapshot.readings if r.id=='BARGRAPH' and r.unit==snapshot.range_unit),None)
    source='BARGRAPH z miernika'
    if reading is None:
        reading=next((r for r in snapshot.readings if r.id=='LIVE' and r.unit==snapshot.range_unit),None)
        source='z LIVE • odświeżanie USB'
    if reading is None: return None
    value=reading.value if reading.valid else None
    signed=snapshot.range_unit in {'VDC','ADC','V','A'}
    if value is not None and value<0: signed=True
    return BarState(full,snapshot.range_multiplier,snapshot.range_unit,signed,
                    value,reading.state,source,snapshot.autorange)


class BarGraph(tk.Canvas):
    def __init__(self,parent):
        super().__init__(parent,bg='#1a2230',height=100,highlightthickness=0)
        self.state=None
        self.connected=False
        self.bind('<Configure>',lambda e:self.draw())

    def update_snapshot(self,snapshot):
        self.state=bar_state(snapshot)
        self.connected=True
        self.draw()

    def disconnect(self):
        self.connected=False
        self.draw()

    def draw(self):
        self.delete('all')
        width=max(self.winfo_width(),260)
        s=self.state
        if not self.connected or s is None:
            self.create_text(0,38,anchor='w',fill='#9aaac0',font=('DejaVu Sans',9),
                             text='Bargraf: brak aktualnych danych' if not self.connected else 'Bargraf: brak zgodnych danych skali')
            return
        left,right=16,width-24
        scale=10.**s.multiplier
        low=-s.full if s.signed else 0.
        span=s.full-low
        def x(value): return left+(value-low)/span*(right-left)
        steps=10 if s.signed else 5
        # One grid aligns tick marks with the bar cells.
        count=steps*20
        for i in range(count+1):
            fraction=i/count
            px=left+fraction*(right-left)
            self.create_line(px,30 if i%20==0 else (34 if i%10==0 else (38 if i%2==0 else 41)),px,44,fill='#9aaac0')
            stride=10 if (right-left)/steps>=120 else (20 if not s.signed or width>=500 else 40)
            if i%stride==0:
                number=(low+fraction*span)/scale
                label=f'{number:g}'
                self.create_text(px,21,text=label,fill='#edf2f7',font=('DejaVu Sans',9))
        self.create_line(left,44,right,44,fill='#607089')
        if s.value is not None:
            value=max(low,min(s.full,s.value))
            zero=x(0)
            # Fractional endpoint keeps the value/scale relationship exact;
            # segments only imitate the physical look of the LCD bar.
            endpoint=x(value)
            lo,hi=sorted((zero,endpoint))
            cell=(right-left)/count
            for i in range(count):
                a=left+i*cell; b=left+(i+1)*cell-min(1.,cell*.15)
                if b>lo and a<hi:
                    self.create_rectangle(max(a,lo),49,min(b,hi),60,fill='#65dbb2',outline='')
            if value!=0:
                self.create_line(endpoint,47,endpoint,62,fill='#65dbb2',width=1)
            if abs(s.value)>s.full:
                self.create_text(right if s.value>0 else left,55,text='▶' if s.value>0 else '◀',fill='#ffc76d')
        else:
            self.create_text((left+right)/2,56,text=s.status,fill='#ffc76d',font=('DejaVu Sans',9,'bold'))
        unit=PREFIX[s.multiplier]+UNITS.get(s.unit,s.unit)
        mode='AUTO' if s.autorange=='AUTO' else s.autorange
        name={'OHM':'Rezystancja','VAC':'Napięcie AC','VDC':'Napięcie DC','V':'Napięcie','ADC':'Prąd DC','AAC':'Prąd AC','A':'Prąd','SIE':'Konduktancja','VAC_PLUS_DC':'Napięcie AC+DC','AAC_PLUS_DC':'Prąd AC+DC'}.get(s.unit,s.unit)
        value_text=f' · {s.value/scale:g} {unit}' if s.value is not None else ' · '+s.status
        self.create_text(left,79,text=f'{name}{value_text} · {mode} · zakres {s.full/scale:g} {unit}',anchor='w',fill='#edf2f7',font=('DejaVu Sans',9))
        self.create_text(right,97,text='Bargraf '+s.source,anchor='se',fill='#9aaac0',font=('DejaVu Sans',8))
