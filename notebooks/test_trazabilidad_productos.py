"""Test del nb09 (trazabilidad de productos): corre las celdas REALES del notebook sobre un SEPA sintético
(2 meses, 2 partes por mes, 8 sucursales, 8 productos) y compara cada métrica con un cálculo directo (fuerza bruta).

El SEPA sintético trae a propósito los defectos que tiene el real:
  - filas sucursal x producto repetidas (idénticas, y una partida en dos filas con días distintos), algunas en otro
    bloque del archivo;
  - provincias vacías, escritas con el nombre ('Santa Fe', 'Provincia de Córdoba');
  - dos archivos para la misma parte de un mes (uno parcial, días 1-5, y el completo), con el parcial ÚLTIMO en el zip;
  - códigos que no son EAN: interno con guiones y de balanza (EAN-13 que empieza con 2).

    python notebooks/test_trazabilidad_productos.py
"""
import gzip, io, json, os, shutil, sys, tempfile, zipfile
from pathlib import Path
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
NB = REPO / 'notebooks' / '09_trazabilidad_productos.ipynb'
rng = np.random.default_rng(7)

# ── SEPA sintético ──────────────────────────────────────────────────────────────
SUCS = [('9', '1', '101', 'AR-C'), ('9', '2', '102', ''), ('12', '1', '201', 'AR-C'),
        ('12', '1', '202', 'Provincia de Córdoba'), ('15', '1', '301', 'AR-B'), ('15', '1', '302', 'AR-T'),
        ('19', '1', '401', 'AR-X'), ('15', '1', '303', 'Santa Fe')]
ISO = {'AR-C': 'AR-C', '': None, 'Provincia de Córdoba': 'AR-X', 'AR-B': 'AR-B', 'AR-T': 'AR-T', 'AR-X': 'AR-X',
       'Santa Fe': 'AR-S'}
EANS = ['7790895000232', '0007790070318312', '7791866001364', '123', '7798181510267', '7790742340108',
        '2003080000005', '10-1-2300377000008']
DIAS = pd.date_range('2026-01-01', '2026-02-28')
# Patrón por producto: probabilidad de que una sucursal lo tenga, días en que el producto no existe
REGLA = {'7790895000232': (1.0, None), '0007790070318312': (0.7, None),
         '7791866001364': (0.9, ('2026-01-10', '2026-01-20')),       # hueco de 11 días
         '123': (0.5, ('2026-01-01', '2026-01-31')),                 # aparece en febrero
         '7798181510267': (0.6, ('2026-02-15', '2026-02-28')),        # desaparece a mitad de febrero
         '7790742340108': (0.15, None),
         '2003080000005': (0.4, None), '10-1-2300377000008': (0.3, None)}
# Una sucursal que no reporta nada del 5 al 8 de enero (cambia el denominador diario)
SIN_REPORTE = ('15', '1', '302'), pd.date_range('2026-01-05', '2026-01-08')

filas = []
for (c, b, s, p) in SUCS:
    for e in EANS:
        prob, fuera = REGLA[e]
        if e == '7790742340108' and c != '9':
            continue                                                  # solo en Cencosud
        for d in DIAS:
            if fuera and pd.Timestamp(fuera[0]) <= d <= pd.Timestamp(fuera[1]):
                continue
            if (c, b, s) == SIN_REPORTE[0] and d in SIN_REPORTE[1]:
                continue
            if (c, b, s) == ('9', '2', '102') and d < pd.Timestamp('2026-01-16'):
                continue                                              # la sucursal sin provincia empieza el 16/01
            if rng.random() < prob:
                filas.append((c, b, s, p, e, d, int(rng.integers(50_000, 900_000))))   # centavos
obs = pd.DataFrame(filas, columns=['c', 'b', 's', 'p', 'e', 'd', 'precio'])

def tabla(mes, dd):
    o = obs[obs['d'].isin(dd)]
    w = o.pivot_table(index=['c', 'b', 's', 'p', 'e'], columns='d', values='precio', aggfunc='first')
    idx = obs[obs['d'].dt.month == mes].groupby(['c', 'b', 's', 'p', 'e']).size().index
    w = w.reindex(idx).reindex(columns=dd)
    w.columns = [f'precio_{d:%Y%m%d}' for d in dd]
    return w.reset_index().rename(columns={'c': 'id_comercio', 'b': 'id_bandera', 's': 'id_sucursal',
                                           'p': 'sucursales_provincia', 'e': 'id_producto'})

