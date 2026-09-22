# -*- coding: utf-8 -*-
"""Auditoria de una salida del nb07 (canastas_alternativas_YYYY-MM-DD.xlsx).

Reproduce los chequeos de la auditoria del 2026-09-22 (docs/AUDITORIA_2026-09-22.md). Corre con el
Excel solo; si ademas se le pasa la carpeta del cache por mes, agrega la replica del precio nacional
y el indice de muestra fija por EAN, que son los dos controles mas fuertes.

    python auditar_salida_nb07.py canastas_alternativas_2026-09-17.xlsx
    python auditar_salida_nb07.py canastas.xlsx --cache C:/.../output_canasta_alternativa/_cache_nb07

Cada bloque imprime OK o REVISAR. REVISAR no significa que este mal: significa que hay que mirarlo
antes de publicar. Al final resume cuantos bloques quedaron para revisar.

Que NO hace: no recalcula el SEPA ni valida el maestro. Audita la salida, no la lectura.
"""
import argparse, pathlib, re, sys
import numpy as np, pandas as pd

QUIEBRE_K = 3.0        # factor a partir del cual una variacion semanal es imposible (ver BUG-36)
SALTO_GRANDE = 4.0     # % de variacion semanal de la canasta que se reporta con su atribucion
TRAZA_MIN = 85.0       # % de meses con dato por debajo del cual un item esta marcado
IPC_NOTA = 'IPC del INDEC: sale a mediados del mes siguiente, por eso la canasta suele tener un mes mas.'

RES = []
def bloque(titulo):
    print('\n' + '=' * 100); print(titulo); print('=' * 100)
def veredicto(ok, msg):
    RES.append(bool(ok)); print(('  OK       ' if ok else '  REVISAR  ') + msg)


# ── Lectura del Excel ─────────────────────────────────────────────────────────
def hoja(x, pre, canasta):
    """Las hojas se truncan a 31 caracteres y llevan acentos: matchea por prefijo."""
    c = [s for s in x.sheet_names if s.startswith(pre) and s[len(pre):len(pre) + 6] == canasta[:6]]
    return c[0] if c else None

def cargar(path):
    x = pd.ExcelFile(path)
    pn = pd.read_excel(x, 'Panel_nacional')
    sem = [c for c in pn.columns if str(c)[:2] == '20']
    P = pn.set_index('item')[sem].astype(float)
    desc = dict(zip(pn['item'], pn['descripcion'].astype(str)))
    canastas = [s[len('Sem_'):] for s in x.sheet_names if s.startswith('Sem_')]
    # nombre completo de la canasta desde la hoja Resumen (las hojas vienen truncadas)
    try:
        nombres = list(pd.read_excel(x, 'Resumen')['canasta'])
        canastas = [n for n in nombres if any(s.startswith('Sem_') and s[4:10] == n[:6] for s in x.sheet_names)]
    except Exception:
        pass
    return x, P, sem, desc, canastas

def receta(x, canasta, P, desc):
    """Receta de la canasta: item -> cantidad. Los frescos vienen con el sufijo de unidad."""
    d = pd.read_excel(x, hoja(x, 'Detalle_', canasta))
    d['detalle'] = d['detalle'].astype(str)
    d['base'] = d['detalle'].str.replace(r' \(\$/(kg|doc|docena)\)$', '', regex=True)
    inv = {}
    for it, ds in desc.items():
        inv.setdefault(ds, it)
    d['item'] = d['base'].map(inv)
    d.loc[d['item'].isna(), 'item'] = d['base'].where(d['base'].isin(P.index))
    return d.dropna(subset=['item'])

