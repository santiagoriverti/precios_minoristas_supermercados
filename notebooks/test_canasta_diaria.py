"""Test del nb08 (valor diario de una canasta): corre las celdas REALES del notebook sobre un SEPA sintético y compara
cada número con un cálculo directo (fuerza bruta).

El SEPA sintético (ene-mar 2026, 10 sucursales de 3 comercios, 4 productos de la canasta y 2 que no) trae a propósito:
  - dos archivos para la misma parte de un mes (el completo y uno parcial, días 1-5, ÚLTIMO en el zip);
  - filas sucursal x producto repetidas (idénticas, y una partida en dos filas con días distintos);
  - marzo en centavos;
  - un hueco de cobertura: las 4 sucursales del comercio 15 (las baratas) no informan del 12 al 18/02;
  - una sucursal que falta 40 días (más que MAX_DIAS_SIN_PRECIO) y faltantes sueltos al azar;
  - un precio x10 un día en una sucursal (relativo fuera de [1/4, 4]);
  - tres provincias (comercio 9 en AR-C, 12 en 'Buenos Aires' escrita con el nombre, 15 en AR-S), una sucursal sin
    provincia, y un producto que el comercio 15 (Santa Fe) no vende: esa provincia lo imputa con el país.
Todas las sucursales siguen la misma tendencia de cada producto (con un nivel propio): el índice apareado tiene que dar
EXACTAMENTE esa tendencia, aunque la mediana salte en el hueco; y en cada provincia, la canasta tiene que valer
Σ cantidad x (mediana de la provincia del último día / tendencia de ese día) x tendencia de hoy.

    python notebooks/test_canasta_diaria.py
"""
import gzip, io, json, os, shutil, sys, tempfile, zipfile
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')

REPO = Path(__file__).resolve().parents[1]
NB = REPO / 'notebooks' / '08_canasta_diaria.ipynb'
rng = np.random.default_rng(11)

# ── SEPA sintético ──────────────────────────────────────────────────────────────
SUCS = ([('9', '1', str(100 + i)) for i in range(3)] + [('12', '1', str(200 + i)) for i in range(3)]
        + [('15', '1', str(300 + i)) for i in range(4)])
NIVEL_COM = {'9': 1.0, '12': 1.25, '15': 0.8}
CANASTA = {'7790895000232': 2.0, '7791866001364': 1.0, '7798181510267': 0.5, '7790742340108': 3.0}
OTROS = ['7790070318312', '123']
BASE = {'7790895000232': 1200.0, '7791866001364': 800.0, '7798181510267': 2500.0, '7790742340108': 300.0,
        '7790070318312': 900.0, '123': 50.0}
G = {'7790895000232': 0.002, '7791866001364': 0.004, '7798181510267': -0.001, '7790742340108': 0.0,
     '7790070318312': 0.001, '123': 0.0}
DIAS = pd.date_range('2026-01-01', '2026-03-31')
F_FIN = pd.Timestamp('2026-03-20')
HUECO = (pd.Timestamp('2026-02-12'), pd.Timestamp('2026-02-18'))
AUSENTE = ('9', '1', '100'), (pd.Timestamp('2026-01-10'), pd.Timestamp('2026-02-18'))
OUTLIER = ('12', '1', '201'), '7790895000232', pd.Timestamp('2026-01-20')
PROV_COM = {'9': 'AR-C', '12': 'Buenos Aires', '15': 'AR-S'}
SIN_PROV = ('9', '1', '102')                          # sucursal con la provincia vacía
NO_VENDE = ('15', '7790742340108')                    # Santa Fe no tiene este producto
ISO = {'AR-C': 'AR-C', 'Buenos Aires': 'AR-B', 'AR-S': 'AR-S'}

def prov_suc(c, b, s):
    return '' if (c, b, s) == SIN_PROV else ISO[PROV_COM[c]]

def tendencia(e, d):
    v = np.exp(G[e] * (d - DIAS[0]).days)
    return v * 1.10 if (e == '7791866001364' and d >= pd.Timestamp('2026-02-10')) else v

