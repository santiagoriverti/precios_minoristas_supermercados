# Candidatos descartados con más cobertura, por tipo y lado: subtipo asignado, motivo y cobertura. Sirve para ver si
# la regla de subtipo ("subtipo no comparable") o la de continuidad dejaron afuera productos que debían entrar.
# Uso: python -I -X utf8 r21_descartes.py <seleccion.parquet de s9> <salida.csv> [n por grupo]
import sys

import pandas as pd

pd.set_option('display.width', 260); pd.set_option('display.max_columns', 40); pd.set_option('display.max_colwidth', 62)
sel = pd.read_parquet(sys.argv[1])
n = int(sys.argv[3]) if len(sys.argv) > 3 else 12
cols = ['tipo_nb06', 'lado', 'subtipo', 'id', 'descripcion', 'marca', 'suc_mes_mediana', 'meses_2022_2026_07',
        'provincias', 'comercios_super', 'cadenas_grandes', 'pct_cadena_principal', 'es_gf', 'motivo']
d = sel[~sel['pasa']].copy()
d = d.sort_values('suc_mes_mediana', ascending=False)
d[cols].to_csv(sys.argv[2], index=False)
for (t, l), g in d.groupby(['tipo_nb06', 'lado'], sort=True):
    print(f'\n===== {t} | {l}: {len(g)} descartados')
    g = g.head(n).copy()
    g['motivo'] = g['motivo'].astype(str).str.slice(0, 70)
    g['descripcion'] = g['descripcion'].astype(str).str.slice(0, 55)
    print(g[['subtipo', 'id', 'descripcion', 'suc_mes_mediana', 'meses_2022_2026_07', 'cadenas_grandes',
             'motivo']].to_string(index=False))
