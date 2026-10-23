"""Test del nb06 (brecha celíaca, canasta fija): corre las celdas REALES del notebook sobre un SEPA sintético y compara
cada número con un cálculo directo (fuerza bruta).

El SEPA sintético (ene-mar 2026, 8 sucursales de 4 comercios, 2 tipos) trae a propósito:
  - dos archivos para la misma parte de enero (el completo COMPLETOb y uno parcial COMPLETO, días 1-5): se usa uno;
  - una fila sucursal x producto repetida y marzo en centavos;
  - un producto con TACC que cambia de código en febrero (los dos códigos en la canasta, conviven en febrero; el viejo
    con precio congelado, fuera de su VIGENCIA) y uno sin TACC con un código nuevo que convive con el viejo al mismo
    precio (PRODUCTO: cuenta una vez en la mediana del lado);
  - un producto con precio x10 (lo saca el filtro de plausibilidad) y otro que salta x2,5 en marzo (control de identidad);
  - dos subtipos por tipo (SUBTIPO) y sucursales a las que les falta el sin TACC de un subtipo: la brecha del tipo es el
    promedio geométrico de las de sus subtipos con los dos lados;
  - una estación de servicio (comercio 23, fuera del universo) y una sucursal 'Web';
  - una sucursal declarada en Mendoza con coordenadas en Córdoba (se reclasifica) y sucursales de Buenos Aires cerca y
    lejos del Obelisco (AMBA / Pampeana);
  - la caché de Georef del nb09 con el departamento de cada sucursal (concentración: HHI de empresas por departamento).
Además, con tablas chicas armadas a mano: un grupo al que le faltan subtipos (misma canasta: toman la brecha nacional) y
un subtipo que falta un mes en la serie (hoja Imputaciones). Serie TPD (CELDA 8b): sin ruido recupera exacto la prima
de cada mes aunque falten productos y un subtipo entero; sobre el SEPA sintético es igual a mínimos cuadrados densos con
todas las indicadoras y la covarianza agrupada escrita a mano (tipo y canasta); un subtipo con productos que no se
pueden comparar queda afuera. Corre dos veces: la segunda lee los meses cerrados del caché.

    python notebooks/test_brecha_celiaca.py
"""
import gzip, io, json, os, sys, tempfile, zipfile
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
for _st in (sys.stdout, sys.stderr):        # el notebook imprime flechas y acentos: que no corte en una consola cp1252
    try:
        _st.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

REPO = Path(__file__).resolve().parents[1]
NB = REPO / 'notebooks' / '06_evolucion_brecha_celiaca.ipynb'

# ── Sucursales, polígonos y productos ──────────────────────────────────────────
SUCS = {  # (comercio, bandera, sucursal): (provincia declarada, lat, lon, tipo, nivel de precios)
    ('9', '1', '101'): ('Ciudad Autónoma de Buenos Aires', -34.60, -58.40, 'Supermercado', 1.00),
    ('9', '1', '102'): ('Ciudad Autónoma de Buenos Aires', -34.62, -58.45, 'Supermercado', 1.10),
    ('10', '1', '201'): ('Provincia de Buenos Aires', -34.92, -57.95, 'Hipermercado', 0.90),   # La Plata: AMBA
    ('10', '1', '202'): ('Provincia de Buenos Aires', -38.00, -57.55, 'Hipermercado', 1.20),   # Mar del Plata
    ('15', '1', '301'): ('Provincia de Córdoba', -31.42, -64.18, 'Supermercado', 0.95),
    ('15', '1', '302'): ('Provincia de Mendoza', -31.40, -64.20, 'Supermercado', 1.05),        # mal declarada
    ('15', '1', '303'): ('Ciudad Autónoma de Buenos Aires', -34.61, -58.42, 'Web', 1.00),      # web: afuera
    ('23', '1', '401'): ('Ciudad Autónoma de Buenos Aires', -34.58, -58.43, 'Autoservicio', 1.00),  # Axion: afuera
}
POLI = {'ARC': ('Ciudad de Buenos Aires', -58.55, -58.33, -34.72, -34.52),
        'ARB': ('Buenos Aires', -63.5, -56.6, -41.0, -33.3),
        'ARX': ('Córdoba', -65.8, -61.7, -35.0, -29.5),
        'ARM': ('Mendoza', -70.6, -66.5, -37.6, -32.0)}
# EAN: (tipo, lado, gramos, $/100 g base del lado, meses en que existe)
P = {
    '7790000000011': ('Fideos secos', 'tacc', 500, 400, (1, 2, 3)),
    '7790000000028': ('Fideos secos', 'tacc', 500, 420, (1, 2)),        # código viejo
    '7790000000035': ('Fideos secos', 'tacc', 500, 420, (2, 3)),        # código nuevo del mismo producto
    '7790000000042': ('Fideos secos', 'sin', 250, 1000, (1, 2, 3)),
    '7790000000059': ('Fideos secos', 'sin', 500, 1100, (1, 2, 3)),
    '7790000000110': ('Fideos secos', 'sin', 250, 1000, (2, 3)),       # código nuevo del 042: conviven
    '7790000000066': ('Galletitas dulces', 'tacc', 100, 1000, (1, 2, 3)),
    '7790000000073': ('Galletitas dulces', 'tacc', 200, 900, (1, 2, 3)),
    '7790000000080': ('Galletitas dulces', 'tacc', 150, 10000, (1, 2, 3)),   # x10: plausibilidad
    '7790000000097': ('Galletitas dulces', 'sin', 105, 1600, (1, 2, 3)),
    '7790000000103': ('Galletitas dulces', 'sin', 150, 1500, (1, 2, 3)),     # salta x2,5 en marzo
    '7799999999998': ('otro', 'tacc', 100, 500, (1, 2, 3)),                  # fuera de la canasta
}
FALTA = {(('15', '1', '301'), '7790000000059'), (('9', '1', '102'), '7790000000103')}
PESOS = {'Fideos secos': 1.503, 'Galletitas dulces': 1.717}
DIAS = pd.date_range('2026-01-01', '2026-03-31')

