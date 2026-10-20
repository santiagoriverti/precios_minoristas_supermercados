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
1. **Lectura** (la pesada): cada archivo `MMAAAA_pais_parteN` se lee entero con pyarrow y se resume en 4 tablas chicas
   que se guardan en `output_trazabilidad/_cache_nb09/`. Un archivo ya resumido no se vuelve a leer (el último mes,
   que puede estar en curso, se relee siempre). Si Colab se corta, se vuelve a ejecutar y sigue donde quedó.
2. **Agregación:** junta todos los resúmenes y arma el ranking. No relee el SEPA.

**Salidas** (en `output_trazabilidad/`): `trazabilidad_productos_<desde>_<hasta>.xlsx` (Resumen, Ranking,
Continuos_periodo, Por_categoria, Cadenas, Provincias, Diccionario), el mismo ranking en `.parquet` y `.csv.gz`, y el
panel mensual producto × mes en `.parquet`.

**Estructura:** Config → Setup → Maestros (sucursales, Georef, productos) → Fase 1 (lectura) → Fase 2 (agregación) →
Métricas y ranking → Exportación"""))

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

TOP_POR_CATEGORIA = 10            # productos por categoría en la hoja Por_categoria"""))

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
subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyarrow', 'xlsxwriter', 'openpyxl', 'scipy', '-q'], check=False)

import zipfile, gzip, re, gc, time, json, warnings, urllib.request
from pathlib import Path
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.compute as pac
import scipy.sparse as sp

pd.set_option('display.max_columns', 60)
pd.set_option('display.width', 200)

SEPA_DIR   = Path(SEPA_DIR)
OUTPUT_DIR = Path(OUTPUT_DIR)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR  = OUTPUT_DIR / '_cache_nb09'
RES_DIR    = CACHE_DIR / 'v1'          # resúmenes por archivo (fase 1); cambiar la versión relee todo
RES_DIR.mkdir(parents=True, exist_ok=True)