def encadenar(V, tope=None):
    """Indice encadenado de muestra apareada. `tope` saca del eslabon los movimientos imposibles."""
    idx = [100.0]; quiebres = []
    for t in range(1, len(V)):
        a = V.iloc[t]; b = V.iloc[t - 1]
        m = a.notna() & b.notna() & (b > 0)
        if tope:
            r = a / b
            mal = m & ((r > tope) | (r < 1.0 / tope))
            quiebres += [(V.index[t], i, float(r[i])) for i in a.index[mal]]
            m = m & ~mal
        den = b[m].sum()
        idx.append(idx[-1] * ((a[m].sum() / den) if (m.any() and den > 0) else 1.0))
    return pd.Series(idx, index=V.index), quiebres


# ── 1. Replica del indice ─────────────────────────────────────────────────────
def chequear_indice(x, P, desc, canastas):
    bloque('1) REPLICA DEL INDICE Y GRUPO DE CONTROL (empaquetados vs frescos)')
    print(f"{'canasta':16s}{'replica':>10s}{'excel':>10s}{'dif max':>10s}{'EMPAQ':>10s}{'FRESCOS':>10s}")
    datos = {}
    for c in canastas:
        r = receta(x, c, P, desc)
        q = r.set_index('item')['qty']; kind = r.set_index('item')['kind']
        its = [i for i in q.index if i in P.index]
        S = pd.read_excel(x, hoja(x, 'Sem_', c))
        sems = S['semana'].astype(str).tolist()
        V = P.loc[its].T.mul(q.reindex(its), axis=1).loc[sems]
        a, _ = encadenar(V); a = a / a.iloc[0] * 100
        dif = float(np.abs(a.values - S['indice_100'].values).max())
        emp = [i for i in its if kind[i] == 'emp']; fr = [i for i in its if kind[i] == 'fresh']
        ie, _ = encadenar(V[emp]); ie = ie / ie.iloc[0] * 100
        ifr = None
        if fr:
            ifr, _ = encadenar(V[fr]); ifr = ifr / ifr.iloc[0] * 100
        datos[c] = dict(V=V, S=S, q=q, kind=kind, idx=a)
        print(f'{c:16s}{a.iloc[-1]:10.1f}{S["indice_100"].iloc[-1]:10.1f}{dif:10.3f}'
              f'{ie.iloc[-1]:10.1f}' + (f'{ifr.iloc[-1]:10.1f}' if ifr is not None else f'{"-":>10s}'))
        veredicto(dif < 0.01, f'{c}: el indice publicado se reproduce desde el panel (dif {dif:.3f})')
        if ifr is not None:
            br = abs(ie.iloc[-1] - ifr.iloc[-1]) / max(ifr.iloc[-1], 1) * 100
            veredicto(br < 40, f'{c}: empaquetados y frescos no divergen ({br:.0f}% de brecha; >40% = revisar el tratamiento de frescos)')
    return datos


# ── 2. Transiciones imposibles ────────────────────────────────────────────────
def chequear_quiebres(x, P, desc, datos):
    bloque(f'2) TRANSICIONES IMPOSIBLES (item que se mueve x{QUIEBRE_K:g} o mas en una semana)')
    R = P.T / P.T.shift()
    filas = []
    for it in P.index:
        s = R[it]
        for w in s.index[(s > QUIEBRE_K) | (s < 1 / QUIEBRE_K)]:
            if s[w] == s[w]:
                j = list(P.columns).index(w)
                filas.append((desc.get(it, it)[:44], w, round(float(s[w]), 2),
                              round(float(P.loc[it, P.columns[j - 1]]), 1), round(float(P.loc[it, w]), 1)))
    b = pd.DataFrame(filas, columns=['item', 'semana', 'factor', 'antes', 'despues'])
    if len(b):
        print(b.sort_values('semana').to_string(index=False))
    veredicto(len(b) == 0, f'{len(b)} transiciones imposibles en {b["item"].nunique() if len(b) else 0} items '
                           f'(con QUIEBRE_ITEM_K activo deberian ser 0 en el indice; la hoja Alertas_quiebre las lista)')
    if len(b):
        print(f'\n  Efecto en el acumulado si se las saca del eslabon:')
        for c, d in datos.items():
            a = d['idx']; t, _ = encadenar(d['V'], tope=QUIEBRE_K); t = t / t.iloc[0] * 100
            print(f'    {c:16s} {a.iloc[-1]:8.1f} -> {t.iloc[-1]:8.1f}  ({t.iloc[-1]/a.iloc[-1]*100-100:+.1f}%)')


