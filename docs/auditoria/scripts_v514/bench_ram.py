# -*- coding: utf-8 -*-
"""Corre el CODIGO REAL de las CELDAS 7 (cola) y 8 (hasta el costo por sucursal) de gen_nb07.py,
version vieja o nueva, sobre un panel sintetico grande. Mide el pico de RAM y guarda las salidas.

    python bench_ram.py <gen_nb07.py> <salida.pkl> <n_suc> [cache_dir]      (CAP=1 guarda las salidas)
    python cmp.py <salida_vieja.pkl> <salida_nueva.pkl>                      (identidad vieja vs nueva)

Ejemplo (2026-10-02): `git show <commit v5.13>:notebooks/gen_nb07.py > gen_old.py`, n_suc=8000 (~31 M de filas,
un tercio del panel real; la primera corrida arma el cache sintetico). Pico por etapa: A carga del cache,
B panel semanal, C sval + nacional, D costo por sucursal. El pico total en Windows sale de peak_wset.
"""
import io, gc, os, sys, pathlib, pickle, tempfile, datetime as _dt, time
import numpy as np, pandas as pd, psutil
from tqdm.auto import tqdm

GEN, OUT, NSUC = sys.argv[1], sys.argv[2], int(sys.argv[3])
CACHE = pathlib.Path(sys.argv[4]) if len(sys.argv) > 4 else pathlib.Path(tempfile.mkdtemp())
src = io.open(GEN, encoding='utf-8').read()
def blk(a, b, incl_b=False):
    i0 = src.index(a); i1 = src.index(b, i0)
    return src[i0:i1 + (len(b) if incl_b else 0)]
B_MES = blk('def _semana_cierre(', '\ndef _sem_anterior(')
B_A = blk('import pyarrow as pa, pyarrow.parquet as pq, pyarrow.compute as pc', '_EAN_NAC.clear(); gc.collect()\n', True)
B_B = blk('# Mes en curso: siempre fresco.', "\n''' ))")
B_C = blk("_SK = ['id_comercio','id_bandera','id_sucursal']\n", '# ── 2b. Frescos: la FORMA')
B_D = blk('# ── Precios POR SUCURSAL de los tipos con nivel anclado', "\n''' ))")

