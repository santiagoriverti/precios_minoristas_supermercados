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
    ('15', '1', '304'): ('Ciudad Autónoma de Buenos Aires', -34.63, -58.41, 'Supermercado', 1.00),  # online: afuera
    ('23', '1', '401'): ('Ciudad Autónoma de Buenos Aires', -34.58, -58.43, 'Autoservicio', 1.00),  # Axion: afuera
}
NOMBRE = {('15', '1', '304'): 'eCommerce'}   # tienda online que el maestro carga como Supermercado (BUG-48)
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
    '7790000000134': ('Fideos secos', 'sin', 500, 950, (1, 2, 3)),           # ADICIONAL (sensibilidad, CELDA 8c)
}
ADIC = {'7790000000134': {'tipo': 'Fideos secos', 'lado': 'sin_tacc', 'subtipo': 'A', 'gramos': 500, 'desde': None,
                          'hasta': None, 'linea_todos': 'Adicional 134', 'motivo': 'composición espejada',
                          'descripcion': 'Producto 134'}}
FALTA = {(('15', '1', '301'), '7790000000059'), (('9', '1', '102'), '7790000000103')}
PESOS = {'Fideos secos': 1.503, 'Galletitas dulces': 1.717}
DIAS = pd.date_range('2026-01-01', '2026-03-31')

def precio(s, e, d):
    tipo, lado, g, base, meses = P[e]
    infl = 1.05 ** (d.month - 1)
    salto = 2.5 if (e == '7790000000103' and d.month == 3) else 1.0
    if e == '7790000000028' and d.month == 2:      # código viejo con precio congelado después del cambio
        salto = 0.3
    if e == '7790000000097' and s[0] == '15' and d.month == 2:   # toda una cadena (DIA) al triple: precio fuera de escala
        salto = 3.0
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
pd.DataFrame({'date': pd.to_datetime(['2025-12-01', '2026-01-01', '2026-02-01', '2026-03-01']),
              'Nivel general': [100.0, 102.0, 105.0, 107.0], 'Alimentos y bebidas no alcohólicas': [100.0, 103.0, 104.0,
                                                                                                   110.0]}).to_excel(
    sepa / 'IPC.xlsx', sheet_name='IPC', index=False)
feats = [{'type': 'Feature', 'properties': {'id': k, 'name': n},
          'geometry': {'type': 'Polygon', 'coordinates': [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]]}}
         for k, (n, x0, x1, y0, y1) in POLI.items()]
(sepa / 'ar.json').write_text(json.dumps({'type': 'FeatureCollection', 'features': feats}), encoding='utf-8')
ms = pd.DataFrame([{'id_comercio': c, 'id_bandera': b, 'id_sucursal': s,
                    'sucursales_nombre': NOMBRE.get((c, b, s), f'Suc {c}-{s}'),
                    'sucursales_tipo': t, 'sucursales_latitud': la, 'sucursales_longitud': lo,
                    'sucursales_localidad': 'Loc', 'PROVINCIA': pv}
                   for (c, b, s), (pv, la, lo, t, _n) in SUCS.items()])
ms.to_excel(tmp / 'data' / 'maestro_sucursales_completo.xlsx', index=False)
# caché de Georef del nb09: departamento de cada sucursal (la estación de servicio 401 no entra en el HHI)
DEPTO = {('9', '1', '101'): '02001', ('9', '1', '102'): '02001', ('10', '1', '201'): '02001', ('23', '1', '401'): '02001',
         ('10', '1', '202'): '06357', ('15', '1', '301'): '14014', ('15', '1', '302'): '14014', ('15', '1', '303'): '02001',
         ('15', '1', '304'): '02001'}
(sepa / 'output_trazabilidad' / '_cache_nb09').mkdir(parents=True)
pd.DataFrame([{'suc': f'{c}|{b}|{s}', 'departamento_id': d, 'departamento': f'Depto {d}', 'municipio': 'M',
               'provincia_georef': 'P'} for (c, b, s), d in DEPTO.items()]).to_parquet(
    sepa / 'output_trazabilidad' / '_cache_nb09' / 'georef_sucursales.parquet', index=False)
mp = pd.DataFrame([{'producto_sepa_id': e, 'producto_descripcion': f'Producto {e[-3:]} {g} Gr', 'producto_marca': 'M',
                    'rubro': 'Almacén', 'producto_cantidad_presentacion': str(g), 'producto_unidad_medida_presentac': 'gr'}
                   for e, (t, l, g, b, m) in P.items()])
mp.to_excel(tmp / 'data' / 'Maestro de Productos Interno.xlsx', index=False)

TIPOS = {t: {'peso': PESOS[t],
             'tacc': {e: f'Producto {e[-3:]}' for e, v in P.items() if v[0] == t and v[1] == 'tacc' and e not in ADIC},
             'sin_tacc': {e: f'Producto {e[-3:]}' for e, v in P.items() if v[0] == t and v[1] == 'sin' and e not in ADIC}}
         for t in PESOS}
GRAMOS = {e: v[2] for e, v in P.items() if v[0] in PESOS and e not in ADIC}
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
# marcas (hoja Prima_misma_marca): la misma marca vende los dos lados en el subtipo A (el sin TACC con otro nombre, MX,
# que MARCA_EQUIVALENTE une con M1) y en el C
MARCA = {'7790000000011': 'M1', '7790000000042': 'MX', '7790000000110': 'MX', '7790000000028': 'M2', '7790000000035': 'M2',
         '7790000000059': 'M3', '7790000000066': 'M4', '7790000000097': 'M4', '7790000000073': 'M5', '7790000000080': 'M5',
         '7790000000103': 'M6', '7790000000134': 'M1'}

# ── Correr las celdas reales (dos veces) ─────────────────────────────────────────
cells = [''.join(c['source']) for c in json.load(open(NB, encoding='utf-8'))['cells'] if c['cell_type'] == 'code']
os.chdir(tmp)

