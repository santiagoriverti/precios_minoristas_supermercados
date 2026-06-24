"""Genera 04_precios_seleccion.ipynb — precios diarios por sucursal cercana a un punto."""
import json, os, hashlib

def _cid(prefix, src):
    return prefix + hashlib.md5(src.encode('utf-8')).hexdigest()[:6]

def cell_md(src):
    lines = src.split('\n')
    source = [l + '\n' for l in lines[:-1]] + ([lines[-1]] if lines[-1] else [])
    return {'cell_type': 'markdown', 'id': _cid('md', src), 'metadata': {}, 'source': source}

def cell_code(src):
    return {'cell_type': 'code', 'execution_count': None, 'id': _cid('c', src),
            'metadata': {}, 'outputs': [], 'source': [src]}

cells = []

# ── CELL 0 — Intro ────────────────────────────────────────────────────────────
cells.append(cell_md("""# 04 — Precios por selección geográfica

Exporta un **Excel** con los precios diarios del **último mes disponible** para todos
los supermercados ubicados a una distancia máxima de un **punto** dado.

**Salida** (`precios_seleccion_YYYY-MM.xlsx`):
- Hoja **`Sucursales`**: índice de los locales seleccionados (cadena, localidad, tipo, distancia, nº de productos).
- **Una hoja por sucursal**: todos sus productos (EAN, descripción, marca, rubro) y el **precio para cada día** del mes.
- Hoja **`General`**: todos los productos únicos × supermercado con el **precio promedio del mes**; celda vacía si ese super no tiene el producto. Incluye `promedio_general`.

**Cómo usar:** ajustá el punto y la distancia en la celda de CONFIGURACIÓN, *Entorno de ejecución → Ejecutar todo*. Al final descarga el Excel.

> Requiere en `carga/` (Drive): los ZIPs SEPA (`2024A.zip`…`2026A.zip`). Los maestros se descargan solos desde GitHub. Precios en centavos → se autodetecta y pasa a pesos."""))

# ── CELL 1 — CONFIG ─────────────────────────────────────────────────────────────
cells.append(cell_code("""\
# ===========================================================
# CONFIGURACIÓN — Modificar solo esta sección
# ===========================================================
SEPA_DIR   = '/content/drive/MyDrive/carga'
OUTPUT_DIR = '/content/drive/MyDrive/carga/output_canasta'

# Punto de referencia (lat, lon) y radio máximo en km
PUNTO_LAT   = -37.115479
PUNTO_LON   = -56.886020
DIST_MAX_KM = 20.0

# Período: None = autodetectar el último mes disponible; o forzar 'YYYY-MM'
PERIODO = None

# Incluir descripción/marca/rubro de cada producto (cruza el Maestro de Productos)
INCLUIR_METADATA = True

# Tope de sucursales (seguridad para puntos en zonas muy densas)
MAX_SUCURSALES = 80"""))

# ── CELL 2 — Setup ────────────────────────────────────────────────────────────
cells.append(cell_code("""\
# ===========================================================
# Setup — dependencias, Drive, imports
# ===========================================================
import subprocess, sys
subprocess.run([sys.executable, '-m', 'pip', 'install', 'openpyxl', 'requests', '-q'], check=False)

import zipfile, gzip, io, os, re, math, urllib.parse, warnings
from pathlib import Path
import numpy as np
import pandas as pd
import requests
warnings.filterwarnings('ignore')

try:
    from google.colab import drive
    drive.mount('/content/drive')
except Exception:
    print('(No es Colab o Drive ya montado)')

SEPA_DIR   = Path(SEPA_DIR)
OUTPUT_DIR = Path(OUTPUT_DIR)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR = Path('/content/tmp_sepa'); TMP_DIR.mkdir(exist_ok=True)
print(f'Punto: ({PUNTO_LAT}, {PUNTO_LON}) | radio {DIST_MAX_KM} km')
print(f'Salida: {OUTPUT_DIR}')"""))

