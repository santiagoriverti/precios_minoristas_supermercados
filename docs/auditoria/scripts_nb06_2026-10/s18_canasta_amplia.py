# Canasta AMPLIA de la oferta actual para el nb06b (panel de expertos, 2026-10-27): las mismas reglas que la canasta
# fija (s9 + s10) sobre la ventana de los últimos 15 meses (ago-2025 -> oct-2026) en lugar de 2022-2026, y con los tipos
# que la canasta fija no puede tener por falta de continuidad: pan envasado, harinas, premezclas, alfajores y tapas.
# Mide el NIVEL de la brecha y su distribución entre regiones, cadenas y mercados con más productos y sucursales; la
# EVOLUCIÓN 2022-2026 sigue siendo la de la canasta fija.
#   1. Lado: sin TACC por la etiqueta o la marca celíaca; con TACC sin ingredientes naturalmente sin gluten (como s9).
#   2. Continuidad en la ventana: precio todos los meses (caché de la lectura amplia, ago-2025 -> sep-2026, y el nb09
#      en oct-2026) y a lo sumo una caída (< 35% de la mediana de la ventana).
#   3. Cobertura en la ventana (caché, sucursales del universo del nb06): sucursales por mes, provincias, comercios súper,
#      cadenas grandes y % de la cadena principal (REGLAS).
#   4. Subtipos comparables (SUBTIPOS); fuera lo que no tiene equivalente.
#   5. Identidad con precios: estabilidad contra su tipo y lado, sin saltos persistentes de más de x2,5 (con los precios
#      de una empresa fuera de escala afuera, como la CELDA 7 del nb06). Gramos: los que publican las cadenas el 22/10
#      (consenso del catálogo: >= 2 cadenas a ±5%; resuelve las presentaciones por unidades, tapas x12 o alfajores x6, y
#      los Maestros desactualizados, como el pan con semillas Smams de 200 g que el Maestro da de 500). Si alguna cadena
#      coincide con el Maestro y el consenso no, es ambiguo y queda afuera; sin consenso, el Maestro si coincide con el
#      SEPA del 22/10. Si el producto cambió de tamaño dentro de la ventana, los meses anteriores quedan con el $/100 g
#      del tamaño actual (el caché no guarda la descripción de cada mes).
#   6. Con TACC de primera línea: 0,6 a 1,67 veces la mediana con TACC de su subtipo.
#   7. Composición espejada: equivalentes antes que sustitutos, la misma marca primero (a lo sumo tantos como sin TACC
#      tenga la marca), tantos con TACC como sin TACC.
#   8. Líneas: misma marca y presentación al mismo precio (±10%) entran una vez.
# Uso: python -I -X utf8 s18_canasta_amplia.py <continuidad.parquet> <caché brecha_v3_xxx de la lectura amplia>
#                                              <pares_20261022.parquet de s3> <sim_suc_geo.parquet> <salida.csv>
#                                              <cat_20261022.parquet de s1>
import re, sys, unicodedata
from pathlib import Path
import numpy as np
import pandas as pd

F_CONT, D_CACHE, F_PAR, F_GEO, F_OUT, F_CAT = (Path(a) for a in sys.argv[1:7])
pd.set_option('display.width', 300); pd.set_option('display.max_colwidth', 60); pd.set_option('display.max_rows', 600)
VENTANA_DESDE = '2025-08'
MAX_CAIDAS = 1
# En la ventana: sucursales por mes (mediana), provincias, comercios súper, cadenas grandes y % de la cadena principal.
# Sin TACC con hasta 85% en una cadena (80% en la canasta fija): los panes sin TACC de Bio y Campero, los de más
# sucursales (~1.240 por mes), tienen 81-82% en DIA; con 80% el pan sin TACC sería de una sola marca (Schar)
REGLAS = {
    'sin_tacc': dict(suc=50, prov=10, com=3, grandes=2, principal=85),
    'tacc':     dict(suc=200, prov=18, com=6, grandes=4, principal=60),
}
GRANDES = {'DIA', 'Carrefour', 'Cencosud (Vea, Disco, Jumbo)', 'La Anónima', 'Cooperativa Obrera', 'Coto', 'ChangoMas',
           'Toledo'}
