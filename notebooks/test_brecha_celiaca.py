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
    lejos del Obelisco (AMBA / Pampeana).
Corre dos veces: la segunda tiene que leer los meses cerrados del caché.

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
PRODUCTO = {'Fideo sin TACC X': ['7790000000042', '7790000000110']}
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
             VENTANA_GEO_MESES=12)
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
