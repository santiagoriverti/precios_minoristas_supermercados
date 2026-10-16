# Corre la geografia REAL de la CELDA 7 del nb02 (CELDA 4 + bloque de bboxes, reclasificacion y AMBA) sobre el maestro
# de sucursales y tabula las sucursales que la CELDA 7 cambia de provincia (declarada en el maestro -> por coordenadas)
# y las que descarta (CABA declarada con coordenadas fuera de CABA).
# Uso: python -I docs/auditoria/scripts_nb02_2026-10/reclasificacion_celda7.py <repo>
# Resultado del 2026-10-16 (BUG-44, abierto): el rectangulo de Neuquen termina en -68,5 de longitud y deja afuera la
# ciudad de Neuquen (-68,06), Centenario y Plottier: esas sucursales pasan a La Pampa. Otras reclasificaciones son
# correctas (p. ej. 6 DIA de Jujuy declarados San Juan).
import json, re, sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
pd.set_option('display.width', 250)
REPO = Path(sys.argv[1])
import os
os.chdir(REPO)
CELDAS = [''.join(c['source']) for c in json.load(open(REPO / 'notebooks/02_evolucion_canasta_representativa.ipynb',
                                                    encoding='utf-8'))['cells'] if c['cell_type'] == 'code']
celda = lambda t: next(c for c in CELDAS if t in c[:300])
bloque = lambda s, a, b: s[s.index(a):s.index(b, s.index(a))]
env = {'np': np, 'pd': pd, 're': re, 'Path': Path, 'SEPA_DIR': '.'}
exec(celda('# CELDA 4 —'), env)
exec(bloque(celda('# CELDA 7 —'), '# ── Bboxes y función de geocodificación', '# ── Calcular canasta por sucursal'), env)
sp, sg = env['suc_pais'].copy(), env['suc_geo_clean']
sp['declarada'] = sp['PROVINCIA'].map(env['PROV_NORM']).fillna(sp['PROVINCIA'])
k = ['id_comercio', 'id_bandera', 'id_sucursal']
m = sp[k + ['declarada', 'sucursales_nombre', 'sucursales_localidad', 'sucursales_latitud', 'sucursales_longitud',
            'sucursales_tipo']].merge(sg[k + ['PROVINCIA_NORM', 'cadena']], on=k, how='left')
desc = m[m['PROVINCIA_NORM'].isna()]
print(f'maestro con coordenadas: {len(sp):,} | en la CELDA 7: {len(sg):,} | descartadas: {len(desc):,} '
      f'(web: {int(desc["sucursales_tipo"].eq("Web").sum())}, resto: CABA con coordenadas fuera de CABA)')
r = m[m['PROVINCIA_NORM'].notna() & (m['PROVINCIA_NORM'] != m['declarada'])]
print(f'reclasificadas: {len(r)}')
print(r.groupby(['declarada', 'PROVINCIA_NORM']).size().rename('sucursales').reset_index()
      .sort_values('sucursales', ascending=False).to_string(index=False))
for (a, b), g in r.groupby(['declarada', 'PROVINCIA_NORM']):
    if len(g) >= 3:
        print(f'\n  {a} -> {b}:', ', '.join(sorted(set(g['sucursales_localidad'].astype(str).str.title())))[:200])
