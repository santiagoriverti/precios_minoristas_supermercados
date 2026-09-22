# -*- coding: utf-8 -*-
"""Test del cache POR MES de nb07 (v5.8).

Ejecuta el CODIGO REAL extraido de gen_nb07.py -no una copia- con `_leer_mes` y `_colapsar`
reemplazados por stubs sinteticos. Cubre lo que fallo el 2026-09-22 (la sesion de Colab murio
por RAM despues de leer los 32 meses y no quedo nada guardado):

  1. una corrida que se corta a mitad de la lectura deja guardados los meses ya leidos;
  2. la corrida siguiente retoma: lee SOLO los meses que faltan;
  3. el panel final es identico al de una corrida sin cortes (y al de USE_CACHE = False);
  4. las semanas cuyo mes dueno es el mes en curso no entran desde el cache;
  5. un mes sin datos se guarda igual (vacio) y no se vuelve a leer;
  6. TODAS las celdas de codigo del .ipynb generado compilan (la CELDA 13 llego a Colab con un
     print partido en dos lineas y habria cortado la corrida despues de la lectura larga).

    python test_cache_por_mes.py     -> RESULTADO: OK / FALLA
"""
import io, gc, os, pathlib, tempfile, datetime as _dt
import numpy as np, pandas as pd
from tqdm.auto import tqdm

SRC = pathlib.Path(__file__).with_name('gen_nb07.py')
src = io.open(SRC, encoding='utf-8').read()
i0 = src.index('import pyarrow as pa, pyarrow.parquet as pq, pyarrow.compute as pc')
i1 = src.index('_EAN_NAC.clear(); gc.collect()\n', i0) + len('_EAN_NAC.clear(); gc.collect()\n')
BLOQUE = src[i0:i1]
print(f'bloque extraido: {len(BLOQUE)} chars\n')

_SKR = ['id_comercio', 'id_bandera', 'id_sucursal']
DIA_CIERRE_SEMANA = 3
# El ultimo es el "mes en curso". 2024-03 termina en DOMINGO: sus ultimos dias caen en la semana que
# cierra el jueves 2024-04-04, cuyo mes dueno es 2024-04 -> el filtro del cache tiene que sacarlos.
MESES = [f'2023-{m:02d}' for m in range(1, 13)] + ['2024-01', '2024-02', '2024-03', '2024-04']
MES_VACIO = '2023-05'

def _semana_cierre(_d):
    _ahead = (DIA_CIERRE_SEMANA - _d.weekday()) % 7
    return (_d + _dt.timedelta(days=int(_ahead))).strftime('%Y-%m-%d')

def _mes_de_semana(_sem):
    _d = _dt.date.fromisoformat(_sem) - _dt.timedelta(days=3)
    return _d.strftime('%Y-%m')

def panel_mes(lbl):
    """Filas sintetico-deterministicas de un mes: 3 sucursales x 2 items x semanas del mes.
    Incluye los dias del mes que caen en una semana que cierra el mes SIGUIENTE."""
    if lbl == MES_VACIO:
        return None
    y, m = map(int, lbl.split('-'))
    d0 = _dt.date(y, m, 1)
    d1 = (_dt.date(y + (m == 12), m % 12 + 1, 1))
    sems = sorted({_semana_cierre(d0 + _dt.timedelta(days=k)) for k in range((d1 - d0).days)})
    rng = np.random.default_rng(int(y * 100 + m))
    filas = [dict(id_comercio='1', id_bandera='1', id_sucursal=str(s), semana=w, item=it,
                  price=float(rng.uniform(100, 200)))
             for s in range(3) for w in sems for it in ('7790001', 'Banana')]
    return pd.DataFrame(filas)

LEIDOS = []
CORTAR_EN = [None]

def _leer_mes(lbl):
    if CORTAR_EN[0] == lbl:
        raise MemoryError(f'corte simulado en {lbl}')
    LEIDOS.append(lbl)
    return panel_mes(lbl)

def _colapsar(df, lbl=''):
    if df is None:
        return None
    _EAN_NAC.append(df[df['item'] == 'Banana']
                    .assign(ean_norm='779BAN', p=lambda x: x['price'], n_suc=1)
                    [['item', 'ean_norm', 'semana', 'p', 'n_suc']])
    return df[_SKR + ['semana', 'item', 'price']]

