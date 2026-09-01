"""Script to generate 07_evolucion_canastas_alternativas.ipynb.

Evolucion SEMANAL del costo de tres canastas socioeconomicas (Popular / Media /
Ejecutiva) en supermercados, comparada con el IPC del INDEC, desagregada por RUBRO
(Almacen, Bebidas, Lacteos, Limpieza, Perfumeria, Congelados... y los frescos nuevos:
Carne, Frutas, Verduras, Huevos) y por provincia y cadena.

Dos fuentes de composicion (hibrido):
- EMPAQUETADOS (por EAN): se leen de la hoja "Productos unicos" del Excel
  canasta_representativa_*.xlsx (columnas cantidad_01=Popular, cantidad_02=Media,
  cantidad_03=Ejecutiva). Cada producto trae su rubro/categoria del maestro.
- FRESCOS (por TIPO/nombre): carne, frutas, verduras y huevos NO tienen EAN estable
  entre cadenas (usan codigos de balanza que cada cadena inventa), asi que se
  seleccionan por REGLA DE NOMBRE sobre el maestro SEPA completo (motor de nb06). El
  precio de un tipo en una sucursal/semana = PROMEDIO de las variantes presentes,
  normalizado a la unidad del tipo ($/kg o $/docena). Asi son comparables entre
  cadenas y provincias.

Series por partida doble: MEDIANA (robusta) y PROMEDIO (outliers fuera), como nb02.
Granularidad SEMANAL (ISO week) ademas de mensual (para el vs-IPC, que es mensual).
El notebook imprime diagnosticos completos (cobertura por EAN/tipo, items poco
comparables, series) para refinar la composicion iterativamente.
"""
import json, os, hashlib

def _cell_id(prefix, src):
    return prefix + hashlib.md5(src.encode('utf-8')).hexdigest()[:6]

def cell_md(src):
    lines = src.split('\n')
    source = [l + '\n' for l in lines[:-1]] + ([lines[-1]] if lines[-1] else [])
    return {'cell_type':'markdown','id':_cell_id('md', src),'metadata':{},'source':source}

def cell_code(src):
    return {'cell_type':'code','execution_count':None,'id':_cell_id('c', src),'metadata':{},'outputs':[],'source':[src]}

cells = []

# ── TITLE ──────────────────────────────────────────────────────────────────────
cells.append(cell_md("""# SEPA — Evolución de Canastas Alternativas (Popular / Media / Ejecutiva)

Costo **semanal** de tres canastas socioeconómicas, comparado con el **IPC** del INDEC,
desagregado por **rubro** (incluida **Carne**, **Frutas**, **Verduras**, **Huevos**),
provincia y cadena.

**Composición (híbrida):**
- **Empaquetados** → hoja `Productos unicos` del Excel `canasta_representativa_*.xlsx`
  (`cantidad_01`=Popular, `cantidad_02`=Media, `cantidad_03`=Ejecutiva).
- **Frescos** → por **tipo/nombre** (carne, frutas, verduras, huevos), porque el EAN
  cambia por cadena. El precio del tipo = promedio de las variantes presentes en la
  sucursal, normalizado a $/kg o $/docena.

El notebook **imprime todos los diagnósticos** para refinar la composición."""))

# ── CELL 1 — CONFIG ────────────────────────────────────────────────────────────
cells.append(cell_code(r'''# ============================================================
# CELDA 1 — CONFIGURACIÓN (modificar solo esta sección)
# ============================================================
SEPA_SOURCE = 'mi_drive'   # 'mi_drive' | 'local'
SEPA_DIR    = '/content/drive/MyDrive/carga'
OUTPUT_DIR  = '/content/drive/MyDrive/carga/output_canasta'   # donde está canasta_representativa_*.xlsx
USE_CACHE   = True

# Hoja del Excel de donde se leen las canastas empaquetadas y el mapeo de columnas.
HOJA_CANASTAS = 'Productos unicos'
CANASTA_COLS  = {'cantidad_01': 'Popular', 'cantidad_02': 'Media', 'cantidad_03': 'Ejecutiva'}

# Serie histórica y ventana
MES_INICIO_HISTORICO = '2024-01'   # primer mes de la serie
MES_INICIO_GRAFICO   = '2024-01'   # base 100 de los gráficos
# Una sucursal cuenta para una canasta si tiene al menos esta fracción de los productos
# EMPAQUETADOS de esa canasta (los faltantes se imputan con la mediana nacional del EAN).
FRAC_PRODUCTOS_MIN = 0.5
# Mínimo de sucursales para reportar una desagregación (provincia/cadena) como confiable.
MIN_SUC_AGG = 30
# Estaciones de servicio / comercios no minoristas a excluir.
CADENAS_FILTRAR = {'19', '2013', '3001', '4'}

# ── FRESCOS por TIPO (selección por nombre; el EAN cambia por cadena) ──────────
# Cada tipo: rubro, unidad ('kg' o 'doc'), regex de inclusión y exclusión (sobre la
# descripción en minúsculas, con \b = borde de palabra para no colar 'camPERA' en 'pera'),
# y la cantidad por canasta (Popular, Media, Ejecutiva) en la unidad del tipo.
# 'qty' = (kg o docenas)/mes. Ajustá con la hoja Cobertura_frescos del primer run.
TIPOS_FRESCOS = {
    # ---- FRUTAS ($/kg) ----
    'Banana':      {'rubro':'Frutas','unidad':'kg','qty':(3,3,3),
                    'inc':r'\bbanana', 'exc':r'licuad|yogur|snack|deshidr|chip|pasas'},
    'Manzana':     {'rubro':'Frutas','unidad':'kg','qty':(2,2,3),
                    'inc':r'\bmanzana', 'exc':r'jugo|pur[eé]|vinagre|snack|licor|yogur|rall|deshidr|chip|desodor|t[eé] '},
    'Naranja':     {'rubro':'Frutas','unidad':'kg','qty':(3,3,3),
                    'inc':r'\bnaranja', 'exc':r'jugo|gaseosa|aceite|esen|yogur|fanta|desodor|aromatiz|jab[oó]n|amarg|licor'},
    'Mandarina':   {'rubro':'Frutas','unidad':'kg','qty':(1,2,2),
                    'inc':r'\bmandarina', 'exc':r'jugo|esen'},
    'Limón':       {'rubro':'Frutas','unidad':'kg','qty':(0.5,0.5,1),
                    'inc':r'\blim[oó]n|\blimones', 'exc':r'jugo|deterg|lavand|gaseosa|jab[oó]n|aceite|yogur|soda|amarg|aromatiz|desodor|hipoclor|limpiad|esen'},
    'Pera':        {'rubro':'Frutas','unidad':'kg','qty':(1,1,2),
                    'inc':r'\bpera\b|\bperas\b', 'exc':r'jugo|campera|frapera|heladera|esen'},
    # ---- VERDURAS ($/kg) ----
    'Papa':        {'rubro':'Verduras','unidad':'kg','qty':(4,4,4),
                    'inc':r'\bpapa\b|\bpapas\b', 'exc':r'frita|snack|pur[eé]|congel|chip|bast[oó]n|noisett|prefrit|rall|española'},
    'Tomate':      {'rubro':'Verduras','unidad':'kg','qty':(2,2,3),
                    'inc':r'\btomate', 'exc':r'salsa|pur[eé]|tritur|extracto|lata|pelado|jugo|ketchup|seco|deshidr|conserva|cubo'},
    'Cebolla':     {'rubro':'Verduras','unidad':'kg','qty':(2,2,2),
                    'inc':r'\bcebolla', 'exc':r'sopa|deshidr|crema|anillo|snack|verdeo en|caldo'},
    'Zanahoria':   {'rubro':'Verduras','unidad':'kg','qty':(1.5,1.5,1.5),
                    'inc':r'\bzanahoria', 'exc':r'rall|congel|sopa|deshidr|bab[yi]'},
    'Zapallo':     {'rubro':'Verduras','unidad':'kg','qty':(1.5,1.5,2),
                    'inc':r'\bzapallo|\bcalabaza', 'exc':r'congel|sopa|semilla|deshidr|crema'},
    'Lechuga':     {'rubro':'Verduras','unidad':'kg','qty':(1,1,1.5),
                    'inc':r'\blechuga', 'exc':r'aderez|snack'},
    'Morrón':      {'rubro':'Verduras','unidad':'kg','qty':(0.5,0.5,1),
                    'inc':r'\bmorr[oó]n|\bmorrones|\bpimiento', 'exc':r'molid|deshidr|conserva|lata|seco|pimentón|pimenton|aji molido'},
    'Batata':      {'rubro':'Verduras','unidad':'kg','qty':(1,1,1),
                    'inc':r'\bbatata', 'exc':r'dulce|congel|snack|chip'},
    # ---- CARNE ($/kg) ----
    'Asado':       {'rubro':'Carne','unidad':'kg','qty':(2,2,3),
                    'inc':r'\basado', 'exc':r'salsa|adob|snack'},
    'Carne picada':{'rubro':'Carne','unidad':'kg','qty':(2,2,2),
                    'inc':r'\bpicada\b|carne molida|\bmolida\b', 'exc':r'salch|congel|caldo|pat[eé]|hamburg'},
    'Nalga/Cuadril':{'rubro':'Carne','unidad':'kg','qty':(1,1.5,2),
                    'inc':r'\bnalga|\bcuadril|bola de lomo|\bcuadrada\b|\bpeceto|colita de cuadril', 'exc':r''},
    'Pollo':       {'rubro':'Carne','unidad':'kg','qty':(3,3,3),
                    'inc':r'\bpollo\b|pata muslo|\bpechuga|\bsuprema', 'exc':r'caldo|sopa|saboriz|congel|nugget|pat[eé]|medall|hamburg|milanesa|pella|arroz|fideo|snack|cubito|aliment'},
    'Milanesa carne':{'rubro':'Carne','unidad':'kg','qty':(1,1,1.5),
                    'inc':r'milanesa', 'exc':r'soja|pollo|congel|merluza|pescado|napolitan|vegetal|pescado'},
    # ---- HUEVOS ($/docena) ----
    'Huevos':      {'rubro':'Huevos','unidad':'doc','qty':(2,2,2),
                    'inc':r'\bhuevo', 'exc':r'chocolate|kinder|pascua|sorpresa|codorniz|conejo|batidora'},
}

# EANs de referencia para autodetectar el factor centavos/pesos (robusto con pocos EANs).
REF_EANS_FACTOR = {'7790072002080', '7790070320285', '7790132098459'}

# Colores/estilos por canasta (para gráficos)
CANASTA_COLORS = {'Popular':'#e74c3c','Media':'#27ae60','Ejecutiva':'#8e44ad'}
CANASTA_MARKERS = {'Popular':'s','Media':'^','Ejecutiva':'D'}
''' ))

