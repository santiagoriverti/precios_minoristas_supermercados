"""Script to generate 02_evolucion_canasta_representativa.ipynb"""
import json, os

def cell_md(src):
    lines = src.split('\n')
    source = [l + '\n' for l in lines[:-1]] + ([lines[-1]] if lines[-1] else [])
    return {'cell_type':'markdown','id':f'md{abs(hash(src))%65536:04x}','metadata':{},'source':source}

def cell_code(src):
    return {'cell_type':'code','execution_count':None,'id':f'c{abs(hash(src))%65536:04x}','metadata':{},'outputs':[],'source':[src]}

cells = []

# CELL 0
cells.append(cell_md("""# SEPA — Evolución de la Canasta Representativa

**Objetivo:** Calcular el costo mensual de la canasta elegida por el economista, mapearlo por provincia, compararlo con el IPC INDEC, y generar rankings por cadena y barrio.

**Canasta:** leída automáticamente desde la pestaña `Selección` del Excel `canasta_representativa_YYYY-MM.xlsx` (campo `cantidad` completado por el economista).

**Estructura:** Config → Setup → Canasta desde Excel → Maestros → ZIPs → Mes actual per-sucursal → Canasta por sucursal → Análisis provincial → Serie histórica → IPC → Comparativa → Gráficos IPC → Cuadro 1 → Mapa coroplético → Cobertura → Rankings → Mapa Folium → Ranking CABA → Excel"""))

# CELL 1 — CONFIG
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

# Mes base para gráficos de índice (debe estar en la serie histórica)
MES_INICIO_GRAFICO = '2024-03'

# Mínimo productos propios para incluir sucursal en análisis
MIN_PRODUCTOS_PROPIOS = 15

# Mínimo sucursales por cadena para aparecer en rankings
MIN_SUCURSALES_RANKING = 10"""))

# CELL 2 — SETUP
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

# Buscar IPC.xlsx / ipc.xlsx (case-insensitive: en Colab el filesystem es case-sensitive)
_ipc_candidatos = [SEPA_DIR / n for n in ('IPC.xlsx', 'ipc.xlsx', 'IPC.XLSX')]
_ipc_encontrado = next((p for p in _ipc_candidatos if p.exists()), None)
IPC_PATH     = _ipc_encontrado if _ipc_encontrado else SEPA_DIR / 'IPC.xlsx'
GEOJSON_PATH = SEPA_DIR / 'ar.json'

print(f'SEPA_DIR:   {SEPA_DIR}')
print(f'OUTPUT_DIR: {OUTPUT_DIR}')
print(f'  IPC.xlsx: {"OK — " + IPC_PATH.name if IPC_PATH.exists() else "NO ENCONTRADO"}')
print(f'  ar.json:  {"OK" if GEOJSON_PATH.exists() else "NO ENCONTRADO"}')"""))

# CELL 3 — CANASTA FROM EXCEL
cells.append(cell_code("""\
# ============================================================
# CELDA 3 — Canasta desde Excel (hoja Seleccion)
# El economista completa la columna `cantidad` en esa hoja.
# ============================================================
import glob as _glob

patrones = sorted(_glob.glob(str(OUTPUT_DIR / 'canasta_representativa_*.xlsx')), reverse=True)
if not patrones:
    raise FileNotFoundError(
        f'No se encontro canasta_representativa_*.xlsx en {OUTPUT_DIR}\\n'
        'Ejecuta primero exploracion_productos.ipynb y completa la columna '
        'cantidad en la hoja Seleccion.'
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
sel['cantidad'] = pd.to_numeric(sel['cantidad'], errors='coerce').fillna(0).astype(int)
sel_activa = sel[sel['cantidad'] > 0].copy().reset_index(drop=True)

if len(sel_activa) == 0:
    raise ValueError(
        'La hoja Seleccion no tiene ningun producto con cantidad > 0.\\n'
        'Completa la columna cantidad para los productos de tu canasta.'
    )

sel_activa['ean_norm']  = sel_activa['id_producto'].str.lstrip('0')
sel_activa['ean_zfill'] = sel_activa['id_producto'].str.zfill(13)

# Resolver nombre de columnas (puede variar entre versiones del notebook 1)
desc_col = next((c for c in ['descripcion','descripcion_producto','nombre']
                 if c in sel_activa.columns), sel_activa.columns[3])
cat_col  = next((c for c in ['categoria','rubro'] if c in sel_activa.columns), 'categoria')

CANASTA = {
    row['ean_norm']: (str(row[desc_col])[:50], int(row['cantidad']), str(row[cat_col]))
    for _, row in sel_activa.iterrows()
}

CANASTA_EANS_NORM  = set(CANASTA.keys())
CANASTA_EANS_ZFILL = {e.zfill(13) for e in CANASTA_EANS_NORM}
N_CANASTA = len(CANASTA)

ean_qty  = lambda e: CANASTA.get(e, ('?', 1, '?'))[1]
ean_cat  = lambda e: CANASTA.get(e, ('?', 1, '?'))[2]
ean_desc = lambda e: CANASTA.get(e, (e,  1, '?'))[0]

print(f'Canasta: {N_CANASTA} productos, {sel_activa["cantidad"].sum()} unidades/mes')
print()
print(sel_activa.groupby(cat_col).agg(
    n_prod=('cantidad','count'), unidades=('cantidad','sum')
).to_string())"""))

# CELL 4 — MAESTROS
cells.append(cell_code("""\
# ============================================================
# CELDA 4 — Maestros de sucursales, cadenas, provincias
# ============================================================
DATA_URL = 'https://raw.githubusercontent.com/santiagoriverti/precios_minoristas_supermercados/main/data'

def leer_maestro(nombre):
    local = Path('data') / nombre
    if local.exists():
        return pd.read_excel(local)
    import urllib.request
    dl = Path('/content/data') / nombre
    Path('/content/data').mkdir(exist_ok=True)
    if not dl.exists():
        print(f'  Descargando {nombre}...')
        urllib.request.urlretrieve(f'{DATA_URL}/{nombre}', dl)
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

# CELL 5 — ZIP FUNCTIONS
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

# CELL 6 — CURRENT MONTH
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
datos = datos.drop_duplicates(
    subset=['id_comercio','id_bandera','id_sucursal','ean_norm'], keep='first')

# Factor precio
ref_e = {'7790072002080'.lstrip('0'), '7790070320285'.lstrip('0'), '7790132098459'.lstrip('0')}
ref_d = datos[datos['ean_norm'].isin(ref_e)]
med_r = ref_d['precio'].median() if len(ref_d) > 0 else datos['precio'].median()
FACTOR = 100 if med_r > 10_000 else 1
if FACTOR == 100:
    datos['precio'] /= 100
    print(f'Factor: {FACTOR} (centavos -> pesos)')
else:
    print(f'Factor: {FACTOR} (ya en pesos)')

print(f'Datos: {len(datos):,} obs | {datos.groupby(["id_comercio","id_bandera","id_sucursal"]).ngroups:,} sucursales')
print(f'EANs con datos: {datos["ean_norm"].nunique()} / {N_CANASTA}')"""))

