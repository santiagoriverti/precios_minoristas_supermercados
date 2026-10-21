"""Script to generate 09_trazabilidad_productos.ipynb — representatividad de todos los productos del SEPA"""
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
cells.append(cell_md("""# SEPA — Trazabilidad y representatividad de TODOS los productos (2022 en adelante)

**Objetivo:** recorrer todos los archivos de los ZIPs semestrales de `MyDrive/carga/` (`2022A.zip` ... `2026B.zip`) y
armar, para cada producto (`id_producto`) que alguna vez reportó precio, qué tan representativo es:

- **Temporal:** días con precio sobre los días del período, primer/último día, rachas, huecos, días "útiles"
  (con ≥ `MIN_SUC_DIA_UTIL` sucursales y ≥ `MIN_PCT_DIA_UTIL` % de las sucursales activas ese día).
- **Sucursal:** sucursales distintas sobre el total histórico y **cuota diaria** (sucursales con precio / sucursales
  activas ese día), que no castiga a un producto por sucursales que todavía no existían.
- **Comercial:** comercios (empresa) y banderas distintos, cuota diaria de comercios, concentración en la cadena principal.
- **Regional:** provincias, regiones INDEC (+ AMBA por coordenadas), departamentos y localidades (Georef).
- **Precio:** mediana y dispersión entre sucursales del último mes.
- **Puntaje 0-100:** media geométrica de temporal, sucursal (cuota diaria), comercial y regional.

**Dos fases:**
1. **Lectura** (la pesada): cada archivo `MMAAAA_pais_parteN` se lee **por bloques** (`BLOQUE_MB`) con un **script
   aparte** (`nb09_lector.py`, un proceso por archivo) y se resume en 4 tablas chicas que se guardan en `output_trazabilidad/_cache_nb09/`. Un archivo ya resumido
   no se vuelve a leer (el último mes, que puede estar en curso, se relee siempre). Si Colab se corta, se vuelve a
   ejecutar y sigue donde quedó.
2. **Agregación:** junta los resúmenes día por día y, para sucursales/cadenas/regiones, de a un grupo de productos por
   vez (`N_GRUPOS`). No relee el SEPA. Ninguna etapa carga todo el período junto: la memoria no crece con los años.
3. **Excel** escrito fila a fila (memoria constante).

**Salidas** (en `output_trazabilidad/`): `trazabilidad_productos_<desde>_<hasta>.xlsx` (Resumen, Ranking,
Continuos_periodo, Por_categoria, Cadenas, Provincias, Diccionario), el mismo ranking en `.parquet` y `.csv.gz`, y el
panel mensual producto × mes en `.parquet`.

**Estructura:** Config → Setup → Maestros (sucursales, Georef, productos) → Fase 1 (lectura) → Fase 2a (días) →
Fase 2b (sucursales, cadenas, regiones) y ranking → Exportación. Cada celda imprime la RAM usada y la libre."""))

# ── CELL 1 — CONFIG ────────────────────────────────────────────────────────────
cells.append(cell_code(r"""# ===========================================================
# CONFIGURACIÓN — Modificar solo esta sección
# ===========================================================
SEPA_DIR   = '/content/drive/MyDrive/carga'                        # ZIPs semestrales 2022A.zip ... 2026B.zip
OUTPUT_DIR = '/content/drive/MyDrive/carga/output_trazabilidad'

FECHA_INICIO = '2022-01-01'
FECHA_FIN    = None               # None = hasta el último día de los ZIPs

# Día "útil" para un producto: al menos tantas sucursales con precio Y tal % de las sucursales activas ese día
MIN_SUC_DIA_UTIL = 100
MIN_PCT_DIA_UTIL = 5.0

# Departamentos y municipios de cada sucursal desde sus coordenadas (API Georef de datos.gob.ar, pública).
# Se consulta una sola vez por sucursal y queda en el caché. False = sin departamentos.
USAR_GEOREF = True

# Radio del AMBA alrededor del Obelisco (como el nb02): CABA + Buenos Aires a <= AMBA_RADIO_KM
AMBA_RADIO_KM = 90

# Comercios que filtra el nb02 (CELDA 6): se marca si el producto está fuera de ellos (columna en_universo_nb02)
CADENAS_FILTRAR_NB02 = {'19', '2013', '3001', '4'}

TOP_POR_CATEGORIA = 10            # productos por categoría en la hoja Por_categoria

# ── Memoria (Colab gratuito, ~12,7 GB) ──
# Cada archivo se lee en bloques de BLOQUE_MB (texto CSV): ~1 GB de pico por archivo con 32. Si la sesión se queda sin
# RAM, bajarlo (16, 8): tarda un poco más, no cambia el resultado.
BLOQUE_MB = 32
# La fase 2 arma la matriz producto x sucursal de a 1/N_GRUPOS de los productos. Más grupos = menos RAM, más tiempo.
# Cambiarlo NO relee el SEPA (los resúmenes se reorganizan solos la primera vez).
N_GRUPOS = 16
# Cada archivo lo lee un script aparte (python nb09_lector.py): al terminar, el sistema libera toda su memoria.
PROCESO_APARTE = True"""))

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
subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyarrow', 'xlsxwriter', 'openpyxl', 'scipy', 'psutil', '-q'],
               check=False)

import os, zipfile, gzip, re, gc, time, json, warnings, urllib.request
from pathlib import Path
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.compute as pac
import pyarrow.parquet as pq
import psutil
import scipy.sparse as sp

pd.set_option('display.max_columns', 60)
pd.set_option('display.width', 200)

SEPA_DIR   = Path(SEPA_DIR)
OUTPUT_DIR = Path(OUTPUT_DIR)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR  = OUTPUT_DIR / '_cache_nb09'
RES_DIR    = CACHE_DIR / 'v1'          # resúmenes por archivo (fase 1); cambiar la versión relee todo
RES_DIR.mkdir(parents=True, exist_ok=True)

def ram():
    # memoria del proceso y la que le queda a la máquina (para seguir el consumo en Colab)
    return (f'RAM: proceso {psutil.Process().memory_info().rss / 1e9:.1f} GB, '
            f'libre {psutil.virtual_memory().available / 1e9:.1f} GB')

print(f'SEPA_DIR:   {SEPA_DIR}')
print(f'OUTPUT_DIR: {OUTPUT_DIR}')
print(ram())"""))

# ── CELL 3 — MAESTROS ──────────────────────────────────────────────────────────
cells.append(cell_code(r"""# ============================================================
# CELDA 3 — Maestros: sucursales (AMBA, región INDEC, Georef), productos y nombres de cadenas
# ============================================================
DATA_URL = 'https://raw.githubusercontent.com/santiagoriverti/precios_minoristas_supermercados/main/data'

def leer_maestro(nombre, **kw):
    # Busqueda: ./data (local) -> Drive (SEPA_DIR y SEPA_DIR/data) -> /content/data -> GitHub raw (repo publico)
    for _p in [Path('data') / nombre, Path('../data') / nombre, SEPA_DIR / nombre, SEPA_DIR / 'data' / nombre,
               Path('/content/data') / nombre]:
        if _p.exists():
            return pd.read_excel(_p, **kw)
    import urllib.parse
    dl = Path('/content/data') / nombre
    dl.parent.mkdir(parents=True, exist_ok=True)
    print(f'  Descargando {nombre} desde GitHub...')
    urllib.request.urlretrieve(f'{DATA_URL}/{urllib.parse.quote(nombre)}', dl)
    return pd.read_excel(dl, **kw)

# ── Provincias (código ISO del archivo de precios -> nombre) y regiones INDEC ──
ISO_PROV = {'AR-C': 'CABA', 'AR-B': 'Buenos Aires', 'AR-K': 'Catamarca', 'AR-H': 'Chaco', 'AR-U': 'Chubut',
            'AR-X': 'Córdoba', 'AR-W': 'Corrientes', 'AR-E': 'Entre Ríos', 'AR-P': 'Formosa', 'AR-Y': 'Jujuy',
            'AR-L': 'La Pampa', 'AR-F': 'La Rioja', 'AR-M': 'Mendoza', 'AR-N': 'Misiones', 'AR-Q': 'Neuquén',
            'AR-R': 'Río Negro', 'AR-A': 'Salta', 'AR-J': 'San Juan', 'AR-D': 'San Luis', 'AR-Z': 'Santa Cruz',
            'AR-S': 'Santa Fe', 'AR-G': 'Santiago del Estero', 'AR-V': 'Tierra del Fuego', 'AR-T': 'Tucumán'}
REGION_PROV = {'CABA': 'GBA (AMBA)', 'Córdoba': 'Pampeana', 'Santa Fe': 'Pampeana', 'Entre Ríos': 'Pampeana',
               'La Pampa': 'Pampeana', 'Jujuy': 'Noroeste', 'Salta': 'Noroeste', 'Tucumán': 'Noroeste',
               'Catamarca': 'Noroeste', 'Santiago del Estero': 'Noroeste', 'La Rioja': 'Noroeste',
               'Corrientes': 'Noreste', 'Chaco': 'Noreste', 'Formosa': 'Noreste', 'Misiones': 'Noreste',
               'Mendoza': 'Cuyo', 'San Juan': 'Cuyo', 'San Luis': 'Cuyo', 'Neuquén': 'Patagonia',
               'Río Negro': 'Patagonia', 'Chubut': 'Patagonia', 'Santa Cruz': 'Patagonia', 'Tierra del Fuego': 'Patagonia'}
