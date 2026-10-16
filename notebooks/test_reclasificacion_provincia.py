# -*- coding: utf-8 -*-
"""Test de la provincia por coordenadas de la CELDA 7 del nb02 (BUG-44).

Corre el bloque REAL de la CELDA 7 del notebook generado (`02_evolucion_canasta_representativa.ipynb`: provincia por
coordenadas con los poligonos de ar.json, filtro de CABA y AMBA), con `suc_pais`, `asignar_cadena` y `PROV_NORM` de la
CELDA 4, sobre un maestro sintetico y un ar.json sintetico (cuadrados con los ids de simplemaps; Buenos Aires con un
agujero donde esta CABA, como un poligono real que no la cubre).

Hasta el 2026-10-16 la CELDA 7 usaba rectangulos y la primera provincia que contenia el punto: pasaba Neuquen capital a
La Pampa, Parana a Santa Fe y San Nicolas a Entre Rios. Comprueba que:
  1. una sucursal de borde (Neuquen capital, a ~4 km dentro del poligono de Rio Negro) se queda en su provincia;
  2. un error grosero (DIA de Jujuy declarado San Juan, a ~600 km) pasa a la provincia que contiene el punto;
  3. el umbral es RECLASIF_TOL_KM: a ~78 km del borde se queda, a ~121 km se reclasifica;
  4. dentro de su poligono, sin poligono para su provincia o fuera de todos los poligonos: no cambia;
  5. el agujero de Buenos Aires (CABA) cuenta como fuera de Buenos Aires, pero a pocos km: se queda en Buenos Aires;
  6. una sucursal reclasificada a Buenos Aires en el conurbano queda en el AMBA (el AMBA se calcula despues);
  7. CABA declarada con coordenadas fuera del rectangulo de CABA se sigue descartando;
  8. sin ar.json no se reclasifica nada y se avisa;
  9. la linea impresa resume las reclasificaciones.

    python notebooks/test_reclasificacion_provincia.py     -> RESULTADO: OK / FALLA
"""
import contextlib, io, json, pathlib, tempfile

import numpy as np
import pandas as pd

NB = pathlib.Path(__file__).with_name('02_evolucion_canasta_representativa.ipynb')
CELDAS = [''.join(c['source']) for c in json.load(open(NB, encoding='utf-8'))['cells'] if c['cell_type'] == 'code']


def celda(tag):
    return next(c for c in CELDAS if tag in c[:300])


def bloque(src, ini, fin):
    i0 = src.index(ini)
    return src[i0:src.index(fin, i0)]


C4, C7 = celda('# CELDA 4 —'), celda('# CELDA 7 —')
fallas = []


def chequear(ok, msg):
    print(('  OK    ' if ok else '  FALLA ') + msg)
    if not ok:
        fallas.append(msg)


def cuadrado(lon0, lon1, lat0, lat1):
    return [[lon0, lat0], [lon1, lat0], [lon1, lat1], [lon0, lat1], [lon0, lat0]]


CABA_R = cuadrado(-58.53, -58.34, -34.71, -34.53)
GEO = {'type': 'FeatureCollection', 'features': [
    {'type': 'Feature', 'properties': {'id': i, 'name': n}, 'geometry': {'type': 'Polygon', 'coordinates': c}}
    for i, n, c in [
        ('ARQ', 'Neuquén', [cuadrado(-71.0, -68.1, -41.0, -36.0)]),
        ('ARR', 'Río Negro', [cuadrado(-68.1, -63.0, -42.0, -37.5)]),
        ('ARY', 'Jujuy', [cuadrado(-66.0, -64.0, -25.0, -22.0)]),
        ('ARJ', 'San Juan', [cuadrado(-70.0, -67.0, -32.0, -29.0)]),
        ('ARB', 'Buenos Aires', [cuadrado(-63.0, -56.5, -41.0, -33.5), CABA_R[::-1]]),    # agujero = CABA
        ('ARC', 'Ciudad de Buenos Aires', [CABA_R])]]}

