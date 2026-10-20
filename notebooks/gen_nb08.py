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

**Objetivo:** tomar una canasta de la hoja `Selección` del Excel `canasta_representativa_YYYY-MM.xlsx`
(por defecto la columna `cantidad_01`, Vulnerable) y devolver un Excel con su valor **día por día** desde
`FECHA_INICIO` (2022-01-01) hasta el último día cargado en los ZIPs semestrales de `MyDrive/carga/`
(`2022A.zip`, `2022B.zip`, ..., `2026B.zip`).

**Método** (el de la serie oficial del nb02, CELDA 9, llevado al día):
- Precio del producto en el día = **mediana nacional** de todas las observaciones (sucursal) de ese día.
- `valor_directo` = Σ cantidad × mediana del día, solo con los productos que tienen dato ese día.
- `valor_canasta` (el principal) = índice **encadenado día a día con productos apareados** (cada eslabón compara
  solo los productos con dato en los dos días, con las cantidades de la canasta), llevado a pesos con el
  `valor_directo` del día ancla (el último día con todos los productos). Así un producto que falta unos días,
  o que todavía no existía en 2022, no hace saltar la serie.

**Caché:** cada mes cerrado se guarda en `output_canasta/_cache/diaria_<clave>/AAAA-MM.parquet` (la clave son los
EANs de la canasta; cambiar cantidades no relee). La primera corrida lee todos los meses (~1-1,5 min por mes);
las siguientes, solo el último mes.

**Estructura:** Config → Setup → Canasta desde Excel → Lectura de ZIPs (con caché) → Serie diaria → Gráfico → Excel"""))

# ── CELL 1 — CONFIG ────────────────────────────────────────────────────────────
cells.append(cell_code(r"""# ===========================================================
# CONFIGURACIÓN — Modificar solo esta sección
# ===========================================================
SEPA_DIR   = '/content/drive/MyDrive/carga'                  # ZIPs semestrales 2022A.zip ... 2026B.zip
OUTPUT_DIR = '/content/drive/MyDrive/carga/output_canasta'   # ahí está canasta_representativa_*.xlsx

CANASTA_COL    = 'cantidad_01'     # columna de la hoja Selección con las cantidades de la canasta
CANASTA_EXCEL  = None              # None = el canasta_representativa_*.xlsx más nuevo de OUTPUT_DIR
FECHA_INICIO   = '2022-01-01'
USE_CACHE      = True

# Aviso si un eslabón diario (productos apareados) se mueve más que esto: suele ser un error de carga
# del SEPA o un cambio de unidades (pesos/centavos) en un mes.
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
subprocess.run([sys.executable, '-m', 'pip', 'install', 'openpyxl', 'pyarrow', '-q'], check=False)

import zipfile, gzip, io, re, gc, hashlib, time, warnings
from pathlib import Path
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
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

print(f'SEPA_DIR:   {SEPA_DIR}')
print(f'OUTPUT_DIR: {OUTPUT_DIR}')"""))

# ── CELL 3 — CANASTA ───────────────────────────────────────────────────────────
cells.append(cell_code(r"""# ============================================================
# CELDA 3 — Canasta desde el Excel (columna CANASTA_COL de la hoja Selección)
# ============================================================
import glob as _glob

if CANASTA_EXCEL:
    CANASTA_EXCEL = Path(CANASTA_EXCEL)
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
desc_col = next((c for c in ['descripcion','descripcion_producto','nombre'] if c in sel.columns), sel.columns[3])
cat_col  = next((c for c in ['categoria','rubro'] if c in sel.columns), None)

CANASTA_NAMES = {'cantidad_01': 'Vulnerable', 'cantidad_02': 'Popular', 'cantidad_03': 'Media',
                 'cantidad_04': 'Media Alta', 'cantidad_05': 'Celíaca Media', 'cantidad_06': 'Vegana Básica'}
CANASTA_SHORT = {'cantidad_01': 'vulnerable', 'cantidad_02': 'popular', 'cantidad_03': 'media',
                 'cantidad_04': 'media_alta', 'cantidad_05': 'celiaca_media', 'cantidad_06': 'vegana_basica'}
