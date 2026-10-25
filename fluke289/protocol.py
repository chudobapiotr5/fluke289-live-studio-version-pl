# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Piotr
# This program comes with NO WARRANTY; see COPYING for license terms.
"""Read-only subset of Fluke 28x remote interface (2007)."""
from dataclasses import dataclass, asdict
import math

class ProtocolError(Exception):
    pass

class MeterError(ProtocolError):
    def __init__(self, code):
        self.code = code
        super().__init__({'1': 'Błąd składni komendy', '2': 'Błąd wykonania', '5': 'Brak danych'}.get(code, 'Nieznany ACK: '+code))

PRIMARY = set('LIMBO V_AC MV_AC V_DC MV_DC V_AC_OVER_DC V_DC_OVER_AC V_AC_PLUS_DC MV_AC_OVER_DC MV_DC_OVER_AC MV_AC_PLUS_DC A_AC MA_AC UA_AC A_DC MA_DC UA_DC A_AC_OVER_DC A_DC_OVER_AC A_AC_PLUS_DC MA_AC_OVER_DC MA_DC_OVER_AC MA_AC_PLUS_DC UA_AC_OVER_DC UA_DC_OVER_AC UA_AC_PLUS_DC TEMPERATURE OHMS CONDUCTANCE CONTINUITY CAPACITANCE DIODE_TEST V_AC_LOZ OHMS_LOW'.split())
SECONDARY = set('NONE HERTZ DUTY_CYCLE PULSE_WIDTH DBM DBV DBM_HERTZ DBV_HERTZ CREST_FACTOR PEAK_MIN_MAX'.split())
MODES = set('AUTO_HOLD HOLD LOW_PASS_FILTER MIN_MAX_AVG RECORD REL REL_PERCENT'.split())

def dial(function):
    """Inference from active function; the protocol has no physical switch field."""
    if function == 'V_AC_LOZ': return 'LoZ V~ (wnioskowane)'
    if function == 'OHMS_LOW': return '50 Ω (wnioskowane)'
    if function in {'OHMS', 'CONTINUITY', 'CONDUCTANCE'}: return 'Ω / ciągłość / nS (wnioskowane)'
    if function in {'CAPACITANCE', 'DIODE_TEST'}: return 'dioda / pojemność (wnioskowane)'
    if function == 'TEMPERATURE' or function.startswith('MV_') and function != 'MV_AC': return 'mV DC / temperatura (wnioskowane)'
    if function == 'MV_AC': return 'mV AC (wnioskowane)'
    if function == 'V_AC': return 'V AC (wnioskowane)'
    if function.startswith('V_'): return 'V DC / AC+DC (wnioskowane)'
    if function.startswith(('A_', 'MA_')): return 'A / mA (wnioskowane)'
    if function.startswith('UA_'): return 'µA (wnioskowane)'
    return 'nieustalone'

@dataclass
class Reading:
    id: str
    value: float
    unit: str
    multiplier: int
    decimals: int
    digits: int
    state: str
    attribute: str
    meter_time: float

    @property
    def valid(self):
        return self.state == 'NORMAL' and math.isfinite(self.value) and abs(self.value) < 9e37

    def display(self):
        if not self.valid: return self.state + ' [' + self.attribute + ']'
        prefix = {-9:'n', -6:'µ', -3:'m', 0:'', 3:'k', 6:'M'}.get(self.multiplier)
        if prefix is None: return f'{self.value:g} {self.unit} (mnożnik {self.multiplier})'
        decimals = max(0, min(self.decimals, 12))
        return f'{self.value / 10**self.multiplier:.{decimals}f} {prefix}{self.unit}'

@dataclass
class Snapshot:
    primary: str
    secondary: str
    autorange: str
    range_unit: str
    range_number: int
    range_multiplier: int
    lightning: str
    minmax_start: float
    modes: list
    readings: list
    raw: str

    @property
    def warnings(self):
        return ([f'Nieznana funkcja: {self.primary}'] if self.primary not in PRIMARY else []) + ([f'Nieznana podfunkcja: {self.secondary}'] if self.secondary not in SECONDARY else []) + [f'Nieznany tryb: {m}' for m in self.modes if m not in MODES]

    def as_dict(self): return asdict(self)

def parse_qdda(raw):
    t = [x.strip() for x in raw.split(',')]
    try:
        if len(t) < 10: raise ValueError('Za krótka odpowiedź')
        n = int(t[8])
        if not 0 <= n <= 64: raise ValueError('Liczba trybów poza limitem')
        k = 9+n
        count = int(t[k])
        if not 0 <= count <= 64 or len(t) != k+1+9*count: raise ValueError('Niezgodna liczba pól odczytów')
        readings = []
        for i in range(count):
            r = t[k+1+i*9:k+1+(i+1)*9]
            rd = Reading(r[0], float(r[1]), r[2], int(r[3]), int(r[4]), int(r[5]), r[6], r[7], float(r[8]))
            if not math.isfinite(rd.value) or not math.isfinite(rd.meter_time): raise ValueError('Niefinitywna liczba')
            if not -12 <= rd.multiplier <= 12 or not 0 <= rd.decimals <= 12: raise ValueError('Format liczby poza limitem')
            readings.append(rd)
        start = float(t[7])
        if not math.isfinite(start): raise ValueError('Niepoprawny czas')
        return Snapshot(t[0], t[1], t[2], t[3], int(t[4]), int(t[5]), t[6], start, t[9:k], readings, raw)
    except (ValueError, IndexError, OverflowError) as e:
        raise ProtocolError(f'Błędne QDDA: {e}') from e
