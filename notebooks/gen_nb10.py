"""Script to generate 10_canasta_reponderada_ipc.ipynb — canasta del nb08 reponderada contra el IPC del INDEC"""
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
cells.append(cell_md("""# Canasta diaria reponderada contra el IPC (y predicción del IPC del mes)

**Qué hace:** pide el Excel `canasta_diaria_*.xlsx` que genera el **nb08**, busca los pesos de la canasta que mejor
siguen la **variación mensual del IPC Nivel general** del INDEC (`MyDrive/carga/IPC.xlsx`) y devuelve **el mismo Excel
con la canasta reponderada**, más la **predicción del IPC del mes en curso** (el mes siguiente al último IPC publicado).

**Cada mes:**
1. Correr el nb08 hasta el último día del SEPA (su Excel sale en `output_canasta/`).
2. Agregar al `IPC.xlsx` de `MyDrive/carga/` la fila del último mes que publicó el INDEC.
3. Abrir este notebook, **Entorno de ejecución → Ejecutar todas**, y subir el Excel del nb08 cuando lo pida.
4. Se descarga `<nombre del Excel>_reponderada_ipc.xlsx` (también queda en `output_canasta/`).

**Método** (detalle en `docs/PASS_THROUGH.md` §7):
- Se reponderan los **16 grupos del IPC** de la canasta (`DIM_REPONDERACION`): las cantidades de los productos de un
  grupo se multiplican por un mismo factor (dentro del grupo las proporciones no cambian) y el valor de la canasta en el
  día ancla no cambia.
- Los pesos nuevos minimizan el error cuadrático entre la variación mensual de la canasta (promedio de los días del mes,
  como mide el IPC) y la del IPC Nivel general, con una penalización `λ` por alejarse de los pesos originales. La ventana
  de estimación y `λ` se eligen **fuera de muestra**: para cada mes desde `BACKTEST_DESDE` se estiman los pesos solo con
  los meses anteriores y se mide el error del mes; gana la combinación con menor error medio en los últimos
  `MESES_CRITERIO` meses (entre los candidatos está **no reponderar**). Con la elegida, los pesos finales usan todos los
  meses con IPC.
- Se recalculan con las cantidades nuevas: `Serie_diaria`, `Resumen_mensual`, `Rubros_*`, `Indices_por_grupo` y
  `Composicion` (con `cantidad_original` y `factor_reponderacion`). **`Provincias_*` quedan como vienen** (canasta
  original: el Excel no trae los precios por provincia) y los valores con el promedio de sucursales
  (`valor_canasta_promedio`, `valor_directo_promedio`, `valor_promedio_mes_promedio`) quedan vacíos (el Excel no trae los
  precios promedio por producto).
- Antes de reponderar, el notebook **recalcula el Excel con las cantidades originales y lo compara con el del nb08**: si
  no da igual, se detiene.

**Predicción del IPC** (hoja `Prediccion_IPC`): la variación del mes anterior (RW), la de la canasta, RW + b × la
aceleración de la canasta, una regresión con la canasta y el rezago, y un **puente por divisiones** (las divisiones que
la canasta cubre se mueven con ella; el resto, como el mes anterior o con los `SUPUESTOS` que se carguen: tarifas,
transporte, prepagas...). **Central** = promedio de los tres últimos, con un intervalo del 80% sacado de sus errores
fuera de muestra. Todo, con la canasta reponderada y con la original.

> **Ojo:** la canasta son productos de supermercado (menos de un tercio del IPC). En el backtest de oct-2026 ningún
> modelo le ganó con claridad a repetir la variación del mes anterior, y reponderar mejoró poco (ver `Reponderacion_seleccion`
> y `Prediccion_IPC`). Los `SUPUESTOS` de precios regulados son lo que más puede mejorar la predicción.

**Estructura:** Config → Setup → Excel del nb08 e IPC → Control (recalcular con las cantidades originales) → Pesos
nuevos → Excel reponderado → Predicción del IPC → Gráficos → Exportación"""))

# ── CELL 1 — CONFIG ────────────────────────────────────────────────────────────
cells.append(cell_code(r"""# ===========================================================
# CONFIGURACIÓN — Modificar solo esta sección
# ===========================================================
SEPA_DIR   = '/content/drive/MyDrive/carga'                  # donde está IPC.xlsx
OUTPUT_DIR = '/content/drive/MyDrive/carga/output_canasta'   # donde queda el Excel reponderado
IPC_XLSX   = 'IPC.xlsx'          # IPC del INDEC: columna de fechas, 'Nivel general' y las 12 divisiones (base dic-2016=100)

# Excel del nb08 (canasta_diaria_*.xlsx). None = el notebook pide subirlo. También puede ser una ruta del Drive.
CANASTA_EXCEL = None
DESCARGAR = True                 # descargar el Excel reponderado al terminar (Colab)

# Reponderación
DIM_REPONDERACION = 'grupo'      # columna de Composicion: 'grupo' (16 grupos del IPC), 'tipo' (6 rubros) o 'categoria'
VENTANAS = ['2022-02', '2024-04']                # primer mes de la ventana de estimación (candidatos)
LAMBDAS  = [None, 100, 30, 10, 3, 1, 0.3, 0]     # penalización por alejarse de los pesos originales; None = no reponderar
BACKTEST_DESDE = '2024-07'       # primer mes del backtest fuera de muestra
MESES_CRITERIO = 12              # se elige la combinación con menor error medio en estos últimos meses del backtest

# Predicción del IPC
INICIO_REGIMEN = '2024-04'       # ventana de la regresión canasta + rezago (después de la desinflación)
PUENTE_DIVISIONES = ['01', '02'] # divisiones del IPC que se mueven con su parte de la canasta (01 alimentos, 02 alcohol)
# Variación % ya conocida de alguna división en el mes a predecir (tarifas, colectivos, nafta, prepagas...). Ejemplo:
# SUPUESTOS = {'Transporte': 3.5, 'Vivienda, agua, electricidad, gas y otros combustibles': 2.8}
SUPUESTOS = {}"""))

# ── CELL 2 — SETUP ─────────────────────────────────────────────────────────────
cells.append(cell_code(r"""# ============================================================
# CELDA 2 — Montar Drive + imports
# ============================================================
try:
    import google.colab
    from google.colab import drive
    drive.mount('/content/drive')
    EN_COLAB = True
    print('Google Drive montado')
except ImportError:
    EN_COLAB = False
    print('Entorno local')

import subprocess, sys
subprocess.run([sys.executable, '-m', 'pip', 'install', 'openpyxl', 'xlsxwriter', 'scipy', '-q'], check=False)

import re, time, warnings, unicodedata
from pathlib import Path
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from scipy.optimize import minimize

pd.set_option('display.max_columns', 50)
pd.set_option('display.width', 200)

SEPA_DIR   = Path(SEPA_DIR)
OUTPUT_DIR = Path(OUTPUT_DIR)
NG = 'Nivel general'

def _norm(s):
    # minúsculas sin tildes, para reconocer columnas
    return unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().lower().strip()"""))

