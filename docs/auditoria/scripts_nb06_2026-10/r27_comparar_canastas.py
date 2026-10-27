# Brecha con varias canastas (CSV de s10) con el estimador simplificado de r26_alternativas.py (mismo nb06 sin la
# imputación de subtipos ni el panel): por subtipo, tipo y canasta, últimos 12 meses, 2022 y todo el período, y
# sucursal-meses con los dos lados. Uso:
#   python -I -X utf8 r27_comparar_canastas.py <precios_mes> <precios_mes_2> <carpeta simulación> <salida.csv>
#                                            nombre=canasta.csv [nombre=canasta.csv ...] [nombre=canasta.csv+ean,ean]
# "canasta.csv+e1,e2" agrega a esa canasta los códigos e1, e2 tomados de la canasta de referencia (la primera).
import sys
from pathlib import Path

import numpy as np
import pandas as pd

pd.set_option('display.width', 250); pd.set_option('display.max_columns', 40)
D1, D2, SIM, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4]
W = {'Fideos secos': 1.503, 'Galletitas dulces': 1.717, 'Galletitas saladas y crackers': 1.407,
     'Pan rallado y rebozador': 0.194, 'Cereales rellenos (almohaditas)': 0.181}
K = ['id_comercio', 'id_bandera', 'id_sucursal', 'mes']
COLS = ['tipo', 'lado', 'ean', 'producto', 'subtipo', 'gramos', 'desde', 'hasta']


def leer(path):
    b = pd.read_csv(path, dtype={'ean': str, 'desde': str, 'hasta': str})
    if 'linea' in b.columns:   # las variantes de una línea son un producto (s10, desde el 2026-10-26)
        b['producto'] = b['linea'].fillna(b['producto'])
    b = b[COLS].copy()
    b['lado'] = b['lado'].map({'tacc': 'tacc', 'sin_tacc': 'sin'})
    return b


canastas, ref = {}, None
for arg in sys.argv[5:]:
    nombre, spec = arg.split('=', 1)
    path, _, extra = spec.partition('+')
    b = leer(path)
    if ref is None:
        ref = b
    if extra:
        b = pd.concat([b, ref[ref['ean'].isin(extra.split(','))]], ignore_index=True)
    canastas[nombre] = b
EANS = sorted(set(pd.concat(canastas.values())['ean']))
fs = sorted(D1.glob('*.parquet')) + sorted(D2.glob('*.parquet'))
P = pd.concat([pd.read_parquet(f, columns=K[:3] + ['ean', 'mes', 'precio_mediana'], filters=[('ean', 'in', EANS)])
               for f in fs], ignore_index=True)
P = P[~P['id_comercio'].isin({'23', '24'})].drop_duplicates(K[:3] + ['ean', 'mes'])
P = P.merge(pd.read_parquet(SIM / 'sim_suc_geo.parquet')[K[:3]].drop_duplicates(), on=K[:3])
ult = ['2025-11', '2025-12'] + [f'2026-{i:02d}' for i in range(1, 11)]


def calcular(spec):
    x = P.merge(spec, on='ean')
    ok = (x['desde'].isna() | (x['mes'] >= x['desde'].fillna(''))) & (x['hasta'].isna() | (x['mes'] <= x['hasta'].fillna('9999')))
    x = x[ok].copy()
    x['p100'] = x['precio_mediana'] / x['gramos'].astype(float) * 100
    pp = x.groupby(K + ['tipo', 'subtipo', 'lado', 'producto'])['p100'].median()
    bs = pp.groupby(level=K + ['tipo', 'subtipo', 'lado']).median().unstack('lado').dropna().reset_index()
    bs['brecha'] = bs['sin'] / bs['tacc'] - 1
    m = bs.groupby(['mes', 'tipo', 'subtipo']).agg(g=('brecha', 'median'), n=('brecha', 'size')).reset_index()
    m = m[m['n'] >= 10]
    t = m.assign(lg=np.log1p(m['g'])).groupby(['mes', 'tipo'])['lg'].mean().pipe(np.expm1).rename('g').reset_index()
    t['w'] = t['tipo'].map(W)
    c = t.groupby('mes').apply(lambda d: (d['w'] * (1 + d['g'])).sum() / d['w'].sum() - 1, include_groups=False)
    r = {'canasta_ult12': 100 * c[c.index.isin(ult)].mean(), 'canasta_2022': 100 * c[c.index.str.startswith('2022')].mean(),
         'canasta_2024': 100 * c[c.index.str.startswith('2024')].mean(), 'canasta_todo': 100 * c.mean()}
    for tp in W:
        tt = t[t['tipo'] == tp]
        r[f'tipo:{tp[:16]}'] = 100 * tt[tt['mes'].isin(ult)]['g'].mean()
    for st, g in m.groupby('subtipo'):
        r[f'sub:{st[:24]}'] = 100 * g[g['mes'].isin(ult)]['g'].mean()
    for st, g in bs.groupby('subtipo'):
        r[f'n_ult12:{st[:24]}'] = int(g['mes'].isin(ult).sum())
        r[f'n_todo:{st[:24]}'] = int(len(g))
    return r


R = pd.DataFrame({k: calcular(v) for k, v in canastas.items()})
R.round(1).to_csv(OUT)
print(R.round(1).to_string())