nivel_suc = {s: NIVEL_COM[s[0]] * rng.uniform(0.95, 1.05) for s in SUCS}
filas = []
for s in SUCS:
    for e in list(CANASTA) + OTROS:
        for d in DIAS:
            if s[0] == '15' and HUECO[0] <= d <= HUECO[1]:
                continue
            if s == AUSENTE[0] and AUSENTE[1][0] <= d <= AUSENTE[1][1]:
                continue
            if (s[0], e) == NO_VENDE:
                continue
            if rng.random() < 0.05:
                continue
            p = BASE[e] * nivel_suc[s] * tendencia(e, d)
            if (s, e, d) == OUTLIER:
                p *= 10
            filas.append((*s, e, d, p))
obs = pd.DataFrame(filas, columns=['c', 'b', 's', 'e', 'd', 'precio'])

def tabla(mes, dd, centavos=False):
    o = obs[obs['d'].isin(dd)]
    w = o.pivot_table(index=['c', 'b', 's', 'e'], columns='d', values='precio', aggfunc='first')
    idx = obs[obs['d'].dt.month == mes].groupby(['c', 'b', 's', 'e']).size().index
    w = w.reindex(idx).reindex(columns=dd) * (100 if centavos else 1)
    w.columns = [f'precio_{d:%Y%m%d}' for d in dd]
    w = w.reset_index().rename(columns={'c': 'id_comercio', 'b': 'id_bandera', 's': 'id_sucursal', 'e': 'id_producto'})
    w.insert(3, 'sucursales_provincia', [('' if (c, b, s) == SIN_PROV else PROV_COM[c])
                                         for c, b, s in zip(w['id_comercio'], w['id_bandera'], w['id_sucursal'])])
    return w

