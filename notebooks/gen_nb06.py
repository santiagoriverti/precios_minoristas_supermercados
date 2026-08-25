"""Script to generate 06_evolucion_brecha_celiaca.ipynb — Brecha TACC vs sin-TACC.

Evalua la evolucion DIARIA, SEMANAL y MENSUAL de la BRECHA entre una canasta base
(productos con TACC) y su equivalente sin-TACC (canasta celiaca), usando SOLO tipos
de producto con dicotomia celiaca (sin diluir con limpieza/higiene/otros alimentos).

Metodologia (acordada con los investigadores):
- Cada TIPO de producto (fideos, galletitas, pan rallado, etc.) tiene 2-3 EANs TACC y
  2-3 EANs sin-TACC representativos. El precio del tipo en una sucursal/dia = PROMEDIO
  de los representativos PRESENTES (robusto a faltantes y a la eleccion del representativo).
- La brecha se calcula POOLED por grupo (nacional/provincia/cadena/localidad): para cada
  tipo se toma el precio TACC y el sin-TACC sobre las sucursales del grupo que ofrecen cada
  lado, y se arma la canasta base y celiaca. Esto es robusto a la BAJA COBERTURA sin-TACC
  (los productos sin-TACC estan en pocas gondolas, asi que exigir ambos lados en la MISMA
  sucursal el mismo dia da 0 obs). Se calcula ademas una brecha intra-sucursal por mes
  (best-effort) para las sucursales que si ofrecen ambos lados.
- Series por partida doble: MEDIANA (robusta) y PROMEDIO (outliers fuera), como nb02/nb05.
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

# ── CELL 0 ─────────────────────────────────────────────────────────────────────
cells.append(cell_md("""# SEPA — Brecha Celíaca (TACC vs sin-TACC)

**Objetivo:** medir la **brecha** entre una canasta **base** (productos con TACC) y su
equivalente **sin-TACC** (canasta celíaca), y su evolución **diaria, semanal y mensual**,
desagregada por provincia, cadena, concentración de comercios y localidad.

**Metodología** (acordada con los investigadores):
- Solo **tipos de producto con dicotomía celíaca** (fideos, galletitas, pan rallado,
  harina/premezcla, rebozador, caldo, cerveza→sidra…). Nada de limpieza/higiene/otros
  alimentos: la brecha se reporta sobre esa canasta acotada, sin maquillar.
- Cada tipo usa **2–3 EANs TACC y 2–3 sin-TACC representativos**; el precio del tipo en
  una sucursal/día = **promedio de los representativos presentes** (robusto a faltantes).
- La brecha se calcula **pooled por grupo** (nacional/provincia/cadena/localidad): por tipo se
  toma el precio TACC y el sin-TACC sobre las sucursales del grupo que ofrecen cada lado. Es
  robusto a la **baja cobertura** de los sin-TACC (exigir ambos lados en la misma sucursal el
  mismo día da 0 obs). Hay además una brecha **intra-sucursal por mes** (best-effort).
- Series por partida doble: **mediana** (robusta) y **promedio** (outliers fuera).

**Config en la CELDA 1**: el diccionario `TIPOS` (tipo → EANs TACC / sin-TACC / cantidad).

**Estructura:** Config → Setup → Maestros → Parseo de tipos → ZIPs → Lectura diaria →
Brecha por sucursal×día → Series (diaria/semanal/mensual) → Gráficos → Mapa → Excel"""))

# ── CELL 1 — CONFIG ────────────────────────────────────────────────────────────
cells.append(cell_code("""\
# ===========================================================
# CONFIGURACIÓN — Modificar solo esta sección
# ===========================================================
# TIPOS: un diccionario tipo -> {qty, tacc:[EANs], sin_tacc:[EANs]}.
#   - Poné VARIOS EANs candidatos por lado (cuantos más, más cobertura por sucursal).
#   - En cada sucursal/día se usa el precio de LOS candidatos que esa sucursal tenga
#     (mediana robusta, $/100g). Un tipo cuenta EN ESA SUCURSAL si tiene al menos 1
#     candidato TACC y 1 sin-TACC → la brecha del tipo se calcula INTRA-SUCURSAL.
#   - 'qty' = peso del tipo en la canasta (para la brecha agregada por sucursal).
# LISTAS AMPLIAS curadas del Maestro (marcas mainstream + varias presentaciones).
# Ajustá con la hoja Cobertura del primer run (n_tacc/n_sin por tipo).
TIPOS = {
    'Fideos secos': {
        'qty': 4,
        # TACC: Lucchetti · Matarazzo · Favorita (todos 500 g) — alta cobertura (canasta_repr. 07/2026, ~1900-2500 suc.)
        'tacc':     ['7790070336385','7790070336118','7790070336149','7790070336316',
                     '7790070336293','7790070320285','7790070320308','7790070320292'],
        # sin-TACC: Blue Patna · Grandiet · Matarazzo s/TACC · otras (maíz/arroz, 500 g)
        'sin_tacc': ['7730114000780','7730114000797','7797330105590','7797330105606',
                     '7790070321800','7790070321794','7798031470024','7794903232240'],
    },
    'Galletitas dulces': {
        'qty': 3,
        # TACC: 9deOro · Don Satur · Chocolinas · Bagley Rumba · Sonrisas · Maná (galletita dulce base) — alta cobertura
        'tacc':     ['7792200000128','7795735000335','7790040143234','7790040143524',
                     '7790040133471','7790040137844'],
        # sin-TACC: Santa María · Smams · Natuzen · Nina · varias
        'sin_tacc': ['7798294150435','7798308250205','7798082000317','7798082000331',
                     '0655257736631','7798079230017','7798079230062','7798181510120','7798181510199'],
    },
    'Galletitas saladas / crackers': {
        'qty': 2,
        # TACC (base trigo): 9deOro · Don Satur · Traviata · Tosti · Hogareñas — alta cobertura
        'tacc':     ['7792200000159','7795735000328','7790040144095','7794529041608',
                     '7790040136069'],
        # sin-TACC (arroz): Crisppino · Olienka · Shiva · Viavita
        'sin_tacc': ['7798199770035','7798199770042','7798289620080','7798289620097',
                     '0617308824087','0617308824094','7798195940173'],
    },
    'Pan rallado / rebozador': {
        'qty': 2,
        # TACC: Preferido · Mamá Cocina · Lucchetti · Pureza · Favorita (pan rallado) — alta cobertura
        'tacc':     ['7790070433169','7792180004741','7790070433275','7792180136480','7790070433312'],
        # sin-TACC: Bio · La Delfina · Maizena · Marvese
        'sin_tacc': ['7798221641845','7798221641944','7798131130200','7798131130231',
                     '7794000005303','7794000007291','7798306830164'],
    },
    # ⚠️ SUSTITUCIÓN (harina de trigo vs premezcla) — NO es el mismo producto sin gluten
    #    y su brecha es enorme (~+700%). Descomentá SOLO si la querés incluir; para una
    #    brecha "like-for-like" pura dejala comentada.
    # 'Harina / premezcla': {
    #     'qty': 2,
    #     'tacc':     ['7792180004512','7790070506924','7792180001528'],
    #     'sin_tacc': ['7790070508010','7794000005273','7798239780178'],
    # },
}

SEPA_SOURCE = 'mi_drive'   # 'mi_drive' | 'local'
SEPA_DIR    = '/content/drive/MyDrive/carga'
OUTPUT_DIR  = '/content/drive/MyDrive/carga/output_brecha'

USE_CACHE = True

# Mínimo de tipos (con ambos lados) para que una sucursal cuente en la brecha de CANASTA.
# La brecha POR TIPO no lo usa (basta ese tipo presente en la sucursal). 1 = permisivo.
MIN_TIPOS = 1