NOMBRE_CANASTA = CANASTA_NAMES.get(CANASTA_COL, CANASTA_COL)
SHORT_CANASTA  = CANASTA_SHORT.get(CANASTA_COL, CANASTA_COL)

_qty = pd.to_numeric(sel[CANASTA_COL], errors='coerce').fillna(0)
composicion = sel.loc[_qty > 0, ['id_producto', 'ean_norm', desc_col] + ([cat_col] if cat_col else [])].copy()
composicion['cantidad'] = _qty[_qty > 0].values
composicion = (composicion.rename(columns={desc_col: 'descripcion', **({cat_col: 'categoria'} if cat_col else {})})
               .drop_duplicates('ean_norm').reset_index(drop=True))
if composicion.empty:
    raise ValueError(f'La columna {CANASTA_COL} no tiene productos con cantidad > 0')

QTY  = composicion.set_index('ean_norm')['cantidad'].astype(float)
EANS = set(QTY.index)
print(f'Canasta {NOMBRE_CANASTA} ({CANASTA_COL}): {len(EANS)} productos, {QTY.sum():g} unidades')"""))

# ── CELL 4 — LECTURA ───────────────────────────────────────────────────────────
cells.append(cell_code(r"""# ============================================================
# CELDA 4 — Lectura de los ZIPs semestrales: mediana nacional por producto y día
# ============================================================
# Mismo universo que la serie del nb02 (CELDA 9): todas las observaciones del archivo, sin filtro de
# sucursales. Para ir rápido se filtran las LÍNEAS del CSV por EAN antes de parsear (de ~10 M de líneas
# por archivo quedan unas decenas de miles).
_PAT_SEM = re.compile(r'^(\d{4})(A|B)$', re.IGNORECASE)
_PAT_ARC = re.compile(r'^(\d{2})(\d{4})_pais_parte.*COMPLETO.*\.csv\.gz$', re.IGNORECASE)
_PAT_FECHA = re.compile(r'^precio_(\d{8})$')

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
                meses.setdefault(f'{m.group(2)}-{m.group(1)}', []).append(nombre)
    return meses

def _leer_archivo(zf, nombre):
    # Devuelve las líneas del CSV con EANs de la canasta, parseadas (ean_norm + columnas precio_AAAAMMDD)
    with zf.open(nombre) as s, gzip.open(s, 'rt', encoding='utf-8', errors='replace') as g:
        hdr = g.readline()
        cols = [c.strip() for c in hdr.split(',')]
        i_ean = cols.index('id_producto')
        keep = []
        for line in g:
            p = line.split(',', i_ean + 2)
            if len(p) > i_ean and p[i_ean].strip().strip('"').lstrip('0') in EANS:
                keep.append(line)
    if not keep:
        return None
    df = pd.read_csv(io.StringIO(hdr + ''.join(keep)), dtype=str, low_memory=False)
    del keep
    df['ean_norm'] = df['id_producto'].str.strip().str.lstrip('0')
    cols_p = [c for c in df.columns if _PAT_FECHA.match(c)]
    return df[['ean_norm'] + cols_p]

def leer_mes(zip_path, archivos):
    # [fecha, ean_norm, precio_mediano, precio_promedio, n_obs] de un mes, en pesos
    partes = []
    with zipfile.ZipFile(zip_path) as zf:
        for nombre in sorted(archivos):
            df = _leer_archivo(zf, nombre)
            if df is None:
                continue
            lg = df.melt(id_vars='ean_norm', var_name='_c', value_name='precio')
            lg['precio'] = pd.to_numeric(lg['precio'], errors='coerce')
            lg = lg[lg['precio'] > 0]
            lg['fecha'] = pd.to_datetime(lg['_c'].str[-8:], format='%Y%m%d')
            partes.append(lg[['fecha', 'ean_norm', 'precio']])
            del df, lg
    if not partes:
        return None
    obs = pd.concat(partes, ignore_index=True)
    del partes
    # Pesos o centavos: misma regla que la CELDA 9 del nb02 (la CELDA 5 revisa además el salto entre meses)
    if obs['precio'].median() > 10_000:
        obs['precio'] /= 100
    g = obs.groupby(['fecha', 'ean_norm'])['precio']
    agg = g.agg(precio_mediano='median', n_obs='size').reset_index()
    # Promedio sin errores gruesos: fuera lo que está a más de 4x de la mediana del día (como _pmean del nb02)
    obs = obs.merge(agg[['fecha', 'ean_norm', 'precio_mediano']], on=['fecha', 'ean_norm'])
    obs = obs[(obs['precio'] >= obs['precio_mediano'] / 4) & (obs['precio'] <= obs['precio_mediano'] * 4)]
    prom = obs.groupby(['fecha', 'ean_norm'])['precio'].mean().rename('precio_promedio').reset_index()
    del obs; gc.collect()
    return agg.merge(prom, on=['fecha', 'ean_norm'], how='left')