FILTRAR = {'19', '2013', '3001', '4', '23', '24'}
BANDA_TIER = (0.6, 1 / 0.6)
LINEA_PRECIO = (0.9, 1 / 0.9)
FACTOR_EMPRESA = 2.5   # como la CELDA 7 del nb06: la mediana de una empresa contra la mediana entre empresas (>= 3)
TIPOS_AMPLIA = {   # tipo del nb06 -> tipos de la tabla de continuidad (s7)
    'Fideos secos': ['Fideos secos'],
    'Galletitas dulces': ['Galletitas dulces'],
    'Galletitas saladas y crackers': ['Galletitas saladas y tostadas'],
    'Pan rallado y rebozador': ['Pan rallado y rebozador'],
    'Cereales rellenos (almohaditas)': ['Cereales y barras'],
    'Pan envasado': ['Pan envasado'],
    'Harinas y premezclas': ['Harinas y premezclas universales', 'Premezclas'],
    'Alfajores': ['Alfajores'],
    'Tapas': ['Tapas'],
}
# Correcciones verificadas de s10 (las cadenas coinciden): gramos de las cajas Wakas y descripción del spaghetti sin TACC
# Matarazzo, que el Maestro llama "Mostachol 5 Cereales"
GRAMOS_FIJOS = {'7798031470024': 250, '7798031470031': 250, '7798031470048': 250, '7798031470086': 250,
                '7798031470093': 250, '7798031470796': 300, '7798031470826': 300, '7798031470802': 300,
                '7798031470819': 300, '7798031470833': 300}
DESC_FIJA = {'7790070336002': 'Fideos Spaghetti sin TACC Matarazzo 500 Gr',
             '7798031470796': 'Fideos Fusilli con Maíz sin TACC Caja Wakas 300 Gr',
             '7798031470826': 'Fideos Fusilli con Quinoa sin TACC Caja Wakas 300 Gr',
             '7798031470802': 'Fideos Fusilli con Amaranto sin TACC Caja Wakas 300 Gr',
             '7798031470819': 'Fideos Fusilli con Chía sin TACC Caja Wakas 300 Gr',
             '7798031470833': 'Fideos Fusilli con Kale sin TACC Caja Wakas 300 Gr'}

def norm(s):
    return unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode('ascii').lower()

RE_G = re.compile(r'(\d+(?:[.,]\d+)?)\s*(kg|kgs|kilo|gr|grs|grm|g|gramos)\b', re.IGNORECASE)
RE_UN_G = re.compile(r'\b(\d+)\s*un\b\D{0,12}?(\d+(?:[.,]\d+)?)\s*(?:gr|grs|grm|g)\b', re.IGNORECASE)

def g_txt(s):
    m = RE_G.search(str(s))
    if not m:
        return np.nan
    v = float(m.group(1).replace(',', '.'))
    return v * 1000 if m.group(2).lower().startswith('k') else v

