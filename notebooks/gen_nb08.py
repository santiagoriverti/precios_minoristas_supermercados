"""Script to generate 08_canasta_diaria.ipynb — valor diario de una canasta desde 2022"""
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
cells.append(cell_md("""# SEPA — Valor diario de una canasta (2022 en adelante)

**Objetivo:** tomar una canasta de la hoja `Selección` de un Excel de canasta y devolver su valor **día por día** y el
precio diario de cada producto, de `FECHA_INICIO` a `FECHA_FIN`, con los ZIPs semestrales de `MyDrive/carga/`
(`2022A.zip` ... `2026B.zip`). **Por defecto** es la canasta fija de **pass-through**: 775 productos con precio todos los
días del 01/01/2022 al 20/10/2026, en `cantidad_01` de `output_canasta/canasta_pass_through_2026-10.xlsx` (ver
`docs/canastas_alternativas/README.md`).

**Dos precios por producto y día:**
- **Mediana nacional** de todas las observaciones (sucursales) del día, como la serie oficial del nb02 (CELDA 9).
- **Sucursales apareadas**: la media geométrica de los relativos *precio de hoy / precio anterior de la misma
  sucursal*, encadenada día a día. Si la sucursal faltó unos días (a lo sumo `MAX_DIAS_SIN_PRECIO`), su precio anterior
  se mueve con el índice del producto, como imputa el IPC los precios que faltan; los relativos fuera de [1/4, 4] no
  cuentan. No se mueve cuando cambian las sucursales que informan (del 16 al 28/07/2023 el SEPA trae la mitad de los
  comercios; desde el 01/08/2026, 8 comercios menos). Es la variable recomendada para el pass-through.

**Series de la canasta** (encadenadas día a día con productos apareados y llevadas a pesos en el día ancla, el último con
todos los productos): `valor_canasta` (medianas) y `valor_canasta_apareado` (sucursales apareadas). Los días con
cobertura incompleta del SEPA se marcan (`cobertura_incompleta`), no se borran.

**Desagregaciones** (sucursales apareadas, la misma canasta en todas):
- **Nivel general vs provincias**: el índice apareado de cada producto se calcula también con las sucursales de cada
  provincia (código ISO de `sucursales_provincia`, como el nb09) y se lleva a pesos con la mediana de la provincia. Si una
  provincia no tiene pares de un producto un día, ese día el producto se mueve como en el país (`peso_imputado_%`).
- **Nivel general vs grandes rubros**: la canasta por `tipo` (Alimentos, Bebidas sin alcohol, Limpieza del hogar...), con
  su peso en el valor de la canasta y su incidencia en la variación del nivel general.

**Caché:** cada mes cerrado queda en `output_canasta/_cache/diaria_v3_<clave>/`: `AAAA-MM.parquet`, `prov_AAAA-MM.parquet`
(producto × provincia × día) y `estado_AAAA-MM.parquet` (el último precio de cada sucursal y producto, para empalmar con
el mes siguiente). La clave son los EANs de la canasta: cambiar cantidades no relee. La primera corrida con los 775
productos lee 58 meses (~1,5 min por mes en una PC, ~2-3 h en el Colab gratuito, ~1,5 GB de RAM); las siguientes, solo
el último mes. Si Colab se corta, se vuelve a ejecutar y sigue donde quedó.

**Salidas** (en `output_canasta/`): `canasta_diaria_<canasta>_<desde>_<hasta>.xlsx` (Serie_diaria, Resumen_mensual,
Provincias_resumen, Provincias_mensual, Provincias_diario, Rubros_resumen, Rubros_mensual, Rubros_incidencia,
Rubros_diario, Composicion, Indices_por_grupo, Precios_diarios, Precios_apareados, Notas),
`panel_diario_<canasta>_<desde>_<hasta>` (`.parquet` y `.csv.gz`: producto × día con los dos precios, para las
regresiones) y `series_desagregadas_<canasta>_<desde>_<hasta>.parquet` (nivel general, provincias y rubros × día).

**Estructura:** Config → Setup → Canasta desde Excel → Lectura de ZIPs (con caché) → Series diarias y desagregaciones →
Gráficos → Exportación"""))

# ── CELL 1 — CONFIG ────────────────────────────────────────────────────────────
cells.append(cell_code(r"""# ===========================================================
# CONFIGURACIÓN — Modificar solo esta sección
# ===========================================================
SEPA_DIR   = '/content/drive/MyDrive/carga'                  # ZIPs semestrales 2022A.zip ... 2026B.zip
OUTPUT_DIR = '/content/drive/MyDrive/carga/output_canasta'   # Excel de canasta, caché y salidas

# Canasta: columna de la hoja Selección y Excel. Por defecto, la canasta fija de pass-through (775 productos con precio
# todos los días del 01/01/2022 al 20/10/2026) que docs/canastas_alternativas/marcar_canasta_pass_through_colab.py pone
# en cantidad_01. Para otra canasta: CANASTA_EXCEL = None (el canasta_representativa_*.xlsx más nuevo de OUTPUT_DIR).
CANASTA_COL    = 'cantidad_01'
CANASTA_EXCEL  = '/content/drive/MyDrive/carga/output_canasta/canasta_pass_through_2026-10.xlsx'
NOMBRE_CANASTA = None              # None = automático: 'Pass-through' si el Excel es canasta_pass_through_*; si no, el
                                   # de la columna (cantidad_01 = Vulnerable, cantidad_03 = Media...)
FECHA_INICIO   = '2022-01-01'
FECHA_FIN      = '2026-10-20'      # None = hasta el último día de los ZIPs
USE_CACHE      = True

# Sucursales apareadas: si una sucursal faltó, su último precio cuenta si es de hace a lo sumo estos días (movido con el
# índice del producto desde entonces); los relativos fuera de [1/RELATIVO_MAX, RELATIVO_MAX] son errores de carga y no
# cuentan.
MAX_DIAS_SIN_PRECIO = 31
RELATIVO_MAX = 4.0

# Día con cobertura incompleta: observaciones de la canasta por debajo de esta fracción de la mediana de su mes.
MIN_COBERTURA_DIA = 0.75

# Aviso si un eslabón diario de la canasta se mueve más que esto: suele ser un error de carga del SEPA o un cambio de
# unidades (pesos/centavos) en un mes.
ALERTA_ESLABON = 0.15"""))

# ── CELL 2 — SETUP ─────────────────────────────────────────────────────────────
cells.append(cell_code(r"""# ============================================================
# CELDA 2 — Montar Drive + imports
# ============================================================
try:
    import google.colab
    from google.colab import drive
    drive.mount('/content/drive')
    print('Google Drive montado')
except ImportError:
    print('Entorno local')

import subprocess, sys
subprocess.run([sys.executable, '-m', 'pip', 'install', 'openpyxl', 'pyarrow', 'xlsxwriter', 'psutil', '-q'], check=False)

import zipfile, gzip, io, re, gc, hashlib, time, warnings
from pathlib import Path
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import psutil
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

pd.set_option('display.max_columns', 50)
pd.set_option('display.float_format', '{:,.2f}'.format)

SEPA_DIR   = Path(SEPA_DIR)
OUTPUT_DIR = Path(OUTPUT_DIR)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR  = OUTPUT_DIR / '_cache'
if USE_CACHE:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

def ram():
    return (f'RAM: proceso {psutil.Process().memory_info().rss / 1e9:.1f} GB, '
            f'libre {psutil.virtual_memory().available / 1e9:.1f} GB')

print(f'SEPA_DIR:   {SEPA_DIR}')
print(f'OUTPUT_DIR: {OUTPUT_DIR}')"""))

