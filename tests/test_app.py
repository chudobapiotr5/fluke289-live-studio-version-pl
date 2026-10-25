# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Piotr
# This program comes with NO WARRANTY; see COPYING for license terms.
import csv
import json
import os
import pty
import queue
import select
import tempfile
import threading
import time
import unittest
from pathlib import Path
from fluke289.protocol import parse_qdda, ProtocolError, MeterError, PRIMARY, SECONDARY, MODES, dial
from fluke289.transport import Meter
from fluke289.storage import Store, export_csv
from fluke289.worker import Worker

# Transcription of the first QDDA example in Fluke remote interface, p. 11.
SAMPLE = ('MV_AC,NONE,AUTO,VAC,50,-3,OFF,0.000,0,2,'
          'LIVE,0.005029,VAC,-3,3,5,NORMAL,NONE,1197308998.282,'
          'PRIMARY,0.005029,VAC,-3,3,5,NORMAL,NONE,1197308998.282')
PEAK = ('MV_AC,PEAK_MIN_MAX,AUTO,VAC,50,-3,OFF,1197309132.612,1,MIN_MAX_AVG,5,'
        'LIVE,0.00515,VAC,-3,2,5,NORMAL,NONE,1197309141.806,'
        'PRIMARY,0.00515,VAC,-3,2,5,NORMAL,NONE,1197309141.806,'
        'MINIMUM,-0.0211,V,-3,2,5,NORMAL,NONE,1197309133.616,'
        'MAXIMUM,0.03055,V,-3,2,5,NORMAL,NONE,1197309133.366,'
        'AVERAGE,0.00529,VAC,-3,2,5,NORMAL,NONE,1197309141.806')

class Emulator:
    """Synthetic serial peer, not hardware verification."""
    def __init__(self, replies):
        self.master, self.slave = pty.openpty()
        self.port = os.ttyname(self.slave)
        self.replies = replies
        self.commands = []
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        buf = b''
        while not self.stop.is_set():
            ready, _, _ = select.select([self.master], [], [], .05)
            if not ready: continue
            try: buf += os.read(self.master, 4096)
            except OSError: return
            while b'\r' in buf:
                cmd, buf = buf.split(b'\r', 1)
                self.commands.append(cmd)
                response = self.replies.get(cmd, b'1\r')
                for chunk in response:
                    os.write(self.master, bytes([chunk]))
                    time.sleep(.0001)

    def close(self):
        self.stop.set()
        self.thread.join(1)
        os.close(self.master)
        os.close(self.slave)

class ProtocolTests(unittest.TestCase):
    def test_official_examples(self):
        s = parse_qdda(SAMPLE)
        self.assertEqual(s.readings[1].display(), '5.029 mVAC')
        self.assertEqual(s.readings[1].value, .005029)
        self.assertEqual(s.warnings, [])
        s = parse_qdda(PEAK)
        self.assertEqual(len(s.readings), 5)
        self.assertEqual(s.modes, ['MIN_MAX_AVG'])
        self.assertEqual(s.readings[2].value, -.0211)

    def test_all_function_tokens_preserved(self):
        for function in PRIMARY:
            s = parse_qdda(SAMPLE.replace('MV_AC,', function+',', 1))
            self.assertEqual(s.primary, function)
            self.assertEqual(s.warnings, [])
        for secondary in SECONDARY:
            self.assertEqual(parse_qdda(SAMPLE.replace(',NONE,AUTO', ','+secondary+',AUTO')).secondary, secondary)
        for mode in MODES:
            self.assertEqual(parse_qdda(SAMPLE.replace(',0,2,LIVE', ',1,'+mode+',2,LIVE')).modes, [mode])
        self.assertEqual(dial('LIMBO'), 'nieustalone')
        self.assertIn('wnioskowane', dial('TEMPERATURE'))

    def test_unknown_tokens_preserved(self):
        s = parse_qdda(SAMPLE.replace('MV_AC', 'NEW_FUNCTION'))
        self.assertTrue(s.warnings)
        self.assertEqual(dial(s.primary), 'nieustalone')

    def test_bad_frames(self):
        for s in ['', SAMPLE+',extra', SAMPLE.rsplit(',', 1)[0], SAMPLE.replace(',0,2,LIVE', ',99,2,LIVE'), SAMPLE.replace('0.005029', 'NaN'), SAMPLE.replace(',3,5,NORMAL', ',99,5,NORMAL'), SAMPLE.replace(',0,2,LIVE', ',0,-1,LIVE')]:
            with self.subTest(s=s):
                with self.assertRaises(ProtocolError): parse_qdda(s)

    def test_overload_not_numeric(self):
        for state in ['OL', 'OL_MINUS', 'OPEN_TC', 'INVALID', 'BLANK', 'DISCHARGE']:
            r = parse_qdda(SAMPLE.replace('NORMAL', state)).readings[0]
            self.assertFalse(r.valid)
            self.assertIn(state, r.display())

