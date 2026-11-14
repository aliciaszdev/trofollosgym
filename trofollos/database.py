"""Copias SQLite consistentes; nunca sobrescribe archivos existentes."""
import argparse
import sqlite3
from pathlib import Path


def copy_database(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if not source.is_file():
        raise ValueError('La base de origen no existe')
    if source == destination:
        raise ValueError('Origen y destino deben ser distintos')
    # Exclusive creation avoids accidentally overwriting production or another backup.
    with destination.open('xb'):
        pass
    try:
        with sqlite3.connect(source.as_uri() + '?mode=ro', uri=True) as src:
            with sqlite3.connect(destination) as dst:
                src.backup(dst)
                if dst.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise ValueError('La comprobación de integridad ha fallado')
    except Exception:
        destination.unlink(missing_ok=True)
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['backup', 'restore'])
    parser.add_argument('--source', required=True)
    parser.add_argument('--destination', required=True)
    parser.add_argument('--confirm-restore')
    args = parser.parse_args()
    if args.action == 'restore' and args.confirm_restore != 'RESTAURAR':
        parser.error('Restaurar exige --confirm-restore RESTAURAR y servicios detenidos')
    copy_database(args.source, args.destination)
    print('Copia íntegra creada; destino no sobrescrito.')

if __name__ == '__main__':
    main()
