# Clasifica el catálogo de un día (s1_catalogo_dia.py) en tipos con dicotomía TACC / sin-TACC y resume la cobertura.
# Uso: python -I -X utf8 s2_clasificar_catalogo.py <cat.parquet> <Maestro de Productos Interno.xlsx> <salida.xlsx>
import re, sys
from pathlib import Path
import numpy as np
import pandas as pd

F_CAT, F_MAE, F_OUT = (Path(a) for a in sys.argv[1:4])
pd.set_option('display.width', 250); pd.set_option('display.max_colwidth', 60)

# ── Sin TACC por nombre (variantes vistas en el SEPA diario de oct-2026) ─────────────────────────────────────────────
RE_SIN = re.compile(
    r'(?:\bsin|\bs)[\s/.\-]*t\.?\s*a\.?\s*c\.?\s*c\b'                    # sin tacc, s/tacc, s tacc, s-tacc, stacc, s.t.a.c.c
    r'|\bsin[\s/.\-]*glut|\bs[\s/.\-]+glut'                               # sin gluten, s/gluten, s gluten
    r'|\blib(?:re|r)?\.?[\s/.\-]*(?:de|d)?[\s/.\-]*(?:bio\s+de\s+)?glut'  # libre de gluten, libre d/gluten, lib.d/gluten, libr d glut
    r'|\bl\.\s*glut|gluten[\s\-]*free|\bcel[ií]ac|\bglutal\b|\bapto\s+cel', re.IGNORECASE)
RE_CON = re.compile(r'\bc/\s*glut|\bcon\s+glut|galletit\w*\s+(?:de\s+)?gluten|\bgluten\s+(?:c/|s/)sal|light\s+gluten|'
                    r'gluten\s+light', re.IGNORECASE)   # "con gluten" explícito y galletitas DE gluten (no son celíacas)

# ── Tipos (en orden: gana el primero que matchea) ────────────────────────────────────────────────────────────────────
# Cada tipo: (incluir, excluir). Sobre la descripción en minúsculas, sin tildes.
TIPOS = [
    ('Premezclas y harinas', r'premez|harina|fecula|almidon|polvo de hornear', r'pescado|rebozad|rallad'),
    ('Pan rallado / rebozador', r'pan rallado|\brallad|rebozad|apanad|empaniz', r'queso|coco|zanahoria|rallador|limon'),
    ('Fideos secos', r'\bfid(?:eo|eos|\.)|spag|tallar|mostach|tirabu|\bpenne|fusil|codit|\bcintas?\b|caracol|rigat|'
                     r'\bletras?\b|mon(?:o|it)|farfall|dedali|cornet|risoni|\bnidos?\b|vermicel|cabello de angel|macarr|'
                     r'lasa[gn]|\bpasta (?:seca|corta|larga)|tornill|\bconchit|ave maria|\bdedal|ditalin|orzo|fetuc',
                     r'noqui|ravio|sorren|canelon|salsa|sopa|caldo|congel|fresc|rellen|\btapa|helado|pure|instant|'
                     r'vasito|\bcup\b|mani|chocolat|galleti|cereal'),
    ('Pastas frescas y ñoquis', r'noqui|ravio|sorren|canelon|capelet|agnolot|tortelin|panzott|\bmasa para pasta',
                                r'salsa|tapa|mani'),
    ('Pizza, tapas y masas', r'prepiz|\bpizz|\btapas?\b|pascualin|empanad|hojaldr|\bmasas?\b|tarta|pionono|\bwrap|'
                             r'tortill|pan arabe|rapidit|fugazz|discos? de', r'helado|salsa|queso rallado|rallad'),
    ('Alfajores', r'alfajor', r''),
    ('Budines, bizcochuelos y tortas', r'budin|bizcochuel|muffin|magdalen|madalen|brownie|\btorta\b|tortas\b|'
                                       r'pan dulce|panetton|\bcake|cupcake|vainillas?\b|plantilla|bay biscuit',
                                       r'galletit|helado|tortita|tortill'),
    ('Galletitas saladas, crackers y tostadas', r'cracker|tostad|tortit|grisin|\bsalad|criollit|bizcochit|\bagua\b|'
                                                r'chalita|talita|snack.*(?:queso|arroz)|(?:galleti|galleta|oblea).*'
                                                r'(?:queso|jamon|pizza|arroz|semilla|integral|salvado|s/sal|sin sal)|'
                                                r'(?:queso|arroz|semilla|salvado).*(?:galleti|galleta)|\bmarineras?\b|'
                                                r'\bsoda\b', r'dulce|chocolat|vainill|limon|coco|frutill|membrill|'
                                                r'mermelad|helado|pan rallado|pescad'),
    ('Galletitas dulces', r'galleti|galleta|oblea|bizcoch|\bscon|\bpepas?\b|wafer|waffle|cookie|marmolad|rellenit|'
                          r'cuadradit|masitas?|\bmerengu|\bbarquill|amaretti|biscotti',
                          r'helado|bizcochuel|pan rallado'),
    ('Pan envasado', r'\bpan\b|\bpanes\b|lactal|\bmolde\b|pebete|figaz|chipa|baguet|\bbollos?\b|fosforit|'
                     r'pancho|hamburg.*pan|pan.*hamburg|\bbudin de pan|\bmignon|felipe|criollo', r'rallad|rebozad|'
                     r'premez|dulce|budin|helado|pan de carne|congelad|hamburguesa de'),
    ('Cereales, copos y barras', r'cereal|\bcopos?\b|granola|avena|muesli|\bbarras?\b|barrit|aritos|anillit|almohadit|'
                                 r'trigo inflado|arroz inflado|corn ?flakes|zucaritas|choco krispis|quaker',
                                 r'galleti|chocolate en barra|barra de chocolate|helado|jabon|desodor'),
    ('Cerveza y maltas', r'cervez|cerve\b|\bbeer\b|\bmalta\b|\bipa\b|\blager\b', r'levadura'),
    ('Snacks', r'palito|chizit|\bsnack|papas? fritas|nacho|tostito|conit|chips|pochocl|\bmani\b|bastoncit',
               r'pescado|helado|chocolate'),
    ('Caldos, sopas y salsas', r'caldo|\bsopa|salsa|\bpure\b|saborizador|condiment', r''),
    ('Polenta y sémola', r'polenta|semola|\bsemolin', r''),
]
_TIPOS_C = [(t, re.compile(i), re.compile(e) if e else None) for t, i, e in TIPOS]

