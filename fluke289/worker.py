# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Piotr
# This program comes with NO WARRANTY; see COPYING for license terms.
import queue
import threading
import time
import serial
from .protocol import ProtocolError
from .transport import Meter
from .storage import Store, CsvStore
from .memory import MemoryClient, MemoryCancelled


class Worker(threading.Thread):
    def __init__(self, port, database=None, interval=0.5, timeout=2, factory=Meter):
        super().__init__(daemon=True)
        self.port, self.database, self.interval, self.timeout = port, database, interval, timeout
        self.factory = factory
        self.stop_event = threading.Event()
        self.events = queue.Queue(maxsize=100)
        self.commands = queue.Queue()
        self.record_deadline = None
        self.store = None
        self.identity = None
        self.meter = None
        self.memory_cancel = threading.Event()

    def memory_request(self, operation, request=None):
        self.memory_cancel.clear()
        self.commands.put(('memory',operation,request))

    def _memory(self,operation,request):
        diagnostics=[]
        original_trace=None
        self.publish('memory_busy',True)
        try:
            if self.store is not None: raise ValueError('Zatrzymaj zapis na dysk przed odczytem pamięci')
            if self.meter is None: raise ValueError('Brak połączenia z miernikiem')
            original_trace=self.meter.trace
            def trace(direction,line):
                diagnostics.append({'direction':direction,'line':line})
                if len(diagnostics)>32: diagnostics.pop(0)
            self.meter.trace=trace
            client=MemoryClient(self.meter,
                cancel=lambda:self.memory_cancel.is_set() or self.stop_event.is_set(),
                progress=lambda done,total:self.publish('memory_progress',(done,total)))
            if operation=='list': result=client.list_items()
            elif operation=='download':
                result=client.download(request['kind'],request['index'],request.get('raw_hex'))
            else: raise ValueError('Nieznana operacja pamięci')
            self.publish('memory_result',{'operation':operation,'result':result,'identity':self.identity})
        except MemoryCancelled as e:
            self.publish('memory_error',{'message':str(e),'diagnostics':diagnostics})
        except Exception as e:
            self.publish('memory_error',{'message':str(e),'diagnostics':diagnostics})
            if isinstance(e,(ProtocolError,OSError,serial.SerialException)) and self.meter:
                self.meter.close()
                self.meter=None
        finally:
            if self.meter is not None and original_trace is not None: self.meter.trace=original_trace
            self.publish('memory_busy',False)

    def start_recording(self, path, format, duration=None):
        self.commands.put(('start', (path,duration), format))

    def stop_recording(self):
        self.commands.put(('stop', None, None))

    def publish(self, kind, data):
        try: self.events.put_nowait((kind, data))
        except queue.Full:
            self.events.get_nowait()
            self.events.put_nowait((kind, data))

    def _close_store(self):
        self.record_deadline = None
        store, self.store = self.store, None
        if store:
            store.close()

    def _record(self, kind, data):
        self._expire_recording()
        if self.store is None:
            return
        try:
            self.store.add(kind, data)
        except Exception as e:
            try: self._close_store()
            except Exception: pass
            self.publish('recording_error', f'Zapis zatrzymany: {e}. Podgląd nadal działa.')

    def _expire_recording(self):
        if self.record_deadline is not None and time.monotonic()>=self.record_deadline:
            try:
                self._close_store()
            except Exception as e:
                self.publish('recording_error',f'Błąd zamykania nagrania: {e}. Podgląd nadal działa.')
                return
            self.publish('recording',None)
            self.publish('recording_finished','Upłynął czas nagrania — plik zapisany, podgląd LIVE pozostaje aktywny.')

    def _commands(self):
        self._expire_recording()
        while not self.stop_event.is_set():
            try: action, path, format = self.commands.get_nowait()
            except queue.Empty: return
            if action=='memory':
                self._memory(path,format)
                continue
            try:
                if action == 'stop':
                    self._close_store()
                    self.publish('recording', None)
                elif action == 'start':
                    path,duration=path if isinstance(path,tuple) else (path,None)
                    if duration is not None and (type(duration) is not int or duration<=0):
                        raise ValueError('Czas nagrania musi być dodatnią liczbą sekund')
                    if self.store is not None:
                        raise ValueError('Najpierw zatrzymaj bieżący zapis')
                    if format not in {'CSV', 'SQLite'}:
                        raise ValueError('Nieobsługiwany format')
                    self.store = CsvStore(path) if format == 'CSV' else Store(path)
                    if self.identity:
                        self.store.add('identity', self.identity)
                    self.record_deadline=time.monotonic()+duration if duration else None
                    self.publish('recording', {'path': path, 'format': format, 'deadline':self.record_deadline})
            except Exception as e:
                try: self._close_store()
                except Exception: pass
                self.publish('recording_error', f'Nie udało się zmienić zapisu: {e}. Podgląd nadal działa.')

    def _wait(self, seconds):
        deadline = time.monotonic() + seconds
        while not self.stop_event.is_set():
            self._commands()
            remaining = deadline - time.monotonic()
            if remaining <= 0: break
            self.stop_event.wait(min(.1, remaining))

    def run(self):
        self.meter = None
        try:
            # Backward compatibility for explicit callers requesting a database.
            # The GUI never passes one: a new connection starts in preview only.
            if self.database:
                self.store = Store(self.database)
                self.publish('recording', {'path': self.database, 'format': 'SQLite'})
            def trace(direction, line):
                self._record('wire', {'direction': direction, 'line': line})
            backoff = max(3, self.timeout*2)
            while not self.stop_event.is_set():
                self._commands()
                try:
                    if self.meter is None:
                        self.publish('status', 'Łączenie…')
                        self.meter = self.factory(self.port, self.timeout, trace)
                        self.identity = self.meter.identify()
                        self._record('identity', self.identity)
                        self.publish('identity', self.identity)
                    started = time.monotonic()
                    snap = self.meter.snapshot()
                    self._record('snapshot', snap.as_dict())
                    self.publish('snapshot', snap)
                    backoff = max(3, self.timeout*2)
                    self._wait(max(0, self.interval-(time.monotonic()-started)))
                except (OSError, serial.SerialException, ProtocolError) as e:
                    message = f'{type(e).__name__}: {e}'
                    self._record('error', message)
                    self.publish('error', message + f' • ponowna próba za {backoff:g} s')
                    if self.meter:
                        self.meter.close()
                        self.meter = None
                    self._wait(backoff)
                    backoff = min(30, backoff*2)
        except Exception as e:
            self.publish('fatal', f'Zatrzymano połączenie: {type(e).__name__}: {e}')
        finally:
            if self.meter:
                try: self.meter.close()
                except OSError: pass
            try: self._close_store()
            except Exception as e: self.publish('recording_error', f'Błąd zamykania pliku: {e}')
            self.publish('recording', None)
            self.publish('stopped', '')
