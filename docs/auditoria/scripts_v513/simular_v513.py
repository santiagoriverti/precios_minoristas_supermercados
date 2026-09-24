# -*- coding: utf-8 -*-
"""Simula la nb07 v5.13 sobre el cache de una corrida anterior (sin releer el SEPA) y estima el indice de cada canasta.

Corre el codigo REAL de notebooks/gen_nb07.py -el bloque 2b de la CELDA 8: indice TPD de los frescos y su nivel-
sobre:
  - el panel por EAN de los frescos (ean_<clave>_v5/);
  - el estimador nacional de cada fresco, replicado desde los precios por sucursal (sem_<clave>_v5/): mediana por
    provincia con >= 3 sucursales, winsor 2,5 entre provincias y promedio ponderado por poblacion (CELDA 8, bloque 1);
  - la cobertura por tipo y semana (sucursales con precio), que decide el nivel fuera de temporada.
A los empaquetados les aplica la cobertura minima de la v5.13 (misma formula que el bloque 1b, sin arrastre). Las
anclas de NIVEL_REFERENCIA_FRESCO quedan en el nivel publicado. Cantidades de empaquetados: el cargador vigente
(docs/canastas_alternativas/cargar_canastas_v5.py); de frescos, las de la corrida (hojas Detalle_*). Los parametros
se leen de gen_nb07.py, asi que la simulacion sigue al generador.

    set AUD_EXCEL=...\\canastas_alternativas_2026-09-24.xlsx   (salida del nb07 de la corrida cuyo cache se usa)
    set AUD_CACHE=...\\_cache_nb07                              (con sem_<clave>_v5 y ean_<clave>_v5 adentro)
    python simular_v513.py [--mes 2026-08]

Referencia (2026-09-24, cache de la v5.12 f32678cd, ene-24 -> ago-26): Popular 242,8 · Media 247,6 · Ejecutiva 243,3 ·
Representativa 239,2 · Femenina 258,7 · Tecnologica 111,9 (jun-25 = 100). Tarda ~4 minutos.
"""
import argparse, ast, datetime as _dt, io, os, re, sys, time
import numpy as np, pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, '..', 'scripts_v59'))
import config                                   # noqa: E402  (rutas por variables de entorno)
import comun as cm                              # noqa: E402

REPO = str(config.REPO)
SRC = io.open(os.path.join(REPO, 'notebooks', 'gen_nb07.py'), encoding='utf-8').read()


def param(nombre):
    """Valor de una constante de la CELDA 1 de gen_nb07.py (NOMBRE = valor)."""
    m = re.search(r'^' + nombre + r'\s*=\s*(.+?)\s*(#.*)?$', SRC, re.M)
    if not m:
        sys.exit(f'No encuentro {nombre} en gen_nb07.py')
    return ast.literal_eval(m.group(1))


def dict_literal(nombre):
    i = SRC.index(nombre + ' = {'); j = SRC.index('\n}\n', i) + 2
    return ast.literal_eval(SRC[i + len(nombre) + 3:j])


def cantidades_cargador():
    t = io.open(os.path.join(REPO, 'docs', 'canastas_alternativas', 'cargar_canastas_v5.py'), encoding='utf-8').read()
    i = t.index('CANTIDADES = {'); j = t.index('\n}\n', i) + 2
    return ast.literal_eval(t[i + len('CANTIDADES = '):j])


def leer_cache(sem_dir, fres):
    """Una pasada por sem_<clave>_v5: sucursales por empaquetado-semana, y precios de los frescos por provincia."""
    ms = cm.sucursales(); prov = dict(zip(ms['key'], ms['prov']))
    n_emp, fr = [], []
    for f in sorted(os.listdir(sem_dir)):
        x = pd.read_parquet(os.path.join(sem_dir, f))
        x['key'] = x['id_comercio'] + '|' + x['id_bandera'] + '|' + x['id_sucursal']
        e = x[~x['item'].isin(fres)]
        n_emp.append(e[['item', 'semana', 'key']].drop_duplicates())
        g = x[x['item'].isin(fres)].copy()
        g['prov'] = g['key'].map(prov)
        fr.append(g.dropna(subset=['prov'])[['item', 'semana', 'prov', 'key', 'price']])
        print(f'  {f}', end='\r')
    n_emp = pd.concat(n_emp, ignore_index=True).drop_duplicates().groupby(['item', 'semana'])['key'].nunique().unstack('item')
    X = pd.concat(fr, ignore_index=True).groupby(['item', 'semana', 'prov', 'key'], as_index=False)['price'].median()
    return n_emp, X