# ── CELL 3 — CANASTA ───────────────────────────────────────────────────────────
cells.append(cell_code(r"""# ============================================================
# CELDA 3 — Canasta desde el Excel (columna CANASTA_COL de la hoja Selección)
# ============================================================
import glob as _glob
import unicodedata as _ud

if CANASTA_EXCEL:
    CANASTA_EXCEL = Path(CANASTA_EXCEL)
    if not CANASTA_EXCEL.exists():
        _hay = sorted(p.name for p in OUTPUT_DIR.glob('canasta_*.xlsx'))
        raise FileNotFoundError(
            f'No existe {CANASTA_EXCEL}.\nExcel de canasta en {OUTPUT_DIR}: {_hay}\n'
            'La canasta de pass-through la arma docs/canastas_alternativas/marcar_canasta_pass_through_colab.py (su salida '
            'canasta_pass_through_AAAA-MM.xlsx va a output_canasta/). Para otra canasta: CANASTA_EXCEL = None.')
else:
    _pat = sorted(_glob.glob(str(OUTPUT_DIR / 'canasta_representativa_*.xlsx')), reverse=True)
    if not _pat:
        raise FileNotFoundError(f'No se encontró canasta_representativa_*.xlsx en {OUTPUT_DIR}')
    CANASTA_EXCEL = Path(_pat[0])
print(f'Excel de canasta: {CANASTA_EXCEL.name}')

for _sn in ['Selección', 'Seleccion']:
    try:
        sel = pd.read_excel(CANASTA_EXCEL, sheet_name=_sn, dtype={'id_producto': str})
        break
    except Exception:
        pass
else:
    raise ValueError(f'No se encontró la hoja Seleccion/Selección en {CANASTA_EXCEL.name}')

if CANASTA_COL not in sel.columns:
    raise ValueError(f'La hoja Selección no tiene la columna {CANASTA_COL}')

sel['id_producto'] = sel['id_producto'].str.strip().str.zfill(13)
sel['ean_norm']    = sel['id_producto'].str.lstrip('0')
desc_col  = next((c for c in ['descripcion','descripcion_producto','nombre'] if c in sel.columns), sel.columns[3])
cat_col   = next((c for c in ['categoria','rubro'] if c in sel.columns), None)
grupo_col = next((c for c in ['pt_grupo_ipc', 'grupo_ipc'] if c in sel.columns), None)   # canasta de pass-through
tipo_col  = next((c for c in ['pt_tipo', 'tipo'] if c in sel.columns), None)

CANASTA_NAMES = {'cantidad_01': 'Vulnerable', 'cantidad_02': 'Popular', 'cantidad_03': 'Media',
                 'cantidad_04': 'Media Alta', 'cantidad_05': 'Celíaca Media', 'cantidad_06': 'Vegana Básica',
                 'cantidad_07': 'Continua 2022'}   # 28 productos con dato todos los días desde 01/01/2022
CANASTA_SHORT = {'cantidad_01': 'vulnerable', 'cantidad_02': 'popular', 'cantidad_03': 'media',
                 'cantidad_04': 'media_alta', 'cantidad_05': 'celiaca_media', 'cantidad_06': 'vegana_basica',
                 'cantidad_07': 'continua_2022'}
if not NOMBRE_CANASTA:
    NOMBRE_CANASTA = ('Pass-through' if CANASTA_EXCEL.name.lower().startswith('canasta_pass_through')
                      else CANASTA_NAMES.get(CANASTA_COL, CANASTA_COL))
SHORT_CANASTA = (CANASTA_SHORT[CANASTA_COL] if NOMBRE_CANASTA == CANASTA_NAMES.get(CANASTA_COL) else
                 re.sub(r'[^a-z0-9]+', '_', _ud.normalize('NFKD', NOMBRE_CANASTA).encode('ascii', 'ignore')
                        .decode().lower()).strip('_'))

_qty = pd.to_numeric(sel[CANASTA_COL], errors='coerce').fillna(0)
_cols = ['id_producto', 'ean_norm', desc_col] + [c for c in (cat_col, grupo_col, tipo_col) if c]
composicion = sel.loc[_qty > 0, _cols].copy()
composicion['cantidad'] = _qty[_qty > 0].values
composicion = (composicion.rename(columns={desc_col: 'descripcion', **({cat_col: 'categoria'} if cat_col else {}),
                                           **({grupo_col: 'grupo'} if grupo_col else {}),
                                           **({tipo_col: 'tipo'} if tipo_col else {})})
               .drop_duplicates('ean_norm').reset_index(drop=True))
if composicion.empty:
    raise ValueError(f'La columna {CANASTA_COL} no tiene productos con cantidad > 0')

QTY  = composicion.set_index('ean_norm')['cantidad'].astype(float)
EANS = set(QTY.index)
EAN_LIST = np.array(sorted(EANS), dtype=object)   # código de cada producto en las matrices del lector
NE = len(EAN_LIST)
print(f'Canasta {NOMBRE_CANASTA} ({CANASTA_COL}): {NE} productos (cantidades que suman {QTY.sum():,.1f})'
      + (f' | {composicion["grupo"].nunique()} grupos' if 'grupo' in composicion else ''))"""))

