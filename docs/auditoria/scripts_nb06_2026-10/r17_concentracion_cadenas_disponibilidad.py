# Revisión metodológica del nb06 (2): concentración dentro de cada empresa, competencia por radio, comparación de
# empresas con una canasta núcleo (fideos + galletitas dulces) que incluye a DIA, disponibilidad de productos sin TACC
# y brecha por tipo de local. Sobre los objetos de la simulación (= Colab).
# Uso: python -I -X utf8 r17_concentracion_cadenas_disponibilidad.py <carpeta sim>
import sys
from pathlib import Path

import numpy as np
import pandas as pd

pd.set_option('display.width', 250); pd.set_option('display.max_columns', 40); pd.set_option('display.max_rows', 200)
SIM = Path(sys.argv[1])
W = {'Fideos secos': 1.503, 'Galletitas dulces': 1.717, 'Galletitas saladas y crackers': 1.407,
     'Pan rallado y rebozador': 0.194, 'Cereales rellenos (almohaditas)': 0.181}
g = pd.read_parquet(SIM / 'sim_suc_geo.parquet')
bm = pd.read_parquet(SIM / 'sim_brecha_suc_mes.parquet')
meses = sorted(bm['mes'].unique())
ult12 = meses[-12:]


def spearman(a, b):
    return pd.Series(a).rank().corr(pd.Series(b).rank())


print('=== D. Concentración (HHI de empresas por departamento) contra la brecha de cada sucursal ===')
x = bm[bm['mes'].isin(ult12) & (bm['peso_propio_pct'] >= 50)]
s = x.groupby('suc_key').agg(brecha=('brecha_comparable', 'median')).reset_index()
s = s.merge(g[['suc_key', 'empresa', 'cadena', 'region', 'departamento_id', 'sucursales_tipo', 'sucursales_latitud',
               'sucursales_longitud']], on='suc_key')
cc = pd.read_parquet(SIM / 'sim_concentracion.parquet')
s = s.merge(cc[['departamento_id', 'hhi', 'sucursales']].rename(columns={'sucursales': 'suc_depto'}), on='departamento_id')
s = s[s['suc_depto'] >= 5]       # como el nb06: departamentos con algunas sucursales (aprox.)
print(f'sucursales: {len(s)}; Spearman agrupado: {spearman(s["brecha"], s["hhi"]):+.2f}')
filas = []
for e, d in s.groupby('empresa'):
    if len(d) >= 30 and d['hhi'].nunique() > 5:
        filas.append({'empresa': e, 'sucursales': len(d), 'spearman_hhi': spearman(d['brecha'], d['hhi']),
                      'hhi_p25': d['hhi'].quantile(.25), 'hhi_p75': d['hhi'].quantile(.75),
                      'brecha_mediana': d['brecha'].median()})
print(pd.DataFrame(filas).round(2).to_string(index=False))
# regresión: log(1 + brecha) ~ HHI + efectos de empresa (+ región)
y = np.log1p(s['brecha'] / 100)
for etiqueta, cols in (('sin controles', []), ('con empresa', ['empresa']), ('con empresa y región', ['empresa', 'region'])):
    X = pd.concat([pd.Series(1.0, index=s.index, name='c'), s['hhi']] +
                  [pd.get_dummies(s[c], prefix=c, drop_first=True, dtype=float) for c in cols], axis=1)
    beta, *_ = np.linalg.lstsq(X.to_numpy(float), y.to_numpy(float), rcond=None)
    res = y.to_numpy() - X.to_numpy(float) @ beta
    XtX = np.linalg.pinv(X.to_numpy(float).T @ X.to_numpy(float))
    # error estándar agrupado por departamento
    sc = pd.DataFrame(X.to_numpy(float) * res[:, None]).groupby(s['departamento_id'].to_numpy()).sum().to_numpy()
    V = XtX @ (sc.T @ sc) @ XtX
    print(f'   OLS {etiqueta}: efecto de +0,1 de HHI = {100 * (np.exp(0.1 * beta[1]) - 1):+.2f}% en (1 + brecha) '
          f'(EE agrupado por departamento {100 * 0.1 * np.sqrt(V[1, 1]):.2f}); n = {len(s)}')

print('\n-- competencia por radio: empresas distintas a <= 3 km (universo del nb06)')
u = g[g['departamento_id'].notna() & g['sucursales_latitud'].notna()].copy()
lat, lon = np.radians(u['sucursales_latitud'].to_numpy(float)), np.radians(u['sucursales_longitud'].to_numpy(float))
emp = u['empresa'].to_numpy()
key = u['suc_key'].to_numpy()
idx = {k: i for i, k in enumerate(key)}
comp = {}
for k in s['suc_key']:
    i = idx.get(k)
    if i is None:
        continue
    d = 2 * 6371 * np.arcsin(np.sqrt(np.sin((lat - lat[i]) / 2) ** 2 + np.cos(lat[i]) * np.cos(lat) * np.sin((lon - lon[i]) / 2) ** 2))
    cerca = d <= 3
    comp[k] = len(set(emp[cerca]) - {emp[i]})