def correr():
    g = {}
    exec(cells[0], g)
    g.update(SEPA_DIR=str(sepa), OUTPUT_DIR=str(out), TIPOS=TIPOS, GRAMOS=GRAMOS, VIGENCIA=VIGENCIA,
             PRODUCTO=PRODUCTO, SUBTIPO=SUBTIPO, MES_INICIO_HISTORICO='2026-01', MIN_SUC_AGG=1, MIN_SUC_SUBTIPO=1,
             VENTANA_GEO_MESES=12, USAR_GEOREF=False, MIN_SUC_DEPTO=1,
             ADICIONALES=ADIC, LINEA_TODOS={}, SUSTITUTOS={'7790000000097'}, PRODUCTO_SIN_LINEA=PRODUCTO,
             BOOT_B=30, RADIO_COMPETENCIA_KM=5, MESES_CBA=2,
             CBA_ITEMS=[('Fideos', 'Fideos secos', None, 1740), ('Galletitas dulces', 'Galletitas dulces', None, 210)],
             MARCA=MARCA, MARCA_EQUIVALENTE={'MX': 'M1'})
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
M_ADIC = M[M['id_producto'].isin(ADIC)].copy()        # el producto adicional (sensibilidad), aparte
M = M[M['id_producto'].isin(GRAMOS)]
M = M[[(e, m) not in FUERA_VIG for e, m in zip(M['id_producto'], M['mes'])]]
# precios de una empresa fuera de escala (CELDA 7): la mediana de cada empresa para el código y mes contra la mediana
# entre empresas (sucursales del maestro, sin Axion ni el EAN de la plausibilidad); fuera de x2,5 se descarta
EMPR = {'9': 'Cencosud', '10': 'Carrefour', '15': 'DIA'}
_mf = M[~M['id_comercio'].eq('23') & ~M['id_producto'].eq('7790000000080')]
_mf = _mf.assign(emp=_mf['id_comercio'].map(EMPR), p100=_mf['precio'] / _mf['id_producto'].map(GRAMOS) * 100)
_ce = _mf.groupby(['id_producto', 'mes', 'emp'])['p100'].median()
_ce = _ce / _ce.groupby(level=['id_producto', 'mes']).transform('median')
ATIP = set(_ce[(_ce > 2.5) | (_ce < 1 / 2.5)].index)
M = M[[(e, m, EMPR.get(c)) not in ATIP for e, m, c in zip(M['id_producto'], M['mes'], M['id_comercio'])]]
dd = g['datos_dia'][['id_comercio', 'id_bandera', 'id_sucursal', 'ean_norm', 'mes', 'precio', 'dias']]
cmp = M.merge(dd, left_on=['id_comercio', 'id_bandera', 'id_sucursal', 'id_producto', 'mes'],
              right_on=['id_comercio', 'id_bandera', 'id_sucursal', 'ean_norm', 'mes'], how='left', suffixes=('', '_nb'))
cmp = cmp[~cmp['id_comercio'].isin(['23']) & ~((cmp['id_comercio'] == '15') & cmp['id_sucursal'].isin(['303', '304']))
          & ~cmp['id_producto'].eq('7790000000080')]
chk('mediana mensual exacta por sucursal x EAN (todas las partes, centavos en marzo)',
    cmp['precio_nb'].notna().all() and np.allclose(cmp['precio'], cmp['precio_nb'], rtol=1e-9))
chk('días con precio: enero 31 (no suma el archivo parcial de los días 1-5)',
    (cmp.loc[cmp['mes'] == '2026-01', 'dias_nb'] == 31).all())
chk('enero usa el archivo COMPLETOb', any('COMPLETOb' in n for _z, n in g['_mapa_mes']['2026-01'])
    and len(g['_mapa_mes']['2026-01']) == 2)
chk('Axion (23), la sucursal web y la tienda online por el nombre ("eCommerce" con tipo Supermercado) fuera',
    not g['bt_sm']['id_comercio'].eq('23').any() and not g['bt_sm']['id_sucursal'].isin(['303', '304']).any()
    and not g['suc_geo']['id_sucursal'].isin(['303', '304']).any())
chk('plausibilidad saca el EAN x10', set(g['plausibilidad']['ean_norm']) == {'7790000000080'})
chk('precio de una empresa fuera de escala: DIA al triple en febrero (un código) afuera, solo esas observaciones',
    ATIP == {('7790000000097', '2026-02', 'DIA')} and len(g['precios_atipicos']) == 1
    and g['precios_atipicos'].iloc[0][['ean_norm', 'mes', 'empresa']].tolist() == ['7790000000097', '2026-02', 'DIA']
    and not ((g['datos_dia']['ean_norm'] == '7790000000097') & (g['datos_dia']['mes'] == '2026-02')
             & (g['datos_dia']['id_comercio'] == '15')).any())
# precio congelado de una empresa: Cencosud repite el precio de E1 los 10 meses mientras el resto sube 10% por mes (el
# índice del tipo y lado, la mediana de las variaciones, también): afuera los meses con el índice arriba de 50% (del 6.º,
# 1,1^5 = 1,61, al 10.º); DIA repite el de E4 solo 5 meses (menos de MESES_CONGELADO): queda
_mc = [f'2025-{m_:02d}' for m_ in range(1, 11)]
_fz = pd.DataFrame([{'id_comercio': c_, 'ean_norm': e_, 'tipo': 'T', 'rol': 'sin', 'mes': m_,
                     'precio_100': b_ * (1.1 ** (t_ if s_ else 0) if e_ != 'E4' else 1.1 ** max(0, t_ - 4))}
                    for c_, e_, b_, s_ in (('9', 'E1', 100, False), ('10', 'E1', 100, True), ('15', 'E2', 50, True),
                                           ('10', 'E3', 80, True), ('15', 'E4', 70, True))
                    for t_, m_ in enumerate(_mc)])
_rz, _fuera_z, _ = g['_congelados_empresa'](_fz)
_ez = g['asignar_empresa']('9')
chk('precio congelado: la racha de 10 meses con el índice arriba de 50% sale desde el 6.º mes; la de 5 meses queda',
    len(_rz) == 1 and _rz.iloc[0][['empresa', 'ean_norm', 'desde', 'hasta', 'meses_iguales', 'primer_mes_descartado',
                                   'meses_descartados']].tolist() == [_ez, 'E1', '2025-01', '2025-10', 10, '2025-06', 5]
    and _fuera_z == {f'{_ez}|E1|{m_}' for m_ in _mc[5:]}
    and len(g['_sin_congelados'](_fz, _fuera_z)[0]) == len(_fz) - 5 and 'Precios_congelados' in pd.ExcelFile(
        out / 'brecha_celiaca_2026-03.xlsx').sheet_names and len(g['precios_congelados']) == 0)
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
B = B[~B['id_comercio'].eq('23') & ~B['id_sucursal'].isin(['303', '304']) & ~B['id_producto'].eq('7790000000080')]
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
chk('canasta comparable por sucursal (falta el subtipo B en la 301, el D en la 102 y, en febrero, el C en la 301 por el '
    'precio fuera de escala: brecha nacional del mes)',
    all(abs(bsm.loc[k, 'brecha_comparable'] - v[0]) < 1e-9 and abs(bsm.loc[k, 'peso_propio_pct'] - v[1]) < 1e-9
        for k, v in fb.items())
    and abs(bsm.loc[('15|1|301', '2026-01'), 'peso_propio_pct'] - 100 * (1 - W['Fideos secos'] / 2)) < 1e-9
    and abs(bsm.loc[('15|1|301', '2026-02'), 'peso_propio_pct']
            - 100 * (1 - W['Fideos secos'] / 2 - W['Galletitas dulces'] / 2)) < 1e-9)

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

