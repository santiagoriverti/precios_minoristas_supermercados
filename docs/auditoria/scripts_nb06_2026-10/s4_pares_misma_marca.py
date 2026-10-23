# Pares de la MISMA MARCA con TACC / sin TACC (mismo tipo, misma forma en fideos, tamaño parecido) y referencias con
# TACC a base de trigo, sobre la clasificación de s3_tipos_y_formas.py. Uso:
#   python -I -X utf8 s4_pares_misma_marca.py <salida .parquet de s3_tipos_y_formas.py> <salida de s1_catalogo_dia.py> <salida.xlsx>
import re, sys, unicodedata
from pathlib import Path
import numpy as np
import pandas as pd

F_P, F_CAT, F_OUT = (Path(a) for a in sys.argv[1:4])
pd.set_option('display.width', 250)
p = pd.read_parquet(F_P)
cat = pd.read_parquet(F_CAT, columns=['id_producto', 'productos_marca'])
cat['id_producto'] = cat['id_producto'].astype(str).str.strip().str.lstrip('0')

def norm(s):
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode('ascii').upper()
    return re.sub(r'[^A-Z0-9 ]', ' ', s).strip()
GENERICOS = {'SIN', 'GLUTEN', 'TACC', 'CLASSIC', 'CLASICO', 'CLASICA', 'EXTRA', 'LA', 'EL', 'LOS', 'LAS', 'DE', 'DEL',
             'S', 'SM', 'CRF', 'CARREF', 'NONE', 'NAN', 'GENERICO', 'SIN MARCA', 'VARIOS', 'X', 'Y', 'GALLETITAS',
             'GALLETITA', 'GALLETAS', 'GALLETA', 'FIDEOS', 'FIDEO', 'CEREAL', 'CEREALES', 'BARRA', 'BARRAS',
             'PREMEZCLA', 'HARINA', 'HARINAS', 'CERVEZA', 'PAN', 'RALLADO', 'TAPAS', 'TAPA', 'ALFAJOR', 'ALFAJORES',
             'BUDIN', 'SNACKS', 'SNACK', 'PIZZA', 'TOSTADAS', 'CRACKERS', 'PASTAS', 'PASTA', 'MASA', 'GRANOLA',
             'AVENA', 'COPOS', 'LIGHT', 'ULTRA', 'SABOR', 'NATURAL', 'FOOD', 'FOODS', 'ALIMENTOS', 'SELECCION',
             'PREMIUM', 'ORIGINAL', 'MARCA', 'PROPIA', 'SUPERMERCADOS', 'RELLENAS', 'INTEGRAL', 'DULCE', 'DULCES'}
# tokens de marca de cada producto: todas las variantes con que lo describen los comercios
_mv = cat.dropna().drop_duplicates()
_mv['tok'] = _mv['productos_marca'].map(lambda m: [t for t in norm(m).split() if t not in GENERICOS and len(t) >= 3]
                                        + ([norm(m).replace(' ', '')] if norm(m).replace(' ', '') not in GENERICOS else []))
TOK = _mv.groupby('id_producto')['tok'].apply(lambda s: set(t for l in s for t in l))
p['marca_tok'] = p['id_producto'].map(TOK).map(lambda x: x if isinstance(x, set) else set())
# la marca también aparece en la descripción (DIA abrevia la marca: 'EXQUI', 'LASAL'): se suman las palabras de la
# descripción para el cruce, pero solo cuentan si coinciden con un token de marca del otro lado
p['desc_tok'] = p['d'].map(lambda d: set(t for t in norm(d).split() if len(t) >= 4))

def misma_marca(a_m, a_d, b_m, b_d):
    for x in a_m:
        for y in b_m:
            if len(x) >= 4 and len(y) >= 4 and (x.startswith(y) or y.startswith(x)):
                return True
    return False

# ── Marcas celíacas (la mayoría de sus productos dice sin TACC): no sirven de referencia con TACC ─────────────────
_b = p.explode('marca_tok').dropna(subset=['marca_tok'])
_share = _b.groupby('marca_tok')['sin_tacc'].agg(['mean', 'size'])
MARCAS_CELIACAS = set(_share[(_share['mean'] >= 0.5) & (_share['size'] >= 2)].index)
SIN_ING = re.compile(r'arroz|maiz|quinoa|quinua|garbanz|lentej|legumbr|mandioc|\bchia\b|amarant|sarracen|\byuca\b|'
                     r'\bpapa\b|almendr|coco\b|\bmijo|sorgo|kale|arvej|poroto|soja|tapioca|fecula|almidon|'
                     r'\bchipa|pan de queso|\bketo\b|\bproteic')
p['es_celiaca_marca'] = p['marca_tok'].map(lambda s: bool(s) and s <= MARCAS_CELIACAS)
p['ref_trigo'] = (~p['sin_tacc']) & (~p['d'].str.contains(SIN_ING)) & (~p['es_celiaca_marca'])

q = p.dropna(subset=['tipo']).copy()
S = q[q['sin_tacc'] & (q['sucursales'] >= 50)]
C = q[q['ref_trigo'] & (q['sucursales'] >= 50) & ~q['d'].str.contains(r'\bdeo\b|desodor|caram|mastic|chicle')]

