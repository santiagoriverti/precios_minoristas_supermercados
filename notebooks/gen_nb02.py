"""Script to generate 02_evolucion_canasta_representativa.ipynb — Multi-canasta version"""
import json, os, hashlib

def _cell_id(prefix, src):
    # id determinista (md5 del contenido) — evita 'drift' espurio al regenerar
    return prefix + hashlib.md5(src.encode('utf-8')).hexdigest()[:6]

def cell_md(src):
    lines = src.split('\n')
    source = [l + '\n' for l in lines[:-1]] + ([lines[-1]] if lines[-1] else [])
    return {'cell_type':'markdown','id':_cell_id('md', src),'metadata':{},'source':source}

def cell_code(src):
    return {'cell_type':'code','execution_count':None,'id':_cell_id('c', src),'metadata':{},'outputs':[],'source':[src]}

cells = []

# ── CELL 0 ─────────────────────────────────────────────────────────────────────
cells.append(cell_md("""# SEPA — Evolución de Canastas Representativas (Multi-canasta)

**Objetivo:** Calcular el costo mensual de hasta 6 canastas definidas por el economista,
mapearlas por provincia, compararlas con el IPC INDEC, y generar rankings por cadena y barrio.

**Canastas:** leídas desde las columnas `cantidad_01`...`cantidad_06` de la hoja `Selección`
del Excel `canasta_representativa_YYYY-MM.xlsx`. Solo se procesan las columnas con al menos
un producto con cantidad > 0.

**Canastas predefinidas:** Vulnerable · Popular · Media · Media Alta · Canasta 05 · Canasta 06

**Estructura:** Config → Setup → Canastas desde Excel → Maestros → ZIPs → Mes actual →
Canasta por sucursal → Análisis provincial → Serie histórica → IPC → Comparativa →
Gráficos IPC → Cuadro por canasta → Mapas coropléticos → Cobertura → Rankings →
Mapas Folium → Rankings CABA → Excel → Desagregación de la variación mensual →
Hoja analisis_detallado (primera del Excel: índices por rubro, región, provincia, cadena y semana)"""))

# ── CELL 1 — CONFIG ────────────────────────────────────────────────────────────
cells.append(cell_code("""\
# ===========================================================
# CONFIGURACIÓN — Modificar solo esta sección
# ===========================================================

SEPA_SOURCE = 'mi_drive'   # 'mi_drive' | 'local'

SEPA_DIR   = '/content/drive/MyDrive/carga'
OUTPUT_DIR = '/content/drive/MyDrive/carga/output_canasta'

USE_CACHE = True

# Período mínimo de la serie histórica
MES_INICIO_HISTORICO = '2024-01'

# Mes base para gráficos de índice (auto-adapta si no está en la serie)
MES_INICIO_GRAFICO = '2024-01'

# Mínimo productos propios para incluir sucursal en análisis
MIN_PRODUCTOS_PROPIOS = 15

# Mínimo sucursales por cadena para aparecer en rankings
MIN_SUCURSALES_RANKING = 10

# Canastas cuya variación mensual se desagrega en el Excel (CELDA 19b: producto, arrastre,
# cadena, provincia, región y tipo de sucursal). Relee del ZIP el mes anterior y el mes en
# curso solo con sus EANs. [] = no se desagrega.
DESAGREGAR_CANASTAS = ['cantidad_03']

# Hoja 'analisis_detallado' (la primera del Excel, CELDA 19c): índices y variaciones mensuales y
# semanales de una canasta por rubro, categoría, región, provincia, cadena y tipo de sucursal.
# La primera corrida lee del SEPA por sucursal los DETALLE_MESES meses viejos de la ventana (~2-2,5 min
# por mes en una PC; más en Colab); después usa el caché del Drive y lee solo el mes nuevo. None = no se arma.
DETALLE_CANASTA = 'cantidad_03'
DETALLE_MESES = 12                 # meses completos en columnas; base = el mes anterior al primero
DETALLE_MIN_SUCURSALES = 10        # mínimo de sucursales para mostrar una región/provincia/cadena/tipo
# Fondo del mapa Folium. 'auto' prueba varios proveedores y se queda con el primero
# que responda desde la red de quien abre el mapa (en la red de INECO, por ejemplo,
# tile.openstreetmap.org no responde). Se puede forzar uno: 'esri' (gris, con nombres
# y limites), 'osm' (OpenStreetMap), 'topo' (OpenTopoMap) o 'carto' (CartoDB Positron:
# sin cuenta devuelve los tiles con la marca de agua "API key required"). Tambien
# acepta una lista con el orden a probar, ej. ['osm', 'esri'].
TILES_MAPA = 'auto'"""))

# ── CELL 2 — SETUP ─────────────────────────────────────────────────────────────
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
                'folium', 'openpyxl', 'tqdm', 'pyarrow', '-q'], check=False)

import zipfile, gzip, re, shutil, warnings, gc, hashlib
import json as _json
from pathlib import Path
from tqdm.auto import tqdm
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.colors as mcolors
import matplotlib.dates as mdates
from matplotlib.colors import LinearSegmentedColormap, Normalize
import seaborn as sns
import folium
from branca.colormap import LinearColormap

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
TMP_DIR = Path('/content/tmp_sepa_nb02')
TMP_DIR.mkdir(exist_ok=True)

_ipc_candidatos = [SEPA_DIR / n for n in ('IPC.xlsx', 'ipc.xlsx', 'IPC.XLSX')]
_ipc_encontrado = next((p for p in _ipc_candidatos if p.exists()), None)
IPC_PATH     = _ipc_encontrado if _ipc_encontrado else SEPA_DIR / 'IPC.xlsx'
GEOJSON_PATH = SEPA_DIR / 'ar.json'

print(f'SEPA_DIR:   {SEPA_DIR}')
print(f'OUTPUT_DIR: {OUTPUT_DIR}')
print(f'  IPC.xlsx: {"OK — " + IPC_PATH.name if IPC_PATH.exists() else "NO ENCONTRADO"}')
print(f'  ar.json:  {"OK" if GEOJSON_PATH.exists() else "NO ENCONTRADO"}')"""))

# ── CELL 3 — MULTI-CANASTA FROM EXCEL ──────────────────────────────────────────
cells.append(cell_code("""\
# ============================================================
# CELDA 3 — Canastas desde Excel (columnas cantidad_01..06)
# ============================================================
import glob as _glob

patrones = sorted(_glob.glob(str(OUTPUT_DIR / 'canasta_representativa_*.xlsx')), reverse=True)
if not patrones:
    raise FileNotFoundError(
        f'No se encontro canasta_representativa_*.xlsx en {OUTPUT_DIR}\\n'
        'Ejecuta primero 01_exploracion_productos.ipynb y completa las columnas cantidad_01..06.'
    )

CANASTA_EXCEL = Path(patrones[0])
print(f'Excel de canasta: {CANASTA_EXCEL.name}')

for _sn in ['Selección', 'Seleccion']:
    try:
        sel = pd.read_excel(CANASTA_EXCEL, sheet_name=_sn, dtype={'id_producto': str})
        break
    except Exception:
        pass
else:
    raise ValueError(f'No se encontró la hoja Seleccion/Selección en {CANASTA_EXCEL.name}')

sel['id_producto'] = sel['id_producto'].str.strip().str.zfill(13)
sel['ean_norm']    = sel['id_producto'].str.lstrip('0')

desc_col = next((c for c in ['descripcion','descripcion_producto','nombre']
                 if c in sel.columns), sel.columns[3])
cat_col  = next((c for c in ['categoria','rubro'] if c in sel.columns), 'categoria')

# ── Nombres, colores y estilos por canasta ───────────────────────────────────
CANT_COLS = ['cantidad_01','cantidad_02','cantidad_03','cantidad_04','cantidad_05','cantidad_06']
CANASTA_NAMES = {
    'cantidad_01': 'Vulnerable',
    'cantidad_02': 'Popular',
    'cantidad_03': 'Media',
    'cantidad_04': 'Media Alta',
    'cantidad_05': 'Celíaca Media',
    'cantidad_06': 'Vegana Básica',
}
CANASTA_SHORT = {
    'cantidad_01': 'vulnerable',
    'cantidad_02': 'popular',
    'cantidad_03': 'media',
    'cantidad_04': 'media_alta',
    'cantidad_05': 'celiaca_media',
    'cantidad_06': 'vegana_basica',
}
CANASTA_COLORS = {
    'cantidad_01': '#0055A4',
    'cantidad_02': '#e74c3c',
    'cantidad_03': '#27ae60',
    'cantidad_04': '#f39c12',
    'cantidad_05': '#9b59b6',
    'cantidad_06': '#1abc9c',
}
CANASTA_LINESTYLES = {
    'cantidad_01': '-',
    'cantidad_02': '--',
    'cantidad_03': '-.',
    'cantidad_04': ':',
    'cantidad_05': (0,(5,1)),
    'cantidad_06': (0,(3,1,1,1)),
}
CANASTA_MARKERS = {
    'cantidad_01': 'o', 'cantidad_02': 's', 'cantidad_03': '^',
    'cantidad_04': 'D', 'cantidad_05': 'v', 'cantidad_06': 'P',
}

# ── Construir CANASTAS (solo las activas) ────────────────────────────────────
CANASTAS = {}
for _col in CANT_COLS:
    if _col not in sel.columns:
        continue
    _qty_s = pd.to_numeric(sel[_col], errors='coerce').fillna(0).astype(int)
    _activos = sel[_qty_s > 0].copy()
    _activos['_qty'] = _qty_s[_qty_s > 0].values
    if len(_activos) == 0:
        continue
    CANASTAS[_col] = {
        row['ean_norm']: (str(row[desc_col])[:50], int(row['_qty']), str(row[cat_col]))
        for _, row in _activos.iterrows()
    }

if not CANASTAS:
    raise ValueError(
        'Ninguna columna cantidad_01..06 tiene productos con cantidad > 0.\\n'
        'Completa al menos una columna cantidad en la hoja Seleccion.'
    )

CANASTAS_ACTIVAS   = list(CANASTAS.keys())
# Rubro SEPA por EAN (Almacén, Frescos, Perfumería, Limpieza, Bebidas, Congelados...): la hoja
# analisis_detallado (CELDA 19c) agrupa las categorías en estos rubros.
RUBRO_EAN = (dict(zip(sel['ean_norm'], sel['rubro'].fillna('Sin rubro').astype(str)))
             if 'rubro' in sel.columns else {})
CANASTA_EANS_NORM  = set().union(*[set(c.keys()) for c in CANASTAS.values()])
CANASTA_EANS_ZFILL = {e.zfill(13) for e in CANASTA_EANS_NORM}
N_EANS_TOTAL       = len(CANASTA_EANS_NORM)
N_CANASTAS         = len(CANASTAS)