def sin_tildes(s):
    return (s.str.lower().str.normalize('NFKD').str.encode('ascii', 'ignore').str.decode('ascii'))

def tipo_de(d):
    for t, i, e in _TIPOS_C:
        if i.search(d) and not (e and e.search(d)):
            return t
    return None

# ── Gramos de la presentación ───────────────────────────────────────────────────────────────────────────────────────
RE_GR = re.compile(r'(\d+(?:[.,]\d+)?)\s*(?:-\s*)?(kgs?|kilos?|grs?|grm|gramos?|g|ml|cc|lts?|litros?|l)\b')
RE_GR2 = re.compile(r'\b(?:gr|grs|g)\s*(\d+(?:[.,]\d+)?)\b')      # 'gr120'
RE_MULT = re.compile(r'(\d+)\s*(?:x|u|un|uni|unid|unidades)\s*(\d+(?:[.,]\d+)?)\s*(?:grs?|grm|g)\b')

def gramos_desc(d):
    m = RE_MULT.search(d)
    if m:
        return float(m.group(1)) * float(m.group(2).replace(',', '.'))
    m = RE_GR.search(d)
    if m:
        v = float(m.group(1).replace(',', '.')); u = m.group(2)
        if u.startswith('k') or u in ('l', 'lt', 'lts', 'litro', 'litros'):
            return v * 1000
        return v
    m = RE_GR2.search(d)
    return float(m.group(1).replace(',', '.')) if m else np.nan

def gramos_pres(q, u):
    q = pd.to_numeric(q, errors='coerce'); u = str(u).strip().lower()
    if pd.isna(q) or q <= 0:
        return np.nan
    if u in ('kg', 'kgm', 'kilo', 'kilogramo', 'l', 'lt', 'lts', 'litro', 'litros'):
        return q * 1000
    if u in ('gr', 'g', 'grs', 'grm', 'gramo', 'gramos', 'ml', 'cc', 'mililitro', 'cm3'):
        return q
    return np.nan

