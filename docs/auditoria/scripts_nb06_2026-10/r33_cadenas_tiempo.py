# Análisis de expertos (2026-10-27, tarde): cadenas, surtido y tiempo sobre los paneles de datos/ de una simulación.
# 1) ¿Cuánto de la variación de la brecha entre sucursales es de la cadena? (precios fijados por cadena: inferencia)
# 2) Surtido: qué cadenas venden cada producto de la canasta, y cómo cambia por año
# 3) Composición de las sucursal-meses con pares por cadena y año (lo que mueve la mediana nacional)
# Uso: python -I -X utf8 r33_cadenas_tiempo.py <carpeta datos de la simulación>
import sys
from pathlib import Path
import numpy as np
import pandas as pd
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30); pd.set_option('display.max_rows', 200)
pd.set_option('display.max_colwidth', 60)
D = Path(sys.argv[1])
S = pd.read_csv(D / 'sucursales.csv', dtype={'suc_key': str, 'departamento_id': str})
B = pd.read_parquet(D / 'panel_sucursal_mes_subtipo.parquet')
print(B.columns.tolist())
P = pd.read_parquet(D / 'panel_producto_sucursal_mes.parquet').merge(S[['suc_key', 'empresa']], on='suc_key')
B['anio'] = B['mes'].str[:4]
U = sorted(B['mes'].unique())[-12:]

# 1) varianza de log(1 + brecha) por subtipo y mes: entre empresas vs dentro de empresas (últimos 12 meses)
x = B[B['mes'].isin(U)].copy()
x['y'] = np.log1p(x['brecha_pct'] / 100)
x['dev'] = x['y'] - x.groupby(['mes', 'subtipo'])['y'].transform('mean')
emp_mean = x.groupby(['mes', 'subtipo', 'empresa'])['dev'].transform('mean')
tot = (x['dev'] ** 2).sum(); entre = (emp_mean ** 2).sum()
print(f'\n1) Brecha por sucursal-mes-subtipo, últimos 12 meses: la empresa explica {100 * entre / tot:.1f}% de la varianza '
      f'(después de sacar subtipo y mes); dentro de cada empresa queda {100 * (1 - entre / tot):.1f}%')
w = (x.assign(r2=lambda d: d.groupby(['mes', 'subtipo', 'empresa'])['dev'].transform('mean'))
     .groupby('subtipo').apply(lambda g: pd.Series({'R2_empresa_pct': 100 * (g['r2'] ** 2).sum() / (g['dev'] ** 2).sum(),
                                                       'obs': len(g), 'empresas': g['empresa'].nunique()}),
                                include_groups=False))
print(w.round(1).to_string())
# dentro de cada empresa, ¿el precio de un producto es el mismo en todas sus sucursales?
q = P[P['mes'].isin(U)]
cv = (q.groupby(['empresa', 'ean_norm', 'mes'])['precio'].agg(['std', 'mean', 'size']).query('size >= 5'))
cv['cv'] = cv['std'] / cv['mean']
print('\nDispersión del precio de un mismo código entre las sucursales de una empresa (coef. de variación, mediana):')
print(cv.groupby(level='empresa')['cv'].median().mul(100).round(1).sort_values().to_string())

# 2) surtido: % de las sucursal-meses de cada empresa con el producto (últimos 12 meses), sin TACC
q = P[P['mes'].isin(U)]
sm = q.groupby('empresa')[['suc_key', 'mes']].apply(lambda d: len(d.drop_duplicates())).rename('suc_meses')
pr = q.groupby(['empresa', 'rol', 'subtipo', 'producto'])[['suc_key', 'mes']].apply(lambda d: len(d.drop_duplicates()))
pr = (pr / pr.index.get_level_values('empresa').map(sm)).mul(100).rename('pct').reset_index()
grandes = sm[sm >= 1000].index
t = pr[pr['empresa'].isin(grandes) & (pr['rol'] == 'sin')].pivot_table(index=['subtipo', 'producto'], columns='empresa',
                                                                         values='pct').fillna(0)
print('\n2) Sin TACC: % de las sucursal-meses de cada empresa (últimos 12 meses) que lo tienen')
print(t.round(0).astype(int).to_string())

# 3) composición de las sucursal-meses con los dos lados, por empresa y año (todas las sucursales)
c = (B.groupby(['anio', 'empresa'])['suc_key'].size().unstack('empresa').fillna(0))
c = c.div(c.sum(axis=1), axis=0).mul(100)
print('\n3) % de las sucursal-mes-subtipo con los dos lados, por empresa y año')
print(c.loc[:, c.max() > 2].round(1).to_string())
