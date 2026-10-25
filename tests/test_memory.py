# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Piotr
# This program comes with NO WARRANTY; see COPYING for license terms.
import struct
import unittest
import tempfile
from pathlib import Path
from fluke289.memory import MemoryClient, MemoryCancelled, number, parse_counts, to_history
from fluke289.transport import Meter
from fluke289.protocol import ProtocolError
from test_app import Emulator


def put_number(data,offset,value):
    raw=struct.pack('<d',value)
    data[offset:offset+8]=raw[4:]+raw[:4]


def reading(code=1,value=1.9062):
    data=bytearray(30)
    struct.pack_into('<H',data,0,code)
    put_number(data,2,value)
    struct.pack_into('<HhhhHH',data,10,1,0,4,5,1,0)
    put_number(data,22,1000.25)
    return data


def saved(kind='measurement',name=b'Save-1'):
    size,offset={'measurement':(38,4),'minmax':(54,20),'peak':(54,20),'recording':(78,44)}[kind]
    data=bytearray(size)
    if kind!='measurement': put_number(data,4,1000.); put_number(data,12,1010.)
    for i,value in [(0,1),(2,0),(4,1),(6,1),(16,0),(18,0),(28,0)]:
        struct.pack_into('<H',data,offset+i,value)
    put_number(data,offset+8,5.)
    struct.pack_into('<H',data,size-2,1)
    if kind=='recording':
        struct.pack_into('<H',data,36,7); struct.pack_into('<H',data,40,1)
    return bytes(data+reading()+name)

MAPS={'readingid':'4,1,PRIMARY,2,MINIMUM,3,MAXIMUM,4,AVERAGE',
      'unit':'1,1,VDC','primfunction':'1,1,V_DC','secfunction':'1,0,NONE',
      'autorange':'1,1,AUTO','bolt':'1,0,OFF','mode':'1,0,NONE',
      'state':'1,1,NORMAL','attribute':'1,0,NONE'}

class FakeMeter:
    def query(self,command):
        if command=='QSLS': return '0,0,0,1'
        return MAPS[command.split()[1]]
    def memory_block(self,command,index): return saved()

class MemoryTests(unittest.TestCase):
    def test_counts_and_swapped_double_without_rounding(self):
        data=bytearray(8); put_number(data,0,.000000000123456789)
        self.assertEqual(number(data,0),.000000000123456789)
        self.assertEqual(parse_counts('1,2,3,4')['measurement'],4)
        for raw in ['1,2,3','1,2,-1,4','0,0,0,99999']:
            with self.assertRaises(ProtocolError): parse_counts(raw)

    def test_list_and_saved_snapshot_to_history(self):
        client=MemoryClient(FakeMeter())
        items=client.list_items()
        self.assertEqual(items[0]['name'],'Save-1')
        self.assertEqual(items[0]['readings'][0]['value'],1.9062)
        archive=client.download('measurement',0,items[0]['raw_hex'])
        h=to_history(archive,'test meter')
        self.assertEqual(h.samples[-1]['data']['readings'][0]['decimals'],4)
        self.assertEqual(h.samples[-1]['time'],1000.25)
        with self.assertRaises(ProtocolError): client.download('measurement',0,'changed')

    def test_cancel_and_truncated_headers(self):
        with self.assertRaises(MemoryCancelled): MemoryClient(FakeMeter(),cancel=lambda:True).list_items()
        meter=FakeMeter(); meter.memory_block=lambda *args:b'\x00'
        with self.assertRaises(ProtocolError): MemoryClient(meter).header('measurement',0)

    def test_real_serial_binary_framing_preserves_embedded_cr(self):
        raw=saved(name=b'Save-13')
        raw=bytearray(raw); raw[0]=13
        replies={b'QSMR 0':b'0\r#0'+raw+b'\r'}
        em=Emulator(replies)
        try:
            m=Meter(em.port,2)
            try:
                self.assertEqual(m.memory_block('QSMR',0),raw)
                with self.assertRaises(ValueError): m.memory_block('DELETE',0)
                with self.assertRaises(ValueError): m.query('QEMAP unit\rRI')
            finally: m.close()
        finally: em.close()

    def test_recording_preserves_accumulator_without_fake_average(self):
        class RecordingMeter(FakeMeter):
            def memory_block(self,*args): return saved('recording')
            def memory_interval(self,*args):
                data=bytearray(146)
                put_number(data,0,1000); put_number(data,8,1005)
                data[16:46]=reading(2,1.8)
                data[46:76]=reading(3,2.0)
                data[76:106]=reading(4,19.)
                data[110:140]=reading(1,1.9)
                struct.pack_into('<H',data,106,10)
                return bytes(data)
        archive=MemoryClient(RecordingMeter()).download('recording',0)
        interval=archive['intervals'][0]
        self.assertEqual(interval['accumulators'][0]['value'],19.)
        self.assertNotIn('AVERAGE',[r['id'] for r in interval['readings']])
        self.assertEqual(len(to_history(archive,'test').samples),1)

    def test_saved_copy_roundtrip_and_meter_clock_source(self):
        import json
        from fluke289.history import load_session
        archive=MemoryClient(FakeMeter()).download('measurement',0)
        archive['identity']='test meter'
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'memory.json'
            path.write_text(json.dumps(archive))
            h=load_session(path)
            self.assertEqual(h.time_source,'meter')
            self.assertEqual(h.samples[-1]['data']['readings'][0]['value'],1.9062)

    def test_worker_exclusively_pauses_live_for_memory(self):
        import threading
        import queue
        from unittest.mock import patch
        from fluke289.worker import Worker
        from fluke289.protocol import parse_qdda
        from test_app import SAMPLE
        entered=threading.Event(); release=threading.Event()
        class Device:
            snapshots=0
            def __init__(self,*args): self.trace=lambda *args:None
            def identify(self): return 'FLUKE 289,V1.41,TEST'
            def snapshot(self): Device.snapshots+=1; return parse_qdda(SAMPLE)
            def close(self): pass
        class Client:
            def __init__(self,*args,**kwargs): pass
            def list_items(self): entered.set(); release.wait(2); return []
        with patch('fluke289.worker.MemoryClient',Client):
            w=Worker('fake',interval=.03,factory=Device)
            w.start()
            try:
                while w.events.get(timeout=2)[0]!='snapshot': pass
                w.memory_request('list')
                self.assertTrue(entered.wait(2))
                count=Device.snapshots
                # The callback runs in the port owner thread and can inspect
                # that no other command takes the serial port while blocked.
                self.assertEqual(Device.snapshots,count)
                release.set()
                kinds=[]
                for _ in range(30):
                    kind,data=w.events.get(timeout=2); kinds.append(kind)
                    if kind=='snapshot' and 'memory_result' in kinds: break
                self.assertIn('memory_result',kinds)
                self.assertEqual(kinds[-1],'snapshot')
            finally:
                release.set(); w.stop_event.set(); w.join(2)
                self.assertFalse(w.is_alive())