# ── CELL 4 — LECTURA ───────────────────────────────────────────────────────────
cells.append(cell_code(r"""# ============================================================
# CELDA 4 — Lectura de los ZIPs semestrales: por producto y día, mediana nacional y relativos de sucursales apareadas
# ============================================================
# Mismo universo que la serie del nb02 (CELDA 9): todas las observaciones de los archivos COMPLETO, sin filtro de
# sucursales. Para ir rápido se filtran las LÍNEAS del CSV por EAN antes de parsear (de ~15 M de líneas por archivo
# quedan ~1 M con la canasta de pass-through), y cada archivo (media quincena) se procesa y se suelta.
_PAT_SEM = re.compile(r'^(\d{4})(A|B)$', re.IGNORECASE)
_PAT_ARC = re.compile(r'^(\d{2})(\d{4})_pais_parte(\d+).*COMPLETO.*\.csv\.gz$', re.IGNORECASE)
_PAT_FECHA = re.compile(r'^precio_(\d{8})$')
F_INI = pd.Timestamp(FECHA_INICIO)
F_FIN = pd.Timestamp(FECHA_FIN) if FECHA_FIN else pd.Timestamp('2100-01-01')
_D0 = pd.Timestamp('2000-01-01')
_ID = {'id_comercio', 'id_bandera', 'id_sucursal', 'id_producto', 'sucursales_provincia'}

# Provincias: código ISO 3166-2:AR de sucursales_provincia, como el nb09 (las escritas con el nombre se pasan al código;
# las vacías o no reconocidas cuentan para el nivel general, no para las provincias)
ISO_PROV = {'AR-C': 'CABA', 'AR-B': 'Buenos Aires', 'AR-K': 'Catamarca', 'AR-H': 'Chaco', 'AR-U': 'Chubut',
            'AR-X': 'Córdoba', 'AR-W': 'Corrientes', 'AR-E': 'Entre Ríos', 'AR-P': 'Formosa', 'AR-Y': 'Jujuy',
            'AR-L': 'La Pampa', 'AR-F': 'La Rioja', 'AR-M': 'Mendoza', 'AR-N': 'Misiones', 'AR-Q': 'Neuquén',
            'AR-R': 'Río Negro', 'AR-A': 'Salta', 'AR-J': 'San Juan', 'AR-D': 'San Luis', 'AR-Z': 'Santa Cruz',
            'AR-S': 'Santa Fe', 'AR-G': 'Santiago del Estero', 'AR-V': 'Tierra del Fuego', 'AR-T': 'Tucumán'}
NOMBRE_ISO = {'caba': 'AR-C', 'ciudad autonoma de buenos aires': 'AR-C', 'capital federal': 'AR-C',
              'buenos aires': 'AR-B', 'catamarca': 'AR-K', 'chaco': 'AR-H', 'chubut': 'AR-U', 'cordoba': 'AR-X',
              'corrientes': 'AR-W', 'entre rios': 'AR-E', 'formosa': 'AR-P', 'jujuy': 'AR-Y', 'la pampa': 'AR-L',
              'la rioja': 'AR-F', 'mendoza': 'AR-M', 'misiones': 'AR-N', 'neuquen': 'AR-Q', 'rio negro': 'AR-R',
              'salta': 'AR-A', 'san juan': 'AR-J', 'san luis': 'AR-D', 'santa cruz': 'AR-Z', 'santa fe': 'AR-S',
              'santiago del estero': 'AR-G', 'tierra del fuego': 'AR-V', 'tucuman': 'AR-T'}
PROV_LIST = np.array(sorted(ISO_PROV), dtype=object)   # código de cada provincia en las matrices del lector
NP = len(PROV_LIST)
_COD_PROV = {c: i for i, c in enumerate(PROV_LIST)}

def iso_provincia(v):
    v = str(v).strip()
    if v.upper() in ISO_PROV:
        return v.upper()
    k = _ud.normalize('NFKD', v).encode('ascii', 'ignore').decode().lower()
    k = re.sub(r'\s+', ' ', re.sub(r',.*$', '', k)).strip()
    return NOMBRE_ISO.get(re.sub(r'^provincia (de |del )?', '', k), '')

def detectar_semestres():
    result = []
    for z in sorted(SEPA_DIR.glob('*.zip')):
        m = _PAT_SEM.match(z.stem)
        if m:
            result.append((z, int(m.group(1)), m.group(2).upper()))
    return result

def _dias_archivo(z, nombre):
    with zipfile.ZipFile(z) as zf, zf.open(nombre) as s, gzip.open(s, 'rt', encoding='utf-8', errors='replace') as g:
        return sum(1 for c in g.readline().split(',') if c.strip().startswith('precio_'))

def archivos_por_mes():
    # {mes: [(zip, archivo), ...]} con UN archivo por parte del mes. Si hay más de uno para la misma parte (2024B.zip
    # trae 082024_pais_parte1COMPLETO.csv.gz, días 1 a 5, y ...COMPLETOb.csv.gz, días 1 a 15, con los mismos precios),
    # se usa el que cubre más días, como el nb09: sumarlos contaba dos veces las observaciones del 1 al 5/08/2024.
    cand = {}
    for z, _a, _s in detectar_semestres():
        with zipfile.ZipFile(z) as zf:
            for info in zf.infolist():
                m = _PAT_ARC.match(Path(info.filename).name)
                if m:
                    cand.setdefault((f'{m.group(2)}-{m.group(1)}', int(m.group(3))), []).append(
                        (z, info.filename, info.file_size))
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

def _leer_archivo(z, nombre):
    # Líneas del CSV con productos de la canasta -> código del producto, sucursal, fechas y precios (fila x día)
    with zipfile.ZipFile(z) as zf, zf.open(nombre) as s, gzip.open(s, 'rt', encoding='utf-8', errors='replace') as g:
        hdr = g.readline()
        i_ean = [c.strip() for c in hdr.split(',')].index('id_producto')
        keep = []
        for line in g:
            p = line.split(',', i_ean + 2)
            if len(p) > i_ean and p[i_ean].strip().strip('"').lstrip('0') in EANS:
                keep.append(line)
    if not keep:
        return None
    _usar = lambda c: c.strip() in _ID or bool(_PAT_FECHA.match(c.strip()) and F_INI <= pd.Timestamp(c.strip()[-8:]) <= F_FIN)
    df = pd.read_csv(io.StringIO(hdr + ''.join(keep)), dtype=str, low_memory=False, usecols=_usar)
    del keep
    df.columns = [c.strip() for c in df.columns]
    cols_p = [c for c in df.columns if _PAT_FECHA.match(c)]
    if not cols_p:
        return None
    e = pd.Categorical(df['id_producto'].str.strip().str.lstrip('0'), categories=EAN_LIST).codes
    _t = {c: df[c].fillna('').str.strip() for c in ('id_comercio', 'id_bandera', 'id_sucursal')}
    suc = (_t['id_comercio'] + '|' + _t['id_bandera'] + '|'
           + _t['id_sucursal'].str.lstrip('0').replace('', '0')).to_numpy(object)
    _pv = df['sucursales_provincia'].fillna('') if 'sucursales_provincia' in df else pd.Series('', index=df.index)
    prov = _pv.map({v: _COD_PROV.get(iso_provincia(v), -1) for v in _pv.unique()}).to_numpy(np.int64)
    P = np.column_stack([pd.to_numeric(df[c], errors='coerce').to_numpy(float) for c in cols_p])
    del df
    P[~(P > 0)] = np.nan
    ok = e >= 0
    return {'e': e[ok].astype(np.int64), 'suc': suc[ok], 'prov': prov[ok], 'P': P[ok],
            'fechas': pd.to_datetime([c[-8:] for c in cols_p], format='%Y%m%d')}

def _agregar_dia(e, x):
    # por producto: mediana, observaciones y promedio sin los valores a más de 4 veces de la mediana (criterio del nb02)
    g = pd.DataFrame({'e': e, 'p': x})
    a = g.groupby('e')['p'].agg(['median', 'size'])
    m = a['median'].reindex(g['e']).to_numpy()
    ok = (x >= m / 4) & (x <= m * 4)
    prom = g[ok].groupby('e')['p'].mean()
    return a.index.to_numpy(), a['median'].to_numpy(), a['size'].to_numpy(), prom.reindex(a.index).to_numpy()

def _estado_vacio():
    return {'pares': pd.DataFrame({'precio': pd.Series(dtype=float), 'dia': pd.Series(dtype=np.int64),
                                   'idx': pd.Series(dtype=float), 'idx_p': pd.Series(dtype=float)}),
            'indice': np.ones(NE), 'indice_prov': np.ones((NE, NP))}

def leer_mes(archivos, estado):
    # Un mes -> [fecha, ean_norm, precio_mediano, n_obs, precio_promedio, suma_log_rel, n_pares], lo mismo por
    # provincia [fecha, e, prov, precio_mediano, n_obs, suma_log_rel, n_pares] (e y prov: posición en EAN_LIST y
    # PROV_LIST) y el estado al cerrar el mes: el índice apareado de cada producto (nacional y por provincia) y, por
    # sucursal x producto, el último precio de los últimos MAX_DIAS_SIN_PRECIO días con su día y los dos índices ese día.
    # Relativo de una sucursal = precio de hoy / su último precio movido con el índice del producto desde entonces
    # (imputación del IPC para los precios que faltan): una sucursal que faltó unos días aporta solo lo que se apartó
    # del resto, sin volver a contar la variación que ya entró por las otras sucursales esos días. En cada provincia,
    # con el índice de la provincia; si la provincia no tiene pares de un producto ese día, se mueve como el nacional.
    partes = [r for r in (_leer_archivo(z, n) for z, n in archivos) if r is not None]
    if not partes:
        return None, None, estado
    partes.sort(key=lambda r: r['fechas'][0])
    # Pesos o centavos: misma regla que la CELDA 9 del nb02 (mediana de todas las observaciones del mes > 10.000)
    _v = np.concatenate([r['P'][np.isfinite(r['P'])] for r in partes])
    fac = 100.0 if len(_v) and np.median(_v) > 10_000 else 1.0
    del _v
    if estado is None:
        estado = _estado_vacio()
    pares, I, IP = estado['pares'], estado['indice'].copy(), estado['indice_prov'].copy()
    filas, filas_p = [], []
    while partes:
        r = partes.pop(0)
        P, e, pr = r['P'] / fac, r['e'], r['prov']
        dia = np.asarray((r['fechas'] - _D0).days, dtype=np.int64)
        # sucursal x producto: si el SEPA repite la fila, para los relativos cuenta el promedio de las repetidas
        clave = pd.Series(r['suc']) + '#' + pd.Series(EAN_LIST[e])
        cod, uni = pd.factorize(clave)
        if len(uni) < len(clave):
            Pu = pd.DataFrame(P).groupby(cod).mean().to_numpy()
            _pri = np.unique(cod, return_index=True)[1]
            eu, pu = e[_pri], pr[_pri]
        else:
            Pu, eu, pu = P, e, pr
        kp = eu * NP + np.maximum(pu, 0)          # producto x provincia (solo vale donde pu >= 0)
        pos = pares.index.get_indexer(uni) if len(pares) else np.full(len(uni), -1)
        ult_p = np.where(pos >= 0, pares['precio'].to_numpy()[pos], np.nan) if len(pares) else np.full(len(uni), np.nan)
        ult_d = (np.where(pos >= 0, pares['dia'].to_numpy()[pos], -10**9) if len(pares)
                 else np.full(len(uni), -10**9, dtype=np.int64))
        ult_i = np.where(pos >= 0, pares['idx'].to_numpy()[pos], np.nan) if len(pares) else np.full(len(uni), np.nan)
        ult_ip = np.where(pos >= 0, pares['idx_p'].to_numpy()[pos], np.nan) if len(pares) else np.full(len(uni), np.nan)
        for j, f in enumerate(r['fechas']):
            x = P[:, j]
            v = np.isfinite(x)
            if not v.any():
                continue
            ee, med, nobs, prom = _agregar_dia(e[v], x[v])
            xu = Pu[:, j]
            vu = np.isfinite(xu)
            par = vu & np.isfinite(ult_p) & (ult_d >= dia[j] - MAX_DIAS_SIN_PRECIO)
            rel = xu[par] / ult_p[par] * ult_i[par] / I[eu[par]]
            k = (rel >= 1 / RELATIVO_MAX) & (rel <= RELATIVO_MAX)
            slr = np.bincount(eu[par][k], weights=np.log(rel[k]), minlength=NE)
            npar = np.bincount(eu[par][k], minlength=NE)
            _con = npar > 0
            I[_con] *= np.exp(slr[_con] / npar[_con])
            # provincias: los mismos pares, con el índice de cada provincia
            _ln_nac = np.where(_con, slr / np.maximum(npar, 1), 0.0)
            parp = par & (pu >= 0)
            relp = xu[parp] / ult_p[parp] * ult_ip[parp] / IP.ravel()[kp[parp]]
            kk = (relp >= 1 / RELATIVO_MAX) & (relp <= RELATIVO_MAX)
            slrp = np.bincount(kp[parp][kk], weights=np.log(relp[kk]), minlength=NE * NP)
            nparp = np.bincount(kp[parp][kk], minlength=NE * NP)
            IP *= np.exp(np.where(nparp > 0, slrp / np.maximum(nparp, 1), np.repeat(_ln_nac, NP))).reshape(NE, NP)
            ult_p[vu] = xu[vu]
            ult_d[vu] = dia[j]
            ult_i[vu] = I[eu[vu]]
            ult_ip[vu] = np.where(pu[vu] >= 0, IP.ravel()[kp[vu]], np.nan)
            filas.append(pd.DataFrame({'fecha': f, 'ean_norm': EAN_LIST[ee], 'precio_mediano': med, 'n_obs': nobs,
                                       'precio_promedio': prom, 'suma_log_rel': slr[ee], 'n_pares': npar[ee]}))
            vp = v & (pr >= 0)
            ap = pd.DataFrame({'k': e[vp] * NP + pr[vp], 'p': x[vp]}).groupby('k')['p'].agg(['median', 'size'])
            ka = ap.index.to_numpy()
            filas_p.append(pd.DataFrame({'fecha': f, 'e': (ka // NP).astype(np.int16), 'prov': (ka % NP).astype(np.int8),
                                         'precio_mediano': ap['median'].to_numpy(), 'n_obs': ap['size'].to_numpy(np.int32),
                                         'suma_log_rel': slrp[ka], 'n_pares': nparp[ka].astype(np.int32)}))
        nuevo = pd.DataFrame({'precio': ult_p, 'dia': ult_d, 'idx': ult_i, 'idx_p': ult_ip}, index=uni)
        nuevo = nuevo[np.isfinite(nuevo['precio'])]
        if len(pares):
            nuevo = pd.concat([pares[~pares.index.isin(uni)], nuevo])
        pares = nuevo[nuevo['dia'] >= dia[-1] - MAX_DIAS_SIN_PRECIO]
        del r, P, Pu, clave, cod, uni, ult_p, ult_d, ult_i, ult_ip
    gc.collect()
    if not filas:
        return None, None, {'pares': pares, 'indice': I, 'indice_prov': IP}
    return (pd.concat(filas, ignore_index=True), pd.concat(filas_p, ignore_index=True),
            {'pares': pares, 'indice': I, 'indice_prov': IP})

def guardar_estado(est, ruta):
    # pares sucursal x producto y, en los metadatos del parquet, el índice apareado de cada producto (nacional y por
    # provincia)
    import pyarrow as pa, pyarrow.parquet as pq, json
    p = est['pares']
    k = p.index.to_series().str.rsplit('#', n=1, expand=True)
    t = pa.Table.from_pandas(pd.DataFrame({'suc': k[0].to_numpy(), 'ean': k[1].to_numpy(), 'precio': p['precio'].to_numpy(),
                                           'dia': p['dia'].to_numpy(np.int32), 'idx': p['idx'].to_numpy(),
                                           'idx_p': p['idx_p'].to_numpy()}),
                             preserve_index=False)
    meta = dict(t.schema.metadata or {})
    meta[b'nb08_indice'] = json.dumps(dict(zip(EAN_LIST.tolist(), est['indice'].tolist()))).encode()
    meta[b'nb08_indice_prov'] = json.dumps({'provincias': PROV_LIST.tolist(),
                                            'indice': dict(zip(EAN_LIST.tolist(), est['indice_prov'].tolist()))}).encode()
    pq.write_table(t.replace_schema_metadata(meta), ruta)

def cargar_estado(ruta):
    import pyarrow.parquet as pq, json
    t = pq.read_table(ruta)
    d = t.to_pandas()
    ind = json.loads(t.schema.metadata[b'nb08_indice'])
    ipr = json.loads(t.schema.metadata[b'nb08_indice_prov'])
    assert ipr['provincias'] == PROV_LIST.tolist()
    return {'pares': pd.DataFrame({'precio': d['precio'].to_numpy(float), 'dia': d['dia'].to_numpy(np.int64),
                                   'idx': d['idx'].to_numpy(float), 'idx_p': d['idx_p'].to_numpy(float)},
                                  index=(d['suc'] + '#' + d['ean']).to_numpy(object)),
            'indice': np.array([ind.get(e, 1.0) for e in EAN_LIST], dtype=float),
            'indice_prov': np.array([ipr['indice'].get(e, [1.0] * NP) for e in EAN_LIST], dtype=float)}

# Meses disponibles -> archivos
_mapa_mes = archivos_por_mes()
MESES = [m for m in sorted(_mapa_mes) if F_INI.strftime('%Y-%m') <= m <= F_FIN.strftime('%Y-%m')]
if not MESES:
    raise RuntimeError(f'No hay ZIPs semestrales (AAAAA.zip / AAAAB.zip) con meses entre {F_INI:%Y-%m} y {F_FIN:%Y-%m} en {SEPA_DIR}')
print(f'Meses: {MESES[0]} -> {MESES[-1]} ({len(MESES)})')
_falta = [str(p) for p in pd.period_range(MESES[0], MESES[-1], freq='M').astype(str) if p not in _mapa_mes]
if _falta:
    print(f'  AVISO: faltan meses en los ZIPs: {_falta}')

# Caché por mes (solo meses cerrados: el último se relee siempre, puede estar en curso)
_clave = hashlib.md5('|'.join(sorted(EANS)).encode()).hexdigest()[:8]
_cache_mes = CACHE_DIR / f'diaria_v3_{_clave}'
if USE_CACHE:
    _cache_mes.mkdir(parents=True, exist_ok=True)

def _p_mes(m):
    return _cache_mes / f'{m}.parquet'

def _p_prov(m):
    return _cache_mes / f'prov_{m}.parquet'

def _p_est(m):
    return _cache_mes / f'estado_{m}.parquet'

# Producto x provincia x día: se acumula mes a mes en matrices (días calendario x productos x provincias) para no
# juntar ~30 M de filas. De las medianas de cada provincia alcanza la del último día con dato (lleva el índice a pesos).
_CAL = pd.date_range(F_INI, min(F_FIN, pd.Period(MESES[-1]).end_time.normalize()))
SLR_P = np.zeros((len(_CAL), NE, NP))
NPAR_P = np.zeros((len(_CAL), NE, NP), dtype=np.int32)
OBS_P = np.zeros((len(_CAL), NP), dtype=np.int64)
MED_P_ULT = np.full((NE, NP), np.nan)
DIA_P_ULT = np.full((NE, NP), -1, dtype=np.int64)

def acumular_prov(d):
    d = d[(d['fecha'] >= F_INI) & (d['fecha'] <= F_FIN)]
    t = _CAL.get_indexer(d['fecha'])
    e, p = d['e'].to_numpy(np.int64), d['prov'].to_numpy(np.int64)
    SLR_P[t, e, p] = d['suma_log_rel'].to_numpy()
    NPAR_P[t, e, p] = d['n_pares'].to_numpy()
    np.add.at(OBS_P, (t, p), d['n_obs'].to_numpy())
    u = d.assign(t=t).sort_values('t', kind='stable').drop_duplicates(['e', 'prov'], keep='last')
    MED_P_ULT[u['e'].to_numpy(np.int64), u['prov'].to_numpy(np.int64)] = u['precio_mediano'].to_numpy()
    DIA_P_ULT[u['e'].to_numpy(np.int64), u['prov'].to_numpy(np.int64)] = u['t'].to_numpy()

# Meses a leer del SEPA: los que no están en caché y el último. Cada uno necesita el estado del mes anterior (último
# precio de cada sucursal): si no está guardado, se relee ese mes también.
A_LEER = {m for m in MESES if not (USE_CACHE and m != MESES[-1] and _p_mes(m).exists() and _p_prov(m).exists())}
_cambio = True
while _cambio:
    _cambio = False
    for _k in range(1, len(MESES)):
        if MESES[_k] in A_LEER and MESES[_k - 1] not in A_LEER and not _p_est(MESES[_k - 1]).exists():
            A_LEER.add(MESES[_k - 1])
            _cambio = True
print(f'Caché ({_cache_mes.name}): {len(MESES) - len(A_LEER)} meses guardados, {len(A_LEER)} por leer del SEPA | {ram()}')

_t0 = time.time()
_lista, estado = [], None
for _k, _m in enumerate(MESES):
    if _m not in A_LEER:
        _lista.append(pd.read_parquet(_p_mes(_m)))
        acumular_prov(pd.read_parquet(_p_prov(_m)))
        estado = None
        continue
    if estado is None and _k > 0 and _p_est(MESES[_k - 1]).exists():
        estado = cargar_estado(_p_est(MESES[_k - 1]))
    _t = time.time()
    _agg, _aggp, estado = leer_mes(_mapa_mes[_m], estado)
    if _agg is None:
        print(f'  {_m}: sin datos de la canasta')
        continue
    _cerrado = _m != MESES[-1]
    if USE_CACHE and _cerrado:
        _agg.to_parquet(_p_mes(_m), index=False)
        _aggp.to_parquet(_p_prov(_m), index=False)
        guardar_estado(estado, _p_est(_m))
    _lista.append(_agg)
    acumular_prov(_aggp)
    del _aggp
    print(f'  {_m}: {_agg["fecha"].nunique()} días, {_agg["ean_norm"].nunique()}/{NE} productos, '
          f'{int(_agg["n_obs"].sum()):,} observaciones ({time.time() - _t:.0f} s'
          f'{", guardado en caché" if USE_CACHE and _cerrado else ""}) | {ram()}', flush=True)

precios_dia = pd.concat(_lista, ignore_index=True)
precios_dia = precios_dia[(precios_dia['fecha'] >= F_INI) & (precios_dia['fecha'] <= F_FIN)].reset_index(drop=True)
del _lista; gc.collect()
print(f'\nLectura: {time.time() - _t0:.0f} s | {precios_dia["fecha"].nunique():,} días | '
      f'{precios_dia["fecha"].min():%Y-%m-%d} -> {precios_dia["fecha"].max():%Y-%m-%d} | {ram()}')
_obs_tot = int(precios_dia['n_obs'].sum())
print(f'Provincias con datos: {int((OBS_P.sum(axis=0) > 0).sum())}/{NP} | observaciones sin provincia reconocida: '
      f'{_obs_tot - int(OBS_P.sum()):,} de {_obs_tot:,} (cuentan para el nivel general, no para las provincias)')"""))

