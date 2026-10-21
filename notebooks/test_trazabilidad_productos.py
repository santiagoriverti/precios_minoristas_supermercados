"""Test del nb09 (trazabilidad de productos): corre las celdas REALES del notebook sobre un SEPA sintético
(2 meses, 2 partes por mes, 7 sucursales, 6 productos) y compara cada métrica con un cálculo directo (fuerza bruta).

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
SUCS = [('9', '1', '101', 'AR-C'), ('9', '2', '102', 'AR-B'), ('12', '1', '201', 'AR-C'), ('12', '1', '202', 'AR-X'),
        ('15', '1', '301', 'AR-B'), ('15', '1', '302', 'AR-T'), ('19', '1', '401', 'AR-X')]
EANS = ['7790895000232', '0007790070318312', '7791866001364', '123', '7798181510267', '7790742340108']
DIAS = pd.date_range('2026-01-01', '2026-02-28')
# Patrón por producto: probabilidad de que una sucursal lo tenga, días en que el producto no existe
REGLA = {'7790895000232': (1.0, None), '0007790070318312': (0.7, None),
         '7791866001364': (0.9, ('2026-01-10', '2026-01-20')),       # hueco de 11 días
         '123': (0.5, ('2026-01-01', '2026-01-31')),                 # aparece en febrero
         '7798181510267': (0.6, ('2026-02-15', '2026-02-28')),        # desaparece a mitad de febrero
         '7790742340108': (0.15, None)}
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
            if rng.random() < prob:
                filas.append((c, b, s, p, e, d, int(rng.integers(50_000, 900_000))))   # centavos
obs = pd.DataFrame(filas, columns=['c', 'b', 's', 'p', 'e', 'd', 'precio'])

tmp = Path(tempfile.mkdtemp(prefix='test_nb09_'))
sepa = tmp / 'carga'; sepa.mkdir()
with zipfile.ZipFile(sepa / '2026A.zip', 'w') as zf:
    for mes in (1, 2):
        dm = [d for d in DIAS if d.month == mes]
        for parte, dd in ((1, [d for d in dm if d.day <= 15]), (2, [d for d in dm if d.day > 15])):
            o = obs[obs['d'].isin(dd)]
            w = o.pivot_table(index=['c', 'b', 's', 'p', 'e'], columns='d', values='precio', aggfunc='first')
            # todas las combinaciones sucursal x producto con alguna fila en el mes aparecen (con NA los días sin precio)
            idx = obs[obs['d'].dt.month == mes].groupby(['c', 'b', 's', 'p', 'e']).size().index
            w = w.reindex(idx).reindex(columns=dd)
            w.columns = [f'precio_{d:%Y%m%d}' for d in dd]
            w = w.reset_index().rename(columns={'c': 'id_comercio', 'b': 'id_bandera', 's': 'id_sucursal',
                                                'p': 'sucursales_provincia', 'e': 'id_producto'})
            buf = io.StringIO(); w.to_csv(buf, index=False, na_rep='NA')
            zf.writestr(f'{mes:02d}2026_pais_parte{parte}COMPLETO.csv.gz', gzip.compress(buf.getvalue().encode()))

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
act = obs.groupby('d')['suc'].nunique()
fechas = pd.DatetimeIndex(sorted(obs['d'].unique()))
ND = len(fechas)
errores = []

def chk(nombre, a, b, tol=1e-6):
    a, b = (float(x) if isinstance(x, (bool, np.bool_)) else x for x in (a, b))
    if not (abs(a - b) <= tol or (pd.isna(a) and pd.isna(b))):
        errores.append(f'{nombre}: notebook {a} vs esperado {b}')

prov_tot = obs['p'].nunique(); com_tot = obs['c'].nunique(); suc_tot = obs['suc'].nunique()
for e, o in obs.groupby('e'):
    r = R.loc[e]
    dd = o.groupby('d')['suc'].nunique()
    chk(f'{e} dias_con_precio', r['dias_con_precio'], len(dd))
    chk(f'{e} pct_dias', r['pct_dias'], round(len(dd) / ND * 100, 2), 0.006)
    chk(f'{e} sucursales_distintas', r['sucursales_distintas'], o['suc'].nunique())
    chk(f'{e} comercios', r['comercios'], o['c'].nunique())
    chk(f'{e} banderas', r['banderas'], o.groupby(['c', 'b']).ngroups)
    chk(f'{e} provincias', r['provincias'], o['p'].nunique())
    chk(f'{e} pct_suc_diaria_prom', r['pct_suc_diaria_prom'], round((dd / act.reindex(dd.index)).mean() * 100, 2), 0.006)
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
    chk(f'{e} continuo_periodo', r['continuo_periodo'], len(dd) == ND)
    chk(f'{e} en_universo_nb02', r['en_universo_nb02'], bool((o['c'] != '19').any()))

chk('productos', len(R), obs['e'].nunique())
chk('es_ean 123', R.loc['123', 'es_ean'], False)
chk('es_ean coca', R.loc['7790895000232', 'es_ean'], True)
chk('sucursales_total', R['sucursales_total'].iloc[0], suc_tot)
chk('comercios_total', R['comercios_total'].iloc[0], com_tot)
chk('provincias_total', R['provincias_total'].iloc[0], prov_tot)
chk('dias_periodo', R['dias_periodo'].iloc[0], ND)
chk('cadena principal cencosud', R.loc['7790742340108', 'pct_cadena_principal'], 100.0)
chk('regiones CABA+Cordoba+Tucuman', R.loc['7790895000232', 'regiones'] >= 3, True)
# El puntaje es la media geométrica de sus 4 componentes
r = R.loc['7791866001364']
chk('puntaje', r['puntaje'], round((r['pct_dias'] * r['pct_suc_diaria_prom'] * r['pct_comercios'] * r['pct_provincias'])
                                    ** 0.25, 2), 0.02)
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
# Lectura en bloques diminutos (muchos bloques por archivo) y 3 grupos de productos: mismo resultado
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
