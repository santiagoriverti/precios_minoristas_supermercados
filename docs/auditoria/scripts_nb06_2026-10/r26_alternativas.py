# Efecto de cada corrección posible de la selección sobre la brecha, con el estimador del nb06 simplificado (sin la
# imputación de subtipos ni el panel balanceado): precio del lado en sucursal x mes x subtipo = mediana $/100 g de sus
# productos presentes (un producto con varios códigos: mediana de sus códigos vigentes); brecha nacional del subtipo
# en el mes = mediana entre sucursales (>= 10); tipo = promedio geométrico de sus subtipos; canasta = pesos ENGHo.
# Precios: mediana exacta mensual por sucursal x EAN de s8 (precios_mes y precios_mes_2), sobre el universo de
# sucursales de la simulación (sim_suc_geo). La canasta base se calibra contra sim_bt_sub (nb06).
# Uso: python -I -X utf8 r26_alternativas.py <canasta.csv> <precios_mes> <precios_mes_2> <carpeta de la simulación> <salida.csv>
# Evaluación de las correcciones sobre la canasta del 2026-10-23 (80 códigos): las alternativas sacan o agregan
# códigos de esa canasta. Para comparar canastas armadas con s10, r27_comparar_canastas.py.
import sys
from pathlib import Path

import numpy as np
import pandas as pd

pd.set_option('display.width', 250); pd.set_option('display.max_columns', 40)
CAN, D1, D2, SIM, OUT = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]), sys.argv[5]
W = {'Fideos secos': 1.503, 'Galletitas dulces': 1.717, 'Galletitas saladas y crackers': 1.407,
     'Pan rallado y rebozador': 0.194, 'Cereales rellenos (almohaditas)': 0.181}
FILT = {'23', '24'}
base = pd.read_csv(CAN, dtype={'ean': str, 'desde': str, 'hasta': str})
base = base[['tipo', 'lado', 'ean', 'producto', 'subtipo', 'gramos', 'desde', 'hasta']].copy()
base['lado'] = base['lado'].map({'tacc': 'tacc', 'sin_tacc': 'sin'})


def fila(tipo, lado, ean, producto, subtipo, gramos, desde=None, hasta=None):
    return dict(tipo=tipo, lado=lado, ean=ean, producto=producto, subtipo=subtipo, gramos=gramos, desde=desde,
                hasta=hasta)


F, D, S = 'Fideos secos', 'Galletitas dulces', 'Galletitas saladas y crackers'
BLUE = ['7730114100077', '7730114100015', '7730114100046']
EXTRA = {
    'tira_sin_matarazzo': [fila(F, 'sin', '7790070321855', 'Tirabuzón sin TACC Matarazzo 500 g', 'Tirabuzón / fusilli',
                                500, None, '2023-09'),
                           fila(F, 'sin', '7790070335982', 'Tirabuzón sin TACC Matarazzo 500 g', 'Tirabuzón / fusilli',
                                500, '2023-10', None)],
    'mana_limon': [fila(D, 'tacc', '7790040133259', 'Galletitas Vainilla Rellenas Limón Maná 152 Gr', 'Rellenas', 152)],
    'opera_92': [fila(D, 'tacc', '77903518', 'Galletitas Obleas Rellena Opera 92 Gr', 'Obleas', 92)],
    'lasfor_4': [fila('Cereales rellenos (almohaditas)', 'tacc', '7798169802667', 'Lasfor Chocolate Suizo 200 g',
                      'Almohaditas rellenas', 200),
                 fila('Cereales rellenos (almohaditas)', 'tacc', '7798169802674', 'Lasfor Crema de Frutilla 200 g',
                      'Almohaditas rellenas', 200)],
}


def alt(nombre):
    b = base.copy()
    if 'sin_blue' in nombre:
        b = b[~b['ean'].isin(BLUE)]
    if 'tira_mat' in nombre:
        b = pd.concat([b, pd.DataFrame(EXTRA['tira_sin_matarazzo'])])
    if 'mana' in nombre:
        b = b[b['ean'] != '7790040133242']
        b = pd.concat([b, pd.DataFrame(EXTRA['mana_limon'])])
    if 'opera92' in nombre:
        b = b[b['ean'] != '7790040008175']
        b = pd.concat([b, pd.DataFrame(EXTRA['opera_92'])])
    if 'opera_ambas' in nombre:
        b = pd.concat([b, pd.DataFrame(EXTRA['opera_92'])])
    if 'lasfor' in nombre:
        b = pd.concat([b, pd.DataFrame(EXTRA['lasfor_4'])])
    if 'crack_sin_arroz' in nombre:       # crackers: solo crackers de los dos lados (sin las galletas de arroz)
        b = b[~((b['subtipo'] == 'Crackers y galletas de arroz') & b['producto'].str.contains('Arroz', case=False))]
    return b.reset_index(drop=True)


