# Config del nb06 (TIPOS, GRAMOS, VIGENCIA, PRODUCTO, SUBTIPO) con TODOS los candidatos que pasan s9 en subtipos
# comparables (tabla .eans.parquet de s10), para leer el SEPA una sola vez en la simulación local: la canasta final es
# un subconjunto y su caché se arma filtrando este (s11 --config).
# Uso: python -I -X utf8 s14_superconjunto.py <canasta.eans.parquet de s10> <canasta.csv final> <salida.json>
import json, sys
from pathlib import Path
import pandas as pd

E = pd.read_parquet(sys.argv[1]).drop_duplicates('ean')
F = pd.read_csv(sys.argv[2], dtype={'ean': str})
PESOS = {'Fideos secos': 1.503, 'Galletitas dulces': 1.717, 'Galletitas saladas y crackers': 1.407,
         'Pan rallado y rebozador': 0.194, 'Cereales rellenos (almohaditas)': 0.181}
E = E[E['gramos'].notna()]
assert set(F['ean']) <= set(E['ean']), set(F['ean']) - set(E['ean'])
T = {t: {'peso': PESOS[t],
         'tacc': {r.ean: r.descripcion for r in g[g['lado'] == 'tacc'].itertuples()},
         'sin_tacc': {r.ean: r.descripcion for r in g[g['lado'] == 'sin_tacc'].itertuples()}}
     for t, g in E.groupby('tipo')}
c = {'TIPOS': T,
     'GRAMOS': {r.ean: float(r.gramos) for r in E.itertuples()},
     'VIGENCIA': {r.ean: [r.desde, r.hasta] for r in E.itertuples() if r.desde or r.hasta},
     'PRODUCTO': {it: list(g['ean']) for it, g in E.groupby('item') if len(g) > 1},
     'SUBTIPO': {s: list(g['ean']) for s, g in E.groupby('subtipo')}}
Path(sys.argv[3]).write_text(json.dumps(c, ensure_ascii=False, indent=1), encoding='utf-8')
print(f"{len(c['GRAMOS'])} EANs ({len(F)} de la canasta final) | " +
      ', '.join(f"{t}: {len(v['tacc'])}/{len(v['sin_tacc'])}" for t, v in T.items()))