def con_repetidas(w):
    # 2 filas repetidas idénticas al final y una fila partida en dos con días distintos
    w = w.copy()
    pc = [c for c in w.columns if c.startswith('precio_')]
    llenas = w.index[(w[pc].notna().sum(axis=1) >= 6) & w['id_producto'].isin(list(CANASTA))]
    rep = w.loc[llenas[:2]]
    i = llenas[4]
    dias_i = [c for c in pc if pd.notna(w.at[i, c])]
    a, b = w.loc[[i]].copy(), w.loc[[i]].copy()
    a[dias_i[len(dias_i) // 2:]] = np.nan
    b[dias_i[:len(dias_i) // 2]] = np.nan
    return pd.concat([w.drop(index=i), a, rep, b], ignore_index=True)

def gz(w):
    buf = io.StringIO(); w.to_csv(buf, index=False, na_rep='NA', float_format='%.10f')
    return gzip.compress(buf.getvalue().encode())

tmp = Path(tempfile.mkdtemp(prefix='test_nb08_'))
sepa = tmp / 'carga'; sepa.mkdir()
out = tmp / 'output_canasta'; out.mkdir()
usados = []                                        # tablas de los archivos que el notebook tiene que usar
with zipfile.ZipFile(sepa / '2026A.zip', 'w') as zf:
    for mes in (1, 2, 3):
        dm = [d for d in DIAS if d.month == mes]
        for parte, dd in ((1, [d for d in dm if d.day <= 15]), (2, [d for d in dm if d.day > 15])):
            w = tabla(mes, dd, centavos=(mes == 3))
            if (mes, parte) == (2, 1):
                w = con_repetidas(w)
            zf.writestr(f'{mes:02d}2026_pais_parte{parte}COMPLETO{"b" if (mes, parte) == (1, 1) else ""}.csv.gz', gz(w))
            usados.append((mes, w))
            if (mes, parte) == (1, 1):     # parcial (días 1-5) de la misma parte, último en el zip: no se usa ni se suma
                zf.writestr('012026_pais_parte1COMPLETO.csv.gz', gz(tabla(1, [d for d in dd if d.day <= 5])))

sel = pd.DataFrame({'periodo': '2026-03', 'id_producto': list(CANASTA) + OTROS,
                    'descripcion': [f'Producto {e}' for e in list(CANASTA) + OTROS],
                    'categoria': ['Bebidas', 'Almacén', 'Almacén', 'Limpieza', 'Almacén', 'Otros'],
                    'cantidad_01': list(CANASTA.values()) + [None, None],
                    'pt_grupo_ipc': ['01.2.2 Aguas', '01.1.1 Pan', '01.1.1 Pan', '05.6.1 Limpieza', None, None],
                    'pt_tipo': ['Bebidas sin alcohol', 'Alimentos', 'Alimentos', 'Limpieza del hogar', None, None]})
with pd.ExcelWriter(out / 'canasta_pass_through_2026-03.xlsx') as xw:
    sel.to_excel(xw, sheet_name='Selección', index=False)

# ── Correr las celdas reales ────────────────────────────────────────────────────
cells = [''.join(c['source']) for c in json.load(open(NB, encoding='utf-8'))['cells'] if c['cell_type'] == 'code']
os.chdir(REPO)

def correr(**extra):
    g = {}
    exec(cells[0], g)
    g.update(SEPA_DIR=str(sepa), OUTPUT_DIR=str(out), CANASTA_EXCEL=str(out / 'canasta_pass_through_2026-03.xlsx'),
             FECHA_INICIO='2026-01-01', FECHA_FIN='2026-03-20', **extra)
    for c in cells[1:]:
        exec(c, g)
    return g

g = correr()
errores = []

def chk(nombre, ok):
    if not ok:
        errores.append(nombre)

# ── Fuerza bruta ────────────────────────────────────────────────────────────────
largo = []
for mes, w in usados:
    pc = [c for c in w.columns if c.startswith('precio_')]
    m = w.melt(id_vars=['id_comercio', 'id_bandera', 'id_sucursal', 'id_producto'], value_vars=pc, var_name='c',
               value_name='precio').dropna(subset=['precio'])
    m['fecha'] = pd.to_datetime(m['c'].str[-8:])
    m['mes'] = mes
    largo.append(m)
L = pd.concat(largo, ignore_index=True)
L = L[L['id_producto'].isin(list(CANASTA)) & (L['fecha'] <= F_FIN)]
fac = L.groupby('mes')['precio'].transform(lambda x: 100.0 if x.median() > 10_000 else 1.0)
L['p'] = L['precio'] / fac
L['suc'] = L['id_comercio'] + '|' + L['id_bandera'] + '|' + L['id_sucursal']

esp = L.groupby(['fecha', 'id_producto'])['p'].agg(['median', 'size'])
L = L.merge(esp['median'].rename('med'), left_on=['fecha', 'id_producto'], right_index=True)
esp['prom'] = L[(L['p'] >= L['med'] / 4) & (L['p'] <= L['med'] * 4)].groupby(['fecha', 'id_producto'])['p'].mean()
pdia = g['precios_dia'].set_index(['fecha', 'ean_norm']).sort_index()
chk('mismas (fecha, producto) que la fuerza bruta', pdia.index.equals(esp.index.rename(['fecha', 'ean_norm'])))
chk('medianas', np.allclose(pdia['precio_mediano'], esp['median'].values, rtol=1e-12))
chk('observaciones (el archivo parcial de enero no se suma)', (pdia['n_obs'].values == esp['size'].values).all())
chk('promedios sin valores a más de 4 veces', np.allclose(pdia['precio_promedio'], esp['prom'].values, rtol=1e-12))

# Relativos apareados: precio de hoy / precio anterior de la sucursal movido con el índice del producto (fuerza bruta,
# producto por producto y día por día)
U = L.groupby(['suc', 'id_producto', 'fecha'])['p'].mean().reset_index()      # filas repetidas: el promedio
slr_esp, npar_esp = {}, {}
for e, ue in U.groupby('id_producto'):
    I, ultimo = 1.0, {}                                                          # suc -> (precio, día, índice)
    for f, uf in ue.groupby('fecha'):
        logs = []
        for s, p in zip(uf['suc'], uf['p']):
            if s in ultimo and (f - ultimo[s][1]).days <= 31:
                r = p / ultimo[s][0] * ultimo[s][2] / I
                if 0.25 <= r <= 4:
                    logs.append(np.log(r))
        if logs:
            I *= np.exp(np.mean(logs))
        for s, p in zip(uf['suc'], uf['p']):
            ultimo[s] = (p, f, I)
        slr_esp[(f, e)], npar_esp[(f, e)] = sum(logs), len(logs)
chk('relativos apareados (suma de logaritmos)', np.allclose(pdia['suma_log_rel'], [slr_esp[k] for k in pdia.index], atol=1e-12))
chk('pares por producto y día', (pdia['n_pares'].values == np.array([npar_esp[k] for k in pdia.index])).all())

# El índice apareado de cada producto = su tendencia (las sucursales difieren solo en el nivel)
IDX = g['IDX']
for e in CANASTA:
    t = np.array([tendencia(e, d) for d in IDX.index])
    chk(f'índice apareado de {e} = tendencia', np.allclose(IDX[e].values / IDX[e].iloc[0], t / t[0], rtol=1e-9))

# Provincias: los mismos relativos con el índice de cada provincia; sin pares en la provincia, el eslabón nacional
U['prov'] = [prov_suc(*s.split('|')) for s in U['suc']]
L['prov'] = [prov_suc(c, b, s) for c, b, s in zip(L['id_comercio'], L['id_bandera'], L['id_sucursal'])]
FECHAS = sorted(pd.to_datetime(U['fecha'].unique()))
slrp_esp, nparp_esp = {}, {}
for (e, pv), ue in U[U['prov'] != ''].groupby(['id_producto', 'prov']):
    I, ultimo, por_dia = 1.0, {}, dict(list(ue.groupby('fecha')))
    for f in FECHAS:
        uf = por_dia.get(f, ue.iloc[:0])
        logs = [np.log(p / ultimo[s][0] * ultimo[s][2] / I) for s, p in zip(uf['suc'], uf['p'])
                if s in ultimo and (f - ultimo[s][1]).days <= 31]
        logs = [x for x in logs if np.log(0.25) <= x <= np.log(4)]
        n_nac = npar_esp.get((f, e), 0)
        I *= np.exp(np.mean(logs)) if logs else (np.exp(slr_esp[(f, e)] / n_nac) if n_nac else 1.0)
        for s, p in zip(uf['suc'], uf['p']):
            ultimo[s] = (p, f, I)
        if logs:
            slrp_esp[(f, e, pv)], nparp_esp[(f, e, pv)] = sum(logs), len(logs)
_PL = list(g['PROV_LIST'])
_EL = list(g['EAN_LIST'])
_t = g['_CAL'].get_indexer(pd.DatetimeIndex([k[0] for k in slrp_esp]))
_ie = [_EL.index(k[1]) for k in slrp_esp]
_ip = [_PL.index(k[2]) for k in slrp_esp]
chk('relativos por provincia (suma de logaritmos)', np.allclose(g['SLR_P'][_t, _ie, _ip], list(slrp_esp.values()), atol=1e-12)
    and np.isclose(np.abs(g['SLR_P']).sum(), sum(abs(x) for x in slrp_esp.values()), atol=1e-10))
chk('pares por producto, provincia y día', (g['NPAR_P'][_t, _ie, _ip] == list(nparp_esp.values())).all()
    and g['NPAR_P'].sum() == sum(nparp_esp.values()))
chk('la sucursal sin provincia cuenta para el nivel general y no para las provincias',
    int(g['precios_dia']['n_obs'].sum()) - int(g['OBS_P'].sum()) == int((L['prov'] == '').sum()) > 0)

# Valor de la canasta en cada provincia = Σ q x nivel de la provincia x tendencia (todas las sucursales siguen la
# tendencia); el nivel = mediana de la provincia del último día con dato / tendencia de ese día (si nunca lo tuvo, el país)
PV = g['prov_val']
_nac_ult = L.groupby('id_producto').apply(lambda x: x.loc[x['fecha'] == x['fecha'].max(), 'p'].median() / tendencia(x.name, x['fecha'].max()))
for pv, nom in (('AR-C', 'CABA'), ('AR-B', 'Buenos Aires'), ('AR-S', 'Santa Fe')):
    Lp = L[L['prov'] == pv]
    niv = {}
    for e in CANASTA:
        x = Lp[Lp['id_producto'] == e]
        niv[e] = (x.loc[x['fecha'] == x['fecha'].max(), 'p'].median() / tendencia(e, x['fecha'].max()) if len(x)
                  else _nac_ult[e])
    esp_v = pd.Series([sum(q * niv[e] * tendencia(e, d) for e, q in CANASTA.items()) for d in PV.index], index=PV.index)
    chk(f'valor de la canasta en {nom} = Σ q x nivel x tendencia', np.allclose(PV[nom], esp_v, rtol=1e-9))
imp_s = pd.DataFrame(g['imp_prov'])
_q_nv = CANASTA[NO_VENDE[1]] * _nac_ult[NO_VENDE[1]] * np.array([tendencia(NO_VENDE[1], d) for d in PV.index])
chk('Santa Fe imputa el producto que no vende todos los días', (imp_s['Santa Fe'].values >= _q_nv / PV['Santa Fe'].values * 100 - 1e-9).all())
chk('Santa Fe imputa todo en el hueco', np.allclose(imp_s.loc[pd.date_range(*HUECO), 'Santa Fe'], 100))
chk('provincias del resumen', g['prov_resumen']['provincia'].tolist() == ['Nivel general', 'Buenos Aires', 'CABA', 'Santa Fe']
    and g['prov_resumen'].set_index('provincia').at['Nivel general', 'relativo_nivel_general_%'] == 100)

# Rubros: suman el nivel general (canasta completa todos los días) y las incidencias, su variación
RV = g['rub_val']
chk('rubros = tipo y suman el nivel general', g['DIM_RUBRO'] == 'tipo' and
    np.allclose(RV.drop(columns='Nivel general').sum(axis=1), RV['Nivel general'], rtol=1e-12))
ri = g['rub_incidencia'].iloc[1:]
chk('incidencias de los rubros = variación del nivel general', np.allclose(ri['Suma de rubros'], ri['Nivel general (variación %)'], atol=1e-9)
    and np.allclose(ri['Nivel general (variación %)'], g['resumen']['variacion_mensual_apareada_%'].iloc[1:], atol=1e-9))
rr = g['rub_resumen'].set_index('rubro')
chk('pesos e incidencias del período de los rubros', np.isclose(rr['peso_ultimo_dia_%'].drop('Nivel general').sum(), 100)
    and np.isclose(rr['incidencia_periodo_pp'].sum(), rr.at['Nivel general', 'variacion_periodo_%']))

S = g['serie'].set_index('fecha')
d0, d1 = HUECO[0] - pd.Timedelta(days=1), HUECO[0]
_tend = sum(q * BASE[e] * tendencia(e, d1) for e, q in CANASTA.items()) / sum(q * BASE[e] * tendencia(e, d0) for e, q in CANASTA.items())
chk('en el hueco la mediana salta y el apareado no', abs(S.at[d1, 'variacion_diaria_%']) > 3 and
    abs(S.at[d1, 'variacion_diaria_apareada_%'] - (_tend - 1) * 100) < 0.2)
inc = set(S.index[S['cobertura_incompleta']])
chk(f'cobertura incompleta = los días del hueco (marcó {sorted(d.strftime("%d/%m") for d in inc)})',
    inc == set(pd.date_range(*HUECO)))
an = g['ANCLA']
chk('valor apareado = valor de medianas en el día ancla', abs(S.at[an, 'valor_canasta_apareado'] - S.at[an, 'valor_canasta']) < 1e-6)
chk('período cortado en FECHA_FIN', S.index.max() == F_FIN and S.index.min() == DIAS[0])
chk('nombre automático Pass-through', g['NOMBRE_CANASTA'] == 'Pass-through' and g['SHORT_CANASTA'] == 'pass_through')
chk('enero usa el archivo completo de la parte 1', any('COMPLETOb' in n for _z, n in g['_mapa_mes']['2026-01']) and
    len(g['_mapa_mes']['2026-01']) == 2)
x = pd.ExcelFile(out / 'canasta_diaria_pass_through_20260101_20260320.xlsx')
chk(f'hojas del Excel {x.sheet_names}', x.sheet_names == [
    'Serie_diaria', 'Resumen_mensual', 'Provincias_resumen', 'Provincias_mensual', 'Provincias_diario', 'Rubros_resumen',
    'Rubros_mensual', 'Rubros_incidencia', 'Rubros_diario', 'Composicion', 'Indices_por_grupo', 'Precios_diarios',
    'Precios_apareados', 'Notas'])
pm = pd.read_excel(x, 'Provincias_mensual')
chk('Provincias_mensual: nivel general = variación mensual apareada', pm.columns.tolist()[:2] == ['mes', 'Nivel general']
    and np.allclose(pm['Nivel general'].iloc[1:], g['resumen']['variacion_mensual_apareada_%'].iloc[1:]))
sd = pd.read_parquet(out / 'series_desagregadas_pass_through_20260101_20260320.parquet')
chk('series desagregadas: nivel general, 3 provincias y 3 rubros por día',
    len(sd) == len(S) * 7 and sd.groupby('desagregacion')['nombre'].nunique().to_dict() == {'Nivel general': 1, 'provincia': 3, 'rubro': 3})
ig = pd.read_excel(x, 'Indices_por_grupo')
chk('índices por tipo y grupo', {'tipo | Alimentos', 'grupo | 01.1.1 Pan'} <= set(ig.columns))
pan = pd.read_parquet(out / 'panel_diario_pass_through_20260101_20260320.parquet')
chk('panel: una fila por producto y día con dato', len(pan) == len(pdia) and pan['precio_apareado'].notna().all())

# ── Caché: misma salida desde el caché, con un mes borrado y con un estado borrado (se relee el mes anterior) ──
base = g['serie'].copy(); base_p = g['precios_dia'].copy(); base_pv = g['prov_val'].copy(); base_rv = g['rub_val'].copy()

def igual(nombre, g2, leidos):
    ok = (g2['serie'].equals(base) and g2['precios_dia'].sort_values(['fecha', 'ean_norm']).reset_index(drop=True)
          .equals(base_p.sort_values(['fecha', 'ean_norm']).reset_index(drop=True))
          and g2['prov_val'].equals(base_pv) and g2['rub_val'].equals(base_rv))
    chk(f'{nombre}: igual (leídos {sorted(g2["A_LEER"])})', ok and sorted(g2['A_LEER']) == leidos)

cache = next((out / '_cache').glob('diaria_v3_*'))
igual('segunda corrida desde el caché', correr(), ['2026-03'])
(cache / '2026-02.parquet').unlink()
igual('sin febrero en el caché', correr(), ['2026-02', '2026-03'])
(cache / '2026-02.parquet').unlink(); (cache / 'estado_2026-01.parquet').unlink()
igual('sin febrero ni el estado de enero', correr(), ['2026-01', '2026-02', '2026-03'])
igual('sin caché', correr(USE_CACHE=False), ['2026-01', '2026-02', '2026-03'])

shutil.rmtree(tmp, ignore_errors=True)
if errores:
    print('FALLAS:'); [print('  ' + x) for x in errores]
    sys.exit(1)
print(f'OK: {len(pdia)} producto-días, {len(S)} días; medianas, relativos apareados, índices, hueco, provincias, rubros, '
      f'caché: todo igual a la fuerza bruta')