# Safeguard MIN_PRODUCTOS_PROPIOS vs tamaño de canasta
_max_n = max(len(c) for c in CANASTAS.values())
if MIN_PRODUCTOS_PROPIOS >= _max_n:
    MIN_PRODUCTOS_PROPIOS = max(1, _max_n // 2)
    print(f'AVISO: MIN_PRODUCTOS_PROPIOS ajustado a {MIN_PRODUCTOS_PROPIOS} (mayor canasta: {_max_n} prods)')

print(f'\\nCanastas activas: {N_CANASTAS}')
for _col in CANASTAS_ACTIVAS:
    _c = CANASTAS[_col]
    _u = sum(v[1] for v in _c.values())
    print(f'  [{CANASTA_NAMES[_col]}] {len(_c)} productos, {_u} unidades/mes')
print(f'EANs únicos (unión): {N_EANS_TOTAL}')"""))

# ── CELL 4 — MAESTROS ──────────────────────────────────────────────────────────
cells.append(cell_code("""\
# ============================================================
# CELDA 4 — Maestros de sucursales, cadenas, provincias
# ============================================================
DATA_URL = 'https://raw.githubusercontent.com/santiagoriverti/precios_minoristas_supermercados/main/data'

def leer_maestro(nombre):
    # Busqueda: ./data (local) -> Drive (SEPA_DIR y SEPA_DIR/data) -> cache -> GitHub raw.
    # El fallback a GitHub SOLO funciona si el repositorio es PUBLICO. Con el repo privado
    # raw.githubusercontent devuelve 404, asi que hay que dejar los maestros en el Drive,
    # junto a los ZIPs del SEPA.
    _cands = [Path('data') / nombre]
    try:
        _cands += [Path(SEPA_DIR) / nombre, Path(SEPA_DIR) / 'data' / nombre]
    except Exception:
        pass
    _cands.append(Path('/content/data') / nombre)
    for _p in _cands:
        if _p.exists():
            return pd.read_excel(_p)
    import urllib.request, urllib.parse
    dl = Path('/content/data') / nombre
    Path('/content/data').mkdir(parents=True, exist_ok=True)
    try:
        print(f'  Descargando {nombre} desde GitHub...')
        urllib.request.urlretrieve(f'{DATA_URL}/{urllib.parse.quote(nombre)}', dl)
    except Exception as _e:
        raise FileNotFoundError(
            f"No se pudo obtener '{nombre}'. Se busco en ./data, el Drive y GitHub ({_e}). "
            f"Si el repositorio es PRIVADO, GitHub responde 404: copia '{nombre}' a la carpeta "
            f"del Drive donde estan los ZIPs del SEPA.")
    return pd.read_excel(dl)

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
print('Maestros OK')"""))

# ── CELL 5 — ZIP FUNCTIONS ─────────────────────────────────────────────────────
cells.append(cell_code("""\
# ============================================================
# CELDA 5 — Funciones de lectura de ZIPs SEPA
# ============================================================
_PAT_SEM = re.compile(r'^(\\d{4})(A|B)$', re.IGNORECASE)
_PAT_ARC = re.compile(r'^(\\d{2})(\\d{4})_pais_parte.*COMPLETO.*\\.csv\\.gz$', re.IGNORECASE)

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

def detectar_ultimo_mes():
    sems = detectar_semestres()
    if not sems:
        raise RuntimeError(f'No hay ZIPs semestrales en {SEPA_DIR}')
    for zip_path, anio, sem in reversed(sems):
        meses = archivos_por_mes(zip_path)
        if meses:
            (a, m) = max(meses.keys())
            return zip_path, a, m, meses[(a, m)]
    raise RuntimeError('No se pudo detectar el ultimo mes')

def normalizar_ean(s):
    if pd.isna(s): return None
    s = str(s).strip().lstrip('0')
    return s if s else '0'

sems = detectar_semestres()
print(f'Semestres encontrados: {len(sems)}')
for z, a, s in sems:
    meses = archivos_por_mes(z)
    meses_str = [f'{m:02d}/{an}' for (an,m) in sorted(meses.keys())]
    print(f'  {a}{s}: {meses_str}')"""))

# ── CELL 6 — CURRENT MONTH ─────────────────────────────────────────────────────
cells.append(cell_code("""\
# ============================================================
# CELDA 6 — Mes actual: carga per-sucursal desde ZIP
# ============================================================
zip_actual, ANIO_ACTUAL, MES_NUM_ACTUAL, archivos_mes = detectar_ultimo_mes()

MES          = f'{MES_NUM_ACTUAL:02d}{ANIO_ACTUAL}'
PERIODO      = f'{ANIO_ACTUAL}-{MES_NUM_ACTUAL:02d}'
ULTIMO_MES   = PERIODO

_NOM = {'01':'enero','02':'febrero','03':'marzo','04':'abril','05':'mayo','06':'junio',
        '07':'julio','08':'agosto','09':'septiembre','10':'octubre','11':'noviembre','12':'diciembre'}
NOMBRE_MES       = f"{_NOM[f'{MES_NUM_ACTUAL:02d}']} {ANIO_ACTUAL}"
NOMBRE_MES_TITLE = NOMBRE_MES.title()

CADENAS_FILTRAR = {'19','2013','3001','4'}
PAT_FECHA = re.compile(r'^precio_(\\d{8})$')

print(f'Procesando: {NOMBRE_MES_TITLE}  ({zip_actual.name})')
print(f'Archivos: {archivos_mes}\\n')

# ── Detección de MES PARCIAL (menos días cargados que los del calendario) ─────
# El último mes en curso (ej. junio al día 23) tiene menos días que el mes
# completo. Su NIVEL es un snapshot válido, pero su VARIACIÓN mensual queda
# subestimada al compararse contra meses completos. Se marca para no confundir.
import calendar as _cal
_dias_cargados = set()
with zipfile.ZipFile(zip_actual) as _zfh:
    for _arch in archivos_mes:
        with _zfh.open(_arch) as _s:
            _hdr0 = gzip.open(_s, 'rt', encoding='utf-8', errors='replace').readline()
        for _c in _hdr0.strip().split(','):
            _mm = PAT_FECHA.match(_c)
            if _mm: _dias_cargados.add(_mm.group(1))
DIAS_CARGADOS  = len(_dias_cargados)
DIAS_MES       = _cal.monthrange(ANIO_ACTUAL, MES_NUM_ACTUAL)[1]
MES_PARCIAL    = 0 < DIAS_CARGADOS < DIAS_MES
SUFIJO_PARCIAL = f' (parcial: {DIAS_CARGADOS}/{DIAS_MES} días)' if MES_PARCIAL else ''
if MES_PARCIAL:
    print(f'⚠️  {NOMBRE_MES_TITLE} es un MES PARCIAL: {DIAS_CARGADOS}/{DIAS_MES} días cargados.')
    print(f'    El NIVEL es un snapshot al día {DIAS_CARGADOS}; la VARIACIÓN mensual está SUBESTIMADA')
    print(f'    (se compara contra meses completos). Re-correr al cierre del mes para el dato definitivo.\\n')

acumulador = []
for archivo in sorted(archivos_mes):
    nombre = Path(archivo).name
    tmp_p  = TMP_DIR / nombre
    with zipfile.ZipFile(zip_actual) as zf:
        with zf.open(archivo) as src, open(tmp_p, 'wb') as dst:
            shutil.copyfileobj(src, dst, length=4*1024*1024)
    print(f'  {nombre}...')
    with gzip.open(tmp_p, 'rt', encoding='utf-8', errors='replace') as g:
        for chunk in pd.read_csv(g, dtype=str, chunksize=300_000, low_memory=False):
            chunk['ean_norm'] = chunk['id_producto'].apply(normalizar_ean)
            chunk = chunk[chunk['ean_norm'].isin(CANASTA_EANS_NORM)].copy()
            if len(chunk) == 0: continue
            for c in ['id_comercio','id_bandera','id_sucursal']:
                chunk[c] = chunk[c].astype(str)
            chunk['_k'] = list(zip(chunk['id_comercio'],chunk['id_bandera'],chunk['id_sucursal']))
            chunk = chunk[chunk['_k'].isin(IDS_PAIS)].drop(columns=['_k']).copy()
            if len(chunk) == 0: continue
            cols_p = [c for c in chunk.columns if PAT_FECHA.match(c)]
            if not cols_p: continue
            df_long = chunk.melt(
                id_vars=['id_comercio','id_bandera','id_sucursal','ean_norm'],
                value_vars=cols_p, var_name='_col', value_name='precio_raw')
            df_long['precio'] = pd.to_numeric(
                df_long['precio_raw'].replace('NA', np.nan), errors='coerce')
            df_long = df_long[df_long['precio'].notna() & (df_long['precio'] > 0)].copy()
            df_long.drop(columns=['_col','precio_raw'], inplace=True)
            acumulador.append(df_long)
    tmp_p.unlink(missing_ok=True)
    del chunk, df_long; gc.collect()

if not acumulador:
    raise RuntimeError('Sin datos de canasta para el mes actual')

datos = pd.concat(acumulador, ignore_index=True)
del acumulador; gc.collect()
# NO se deduplica: se conservan TODAS las observaciones (sucursal x dia) del mes.
# El precio por sucursal (mediana Y promedio sobre los dias) se calcula en CELDA 7.

# ── Promedio con outliers fuera (banda relativa a la mediana) ────────────────
# Para el analisis PROMEDIO: en cada grupo se descartan los valores fuera de
# [mediana/4, mediana x4] (errores gruesos del SEPA: 100x, centavos sueltos) y
# recien despues se promedia. Robusto a cualquier tamano de muestra. Se usa en
# TODAS las agregaciones chicas del analisis promedio (provincias, cadenas,
# barrios). Para el groupby grande (sucursal x EAN sobre dias) se usa una
# version VECTORIZADA equivalente en la CELDA 7 (mismo criterio, mas rapida).
def _pmean(_s):
    _s = pd.to_numeric(_s, errors='coerce').dropna()
    if len(_s) == 0: return float('nan')
    _m = _s.median()
    if _m and _m > 0:
        _f = _s[(_s >= _m/4) & (_s <= _m*4)]
        if len(_f) > 0: _s = _f
    return _s.mean()

ref_e = {'7790072002080'.lstrip('0'), '7790070320285'.lstrip('0'), '7790132098459'.lstrip('0')}
ref_d = datos[datos['ean_norm'].isin(ref_e)]
med_r = ref_d['precio'].median() if len(ref_d) > 0 else datos['precio'].median()
FACTOR = 100 if med_r > 10_000 else 1
if FACTOR == 100:
    datos['precio'] /= 100
    print(f'Factor: {FACTOR} (centavos -> pesos)')
else:
    print(f'Factor: {FACTOR} (ya en pesos)')

_n_suc = datos.groupby(['id_comercio','id_bandera','id_sucursal']).ngroups
print(f'Observaciones (sucursal x dia): {len(datos):,} | Sucursales: {_n_suc:,}')
print(f'EANs únicos con datos: {datos["ean_norm"].nunique()} / {N_EANS_TOTAL} (unión de canastas activas)')"""))

# ── CELL 7 — PER-SUCURSAL BASKETS (multi-canasta) ─────────────────────────────
cells.append(cell_code("""\
# ============================================================
# CELDA 7 — Canasta por sucursal para cada canasta activa
# ============================================================
# Precio por sucursal-EAN agregando sobre TODOS los dias del mes:
#   precio_mediana = mediana de los dias (analisis MEDIANA)
#   precio_prom    = media con outliers fuera [med/4, med x4] (analisis PROMEDIO)
# La limpieza de outliers del promedio es VECTORIZADA (equivalente a _pmean).
_keys = ['id_comercio','id_bandera','id_sucursal','ean_norm']
_med_dia = datos.groupby(_keys)['precio'].transform('median')
_mask_ok = (datos['precio'] >= _med_dia/4) & (datos['precio'] <= _med_dia*4)
_gm = datos.groupby(_keys)['precio'].median().rename('precio_mediana')
_gp = datos[_mask_ok].groupby(_keys)['precio'].mean().rename('precio_prom')
precio_mes = pd.concat([_gm, _gp], axis=1).reset_index()
precio_mes['precio_prom'] = precio_mes['precio_prom'].fillna(precio_mes['precio_mediana'])
precio_mes = precio_mes[~precio_mes['id_comercio'].isin(CADENAS_FILTRAR)].copy()
# Referencias nacionales por EAN para imputar productos faltantes (una por analisis):
precio_med_nac  = precio_mes.groupby('ean_norm')['precio_mediana'].median().to_dict()
precio_prom_nac = precio_mes.groupby('ean_norm')['precio_prom'].agg(_pmean).to_dict()

# ── Provincia por coordenadas: polígonos de ar.json con tolerancia (BUG-44) ──
# Una sucursal cambia de provincia SOLO si sus coordenadas caen a más de RECLASIF_TOL_KM del polígono de su
# provincia declarada y dentro del polígono de otra: errores groseros de carga (DIA de Jujuy declarados San Juan,
# sucursales de Posadas declaradas Mendoza). Cerca de un borde manda la provincia declarada: los polígonos
# simplificados de ar.json no alcanzan para decidir y una ciudad de borde queda a pocos km del lado equivocado.
# Hasta el 2026-10-16 se usaban rectángulos y la primera provincia que contenía el punto: pasaban Neuquén capital a
# La Pampa, Paraná a Santa Fe y San Nicolás a Entre Ríos (121 reclasificadas, la mayoría mal). CABA se trata aparte
# (filtro por rectángulo, abajo). Sin ar.json no se reclasifica nada.
import json as _json
from matplotlib.path import Path as _MPath

RECLASIF_TOL_KM = 100
# id de ar.json (simplemaps: 'AR' + letra del código ISO 3166-2) -> provincia
_GEO_ID_PROV = {'ARB': 'Buenos Aires', 'ARC': 'CABA', 'ARK': 'Catamarca', 'ARH': 'Chaco', 'ARU': 'Chubut',
                'ARX': 'Córdoba', 'ARW': 'Corrientes', 'ARE': 'Entre Ríos', 'ARP': 'Formosa', 'ARY': 'Jujuy',
                'ARL': 'La Pampa', 'ARF': 'La Rioja', 'ARM': 'Mendoza', 'ARN': 'Misiones', 'ARQ': 'Neuquén',
                'ARR': 'Río Negro', 'ARA': 'Salta', 'ARJ': 'San Juan', 'ARD': 'San Luis', 'ARZ': 'Santa Cruz',
                'ARS': 'Santa Fe', 'ARG': 'Santiago del Estero', 'ARV': 'Tierra del Fuego', 'ART': 'Tucumán'}

def _poligonos_provincias(_ruta):
    # provincia -> lista de polígonos; cada polígono, lista de anillos [lon, lat] (el primero es el exterior)
    with open(_ruta, 'r', encoding='utf-8') as _f:
        _g = _json.load(_f)
    _pol = {}
    for _ft in _g['features']:
        _prov = _GEO_ID_PROV.get(_ft['properties'].get('id'))
        if _prov is None:
            continue
        _geo = _ft['geometry']
        _ps = _geo['coordinates'] if _geo['type'] == 'MultiPolygon' else [_geo['coordinates']]
        _pol.setdefault(_prov, []).extend([[np.asarray(_r, dtype=float) for _r in _p] for _p in _ps])
    return _pol

def _dentro_poligono(_pols, _lon, _lat):
    # True si el punto está dentro de alguno de los polígonos (y fuera de sus agujeros)
    _pts = np.column_stack([_lon, _lat])
    _res = np.zeros(len(_pts), bool)
    for _p in _pols:
        _en = _MPath(_p[0]).contains_points(_pts)
        for _h in _p[1:]:
            _en &= ~_MPath(_h).contains_points(_pts)
        _res |= _en
    return _res

def _km_al_poligono(_pols, _lon, _lat):
    # Distancia (km) de cada punto al borde más cercano de los polígonos (proyección equirectangular local)
    _segs = np.concatenate([np.column_stack([_r[:-1], _r[1:]]) for _p in _pols for _r in _p])
    _out = np.empty(len(_lon))
    for _i, (_x, _y) in enumerate(zip(_lon, _lat)):
        _kx = 111.32 * np.cos(np.radians(_y))
        _x1, _y1 = (_segs[:, 0] - _x) * _kx, (_segs[:, 1] - _y) * 110.57
        _x2, _y2 = (_segs[:, 2] - _x) * _kx, (_segs[:, 3] - _y) * 110.57
        _dx, _dy = _x2 - _x1, _y2 - _y1
        _t = np.clip(-(_x1 * _dx + _y1 * _dy) / np.maximum(_dx * _dx + _dy * _dy, 1e-12), 0, 1)
        _out[_i] = np.sqrt((_x1 + _t * _dx) ** 2 + (_y1 + _t * _dy) ** 2).min()
    return _out

# ── Pre-limpiar geografía (ONCE para todas las canastas) ─────────────────────
_cols_suc = ['id_comercio','id_bandera','id_sucursal',
             'sucursales_nombre','sucursales_latitud','sucursales_longitud',
             'sucursales_barrio','sucursales_localidad','PROVINCIA']
if 'sucursales_tipo' in suc_pais.columns:
    _cols_suc.append('sucursales_tipo')

suc_geo_clean = suc_pais[_cols_suc].copy()
if 'sucursales_tipo' not in suc_geo_clean.columns:
    suc_geo_clean['sucursales_tipo'] = 'N/D'
suc_geo_clean['cadena'] = suc_geo_clean.apply(asignar_cadena, axis=1)
suc_geo_clean['PROVINCIA_NORM'] = suc_geo_clean['PROVINCIA'].map(PROV_NORM).fillna(suc_geo_clean['PROVINCIA'])
suc_geo_clean = suc_geo_clean[suc_geo_clean['sucursales_tipo'] != 'Web'].copy()
_mask_caba = (
    suc_geo_clean['PROVINCIA_NORM'].eq('CABA') & (
        (suc_geo_clean['sucursales_latitud'] < -34.71) |
        (suc_geo_clean['sucursales_latitud'] > -34.53) |
        (suc_geo_clean['sucursales_longitud'] < -58.53) |
        (suc_geo_clean['sucursales_longitud'] > -58.34)))
suc_geo_clean = suc_geo_clean[~_mask_caba].copy()

_POL_PROV = _poligonos_provincias(GEOJSON_PATH) if GEOJSON_PATH.exists() else {}
if not _POL_PROV:
    print(f'  AVISO: no está {GEOJSON_PATH.name}: no se reclasifica la provincia de ninguna sucursal')
_lon = suc_geo_clean['sucursales_longitud'].to_numpy(dtype=float)
_lat = suc_geo_clean['sucursales_latitud'].to_numpy(dtype=float)
_decl = suc_geo_clean['PROVINCIA_NORM'].to_numpy(dtype=object)
_dentro_de = {_p: _dentro_poligono(_pl, _lon, _lat) for _p, _pl in _POL_PROV.items()}
_nueva = _decl.copy()
for _p in sorted((set(_decl) & set(_POL_PROV)) - {'CABA'}):
    _idx = np.where((_decl == _p) & ~_dentro_de[_p])[0]
    if len(_idx) == 0:
        continue
    _lejos = _idx[_km_al_poligono(_POL_PROV[_p], _lon[_idx], _lat[_idx]) > RECLASIF_TOL_KM]
    for _i in _lejos:
        _q = next((_o for _o in _POL_PROV if _o != _p and _dentro_de[_o][_i]), None)
        if _q is not None:
            _nueva[_i] = _q
_cambio = _nueva != _decl
suc_geo_clean['PROVINCIA_NORM'] = _nueva
if _cambio.any():
    _det = pd.Series([f'{_a} -> {_b}' for _a, _b in zip(_decl[_cambio], _nueva[_cambio])]).value_counts()
    print(f'  Reclasificadas {int(_cambio.sum())} sucursales por coordenadas (a más de {RECLASIF_TOL_KM} km de su '
          f'provincia declarada): ' + ', '.join(f'{_k} ({_v})' for _k, _v in _det.items()))

# ── AMBA por coordenadas (rankings de cadenas AMBA, CELDAS 16 y 20) ──────────
# AMBA = CABA + sucursales de Buenos Aires a <= AMBA_RADIO_KM del Obelisco. NO es toda la
# provincia (asi entraban Toledo de Mar del Plata y la Cooperativa Obrera de Bahia Blanca) ni la
# REGION del maestro, que marca AMBA a ~100 sucursales de DIA del interior bonaerense (localidad
# 'BUENOS AIRES': Mar del Plata, Tandil, Pergamino). 90 km toma La Plata (55), Lujan (67),
# Campana (72) y Zarate (81) y deja afuera Lobos, Navarro, Mercedes y Chascomus (92-114 km).
AMBA_RADIO_KM = 90
_OBELISCO = (-34.6037, -58.3816)

def _km_obelisco(lat, lon):
    _la, _lo = np.radians(lat), np.radians(lon)
    _la0, _lo0 = np.radians(_OBELISCO[0]), np.radians(_OBELISCO[1])
    _a = np.sin((_la - _la0) / 2) ** 2 + np.cos(_la0) * np.cos(_la) * np.sin((_lo - _lo0) / 2) ** 2
    return 2 * 6371 * np.arcsin(np.sqrt(_a))

suc_geo_clean['amba'] = (suc_geo_clean['PROVINCIA_NORM'].eq('CABA') |
                         (suc_geo_clean['PROVINCIA_NORM'].eq('Buenos Aires') &
                          (_km_obelisco(suc_geo_clean['sucursales_latitud'],
                                        suc_geo_clean['sucursales_longitud']) <= AMBA_RADIO_KM)))
print(f'  AMBA (CABA + Buenos Aires a <= {AMBA_RADIO_KM} km del Obelisco): '
      f'{int(suc_geo_clean["amba"].sum()):,} sucursales')

# ── Calcular canasta por sucursal para CADA canasta activa ───────────────────
canasta_geo_dict = {}

for _col_id, _canasta in CANASTAS.items():
    _name    = CANASTA_NAMES[_col_id]
    _min_p   = min(MIN_PRODUCTOS_PROPIOS, len(_canasta))

    # Cada sucursal aporta DOS costos de canasta: uno con precios medianos
    # (canasta_total) y otro con precios promedio-sin-outliers (canasta_total_prom).
    # Productos faltantes se imputan con la referencia nacional del mismo analisis.
    def _calc(grupo, _c=_canasta, _pm=precio_med_nac, _pp=precio_prom_nac):
        loc_m = dict(zip(grupo['ean_norm'], grupo['precio_mediana']))
        loc_p = dict(zip(grupo['ean_norm'], grupo['precio_prom']))
        tot_m = 0.0; tot_p = 0.0; propios = 0
        for ean, (nom, qty, cat) in _c.items():
            if ean in loc_m:
                prm = loc_m[ean]; prp = loc_p[ean]; propios += 1
            else:
                prm = _pm.get(ean, 0); prp = _pp.get(ean, 0)
            tot_m += prm * qty; tot_p += prp * qty
        return pd.Series({'canasta_total': tot_m, 'canasta_total_prom': tot_p,
                          'productos_propios': propios})

    _suc = (precio_mes.groupby(['id_comercio','id_bandera','id_sucursal'])
            .apply(_calc, include_groups=False).reset_index())
    _suc = _suc[_suc['productos_propios'] >= _min_p].copy()
    _cgeo = _suc.merge(suc_geo_clean, on=['id_comercio','id_bandera','id_sucursal'], how='inner')
    canasta_geo_dict[_col_id] = _cgeo.copy()
    print(f'  [{_name}] {len(_cgeo):,} sucursales | '
          f'mediana ${_cgeo["canasta_total"].min():,.0f}–${_cgeo["canasta_total"].max():,.0f}')

print()
print('Cadenas (primera canasta activa):')
print(canasta_geo_dict[CANASTAS_ACTIVAS[0]]['cadena'].value_counts().to_string())"""))

# ── CELL 8 — PROVINCE ANALYSIS (multi-canasta) ────────────────────────────────
cells.append(cell_code("""\
# ============================================================
# CELDA 8 — Análisis provincial para cada canasta activa
# ============================================================
def fmt_ar(x, dec=0):
    s = f'{x:,.{dec}f}'
    return s.replace(',','X').replace('.',',').replace('X','.')

serie_prov_dict     = {}   # col_id -> provincia: canasta_total (mediana) + canasta_total_prom (promedio)
prom_nac_dict       = {}   # col_id -> nacional ponderado por poblacion — MEDIANA
prom_nac_prom_dict  = {}   # col_id -> nacional ponderado por poblacion — PROMEDIO (outliers fuera)

for _col_id in CANASTAS_ACTIVAS:
    _cgf  = canasta_geo_dict[_col_id]
    # MEDIANA : mediana provincial de las canastas medianas por sucursal.
    # PROMEDIO: media provincial (outliers fuera, _pmean) de las canastas promedio por sucursal.
    _cpp  = (_cgf.groupby('PROVINCIA_NORM')
             .agg(canasta_total=('canasta_total','median'),
                  canasta_total_prom=('canasta_total_prom', _pmean)).reset_index()
             .rename(columns={'PROVINCIA_NORM':'provincia'}))
    _cpp['mes']  = PERIODO
    _cpp['peso'] = _cpp['provincia'].map(PESOS_POBLACION).fillna(0)
    _pob = _cpp[_cpp['peso'] > 0]['peso'].sum()
    _prom      = ((_cpp['canasta_total'] * _cpp['peso']).sum() / _pob
                  if _pob > 0 else _cpp['canasta_total'].mean())
    _prom_prom = ((_cpp['canasta_total_prom'] * _cpp['peso']).sum() / _pob
                  if _pob > 0 else _cpp['canasta_total_prom'].mean())
    serie_prov_dict[_col_id]    = _cpp[['mes','provincia','canasta_total','canasta_total_prom']].copy()
    prom_nac_dict[_col_id]      = _prom
    prom_nac_prom_dict[_col_id] = _prom_prom

print(f'=== CUADRO: Canastas por provincia — {NOMBRE_MES_TITLE} ===')
for _col_id in CANASTAS_ACTIVAS:
    _name = CANASTA_NAMES[_col_id]
    _spv  = serie_prov_dict[_col_id].sort_values('canasta_total')
    _prom = prom_nac_dict[_col_id]
    print(f'\\n  ── {_name} ──')
    for _, r in _spv.iterrows():
        _vs = ((r['canasta_total'] / _prom) - 1) * 100
        print(f'  {r["provincia"]:<25} ${r["canasta_total"]:>10,.0f}  {_vs:+.2f}%')
    print(f'  {"Promedio (ponderado)":<25} ${_prom:>10,.0f}   0.00%')
print(f'\\nProvincias con datos (primera canasta): {len(serie_prov_dict[CANASTAS_ACTIVAS[0]])}')"""))

# ── CELL 9 — HISTORICAL SERIES (one raw cache, per-canasta aggregation) ───────
cells.append(cell_code("""\
# ============================================================
# CELDA 9 — Serie histórica (cache de meses cerrados + mes en curso fresco)
# ============================================================
# Cache identificado por la unión de EANs activos (cambiar cantidades reusa;
# agregar/quitar EANs invalida). IMPORTANTE: el cache guarda SOLO meses
# CERRADOS. El último mes disponible (en curso, crece día a día) se RELEE
# SIEMPRE fresco, así sus promedios usan los días efectivamente cargados.
_cache_key  = hashlib.md5('|'.join(sorted(CANASTA_EANS_NORM)).encode()).hexdigest()[:8]
# _v2m: esquema con precio_medio (media recortada 1%) ademas de precio_mediano.
# Al cambiar el nombre, la primera corrida reconstruye el cache con ambas medidas
# (los .parquet viejos sin precio_medio quedan huerfanos; se pueden borrar).
_cache_path = CACHE_DIR / f'hist_union_{_cache_key}_v2m.parquet'

# Mapa de meses disponibles -> (zip, archivos del mes)
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

def _leer_mes_hist(_lbl):
    # Lee los archivos del mes _lbl, filtra a los EANs de las canastas y
    # devuelve [ean_norm, precio_mediano, anio_mes] (mediana sobre todos los
    # días cargados de ese mes). Devuelve None si no hay datos.
    _zip_path, _archs = _mapa_mes[_lbl]
    _all_rows = []
    for _archivo in sorted(_archs):
        _tmp_p = TMP_DIR / Path(_archivo).name
        with zipfile.ZipFile(_zip_path) as _zf:
            with _zf.open(_archivo) as _s, open(_tmp_p,'wb') as _d:
                shutil.copyfileobj(_s, _d, length=4*1024*1024)
        with gzip.open(_tmp_p,'rt',encoding='utf-8',errors='replace') as _g:
            for _chunk in pd.read_csv(_g, dtype=str, chunksize=300_000, low_memory=False):
                _chunk['ean_norm'] = _chunk['id_producto'].apply(normalizar_ean)
                _chunk = _chunk[_chunk['ean_norm'].isin(CANASTA_EANS_NORM)].copy()
                if len(_chunk) == 0: continue
                _cols_p = [c for c in _chunk.columns if re.match(r'^precio_\\d{8}$', c)]
                if not _cols_p: continue
                _sub = _chunk[['ean_norm']+_cols_p].copy()
                for _cp in _cols_p:
                    _sub[_cp] = pd.to_numeric(_sub[_cp].replace('NA',np.nan), errors='coerce')
                _mlt = _sub.melt(id_vars='ean_norm', value_vars=_cols_p,
                                 var_name='_c', value_name='precio')
                _mlt = _mlt[_mlt['precio'].notna() & (_mlt['precio']>0)]
                _all_rows.append(_mlt[['ean_norm','precio']])
        _tmp_p.unlink(missing_ok=True)
    if not _all_rows:
        return None
    _df_m = pd.concat(_all_rows, ignore_index=True)
    _fac = 100 if _df_m['precio'].median() > 10_000 else 1
    if _fac == 100: _df_m['precio'] /= 100
    _agg = (_df_m.groupby('ean_norm')['precio']
            .agg(precio_mediano='median', precio_medio=_pmean).reset_index())
    _agg['anio_mes'] = _lbl
    del _df_m, _all_rows; gc.collect()
    return _agg

# ── 1) Meses CERRADOS (todos menos el último): usar/actualizar cache ──────────
if USE_CACHE and _cache_path.exists():
    df_cache = pd.read_parquet(_cache_path)
    df_cache = df_cache[df_cache['anio_mes'] < _mes_actual].copy()
else:
    df_cache = pd.DataFrame(columns=['ean_norm','precio_mediano','precio_medio','anio_mes'])

_meses_en_cache = set(df_cache['anio_mes'].unique())
_faltantes = [m for m in _meses_disp if m < _mes_actual and m not in _meses_en_cache]
_nuevos = []
for _lbl in _faltantes:
    _agg = _leer_mes_hist(_lbl)
    if _agg is not None:
        _nuevos.append(_agg)
        print(f'  {_lbl}: {_agg["ean_norm"].nunique()} EANs (agregado al cache)')
if _nuevos:
    df_cache = pd.concat([df_cache] + _nuevos, ignore_index=True)
    if USE_CACHE:
        df_cache.to_parquet(_cache_path, compression='snappy', index=False)
        print(f'Cache actualizado: {_cache_path.name} ({df_cache["anio_mes"].nunique()} meses cerrados)')
elif USE_CACHE and _cache_path.exists():
    print(f'Cache al día: {_cache_path.name} ({len(_meses_en_cache)} meses cerrados)')

# ── 2) Mes en curso: SIEMPRE fresco (usa los días cargados a la fecha) ────────
_actual = _leer_mes_hist(_mes_actual)
if _actual is not None:
    print(f'  {_mes_actual}: {_actual["ean_norm"].nunique()} EANs (mes en curso — recalculado fresco)')

df_hist_raw = (pd.concat([df_cache] + ([_actual] if _actual is not None else []),
                         ignore_index=True)
               if (len(df_cache) > 0 or _actual is not None)
               else pd.DataFrame(columns=['ean_norm','precio_mediano','precio_medio','anio_mes']))
df_hist_raw = df_hist_raw.sort_values('anio_mes').reset_index(drop=True)

# ── Agregar por canasta ──────────────────────────────────────────────────────
serie_nac_dict = {}   # col_id -> serie_nacional_valida

for _col_id, _canasta in CANASTAS.items():
    _name  = CANASTA_NAMES[_col_id]
    _eans  = set(_canasta.keys())
    _dh    = df_hist_raw[df_hist_raw['ean_norm'].isin(_eans)].copy()
    _dh['qty']              = _dh['ean_norm'].map(lambda e, c=_canasta: c.get(e,('?',0,'?'))[1])
    _dh['costo_item']      = _dh['precio_mediano'] * _dh['qty']
    _dh['costo_item_prom'] = _dh['precio_medio']   * _dh['qty']
    _sn = (_dh.groupby('anio_mes')
           .agg(canasta_nacional_ponderada=('costo_item','sum'),
                canasta_nacional_ponderada_prom=('costo_item_prom','sum'),
                n_eans=('ean_norm','nunique'))
           .reset_index().rename(columns={'anio_mes':'mes'})
           .sort_values('mes').reset_index(drop=True))
    _sn = _sn[_sn['mes'] >= MES_INICIO_HISTORICO].copy()
    _sn['variacion_mensual_%']      = _sn['canasta_nacional_ponderada'].pct_change() * 100
    _sn['variacion_mensual_prom_%'] = _sn['canasta_nacional_ponderada_prom'].pct_change() * 100
    _bv = _sn['canasta_nacional_ponderada'].iloc[0] if len(_sn) > 0 else 1
    _sn['indice_canasta_base100'] = (_sn['canasta_nacional_ponderada'] / _bv * 100).round(2)
    serie_nac_dict[_col_id] = _sn.copy()
    _rng = f'{_sn["mes"].min()} -> {_sn["mes"].max()}' if len(_sn) > 0 else 'sin datos'
    print(f'  [{_name}] {len(_sn)} meses | {_rng}')"""))

# ── CELL 10 — IPC ──────────────────────────────────────────────────────────────
cells.append(cell_code("""\
# ============================================================
# CELDA 10 — IPC INDEC desde carga/IPC.xlsx
# ============================================================
if not IPC_PATH.exists():
    raise FileNotFoundError(
        f'IPC.xlsx no encontrado en {SEPA_DIR}\\n'
        'Asegurate de tener el archivo IPC.xlsx en la carpeta carga/'
    )

ipc_raw = pd.read_excel(IPC_PATH)
print(f'IPC cargado: {len(ipc_raw)} filas, columnas: {list(ipc_raw.columns[:4])} ...')

fecha_col = next((c for c in ipc_raw.columns
                  if str(c).lower().strip() in ('date','fecha','mes','period')),
                 ipc_raw.columns[0])

if pd.api.types.is_datetime64_any_dtype(ipc_raw[fecha_col]):
    ipc_raw['mes'] = ipc_raw[fecha_col].dt.strftime('%Y-%m')
else:
    _MES_ESP = {'ene':1,'feb':2,'mar':3,'abr':4,'may':5,'jun':6,
                'jul':7,'ago':8,'sep':9,'oct':10,'nov':11,'dic':12}
    def _parse_ipc_fecha(val):
        if pd.isna(val): return pd.NaT
        if isinstance(val, pd.Timestamp): return val
        s = str(val).strip().lower()
        try:
            partes = s.split('-')
            if len(partes) == 2 and partes[0] in _MES_ESP:
                return pd.Timestamp(year=int(partes[1]), month=_MES_ESP[partes[0]], day=1)
        except Exception:
            pass
        return pd.to_datetime(val, errors='coerce')
    ipc_raw['mes'] = ipc_raw[fecha_col].apply(_parse_ipc_fecha).dt.strftime('%Y-%m')

rename_map = {}
for c in ipc_raw.columns:
    cs = str(c).strip()
    if 'nivel general' in cs.lower():               rename_map[c] = 'ipc_general'
    elif 'alimentos y bebidas no alc' in cs.lower(): rename_map[c] = 'ipc_alimentos'
ipc_raw = ipc_raw.rename(columns=rename_map)

for c in ['ipc_general','ipc_alimentos']:
    if c in ipc_raw.columns:
        ipc_raw[c] = pd.to_numeric(
            ipc_raw[c].astype(str).str.replace(',', '.', regex=False), errors='coerce')

_ipc_cols = ['mes','ipc_general'] + (['ipc_alimentos'] if 'ipc_alimentos' in ipc_raw.columns else [])
ipc = (ipc_raw[_ipc_cols]
       .dropna(subset=['ipc_general']).sort_values('mes').reset_index(drop=True))
if 'ipc_alimentos' not in ipc.columns:
    ipc['ipc_alimentos'] = np.nan
ipc['ipc_general_var_%']   = ipc['ipc_general'].pct_change(fill_method=None) * 100
ipc['ipc_alimentos_var_%'] = ipc['ipc_alimentos'].pct_change(fill_method=None) * 100

print(f'IPC procesado: {len(ipc)} meses | {ipc["mes"].min()} -> {ipc["mes"].max()}')
print(ipc[['mes','ipc_general','ipc_general_var_%','ipc_alimentos','ipc_alimentos_var_%']].tail(6).to_string(index=False))"""))

# ── CELL 11 — COMPARATIVA (multi-canasta) ─────────────────────────────────────
cells.append(cell_code("""\
# ============================================================
# CELDA 11 — Comparativa SEPA vs IPC para cada canasta
# ============================================================
comparativa_dict  = {}   # col_id -> comparativa DataFrame
df_g_dict         = {}   # col_id -> df_g (desde MES_INICIO_GRAFICO)
_lbl_base_dict    = {}   # col_id -> label base ej '03-24'
_serie_vacia_dict = {}   # col_id -> bool

for _col_id in CANASTAS_ACTIVAS:
    _sn   = serie_nac_dict[_col_id]
    _name = CANASTA_NAMES[_col_id]

    if len(_sn) == 0:
        print(f'AVISO [{_name}]: Serie histórica vacía — gráficos de índices no disponibles.')
        _serie_vacia_dict[_col_id] = True
        comparativa_dict[_col_id]  = pd.DataFrame()
        df_g_dict[_col_id]         = pd.DataFrame()
        _lbl_base_dict[_col_id]    = PERIODO[5:7] + '-' + PERIODO[2:4]
        continue

    _comp = _sn.merge(
        ipc[['mes','ipc_general','ipc_general_var_%','ipc_alimentos','ipc_alimentos_var_%']],
        on='mes', how='left')
    _ipc_b = _comp['ipc_general'].dropna().iloc[0] if _comp['ipc_general'].notna().any() else 1
    _ialb  = _comp['ipc_alimentos'].dropna().iloc[0] if _comp['ipc_alimentos'].notna().any() else 1
    _comp['indice_ipc_general_base100']   = (_comp['ipc_general']   / _ipc_b * 100).round(2)
    _comp['indice_ipc_alimentos_base100'] = (_comp['ipc_alimentos'] / _ialb  * 100).round(2)

    _mg = MES_INICIO_GRAFICO
    if _mg not in _comp['mes'].values:
        _mg = _comp['mes'].min()
    _dg = _comp[_comp['mes'] >= _mg].copy().reset_index(drop=True)
    _bg  = _dg['canasta_nacional_ponderada'].iloc[0]
    _bgp = _dg['canasta_nacional_ponderada_prom'].iloc[0]
    _big = _dg['ipc_general'].dropna().iloc[0] if _dg['ipc_general'].notna().any() else 1
    _bia = _dg['ipc_alimentos'].dropna().iloc[0] if _dg['ipc_alimentos'].notna().any() else 1
    _lbl = _mg[5:7] + '-' + _mg[2:4]
    _dg['idx_canasta_base']       = (_dg['canasta_nacional_ponderada']      / _bg  * 100).round(2)
    _dg['idx_canasta_base_prom']  = (_dg['canasta_nacional_ponderada_prom'] / _bgp * 100).round(2)
    _dg['idx_ipc_general_base']   = (_dg['ipc_general']                / _big * 100).round(2)
    _dg['idx_ipc_alimentos_base'] = (_dg['ipc_alimentos']              / _bia * 100).round(2)
    _dg['fecha'] = pd.to_datetime(_dg['mes'] + '-01')

    comparativa_dict[_col_id]  = _comp
    df_g_dict[_col_id]         = _dg
    _lbl_base_dict[_col_id]    = _lbl
    _serie_vacia_dict[_col_id] = False

    print(f'  [{_name}] {len(_comp)} meses | desde {_mg} ({len(_dg)} pts) | '
          f'último: ${_dg["canasta_nacional_ponderada"].iloc[-1]:,.0f} '
          f'({_dg["variacion_mensual_%"].iloc[-1]:+.1f}%)')"""))

# ── CELL 12 — CHARTS (multi-canasta) ──────────────────────────────────────────
cells.append(cell_code("""\
# ============================================================
# CELDA 12 — Gráficos: índices y variaciones (MEDIANA y PROMEDIO, por duplicado)
# ============================================================
# Cada gráfico se genera DOS veces: análisis MEDIANA (archivos sin sufijo) y
# análisis PROMEDIO (sufijo _prom, precios con outliers fuera).
COLOR_IPC_GEN = '#D62728'
COLOR_IPC_ALI = '#FF7F0E'

_MESES_ES = {1:'ene',2:'feb',3:'mar',4:'abr',5:'may',6:'jun',
             7:'jul',8:'ago',9:'sep',10:'oct',11:'nov',12:'dic'}
def _fmt_mes_es(x, pos):
    try:
        ts = mdates.num2date(x)
        return f'{_MESES_ES[ts.month]}-{str(ts.year)[2:]}'
    except Exception:
        return ''

_activas_con_datos = [c for c in CANASTAS_ACTIVAS if not _serie_vacia_dict[c] and len(df_g_dict[c]) > 0]
if not _activas_con_datos:
    print('AVISO: Sin serie histórica para ninguna canasta. Saltando gráficos de índices.')
else:
    # Canasta de referencia del eje temporal y de las series de IPC: la que arranca
    # ANTES (y a igual arranque, la mas larga). Tomar la primera de la lista dejaba el
    # eje corto si esa canasta tenia menos historia que el resto (BUG-29).
    _cid_ref  = min(_activas_con_datos,
                    key=lambda c: (df_g_dict[c]['fecha'].iloc[0], -len(df_g_dict[c])))
    _lbl_base = _lbl_base_dict[_cid_ref]
    _dg0      = df_g_dict[_cid_ref]
    # Una canasta que arranca despues tiene su indice en base a SU primer mes: se
    # aclara en la leyenda para no leerla como comparable con las demas.
    _lbl_can = {c: (f'ICR {CANASTA_NAMES[c]}' if _lbl_base_dict[c] == _lbl_base
                    else f'ICR {CANASTA_NAMES[c]} (base {_lbl_base_dict[c]})')
                for c in _activas_con_datos}
    # (sufijo_archivo, titulo, col_indice_canasta, col_variacion, dict_prom_nacional)
    _MEDIDAS_G = [
        ('',      'mediana',  'idx_canasta_base',      'variacion_mensual_%',      prom_nac_dict),
        ('_prom', 'promedio', 'idx_canasta_base_prom', 'variacion_mensual_prom_%', prom_nac_prom_dict),
    ]
    for _SFX, _TIT, _IDXCOL, _VARCOL, _PROMD in _MEDIDAS_G:

        # ── GRAFICO 1: Índices base ─────────────────────────────────────────────
        fig1, ax1 = plt.subplots(figsize=(13, 6))
        for _col_id in _activas_con_datos:
            _dg   = df_g_dict[_col_id]
            _name = CANASTA_NAMES[_col_id]
            ax1.plot(_dg['fecha'], _dg[_IDXCOL],
                     color=CANASTA_COLORS[_col_id], linewidth=2.5,
                     linestyle=CANASTA_LINESTYLES[_col_id],
                     marker=CANASTA_MARKERS[_col_id], markersize=5,
                     label=_lbl_can[_col_id])
            _dgv = _dg.dropna(subset=[_IDXCOL])
            if len(_dgv):
                _ult = _dgv.iloc[-1]
                ax1.annotate(f"{_ult[_IDXCOL]:.0f}",
                             xy=(_ult['fecha'], _ult[_IDXCOL]),
                             xytext=(8, 0), textcoords='offset points',
                             color=CANASTA_COLORS[_col_id], fontweight='bold', fontsize=9)
        if _dg0['idx_ipc_general_base'].notna().any():
            ax1.plot(_dg0['fecha'], _dg0['idx_ipc_general_base'],
                     color=COLOR_IPC_GEN, linewidth=1.8, linestyle='--', marker='s', markersize=4,
                     label='IPC INDEC - Nivel general')
            _iu = _dg0.dropna(subset=['idx_ipc_general_base']).iloc[-1]
            ax1.annotate(f"{_iu['idx_ipc_general_base']:.0f}",
                         xy=(_iu['fecha'], _iu['idx_ipc_general_base']),
                         xytext=(8,-3), textcoords='offset points',
                         color=COLOR_IPC_GEN, fontweight='bold', fontsize=9)
        if _dg0['idx_ipc_alimentos_base'].notna().any():
            ax1.plot(_dg0['fecha'], _dg0['idx_ipc_alimentos_base'],
                     color=COLOR_IPC_ALI, linewidth=1.8, linestyle=':', marker='^', markersize=4,
                     label='IPC INDEC - Alimentos y bebidas')
            _ia = _dg0.dropna(subset=['idx_ipc_alimentos_base']).iloc[-1]
            ax1.annotate(f"{_ia['idx_ipc_alimentos_base']:.0f}",
                         xy=(_ia['fecha'], _ia['idx_ipc_alimentos_base']),
                         xytext=(8,3), textcoords='offset points',
                         color=COLOR_IPC_ALI, fontweight='bold', fontsize=9)
        ax1.set_ylabel(f'Índice ({_lbl_base} = 100)', fontsize=11)
        ax1.legend(loc='upper left', fontsize=9, framealpha=0.95)
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
        ax1.xaxis.set_major_formatter(mticker.FuncFormatter(_fmt_mes_es))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
        _t1 = f'Índices de canastas vs IPC — análisis {_TIT}'
        if MES_PARCIAL:
            _t1 += f'  ·  {NOMBRE_MES_TITLE} PARCIAL {DIAS_CARGADOS}/{DIAS_MES} días (preliminar)'
        ax1.set_title(_t1, fontsize=10, color=('#C00000' if MES_PARCIAL else '#333'),
                      style=('italic' if MES_PARCIAL else 'normal'), pad=8)
        plt.tight_layout()
        out1 = OUTPUT_DIR / f'indices_canasta_vs_ipc_{MES}{_SFX}.png'
        plt.savefig(out1, dpi=600, bbox_inches='tight', facecolor='white')
        plt.show()
        print(f'Gráfico 1 [{_TIT}] guardado: {out1}')

        # ── GRAFICO 2: Variaciones mensuales (barras agrupadas) ─────────────────
        # Cada serie lleva SU propio eje de fechas: si una canasta arranca despues que
        # las demas, usar el eje de la de referencia rompe el grafico (BUG-29).
        _series_bar = (
            [(CANASTA_COLORS[c], f'ICR {CANASTA_NAMES[c]}',
              df_g_dict[c]['fecha'], df_g_dict[c][_VARCOL]) for c in _activas_con_datos] +
            [(COLOR_IPC_GEN, 'IPC INDEC - Nivel general',
              _dg0['fecha'], _dg0['ipc_general_var_%']),
             (COLOR_IPC_ALI, 'IPC INDEC - Alimentos y bebidas',
              _dg0['fecha'], _dg0['ipc_alimentos_var_%'])]
        )
        _n_b    = len(_series_bar)
        _fig_w  = max(20, _n_b * 2 + 10)
        _bw2    = pd.Timedelta(days=max(3, int(22 / max(_n_b, 1))))
        _offs2  = [(_i - (_n_b - 1) / 2) * _bw2 for _i in range(_n_b)]
        _tick_i = 2 if _n_b > 5 else 1
        fig2, ax2 = plt.subplots(figsize=(_fig_w, 8))
        for _i, (_col, _lbl, _fch, _vals) in enumerate(_series_bar):
            if _vals.notna().any():
                _alpha = 0.88 if _i < len(_activas_con_datos) else 0.72
                ax2.bar(_fch + _offs2[_i], _vals,
                        width=_bw2, color=_col, alpha=_alpha, label=_lbl, edgecolor='none')
        ax2.axhline(0, color='#444444', linewidth=0.8)
        ax2.set_ylabel('Variación mensual (%)', fontsize=11)
        ax2.legend(loc='upper right', fontsize=9, framealpha=0.95,
                   ncol=max(1, _n_b // 4 + 1))
        ax2.grid(True, alpha=0.2, axis='y', linewidth=0.7)
        ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=_tick_i))
        ax2.xaxis.set_major_formatter(mticker.FuncFormatter(_fmt_mes_es))
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=9)
        for sp in ['top', 'right']: ax2.spines[sp].set_visible(False)
        ax2.spines['bottom'].set_color('#cccccc')
        ax2.spines['left'].set_color('#cccccc')
        _vmax_l2 = [s.dropna().max() for *_, s in _series_bar if s.notna().any()]
        if _vmax_l2: ax2.set_ylim(top=max(_vmax_l2) * 1.35)
        _t2 = f'Variación mensual — análisis {_TIT}'
        if MES_PARCIAL:
            _t2 += f'  ·  {NOMBRE_MES_TITLE} PARCIAL {DIAS_CARGADOS}/{DIAS_MES} días (preliminar)'
        ax2.set_title(_t2, fontsize=10, color=('#C00000' if MES_PARCIAL else '#333'),
                      style=('italic' if MES_PARCIAL else 'normal'), pad=8)
        plt.tight_layout()
        out2 = OUTPUT_DIR / f'variaciones_canasta_vs_ipc_{MES}{_SFX}.png'
        plt.savefig(out2, dpi=600, bbox_inches='tight', facecolor='white')
        plt.show()
        print(f'Gráfico 2 [{_TIT}] guardado: {out2}')

        # ── GRAFICO 3: Ranking de valores absolutos por canasta ─────────────────
        _abs_data = sorted(
            [(CANASTA_NAMES[c], _PROMD[c], CANASTA_COLORS[c]) for c in CANASTAS_ACTIVAS],
            key=lambda x: x[1])
        _pnames  = [d[0] for d in _abs_data]
        _pvals   = [d[1] for d in _abs_data]
        _pcolors = [d[2] for d in _abs_data]
        _base_v  = _pvals[0] if _pvals else 1
        _n_bars  = len(_pvals)
        fig3, ax3 = plt.subplots(figsize=(12, max(5, _n_bars * 1.6 + 2)))
        bars3 = ax3.barh(_pnames, _pvals, color=_pcolors,
                         edgecolor='none', height=0.55, zorder=2)
        ax3.barh(_pnames, _pvals, color='black', alpha=0.06,
                 height=0.60, zorder=1)
        ax3.axvline(_base_v, color='#aaaaaa', linewidth=1.2, linestyle='--', zorder=3)
        for bar, val, name in zip(bars3, _pvals, _pnames):
            _ratio = val / _base_v if _base_v > 0 else 1
            _ratio_str = f'  ×{_ratio:.1f}' if _ratio > 1.05 else '  base'
            ax3.text(val + max(_pvals) * 0.008,
                     bar.get_y() + bar.get_height() / 2,
                     f'${int(val):,}'.replace(',', '.') + _ratio_str,
                     va='center', fontsize=11, fontweight='bold',
                     color='#2c3e50')
        ax3.set_yticklabels(_pnames, fontsize=12, fontweight='bold')
        ax3.set_xlabel(f'Costo mensual nacional (ARS) — análisis {_TIT}', fontsize=11, color='#444')
        ax3.xaxis.set_major_formatter(mticker.FuncFormatter(
            lambda x, _: f'${int(x):,}'.replace(',', '.')))
        ax3.set_xlim(0, max(_pvals) * 1.22)
        ax3.tick_params(axis='x', labelsize=10, colors='#555')
        ax3.grid(True, alpha=0.25, axis='x', zorder=0); ax3.set_axisbelow(True)
        for sp in ['top', 'right', 'left']: ax3.spines[sp].set_visible(False)
        ax3.spines['bottom'].set_color('#cccccc')
        fig3.text(0.98, 0.01, f'{NOMBRE_MES_TITLE}{SUFIJO_PARCIAL}',
                  ha='right', va='bottom', fontsize=9, color=('#C00000' if MES_PARCIAL else '#999'))
        plt.tight_layout()
        out3 = OUTPUT_DIR / f'ranking_canastas_{MES}{_SFX}.png'
        plt.savefig(out3, dpi=600, bbox_inches='tight', facecolor='white')
        plt.show()
        print(f'Gráfico 3 [{_TIT}] guardado: {out3}')"""))

# ── CELL 13 — CUADRO 1 + LaTeX (per-canasta) ──────────────────────────────────
cells.append(cell_code("""\
# ============================================================
# CELDA 13 — Cuadro 1 provincial + LaTeX (MEDIANA y PROMEDIO, por duplicado)
# ============================================================
def fmt_ar(x, dec=0):
    s = f'{x:,.{dec}f}'
    return s.replace(',','X').replace('.',',').replace('X','.')

nom_mes = {'01':'enero','02':'febrero','03':'marzo','04':'abril','05':'mayo','06':'junio',
           '07':'julio','08':'agosto','09':'septiembre','10':'octubre','11':'noviembre','12':'diciembre'}
_mes_s  = nom_mes[ULTIMO_MES[5:7]]
_anio_s = ULTIMO_MES[:4]