pares = []
for r in S.itertuples(index=False):
    cand = C[C['tipo'] == r.tipo]
    if r.tipo == 'Fideos secos':
        cand = cand[cand['forma'] == r.forma]
    cand = cand[[misma_marca(r.marca_tok, r.desc_tok, m, d) for m, d in zip(cand['marca_tok'], cand['desc_tok'])]]
    if pd.notna(r.gramos):
        cand = cand[cand['gramos'].isna() | (cand['gramos'] / r.gramos).between(0.5, 2.0)]
    if len(cand) == 0:
        continue
    b = cand.sort_values('sucursales', ascending=False).iloc[0]
    pares.append({'tipo': r.tipo, 'forma': r.forma,
                  'sin_id': r.id_producto, 'sin_desc': r.descripcion, 'sin_marca': r.marca, 'sin_g': r.gramos,
                  'sin_suc': r.sucursales, 'sin_cad': r.cadenas, 'sin_prov': r.provincias, 'sin_100g': r.precio_100g,
                  'sin_precio': r.precio_mediano, 'sin_cadenas_detalle': r.cadenas_detalle,
                  'con_id': b['id_producto'], 'con_desc': b['descripcion'], 'con_marca': b['marca'],
                  'con_g': b['gramos'], 'con_suc': b['sucursales'], 'con_cad': b['cadenas'],
                  'con_100g': b['precio_100g'], 'con_precio': b['precio_mediano']})
pares = pd.DataFrame(pares)
pares['brecha_100g_%'] = (pares['sin_100g'] / pares['con_100g'] - 1) * 100
pares['brecha_paquete_%'] = (pares['sin_precio'] / pares['con_precio'] - 1) * 100
pares['suc_min'] = pares[['sin_suc', 'con_suc']].min(axis=1)
pares = pares.sort_values(['tipo', 'suc_min'], ascending=[True, False])

print(f'Marcas celíacas detectadas ({len(MARCAS_CELIACAS)}): {sorted(MARCAS_CELIACAS)[:60]}')
print(f'\n=== Pares de la MISMA MARCA: {len(pares)} (sin TACC >= 50 sucursales; con TACC a base de trigo) ===')
for t, g in pares.groupby('tipo', sort=False):
    print(f'\n## {t}')
    print(g[['forma', 'sin_desc', 'sin_g', 'sin_suc', 'sin_cad', 'con_desc', 'con_g', 'con_suc', 'con_cad',
             'sin_100g', 'con_100g', 'brecha_100g_%']].head(10).round(0).to_string(index=False, max_colwidth=40))

# ── Referencias con TACC (trigo, marca no celíaca) más cubiertas, por tipo ─────────────────────────────────────────
print('\n=== Referencias con TACC (trigo) con más cobertura, por tipo (top 5) ===')
for t, g in C.groupby('tipo'):
    print(f'\n## {t}')
    print(g.nlargest(5, 'sucursales')[['descripcion', 'marca', 'gramos', 'sucursales', 'cadenas', 'provincias',
                                        'precio_100g']].round(0).to_string(index=False, max_colwidth=40))

# ── sin TACC "multicadena" (>= 300 sucursales y >= 5 cadenas), por tipo ────────────────────────────────────────────
multi = S[(S['sucursales'] >= 300) & (S['cadenas'] >= 5)].copy()
multi['con_par_misma_marca'] = multi['id_producto'].isin(set(pares['sin_id']))
print(f'\n=== sin TACC multicadena (>= 300 sucursales y >= 5 cadenas): {len(multi)} ===')
print(multi.groupby('tipo').agg(productos=('id_producto', 'size'), con_par=('con_par_misma_marca', 'sum'),
                                suc_max=('sucursales', 'max')).sort_values('productos', ascending=False).to_string())

out_cols = ['tipo', 'forma', 'lado', 'id_producto', 'descripcion', 'marca', 'gramos', 'sucursales', 'cadenas',
            'provincias', 'precio_mediano', 'precio_100g', 'ref_trigo', 'es_celiaca_marca', 'en_maestro', 'rubro',
            'categoria', 'subcategoria', 'cadenas_detalle']
with pd.ExcelWriter(F_OUT, engine='openpyxl') as w:
    pares.drop(columns=['suc_min']).to_excel(w, sheet_name='Pares_misma_marca', index=False)
    multi.sort_values(['tipo', 'sucursales'], ascending=[True, False])[out_cols + ['con_par_misma_marca']] \
        .to_excel(w, sheet_name='Sin_TACC_multicadena', index=False)
    C.sort_values(['tipo', 'sucursales'], ascending=[True, False]).groupby('tipo').head(30)[out_cols] \
        .to_excel(w, sheet_name='Referencias_con_TACC', index=False)
    q.sort_values(['tipo', 'lado', 'sucursales'], ascending=[True, False, False])[out_cols] \
        .to_excel(w, sheet_name='Todos_por_tipo', index=False)
pares.to_parquet(F_OUT.with_suffix('.pares.parquet'), index=False)
print(f'\nGuardado: {F_OUT}')
