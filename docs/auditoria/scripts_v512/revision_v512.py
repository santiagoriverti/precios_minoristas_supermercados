# -*- coding: utf-8 -*-
"""Reproduce los numeros de docs/AUDITORIA_2026-09-24_v512.md (revision de la corrida nb07 v5.12).

Variables de entorno:
    AUD_EXCEL        canastas_alternativas_2026-09-24.xlsx (corrida v5.12)
    AUD_EXCEL_PREV   canastas_alternativas_2026-09-17.xlsx (corrida anterior, v5.11.1 con reemplazos)
    AUD_CACHE        carpeta con sem_<clave>_v5 y ean_<clave>_v5 de la v5.12
    AUD_CACHE_PREV   idem de la corrida anterior (para comparar Naranja/Tomate y la revision de niveles)
    AUD_INDEC        data/sh_ipc_precios_promedio_2026-08.xls (por defecto, el del repo)

    python revision_v512.py [seccion ...]      secciones: brecha frescos jackknife flacos deriva estacional niveles

Tarda unos minutos (lee el cache por mes con pyarrow). Usa comun.py de scripts_v59 (receta, encadenado).
"""
import os, re, sys, pathlib
import numpy as np, pandas as pd, pyarrow.parquet as pq

AQUI = pathlib.Path(__file__).resolve().parent
REPO = AQUI.parents[2]
sys.path.insert(0, str(AQUI.parent / 'scripts_v59')); sys.path.insert(0, str(REPO / 'notebooks'))
os.environ.setdefault('AUD_TRABAJO', str(AQUI / '_trabajo'))
import comun as cm                          # noqa: E402 (lee AUD_EXCEL)
import auditar_salida_nb07 as au            # noqa: E402
INDEC = os.environ.get('AUD_INDEC', str(REPO / 'data' / 'sh_ipc_precios_promedio_2026-08.xls'))
CAN = ['Popular', 'Media', 'Ejecutiva', 'Representativa']
NOALIM = ['Limpieza', 'Perfumería', 'Bebés Y Mamás', 'Mascotas']
ALC = 'Cerveza|Vino|Fernet|Aperitivo|Whisky|Espumante|Sidra|Vodka|Gin'
P = cm.P
PM = P.T.groupby([cm.mes_de_semana(w) for w in P.columns]).mean().T
pd.set_option('display.width', 250); pd.set_option('display.max_colwidth', 50)

def carpeta(var, pref):
    c = os.environ.get(var)
    if not c:
        return None
    return next(iter(sorted(pathlib.Path(c).glob(f'{pref}_*_v5'))), None)

def indice(q, items=None, a='2024-01', b='2026-08', Pm=None):
    Pm = P if Pm is None else Pm
    its = [i for i in (items if items is not None else q.index) if i in Pm.index]
    s = cm.encadenar(Pm.loc[its].T.mul(q.reindex(its), axis=1))
    m = s.groupby([cm.mes_de_semana(w) for w in s.index]).mean()
    return m[b] / m[a] * 100

def alimentos(r):
    return [i for i, rb, ds in zip(r['item'], r['rubro'], r['detalle']) if rb not in NOALIM and not re.search(ALC, str(ds), re.I)]

def sucursales_item_semana():
    c = carpeta('AUD_CACHE', 'sem')
    if c is None:
        sys.exit('Esta seccion necesita AUD_CACHE')
    out = []
    for f in sorted(c.glob('*.parquet')):
        d = pq.read_table(f, columns=['id_comercio', 'id_bandera', 'id_sucursal', 'item', 'semana']).to_pandas()
        d = d[d['item'].str.isdigit()].drop_duplicates()
        out.append(d.groupby(['item', 'semana']).size().rename('n').reset_index())
    n = pd.concat(out).groupby(['item', 'semana'])['n'].sum().reset_index()
    return n.pivot(index='item', columns='semana', values='n').reindex(columns=cm.SEM)