print(f'SEPA_DIR:   {SEPA_DIR}')
print(f'OUTPUT_DIR: {OUTPUT_DIR}')"""))

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
# CELDA 4 — Fase 1: lectura de cada archivo del SEPA y resumen (con caché por archivo)
# ============================================================
# Cada archivo MMAAAA_pais_parteN (una fila por sucursal x producto, una columna precio_AAAAMMDD por día) se resume en:
#   ean_dia : producto x día -> sucursales, comercios y provincias con precio
#   ean_suc : producto x sucursal -> días con precio y precio promedio de esos días (pesos)
#   suc     : sucursales del archivo (comercio, bandera, sucursal, provincia) y días con algún precio
#   dia     : día -> sucursales, comercios, banderas y provincias activas, productos con precio (denominadores)
# El resumen de 'dia' se escribe último: si existe, el archivo está completo.
_PAT_SEM = re.compile(r'^(\d{4})(A|B)$', re.IGNORECASE)
_PAT_ARC = re.compile(r'^(\d{2})(\d{4})_pais_parte(\d+).*COMPLETO.*\.csv\.gz$', re.IGNORECASE)
_PAT_FECHA = re.compile(r'^precio_(\d{8})$')
ID_COLS = ['id_comercio', 'id_bandera', 'id_sucursal', 'sucursales_provincia', 'id_producto']
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

def _codigos(col, ean=False):
    # Columna diccionario de pyarrow -> (código entero por fila, valores únicos limpios). Se limpia solo el
    # diccionario (miles de valores), nunca un texto por fila: con 16 M de filas eso eran varios GB.
    a = col.combine_chunks()
    if not pa.types.is_dictionary(a.type):
        a = pac.cast(a, pa.string()).dictionary_encode()
    dic = pd.Series(a.dictionary.to_pylist(), dtype=object).fillna('').astype(str).str.strip()
    if ean:
        dic = dic.str.lstrip('0').replace('', '0')
    dic = pd.concat([dic, pd.Series([''])], ignore_index=True)              # último lugar = nulo
    idx = pac.fill_null(a.indices, len(dic) - 1).to_numpy(zero_copy_only=False).astype(np.int64)
    uniq, inv = np.unique(dic.to_numpy(dtype=object).astype(str), return_inverse=True)   # '0123' y '123' = uno
    return inv.ravel()[idx], uniq.astype(object)

def _leer_tabla(zip_path, nombre):
    with zipfile.ZipFile(zip_path) as zf:
        with zf.open(nombre) as s0, gzip.open(s0, 'rt', encoding='utf-8', errors='replace') as g:
            hdr = [c.strip() for c in g.readline().split(',')]
        cols_p = [c for c in hdr if _PAT_FECHA.match(c) and F_INI <= pd.Timestamp(c[-8:]) <= F_FIN]
        if not cols_p:
            return None, []
        tipos = {c: pa.dictionary(pa.int32(), pa.string()) for c in ID_COLS}
        for intento in ('float32', 'inferido'):
            if intento == 'float32':
                tipos.update({c: pa.float32() for c in cols_p})
            else:
                print(f'  AVISO {nombre}: precios no numéricos, se leen como texto y se convierten')
                tipos = {c: tipos[c] for c in ID_COLS}
            try:
                with zf.open(nombre) as s0, pa.CompressedInputStream(pa.PythonFile(s0, mode='r'), 'gzip') as s:
                    tb = pacsv.read_csv(s, read_options=pacsv.ReadOptions(block_size=32 << 20),
                                        convert_options=pacsv.ConvertOptions(
                                            column_types=tipos, include_columns=ID_COLS + cols_p,
                                            null_values=['NA', ''], strings_can_be_null=True))
                return tb, cols_p
            except pa.ArrowInvalid:
                if intento == 'inferido':
                    raise

def resumir_archivo(zip_path, nombre):
    tb, cols_p = _leer_tabla(zip_path, nombre)
    if tb is None:
        return None
    fechas = pd.to_datetime([c[-8:] for c in cols_p], format='%Y%m%d')

    # Códigos enteros de producto y sucursal (nada de textos por fila)
    e, eans = _codigos(tb['id_producto'], ean=True)
    e = e.astype(np.int32)
    _cod = [_codigos(tb[c]) for c in ['id_comercio', 'id_bandera', 'id_sucursal', 'sucursales_provincia']]
    tb = tb.drop_columns(ID_COLS)
    (ci, cd), (bi, bd), (si, sd), (pi, pdic) = _cod
    _k = (ci << 42) | (bi << 21) | si
    _uk, _first, st = np.unique(_k, return_index=True, return_inverse=True)
    st = st.astype(np.int32).ravel()
    suc_c, suc_b, suc_s = cd[ci[_first]], bd[bi[_first]], sd[si[_first]]
    suc_p = pdic[pi[_first]]
    ns, ne = len(_uk), len(eans)

    # Precios (float32) y máscara de precio válido
    P = np.empty((tb.num_rows, len(cols_p)), dtype=np.float32)
    for j, c in enumerate(cols_p):
        _col = tb[c]
        try:
            _col = pac.cast(_col, pa.float32())
        except Exception:
            _col = pa.array(pd.to_numeric(_col.to_pandas(), errors='coerce'), type=pa.float32())
        P[:, j] = pac.fill_null(_col, np.nan).to_numpy(zero_copy_only=False)
        tb = tb.drop_columns([c])                                    # libera la columna ya copiada
        del _col
    del tb; gc.collect()
    V = np.isfinite(P) & (P > 0)

    # Una fila por sucursal x producto (si hubiera duplicadas, la primera)
    _ke = st.astype(np.int64) * ne + e
    _u, _idx = np.unique(_ke, return_index=True)
    if len(_u) < len(_ke):
        _idx.sort()
        e, st, P, V = e[_idx], st[_idx], P[_idx], V[_idx]
    del _ke, _u, _idx

    # Comercio, bandera y provincia de cada fila, como códigos
    _cu, s_com = np.unique(suc_c, return_inverse=True)
    _bu, s_ban = np.unique(np.char.add(np.char.add(suc_c.astype(str), '|'), suc_b.astype(str)), return_inverse=True)
    _pu, s_prv = np.unique(suc_p.astype(str), return_inverse=True)
    r_com, r_prv = s_com[st], s_prv[st]
    # pares producto-comercio y producto-provincia (para contar distintos por día sin np.unique por día)
    _pc, pc_inv = np.unique(e.astype(np.int64) * len(_cu) + r_com, return_inverse=True)
    _pp, pp_inv = np.unique(e.astype(np.int64) * len(_pu) + r_prv, return_inverse=True)
    pc_e, pp_e = (_pc // len(_cu)).astype(np.int32), (_pp // len(_pu)).astype(np.int32)

    ed, dias = [], []
    for j, f in enumerate(fechas):
        v = V[:, j]
        if not v.any():
            continue
        n_suc = np.bincount(e[v], minlength=ne)
        m = np.zeros(len(_pc), bool); m[pc_inv[v]] = True
        n_com = np.bincount(pc_e[m], minlength=ne)
        m = np.zeros(len(_pp), bool); m[pp_inv[v]] = True
        n_prv = np.bincount(pp_e[m], minlength=ne)
        k = np.nonzero(n_suc)[0]
        ed.append(pd.DataFrame({'e': k.astype(np.int32), 'fecha': f, 'n_suc': n_suc[k].astype(np.int32),
                                'n_com': n_com[k].astype(np.int16), 'n_prov': n_prv[k].astype(np.int16)}))
        sa = np.zeros(ns, bool); sa[st[v]] = True
        dias.append({'fecha': f, 'n_suc': int(sa.sum()), 'n_com': int(len(np.unique(s_com[sa]))),
                     'n_ban': int(len(np.unique(s_ban[sa]))), 'n_prov': int(len(np.unique(s_prv[sa]))),
                     'n_productos': int(len(k)), 'n_precios': int(v.sum())})
    if not dias:
        return None
    ean_dia = pd.concat(ed, ignore_index=True)
    ean_dia['ean'] = pd.Categorical.from_codes(ean_dia.pop('e'), categories=eans).remove_unused_categories()

    # Producto x sucursal: días con precio y promedio de esos días
    nd = V.sum(axis=1)
    k = nd > 0
    np.putmask(P, ~V, 0)                                             # en el lugar: sin copiar la matriz
    with np.errstate(all='ignore'):
        precio = (P.sum(axis=1, dtype=np.float64)[k] / nd[k]).astype(np.float32)
    del P
    # Pesos o centavos: regla del nb02 (mediana > 10.000 -> centavos)
    fac = 100.0 if np.nanmedian(precio) > 10_000 else 1.0
    sucs = np.array([clave_suc(c, b, s) for c, b, s in zip(suc_c, suc_b, suc_s)], dtype=object)
    o = np.lexsort((st[k], e[k]))                  # ordenado por producto: el parquet pesa ~2,5 veces menos
    ean_suc = pd.DataFrame({'ean': pd.Categorical.from_codes(e[k][o], categories=eans),
                            'suc': pd.Categorical.from_codes(st[k][o], categories=sucs),
                            'n_dias': nd[k][o].astype(np.int16), 'precio': (precio / fac)[o]})
    sa_d = np.bincount(st, weights=V.any(axis=1), minlength=ns)       # filas con algún precio por sucursal
    suc_dias = np.zeros(ns, np.int16)
    for j in range(V.shape[1]):
        sa = np.zeros(ns, bool); sa[st[V[:, j]]] = True
        suc_dias += sa
    suc = pd.DataFrame({'suc': sucs, 'id_comercio': suc_c, 'id_bandera': suc_b, 'id_sucursal': suc_s,
                        'provincia_iso': suc_p, 'dias_activa': suc_dias, 'filas_con_precio': sa_d.astype(np.int32)})
    dia = pd.DataFrame(dias)
    dia['factor_precio'] = fac
    return {'ean_dia': ean_dia, 'ean_suc': ean_suc, 'suc': suc, 'dia': dia}

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

def _ruta(tag, tipo):
    return RES_DIR / f'{tag}__{tipo}.parquet'

_t0 = time.time()
_n_leidos = 0
for _tag, (_z, _n, _mes) in ARCHIVOS.items():
    if _mes != MES_ULTIMO and _ruta(_tag, 'dia').exists():
        continue
    _t = time.time()
    _r = resumir_archivo(_z, _n)
    if _r is None:
        print(f'  {_tag}: sin días en el período')
        continue
    for _tipo in ('ean_dia', 'ean_suc', 'suc', 'dia'):          # 'dia' al final = archivo completo
        _r[_tipo].to_parquet(_ruta(_tag, _tipo), index=False, compression='zstd')
    _d = _r['dia']
    print(f'  {_tag}: {len(_d)} días, {_d["n_productos"].max():,} productos/día, {_d["n_suc"].max():,} sucursales, '
          f'{len(_r["ean_suc"]):,} pares producto-sucursal ({time.time() - _t:.0f} s)')
    _n_leidos += 1
    del _r; gc.collect()
print(f'\nFase 1: {_n_leidos} archivos leídos en {(time.time() - _t0) / 60:.1f} min; '
      f'{len(ARCHIVOS) - _n_leidos} desde el caché ({RES_DIR})')"""))