# ── CELL 3 — Funciones + maestros ─────────────────────────────────────────────
cells.append(cell_code("""\
# ===========================================================
# Funciones auxiliares y maestros
# ===========================================================
_BASE_GH = 'https://raw.githubusercontent.com/santiagoriverti/precios_minoristas_supermercados/main/data/'

def descargar_maestro(fname):
    dst = OUTPUT_DIR / fname
    if not dst.exists():
        print(f'  Descargando desde GitHub: {fname} ...')
        r = requests.get(_BASE_GH + urllib.parse.quote(fname), timeout=180)
        r.raise_for_status()
        dst.write_bytes(r.content)
    return dst

def normalizar_ean(s):
    if pd.isna(s): return None
    s = str(s).strip().lstrip('0')
    return s if s else '0'

def nid(x):
    # normaliza id quitando ceros a la izquierda (004 -> 4); 10 -> 10
    s = str(x).strip().lstrip('0')
    return s if s else '0'

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0088
    p1 = np.radians(lat1); p2 = np.radians(lat2)
    dphi = np.radians(lat2 - lat1); dl = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))

# Cadena legible por (id_comercio, id_bandera)
_CAD_COMP = {('9','1'):'Vea',('9','2'):'Disco',('9','3'):'Jumbo',('10','1'):'Carrefour',
             ('10','2'):'Carrefour Market',('10','3'):'Carrefour Express',('11','2'):'ChangoMas',
             ('11','4'):'Hiper ChangoMas',('11','5'):'Mi ChangoMas',('16','1'):'Hipermercado Libertad',
             ('16','2'):'Mini Libertad'}
_CAD_SIMP = {'2':'La Anonima','3':'Cadena 3','5':'Hipermercado Misiones','8':'Cadena 8',
             '12':'Coto','13':'Cooperativa Obrera','15':'DIA','20':'LAR','21':'Toledo',
             '23':'Cadena 23','47':'Pasamonte'}
def nombre_cadena(c, b):
    return _CAD_COMP.get((str(c), str(b))) or _CAD_SIMP.get(str(c)) or f'Comercio {c}'

# Detección del último mes en los ZIPs semestrales (YYYYA / YYYYB)
_PAT_SEM = re.compile(r'^(\\d{4})(A|B)$', re.IGNORECASE)
_PAT_ARC = re.compile(r'^(\\d{2})(\\d{4})_pais_parte.*COMPLETO.*\\.csv\\.gz$', re.IGNORECASE)

def detectar_ultimo_mes(sepa_dir, periodo=None):
    meses = {}
    for zp in sorted(Path(sepa_dir).glob('*.zip')):
        if not _PAT_SEM.match(zp.stem): continue
        try:
            with zipfile.ZipFile(zp) as zf: nombres = zf.namelist()
        except Exception: continue
        for n in nombres:
            m = _PAT_ARC.match(Path(n).name)
            if m:
                meses.setdefault((int(m.group(2)), int(m.group(1))), {'zip': zp, 'arch': []})
                meses[(int(m.group(2)), int(m.group(1)))]['arch'].append(n)
    if not meses:
        raise RuntimeError(f'No se hallaron archivos SEPA en {sepa_dir}')
    if periodo:
        key = (int(periodo[:4]), int(periodo[5:7]))
        if key not in meses:
            raise RuntimeError(f'{periodo} no disponible. Hay: {sorted(meses)}')
    else:
        key = max(meses)
    info = meses[key]
    return info['zip'], f'{key[0]}-{key[1]:02d}', sorted(info['arch'])

# Maestros
_suc_path = descargar_maestro('maestro_sucursales_completo.xlsx')
MS = pd.read_excel(_suc_path, dtype=str)
MS['lat'] = pd.to_numeric(MS['sucursales_latitud'], errors='coerce')
MS['lon'] = pd.to_numeric(MS['sucursales_longitud'], errors='coerce')
MS = MS.dropna(subset=['lat', 'lon'])
MS['key'] = MS['id_comercio'].map(nid) + '|' + MS['id_bandera'].map(nid) + '|' + MS['id_sucursal'].map(nid)

MP_META = None
if INCLUIR_METADATA:
    _prod_path = descargar_maestro('Maestro de Productos Interno.xlsx')
    # OJO: el EAN real está en 'producto_sepa_id' ('producto_ean' es un flag 0/1)
    _mp = pd.read_excel(_prod_path, dtype=str,
                        usecols=['producto_sepa_id', 'producto_descripcion', 'producto_marca', 'rubro'])
    _mp['ean_norm'] = _mp['producto_sepa_id'].map(normalizar_ean)
    MP_META = (_mp.dropna(subset=['ean_norm']).drop_duplicates('ean_norm')
               [['ean_norm', 'producto_descripcion', 'producto_marca', 'rubro']]
               .rename(columns={'producto_descripcion': 'descripcion', 'producto_marca': 'marca'}))
    del _mp
print(f'Maestro sucursales: {len(MS):,} con coordenadas')
print('Maestros listos')"""))