# (a2) el panel mueve el subtipo-mes sin pares con el MISMO subtipo de todas las sucursales (si ahí tiene dato propio),
#      no con los demás subtipos: con primas distintas por subtipo, moverlo con los demás erraría y con el mismo es
#      exacto. En el "panel" (sucursales 0-14) B no tiene sin TACC en los meses 3 y 4; en todas (0-29) sí.
rng2 = np.random.default_rng(11)
BETA2 = {'A': [0, .05, .12, .2, .15, .3, .35, .25, .4, .5], 'B': [0, .3, -.1, .5, .6, .2, .1, .4, .0, .2]}
TR2 = {'A': (['a1', 'a2'], ['a3', 'a4']), 'B': (['b1', 'b2'], ['b3', 'b4'])}
_rows2 = []
for s in range(30):
    for t, mes in enumerate(MS):
        alfa = rng2.normal(0, .2)
        for sub, (con, sin) in TR2.items():
            alfa_sub = alfa + rng2.normal(0, .1)
            for p in con + sin:
                if sub == 'B' and p in sin and s < 15 and t in (3, 4):
                    continue
                if rng2.random() > 0.7 and not (s in (0, 15) and p in sin):
                    continue
                _rows2.append({'suc_key': f's{s}', 'mes': mes, 'tipo': 'T1', 'subtipo': sub,
                               'rol': 'sin' if p in sin else 'tacc', 'producto': p,
                               'precio_100': float(np.exp(alfa_sub + GAM[p] + BETA2[sub][t] * (p in sin)))})
_df2 = pd.DataFrame(_rows2)
_r_todas = g['_tpd_serie'](_df2, ['T1'], {'T1': 1.0}, 1)
_pan = _df2[_df2['suc_key'].str.slice(1).astype(int) < 15]
_r_pan = g['_tpd_serie'](_pan, ['T1'], {'T1': 1.0}, 1, _r_todas['niveles'])
_r_pan0 = g['_tpd_serie'](_pan, ['T1'], {'T1': 1.0}, 1)               # sin referencia: con los demás subtipos
def _serie_b(_r):
    return np.log1p(_r['subtipos'].set_index(['subtipo', 'mes']).loc['B', 'brecha_tpd'].to_numpy() / 100)
_lb, _lb0 = _serie_b(_r_pan), _serie_b(_r_pan0)
_esp = _lb[0] + np.array(BETA2['B']) - BETA2['B'][0]                 # nivel propio del panel + prima de cada mes
_mc = _r_pan['subtipos'].set_index(['subtipo', 'mes'])['movido_con']
chk('TPD: en el panel, el subtipo-mes sin pares se mueve con el mismo subtipo de todas las sucursales (exacto con primas '
    'distintas por subtipo; con los demás subtipos no lo sería)',
    np.allclose(_lb, _esp, atol=1e-9) and not np.allclose(_lb0, _esp, atol=1e-3)
    and list(_mc.loc['B']) == ['mismo subtipo en todas las sucursales' if t in (3, 4) else '' for t in range(10)]
    and not _r_todas['subtipos']['movido_con_los_demas'].any())

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
# agrupados por empresa: los puntajes de las sucursales de cada empresa (comercio) se suman; CR1 con 3 empresas
_COM_PP = sorted({s_.split('|')[0] for s_ in SUCS_PP})
A_PP = np.array([[float(s_.split('|')[0] == c_) for s_ in SUCS_PP] for c_ in _COM_PP])
Q_E = len(_COM_PP) / (len(_COM_PP) - 1)
_ok_tipo, _ok_emp, _lam = True, True, {}
for tipo in PESOS:
    subs_t = sorted({k[1] for k in _niv if k[0] == tipo})
    for mes in MESES_PP:
        lam = np.mean([_niv[(tipo, s_, mes)] for s_ in subs_t])
        z = sum(_gs[(tipo, s_, mes)] for s_ in subs_t) / len(subs_t)
        _lam[(tipo, mes)] = (lam, z)
        _ok_tipo &= (abs(bt_tpd.loc[(tipo, mes), 'brecha_tpd'] - 100 * np.expm1(lam)) < 1e-8
                     and abs(bt_tpd.loc[(tipo, mes), 'error_estandar_log'] - np.sqrt(Q_PP * float(z @ z))) < 1e-10)
        ze = A_PP @ z
        _ok_emp &= abs(bt_tpd.loc[(tipo, mes), 'error_estandar_log_empresa'] - np.sqrt(Q_E * float(ze @ ze))) < 1e-10
chk('TPD sobre el SEPA sintético: brecha por tipo y mes y su error estándar = mínimos cuadrados densos por subtipo',
    _ok_tipo and len(bt_tpd) == len(_lam))
chk('TPD: error estándar agrupado por empresa (3 empresas) = los puntajes de sus sucursales sumados a mano',
    _ok_emp and len(_COM_PP) == 3)
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

# ── CELDA 8c: análisis complementarios ──────────────────────────────────────────
def canasta_bf(ss, pesos=None):
    # brecha nacional del período: mediana de cada subtipo entre sucursal-meses, tipo = promedio geométrico (pesos
    # iguales o por sucursal-meses), canasta ENGHo
    m = ss.groupby(['tipo', 'sub'])['brecha'].agg(['median', 'size'])
    t = {}
    for tp, x in m.groupby(level='tipo'):
        wts = x['size'].to_numpy(float) if pesos == 'disp' else np.ones(len(x))
        t[tp] = np.expm1(np.average(np.log1p(x['median'] / 100), weights=wts))
    return 100 * (sum(W[k] * (1 + v) for k, v in t.items()) / sum(W[k] for k in t) - 1)

def ss_desde(bb, modo='mediana'):
    p = bb.groupby(_kb + ['prod'])['p100'].median()
    if modo == 'minimo':
        mm = p.groupby(level=_kb).transform('median')
        p = p[(p >= mm / 4) & (p <= mm * 4)]
        s = p.groupby(level=_kb).min()
    else:
        s = p.groupby(level=_kb).median()
    s = s.unstack('rol').dropna()
    s['brecha'] = (s['sin'] / s['tacc'] - 1) * 100
    return s.reset_index()

sens = g['sensibilidad'].set_index('escenario')['brecha_canasta']
E8 = g['ESCENARIOS_SENSIBILIDAD']
_nom = {v_.get('agregar', '') + str(v_.get('quitar_sustitutos', '')) + v_.get('estimador', '') + v_.get('pesos_subtipo', '')
        + v_.get('pesos_sucursal', ''): k_ for k_, v_ in E8.items()}
# adicional: el producto 134 en el lado sin TACC del subtipo A (escenario "todos")
Ba = M_ADIC.merge(pd.DataFrame([('7790000000134', 'Fideos secos', 'sin', 500)], columns=['id_producto', 'tipo', 'rol', 'g']),
                  on='id_producto')
Ba = Ba[~Ba['id_comercio'].eq('23') & ~Ba['id_sucursal'].isin(['303', '304'])]
Ba = Ba.assign(p100=Ba['precio'] / Ba['g'] * 100, prod='Adicional 134', sub='A')
chk('sensibilidad: el escenario principal = la brecha nacional de la CELDA 8 = fuerza bruta',
    abs(sens.iloc[0] - canasta_bf(SS.assign(sub=SS['sub']))) < 1e-9
    and abs(sens.iloc[0] - g['_canasta_nac'](g['bt_v'])[0]) < 1e-9)