# ── CELL 2 — DRIVE + DEPS + IMPORTS ────────────────────────────────────────────
cells.append(cell_code(r'''# ============================================================
# CELDA 2 — Montar Drive + dependencias + imports
# ============================================================
try:
    import google.colab
    if SEPA_SOURCE == 'mi_drive':
        from google.colab import drive
        drive.mount('/content/drive')
        print('Google Drive montado en /content/drive')
except ImportError:
    print('Entorno local detectado')

import subprocess, sys
subprocess.run([sys.executable, '-m', 'pip', 'install', 'openpyxl', 'tqdm', 'pyarrow', '-q'], check=False)

import zipfile, gzip, io, os, re, shutil, warnings, hashlib, gc
from pathlib import Path
from tqdm.auto import tqdm
warnings.filterwarnings('ignore')
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
plt.rcParams['figure.figsize'] = (13, 6); plt.rcParams['font.size'] = 11

SEPA_DIR   = Path(SEPA_DIR)
OUTPUT_DIR = Path(OUTPUT_DIR)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR  = OUTPUT_DIR / '_cache_nb07'
CACHE_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR    = Path('/content/tmp_sepa07'); TMP_DIR.mkdir(exist_ok=True)

def normalizar_ean(s):
    if s is None: return ''
    d = re.sub(r'\D', '', str(s))
    return (d.lstrip('0') or '0') if d else ''

REF_EANS_FACTOR = {normalizar_ean(e) for e in REF_EANS_FACTOR}

def _pmean(_s):
    # Promedio robusto: descarta outliers fuera de [mediana/4, mediana*4] y promedia.
    _s = pd.to_numeric(_s, errors='coerce').dropna()
    if len(_s) == 0: return float('nan')
    _m = _s.median()
    if _m and _m > 0:
        _f = _s[(_s >= _m/4) & (_s <= _m*4)]
        if len(_f) > 0: _s = _f
    return _s.mean()

def _to_gramos(_q, _u):
    # Presentación -> gramos/ml (para normalizar a $/kg). None si no aplica.
    _q = pd.to_numeric(str(_q).replace(',', '.'), errors='coerce'); _u = str(_u).strip().lower()
    if pd.isna(_q) or _q <= 0: return np.nan
    if _u in ('kg','kgm','l','lt','litro','litros','kilogramo','kilogramos'): return _q * 1000
    if _u in ('gr','g','grs','gramo','gramos','ml','cc','mililitro'): return _q
    return np.nan
_RE_GR = re.compile(r'(\d+(?:[.,]\d+)?)\s*(kg|kgm|kilo|grs?|gramos?|ml|cc|lts?|litros?|g)\b')
def _gramos_desc(_s):
    _m = _RE_GR.search(str(_s).lower())
    if not _m: return np.nan
    _v = float(_m.group(1).replace(',', '.')); _u = _m.group(2)
    if _u.startswith('k') or _u in ('lt','l','lts','litro','litros'): return _v * 1000
    return _v
_RE_UN = re.compile(r'(?:x\s*)?(\d+)\s*(?:un|u|unid|unidad|unidades|maple)\b')
def _unidades_desc(_s):
    # Cantidad de unidades (para huevos -> $/docena). 1 por defecto si no dice.
    _m = _RE_UN.search(str(_s).lower())
    if _m:
        _n = int(_m.group(1))
        if 1 <= _n <= 60: return _n
    return np.nan

print('Imports OK')
''' ))

# ── CELL 3 — CANASTAS EMPAQUETADAS DESDE EXCEL ─────────────────────────────────
cells.append(cell_code(r'''# ============================================================
# CELDA 3 — Canastas EMPAQUETADAS desde "Productos unicos" (cantidad_01/02/03)
# ============================================================
import glob as _glob
_patrones = sorted(_glob.glob(str(OUTPUT_DIR / 'canasta_representativa_*.xlsx')), reverse=True)
if not _patrones:
    raise FileNotFoundError(
        f'No se encontró canasta_representativa_*.xlsx en {OUTPUT_DIR}. '
        'Subí a Drive el Excel con la hoja "Productos unicos" poblada (cantidad_01/02/03).')
CANASTA_EXCEL = Path(_patrones[0])
print(f'Excel de canasta: {CANASTA_EXCEL.name}  (hoja: {HOJA_CANASTAS})')

_sel = pd.read_excel(CANASTA_EXCEL, sheet_name=HOJA_CANASTAS, dtype={'id_producto': str})
_sel['ean_norm'] = _sel['id_producto'].map(normalizar_ean)
_desc_col = next((c for c in ['descripcion','descripcion_producto','nombre'] if c in _sel.columns), _sel.columns[0])
_rubro_col = next((c for c in ['rubro','categoria'] if c in _sel.columns), None)
_cat_col   = next((c for c in ['categoria','subcategoria'] if c in _sel.columns), _rubro_col)

# CANASTAS_EMP[nombre] = { ean_norm: (desc, qty, rubro, categoria) }
CANASTAS_EMP = {}
for _col, _name in CANASTA_COLS.items():
    if _col not in _sel.columns:
        print(f'AVISO: columna {_col} ausente en la hoja — canasta {_name} vacía.')
        continue
    _q = pd.to_numeric(_sel[_col], errors='coerce').fillna(0)
    _act = _sel[_q > 0].copy(); _act['_q'] = _q[_q > 0].values
    CANASTAS_EMP[_name] = {
        r['ean_norm']: (str(r[_desc_col])[:60], float(r['_q']),
                        str(r[_rubro_col]).title() if _rubro_col else 'Otros',
                        str(r[_cat_col]) if _cat_col else '')
        for _, r in _act.iterrows() if r['ean_norm']}

CANASTAS_ACTIVAS = [n for n in CANASTA_COLS.values() if CANASTAS_EMP.get(n)]
if not CANASTAS_ACTIVAS:
    raise ValueError('Ninguna columna cantidad_01/02/03 tiene productos > 0 en la hoja.')

EANS_EMP = set().union(*[set(c.keys()) for c in CANASTAS_EMP.values()])
print(f'\nCanastas activas: {CANASTAS_ACTIVAS}')
for _name in CANASTAS_ACTIVAS:
    _c = CANASTAS_EMP[_name]
    _u = sum(v[1] for v in _c.values())
    _rub = pd.Series([v[2] for v in _c.values()]).value_counts().to_dict()
    print(f'  [{_name}] {len(_c)} productos empaquetados, {_u:.0f} unidades/mes | rubros: {_rub}')
print(f'EANs empaquetados (unión): {len(EANS_EMP)}')
''' ))