# Meses disponibles -> (zip, archivos)
_mapa_mes = {}
for _z, _a, _s in detectar_semestres():
    for _lbl, _archs in archivos_por_mes(_z).items():
        if _lbl >= FECHA_INICIO[:7]:
            _mapa_mes[_lbl] = (_z, _archs)
MESES = sorted(_mapa_mes)
if not MESES:
    raise RuntimeError(f'No hay ZIPs semestrales (AAAAA.zip / AAAAB.zip) con meses >= {FECHA_INICIO[:7]} en {SEPA_DIR}')
print(f'Meses en los ZIPs: {MESES[0]} -> {MESES[-1]} ({len(MESES)})')
_falta = [str(p) for p in pd.period_range(MESES[0], MESES[-1], freq='M').astype(str) if p not in _mapa_mes]
if _falta:
    print(f'  AVISO: faltan meses en los ZIPs: {_falta}')

# Caché por mes (solo meses cerrados: el último se relee siempre, puede estar en curso)
_clave = hashlib.md5('|'.join(sorted(EANS)).encode()).hexdigest()[:8]
_cache_mes = CACHE_DIR / f'diaria_{_clave}'
if USE_CACHE:
    _cache_mes.mkdir(parents=True, exist_ok=True)

_t0 = time.time()
_lista = []
for _lbl in MESES:
    _p = _cache_mes / f'{_lbl}.parquet'
    if USE_CACHE and _lbl != MESES[-1] and _p.exists():
        _lista.append(pd.read_parquet(_p))
        continue
    _t = time.time()
    _m = leer_mes(*_mapa_mes[_lbl])
    if _m is None:
        print(f'  {_lbl}: sin datos de la canasta')
        continue
    if USE_CACHE and _lbl != MESES[-1]:
        _m.to_parquet(_p, index=False)
    _lista.append(_m)
    print(f'  {_lbl}: {_m["fecha"].nunique()} días, {_m["ean_norm"].nunique()}/{len(EANS)} productos '
          f'({time.time() - _t:.0f} s{"" if _lbl == MESES[-1] else ", guardado en caché"})')

precios_dia = pd.concat(_lista, ignore_index=True)
precios_dia = precios_dia[precios_dia['fecha'] >= pd.Timestamp(FECHA_INICIO)].reset_index(drop=True)
del _lista; gc.collect()
print(f'\nLectura: {time.time() - _t0:.0f} s | {precios_dia["fecha"].nunique():,} días | '
      f'{precios_dia["fecha"].min():%Y-%m-%d} -> {precios_dia["fecha"].max():%Y-%m-%d}')"""))

# ── CELL 5 — SERIE ─────────────────────────────────────────────────────────────
cells.append(cell_code(r"""# ============================================================
# CELDA 5 — Serie diaria: valor directo y valor encadenado con productos apareados
# ============================================================
MED  = precios_dia.pivot(index='fecha', columns='ean_norm', values='precio_mediano').sort_index()
PROM = precios_dia.pivot(index='fecha', columns='ean_norm', values='precio_promedio').reindex(MED.index)
NOBS = precios_dia.pivot(index='fecha', columns='ean_norm', values='n_obs').reindex(MED.index)
_q = QTY.reindex(MED.columns)

def eslabones(P):
    # Eslabón día a día: Σ q·p_t / Σ q·p_{t-1} sobre los productos con dato en los dos días
    prev = P.shift(1)
    both = P.notna() & prev.notna()
    num = P.mul(_q, axis=1).where(both).sum(axis=1)
    den = prev.mul(_q, axis=1).where(both).sum(axis=1)
    return (num / den.replace(0, np.nan)), both.sum(axis=1)

