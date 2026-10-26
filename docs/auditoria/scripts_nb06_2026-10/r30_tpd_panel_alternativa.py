# TPD del panel: el subtipo-mes sin dato propio (< 10 sucursales con los dos lados) hoy se mueve con los demás subtipos
# de su tipo. Alternativa: moverlo con la variación del MISMO subtipo en todas las sucursales (mismos productos, más
# sucursales), si ahí tiene dato propio en los dos meses. Recalcula tipo (promedio geométrico) y canasta (pesos ENGHo)
# desde TPD_subtipos y los compara con la serie del Excel (control: los meses sin cambios tienen que coincidir).
# Uso: python -I -X utf8 r30_tpd_panel_alternativa.py <carpeta de esperados (s17)>
import sys
from pathlib import Path

import numpy as np
import pandas as pd

pd.set_option('display.width', 250)
D = Path(sys.argv[1])
W = {'Fideos secos': 1.503, 'Galletitas dulces': 1.717, 'Galletitas saladas y crackers': 1.407,
     'Pan rallado y rebozador': 0.194, 'Cereales rellenos (almohaditas)': 0.181}
t = pd.read_csv(D / 'TPD_subtipos.csv')
t['mov'] = t['movido_con_los_demas'].astype(str).eq('True')
P = t[t['universo'] == 'panel balanceado'].pivot_table(index='mes', columns=['tipo', 'subtipo'], values='brecha_tpd')
M = t[t['universo'] == 'panel balanceado'].pivot_table(index='mes', columns=['tipo', 'subtipo'], values='mov', aggfunc='first')
T = t[t['universo'] == 'todas las sucursales'].pivot_table(index='mes', columns=['tipo', 'subtipo'], values='brecha_tpd')
MT = t[t['universo'] == 'todas las sucursales'].pivot_table(index='mes', columns=['tipo', 'subtipo'], values='mov', aggfunc='first')


def canasta(sub):
    lt = np.log1p(sub / 100).T.groupby(level='tipo').mean().T
    g = np.expm1(lt)
    w = pd.Series(W)[g.columns]
    return 100 * ((1 + g) * w).sum(axis=1) / w.sum() - 100, 100 * g


c0, g0 = canasta(P)
s = pd.read_csv(D / 'Serie_TPD.csv').set_index('mes')['brecha_canasta_tpd_panel']
print(f'control: canasta recalculada vs Excel, dif. máx. {float((c0 - s).abs().max()):.2e} pp')
A = P.copy()
meses = list(P.index)
cambios = []
for col in P.columns:
    for i, m in enumerate(meses):
        if not M.loc[m, col] or i == 0:
            continue
        prev = meses[i - 1]
        if col in T.columns and not MT.loc[m, col] and not MT.loc[prev, col]:
            nuevo = 100 * ((1 + A.loc[prev, col] / 100) * (1 + T.loc[m, col] / 100) / (1 + T.loc[prev, col] / 100) - 1)
            cambios.append((m, col[1], round(P.loc[m, col], 1), round(nuevo, 1)))
            A.loc[m, col] = nuevo
c1, g1 = canasta(A)
print('\nSubtipo-mes movidos del panel: hoy (con los demás de su tipo) -> con el mismo subtipo en todas las sucursales')
for x in cambios:
    print('  ', x)
d = pd.DataFrame({'canasta_hoy': c0, 'canasta_alt': c1, 'fideos_hoy': g0['Fideos secos'], 'fideos_alt': g1['Fideos secos'],
                  'dulces_hoy': g0['Galletitas dulces'], 'dulces_alt': g1['Galletitas dulces']}).round(1)
print('\nMeses que cambian:')
print(d[(d['canasta_hoy'] - d['canasta_alt']).abs() > 0.05].to_string())
print('\nPromedio por año (canasta, panel): hoy / alternativa')
print(pd.DataFrame({'hoy': c0.groupby(c0.index.str.slice(0, 4)).mean(), 'alt': c1.groupby(c1.index.str.slice(0, 4)).mean()}).round(1).T.to_string())
dv = lambda x: float(x.diff().std())
print(f'\nDesvío de la variación mensual de la canasta del panel: hoy {dv(c0):.1f} pp, alternativa {dv(c1):.1f} pp')
