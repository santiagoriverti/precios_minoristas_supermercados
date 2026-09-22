# -*- coding: utf-8 -*-
"""Paso 4 - Todas las tablas de docs/AUDITORIA_2026-09-22_v59.md, en el orden del informe.

Usa los intermedios de los pasos 1-3 (en AUD_TRABAJO), el Excel (AUD_EXCEL), el cache (AUD_CACHE)
y la planilla del INDEC (AUD_INDEC). Cada seccion se saltea si le falta su insumo.
"""
import datetime as dt
import numpy as np, pandas as pd, pyarrow.parquet as pq
import config
from comun import (X, P, SEM, DESC, FRES, CANASTAS, SK, FILT, POB, receta, encadenar, serie_canasta,
                   mes_de_semana, sucursales)

pd.set_option('display.width', 250); pd.set_option('display.max_colwidth', 50)
T = config.TRABAJO
W0 = ['2024-01-11', '2024-01-18', '2024-01-25']; W1 = ['2026-08-13', '2026-08-20', '2026-08-27']
AUG = ['2026-08-06', '2026-08-13', '2026-08-20', '2026-08-27']
ALIM = ['Popular', 'Media', 'Ejecutiva', 'Representativa']
INDEC_MAP = {'Pan francés': 'Pan francés tipo flauta', 'Asado': 'Asado', 'Carne picada': 'Carne picada común',
             'Paleta': 'Paleta', 'Nalga/Cuadril': 'Nalga', 'Pollo': 'Pollo entero', 'Merluza': 'Filet de merluza fresco',
             'Jamón cocido (kg)': 'Jamón cocido', 'Salame/Salamín': 'Salame', 'Queso cremoso': 'Queso cremoso',
             'Queso barra/Dambo': 'Queso pategrás', 'Queso rallar (sardo/reggianito)': 'Queso sardo',
             'Huevos': 'Huevos de gallina', 'Manzana': 'Manzana deliciosa', 'Limón': 'Limón', 'Naranja': 'Naranja',
             'Banana': 'Banana', 'Batata': 'Batata', 'Papa': 'Papa', 'Cebolla': 'Cebolla', 'Lechuga': 'Lechuga',
             'Tomate': 'Tomate redondo', 'Zapallo': 'Zapallo anco'}
QB = set(pd.read_excel(X, 'Alertas_quiebre')['item'].astype(str))
TZ = set(pd.read_excel(X, 'Alertas_trazabilidad')['item'].astype(str))
PM = pd.read_excel(X, 'Panel_nacional_mes'); PM['item'] = PM['item'].astype(str); PM = PM.set_index('item')

def titulo(t):
    print('\n' + '=' * 100 + '\n' + t + '\n' + '=' * 100)

def leer_indec():
    from importlib import util
    spec = util.spec_from_file_location('aud', config.REPO / 'notebooks' / 'auditar_salida_nb07.py')
    m = util.module_from_spec(spec); spec.loader.exec_module(m)
    return m.leer_indec(config.INDEC)

def geo_mensual(A, col, geo):
    x = A.groupby([geo, 'semana']).agg(v=(col, 'median'), n=('id_sucursal', 'size')).reset_index()
    return x.groupby(geo).agg(v=('v', 'mean'), n=('n', 'max'))

# ── 1. Replicas ────────────────────────────────────────────────────────────────
def s1_replicas():
    titulo('1) REPLICAS: indice semanal (con quiebre x3) y precio nacional de los empaquetados')
    for c in CANASTAS:
        S = pd.read_excel(X, 'Sem_' + c); s = serie_canasta(c, P, desde=S.semana.iloc[0])
        print(f'  {c:15s} dif max {np.abs(s.values / s.iloc[0] * 100 - S.indice_100.values).max():.4f}')
    f = T / 'rep_nac.parquet'
    if not f.exists():
        print('  (sin rep_nac.parquet: correr el paso 1)'); return
    nac = pd.read_parquet(f); nac['item'] = nac['item'].astype(str)
    R = nac.pivot(index='item', columns='semana', values='nac_rep')
    emp = [i for i in P.index if i not in FRES]
    com = [c for c in R.columns if c in P.columns and c <= '2026-08-27']
    A = P.loc[emp, com]; B = R.reindex(emp)[com]
    v = ((A / B - 1).where(A.notna() & B.notna())).stack()
    print(f'  precio nacional, {len(emp)} empaquetados: {len(v):,} celdas | dentro de 0,1%: {(v.abs() < 0.001).mean() * 100:.2f}% '
          f'| mediana |dif| {v.abs().median() * 100:.4f}%')

