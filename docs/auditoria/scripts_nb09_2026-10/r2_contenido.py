# Contenido del ranking del nb09 v2: puntaje, componentes, codigos, precios, cadenas, cruces con otras salidas.
# Uso: python -I -X utf8 r2_contenido.py <carpeta datos> <carpeta proyectos>
import sys
from pathlib import Path
import numpy as np
import pandas as pd

D, PRY = Path(sys.argv[1]), Path(sys.argv[2])
R = pd.read_parquet(D / 'trazabilidad_productos_20220101_20261015.parquet')
P = pd.read_parquet(D / 'panel_mensual_productos_20220101_20261015.parquet')
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 40); pd.set_option('display.max_colwidth', 50)
COMP = ['pct_dias', 'pct_suc_diaria_prom', 'pct_com_diaria_prom', 'pct_provincias']

print('=== Puntaje por tipo de codigo ===')
R['tipo'] = np.select([R['es_ean'] & R['en_maestro'], R['es_ean'], R['en_maestro']],
                      ['EAN en maestro', 'EAN fuera del maestro', 'interno en maestro'], 'interno fuera del maestro')
print(R.groupby('tipo').agg(n=('puntaje', 'size'), mediana=('puntaje', 'median'), p90=('puntaje', lambda s: s.quantile(.9)),
                            ge50=('puntaje', lambda s: (s >= 50).sum()), ge75=('puntaje', lambda s: (s >= 75).sum())).round(1))
print('\nblacklist:', int(R['blacklist'].sum()), '| con puntaje >= 50:', int((R['blacklist'] & (R['puntaje'] >= 50)).sum()))

print('\n=== Componentes (productos con puntaje >= 50) ===')
A = R[R['puntaje'] >= 50]
print(A[COMP].describe(percentiles=[.1, .5, .9]).round(1).T)
lim = A[COMP].idxmin(axis=1).value_counts()
print('componente que limita (el minimo):', lim.to_dict())
print('\nmax de cada componente en todo el ranking:', R[COMP].max().round(2).to_dict())
print('pct_com_diaria_prom: cuantiles del top 100:', R.head(100)['pct_com_diaria_prom'].quantile([0, .5, 1]).round(1).to_dict())

print('\n=== Codigos (es_ean) ===')
ids = R['id_producto'].astype(str)
L = ids.str.len()
dig = ids.str.isdigit()
print('no numericos:', int((~dig).sum()), '| ejemplos:', ids[~dig].head(8).tolist())
print('largo de los EAN:', L[R['es_ean']].value_counts().sort_index().to_dict())
print('largo de los internos numericos:', L[~R['es_ean'] & dig].value_counts().sort_index().head(16).to_dict())
def dv_ok(x):
    z = x.zfill(14); d = [int(c) for c in z[:-1]][::-1]
    return (10 - sum(v * (3 if i % 2 == 0 else 1) for i, v in enumerate(d)) % 10) % 10 == int(z[-1])
m = dig & L.between(8, 14)
dv = pd.Series([bool(mm) and dv_ok(x) for x, mm in zip(ids, m)], index=R.index, dtype=bool)
restr = ((L.isin([8, 13])) & ids.str[0].eq('2')) | ((L == 12) & ids.str[0].isin(['2', '4']))
print('es_ean=True con DV invalido:', int((R['es_ean'] & ~dv).sum()), '| en rango restringido:', int((R['es_ean'] & restr).sum()))
print('internos con DV valido (balanza/uso interno o marcados 0 en maestro):', int((~R['es_ean'] & dv).sum()),
      '| de ellos rango restringido:', int((~R['es_ean'] & dv & restr).sum()))
print('internos (es_ean False) en top 2.496 (>=50):', int((~A['es_ean']).sum()))
print(A.loc[~A['es_ean'], ['ranking', 'id_producto', 'descripcion', 'puntaje', 'comercios', 'cadena_principal', 'pct_cadena_principal']].head(12).to_string(index=False))

print('\n=== Top 30 ===')
cols = ['ranking', 'id_producto', 'descripcion', 'rubro', 'puntaje', 'pct_suc_diaria_prom', 'pct_com_diaria_prom', 'comercios', 'cadena_principal', 'pct_cadena_principal']
print(R[cols].head(30).to_string(index=False))
print('\nrubros del top 100:', R.head(100)['rubro'].value_counts().to_dict())
print('rubros del top 1000:', R.head(1000)['rubro'].value_counts().head(12).to_dict())

print('\n=== Productos basicos: el mejor de cada uno ===')
for pat in ['^Leche ', '^Aceite ', '^Yerba ', '^Arroz ', '^Az[uú]car ', '^Harina ', '^Fideos ', '^Pan ', '^Huevo', '^Gaseosa ',
            '^Agua ', '^Cerveza ', '^Vino ', 'Papel Higi', 'Detergente', 'Lavandina', 'Jab[oó]n', 'Shampoo', 'Pa[nñ]al']:
    s = R[R['descripcion'].fillna('').str.contains(pat, case=False, regex=True)]
    if len(s):
        x = s.iloc[0]
        print(f'  {pat:14s} n={len(s):5d} mejor: #{x.ranking:6d} {str(x.descripcion)[:45]:45s} punt {x.puntaje:5.1f} '
              f'| suc {x.pct_suc_diaria_prom:5.1f} com {x.pct_com_diaria_prom:5.1f} | >=50: {(s.puntaje >= 50).sum()}')