# (id_sucursal, provincia del maestro, lat, lon, provincia esperada o None si se descarta, amba esperado, caso)
CASOS = [
    ('1', 'Provincia del Neuquén', -38.95, -68.06, 'Neuquén', False, 'borde: Neuquen capital a ~4 km en Rio Negro'),
    ('2', 'Provincia de San Juan', -24.20, -65.30, 'Jujuy', False, 'error grosero: Jujuy declarado San Juan'),
    ('3', 'Provincia del Neuquén', -38.95, -67.20, 'Neuquén', False, 'a ~78 km del borde: se queda'),
    ('4', 'Provincia del Neuquén', -38.95, -66.70, 'Río Negro', False, 'a ~121 km del borde: se reclasifica'),
    ('5', 'Provincia de Río Negro', -40.80, -63.50, 'Río Negro', False, 'dentro de su poligono'),
    ('6', 'Provincia de Mendoza', -24.20, -65.30, 'Mendoza', False, 'provincia sin poligono: no cambia'),
    ('7', 'Provincia de San Juan', -45.00, -55.50, 'San Juan', False, 'fuera de todos los poligonos: no cambia'),
    ('8', 'Provincia de Buenos Aires', -34.60, -58.42, 'Buenos Aires', True, 'en el agujero (CABA), a pocos km de BA'),
    ('9', 'Provincia de San Juan', -34.70, -58.58, 'Buenos Aires', True, 'reclasificada al conurbano: AMBA'),
    ('10', 'Ciudad Autónoma de Buenos Aires', -34.80, -58.40, None, None, 'CABA fuera del rectangulo: se descarta'),
    ('11', 'Ciudad Autónoma de Buenos Aires', -34.60, -58.42, 'CABA', True, 'CABA dentro de CABA')]


def correr(geojson_path):
    maestro = pd.DataFrame([{'id_comercio': '15', 'id_bandera': '1', 'id_sucursal': s, 'PROVINCIA': p,
                             'sucursales_nombre': c, 'sucursales_barrio': None, 'sucursales_localidad': 'X',
                             'sucursales_latitud': la, 'sucursales_longitud': lo, 'sucursales_tipo': 'Supermercado'}
                            for s, p, la, lo, _, _, c in CASOS])
    env = {'np': np, 'pd': pd, 'maestro_suc': maestro, 'GEOJSON_PATH': geojson_path}
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        exec(bloque(C4, 'suc_pais = maestro_suc[', 'NOMBRES_COMPUESTOS = {'), env)
        exec(bloque(C4, 'NOMBRES_COMPUESTOS = {', 'PESOS_POBLACION = {'), env)
        exec(bloque(C7, '# ── Provincia por coordenadas', '# ── Calcular canasta por sucursal'), env)
    return env, out.getvalue()


tmp = pathlib.Path(tempfile.mkdtemp(prefix='test_reclasif_'))
ruta = tmp / 'ar.json'
ruta.write_text(json.dumps(GEO, ensure_ascii=False), encoding='utf-8')

print('1. con ar.json')
env, out = correr(ruta)
sg = env['suc_geo_clean'].set_index('id_sucursal')
chequear(env['RECLASIF_TOL_KM'] == 100, f'RECLASIF_TOL_KM = {env["RECLASIF_TOL_KM"]}')
for s, _, _, _, prov, amba, caso in CASOS:
    if prov is None:
        chequear(s not in sg.index, f'[{s}] {caso}')
    else:
        obt = (sg.loc[s, 'PROVINCIA_NORM'], bool(sg.loc[s, 'amba'])) if s in sg.index else None
        chequear(obt == (prov, amba), f'[{s}] {caso}: {obt} (esperado {(prov, amba)})')
linea = next((l for l in out.splitlines() if 'Reclasificadas' in l), '')
chequear('Reclasificadas 3 sucursales' in linea and 'San Juan -> Jujuy (1)' in linea
         and 'San Juan -> Buenos Aires (1)' in linea and 'Neuquén -> Río Negro (1)' in linea,
         f'resumen impreso: {linea.strip()}')
d = env['_km_al_poligono'](env['_POL_PROV']['Neuquén'], np.array([-68.06, -67.2]), np.array([-38.95, -38.95]))
chequear(abs(d[0] - 0.04 * 111.32 * np.cos(np.radians(38.95))) < 0.05 and abs(d[1] - 0.9 * 111.32 * np.cos(np.radians(38.95))) < 0.05,
         f'distancia al borde en km ({d[0]:.2f} y {d[1]:.2f})')

print('2. sin ar.json')
env2, out2 = correr(tmp / 'no_existe.json')
sg2 = env2['suc_geo_clean'].set_index('id_sucursal')
decl = {s: env2['PROV_NORM'][p] for s, p, *_ in CASOS}
chequear(all(sg2.loc[s, 'PROVINCIA_NORM'] == decl[s] for s in sg2.index) and 'AVISO' in out2
         and 'Reclasificadas' not in out2, 'no reclasifica nada y avisa')
chequear(bool(sg2.loc['8', 'amba']) and not bool(sg2.loc['9', 'amba']),
         'el AMBA se calcula igual (sin reclasificar, la de San Juan en el conurbano no es AMBA)')

print('\nRESULTADO:', 'OK' if not fallas else f'FALLA ({len(fallas)})')
raise SystemExit(1 if fallas else 0)