# ── CELL 5 — FASE 2 ────────────────────────────────────────────────────────────
cells.append(cell_code(r"""# ============================================================
# CELDA 5 — Fase 2: agregación de todos los resúmenes (no relee el SEPA)
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
print(f'Productos distintos con algún precio: {NE:,}')

# ── Acumuladores por producto (recorrido en orden de fechas) ──
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
S = sp.csr_matrix((NE, NS), dtype=np.int32)           # producto x sucursal: días con precio
_ult_mes = []

_orden = sorted(TAGS, key=lambda t: pd.read_parquet(_ruta(t, 'dia'), columns=['fecha'])['fecha'].min())
for _i, t in enumerate(_orden):
    ed = pd.read_parquet(_ruta(t, 'ean_dia'))
    ed = ed[ed['fecha'].map(TAG_FECHA).eq(t).to_numpy()]
    _e = EANS.get_indexer(ed['ean'].astype(str))
    _d = POS_DIA.reindex(ed['fecha']).to_numpy()
    for d in np.unique(_d):                              # días del archivo, en orden
        m = _d == d
        ee = _e[m]
        n_s = np.zeros(NE, np.int64); n_s[ee] = ed['n_suc'].to_numpy()[m]
        n_c = np.zeros(NE); n_c[ee] = ed['n_com'].to_numpy()[m]
        n_p = np.zeros(NE); n_p[ee] = ed['n_prov'].to_numpy()[m]
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
    del ed
    es = pd.read_parquet(_ruta(t, 'ean_suc'))
    _er = EANS.get_indexer(es['ean'].astype(str)); _sr = POS_SUC.reindex(es['suc'].astype(str)).to_numpy()
    S = S + sp.csr_matrix((es['n_dias'].to_numpy(np.int32), (_er, _sr)), shape=(NE, NS))
    if ARCHIVOS[t][2] == MES_ULTIMO:
        _ult_mes.append(es.assign(e=_er))
    del es; gc.collect()
    if (_i + 1) % 12 == 0:
        print(f'  {_i + 1}/{len(_orden)} archivos agregados ({time.time() - _t0:.0f} s, {S.nnz:,} pares producto-sucursal)')
S.sum_duplicates()
print(f'Fase 2: {len(_orden)} archivos en {time.time() - _t0:.0f} s | {S.nnz:,} pares producto-sucursal distintos')"""))

