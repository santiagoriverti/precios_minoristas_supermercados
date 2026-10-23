"""Script to generate 06_evolucion_brecha_celiaca.ipynb — Brecha TACC vs sin-TACC con canasta FIJA 2022-2026.

Mide la brecha de precios entre productos con TACC y sus equivalentes sin TACC (dentro de cada supermercado, por tipo
de producto, en $/100 g) y cómo se distribuye en el tiempo (mensual desde enero de 2022), geográficamente (provincia,
región, AMBA) y entre cadenas.

Canasta FIJA (2026-10-23): para cada tipo con dicotomía celíaca, productos con TACC y sin TACC elegidos por
continuidad temporal 2022-2026, cobertura geográfica y por cadenas sobre las salidas del nb09. La lista vive en
docs/brecha_celiaca/canasta_fija_2022_2026.csv (con las métricas de cada producto) y este generador la embebe en la
CELDA 1. Reglas y fundamentos: docs/BRECHA_CELIACA.md §14.

Regenerar:  python notebooks/gen_nb06.py   (commitear generador + .ipynb + CSV juntos)
"""
import csv, json, os, hashlib

def _cell_id(prefix, src):
    return prefix + hashlib.md5(src.encode('utf-8')).hexdigest()[:6]

def cell_md(src):
    lines = src.split('\n')
    source = [l + '\n' for l in lines[:-1]] + ([lines[-1]] if lines[-1] else [])
    return {'cell_type':'markdown','id':_cell_id('md', src),'metadata':{},'source':source}

def cell_code(src):
    return {'cell_type':'code','execution_count':None,'id':_cell_id('c', src),'metadata':{},'outputs':[],'source':[src]}

HERE = os.path.dirname(os.path.abspath(__file__))
CANASTA_CSV = os.path.join(HERE, '..', 'docs', 'brecha_celiaca', 'canasta_fija_2022_2026.csv')

# Peso de cada tipo = % del gasto de los hogares en alimentos y bebidas no alcohólicas (división A01) que va a sus
# artículos en la ENGHo 2017/18 (INDEC, microdatos de gastos, monto x pondera; hogar promedio, no celíaco). Se
# renormaliza entre los tipos de la canasta.
PESOS_ENGHO = {
    'Fideos secos': (1.503, 'A0111304 Fideos secos'),
    'Galletitas dulces': (1.717, 'A0111105 Galletitas dulces envasadas + A0111108 Masas secas o finas'),
    'Galletitas saladas y crackers': (1.407, 'A0111103 Galletitas de agua envasadas + A0111102 Galletas, grisines '
                                             'y tostadas + A0111107 Galletitas de otro tipo'),
    'Pan rallado y rebozador': (0.194, 'A0111114 Pan rallado'),
    'Cereales rellenos (almohaditas)': (0.181, 'A0111207 Cereales inflados'),
}
ORDEN_TIPOS = list(PESOS_ENGHO)


def _bloque_canasta():
    # TIPOS y GRAMOS de la CELDA 1, desde el CSV de la canasta fija
    with open(CANASTA_CSV, encoding='utf-8') as f:
        filas = list(csv.DictReader(f))
    tipos = {r['tipo'] for r in filas}
    falta = tipos - set(ORDEN_TIPOS)
    if falta:
        raise ValueError(f'Tipos del CSV sin peso ENGHo: {falta}')
    out = ['TIPOS = {']
    for tipo in ORDEN_TIPOS:
        fs = [r for r in filas if r['tipo'] == tipo]
        if not fs:
            continue
        peso, art = PESOS_ENGHO[tipo]
        out.append(f'    {tipo!r}: {{')
        out.append(f"        'peso': {peso},   # % del gasto en alimentos (ENGHo 2017/18): {art}")
        for lado in ('tacc', 'sin_tacc'):
            out.append(f'        {lado!r}: {{')
            for r in fs:
                if r['lado'] != lado:
                    continue
                nota = f"  # {r['subtipo']}" + (f" · {r['nota']}" if r.get('nota') else '')
                out.append(f"            {r['ean']!r}: {r['descripcion']!r},{nota}")
            out.append('        },')
        out.append('    },')
    out.append('}')
    out.append('')
    out.append('# Gramos de cada presentación, verificados contra el SEPA (descripciones de las cadenas en oct-2026) y el')
    out.append('# Maestro. NO se toman del maestro: hay EANs reutilizados con la descripción vieja.')
    out.append('GRAMOS = {')
    gs = [(r['ean'], r['gramos']) for t in ORDEN_TIPOS for r in filas if r['tipo'] == t]
    for i in range(0, len(gs), 5):
        out.append('    ' + ' '.join(f"{e!r}: {float(g):g}," for e, g in gs[i:i + 5]))
    out.append('}')
    out.append('')
    out.append('# Vigencia de los códigos de un producto que cambió de EAN (desde, hasta; None = sin límite). Los códigos viejos')
    out.append('# de Molinos que siguen apareciendo después del cambio (sep-oct 2023) traen precios CONGELADOS en ~100 sucursales')
    out.append('# (Mostacholes Lucchetti viejo a $246-337 en 2024-2025 contra $1.042-1.700 del nuevo): fuera de su vigencia no')
    out.append('# se usan (se filtran en la CELDA 7, NO cambian el caché).')
    out.append('VIGENCIA = {')
    for t in ORDEN_TIPOS:
        for r in filas:
            if r['tipo'] == t and (r.get('desde') or r.get('hasta')):
                d = repr(r['desde']) if r.get('desde') else 'None'
                h = repr(r['hasta']) if r.get('hasta') else 'None'
                out.append(f"    {r['ean']!r}: ({d}, {h}),   # {r['descripcion']}")
    out.append('}')
    out.append('')
    out.append('# Productos con más de un código (empalmes): en cada sucursal y mes el precio del producto es la mediana de sus')
    out.append('# códigos vigentes, así cuenta UNA vez en la mediana de su lado aunque la sucursal tenga los dos códigos.')
    out.append('PRODUCTO = {')
    _prod = {}
    for t in ORDEN_TIPOS:
        for r in filas:
            if r['tipo'] == t and r.get('producto'):
                _prod.setdefault(r['producto'], []).append(r['ean'])
    for p, es in _prod.items():
        if len(es) > 1:
            out.append(f'    {p!r}: {es!r},')
    out.append('}')
    out.append('')
    out.append('# Subtipo de cada producto (comparabilidad: en cada subtipo hay tantos productos con TACC como sin TACC). Se usa')
    out.append('# en la hoja Comparacion_productos y en el mapa por sucursal; la brecha se calcula por tipo.')
    out.append('SUBTIPO = {')
    _sub = {}
    for t in ORDEN_TIPOS:
        for r in filas:
            if r['tipo'] == t and r.get('subtipo'):
                _sub.setdefault(r['subtipo'], []).append(r['ean'])
    for s, es in _sub.items():
        out.append(f'    {s!r}: [')
        for i in range(0, len(es), 6):
            out.append('        ' + ' '.join(f'{e!r},' for e in es[i:i + 6]))
        out.append('    ],')
    out.append('}')
    return '\n'.join(out)


cells = []

# ── CELL 0 ─────────────────────────────────────────────────────────────────────
cells.append(cell_md("""# SEPA — Brecha Celíaca (TACC vs sin-TACC), canasta fija 2022-2026

**Objetivo:** medir la **brecha** de precios entre productos **con TACC** y sus equivalentes **sin TACC**, y cómo se
distribuye **en el tiempo** (mensual, desde enero de 2022), **geográficamente** (provincia, región, AMBA) y **entre
cadenas**.

**Canasta fija:** para cada tipo con dicotomía celíaca (fideos secos, galletitas dulces, galletitas saladas y crackers,
rebozador, cereales rellenos) una lista FIJA de productos con TACC y sin TACC elegidos por **continuidad temporal**
(precio todos los meses desde enero de 2022), **cobertura geográfica** (provincias y regiones) y **cobertura por
cadenas**, sobre las salidas del nb09. Reglas, listas y métricas: `docs/BRECHA_CELIACA.md` §14 y
`docs/brecha_celiaca/canasta_fija_2022_2026.csv`.

**Medición:**
- Precio de cada producto en cada sucursal y mes = **mediana de sus precios diarios**, en **$/100 g**.
- En cada sucursal y mes, por **subtipo** (spaghetti, crackers, rellenas…): precio de cada lado = **mediana** de los
  productos presentes; **brecha del subtipo = sin TACC / con TACC − 1**, dentro del mismo super (controla el nivel de
  precios de cada lugar y compara productos equivalentes).
- Como un índice de precios: **subtipo** (mediana entre sucursales) → **tipo** (promedio geométrico de sus subtipos)
  → **canasta** (promedio de los tipos ponderado por el **gasto de los hogares, ENGHo 2017/18**). Serie mensual con
  todas las sucursales y con **panel balanceado**; un subtipo-mes con muy pocas sucursales se imputa con el mes anterior
  (hoja `Imputaciones`).
- Provincias, regiones, empresas, cadenas y sucursales (mapa) se comparan con la **misma canasta de subtipos**: lo que
  un grupo no tiene se completa con la brecha nacional del período y se informa qué parte del peso es imputada.
- **Concentración**: HHI de empresas por **departamento** (Georef de datos.gob.ar; la caché del nb09).
- **Serie TPD (hedónica)**, robustez de la serie mensual frente a la imputación de subtipos (CELDA 8b): por subtipo, log
  del precio = efecto de la sucursal-mes + efecto de cada producto + prima sin TACC del mes. Compara cada producto
  consigo mismo, usa los meses con pocas sucursales que la descriptiva imputa y da intervalos de confianza.

**Config en la CELDA 1.** Estructura: Config → Setup → Maestros → Canasta → ZIPs → Lectura (caché por mes) → Brecha por
sucursal × mes × tipo → Agregaciones → Serie TPD → Gráficos → Mapa → Excel → Mapa por sucursal"""))

# ── CELL 1 — CONFIG ────────────────────────────────────────────────────────────
_CONFIG_PRE = r"""# ===========================================================
# CONFIGURACIÓN — Modificar solo esta sección
# ===========================================================
# CANASTA FIJA 2022-2026 (docs/BRECHA_CELIACA.md §14; lista con métricas: docs/brecha_celiaca/canasta_fija_2022_2026.csv)
# TIPOS: tipo -> {'peso': % del gasto de los hogares en alimentos y bebidas no alcohólicas (ENGHo 2017/18),
#                 'tacc': {EAN: descripción}, 'sin_tacc': {EAN: descripción}}.
#   Algunos productos tienen DOS códigos porque el fabricante cambió el EAN (Molinos en sep-oct 2023, Wakas en jun-2024):
#   van los dos, cada uno con su VIGENCIA (abajo), y PRODUCTO los junta: en cada sucursal y mes el producto entra una
#   vez, con la mediana de sus códigos vigentes.
#   Cambiar un EAN cambia la clave del caché: relee todo el SEPA. Cambiar GRAMOS, VIGENCIA, PRODUCTO, SUBTIPO, pesos o
#   descripciones NO relee.
"""

_CONFIG_POST = r"""

# Ponderación de la canasta: 'engho' = la brecha de la canasta es el promedio de las brechas por tipo con los pesos
# ENGHo de TIPOS (y la canasta por sucursal usa cantidades = peso / precio con TACC del año base); 'qty' = cantidades
# fijas TIPOS[tipo]['qty'] (el método de las corridas de agosto de 2026).
PONDERACION = 'engho'
ANIO_BASE_PONDERACION = None   # None = los primeros 12 meses del panel

# Canasta FLEXIBLE (corridas de agosto de 2026): True agrega como candidatos sin TACC todos los productos del maestro
# cuya descripción diga "sin TACC" y matcheen las palabras del tipo (SIN_TACC_REGLA). Rompe la continuidad y hace que
# la canasta dependa de qué maestro_sepa_completo haya en el Drive: dejarlo en False salvo para comparar.
USAR_REGLA_NOMBRE = False
SIN_TACC_REGLA = {
    'Fideos secos': (
        r'fideo|spaghetti|spagueti|tallarin|mostachol|tirabuz|penne|fusilli|codito|cintas|caracol|rigat|letras|moñito|farfalle|dedalitos|cornetti|risoni|canestri|spirali',
        r'premezcla|ñoqui|noqui|harina|frola|salsa|rallado|rebozador|tapa|tarta|sopa|salvado|arroz integral|yamani'),
    'Galletitas dulces': (
        r'galletit|galleta|biscuit|bizcoch|oblea|scon|pepa|magdalena|masita|vainilla|marmolad|nevadit|rueditas',
        r'salad|queso|jamon|cracker|tostada|arroz|pizza|premezcla|bizcochuelo|flan|postre|leche|grisin|palito|semilla|rallado|ensalada|hamburg|pochoclo|pan dulce|cereal|copitas|barrita|turron|budin|budín|yerba|mate|mermelada|caramelo|tableta|bocadito|bombon|gomita|chupetin|jugo|bebida|agua|infusion|pimenton|cacao|dulce de leche|polvo|helado|alfajor'),
    'Galletitas saladas y crackers': (
        r'cracker|tostada|tortita|talita|chalita|grisin|bizcochito|tostadita|(?:galletit|galleta).*(?:salad|queso|jamon|de arroz|pizza)|snack.*queso|palito.*(?:maiz|queso)',
        r'dulce|vainilla|chocolate|coco|limon|pepas|marmolad|premezcla|budin|oblea|alfajor|flan|leche|manteca|fideo|ensalada|hamburg|dambo|yamani|arroz integral|bizcochuelo|scon|rallado'),
    'Pan rallado y rebozador': (r'pan rallado|rebozador|rebozar|apanad', r'premezcla|coco|queso rallado'),
}

# EANs a excluir a mano (se filtran en la CELDA 7, después de leer: NO cambian el caché). Vacío por diseño: los errores
# de carga los saca el filtro de plausibilidad (banda x FACTOR_PLAUS, CELDA 7), que es simétrico y reproducible.
EANS_EXCLUIR = set()
FACTOR_PLAUS = 4   # banda de plausibilidad a nivel EAN (precio relativo a sus pares del mes)

SEPA_SOURCE = 'mi_drive'   # 'mi_drive' | 'local'
SEPA_DIR    = '/content/drive/MyDrive/carga'
OUTPUT_DIR  = '/content/drive/MyDrive/carga/output_brecha'
USE_CACHE = True

MES_INICIO_HISTORICO = '2022-01'   # la canasta fija se eligió con continuidad desde enero de 2022
MIN_TIPOS = 1         # tipos con los dos lados para que una sucursal-mes cuente en la canasta POR SUCURSAL (mapa)
MIN_SUC_AGG = 30      # sucursales mínimas para marcar una desagregación como confiable
MIN_SUC_SUBTIPO = 10  # sucursales mínimas para que un subtipo entre en la brecha de su tipo en un mes o grupo
FRAC_SUBTIPO_MES = 0.5   # serie mensual: un subtipo-mes con menos de esta fracción de sus sucursales habituales se
                         # imputa con su último mes válido (cambios de código de Molinos en sep-oct 2023, su hueco de
                         # dic-2023 a mar-2024: la mediana de pocas sucursales distintas movía el tipo entero)
FRAC_MESES_PANEL = 0.7   # panel balanceado: sucursal x tipo presentes en >= este % de los meses
VENTANA_GEO_MESES = 12   # provincias, regiones y cadenas: últimos N meses (además de las tablas por año)
MAX_PESO_IMPUTADO = 25   # provincias, regiones, empresas, cadenas y sucursales se comparan con la MISMA canasta (los 12
                         # subtipos con sus pesos): el subtipo con < MIN_SUC_SUBTIPO sucursales en el grupo toma la brecha
                         # nacional del mismo período. Confiable = eso pesa <= este % y el grupo tiene >= MIN_SUC_AGG sucursales
USAR_GEOREF = True       # concentración: departamento de cada sucursal por coordenadas (API Georef de datos.gob.ar); usa la
                         # caché del nb09 (output_trazabilidad/_cache_nb09/) y consulta solo las sucursales que falten
MIN_SUC_DEPTO = 5        # concentración: sucursales con brecha propia para mostrar un departamento

# Comercios fuera del universo: estaciones de servicio (19, 3001, 4 Estación Lima, 23 Axion Energy), Mercado Libre
# (2013) y farmacias (24 Farmacity / Simplicity)
CADENAS_FILTRAR = {'19', '2013', '3001', '4', '23', '24'}

RECLASIF_TOL_KM = 100   # provincia: se cambia solo si la sucursal cae a más de esto de su provincia declarada (BUG-44)
AMBA_RADIO_KM = 90      # AMBA = CABA + Buenos Aires a <= AMBA_RADIO_KM del Obelisco (BUG-42)"""

cells.append(cell_code(_CONFIG_PRE + _bloque_canasta() + _CONFIG_POST))

# ── CELL 2 — SETUP ─────────────────────────────────────────────────────────────
cells.append(cell_code(r"""# ============================================================
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
subprocess.run([sys.executable, '-m', 'pip', 'install', 'openpyxl', 'tqdm', 'pyarrow', '-q'], check=False)

import zipfile, gzip, io, re, shutil, warnings, gc, hashlib, tempfile, calendar as _cal
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
TMP_DIR = (Path('/content/tmp_sepa_nb06') if Path('/content').exists()
           else Path(tempfile.gettempdir()) / 'tmp_sepa_nb06')
TMP_DIR.mkdir(parents=True, exist_ok=True)

GEOJSON_PATH = SEPA_DIR / 'ar.json'
# Departamento de cada sucursal (concentración, CELDA 7): la caché de Georef que arma el nb09 en el Drive
GEOREF_PATH = SEPA_DIR / 'output_trazabilidad' / '_cache_nb09' / 'georef_sucursales.parquet'

def normalizar_ean(s):
    if pd.isna(s): return None
    s = str(s).strip().lstrip('0')
    return s if s else '0'

# EANs de referencia SOLO para detectar el factor centavos/pesos de cada mes.
REF_EANS_FACTOR = {'7790072002080', '7790070320285', '7790132098459'}

# ── Promedio con outliers fuera (banda relativa a la mediana) ────────────────
# Descarta valores fuera de [mediana/4, mediana x4] antes de promediar (igual que nb02/nb05).
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
print(f'  ar.json:  {"OK" if GEOJSON_PATH.exists() else "NO ENCONTRADO (no se reclasifican provincias ni hay mapas)"}')
print(f'  Georef:   {"caché del nb09 OK" if GEOREF_PATH.exists() else "sin la caché del nb09 (la CELDA 7 consulta la API)"}')"""))