# CELL 7 — PER-SUCURSAL BASKET
cells.append(cell_code("""\
# ============================================================
# CELDA 7 — Canasta por sucursal -> canasta_geo_filtros
# ============================================================
precio_mes = (datos.groupby(['id_comercio','id_bandera','id_sucursal','ean_norm'])
              ['precio'].mean().reset_index())
precio_mes = precio_mes[~precio_mes['id_comercio'].isin(CADENAS_FILTRAR)].copy()

precio_prom_nac = precio_mes.groupby('ean_norm')['precio'].mean().to_dict()

def calcular_canasta_completa(grupo):
    locales = dict(zip(grupo['ean_norm'], grupo['precio']))
    total = 0; propios = 0; detalle = []
    for ean_norm, (nombre, qty, cat) in CANASTA.items():
        if ean_norm in locales:
            precio = locales[ean_norm]; es_propio = True; propios += 1
        else:
            precio = precio_prom_nac.get(ean_norm, 0); es_propio = False
        subtotal = precio * qty; total += subtotal
        detalle.append((nombre, cat, qty, precio, subtotal, es_propio))
    return pd.Series({'canasta_total':total,'productos_propios':propios,'detalle_productos':detalle})

print('Calculando canasta por sucursal...')
canasta_suc = (precio_mes.groupby(['id_comercio','id_bandera','id_sucursal'])
               .apply(calcular_canasta_completa, include_groups=False)
               .reset_index())
canasta_suc = canasta_suc[canasta_suc['productos_propios'] >= MIN_PRODUCTOS_PROPIOS].copy()
print(f'  Sucursales validas (>={MIN_PRODUCTOS_PROPIOS} productos): {len(canasta_suc):,}')

# Merge geografia
cols_suc = ['id_comercio','id_bandera','id_sucursal',
            'sucursales_nombre','sucursales_latitud','sucursales_longitud',
            'sucursales_barrio','sucursales_localidad','PROVINCIA']
if 'sucursales_tipo' in suc_pais.columns:
    cols_suc.append('sucursales_tipo')

canasta_geo = canasta_suc.merge(suc_pais[cols_suc].copy(),
                                on=['id_comercio','id_bandera','id_sucursal'], how='inner')

if 'sucursales_tipo' not in canasta_geo.columns:
    canasta_geo['sucursales_tipo'] = 'N/D'

canasta_geo['cadena'] = canasta_geo.apply(asignar_cadena, axis=1)
canasta_geo['PROVINCIA_NORM'] = canasta_geo['PROVINCIA'].map(PROV_NORM).fillna(canasta_geo['PROVINCIA'])

# Limpiar
canasta_geo = canasta_geo[canasta_geo['sucursales_tipo'] != 'Web'].copy()
mask_caba_bad = (
    canasta_geo['PROVINCIA_NORM'].eq('CABA') & (
        (canasta_geo['sucursales_latitud'] < -34.71) |
        (canasta_geo['sucursales_latitud'] > -34.53) |
        (canasta_geo['sucursales_longitud'] < -58.53) |
        (canasta_geo['sucursales_longitud'] > -58.34)
    ))
if mask_caba_bad.sum():
    print(f'  Eliminando {mask_caba_bad.sum()} sucursales mal clasificadas como CABA')
    canasta_geo = canasta_geo[~mask_caba_bad].copy()

canasta_geo_filtros = canasta_geo.copy()
print(f'canasta_geo_filtros: {len(canasta_geo_filtros):,} sucursales')
print(f'  Rango: ${canasta_geo_filtros["canasta_total"].min():,.0f} – ${canasta_geo_filtros["canasta_total"].max():,.0f}')
print()
print(canasta_geo_filtros['cadena'].value_counts().to_string())"""))

# CELL 8 — PROVINCE ANALYSIS
cells.append(cell_code("""\
# ============================================================
# CELDA 8 — Analisis provincial -> serie_provincia_valida
# ============================================================
canasta_por_prov = (
    canasta_geo_filtros.groupby('PROVINCIA_NORM')['canasta_total']
    .median().reset_index()
    .rename(columns={'PROVINCIA_NORM':'provincia','canasta_total':'canasta_total'})
)
canasta_por_prov['mes'] = PERIODO
serie_provincia_valida = canasta_por_prov[['mes','provincia','canasta_total']].copy()

# Promedio nacional ponderado por poblacion
canasta_por_prov['peso'] = canasta_por_prov['provincia'].map(PESOS_POBLACION).fillna(0)
pob_cobertura = canasta_por_prov[canasta_por_prov['peso'] > 0]['peso'].sum()
prom_nac_ponderado = (
    (canasta_por_prov['canasta_total'] * canasta_por_prov['peso']).sum() / pob_cobertura
    if pob_cobertura > 0 else canasta_por_prov['canasta_total'].mean()
)

def fmt_ar(x, dec=0):
    s = f'{x:,.{dec}f}'
    return s.replace(',','X').replace('.',',').replace('X','.')

print(f'=== CUADRO: Canasta por provincia — {NOMBRE_MES_TITLE} ===\\n')
df_disp = serie_provincia_valida.sort_values('canasta_total').copy()
df_disp['vs_%'] = ((df_disp['canasta_total'] / prom_nac_ponderado) - 1) * 100
for _, r in df_disp.iterrows():
    print(f'  {r["provincia"]:<25} ${r["canasta_total"]:>10,.0f}  {r["vs_%"]:+.2f}%')
print(f'  {"Promedio (ponderado)":<25} ${prom_nac_ponderado:>10,.0f}   0.00%')
print(f'\\nProvincias con datos: {len(serie_provincia_valida)}')"""))

# CELL 9 — HISTORICAL
cells.append(cell_code("""\
# ============================================================
# CELDA 9 — Serie historica nacional (con cache por hash EANs)
# ============================================================
# Hash incluye EANs + cantidades → cambiar cantidades invalida el cache
_cache_key  = hashlib.md5('|'.join(f'{k}:{CANASTA[k][1]}' for k in sorted(CANASTA.keys())).encode()).hexdigest()[:8]
_cache_path = CACHE_DIR / f'hist_{_cache_key}.parquet'

if USE_CACHE and _cache_path.exists():
    print(f'Cargando cache: {_cache_path.name}')
    df_hist = pd.read_parquet(_cache_path)
else:
    sems = detectar_semestres()
    registros = []
    for zip_path, anio, sem in sems:
        meses = archivos_por_mes(zip_path)
        for (anio_m, mes_m), archs in sorted(meses.items()):
            lbl = f'{anio_m}-{mes_m:02d}'
            if lbl < MES_INICIO_HISTORICO:
                continue
            all_rows = []
            for archivo in sorted(archs):
                tmp_p = TMP_DIR / Path(archivo).name
                with zipfile.ZipFile(zip_path) as zf:
                    with zf.open(archivo) as s, open(tmp_p,'wb') as d:
                        shutil.copyfileobj(s, d, length=4*1024*1024)
                with gzip.open(tmp_p,'rt',encoding='utf-8',errors='replace') as g:
                    for chunk in pd.read_csv(g, dtype=str, chunksize=300_000, low_memory=False):
                        chunk['ean_norm'] = chunk['id_producto'].apply(normalizar_ean)
                        chunk = chunk[chunk['ean_norm'].isin(CANASTA_EANS_NORM)].copy()
                        if len(chunk) == 0: continue
                        cols_p = [c for c in chunk.columns if re.match(r'^precio_\\d{8}$', c)]
                        if not cols_p: continue
                        sub = chunk[['ean_norm'] + cols_p].copy()
                        for cp in cols_p:
                            sub[cp] = pd.to_numeric(sub[cp].replace('NA',np.nan), errors='coerce')
                        mlt = sub.melt(id_vars='ean_norm', value_vars=cols_p,
                                       var_name='_c', value_name='precio')
                        mlt = mlt[mlt['precio'].notna() & (mlt['precio'] > 0)]
                        all_rows.append(mlt[['ean_norm','precio']])
                tmp_p.unlink(missing_ok=True)
            if not all_rows:
                continue
            df_m = pd.concat(all_rows, ignore_index=True)
            med_raw = df_m['precio'].median()
            fac = 100 if med_raw > 10_000 else 1
            if fac == 100: df_m['precio'] /= 100
            agg = df_m.groupby('ean_norm')['precio'].median().reset_index(name='precio_mediano')
            agg['anio_mes'] = lbl
            registros.append(agg)
            print(f'  {lbl}: {agg["ean_norm"].nunique()} EANs | factor={fac}')
            del df_m, agg, all_rows; gc.collect()

    df_hist = pd.concat(registros, ignore_index=True) if registros else pd.DataFrame(
        columns=['ean_norm','precio_mediano','anio_mes'])
    if USE_CACHE and len(df_hist) > 0:
        df_hist.to_parquet(_cache_path, compression='snappy', index=False)
        print(f'Cache guardado: {_cache_path}')

df_hist['qty']        = df_hist['ean_norm'].map(ean_qty)
df_hist['costo_item'] = df_hist['precio_mediano'] * df_hist['qty']

serie_nac = (df_hist.groupby('anio_mes')
             .agg(canasta_nacional_ponderada=('costo_item','sum'), n_eans=('ean_norm','nunique'))
             .reset_index()
             .rename(columns={'anio_mes': 'mes'})
             .sort_values('mes').reset_index(drop=True))
serie_nac = serie_nac[serie_nac['mes'] >= MES_INICIO_HISTORICO].copy()
serie_nac['variacion_mensual_%'] = serie_nac['canasta_nacional_ponderada'].pct_change() * 100

base_v = serie_nac['canasta_nacional_ponderada'].iloc[0]
serie_nac['indice_canasta_base100'] = (serie_nac['canasta_nacional_ponderada'] / base_v * 100).round(2)
serie_nacional_valida = serie_nac.copy()

print(f'Serie historica: {len(serie_nacional_valida)} meses')
print(f'  Periodo: {serie_nacional_valida["mes"].min()} -> {serie_nacional_valida["mes"].max()}')"""))