SUBTIPOS = {   # (nombre, regex) en orden; None = fuera de la canasta (no comparable). Los cinco primeros, como s9
    'Fideos secos': [
        (None, r'al huevo|blue patna|integral|vegetal|espinaca|morron|legumbre|alubia|garbanz|lentej|arveja|poroto|'
               r'proteina|\brina\b|nido|cabello|mono|bucat|foratt|guiser|3 minutos|instant|preparad|sabor|queso|fileto|'
               r'\bmix\b|soja|risoni'),
        ('Spaghetti', r'spag|spagu|largos'),
        ('Tallarín / cintas', r'tallar|fettu|fetuc|cinta|linguin'),
        ('Tirabuzón / fusilli', r'tirabu|fusil|tornill|caracol|spiral'),
        ('Mostachol / penne', r'mostach|penne|rigat|pluma'),
        ('Cortos (codito, dedalito, munición...)', r'codit|dedal|municion|ave maria|letrit'),
    ],
    'Galletitas dulces': [
        (None, r'banad|bañad|cubiert|alfajor|tapita|hojald|hojalmar|integral|avena|salvado|granola|cereal|fibra|organic|'
               r'sin azuc|light|dietet|surtid|variedad|kit kat|rhodesia|bon o bon|chocopause|graffiti|habanit|\btita\b|'
               r'brownie|merengu|tripack|3 un|5 un|biscuit|tostad|vainillas\b|okebon|molino natural'),
        ('Obleas', r'oblea|wafer'),
        ('Rellenas', r'rellen'),
        ('Pepas', r'pepa'),
        ('Con chips', r'chip'),
        ('Bizcochos', r'bizcoch|agridulce'),
        ('Secas (vainilla, limón, chocolate)', r'.'),
    ],
    'Galletitas saladas y crackers': [
        (None, r'salvado|integral|avena|fibra|bizcochit|grasa|tostad|palito|grisin|sandwich|3 en 1|pack|\bdulce'),
        ('Saborizadas / snack', r'snack|queso|jamon|pizza|oliva|calabresa|kesitas|\brex\b|saladix|chalita'),
        ('Crackers', r'cracker|criollit|marinera|\bagua\b|crackines|arroz'),
    ],
    'Pan rallado y rebozador': [
        (None, r'queso|coco|semilla'),
        ('Rebozador', r'rebozad|apanad'),
        ('Pan rallado', r'rallad'),
    ],
    'Cereales rellenos (almohaditas)': [
        ('Almohaditas rellenas', r'almohadit'),
        (None, r'.'),
    ],
    'Pan envasado': [
        (None, r'rallad|tostad|grisin|budin|dulce|pionono|chips|palito|crouton|miga|integral|salvado|avena|centeno|'
               r'arabe|pita|tortilla|rapidita|fajita|figaz|pizza|chipa|brioche|negro|lino|sin sal'),
        ('Pan para hamburguesas y panchos', r'hamburg|pancho|pebete|viena|super pancho'),
        ('Pan de molde y de mesa', r'molde|lactal|rodaja|rebanad|blanco|tradicional|clasico|multigran|semilla|mesa|campo|'
                                   r'criollo|frances|\bpan\b'),
    ],
    'Harinas y premezclas': [
        (None, r'almidon|fecula|maicena|goma|xantica|quinoa|garbanz|almendra|algarrob|arveja|\bmani\b|coco|avena|'
               r'sarraceno|lino|chia|integral|leudante|levadura|pan casero|polenta|semola|rallad|reboz|salvado|soja|'
               r'budin|flan|postre|gelatina|mousse|helado'),
        ('Premezcla para bizcochuelo y tortas', r'bizcochuel|torta|muffin|magdalena'),
        ('Premezcla para brownie', r'brownie'),
        ('Premezcla para pizza y ñoquis', r'pizza|noqui|pan de queso'),
        ('Harina o premezcla universal', r'harina|premezcla|\bmix\b|panaderia'),
    ],
    'Alfajores': [   # el alfajor suelto no se compara con la caja o el paquete (el $/100 g baja con el envase)
        (None, r'mini|minis|bocadito|alfajorcito|torta|cubanito|barrita|chocolate en barra|sin azuc|light|diet'),
        ('Alfajores en caja o paquete', r'\b(?:[2-9]|[1-9]\d)\s*un\b|\bcaja\b|\bpaquete\b|\bpack\b|\bx\s*\d'),
        ('Alfajor individual', r'alfajor'),
    ],
    'Tapas': [
        (None, r'hojaldr|canelon|lasagn|panqueq|rotiser|copetin|cocktail|integral|light'),
        ('Tapas para empanadas', r'empanad'),
        ('Tapas para tartas', r'tarta|pascualin'),
    ],
}
# sustitutos (otro producto, naturalmente sin gluten): entran solo si el subtipo no tiene un equivalente
SUSTITUTO = {
    'Galletitas saladas y crackers': r'\bgalletas? de arroz\b|\bgalletitas? (?:de )?arroz\b|\btostad\w* de arroz\b',
    'Harinas': r'harina de arroz|\barroz\b',
    'Premezclas': r'harina de arroz|\barroz\b',
    'Alfajores': r'\barroz\b',
}

def subtipo(tipo, d):
    for nombre, rx in SUBTIPOS[tipo]:
        if re.search(rx, d):
            if nombre == 'Alfajor individual' and g_txt(d) > 100:   # Tofi 276 g, Cachafaz 360 g: son cajas
                return 'Alfajores en caja o paquete'
            return nombre if nombre else '(fuera)'
    return '(fuera)'