# Período mínimo de la serie histórica (semanal/mensual)
MES_INICIO_HISTORICO = '2024-01'

# Ventana de la serie DIARIA (meses hacia atrás desde el último mes). La semanal y
# mensual usan TODO el histórico; la diaria solo esta ventana (evita gráficos gigantes).
VENTANA_DIARIA_MESES = 3

# Excluir estaciones de servicio / comercios no minoristas de referencia
CADENAS_FILTRAR = {'19', '2013', '3001', '4'}"""))

# ── CELL 2 — SETUP (idéntica a nb05, TMP/OUTPUT propios) ───────────────────────
cells.append(cell_code("""\
# ============================================================
# CELDA 2 — Montar Drive + dependencias + imports
# ============================================================
try:
    import google.colab
    from google.colab import drive
    drive.mount('/content/drive')
    print('Google Drive montado')
except ImportError:
    print('Entorno local')

import subprocess, sys
subprocess.run([sys.executable, '-m', 'pip', 'install',
                'openpyxl', 'tqdm', 'pyarrow', '-q'], check=False)

import zipfile, gzip, re, shutil, warnings, gc, hashlib, calendar as _cal
import json as _json
from pathlib import Path
from tqdm.auto import tqdm
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.dates as mdates
from matplotlib.colors import LinearSegmentedColormap, Normalize
import seaborn as sns

plt.rcParams['figure.figsize'] = (13, 6)
plt.rcParams['font.size'] = 11
sns.set_theme(style='whitegrid')
pd.set_option('display.max_columns', 50)
pd.set_option('display.float_format', '{:,.2f}'.format)

SEPA_DIR   = Path(SEPA_DIR)
OUTPUT_DIR = Path(OUTPUT_DIR)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR  = OUTPUT_DIR / '_cache'
if USE_CACHE:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR = Path('/content/tmp_sepa_nb06')
TMP_DIR.mkdir(exist_ok=True)

GEOJSON_PATH = SEPA_DIR / 'ar.json'

def normalizar_ean(s):
    if pd.isna(s): return None
    s = str(s).strip().lstrip('0')
    return s if s else '0'

# EANs de referencia SOLO para detectar el factor centavos/pesos de cada mes.
REF_EANS_FACTOR = {'7790072002080'.lstrip('0'), '7790070320285'.lstrip('0'), '7790132098459'.lstrip('0')}

# ── Promedio con outliers fuera (banda relativa a la mediana) ────────────────
# Descarta valores fuera de [mediana/4, mediana x4] antes de promediar. Robusto a
# errores gruesos del SEPA a cualquier tamaño de muestra. (Igual que nb02/nb05.)
def _pmean(_s):
    _s = pd.to_numeric(_s, errors='coerce').dropna()
    if len(_s) == 0: return float('nan')
    _m = _s.median()
    if _m and _m > 0:
        _f = _s[(_s >= _m/4) & (_s <= _m*4)]
        if len(_f) > 0: _s = _f
    return _s.mean()

print(f'SEPA_DIR:   {SEPA_DIR}')
print(f'OUTPUT_DIR: {OUTPUT_DIR}')
print(f'  ar.json:  {"OK" if GEOJSON_PATH.exists() else "NO ENCONTRADO (mapa se saltea)"}')"""))

# ── CELL 3 — MAESTROS (idéntica a nb05) ────────────────────────────────────────
cells.append(cell_code("""\
# ============================================================
# CELDA 3 — Maestros de sucursales, cadenas, provincias y productos
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
    maestro_suc['sucursales_latitud'].notna() &
    maestro_suc['sucursales_longitud'].notna() &
    (maestro_suc['sucursales_latitud'].between(-55, -22)) &
    (maestro_suc['sucursales_longitud'].between(-73, -53))
].copy()
IDS_PAIS = set(zip(suc_pais['id_comercio'], suc_pais['id_bandera'], suc_pais['id_sucursal']))
print(f'  Sucursales validas: {len(suc_pais):,} | IDs unicos: {len(IDS_PAIS):,}')

NOMBRES_COMPUESTOS = {
    ('9','1'):'Vea',('9','2'):'Disco',('9','3'):'Jumbo',
    ('10','1'):'Carrefour',('10','2'):'Carrefour Market',('10','3'):'Carrefour Express',
    ('11','2'):'ChangoMas',('11','4'):'Hiper ChangoMas',('11','5'):'Mi ChangoMas',
    ('16','1'):'Hipermercado Libertad',('16','2'):'Mini Libertad',
}
NOMBRES_SIMPLES = {
    '2':'La Anonima','3':'Cadena 3','5':'Hipermercado Misiones',
    '8':'Cadena 8 (Cordoba)','12':'Coto','13':'Cooperativa Obrera',
    '15':'DIA','20':'LAR','21':'Toledo','23':'Cadena 23','47':'Pasamonte',
}

def asignar_cadena(row):
    k = (row['id_comercio'], row['id_bandera'])
    if k in NOMBRES_COMPUESTOS: return NOMBRES_COMPUESTOS[k]
    if row['id_comercio'] in NOMBRES_SIMPLES: return NOMBRES_SIMPLES[row['id_comercio']]
    return f"Cadena {row['id_comercio']}"

PROV_NORM = {
    'Ciudad Autonoma de Buenos Aires':'CABA',
    'Ciudad Autónoma de Buenos Aires':'CABA',
    'Provincia de Buenos Aires':'Buenos Aires',
    'Provincia de Catamarca':'Catamarca',
    'Provincia del Chaco':'Chaco','Provincia del Chubut':'Chubut',
    'Provincia de Cordoba':'Córdoba','Provincia de Córdoba':'Córdoba',
    'Provincia de Corrientes':'Corrientes',
    'Provincia de Entre Rios':'Entre Ríos','Provincia de Entre Ríos':'Entre Ríos',
    'Provincia de Formosa':'Formosa','Provincia de Jujuy':'Jujuy',
    'Provincia de La Pampa':'La Pampa','Provincia de La Rioja':'La Rioja',
    'Provincia de Mendoza':'Mendoza','Provincia de Misiones':'Misiones',
    'Provincia del Neuquen':'Neuquén','Provincia del Neuquén':'Neuquén','Neuquén':'Neuquén',
    'Provincia de Rio Negro':'Río Negro','Provincia de Río Negro':'Río Negro',
    'Provincia de Salta':'Salta','Provincia de San Juan':'San Juan',
    'Provincia de San Luis':'San Luis','Provincia de Santa Cruz':'Santa Cruz',
    'Provincia de Santa Fe':'Santa Fe',
    'Provincia de Santiago del Estero':'Santiago del Estero',
    'Provincia de Tierra del Fuego, Antartida e Islas del Atlantico Sur':'Tierra del Fuego',
    'Provincia de Tierra del Fuego, Antártida e Islas del Atlántico Sur':'Tierra del Fuego',
    'Tierra del Fuego':'Tierra del Fuego',
    'Provincia de Tucuman':'Tucumán','Provincia de Tucumán':'Tucumán',
    'Buenos Aires':'Buenos Aires','CABA':'CABA','Catamarca':'Catamarca',
    'Chaco':'Chaco','Chubut':'Chubut','Córdoba':'Córdoba','Corrientes':'Corrientes',
    'Entre Ríos':'Entre Ríos','Formosa':'Formosa','Jujuy':'Jujuy',
    'La Pampa':'La Pampa','La Rioja':'La Rioja','Mendoza':'Mendoza',
    'Misiones':'Misiones','Río Negro':'Río Negro','Salta':'Salta',
    'San Juan':'San Juan','San juan':'San Juan','SAN JUAN':'San Juan',
    'San Luis':'San Luis','Santa Cruz':'Santa Cruz',
    'Santa Fe':'Santa Fe','Santiago del Estero':'Santiago del Estero','Tucumán':'Tucumán',
}
PESOS_POBLACION = {
    'Buenos Aires':17709732,'CABA':3075646,'Catamarca':415438,
    'Chaco':1204541,'Chubut':618994,'Córdoba':3978984,
    'Corrientes':1120801,'Entre Ríos':1385961,'Formosa':605193,
    'Jujuy':770881,'La Pampa':368550,'La Rioja':393531,
    'Mendoza':2014533,'Misiones':1261294,'Neuquén':664057,
    'Río Negro':747610,'Salta':1441998,'San Juan':781217,
    'San Luis':531745,'Santa Cruz':333473,'Santa Fe':3556522,
    'Santiago del Estero':1019304,'Tierra del Fuego':190641,'Tucumán':1737127,
}