# CELL 10 — IPC
cells.append(cell_code("""\
# ============================================================
# CELDA 10 — IPC INDEC desde carga/IPC.xlsx
# Formato real: columna 'date' = datetime64 (Excel seriales),
# demás columnas = float64 con punto decimal.
# ============================================================
if not IPC_PATH.exists():
    raise FileNotFoundError(
        f'IPC.xlsx no encontrado en {SEPA_DIR}\\n'
        'Asegurate de tener el archivo IPC.xlsx (o ipc.xlsx) en la carpeta carga/'
    )

ipc_raw = pd.read_excel(IPC_PATH)
print(f'IPC cargado: {len(ipc_raw)} filas, columnas: {list(ipc_raw.columns[:4])} ...')

# Detectar columna de fecha
fecha_col = next((c for c in ipc_raw.columns
                  if str(c).lower().strip() in ('date','fecha','mes','period')),
                 ipc_raw.columns[0])

# Parsear fecha:
#   Caso normal (IPC.xlsx real): columna ya es datetime64 porque Excel guarda
#   fechas como seriales numéricos y pandas los convierte automáticamente.
#   La visualización 'ene-2017' en Excel es solo formato de celda, no el dato.
#   Caso fallback: texto 'ene-2017' (si alguna versión exportó como texto).
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

# Renombrar columnas de interés
rename_map = {}
for c in ipc_raw.columns:
    cs = str(c).strip()
    if 'nivel general' in cs.lower():               rename_map[c] = 'ipc_general'
    elif 'alimentos y bebidas no alc' in cs.lower(): rename_map[c] = 'ipc_alimentos'
ipc_raw = ipc_raw.rename(columns=rename_map)

# Convertir a float (normalmente ya son float64; por robustez también maneja coma decimal)
for c in ['ipc_general','ipc_alimentos']:
    if c in ipc_raw.columns:
        ipc_raw[c] = pd.to_numeric(
            ipc_raw[c].astype(str).str.replace(',', '.', regex=False), errors='coerce')

# Construir serie IPC (con fallback si falta columna ipc_alimentos)
_ipc_cols = ['mes','ipc_general'] + (['ipc_alimentos'] if 'ipc_alimentos' in ipc_raw.columns else [])
ipc = (ipc_raw[_ipc_cols]
       .dropna(subset=['ipc_general']).sort_values('mes').reset_index(drop=True))
if 'ipc_alimentos' not in ipc.columns:
    ipc['ipc_alimentos'] = np.nan
    print('AVISO: no se encontro columna Alimentos y bebidas — se usara NaN')
ipc['ipc_general_var_%']   = ipc['ipc_general'].pct_change(fill_method=None) * 100
ipc['ipc_alimentos_var_%'] = ipc['ipc_alimentos'].pct_change(fill_method=None) * 100

print(f'IPC procesado: {len(ipc)} meses | {ipc["mes"].min()} -> {ipc["mes"].max()}')
print(ipc[['mes','ipc_general','ipc_general_var_%','ipc_alimentos','ipc_alimentos_var_%']].tail(6).to_string(index=False))"""))

# CELL 11 — COMPARATIVA
cells.append(cell_code("""\
# ============================================================
# CELDA 11 — Tabla comparativa SEPA vs IPC
# ============================================================
comparativa = serie_nacional_valida.merge(
    ipc[['mes','ipc_general','ipc_general_var_%','ipc_alimentos','ipc_alimentos_var_%']],
    on='mes', how='left')

ipc_b  = comparativa['ipc_general'].dropna().iloc[0]
ialb   = comparativa['ipc_alimentos'].dropna().iloc[0]
comparativa['indice_ipc_general_base100']   = (comparativa['ipc_general']   / ipc_b * 100).round(2)
comparativa['indice_ipc_alimentos_base100'] = (comparativa['ipc_alimentos'] / ialb  * 100).round(2)

# Reindexar desde MES_INICIO_GRAFICO — auto-adapta si el mes no está en la serie
_mg = MES_INICIO_GRAFICO
if _mg not in comparativa['mes'].values:
    _mg = comparativa['mes'].min()
    print(f'AVISO: MES_INICIO_GRAFICO {MES_INICIO_GRAFICO} no está en la serie → usando {_mg}')
df_g = comparativa[comparativa['mes'] >= _mg].copy().reset_index(drop=True)
bg   = df_g['canasta_nacional_ponderada'].iloc[0]
big  = df_g['ipc_general'].dropna().iloc[0] if df_g['ipc_general'].notna().any() else 1
bia  = df_g['ipc_alimentos'].dropna().iloc[0] if df_g['ipc_alimentos'].notna().any() else 1
_lbl_base = _mg[5:7] + '-' + _mg[2:4]   # ej. '03-24'
df_g['idx_canasta_base']       = (df_g['canasta_nacional_ponderada'] / bg  * 100).round(2)
df_g['idx_ipc_general_base']   = (df_g['ipc_general']                / big * 100).round(2)
df_g['idx_ipc_alimentos_base'] = (df_g['ipc_alimentos']              / bia * 100).round(2)
df_g['fecha'] = pd.to_datetime(df_g['mes'] + '-01')

print(f'Comparativa: {len(comparativa)} meses | Grafico desde: {_mg} ({len(df_g)} meses)')
cols = ['mes','canasta_nacional_ponderada','variacion_mensual_%','ipc_general_var_%']
print(comparativa[cols].tail(6).to_string(index=False))"""))