# ── 2. Empaquetados: encadenado contra directo por sucursal ───────────────────
def s2_empaquetados():
    titulo('2) EMPAQUETADOS: encadenado publicado vs comparacion directa por sucursal (ene-24 -> ago-26)')
    f = T / 'largo_plazo_items.parquet'
    if not f.exists():
        print('  (sin largo_plazo_items.parquet: correr el paso 2)'); return
    L = pd.read_parquet(f)
    print(f"  {'canasta':15s}{'muestra':>14s}{'encadenado':>12s}{'directo':>10s}{'dif %':>8s}   (muestra limpia: sin quiebres, sin huecos, ratio en [1,2; 8])")
    for c in ['Popular', 'Media', 'Ejecutiva', 'Representativa', 'Femenina']:
        r = receta(c); q = r.set_index('item')['qty']; emp = [i for i in q.index if i not in FRES]
        ok = [i for i in emp if i not in QB and i not in TZ and i in L.index and 1.2 <= L.at[i, 'r_med'] <= 8
              and P.loc[i, W0].notna().all() and P.loc[i, W1].notna().all()]
        ch = encadenar(P.loc[ok].T.mul(q.reindex(ok), axis=1))
        g = lambda w: np.exp(np.log(ch[w]).mean())
        v1 = q[ok] * np.exp(P.loc[ok, W1].apply(np.log).mean(axis=1))
        dm = v1.sum() / (v1 / L.loc[ok, 'r_med']).sum()
        print(f'  {c:15s}{len(ok):>8d}/{len(emp):<5d}{g(W1) / g(W0):12.3f}{dm:10.3f}{(g(W1) / g(W0) / dm - 1) * 100:8.1f}')

# ── 3. Frescos contra el INDEC y la muestra fija de EANs ──────────────────────
def s3_frescos_indec():
    titulo('3) FRESCOS: publicado vs INDEC GBA vs muestra fija de EANs (ene-24 -> ago-26)')
    if config.INDEC is None:
        print('  (sin AUD_INDEC)'); return None
    g = leer_indec()
    fx = None
    if config.CACHE is not None:
        eanc = config.carpeta_cache('ean')
        em = lambda m: pq.read_table(eanc / f'{m}.parquet').to_pandas().groupby(['item', 'ean_norm']).agg(p=('p', 'median'), n=('n_suc', 'median')).reset_index()
        ee = em('2024-01').merge(em('2026-08'), on=['item', 'ean_norm'], suffixes=('0', '1'))
        ee = ee[(ee.n0 >= 10) & (ee.n1 >= 10)]
        fx = ee.groupby('item').apply(lambda d: pd.Series({'n_EAN': len(d), 'EANfijo': np.exp(np.average(np.log(d.p1 / d.p0), weights=d.n1))}), include_groups=False)
    rows = []
    for t, v in INDEC_MAP.items():
        rows.append((t, g.at[v, '2026-08'] / g.at[v, '2024-01'], PM.at[t, '2026-08'] / PM.at[t, '2024-01'],
                     fx['EANfijo'].get(t, np.nan) if fx is not None else np.nan, fx['n_EAN'].get(t, 0) if fx is not None else 0,
                     PM.at[t, '2026-08'], g.at[v, '2026-08']))
    D = pd.DataFrame(rows, columns=['tipo', 'INDEC', 'publicado', 'EAN_fijo', 'n_EAN', 'nivel_pub', 'nivel_INDEC']).set_index('tipo')
    D['pub/INDEC'] = D.publicado / D.INDEC; D['nivel pub/INDEC'] = D.nivel_pub / D.nivel_INDEC
    print(D.round(2).to_string())
    print(f"\n  var pub/INDEC: mediana {D['pub/INDEC'].median():.3f} | geo-media {np.exp(np.log(D['pub/INDEC']).mean()):.3f}")
    print('\n  Efecto en el COSTO de ago-26 si esos tipos cotizaran al nivel del INDEC:')
    for c in ALIM:
        q = receta(c).set_index('item')['qty']; tot = (q * PM['2026-08'].reindex(q.index)).sum()
        mal = sum(q.get(t, 0) * (PM.at[t, '2026-08'] - D.at[t, 'nivel_INDEC']) for t in ['Pollo', 'Carne picada', 'Merluza', 'Limón'])
        pan = q.get('Pan francés', 0) * (PM.at['Pan francés', '2026-08'] - D.at['Pan francés', 'nivel_INDEC'])
        print(f'    {c:15s} pollo+picada+merluza+limon {mal / tot * 100:+.1f}% | pan (ancla 6.200) {pan / tot * 100:+.1f}%')
    return D

