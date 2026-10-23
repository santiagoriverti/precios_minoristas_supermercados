# Variantes de la imputación de la serie mensual del nb06 (subtipo-mes con pocas sucursales), sobre los objetos de una
# simulación con las celdas reales (s11: sim_bt_sub.parquet) y los pesos del Excel. Hoy (V0): "habituales" = mediana de
# las sucursales del subtipo en todo el período; un subtipo-mes con < FRAC de eso (o < MIN sucursales) arrastra su último
# mes válido SIN límite. Variantes:
#   V1 K: arrastre de a lo sumo K meses; después el subtipo-mes queda afuera (el tipo sale de sus otros subtipos)
#   V2 K: V1 + "habituales" = mediana centrada de 13 meses (6 antes y 6 después)
#   V3 K: V2 + después de K meses, el dato propio del mes (si tiene >= MIN sucursales)
#   V4 K: "habituales" de todo el período (como hoy) + arrastre de a lo sumo K meses + después, el dato propio
# Control: V0 tiene que dar la serie del Excel (Serie_canasta y Serie_canasta_balanceada).
# Uso: python -I -X utf8 r6_variantes_imputacion.py <carpeta sim_final> <brecha_celiaca_AAAA-MM.xlsx> [K]
import sys
from pathlib import Path
import numpy as np
import pandas as pd

pd.set_option('display.width', 250); pd.set_option('display.max_rows', 300); pd.set_option('display.max_columns', 40)
SIM, XLS = Path(sys.argv[1]), Path(sys.argv[2])
K = int(sys.argv[3]) if len(sys.argv) > 3 else 3
MIN, FRAC, FRAC_PANEL = 10, 0.5, 0.7
bt = pd.read_parquet(SIM / 'sim_bt_sub.parquet')
pond = pd.read_excel(XLS, sheet_name='Ponderaciones')
W = dict(zip(pond['tipo'], pond['peso_en_la_canasta_pct'] / 100))
ORDEN = list(pond['tipo'])
_sk = ['id_comercio', 'id_bandera', 'id_sucursal']
pres = bt.groupby(_sk + ['tipo', 'subtipo'])['mes'].nunique()
celdas = pres[pres >= int(round(FRAC_PANEL * bt['mes'].nunique()))].index
bal = bt[bt.set_index(_sk + ['tipo', 'subtipo']).index.isin(celdas)]


def tipo_mensual(df, variante, k):
    meses = sorted(df['mes'].unique())
    n = df.groupby(['mes', 'tipo', 'subtipo'])['suc_key'].nunique().rename('n').reset_index()
    if variante in ('V2', 'V3'):
        n = n.sort_values(['tipo', 'subtipo', 'mes'])
        ref = n.groupby(['tipo', 'subtipo'])['n'].transform(lambda x: x.rolling(13, center=True, min_periods=1).median())
    else:
        ref = n.groupby(['tipo', 'subtipo'])['n'].transform('median')
    n['ok'] = (n['n'] >= MIN) & (n['n'] >= FRAC * ref)
    n['base'] = n['n'] >= MIN
    s = df.groupby(['mes', 'tipo', 'subtipo'])['brecha_pct'].median().rename('b').reset_index().merge(n)
    s['lb'] = np.where(s['ok'], np.log1p(s['b'] / 100), np.nan)
    s['lb_propio'] = np.where(s['base'], np.log1p(s['b'] / 100), np.nan)
    grid = s[['tipo', 'subtipo']].drop_duplicates().merge(pd.DataFrame({'mes': meses}), how='cross')
    s = grid.merge(s, on=['mes', 'tipo', 'subtipo'], how='left').sort_values(['tipo', 'subtipo', 'mes'])
    s['lb'] = s.groupby(['tipo', 'subtipo'])['lb'].ffill(limit=None if variante == 'V0' else k)
    if variante in ('V3', 'V4'):
        s['lb'] = s['lb'].fillna(s['lb_propio'])
    s = s[s['lb'].notna()]
    t = s.groupby(['mes', 'tipo'])['lb'].mean()
    return (np.expm1(t) * 100).unstack('tipo').reindex(columns=ORDEN)


def canasta(t):
    w = pd.Series(W).reindex(ORDEN)
    rel = 1 + t / 100
    return ((rel * w).sum(axis=1, min_count=1) / (rel.notna() * w).sum(axis=1) - 1) * 100


res = {}
for v in ('V0', 'V1', 'V2', 'V3', 'V4'):
    res[v] = {lab: tipo_mensual(df, v, K) for lab, df in (('todas', bt), ('panel', bal))}
for lab, hoja in (('todas', 'Serie_canasta'), ('panel', 'Serie_canasta_balanceada')):
    x = pd.read_excel(XLS, sheet_name=hoja).set_index('mes')['brecha_canasta']
    print(f'control V0 = Excel ({hoja}): dif. máx. {(canasta(res["V0"][lab]) - x).abs().max():.2e}')

print(f'\n=== Canasta: promedio de los meses de cada año y desvío de la variación mensual (pp), K = {K}')
filas = []
for v, d in res.items():
    for lab in ('todas', 'panel'):
        c = canasta(d[lab])
        a = c.groupby(c.index.str[:4]).mean().round(1)
        filas.append({'variante': v, 'serie': lab, **a.to_dict(), 'desvio_var_mensual': round(c.diff().std(), 1)})
print(pd.DataFrame(filas).to_string(index=False))
for v in ('V1', 'V2', 'V3', 'V4'):
    for lab in ('todas', 'panel'):
        dc = canasta(res[v][lab]) - canasta(res['V0'][lab])
        dt = (res[v][lab] - res['V0'][lab]).round(1)
        print(f'\n-- {v} {lab}: meses con |dif. de la canasta| > 1 pp: {int((dc.abs() > 1).sum())}')
        print(pd.concat([dc.round(1).rename('canasta'), dt], axis=1)[dc.abs() > 1].to_string())