# ── 3. Saltos semanales con atribucion ────────────────────────────────────────
def chequear_saltos(desc, datos):
    bloque(f'3) SEMANAS CON VARIACION MAYOR A {SALTO_GRANDE:g}% Y SU ATRIBUCION')
    recientes = 0
    for c, d in datos.items():
        S = d['S']; V = d['V']
        v = S['var_sem_%'].dropna()
        big = S.reindex(v[v.abs() > SALTO_GRANDE].index)
        print(f"\n--- {c}: {len(big)} semanas | mediana {v.median():+.2f}% | p95 {v.quantile(.95):+.2f}% | max {v.max():+.2f}%")
        for _, row in big.head(6).iterrows():
            w = str(row['semana']); t = list(V.index).index(w)
            a = V.iloc[t]; b = V.iloc[t - 1]; m = a.notna() & b.notna()
            dd = (a[m] - b[m]).sort_values(); base = b[m].sum()
            top = pd.concat([dd.head(2), dd.tail(3)])
            det = ' | '.join(f'{desc.get(i, i)[:24]} {100*dd[i]/base:+.2f}pp' for i in top.index if abs(dd[i]) / base > 0.003)
            print(f"   {w} {row['var_sem_%']:+6.2f}%: {det}")
            if w >= '2025-01-01':
                recientes += 1
    veredicto(recientes == 0, f'{recientes} semanas con variacion >{SALTO_GRANDE:g}% desde 2025 '
                              f'(en 2024 son inflacion real: hubo meses de dos digitos)')


# ── 4. Trazabilidad ───────────────────────────────────────────────────────────
def chequear_trazabilidad(x, P, desc, canastas):
    bloque(f'4) TRAZABILIDAD: peso en el costo de los items con menos de {TRAZA_MIN:g}% de meses con dato')
    try:
        al = pd.read_excel(x, 'Alertas_trazabilidad')
    except Exception:
        print('  (sin hoja Alertas_trazabilidad)'); return
    if 'descripcion' not in al.columns:
        veredicto(True, 'ningun item con huecos'); return
    mal = set(al['descripcion'].astype(str))
    peor = 0.0
    for c in canastas:
        d = pd.read_excel(x, hoja(x, 'Detalle_', c)); tot = d['costo'].sum()
        d['base'] = d['detalle'].astype(str).str.replace(r' \(\$/(kg|doc|docena)\)$', '', regex=True)
        sub = d[d['base'].isin(mal)]
        peso = 100 * sub['costo'].sum() / tot if tot else 0
        peor = max(peor, peso) if c.lower() != 'tecnológica' else peor
        det = ', '.join(f'{r.base[:24]} {100*r.costo/tot:.1f}%' for r in sub.sort_values('costo', ascending=False).head(3).itertuples())
        print(f'{c:16s} {len(sub):2d} items | {peso:5.1f}% del costo' + (f' | {det}' if det else ''))
    veredicto(peor < 5, f'peso maximo de items con huecos fuera de Tecnologica: {peor:.1f}% '
                        f'(>5% = conviene reemplazarlos en el constructor)')