# (sufijo_archivo, titulo, col_valor, dict_prom_nacional)
_MEDIDAS13 = [
    ('',      'mediana',  'canasta_total',      prom_nac_dict),
    ('_prom', 'promedio', 'canasta_total_prom', prom_nac_prom_dict),
]
for _col_id in CANASTAS_ACTIVAS:
    _name  = CANASTA_NAMES[_col_id]
    _short = CANASTA_SHORT[_col_id]
    for _SFX, _TIT, _VCOL, _PROMD in _MEDIDAS13:
        _spv   = serie_prov_dict[_col_id].copy()
        _prom  = _PROMD[_col_id]
        _spv['vs_%'] = ((_spv[_VCOL] / _prom) - 1) * 100
        _spv = _spv.sort_values(_VCOL).reset_index(drop=True)

        print(f'\\n=== CUADRO 1: {_name.upper()} [{_TIT}] — {NOMBRE_MES_TITLE} ===\\n')
        print(f'{"Provincia":<25} {"Canasta":>14} {"Vs. promedio":>14}')
        print('-'*55)
        for _, r in _spv.iterrows():
            _c = fmt_ar(r[_VCOL])
            _v = f"{r['vs_%']:+.2f}%".replace('.',',')
            print(f"{r['provincia']:<25} {_c:>14} {_v:>14}")
        print('-'*55)
        print(f'{"Promedio nacional":<25} {fmt_ar(_prom):>14} {"0,00%":>14}')

        ltx = [
            r'\\begin{table}[H]',
            r'\\centering',
            r'\\renewcommand{\\arraystretch}{1.15}',
            f'\\\\caption{{Canasta {_name} por provincia ({_mes_s} {_anio_s}) --- analisis {_TIT}}}',
            r'\\begin{tabular}{@{}l r r@{}}',
            r'\\toprule',
            f'\\\\textbf{{Provincia}} & \\\\textbf{{Canasta}} & \\\\shortstack{{\\\\textbf{{Vs. promedio}}\\\\\\\\\\\\textbf{{pais (\\\\%)}}}} \\\\\\\\',
            r'\\midrule',
        ]
        for _, r in _spv.iterrows():
            _c = fmt_ar(r[_VCOL])
            _v = f"{r['vs_%']:+.2f}".replace('.',',')
            ltx.append(f"{r['provincia']:<22} & {_c} & {_v}\\\\% \\\\\\\\")
        ltx += [
            r'\\midrule',
            f'\\\\textbf{{Promedio}} & {fmt_ar(_prom)} & 0,00\\\\% \\\\\\\\',
            r'\\bottomrule',
            r'\\end{tabular}\\\\[0.2cm]',
            r'\\caption*{Fuente: Elaboracion propia en base a SEPA}',
            f'\\\\label{{tab:canasta_{_short}_{ULTIMO_MES}{_SFX}}}',
            r'\\end{table}',
        ]
        _latex_out = '\\n'.join(ltx)
        _out_tex = OUTPUT_DIR / f'tabla_canasta_{_short}_{ULTIMO_MES}{_SFX}.tex'
        _out_tex.write_text(_latex_out, encoding='utf-8')
        print(f'  LaTeX [{_TIT}] guardado: {_out_tex.name}')"""))

# ── CELL 14 — CHOROPLETH MAPS (one per canasta) ────────────────────────────────
cells.append(cell_code("""\
# ============================================================
# CELDA 14 — Mapa coroplético por canasta (MEDIANA y PROMEDIO, por duplicado)
# ============================================================
if not GEOJSON_PATH.exists():
    print(f'GeoJSON no encontrado en {GEOJSON_PATH} — saltear celda')
else:
    with open(GEOJSON_PATH, 'r', encoding='utf-8') as f:
        geo = _json.load(f)

    NORM_GEO = {'Ciudad de Buenos Aires': 'CABA'}
    AJUST = {
        'Salta':(0,-1),'Tucuman':(0.3,0),'Tucumán':(0.3,0),'Chaco':(0,-1),
        'Tierra del Fuego':(-1,-0.2),'Santa Fe':(0,1),'Santiago del Estero':(0.7,0),
    }

    def centroide(coords):
        xs,ys = [],[]
        if isinstance(coords[0][0][0],(int,float)):
            for p in coords[0]: xs.append(p[0]); ys.append(p[1])
        else:
            poly = max(coords, key=lambda p: len(p[0]))
            for p in poly[0]: xs.append(p[0]); ys.append(p[1])
        return sum(xs)/len(xs), sum(ys)/len(ys)

    def draw(ax, coords, color):
        if isinstance(coords[0][0][0],(int,float)):
            ax.fill([c[0] for c in coords[0]], [c[1] for c in coords[0]],
                    facecolor=color, edgecolor='white', linewidth=0.6)
        else:
            for poly in coords:
                ax.fill([c[0] for c in poly[0]], [c[1] for c in poly[0]],
                        facecolor=color, edgecolor='white', linewidth=0.6)

    cmap_m = LinearSegmentedColormap.from_list('c',
        ['#1a9850','#66bd63','#a6d96a','#d9ef8b','#fee08b','#fdae61','#f46d43','#d73027'], N=256)

    for _col_id in CANASTAS_ACTIVAS:
        _name   = CANASTA_NAMES[_col_id]
        _short  = CANASTA_SHORT[_col_id]
        _spv    = serie_prov_dict[_col_id]
        if len(_spv) == 0:
            print(f'  [{_name}] Sin datos provinciales — saltear mapa')
            continue
        for _SFX, _TIT, _VCOL in [('','mediana','canasta_total'), ('_prom','promedio','canasta_total_prom')]:
            _can_prov = dict(zip(_spv['provincia'], _spv[_VCOL]))
            _vals = list(_can_prov.values())
            norm_c = Normalize(vmin=min(_vals), vmax=max(_vals))

            fig, ax = plt.subplots(figsize=(12, 16))
            caba_c = None
            for feat in geo['features']:
                ng  = feat['properties']['name']
                nom = NORM_GEO.get(ng, ng)
                val = _can_prov.get(nom)
                col = cmap_m(norm_c(val)) if val is not None else '#dddddd'
                gt  = feat['geometry']['type']
                co  = feat['geometry']['coordinates']
                draw(ax, [co] if gt=='Polygon' else co, col)
                cx, cy = centroide([co] if gt=='Polygon' else co)
                if nom == 'CABA':
                    caba_c = (cx, cy); continue
                dx, dy = AJUST.get(nom, (0,0))
                if val is not None:
                    ax.text(cx+dx, cy+dy, f'{nom}\\n${val/1000:.0f}k',
                            ha='center', va='center', fontsize=7.5, fontweight='bold',
                            bbox=dict(boxstyle='round,pad=0.25', facecolor='white', alpha=0.75, edgecolor='none'))
            if caba_c and 'CABA' in _can_prov:
                vc = _can_prov['CABA']
                cc = cmap_m(norm_c(vc))
                lx, ly = caba_c[0]+2.2, caba_c[1]+0.8
                ax.annotate('', xy=caba_c, xytext=(lx,ly),
                            arrowprops=dict(arrowstyle='-', color='black', linewidth=1.0))
                ax.text(lx, ly, f'CABA\\n${vc/1000:.0f}k',
                        ha='center', va='center', fontsize=9, fontweight='bold',
                        bbox=dict(boxstyle='round,pad=0.5', facecolor=cc, alpha=0.95,
                                  edgecolor='black', linewidth=1.0))
                ax.plot(*caba_c, marker='o', markersize=10, markerfacecolor=cc,
                        markeredgecolor='black', markeredgewidth=1.2, zorder=5)
            ax.set_title(f'Canasta {_name} por provincia — análisis {_TIT}',
                         fontsize=13, fontweight='bold', pad=6)
            ax.set_aspect('equal'); ax.axis('off')
            plt.tight_layout()
            _out_m = OUTPUT_DIR / f'mapa_canasta_{_short}_{ULTIMO_MES}{_SFX}.png'
            plt.savefig(_out_m, dpi=600, bbox_inches='tight', facecolor='white')
            plt.show()
            print(f'  Mapa [{_name}/{_TIT}] guardado: {_out_m.name}')"""))

# ── CELL 15 — COVERAGE ─────────────────────────────────────────────────────────
cells.append(cell_code("""\
# ============================================================
# CELDA 15 — Gráficos de cobertura (primera canasta activa)
# ============================================================
_cgf0 = canasta_geo_dict[CANASTAS_ACTIVAS[0]]

_pm_info = (_cgf0[['id_comercio','id_bandera','id_sucursal',
                    'PROVINCIA_NORM','cadena']].drop_duplicates())
_pm_geo  = precio_mes.merge(_pm_info, on=['id_comercio','id_bandera','id_sucursal'], how='inner')
_pm_geo['suc_key'] = (_pm_geo['id_comercio'] + '_' +
                      _pm_geo['id_bandera']   + '_' + _pm_geo['id_sucursal'])

cob_provincia = (_pm_geo.groupby('PROVINCIA_NORM')
    .agg(n_productos_unicos=('ean_norm','nunique'),
         n_cadenas=('cadena','nunique'),
         n_sucursales=('suc_key','nunique'))
    .reset_index().rename(columns={'PROVINCIA_NORM':'provincia'}))

cob_cadena = (_pm_geo.groupby('cadena')
    .agg(n_productos_unicos=('ean_norm','nunique'),
         n_provincias=('PROVINCIA_NORM','nunique'),
         n_sucursales=('suc_key','nunique'))
    .reset_index())

matriz_cad_prov = (_pm_geo.groupby(['cadena','PROVINCIA_NORM'])['ean_norm']
    .nunique().unstack(fill_value=0))

df_p = cob_provincia.sort_values('n_productos_unicos', ascending=True).reset_index(drop=True)
fig, axes = plt.subplots(1, 3, figsize=(15, max(9, len(df_p)*0.38+2)), sharey=True)
for ax, (col, titulo, color) in zip(axes, [
        ('n_productos_unicos','Productos únicos','#0055A4'),
        ('n_cadenas','Cadenas presentes','#27ae60'),
        ('n_sucursales','Sucursales','#c0392b')]):
    ax.barh(df_p['provincia'], df_p[col], color=color, edgecolor='white')
    for i, v in enumerate(df_p[col]):
        ax.text(v+max(df_p[col])*0.01, i, f'{int(v):,}', va='center', fontsize=8, color='#2c3e50')
    ax.set_title(titulo, fontsize=11, fontweight='bold', color=color)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f'{int(x):,}'))
    ax.set_xlim(0, max(df_p[col])*1.15)
    for sp in ['top','right']: ax.spines[sp].set_visible(False)
plt.tight_layout()
out_cp = OUTPUT_DIR / f'cobertura_provincia_{MES}.png'
plt.savefig(out_cp, dpi=600, bbox_inches='tight'); plt.show()

df_c = cob_cadena.sort_values('n_productos_unicos', ascending=True).reset_index(drop=True)
fig, axes = plt.subplots(1, 3, figsize=(15, max(8, len(df_c)*0.5+2)), sharey=True)
for ax, (col, titulo, color) in zip(axes, [
        ('n_productos_unicos','Productos únicos','#0055A4'),
        ('n_provincias','Provincias presentes','#27ae60'),
        ('n_sucursales','Sucursales','#c0392b')]):
    ax.barh(df_c['cadena'], df_c[col], color=color, edgecolor='white')
    for i, v in enumerate(df_c[col]):
        ax.text(v+max(df_c[col])*0.01, i, f'{int(v):,}', va='center', fontsize=8, color='#2c3e50')
    ax.set_title(titulo, fontsize=11, fontweight='bold', color=color)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f'{int(x):,}'))
    ax.set_xlim(0, max(df_c[col])*1.15)
    for sp in ['top','right']: ax.spines[sp].set_visible(False)
axes[0].tick_params(axis='y', labelsize=8)
plt.tight_layout()
out_cc = OUTPUT_DIR / f'cobertura_cadena_{MES}.png'
plt.savefig(out_cc, dpi=600, bbox_inches='tight'); plt.show()

df_m = matriz_cad_prov.copy()
df_m['_total'] = df_m.sum(axis=1)
df_m = df_m.sort_values('_total', ascending=False).drop(columns='_total')
orden_prov = (df_m > 0).sum(axis=0).sort_values(ascending=False).index
df_m = df_m[orden_prov]

fig, ax = plt.subplots(figsize=(13, max(6, len(df_m)*0.55+2)))
binaria = (df_m > 0).astype(int)
sns.heatmap(binaria, cmap='Blues', cbar=False,
            linewidths=0.5, linecolor='white', xticklabels=True, yticklabels=True, ax=ax)
for i in range(binaria.shape[0]):
    for j in range(binaria.shape[1]):
        if binaria.iat[i, j]:
            ax.text(j+0.5, i+0.5, '●', ha='center', va='center', color='white', fontsize=9)
ax.set_xlabel(''); ax.set_ylabel('')
plt.xticks(rotation=45, ha='right', fontsize=9); plt.yticks(rotation=0, fontsize=9)
plt.tight_layout()
out_mp = OUTPUT_DIR / f'matriz_presencia_{MES}.png'
plt.savefig(out_mp, dpi=600, bbox_inches='tight'); plt.show()

fig, ax = plt.subplots(figsize=(13, max(6, len(df_m)*0.55+2)))
data_log = np.log10(df_m.replace(0, np.nan))
sns.heatmap(data_log, cmap='YlOrRd', linewidths=0.5, linecolor='white',
            cbar_kws={'label': 'log10(productos unicos)'},
            xticklabels=True, yticklabels=True, ax=ax)
ax.set_xlabel(''); ax.set_ylabel('')
plt.xticks(rotation=45, ha='right', fontsize=9); plt.yticks(rotation=0, fontsize=9)
plt.tight_layout()
out_mi = OUTPUT_DIR / f'matriz_intensidad_{MES}.png'
plt.savefig(out_mi, dpi=600, bbox_inches='tight'); plt.show()
print('Gráficos cobertura guardados')"""))

# ── CELL 16 — RANKINGS (per-canasta) ──────────────────────────────────────────
cells.append(cell_code("""\
# ============================================================
# CELDA 16 — Rankings de cadenas (MEDIANA y PROMEDIO, por duplicado)
# ============================================================
def fmtn(x): return f'{x:,.0f}'.replace(',','.')

# (sufijo, titulo, col_valor, agregador_por_cadena)
_MEDIDAS16 = [('','mediana','canasta_total','median'), ('_prom','promedio','canasta_total_prom',_pmean)]
for _col_id in CANASTAS_ACTIVAS:
    _name  = CANASTA_NAMES[_col_id]
    _short = CANASTA_SHORT[_col_id]
    _cgf   = canasta_geo_dict[_col_id]
    for _SFX, _TIT, _VCOL, _AGG in _MEDIDAS16:

        _rk_nac = (_cgf.groupby('cadena')
                   .agg(n_sucursales=(_VCOL,'count'), valor=(_VCOL,_AGG))
                   .round(0).reset_index())
        _rk_nac = _rk_nac[_rk_nac['n_sucursales'] >= MIN_SUCURSALES_RANKING].sort_values('valor')
        # Referencia del pais = la del Cuadro 1 (CELDA 8), la misma en todo el informe
        _prom_nac_rk = (prom_nac_dict[_col_id] if _SFX == '' else prom_nac_prom_dict[_col_id])

        _amba = _cgf[_cgf['amba']]      # CABA + conurbano por coordenadas (CELDA 7)
        _rk_amba = (_amba.groupby('cadena')
                    .agg(n_sucursales=(_VCOL,'count'), valor=(_VCOL,_AGG))
                    .round(0).reset_index())
        _rk_amba = _rk_amba[_rk_amba['n_sucursales'] >= MIN_SUCURSALES_RANKING].sort_values('valor')
        _prom_amba_rk = ((_amba[_VCOL].median() if _SFX == '' else _pmean(_amba[_VCOL])) if len(_amba) > 0 else 0)

        for (_rk, _prom_r, _lbl_r, _titulo, _out_name) in [
            (_rk_nac,  _prom_nac_rk,  'Nacional (Cuadro 1)', f'Ranking nacional [{_name}/{_TIT}]',  f'ranking_cadenas_nacional_{MES}_{_short}{_SFX}'),
            (_rk_amba, _prom_amba_rk, 'AMBA',                f'Ranking AMBA [{_name}/{_TIT}]',      f'ranking_cadenas_amba_{MES}_{_short}{_SFX}'),
        ]:
            if len(_rk) == 0:
                print(f'  Sin datos para {_titulo}'); continue
            fig, ax = plt.subplots(figsize=(11, max(5, len(_rk)*0.5+2)))
            labs   = [f"{r.cadena}  ({int(r.n_sucursales)})" for r in _rk.itertuples()]
            _n_c   = len(_rk)
            _cols  = plt.cm.RdYlGn_r(np.linspace(0.1, 0.9, _n_c)) if _n_c > 1 else [CANASTA_COLORS[_col_id]]
            bars   = ax.barh(labs, _rk['valor'], color=_cols, edgecolor='black', linewidth=0.4)
            for bar, val in zip(bars, _rk['valor']):
                ax.text(bar.get_width() + _rk['valor'].max()*0.005,
                        bar.get_y()+bar.get_height()/2,
                        f'${fmtn(val)}', va='center', fontsize=9, fontweight='bold')
            ax.axvline(_prom_r, color='#666', linestyle='--', linewidth=1.5,
                       label=f'{_lbl_r}: ${fmtn(_prom_r)}')
            ax.set_xlabel(f'Canasta por cadena (ARS) — {_TIT}', fontsize=11)
            ax.set_title(_titulo, fontsize=11, fontweight='bold')
            ax.set_xlim(_rk['valor'].min()*0.95, _rk['valor'].max()*1.07)
            ax.xaxis.set_major_formatter(mticker.FuncFormatter(
                lambda x,_: f'${int(x):,}'.replace(',','.')))
            ax.legend(loc='lower right', fontsize=10)
            ax.grid(True, alpha=0.3, axis='x'); ax.set_axisbelow(True)
            for sp in ['top','right']: ax.spines[sp].set_visible(False)
            plt.tight_layout()
            _out_r = OUTPUT_DIR / f'{_out_name}.png'
            plt.savefig(_out_r, dpi=600, bbox_inches='tight'); plt.show()
            print(f'  Ranking [{_name}/{_TIT}] guardado: {_out_r.name}')

        print(f'\\n  === RANKING NACIONAL [{_name}/{_TIT}] ===')
        for i, r in enumerate(_rk_nac.sort_values('valor', ascending=False).itertuples(), 1):
            print(f'    {i:>2}. {r.cadena:<25} ${fmtn(r.valor):>12}  ({int(r.n_sucursales)} sucs)')"""))

# ── CELL 17 — FOLIUM MAP (marcadores dibujados en el navegador) ───────────────
cells.append(cell_code("""\
# ============================================================
# CELDA 17 — Mapa Folium: los circulos los dibuja el navegador
# Antes se escribia un objeto Leaflet por canasta x sucursal (~1,6 KB cada uno,
# con popup y tooltip propios). Con muchos canastas el HTML se iba a decenas de
# MB y el 95% eran marcadores ocultos (solo se ve una por vez). Ahora va SOLO
# el JSON de sucursales -que ya existia para los popups- mas lat/lon, y Leaflet
# dibuja al vuelo los del canasta elegido. Ver BUG-31.
# ============================================================
def fmtm(x): return f'{x:,.0f}'.replace(',','.')

RAMPA_MAPA = ['#1a9850','#66bd63','#a6d96a','#fee08b','#fdae61','#f46d43','#d73027']

# CSS y JS del mapa: strings PLANOS (no f-strings) para no doblar llaves ni
# escapar comillas. Lo unico que se inyecta despues es el nombre del mapa.
_CSS_MAPA = '''
.lz-w{font-family:Arial;font-size:12px;width:420px;max-height:500px;overflow-y:auto}
.lz-h4{margin:0;color:#0055A4}
.lz-nfo{font-size:11px;color:#555;margin-bottom:5px}
.lz-bg{background:#e6eef7;padding:2px 6px;border-radius:3px;font-size:10px}
.lz-cx{text-align:center;margin:8px 0}
.lz-lbl{font-size:11px;color:#555;margin-bottom:2px}
.lz-tot{color:#0055A4;font-size:22px;font-weight:bold}
.lz-sub{font-size:11px;color:#888;text-align:center;margin-top:3px}
.lz-hr{margin:5px 0}
#lgd{position:fixed;bottom:25px;right:25px;width:260px;background:white;border:2px solid #0055A4;
     border-radius:8px;padding:10px 12px;font-family:Arial;z-index:9999}
.lg-t{font-size:11px;color:#0055A4;font-weight:bold;margin-bottom:6px;line-height:1.3}
.lg-bar{height:14px;border:1px solid #999;border-radius:2px}
.lg-x{display:flex;justify-content:space-between;font-size:10px;color:#555;margin-top:3px}
#load{position:fixed;top:0;left:0;right:0;bottom:0;background:#f4f4f4;z-index:10000;display:flex;
      align-items:center;justify-content:center;font-family:Arial;font-size:13px;color:#0055A4}
#pfh{cursor:pointer}
#pfc{float:right;color:#888}
#pf.min #pfb{display:none}
@media (max-width:700px){
 #info{left:6px !important;right:6px;top:6px !important;width:auto !important;
       padding:8px 10px !important}
 #pf{left:6px !important;right:6px;bottom:6px !important;width:auto !important;
     padding:8px 10px !important}
 #lgd{position:static !important;width:auto !important;border:0 !important;box-shadow:none;
      padding:8px 0 0 !important;margin-top:6px}
 .lz-w{width:auto;max-width:78vw}
}
#tw{display:none;position:fixed;top:10px;right:25px;width:300px;background:#fff6e5;
    border:2px solid #d98b00;border-radius:8px;padding:10px 12px;font-family:Arial;
    font-size:11px;color:#7a4f00;z-index:9999;line-height:1.4}
'''

_JS_MAPA = '''
(function(){
var MAP=null,LAYER=null,PD=null,CFG=null,ESC={},NAMES={},TRIES=0;
function el(i){return document.getElementById(i);}
function J(i){var e=el(i);return e?JSON.parse(e.textContent):null;}
function fmt(x){return "$"+Number(x).toLocaleString("es-AR",{minimumFractionDigits:0,maximumFractionDigits:0});}
function mix(a,b,f){
 var pa=[parseInt(a.substr(1,2),16),parseInt(a.substr(3,2),16),parseInt(a.substr(5,2),16)];
 var pb=[parseInt(b.substr(1,2),16),parseInt(b.substr(3,2),16),parseInt(b.substr(5,2),16)];
 return "rgb("+pa.map(function(v,i){return Math.round(v+(pb[i]-v)*f);}).join(",")+")";
}
function color(v,mn,mx){
 var r=CFG.ramp,t=(mx>mn)?(v-mn)/(mx-mn):0;
 t=Math.max(0,Math.min(1,t));
 var p=t*(r.length-1),i=Math.floor(p);
 if(i>=r.length-1){return r[r.length-1];}
 return mix(r[i],r[i+1],p-i);
}
function val(s,id){var c=s.can[id];return (c===undefined)?undefined:c.t;}
function popup(s,id){
 var c=s.can[id];
 if(c===undefined){return "<div>Sin datos.</div>";}
 var v=c.t;
 return '<div class="lz-w"><h4 class="lz-h4">'+s.cad+"</h4>"
  +'<div class="lz-nfo"><b>'+s.nom+"</b><br>"+(s.bar?s.bar+" — ":"")+s.prv
  +'<br><span class="lz-bg">'+s.tip+"</span></div>"
  +'<hr class="lz-hr">'
  +'<div class="lz-cx"><div class="lz-lbl">'+NAMES[id]+'</div><span class="lz-tot">'+fmt(v)+"</span></div>"
  +'<div class="lz-sub">'+c.p+"/"+c.n+" productos propios ("+Math.round(c.p/c.n*100)+"%)</div>"
  +"</div>";
}
function popFn(s,id){return function(){return popup(s,id);};}
function legend(id){
 var e=ESC[id],c=el("lgd");
 if(!c||!e){return;}
 c.innerHTML='<div class="lg-t">'+e.nom+" — "+CFG.cap+"</div>"
  +'<div class="lg-bar" style="background:linear-gradient(to right,'+CFG.ramp.join(",")+')"></div>'
  +'<div class="lg-x"><span>'+fmt(e.min)+"</span><span>"+fmt(e.max)+"</span></div>";
}
function render(){
 var id=el("fcan").value,ca=el("fca").value,pv=el("fp").value,e=ESC[id];
 if(!e){return;}
 if(LAYER){MAP.removeLayer(LAYER);}
 LAYER=L.layerGroup();
 var n=0,sum=0;
 for(var k in PD){
  var s=PD[k],v=val(s,id);
  if(v===undefined){continue;}
  if(ca!=="all"&&s.cad!==ca){continue;}
  if(pv!=="all"&&s.prv!==pv){continue;}
  var col=color(v,e.min,e.max);
  var mk=L.circleMarker([s.la,s.lo],{radius:5,color:col,fillColor:col,fill:true,fillOpacity:0.8,weight:1});
  mk.bindTooltip("<b>"+s.cad+"</b><br>"+s.prv+"<br><b>"+fmt(v)+"</b>");
  mk.bindPopup(popFn(s,id),{maxWidth:450});
  LAYER.addLayer(mk);n++;sum+=v;
 }
 LAYER.addTo(MAP);
 var a=el("info_avg");
 if(a){a.innerHTML=(n?fmt(sum/n):"s/d")+" ("+NAMES[id]+", "+n.toLocaleString("es-AR")+" sucursales)";}
 legend(id);
}
function base(i){
 var t=CFG.tiles[i];
 if(!t){var w=el("tw");if(w){w.style.display="block";}return;}
 var ok=0,err=0,fue=false;
 var opt={attribution:t.attr,maxZoom:19,maxNativeZoom:t.maxn};
 var lay=L.tileLayer(t.url,opt),ref=t.ref?L.tileLayer(t.ref,opt):null;
 function sig(){
  if(fue){return;}
  fue=true;
  MAP.removeLayer(lay);
  if(ref){MAP.removeLayer(ref);}
  base(i+1);
 }
 lay.on("tileload",function(){ok=ok+1;});
 lay.on("tileerror",function(){err=err+1;if(ok===0&&err>=4){sig();}});
 lay.addTo(MAP);
 if(ref){ref.addTo(MAP);}
 // si en 9 s no entro ni un mosaico, el proveedor no responde desde esta red
 setTimeout(function(){if(ok===0){sig();}},9000);
}
function boot(){
 MAP=window["__MAPVAR__"];
 if(typeof L==="undefined"||!MAP||!MAP.addLayer){
  TRIES=TRIES+1;
  if(TRIES>300){return;}
  return setTimeout(boot,100);
 }
 PD=J("_pd_json");CFG=J("_cfg_json");
 if(!PD||!CFG){return;}
 base(0);
 CFG.items.forEach(function(p){ESC[p.id]=p;NAMES[p.id]=p.nom;});
 ["fcan","fca","fp"].forEach(function(i){var x=el(i);if(x){x.addEventListener("change",render);}});
 var b=el("fr");
 if(b){b.addEventListener("click",function(){
  el("fcan").value=CFG.items[0].id;el("fca").value="all";el("fp").value="all";render();});}
 render();
}
boot();
})();
'''

# Interfaz: layout para telefono, panel de filtros plegable y pantalla de carga.
# Va aparte del JS del mapa porque no depende de el (BUG-33).
_JS_UI = '''
(function(){
function el(i){return document.getElementById(i);}
function chico(){return window.matchMedia("(max-width:700px)").matches;}
function layout(){
 var pf=el("pf"),lg=el("lgd"),bd=el("pfb"),c=el("pfc");
 if(!pf||!lg||!bd){return;}
 if(chico()){
  if(lg.parentNode!==bd){bd.appendChild(lg);}
  if(!pf.getAttribute("data-ini")){pf.className="min";pf.setAttribute("data-ini","1");}
 }else{
  if(lg.parentNode===bd){document.body.appendChild(lg);}
  pf.className="";
 }
 if(c){c.innerHTML=(pf.className==="min")?"+":"-";}
}
var h=el("pfh");
if(h){h.addEventListener("click",function(){
 var pf=el("pf");
 pf.className=(pf.className==="min")?"":"min";
 layout();
});}
window.addEventListener("resize",layout);
layout();
var n=0;
(function espera(){
 n=n+1;
 var lo=el("load");
 if(document.querySelector("path.leaflet-interactive")||n>200){
  if(lo&&lo.parentNode){lo.parentNode.removeChild(lo);}
  return;
 }
 setTimeout(espera,150);
})();
})();'''