# ── 2.1 y 2.2: brecha con el IPC por subperiodo y SEPA vs INDEC por categoria ──────────────────
def brecha():
    v = {c: pd.read_excel(cm.X, 'vsIPC_' + c).set_index('mes') for c in CAN}
    print('== 2.1 variacion % por subperiodo')
    for nom, a, b in [('ene24-dic24', '2024-01', '2024-12'), ('dic24-dic25', '2024-12', '2025-12'), ('dic25-ago26', '2025-12', '2026-08'),
                      ('ago25-ago26', '2025-08', '2026-08'), ('ene24-ago26', '2024-01', '2026-08')]:
        f = [f"{c} {100 * (v[c].at[b, 'indice_100'] / v[c].at[a, 'indice_100'] - 1):+.1f}" for c in CAN]
        ipc = v['Popular']
        print(f"  {nom:12s} " + ' | '.join(f) + f" | IPC alim {100 * (ipc.at[b, 'ipc_alimentos'] / ipc.at[a, 'ipc_alimentos'] - 1):+.1f}"
              f" | IPC gral {100 * (ipc.at[b, 'ipc_general'] / ipc.at[a, 'ipc_general'] - 1):+.1f}")
    I = au.leer_indec(INDEC)
    MAP = {'Aceite de girasol': r'aceite de girasol', 'Azúcar': r'az[uú]car', 'Yerba mate': r'yerba', 'Café molido': r'caf[eé]',
           'Fideos secos tipo guisero': r'fideos|spaghetti|tallar[ií]n', 'Arroz blanco simple': r'\barroz\b', 'Harina de trigo común 000': r'harina de trigo',
           'Leche fresca entera en sachet': r'leche.*(entera|sachet)', 'Manteca': r'manteca', 'Yogur firme': r'yogur', 'Dulce de leche': r'dulce de leche',
           'Pan de mesa': r'pan de mesa|pan lactal|rodajas', 'Galletitas de agua envasadas': r'galletitas? de agua|crackers',
           'Salchicha tipo viena': r'salchicha', 'Hamburguesas congeladas': r'hamburguesa', 'Tomate entero en conserva': r'tomate (entero|perita|triturado)|pur[eé] de tomate',
           'Arvejas secas remojadas': r'arvejas', 'Sal fina': r'\bsal (fina|gruesa)', 'Gaseosa base cola': r'gaseosa cola|coca cola|pepsi|cola classic',
           'Agua sin gas': r'agua (mineral|sin gas)(?!.*sabor)', 'Cerveza en botella': r'cerveza', 'Vino común': r'\bvino\b',
           'Jabón en polvo para ropa': r'jab[oó]n en polvo', 'Detergente líquido': r'detergente', 'Jabón en pan': r'jab[oó]n (en pan|blanco)',
           'Lavandina': r'lavandina', 'Algodón': r'algod[oó]n', 'Champú': r'shampoo|champ[uú]', 'Desodorante': r'desodorante',
           'Jabón de tocador': r'jab[oó]n (de )?tocador', 'Polvo para flan': r'\bflan\b'}
    en_canasta = set().union(*[set(cm.receta(c)['item']) for c in CAN])
    desc = {i: d.lower() for i, d in cm.DESC.items()}
    for a, b in [('2025-01', '2026-08'), ('2024-01', '2026-08')]:
        rat = []
        for var, rx in MAP.items():
            its = [i for i in en_canasta if str(i).isdigit() and re.search(rx, desc.get(i, ''))]
            r = (PM.loc[its, b] / PM.loc[its, a]).replace([np.inf, -np.inf], np.nan).dropna()
            if var in I.index and len(r):
                rat.append((var, float(np.exp(np.log(r).mean())) / (I.at[var, b] / I.at[var, a])))
        s = pd.Series(dict(rat))
        print(f'== 2.2 SEPA/INDEC por categoria {a} -> {b}: {len(s)} categorias | mediana {s.median():.3f} | geo {np.exp(np.log(s).mean()):.3f}'
              f' | min {s.idxmin()} {s.min():.2f} | max {s.idxmax()} {s.max():.2f}')

