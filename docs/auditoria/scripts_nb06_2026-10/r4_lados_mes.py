# Precio mediano de cada lado por subtipo y mes (entre sucursales con los dos lados) y variación mensual, desde
# sim_bt_sub.parquet; y $/100 g nacional por producto y mes desde sim_datos_dia.parquet, para un subtipo.
# Uso: python -I -X utf8 r4_lados_mes.py <carpeta sim_final> <subtipo> [desde AAAA-MM] [hasta AAAA-MM]
import sys
from pathlib import Path
import pandas as pd

pd.set_option('display.width', 250)
pd.set_option('display.max_columns', 60)
pd.set_option('display.max_rows', 500)
D = Path(sys.argv[1])
SUB = sys.argv[2]
DESDE = sys.argv[3] if len(sys.argv) > 3 else '2022-01'
HASTA = sys.argv[4] if len(sys.argv) > 4 else '2026-12'
b = pd.read_parquet(D / 'sim_bt_sub.parquet')
x = b[(b['subtipo'] == SUB) & (b['mes'] >= DESDE) & (b['mes'] <= HASTA)]
r = x.groupby('mes').agg(tacc=('tacc', 'median'), sin=('sin', 'median'), brecha=('brecha_pct', 'median'),
                         n=('brecha_pct', 'size'), n_tacc_prom=('n_tacc', 'mean'), n_sin_prom=('n_sin', 'mean'))
r['var_tacc_%'] = r['tacc'].pct_change() * 100
r['var_sin_%'] = r['sin'].pct_change() * 100
print(f'=== {SUB}: lados (mediana entre sucursales con los dos lados)')
print(r.round(2).to_string())

dd = pd.read_parquet(D / 'sim_datos_dia.parquet')
print('\ncolumnas datos_dia:', list(dd.columns), '| filas', len(dd))
if 'subtipo' in dd.columns:
    y = dd[(dd['subtipo'] == SUB) & (dd['mes'] >= DESDE) & (dd['mes'] <= HASTA)]
else:
    y = dd[(dd['mes'] >= DESDE) & (dd['mes'] <= HASTA)]
pcol = 'precio_100g' if 'precio_100g' in y.columns else [c for c in y.columns if '100' in c][0]
key = 'producto' if 'producto' in y.columns else 'ean_norm'
p = y.groupby([key, 'mes'])[pcol].median().unstack('mes')
n = y.groupby([key, 'mes'])[pcol].size().unstack('mes')
print(f'\n$/100 g nacional (mediana entre sucursales) por {key}:')
print(p.round(1).to_string())
print('\nsucursales por producto y mes:')
print(n.to_string())