_mp_raw = leer_maestro('Maestro de Productos Interno.xlsx', dtype=str,
                       usecols=['producto_sepa_id','producto_descripcion','producto_marca','rubro',
                                'producto_cantidad_presentacion','producto_unidad_medida_presentac'])
MP_META = _mp_raw.rename(columns={'producto_descripcion':'descripcion','producto_marca':'marca'})
MP_META['ean_norm'] = MP_META['producto_sepa_id'].map(normalizar_ean)
# gramos/ml de la presentación → para normalizar el precio a $/100g (comparabilidad
# entre presentaciones distintas: fideos 500g vs harina 1kg, etc.)
def _to_gramos(_q, _u):
    _q = pd.to_numeric(str(_q).replace(',', '.'), errors='coerce'); _u = str(_u).strip().lower()
    if pd.isna(_q) or _q <= 0: return np.nan
    if _u in ('kg','kgm','l','lt','litro','litros','kilogramo','kilogramos'): return _q * 1000
    if _u in ('gr','g','grs','gramo','gramos','ml','cc','mililitro'): return _q
    return np.nan
MP_META['grams'] = [_to_gramos(a, b) for a, b in zip(MP_META['producto_cantidad_presentacion'],
                                                     MP_META['producto_unidad_medida_presentac'])]
MP_META = (MP_META.dropna(subset=['ean_norm']).drop_duplicates('ean_norm')
           .set_index('ean_norm')[['descripcion','marca','rubro','grams']])
print(f'  Maestro de productos: {len(MP_META):,} EANs con metadata')
print('Maestros OK')"""))

# ── CELL 4 — PARSEO DE TIPOS (config) ──────────────────────────────────────────
cells.append(cell_code("""\
# ============================================================
# CELDA 4 — Parseo de tipos TACC / sin-TACC (CELDA 1)
# ============================================================
def _norm_lista(_lst):
    _out = []
    for _e in _lst:
        _limpio = re.sub(r'\\D', '', str(_e))
        if _limpio:
            _out.append(_limpio.lstrip('0') or '0')
    return _out

TIPO_TACC = {}      # tipo -> set(ean_norm) TACC
TIPO_SIN  = {}      # tipo -> set(ean_norm) sin-TACC
TIPO_QTY  = {}      # tipo -> cantidad
EAN_TIPO  = {}      # ean_norm -> tipo
EAN_ROL   = {}      # ean_norm -> 'tacc' | 'sin'
EAN_DESC  = {}      # ean_norm -> descripcion (del maestro o el propio EAN)

for _tipo, _cfg in TIPOS.items():
    _tacc = set(_norm_lista(_cfg.get('tacc', [])))
    _sin  = set(_norm_lista(_cfg.get('sin_tacc', [])))
    if not _tacc or not _sin:
        print(f'AVISO: el tipo \"{_tipo}\" no tiene EANs en ambos lados — se ignora.')
        continue
    TIPO_TACC[_tipo] = _tacc
    TIPO_SIN[_tipo]  = _sin
    TIPO_QTY[_tipo]  = float(_cfg.get('qty', 1))
    for _e in _tacc: EAN_TIPO[_e] = _tipo; EAN_ROL[_e] = 'tacc'
    for _e in _sin:  EAN_TIPO[_e] = _tipo; EAN_ROL[_e] = 'sin'

if not TIPO_TACC:
    raise ValueError('Ningún tipo válido en TIPOS (cada tipo necesita EANs TACC y sin-TACC).')

EANS_CONFIG = set(EAN_TIPO.keys())
EAN_GRAMS = {}      # ean_norm -> gramos/ml de la presentación (para normalizar a $/100g)
_sin_gramos = []
for _e in EANS_CONFIG:
    if _e in MP_META.index and pd.notna(MP_META.loc[_e, 'descripcion']):
        EAN_DESC[_e] = str(MP_META.loc[_e, 'descripcion'])[:50]
    else:
        EAN_DESC[_e] = f'EAN {_e}'
    _g = MP_META.loc[_e, 'grams'] if _e in MP_META.index else np.nan
    if pd.notna(_g) and _g > 0:
        EAN_GRAMS[_e] = float(_g)
    else:
        _sin_gramos.append(_e)
if _sin_gramos:
    print(f'AVISO: {len(_sin_gramos)} EAN sin presentación en el maestro — usan precio por paquete '
          f'(NO normalizado a $/100g): {_sin_gramos}')

print(f'Tipos activos: {len(TIPO_TACC)} | EANs de config: {len(EANS_CONFIG)}')
for _t in TIPO_TACC:
    print(f'  [{_t}] qty={TIPO_QTY[_t]:.0f} | TACC: {len(TIPO_TACC[_t])} · sin-TACC: {len(TIPO_SIN[_t])}')"""))

# ── CELL 5 — ZIP FUNCTIONS (idéntica a nb05) ───────────────────────────────────
cells.append(cell_code("""\
# ============================================================
# CELDA 5 — Funciones de lectura de ZIPs SEPA
# ============================================================
_PAT_SEM  = re.compile(r'^(\\d{4})(A|B)$', re.IGNORECASE)
_PAT_ARC  = re.compile(r'^(\\d{2})(\\d{4})_pais_parte.*COMPLETO.*\\.csv\\.gz$', re.IGNORECASE)
PAT_FECHA = re.compile(r'^precio_(\\d{8})$')

def detectar_semestres():
    result = []
    for z in sorted(SEPA_DIR.glob('*.zip')):
        m = _PAT_SEM.match(z.stem)
        if m:
            result.append((z, int(m.group(1)), m.group(2).upper()))
    return result

def archivos_por_mes(zip_path):
    meses = {}
    with zipfile.ZipFile(zip_path) as zf:
        for nombre in zf.namelist():
            m = _PAT_ARC.match(Path(nombre).name)
            if m:
                mes_n, anio = int(m.group(1)), int(m.group(2))
                meses.setdefault((anio, mes_n), []).append(nombre)
    return meses

# Mapa de meses disponibles -> (zip, archivos)
_mapa_mes = {}
for _zip_path, _anio, _sem in detectar_semestres():
    for (_anio_m, _mes_m), _archs in archivos_por_mes(_zip_path).items():
        _lbl = f'{_anio_m}-{_mes_m:02d}'
        if _lbl >= MES_INICIO_HISTORICO:
            _mapa_mes[_lbl] = (_zip_path, _archs)
_meses_disp = sorted(_mapa_mes)
if not _meses_disp:
    raise RuntimeError(f'No hay meses disponibles >= {MES_INICIO_HISTORICO}')