chk('sensibilidad: todos los productos (con el ADICIONAL), sin sustitutos, el más barato, el cociente nacional y pesos '
    'por disponibilidad = fuerza bruta',
    abs(sens[_nom['todos']] - canasta_bf(ss_desde(pd.concat([B, Ba], ignore_index=True)))) < 1e-9
    and abs(sens[_nom['True']] - canasta_bf(ss_desde(B[~B['id_producto'].eq('7790000000097')]))) < 1e-9
    and abs(sens[_nom['minimo']] - canasta_bf(ss_desde(B, 'minimo'))) < 1e-9
    and abs(sens[_nom['disponibilidad']] - canasta_bf(SS, 'disp')) < 1e-9
    and abs(sens[_nom['nacional']] - canasta_bf(
        B.groupby(_kb + ['prod'])['p100'].median().groupby(level=_kb).median()
        .groupby(level=['tipo', 'sub', 'rol']).median().unstack('rol').dropna()
        .assign(brecha=lambda d: (d['sin'] / d['tacc'] - 1) * 100).reset_index())) < 1e-9)

# escenario por población: mediana ponderada (cada provincia pesa por su población, repartida entre sus sucursal-meses
# del subtipo y mes); la mediana ponderada por fuerza bruta = el valor que minimiza la suma de |v - m| ponderada (el
# punto medio si los que la minimizan son un intervalo)
def wmed_bf(v, w):
    v, w = np.asarray(v, float), np.asarray(w, float)
    f = np.array([np.sum(w * np.abs(v - m)) for m in v])
    mins = v[np.abs(f - f.min()) <= 1e-9 * max(1.0, f.min())]
    return (mins.min() + mins.max()) / 2
POB = g['PESOS_POBLACION']
_pv = g['suc_geo'].drop_duplicates(['id_comercio', 'id_bandera', 'id_sucursal']).set_index(
    ['id_comercio', 'id_bandera', 'id_sucursal'])['PROVINCIA_NORM']
SSp = SS.assign(prov=[_pv[(a, b, c)] for a, b, c in zip(SS['id_comercio'], SS['id_bandera'], SS['id_sucursal'])])
SSp['w'] = SSp['prov'].map(POB) / SSp.groupby(['tipo', 'sub', 'mes', 'prov'])['brecha'].transform('size')
_tp = {}
for (tp, sb), x in SSp.groupby(['tipo', 'sub']):
    _tp.setdefault(tp, []).append(np.log1p(wmed_bf(x['brecha'], x['w']) / 100))
_esp_pob = 100 * (sum(W[k] * np.exp(np.mean(v)) for k, v in _tp.items()) / sum(W[k] for k in _tp) - 1)
chk('sensibilidad: sucursales ponderadas por la población de su provincia = mediana ponderada por fuerza bruta',
    set(SSp['prov']) == {'CABA', 'Buenos Aires', 'Córdoba'} and abs(sens[_nom['poblacion']] - _esp_pob) < 1e-9
    and abs(g['_wmediana']([1, 2, 3, 4], [1, 1, 1, 1]) - 2.5) < 1e-12 and g['_wmediana']([1, 2, 3], [1, 1, 5]) == 3)

# índices de cada lado: por subtipo y lado, mínimos cuadrados densos de ln p con una indicadora por ítem (producto en la
# sucursal) y por mes (sin la del primero); tipo = promedio de sus subtipos (en logs), canasta = pesos ENGHo; IPC rebasado
PM = B.groupby(['id_comercio', 'id_bandera', 'id_sucursal', 'mes', 'tipo', 'sub', 'rol', 'prod'])['p100'].median().reset_index()
MS_ = sorted(PM['mes'].unique())
tau = {}
for (tp, sb, rl), x in PM.groupby(['tipo', 'sub', 'rol']):
    it = (x['id_comercio'] + x['id_sucursal'] + x['prod']).to_numpy()
    items = sorted(set(it))
    X = np.zeros((len(x), len(items) + len(MS_) - 1))
    for r_, (i_, m_) in enumerate(zip(it, x['mes'])):
        X[r_, items.index(i_)] = 1
        if m_ != MS_[0]:
            X[r_, len(items) + MS_.index(m_) - 1] = 1
    cf = np.linalg.lstsq(X, np.log(x['p100'].to_numpy()), rcond=None)[0]
    tau[(tp, sb, rl)] = np.r_[0.0, cf[len(items):]]
ti = {(tp, rl, k): 100 * np.exp(np.mean([tau[(tp, sb, rl)][k] for (t2, sb, r2) in tau if t2 == tp and r2 == rl]))
      for (tp, sb, rl) in tau for k in range(len(MS_))}
il = g['indices_lados']
ilc = il[il['nivel'] == 'Canasta'].set_index('mes')
ok_i = abs(ilc.loc['2026-01', 'indice_con_tacc'] - 100) < 1e-9
for i, mes in ((1, '2026-02'), (2, '2026-03')):
    for rol, col in (('tacc', 'indice_con_tacc'), ('sin', 'indice_sin_tacc')):
        esp = sum(W[t] * ti[(t, rol, i)] for t in PESOS) / W.sum()
        ok_i &= abs(ilc.loc[mes, col] - esp) < 1e-8
chk('índices de cada lado (efectos fijos de ítem y mes) = mínimos cuadrados densos; IPC del INDEC rebasado',
    ok_i and abs(ilc.loc['2026-01', 'ipc_alimentos'] - 100) < 1e-9
    and abs(ilc.loc['2026-03', 'ipc_alimentos'] - 100 * 110 / 103) < 1e-9
    and abs(ilc.loc['2026-02', 'sin_sobre_con'] - 100 * ilc.loc['2026-02', 'indice_sin_tacc'] / ilc.loc['2026-02', 'indice_con_tacc']) < 1e-9)

# disponibilidad: de las sucursal-meses con el tipo con TACC, las que tienen también el sin TACC
lad0 = B.groupby(['id_comercio', 'id_bandera', 'id_sucursal', 'mes', 'tipo'])['rol'].agg(set)
lad0 = lad0[lad0.map(lambda s: 'tacc' in s)].map(lambda s: 'sin' in s)
lad = lad0.groupby(level='tipo').mean()
lads = lad0.groupby(level=['id_comercio', 'id_bandera', 'id_sucursal', 'tipo']).max().groupby(level='tipo').mean()
dpi = g['disponibilidad'].set_index(['agrupacion', 'grupo', 'medida'])
dp, dps = dpi.loc[('País', 'País', 'sucursal-meses')], dpi.loc[('País', 'País', 'sucursales (alguna vez)')]
chk('disponibilidad del país por tipo y ponderada (sucursal-meses y sucursales) = fuerza bruta',
    all(abs(dp[f'disponibilidad_{t}_pct'] - 100 * lad[t]) < 1e-9 for t in PESOS)
    and all(abs(dps[f'disponibilidad_{t}_pct'] - 100 * lads[t]) < 1e-9 for t in PESOS)
    and abs(dp['disponibilidad_ponderada_pct'] - 100 * sum(W[t] * lad[t] for t in PESOS) / W.sum()) < 1e-9)