# CELL 12 — IPC CHARTS
cells.append(cell_code("""\
# ============================================================
# CELDA 12 — Graficos: indices y variaciones vs IPC
# ============================================================
COLOR_CANASTA = '#0055A4'
COLOR_IPC_GEN = '#D62728'
COLOR_IPC_ALI = '#FF7F0E'

# Formateador de meses en español para los ejes X
_MESES_ES = {1:'ene',2:'feb',3:'mar',4:'abr',5:'may',6:'jun',
             7:'jul',8:'ago',9:'sep',10:'oct',11:'nov',12:'dic'}
def _fmt_mes_es(x, pos):
    try:
        ts = mdates.num2date(x)
        return f'{_MESES_ES[ts.month]}-{str(ts.year)[2:]}'
    except Exception:
        return ''

# ── GRAFICO 1: Indices base = 100 ─────────────────────────────────────────────
fig1, ax1 = plt.subplots(figsize=(13, 6))
ax1.plot(df_g['fecha'], df_g['idx_canasta_base'],
         color=COLOR_CANASTA, linewidth=2.5,
         label=f'ICM-UADE ({N_CANASTA} productos)', marker='o', markersize=5)
ax1.plot(df_g['fecha'], df_g['idx_ipc_general_base'],
         color=COLOR_IPC_GEN, linewidth=2,
         label='IPC INDEC - Nivel general', linestyle='--', marker='s', markersize=4)
ax1.plot(df_g['fecha'], df_g['idx_ipc_alimentos_base'],
         color=COLOR_IPC_ALI, linewidth=2,
         label='IPC INDEC - Alimentos y bebidas', linestyle=':', marker='^', markersize=4)
ax1.set_ylabel(f'Índice ({_lbl_base} = 100)', fontsize=11)
ax1.legend(loc='upper left', fontsize=10, framealpha=0.95)
ax1.grid(True, alpha=0.3)
ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
ax1.xaxis.set_major_formatter(mticker.FuncFormatter(_fmt_mes_es))
plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
# Anotar valores finales
ult = df_g.iloc[-1]
ax1.annotate(f"{ult['idx_canasta_base']:.1f}",
             xy=(ult['fecha'], ult['idx_canasta_base']),
             xytext=(8,0), textcoords='offset points',
             color=COLOR_CANASTA, fontweight='bold', fontsize=11)
iu = df_g.dropna(subset=['idx_ipc_general_base']).iloc[-1]
ax1.annotate(f"{iu['idx_ipc_general_base']:.1f}",
             xy=(iu['fecha'], iu['idx_ipc_general_base']),
             xytext=(8,-3), textcoords='offset points',
             color=COLOR_IPC_GEN, fontweight='bold', fontsize=11)
if df_g['idx_ipc_alimentos_base'].notna().any():
    ia = df_g.dropna(subset=['idx_ipc_alimentos_base']).iloc[-1]
    ax1.annotate(f"{ia['idx_ipc_alimentos_base']:.1f}",
                 xy=(ia['fecha'], ia['idx_ipc_alimentos_base']),
                 xytext=(8,3), textcoords='offset points',
                 color=COLOR_IPC_ALI, fontweight='bold', fontsize=11)
plt.tight_layout()
out1 = OUTPUT_DIR / f'indices_canasta_vs_ipc_{MES}.png'
plt.savefig(out1, dpi=200, bbox_inches='tight', facecolor='white')
plt.show()
print(f'Grafico 1 guardado: {out1}')

# ── GRAFICO 2: Variaciones mensuales (3 barras: ICM-UADE, IPC General, IPC Alimentos) ──
fig2, ax2 = plt.subplots(figsize=(14, 6))
x      = df_g['fecha']
width  = pd.Timedelta(days=6)
offsets = [-width, pd.Timedelta(0), width]   # ICM-UADE izq, IPC Gen centro, IPC Ali der
bc  = ax2.bar(x + offsets[0], df_g['variacion_mensual_%'],  width=width,
              color=COLOR_CANASTA, alpha=0.90, label='ICM-UADE')
big = ax2.bar(x + offsets[1], df_g['ipc_general_var_%'],    width=width,
              color=COLOR_IPC_GEN, alpha=0.75, label='IPC INDEC - Nivel general')
bia = ax2.bar(x + offsets[2], df_g['ipc_alimentos_var_%'],  width=width,
              color=COLOR_IPC_ALI, alpha=0.75, label='IPC INDEC - Alimentos y bebidas')
for bars, vals, col in [
    (bc,  df_g['variacion_mensual_%'], COLOR_CANASTA),
    (big, df_g['ipc_general_var_%'],   COLOR_IPC_GEN),
    (bia, df_g['ipc_alimentos_var_%'], COLOR_IPC_ALI),
]:
    for bar, val in zip(bars, vals):
        if pd.notna(val) and val != 0:
            ypos = bar.get_height() + 0.1 if val >= 0 else bar.get_height() - 0.6
            ax2.text(bar.get_x()+bar.get_width()/2, ypos,
                     f'{val:.1f}', ha='center', va='bottom',
                     fontsize=6.5, color=col, fontweight='bold', rotation=90)
ax2.axhline(0, color='black', linewidth=0.5)
ax2.set_ylabel('Variación mensual (%)', fontsize=11)
ax2.legend(loc='upper right', fontsize=9, framealpha=0.95)
ax2.grid(True, alpha=0.3, axis='y')
ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
ax2.xaxis.set_major_formatter(mticker.FuncFormatter(_fmt_mes_es))
plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
_vals_max = [s.dropna().max() for s in [df_g['variacion_mensual_%'],
             df_g['ipc_general_var_%'], df_g['ipc_alimentos_var_%']] if s.notna().any()]
if _vals_max:
    ax2.set_ylim(top=max(_vals_max) * 1.35)
plt.tight_layout()
out2 = OUTPUT_DIR / f'variaciones_canasta_vs_ipc_{MES}.png'
plt.savefig(out2, dpi=200, bbox_inches='tight', facecolor='white')
plt.show()
print(f'Grafico 2 guardado: {out2}')"""))

# CELL 13 — TABLE + LATEX
cells.append(cell_code("""\
# ============================================================
# CELDA 13 — Cuadro 1: canasta por provincia + LaTeX
# ============================================================
def fmt_ar(x, dec=0):
    s = f'{x:,.{dec}f}'
    return s.replace(',','X').replace('.',',').replace('X','.')

df_prov = serie_provincia_valida.copy()
df_prov['vs_%'] = ((df_prov['canasta_total'] / prom_nac_ponderado) - 1) * 100
df_prov = df_prov.sort_values('canasta_total').reset_index(drop=True)

print('=== CUADRO 1: CANASTA POR PROVINCIA ===\\n')
print(f'{"Provincia":<25} {"Canasta":>14} {"Vs. promedio pais":>18}')
print('-'*60)
for _, r in df_prov.iterrows():
    c = fmt_ar(r['canasta_total'])
    v = f"{r['vs_%']:+.2f}%".replace('.',',')
    print(f"{r['provincia']:<25} {c:>14} {v:>18}")
print('-'*60)
print(f'{"Promedio nacional":<25} {fmt_ar(prom_nac_ponderado):>14} {"0,00%":>18}')

# LaTeX
nom_mes = {'01':'enero','02':'febrero','03':'marzo','04':'abril','05':'mayo','06':'junio',
           '07':'julio','08':'agosto','09':'septiembre','10':'octubre','11':'noviembre','12':'diciembre'}
mes_s = nom_mes[ULTIMO_MES[5:7]]
anio_s = ULTIMO_MES[:4]

ltx = [
    r'\\begin{table}[H]',
    r'\\centering',
    r'\\renewcommand{\\arraystretch}{1.15}',
    f'\\\\caption{{Valor de la canasta por provincia ({mes_s} {anio_s})}}',
    r'\\begin{tabular}{@{}l r r@{}}',
    r'\\toprule',
    r'\\textbf{Provincia} & \\textbf{Canasta} & \\shortstack{\\textbf{Vs. promedio}\\\\\\\\\\textbf{pais (\\%)}} \\\\\\\\',
    r'\\midrule',
]
for _, r in df_prov.iterrows():
    c = fmt_ar(r['canasta_total'])
    v = f"{r['vs_%']:+.2f}".replace('.',',')
    ltx.append(f"{r['provincia']:<22} & {c} & {v}\\\\% \\\\\\\\")
ltx += [
    r'\\midrule',
    f'\\\\textbf{{Promedio}} & {fmt_ar(prom_nac_ponderado)} & 0,00\\\\% \\\\\\\\',
    r'\\bottomrule',
    r'\\end{tabular}\\\\[0.2cm]',
    r'\\caption*{Fuente: Elaboracion propia en base a SEPA}',
    r'\\label{tab:canasta_provincias}',
    r'\\end{table}',
]
latex_out = '\\n'.join(ltx)

out_tex = OUTPUT_DIR / f'tabla_canasta_provincias_{ULTIMO_MES}.tex'
out_tex.write_text(latex_out, encoding='utf-8')
print(f'\\nLaTeX guardado: {out_tex}')
print('\\n=== LATEX ===')
print(latex_out)"""))