# ── CELL 3 — ENTRADAS ──────────────────────────────────────────────────────────
cells.append(cell_code(r"""# ============================================================
# CELDA 3 — Excel del nb08 (se sube) e IPC del INDEC (IPC.xlsx del Drive)
# ============================================================
def _subir(texto, patron):
    from google.colab import files
    print(texto)
    _up = files.upload()
    if not _up:
        raise ValueError('No se subió ningún archivo.')
    _nom = next((n for n in _up if re.search(patron, n, re.I)), next(iter(_up)))
    _ruta = Path('/content') / _nom
    _ruta.write_bytes(_up[_nom])
    return _ruta

if CANASTA_EXCEL:
    EXCEL_IN = Path(CANASTA_EXCEL)
elif EN_COLAB:
    EXCEL_IN = _subir('Subí el Excel canasta_diaria_*.xlsx del nb08:', r'canasta_diaria.*\.xlsx$')
else:
    raise ValueError('Fuera de Colab hay que poner la ruta del Excel del nb08 en CANASTA_EXCEL.')
if not EXCEL_IN.exists():
    raise FileNotFoundError(f'No existe {EXCEL_IN}')
print(f'Excel del nb08: {EXCEL_IN.name} ({EXCEL_IN.stat().st_size / 1e6:,.1f} MB). Leyendo...')
_t0 = time.time()
HOJAS = pd.read_excel(EXCEL_IN, sheet_name=None)
HOJAS['Composicion'] = pd.read_excel(EXCEL_IN, sheet_name='Composicion', dtype={'id_producto': str})
_faltan = [h for h in ('Serie_diaria', 'Resumen_mensual', 'Composicion', 'Indices_por_grupo', 'Precios_diarios',
                       'Precios_apareados', 'Notas') if h not in HOJAS]
if _faltan:
    raise ValueError(f'El Excel no parece del nb08: le faltan las hojas {_faltan}')
print(f'  {len(HOJAS)} hojas en {time.time() - _t0:,.0f} s: {list(HOJAS)}')

# IPC del INDEC: IPC.xlsx del Drive (si no está, se pide)
DIVISIONES = [  # código COICOP, nombre en el IPC, ponderación nacional del INDEC (%), clave para reconocer la columna
    ('01', 'Alimentos y bebidas no alcohólicas', 26.9, 'alimentos'),
    ('02', 'Bebidas alcohólicas y tabaco', 3.5, 'bebidas alcoh'),
    ('03', 'Prendas de vestir y calzado', 9.9, 'prendas'),
    ('04', 'Vivienda, agua, electricidad, gas y otros combustibles', 9.4, 'vivienda'),
    ('05', 'Equipo y mantenimiento del hogar', 6.4, 'equip'),
    ('06', 'Salud', 8.0, 'salud'),
    ('07', 'Transporte', 11.0, 'transporte'),
    ('08', 'Comunicación', 2.8, 'comunicacion'),
    ('09', 'Recreación y cultura', 7.3, 'recreacion'),
    ('10', 'Educación', 2.3, 'educacion'),
    ('11', 'Restaurantes y hoteles', 9.0, 'restaurantes'),
    ('12', 'Bienes y servicios varios', 3.5, 'bienes y servicios'),
]
_MESES_ES = {'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6, 'jul': 7, 'ago': 8, 'sep': 9, 'set': 9,
             'oct': 10, 'nov': 11, 'dic': 12}

def _mes_ipc(v):
    # fecha del IPC: datetime, '2026-09', 'sept-2026' o 'sep-26'
    if isinstance(v, (pd.Timestamp, np.datetime64)) or hasattr(v, 'year'):
        return pd.Timestamp(v).to_period('M')
    s = _norm(v)
    m = re.match(r'^([a-z]+)[\s\-/\.]+(\d{2,4})$', s)
    if m and m.group(1)[:3] in _MESES_ES:
        a = int(m.group(2))
        return pd.Period(year=a + 2000 if a < 100 else a, month=_MESES_ES[m.group(1)[:3]], freq='M')
    try:
        return pd.Timestamp(pd.to_datetime(v)).to_period('M')
    except (ValueError, TypeError):
        return None            # filas de notas o vacías: no son meses

def leer_ipc(ruta):
    d = pd.read_excel(ruta)
    _cf = next((c for c in d.columns if _norm(c) in ('date', 'fecha', 'mes', 'periodo', 'period')), d.columns[0])
    d = d[d[_cf].notna()].copy()
    _ms = [_mes_ipc(v) for v in d[_cf]]
    d = d[[m is not None for m in _ms]].copy()
    d.index = pd.PeriodIndex([m for m in _ms if m is not None], freq='M')
    _cols = {}
    for c in d.columns:
        n = _norm(c)
        if n.startswith('nivel general'):
            _cols[c] = NG
        else:
            for _cod, _nom, _w, _clave in DIVISIONES:
                if n.startswith(_clave):
                    _cols[c] = _nom
    if NG not in _cols.values():
        raise ValueError(f'{ruta.name} no tiene la columna Nivel general (columnas: {list(d.columns)})')
    d = d[list(_cols)].rename(columns=_cols)
    for c in d.columns:
        d[c] = pd.to_numeric(d[c].astype(str).str.replace(',', '.', regex=False), errors='coerce')
    d = d[d[NG].notna()].sort_index()
    return d[~d.index.duplicated(keep='last')]

_cand = [SEPA_DIR / IPC_XLSX] + [SEPA_DIR / n for n in ('IPC.xlsx', 'ipc.xlsx', 'IPC.XLSX')]
IPC_PATH = next((p for p in _cand if p.exists()), None)
if IPC_PATH is None:
    if not EN_COLAB:
        raise FileNotFoundError(f'No está {IPC_XLSX} en {SEPA_DIR}')
    IPC_PATH = _subir(f'No encontré {IPC_XLSX} en {SEPA_DIR}. Subilo:', r'ipc.*\.xlsx$')
IPC = leer_ipc(IPC_PATH)
DIV_IPC = [n for _, n, _, _ in DIVISIONES if n in IPC.columns]
PI = IPC[NG].pct_change() * 100                       # variación mensual del IPC Nivel general (%)
print(f'IPC: {IPC_PATH.name}, {IPC.index.min()} -> {IPC.index.max()}, {len(DIV_IPC)} de 12 divisiones')
print(IPC[[NG]].assign(var_mm=PI).tail(4).round(2).to_string())
if len(DIV_IPC) == 12:
    # control: las divisiones con las ponderaciones del INDEC dan la variación del nivel general
    _W0 = pd.Series({n: w for _, n, w, _ in DIVISIONES})
    _wt = IPC[DIV_IPC].shift(1).mul(_W0)
    _agr = (IPC[DIV_IPC].pct_change() * 100).mul(_wt).sum(axis=1) / _wt.sum(axis=1)
    print(f'Control ponderaciones: las divisiones reproducen la variación del nivel general con error medio '
          f'{(_agr - PI).iloc[1:].abs().mean():.3f} pp (máx. {(_agr - PI).iloc[1:].abs().max():.3f})')
else:
    print('  AVISO: IPC.xlsx no trae las 12 divisiones: la predicción no usa el puente por divisiones.')"""))