# ── 2.3: canasta de solo alimentos con la evolucion del INDEC en los frescos ─────────────────────
def frescos():
    I = au.leer_indec(INDEC)
    v = pd.read_excel(cm.X, 'vsIPC_Popular').set_index('mes')
    for a, b in [('2024-01', '2026-08'), ('2025-01', '2026-08'), ('2025-08', '2026-08')]:
        print(f"== 2.3 {a} -> {b} | IPC alimentos {v.at[b, 'ipc_alimentos'] / v.at[a, 'ipc_alimentos'] * 100:.1f}")
        for c in CAN:
            r = cm.receta(c); q = r.set_index('item')['qty']
            ok = [i for i in alimentos(r) if i in PM.index and PM.at[i, a] == PM.at[i, a] and PM.at[i, b] == PM.at[i, b]]
            pb = PM.loc[ok, b] * q[ok]; pa = PM.loc[ok, a] * q[ok]; pa2 = pa.copy()
            for i in ok:
                v_ = au.INDEC_MAP.get(i)
                if v_ in I.index and I.at[v_, a] == I.at[v_, a]:
                    pa2[i] = pb[i] / (I.at[v_, b] / I.at[v_, a])
            print(f'   {c:15s} frescos SEPA {pb.sum() / pa.sum() * 100:6.1f} | con evolucion INDEC {pb.sum() / pa2.sum() * 100:6.1f}')

# ── 3.1: jackknife por producto ─────────────────────────────────────────────────────────────
def jackknife():
    print('== 3.1 error estandar por eleccion de productos (sacar un item por vez)')
    for c in CAN:
        q = cm.receta(c).set_index('item')['qty']; its = [i for i in q.index if i in P.index]
        for a, b, nom in [('2024-01', '2026-08', 'ene24-ago26'), ('2025-08', '2026-08', 'interanual')]:
            th = np.array([indice(q, [j for j in its if j != i], a, b) for i in its]); n = len(th)
            se = np.sqrt((n - 1) / n * ((th - th.mean()) ** 2).sum())
            print(f'   {c:15s} {nom:12s} {indice(q, its, a, b):7.1f} +- {se:4.1f}')

# ── 3.2: regla de cobertura minima ───────────────────────────────────────────────────────────
def flacos():
    N = sucursales_item_semana()
    emp = [i for i in P.index if str(i).isdigit() and i in N.index]
    print('== 3.2 indice ene24 -> ago26 con el precio de un empaquetado como faltante en semanas con pocas sucursales')
    reglas = [('sin regla', None), ('min 100', 100), ('min 300', 300), ('25% de su cobertura tipica', 'rel')]
    for nom, u in reglas:
        Pm = P.copy()
        if u is not None:
            if u == 'rel':
                ref = N.loc[emp, [s for s in cm.SEM if N[s].notna().any()][-24:]].median(axis=1)
                mask = N.loc[emp].lt(ref * 0.25, axis=0) & N.loc[emp].notna()
            else:
                mask = (N.loc[emp] < u) & N.loc[emp].notna()
            Pm.loc[emp] = Pm.loc[emp].where(~mask.reindex(columns=Pm.columns, fill_value=False))
        print(f'   {nom:28s} ' + ' | '.join(f"{c} {indice(cm.receta(c).set_index('item')['qty'], Pm=Pm):6.1f}" for c in CAN + ['Femenina']))