# Dos mapas: analisis MEDIANA (sin sufijo) y PROMEDIO (_prom)
for _SFX, _TIT, _VCOL in [('','mediana','canasta_total'), ('_prom','promedio','canasta_total_prom')]:
    # ── Un registro por sucursal: metadata + lat/lon + valor de cada canasta ────
    _popup_data = {}
    for _col_id in CANASTAS_ACTIVAS:
        _nc = len(CANASTAS[_col_id])
        for _, _r in canasta_geo_dict[_col_id].iterrows():
            _sk = f"{_r['id_comercio']}_{_r['id_bandera']}_{_r['id_sucursal']}"
            if _sk not in _popup_data:
                _popup_data[_sk] = {
                    'nom': str(_r['sucursales_nombre'])[:40],
                    'bar': str(_r.get('sucursales_barrio') or _r.get('sucursales_localidad') or '')[:30],
                    'prv': _r['PROVINCIA_NORM'],
                    'cad': _r['cadena'],
                    'tip': str(_r.get('sucursales_tipo') or 'N/D'),
                    'la': round(float(_r['sucursales_latitud']), 5),
                    'lo': round(float(_r['sucursales_longitud']), 5),
                    'can': {}
                }
            _popup_data[_sk]['can'][_col_id] = {
                't': int(_r[_VCOL]),
                'p': int(_r['productos_propios']),
                'n': _nc
            }


    # Escala de color por canasta (mismos percentiles que usaba LinearColormap)
    _items_cfg = []
    for _col_id in CANASTAS_ACTIVAS:
        _v = canasta_geo_dict[_col_id][_VCOL]
        _a, _b = float(_v.quantile(0.05)), float(_v.quantile(0.95))
        if _a == _b: _a, _b = float(_v.min()), float(_v.max())
        if _a == _b: _b = _a + 1.0
        _items_cfg.append({'id': _col_id, 'nom': f'ICR {CANASTA_NAMES[_col_id]}',
                           'min': round(_a, 2), 'max': round(_b, 2)})

    # ── Mosaicos del mapa base ───────────────────────────────────────────────────
    # Mosaicos del mapa base: NO se fija uno solo. Van varios en orden y el navegador
    # se queda con el PRIMERO QUE RESPONDA (BUG-32). Desde la red de INECO
    # tile.openstreetmap.org no responde: el mapa quedaba sin lineas limitrofes y la
    # pestaña "cargando" para siempre esperando mosaicos que nunca llegaban.
    # CartoDB va ultimo porque sin cuenta estampa "API key required" (BUG-30) y eso
    # NO da error, asi que nunca se descarta solo.
    _ESRI = 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/'
    _TILES_OPC = {
        'esri':  {'url': _ESRI + 'World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}',
                  'ref': _ESRI + 'World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}',
                  'attr': 'Mosaicos &copy; Esri', 'maxn': 16},
        'osm':   {'url': 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                  'attr': '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
                  'maxn': 19},
        'topo':  {'url': 'https://tile.opentopomap.org/{z}/{x}/{y}.png',
                  'attr': '&copy; OpenTopoMap (CC-BY-SA) &middot; &copy; OpenStreetMap contributors',
                  'maxn': 17},
        'carto': {'url': 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
                  'attr': '&copy; OpenStreetMap contributors &copy; CARTO', 'maxn': 20},
    }
    _ORDEN_DEF = ['esri', 'osm', 'topo', 'carto']
    _pref = globals().get('TILES_MAPA', 'auto')
    _pref = [_pref] if isinstance(_pref, str) else list(_pref)
    _pref = [str(_t).lower() for _t in _pref if str(_t).lower() != 'auto']
    _malos = [_t for _t in _pref if _t not in _TILES_OPC]
    if _malos:
        print(f'AVISO: TILES_MAPA desconocido {_malos}; opciones: {list(_TILES_OPC)}')
    _orden = ([_t for _t in _pref if _t in _TILES_OPC]
              + [_t for _t in _ORDEN_DEF if _t not in _pref])
    _tiles_cfg = [dict(_TILES_OPC[_t], id=_t) for _t in _orden]
    print(f'Mapa base: se prueba en orden {_orden} (el navegador se queda con el primero que responda)')

    _popup_json = _json.dumps(_popup_data, ensure_ascii=False, separators=(',',':'))
    _cfg_json   = _json.dumps({'ramp': RAMPA_MAPA, 'items': _items_cfg,
                               'cap': f'{NOMBRE_MES_TITLE} ({_TIT}, ARS)',
                               'tiles': _tiles_cfg},
                              ensure_ascii=False, separators=(',',':'))
    print(f'Datos mapa [{_TIT}]: {len(_popup_data):,} sucursales | '
          f'{(len(_popup_json)+len(_cfg_json))/1024/1024:.2f} MB JSON')

    # ── Mapa Folium ───────────────────────────────────────────────────────────────
    m = folium.Map(location=[-38.0,-63.5], zoom_start=5,
                   tiles=None, control_scale=True)
    folium.map.Marker(
        location=[-51.7963,-59.5236],
        icon=folium.DivIcon(icon_size=(140,28), icon_anchor=(70,14),
            html='<div style="background:rgba(255,255,255,.95);border:1px solid #777;border-radius:3px;padding:3px 7px;font-family:Arial;font-size:11px;font-weight:600;text-align:center;white-space:nowrap;">Islas Malvinas (ARG)</div>')
    ).add_to(m)

    # ── Datos embebidos como JSON (el navegador los lee al abrir) ────────────────
    m.get_root().html.add_child(folium.Element(
        f'<script type="application/json" id="_pd_json">{_popup_json}</script>'))
    m.get_root().html.add_child(folium.Element(
        f'<script type="application/json" id="_cfg_json">{_cfg_json}</script>'))

    # ── Paneles (info, filtros, leyenda) ────────────────────────────────────────
    _cadenas_u = sorted({_d['cad'] for _d in _popup_data.values()})
    _provs_u   = sorted({_d['prv'] for _d in _popup_data.values()})
    _can_opts  = ''.join(f'<option value="{_c["id"]}">{_c["nom"]}</option>' for _c in _items_cfg)
    _cad_opts  = ''.join(f'<option value="{_c}">{_c}</option>' for _c in _cadenas_u)
    _prov_opts = ''.join(f'<option value="{_p}">{_p}</option>' for _p in _provs_u)

    info_h = (f'<div id="info" style="position:fixed;top:10px;left:50px;width:340px;background:white;border:2px solid #0055A4;'
              f'border-radius:8px;padding:12px 15px;font-family:Arial;z-index:9999;box-shadow:0 2px 8px rgba(0,0,0,.15);">'
              f'<div style="color:#0055A4;font-size:15px;font-weight:bold;margin-bottom:5px;">ICR — {NOMBRE_MES_TITLE} ({_TIT})</div>'
              f'<div style="font-size:11px;color:#555;line-height:1.5;">'
              f'<b>{len(_popup_data):,}</b> sucursales · <b>{len(_items_cfg)}</b> canastas<br>'
              f'Promedio: <span id="info_avg" style="font-weight:bold;"></span></div></div>')
    m.get_root().html.add_child(folium.Element(info_h))

    filtros_h = (
        f'<div id="pf" style="position:fixed;bottom:25px;left:50px;width:280px;background:white;'
        f'border:2px solid #0055A4;border-radius:8px;padding:12px 15px;font-family:Arial;z-index:9999;">'
        f'<div id="pfh" style="color:#0055A4;font-size:13px;font-weight:bold;margin-bottom:8px;"><span id="pfc"></span>🔍 Filtros</div><div id="pfb">'
        f'<label style="font-size:11px;color:#555;display:block;margin-top:4px;">Canasta:'
        f'<select id="fcan" style="width:100%;padding:4px;font-size:11px;margin-top:3px;">{_can_opts}</select></label>'
        f'<label style="font-size:11px;color:#555;display:block;margin-top:6px;">Cadena:'
        f'<select id="fca" style="width:100%;padding:4px;font-size:11px;margin-top:3px;">'
        f'<option value="all">Todas</option>{_cad_opts}</select></label>'
        f'<label style="font-size:11px;color:#555;display:block;margin-top:6px;">Provincia:'
        f'<select id="fp" style="width:100%;padding:4px;font-size:11px;margin-top:3px;">'
        f'<option value="all">Todas</option>{_prov_opts}</select></label>'
        f'<button id="fr" style="width:100%;margin-top:10px;padding:6px;background:#f0f0f0;'
        f'border:1px solid #ccc;border-radius:4px;font-size:11px;cursor:pointer;">Restablecer</button></div></div>'
        f'<div id="lgd"></div>'
        f'<div id="tw">No se pudieron cargar los mosaicos del mapa base desde esta red '
        f'(se probaron: {", ".join(_orden)}). Los datos y los marcadores estan bien; '
        f'lo que falta es solo el fondo del mapa.</div>'
        f'<div id="load">Cargando el mapa...</div>'
        '<script>' + _JS_UI + '</script>')
    m.get_root().html.add_child(folium.Element(filtros_h))

    # ── Titulo, descripcion y favicon: esto se comparte por link (BUG-33) ───────
    _tit_pag = f'Mapa del ICR por supermercado — {NOMBRE_MES_TITLE}'
    _desc_pag = (f'{len(_popup_data):,} sucursales de todo el pais con el costo de 'f'{len(_items_cfg)} canastas ({_TIT}). Datos del SEPA.')
    _svg_fav = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'>"
                "<rect width='32' height='32' rx='6' fill='rgb(0,85,164)'/>"
                "<circle cx='16' cy='13' r='4.5' fill='rgb(255,255,255)'/>"
                "<path d='M16 30 L9 17 L23 17 Z' fill='rgb(255,255,255)'/></svg>")
    _fav = 'data:image/svg+xml,' + _svg_fav.replace('<','%3C').replace('>','%3E').replace(' ','%20')
    m.get_root().header.add_child(folium.Element(
        f'<title>{_tit_pag}</title>'
        f'<meta name="description" content="{_desc_pag}">'
        f'<meta property="og:type" content="website">'
        f'<meta property="og:title" content="{_tit_pag}">'
        f'<meta property="og:description" content="{_desc_pag}">'
        f'<link rel="icon" href="{_fav}">'))

    # ── CSS + JS ────────────────────────────────────────────────────────────────
    m.get_root().html.add_child(folium.Element(
        '<style>' + _CSS_MAPA + '</style>'
        '<script>' + _JS_MAPA.replace('__MAPVAR__', m.get_name()) + '</script>'))

    # Folium engancha jQuery, Bootstrap, Font Awesome y awesome-markers, que este mapa
    # no usa: son 6 pedidos externos de mas (uno de ellos, netdna.bootstrapcdn.com, es
    # de un CDN discontinuado). Se sacan del HTML antes de guardar.
    _CDN_SOBRAN = ('code.jquery.com', 'bootstrap@5', 'bootstrap-glyphicons',
                   'fontawesome-free', 'leaflet.awesome-markers', 'leaflet.awesome.rotate')
    _html = m.get_root().render()
    _lineas = [_l for _l in _html.splitlines()
               if not (('<script src=' in _l or '<link rel="stylesheet"' in _l)
                       and any(_d in _l for _d in _CDN_SOBRAN))]
    out_map = OUTPUT_DIR / f'mapa_interactivo_{MES}{_SFX}.html'
    out_map.write_text(chr(10).join(_lineas), encoding='utf-8')
    _mb = out_map.stat().st_size / 1024 / 1024
    print(f'Mapa [{_TIT}] guardado: {out_map.name} '
          f'({len(_items_cfg)} canastas · {len(_popup_data):,} sucs · {_mb:.1f} MB)')"""))

# ── CELL 18 — CABA RANKINGS (per-canasta) ─────────────────────────────────────
cells.append(cell_code("""\
# ============================================================
# CELDA 18 — Ranking de barrios CABA para cada canasta
# ============================================================
BARRIOS_BBOX = {
    'Agronomia':           (-34.604,-34.587,-58.498,-58.476),
    'Almagro':             (-34.622,-34.598,-58.435,-58.405),
    'Balvanera':           (-34.617,-34.598,-58.418,-58.388),
    'Barracas':            (-34.661,-34.628,-58.395,-58.366),
    'Belgrano':            (-34.575,-34.547,-58.471,-58.434),
    'Boedo':               (-34.638,-34.620,-58.426,-58.408),
    'Caballito':           (-34.628,-34.602,-58.460,-58.421),
    'Chacarita':           (-34.595,-34.575,-58.470,-58.443),
    'Coghlan':             (-34.572,-34.555,-58.485,-58.469),
    'Colegiales':          (-34.580,-34.563,-58.460,-58.439),
    'Constitucion':        (-34.631,-34.620,-58.395,-58.378),
    'Flores':              (-34.642,-34.615,-58.480,-58.435),
    'Floresta':            (-34.633,-34.615,-58.500,-58.479),
    'La Boca':             (-34.643,-34.620,-58.371,-58.350),
    'La Paternal':         (-34.605,-34.585,-58.475,-58.456),
    'Liniers':             (-34.652,-34.628,-58.534,-58.506),
    'Mataderos':           (-34.665,-34.641,-58.522,-58.488),
    'Monte Castro':        (-34.628,-34.610,-58.520,-58.500),
    'Monserrat':           (-34.625,-34.605,-58.391,-58.371),
    'Nueva Pompeya':       (-34.658,-34.638,-58.418,-58.396),
    'Nunez':               (-34.553,-34.532,-58.475,-58.443),
    'Palermo':             (-34.595,-34.560,-58.435,-58.398),
    'Parque Avellaneda':   (-34.660,-34.638,-58.495,-58.470),
    'Parque Chacabuco':    (-34.645,-34.625,-58.448,-58.422),
    'Parque Chas':         (-34.591,-34.578,-58.487,-58.475),
    'Parque Patricios':    (-34.652,-34.628,-58.418,-58.395),
    'Puerto Madero':       (-34.625,-34.587,-58.371,-58.349),
    'Recoleta':            (-34.598,-34.575,-58.405,-58.378),
    'Retiro':              (-34.595,-34.578,-58.388,-58.365),
    'Saavedra':            (-34.560,-34.540,-58.495,-58.467),
    'San Cristobal':       (-34.625,-34.612,-58.408,-58.391),
    'San Nicolas':         (-34.610,-34.595,-58.395,-58.371),
    'San Telmo':           (-34.625,-34.610,-58.378,-58.365),
    'Velez Sarsfield':     (-34.642,-34.624,-58.510,-58.493),
    'Versalles':           (-34.640,-34.621,-58.525,-58.508),
    'Villa Crespo':        (-34.605,-34.585,-58.452,-58.428),
    'Villa del Parque':    (-34.615,-34.595,-58.498,-58.472),
    'Villa Devoto':        (-34.612,-34.585,-58.518,-58.490),
    'Villa General Mitre': (-34.615,-34.600,-58.475,-58.458),
    'Villa Lugano':        (-34.690,-34.660,-58.475,-58.435),
    'Villa Luro':          (-34.645,-34.628,-58.510,-58.491),
    'Villa Ortuzar':       (-34.590,-34.575,-58.475,-58.456),
    'Villa Pueyrredon':    (-34.585,-34.565,-58.510,-58.485),
    'Villa Real':          (-34.628,-34.615,-58.530,-58.512),
    'Villa Riachuelo':     (-34.695,-34.680,-58.470,-58.450),
    'Villa Santa Rita':    (-34.622,-34.605,-58.488,-58.470),
    'Villa Soldati':       (-34.682,-34.655,-58.460,-58.420),
    'Villa Urquiza':       (-34.590,-34.565,-58.495,-58.470),
}

def det_barrio(lat, lon):
    if pd.isna(lat) or pd.isna(lon): return 'Sin clasificar'
    for b,(lmin,lmax,lonmin,lonmax) in BARRIOS_BBOX.items():
        if lmin <= lat <= lmax and lonmin <= lon <= lonmax: return b
    return 'Sin clasificar'

def fmtb(x): return f'${x:,.0f}'.replace(',','.')

# Dos rankings por canasta: analisis MEDIANA y PROMEDIO (outliers fuera).
_MEDIDAS18 = [('mediana','canasta_total','median'), ('promedio','canasta_total_prom',_pmean)]
for _col_id in CANASTAS_ACTIVAS:
    _name  = CANASTA_NAMES[_col_id]
    _cgf   = canasta_geo_dict[_col_id]
    _caba  = _cgf[_cgf['PROVINCIA_NORM'] == 'CABA'].copy()
    if len(_caba) == 0:
        print(f'  [{_name}] Sin sucursales en CABA'); continue
    _caba['barrio'] = _caba.apply(
        lambda r: det_barrio(r['sucursales_latitud'], r['sucursales_longitud']), axis=1)
    for _TIT, _VCOL, _AGG in _MEDIDAS18:
        _rk_b = (_caba[_caba['barrio'] != 'Sin clasificar']
                 .groupby('barrio')
                 .agg(n_sucs=(_VCOL,'count'), valor=(_VCOL,_AGG))
                 .round(0).sort_values('valor'))
        _rk_b_fil = _rk_b[_rk_b['n_sucs'] >= 2]
        # CABA = la fila CABA del Cuadro 1; pais = el promedio ponderado del Cuadro 1 (CELDA 8)
        _pc = (_caba[_VCOL].median() if _TIT == 'mediana' else _pmean(_caba[_VCOL]))
        _pp = (prom_nac_dict[_col_id] if _TIT == 'mediana' else prom_nac_prom_dict[_col_id])

        print(f'\\n{"="*78}')
        print(f'  RANKING BARRIOS CABA [{_name.upper()}/{_TIT}] — {NOMBRE_MES_TITLE}')
        print(f'{"="*78}')
        print(f'  {"#":<3} {"Barrio":<22} {"Sucs.":<7} {"Valor":<13} {"vs CABA":<10} {"vs Pais"}')
        print(f'  {"-"*70}')
        for i, (b, r) in enumerate(_rk_b_fil.iterrows(), 1):
            vc = (r["valor"]/max(_pc,1)-1)*100
            vp = (r["valor"]/max(_pp,1)-1)*100
            print(f'  {i:<3} {b:<22} {int(r["n_sucs"]):<7} {fmtb(r["valor"]):<13} {vc:+.2f}%  {vp:+.2f}%')
        print(f'  {"-"*70}')
        print(f'  [{_TIT}] CABA (Cuadro 1): {fmtb(_pc)}   Pais (Cuadro 1, ponderado): {fmtb(_pp)}')
        _sin = set(BARRIOS_BBOX.keys()) - set(_rk_b.index)
        if _sin:
            print(f'  Sin sucursales ({len(_sin)}): {", ".join(sorted(_sin))}')"""))

# ── CELL 19 — EXCEL EXPORT (multi-canasta) ────────────────────────────────────
cells.append(cell_code("""\
# ============================================================
# CELDA 19 — Exportación Excel multi-canasta (MEDIANA y PROMEDIO, por duplicado)
# ============================================================
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

# Colores del Excel (canasta_analisis_*.xlsx), los mismos en todas las hojas:
#   VERDE_OSCURO: encabezados de las hojas y filas de sección de analisis_detallado (texto blanco encima).
#                 Excel: "Verde, Énfasis 6, Oscuro 50%". Antes azul oscuro 1F4E79.
#   VERDE_CLARO:  fila de encabezado de analisis_detallado (texto negro). Excel: "Verde claro" (colores
#                 estándar). Antes azul claro D9E1F2.
VERDE_OSCURO = '375623'
VERDE_CLARO  = '92D050'
HDR_FILL = PatternFill(start_color=VERDE_OSCURO, end_color=VERDE_OSCURO, fill_type='solid')
HDR_FONT = Font(bold=True, color='FFFFFF', size=10)
HDR_ALIG = Alignment(horizontal='center', wrap_text=True, vertical='center')

def fmt_ws(ws):
    ws.row_dimensions[1].height = 30
    ws.freeze_panes = 'A2'
    for cell in ws[1]:
        cell.fill = HDR_FILL; cell.font = HDR_FONT; cell.alignment = HDR_ALIG

def auto_widths(ws):
    for ci in range(1, ws.max_column+1):
        cl  = get_column_letter(ci)
        hdr = str(ws.cell(1,ci).value or '').lower()
        w   = 28 if any(x in hdr for x in ('nombre','provincia','cadena','barrio','sucursal','localidad')) else (42 if 'desc' in hdr else 14)
        ws.column_dimensions[cl].width = w
        if any(x in hdr for x in ('canasta','precio','ipc','costo','promedio','mediana','prom')):
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=ci, max_col=ci):
                for cell in row: cell.number_format = '#,##0.00'
        elif '%' in hdr:
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=ci, max_col=ci):
                for cell in row: cell.number_format = '+0.00"%"'

out_xls = OUTPUT_DIR / f'canasta_analisis_{ULTIMO_MES}.xlsx'
with pd.ExcelWriter(out_xls, engine='openpyxl') as writer:

    # ── Hoja Evolucion_IPC: todas las canastas + IPC (mediana y promedio) ──────
    _ipc_base = ipc[['mes','ipc_general','ipc_general_var_%',
                      'ipc_alimentos','ipc_alimentos_var_%']].copy()
    _evo = _ipc_base
    for _col_id in CANASTAS_ACTIVAS:
        if len(serie_nac_dict[_col_id]) == 0: continue
        _sn = serie_nac_dict[_col_id][['mes','canasta_nacional_ponderada','variacion_mensual_%',
                                       'canasta_nacional_ponderada_prom','variacion_mensual_prom_%']].copy()
        _n  = CANASTA_SHORT[_col_id]
        _sn = _sn.rename(columns={
            'canasta_nacional_ponderada':      f'canasta_{_n}',
            'variacion_mensual_%':             f'var_{_n}_%',
            'canasta_nacional_ponderada_prom': f'canasta_{_n}_prom',
            'variacion_mensual_prom_%':        f'var_{_n}_prom_%'
        })
        _evo = _evo.merge(_sn, on='mes', how='outer')
    _evo = _evo.sort_values('mes').reset_index(drop=True)
    _evo.to_excel(writer, sheet_name='Evolucion_IPC', index=False)

    # ── Hoja por canasta: Provincias, Ranking y Sucursales ──────────────────────
    for _col_id in CANASTAS_ACTIVAS:
        _name  = CANASTA_NAMES[_col_id]
        _short = CANASTA_SHORT[_col_id]
        _spv   = serie_prov_dict[_col_id].copy()
        _prom      = prom_nac_dict[_col_id]
        _prom_prom = prom_nac_prom_dict[_col_id]
        _spv['vs_promedio_%']      = ((_spv['canasta_total'] / _prom) - 1) * 100
        _spv['vs_promedio_prom_%'] = ((_spv['canasta_total_prom'] / _prom_prom) - 1) * 100
        _spv = _spv[['mes','provincia','canasta_total','vs_promedio_%',
                     'canasta_total_prom','vs_promedio_prom_%']]
        _spv.sort_values('canasta_total').to_excel(
            writer, sheet_name=f'Prov_{_short}', index=False)

        # Ranking por cadena: MEDIANA (mediana por cadena) y PROMEDIO (_pmean por cadena)
        _cgf = canasta_geo_dict[_col_id]
        _rk  = (_cgf.groupby('cadena')
                .agg(n_sucursales=('canasta_total','count'),
                     canasta_mediana=('canasta_total','median'),
                     canasta_prom=('canasta_total_prom', _pmean))
                .reset_index())
        _rk['canasta_mediana'] = _rk['canasta_mediana'].round(0)
        _rk['canasta_prom']    = _rk['canasta_prom'].round(0)
        _rk = _rk.sort_values('canasta_mediana', ascending=False)
        _rk['vs_mediana_%'] = ((_rk['canasta_mediana'] / _prom) - 1) * 100       # vs pais del Cuadro 1
        _rk['vs_prom_%']    = ((_rk['canasta_prom'] / _prom_prom) - 1) * 100
        _rk = _rk[['cadena','n_sucursales','canasta_mediana','vs_mediana_%','canasta_prom','vs_prom_%']]
        _rk.to_excel(writer, sheet_name=f'Ranking_{_short}', index=False)

        _suc_exp = _cgf[[
            'id_comercio','id_bandera','id_sucursal','cadena','PROVINCIA_NORM',
            'sucursales_nombre','sucursales_localidad','sucursales_barrio',
            'sucursales_latitud','sucursales_longitud','sucursales_tipo',
            'canasta_total','canasta_total_prom','productos_propios','amba'
        ]].sort_values(['PROVINCIA_NORM','cadena','canasta_total']).copy()
        _suc_exp.to_excel(writer, sheet_name=f'Sucs_{_short}', index=False)

    # ── Hoja Serie_precios: precio mediano y promedio por canasta x mes x producto ─
    _sp_rows = []
    for _col_id, _canasta in CANASTAS.items():
        _eans = set(_canasta.keys())
        _dh   = df_hist_raw[df_hist_raw['ean_norm'].isin(_eans)].copy()
        _dh['id_producto']  = _dh['ean_norm'].apply(lambda e: e.zfill(13))
        _dh['descripcion']  = _dh['ean_norm'].map(lambda e, c=_canasta: c.get(e,('',0,''))[0])
        _dh['categoria']    = _dh['ean_norm'].map(lambda e, c=_canasta: c.get(e,('',0,'?'))[2])
        _dh['qty']              = _dh['ean_norm'].map(lambda e, c=_canasta: c.get(e,('',0,''))[1])
        _dh['costo_item']       = _dh['precio_mediano'] * _dh['qty']
        _dh['costo_item_prom']  = _dh['precio_medio']   * _dh['qty']
        _dh['canasta_id']   = _col_id
        _dh['canasta_name'] = CANASTA_NAMES[_col_id]
        _sp_rows.append(_dh[['canasta_id','canasta_name','anio_mes',
                              'id_producto','descripcion','categoria',
                              'qty','precio_mediano','costo_item',
                              'precio_medio','costo_item_prom']])
    if _sp_rows:
        _sp_all = pd.concat(_sp_rows, ignore_index=True).sort_values(
            ['canasta_id','id_producto','anio_mes']).reset_index(drop=True)
        _sp_all = _sp_all.rename(columns={'anio_mes':'mes','precio_medio':'precio_prom'})
        _sp_all.to_excel(writer, sheet_name='Serie_precios', index=False)

    # ── Hojas de detalle geografico (canasta MEDIA) — belgrano, Pinamar, costa, CABA ──
    # MISMA fuente que Sucs_Media. Cada hoja trae canasta_mediana y canasta_prom
    # (promedio con outliers fuera), geolocalizando por lat/lon.
    _MID = 'cantidad_03'
    if _MID in canasta_geo_dict:
        _cgm    = canasta_geo_dict[_MID]
        _pais_m = prom_nac_dict[_MID]        # cuadro pais — mediana
        _pais_p = prom_nac_prom_dict[_MID]   # cuadro pais — promedio

        _cgm_caba = _cgm[_cgm['PROVINCIA_NORM'] == 'CABA'].copy()
        _cgm_caba['barrio'] = _cgm_caba.apply(
            lambda r: det_barrio(r['sucursales_latitud'], r['sucursales_longitud']), axis=1)

        # Hoja 'belgrano'
        _bel = _cgm_caba[_cgm_caba['barrio'] == 'Belgrano']
        if len(_bel):
            _bel_g = (_bel.groupby('cadena')
                      .agg(n_sucursales=('canasta_total','count'),
                           canasta_mediana=('canasta_total','median'),
                           canasta_prom=('canasta_total_prom', _pmean))
                      .reset_index().sort_values('canasta_mediana'))
            _bel_g['canasta_mediana'] = _bel_g['canasta_mediana'].round(0)
            _bel_g['canasta_prom']    = _bel_g['canasta_prom'].round(0)
            _bel_g = pd.concat([_bel_g, pd.DataFrame([{
                'cadena': 'Total Belgrano',
                'n_sucursales': int(_bel_g['n_sucursales'].sum()),
                'canasta_mediana': round(_bel['canasta_total'].median(), 0),
                'canasta_prom': round(_pmean(_bel['canasta_total_prom']), 0)}])],
                ignore_index=True)
            _bel_g.to_excel(writer, sheet_name='belgrano', index=False)

        # Hoja 'CABA'
        _caba_rk = (_cgm_caba[_cgm_caba['barrio'] != 'Sin clasificar']
                    .groupby('barrio')
                    .agg(n_sucursales=('canasta_total','count'),
                         canasta_mediana=('canasta_total','median'),
                         canasta_prom=('canasta_total_prom', _pmean))
                    .reset_index())
        _caba_rk = _caba_rk[_caba_rk['n_sucursales'] >= 2].sort_values(
            'canasta_mediana', ascending=False)
        _caba_rk['canasta_mediana'] = _caba_rk['canasta_mediana'].round(0)
        _caba_rk['canasta_prom']    = _caba_rk['canasta_prom'].round(0)
        if len(_caba_rk):
            _caba_rk = pd.concat([_caba_rk, pd.DataFrame([
                {'barrio': 'Promedio CABA',
                 'n_sucursales': int(_caba_rk['n_sucursales'].sum()),
                 'canasta_mediana': round(_cgm_caba['canasta_total'].median(), 0),
                 'canasta_prom': round(_pmean(_cgm_caba['canasta_total_prom']), 0)},
                {'barrio': 'Promedio pais', 'n_sucursales': '',
                 'canasta_mediana': round(_pais_m, 0),
                 'canasta_prom': round(_pais_p, 0)}])], ignore_index=True)
            _caba_rk.to_excel(writer, sheet_name='CABA', index=False)

        # ── Localidades de la Costa Atlantica bonaerense por lat/lon ──────────────
        COSTA_BBOX = {
            'San Clemente':  (-36.44,  -36.32,  -56.80, -56.64),
            'Mar del Tuyu':  (-36.62,  -36.50,  -56.76, -56.62),
            'San Bernardo':  (-36.712, -36.66,  -56.74, -56.61),
            'Mar de Ajo':    (-36.76,  -36.713, -56.74, -56.61),
            'Pinamar':       (-37.19,  -37.05,  -56.94, -56.81),
            'Gesell':        (-37.37,  -37.20,  -57.04, -56.91),
            'Madariaga':     (-37.07,  -36.93,  -57.24, -57.05),
            'Mar del Plata': (-38.13,  -37.87,  -57.74, -57.45),
            'Miramar':       (-38.35,  -38.19,  -57.94, -57.75),
            'Necochea':      (-38.63,  -38.47,  -58.84, -58.62),
        }
        def _det_costa(_lat, _lon):
            if pd.isna(_lat) or pd.isna(_lon): return 'Sin clasificar'
            for _loc, (_a0, _a1, _o0, _o1) in COSTA_BBOX.items():
                if _a0 <= _lat <= _a1 and _o0 <= _lon <= _o1: return _loc
            return 'Sin clasificar'

        _cgm_ba = _cgm[_cgm['PROVINCIA_NORM'] == 'Buenos Aires'].copy()
        _cgm_ba['loc_costa'] = _cgm_ba.apply(
            lambda r: _det_costa(r['sucursales_latitud'], r['sucursales_longitud']), axis=1)

        # Hoja 'Pinamar': una fila por sucursal
        _pin = _cgm_ba[_cgm_ba['loc_costa'] == 'Pinamar']
        if len(_pin):
            _pin_out = (_pin[['cadena','sucursales_nombre','canasta_total','canasta_total_prom']]
                        .rename(columns={'sucursales_nombre':'sucursal',
                                         'canasta_total':'canasta_mediana',
                                         'canasta_total_prom':'canasta_prom'})
                        .sort_values('canasta_mediana'))
            _pin_out['canasta_mediana'] = _pin_out['canasta_mediana'].round(0)
            _pin_out['canasta_prom']    = _pin_out['canasta_prom'].round(0)
            _pin_out = pd.concat([_pin_out, pd.DataFrame([{
                'cadena': 'Total Pinamar', 'sucursal': '',
                'canasta_mediana': round(_pin['canasta_total'].median(), 0),
                'canasta_prom': round(_pmean(_pin['canasta_total_prom']), 0)}])],
                ignore_index=True)
            _pin_out.to_excel(writer, sheet_name='Pinamar', index=False)

        # Hoja 'costa': ranking de localidades
        _costa = _cgm_ba[_cgm_ba['loc_costa'] != 'Sin clasificar']
        if len(_costa):
            _costa_g = (_costa.groupby('loc_costa')
                        .agg(n_sucursales=('canasta_total','count'),
                             canasta_mediana=('canasta_total','median'),
                             canasta_prom=('canasta_total_prom', _pmean))
                        .reset_index().rename(columns={'loc_costa':'localidad'}))
            _costa_g['canasta_mediana'] = _costa_g['canasta_mediana'].round(0)
            _costa_g['canasta_prom']    = _costa_g['canasta_prom'].round(0)
            _costa_g['vs_pais_%']      = (_costa_g['canasta_mediana'] / _pais_m - 1) * 100
            _costa_g['vs_pais_prom_%'] = (_costa_g['canasta_prom'] / _pais_p - 1) * 100
            _costa_g = _costa_g.sort_values('canasta_mediana')
            _costa_g = pd.concat([_costa_g, pd.DataFrame([{
                'localidad': 'Total Costa Atlantica',
                'n_sucursales': int(_costa_g['n_sucursales'].sum()),
                'canasta_mediana': round(_costa['canasta_total'].median(), 0),
                'canasta_prom': round(_pmean(_costa['canasta_total_prom']), 0),
                'vs_pais_%': (_costa['canasta_total'].median() / _pais_m - 1) * 100,
                'vs_pais_prom_%': (_pmean(_costa['canasta_total_prom']) / _pais_p - 1) * 100}])], ignore_index=True)
            _costa_g = _costa_g[['localidad','n_sucursales','canasta_mediana','vs_pais_%','canasta_prom','vs_pais_prom_%']]
            _costa_g.to_excel(writer, sheet_name='costa', index=False)

    # ── Formato ──────────────────────────────────────────────────────────────
    for sn in writer.sheets:
        ws = writer.sheets[sn]
        fmt_ws(ws)
        auto_widths(ws)

print(f'Excel guardado: {out_xls}')
print()
print('='*65)
print(f'  RESUMEN — {NOMBRE_MES_TITLE.upper()}')
print('='*65)
for _col_id in CANASTAS_ACTIVAS:
    _name = CANASTA_NAMES[_col_id]
    _cgf  = canasta_geo_dict[_col_id]
    _prom = prom_nac_dict[_col_id]
    _promp = prom_nac_prom_dict[_col_id]
    _sn   = serie_nac_dict[_col_id]
    _rng  = f'{_sn["mes"].min()} -> {_sn["mes"].max()}' if len(_sn) > 0 else 'sin historia'
    print(f'  [{_name}] {len(_cgf):,} sucs | Mediana: ${_prom:,.0f} | Promedio: ${_promp:,.0f} | Serie: {_rng}')