# ── CELL 3 — MAESTROS ──────────────────────────────────────────────────────────
cells.append(cell_code(r"""# ============================================================
# CELDA 3 — Maestros de sucursales, cadenas, provincias y productos
# ============================================================
DATA_URL = 'https://raw.githubusercontent.com/santiagoriverti/precios_minoristas_supermercados/main/data'

def leer_maestro(nombre, **kwargs):
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
            return pd.read_excel(_p, **kwargs)
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

# Nombres según el comercio.csv del SEPA (SEPA diario, oct-2026). 'cadena' = bandera; 'empresa' = comercio.
NOMBRES_COMPUESTOS = {
    ('9','1'):'Vea', ('9','2'):'Disco', ('9','3'):'Jumbo',
    ('10','1'):'Carrefour', ('10','2'):'Carrefour Market', ('10','3'):'Carrefour Express', ('10','4'):'Carrefour Maxi',
    ('11','1'):'SuperChangomas', ('11','2'):'ChangoMas', ('11','3'):'SuperChangomas', ('11','4'):'SuperChangomas',
    ('11','5'):'HiperChangomas',
    ('16','1'):'Hipermercado Libertad', ('16','2'):'Mini Libertad',
}
NOMBRES_SIMPLES = {
    '2':'La Anónima', '3':'Deheza', '5':'California', '6':'Comodín', '8':'Mariano Max', '12':'Coto',
    '13':'Cooperativa Obrera', '15':'DIA', '20':'La Agrícola Regional', '21':'Toledo', '23':'Axion Energy',
    '24':'Farmacity', '47':'Unicoop',
}
EMPRESAS = {'9':'Cencosud (Vea, Disco, Jumbo)', '10':'Carrefour', '11':'ChangoMas', '16':'Libertad'}

def asignar_cadena(row):
    k = (row['id_comercio'], row['id_bandera'])
    if k in NOMBRES_COMPUESTOS: return NOMBRES_COMPUESTOS[k]
    if row['id_comercio'] in NOMBRES_SIMPLES: return NOMBRES_SIMPLES[row['id_comercio']]
    return f"Cadena {row['id_comercio']}"

def asignar_empresa(_c):
    return EMPRESAS.get(_c) or NOMBRES_SIMPLES.get(_c) or f'Cadena {_c}'

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
# Regiones INDEC; Buenos Aires se parte en AMBA (por coordenadas, CELDA 7) y resto (Pampeana)
REGION_PROV = {
    'CABA':'AMBA', 'Buenos Aires':'Pampeana', 'Córdoba':'Pampeana', 'Entre Ríos':'Pampeana', 'La Pampa':'Pampeana',
    'Santa Fe':'Pampeana', 'Catamarca':'Noroeste', 'Jujuy':'Noroeste', 'La Rioja':'Noroeste', 'Salta':'Noroeste',
    'Santiago del Estero':'Noroeste', 'Tucumán':'Noroeste', 'Chaco':'Noreste', 'Corrientes':'Noreste',
    'Formosa':'Noreste', 'Misiones':'Noreste', 'Mendoza':'Cuyo', 'San Juan':'Cuyo', 'San Luis':'Cuyo',
    'Chubut':'Patagonia', 'Neuquén':'Patagonia', 'Río Negro':'Patagonia', 'Santa Cruz':'Patagonia',
    'Tierra del Fuego':'Patagonia',
}

_mp_raw = leer_maestro('Maestro de Productos Interno.xlsx', dtype=str,
                       usecols=['producto_sepa_id','producto_descripcion','producto_marca','rubro',
                                'producto_cantidad_presentacion','producto_unidad_medida_presentac'])
# Maestro SEPA COMPLETO (opcional, del Drive carga/): nombres de productos que no están en el interno. Con la canasta
# fija solo se usa como respaldo de las descripciones (las de la canasta vienen en TIPOS).
_msepa = None
try:
    _msp = Path(SEPA_DIR) / 'maestro_sepa_completo.csv.gz'
    if _msp.exists():
        _msepa = pd.read_csv(_msp, dtype=str)
        print(f'  Maestro SEPA completo (Drive): {len(_msepa):,} EANs')
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
    _extra = _extra[~_extra['ean_norm'].isin(set(_base['ean_norm']))]   # solo EANs que faltan
    MP_META = pd.concat([_base, _extra], ignore_index=True)
    print(f'  Fusión de maestros: interno {len(_base):,} + {len(_extra):,} nuevos del SEPA = {len(MP_META):,} EANs')
else:
    MP_META = _base

# gramos/ml de la presentación (respaldo de GRAMOS): del CAMPO presentación o, si no da, de la descripción
def _to_gramos(_q, _u):
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
_g1 = [_to_gramos(a, b) for a, b in zip(MP_META['producto_cantidad_presentacion'],
                                        MP_META['producto_unidad_medida_presentac'])]
_g2 = [_gramos_desc(x) for x in MP_META['descripcion']]
MP_META['grams'] = [(_a if (_a == _a) else _b) for _a, _b in zip(_g1, _g2)]
MP_META = (MP_META.dropna(subset=['ean_norm']).drop_duplicates('ean_norm')
           .set_index('ean_norm')[['descripcion','marca','rubro','grams']])
print(f'  Maestro de productos (total): {len(MP_META):,} EANs con metadata')
print('Maestros OK')"""))

# ── CELL 4 — CANASTA ───────────────────────────────────────────────────────────
cells.append(cell_code(r"""# ============================================================
# CELDA 4 — Canasta: productos con TACC / sin TACC por tipo (CELDA 1)
# ============================================================
def _norm_ean(_e):
    _l = re.sub(r'\D', '', str(_e))
    return (_l.lstrip('0') or '0') if _l else None

def _items(_x):
    # {EAN: descripción} o [EAN, ...] -> {ean_norm: descripción o None}
    if isinstance(_x, dict):
        return {_norm_ean(k): (str(v) if v else None) for k, v in _x.items() if _norm_ean(k)}
    return {_norm_ean(k): None for k in _x if _norm_ean(k)}

# Canasta flexible (opcional): candidatos sin TACC por nombre
_desc_all = MP_META['descripcion'].fillna('').astype(str).str.lower()
_gf_all = _desc_all.str.contains(r'sin tacc|sin gluten|libre de gluten|s/tacc', regex=True)
def _sin_por_regla(_tp):
    _r = SIN_TACC_REGLA.get(_tp)
    if not _r: return set()
    _kw, _ex = _r
    _m = _gf_all & _desc_all.str.contains(_kw, regex=True) & ~_desc_all.str.contains(_ex, regex=True)
    return set(MP_META.index[_m])

TIPO_TACC, TIPO_SIN, TIPO_QTY, TIPO_PESO = {}, {}, {}, {}
EAN_TIPO, EAN_ROL, EAN_DESC = {}, {}, {}
for _tipo, _cfg in TIPOS.items():
    _t = _items(_cfg.get('tacc', {}))
    _s = _items(_cfg.get('sin_tacc', {}))
    if USAR_REGLA_NOMBRE:
        _s.update({_e: None for _e in _sin_por_regla(_tipo) if _e not in _s and _e not in _t})
    if not _t or not _s:
        print(f'AVISO: el tipo "{_tipo}" no tiene EANs en los dos lados: se ignora.')
        continue
    _dup = (set(_t) & set(_s)) | ((set(_t) | set(_s)) & set(EAN_TIPO))
    if _dup:
        raise ValueError(f'EANs repetidos entre lados o tipos en "{_tipo}": {sorted(_dup)}')
    TIPO_TACC[_tipo] = set(_t)
    TIPO_SIN[_tipo]  = set(_s)
    TIPO_QTY[_tipo]  = float(_cfg.get('qty', 1))
    TIPO_PESO[_tipo] = float(_cfg.get('peso', float('nan')))
    for _e, _d in _t.items(): EAN_TIPO[_e] = _tipo; EAN_ROL[_e] = 'tacc'; EAN_DESC[_e] = _d
    for _e, _d in _s.items(): EAN_TIPO[_e] = _tipo; EAN_ROL[_e] = 'sin';  EAN_DESC[_e] = _d
if not TIPO_TACC:
    raise ValueError('Ningún tipo válido en TIPOS (cada tipo necesita EANs con TACC y sin TACC).')
EANS_CONFIG = set(EAN_TIPO)

# Descripción: la de TIPOS (o la del maestro). Gramos: GRAMOS (verificados) o, si falta, el maestro (con aviso).
_GR_CFG = {_norm_ean(k): float(v) for k, v in globals().get('GRAMOS', {}).items() if _norm_ean(k)}
EAN_GRAMS, _gr_maestro, _sin_gramos = {}, [], []
for _e in sorted(EANS_CONFIG):
    if not EAN_DESC.get(_e):
        _dm = MP_META['descripcion'].get(_e) if _e in MP_META.index else None
        EAN_DESC[_e] = str(_dm)[:60] if isinstance(_dm, str) and _dm else f'EAN {_e}'
    _g = _GR_CFG.get(_e, float('nan'))
    if not (_g > 0):
        _g = MP_META['grams'].get(_e, float('nan')) if _e in MP_META.index else float('nan')
        if _g > 0:
            _gr_maestro.append(_e)
    if _g > 0:
        EAN_GRAMS[_e] = float(_g)
    else:
        _sin_gramos.append(_e)
if _gr_maestro:
    print(f'AVISO: {len(_gr_maestro)} EAN sin GRAMOS en la CELDA 1, se usan los del maestro: {_gr_maestro}')
if _sin_gramos:
    print(f'AVISO: {len(_sin_gramos)} EAN sin gramos (quedan afuera, no se pueden pasar a $/100 g): {_sin_gramos}')

# ── Subtipo / EQUIVALENCIA dentro de cada tipo (mapa y hoja Comparacion_productos) ──
# Fideos: por FORMA (Spaghetti↔Spaghetti, Tirabuzón↔Tirabuzón…), que sí es una equivalencia real. En los demás tipos
# los surtidos con y sin TACC son variedades distintas: la equivalencia honesta es el tipo (un solo grupo).
_SUBTIPO_KW = {
    'Fideos secos': [
        ('Spaghetti', ['spaghetti','spagueti','spaguetti','spaghettini','cabello','vermicelli','fideo fino','fideos finos']),
        ('Tallarín/Cintas', ['tallarin','tallarín','fettuccini','fetuccini','fettuccine','cintas','nido','canestri']),
        ('Mostachol/Penne', ['mostachol','rigati','rigato','penne','pluma','plumita','rigate']),
        ('Tirabuzón/Fusilli', ['tirabuzon','tirabuzón','fusilli','fusili','caracol','spirali']),
        ('Corto (codito, dedalito...)', ['codito','dedalitos','dedalito','tornillo','moñito','moñitos','farfalle',
                                         'risoni','cornetti','coditos','municion','ave maria','ave maría','letritas']),
    ],
}
def _subtipo(_desc, _tipo):
    if _tipo not in _SUBTIPO_KW:
        return _tipo
    _d = str(_desc).lower()
    for _lab, _kws in _SUBTIPO_KW[_tipo]:
        if any(_k in _d for _k in _kws):
            return _lab
    return 'Otros'
# El subtipo de la canasta fija (SUBTIPO, CELDA 1) manda; sin él, por palabras de la descripción
_SUBT_CFG = {_norm_ean(_e): _s for _s, _es in globals().get('SUBTIPO', {}).items() for _e in _es if _norm_ean(_e)}
EAN_SUBTIPO = {_e: _SUBT_CFG.get(_e) or _subtipo(EAN_DESC.get(_e, ''), EAN_TIPO[_e]) for _e in EANS_CONFIG}

print(f'Tipos: {len(TIPO_TACC)} | EANs de la canasta: {len(EANS_CONFIG)} | con gramos: {len(EAN_GRAMS)}')
for _t in TIPO_TACC:
    print(f'  [{_t}] {TIPO_PESO[_t]:.3f}% del gasto en alimentos (ENGHo) | con TACC: {len(TIPO_TACC[_t])} · '
          f'sin TACC: {len(TIPO_SIN[_t])}')"""))

# ── CELL 5 — ZIPs ──────────────────────────────────────────────────────────────
cells.append(cell_code(r"""# ============================================================
# CELDA 5 — ZIPs del SEPA: un archivo por parte de cada mes
# ============================================================
_PAT_SEM  = re.compile(r'^(\d{4})(A|B)$', re.IGNORECASE)
_PAT_ARC  = re.compile(r'^(\d{2})(\d{4})_pais_parte(\d+).*COMPLETO.*\.csv\.gz$', re.IGNORECASE)
PAT_FECHA = re.compile(r'^precio_(\d{8})$')

def detectar_semestres():
    result = []
    for z in sorted(SEPA_DIR.glob('*.zip')):
        m = _PAT_SEM.match(z.stem)
        if m:
            result.append((z, int(m.group(1)), m.group(2).upper()))
    return result

def _dias_archivo(z, nombre):
    with zipfile.ZipFile(z) as zf:
        with zf.open(nombre) as s:
            with gzip.open(s, 'rt', encoding='utf-8', errors='replace') as g:
                return sum(1 for c in g.readline().split(',') if c.strip().startswith('precio_'))

def archivos_por_mes():
    # {mes: [(zip, archivo), ...]} con UN archivo por parte del mes. Si hay más de uno para la misma parte (2024B.zip
    # trae 082024_pais_parte1COMPLETO.csv.gz, días 1 a 5, y ...COMPLETOb.csv.gz, días 1 a 15, con los mismos precios),
    # se usa el que cubre más días, como el nb08 y el nb09 (las corridas anteriores del nb06 leían los dos).
    cand = {}
    for z, _a, _s in detectar_semestres():
        with zipfile.ZipFile(z) as zf:
            for info in zf.infolist():
                m = _PAT_ARC.match(Path(info.filename).name)
                if m:
                    mes = f'{m.group(2)}-{m.group(1)}'
                    if mes >= MES_INICIO_HISTORICO:
                        cand.setdefault((mes, int(m.group(3))), []).append((z, info.filename, info.file_size))
    meses = {}
    for (mes, parte), c in sorted(cand.items()):
        if len(c) > 1:
            dias = [_dias_archivo(z, n) for z, n, _t in c]
            k = max(range(len(c)), key=lambda j: (dias[j], c[j][2], j))
            print(f'  AVISO {mes} parte {parte}: {len(c)} archivos ('
                  + '; '.join(f'{Path(n).name} {d} días' for (z, n, _t), d in zip(c, dias))
                  + f'); se usa {Path(c[k][1]).name}')
            c = [c[k]]
        meses.setdefault(mes, []).append(c[0][:2])
    return meses

_mapa_mes = archivos_por_mes()
_meses_disp = sorted(_mapa_mes)
if not _meses_disp:
    raise RuntimeError(f'No hay meses disponibles >= {MES_INICIO_HISTORICO} en {SEPA_DIR}')
_mes_actual = _meses_disp[-1]   # mes en curso -> NUNCA se cachea
print(f'Meses disponibles: {len(_meses_disp)}  ({_meses_disp[0]} → {_meses_disp[-1]})')
_huecos = [str(p) for p in pd.period_range(_meses_disp[0], _meses_disp[-1], freq='M') if str(p) not in _mapa_mes]
if _huecos:
    print(f'  AVISO: meses sin archivo en los zips: {_huecos}')"""))

# ── CELL 6 — LECTURA ───────────────────────────────────────────────────────────
cells.append(cell_code(r"""# ============================================================
# CELDA 6 — Lectura MENSUAL de precios (una fila por sucursal × EAN × mes), con caché por mes
# ============================================================
# Para cada mes >= MES_INICIO_HISTORICO, el precio de cada EAN de la canasta en cada sucursal es la MEDIANA de sus
# precios diarios del mes (de todas las partes) y 'dias' los días con precio. Se filtran las LÍNEAS del CSV por EAN
# antes de parsear (como el nb08). Filas repetidas del SEPA (misma sucursal, producto y día): una sola vez. Factor
# centavos/pesos por mes con los EANs de referencia. Solo sucursales del maestro con coordenadas.
# Caché: un archivo por MES CERRADO en _cache/brecha_v3_<clave>/ (si Colab se corta, al volver a ejecutar sigue donde
# quedó); el mes en curso se lee siempre. La clave cambia con los EANs de la canasta. El caché NO mira si cambió el
# zip: si se reemplaza el zip de un mes ya guardado (p. ej. el semestral oficial de 2026B), borrar sus AAAA-MM.parquet.
_K = ['id_comercio', 'id_bandera', 'id_sucursal', 'ean_norm']
_EANS_LECTURA = EANS_CONFIG | REF_EANS_FACTOR
_SUC_OK = {f'{a}|{b}|{c}' for a, b, c in IDS_PAIS}
_cache_key = hashlib.md5('|'.join(sorted(EANS_CONFIG)).encode()).hexdigest()[:8]
_cache_dir = CACHE_DIR / f'brecha_v3_{_cache_key}'

def _leer_archivo(_z, _nombre):
    # Líneas del CSV con EANs de la canasta (o de referencia) -> filas (sucursal, EAN, día, precio)
    _keep = []
    with zipfile.ZipFile(_z) as _zf:
        with _zf.open(_nombre) as _s:
            with gzip.open(_s, 'rt', encoding='utf-8', errors='replace') as _g:
                _hdr = _g.readline()
                _i = [c.strip().strip('"') for c in _hdr.split(',')].index('id_producto')
                for _line in _g:
                    _p = _line.split(',', _i + 2)
                    if len(_p) > _i and _p[_i].strip().strip('"').lstrip('0') in _EANS_LECTURA:
                        _keep.append(_line)
    if not _keep:
        return None
    _df = pd.read_csv(io.StringIO(_hdr + ''.join(_keep)), dtype=str, low_memory=False)
    del _keep
    _df.columns = [c.strip().strip('"') for c in _df.columns]
    _cp = [c for c in _df.columns if PAT_FECHA.match(c)]
    _df['ean_norm'] = _df['id_producto'].astype(str).str.strip().str.lstrip('0')
    for _c in ['id_comercio', 'id_bandera', 'id_sucursal']:
        _df[_c] = _df[_c].astype(str).str.strip()
    _L = _df.melt(id_vars=_K, value_vars=_cp, var_name='dia', value_name='precio')
    _L['precio'] = pd.to_numeric(_L['precio'], errors='coerce')
    _L = _L[_L['precio'] > 0].copy()
    _L['dia'] = _L['dia'].str[-8:]
    return _L

def _leer_mes(_lbl):
    _ps = [_p for _p in (_leer_archivo(_z, _n) for _z, _n in _mapa_mes[_lbl]) if _p is not None and len(_p)]
    if not _ps:
        return None
    _L = pd.concat(_ps, ignore_index=True)
    del _ps
    _ref = _L.loc[_L['ean_norm'].isin(REF_EANS_FACTOR), 'precio']
    _med_ref = float(_ref.median()) if len(_ref) else float(_L['precio'].median())
    _fac = 100 if _med_ref > 10_000 else 1
    _L = _L[_L['ean_norm'].isin(EANS_CONFIG)]
    _L = _L[(_L['id_comercio'] + '|' + _L['id_bandera'] + '|' + _L['id_sucursal']).isin(_SUC_OK)]
    if not len(_L):
        return None
    if _fac == 100:
        _L['precio'] = _L['precio'] / 100
    _L = _L.groupby(_K + ['dia'], as_index=False)['precio'].median()          # filas repetidas: una vez por día
    _A = _L.groupby(_K, as_index=False).agg(precio=('precio', 'median'), dias=('precio', 'size'))
    _A['mes'] = _lbl
    _A['factor'] = _fac
    return _A

_cerrados = [m for m in _meses_disp if m < _mes_actual]
_mem = {}
if USE_CACHE:
    _cache_dir.mkdir(parents=True, exist_ok=True)
    _en_cache = {p.stem for p in _cache_dir.glob('????-??.parquet')}
else:
    _en_cache = set()
_faltan = [m for m in _cerrados if m not in _en_cache]
print(f'Caché {_cache_dir.name}: {len(set(_cerrados) & _en_cache)} meses cerrados guardados, {len(_faltan)} por leer '
      f'(+ el mes en curso {_mes_actual}, que se lee siempre)')
for _lbl in tqdm(_faltan, desc='Meses cerrados'):
    _d = _leer_mes(_lbl)
    if _d is None:
        print(f'  {_lbl}: sin precios de la canasta')
        continue
    if USE_CACHE:
        _d.to_parquet(_cache_dir / f'{_lbl}.parquet', index=False)
    else:
        _mem[_lbl] = _d
    del _d; gc.collect()

_partes = []
for _m in _cerrados:
    if USE_CACHE and (_cache_dir / f'{_m}.parquet').exists():
        _partes.append(pd.read_parquet(_cache_dir / f'{_m}.parquet'))
    elif _m in _mem:
        _partes.append(_mem[_m])
_actual = _leer_mes(_mes_actual)
if _actual is not None:
    _partes.append(_actual)
if not _partes:
    raise RuntimeError('Sin datos para los EANs de la canasta. Revisá los EANs de TIPOS (CELDA 1).')
datos_dia = pd.concat(_partes, ignore_index=True)
del _partes, _mem; gc.collect()
datos_dia = datos_dia.sort_values('mes').reset_index(drop=True)

ULTIMO_MES = _mes_actual
_NOM = {'01':'enero','02':'febrero','03':'marzo','04':'abril','05':'mayo','06':'junio',
        '07':'julio','08':'agosto','09':'septiembre','10':'octubre','11':'noviembre','12':'diciembre'}
NOMBRE_MES_TITLE = f"{_NOM[_mes_actual[5:7]]} {_mes_actual[:4]}".title()
_fx = datos_dia.groupby('mes')['factor'].first()
print(f'Observaciones (sucursal×EAN×mes): {len(datos_dia):,} | EANs con datos: {datos_dia["ean_norm"].nunique()}/{len(EANS_CONFIG)}')
print(f'Meses: {datos_dia["mes"].min()} → {datos_dia["mes"].max()} ({datos_dia["mes"].nunique()}) | Sucursales: '
      f'{datos_dia.groupby(["id_comercio","id_bandera","id_sucursal"]).ngroups:,} | meses en centavos: '
      f'{list(_fx[_fx == 100].index) or "ninguno"}')
_sin_datos = sorted(EANS_CONFIG - set(datos_dia['ean_norm']))
if _sin_datos:
    print(f'  AVISO: EANs de la canasta sin ningún precio: {_sin_datos}')"""))

