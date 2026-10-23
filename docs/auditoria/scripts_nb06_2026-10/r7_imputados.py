# Qué subtipo-mes se imputa en la serie mensual (todas y panel) y por cuántos meses seguidos; n por subtipo y mes.
# (Cálculo independiente de la regla de la CELDA 8; desde el 2026-10-23 el nb06 lo exporta en la hoja Imputaciones.)
# Uso: python -I -X utf8 r7_imputados.py <carpeta sim_final>
import sys
from pathlib import Path
import numpy as np
import pandas as pd
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 300); pd.set_option('display.max_columns', 40)
pd.set_option('future.no_silent_downcasting', True)
SIM = Path(sys.argv[1])
bt_sub = pd.read_parquet(SIM / 'sim_bt_sub.parquet')
_sk = ['id_comercio', 'id_bandera', 'id_sucursal']
nmes = bt_sub['mes'].nunique(); minm = int(round(0.7 * nmes))
pres = bt_sub.groupby(_sk + ['tipo', 'subtipo'])['mes'].nunique()
celdas = pres[pres >= minm].index
bt_bal = bt_sub[bt_sub.set_index(_sk + ['tipo', 'subtipo']).index.isin(celdas)]
for lab, df in (('todas', bt_sub), ('panel', bt_bal)):
    n = df.groupby(['tipo', 'subtipo', 'mes'])['suc_key'].nunique().rename('n').reset_index()
    n['med'] = n.groupby(['tipo', 'subtipo'])['n'].transform('median')
    n['falta'] = (n['n'] < 10) | (n['n'] < 0.5 * n['med'])
    meses = sorted(df['mes'].unique())
    grid = n[['tipo', 'subtipo']].drop_duplicates().merge(pd.DataFrame({'mes': meses}), how='cross')
    n = grid.merge(n, on=['tipo', 'subtipo', 'mes'], how='left')
    n['falta'] = n['falta'].fillna(True)
    print(f'\n=== {lab}: subtipo-mes imputados (rachas de meses seguidos)')
    for (t, s), g in n.sort_values('mes').groupby(['tipo', 'subtipo']):
        f = g['falta'].to_numpy(); m = g['mes'].to_numpy(); nn = g['n'].to_numpy(); md = g['med'].dropna().iloc[0] if g['med'].notna().any() else np.nan
        rachas, i = [], 0
        while i < len(f):
            if f[i]:
                j = i
                while j + 1 < len(f) and f[j + 1]:
                    j += 1
                rachas.append(f'{m[i]}→{m[j]} ({j - i + 1}m; n {"/".join(str(int(x)) if x == x else "0" for x in nn[i:j + 1][:8])})')
                i = j + 1
            else:
                i += 1
        if rachas:
            print(f'  [{t} / {s}] mediana n={md:.0f}: ' + '; '.join(rachas))
