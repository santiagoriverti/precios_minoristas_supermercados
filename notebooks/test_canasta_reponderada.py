"""Test del nb10 (canasta del nb08 reponderada contra el IPC): corre las celdas REALES del notebook sobre un Excel del
nb08 sintético y compara cada número con un cálculo directo (fuerza bruta).

El Excel sintético (01/01/2024 → 20/06/2026, 12 productos en 4 grupos del IPC y 3 tipos) trae a propósito:
  - EANs con ceros adelante (como los escribe el nb08) y dos días calendario sin dato;
  - un producto que aparece el 10/03/2024 y otro con 5 días sin precio (el encadenado tiene que saltearlos);
  - medianas distintas del índice apareado y el último mes incompleto (al 20/06).
El IPC sintético es, por construcción, la variación mensual de la canasta con unas participaciones VERDADERAS distintas de
las originales: con λ = 0 el notebook las tiene que recuperar y elegirlas fuera de muestra.

Corridas: A) IPC hasta may-2026 con un supuesto (predice jun-2026); B) IPC hasta dic-2025 (los pesos del backtest de
ene-2026 de A tienen que ser los finales de B: sin mirar el futuro); C) IPC hasta jun-2026 (no hay mes para predecir);
D) el Excel con un valor tocado (el control tiene que frenar); E) el IPC con fechas 'sept-2024' y comas decimales.

    python notebooks/test_canasta_reponderada.py
"""
import json, os, shutil, sys, tempfile
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')

REPO = Path(__file__).resolve().parents[1]
NB = REPO / 'notebooks' / '10_canasta_reponderada_ipc.ipynb'
rng = np.random.default_rng(7)

# ── Excel del nb08 sintético ────────────────────────────────────────────────────
GRUPOS = {'01.1.1 Pan y cereales': 'Alimentos', '01.1.2 Carnes y derivados': 'Alimentos',
          '02.1.2 Vinos': 'Bebidas alcohólicas', '05.6.1 Bienes para el hogar no durables': 'Limpieza del hogar'}
EANS = ['0000077900661', '7790070012050', '7792180001665', '0000077903518', '7790272001005', '7791866001364',
        '7798181510267', '7790742340108', '7790895000232', '7790070318312', '0000077956262', '7790580000011']
