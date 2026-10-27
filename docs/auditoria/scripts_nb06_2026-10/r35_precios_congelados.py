# Precios congelados: una empresa repite el mismo precio de un código mes tras mes mientras el de referencia sube (en
# 2023-2024 la inflación fue de 10-25% por mes). Sobre los paneles de datos/ de una simulación.
# Uso: python -I -X utf8 r35_precios_congelados.py <carpeta datos> [subida mínima, p. ej. 0.30] [meses mínimos de la racha, p. ej. 6]
# (el nb06 usa 0.5 y 6: SUBA_CONGELADO y MESES_CONGELADO; con 0.30 y 2 aparecen los rezagos de un mes de dic-2023)
import sys
from pathlib import Path
import numpy as np
import pandas as pd
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30); pd.set_option('display.max_rows', 200)
D = Path(sys.argv[1])
SUBA = float(sys.argv[2]) if len(sys.argv) > 2 else 0.30
MIN_M = int(sys.argv[3]) if len(sys.argv) > 3 else 2
p = pd.read_parquet(D / 'panel_producto_sucursal_mes.parquet')
s = pd.read_csv(D / 'sucursales.csv', dtype=str)[['suc_key', 'empresa']]
p = p.merge(s, on='suc_key', how='left')
# precio de la empresa para el código y mes (mediana entre sus sucursales) y la referencia: la mediana del mismo código en
# las OTRAS empresas; si ninguna otra lo tiene ese mes, el índice del tipo y lado (mediana de los relativos mes a mes)
e = p.groupby(['empresa', 'ean_norm', 'tipo', 'rol', 'mes'], as_index=False).agg(pe=('precio', 'median'), n=('precio', 'size'))
meses = sorted(e['mes'].unique()); im = {m: i for i, m in enumerate(meses)}
e['t'] = e['mes'].map(im)
# índice del tipo y lado: mediana entre códigos y empresas del cambio mensual del precio (log), encadenado
e = e.sort_values(['empresa', 'ean_norm', 't'])
e['dl'] = np.where(e.groupby(['empresa', 'ean_norm'])['t'].diff() == 1, np.log(e['pe']).groupby([e['empresa'], e['ean_norm']]).diff(), np.nan)
idx = e.groupby(['tipo', 'rol', 't'])['dl'].median().unstack(['tipo', 'rol']).reindex(range(len(meses))).fillna(0).cumsum()
# rachas de precio idéntico (|log| < 0.5%) en meses seguidos
filas = []
for (em, ea), g in e.groupby(['empresa', 'ean_norm']):
    t, lp = g['t'].to_numpy(), np.log(g['pe'].to_numpy())
    tp, rl = g['tipo'].iloc[0], g['rol'].iloc[0]
    i = 0
    while i < len(t):
        j = i
        while j + 1 < len(t) and t[j + 1] == t[j] + 1 and abs(lp[j + 1] - lp[i]) < 0.005:
            j += 1
        if j - i + 1 >= MIN_M:
            ref = idx[(tp, rl)].to_numpy()
            suba = np.expm1(ref[t[i:j + 1]] - ref[t[i]])
            stale = suba > SUBA
            if stale.any():
                filas.append({'empresa': em, 'ean': ea, 'tipo': tp, 'rol': rl, 'desde': meses[t[i]], 'hasta': meses[t[j]],
                              'meses': j - i + 1, 'meses_congelados': int(stale.sum()), 'suba_ref_pct': 100 * suba[-1],
                              'obs_congeladas': int(g['n'].to_numpy()[i:j + 1][stale].sum()), 'precio': float(np.exp(lp[i]))})
        i = j + 1
r = pd.DataFrame(filas)
print(f'Rachas con el precio repetido mientras el índice del tipo y lado sube > {100 * SUBA:.0f}%: {len(r)}')
if len(r):
    print(r.groupby('empresa').agg(rachas=('ean', 'size'), codigos=('ean', 'nunique'), meses=('meses_congelados', 'sum'),
                                   obs=('obs_congeladas', 'sum')).sort_values('obs', ascending=False).to_string())
    print(f'obs congeladas: {r["obs_congeladas"].sum():,} de {len(p):,} ({100 * r["obs_congeladas"].sum() / len(p):.2f}%)')
    print(r.sort_values('obs_congeladas', ascending=False).head(40).round(1).to_string(index=False))