# ── CELL 4 — Filtrar sucursales por distancia ─────────────────────────────────
cells.append(cell_code("""\
# ===========================================================
# CELDA 4 — Sucursales dentro del radio
# ===========================================================
MS['distancia_km'] = haversine_km(PUNTO_LAT, PUNTO_LON, MS['lat'].values, MS['lon'].values)
sel = MS[MS['distancia_km'] <= DIST_MAX_KM].copy()
sel = sel.drop_duplicates('key').sort_values('distancia_km').reset_index(drop=True)

if len(sel) == 0:
    raise RuntimeError(f'No hay sucursales a <= {DIST_MAX_KM} km del punto. Probá ampliar DIST_MAX_KM.')
if len(sel) > MAX_SUCURSALES:
    print(f'⚠️  {len(sel)} sucursales en el radio; recortando a las {MAX_SUCURSALES} más cercanas (MAX_SUCURSALES).')
    sel = sel.head(MAX_SUCURSALES).copy()

sel['cadena'] = [nombre_cadena(c, b) for c, b in zip(sel['id_comercio'], sel['id_bandera'])]

# Nombre de hoja seguro (<=31 chars, sin caracteres inválidos, único)
_usados = set()
def _safe_sheet(cad, loc, i):
    base = f'{cad} {loc}'.strip()
    base = re.sub(r'[\\\\/*?:\\[\\]]', ' ', base)
    base = re.sub(r'\\s+', ' ', base).strip()[:28]
    name = base if base else f'Suc {i}'
    k = 1
    while name.lower() in _usados:
        suf = f' {k}'; name = (base[:28 - len(suf)] + suf); k += 1
    _usados.add(name.lower())
    return name

sel['localidad'] = sel['sucursales_localidad'].fillna('').str.strip()
sel['sheet'] = [_safe_sheet(c, l, i) for i, (c, l) in enumerate(zip(sel['cadena'], sel['localidad']), 1)]
sel['label'] = sel['cadena'] + ' - ' + sel['localidad'].replace('', 'sl')

print(f'Sucursales dentro de {DIST_MAX_KM} km: {len(sel)}')
print(sel[['cadena', 'sucursales_nombre', 'sucursales_tipo', 'localidad',
           'distancia_km']].to_string(index=False))"""))