# Buenos Aires: GBA (AMBA) si está a <= AMBA_RADIO_KM del Obelisco, Pampeana si no; sin coordenadas, sin región.

# ── Nombres de comercio (empresa) y bandera (los del nb02, CELDA 4) ──
NOMBRE_COMERCIO = {'2': 'La Anonima', '3': 'Cadena 3', '5': 'Hipermercado Misiones', '8': 'Cadena 8 (Cordoba)',
                   '9': 'Cencosud (Vea, Disco, Jumbo)', '10': 'Carrefour', '11': 'ChangoMas', '12': 'Coto',
                   '13': 'Cooperativa Obrera', '15': 'DIA', '16': 'Libertad', '20': 'LAR', '21': 'Toledo',
                   '23': 'Cadena 23', '47': 'Pasamonte'}
NOMBRE_BANDERA = {('9', '1'): 'Vea', ('9', '2'): 'Disco', ('9', '3'): 'Jumbo', ('10', '1'): 'Carrefour',
                  ('10', '2'): 'Carrefour Market', ('10', '3'): 'Carrefour Express', ('11', '2'): 'ChangoMas',
                  ('11', '4'): 'Hiper ChangoMas', ('11', '5'): 'Mi ChangoMas', ('16', '1'): 'Hipermercado Libertad',
                  ('16', '2'): 'Mini Libertad'}

def nombre_comercio(c):
    return NOMBRE_COMERCIO.get(str(c), f'Cadena {c}')

def nombre_bandera(c, b):
    return NOMBRE_BANDERA.get((str(c), str(b)), nombre_comercio(c) + ('' if str(b) == '1' else f' (bandera {b})'))

def clave_suc(c, b, s):
    return f'{c}|{b}|{s}'

# ── Maestro de sucursales: coordenadas, localidad, tipo, AMBA ──
print('Cargando maestros...')
maestro_suc = leer_maestro('maestro_sucursales_completo.xlsx', dtype={'id_comercio': str, 'id_bandera': str,
                                                                       'id_sucursal': str})
maestro_suc['suc'] = [clave_suc(c, b, s) for c, b, s in
                      zip(maestro_suc['id_comercio'], maestro_suc['id_bandera'], maestro_suc['id_sucursal'])]
maestro_suc = maestro_suc.drop_duplicates('suc').set_index('suc')
_lat = pd.to_numeric(maestro_suc['sucursales_latitud'], errors='coerce')
_lon = pd.to_numeric(maestro_suc['sucursales_longitud'], errors='coerce')
_ok = _lat.between(-55.5, -21.5) & _lon.between(-74, -53)
maestro_suc['lat'] = _lat.where(_ok)
maestro_suc['lon'] = _lon.where(_ok)
_R = 6371.0
_p1, _p2 = np.radians(-34.6037), np.radians(maestro_suc['lat'])
_dl = np.radians(maestro_suc['lon'] - (-58.3816))
maestro_suc['dist_obelisco_km'] = 2 * _R * np.arcsin(np.sqrt(np.sin((_p2 - _p1) / 2) ** 2 +
                                                            np.cos(_p1) * np.cos(_p2) * np.sin(_dl / 2) ** 2))
print(f'  Maestro de sucursales: {len(maestro_suc):,} ({int(_ok.sum()):,} con coordenadas válidas)')

# ── Georef: departamento y municipio por coordenadas (caché en el Drive) ──
GEOREF_CACHE = CACHE_DIR / 'georef_sucursales.parquet'
georef = (pd.read_parquet(GEOREF_CACHE) if GEOREF_CACHE.exists()
          else pd.DataFrame(columns=['suc', 'departamento_id', 'departamento', 'municipio', 'provincia_georef']))
if USAR_GEOREF:
    _pend = maestro_suc[maestro_suc['lat'].notna() & ~maestro_suc.index.isin(georef['suc'])]
    if len(_pend):
        print(f'  Georef: consultando {len(_pend):,} sucursales...')
        _filas = []
        for _i in range(0, len(_pend), 500):
            _b = _pend.iloc[_i:_i + 500]
            _body = json.dumps({'ubicaciones': [{'lat': float(la), 'lon': float(lo), 'aplanar': True,
                                                 'campos': 'provincia.nombre,departamento.id,departamento.nombre,'
                                                           'municipio.nombre'}
                                                for la, lo in zip(_b['lat'], _b['lon'])]}).encode()
            try:
                _req = urllib.request.Request('https://apis.datos.gob.ar/georef/api/ubicacion', data=_body,
                                              headers={'Content-Type': 'application/json'})
                with urllib.request.urlopen(_req, timeout=120) as _r:
                    _res = json.loads(_r.read())['resultados']
            except Exception as _e:
                print(f'  AVISO: Georef no respondió ({_e}); las sucursales que faltan quedan sin departamento '
                      f'(se reintenta en la próxima corrida)')
                break
            for _k, _x in zip(_b.index, _res):
                _u = _x.get('ubicacion') or {}
                _filas.append({'suc': _k, 'departamento_id': _u.get('departamento_id'),
                               'departamento': _u.get('departamento_nombre'), 'municipio': _u.get('municipio_nombre'),
                               'provincia_georef': _u.get('provincia_nombre')})
            time.sleep(0.5)
        if _filas:
            georef = pd.concat([georef, pd.DataFrame(_filas)], ignore_index=True).drop_duplicates('suc', keep='last')
            georef.to_parquet(GEOREF_CACHE, index=False)
    print(f'  Georef: {georef["departamento_id"].notna().sum():,} sucursales con departamento')
maestro_suc = maestro_suc.join(georef.set_index('suc')[['departamento_id', 'departamento', 'municipio']], how='left')

# ── Maestro de productos interno: descripción, marca, rubro/categoría, proveedor, EAN o código interno ──
maestro_prod = leer_maestro('Maestro de Productos Interno.xlsx', dtype=str)
maestro_prod['id'] = maestro_prod['producto_sepa_id'].str.strip().str.lstrip('0').replace('', '0')
maestro_prod['presentacion'] = (maestro_prod['producto_cantidad_presentacion'].fillna('') + ' ' +
                                maestro_prod['producto_unidad_medida_presentac'].fillna('')).str.strip()
maestro_prod = (maestro_prod.drop_duplicates('id').set_index('id')
                .rename(columns={'producto_descripcion': 'descripcion', 'producto_marca': 'marca',
                                 'producto_blacklist': 'blacklist', 'producto_ean': 'ean_maestro'})
                [['descripcion', 'marca', 'presentacion', 'rubro', 'categoria', 'subcategoria', 'proveedor',
                  'blacklist', 'ean_maestro']])
print(f'  Maestro de productos: {len(maestro_prod):,} productos')

def gtin_valido(s):
    # Dígito verificador GTIN-8/12/13/14
    if not s.isdigit() or len(s) not in (8, 12, 13, 14):
        return False
    d = [int(x) for x in s[:-1]][::-1]
    return (10 - sum(x * (3 if i % 2 == 0 else 1) for i, x in enumerate(d)) % 10) % 10 == int(s[-1])
print('Maestros OK')"""))

# ── CELL 4 — FASE 1 ────────────────────────────────────────────────────────────
cells.append(cell_code(r"""# ============================================================
# CELDA 4 — Fase 1: lectura de cada archivo del SEPA POR BLOQUES, en un proceso aparte (con caché por archivo)
# ============================================================
# Cada archivo MMAAAA_pais_parteN (una fila por sucursal x producto, una columna precio_AAAAMMDD por día) se lee en
# bloques de BLOQUE_MB y se resume en:
#   ean_dia : producto x día -> sucursales, comercios y provincias con precio
#   ean_suc : producto x sucursal -> días con precio y precio promedio de esos días (pesos), partido en N_GRUPOS grupos
#             de productos (un row group del parquet por grupo: la fase 2 lee un grupo por vez)
#   suc     : sucursales del archivo (comercio, bandera, sucursal, provincia) y días con algún precio
#   dia     : día -> sucursales, comercios, banderas y provincias activas, productos con precio (denominadores)
# 'dia' se escribe último: si existe, el archivo está completo.
# El lector es un script aparte (nb09_lector.py, lo escribe esta celda) que se ejecuta con `python` para cada archivo:
# al terminar, el sistema operativo recupera TODA su memoria (sin esto la RAM crecía archivo a archivo hasta colapsar
# la sesión). Verificado: el SEPA no repite sucursal x producto dentro de un archivo, así que sumar bloques es exacto.
import importlib, tempfile

