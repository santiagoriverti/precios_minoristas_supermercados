# Compara dos corridas del nb09 (anterior y nueva) y revisa lo agregado el 2026-10-22: hoja Dias, comercios que dejaron
# de publicar, codigos con basura unidos a su EAN, precio simbolico.
# Uso: python -I -X utf8 r8_comparar_corridas.py <carpeta corrida anterior> <carpeta corrida nueva>
import re, sys
from pathlib import Path
import numpy as np
import pandas as pd

A, N = Path(sys.argv[1]), Path(sys.argv[2])
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30); pd.set_option('display.max_colwidth', 60)
R1 = pd.read_parquet(next(A.glob('trazabilidad_productos_*.parquet'))).set_index('id_producto')
R2 = pd.read_parquet(next(N.glob('trazabilidad_productos_*.parquet'))).set_index('id_producto')
P1 = pd.read_parquet(next(A.glob('panel_mensual_productos_*.parquet')))
P2 = pd.read_parquet(next(N.glob('panel_mensual_productos_*.parquet')))
H = pd.read_excel(next(N.glob('trazabilidad_productos_*.xlsx')), sheet_name=['Resumen', 'Cadenas', 'Dias'],
                  engine='calamine', dtype={'id_comercio': str})

def limpiar(x):
    m = re.match(r'^(\d{8,14})[^\x00-\x7f]', x)
    return m.group(1) if (not x.isascii() and m) else x

print('=== Productos ===')
print(f'anterior {len(R1):,} | nueva {len(R2):,}')
solo1 = R1.index.difference(R2.index); solo2 = R2.index.difference(R1.index)
print(f'solo en la anterior: {len(solo1)} (con basura: {sum(not i.isascii() for i in solo1)})')
print(f'solo en la nueva: {len(solo2)} | primer día de esos:', R2.loc[solo2, 'primer_dia'].dt.strftime('%Y-%m-%d').value_counts().sort_index().to_dict())
TAB = ['8806094046892', '8806094046908']
cols = ['dias_con_precio', 'sucursales_distintas', 'primer_dia', 'ultimo_dia', 'sucursal_dias', 'puntaje']
print('tablets Samsung (anterior / nueva):')
print(pd.concat([R1.loc[TAB, cols].add_suffix('_ant'), R2.loc[TAB, cols].add_suffix('_nva')], axis=1).T.to_string())

print('\n=== Panel mensual: meses cerrados (2022-01 a 2026-09) ===')
P1['id_producto'] = P1['id_producto'].map(limpiar)
P1['sd'] = P1['suc_diarias_prom'].astype(float) * P1['dias_con_precio']
P1g = P1.groupby(['id_producto', 'mes']).agg(d=('dias_con_precio', 'sum'), sd=('sd', 'sum')).reset_index()
c1, c2 = P1g[P1g['mes'] < '2026-10'], P2[P2['mes'] < '2026-10'].copy()
J = c1.merge(c2, on=['id_producto', 'mes'], how='outer', indicator=True)
B = J[J['_merge'] == 'both']
dd = B['d'] != B['dias_con_precio']
ds = np.abs(B['sd'] / B['d'] - B['suc_diarias_prom'].astype(float)) > 0.051
print(f'filas: {len(c1):,} vs {len(c2):,} | solo anterior {int((J["_merge"] == "left_only").sum())} | solo nueva '
      f'{int((J["_merge"] == "right_only").sum())} | días distintos {int(dd.sum())} | suc/día distintos {int(ds.sum())}')
print(B[dd | ds][['id_producto', 'mes', 'd', 'dias_con_precio', 'sd', 'suc_diarias_prom']].head(10).to_string(index=False))

print('\n=== Ranking: productos en las dos corridas ===')
C = R1.index.intersection(R2.index)
dd = (R2.loc[C, 'dias_con_precio'] - R1.loc[C, 'dias_con_precio'])
print('días con precio de más (los 7 días nuevos):', dd.value_counts().sort_index().to_dict())
print('primer día distinto:', int((R1.loc[C, 'primer_dia'] != R2.loc[C, 'primer_dia']).sum()))
for c in ['puntaje', 'pct_suc_diaria_prom', 'pct_com_diaria_prom', 'comercios', 'provincias', 'sucursales_distintas']:
    d = (R2.loc[C, c].astype(float) - R1.loc[C, c].astype(float))
    print(f'  {c}: cambio medio {d.mean():+.4f}, máx |cambio| {d.abs().max():.4f}')