# ── 4. Sensibilidad del indice de canasta al metodo de frescos ────────────────
def s4_sensibilidad(D):
    titulo('4) SENSIBILIDAD: indice mensual ago-26 (ene-24 = 100) segun el metodo de los frescos')
    fin = '2026-08-27'; weeks = [w for w in SEM if w <= fin]
    alts = {'publicado': P[weeks]}
    f = T / 'tpd_series.parquet'
    if f.exists():
        S = pd.read_parquet(f)
        for col, nom in (('tpd_w', 'TPD ponderado'), ('tpd_u', 'TPD simple')):
            Pa = P[weeks].copy()
            for t in S.index.get_level_values(0).unique():
                if t in Pa.index and P.at[t, fin] == P.at[t, fin]:
                    s = S.loc[t][col].reindex(weeks)
                    if s.notna().sum() >= 2:
                        Pa.loc[t] = (P.at[t, fin] * s / s[fin]).values
            alts[nom] = Pa.where(P[weeks].notna())
    print(f"  {'canasta':15s}" + ''.join(f'{k:>16s}' for k in alts) + '   (sin la semana 2026-09-03: comparar entre columnas)')
    for c in ALIM:
        out = []
        for Pm in alts.values():
            s = serie_canasta(c, Pm); m = s.groupby([mes_de_semana(w) for w in s.index]).mean()
            out.append(m['2026-08'] / m['2024-01'] * 100)
        print(f'  {c:15s}' + ''.join(f'{v:16.1f}' for v in out))
    if D is not None:
        print('\n  Laspeyres directo (precios mensuales) con los frescos mapeados siguiendo al INDEC:')
        for c in ALIM:
            q = receta(c).set_index('item')['qty']; its = [i for i in q.index if PM.at[i, '2026-08'] == PM.at[i, '2026-08'] and PM.at[i, '2024-01'] == PM.at[i, '2024-01']]
            p1 = PM.loc[its, '2026-08']; p0 = PM.loc[its, '2024-01'].copy(); v1 = q[its] * p1
            base = v1.sum() / (q[its] * p0).sum()
            for t in D.index:
                if t in its:
                    p0[t] = p1[t] / D.at[t, 'INDEC']
            print(f'    {c:15s} publicado x{base:.3f} -> frescos como el INDEC x{v1.sum() / (q[its] * p0).sum():.3f} ({(v1.sum() / (q[its] * p0).sum() / base - 1) * 100:+.1f}%)')