# ── Datos ────────────────────────────────────────────────────────────────────────────────────────────────────────────
df = pd.read_parquet(F_CAT)
suc = pd.read_parquet(F_CAT.with_name(F_CAT.stem + '_sucursales.parquet'))
com = pd.read_parquet(F_CAT.with_name(F_CAT.stem + '_comercios.parquet'))
com = com[pd.to_numeric(com['id_comercio'], errors='coerce').notna()]
NOM = {(r.id_comercio, r.id_bandera): r.comercio_bandera_nombre for r in com.itertuples()}
for c in ['id_comercio', 'id_bandera', 'id_sucursal']:
    df[c] = df[c].astype(str).str.strip(); suc[c] = suc[c].astype(str).str.strip()
suc = suc.drop_duplicates(['id_comercio', 'id_bandera', 'id_sucursal'])
df = df.merge(suc[['id_comercio', 'id_bandera', 'id_sucursal', 'sucursales_provincia']], how='left',
              on=['id_comercio', 'id_bandera', 'id_sucursal'])
df['cadena'] = [NOM.get((a, b), f'Comercio {a}') for a, b in zip(df['id_comercio'], df['id_bandera'])]
df['suc_k'] = df['id_comercio'] + '-' + df['id_bandera'] + '-' + df['id_sucursal']
df['id_producto'] = df['id_producto'].astype(str).str.strip().str.lstrip('0')

# Descripciones distintas por producto (cada comercio describe a su modo): clasificación por la más frecuente
dd = (df.groupby(['id_producto', 'productos_descripcion']).size().rename('n').reset_index()
      .sort_values(['id_producto', 'n'], ascending=[True, False]))
dd['d'] = sin_tildes(dd['productos_descripcion'].fillna(''))
dd['sin'] = dd['d'].str.contains(RE_SIN) & ~dd['d'].str.contains(RE_CON)
dd['con_explicito'] = dd['d'].str.contains(RE_CON)
prod = dd.groupby('id_producto').agg(descripcion=('productos_descripcion', 'first'), d=('d', 'first'),
                                     sin_tacc=('sin', 'any'), con_explicito=('con_explicito', 'any'),
                                     n_desc=('d', 'size'))
prod['tipo'] = prod['d'].map(tipo_de)
# si la descripción principal no da tipo, probar con las otras
_sin_tipo = prod['tipo'].isna()
if _sin_tipo.any():
    _alt = dd[dd['id_producto'].isin(prod.index[_sin_tipo])].assign(t=lambda x: x['d'].map(tipo_de)).dropna(subset=['t'])
    prod.loc[_alt.groupby('id_producto')['t'].first().index, 'tipo'] = _alt.groupby('id_producto')['t'].first()

# Maestro interno: rubro / categoría / subcategoría
mae = pd.read_excel(F_MAE, dtype=str, engine='calamine',
                    usecols=['producto_sepa_id', 'producto_descripcion', 'producto_marca', 'rubro', 'categoria',
                             'subcategoria', 'producto_cantidad_presentacion', 'producto_unidad_medida_presentac'])
mae['id_producto'] = mae['producto_sepa_id'].astype(str).str.strip().str.lstrip('0')
mae = mae.drop_duplicates('id_producto').set_index('id_producto')
prod = prod.join(mae[['rubro', 'categoria', 'subcategoria', 'producto_descripcion']].rename(
    columns={'producto_descripcion': 'desc_maestro'}), how='left')
prod['en_maestro'] = prod['rubro'].notna()
# el maestro también dice "sin TACC" en su descripción
_dm = sin_tildes(prod['desc_maestro'].fillna(''))
prod['sin_tacc'] = prod['sin_tacc'] | (_dm.str.contains(RE_SIN) & ~_dm.str.contains(RE_CON))