# ── Candidatos: tabla de continuidad (s7) con el lado como en s9 ─────────────────────────────────────────────────────
c = pd.read_parquet(F_CONT)
c['id'] = c['id'].astype(str)
c['descripcion'] = c['id'].map(DESC_FIJA).fillna(c['descripcion'])
c['marca_n'] = c['marca'].map(lambda s: re.sub(r'[^A-Z0-9 ]', '', norm(s).upper()).strip())
_b = c.groupby('marca_n')['sin_tacc'].agg(['mean', 'size'])
MARCAS_CELIACAS = set(_b[(_b['mean'] >= 0.5) & (_b['size'] >= 2)].index) - {''}
c['es_gf'] = c['sin_tacc'] | (c['marca_n'].isin(MARCAS_CELIACAS) & ~c['con_gluten_explicito'])
c['ref_trigo'] = ~c['es_gf'] & ~c['ingrediente_sin_gluten']
inv = {s: t for t, ss in TIPOS_AMPLIA.items() for s in ss}
c = c[c['tipo'].isin(inv)].copy()
c['tipo_nb06'] = c['tipo'].map(inv)
c['lado'] = np.where(c['es_gf'], 'sin_tacc', np.where(c['ref_trigo'], 'tacc', 'excluido'))
c['d'] = (c['descripcion'].fillna('') + ' ' + c['desc_sepa_22oct'].fillna('')).map(norm)
# el Maestro dice "Matarazzo" para el tirabuzón Lucchetti y "Luchetti" para otros (MARCA_FIJA de s10)
c.loc[c['descripcion'].map(norm).str.contains(r'\bl?ucc?hetti\b'), 'marca_n'] = 'LUCCHETTI'
c['subtipo'] = [subtipo(t, d) for t, d in zip(c['tipo_nb06'], c['d'])]   # Maestro + lo que publican las cadenas
# Harinas y premezclas son dos tipos con su peso ENGHo: la harina de trigo (o la premezcla universal que la reemplaza)
# pesa 0,593% del gasto y las premezclas de bizcochuelo, brownie o pizza 0,133%. Juntas, la harina común (un cuarto del
# precio de las premezclas) caía en el filtro de plausibilidad del tipo (CELDA 7) y pesaba un tercio del tipo
_hp = c['tipo_nb06'] == 'Harinas y premezclas'
c.loc[_hp, 'tipo_nb06'] = np.where(c.loc[_hp, 'subtipo'].isin(['Harina o premezcla universal', '(fuera)']), 'Harinas',
                                   'Premezclas')
SER = pd.read_parquet(F_CONT.with_name(F_CONT.stem + '_serie.parquet'))
SER.index = SER.index.astype(str)
MES_FIN = max(SER.columns)

# ── Precios y cobertura en la ventana: caché de la lectura amplia (sucursal × EAN × mes), universo del nb06 ──────────
geo = pd.read_parquet(F_GEO)
geo = geo[~geo['id_comercio'].astype(str).isin(FILTRAR)]
P = pd.concat([pd.read_parquet(f) for f in sorted(D_CACHE.glob('????-??.parquet'))], ignore_index=True)
P = P[P['mes'] >= VENTANA_DESDE].merge(geo[['id_comercio', 'id_bandera', 'id_sucursal', 'PROVINCIA_NORM', 'empresa',
                                            'suc_key']], on=['id_comercio', 'id_bandera', 'id_sucursal'])
MESES = sorted(P['mes'].unique())
print(f'Ventana: {MESES[0]} -> {MESES[-1]} en el caché ({len(MESES)} meses) + {MES_FIN} del nb09 | {P["ean_norm"].nunique()} EANs')
cob = P.groupby(['ean_norm', 'mes'])['suc_key'].nunique().unstack('mes').reindex(columns=MESES)
COB = pd.DataFrame({'meses_ventana': cob.notna().sum(axis=1), 'suc_mes_mediana': cob.median(axis=1)})
COB['caidas'] = (cob.lt(0.35 * COB['suc_mes_mediana'], axis=0)).sum(axis=1)
_g = P.groupby('ean_norm')
COB['provincias'] = _g['PROVINCIA_NORM'].nunique()
COB['comercios_super'] = _g['id_comercio'].nunique()
COB['cadenas_grandes'] = _g['empresa'].agg(lambda s: len(set(s) & GRANDES))
_ep = P.groupby(['ean_norm', 'empresa']).size()
COB['pct_cadena_principal'] = 100 * _ep.groupby(level='ean_norm').max() / _ep.groupby(level='ean_norm').sum()
c = c.join(COB, on='id', how='inner', rsuffix='_v')
c['en_mes_fin'] = c['id'].map(SER[MES_FIN]).fillna(0) > 0