def precio(s, e, d):
    tipo, lado, g, base, meses = P[e]
    infl = 1.05 ** (d.month - 1)
    salto = 2.5 if (e == '7790000000103' and d.month == 3) else 1.0
    if e == '7790000000028' and d.month == 2:      # código viejo con precio congelado después del cambio
        salto = 0.3
    ruido = 1 + 0.02 * np.sin(d.day * 1.7 + int(e[-3:]) % 7) + 0.01 * np.cos(int(s[2]) % 13 + d.day)
    return base * g / 100 * SUCS[s][4] * infl * salto * ruido

filas = []
for s in SUCS:
    for e, (tipo, lado, g, base, meses) in P.items():
        if (s, e) in FALTA:
            continue
        for d in DIAS:
            if d.month in meses:
                filas.append((*s, e, d, round(precio(s, e, d), 2)))
obs = pd.DataFrame(filas, columns=['c', 'b', 's', 'e', 'd', 'precio'])

def tabla(mes, dd, centavos=False):
    o = obs[obs['d'].isin(dd)]
    w = o.pivot_table(index=['c', 'b', 's', 'e'], columns='d', values='precio', aggfunc='first')
    w = w.reindex(columns=dd) * (100 if centavos else 1)
    w.columns = [f'precio_{d:%Y%m%d}' for d in dd]
    w = w.reset_index().rename(columns={'c': 'id_comercio', 'b': 'id_bandera', 's': 'id_sucursal', 'e': 'id_producto'})
    w.insert(3, 'sucursales_provincia', 'AR-C')
    return w

def gz(w):
    buf = io.StringIO(); w.to_csv(buf, index=False, na_rep='NA', float_format='%.4f')
    return gzip.compress(buf.getvalue().encode())

tmp = Path(tempfile.mkdtemp(prefix='test_nb06_'))
sepa = tmp / 'carga'; sepa.mkdir()
out = tmp / 'output_brecha'; out.mkdir()
(tmp / 'data').mkdir()
usados = []
with zipfile.ZipFile(sepa / '2026A.zip', 'w') as zf:
    for mes in (1, 2, 3):
        dm = [d for d in DIAS if d.month == mes]
        for parte, dd in ((1, [d for d in dm if d.day <= 15]), (2, [d for d in dm if d.day > 15])):
            w = tabla(mes, dd, centavos=(mes == 3))
            if (mes, parte) == (2, 1):    # una fila repetida
                w = pd.concat([w, w.iloc[[3]]], ignore_index=True)
            zf.writestr(f'{mes:02d}2026_pais_parte{parte}COMPLETO{"b" if (mes, parte) == (1, 1) else ""}.csv.gz', gz(w))
            usados.append((mes, w, mes == 3))
            if (mes, parte) == (1, 1):     # parcial (días 1-5) de la misma parte: no se usa ni se suma
                zf.writestr('012026_pais_parte1COMPLETO.csv.gz', gz(tabla(1, [d for d in dd if d.day <= 5])))
feats = [{'type': 'Feature', 'properties': {'id': k, 'name': n},
          'geometry': {'type': 'Polygon', 'coordinates': [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]]}}
         for k, (n, x0, x1, y0, y1) in POLI.items()]
(sepa / 'ar.json').write_text(json.dumps({'type': 'FeatureCollection', 'features': feats}), encoding='utf-8')
ms = pd.DataFrame([{'id_comercio': c, 'id_bandera': b, 'id_sucursal': s, 'sucursales_nombre': f'Suc {c}-{s}',
                    'sucursales_tipo': t, 'sucursales_latitud': la, 'sucursales_longitud': lo,
                    'sucursales_localidad': 'Loc', 'PROVINCIA': pv}
                   for (c, b, s), (pv, la, lo, t, _n) in SUCS.items()])
ms.to_excel(tmp / 'data' / 'maestro_sucursales_completo.xlsx', index=False)
# caché de Georef del nb09: departamento de cada sucursal (la estación de servicio 401 no entra en el HHI)
DEPTO = {('9', '1', '101'): '02001', ('9', '1', '102'): '02001', ('10', '1', '201'): '02001', ('23', '1', '401'): '02001',
         ('10', '1', '202'): '06357', ('15', '1', '301'): '14014', ('15', '1', '302'): '14014', ('15', '1', '303'): '02001'}
(sepa / 'output_trazabilidad' / '_cache_nb09').mkdir(parents=True)
pd.DataFrame([{'suc': f'{c}|{b}|{s}', 'departamento_id': d, 'departamento': f'Depto {d}', 'municipio': 'M',
               'provincia_georef': 'P'} for (c, b, s), d in DEPTO.items()]).to_parquet(
    sepa / 'output_trazabilidad' / '_cache_nb09' / 'georef_sucursales.parquet', index=False)