# ── CELL 6 — MÉTRICAS ──────────────────────────────────────────────────────────
cells.append(cell_code(r"""# ============================================================
# CELDA 6 — Métricas por producto, puntaje y ranking
# ============================================================
B = S.copy(); B.data = np.ones_like(B.data)          # producto x sucursal: 1 si tuvo precio alguna vez

def indicadora(codigos):
    # sucursal x grupo (los códigos < 0 = sin dato, no cuentan)
    codigos = np.asarray(codigos)
    k = codigos >= 0
    return sp.csr_matrix((np.ones(k.sum(), np.int32), (np.nonzero(k)[0], codigos[k])),
                         shape=(NS, max(codigos.max() + 1, 1)))

def distintos(col):
    cats = pd.Categorical(SUC[col])
    G = indicadora(cats.codes)
    M = (B @ G).tocsr()
    M.eliminate_zeros()
    return M, np.asarray(cats.categories), len(cats.categories)

M_com, CAT_COM, T_COM = distintos('id_comercio')
M_ban, _, T_BAN = distintos('bandera')
M_prv, CAT_PRV, T_PRV = distintos('provincia')
M_reg, CAT_REG, T_REG = distintos('region')
M_dep, _, T_DEP = distintos('depto')
M_loc, _, T_LOC = distintos('localidad')
_amba = (B @ SUC['amba'].to_numpy(np.int32)) > 0

# Concentración: sucursal-días por comercio
SD_com = (S @ indicadora(pd.Categorical(SUC['id_comercio'], categories=CAT_COM).codes)).tocsr()
_tot = np.asarray(SD_com.sum(axis=1)).ravel().astype(float)
_max = np.asarray(SD_com.max(axis=1).todense()).ravel().astype(float)
_cuad = np.asarray(SD_com.multiply(SD_com).sum(axis=1)).ravel().astype(float)
_arg = np.asarray(SD_com.argmax(axis=1)).ravel()
_fuera_nb02 = np.array([c not in CADENAS_FILTRAR_NB02 for c in CAT_COM])
_en_nb02 = np.asarray(SD_com[:, np.nonzero(_fuera_nb02)[0]].sum(axis=1)).ravel() > 0

def listas(M, cats, nombres=None):
    out = []
    for i in range(M.shape[0]):
        idx = M.indices[M.indptr[i]:M.indptr[i + 1]]
        out.append(', '.join(sorted(nombres[cats[j]] if nombres else cats[j] for j in idx)))
    return out

_nom_com = {c: nombre_comercio(c) for c in CAT_COM}
_cadenas = listas(M_com, CAT_COM, _nom_com)
_prov_pres = listas(M_prv, CAT_PRV)
_n_prv = M_prv.getnnz(axis=1)
_todas = set(CAT_PRV)
_prov_falt = [', '.join(sorted(_todas - set(p.split(', ')))) if n > T_PRV / 2 else '' for p, n in zip(_prov_pres, _n_prv)]

# Precio del último mes: mediana y dispersión entre sucursales
_um = (pd.concat(_ult_mes, ignore_index=True) if _ult_mes
       else pd.DataFrame({'e': [], 'suc': [], 'n_dias': [], 'precio': []}))
# precio del mes por sucursal = promedio de las dos partes del mes ponderado por días
_um['_pd'] = _um['precio'] * _um['n_dias']
_um = _um.groupby(['e', _um['suc'].astype(str)])[['_pd', 'n_dias']].sum()
_um = (_um['_pd'] / _um['n_dias']).rename('precio').reset_index()
_pm = _um.groupby('e')['precio'].agg(['median', 'mean', 'std'])
_su = _um.groupby('e')['suc'].nunique()

fin = ND - 1
_dias_vida = np.where(primer >= 0, fin - primer + 1, 0)
_u365 = FECHAS >= F_HASTA - pd.Timedelta(days=364)
_u90 = FECHAS >= F_HASTA - pd.Timedelta(days=89)

R = pd.DataFrame({'id_producto': EANS})
_mp = maestro_prod.reindex(EANS)
for c in ['descripcion', 'marca', 'presentacion', 'rubro', 'categoria', 'subcategoria', 'proveedor']:
    R[c] = _mp[c].to_numpy()
R['es_ean'] = np.where(_mp['ean_maestro'].notna(), _mp['ean_maestro'].to_numpy() == '1',
                       [gtin_valido(x) for x in EANS])
R['en_maestro'] = _mp['descripcion'].notna().to_numpy()
R['blacklist'] = (_mp['blacklist'] == '1').to_numpy()
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
R['pct_dias_ultimo_anio'] = np.nan            # se completan abajo
R['pct_dias_ultimos_90'] = np.nan
# Sucursal
R['sucursales_total'] = NS
R['sucursales_distintas'] = B.getnnz(axis=1)
R['pct_sucursales_distintas'] = R['sucursales_distintas'] / NS * 100
R['pct_suc_diaria_prom'] = np.where(dias_precio > 0, sh_suc / np.maximum(dias_precio, 1) * 100, 0)
R['pct_suc_diaria_periodo'] = sh_suc / ND * 100
R['suc_diarias_prom'] = np.where(dias_precio > 0, suc_obs / np.maximum(dias_precio, 1), 0)
R['suc_diarias_min'] = np.where(dias_precio > 0, min_suc, 0)
R['sucursal_dias'] = suc_obs
R['sucursales_ultimo_mes'] = _su.reindex(range(NE)).fillna(0).astype(int).to_numpy()
# Comercial
R['comercios_total'] = T_COM
R['comercios'] = M_com.getnnz(axis=1)
R['pct_comercios'] = R['comercios'] / T_COM * 100
R['pct_com_diaria_prom'] = np.where(dias_precio > 0, sh_com / np.maximum(dias_precio, 1) * 100, 0)
R['banderas_total'] = T_BAN
R['banderas'] = M_ban.getnnz(axis=1)
R['pct_banderas'] = R['banderas'] / T_BAN * 100
R['cadena_principal'] = [_nom_com[CAT_COM[j]] if t > 0 else '' for j, t in zip(_arg, _tot)]
R['pct_cadena_principal'] = np.where(_tot > 0, _max / np.maximum(_tot, 1) * 100, np.nan)
R['hhi_cadenas'] = np.where(_tot > 0, _cuad / np.maximum(_tot, 1) ** 2, np.nan)
R['cadenas'] = _cadenas
R['en_universo_nb02'] = _en_nb02
# Regional
R['provincias_total'] = T_PRV
R['provincias'] = _n_prv
R['pct_provincias'] = _n_prv / T_PRV * 100
R['pct_prov_diaria_prom'] = np.where(dias_precio > 0, sh_prv / np.maximum(dias_precio, 1) * 100, 0)
R['regiones_total'] = T_REG
R['regiones'] = M_reg.getnnz(axis=1)
R['en_amba'] = _amba
R['departamentos_total'] = T_DEP
R['departamentos'] = M_dep.getnnz(axis=1)
R['pct_departamentos'] = R['departamentos'] / max(T_DEP, 1) * 100
R['localidades_total'] = T_LOC
R['localidades'] = M_loc.getnnz(axis=1)
R['provincias_presentes'] = [p if n <= T_PRV / 2 else '' for p, n in zip(_prov_pres, _n_prv)]
R['provincias_faltantes'] = _prov_falt
# Precio (último mes)
R['precio_mediano_ultimo_mes'] = _pm['median'].reindex(range(NE)).to_numpy()
R['cv_precio_ultimo_mes_%'] = (_pm['std'] / _pm['mean'] * 100).reindex(range(NE)).to_numpy()

# Ventanas recientes (últimos 365 y 90 días): segundo recorrido liviano, solo los archivos de la ventana
_d365 = int(_u365.sum()); _d90 = int(_u90.sum())
_ini365 = int(np.argmax(_u365)); _ini90 = int(np.argmax(_u90))
_c365 = np.zeros(NE, np.int32); _c90 = np.zeros(NE, np.int32)
for t in TAGS:
    _fx = pd.read_parquet(_ruta(t, 'dia'), columns=['fecha'])['fecha']
    if _fx.max() < FECHAS[_ini365]:
        continue
    ed = pd.read_parquet(_ruta(t, 'ean_dia'), columns=['ean', 'fecha'])
    ed = ed[ed['fecha'].map(TAG_FECHA).eq(t).to_numpy()]
    _d = POS_DIA.reindex(ed['fecha']).to_numpy(); _e = EANS.get_indexer(ed['ean'].astype(str))
    np.add.at(_c365, _e[_d >= _ini365], 1)
    np.add.at(_c90, _e[_d >= _ini90], 1)
R['pct_dias_ultimo_anio'] = _c365 / max(_d365, 1) * 100
R['pct_dias_ultimos_90'] = _c90 / max(_d90, 1) * 100

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
# CELDA 7 — Exportación: Excel + parquet + csv.gz + panel mensual
# ============================================================
_suf = f'{F_DESDE:%Y%m%d}_{F_HASTA:%Y%m%d}'
_base = OUTPUT_DIR / f'trazabilidad_productos_{_suf}'

# Panel mensual producto x mes (solo celdas con precio)
_mi, _ei = np.nonzero(mes_dias)
panel = pd.DataFrame({'id_producto': EANS[_ei], 'mes': np.array(MESES)[_mi], 'dias_con_precio': mes_dias[_mi, _ei],
                      'suc_diarias_prom': (mes_suc[_mi, _ei] / mes_dias[_mi, _ei]).round(1)})
panel.to_parquet(OUTPUT_DIR / f'panel_mensual_productos_{_suf}.parquet', index=False)
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
_sd['productos_distintos'] = pd.Series(np.asarray((M_com > 0).sum(axis=0)).ravel(), index=CAT_COM).reindex(_sd.index)
cadenas = _sd.sort_values('sucursales', ascending=False).reset_index()
_pv = SUC.groupby('provincia').agg(region=('region', lambda s: s.mode().iat[0] if s.notna().any() else ''),
                                   sucursales=('bandera', 'size'), comercios=('id_comercio', 'nunique'),
                                   departamentos=('depto', 'nunique'))
_pv['productos_distintos'] = pd.Series(np.asarray((M_prv > 0).sum(axis=0)).ravel(), index=CAT_PRV).reindex(_pv.index)
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
out_xls = f'{_base}.xlsx'
with pd.ExcelWriter(out_xls, engine='xlsxwriter', datetime_format='dd/mm/yyyy') as w:
    wb = w.book
    f_hdr = wb.add_format({'bold': True, 'font_color': 'white', 'bg_color': '#375623', 'text_wrap': True,
                           'valign': 'vcenter', 'align': 'center', 'font_size': 10})
    f_pct = wb.add_format({'num_format': '0.0'}); f_num = wb.add_format({'num_format': '#,##0'})
    f_pes = wb.add_format({'num_format': '#,##0.00'})
    for nombre, df in _hojas:
        df.to_excel(w, sheet_name=nombre, index=False)
        ws = w.sheets[nombre]
        for j, c in enumerate(df.columns):
            ws.write(0, j, c, f_hdr)
            fmt = (f_pct if (c.startswith('pct_') or c in ('puntaje', 'cv_precio_ultimo_mes_%')) else
                   f_pes if 'precio' in c else f_num if pd.api.types.is_integer_dtype(df[c]) else None)
            ancho = (60 if c in ('descripcion', 'cadenas', 'provincias_presentes', 'provincias_faltantes', 'definicion',
                                 'valor') else 34 if c in ('concepto', 'columna') else
                     16 if c in ('id_producto', 'proveedor', 'comercio') else 12)
            ws.set_column(j, j, ancho, fmt)
        ws.set_row(0, 32)
        ws.freeze_panes(1, 3 if nombre in ('Ranking', 'Continuos_periodo', 'Por_categoria') else 1)
        if len(df) > 1 and nombre != 'Resumen':
            ws.autofilter(0, 0, len(df), len(df.columns) - 1)
print(f'Excel:   {out_xls}')
print(f'Parquet: {_base}.parquet  |  CSV: {_base}.csv.gz')
print(f'Panel mensual: panel_mensual_productos_{_suf}.parquet ({len(panel):,} filas)')"""))

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
