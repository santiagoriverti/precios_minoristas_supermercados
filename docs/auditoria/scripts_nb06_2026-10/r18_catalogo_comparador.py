# Revisión metodológica del nb06 (3): catálogo del SEPA del 22/10/2026. (a) En DIA, ¿qué fideos con TACC se venden y a
# qué precio, frente a las marcas de primera línea del lado con TACC de la canasta? (b) ¿Hay marcas propias sin TACC
# en fideos y galletitas? (c) ¿Qué parte de la oferta sin TACC (presencia en sucursales) cubre la canasta fija?
# Uso: python -I -X utf8 r18_catalogo_comparador.py <catalogo parquet> <canasta_fija_2022_2026.csv>
import re
import sys

import numpy as np
import pandas as pd

pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30); pd.set_option('display.max_rows', 200)
pd.set_option('display.max_colwidth', 60)
cat = pd.read_parquet(sys.argv[1])
can = pd.read_csv(sys.argv[2], dtype={'ean': str})
cat['desc'] = cat['productos_descripcion'].astype(str).str.lower()
cat['marca'] = cat['productos_marca'].astype(str).str.upper().str.strip()
um = cat['productos_unidad_medida_presentacion'].astype(str).str.lower().str.strip()
cant = pd.to_numeric(cat['productos_cantidad_presentacion'], errors='coerce')
gr = np.where(um.isin(['gr', 'g', 'grm', 'grs']), cant, np.where(um.isin(['kg', 'kgm', 'kgs']), cant * 1000, np.nan))
cat['p100'] = pd.to_numeric(cat['precio'], errors='coerce') / gr * 100
cat['ean'] = cat['id_producto'].astype(str).str.lstrip('0')
sin = cat['desc'].str.contains(r'sin tacc|sin gluten|s/tacc|libre de gluten')
fideo = cat['desc'].str.contains(r'fideo|spaghetti|tallarin|mostachol|tirabuz|fusilli|penne|codito|mo[nñ]o')
galle = cat['desc'].str.contains(r'galletit|galleta|cracker')
dia = cat['id_comercio'].astype(str) == '15'
canasta = set(can['ean'].str.lstrip('0'))
con_can = set(can.loc[can['lado'] == 'tacc', 'ean'].str.lstrip('0'))

print('=== (a) Fideos secos con TACC en DIA: marcas, sucursales y $/100 g (22/10) ===')
x = cat[dia & fideo & ~sin & cat['p100'].between(20, 5000)]
r = x.groupby('marca').agg(eans=('ean', 'nunique'), sucursales=('id_sucursal', 'nunique'), p100=('p100', 'median'),
                           en_canasta=('ean', lambda e: int(len(set(e) & con_can))))
print(r.sort_values('sucursales', ascending=False).head(12).round(0).to_string())
todos = cat[fideo & ~sin & cat['p100'].between(20, 5000)]
print(f'   precio mediano de los fideos con TACC de la canasta (todas las cadenas): '
      f'${todos[todos["ean"].isin(con_can)]["p100"].median():,.0f}/100 g')

print('\n=== (b) Marcas de los productos sin TACC de fideos y galletitas (presencia en sucursales, todas las cadenas) ===')
for nombre, m in (('fideos', fideo), ('galletitas', galle)):
    y = cat[sin & m & cat['p100'].between(20, 20000)]
    r = y.groupby('marca').agg(eans=('ean', 'nunique'), sucursal_producto=('id_sucursal', 'size'),
                               p100=('p100', 'median'), en_canasta=('ean', lambda e: int(len(set(e) & canasta))))
    r['pct_presencia'] = 100 * r['sucursal_producto'] / r['sucursal_producto'].sum()
    print(f'-- {nombre} sin TACC: {y["ean"].nunique()} códigos, {len(y):,} sucursal-producto')
    print(r.sort_values('sucursal_producto', ascending=False).head(15).round(1).to_string())
    cub = y['ean'].isin(canasta).mean() * 100
    print(f'   la canasta fija cubre el {cub:.0f}% de la presencia (sucursal-producto) de {nombre} sin TACC del 22/10')