# Cambio de unidades entre meses (un mes en centavos y el vecino en pesos): el eslabón del primer día del
# mes da ~100 o ~0,01. Se corrige el mes entero y se avisa.
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
_compl = n_prod[n_prod == len(EANS)]
ANCLA = _compl.index[-1] if len(_compl) else n_prod[n_prod == n_prod.max()].index[-1]

dir_med, link_med, npar, idx_med, sinpar = serie_valor(MED)
dir_prom, link_prom, _, idx_prom, _ = serie_valor(PROM)
val_med  = idx_med  / idx_med[ANCLA]  * dir_med[ANCLA]
val_prom = idx_prom / idx_prom[ANCLA] * dir_prom[ANCLA]

serie = pd.DataFrame({
    'fecha': MED.index,
    'valor_canasta': val_med.values,
    'variacion_diaria_%': (link_med.values - 1) * 100,
    'indice_base100': (val_med / val_med.iloc[0] * 100).values,
    'valor_directo': dir_med.values,
    'productos_con_dato': n_prod.values,
    'productos_total': len(EANS),
    'cobertura_ponderada_%': (peso_cub * 100).values,
    'productos_apareados': npar.values,
    'observaciones': NOBS.sum(axis=1).astype(int).values,
    'valor_canasta_promedio': val_prom.values,
    'valor_directo_promedio': dir_prom.values,
})
serie.loc[0, 'variacion_diaria_%'] = np.nan
serie['valor_completo'] = serie['productos_con_dato'] == len(EANS)

# Días calendario sin datos en el SEPA (feriados, días no publicados): se listan, no se inventan
_cal = pd.date_range(serie['fecha'].min(), serie['fecha'].max(), freq='D')
DIAS_SIN_DATO = _cal.difference(pd.DatetimeIndex(serie['fecha']))

# Resumen mensual
serie['mes'] = serie['fecha'].dt.to_period('M').astype(str)
resumen = (serie.groupby('mes')
           .agg(dias_con_dato=('fecha', 'size'),
                valor_promedio_mes=('valor_canasta', 'mean'),
                valor_primer_dia=('valor_canasta', 'first'),
                valor_ultimo_dia=('valor_canasta', 'last'),
                valor_minimo=('valor_canasta', 'min'),
                valor_maximo=('valor_canasta', 'max'),
                productos_con_dato_min=('productos_con_dato', 'min'),
                valor_promedio_mes_promedio=('valor_canasta_promedio', 'mean'))
           .reset_index())
resumen['variacion_mensual_%'] = resumen['valor_promedio_mes'].pct_change() * 100
resumen['variacion_punta_a_punta_%'] = resumen['valor_ultimo_dia'].pct_change() * 100
resumen.insert(3, 'variacion_mensual_%', resumen.pop('variacion_mensual_%'))
resumen.insert(6, 'variacion_punta_a_punta_%', resumen.pop('variacion_punta_a_punta_%'))
serie = serie.drop(columns='mes')

# Precios diarios por producto (mediana), para auditar
precios_wide = MED.copy()
precios_wide.columns = [f"{e} | {composicion.set_index('ean_norm').loc[e, 'descripcion']}"[:60] for e in MED.columns]
precios_wide = precios_wide.reset_index()

# Controles
print(f'Canasta {NOMBRE_CANASTA}: {len(serie):,} días con dato ({serie["fecha"].min():%d/%m/%Y} -> '
      f'{serie["fecha"].max():%d/%m/%Y}); días calendario sin dato: {len(DIAS_SIN_DATO)}')
print(f'Día ancla (pesos del valor encadenado): {ANCLA:%d/%m/%Y} con {n_prod[ANCLA]}/{len(EANS)} productos '
      f'= ${dir_med[ANCLA]:,.2f}')
print(f'Días con todos los productos: {int(serie["valor_completo"].sum()):,} de {len(serie):,}')
_nunca = sorted(EANS - set(MED.columns))
if _nunca:
    print(f'  AVISO: {len(_nunca)} productos sin ningún dato en el período: '
          f'{composicion.set_index("ean_norm").loc[_nunca, "descripcion"].tolist()}')
