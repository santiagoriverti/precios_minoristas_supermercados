# -*- coding: utf-8 -*-
"""Test de la CELDA 19b del nb02: desagregacion de la variacion mensual de la canasta.

Corre las celdas REALES del notebook generado (`02_evolucion_canasta_representativa.ipynb`): la
CELDA 5 (lectura de ZIPs), la CELDA 9 (serie oficial), los nombres de la CELDA 3, `suc_pais`,
`asignar_cadena` y `PROV_NORM` de la CELDA 4, `_pmean` de la CELDA 6, la geografia de la CELDA 7
(`suc_geo_clean` con la columna `amba`, de donde sale la region), el formato de la CELDA 19 y la CELDA 19b entera, sobre dos
ZIPs semestrales sinteticos: jun-26 completo en 2026A.zip y jul-26 al 15 en 2026B.zip (el mes
anterior esta en otro semestre, como cada julio). No hay `datos` en el entorno: la celda no lo usa.

El sintetico trae los casos que muerden: una suba a mitad de junio (arrastre), un producto que
desaparece en julio, pares sucursal-producto sin el otro mes, un par fuera de la banda [1/4, 4],
un par sucursal-producto sin la ultima semana de junio, un rubro fuera del mapa de grupos, un EAN que llega
con ceros a la izquierda, una bandera de Carrefour fuera del diccionario, sucursales fuera del
maestro, regiones con espacio duro (como el maestro real) y una cadena de CADENAS_FILTRAR (entra:
el universo es el de la CELDA 9). Region por coordenadas (BUG-43): una sucursal que el maestro marca AMBA
en Mar del Plata (va a Pampeana), una del maestro sin coordenadas (Buenos Aires s/ubicar), una con un
codigo de provincia desconocido (Sin dato) y una de Neuquen capital (la que los rectangulos viejos de la CELDA 7
pasaban a La Pampa, BUG-44): su region tiene que ser Patagonia. Se desagregan dos canastas (Media y Popular) a la vez.

Comprueba que:
  1. la variacion oficial es la de la CELDA 9 y la de un calculo independiente, y la celda
     reproduce las medianas oficiales de todos los productos;
  2. los aportes por producto suman la variacion oficial; arrastre_pp + nuevo_pp = aporte, producto
     a producto, y el arrastre coincide con el calculo independiente;
  3. la variacion del panel apareado coincide con un calculo independiente;
  4. cada corte (cadena, provincia, region, tipo) suma la variacion del panel grupo a grupo contra
     el calculo independiente, su columna reescalada suma la oficial y la fila TOTAL trae ambas;
     Grupos y Rubros suman la oficial, el arrastre y el panel;
  5. Aporte_prod_x_cadena y Subas_y_bajas suman el panel; Mes_parcial trae la oficial y el arrastre;
  6. las hojas se agregan al Excel existente sin borrar las demas y re-correr la celda las reemplaza;
  7. con los precios en centavos da exactamente lo mismo.

    python notebooks/test_desagregacion_variacion.py     -> RESULTADO: OK / FALLA
"""
import gc, gzip, hashlib, io, json, math, pathlib, re, shutil, statistics, tempfile, zipfile
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

NB = pathlib.Path(__file__).with_name('02_evolucion_canasta_representativa.ipynb')
CELDAS = [''.join(c['source']) for c in json.load(open(NB, encoding='utf-8'))['cells']
          if c['cell_type'] == 'code']


def celda(tag):
    return next(c for c in CELDAS if tag in c[:300])


def bloque(src, ini, fin):
    i0 = src.index(ini)
    return src[i0:src.index(fin, i0)]


C3, C4, C5 = celda('# CELDA 3 —'), celda('# CELDA 4 —'), celda('# CELDA 5 —')
C6, C9, C19, C19B = celda('# CELDA 6 —'), celda('# CELDA 9 —'), celda('# CELDA 19 —'), celda('# CELDA 19b —')
C7 = celda('# CELDA 7 —')

fallas = []


def chequear(ok, msg):
    print(('  OK    ' if ok else '  FALLA ') + msg)
    if not ok:
        fallas.append(msg)


def cerca(a, b, tol=1e-9):
    return abs(float(a) - float(b)) <= tol


