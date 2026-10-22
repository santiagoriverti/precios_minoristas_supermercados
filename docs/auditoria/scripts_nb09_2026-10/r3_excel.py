# Excel del nb09 v2: hojas de apoyo, Ranking contra el parquet, comercios repetidos, codigos y nb08.
# Uso: python -I -X utf8 r3_excel.py <carpeta datos> <carpeta data del repo> <carpeta proyectos>
import sys, time
from pathlib import Path
import numpy as np
import pandas as pd

D, DATA, PRY = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30); pd.set_option('display.max_colwidth', 70)
X = D / 'trazabilidad_productos_20220101_20261015.xlsx'
R = pd.read_parquet(D / 'trazabilidad_productos_20220101_20261015.parquet')

t = time.time()
H = pd.read_excel(X, sheet_name=None, engine='calamine', dtype={'id_producto': str})
print(f'Excel leido en {time.time() - t:.0f} s; hojas: {[(k, v.shape) for k, v in H.items()]}')

print('\n=== Resumen ===')
print(H['Resumen'].to_string(index=False))
print('\n=== Cadenas ===')
print(H['Cadenas'].to_string(index=False))
print('\n=== Provincias ===')
print(H['Provincias'].to_string(index=False))

print('\n=== Ranking del Excel vs parquet ===')
E = H['Ranking']
print('filas', len(E), 'vs', len(R), '| columnas iguales:', list(E.columns) == list(R.columns))
dif = []
for c in R.columns:
    a, b = E[c], R[c]
    if pd.api.types.is_numeric_dtype(b) and not pd.api.types.is_bool_dtype(b):
        a = pd.to_numeric(a, errors='coerce')
        bad = ~(np.isclose(a.to_numpy(float), b.to_numpy(float), rtol=1e-9, atol=1e-9, equal_nan=True))
    elif pd.api.types.is_bool_dtype(b):
        bad = a.astype(bool).to_numpy() != b.to_numpy()
    elif pd.api.types.is_datetime64_any_dtype(b):
        bad = ~((pd.to_datetime(a) == b) | (a.isna() & b.isna())).to_numpy()
    else:
        bad = ~((a.astype(str) == b.astype(str)) | (a.isna() & b.isna())).to_numpy()
    if bad.sum():
        dif.append((c, int(bad.sum())))
        print(f'  {c}: {int(bad.sum())} distintas, ej.:', list(zip(a[bad].head(3), b[bad].head(3))))
print('columnas con diferencias:', dif or 'ninguna')

print('\n=== Continuos_periodo y Por_categoria ===')
C = H['Continuos_periodo']
print('Continuos:', len(C), '| = continuo_periodo del parquet:', len(C) == int(R['continuo_periodo'].sum()),
      '| ordenado por suc_diarias_min desc:', bool((np.diff(C['suc_diarias_min'].to_numpy()) <= 0).all()))
print(C.head(10)[['ranking', 'descripcion', 'suc_diarias_min', 'suc_diarias_prom', 'comercios', 'puntaje']].to_string(index=False))
PC = H['Por_categoria']
print('Por_categoria:', len(PC), 'filas,', PC.groupby(['rubro', 'categoria']).ngroups, 'categorias; max por categoria',
      PC.groupby(['rubro', 'categoria']).size().max(), '| todos EAN:', bool(PC['es_ean'].astype(bool).all()))

print('\n=== Comercios que parecen repetidos (44/45/46, 49/50) ===')
cad = R['cadenas']
for grupo in [('Cadena 44', 'Cadena 45', 'Cadena 46'), ('Cadena 49', 'Cadena 50'), ('Cadena 2000', 'Cadena 2002', 'Cadena 2003')]:
    sets = {g: set(R.loc[cad.str.contains(g + '(;|$)', regex=True), 'id_producto']) for g in grupo}
    base = sets[grupo[0]]
    print('  ', {g: len(s) for g, s in sets.items()}, '| comunes con', grupo[0], ':',
          {g: len(s & base) for g, s in sets.items()})
ms = pd.read_excel(DATA / 'maestro_sucursales_completo.xlsx', dtype=str)
print('  columnas del maestro:', list(ms.columns))
for c in ['44', '45', '46', '49', '50', '25', '1', '7', '14', '18', '35', '36', '2013', '3000', '1002']:
    s = ms[ms['id_comercio'] == c]
    if len(s):
        nom = [x for x in ['comercio_razon_social', 'comercio_bandera_nombre', 'sucursales_nombre', 'banderaDescripcion']
               if x in s.columns]
        print(f'  comercio {c}: {len(s)} sucursales en el maestro | provincias {s["sucursales_provincia"].nunique()} | '
              + ' | '.join(f'{x}: {s[x].dropna().unique()[:3].tolist()}' for x in nom)
              + f' | localidades {s["sucursales_localidad"].dropna().unique()[:4].tolist()}')
    else:
        print(f'  comercio {c}: no esta en el maestro')

print('\n=== Codigos: digito verificador (control independiente) ===')
ids = R['id_producto'].astype(str)
L = ids.str.len(); dig = ids.str.isdigit()
def dv_ok(x):
    if not (x.isdigit() and 8 <= len(x) <= 14):
        return False
    z = x.zfill(14); d = [int(c) for c in z[:-1]][::-1]
    return (10 - sum(v * (3 if i % 2 == 0 else 1) for i, v in enumerate(d)) % 10) % 10 == int(z[-1])
dv = np.array([dv_ok(x) for x in ids])
restr = (((L == 8) | (L == 13)) & ids.str[0].eq('2')) | ((L == 12) & ids.str[0].isin(['2', '4']))
restr = restr.to_numpy()
e = R['es_ean'].to_numpy()
print('es_ean y DV invalido:', int((e & ~dv).sum()), '| es_ean y rango restringido:', int((e & restr).sum()))
print('no es_ean con DV valido:', int((~e & dv).sum()), '-> restringido', int((~e & dv & restr).sum()),
      '| el resto (marcados no EAN en el maestro):', int((~e & dv & ~restr).sum()))
print('  ejemplos del resto:', R.loc[~e & dv & ~restr, ['id_producto', 'descripcion', 'puntaje']].head(6).to_string(index=False))
print('no numericos por prefijo:', ids[~dig].str.extract(r'^(\d+-\d+)-')[0].value_counts().head(10).to_dict())

print('\n=== Precios simbolicos ($1 a $10) en EAN validos con >= 30 sucursales el ultimo mes ===')
s = R[R['es_ean'] & (R['precio_mediano_ultimo_mes'] <= 10) & (R['sucursales_ultimo_mes'] >= 30)]
print(len(s)); print(s[['ranking', 'id_producto', 'descripcion', 'precio_mediano_ultimo_mes', 'cv_precio_ultimo_mes_%', 'sucursales_ultimo_mes', 'cadena_principal']].head(12).to_string(index=False))

print('\n=== nb08 (Continua 2022): sucursales minimas por dia ===')
cc = pd.read_excel(PRY / 'canasta_continua_cantidad_07.xlsx', dtype={'id_producto': str})
cc['id'] = cc['id_producto'].str.lstrip('0')
Y = cc.set_index('id')[['descripcion', 'sucursales_min_dia', 'sucursales_mediana_2026']].join(
    R.set_index('id_producto')[['suc_diarias_min', 'suc_diarias_prom']])
Y['dif_min'] = Y['suc_diarias_min'] - Y['sucursales_min_dia']
print(Y.to_string())