# ── 5. BUG-37 medido sobre agosto ──────────────────────────────────────────────
def s5_bug37():
    titulo('5) BUG-37: costo por sucursal de ago-26, formula v5.9 contra corregida (x el nacional)')
    if config.CACHE is None:
        print('  (sin AUD_CACHE)'); return
    semc = config.carpeta_cache('sem')
    d = pd.concat([pq.read_table(semc / f'{m}.parquet').to_pandas() for m in ('2026-07', '2026-08')])
    d = d[d.semana.isin(AUG) & ~d.id_comercio.isin(FILT)].groupby(SK + ['item', 'semana'], as_index=False).price.median()
    nac = P[AUG].reset_index().melt(id_vars='item', var_name='semana', value_name='nac').dropna()
    geo = sucursales()[SK + ['cadena', 'prov', 'region']]
    for c in ['Popular', 'Media', 'Representativa', 'Tecnológica']:
        rec = receta(c)[['item', 'qty', 'rubro', 'kind']]; n_emp = int((rec.kind == 'emp').sum())
        av = nac.merge(rec, on='item'); av['val'] = av.nac * av.qty
        allr = av.groupby(['semana', 'rubro'], as_index=False).val.sum().rename(columns={'val': 'val_all'})
        tot = av.groupby('semana').val.sum().rename('tot_nac')
        pv = d.merge(rec, on='item').merge(nac, on=['item', 'semana'], how='left')
        pv['sv'] = pv.price * pv.qty; pv['nv'] = pv.nac * pv.qty; pv['ie'] = (pv.kind == 'emp').astype(int)
        g = pv.groupby(SK + ['semana', 'rubro']).agg(S=('sv', 'sum'), N=('nv', 'sum'), nemp=('ie', 'sum')).reset_index().merge(allr, on=['semana', 'rubro'], how='left')
        g['costo'] = g.S + (g.val_all.fillna(0) - g.N.fillna(0))
        cov = g.groupby(SK + ['semana']).nemp.sum().reset_index(); cov = cov[cov.nemp / n_emp >= 0.8]
        g = g.merge(cov[SK + ['semana']], on=SK + ['semana'])
        A = g.groupby(SK + ['semana']).agg(costo=('costo', 'sum'), S=('S', 'sum'), N=('N', 'sum'), nrub=('rubro', 'nunique')).reset_index().merge(tot, on='semana')
        A['corr'] = A.tot_nac + (A.S - A.N); A = A.merge(geo, on=SK, how='left'); nt = tot.mean()
        print(f'\n  --- {c} (nacional ${nt:,.0f}, {rec.rubro.nunique()} rubros)')
        for geo_ in ('cadena', 'region'):
            a = geo_mensual(A, 'costo', geo_).rename(columns={'v': 'v59'}).join(geo_mensual(A, 'corr', geo_)[['v']].rename(columns={'v': 'corr'}))
            if geo_ == 'cadena':
                a = a.join(A.groupby('cadena').nrub.median().rename('rubros'))
            a = a[a.n >= 30]
            print(f'  {geo_:7s}: ' + ' | '.join(f'{i} {r.v59 / nt:.2f}->{r["corr"] / nt:.2f}' + (f' ({int(r.rubros)} rub.)' if geo_ == 'cadena' else '')
                                          for i, r in a.sort_values('v59').iterrows()))