# ── Datos sinteticos ──────────────────────────────────────────────────────────
ANT, ACT, N_ANT, D_ACT = 202606, 202607, 30, 15
# (comercio, bandera, sucursal, provincia ISO, (REGION, sucursales_tipo) del maestro o None, (lat, lon) o None)
# La region sale de las coordenadas (CELDA 7), no de la REGION del maestro: 12-1-2 figura AMBA en el maestro pero
# esta en Mar del Plata (Pampeana, BUG-43); 20-1-1 esta en el maestro sin coordenadas (Buenos Aires s/ubicar).
SUCS = [('9', '1', '1', 'AR-C', ('AMBA', 'Supermercado'), (-34.60, -58.42)),
        ('9', '1', '2', 'AR-B', ('AMBA\xa0', 'SUPERMERCADO'), (-34.70, -58.58)),      # La Matanza
        ('9', '1', '3', 'AR-X', ('Pampeana', 'Hipermercado'), (-31.42, -64.18)),
        ('15', '1', '1', 'AR-C', ('AMBA', 'Autoservicio'), (-34.61, -58.44)),
        ('15', '1', '2', 'AR-X', ('Pampeana', 'autoservicio'), (-31.40, -64.20)),
        ('15', '1', '3', 'AR-M', ('Cuyo\xa0', 'Autoservicio'), (-32.89, -68.84)),
        ('12', '1', '1', 'AR-C', ('AMBA', 'Hipermercado'), (-34.58, -58.43)),
        ('12', '1', '2', 'AR-B', ('AMBA', 'Tienda Fisica'), (-38.00, -57.55)),       # Mar del Plata
        ('10', '4', '1', 'AR-S', None, None),
        ('99', '1', '1', 'AR-B', None, None),
        ('19', '1', '1', 'AR-T', ('Noroeste', 'Supermercado'), (-26.83, -65.22)),
        ('20', '1', '1', 'AR-B', ('AMBA', 'Supermercado'), None),                    # maestro sin coordenadas
        ('21', '1', '9', 'AR-ZZ', None, None),                                       # provincia ISO desconocida
        ('2', '1', '5', 'AR-Q', ('Patagonia', 'Supermercado'), (-38.95, -68.06))]    # Neuquen capital
CADENA_ESP = {('9', '1'): 'Vea', ('15', '1'): 'DIA', ('12', '1'): 'Coto',
              ('10', '4'): 'Carrefour (bandera 4)', ('99', '1'): 'Cadena 99', ('19', '1'): 'Cadena 19',
              ('20', '1'): 'LAR', ('21', '1'): 'Toledo', ('2', '1'): 'La Anonima'}
PROV_ESP = {'AR-C': 'CABA', 'AR-B': 'Buenos Aires', 'AR-X': 'Córdoba', 'AR-M': 'Mendoza',
            'AR-S': 'Santa Fe', 'AR-T': 'Tucumán', 'AR-ZZ': 'Sin dato', 'AR-Q': 'Neuquén'}
PROV_LARGA = {'AR-C': 'Ciudad Autónoma de Buenos Aires', 'AR-B': 'Provincia de Buenos Aires',
              'AR-X': 'Provincia de Córdoba', 'AR-M': 'Provincia de Mendoza', 'AR-T': 'Provincia de Tucumán',
              'AR-Q': 'Provincia del Neuquén'}
# Region esperada fuera del AMBA: la de la provincia del ARCHIVO (ISO), no la de la CELDA 7 (hasta el BUG-44 sus
# rectangulos pasaban Neuquen capital a La Pampa)
REGION_PROV = {'CABA': 'AMBA', 'Buenos Aires': 'Pampeana', 'Córdoba': 'Pampeana', 'Mendoza': 'Cuyo',
               'Tucumán': 'Noroeste', 'Neuquén': 'Patagonia'}
REGION_FUERA = {'AR-S': 'Pampeana', 'AR-B': 'Buenos Aires s/ubicar', 'AR-ZZ': 'Sin dato'}


def km_obelisco(lat, lon):
    la0, lo0, la, lo = map(math.radians, (-34.6037, -58.3816, lat, lon))
    a = math.sin((la - la0) / 2) ** 2 + math.cos(la0) * math.cos(la) * math.sin((lo - lo0) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(a))


