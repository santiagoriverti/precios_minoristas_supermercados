# -*- coding: utf-8 -*-
"""Paso 1 - Replica independiente desde el cache POR SUCURSAL del nb07 (meses cerrados).

Lee los parquet `sem_<key>_v5/<mes>.parquet` (una fila por sucursal x item x semana) y produce, en
AUD_TRABAJO:
  rep_nac.parquet   precio nacional replicado por item x semana (mediana provincial ponderada por
                    poblacion, >=3 sucursales por provincia, winsor K=2,5, fallback mediana simple)
  rep_jev.parquet   eslabon semanal de un indice de muestra apareada POR SUCURSAL (misma sucursal,
                    mismo item, semana t contra t-1). OJO: sesgado hacia abajo en este panel (pierde
                    el eslabon cuando un item falta una semana y vuelve repreciado); se conserva
                    como evidencia de por que no se lo usa como control.
  rep_cad.parquet   mediana y n de sucursales por item x semana x cadena
  rep_prov.parquet  idem por provincia

Tarda ~4 minutos y necesita ~4 GB de RAM (85 M de filas).
"""
import time
import numpy as np, pandas as pd, pyarrow.parquet as pq
import config
from comun import FILT, POB, sucursales

MIN_SUC, K_WIN, K_QB = 3, 2.5, 3.0
t0 = time.time()
ms = sucursales()
SUC_IDX = dict(zip(ms.key, ms.index))
PROVS = sorted(ms.prov.unique()); P_IDX = {p: i for i, p in enumerate(PROVS)}
CADS = sorted(ms.cadena.unique()); C_IDX = {c: i for i, c in enumerate(CADS)}
suc_prov = ms.prov.map(P_IDX).to_numpy(np.int16)
suc_cad = ms.cadena.map(C_IDX).to_numpy(np.int16)
w_prov = np.array([POB.get(p, 0.0) for p in PROVS], dtype=float)

S, I, W, PR = [], [], [], []
items, weeks = {}, {}
for f in sorted(config.carpeta_cache('sem').glob('*.parquet')):
    d = pq.read_table(f).to_pandas()
    d = d[~d.id_comercio.isin(FILT)]
    k = (d.id_comercio + '|' + d.id_bandera + '|' + d.id_sucursal).map(SUC_IDX)
    ok = k.notna(); d = d[ok]; k = k[ok].astype(np.int32)
    for it in d.item.unique():
        items.setdefault(it, len(items))
    for w in d.semana.unique():
        weeks.setdefault(w, None)
    S.append(k.to_numpy(np.int32)); I.append(d.item.map(items).to_numpy(np.int16))
    W.append(d.semana.to_numpy()); PR.append(d.price.to_numpy(np.float64))
    print(f.stem, len(d), f'{time.time()-t0:.0f}s', flush=True)
WEEKS = sorted(weeks); W_IDX = {w: i for i, w in enumerate(WEEKS)}
S = np.concatenate(S); I = np.concatenate(I); PR = np.concatenate(PR)
W = np.concatenate([pd.Series(x).map(W_IDX).to_numpy(np.int16) for x in W])
ITEMS = [None] * len(items)
for it, i in items.items():
    ITEMS[i] = it
print('filas', len(S), 'items', len(ITEMS), 'semanas', len(WEEKS))

# Una semana partida entre dos meses aparece en los dos parquet (una fila por mes, cada una con la
# mediana de sus dias) -> promedio de las dos, que es lo que hace el groupby-median del nb07.
key = (I.astype(np.int64) * 100000 + S.astype(np.int64)) * 1000 + W.astype(np.int64)
o = np.argsort(key, kind='stable')
key, S, I, W, PR = key[o], S[o], I[o], W[o], PR[o]
_, st, cnt = np.unique(key, return_index=True, return_counts=True)
PR = np.add.reduceat(PR, st) / cnt
S, I, W = S[st], I[st], W[st]
del key, o
print('filas unicas', len(S), f'{time.time()-t0:.0f}s')

