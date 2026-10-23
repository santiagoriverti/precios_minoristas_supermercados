# Serie TPD de cada subtipo de un tipo (hoja TPD_subtipos) contra la descriptiva del mismo subtipo-mes en las celdas del
# panel balanceado: la mediana entre sucursales antes de imputar, sus sucursales y el valor que arrastra la serie
# mensual cuando tiene menos de la mitad de las habituales (sim_imputaciones). Muestra qué meses arrastra la descriptiva
# y qué estima la TPD con las sucursales que hay (BRECHA_CELIACA §14.12).
# Uso: python -I -X utf8 r12_tpd_vs_descriptiva_subtipo.py <carpeta de la simulación (s11)> <brecha_celiaca_AAAA-MM.xlsx de esa simulación>
#                                                        [tipo] [desde AAAA-MM] [hasta AAAA-MM]
import sys
from pathlib import Path
import pandas as pd

pd.set_option('display.width', 250); pd.set_option('display.max_columns', 40); pd.set_option('display.max_rows', 400)
SIM, XLS = Path(sys.argv[1]), Path(sys.argv[2])
TIPO = sys.argv[3] if len(sys.argv) > 3 else 'Fideos secos'
DESDE = sys.argv[4] if len(sys.argv) > 4 else '2023-04'
HASTA = sys.argv[5] if len(sys.argv) > 5 else '2024-08'
# celdas del panel balanceado, como la CELDA 8 (sucursal × subtipo con los dos lados en >= 70% de los meses)
bs = pd.read_parquet(SIM / 'sim_bt_sub.parquet', columns=['suc_key', 'tipo', 'subtipo', 'mes', 'brecha_pct'])
pres = bs.groupby(['suc_key', 'tipo', 'subtipo'])['mes'].nunique()
cel = pres[pres >= max(1, int(round(0.7 * bs['mes'].nunique())))].reset_index()[['suc_key', 'tipo', 'subtipo']]
b = bs.merge(cel, on=['suc_key', 'tipo', 'subtipo'])
b = b[b['tipo'] == TIPO]
desc = b.groupby(['subtipo', 'mes'])['brecha_pct'].agg(descriptiva_sin_imputar='median', sucursales='size')
habit = desc.groupby('subtipo')['sucursales'].median()
imp = pd.read_parquet(SIM / 'sim_imputaciones.parquet')
imp = imp[(imp['serie'] == 'panel balanceado') & (imp['tipo'] == TIPO)]
arr = {(r.subtipo, m): r.brecha_arrastrada for r in imp.itertuples(index=False)
       for m in pd.period_range(r.desde, r.hasta, freq='M').astype(str)}
tp = pd.read_excel(XLS, sheet_name='TPD_subtipos', dtype={'mes': str})
tp = tp[(tp['universo'] == 'panel balanceado') & (tp['tipo'] == TIPO)].set_index(['subtipo', 'mes'])
x = tp[['brecha_tpd', 'sucursales_con_pares', 'movido_con_los_demas']].join(desc, how='outer').reset_index()
x['descriptiva_arrastrada'] = [arr.get((s, m)) for s, m in zip(x['subtipo'], x['mes'])]
x = x[(x['mes'] >= DESDE) & (x['mes'] <= HASTA)]
for sub, d in x.groupby('subtipo'):
    print(f'\n== {TIPO} / {sub} (sucursales habituales en el panel: {habit.get(sub, 0):.0f}; descriptiva_arrastrada = '
          'valor que la serie mensual usa ese mes en lugar del propio)')
    print(d.drop(columns='subtipo').round(1).to_string(index=False))