s['rivales_3km'] = s['suc_key'].map(comp)
print(f'   Spearman brecha vs empresas rivales a <= 3 km: agrupado {spearman(s["brecha"], s["rivales_3km"]):+.2f}')
for e, d in s.groupby('empresa'):
    if len(d) >= 30:
        print(f'   {e}: {spearman(d["brecha"], d["rivales_3km"]):+.2f} (n = {len(d)}; rivales mediana {d["rivales_3km"].median():.0f})')

print('\n=== E. Empresas con la canasta núcleo (fideos + galletitas dulces, el 64% del peso), últimos 12 meses ===')
bs = pd.read_parquet(SIM / 'sim_bt_sub.parquet')
bs = bs[bs['mes'].isin(ult12) & bs['tipo'].isin(['Fideos secos', 'Galletitas dulces'])]
nac = bs.groupby(['tipo', 'subtipo'])['brecha_pct'].median()
filas = []
for e, d in bs.groupby('empresa'):
    if d['suc_key'].nunique() < 30:
        continue
    st = d.groupby(['tipo', 'subtipo']).agg(b=('brecha_pct', 'median'), n=('suc_key', 'nunique'))
    st = st.reindex(nac.index)
    imp = st['n'].fillna(0) < 10
    st.loc[imp, 'b'] = nac[imp]
    tipos = np.exp(np.log1p(st['b'] / 100).groupby(level='tipo').mean()) - 1
    can = (W['Fideos secos'] * (1 + tipos['Fideos secos']) + W['Galletitas dulces'] * (1 + tipos['Galletitas dulces'])) \
        / (W['Fideos secos'] + W['Galletitas dulces']) - 1
    peso_imp = sum((W[t] / (W['Fideos secos'] + W['Galletitas dulces'])) * imp.xs(t, level='tipo').mean()
                   for t in ('Fideos secos', 'Galletitas dulces'))
    filas.append({'empresa': e, 'sucursales': d['suc_key'].nunique(), 'canasta_nucleo': 100 * can,
                  'fideos': 100 * tipos['Fideos secos'], 'dulces': 100 * tipos['Galletitas dulces'],
                  'peso_imputado_pct': 100 * peso_imp})
print(pd.DataFrame(filas).sort_values('canasta_nucleo').round(1).to_string(index=False))

print('\n=== F. Disponibilidad: sucursales que venden el tipo con TACC y también sin TACC (últimos 12 meses) ===')
dd = pd.read_parquet(SIM / 'sim_datos_dia.parquet', columns=['id_comercio', 'id_bandera', 'id_sucursal', 'mes', 'tipo', 'rol'])
dd = dd[dd['mes'].isin(ult12)]
dd['suc_key'] = dd['id_comercio'] + '|' + dd['id_bandera'] + '|' + dd['id_sucursal']
dd = dd.merge(g[['suc_key', 'empresa', 'region']], on='suc_key')     # el universo del nb06 (sin web, sin estaciones)
lados = dd.groupby(['suc_key', 'tipo', 'empresa', 'region'])['rol'].agg(lambda r: set(r)).reset_index()
lados['con'] = lados['rol'].map(lambda r: 'tacc' in r); lados['ambos'] = lados['rol'].map(lambda r: {'tacc', 'sin'} <= r)
L = lados[lados['con']]
print((L.groupby('tipo')['ambos'].mean() * 100).round(1).to_string())
print('   por región (promedio de los tipos, ponderado ENGHo):')
r = (L.groupby(['region', 'tipo'])['ambos'].mean() * 100).unstack('tipo')
r['ponderado'] = sum(r[t] * W[t] for t in W) / sum(W.values())
print(r.round(0).to_string())
print('   por empresa (>= 30 sucursales con el lado con TACC):')
e = (L.groupby(['empresa', 'tipo'])['ambos'].mean() * 100).unstack('tipo')
n = L.groupby('empresa')['suc_key'].nunique()
e = e[n.reindex(e.index) >= 30]
print(e.round(0).to_string())

print('\n=== H. Brecha (canasta comparable) por tipo de local, últimos 12 meses ===')
print(s.groupby('sucursales_tipo')['brecha'].agg(['median', 'size']).round(1).to_string())
for e_ in ('Carrefour', 'Cencosud (Vea, Disco, Jumbo)'):
    print(f'   {e_}:', s[s['empresa'] == e_].groupby('sucursales_tipo')['brecha'].agg(['median', 'size']).round(1).to_dict())
