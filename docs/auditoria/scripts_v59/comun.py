# -*- coding: utf-8 -*-
"""Lectura del Excel del nb07 y utilidades compartidas: recetas, indice encadenado, geografia."""
import re, unicodedata
import numpy as np, pandas as pd
import config

X = pd.ExcelFile(config.EXCEL)
pn = pd.read_excel(X, 'Panel_nacional'); pn['item'] = pn['item'].astype(str)
SEM = [c for c in pn.columns if str(c)[:2] == '20']
P = pn.set_index('item')[SEM].astype(float)
DESC = dict(zip(pn['item'], pn['descripcion'].astype(str)))
FRES = set(pd.read_excel(X, 'Cobertura_frescos')['tipo'])
CANASTAS = ['Popular', 'Media', 'Ejecutiva', 'Tecnológica', 'Representativa', 'Femenina']
QUIEBRE_K = 3.0

def receta(c):
    """Receta de la canasta desde Detalle_*: item, qty, rubro, kind."""
    d = pd.read_excel(X, 'Detalle_' + c)
    d['base'] = d['detalle'].astype(str).str.replace(r' \(\$/(kg|doc|docena)\)$', '', regex=True)
    inv = {}
    for it, ds in DESC.items():
        inv.setdefault(ds, it)
    d['item'] = d['base'].map(inv)
    d.loc[d['item'].isna(), 'item'] = d['base'].where(d['base'].isin(P.index))
    return d.dropna(subset=['item'])

def encadenar(V, k=QUIEBRE_K):
    """Indice encadenado de muestra apareada con la regla de quiebre del nb07 v5.9."""
    idx = [1.0]
    for t in range(1, len(V)):
        a = V.iloc[t]; b = V.iloc[t - 1]
        m = a.notna() & b.notna() & (b > 0)
        if k:
            r = a / b; m = m & ~((r > k) | (r < 1 / k))
        den = b[m].sum()
        idx.append(idx[-1] * ((a[m].sum() / den) if (m.any() and den > 0) else 1.0))
    return pd.Series(idx, index=V.index)

def serie_canasta(c, Pm, k=QUIEBRE_K, desde=None, items=None):
    r = receta(c); q = r.set_index('item')['qty']
    its = [i for i in (items if items is not None else q.index) if i in Pm.index]
    V = Pm.loc[its].T.mul(q.reindex(its), axis=1)
    if desde:
        V = V.loc[desde:]
    return encadenar(V, k)

def mes_de_semana(w):
    import datetime as dt
    return (dt.date.fromisoformat(w) - dt.timedelta(days=3)).strftime('%Y-%m')

# ── Geografia de sucursales, identica a la del nb07 (CELDA 4 y CELDA 8) ──────
FILT = {'19', '2013', '3001', '4'}
SK = ['id_comercio', 'id_bandera', 'id_sucursal']
def _sa(s):
    s = ''.join(ch for ch in unicodedata.normalize('NFD', str(s)) if unicodedata.category(ch) != 'Mn')
    return re.sub(r'\s+', ' ', s).strip().lower()
POB = {'buenos aires':17709732,'caba':3075646,'catamarca':415438,'chaco':1204541,'chubut':618994,
       'cordoba':3978984,'corrientes':1120801,'entre rios':1385961,'formosa':605193,'jujuy':770881,
       'la pampa':368550,'la rioja':393531,'mendoza':2014533,'misiones':1261294,'neuquen':664057,
       'rio negro':747610,'salta':1441998,'san juan':781217,'san luis':531745,'santa cruz':333473,
       'santa fe':3556522,'santiago del estero':1019304,'tierra del fuego':190641,'tucuman':1737127}
REGION = {'buenos aires':'Centro/Pampeana','caba':'Centro/Pampeana','cordoba':'Centro/Pampeana','santa fe':'Centro/Pampeana',
          'entre rios':'Centro/Pampeana','la pampa':'Centro/Pampeana','jujuy':'NOA','salta':'NOA','tucuman':'NOA',
          'catamarca':'NOA','la rioja':'NOA','santiago del estero':'NOA','chaco':'NEA','corrientes':'NEA',
          'formosa':'NEA','misiones':'NEA','mendoza':'Cuyo','san juan':'Cuyo','san luis':'Cuyo','neuquen':'Patagonia',
          'rio negro':'Patagonia','chubut':'Patagonia','santa cruz':'Patagonia','tierra del fuego':'Patagonia'}
_NC = {('9','1'):'Vea',('9','2'):'Disco',('9','3'):'Jumbo',('10','1'):'Carrefour',('10','2'):'Carrefour Market',
       ('10','3'):'Carrefour Express',('11','2'):'ChangoMas',('11','4'):'Hiper ChangoMas',('11','5'):'Mi ChangoMas',
       ('16','1'):'Hipermercado Libertad',('16','2'):'Mini Libertad'}
_NS = {'2':'La Anonima','3':'Cadena 3','5':'Hipermercado Misiones','8':'Mariano Max','12':'Coto',
       '13':'Cooperativa Obrera','15':'DIA','20':'LAR','21':'Toledo','23':'Cadena 23','47':'Pasamonte'}

def sucursales():
    ms = pd.read_excel(config.MAESTRO_SUC, dtype={'id_comercio': str, 'id_bandera': str, 'id_sucursal': str})
    ms = ms[ms.sucursales_latitud.between(-55, -22) & ms.sucursales_longitud.between(-73, -53)]
    ms = ms.drop_duplicates(SK).copy()
    ms['cadena'] = [_NC.get((c, b), _NS.get(c, f'Cadena {c}')) for c, b in zip(ms.id_comercio, ms.id_bandera)]
    ms['prov'] = [{'ciudad autonoma de buenos aires': 'caba', 'provincia de buenos aires': 'buenos aires'}.get(_sa(p), _sa(p))
                  for p in ms.PROVINCIA]
    assert set(ms.prov) <= set(POB), sorted(set(ms.prov) - set(POB))
    ms['region'] = ms.prov.map(REGION)
    ms['key'] = ms.id_comercio + '|' + ms.id_bandera + '|' + ms.id_sucursal
    return ms.reset_index(drop=True)