def motivo(r):
    if r['lado'] == 'excluido':
        return 'naturalmente sin gluten sin etiqueta (no sirve de referencia con TACC)'
    if r['subtipo'] == '(fuera)':
        return 'subtipo no comparable'
    g = REGLAS[r['lado']]
    m = []
    if r['meses_ventana'] < len(MESES): m.append(f"meses {int(r['meses_ventana'])}/{len(MESES)}")
    if not r['en_mes_fin']: m.append(f'sin precio en {MES_FIN}')
    if r['caidas_v'] > MAX_CAIDAS: m.append(f"{int(r['caidas_v'])} caídas")
    if r['suc_mes_mediana_v'] < g['suc']: m.append(f"suc {r['suc_mes_mediana_v']:.0f}")
    if r['provincias_v'] < g['prov']: m.append(f"prov {int(r['provincias_v'])}")
    if r['comercios_super_v'] < g['com']: m.append(f"comercios {int(r['comercios_super_v'])}")
    if r['cadenas_grandes_v'] < g['grandes']: m.append(f"grandes {int(r['cadenas_grandes_v'])}")
    if r['pct_cadena_principal_v'] > g['principal']: m.append(f"principal {r['pct_cadena_principal_v']:.0f}%")
    return '; '.join(m)

for k in ('suc_mes_mediana', 'provincias', 'comercios_super', 'cadenas_grandes', 'pct_cadena_principal', 'caidas'):
    if k + '_v' not in c.columns:
        c[k + '_v'] = c[k]
c['motivo'] = c.apply(motivo, axis=1)
c['pasa'] = c['motivo'].eq('')
c.drop(columns=['d']).to_parquet(F_OUT.with_suffix('.reglas.parquet'), index=False)
print('\nPasan las reglas 1-4 (tipo / subtipo / lado):')
print(c[c['pasa']].groupby(['tipo_nb06', 'subtipo', 'lado']).size().unstack('lado').fillna(0).astype(int).to_string())

# ── Gramos (regla 5): el Maestro contra el consenso del catálogo de las cadenas del 22/10 ────────────────────────────
def g_cadena(q, u, d):
    # gramos que publica una cadena: cantidad y unidad de la presentación; si es por unidades, los de la descripción
    u = norm(u).strip().rstrip('.')
    try:
        q = float(str(q).replace(',', '.'))
    except ValueError:
        q = np.nan
    if u in ('kg', 'kgs', 'kilo', 'kilos', 'kilogramo') and q > 0:
        return q * 1000
    if u in ('gr', 'grs', 'grm', 'g', 'gramos', 'gramo') and q > 0:
        return q * 1000 if q < 5 else q          # Coto: ".33 gr." = 0,33 kg
    d = norm(d)
    m = re.search(r'\b(\d+)\s*x\s*(\d+(?:[.,]\d+)?)\s*(?:grs?|grm|g)\b', d)   # "caja 6 x 50 grs"
    if m:
        return float(m.group(1)) * float(m.group(2).replace(',', '.'))
    ms = list(RE_G.finditer(d))
    if ms:
        v = float(ms[-1].group(1).replace(',', '.'))
        return v * 1000 if ms[-1].group(2).lower().startswith('k') else v
    return np.nan

cat = pd.read_parquet(F_CAT, columns=['id_comercio', 'id_producto', 'productos_descripcion',
                                      'productos_cantidad_presentacion', 'productos_unidad_medida_presentacion'])
cat['id'] = cat['id_producto'].astype(str).str.lstrip('0')
cat = cat[cat['id'].isin(set(c.loc[c['pasa'], 'id']))].drop_duplicates(
    ['id', 'id_comercio', 'productos_descripcion', 'productos_cantidad_presentacion', 'productos_unidad_medida_presentacion'])
cat['g'] = [g_cadena(q, u, d) for q, u, d in zip(cat['productos_cantidad_presentacion'],
                                                  cat['productos_unidad_medida_presentacion'], cat['productos_descripcion'])]
_gc = cat.dropna(subset=['g']).groupby(['id', 'id_comercio'])['g'].median().reset_index()
_gm = _gc.groupby('id')['g'].median()
_gc['ok'] = (_gc['g'] / _gc['id'].map(_gm) - 1).abs() <= 0.05
GCAT = pd.DataFrame({'g_cadenas': _gm, 'cadenas_con_gramos': _gc.groupby('id').size(),
                     'cadenas_de_acuerdo': _gc.groupby('id')['ok'].sum(), 'valores_cadenas': _gc.groupby('id')['g'].agg(list)})
GCAT['g_consenso'] = GCAT['g_cadenas'].where((GCAT['cadenas_de_acuerdo'] >= 2) |
                                             ((GCAT['cadenas_con_gramos'] == 1) & (GCAT['cadenas_de_acuerdo'] == 1)))

