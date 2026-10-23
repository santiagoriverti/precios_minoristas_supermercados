# Por qué la serie TPD de galletitas saladas queda debajo de la descriptiva desde 2024 (BRECHA_CELIACA §14.12), en las
# celdas del panel balanceado: (1) brecha por sucursal-mes de cada subtipo por año, mediana (lo que toma la descriptiva)
# contra promedio geométrico (lo que promedia la TPD); (2) composición de cada lado: % de las observaciones de cada
# producto por año, junto a su nivel estimado por la TPD (hoja TPD_productos: en el mes base, frente al promedio de los
# con TACC del subtipo).
# Uso: python -I -X utf8 r11_saladas_composicion.py <carpeta de la simulación (s11)> <brecha_celiaca_AAAA-MM.xlsx de esa simulación> [tipo]
import sys
from pathlib import Path
import numpy as np
import pandas as pd

pd.set_option('display.width', 250); pd.set_option('display.max_columns', 40); pd.set_option('display.max_rows', 200)
SIM, XLS = Path(sys.argv[1]), Path(sys.argv[2])
TIPO = sys.argv[3] if len(sys.argv) > 3 else 'Galletitas saladas y crackers'
sk = ['id_comercio', 'id_bandera', 'id_sucursal']
# celdas del panel balanceado, como la CELDA 8 (sucursal × subtipo con los dos lados en >= 70% de los meses)
bs = pd.read_parquet(SIM / 'sim_bt_sub.parquet', columns=['suc_key', 'tipo', 'subtipo', 'mes', 'brecha_pct'])
pres = bs.groupby(['suc_key', 'tipo', 'subtipo'])['mes'].nunique()
cel = pres[pres >= max(1, int(round(0.7 * bs['mes'].nunique())))].reset_index()[['suc_key', 'tipo', 'subtipo']]
cel = cel[cel['tipo'] == TIPO]
b = bs.merge(cel, on=['suc_key', 'tipo', 'subtipo'])
b['anio'] = b['mes'].str[:4]
r = b.groupby(['subtipo', 'anio'])['brecha_pct'].agg(
    mediana='median', promedio_geometrico=lambda x: 100 * np.expm1(np.log1p(x / 100).mean()), sucursal_mes='size')
print(f'=== {TIPO}, celdas del panel: brecha por sucursal-mes (%), mediana y promedio geométrico por año')
print(r.round(1).to_string())
dd = pd.read_parquet(SIM / 'sim_datos_dia.parquet', columns=sk + ['mes', 'tipo', 'subtipo', 'rol', 'producto', 'precio_100'])
dd = dd[dd['tipo'] == TIPO]
sg = pd.read_parquet(SIM / 'sim_suc_geo.parquet', columns=sk + ['suc_key'])
pt = dd.merge(sg, on=sk).groupby(['suc_key', 'mes', 'subtipo', 'rol', 'producto'], as_index=False)['precio_100'].median()
pt = pt.merge(cel[['suc_key', 'subtipo']], on=['suc_key', 'subtipo'])
pt['anio'] = pt['mes'].str[:4]
prod = pd.read_excel(XLS, sheet_name='TPD_productos', dtype={'producto': str})
prod = prod[(prod['universo'] == 'panel balanceado') & (prod['tipo'] == TIPO)]
niv = prod.set_index('producto')[['descripcion', 'nivel_vs_con_tacc_subtipo_pct', 'peso_en_el_nivel']]
for sub, d in pt.groupby('subtipo'):
    for lado in ('sin', 'tacc'):
        x = d[d['rol'] == lado]
        sh = (x.groupby(['anio', 'producto']).size() / x.groupby('anio').size()).unstack('anio').fillna(0) * 100
        sh = sh.join(niv, how='left').sort_values('nivel_vs_con_tacc_subtipo_pct')
        print(f'\n=== {sub} / {"sin TACC" if lado == "sin" else "con TACC"}: % de las observaciones del lado por año '
              '(celdas del panel) y nivel TPD del producto')
        print(sh.round(1).to_string())
