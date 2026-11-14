"""Validación compartida y transacciones de las operaciones de la fase 2."""
import functools
import sqlite3
from datetime import date
from flask import abort, jsonify, redirect, request

DAYS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
EQUIPMENT = {'machine':'Máquina', 'cable':'Polea', 'barbell':'Barra', 'dumbbell':'Mancuernas', 'bodyweight':'Peso corporal', 'other':'Otro'}


def data():
    value = request.get_json() if request.is_json else request.form
    if not isinstance(value, dict) and not hasattr(value, 'getlist'):
        abort(400, 'Datos no válidos.')
    return value


def text(values, key, limit=500, required=False):
    value = values.get(key, '')
    if not isinstance(value, str):
        abort(400, 'Campo de texto no válido: ' + key)
    value = value.strip()
    if len(value) > limit or (required and not value):
        abort(400, 'Revisa el campo ' + key + '.')
    return value


def integer(value, minimum=0, maximum=10000):
    try:
        if isinstance(value, bool) or str(int(value)) != str(value):
            raise ValueError()
        value = int(value)
        if not minimum <= value <= maximum:
            raise ValueError()
        return value
    except (ValueError, TypeError):
        abort(400, 'Número fuera del intervalo permitido.')


def dates(values):
    start = text(values, 'date_from', 10, True)
    end = text(values, 'date_until', 10) or None
    for value in (start, end):
        if value:
            try:
                if date.fromisoformat(value).isoformat() != value:
                    raise ValueError()
            except ValueError:
                abort(400, 'Fecha no válida. Usa año-mes-día.')
    if end and end < start:
        abort(400, 'La fecha final debe ser igual o posterior a la inicial.')
    return start, end


def revision(row, values):
    if integer(values.get('revision'), 1, 10**9) != row['revision']:
        abort(409, 'Este registro ha cambiado en otra ventana. Recarga antes de guardar.')


def result(payload, location, status=200):
    return (jsonify(payload), status) if request.is_json else redirect(location, code=303)


def write(db):
    def decorate(fn):
        @functools.wraps(fn)
        def wrapped(*args, **kwargs):
            db().execute('BEGIN IMMEDIATE')
            try:
                response = fn(*args, **kwargs)
                db().commit()
                return response
            except sqlite3.IntegrityError:
                db().rollback()
                abort(409, 'Ese número de pegatina ya existe o hay una referencia en conflicto. Busca la máquina existente.')
            except Exception:
                db().rollback()
                raise
        return wrapped
    return decorate