# ── CELL 4 — CONTROL ───────────────────────────────────────────────────────────
cells.append(cell_code(r"""# ============================================================
# CELDA 4 — Recalcular el Excel con las cantidades originales (tiene que dar igual al del nb08)
# ============================================================
SERIE_X = HOJAS['Serie_diaria'].copy()
SERIE_X['fecha'] = pd.to_datetime(SERIE_X['fecha'])

def _matriz(df):
    m = df.copy()
    m['fecha'] = pd.to_datetime(m['fecha'])
    m = m.set_index('fecha')
    m.columns = [str(c).split(' | ')[0].strip().lstrip('0') for c in m.columns]
    return m.astype(float)

MED  = _matriz(HOJAS['Precios_diarios'])      # mediana nacional por producto y día
P_AP = _matriz(HOJAS['Precios_apareados'])    # índice de sucursales apareadas en pesos
if not (MED.index.equals(pd.DatetimeIndex(SERIE_X['fecha'])) and P_AP.index.equals(MED.index)
        and list(P_AP.columns) == list(MED.columns)):
    raise ValueError('Precios_diarios, Precios_apareados y Serie_diaria no tienen los mismos días y productos')

COMP = HOJAS['Composicion'].copy()
COMP['id_producto'] = COMP['id_producto'].astype(str).str.strip()
COMP['ean_norm'] = COMP['id_producto'].str.lstrip('0')
COMP_IDX = COMP.set_index('ean_norm')
Q0 = COMP_IDX['cantidad'].astype(float).reindex(MED.columns)
if Q0.isna().any():
    raise ValueError(f'{int(Q0.isna().sum())} productos de los precios no están en Composicion')
if DIM_REPONDERACION not in COMP or COMP[DIM_REPONDERACION].isna().any():
    raise ValueError(f'Composicion no trae la columna {DIM_REPONDERACION} completa (columnas: {list(COMP.columns)})')

def eslabones(P, q):
    # Eslabón día a día: Σ q·p_t / Σ q·p_{t-1} sobre los productos con dato en los dos días (como el nb08)
    prev = P.shift(1)
    both = P.notna() & prev.notna()
    num = P.mul(q, axis=1).where(both).sum(axis=1)
    den = prev.mul(q, axis=1).where(both).sum(axis=1)
    return (num / den.replace(0, np.nan)), both.sum(axis=1)

def serie_valor(P, q):
    _dir = P.mul(q, axis=1).sum(axis=1, min_count=1)
    _l, _np = eslabones(P, q)
    _l.iloc[0] = 1.0
    _sin_par = _l.isna()
    _idx = _l.fillna(1.0).cumprod()
    return _dir, _l, _np, _idx, _sin_par

# Día ancla (como el nb08): el último con todos los productos de la canasta
NE = int(SERIE_X['productos_total'].iloc[0])
_n_prod = MED.notna().sum(axis=1)
_compl = _n_prod[_n_prod == NE]
ANCLA = _compl.index[-1] if len(_compl) else _n_prod[_n_prod == _n_prod.max()].index[-1]

def valor(P, q):
    # valor encadenado en pesos del día ancla
    _d, _l, _, _i, _ = serie_valor(P, q)
    return _i / _i[ANCLA] * _d[ANCLA], _l, _d

def calc_serie(q, promedio=True):
    q = q.reindex(MED.columns).astype(float)
    val_med, link_med, dir_med = valor(MED, q)
    val_ap, link_ap, _ = valor(P_AP, q)
    s = SERIE_X.copy()
    s['valor_canasta'] = val_med.values
    s['variacion_diaria_%'] = (link_med.values - 1) * 100
    s['indice_base100'] = (val_med / val_med.iloc[0] * 100).values
    s['valor_canasta_apareado'] = val_ap.values
    s['variacion_diaria_apareada_%'] = (link_ap.values - 1) * 100
    s['indice_apareado_base100'] = (val_ap / val_ap.iloc[0] * 100).values
    s['valor_directo'] = dir_med.values
    s['cobertura_ponderada_%'] = (MED.notna().mul(q, axis=1).sum(axis=1) / q.sum() * 100).values
    s.loc[0, ['variacion_diaria_%', 'variacion_diaria_apareada_%']] = np.nan
    if not promedio:   # el Excel no trae los precios promedio por producto
        s['valor_canasta_promedio'] = np.nan
        s['valor_directo_promedio'] = np.nan
    return s, val_ap

def calc_resumen(serie):
    serie = serie.copy()
    serie['mes'] = serie['fecha'].dt.to_period('M').astype(str)
    r = (serie.groupby('mes')
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
    r.insert(4, 'variacion_mensual_%', r['valor_promedio_mes'].pct_change() * 100)
    r.insert(7, 'variacion_punta_a_punta_%', r['valor_ultimo_dia'].pct_change() * 100)
    r['variacion_mensual_apareada_%'] = r['valor_promedio_mes_apareado'].pct_change() * 100
    r['variacion_punta_a_punta_apareada_%'] = r['valor_ultimo_dia_apareado'].pct_change() * 100
    return r[HOJAS['Resumen_mensual'].columns]

# ── Rubros (como la CELDA 5 del nb08) ──
DIM_RUBRO = next((c for c in ('tipo', 'categoria') if c in COMP_IDX and COMP_IDX[c].notna().any()), None)

def _mensual(V):
    M = V.groupby(V.index.to_period('M')).mean()
    M.index = M.index.astype(str)
    M.index.name = 'mes'
    return M

def _antes(M, k):
    p = pd.PeriodIndex(M.index, freq='M')
    return M.iloc[p.get_loc(p[-1] - k)] if (p[-1] - k) in p else M.iloc[-1] * np.nan

def _var(M, k):
    return (M.iloc[-1] / _antes(M, k) - 1) * 100

def resumen_vs_ng(V, nombre):
    M = _mensual(V)
    u, p0 = V.iloc[-1], V.iloc[0]
    r = pd.DataFrame({'valor_primer_dia': p0, 'valor_ultimo_dia': u,
                      'variacion_periodo_%': (u / p0 - 1) * 100,
                      'variacion_12_meses_%': _var(M, 12),
                      'variacion_ultimo_mes_%': _var(M, 1)})
    for c in ('variacion_periodo_%', 'variacion_12_meses_%', 'variacion_ultimo_mes_%'):
        r[f'dif_{c[:-2]}_vs_NG_pp'] = r[c] - r.at[NG, c]
    return r.rename_axis(nombre).reset_index()

def calc_rubros(q, val_ap):
    # rubros con cantidad > 0 (un rubro que la reponderación deja en cero no sale)
    q = q.reindex(MED.columns).astype(float)
    val_rub, n_rub = {}, {}
    for _g, _ix in sorted(COMP_IDX.groupby(DIM_RUBRO).groups.items()):
        _cs = [e for e in _ix if e in P_AP.columns]
        if _cs and q[_cs].sum() > 0:
            val_rub[_g] = valor(P_AP[_cs], q[_cs])[0]
            n_rub[_g] = int((q[_cs] > 0).sum())
    rub_val = pd.DataFrame({NG: val_ap, **val_rub})
    rub_mensual = _mensual(rub_val)
    out = {'Rubros_mensual': (rub_mensual.pct_change() * 100).reset_index(),
           'Rubros_diario': (rub_val / rub_val.iloc[0] * 100).reset_index()}
    _ru = [c for c in rub_mensual.columns if c != NG]
    inc = rub_mensual[_ru].diff().div(rub_mensual[NG].shift(), axis=0) * 100
    inc['Suma de rubros'] = inc[_ru].sum(axis=1, min_count=1)
    inc[f'{NG} (variación %)'] = rub_mensual[NG].pct_change() * 100
    out['Rubros_incidencia'] = inc.reset_index()
    rr = resumen_vs_ng(rub_val, 'rubro')
    rr.insert(1, 'productos', rr['rubro'].map(n_rub).fillna(int((q > 0).sum())).astype(int))
    rr.insert(2, 'peso_primer_dia_%', rr['valor_primer_dia'] / rub_val[NG].iloc[0] * 100)
    rr.insert(3, 'peso_ultimo_dia_%', rr['valor_ultimo_dia'] / rub_val[NG].iloc[-1] * 100)
    rr['incidencia_periodo_pp'] = (rr['valor_ultimo_dia'] - rr['valor_primer_dia']) / rub_val[NG].iloc[0] * 100
    _a12 = _antes(rub_mensual, 12)
    rr['incidencia_12_meses_pp'] = rr['rubro'].map((rub_mensual.iloc[-1] - _a12) / _a12[NG] * 100)
    rr.loc[rr['rubro'] == NG, ['incidencia_periodo_pp', 'incidencia_12_meses_pp']] = np.nan
    out['Rubros_resumen'] = rr
    for k in out:
        out[k].columns = [str(c) for c in out[k].columns]
    out['Rubros_diario'] = out['Rubros_diario'].rename(columns={'index': 'fecha'})
    return {k: v for k, v in out.items() if k in HOJAS}

# ── Índices por grupo: las columnas 'dimensión | grupo' del Excel ──
_ETIQ = {}
for _d in ('tipo', 'grupo', 'categoria'):
    if _d in COMP_IDX:
        for _g, _ix in COMP_IDX.groupby(_d).groups.items():
            _ETIQ[f'{_d} | {_g}'[:60]] = [e for e in _ix if e in P_AP.columns]

def calc_indices(q, val_ap):
    q = q.reindex(MED.columns).astype(float)
    ix = HOJAS['Indices_por_grupo'].copy()
    ix['fecha'] = pd.to_datetime(ix['fecha'])
    ix['Canasta'] = (val_ap / val_ap.iloc[0] * 100).values
    for c in ix.columns[2:]:
        _cs = _ETIQ.get(c)
        if not _cs:
            continue                      # no se reconoce: queda como viene
        _qq = q[_cs] if q[_cs].sum() > 0 else Q0[_cs]   # grupo en cero: índice de precios con las cantidades originales
        _i = serie_valor(P_AP[_cs], _qq)[3]
        ix[c] = (_i / _i.iloc[0] * 100).values
    return ix

def _difmax(a, b):
    # máxima diferencia relativa entre dos tablas numéricas del mismo tamaño (NaN en las dos posiciones = igual)
    a = a.select_dtypes('number').to_numpy(float)
    b = b.select_dtypes('number').to_numpy(float)
    if a.shape != b.shape:
        return np.inf
    if (np.isnan(a) != np.isnan(b)).any():
        return np.inf
    m = ~np.isnan(a)
    return float(np.max(np.abs(a[m] - b[m]) / np.maximum(np.abs(b[m]), 1.0))) if m.any() else 0.0

_s0, _vap0 = calc_serie(Q0)
_ctrl = {'Serie_diaria': _difmax(_s0, SERIE_X), 'Resumen_mensual': _difmax(calc_resumen(_s0), HOJAS['Resumen_mensual']),
         'Indices_por_grupo': _difmax(calc_indices(Q0, _vap0), HOJAS['Indices_por_grupo'])}
if DIM_RUBRO:
    for _k, _v in calc_rubros(Q0, _vap0).items():
        _ctrl[_k] = _difmax(_v, HOJAS[_k])
print(f'Canasta: {len(MED.columns)} productos, {len(MED):,} días ({MED.index[0]:%d/%m/%Y} -> {MED.index[-1]:%d/%m/%Y}); '
      f'día ancla {ANCLA:%d/%m/%Y}')
print('Control (recalculado con las cantidades originales vs el Excel del nb08, máx. diferencia relativa):')
for _k, _v in _ctrl.items():
    print(f'  {_k:20s} {_v:.1e}')
_mal = {k: v for k, v in _ctrl.items() if not v < 1e-8}
if _mal:
    raise ValueError(f'El recálculo no da igual al Excel en {list(_mal)}: ¿el Excel es del nb08 v3 y no se editó?')
print('OK: el notebook reproduce el Excel del nb08.')"""))

