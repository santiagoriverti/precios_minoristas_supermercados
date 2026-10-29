# Corre las celdas reales del nb08 (v3: nivel general vs provincias y vs grandes rubros) sobre zips locales para un
# período corto e imprime tiempo y RAM por celda. Así se validó la v3 el 2026-10-29 (jul-sep 2024, 775 productos).
# Uso: python -X utf8 correr_real_desagregado.py <repo> <carpeta zips> <salida> <Excel canasta> <columna> <desde> <hasta>
# Ej.: ... C:/.../SEPA_Bases_Originales/carga <salida> C:/Users/sriverti/proyectos/canasta_pass_through_20220101_20261020.xlsx
#      cantidad_08 2024-07-01 2024-09-30
import json, os, sys, time
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.show = lambda *a, **k: None

REPO, ZIPS, OUT, XLS, COL, DESDE, HASTA = sys.argv[1:8]
os.makedirs(OUT, exist_ok=True)
os.chdir(REPO)
cells = [''.join(c['source']) for c in json.load(open('notebooks/08_canasta_diaria.ipynb', encoding='utf-8'))['cells']
         if c['cell_type'] == 'code']
g = {}
exec(cells[0], g)
g.update(SEPA_DIR=ZIPS, OUTPUT_DIR=OUT, CANASTA_EXCEL=XLS, CANASTA_COL=COL, FECHA_INICIO=DESDE, FECHA_FIN=HASTA)
t = time.time()
for i, c in enumerate(cells[1:], 2):
    exec(c, g)
    print(f'[celda {i}] {time.time() - t:.0f} s acumulados | {g["ram"]() if "ram" in g else ""}', flush=True)