# ── CELL 4 — MAESTROS ──────────────────────────────────────────────────────────
cells.append(cell_code(r'''# ============================================================
# CELDA 4 — Maestros de sucursales, cadenas, provincias y productos
# ============================================================
DATA_URL = 'https://raw.githubusercontent.com/santiagoriverti/precios_minoristas_supermercados/main/data'
def leer_maestro(nombre, **kwargs):
    local = Path('data') / nombre
    if local.exists():
        return pd.read_excel(local, **kwargs)
    import urllib.request, urllib.parse
    dl = Path('/content/data') / nombre
    Path('/content/data').mkdir(exist_ok=True)
    if not dl.exists():
        print(f'  Descargando {nombre}...')
        urllib.request.urlretrieve(f'{DATA_URL}/{urllib.parse.quote(nombre)}', dl)
    return pd.read_excel(dl, **kwargs)

print('Cargando maestros...')
maestro_suc = leer_maestro('maestro_sucursales_completo.xlsx')
for c in ['id_comercio','id_bandera','id_sucursal']:
    maestro_suc[c] = maestro_suc[c].astype(str)
suc_pais = maestro_suc[
    maestro_suc['sucursales_latitud'].notna() & maestro_suc['sucursales_longitud'].notna() &
    (maestro_suc['sucursales_latitud'].between(-55, -22)) &
    (maestro_suc['sucursales_longitud'].between(-73, -53))].copy()
IDS_PAIS = set(zip(suc_pais['id_comercio'], suc_pais['id_bandera'], suc_pais['id_sucursal']))
print(f'  Sucursales válidas: {len(suc_pais):,}')

NOMBRES_COMPUESTOS = {
    ('9','1'):'Vea',('9','2'):'Disco',('9','3'):'Jumbo',
    ('10','1'):'Carrefour',('10','2'):'Carrefour Market',('10','3'):'Carrefour Express',
    ('11','2'):'ChangoMas',('11','4'):'Hiper ChangoMas',('11','5'):'Mi ChangoMas',
    ('16','1'):'Hipermercado Libertad',('16','2'):'Mini Libertad'}
NOMBRES_SIMPLES = {
    '2':'La Anonima','3':'Cadena 3','5':'Hipermercado Misiones','8':'Mariano Max',
    '12':'Coto','13':'Cooperativa Obrera','15':'DIA','20':'LAR','21':'Toledo','23':'Cadena 23','47':'Pasamonte'}
def asignar_cadena(row):
    k = (row['id_comercio'], row['id_bandera'])
    if k in NOMBRES_COMPUESTOS: return NOMBRES_COMPUESTOS[k]
    if row['id_comercio'] in NOMBRES_SIMPLES: return NOMBRES_SIMPLES[row['id_comercio']]
    return f"Cadena {row['id_comercio']}"

PROV_NORM = {
    'Ciudad Autonoma de Buenos Aires':'CABA','Ciudad Autónoma de Buenos Aires':'CABA',
    'Provincia de Buenos Aires':'Buenos Aires','Provincia de Catamarca':'Catamarca',
    'Provincia del Chaco':'Chaco','Provincia del Chubut':'Chubut',
    'Provincia de Cordoba':'Córdoba','Provincia de Córdoba':'Córdoba','Provincia de Corrientes':'Corrientes',
    'Provincia de Entre Rios':'Entre Ríos','Provincia de Entre Ríos':'Entre Ríos',
    'Provincia de Formosa':'Formosa','Provincia de Jujuy':'Jujuy','Provincia de La Pampa':'La Pampa',
    'Provincia de La Rioja':'La Rioja','Provincia de Mendoza':'Mendoza','Provincia de Misiones':'Misiones',
    'Provincia del Neuquen':'Neuquén','Provincia del Neuquén':'Neuquén','Neuquén':'Neuquén',
    'Provincia de Rio Negro':'Río Negro','Provincia de Río Negro':'Río Negro',
    'Provincia de Salta':'Salta','Provincia de San Juan':'San Juan','Provincia de San Luis':'San Luis',
    'Provincia de Santa Cruz':'Santa Cruz','Provincia de Santa Fe':'Santa Fe',
    'Provincia de Santiago del Estero':'Santiago del Estero',
    'Provincia de Tierra del Fuego, Antartida e Islas del Atlantico Sur':'Tierra del Fuego',
    'Provincia de Tierra del Fuego, Antártida e Islas del Atlántico Sur':'Tierra del Fuego',
    'Provincia de Tucuman':'Tucumán','Provincia de Tucumán':'Tucumán',
    'Buenos Aires':'Buenos Aires','CABA':'CABA'}
PESOS_POBLACION = {
    'Buenos Aires':17709732,'CABA':3075646,'Catamarca':415438,'Chaco':1204541,'Chubut':618994,
    'Córdoba':3978984,'Corrientes':1120801,'Entre Ríos':1385961,'Formosa':605193,'Jujuy':770881,
    'La Pampa':368550,'La Rioja':393531,'Mendoza':2014533,'Misiones':1261294,'Neuquén':664057,
    'Río Negro':747610,'Salta':1441998,'San Juan':781217,'San Luis':531745,'Santa Cruz':333473,
    'Santa Fe':3556522,'Santiago del Estero':1019304,'Tierra del Fuego':190641,'Tucumán':1737127}

# Maestro de productos (interno + SEPA completo del Drive) -> descripcion/rubro/grams/unidades
_mp_raw = leer_maestro('Maestro de Productos Interno.xlsx', dtype=str,
                       usecols=['producto_sepa_id','producto_descripcion','producto_marca','rubro',
                                'producto_cantidad_presentacion','producto_unidad_medida_presentac'])
_msepa = None
try:
    _msp = Path(SEPA_DIR) / 'maestro_sepa_completo.csv.gz'
    if _msp.exists():
        _msepa = pd.read_csv(_msp, dtype=str)
        print(f'  Maestro SEPA completo (Drive): {len(_msepa):,} EANs')
    else:
        print('  (aviso: maestro_sepa_completo.csv.gz no está en el Drive — solo maestro interno. '
              'Los frescos de nicho por cadena pueden quedar sub-representados.)')
except Exception as _e:
    print(f'  (aviso: no se pudo leer maestro_sepa_completo.csv.gz: {_e})')

def _prep_master(_df):
    _df = _df.rename(columns={'producto_descripcion':'descripcion','producto_marca':'marca'})
    if 'rubro' not in _df.columns: _df['rubro'] = ''
    _df['ean_norm'] = _df['producto_sepa_id'].map(normalizar_ean)
    return _df[['ean_norm','descripcion','marca','rubro',
                'producto_cantidad_presentacion','producto_unidad_medida_presentac']]
_base = _prep_master(_mp_raw)
if _msepa is not None:
    _extra = _prep_master(_msepa)
    _extra = _extra[~_extra['ean_norm'].isin(set(_base['ean_norm']))]
    MP_META = pd.concat([_base, _extra], ignore_index=True)
    print(f'  Fusión maestros: interno {len(_base):,} + {len(_extra):,} nuevos = {len(MP_META):,} EANs')
else:
    MP_META = _base
_g1 = [_to_gramos(a, b) for a, b in zip(MP_META['producto_cantidad_presentacion'],
                                        MP_META['producto_unidad_medida_presentac'])]
_g2 = [_gramos_desc(x) for x in MP_META['descripcion']]
MP_META['grams'] = [(_a if (_a == _a) else _b) for _a, _b in zip(_g1, _g2)]
MP_META['unidades'] = [_unidades_desc(x) for x in MP_META['descripcion']]
MP_META = (MP_META.dropna(subset=['ean_norm']).drop_duplicates('ean_norm')
           .set_index('ean_norm')[['descripcion','marca','rubro','grams','unidades']])
print(f'  Maestro de productos (total): {len(MP_META):,} EANs con metadata')
print('Maestros OK')
''' ))