# ── CELL 7 — BRECHA POR SUCURSAL × MES × TIPO ──────────────────────────────────
cells.append(cell_code(r"""# ============================================================
# CELDA 7 — Brecha INTRA-SUPERMERCADO por tipo (sucursal × mes)
# ============================================================
# Para cada SUCURSAL y MES, por tipo, el precio de cada lado = MEDIANA $/100 g de los productos de la lista que esa
# sucursal tuvo ese mes. Un tipo cuenta en esa sucursal-mes si tuvo >= 1 producto con TACC y >= 1 sin TACC: la brecha
# del tipo se calcula DENTRO del mismo super. El "más barato" (mínimo) se guarda solo como referencia ilustrativa
# (sesgado al alza porque el lado con TACC tiene más productos por sucursal; BRECHA_CELIACA §3.7).
datos_dia['tipo'] = datos_dia['ean_norm'].map(EAN_TIPO)
datos_dia['rol']  = datos_dia['ean_norm'].map(EAN_ROL)
datos_dia = datos_dia[datos_dia['tipo'].notna() & ~datos_dia['id_comercio'].isin(CADENAS_FILTRAR)].copy()
# Vigencia de los códigos que cambiaron de EAN (CELDA 1): fuera de su ventana no se usan (precios congelados)
_VIG = {_norm_ean(k): v for k, v in globals().get('VIGENCIA', {}).items() if _norm_ean(k)}
if _VIG:
    _vd = datos_dia['ean_norm'].map({_e: _v[0] for _e, _v in _VIG.items()})
    _vh = datos_dia['ean_norm'].map({_e: _v[1] for _e, _v in _VIG.items()})
    _fuera = ((_vd.notna() & (datos_dia['mes'] < _vd.fillna(''))) |
              (_vh.notna() & (datos_dia['mes'] > _vh.fillna('9999-99'))))
    print(f'  Vigencia de códigos (CELDA 1): {int(_fuera.sum()):,} obs fuera de la ventana de su código, no se usan '
          f'({datos_dia.loc[_fuera, "ean_norm"].nunique()} códigos)')
    datos_dia = datos_dia[~_fuera].copy()
_ex = set(globals().get('EANS_EXCLUIR', set()))
if _ex:
    _n0e = len(datos_dia)
    datos_dia = datos_dia[~datos_dia['ean_norm'].isin(_ex)].copy()
    print(f'  Excluidos {len(_ex)} EANs a mano (EANS_EXCLUIR): {_n0e - len(datos_dia):,} obs')
datos_dia['grams'] = datos_dia['ean_norm'].map(EAN_GRAMS)
_n0 = len(datos_dia)
datos_dia = datos_dia[datos_dia['grams'].notna() & (datos_dia['grams'] > 0)].copy()
if _n0 - len(datos_dia):
    print(f'  Excluidas {_n0 - len(datos_dia):,} obs de EANs sin gramos (no normalizables a $/100 g)')
datos_dia['precio_100'] = datos_dia['precio'] / datos_dia['grams'] * 100

# ── Filtro de plausibilidad a nivel EAN (data-quality, §3.8) ──────────────────
# Regla SIMÉTRICA e INFLACIÓN-ROBUSTA: cada EAN se mide contra sus pares del mismo tipo, lado y MES (mediana de los
# precios-EAN, uno por producto). Se descarta el EAN si su precio relativo mediano cae fuera de [1/FACTOR_PLAUS,
# FACTOR_PLAUS]: errores de carga groseros, sin elegir a mano ni favorecer la dirección de la brecha.
_fp = globals().get('FACTOR_PLAUS', 4)
_eanm = datos_dia.groupby(['tipo','rol','mes','ean_norm'])['precio_100'].median().reset_index(name='_p')
_eanm['_ref'] = _eanm.groupby(['tipo','rol','mes'])['_p'].transform('median')
_eanm['_rel'] = _eanm['_p'] / _eanm['_ref']
_emr = _eanm.groupby('ean_norm')['_rel'].median()
_bad = set(_emr[(_emr < 1/_fp) | (_emr > _fp)].index)
plausibilidad = pd.DataFrame({'ean_norm': sorted(_bad)})
if _bad:
    plausibilidad['tipo'] = plausibilidad['ean_norm'].map(EAN_TIPO)
    plausibilidad['rol'] = plausibilidad['ean_norm'].map(EAN_ROL)
    plausibilidad['descripcion'] = plausibilidad['ean_norm'].map(EAN_DESC)
    plausibilidad['precio_relativo_mediano'] = plausibilidad['ean_norm'].map(_emr).round(3)
    _n0p = len(datos_dia)
    datos_dia = datos_dia[~datos_dia['ean_norm'].isin(_bad)].copy()
    print(f'  Filtro de plausibilidad (banda ×{_fp}): {len(_bad)} EAN(s) fuera → {_n0p - len(datos_dia):,} obs:')
    for _r in plausibilidad.itertuples(index=False):
        print(f'      - {_r.ean_norm}  rel={_r.precio_relativo_mediano:.2f}  {str(_r.descripcion)[:50]}')

# ── Control de identidad de cada EAN (diagnóstico, no excluye) ────────────────
# Precio $/100 g de cada EAN relativo a la mediana del lado CON TACC de su tipo, mes por mes. Un código reutilizado
# para otro producto o una presentación mal cargada se ve como un salto del relativo: se marca 'revisar' si el
# relativo de sus últimos 12 meses difiere en más del doble del de sus primeros 12, o si salta x2 de un mes al otro.
_rt = (datos_dia[datos_dia['rol'] == 'tacc'].groupby(['tipo','mes','ean_norm'])['precio_100'].median()
       .groupby(level=['tipo','mes']).median().rename('_ref_tacc'))
_ce = (datos_dia.groupby(['tipo','rol','mes','ean_norm'])
       .agg(_p=('precio_100', 'median'), _n=('id_sucursal', 'size')).reset_index()
       .merge(_rt.reset_index(), on=['tipo','mes'], how='left'))
_ce['_rel'] = _ce['_p'] / _ce['_ref_tacc']
_rows_ce = []
for (_t, _r, _e), _g in _ce.sort_values('mes').groupby(['tipo','rol','ean_norm']):
    _v = _g['_rel'].to_numpy()
    _ini, _fin = np.nanmedian(_v[:12]), np.nanmedian(_v[-12:])
    _lr = np.abs(np.diff(np.log(_v[np.isfinite(_v) & (_v > 0)]))) if len(_v) > 1 else np.array([])
    _rows_ce.append({'tipo': _t, 'rol': _r, 'ean_norm': _e, 'descripcion': EAN_DESC.get(_e),
                     'gramos': EAN_GRAMS.get(_e), 'meses_con_precio': len(_g), 'primer_mes': _g['mes'].iloc[0],
                     'ultimo_mes': _g['mes'].iloc[-1], 'sucursales_mes_mediana': float(_g['_n'].median()),
                     'precio_100g_ultimo_mes': float(_g['_p'].iloc[-1]),
                     'relativo_al_lado_con_tacc': float(np.nanmedian(_v)), 'relativo_primeros_12': float(_ini),
                     'relativo_ultimos_12': float(_fin), 'cambio_ultimos_sobre_primeros': float(_fin / _ini),
                     'saltos_x2_mes_a_mes': int((_lr > np.log(2)).sum())})
control_ean = pd.DataFrame(_rows_ce)
if len(control_ean):
    control_ean['revisar'] = (~control_ean['cambio_ultimos_sobre_primeros'].between(0.5, 2)) | (control_ean['saltos_x2_mes_a_mes'] > 0)
    _rv = control_ean[control_ean['revisar']]
    print(f'  Control de identidad: {len(_rv)} EAN(s) para revisar (cambio de nivel x2 o salto x2 mes a mes; no se excluyen):')
    for _r in _rv.itertuples(index=False):
        print(f'      - [{_r.tipo} / {_r.rol}] {_r.ean_norm} {str(_r.descripcion)[:40]}: relativo {_r.relativo_primeros_12:.2f} '
              f'→ {_r.relativo_ultimos_12:.2f}, saltos x2: {_r.saltos_x2_mes_a_mes}')

# Precio de cada SUBTIPO por (sucursal, mes, lado): MEDIANA $/100 g de los productos presentes (estimador PRIMARIO,
# §3.3 y §14). La comparación es por subtipo (crackers con crackers, snacks con snacks, spaghetti con spaghetti): la
# mediana del tipo entero mezclaba subtipos de niveles muy distintos según qué tuviera cada sucursal (en las saladas,
# snacks con TACC de $2.000/100 g contra crackers sin TACC). Un producto con dos códigos (PRODUCTO, CELDA 1) entra con
# la mediana de sus códigos: cuenta una vez. El "más barato" (ilustrativo) es el mínimo de los productos a menos de x4
# de la mediana del grupo (siempre hay al menos uno), vectorizado: una función de Python por grupo tardaba minutos.
_sk = ['id_comercio','id_bandera','id_sucursal']
_PROD = {_norm_ean(_e): _p for _p, _es in globals().get('PRODUCTO', {}).items() for _e in _es if _norm_ean(_e)}
datos_dia['producto'] = datos_dia['ean_norm'].map(_PROD).fillna(datos_dia['ean_norm'])
datos_dia['subtipo'] = datos_dia['ean_norm'].map(EAN_SUBTIPO)
_pp = datos_dia.groupby(_sk + ['mes','tipo','subtipo','rol','producto'], as_index=False)['precio_100'].median()
_gtp = _sk + ['mes','tipo','subtipo','rol']
_mg = _pp.groupby(_gtp)['precio_100'].transform('median')
_pp['_banda'] = _pp['precio_100'].where((_pp['precio_100'] >= _mg / 4) & (_pp['precio_100'] <= _mg * 4))
tp = (_pp.groupby(_gtp).agg(precio_rep=('precio_100', 'median'), precio_min=('_banda', 'min'),
                             n_items=('precio_100', 'size')).reset_index())
del _pp, _mg

# ── Geografía: provincia por polígonos de ar.json con tolerancia (BUG-44), AMBA por coordenadas (BUG-42), región ──
# Una sucursal cambia de provincia SOLO si cae a más de RECLASIF_TOL_KM del polígono de su provincia declarada y dentro
# del polígono de otra (errores groseros de carga); cerca de un borde manda la declarada. Hasta 2026-10 el nb06 usaba
# rectángulos (pasaban Neuquén capital a La Pampa, Paraná a Santa Fe y San Nicolás a Entre Ríos). Sin ar.json no se
# reclasifica. Se sacan las sucursales 'Web' y las de CABA con coordenadas fuera de CABA (como el nb02).
from matplotlib.path import Path as _MPath
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

_OBELISCO = (-34.6037, -58.3816)
def _km_obelisco(lat, lon):
    _la, _lo = np.radians(lat), np.radians(lon)
    _la0, _lo0 = np.radians(_OBELISCO[0]), np.radians(_OBELISCO[1])
    _a = np.sin((_la - _la0) / 2) ** 2 + np.cos(_la0) * np.cos(_la) * np.sin((_lo - _lo0) / 2) ** 2
    return 2 * 6371 * np.arcsin(np.sqrt(_a))

_cols_suc = ['id_comercio','id_bandera','id_sucursal','sucursales_nombre','sucursales_latitud','sucursales_longitud',
             'sucursales_localidad','PROVINCIA'] + (['sucursales_tipo'] if 'sucursales_tipo' in suc_pais.columns else [])
suc_geo = suc_pais[_cols_suc].copy()
if 'sucursales_tipo' in suc_geo.columns:
    suc_geo = suc_geo[~suc_geo['sucursales_tipo'].astype(str).str.lower().str.contains('web|virtual')].copy()
suc_geo['cadena'] = suc_geo.apply(asignar_cadena, axis=1)
suc_geo['empresa'] = suc_geo['id_comercio'].map(asignar_empresa)
suc_geo['PROVINCIA_NORM'] = suc_geo['PROVINCIA'].map(PROV_NORM).fillna(suc_geo['PROVINCIA'])
_mask_caba = (suc_geo['PROVINCIA_NORM'].eq('CABA') & (
    (suc_geo['sucursales_latitud'] < -34.71) | (suc_geo['sucursales_latitud'] > -34.53) |
    (suc_geo['sucursales_longitud'] < -58.53) | (suc_geo['sucursales_longitud'] > -58.34)))
suc_geo = suc_geo[~_mask_caba].copy()
_POL_PROV = _poligonos_provincias(GEOJSON_PATH) if GEOJSON_PATH.exists() else {}
if not _POL_PROV:
    print(f'  AVISO: no está {GEOJSON_PATH.name}: no se reclasifica la provincia de ninguna sucursal')
_lon = suc_geo['sucursales_longitud'].to_numpy(dtype=float)
_lat = suc_geo['sucursales_latitud'].to_numpy(dtype=float)
_decl = suc_geo['PROVINCIA_NORM'].to_numpy(dtype=object)
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
suc_geo['PROVINCIA_NORM'] = _nueva
if _cambio.any():
    _det = pd.Series([f'{_a} -> {_b}' for _a, _b in zip(_decl[_cambio], _nueva[_cambio])]).value_counts()
    print(f'  Reclasificadas {int(_cambio.sum())} sucursales por coordenadas (a más de {RECLASIF_TOL_KM} km de su '
          f'provincia declarada): ' + ', '.join(f'{_k} ({_v})' for _k, _v in _det.items()))
suc_geo['amba'] = (suc_geo['PROVINCIA_NORM'].eq('CABA') |
                   (suc_geo['PROVINCIA_NORM'].eq('Buenos Aires') &
                    (_km_obelisco(suc_geo['sucursales_latitud'], suc_geo['sucursales_longitud']) <= AMBA_RADIO_KM)))
suc_geo['region'] = np.where(suc_geo['amba'], 'AMBA', suc_geo['PROVINCIA_NORM'].map(REGION_PROV).fillna('Sin región'))
print(f'  AMBA (CABA + Buenos Aires a <= {AMBA_RADIO_KM} km del Obelisco): {int(suc_geo["amba"].sum()):,} sucursales')

# ── Departamento de cada sucursal (Georef de datos.gob.ar, por coordenadas) para la concentración (CELDA 8): la caché
# del nb09 y la propia (_cache/georef_sucursales.parquet); con USAR_GEOREF se consultan las sucursales que falten. La
# localidad del maestro no sirve como mercado: DIA la carga con el nombre de la provincia ("CAPITAL FEDERAL") ──
suc_geo = suc_geo.drop_duplicates(['id_comercio','id_bandera','id_sucursal']).copy()
suc_geo['suc_key'] = suc_geo['id_comercio'] + '|' + suc_geo['id_bandera'] + '|' + suc_geo['id_sucursal']
_GR_COLS = ['suc','departamento_id','departamento','municipio']
_gr_propia = CACHE_DIR / 'georef_sucursales.parquet'
_gr = [pd.read_parquet(_p)[_GR_COLS] for _p in (Path(GEOREF_PATH), _gr_propia) if _p.exists()]
_gr = (pd.concat(_gr, ignore_index=True).drop_duplicates('suc', keep='last') if _gr
       else pd.DataFrame(columns=_GR_COLS))
_pend = suc_geo[~suc_geo['suc_key'].isin(set(_gr['suc']))]
if USAR_GEOREF and len(_pend):
    import urllib.request, time as _time
    print(f'  Georef: consultando {len(_pend):,} sucursales...')
    _filas = []
    for _i in range(0, len(_pend), 500):
        _b = _pend.iloc[_i:_i + 500]
        _body = _json.dumps({'ubicaciones': [{'lat': float(_la), 'lon': float(_lo), 'aplanar': True,
                                              'campos': 'departamento.id,departamento.nombre,municipio.nombre'}
                                             for _la, _lo in zip(_b['sucursales_latitud'], _b['sucursales_longitud'])]}).encode()
        try:
            _req = urllib.request.Request('https://apis.datos.gob.ar/georef/api/ubicacion', data=_body,
                                          headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(_req, timeout=120) as _r:
                _res = _json.loads(_r.read())['resultados']
        except Exception as _e:
            print(f'  AVISO: Georef no respondió ({_e}): las sucursales que faltan quedan sin departamento')
            break
        for _k, _x in zip(_b['suc_key'], _res):
            _u = _x.get('ubicacion') or {}
            _filas.append({'suc': _k, 'departamento_id': _u.get('departamento_id'),
                           'departamento': _u.get('departamento_nombre'), 'municipio': _u.get('municipio_nombre')})
        _time.sleep(0.5)
    if _filas:
        _gr = pd.concat([_gr, pd.DataFrame(_filas)], ignore_index=True).drop_duplicates('suc', keep='last')
        if USE_CACHE:
            _gr.to_parquet(_gr_propia, index=False)
suc_geo = suc_geo.merge(_gr.rename(columns={'suc': 'suc_key'}), on='suc_key', how='left')
print(f'  Departamento (Georef): {int(suc_geo["departamento_id"].notna().sum()):,} de {len(suc_geo):,} sucursales')

_GEO = ['cadena','empresa','PROVINCIA_NORM','region','amba','sucursales_localidad','sucursales_nombre']
tp = tp.merge(suc_geo[_sk + _GEO], on=_sk, how='inner')
tp['localidad'] = (tp['sucursales_localidad'].astype(str).str.strip()
                   .replace({'':'N/D','nan':'N/D','None':'N/D'}))

# ── DIAGNÓSTICO de cobertura por tipo (todo el período) ──────────────────────
_cob_rows = []
print('=== Cobertura por tipo (sucursales que ofrecen cada lado, todo el período) ===')
for _t in TIPO_TACC:
    _st = tp[tp['tipo'] == _t]
    _set_t = set(map(tuple, _st[_st['rol']=='tacc'][_sk].drop_duplicates().to_numpy()))
    _set_s = set(map(tuple, _st[_st['rol']=='sin'][_sk].drop_duplicates().to_numpy()))
    _both  = _set_t & _set_s
    print(f'  [{_t}] con TACC: {len(_set_t):>5} · sin TACC: {len(_set_s):>5} · con LOS DOS: {len(_both):>5}')
    _cob_rows.append({'tipo':_t,'sucursales_tacc':len(_set_t),'sucursales_sin_tacc':len(_set_s),'sucursales_ambos':len(_both)})
cobertura_tipo = pd.DataFrame(_cob_rows)

# ── ATÓMICO: brecha por (sucursal, mes, tipo, subtipo) con LOS DOS lados en ese super-mes; la del TIPO en la
# sucursal-mes = promedio geométrico de las de sus subtipos con los dos lados (pesos iguales): sus precios con y sin
# TACC son los promedios geométricos de las medianas de esos subtipos, así que sin / tacc - 1 es esa brecha ─
_idx = _sk + ['mes','PROVINCIA_NORM','region','amba','cadena','empresa','localidad','sucursales_nombre','tipo']
_tacc = tp[tp['rol']=='tacc'][_idx + ['subtipo','precio_rep','precio_min','n_items']].rename(
    columns={'precio_rep':'tacc','precio_min':'tacc_min','n_items':'n_tacc'})
_sin  = tp[tp['rol']=='sin'][_idx + ['subtipo','precio_rep','precio_min','n_items']].rename(
    columns={'precio_rep':'sin','precio_min':'sin_min','n_items':'n_sin'})
bt_sub = _tacc.merge(_sin, on=_idx + ['subtipo'], how='inner')
bt_sub['brecha_pct'] = (bt_sub['sin'] / bt_sub['tacc'] - 1) * 100
bt_sub['brecha_min'] = (bt_sub['sin_min'] / bt_sub['tacc_min'] - 1) * 100
bt_sub['anio'] = bt_sub['mes'].str[:4]
bt_sub['suc_key'] = bt_sub['id_comercio'] + '|' + bt_sub['id_bandera'] + '|' + bt_sub['id_sucursal']
_lg = ['tacc', 'sin', 'tacc_min', 'sin_min']
bt_sm = (bt_sub.assign(**{f'_l_{_c}': np.log(bt_sub[_c]) for _c in _lg})
         .groupby(_idx, dropna=False)
         .agg(**{f'_l_{_c}': (f'_l_{_c}', 'mean') for _c in _lg},
              n_tacc=('n_tacc', 'sum'), n_sin=('n_sin', 'sum'), n_subtipos=('subtipo', 'size'))
         .reset_index())
for _c in _lg:
    bt_sm[_c] = np.exp(bt_sm.pop(f'_l_{_c}'))
bt_sm['brecha_pct'] = (bt_sm['sin'] / bt_sm['tacc'] - 1) * 100          # PRIMARIO: medianas por subtipo (§3.4, §14)
bt_sm['brecha_min'] = (bt_sm['sin_min'] / bt_sm['tacc_min'] - 1) * 100  # ilustrativo "más barato" (§3.7)
bt_sm['anio'] = bt_sm['mes'].str[:4]
bt_sm['suc_key'] = bt_sm['id_comercio'] + '|' + bt_sm['id_bandera'] + '|' + bt_sm['id_sucursal']

cobertura_mensual = (bt_sm.groupby(['tipo','mes'])
                     .agg(sucursales_ambos=('id_sucursal','size'), productos_tacc_prom=('n_tacc','mean'),
                          productos_sin_prom=('n_sin','mean')).reset_index()
                     .pivot_table(index='mes', columns='tipo', values='sucursales_ambos').reset_index())

# ── Ponderación ENGHo ─────────────────────────────────────────────────────────
# Brecha de la canasta = sum_k w_k (1 + g_k) - 1, con w_k = peso ENGHo del tipo renormalizado entre los tipos presentes
# y g_k la brecha del tipo (mediana entre sucursales). Para la canasta POR SUCURSAL (mapa, Brecha_sucursal) se usan
# cantidades fijas qty_k = w_k / (precio con TACC de k en el año base): con los precios del año base, el gasto con
# TACC se reparte como la ENGHo.
_meses_bt = sorted(bt_sm['mes'].unique())
if ANIO_BASE_PONDERACION:
    _mb = [m for m in _meses_bt if m.startswith(str(ANIO_BASE_PONDERACION))]
else:
    _mb = _meses_bt[:12]
_pb = bt_sm[bt_sm['mes'].isin(_mb)].groupby('tipo')['tacc'].median()
if PONDERACION == 'engho':
    _sin_peso = [t for t in TIPO_TACC if not (TIPO_PESO.get(t, float('nan')) > 0)]
    if _sin_peso:
        raise ValueError(f'PONDERACION = "engho" pero estos tipos no tienen peso en TIPOS: {_sin_peso}')
    W_TIPO = {t: TIPO_PESO[t] for t in TIPO_TACC}
    TIPO_QTY = {t: W_TIPO[t] / _pb[t] for t in TIPO_TACC if t in _pb.index}
else:
    W_TIPO = {t: TIPO_QTY[t] * _pb.get(t, float('nan')) for t in TIPO_TACC}
_sw = sum(v for v in W_TIPO.values() if v == v)
W_TIPO = {t: v / _sw for t, v in W_TIPO.items() if v == v}
ponderaciones = pd.DataFrame({'tipo': list(W_TIPO),
                              'pct_gasto_alimentos_engho': [TIPO_PESO.get(t) for t in W_TIPO],
                              'peso_en_la_canasta_pct': [100 * W_TIPO[t] for t in W_TIPO],
                              'precio_con_tacc_100g_base': [_pb.get(t) for t in W_TIPO],
                              'cantidad_100g_canasta_sucursal': [TIPO_QTY.get(t) for t in W_TIPO]})
print(f'\nPonderación ({PONDERACION}), año base {_mb[0]} → {_mb[-1]}:')
print(ponderaciones.to_string(index=False, float_format=lambda _x: f'{_x:,.4g}'))

# ── Canasta por (sucursal, mes): suma sobre los tipos con los dos lados (mapa y Brecha_sucursal) ─
bt_sm['qty'] = bt_sm['tipo'].map(TIPO_QTY)
bt_sm['base_c'] = bt_sm['tacc'] * bt_sm['qty']
bt_sm['cel_c']  = bt_sm['sin']  * bt_sm['qty']
_gk = _sk + ['mes','PROVINCIA_NORM','region','cadena','empresa','localidad']
if len(bt_sm):
    brecha_suc_mes = (bt_sm.groupby(_gk).agg(base=('base_c','sum'), celiaca=('cel_c','sum'),
                                             n_tipos=('tipo','nunique')).reset_index())
    brecha_suc_mes = brecha_suc_mes[brecha_suc_mes['n_tipos'] >= MIN_TIPOS].copy()
    brecha_suc_mes['brecha_pct'] = (brecha_suc_mes['celiaca'] / brecha_suc_mes['base'] - 1) * 100
    brecha_suc_mes['suc_key'] = (brecha_suc_mes['id_comercio'] + '|' + brecha_suc_mes['id_bandera'] + '|'
                                 + brecha_suc_mes['id_sucursal'])
else:
    brecha_suc_mes = pd.DataFrame(columns=_gk + ['base','celiaca','n_tipos','brecha_pct','suc_key'])

_nsuc_bt = bt_sm[_sk].drop_duplicates().shape[0] if len(bt_sm) else 0
print(f'\nObs (sucursal×mes×tipo) con los dos lados: {len(bt_sm):,} | sucursales con >= 1 par: {_nsuc_bt:,}')
print(f'Canasta por sucursal-mes (>= {MIN_TIPOS} tipos): {len(brecha_suc_mes):,} obs')"""))