# ── 5. IPC ────────────────────────────────────────────────────────────────────
def chequear_ipc(x, canastas):
    bloque('5) COMPARACION CONTRA EL IPC Y MES PARCIAL')
    print(f'  {IPC_NOTA}')
    parciales = []
    for c in canastas:
        h = hoja(x, 'vsIPC_', c)
        if h is None: continue
        v = pd.read_excel(x, h)
        if 'idx_ipc_gral' not in v.columns: continue
        com = v[v['idx_ipc_gral'].notna() & v['idx_canasta'].notna()]
        if not len(com): continue
        m = com['mes'].iloc[-1]
        extra = '' if m == v['mes'].iloc[-1] else f'  [la canasta llega a {v["mes"].iloc[-1]}: {com["idx_canasta"].iloc[-1]:.0f} -> {v["idx_canasta"].dropna().iloc[-1]:.0f}, sin IPC]'
        alim = f" | IPC alim {com['idx_ipc_alim'].dropna().iloc[-1]:.0f}" if com['idx_ipc_alim'].notna().any() else ''
        print(f"{c:16s} ultimo mes en comun {m}: canasta {com['idx_canasta'].iloc[-1]:.0f} | "
              f"IPC gral {com['idx_ipc_gral'].iloc[-1]:.0f}{alim}{extra}")
        ns = v['n_semanas'].iloc[-1] if 'n_semanas' in v.columns else np.nan
        if ns == ns and int(ns) < 4:
            parciales.append(f'{v["mes"].iloc[-1]} ({int(ns)} semanas)')
    if parciales:
        print(f'\n  MES PARCIAL: {parciales[0]} - es una quincena, no un mes. No comparar contra meses completos.')
    veredicto(True, 'comparacion hecha en el ultimo mes en comun' + (f'; ultimo mes parcial: {parciales[0]}' if parciales else ''))


# ── 6. Frescos ────────────────────────────────────────────────────────────────
def chequear_frescos(x, P):
    bloque('6) FRESCOS: cobertura, huecos y series planas')
    try:
        cf = pd.read_excel(x, 'Cobertura_frescos')
    except Exception:
        print('  (sin hoja Cobertura_frescos)'); return
    filas = []
    n_sem = P.shape[1]
    for t in cf['tipo']:
        if t not in P.index: continue
        s = P.loc[t].dropna()
        mx = cur = 0
        for v in (s.diff() == 0).values[1:]:
            cur = cur + 1 if v else 0; mx = max(mx, cur)
        filas.append((t, len(s), mx, float(s.iloc[-1]) if len(s) else np.nan,
                      int(cf.loc[cf.tipo == t, 'n_sucursales'].iloc[0])))
    d = pd.DataFrame(filas, columns=['tipo', 'semanas', 'max_plana', 'precio_ult', 'n_suc'])
    flojos = d[(d['semanas'] < n_sem * 0.95) | (d['max_plana'] > 8) | (d['n_suc'] < 300)]
    if len(flojos):
        print(flojos.sort_values('semanas').to_string(index=False))
    veredicto(len(flojos) == 0, f'{len(flojos)} tipos con huecos, series planas largas o menos de 300 sucursales '
                                f'(no publicarlos a nivel de item; pesan poco en la canasta)')


