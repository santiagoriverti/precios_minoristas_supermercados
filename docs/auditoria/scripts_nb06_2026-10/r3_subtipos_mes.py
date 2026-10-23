# Serie mensual por subtipo (mediana entre sucursales de la brecha sucursal x mes x subtipo) desde sim_bt_sub.parquet
# de la simulación del nb06 (= corrida de Colab). Muestra también precios medianos de cada lado y sucursales.
# Uso: python -I -X utf8 r3_subtipos_mes.py <carpeta sim_final> [tipo ...]
import sys
from pathlib import Path
import pandas as pd

pd.set_option('display.width', 250)
pd.set_option('display.max_columns', 60)
pd.set_option('display.max_rows', 500)
D = Path(sys.argv[1])
b = pd.read_parquet(D / 'sim_bt_sub.parquet')
print('columnas bt_sub:', list(b.columns), '| filas', len(b))
print(b.head(3).to_string())
tipos = sys.argv[2:] or sorted(b['tipo'].unique())
for t in tipos:
    x = b[b['tipo'] == t]
    g = x.groupby(['mes', 'subtipo'], observed=True)
    col_b = 'brecha' if 'brecha' in x.columns else [c for c in x.columns if 'brecha' in c][0]
    r = g.agg(brecha=(col_b, 'median'), n=(col_b, 'size')).reset_index()
    tab = r.pivot(index='mes', columns='subtipo', values=['brecha', 'n']).round(1)
    print(f'\n=== {t}')
    print(tab.to_string())