# intervalos de confianza: réplicas con semilla fija (las dos corridas iguales) y el país adentro de su intervalo
icg, icg2 = g['ic_grupos'], g2['ic_grupos']
ip = icg.set_index(['agrupacion', 'grupo']).loc[('País', 'País')]
chk('IC por bootstrap: 30 réplicas, el país adentro de su IC y las dos corridas iguales (semilla fija)',
    ip['replicas'] == 30 and ip['ic95_inf'] <= ip['brecha_canasta'] <= ip['ic95_sup']
    and icg.equals(icg2) and {'Región', 'Empresa', 'Cadena', 'Provincia'} <= set(icg['agrupacion']))
# bootstrap por empresa: se sortean las 3 empresas con reposición (semilla BOOT_SEED + 1), cada una con todas sus
# sucursal-meses, y en cada réplica la brecha del país por fuerza bruta; sin IC por empresa con una sola empresa
_bv = g['bt_v'][['suc_key', 'mes', 'tipo', 'subtipo', 'brecha_pct', 'empresa']].reset_index(drop=True)
_ue = _bv['empresa'].unique()
_rgb = np.random.default_rng(g['BOOT_SEED'] + 1)
_nbs = []
for _b in range(30):
    _dr = _rgb.integers(0, len(_ue), len(_ue))
    _xb = pd.concat([_bv[_bv['empresa'] == _ue[_j]] for _j in _dr], ignore_index=True)
    _nbs.append(canasta_bf(_xb.rename(columns={'subtipo': 'sub', 'brecha_pct': 'brecha'})))
_nbs = pd.Series(_nbs)
_ie = icg.set_index(['agrupacion', 'grupo'])
chk('IC por empresa: el del país = bootstrap de empresas por fuerza bruta; sin IC por empresa con una sola empresa',
    len(_ue) == 3 and ip['n_empresas'] == 3 and ip['replicas_empresa'] == 30
    and abs(ip['ic95_inf_empresa'] - _nbs.quantile(.025)) < 1e-9 and abs(ip['ic95_sup_empresa'] - _nbs.quantile(.975)) < 1e-9
    and icg.loc[icg['agrupacion'].isin(['Empresa', 'Cadena', 'Provincia']), 'ic95_inf_empresa'].isna().all()
    and (_ie.loc[[('Región', 'AMBA'), ('Región', 'Pampeana')], 'n_empresas'] == 2).all()
    and _ie.loc[[('Región', 'AMBA'), ('Región', 'Pampeana')], 'ic95_inf_empresa'].notna().all())
# el bootstrap rápido (medianas ponderadas por las veces que sale cada fila) = el directo (la tabla de cada réplica
# armada y la CELDA 8), réplica por réplica, por sucursal y por empresa, en el país y en todos los grupos
_gi = g['_GRUPOS_IC']
_ok_bs = True
for _col, _sd, _gr in (('suc_key', g['BOOT_SEED'], _gi),
                       ('empresa', g['BOOT_SEED'] + 1, [_x for _x in _gi if _x[0] in ('Región', 'Provincia')])):
    _f = g['_bootstrap'](_col, _sd, _gr, 0)
    _dd = g['_bootstrap_directo'](_col, _sd, _gr, 30)
    _mb = _f.merge(_dd, on=['agrupacion', 'grupo', 'replica'], how='outer', indicator=True)
    _ok_bs &= (len(_f) > 30 and (_mb['_merge'] == 'both').all()
               and np.allclose(_mb['brecha_x'], _mb['brecha_y'], rtol=0, atol=1e-9)
               and np.allclose(_mb['nacional_x'], _mb['nacional_y'], rtol=0, atol=1e-9))
chk('bootstrap rápido = directo en las 30 réplicas (por sucursal y por empresa; país y grupos)', _ok_bs)

# competencia local: sucursales y empresas a <= 5 km (haversine), con la misma sucursal
cl = g['competencia_local'].set_index('suc_key')
sg2 = g['suc_geo'][~g['suc_geo']['id_comercio'].isin(g['CADENAS_FILTRAR'])].set_index('suc_key')
def km(a, b):
    la1, lo1, la2, lo2 = map(np.radians, (a[0], a[1], b[0], b[1]))
    h = np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371 * np.arcsin(np.sqrt(h))
ok_c = True
for k, r in sg2.iterrows():
    cerca = [k2 for k2, r2 in sg2.iterrows()
             if km((r['sucursales_latitud'], r['sucursales_longitud']), (r2['sucursales_latitud'], r2['sucursales_longitud'])) <= 5]
    emps = sg2.loc[cerca, 'empresa'].value_counts()
    ok_c &= (cl.loc[k, 'sucursales_en_radio'] == len(cerca) and cl.loc[k, 'empresas_en_radio'] == len(emps)
             and abs(cl.loc[k, 'hhi_local'] - ((emps / len(cerca)) ** 2).sum()) < 1e-12)
chk('competencia local: sucursales, empresas y HHI a <= 5 km = fuerza bruta', ok_c and len(cl) == len(sg2))

# hedónica de grupos: sin ruido recupera exacto los efectos de región, empresa y HHI puestos a mano
rng3 = np.random.default_rng(5)
SUCH = [(f's{i}', ['R1', 'R1', 'R2', 'R3'][i % 4], ['Carrefour', 'E2', 'E3'][i % 3], f'd{i % 20}') for i in range(60)]
HHI = {f'd{j}': 0.2 + 0.03 * j for j in range(20)}
BR, BE, LAM = {'R1': 0, 'R2': .10, 'R3': -.05}, {'Carrefour': 0, 'E2': .20, 'E3': .05}, .03
GAMH = {p: rng3.normal(0, .3) + (0.7 if p.endswith(('3', '4')) else 0) for p in ('a1', 'a2', 'a3', 'a4', 'b1', 'b2', 'b3', 'b4')}
filas_h = []
for s, rg, em, dp_ in SUCH:
    for mes in ('2026-01', '2026-02'):
        for sub, prods in (('A', ('a1', 'a2', 'a3', 'a4')), ('B', ('b1', 'b2', 'b3', 'b4'))):
            alfa = rng3.normal(0, .2)
            for p in prods:
                sin = p.endswith(('3', '4'))
                for lam, lista in ((0.0, 'h0'), (LAM, 'h1')):
                    lp = alfa + GAMH[p] + sin * (BR[rg] + BE[em] + lam * (HHI[dp_] - 0.485) * 10)
                    filas_h.append({'lista': lista, 'suc_key': s, 'mes': mes, 'subtipo': sub, 'rol': 'sin' if sin else 'tacc',
                                    'producto': p, 'precio_100': float(np.exp(lp)), 'w': 1.0, 'region': rg, 'empresa': em,
                                    'departamento_id': dp_, 'hhi_departamento': HHI[dp_],
                                    'empresas_rivales_en_radio': int(rng3.integers(0, 5))})