# ── CELL 5 — PESOS ─────────────────────────────────────────────────────────────
cells.append(cell_code(r"""# ============================================================
# CELDA 5 — Pesos nuevos: variación mensual de la canasta lo más parecida a la del IPC (elegidos fuera de muestra)
# ============================================================
# Celdas = grupo de reponderación x grupo del IPC (para el puente por divisiones). Valor de cada celda = su parte de la
# canasta (sucursales apareadas, cantidades originales) encadenada y en pesos del día ancla. Con factores f por grupo, la
# canasta es Σ f x valor de sus celdas; con participaciones s en el día ancla, f = s / s_original (el valor de la canasta
# en el día ancla no cambia).
_dims = [DIM_REPONDERACION] + (['grupo'] if 'grupo' in COMP_IDX and DIM_REPONDERACION != 'grupo' else [])
_celdas = {}
for _k, _ix in COMP_IDX.groupby(_dims).groups.items():
    _k = _k if isinstance(_k, tuple) else (_k,)
    _cs = [e for e in _ix if e in P_AP.columns]
    if _cs:
        _celdas[_k] = valor(P_AP[_cs], Q0[_cs])[0]
VC = pd.DataFrame(_celdas)                               # día x celda
GRUPOS = sorted(set(k[0] for k in VC.columns))
CEL_GRUPO = np.array([GRUPOS.index(k[0]) for k in VC.columns])
CEL_IPC = [k[-1] if 'grupo' in _dims else None for k in VC.columns]   # grupo del IPC de cada celda
MC = VC.groupby(VC.index.to_period('M')).mean()          # promedio de los días de cada mes
VA = VC.loc[ANCLA].groupby(CEL_GRUPO).sum().reindex(range(len(GRUPOS))).to_numpy()
S0 = VA / VA.sum()                                        # participaciones originales en el día ancla

# Meses con todos sus días (se permiten 2 días sin dato en las puntas): solo esos entran en la estimación
_fe = pd.Series(MED.index, index=MED.index)
_pm = _fe.groupby(_fe.index.to_period('M'))
COMPLETO = ((_pm.max().dt.day >= _pm.max().dt.days_in_month - 2) & (_pm.min().dt.day <= 3))
MESES = [m for m in MC.index if m - 1 in MC.index and COMPLETO.get(m, False) and COMPLETO.get(m - 1, False)]

def var_canasta(s, celdas=None):
    # variación mensual (%) de la canasta (o de las celdas indicadas) con participaciones s en el día ancla
    f = (s / np.where(S0 > 0, S0, 1.0))[CEL_GRUPO]
    X = MC.to_numpy() if celdas is None else MC.to_numpy()[:, celdas]
    B = X @ (f if celdas is None else f[celdas])
    return pd.Series(np.r_[np.nan, B[1:] / B[:-1] * 100 - 100], index=MC.index)

def ajustar(meses, lam):
    # participaciones >= 0 que suman 1 y minimizan el error cuadrático medio contra el IPC + lam x Σ (s - s0)²
    if lam is None or not len(meses):
        return S0.copy()
    meses = [m for m in meses if m in PI.index and pd.notna(PI[m])]
    y = PI.reindex(meses).to_numpy()
    pos = MC.index.get_indexer(meses)
    X1, X0 = MC.to_numpy()[pos], MC.to_numpy()[pos - 1]
    den0 = np.where(S0 > 0, S0, 1.0)
    def obj(s):
        f = (s / den0)[CEL_GRUPO]
        return np.mean((X1 @ f / (X0 @ f) * 100 - 100 - y) ** 2) + lam * np.sum((s - S0) ** 2)
    r = minimize(obj, S0, method='SLSQP', bounds=[(0, 1)] * len(S0),
                 constraints=[{'type': 'eq', 'fun': lambda s: s.sum() - 1}], options={'maxiter': 1000, 'ftol': 1e-12})
    s = np.clip(r.x, 0, None)
    s = s / s.sum()
    return s if obj(s) <= obj(S0) else S0.copy()

ULT_IPC = IPC.index.max()
MESES_IPC = [m for m in MESES if m <= ULT_IPC and pd.notna(PI.get(m))]
BT = [m for m in MESES_IPC if m >= pd.Period(BACKTEST_DESDE, 'M')]
if len(BT) < 3:
    raise ValueError(f'Hacen falta al menos 3 meses con IPC desde {BACKTEST_DESDE} para elegir los pesos (hay {len(BT)})')

_t0 = time.time()
PESOS_BT, _filas = {}, []
for _v in VENTANAS:
    for _lam in LAMBDAS:
        _e = []
        for _m in BT:
            _tr = [x for x in MESES_IPC if pd.Period(_v, 'M') <= x < _m]
            _s = ajustar(_tr, _lam)
            PESOS_BT[(_v, _lam, _m)] = _s
            _e.append(var_canasta(_s)[_m] - PI[_m])
        _e = np.array(_e)
        _filas.append({'ventana_desde': _v, 'lambda': 'sin reponderar' if _lam is None else _lam,
                       'MAE_backtest_pp': np.abs(_e).mean(), f'MAE_ultimos_{MESES_CRITERIO}m_pp': np.abs(_e[-MESES_CRITERIO:]).mean(),
                       'sesgo_pp': _e.mean(), 'meses': len(_e), '_v': _v, '_lam': _lam})
SELECCION = pd.DataFrame(_filas)
# gana el menor error en los últimos meses; los empates, el que menos se aleja de los pesos originales (orden de LAMBDAS)
_crit = f'MAE_ultimos_{MESES_CRITERIO}m_pp'
_best = SELECCION[_crit].round(6).idxmin()
SELECCION['elegido'] = SELECCION.index == _best
VENTANA, LAMBDA = SELECCION.at[_best, '_v'], SELECCION.at[_best, '_lam']
SELECCION = SELECCION.drop(columns=['_v', '_lam'])
print(f'Backtest de la reponderación ({BT[0]} -> {BT[-1]}, {len(BT)} meses, {time.time() - _t0:,.0f} s); error de la '
      f'variación mensual de la canasta contra el IPC (pp):')
print(SELECCION.round(3).to_string(index=False))

MESES_FIN = [x for x in MESES_IPC if x >= pd.Period(VENTANA, 'M')]
S_NUEVO = ajustar(MESES_FIN, LAMBDA)
F_GRUPO = pd.Series(S_NUEVO / np.where(S0 > 0, S0, 1.0), index=GRUPOS)
Q_NUEVO = Q0 * COMP_IDX[DIM_REPONDERACION].reindex(MED.columns).map(F_GRUPO).astype(float)
_sin = SELECCION.loc[SELECCION['lambda'] == 'sin reponderar', _crit]
print(f'\nElegido: ventana desde {VENTANA}, lambda = {"sin reponderar" if LAMBDA is None else LAMBDA} '
      f'(error medio últimos {MESES_CRITERIO} meses {SELECCION.loc[SELECCION["elegido"], _crit].iloc[0]:.3f} pp'
      + (f'; sin reponderar {_sin.min():.3f} pp)' if len(_sin) else ')'))
if LAMBDA is None:
    print('  Ninguna reponderación le ganó a los pesos originales fuera de muestra: la canasta queda como está.')
REPONDERACION = pd.DataFrame({DIM_REPONDERACION: GRUPOS,
                              'productos': [int((COMP_IDX[DIM_REPONDERACION] == g).sum()) for g in GRUPOS],
                              'peso_original_%': S0 * 100, 'peso_nuevo_%': S_NUEVO * 100,
                              'cambio_pp': (S_NUEVO - S0) * 100, 'factor_cantidades': F_GRUPO.values})
print(REPONDERACION.round(2).to_string(index=False))"""))