# CELL 14 — MAP
cells.append(cell_code("""\
# ============================================================
# CELDA 14 — Mapa coropletico por provincia
# ============================================================
if not GEOJSON_PATH.exists():
    print(f'GeoJSON no encontrado en {GEOJSON_PATH} — saltear celda')
else:
    with open(GEOJSON_PATH, 'r', encoding='utf-8') as f:
        geo = _json.load(f)

    NORM_GEO = {'Ciudad de Buenos Aires': 'CABA'}
    can_prov = dict(zip(df_prov['provincia'], df_prov['canasta_total']))
    vals = list(can_prov.values())
    norm_c = Normalize(vmin=min(vals), vmax=max(vals))
    cmap_m = LinearSegmentedColormap.from_list('c',
        ['#1a9850','#66bd63','#a6d96a','#d9ef8b','#fee08b','#fdae61','#f46d43','#d73027'], N=256)

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

    fig, ax = plt.subplots(figsize=(12, 16))
    caba_c = None

    for feat in geo['features']:
        ng  = feat['properties']['name']
        nom = NORM_GEO.get(ng, ng)
        val = can_prov.get(nom)
        col = cmap_m(norm_c(val)) if val is not None else '#dddddd'
        gt  = feat['geometry']['type']
        co  = feat['geometry']['coordinates']
        draw(ax, [co] if gt == 'Polygon' else co, col)
        cx, cy = centroide([co] if gt == 'Polygon' else co)

        if nom == 'CABA':
            caba_c = (cx, cy); continue

        dx, dy = AJUST.get(nom, (0,0))
        if val is not None:
            ax.text(cx+dx, cy+dy, f'{nom}\\n${val/1000:.0f}k',
                    ha='center', va='center', fontsize=7.5, fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.25', facecolor='white', alpha=0.75, edgecolor='none'))

    if caba_c and 'CABA' in can_prov:
        vc = can_prov['CABA']
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

    ax.set_aspect('equal'); ax.axis('off')
    ax.set_title(f'ICM-UADE por provincia — {NOMBRE_MES_TITLE}\\n({N_CANASTA} productos)',
                 fontsize=14, fontweight='bold', pad=12)
    plt.tight_layout()
    out_m = OUTPUT_DIR / f'mapa_canasta_{ULTIMO_MES}.png'
    plt.savefig(out_m, dpi=200, bbox_inches='tight', facecolor='white')
    plt.show()
    print(f'Mapa guardado: {out_m}')"""))

# CELL 15 — COVERAGE
cells.append(cell_code("""\
# ============================================================
# CELDA 15 — Graficos de cobertura
# ============================================================
cob_p = (canasta_geo_filtros.groupby('PROVINCIA_NORM')
         .agg(n_sucursales=('canasta_total','count'), n_cadenas=('cadena','nunique'))
         .reset_index().rename(columns={'PROVINCIA_NORM':'provincia'})
         .sort_values('n_sucursales'))

fig, axes = plt.subplots(1, 2, figsize=(14, max(8, len(cob_p)*0.35+2)), sharey=True)
for ax, (col, titulo, color) in zip(axes, [
        ('n_sucursales','Sucursales con datos','#0055A4'),
        ('n_cadenas','Cadenas presentes','#27ae60')]):
    ax.barh(cob_p['provincia'], cob_p[col], color=color, edgecolor='white')
    for i, v in enumerate(cob_p[col]):
        ax.text(v+max(cob_p[col])*0.01, i, f'{int(v):,}', va='center', fontsize=8)
    ax.set_title(titulo, fontsize=11, fontweight='bold', color=color)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f'{int(x):,}'))
    ax.set_xlim(0, max(cob_p[col])*1.18)
    for sp in ['top','right']: ax.spines[sp].set_visible(False)
fig.suptitle(f'Cobertura por provincia — {NOMBRE_MES_TITLE}', fontsize=13, fontweight='bold')
plt.tight_layout()
out_cp = OUTPUT_DIR / f'cobertura_provincia_{MES}.png'
plt.savefig(out_cp, dpi=150, bbox_inches='tight'); plt.show()

cob_c = (canasta_geo_filtros.groupby('cadena')
         .agg(n_sucursales=('canasta_total','count'), n_provincias=('PROVINCIA_NORM','nunique'))
         .reset_index().sort_values('n_sucursales'))

fig, axes = plt.subplots(1, 2, figsize=(14, max(6, len(cob_c)*0.45+2)), sharey=True)
for ax, (col, titulo, color) in zip(axes, [
        ('n_sucursales','Sucursales con datos','#0055A4'),
        ('n_provincias','Provincias presentes','#c0392b')]):
    ax.barh(cob_c['cadena'], cob_c[col], color=color, edgecolor='white')
    for i, v in enumerate(cob_c[col]):
        ax.text(v+max(cob_c[col])*0.01, i, f'{int(v):,}', va='center', fontsize=8)
    ax.set_title(titulo, fontsize=11, fontweight='bold', color=color)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f'{int(x):,}'))
    ax.set_xlim(0, max(cob_c[col])*1.18)
    for sp in ['top','right']: ax.spines[sp].set_visible(False)
axes[0].tick_params(axis='y', labelsize=8)
fig.suptitle(f'Cobertura por cadena — {NOMBRE_MES_TITLE}', fontsize=13, fontweight='bold')
plt.tight_layout()
out_cc = OUTPUT_DIR / f'cobertura_cadena_{MES}.png'
plt.savefig(out_cc, dpi=150, bbox_inches='tight'); plt.show()
print(f'Graficos cobertura guardados')"""))

# CELL 16 — RANKINGS
cells.append(cell_code("""\
# ============================================================
# CELDA 16 — Ranking de cadenas: nacional + AMBA
# ============================================================
def fmtn(x): return f'{x:,.0f}'.replace(',','.')

rk_nac = (canasta_geo_filtros.groupby('cadena')
           .agg(n_sucursales=('canasta_total','count'),
                canasta_promedio=('canasta_total','mean'))
           .round(0).reset_index())
rk_nac = rk_nac[rk_nac['n_sucursales'] >= MIN_SUCURSALES_RANKING].sort_values('canasta_promedio')
prom_nac_rk = canasta_geo_filtros['canasta_total'].mean()

amba = canasta_geo_filtros[canasta_geo_filtros['PROVINCIA_NORM'].isin(['Buenos Aires','CABA'])]
rk_amba = (amba.groupby('cadena')
            .agg(n_sucursales=('canasta_total','count'),
                 canasta_promedio=('canasta_total','mean'))
            .round(0).reset_index())
rk_amba = rk_amba[rk_amba['n_sucursales'] >= MIN_SUCURSALES_RANKING].sort_values('canasta_promedio')
prom_amba_rk = amba['canasta_total'].mean() if len(amba) > 0 else 0

for (rk, prom_r, titulo, out_name) in [
        (rk_nac, prom_nac_rk, f'Ranking nacional — {NOMBRE_MES_TITLE}', f'ranking_cadenas_nacional_{MES}'),
        (rk_amba, prom_amba_rk, f'Ranking AMBA — {NOMBRE_MES_TITLE}', f'ranking_cadenas_amba_{MES}'),
]:
    if len(rk) == 0: print(f'Sin datos suficientes para {titulo}'); continue
    fig, ax = plt.subplots(figsize=(11, max(5, len(rk)*0.5+2)))
    labs = [f"{r.cadena}  ({int(r.n_sucursales)})" for r in rk.itertuples()]
    n_c  = len(rk)
    cols_c = plt.cm.RdYlGn_r(np.linspace(0.1, 0.9, n_c)) if n_c > 1 else ['#0055A4']
    bars = ax.barh(labs, rk['canasta_promedio'], color=cols_c, edgecolor='black', linewidth=0.4)
    for bar, val in zip(bars, rk['canasta_promedio']):
        ax.text(bar.get_width() + rk['canasta_promedio'].max()*0.005,
                bar.get_y() + bar.get_height()/2,
                f'${fmtn(val)}', va='center', fontsize=9, fontweight='bold')
    ax.axvline(prom_r, color='#666', linestyle='--', linewidth=1.5,
               label=f'Promedio: ${fmtn(prom_r)}')
    ax.set_xlabel('Canasta promedio (ARS)', fontsize=11)
    ax.set_xlim(rk['canasta_promedio'].min()*0.95, rk['canasta_promedio'].max()*1.07)
    ax.set_title(titulo, fontsize=13, fontweight='bold')
    ax.legend(loc='lower right', fontsize=10)
    ax.grid(True, alpha=0.3, axis='x'); ax.set_axisbelow(True)
    for sp in ['top','right']: ax.spines[sp].set_visible(False)
    plt.tight_layout()
    out_r = OUTPUT_DIR / f'{out_name}.png'
    plt.savefig(out_r, dpi=150, bbox_inches='tight'); plt.show()
    print(f'Ranking guardado: {out_r}')

print('\\n=== RANKING NACIONAL ===')
for i, r in enumerate(rk_nac.sort_values('canasta_promedio',ascending=False).itertuples(),1):
    print(f'  {i:>2}. {r.cadena:<25} ${fmtn(r.canasta_promedio):>12}  ({int(r.n_sucursales)} sucs)')"""))