PH = pd.DataFrame(filas_h)
h0 = g['_hedonica_grupos'](PH[PH['lista'] == 'h0'].drop(columns='lista'))[0].set_index(['modelo', 'termino'])
h1 = g['_hedonica_grupos'](PH[PH['lista'] == 'h1'].drop(columns='lista'))[0].set_index(['modelo', 'termino'])
m0, m1 = 'región y empresa', 'región, empresa y HHI del departamento'
chk('hedónica de grupos: sin ruido recupera exactos los efectos de región y empresa (y el del HHI en su modelo)',
    all(abs(h0.loc[(m0, r_), 'coef_log'] - v_) < 1e-9 for r_, v_ in (('R2', .10), ('R3', -.05), ('E2', .20), ('E3', .05)))
    and all(abs(h1.loc[(m1, r_), 'coef_log'] - v_) < 1e-9 for r_, v_ in (('R2', .10), ('R3', -.05), ('E2', .20), ('E3', .05)))
    and abs(h1.loc[(m1, 'HHI del departamento (+0,1)'), 'coef_log'] - LAM) < 1e-9
    and abs(h0.loc[(m1, 'HHI del departamento (+0,1)'), 'coef_log']) < 1e-9
    and (h0['error_estandar_log'] < 1e-6).all() and (h0['departamentos'] == 20).all()
    and (h0['empresas'] == 3).all() and h0.loc[h0['grupo'] == 'Empresa', 'error_estandar_log_empresa'].isna().all())

# hedónica con el surtido de cada grupo (sin efectos de producto, con una prima base por subtipo): si a las sucursales de
# la región R2 les falta el producto a4 (sin TACC), con los efectos de producto sigue exacta y sin ellos da los mínimos
# cuadrados ponderados de la brecha de cada celda (promedio de log sin TACC - promedio de log con TACC) sobre subtipo,
# región y empresa, con el peso de la celda W_sin W_con / (W_sin + W_con); efecto_surtido_pct = la diferencia
PH2 = PH[(PH['lista'] == 'h0') & ~((PH['region'] == 'R2') & (PH['producto'] == 'a4'))].drop(columns='lista')
h2 = g['_hedonica_grupos'](PH2)[0].set_index(['modelo', 'termino'])
_cel = []
for (s_, m_, sb_), x in PH2.groupby(['suc_key', 'mes', 'subtipo']):
    _si, _ly = (x['rol'] == 'sin').to_numpy(), np.log(x['precio_100'].to_numpy())
    ws_, wt_ = x['w'].to_numpy()[_si].sum(), x['w'].to_numpy()[~_si].sum()
    _gap = np.average(_ly[_si], weights=x['w'].to_numpy()[_si]) - np.average(_ly[~_si], weights=x['w'].to_numpy()[~_si])
    _cel.append((_gap, ws_ * wt_ / (ws_ + wt_), sb_, x['region'].iloc[0], x['empresa'].iloc[0]))
_cel = pd.DataFrame(_cel, columns=['gap', 'k', 'subtipo', 'region', 'empresa'])
Z = np.column_stack([(_cel['subtipo'] == s_).to_numpy(float) for s_ in ('A', 'B')]
                    + [(_cel['region'] == r_).to_numpy(float) for r_ in ('R2', 'R3')]
                    + [(_cel['empresa'] == e_).to_numpy(float) for e_ in ('E2', 'E3')])
sk_ = np.sqrt(_cel['k'].to_numpy())
bz = np.linalg.lstsq(Z * sk_[:, None], _cel['gap'].to_numpy() * sk_, rcond=None)[0][2:]
MS2 = g['_MOD_SURTIDO']
chk('hedónica con el surtido de cada grupo (sin efectos de producto) = mínimos cuadrados de la brecha de cada celda; '
    'con los efectos de producto sigue exacta; efecto_surtido_pct = la diferencia',
    abs(h2.loc[(m0, 'R2'), 'coef_log'] - .10) < 1e-9 and abs(h2.loc[(m0, 'E2'), 'coef_log'] - .20) < 1e-9
    and all(abs(h2.loc[(MS2, t_), 'coef_log'] - b_) < 1e-9 for t_, b_ in zip(('R2', 'R3', 'E2', 'E3'), bz))
    and abs(bz[0] - .10) > 1e-3 and abs(h0.loc[(MS2, 'R2'), 'coef_log'] - .10) < 1e-9
    and abs(h2.loc[(m0, 'R2'), 'efecto_surtido_pct'] - 100 * np.expm1(bz[0] - .10)) < 1e-6
    and abs(h2.loc[(m0, 'R2'), 'efecto_con_surtido_pct'] - 100 * np.expm1(bz[0])) < 1e-6)

# errores agrupados por empresa: con ruido, el de cada efecto de región = la covarianza agrupada (CR1) escrita a mano,
# con mínimos cuadrados densos (indicadoras de celda y de producto; pesos 1)
rng4 = np.random.default_rng(9)
PH3 = PH[PH['lista'] == 'h0'].drop(columns='lista').reset_index(drop=True)
PH3['precio_100'] = PH3['precio_100'] * np.exp(rng4.normal(0, .05, len(PH3)))
h3 = g['_hedonica_grupos'](PH3)[0].set_index(['modelo', 'termino'])
_c3 = PH3['suc_key'] + PH3['mes'] + PH3['subtipo']
_pr3 = sorted(PH3['producto'].unique())
X3 = np.column_stack([(_c3 == c_).to_numpy(float) for c_ in sorted(_c3.unique())]
                     + [(PH3['producto'] == p_).to_numpy(float) for p_ in _pr3 if p_ not in ('a1', 'b1')]
                     + [((PH3['rol'] == 'sin') & (PH3['region'] == r_)).to_numpy(float) for r_ in ('R2', 'R3')]
                     + [((PH3['rol'] == 'sin') & (PH3['empresa'] == e_)).to_numpy(float) for e_ in ('E2', 'E3')])
y3 = np.log(PH3['precio_100'].to_numpy())
br3 = np.linalg.inv(X3.T @ X3)
b3 = br3 @ X3.T @ y3
u3 = y3 - X3 @ b3
_em3 = PH3['empresa'].to_numpy()
S3 = np.array([(X3[_em3 == e_] * u3[_em3 == e_, None]).sum(axis=0) for e_ in sorted(set(_em3))])
V3 = 3 / 2 * br3 @ S3.T @ S3 @ br3
_k3 = X3.shape[1] - 4
chk('hedónica: errores agrupados por empresa (CR1) de los efectos de región = cálculo denso a mano',
    all(abs(h3.loc[(m0, r_), 'error_estandar_log_empresa'] - np.sqrt(V3[_k3 + i_, _k3 + i_])) < 1e-9
        for i_, r_ in enumerate(('R2', 'R3')))
    and all(abs(h3.loc[(m0, r_), 'coef_log'] - b3[_k3 + i_]) < 1e-9 for i_, r_ in enumerate(('R2', 'R3'))))