mp = pd.DataFrame([{'producto_sepa_id': e, 'producto_descripcion': f'Producto {e[-3:]} {g} Gr', 'producto_marca': 'M',
                    'rubro': 'Almacén', 'producto_cantidad_presentacion': str(g), 'producto_unidad_medida_presentac': 'gr'}
                   for e, (t, l, g, b, m) in P.items()])
mp.to_excel(tmp / 'data' / 'Maestro de Productos Interno.xlsx', index=False)

TIPOS = {t: {'peso': PESOS[t],
             'tacc': {e: f'Producto {e[-3:]}' for e, v in P.items() if v[0] == t and v[1] == 'tacc'},
             'sin_tacc': {e: f'Producto {e[-3:]}' for e, v in P.items() if v[0] == t and v[1] == 'sin'}}
         for t in PESOS}
GRAMOS = {e: v[2] for e, v in P.items() if v[0] in PESOS}
VIGENCIA = {'7790000000028': (None, '2026-01'), '7790000000035': ('2026-02', None)}
FUERA_VIG = {('7790000000028', '2026-02')}
PRODUCTO = {'Fideo sin TACC X': ['7790000000042', '7790000000110'],
            'Fideo con TACC Y': ['7790000000028', '7790000000035']}   # cambio de código (vigencia), como Molinos
PROD_DE = {e: p for p, es in PRODUCTO.items() for e in es}
SUBTIPO = {'A': ['7790000000011', '7790000000042', '7790000000110'],
           'B': ['7790000000028', '7790000000035', '7790000000059'],
           'C': ['7790000000066', '7790000000097'],
           'D': ['7790000000073', '7790000000080', '7790000000103']}
SUB_DE = {e: s for s, es in SUBTIPO.items() for e in es}

# ── Correr las celdas reales (dos veces) ─────────────────────────────────────────
cells = [''.join(c['source']) for c in json.load(open(NB, encoding='utf-8'))['cells'] if c['cell_type'] == 'code']
os.chdir(tmp)

def correr():
    g = {}
    exec(cells[0], g)
    g.update(SEPA_DIR=str(sepa), OUTPUT_DIR=str(out), TIPOS=TIPOS, GRAMOS=GRAMOS, VIGENCIA=VIGENCIA,
             PRODUCTO=PRODUCTO, SUBTIPO=SUBTIPO, MES_INICIO_HISTORICO='2026-01', MIN_SUC_AGG=1, MIN_SUC_SUBTIPO=1,
             VENTANA_GEO_MESES=12, USAR_GEOREF=False, MIN_SUC_DEPTO=1)
    for c in cells[1:]:
        exec(c, g)
    return g

g = correr()
g2 = correr()
errores = []

def chk(nombre, ok):
    print(('  OK   ' if ok else '  FALLA ') + nombre)
    if not ok:
        errores.append(nombre)

# ── Fuerza bruta ────────────────────────────────────────────────────────────────
largo = []
for mes, w, cent in usados:
    pc = [c for c in w.columns if c.startswith('precio_')]
    m = w.melt(id_vars=['id_comercio', 'id_bandera', 'id_sucursal', 'id_producto'], value_vars=pc, var_name='c',
               value_name='precio').dropna(subset=['precio'])
    m['dia'] = m['c'].str[-8:]
    m['mes'] = f'2026-{mes:02d}'
    m['precio'] = m['precio'] / (100 if cent else 1)
    largo.append(m)
L = pd.concat(largo, ignore_index=True)
L = L.groupby(['id_comercio', 'id_bandera', 'id_sucursal', 'id_producto', 'mes', 'dia'], as_index=False)['precio'].median()
M = L.groupby(['id_comercio', 'id_bandera', 'id_sucursal', 'id_producto', 'mes'], as_index=False).agg(
    precio=('precio', 'median'), dias=('precio', 'size'))
M = M[M['id_producto'].isin(GRAMOS)]
M = M[[(e, m) not in FUERA_VIG for e, m in zip(M['id_producto'], M['mes'])]]
dd = g['datos_dia'][['id_comercio', 'id_bandera', 'id_sucursal', 'ean_norm', 'mes', 'precio', 'dias']]
cmp = M.merge(dd, left_on=['id_comercio', 'id_bandera', 'id_sucursal', 'id_producto', 'mes'],
              right_on=['id_comercio', 'id_bandera', 'id_sucursal', 'ean_norm', 'mes'], how='left', suffixes=('', '_nb'))
cmp = cmp[~cmp['id_comercio'].isin(['23']) & ~((cmp['id_comercio'] == '15') & (cmp['id_sucursal'] == '303'))
          & ~cmp['id_producto'].eq('7790000000080')]
chk('mediana mensual exacta por sucursal x EAN (todas las partes, centavos en marzo)',
    cmp['precio_nb'].notna().all() and np.allclose(cmp['precio'], cmp['precio_nb'], rtol=1e-9))
chk('días con precio: enero 31 (no suma el archivo parcial de los días 1-5)',
    (cmp.loc[cmp['mes'] == '2026-01', 'dias_nb'] == 31).all())
chk('enero usa el archivo COMPLETOb', any('COMPLETOb' in n for _z, n in g['_mapa_mes']['2026-01'])
    and len(g['_mapa_mes']['2026-01']) == 2)
chk('Axion (23) y la sucursal web fuera', not g['bt_sm']['id_comercio'].eq('23').any()
    and not g['bt_sm']['id_sucursal'].eq('303').any())
