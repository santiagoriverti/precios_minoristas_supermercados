# Evidencia sobre el componente comercial, el regional y el corte de ago-2026 (fuente diaria via nb03).
import sys
import numpy as np
import pandas as pd
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30); pd.set_option('display.max_colwidth', 60)
R = pd.read_parquet(sys.argv[1] + '/trazabilidad_productos_20220101_20261015.parquet')
cad = R['cadenas'].map(lambda x: set(x.split('; ')))
GRANDES = {'Carrefour', 'ChangoMas', 'Coto', 'Libertad', 'Cencosud (Vea/Disco/Jumbo)', 'La Anónima', 'Cooperativa Obrera',
           'DIA', 'Toledo', 'Cadena 24'}
NO_SUPER = {'Axion Energy', 'Estación Lima', 'Cadena 2013', 'Cadena 19'}
DUP = {'Cadena 45', 'Cadena 46', 'Cadena 50'}
R['n_grandes'] = cad.map(lambda s: len(s & GRANDES))
R['n_no_super'] = cad.map(lambda s: len(s & NO_SUPER))
R['n_dup'] = cad.map(lambda s: len(s & DUP))
R['n_resto'] = R['comercios'] - R['n_grandes'] - R['n_no_super']
A = R[R['puntaje'] >= 50].copy()
A['tramo'] = pd.cut(A['ranking'], [0, 100, 500, 1000, 2500], labels=['1-100', '101-500', '501-1000', '1001-2496'])
print('Promedios por tramo del ranking (puntaje >= 50):')
print(A.groupby('tramo', observed=True)[['pct_suc_diaria_prom', 'pct_com_diaria_prom', 'n_grandes', 'n_no_super', 'n_dup', 'n_resto', 'comercios']].mean().round(2))
print('\ncorrelacion (puntaje>=50) pct_com_diaria_prom con: n_no_super %.2f | n_resto %.2f | n_grandes %.2f | pct_suc %.2f' % (
    A['pct_com_diaria_prom'].corr(A['n_no_super']), A['pct_com_diaria_prom'].corr(A['n_resto']),
    A['pct_com_diaria_prom'].corr(A['n_grandes']), A['pct_com_diaria_prom'].corr(A['pct_suc_diaria_prom'])))
for a, b in [('7790895000997', '7790742340108'), ('7790895641183', '7790060023684')]:
    x = R[R['id_producto'] == a].iloc[0]; y = R[R['id_producto'].isin([b])]
    if not len(y):
        continue
    y = y.iloc[0]
    print(f'\n#{x.ranking} {x.descripcion}: suc {x.pct_suc_diaria_prom:.1f} com {x.pct_com_diaria_prom:.1f} ({x.comercios})')
    print(f'#{y.ranking} {y.descripcion}: suc {y.pct_suc_diaria_prom:.1f} com {y.pct_com_diaria_prom:.1f} ({y.comercios})')
    print('  solo en el 1ro:', sorted(set(x.cadenas.split('; ')) - set(y.cadenas.split('; '))))
    print('  solo en el 2do:', sorted(set(y.cadenas.split('; ')) - set(x.cadenas.split('; '))))
print('\nLeche y aceite mejor ubicados:')
for pat in ['^Leche (Entera|Descremada|Parcialmente)', '^Aceite de Girasol', '^Yerba Mate', '^Az[uú]car (Com|Blanca|Refinada)', '^Arroz (Largo|Doble|Blanco|Parboil)', '^Fideos (Spaghetti|Tallar|Mostach)']:
    s = R[R['descripcion'].fillna('').str.contains(pat, regex=True)].head(3)
    for _, z in s.iterrows():
        print(f'  #{z.ranking:5d} {str(z.descripcion)[:55]:55s} punt {z.puntaje:5.1f} dias {z.pct_dias:5.1f} suc {z.pct_suc_diaria_prom:5.1f} com {z.pct_com_diaria_prom:5.1f} no_super {z.n_no_super}')

print('\nComponente regional: pct_provincias vs pct_prov_diaria_prom (puntaje >= 50)')
print(A[['pct_provincias', 'pct_prov_diaria_prom']].describe(percentiles=[.1, .5, .9]).round(1).T)
comp2 = np.column_stack([R['pct_dias'], R['pct_suc_diaria_prom'], R['pct_com_diaria_prom'], R['pct_prov_diaria_prom']]) / 100
p2 = np.prod(np.clip(comp2, 0, 1), axis=1) ** 0.25 * 100
r2 = pd.Series(p2).rank(ascending=False, method='first').astype(int).to_numpy()
print('con la cuota diaria de provincias: top 100 que siguen en el top 100:', int((r2[:100] <= 100).sum()),
      '| top 1000 en top 1000:', int((r2[:1000] <= 1000).sum()), '| >= 50:', int((p2 >= 50).sum()))

print('\nCorte de ago-2026 (el SEPA diario no trae 8 comercios):')
VAN = {'Cadena 19', 'Cadena 1000', 'Cadena 2000', 'Cadena 2002', 'Cadena 2005', 'Cadena 2007', 'Cadena 2013', 'Cadena 3001'}
jul = R['ultimo_dia'].between('2026-07-25', '2026-07-31')
solo_van = cad.map(lambda s: s <= VAN)
print('  ultimo dia entre el 25 y el 31/07/2026:', int(jul.sum()), '| de ellos solo en esos 8 comercios:', int((jul & solo_van).sum()))
print('  productos que alguna vez estuvieron solo en esos 8 comercios:', int(solo_van.sum()))
print('  ultimo_dia por mes (2026):', R.loc[R['ultimo_dia'] >= '2026-01-01', 'ultimo_dia'].dt.strftime('%Y-%m').value_counts().sort_index().to_dict())

print('\nBlacklist con puntaje >= 50:')
print(R[R['blacklist'] & (R['puntaje'] >= 50)][['ranking', 'id_producto', 'descripcion', 'rubro', 'puntaje']].to_string(index=False))