# ── CELL 6 — EXCEL REPONDERADO ─────────────────────────────────────────────────
cells.append(cell_code(r"""# ============================================================
# CELDA 6 — El Excel del nb08 con las cantidades nuevas
# ============================================================
NUEVAS = {}
serie_n, val_ap_n = calc_serie(Q_NUEVO, promedio=False)
NUEVAS['Serie_diaria'] = serie_n
NUEVAS['Resumen_mensual'] = calc_resumen(serie_n)
NUEVAS['Indices_por_grupo'] = calc_indices(Q_NUEVO, val_ap_n)
if DIM_RUBRO:
    NUEVAS.update(calc_rubros(Q_NUEVO, val_ap_n))
_comp = HOJAS['Composicion'].copy()
_comp['id_producto'] = _comp['id_producto'].astype(str)
_q = Q_NUEVO.copy()
_q.index = _q.index.astype(str)
_comp.insert(list(_comp.columns).index('cantidad') + 1, 'cantidad_original', _comp['cantidad'])
_comp['cantidad'] = _comp['id_producto'].str.lstrip('0').map(_q).fillna(0.0)
_comp.insert(list(_comp.columns).index('cantidad_original') + 1, 'factor_reponderacion',
             _comp[DIM_REPONDERACION].map(F_GRUPO).values)
NUEVAS['Composicion'] = _comp

# Controles
_va0 = SERIE_X.set_index('fecha').loc[ANCLA, 'valor_canasta_apareado']
_va1 = serie_n.set_index('fecha').loc[ANCLA, 'valor_canasta_apareado']
print(f'Valor de la canasta en el día ancla {ANCLA:%d/%m/%Y}: original ${_va0:,.2f} | reponderada ${_va1:,.2f}')
_rm = NUEVAS['Resumen_mensual'].set_index('mes')['variacion_mensual_apareada_%']
_ap = var_canasta(S_NUEVO)
_ap.index = _ap.index.astype(str)
_dd = (_rm - _ap.reindex(_rm.index)).abs()
print(f'Variación mensual de la canasta reponderada: la del encadenado diario (Resumen_mensual) y la de la estimación '
      f'(suma de grupos) difieren a lo sumo {_dd.max():.4f} pp')
if 'Rubros_diario' in NUEVAS:
    _rv = NUEVAS['Rubros_diario'].set_index('fecha')
    print(f'Rubros: {_rv.shape[1] - 1} con cantidad > 0'
          + (f' (salen {sorted(set(HOJAS["Rubros_diario"].columns[2:]) - set(_rv.columns))})'
             if set(HOJAS['Rubros_diario'].columns[2:]) - set(_rv.columns) else ''))
print(NUEVAS['Resumen_mensual'][['mes', 'variacion_mensual_apareada_%']].assign(
    original=HOJAS['Resumen_mensual']['variacion_mensual_apareada_%'].values,
    ipc=NUEVAS['Resumen_mensual']['mes'].map(lambda m: PI.get(pd.Period(m, 'M')))).tail(13).round(2).to_string(index=False))"""))