chk('plausibilidad saca el EAN x10', set(g['plausibilidad']['ean_norm']) == {'7790000000080'})
ce = g['control_ean'].set_index('ean_norm')
chk('control de identidad marca el salto x2,5', bool(ce.loc['7790000000103', 'revisar'])
    and not ce.drop(index='7790000000103')['revisar'].any())
sg = g['suc_geo'].set_index('id_sucursal')
chk('reclasifica la sucursal de Mendoza con coordenadas en Córdoba', sg.loc['302', 'PROVINCIA_NORM'] == 'Córdoba')
chk('región: CABA y La Plata = AMBA, Mar del Plata = Pampeana, Córdoba = Pampeana',
    list(sg.loc[['101', '102', '201', '202', '301', '302'], 'region']) == ['AMBA'] * 3 + ['Pampeana'] * 3)
chk('cadenas: Vea, Carrefour, DIA', set(g['bt_sm']['cadena']) == {'Vea', 'Carrefour', 'DIA'})

# brecha por sucursal x mes x tipo
B = M.merge(pd.DataFrame([(e, v[0], v[1], v[2]) for e, v in P.items()], columns=['id_producto', 'tipo', 'rol', 'g']),
            on='id_producto')
B = B[~B['id_comercio'].eq('23') & ~B['id_sucursal'].eq('303') & ~B['id_producto'].eq('7790000000080')]
B['p100'] = B['precio'] / B['g'] * 100
B['prod'] = B['id_producto'].map(PROD_DE).fillna(B['id_producto'])   # producto con dos códigos: mediana de los dos
B['sub'] = B['id_producto'].map(SUB_DE)
_ks = ['id_comercio', 'id_bandera', 'id_sucursal', 'mes', 'tipo']
_kb = _ks + ['sub', 'rol']
SS = B.groupby(_kb + ['prod'])['p100'].median().groupby(level=_kb).median().unstack('rol').dropna()   # subtipos con los dos lados
SS['brecha'] = (SS['sin'] / SS['tacc'] - 1) * 100
S = np.exp(np.log(SS[['tacc', 'sin']]).groupby(level=_ks).mean())    # tipo: promedio geométrico de sus subtipos
S['brecha'] = (S['sin'] / S['tacc'] - 1) * 100
S = S.reset_index()
SS = SS.reset_index()
bs = g['bt_sub'].merge(SS.rename(columns={'sub': 'subtipo'}), on=_ks + ['subtipo'], suffixes=('', '_fb'))
chk('brecha por sucursal x mes x subtipo (falta el sin TACC del subtipo B en la sucursal 301 y del D en la 102)',
    len(bs) == len(SS) == len(g['bt_sub']) and np.allclose(bs['brecha_pct'], bs['brecha'], rtol=1e-9)
    and not ((g['bt_sub']['id_sucursal'] == '301') & (g['bt_sub']['subtipo'] == 'B')).any())
bt = g['bt_sm'].merge(S, on=['id_comercio', 'id_bandera', 'id_sucursal', 'mes', 'tipo'], suffixes=('', '_fb'))
chk('brecha por sucursal x mes x tipo = promedio geométrico de sus subtipos', len(bt) == len(S) == len(g['bt_sm'])
    and np.allclose(bt['brecha_pct'], bt['brecha'], rtol=1e-9) and np.allclose(bt['tacc'], bt['tacc_fb'], rtol=1e-9))
def tipo_desde_subtipos(keys):
    # mediana de cada subtipo entre sucursal-mes del grupo; tipo = promedio geométrico de sus subtipos
    m = SS.groupby(keys + ['tipo', 'sub'])['brecha'].median()
    return np.expm1(np.log1p(m / 100).groupby(level=keys + ['tipo']).mean()) * 100

bt_t = g['brecha_tipo'].set_index('tipo')['brecha_mediana']
chk('brecha por tipo = promedio geométrico de las medianas de sus subtipos',
    np.allclose(bt_t.sort_index(), tipo_desde_subtipos([]).sort_index(), rtol=1e-12))
gm = tipo_desde_subtipos(['mes']).unstack('tipo')
w = pd.Series(PESOS) / sum(PESOS.values())
esp = ((1 + gm / 100) * w).sum(axis=1) / w.sum() * 100 - 100
sm = g['serie_mensual'].set_index('mes')['brecha_canasta']
chk('canasta mensual = promedio ENGHo de las brechas por tipo', np.allclose(sm.sort_index(), esp.sort_index(), rtol=1e-12))
_d = pd.DataFrame([{'mes': mes, 'tipo': 'T', 'subtipo': s, 'suc_key': f'{s}{k}', 'tacc': 100.0, 'sin': 100.0 + br,
                    'brecha_pct': br, 'brecha_min': br}
                   for mes, subs in (('2026-01', {'A': 100, 'B': 50}), ('2026-02', {'A': 120}), ('2026-03', {'A': 80, 'B': 60}))
                   for s, br in subs.items() for k in range(4)])
_r = g['_agg_tipo'](_d, ['mes']).set_index('mes')
chk('serie mensual: un subtipo-mes faltante se imputa con su último mes válido',
    abs(_r.loc['2026-02', 'brecha_mediana'] - (np.sqrt(2.20 * 1.50) - 1) * 100) < 1e-9
    and list(_r['n_subtipos_imputados']) == [0, 1, 0] and list(_r['n_subtipos']) == [2, 2, 2])
