# Controles internos del ranking del nb09 v2 (parquet) y del panel mensual.
# Uso: python -I r1_consistencia.py <carpeta datos>
import sys
from pathlib import Path
import numpy as np
import pandas as pd

D = Path(sys.argv[1])
R = pd.read_parquet(D / 'trazabilidad_productos_20220101_20261015.parquet')
P = pd.read_parquet(D / 'panel_mensual_productos_20220101_20261015.parquet')
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 80); pd.set_option('display.max_colwidth', 60)

print('=== Esquema ===')
print(len(R), 'filas', R.shape[1], 'columnas')
print(list(R.columns))
print(R.dtypes.value_counts().to_dict())

fallas = []
def chk(nombre, mask, cols=None, n=8):
    m = np.asarray(mask, bool)
    k = int(m.sum())
    print(f'[{"OK " if k == 0 else "MAL"}] {nombre}: {k:,}')
    if k:
        fallas.append((nombre, k))
        if cols:
            print(R.loc[m, cols].head(n).to_string(index=False))

print('\n=== Identidad y orden ===')
chk('id_producto repetido', R['id_producto'].duplicated())
chk('ranking no es 1..N', R['ranking'].to_numpy() != np.arange(1, len(R) + 1))
chk('puntaje no decreciente', np.diff(R['puntaje'].to_numpy()) > 1e-9)

print('\n=== Constantes ===')
for c in ['dias_periodo', 'meses_periodo', 'sucursales_total', 'comercios_total', 'banderas_total', 'provincias_total',
          'regiones_total', 'departamentos_total', 'localidades_total']:
    print(f'  {c}: {sorted(R[c].unique())[:5]}')

print('\n=== Puntaje recalculado ===')
comp = R[['pct_dias', 'pct_suc_diaria_prom', 'pct_com_diaria_prom', 'pct_provincias']].to_numpy() / 100
p2 = np.prod(np.clip(comp, 0, 1), axis=1) ** 0.25 * 100
dif = np.abs(p2 - R['puntaje'].to_numpy())
print(f'  dif max {dif.max():.5f}, p99 {np.quantile(dif, .99):.5f}')
chk('puntaje != media geometrica (> 0,006)', dif > 0.006)

print('\n=== Rangos ===')
for c in [c for c in R.columns if c.startswith('pct_')]:
    chk(f'{c} fuera de [0,100]', (R[c] < -1e-9) | (R[c] > 100 + 1e-6))
ND = int(R['dias_periodo'].iat[0])
chk('pct_dias != dias_con_precio/dias_periodo', np.abs(R['pct_dias'] - R['dias_con_precio'] / ND * 100) > 1e-3)
chk('dias_con_precio = 0', R['dias_con_precio'] == 0)
chk('provincias > provincias_total', R['provincias'] > R['provincias_total'])
chk('pct_provincias != provincias/total', np.abs(R['pct_provincias'] - R['provincias'] / R['provincias_total'] * 100) > 1e-3)
chk('regiones > regiones_total', R['regiones'] > R['regiones_total'])
chk('comercios > comercios_total', R['comercios'] > R['comercios_total'])
chk('banderas < comercios', R['banderas'] < R['comercios'])
chk('comercios = 0', R['comercios'] == 0)

print('\n=== Sucursales ===')
chk('suc_diarias_prom > sucursales_distintas', R['suc_diarias_prom'] > R['sucursales_distintas'] + 1e-6,
    ['id_producto', 'suc_diarias_prom', 'sucursales_distintas'])
chk('suc_diarias_min > suc_diarias_prom', R['suc_diarias_min'] > R['suc_diarias_prom'] + 0.006)
chk('sucursal_dias < sucursales_distintas', R['sucursal_dias'] < R['sucursales_distintas'])
chk('sucursal_dias != suc_diarias_prom*dias (rel > 1e-3)',
    np.abs(R['sucursal_dias'] - R['suc_diarias_prom'] * R['dias_con_precio']) / R['sucursal_dias'] > 1e-3)
chk('sucursales_distintas > total', R['sucursales_distintas'] > R['sucursales_total'])
chk('sucursales_ultimo_mes > sucursales_distintas', R['sucursales_ultimo_mes'] > R['sucursales_distintas'])
chk('pct_suc_diaria_periodo > pct_suc_diaria_prom', R['pct_suc_diaria_periodo'] > R['pct_suc_diaria_prom'] + 1e-3)
chk('pct_suc_diaria_periodo != prom*pct_dias/100',
    np.abs(R['pct_suc_diaria_periodo'] - R['pct_suc_diaria_prom'] * R['pct_dias'] / 100) > 2e-3)

print('\n=== Concentracion ===')
h = R['hhi_cadenas']; s = R['pct_cadena_principal'] / 100
chk('hhi NaN', h.isna())
chk('hhi < 1/comercios', h < 1 / R['comercios'] - 1e-4, ['id_producto', 'comercios', 'hhi_cadenas'])
chk('hhi > 1', h > 1 + 1e-9)
chk('hhi < cuota_max^2', h < s ** 2 - 1e-4)
chk('hhi > cuota_max', h > s + 1e-4)
chk('comercios = 1 y hhi != 1', (R['comercios'] == 1) & (np.abs(h - 1) > 1e-6))
ncad = R['cadenas'].fillna('').map(lambda x: len(x.split('; ')) if x else 0)
chk('cantidad en "cadenas" != comercios', ncad != R['comercios'], ['id_producto', 'comercios', 'cadenas'])
chk('cadena_principal no esta en cadenas',
    [cp not in c.split('; ') for cp, c in zip(R['cadena_principal'].fillna(''), R['cadenas'].fillna(''))])

