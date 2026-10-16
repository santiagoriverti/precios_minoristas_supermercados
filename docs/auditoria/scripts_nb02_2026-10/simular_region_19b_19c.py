# Corre las CELDAS 19b y 19c REALES de un notebook nb02 (el vigente o uno viejo, para comparar) sobre ZIPs del SEPA
# locales, con la canasta y la serie oficial de una corrida (su canasta_analisis_*.xlsx) y deja en <trabajo>:
#   detalle_long.parquet (la hoja analisis_detallado en formato largo), atributos_sucursal.parquet (cadena,
#   provincia, region y tipo de cada sucursal del panel), el Excel con las hojas de la 19b y el cache de la 19c.
# Ejecuta tambien CELDA 4 (maestro) y el bloque de geografia de la CELDA 7 (suc_geo_clean con la columna amba), que la
# 19b usa para la region desde el 2026-10-16.
# Uso: python -I docs/auditoria/scripts_nb02_2026-10/simular_region_19b_19c.py <repo> <notebook.ipynb>
#        <carpeta con YYYYA.zip/YYYYB.zip> <canasta_analisis.xlsx> <canasta_representativa.xlsx (hoja Seleccion)>
#        <PERIODO YYYY-MM> <DETALLE_MESES> <carpeta de trabajo> [carpeta con un detalle_*_v1.parquet a sembrar]
# Resultado del 2026-10-16 (BUG-43): ver docs/AUDITORIA_2026-10-16_nb02.md, seccion 8.
import gc, gzip, hashlib, json, os, re, shutil, sys, time, zipfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
REPO, NBP, ZIPDIR, XLS, SELX = [Path(a) for a in sys.argv[1:6]]
PERIODO, DMESES, WORK = sys.argv[6], int(sys.argv[7]), Path(sys.argv[8])
SEMILLA = Path(sys.argv[9]) if len(sys.argv) > 9 else None
os.chdir(REPO)                                    # la CELDA 4 busca data/maestro_sucursales_completo.xlsx
CELDAS = [''.join(c['source']) for c in json.load(open(NBP, encoding='utf-8'))['cells'] if c['cell_type'] == 'code']
celda = lambda tag: next(c for c in CELDAS if tag in c[:300])


def bloque(src, ini, fin):
    i0 = src.index(ini)
    return src[i0:src.index(fin, i0)]


out_dir, tmp_dir, cache_dir = WORK / 'out', WORK / 'tmp', WORK / 'cache'
for d in (out_dir, tmp_dir, cache_dir):
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
if SEMILLA:
    for f in SEMILLA.glob('detalle_*_v1.parquet'):
        shutil.copy(f, cache_dir / f.name)
xls_out = out_dir / f'canasta_analisis_{PERIODO}.xlsx'
shutil.copy(XLS, xls_out)

env = {'__builtins__': __builtins__, 'np': np, 'pd': pd, 're': re, 'zipfile': zipfile, 'gzip': gzip,
       'shutil': shutil, 'gc': gc, 'hashlib': hashlib, 'Path': Path}
exec(celda('# CONFIGURACI'), env)
env.update(SEPA_DIR=ZIPDIR, OUTPUT_DIR=out_dir, TMP_DIR=tmp_dir, CACHE_DIR=cache_dir, USE_CACHE=True,
           PERIODO=PERIODO, ULTIMO_MES=PERIODO, DETALLE_MESES=DMESES, DESAGREGAR_CANASTAS=['cantidad_03'])
exec(bloque(celda('# CELDA 3 —'), 'CANT_COLS =', '# ── Construir CANASTAS'), env)
exec(celda('# CELDA 4 —'), env)
exec(celda('# CELDA 5 —'), env)
C7 = celda('# CELDA 7 —')
exec(bloque(C7, '# ── Bboxes y función de geocodificación', '# ── Calcular canasta por sucursal'), env)
exec(bloque(celda('# CELDA 19 —'), 'from openpyxl.styles', 'out_xls ='), env)

sp = pd.read_excel(XLS, sheet_name='Serie_precios', dtype={'id_producto': str})
sp['ean_norm'] = sp['id_producto'].str.strip().str.lstrip('0')
env['CANASTAS'] = {cid: {r.ean_norm: (str(r.descripcion)[:50], int(r.qty), str(r.categoria))
                         for r in g.drop_duplicates('ean_norm').itertuples()}
                   for cid, g in sp.groupby('canasta_id')}
env['CANASTAS_ACTIVAS'] = list(env['CANASTAS'])
xs = pd.ExcelFile(SELX)
sel = xs.parse([n for n in xs.sheet_names if n.startswith('Selecci')][0], dtype={'id_producto': str})
sel['ean_norm'] = sel['id_producto'].str.strip().str.lstrip('0')
exec(bloque(celda('# CELDA 3 —'), '# Rubro SEPA por EAN', 'N_EANS_TOTAL'), {**env, 'sel': sel}, env)
env['df_hist_raw'] = (sp.drop_duplicates(['ean_norm', 'mes'])
                      .rename(columns={'mes': 'anio_mes'})[['ean_norm', 'precio_mediano', 'anio_mes']])
evo = pd.read_excel(XLS, sheet_name='Evolucion_IPC')
evo['mes'] = evo['mes'].astype(str)
SH = env['CANASTA_SHORT']
env['serie_nac_dict'] = {cid: evo[['mes', f'canasta_{SH[cid]}', f'var_{SH[cid]}_%']]
                         .rename(columns={f'canasta_{SH[cid]}': 'canasta_nacional_ponderada',
                                          f'var_{SH[cid]}_%': 'variacion_mensual_%'})
                         for cid in env['CANASTAS']}

for nombre in ('CELDA 19b', 'CELDA 19c'):
    t = time.time()
    exec(compile(celda(f'# {nombre} —'), f'<{nombre}>', 'exec'), env)
    print(f'{nombre}: {time.time() - t:,.0f} s', flush=True)

env['detalle_long'].to_parquet(WORK / 'detalle_long.parquet')
env['_SUC'].to_parquet(WORK / 'atributos_sucursal.parquet')
print('cache:', [f.name for f in cache_dir.glob('detalle_*')])
print('listo:', WORK)
