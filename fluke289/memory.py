# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Piotr
# This program comes with NO WARRANTY; see COPYING for license terms.
"""Read-only Fluke 28x memory protocol, independently implemented.

Binary layouts researched against N0ury/dmm_util and fvaleur/dmm_util.
See docs/PAMIEC.md for provenance, limitations and validation status.
"""
import csv
import math
import struct
from dataclasses import asdict
from .protocol import ProtocolError, Reading

KINDS={'recording':('Recording','QRSI',78,76),
       'minmax':('MIN MAX','QMMSI',54,52),
       'peak':('Peak','QPSI',54,52),
       'measurement':('Measurement','QSMR',38,36)}
MAPS={'primfunction','secfunction','autorange','unit','bolt','mode','readingid','state','attribute'}
MAX_ITEMS=2000
MAX_READINGS=64
MAX_SAMPLES=100000

class MemoryCancelled(Exception): pass

def u16(data,offset): return struct.unpack_from('<H',data,offset)[0]
def s16(data,offset): return struct.unpack_from('<h',data,offset)[0]
def number(data,offset):
    # Fluke uses big word first, little-endian bytes within each 32-bit word.
    raw=data[offset:offset+8]
    if len(raw)!=8: raise ProtocolError('Ucięta liczba binarna')
    value=struct.unpack('<d',raw[4:]+raw[:4])[0]
    if not math.isfinite(value): raise ProtocolError('Niefinitywna liczba pamięci')
    return value


def parse_counts(text):
    try:
        fields=next(csv.reader([text],skipinitialspace=True))
        counts=[int(field) for field in fields]
        if len(counts)!=4 or any(n<0 or n>MAX_ITEMS for n in counts): raise ValueError()
        return dict(zip(KINDS,counts))
    except (ValueError,csv.Error) as e: raise ProtocolError('Niepoprawna odpowiedź QSLS') from e