def region_esp(s):
    # En el maestro con coordenadas: AMBA = CABA o Buenos Aires a <= 90 km del Obelisco; si no, por provincia
    if s[4] and s[5]:
        prov = PROV_ESP[s[3]]
        if prov == 'CABA' or (prov == 'Buenos Aires' and km_obelisco(*s[5]) <= 90):
            return 'AMBA'
        return REGION_PROV[prov]
    return REGION_FUERA[s[3]]
TIPO_ESP = {'Supermercado': 'Supermercado', 'SUPERMERCADO': 'Supermercado', 'Hipermercado': 'Hipermercado',
            'Autoservicio': 'Autoservicio', 'autoservicio': 'Autoservicio', 'Tienda Fisica': 'Tienda física'}

E_LECHE, E_GASEOSA, E_LAVANDINA, E_SHAMPOO = '7790001000011', '7790001000028', '7790001000035', '7790001000042'
E_GALLE, E_PERRO, E_YERBA, E_ARROZ = '40084107', '7790001000059', '7790001000066', '7790001000073'
E_RUIDO = '7790009999999'
CAN = {'cantidad_03': [(E_LECHE, 'Leche Entera 1 Lt', 3, 'Lácteos'),
                       (E_GASEOSA, 'Gaseosa Cola 2,25 Lt', 2, 'Gaseosas'),
                       (E_LAVANDINA, 'Lavandina 1 Lt', 1, 'Lavandina'),
                       (E_SHAMPOO, 'Shampoo 400 Ml', 1, 'Cuidado del Cabello'),
                       (E_GALLE, 'Galletitas de Agua 300 Gr', 4, 'Galletitas'),
                       (E_PERRO, 'Alimento para Perros 1,5 Kg', 1, 'Mascotas'),
                       (E_YERBA, 'Yerba Mate 1 Kg', 2, 'Infusiones')],
       'cantidad_02': [(E_LECHE, 'Leche Entera 1 Lt', 2, 'Lácteos'),
                       (E_ARROZ, 'Arroz Largo Fino 1 Kg', 2, 'Arroz y Legumbres')]}


def sk(s):
    return f'{s[0]}-{s[1]}-{s[2]}'


def generar():
    # Observaciones (indice de sucursal, ean, fecha AAAAMMDD, precio en pesos con 2 decimales)
    rng = np.random.default_rng(7)
    eans = sorted({e for ps in CAN.values() for e, *_ in ps} | {E_RUIDO})
    base = {e: float(rng.integers(500, 5000)) for e in eans}
    obs = []
    for si, s in enumerate(SUCS):
        f = rng.uniform(0.85, 1.25)
        for e in eans:
            if rng.random() < 0.12 and e != E_GALLE:
                continue                                        # la sucursal no vende el producto
            p0 = round(base[e] * f, 2)
            k = int(rng.integers(8, 29))
            p1 = round(p0 * (1 + rng.choice([0, 0, 0.05, 0.10, -0.03])), 2)     # cambio a mitad de junio
            p2 = round(p1 * (1 + rng.choice([0, 0, 0.04, -0.02, 0.08])), 2)     # julio
            sin_ant = (sk(s), e) == ('10-4-1', E_LAVANDINA)
            sin_act = e == E_YERBA or (sk(s), e) == ('99-1-1', E_SHAMPOO)
            hasta = 10 if (sk(s), e) == ('15-1-3', E_GALLE) else N_ANT       # sin la ultima semana de junio
            if (sk(s), e) == ('12-1-2', E_GASEOSA):
                p2 = round(p1 * 10, 2)                                        # fuera de la banda [1/4, 4]
            for d in range(1, hasta + 1):
                if not sin_ant and rng.random() >= 0.05:
                    obs.append((si, e, ANT * 100 + d, p0 if d <= k else p1))
            for d in range(1, D_ACT + 1):
                if not sin_act and rng.random() >= 0.05:
                    obs.append((si, e, ACT * 100 + d, p2))
    return obs


OBS = generar()
PARTES = {('2026A.zip', '062026_pais_parte1COMPLETO.csv.gz'): (ANT, range(1, 16)),
          ('2026A.zip', '062026_pais_parte2COMPLETO.csv.gz'): (ANT, range(16, 31)),
          ('2026B.zip', '072026_pais_parte1COMPLETO.csv.gz'): (ACT, range(1, 16))}


