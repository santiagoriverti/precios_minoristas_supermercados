# Revisión de la canasta POR SUCURSAL (mapa y Brecha_sucursal) y de la hoja Concentracion del nb06.
# Uso: python -I -X utf8 r5_sucursal_y_localidad.py <brecha_celiaca_AAAA-MM.xlsx> <carpeta sim_final>
import sys
from pathlib import Path
import pandas as pd

pd.set_option('display.width', 250)
pd.set_option('display.max_columns', 40)
pd.set_option('display.max_rows', 200)
F, D = Path(sys.argv[1]), Path(sys.argv[2])

bs = pd.read_excel(F, sheet_name='Brecha_sucursal')
print('=== Brecha_sucursal (último mes): sucursales por n_tipos y brecha de su canasta')
print(bs.groupby('n_tipos')['brecha_canasta'].describe(percentiles=[.05, .5, .95]).round(1).to_string())
print('\nmínimo de brecha_canasta:', round(bs['brecha_canasta'].min(), 1), '| negativas:', int((bs['brecha_canasta'] < 0).sum()))
print('\nn_tipos por empresa (último mes):')
print(pd.crosstab(bs['empresa'], bs['n_tipos']).to_string())

# qué tipos tiene cada sucursal en el último mes (desde bt_sm de la simulación = Colab)
bt = pd.read_parquet(D / 'sim_bt_sm.parquet')
ult = bt['mes'].max()
u = bt[bt['mes'] == ult]
comb = u.groupby('suc_key')['tipo'].apply(lambda s: ' + '.join(sorted(x.split()[0] for x in s)))
print(f'\n=== combinaciones de tipos por sucursal en {ult} (top 12)')
print(comb.value_counts().head(12).to_string())
print('\nbrecha negativa por sucursal x tipo en el último mes:', int((u['brecha_pct'] < 0).sum()), 'de', len(u))

c = pd.read_excel(F, sheet_name='Concentracion')
print('\n=== Concentracion: 15 localidades con más sucursales')
print(c.head(15).round(1).to_string(index=False))
bsm = bt[bt['mes'].isin(sorted(bt['mes'].unique())[-12:])]
top = c.head(6)['localidad'].tolist()
print('\nempresas y provincias de esas localidades (últimos 12 meses, sucursales distintas):')
x = bsm[bsm['localidad'].isin(top)].drop_duplicates('suc_key')
print(pd.crosstab([x['localidad'], x['PROVINCIA_NORM']], x['empresa']).to_string())