NORM = [e.lstrip('0') for e in EANS]
GRUPO_DE = [list(GRUPOS)[i // 3] for i in range(12)]
Q0 = pd.Series(rng.uniform(0.3, 3.0, 12), index=NORM)
DIAS = pd.date_range('2024-01-01', '2026-06-20').drop([pd.Timestamp('2024-05-01'), pd.Timestamp('2025-03-15')])
MESES = pd.period_range('2024-01', '2026-06', freq='M')
INF = {g: rng.uniform(0.5, 6.0, len(MESES)) for g in GRUPOS}   # inflación mensual de cada grupo (%), distinta
ap = np.zeros((len(DIAS), 12))
for j in range(12):
    _pi = INF[GRUPO_DE[j]][MESES.get_indexer(DIAS.to_period('M'))]
    _d = np.log1p(_pi / 100) / DIAS.days_in_month + rng.normal(0, 0.002, len(DIAS))
    ap[:, j] = rng.uniform(300, 3000) * np.exp(np.cumsum(_d))
P_AP = pd.DataFrame(ap, index=DIAS, columns=NORM)
P_AP.index.name = 'fecha'
P_AP.loc[:'2024-03-09', NORM[4]] = np.nan                                   # aparece el 10/03/2024
P_AP.loc['2025-02-03':'2025-02-07', NORM[8]] = np.nan                       # 5 días sin precio
MED = P_AP * rng.uniform(0.97, 1.03, P_AP.shape)
ANCLA = DIAS[-1]

def encadenar(P, q):
    # índice día a día con productos apareados (fuerza bruta, un día a la vez)
    v, A = [1.0], P.to_numpy()
    q = q.reindex(P.columns).to_numpy()
    links = [np.nan]
    for t in range(1, len(A)):
        m = ~np.isnan(A[t]) & ~np.isnan(A[t - 1])
        l = (q[m] * A[t, m]).sum() / (q[m] * A[t - 1, m]).sum() if m.any() else np.nan
        links.append(l)
        v.append(v[-1] * (1.0 if np.isnan(l) else l))
    return pd.Series(v, index=P.index), pd.Series(links, index=P.index)

def en_pesos(P, q):
    i, l = encadenar(P, q)
    d = (P.fillna(0) * q.reindex(P.columns)).sum(axis=1)
    return i / i[ANCLA] * d[ANCLA], l, d

def serie_bf(q):
    vm, lm, dm = en_pesos(MED, q)
    va, la, _ = en_pesos(P_AP, q)
    return pd.DataFrame({
        'fecha': DIAS, 'valor_canasta': vm.values, 'variacion_diaria_%': (lm.values - 1) * 100,
        'indice_base100': (vm / vm.iloc[0] * 100).values, 'valor_canasta_apareado': va.values,
        'variacion_diaria_apareada_%': (la.values - 1) * 100, 'indice_apareado_base100': (va / va.iloc[0] * 100).values,
        'cobertura_incompleta': np.arange(len(DIAS)) % 97 == 5, 'valor_directo': dm.values,
        'productos_con_dato': MED.notna().sum(axis=1).values, 'productos_total': 12,
        'cobertura_ponderada_%': (MED.notna() * q).sum(axis=1).values / q.sum() * 100,
        'productos_apareados': (MED.notna() & MED.shift().notna()).sum(axis=1).values,
        'pares_sucursal_producto': rng.integers(100, 200, len(DIAS)), 'observaciones': rng.integers(500, 900, len(DIAS)),
        'valor_canasta_promedio': vm.values * 1.01, 'valor_directo_promedio': dm.values * 1.01,
        'valor_completo': (MED.notna().sum(axis=1) == 12).values})

def resumen_bf(s):
    s = s.assign(mes=s['fecha'].dt.to_period('M').astype(str))
    r = s.groupby('mes').agg(dias_con_dato=('fecha', 'size'), dias_cobertura_incompleta=('cobertura_incompleta', 'sum'),
                             valor_promedio_mes=('valor_canasta', 'mean'), valor_primer_dia=('valor_canasta', 'first'),
                             valor_ultimo_dia=('valor_canasta', 'last'), valor_minimo=('valor_canasta', 'min'),
                             valor_maximo=('valor_canasta', 'max'), productos_con_dato_min=('productos_con_dato', 'min'),
                             valor_promedio_mes_apareado=('valor_canasta_apareado', 'mean'),
                             valor_ultimo_dia_apareado=('valor_canasta_apareado', 'last'),
                             valor_promedio_mes_promedio=('valor_canasta_promedio', 'mean')).reset_index()
    r.insert(4, 'variacion_mensual_%', r['valor_promedio_mes'].pct_change() * 100)
    r.insert(7, 'variacion_punta_a_punta_%', r['valor_ultimo_dia'].pct_change() * 100)
    r['variacion_mensual_apareada_%'] = r['valor_promedio_mes_apareado'].pct_change() * 100
    r['variacion_punta_a_punta_apareada_%'] = r['valor_ultimo_dia_apareado'].pct_change() * 100
    return r

TIPOS = sorted(set(GRUPOS.values()))

def rubros_bf(q):
    # valores de cada tipo (en pesos del día ancla) y del nivel general
    V = {'Nivel general': en_pesos(P_AP, q)[0]}
    for t in TIPOS:
        cs = [NORM[j] for j in range(12) if GRUPOS[GRUPO_DE[j]] == t]
        if q[cs].sum() > 0:
            V[t] = en_pesos(P_AP[cs], q[cs])[0]
    return pd.DataFrame(V)

def mensual(V):
    M = V.groupby(V.index.to_period('M')).mean()
    M.index = M.index.astype(str)
    M.index.name = 'mes'
    return M

def rubros_hojas(q):
    R = rubros_bf(q)
    M = mensual(R)
    ru = [c for c in M.columns if c != 'Nivel general']
    inc = M[ru].diff().div(M['Nivel general'].shift(), axis=0) * 100
    inc['Suma de rubros'] = inc[ru].sum(axis=1, min_count=1)
    inc['Nivel general (variación %)'] = M['Nivel general'].pct_change() * 100
    u, p0 = R.iloc[-1], R.iloc[0]
    v12 = (M.iloc[-1] / M.loc['2025-06'] - 1) * 100
    v1 = (M.iloc[-1] / M.iloc[-2] - 1) * 100
    rr = pd.DataFrame({'valor_primer_dia': p0, 'valor_ultimo_dia': u, 'variacion_periodo_%': (u / p0 - 1) * 100,
                       'variacion_12_meses_%': v12, 'variacion_ultimo_mes_%': v1})
    for c in ('variacion_periodo_%', 'variacion_12_meses_%', 'variacion_ultimo_mes_%'):
        rr[f'dif_{c[:-2]}_vs_NG_pp'] = rr[c] - rr.at['Nivel general', c]
    rr = rr.rename_axis('rubro').reset_index()
    n = {t: sum(1 for j in range(12) if GRUPOS[GRUPO_DE[j]] == t and q[NORM[j]] > 0) for t in TIPOS}
    rr.insert(1, 'productos', rr['rubro'].map(n).fillna(int((q > 0).sum())).astype(int))
    rr.insert(2, 'peso_primer_dia_%', rr['valor_primer_dia'] / R['Nivel general'].iloc[0] * 100)
    rr.insert(3, 'peso_ultimo_dia_%', rr['valor_ultimo_dia'] / R['Nivel general'].iloc[-1] * 100)
    rr['incidencia_periodo_pp'] = (rr['valor_ultimo_dia'] - rr['valor_primer_dia']) / R['Nivel general'].iloc[0] * 100
    a12 = M.loc['2025-06']
    rr['incidencia_12_meses_pp'] = rr['rubro'].map((M.iloc[-1] - a12) / a12['Nivel general'] * 100)
    rr.loc[rr['rubro'] == 'Nivel general', ['incidencia_periodo_pp', 'incidencia_12_meses_pp']] = np.nan
    return {'Rubros_resumen': rr, 'Rubros_mensual': (M.pct_change() * 100).reset_index(),
            'Rubros_incidencia': inc.reset_index(), 'Rubros_diario': (R / R.iloc[0] * 100).rename_axis('fecha').reset_index()}

def indices_bf(q):
    ix = pd.DataFrame({'fecha': DIAS, 'Canasta': (lambda v: v / v.iloc[0] * 100)(en_pesos(P_AP, q)[0]).values})
    for dim, mapa in (('tipo', {NORM[j]: GRUPOS[GRUPO_DE[j]] for j in range(12)}),
                      ('grupo', {NORM[j]: GRUPO_DE[j] for j in range(12)})):
        for g in sorted(set(mapa.values())):
            cs = [e for e in NORM if mapa[e] == g]
            i = encadenar(P_AP[cs], q[cs])[0]
            ix[f'{dim} | {g}'[:60]] = (i / i.iloc[0] * 100).values
    return ix

COMP = pd.DataFrame({'id_producto': EANS, 'descripcion': [f'Producto {i}' for i in range(12)],
                     'categoria': ['Cat'] * 12, 'grupo': GRUPO_DE, 'tipo': [GRUPOS[g] for g in GRUPO_DE],
                     'cantidad': Q0.values})
_s = serie_bf(Q0)
_cols = [f'{e} | Producto {i}' for i, e in enumerate(EANS)]
HOJAS = {'Serie_diaria': _s, 'Resumen_mensual': resumen_bf(_s),
         'Provincias_resumen': pd.DataFrame({'provincia': ['Nivel general', 'CABA'], 'valor_ultimo_dia': [1.0, 2.0]}),
         'Provincias_mensual': pd.DataFrame({'mes': ['2024-01', '2024-02'], 'Nivel general': [np.nan, 3.0], 'CABA': [np.nan, 4.0]}),
         'Provincias_diario': pd.DataFrame({'fecha': DIAS[:3], 'Nivel general': [100, 101, 102.5], 'CABA': [100, 99, 98.25]}),
         **rubros_hojas(Q0), 'Composicion': COMP, 'Indices_por_grupo': indices_bf(Q0),
         'Precios_diarios': MED.set_axis(_cols, axis=1).reset_index(),
         'Precios_apareados': P_AP.set_axis(_cols, axis=1).reset_index(),
         'Notas': pd.DataFrame({'nota': ['Nota del nb08 sintética.']})}
ORDEN = ['Serie_diaria', 'Resumen_mensual', 'Provincias_resumen', 'Provincias_mensual', 'Provincias_diario',
         'Rubros_resumen', 'Rubros_mensual', 'Rubros_incidencia', 'Rubros_diario', 'Composicion', 'Indices_por_grupo',
         'Precios_diarios', 'Precios_apareados', 'Notas']

tmp = Path(tempfile.mkdtemp(prefix='test_nb10_'))
def escribir(hojas, nombre):
    ruta = tmp / nombre
    with pd.ExcelWriter(ruta, engine='xlsxwriter', datetime_format='dd/mm/yyyy') as xw:
        for h in ORDEN:
            hojas[h].to_excel(xw, sheet_name=h, index=False)
    return ruta
EXCEL = escribir(HOJAS, 'canasta_diaria_sintetica_20240101_20260620.xlsx')

# ── IPC sintético: la canasta con participaciones VERDADERAS ────────────────────
VG = pd.DataFrame({g: en_pesos(P_AP[[NORM[j] for j in range(12) if GRUPO_DE[j] == g]],
                               Q0[[NORM[j] for j in range(12) if GRUPO_DE[j] == g]])[0] for g in GRUPOS})
S0_BF = (VG.loc[ANCLA] / VG.loc[ANCLA].sum()).to_numpy()
S_VERD = np.array([0.15, 0.45, 0.10, 0.30])
B = mensual(VG) @ (S_VERD / S0_BF)
NIVEL = 100 * B / B.iloc[0]
DIVS = ['Alimentos y bebidas no alcohólicas', 'Bebidas Alcohólicas y tabaco', 'Prendas de vestir y calzado',
        'Vivienda, agua, electricidad, gas y otros combustibles', 'Equipo y mantenimiento del hogar', 'Salud',
        'Transporte', 'Comunicación', 'Recreación y cultura', 'Educación', 'Restaurantes y hoteles',
        'Bienes y servicios varios']

def ipc_excel(hasta, nombre, espanol=False):
    d = pd.DataFrame({'date': pd.PeriodIndex(NIVEL.index, freq='M').to_timestamp(), 'Nivel general': NIVEL.values})
    for c in DIVS:
        d[c] = NIVEL.values
    d = d[d['date'] <= pd.Timestamp(hasta)]
    if espanol:
        _m = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sept', 'oct', 'nov', 'dic']
        d['date'] = [f'{_m[x.month - 1]}-{x.year}' for x in d['date']]
        for c in d.columns[1:]:
            d[c] = [f'{v:.10f}'.replace('.', ',') for v in d[c]]
    carpeta = tmp / nombre
    carpeta.mkdir()
    d.to_excel(carpeta / 'IPC.xlsx', index=False, sheet_name='IPC')
    return carpeta

# ── Correr las celdas reales ────────────────────────────────────────────────────
cells = [''.join(c['source']) for c in json.load(open(NB, encoding='utf-8'))['cells'] if c['cell_type'] == 'code']
os.chdir(REPO)

def correr(excel, ipc_dir, salida, **extra):
    g = {}
    exec(cells[0], g)
    g.update({'CANASTA_EXCEL': str(excel), 'SEPA_DIR': str(ipc_dir), 'OUTPUT_DIR': str(tmp / salida),
              'VENTANAS': ['2024-02'], 'LAMBDAS': [None, 0], 'BACKTEST_DESDE': '2025-09', 'MESES_CRITERIO': 6,
              'INICIO_REGIMEN': '2024-06', **extra})
    for c in cells[1:]:
        exec(c, g)
    return g

errores = []
def chk(nombre, ok):
    print(f'  {"OK " if ok else "MAL"} {nombre}')
    if not ok:
        errores.append(nombre)

def iguales(a, b, tol=1e-9):
    a, b = np.asarray(a, float), np.asarray(b, float)
    return a.shape == b.shape and bool(np.all((np.isnan(a) & np.isnan(b)) |
                                              (np.abs(a - b) <= tol * np.maximum(np.abs(b), 1.0))))

print('\n=== A) IPC hasta may-2026, supuesto de Transporte ===')
gA = correr(EXCEL, ipc_excel('2026-05-01', 'ipcA'), 'outA', SUPUESTOS={'transporte': 5})
OUT = pd.read_excel(gA['out_xls'], sheet_name=None, dtype={'id_producto': str})
chk('elige reponderar con λ = 0', gA['LAMBDA'] == 0 and gA['VENTANA'] == '2024-02')
chk('recupera las participaciones verdaderas', np.allclose(gA['S_NUEVO'], S_VERD, atol=1e-3))
chk('participaciones originales = fuerza bruta', np.allclose(gA['S0'], S0_BF, atol=1e-12))
q1 = pd.Series(gA['S_NUEVO'] / S0_BF, index=list(GRUPOS)).reindex(GRUPO_DE).to_numpy() * Q0
c = OUT['Composicion']
chk('Composicion: ids, cantidad_original y cantidad nueva = original x factor',
    list(c['id_producto']) == EANS and iguales(c['cantidad_original'], Q0.values)
    and iguales(c['cantidad'], q1.values, 1e-12) and iguales(c['factor_reponderacion'] * c['cantidad_original'], c['cantidad']))
s1 = serie_bf(q1)
sn = OUT['Serie_diaria']
chk('Serie_diaria reponderada = fuerza bruta (medianas, apareado, directo, cobertura)',
    all(iguales(sn[k], s1[k]) for k in ('valor_canasta', 'variacion_diaria_%', 'indice_base100', 'valor_canasta_apareado',
                                        'variacion_diaria_apareada_%', 'indice_apareado_base100', 'valor_directo',
                                        'cobertura_ponderada_%')))
chk('Serie_diaria: lo que no depende de las cantidades no cambia; promedios vacíos',
    all(iguales(sn[k], _s[k]) for k in ('productos_con_dato', 'pares_sucursal_producto', 'observaciones'))
    and sn['valor_canasta_promedio'].isna().all() and sn['valor_directo_promedio'].isna().all())
chk('valor de la canasta en el día ancla = el original',
    abs(sn['valor_canasta_apareado'].iloc[-1] / _s['valor_canasta_apareado'].iloc[-1] - 1) < 1e-12)
r1 = resumen_bf(s1.assign(valor_canasta_promedio=np.nan))
chk('Resumen_mensual reponderado = fuerza bruta', iguales(OUT['Resumen_mensual'].select_dtypes('number'),
                                                         r1.select_dtypes('number')))
rb = rubros_hojas(q1)
chk('Rubros_* reponderados = fuerza bruta', all(iguales(OUT[k].select_dtypes('number'), rb[k].select_dtypes('number'))
                                                for k in rb))
chk('Indices_por_grupo reponderado = fuerza bruta', iguales(OUT['Indices_por_grupo'].select_dtypes('number'),
                                                            indices_bf(q1).select_dtypes('number')))
chk('Provincias_* y Precios_* no cambian', all(iguales(OUT[k].select_dtypes('number'), HOJAS[k].select_dtypes('number'))
                                               for k in ('Provincias_resumen', 'Provincias_mensual', 'Provincias_diario',
                                                         'Precios_diarios', 'Precios_apareados')))
chk('hojas: las del nb08 en su orden, más las nuevas, Notas al final',
    list(OUT) == ['Prediccion_IPC', 'Reponderacion'] + ORDEN[:-1] + ['Reponderacion_seleccion', 'Backtest_IPC',
                                                                      'Comparacion_IPC', 'Prediccion_divisiones', 'Notas'])
_ipc_mm = NIVEL.pct_change() * 100
_rm = OUT['Resumen_mensual'].set_index('mes')['variacion_mensual_apareada_%']
# hasta abr-2024 el producto que aparece el 10/03 se imputa distinto en el encadenado de la canasta (con toda la canasta)
# y en la suma de grupos que usa la estimación (con su grupo): ahí la diferencia llega a ~0,15 pp
_comp = [m for m in _ipc_mm.index[1:] if '2024-05' <= m <= '2026-05']
print('    dif. máx. canasta reponderada vs IPC por mes (pp):', (_rm[_comp] - _ipc_mm[_comp]).abs().sort_values().tail(3).round(4).to_dict())
chk('la canasta reponderada sigue al IPC mes a mes desde may-2024 (< 0,05 pp; el IPC sale de la suma de grupos)',
    float((_rm[_comp] - _ipc_mm[_comp]).abs().max()) < 0.05)
p = OUT['Prediccion_IPC'].set_index('modelo')
_jun = _rm['2026-06']
chk('predice jun-2026 con la variación de la canasta del mes (incompleto)',
    gA['MES_PRED'] == pd.Period('2026-06', 'M') and abs(p.at['Canasta (variación directa)', 'var_mm_%'] - _jun) < 1e-6)
chk('RW = variación del IPC de may-2026', abs(p.at['RW (variación del mes anterior)', 'var_mm_%'] - _ipc_mm['2026-05']) < 1e-9)
chk('nivel = IPC de mayo x (1 + variación)', abs(p.at['Central', 'nivel_ipc'] - NIVEL['2026-05'] * (1 + p.at['Central', 'var_mm_%'] / 100)) < 1e-6)
_cen = np.nanmean([p.at[k, 'var_mm_%'] for k in ('RW + b x aceleración de la canasta', 'MCO canasta + rezago',
                                                  'Puente por divisiones')])
chk('Central = promedio de los tres modelos', abs(p.at['Central', 'var_mm_%'] - _cen) < 1e-9)
chk('intervalo del 80% alrededor de la central', p.at['Central: límite inferior 80%', 'var_mm_%'] <= p.at['Central', 'var_mm_%']
    <= p.at['Central: límite superior 80%', 'var_mm_%'])
d = OUT['Prediccion_divisiones'].set_index('division')
chk('supuesto de Transporte aplicado en el puente', d.at['Transporte', 'var_mm_%'] == 5 and d.at['Transporte', 'origen'] == 'supuesto'
    and d.at['Alimentos y bebidas no alcohólicas', 'origen'] == 'canasta' and abs(d['peso_efectivo_%'].sum() - 100) < 1e-9)
_w = pd.Series(dict(zip(gA['W0'].index, gA['W0'].values)))
_pu = (d['peso_efectivo_%'] / 100 * d['var_mm_%']).sum()
chk('puente = suma de divisiones x pesos efectivos', abs(p.at['Puente por divisiones', 'var_mm_%'] - _pu) < 1e-9)
bt = OUT['Backtest_IPC']
chk('backtest: un mes por fila de sep-2025 a may-2026 con el IPC real',
    list(bt['mes']) == [str(m) for m in pd.period_range('2025-09', '2026-05', freq='M')]
    and iguales(bt['ipc_real_%'], _ipc_mm[list(bt['mes'])].values))
chk('backtest: con λ = 0 la canasta reponderada acierta el IPC (< 0,05 pp)',
    float((bt['Canasta (variación directa) | reponderada %'] - bt['ipc_real_%']).abs().max()) < 0.05)
chk('Notas: las del nb10 y después las del nb08', OUT['Notas']['nota'].iloc[0].startswith('CANASTA REPONDERADA')
    and OUT['Notas']['nota'].iloc[-1] == 'Nota del nb08 sintética.')

print('\n=== B) IPC hasta dic-2025: el backtest de ene-2026 no mira el futuro ===')
gB = correr(EXCEL, ipc_excel('2025-12-01', 'ipcB'), 'outB', BACKTEST_DESDE='2025-07', MESES_CRITERIO=3)
chk('pesos del backtest de ene-2026 (A) = pesos finales con el IPC hasta dic-2025 (B)',
    gB['LAMBDA'] == 0 and np.allclose(gA['PESOS_BT'][('2024-02', 0, pd.Period('2026-01', 'M'))], gB['S_NUEVO'], atol=1e-9))
chk('B predice ene-2026', gB['MES_PRED'] == pd.Period('2026-01', 'M') and gB['PRED'] is not None)

print('\n=== C) IPC hasta jun-2026: no hay mes para predecir ===')
gC = correr(EXCEL, ipc_excel('2026-06-01', 'ipcC'), 'outC')
chk('sin predicción y con Excel', gC['PRED'] is None and Path(gC['out_xls']).exists())
chk('jun-2026 (incompleto) no entra en la estimación', pd.Period('2026-06', 'M') not in gC['MESES_IPC'])

print('\n=== D) Excel tocado: el control frena ===')
_h = {k: v.copy() for k, v in HOJAS.items()}
_h['Serie_diaria'].loc[100, 'valor_canasta_apareado'] *= 1.001
try:
    correr(escribir(_h, 'canasta_diaria_tocada.xlsx'), tmp / 'ipcA', 'outD')
    chk('el control frena con un valor tocado', False)
except ValueError as e:
    chk('el control frena con un valor tocado', 'Serie_diaria' in str(e))

print('\n=== E) IPC con fechas en castellano y comas decimales ===')
gE = correr(EXCEL, ipc_excel('2026-05-01', 'ipcE', espanol=True), 'outE')
chk('mismo IPC y mismos pesos que A', gE['IPC'].index.equals(gA['IPC'].index) and np.allclose(gE['IPC'], gA['IPC'])
    and np.allclose(gE['S_NUEVO'], gA['S_NUEVO'], atol=1e-9))

shutil.rmtree(tmp, ignore_errors=True)
print(f'\n{"TODO OK" if not errores else f"{len(errores)} ERRORES: {errores}"}')
sys.exit(1 if errores else 0)