pond = g['ponderaciones'].set_index('tipo')
pb = S.groupby('tipo')['tacc'].median()
chk('cantidades ENGHo: con los precios del año base el gasto con TACC se reparte como la ENGHo',
    np.allclose((pond['cantidad_100g_canasta_sucursal'] * pb / (pond['cantidad_100g_canasta_sucursal'] * pb).sum())
                .sort_index(), w.sort_index(), rtol=1e-12))
_feb = set(g['datos_dia'].loc[g['datos_dia']['mes'] == '2026-02', 'ean_norm'])
chk('vigencia: en febrero entra el código nuevo y no el viejo (precio congelado)',
    '7790000000035' in _feb and '7790000000028' not in _feb
    and '7790000000028' in set(g['datos_dia'].loc[g['datos_dia']['mes'] == '2026-01', 'ean_norm']))
_f = g['bt_sm'][(g['bt_sm']['tipo'] == 'Fideos secos') & (g['bt_sm']['id_sucursal'] == '101')].set_index('mes')
chk('producto con dos códigos que conviven: cuenta una vez (2 productos sin TACC en feb-mar, no 3)',
    list(_f.loc[['2026-01', '2026-02', '2026-03'], 'n_sin']) == [2, 2, 2])
br = g['brecha_region'].set_index('region')
chk('región AMBA y Pampeana con los dos tipos', set(br.index) == {'AMBA', 'Pampeana'} and (br['n_tipos'] == 2).all())

# canasta COMPARABLE por sucursal y mes: subtipo propio o, si la sucursal no lo tiene, la brecha nacional del mes
W = pd.Series(PESOS) / sum(PESOS.values())
TSUB = {'A': 'Fideos secos', 'B': 'Fideos secos', 'C': 'Galletitas dulces', 'D': 'Galletitas dulces'}
nac = SS.groupby(['mes', 'sub'])['brecha'].median()
own = SS.assign(suc=SS['id_comercio'] + '|' + SS['id_bandera'] + '|' + SS['id_sucursal']).set_index(['suc', 'mes', 'sub'])['brecha']
fb = {}
for suc, mes in g['brecha_suc_mes'][['suc_key', 'mes']].itertuples(index=False):
    rel, propio = 0.0, 0.0
    for t in PESOS:
        subs = [s for s in TSUB if TSUB[s] == t]
        lg = []
        for s in subs:
            v = own.get((suc, mes, s))
            if v is not None and v == v:
                propio += W[t] / len(subs)
            else:
                v = nac[(mes, s)]
            lg.append(np.log1p(v / 100))
        rel += W[t] * np.exp(np.mean(lg))
    fb[(suc, mes)] = ((rel - 1) * 100, 100 * propio)
bsm = g['brecha_suc_mes'].set_index(['suc_key', 'mes'])
chk('canasta comparable por sucursal (falta el subtipo B en la 301 y el D en la 102: brecha nacional del mes)',
    all(abs(bsm.loc[k, 'brecha_comparable'] - v[0]) < 1e-9 and abs(bsm.loc[k, 'peso_propio_pct'] - v[1]) < 1e-9
        for k, v in fb.items())
    and abs(bsm.loc[('15|1|301', '2026-02'), 'peso_propio_pct'] - 100 * (1 - W['Fideos secos'] / 2)) < 1e-9)

# grupos con la MISMA canasta: el subtipo con < MIN_SUC_SUBTIPO sucursales en el grupo toma la brecha nacional
_rows = []
for grupo, subs in (('g1', {'A': (100, 120, 140), 'B': (50, 60, 70), 'C': (80, 90, 100), 'D': (20, 30, 40)}),
                    ('g2', {'A': (200, 210, 220), 'B': (150, 160, 170), 'C': (300,)})):
    for s, vals in subs.items():
        for k, v in enumerate(vals):
            _rows.append({'grupo': grupo, 'tipo': TSUB[s], 'subtipo': s, 'suc_key': f'{grupo}{s}{k}', 'tacc': 100.0,
                          'sin': 100.0 + v, 'brecha_pct': float(v), 'brecha_min': float(v)})
_dg = pd.DataFrame(_rows)
g['MIN_SUC_SUBTIPO'], g['MAX_PESO_IMPUTADO'] = 2, 25
_cg = g['_canasta'](_dg, ['grupo'], []).set_index('grupo')
g['MIN_SUC_SUBTIPO'] = 1
_nat = _dg.groupby('subtipo')['brecha_pct'].median()
_l = lambda *v: np.exp(np.mean(np.log1p(np.array(v) / 100)))
_e1 = W['Fideos secos'] * _l(120, 60) + W['Galletitas dulces'] * _l(90, 30) - 1
_e2 = W['Fideos secos'] * _l(210, 160) + W['Galletitas dulces'] * _l(_nat['C'], _nat['D']) - 1
chk('grupos: subtipos sin datos en el grupo con la brecha nacional; peso imputado y confiable',
    abs(_cg.loc['g1', 'brecha_canasta'] - 100 * _e1) < 1e-9 and abs(_cg.loc['g2', 'brecha_canasta'] - 100 * _e2) < 1e-9
    and abs(_cg.loc['g2', 'peso_imputado_pct'] - 100 * W['Galletitas dulces']) < 1e-9
    and _cg.loc['g1', 'peso_imputado_pct'] == 0 and bool(_cg.loc['g1', 'confiable'])
    and not bool(_cg.loc['g2', 'confiable']) and _cg.loc['g2', 'subtipos_con_brecha_nacional'] == 'C, D'
    and _cg.loc['g2', 'n_Galletitas dulces'] == 0 and _cg.loc['g2', 'n_tipos'] == 2)