# ── CELL 5 — RESOLVER FRESCOS POR NOMBRE ───────────────────────────────────────
cells.append(cell_code(r'''# ============================================================
# CELDA 5 — Resolver EANs de FRESCOS por regla de nombre (el EAN cambia por cadena)
# ============================================================
# Para cada tipo fresco, candidatos = EANs del maestro cuya descripción matchea inc y no exc.
# Se normaliza el precio a la unidad del tipo: kg (usa grams) o doc (usa unidades).
_desc_all = MP_META['descripcion'].fillna('').astype(str).str.lower()

EAN_TIPO = {}       # ean_norm -> tipo fresco
FRESCO_INFO = {}    # tipo -> {rubro, unidad, qty:(pop,med,eje)}
EAN_NORMFACTOR = {} # ean_norm -> gramos (kg) o unidades (doc) segun el tipo
_cob_fresco = []
for _tipo, _cfg in TIPOS_FRESCOS.items():
    _inc, _exc = _cfg['inc'], _cfg.get('exc', '')
    _m = _desc_all.str.contains(_inc, regex=True)
    if _exc: _m &= ~_desc_all.str.contains(_exc, regex=True)
    _cand = MP_META[_m].copy()
    # normalizador de unidad segun tipo
    if _cfg['unidad'] == 'kg':
        _cand = _cand[_cand['grams'].notna() & (_cand['grams'] > 0)]
        _fac = _cand['grams']            # $/g -> luego *1000 = $/kg
    else:  # doc
        _u = _cand['unidades'].fillna(1).clip(lower=1)
        _cand = _cand[_u > 0]; _fac = _u  # $/un -> luego *12 = $/docena
    FRESCO_INFO[_tipo] = {'rubro':_cfg['rubro'],'unidad':_cfg['unidad'],'qty':_cfg['qty']}
    for _e, _f in zip(_cand.index, _fac):
        if _e not in EAN_TIPO:  # primer tipo que lo reclama
            EAN_TIPO[_e] = _tipo; EAN_NORMFACTOR[_e] = float(_f)
    _cob_fresco.append({'tipo':_tipo,'rubro':_cfg['rubro'],'unidad':_cfg['unidad'],
                        'n_EANs_maestro':int(_m.sum()),'n_EANs_usables':len(_cand)})
cobertura_fresco_maestro = pd.DataFrame(_cob_fresco)
EANS_FRESCOS = set(EAN_TIPO.keys())

# Universo de EANs a leer del SEPA = empaquetados ∪ frescos ∪ referencia de factor
EANS_LECTURA = EANS_EMP | EANS_FRESCOS | REF_EANS_FACTOR
print(f'Tipos frescos: {len(FRESCO_INFO)} | EANs frescos candidatos (maestro): {len(EANS_FRESCOS):,}')
print(cobertura_fresco_maestro.to_string(index=False))
print(f'\nUniverso de EANs a leer del SEPA: {len(EANS_LECTURA):,} '
      f'(empaquetados {len(EANS_EMP)} + frescos {len(EANS_FRESCOS)})')
_sin_cand = [t for t in TIPOS_FRESCOS if cobertura_fresco_maestro.set_index("tipo").loc[t,"n_EANs_usables"] == 0]
if _sin_cand:
    print(f'⚠️ Tipos SIN candidatos en el maestro (revisá inc/exc o falta maestro SEPA completo): {_sin_cand}')
''' ))

# ── CELL 6 — ZIP FUNCTIONS + MAPA DE MESES ─────────────────────────────────────
cells.append(cell_code(r'''# ============================================================
# CELDA 6 — Funciones de lectura de ZIPs SEPA + mapa de meses
# ============================================================
import datetime as _dt
_PAT_SEM  = re.compile(r'^(\d{4})(A|B)$', re.IGNORECASE)
_PAT_ARC  = re.compile(r'^(\d{2})(\d{4})_pais_parte.*COMPLETO.*\.csv\.gz$', re.IGNORECASE)
PAT_FECHA = re.compile(r'^precio_(\d{8})$')

def detectar_semestres():
    out = []
    for z in sorted(SEPA_DIR.glob('*.zip')):
        m = _PAT_SEM.match(z.stem)
        if m: out.append((z, int(m.group(1)), m.group(2).upper()))
    return out
def archivos_por_mes(zip_path):
    meses = {}
    with zipfile.ZipFile(zip_path) as zf:
        for nombre in zf.namelist():
            m = _PAT_ARC.match(Path(nombre).name)
            if m:
                meses.setdefault((int(m.group(2)), int(m.group(1))), []).append(nombre)
    return meses

_mapa_mes = {}
for _zip_path, _anio, _sem in detectar_semestres():
    for (_a, _mm), _archs in archivos_por_mes(_zip_path).items():
        _lbl = f'{_a}-{_mm:02d}'
        if _lbl >= MES_INICIO_HISTORICO:
            _mapa_mes[_lbl] = (_zip_path, _archs)
_meses_disp = sorted(_mapa_mes)
if not _meses_disp:
    raise RuntimeError(f'No hay meses SEPA disponibles >= {MES_INICIO_HISTORICO}')
_mes_actual = _meses_disp[-1]

def _sem_de_fecha(_f):
    _iso = _f.isocalendar()
    return f'{_iso[0]}-W{_iso[1]:02d}'
def _mes_de_semana(_sem):
    _y, _w = _sem.split('-W')
    _thu = _dt.date.fromisocalendar(int(_y), int(_w), 4)  # jueves de la semana ISO
    return _thu.strftime('%Y-%m')
_NOM = {'01':'enero','02':'febrero','03':'marzo','04':'abril','05':'mayo','06':'junio',
        '07':'julio','08':'agosto','09':'septiembre','10':'octubre','11':'noviembre','12':'diciembre'}
NOMBRE_MES_TITLE = f"{_NOM[_mes_actual[5:7]]} {_mes_actual[:4]}".title()
print(f'Meses disponibles: {len(_meses_disp)}  ({_meses_disp[0]} → {_meses_disp[-1]}) | mes en curso: {_mes_actual}')
''' ))