_mes_actual = _meses_disp[-1]   # mes en curso -> NUNCA se cachea
print(f'Meses disponibles: {len(_meses_disp)}  ({_meses_disp[0]} → {_meses_disp[-1]})')"""))

# ── CELL 6 — LECTURA DIARIA (todos los meses, dimensión fecha) ─────────────────
cells.append(cell_code("""\
# ============================================================
# CELDA 6 — Lectura DIARIA de precios (una fila por sucursal×EAN×día)
# ============================================================
# Lee los EANs de config en todos los meses >= MES_INICIO_HISTORICO conservando el
# día (columnas precio_YYYYMMDD). Cache de meses cerrados; el mes en curso se relee.
_cache_key    = hashlib.md5('|'.join(sorted(EANS_CONFIG)).encode()).hexdigest()[:8]
_cache_path   = CACHE_DIR / f'brecha_dia_{_cache_key}_v1.parquet'
_EANS_LECTURA = EANS_CONFIG | REF_EANS_FACTOR

def _leer_mes_dia(_lbl):
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
                _chunk = _chunk[_chunk['ean_norm'].isin(_EANS_LECTURA)].copy()
                if len(_chunk) == 0: continue
                for _c in ['id_comercio','id_bandera','id_sucursal']:
                    _chunk[_c] = _chunk[_c].astype(str)
                _chunk['_k'] = list(zip(_chunk['id_comercio'],_chunk['id_bandera'],_chunk['id_sucursal']))
                _chunk = _chunk[_chunk['_k'].isin(IDS_PAIS)].drop(columns=['_k']).copy()
                if len(_chunk) == 0: continue
                _cols_p = [c for c in _chunk.columns if PAT_FECHA.match(c)]
                if not _cols_p: continue
                _mlt = _chunk.melt(
                    id_vars=['id_comercio','id_bandera','id_sucursal','ean_norm'],
                    value_vars=_cols_p, var_name='_col', value_name='precio_raw')
                _mlt['precio'] = pd.to_numeric(_mlt['precio_raw'].replace('NA', np.nan), errors='coerce')
                _mlt = _mlt[_mlt['precio'].notna() & (_mlt['precio'] > 0)].copy()
                _mlt['fecha'] = pd.to_datetime(_mlt['_col'].str[-8:], format='%Y%m%d', errors='coerce')
                _mlt = _mlt[_mlt['fecha'].notna()]
                _es_ref = _mlt['ean_norm'].isin(REF_EANS_FACTOR)
                if _es_ref.any():
                    _muestra_ref.extend(_mlt.loc[_es_ref, 'precio'].tolist())
                _mlt = _mlt[_mlt['ean_norm'].isin(EANS_CONFIG)]
                if len(_mlt) > 0:
                    _rows.append(_mlt[['id_comercio','id_bandera','id_sucursal','ean_norm','fecha','precio']])
        _tmp_p.unlink(missing_ok=True)
    if not _rows:
        return None
    _df = pd.concat(_rows, ignore_index=True)
    _med_ref = (pd.Series(_muestra_ref).median() if _muestra_ref else _df['precio'].median())
    _fac = 100 if _med_ref > 10_000 else 1
    if _fac == 100: _df['precio'] /= 100
    _df['mes'] = _lbl
    del _rows, _muestra_ref; gc.collect()
    return _df

# Meses cerrados: cache incremental
if USE_CACHE and _cache_path.exists():
    df_cache = pd.read_parquet(_cache_path)
    df_cache = df_cache[df_cache['mes'] < _mes_actual].copy()
else:
    df_cache = pd.DataFrame(columns=['id_comercio','id_bandera','id_sucursal','ean_norm','fecha','precio','mes'])

_en_cache = set(df_cache['mes'].unique())
_faltantes = [m for m in _meses_disp if m < _mes_actual and m not in _en_cache]
_nuevos = []
for _lbl in tqdm(_faltantes, desc='Meses cerrados'):
    _d = _leer_mes_dia(_lbl)
    if _d is not None: _nuevos.append(_d)
if _nuevos:
    df_cache = pd.concat([df_cache] + _nuevos, ignore_index=True)
    if USE_CACHE:
        df_cache.to_parquet(_cache_path, compression='snappy', index=False)
        print(f'Cache actualizado: {_cache_path.name} ({df_cache["mes"].nunique()} meses cerrados)')

# Mes en curso: siempre fresco
_actual = _leer_mes_dia(_mes_actual)
datos_dia = (pd.concat([df_cache] + ([_actual] if _actual is not None else []), ignore_index=True)
             if (len(df_cache) > 0 or _actual is not None)
             else pd.DataFrame(columns=df_cache.columns))
if len(datos_dia) == 0:
    raise RuntimeError('Sin datos para los EANs de config. Revisá los EANs de TIPOS (CELDA 1).')
datos_dia = datos_dia.sort_values('fecha').reset_index(drop=True)

ULTIMO_MES = _mes_actual
_NOM = {'01':'enero','02':'febrero','03':'marzo','04':'abril','05':'mayo','06':'junio',
        '07':'julio','08':'agosto','09':'septiembre','10':'octubre','11':'noviembre','12':'diciembre'}
NOMBRE_MES_TITLE = f"{_NOM[_mes_actual[5:7]]} {_mes_actual[:4]}".title()
print(f'Observaciones diarias: {len(datos_dia):,} | EANs con datos: {datos_dia["ean_norm"].nunique()}/{len(EANS_CONFIG)}')
print(f'Rango: {datos_dia["fecha"].min().date()} → {datos_dia["fecha"].max().date()} | Sucursales: {datos_dia.groupby(["id_comercio","id_bandera","id_sucursal"]).ngroups:,}')"""))

# ── CELL 7 — BRECHA POR SUCURSAL × DÍA ─────────────────────────────────────────
cells.append(cell_code("""\
# ============================================================
# CELDA 7 — Brecha INTRA-SUPERMERCADO por tipo (por sucursal, sobre el mes)
# ============================================================
# Para cada SUCURSAL y MES, por tipo, el precio de cada lado = mediana $/100g de los
# candidatos que esa sucursal tuvo ese mes (sobre todos sus días). Un tipo cuenta en
# esa sucursal-mes si tuvo ≥1 candidato TACC y ≥1 sin-TACC → la brecha del tipo se
# calcula DENTRO del mismo super (sin exigir el MISMO día → mucho más robusto). Luego
# se promedia entre supers (y por zonas/provincia/cadena).
datos_dia['tipo'] = datos_dia['ean_norm'].map(EAN_TIPO)
datos_dia['rol']  = datos_dia['ean_norm'].map(EAN_ROL)
datos_dia = datos_dia[~datos_dia['id_comercio'].isin(CADENAS_FILTRAR)].copy()

# Precio normalizado a $/100g (presentación del maestro; fallback = precio por paquete)
datos_dia['grams'] = datos_dia['ean_norm'].map(EAN_GRAMS)
datos_dia['precio_100'] = np.where(datos_dia['grams'].notna() & (datos_dia['grams'] > 0),
                                   datos_dia['precio'] / datos_dia['grams'] * 100,
                                   datos_dia['precio'])

# Precio del tipo por (sucursal, mes, lado) = mediana $/100g de los candidatos presentes
_sk = ['id_comercio','id_bandera','id_sucursal']
tp = (datos_dia.groupby(_sk + ['mes','tipo','rol'])['precio_100'].median()
      .reset_index().rename(columns={'precio_100':'precio_rep'}))