class TransportTests(unittest.TestCase):
    def test_fragmented_crlf_and_identity(self):
        em = Emulator({b'ID': b'0\r\nFLUKE 289,V1.00,95081087\r\n', b'QDDA': b'0\r'+SAMPLE.encode()+b'\r'})
        try:
            m = Meter(em.port, 2)
            try:
                self.assertEqual(m.serial.baudrate, 115200)
                self.assertIn('FLUKE 289', m.identify())
                self.assertEqual(m.snapshot().primary, 'MV_AC')
                with self.assertRaises(ValueError): m.query('RI')
            finally: m.close()
            self.assertEqual(em.commands, [b'ID', b'QDDA'])
        finally: em.close()

    def test_ack_errors(self):
        for code in ['1', '2', '5', '9']:
            em = Emulator({b'ID': (code+'\r').encode()})
            try:
                m = Meter(em.port, .3)
                try:
                    with self.assertRaises(MeterError): m.identify()
                finally: m.close()
            finally: em.close()

    def test_timeout_and_other_model(self):
        for response in [b'0\rpartial', b'0\rFLUKE 287,V1,123\r', b'0\r\xff\r']:
            em = Emulator({b'ID': response})
            try:
                m = Meter(em.port, .2)
                try:
                    with self.assertRaises(ProtocolError): m.identify()
                finally: m.close()
            finally: em.close()

class StorageWorkerTests(unittest.TestCase):
    def test_export_and_invalid_value(self):
        with tempfile.TemporaryDirectory() as d:
            db, csvpath = str(Path(d)/'log.sqlite3'), str(Path(d)/'log.csv')
            s = Store(db)
            s.add('identity', 'FLUKE 289,V1,123')
            s.add('snapshot', parse_qdda(SAMPLE).as_dict())
            s.add('snapshot', parse_qdda(SAMPLE.replace('NORMAL','OL')).as_dict())
            s.add('snapshot', parse_qdda(SAMPLE.replace('MV_AC', '=FORMULA')).as_dict())
            s.close()
            export_csv(db, csvpath)
            with open(csvpath, encoding='utf-8-sig') as f: rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 6)
            self.assertEqual(rows[0]['value_base'], '0.005029')
            self.assertEqual(rows[2]['value_base'], '')
            self.assertEqual(rows[4]['primary_function'], "'=FORMULA")
            with self.assertRaises(ValueError): export_csv(db, db)

    def test_worker_real_serial_and_stop(self):
        em = Emulator({b'ID': b'0\rFLUKE 289,V1,123\r', b'QDDA': b'0\r'+SAMPLE.encode()+b'\r'})
        try:
            with tempfile.TemporaryDirectory() as d:
                w = Worker(em.port, str(Path(d)/'s.sqlite3'), .2, .5)
                w.start()
                kinds = []
                deadline = time.monotonic()+3
                while time.monotonic() < deadline:
                    kind, data = w.events.get(timeout=3)
                    kinds.append(kind)
                    if kind == 'snapshot': break
                w.stop_event.set()
                w.join(2)
                self.assertFalse(w.is_alive())
                self.assertIn('snapshot', kinds)
        finally: em.close()

    def test_reconnect_after_failure(self):
        class FakeMeter:
            attempts = 0
            closed = 0
            def __init__(self, *args):
                FakeMeter.attempts += 1
                self.attempt = FakeMeter.attempts
            def identify(self): return 'FLUKE 289,V1,123'
            def snapshot(self):
                if self.attempt == 1: raise ProtocolError('przerwane łącze')
                return parse_qdda(SAMPLE)
            def close(self): FakeMeter.closed += 1
        with tempfile.TemporaryDirectory() as d:
            w = Worker('fake', str(Path(d)/'s.sqlite3'), .2, .1, FakeMeter)
            w.start()
            kinds = []
            try:
                deadline = time.monotonic()+6
                while time.monotonic() < deadline:
                    kind, data = w.events.get(timeout=5)
                    kinds.append(kind)
                    if kind == 'snapshot': break
            finally:
                w.stop_event.set()
                w.join(2)
            self.assertIn('error', kinds)
            self.assertIn('snapshot', kinds)
            self.assertGreaterEqual(FakeMeter.closed, 2)

    def test_storage_failure_is_fatal(self):
        w = Worker('unused', '/does-not-exist/no.sqlite3')
        w.start()
        w.join(2)
        self.assertEqual(w.events.get_nowait()[0], 'fatal')

if __name__ == '__main__': unittest.main()