def correr(cache_dir, use_cache, cortar_en=None):
    LEIDOS.clear(); CORTAR_EN[0] = cortar_en
    g = dict(pd=pd, np=np, os=os, gc=gc, tqdm=tqdm, _SKR=_SKR, _mes_de_semana=_mes_de_semana,
             _leer_mes=_leer_mes, _colapsar=_colapsar, _EAN_NAC=[], USE_CACHE=use_cache,
             _meses_disp=MESES, _mes_actual=MESES[-1],
             _cache_dir_sem=cache_dir / 'sem_k_v5', _cache_dir_ean=cache_dir / 'ean_k_v5')
    globals()['_EAN_NAC'] = g['_EAN_NAC']
    exec(BLOQUE, g)
    return g['_cache'], g['_ean_cerrados'], list(LEIDOS)

def norm(df):
    return df.sort_values(list(df.columns)).reset_index(drop=True)

fallas = []
def chequear(ok, msg):
    print(('  OK    ' if ok else '  FALLA ') + msg)
    if not ok:
        fallas.append(msg)

with tempfile.TemporaryDirectory() as tmp:
    tmp = pathlib.Path(tmp)
    cerrados = MESES[:-1]

    print('=== 1) corrida de referencia sin cache (USE_CACHE = False) ===')
    ref_sem, ref_ean, _ = correr(tmp / 'nocache', use_cache=False)
    chequear(len(ref_sem) > 0 and len(ref_ean) > 0, f'panel de referencia: {len(ref_sem)} filas, {len(ref_ean)} por EAN')
    _crudo = panel_mes(MESES[-2])
    chequear(_crudo['semana'].map(_mes_de_semana).eq(MESES[-1]).any(),
             f'el ultimo mes cerrado trae semanas del mes en curso (el caso existe en el test)')
    en_curso = ref_sem['semana'].map(_mes_de_semana).eq(MESES[-1]).sum()
    chequear(en_curso == 0, 'sin semanas del mes en curso en el panel de cerrados')

    print('\n=== 2) corrida que se CORTA en el octavo mes ===')
    try:
        correr(tmp, use_cache=True, cortar_en=cerrados[7])
        chequear(False, 'la corrida cortada deberia haber lanzado MemoryError')
    except MemoryError:
        pass
    guardados = sorted(p.stem for p in (tmp / 'sem_k_v5').glob('*.parquet'))
    chequear(guardados == cerrados[:7], f'meses guardados antes del corte: {guardados}')
    chequear(not list((tmp / 'sem_k_v5').glob('*.tmp')), 'sin temporales colgados')

    print('\n=== 3) corrida siguiente: retoma ===')
    sem, ean, leidos = correr(tmp, use_cache=True)
    chequear(leidos == cerrados[7:], f'lee solo los faltantes: {leidos}')
    chequear(norm(sem).equals(norm(ref_sem)), 'panel por sucursal identico al de referencia')
    chequear(norm(ean).equals(norm(ref_ean)), 'panel por EAN identico al de referencia')
    chequear(MES_VACIO in {p.stem for p in (tmp / 'sem_k_v5').glob('*.parquet')},
             f'el mes sin datos ({MES_VACIO}) quedo guardado vacio')

    print('\n=== 4) tercera corrida: todo desde cache ===')
    sem2, ean2, leidos2 = correr(tmp, use_cache=True)
    chequear(leidos2 == [], f'no relee nada: {leidos2}')
    chequear(norm(sem2).equals(norm(ref_sem)) and norm(ean2).equals(norm(ref_ean)), 'mismo panel')
    chequear(list(sem2.dtypes.astype(str)) == ['object'] * 5 + ['float64'], f'tipos: {list(sem2.dtypes.astype(str))}')

    print('\n=== 5) mes con `sem` y sin `ean` -> error explicito ===')
    (tmp / 'ean_k_v5' / '2023-03.parquet').unlink()
    try:
        correr(tmp, use_cache=True)
        chequear(False, 'deberia haber avisado del cache inconsistente')
    except RuntimeError as e:
        chequear('2023-03' in str(e), f'avisa: {str(e)[:70]}...')

print('\n=== 6) todas las celdas del notebook generado compilan ===')
import ast, json
_nb = json.load(io.open(SRC.with_name('07_evolucion_canastas_alternativas.ipynb'), encoding='utf-8'))
_n = 0
for _i, _c in enumerate(_nb['cells']):
    if _c['cell_type'] != 'code':
        continue
    _n += 1
    try:
        ast.parse(''.join(_c['source']))
    except SyntaxError as e:
        chequear(False, f'celda {_i}: {e}  (regenerar con gen_nb07.py y revisar saltos de linea)')
chequear(True, f'{_n} celdas de codigo revisadas')

print('\nRESULTADO:', 'OK' if not fallas else f'FALLA ({len(fallas)})')