# ── Geo (una vez) ────────────────────────────────────────────────────────────
_PROV_BBOX = {
    'CABA':(-34.72,-34.52,-58.54,-58.33),'Tucumán':(-28.0,-26.0,-66.5,-64.5),
    'Jujuy':(-24.5,-21.5,-67.5,-63.5),'Misiones':(-28.5,-25.5,-56.5,-53.0),
    'Chaco':(-27.5,-24.0,-63.0,-57.5),'Formosa':(-26.5,-22.0,-62.5,-58.0),
    'Corrientes':(-30.5,-27.0,-60.0,-55.5),'Entre Ríos':(-34.0,-30.0,-60.5,-57.5),
    'San Luis':(-36.0,-32.5,-68.5,-65.0),'San Juan':(-34.5,-27.5,-71.0,-65.0),
    'La Rioja':(-32.5,-27.0,-70.0,-65.0),'Catamarca':(-29.5,-25.0,-70.5,-64.5),
    'Salta':(-26.5,-21.5,-68.5,-62.5),'Santiago del Estero':(-30.0,-25.5,-65.5,-61.5),
    'Mendoza':(-37.5,-32.0,-70.5,-66.5),'Neuquén':(-40.5,-36.0,-71.5,-68.5),
    'La Pampa':(-40.0,-35.0,-68.5,-63.5),'Santa Fe':(-34.5,-28.5,-62.5,-59.0),
    'Córdoba':(-39.0,-29.5,-67.0,-62.0),'Río Negro':(-42.5,-38.5,-71.5,-62.5),
    'Chubut':(-46.5,-41.0,-72.5,-63.0),'Buenos Aires':(-42.5,-33.5,-63.5,-56.5),
    'Santa Cruz':(-52.5,-46.0,-72.5,-65.5),'Tierra del Fuego':(-55.5,-51.0,-70.5,-63.5),
}
def _geocodif(lat, lon):
    if pd.isna(lat) or pd.isna(lon): return None
    for p,(la0,la1,lo0,lo1) in _PROV_BBOX.items():
        if la0 <= lat <= la1 and lo0 <= lon <= lo1: return p
    return None
_cols_suc = ['id_comercio','id_bandera','id_sucursal','sucursales_nombre',
             'sucursales_latitud','sucursales_longitud','sucursales_localidad','PROVINCIA']
suc_geo = suc_pais[_cols_suc].copy()
suc_geo['cadena'] = suc_geo.apply(asignar_cadena, axis=1)
suc_geo['PROVINCIA_NORM'] = suc_geo['PROVINCIA'].map(PROV_NORM).fillna(suc_geo['PROVINCIA'])
_n_recl = 0
for _idx,_row in suc_geo.iterrows():
    _p = _row['PROVINCIA_NORM']
    if _p not in _PROV_BBOX: continue
    _la0,_la1,_lo0,_lo1 = _PROV_BBOX[_p]
    if _la0 <= _row['sucursales_latitud'] <= _la1 and _lo0 <= _row['sucursales_longitud'] <= _lo1: continue
    _nueva = _geocodif(_row['sucursales_latitud'], _row['sucursales_longitud'])
    if _nueva and _nueva != _p:
        suc_geo.at[_idx,'PROVINCIA_NORM'] = _nueva; _n_recl += 1
if _n_recl: print(f'  Reclasificadas {_n_recl} sucursales por coordenadas')

tp = tp.merge(suc_geo[['id_comercio','id_bandera','id_sucursal','cadena','PROVINCIA_NORM',
                       'sucursales_localidad','sucursales_nombre']],
              on=['id_comercio','id_bandera','id_sucursal'], how='inner')
tp['localidad'] = (tp['sucursales_localidad'].astype(str).str.strip()
                   .replace({'':'N/D','nan':'N/D','None':'N/D'}))

# ── DIAGNÓSTICO de cobertura por tipo ────────────────────────────────────────
_cob_rows = []
print('=== Cobertura por tipo (sucursales que ofrecen cada lado, todo el período) ===')
for _t in TIPO_TACC:
    _st = tp[tp['tipo'] == _t]
    _set_t = set(map(tuple, _st[_st['rol']=='tacc'][_sk].drop_duplicates().to_numpy()))
    _set_s = set(map(tuple, _st[_st['rol']=='sin'][_sk].drop_duplicates().to_numpy()))
    _both  = _set_t & _set_s
    print(f'  [{_t}] TACC: {len(_set_t):>5} · sin-TACC: {len(_set_s):>5} · con AMBOS: {len(_both):>5}')
    _cob_rows.append({'tipo':_t,'sucursales_tacc':len(_set_t),'sucursales_sin_tacc':len(_set_s),'sucursales_ambos':len(_both)})
cobertura_tipo = pd.DataFrame(_cob_rows)

# ── ATÓMICO: brecha por (sucursal, mes, tipo) con AMBOS lados en ese super-mes ─
_idx = _sk + ['mes','PROVINCIA_NORM','cadena','localidad','sucursales_nombre','tipo']
_tacc = tp[tp['rol']=='tacc'][_idx + ['precio_rep']].rename(columns={'precio_rep':'tacc'})
_sin  = tp[tp['rol']=='sin'][_idx + ['precio_rep']].rename(columns={'precio_rep':'sin'})
bt_sm = _tacc.merge(_sin, on=_idx, how='inner')   # inner = ambos lados en el mismo super-mes
bt_sm['brecha_pct'] = (bt_sm['sin'] / bt_sm['tacc'] - 1) * 100
bt_sm['qty'] = bt_sm['tipo'].map(TIPO_QTY)
bt_sm['base_c'] = bt_sm['tacc'] * bt_sm['qty']
bt_sm['cel_c']  = bt_sm['sin']  * bt_sm['qty']

# ── Canasta por (sucursal, mes): suma sobre los tipos con ambos lados ────────
if len(bt_sm):
    brecha_suc_mes = (bt_sm.groupby(_sk + ['mes','PROVINCIA_NORM','cadena','localidad'])
                      .agg(base=('base_c','sum'), celiaca=('cel_c','sum'), n_tipos=('tipo','nunique'))
                      .reset_index())
    brecha_suc_mes = brecha_suc_mes[brecha_suc_mes['n_tipos'] >= MIN_TIPOS].copy()
    brecha_suc_mes['brecha_pct'] = (brecha_suc_mes['celiaca'] / brecha_suc_mes['base'] - 1) * 100
else:
    brecha_suc_mes = pd.DataFrame(columns=_sk + ['mes','PROVINCIA_NORM','cadena','localidad',
                                                 'base','celiaca','n_tipos','brecha_pct'])

_nsuc_bt = bt_sm[_sk].drop_duplicates().shape[0] if len(bt_sm) else 0
print(f'\\nObs (sucursal×mes×tipo) con ambos lados: {len(bt_sm):,} | sucursales con ≥1 par: {_nsuc_bt:,}')
print(f'Canasta por (sucursal×mes, ≥{MIN_TIPOS} tipos): {len(brecha_suc_mes):,} obs'
      + (f' | brecha mediana {brecha_suc_mes["brecha_pct"].median():+.1f}%' if len(brecha_suc_mes) else ''))"""))

# ── CELL 8 — SERIES (diaria / semanal / mensual) + desagregaciones ─────────────
cells.append(cell_code("""\
# ============================================================
# CELDA 8 — Brecha POR TIPO (intra-super) + evolución + desagregaciones
# ============================================================
# Todo se deriva de bt_sm (brecha por sucursal×mes×tipo) y brecha_suc_mes (canasta
# por sucursal×mes). Se promedia ENTRE sucursales (mediana + promedio robusto).
def _agg_tipo(df, keys):
    _cols = keys + ['tipo','tacc_100','sin_100','brecha_mediana','brecha_prom','n_sucursales']
    if len(df) == 0:
        return pd.DataFrame(columns=_cols)
    return (df.groupby(keys + ['tipo'])
            .agg(tacc_100=('tacc','median'), sin_100=('sin','median'),
                 brecha_mediana=('brecha_pct','median'), brecha_prom=('brecha_pct', _pmean),
                 n_sucursales=('id_sucursal','nunique')).reset_index())

