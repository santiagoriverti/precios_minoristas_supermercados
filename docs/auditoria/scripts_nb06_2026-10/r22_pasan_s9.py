# Los candidatos que pasan s9 (pasa = True) por subtipo y lado, y si quedaron en la canasta final (s10). Muestra la
# verificación de s10 (.verif.parquet) para los que no entraron.
# Uso: python -I -X utf8 r22_pasan_s9.py <seleccion.parquet de s9> <canasta.csv> <canasta.verif.parquet>
import sys

import pandas as pd

pd.set_option('display.width', 260); pd.set_option('display.max_columns', 40); pd.set_option('display.max_colwidth', 58)
sel = pd.read_parquet(sys.argv[1])
can = pd.read_csv(sys.argv[2], dtype={'ean': str})
ver = pd.read_parquet(sys.argv[3])
print('verif:', ver.shape, list(ver.columns))
p = sel[sel['pasa']].copy()
en = set(can['ean'].str.lstrip('0')) | set(can['producto'])
p['en_canasta'] = p['id'].astype(str).str.lstrip('0').isin(en) | p['descripcion'].isin(en)
p['descripcion'] = p['descripcion'].astype(str).str.slice(0, 55)
for (st, l), g in p.sort_values('suc_mes_mediana', ascending=False).groupby(['subtipo', 'lado']):
    print(f'\n== {st} | {l}: {len(g)} pasan s9, {int(g["en_canasta"].sum())} en la canasta')
    print(g[['id', 'descripcion', 'suc_mes_mediana', 'cadenas_grandes', 'precio_100g_22oct', 'gramos_22oct',
             'en_canasta']].to_string(index=False))