print('='*65)
if MES_PARCIAL:
    print(f'\\n⚠️  {NOMBRE_MES_TITLE}: MES PARCIAL ({DIAS_CARGADOS}/{DIAS_MES} días).')
    print('    Los promedios son un snapshot al día; la VARIACIÓN mensual es PRELIMINAR')
    print('    (subestimada vs meses completos). Re-correr al cierre del mes para el dato final.')"""))

# ── CELL 19b — DESAGREGACIÓN DE LA VARIACIÓN MENSUAL ──────────────────────────
cells.append(cell_code(r'''# ============================================================
# CELDA 19b — Desagregación de la variación mensual: producto, arrastre, cadena y geografía
# ============================================================
# Reparte la variación mensual oficial (CELDA 9) de cada canasta de DESAGREGAR_CANASTAS
# (CELDA 1) y la agrega como hojas nuevas a canasta_analisis_{PERIODO}.xlsx.
# Serie oficial: canasta(m) = suma de qty x mediana nacional de TODAS las observaciones
# sucursal x día del mes, sin filtros de cadena ni de geografía.
#   - Productos / Rubros / Grupos: aporte_oficial_pp = qty x (mediana del mes - mediana del
#     mes anterior) / canasta del mes anterior. Suma EXACTA a la variación oficial.
#   - Arrastre: mediana de la última semana del mes anterior. arrastre_pp + nuevo_pp = aporte,
#     producto a producto (cuánto de la suba ya estaba en los precios de fin del mes anterior).
#   - Cadenas / Provincias / Regiones / Tipo_sucursal: la mediana nacional no se reparte entre
#     grupos. Panel apareado sucursal x producto (precio mensual = mediana de los días, como la
#     CELDA 7) con los pesos oficiales del mes anterior:
#         aporte = w_i x (p_is - p_is,ant) / suma_s p_is,ant     (w_i = qty_i x med_i,ant / canasta_ant)
#     Es aditivo y suma la variación del panel. aporte_equiv_sobre_oficial_pp lo reescala a la
#     variación oficial; var_mediana_grupo_% es el control con el método oficial dentro del grupo.
# Relee del ZIP el mes anterior y el mes en curso por sucursal x día SOLO con los EANs de las
# canastas a desagregar, en formato compacto (enteros + float64). No usa ni copia `datos` (la
# CELDA 6 filtra sucursales y descarta el día): el universo es el de la CELDA 9.
# Hojas (la Media va sin sufijo; otra canasta lleva _<nombre corto>): Resumen_variacion,
# Productos, Grupos, Rubros, Cadenas, Provincias, Regiones, Tipo_sucursal, Aporte_prod_x_cadena,
# Var_prod_x_cadena, Subas_y_bajas, Mes_parcial y Serie_diaria.
import calendar as _cal
import contextlib

_PAT_DIA = re.compile(r'^precio_(\d{8})$')
_MES_ABR = {1: 'ene', 2: 'feb', 3: 'mar', 4: 'abr', 5: 'may', 6: 'jun',
            7: 'jul', 8: 'ago', 9: 'sep', 10: 'oct', 11: 'nov', 12: 'dic'}
# Provincia = código ISO del SEPA (columna sucursales_provincia del archivo de precios)
_PROV_ISO = {'AR-B': 'Buenos Aires', 'AR-C': 'CABA', 'AR-K': 'Catamarca', 'AR-H': 'Chaco',
             'AR-U': 'Chubut', 'AR-X': 'Córdoba', 'AR-W': 'Corrientes', 'AR-E': 'Entre Ríos',
             'AR-P': 'Formosa', 'AR-Y': 'Jujuy', 'AR-L': 'La Pampa', 'AR-F': 'La Rioja',
             'AR-M': 'Mendoza', 'AR-N': 'Misiones', 'AR-Q': 'Neuquén', 'AR-R': 'Río Negro',
             'AR-A': 'Salta', 'AR-J': 'San Juan', 'AR-D': 'San Luis', 'AR-Z': 'Santa Cruz',
             'AR-S': 'Santa Fe', 'AR-G': 'Santiago del Estero', 'AR-V': 'Tierra del Fuego',
             'AR-T': 'Tucumán'}
# Región = AMBA por coordenadas, la columna amba de la CELDA 7 (CABA + Buenos Aires a <= AMBA_RADIO_KM del
# Obelisco); el resto, por la provincia del archivo de precios (Buenos Aires fuera del AMBA = Pampeana). Sucursales
# que la CELDA 7 no ubica (fuera del maestro, sin coordenadas, web): Buenos Aires no se puede partir entre AMBA y
# Pampeana ('Buenos Aires s/ubicar'); un código de provincia desconocido queda 'Sin dato'.
_REGION_PROV = {'CABA': 'AMBA', 'Córdoba': 'Pampeana', 'Entre Ríos': 'Pampeana', 'La Pampa': 'Pampeana',
                'Santa Fe': 'Pampeana', 'Catamarca': 'Noroeste', 'Jujuy': 'Noroeste',
                'La Rioja': 'Noroeste', 'Salta': 'Noroeste', 'Santiago del Estero': 'Noroeste',
                'Tucumán': 'Noroeste', 'Chaco': 'Noreste', 'Corrientes': 'Noreste',
                'Formosa': 'Noreste', 'Misiones': 'Noreste', 'Mendoza': 'Cuyo', 'San Juan': 'Cuyo',
                'San Luis': 'Cuyo', 'Chubut': 'Patagonia', 'Neuquén': 'Patagonia',
                'Río Negro': 'Patagonia', 'Santa Cruz': 'Patagonia', 'Tierra del Fuego': 'Patagonia'}
_GRUPOS_RUBRO = {
    'Alimentos': ['Lácteos', 'Fiambrería', 'Carnicería', 'Hamburguesas', 'Galletitas', 'Conservas',
                  'Papas Congeladas', 'Aceites', 'Alimentos Congelados', 'Golosinas', 'Harinas',
                  'Infusiones', 'Arroz y Legumbres', 'Azúcar y Edulcorantes', 'Aderezos', 'Cereales',
                  'Pastas Secas', 'Vegetales', 'Sopas Caldos y Puré', 'Snacks'],
    'Bebidas': ['Gaseosas', 'Vinos y Espumantes', 'Isotónicas y Energizantes', 'Bebida Herbal',
                'Cerveza', 'Jugos', 'Aguas'],
    'Limpieza y papeles': ['Lavandina', 'Desodorante de Ambientes', 'Limpieza de Baño', 'Papeles',
                           'Limpieza de Ropa', 'Limpieza de Cocina', 'Limpieza Piso y Muebles',
                           'Accesorios de Limpieza'],
    'Higiene y cuidado personal': ['Cuidado Corporal', 'Cuidado del Cabello', 'Protección Femenina',
                                   'Cuidado Oral', 'Productos Farmacéuticos'],
}
_RUBRO_GRUPO = {_r: _g for _g, _rs in _GRUPOS_RUBRO.items() for _r in _rs}
_HOJAS_DESAG = ['Resumen_variacion', 'Productos', 'Grupos', 'Rubros', 'Cadenas', 'Provincias',
                'Regiones', 'Tipo_sucursal', 'Aporte_prod_x_cadena', 'Var_prod_x_cadena',
                'Subas_y_bajas', 'Mes_parcial', 'Serie_diaria']


def _hoja_desag(_base, _cid):
    return _base if _cid == 'cantidad_03' else f'{_base}_{CANASTA_SHORT[_cid]}'[:31]


def _cadena_desag(_com, _ban):
    # Mismos nombres que asignar_cadena (CELDA 4); las banderas de Carrefour que no están en el
    # diccionario se distinguen en vez de quedar todas como 'Cadena 10'.
    _c = asignar_cadena({'id_comercio': _com, 'id_bandera': _ban})
    return f'Carrefour (bandera {_ban})' if _c == 'Cadena 10' else _c


def _lbl_mes(_ym):
    return f'{_MES_ABR[_ym % 100]}-{str(_ym // 100)[2:]}'


def _leer_mes_desag(_lbl, _eans=None):
    # Observaciones sucursal x día del mes _lbl con los EANs de _EAN_COD (o el subconjunto _eans),
    # sin filtro de sucursales (como la CELDA 9): suc (int32, código de _SUC_COD), ean (int16,
    # código de _EAN_COD), fecha AAAAMMDD (int32) y precio (float64). Registra las sucursales en
    # _SUC_ATR. También lo usa la CELDA 19c para los meses viejos de la hoja analisis_detallado.
    _filtro = _EAN_SET if _eans is None else set(_eans)
    _zip_path, _archs = _mapa_desag[_lbl]
    _partes = []
    for _archivo in sorted(_archs):
        _tmp_p = TMP_DIR / Path(_archivo).name
        with zipfile.ZipFile(_zip_path) as _zf:
            with _zf.open(_archivo) as _s, open(_tmp_p, 'wb') as _d:
                shutil.copyfileobj(_s, _d, length=4*1024*1024)
        with gzip.open(_tmp_p, 'rt', encoding='utf-8', errors='replace') as _g:
            for _ch in pd.read_csv(_g, dtype=str, chunksize=300_000, low_memory=False):
                # normalizar_ean (CELDA 5), como las CELDAS 6 y 9. NO usar .str.strip().str.lstrip('0'):
                # sobre el chunk de 300k filas lleva el pico de RAM de +0,2 a +2,1 GB (medido, oct-26).
                _ean = _ch['id_producto'].apply(normalizar_ean)
                _sel = _ean.isin(_filtro)
                if not _sel.any(): continue
                _ch, _ean = _ch[_sel], _ean[_sel]
                _cols_p = [c for c in _ch.columns if _PAT_DIA.match(c)]
                if not _cols_p: continue
                _k = (_ch['id_comercio'].astype(str) + '|' + _ch['id_bandera'].astype(str)
                      + '|' + _ch['id_sucursal'].astype(str))
                _pv = (_ch['sucursales_provincia'] if 'sucursales_provincia' in _ch.columns
                       else pd.Series(np.nan, index=_ch.index))
                for _kk, _p in (pd.DataFrame({'k': _k.values, 'p': _pv.values})
                                .drop_duplicates().itertuples(index=False)):
                    _c = _SUC_COD.get(_kk)
                    if _c is None:
                        _SUC_COD[_kk] = len(_SUC_ATR)
                        _SUC_ATR.append(_kk.split('|') + [_p])
                    elif pd.isna(_SUC_ATR[_c][3]) and not pd.isna(_p):
                        _SUC_ATR[_c][3] = _p
                _pr = _ch[_cols_p].apply(pd.to_numeric, errors='coerce').to_numpy(dtype='float64')
                _fi, _ci = np.nonzero(_pr > 0)
                _dias = np.array([int(c[7:]) for c in _cols_p], dtype='int32')
                _partes.append(pd.DataFrame({
                    'suc': _k.map(_SUC_COD).to_numpy(dtype='int32')[_fi],
                    'ean': _ean.map(_EAN_COD).to_numpy(dtype='int16')[_fi],
                    'fecha': _dias[_ci], 'precio': _pr[_fi, _ci]}))
        _tmp_p.unlink(missing_ok=True)
    if not _partes:
        raise RuntimeError(f'Sin observaciones de las canastas a desagregar en {_lbl}')
    _o = pd.concat(_partes, ignore_index=True)
    del _partes
    # Pesos o centavos: se sigue a la CELDA 9 (la mediana reproducida ~100x la oficial = centavos)
    _rep = _o.groupby('ean')['precio'].median()
    _ofi = pd.Series({_EAN_COD[e]: v for e, v in (_MED_OFI[_lbl].items() if _lbl in _MED_OFI.columns else [])
                      if e in _EAN_COD and pd.notna(v)}, dtype='float64')
    _rat = (_rep / _ofi.reindex(_rep.index)).median()
    if (_rat > 10) if pd.notna(_rat) else (_o['precio'].median() > 10_000):
        _o['precio'] /= 100
    print(f'  {_lbl}: {len(_o):,} observaciones sucursal x día | {_o["suc"].nunique():,} sucursales | '
          f'{_o["ean"].nunique()} EANs')
    return _o


def _atributos_sucursal():
    # Cadena, provincia, región y tipo de cada sucursal registrada (índice = código de _SUC_COD)
    _s = pd.DataFrame(_SUC_ATR, columns=['id_comercio', 'id_bandera', 'id_sucursal', 'prov_iso'])
    _k = _s['id_comercio'] + '|' + _s['id_bandera'] + '|' + _s['id_sucursal']
    _ms = (maestro_suc.assign(_k=maestro_suc['id_comercio'] + '|' + maestro_suc['id_bandera']
                              + '|' + maestro_suc['id_sucursal'])
           .drop_duplicates('_k').set_index('_k'))
    _s['cadena'] = [_cadena_desag(c, b) for c, b in zip(_s['id_comercio'], _s['id_bandera'])]
    _s['provincia'] = _s['prov_iso'].astype(str).map(_PROV_ISO).fillna('Sin dato')
    # Región (BUG-43): AMBA = columna amba de la CELDA 7 (CABA + Buenos Aires a <= AMBA_RADIO_KM del Obelisco),
    # el mismo AMBA del Cuadro 1, los rankings y Valores_Documento. El resto, por la provincia del archivo de precios
    # (la de la dimensión provincia de esta hoja; Buenos Aires fuera del AMBA = Pampeana). NO se usa la REGION del
    # maestro (marca AMBA a ~100 DIA del interior bonaerense) ni la provincia reclasificada de la CELDA 7 (sus
    # rectángulos pasan Neuquén capital a La Pampa y Paraná a Santa Fe, BUG-44). Sin coordenadas en la CELDA 7:
    # Buenos Aires queda 'Buenos Aires s/ubicar'.
    _geo = (suc_geo_clean.assign(_k=suc_geo_clean['id_comercio'] + '|' + suc_geo_clean['id_bandera']
                                 + '|' + suc_geo_clean['id_sucursal'])
            .drop_duplicates('_k').set_index('_k'))
    _amba = _k.map(_geo['amba'])                  # True / False; NaN = la CELDA 7 no la ubica
    _ubic, _en_amba = _amba.notna().values, _amba.eq(True).values
    _s['region'] = _s['provincia'].map({**_REGION_PROV, 'Buenos Aires': 'Pampeana'}).fillna('Sin dato')
    _s.loc[_ubic & _en_amba, 'region'] = 'AMBA'
    _s.loc[_ubic & ~_en_amba & _s['region'].eq('AMBA').values, 'region'] = 'Pampeana'   # CABA en el archivo, ubicada fuera
    _s.loc[~_ubic & _s['provincia'].eq('Buenos Aires').values, 'region'] = 'Buenos Aires s/ubicar'
    _tipo = (_ms['sucursales_tipo'].astype(str).str.strip().str.title().replace(
                 {'Tienda Fisica': 'Tienda física', 'Web': 'Web/virtual', 'Tienda Virtual': 'Web/virtual'})
             if 'sucursales_tipo' in _ms.columns else pd.Series(dtype=str))
    _s['tipo'] = _k.map(_tipo).fillna('Sin dato en maestro')
    _s['en_maestro'] = _k.isin(_ms.index).values
    return _s


def _desagregar(_cid):
    _name, _can = CANASTA_NAMES[_cid], CANASTAS[_cid]

    # ── Canasta oficial (CELDA 9): mediana nacional por producto, mes anterior y mes en curso ──
    _dos = _MED_OFI[[_MES_ANT, PERIODO]].dropna(how='all')
    _eans = [e for e in _can if e in _dos.index]
    prod = pd.DataFrame({'descripcion': [_can[e][0] for e in _eans],
                         'categoria': [_can[e][2] for e in _eans],
                         'qty': [_can[e][1] for e in _eans],
                         'med_ant': _MED_OFI.loc[_eans, _MES_ANT].values,
                         'med_act': _MED_OFI.loc[_eans, PERIODO].values},
                        index=pd.Index([e.zfill(13) for e in _eans], name='id_producto'))
    _sin_grupo = sorted(set(prod.loc[~prod['categoria'].isin(list(_RUBRO_GRUPO)), 'categoria']))
    if _sin_grupo:
        print(f'  AVISO [{_name}]: rubros sin grupo, van a "Otros": {_sin_grupo}')
    prod['grupo'] = prod['categoria'].map(_RUBRO_GRUPO).fillna('Otros')
    prod['costo_ant'] = prod['qty'] * prod['med_ant']
    prod['costo_act'] = prod['qty'] * prod['med_act']
    T0, T1 = prod['costo_ant'].sum(), prod['costo_act'].sum()
    V_OF = (T1 / T0 - 1) * 100
    _sn = serie_nac_dict.get(_cid)
    _v9 = (_sn.set_index('mes')['variacion_mensual_%'].get(PERIODO)
           if _sn is not None and len(_sn) else None)
    if _v9 is not None and pd.notna(_v9) and abs(_v9 - V_OF) > 1e-6:
        print(f'  AVISO [{_name}]: variación recalculada {V_OF:+.4f}% distinta de la CELDA 9 ({_v9:+.4f}%)')
    _incomp = int(prod[['med_ant', 'med_act']].isna().any(axis=1).sum())
    if _incomp:
        # El aporte de un producto con precio en un solo mes es su costo entero (la serie oficial
        # también lo suma en un mes y no en el otro): la suma sigue siendo exacta.
        print(f'  AVISO [{_name}]: {_incomp} productos con precio en un solo mes (efecto composición)')
    prod['w'] = (prod['costo_ant'] / T0).fillna(0)
    prod['peso_%'] = prod['w'] * 100
    prod['var_mediana_%'] = (prod['med_act'] / prod['med_ant'] - 1) * 100
    prod['aporte_oficial_pp'] = (prod['costo_act'].fillna(0) - prod['costo_ant'].fillna(0)) / T0 * 100

    # ── Observaciones de la canasta (códigos de EAN -> id_producto) ──────────
    _cod = np.array([_EAN_COD[e] for e in _eans], dtype='int16')
    _id_de = pd.Series(prod.index.values, index=_cod)
    _qty_de = pd.Series(prod['qty'].values, index=_cod)
    _m = np.isin(_OBS['ean'].values, _cod)
    o = _OBS if _m.all() else _OBS[_m]
    _ym = o['fecha'].values // 100
    _fc = o['fecha'].values

    # Control: la mediana nacional se reproduce con estas observaciones
    _rep = (o.groupby([o['ean'].values, _ym])['precio'].median().unstack()
            .reindex(columns=[_YM_ANT, _YM_ACT]))
    _rep.index = _id_de.reindex(_rep.index).values
    _rep = _rep.reindex(prod.index)
    _igual = pd.Series(True, index=prod.index)
    for _yc, _mc in ((_YM_ANT, 'med_ant'), (_YM_ACT, 'med_act')):
        _igual &= ((_rep[_yc] - prod[_mc]).abs() <= 0.005) | (_rep[_yc].isna() & prod[_mc].isna())
    N_REP = int(_igual.sum())

    # ── Arrastre: mediana de la última semana del mes anterior ───────────────
    _N = _cal.monthrange(_YM_ANT // 100, _YM_ANT % 100)[1]
    _D = int(_fc[_ym == _YM_ACT].max() % 100)
    _ACT_COMPLETO = _D >= _cal.monthrange(_YM_ACT // 100, _YM_ACT % 100)[1]
    _w = (_fc >= _YM_ANT * 100 + _N - 6) & (_fc <= _YM_ANT * 100 + _N)
    _mcie = o['precio'][_w].groupby(o['ean'].values[_w]).median()
    _mcie.index = _id_de.reindex(_mcie.index).values
    prod['med_cierre_ant'] = _mcie.reindex(prod.index)
    prod['arrastre_pp'] = (prod['qty'] * (prod['med_cierre_ant'] - prod['med_ant']) / T0 * 100).fillna(0)
    prod['nuevo_pp'] = prod['qty'] * (prod['med_act'] - prod['med_cierre_ant']) / T0 * 100
    _res = prod['nuevo_pp'].isna()      # sin precio en alguno de los tres tramos: el resto del aporte
    prod.loc[_res, 'nuevo_pp'] = prod.loc[_res, 'aporte_oficial_pp'] - prod.loc[_res, 'arrastre_pp']
    T_CIE = (prod['qty'] * prod['med_cierre_ant']).sum()
    ARR, NUE = prod['arrastre_pp'].sum(), prod['nuevo_pp'].sum()

    # ── Panel apareado sucursal x producto (precio mensual = mediana de los días) ──
    _pm = (o.groupby([o['suc'].values, o['ean'].values, _ym])['precio'].median().unstack()
           .reindex(columns=[_YM_ANT, _YM_ACT]))
    _pm.columns = ['p_ant', 'p_act']
    _pm.index.names = ['suc', 'ean']
    N_PARES = len(_pm)
    _pm = _pm.dropna()
    _r = _pm['p_act'] / _pm['p_ant']
    _fuera = (_r < 0.25) | (_r > 4)
    N_FUERA = int(_fuera.sum())
    p = _pm[~_fuera].reset_index()
    del _pm, _r, _fuera
    p['id_producto'] = _id_de.reindex(p['ean']).values
    p = p.merge(prod[['w', 'qty', 'descripcion', 'categoria', 'grupo']],
                left_on='id_producto', right_index=True)
    for _c in ['cadena', 'provincia', 'region', 'tipo']:
        p[_c] = _SUC[_c].values[p['suc'].values]
    _S0 = p.groupby('id_producto')['p_ant'].transform('sum')
    p['peso_par'] = p['w'] * p['p_ant'] / _S0 * 100              # suma 100 sobre el panel
    p['aporte_pp'] = p['w'] * (p['p_act'] - p['p_ant']) / _S0 * 100
    p['cambio'] = np.select([p['p_act'] > p['p_ant'], p['p_act'] < p['p_ant']], ['sube', 'baja'], 'igual')
    V_PAN = p['aporte_pp'].sum()

    def _var_mediana(_col):
        # Método oficial (mediana de las observaciones) dentro del grupo; productos con dato en
        # los dos meses. No es aditivo: es el control.
        _cat = pd.Categorical(_SUC[_col])
        _gk = _cat.codes[o['suc'].values]
        _mg = (o.groupby([_gk, o['ean'].values, _ym])['precio'].median().unstack()
               .reindex(columns=[_YM_ANT, _YM_ACT]).dropna())
        _q = _qty_de.reindex(_mg.index.get_level_values(1)).values
        _g = pd.DataFrame({'q0': _q * _mg[_YM_ANT].values, 'q1': _q * _mg[_YM_ACT].values},
                          index=_mg.index.get_level_values(0))
        _g = _g.groupby(level=0).agg(q0=('q0', 'sum'), q1=('q1', 'sum'), productos_apareados=('q0', 'size'))
        _g['var_mediana_grupo_%'] = (_g['q1'] / _g['q0'] - 1) * 100
        _g.index = _cat.categories[_g.index]
        return _g[['var_mediana_grupo_%', 'productos_apareados']]

    def _corte(_col):
        _g = p.groupby(_col).agg(sucursales=('suc', 'nunique'), pares=('suc', 'size'),
                                 peso_base_pct=('peso_par', 'sum'), aporte_pp=('aporte_pp', 'sum'))
        _g['variacion_%'] = _g['aporte_pp'] / _g['peso_base_pct'] * 100
        _g['pct_del_aumento'] = _g['aporte_pp'] / V_PAN * 100
        _g['aporte_equiv_sobre_oficial_pp'] = _g['pct_del_aumento'] / 100 * V_OF
        _sb = p.assign(sube=p['cambio'].eq('sube'), baja=p['cambio'].eq('baja'))
        _g['pct_precios_suben'] = _sb.groupby(_col)['sube'].mean() * 100
        _g['pct_precios_bajan'] = _sb.groupby(_col)['baja'].mean() * 100
        _g = _g.join(_var_mediana(_col)).sort_values('aporte_pp', ascending=False)
        # peso_base_pct del TOTAL = 100 salvo que algún producto no tenga pares (desapareció en el mes)
        _tot = pd.DataFrame([{'sucursales': p['suc'].nunique(), 'pares': len(p), 'peso_base_pct': p['peso_par'].sum(),
                              'aporte_pp': V_PAN, 'variacion_%': V_PAN, 'pct_del_aumento': 100.0,
                              'aporte_equiv_sobre_oficial_pp': V_OF,
                              'pct_precios_suben': p['cambio'].eq('sube').mean() * 100,
                              'pct_precios_bajan': p['cambio'].eq('baja').mean() * 100,
                              'var_mediana_grupo_%': V_OF, 'productos_apareados': len(prod)}],
                            index=['TOTAL'])
        return pd.concat([_g, _tot]).rename_axis(_col).reset_index()

    cortes = {_c: _corte(_c) for _c in ['cadena', 'provincia', 'region', 'tipo']}

    # ── Productos: oficial + panel ────────────────────────────────────────────
    _pp = p.groupby('id_producto').agg(sucursales_apareadas=('suc', 'size'),
                                       aporte_panel_pp=('aporte_pp', 'sum'),
                                       pct_suben=('cambio', lambda s: (s == 'sube').mean() * 100),
                                       pct_bajan=('cambio', lambda s: (s == 'baja').mean() * 100))
    prod = prod.join(_pp)
    prod['var_media_sucursales_%'] = prod['aporte_panel_pp'] / prod['peso_%'] * 100
    prod['pct_del_aumento_oficial'] = prod['aporte_oficial_pp'] / V_OF * 100
    prod = prod.sort_values('aporte_oficial_pp', ascending=False)

    _agg = dict(productos=('qty', 'size'), peso_pct=('peso_%', 'sum'),
                aporte_oficial_pp=('aporte_oficial_pp', 'sum'), aporte_panel_pp=('aporte_panel_pp', 'sum'))
    rub = prod.groupby(['grupo', 'categoria']).agg(**_agg).reset_index()
    rub['variacion_mediana_%'] = rub['aporte_oficial_pp'] / rub['peso_pct'] * 100
    rub['pct_del_aumento'] = rub['aporte_oficial_pp'] / V_OF * 100
    rub = rub.merge(prod.groupby('categoria')[['arrastre_pp', 'nuevo_pp']].sum(),
                    left_on='categoria', right_index=True).sort_values('aporte_oficial_pp', ascending=False)
    gru = prod.groupby('grupo').agg(**_agg).reset_index()
    gru['variacion_mediana_%'] = gru['aporte_oficial_pp'] / gru['peso_pct'] * 100
    gru['variacion_panel_%'] = gru['aporte_panel_pp'] / gru['peso_pct'] * 100
    gru['pct_del_aumento'] = gru['aporte_oficial_pp'] / V_OF * 100
    gru = gru.merge(prod.groupby('grupo')[['arrastre_pp', 'nuevo_pp']].sum(),
                    left_on='grupo', right_index=True).sort_values('aporte_oficial_pp', ascending=False)

    # ── Producto x cadena: aporte en el panel (pp) y variación media de sucursales (%) ──
    _top = cortes['cadena'].query('cadena != "TOTAL"').head(12)['cadena'].tolist()
    _pc = p.assign(cad=np.where(p['cadena'].isin(_top), p['cadena'], 'Resto'))
    pxc = _pc.pivot_table(index='id_producto', columns='cad', values='aporte_pp', aggfunc='sum', fill_value=0)
    pxc = pxc[[c for c in _top + ['Resto'] if c in pxc.columns]]
    pxc['TOTAL'] = pxc.sum(axis=1)
    pxc = prod[['descripcion']].join(pxc).fillna(0).sort_values('TOTAL', ascending=False)
    vxc = (_pc.groupby(['id_producto', 'cad'])[['p_ant', 'p_act']].sum()
           .pipe(lambda d: (d['p_act'] / d['p_ant'] - 1) * 100).unstack())
    vxc = vxc[[c for c in _top + ['Resto'] if c in vxc.columns]]
    vxc = prod[['descripcion', 'var_mediana_%']].join(vxc).loc[pxc.index]
    del _pc

    # ── Frecuencia e intensidad de los cambios ────────────────────────────────
    fr = p.groupby('cambio').agg(pares=('suc', 'size'), peso_base_pct=('peso_par', 'sum'),
                                 aporte_pp=('aporte_pp', 'sum'))
    fr['pct_pares'] = fr['pares'] / len(p) * 100
    _rel = (p['p_act'] / p['p_ant'] - 1) * 100
    fr['cambio_medio_%'] = _rel.groupby(p['cambio']).mean()
    fr['cambio_mediano_%'] = _rel.groupby(p['cambio']).median()
    fr = fr.reindex(['sube', 'igual', 'baja']).rename_axis('cambio').reset_index()

    # ── Mes parcial: ventanas de días y arrastre ──────────────────────────────
    def _canasta_vent(_d0, _d1):
        _v = (_fc >= _d0) & (_fc <= _d1)
        _mv = o['precio'][_v].groupby(o['ean'].values[_v]).median()
        _mv.index = _id_de.reindex(_mv.index).values
        return (prod['qty'] * _mv).sum(), int(_mv.notna().sum())

    _A, _B = _MES_ABR[_YM_ANT % 100].title(), _MES_ABR[_YM_ACT % 100].title()
    _a0, _a1 = _YM_ANT * 100 + 1, _YM_ANT * 100 + _N
    _c0, _c1 = _YM_ACT * 100 + 1, _YM_ACT * 100 + _D
    _vents = [(f'{_A} completo (1-{_N}) vs {_B} 1-{_D}  [oficial nb02]', (_a0, _a1), (_c0, _c1))]
    if _D < _N:
        _vents += [(f'{_A} 1-{_D} vs {_B} 1-{_D}  [mismos dias, un mes]', (_a0, _a0 + _D - 1), (_c0, _c1)),
                   (f'{_A} {_D + 1}-{_N} vs {_B} 1-{_D}  [periodos consecutivos]', (_a0 + _D, _a1), (_c0, _c1)),
                   (f'{_A} 1-{_D} vs {_A} {_D + 1}-{_N}  [dentro de {_A}]', (_a0, _a0 + _D - 1), (_a0 + _D, _a1))]
    vent = []
    for _nom, _ini, _fin in _vents:
        (_k0, _n0), (_k1, _n1) = _canasta_vent(*_ini), _canasta_vent(*_fin)
        vent.append({'comparacion': _nom, 'canasta_inicio': _k0, 'canasta_fin': _k1,
                     'variacion_%': (_k1 / _k0 - 1) * 100, 'productos': min(_n0, _n1)})
    vent += [{'comparacion': f'Arrastre: {_A} completo vs ultima semana de {_A} ({_N - 6}-{_N})',
              'canasta_inicio': T0, 'canasta_fin': T_CIE, 'variacion_%': ARR, 'productos': len(prod)},
             {'comparacion': f'Suba nueva: ultima semana de {_A} ({_N - 6}-{_N}) vs {_B} 1-{_D}, '
                             f'en pp sobre la canasta de {_A}',
              'canasta_inicio': T_CIE, 'canasta_fin': T1, 'variacion_%': NUE, 'productos': len(prod)}]
    vent = pd.DataFrame(vent)

    # ── Serie diaria con el método oficial (mediana nacional del día) ─────────
    _dd = o.groupby([_fc, o['ean'].values])['precio'].median().unstack()
    _dd.columns = _id_de.reindex(_dd.columns).values
    diaria = pd.DataFrame({'canasta': (_dd * prod['qty']).sum(axis=1),
                           'productos_con_dato': _dd.notna().sum(axis=1),
                           'observaciones': pd.Series(_fc).value_counts()}).sort_index()
    diaria['indice_mes_ant_completo=100'] = diaria['canasta'] / T0 * 100
    diaria.insert(0, 'dia', pd.to_datetime(diaria.index.astype(str), format='%Y%m%d'))
    diaria = diaria.reset_index(drop=True)

    # ── Resumen ───────────────────────────────────────────────────────────────
    _m0 = _lbl_mes(_YM_ANT)
    _m1 = _lbl_mes(_YM_ACT) + ('' if _ACT_COMPLETO else f' al {_D}/{_YM_ACT % 100}')
    res = [
        (f'Canasta {_name} {_m0} (nb02)', T0), (f'Canasta {_name} {_m1} (nb02)', T1),
        ('Variacion oficial nb02 (%)', V_OF),
        ('Variacion panel apareado, media de sucursales, pesos oficiales (%)', V_PAN),
        ('Diferencia oficial - panel (efecto mediana / composicion, pp)', V_OF - V_PAN),
        (f'Arrastre: suba ya presente en la ultima semana de {_m0} (pp)', ARR),
        (f'Suba nueva entre fin de {_m0} y {_m1} (pp)', NUE),
        ('Aporte en el panel de los productos con mediana sin cambio (pp)',
         prod.loc[prod['var_mediana_%'] == 0, 'aporte_panel_pp'].sum()),
        ('Productos en la canasta', len(prod)),
        ('Productos con mediana sin cambio', int((prod['var_mediana_%'] == 0).sum())),
        ('Productos con mediana en baja', int((prod['var_mediana_%'] < 0).sum())),
        ('Aporte de los 5 productos que mas suman (pp)', prod.head(5)['aporte_oficial_pp'].sum()),
        ('Aporte de los 10 productos que mas suman (pp)', prod.head(10)['aporte_oficial_pp'].sum()),
        ('Sucursales en el panel', p['suc'].nunique()),
        ('Pares sucursal-producto apareados', len(p)),
        ('Pares descartados por banda [1/4, 4]', N_FUERA),
        ('% de precios (sucursal-producto) que subieron', p['cambio'].eq('sube').mean() * 100),
        ('% de precios que bajaron', p['cambio'].eq('baja').mean() * 100),
        ('% de precios sin cambio', p['cambio'].eq('igual').mean() * 100),
        ('Productos con la mediana de la CELDA 9 reproducida (control)', N_REP),
    ]
    resumen = pd.DataFrame(res, columns=['indicador', 'valor'])
    notas = pd.DataFrame({'nota': [
        f'Fuente: serie oficial del nb02 (CELDA 9, canasta {_name} = {_cid}) y observaciones sucursal x dia '
        f'del SEPA de {_m0} y {_m1}.' + ('' if _ACT_COMPLETO else f' {_B} es PARCIAL (1-{_D}).'),
        'Variacion oficial: la del nb02 (CELDA 9): suma de qty x mediana nacional de todas las observaciones '
        'sucursal x dia del mes.',
        'Productos y rubros: aporte_oficial_pp = qty x (mediana del mes - mediana del mes anterior) / canasta '
        'del mes anterior. Suma exacta a la variacion oficial.',
        'Cadenas, provincias, regiones y tipo: la mediana nacional no se puede repartir entre grupos. Se usa el '
        'panel apareado sucursal x producto (precio mensual por sucursal = mediana de los dias, como la CELDA 7 '
        'del nb02), con los pesos oficiales del mes anterior por producto. aporte = w_producto x (p_mes - p_ant) '
        '/ suma de p_ant del producto en todas las sucursales. Es aditivo: los grupos suman la variacion del panel.',
        f'pct_del_aumento = aporte del grupo / variacion del panel. aporte_equiv_sobre_oficial_pp reparte la '
        f'variacion oficial ({V_OF:.2f}%) con esas proporciones.',
        'peso_base_pct = participacion del grupo en el costo base (cuanto pesan sus sucursales). variacion_% = '
        'aporte / peso: cuanto subio la canasta en ese grupo.',
        'var_mediana_grupo_% = el metodo oficial aplicado solo a las observaciones del grupo (productos con dato '
        'en ambos meses). No es aditivo, sirve de control.',
        'Las sucursales pesan por igual dentro de cada producto (como la mediana nacional, que pesa por cantidad '
        'de observaciones): las cadenas con muchas sucursales pesan mas.',
        'Arrastre: la mediana del mes anterior es un promedio del mes; si los precios subieron en la segunda '
        'quincena, el mes arranca mas arriba aunque no haya subas nuevas. arrastre_pp = qty x (mediana de la '
        'ultima semana del mes anterior - mediana del mes anterior) / canasta del mes anterior; nuevo_pp = qty x '
        '(mediana del mes - mediana de la ultima semana del mes anterior) / canasta del mes anterior. Suman el '
        'aporte oficial producto a producto.',
        'Region: AMBA = CABA + Buenos Aires a <= 90 km del Obelisco por coordenadas (columna amba de la CELDA 7, '
        'la misma del Cuadro 1 y los rankings); el resto por la provincia del archivo de precios (Buenos Aires fuera '
        'del AMBA: Pampeana; sin coordenadas: "Buenos Aires s/ubicar").',
    ]})

    _cols_prod = ['descripcion', 'grupo', 'categoria', 'qty', 'med_ant', 'med_act', 'var_mediana_%', 'peso_%',
                  'aporte_oficial_pp', 'pct_del_aumento_oficial', 'med_cierre_ant', 'arrastre_pp', 'nuevo_pp',
                  'sucursales_apareadas', 'pct_suben', 'pct_bajan', 'var_media_sucursales_%', 'aporte_panel_pp']
    hojas = {'Productos': prod[_cols_prod].reset_index(), 'Grupos': gru, 'Rubros': rub,
             'Cadenas': cortes['cadena'], 'Provincias': cortes['provincia'], 'Regiones': cortes['region'],
             'Tipo_sucursal': cortes['tipo'], 'Aporte_prod_x_cadena': pxc.reset_index(),
             'Var_prod_x_cadena': vxc.reset_index(), 'Subas_y_bajas': fr, 'Mes_parcial': vent,
             'Serie_diaria': diaria}
    tot = {'T0': T0, 'T1': T1, 'V_OF': V_OF, 'V_PAN': V_PAN, 'ARR': ARR, 'NUE': NUE, 'N_REP': N_REP,
           'N_PROD': len(prod), 'N_SUC': p['suc'].nunique(), 'N_PARES': len(p), 'N_FUERA': N_FUERA,
           'meses': (_m0, _m1)}
    return {'resumen': resumen, 'notas': notas, 'hojas': hojas, 'totales': tot}


def _fmt_desag(ws):
    fmt_ws(ws)      # encabezado como el resto del Excel (CELDA 19)
    for _col in ws.columns:
        _ancho = max([len(str(_col[0].value or ''))] +
                     [len(f'{c.value:.2f}') if isinstance(c.value, float) else len(str(c.value or ''))
                      for c in _col[1:60]])
        ws.column_dimensions[_col[0].column_letter].width = min(_ancho + 2, 60)
        for c in _col[1:]:
            if isinstance(c.value, float):
                c.number_format = '#,##0' if abs(c.value) >= 1000 else '0.000'


# ── Ejecución ─────────────────────────────────────────────────────────────────
desag_dict = {}
_OBS = None          # mes anterior + mes en curso por sucursal x día; lo usa también la CELDA 19c
_DESAG = [c for c in DESAGREGAR_CANASTAS if c in CANASTAS]
_DET = DETALLE_CANASTA if DETALLE_CANASTA in CANASTAS else None     # hoja analisis_detallado (19c)
_LEER = _DESAG + ([_DET] if _DET and _DET not in _DESAG else [])
_MES_ANT = str(pd.Period(PERIODO, freq='M') - 1)
_YM_ANT, _YM_ACT = int(_MES_ANT.replace('-', '')), int(PERIODO.replace('-', ''))
_mapa_desag = {}
for _zp, _an, _sm in detectar_semestres():
    for (_am, _mm), _archs in archivos_por_mes(_zp).items():
        _mapa_desag[f'{_am}-{_mm:02d}'] = (_zp, _archs)
# Mediana oficial (CELDA 9) por EAN x mes, todos los meses (la 19c usa los viejos)
_MED_OFI = df_hist_raw.groupby(['ean_norm', 'anio_mes'])['precio_mediano'].first().unstack()
for _c in (_MES_ANT, PERIODO):
    if _c not in _MED_OFI.columns:
        _MED_OFI[_c] = np.nan

if not _LEER:
    print('DESAGREGAR_CANASTAS vacía y DETALLE_CANASTA sin canasta activa: no se desagrega la variación.')
elif _MES_ANT not in _mapa_desag or _MED_OFI[_MES_ANT].isna().all():
    print(f'AVISO: falta el mes anterior ({_MES_ANT}) en los ZIPs o en la serie: no se desagrega la variación.')
else:
    _EAN_COD = {e: i for i, e in enumerate(sorted(set().union(*[set(CANASTAS[c]) for c in _LEER])))}
    _EAN_SET = set(_EAN_COD)
    _SUC_COD, _SUC_ATR = {}, []
    print(f'Desagregación {_lbl_mes(_YM_ANT)} -> {_lbl_mes(_YM_ACT)}: '
          f'{", ".join(CANASTA_NAMES[c] for c in _LEER)} ({len(_EAN_COD)} EANs)')
    _OBS = pd.concat([_leer_mes_desag(_MES_ANT), _leer_mes_desag(PERIODO)], ignore_index=True)
    _SUC = _atributos_sucursal()
    print(f'  {len(_OBS):,} observaciones en memoria ({_OBS.memory_usage(deep=True).sum() / 1e6:,.0f} MB) | '
          f'{len(_SUC):,} sucursales ({_SUC["en_maestro"].sum():,} en el maestro)')
    for _cid in _DESAG:
        desag_dict[_cid] = _desagregar(_cid)
    if _DET is None:            # sin hoja analisis_detallado: se libera ya
        _OBS = None
    gc.collect()

    _out_desag = OUTPUT_DIR / f'canasta_analisis_{ULTIMO_MES}.xlsx'
    _modo = dict(mode='a', if_sheet_exists='overlay') if _out_desag.exists() else dict(mode='w')
    with (pd.ExcelWriter(_out_desag, engine='openpyxl', **_modo) if desag_dict else contextlib.nullcontext()) as _xw:
        for _cid, _dz in desag_dict.items():
            _nombres = {h: _hoja_desag(h, _cid) for h in _HOJAS_DESAG}
            for _sh in _nombres.values():           # re-correr la celda reemplaza sus hojas
                if _sh in _xw.book.sheetnames:
                    del _xw.book[_sh]
            _dz['resumen'].to_excel(_xw, sheet_name=_nombres['Resumen_variacion'], index=False)
            _dz['notas'].to_excel(_xw, sheet_name=_nombres['Resumen_variacion'], index=False,
                                  startrow=len(_dz['resumen']) + 2)
            for _h, _df in _dz['hojas'].items():
                _df.to_excel(_xw, sheet_name=_nombres[_h], index=False)
            for _sh in _nombres.values():
                _fmt_desag(_xw.book[_sh])
            _xw.book[_nombres['Resumen_variacion']].column_dimensions['A'].width = 70
    if desag_dict:
        print(f'Hojas de la desagregación agregadas a: {_out_desag.name}')

    for _cid, _dz in desag_dict.items():
        _t, _hj = _dz['totales'], _dz['hojas']
        print(f'\n=== {CANASTA_NAMES[_cid]}: {_t["meses"][0]} -> {_t["meses"][1]} ===')
        print(f'  Oficial (CELDA 9): {_t["V_OF"]:+.3f}%  (${_t["T0"]:,.0f} -> ${_t["T1"]:,.0f}) | '
              f'medianas reproducidas {_t["N_REP"]}/{_t["N_PROD"]}')
        print(f'  Arrastre (ultima semana del mes anterior): {_t["ARR"]:+.3f} pp | suba nueva: {_t["NUE"]:+.3f} pp')
        print(f'  Panel apareado (media de sucursales): {_t["V_PAN"]:+.3f}% | {_t["N_SUC"]:,} sucursales, '
              f'{_t["N_PARES"]:,} pares ({_t["N_FUERA"]} fuera de banda)')
        print('\n  Productos que más aportan (pp de la variación oficial):')
        print(_hj['Productos'].head(10)[['descripcion', 'var_mediana_%', 'aporte_oficial_pp',
                                         'arrastre_pp', 'nuevo_pp']].round(3).to_string(index=False))
        print('\n  Grupos:')
        print(_hj['Grupos'][['grupo', 'aporte_oficial_pp', 'arrastre_pp', 'nuevo_pp',
                             'variacion_mediana_%']].round(3).to_string(index=False))
        for _h, _c in (('Cadenas', 'cadena'), ('Regiones', 'region')):
            print(f'\n  {_h} (panel; aporte_equiv = reescalado a la oficial):')
            print(_hj[_h].head(10)[[_c, 'sucursales', 'aporte_pp', 'aporte_equiv_sobre_oficial_pp',
                                    'variacion_%', 'var_mediana_grupo_%']].round(3).to_string(index=False))'''))

# ── CELL 19c — HOJA analisis_detallado ────────────────────────────────────────
cells.append(cell_code(r'''# ============================================================
# CELDA 19c — Hoja 'analisis_detallado': índices y variaciones por rubro, región, provincia,
#             cadena y tipo de sucursal (queda como PRIMERA hoja del Excel)
# ============================================================
# Para la canasta DETALLE_CANASTA (CELDA 1; default la Media) arma un cuadro tipo informe:
#   filas    = Total, rubros SEPA (Almacén, Frescos, Perfumería...) con sus categorías, regiones,
#              provincias, cadenas (supermercados) y tipos de sucursal;
#   columnas = los últimos DETALLE_MESES meses completos (índice base = el mes anterior al primero
#              = 100, así la última columna menos 100 es la variación interanual), el mes en curso
#              si es parcial, y las semanas del mes anterior y del mes en curso (1S = días 1-7,
#              2S = 8-14, 3S = 15-21, 4S = 22 a fin de mes; del mes en curso, solo las completas).
# Debajo, el mismo cuadro en variación %: mes contra mes anterior, semana contra semana anterior.
# Método (el de la serie oficial, CELDA 9, aplicado a cada fila):
#   - Total: la serie oficial (suma de qty x mediana nacional de TODAS las observaciones del mes).
#   - Rubros y categorías: las mismas medianas nacionales, solo con los productos de la fila.
#   - Regiones, provincias, cadenas y tipos: la mediana de las observaciones sucursal x día del
#     grupo, producto por producto (es la columna de control var_mediana_grupo_% de la CELDA 19b).
#   - Cada eslabón compara solo los productos con precio en los dos períodos (índice encadenado).
#     Con la canasta completa, Total = suma de Pond x índice de los rubros / 100 (Pond = participación
#     en el costo del mes base).
#   - Semana: nivel = índice del mes anterior x (canasta con las medianas de la semana / canasta con
#     las medianas del mes anterior), con las mismas observaciones.
# Datos: el mes anterior y el mes en curso salen de lo que leyó la CELDA 19b (_OBS). Los meses viejos
# se leen del SEPA por sucursal (solo los EANs de la canasta) y se guardan agregados en el caché
# (_cache/detalle_<clave>_v1.parquet): la primera corrida lee DETALLE_MESES + 1 meses, las
# siguientes solo el mes nuevo. La clave cambia con los EANs de la canasta, la región de las
# sucursales (provincia y AMBA de la CELDA 7), el tipo del maestro y los nombres de cadena
# (entonces se relee todo).
import time as _time
from openpyxl import Workbook as _Workbook, load_workbook as _load_workbook
from openpyxl.styles import Font as _Font, PatternFill as _Fill, Alignment as _Align
from openpyxl.utils import get_column_letter as _col_letter

_HOJA_DET = 'analisis_detallado'
_DIMS_DET = [('region', 'Regiones'), ('provincia', 'Provincias'),
             ('cadena', 'Cadenas (supermercados)'), ('tipo', 'Tipo de sucursal')]
_ORDEN_REGION = ['AMBA', 'Pampeana', 'Noroeste', 'Noreste', 'Cuyo', 'Patagonia', 'Buenos Aires s/ubicar',
                 'Sin dato']


def _firma_detalle(_eans):
    # Clave del caché: EANs de la canasta + región (provincia y AMBA de la CELDA 7) + tipo (maestro) + nombres
    # de cadena. Desde la región por coordenadas (2026-10-16) la REGION del maestro no entra.
    _cols = ['id_comercio', 'id_bandera', 'id_sucursal'] + [c for c in ('sucursales_tipo',)
                                                           if c in maestro_suc.columns]
    _geo = suc_geo_clean[['id_comercio', 'id_bandera', 'id_sucursal', 'PROVINCIA_NORM', 'amba']].astype(str)
    _txt = (maestro_suc[_cols].astype(str).sort_values(_cols).to_csv(index=False)
            + _geo.sort_values(list(_geo.columns)).to_csv(index=False)
            + repr(sorted(NOMBRES_COMPUESTOS.items())) + repr(sorted(NOMBRES_SIMPLES.items()))
            + repr(sorted(_PROV_ISO.items())) + repr(sorted(_REGION_PROV.items()))
            + '|'.join(sorted(_eans)) + '|detalle_v1|region_coord')
    return hashlib.md5(_txt.encode('utf-8')).hexdigest()[:8]


def _agg_grupos_mes(_o):
    # Mediana por (dimensión, grupo, EAN) de las observaciones de UN mes, y sucursales del grupo
    # (fila con ean_norm '*'). La dimensión 'nacional' (grupo 'Total') reproduce la CELDA 9.
    _ean_de = np.array(list(_EAN_COD))          # código -> ean_norm
    _suc = _o['suc'].values
    _res = []
    for _dim in ['nacional'] + [d for d, _ in _DIMS_DET]:
        _cat = pd.Categorical(np.full(len(_SUC), 'Total') if _dim == 'nacional' else _SUC[_dim])
        _gk = _cat.codes[_suc]
        _g = _o.groupby([_gk, _o['ean'].values])['precio'].agg(['median', 'size'])
        _gi, _ei = _g.index.get_level_values(0), _g.index.get_level_values(1)
        _res.append(pd.DataFrame({'dim': _dim, 'grupo': np.asarray(_cat.categories)[_gi],
                                  'ean_norm': _ean_de[_ei], 'mediana': _g['median'].values,
                                  'n_obs': _g['size'].values}))
        _ns = pd.Series(_suc).groupby(_gk).nunique()
        _res.append(pd.DataFrame({'dim': _dim, 'grupo': np.asarray(_cat.categories)[_ns.index.values],
                                  'ean_norm': '*', 'mediana': np.nan, 'n_obs': _ns.values}))
    return pd.concat(_res, ignore_index=True)


def _enlace(_a, _b, _q):
    # Canasta con las medianas _b / canasta con las medianas _a, solo productos con precio en ambas
    _m = _a.notna() & _b.notna()
    if not _m.any():
        return np.nan
    return (_q[_m] * _b[_m]).sum() / (_q[_m] * _a[_m]).sum()


def _serie_det(_Mm, _Mw, _q):
    # _Mm: medianas EAN x _PER_M (meses: base, columnas y mes parcial); _Mw: EAN x ['REF'] + _PER_W
    # (semanas y, en REF, el mes anterior con las mismas observaciones). Devuelve índice y variación %.
    _idx, _var, _ult = {}, {}, None
    for _k, _p in enumerate(_PER_M):
        if _k == 0:
            _idx[_p] = 100.0 if _Mm[_p].notna().any() else np.nan
            _var[_p] = np.nan
        else:
            _l = _enlace(_Mm[_PER_M[_k - 1]], _Mm[_p], _q)
            _var[_p] = (_l - 1) * 100
            if _ult is None:
                _idx[_p] = np.nan
            else:
                _lu = _l if _ult == _PER_M[_k - 1] else _enlace(_Mm[_ult], _Mm[_p], _q)
                _idx[_p] = _idx[_ult] * _lu
        if pd.notna(_idx[_p]):
            _ult = _p
    _r_ant = np.nan
    for _w in _PER_W:
        _r = _enlace(_Mw['REF'], _Mw[_w], _q)
        _idx[_w] = _idx.get(_MES_ANT, np.nan) * _r
        _var[_w] = (_r / _r_ant - 1) * 100
        _r_ant = _r
    return _idx, _var


def _escribir_hoja_detalle(_ruta, _filas, _cols_m, _cols_w, _titulo, _sub, _notas, _titulo_bloque, _lab_pond):
    _wb = _load_workbook(_ruta) if _ruta.exists() else _Workbook()
    if not _ruta.exists():
        _wb.remove(_wb.active)
    if _HOJA_DET in _wb.sheetnames:
        del _wb[_HOJA_DET]
    _ws = _wb.create_sheet(_HOJA_DET, 0)
    for _w in _wb.worksheets:                  # una sola pestaña seleccionada (si no, Excel las agrupa)
        _w.sheet_view.tabSelected = False
    _ws.sheet_view.tabSelected = True
    _wb.active = 0
    _f_tit, _f_neg = _Font(bold=True, size=13), _Font(bold=True)
    _f_sec = _Font(bold=True, color='FFFFFF')
    # Colores de la CELDA 19: filas de sección verde oscuro, fila de encabezado verde claro
    _rell_sec, _rell_hdr = _Fill('solid', start_color=VERDE_OSCURO), _Fill('solid', start_color=VERDE_CLARO)
    _ws.cell(1, 1, _titulo).font = _f_tit
    for _i, _t in enumerate(_sub):
        _ws.cell(2 + _i, 1, _t)
    _c0 = 5                                     # primera columna de períodos
    _col_de = {}
    for _i, (_p, _lab) in enumerate(_cols_m):
        _col_de[_p] = (_c0 + _i, _lab)
    for _i, (_p, _lab) in enumerate(_cols_w):
        _col_de[_p] = (_c0 + len(_cols_m) + 1 + _i, _lab)     # una columna vacía antes de las semanas
    _ult_col = _c0 + len(_cols_m) + len(_cols_w)
    _fila = 3 + len(_sub)
    _primera_hdr = None
    for _bloque, _clave, _fmt in (('ÍNDICE', 'idx', '0.0'),
                                  ('VARIACIÓN % (meses: contra el mes anterior; semanas: contra la semana anterior)',
                                   'var', '+0.00;-0.00;0.00')):
        _ws.cell(_fila, 1, _bloque).font = _f_tit
        _fila += 1
        _hdr = {1: _titulo_bloque[_clave], 2: _lab_pond, 3: 'Sucursales', 4: 'Productos'}
        _hdr.update({c: lab for c, lab in _col_de.values()})
        for _c, _v in _hdr.items():
            _x = _ws.cell(_fila, _c, _v)
            _x.font, _x.fill = _f_neg, _rell_hdr
            _x.alignment = _Align(horizontal='center', vertical='center', wrap_text=True)
        if _primera_hdr is None:
            _primera_hdr = _fila
        _fila += 1
        for _r in _filas:
            if _r['tipo'] == 'seccion':
                for _c in range(1, _ult_col + 1):
                    _ws.cell(_fila, _c).fill = _rell_sec
                _ws.cell(_fila, 1, _r['label']).font = _f_sec
                _fila += 1
                continue
            _ws.cell(_fila, 1, _r['label'])
            if _r['tipo'] in ('total', 'rubro'):
                _ws.cell(_fila, 1).font = _f_neg
            for _c, _k, _nf in ((2, 'pond', '0.0'), (3, 'suc', '#,##0'), (4, 'prod', '0')):
                if pd.notna(_r.get(_k, np.nan)):
                    _ws.cell(_fila, _c, float(_r[_k]) if _k == 'pond' else int(_r[_k])).number_format = _nf
            for _p, (_c, _lab) in _col_de.items():
                _v = _r[_clave].get(_p, np.nan)
                if pd.notna(_v) and np.isfinite(_v):
                    _x = _ws.cell(_fila, _c, round(float(_v), 6))
                    _x.number_format = _fmt
                    if _r['tipo'] in ('total', 'rubro'):
                        _x.font = _f_neg
            _fila += 1
        _fila += 2
    for _i, _t in enumerate(_notas):
        _ws.cell(_fila + _i, 1, _t)
    _ws.column_dimensions['A'].width = 40
    for _c in range(2, _ult_col + 1):
        _ws.column_dimensions[_col_letter(_c)].width = 10 if _c <= 4 else 9.5
    _ws.row_dimensions[_primera_hdr].height = 30
    _ws.freeze_panes = _ws.cell(_primera_hdr + 1, _c0)
    _wb.save(_ruta)


# ── Ejecución ─────────────────────────────────────────────────────────────────
detalle_long = None
if DETALLE_CANASTA is None:
    print('DETALLE_CANASTA = None: no se arma la hoja analisis_detallado.')
elif DETALLE_CANASTA not in CANASTAS:
    print(f'AVISO: DETALLE_CANASTA = {DETALLE_CANASTA!r} no es una canasta activa: no se arma la hoja analisis_detallado.')
elif globals().get('_OBS') is None or globals().get('_DET') != DETALLE_CANASTA:
    print('AVISO: faltan las observaciones de la CELDA 19b (correrla justo antes que esta; esta celda las libera '
          'al terminar): no se arma la hoja analisis_detallado.')
else:
    _t0 = _time.time()
    _cid = DETALLE_CANASTA
    _can, _name = CANASTAS[_cid], CANASTA_NAMES[_cid]
    _eans_det = sorted(e for e in _can if e in _EAN_COD)
    _cod_det = np.array([_EAN_COD[e] for e in _eans_det], dtype='int16')
    _qty = pd.Series({e: float(_can[e][1]) for e in _eans_det})
    _rubro_de = pd.Series({e: RUBRO_EAN.get(e, 'Sin rubro') for e in _eans_det})
    _categ_de = pd.Series({e: _can[e][2] for e in _eans_det})
    _m = np.isin(_OBS['ean'].values, _cod_det)
    _o_det = _OBS if _m.all() else _OBS[_m]
    _fc_d = _o_det['fecha'].values
    _ym_d = _fc_d // 100

    # ── Períodos ──────────────────────────────────────────────────────────────
    _D = int(_fc_d[_ym_d == _YM_ACT].max() % 100)
    _N_ACT = _cal.monthrange(_YM_ACT // 100, _YM_ACT % 100)[1]
    _ACT_COMPLETO = _D >= _N_ACT
    _L = pd.Period(PERIODO if _ACT_COMPLETO else _MES_ANT, freq='M')     # último mes completo
    _NM = max(1, int(DETALLE_MESES))
    _MESES_COL = [str(_L - k) for k in range(_NM - 1, -1, -1)]
    _BASE = str(_L - _NM)
    _PER_M = [_BASE] + _MESES_COL + ([] if _ACT_COMPLETO else [PERIODO])
    _sem_d = np.minimum((_fc_d % 100 - 1) // 7, 3)
    _fin_sem = [7, 14, 21, _N_ACT]
    _PER_W = ([f'{_MES_ANT}-S{k + 1}' for k in range(4)]
              + [f'{PERIODO}-S{k + 1}' for k in range(4) if _D >= _fin_sem[k]])
    _ym_lbl = lambda _p: int(_p[:7].replace('-', ''))
    _cols_m = [(p, _lbl_mes(_ym_lbl(p))) for p in _MESES_COL]
    if not _ACT_COMPLETO:
        _cols_m.append((PERIODO, f'{_lbl_mes(_YM_ACT)} (al {_D}/{_YM_ACT % 100})'))
    _cols_w = [(w, f'{w[-1]}S {_MES_ABR[_ym_lbl(w) % 100]}') for w in _PER_W]
    print(f'Hoja analisis_detallado — {_name}: meses {_MESES_COL[0]} a {_MESES_COL[-1]} (base {_BASE} = 100)'
          + ('' if _ACT_COMPLETO else f', {PERIODO} parcial al día {_D}') + f'; {len(_PER_W)} semanas')

    # ── Medianas por grupo y mes: caché + meses de la 19b + meses viejos del SEPA ──
    _clave_det = _firma_detalle(_eans_det)
    _cache_det = CACHE_DIR / f'detalle_{_clave_det}_v1.parquet'
    _agg = {}
    for _mx in (_MES_ANT, PERIODO):
        if _mx in _PER_M:
            _agg[_mx] = _agg_grupos_mes(_o_det[_ym_d == _ym_lbl(_mx)])
    _cdf = pd.read_parquet(_cache_det) if (USE_CACHE and _cache_det.exists()) else pd.DataFrame()
    for _mx in _PER_M:
        if _mx not in _agg and len(_cdf) and (_cdf['mes'] == _mx).any():
            _agg[_mx] = _cdf[_cdf['mes'] == _mx].drop(columns='mes').reset_index(drop=True)
    _falt = [m for m in _PER_M if m not in _agg]
    print(f'  medianas por grupo: {len(_PER_M) - len(_falt)} meses listos (caché {_cache_det.name} o 19b), '
          f'{len(_falt)} a leer del SEPA')
    for _mx in _falt:
        if _mx not in _mapa_desag:
            print(f'  AVISO: {_mx} no está en los ZIPs: columna vacía para regiones, provincias, cadenas y tipos')
            continue
        _t1 = _time.time()
        _om = _leer_mes_desag(_mx, _eans_det)
        _SUC = _atributos_sucursal()            # sucursales nuevas de los meses viejos
        _agg[_mx] = _agg_grupos_mes(_om)
        del _om
        gc.collect()
        print(f'    {_mx} agregado en {_time.time() - _t1:,.0f} s')
    _nuevos = [m for m in _agg if m < PERIODO and (not len(_cdf) or not (_cdf['mes'] == m).any())]
    if USE_CACHE and _nuevos:
        _cdf = pd.concat(([_cdf] if len(_cdf) else []) + [_agg[m].assign(mes=m) for m in _nuevos],
                         ignore_index=True)
        _cdf.to_parquet(_cache_det, compression='snappy', index=False)
        print(f'  caché actualizado: {_cache_det.name} ({_cdf["mes"].nunique()} meses)')

    _A = pd.concat([d.assign(mes=m) for m, d in _agg.items()], ignore_index=True)
    _A_med = _A[_A['ean_norm'] != '*'].pivot_table(index=['dim', 'grupo', 'ean_norm'], columns='mes',
                                                   values='mediana', aggfunc='first')
    _A_suc = _A[_A['ean_norm'] == '*'].pivot_table(index=['dim', 'grupo'], columns='mes',
                                                   values='n_obs', aggfunc='first')

    # ── Medianas semanales por grupo (clave entera AAAAMM*10 + semana: nada de textos por observación) ──
    _wk_key = _ym_d.astype('int64') * 10 + _sem_d + 1
    _lbl_sem = lambda _k: f'{_k // 1000}-{(_k // 10) % 100:02d}-S{_k % 10}'
    _W = []
    for _dim in ['nacional'] + [d for d, _ in _DIMS_DET]:
        _cat = pd.Categorical(np.full(len(_SUC), 'Total') if _dim == 'nacional' else _SUC[_dim])
        _gk = _cat.codes[_o_det['suc'].values]
        _g = _o_det.groupby([_gk, _o_det['ean'].values, _wk_key])['precio'].median()
        _W.append(pd.DataFrame({'dim': _dim,
                                'grupo': np.asarray(_cat.categories)[_g.index.get_level_values(0)],
                                'ean_norm': np.array(list(_EAN_COD))[_g.index.get_level_values(1)],
                                'per': [_lbl_sem(k) for k in _g.index.get_level_values(2)],
                                'mediana': _g.values}))
    del _wk_key, _sem_d
    _W = pd.concat(_W, ignore_index=True)
    _W = _W[_W['per'].isin(_PER_W)]
    _W_med = _W.pivot_table(index=['dim', 'grupo', 'ean_norm'], columns='per', values='mediana', aggfunc='first')

    def _mat(_tabla, _dim, _grupo, _cols, _eans):
        # medianas EAN x períodos de un grupo (NaN donde no hay dato)
        if (_dim, _grupo) in _tabla.index.droplevel(2):
            _t = _tabla.xs((_dim, _grupo), level=(0, 1))
        else:
            _t = pd.DataFrame()
        return _t.reindex(index=_eans, columns=_cols)

    def _mw(_dim, _grupo, _eans):
        _w = _mat(_W_med, _dim, _grupo, _PER_W, _eans)
        _w.insert(0, 'REF', _mat(_A_med, _dim, _grupo, [_MES_ANT], _eans)[_MES_ANT])
        return _w

    # ── Filas ─────────────────────────────────────────────────────────────────
    _ofi = _MED_OFI.reindex(index=_eans_det, columns=_PER_M)        # medianas oficiales (CELDA 9)
    _costo_base = _qty * _ofi[_BASE]
    _T_base = _costo_base.sum()
    _ultimo = str(_L)
    _filas = []

    # Total: la serie oficial de la CELDA 9
    _S = serie_nac_dict[_cid].set_index('mes')['canasta_nacional_ponderada']
    _idx_t = {p: (_S.get(p, np.nan) / _S.get(_BASE, np.nan) * 100) for p in _PER_M}
    _var_t = {p: ((_S.get(p, np.nan) / _S.get(_PER_M[k - 1], np.nan) - 1) * 100 if k else np.nan)
              for k, p in enumerate(_PER_M)}
    _mw_nac = _mw('nacional', 'Total', _eans_det)
    _r_ant = np.nan
    for _w in _PER_W:
        _r = _enlace(_mw_nac['REF'], _mw_nac[_w], _qty)
        _idx_t[_w] = _idx_t.get(_MES_ANT, np.nan) * _r
        _var_t[_w] = (_r / _r_ant - 1) * 100
        _r_ant = _r
    _suc_L = lambda _dim, _g: (_A_suc.loc[(_dim, _g), _ultimo]
                               if (_dim, _g) in _A_suc.index and _ultimo in _A_suc.columns else np.nan)
    _filas.append({'tipo': 'total', 'label': f'Total {_name}', 'dim': 'nacional', 'grupo': 'Total',
                   'pond': 100.0, 'suc': _suc_L('nacional', 'Total'), 'prod': int(_ofi[_ultimo].notna().sum()),
                   'idx': _idx_t, 'var': _var_t})

    # Rubros SEPA y sus categorías (medianas nacionales)
    _filas.append({'tipo': 'seccion', 'label': 'Rubros (SEPA) y categorías'})
    _pond = (_costo_base / _T_base * 100)
    for _rub in _pond.groupby(_rubro_de).sum().sort_values(ascending=False).index:
        _er = [e for e in _eans_det if _rubro_de[e] == _rub]
        _i, _v = _serie_det(_ofi.loc[_er], _mw_nac.loc[_er], _qty[_er])
        _filas.append({'tipo': 'rubro', 'label': _rub, 'dim': 'rubro', 'grupo': _rub, 'pond': _pond[_er].sum(),
                       'prod': len(_er), 'idx': _i, 'var': _v})
        _pc = _pond[_er].groupby(_categ_de[_er]).sum().sort_values(ascending=False)
        for _cat_n in _pc.index:
            _ec = [e for e in _er if _categ_de[e] == _cat_n]
            _i, _v = _serie_det(_ofi.loc[_ec], _mw_nac.loc[_ec], _qty[_ec])
            _filas.append({'tipo': 'categoria', 'label': '    ' + _cat_n, 'dim': 'categoria', 'grupo': _cat_n,
                           'pond': _pond[_ec].sum(), 'prod': len(_ec), 'idx': _i, 'var': _v})

    # Regiones, provincias, cadenas y tipos de sucursal (mediana dentro del grupo)
    _omitidos = []
    for _dim, _titulo in _DIMS_DET:
        _grupos = [g for (d, g) in _A_suc.index if d == _dim]
        _ns = {g: _suc_L(_dim, g) for g in _grupos}
        _vis = [g for g in _grupos if pd.notna(_ns[g]) and _ns[g] >= DETALLE_MIN_SUCURSALES]
        _omitidos += [f'{g} ({0 if pd.isna(_ns[g]) else int(_ns[g])})' for g in _grupos if g not in _vis]
        if _dim == 'region':
            _vis = [g for g in _ORDEN_REGION if g in _vis] + sorted(g for g in _vis if g not in _ORDEN_REGION)
        elif _dim == 'provincia':
            _vis = sorted(_vis)
        else:
            _vis = sorted(_vis, key=lambda g: -_ns[g])
        _filas.append({'tipo': 'seccion', 'label': _titulo})
        for _g in _vis:
            _Mm = _mat(_A_med, _dim, _g, _PER_M, _eans_det)
            _i, _v = _serie_det(_Mm, _mw(_dim, _g, _eans_det), _qty)
            _filas.append({'tipo': 'grupo', 'label': _g, 'dim': _dim, 'grupo': _g, 'pond': np.nan,
                           'suc': _ns[_g], 'prod': int(_Mm[_ultimo].notna().sum()), 'idx': _i, 'var': _v})

    # Control: con la canasta completa, el Total es la suma ponderada de los rubros
    _rubs = [f for f in _filas if f['tipo'] == 'rubro']
    _dif = max((abs(sum(f['pond'] * f['idx'][p] for f in _rubs) / 100 - _filas[0]['idx'][p])
                for p in _PER_M if pd.notna(_filas[0]['idx'][p])), default=0.0)
    if _dif > 1e-6:
        print(f'  AVISO: Total vs suma ponderada de los rubros difiere hasta {_dif:.4f} puntos '
              f'(algún producto sin precio en algún mes de la ventana)')

    # ── Excel: primera hoja ─────────────────────────────────────────────────────
    _lab_pond = f'Pond. {_lbl_mes(_ym_lbl(_BASE))} %'
    _titulo_bloque = {'idx': f'Índice base {_lbl_mes(_ym_lbl(_BASE))} = 100', 'var': 'Variación %'}
    _titulo = (f'Canasta {_name} — análisis detallado de la variación de precios '
               f'(SEPA, {_lbl_mes(_YM_ACT)}' + ('' if _ACT_COMPLETO else f' al {_D}/{_YM_ACT % 100}') + ')')
    _sub = [f'Índice base {_lbl_mes(_ym_lbl(_BASE))} = 100: la columna {_lbl_mes(_ym_lbl(_ultimo))} menos 100 es la '
            f'variación interanual. Total = serie oficial del nb02 (CELDA 9).',
            'Rubros y categorías: medianas nacionales. Regiones, provincias, cadenas y tipos: mediana de las '
            'observaciones del grupo (mismo método). Pond = participación en el costo de la canasta en el mes base.']
    _notas = [
        'Notas',
        'Método: en cada fila, la canasta es la suma de qty x mediana de las observaciones sucursal x día del '
        'período (todas las del país, o solo las del grupo). Cada eslabón compara solo los productos con precio '
        'en los dos períodos (índice encadenado).',
        f'Semanas: 1S = días 1-7, 2S = 8-14, 3S = 15-21, 4S = 22 a fin de mes. Del mes en curso solo las semanas '
        f'completas. Nivel = índice de {_lbl_mes(_YM_ANT)} x (canasta de la semana / canasta de {_lbl_mes(_YM_ANT)}).',
        'Variación % de las semanas: contra la semana anterior. La de las regiones, provincias, cadenas y tipos no '
        'suma la del Total (es una mediana): el aporte aditivo de cada grupo está en las hojas Cadenas, Provincias, '
        'Regiones y Tipo_sucursal (CELDA 19b), y el de cada producto en Productos.',
        f'Sucursales y Productos: con precio en {_lbl_mes(_ym_lbl(_ultimo))}. Se muestran los grupos con al menos '
        f'{DETALLE_MIN_SUCURSALES} sucursales (DETALLE_MIN_SUCURSALES).',
        'Región: AMBA = CABA + Buenos Aires a <= 90 km del Obelisco por coordenadas (columna amba de la CELDA 7, '
        'la misma del Cuadro 1 y los rankings); el resto por la provincia del archivo del SEPA (Buenos Aires fuera del '
        'AMBA: Pampeana; sin coordenadas: "Buenos Aires s/ubicar"). Provincia: la del archivo del SEPA.',
    ]
    if _omitidos:
        _notas.append('Grupos con menos sucursales (no se muestran): ' + ', '.join(_omitidos))
    _out_det = OUTPUT_DIR / f'canasta_analisis_{ULTIMO_MES}.xlsx'
    _escribir_hoja_detalle(_out_det, _filas, _cols_m, _cols_w, _titulo, _sub, _notas, _titulo_bloque, _lab_pond)

    detalle_long = pd.DataFrame([{'seccion': f['dim'], 'fila': f['label'].strip(), 'periodo': p,
                                  'indice': f['idx'].get(p, np.nan), 'variacion_%': f['var'].get(p, np.nan),
                                  'pond': f.get('pond', np.nan), 'sucursales': f.get('suc', np.nan),
                                  'productos': f.get('prod', np.nan)}
                                 for f in _filas if f['tipo'] != 'seccion' for p in _PER_M[1:] + _PER_W])
    _OBS = None
    del _o_det, _A, _W
    gc.collect()
    print(f'Hoja {_HOJA_DET} escrita como primera hoja de {_out_det.name} '
          f'({len([f for f in _filas if f["tipo"] != "seccion"])} filas, {_time.time() - _t0:,.0f} s)')
    _col_fin = PERIODO if not _ACT_COMPLETO else _ultimo
    print(f'  Variación % {_col_fin} ' + ('(parcial) ' if not _ACT_COMPLETO else '') + 'contra el mes anterior:')
    print(detalle_long[(detalle_long['periodo'] == _col_fin)
                       & detalle_long['seccion'].isin(['nacional', 'rubro', 'region'])]
          [['fila', 'pond', 'indice', 'variacion_%']].round(2).to_string(index=False))'''))

# ── CELL 20 — VALORES PARA DOCUMENTO TÉCNICO ──────────────────────────────────
cells.append(cell_code("""\
# ============================================================
# CELDA 20 — Valores para actualizar el documento técnico
# ============================================================
# Calcula todos los números que aparecen en el LaTeX (portada,
# resumen ejecutivo, evolución, provincias, cadenas, barrios,
# canastas especiales, acumulados) y los exporta como:
#   - Print organizado por sección del documento
#   - Hoja 'Valores_Documento' en canasta_analisis_{MES}.xlsx
# ============================================================

