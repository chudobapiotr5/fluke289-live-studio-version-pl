# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Piotr
# This program comes with NO WARRANTY; see COPYING for license terms.
"""Display the meter's MIN/MAX/AVG; never compute substitute statistics."""
import math
from .display import format_reading

FIELDS=(('MAXIMUM','Maximum'),('AVERAGE','Average'),('MINIMUM','Minimum'))

def elapsed_text(timestamp, start):
    if not math.isfinite(start) or not math.isfinite(timestamp) or start<=0 or timestamp<start:
        return '—'
    total=int(timestamp-start+1e-6)
    days,total=divmod(total,86400)
    hours,total=divmod(total,3600)
    minutes,seconds=divmod(total,60)
    return (f'{days} d ' if days else '')+f'{hours:02}:{minutes:02}:{seconds:02}'


def meter_minmax(snapshot):
    readings={r.id:r for r in snapshot.readings}
    active=('MIN_MAX_AVG' in snapshot.modes or snapshot.secondary=='PEAK_MIN_MAX'
            or any(key in readings for key,label in FIELDS))
    if not active: return None
    result=[]
    for key,label in FIELDS:
        r=readings.get(key)
        result.append((key,label,format_reading(r) if r else '—',
                       elapsed_text(r.meter_time,snapshot.minmax_start) if r else '—'))
    return result