# ── CELL 7 — LECTURA SEMANAL ───────────────────────────────────────────────────
cells.append(cell_code(r'''# ============================================================
# CELDA 7 — Lectura SEMANAL de precios (una fila por sucursal×EAN×semana ISO)
# ============================================================
# Colapsa los días a la MEDIANA semanal por (sucursal, EAN, semana). Cachea meses
# cerrados; el mes en curso se relee siempre fresco. Autodetecta centavos/pesos por mes.
_cache_key  = hashlib.md5('|'.join(sorted(EANS_LECTURA)).encode()).hexdigest()[:8]
_cache_path = CACHE_DIR / f'sem_{_cache_key}.parquet'

def _leer_mes(_lbl):
    _zip_path, _archs = _mapa_mes[_lbl]
    _rows = []; _muestra_ref = []
    for _archivo in sorted(_archs):
        _tmp_p = TMP_DIR / Path(_archivo).name
        with zipfile.ZipFile(_zip_path) as _zf:
            with _zf.open(_archivo) as _s, open(_tmp_p, 'wb') as _d:
                shutil.copyfileobj(_s, _d, length=4*1024*1024)
        with gzip.open(_tmp_p, 'rt', encoding='utf-8', errors='replace') as _g:
            for _chunk in pd.read_csv(_g, dtype=str, chunksize=300_000, low_memory=False):
                _chunk['ean_norm'] = _chunk['id_producto'].apply(normalizar_ean)
                _chunk = _chunk[_chunk['ean_norm'].isin(EANS_LECTURA)].copy()
                if len(_chunk) == 0: continue
                for _c in ['id_comercio','id_bandera','id_sucursal']:
                    _chunk[_c] = _chunk[_c].astype(str)
                _chunk['_k'] = list(zip(_chunk['id_comercio'],_chunk['id_bandera'],_chunk['id_sucursal']))
                _chunk = _chunk[_chunk['_k'].isin(IDS_PAIS)].drop(columns=['_k']).copy()
                if len(_chunk) == 0: continue
                _cols_p = [c for c in _chunk.columns if PAT_FECHA.match(c)]
                if not _cols_p: continue
                _mlt = _chunk.melt(id_vars=['id_comercio','id_bandera','id_sucursal','ean_norm'],
                                   value_vars=_cols_p, var_name='_col', value_name='precio_raw')
                _mlt['precio'] = pd.to_numeric(_mlt['precio_raw'].replace('NA', np.nan), errors='coerce')
                _mlt = _mlt[_mlt['precio'].notna() & (_mlt['precio'] > 0)].copy()
                _mlt['fecha'] = pd.to_datetime(_mlt['_col'].str[-8:], format='%Y%m%d', errors='coerce')
                _mlt = _mlt[_mlt['fecha'].notna()]
                _es_ref = _mlt['ean_norm'].isin(REF_EANS_FACTOR)
                if _es_ref.any(): _muestra_ref.extend(_mlt.loc[_es_ref, 'precio'].tolist())
                _mlt = _mlt[_mlt['ean_norm'].isin(EANS_EMP | EANS_FRESCOS)]
                if len(_mlt) == 0: continue
                _mlt['semana'] = _mlt['fecha'].dt.isocalendar().year.astype(str) + '-W' + \
                                 _mlt['fecha'].dt.isocalendar().week.map(lambda w: f'{w:02d}')
                _rows.append(_mlt.groupby(['id_comercio','id_bandera','id_sucursal','ean_norm','semana'],
                                          as_index=False)['precio'].median())
        _tmp_p.unlink(missing_ok=True)
    if not _rows: return None
    _df = pd.concat(_rows, ignore_index=True)
    _med_ref = pd.Series(_muestra_ref).median() if _muestra_ref else _df['precio'].median()
    if _med_ref > 10_000: _df['precio'] /= 100
    _df = _df.groupby(['id_comercio','id_bandera','id_sucursal','ean_norm','semana'],
                      as_index=False)['precio'].median()
    return _df

# Meses cerrados: caché incremental
if USE_CACHE and _cache_path.exists():
    _cache = pd.read_parquet(_cache_path)
    _cache['mes'] = _cache['semana'].map(_mes_de_semana)
    _cache = _cache[_cache['mes'] < _mes_actual].drop(columns='mes').copy()
else:
    _cache = pd.DataFrame(columns=['id_comercio','id_bandera','id_sucursal','ean_norm','semana','precio'])
_cache['_mes'] = _cache['semana'].map(_mes_de_semana) if len(_cache) else pd.Series(dtype=str)
_en_cache = set(_cache['_mes'].unique()) if len(_cache) else set()
_faltantes = [m for m in _meses_disp if m < _mes_actual and m not in _en_cache]
_nuevos = []
for _lbl in tqdm(_faltantes, desc='Meses cerrados'):
    _d = _leer_mes(_lbl)
    if _d is not None: _nuevos.append(_d)
if _nuevos:
    _cache = pd.concat([_cache.drop(columns='_mes', errors='ignore')] + _nuevos, ignore_index=True)
    if USE_CACHE:
        _cache.to_parquet(_cache_path, compression='snappy', index=False)
        print(f'Caché actualizado: {_cache_path.name}')
_cache = _cache.drop(columns='_mes', errors='ignore')

# Mes en curso: fresco
_actual = _leer_mes(_mes_actual)
datos_sem = pd.concat([_cache] + ([_actual] if _actual is not None else []), ignore_index=True)
if len(datos_sem) == 0:
    raise RuntimeError('Sin datos para los EANs configurados. Revisá las canastas y los frescos (CELDA 1).')
# Re-agregar semanas partidas entre meses/archivos
datos_sem = datos_sem.groupby(['id_comercio','id_bandera','id_sucursal','ean_norm','semana'],
                              as_index=False)['precio'].median()
datos_sem['mes'] = datos_sem['semana'].map(_mes_de_semana)
datos_sem = datos_sem[datos_sem['mes'] >= MES_INICIO_HISTORICO].copy()
_sems = sorted(datos_sem['semana'].unique())
ULTIMA_SEMANA = _sems[-1]
print(f'Observaciones (sucursal×EAN×semana): {len(datos_sem):,}')
print(f'Semanas: {_sems[0]} → {_sems[-1]} ({len(_sems)} semanas) | Sucursales: '
      f'{datos_sem.groupby(["id_comercio","id_bandera","id_sucursal"]).ngroups:,}')
print(f'EANs con datos: empaquetados {datos_sem[datos_sem["ean_norm"].isin(EANS_EMP)]["ean_norm"].nunique()}/{len(EANS_EMP)} · '
      f'frescos {datos_sem[datos_sem["ean_norm"].isin(EANS_FRESCOS)]["ean_norm"].nunique()}/{len(EANS_FRESCOS)}')
''' ))

# ── CELL 8 — COSTO POR SUCURSAL×SEMANA (empaquetados + frescos, por rubro) ──────
cells.append(cell_code(r'''# ============================================================
# CELDA 8 — Costo de canasta por sucursal×semana (empaquetados + frescos), por rubro
# ============================================================
# Metodología:
#  - EMPAQUETADO: precio de la sucursal-semana por EAN (mediana de días).
#  - FRESCO: precio del TIPO en la sucursal-semana = MEDIANA de las variantes presentes,
#    normalizado a $/kg (grams) o $/docena (unidades).
#  - Ítem faltante en una sucursal-semana → se imputa con la MEDIANA NACIONAL de esa
#    semana (para ese EAN o tipo). Costo de canasta = Σ (precio × cantidad), por rubro.
#  - Serie nacional = MEDIANA y PROMEDIO(sin outliers) del costo ENTRE sucursales.
_SK = ['id_comercio','id_bandera','id_sucursal']
_dd = datos_sem[~datos_sem['id_comercio'].isin(CADENAS_FILTRAR)].copy()

# ── Precio de ítem por sucursal-semana: empaquetados (item=ean) + frescos (item=tipo) ──
_emp = _dd[_dd['ean_norm'].isin(EANS_EMP)][_SK + ['semana','ean_norm','precio']].rename(columns={'ean_norm':'item'})
_emp['price'] = _emp['precio']
_fr = _dd[_dd['ean_norm'].isin(EANS_FRESCOS)].copy()
if len(_fr):
    _fr['tipo'] = _fr['ean_norm'].map(EAN_TIPO)
    _fac = _fr['ean_norm'].map(EAN_NORMFACTOR)
    _mult = _fr['tipo'].map(lambda t: 1000.0 if FRESCO_INFO[t]['unidad']=='kg' else 12.0)
    _fr['price'] = _fr['precio'] / _fac * _mult   # $/kg o $/docena
    _frsv = (_fr.groupby(_SK + ['semana','tipo'], as_index=False)['price'].median()
               .rename(columns={'tipo':'item'}))
else:
    _frsv = pd.DataFrame(columns=_SK + ['semana','item','price'])
sval = pd.concat([_emp[_SK + ['semana','item','price']], _frsv[_SK + ['semana','item','price']]], ignore_index=True)

# Mediana nacional por (item, semana) — referencia de imputación
nac_item = sval.groupby(['item','semana'])['price'].median().rename('nac').reset_index()

# ── Geografía de sucursales (cadena + provincia) ─────────────────────────────
_sg = suc_pais[_SK + ['sucursales_nombre','sucursales_latitud','sucursales_longitud',
                      'sucursales_localidad','PROVINCIA']].copy()
_sg['cadena'] = _sg.apply(asignar_cadena, axis=1)
_sg['provincia'] = _sg['PROVINCIA'].map(PROV_NORM).fillna(_sg['PROVINCIA'])
suc_geo = _sg.drop_duplicates(_SK)

def _recipe(_name):
    # DataFrame item->(qty,rubro) para una canasta (empaquetados + frescos)
    _rows = []
    for _ean,(_desc,_q,_rub,_cat) in CANASTAS_EMP[_name].items():
        _rows.append((_ean, float(_q), _rub, 'emp'))
    _pos = CANASTAS_ACTIVAS.index(_name)   # 0=Popular,1=Media,2=Ejecutiva (según orden activo)
    for _tipo,_info in FRESCO_INFO.items():
        _q = _info['qty'][_pos] if _pos < len(_info['qty']) else _info['qty'][-1]
        if _q and _q > 0:
            _rows.append((_tipo, float(_q), _info['rubro'], 'fresh'))
    return pd.DataFrame(_rows, columns=['item','qty','rubro','kind'])

def _costo_por_rubro(_name):
    _rec = _recipe(_name)
    _n_emp = int((_rec['kind']=='emp').sum())
    # valor nacional completo por (semana, rubro): Σ nac*qty sobre TODOS los ítems de la receta
    _av = nac_item.merge(_rec, on='item', how='inner')
    _av['val'] = _av['nac'] * _av['qty']
    _all = _av.groupby(['semana','rubro'], as_index=False)['val'].sum().rename(columns={'val':'val_all'})
    # presentes por sucursal-semana
    _pv = sval.merge(_rec, on='item', how='inner').merge(nac_item, on=['item','semana'], how='left')
    _pv['store_val'] = _pv['price'] * _pv['qty']
    _pv['nac_val']   = _pv['nac']   * _pv['qty']
    _g = (_pv.groupby(_SK + ['semana','rubro'])
            .agg(S_store=('store_val','sum'), S_nac=('nac_val','sum'),
                 n_emp=('kind', lambda s: (s=='emp').sum())).reset_index())
    _g = _g.merge(_all, on=['semana','rubro'], how='left')
    _g['costo'] = _g['S_store'] + (_g['val_all'].fillna(0) - _g['S_nac'])   # presentes reales + faltantes imputados
    _g['canasta'] = _name
    # cobertura de empaquetados por sucursal-semana (para filtrar)
    _cov = _g.groupby(_SK + ['semana'])['n_emp'].sum().reset_index(name='n_emp_tot')
    _cov['frac'] = _cov['n_emp_tot'] / max(_n_emp, 1)
    _ok = _cov[_cov['frac'] >= FRAC_PRODUCTOS_MIN][_SK + ['semana']]
    _g = _g.merge(_ok, on=_SK + ['semana'], how='inner')
    return _g

# Costo por (canasta, sucursal, semana, rubro) y total por (canasta, sucursal, semana)
costo_rubro = pd.concat([_costo_por_rubro(n) for n in CANASTAS_ACTIVAS], ignore_index=True)
costo_rubro['mes'] = costo_rubro['semana'].map(_mes_de_semana)
costo_rubro = costo_rubro.merge(suc_geo[_SK + ['cadena','provincia','sucursales_localidad']], on=_SK, how='left')
costo_suc = (costo_rubro.groupby(['canasta'] + _SK + ['semana','mes','cadena','provincia'], as_index=False)['costo'].sum())

# ── Serie nacional semanal por canasta (mediana y promedio entre sucursales) ──
serie_sem_dict = {}
for _name in CANASTAS_ACTIVAS:
    _cs = costo_suc[costo_suc['canasta']==_name]
    _s = (_cs.groupby('semana').agg(costo_mediana=('costo','median'), costo_prom=('costo', _pmean),
                                    n_sucursales=('id_sucursal','nunique')).reset_index().sort_values('semana'))
    _s['mes'] = _s['semana'].map(_mes_de_semana)
    _s['var_sem_%'] = _s['costo_mediana'].pct_change(fill_method=None) * 100
    serie_sem_dict[_name] = _s
    if len(_s):
        print(f'  [{_name}] {len(_s)} semanas | último costo mediano ${_s["costo_mediana"].iloc[-1]:,.0f} '
              f'({_s["var_sem_%"].iloc[-1]:+.1f}% sem) | n≈{int(_s["n_sucursales"].median())} sucursales')
''' ))