_ini = MED.notna().idxmax()
_tarde = _ini[_ini > MED.index[0] + pd.Timedelta(days=31)].sort_values()
if len(_tarde):
    print(f'  {len(_tarde)} productos aparecen después del primer mes (entran al encadenado desde ese día):')
    for _e, _d in _tarde.items():
        print(f'    {_d:%d/%m/%Y}  {composicion.set_index("ean_norm").loc[_e, "descripcion"]}')
if sinpar.iloc[1:].any():
    print(f'  AVISO: {int(sinpar.iloc[1:].sum())} días sin productos en común con el anterior (eslabón = 1)')
_salto = serie[(serie['variacion_diaria_%'].abs() > ALERTA_ESLABON * 100)]
if len(_salto):
    print(f'  AVISO: {len(_salto)} días con variación diaria mayor a ±{ALERTA_ESLABON:.0%}:')
    print(_salto[['fecha', 'variacion_diaria_%', 'productos_apareados', 'valor_canasta']].head(15).to_string(index=False))
_u = serie.iloc[-1]
print(f'\nÚltimo día {_u["fecha"]:%d/%m/%Y}: ${_u["valor_canasta"]:,.2f} '
      f'({int(_u["productos_con_dato"])}/{len(EANS)} productos)')
print(f'Primer día {serie.iloc[0]["fecha"]:%d/%m/%Y}: ${serie.iloc[0]["valor_canasta"]:,.2f}')
print(resumen[['mes', 'dias_con_dato', 'valor_promedio_mes', 'variacion_mensual_%', 'productos_con_dato_min']]
      .tail(12).to_string(index=False))"""))

# ── CELL 6 — GRÁFICO ───────────────────────────────────────────────────────────
cells.append(cell_code(r"""# ============================================================
# CELDA 6 — Gráfico de control
# ============================================================
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 8), sharex=True, gridspec_kw={'height_ratios': [3, 1]})
ax1.plot(serie['fecha'], serie['valor_canasta'], color='#375623', lw=1.2, label='Valor encadenado (mediana)')
ax1.plot(serie['fecha'], serie['valor_directo'], color='#92D050', lw=0.8, alpha=0.8,
         label='Valor directo (solo productos con dato)')
ax1.set_yscale('log')
ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'${v:,.0f}'))
ax1.set_title(f'Canasta {NOMBRE_CANASTA} — valor diario (escala logarítmica)')
ax1.legend()
ax2.plot(serie['fecha'], serie['productos_con_dato'], color='gray', lw=0.8)
ax2.axhline(len(EANS), color='#375623', ls=':', lw=0.8)
ax2.set_ylabel('productos con dato')
plt.tight_layout()
plt.show()"""))

# ── CELL 7 — EXCEL ─────────────────────────────────────────────────────────────
cells.append(cell_code(r"""# ============================================================
# CELDA 7 — Exportación Excel
# ============================================================
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.utils import get_column_letter

VERDE_OSCURO = '375623'      # mismos colores que el Excel del nb02
HDR_FILL = PatternFill(start_color=VERDE_OSCURO, end_color=VERDE_OSCURO, fill_type='solid')
HDR_FONT = Font(bold=True, color='FFFFFF', size=10)
HDR_ALIG = Alignment(horizontal='center', wrap_text=True, vertical='center')

def fmt_ws(ws, ancho_primera=12):
    ws.row_dimensions[1].height = 30
    ws.freeze_panes = 'B2'
    for cell in ws[1]:
        cell.fill = HDR_FILL; cell.font = HDR_FONT; cell.alignment = HDR_ALIG
    for ci in range(1, ws.max_column + 1):
        hdr = str(ws.cell(1, ci).value or '').lower()
        ws.column_dimensions[get_column_letter(ci)].width = (ancho_primera if ci == 1 else
                                                             42 if 'desc' in hdr or '|' in hdr else 15)
        fmt = ('DD/MM/YYYY' if hdr == 'fecha' else '+0.00"%";-0.00"%"' if '%' in hdr and 'cobertura' not in hdr
               else '0.0' if 'cobertura' in hdr else '#,##0.00' if any(x in hdr for x in ('valor', 'precio', '|', 'indice'))
               else None)
        if fmt:
            for (cell,) in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=ci, max_col=ci):
                cell.number_format = fmt

