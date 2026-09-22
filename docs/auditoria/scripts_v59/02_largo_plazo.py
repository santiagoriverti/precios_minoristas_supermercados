# -*- coding: utf-8 -*-
"""Paso 2 - Comparacion DIRECTA de largo plazo por sucursal apareada.

Ventanas: ene-2024 (semanas 11, 18 y 25) contra ago-2026 (semanas 13, 20 y 27). Para cada item y
cada sucursal presente en las dos: ratio de precio (promedio geometrico de cada ventana). Resumen
robusto por item: mediana entre sucursales (inmune a la rigidez semanal de los precios y a las
sucursales "zombi" que nunca actualizan) y mediana provincial ponderada por poblacion.
Escribe largo_plazo_items.parquet en AUD_TRABAJO.

Limite conocido: en ene-2024 algunos EANs cotizan con error de escala en TODAS las sucursales que
los publican (Arroz Largo Fino Molinos Ala 1 kg a $124 en ChangoMas, 1/10 del mercado). Ahi este
control tambien se contamina: por eso el paso 4 los excluye antes de comparar.
"""
import numpy as np, pandas as pd, pyarrow.parquet as pq
import config
from comun import P, DESC, FRES, FILT, POB, sucursales

W0 = ['2024-01-11', '2024-01-18', '2024-01-25']
W1 = ['2026-08-13', '2026-08-20', '2026-08-27']
SEMC = config.carpeta_cache('sem')

def ventana(mes, weeks):
    d = pq.read_table(SEMC / f'{mes}.parquet').to_pandas()
    d = d[d.semana.isin(weeks) & ~d.id_comercio.isin(FILT)]
    d['key'] = d.id_comercio + '|' + d.id_bandera + '|' + d.id_sucursal
    d['lp'] = np.log(d.price)
    return d.groupby(['item', 'key']).lp.mean()

a = ventana('2024-01', W0); b = ventana('2026-08', W1)
j = pd.concat([a.rename('lp0'), b.rename('lp1')], axis=1, join='inner').reset_index()
j['r'] = np.exp(j.lp1 - j.lp0)
j = j.merge(sucursales()[['key', 'prov', 'cadena']], on='key', how='left')
j['w'] = j.prov.map(POB).fillna(0)

def med_pob(g):
    pv = g.groupby('prov').agg(r=('r', 'median'), n=('r', 'size'), w=('w', 'first'))
    pv = pv[(pv.n >= 3) & (pv.w > 0)]
    return np.nan if pv.empty else float(np.exp(np.average(np.log(pv.r), weights=pv.w)))

rows = [(it, len(g), g.r.median(), med_pob(g)) for it, g in j.groupby('item')]
L = pd.DataFrame(rows, columns=['item', 'n_suc', 'r_med', 'r_pob']).set_index('item')
L['r_pub'] = np.exp(P[W1].apply(np.log).mean(axis=1) - P[W0].apply(np.log).mean(axis=1)).reindex(L.index)
L['desc'] = [DESC.get(i, i)[:44] for i in L.index]; L['fresco'] = [i in FRES for i in L.index]
L.to_parquet(config.TRABAJO / 'largo_plazo_items.parquet')
print('pares sucursal-item en ambas ventanas:', len(j), '| items:', len(L))
