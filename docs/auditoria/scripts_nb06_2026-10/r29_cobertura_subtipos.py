# Cobertura de cada subtipo en la simulación (sucursales con los dos lados por mes, mediana por año) y, en el SEPA
# diario del 22/10, en cuántas sucursales del sin TACC de un subtipo está cada candidato con TACC (¿el comparador
# elegido está donde está el sin TACC?).
# Uso: python -I -X utf8 r29_cobertura_subtipos.py <carpeta sim> <cat_20261022.parquet del SEPA diario>
import sys
from pathlib import Path

import pandas as pd

pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30)
SIM, CAT = Path(sys.argv[1]), sys.argv[2]
b = pd.read_parquet(SIM / 'sim_bt_sub.parquet', columns=['mes', 'subtipo', 'suc_key'])
n = b.groupby(['subtipo', 'mes'])['suc_key'].nunique().unstack('subtipo')
n['anio'] = n.index.str.slice(0, 4)
print('Sucursales con los dos lados por mes (mediana de cada año):')
print(n.groupby('anio').median().round(0).astype(int).T.to_string())
cat = pd.read_parquet(CAT, columns=['id_comercio', 'id_bandera', 'id_sucursal', 'id_producto', 'productos_descripcion'])
cat['ean'] = cat['id_producto'].astype(str).str.lstrip('0')
cat['suc'] = cat['id_comercio'].astype(str) + '|' + cat['id_bandera'].astype(str) + '|' + cat['id_sucursal'].astype(str)
GRUPOS = {
    'Con chips: Smams chips 150 g': ('7798181511004', {
        'Par Nor Suavecitas 140 g (canasta)': '7791324156926', 'Pepitos 119 g': '7622201735906',
        'Pepitos 357 g': '7622201735883', 'Toddy chips 126 g (nuevo)': '7790380023432',
        'Toddy chips 126 g (viejo)': '7790310982846'}),
    'Obleas: Santa María limón 90 g': ('7798079230833', {
        'Opera 220 g (canasta)': '7790040008175', 'Opera rellena 92 g': '77903518', 'Opera rellena 55 g': '77903501'}),
    'Pepas: Smams membrillo 150 g': ('7798181510786', {
        'Trío pepas 320 g (canasta)': '7791787100924', 'Trío pepas alemanas 300 g': '7791787100719'}),
}
for g, (sin, cands) in GRUPOS.items():
    s = set(cat.loc[cat['ean'] == sin, 'suc'])
    print(f'\n{g}: {len(s)} sucursales el 22/10')
    for nom, e in cands.items():
        c = set(cat.loc[cat['ean'] == e, 'suc'])
        print(f'   {nom:38s} en {len(c):5d} sucursales; junto al sin TACC en {len(s & c):5d}')