top1, top2 = R1.sort_values('ranking').index[:100], R2.sort_values('ranking').index[:100]
print('top 100 que siguen en el top 100:', len(set(top1) & set(top2)))
print('continuos que dejaron de serlo:', int((R1.loc[C, 'continuo_periodo'] & ~R2.loc[C, 'continuo_periodo']).sum()))

print('\n=== Resumen (filas nuevas) ===')
Rs = H['Resumen']
print(Rs[Rs['concepto'].str.contains('Sucursales activas|sin precios|solo estuvieron|caracteres|simbólico|Período', na=False)].to_string(index=False))

print('\n=== Hoja Dias ===')
Dd = H['Dias']
Dd['fecha'] = pd.to_datetime(Dd['fecha'])
print('filas:', len(Dd), '| columnas:', list(Dd.columns))
print('5 días con menos sucursales:'); print(Dd.nsmallest(5, 'sucursales').to_string(index=False))
m = Dd.groupby(Dd['fecha'].dt.strftime('%Y-%m')).agg(sucursales=('sucursales', 'median'), comercios=('comercios', 'median'),
                                                     productos=('productos', 'median'))
print('mediana por mes (2026):'); print(m[m.index >= '2026-01'].T.to_string())
print('comercios por día del 25/09 al 05/10/2026:', Dd[Dd['fecha'].between('2026-09-25', '2026-10-05')].set_index('fecha')['comercios'].to_dict())

print('\n=== Cadenas y comercios que dejaron de publicar ===')
Cd = H['Cadenas']
sin = Cd[~Cd['publica_en_el_ultimo_mes'].astype(bool)]
print(f'{len(sin)} comercios sin precios en el último mes; por año de su último mes:',
      sin['ultimo_mes'].str[:4].value_counts().sort_index().to_dict())
ult = dict(zip(Cd['comercio'], Cd['ultimo_mes']))
publica = dict(zip(Cd['comercio'], Cd['publica_en_el_ultimo_mes'].astype(bool)))
cad = R2['cadenas'].map(lambda x: x.split('; '))
esperado = cad.map(lambda l: not any(publica[c] for c in l))
F = R2['solo_en_comercios_que_dejaron_de_publicar']
print('marca = "ninguna de sus cadenas publica en el último mes":', bool((esperado == F).all()), '| marcados', int(F.sum()))
baja = cad.map(lambda l: max(ult[c] for c in l))[F]               # mes en que dejó de publicar la última de sus cadenas
print('marcados por mes en que dejó de publicar su última cadena (año):', baja.str[:4].value_counts().sort_index().to_dict())
print('  de 2026:', baja[baja >= '2026-01'].value_counts().sort_index().to_dict())
X = R2[F]
print('  último día después del mes de baja de sus cadenas:', int((X['ultimo_dia'].dt.strftime('%Y-%m') > baja).sum()))
print('  EAN', int(X['es_ean'].sum()), '| en el maestro', int(X['en_maestro'].sum()), '| puntaje máx', round(X['puntaje'].max(), 1),
      '| puntaje >= 20:', int((X['puntaje'] >= 20).sum()))
print('  cadenas más frecuentes de los marcados:', pd.Series([c for l in cad[F] for c in l]).value_counts().head(10).to_dict())
for mes in ('2026-07', '2026-09'):
    s = X[baja == mes].sort_values('ranking').head(5)
    print(f'  mejores con baja en {mes}:'); print(s[['ranking', 'descripcion', 'cadenas', 'ultimo_dia', 'sucursales_distintas']].to_string())

print('\n=== Precio simbólico ===')
S = R2[R2['precio_simbolico']]
print(len(S), '| por cadena principal:', S['cadena_principal'].value_counts().to_dict())
print('  EAN:', int(S['es_ean'].sum()), '| precio:', S['precio_mediano_ultimo_mes'].value_counts().sort_index().to_dict())
print(S.sort_values('sucursales_ultimo_mes', ascending=False)[['descripcion', 'precio_mediano_ultimo_mes', 'sucursales_ultimo_mes',
                                                                'cadena_principal']].head(12).to_string())
print('  precio entre $10 y $50 con >= 30 sucursales (quedan afuera de la marca):')
T = R2[(R2['precio_mediano_ultimo_mes'] > 10) & (R2['precio_mediano_ultimo_mes'] <= 50) & (R2['sucursales_ultimo_mes'] >= 30)]
print(T[['descripcion', 'precio_mediano_ultimo_mes', 'sucursales_ultimo_mes', 'cadena_principal']].head(12).to_string())
