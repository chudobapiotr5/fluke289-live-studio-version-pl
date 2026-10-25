# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Piotr
"""Read-only comparison; source timestamps and readings are never modified."""
import math
from .history import History

def choices(history):
    return list(dict.fromkeys((s['segment'],r['id'],r['unit']) for s in history.samples for r in s['data']['readings']))

def compare_histories(first,second,selection_a,selection_b,shift=0.,relative=False):
    if selection_a[2]!=selection_b[2]: raise ValueError('Wybierz tę samą jednostkę w obu zapisach.')
    if not math.isfinite(shift): raise ValueError('Przesunięcie musi być skończoną liczbą sekund.')
    result=History(limit=len(first.samples)+len(second.samples)); result.time_source='meter'
    events=[]
    for label,history,selection,offset in [('A',first,selection_a,0.),('B',second,selection_b,shift)]:
        segment,field,unit=selection;points=[]
        for s in history.samples:
            if s['segment']!=segment:continue
            for r in s['data']['readings']:
                if r['id']!=field or r['unit']!=unit:continue
                t=r.get('meter_time',0)
                if not relative and (not math.isfinite(t) or t<=0):
                    raise ValueError('Brak czasu miernika dla wybranego pola. Wybierz dopasowanie od początku.')
                points.append((s['time'] if relative else t,s,r))
        if not points: raise ValueError('Brak punktów wybranej serii.')
        origin=min(t for t,s,r in points) if relative else 0
        for t,s,r in points:
            copy=dict(r,id=f'{label} · {field}')
            data=dict(s['data'],primary='PORÓWNANIE',secondary='NONE',modes=[],minmax_start=0,readings=[copy])
            events.append((t-origin+offset,data,s['gap']))
    for t,data,gap in sorted(events,key=lambda e:e[0]):
        if gap:result.gap()
        result.add(data,t,'Porównanie A/B')
    result.comparison_relative=relative
    return result


def preferred_pair(options_a,options_b):
    """Prefer matching main readings, independently of wire record order."""
    pairs=[(a,b) for a in options_a for b in options_b if a[2]==b[2]]
    if not pairs:return None
    priority={'PRIMARY':0,'LIVE':1,'SECONDARY':2,'AVERAGE':3,'MINIMUM':4,'MAXIMUM':5}
    return min(pairs,key=lambda pair:(pair[0][1]!=pair[1][1],priority.get(pair[0][1],9)+priority.get(pair[1][1],9)))


def comparison_stats(history,tolerance=.5):
    """Nearest-time proposals, shortest first, each source point used once."""
    import bisect
    from decimal import Decimal,ROUND_HALF_EVEN
    from .history import valid
    if not math.isfinite(tolerance) or tolerance<=0:raise ValueError('Limit dopasowania musi być dodatnią liczbą sekund.')
    groups={'A':[],'B':[]}
    for s in history.samples:
        for r in s['data']['readings']:
            label=r['id'].split(' · ')[0]
            if label in groups:groups[label].append((s['time'],r))
    a,b=[sorted(groups[k],key=lambda p:p[0]) for k in ('A','B')]
    result={'count':0,'equal':0,'tolerance':tolerance,'mean':None,'maximum':None,'max_dt':None,'worst':None,'overlap':None,'pairs':[]}
    if not a or not b:return result
    low=max(a[0][0],b[0][0]);high=min(a[-1][0],b[-1][0])
    if high<low:return result
    result['overlap']=(low,high)
    a=[p for p in a if low<=p[0]<=high and valid(p[1])];b=[p for p in b if low<=p[0]<=high and valid(p[1])]
    times=[p[0] for p in b];proposals=[]
    for i,(t,r) in enumerate(a):
        j=bisect.bisect_left(times,t)
        candidates=[k for k in (j-1,j) if 0<=k<len(b)]
        if not candidates:continue
        k=min(candidates,key=lambda k:abs(times[k]-t));dt=abs(times[k]-t)
        if dt<=tolerance:proposals.append((dt,i,k))
    used=set();pairs=[]
    for dt,i,k in sorted(proposals):
        if k in used:continue
        used.add(k);ta,ra=a[i];tb,rb=b[k]
        va=Decimal(str(ra['value']));vb=Decimal(str(rb['value']))
        exponent=max(ra['multiplier']-ra['decimals'],rb['multiplier']-rb['decimals'])
        quantum=Decimal(1).scaleb(exponent)
        equal=va.quantize(quantum,rounding=ROUND_HALF_EVEN)==vb.quantize(quantum,rounding=ROUND_HALF_EVEN)
        pairs.append({'a':(ta,ra),'b':(tb,rb),'dt':dt,'difference':float(abs(vb-va)),'equal':equal})
    if not pairs:return result
    worst=max(pairs,key=lambda p:p['difference'])
    result.update(pairs=sorted(pairs,key=lambda p:p['a'][0]),count=len(pairs),equal=sum(p['equal'] for p in pairs),mean=math.fsum(p['difference'] for p in pairs)/len(pairs),maximum=worst['difference'],max_dt=max(p['dt'] for p in pairs),worst=worst)
    return result