LECTOR_SRC = r'''
import gzip, json, os, re, sys, time, traceback, zipfile, zlib
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.compute as pac
import pyarrow.parquet as pq

PAT_FECHA = re.compile(r'^precio_(\d{8})$')
ID_COLS = ['id_comercio', 'id_bandera', 'id_sucursal', 'sucursales_provincia', 'id_producto']

def clave_suc(c, b, s):
    return f'{c}|{b}|{s}'

def grupo_de(eans, n_grupos):
    # grupo estable de cada producto (crc32 del código): el mismo en todos los archivos y corridas
    return np.array([zlib.crc32(str(x).encode()) % n_grupos for x in eans], dtype=np.int16)

class Codigos:
    # texto -> código entero estable dentro de un archivo. Se limpia solo el diccionario de cada bloque (miles de
    # valores), nunca un texto por fila.
    def __init__(self, ean=False):
        self.mapa, self.ean = {}, ean
    def __call__(self, arr):
        if not pa.types.is_dictionary(arr.type):
            arr = pac.cast(arr, pa.string()).dictionary_encode()
        vals = arr.dictionary.to_pylist() + [None]
        m = np.empty(len(vals), np.int64)
        for i, v in enumerate(vals):
            v = '' if v is None else str(v).strip()
            if self.ean:
                v = v.lstrip('0') or '0'
            c = self.mapa.get(v)
            if c is None:
                c = self.mapa[v] = len(self.mapa)
            m[i] = c
        idx = pac.fill_null(arr.indices, len(vals) - 1).to_numpy(zero_copy_only=False)
        return m[idx]
    def valores(self):
        out = np.empty(len(self.mapa), dtype=object)
        for v, c in self.mapa.items():
            out[c] = v
        return out

def crecer(a, n, eje=0):
    # agranda un acumulador (con margen) cuando aparecen códigos nuevos
    if a.shape[eje] >= n:
        return a
    forma = list(a.shape); forma[eje] = max(n, int(a.shape[eje] * 1.5) + 16)
    b = np.zeros(forma, a.dtype)
    b[tuple(slice(0, s) for s in a.shape)] = a
    return b

def a_float32(col):
    if pa.types.is_string(col.type) or pa.types.is_large_string(col.type):
        return pd.to_numeric(col.to_pandas(), errors='coerce').to_numpy(np.float32)
    return pac.fill_null(pac.cast(col, pa.float32()), np.nan).to_numpy(zero_copy_only=False)

def resumir(zip_path, nombre, f_ini, f_fin, bloque_mb, n_grupos, precios_texto=False):
    with zipfile.ZipFile(zip_path) as zf:
        with zf.open(nombre) as s0, gzip.open(s0, 'rt', encoding='utf-8', errors='replace') as g:
            hdr = [c.strip() for c in g.readline().split(',')]
        cols_p = [c for c in hdr if PAT_FECHA.match(c) and f_ini <= pd.Timestamp(c[-8:]) <= f_fin]
        if not cols_p:
            return None
        fechas = pd.to_datetime([c[-8:] for c in cols_p], format='%Y%m%d')
        nd = len(cols_p)
        tipos = {c: pa.dictionary(pa.int32(), pa.string()) for c in ID_COLS}
        tipos.update({c: (pa.string() if precios_texto else pa.float64()) for c in cols_p})
        cod_e, cod_c, cod_b, cod_s, cod_p = Codigos(ean=True), Codigos(), Codigos(), Codigos(), Codigos()
        suc_mapa = {}                                   # (c, b, s) -> código de sucursal del archivo
        suc_cbs, suc_prv = [], []                       # comercio/bandera/sucursal y provincia por sucursal
        n_suc = np.zeros((1024, nd), np.int32)          # producto x día: sucursales con precio
        a_com = np.zeros((1024, 8, nd), bool)           # producto x comercio x día
        a_prv = np.zeros((1024, 8, nd), bool)           # producto x provincia x día
        s_dia = np.zeros((256, nd), bool)               # sucursal x día activa
        s_fil = np.zeros(256, np.int64)                 # filas con algún precio por sucursal
        es_e, es_s, es_n, es_p = [], [], [], []
        with zf.open(nombre) as s0, pa.CompressedInputStream(pa.PythonFile(s0, mode='r'), 'gzip') as s:
            lector = pacsv.open_csv(s, read_options=pacsv.ReadOptions(block_size=max(int(bloque_mb * 2 ** 20), 1024)),
                                    convert_options=pacsv.ConvertOptions(
                                        column_types=tipos, include_columns=ID_COLS + cols_p,
                                        null_values=['NA', ''], strings_can_be_null=True))
            for bl in lector:
                if bl.num_rows == 0:
                    continue
                e = cod_e(bl.column('id_producto'))
                c = cod_c(bl.column('id_comercio')); b = cod_b(bl.column('id_bandera'))
                si = cod_s(bl.column('id_sucursal')); pv = cod_p(bl.column('sucursales_provincia'))
                k = (c << 42) | (b << 21) | si
                uk, prim, inv = np.unique(k, return_index=True, return_inverse=True)
                st_u = np.empty(len(uk), np.int64)
                for i, x in enumerate(uk):
                    y = suc_mapa.get(int(x))
                    if y is None:
                        j = int(prim[i])
                        y = suc_mapa[int(x)] = len(suc_mapa)
                        suc_cbs.append((int(c[j]), int(b[j]), int(si[j]))); suc_prv.append(int(pv[j]))
                    st_u[i] = y
                st = st_u[inv.ravel()]
                P = np.empty((bl.num_rows, nd), np.float32)
                for j, col in enumerate(cols_p):
                    P[:, j] = a_float32(bl.column(col))
                del bl
                V = np.isfinite(P) & (P > 0)
                ne, ns = len(cod_e.mapa), len(suc_mapa)
                n_suc = crecer(n_suc, ne); s_dia = crecer(s_dia, ns); s_fil = crecer(s_fil, ns)
                a_com = crecer(crecer(a_com, ne), len(cod_c.mapa), 1)
                a_prv = crecer(crecer(a_prv, ne), len(cod_p.mapa), 1)
                com_f = np.array([x[0] for x in suc_cbs])[st]           # comercio de cada fila (código del archivo)
                prv_f = np.array(suc_prv)[st]
                for j in range(nd):
                    v = V[:, j]
                    if not v.any():
                        continue
                    n_suc[:, j] += np.bincount(e[v], minlength=n_suc.shape[0]).astype(np.int32)
                    a_com[e[v], com_f[v], j] = True
                    a_prv[e[v], prv_f[v], j] = True
                    s_dia[st[v], j] = True
                n = V.sum(axis=1)
                np.add.at(s_fil, st[n > 0], 1)
                np.putmask(P, ~V, 0)
                m = n > 0
                es_e.append(e[m].astype(np.int32)); es_s.append(st[m].astype(np.int32)); es_n.append(n[m].astype(np.int16))
                es_p.append(P.sum(axis=1, dtype=np.float64)[m])
                del P, V, e, st, k, inv
    ne, ns = len(cod_e.mapa), len(suc_mapa)
    eans = cod_e.valores()
    n_suc, a_com, a_prv, s_dia, s_fil = n_suc[:ne], a_com[:ne], a_prv[:ne], s_dia[:ns], s_fil[:ns]
    if not s_dia.any():
        return None
    cv, bv, sv, pvv = cod_c.valores(), cod_b.valores(), cod_s.valores(), cod_p.valores()
    suc_c = np.array([cv[x[0]] for x in suc_cbs], dtype=object)
    suc_b = np.array([bv[x[1]] for x in suc_cbs], dtype=object)
    suc_s = np.array([sv[x[2]] for x in suc_cbs], dtype=object)
    suc_p = np.array([pvv[x] for x in suc_prv], dtype=object)
    sucs = np.array([clave_suc(a, b, c) for a, b, c in zip(suc_c, suc_b, suc_s)], dtype=object)

    # producto x día
    n_com, n_prv = a_com.sum(axis=1), a_prv.sum(axis=1)
    del a_com, a_prv
    ed = []
    for j, f in enumerate(fechas):
        k = np.nonzero(n_suc[:, j])[0]
        if len(k):
            ed.append(pd.DataFrame({'e': k.astype(np.int32), 'fecha': f, 'n_suc': n_suc[k, j],
                                    'n_com': n_com[k, j].astype(np.int16), 'n_prov': n_prv[k, j].astype(np.int16)}))
    ean_dia = pd.concat(ed, ignore_index=True)
    ean_dia['ean'] = pd.Categorical.from_codes(ean_dia.pop('e'), categories=eans).remove_unused_categories()

    # días (denominadores)
    ban = np.array([f'{a}|{b}' for a, b in zip(suc_c, suc_b)])
    dia = pd.DataFrame([{'fecha': f, 'n_suc': int(s_dia[:, j].sum()), 'n_com': int(len(set(suc_c[s_dia[:, j]]))),
                         'n_ban': int(len(set(ban[s_dia[:, j]]))), 'n_prov': int(len(set(suc_p[s_dia[:, j]]))),
                         'n_productos': int((n_suc[:, j] > 0).sum()), 'n_precios': int(n_suc[:, j].sum())}
                        for j, f in enumerate(fechas) if s_dia[:, j].any()])

    # producto x sucursal, ordenado por grupo y producto
    e = np.concatenate(es_e); st = np.concatenate(es_s); n = np.concatenate(es_n)
    precio = (np.concatenate(es_p) / n).astype(np.float32)
    del es_e, es_s, es_n, es_p
    fac = 100.0 if np.median(precio) > 10_000 else 1.0           # pesos o centavos: regla del nb02
    dia['factor_precio'] = fac
    precio /= fac
    g = grupo_de(eans, n_grupos)[e]
    o = np.lexsort((st, e, g))
    e, st, n, precio, g = e[o], st[o], n[o], precio[o], g[o]
    suc = pd.DataFrame({'suc': sucs, 'id_comercio': suc_c, 'id_bandera': suc_b, 'id_sucursal': suc_s,
                        'provincia_iso': suc_p, 'dias_activa': s_dia.sum(axis=1).astype(np.int16),
                        'filas_con_precio': s_fil.astype(np.int32)})
    return {'ean_dia': ean_dia, 'ean_suc': (eans, sucs, e, st, n, precio, g), 'suc': suc, 'dia': dia}

def escribir_ean_suc(ruta, eans, sucs, e, st, n, precio, g, n_grupos):
    # un row group por grupo de productos (filas ya ordenadas por grupo); el mapa grupo -> row group va en los
    # metadatos del parquet. Se escribe a un temporal y se renombra: nunca queda un archivo a medias.
    cortes = np.searchsorted(g, np.arange(n_grupos + 1))
    no_vacios = [k for k in range(n_grupos) if cortes[k] < cortes[k + 1]]
    dic = pa.dictionary(pa.int32(), pa.string())
    esquema = pa.schema([('ean', dic), ('suc', dic), ('n_dias', pa.int16()), ('precio', pa.float32())],
                        metadata={'nb09_grupos': json.dumps({str(k): i for i, k in enumerate(no_vacios)}),
                                  'nb09_n_grupos': str(n_grupos)})
    tmp = str(ruta) + '.tmp'
    with pq.ParquetWriter(tmp, esquema, compression='zstd') as w:
        for k in no_vacios:
            a, b = cortes[k], cortes[k + 1]
            ue, ie = np.unique(e[a:b], return_inverse=True)
            us, is_ = np.unique(st[a:b], return_inverse=True)
            t = pa.table({'ean': pa.DictionaryArray.from_arrays(pa.array(ie.ravel().astype(np.int32)),
                                                                pa.array(list(eans[ue]), pa.string())),
                          'suc': pa.DictionaryArray.from_arrays(pa.array(is_.ravel().astype(np.int32)),
                                                                pa.array(list(sucs[us]), pa.string())),
                          'n_dias': pa.array(n[a:b], pa.int16()), 'precio': pa.array(precio[a:b], pa.float32())},
                         schema=esquema)
            w.write_table(t, row_group_size=len(t) + 1)
    os.replace(tmp, ruta)

def leer_grupo(ruta, k, n_grupos):
    # filas del grupo de productos k de un ean_suc. Uno con otro formato (sin grupos o con otro N_GRUPOS) se
    # reorganiza una vez, sin releer el SEPA.
    pf = pq.ParquetFile(str(ruta))
    md = pf.schema_arrow.metadata or {}
    if b'nb09_grupos' not in md or int(md.get(b'nb09_n_grupos', b'0')) != n_grupos:
        d = pf.read().to_pandas()
        del pf
        eans = np.asarray(d['ean'].cat.categories, dtype=object); sucs = np.asarray(d['suc'].cat.categories, dtype=object)
        e = d['ean'].cat.codes.to_numpy(np.int64); st = d['suc'].cat.codes.to_numpy(np.int64)
        g = grupo_de(eans, n_grupos)[e]; o = np.lexsort((st, e, g))
        escribir_ean_suc(ruta, eans, sucs, e[o], st[o], d['n_dias'].to_numpy(np.int16)[o],
                         d['precio'].to_numpy(np.float32)[o], g[o], n_grupos)
        del d
        pf = pq.ParquetFile(str(ruta)); md = pf.schema_arrow.metadata
    mapa = json.loads(md[b'nb09_grupos'])
    if str(k) not in mapa:
        return None
    return pf.read_row_group(mapa[str(k)]).to_pandas()

def ruta(res_dir, tag, tipo):
    return Path(res_dir) / f'{tag}__{tipo}.parquet'

def procesar_y_guardar(a):
    t = time.time()
    f_ini, f_fin = pd.Timestamp(a['f_ini']), pd.Timestamp(a['f_fin'])
    try:
        r = resumir(a['zip'], a['nombre'], f_ini, f_fin, a['bloque_mb'], a['n_grupos'])
    except pa.ArrowInvalid as ex:
        print(f'  AVISO {a["nombre"]}: precios no numéricos ({str(ex)[:80]}); se relee convirtiendo', flush=True)
        r = resumir(a['zip'], a['nombre'], f_ini, f_fin, a['bloque_mb'], a['n_grupos'], precios_texto=True)
    if r is None:
        return {'tag': a['tag'], 'vacio': True}
    r['ean_dia'].to_parquet(ruta(a['res_dir'], a['tag'], 'ean_dia'), index=False, compression='zstd')
    escribir_ean_suc(ruta(a['res_dir'], a['tag'], 'ean_suc'), *r['ean_suc'], a['n_grupos'])
    r['suc'].to_parquet(ruta(a['res_dir'], a['tag'], 'suc'), index=False, compression='zstd')
    d = r['dia']
    pico = None
    try:
        import resource
        pico = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6, 2)   # Linux: KB -> GB
    except ImportError:
        pass
    info = {'tag': a['tag'], 'vacio': False, 'dias': len(d), 'productos': int(d['n_productos'].max()),
            'sucursales': int(d['n_suc'].max()), 'pares': int(len(r['ean_suc'][2])),
            'factor': float(d['factor_precio'].iat[0]), 'seg': round(time.time() - t), 'pico_gb': pico}
    d.to_parquet(ruta(a['res_dir'], a['tag'], 'dia'), index=False, compression='zstd')    # último = completo
    return info

if __name__ == '__main__':
    a = json.loads(sys.argv[1])
    try:
        info = procesar_y_guardar(a)
    except BaseException:
        info = {'tag': a['tag'], 'error': traceback.format_exc()[-3000:]}
    Path(a['res_dir'], f"{a['tag']}__info.json").write_text(json.dumps(info))
    sys.exit(1 if 'error' in info else 0)
'''

