# Cálculo independiente de la canasta COMPARABLE por sucursal y mes del nb06 vigente (BUG-47) y comparación con la
# simulación (s11: sim_bt_sub.parquet y sim_brecha_suc_mes.parquet). En cada sucursal-mes: subtipo propio (brecha con
# los dos lados) o, si no lo tiene, la brecha nacional del mes (mediana entre sucursales, con la imputación de la serie
# mensual: subtipo-mes con < 10 sucursales o < 50% de su mediana del período arrastra su último mes válido); tipo =
# promedio geométrico de sus subtipos; canasta = sum_k w_k (1 + g_k) - 1 (pesos ENGHo de la hoja Ponderaciones).
# Uso: python -I -X utf8 r9_canasta_comparable_sucursal.py <carpeta de la simulación> <brecha_celiaca_AAAA-MM.xlsx>
import sys
from pathlib import Path
import numpy as np
import pandas as pd

SIM, XLS = Path(sys.argv[1]), Path(sys.argv[2])
MIN, FRAC = 10, 0.5
bt = pd.read_parquet(SIM / 'sim_bt_sub.parquet', columns=['suc_key', 'mes', 'tipo', 'subtipo', 'brecha_pct'])
nb = pd.read_parquet(SIM / 'sim_brecha_suc_mes.parquet', columns=['suc_key', 'mes', 'brecha_comparable', 'peso_propio_pct'])
pond = pd.read_excel(XLS, sheet_name='Ponderaciones')
W = dict(zip(pond['tipo'], pond['peso_en_la_canasta_pct'] / 100))

# nacional por subtipo y mes, con la imputación de la serie mensual
q = bt.groupby(['tipo', 'subtipo', 'mes']).agg(b=('brecha_pct', 'median'), n=('suc_key', 'nunique')).reset_index()
q['ok'] = (q['n'] >= MIN) & (q['n'] >= FRAC * q.groupby(['tipo', 'subtipo'])['n'].transform('median'))
w = q[q['ok']].pivot_table(index='mes', columns=['tipo', 'subtipo'], values='b').reindex(sorted(bt['mes'].unique()))
nac = np.log1p(w / 100).ffill()

subs = list(nac.columns)
peso = {s: W[s[0]] / sum(1 for x in subs if x[0] == s[0]) for s in subs}
own = np.log1p(bt.set_index(['suc_key', 'mes', 'tipo', 'subtipo'])['brecha_pct'] / 100)
own = own.unstack(['tipo', 'subtipo']).reindex(columns=pd.MultiIndex.from_tuples(subs))
own = own.reindex(pd.MultiIndex.from_frame(nb[['suc_key', 'mes']]))
propio = own.notna()
lg = own.fillna(nac.reindex(own.index.get_level_values('mes')).set_axis(own.index))
rel = np.exp(lg.T.groupby(level=0).mean().T)                        # tipo: promedio geométrico de sus subtipos
canasta = (rel * pd.Series(W)).sum(axis=1) * 100 - 100
pp = (propio * pd.Series(peso)).sum(axis=1) * 100
d1 = (canasta.to_numpy() - nb['brecha_comparable'].to_numpy())
d2 = (pp.to_numpy() - nb['peso_propio_pct'].to_numpy())
print(f'{len(nb):,} sucursal-mes | canasta comparable: dif. máx. {np.nanmax(np.abs(d1)):.2e} pp '
      f'(NaN en uno solo: {int((np.isnan(canasta.to_numpy()) != nb["brecha_comparable"].isna().to_numpy()).sum())}) | '
      f'peso propio: dif. máx. {np.nanmax(np.abs(d2)):.2e}')
u = nb['mes'].max()
x = nb[nb['mes'] == u]
print(f'{u}: {len(x):,} sucursales; canasta comparable mediana {x["brecha_comparable"].median():+.1f}%, peso propio '
      f'mediano {x["peso_propio_pct"].median():.1f}%')