def _ar(x): return f"${int(round(x)):,}".replace(",", ".")
def _pp(x, dec=2):
    s = "+" if x >= 0 else ""; return f"{s}{x:.{dec}f}%".replace(".", ",")
def _pct(x, dec=1):      # porcentaje sin signo y con coma decimal (brechas y dispersiones)
    return f"{x:.{dec}f}%".replace(".", ",")

_MEDIA_ID = 'cantidad_03'
_POP_ID   = 'cantidad_02'
_N_EXTREMOS = 3          # caras y baratas del resumen: las mismas de cada lado

# Referencias UNICAS en toda la celda (las del Cuadro 1, CELDA 8):
#   pais = promedio de las medianas provinciales ponderado por poblacion (prom_nac_dict);
#   CABA = mediana de sus sucursales (su fila del Cuadro 1);
#   AMBA = mediana de las sucursales del AMBA (CELDA 7: CABA + conurbano por coordenadas).
# Cadenas y barrios: mediana de sus sucursales, como los rankings [mediana] de las CELDAS 16 y 18.

# ── 1. Valores por canasta ────────────────────────────────────────────────────
_vals = {c: prom_nac_dict[c] for c in CANASTAS_ACTIVAS}
_vals_prom = {c: prom_nac_prom_dict[c] for c in CANASTAS_ACTIVAS}
_vars = {}
_vars_prom = {}
for c in CANASTAS_ACTIVAS:
    _sn = serie_nac_dict[c]
    if len(_sn) > 1:
        _vars[c] = _sn['variacion_mensual_%'].iloc[-1]
        _vars_prom[c] = _sn['variacion_mensual_prom_%'].iloc[-1]