NUEVA = 'SUC_COD' in src
_SKR = ['id_comercio', 'id_bandera', 'id_sucursal']
MESES = [f'2024-{m:02d}' for m in range(1, 12)]
ACT = MESES[-1]
rng0 = np.random.default_rng(7)
# Sucursales: comercios 1..20 (el 99 es una estacion de servicio a filtrar). Provincias al azar.
COM = rng0.integers(1, 21, NSUC).astype(str); COM[:NSUC // 50] = '99'
SUCS = pd.DataFrame({'id_comercio': COM, 'id_bandera': rng0.integers(1, 4, NSUC).astype(str),
                     'id_sucursal': np.arange(NSUC).astype(str)})
PROVS = ['Provincia de Buenos Aires', 'Ciudad Autonoma de Buenos Aires', 'Provincia de Cordoba',
         'Provincia de Santa Fe', 'Provincia de Mendoza', 'Provincia de Salta', 'Provincia de Neuquen']
SUCS['PROVINCIA'] = rng0.choice(PROVS, NSUC)
EMP = [f'7790{i:09d}' for i in range(200)]
FR = ['Banana', 'Papa', 'Pollo', 'Tomate', 'Naranja', 'Asado', 'Leche suelta', 'Pan'] * 1
ITEMS = EMP + FR
BASE = dict(zip(ITEMS, rng0.uniform(500, 8000, len(ITEMS))))

def panel_mes(lbl):
    y, m = map(int, lbl.split('-'))
    d0 = _dt.date(y, m, 1); d1 = _dt.date(y + (m == 12), m % 12 + 1, 1)
    dias = [d0 + _dt.timedelta(days=k) for k in range((d1 - d0).days)]
    sems = sorted({ns['_semana_cierre'](d) for d in dias})
    rng = np.random.default_rng(y * 100 + m)
    n = NSUC * len(ITEMS)
    out = []
    for w in sems:
        keep = rng.random(n) < 0.35
        si = np.repeat(np.arange(NSUC), len(ITEMS))[keep]
        ii = np.tile(np.arange(len(ITEMS)), NSUC)[keep]
        infl = 1.03 ** (m + (int(w[8:]) / 31))
        pr = np.array([BASE[i] for i in ITEMS])[ii] * infl * rng.lognormal(0, 0.15, keep.sum())
        df = SUCS.iloc[si][_SKR].reset_index(drop=True)
        df['semana'] = w; df['item'] = np.array(ITEMS, dtype=object)[ii]; df['price'] = pr
        out.append(df)
    return pd.concat(out, ignore_index=True)

ns = {'_dt': _dt, 'DIA_CIERRE_SEMANA': 3}
exec(B_MES, ns)
def _leer_mes(lbl):
    return panel_mes(lbl)
def _colapsar(df, lbl=''):
    if df is None: return None
    g['_EAN_NAC'].append(df[df['item'].isin(FR)].groupby(['item', 'semana'], as_index=False)
                         .agg(p=('price', 'median'), n_suc=('price', 'size')).assign(ean_norm='x')
                         [['item', 'ean_norm', 'semana', 'p', 'n_suc']])
    return df[_SKR + ['semana', 'item', 'price']]

REGION = {'Buenos Aires': 'Pampeana', 'CABA': 'GBA', 'Cordoba': 'Pampeana', 'Santa Fe': 'Pampeana',
          'Mendoza': 'Cuyo', 'Salta': 'NOA', 'Neuquen': 'Patagonia'}
def norm_prov(x):
    return {'Provincia de Buenos Aires': 'Buenos Aires', 'Ciudad Autonoma de Buenos Aires': 'CABA'}.get(
        x, x.replace('Provincia de ', '').replace('Provincia del ', ''))
def asignar_cadena(row):
    return f"Cadena {row['id_comercio']}"
REC = {}
for k, name in enumerate(['Popular', 'Media']):
    its = EMP[k * 50:k * 50 + 60] + FR
    REC[name] = pd.DataFrame({'item': its, 'qty': 1.0 + np.arange(len(its)) % 3,
                              'rubro': [f'R{j % 9}' for j in range(len(its))],
                              'kind': ['emp'] * 60 + ['fresh'] * len(FR)})
IDS = set(zip(SUCS['id_comercio'], SUCS['id_bandera'], SUCS['id_sucursal']))
g = dict(pd=pd, np=np, os=os, gc=gc, tqdm=tqdm, _dt=_dt, _SKR=_SKR, _mes_de_semana=ns['_mes_de_semana'],
         _leer_mes=_leer_mes, _colapsar=_colapsar, _EAN_NAC=[], USE_CACHE=True,
         _meses_disp=MESES, _mes_actual=ACT, _cache_dir_sem=CACHE / 'sem_k_v5', _cache_dir_ean=CACHE / 'ean_k_v5',
         _FECHAS_MAX=[pd.Timestamp('2024-11-30')], MES_INICIO_HISTORICO='2024-01', FRESCO_INFO={t: {} for t in FR},
         EANS_EMP=set(EMP), EANS_EMP_LECT=set(EMP),
         suc_pais=SUCS, asignar_cadena=asignar_cadena, norm_prov=norm_prov, REGION_PROV=REGION,
         CADENAS_FILTRAR=['99'], AGG_NACIONAL='poblacion', MIN_SUC_PROV_ITEM=3, PROV_OUTLIER_K=2.5,
         PESOS_POBLACION={'Buenos Aires': 17.7, 'CABA': 3.1, 'Cordoba': 4.0, 'Santa Fe': 3.6, 'Mendoza': 2.0,
                          'Salta': 1.4, 'Neuquen': 0.7},
         MIN_SUC_ITEM_SEMANA=60, FRAC_SUC_ITEM_TIPICA=0.5,
         RECETAS=REC, CANASTAS_ACTIVAS=['Popular', 'Media'], FRAC_PRODUCTOS_MIN=0.3,
         FACTOR_NIVEL_FRESCO={'Pollo': 0.5})
if NUEVA:
    g['SUC_COD'] = {k: i for i, k in enumerate(sorted(IDS))}
proc = psutil.Process()
import threading
PK = {'v': 0}
def _mon():
    while True:
        PK['v'] = max(PK['v'], proc.memory_info().rss); time.sleep(0.05)
threading.Thread(target=_mon, daemon=True).start()
def etapa(nombre, code):
    PK['v'] = proc.memory_info().rss; t = time.time()
    exec(code, g); gc.collect()
    print(f'  {nombre:<28} pico {PK["v"]/2**30:5.2f} GB | queda {proc.memory_info().rss/2**30:5.2f} GB | {time.time()-t:.0f}s', flush=True)
t0 = time.time()
etapa('A carga del cache', B_A)
etapa('B panel semanal', B_B)
res = {}
if os.environ.get('CAP'):
    d = g['datos_sem']
    if NUEVA:
        inv = pd.DataFrame(sorted(g['SUC_COD'], key=g['SUC_COD'].get), columns=_SKR)
        k = inv.iloc[d['suc'].to_numpy()].reset_index(drop=True)
        res['datos_sem'] = pd.concat([k, d[['item', 'semana']].astype(object).reset_index(drop=True),
                                      d[['price']].reset_index(drop=True)], axis=1)
    else:
        res['datos_sem'] = d[_SKR + ['item', 'semana', 'price']].reset_index(drop=True)
etapa('C sval + nacional', B_C)
g['nac_ff_long'] = g['nac_item'][['item', 'semana', 'nac']].dropna()
etapa('D costo por sucursal', B_D)
res.update(nac_item=g['nac_item'], nac_wide=g['nac_wide'], nsuc=g['N_SUC_ITEM_SEMANA'], costo_suc=g['costo_suc'],
           peak=proc.memory_info().peak_wset)
pickle.dump(res, open(OUT, 'wb'))
print(f'{"NUEVA" if NUEVA else "VIEJA"}: pico total {proc.memory_info().peak_wset/2**30:.2f} GB | {time.time()-t0:.0f}s')
