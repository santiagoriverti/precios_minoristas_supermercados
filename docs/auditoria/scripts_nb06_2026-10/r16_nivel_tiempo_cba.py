# Revisión metodológica del nb06 (1): ponderación de subtipos, composición del panel, índices de precio de cada lado y
# costo mensual con las cantidades de la CBA. Sobre los objetos de la simulación (= Colab).
# Uso: python -I -X utf8 r16_nivel_tiempo_cba.py <carpeta sim>
import sys
from pathlib import Path

import numpy as np
import pandas as pd

pd.set_option('display.width', 250); pd.set_option('display.max_columns', 40); pd.set_option('display.max_rows', 200)
SIM = Path(sys.argv[1])
W = {'Fideos secos': 1.503, 'Galletitas dulces': 1.717, 'Galletitas saladas y crackers': 1.407,
     'Pan rallado y rebozador': 0.194, 'Cereales rellenos (almohaditas)': 0.181}
bs = pd.read_parquet(SIM / 'sim_bt_sub.parquet')
bs['anio'] = bs['mes'].str[:4]
meses = sorted(bs['mes'].unique())
ult12 = meses[-12:]
pres = bs.groupby(['suc_key', 'tipo', 'subtipo'])['mes'].nunique()
panel = pres[pres >= int(round(0.7 * len(meses)))].reset_index()[['suc_key', 'tipo', 'subtipo']]
bp = bs.merge(panel, on=['suc_key', 'tipo', 'subtipo'])


def canasta(tipos):
    return 100 * (sum(W[k] * (1 + tipos[k] / 100) for k in tipos.index) / sum(W[k] for k in tipos.index) - 1)


def tipo_geo(sub, peso=None):
    # sub: DataFrame con tipo, subtipo, brecha (%), n; peso None = iguales
    out = {}
    for t, d in sub.groupby('tipo'):
        w = np.ones(len(d)) if peso is None else d[peso].to_numpy(float)
        out[t] = 100 * (np.exp(np.average(np.log1p(d['brecha'] / 100), weights=w)) - 1)
    return pd.Series(out)


print('=== A. Ponderación de los subtipos dentro de su tipo (todas las sucursales) ===')
for etiqueta, d in (('todo el período', bs), ('últimos 12 meses', bs[bs['mes'].isin(ult12)])):
    s = d.groupby(['tipo', 'subtipo']).agg(brecha=('brecha_pct', 'median'), n=('brecha_pct', 'size'),
                                          suc=('suc_key', 'nunique')).reset_index()
    eq, wn = tipo_geo(s), tipo_geo(s, 'n')
    print(f'\n-- {etiqueta}')
    print(s.assign(peso_disponibilidad=lambda x: x['n'] / x.groupby('tipo')['n'].transform('sum')).round(3).to_string(index=False))
    print(pd.DataFrame({'pesos iguales (hoy)': eq, 'pesos por disponibilidad': wn}).round(1).to_string())
    print(f'   canasta: pesos iguales {canasta(eq):.1f}% | por disponibilidad {canasta(wn):.1f}%')
print('\n-- canasta por año, pesos iguales vs por disponibilidad (panel; mediana de los sucursal-mes del año)')
for a, d in bp.groupby('anio'):
    s = d.groupby(['tipo', 'subtipo']).agg(brecha=('brecha_pct', 'median'), n=('brecha_pct', 'size')).reset_index()
    print(f'   {a}: {canasta(tipo_geo(s)):.1f}% | {canasta(tipo_geo(s, "n")):.1f}%')

print('\n=== B. Composición del panel balanceado (sucursales) ===')
g = pd.read_parquet(SIM / 'sim_suc_geo.parquet', columns=['suc_key', 'cadena', 'empresa', 'region', 'sucursales_tipo',
                                                         'PROVINCIA_NORM'])
ps = panel[['suc_key']].drop_duplicates().merge(g, on='suc_key')
todas = bs[bs['mes'].isin(ult12)][['suc_key']].drop_duplicates().merge(g, on='suc_key')
for col in ('empresa', 'region', 'sucursales_tipo'):
    c = pd.DataFrame({'panel': ps[col].value_counts(normalize=True) * 100,
                      'con brecha últimos 12 meses': todas[col].value_counts(normalize=True) * 100}).fillna(0)
    print(c.sort_values('panel', ascending=False).round(1).head(12).to_string())
print(f'   panel: {len(ps)} sucursales; con brecha en los últimos 12 meses: {len(todas)}')

print('\n=== C. Índices de precio de cada lado (panel, pares en la misma sucursal; base 2022 = 100) ===')
x = bp.groupby(['tipo', 'subtipo', 'mes']).agg(con=('tacc', 'median'), sin=('sin', 'median')).reset_index()
x['anio'] = x['mes'].str[:4]
t = x.groupby(['tipo', 'mes']).agg(con=('con', lambda v: np.exp(np.log(v).mean())),
                                    sin=('sin', lambda v: np.exp(np.log(v).mean()))).reset_index()
t['anio'] = t['mes'].str[:4]
a = t.groupby(['tipo', 'anio'])[['con', 'sin']].mean()
base = a.xs('2022', level='anio')
idx = (a / base.reindex(a.index.get_level_values('tipo')).set_index(a.index)) * 100
idx['brecha_relativa'] = idx['sin'] / idx['con'] * 100
print(idx.round(0).unstack('anio').to_string())
# canasta: índice ENGHo de cada lado (Laspeyres sobre los tipos, base 2022)
ca = {}
for lado in ('con', 'sin'):
    m = idx[lado].unstack('anio')
    ca[lado] = (m.mul(pd.Series(W), axis=0).sum() / sum(W.values()))
ca = pd.DataFrame(ca)
ca['sin / con'] = ca['sin'] / ca['con'] * 100
print('   canasta (índices ENGHo de cada lado):'); print(ca.round(0).to_string())

print('\n=== I. Costo mensual con las cantidades de la CBA (INDEC, g por adulto equivalente) ===')
# precio mediano nacional $/100 g de los pares (todas las sucursales) en los últimos 3 meses
u3 = meses[-3:]
q = {('Fideos secos', None): 1740, ('Galletitas saladas y crackers', 'Crackers y galletas de arroz'): 420,
     ('Galletitas dulces', None): 210}
tot_con = tot_sin = 0.0
for (tp, sub), gramos in q.items():
    d = bs[bs['mes'].isin(u3) & (bs['tipo'] == tp)]
    if sub:
        d = d[d['subtipo'] == sub]
    s = d.groupby('subtipo').agg(con=('tacc', 'median'), sin=('sin', 'median'))
    con, sin = np.exp(np.log(s['con']).mean()), np.exp(np.log(s['sin']).mean())
    tot_con += con * gramos / 100; tot_sin += sin * gramos / 100
    print(f'   {tp}{" / " + sub if sub else ""}: {gramos} g/AE; con TACC ${con:,.0f}/100 g, sin TACC ${sin:,.0f}/100 g -> '
          f'${con * gramos / 100:,.0f} contra ${sin * gramos / 100:,.0f} por mes (+${(sin - con) * gramos / 100:,.0f})')
print(f'   total por adulto equivalente: ${tot_con:,.0f} contra ${tot_sin:,.0f} (+${tot_sin - tot_con:,.0f} por mes, '
      f'+{100 * (tot_sin / tot_con - 1):.0f}%); hogar tipo 2 (3,09 AE): +${3.09 * (tot_sin - tot_con):,.0f}')
print('   la CBA también tiene pan 6.750 g y harina de trigo 1.080 g por AE (sin equivalente en la canasta del nb06)')