LECTOR_DIR = Path(tempfile.gettempdir()) / 'nb09'
LECTOR_DIR.mkdir(exist_ok=True)
LECTOR_PY = LECTOR_DIR / 'nb09_lector.py'
LECTOR_PY.write_text(LECTOR_SRC, encoding='utf-8')
if str(LECTOR_DIR) not in sys.path:
    sys.path.insert(0, str(LECTOR_DIR))
import nb09_lector as L
L = importlib.reload(L)

_PAT_SEM = re.compile(r'^(\d{4})(A|B)$', re.IGNORECASE)
_PAT_ARC = re.compile(r'^(\d{2})(\d{4})_pais_parte(\d+).*COMPLETO.*\.csv\.gz$', re.IGNORECASE)
F_INI = pd.Timestamp(FECHA_INICIO)
F_FIN = pd.Timestamp(FECHA_FIN) if FECHA_FIN else pd.Timestamp('2100-01-01')

def listar_archivos():
    # {tag: (zip, nombre, 'AAAA-MM')}; si un mes está en dos zips, gana el último (orden alfabético)
    out = {}
    for z in sorted(SEPA_DIR.glob('*.zip')):
        if not _PAT_SEM.match(z.stem):
            continue
        with zipfile.ZipFile(z) as zf:
            for n in zf.namelist():
                m = _PAT_ARC.match(Path(n).name)
                if m:
                    mes = f'{m.group(2)}-{m.group(1)}'
                    out[f'{mes}_p{int(m.group(3))}'] = (z, n, mes)
    return dict(sorted(out.items()))

def _ruta(tag, tipo):
    return L.ruta(RES_DIR, tag, tipo)

ARCHIVOS = listar_archivos()
ARCHIVOS = {t: v for t, v in ARCHIVOS.items() if F_INI.strftime('%Y-%m') <= v[2] <= F_FIN.strftime('%Y-%m')}
if not ARCHIVOS:
    raise RuntimeError(f'No hay archivos de los ZIPs semestrales en {SEPA_DIR} para el período')
MES_ULTIMO = max(v[2] for v in ARCHIVOS.values())
_meses = sorted({v[2] for v in ARCHIVOS.values()})
print(f'Archivos: {len(ARCHIVOS)} | meses {_meses[0]} -> {_meses[-1]} ({len(_meses)})')
_falta = [m for m in pd.period_range(_meses[0], _meses[-1], freq='M').astype(str) if m not in _meses]
if _falta:
    print(f'  AVISO: faltan meses en los ZIPs: {_falta}')