# ── CELL 7 — PREDICCIÓN ────────────────────────────────────────────────────────
cells.append(cell_code(r"""# ============================================================
# CELDA 7 — Predicción del IPC del mes en curso (y backtest fuera de muestra de cada modelo)
# ============================================================
MODELOS = ['RW (variación del mes anterior)', 'Canasta (variación directa)', 'RW + b x aceleración de la canasta',
           'MCO canasta + rezago', 'Puente por divisiones', 'Central']
W0 = pd.Series({n: w for _, n, w, _ in DIVISIONES})
_PUENTE = {n: [j for j, g in enumerate(CEL_IPC) if g is not None and str(g).startswith(c + '.')]
           for c, n, _, _ in DIVISIONES if c in PUENTE_DIVISIONES and n in DIV_IPC}
_PUENTE = {n: j for n, j in _PUENTE.items() if j}
HAY_PUENTE = len(DIV_IPC) == 12
DIVV = IPC[DIV_IPC].pct_change() * 100

def _b_acel(y, x, hasta):
    # b de (y_t - y_t-1) = b (x_t - x_t-1), meses completos hasta 'hasta' (sin constante)
    t = pd.DataFrame({'y': y, 'x': x}).reindex([m for m in MESES_IPC if m <= hasta])
    t = t.assign(dy=t['y'].diff(), dx=t['x'].diff())
    t = t[[(m - 1) in t.index for m in t.index]].dropna()
    return float((t['dx'] * t['dy']).sum() / (t['dx'] ** 2).sum()) if len(t) > 2 and (t['dx'] ** 2).sum() > 0 else 0.0

def predecir(m, s, supuestos=None):
    # predicciones de la variación mensual (%) del IPC del mes m con la canasta de participaciones s
    ant = m - 1
    r = var_canasta(s)
    p = {MODELOS[0]: PI[ant], MODELOS[1]: r[m]}
    p[MODELOS[2]] = PI[ant] + _b_acel(PI, r, ant) * (r[m] - r[ant])
    _t = pd.DataFrame({'y': PI, 'x': r, 'l': PI.shift(1)}).reindex(
        [x for x in MESES_IPC if pd.Period(INICIO_REGIMEN, 'M') <= x <= ant]).dropna()
    if len(_t) >= 6:
        _c = np.linalg.lstsq(np.column_stack([np.ones(len(_t)), _t[['x', 'l']].to_numpy()]), _t['y'].to_numpy(), rcond=None)[0]
        p[MODELOS[3]] = _c[0] + _c[1] * r[m] + _c[2] * PI[ant]
    else:
        p[MODELOS[3]] = np.nan
    if HAY_PUENTE:
        _w = W0 * IPC.loc[ant, list(W0.index)]
        _w = _w / _w.sum()
        _d = {}
        for n in W0.index:
            if supuestos and n in supuestos:
                _d[n] = supuestos[n]
            elif n in _PUENTE:
                _rp = var_canasta(s, _PUENTE[n])
                _d[n] = DIVV.loc[ant, n] + _b_acel(DIVV[n], _rp, ant) * (_rp[m] - _rp[ant])
            else:
                _d[n] = DIVV.loc[ant, n]
        p[MODELOS[4]] = float(sum(_w[n] * _d[n] for n in W0.index))
        p['_divisiones'] = _d
        p['_pesos'] = _w
    else:
        p[MODELOS[4]] = np.nan
    p[MODELOS[5]] = np.nanmean([p[MODELOS[2]], p[MODELOS[3]], p[MODELOS[4]]])
    return p

# Supuestos: nombre de la división (se reconoce por el principio del nombre, sin tildes)
SUP = {}
for _k, _v in SUPUESTOS.items():
    _n = [n for n in W0.index if _norm(n).startswith(_norm(_k))]
    if len(_n) != 1:
        raise ValueError(f'SUPUESTOS: "{_k}" no identifica una división del IPC: {list(W0.index)}')
    SUP[_n[0]] = float(str(_v).replace(',', '.'))

# Backtest: cada mes con los pesos estimados solo con los meses anteriores (los de la combinación elegida)
_bt = []
for _m in BT:
    _pr = predecir(_m, PESOS_BT[(VENTANA, LAMBDA, _m)])
    _po = predecir(_m, S0)
    _bt.append({'mes': str(_m), 'ipc_real_%': PI[_m],
                **{f'{k} | reponderada %': _pr[k] for k in MODELOS}, **{f'{k} | original %': _po[k] for k in MODELOS}})
BACKTEST = pd.DataFrame(_bt)

def _errores(sufijo):
    E = BACKTEST[[f'{k} | {sufijo} %' for k in MODELOS]].sub(BACKTEST['ipc_real_%'], axis=0)
    E.columns = MODELOS
    return E

E_REP, E_ORI = _errores('reponderada'), _errores('original')

# Mes a predecir: el siguiente al último IPC, si la canasta tiene días de ese mes
MES_PRED = ULT_IPC + 1
PRED = None
if MES_PRED in MC.index and ULT_IPC in MC.index:
    PRED = predecir(MES_PRED, S_NUEVO, SUP)
    PRED_ORI = predecir(MES_PRED, S0, SUP)
    _base = IPC.loc[ULT_IPC, NG]
    _ia = IPC.loc[MES_PRED - 12, NG] if (MES_PRED - 12) in IPC.index else np.nan
    _ec = E_REP['Central'].dropna()
    LIM = (PRED['Central'] - _ec.quantile(0.9), PRED['Central'] - _ec.quantile(0.1))
    _filas = []
    for k in MODELOS:
        _filas.append({'mes': str(MES_PRED), 'modelo': k, 'var_mm_%': PRED[k], 'nivel_ipc': _base * (1 + PRED[k] / 100),
                       'var_interanual_%': (_base * (1 + PRED[k] / 100) / _ia - 1) * 100,
                       'MAE_backtest_pp': E_REP[k].abs().mean(),
                       f'MAE_ultimos_{MESES_CRITERIO}m_pp': E_REP[k].abs().iloc[-MESES_CRITERIO:].mean(),
                       'sesgo_pp': E_REP[k].mean(), 'var_mm_%_canasta_original': PRED_ORI[k],
                       'MAE_backtest_pp_canasta_original': E_ORI[k].abs().mean()})
    for _nom, _v in (('Central: límite inferior 80%', LIM[0]), ('Central: límite superior 80%', LIM[1])):
        _filas.append({'mes': str(MES_PRED), 'modelo': _nom, 'var_mm_%': _v, 'nivel_ipc': _base * (1 + _v / 100),
                       'var_interanual_%': (_base * (1 + _v / 100) / _ia - 1) * 100})
    PREDICCION = pd.DataFrame(_filas)
    _dias = int((MED.index.to_period('M') == MES_PRED).sum())
    print(f'IPC {ULT_IPC}: {PI[ULT_IPC]:.2f}% (nivel {_base:,.2f}) | canasta {MES_PRED}: {_dias} días con dato'
          + ('' if COMPLETO.get(MES_PRED, False) else ' (mes incompleto: el promedio es de los días que hay)'))
    print(f'\nPREDICCIÓN IPC {MES_PRED} (canasta reponderada; backtest {BT[0]} -> {BT[-1]}):')
    print(PREDICCION[['modelo', 'var_mm_%', 'nivel_ipc', 'var_interanual_%', 'MAE_backtest_pp',
                      f'MAE_ultimos_{MESES_CRITERIO}m_pp', 'var_mm_%_canasta_original',
                      'MAE_backtest_pp_canasta_original']].round(3).to_string(index=False))
    print(f'\n  CENTRAL: {PRED["Central"]:.2f}% m/m (intervalo 80%: {LIM[0]:.2f}% a {LIM[1]:.2f}%), '
          f'nivel {_base * (1 + PRED["Central"] / 100):,.2f}')
    if SUP:
        print(f'  Supuestos: {SUP}')
    if HAY_PUENTE:
        PUENTE_TABLA = pd.DataFrame({'division': list(W0.index), 'peso_efectivo_%': PRED['_pesos'].values * 100,
                                     'var_mm_%': [PRED['_divisiones'][n] for n in W0.index],
                                     'origen': ['supuesto' if n in SUP else 'canasta' if n in _PUENTE else 'mes anterior'
                                                for n in W0.index]})
        print(PUENTE_TABLA.round(2).to_string(index=False))
else:
    PREDICCION = pd.DataFrame({'mes': [str(MES_PRED)], 'modelo': [f'La canasta no tiene días de {MES_PRED}: no hay '
                                                                  'mes para predecir (el IPC ya está publicado)']})
    print(PREDICCION['modelo'].iloc[0])

# Comparación mensual con los pesos finales (dentro de muestra)
_ro, _rn = var_canasta(S0), var_canasta(S_NUEVO)
COMPARACION = pd.DataFrame({'mes': MC.index.astype(str), 'mes_completo': [bool(COMPLETO.get(m, False)) for m in MC.index],
                            'ipc_nivel_general': IPC[NG].reindex(MC.index).values, 'ipc_var_mm_%': PI.reindex(MC.index).values,
                            'canasta_original_var_mm_%': _ro.values, 'canasta_reponderada_var_mm_%': _rn.values})
COMPARACION['dif_original_vs_ipc_pp'] = COMPARACION['canasta_original_var_mm_%'] - COMPARACION['ipc_var_mm_%']
COMPARACION['dif_reponderada_vs_ipc_pp'] = COMPARACION['canasta_reponderada_var_mm_%'] - COMPARACION['ipc_var_mm_%']"""))