# ── 6. DIA en el precio nacional ───────────────────────────────────────────────
def s6_dia():
    titulo('6) DIA: parte del costo nacional donde la mediana provincial ES el precio de DIA (sem 2026-08-20)')
    if config.CACHE is None:
        print('  (sin AUD_CACHE)'); return
    d = pq.read_table(config.carpeta_cache('sem') / '2026-08.parquet').to_pandas()
    d = d[d.semana == '2026-08-20'].merge(sucursales()[SK + ['cadena', 'prov']], on=SK)
    g = d.groupby(['item', 'prov']).agg(med=('price', 'median'), n=('price', 'size'), n_dia=('cadena', lambda s: (s == 'DIA').sum())).reset_index()
    g = g.join(d[d.cadena == 'DIA'].groupby(['item', 'prov']).price.median().rename('p_dia'), on=['item', 'prov']); g = g[g.n >= 3]
    g['es_dia'] = g.p_dia.notna() & ((g.med / g.p_dia - 1).abs() < 0.005) & (g.n_dia / g.n > 0.5)
    g['w'] = g.prov.map(POB)
    for c in ['Popular', 'Media', 'Representativa']:
        q = receta(c).set_index('item')['qty']; x = g[g.item.isin(q.index)].copy()
        x['wn'] = x.w / x.groupby('item').w.transform('sum') * x.item.map(q) * x.item.map(P['2026-08-20'])
        print(f'  {c:15s} {x.wn[x.es_dia].sum() / x.wn.sum() * 100:5.1f}%')
    r = receta('Representativa'); x = g[g.item.isin(set(r['item']))]
    print('  DIA en las sucursales con dato:', ' | '.join(f'{p} {v:.0f}%' for p, v in (x.groupby('prov').apply(lambda s: (s.n_dia / s.n).median(), include_groups=False) * 100).sort_values(ascending=False).head(6).items()))
    f = T / 'rep_cad.parquet'
    if f.exists():
        cad = pd.read_parquet(f); cad['item'] = cad['item'].astype(str)
        weeks = [w for w in SEM if w <= '2026-08-27']
        print('\n  Indice de empaquetados limpios por cadena, ene-24 -> ago-26 (subconjunto que publica cada cadena):')
        for c in ['Popular', 'Media', 'Representativa']:
            r = receta(c); q = r.set_index('item')['qty']; emp = [i for i in q.index if i not in FRES and i not in QB and i not in TZ]
            ch = encadenar(P.loc[emp, weeks].T.mul(q.reindex(emp), axis=1)); gg = lambda s, w: np.exp(np.log(s[w]).mean())
            out = [f'NACIONAL x{gg(ch, W1) / gg(ch, W0):.3f}']
            for k in ['DIA', 'Coto', 'Carrefour', 'La Anonima', 'Vea', 'Disco']:
                xk = cad[cad.cadena == k].pivot(index='semana', columns='item', values='p').reindex(weeks)
                its = [i for i in emp if i in xk.columns and xk[i].loc[W0].notna().all() and xk[i].loc[W1].notna().all()]
                if len(its) >= 0.5 * len(emp):
                    ck = encadenar(xk[its].mul(q.reindex(its), axis=1).ffill(limit=8)); out.append(f'{k} x{gg(ck, W1) / gg(ck, W0):.3f}')
            print(f'    {c:15s} ' + ' | '.join(out))

# ── 7. Composicion ─────────────────────────────────────────────────────────────
def s7_composicion():
    titulo('7) COMPOSICION: pañales, mascotas, alcohol; solo alimentos contra el IPC de alimentos')
    NOALIM = ['Limpieza', 'Perfumería', 'Bebés Y Mamás', 'Mascotas']
    ALC = 'Cerveza|Vino|Fernet|Aperitivo|Whisky|Espumante|Sidra|Vodka|Gin'
    ipc = pd.read_excel(X, 'vsIPC_Popular').set_index('mes')
    ipc_al = ipc.at['2026-08', 'ipc_alimentos'] / ipc.at['2024-01', 'ipc_alimentos'] * 100
    for c in ALIM:
        d = pd.read_excel(X, 'Detalle_' + c); tot = d.costo.sum()
        sh = lambda m: d.loc[m, 'costo'].sum() / tot * 100
        r = receta(c); q = r.set_index('item')['qty']
        food = [i for i, rb, ds in zip(r['item'], r['rubro'], r['detalle']) if rb not in NOALIM and not pd.Series([ds]).str.contains(ALC, case=False).iloc[0]]
        def idx(its):
            s = serie_canasta(c, P, items=its); m = s.groupby([mes_de_semana(w) for w in s.index]).mean()
            return m['2026-08'] / m['2024-01'] * 100
        print(f'  {c:15s} pañales/toallitas {sh(d.rubro == "Bebés Y Mamás"):4.1f}% | mascotas {sh(d.rubro == "Mascotas"):4.1f}% | '
              f'alcohol {sh(d.detalle.str.contains(ALC, case=False)):4.1f}% || indice completo {idx(list(q.index)):6.1f} | '
              f'solo alimentos {idx(food):6.1f} | IPC alimentos {ipc_al:6.1f}')

if __name__ == '__main__':
    s1_replicas(); s2_empaquetados(); D = s3_frescos_indec(); s4_sensibilidad(D); s5_bug37(); s6_dia(); s7_composicion()
