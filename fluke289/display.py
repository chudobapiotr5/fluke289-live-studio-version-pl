# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Piotr
# This program comes with NO WARRANTY; see COPYING for license terms.
"""One meter-specified format for live, history and export."""
from dataclasses import asdict, is_dataclass
from decimal import Decimal
import math

PREFIX = {-9:'n', -6:'µ', -3:'m', 0:'', 3:'k', 6:'M'}
UNITS = {'OHM':'Ω', 'SIE':'S', 'CEL':'°C', 'FAR':'°F', 'PCT':'%'}

def meter_scale(reading):
    r = asdict(reading) if is_dataclass(reading) else reading
    multiplier=int(r['multiplier'])
    if multiplier not in PREFIX: raise ValueError('Nieznany przedrostek miernika')
    return 10.0**multiplier, PREFIX[multiplier]+UNITS.get(r['unit'],r['unit'])

def reading_parts(reading):
    r = asdict(reading) if is_dataclass(reading) else reading
    state=r['state']
    if state!='NORMAL' or not math.isfinite(r['value']) or abs(r['value'])>=9e37:
        return state, ''
    multiplier=int(r['multiplier']); places=int(r['decimals'])
    if multiplier not in PREFIX or not 0<=places<=12:
        return 'Nieznany format odczytu', ''
    # QDDA gives base units, LCD multiplier and decimal places. Preserve all
    # display digits, including trailing zeros; never choose a new SI prefix.
    number=Decimal(str(r['value'])).scaleb(-multiplier)
    value=f'{number:.{places}f}'
    unit=PREFIX[multiplier]+UNITS.get(r['unit'],r['unit'])
    return value,unit

def format_reading(reading):
    value,unit=reading_parts(reading)
    return value+(' '+unit if unit else '')