# hoja Imputaciones: rachas de un subtipo imputado con su último mes válido
_det = []
g['_agg_tipo'](_d, ['mes'], None, _det)
_ri = pd.DataFrame(g['_rachas'](_det, 'x'))
chk('imputaciones: el subtipo B falta en febrero y arrastra la brecha de enero',
    len(_ri) == 1 and _ri.iloc[0][['subtipo', 'desde', 'hasta', 'meses']].tolist() == ['B', '2026-02', '2026-02', 1]
    and abs(_ri.iloc[0]['brecha_arrastrada'] - 50) < 1e-9 and 'Imputaciones' in pd.ExcelFile(
        out / 'brecha_celiaca_2026-03.xlsx').sheet_names)

# concentración: HHI de empresas por departamento (cuota = sucursales; sin la estación de servicio) y brecha mediana
cc = g['concentracion'].set_index('departamento_id')
bsuc = g['brecha_suc_mes'].groupby('suc_key')['brecha_comparable'].median()
chk('concentración: HHI por departamento (2/3 Cencosud y 1/3 Carrefour en el 02001) y brecha de sus sucursales',
    abs(cc.loc['02001', 'hhi'] - 5 / 9) < 1e-12 and cc.loc['02001', 'sucursales'] == 3 and cc.loc['02001', 'empresas'] == 2
    and cc.loc['02001', 'empresa_principal'] == 'Cencosud (Vea, Disco, Jumbo)' and cc.loc['06357', 'hhi'] == 1
    and cc.loc['14014', 'hhi'] == 1 and cc.loc['14014', 'sucursales_con_brecha'] == 2
    and abs(cc.loc['02001', 'brecha_mediana'] - bsuc[['9|1|101', '9|1|102', '10|1|201']].median()) < 1e-9
    and (out / 'brecha_concentracion_032026.png').exists())

# ── Serie TPD (CELDA 8b) ────────────────────────────────────────────────────────
# (a) sin ruido, con productos que faltan al azar y el lado sin TACC del subtipo B que en los meses 3 y 6 está en una sola
#     sucursal y en los meses 4 y 5 en ninguna (la descriptiva lo arrastraría): la TPD recupera exacto la prima de cada mes
#     (los meses sin pares de B, moviéndolo con los demás subtipos del tipo); niveles con los pesos por disponibilidad.
#     Con un mínimo de 2 sucursales con pares (MIN_SUC_SUBTIPO), B se mueve también en los meses de una sola, y sigue exacto
rng = np.random.default_rng(7)
TR = {'T1': {'A': (['a1', 'a2'], ['a3', 'a4']), 'B': (['b1', 'b2'], ['b3', 'b4'])}, 'T2': {'C': (['c1', 'c2'], ['c3'])}}
BETA = {'T1': [0, .05, .12, .2, .15, .3, .35, .25, .4, .5], 'T2': [0, -.02, .04, .1, .1, .12, .2, .18, .25, .3]}
GAM = {p: rng.normal(0, .3) + (0.8 if p in ('a3', 'a4', 'b3', 'b4', 'c3') else 0) for t in TR for s in TR[t]
       for lado in TR[t][s] for p in lado}
MS = [f'2025-{m:02d}' for m in range(1, 11)]
_rows = []
for s in range(30):
    for t, mes in enumerate(MS):
        alfa = rng.normal(0, .2)
        for tipo, subs in TR.items():
            for sub, (con, sin) in subs.items():
                alfa_sub = alfa + rng.normal(0, .1)          # efecto de la celda (sucursal × mes × subtipo)
                for p in con + sin:
                    if tipo == 'T1' and sub == 'B' and p in sin and ((t in (2, 5) and s != 0) or t in (3, 4)):
                        continue
                    if rng.random() > 0.7 and not (s == 0 and p in sin):
                        continue
                    _rows.append({'suc_key': f's{s}', 'mes': mes, 'tipo': tipo, 'subtipo': sub,
                                  'rol': 'sin' if p in sin else 'tacc', 'producto': p,
                                  'precio_100': float(np.exp(alfa_sub + GAM[p] + BETA[tipo][t] * (p in sin)))})
_df_tpd = pd.DataFrame(_rows)
_obs = _df_tpd.groupby('producto').size()
def _nivel(con, sin):
    return (sum(GAM[p] * _obs[p] for p in sin) / _obs[list(sin)].sum()
            - sum(GAM[p] * _obs[p] for p in con) / _obs[list(con)].sum())