# ── CELL 5 — Leer precios del mes (solo sucursales seleccionadas) ─────────────
cells.append(cell_code("""\
# ===========================================================
# CELDA 5 — Leer precios del último mes para esas sucursales
# ===========================================================
zip_path, PERIODO, archivos = detectar_ultimo_mes(SEPA_DIR, PERIODO)
print(f'Mes: {PERIODO}  | ZIP: {zip_path.name}')
print(f'Archivos: {archivos}')

keys_sel = set(sel['key'])
_parts = []
_all_days = set()
_factor_sample = []   # muestra GLOBAL de precios del mes (robusta para detectar centavos/pesos)
for arch in archivos:
    tmp_p = TMP_DIR / Path(arch).name
    with zipfile.ZipFile(zip_path) as zf:
        with zf.open(arch) as s, open(tmp_p, 'wb') as d:
            import shutil; shutil.copyfileobj(s, d, length=4 * 1024 * 1024)
    with gzip.open(tmp_p, 'rt', encoding='utf-8', errors='replace') as g:
        for chunk in pd.read_csv(g, dtype=str, chunksize=300_000, low_memory=False):
            chunk['key'] = (chunk['id_comercio'].map(nid) + '|' +
                            chunk['id_bandera'].map(nid) + '|' +
                            chunk['id_sucursal'].map(nid))
            cols_p = [c for c in chunk.columns if re.match(r'^precio_\\d{8}$', c)]
            _all_days.update(cols_p)
            # Muestra global (ANTES de filtrar por sucursal) para el factor
            if len(_factor_sample) < 500_000 and cols_p:
                _v = pd.to_numeric(chunk[cols_p[0]].replace('NA', np.nan), errors='coerce')
                _factor_sample.extend(_v.dropna().tolist())
            chunk = chunk[chunk['key'].isin(keys_sel)]
            if len(chunk) == 0: continue
            _parts.append(chunk[['key', 'id_producto'] + cols_p])
    tmp_p.unlink(missing_ok=True)

if not _parts:
    raise RuntimeError('Las sucursales seleccionadas no reportaron precios este mes.')

# parte1 (días 1-15) y parte2 (16-fin) traen columnas de día distintas -> unión
day_cols = sorted(_all_days)
df_precios = pd.concat(_parts, ignore_index=True)
del _parts
for c in day_cols:
    if c not in df_precios.columns:
        df_precios[c] = np.nan
    df_precios[c] = pd.to_numeric(df_precios[c].replace('NA', np.nan), errors='coerce')
# Precio <= 0 = sin precio válido -> NaN (mismo criterio que nb02)
df_precios[day_cols] = df_precios[day_cols].where(df_precios[day_cols] > 0)
# Combinar las dos mitades en UNA fila por (sucursal, producto) — first() ignora NaN
df_precios = df_precios.groupby(['key', 'id_producto'], as_index=False)[day_cols].first()

# Factor centavos -> pesos (mediana GLOBAL del mes -> robusta ante subconjuntos sesgados)
_med = float(np.median(_factor_sample)) if _factor_sample else float(np.nanmedian(df_precios[day_cols].values))
FACTOR = 100 if _med > 10_000 else 1
if FACTOR == 100:
    df_precios[day_cols] = df_precios[day_cols] / 100
print(f'Factor detectado: ÷{FACTOR} (mediana global del mes: {_med:,.0f})')

# Descartar productos sin ningún precio válido en el mes
df_precios = df_precios[df_precios[day_cols].notna().any(axis=1)].reset_index(drop=True)

# Quedarnos con las sucursales que efectivamente tienen datos
keys_con_datos = set(df_precios['key'])
sel = sel[sel['key'].isin(keys_con_datos)].reset_index(drop=True)
df_precios['ean_norm'] = df_precios['id_producto'].map(normalizar_ean)
df_precios['EAN'] = df_precios['id_producto'].astype(str).str.zfill(13)
print(f'Filas de precios: {len(df_precios):,} | sucursales con datos: {len(sel)} | '
      f'días: {len(day_cols)}')"""))