class MemoryClient:
    def __init__(self,meter,cancel=None,progress=None):
        self.meter=meter
        self.cancel=cancel or (lambda:False)
        self.progress=progress or (lambda done,total:None)
        self.maps={}

    def check(self):
        if self.cancel(): raise MemoryCancelled('Anulowano odczyt pamięci')

    def enum(self,name,code):
        self.check()
        if name not in self.maps:
            if name not in MAPS: raise ValueError('Niedozwolona mapa')
            text=self.meter.query('QEMAP '+name)
            try:
                tokens=[t.strip() for t in next(csv.reader([text],skipinitialspace=True))]
                count=int(tokens[0])
                if not 0<=count<=1024 or len(tokens)!=1+count*2: raise ValueError()
                self.maps[name]={int(tokens[i]):tokens[i+1] for i in range(1,len(tokens),2)}
                if len(self.maps[name])!=count: raise ValueError()
            except (ValueError,IndexError,csv.Error) as e:
                raise ProtocolError('Niepoprawna mapa '+name) from e
        mapping=self.maps[name]
        if code in mapping: return mapping[code]
        if name=='mode':
            # Flags may be combinations not present as complete map entries.
            parts=[(bit,label) for bit,label in mapping.items() if bit>0 and bit&(bit-1)==0 and bit&code]
            combined=0
            for bit,label in parts: combined|=bit
            if combined==code: return '|'.join(label for bit,label in parts)
        return f'UNKNOWN_{name}({code})'

    def readings(self,data):
        if len(data)%30 or len(data)>30*MAX_READINGS:
            raise ProtocolError('Niepoprawny blok odczytów pamięci')
        result=[]
        for offset in range(0,len(data),30):
            value=number(data,offset+2)
            multiplier=s16(data,offset+12); decimals=s16(data,offset+14); digits=s16(data,offset+16)
            if not -12<=multiplier<=12 or not 0<=decimals<=12 or not 0<=digits<=12:
                raise ProtocolError('Niepoprawny format odczytu pamięci')
            r=Reading(self.enum('readingid',u16(data,offset)),value,
                      self.enum('unit',u16(data,offset+10)),multiplier,decimals,digits,
                      self.enum('state',u16(data,offset+18)),self.enum('attribute',u16(data,offset+20)),number(data,offset+22))
            result.append(asdict(r))
        return result

    def header(self,kind,index):
        self.check()
        if kind not in KINDS or type(index) is not int or not 0<=index<MAX_ITEMS:
            raise ValueError('Niepoprawny indeks pamięci')
        title,command,size,count_offset=KINDS[kind]
        raw=self.meter.memory_block(command,index)
        if len(raw)<size: raise ProtocolError('Ucięty nagłówek pamięci')
        count=u16(raw,count_offset)
        end=size+count*30
        if count>MAX_READINGS or len(raw)<end: raise ProtocolError('Ucięte odczyty pamięci')
        if kind=='measurement': offset=4; start=None; finish=None
        else:
            offset=44 if kind=='recording' else 20
            start=number(raw,4); finish=number(raw,12)
            if start<0 or finish<start: raise ProtocolError('Niepoprawne daty pamięci')
        readings=self.readings(raw[size:end])
        if start is None:
            primary=next((r for r in readings if r['id']=='PRIMARY'),None)
            start=primary['meter_time'] if primary else None
            finish=start
        modes=self.enum('mode',u16(raw,offset+28))
        item={'kind':kind,'index':index,'name':raw[end:].rstrip(b'\x00').decode('utf-8',errors='replace'),
              'start':start,'end':finish,'readings':readings,'raw_hex':raw.hex(),
              'primary':self.enum('primfunction',u16(raw,offset)),
              'secondary':self.enum('secfunction',u16(raw,offset+2)),
              'autorange':self.enum('autorange',u16(raw,offset+4)),
              'range_unit':self.enum('unit',u16(raw,offset+6)),
              'range_number':number(raw,offset+8),'range_multiplier':s16(raw,offset+16),
              'lightning':self.enum('bolt',u16(raw,offset+18)),
              'modes':[] if modes=='NONE' else modes.split('|')}
        if kind=='recording':
            # These words have not been assumed to be 32-bit values: preserve
            # and reject nonzero high words until the layout is verified.
            if u16(raw,38) or u16(raw,42):
                raise ProtocolError('Nieobsługiwane wysokie słowo indeksu/liczby próbek; zachowaj diagnostykę')
            item.update(reading_index=u16(raw,36),sample_count=u16(raw,40),sample_interval=number(raw,20))
        return item

    def list_items(self):
        self.check()
        counts=parse_counts(self.meter.query('QSLS'))
        total=sum(counts.values()); result=[]
        for kind,count in counts.items():
            for index in range(count):
                item=self.header(kind,index)
                result.append(item)
                self.progress(len(result),total)
        # Detect memory changes rather than presenting mixed indexes as stable.
        if parse_counts(self.meter.query('QSLS'))!=counts:
            raise ProtocolError('Lista pamięci zmieniła się podczas odczytu; odśwież ją ponownie')
        return result

    def download(self,kind,index,expected_hex=None):
        item=self.header(kind,index)
        if expected_hex and item['raw_hex']!=expected_hex:
            raise ProtocolError('Zapis zmienił się od odczytu listy; odśwież listę')
        result={'format':'fluke289-memory-v1','header':item,'intervals':[]}
        if kind!='recording': return result
        count=item['sample_count']
        if count>MAX_SAMPLES: raise ProtocolError('Za duża sesja')
        for index in range(count):
            self.check()
            raw=self.meter.memory_interval(item['reading_index'],index)
            if len(raw)!=146: raise ProtocolError('Niepoprawna długość interwału sesji')
            start,end=number(raw,0),number(raw,8)
            if start<0 or end<start: raise ProtocolError('Niepoprawny czas interwału')
            records=self.readings(raw[16:106])
            primary=self.readings(raw[110:140])
            # AVERAGE here is an accumulator in existing implementations.
            # Keep it losslessly as raw metadata; do not invent a display mean.
            result['intervals'].append({'start':start,'end':end,
                'readings':[r for r in records if r['id']!='AVERAGE']+primary,
                'accumulators':[r for r in records if r['id']=='AVERAGE'],
                'sample_count_raw':u16(raw,106),'unknown_108':u16(raw,108),
                'record_type_code':u16(raw,140),'stable_code':u16(raw,142),
                'transient_code':u16(raw,144),'raw_hex':raw.hex()})
            self.progress(index+1,count)
        return result


def to_history(archive,identity):
    from .history import History
    h=History()
    h.time_source='meter'
    item=archive['header']
    intervals=archive['intervals']
    sources=intervals if item['kind']=='recording' else [{'readings':item['readings'],'end':item['end']}]
    events=[]
    for source in sources:
        readings=source['readings']
        if not isinstance(readings,list) or len(readings)>MAX_READINGS: raise ProtocolError('Niepoprawna lista odczytów kopii')
        for r in readings:
            if not isinstance(r,dict) or not math.isfinite(r['value']) or not math.isfinite(r['meter_time']):
                raise ProtocolError('Niepoprawne liczby w kopii pamięci')
            if type(r['multiplier']) is not int or not -12<=r['multiplier']<=12 or type(r['decimals']) is not int or not 0<=r['decimals']<=12:
                raise ProtocolError('Niepoprawny format odczytu kopii')
        timestamp=source['end']
        if timestamp is None: continue
        if not math.isfinite(timestamp) or not 0<=timestamp<=253402214400: raise ProtocolError('Niepoprawny czas kopii pamięci')
        data={key:item[key] for key in ['primary','secondary','modes','autorange','range_unit','range_number','range_multiplier','lightning']}
        data.update(readings=readings,minmax_start=item['start'] or 0,raw=item['raw_hex'])
        if item['kind']=='recording':
            grouped={}
            for r in readings:
                stamp=r['meter_time']
                if not 0<=stamp<=253402214400: raise ProtocolError('Niepoprawny czas odczytu pamięci')
                grouped.setdefault(stamp,[]).append(r)
            for stamp,records in grouped.items():
                events.append((stamp,dict(data,readings=records)))
        else:
            events.append((timestamp,data))
    for timestamp,data in sorted(events,key=lambda event:event[0]):
        h.add(data,timestamp,identity)
    return h
