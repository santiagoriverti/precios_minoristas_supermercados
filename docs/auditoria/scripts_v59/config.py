# -*- coding: utf-8 -*-
"""Rutas de la auditoria de la corrida nb07 v5.9 (docs/AUDITORIA_2026-09-22_v59.md).

Se configuran por variables de entorno para que los scripts corran en cualquier PC:

    AUD_EXCEL   canastas_alternativas_YYYY-MM-DD.xlsx (salida del nb07)
    AUD_CACHE   carpeta _cache_nb07 del Drive, con sem_<key>_v5/ y ean_<key>_v5/ adentro
    AUD_INDEC   sh_ipc_precios_promedio.xls del INDEC (www.indec.gob.ar/ftp/cuadros/economia/)
    AUD_TRABAJO carpeta para los intermedios (default: _trabajo/ junto a estos scripts; no se versiona)
"""
import os, pathlib, sys

AQUI = pathlib.Path(__file__).resolve().parent
REPO = AQUI.parents[2]

def _ruta(var, obligatoria=True):
    v = os.environ.get(var, '')
    if not v and obligatoria:
        sys.exit(f'Falta la variable de entorno {var} (ver docstring de config.py)')
    return pathlib.Path(v) if v else None

EXCEL = _ruta('AUD_EXCEL')
CACHE = _ruta('AUD_CACHE', obligatoria=False)
INDEC = _ruta('AUD_INDEC', obligatoria=False)
TRABAJO = pathlib.Path(os.environ.get('AUD_TRABAJO', AQUI / '_trabajo'))
TRABAJO.mkdir(parents=True, exist_ok=True)
MAESTRO_SUC = REPO / 'data' / 'maestro_sucursales_completo.xlsx'

def carpeta_cache(prefijo):
    """sem_<key>_v5 o ean_<key>_v5 dentro de AUD_CACHE (la unica, o la mas reciente)."""
    if CACHE is None:
        sys.exit('Este script necesita AUD_CACHE (carpeta _cache_nb07 con sem_<key>_v5 y ean_<key>_v5)')
    c = sorted(CACHE.glob(f'{prefijo}_*_v5'), key=lambda p: p.stat().st_mtime)
    if not c:
        sys.exit(f'No hay {prefijo}_<key>_v5 dentro de {CACHE}')
    return c[-1]