def _agg_suc(df, keys):
    _cols = keys + ['brecha_mediana','brecha_prom','n_sucursales']
    if len(df) == 0:
        return pd.DataFrame(columns=_cols)
    return (df.groupby(keys)
            .agg(brecha_mediana=('brecha_pct','median'), brecha_prom=('brecha_pct', _pmean),
                 n_sucursales=('id_sucursal','nunique')).reset_index())

# Brecha POR TIPO (el número clave): mediana de las brechas intra-super
brecha_tipo         = _agg_tipo(bt_sm, [])
if len(brecha_tipo): brecha_tipo = brecha_tipo.sort_values('brecha_mediana')
brecha_tipo_mensual = _agg_tipo(bt_sm, ['mes'])
brecha_tipo_prov    = _agg_tipo(bt_sm, ['PROVINCIA_NORM']).rename(columns={'PROVINCIA_NORM':'provincia'})

# Series de CANASTA (brecha por sucursal, promediada entre supers). Granularidad MENSUAL
# (intra-super por mes; diaria/semanal no aplican a este método y quedan vacías).
serie_mensual = _agg_suc(brecha_suc_mes, ['mes'])
if len(serie_mensual): serie_mensual = serie_mensual.sort_values('mes')
serie_semanal = pd.DataFrame(columns=['semana','brecha_mediana','brecha_prom','n_sucursales'])
serie_diaria  = pd.DataFrame(columns=['fecha','brecha_mediana','brecha_prom','n_sucursales'])

# Desagregaciones (promedio entre supers, por zona)
brecha_prov   = _agg_suc(brecha_suc_mes, ['PROVINCIA_NORM']).rename(columns={'PROVINCIA_NORM':'provincia'})
if len(brecha_prov): brecha_prov = brecha_prov.sort_values('brecha_mediana')
brecha_cadena = _agg_suc(brecha_suc_mes, ['cadena'])
if len(brecha_cadena): brecha_cadena = brecha_cadena.sort_values('brecha_mediana')
concentracion = _agg_suc(brecha_suc_mes, ['localidad'])
if len(concentracion):
    concentracion = concentracion[concentracion['localidad'] != 'N/D'].sort_values('n_sucursales', ascending=False)

# ── Resumen ──────────────────────────────────────────────────────────────────
print('=== Brecha POR TIPO (intra-super, $/100g) — el número clave ===')
if len(brecha_tipo):
    print(brecha_tipo[['tipo','tacc_100','sin_100','brecha_mediana','n_sucursales']].round(1).to_string(index=False))
    print('  ⚠️ Revisá n_sucursales por tipo (y la hoja Cobertura): pocas = poco confiable.')
else:
    print('  (sin datos — revisá la Cobertura por tipo y los EANs de TIPOS)')

print('\\n=== Brecha de CANASTA mensual (intra-super) — últimos 6 ===')
if len(serie_mensual):
    print(serie_mensual.tail(6).round(1).to_string(index=False))
else:
    print('  (sin datos)')
if len(brecha_prov):
    print(f'\\nProvincia MENOR brecha: {brecha_prov.iloc[0]["provincia"]} ({brecha_prov.iloc[0]["brecha_mediana"]:+.1f}%)')
    print(f'Provincia MAYOR brecha: {brecha_prov.iloc[-1]["provincia"]} ({brecha_prov.iloc[-1]["brecha_mediana"]:+.1f}%)')

# ── Resumen ──────────────────────────────────────────────────────────────────
print('=== Brecha mensual (nacional, pooled) — últimos 6 ===')
if len(serie_mensual):
    print(serie_mensual.tail(6)[['mes','brecha_mediana','brecha_prom','n_sucursales']].to_string(index=False))
    if len(serie_mensual) >= 2:
        _b0, _b1 = serie_mensual['brecha_mediana'].iloc[0], serie_mensual['brecha_mediana'].iloc[-1]
        print(f'Brecha mediana: {_b0:+.2f}% ({serie_mensual["mes"].iloc[0]}) -> {_b1:+.2f}% ({serie_mensual["mes"].iloc[-1]}) | cambio {(_b1-_b0):+.2f} pp')
else:
    print('  (sin datos — revisá la cobertura por tipo arriba y los EANs de TIPOS)')
if len(brecha_prov):
    print(f'Provincia MENOR brecha: {brecha_prov.iloc[0]["provincia"]} ({brecha_prov.iloc[0]["brecha_mediana"]:+.2f}%)')
    print(f'Provincia MAYOR brecha: {brecha_prov.iloc[-1]["provincia"]} ({brecha_prov.iloc[-1]["brecha_mediana"]:+.2f}%)')"""))

# ── CELL 9 — GRÁFICOS ──────────────────────────────────────────────────────────
cells.append(cell_code("""\
# ============================================================
# CELDA 9 — Gráficos de la brecha
# ============================================================
MES = f'{ULTIMO_MES[5:7]}{ULTIMO_MES[:4]}'
_C_MED, _C_PRO = '#0055A4', '#D62728'

# 1) Serie temporal (mensual + semanal) con mediana y promedio
fig, ax = plt.subplots(figsize=(13, 6))
_sm = serie_mensual.copy(); _sm['fecha'] = pd.to_datetime(_sm['mes'] + '-01')
ax.plot(_sm['fecha'], _sm['brecha_mediana'], color=_C_MED, lw=2.5, marker='o', label='Brecha mensual (mediana)')
ax.plot(_sm['fecha'], _sm['brecha_prom'],   color=_C_PRO, lw=2.0, ls='--', marker='s', label='Brecha mensual (promedio)')
ax.axhline(_sm['brecha_mediana'].mean(), color='#888', ls=':', lw=1, label=f'Media período: {_sm["brecha_mediana"].mean():+.1f}%')
ax.set_ylabel('Brecha celíaca (%)'); ax.set_title('Evolución de la brecha celíaca (canasta sin-TACC vs base)')
ax.legend(); ax.grid(True, alpha=0.3)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f'{x:+.0f}%'))
plt.tight_layout(); _o = OUTPUT_DIR / f'brecha_mensual_{MES}.png'
plt.savefig(_o, dpi=200, bbox_inches='tight', facecolor='white'); plt.show()
print(f'Guardado: {_o.name}')

# 2) Serie DIARIA (ventana)
if len(serie_diaria) > 1:
    fig, ax = plt.subplots(figsize=(13, 5))
    ax.plot(serie_diaria['fecha'], serie_diaria['brecha_mediana'], color=_C_MED, lw=1.5, label='Diaria (mediana)')
    ax.plot(serie_diaria['fecha'], serie_diaria['brecha_prom'], color=_C_PRO, lw=1.2, alpha=0.8, label='Diaria (promedio)')
    ax.set_ylabel('Brecha (%)'); ax.set_title(f'Brecha diaria — últimos {VENTANA_DIARIA_MESES} meses')
    ax.legend(); ax.grid(True, alpha=0.3)
    plt.tight_layout(); _o = OUTPUT_DIR / f'brecha_diaria_{MES}.png'
    plt.savefig(_o, dpi=200, bbox_inches='tight', facecolor='white'); plt.show()
    print(f'Guardado: {_o.name}')

# 3) Brecha por provincia (barras)
fig, ax = plt.subplots(figsize=(11, max(5, len(brecha_prov)*0.35+2)))
_cols = plt.cm.RdYlGn_r(np.linspace(0.15, 0.9, len(brecha_prov)))
ax.barh(brecha_prov['provincia'], brecha_prov['brecha_mediana'], color=_cols, edgecolor='black', lw=0.4)
for _i,(_,_r) in enumerate(brecha_prov.iterrows()):
    ax.text(_r['brecha_mediana'], _i, f' {_r["brecha_mediana"]:+.1f}%', va='center', fontsize=8)