_sorted_ids = sorted(CANASTAS_ACTIVAS, key=lambda c: _vals[c])
_min_id, _max_id = _sorted_ids[0], _sorted_ids[-1]
_brecha_abs = _vals[_max_id] - _vals[_min_id]
_brecha_pct = _brecha_abs / _vals[_min_id] * 100

# ── 2. Análisis provincial (canasta media) ────────────────────────────────────
_v_media = _vals[_MEDIA_ID]
_v_media_prom = _vals_prom[_MEDIA_ID]
_spv = serie_prov_dict[_MEDIA_ID].copy()
_spv['vs_%'] = (_spv['canasta_total'] / _v_media - 1) * 100
_prov_min = _spv.loc[_spv['canasta_total'].idxmin()]
_prov_max = _spv.loc[_spv['canasta_total'].idxmax()]
_disp_prov = (_prov_max['canasta_total'] - _prov_min['canasta_total']) / _prov_min['canasta_total'] * 100

# Serie mensual de la Media (CELDA 9): de ahí sale la variación; el nivel es el del Cuadro 1
_sn_media = serie_nac_dict[_MEDIA_ID]
_serie_ant = _sn_media['canasta_nacional_ponderada'].iloc[-2] if len(_sn_media) >= 2 else None
_serie_act = _sn_media['canasta_nacional_ponderada'].iloc[-1] if len(_sn_media) >= 1 else None

# ── 3. Dispersión entre sucursales (canasta media) ────────────────────────────
# Se publica P5-P95: el mín-máx lo mueven una o dos sucursales atípicas (oct-26: una con la
# canasta 20% abajo y tres de una cadena con 41 de 69 productos con precio propio).
_cgf_m = canasta_geo_dict[_MEDIA_ID]
_vsuc = _cgf_m['canasta_total']
_suc_min, _suc_max = _vsuc.min(), _vsuc.max()
_p05, _p25, _p75, _p95 = (_vsuc.quantile(q) for q in (0.05, 0.25, 0.75, 0.95))
_disp_suc = (_p95 - _p05) / _p05 * 100
_disp_suc_mm = (_suc_max - _suc_min) / _suc_min * 100
_n_prod_media = len(CANASTAS[_MEDIA_ID])

def _quien(r):
    return (f"{r['cadena']} {r['sucursales_nombre']} ({r['PROVINCIA_NORM']}; "
            f"{int(r['productos_propios'])}/{_n_prod_media} productos con precio propio)")

_suc_min_q = _quien(_cgf_m.loc[_vsuc.idxmin()])
_suc_max_q = _quien(_cgf_m.loc[_vsuc.idxmax()])

def _ranking(_df, _col):
    return (_df.groupby(_col)
            .agg(n=('canasta_total', 'count'), valor=('canasta_total', 'median'))
            .reset_index())

def _disp(_s):
    return (_s.max() - _s.min()) / _s.min() * 100 if len(_s) >= 2 else 0

# ── 4. Cadenas nacionales (canasta media) ─────────────────────────────────────
_rk_nac = _ranking(_cgf_m, 'cadena')
_rk_nac = _rk_nac[_rk_nac['n'] >= MIN_SUCURSALES_RANKING].sort_values('valor', ascending=False)
_rk_nac['vs_pais_%'] = (_rk_nac['valor'] / _v_media - 1) * 100
_disp_cad_nac = _disp(_rk_nac['valor'])

# ── 5. Cadenas AMBA (canasta media) ───────────────────────────────────────────
_cgf_amba = _cgf_m[_cgf_m['amba']]
_v_amba = _cgf_amba['canasta_total'].median() if len(_cgf_amba) else float('nan')
_rk_amba = _ranking(_cgf_amba, 'cadena')
_rk_amba = _rk_amba[_rk_amba['n'] >= MIN_SUCURSALES_RANKING].sort_values('valor', ascending=False)
_rk_amba['vs_amba_%'] = (_rk_amba['valor'] / _v_amba - 1) * 100
_rk_amba['vs_pais_%'] = (_rk_amba['valor'] / _v_media - 1) * 100
_disp_cad_amba = _disp(_rk_amba['valor'])

# ── 6. Barrios CABA (canasta media) ───────────────────────────────────────────
_cgf_caba = _cgf_m[_cgf_m['PROVINCIA_NORM'] == 'CABA'].copy()
_cgf_caba['barrio'] = [det_barrio(_la, _lo) for _la, _lo in
                       zip(_cgf_caba['sucursales_latitud'], _cgf_caba['sucursales_longitud'])]
_brk = _ranking(_cgf_caba[_cgf_caba['barrio'] != 'Sin clasificar'], 'barrio')
_brk = _brk[_brk['n'] >= 2].sort_values('valor', ascending=False).reset_index(drop=True)
_v_caba = _cgf_caba['canasta_total'].median() if len(_cgf_caba) else float('nan')
_brk['vs_caba_%'] = (_brk['valor'] / _v_caba - 1) * 100
_brk['vs_pais_%'] = (_brk['valor'] / _v_media - 1) * 100
_disp_bar = _disp(_brk['valor'])

# ── 7. Canastas especiales ────────────────────────────────────────────────────
_prima_cel  = ((_vals['cantidad_05'] / _v_media) - 1) * 100 if 'cantidad_05' in _vals else None
_ahorro_veg = ((_vals['cantidad_06'] / _vals[_POP_ID]) - 1) * 100 if 'cantidad_06' in _vals and _POP_ID in _vals else None

# ── 8. Acumulados: canasta e IPC en el MISMO período ──────────────────────────
# Desde MES_INICIO_GRAFICO (o el primer mes que tengan todas las series) hasta el último mes con
# IPC publicado. El mes en curso, sin IPC todavía, va aparte y no se compara con el IPC.
def _acum_entre(_s, _m0, _m1):
    # Variación % de la serie _s (índice = mes) entre _m0 y _m1; None si falta un extremo
    if _m0 in _s.index and _m1 in _s.index and pd.notna(_s[_m0]) and pd.notna(_s[_m1]) and _s[_m0] > 0:
        return (_s[_m1] / _s[_m0] - 1) * 100
    return None

_ipc_idx = ipc.set_index('mes')
_ipc_gen = _ipc_idx['ipc_general'].dropna()
_ipc_ali = _ipc_idx['ipc_alimentos'].dropna()
_series_acum = {c: serie_nac_dict[c].set_index('mes')['canasta_nacional_ponderada'].dropna()
                for c in CANASTAS_ACTIVAS if len(serie_nac_dict[c]) >= 2}
_M0_ACUM = max([MES_INICIO_GRAFICO] + [_s.index.min() for _s in _series_acum.values()]
               + ([_ipc_gen.index.min()] if len(_ipc_gen) else []))
_M1_ACUM = min([_s.index.max() for _s in _series_acum.values()]
               + ([_ipc_gen.index.max()] if len(_ipc_gen) else []) or [PERIODO])
_acum = {c: _acum_entre(_s, _M0_ACUM, _M1_ACUM) for c, _s in _series_acum.items()}
_acum = {c: v for c, v in _acum.items() if v is not None}
_acum_ult = {}           # hasta el último mes de la serie cuando el IPC todavía no lo publicó
for c, _s in _series_acum.items():
    if _s.index.max() > _M1_ACUM:
        _v = _acum_entre(_s, _M0_ACUM, _s.index.max())
        if _v is not None:
            _acum_ult[c] = (_s.index.max(), _v)
_acum_ipc_gen = _acum_entre(_ipc_gen, _M0_ACUM, _M1_ACUM)
_acum_ipc_ali = _acum_entre(_ipc_ali, _M0_ACUM, _M1_ACUM)

# ── 9. Variaciones últimos 3 meses ────────────────────────────────────────────
_var3_canastas = {}
for c in CANASTAS_ACTIVAS:
    _sn = serie_nac_dict[c]
    if len(_sn) >= 3:
        _var3_canastas[c] = _sn[['mes','variacion_mensual_%']].tail(3).values.tolist()

_ipc_tail3 = ipc[['mes','ipc_general_var_%','ipc_alimentos_var_%']].tail(3)

# ═══════════════════════════════════════════════════════════════════════════════
# IMPRIMIR RESUMEN POR SECCIÓN DEL DOCUMENTO
# ═══════════════════════════════════════════════════════════════════════════════
print("=" * 72)
print(f"  VALORES PARA DOCUMENTO TÉCNICO — {NOMBRE_MES_TITLE.upper()}")
print("=" * 72)
print("  Referencias: país = Cuadro 1 (medianas provinciales ponderadas por población);")
print("  cadenas y barrios = mediana de sus sucursales; AMBA = CABA + conurbano por coordenadas.")

print("\\n[PORTADA / TÍTULO]")
print(f"  Mes:                 {NOMBRE_MES_TITLE}{SUFIJO_PARCIAL}")
print(f"  Canasta media:       {_ar(_v_media)}  (Cuadro 1)")
_txt_serie = (f"  (serie mensual: {_ar(_serie_ant)} -> {_ar(_serie_act)})" if _serie_ant is not None else '')
print(f"  Var. mensual media:  {_pp(_vars.get(_MEDIA_ID, float('nan')))}{_txt_serie}" + ('  ⚠️ PRELIMINAR (mes parcial)' if MES_PARCIAL else ''))

print("\\n[RESUMEN EJECUTIVO — Item 1: valores y variaciones por canasta]")
for c in _sorted_ids:
    _nm = CANASTA_NAMES[c]
    print(f"  {_nm:<22} {_ar(_vals[c]):>12}   var.mensual: {_pp(_vars.get(c, float('nan')))}")
print(f"  Brecha absoluta:       {_ar(_brecha_abs)}")
print(f"  Brecha relativa:       {_pct(_brecha_pct)}  ({CANASTA_NAMES[_min_id]} a {CANASTA_NAMES[_max_id]})")

print("\\n[RESUMEN EJECUTIVO — Item 2: patrón provincial]")
print(f"  Prov. más barata:  {_prov_min['provincia']:<25} {_ar(_prov_min['canasta_total'])}  ({_pp(_prov_min['vs_%'])})")
print(f"  Prov. más cara:    {_prov_max['provincia']:<25} {_ar(_prov_max['canasta_total'])}  ({_pp(_prov_max['vs_%'])})")
print(f"  Dispersión prov.:  {_pct(_disp_prov)}")