print(f'Lector: {LECTOR_PY} | {"un proceso por archivo" if PROCESO_APARTE else "en este proceso"} | '
      f'bloques de {BLOQUE_MB} MB | {ram()}')

_t0 = time.time()
_n_leidos = 0
for _tag, (_z, _n, _mes) in ARCHIVOS.items():
    if _mes != MES_ULTIMO and _ruta(_tag, 'dia').exists():
        continue
    _ruta(_tag, 'dia').unlink(missing_ok=True)
    _inf = RES_DIR / f'{_tag}__info.json'
    _inf.unlink(missing_ok=True)
    _args = {'tag': _tag, 'zip': str(_z), 'nombre': _n, 'res_dir': str(RES_DIR), 'f_ini': str(F_INI.date()),
             'f_fin': str(F_FIN.date()), 'bloque_mb': BLOQUE_MB, 'n_grupos': N_GRUPOS}
    if PROCESO_APARTE:
        _r = subprocess.run([sys.executable, str(LECTOR_PY), json.dumps(_args)], capture_output=True, text=True)
        if _r.stdout.strip():
            print(_r.stdout.strip())
        if _r.returncode != 0:
            if _inf.exists() and 'error' in json.loads(_inf.read_text()):
                raise RuntimeError(f'{_tag}: error en la lectura\n' + json.loads(_inf.read_text())['error'])
            raise RuntimeError(
                f'{_tag}: el lector terminó con código {_r.returncode}' +
                (' — SIN MEMORIA: bajar BLOQUE_MB en la CELDA 1 (16, 8) y volver a ejecutar desde la CELDA 1; lo ya '
                 'leído queda en el caché' if _r.returncode in (-9, 137) else '') + '\n' + _r.stderr[-2000:])
        _info = json.loads(_inf.read_text())
    else:
        _info = L.procesar_y_guardar(_args)
        gc.collect(); pa.default_memory_pool().release_unused()
    if _info.get('vacio'):
        print(f'  {_tag}: sin días en el período')
        continue
    _n_leidos += 1
    print(f'  {_tag}: {_info["dias"]} días, {_info["productos"]:,} productos/día, {_info["sucursales"]:,} sucursales, '
          f'{_info["pares"]:,} pares producto-sucursal, factor {_info["factor"]:g} ({_info["seg"]} s'
          + (f', pico del lector {_info["pico_gb"]} GB' if _info.get('pico_gb') else '') + f') | {ram()}', flush=True)
print(f'\nFase 1: {_n_leidos} archivos leídos en {(time.time() - _t0) / 60:.1f} min; '
      f'{len(ARCHIVOS) - _n_leidos} desde el caché ({RES_DIR})')"""))

# ── CELL 5 — FASE 2a ───────────────────────────────────────────────────────────
cells.append(cell_code(r"""# ============================================================
# CELDA 5 — Fase 2a: días, sucursales y recorrido diario por producto (no relee el SEPA)
# ============================================================
_t0 = time.time()
TAGS = [t for t in ARCHIVOS if _ruta(t, 'dia').exists()]

# ── Días del período y denominadores diarios ──
DIA = (pd.concat([pd.read_parquet(_ruta(t, 'dia')).assign(tag=t) for t in TAGS], ignore_index=True)
       .sort_values('fecha').drop_duplicates('fecha', keep='last').reset_index(drop=True))
FECHAS = pd.DatetimeIndex(DIA['fecha'])
TAG_FECHA = DIA.set_index('fecha')['tag']      # si un día viniera en dos archivos, cuenta solo el que quedó
ND = len(FECHAS)
POS_DIA = pd.Series(np.arange(ND), index=FECHAS)
ACT_SUC = DIA['n_suc'].to_numpy(float)
ACT_COM = DIA['n_com'].to_numpy(float)
ACT_PRV = DIA['n_prov'].to_numpy(float)
F_DESDE, F_HASTA = FECHAS[0], FECHAS[-1]
DIAS_CAL_SIN_DATO = pd.date_range(F_DESDE, F_HASTA).difference(FECHAS)
print(f'Período: {F_DESDE:%d/%m/%Y} -> {F_HASTA:%d/%m/%Y} | {ND:,} días con dato '
      f'({len(DIAS_CAL_SIN_DATO)} días calendario sin dato)')
_fac = DIA.groupby('factor_precio').size()
print(f'Factor de precio (100 = el archivo venía en centavos): {_fac.to_dict()} días')

# ── Sucursales (todas las que alguna vez reportaron) ──
SUC = (pd.concat([pd.read_parquet(_ruta(t, 'suc')) for t in TAGS], ignore_index=True)
       .groupby('suc', sort=True)
       .agg(id_comercio=('id_comercio', 'first'), id_bandera=('id_bandera', 'first'),
            id_sucursal=('id_sucursal', 'first'), provincia_iso=('provincia_iso', lambda s: s.mode().iat[0]),
            dias_activa=('dias_activa', 'sum')))
SUC['provincia'] = SUC['provincia_iso'].map(ISO_PROV).fillna('Sin provincia (' + SUC['provincia_iso'].astype(str) + ')')
SUC = SUC.join(maestro_suc[['lat', 'lon', 'dist_obelisco_km', 'sucursales_localidad', 'sucursales_tipo',
                            'departamento_id', 'departamento', 'municipio']], how='left')
SUC['amba'] = (SUC['provincia'] == 'CABA') | ((SUC['provincia'] == 'Buenos Aires') &
                                              (SUC['dist_obelisco_km'] <= AMBA_RADIO_KM))
SUC['region'] = SUC['provincia'].map(REGION_PROV)
_ba = SUC['provincia'] == 'Buenos Aires'
SUC.loc[_ba & SUC['amba'], 'region'] = 'GBA (AMBA)'
SUC.loc[_ba & ~SUC['amba'] & SUC['dist_obelisco_km'].notna(), 'region'] = 'Pampeana'
SUC['comercio'] = SUC['id_comercio'].map(nombre_comercio)
SUC['bandera'] = [nombre_bandera(c, b) for c, b in zip(SUC['id_comercio'], SUC['id_bandera'])]
SUC['localidad'] = (SUC['provincia'] + ' | ' + SUC['sucursales_localidad'].astype(str).str.strip().str.upper()
                    ).where(SUC['sucursales_localidad'].notna())
SUC['depto'] = (SUC['provincia'] + ' | ' + SUC['departamento'].astype(str)).where(SUC['departamento_id'].notna())
NS = len(SUC)
POS_SUC = pd.Series(np.arange(NS), index=SUC.index)
print(f'Sucursales: {NS:,} ({SUC["lat"].notna().sum():,} en el maestro con coordenadas, '
      f'{SUC["depto"].notna().sum():,} con departamento) | comercios {SUC["id_comercio"].nunique()} | '
      f'banderas {SUC["bandera"].nunique()} | provincias {SUC["provincia"].nunique()}')

# ── Productos: unión de todos los archivos ──
_cats = set()
for t in TAGS:
    _cats.update(pd.read_parquet(_ruta(t, 'ean_dia'), columns=['ean'])['ean'].cat.categories)
EANS = pd.Index(sorted(_cats))
NE = len(EANS)
GRUPO = L.grupo_de(EANS, N_GRUPOS)
del _cats; gc.collect()
print(f'Productos distintos con algún precio: {NE:,} | {ram()}')

# ── Acumuladores por producto (recorrido en orden de fechas; memoria = unos pocos vectores de NE) ──
dias_precio = np.zeros(NE, np.int32); dias_util = np.zeros(NE, np.int32)
sh_suc = np.zeros(NE); sh_com = np.zeros(NE); sh_prv = np.zeros(NE)
suc_obs = np.zeros(NE, np.int64)                     # sucursal-días con precio
min_suc = np.full(NE, np.iinfo(np.int32).max, np.int64)
primer = np.full(NE, -1, np.int32); ultimo = np.full(NE, -1, np.int32)
racha = np.zeros(NE, np.int32); racha_max = np.zeros(NE, np.int32)
hueco = np.zeros(NE, np.int32); hueco_max = np.zeros(NE, np.int32)
MESES = sorted({f.strftime('%Y-%m') for f in FECHAS})
POS_MES = {m: i for i, m in enumerate(MESES)}
mes_dias = np.zeros((len(MESES), NE), np.int16)       # panel mensual: días con precio
mes_suc = np.zeros((len(MESES), NE), np.float32)      # panel mensual: suma diaria de sucursales
_u365 = FECHAS >= F_HASTA - pd.Timedelta(days=364)
_u90 = FECHAS >= F_HASTA - pd.Timedelta(days=89)
c365 = np.zeros(NE, np.int32); c90 = np.zeros(NE, np.int32)