# costo con la CBA: mediana de cada lado de los subtipos del ítem en los últimos 2 meses, promedio geométrico
cb = g['costo_cba'].set_index('item_cba')
u2 = bt_sub_ = g['bt_sub'][g['bt_sub']['mes'].isin(['2026-02', '2026-03'])]
ok_k = True
for it, tp, gr in (('Fideos', 'Fideos secos', 1740), ('Galletitas dulces', 'Galletitas dulces', 210)):
    s_ = u2[u2['tipo'] == tp].groupby('subtipo')[['tacc', 'sin']].median()
    pc, ps = np.exp(np.log(s_['tacc']).mean()), np.exp(np.log(s_['sin']).mean())
    ok_k &= abs(cb.loc[it, 'costo_extra_ae'] - (ps - pc) * gr / 100) < 1e-6 and abs(
        cb.loc[it, 'costo_extra_hogar_tipo'] - 3.09 * (ps - pc) * gr / 100) < 1e-6
chk('costo con la CBA por adulto equivalente y hogar tipo = fuerza bruta (y la fila Total)',
    ok_k and abs(cb.loc['Total', 'costo_extra_ae'] - cb.drop(index='Total')['costo_extra_ae'].sum()) < 1e-6
    and len(g['costo_cba_mensual']) == 3)
# prima de la misma marca. (a) Sobre el SEPA sintético: en el subtipo A todo es de la marca M1 (el sin TACC, MX, unido
# por MARCA_EQUIVALENTE) y en el C de la M4: la misma marca es la canasta, celda por celda; en B y D no hay pares
pmm = g['prima_misma_marca']
pmv = pmm[pmm['periodo'].str.startswith('últimos')].set_index(['subtipo', 'marca'])
ssA = SS[SS['sub'] == 'A']
chk('prima de la misma marca sobre el SEPA sintético: pares en A (M1 con MX unida) y C, celdas y brechas = la canasta',
    set(pmv.index) == {('A', 'M1'), ('C', 'M4')} and pmv.loc[('A', 'M1'), 'celdas'] == len(ssA)
    and abs(pmv.loc[('A', 'M1'), 'brecha_misma_marca_pct'] - ssA['brecha'].median()) < 1e-9
    and abs(pmv.loc[('A', 'M1'), 'prima_de_marca_pct']) < 1e-9
    and abs(pmv.loc[('A', 'M1'), 'brecha_subtipo_pct'] - ssA['brecha'].median()) < 1e-9
    and set(pmm['periodo']) == {'2026', 'últimos 3 meses (2026-01 → 2026-03)'})
# (b) a mano: dos productos por lado de marcas distintas; la marca A vende los dos lados en 7 de las 8 celdas
_fm = []
for s_, e_, f_ in (('s1', 'E1', 1.0), ('s2', 'E1', 1.1), ('s3', 'E2', 0.9), ('s4', 'E2', 1.2)):
    for m_, fm_ in (('2026-01', 1.0), ('2026-02', 1.05)):
        for p_, rol_, mar_, base_ in (('P1', 'tacc', 'A', 100), ('P2', 'tacc', 'B', 80), ('Q1', 'sin', 'A', 250),
                                      ('Q2', 'sin', 'C', 300)):
            if not (s_ == 's4' and m_ == '2026-02' and p_ == 'P1'):
                _fm.append({'suc_key': s_, 'empresa': e_, 'mes': m_, 'tipo': 'T', 'subtipo': 'S', 'rol': rol_,
                            'producto': p_, 'marca': mar_, 'precio_100': base_ * f_ * fm_})
_fm = pd.DataFrame(_fm)
_bts = (_fm.groupby(['suc_key', 'mes', 'tipo', 'subtipo', 'rol'])['precio_100'].median().unstack('rol')
        .assign(brecha_pct=lambda d: (d['sin'] / d['tacc'] - 1) * 100).reset_index())
_pm2 = g['_prima_marca'](_fm, _bts, ['2026-01', '2026-02'], 'x').set_index('periodo')
_b_can, _b_mm = (275 / 90 - 1) * 100, 150.0
chk('prima de la misma marca a mano: 7 celdas, misma marca +150%, canasta en esas celdas +205,6% y prima de marca '
    '(1 + canasta) / (1 + misma marca) - 1',
    _pm2.loc['2026', 'celdas'] == 7 and _pm2.loc['2026', 'empresas'] == 2
    and abs(_pm2.loc['2026', 'brecha_misma_marca_pct'] - _b_mm) < 1e-9
    and abs(_pm2.loc['2026', 'brecha_canasta_mismas_celdas_pct'] - _b_can) < 1e-9
    and abs(_pm2.loc['2026', 'prima_de_marca_pct'] - 100 * ((1 + _b_can / 100) / (1 + _b_mm / 100) - 1)) < 1e-9
    and abs(_pm2.loc['2026', 'brecha_subtipo_pct'] - _b_can) < 1e-9
    and _pm2.loc['2026', 'productos_con_tacc'] == 'P1' and _pm2.loc['2026', 'productos_sin_tacc'] == 'Q1')

# composición por empresa (celdas de bt_sub por año), varianza entre sucursales (R² de la empresa = suma de cuadrados
# entre empresas / total) y surtido (de las celdas de la empresa en el subtipo, % con el producto)
_bs = g['bt_sub']
_ce = g['composicion_empresas']
_ce = _ce[(_ce['universo'] == 'todas las sucursales') & (_ce['periodo'] == '2026')].set_index('empresa')
_n_e = _bs.groupby('empresa').size()
_vA = (g['bt_v'][g['bt_v']['subtipo'] == 'A'].assign(l=lambda d: np.log1p(d['brecha_pct'] / 100))
       .groupby(['suc_key', 'empresa'])['l'].mean().reset_index())
_sst = ((_vA['l'] - _vA['l'].mean()) ** 2).sum()
_ssb = (_vA.groupby('empresa')['l'].transform('mean') - _vA['l'].mean()).pow(2).sum()
_va = g['varianza_empresa'].set_index('subtipo')
_se_ = g['surtido_empresa']
_dd8 = g['datos_dia'].assign(suc_key=lambda d: d['id_comercio'] + '|' + d['id_bandera'] + '|' + d['id_sucursal'])
_cA = _bs[(_bs['subtipo'] == 'A') & (_bs['id_comercio'] == '9')][['suc_key', 'mes']]
_conA = _cA.merge(_dd8[_dd8['producto'] == '7790000000011'][['suc_key', 'mes']].drop_duplicates(), on=['suc_key', 'mes'])
_sA = _se_[(_se_['producto'] == '7790000000011') & (_se_['empresa'] == _bs.loc[_bs['id_comercio'] == '9', 'empresa'].iloc[0])]
chk('composición por empresa, R² de la empresa y surtido = fuerza bruta',
    all(_ce.loc[e_, 'celdas'] == n_ for e_, n_ in _n_e.items()) and abs(_ce['pct_celdas'].sum() - 100) < 1e-9
    and abs(_va.loc['A', 'r2_empresa'] - _ssb / _sst) < 1e-9 and _va.loc['A', 'sucursales'] == len(_vA)
    and len(_sA) == 1 and abs(_sA['pct_celdas'].iloc[0] - 100 * len(_conA) / len(_cA)) < 1e-9)

