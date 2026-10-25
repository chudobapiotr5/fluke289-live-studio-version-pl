# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Piotr
# This program comes with NO WARRANTY; see COPYING for license terms.
import argparse
from . import __version__
from .about import build_information
import json
import sys
from .transport import Meter
from .storage import Store, export_csv
from serial.tools import list_ports

def main():
    parser = argparse.ArgumentParser(description='Fluke 289: GUI, diagnostyka i eksport CSV')
    parser.add_argument('--version',action='version',version='Fluke 289 Live Studio '+__version__+' | build '+build_information()['build_id'])
    commands = parser.add_subparsers(dest='command')
    commands.add_parser('ports')
    diag = commands.add_parser('diagnose')
    diag.add_argument('port')
    diag.add_argument('--timeout', type=float, default=2)
    diag.add_argument('--database', default='diagnostyka.sqlite3')
    exp = commands.add_parser('export')
    exp.add_argument('database')
    exp.add_argument('csv')
    args = parser.parse_args()
    if args.command == 'ports':
        ports = list(list_ports.comports())
        for p in ports: print(f'{p.device}\t{p.description}\t{p.hwid}')
        if not ports: print('Brak portów szeregowych.')
        return 0
    if args.command == 'export':
        export_csv(args.database, args.csv)
        print('Zapisano: '+args.csv)
        return 0
    if args.command == 'diagnose':
        if not 0.1 <= args.timeout <= 30: parser.error('Timeout: 0.1–30 s')
        store = Store(args.database)
        meter = None
        def trace(direction, line):
            print(direction, repr(line))
            store.add('wire', {'direction': direction, 'line': line})
        try:
            meter = Meter(args.port, args.timeout, trace)
            identity = meter.identify()
            store.add('identity', identity)
            snap = meter.snapshot()
            store.add('snapshot', snap.as_dict())
            print(json.dumps(snap.as_dict(), ensure_ascii=False, indent=2))
            print('OK: ID i QDDA. To nie potwierdza wszystkich pozycji pokrętła.')
            return 0
        except Exception as e:
            store.add('error', str(e))
            print(f'BŁĄD: {e}', file=sys.stderr)
            return 1
        finally:
            if meter: meter.close()
            store.close()
    from .gui import main as gui
    gui()
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