# ── CELL 8 — AGREGACIONES ──────────────────────────────────────────────────────
cells.append(cell_code(r"""# ============================================================
# CELDA 8 — Brecha por tipo y de la canasta: tiempo, geografía y cadenas
# ============================================================
# Todo sale de bt_sub (brecha por sucursal × mes × SUBTIPO), como un índice de precios: (1) por subtipo, mediana ENTRE
# sucursales de su brecha; (2) brecha del tipo = promedio geométrico de las de sus subtipos (pesos iguales, entre los
# presentes en el grupo con >= MIN_SUC_SUBTIPO sucursales: la mediana de menos es ruido); (3) canasta de un grupo =
# sum_k w_k (1 + brecha del tipo k) - 1 (pesos ENGHo; en los grupos con ref_keys están todos los tipos). Así la serie no la
# mueve qué subtipos o tipos tiene cada sucursal cada mes (la mediana entre sucursales de la brecha del tipo de cada
# una tenía 2-3 veces más ruido mes a mes). 'confiable' (series) = están todos los tipos y cada uno con >= MIN_SUC_AGG
# sucursales. Provincias, regiones, empresas y cadenas se comparan con la MISMA canasta de subtipos (ref_keys, abajo).
def _agg_tipo(df, keys, ref_keys=None, detalle=None):
    # ref_keys (grupos: provincia, región, empresa, cadena): canasta FIJA de subtipos. El subtipo con menos de
    # MIN_SUC_SUBTIPO sucursales en el grupo toma la brecha NACIONAL del mismo período (ref_keys = [] o ['anio']), como
    # una celda que falta en un índice de precios: sin esto, un grupo sin snacks quedaba con la brecha de los crackers
    # sola (+165%) y una cadena sin obleas ni pepas, con otra composición de galletitas dulces. detalle: lista donde se
    # agrega la tabla por subtipo (con _imp = 1 en los subtipos imputados).
    _cols = keys + ['tipo','tacc_100','sin_100','brecha_mediana','brecha_prom','brecha_min_ilustr','n_subtipos',
                    'n_subtipos_imputados','n_sucursales','n_obs']
    if len(df) == 0:
        return pd.DataFrame(columns=_cols)
    _mensual = keys == ['mes']
    _grupos = ref_keys is not None and not _mensual
    _meses_all = sorted(df['mes'].unique()) if _mensual else []
    _n = df.groupby(keys + ['tipo','subtipo'])['suc_key'].nunique().rename('n_suc').reset_index()
    _ok = _n['n_suc'] >= globals().get('MIN_SUC_SUBTIPO', 1)
    if _mensual:
        # serie mensual: subtipo-mes con menos de FRAC_SUBTIPO_MES de sus sucursales habituales = faltante
        _ok &= _n['n_suc'] >= (globals().get('FRAC_SUBTIPO_MES', 0)
                               * _n.groupby(['tipo','subtipo'])['n_suc'].transform('median'))
    _L = ['_lt','_ls','_lb','_lbp','_lbm']
    def _medianas(_d, _k):
        _x = (_d.groupby(_k + ['tipo','subtipo'])
              .agg(tacc=('tacc','median'), sin=('sin','median'), b=('brecha_pct','median'), bp=('brecha_pct', _pmean),
                   bm=('brecha_min','median'), n_obs=('brecha_pct','size')).reset_index())
        return _x.assign(_lt=np.log(_x['tacc']), _ls=np.log(_x['sin']), _lb=np.log1p(_x['b'] / 100),
                         _lbp=np.log1p(_x['bp'] / 100), _lbm=np.log1p(_x['bm'] / 100), _imp=0)
    _ref = _medianas(df, ref_keys) if _grupos else None    # el país (o el país en ese año), con todas las sucursales
    df = df.merge(_n.loc[_ok, keys + ['tipo','subtipo']], on=keys + ['tipo','subtipo'], how='inner')
    if len(df) == 0 and not _grupos:
        return pd.DataFrame(columns=_cols)
    _s = _medianas(df, keys)
    if _mensual:
        # el subtipo-mes faltante se imputa con su último mes válido (como un índice de precios con un ítem que falta
        # temporalmente): la composición de subtipos del tipo no cambia de un mes a otro
        _grid = _s[['tipo','subtipo']].drop_duplicates().merge(pd.DataFrame({'mes': _meses_all}), how='cross')
        _s = _grid.merge(_s, on=['mes','tipo','subtipo'], how='left').sort_values(['tipo','subtipo','mes'])
        _falta = _s['_lb'].isna()
        _s[_L] = _s.groupby(['tipo','subtipo'])[_L].ffill()
        _s['_imp'] = (_falta & _s['_lb'].notna()).astype(int)
        _s['n_obs'] = _s['n_obs'].fillna(0)
        _s = _s[_s['_lb'].notna()]
    elif _grupos:
        _gs = _n[keys].drop_duplicates()
        _grid = (_gs.merge(_ref[ref_keys + ['tipo','subtipo']], on=ref_keys, how='inner') if ref_keys
                 else _gs.merge(_ref[['tipo','subtipo']], how='cross'))
        _rf = _ref[ref_keys + ['tipo','subtipo'] + _L].rename(columns={_c: _c + '_ref' for _c in _L})
        _s = (_grid.merge(_s, on=keys + ['tipo','subtipo'], how='left')
              .merge(_rf, on=ref_keys + ['tipo','subtipo'], how='left'))
        _falta = _s['_lb'].isna()
        for _c in _L:
            _s[_c] = _s[_c].fillna(_s.pop(_c + '_ref'))
        _s['_imp'] = _falta.astype(int)
        _s['n_obs'] = _s['n_obs'].fillna(0)
    if detalle is not None:
        detalle.append(_s.merge(_n[keys + ['tipo','subtipo','n_suc']], on=keys + ['tipo','subtipo'], how='left')
                       .assign(brecha=lambda _x: np.expm1(_x['_lb']) * 100)
                       [keys + ['tipo','subtipo','brecha','n_suc','_imp']])
    _o = (_s.groupby(keys + ['tipo'])
          .agg(_lt=('_lt','mean'), _ls=('_ls','mean'), _lb=('_lb','mean'), _lbp=('_lbp','mean'), _lbm=('_lbm','mean'),
               n_subtipos=('subtipo','size'), n_subtipos_imputados=('_imp','sum'), n_obs=('n_obs','sum'))
          .reset_index())
    _o['tacc_100'] = np.exp(_o['_lt'])
    _o['sin_100'] = np.exp(_o['_ls'])
    _o['brecha_mediana'] = np.expm1(_o['_lb']) * 100
    _o['brecha_prom'] = np.expm1(_o['_lbp']) * 100
    _o['brecha_min_ilustr'] = np.expm1(_o['_lbm']) * 100
    _o = _o.merge(df.groupby(keys + ['tipo'])['suc_key'].nunique().rename('n_sucursales').reset_index(),
                  on=keys + ['tipo'], how='left')
    if _grupos:
        _o['n_sucursales'] = _o['n_sucursales'].fillna(0).astype(int)
    return _o[_cols]

TIPOS_ORD = [t for t in TIPO_TACC]
def _canasta(df, keys, ref_keys=None, detalle=None):
    # tabla ancha: por grupo, brecha de la canasta (ponderada) + brecha mediana y n de cada tipo. peso_imputado_pct =
    # parte del peso de la canasta que no se midió en el grupo o mes: subtipos imputados con su último mes válido (serie
    # mensual) o con la brecha nacional del período (grupos, ref_keys; ahí confiable = eso <= MAX_PESO_IMPUTADO y el
    # grupo tiene >= MIN_SUC_AGG sucursales)
    _det = []
    _t = _agg_tipo(df, keys, ref_keys, _det)
    if detalle is not None:
        detalle.extend(_det)
    if not len(_t):
        return pd.DataFrame(columns=keys + ['brecha_canasta','n_tipos','n_min','peso_imputado_pct','confiable'])
    if keys:
        _pv = lambda _v: _t.pivot_table(index=keys, columns='tipo', values=_v, aggfunc='first')
    else:
        _pv = lambda _v: _t.set_index('tipo')[_v].to_frame().T.reset_index(drop=True)
    _g, _n, _im, _ns = (_pv(_v).reindex(columns=TIPOS_ORD) for _v in
                        ('brecha_mediana', 'n_sucursales', 'n_subtipos_imputados', 'n_subtipos'))
    _n, _im, _ns = (_x.reindex(index=_g.index) for _x in (_n, _im, _ns))
    _w = pd.Series(W_TIPO).reindex(TIPOS_ORD)
    _rel = 1 + _g / 100
    _num = (_rel * _w).sum(axis=1, min_count=1)
    _den = (_rel.notna() * _w).sum(axis=1)
    _o = pd.DataFrame(index=_g.index)
    _o['brecha_canasta'] = (_num / _den - 1) * 100
    _o['n_tipos'] = _g.notna().sum(axis=1)
    _o['n_min'] = _n.min(axis=1)
    _o['peso_imputado_pct'] = 100 * ((_im / _ns).fillna(0) * _w).sum(axis=1) / _den
    if ref_keys is not None and keys != ['mes']:
        _o['n_sucursales'] = df.groupby(keys)['suc_key'].nunique().reindex(_g.index).fillna(0).astype(int)
        _o['confiable'] = (_o['peso_imputado_pct'] <= MAX_PESO_IMPUTADO + 1e-9) & (_o['n_sucursales'] >= MIN_SUC_AGG)
        _d = pd.concat(_det, ignore_index=True)
        _d = _d[_d['_imp'] == 1]
        _o['subtipos_con_brecha_nacional'] = (_d.groupby(keys)['subtipo'].agg(lambda _x: ', '.join(_x))
                                              .reindex(_g.index).fillna(''))
    else:
        _o['confiable'] = (_o['n_tipos'] == len(TIPOS_ORD)) & (_o['n_min'] >= MIN_SUC_AGG)
    _o['subtipos_imputados'] = _im.sum(axis=1)
    for _c in TIPOS_ORD:
        _o[f'brecha_{_c}'] = _g[_c]
    for _c in TIPOS_ORD:
        _o[f'n_{_c}'] = _n[_c]
    if ref_keys is not None and keys != ['mes']:
        _o = _o[_o['peso_imputado_pct'] < 100 - 1e-9]     # un grupo sin ningún subtipo propio es la brecha nacional
    return _o.reset_index() if keys else _o.reset_index(drop=True)

# ── Panel BALANCEADO: sucursal × subtipo presentes (con los dos lados) en >= FRAC_MESES_PANEL de los meses ──
_nmes = bt_sub['mes'].nunique()
_minm = max(1, int(round(FRAC_MESES_PANEL * _nmes)))
_pres = bt_sub.groupby(_sk + ['tipo','subtipo'])['mes'].nunique()
_celdas = _pres[_pres >= _minm].index
bt_bal = bt_sub[bt_sub.set_index(_sk + ['tipo','subtipo']).index.isin(_celdas)].copy()
print(f'Panel balanceado: {len(_celdas):,} sucursal×subtipo presentes en >= {_minm}/{_nmes} meses '
      f'({bt_bal["suc_key"].nunique():,} sucursales)')

# ── Por tipo: período completo, mes (todas y panel), año ─────────────────────
brecha_tipo = _agg_tipo(bt_sub, [])
brecha_tipo_mensual = _agg_tipo(bt_sub, ['mes'])
brecha_tipo_mensual_bal = _agg_tipo(bt_bal, ['mes'])
brecha_tipo_anual = _agg_tipo(bt_sub, ['anio'])
brecha_tipo_anual_bal = _agg_tipo(bt_bal, ['anio'])

# ── Por subtipo (la comparación de base): período completo y por año ─────────
def _agg_subtipo(df, keys):
    _cols = keys + ['tipo','subtipo','tacc_100','sin_100','brecha_mediana','n_sucursales','n_obs']
    if len(df) == 0:
        return pd.DataFrame(columns=_cols)
    return (df.groupby(keys + ['tipo','subtipo'])
            .agg(tacc_100=('tacc','median'), sin_100=('sin','median'), brecha_mediana=('brecha_pct','median'),
                 n_sucursales=('suc_key','nunique'), n_obs=('brecha_pct','size')).reset_index())[_cols]
brecha_subtipo = _agg_subtipo(bt_sub, [])
brecha_subtipo_anual = _agg_subtipo(bt_sub, ['anio'])
brecha_subtipo_anual_bal = _agg_subtipo(bt_bal, ['anio'])

# ── Canasta: serie mensual (todas las sucursales y panel balanceado) ──────────
_det_todas, _det_bal = [], []
serie_mensual = _canasta(bt_sub, ['mes'], detalle=_det_todas)
serie_mensual_bal = _canasta(bt_bal, ['mes'], detalle=_det_bal)
serie_anual = _canasta(bt_sub, ['anio'])
serie_anual_bal = _canasta(bt_bal, ['anio'])
if len(serie_mensual):
    _nmed = serie_mensual['n_min'].median()
    _bajos = serie_mensual[serie_mensual['n_min'] < 0.6 * _nmed]
    if len(_bajos):
        print(f'  ⚠️ Cobertura BAJA en {len(_bajos)} mes(es) (el tipo con menos sucursales tiene < 60% de su mediana '
              f'{_nmed:.0f}): ' + ', '.join(f'{_m}(n={int(_n)})' for _m, _n in zip(_bajos['mes'], _bajos['n_min'])))

# ── Subtipos imputados en la serie mensual (rachas de meses seguidos con el valor de su último mes válido) ──
def _rachas(_det, _serie):
    _rows = []
    if not _det:
        return _rows
    for (_t, _st), _g in pd.concat(_det, ignore_index=True).sort_values('mes').groupby(['tipo','subtipo']):
        _f, _m = _g['_imp'].to_numpy(), _g['mes'].to_numpy()
        _nn, _bb = _g['n_suc'].fillna(0).to_numpy(), _g['brecha'].to_numpy()
        _i = 0
        while _i < len(_f):
            if _f[_i]:
                _j = _i
                while _j + 1 < len(_f) and _f[_j + 1]:
                    _j += 1
                _rows.append({'serie': _serie, 'tipo': _t, 'subtipo': _st, 'desde': _m[_i], 'hasta': _m[_j],
                              'meses': _j - _i + 1, 'sucursales_min': int(_nn[_i:_j + 1].min()),
                              'sucursales_max': int(_nn[_i:_j + 1].max()), 'brecha_arrastrada': float(_bb[_i])})
                _i = _j + 1
            else:
                _i += 1
    return _rows
imputaciones = pd.DataFrame(_rachas(_det_todas, 'todas las sucursales') + _rachas(_det_bal, 'panel balanceado'),
                            columns=['serie','tipo','subtipo','desde','hasta','meses','sucursales_min','sucursales_max',
                                     'brecha_arrastrada'])
_largas = imputaciones[imputaciones['meses'] > 3]
if len(_largas):
    print(f'  ⚠️ Subtipos imputados más de 3 meses seguidos (hoja Imputaciones; la serie arrastra su último valor):')
    for _r in _largas.itertuples(index=False):
        print(f'      - [{_r.serie}] {_r.tipo} / {_r.subtipo}: {_r.desde} → {_r.hasta} ({_r.meses} meses, '
              f'{_r.sucursales_min}-{_r.sucursales_max} sucursales; arrastra {_r.brecha_arrastrada:+.1f}%)')

# ── Geografía y cadenas: últimos VENTANA_GEO_MESES meses y por año ────────────
# Misma canasta en todos los grupos (ref_keys): el subtipo sin MIN_SUC_SUBTIPO sucursales en el grupo toma la brecha
# nacional del período; peso_imputado_pct dice cuánto de la canasta no se midió en el grupo
_meses_v = sorted(bt_sub['mes'].unique())[-VENTANA_GEO_MESES:]
bt_v = bt_sub[bt_sub['mes'].isin(_meses_v)]
VENTANA_TXT = f'{_meses_v[0]} → {_meses_v[-1]}' if _meses_v else ''
def _con_datos_propios(_t):
    # tablas por tipo y grupo: afuera el tipo sin ningún subtipo propio en el grupo (sería la brecha nacional)
    return _t[_t['n_subtipos_imputados'] < _t['n_subtipos']].reset_index(drop=True) if len(_t) else _t
brecha_prov = _canasta(bt_v, ['PROVINCIA_NORM'], []).rename(columns={'PROVINCIA_NORM':'provincia'})
brecha_tipo_prov = _con_datos_propios(_agg_tipo(bt_v, ['PROVINCIA_NORM'], [])).rename(columns={'PROVINCIA_NORM':'provincia'})
brecha_region = _canasta(bt_v, ['region'], [])
brecha_tipo_region = _con_datos_propios(_agg_tipo(bt_v, ['region'], []))
brecha_region_anual = _canasta(bt_sub, ['region','anio'], ['anio'])
brecha_empresa = _canasta(bt_v, ['empresa'], [])
brecha_tipo_empresa = _con_datos_propios(_agg_tipo(bt_v, ['empresa'], []))
brecha_empresa_anual = _canasta(bt_sub, ['empresa','anio'], ['anio'])
brecha_cadena = _canasta(bt_v, ['cadena'], [])
for _d in (brecha_prov, brecha_region, brecha_empresa, brecha_cadena):
    if len(_d):
        _d.sort_values('brecha_canasta', inplace=True)

# ── Canasta COMPARABLE por sucursal y mes (mapa, Brecha_sucursal, concentración): la misma canasta de subtipos en todas
# las sucursales; el subtipo que la sucursal no tiene con los dos lados toma la brecha nacional del mes (la de la serie
# mensual, imputación incluida). peso_propio_pct = parte del peso medida en la sucursal. La canasta por cantidades de la
# CELDA 7 (brecha_pct) suma solo los tipos presentes: dependía de qué tipos tiene cada sucursal (con 2 tipos, mediana
# +77%; con 3, +134%; DIA solo tiene fideos y galletitas dulces).
_subs = bt_sub[['tipo','subtipo']].drop_duplicates()
_subs['_w'] = _subs['tipo'].map(W_TIPO) / _subs.groupby('tipo')['subtipo'].transform('size')
_nac = (pd.concat(_det_todas, ignore_index=True)[['mes','tipo','subtipo','brecha']].rename(columns={'brecha': '_bn'})
        if _det_todas else pd.DataFrame(columns=['mes','tipo','subtipo','_bn']))
_cs = (brecha_suc_mes[['suc_key','mes']].drop_duplicates().merge(_subs, how='cross')
       .merge(bt_sub[['suc_key','mes','tipo','subtipo','brecha_pct']], on=['suc_key','mes','tipo','subtipo'], how='left')
       .merge(_nac, on=['mes','tipo','subtipo'], how='left'))
_cs['_wp'] = _cs['_w'] * _cs['brecha_pct'].notna()
_cs['_lb'] = np.log1p(_cs['brecha_pct'].fillna(_cs['_bn']) / 100)
_ct = _cs.groupby(['suc_key','mes','tipo'], as_index=False).agg(_lb=('_lb','mean'), _wp=('_wp','sum'))
_ct['_v'] = np.exp(_ct['_lb']) * _ct['tipo'].map(W_TIPO)
_cc = _ct.groupby(['suc_key','mes'], as_index=False).agg(_v=('_v','sum'), peso_propio_pct=('_wp','sum'))
_cc['brecha_comparable'] = (_cc['_v'] - 1) * 100
_cc['peso_propio_pct'] *= 100
brecha_suc_mes = brecha_suc_mes.drop(columns=['brecha_comparable','peso_propio_pct'], errors='ignore').merge(
    _cc[['suc_key','mes','brecha_comparable','peso_propio_pct']], on=['suc_key','mes'], how='left')
del _cs, _ct, _cc

# ── Concentración: mercado local = DEPARTAMENTO (Georef, CELDA 7) ─────────────
# HHI de empresas con la cuota = sucursales de cada empresa entre las del universo del departamento (el SEPA no tiene
# ventas). Brecha de cada sucursal = mediana de su canasta comparable en la ventana; solo las sucursales con >= 50% del
# peso medido en ellas (en las demás la canasta es casi la nacional). Antes se agrupaba por el texto de la localidad,
# que DIA carga con el nombre de la provincia ("CAPITAL FEDERAL", "BUENOS AIRES"): la correlación salía de la cadena.
_uni = suc_geo[~suc_geo['id_comercio'].isin(CADENAS_FILTRAR) & suc_geo['departamento_id'].notna()]
_bs = (brecha_suc_mes[brecha_suc_mes['mes'].isin(_meses_v)]
       .groupby('suc_key').agg(brecha=('brecha_comparable','median'), peso_propio_pct=('peso_propio_pct','mean')))
_bs = _bs[_bs['peso_propio_pct'] >= 50].join(suc_geo.set_index('suc_key')['departamento_id'], how='inner')
CONC_RHO, CONC_N = float('nan'), 0
if len(_uni):
    _cnt = _uni.groupby(['departamento_id','empresa']).size().rename('_n').reset_index()
    _cnt['_cuota'] = _cnt['_n'] / _cnt.groupby('departamento_id')['_n'].transform('sum')
    _dep = _cnt.groupby('departamento_id').agg(sucursales=('_n','sum'), empresas=('empresa','size'))
    _dep['hhi'] = (_cnt['_cuota'] ** 2).groupby(_cnt['departamento_id']).sum()
    _top = _cnt.sort_values(['_cuota','empresa'], ascending=[False, True]).drop_duplicates('departamento_id')
    _dep = _dep.join(_top.set_index('departamento_id')[['empresa','_cuota']]
                     .rename(columns={'empresa':'empresa_principal','_cuota':'cuota_principal_pct'}))
    _dep['cuota_principal_pct'] *= 100
    _nom = _uni.groupby('departamento_id').agg(provincia=('PROVINCIA_NORM', lambda _x: _x.mode().iat[0]),
                                                departamento=('departamento','first'))
    _bd = _bs.groupby('departamento_id').agg(sucursales_con_brecha=('brecha','size'), brecha_mediana=('brecha','median'),
                                             brecha_prom=('brecha', _pmean), peso_propio_medio=('peso_propio_pct','mean'))
    concentracion = _nom.join(_dep).join(_bd, how='left').reset_index()
    concentracion['sucursales_con_brecha'] = concentracion['sucursales_con_brecha'].fillna(0).astype(int)
    concentracion['confiable'] = concentracion['sucursales_con_brecha'] >= MIN_SUC_DEPTO
    concentracion = concentracion.sort_values('sucursales', ascending=False).reset_index(drop=True)
    # correlación de rangos (Spearman) entre la brecha de cada sucursal y el HHI de su departamento
    _sx = _bs.join(_dep['hhi'], on='departamento_id').dropna(subset=['brecha','hhi'])
    if len(_sx) > 2:
        CONC_RHO, CONC_N = float(_sx['brecha'].rank().corr(_sx['hhi'].rank())), len(_sx)
else:
    concentracion = pd.DataFrame(columns=['departamento_id','provincia','departamento','sucursales','empresas','hhi',
                                          'empresa_principal','cuota_principal_pct','sucursales_con_brecha',
                                          'brecha_mediana','brecha_prom','peso_propio_medio','confiable'])
    print('  (sin departamentos de Georef: no se calcula la concentración)')

# ── Resumen ──────────────────────────────────────────────────────────────────
print('\n=== Brecha POR SUBTIPO (intra-super, $/100 g), todo el período ===')
if len(brecha_subtipo):
    print(brecha_subtipo[['tipo','subtipo','tacc_100','sin_100','brecha_mediana','n_sucursales']].round(1).to_string(index=False))
print('\n=== Brecha POR TIPO (promedio geométrico de las de sus subtipos), todo el período ===')
if len(brecha_tipo):
    print(brecha_tipo[['tipo','tacc_100','sin_100','brecha_mediana','brecha_min_ilustr','n_sucursales']].round(1).to_string(index=False))
print('\n=== Por tipo y año (panel balanceado) ===')
if len(brecha_tipo_anual_bal):
    print(brecha_tipo_anual_bal.pivot_table(index='anio', columns='tipo', values='brecha_mediana').round(1).to_string())
print('\n=== Canasta por año (ponderada ENGHo): todas las sucursales / panel balanceado ===')
if len(serie_anual):
    _sa = serie_anual[['anio','brecha_canasta','n_min']].merge(
        serie_anual_bal[['anio','brecha_canasta','n_min']], on='anio', how='left', suffixes=('', '_bal'))
    print(_sa.round(1).to_string(index=False))
_cg = ['brecha_canasta','peso_imputado_pct','n_sucursales','confiable']
print(f'\n=== Región (últimos {VENTANA_GEO_MESES} meses, {VENTANA_TXT}; misma canasta: subtipos sin datos en el grupo = '
      f'brecha nacional; confiable = <= {MAX_PESO_IMPUTADO}% del peso imputado y >= {MIN_SUC_AGG} sucursales) ===')
if len(brecha_region):
    print(brecha_region[['region'] + _cg].round(1).to_string(index=False))
print(f'\n=== Empresas (últimos {VENTANA_GEO_MESES} meses) ===')
if len(brecha_empresa):
    print(brecha_empresa[['empresa'] + _cg].round(1).to_string(index=False))
print(f'\n=== Cadenas (últimos {VENTANA_GEO_MESES} meses, solo confiables) ===')
if len(brecha_cadena):
    print(brecha_cadena.loc[brecha_cadena['confiable'], ['cadena'] + _cg[:-1]].round(1).to_string(index=False))
_pc = brecha_prov[brecha_prov['confiable']] if len(brecha_prov) else brecha_prov
if len(_pc):
    print(f'\nProvincias confiables: {len(_pc)} de {len(brecha_prov)} · MENOR brecha: {_pc.iloc[0]["provincia"]} '
          f'({_pc.iloc[0]["brecha_canasta"]:+.1f}%) · MAYOR: {_pc.iloc[-1]["provincia"]} ({_pc.iloc[-1]["brecha_canasta"]:+.1f}%)')
if len(concentracion):
    _cf = concentracion[concentracion['confiable']]
    print(f'\n=== Concentración (departamentos con >= {MIN_SUC_DEPTO} sucursales con brecha propia: {len(_cf)}) ===')
    print(f'  Spearman entre la brecha de cada sucursal y el HHI de su departamento: {CONC_RHO:+.2f} ({CONC_N:,} sucursales)')
    if len(_bs) >= 3:
        _h = _bs.join(concentracion.set_index('departamento_id')['hhi'], on='departamento_id').dropna(subset=['hhi'])
        _h['tercil_hhi'] = pd.qcut(_h['hhi'].rank(method='first'), 3, labels=['bajo','medio','alto'])
        print(_h.groupby('tercil_hhi', observed=True).agg(hhi_mediano=('hhi','median'), brecha_mediana=('brecha','median'),
                                                          sucursales=('brecha','size')).round(2).to_string())"""))