def con_repetidas(w):
    # 3 filas repetidas idénticas al final del archivo (otro bloque) y una fila partida en dos con días distintos
    w = w.copy()
    pc = [c for c in w.columns if c.startswith('precio_')]
    llenas = w.index[w[pc].notna().sum(axis=1) >= 4]
    rep = w.loc[llenas[:3]]
    i = llenas[5]
    dias_i = [c for c in pc if pd.notna(w.at[i, c])]
    a, b = w.loc[[i]].copy(), w.loc[[i]].copy()
    a[dias_i[len(dias_i) // 2:]] = np.nan
    b[dias_i[:len(dias_i) // 2]] = np.nan
    return pd.concat([w.drop(index=i), a, rep, b], ignore_index=True)

def gz(w):
    buf = io.StringIO(); w.to_csv(buf, index=False, na_rep='NA')
    return gzip.compress(buf.getvalue().encode())

tmp = Path(tempfile.mkdtemp(prefix='test_nb09_'))
sepa = tmp / 'carga'; sepa.mkdir()
with zipfile.ZipFile(sepa / '2026A.zip', 'w') as zf:
    for mes in (1, 2):
        dm = [d for d in DIAS if d.month == mes]
        for parte, dd in ((1, [d for d in dm if d.day <= 15]), (2, [d for d in dm if d.day > 15])):
            w = tabla(mes, dd)
            if (mes, parte) == (1, 2):
                w = con_repetidas(w)
            zf.writestr(f'{mes:02d}2026_pais_parte{parte}COMPLETO{"b" if (mes, parte) == (1, 1) else ""}.csv.gz', gz(w))
            if (mes, parte) == (1, 1):
                # el archivo parcial (días 1-5) de la misma parte, ÚLTIMO en el zip: no se debe usar ni sumar
                zf.writestr('012026_pais_parte1COMPLETO.csv.gz', gz(tabla(1, [d for d in dd if d.day <= 5])))

# ── Correr las celdas reales ────────────────────────────────────────────────────
cells = [''.join(c['source']) for c in json.load(open(NB, encoding='utf-8'))['cells'] if c['cell_type'] == 'code']
os.chdir(REPO)

def correr(out='out', **extra):
    g = {}
    exec(cells[0], g)
    g.update(SEPA_DIR=str(sepa), OUTPUT_DIR=str(tmp / out), FECHA_INICIO='2026-01-01', USAR_GEOREF=False,
             MIN_SUC_DIA_UTIL=3, MIN_PCT_DIA_UTIL=50.0, **extra)
    for c in cells[1:]:
        exec(c, g)
    return g

g = correr()
R = g['R'].set_index('id_producto')

# ── Fuerza bruta ────────────────────────────────────────────────────────────────
obs['e'] = obs['e'].str.lstrip('0')
obs['suc'] = obs['c'] + '|' + obs['b'] + '|' + obs['s']
obs['iso'] = obs['p'].map(ISO)
act = obs.groupby('d')['suc'].nunique()
act_com = obs.groupby('d')['c'].nunique()
act_prv = obs.dropna(subset=['iso']).groupby('d')['iso'].nunique()
fechas = pd.DatetimeIndex(sorted(obs['d'].unique()))
ND = len(fechas)
errores = []

def chk(nombre, a, b, tol=1e-6):
    a, b = (float(x) if isinstance(x, (bool, np.bool_)) else x for x in (a, b))
    if not (abs(a - b) <= tol or (pd.isna(a) and pd.isna(b))):
        errores.append(f'{nombre}: notebook {a} vs esperado {b}')

prov_tot = obs['iso'].dropna().nunique(); com_tot = obs['c'].nunique(); suc_tot = obs['suc'].nunique()
for e, o in obs.groupby('e'):
    r = R.loc[e]
    dd = o.groupby('d')['suc'].nunique()
    chk(f'{e} dias_con_precio', r['dias_con_precio'], len(dd))
    chk(f'{e} pct_dias', r['pct_dias'], len(dd) / ND * 100, 1e-4)
    chk(f'{e} sucursales_distintas', r['sucursales_distintas'], o['suc'].nunique())
    chk(f'{e} comercios', r['comercios'], o['c'].nunique())
    chk(f'{e} banderas', r['banderas'], o.groupby(['c', 'b']).ngroups)
    chk(f'{e} provincias', r['provincias'], o['iso'].dropna().nunique())
    chk(f'{e} pct_suc_diaria_prom', r['pct_suc_diaria_prom'], (dd / act.reindex(dd.index)).mean() * 100, 1e-4)
    dc = o.groupby('d')['c'].nunique()
    chk(f'{e} pct_com_diaria_prom', r['pct_com_diaria_prom'], (dc / act_com.reindex(dc.index)).mean() * 100, 1e-4)
    dp = o.dropna(subset=['iso']).groupby('d')['iso'].nunique().reindex(dd.index).fillna(0)
    chk(f'{e} pct_prov_diaria_prom', r['pct_prov_diaria_prom'], (dp / act_prv.reindex(dd.index)).mean() * 100, 1e-4)
    chk(f'{e} suc_diarias_min', r['suc_diarias_min'], dd.min())
    chk(f'{e} sucursal_dias', r['sucursal_dias'], len(o.drop_duplicates(['suc', 'd'])))
    util = ((dd >= 3) & (dd / act.reindex(dd.index) * 100 >= 50)).sum()
    chk(f'{e} dias_utiles', r['dias_utiles'], util)
    chk(f'{e} primer_dia', r['primer_dia'].value, dd.index.min().value)
    chk(f'{e} ultimo_dia', r['ultimo_dia'].value, dd.index.max().value)
    pres = pd.Series(fechas.isin(dd.index), index=fechas)
    pres_v = pres[pres.idxmax():]
    grp = (pres_v != pres_v.shift()).cumsum()
    rachas = pres_v.groupby(grp).agg(['first', 'size'])
    chk(f'{e} racha_max', r['racha_max_dias'], rachas.loc[rachas['first'], 'size'].max())
    chk(f'{e} hueco_max', r['hueco_max_dias'], rachas.loc[~rachas['first'], 'size'].max() if (~rachas['first']).any() else 0)
    feb = o[o['d'].dt.month == 2]
    if len(feb):
        med = (feb.groupby('suc')['precio'].mean() / 100).median()
        chk(f'{e} precio_mediano_ultimo_mes', r['precio_mediano_ultimo_mes'], med, 0.01)
    sd = o.groupby('c')['d'].size()                                   # sucursal-días por comercio
    chk(f'{e} hhi_cadenas', r['hhi_cadenas'], ((sd / sd.sum()) ** 2).sum(), 1e-4)
    chk(f'{e} pct_cadena_principal', r['pct_cadena_principal'], sd.max() / sd.sum() * 100, 1e-4)
    chk(f'{e} continuo_periodo', r['continuo_periodo'], len(dd) == ND)
    chk(f'{e} en_universo_nb02', r['en_universo_nb02'], bool((o['c'] != '19').any()))
    chk(f'{e} puntaje', r['puntaje'], (r['pct_dias'] * r['pct_suc_diaria_prom'] * r['pct_com_diaria_prom'] *
                                       r['pct_provincias'] / 100 ** 4) ** 0.25 * 100, 0.006)

chk('productos', len(R), obs['e'].nunique())
for cod, esperado in (('123', False), ('7790895000232', True), ('7790070318312', True), ('2003080000005', False),
                      ('10-1-2300377000008', False)):
    chk(f'es_ean {cod}', R.loc[cod, 'es_ean'], esperado)
chk('sucursales_total', R['sucursales_total'].iloc[0], suc_tot)
chk('comercios_total', R['comercios_total'].iloc[0], com_tot)
chk('provincias_total (sin la vacía; nombres pasados a código)', R['provincias_total'].iloc[0], prov_tot)
chk('dias_periodo', R['dias_periodo'].iloc[0], ND)
chk('cadena principal cencosud', R.loc['7790742340108', 'pct_cadena_principal'], 100.0)
chk('lista de cadenas separada por ;', R.loc['7790895000232', 'cadenas'].count('; '), com_tot - 1)
chk('parte repetida: se eligió el archivo completo', [x[2] for x in g['ARCHIVOS_REPETIDOS']] == ['2026A.zip/012026_pais_parte1COMPLETOb.csv.gz'], True)
chk('filas repetidas contadas', int(sum((g['_info_de'](t).get('duplicados') or 0) for t in g['TAGS'])), 4)
chk('fuente de la provincia', g['SUC']['provincia_fuente'].value_counts().to_dict() ==
    {'archivo': 5, 'archivo (nombre pasado a código)': 2, 'sin dato': 1}, True)
pv = pd.read_excel(next((tmp / 'out').glob('trazabilidad_productos_*.xlsx')), 'Provincias').set_index('provincia')
chk('Provincias: una sucursal sin dato', int(pv.loc[[i for i in pv.index if i.startswith('Sin dato')], 'sucursales'].sum()), 1)
chk('Provincias: 5 reales + sin dato', len(pv), prov_tot + 1)
# Panel mensual
pm = pd.read_parquet(next((tmp / 'out').glob('panel_mensual_productos_*.parquet')))
chk('panel enero coca', pm.query("id_producto == '7790895000232' and mes == '2026-01'")['dias_con_precio'].iat[0],
    obs.query("e == '7790895000232' and d.dt.month == 1")['d'].nunique())
# Excel con todas las hojas
x = pd.ExcelFile(next((tmp / 'out').glob('trazabilidad_productos_*.xlsx')))
chk('hojas Excel', x.sheet_names == ['Resumen', 'Ranking', 'Continuos_periodo', 'Por_categoria', 'Cadenas',
                                    'Provincias', 'Diccionario'], True)
chk('filas Ranking', len(pd.read_excel(x, 'Ranking')), len(R))

cols = [c for c in R.columns if c != 'ranking']

def igual(nombre, R2):
    a, b = R[cols].sort_index(), R2[cols].sort_index()
    ok = a.index.equals(b.index) and all(
        (a[c].fillna(-1) == b[c].fillna(-1)).all() if a[c].dtype == object or a[c].dtype == bool
        else np.allclose(a[c].astype(float), b[c].astype(float), equal_nan=True, rtol=1e-6) if pd.api.types.is_numeric_dtype(a[c])
        else a[c].equals(b[c]) for c in cols)
    chk(nombre, ok, True)

# Segunda corrida: enero desde el caché, febrero (último mes) releído; mismo resultado
igual('segunda corrida igual', correr()['R'].set_index('id_producto'))
# Caché de una versión anterior del lector: un resumen con una provincia escrita con el nombre se relee; otro que está
# bien solo se marca como versión actual. Mismo resultado.
_res = tmp / 'out' / '_cache_nb09' / 'v1'
for t in ('2026-01_p1', '2026-01_p2'):
    inf = json.loads((_res / f'{t}__info.json').read_text()); inf.pop('version'); (_res / f'{t}__info.json').write_text(json.dumps(inf))
_s = pd.read_parquet(_res / '2026-01_p2__suc.parquet'); _s.loc[_s['suc'] == '15|1|303', 'provincia_iso'] = 'Santa Fe'
_s.to_parquet(_res / '2026-01_p2__suc.parquet', index=False)
g3 = correr()
chk('caché viejo: se relee solo el que hace falta', sorted(g3['_releer']) == ['2026-01_p2'], True)
igual('caché viejo actualizado igual', g3['R'].set_index('id_producto'))
# Lectura en bloques diminutos (las filas repetidas caen en otro bloque) y 3 grupos de productos: mismo resultado
igual('bloques chicos y 3 grupos', correr('out_bloques', BLOQUE_MB=0.002, N_GRUPOS=3)['R'].set_index('id_producto'))
# Cambiar N_GRUPOS con el caché hecho: los resúmenes producto x sucursal se reorganizan solos, mismo resultado
igual('caché reorganizado a 5 grupos', correr('out_bloques', BLOQUE_MB=0.002, N_GRUPOS=5)['R'].set_index('id_producto'))
# Lector en este proceso (sin subproceso): mismo resultado
igual('sin proceso aparte', correr('out_mismo', PROCESO_APARTE=False)['R'].set_index('id_producto'))

shutil.rmtree(tmp, ignore_errors=True)
if errores:
    print('FALLAS:'); [print('  ' + x) for x in errores]
    sys.exit(1)
print(f'OK: {len(R)} productos, {ND} días, todas las métricas iguales a la fuerza bruta')