# ── CELL 5 — SERIE ─────────────────────────────────────────────────────────────
cells.append(cell_code(r"""# ============================================================
# CELDA 5 — Series diarias: medianas y sucursales apareadas, encadenadas con productos apareados
# ============================================================
def _ancho(col):
    return precios_dia.pivot(index='fecha', columns='ean_norm', values=col).sort_index()

MED  = _ancho('precio_mediano')
PROM = _ancho('precio_promedio').reindex(MED.index)
NOBS = _ancho('n_obs').reindex(MED.index)
SLR  = _ancho('suma_log_rel').reindex(MED.index)
NPAR = _ancho('n_pares').reindex(MED.index)
_q = QTY.reindex(MED.columns)

def eslabones(P):
    # Eslabón día a día: Σ q·p_t / Σ q·p_{t-1} sobre los productos con dato en los dos días
    prev = P.shift(1)
    both = P.notna() & prev.notna()
    num = P.mul(_q, axis=1).where(both).sum(axis=1)
    den = prev.mul(_q, axis=1).where(both).sum(axis=1)
    return (num / den.replace(0, np.nan)), both.sum(axis=1)

# Cambio de unidades entre meses (un mes en centavos y el vecino en pesos): el eslabón del primer día del
# mes da ~100 o ~0,01. Se corrige el mes entero y se avisa (los relativos de sucursales apareadas no lo necesitan).
_mes_idx = MED.index.to_period('M')
_link, _ = eslabones(MED)
for _mx in sorted(set(_mes_idx))[1:]:
    _d0 = MED.index[_mes_idx == _mx][0]
    _r = _link.get(_d0)
    if pd.notna(_r) and (_r > 30 or _r < 1/30):
        _f = 100 if _r > 30 else 0.01
        for _X in (MED, PROM):
            _X.loc[_mes_idx >= _mx] = _X.loc[_mes_idx >= _mx] / _f
        print(f'  AVISO: {_mx} parece en otras unidades que el mes anterior (eslabón {_r:,.2f}): '
              f'se divide por {_f:g} desde ese mes')
        _link, _ = eslabones(MED)

def serie_valor(P):
    _dir = P.mul(_q, axis=1).sum(axis=1, min_count=1)
    _l, _np = eslabones(P)
    _l.iloc[0] = 1.0
    _sin_par = _l.isna()
    _idx = _l.fillna(1.0).cumprod()
    return _dir, _l, _np, _idx, _sin_par

n_prod = MED.notna().sum(axis=1)
peso_cub = (MED.notna().mul(_q, axis=1).sum(axis=1)) / _q.sum()

# Día ancla: el último con todos los productos de la canasta (si no hay ninguno, el último con más productos)
_compl = n_prod[n_prod == NE]
ANCLA = _compl.index[-1] if len(_compl) else n_prod[n_prod == n_prod.max()].index[-1]

dir_med, link_med, npar, idx_med, sinpar = serie_valor(MED)
dir_prom, link_prom, _, idx_prom, _ = serie_valor(PROM)
val_med  = idx_med  / idx_med[ANCLA]  * dir_med[ANCLA]
val_prom = idx_prom / idx_prom[ANCLA] * dir_prom[ANCLA]

# ── Sucursales apareadas ──
# Eslabón de cada producto = media geométrica de los relativos de sus sucursales apareadas; sin pares, el precio no se
# mueve ese día. Índice del producto desde su primer día con dato, llevado a pesos con su mediana del último día con
# dato (en la canasta de pass-through, el último día del período): precio_apareado.
LINK = np.exp(SLR / NPAR.where(NPAR > 0))
IDX = LINK.where(LINK.notna(), 1.0).where(MED.notna().cummax()).cumprod()
_ult = MED.apply(pd.Series.last_valid_index)
_nivel = pd.Series({e: MED.at[_ult[e], e] / IDX.at[_ult[e], e] for e in MED.columns if pd.notna(_ult[e])})
P_AP = (IDX * _nivel.reindex(MED.columns)).where(MED.notna())
dir_ap, link_ap, _, idx_ap, _ = serie_valor(P_AP)
val_ap = idx_ap / idx_ap[ANCLA] * dir_ap[ANCLA]

# Días con cobertura incompleta del SEPA: observaciones de la canasta bajo MIN_COBERTURA_DIA de la mediana de su mes
obs_dia = NOBS.sum(axis=1)
cob_inc = obs_dia < MIN_COBERTURA_DIA * obs_dia.groupby(obs_dia.index.to_period('M')).transform('median')

serie = pd.DataFrame({
    'fecha': MED.index,
    'valor_canasta': val_med.values,
    'variacion_diaria_%': (link_med.values - 1) * 100,
    'indice_base100': (val_med / val_med.iloc[0] * 100).values,
    'valor_canasta_apareado': val_ap.values,
    'variacion_diaria_apareada_%': (link_ap.values - 1) * 100,
    'indice_apareado_base100': (val_ap / val_ap.iloc[0] * 100).values,
    'cobertura_incompleta': cob_inc.values,
    'valor_directo': dir_med.values,
    'productos_con_dato': n_prod.values,
    'productos_total': NE,
    'cobertura_ponderada_%': (peso_cub * 100).values,
    'productos_apareados': npar.values,
    'pares_sucursal_producto': NPAR.sum(axis=1).astype(int).values,
    'observaciones': obs_dia.astype(int).values,
    'valor_canasta_promedio': val_prom.values,
    'valor_directo_promedio': dir_prom.values,
})
serie.loc[0, ['variacion_diaria_%', 'variacion_diaria_apareada_%']] = np.nan
serie['valor_completo'] = serie['productos_con_dato'] == NE

# Días calendario sin datos en el SEPA (feriados, días no publicados): se listan, no se inventan
_cal = pd.date_range(serie['fecha'].min(), serie['fecha'].max(), freq='D')
DIAS_SIN_DATO = _cal.difference(pd.DatetimeIndex(serie['fecha']))

# Resumen mensual
serie['mes'] = serie['fecha'].dt.to_period('M').astype(str)
resumen = (serie.groupby('mes')
           .agg(dias_con_dato=('fecha', 'size'),
                dias_cobertura_incompleta=('cobertura_incompleta', 'sum'),
                valor_promedio_mes=('valor_canasta', 'mean'),
                valor_primer_dia=('valor_canasta', 'first'),
                valor_ultimo_dia=('valor_canasta', 'last'),
                valor_minimo=('valor_canasta', 'min'),
                valor_maximo=('valor_canasta', 'max'),
                productos_con_dato_min=('productos_con_dato', 'min'),
                valor_promedio_mes_apareado=('valor_canasta_apareado', 'mean'),
                valor_ultimo_dia_apareado=('valor_canasta_apareado', 'last'),
                valor_promedio_mes_promedio=('valor_canasta_promedio', 'mean'))
           .reset_index())
resumen.insert(4, 'variacion_mensual_%', resumen['valor_promedio_mes'].pct_change() * 100)
resumen.insert(7, 'variacion_punta_a_punta_%', resumen['valor_ultimo_dia'].pct_change() * 100)
resumen['variacion_mensual_apareada_%'] = resumen['valor_promedio_mes_apareado'].pct_change() * 100
resumen['variacion_punta_a_punta_apareada_%'] = resumen['valor_ultimo_dia_apareado'].pct_change() * 100
serie = serie.drop(columns='mes')

# Índices por grupo (sucursales apareadas, base 100 el primer día): tipo y grupo del IPC si la canasta los trae
_comp = composicion.set_index('ean_norm')
_dims = [c for c in ('tipo', 'grupo') if c in _comp and _comp[c].notna().any()] or (['categoria'] if 'categoria' in _comp else [])
indices_grupo = pd.DataFrame({'fecha': MED.index, 'Canasta': (val_ap / val_ap.iloc[0] * 100).values})
for _d in _dims:
    for _g, _ix in _comp.groupby(_d).groups.items():
        _cs = [e for e in _ix if e in P_AP.columns]
        if _cs:
            _i = serie_valor(P_AP[_cs])[3]
            indices_grupo[f'{_d} | {_g}'[:60]] = (_i / _i.iloc[0] * 100).values

# ── Nivel general vs provincias (sucursales apareadas, la misma canasta en todas) ──
# Eslabón de un producto en una provincia = media geométrica de los relativos de sus sucursales; sin pares en la
# provincia ese día, el eslabón nacional (lo que se imputa: peso_imputado_%). Se lleva a pesos con la mediana de la
# provincia del último día con dato; un producto que la provincia nunca tuvo vale como en el país. Valor de la canasta
# encadenado como el nacional y llevado a pesos en el día ancla: comparable en nivel con el nivel general.
NG = 'Nivel general'
REGION_PROV = {'CABA': 'GBA', 'Buenos Aires': 'GBA y Pampeana', 'Córdoba': 'Pampeana', 'Santa Fe': 'Pampeana',
               'Entre Ríos': 'Pampeana', 'La Pampa': 'Pampeana', 'Jujuy': 'Noroeste', 'Salta': 'Noroeste',
               'Tucumán': 'Noroeste', 'Catamarca': 'Noroeste', 'Santiago del Estero': 'Noroeste', 'La Rioja': 'Noroeste',
               'Corrientes': 'Noreste', 'Chaco': 'Noreste', 'Formosa': 'Noreste', 'Misiones': 'Noreste',
               'Mendoza': 'Cuyo', 'San Juan': 'Cuyo', 'San Luis': 'Cuyo', 'Neuquén': 'Patagonia',
               'Río Negro': 'Patagonia', 'Chubut': 'Patagonia', 'Santa Cruz': 'Patagonia', 'Tierra del Fuego': 'Patagonia'}
_t_dias = _CAL.get_indexer(MED.index)
_ie = pd.Index(EAN_LIST).get_indexer(MED.columns)
_ln_nac = np.log(LINK.where(LINK.notna(), 1.0)).to_numpy()
_activo = MED.notna().cummax()
val_prov, imp_prov, obs_prov, prod_prov = {}, {}, {}, {}
for _p in sorted(range(NP), key=lambda i: _ud.normalize('NFKD', ISO_PROV[PROV_LIST[i]]).encode('ascii', 'ignore')):
    if not OBS_P[:, _p].any():
        continue
    _nom = ISO_PROV[PROV_LIST[_p]]
    _npp = NPAR_P[_t_dias[:, None], _ie[None, :], _p]
    _lp = np.where(_npp > 0, SLR_P[_t_dias[:, None], _ie[None, :], _p] / np.maximum(_npp, 1), _ln_nac)
    _IDXp = pd.DataFrame(np.exp(_lp), index=MED.index, columns=MED.columns).where(_activo).cumprod()
    _du, _niv = DIA_P_ULT[_ie, _p], _nivel.reindex(MED.columns).to_numpy().copy()
    _con = np.flatnonzero(_du >= 0)
    _niv[_con] = MED_P_ULT[_ie[_con], _p] / _IDXp.to_numpy()[MED.index.get_indexer(_CAL[_du[_con]]), _con]
    _Pp = (_IDXp * _niv).where(MED.notna())
    _dir, _, _, _ix, _ = serie_valor(_Pp)
    val_prov[_nom] = _ix / _ix[ANCLA] * _dir[ANCLA]
    _vq = _Pp.mul(_q, axis=1)
    imp_prov[_nom] = _vq.where(_npp == 0).sum(axis=1) / _vq.sum(axis=1) * 100
    obs_prov[_nom] = pd.Series(OBS_P[_t_dias, _p], index=MED.index)
    prod_prov[_nom] = len(_con)
prov_val = pd.DataFrame({NG: val_ap, **val_prov})

# ── Nivel general vs grandes rubros (tipo de la canasta; si no lo trae, la categoría) ──
# Valor de cada rubro = su parte de la canasta, encadenada como el nivel general y en pesos del día ancla: los rubros
# suman el nivel general en el día ancla (en el resto, salvo lo que separa encadenarlos por separado).
DIM_RUBRO = next((c for c in ('tipo', 'categoria') if c in _comp and _comp[c].notna().any()), None)
val_rub = {}
if DIM_RUBRO:
    for _g, _ix in sorted(_comp.groupby(DIM_RUBRO).groups.items()):
        _cs = [e for e in _ix if e in P_AP.columns]
        if _cs:
            _dir, _, _, _i, _ = serie_valor(P_AP[_cs])
            val_rub[_g] = _i / _i[ANCLA] * _dir[ANCLA]
rub_val = pd.DataFrame({NG: val_ap, **val_rub})
n_rub = _comp.groupby(DIM_RUBRO).size() if DIM_RUBRO else pd.Series(dtype=int)

def _mensual(V):
    # promedio de los días de cada mes (como variacion_mensual_% de Resumen_mensual)
    M = V.groupby(V.index.to_period('M')).mean()
    M.index = M.index.astype(str)
    M.index.name = 'mes'
    return M

def _antes(M, k):
    # fila de k meses antes del último (NaN si ese mes no está)
    p = pd.PeriodIndex(M.index, freq='M')
    return M.iloc[p.get_loc(p[-1] - k)] if (p[-1] - k) in p else M.iloc[-1] * np.nan

def _var(M, k):
    return (M.iloc[-1] / _antes(M, k) - 1) * 100

def resumen_vs_ng(V, nombre):
    # una fila por grupo (la primera, el nivel general): valor, variaciones y diferencia con el nivel general
    M = _mensual(V)
    u, p0 = V.iloc[-1], V.iloc[0]
    r = pd.DataFrame({'valor_primer_dia': p0, 'valor_ultimo_dia': u,
                      'variacion_periodo_%': (u / p0 - 1) * 100,
                      'variacion_12_meses_%': _var(M, 12),
                      'variacion_ultimo_mes_%': _var(M, 1)})
    for c in ('variacion_periodo_%', 'variacion_12_meses_%', 'variacion_ultimo_mes_%'):
        r[f'dif_{c[:-2]}_vs_NG_pp'] = r[c] - r.at[NG, c]
    return r.rename_axis(nombre).reset_index()

prov_mensual = _mensual(prov_val)
prov_var_mensual = (prov_mensual.pct_change() * 100).reset_index()
prov_diario = (prov_val / prov_val.iloc[0] * 100).reset_index()
prov_resumen = resumen_vs_ng(prov_val, 'provincia')
prov_resumen.insert(1, 'region', prov_resumen['provincia'].map(REGION_PROV).fillna('País'))
prov_resumen.insert(4, 'relativo_nivel_general_%', prov_resumen['valor_ultimo_dia'] / prov_val[NG].iloc[-1] * 100)
_imp = pd.DataFrame(imp_prov).iloc[1:]           # el primer día no tiene eslabón
prov_resumen['peso_imputado_prom_%'] = prov_resumen['provincia'].map(_imp.mean())
prov_resumen['peso_imputado_max_%'] = prov_resumen['provincia'].map(_imp.max())
prov_resumen['productos_con_dato'] = prov_resumen['provincia'].map(prod_prov).fillna(len(MED.columns)).astype(int)
prov_resumen['observaciones_prom_dia'] = prov_resumen['provincia'].map(pd.DataFrame(obs_prov).mean()).fillna(obs_dia.mean())

rub_mensual = _mensual(rub_val)
rub_var_mensual = (rub_mensual.pct_change() * 100).reset_index()
rub_diario = (rub_val / rub_val.iloc[0] * 100).reset_index()
# incidencia de cada rubro en la variación mensual del nivel general (pp): cambio del valor del rubro / nivel general
# del mes anterior. Suman la variación del nivel general salvo lo que separa encadenar los rubros por separado.
_ru = [c for c in rub_mensual.columns if c != NG]
rub_incidencia = rub_mensual[_ru].diff().div(rub_mensual[NG].shift(), axis=0) * 100
rub_incidencia['Suma de rubros'] = rub_incidencia[_ru].sum(axis=1, min_count=1)
rub_incidencia[f'{NG} (variación %)'] = rub_mensual[NG].pct_change() * 100
rub_incidencia = rub_incidencia.reset_index()
rub_resumen = resumen_vs_ng(rub_val, 'rubro')
rub_resumen.insert(1, 'productos', rub_resumen['rubro'].map(n_rub).fillna(len(MED.columns)).astype(int))
rub_resumen.insert(2, 'peso_primer_dia_%', rub_resumen['valor_primer_dia'] / rub_val[NG].iloc[0] * 100)
rub_resumen.insert(3, 'peso_ultimo_dia_%', rub_resumen['valor_ultimo_dia'] / rub_val[NG].iloc[-1] * 100)
rub_resumen['incidencia_periodo_pp'] = (rub_resumen['valor_ultimo_dia'] - rub_resumen['valor_primer_dia']) / rub_val[NG].iloc[0] * 100
_a12 = _antes(rub_mensual, 12)
rub_resumen['incidencia_12_meses_pp'] = rub_resumen['rubro'].map((rub_mensual.iloc[-1] - _a12) / _a12[NG] * 100)
rub_resumen.loc[rub_resumen['rubro'] == NG, ['incidencia_periodo_pp', 'incidencia_12_meses_pp']] = np.nan

# Series desagregadas en formato largo (para las regresiones)
def _largo_dim(V, dim, imp=None):
    L = (V / V.iloc[0] * 100).rename_axis('fecha').reset_index().melt(id_vars='fecha', var_name='nombre',
                                                                       value_name='indice_base100')
    L['valor_canasta_apareado'] = V.rename_axis('fecha').reset_index().melt(id_vars='fecha')['value'].to_numpy()
    L['variacion_diaria_%'] = (V / V.shift() - 1).mul(100).rename_axis('fecha').reset_index().melt(id_vars='fecha')['value'].to_numpy()
    L.insert(1, 'desagregacion', np.where(L['nombre'] == NG, NG, dim))
    if imp is not None:
        L['peso_imputado_%'] = pd.DataFrame(imp).reindex(index=V.index, columns=V.columns).melt()['value'].to_numpy()
    return L
series_desagregadas = pd.concat([_largo_dim(prov_val, 'provincia', imp_prov),
                                 _largo_dim(rub_val[[c for c in rub_val if c != NG]], 'rubro')], ignore_index=True)
series_desagregadas['cobertura_incompleta'] = series_desagregadas['fecha'].map(cob_inc)

# Precios diarios por producto (mediana y apareado), una columna por producto
_nombre = composicion.set_index('ean_norm')['descripcion']
precios_wide = MED.copy()
precios_wide.columns = [f'{e} | {_nombre[e]}'[:60] for e in MED.columns]
precios_wide = precios_wide.reset_index()
precios_ap_wide = P_AP.copy()
precios_ap_wide.columns = precios_wide.columns[1:]
precios_ap_wide = precios_ap_wide.reset_index()

# Panel producto x día (días con dato), para las regresiones
_largo = [X.reset_index().melt(id_vars='fecha', var_name='ean_norm', value_name=n).set_index(['fecha', 'ean_norm'])[n]
          for n, X in [('precio_mediano', MED), ('precio_promedio', PROM), ('n_obs', NOBS), ('n_pares', NPAR),
                       ('relativo_apareado', LINK), ('indice_apareado', IDX), ('precio_apareado', P_AP)]]
panel = pd.concat(_largo, axis=1).reset_index()
panel = panel[panel['precio_mediano'].notna()]
panel = (panel.merge(composicion.drop(columns='id_producto'), on='ean_norm', how='left')
         .sort_values(['ean_norm', 'fecha']).reset_index(drop=True))
panel['cobertura_incompleta'] = panel['fecha'].map(cob_inc)
del _largo; gc.collect()

# Controles
print(f'Canasta {NOMBRE_CANASTA}: {len(serie):,} días con dato ({serie["fecha"].min():%d/%m/%Y} -> '
      f'{serie["fecha"].max():%d/%m/%Y}); días calendario sin dato: {len(DIAS_SIN_DATO)}')
print(f'Día ancla (pesos de los valores encadenados): {ANCLA:%d/%m/%Y} con {n_prod[ANCLA]}/{NE} productos '
      f'= ${dir_med[ANCLA]:,.2f}')
print(f'Días con todos los productos: {int(serie["valor_completo"].sum()):,} de {len(serie):,} | '
      f'días con cobertura incompleta del SEPA: {int(serie["cobertura_incompleta"].sum())}')
_nunca = sorted(EANS - set(MED.columns))
if _nunca:
    print(f'  AVISO: {len(_nunca)} productos sin ningún dato en el período: '
          f'{composicion.set_index("ean_norm").loc[_nunca, "descripcion"].tolist()}')
_ini = MED.notna().idxmax()
_tarde = _ini[_ini > MED.index[0] + pd.Timedelta(days=31)].sort_values()
if len(_tarde):
    print(f'  {len(_tarde)} productos aparecen después del primer mes (entran al encadenado desde ese día):')
    for _e, _d in _tarde.head(30).items():
        print(f'    {_d:%d/%m/%Y}  {composicion.set_index("ean_norm").loc[_e, "descripcion"]}')
if sinpar.iloc[1:].any():
    print(f'  AVISO: {int(sinpar.iloc[1:].sum())} días sin productos en común con el anterior (eslabón = 1)')
for _col, _nom in (('variacion_diaria_%', 'medianas'), ('variacion_diaria_apareada_%', 'sucursales apareadas')):
    _salto = serie[serie[_col].abs() > ALERTA_ESLABON * 100]
    if len(_salto):
        print(f'  AVISO ({_nom}): {len(_salto)} días con variación diaria mayor a ±{ALERTA_ESLABON:.0%}:')
        print(_salto[['fecha', _col, 'productos_apareados', 'cobertura_incompleta']].head(15).to_string(index=False))
_u, _p = serie.iloc[-1], serie.iloc[0]
print(f'\nÚltimo día {_u["fecha"]:%d/%m/%Y}: ${_u["valor_canasta"]:,.2f} (medianas) | ${_u["valor_canasta_apareado"]:,.2f} '
      f'(apareado) | {int(_u["productos_con_dato"])}/{NE} productos')
print(f'Primer día {_p["fecha"]:%d/%m/%Y}: ${_p["valor_canasta"]:,.2f} (medianas) | ${_p["valor_canasta_apareado"]:,.2f} (apareado)')
print(f'Variación del período: medianas {(_u["valor_canasta"] / _p["valor_canasta"] - 1) * 100:+,.1f}% | '
      f'apareado {(_u["valor_canasta_apareado"] / _p["valor_canasta_apareado"] - 1) * 100:+,.1f}%')
print(resumen[['mes', 'dias_con_dato', 'dias_cobertura_incompleta', 'variacion_mensual_%', 'variacion_mensual_apareada_%',
               'productos_con_dato_min']].tail(12).to_string(index=False))
_cols = ['valor_ultimo_dia', 'variacion_periodo_%', 'variacion_12_meses_%', 'variacion_ultimo_mes_%']
print(f'\nNivel general vs provincias ({len(val_prov)} provincias):')
print(prov_resumen.set_index('provincia')[['relativo_nivel_general_%'] + _cols + ['peso_imputado_prom_%',
                                                                                 'productos_con_dato']].round(2).to_string())
print(f'\nNivel general vs grandes rubros ({DIM_RUBRO}):')
print(rub_resumen.set_index('rubro')[['productos', 'peso_ultimo_dia_%'] + _cols + ['incidencia_periodo_pp']].round(2).to_string())
_suma = rub_val.drop(columns=NG).sum(axis=1)
print(f'Control: la suma de los rubros se aparta del nivel general a lo sumo {((_suma / rub_val[NG] - 1).abs().max() * 100):.3f}% '
      f'(cero en el día ancla; encadenar cada rubro por separado)')
if len(_imp) and _imp.mean().max() > 5:
    print(f'  AVISO: provincias con más de 5% del valor imputado en promedio: '
          f'{_imp.mean()[_imp.mean() > 5].round(1).to_dict()}')"""))