# ── CELL 8b — SERIE TPD (HEDÓNICA) ─────────────────────────────────────────────
cells.append(cell_code(r"""# ============================================================
# CELDA 8b — Serie TPD (hedónica) de la brecha: robustez frente a la imputación de subtipos
# ============================================================
# BRECHA_CELIACA §3.9 y §14.12. Una regresión por SUBTIPO con todas sus observaciones producto × sucursal × mes ($/100 g;
# un producto con dos códigos entra una vez, con la mediana de sus códigos, como en la CELDA 7):
#     ln p(producto, sucursal, mes) = α(sucursal, mes) + γ(producto) + β(mes) · sinTACC + ε
# α es la celda de la descriptiva (el subtipo en esa sucursal y mes): cada sin TACC se compara con los con TACC de su
# subtipo en el mismo super y mes. Con α por sucursal-mes del TIPO entero, la prima de un subtipo se medía contra todos
# los con TACC del tipo (las galletitas con chips daban la evolución al revés). γ fija el nivel de cada producto: qué
# productos tiene cada sucursal no mueve la serie (la mediana de la descriptiva sí). Mínimos cuadrados ponderados: cada
# producto pesa 1 / (productos de su lado en la celda). Nivel del subtipo = promedio de γ sin TACC − promedio de γ con
# TACC, cada producto pesado por su disponibilidad (observaciones de todo el período: ponderaciones fijas); brecha del
# subtipo en el mes = exp(nivel + β(mes)) − 1 (no depende de qué producto o mes se fija como referencia). Tipo =
# promedio geométrico de sus subtipos y canasta = suma ENGHo, como la descriptiva. NO arrastra: el subtipo-mes con menos
# de la mitad de sus sucursales, que la descriptiva arrastra (hoja Imputaciones), sale de las sucursales que hay, con su
# IC; solo con menos de MIN_SUC_SUBTIPO sucursales con los dos lados (con tan pocas, el error agrupado por sucursal
# subestima la incertidumbre) se mueve con el promedio de los demás subtipos de su tipo (el único subtipo de su tipo,
# el rebozador, queda con el valor del mes vecino). Dos universos: las celdas del panel balanceado (comparable con la
# serie clave) y todas las sucursales. Errores estándar agrupados por sucursal (CR1) e IC 95% por el método delta, con
# la covarianza entre subtipos y tipos. Ajuste exacto (ecuaciones normales con los efectos de celda descontados,
# matrices dispersas): no itera.
from scipy import sparse as _sp

def _tpd_ajuste(_d, _np, _nt, _nc, _ref, _base):
    # _d: g (celda: sucursal-mes del subtipo), c (sucursal), j (producto), t (mes), s (1 = sin TACC), y (log del precio), w (peso), enteros
    # 0..n-1 (c sobre las _nc sucursales de todos los tipos). Columnas: _np productos y _nt meses (sin TACC × mes); se
    # fijan γ(_ref) = 0 y β(_base) = 0. Devuelve θ completo (NaN = no identificado), la inversa de X'WX (columnas
    # estimadas) y los puntajes por sucursal Σ w·x·u para la covarianza agrupada.
    _N = len(_d)
    _g, _c, _j, _t, _s = (_d[_x].to_numpy() for _x in ('g', 'c', 'j', 't', 's'))
    _y, _w = _d['y'].to_numpy(float), _d['w'].to_numpy(float)
    _p, _ix = _np + _nt, np.arange(_N)
    _X = _sp.csr_matrix((np.ones(_N + int(_s.sum())), (np.concatenate([_ix, _ix[_s == 1]]),
                                                          np.concatenate([_j, _np + _t[_s == 1]]))), shape=(_N, _p))
    _G = int(_g.max()) + 1
    _Wg = np.bincount(_g, weights=_w, minlength=_G)
    _Cg = _sp.csr_matrix((_w, (_g, _ix)), shape=(_G, _N)) @ _X              # suma ponderada de x en cada sucursal-mes
    _A = (_X.T @ _sp.diags(_w) @ _X).toarray() - (_Cg.T @ _sp.diags(1.0 / _Wg) @ _Cg).toarray()
    _Sy = np.bincount(_g, weights=_w * _y, minlength=_G)
    _b = _X.T @ (_w * _y) - _Cg.T @ (_Sy / _Wg)
    _k = np.ones(_p, bool)
    _k[_ref] = False
    _k[_np + _base] = False
    _k &= np.diag(_A) > 1e-9 * max(1.0, float(np.diag(_A).max()))            # sin variación propia: no identificado
    _B = _A[np.ix_(_k, _k)]
    _rango = int(np.linalg.matrix_rank(_B))
    _Bi = np.linalg.inv(_B) if _rango == _B.shape[0] else np.linalg.pinv(_B)
    _th = np.full(_p, np.nan)
    _th[_k] = _Bi @ _b[_k]
    _th[_ref] = 0.0
    _th[_np + _base] = 0.0
    _f = _X @ np.nan_to_num(_th)
    _u = (_y - (_Sy / _Wg)[_g]) - (_f - (np.bincount(_g, weights=_w * _f, minlength=_G) / _Wg)[_g])
    _Sc = (_sp.csr_matrix((_w * _u, (_c, _ix)), shape=(_nc, _N)) @ _X).tocsc()[:, np.where(_k)[0]]
    # con rango incompleto (productos de un lado que nunca conviven en una celda con los demás, p. ej. dos códigos del
    # mismo producto sin unir en PRODUCTO) solo son válidas las combinaciones del espacio de filas: proyección para verlo
    return {'theta': _th, 'k': _k, 'Binv': _Bi, 'Sc': _Sc, 'rango_completo': _rango == _B.shape[0], 'grupos': _G,
            'proy': None if _rango == _B.shape[0] else _B @ _Bi}

def _tpd_comb(*_partes):
    # combina gradientes {subtipo: vector} con coeficientes: _partes = (coef, gradiente), ...
    _o = {}
    for _cf, _gd in _partes:
        for _key, _v in _gd.items():
            _o[_key] = _o.get(_key, 0) + _cf * _v
    return _o

def _tpd_serie(_pt, _tipos, _w_tipo, _min_suc=1):
    # _pt: suc_key, mes, tipo, subtipo, rol ('tacc' / 'sin'), producto, precio_100 (una fila por producto, sucursal y
    # mes). Una regresión por subtipo con efecto de celda (sucursal-mes del subtipo); tipo = promedio de sus subtipos;
    # canasta con los pesos ENGHo. El subtipo-mes con menos de _min_suc sucursales con los dos lados no tiene dato propio
    # (se mueve con los demás subtipos del tipo). Devuelve tipos, canasta, subtipos, productos y diagnóstico del ajuste.
    _pt = _pt[_pt['precio_100'] > 0].copy()
    _pt['w'] = 1.0 / _pt.groupby(['suc_key','mes','tipo','subtipo','rol'])['producto'].transform('size')
    _pt['y'] = np.log(_pt['precio_100'].astype(float))
    _pt['s'] = (_pt['rol'] == 'sin').astype(int)
    _meses = sorted(_pt['mes'].unique())
    _nt = len(_meses)
    _pt['t'] = _pt['mes'].map({_m: _i for _i, _m in enumerate(_meses)})
    _sucs = sorted(_pt['suc_key'].unique())
    _nc = len(_sucs)
    _pt['c'] = _pt['suc_key'].map({_x: _i for _i, _x in enumerate(_sucs)})
    _q = _nc / max(_nc - 1, 1)                                               # CR1
    _fit, _lev, _id, _grad, _npar = {}, {}, {}, {}, {}
    _prods, _diag = [], []
    for (_tp, _sub), _d in _pt.groupby(['tipo','subtipo'], sort=True):
        if _tp not in _tipos or _d['s'].nunique() < 2:
            continue
        _d = _d.copy()
        _d['g'] = _d.groupby(['suc_key','mes'], sort=False).ngroup()
        _pi = (_d.groupby(['producto','rol'], as_index=False).agg(obs=('y', 'size'))
               .sort_values(['rol','producto']).reset_index(drop=True))
        _np = len(_pi)
        _d['j'] = _d['producto'].map(dict(zip(_pi['producto'], _pi.index)))
        _cel = _d.groupby('g').agg(t=('t', 'first'), smin=('s', 'min'), smax=('s', 'max'))
        _pares = (_cel[(_cel['smin'] == 0) & (_cel['smax'] == 1)].groupby('t').size()
                  .reindex(range(_nt), fill_value=0))
        if _pares.sum() == 0:
            continue
        _base = int(_pares[_pares > 0].index.min())
        _ref = int(_pi.loc[_pi['rol'] == 'tacc', 'obs'].idxmax())
        _r = _tpd_ajuste(_d, _np, _nt, _nc, _ref, _base)
        _th, _keep = _r['theta'], np.where(_r['k'])[0]
        _ok = ~np.isnan(_th[:_np])
        # nivel del subtipo: promedio de γ sin TACC − promedio de γ con TACC, cada producto pesado por su disponibilidad
        # (observaciones en todo el período: canasta fija, como un índice con ponderaciones fijas)
        _aL = np.zeros(_np + _nt)
        _peso = np.zeros(_np)
        for _lado, _sg in (('sin', 1.0), ('tacc', -1.0)):
            _x = _pi[(_pi['rol'] == _lado) & _ok]
            _peso[_x.index] = _x['obs'] / _x['obs'].sum()
            _aL[_x.index] = _sg * _peso[_x.index]
        _key = (_tp, _sub)
        _fit[_key] = {'Binv': _r['Binv'], 'Sc': _r['Sc']}
        _lv = np.full(_nt, np.nan)
        _no_est = 0
        for _t in range(_nt):
            if _pares[_t] < max(_min_suc, 1) or np.isnan(_th[_np + _t]):
                continue
            _a = _aL.copy()
            _a[_np + _t] += 1.0
            if _r['proy'] is not None and np.abs(_r['proy'] @ _a[_keep] - _a[_keep]).max() > 1e-7:
                _no_est += 1                       # nivel no identificado: se mueve con los demás subtipos
                continue
            _lv[_t] = float(_a @ np.nan_to_num(_th))
            _grad[(_tp, _sub, _t)] = {_key: _a[_keep]}
        _lev[_key], _id[_key], _npar[_key] = _lv, ~np.isnan(_lv), _pares.to_numpy()
        _gcon = float((_th[:_np] * _peso)[(_pi['rol'] == 'tacc').to_numpy() & _ok].sum())
        for _i, _row in _pi.iterrows():
            _prods.append({'tipo': _tp, 'subtipo': _sub, 'lado': 'sin TACC' if _row['rol'] == 'sin' else 'con TACC',
                           'producto': _row['producto'], 'obs': int(_row['obs']), 'peso_en_el_nivel': _peso[_i],
                           'gamma': _th[_i], 'mes_base': _meses[_base],
                           'nivel_vs_con_tacc_subtipo_pct': np.expm1(_th[_i] - _gcon) * 100, 'referencia': _i == _ref})
        _diag.append({'tipo': _tp, 'subtipo': _sub, 'obs': len(_d), 'celdas': _r['grupos'], 'productos': _np,
                      'meses_con_pares': int((_pares > 0).sum()), 'meses_con_dato_propio': int((~np.isnan(_lv)).sum()),
                      'meses_no_estimables': _no_est, 'rango_completo': _r['rango_completo']})
    # subtipo-mes sin dato propio: su valor del mes vecino movido con el promedio de los demás subtipos del tipo que tienen
    # dato propio en los dos meses (imputación por la variación del resto del agregado; adelante y después hacia atrás)
    _filas_s = []
    for _tp in _tipos:
        _subs = [_k for _k in _lev if _k[0] == _tp]
        for _paso in (1, -1):
            _orden = range(1, _nt) if _paso == 1 else range(_nt - 2, -1, -1)
            for _t in _orden:
                _u = _t - _paso
                for _k in _subs:
                    if not np.isnan(_lev[_k][_t]) or np.isnan(_lev[_k][_u]):
                        continue
                    _otros = [_o for _o in _subs if _o != _k and _id[_o][_t] and _id[_o][_u]]
                    _mov = float(np.mean([_lev[_o][_t] - _lev[_o][_u] for _o in _otros])) if _otros else 0.0
                    _lev[_k][_t] = _lev[_k][_u] + _mov
                    _grad[(_tp, _k[1], _t)] = _tpd_comb((1.0, _grad[(_tp, _k[1], _u)]),
                                                        *[(1.0 / len(_otros), _grad[(_tp, _o[1], _t)]) for _o in _otros],
                                                        *[(-1.0 / len(_otros), _grad[(_tp, _o[1], _u)]) for _o in _otros])
        for _k in _subs:
            for _t in range(_nt):
                if not np.isnan(_lev[_k][_t]):
                    _filas_s.append({'mes': _meses[_t], 'tipo': _tp, 'subtipo': _k[1],
                                     'brecha_tpd': np.expm1(_lev[_k][_t]) * 100,
                                     'sucursales_con_pares': int(_npar[_k][_t]), 'movido_con_los_demas': not _id[_k][_t]})

    def _se(_gd):
        # error estándar de una combinación lineal de los parámetros de varios subtipos (covarianza agrupada por sucursal)
        _z = np.zeros(_nc)
        for _key, _v in _gd.items():
            _z += np.asarray(_fit[_key]['Sc'] @ (_fit[_key]['Binv'] @ _v)).ravel()
        return float(np.sqrt(_q * (_z ** 2).sum()))

    _filas, _lam, _fmov = [], {}, {}
    for _tp in _tipos:
        _subs = [_k for _k in _lev if _k[0] == _tp]
        for _t in range(_nt):
            _ks = [_k for _k in _subs if not np.isnan(_lev[_k][_t])]
            if not _ks:
                continue
            _l = float(np.mean([_lev[_k][_t] for _k in _ks]))
            _g = _tpd_comb(*[(1.0 / len(_ks), _grad[(_tp, _k[1], _t)]) for _k in _ks])
            _s = _se(_g)
            _lam[(_tp, _t)] = (_l, _g)
            _nm = int(sum(not _id[_k][_t] for _k in _ks))
            _fmov[(_tp, _t)] = _nm / len(_ks)
            _filas.append({'mes': _meses[_t], 'tipo': _tp, 'brecha_tpd': np.expm1(_l) * 100,
                           'brecha_tpd_ic95_inf': np.expm1(_l - 1.96 * _s) * 100,
                           'brecha_tpd_ic95_sup': np.expm1(_l + 1.96 * _s) * 100, 'error_estandar_log': _s,
                           'subtipos': len(_ks), 'subtipos_movidos': _nm})
    _filas_c = []
    for _t in range(_nt):
        _ws = {_tp: _w_tipo[_tp] for _tp in _tipos if (_tp, _t) in _lam}
        if not _ws:
            continue
        _sw = sum(_ws.values())
        _v = sum(_wk * np.exp(_lam[(_tp, _t)][0]) for _tp, _wk in _ws.items()) / _sw
        _s = _se(_tpd_comb(*[(_wk * np.exp(_lam[(_tp, _t)][0]) / _sw, _lam[(_tp, _t)][1]) for _tp, _wk in _ws.items()]))
        # peso_movido_pct: parte del peso de la canasta en subtipos sin dato propio ese mes (como peso_imputado_pct)
        _filas_c.append({'mes': _meses[_t], 'brecha_canasta_tpd': (_v - 1) * 100,
                         'brecha_canasta_tpd_ic95_inf': (_v - 1.96 * _s - 1) * 100,
                         'brecha_canasta_tpd_ic95_sup': (_v + 1.96 * _s - 1) * 100,
                         'peso_movido_pct': 100 * sum(_wk * _fmov[(_tp, _t)] for _tp, _wk in _ws.items()) / _sw,
                         'tipos_tpd': len(_ws)})
    return {'tipos': pd.DataFrame(_filas), 'canasta': pd.DataFrame(_filas_c), 'subtipos': pd.DataFrame(_filas_s),
            'productos': pd.DataFrame(_prods), 'ajuste': pd.DataFrame(_diag)}

# ── Datos: producto × sucursal × mes, con las sucursales del universo (CELDA 7); dos universos: las celdas del panel
# balanceado (sucursal × subtipo de la CELDA 8, comparable con la serie clave) y todas las sucursales ──
_pt = (datos_dia[['id_comercio','id_bandera','id_sucursal','mes','tipo','subtipo','rol','producto','precio_100']]
       .merge(suc_geo[['id_comercio','id_bandera','id_sucursal','suc_key']], on=['id_comercio','id_bandera','id_sucursal'],
              how='inner')
       .groupby(['suc_key','mes','tipo','subtipo','rol','producto'], as_index=False)['precio_100'].median())
_UNI_TPD = {'panel balanceado': _pt.merge(bt_bal[['suc_key','tipo','subtipo']].drop_duplicates(),
                                          on=['suc_key','tipo','subtipo'], how='inner'),
            'todas las sucursales': _pt}
_DESC = {'panel balanceado': (brecha_tipo_mensual_bal, serie_mensual_bal),
         'todas las sucursales': (brecha_tipo_mensual, serie_mensual)}
_tpd = {_u: _tpd_serie(_d, TIPOS_ORD, W_TIPO, MIN_SUC_SUBTIPO) for _u, _d in _UNI_TPD.items()}
del _pt, _UNI_TPD
tpd_ajuste = pd.concat([_r['ajuste'].assign(universo=_u) for _u, _r in _tpd.items()], ignore_index=True)
tpd_subtipos = pd.concat([_r['subtipos'].assign(universo=_u) for _u, _r in _tpd.items()], ignore_index=True)
tpd_productos = pd.concat([_r['productos'].assign(universo=_u) for _u, _r in _tpd.items()], ignore_index=True)
if len(tpd_productos):
    tpd_productos['descripcion'] = tpd_productos['producto'].map(lambda _x: EAN_DESC.get(_x, _x))
_bt = []
for _u, _r in _tpd.items():
    if len(_r['tipos']):
        _bt.append(_r['tipos'].assign(universo=_u).merge(
            _DESC[_u][0][['mes','tipo','brecha_mediana','n_subtipos_imputados']]
            .rename(columns={'brecha_mediana': 'brecha_descriptiva', 'n_subtipos_imputados': 'subtipos_imputados_descriptiva'}),
            on=['mes','tipo'], how='left'))
brecha_tipo_tpd = pd.concat(_bt, ignore_index=True) if _bt else pd.DataFrame(columns=['mes','tipo','universo'])
# serie de la canasta: una fila por mes, TPD y descriptiva de los dos universos
serie_tpd = pd.DataFrame({'mes': sorted(set(serie_mensual['mes']) | set(serie_mensual_bal['mes']))})
for _u, _suf in (('panel balanceado', 'panel'), ('todas las sucursales', 'todas')):
    _c = _tpd[_u]['canasta']
    if len(_c):
        serie_tpd = serie_tpd.merge(_c.drop(columns='tipos_tpd').rename(
            columns={_x: f'{_x}_{_suf}' for _x in _c.columns if _x != 'mes'}), on='mes', how='left')
    _ds = _DESC[_u][1][['mes','brecha_canasta','peso_imputado_pct']].rename(
        columns={'brecha_canasta': f'brecha_canasta_descriptiva_{_suf}', 'peso_imputado_pct': f'peso_imputado_pct_{_suf}'})
    serie_tpd = serie_tpd.merge(_ds, on='mes', how='left')
    if f'brecha_canasta_tpd_{_suf}' in serie_tpd.columns:
        serie_tpd[f'dif_tpd_menos_descriptiva_{_suf}_pp'] = (serie_tpd[f'brecha_canasta_tpd_{_suf}']
                                                            - serie_tpd[f'brecha_canasta_descriptiva_{_suf}'])
# por año: promedio de los meses (TPD y descriptiva por igual)
_cols_a = [_c for _c in serie_tpd.columns if _c.startswith('brecha_canasta_') and 'ic95' not in _c]
tpd_anual = serie_tpd.assign(anio=serie_tpd['mes'].str[:4]).groupby('anio')[_cols_a].mean().reset_index()
if len(brecha_tipo_tpd):
    _ta = (brecha_tipo_tpd[brecha_tipo_tpd['universo'] == 'panel balanceado'].assign(anio=lambda _x: _x['mes'].str[:4])
           .groupby(['anio','tipo'])[['brecha_tpd','brecha_descriptiva']].mean().unstack('tipo'))
    _ta.columns = [f'{_a}_panel_{_b}' for _a, _b in _ta.columns]
    tpd_anual = tpd_anual.merge(_ta.reset_index(), on='anio', how='left')

print('=== Serie TPD (hedónica): robustez frente a la imputación de subtipos (BRECHA_CELIACA §14.12) ===')
if len(tpd_ajuste):
    _aj = tpd_ajuste.groupby('universo').agg(subtipos=('subtipo', 'size'), obs=('obs', 'sum'), celdas=('celdas', 'sum'),
                                             rango_completo=('rango_completo', 'all'))
    print(_aj.to_string())
    if not tpd_ajuste['rango_completo'].all():
        _ri = tpd_ajuste[~tpd_ajuste['rango_completo']]
        print('  ⚠️ subtipos con productos que no se pueden comparar entre sí (nunca conviven en una celda; ¿dos códigos '
              'del mismo producto sin unir en PRODUCTO?): ' + ', '.join(
                  f'[{_r.universo}] {_r.subtipo} ({_r.meses_no_estimables} meses sin nivel estimable)'
                  for _r in _ri.itertuples(index=False)))
    _mv = tpd_subtipos[tpd_subtipos['movido_con_los_demas']]
    if len(_mv):
        print(f'  Subtipo-mes con menos de {MIN_SUC_SUBTIPO} sucursales con los dos lados (movidos con los demás subtipos '
              'del tipo, o con el mes vecino si es el único de su tipo): ' +
              ', '.join(f'[{_u}] {_s} {len(_g)}' for (_u, _s), _g in _mv.groupby(['universo','subtipo'])))
if len(serie_tpd) and 'brecha_canasta_tpd_panel' in serie_tpd.columns:
    print('\nCanasta por año (promedio de los meses): TPD y descriptiva, panel balanceado y todas las sucursales')
    print(tpd_anual[['anio'] + [_c for _c in tpd_anual.columns if _c.startswith('brecha_canasta_')]].round(1)
          .to_string(index=False))
    _dp = serie_tpd['dif_tpd_menos_descriptiva_panel_pp']
    _imp = serie_tpd['peso_imputado_pct_panel'] > 0
    print(f'TPD − descriptiva (canasta, panel): mediana {_dp.median():+.1f} pp; |dif.| mediana {_dp[~_imp].abs().median():.1f} '
          f'pp en los {int((~_imp).sum())} meses sin subtipos imputados y {_dp[_imp].abs().median():.1f} pp en los '
          f'{int(_imp.sum())} con alguno. Desvío de la variación mensual: TPD '
          f'{serie_tpd["brecha_canasta_tpd_panel"].diff().std():.1f} pp, descriptiva '
          f'{serie_tpd["brecha_canasta_descriptiva_panel"].diff().std():.1f} pp')
    print(f'Meses con algún subtipo sin dato propio (panel): TPD {int((serie_tpd["peso_movido_pct_panel"] > 0).sum())} '
          f'(movido con los demás), descriptiva {int(_imp.sum())} (arrastrado)')
    _ult = serie_tpd.dropna(subset=['brecha_canasta_tpd_panel']).iloc[-1]
    print(f'Último mes ({_ult["mes"]}), panel: TPD {_ult["brecha_canasta_tpd_panel"]:+.1f}% (IC 95% '
          f'{_ult["brecha_canasta_tpd_ic95_inf_panel"]:+.1f}% a {_ult["brecha_canasta_tpd_ic95_sup_panel"]:+.1f}%) · '
          f'descriptiva {_ult["brecha_canasta_descriptiva_panel"]:+.1f}%')
if len(brecha_tipo_tpd):
    _tt = (brecha_tipo_tpd[brecha_tipo_tpd['universo'] == 'panel balanceado'].assign(anio=lambda _x: _x['mes'].str[:4])
           .groupby(['tipo','anio'])[['brecha_tpd','brecha_descriptiva']].mean().unstack('anio').round(1))
    print('\nPor tipo y año, panel balanceado (promedio de los meses): TPD / descriptiva')
    print(_tt.to_string())"""))