ax.set_xlabel('Brecha mediana (%)'); ax.set_title('Brecha celíaca por provincia')
ax.grid(True, alpha=0.3, axis='x')
plt.tight_layout(); _o = OUTPUT_DIR / f'brecha_provincia_{MES}.png'
plt.savefig(_o, dpi=200, bbox_inches='tight', facecolor='white'); plt.show()
print(f'Guardado: {_o.name}')

# 4) Brecha por cadena (barras)
_bc = brecha_cadena[brecha_cadena['n_sucursales'] >= 5]
if len(_bc) > 0:
    fig, ax = plt.subplots(figsize=(11, max(4, len(_bc)*0.4+2)))
    _cols = plt.cm.RdYlGn_r(np.linspace(0.15, 0.9, len(_bc)))
    ax.barh(_bc['cadena'], _bc['brecha_mediana'], color=_cols, edgecolor='black', lw=0.4)
    for _i,(_,_r) in enumerate(_bc.iterrows()):
        ax.text(_r['brecha_mediana'], _i, f' {_r["brecha_mediana"]:+.1f}%', va='center', fontsize=8)
    ax.set_xlabel('Brecha mediana (%)'); ax.set_title('Brecha celíaca por cadena (≥5 sucursales)')
    ax.grid(True, alpha=0.3, axis='x')
    plt.tight_layout(); _o = OUTPUT_DIR / f'brecha_cadena_{MES}.png'
    plt.savefig(_o, dpi=200, bbox_inches='tight', facecolor='white'); plt.show()
    print(f'Guardado: {_o.name}')

# 5) Brecha vs concentración de comercios (scatter)
_cc = concentracion[concentracion['n_sucursales'] >= 2]
if len(_cc) >= 3:
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.scatter(_cc['n_sucursales'], _cc['brecha_mediana'], s=28, alpha=0.6, color=_C_MED, edgecolor='white')
    _corr = _cc['n_sucursales'].corr(_cc['brecha_mediana'])
    _corr_str = f'{_corr:+.2f}' if pd.notna(_corr) else 'n/d'
    ax.set_xscale('log')
    ax.set_xlabel('Nº de sucursales en la localidad (log)'); ax.set_ylabel('Brecha mediana (%)')
    ax.set_title(f'Brecha vs concentración de comercios (corr={_corr_str})')
    ax.grid(True, alpha=0.3)
    plt.tight_layout(); _o = OUTPUT_DIR / f'brecha_concentracion_{MES}.png'
    plt.savefig(_o, dpi=200, bbox_inches='tight', facecolor='white'); plt.show()
    print(f'Guardado: {_o.name} | correlación brecha–concentración: {_corr_str}')

# 6) Brecha POR TIPO (barras) — el gráfico clave
if len(brecha_tipo):
    _bt = brecha_tipo.sort_values('brecha_mediana')
    fig, ax = plt.subplots(figsize=(11, max(4, len(_bt)*0.7+2)))
    _cols = plt.cm.RdYlGn_r(np.linspace(0.2, 0.9, len(_bt)))
    ax.barh(_bt['tipo'], _bt['brecha_mediana'], color=_cols, edgecolor='black', lw=0.4)
    for _i,(_,_r) in enumerate(_bt.iterrows()):
        ax.text(_r['brecha_mediana'], _i, f'  {_r["brecha_mediana"]:+.0f}%  ({int(_r["n_sucursales"])} sucs con ambos)',
                va='center', fontsize=8)
    ax.set_xlabel('Brecha mediana (%) — precio sin-TACC vs TACC, $/100g')
    ax.set_title('Brecha celíaca POR TIPO de producto')
    ax.grid(True, alpha=0.3, axis='x')
    plt.tight_layout(); _o = OUTPUT_DIR / f'brecha_por_tipo_{MES}.png'
    plt.savefig(_o, dpi=200, bbox_inches='tight', facecolor='white'); plt.show()
    print(f'Guardado: {_o.name}')

# 7) Evolución mensual de la brecha por tipo
if len(brecha_tipo_mensual):
    fig, ax = plt.subplots(figsize=(13, 6))
    for _t, _g in brecha_tipo_mensual.groupby('tipo'):
        _g = _g.sort_values('mes'); _x = pd.to_datetime(_g['mes'] + '-01')
        ax.plot(_x, _g['brecha_mediana'], marker='o', ms=4, lw=1.8, label=_t)
    ax.set_ylabel('Brecha (%)'); ax.set_title('Evolución mensual de la brecha por tipo')
    ax.legend(fontsize=8, ncol=2); ax.grid(True, alpha=0.3)
    plt.tight_layout(); _o = OUTPUT_DIR / f'brecha_tipo_mensual_{MES}.png'
    plt.savefig(_o, dpi=200, bbox_inches='tight', facecolor='white'); plt.show()
    print(f'Guardado: {_o.name}')"""))

# ── CELL 10 — MAPA COROPLÉTICO de la brecha por provincia ──────────────────────
cells.append(cell_code("""\
# ============================================================
# CELDA 10 — Mapa coroplético de la brecha por provincia
# ============================================================
if not GEOJSON_PATH.exists():
    print(f'GeoJSON no encontrado en {GEOJSON_PATH} — saltear mapa')
else:
    with open(GEOJSON_PATH, 'r', encoding='utf-8') as f:
        geo = _json.load(f)
    NORM_GEO = {'Ciudad de Buenos Aires':'CABA'}
    AJUST = {'Salta':(0,-1),'Tucumán':(0.3,0),'Chaco':(0,-1),'Tierra del Fuego':(-1,-0.2),
             'Santa Fe':(0,1),'Santiago del Estero':(0.7,0)}
    def centroide(coords):
        xs,ys=[],[]
        if isinstance(coords[0][0][0],(int,float)):
            for p in coords[0]: xs.append(p[0]); ys.append(p[1])
        else:
            poly=max(coords,key=lambda p:len(p[0]))
            for p in poly[0]: xs.append(p[0]); ys.append(p[1])
        return sum(xs)/len(xs), sum(ys)/len(ys)
    def draw(ax,coords,color):
        if isinstance(coords[0][0][0],(int,float)):
            ax.fill([c[0] for c in coords[0]],[c[1] for c in coords[0]],facecolor=color,edgecolor='white',linewidth=0.6)
        else:
            for poly in coords:
                ax.fill([c[0] for c in poly[0]],[c[1] for c in poly[0]],facecolor=color,edgecolor='white',linewidth=0.6)
    cmap_m = LinearSegmentedColormap.from_list('c',
        ['#1a9850','#66bd63','#a6d96a','#fee08b','#fdae61','#f46d43','#d73027'], N=256)

    _prov_val = dict(zip(brecha_prov['provincia'], brecha_prov['brecha_mediana']))
    _vals = list(_prov_val.values())
    if _vals:
        norm_c = Normalize(vmin=min(_vals), vmax=max(_vals))
        fig, ax = plt.subplots(figsize=(12, 16)); caba_c = None
        for feat in geo['features']:
            nom = NORM_GEO.get(feat['properties']['name'], feat['properties']['name'])
            val = _prov_val.get(nom)
            col = cmap_m(norm_c(val)) if val is not None else '#dddddd'
            gt, co = feat['geometry']['type'], feat['geometry']['coordinates']
            draw(ax, [co] if gt=='Polygon' else co, col)
            cx, cy = centroide([co] if gt=='Polygon' else co)
            if nom == 'CABA': caba_c=(cx,cy); continue
            dx,dy = AJUST.get(nom,(0,0))
            if val is not None:
                ax.text(cx+dx, cy+dy, f'{nom}\\n{val:+.1f}%', ha='center', va='center', fontsize=7.5,
                        fontweight='bold', bbox=dict(boxstyle='round,pad=0.25', facecolor='white', alpha=0.75, edgecolor='none'))
        if caba_c and 'CABA' in _prov_val:
            vc = _prov_val['CABA']; cc = cmap_m(norm_c(vc)); lx,ly = caba_c[0]+2.2, caba_c[1]+0.8
            ax.annotate('', xy=caba_c, xytext=(lx,ly), arrowprops=dict(arrowstyle='-', color='black', linewidth=1.0))
            ax.text(lx, ly, f'CABA\\n{vc:+.1f}%', ha='center', va='center', fontsize=9, fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.5', facecolor=cc, alpha=0.95, edgecolor='black', linewidth=1.0))
            ax.plot(*caba_c, marker='o', markersize=10, markerfacecolor=cc, markeredgecolor='black', markeredgewidth=1.2, zorder=5)
        ax.set_title('Brecha celíaca por provincia (mediana %)', fontsize=13, fontweight='bold', pad=6)
        ax.set_aspect('equal'); ax.axis('off'); plt.tight_layout()
        _o = OUTPUT_DIR / f'mapa_brecha_{MES}.png'
        plt.savefig(_o, dpi=300, bbox_inches='tight', facecolor='white'); plt.show()
        print(f'Guardado: {_o.name}')"""))

# ── CELL 11 — EXCEL EXPORT ─────────────────────────────────────────────────────
cells.append(cell_code("""\
# ============================================================
# CELDA 11 — Exportación Excel
# ============================================================
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
HDR_FILL = PatternFill(start_color='1F4E79', end_color='1F4E79', fill_type='solid')
HDR_FONT = Font(bold=True, color='FFFFFF', size=10)
HDR_ALIG = Alignment(horizontal='center', wrap_text=True, vertical='center')
def fmt_ws(ws):
    ws.row_dimensions[1].height = 28; ws.freeze_panes = 'A2'
    for cell in ws[1]: cell.fill = HDR_FILL; cell.font = HDR_FONT; cell.alignment = HDR_ALIG
def auto_widths(ws):
    for ci in range(1, ws.max_column+1):
        cl = get_column_letter(ci); hdr = str(ws.cell(1,ci).value or '').lower()
        ws.column_dimensions[cl].width = 30 if any(x in hdr for x in ('provincia','cadena','localidad','tipo','desc','producto','sucursal','nombre')) else 14
        if any(x in hdr for x in ('brecha','base','celiaca','precio','n_','100','tacc','grams')):
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=ci, max_col=ci):
                for cell in row:
                    cell.number_format = ('+0.00"%"' if 'brecha' in hdr else '#,##0.00')