# ── CELL 6 — GRÁFICO ───────────────────────────────────────────────────────────
cells.append(cell_code(r"""# ============================================================
# CELDA 6 — Gráfico de control
# ============================================================
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 8), sharex=True, gridspec_kw={'height_ratios': [3, 1]})
ax1.plot(serie['fecha'], serie['valor_canasta_apareado'], color='#375623', lw=1.2, label='Sucursales apareadas')
ax1.plot(serie['fecha'], serie['valor_canasta'], color='#92D050', lw=0.9, alpha=0.9, label='Medianas')
_inc = serie[serie['cobertura_incompleta']]
ax1.scatter(_inc['fecha'], _inc['valor_canasta'], color='#C00000', s=10, zorder=3, label='Cobertura incompleta del SEPA')
ax1.set_yscale('log')
ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'${v:,.0f}'))
ax1.set_title(f'Canasta {NOMBRE_CANASTA} — valor diario (escala logarítmica)')
ax1.legend()
ax2.plot(serie['fecha'], serie['observaciones'], color='gray', lw=0.8)
ax2.set_ylabel('observaciones')
plt.tight_layout()
plt.show()

# Nivel general vs provincias y vs grandes rubros (sucursales apareadas, base 100 el primer día)
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5.5), sharey=True)
for _c in prov_diario.columns[2:]:
    ax1.plot(prov_diario['fecha'], prov_diario[_c], color='#A6A6A6', lw=0.6)
_hi = prov_resumen[prov_resumen['provincia'] != NG].sort_values('variacion_periodo_%')['provincia']
for _c, _col in ((_hi.iloc[0], '#2E75B6'), (_hi.iloc[-1], '#C00000')) if len(_hi) else ():
    ax1.plot(prov_diario['fecha'], prov_diario[_c], color=_col, lw=1.1, label=f'{_c} (extremo)')
ax1.plot(prov_diario['fecha'], prov_diario[NG], color='black', lw=1.6, label=NG)
ax1.set_title('Nivel general vs provincias (gris: cada provincia)')
ax1.legend(fontsize=8)
for _c, _col in zip(rub_diario.columns[2:], plt.cm.tab10.colors):
    ax2.plot(rub_diario['fecha'], rub_diario[_c], color=_col, lw=1.0, label=_c)
ax2.plot(rub_diario['fecha'], rub_diario[NG], color='black', lw=1.6, label=NG)
ax2.set_title(f'Nivel general vs grandes rubros ({DIM_RUBRO})')
ax2.legend(fontsize=8)
for _a in (ax1, ax2):
    _a.set_yscale('log')
    _a.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'{v:,.0f}'))
plt.tight_layout()
plt.show()"""))