def escribir_zips(sepa_dir, centavos):
    serie = defaultdict(dict)
    for si, e, fe, p in OBS:
        serie[(si, e)][fe] = p
    fmt = (lambda p: str(int(round(p * 100)))) if centavos else (lambda p: ('%.2f' % p).rstrip('0').rstrip('.'))
    por_zip = defaultdict(dict)
    for (zn, fn), (ym, dias) in PARTES.items():
        fechas = [ym * 100 + d for d in dias]
        lineas = [','.join(['id_comercio', 'id_bandera', 'id_sucursal', 'sucursales_provincia', 'id_producto']
                           + [f'precio_{fe}' for fe in fechas])]
        for (si, e), ps in sorted(serie.items()):
            if not any(fe in ps for fe in fechas):
                continue
            s = SUCS[si]
            lineas.append(','.join([s[0], s[1], s[2], s[3], e.zfill(13)]
                                   + [fmt(ps[fe]) if fe in ps else 'NA' for fe in fechas]))
        por_zip[zn][fn] = gzip.compress(('\n'.join(lineas) + '\n').encode('utf-8'))
    for zn, arch in por_zip.items():
        with zipfile.ZipFile(sepa_dir / zn, 'w', zipfile.ZIP_STORED) as z:
            for fn, b in arch.items():
                z.writestr(fn, b)


def fila_maestro(s, region, tipo, coord):
    return {'id_comercio': s[0], 'id_bandera': s[1], 'id_sucursal': s[2], 'REGION': region,
            'sucursales_tipo': tipo, 'PROVINCIA': PROV_LARGA.get(s[3], 'Provincia de Mendoza'),
            'sucursales_nombre': f'Suc {s[0]}-{s[2]}', 'sucursales_barrio': None, 'sucursales_localidad': 'X',
            'sucursales_latitud': coord[0] if coord else np.nan,
            'sucursales_longitud': coord[1] if coord else np.nan}


MAESTRO = pd.DataFrame(
    [fila_maestro(s, s[4][0], s[4][1], s[5]) for s in SUCS if s[4]] +
    [fila_maestro(('9', '1', '1', 'AR-C'), 'Patagonia', 'Web', None),         # duplicado: gana el primero
     fila_maestro(('50', '1', '1', 'AR-M'), 'Cuyo', 'Supermercado', (-32.9, -68.8))])   # sin datos de precio


def correr(tmp, centavos):
    sepa, out, tdir = tmp / f'sepa_{centavos}', tmp / f'out_{centavos}', tmp / f'tmp_{centavos}'
    for d in (sepa, out, tdir):
        d.mkdir()
    escribir_zips(sepa, centavos)
    xls = out / 'canasta_analisis_2026-07.xlsx'
    with pd.ExcelWriter(xls, engine='openpyxl') as w:      # lo que dejo la CELDA 19
        pd.DataFrame({'mes': ['2026-06', '2026-07'], 'var_media_%': [1.0, 2.0]}).to_excel(
            w, sheet_name='Evolucion_IPC', index=False)
        pd.DataFrame({'x': [1]}).to_excel(w, sheet_name='Serie_precios', index=False)
    env = {'__builtins__': __builtins__, 'np': np, 'pd': pd, 're': re, 'zipfile': zipfile, 'gzip': gzip,
           'shutil': shutil, 'gc': gc, 'hashlib': hashlib, 'Path': Path,
           'SEPA_DIR': sepa, 'OUTPUT_DIR': out, 'CACHE_DIR': out, 'TMP_DIR': tdir, 'USE_CACHE': False,
           'MES_INICIO_HISTORICO': '2026-06', 'PERIODO': '2026-07', 'ULTIMO_MES': '2026-07',
           'maestro_suc': MAESTRO.copy(),
           'DESAGREGAR_CANASTAS': ['cantidad_03', 'cantidad_02', 'cantidad_06'],   # la 06 no esta activa
           'DETALLE_CANASTA': None}           # la hoja analisis_detallado tiene su propio test
    exec(bloque(C3, 'CANT_COLS =', '# ── Construir CANASTAS'), env)
    env['CANASTAS'] = {cid: {e: (d[:50], q, c) for e, d, q, c in ps} for cid, ps in CAN.items()}
    env['CANASTAS_ACTIVAS'] = list(CAN)
    env['CANASTA_EANS_NORM'] = set().union(*[set(c) for c in env['CANASTAS'].values()])
    exec(bloque(C4, 'suc_pais = maestro_suc[', 'NOMBRES_COMPUESTOS = {'), env)
    exec(bloque(C4, 'NOMBRES_COMPUESTOS = {', 'PESOS_POBLACION = {'), env)
    exec(C5, env)
    exec(bloque(C6, 'def _pmean(_s):', 'ref_e ='), env)
    env['GEOJSON_PATH'] = Path('sin_ar.json')        # sin poligonos: la CELDA 7 no reclasifica
    exec(bloque(C7, '# ── Provincia por coordenadas', '# ── Calcular canasta por sucursal'), env)
    exec(C9, env)
    exec(bloque(C19, 'from openpyxl.styles', 'out_xls ='), env)
    exec(compile(C19B, '<CELDA 19b>', 'exec'), env)
    return env, xls