# ── Detalle intra-sucursal por producto (último mes): precio por sucursal×EAN ──
_ult = datos_dia[datos_dia['mes'] == ULTIMO_MES]
_det = (_ult.groupby(['id_comercio','id_bandera','id_sucursal','ean_norm','tipo','rol'])['precio']
        .median().reset_index().rename(columns={'precio':'precio_mediano_mes'}))
_det['descripcion'] = _det['ean_norm'].map(EAN_DESC)
_det['grams'] = _det['ean_norm'].map(EAN_GRAMS)
_det['precio_100g'] = np.where(_det['grams'].notna() & (_det['grams'] > 0),
                               _det['precio_mediano_mes'] / _det['grams'] * 100, np.nan)
_det = _det.merge(suc_geo[['id_comercio','id_bandera','id_sucursal','cadena','PROVINCIA_NORM',
                           'sucursales_localidad','sucursales_nombre']],
                  on=['id_comercio','id_bandera','id_sucursal'], how='left')
_det = _det[['cadena','PROVINCIA_NORM','sucursales_localidad','sucursales_nombre',
             'id_comercio','id_bandera','id_sucursal','tipo','rol','ean_norm','descripcion',
             'grams','precio_mediano_mes','precio_100g']]
_det = _det.sort_values(['PROVINCIA_NORM','cadena','sucursales_nombre','tipo','rol'])

# ── Brecha por SUCURSAL (canasta intra-super) — último mes ────────────────────
_bsm = brecha_suc_mes[brecha_suc_mes['mes'] == ULTIMO_MES].copy()
if len(_bsm):
    _brecha_suc = (_bsm.merge(suc_geo[['id_comercio','id_bandera','id_sucursal','sucursales_nombre']],
                              on=['id_comercio','id_bandera','id_sucursal'], how='left')
                   .rename(columns={'base':'base_mediana','celiaca':'celiaca_mediana','brecha_pct':'brecha_mediana'})
                   [['cadena','PROVINCIA_NORM','localidad','sucursales_nombre','id_comercio','id_bandera',
                     'id_sucursal','base_mediana','celiaca_mediana','n_tipos','brecha_mediana']]
                   .sort_values('brecha_mediana', ascending=False))
else:
    _brecha_suc = pd.DataFrame(columns=['cadena','PROVINCIA_NORM','localidad','sucursales_nombre',
                                        'base_mediana','celiaca_mediana','n_tipos','brecha_mediana'])

out_xls = OUTPUT_DIR / f'brecha_celiaca_{ULTIMO_MES}.xlsx'
with pd.ExcelWriter(out_xls, engine='openpyxl') as writer:
    cobertura_tipo.to_excel(writer, sheet_name='Cobertura', index=False)
    brecha_tipo.to_excel(writer, sheet_name='Brecha_tipo', index=False)
    brecha_tipo_mensual.to_excel(writer, sheet_name='Brecha_tipo_mes', index=False)
    brecha_tipo_prov.to_excel(writer, sheet_name='Brecha_tipo_prov', index=False)
    serie_diaria.to_excel(writer, sheet_name='Serie_diaria', index=False)
    serie_semanal.to_excel(writer, sheet_name='Serie_semanal', index=False)
    serie_mensual.to_excel(writer, sheet_name='Serie_mensual', index=False)
    brecha_prov.to_excel(writer, sheet_name='Brecha_provincia', index=False)
    brecha_cadena.to_excel(writer, sheet_name='Brecha_cadena', index=False)
    concentracion.to_excel(writer, sheet_name='Concentracion', index=False)
    _brecha_suc.to_excel(writer, sheet_name='Brecha_sucursal', index=False)
    _det.to_excel(writer, sheet_name='Detalle_producto', index=False)
    for sn in writer.sheets:
        ws = writer.sheets[sn]; fmt_ws(ws); auto_widths(ws)
print(f'Excel guardado: {out_xls}')
print(f'  Hojas: Cobertura · Brecha_tipo/_mes/_prov · Serie_diaria/semanal/mensual · Brecha_provincia/cadena · Concentracion · Brecha_sucursal · Detalle_producto')
print(f'  Detalle_producto: {len(_det):,} filas (sucursal × EAN, {ULTIMO_MES}) · Brecha_sucursal (intra): {len(_brecha_suc):,}')
print(f'  ⚠️ El número clave está en Brecha_tipo (brecha por tipo en $/100g). La canasta pooled mezcla tipos de brecha muy distinta.')"""))

# ── Write notebook ──────────────────────────────────────────────────────────────
nb = {
    'cells': cells,
    'metadata': {
        'kernelspec': {'display_name':'Python 3','language':'python','name':'python3'},
        'language_info': {'codemirror_mode':{'name':'ipython','version':3},
                          'file_extension':'.py','mimetype':'text/x-python',
                          'name':'python','nbformat':4,'pygments_lexer':'ipython3','version':'3.10.0'}
    },
    'nbformat': 4,
    'nbformat_minor': 5
}
script_dir = os.path.dirname(os.path.abspath(__file__))
out_path = os.path.join(script_dir, '06_evolucion_brecha_celiaca.ipynb')
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
print(f'Written: {out_path}')
print(f'Cells: {len(cells)}')