# ── CELL 9 — DESAGREGACIÓN POR RUBRO (con drill-down) ──────────────────────────
cells.append(cell_code(r'''# ============================================================
# CELDA 9 — Desagregación por RUBRO (Carne, Frutas, Verduras, Almacén, ...) + drill-down
# ============================================================
# Nivel 1: costo por rubro y semana (mediana entre sucursales).
# Nivel 2/3: detalle por ítem (producto/tipo) del último mes → composición fina.
rubro_sem_dict = {}    # canasta -> semana×rubro (costo mediano entre sucursales)
rubro_share_dict = {}  # canasta -> rubro (costo último mes + participación %)
detalle_dict = {}      # canasta -> ítem (rubro, detalle, cantidad, precio_unit, costo) último mes

_ult_mes = costo_rubro['mes'].max()
for _name in CANASTAS_ACTIVAS:
    _cr = costo_rubro[costo_rubro['canasta']==_name]
    # Nivel 1: costo por rubro × semana (mediana entre sucursales de ese rubro)
    _rs = (_cr.groupby(['semana','rubro'])['costo'].median().reset_index())
    _rs['mes'] = _rs['semana'].map(_mes_de_semana)
    rubro_sem_dict[_name] = _rs.sort_values(['semana','rubro'])
    # Participación por rubro (último mes)
    _rm = _rs[_rs['mes']==_ult_mes].groupby('rubro')['costo'].mean()
    _sh = _rm.reset_index().rename(columns={'costo':'costo_mensual'})
    _sh['participacion_%'] = (_sh['costo_mensual'] / _sh['costo_mensual'].sum() * 100).round(1)
    rubro_share_dict[_name] = _sh.sort_values('costo_mensual', ascending=False)
    # Nivel 3: detalle por ítem (precio nacional del último mes × cantidad)
    _rec = _recipe(_name)
    _sv_um = sval[sval['semana'].map(_mes_de_semana)==_ult_mes]
    _pu = _sv_um.groupby('item')['price'].median().rename('precio_unit').reset_index()
    _det = _rec.merge(_pu, on='item', how='left')
    _det['detalle'] = _det.apply(lambda r: (str(CANASTAS_EMP[_name][r['item']][0]) if r['kind']=='emp'
                                            else f"{r['item']} ($/{FRESCO_INFO[r['item']]['unidad']})"), axis=1)
    _det['costo'] = _det['precio_unit'] * _det['qty']
    detalle_dict[_name] = _det[['rubro','detalle','kind','qty','precio_unit','costo']].sort_values(['rubro','costo'], ascending=[True,False])

# Resumen por pantalla
for _name in CANASTAS_ACTIVAS:
    _sh = rubro_share_dict[_name]
    print(f'=== [{_name}] Composición por rubro (último mes {_ult_mes}) — total ${_sh["costo_mensual"].sum():,.0f} ===')
    print(_sh.to_string(index=False))
    _carne = _sh[_sh['rubro']=='Carne']
    if len(_carne):
        print(f'   → Carne: ${_carne["costo_mensual"].iloc[0]:,.0f} ({_carne["participacion_%"].iloc[0]:.1f}%)')
    print()
''' ))

# ── CELL 10 — IPC + SERIE MENSUAL + vs IPC ─────────────────────────────────────
cells.append(cell_code(r'''# ============================================================
# CELDA 10 — IPC INDEC + serie MENSUAL de canastas + comparación vs IPC
# ============================================================
IPC_PATH = SEPA_DIR / 'IPC.xlsx'
ipc = None
if IPC_PATH.exists():
    _ipc = pd.read_excel(IPC_PATH)
    _fcol = next((c for c in _ipc.columns if str(c).lower().strip() in ('date','fecha','mes','period')), _ipc.columns[0])
    if pd.api.types.is_datetime64_any_dtype(_ipc[_fcol]):
        _ipc['mes'] = _ipc[_fcol].dt.strftime('%Y-%m')
    else:
        _ME = {'ene':1,'feb':2,'mar':3,'abr':4,'may':5,'jun':6,'jul':7,'ago':8,'sep':9,'oct':10,'nov':11,'dic':12}
        def _pf(v):
            if pd.isna(v): return pd.NaT
            s=str(v).strip().lower(); p=s.split('-')
            if len(p)==2 and p[0][:3] in _ME:
                try: return pd.Timestamp(year=int(p[1]) if len(p[1])==4 else 2000+int(p[1]), month=_ME[p[0][:3]], day=1)
                except Exception: pass
            return pd.to_datetime(v, errors='coerce')
        _ipc['mes'] = _ipc[_fcol].apply(_pf).dt.strftime('%Y-%m')
    _rm = {}
    for c in _ipc.columns:
        cl = str(c).lower()
        if 'nivel general' in cl: _rm[c]='ipc_general'
        elif 'alimentos y bebidas no alc' in cl: _rm[c]='ipc_alimentos'
    _ipc = _ipc.rename(columns=_rm)
    for c in ['ipc_general','ipc_alimentos']:
        if c in _ipc.columns:
            _ipc[c]=pd.to_numeric(_ipc[c].astype(str).str.replace(',','.',regex=False), errors='coerce')
    _cols=['mes','ipc_general']+(['ipc_alimentos'] if 'ipc_alimentos' in _ipc.columns else [])
    ipc=_ipc[_cols].dropna(subset=['ipc_general']).sort_values('mes').reset_index(drop=True)
    if 'ipc_alimentos' not in ipc.columns: ipc['ipc_alimentos']=np.nan
    print(f'IPC: {len(ipc)} meses ({ipc["mes"].min()}→{ipc["mes"].max()})')
else:
    print(f'⚠️ IPC.xlsx no encontrado en {SEPA_DIR} — se omite la comparación vs IPC.')

# Serie MENSUAL de canastas: por sucursal, mediana de sus semanas del mes; luego entre sucursales.
serie_mes_dict = {}; comparativa_dict = {}
for _name in CANASTAS_ACTIVAS:
    _cs = costo_suc[costo_suc['canasta']==_name]
    _sm = (_cs.groupby(_SK + ['mes'])['costo'].median().reset_index()   # por sucursal-mes
             .groupby('mes').agg(canasta_mediana=('costo','median'), canasta_prom=('costo', _pmean),
                                 n_sucursales=('costo','size')).reset_index().sort_values('mes'))
    _sm['var_mensual_%'] = _sm['canasta_mediana'].pct_change(fill_method=None) * 100
    serie_mes_dict[_name] = _sm
    if ipc is not None and len(_sm):
        _c = _sm.merge(ipc, on='mes', how='left')
        _b  = _c['canasta_mediana'].iloc[0]
        _bi = _c['ipc_general'].dropna().iloc[0] if _c['ipc_general'].notna().any() else np.nan
        _ba = _c['ipc_alimentos'].dropna().iloc[0] if _c['ipc_alimentos'].notna().any() else np.nan
        _c['idx_canasta']   = (_c['canasta_mediana'] / _b * 100).round(1)
        _c['idx_ipc_gral']  = (_c['ipc_general'] / _bi * 100).round(1) if _bi==_bi else np.nan
        _c['idx_ipc_alim']  = (_c['ipc_alimentos'] / _ba * 100).round(1) if _ba==_ba else np.nan
        comparativa_dict[_name] = _c
        if len(_c) >= 2:
            _n0 = _c[_c['idx_ipc_gral'].notna()]
            if len(_n0)>=2:
                print(f'  [{_name}] {_c["mes"].iloc[0]}→{_c["mes"].iloc[-1]}: canasta {_c["idx_canasta"].iloc[-1]:.0f} '
                      f'vs IPC {_n0["idx_ipc_gral"].iloc[-1]:.0f} (base 100)')
    else:
        comparativa_dict[_name] = _sm.copy()
''' ))