par = pd.read_parquet(F_PAR)
par['id'] = par['id_producto'].astype(str).str.lstrip('0')
par = par.drop_duplicates('id').set_index('id')
cand = c[c['pasa']].copy()
cand['g_maestro'] = [g_txt(p) if g_txt(p) == g_txt(p) else g_txt(d) for p, d in zip(cand['presentacion'], cand['descripcion'])]
# "3 Un 50 Gr": puede ser cada unidad (3 x 50) o el total; vale la que coincide con las cadenas
cand['g_maestro_pack'] = [float(m.group(1)) * float(m.group(2).replace(',', '.')) if m else np.nan
                          for m in (RE_UN_G.search(str(d)) for d in cand['descripcion'])]
cand = cand.join(GCAT, on='id')
cand['g_sepa'] = cand['id'].map(par['gramos'])

def gramos(r):
    if r['id'] in GRAMOS_FIJOS:
        return GRAMOS_FIJOS[r['id']], 'corrección verificada (s10)'
    gc, gm = r['g_consenso'], [x for x in (r['g_maestro'], r['g_maestro_pack']) if x == x and x > 0]
    if gc == gc and gc > 0:
        if any(abs(x / gc - 1) <= 0.05 for x in gm):
            return gc, 'Maestro = cadenas'
        if any(abs(v / x - 1) <= 0.05 for v in r['valores_cadenas'] for x in gm):
            return np.nan, f"ambiguo: cadenas {gc:g} g, el Maestro y alguna cadena {gm[0]:g} g"
        return gc, (f"cadenas (el Maestro dice {gm[0]:g} g)" if gm else 'cadenas (el Maestro no tiene gramos)')
    if gm:
        gs = r['g_sepa']
        if gs == gs and gs > 0 and abs(gm[0] / gs - 1) > 0.05:
            return np.nan, f'conflicto: Maestro {gm[0]:g} g, SEPA {gs:g} g'
        return gm[0], 'Maestro (sin consenso de las cadenas)'
    return np.nan, 'sin gramos'

_gr = [gramos(r) for _, r in cand.iterrows()]
cand['gramos'] = [g for g, _ in _gr]
cand['fuente_gramos'] = [f for _, f in _gr]
cand['ok_gramos'] = cand['gramos'].gt(0)
# alfajores: suelto o caja por los gramos verificados (el Maestro llama "6 Un 228 Gr" al Terrabusi glaseado de 38 g)
_alf = (cand['tipo_nb06'] == 'Alfajores') & cand['ok_gramos']
cand.loc[_alf, 'subtipo'] = np.where(cand.loc[_alf, 'gramos'] > 90, 'Alfajores en caja o paquete', 'Alfajor individual')

# Precios de una empresa fuera de escala (como la CELDA 7 del nb06): fuera antes de medir la identidad
_pe = P[P['ean_norm'].isin(set(cand['id']))].groupby(['ean_norm', 'mes', 'empresa'])['precio'].median().rename('pe').reset_index()
_pe['_ne'] = _pe.groupby(['ean_norm', 'mes'])['empresa'].transform('size')
_pe['_rel'] = _pe['pe'] / _pe.groupby(['ean_norm', 'mes'])['pe'].transform('median')
AT = _pe[(_pe['_ne'] >= 3) & ((_pe['_rel'] > FACTOR_EMPRESA) | (_pe['_rel'] < 1 / FACTOR_EMPRESA))]
PP = P[P['ean_norm'].isin(set(cand['id']))].merge(AT[['ean_norm', 'mes', 'empresa']].assign(_at=1),
                                                    on=['ean_norm', 'mes', 'empresa'], how='left')
print(f'\nPrecios de una empresa fuera de escala (x{FACTOR_EMPRESA}): {len(AT)} empresa-código-mes, '
      f'{int(PP["_at"].notna().sum()):,} obs fuera')
PP = PP[PP['_at'].isna()]
N = PP.groupby(['ean_norm', 'mes']).agg(p=('precio', 'median'), n=('suc_key', 'nunique')).reset_index()
N = N[N['n'] >= 10].merge(cand[['id', 'tipo_nb06', 'subtipo', 'lado', 'gramos']].rename(columns={'id': 'ean_norm'}),
                          on='ean_norm')