_orden = sorted(TAGS, key=lambda t: pd.read_parquet(_ruta(t, 'dia'), columns=['fecha'])['fecha'].min())
for _i, t in enumerate(_orden):
    ed = pd.read_parquet(_ruta(t, 'ean_dia'))
    ed = ed[ed['fecha'].map(TAG_FECHA).eq(t).to_numpy()]
    _e = EANS.get_indexer(ed['ean'].cat.categories)[ed['ean'].cat.codes.to_numpy()]
    _d = POS_DIA.reindex(ed['fecha']).to_numpy()
    _ns, _nc, _np = ed['n_suc'].to_numpy(), ed['n_com'].to_numpy(), ed['n_prov'].to_numpy()
    del ed
    for d in np.unique(_d):                              # días del archivo, en orden
        m = _d == d
        ee = _e[m]
        n_s = np.zeros(NE, np.int64); n_s[ee] = _ns[m]
        n_c = np.zeros(NE); n_c[ee] = _nc[m]
        n_p = np.zeros(NE); n_p[ee] = _np[m]
        pres = n_s > 0
        dias_precio += pres
        suc_obs += n_s
        sh_suc += n_s / ACT_SUC[d]; sh_com += n_c / ACT_COM[d]; sh_prv += n_p / ACT_PRV[d]
        dias_util += pres & (n_s >= MIN_SUC_DIA_UTIL) & (n_s / ACT_SUC[d] * 100 >= MIN_PCT_DIA_UTIL)
        np.minimum(min_suc, np.where(pres, n_s, min_suc), out=min_suc)
        primer[(primer < 0) & pres] = d
        ultimo[pres] = d
        racha = np.where(pres, racha + 1, 0); np.maximum(racha_max, racha, out=racha_max)
        hueco = np.where(pres, 0, np.where(primer >= 0, hueco + 1, 0)); np.maximum(hueco_max, hueco, out=hueco_max)
        mi = POS_MES[FECHAS[d].strftime('%Y-%m')]
        mes_dias[mi] += pres
        mes_suc[mi] += n_s
        if _u365[d]:
            c365 += pres
        if _u90[d]:
            c90 += pres
    if (_i + 1) % 12 == 0:
        print(f'  {_i + 1}/{len(_orden)} archivos ({time.time() - _t0:.0f} s) | {ram()}', flush=True)
gc.collect()
print(f'Fase 2a: {len(_orden)} archivos en {time.time() - _t0:.0f} s | {ram()}')"""))

# ── CELL 6 — FASE 2b + MÉTRICAS ────────────────────────────────────────────────
cells.append(cell_code(r"""# ============================================================
# CELDA 6 — Fase 2b: sucursales, cadenas y regiones por grupos de productos + métricas y ranking
# ============================================================
# La matriz producto x sucursal de todo el período no se arma nunca entera: se arma la de un grupo de productos
# (1/N_GRUPOS del total) leyendo solo ese row group de cada archivo, se calculan sus métricas y se libera.
_t0 = time.time()

def indicadora(codigos, ng):
    # sucursal x grupo (los códigos < 0 = sin dato, no cuentan)
    codigos = np.asarray(codigos)
    k = codigos >= 0
    return sp.csr_matrix((np.ones(k.sum(), np.int32), (np.nonzero(k)[0], codigos[k])), shape=(NS, max(ng, 1)))

DIMS = {}
for _col in ('id_comercio', 'bandera', 'provincia', 'region', 'depto', 'localidad'):
    _cat = pd.Categorical(SUC[_col])
    DIMS[_col] = (indicadora(_cat.codes, len(_cat.categories)), np.asarray(_cat.categories, dtype=object))
CAT_COM, CAT_PRV = DIMS['id_comercio'][1], DIMS['provincia'][1]
T_COM, T_BAN, T_PRV, T_REG, T_DEP, T_LOC = (len(DIMS[c][1]) for c in
                                            ('id_comercio', 'bandera', 'provincia', 'region', 'depto', 'localidad'))
AMBA_V = SUC['amba'].to_numpy(np.int32)
_fuera_nb02 = np.nonzero(np.array([c not in CADENAS_FILTRAR_NB02 for c in CAT_COM]))[0]
_nom_com = np.array([nombre_comercio(c) for c in CAT_COM], dtype=object)

suc_dist = np.zeros(NE, np.int32)
n_dim = {c: np.zeros(NE, np.int32) for c in DIMS}
en_amba = np.zeros(NE, bool); en_nb02 = np.zeros(NE, bool)
cad_pri = np.full(NE, '', dtype=object); pct_pri = np.full(NE, np.nan); hhi = np.full(NE, np.nan)
cadenas_txt = np.full(NE, '', dtype=object); prov_pres = np.full(NE, '', dtype=object); prov_falt = np.full(NE, '', dtype=object)
precio_med = np.full(NE, np.nan); precio_cv = np.full(NE, np.nan); suc_um = np.zeros(NE, np.int32)
prod_por_com = np.zeros(T_COM, np.int64); prod_por_prv = np.zeros(T_PRV, np.int64)
_tags_um = [t for t in TAGS if ARCHIVOS[t][2] == MES_ULTIMO]
_todas_prv = set(CAT_PRV)

def _filas_txt(M, nombres, i):
    return [nombres[j] for j in M.indices[M.indptr[i]:M.indptr[i + 1]]]

for k in range(N_GRUPOS):
    gi = np.nonzero(GRUPO == k)[0]                     # productos del grupo (índices globales)
    if not len(gi):
        continue
    loc = np.full(NE, -1, np.int64); loc[gi] = np.arange(len(gi))
    S = sp.csr_matrix((len(gi), NS), dtype=np.int32)
    _um = []
    for t in TAGS:
        es = L.leer_grupo(_ruta(t, 'ean_suc'), k, N_GRUPOS)
        if es is None or not len(es):
            continue
        _er = loc[EANS.get_indexer(es['ean'].cat.categories)[es['ean'].cat.codes.to_numpy()]]
        _sr = POS_SUC.reindex(es['suc'].cat.categories).to_numpy()[es['suc'].cat.codes.to_numpy()]
        S = S + sp.csr_matrix((es['n_dias'].to_numpy(np.int32), (_er, _sr)), shape=(len(gi), NS))
        if t in _tags_um:
            _um.append(pd.DataFrame({'e': _er, 'suc': _sr, 'n_dias': es['n_dias'].to_numpy(), 'precio': es['precio'].to_numpy()}))
        del es
    S.sum_duplicates()
    B = S.copy(); B.data[:] = 1
    suc_dist[gi] = B.getnnz(axis=1)
    for c, (G, cats) in DIMS.items():
        M = (B @ G).tocsr(); M.eliminate_zeros()
        n_dim[c][gi] = M.getnnz(axis=1)
        if c == 'id_comercio':
            prod_por_com += M.getnnz(axis=0)
            cadenas_txt[gi] = [', '.join(sorted(_nom_com[j] for j in M.indices[M.indptr[i]:M.indptr[i + 1]]))
                               for i in range(len(gi))]
        if c == 'provincia':
            prod_por_prv += M.getnnz(axis=0)
            for i in range(len(gi)):
                pr = _filas_txt(M, cats, i)
                if len(pr) <= T_PRV / 2:
                    prov_pres[gi[i]] = ', '.join(sorted(pr))
                else:
                    prov_falt[gi[i]] = ', '.join(sorted(_todas_prv - set(pr)))
        del M
    en_amba[gi] = (B @ AMBA_V) > 0
    SD = (S @ DIMS['id_comercio'][0]).tocsr()            # sucursal-días por comercio
    _tot = np.asarray(SD.sum(axis=1)).ravel().astype(float)
    _max = np.asarray(SD.max(axis=1).todense()).ravel().astype(float)
    _cuad = np.asarray(SD.multiply(SD).sum(axis=1)).ravel().astype(float)
    _arg = np.asarray(SD.argmax(axis=1)).ravel()
    _ok = _tot > 0
    cad_pri[gi[_ok]] = _nom_com[_arg[_ok]]
    pct_pri[gi[_ok]] = _max[_ok] / _tot[_ok] * 100
    hhi[gi[_ok]] = _cuad[_ok] / _tot[_ok] ** 2
    en_nb02[gi] = np.asarray(SD[:, _fuera_nb02].sum(axis=1)).ravel() > 0
    if _um:
        um = pd.concat(_um, ignore_index=True)
        um['_pd'] = um['precio'].astype(float) * um['n_dias']
        um = um.groupby(['e', 'suc'])[['_pd', 'n_dias']].sum()
        um = (um['_pd'] / um['n_dias']).rename('precio').reset_index()
        _pm = um.groupby('e')['precio'].agg(['median', 'mean', 'std', 'size'])
        _ix = gi[_pm.index.to_numpy()]
        precio_med[_ix] = _pm['median'].to_numpy(); precio_cv[_ix] = (_pm['std'] / _pm['mean'] * 100).to_numpy()
        suc_um[_ix] = _pm['size'].to_numpy()
        del um, _pm
    del S, B, SD, _um; gc.collect()
    print(f'  grupo {k + 1}/{N_GRUPOS}: {len(gi):,} productos ({time.time() - _t0:.0f} s) | {ram()}', flush=True)