# ── CELL 8 — GRÁFICOS ──────────────────────────────────────────────────────────
cells.append(cell_code(r"""# ============================================================
# CELDA 8 — Gráficos de control
# ============================================================
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 5.5), gridspec_kw={'width_ratios': [3, 2]})
_c = COMPARACION[COMPARACION['mes'] >= str(pd.Period(BACKTEST_DESDE, 'M') - 6)]
_x = pd.PeriodIndex(_c['mes'], freq='M').to_timestamp()
ax1.plot(_x, _c['ipc_var_mm_%'], color='black', lw=1.8, marker='o', ms=3, label='IPC Nivel general')
ax1.plot(_x, _c['canasta_original_var_mm_%'], color='#92D050', lw=1.2, label='Canasta original')
ax1.plot(_x, _c['canasta_reponderada_var_mm_%'], color='#375623', lw=1.4, label='Canasta reponderada')
if PRED is not None:
    _xp = MES_PRED.to_timestamp()
    ax1.errorbar([_xp], [PRED['Central']], yerr=[[PRED['Central'] - LIM[0]], [LIM[1] - PRED['Central']]],
                 color='#C00000', marker='D', capsize=4, label=f'Predicción {MES_PRED} (central, 80%)')
ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'{v:.1f}%'))
ax1.set_title('Variación mensual: IPC vs canasta (promedio de los días del mes)')
ax1.legend(fontsize=8)
_y = np.arange(len(GRUPOS))
ax2.barh(_y - 0.2, S0 * 100, height=0.4, color='#92D050', label='Original')
ax2.barh(_y + 0.2, S_NUEVO * 100, height=0.4, color='#375623', label='Reponderada')
ax2.set_yticks(_y)
ax2.set_yticklabels([str(g)[:38] for g in GRUPOS], fontsize=7)
ax2.invert_yaxis()
ax2.set_title(f'Peso de cada {DIM_REPONDERACION} en el día ancla (%)')
ax2.legend(fontsize=8)
plt.tight_layout()
plt.show()"""))

