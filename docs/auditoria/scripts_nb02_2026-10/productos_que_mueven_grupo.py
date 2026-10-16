# Que productos mueven la variacion mensual de un grupo (cadena, region, provincia, tipo) de la hoja
# analisis_detallado, leyendo el cache de la CELDA 19c (_cache/detalle_<clave>_v1.parquet: mediana por EAN, grupo y
# mes). Imprime los EANs ordenados por variacion entre <mes0> y <mes1>, con las observaciones de cada mes.
# Uso: python -I docs/auditoria/scripts_nb02_2026-10/productos_que_mueven_grupo.py <detalle_*.parquet> <dim> <grupo>
#        <mes0> <mes1>      p. ej.  ... detalle_ea281ee7_v1.parquet cadena Vea 2026-06 2026-07
# dim: nacional (grupo Total), region, provincia, cadena, tipo. El cache solo tiene meses CERRADOS.
# Resultado del 2026-10-16: Vea jun -> jul-26, 19 de 67 productos bajan mas de 5% (-10 a -28%) con ~3.000-4.700
# observaciones cada uno y siguen abajo en agosto: rebaja de precios de Vea, no un error de carga. Explica la caida
# de Cuyo y el Noroeste en jul-26 (Vea pesa ahi) y el rebote de oct-26 (Vea +4,3%, el mayor aporte por cadena).
import sys

import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
pd.set_option('display.width', 250)
parq, dim, grupo, m0, m1 = sys.argv[1:6]
d = pd.read_parquet(parq)
print('meses en el cache:', sorted(d['mes'].unique()))
s = d[(d['dim'] == dim) & (d['grupo'] == grupo) & d['mes'].isin([m0, m1])]
if s.empty:
    raise SystemExit(f'sin datos para {dim}/{grupo} en {m0}-{m1}; grupos de {dim}: '
                     f'{sorted(d.loc[d["dim"] == dim, "grupo"].unique())[:40]}')
p = s.pivot_table(index='ean_norm', columns='mes', values='mediana')
n = s.pivot_table(index='ean_norm', columns='mes', values='n_obs')
p['var_%'] = (p[m1] / p[m0] - 1) * 100
p[f'n_{m0}'], p[f'n_{m1}'] = n[m0], n[m1]
print(f'{dim}/{grupo}: {len(p)} EANs | bajan >5%: {(p["var_%"] < -5).sum()} | suben >5%: {(p["var_%"] > 5).sum()}')
print(p.sort_values('var_%').round(1).to_string())