# CELL 17 — FOLIUM
cells.append(cell_code("""\
# ============================================================
# CELDA 17 — Mapa interactivo Folium por sucursal
# ============================================================
cgf = canasta_geo_filtros.copy()
vmin_m = cgf['canasta_total'].quantile(0.05)
vmax_m = cgf['canasta_total'].quantile(0.95)

m = folium.Map(location=[-38.0,-63.5], zoom_start=5,
               tiles='cartodbpositron', control_scale=True)

folium.map.Marker(
    location=[-51.7963,-59.5236],
    icon=folium.DivIcon(icon_size=(140,28), icon_anchor=(70,14),
        html='<div style="background:rgba(255,255,255,.95);border:1px solid #777;border-radius:3px;padding:3px 7px;font-family:Arial;font-size:11px;font-weight:600;text-align:center;white-space:nowrap;">Islas Malvinas (ARG)</div>')
).add_to(m)

cm_m = LinearColormap(
    colors=['#1a9850','#66bd63','#a6d96a','#fee08b','#fdae61','#f46d43','#d73027'],
    vmin=vmin_m, vmax=vmax_m, caption=f'Canasta {NOMBRE_MES_TITLE} (ARS)')
cm_m.add_to(m)

def fmtm(x): return f'{x:,.0f}'.replace(',','.')

def det_html(det):
    cats = {}
    for nom,cat,qty,pre,sub,esp in det: cats.setdefault(cat,[]).append((nom,qty,pre,sub,esp))
    rows = []
    for cat, items in cats.items():
        rows.append(f'<tr style="background:#0055A4;color:white;"><td colspan="4" style="padding:3px 5px;font-weight:bold;">{cat}</td></tr>')
        for nom,qty,pre,sub,esp in items:
            st = '' if esp else 'color:#888;font-style:italic;'
            mk = '' if esp else ' *'
            rows.append(f'<tr style="{st}"><td style="padding:2px 5px;">{nom}{mk}</td><td style="padding:2px 5px;text-align:center;">x{qty}</td><td style="padding:2px 5px;text-align:right;">${fmtm(pre)}</td><td style="padding:2px 5px;text-align:right;font-weight:600;">${fmtm(sub)}</td></tr>')
    return ('<table style="width:100%;border-collapse:collapse;font-size:10px;font-family:Arial;">'
            '<thead><tr style="background:#e6eef7;font-weight:bold;">'
            '<th style="padding:3px 5px;text-align:left;">Producto</th>'
            '<th style="padding:3px 5px;">Cant.</th>'
            '<th style="padding:3px 5px;text-align:right;">P.Unit</th>'
            '<th style="padding:3px 5px;text-align:right;">Subtotal</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table>'
            '<div style="font-size:9px;color:#666;margin-top:4px;">* Precio imputado promedio nacional.</div>')

cads_u = sorted(cgf['cadena'].unique())
provs_u = sorted(cgf['PROVINCIA_NORM'].unique())
tipos_u = sorted([t for t in cgf['sucursales_tipo'].dropna().unique() if t and t != 'Web'])

fgs = {c: folium.FeatureGroup(name=f'🏪 {c} ({(cgf["cadena"]==c).sum()})', show=True) for c in cads_u}

for _, row in cgf.iterrows():
    val = row['canasta_total']
    col = cm_m(max(vmin_m, min(vmax_m, val)))
    cad = row['cadena']
    tip = str(row.get('sucursales_tipo') or 'N/D')
    prv = row['PROVINCIA_NORM']
    tooltip_t = f"<b>{cad}</b><br>{prv}<br><b>${fmtm(val)}</b> · {tip}"
    dh = det_html(row['detalle_productos'])
    popup_h = (f'<div style="font-family:Arial;font-size:12px;width:420px;max-height:500px;overflow-y:auto;">'
               f'<h4 style="margin:0;color:#0055A4;">{cad}</h4>'
               f'<div style="font-size:11px;color:#555;margin-bottom:5px;"><b>{row["sucursales_nombre"]}</b><br>'
               f'{row.get("sucursales_barrio") or row.get("sucursales_localidad") or "N/D"} — {prv}<br>'
               f'<span style="background:#e6eef7;padding:2px 6px;border-radius:3px;font-size:10px;">{tip}</span></div>'
               f'<hr style="margin:5px 0;">'
               f'<div style="text-align:center;margin:8px 0;">'
               f'<span style="font-size:11px;color:#666;">Canasta total</span><br>'
               f'<span style="color:#0055A4;font-size:20px;font-weight:bold;">${fmtm(val)}</span><br>'
               f'<span style="font-size:10px;color:#888;">({row["productos_propios"]}/{N_CANASTA} productos propios)</span></div>'
               f'<hr style="margin:5px 0;">{dh}</div>')
    cl = f'sucursal-marker cadena-{cad.replace(" ","_").replace("(","").replace(")","").replace("/","")} prov-{prv.replace(" ","_").replace("(","").replace(")","")}'
    folium.CircleMarker(
        location=[row['sucursales_latitud'], row['sucursales_longitud']],
        radius=5, color=col, fill=True, fillColor=col, fillOpacity=0.8, weight=1,
        tooltip=tooltip_t, popup=folium.Popup(popup_h, max_width=450), className=cl
    ).add_to(fgs[cad])

for fg in fgs.values(): fg.add_to(m)
folium.LayerControl(position='topright', collapsed=False).add_to(m)
m.get_root().html.add_child(folium.Element(
    '<script>setTimeout(function(){document.querySelectorAll(".leaflet-control-layers-base,.leaflet-control-layers-separator").forEach(e=>e.style.display="none");},500);</script>'))

prov_opts = ''.join([f'<option value="prov-{p.replace(" ","_")}">{p}</option>' for p in provs_u])
tipo_opts = ''.join([f'<option value="tipo-{t.replace(" ","_")}">{t}</option>' for t in tipos_u])
info_h = (f'<div style="position:fixed;top:10px;left:50px;width:340px;background:white;border:2px solid #0055A4;'
          f'border-radius:8px;padding:12px 15px;font-family:Arial;z-index:9999;box-shadow:0 2px 8px rgba(0,0,0,.15);">'
          f'<div style="color:#0055A4;font-size:15px;font-weight:bold;margin-bottom:5px;">'
          f'Canasta SEPA por sucursal — {NOMBRE_MES_TITLE}</div>'
          f'<div style="font-size:11px;color:#555;line-height:1.5;">'
          f'<b>{len(cgf):,}</b> sucursales · <b>{len(cads_u)}</b> cadenas · <b>{len(provs_u)}</b> provincias<br>'
          f'Promedio nacional: <b>${fmtm(cgf["canasta_total"].mean())}</b></div>'
          f'<div style="font-size:10px;color:#888;margin-top:6px;padding-top:6px;border-top:1px solid #eee;">'
          f'🏪 Cadenas: panel der. · 📍 Prov/Tipo: panel inf. izq. · Click para detalle</div></div>')
m.get_root().html.add_child(folium.Element(info_h))

filtros_h = (
    f'<div id="pf" style="position:fixed;bottom:25px;left:50px;width:270px;background:white;'
    f'border:2px solid #0055A4;border-radius:8px;padding:12px 15px;font-family:Arial;z-index:9999;'
    f'box-shadow:0 2px 8px rgba(0,0,0,.15);">'
    f'<div style="color:#0055A4;font-size:13px;font-weight:bold;margin-bottom:8px;">🔍 Filtros</div>'
    f'<label style="font-size:11px;color:#555;display:block;margin-top:6px;">Provincia:'
    f'<select id="fp" style="width:100%;padding:4px;font-size:11px;margin-top:3px;">'
    f'<option value="all">Todas</option>{prov_opts}</select></label>'
    f'<label style="font-size:11px;color:#555;display:block;margin-top:6px;">Tipo:'
    f'<select id="ft" style="width:100%;padding:4px;font-size:11px;margin-top:3px;">'
    f'<option value="all">Todos</option>{tipo_opts}</select></label>'
    f'<button id="fr" style="width:100%;margin-top:10px;padding:6px;background:#f0f0f0;color:#555;'
    f'border:1px solid #ccc;border-radius:4px;font-size:11px;cursor:pointer;">Restablecer</button>'
    f'<div id="fr2" style="font-size:10px;color:#888;margin-top:8px;padding-top:6px;'
    f'border-top:1px solid #eee;text-align:center;">Mostrando todas</div></div>'
    '<script>function apl(){var p=document.getElementById("fp").value,t=document.getElementById("ft").value,v=0,tot=0;'
    'document.querySelectorAll(".sucursal-marker").forEach(function(el){'
    'tot++;var c=el.className.baseVal||el.className||"",'
    'mp=(p==="all")||c.indexOf(p)>=0,mt=(t==="all")||c.indexOf(t)>=0;'
    'if(mp&&mt){el.style.display="";v++;}else{el.style.display="none";}});'
    'var d=document.getElementById("fr2");if(d)d.innerHTML=v===tot?"Mostrando todas ("+tot+")":"Mostrando "+v+" de "+tot;}'
    'function rst(){document.getElementById("fp").value="all";document.getElementById("ft").value="all";'
    'document.querySelectorAll(".sucursal-marker").forEach(e=>e.style.display="");'
    'var d=document.getElementById("fr2");if(d)d.innerHTML="Mostrando todas";}'
    'setTimeout(function(){var sp=document.getElementById("fp"),st=document.getElementById("ft"),btn=document.getElementById("fr");'
    'if(sp)sp.addEventListener("change",apl);if(st)st.addEventListener("change",apl);if(btn)btn.addEventListener("click",rst);},1000);</script>'
)
m.get_root().html.add_child(folium.Element(filtros_h))

out_map = OUTPUT_DIR / f'mapa_interactivo_{MES}.html'
m.save(str(out_map))
print(f'Mapa guardado: {out_map}  ({len(cgf):,} sucursales)')
m"""))