# ── CELL 7 — EXPORTACIÓN ───────────────────────────────────────────────────────
cells.append(cell_code(r"""# ============================================================
# CELDA 7 — Exportación: Excel + panel producto x día (parquet y csv.gz)
# ============================================================
_desde, _hasta = serie['fecha'].min(), serie['fecha'].max()
_base = f'{SHORT_CANASTA}_{_desde:%Y%m%d}_{_hasta:%Y%m%d}'
notas = pd.DataFrame({'nota': [
    f'Canasta {NOMBRE_CANASTA} (columna {CANASTA_COL} de la hoja Selección de {CANASTA_EXCEL.name}): '
    f'{NE} productos (las cantidades suman {QTY.sum():,.2f}).',
    f'Período: {_desde:%d/%m/%Y} a {_hasta:%d/%m/%Y}, {len(serie):,} días con dato del SEPA '
    f'({len(DIAS_SIN_DATO)} días calendario sin dato publicados; no se completan).',
    'Precio de un producto en un día (Precios_diarios) = mediana nacional de todas las observaciones (sucursales) de ese '
    'día en los archivos COMPLETO de los ZIPs semestrales (uno por quincena: si hay dos para la misma, el que cubre más '
    'días), sin filtro de sucursales, como la serie oficial del nb02 (CELDA 9).',
    f'Sucursales apareadas (Precios_apareados): para cada sucursal y producto, relativo = precio del día / su precio '
    f'anterior (si la sucursal repite la fila, el promedio). Si faltó unos días (a lo sumo {MAX_DIAS_SIN_PRECIO}), el precio '
    'anterior es el último que informó movido con el índice del producto desde entonces (imputación del IPC para precios '
    f'faltantes). Los relativos fuera de [1/{RELATIVO_MAX:g}, {RELATIVO_MAX:g}] no cuentan. Eslabón del producto = media '
    'geométrica de sus relativos (sin pares, no se mueve). Se encadena desde el primer día con dato y se lleva a pesos con '
    'la mediana del último día con dato. No cambia cuando cambian las sucursales que informan.',
    'valor_canasta y valor_canasta_apareado = índices encadenados día a día con productos apareados: cada eslabón = '
    'suma q x p(t) / suma q x p(t-1) sobre los productos con dato los dos días, llevados a pesos con el valor del día '
    f'ancla ({ANCLA:%d/%m/%Y}, {int(n_prod[ANCLA])}/{NE} productos = ${dir_med[ANCLA]:,.2f}). valor_directo = suma q x '
    'mediana del día, solo con los productos con dato (si falta uno, baja).',
    f'cobertura_incompleta: observaciones de la canasta por debajo del {MIN_COBERTURA_DIA:.0%} de la mediana de su mes '
    '(p. ej. 16-28/07/2023, con la mitad de los comercios). La mediana de esos días puede moverse por el cambio de '
    'sucursales; el apareado no. Conviene excluirlos o tratarlos aparte en las regresiones.',
    'variacion_diaria_% = eslabón del día - 1. indice_base100 = valor / valor del primer día x 100.',
    'valor_canasta_promedio / valor_directo_promedio: lo mismo con el promedio de las sucursales sin los valores a más de '
    '4 veces de la mediana del día (el criterio del análisis promedio del nb02).',
    'Resumen_mensual: variacion_mensual_% compara el promedio de los días del mes; variacion_punta_a_punta_%, el último '
    'día de cada mes. El último mes puede estar incompleto (ver dias_con_dato).',
    'Indices_por_grupo: índice con sucursales apareadas de cada tipo y grupo del IPC (o categoría), base 100 el primer día, '
    'con las cantidades de la canasta.',
    'Nivel general = valor_canasta_apareado (la canasta en todo el país). Las desagregaciones usan sucursales apareadas y '
    'la misma canasta (productos y cantidades) en todos los grupos.',
    'Provincias_*: la provincia de cada sucursal es el código ISO de sucursales_provincia (como el nb09; las escritas con '
    'el nombre se pasan al código; las vacías cuentan para el nivel general y no para ninguna provincia). Eslabón de un '
    'producto en la provincia = media geométrica de los relativos de sus sucursales (con el índice de la provincia para '
    'las que faltaron unos días); si la provincia no tiene pares de ese producto ese día, se mueve como en el país '
    '(peso_imputado_% = parte del valor de la canasta con eslabón nacional ese día; el primer día es 100%). Se lleva a '
    'pesos con la mediana de la provincia del último día con dato; un producto que la provincia nunca tuvo vale como en '
    'el país. El valor se encadena como el nivel general y se lleva a pesos en el día ancla: relativo_nivel_general_% '
    'compara el costo de la canasta en la provincia con el del país (precios de lista).',
    f'Rubros_*: la canasta partida por {DIM_RUBRO} (grandes rubros de consumo). Valor de cada rubro = su parte de la '
    'canasta, encadenada como el nivel general y en pesos del día ancla. peso_%: parte del valor de la canasta ese día. '
    'Incidencia (pp) = cambio del valor del rubro / valor del nivel general del período anterior x 100: las incidencias '
    'suman la variación del nivel general (salvo lo que separa encadenar cada rubro por separado; ver Suma de rubros).',
    '*_mensual: variación del promedio de los días de cada mes contra el mes anterior (igual que Resumen_mensual). '
    '*_resumen: variacion_periodo_% = último día / primer día; variacion_12_meses_% y variacion_ultimo_mes_%, con los '
    'promedios mensuales (el último mes puede estar incompleto); dif_*_vs_NG_pp = diferencia con el nivel general en '
    'puntos porcentuales. *_diario: índice base 100 el primer día.',
    'Pesos o centavos: un mes se pasa a pesos si su mediana supera 10.000 (regla del nb02); además se corrige un mes '
    'entero de las medianas si el eslabón de su primer día da más de 30 o menos de 1/30 contra el mes anterior.',
    f'panel_diario_{_base}.parquet / .csv.gz: una fila por producto y día con dato (precio_mediano, precio_promedio, '
    'n_obs, n_pares, relativo_apareado, indice_apareado, precio_apareado, cobertura_incompleta y la composición).',
    f'series_desagregadas_{_base}.parquet: una fila por día y grupo (nivel general, provincias y rubros) con '
    'valor_canasta_apareado, indice_base100, variacion_diaria_%, peso_imputado_% (provincias) y cobertura_incompleta.',
    f'Días calendario sin dato: {", ".join(d.strftime("%d/%m/%Y") for d in DIAS_SIN_DATO[:60])}'
    + (' ...' if len(DIAS_SIN_DATO) > 60 else ''),
]})

out_xls = OUTPUT_DIR / f'canasta_diaria_{_base}.xlsx'
_hojas = [('Serie_diaria', serie), ('Resumen_mensual', resumen),
          ('Provincias_resumen', prov_resumen), ('Provincias_mensual', prov_var_mensual), ('Provincias_diario', prov_diario),
          ('Rubros_resumen', rub_resumen), ('Rubros_mensual', rub_var_mensual), ('Rubros_incidencia', rub_incidencia),
          ('Rubros_diario', rub_diario),
          ('Composicion', composicion.drop(columns='ean_norm')),
          ('Indices_por_grupo', indices_grupo), ('Precios_diarios', precios_wide), ('Precios_apareados', precios_ap_wide),
          ('Notas', notas)]
with pd.ExcelWriter(out_xls, engine='xlsxwriter', datetime_format='dd/mm/yyyy', date_format='dd/mm/yyyy') as _xw:
    _wb = _xw.book
    _f_hdr = _wb.add_format({'bold': True, 'font_color': 'white', 'bg_color': '#375623', 'text_wrap': True,
                             'valign': 'vcenter', 'align': 'center', 'font_size': 10})
    _f_pes = _wb.add_format({'num_format': '#,##0.00'})
    _f_var = _wb.add_format({'num_format': '+0.00"%";-0.00"%"'})
    _f_pp = _wb.add_format({'num_format': '+0.00;-0.00'})
    _f_ind = _wb.add_format({'num_format': '0.00'})
    _f_nota = _wb.add_format({'text_wrap': True, 'valign': 'top'})
    # hojas con un mismo formato en todas las columnas de datos (la primera es la fecha o el mes)
    _fmt_hoja = {'Indices_por_grupo': _f_ind, 'Provincias_diario': _f_ind, 'Rubros_diario': _f_ind,
                 'Provincias_mensual': _f_var, 'Rubros_mensual': _f_var, 'Rubros_incidencia': _f_pp}
    for _sh, _df in _hojas:
        _df.to_excel(_xw, sheet_name=_sh, index=False)
        _ws = _xw.sheets[_sh]
        _ws.set_row(0, 45 if _sh.endswith('_resumen') else 30)
        _ws.freeze_panes(1, 1)
        for _j, _c in enumerate(_df.columns):
            _h = str(_c).lower()
            _fmt = (_f_nota if _sh == 'Notas' else
                    (_f_var if _sh == 'Rubros_incidencia' and '(variación %)' in _h else _fmt_hoja[_sh]) if _sh in _fmt_hoja and _j > 0 else
                    _f_pp if _h.endswith('_pp') else
                    _f_ind if 'indice' in _h or 'cobertura_ponderada' in _h or 'relativo_' in _h or 'peso_' in _h else
                    _f_var if '%' in _h else
                    _f_pes if any(x in _h for x in ('valor', 'precio', '|')) else None)
            _ancho = (160 if _sh == 'Notas' else 22 if _j == 0 and _sh.endswith('_resumen') else 12 if _j == 0 else
                      42 if ('desc' in _h or '|' in _h) else 15)
            _ws.set_column(_j, _j, _ancho, _fmt)
            _ws.write(0, _j, _c, _f_hdr)
print(f'Excel: {out_xls}')
print(f'  Serie_diaria {len(serie):,} filas | Resumen_mensual {len(resumen)} | Provincias {len(val_prov)} | '
      f'Rubros {len(val_rub)} | Composicion {len(composicion)} | Indices_por_grupo {indices_grupo.shape[1] - 1} series | '
      f'Precios_diarios y Precios_apareados {precios_wide.shape[1] - 1} productos')
panel.to_parquet(OUTPUT_DIR / f'panel_diario_{_base}.parquet', index=False)
panel.to_csv(OUTPUT_DIR / f'panel_diario_{_base}.csv.gz', index=False, compression='gzip')
print(f'Panel: panel_diario_{_base}.parquet y .csv.gz ({len(panel):,} filas producto x día) | {ram()}')
series_desagregadas.to_parquet(OUTPUT_DIR / f'series_desagregadas_{_base}.parquet', index=False)
print(f'Series desagregadas: series_desagregadas_{_base}.parquet ({len(series_desagregadas):,} filas día x grupo)')"""))

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
out_path = os.path.join(script_dir, '08_canasta_diaria.ipynb')
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f'Written: {out_path}')
print(f'Cells: {len(cells)}')