# ── CELL 11 — GRÁFICOS ─────────────────────────────────────────────────────────
cells.append(cell_code(r'''# ============================================================
# CELDA 11 — Gráficos: índice semanal, vs IPC (mensual) y composición por rubro
# ============================================================
# Fig 1 — Índice semanal (base 100 en la primera semana)
fig, ax = plt.subplots(figsize=(13,6))
for _name in CANASTAS_ACTIVAS:
    _s = serie_sem_dict[_name]
    if len(_s) == 0: continue
    _base = _s['costo_mediana'].iloc[0]
    ax.plot(_s['semana'], _s['costo_mediana']/_base*100, marker=CANASTA_MARKERS.get(_name,'o'),
            ms=4, color=CANASTA_COLORS.get(_name), label=_name)
ax.set_title(f'Índice de costo SEMANAL por canasta (base 100 = {serie_sem_dict[CANASTAS_ACTIVAS[0]]["semana"].iloc[0] if len(serie_sem_dict[CANASTAS_ACTIVAS[0]]) else ""})')
ax.set_ylabel('Índice (base 100)'); ax.legend(); ax.grid(alpha=.3)
_xt = serie_sem_dict[CANASTAS_ACTIVAS[0]]['semana'] if len(serie_sem_dict[CANASTAS_ACTIVAS[0]]) else []
if len(_xt): ax.set_xticks(_xt[::max(1,len(_xt)//12)]); plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
plt.tight_layout(); plt.show()

# Fig 2 — Índice MENSUAL de canastas vs IPC (base 100 primer mes)
if ipc is not None:
    fig, ax = plt.subplots(figsize=(13,6))
    for _name in CANASTAS_ACTIVAS:
        _c = comparativa_dict[_name]
        if 'idx_canasta' in _c.columns and len(_c):
            ax.plot(_c['mes'], _c['idx_canasta'], marker=CANASTA_MARKERS.get(_name,'o'), ms=4,
                    color=CANASTA_COLORS.get(_name), label=f'Canasta {_name}')
    _c0 = comparativa_dict[CANASTAS_ACTIVAS[0]]
    if 'idx_ipc_gral' in _c0.columns:
        ax.plot(_c0['mes'], _c0['idx_ipc_gral'], '--', color='black', lw=2, label='IPC General')
        if _c0['idx_ipc_alim'].notna().any():
            ax.plot(_c0['mes'], _c0['idx_ipc_alim'], ':', color='gray', lw=2, label='IPC Alimentos')
    ax.set_title('Canastas vs IPC — índice mensual (base 100)'); ax.set_ylabel('Índice (base 100)')
    ax.legend(); ax.grid(alpha=.3); plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
    plt.tight_layout(); plt.show()

# Fig 3 — Composición por rubro (último mes), barras apiladas por canasta
_rubros = sorted(set().union(*[set(rubro_share_dict[n]['rubro']) for n in CANASTAS_ACTIVAS]))
_cmap = plt.get_cmap('tab20', max(1, len(_rubros)))
fig, ax = plt.subplots(figsize=(11,6)); _bottom = np.zeros(len(CANASTAS_ACTIVAS))
for _i,_r in enumerate(_rubros):
    _vals = [float(rubro_share_dict[n].set_index('rubro')['costo_mensual'].get(_r, 0)) for n in CANASTAS_ACTIVAS]
    ax.bar(CANASTAS_ACTIVAS, _vals, bottom=_bottom, label=_r, color=_cmap(_i))
    _bottom += np.array(_vals)
ax.set_title(f'Composición del costo por rubro — {_ult_mes}'); ax.set_ylabel('$ / mes')
ax.legend(bbox_to_anchor=(1.02,1), loc='upper left', fontsize=8); ax.grid(alpha=.3, axis='y')
plt.tight_layout(); plt.show()
''' ))

# ── CELL 12 — PROVINCIAS + CADENAS ─────────────────────────────────────────────
cells.append(cell_code(r'''# ============================================================
# CELDA 12 — Desagregación por PROVINCIA y CADENA (último mes)
# ============================================================
prov_dict = {}; cadena_dict = {}
_cs_um = costo_suc[costo_suc['mes']==_ult_mes]
for _name in CANASTAS_ACTIVAS:
    _cs = _cs_um[_cs_um['canasta']==_name]
    _p = (_cs.groupby('provincia').agg(costo_mediana=('costo','median'), costo_prom=('costo', _pmean),
                                       n_sucursales=('id_sucursal','nunique')).reset_index())
    _p['confiable'] = _p['n_sucursales'] >= MIN_SUC_AGG
    prov_dict[_name] = _p.sort_values('costo_mediana')
    _c = (_cs.groupby('cadena').agg(costo_mediana=('costo','median'), costo_prom=('costo', _pmean),
                                    n_sucursales=('id_sucursal','nunique')).reset_index())
    _c['confiable'] = _c['n_sucursales'] >= MIN_SUC_AGG
    cadena_dict[_name] = _c.sort_values('costo_mediana')

for _name in CANASTAS_ACTIVAS:
    _p = prov_dict[_name]; _pc = _p[_p['confiable']]
    _c = cadena_dict[_name]; _cc = _c[_c['confiable']]
    print(f'=== [{_name}] {_ult_mes} — provincias confiables (n≥{MIN_SUC_AGG}): {len(_pc)} ===')
    if len(_pc):
        print(f'   más barata: {_pc.iloc[0]["provincia"]} ${_pc.iloc[0]["costo_mediana"]:,.0f} | '
              f'más cara: {_pc.iloc[-1]["provincia"]} ${_pc.iloc[-1]["costo_mediana"]:,.0f}')
    if len(_cc):
        print(f'   cadena más barata: {_cc.iloc[0]["cadena"]} ${_cc.iloc[0]["costo_mediana"]:,.0f} | '
              f'más cara: {_cc.iloc[-1]["cadena"]} ${_cc.iloc[-1]["costo_mediana"]:,.0f}')
''' ))