# ── CELL 9 — GRÁFICOS ──────────────────────────────────────────────────────────
cells.append(cell_code(r"""# ============================================================
# CELDA 9 — Gráficos de la brecha
# ============================================================
MES = f'{ULTIMO_MES[5:7]}{ULTIMO_MES[:4]}'
_C_MED, _C_BAL = '#0055A4', '#2ca02c'

def _guardar(_nombre):
    plt.tight_layout(); _o = OUTPUT_DIR / f'{_nombre}_{MES}.png'
    plt.savefig(_o, dpi=200, bbox_inches='tight', facecolor='white'); plt.show()
    print(f'Guardado: {_o.name}')

# 1) Canasta mensual: todas las sucursales vs panel balanceado (+ sucursales del tipo con menos cobertura). Marcador
#    vacío: mes con algún subtipo imputado con su último mes válido (hoja Imputaciones)
if len(serie_mensual):
    fig, ax = plt.subplots(figsize=(13, 6))
    _sm = serie_mensual.assign(f=pd.to_datetime(serie_mensual['mes'] + '-01'))
    ax.plot(_sm['f'], _sm['brecha_canasta'], color=_C_MED, lw=2.2, marker='o', ms=3, label='Todas las sucursales')
    _im = _sm['peso_imputado_pct'] > 0
    ax.plot(_sm.loc[_im, 'f'], _sm.loc[_im, 'brecha_canasta'], ls='none', marker='o', ms=6, mfc='white', mec=_C_MED)
    if len(serie_mensual_bal):
        _sb = serie_mensual_bal.assign(f=pd.to_datetime(serie_mensual_bal['mes'] + '-01'))
        ax.plot(_sb['f'], _sb['brecha_canasta'], color=_C_BAL, lw=2.2, marker='D', ms=3, label='Panel balanceado')
        _im = _sb['peso_imputado_pct'] > 0
        ax.plot(_sb.loc[_im, 'f'], _sb.loc[_im, 'brecha_canasta'], ls='none', marker='D', ms=6, mfc='white', mec=_C_BAL)
    ax.plot([], [], ls='none', marker='o', ms=6, mfc='white', mec='#555',
            label='mes con algún subtipo imputado (último mes válido)')
    ax.set_ylabel('Brecha de la canasta (%)')
    ax.set_title('Brecha celíaca de la canasta (ponderada ENGHo) — canasta fija 2022-2026')
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x:+.0f}%')); ax.grid(True, alpha=0.3)
    _a2 = ax.twinx()
    _a2.bar(_sm['f'], _sm['n_min'], width=20, color='#cccccc', alpha=0.35, label='sucursales del tipo con menos (der.)')
    _a2.set_ylim(0, max(1, _sm['n_min'].max()) * 3); _a2.set_ylabel('sucursales', color='#999')
    _l1, _b1 = ax.get_legend_handles_labels(); _l2, _b2 = _a2.get_legend_handles_labels()
    ax.legend(_l1 + _l2, _b1 + _b2, loc='upper left', fontsize=9)
    _guardar('brecha_mensual')

# 2) Brecha mensual por tipo (panel balanceado)
if len(brecha_tipo_mensual_bal):
    fig, ax = plt.subplots(figsize=(13, 6))
    for _t, _g in brecha_tipo_mensual_bal.groupby('tipo'):
        _g = _g.sort_values('mes')
        _f = pd.to_datetime(_g['mes'] + '-01')
        _ln = ax.plot(_f, _g['brecha_mediana'], marker='o', ms=3, lw=1.8, label=_t)[0]
        _im = (_g['n_subtipos_imputados'] > 0).to_numpy()
        ax.plot(_f[_im], _g['brecha_mediana'][_im], ls='none', marker='o', ms=6, mfc='white', mec=_ln.get_color(),
                color=_ln.get_color())   # con color explícito no consume un color del ciclo
    ax.plot([], [], ls='none', marker='o', ms=6, mfc='white', mec='#555', label='con algún subtipo imputado')
    ax.set_ylabel('Brecha (%)'); ax.set_title('Brecha mensual por tipo — panel balanceado')
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x:+.0f}%'))
    ax.legend(fontsize=8, ncol=2); ax.grid(True, alpha=0.3)
    _guardar('brecha_tipo_mensual')

# 3) Brecha por tipo (todo el período)
if len(brecha_tipo):
    _bt = brecha_tipo.sort_values('brecha_mediana')
    fig, ax = plt.subplots(figsize=(11, max(4, len(_bt) * 0.7 + 2)))
    ax.barh(_bt['tipo'], _bt['brecha_mediana'], color=plt.cm.RdYlGn_r(np.linspace(0.2, 0.9, len(_bt))),
            edgecolor='black', lw=0.4)
    for _i, (_, _r) in enumerate(_bt.iterrows()):
        ax.text(_r['brecha_mediana'], _i, f'  {_r["brecha_mediana"]:+.0f}%  ({int(_r["n_sucursales"])} sucursales)',
                va='center', fontsize=8)
    ax.set_xlabel('Brecha mediana (%) — sin TACC vs con TACC, $/100 g'); ax.set_title('Brecha celíaca por tipo (2022 → hoy)')
    ax.grid(True, alpha=0.3, axis='x')
    _guardar('brecha_por_tipo')

# 4) Canasta por año y región (todas las sucursales; misma canasta en todas las regiones). Marcador vacío: no confiable
if len(brecha_region_anual):
    fig, ax = plt.subplots(figsize=(11, 6))
    for _rg, _g in brecha_region_anual.groupby('region'):
        _g = _g.sort_values('anio')
        _ln = ax.plot(_g['anio'], _g['brecha_canasta'], marker='o', lw=2, label=_rg)[0]
        _nc = ~_g['confiable'].astype(bool)
        ax.plot(_g.loc[_nc, 'anio'], _g.loc[_nc, 'brecha_canasta'], ls='none', marker='o', ms=8, mfc='white',
                mec=_ln.get_color(), color=_ln.get_color())
    ax.set_ylabel('Brecha de la canasta (%)')
    ax.set_title(f'Brecha celíaca de la canasta por región y año (marcador vacío: > {MAX_PESO_IMPUTADO}% del peso con la '
                 f'brecha nacional o < {MIN_SUC_AGG} sucursales)', fontsize=10)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x:+.0f}%'))
    ax.legend(fontsize=9); ax.grid(True, alpha=0.3)
    _guardar('brecha_region_anual')

# 5), 6) y 7) Provincia, empresa y cadena (últimos meses; solo confiables: misma canasta de subtipos en todos los grupos)
for _df, _col, _tit, _nom in ((brecha_prov, 'provincia', 'provincia', 'brecha_provincia'),
                              (brecha_empresa, 'empresa', 'empresa', 'brecha_empresa'),
                              (brecha_cadena, 'cadena', 'cadena', 'brecha_cadena')):
    _d = _df[_df['confiable']] if len(_df) else _df
    if not len(_d):
        continue
    fig, ax = plt.subplots(figsize=(11, max(4, len(_d) * 0.38 + 2)))
    ax.barh(_d[_col], _d['brecha_canasta'], color=plt.cm.RdYlGn_r(np.linspace(0.15, 0.9, len(_d))),
            edgecolor='black', lw=0.4)
    for _i, (_, _r) in enumerate(_d.iterrows()):
        ax.text(_r['brecha_canasta'], _i, f' {_r["brecha_canasta"]:+.1f}% ({int(_r["n_sucursales"])} sucursales; '
                f'{_r["peso_imputado_pct"]:.0f}% del peso con la brecha nacional)', va='center', fontsize=8)
    ax.set_xlabel('Brecha de la canasta (%)')
    ax.set_title(f'Brecha celíaca por {_tit} — {VENTANA_TXT}\n(misma canasta en todos; subtipos sin datos = brecha '
                 f'nacional, <= {MAX_PESO_IMPUTADO}% del peso; >= {MIN_SUC_AGG} sucursales)', fontsize=11)
    ax.grid(True, alpha=0.3, axis='x')
    _guardar(_nom)

# 8) Brecha vs concentración del mercado local: HHI de empresas por departamento (cuota = sucursales)
_cc = concentracion[concentracion['confiable']] if len(concentracion) else concentracion
if len(_cc) >= 3:
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(_cc['hhi'], _cc['brecha_mediana'], s=12 + 3 * _cc['sucursales_con_brecha'].clip(upper=150), alpha=0.6,
               color=_C_MED, edgecolor='white')
    ax.set_xlabel('HHI de empresas en el departamento (cuota = sucursales; 1 = una sola empresa)')
    ax.set_ylabel('Brecha de la canasta (mediana de sus sucursales, %)')
    ax.set_title(f'Brecha vs concentración del mercado local — {VENTANA_TXT}\nDepartamentos con >= {MIN_SUC_DEPTO} '
                 f'sucursales con brecha propia (tamaño = sucursales) · Spearman por sucursal {CONC_RHO:+.2f} '
                 f'(n = {CONC_N:,})', fontsize=11)
    ax.grid(True, alpha=0.3)
    _guardar('brecha_concentracion')

# 9) Serie TPD (hedónica, CELDA 8b) contra la descriptiva: canasta, panel balanceado y todas las sucursales
_C_TPD = '#d62728'
if len(serie_tpd) and 'brecha_canasta_tpd_panel' in serie_tpd.columns:
    fig, axs = plt.subplots(2, 1, figsize=(13, 10), sharex=True)
    _st = serie_tpd.assign(f=pd.to_datetime(serie_tpd['mes'] + '-01'))
    for _ax, _suf, _col, _tit in ((axs[0], 'panel', _C_BAL, 'Panel balanceado (la serie clave)'),
                                  (axs[1], 'todas', _C_MED, 'Todas las sucursales')):
        if f'brecha_canasta_tpd_{_suf}' not in _st.columns:
            continue
        _ax.fill_between(_st['f'], _st[f'brecha_canasta_tpd_ic95_inf_{_suf}'], _st[f'brecha_canasta_tpd_ic95_sup_{_suf}'],
                         color=_C_TPD, alpha=0.15, lw=0, label='TPD: IC 95% (errores agrupados por sucursal)')
        _ax.plot(_st['f'], _st[f'brecha_canasta_tpd_{_suf}'], color=_C_TPD, lw=2.4,
                 label='TPD (hedónica): canasta fija de productos')
        _mv = _st[f'peso_movido_pct_{_suf}'] > 0
        _ax.plot(_st.loc[_mv, 'f'], _st.loc[_mv, f'brecha_canasta_tpd_{_suf}'], ls='none', marker='o', ms=6,
                 mfc='white', mec=_C_TPD, color=_C_TPD,
                 label=f'TPD: mes con algún subtipo movido con los demás (< {MIN_SUC_SUBTIPO} sucursales)')
        _ax.plot(_st['f'], _st[f'brecha_canasta_descriptiva_{_suf}'], color=_col, lw=1.6, marker='D', ms=3,
                 label='Descriptiva')
        _im = _st[f'peso_imputado_pct_{_suf}'] > 0
        _ax.plot(_st.loc[_im, 'f'], _st.loc[_im, f'brecha_canasta_descriptiva_{_suf}'], ls='none', marker='D', ms=6,
                 mfc='white', mec=_col, color=_col, label='descriptiva: mes con algún subtipo imputado')
        _ax.set_title(_tit, fontsize=11, loc='left'); _ax.set_ylabel('Brecha de la canasta (%)')
        _ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x:+.0f}%'))
        _ax.legend(loc='upper left', fontsize=8); _ax.grid(True, alpha=0.3)
    fig.suptitle('Brecha celíaca de la canasta: serie TPD (hedónica) y serie descriptiva', y=1.0)
    _guardar('brecha_tpd')

# 10) Serie TPD por tipo contra la descriptiva (panel balanceado)
_btp = brecha_tipo_tpd[brecha_tipo_tpd['universo'] == 'panel balanceado'] if len(brecha_tipo_tpd) else brecha_tipo_tpd
if len(_btp):
    _tps = [_t for _t in TIPOS_ORD if _t in set(_btp['tipo'])]
    fig, axs = plt.subplots(len(_tps), 1, figsize=(13, 2.9 * len(_tps)), sharex=True)
    axs = np.atleast_1d(axs)
    for _ax, _tp in zip(axs, _tps):
        _x = _btp[_btp['tipo'] == _tp].sort_values('mes')
        _f = pd.to_datetime(_x['mes'] + '-01')
        _ax.fill_between(_f, _x['brecha_tpd_ic95_inf'], _x['brecha_tpd_ic95_sup'], color=_C_TPD, alpha=0.15, lw=0)
        _ax.plot(_f, _x['brecha_tpd'], color=_C_TPD, lw=2, label='TPD (IC 95%)')
        _mv = (_x['subtipos_movidos'] > 0).to_numpy()
        _ax.plot(_f[_mv], _x['brecha_tpd'][_mv], ls='none', marker='o', ms=5, mfc='white', mec=_C_TPD, color=_C_TPD,
                 label='TPD: subtipo movido')
        _ax.plot(_f, _x['brecha_descriptiva'], color=_C_BAL, lw=1.3, marker='o', ms=2.5, label='Descriptiva')
        _im = (_x['subtipos_imputados_descriptiva'] > 0).to_numpy()
        _ax.plot(_f[_im], _x['brecha_descriptiva'][_im], ls='none', marker='o', ms=5, mfc='white', mec=_C_BAL,
                 color=_C_BAL, label='descriptiva: subtipo imputado')
        _ax.set_title(_tp, fontsize=10, loc='left')
        _ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x:+.0f}%')); _ax.grid(True, alpha=0.3)
    axs[0].legend(loc='upper right', fontsize=8, ncol=4)
    fig.suptitle('Brecha por tipo, panel balanceado: serie TPD (hedónica) y descriptiva', y=1.0)
    _guardar('brecha_tpd_tipos')"""))