print(f"\\n[RESUMEN EJECUTIVO — Item 3: barrios CABA (top {_N_EXTREMOS} / bottom {_N_EXTREMOS})]")
_n_ext_b = min(_N_EXTREMOS, len(_brk) // 2)
for _, r in _brk.head(_n_ext_b).iterrows():
    print(f"  CARO   {r['barrio']:<25} {_ar(r['valor'])}  ({_pp(r['vs_caba_%'])})")
for _, r in _brk.tail(_n_ext_b).sort_values('valor').iterrows():
    print(f"  BARATO {r['barrio']:<25} {_ar(r['valor'])}  ({_pp(r['vs_caba_%'])})")
print(f"  Dispersión CABA:   {_pct(_disp_bar, 2)}")
print(f"  CABA (Cuadro 1):   {_ar(_v_caba)}")

print("\\n[RESUMEN EJECUTIVO — Item 4: cadenas nacionales y AMBA (mediana por cadena)]")
print("  Nacional (vs país):")
_n_ext = min(_N_EXTREMOS, len(_rk_nac) // 2)
for _, r in _rk_nac.head(_n_ext).iterrows():
    print(f"    CARA   {r['cadena']:<28} {_ar(r['valor'])}  ({_pp(r['vs_pais_%'])})")
for _, r in _rk_nac.tail(_n_ext).sort_values('valor').iterrows():
    print(f"    BARATA {r['cadena']:<28} {_ar(r['valor'])}  ({_pp(r['vs_pais_%'])})")
print(f"  Dispersión nacional: {_pct(_disp_cad_nac)}")
if len(_rk_amba) >= 2:
    print(f"  AMBA (vs AMBA = {_ar(_v_amba)}):")
    _n_ext_a = min(_N_EXTREMOS, len(_rk_amba) // 2)
    for _, r in _rk_amba.head(_n_ext_a).iterrows():
        print(f"    CARA   {r['cadena']:<28} {_ar(r['valor'])}  ({_pp(r['vs_amba_%'])})")
    for _, r in _rk_amba.tail(_n_ext_a).sort_values('valor').iterrows():
        print(f"    BARATA {r['cadena']:<28} {_ar(r['valor'])}  ({_pp(r['vs_amba_%'])})")
    print(f"  Dispersión AMBA:     {_pct(_disp_cad_amba)}")

print("\\n[RESUMEN EJECUTIVO — Item 5: canastas especiales]")
if _prima_cel is not None:
    print(f"  Prima celíaca:   {_pp(_prima_cel)}   ({_ar(_vals['cantidad_05'])} vs {_ar(_v_media)})")
if _ahorro_veg is not None:
    print(f"  Ahorro vegano:   {_pp(_ahorro_veg)}   ({_ar(_vals['cantidad_06'])} vs {_ar(_vals[_POP_ID])})")

print(f"\\n[RESUMEN EJECUTIVO — Item 6: acumulados {_M0_ACUM} -> {_M1_ACUM} (mismo período que el IPC)]")
for c in _sorted_ids:
    if c in _acum:
        print(f"  {CANASTA_NAMES[c]:<22} {_pp(_acum[c])}")
if _acum_ipc_gen is not None:
    print(f"  {'IPC Nivel General':<22} {_pp(_acum_ipc_gen)}")
if _acum_ipc_ali is not None:
    print(f"  {'IPC Alimentos':<22} {_pp(_acum_ipc_ali)}")
if _acum_ult:
    _m_ult = max(m for m, _ in _acum_ult.values())
    print(f"  Hasta {_m_ult}{' (mes parcial)' if MES_PARCIAL else ''}, sin IPC publicado (no comparar con el IPC):")
    for c in _sorted_ids:
        if c in _acum_ult:
            print(f"    {CANASTA_NAMES[c]:<20} {_pp(_acum_ult[c][1])}")

print("\\n[SECCIÓN EVOLUCIÓN — Variaciones últimos 3 meses]")
print(f"  {'Mes':<10}  {'IPC Gral':>10}  {'IPC Ali':>10}")
for _, r in _ipc_tail3.iterrows():
    print(f"  {r['mes']:<10}  {_pp(r['ipc_general_var_%']):>10}  {_pp(r['ipc_alimentos_var_%']):>10}")
for c in CANASTAS_ACTIVAS:
    if c in _var3_canastas:
        _nm = CANASTA_NAMES[c]
        _vs = [_pp(v[1]) for v in _var3_canastas[c]]
        _ms = [v[0] for v in _var3_canastas[c]]
        print(f"  {_nm:<22}  " + "  ".join(f"{m}: {v}" for m, v in zip(_ms, _vs)))

print("\\n[SECCIÓN PROVINCIAL — Dispersión entre sucursales (canasta media)]")
print(f"  Dispersión P5-P95: {_pct(_disp_suc)}   (P5 {_ar(_p05)} - P95 {_ar(_p95)})")
print(f"  P25:               {_ar(_p25)}")
print(f"  P75:               {_ar(_p75)}")
print(f"  Mín-máx:           {_pct(_disp_suc_mm)}   (no publicar: lo mueven sucursales atípicas)")
print(f"    mínima {_ar(_suc_min)}: {_suc_min_q}")
print(f"    máxima {_ar(_suc_max)}: {_suc_max_q}")

print(f"\\n[SECCIÓN CADENAS — Ranking nacional completo (canasta media; vs país = {_ar(_v_media)})]")
for _, r in _rk_nac.iterrows():
    print(f"  {r['cadena']:<28} {int(r['n']):>4} sucs   {_ar(r['valor'])}  ({_pp(r['vs_pais_%'])})")

if len(_rk_amba) >= 2:
    print(f"\\n[SECCIÓN CADENAS — Ranking AMBA completo (canasta media; AMBA = {_ar(_v_amba)})]")
    for _, r in _rk_amba.iterrows():
        print(f"  {r['cadena']:<28} {int(r['n']):>4} sucs   {_ar(r['valor'])}  vs AMBA: {_pp(r['vs_amba_%'])}  vs país: {_pp(r['vs_pais_%'])}")

print(f"\\n[SECCIÓN BARRIOS CABA — Ranking completo (canasta media; CABA = {_ar(_v_caba)})]")
for i, r in _brk.iterrows():
    print(f"  {str(i+1):>2}. {r['barrio']:<25} {int(r['n']):>3} sucs   {_ar(r['valor'])}  vs CABA: {_pp(r['vs_caba_%'])}  vs país: {_pp(r['vs_pais_%'])}")
print("=" * 72)

# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTAR A EXCEL (nueva hoja en canasta_analisis_{MES}.xlsx)
# ═══════════════════════════════════════════════════════════════════════════════
import openpyxl as _opxl
_xls_path = OUTPUT_DIR / f'canasta_analisis_{PERIODO}.xlsx'
try:
    _wb = _opxl.load_workbook(_xls_path)
    if 'Valores_Documento' in _wb.sheetnames:      # re-correr la celda la reemplaza
        del _wb['Valores_Documento']
    _ws = _wb.create_sheet('Valores_Documento')

    # Cabecera
    _ws.append(['Seccion', 'Variable', 'Valor_LaTeX', 'Valor_numero'])
    _hdr = _ws[1]
    for _cell in _hdr:
        _cell.font = _opxl.styles.Font(bold=True)

    _rows_doc = []
    # Portada
    _rows_doc.append(['Portada', 'Mes', NOMBRE_MES_TITLE, NOMBRE_MES_TITLE])
    _rows_doc.append(['Portada', 'Canasta media valor', _ar(_v_media), round(_v_media, 0)])
    _rows_doc.append(['Portada', 'Canasta media valor (prom)', _ar(_v_media_prom), round(_v_media_prom, 0)])
    _rows_doc.append(['Portada', 'Canasta media var.mensual', _pp(_vars.get(_MEDIA_ID, 0)), round(_vars.get(_MEDIA_ID, 0), 2)])
    if _serie_ant is not None:
        _rows_doc.append(['Portada', 'Canasta media serie mensual mes anterior (base de la var.)', _ar(_serie_ant), round(_serie_ant, 0)])
        _rows_doc.append(['Portada', 'Canasta media serie mensual mes actual (base de la var.)', _ar(_serie_act), round(_serie_act, 0)])
    # Canastas (valor y var.mensual: MEDIANA y su gemela MEDIA recortada)
    for c in _sorted_ids:
        _nm = CANASTA_NAMES[c]
        _rows_doc.append(['Canastas', f'{_nm} — valor', _ar(_vals[c]), round(_vals[c], 0)])
        _rows_doc.append(['Canastas', f'{_nm} — valor (prom)', _ar(_vals_prom[c]), round(_vals_prom[c], 0)])
        _rows_doc.append(['Canastas', f'{_nm} — var.mensual', _pp(_vars.get(c, 0)), round(_vars.get(c, 0), 2)])
        _rows_doc.append(['Canastas', f'{_nm} — var.mensual (prom)', _pp(_vars_prom.get(c, 0)), round(_vars_prom.get(c, 0), 2)])
    _rows_doc.append(['Canastas', 'Brecha absoluta', _ar(_brecha_abs), round(_brecha_abs, 0)])
    _rows_doc.append(['Canastas', 'Brecha relativa (%)', _pct(_brecha_pct), round(_brecha_pct, 1)])
    # Provincias
    _rows_doc.append(['Provincias', 'País (Cuadro 1)', _ar(_v_media), round(_v_media, 0)])
    _rows_doc.append(['Provincias', 'Prov. más barata (nombre)', _prov_min['provincia'], _prov_min['provincia']])
    _rows_doc.append(['Provincias', 'Prov. más barata (valor)', _ar(_prov_min['canasta_total']), round(_prov_min['canasta_total'], 0)])
    _rows_doc.append(['Provincias', 'Prov. más barata (vs. prom.)', _pp(_prov_min['vs_%']), round(_prov_min['vs_%'], 2)])
    _rows_doc.append(['Provincias', 'Prov. más cara (nombre)', _prov_max['provincia'], _prov_max['provincia']])
    _rows_doc.append(['Provincias', 'Prov. más cara (valor)', _ar(_prov_max['canasta_total']), round(_prov_max['canasta_total'], 0)])
    _rows_doc.append(['Provincias', 'Prov. más cara (vs. prom.)', _pp(_prov_max['vs_%']), round(_prov_max['vs_%'], 2)])
    _rows_doc.append(['Provincias', 'Dispersión interprovincial (%)', _pct(_disp_prov), round(_disp_prov, 1)])
    _rows_doc.append(['Provincias', 'Dispersión inter-sucursal P5-P95 (%)', _pct(_disp_suc), round(_disp_suc, 1)])
    _rows_doc.append(['Provincias', 'P5 sucursales', _ar(_p05), round(_p05, 0)])
    _rows_doc.append(['Provincias', 'P25 sucursales', _ar(_p25), round(_p25, 0)])
    _rows_doc.append(['Provincias', 'P75 sucursales', _ar(_p75), round(_p75, 0)])
    _rows_doc.append(['Provincias', 'P95 sucursales', _ar(_p95), round(_p95, 0)])
    _rows_doc.append(['Provincias', 'Dispersión inter-sucursal mín-máx (%) — no publicar', _pct(_disp_suc_mm), round(_disp_suc_mm, 1)])
    _rows_doc.append(['Provincias', 'Sucursal más barata', _ar(_suc_min), round(_suc_min, 0)])
    _rows_doc.append(['Provincias', 'Sucursal más barata (cuál)', _suc_min_q, _suc_min_q])
    _rows_doc.append(['Provincias', 'Sucursal más cara', _ar(_suc_max), round(_suc_max, 0)])
    _rows_doc.append(['Provincias', 'Sucursal más cara (cuál)', _suc_max_q, _suc_max_q])
    # Cadenas nacionales (mediana por cadena, vs país del Cuadro 1)
    for _, r in _rk_nac.iterrows():
        _rows_doc.append(['Cadenas_Nacional', r['cadena'], _ar(r['valor']), round(r['valor'], 0)])
        _rows_doc.append(['Cadenas_Nacional', f"{r['cadena']} — vs país", _pp(r['vs_pais_%']), round(r['vs_pais_%'], 2)])
    _rows_doc.append(['Cadenas_Nacional', 'Dispersión (%)', _pct(_disp_cad_nac), round(_disp_cad_nac, 1)])
    # Cadenas AMBA (mediana por cadena, vs mediana del AMBA)
    if len(_rk_amba):
        _rows_doc.append(['Cadenas_AMBA', 'AMBA (mediana de sucursales)', _ar(_v_amba), round(_v_amba, 0)])
    for _, r in _rk_amba.iterrows():
        _rows_doc.append(['Cadenas_AMBA', r['cadena'], _ar(r['valor']), round(r['valor'], 0)])
        _rows_doc.append(['Cadenas_AMBA', f"{r['cadena']} — vs AMBA", _pp(r['vs_amba_%']), round(r['vs_amba_%'], 2)])
    if len(_rk_amba) >= 2:
        _rows_doc.append(['Cadenas_AMBA', 'Dispersión (%)', _pct(_disp_cad_amba), round(_disp_cad_amba, 1)])
    # Barrios CABA (mediana por barrio, vs CABA del Cuadro 1)
    for i, r in _brk.iterrows():
        _rows_doc.append(['Barrios_CABA', r['barrio'], _ar(r['valor']), round(r['valor'], 0)])
        _rows_doc.append(['Barrios_CABA', f"{r['barrio']} — vs CABA", _pp(r['vs_caba_%']), round(r['vs_caba_%'], 2)])
    _rows_doc.append(['Barrios_CABA', 'CABA (Cuadro 1)', _ar(_v_caba), round(_v_caba, 0)])
    _rows_doc.append(['Barrios_CABA', 'Dispersión barrios (%)', _pct(_disp_bar, 2), round(_disp_bar, 2)])
    # Canastas especiales
    if _prima_cel is not None:
        _rows_doc.append(['Especiales', 'Prima celíaca (%)', _pp(_prima_cel), round(_prima_cel, 2)])
    if _ahorro_veg is not None:
        _rows_doc.append(['Especiales', 'Ahorro vegano (%)', _pp(_ahorro_veg), round(_ahorro_veg, 2)])
    # Acumulados (mismo período que el IPC; el mes sin IPC, aparte)
    for c in _sorted_ids:
        if c in _acum:
            _rows_doc.append(['Acumulados', f'{CANASTA_NAMES[c]} {_M0_ACUM} a {_M1_ACUM}', _pp(_acum[c]), round(_acum[c], 2)])
    if _acum_ipc_gen is not None:
        _rows_doc.append(['Acumulados', f'IPC Nivel General {_M0_ACUM} a {_M1_ACUM}', _pp(_acum_ipc_gen), round(_acum_ipc_gen, 2)])
    if _acum_ipc_ali is not None:
        _rows_doc.append(['Acumulados', f'IPC Alimentos {_M0_ACUM} a {_M1_ACUM}', _pp(_acum_ipc_ali), round(_acum_ipc_ali, 2)])
    for c in _sorted_ids:
        if c in _acum_ult:
            _m, _v = _acum_ult[c]
            _rows_doc.append(['Acumulados', f'{CANASTA_NAMES[c]} {_M0_ACUM} a {_m} (sin IPC; no comparar)', _pp(_v), round(_v, 2)])
    # Variaciones últimos 3 meses
    for _, r in _ipc_tail3.iterrows():
        _rows_doc.append(['Var_3meses', f'IPC General {r["mes"]}', _pp(r['ipc_general_var_%']), round(r['ipc_general_var_%'], 2)])
        _rows_doc.append(['Var_3meses', f'IPC Alimentos {r["mes"]}', _pp(r['ipc_alimentos_var_%']), round(r['ipc_alimentos_var_%'], 2)])
    for c in CANASTAS_ACTIVAS:
        if c in _var3_canastas:
            for _m, _v in _var3_canastas[c]:
                _rows_doc.append(['Var_3meses', f'{CANASTA_NAMES[c]} {_m}', _pp(_v), round(_v, 2)])

    for row in _rows_doc:
        _ws.append(row)

    # Ancho de columnas
    _ws.column_dimensions['A'].width = 20
    _ws.column_dimensions['B'].width = 52
    _ws.column_dimensions['C'].width = 18
    _ws.column_dimensions['D'].width = 16

    _wb.save(_xls_path)
    print(f'Hoja Valores_Documento agregada a: {_xls_path.name}')
except Exception as _e:
    print(f'AVISO: No se pudo agregar hoja al Excel: {_e}')
"""))

# ── CELL 21 — DIAGNOSTIC: trazabilidad temporal de Candidatos ──────────────────
cells.append(cell_code("""\
# ============================================================
# CELDA 20 — DIAGNÓSTICO: Trazabilidad temporal de Candidatos
# ============================================================
# Lee hoja Candidatos, escanea ZIPs con usecols=['id_producto'] solo
# (~15-20 min). Muestra qué candidatos son estables históricamente.
# No modifica ninguna canasta — es solo informativo.

try:
    df_cand = pd.read_excel(CANASTA_EXCEL, sheet_name='Candidatos',
                            dtype={'id_producto': str})
    df_cand['ean_norm'] = df_cand['id_producto'].str.lstrip('0')
    CAND_EANS = set(df_cand['ean_norm'])
    print(f'Candidatos cargados: {len(CAND_EANS):,} EANs únicos')
except Exception as _e:
    raise RuntimeError(f'No se pudo leer hoja Candidatos: {_e}')

_presencia = {}
_meses_vis = []
for _zip_path, _anio, _sem in detectar_semestres():
    _meses = archivos_por_mes(_zip_path)
    for (_anio_m, _mes_m), _archs in sorted(_meses.items()):
        _lbl = f'{_anio_m}-{_mes_m:02d}'
        if _lbl < MES_INICIO_HISTORICO: continue
        _meses_vis.append(_lbl)
        _found = set()
        for _archivo in sorted(_archs):
            _tmp_p = TMP_DIR / Path(_archivo).name
            with zipfile.ZipFile(_zip_path) as _zf:
                with _zf.open(_archivo) as _s, open(_tmp_p, 'wb') as _d:
                    shutil.copyfileobj(_s, _d, length=4*1024*1024)
            with gzip.open(_tmp_p, 'rt', encoding='utf-8', errors='replace') as _g:
                for _chunk in pd.read_csv(_g, dtype={'id_producto': str},
                                           usecols=['id_producto'],
                                           chunksize=500_000, low_memory=False):
                    _chunk['ean_norm'] = _chunk['id_producto'].apply(normalizar_ean)
                    _found |= set(_chunk[_chunk['ean_norm'].isin(CAND_EANS)]['ean_norm'])
            _tmp_p.unlink(missing_ok=True)
        for _ean in _found:
            _presencia.setdefault(_ean, set()).add(_lbl)
        print(f'  {_lbl}: {len(_found):,} candidatos encontrados')

_n_meses = len(set(_meses_vis))
_mes_min  = min(_meses_vis) if _meses_vis else MES_INICIO_HISTORICO
_mes_max  = max(_meses_vis) if _meses_vis else ULTIMO_MES

_rows = []
for _ean, _mp in _presencia.items():
    _rows.append({'ean_norm':_ean,'meses_presentes':len(_mp),
                  'pct_trazabilidad':len(_mp)/_n_meses*100,
                  'primer_mes':min(_mp),'ultimo_mes':max(_mp),
                  'en_canasta':_ean in CANASTA_EANS_NORM})
for _ean in CAND_EANS - set(_presencia.keys()):
    _rows.append({'ean_norm':_ean,'meses_presentes':0,'pct_trazabilidad':0.0,
                  'primer_mes':None,'ultimo_mes':None,'en_canasta':_ean in CANASTA_EANS_NORM})

df_traz = pd.DataFrame(_rows)
_mc = ['ean_norm'] + [c for c in ['descripcion','marca','categoria','subcategoria',
                                   'precio_mediano','score_cobertura'] if c in df_cand.columns]
df_traz = (df_traz.merge(df_cand[_mc], on='ean_norm', how='left')
           .sort_values('pct_trazabilidad', ascending=False).reset_index(drop=True))

print(f'\\n{"="*60}')
print(f'  TRAZABILIDAD TEMPORAL — {_mes_min} a {_mes_max} ({_n_meses} meses)')
print(f'{"="*60}')
print(f'  Candidatos con trazabilidad 100%  : {(df_traz["pct_trazabilidad"]==100).sum():>5,}')
print(f'  Candidatos con trazabilidad  >90% : {(df_traz["pct_trazabilidad"]> 90).sum():>5,}')
print(f'  Candidatos con trazabilidad  >75% : {(df_traz["pct_trazabilidad"]> 75).sum():>5,}')
print(f'  Candidatos con trazabilidad  <50% : {(df_traz["pct_trazabilidad"]< 50).sum():>5,}')
_can_traz = df_traz[df_traz['en_canasta']]['pct_trazabilidad']
if len(_can_traz) > 0:
    print(f'\\n  EANs en canastas activas ({len(_can_traz)} únicos):')
    print(f'    Trazabilidad promedio : {_can_traz.mean():.1f}%')
    print(f'    Trazabilidad mínima   : {_can_traz.min():.1f}%')
print(f'{"="*60}')

_cols_show = [c for c in ['descripcion','marca','categoria','meses_presentes',
                           'pct_trazabilidad','primer_mes','en_canasta'] if c in df_traz.columns]
display(df_traz[_cols_show].head(30).style
    .background_gradient(subset=['pct_trazabilidad'], cmap='RdYlGn', vmin=0, vmax=100)
    .format({'pct_trazabilidad': '{:.1f}%'})
    .set_caption(f'Top 30 candidatos por trazabilidad ({_mes_min} → {_mes_max})'))

_fig, _axes = plt.subplots(1, 2, figsize=(14, 5))
_axes[0].hist(df_traz['pct_trazabilidad'], bins=20, color='#0055A4', edgecolor='white', alpha=0.85)
if len(_can_traz) > 0:
    _axes[0].axvline(_can_traz.mean(), color='#D62728', linewidth=2,
                     linestyle='--', label=f'Promedio canastas activas ({_can_traz.mean():.0f}%)')
    _axes[0].legend(fontsize=9)
_axes[0].set_xlabel('Trazabilidad temporal (%)'); _axes[0].set_ylabel('Número de productos')
_axes[0].set_title('Distribución de trazabilidad (todos los candidatos)')
if 'categoria' in df_traz.columns:
    _top_cat = (df_traz.groupby('categoria')['pct_trazabilidad']
                .agg(_mean='mean', _n='count').query('_n >= 5')
                .sort_values('_mean', ascending=True).tail(15))
    _axes[1].barh(_top_cat.index, _top_cat['_mean'], color='#0055A4', alpha=0.85)
    _axes[1].axvline(90, color='gray', linestyle='--', linewidth=1, alpha=0.6)
    _axes[1].set_xlabel('Trazabilidad promedio (%)'); _axes[1].set_xlim(0, 105)
    _axes[1].set_title('Trazabilidad por categoría (>=5 candidatos)')
    for _i, (_idx, _row) in enumerate(_top_cat.iterrows()):
        _axes[1].text(_row['_mean']+0.5, _i, f'{_row["_mean"]:.0f}%', va='center', fontsize=8)
plt.tight_layout()
_fig.savefig(OUTPUT_DIR / f'trazabilidad_candidatos_{ULTIMO_MES}.png', dpi=600, bbox_inches='tight')
plt.show()

_out_traz = OUTPUT_DIR / f'trazabilidad_candidatos_{ULTIMO_MES}.xlsx'
df_traz.to_excel(_out_traz, index=False)
print(f'Tabla completa guardada: {_out_traz.name}')"""))

# ── CELL 22 — DATOS ECONOMETRIA (motor semanal + mensual, histórico completo) ────
cells.append(cell_code(r'''# ============================================================
# CELDA 22 — DATOS ECONOMETRIA: series SEMANAL + MENSUAL por nivel (histórico completo)
# ============================================================
# Exporta un Excel tidy (formato largo) para análisis de series de tiempo:
#   - Costo de CADA canasta activa (cantidad_01..06 de la hoja Selección)
#   - Precio de 10 PRODUCTOS representativos (config abajo)
# con frecuencia SEMANAL (ISO) y MENSUAL, a nivel NACIONAL (ponderado por población),
# por PROVINCIA y por CADENA. Historia completa (>= MES_INICIO_HISTORICO).
# Cachea meses cerrados; relee el mes en curso fresco.

# ════════════════════════════════════════════════════════════════════════════════
# CONFIG PRODUCTOS (EDITAR ACÁ) — EAN -> nombre. Precio de cada uno por semana/mes,
# a nivel nacional / provincia / cadena. Todos verificados cad=5 / 24 provincias.
# Para cambiar la lista, editá este diccionario antes de ejecutar.
# ════════════════════════════════════════════════════════════════════════════════
PRODUCTOS_ECONOMETRIA = {
    # --- Bebidas ---
    '7790290101602': 'Fernet Branca 750 Ml',
    '7790895000232': 'Coca Cola Original Lata 354 Cc',
    '7790895067587': 'Coca Cola sin Azucar Lata 354 Cc',
    '7791250001345': 'Vodka Smirnoff 750 Cc',
    '7790950133325': 'Aperitivo Amargo Terma Light 1.35 Lt',
    '7790070760845': 'Espumante Brut Rose Nieto Senetiner 750 Ml',
    # --- Almacén ---
    '7790070012050': 'Aceite Girasol Cocinero 900 Ml',
    '7790070265098': 'Aceite Oliva Puro sin TACC 500 Ml',
    '7790387013610': 'Yerba Mate Taragui 4Flex 1 Kg',
    '7791004000051': 'Sal Entrefina Celusal 1 Kg',
    '7791866001364': 'Mayonesa Natura Doypack 500 Ml',
    '7794000008557': 'Caldo de Verdura Knorr 12 Un',
    '7790070318312': 'Fideos Fettucini Lucchetti 500 Gr',
    '7790070336293': 'Fideos Tirabuzon Matarazzo 500 Gr',
    '8445291121904': 'Cacao sin TACC Nesquik 800 Gr',
    '7622201808860': 'Galletitas Boca de Dama Terrabusi 170 Gr',
    # --- Frescos ---
    '7790742625205': 'Dulce de Leche Colonial La Serenisima 400 Gr',
    '7790742358509': 'Leche Parc Descremada La Serenisima 1 L',
    '7791337061361': 'Queso Crema Casancrem 290 Gr',
    # --- Limpieza / Perfumería ---
    '7793253003753': 'Lavandina Glaciar Ayudin 2 Lt',
    '7790740000264': 'Shampoo Plusbelle 1000 Cc',
    '7791070000696': 'Papel Higienico Campanita 4 Un',
    '7790010002714': 'Toallas Femeninas Siempre Libre 8 Un',
}   # 23 productos
ECON_MIN_SUC = 5          # mínimo de sucursales para reportar una celda provincia/cadena
ECON_XLSX    = OUTPUT_DIR / f'datos_econometria_{ULTIMO_MES}.xlsx'   # se guarda en el Drive

import datetime as _dt
PRODUCTOS_ECONOMETRIA = {normalizar_ean(k): v for k, v in PRODUCTOS_ECONOMETRIA.items()}
PROD_ECON_EANS = set(PRODUCTOS_ECONOMETRIA)
EANS_ECON = set(CANASTA_EANS_NORM) | PROD_ECON_EANS
_PAT_P8 = re.compile(r'^precio_\d{8}$')

def _fecha_de_periodo(_freq, _periodo):
    if _freq == 'mensual':
        _y, _m = _periodo.split('-'); return f'{_y}-{_m}-01'
    _y, _w = _periodo.split('-W')
    return _dt.date.fromisocalendar(int(_y), int(_w), 1).isoformat()

def _leer_mes_dia_econ(_lbl):
    # Devuelve [id_comercio,id_bandera,id_sucursal,ean_norm,fecha,precio] del mes _lbl
    _zip_path, _archs = _mapa_mes[_lbl]
    _rows = []
    for _archivo in sorted(_archs):
        _tmp = TMP_DIR / Path(_archivo).name
        with zipfile.ZipFile(_zip_path) as _zf:
            with _zf.open(_archivo) as _s, open(_tmp, 'wb') as _d:
                shutil.copyfileobj(_s, _d, length=4*1024*1024)
        with gzip.open(_tmp, 'rt', encoding='utf-8', errors='replace') as _g:
            for _ch in pd.read_csv(_g, dtype=str, chunksize=300_000, low_memory=False):
                _ch['ean_norm'] = _ch['id_producto'].apply(normalizar_ean)
                _ch = _ch[_ch['ean_norm'].isin(EANS_ECON)]
                if len(_ch) == 0: continue
                for _c in ['id_comercio','id_bandera','id_sucursal']:
                    _ch[_c] = _ch[_c].astype(str)
                _ch['_k'] = list(zip(_ch['id_comercio'], _ch['id_bandera'], _ch['id_sucursal']))
                _ch = _ch[_ch['_k'].isin(IDS_PAIS)].drop(columns='_k')
                if len(_ch) == 0: continue
                _cp = [c for c in _ch.columns if _PAT_P8.match(c)]
                if not _cp: continue
                _m = _ch.melt(id_vars=['id_comercio','id_bandera','id_sucursal','ean_norm'],
                              value_vars=_cp, var_name='_c', value_name='precio_raw')
                _m['precio'] = pd.to_numeric(_m['precio_raw'].replace('NA', np.nan), errors='coerce')
                _m = _m[_m['precio'].notna() & (_m['precio'] > 0)]
                if len(_m) == 0: continue
                _m['fecha'] = pd.to_datetime(_m['_c'].str[-8:], format='%Y%m%d', errors='coerce')
                _rows.append(_m[['id_comercio','id_bandera','id_sucursal','ean_norm','fecha','precio']])
        _tmp.unlink(missing_ok=True)
    if not _rows: return None
    _dd = pd.concat(_rows, ignore_index=True)
    _dd = _dd[_dd['fecha'].notna()].copy()
    if len(_dd) and _dd['precio'].median() > 10_000:
        _dd['precio'] /= 100
    return _dd

def _agg_desde_diario(_d):
    # Toma el df diario y devuelve filas LARGAS (tidy) para canastas y productos,
    # frecuencia semanal + mensual, niveles nacional/provincia/cadena.
    if _d is None or len(_d) == 0: return None
    _d = _d.copy()
    _d['mensual'] = _d['fecha'].dt.strftime('%Y-%m')
    _d['semanal'] = _d['fecha'].dt.strftime('%G-W%V')
    _k3 = ['id_comercio','id_bandera','id_sucursal']
    _out = []
    for _freq in ['mensual','semanal']:
        _key = _k3 + ['ean_norm', _freq]
        _md = _d.groupby(_key)['precio'].transform('median')
        _ok = (_d['precio'] >= _md/4) & (_d['precio'] <= _md*4)
        _gm = _d.groupby(_key)['precio'].median().rename('precio_med')
        _gp = _d[_ok].groupby(_key)['precio'].mean().rename('precio_prom')
        _px = pd.concat([_gm, _gp], axis=1).reset_index()
        _px['precio_prom'] = _px['precio_prom'].fillna(_px['precio_med'])
        _px = _px[~_px['id_comercio'].isin(CADENAS_FILTRAR)]
        _px = _px.merge(suc_geo_clean[_k3 + ['PROVINCIA_NORM','cadena']], on=_k3, how='inner')
        if len(_px) == 0: continue
        _nac = (_px.groupby(['ean_norm', _freq])
                   .agg(nac_med=('precio_med','median'), nac_prom=('precio_prom', _pmean))
                   .reset_index())
        _px = _px.merge(_nac, on=['ean_norm', _freq], how='left')

        # ---------------- CANASTAS ----------------
        for _col_id, _canasta in CANASTAS.items():
            _nm_can = CANASTA_NAMES[_col_id]
            _rec = pd.DataFrame([(e, q) for e, (nm, q, ct) in _canasta.items()],
                                columns=['ean_norm','qty'])
            _min_p = min(MIN_PRODUCTOS_PROPIOS, len(_canasta))
            _pr = _px.merge(_rec, on='ean_norm', how='inner')
            if len(_pr) == 0: continue
            _pr['store_m'] = _pr['precio_med']  * _pr['qty']
            _pr['store_p'] = _pr['precio_prom'] * _pr['qty']
            _pr['nacv_m']  = _pr['nac_med']  * _pr['qty']
            _pr['nacv_p']  = _pr['nac_prom'] * _pr['qty']
            _g = (_pr.groupby(_k3 + [_freq, 'PROVINCIA_NORM', 'cadena'])
                     .agg(S_store_m=('store_m','sum'), S_store_p=('store_p','sum'),
                          S_nac_m=('nacv_m','sum'),   S_nac_p=('nacv_p','sum'),
                          n_prop=('qty','count')).reset_index())
            _rn = _nac.merge(_rec, on='ean_norm', how='inner')
            _rn['am'] = _rn['nac_med']  * _rn['qty']
            _rn['ap'] = _rn['nac_prom'] * _rn['qty']
            _allnac = _rn.groupby(_freq)[['am','ap']].sum().reset_index().rename(
                columns={'am':'all_m','ap':'all_p'})
            _g = _g.merge(_allnac, on=_freq, how='left')
            _g['valor_med']  = _g['S_store_m'] + (_g['all_m'] - _g['S_nac_m'])
            _g['valor_prom'] = _g['S_store_p'] + (_g['all_p'] - _g['S_nac_p'])
            _g = _g[_g['n_prop'] >= _min_p]
            if len(_g) == 0: continue

            # provincia
            _pv = (_g.groupby([_freq,'PROVINCIA_NORM'])
                     .agg(valor_mediana=('valor_med','median'),
                          valor_promedio=('valor_prom', _pmean),
                          n_sucursales=('valor_med','size')).reset_index())
            _pv = _pv[_pv['n_sucursales'] >= ECON_MIN_SUC]
            for _, r in _pv.iterrows():
                _out.append((_freq, r[_freq], 'canasta', _nm_can, 'provincia', r['PROVINCIA_NORM'],
                             int(r['n_sucursales']), r['valor_mediana'], r['valor_promedio']))
            # cadena
            _cd = (_g.groupby([_freq,'cadena'])
                     .agg(valor_mediana=('valor_med','median'),
                          valor_promedio=('valor_prom', _pmean),
                          n_sucursales=('valor_med','size')).reset_index())
            _cd = _cd[_cd['n_sucursales'] >= ECON_MIN_SUC]
            for _, r in _cd.iterrows():
                _out.append((_freq, r[_freq], 'canasta', _nm_can, 'cadena', r['cadena'],
                             int(r['n_sucursales']), r['valor_mediana'], r['valor_promedio']))
            # nacional ponderado por población (mediana provincial -> peso poblacional)
            _pvw = _pv.copy()
            _pvw['peso'] = _pvw['PROVINCIA_NORM'].map(PESOS_POBLACION).fillna(0)
            for _per, _sub in _pvw.groupby(_freq):
                _w = _sub[_sub['peso'] > 0]['peso'].sum()
                if _w > 0:
                    _vm = (_sub['valor_mediana'] * _sub['peso']).sum() / _w
                    _vp = (_sub['valor_promedio'] * _sub['peso']).sum() / _w
                else:
                    _vm = _sub['valor_mediana'].mean(); _vp = _sub['valor_promedio'].mean()
                _nsu = int(_g[_g[_freq] == _per]['id_sucursal'].nunique())
                _out.append((_freq, _per, 'canasta', _nm_can, 'nacional', 'Nacional',
                             _nsu, _vm, _vp))

        # ---------------- PRODUCTOS ----------------
        _pp = _px[_px['ean_norm'].isin(PROD_ECON_EANS)].copy()
        if len(_pp):
            _pp['prod'] = _pp['ean_norm'].map(PRODUCTOS_ECONOMETRIA)
            # provincia
            _ppv = (_pp.groupby([_freq,'prod','PROVINCIA_NORM'])
                      .agg(valor_mediana=('precio_med','median'),
                           valor_promedio=('precio_prom', _pmean),
                           n_sucursales=('precio_med','size')).reset_index())
            _ppv = _ppv[_ppv['n_sucursales'] >= ECON_MIN_SUC]
            for _, r in _ppv.iterrows():
                _out.append((_freq, r[_freq], 'producto', r['prod'], 'provincia', r['PROVINCIA_NORM'],
                             int(r['n_sucursales']), r['valor_mediana'], r['valor_promedio']))
            # cadena
            _pcd = (_pp.groupby([_freq,'prod','cadena'])
                      .agg(valor_mediana=('precio_med','median'),
                           valor_promedio=('precio_prom', _pmean),
                           n_sucursales=('precio_med','size')).reset_index())
            _pcd = _pcd[_pcd['n_sucursales'] >= ECON_MIN_SUC]
            for _, r in _pcd.iterrows():
                _out.append((_freq, r[_freq], 'producto', r['prod'], 'cadena', r['cadena'],
                             int(r['n_sucursales']), r['valor_mediana'], r['valor_promedio']))
            # nacional (mediana y promedio simples entre sucursales)
            _pnc = (_pp.groupby([_freq,'prod'])
                      .agg(valor_mediana=('precio_med','median'),
                           valor_promedio=('precio_prom', _pmean),
                           n_sucursales=('precio_med','size')).reset_index())
            for _, r in _pnc.iterrows():
                _out.append((_freq, r[_freq], 'producto', r['prod'], 'nacional', 'Nacional',
                             int(r['n_sucursales']), r['valor_mediana'], r['valor_promedio']))
    if not _out: return None
    return pd.DataFrame(_out, columns=['frecuencia','periodo','tipo','clave','nivel','grupo',
                                       'n_sucursales','valor_mediana','valor_promedio'])

# ── Recorrer historia con caché (meses cerrados) + mes en curso fresco ──────────
# Clave: EANs + provincia y cadena de cada sucursal (CELDA 7). Si cambia la geografía (BUG-44, 2026-10-16: provincia
# por polígonos) los meses guardados tendrían la provincia vieja y la serie se cortaría en el mes nuevo: se releen.
_geo_econ = suc_geo_clean[['id_comercio', 'id_bandera', 'id_sucursal', 'PROVINCIA_NORM', 'cadena']].astype(str)
_econ_key = hashlib.md5(('|'.join(sorted(EANS_ECON)) + '|econv1|'
                         + _geo_econ.sort_values(list(_geo_econ.columns)).to_csv(index=False)).encode()).hexdigest()[:8]
_econ_cache = CACHE_DIR / f'econ_{_econ_key}.parquet'
_econ_mes_actual = _meses_disp[-1]

if USE_CACHE and _econ_cache.exists():
    _econ_df = pd.read_parquet(_econ_cache)
    _econ_df = _econ_df[_econ_df['_mes_src'] < _econ_mes_actual].copy()
else:
    _econ_df = pd.DataFrame()

_en_cache = set(_econ_df['_mes_src'].unique()) if len(_econ_df) else set()
_falt = [m for m in _meses_disp if m < _econ_mes_actual and m not in _en_cache]
print(f'Datos econometria: {len(_meses_disp)} meses | en cache: {len(_en_cache)} | a leer: {len(_falt)}')
_nuevos_e = []
for _lbl in _falt:
    _r = _agg_desde_diario(_leer_mes_dia_econ(_lbl))
    if _r is not None:
        _r['_mes_src'] = _lbl
        _nuevos_e.append(_r)
        print(f'  {_lbl}: {len(_r)} filas')
    gc.collect()
if _nuevos_e:
    _econ_df = pd.concat([_econ_df] + _nuevos_e, ignore_index=True)
    if USE_CACHE:
        _econ_df.to_parquet(_econ_cache, compression='snappy', index=False)
        print(f'Cache econometria actualizado: {_econ_cache.name}')

# Mes en curso: siempre fresco
_r_act = _agg_desde_diario(_leer_mes_dia_econ(_econ_mes_actual))
if _r_act is not None:
    _r_act['_mes_src'] = _econ_mes_actual
    print(f'  {_econ_mes_actual}: {len(_r_act)} filas (mes en curso — fresco)')
econ_long = pd.concat([_econ_df] + ([_r_act] if _r_act is not None else []), ignore_index=True)
econ_long = econ_long[econ_long['periodo'].notna()].copy()
# Semanas ISO de BORDE: una misma semana partida entre 2 archivos mensuales genera
# fragmentos duplicados. Se asigna cada semana a su mes "dueño" (el del jueves ISO)
# y se conserva ese fragmento (el más completo). Los meses no tienen este problema.
def _owner_mes(_p):
    _y, _w = _p.split('-W')
    return _dt.date.fromisocalendar(int(_y), int(_w), 4).strftime('%Y-%m')
_wk = econ_long[econ_long['frecuencia'] == 'semanal'].copy()
_ms = econ_long[econ_long['frecuencia'] == 'mensual'].copy()
if len(_wk):
    _wk['_own'] = _wk['periodo'].map(_owner_mes)
    _wk['_is_own'] = (_wk['_own'] == _wk['_mes_src']).astype(int)
    _wk = (_wk.sort_values('_is_own', ascending=False)
             .drop_duplicates(['tipo','clave','nivel','grupo','periodo'], keep='first')
             .drop(columns=['_own','_is_own']))
econ_long = pd.concat([_ms, _wk], ignore_index=True)
econ_long['fecha'] = [ _fecha_de_periodo(f, p) for f, p in zip(econ_long['frecuencia'], econ_long['periodo']) ]
econ_long = econ_long.drop(columns=['_mes_src'])
econ_long = econ_long.sort_values(['tipo','clave','nivel','grupo','frecuencia','fecha']).reset_index(drop=True)
# variación % dentro de cada serie
econ_long['variacion_%'] = (econ_long.groupby(['frecuencia','tipo','clave','nivel','grupo'])['valor_mediana']
                            .pct_change() * 100)
print(f'econ_long: {len(econ_long):,} filas | periodos {econ_long["periodo"].nunique()}')'''))

# ── CELL 23 — DATOS ECONOMETRIA: exportar Excel tidy ────────────────────────────
cells.append(cell_code(r'''# ============================================================
# CELDA 23 — DATOS ECONOMETRIA: exportar Excel tidy (una hoja por tipo x nivel)
# ============================================================
_COLS = ['frecuencia','periodo','fecha','clave','grupo','n_sucursales',
         'valor_mediana','valor_promedio','variacion_%']

def _hoja(_tipo, _nivel):
    _s = econ_long[(econ_long['tipo'] == _tipo) & (econ_long['nivel'] == _nivel)].copy()
    if _nivel == 'nacional':
        _cols = [c for c in _COLS if c != 'grupo']
    else:
        _cols = _COLS
    return _s[_cols].sort_values(['clave','grupo','frecuencia','fecha'] if _nivel != 'nacional'
                                 else ['clave','frecuencia','fecha']).reset_index(drop=True)

_dicc = pd.DataFrame([
    ('frecuencia',    'semanal (ISO) o mensual'),
    ('periodo',       'etiqueta del período: YYYY-Www (semana ISO) o YYYY-MM (mes)'),
    ('fecha',         'fecha real: lunes de la semana ISO, o primer día del mes (para series de tiempo)'),
    ('clave',         'nombre de la canasta (cantidad_01..06) o del producto'),
    ('nivel',         'nacional | provincia | cadena (en el nombre de la hoja)'),
    ('grupo',         'provincia o cadena concreta (Nacional en las hojas nacionales)'),
    ('n_sucursales',  'nº de sucursales que respaldan el valor'),
    ('valor_mediana', 'costo de canasta / precio de producto — MEDIANA entre sucursales'),
    ('valor_promedio','ídem — PROMEDIO con outliers fuera [mediana/4, mediana x4]'),
    ('variacion_%',   'variación % del valor_mediana respecto del período anterior de esa serie'),
    ('nacional (canasta)', 'ponderado por población provincial (mediana provincial -> peso poblacional)'),
    ('nacional (producto)','mediana/promedio simple entre sucursales del país'),
    ('imputación',    'items faltantes en una sucursal se imputan con la referencia nacional del período'),
    ('umbral',        f'se reportan celdas provincia/cadena con n_sucursales >= {ECON_MIN_SUC}'),
], columns=['campo','descripcion'])

with pd.ExcelWriter(ECON_XLSX, engine='openpyxl') as _w:
    _dicc.to_excel(_w, sheet_name='Diccionario', index=False)
    _hoja('canasta','nacional').to_excel(_w, sheet_name='canastas_nacional', index=False)
    _hoja('canasta','provincia').to_excel(_w, sheet_name='canastas_provincia', index=False)
    _hoja('canasta','cadena').to_excel(_w, sheet_name='canastas_cadena', index=False)
    _hoja('producto','nacional').to_excel(_w, sheet_name='productos_nacional', index=False)
    _hoja('producto','provincia').to_excel(_w, sheet_name='productos_provincia', index=False)
    _hoja('producto','cadena').to_excel(_w, sheet_name='productos_cadena', index=False)

print(f'✅ Excel econometria guardado: {ECON_XLSX}')
_res = (econ_long.groupby(['tipo','nivel','frecuencia'])
        .agg(filas=('valor_mediana','size'), series=('clave','nunique'),
             periodos=('periodo','nunique')).reset_index())
print(_res.to_string(index=False))
_prod_con = set(econ_long[econ_long['tipo']=='producto']['clave'])
_prod_sin = [v for v in PRODUCTOS_ECONOMETRIA.values() if v not in _prod_con]
if _prod_sin:
    print(f'⚠️ Productos SIN datos (revisar EAN en PRODUCTOS_ECONOMETRIA): {_prod_sin}')'''))

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
out_path = os.path.join(script_dir, '02_evolucion_canasta_representativa.ipynb')
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f'Written: {out_path}')
print(f'Cells: {len(cells)}')