N = N[N['gramos'] > 0]
N['p100'] = N['p'] / N['gramos'] * 100
N['ref'] = N.groupby(['tipo_nb06', 'lado', 'mes'])['p100'].transform('median')
N['real'] = N['p100'] / N['ref']
_mt = N[N['lado'] == 'tacc'].groupby(['tipo_nb06', 'subtipo', 'mes'])['p100'].median().rename('_mt')
N = N.join(_mt, on=['tipo_nb06', 'subtipo', 'mes'])
N['rel_tier'] = N['p100'] / N['_mt']

def saltos(real):
    L = np.log(real)
    n = 0
    for i in range(1, len(L)):
        a, b = L[max(0, i - 3):i], L[i:i + 3]
        if len(a) and len(b) and abs(np.median(b) - np.median(a)) > np.log(2.5):
            n += 1
    return n

Q = (N.sort_values('mes').groupby('ean_norm')
     .apply(lambda g: pd.Series({'meses_precio': len(g), 'p100_ultimo': g['p100'].iloc[-1], 'mes_ultimo': g['mes'].iloc[-1],
                                 'estab': float(np.median(g['real'].iloc[-3:]) / np.median(g['real'].iloc[:3])),
                                 'saltos': saltos(g['real'].to_numpy()), 'rel_tier': float(g['rel_tier'].median())}),
            include_groups=False)
     .reset_index().rename(columns={'ean_norm': 'id'}))
cand = cand.merge(Q, on='id', how='left')
cand['ok_estab'] = cand['estab'].between(0.4, 2.5) & (cand['saltos'] == 0)
cand['ok_tier'] = np.where(cand['lado'] == 'tacc', cand['rel_tier'].between(*BANDA_TIER), True)
cand['ok_todo'] = cand[['ok_gramos', 'ok_estab', 'ok_tier']].all(axis=1) & cand['meses_precio'].ge(len(MESES) - 1)
print('\nGramos de las cadenas distintos de los del Maestro, o ambiguos:')
print(cand.loc[cand['fuente_gramos'].str.startswith(('cadenas (el Maestro dice', 'ambiguo')),
               ['tipo_nb06', 'lado', 'descripcion', 'gramos', 'fuente_gramos']].round(2).to_string(index=False))
print('\nVerificación con precios (afuera):')
print(cand.loc[~cand['ok_todo'], ['tipo_nb06', 'subtipo', 'lado', 'descripcion', 'gramos', 'fuente_gramos', 'estab',
                                  'saltos', 'rel_tier', 'meses_precio']].round(2).to_string(index=False))

# ── Composición espejada (regla 7) y líneas (regla 8), como s10 ──────────────────────────────────────────────────────
ok = cand[cand['ok_todo']].copy()
ok['item'] = ok['id']
ok['sustituto'] = [bool(re.search(SUSTITUTO[t], d)) if t in SUSTITUTO and l == 'sin_tacc' else False
                   for t, l, d in zip(ok['tipo_nb06'], ok['lado'], ok['d'])]
fin, sust_fuera, subtipos_ok = [], set(), set()
for (t, st), g in ok.groupby(['tipo_nb06', 'subtipo']):
    s_ = g[g['lado'] == 'sin_tacc'].sort_values('suc_mes_mediana_v', ascending=False)
    if s_['sustituto'].any() and (~s_['sustituto']).any():
        sust_fuera |= set(s_.loc[s_['sustituto'], 'item'])
        s_ = s_[~s_['sustituto']]
    # la misma marca primero, a lo sumo tantos como sin TACC tenga la marca; después por cobertura
    c_ = g[g['lado'] == 'tacc'].sort_values('suc_mes_mediana_v', ascending=False)
    c_ = (c_.assign(_mm=c_.groupby('marca_n').cumcount() < c_['marca_n'].map(s_['marca_n'].value_counts()).fillna(0))
          .sort_values(['_mm', 'suc_mes_mediana_v'], ascending=False, kind='stable').drop(columns='_mm'))
    if s_.empty or c_.empty:
        print(f'  subtipo sin los dos lados (afuera): {t} / {st} (sin TACC {len(s_)}, con TACC {len(c_)})')
        continue
    subtipos_ok.add((t, st))
    fin += [s_, c_.head(len(s_))]
F = pd.concat(fin, ignore_index=True)
I = N.rename(columns={'ean_norm': 'item'})[['item', 'mes', 'p100']]

