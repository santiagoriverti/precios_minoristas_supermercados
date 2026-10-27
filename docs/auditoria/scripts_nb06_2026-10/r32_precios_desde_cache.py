# Precio mensual por sucursal x EAN para s10 y s12 (formato de s8: id_comercio, id_bandera, id_sucursal, ean, precio_mediana, dias,
# mes) tomado del caché del nb06 de una lectura del superconjunto (la columna precio del caché es la mediana exacta de
# los días, igual a la de s8: verificado en 97.526 pares de feb-2023). Junta en <salida> los archivos de una carpeta de
# s8 existente (p. ej. precios_mes_2) y las filas de los EANs pedidos que no están en ninguna extracción.
# Uso: python -I -X utf8 r32_precios_desde_cache.py <caché brecha_v3_xxx> <precios_mes_2> <salida> <ean> [<ean> ...]
import sys
from pathlib import Path

import pandas as pd

CACHE, P2, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
EANS = set(sys.argv[4:])
OUT.mkdir(parents=True, exist_ok=True)
cols = ['id_comercio', 'id_bandera', 'id_sucursal', 'ean', 'precio_mediana', 'dias', 'mes']
n = 0
meses = sorted({f.stem for f in CACHE.glob('????-??.parquet')} | {f.stem for f in P2.glob('????-??.parquet')})
for m in meses:
    partes = []
    if (P2 / f'{m}.parquet').exists():
        partes.append(pd.read_parquet(P2 / f'{m}.parquet'))
    if (CACHE / f'{m}.parquet').exists():
        d = pd.read_parquet(CACHE / f'{m}.parquet')
        d = d[d['ean_norm'].isin(EANS)].rename(columns={'ean_norm': 'ean', 'precio': 'precio_mediana'})
        if len(d):
            partes.append(d[cols])
            n += len(d)
    if partes:
        pd.concat(partes, ignore_index=True).to_parquet(OUT / f'{m}.parquet', index=False)
print(f'{len(meses)} meses -> {OUT} | filas nuevas de {sorted(EANS)}: {n:,}')
