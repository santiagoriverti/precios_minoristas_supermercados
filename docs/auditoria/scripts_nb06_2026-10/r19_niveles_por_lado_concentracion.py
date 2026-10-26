# Nivel de cada lado de la brecha por sucursal contra la concentración (revisión metodológica del 2026-10-26, §2.7):
# precio con TACC y sin TACC de la sucursal sobre la mediana nacional del mismo subtipo y mes (log, promedio de los
# últimos 12 meses), contra el HHI de empresas de su departamento, por empresa. La brecha es un cociente: la
# concentración (o el costo de llegar a un lugar alejado) puede subir cualquiera de los dos lados.
# Uso: python -I -X utf8 r19_niveles_por_lado_concentracion.py <carpeta de la simulación (s11)>
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SIM = Path(sys.argv[1])
bs = pd.read_parquet(SIM / 'sim_bt_sub.parquet', columns=['suc_key', 'empresa', 'region', 'mes', 'tipo', 'subtipo', 'tacc', 'sin'])
meses = sorted(bs['mes'].unique())
bs = bs[bs['mes'].isin(meses[-12:])]
med = bs.groupby(['subtipo', 'mes'])[['tacc', 'sin']].transform('median')
bs['rel_con'] = np.log(bs['tacc'] / med['tacc'])
bs['rel_sin'] = np.log(bs['sin'] / med['sin'])
g = pd.read_parquet(SIM / 'sim_suc_geo.parquet', columns=['suc_key', 'departamento_id', 'PROVINCIA_NORM'])
cc = pd.read_parquet(SIM / 'sim_concentracion.parquet', columns=['departamento_id', 'hhi'])
s = bs.groupby(['suc_key', 'empresa', 'region'])[['rel_con', 'rel_sin']].mean().reset_index()
s = s.merge(g, on='suc_key').merge(cc, on='departamento_id')
s['rel_brecha'] = s['rel_sin'] - s['rel_con']
for e in ('La Anónima', 'Carrefour', 'Cencosud (Vea, Disco, Jumbo)'):
    d = s[s['empresa'] == e]
    r = lambda a, b: d[a].rank().corr(d[b].rank())
    print(f'{e} (n = {len(d)}): Spearman con el HHI -> nivel con TACC {r("rel_con", "hhi"):+.2f}, nivel sin TACC '
          f'{r("rel_sin", "hhi"):+.2f}, brecha relativa {r("rel_brecha", "hhi"):+.2f}')
d = s[s['empresa'] == 'La Anónima']
d = d.assign(hhi_alto=d['hhi'] >= d['hhi'].median())
print('La Anónima, nivel de cada lado (% sobre la mediana nacional) según el HHI de su departamento:')
print(d.groupby('hhi_alto')[['rel_con', 'rel_sin', 'rel_brecha']].mean().mul(100).round(1).to_string())
print(d.groupby('region')[['rel_con', 'rel_sin', 'rel_brecha', 'hhi']].mean().round(3).assign(n=d.groupby('region').size()).to_string())
