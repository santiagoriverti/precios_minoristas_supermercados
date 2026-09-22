# -*- coding: utf-8 -*-
"""Paso 3 - Indice multilateral Time-Product-Dummy (TPD) por tipo fresco y replica del encadenado.

Sobre el panel POR EAN del cache (`ean_<key>_v5/<mes>.parquet`, EANs con >=10 sucursales):
  - TPD ponderado por sucursales y TPD simple: log p(e,t) = a(t) + g(e), resuelto por proyecciones
    alternadas. Es el estandar internacional para datos de escaner: no acumula deriva de cadena.
  - replica del encadenado semanal del nb07 (media geometrica recortada de EANs apareados, clip
    x2,5, >=2 EANs, hueco max 8 semanas) para verificar que la serie publicada es la que dice ser.
Escribe tpd_frescos.parquet (resumen por tipo) y tpd_series.parquet (series semanales).
"""
import numpy as np, pandas as pd, pyarrow.parquet as pq
import config
from comun import P

E = pd.concat([pq.read_table(f).to_pandas() for f in sorted(config.carpeta_cache('ean').glob('*.parquet'))])
E = E.groupby(['item', 'ean_norm', 'semana'], as_index=False).agg(p=('p', 'median'), n_suc=('n_suc', 'sum'))
E = E[E.n_suc >= 10]
WEEKS = [w for w in sorted(E.semana.unique()) if w <= '2026-08-27']
E = E[E.semana.isin(WEEKS)]
wi = {w: i for i, w in enumerate(WEEKS)}

def tpd(d, pesos=True, it=200):
    t = d.semana.map(wi).to_numpy(); e = pd.factorize(d.ean_norm)[0]
    y = np.log(d.p.to_numpy()); w = d.n_suc.to_numpy(float) if pesos else np.ones(len(d))
    a = np.zeros(len(WEEKS)); g = np.zeros(e.max() + 1)
    for _ in range(it):
        g = np.bincount(e, w * (y - a[t]), minlength=len(g)) / np.bincount(e, w, minlength=len(g))
        num = np.bincount(t, w * (y - g[e]), minlength=len(WEEKS)); den = np.bincount(t, w, minlength=len(WEEKS))
        a_new = pd.Series(np.where(den > 0, num / np.where(den > 0, den, 1), np.nan)).ffill().bfill().to_numpy()
        if np.nanmax(np.abs(a_new - a)) < 1e-9:
            a = a_new; break
        a = a_new
    return pd.Series(np.exp(a - a[0]), index=WEEKS)

def cadena_nb07(d, k=2.5, min_par=2, hueco=8):
    W = d.pivot_table(index='semana', columns='ean_norm', values='p', aggfunc='median').reindex(WEEKS)
    idx = pd.Series(np.nan, index=WEEKS); prev = None; lvl = 1.0
    for s in WEEKS:
        f = W.loc[s]
        if f.notna().sum() == 0:
            continue
        if prev is None or WEEKS.index(s) - WEEKS.index(prev) > hueco:
            if f.notna().sum() < min_par:
                continue
            idx[s] = lvl; prev = s; continue
        a, b = W.loc[prev], f; par = a.notna() & b.notna()
        if par.sum() < min_par:
            continue
        lr = np.log((b[par] / a[par]).astype(float)).to_numpy()
        lvl *= float(np.exp(np.clip(lr, -np.log(k), np.log(k)).mean()))
        idx[s] = lvl; prev = s
    return idx / idx.dropna().iloc[0]

rows, series = [], {}
for t, d in E.groupby('item'):
    a = tpd(d); b = tpd(d, pesos=False); c = cadena_nb07(d)
    series[t] = pd.DataFrame({'tpd_w': a, 'tpd_u': b, 'cadena': c})
    f = lambda s: s.dropna().iloc[-1] / s.dropna().iloc[0]
    pub = P.loc[t, '2026-08-27'] / P.loc[t, '2024-01-04'] if t in P.index else np.nan
    rows.append((t, d.ean_norm.nunique(), f(a), f(b), f(c), pub))
R = pd.DataFrame(rows, columns=['tipo', 'n_EAN', 'TPD_pond', 'TPD_simple', 'cadena_replica', 'publicado']).set_index('tipo')
R.to_parquet(config.TRABAJO / 'tpd_frescos.parquet')
pd.concat(series, names=['tipo', 'semana']).to_parquet(config.TRABAJO / 'tpd_series.parquet')
print(R.round(2).sort_values('publicado').to_string())
print('\ntipos con la replica identica a lo publicado (dif < 0,5%):',
      int(((R.cadena_replica / R.publicado - 1).abs() < 0.005).sum()), 'de', len(R))
print('mediana publicado/TPD_pond:', round(float((R.publicado / R.TPD_pond).median()), 3))