def asignar_lineas(D):
    D = D.copy()
    D['_lin'] = list(zip(D['subtipo'], D['lado'], D['marca_n'], D['gramos'].round(0)))
    li = I.merge(D.loc[D.groupby('_lin')['item'].transform('size') >= 2, ['item', '_lin']], on='item')
    li = li[li.groupby(['_lin', 'mes'])['item'].transform('size') >= 2].copy()
    li['rel'] = li['p100'] / li.groupby(['_lin', 'mes'])['p100'].transform('median')
    fuera = set(li.groupby('item')['rel'].median().pipe(lambda s: s[~s.between(*LINEA_PRECIO)]).index)
    D['_lin'] = [k + (it,) if it in fuera else k for k, it in zip(D['_lin'], D['item'])]
    D['_n'] = D.groupby(['tipo_nb06', '_lin'])['item'].transform('size')
    D['linea'] = [f"{k[0]}{' sin TACC' if k[1] == 'sin_tacc' else ''} {str(m).title()} {g:g} g ({n} variantes)"
                  if n >= 2 else d for k, n, d, m, g in zip(D['_lin'], D['_n'], D['descripcion'], D['marca'], D['gramos'])]
    rep = D['linea'].map(D.drop_duplicates(['linea', '_lin']).groupby('linea').size()) > 1
    D.loc[rep & (D['_n'] < 2), 'linea'] = D['linea'] + ' (' + D['item'] + ')'
    return D

F = asignar_lineas(F)
F = F.sort_values(['tipo_nb06', 'subtipo', 'lado', 'linea', 'suc_mes_mediana_v'],
                  ascending=[True, True, True, True, False]).reset_index(drop=True)
print('\n=== Canasta amplia (productos y líneas) ===')
print(F.groupby(['tipo_nb06', 'subtipo', 'lado']).agg(productos=('item', 'size'), lineas=('linea', 'nunique'))
      .unstack('lado').to_string())
U = ok[[(t, st) in subtipos_ok for t, st in zip(ok['tipo_nb06'], ok['subtipo'])]].copy()
U = asignar_lineas(U)
U['en_canasta'] = U['item'].isin(set(F['item']))
U['motivo'] = np.select([U['en_canasta'], U['item'].isin(sust_fuera)],
                        ['', 'sustituto: el subtipo tiene un sin TACC equivalente'], 'composición espejada')

def filas(D, extra):
    return pd.DataFrame([{'tipo': r.tipo_nb06, 'lado': r.lado, 'ean': r.item, 'descripcion': r.descripcion,
                          'gramos': r.gramos, 'subtipo': r.subtipo, 'desde': '', 'hasta': '', **extra(r)}
                         for r in D.itertuples(index=False)])

OUT = filas(F, lambda r: {
    'marca': r.marca_n, 'nota': 'sustituto: el subtipo no tiene un sin TACC equivalente' if r.sustituto else '', 'producto': r.descripcion,
    'linea': r.linea, 'fuente_gramos': r.fuente_gramos, 'sucursales_mes_mediana_ventana': round(r.suc_mes_mediana_v, 1),
    'provincias': int(r.provincias_v), 'comercios': int(r.comercios_super_v), 'cadenas_grandes': int(r.cadenas_grandes_v),
    'pct_cadena_principal': round(r.pct_cadena_principal_v, 1), 'precio_100g_ultimo_mes': round(r.p100_ultimo, 1),
    'ultimo_mes_con_precio': r.mes_ultimo, 'precio_sobre_mediana_con_tacc_subtipo': round(r.rel_tier, 3)})
OUT.to_csv(F_OUT, index=False, encoding='utf-8')
SENS = filas(U, lambda r: {'marca': r.marca_n, 'nota': '', 'producto': r.descripcion, 'linea_todos': r.linea, 'en_canasta': r.en_canasta,
                           'motivo': r.motivo, 'sustituto': r.sustituto,
                           'sucursales_mes_mediana_ventana': round(r.suc_mes_mediana_v, 1),
                           'precio_sobre_mediana_con_tacc_subtipo': round(r.rel_tier, 3)})
SENS.to_csv(F_OUT.with_name('productos_sensibilidad_amplia.csv'), index=False, encoding='utf-8')
cand.drop(columns=['d']).to_parquet(F_OUT.with_suffix('.verif.parquet'), index=False)
print(f'\nGuardado: {F_OUT} ({len(OUT)} EANs, {F["linea"].nunique()} líneas) y productos_sensibilidad_amplia.csv '
      f'({int((~SENS["en_canasta"]).sum())} afuera de la canasta)')
print(f'Marcas celíacas: {len(MARCAS_CELIACAS)}')