# ── Tabla de productos ──
fin = ND - 1
_dias_vida = np.where(primer >= 0, fin - primer + 1, 0)
R = pd.DataFrame({'id_producto': EANS})
_mp = maestro_prod.reindex(EANS)
for c in ['descripcion', 'marca', 'presentacion', 'rubro', 'categoria', 'subcategoria', 'proveedor']:
    R[c] = _mp[c].to_numpy()
R['es_ean'] = np.where(_mp['ean_maestro'].notna(), _mp['ean_maestro'].to_numpy() == '1',
                       [gtin_valido(x) for x in EANS])
R['en_maestro'] = _mp['descripcion'].notna().to_numpy()
R['blacklist'] = (_mp['blacklist'] == '1').to_numpy()
del _mp
# Temporal
R['dias_periodo'] = ND
R['dias_con_precio'] = dias_precio
R['pct_dias'] = dias_precio / ND * 100
R['primer_dia'] = FECHAS[np.maximum(primer, 0)].where(primer >= 0)
R['ultimo_dia'] = FECHAS[np.maximum(ultimo, 0)].where(ultimo >= 0)
R['pct_dias_desde_aparicion'] = np.where(_dias_vida > 0, dias_precio / np.maximum(_dias_vida, 1) * 100, np.nan)
R['dias_desde_ultimo'] = np.where(ultimo >= 0, fin - ultimo, np.nan)
R['meses_con_precio'] = (mes_dias > 0).sum(axis=0)
R['meses_periodo'] = len(MESES)
R['racha_max_dias'] = racha_max
R['hueco_max_dias'] = hueco_max
R['dias_utiles'] = dias_util
R['pct_dias_utiles'] = dias_util / ND * 100
R['pct_dias_ultimo_anio'] = c365 / max(int(_u365.sum()), 1) * 100
R['pct_dias_ultimos_90'] = c90 / max(int(_u90.sum()), 1) * 100
# Sucursal
R['sucursales_total'] = NS
R['sucursales_distintas'] = suc_dist
R['pct_sucursales_distintas'] = suc_dist / NS * 100
R['pct_suc_diaria_prom'] = np.where(dias_precio > 0, sh_suc / np.maximum(dias_precio, 1) * 100, 0)
R['pct_suc_diaria_periodo'] = sh_suc / ND * 100
R['suc_diarias_prom'] = np.where(dias_precio > 0, suc_obs / np.maximum(dias_precio, 1), 0)
R['suc_diarias_min'] = np.where(dias_precio > 0, min_suc, 0)
R['sucursal_dias'] = suc_obs
R['sucursales_ultimo_mes'] = suc_um
# Comercial
R['comercios_total'] = T_COM
R['comercios'] = n_dim['id_comercio']
R['pct_comercios'] = n_dim['id_comercio'] / T_COM * 100
R['pct_com_diaria_prom'] = np.where(dias_precio > 0, sh_com / np.maximum(dias_precio, 1) * 100, 0)
R['banderas_total'] = T_BAN
R['banderas'] = n_dim['bandera']
R['pct_banderas'] = n_dim['bandera'] / T_BAN * 100
R['cadena_principal'] = cad_pri
R['pct_cadena_principal'] = pct_pri
R['hhi_cadenas'] = hhi
R['cadenas'] = cadenas_txt
R['en_universo_nb02'] = en_nb02
# Regional
R['provincias_total'] = T_PRV
R['provincias'] = n_dim['provincia']
R['pct_provincias'] = n_dim['provincia'] / T_PRV * 100
R['pct_prov_diaria_prom'] = np.where(dias_precio > 0, sh_prv / np.maximum(dias_precio, 1) * 100, 0)
R['regiones_total'] = T_REG
R['regiones'] = n_dim['region']
R['en_amba'] = en_amba
R['departamentos_total'] = T_DEP
R['departamentos'] = n_dim['depto']
R['pct_departamentos'] = n_dim['depto'] / max(T_DEP, 1) * 100
R['localidades_total'] = T_LOC
R['localidades'] = n_dim['localidad']
R['provincias_presentes'] = prov_pres
R['provincias_faltantes'] = prov_falt
# Precio (último mes)
R['precio_mediano_ultimo_mes'] = precio_med
R['cv_precio_ultimo_mes_%'] = precio_cv
# Continuidad y puntaje
R['continuo_periodo'] = R['dias_con_precio'] == ND
R['continuo_util'] = R['dias_utiles'] == ND
_comp = np.column_stack([R['pct_dias'], R['pct_suc_diaria_prom'], R['pct_comercios'], R['pct_provincias']]) / 100
R['puntaje'] = np.prod(np.clip(_comp, 0, 1), axis=1) ** 0.25 * 100
R = R.sort_values(['puntaje', 'sucursal_dias'], ascending=False).reset_index(drop=True)
R.insert(0, 'ranking', np.arange(1, len(R) + 1))
for c in [c for c in R.columns if c.startswith('pct_') or c in ('puntaje', 'suc_diarias_prom', 'hhi_cadenas',
                                                                    'cv_precio_ultimo_mes_%')]:
    R[c] = R[c].astype(float).round(4 if c == 'hhi_cadenas' else 2)
gc.collect()

print(f'\nFase 2b: {time.time() - _t0:.0f} s | {ram()}')
print(f'Productos: {len(R):,} | EAN {int(R["es_ean"].sum()):,} | códigos internos {int((~R["es_ean"]).sum()):,} | '
      f'en el maestro {int(R["en_maestro"].sum()):,}')
print(f'Con precio todos los días: {int(R["continuo_periodo"].sum()):,} | todos los días útiles '
      f'(>= {MIN_SUC_DIA_UTIL} suc y >= {MIN_PCT_DIA_UTIL}%): {int(R["continuo_util"].sum()):,}')
print(f'Puntaje: mediana {R["puntaje"].median():.1f} | >= 50: {int((R["puntaje"] >= 50).sum()):,} | '
      f'>= 75: {int((R["puntaje"] >= 75).sum()):,}')
print(R[['ranking', 'id_producto', 'descripcion', 'puntaje', 'pct_dias', 'pct_suc_diaria_prom', 'comercios',
         'provincias']].head(15).to_string(index=False))"""))

# ── CELL 7 — EXPORT ────────────────────────────────────────────────────────────
cells.append(cell_code(r"""# ============================================================
# CELDA 7 — Exportación: Excel (fila a fila, memoria constante) + parquet + csv.gz + panel mensual
# ============================================================
import datetime as _dt
import xlsxwriter
_suf = f'{F_DESDE:%Y%m%d}_{F_HASTA:%Y%m%d}'
_base = OUTPUT_DIR / f'trazabilidad_productos_{_suf}'

# Panel mensual producto x mes (solo celdas con precio)
_mi, _ei = np.nonzero(mes_dias)
panel = pd.DataFrame({'id_producto': EANS[_ei], 'mes': np.array(MESES)[_mi], 'dias_con_precio': mes_dias[_mi, _ei],
                      'suc_diarias_prom': (mes_suc[_mi, _ei] / mes_dias[_mi, _ei]).round(1)})
panel.to_parquet(OUTPUT_DIR / f'panel_mensual_productos_{_suf}.parquet', index=False)
_n_panel = len(panel)
del panel, _mi, _ei; gc.collect()
R.to_parquet(f'{_base}.parquet', index=False)
R.to_csv(f'{_base}.csv.gz', index=False, compression='gzip')

# Hojas de apoyo
_cont = R[R['continuo_periodo']].sort_values(['suc_diarias_min', 'puntaje'], ascending=False)
_cat = (R[R['es_ean'] & R['categoria'].notna()].sort_values('puntaje', ascending=False)
        .groupby(['rubro', 'categoria'], dropna=False, sort=True).head(TOP_POR_CATEGORIA)
        .sort_values(['rubro', 'categoria', 'puntaje'], ascending=[True, True, False]))
_sd = SUC.groupby('id_comercio').agg(comercio=('comercio', 'first'), banderas=('bandera', 'nunique'),
                                     sucursales=('bandera', 'size'), provincias=('provincia', 'nunique'),
                                     dias_activa_max=('dias_activa', 'max'))
_sd['productos_distintos'] = pd.Series(prod_por_com, index=CAT_COM).reindex(_sd.index)
cadenas = _sd.sort_values('sucursales', ascending=False).reset_index()
_pv = SUC.groupby('provincia').agg(region=('region', lambda s: s.mode().iat[0] if s.notna().any() else ''),
                                   sucursales=('bandera', 'size'), comercios=('id_comercio', 'nunique'),
                                   departamentos=('depto', 'nunique'))
_pv['productos_distintos'] = pd.Series(prod_por_prv, index=CAT_PRV).reindex(_pv.index)
provincias = _pv.sort_values('sucursales', ascending=False).reset_index()