_L = {'T1': np.mean([_nivel(*TR['T1'][m]) for m in ('A', 'B')]), 'T2': _nivel(*TR['T2']['C'])}
def _ok_tpd_exacto(_min_suc, _movidos):
    _tr = g['_tpd_serie'](_df_tpd, ['T1', 'T2'], {'T1': 0.6, 'T2': 0.4}, _min_suc)
    _tt = _tr['tipos'].set_index(['tipo', 'mes'])
    _ok_t = all(abs(_tt.loc[(tp, mes), 'brecha_tpd'] - 100 * np.expm1(_L[tp] + BETA[tp][t])) < 1e-6
                and _tt.loc[(tp, mes), 'error_estandar_log'] < 1e-6 for tp in TR for t, mes in enumerate(MS))
    _can = _tr['canasta'].set_index('mes')
    _ok_c = all(abs(_can.loc[mes, 'brecha_canasta_tpd'] - 100 * (0.6 * np.exp(_L['T1'] + BETA['T1'][t])
                                                                 + 0.4 * np.exp(_L['T2'] + BETA['T2'][t]) - 1)) < 1e-6
                # peso movido: la mitad de T1 (B de 2 subtipos) con el 60% del peso
                and abs(_can.loc[mes, 'peso_movido_pct'] - (30 if t in _movidos else 0)) < 1e-9 for t, mes in enumerate(MS))
    _mov = _tr['subtipos'].set_index(['subtipo', 'mes'])['movido_con_los_demas']
    _aj = _tr['ajuste'].set_index('subtipo')
    return (_ok_t and _ok_c and len(_tt) == 20 and _aj['rango_completo'].all()
            and list(_mov.loc['B'].to_numpy()) == [t in _movidos for t in range(10)] and not _mov.loc['A'].any()
            and list(_tt.loc['T1', 'subtipos_movidos']) == [int(t in _movidos) for t in range(10)]
            and _aj.loc['B', 'meses_con_pares'] == 8 and _aj.loc['B', 'meses_con_dato_propio'] == 10 - len(_movidos))
chk('TPD: recupera exacto la prima de cada mes aunque falten productos y el subtipo B no tenga pares en 2 meses '
    '(con mínimo de 2 sucursales, tampoco en los 2 de una sola)', _ok_tpd_exacto(1, (3, 4)) and _ok_tpd_exacto(2, (2, 3, 4, 5)))

# (b) sobre el SEPA sintético: la CELDA 8b contra mínimos cuadrados densos con todas las variables indicadoras (efecto
#     de cada celda sucursal-mes, de cada producto y sin TACC × mes, una regresión por subtipo) y la covarianza agrupada
#     por sucursal escrita a mano, sumando los puntajes de los subtipos (tipo) y de los tipos (canasta)
PP = (B.groupby(['id_comercio', 'id_bandera', 'id_sucursal', 'mes', 'tipo', 'sub', 'rol', 'prod'])['p100'].median()
      .reset_index())
PP['suc'] = PP['id_comercio'] + '|' + PP['id_bandera'] + '|' + PP['id_sucursal']
PP['w'] = 1 / PP.groupby(['suc', 'mes', 'tipo', 'sub', 'rol'])['prod'].transform('size')
SUCS_PP = sorted(PP['suc'].unique())
MESES_PP = sorted(PP['mes'].unique())
Q_PP = len(SUCS_PP) / (len(SUCS_PP) - 1)
_niv, _gs = {}, {}              # (tipo, subtipo, mes) -> nivel; (tipo, subtipo, mes) -> vector de puntajes Sc @ bread @ a
for (tipo, sub), D in PP.groupby(['tipo', 'sub']):
    D = D.reset_index(drop=True)
    gm = sorted(set(zip(D['suc'], D['mes'])))
    prods = sorted(D['prod'].unique())
    ref = sorted(D.loc[D['rol'] == 'tacc', 'prod'].unique())[0]
    cols = [('g', x) for x in gm] + [('p', p) for p in prods if p != ref] + [('b', m) for m in MESES_PP[1:]]
    ci = {c: i for i, c in enumerate(cols)}
    X = np.zeros((len(D), len(cols)))
    for i, r in D.iterrows():
        X[i, ci[('g', (r['suc'], r['mes']))]] = 1
        if r['prod'] != ref:
            X[i, ci[('p', r['prod'])]] = 1
        if r['rol'] == 'sin' and r['mes'] != MESES_PP[0]:
            X[i, ci[('b', r['mes'])]] = 1
    y, w_ = np.log(D['p100'].to_numpy()), D['w'].to_numpy()
    bread = np.linalg.inv(X.T @ (X * w_[:, None]))
    coef = bread @ (X.T @ (w_ * y))
    u = y - X @ coef
    S = np.zeros((len(SUCS_PP), len(cols)))
    for i, r in D.iterrows():
        S[SUCS_PP.index(r['suc'])] += w_[i] * X[i] * u[i]
    obs = D.groupby('prod').size()
    a_L = np.zeros(len(cols))
    for lado, sg in (('sin', 1.0), ('tacc', -1.0)):
        ps = sorted(D.loc[D['rol'] == lado, 'prod'].unique())
        for p in ps:
            if p != ref:
                a_L[ci[('p', p)]] += sg * obs[p] / obs[ps].sum()
    L = a_L @ coef
    for mes in MESES_PP:
        a = a_L.copy()
        if mes != MESES_PP[0]:
            a[ci[('b', mes)]] += 1
        _niv[(tipo, sub, mes)] = L + (coef[ci[('b', mes)]] if mes != MESES_PP[0] else 0.0)
        _gs[(tipo, sub, mes)] = S @ (bread @ a)
bt_tpd = g['brecha_tipo_tpd']
bt_tpd = bt_tpd[bt_tpd['universo'] == 'todas las sucursales'].set_index(['tipo', 'mes'])
_ok_tipo, _lam = True, {}
for tipo in PESOS:
    subs_t = sorted({k[1] for k in _niv if k[0] == tipo})
    for mes in MESES_PP:
        lam = np.mean([_niv[(tipo, s_, mes)] for s_ in subs_t])
        z = sum(_gs[(tipo, s_, mes)] for s_ in subs_t) / len(subs_t)
        _lam[(tipo, mes)] = (lam, z)
        _ok_tipo &= (abs(bt_tpd.loc[(tipo, mes), 'brecha_tpd'] - 100 * np.expm1(lam)) < 1e-8
                     and abs(bt_tpd.loc[(tipo, mes), 'error_estandar_log'] - np.sqrt(Q_PP * float(z @ z))) < 1e-10)
