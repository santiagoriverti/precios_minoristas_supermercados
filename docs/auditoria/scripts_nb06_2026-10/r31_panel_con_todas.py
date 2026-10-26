# Serie descriptiva del PANEL: el subtipo-mes con pocas sucursales hoy arrastra su último mes válido (V0). Variante V5:
# se mueve con la variación del MISMO subtipo en todas las sucursales (mediana de sus sucursales, con dato propio en
# los dos meses); si todas tampoco tiene dato, arrastra como hoy. Misma regla que la del nb06 (r6_variantes_imputacion).
# Uso: python -I -X utf8 r31_panel_con_todas.py <carpeta sim> <Excel de la simulación>
import sys
from pathlib import Path

import numpy as np
import pandas as pd

pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30)
SIM, XLS = Path(sys.argv[1]), Path(sys.argv[2])
MIN, FRAC, FRAC_PANEL = 10, 0.5, 0.7
bt = pd.read_parquet(SIM / 'sim_bt_sub.parquet')
pond = pd.read_excel(XLS, sheet_name='Ponderaciones')
W = dict(zip(pond['tipo'], pond['peso_en_la_canasta_pct'] / 100))
ORDEN = list(pond['tipo'])
_sk = ['id_comercio', 'id_bandera', 'id_sucursal']
pres = bt.groupby(_sk + ['tipo', 'subtipo'])['mes'].nunique()
celdas = pres[pres >= int(round(FRAC_PANEL * bt['mes'].nunique()))].index
bal = bt[bt.set_index(_sk + ['tipo', 'subtipo']).index.isin(celdas)]
MESES = sorted(bt['mes'].unique())


def sub_mensual(df):
    n = df.groupby(['mes', 'tipo', 'subtipo'])['suc_key'].nunique().rename('n').reset_index()
    ref = n.groupby(['tipo', 'subtipo'])['n'].transform('median')
    n['ok'] = (n['n'] >= MIN) & (n['n'] >= FRAC * ref)
    s = df.groupby(['mes', 'tipo', 'subtipo'])['brecha_pct'].median().rename('b').reset_index().merge(n)
    s['lb'] = np.where(s['ok'], np.log1p(s['b'] / 100), np.nan)
    grid = s[['tipo', 'subtipo']].drop_duplicates().merge(pd.DataFrame({'mes': MESES}), how='cross')
    s = grid.merge(s, on=['mes', 'tipo', 'subtipo'], how='left')
    return s.pivot_table(index='mes', columns=['tipo', 'subtipo'], values='lb', dropna=False).reindex(MESES)


def tipo_canasta(L):
    t = L.T.groupby(level='tipo').mean().T
    t = (np.expm1(t) * 100).reindex(columns=ORDEN)
    w = pd.Series(W).reindex(ORDEN)
    rel = 1 + t / 100
    return t, ((rel * w).sum(axis=1, min_count=1) / (rel.notna() * w).sum(axis=1) - 1) * 100


LT, LP = sub_mensual(bt), sub_mensual(bal)
V0 = LP.ffill()
V5 = LP.copy()
movidos = []
for col in LP.columns:
    for i, m in enumerate(MESES):
        if not np.isnan(LP.loc[m, col]) or i == 0 or np.isnan(V5.iloc[i - 1][col]):
            continue
        prev = MESES[i - 1]
        if col in LT.columns and not np.isnan(LT.loc[m, col]) and not np.isnan(LT.loc[prev, col]):
            V5.loc[m, col] = V5.loc[prev, col] + LT.loc[m, col] - LT.loc[prev, col]
            movidos.append((m, col[1]))
        else:
            V5.loc[m, col] = V5.loc[prev, col]
t0, c0 = tipo_canasta(V0)
t5, c5 = tipo_canasta(V5)
x = pd.read_excel(XLS, sheet_name='Serie_canasta_balanceada').set_index('mes')['brecha_canasta']
print(f'control V0 = Excel (Serie_canasta_balanceada): dif. máx. {(c0 - x).abs().max():.2e}')
print(f'Subtipo-mes del panel movidos con todas las sucursales: {len(movidos)}')
a = pd.DataFrame({'V0': c0.groupby(c0.index.str[:4]).mean(), 'V5': c5.groupby(c5.index.str[:4]).mean()}).round(1).T
print('\nCanasta del panel, promedio por año:'); print(a.to_string())
print(f'Desvío de la variación mensual: V0 {c0.diff().std():.1f} pp, V5 {c5.diff().std():.1f} pp')
d = pd.concat({'canasta_V0': c0, 'canasta_V5': c5, 'fideos_V0': t0['Fideos secos'], 'fideos_V5': t5['Fideos secos']},
              axis=1).round(1)
print('\nMeses con |dif.| > 1 pp en la canasta:')
print(d[(d['canasta_V0'] - d['canasta_V5']).abs() > 1].to_string())
fa = pd.DataFrame({'V0': t0['Fideos secos'].groupby(t0.index.str[:4]).mean(),
                   'V5': t5['Fideos secos'].groupby(t5.index.str[:4]).mean()}).round(1).T
print('\nFideos del panel, promedio por año:'); print(fa.to_string())