# ── CELL 9 — EXPORTACIÓN ───────────────────────────────────────────────────────
cells.append(cell_code(r"""# ============================================================
# CELDA 9 — Exportación: el Excel del nb08 reponderado + hojas de la reponderación y de la predicción
# ============================================================
_lam_txt = 'sin reponderar (pesos originales)' if LAMBDA is None else f'λ = {LAMBDA}'
_notas_nb08 = HOJAS['Notas'].iloc[:, 0].fillna('').astype(str).tolist()
notas = pd.DataFrame({'nota': [
    f'CANASTA REPONDERADA CONTRA EL IPC (nb10) — {pd.Timestamp.today():%d/%m/%Y}. Entrada: {EXCEL_IN.name} (nb08) e '
    f'{IPC_PATH.name} (IPC del INDEC, {IPC.index.min()} a {ULT_IPC}).',
    f'Reponderación por {DIM_REPONDERACION} ({len(GRUPOS)} grupos): las cantidades de los productos de cada grupo se '
    'multiplican por un mismo factor (factor_reponderacion en Composicion; la cantidad original en cantidad_original). '
    f'Dentro del grupo no cambian las proporciones y el valor de la canasta en el día ancla ({ANCLA:%d/%m/%Y}) es el mismo.',
    'Pesos = participaciones de los grupos en el día ancla (>= 0, suman 100%) que minimizan el error cuadrático medio '
    'entre la variación mensual de la canasta (promedio de los días del mes, sucursales apareadas) y la del IPC Nivel '
    'general, más λ x Σ (peso - peso original)². Solo meses con todos sus días. La estimación usa la suma de las partes '
    'de cada grupo; si hay productos que aparecen tarde o días sin precio, puede diferir un poco de la variación del '
    'encadenado diario (Resumen_mensual): la CELDA 6 imprime la diferencia máxima.',
    f'Elección fuera de muestra (hoja Reponderacion_seleccion): para cada mes de {BT[0]} a {BT[-1]} se estiman los pesos '
    'con los meses anteriores y se mide el error de ese mes, para cada ventana (VENTANAS) y cada λ (LAMBDAS; entre los '
    f'candidatos, no reponderar). Gana el menor error medio de los últimos {MESES_CRITERIO} meses. Elegido: ventana desde '
    f'{VENTANA}, {_lam_txt}. Pesos finales estimados con {MESES_FIN[0]} a {MESES_FIN[-1]}.',
    'Recalculadas con las cantidades nuevas: Serie_diaria, Resumen_mensual, Rubros_* (los rubros que quedan en cero no '
    'salen), Indices_por_grupo (la columna Canasta y los tipos; un grupo es el mismo índice de precios) y Composicion.',
    'NO recalculadas: Provincias_resumen, Provincias_mensual y Provincias_diario son las del nb08 con la canasta ORIGINAL '
    '(el Excel no trae los precios por provincia; su Nivel general no es el de la canasta reponderada). Las columnas con el '
    'promedio de sucursales (valor_canasta_promedio, valor_directo_promedio, valor_promedio_mes_promedio) quedan vacías '
    '(el Excel no trae los precios promedio por producto). Precios_diarios y Precios_apareados no cambian.',
    'Control: el notebook recalculó el Excel con las cantidades originales y dio igual al del nb08 (diferencia relativa '
    f'máxima {max(_ctrl.values()):.1e}).',
    f'Prediccion_IPC: IPC Nivel general de {MES_PRED} (el mes siguiente al último publicado) con la canasta del mes '
    '(promedio de los días con dato; puede estar incompleto). Modelos: RW = la variación del mes anterior; Canasta = la '
    'variación de la canasta reponderada; RW + b x aceleración = la del mes anterior más b veces el cambio de la variación '
    'de la canasta (b por MCO sin constante con todos los meses); MCO canasta + rezago = IPC_t = a + c canasta_t + d '
    f'IPC_t-1 desde {INICIO_REGIMEN}; Puente = las 12 divisiones con las ponderaciones del INDEC actualizadas por precios '
    f'relativos, las divisiones {PUENTE_DIVISIONES} con su parte de la canasta (como RW + b x aceleración) y el resto '
    f'como el mes anterior o con los SUPUESTOS ({SUP if SUP else "ninguno"}). Central = promedio de los tres últimos; '
    'intervalo del 80% = percentiles 10 y 90 de sus errores en el backtest.',
    'Backtest_IPC: la predicción de cada modelo para cada mes, con los pesos estimados solo con los meses anteriores '
    '(reponderada) y con los originales. MAE = error absoluto medio en puntos porcentuales; sesgo = error medio '
    '(positivo: la predicción quedó arriba del IPC).',
    'Comparacion_IPC: variación mensual del IPC y de la canasta con los pesos originales y con los finales (dentro de '
    'muestra: los pesos finales usan esos meses).',
    'La canasta son productos de supermercado (menos de un tercio del IPC): servicios, precios regulados, frescos, ropa y '
    'restaurantes no están. Por eso conviene mirar el error del backtest antes que el ajuste dentro de muestra.',
    '',
    '— Notas del nb08 (canasta ORIGINAL; valen para lo que no cambia) —',
] + _notas_nb08})

_nuevas_hojas = {'Prediccion_IPC': PREDICCION, 'Reponderacion': REPONDERACION,
                 'Reponderacion_seleccion': SELECCION, 'Backtest_IPC': BACKTEST, 'Comparacion_IPC': COMPARACION}
if PRED is not None and HAY_PUENTE:
    _nuevas_hojas['Prediccion_divisiones'] = PUENTE_TABLA
_hojas = [('Prediccion_IPC', PREDICCION), ('Reponderacion', REPONDERACION)]
_hojas += [(h, NUEVAS.get(h, df)) for h, df in HOJAS.items() if h != 'Notas']
_hojas += [(h, df) for h, df in _nuevas_hojas.items() if h not in ('Prediccion_IPC', 'Reponderacion')]
_hojas += [('Notas', notas)]

_dir = OUTPUT_DIR
try:
    _dir.mkdir(parents=True, exist_ok=True)
except OSError:
    _dir = Path('.')
out_xls = _dir / f'{EXCEL_IN.stem}_reponderada_ipc.xlsx'
with pd.ExcelWriter(out_xls, engine='xlsxwriter', datetime_format='dd/mm/yyyy', date_format='dd/mm/yyyy') as _xw:
    _wb = _xw.book
    _f_hdr = _wb.add_format({'bold': True, 'font_color': 'white', 'bg_color': '#375623', 'text_wrap': True,
                             'valign': 'vcenter', 'align': 'center', 'font_size': 10})
    _f_pes = _wb.add_format({'num_format': '#,##0.00'})
    _f_var = _wb.add_format({'num_format': '+0.00"%";-0.00"%"'})
    _f_pp = _wb.add_format({'num_format': '+0.00;-0.00'})
    _f_ind = _wb.add_format({'num_format': '0.00'})
    _f_fac = _wb.add_format({'num_format': '0.0000'})
    _f_nota = _wb.add_format({'text_wrap': True, 'valign': 'top'})
    _fmt_hoja = {'Indices_por_grupo': _f_ind, 'Provincias_diario': _f_ind, 'Rubros_diario': _f_ind,
                 'Provincias_mensual': _f_var, 'Rubros_mensual': _f_var, 'Rubros_incidencia': _f_pp}
    for _sh, _df in _hojas:
        _df.to_excel(_xw, sheet_name=_sh, index=False)
        _ws = _xw.sheets[_sh]
        _ws.set_row(0, 45 if _sh.endswith(('_resumen', '_IPC', '_seleccion')) or _sh == 'Reponderacion' else 30)
        _ws.freeze_panes(1, 1)
        for _j, _c in enumerate(_df.columns):
            _h = str(_c).lower()
            _fmt = (_f_nota if _sh == 'Notas' else
                    (_f_var if _sh == 'Rubros_incidencia' and '(variación %)' in _h else _fmt_hoja[_sh]) if _sh in _fmt_hoja and _j > 0 else
                    _f_pp if _h.endswith('_pp') else
                    _f_fac if 'factor' in _h or _h == 'lambda' else
                    _f_ind if 'indice' in _h or 'cobertura_ponderada' in _h or 'relativo_' in _h or 'peso_' in _h else
                    _f_var if '%' in _h else
                    _f_pes if any(x in _h for x in ('valor', 'precio', 'nivel', '|')) else None)
            _ancho = (160 if _sh == 'Notas' else 34 if _h in ('modelo', 'division') else
                      22 if _j == 0 and (_sh.endswith('_resumen') or _sh == 'Reponderacion') else 12 if _j == 0 else
                      42 if ('desc' in _h or '|' in _h) else 15)
            _ws.set_column(_j, _j, _ancho, _fmt)
            _ws.write(0, _j, _c, _f_hdr)
print(f'Excel: {out_xls}')
print(f'  {len(_hojas)} hojas: {[h for h, _ in _hojas]}')
if EN_COLAB and DESCARGAR:
    from google.colab import files
    files.download(str(out_xls))"""))

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
out_path = os.path.join(script_dir, '10_canasta_reponderada_ipc.ipynb')
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f'Written: {out_path}')
print(f'Cells: {len(cells)}')