# ── CELL 10 — MAPA COROPLÉTICO ─────────────────────────────────────────────────
cells.append(cell_code("""\
# ============================================================
# CELDA 10 — Mapa coroplético de la brecha de la canasta por provincia (últimos meses)
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

    # Solo se colorean las provincias confiables (misma canasta: <= MAX_PESO_IMPUTADO% del peso con la brecha nacional y
    # >= MIN_SUC_AGG sucursales); las demás quedan en gris con su nombre (sus números están en la hoja Brecha_provincia)
    _pv = brecha_prov[brecha_prov['confiable']] if len(brecha_prov) else brecha_prov
    _prov_val = dict(zip(_pv['provincia'], _pv['brecha_canasta']))
    _con_datos = set(brecha_prov['provincia']) if len(brecha_prov) else set()
    _vals = list(_prov_val.values())
    if _vals:
        norm_c = Normalize(vmin=min(_vals), vmax=max(_vals) if max(_vals) > min(_vals) else min(_vals) + 1)
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
            if val is not None or nom in _con_datos:
                _tx = f'{nom}\\n{val:+.1f}%' if val is not None else f'{nom}\\n(pocos datos)'
                ax.text(cx+dx, cy+dy, _tx, ha='center', va='center', fontsize=7.5,
                        fontweight='bold' if val is not None else 'normal', color='black' if val is not None else '#666',
                        bbox=dict(boxstyle='round,pad=0.25', facecolor='white', alpha=0.75, edgecolor='none'))
        if caba_c and 'CABA' in _prov_val:
            vc = _prov_val['CABA']; cc = cmap_m(norm_c(vc)); lx,ly = caba_c[0]+2.2, caba_c[1]+0.8
            ax.annotate('', xy=caba_c, xytext=(lx,ly), arrowprops=dict(arrowstyle='-', color='black', linewidth=1.0))
            ax.text(lx, ly, f'CABA\\n{vc:+.1f}%', ha='center', va='center', fontsize=9, fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.5', facecolor=cc, alpha=0.95, edgecolor='black', linewidth=1.0))
            ax.plot(*caba_c, marker='o', markersize=10, markerfacecolor=cc, markeredgecolor='black', markeredgewidth=1.2, zorder=5)
        ax.set_title(f'Brecha celíaca de la canasta por provincia — {VENTANA_TXT}\\n(misma canasta en todas; gris: < {MIN_SUC_AGG} '
                     f'sucursales o > {MAX_PESO_IMPUTADO}% del peso sin datos propios)', fontsize=13, fontweight='bold', pad=6)
        ax.set_aspect('equal'); ax.axis('off'); plt.tight_layout()
        _o = OUTPUT_DIR / f'mapa_brecha_{MES}.png'
        plt.savefig(_o, dpi=300, bbox_inches='tight', facecolor='white'); plt.show()
        print(f'Guardado: {_o.name}')"""))

# ── CELL 11 — EXCEL ────────────────────────────────────────────────────────────
cells.append(cell_code(r"""# ============================================================
# CELDA 11 — Exportación Excel
# ============================================================
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
HDR_FILL = PatternFill(start_color='1F4E79', end_color='1F4E79', fill_type='solid')
HDR_FONT = Font(bold=True, color='FFFFFF', size=10)
HDR_ALIG = Alignment(horizontal='center', wrap_text=True, vertical='center')
def fmt_ws(ws):
    ws.row_dimensions[1].height = 30; ws.freeze_panes = 'A2'
    for cell in ws[1]: cell.fill = HDR_FILL; cell.font = HDR_FONT; cell.alignment = HDR_ALIG
def auto_widths(ws):
    for ci in range(1, ws.max_column+1):
        cl = get_column_letter(ci); hdr = str(ws.cell(1,ci).value or '').lower()
        ws.column_dimensions[cl].width = 34 if any(x in hdr for x in ('provincia','cadena','empresa','localidad','tipo',
                                                                      'desc','producto','sucursal','nombre','region')) else 14
        if any(x in hdr for x in ('brecha','base','celiaca','precio','100','tacc','grams','gramos','peso','relativo')):
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=ci, max_col=ci):
                for cell in row:
                    cell.number_format = ('+0.0"%"' if 'brecha' in hdr else '#,##0.00')

# ── Canasta (lo que entró) ────────────────────────────────────────────────────
_obs = datos_dia.groupby('ean_norm').agg(meses_con_precio=('mes','nunique'), primer_mes=('mes','min'),
                                         ultimo_mes=('mes','max'), obs_sucursal_mes=('mes','size'))
canasta = pd.DataFrame({'ean': sorted(EANS_CONFIG)})
canasta['tipo'] = canasta['ean'].map(EAN_TIPO)
canasta['lado'] = canasta['ean'].map(EAN_ROL).map({'tacc': 'con TACC', 'sin': 'sin TACC'})
canasta['descripcion'] = canasta['ean'].map(EAN_DESC)
canasta['producto'] = canasta['ean'].map(_PROD).fillna(canasta['descripcion'])
canasta['gramos'] = canasta['ean'].map(EAN_GRAMS)
canasta['subtipo'] = canasta['ean'].map(EAN_SUBTIPO)
_VIGX = {_norm_ean(k): v for k, v in globals().get('VIGENCIA', {}).items() if _norm_ean(k)}
canasta['vigente_desde'] = canasta['ean'].map(lambda _e: _VIGX.get(_e, (None, None))[0])
canasta['vigente_hasta'] = canasta['ean'].map(lambda _e: _VIGX.get(_e, (None, None))[1])
canasta = canasta.join(_obs, on='ean')
canasta['excluido_plausibilidad'] = canasta['ean'].isin(_bad)
canasta = canasta.sort_values(['tipo','lado','descripcion'])

# ── Detalle intra-sucursal por producto (último mes) ─────────────────────────
_ult = datos_dia[datos_dia['mes'] == ULTIMO_MES]
_det = _ult[['id_comercio','id_bandera','id_sucursal','ean_norm','tipo','rol','precio','dias','grams','precio_100']].copy()
_det['descripcion'] = _det['ean_norm'].map(EAN_DESC)
_det = _det.merge(suc_geo[['id_comercio','id_bandera','id_sucursal','cadena','empresa','PROVINCIA_NORM','region',
                           'sucursales_localidad','sucursales_nombre']],
                  on=['id_comercio','id_bandera','id_sucursal'], how='left')
_det = _det.rename(columns={'precio':'precio_mediano_mes','precio_100':'precio_100g'})
_det = _det[['cadena','empresa','PROVINCIA_NORM','region','sucursales_localidad','sucursales_nombre','id_comercio',
             'id_bandera','id_sucursal','tipo','rol','ean_norm','descripcion','grams','precio_mediano_mes','dias',
             'precio_100g']].sort_values(['PROVINCIA_NORM','cadena','sucursales_nombre','tipo','rol'])

# ── Brecha por SUCURSAL — último mes: canasta comparable (misma canasta de subtipos en todas; lo que la sucursal no
# tiene, con la brecha nacional del mes) y, de referencia, la canasta por cantidades de los tipos que tiene ──
_bsm = brecha_suc_mes[brecha_suc_mes['mes'] == ULTIMO_MES].copy()
_brecha_suc = (_bsm.merge(suc_geo[['id_comercio','id_bandera','id_sucursal','sucursales_nombre','departamento']],
                          on=['id_comercio','id_bandera','id_sucursal'], how='left')
               .rename(columns={'base':'canasta_con_tacc','celiaca':'canasta_sin_tacc',
                                'brecha_pct':'brecha_tipos_presentes','brecha_comparable':'brecha_canasta'})
               .sort_values('brecha_canasta', ascending=False)) if len(_bsm) else pd.DataFrame()
if len(_brecha_suc):
    _c1 = ['id_comercio','id_bandera','id_sucursal','mes','PROVINCIA_NORM','region','departamento','cadena','empresa',
           'localidad','sucursales_nombre','brecha_canasta','peso_propio_pct','n_tipos','brecha_tipos_presentes',
           'canasta_con_tacc','canasta_sin_tacc','suc_key']
    _brecha_suc = _brecha_suc[[c for c in _c1 if c in _brecha_suc.columns]]

# ── Comparación de productos EQUIVALENTES por sucursal (último mes) ───────────
_cu = _ult.copy()
_cu['subtipo'] = _cu['ean_norm'].map(EAN_SUBTIPO)
_cu['descripcion'] = _cu['ean_norm'].map(EAN_DESC)
def _items_lado(_g):
    _g = _g.sort_values('precio_100')
    return '; '.join(f'{_t.descripcion} ({int(_t.grams)}g, ${_t.precio_100:,.0f}/100g)' for _t in _g.itertuples(index=False))
_rows_c = []
for _kk, _g in _cu.groupby(['id_comercio','id_bandera','id_sucursal','tipo','subtipo','rol']):
    _rows_c.append((*_kk, _items_lado(_g), float(_g['precio_100'].median()), int(_g['ean_norm'].nunique())))
_cg = pd.DataFrame(_rows_c, columns=['id_comercio','id_bandera','id_sucursal','tipo','subtipo','rol','productos',
                                     'precio_100g_med','n'])
if len(_cg):
    _tc = _cg[_cg['rol']=='tacc'].drop(columns='rol').rename(columns={'productos':'productos_tacc','precio_100g_med':'precio_tacc_100g','n':'n_tacc'})
    _sc = _cg[_cg['rol']=='sin'].drop(columns='rol').rename(columns={'productos':'productos_sin','precio_100g_med':'precio_sin_100g','n':'n_sin'})
    _comp = _tc.merge(_sc, on=['id_comercio','id_bandera','id_sucursal','tipo','subtipo'], how='outer')
    _comp['n_tacc'] = _comp['n_tacc'].fillna(0).astype(int); _comp['n_sin'] = _comp['n_sin'].fillna(0).astype(int)
    _comp['equivalencia'] = np.where((_comp['n_tacc']>0) & (_comp['n_sin']>0), 'ambos',
                              np.where(_comp['n_tacc']>0, 'solo con TACC', 'solo sin TACC'))
    _comp['brecha_subtipo_pct'] = (_comp['precio_sin_100g'] / _comp['precio_tacc_100g'] - 1) * 100
    _comp = _comp.merge(suc_geo[['id_comercio','id_bandera','id_sucursal','cadena','PROVINCIA_NORM','sucursales_localidad',
                                 'sucursales_nombre']], on=['id_comercio','id_bandera','id_sucursal'], how='left')
    _comp = _comp[['cadena','PROVINCIA_NORM','sucursales_localidad','sucursales_nombre','id_comercio','id_bandera',
                   'id_sucursal','tipo','subtipo','equivalencia','n_tacc','productos_tacc','precio_tacc_100g','n_sin',
                   'productos_sin','precio_sin_100g','brecha_subtipo_pct']].sort_values(
                       ['PROVINCIA_NORM','cadena','sucursales_nombre','tipo','subtipo'])
else:
    _comp = pd.DataFrame()

leeme = pd.DataFrame({'hoja_o_columna': [
    'Método', 'Canasta', 'Ponderaciones', 'Brecha_subtipo*', 'Brecha_tipo*', 'Serie_canasta*',
    'Brecha_provincia / region / empresa / cadena', '*_anual', 'brecha_canasta', 'n_min / confiable', 'Panel balanceado',
    'peso_imputado_pct', 'Imputaciones', 'Serie_TPD / Brecha_tipo_TPD', 'TPD_subtipos', 'TPD_anual', 'TPD_productos',
    'Brecha_sucursal', 'Concentracion', 'Control_EAN', 'Plausibilidad', 'Fuente'],
    'definicion': [
    'Brecha de un subtipo en una sucursal y mes = mediana $/100 g de los productos sin TACC presentes / mediana $/100 g de '
    'los con TACC presentes - 1 (los dos lados en el mismo super). Brecha del tipo = promedio geométrico de las de sus '
    'subtipos con los dos lados (pesos iguales). Precio de un producto en el mes = mediana de sus precios diarios.',
    'Productos de la canasta fija (CELDA 1), con los meses en que tuvieron precio. Un producto que cambió de código '
    'ocupa una fila por código (misma columna producto; vigente_desde / vigente_hasta: meses en que se usa cada código). '
    'Lista con métricas: docs/brecha_celiaca/canasta_fija_2022_2026.csv; reglas: docs/BRECHA_CELIACA.md §14.',
    'Peso de cada tipo: % del gasto de los hogares en alimentos y bebidas no alcohólicas que va a sus artículos (ENGHo '
    '2017/18), renormalizado entre los tipos de la canasta; cantidades de la canasta por sucursal (peso / precio con '
    'TACC del año base).',
    'Por subtipo (crackers, snacks, spaghetti, rellenas...): mediana entre sucursal-mes de la brecha del subtipo, '
    'precios medianos $/100 g de cada lado y sucursales; todo el período y por año. Es la comparación de base.',
    'Por tipo: promedio geométrico (pesos iguales) de las brechas medianas de sus subtipos presentes en el grupo '
    '(brecha_mediana; ídem con el promedio sin outliers, brecha_prom, y el "más barato" ilustrativo, sesgado al alza), '
    'precios $/100 g de cada lado (promedio geométrico de los de sus subtipos), subtipos y sucursales.',
    'Canasta por mes (y año): sum_k w_k (1 + brecha del tipo k) - 1, con los pesos ENGHo.',
    f'Últimos {VENTANA_GEO_MESES} meses ({VENTANA_TXT}). Misma canasta en todos los grupos: el subtipo con menos de '
    f'{MIN_SUC_SUBTIPO} sucursales en el grupo toma la brecha nacional del período (subtipos_con_brecha_nacional), así '
    'un grupo sin snacks o sin obleas no cambia de composición. Una columna por tipo con su brecha y sus sucursales.',
    'Mismo cálculo por año (todas las sucursales del año; lo que falta en el grupo, con la brecha nacional de ese año).',
    'Brecha de la canasta del grupo o mes: sum_k w_k (1 + brecha del tipo k) - 1 (pesos ENGHo).',
    f'Series: n_min = sucursales del tipo con menos sucursales; confiable = están todos los tipos y n_min >= {MIN_SUC_AGG}. '
    f'Grupos: confiable = peso_imputado_pct <= {MAX_PESO_IMPUTADO} y n_sucursales >= {MIN_SUC_AGG}.',
    f'Solo sucursal x subtipo con los dos lados en >= {int(FRAC_MESES_PANEL * 100)}% de los meses: la serie no cambia '
    'por sucursales que entran o salen.',
    'Parte del peso de la canasta que no se midió: en la serie mensual, subtipos imputados con su último mes válido '
    '(pocas sucursales ese mes); en los grupos, subtipos con la brecha nacional del período.',
    'Rachas de meses en que un subtipo se imputa con su último mes válido en la serie mensual (todas las sucursales y '
    'panel balanceado): desde, hasta, sucursales que tenía y brecha arrastrada. Más de 3 meses: leer ese tramo con cuidado.',
    'Serie TPD (hedónica, CELDA 8b), robustez de la serie mensual: por subtipo, ln p = efecto de la celda (sucursal-mes '
    'del subtipo) + efecto de producto + prima sin TACC del mes (mínimos cuadrados; cada producto pesa 1 / productos de su '
    'lado en la celda). Brecha del subtipo = exp(nivel + prima del mes) - 1, con nivel = promedio de los efectos de los sin '
    'TACC - promedio de los con TACC (cada producto pesado por su disponibilidad en todo el período); tipo = promedio '
    'geométrico de sus subtipos; canasta con los pesos ENGHo. Canasta fija de productos; usa los subtipo-mes que la '
    'descriptiva imputa (menos de la mitad de sus sucursales) y solo con menos de '
    f'{MIN_SUC_SUBTIPO} sucursales con los dos lados mueve el subtipo con los demás de su tipo (subtipos_movidos; el '
    'único subtipo de su tipo queda con el mes vecino; peso_movido_pct = parte del peso de la canasta en subtipos '
    'movidos, como peso_imputado_pct en la descriptiva). Dos universos: las celdas del panel balanceado y todas las '
    'sucursales, cada uno al lado de su descriptiva (y de cuánto se imputó en ella). IC 95% con errores agrupados por '
    'sucursal y la covarianza entre subtipos y tipos (en un mes movido, sin la incertidumbre de la imputación).',
    'Brecha TPD de cada subtipo por mes y universo, sucursales con los dos lados y si se movió con los demás subtipos '
    f'(menos de {MIN_SUC_SUBTIPO} sucursales).',
    'Promedio de los meses de cada año de la serie TPD y de la descriptiva: canasta (los dos universos) y tipos (panel).',
    'Por universo y subtipo: efecto estimado de cada producto (gamma, log), su peso en el nivel (disponibilidad) y su nivel '
    'contra el promedio ponderado de los con TACC del subtipo; en los sin TACC es la prima del producto en el mes base. '
    'referencia = producto fijado en 0.',
    'Último mes: brecha_canasta = canasta comparable (misma canasta de subtipos en todas las sucursales; lo que la '
    'sucursal no tiene con los dos lados, con la brecha nacional del mes; peso_propio_pct = parte medida en la sucursal). '
    'brecha_tipos_presentes = canasta por cantidades solo con los tipos que tiene (depende de cuántos tiene: no comparar).',
    'Por departamento (Georef): sucursales del universo, empresas, HHI de empresas (cuota = sucursales; el SEPA no tiene '
    'ventas), empresa principal, sucursales con brecha propia (>= 50% del peso medido en ellas) y su brecha mediana '
    f'(canasta comparable, últimos {VENTANA_GEO_MESES} meses). confiable = >= {MIN_SUC_DEPTO} sucursales con brecha.',
    'Precio de cada EAN relativo a la mediana del lado con TACC de su tipo, mes a mes; revisar = cambio de nivel x2 o '
    'salto x2 mes a mes (código reutilizado, presentación mal cargada). No excluye.',
    f'EANs excluidos por precio relativo a sus pares fuera de [1/{FACTOR_PLAUS}, {FACTOR_PLAUS}].',
    'SEPA (zips semestrales del Drive). Desde ago-2026 los meses salen del SEPA diario (script 03), sin 8 comercios.']})

out_xls = OUTPUT_DIR / f'brecha_celiaca_{ULTIMO_MES}.xlsx'
_hojas = [
    ('Leeme', leeme), ('Canasta', canasta), ('Ponderaciones', ponderaciones), ('Cobertura', cobertura_tipo),
    ('Cobertura_mensual', cobertura_mensual), ('Brecha_subtipo', brecha_subtipo),
    ('Brecha_subtipo_anual', brecha_subtipo_anual), ('Brecha_subtipo_anual_balanc', brecha_subtipo_anual_bal),
    ('Brecha_tipo', brecha_tipo), ('Brecha_tipo_mes', brecha_tipo_mensual),
    ('Brecha_tipo_mes_balanceado', brecha_tipo_mensual_bal), ('Brecha_tipo_anual', brecha_tipo_anual),
    ('Brecha_tipo_anual_balanceado', brecha_tipo_anual_bal), ('Serie_canasta', serie_mensual),
    ('Serie_canasta_balanceada', serie_mensual_bal), ('Canasta_anual', serie_anual),
    ('Canasta_anual_balanceada', serie_anual_bal), ('Serie_TPD', serie_tpd), ('Brecha_tipo_TPD', brecha_tipo_tpd),
    ('TPD_subtipos', tpd_subtipos), ('TPD_anual', tpd_anual), ('TPD_productos', tpd_productos),
    ('Brecha_provincia', brecha_prov),
    ('Brecha_tipo_provincia', brecha_tipo_prov), ('Brecha_region', brecha_region),
    ('Brecha_tipo_region', brecha_tipo_region), ('Brecha_region_anual', brecha_region_anual),
    ('Brecha_empresa', brecha_empresa), ('Brecha_tipo_empresa', brecha_tipo_empresa),
    ('Brecha_empresa_anual', brecha_empresa_anual), ('Brecha_cadena', brecha_cadena), ('Concentracion', concentracion),
    ('Brecha_sucursal', _brecha_suc), ('Comparacion_productos', _comp), ('Detalle_producto', _det),
    ('Imputaciones', imputaciones), ('Control_EAN', control_ean), ('Plausibilidad', plausibilidad)]
with pd.ExcelWriter(out_xls, engine='openpyxl') as writer:
    for _sn, _df in _hojas:
        (_df if len(_df.columns) else pd.DataFrame({'(sin datos)': []})).to_excel(writer, sheet_name=_sn, index=False)
    for sn in writer.sheets:
        ws = writer.sheets[sn]; fmt_ws(ws); auto_widths(ws)
    writer.sheets['Leeme'].column_dimensions['B'].width = 140
print(f'Excel guardado: {out_xls}')
print(f'  {len(_hojas)} hojas · Detalle_producto {len(_det):,} filas · Comparacion_productos {len(_comp):,} · '
      f'Brecha_sucursal {len(_brecha_suc):,}')
print('  El número clave: Brecha_tipo (por tipo) y Serie_canasta_balanceada / Canasta_anual_balanceada (evolución).')"""))