resumen = pd.DataFrame([
    ('Período', f'{F_DESDE:%d/%m/%Y} a {F_HASTA:%d/%m/%Y}'),
    ('Días con dato del SEPA (denominador temporal)', ND),
    ('Días calendario sin dato', len(DIAS_CAL_SIN_DATO)),
    ('Meses', len(MESES)),
    ('Archivos leídos', len(TAGS)),
    ('Productos distintos con algún precio', len(R)),
    ('  de ellos EAN (maestro o dígito verificador)', int(R['es_ean'].sum())),
    ('  de ellos códigos internos de comercio', int((~R['es_ean']).sum())),
    ('  en el Maestro de Productos Interno', int(R['en_maestro'].sum())),
    ('Sucursales que alguna vez reportaron', NS),
    ('Sucursales activas por día (mín / mediana / máx)', f'{int(ACT_SUC.min())} / {int(np.median(ACT_SUC))} / {int(ACT_SUC.max())}'),
    ('Comercios / banderas', f'{T_COM} / {T_BAN}'),
    ('Provincias / regiones', f'{T_PRV} / {T_REG}'),
    ('Departamentos / localidades con sucursales (las del maestro con coordenadas)', f'{T_DEP} / {T_LOC}'),
    ('Productos con precio todos los días', int(R['continuo_periodo'].sum())),
    (f'Productos con todos los días útiles (>= {MIN_SUC_DIA_UTIL} sucursales y >= {MIN_PCT_DIA_UTIL}%)', int(R['continuo_util'].sum())),
    ('Productos con >= 90% de los días', int((R['pct_dias'] >= 90).sum())),
    ('Productos con puntaje >= 50 / >= 75', f'{int((R["puntaje"] >= 50).sum())} / {int((R["puntaje"] >= 75).sum())}'),
    ('Factor de precio por día (100 = centavos)', str(DIA.groupby('factor_precio').size().to_dict())),
    ('Días calendario sin dato', ', '.join(d.strftime('%d/%m/%Y') for d in DIAS_CAL_SIN_DATO[:80])),
], columns=['concepto', 'valor'])

diccionario = pd.DataFrame([
    ('ranking', 'Posición por puntaje (desempate: sucursal-días)'),
    ('id_producto', 'Código del SEPA sin ceros a la izquierda'),
    ('descripcion ... proveedor', 'Del Maestro de Productos Interno (data/); vacío si el código no está'),
    ('es_ean', 'EAN real (maestro: producto_ean = 1; si no está, dígito verificador GTIN válido). False = código interno '
               'de un comercio: el mismo número puede ser productos distintos en cadenas distintas'),
    ('dias_periodo / dias_con_precio / pct_dias', 'Días con dato del SEPA en el período; días en que al menos una sucursal '
                                                  'informó precio; porcentaje'),
    ('pct_dias_desde_aparicion', 'Días con precio sobre los días desde su primer día'),
    ('dias_desde_ultimo', 'Días con dato del SEPA entre su último día con precio y el final del período'),
    ('racha_max_dias / hueco_max_dias', 'Mayor cantidad de días seguidos (con dato del SEPA) con y sin precio desde que apareció'),
    ('dias_utiles / pct_dias_utiles', f'Días con >= {MIN_SUC_DIA_UTIL} sucursales y >= {MIN_PCT_DIA_UTIL}% de las sucursales activas ese día'),
    ('pct_dias_ultimo_anio / ultimos_90', 'Porcentaje de días con precio en los últimos 365 y 90 días calendario'),
    ('sucursales_distintas / pct_sucursales_distintas', 'Sucursales que alguna vez lo informaron, sobre todas las que alguna vez reportaron'),
    ('pct_suc_diaria_prom', 'Promedio, en los días con precio, de sucursales con precio / sucursales activas ese día (componente sucursal del puntaje)'),
    ('pct_suc_diaria_periodo', 'Lo mismo promediado sobre todos los días del período (0 en los días sin precio)'),
    ('suc_diarias_prom / suc_diarias_min / sucursal_dias', 'Sucursales por día (promedio y mínimo en días con precio) y total de sucursal-días'),
    ('comercios / pct_comercios', 'Comercios (empresa, id_comercio) donde apareció alguna vez, sobre el total (componente comercial)'),
    ('pct_com_diaria_prom', 'Promedio diario de comercios con precio / comercios activos'),
    ('banderas', 'Banderas (Vea, Disco, Jumbo... por separado)'),
    ('cadena_principal / pct_cadena_principal / hhi_cadenas', 'Comercio con más sucursal-días, su cuota y el índice de concentración (1 = una sola cadena)'),
    ('en_universo_nb02', 'Tiene precios en comercios que el nb02 no filtra (19, 2013, 3001, 4)'),
    ('provincias / pct_provincias', 'Provincias (del archivo de precios) donde apareció, sobre el total (componente regional)'),
    ('regiones', 'Regiones INDEC: GBA (AMBA por coordenadas: CABA + Buenos Aires a <= AMBA_RADIO_KM km del Obelisco), Pampeana, '
                 'Noroeste, Noreste, Cuyo, Patagonia. Las sucursales de Buenos Aires sin coordenadas no tienen región'),
    ('departamentos / localidades', 'De las sucursales del maestro con coordenadas (Georef de datos.gob.ar) y su localidad'),
    ('provincias_presentes / provincias_faltantes', 'Se lista la más corta de las dos'),
    ('precio_mediano_ultimo_mes / cv_precio_ultimo_mes_%', 'Mediana entre sucursales del precio promedio de cada sucursal en el último mes (pesos) y coeficiente de variación'),
    ('continuo_periodo / continuo_util', 'Precio todos los días del período / todos los días útiles'),
    ('puntaje', 'Media geométrica de pct_dias, pct_suc_diaria_prom, pct_comercios y pct_provincias (0-100)'),
], columns=['columna', 'definicion'])

_cols_cont = ['ranking', 'id_producto', 'descripcion', 'marca', 'rubro', 'categoria', 'puntaje', 'dias_con_precio',
              'dias_utiles', 'suc_diarias_min', 'suc_diarias_prom', 'pct_suc_diaria_prom', 'comercios', 'provincias',
              'cadena_principal', 'pct_cadena_principal', 'es_ean']
_hojas = [('Resumen', resumen), ('Ranking', R), ('Continuos_periodo', _cont[_cols_cont]),
          ('Por_categoria', _cat[_cols_cont]), ('Cadenas', cadenas), ('Provincias', provincias),
          ('Diccionario', diccionario)]

def _valor(v):
    if v is None or (isinstance(v, float) and np.isnan(v)) or v is pd.NaT:
        return None
    if isinstance(v, pd.Timestamp):
        return v.to_pydatetime()
    if isinstance(v, np.generic):
        return v.item()
    return v

out_xls = f'{_base}.xlsx'
wb = xlsxwriter.Workbook(out_xls, {'constant_memory': True, 'nan_inf_to_errors': True})
f_hdr = wb.add_format({'bold': True, 'font_color': 'white', 'bg_color': '#375623', 'text_wrap': True,
                       'valign': 'vcenter', 'align': 'center', 'font_size': 10})
f_pct = wb.add_format({'num_format': '0.0'}); f_num = wb.add_format({'num_format': '#,##0'})
f_pes = wb.add_format({'num_format': '#,##0.00'}); f_fec = wb.add_format({'num_format': 'dd/mm/yyyy'})
for nombre, df in _hojas:
    ws = wb.add_worksheet(nombre)
    fmts = []
    for j, c in enumerate(df.columns):
        fmt = (f_pct if (c.startswith('pct_') or c in ('puntaje', 'cv_precio_ultimo_mes_%')) else
               f_pes if 'precio' in c else f_fec if pd.api.types.is_datetime64_any_dtype(df[c]) else
               f_num if pd.api.types.is_integer_dtype(df[c]) else None)
        ancho = (60 if c in ('descripcion', 'cadenas', 'provincias_presentes', 'provincias_faltantes', 'definicion',
                             'valor') else 34 if c in ('concepto', 'columna') else
                 16 if c in ('id_producto', 'proveedor', 'comercio') else 12)
        ws.set_column(j, j, ancho, fmt); fmts.append(fmt)
    ws.set_row(0, 32)
    ws.freeze_panes(1, 3 if nombre in ('Ranking', 'Continuos_periodo', 'Por_categoria') else 1)
    ws.write_row(0, 0, list(df.columns), f_hdr)
    for a in range(0, len(df), 20_000):                  # de a 20 mil filas: nunca el Excel entero en memoria
        for i, fila in enumerate(df.iloc[a:a + 20_000].itertuples(index=False, name=None), start=a + 1):
            for j, v in enumerate(fila):
                v = _valor(v)
                if v is None:
                    continue
                ws.write(i, j, v, fmts[j])
    if len(df) > 1 and nombre != 'Resumen':
        ws.autofilter(0, 0, len(df), len(df.columns) - 1)
wb.close()
print(f'Excel:   {out_xls}')
print(f'Parquet: {_base}.parquet  |  CSV: {_base}.csv.gz')
print(f'Panel mensual: panel_mensual_productos_{_suf}.parquet ({_n_panel:,} filas) | {ram()}')"""))

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
out_path = os.path.join(script_dir, '09_trazabilidad_productos.ipynb')
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f'Written: {out_path}')
print(f'Cells: {len(cells)}')