print('\n=== Provincias presentes/faltantes ===')
npres = R['provincias_presentes'].fillna('').map(lambda x: len(x.split('; ')) if x else 0)
nfalt = R['provincias_faltantes'].fillna('').map(lambda x: len(x.split('; ')) if x else 0)
T = R['provincias_total']
chk('presentes: cantidad != provincias', (R['provincias'] <= T / 2) & (npres != R['provincias']))
chk('faltantes: cantidad != total - provincias', (R['provincias'] > T / 2) & (nfalt != T - R['provincias']))
todas = set()
for x in R['provincias_presentes'].dropna():
    todas.update(y for y in x.split('; ') if y)
for x in R['provincias_faltantes'].dropna():
    todas.update(y for y in x.split('; ') if y)
print(f'  nombres de provincia que aparecen: {len(todas)} -> {sorted(todas)}')

print('\n=== Temporal ===')
chk('primer_dia > ultimo_dia', R['primer_dia'] > R['ultimo_dia'])
chk('racha_max > dias_con_precio', R['racha_max_dias'] > R['dias_con_precio'])
chk('dias_utiles > dias_con_precio', R['dias_utiles'] > R['dias_con_precio'])
chk('continuo_periodo != (dias == ND)', R['continuo_periodo'] != (R['dias_con_precio'] == ND))
chk('continuo_util != (utiles == ND)', R['continuo_util'] != (R['dias_utiles'] == ND))
chk('continuo y racha != ND', R['continuo_periodo'] & (R['racha_max_dias'] != ND))
chk('continuo y hueco > 0', R['continuo_periodo'] & (R['hueco_max_dias'] > 0))
chk('pct_dias_desde_aparicion > 100', R['pct_dias_desde_aparicion'] > 100 + 1e-6)
chk('meses_con_precio > meses_periodo', R['meses_con_precio'] > R['meses_periodo'])
chk('dias_desde_ultimo < 0', R['dias_desde_ultimo'] < 0)
F0, F1 = R['primer_dia'].min(), R['ultimo_dia'].max()
print(f'  primer_dia min {F0:%d/%m/%Y}, ultimo_dia max {F1:%d/%m/%Y}')
chk('dias_desde_ultimo = 0 y ultimo_dia != F1', (R['dias_desde_ultimo'] == 0) & (R['ultimo_dia'] != F1))

print('\n=== Precio ===')
pm = R['precio_mediano_ultimo_mes']
chk('suc_ultimo_mes > 0 y sin precio', (R['sucursales_ultimo_mes'] > 0) & pm.isna())
chk('suc_ultimo_mes = 0 y con precio', (R['sucursales_ultimo_mes'] == 0) & pm.notna())
chk('precio <= 0', pm <= 0)
chk('ultimo_dia en oct-26 y suc_ultimo_mes = 0', (R['ultimo_dia'] >= '2026-10-01') & (R['sucursales_ultimo_mes'] == 0))
chk('ultimo_dia antes de oct-26 y suc_ultimo_mes > 0', (R['ultimo_dia'] < '2026-10-01') & (R['sucursales_ultimo_mes'] > 0))
print('  precio mediano ult. mes, cuantiles:', pm.quantile([0, .001, .01, .5, .99, .999, 1]).round(2).to_dict())
print('  cv ult. mes, cuantiles:', R['cv_precio_ultimo_mes_%'].quantile([.5, .9, .99, .999, 1]).round(1).to_dict())

print('\n=== Panel mensual ===')
print(len(P), 'filas;', P['mes'].nunique(), 'meses;', P['id_producto'].nunique(), 'productos')
print(P.dtypes.to_dict())
g = P.groupby('id_producto').agg(d=('dias_con_precio', 'sum'), m=('mes', 'size'),
                                  sd=('suc_diarias_prom', lambda s: 0))
g['sd'] = (P['suc_diarias_prom'] * P['dias_con_precio']).groupby(P['id_producto']).sum()
X = R.set_index('id_producto')[['dias_con_precio', 'meses_con_precio', 'sucursal_dias']].join(g, how='outer')
chk('producto en uno y no en el otro', X.isna().any(axis=1))
chk('sum(dias panel) != dias_con_precio', X['d'] != X['dias_con_precio'])
chk('meses en panel != meses_con_precio', X['m'] != X['meses_con_precio'])
rel = np.abs(X['sd'] - X['sucursal_dias']) / X['sucursal_dias']
print(f'  sucursal-dias panel vs ranking: dif rel max {rel.max():.2e} (redondeo a 0,1)')
chk('sucursal-dias panel vs ranking (rel > 1e-3 y abs > 0.05*dias)',
    (rel > 1e-3) & (np.abs(X['sd'] - X['sucursal_dias']) > 0.05 * X['d']))
dpm = P.groupby('mes')['dias_con_precio'].max()
print('  dias max por mes (= dias con dato del mes):')
print('  ', dpm.to_dict())

print('\n=== Resumen de fallas ===')
for f in fallas:
    print('  ', f)
print('total controles con fallas:', len(fallas))
