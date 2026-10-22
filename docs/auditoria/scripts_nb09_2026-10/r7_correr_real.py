# Corre las celdas REALES del nb09 sobre los zips semestrales de la PC para un período corto y compara el panel mensual
# con el de la corrida de Colab (mismos meses: tienen que dar igual). Revisa las salidas nuevas (hoja Dias, marcas).
# Uso: python -I -X utf8 r7_correr_real.py <repo> <carpeta zips> <salida> <panel de Colab> <desde> <hasta>
import json, os, sys
from pathlib import Path
import numpy as np
import pandas as pd

REPO, ZIPS, OUT, PANEL, DESDE, HASTA = sys.argv[1:7]
cells = [''.join(c['source']) for c in json.load(open(Path(REPO) / 'notebooks' / '09_trazabilidad_productos.ipynb',
                                                      encoding='utf-8'))['cells'] if c['cell_type'] == 'code']
os.chdir(REPO)
g = {}
exec(cells[0], g)
g.update(SEPA_DIR=ZIPS, OUTPUT_DIR=OUT, FECHA_INICIO=DESDE, FECHA_FIN=HASTA, USAR_GEOREF=False)
for c in cells[1:]:
    exec(c, g)

R = g['R']
pm = pd.read_parquet(next(Path(OUT).glob('panel_mensual_productos_*.parquet')))
pc = pd.read_parquet(PANEL)
pc = pc[pc['mes'].isin(pm['mes'].unique())]
J = pm.merge(pc, on=['id_producto', 'mes'], how='outer', suffixes=('', '_colab'), indicator=True)
B = J[J['_merge'] == 'both']
print(f'\nPanel local vs Colab ({sorted(pm["mes"].unique())}): filas {len(pm):,} vs {len(pc):,} | solo local '
      f'{int((J["_merge"] == "left_only").sum())} | solo Colab {int((J["_merge"] == "right_only").sum())} | días distintos '
      f'{int((B["dias_con_precio"] != B["dias_con_precio_colab"]).sum())} | suc/día distintos '
      f'{int((np.abs(B["suc_diarias_prom"] - B["suc_diarias_prom_colab"]) > 1e-3).sum())}')
x = pd.ExcelFile(next(Path(OUT).glob('trazabilidad_productos_*.xlsx')), engine='calamine')
print('hojas:', x.sheet_names)
print(x.parse('Dias').head(3).to_string(index=False)); print('...'); print(x.parse('Dias').tail(2).to_string(index=False))
print(x.parse('Resumen').to_string(index=False))
print(x.parse('Cadenas')[['id_comercio', 'comercio', 'ultimo_mes', 'publica_en_el_ultimo_mes']].to_string(index=False))
print('solo en comercios que dejaron de publicar:', int(R['solo_en_comercios_que_dejaron_de_publicar'].sum()),
      '| precio simbólico:', int(R['precio_simbolico'].sum()))
print(R.loc[R['precio_simbolico'], ['id_producto', 'descripcion', 'precio_mediano_ultimo_mes', 'sucursales_ultimo_mes',
                                    'cadena_principal']].head(10).to_string(index=False))