# ── CELL 13 — DIAGNÓSTICOS DE COBERTURA (para refinar) ─────────────────────────
cells.append(cell_code(r'''# ============================================================
# CELDA 13 — DIAGNÓSTICOS: cobertura por EAN y por tipo fresco (copiá esto para refinar)
# ============================================================
# Cobertura geográfica por ítem en el ÚLTIMO MES (n_cadenas / n_provincias / n_sucursales).
# Ítems con baja cobertura NO son comparables entre cadenas/provincias → candidatos a
# reemplazar. Frescos: además nº de variantes (EANs) capturadas por la regla de nombre.
_dm = datos_sem[datos_sem['mes']==_ult_mes].merge(suc_geo[_SK+['cadena','provincia']], on=_SK, how='left')

# --- Empaquetados ---
_emp_cov = (_dm[_dm['ean_norm'].isin(EANS_EMP)].groupby('ean_norm')
            .agg(n_cadenas=('cadena','nunique'), n_provincias=('provincia','nunique'),
                 n_sucursales=('id_sucursal','nunique'), precio_med=('precio','median')).reset_index())
_rows = []
for _name in CANASTAS_ACTIVAS:
    for _ean,(_desc,_q,_rub,_cat) in CANASTAS_EMP[_name].items():
        _r = _emp_cov[_emp_cov['ean_norm']==_ean]
        _rows.append({'canasta':_name,'ean':_ean,'descripcion':_desc,'rubro':_rub,'cantidad':_q,
                      'n_cadenas':int(_r['n_cadenas'].iloc[0]) if len(_r) else 0,
                      'n_provincias':int(_r['n_provincias'].iloc[0]) if len(_r) else 0,
                      'n_sucursales':int(_r['n_sucursales'].iloc[0]) if len(_r) else 0,
                      'precio_med':round(float(_r['precio_med'].iloc[0]),1) if len(_r) else None})
cobertura_emp = pd.DataFrame(_rows)
cobertura_emp['comparable'] = (cobertura_emp['n_cadenas']>=3) & (cobertura_emp['n_provincias']>=15)
_sindata = cobertura_emp[cobertura_emp['n_sucursales']==0]
_pobre   = cobertura_emp[(cobertura_emp['n_sucursales']>0) & (~cobertura_emp['comparable'])]
print(f'=== EMPAQUETADOS — cobertura (último mes {_ult_mes}) ===')
print(f'  Total ítems-canasta: {len(cobertura_emp)} | SIN datos: {len(_sindata)} | baja comparabilidad: {len(_pobre)}')
if len(_sindata):
    print('  ⚠️ SIN DATOS en el SEPA (revisar/reemplazar EAN):')
    print(_sindata[['canasta','ean','descripcion']].to_string(index=False))
if len(_pobre):
    print('  ⚠️ BAJA COMPARABILIDAD (n_cadenas<3 o n_provincias<15):')
    print(_pobre[['canasta','ean','descripcion','n_cadenas','n_provincias','n_sucursales']].to_string(index=False))

# --- Frescos (por tipo) ---
_fr_dm = _dm[_dm['ean_norm'].isin(EANS_FRESCOS)].copy()
_fr_dm['tipo'] = _fr_dm['ean_norm'].map(EAN_TIPO)
cobertura_frescos = (_fr_dm.groupby('tipo')
    .agg(n_variantes=('ean_norm','nunique'), n_cadenas=('cadena','nunique'),
         n_provincias=('provincia','nunique'), n_sucursales=('id_sucursal','nunique')).reset_index())
_fac_map = {t:('kg' if FRESCO_INFO[t]['unidad']=='kg' else 'doc') for t in FRESCO_INFO}
cobertura_frescos['unidad'] = cobertura_frescos['tipo'].map(_fac_map)
cobertura_frescos['rubro'] = cobertura_frescos['tipo'].map(lambda t: FRESCO_INFO[t]['rubro'])
# precio normalizado nacional del tipo (último mes)
_pn = sval[(sval['item'].isin(FRESCO_INFO.keys())) & (sval['semana'].map(_mes_de_semana)==_ult_mes)]
_pnm = _pn.groupby('item')['price'].median()
cobertura_frescos['precio_norm_med'] = cobertura_frescos['tipo'].map(lambda t: round(float(_pnm.get(t, np.nan)),1))
cobertura_frescos = cobertura_frescos.merge(
    cobertura_fresco_maestro[['tipo','n_EANs_maestro','n_EANs_usables']], on='tipo', how='left')
print(f'\n=== FRESCOS — cobertura por tipo (último mes {_ult_mes}) ===')
print(cobertura_frescos[['tipo','rubro','unidad','n_variantes','n_cadenas','n_provincias',
                         'n_sucursales','precio_norm_med']].to_string(index=False))
_fr_pobre = cobertura_frescos[(cobertura_frescos['n_cadenas']<3)|(cobertura_frescos['n_provincias']<10)]
if len(_fr_pobre):
    print(f'  ⚠️ Tipos frescos con baja cobertura (afinar inc/exc o cantidad): {list(_fr_pobre["tipo"])}')
_fr_sin = [t for t in FRESCO_INFO if t not in set(cobertura_frescos['tipo'])]
if _fr_sin:
    print(f'  ⚠️ Tipos frescos SIN datos en el SEPA: {_fr_sin}')
print('\n>>> Copiá los bloques ⚠️ y las tablas de cobertura para refinar la composición.')
''' ))

# ── CELL 14 — EXCEL ────────────────────────────────────────────────────────────
cells.append(cell_code(r'''# ============================================================
# CELDA 14 — Exportación Excel (todas las tablas para revisar/refinar)
# ============================================================
from openpyxl.utils import get_column_letter
_xlsx = OUTPUT_DIR / f'canastas_alternativas_{ULTIMA_SEMANA}.xlsx'
with pd.ExcelWriter(_xlsx, engine='openpyxl') as _w:
    # Resumen
    _res = []
    for _name in CANASTAS_ACTIVAS:
        _sm = serie_mes_dict[_name]; _ss = serie_sem_dict[_name]
        _res.append({'canasta':_name,
                     'costo_mensual_ult': round(float(_sm['canasta_mediana'].iloc[-1]),0) if len(_sm) else None,
                     'var_mensual_%': round(float(_sm['var_mensual_%'].iloc[-1]),1) if len(_sm)>1 else None,
                     'costo_semanal_ult': round(float(_ss['costo_mediana'].iloc[-1]),0) if len(_ss) else None,
                     'n_productos_emp': len(CANASTAS_EMP[_name]),
                     'n_tipos_frescos': sum(1 for t in FRESCO_INFO if FRESCO_INFO[t]['qty'][CANASTAS_ACTIVAS.index(_name)]>0)})
    pd.DataFrame(_res).to_excel(_w, 'Resumen', index=False)
    # Series
    for _name in CANASTAS_ACTIVAS:
        _sfx = _name[:20]
        serie_sem_dict[_name].to_excel(_w, f'Sem_{_sfx}', index=False)
        serie_mes_dict[_name].to_excel(_w, f'Mes_{_sfx}', index=False)
        comparativa_dict[_name].to_excel(_w, f'vsIPC_{_sfx}', index=False)
        rubro_sem_dict[_name].to_excel(_w, f'Rubro_sem_{_sfx}'[:31], index=False)
        rubro_share_dict[_name].to_excel(_w, f'Comp_rubro_{_sfx}'[:31], index=False)
        detalle_dict[_name].to_excel(_w, f'Detalle_{_sfx}'[:31], index=False)
        prov_dict[_name].to_excel(_w, f'Prov_{_sfx}'[:31], index=False)
        cadena_dict[_name].to_excel(_w, f'Cadena_{_sfx}'[:31], index=False)
    # Diagnósticos
    cobertura_emp.to_excel(_w, 'Cobertura_emp', index=False)
    cobertura_frescos.to_excel(_w, 'Cobertura_frescos', index=False)
print(f'✅ Excel: {_xlsx.name}  ({_xlsx.stat().st_size/1024:.0f} KB)')
print(f'   Subilo/compartilo para refinar. Hojas: Resumen, Sem_*, Mes_*, vsIPC_*, Rubro_sem_*, '
      f'Comp_rubro_*, Detalle_*, Prov_*, Cadena_*, Cobertura_emp, Cobertura_frescos')
''' ))

# ── GENERAR EL NOTEBOOK ────────────────────────────────────────────────────────
nb = {'cells': cells,
      'metadata': {'kernelspec': {'display_name':'Python 3','language':'python','name':'python3'},
                   'language_info': {'name':'python'}},
      'nbformat': 4, 'nbformat_minor': 5}
_out = os.path.join(os.path.dirname(__file__), '07_evolucion_canastas_alternativas.ipynb')
with open(_out, 'w', encoding='utf-8') as _f:
    json.dump(nb, _f, ensure_ascii=False, indent=1)
print(f'Notebook generado: {_out}  ({len(cells)} celdas)')







