# Compara dos salidas de simular_region_19b_19c.py (codigo viejo: region de la REGION del maestro; codigo nuevo:
# AMBA por coordenadas de la CELDA 7) y, opcionalmente, el cache de la 19c del codigo nuevo contra el de una corrida
# real de Colab (para validar que los datos locales reproducen la corrida en las dimensiones que no cambian).
# Uso: python -I docs/auditoria/scripts_nb02_2026-10/comparar_region_19b_19c.py <trabajo viejo> <trabajo nuevo>
#        [detalle_*_v1.parquet de la corrida real]
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
pd.set_option('display.width', 250)
pd.set_option('display.max_rows', 200)
V, N = Path(sys.argv[1]), Path(sys.argv[2])
REAL = Path(sys.argv[3]) if len(sys.argv) > 3 else None

# 1) Sucursales: region vieja x nueva
sv, sn = pd.read_parquet(V / 'atributos_sucursal.parquet'), pd.read_parquet(N / 'atributos_sucursal.parquet')
k = ['id_comercio', 'id_bandera', 'id_sucursal']
m = sv[k + ['cadena', 'provincia', 'region']].merge(sn[k + ['region']], on=k, suffixes=('_viejo', '_nuevo'))
print(f'1) sucursales del panel: {len(m):,}; cambian de region: {(m["region_viejo"] != m["region_nuevo"]).sum():,}')
print(pd.crosstab(m['region_viejo'], m['region_nuevo'], margins=True).to_string())
cam = m[m['region_viejo'] != m['region_nuevo']]
print('\n   las que cambian, por cadena y provincia:')
print(cam.groupby(['region_viejo', 'region_nuevo', 'cadena', 'provincia']).size().rename('sucursales')
      .reset_index().sort_values('sucursales', ascending=False).head(25).to_string(index=False))

# 2) Hoja analisis_detallado (formato largo): variacion % por fila y periodo
dv, dn = pd.read_parquet(V / 'detalle_long.parquet'), pd.read_parquet(N / 'detalle_long.parquet')
j = dv.merge(dn, on=['seccion', 'fila', 'periodo'], how='outer', suffixes=('_v', '_n'), indicator=True)
otras = j[(j['seccion'] != 'region') & (j['_merge'] == 'both')]
dif = otras[~np.isclose(otras['variacion_%_v'], otras['variacion_%_n'], equal_nan=True, rtol=0, atol=1e-9)
            | ~np.isclose(otras['indice_v'], otras['indice_n'], equal_nan=True, rtol=0, atol=1e-9)]
print(f'\n2) filas que no son region: {len(otras):,} celdas; distintas: {len(dif)} '
      f'(solo en una corrida: {(j.loc[j["seccion"] != "region", "_merge"] != "both").sum()})')
reg = j[j['seccion'] == 'region']
tabla = reg.pivot_table(index='fila', columns='periodo', values=['variacion_%_v', 'variacion_%_n'])
per = [p for p in sorted(reg['periodo'].unique()) if '-S' not in p]
print('\n   variacion % mensual por region (viejo / nuevo):')
for f in tabla.index:
    v = [tabla.loc[f].get(('variacion_%_v', p), np.nan) for p in per]
    n = [tabla.loc[f].get(('variacion_%_n', p), np.nan) for p in per]
    print(f'   {f:24s} ' + '  '.join(f'{p[2:]}: {a:+.2f}/{b:+.2f}' for p, a, b in zip(per, v, n)))
ind = reg[reg['periodo'] == per[-1]][['fila', 'indice_v', 'indice_n']]
print(f'\n   indice a {per[-1]} (base = mes anterior al primero = 100):')
print(ind.round(2).to_string(index=False))

# 3) Hoja Regiones de la 19b (mes en curso contra el anterior)
xv = next((V / 'out').glob('canasta_analisis_*.xlsx'))
xn = next((N / 'out').glob('canasta_analisis_*.xlsx'))
rv, rn = pd.read_excel(xv, sheet_name='Regiones'), pd.read_excel(xn, sheet_name='Regiones')
cols = ['region', 'sucursales', 'aporte_equiv_sobre_oficial_pp', 'variacion_%', 'var_mediana_grupo_%']
cols = [c for c in cols if c in rv.columns]
print('\n3) hoja Regiones de la 19b, viejo:')
print(rv[cols].round(3).to_string(index=False))
print('   nuevo:')
print(rn[cols].round(3).to_string(index=False))

# 4) Cache de la 19c nuevo contra el de la corrida real (dimensiones que no son region)
if REAL:
    cn = pd.read_parquet(next((N / 'cache').glob('detalle_*_v1.parquet')))
    cr = pd.read_parquet(REAL)
    meses = sorted(set(cn['mes']) & set(cr['mes']))
    kk = ['dim', 'grupo', 'ean_norm', 'mes']
    a = cn[cn['mes'].isin(meses)].merge(cr[cr['mes'].isin(meses)], on=kk, how='outer', suffixes=('_sim', '_real'),
                                        indicator=True)
    for dim in ['nacional', 'provincia', 'cadena', 'tipo', 'region']:
        x = a[a['dim'] == dim]
        ambos = x[x['_merge'] == 'both']
        ig = (np.isclose(ambos['mediana_sim'], ambos['mediana_real'], equal_nan=True)
              & (ambos['n_obs_sim'] == ambos['n_obs_real']))
        print(f'4) cache {dim:9s} meses {meses[0]}..{meses[-1]}: {len(ambos):,} celdas en ambos, {int((~ig).sum())} '
              f'distintas, {int((x["_merge"] != "both").sum())} solo en uno')