# CELL 18 — CABA
cells.append(cell_code("""\
# ============================================================
# CELDA 18 — Ranking de barrios de CABA
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

caba = canasta_geo_filtros[canasta_geo_filtros['PROVINCIA_NORM'] == 'CABA'].copy()
print(f'Sucursales CABA: {len(caba)}')

def det_barrio(lat, lon):
    if pd.isna(lat) or pd.isna(lon): return 'Sin clasificar'
    for b,(lmin,lmax,lonmin,lonmax) in BARRIOS_BBOX.items():
        if lmin <= lat <= lmax and lonmin <= lon <= lonmax:
            return b
    return 'Sin clasificar'

caba['barrio'] = caba.apply(lambda r: det_barrio(r['sucursales_latitud'],r['sucursales_longitud']), axis=1)
print(f'  Asignados: {(caba["barrio"] != "Sin clasificar").sum()} | Sin clasificar: {(caba["barrio"] == "Sin clasificar").sum()}')

rk_b = (caba[caba['barrio'] != 'Sin clasificar']
        .groupby('barrio')
        .agg(n_sucs=('canasta_total','count'),
             promedio=('canasta_total','mean'),
             mediana=('canasta_total','median'),
             minimo=('canasta_total','min'),
             maximo=('canasta_total','max'))
        .round(0).sort_values('promedio'))
rk_b_fil = rk_b[rk_b['n_sucs'] >= 2]

pc = caba['canasta_total'].mean()
pp = canasta_geo_filtros['canasta_total'].mean()

def fmtb(x): return f'${x:,.0f}'.replace(',','.')

print(f'\\n{"="*78}')
print(f'  RANKING DE BARRIOS CABA — {NOMBRE_MES_TITLE.upper()}')
print(f'{"="*78}')
print(f'\\n  {"#":<3} {"Barrio":<22} {"Sucs.":<7} {"Promedio":<13} {"vs CABA":<10} {"vs Pais"}')
print(f'  {"-"*70}')
for i, (b, r) in enumerate(rk_b_fil.iterrows(), 1):
    vc = (r["promedio"]/pc-1)*100
    vp = (r["promedio"]/pp-1)*100
    print(f'  {i:<3} {b:<22} {int(r["n_sucs"]):<7} {fmtb(r["promedio"]):<13} {vc:+.2f}%  {vp:+.2f}%')
print(f'  {"-"*70}')
print(f'  Promedio CABA: {fmtb(pc)}   Promedio pais: {fmtb(pp)}')

barrios_sin = set(BARRIOS_BBOX.keys()) - set(rk_b.index)
if barrios_sin:
    print(f'\\n  Sin sucursales relevadas ({len(barrios_sin)}): {", ".join(sorted(barrios_sin))}')"""))

# CELL 19 — EXPORT
cells.append(cell_code("""\
# ============================================================
# CELDA 19 — Exportacion Excel consolidado
# ============================================================
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

HDR_FILL = PatternFill(start_color='1F4E79', end_color='1F4E79', fill_type='solid')
HDR_FONT = Font(bold=True, color='FFFFFF', size=10)
HDR_ALIG = Alignment(horizontal='center', wrap_text=True, vertical='center')

def fmt_ws(ws):
    ws.row_dimensions[1].height = 30
    ws.freeze_panes = 'A2'
    for cell in ws[1]:
        cell.fill = HDR_FILL; cell.font = HDR_FONT; cell.alignment = HDR_ALIG

comp_exp = comparativa[['mes','canasta_nacional_ponderada','variacion_mensual_%',
                         'ipc_general','ipc_general_var_%','ipc_alimentos',
                         'ipc_alimentos_var_%','indice_canasta_base100']].copy()

# ── Hoja Serie_precios: precio mediano por producto por mes (de df_hist) ─────
_sp = df_hist[['ean_norm','anio_mes','precio_mediano','qty','costo_item']].copy()
_sp['id_producto'] = _sp['ean_norm'].apply(lambda e: e.zfill(13))
_sp['descripcion'] = _sp['ean_norm'].map(lambda e: CANASTA.get(e,('',0,''))[0])
_sp['categoria']   = _sp['ean_norm'].map(lambda e: CANASTA.get(e,('',0,'?'))[2])
serie_precios_exp = (
    _sp[['anio_mes','id_producto','descripcion','categoria','qty','precio_mediano','costo_item']]
    .rename(columns={'anio_mes':'mes'})
    .sort_values(['id_producto','mes'])
    .reset_index(drop=True)
)
del _sp

prov_exp = serie_provincia_valida.copy()
prov_exp['vs_promedio_%'] = ((prov_exp['canasta_total'] / prom_nac_ponderado) - 1) * 100
prov_exp = prov_exp.sort_values('canasta_total').reset_index(drop=True)

suc_exp = canasta_geo_filtros[[
    'id_comercio','id_bandera','id_sucursal','cadena','PROVINCIA_NORM',
    'sucursales_nombre','sucursales_localidad','sucursales_barrio',
    'sucursales_latitud','sucursales_longitud','sucursales_tipo',
    'canasta_total','productos_propios'
]].sort_values(['PROVINCIA_NORM','cadena','canasta_total']).copy()

rk_exp = rk_nac.sort_values('canasta_promedio', ascending=False).copy()
rk_exp['vs_promedio_%'] = ((rk_exp['canasta_promedio'] / prom_nac_rk) - 1) * 100

out_xls = OUTPUT_DIR / f'canasta_analisis_{ULTIMO_MES}.xlsx'
with pd.ExcelWriter(out_xls, engine='openpyxl') as writer:
    comp_exp.to_excel        (writer, sheet_name='Evolucion_IPC',   index=False)
    prov_exp.to_excel        (writer, sheet_name='Por_provincia',   index=False)
    suc_exp.to_excel         (writer, sheet_name='Por_sucursal',    index=False)
    rk_exp.to_excel          (writer, sheet_name='Ranking_cadenas', index=False)
    serie_precios_exp.to_excel(writer, sheet_name='Serie_precios',  index=False)
    for sn in ['Evolucion_IPC','Por_provincia','Por_sucursal','Ranking_cadenas','Serie_precios']:
        ws = writer.sheets[sn]
        fmt_ws(ws)
        for ci in range(1, ws.max_column+1):
            cl = get_column_letter(ci)
            hdr = str(ws.cell(1,ci).value or '').lower()
            w = 28 if any(x in hdr for x in ('nombre','provincia','cadena')) else (42 if 'desc' in hdr else 14)
            ws.column_dimensions[cl].width = w
            if any(x in hdr for x in ('canasta','precio','ipc','costo')):
                for row in ws.iter_rows(min_row=2,max_row=ws.max_row,min_col=ci,max_col=ci):
                    for cell in row: cell.number_format = '#,##0.00'
            elif '%' in hdr:
                for row in ws.iter_rows(min_row=2,max_row=ws.max_row,min_col=ci,max_col=ci):
                    for cell in row: cell.number_format = '+0.00"%"'

print(f'Excel guardado: {out_xls}')
print()
print('='*65)
print(f'  RESUMEN — CANASTA {NOMBRE_MES_TITLE.upper()}')
print('='*65)
print(f'  Productos:            {N_CANASTA}')
print(f'  Sucursales validas:   {len(canasta_geo_filtros):,}')
print(f'  Cadenas:              {canasta_geo_filtros["cadena"].nunique()}')
print(f'  Provincias:           {canasta_geo_filtros["PROVINCIA_NORM"].nunique()}')
print(f'  Promedio nacional:    ${prom_nac_ponderado:,.0f}')
print(f'  Serie historica:      {serie_nacional_valida["mes"].min()} -> {serie_nacional_valida["mes"].max()}')
print('='*65)"""))