# hedónica por año: con los 3 meses del SEPA sintético en un solo año, la de 2026 = la de la ventana
_hg = g['hedonica_grupos']
_ha = g['hedonica_grupos_anual']
_hm = _hg[_hg['modelo'] == m0].set_index('termino')['coef_log']
_ham = _ha[(_ha['modelo'] == m0) & (_ha['anio'] == '2026')].set_index('termino')['coef_log']
chk('hedónica por año: 2026 = la ventana (los mismos meses), con las mismas bases',
    len(_hm) > 0 and set(_hm.index) == set(_ham.index) and np.allclose(_hm.sort_index(), _ham.sort_index(), atol=1e-12)
    and set(_ha['modelo']) == {m0, MS2})

xs = set(pd.ExcelFile(out / 'brecha_celiaca_2026-03.xlsx').sheet_names)
_pr8 = pd.read_csv(out / 'datos' / 'productos.csv', dtype={'ean': str})
_dic8 = pd.read_csv(out / 'datos' / 'diccionario_datos.csv').fillna('')
_p18 = pd.read_parquet(out / 'datos' / 'panel_sucursal_mes_subtipo.parquet')
chk('CELDA 8c: hojas, gráficos y datos para el análisis propio (productos, diccionario sin columnas sin describir, '
    'LEEME con la brecha del país)',
    {'Sensibilidad', 'Indices_lados', 'Indices_lados_anual', 'Disponibilidad', 'Disponibilidad_mensual', 'IC_grupos',
     'Hedonica_grupos', 'Hedonica_grupos_anual', 'Concentracion_modelos', 'Competencia_local', 'Composicion_empresas',
     'Varianza_empresa', 'Surtido_empresa', 'Prima_misma_marca', 'Costo_CBA', 'Costo_CBA_mensual'} <= xs
    and all((out / f'{n}_032026.png').exists() for n in ('indices_lados', 'disponibilidad_region', 'ic_grupos', 'sensibilidad',
                                                         'prima_misma_marca', 'composicion_empresas'))
    and all((out / 'datos' / f).exists() for f in ('panel_sucursal_mes_subtipo.parquet', 'panel_sucursal_mes_subtipo.csv.gz',
                                                   'panel_producto_sucursal_mes.parquet',
                                                   'panel_producto_sucursal_mes_adicionales.parquet', 'sucursales.csv',
                                                   'productos.csv', 'diccionario_datos.csv', 'LEEME.md'))
    and len(_p18) == len(g['bt_sub']) and _p18['en_panel_balanceado'].sum() == len(g['bt_bal'])
    and abs(_p18.drop_duplicates('tipo')['peso_tipo_canasta'].sum() - 1) < 1e-12
    and set(_pr8['ean']) == set(GRAMOS) | set(ADIC) and (_pr8['en_canasta'] == _pr8['ean'].isin(GRAMOS)).all()
    and (_dic8['descripcion'] != '').all()
    and f"{g['ic_grupos'].iloc[0]['brecha_canasta']:+.2f}%" in (out / 'datos' / 'LEEME.md').read_text(encoding='utf-8'))

# hoja Resumen: cada número es el de su hoja (la brecha del país con su IC, el último mes del panel y la calidad de datos)
rs = pd.read_excel(out / 'brecha_celiaca_2026-03.xlsx', sheet_name='Resumen')
icp = g['ic_grupos'][g['ic_grupos']['agrupacion'] == 'País'].iloc[0]
sb_ = g['serie_mensual_bal'].sort_values('mes').iloc[-1]
fila = lambda tema, txt: rs[(rs['tema'] == tema) & rs['indicador'].str.contains(txt, regex=False)]
chk('hoja Resumen = los números de cada hoja (país con IC, último mes del panel, atípicos, tipos)',
    pd.ExcelFile(out / 'brecha_celiaca_2026-03.xlsx').sheet_names[:2] == ['Leeme', 'Resumen']
    and abs(fila('Nivel', 'todas las sucursales')['valor'].iloc[0] - round(icp['brecha_canasta'], 1)) < 1e-9
    and abs(fila('Nivel', 'todas las sucursales')['ic95_inf'].iloc[0] - round(icp['ic95_inf'], 1)) < 1e-9
    and abs(fila('Nivel', 'descriptiva')['valor'].iloc[0] - round(sb_['brecha_canasta'], 1)) < 1e-9
    and fila('Calidad de datos', 'fuera de escala')['valor'].iloc[0] == len(g['precios_atipicos'])
    and len(rs[rs['tema'] == 'Por tipo (todo el período)']) == len(g['brecha_tipo']))

# nb06b (canasta amplia): las celdas 2 a 13 son las del nb06 y la CELDA 1 arma la canasta de 10 tipos con sus pesos,
# los gramos y el subtipo de cada código, otra ventana, otra carpeta y otro nombre de Excel
c6 = json.load(open(NB, encoding='utf-8'))['cells']
c6b = json.load(open(REPO / 'notebooks' / '06b_brecha_celiaca_canasta_amplia.ipynb', encoding='utf-8'))['cells']
g6b = {}
exec(''.join(c6b[1]['source']), g6b)
e6b = {e for t_ in g6b['TIPOS'].values() for l_ in ('tacc', 'sin_tacc') for e in t_[l_]}
chk('nb06b: celdas 2-13 = las del nb06; CELDA 1 con 10 tipos, pesos ENGHo, gramos y subtipo de cada código',
    len(c6b) == len(c6) and all(a_['source'] == b_['source'] for a_, b_ in zip(c6[2:], c6b[2:]))
    and len(g6b['TIPOS']) == 10 and all(t_['peso'] > 0 for t_ in g6b['TIPOS'].values())
    and all(len(t_['tacc']) and len(t_['sin_tacc']) for t_ in g6b['TIPOS'].values())
    and e6b <= set(g6b['GRAMOS']) and all(g6b['GRAMOS'][e] > 0 for e in e6b)
    and e6b <= {e for es in g6b['SUBTIPO'].values() for e in es}
    and not (e6b & set(g6b['ADICIONALES'])) and g6b['MES_INICIO_HISTORICO'] == '2025-08'
    and g6b['OUTPUT_DIR'].endswith('output_brecha_amplia') and g6b['PREFIJO_EXCEL'] == 'brecha_celiaca_amplia'
    and g6b['CBA_ITEMS'][3][2] == 'Pan de molde y de mesa')

print()
if errores:
    print(f'FALLARON {len(errores)}: {errores}')
    sys.exit(1)
print('test_brecha_celiaca: OK')
