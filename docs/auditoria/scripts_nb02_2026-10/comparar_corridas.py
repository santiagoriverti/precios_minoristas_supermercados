# Compara dos canasta_analisis_YYYY-MM.xlsx del nb02 hoja por hoja: lista las hojas que cambian (celdas numericas y de
# texto distintas, o forma distinta) y compara Valores_Documento fila por fila (Seccion + Variable). Al final muestra
# la columna amba de Sucs_media y las primeras filas de Ranking_media de la corrida NUEVA.
# Uso: python -I docs/auditoria/scripts_nb02_2026-10/comparar_corridas.py <Excel nuevo> <Excel anterior o simulado>
# Resultado del 2026-10-16 (segunda corrida de oct-26 contra la primera con la CELDA 20 simulada): Valores_Documento
# identica salvo el rotulo del mes; solo cambian Ranking_* (vs_mediana_%, vs_prom_%) y Sucs_* (columna amba nueva).
import sys

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
pd.set_option('display.width', 250)
nuevo, viejo = sys.argv[1], sys.argv[2]
xn, xv = pd.ExcelFile(nuevo), pd.ExcelFile(viejo)
print('hojas nuevo:', len(xn.sheet_names), '| primera:', xn.sheet_names[0], '| ultima:', xn.sheet_names[-1])
print('solo en nuevo:', sorted(set(xn.sheet_names) - set(xv.sheet_names)),
      '| solo en anterior:', sorted(set(xv.sheet_names) - set(xn.sheet_names)))
for h in xn.sheet_names:
    if h not in xv.sheet_names:
        continue
    a, b = xn.parse(h, header=None), xv.parse(h, header=None)
    if a.shape != b.shape:
        print(f'  {h:28s} FORMA distinta {a.shape} vs {b.shape}')
        continue
    na, nb = a.apply(pd.to_numeric, errors='coerce'), b.apply(pd.to_numeric, errors='coerce')
    num = na.notna() & nb.notna()
    dif_num = (np.abs(na[num] - nb[num]) > 1e-6 * np.maximum(1, np.abs(nb[num]))).sum().sum()
    txt = ~num & ~(a.isna() & b.isna())
    dif_txt = (a[txt].astype(str) != b[txt].astype(str)).sum().sum()
    if dif_num or dif_txt:
        print(f'  {h:28s} difiere: {int(dif_num)} celdas numericas, {int(dif_txt)} de texto')
print('las hojas no listadas son identicas')

if 'Valores_Documento' in xn.sheet_names and 'Valores_Documento' in xv.sheet_names:
    v, w = xn.parse('Valores_Documento'), xv.parse('Valores_Documento')
    m = v.merge(w, on=['Seccion', 'Variable'], how='outer', suffixes=('_nuevo', '_anterior'), indicator=True)
    print('\nValores_Documento: filas nuevo', len(v), '| anterior', len(w), '|', m['_merge'].value_counts().to_dict())
    d = m[(m['_merge'] == 'both') & (m['Valor_LaTeX_nuevo'].astype(str) != m['Valor_LaTeX_anterior'].astype(str))]
    print('Valor_LaTeX distintos:', len(d))
    print(d[['Seccion', 'Variable', 'Valor_LaTeX_nuevo', 'Valor_LaTeX_anterior']].to_string())

if 'Sucs_media' in xn.sheet_names:
    s = xn.parse('Sucs_media')
    if 'amba' in s.columns:
        print('\nSucs_media amba:', int(s['amba'].sum()))
        print(pd.crosstab(s['PROVINCIA_NORM'].where(s['PROVINCIA_NORM'].isin(['CABA', 'Buenos Aires']), 'otra'),
                          s['amba']))
if 'Ranking_media' in xn.sheet_names:
    print(xn.parse('Ranking_media').head(4).to_string())
