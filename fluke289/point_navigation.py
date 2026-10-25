# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Piotr
import bisect

def step_point(points,current,direction):
    """Move by measured time; never interpolates or wraps at an endpoint."""
    if not points:return None
    points=sorted(points,key=lambda p:p[0]);times=[p[0] for p in points]
    if current is None:return points[0] if direction>0 else points[-1]
    index=bisect.bisect_right(times,current) if direction>0 else bisect.bisect_left(times,current)-1
    return points[max(0,min(len(points)-1,index))]

def elapsed_text(seconds,milliseconds=True):
    sign='−' if seconds<0 else '';total=abs(seconds)
    whole=int(round(total*1000)) if milliseconds else int(total)*1000
    hours,rest=divmod(whole,3600000);minutes,rest=divmod(rest,60000);secs,ms=divmod(rest,1000)
    prefix=f'{hours:02}:' if hours else ''
    return sign+prefix+f'{minutes:02}:{secs:02}'+(f'.{ms:03}' if milliseconds else '')