# ── 7. Controles con el cache (opcionales) ────────────────────────────────────
def chequear_cache(cache, x, P, desc):
    bloque('7) CONTROLES CON EL CACHE (mediana simple por sucursal e indice de muestra fija por EAN)')
    cache = pathlib.Path(cache)
    dsem = next(iter(sorted(cache.glob('sem_*_v5'))), None)
    dean = next(iter(sorted(cache.glob('ean_*_v5'))), None)
    if dsem is None and dean is None:
        print('  (no encontre carpetas sem_<key>_v5 / ean_<key>_v5 adentro de', cache, ')'); return
    if dsem is not None:
        out = []
        for f in sorted(dsem.glob('*.parquet')):
            dd = pd.read_parquet(f, columns=['semana', 'item', 'price'])
            out.append(dd.groupby(['item', 'semana'], as_index=False)['price'].median())
        m = pd.concat(out, ignore_index=True).groupby(['item', 'semana'], as_index=False)['price'].median()
        M = m.pivot(index='semana', columns='item', values='price').reindex(P.columns)
        com = [c for c in M.columns if c in P.index]
        R = (P.loc[com].T) / M[com]
        ini = R.iloc[:8].median(); fin = R.iloc[-8:].median()
        dr = ((fin / ini - 1) * 100).dropna()
        print(f'  ratio publicado/mediana-simple: inicial {ini.median():.3f} -> final {fin.median():.3f} | '
              f'deriva mediana {dr.median():+.1f}%')
        peor = dr.abs().sort_values(ascending=False).head(6)
        for i in peor.index:
            print(f'    {desc.get(i, i)[:40]:42s} {dr[i]:+8.0f}%')
        veredicto(abs(dr.median()) < 25, f'deriva mediana del panel contra el dato crudo: {dr.median():+.1f}% '
                                         f'(la del encadenado de frescos es esperable; >25% = mirar)')
    if dean is not None:
        E = pd.concat([pd.read_parquet(f) for f in sorted(dean.glob('*.parquet'))], ignore_index=True)
        E = E.groupby(['item', 'ean_norm', 'semana'], as_index=False).agg(p=('p', 'median'), n_suc=('n_suc', 'sum'))
        E = E[E.n_suc >= 10]
        sem = sorted(E['semana'].unique()); ini, fin = sem[0], sem[-1]
        filas = []
        for t, g in E.groupby('item'):
            a = g[g.semana == ini].set_index('ean_norm')['p']; b = g[g.semana == fin].set_index('ean_norm')['p']
            com = a.index.intersection(b.index)
            if len(com) < 3 or t not in P.index: continue
            w = g[g.semana == fin].set_index('ean_norm')['n_suc'].reindex(com)
            lp = np.log((b[com] / a[com]).astype(float))
            fijo = (float(np.exp(np.average(lp, weights=w))) - 1) * 100
            pa, pb = P.loc[t, ini], P.loc[t, fin]
            pub = (pb / pa - 1) * 100 if (pa == pa and pb == pb and pa > 0) else np.nan
            filas.append((t, len(com), fijo, pub))
        d = pd.DataFrame(filas, columns=['tipo', 'EANs', 'muestra_fija_%', 'publicado_%']).dropna()
        if len(d):
            dif = (d['publicado_%'] - d['muestra_fija_%']).median()
            print(f'\n  muestra fija por EAN ({ini} -> {fin}, {len(d)} tipos con 3+ EANs supervivientes):')
            print(f'    publicado mediana {d["publicado_%"].median():+.1f}% | muestra fija {d["muestra_fija_%"].median():+.1f}% | diferencia {dif:+.1f} pp')
            veredicto(abs(dif) < 40, f'el encadenado no se despega de la muestra fija ({dif:+.1f} pp de mediana)')


def main():
    ap = argparse.ArgumentParser(description='Audita una salida del nb07.')
    ap.add_argument('excel', help='canastas_alternativas_YYYY-MM-DD.xlsx')
    ap.add_argument('--cache', help='carpeta _cache_nb07 (opcional: agrega los controles contra el dato crudo)')
    a = ap.parse_args()
    x, P, sem, desc, canastas = cargar(a.excel)
    print(f'Excel: {pathlib.Path(a.excel).name}')
    print(f'Panel: {P.shape[0]} items x {len(sem)} semanas ({sem[0]} -> {sem[-1]}) | canastas: {", ".join(canastas)}')
    datos = chequear_indice(x, P, desc, canastas)
    chequear_quiebres(x, P, desc, datos)
    chequear_saltos(desc, datos)
    chequear_trazabilidad(x, P, desc, canastas)
    chequear_ipc(x, canastas)
    chequear_frescos(x, P)
    if a.cache:
        chequear_cache(a.cache, x, P, desc)
    bloque('RESUMEN')
    malos = len(RES) - sum(RES)
    print(f'  {sum(RES)} chequeos OK | {malos} para revisar')
    print('  Detalle de cada punto y como leerlo: docs/AUDITORIA_2026-09-22.md')
    return 0


if __name__ == '__main__':
    sys.exit(main())