bounds = np.flatnonzero(np.diff(I)) + 1
out_nac, out_jev, out_cad, out_prov = [], [], [], []
for a, b in zip(np.r_[0, bounds], np.r_[bounds, len(I)]):
    it = ITEMS[I[a]]
    s = S[a:b]; w = W[a:b]; p = PR[a:b]
    df = pd.DataFrame({'s': s, 'w': w, 'p': p, 'pv': suc_prov[s], 'cd': suc_cad[s]})
    # precio nacional (replica del estimador del nb07, CELDA 8)
    simple = df.groupby('w').p.median()
    pi = df.groupby(['w', 'pv']).agg(p=('p', 'median'), n=('s', 'nunique')).reset_index()
    pi = pi[pi.n >= MIN_SUC]
    med = pi.groupby('w').p.transform('median')
    pi = pi[(pi.p >= med / K_WIN) & (pi.p <= med * K_WIN)].copy()
    pi['wt'] = w_prov[pi.pv.to_numpy()]; pi['wv'] = pi.wt * pi.p
    g = pi.groupby('w').agg(wv=('wv', 'sum'), wt=('wt', 'sum'), n_prov=('pv', 'nunique'))
    nac = pd.DataFrame({'simple': simple}).join(g, how='left')
    nac['nac_rep'] = np.where(nac.wt.fillna(0) > 0, nac.wv / nac.wt, nac.simple)
    nac['n_suc'] = df.groupby('w').s.nunique(); nac['item'] = it
    out_nac.append(nac.reset_index()[['item', 'w', 'nac_rep', 'simple', 'n_prov', 'n_suc']])
    # muestra apareada por sucursal (semanas consecutivas)
    m = pd.DataFrame({'s': s, 'w': w, 'lp': np.log(p), 'pv': suc_prov[s]})
    prev = m.assign(w=m.w + 1).rename(columns={'lp': 'lp0'})[['s', 'w', 'lp0']]
    j = m.merge(prev, on=['s', 'w'], how='inner'); j['r'] = j.lp - j.lp0; j = j[np.isfinite(j.r)]
    jj = j[np.abs(j.r) <= np.log(K_QB)]
    jp = jj.groupby(['w', 'pv']).r.mean().reset_index(); jp['wt'] = w_prov[jp.pv.to_numpy()]; jp = jp[jp.wt > 0]
    jb = jp.assign(wr=jp.r * jp.wt).groupby('w').agg(wr=('wr', 'sum'), wt=('wt', 'sum'))
    jv = pd.DataFrame({'jev_simple': jj.groupby('w').r.mean(), 'n_pares': jj.groupby('w').r.size()})
    jv = jv.join((jb.wr / jb.wt).rename('jev_pob'), how='outer').join(j.groupby('w').r.mean().rename('jev_sinq'), how='outer')
    jv['item'] = it
    out_jev.append(jv.reset_index())
    cc = df.groupby(['w', 'cd']).agg(p=('p', 'median'), n=('s', 'nunique')).reset_index(); cc['item'] = it
    out_cad.append(cc)
    pr = df.groupby(['w', 'pv']).agg(p=('p', 'median'), n=('s', 'nunique')).reset_index(); pr['item'] = it
    out_prov.append(pr)

nac = pd.concat(out_nac); jev = pd.concat(out_jev); cad = pd.concat(out_cad); prov = pd.concat(out_prov)
for d in (nac, jev, cad, prov):
    d['semana'] = d.w.map(dict(enumerate(WEEKS)))
cad['cadena'] = cad.cd.map(dict(enumerate(CADS))); prov['provincia'] = prov.pv.map(dict(enumerate(PROVS)))
nac.to_parquet(config.TRABAJO / 'rep_nac.parquet'); jev.to_parquet(config.TRABAJO / 'rep_jev.parquet')
cad.to_parquet(config.TRABAJO / 'rep_cad.parquet'); prov.to_parquet(config.TRABAJO / 'rep_prov.parquet')
print('listo', f'{time.time()-t0:.0f}s ->', config.TRABAJO)