# ── CELL 12 — MAPA FOLIUM POR SUCURSAL (lazy-load) ─────────────────────────────
cells.append(cell_code("""\
# ============================================================
# CELDA 12 — Mapa Folium interactivo POR SUCURSAL (brecha celíaca, último dato de cada sucursal)
# ============================================================
# Un punto por supermercado; color VERDE→ROJO graduado por la brecha de la canasta COMPARABLE de esa sucursal (misma
# canasta de subtipos en todas; lo que la sucursal no tiene con los dos lados, con la brecha nacional del mes: si no, el
# color dependía de cuántos tipos tiene cada sucursal). LIVIANO: los popups se arman al hacer clic (lazy-load desde un
# JSON compacto). Popup: (1) brecha comparable, parte del peso medida en la sucursal y valor de cada canasta; (2)
# productos por EQUIVALENCIA (subtipo) — con TACC vs sin TACC, con presentación y $/100g; (3) cadena +
# localidad/provincia. La brecha AUTORITATIVA es la del tipo (§3). Filtro por cadena (LayerControl) + pantalla
# completa. Mosaicos: Esri World Light Gray (sin API key y responde desde la red del INECO, BUG-32) + límites
# provinciales dibujados desde el ar.json local (se ven aunque la red bloquee los mosaicos).
import folium
from folium.plugins import Fullscreen
from branca.colormap import LinearColormap
import json as _json

# Snapshot = ÚLTIMA brecha disponible POR SUCURSAL dentro de una ventana de meses (cadenas que no informaron el
# último mes aparecen con su dato más reciente; el popup indica de qué mes es).
_sk3m = ['id_comercio','id_bandera','id_sucursal']
VENTANA_MAPA_MESES = 6
_meses_ord = sorted(brecha_suc_mes['mes'].unique())
_meses_win = set(_meses_ord[-VENTANA_MAPA_MESES:]) if _meses_ord else set()
_bsm_w = brecha_suc_mes[brecha_suc_mes['mes'].isin(_meses_win) & brecha_suc_mes['brecha_comparable'].notna()]
_bk = (_bsm_w.sort_values('mes').groupby(_sk3m, as_index=False).tail(1)
       .merge(suc_geo[['id_comercio','id_bandera','id_sucursal','sucursales_nombre',
                       'sucursales_latitud','sucursales_longitud']],
              on=_sk3m, how='left')
       .dropna(subset=['sucursales_latitud','sucursales_longitud']))
_um = _meses_ord[-1] if _meses_ord else ULTIMO_MES
_sel_mes = _bk[_sk3m + ['mes']]

_btm = bt_sm.merge(_sel_mes, on=_sk3m + ['mes'], how='inner')[_sk3m + ['tipo','tacc','sin','brecha_pct']]
_bt_por_suc = {}
for _r in _btm.itertuples(index=False):
    _bt_por_suc.setdefault((_r.id_comercio, _r.id_bandera, _r.id_sucursal), {})[_r.tipo] = (_r.tacc, _r.sin, _r.brecha_pct)

_pu = datos_dia.merge(_sel_mes, on=_sk3m + ['mes'], how='inner').copy()
_pu['descripcion'] = _pu['ean_norm'].map(EAN_DESC)
_pu['subtipo'] = _pu['ean_norm'].map(EAN_SUBTIPO)
_prod = {}
for _r in _pu.itertuples(index=False):
    _d = (_prod.setdefault((_r.id_comercio, _r.id_bandera, _r.id_sucursal), {})
              .setdefault(_r.tipo, {}).setdefault(_r.subtipo, {'A': [], 'B': []}))
    _d['A' if _r.rol == 'tacc' else 'B'].append((str(_r.descripcion)[:38], _r.grams, _r.precio_100))

def _iround(_x):
    try: return int(round(float(_x)))
    except Exception: return None
def _p_arr(_lst):
    _lst = sorted(_lst, key=lambda x: (x[2] if x[2] == x[2] else 9e9))[:8]
    return [[_d, (int(_g) if (_g == _g and _g > 0) else 0), (_iround(_p) if _p == _p else None)] for _d, _g, _p in _lst]

_pd = {}
for _r in _bk.itertuples(index=False):
    _skk = (_r.id_comercio, _r.id_bandera, _r.id_sucursal)
    _key = f'{_r.id_comercio}_{_r.id_bandera}_{_r.id_sucursal}'
    _tipos = _bt_por_suc.get(_skk, {})
    _T = []
    for _tp in sorted(_tipos, key=lambda t: -_tipos[t][2]):
        _tacc_p, _sin_p, _brk = _tipos[_tp]
        _subs = _prod.get(_skk, {}).get(_tp, {})
        def _ord(_s):
            _d = _subs[_s]; return (0 if (_d['A'] and _d['B']) else 1, _s)
        _S = [{'s': _s, 'A': _p_arr(_subs[_s]['A']), 'B': _p_arr(_subs[_s]['B'])} for _s in sorted(_subs, key=_ord)]
        _T.append({'t': _tp, 'ta': _iround(_tacc_p), 'si': _iround(_sin_p), 'g': _iround(_brk), 'S': _S})
    _pd[_key] = {'c': str(_r.cadena), 'n': str(_r.sucursales_nombre)[:46], 'p': str(_r.PROVINCIA_NORM),
                 'l': str(_r.localidad), 'm': str(_r.mes), 'b': _iround(_r.brecha_comparable),
                 'pp': _iround(_r.peso_propio_pct), 'bt': _iround(_r.brecha_pct), 'bs': _iround(_r.base),
                 'cl': _iround(_r.celiaca), 'nt': int(_r.n_tipos), 'T': _T}
_json_str = _json.dumps(_pd, ensure_ascii=False, separators=(',', ':'))

_vmin = float(_bk['brecha_comparable'].quantile(0.05)); _vmax = float(_bk['brecha_comparable'].quantile(0.95))
if _vmin == _vmax: _vmin, _vmax = float(_bk['brecha_comparable'].min()), float(_bk['brecha_comparable'].max()) + 1
_cm = LinearColormap(colors=['#1a9850','#66bd63','#a6d96a','#fee08b','#fdae61','#f46d43','#d73027'],
                     vmin=_vmin, vmax=_vmax, caption=f'Brecha de canasta celíaca (%) — {NOMBRE_MES_TITLE}')

m = folium.Map(location=[-38.0, -63.5], zoom_start=5, tiles=None, control_scale=True)
_ESRI = 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/'
folium.TileLayer(tiles=_ESRI + 'World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}', attr='Esri, HERE, Garmin, OSM',
                 name='Esri Light Gray', control=False).add_to(m)
folium.TileLayer(tiles=_ESRI + 'World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}', attr='Esri',
                 name='Esri nombres', control=False, overlay=True).add_to(m)
try:
    if 'GEOJSON_PATH' in dir() and Path(GEOJSON_PATH).exists():
        with open(GEOJSON_PATH, 'r', encoding='utf-8') as _gf:
            _geo_base = _json.load(_gf)
        folium.GeoJson(_geo_base, name='Límites provinciales', control=False,
                       style_function=lambda _f: {'color': '#8a8f98', 'weight': 1.0,
                                                  'fillColor': '#eef0f2', 'fillOpacity': 0.20}
                       ).add_to(m)
except Exception as _e:
    print(f'  (aviso: no se pudieron dibujar los límites provinciales: {_e})')
_cm.add_to(m)
Fullscreen(position='topright', title='Pantalla completa', title_cancel='Salir').add_to(m)

_fgs = {}
def _fg(_cad):
    if _cad not in _fgs:
        _fgs[_cad] = folium.FeatureGroup(name=str(_cad), show=True)
    return _fgs[_cad]

for _r in _bk.itertuples(index=False):
    _key = f'{_r.id_comercio}_{_r.id_bandera}_{_r.id_sucursal}'
    _b = float(_r.brecha_comparable); _col = _cm(max(_vmin, min(_vmax, _b)))
    _ph = (f'<div class="lz-pop" data-key="{_key}" style="min-width:320px">'
           f'<span style="color:#aaa;font-family:Arial;font-size:12px">Cargando detalle…</span></div>')
    folium.CircleMarker(
        location=[_r.sucursales_latitud, _r.sucursales_longitud],
        radius=6, color='#333', weight=0.6, fill=True, fillColor=_col, fillOpacity=0.9,
        tooltip=(f'<b>{_r.cadena}</b><br>{_r.PROVINCIA_NORM}<br>Brecha <b>{_b:+.0f}%</b> '
                 f'({_r.peso_propio_pct:.0f}% de la canasta medida acá)'),
        popup=folium.Popup(_ph, max_width=500)
    ).add_to(_fg(_r.cadena))

for _c in sorted(_fgs): _fgs[_c].add_to(m)
folium.LayerControl(collapsed=True, position='topright').add_to(m)

_med_nac = _bk['brecha_comparable'].median()
_info = (f'<div style="position:fixed;top:10px;left:50px;width:335px;background:white;border:2px solid #0055A4;'
         f'border-radius:8px;padding:12px 15px;font-family:Arial;z-index:9999;box-shadow:0 2px 8px rgba(0,0,0,.15)">'
         f'<div style="color:#0055A4;font-size:15px;font-weight:bold;margin-bottom:4px">Brecha celíaca por sucursal</div>'
         f'<div style="font-size:11px;color:#555;line-height:1.5">Última brecha disponible por sucursal '
         f'(últimos {VENTANA_MAPA_MESES} meses) · <b>{len(_bk):,}</b> sucursales · <b>{len(_fgs)}</b> cadenas<br>'
         f'Brecha mediana: <b>{_med_nac:+.0f}%</b> · el popup indica de qué mes es cada dato<br>'
         f'Misma canasta en todas: lo que una sucursal no vende, con la brecha nacional del mes<br>'
         f'<span style="color:#1a9850">■</span> menor &nbsp; <span style="color:#d73027">■</span> mayor brecha &nbsp;·&nbsp; '
         f'filtrá cadenas con el control de capas (arriba der.)</div></div>')
m.get_root().html.add_child(folium.Element(_info))
m.get_root().html.add_child(folium.Element(f'<script type="application/json" id="_pd_json">{_json_str}</script>'))

_MV = m.get_name()
_JS = '''<script>
var _MV="__MAPVAR__", _MES="__MES__", _PD=null;
function _gpd(){ if(!_PD){ var el=document.getElementById("_pd_json"); if(el) _PD=JSON.parse(el.textContent); } return _PD; }
function _fmt(x){ return "$"+Number(x).toLocaleString("es-AR"); }
function _sg(x){ return (x>=0?"+":"")+x; }
function _plist(a){ if(!a||!a.length) return '<span style="color:#bbb">—</span>'; var s=""; for(var i=0;i<a.length;i++){ var g=a[i][1]?a[i][1]+" g":"s/pres"; var p=(a[i][2]!=null)?_fmt(a[i][2])+"/100g":"s/precio"; s+='<div style="margin:1px 0">• '+a[i][0]+' <span style="color:#777">('+g+", "+p+')</span></div>'; } return s; }
function _bpop(k){ var pd=_gpd(); if(!pd||!pd[k]) return "<div>Sin datos.</div>"; var d=pd[k];
  var h='<div style="font-family:Arial;font-size:12px;min-width:360px;max-width:480px;max-height:520px;overflow-y:auto">';
  h+='<div style="font-size:14px;font-weight:bold">'+d.n+'</div>';
  h+='<div style="color:#555;margin-bottom:5px">'+d.c+" · "+d.l+", "+d.p+'</div>';
  h+='<div style="padding:6px;background:#f5f5f5;border-radius:4px;margin-bottom:4px">Brecha de la canasta celíaca: <b style="font-size:15px">'+_sg(d.b)+'%</b><br><span style="color:#888;font-size:11px">Misma canasta en todas las sucursales: '+d.pp+'% medida acá; lo que no vende, con la brecha nacional del mes</span><br>Solo con sus '+d.nt+' tipo(s): '+_sg(d.bt)+'% · canasta con TACC <b>'+_fmt(d.bs)+'</b> · sin TACC <b>'+_fmt(d.cl)+'</b> <span style="color:#888">($/100g ponderado)</span><br><span style="color:#888;font-size:11px">dato de '+d.m+'</span></div>';
  for(var i=0;i<d.T.length;i++){ var t=d.T[i];
    h+='<div style="margin-top:7px;font-weight:bold;color:#1F4E79">'+t.t+" · brecha del tipo "+_sg(t.g)+'% <span style="color:#888;font-weight:normal">(mediana con TACC '+_fmt(t.ta)+" vs sin "+_fmt(t.si)+'/100g)</span></div>';
    h+='<table style="border-collapse:collapse;width:100%;font-size:11px"><tr style="background:#1F4E79;color:#fff"><th style="padding:2px">Equivalente</th><th style="padding:2px">Con TACC</th><th style="padding:2px">Sin TACC</th></tr>';
    for(var j=0;j<t.S.length;j++){ var s=t.S[j];
      h+='<tr><td style="border:1px solid #ddd;padding:3px;vertical-align:top;font-weight:600">'+s.s+'</td><td style="border:1px solid #ddd;padding:3px;vertical-align:top">'+_plist(s.A)+'</td><td style="border:1px solid #ddd;padding:3px;vertical-align:top">'+_plist(s.B)+'</td></tr>';
    }
    h+="</table>";
  }
  h+='<div style="color:#999;font-size:10px;margin-top:5px">Filas = productos equivalentes. La brecha autoritativa es la del tipo (§3); acá se listan los productos comparados de cada lado.</div></div>';
  return h;
}
function _init(){ var mp=window[_MV]; if(!mp){ setTimeout(_init,300); return; } mp.on("popupopen",function(e){ var el=e.popup.getElement().querySelector(".lz-pop"); if(el&&el.getAttribute("data-b")!=="1"){ el.innerHTML=_bpop(el.getAttribute("data-key")); el.setAttribute("data-b","1"); e.popup.update(); } }); }
setTimeout(_init,500);
</script>'''
_JS = _JS.replace('__MAPVAR__', _MV).replace('__MES__', NOMBRE_MES_TITLE)
m.get_root().html.add_child(folium.Element(_JS))

_out_map = OUTPUT_DIR / f'mapa_sucursales_brecha_{MES}.html'
m.save(str(_out_map))
print(f'Mapa Folium por sucursal guardado: {_out_map}')
print(f'  {len(_bk):,} sucursales · {len(_fgs)} cadenas (últimos {VENTANA_MAPA_MESES} meses; incluye cadenas sin dato el último mes)'
      f' · popup lazy-load · límites del GeoJSON local · JSON {len(_json_str)/1024/1024:.1f} MB')
_mmix = _bk['mes'].value_counts().to_dict()
print(f'  Meses del snapshot (sucursal→mes más reciente): ' + ', '.join(f'{_m}:{_n}' for _m,_n in sorted(_mmix.items(), reverse=True)))"""))

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
out_path = os.path.join(HERE, '06_evolucion_brecha_celiaca.ipynb')
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
print(f'Written: {out_path}')
print(f'Cells: {len(cells)}')