ALTS = ['base', 'sin_blue', 'tira_mat', 'sin_blue+tira_mat', 'mana', 'opera92', 'opera_ambas', 'lasfor',
        'crack_sin_arroz', 'sin_blue+tira_mat+mana+lasfor']
todos = pd.concat([alt(a) for a in ALTS])
EANS = sorted(set(todos['ean']))
fs = sorted(D1.glob('*.parquet')) + sorted(D2.glob('*.parquet'))
P = pd.concat([pd.read_parquet(f, columns=['id_comercio', 'id_bandera', 'id_sucursal', 'ean', 'mes', 'precio_mediana'],
                               filters=[('ean', 'in', EANS)]) for f in fs], ignore_index=True)
P = P[~P['id_comercio'].isin(FILT)].drop_duplicates(['id_comercio', 'id_bandera', 'id_sucursal', 'ean', 'mes'])
sg = pd.read_parquet(SIM / 'sim_suc_geo.parquet')[['id_comercio', 'id_bandera', 'id_sucursal']].drop_duplicates()
P = P.merge(sg, on=['id_comercio', 'id_bandera', 'id_sucursal'])
print('precios:', P.shape, 'EANs con precio:', P['ean'].nunique(), 'de', len(EANS),
      '| sin precio:', sorted(set(EANS) - set(P['ean'])))
K = ['id_comercio', 'id_bandera', 'id_sucursal', 'mes']


def brecha_sub(spec):
    s = spec.copy()
    x = P.merge(s, on='ean')
    ok = (x['desde'].isna() | (x['mes'] >= x['desde'].fillna(''))) & (x['hasta'].isna() | (x['mes'] <= x['hasta'].fillna('9999')))
    x = x[ok].copy()
    x['p100'] = x['precio_mediana'] / x['gramos'].astype(float) * 100
    pp = x.groupby(K + ['tipo', 'subtipo', 'lado', 'producto'])['p100'].median()
    lado = pp.groupby(level=K + ['tipo', 'subtipo', 'lado']).median().unstack('lado').dropna()
    lado['brecha'] = lado['sin'] / lado['tacc'] - 1
    return lado.reset_index()


def resumen(bs):
    m = bs.groupby(['mes', 'tipo', 'subtipo']).agg(g=('brecha', 'median'), n=('brecha', 'size')).reset_index()
    m = m[m['n'] >= 10]
    t = (m.assign(lg=np.log1p(m['g'])).groupby(['mes', 'tipo'])['lg'].mean().pipe(np.expm1).rename('g').reset_index())
    t['w'] = t['tipo'].map(W)
    c = t.groupby('mes').apply(lambda d: (d['w'] * (1 + d['g'])).sum() / d['w'].sum() - 1, include_groups=False)
    return m, t, c


ult = [f'{y}-{mm:02d}' for y, mm in [(2025, 11), (2025, 12)] + [(2026, i) for i in range(1, 11)]]
filas, res = [], {}
for a in ALTS:
    bs = brecha_sub(alt(a))
    m, t, c = resumen(bs)
    res[a] = (bs, m, t, c)
    r = {'alternativa': a, 'canasta_ult12': 100 * c[c.index.isin(ult)].mean(),
         'canasta_2022': 100 * c[c.index.str.startswith('2022')].mean(), 'canasta_todo': 100 * c.mean()}
    for tp in W:
        tt = t[t['tipo'] == tp]
        r[f'{tp[:14]}_ult12'] = 100 * tt[tt['mes'].isin(ult)]['g'].mean()
    for (tp, st), g in m.groupby(['tipo', 'subtipo']):
        r[f'sub:{st[:22]}'] = 100 * g[g['mes'].isin(ult)]['g'].mean()
        r[f'n:{st[:22]}'] = int(bs[(bs['subtipo'] == st) & bs['mes'].isin(ult)].shape[0])
    filas.append(r)
R = pd.DataFrame(filas).set_index('alternativa')
R.round(1).T.to_csv(OUT)
print(R[[c for c in R.columns if not c.startswith(('sub:', 'n:'))]].round(1).to_string())
print()
sub = R[[c for c in R.columns if c.startswith('sub:')]].round(1).T
print(sub.to_string())
print()
print(R[[c for c in R.columns if c.startswith('n:')]].T.to_string())

# calibración de la base contra el nb06 (sim_bt_sub): misma brecha por sucursal x mes x subtipo
nb = pd.read_parquet(SIM / 'sim_bt_sub.parquet', columns=K + ['subtipo', 'brecha_pct'])
b0 = res['base'][0]
mm = b0.merge(nb, on=K + ['subtipo'], how='outer', indicator=True)
print('\nCalibración base vs nb06 (sucursal x mes x subtipo):', mm['_merge'].value_counts().to_dict())
both = mm[mm['_merge'] == 'both']
d = (100 * both['brecha'] - both['brecha_pct']).abs()
print(f'  diferencia |pp|: mediana {d.median():.4f}, p99 {d.quantile(0.99):.4f}, máx {d.max():.3f}')