# CELL 20 — DIAGNOSTIC: temporal traceability of Candidatos
cells.append(cell_code("""\
# ============================================================
# CELDA 20 — DIAGNÓSTICO: Trazabilidad temporal de Candidatos
# ============================================================
# Escanea los ZIPs históricos leyendo SOLO la columna id_producto
# (sin precios — mucho más rápido) para determinar en cuántos
# meses aparece cada producto de la hoja Candidatos.
# Útil para elegir productos estables para la canasta.
#
# Tiempo estimado: ~15-20 min (vs ~60 min de la serie histórica
# completa, porque no lee las columnas de precio).
# ============================================================

# ── 1. Leer hoja Candidatos ──────────────────────────────────
try:
    df_cand = pd.read_excel(CANASTA_EXCEL, sheet_name='Candidatos',
                            dtype={'id_producto': str})
    df_cand['ean_norm'] = df_cand['id_producto'].str.lstrip('0')
    CAND_EANS = set(df_cand['ean_norm'])
    print(f'Candidatos cargados: {len(CAND_EANS):,} EANs unicos')
except Exception as _e:
    raise RuntimeError(f'No se pudo leer hoja Candidatos: {_e}')

# ── 2. Escanear ZIPs (solo id_producto) ─────────────────────
_presencia   = {}   # ean_norm → set de meses donde aparece
_meses_vis   = []

for _zip_path, _anio, _sem in detectar_semestres():
    _meses = archivos_por_mes(_zip_path)
    for (_anio_m, _mes_m), _archs in sorted(_meses.items()):
        _lbl = f'{_anio_m}-{_mes_m:02d}'
        if _lbl < MES_INICIO_HISTORICO:
            continue
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
print(f'\\nTotal meses escaneados: {_n_meses} ({_mes_min} -> {_mes_max})')

# ── 3. Construir tabla de trazabilidad ───────────────────────
_rows = []
for _ean, _mp in _presencia.items():
    _rows.append({
        'ean_norm'         : _ean,
        'meses_presentes'  : len(_mp),
        'pct_trazabilidad' : len(_mp) / _n_meses * 100,
        'primer_mes'       : min(_mp),
        'ultimo_mes'       : max(_mp),
        'en_canasta'       : _ean in CANASTA,
    })
# EANs con 0 presencia
for _ean in CAND_EANS - set(_presencia.keys()):
    _rows.append({'ean_norm':_ean,'meses_presentes':0,'pct_trazabilidad':0.0,
                  'primer_mes':None,'ultimo_mes':None,'en_canasta':_ean in CANASTA})

df_traz = pd.DataFrame(_rows)

# Merge con metadata de candidatos
_mc = ['ean_norm'] + [c for c in
       ['descripcion','marca','categoria','subcategoria','precio_mediano','score_cobertura']
       if c in df_cand.columns]
df_traz = (df_traz
           .merge(df_cand[_mc], on='ean_norm', how='left')
           .sort_values('pct_trazabilidad', ascending=False)
           .reset_index(drop=True))

# ── 4. Resumen estadístico ───────────────────────────────────
print(f'\\n{"="*60}')
print(f'  TRAZABILIDAD TEMPORAL — {_mes_min} a {_mes_max} ({_n_meses} meses)')
print(f'{"="*60}')
print(f'  Candidatos con trazabilidad 100%  : {(df_traz["pct_trazabilidad"]==100).sum():>5,}')
print(f'  Candidatos con trazabilidad  >90% : {(df_traz["pct_trazabilidad"]> 90).sum():>5,}')
print(f'  Candidatos con trazabilidad  >75% : {(df_traz["pct_trazabilidad"]> 75).sum():>5,}')
print(f'  Candidatos con trazabilidad  <50% : {(df_traz["pct_trazabilidad"]< 50).sum():>5,}')
print(f'  Candidatos sin presencia historica: {(df_traz["pct_trazabilidad"]==  0).sum():>5,}')
_can_traz = df_traz[df_traz['en_canasta']]['pct_trazabilidad']
print(f'\\n  Tu canasta actual ({len(_can_traz)} productos):')
print(f'    Trazabilidad promedio : {_can_traz.mean():.1f}%')
print(f'    Trazabilidad minima   : {_can_traz.min():.1f}%')
print(f'{"="*60}')

# ── 5. Tabla top 30 ──────────────────────────────────────────
_cols_show = [c for c in
    ['descripcion','marca','categoria','meses_presentes','pct_trazabilidad','primer_mes','en_canasta']
    if c in df_traz.columns]
display(df_traz[_cols_show].head(30).style
    .background_gradient(subset=['pct_trazabilidad'], cmap='RdYlGn', vmin=0, vmax=100)
    .format({'pct_trazabilidad': '{:.1f}%'})
    .set_caption(f'Top 30 candidatos por trazabilidad temporal ({_mes_min} → {_mes_max})')
)

# ── 6. Gráficos ──────────────────────────────────────────────
_fig, _axes = plt.subplots(1, 2, figsize=(14, 5))

# Histograma de distribución
_axes[0].hist(df_traz['pct_trazabilidad'], bins=20,
              color='#0055A4', edgecolor='white', alpha=0.85)
_axes[0].axvline(_can_traz.mean(), color='#D62728', linewidth=2,
                 linestyle='--', label=f'Promedio canasta actual ({_can_traz.mean():.0f}%)')
_axes[0].set_xlabel('Trazabilidad temporal (%)')
_axes[0].set_ylabel('Número de productos')
_axes[0].set_title('Distribución de trazabilidad\\n(todos los candidatos)')
_axes[0].legend(fontsize=9)

# Trazabilidad promedio por categoría
if 'categoria' in df_traz.columns:
    _top_cat = (df_traz.groupby('categoria')['pct_trazabilidad']
                .agg(_mean='mean', _n='count')
                .query('_n >= 5')
                .sort_values('_mean', ascending=True)
                .tail(15))
    _axes[1].barh(_top_cat.index, _top_cat['_mean'], color='#0055A4', alpha=0.85)
    _axes[1].axvline(90, color='gray', linestyle='--', linewidth=1, alpha=0.6)
    _axes[1].set_xlabel('Trazabilidad promedio (%)')
    _axes[1].set_title('Trazabilidad por categoría\\n(categorías con ≥5 candidatos)')
    _axes[1].set_xlim(0, 105)
    for _i, (_idx, _row) in enumerate(_top_cat.iterrows()):
        _axes[1].text(_row['_mean']+0.5, _i, f'{_row["_mean"]:.0f}%', va='center', fontsize=8)

plt.tight_layout()
_fig.savefig(OUTPUT_DIR / f'trazabilidad_candidatos_{ULTIMO_MES}.png',
             dpi=150, bbox_inches='tight')
plt.show()

# ── 7. Exportar tabla completa ───────────────────────────────
_out_traz = OUTPUT_DIR / f'trazabilidad_candidatos_{ULTIMO_MES}.xlsx'
df_traz.to_excel(_out_traz, index=False)
print(f'Tabla completa guardada: {_out_traz.name}')
print('Tip: filtra por pct_trazabilidad > 90 y en_canasta = False para ver '
      'candidatos estables que aun no estan en tu canasta.')
"""))

# Write notebook
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
