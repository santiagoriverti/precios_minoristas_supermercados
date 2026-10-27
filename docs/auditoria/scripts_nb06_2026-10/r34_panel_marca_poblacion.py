# Análisis de expertos (2): composición por empresa del panel balanceado, pares de la misma marca, ponderación por
# población provincial y bootstrap por empresa de la brecha nacional. Sobre los paneles de datos/ de una simulación.
# Uso: python -I -X utf8 r34_panel_marca_poblacion.py <carpeta datos> <canasta.csv>
# (exploratorio: la versión del notebook está en las hojas Composicion_empresas, Sensibilidad, IC_grupos y Prima_misma_marca)
import re, sys
from pathlib import Path
import numpy as np
import pandas as pd
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30); pd.set_option('display.max_rows', 200)
D, CAN = Path(sys.argv[1]), Path(sys.argv[2])
S = pd.read_csv(D / 'sucursales.csv', dtype={'suc_key': str, 'departamento_id': str})
B = pd.read_parquet(D / 'panel_sucursal_mes_subtipo.parquet')
B['anio'] = B['mes'].str[:4]
U = sorted(B['mes'].unique())[-12:]

# a) panel balanceado: sucursal x subtipo presentes en >= 70% de los meses (como la CELDA 8)
nm = B['mes'].nunique()
pres = B.groupby(['suc_key', 'subtipo'])['mes'].nunique()
bal = set(pres[pres >= 0.7 * nm].index)
Bb = B[[(s, t) in bal for s, t in zip(B['suc_key'], B['subtipo'])]]
c = Bb.groupby(['anio', 'empresa']).size().unstack('empresa').fillna(0)
c = c.div(c.sum(axis=1), axis=0).mul(100)
print('a) Panel balanceado: % de las sucursal-mes-subtipo por empresa y año')
print(c.loc[:, c.max() > 2].round(1).to_string())

# b) brecha nacional de los últimos 12 meses: mediana por subtipo y mes (sucursales iguales) contra ponderada por
# población provincial (cada provincia pesa por su población, repartida entre sus sucursales)
POB = {'Buenos Aires': 17569053, 'CABA': 3120612, 'Catamarca': 429556, 'Chaco': 1142963, 'Chubut': 603120,
       'Córdoba': 3978984, 'Corrientes': 1197553, 'Entre Ríos': 1426426, 'Formosa': 606041, 'Jujuy': 797955,
       'La Pampa': 361394, 'La Rioja': 384607, 'Mendoza': 2014533, 'Misiones': 1280960, 'Neuquén': 726590,
       'Río Negro': 762067, 'Salta': 1440672, 'San Juan': 818234, 'San Luis': 540905, 'Santa Cruz': 333473,
       'Santa Fe': 3556522, 'Santiago del Estero': 1054028, 'Tierra del Fuego': 190641, 'Tucumán': 1731820}
x = B[B['mes'].isin(U)].copy()
def wmed(v, w):
    o = np.argsort(v); v, w = v[o], w[o]; c = np.cumsum(w) / w.sum()
    return float(v[np.searchsorted(c, 0.5)])
x['_n'] = x.groupby(['mes', 'subtipo', 'PROVINCIA_NORM'])['suc_key'].transform('size')
x['_w'] = x['PROVINCIA_NORM'].map(POB).fillna(0) / x['_n']
r = x.groupby(['tipo', 'subtipo', 'mes']).apply(lambda g: pd.Series({
    'med': g['brecha_pct'].median(), 'med_pob': wmed(g['brecha_pct'].to_numpy(), g['_w'].to_numpy()) if g['_w'].sum() > 0 else np.nan}),
    include_groups=False)
rr = r.groupby(level=['tipo', 'subtipo']).mean()
print('\nb) Brecha por subtipo, últimos 12 meses (promedio de las medianas mensuales): sucursales iguales vs población')
print(rr.round(1).to_string())
print('provincias en el panel:', sorted(set(x['PROVINCIA_NORM']) - set(POB)))

# c) bootstrap de la brecha de un subtipo por empresa (las empresas con sus sucursales) contra por sucursal
rng = np.random.default_rng(20261027)
for st in ['Spaghetti', 'Crackers', 'Rellenas']:
    g = x[x['subtipo'] == st]
    emps = g['empresa'].unique(); sucs = g['suc_key'].unique()
    est = g.groupby('mes')['brecha_pct'].median().mean()
    be, bs = [], []
    for _ in range(300):
        e = rng.choice(emps, len(emps)); ge = pd.concat([g[g['empresa'] == k] for k in e])
        be.append(ge.groupby('mes')['brecha_pct'].median().mean())
        s = rng.choice(sucs, len(sucs)); gs = g.set_index('suc_key').loc[s].reset_index()
        bs.append(gs.groupby('mes')['brecha_pct'].median().mean())
    print(f'c) {st}: {est:.1f}% | IC 95% por sucursal {np.percentile(bs, 2.5):.1f} a {np.percentile(bs, 97.5):.1f} | '
          f'por empresa {np.percentile(be, 2.5):.1f} a {np.percentile(be, 97.5):.1f} ({len(emps)} empresas)')

# d) pares de la misma marca (por la descripción de la canasta)
can = pd.read_csv(CAN, dtype={'ean': str})
MARCAS = ['matarazzo', 'lucchetti', 'wakas', 'smams', 'samms', 'terrabusi', 'snuks', 'lasfor', 'oreo', 'la salteña',
          'preferido', 'mamá cocina', 'exquisita', 'arcor', 'santa maría', 'santa maria', 'crisppino', 'grandiet', 'aglu',
          'bagley', 'don satur', 'paseo', 'criollitas', 'saladix', 'kesitas', 'rex', 'pepitos', 'opera', 'toddy']
def marca(d):
    d = d.lower()
    for m in MARCAS:
        if m in d:
            return {'samms': 'smams', 'santa maria': 'santa maría'}.get(m, m)
    return '?'
can['marca'] = can['descripcion'].map(marca)
pairs = can.groupby(['subtipo', 'marca'])['lado'].nunique().pipe(lambda s: s[s == 2]).reset_index()[['subtipo', 'marca']]
print('\nd) Marcas con los dos lados en un subtipo de la canasta:'); print(pairs.to_string(index=False))