# ── Calculo independiente (sin pandas: listas y statistics.median) ────────────
def independiente(cid):
    qty = {e: q for e, _d, q, _c in CAN[cid]}
    dias = defaultdict(list)            # (ean, mes) -> precios
    cierre = defaultdict(list)          # ean -> precios de la ultima semana de junio
    porsuc = defaultdict(list)          # (sucursal, ean, mes) -> precios
    for si, e, fe, p in OBS:
        if e not in qty:
            continue
        dias[(e, fe // 100)].append(p)
        porsuc[(si, e, fe // 100)].append(p)
        if ANT * 100 + N_ANT - 6 <= fe <= ANT * 100 + N_ANT:
            cierre[e].append(p)
    med = {k: statistics.median(v) for k, v in dias.items()}
    t0 = sum(qty[e] * med[(e, ANT)] for e in qty if (e, ANT) in med)
    t1 = sum(qty[e] * med[(e, ACT)] for e in qty if (e, ACT) in med)
    arr = sum(qty[e] * (statistics.median(cierre[e]) - med[(e, ANT)]) / t0 * 100
              for e in qty if cierre[e] and (e, ANT) in med)
    pares = []
    for (si, e, ym), v in porsuc.items():
        if ym != ANT or (si, e, ACT) not in porsuc:
            continue
        pa, pb = statistics.median(v), statistics.median(porsuc[(si, e, ACT)])
        if 0.25 <= pb / pa <= 4:
            pares.append((si, e, pa, pb))
    suma_ant = defaultdict(float)
    for si, e, pa, pb in pares:
        suma_ant[e] += pa
    aporte = defaultdict(float)         # (atributo, valor) -> pp
    total = 0.0
    for si, e, pa, pb in pares:
        a = qty[e] * med[(e, ANT)] / t0 * (pb - pa) / suma_ant[e] * 100
        s = SUCS[si]
        region = region_esp(s)
        tipo = TIPO_ESP[s[4][1]] if s[4] else 'Sin dato en maestro'
        for atr, val in (('cadena', CADENA_ESP[(s[0], s[1])]), ('provincia', PROV_ESP[s[3]]),
                         ('region', region), ('tipo', tipo)):
            aporte[(atr, val)] += a
        total += a
    return {'T0': t0, 'T1': t1, 'V_OF': (t1 / t0 - 1) * 100, 'ARR': arr, 'V_PAN': total,
            'aporte': aporte, 'pares': len(pares), 'n_prod': len({e for e, _ in med})}


def verificar(env, xls, etiqueta):
    print(f'\n-- {etiqueta} --')
    hojas = pd.read_excel(xls, sheet_name=None, dtype={'id_producto': str})
    chequear('Evolucion_IPC' in hojas and 'Serie_precios' in hojas, 'el Excel conserva las hojas de la CELDA 19')
    chequear(set(env['desag_dict']) == {'cantidad_03', 'cantidad_02'},
             f'desagrega las canastas activas de DESAGREGAR_CANASTAS: {sorted(env["desag_dict"])}')
    for cid in ['cantidad_03', 'cantidad_02']:
        suf = '' if cid == 'cantidad_03' else '_' + env['CANASTA_SHORT'][cid]
        h = {b: hojas.get(f'{b}{suf}'[:31]) for b in env['_HOJAS_DESAG']}
        nom = env['CANASTA_NAMES'][cid]
        if any(v is None for v in h.values()):
            chequear(False, f'[{nom}] faltan hojas: {[b for b, v in h.items() if v is None]}')
            continue
        ind = independiente(cid)
        t = env['desag_dict'][cid]['totales']
        sn = env['serie_nac_dict'][cid].set_index('mes')
        v9 = sn.loc['2026-07', 'variacion_mensual_%']
        chequear(cerca(t['V_OF'], v9) and cerca(t['V_OF'], ind['V_OF']),
                 f'[{nom}] oficial {t["V_OF"]:+.6f}% = CELDA 9 {v9:+.6f}% = independiente {ind["V_OF"]:+.6f}%')
        chequear(t['N_REP'] == t['N_PROD'] == ind['n_prod'],
                 f'[{nom}] medianas de la CELDA 9 reproducidas: {t["N_REP"]}/{t["N_PROD"]}')

        P = h['Productos']
        chequear(cerca(P['aporte_oficial_pp'].sum(), t['V_OF']),
                 f'[{nom}] Productos: aportes suman la oficial ({P["aporte_oficial_pp"].sum():+.9f})')
        chequear(np.allclose(P['arrastre_pp'] + P['nuevo_pp'], P['aporte_oficial_pp'], rtol=0, atol=1e-12),
                 f'[{nom}] Productos: arrastre_pp + nuevo_pp = aporte, producto a producto')
        comp = P.dropna(subset=['med_ant', 'med_act', 'med_cierre_ant'])
        nuevo = comp['qty'] * (comp['med_act'] - comp['med_cierre_ant']) / t['T0'] * 100
        chequear(len(comp) > 0 and np.allclose(comp['nuevo_pp'], nuevo, rtol=0, atol=1e-12),
                 f'[{nom}] Productos: nuevo_pp = qty x (mediana mes - mediana ultima semana) / canasta ant')
        chequear(cerca(t['ARR'], ind['ARR']) and cerca(t['ARR'] + t['NUE'], t['V_OF']),
                 f'[{nom}] arrastre {t["ARR"]:+.6f} = independiente {ind["ARR"]:+.6f}; '
                 f'arrastre + nuevo = oficial')
        chequear(cerca(t['V_PAN'], ind['V_PAN']) and t['N_PARES'] == ind['pares'],
                 f'[{nom}] panel {t["V_PAN"]:+.6f}% = independiente {ind["V_PAN"]:+.6f}% '
                 f'({t["N_PARES"]} pares)')
        chequear(cerca(P['aporte_panel_pp'].sum(), t['V_PAN']), f'[{nom}] Productos: aporte_panel_pp suma el panel')
        # el panel pesa 100 salvo los productos sin pares (la Yerba desaparece en julio)
        peso_panel = 100 - P.loc[P['sucursales_apareadas'].isna(), 'peso_%'].sum()
        chequear(cerca(peso_panel, 100) == (cid != 'cantidad_03'),
                 f'[{nom}] peso del panel {peso_panel:.4f} (100 salvo productos sin pares)')
        for hoja, col in (('Cadenas', 'cadena'), ('Provincias', 'provincia'), ('Regiones', 'region'),
                          ('Tipo_sucursal', 'tipo')):
            g = h[hoja]
            gr, tot = g[g[col] != 'TOTAL'], g[g[col] == 'TOTAL'].iloc[0]
            esp = {v: a for (atr, v), a in ind['aporte'].items() if atr == col}
            obt = dict(zip(gr[col], gr['aporte_pp']))
            ok_grupos = set(esp) == set(obt) and all(cerca(obt[v], esp[v]) for v in esp)
            chequear(ok_grupos and cerca(gr['aporte_pp'].sum(), t['V_PAN']) and cerca(tot['aporte_pp'], t['V_PAN'])
                     and cerca(gr['aporte_equiv_sobre_oficial_pp'].sum(), t['V_OF'])
                     and cerca(tot['aporte_equiv_sobre_oficial_pp'], t['V_OF'])
                     and cerca(gr['peso_base_pct'].sum(), tot['peso_base_pct'])
                     and cerca(tot['peso_base_pct'], peso_panel),
                     f'[{nom}] {hoja}: {len(gr)} grupos = independiente, suman el panel y el reescalado la oficial')
            if not ok_grupos:
                print('        esperado:', {k: round(v, 6) for k, v in esp.items()})
                print('        obtenido:', {k: round(v, 6) for k, v in obt.items()})
            chequear(g['var_mediana_grupo_%'].notna().all(), f'[{nom}] {hoja}: control var_mediana_grupo_% completo')
        for hoja in ('Grupos', 'Rubros'):
            g = h[hoja]
            chequear(cerca(g['aporte_oficial_pp'].sum(), t['V_OF']) and cerca(g['aporte_panel_pp'].sum(), t['V_PAN'])
                     and cerca(g['arrastre_pp'].sum(), t['ARR']) and cerca(g['nuevo_pp'].sum(), t['NUE']),
                     f'[{nom}] {hoja}: suman la oficial, el panel, el arrastre y lo nuevo')
        X = h['Aporte_prod_x_cadena']
        cad = [c for c in X.columns if c not in ('id_producto', 'descripcion', 'TOTAL')]
        chequear(cerca(X['TOTAL'].sum(), t['V_PAN']) and np.allclose(X[cad].sum(axis=1), X['TOTAL'], atol=1e-12),
                 f'[{nom}] Aporte_prod_x_cadena: {len(cad)} columnas suman el TOTAL y el TOTAL el panel')
        S = h['Subas_y_bajas']
        chequear(cerca(S['aporte_pp'].sum(), t['V_PAN']) and int(S['pares'].sum()) == t['N_PARES'],
                 f'[{nom}] Subas_y_bajas: suman el panel y los pares')
        M = h['Mes_parcial']
        chequear(cerca(M['variacion_%'].iloc[0], t['V_OF']) and cerca(M['variacion_%'].iloc[-2], t['ARR'])
                 and cerca(M['variacion_%'].iloc[-1], t['NUE']) and len(M) == 6,
                 f'[{nom}] Mes_parcial: 4 ventanas + arrastre; la primera es la oficial')
        D = h['Serie_diaria']
        chequear(len(D) == N_ANT + D_ACT and int(D['observaciones'].sum()) ==
                 sum(1 for _, e, _, _ in OBS if e in {x for x, *_ in CAN[cid]}),
                 f'[{nom}] Serie_diaria: {len(D)} dias con todas las observaciones')
        if cid == 'cantidad_03':
            R = h['Resumen_variacion']
            chequear(cerca(R.loc[R['indicador'] == 'Variacion oficial nb02 (%)', 'valor'].iloc[0], t['V_OF']),
                     f'[{nom}] Resumen_variacion trae la variacion oficial')
            yerba = P[P['id_producto'] == E_YERBA.zfill(13)].iloc[0]
            chequear(cerca(yerba['aporte_oficial_pp'], -yerba['qty'] * yerba['med_ant'] / t['T0'] * 100),
                     f'[{nom}] producto que desaparece: aporte = -su costo del mes anterior')
            chequear(P.loc[P['categoria'] == 'Mascotas', 'grupo'].eq('Otros').all(),
                     f'[{nom}] rubro fuera del mapa de grupos -> "Otros"')
            chequear((P['id_producto'] == E_GALLE.zfill(13)).any(), f'[{nom}] EAN con ceros a la izquierda leido')
    return hojas


if __name__ == '__main__':
    tmp = pathlib.Path(tempfile.mkdtemp(prefix='test_desag_nb02_'))
    env, xls = correr(tmp, centavos=False)
    hojas = verificar(env, xls, 'precios en pesos')

    # Re-correr la celda: reemplaza sus hojas, no duplica ni borra las demas
    n_hojas = len(hojas)
    exec(compile(C19B, '<CELDA 19b>', 'exec'), env)
    hojas2 = pd.read_excel(xls, sheet_name=None)
    chequear(len(hojas2) == n_hojas and list(hojas2) == list(hojas),
             f're-correr la celda reemplaza sus hojas ({len(hojas2)} hojas, sin duplicados)')

    env_c, xls_c = correr(tmp, centavos=True)
    verificar(env_c, xls_c, 'precios en centavos')
    print()
    for cid in ['cantidad_03', 'cantidad_02']:
        a, b = env['desag_dict'][cid]['totales'], env_c['desag_dict'][cid]['totales']
        chequear(all(cerca(a[k], b[k], 1e-12) for k in ('V_OF', 'V_PAN', 'ARR', 'NUE')),
                 f'[{cid}] centavos = pesos (oficial, panel, arrastre)')
    shutil.rmtree(tmp, ignore_errors=True)
    print('\nRESULTADO:', 'OK' if not fallas else f'FALLA ({len(fallas)})')
    raise SystemExit(1 if fallas else 0)