print('\n=== Cadenas presentes en el top 100 (frecuencia) ===')
from collections import Counter
cnt = Counter()
for c in R.head(100)['cadenas']:
    cnt.update(c.split('; '))
print(dict(cnt.most_common()))
cnt_all = Counter()
for c in R['cadenas']:
    cnt_all.update(c.split('; '))
print('\nproductos por cadena (todo el ranking):', dict(cnt_all.most_common()))

print('\n=== Precio del ultimo mes: extremos ===')
pm = R[['ranking', 'id_producto', 'descripcion', 'presentacion', 'precio_mediano_ultimo_mes', 'cv_precio_ultimo_mes_%', 'sucursales_ultimo_mes', 'cadena_principal']]
print('mas caros:'); print(pm.sort_values('precio_mediano_ultimo_mes', ascending=False).head(8).to_string(index=False))
print('mas baratos (>= 10 suc):'); print(pm[pm['sucursales_ultimo_mes'] >= 10].sort_values('precio_mediano_ultimo_mes').head(8).to_string(index=False))
print('cv > 100% con >= 30 sucursales:', int(((R['cv_precio_ultimo_mes_%'] > 100) & (R['sucursales_ultimo_mes'] >= 30)).sum()))
print(pm[(R['cv_precio_ultimo_mes_%'] > 100) & (R['sucursales_ultimo_mes'] >= 30)].sort_values('cv_precio_ultimo_mes_%', ascending=False).head(10).to_string(index=False))

print('\n=== Rubros y categorias del maestro (formas) ===')
import unicodedata
def k(v):
    return unicodedata.normalize('NFKD', str(v)).encode('ascii', 'ignore').decode().lower().strip()
for c in ['rubro', 'categoria', 'subcategoria']:
    u = pd.Series(R[c].dropna().unique())
    dup = u.groupby(u.map(k)).size()
    print(f'  {c}: {len(u)} valores, {int((dup > 1).sum())} con mas de una forma')
print('  rubros:', sorted(R['rubro'].dropna().unique()))

print('\n=== Continuidad ===')
print('continuo_periodo:', int(R['continuo_periodo'].sum()), '| continuo_util:', int(R['continuo_util'].sum()))
C = R[R['continuo_periodo']]
print('  de los continuos: EAN', int(C['es_ean'].sum()), '| en maestro', int(C['en_maestro'].sum()),
      '| suc_diarias_min >= 100:', int((C['suc_diarias_min'] >= 100).sum()), '| >= 300:', int((C['suc_diarias_min'] >= 300).sum()))
print('  rubros de los continuos con suc_diarias_min >= 100:', C[C['suc_diarias_min'] >= 100]['rubro'].value_counts().head(12).to_dict())

print('\n=== Cruce 1: canasta Continua 2022 (nb08, lector independiente) ===')
cc = pd.read_excel(PRY / 'canasta_continua_cantidad_07.xlsx', sheet_name=None)
for n, df in cc.items():
    print('  hoja', n, df.shape, list(df.columns)[:12])
sel = list(cc.values())[0]
col_ean = [c for c in sel.columns if 'ean' in c.lower() or 'producto' in c.lower()][0]
sel['id'] = sel[col_ean].astype(str).str.strip().str.replace(r'\.0$', '', regex=True).str.lstrip('0')
q = [c for c in sel.columns if 'cantidad_07' in c]
s7 = sel[sel[q[0]].fillna(0) > 0] if q else sel
X = R.set_index('id_producto').reindex(s7['id'])
print(f'  {len(s7)} productos; en el ranking: {int(X["ranking"].notna().sum())}; continuo_periodo: {int(X["continuo_periodo"].fillna(False).sum())}')
print(X[['ranking', 'descripcion', 'dias_con_precio', 'suc_diarias_min', 'puntaje']].sort_values('ranking').to_string())

print('\n=== Cruce 2: muestra v1 local (may-jul 2026) vs panel mensual v2 ===')
M = pd.read_excel(PRY / 'trazabilidad_productos_MUESTRA_20260501_20260731.xlsx', sheet_name='Ranking', engine='calamine',
                  dtype={'id_producto': str})
print('  muestra:', M.shape)
Pm = P[P['mes'].isin(['2026-05', '2026-06', '2026-07'])].copy()
Pm['sd'] = Pm['suc_diarias_prom'].astype(float) * Pm['dias_con_precio']
g = Pm.groupby('id_producto').agg(d=('dias_con_precio', 'sum'), sd=('sd', 'sum'))
Y = M.set_index('id_producto')[['dias_con_precio', 'sucursal_dias']].join(g, how='outer')
print('  productos solo en la muestra:', int(Y['d'].isna().sum()), '| solo en el panel:', int(Y['dias_con_precio'].isna().sum()))
Y = Y.dropna()
print('  dias distintos:', int((Y['d'] != Y['dias_con_precio']).sum()), 'de', len(Y))
r = np.abs(Y['sd'] - Y['sucursal_dias'])
print('  sucursal-dias: |dif| > 0,05*dias:', int((r > 0.05 * Y['d'] + 1e-6).sum()))
print(Y[Y['d'] != Y['dias_con_precio']].head(10))