# ── CELL 6 — Construir hojas y exportar Excel ─────────────────────────────────
cells.append(cell_code("""\
# ===========================================================
# CELDA 6 — Construir el Excel (índice + 1 hoja por sucursal + general)
# ===========================================================
def _fecha_col(c):
    d = c.replace('precio_', '')
    return f'{d[:4]}-{d[4:6]}-{d[6:8]}'
_FECHA = {c: _fecha_col(c) for c in day_cols}

if MP_META is not None:
    df_precios = df_precios.merge(MP_META, on='ean_norm', how='left')
else:
    df_precios['descripcion'] = ''; df_precios['marca'] = ''; df_precios['rubro'] = ''

META_COLS = ['EAN', 'descripcion', 'marca', 'rubro']

hojas = []          # (sheet_name, DataFrame)
avg_by_label = {}   # label -> Series(index ean_norm) precio promedio del mes
meta_by_ean = {}    # ean_norm -> dict de metadata
idx_rows = []

for _, s in sel.iterrows():
    sub = df_precios[df_precios['key'] == s['key']].drop_duplicates('ean_norm', keep='first').copy()
    if len(sub) == 0: continue
    sub['_avg'] = sub[day_cols].mean(axis=1).round(2)
    avg_by_label[s['label']] = sub.set_index('ean_norm')['_avg']
    for _, r in sub.iterrows():
        meta_by_ean.setdefault(r['ean_norm'],
            {'EAN': r['EAN'], 'descripcion': r.get('descripcion', ''),
             'marca': r.get('marca', ''), 'rubro': r.get('rubro', '')})
    # Hoja de la sucursal: metadata + un precio por día
    hoja = sub[META_COLS + day_cols].copy()
    hoja[day_cols] = hoja[day_cols].round(2)
    hoja = hoja.rename(columns=_FECHA).sort_values(['rubro', 'descripcion'], na_position='last')
    hojas.append((s['sheet'], hoja))
    idx_rows.append({'hoja': s['sheet'], 'cadena': s['cadena'],
                     'sucursal': s['sucursales_nombre'], 'tipo': s['sucursales_tipo'],
                     'localidad': s['localidad'], 'provincia': s.get('PROVINCIA', ''),
                     'lat': s['lat'], 'lon': s['lon'],
                     'distancia_km': round(s['distancia_km'], 2), 'n_productos': len(sub)})

# Hoja General: producto × supermercado (precio promedio del mes)
_labels = list(avg_by_label.keys())
general = pd.DataFrame(avg_by_label)                      # index=ean_norm, NaN donde falta
general['promedio_general'] = general[_labels].mean(axis=1).round(2)
_meta = pd.DataFrame.from_dict(meta_by_ean, orient='index')
general = _meta.join(general)
general = general[META_COLS + _labels + ['promedio_general']]
general = general.sort_values(['rubro', 'descripcion'], na_position='last').reset_index(drop=True)

df_index = pd.DataFrame(idx_rows)

out_path = OUTPUT_DIR / f'precios_seleccion_{PERIODO}.xlsx'
with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
    df_index.to_excel(writer, sheet_name='Sucursales', index=False)
    for name, df in hojas:
        df.to_excel(writer, sheet_name=name, index=False)
    general.to_excel(writer, sheet_name='General', index=False)

print(f'Excel guardado: {out_path}')
print(f'  Hojas: Sucursales (índice) + {len(hojas)} sucursales + General')
print(f'  Productos únicos (General): {len(general):,}')

# Descargar
try:
    from google.colab import files
    files.download(str(out_path))
except Exception as e:
    print(f'(Descargá el archivo manualmente desde {out_path}) {e}')"""))

# ── Escribir notebook ─────────────────────────────────────────────────────────
nb = {
    'cells': cells,
    'metadata': {
        'colab': {'provenance': [], 'toc_visible': True},
        'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'},
        'language_info': {'name': 'python'},
    },
    'nbformat': 4,
    'nbformat_minor': 0,
}
out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '04_precios_seleccion.ipynb')
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
print(f'Written: {out_path}')
print(f'Cells: {len(cells)}')