_desde, _hasta = serie['fecha'].min(), serie['fecha'].max()
notas = pd.DataFrame({'nota': [
    f'Canasta {NOMBRE_CANASTA} (columna {CANASTA_COL} de la hoja Selección de {CANASTA_EXCEL.name}): '
    f'{len(EANS)} productos, {QTY.sum():g} unidades.',
    f'Período: {_desde:%d/%m/%Y} a {_hasta:%d/%m/%Y}, {len(serie):,} días con dato del SEPA '
    f'({len(DIAS_SIN_DATO)} días calendario sin dato publicados; no se completan).',
    'Precio de un producto en un día = mediana nacional de todas las observaciones (sucursales) de ese día en los '
    'archivos COMPLETO de los ZIPs semestrales, sin filtro de sucursales (como la serie oficial del nb02, CELDA 9).',
    'valor_directo = suma de cantidad x mediana del día, solo con los productos que tienen dato ese día '
    '(si falta un producto, baja).',
    'valor_canasta (principal) = índice encadenado día a día: cada eslabón = suma q x p(t) / suma q x p(t-1) sobre los '
    'productos con dato en los dos días (productos apareados), llevado a pesos con el valor_directo del día ancla '
    f'({ANCLA:%d/%m/%Y}, {int(n_prod[ANCLA])}/{len(EANS)} productos = ${dir_med[ANCLA]:,.2f}). En los días con todos los '
    'productos, la diferencia con valor_directo muestra el desvío acumulado del encadenado.',
    'variacion_diaria_% = eslabón del día - 1. indice_base100 = valor_canasta / valor del primer día x 100.',
    'valor_canasta_promedio / valor_directo_promedio: lo mismo con el promedio de las sucursales sin los valores a más de '
    '4 veces de la mediana del día (el criterio del análisis promedio del nb02).',
    'Resumen_mensual: variacion_mensual_% compara el promedio de los días del mes; variacion_punta_a_punta_%, el último '
    'día de cada mes. El último mes puede estar incompleto (ver dias_con_dato).',
    'Pesos o centavos: un mes se pasa a pesos si su mediana supera 10.000 (regla del nb02); además se corrige un mes '
    'entero si el eslabón de su primer día da más de 30 o menos de 1/30 contra el mes anterior.',
    'Precios_diarios: mediana nacional por producto y día (pesos), para auditar.',
    f'Días calendario sin dato: {", ".join(d.strftime("%d/%m/%Y") for d in DIAS_SIN_DATO[:60])}'
    + (' ...' if len(DIAS_SIN_DATO) > 60 else ''),
]})

out_xls = OUTPUT_DIR / f'canasta_diaria_{SHORT_CANASTA}_{_desde:%Y%m%d}_{_hasta:%Y%m%d}.xlsx'
with pd.ExcelWriter(out_xls, engine='openpyxl') as writer:
    serie.to_excel(writer, sheet_name='Serie_diaria', index=False)
    resumen.to_excel(writer, sheet_name='Resumen_mensual', index=False)
    composicion.drop(columns='ean_norm').to_excel(writer, sheet_name='Composicion', index=False)
    precios_wide.to_excel(writer, sheet_name='Precios_diarios', index=False)
    notas.to_excel(writer, sheet_name='Notas', index=False)
    for _sh in ('Serie_diaria', 'Resumen_mensual', 'Composicion', 'Precios_diarios'):
        fmt_ws(writer.sheets[_sh], ancho_primera=16 if _sh == 'Composicion' else 12)
    _wn = writer.sheets['Notas']
    fmt_ws(_wn); _wn.column_dimensions['A'].width = 160
    for (cell,) in _wn.iter_rows(min_row=2, max_col=1):
        cell.alignment = Alignment(wrap_text=True, vertical='top')
print(f'Excel: {out_xls}')
print(f'  Serie_diaria {len(serie):,} filas | Resumen_mensual {len(resumen)} | Composicion {len(composicion)} | '
      f'Precios_diarios {precios_wide.shape[1] - 1} productos')"""))

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