def estimador_frescos(X):
    cob = X.groupby(['item', 'semana'])['key'].nunique().unstack('item')
    pm = X.groupby(['item', 'semana', 'prov']).agg(p=('price', 'median'), n=('price', 'size')).reset_index()
    pm = pm[pm['n'] >= param('MIN_SUC_PROV_ITEM')]
    pm['med'] = pm.groupby(['item', 'semana'])['p'].transform('median')
    k = param('PROV_OUTLIER_K')
    pm = pm[(pm['p'] >= pm['med'] / k) & (pm['p'] <= pm['med'] * k)]
    pm['w'] = pm['prov'].map(cm.POB); pm['pw'] = pm['p'] * pm['w']
    g = pm.groupby(['item', 'semana'])[['pw', 'w']].sum()
    return (g['pw'] / g['w']).unstack('item'), cob


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--mes', default=None, help='mes a comparar (default: el de NIVEL_REFERENCIA_FRESCO)')
    a = ap.parse_args()
    t0 = time.time()
    NIV = dict_literal('NIVEL_REFERENCIA_FRESCO')
    ref = a.mes or max({v[1] for v in NIV.values()}, key=lambda m: sum(v[1] == m for v in NIV.values()))
    SEM = cm.SEM; MES = pd.Series([cm.mes_de_semana(w) for w in SEM], index=SEM)
    P0 = cm.P.copy(); fr = sorted(cm.FRES & set(P0.index))
    print(f'Corrida: {config.EXCEL.name} | {len(SEM)} semanas | mes de nivel y de comparacion: {ref}')

    print('Leyendo el cache...')
    n_emp, X = leer_cache(config.carpeta_cache('sem'), set(fr))
    est, cob = estimador_frescos(X)
    ea = config.carpeta_cache('ean')
    E = pd.concat([pd.read_parquet(os.path.join(ea, f)) for f in sorted(os.listdir(ea))], ignore_index=True)
    E['pn'] = E['p'] * E['n_suc']
    E = E.groupby(['item', 'ean_norm', 'semana'], as_index=False).agg(pn=('pn', 'sum'), n_suc=('n_suc', 'sum'))
    E['p'] = E['pn'] / E['n_suc']

    # ── empaquetados: cobertura minima (formula del bloque 1b), sin arrastre ──
    N = n_emp.reindex(index=SEM)
    emp = [i for i in P0.index if i not in fr and i in N.columns]
    tip = N[emp].apply(lambda s: s.dropna().iloc[-26:].median() if s.notna().any() else np.nan)
    umb = np.minimum(float(param('MIN_SUC_ITEM_SEMANA')), param('FRAC_SUC_ITEM_TIPICA') * tip)
    flaco = N[emp].lt(umb, axis=1).T & P0.loc[emp].notna()
    P1 = P0.copy(); P1.loc[emp] = P1.loc[emp].mask(flaco)
    print(f'Cobertura minima: {int(flaco.values.sum()):,} celdas de empaquetados faltantes '
          f'({100 * flaco.values.sum() / max(P0.loc[emp].notna().values.sum(), 1):.1f}%)')

    # ── frescos: bloque 2b REAL ──
    B2 = SRC[SRC.index('# ── 2b. Frescos: la FORMA de la serie sale de un indice por EAN'):
             SRC.index('# ── Banda de plausibilidad POR TIPO')]
    ns = dict(np=np, pd=pd, _dt=_dt)
    exec(SRC[SRC.index('def _mes_de_semana('):SRC.index('\ndef _sem_anterior(')], ns)
    for c in ['FRESCO_NAC_ENCADENADO', 'FRESCO_EAN_MIN_SUC', 'FRESCO_MIN_EANS_PAR', 'FRESCO_MAX_HUECO_PAR',
              'FRESCO_ESLABON_K', 'FRESCO_METODO', 'FRESCO_TPD_VENTANA', 'FRESCO_TPD_ITER', 'FRESCO_NIVEL_MESES',
              'FRESCO_NIVEL_COB_MIN']:
        ns[c] = param(c)
    nw = est.reindex(index=SEM)[fr].copy(); nw.index.name = 'semana'
    ns.update(ean_nac=E[['item', 'ean_norm', 'semana', 'p', 'n_suc']], nac_wide=nw, FRESCO_INFO={t: {} for t in fr},
              FRESCO_EXPORTAR_METODOS=False, FRESCO_NIVEL_MES=ref, NIVEL_REFERENCIA_FRESCO=NIV,
              _nsuc_is=cob.reindex(index=SEM))
    exec(B2, ns)
    F = ns['nac_wide']
    en_ref = [w for w in SEM if MES[w] == ref]
    for t in NIV:
        if t in F.columns and t in P0.index:
            F[t] = F[t] * (P0.loc[t, en_ref].mean() / F.loc[en_ref, t].mean())
    for t in fr:
        P1.loc[t] = F[t].reindex(SEM).values
    d = pd.DataFrame({'v513': F.loc[en_ref].mean(), 'publicado': P0.loc[fr, en_ref].mean(axis=1)})
    d['cambio'] = d['v513'] / d['publicado']
    d = d.sort_values('cambio')
    print('Nivel de los frescos en ' + ref + ' (v5.13 / publicado), los extremos: '
          + ', '.join(f'{t} x{r:.2f}' for t, r in pd.concat([d['cambio'].head(4), d['cambio'].tail(3)]).items()))

    # ── canastas: indice encadenado con la regla de arranque del nb07 ──
    Q = cantidades_cargador()
    COL = {'Popular': 'cantidad_01', 'Media': 'cantidad_02', 'Ejecutiva': 'cantidad_03', 'Tecnológica': 'cantidad_04',
           'Representativa': 'cantidad_05', 'Femenina': 'cantidad_06'}
    cmin = param('COBERTURA_MIN_INDICE'); k = param('QUIEBRE_ITEM_K')
    ant = (pd.Period(ref, 'M') - 12).strftime('%Y-%m'); prev = (pd.Period(ref, 'M') - 1).strftime('%Y-%m')

    def indice(P, q):
        its = [x for x in q.index if x in P.index and q[x] > 0]
        V = P.loc[its].T.mul(q.reindex(its), axis=1)
        cov = V.notna().sum(axis=1) / len(its)
        ok = cov[cov >= cmin].index
        V = V.loc[ok[0]:] if len(ok) else V
        s = cm.encadenar(V, k); m = s.groupby(MES.reindex(s.index)).mean()
        base = MES[V.index[0]]
        return (m[ref] / m[base] * 100, (m[ref] / m[ant] - 1) * 100 if ant in m else np.nan,
                (m[ref] / m[prev] - 1) * 100, base)

    filas = []
    for c, col in COL.items():
        q0 = cm.receta(c).set_index('item')['qty']
        q1 = pd.concat([q0[[i in fr for i in q0.index]], pd.Series({e: v[col] for e, v in Q.items() if v[col] > 0})])
        a0 = indice(P0, q0); a1 = indice(P1, q1)
        filas.append({'canasta': c, 'base': a0[3], 'publicado': round(a0[0], 1), 'v5.13': round(a1[0], 1),
                      f'i.a. {ref} pub': round(a0[1], 1), f'i.a. {ref} v5.13': round(a1[1], 1),
                      'm/m pub': round(a0[2], 1), 'm/m v5.13': round(a1[2], 1)})
    pd.set_option('display.width', 200)
    print(f'\nIndice {ref} (base = primer mes con cobertura >= {cmin:.0%}, 100):')
    print(pd.DataFrame(filas).to_string(index=False))
    print(f'\n({time.time() - t0:.0f} s)')


if __name__ == '__main__':
    main()