chk('TPD sobre el SEPA sintético: brecha por tipo y mes y su error estándar = mínimos cuadrados densos por subtipo',
    _ok_tipo and len(bt_tpd) == len(_lam))
_sw = sum(PESOS.values())
_ok_can = True
st_ = g['serie_tpd'].set_index('mes')
for mes in MESES_PP:
    v = sum(PESOS[tp] * np.exp(_lam[(tp, mes)][0]) for tp in PESOS) / _sw
    z = sum(_lam[(tp, mes)][1] * PESOS[tp] * np.exp(_lam[(tp, mes)][0]) / _sw for tp in PESOS)
    se = np.sqrt(Q_PP * float(z @ z))
    _ok_can &= (abs(st_.loc[mes, 'brecha_canasta_tpd_todas'] - 100 * (v - 1)) < 1e-8
                and abs(st_.loc[mes, 'brecha_canasta_tpd_ic95_sup_todas'] - 100 * (v + 1.96 * se - 1)) < 1e-8)
# (c) dos códigos del mismo producto con TACC que nunca conviven y SIN unir en PRODUCTO: el nivel del subtipo B no está
#     identificado (se confunde con la prima del mes); la TPD no lo inventa: lo deja afuera y el tipo sale del subtipo A
PP2 = B.assign(producto=B['id_producto'].map(lambda e: e if e in ('7790000000028', '7790000000035')
                                             else PROD_DE.get(e, e)))
PP2 = (PP2.groupby(['id_comercio', 'id_bandera', 'id_sucursal', 'mes', 'tipo', 'sub', 'rol', 'producto'])['p100']
       .median().reset_index())
PP2 = PP2.assign(suc_key=PP2['id_comercio'] + '|' + PP2['id_bandera'] + '|' + PP2['id_sucursal']).rename(
    columns={'sub': 'subtipo', 'p100': 'precio_100'})
_r2 = g['_tpd_serie'](PP2[['suc_key', 'mes', 'tipo', 'subtipo', 'rol', 'producto', 'precio_100']], list(PESOS),
                      {k: v / sum(PESOS.values()) for k, v in PESOS.items()})
_aj2 = _r2['ajuste'].set_index('subtipo')
_t2 = _r2['tipos'].set_index(['tipo', 'mes'])
chk('TPD: un subtipo con productos que no se pueden comparar entre sí queda afuera (no inventa el nivel)',
    not bool(_aj2.loc['B', 'rango_completo']) and _aj2.loc['B', 'meses_no_estimables'] == 3
    and 'B' not in set(_r2['subtipos']['subtipo']) and (_t2.loc['Fideos secos', 'subtipos'] == 1).all()
    and np.allclose(_t2.loc['Fideos secos', 'brecha_tpd'].to_numpy(),
                    [100 * np.expm1(_niv[('Fideos secos', 'A', m)]) for m in MESES_PP], rtol=1e-9))
chk('TPD: canasta y su IC (covarianza entre subtipos y tipos agrupada por sucursal) = cálculo denso; hojas y gráficos',
    _ok_can and {'Serie_TPD', 'Brecha_tipo_TPD', 'TPD_subtipos', 'TPD_anual', 'TPD_productos'} <= set(
        pd.ExcelFile(out / 'brecha_celiaca_2026-03.xlsx').sheet_names)
    and set(g['brecha_tipo_tpd']['universo']) == {'panel balanceado', 'todas las sucursales'}
    and (out / 'brecha_tpd_032026.png').exists() and (out / 'brecha_tpd_tipos_032026.png').exists())
chk('segunda corrida: meses cerrados desde el caché', g2['_faltan'] == [] and
    len(list((out / '_cache' / f'brecha_v3_{g["_cache_key"]}').glob('*.parquet'))) == 2)
chk('segunda corrida: mismos datos', g2['datos_dia'].reset_index(drop=True).equals(g['datos_dia'].reset_index(drop=True)))
x = pd.ExcelFile(out / 'brecha_celiaca_2026-03.xlsx')
faltan_h = {'Leeme', 'Canasta', 'Ponderaciones', 'Brecha_subtipo', 'Brecha_subtipo_anual', 'Brecha_tipo', 'Serie_canasta', 'Serie_canasta_balanceada',
            'Canasta_anual', 'Brecha_provincia', 'Brecha_region', 'Brecha_region_anual', 'Brecha_empresa',
            'Brecha_cadena', 'Brecha_sucursal', 'Comparacion_productos', 'Detalle_producto', 'Control_EAN',
            'Plausibilidad', 'Brecha_tipo_mes_balanceado', 'Cobertura_mensual'} - set(x.sheet_names)
chk(f'hojas del Excel (faltan {sorted(faltan_h)})', not faltan_h)
chk('mapa por sucursal', (out / 'mapa_sucursales_brecha_032026.html').exists())

print()
if errores:
    print(f'FALLARON {len(errores)}: {errores}')
    sys.exit(1)
print('test_brecha_celiaca: OK')