# Marca, gramos y cobertura
first = lambda s: s.dropna().mode().iloc[0] if s.notna().any() else None
agg = df.groupby('id_producto').agg(
    marca=('productos_marca', first),
    cant=('productos_cantidad_presentacion', first), unidad=('productos_unidad_medida_presentacion', first),
    sucursales=('suc_k', 'nunique'), comercios=('id_comercio', 'nunique'), cadenas=('cadena', 'nunique'),
    provincias=('sucursales_provincia', 'nunique'), precio_mediano=('precio', 'median'),
    precio_p10=('precio', lambda s: s.quantile(.1)), precio_p90=('precio', lambda s: s.quantile(.9)))
prod = prod.join(agg)
_g1 = np.array([gramos_pres(q, u) for q, u in zip(prod['cant'], prod['unidad'])])
_g2 = np.array([gramos_desc(d) for d in prod['d']])
prod['gramos'] = np.where(np.isfinite(_g1), _g1, _g2)
prod['precio_100g'] = prod['precio_mediano'] / prod['gramos'] * 100
_cad = (df.groupby(['id_producto', 'cadena'])['suc_k'].nunique().reset_index()
        .sort_values(['id_producto', 'suc_k'], ascending=[True, False]))
prod['cadenas_detalle'] = _cad.groupby('id_producto').apply(
    lambda g: ', '.join(f'{c} {n}' for c, n in zip(g['cadena'], g['suc_k'])))
prod['lado'] = np.where(prod['sin_tacc'], 'sin TACC', 'con TACC')
prod = prod.reset_index()

TOT_SUC = df['suc_k'].nunique()
print(f'Sucursales del día: {TOT_SUC:,} | productos relevantes: {len(prod):,} | sin TACC: {prod["sin_tacc"].sum():,} '
      f'| sin tipo: {prod["tipo"].isna().sum():,}')

# ── Resumen por tipo ─────────────────────────────────────────────────────────────────────────────────────────────────
def resumen(g):
    s, c = g[g['sin_tacc']], g[~g['sin_tacc']]
    return pd.Series({
        'productos_con': len(c), 'productos_sin': len(s),
        'sin_con_100suc': int((s['sucursales'] >= 100).sum()), 'sin_con_300suc': int((s['sucursales'] >= 300).sum()),
        'sin_max_suc': int(s['sucursales'].max()) if len(s) else 0,
        'con_max_suc': int(c['sucursales'].max()) if len(c) else 0,
        'sin_cadenas_max': int(s['cadenas'].max()) if len(s) else 0,
        'marcas_sin': s['marca'].nunique(),
        'marcas_con_ambas': len(set(s['marca'].dropna().str.upper()) & set(c['marca'].dropna().str.upper())),
    })
res = prod.dropna(subset=['tipo']).groupby('tipo').apply(resumen).sort_values('sin_max_suc', ascending=False)
print('\n=== Resumen por tipo (22/10/2026) ===')
print(res.to_string())

cols = ['id_producto', 'descripcion', 'marca', 'gramos', 'sucursales', 'cadenas', 'provincias', 'precio_mediano',
        'precio_100g', 'en_maestro', 'cadenas_detalle']
for t in res.index:
    g = prod[prod['tipo'] == t]
    print(f'\n##### {t}')
    print('  -- sin TACC (top 15 por sucursales)')
    print(g[g['sin_tacc']].nlargest(15, 'sucursales')[cols].to_string(index=False, max_colwidth=48))
    print('  -- con TACC (top 8 por sucursales)')
    print(g[~g['sin_tacc']].nlargest(8, 'sucursales')[cols[:-1]].to_string(index=False, max_colwidth=48))

# sin TACC que no cayeron en ningún tipo
_st = prod[prod['sin_tacc'] & prod['tipo'].isna()].nlargest(40, 'sucursales')
print('\n=== sin TACC sin tipo (top 40) ===')
print(_st[['id_producto', 'descripcion', 'marca', 'sucursales', 'categoria']].to_string(index=False))

with pd.ExcelWriter(F_OUT, engine='openpyxl') as w:
    res.reset_index().to_excel(w, sheet_name='Resumen_tipos', index=False)
    prod.drop(columns=['d']).sort_values(['tipo', 'lado', 'sucursales'], ascending=[True, False, False]) \
        .to_excel(w, sheet_name='Productos', index=False)
prod.to_parquet(F_OUT.with_suffix('.parquet'), index=False)
print(f'\nGuardado: {F_OUT}')
