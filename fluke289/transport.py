# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Piotr
# This program comes with NO WARRANTY; see COPYING for license terms.
import time
import re
import struct
import serial
from .protocol import ProtocolError, MeterError, parse_qdda

class Meter:
    def __init__(self, port, timeout=2.0, trace=None):
        self.timeout = timeout
        self.trace = trace or (lambda *args: None)
        self.serial = serial.Serial(port, 115200, timeout=0.05, write_timeout=timeout,
                                    bytesize=8, parity='N', stopbits=1,
                                    xonxoff=False, rtscts=False, dsrdtr=False, exclusive=True)

    def close(self): self.serial.close()

    def _line(self, deadline):
        b = bytearray()
        while time.monotonic() < deadline:
            c = self.serial.read(1)
            if not c or c == b'\n' and not b: continue
            if c == b'\r':
                if not b: continue
                try:
                    result = b.decode('ascii')
                except UnicodeDecodeError as e:
                    raise ProtocolError('Odpowiedź nie jest ASCII') from e
                self.trace('RX', result)
                return result
            b.extend(c)
            if len(b) > 32768: raise ProtocolError('Przekroczony limit odpowiedzi')
        raise ProtocolError('Timeout: niepełna odpowiedź miernika')

    def query(self, command):
        if command not in {'ID','QDDA','QM','QSLS'} and not re.fullmatch(r'QEMAP (primfunction|secfunction|autorange|unit|bolt|mode|readingid|state|attribute)',command):
            raise ValueError('Dozwolone tylko komendy odczytu')
        # Each transaction follows a complete prior response; on error the worker
        # closes and reopens after a quiet recovery delay before another ID.
        self.serial.reset_input_buffer()
        self.trace('TX', command)
        self.serial.write((command+'\r').encode('ascii'))
        deadline = time.monotonic() + self.timeout
        ack = self._line(deadline).strip()
        if ack != '0': raise MeterError(ack)
        return self._line(deadline).strip()

    def identify(self):
        identity = self.query('ID')
        fields = [f.strip() for f in identity.split(',')]
        if len(fields) != 3 or fields[0] != 'FLUKE 289':
            raise ProtocolError('Oczekiwano FLUKE 289; odpowiedź: '+identity)
        return identity

    def snapshot(self): return parse_qdda(self.query('QDDA'))

    def _exact(self, count, deadline):
        result=bytearray()
        while len(result)<count and time.monotonic()<deadline:
            result.extend(self.serial.read(count-len(result)))
        if len(result)!=count: raise ProtocolError('Timeout: ucięta odpowiedź binarna pamięci')
        return bytes(result)

    def _memory_start(self, command):
        self.serial.reset_input_buffer()
        self.trace('TX',command)
        self.serial.write((command+'\r').encode('ascii'))
        deadline=time.monotonic()+max(5,self.timeout)
        ack=self._line(deadline).strip()
        if ack!='0': raise MeterError(ack)
        first=self._exact(1,deadline)
        if first==b'\n': first=self._exact(1,deadline)
        if first+self._exact(1,deadline)!=b'#0':
            raise ProtocolError('Oczekiwano binarnego bloku #0')
        return deadline

    def memory_block(self,command,index):
        layouts={'QSMR':(38,36),'QMMSI':(54,52),'QPSI':(54,52),'QRSI':(78,76)}
        if command not in layouts or type(index) is not int or not 0<=index<2000:
            raise ValueError('Niedozwolona komenda pamięci')
        deadline=self._memory_start(f'{command} {index}')
        size,offset=layouts[command]
        header=self._exact(size,deadline)
        count=struct.unpack_from('<H',header,offset)[0]
        if count>64: raise ProtocolError('Za dużo pól w zapisie pamięci')
        readings=self._exact(count*30,deadline)
        name=bytearray()
        while True:
            ch=self._exact(1,deadline)
            if ch==b'\r': break
            name.extend(ch)
            if len(name)>1024: raise ProtocolError('Zbyt długa nazwa zapisu')
        result=header+readings+bytes(name)
        self.trace('RX_BINARY',result.hex())
        return result

    def memory_interval(self,record,index):
        if any(type(n) is not int or not 0<=n<100000 for n in [record,index]):
            raise ValueError('Niepoprawny indeks interwału')
        deadline=self._memory_start(f'QSRR {record},{index}')
        result=self._exact(146,deadline)
        if self._exact(1,deadline)!=b'\r': raise ProtocolError('Brak końca bloku interwału')
        self.trace('RX_BINARY',result.hex())
        return result