# ── 3.3: deriva del encadenado con productos limpios ─────────────────────────────────────────
def deriva():
    N = sucursales_item_semana()
    Nm = N.T.groupby([cm.mes_de_semana(w) for w in N.columns]).max().T
    R = P.T / P.T.shift(); quiebre = ((R > 3) | (R < 1 / 3)).any(axis=0)
    limpio = lambda i: (not str(i).isdigit()) or (i in Nm.index and bool((Nm.loc[i].fillna(0) >= 300).all()) and not bool(quiebre.get(i, False)))
    for a, b in [('2024-01', '2026-08'), ('2025-01', '2026-08')]:
        print(f'== 3.3 encadenado vs canasta fija, productos limpios, {a} -> {b}')
        for c in CAN:
            q = cm.receta(c).set_index('item')['qty']
            ok = [i for i in q.index if i in P.index and limpio(i) and PM.at[i, a] == PM.at[i, a] and PM.at[i, b] == PM.at[i, b]]
            d = float((PM.loc[ok, b] * q[ok]).sum() / (PM.loc[ok, a] * q[ok]).sum() * 100); e = indice(q, ok, a, b)
            print(f'   {c:15s} encadenado {e:6.1f} | directo {d:6.1f} | {100 * (e / d - 1):+.1f}%')

# ── 4.1: estacionalidad contra la banda del filtro de regimen ────────────────────────────────
def estacional():
    I = au.leer_indec(INDEC)
    ce = carpeta('AUD_CACHE', 'ean')
    if ce is None:
        sys.exit('Esta seccion necesita AUD_CACHE')
    ANCLA = ['Papa', 'Cebolla', 'Zapallo', 'Zanahoria', 'Tomate', 'Banana', 'Manzana', 'Naranja']
    anc = {}
    for f in sorted(ce.glob('*.parquet')):
        e = pq.read_table(f, filters=[('item', 'in', ANCLA)]).to_pandas()
        anc[f.stem] = float(pd.Series(np.repeat(e['p'].values, e['n_suc'].clip(upper=50).values)).median())
    print('== 4.1 cociente INDEC/ancla por mes y banda [ratio/3, ratio*3]')
    for var, t, ratio in [('Naranja', 'Naranja', 0.37), ('Tomate redondo', 'Tomate', 0.95), ('Limón', 'Limón', 0.45)]:
        s = pd.Series({m: I.at[var, m] / a for m, a in anc.items() if m in I.columns})
        print(f'   {t:8s} {s.min():.2f} a {s.max():.2f} | banda [{ratio / 3:.2f}, {ratio * 3:.2f}] | meses afuera {int(((s < ratio / 3) | (s > ratio * 3)).sum())}'
              f' | centro geometrico {np.sqrt(s.min() * s.max()):.2f}')

# ── 4.2: revision del nivel de los frescos entre dos corridas ─────────────────────────────────
def niveles():
    prev = os.environ.get('AUD_EXCEL_PREV')
    if not prev:
        sys.exit('Esta seccion necesita AUD_EXCEL_PREV')
    pa = pd.read_excel(prev, 'Panel_nacional'); pa['item'] = pa['item'].astype(str)
    Pa = pa.set_index('item')[[c for c in pa.columns if str(c)[:2] == '20']].astype(float)
    com = [s for s in Pa.columns if s in P.columns]
    Rr = P.loc[Pa.index.intersection(P.index), com] / Pa.loc[Pa.index.intersection(P.index), com]
    fr = [i for i in Rr.index if not str(i).isdigit() and (Rr.loc[i].dropna() - 1).abs().max() > 0.001]
    d = pd.DataFrame({'ratio': Rr.loc[fr].median(axis=1), 'desvio': Rr.loc[fr].std(axis=1)}).sort_values('ratio')
    print(f'== 4.2 frescos con la serie entera cambiada: {len(d)} | con factor constante (desvio < 0,001): {int((d.desvio < 0.001).sum())}')
    print(d.round(4).head(5).to_string()); print(d.round(4).tail(5).to_string())

SECCIONES = {'brecha': brecha, 'frescos': frescos, 'jackknife': jackknife, 'flacos': flacos, 'deriva': deriva,
             'estacional': estacional, 'niveles': niveles}
if __name__ == '__main__':
    for s in (sys.argv[1:] or ['brecha', 'frescos', 'jackknife']):
        SECCIONES[s]()
