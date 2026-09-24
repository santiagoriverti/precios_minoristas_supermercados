# -*- coding: utf-8 -*-
"""Tests de la v5.13 del nb07: indice TPD de frescos, nivel fijo y cobertura minima de empaquetados.

Ejecuta el CODIGO REAL de gen_nb07.py (bloques 1b y 2b de la CELDA 8) contra paneles sinteticos.

Comprueba que:
  1. en un panel balanceado el TPD sin ponderar es exactamente el indice de Jevons;
  2. con EANs que entran y salen (cada uno vive 20 semanas) los dos metodos recuperan la inflacion;
  3. con el nivel fijado en un mes de referencia, agregar una semana NO revisa la historia, ni con
     el TPD (empalme de movimiento) ni con el encadenado; y con el nivel en la ultima semana (lo de
     v5.12) si la revisa;
  4. la cobertura minima saca los item-semana de pocas sucursales, respeta a un item de pocas
     sucursales por naturaleza (tipo Tecnologica: umbral relativo) y no toca los frescos;
  5. el arrastre no rellena una celda sacada por cobertura (queda fuera de la muestra apareada);
  6. el nivel sale de los 3 ultimos meses con cobertura normal hasta el mes de referencia: un mes
     fuera de temporada (caso Durazno) no cuenta, y un solo mes raro no fija el nivel.

    python test_frescos_v513.py     -> RESULTADO: OK / FALLA
"""
import io, pathlib, datetime as _dt, numpy as np, pandas as pd

SRC = pathlib.Path(__file__).with_name('gen_nb07.py')
src = io.open(SRC, encoding='utf-8').read()
B2 = src[src.index('# ── 2b. Frescos: la FORMA de la serie sale de un indice por EAN'):
         src.index('# ── Banda de plausibilidad POR TIPO')]
B1 = src[src.index('# ── 1b. Cobertura minima de los EMPAQUETADOS'):
         src.index('# ── 2b. Frescos: la FORMA de la serie sale de un indice por EAN')]
MES = src[src.index('def _mes_de_semana('):src.index('\ndef _sem_anterior(')]

fallas = []
def chequear(ok, msg):
    print(('  OK    ' if ok else '  FALLA ') + msg)
    if not ok:
        fallas.append(msg)

BASE = dict(np=np, pd=pd, _dt=_dt, FRESCO_NAC_ENCADENADO=True, FRESCO_EAN_MIN_SUC=10, FRESCO_MIN_EANS_PAR=2,
            FRESCO_MAX_HUECO_PAR=8, FRESCO_ESLABON_K=2.5, FRESCO_TPD_VENTANA=52, FRESCO_TPD_ITER=300,
            FRESCO_EXPORTAR_METODOS=True, FRESCO_NIVEL_MES=None, NIVEL_REFERENCIA_FRESCO={}, FRESCO_NIVEL_COB_MIN=0.5,
            FRESCO_NIVEL_MESES=3)
exec(MES, BASE)
SEM = [(_dt.date(2025, 1, 2) + _dt.timedelta(weeks=k)).isoformat() for k in range(70)]   # jueves

def correr(ean_nac, nac_wide, metodo, nivel_mes=None, extra=None):
    ns = dict(BASE); ns.update(ean_nac=ean_nac, nac_wide=nac_wide.copy(), FRESCO_METODO=metodo,
                               FRESCO_INFO={c: {} for c in nac_wide.columns}, FRESCO_NIVEL_MES=nivel_mes)
    ns.update(extra or {})
    exec(B2, ns)
    return ns['nac_wide'], ns['FRESCO_SERIES_METODO']

# ── 1. panel balanceado: TPD = Jevons ────────────────────────────────────────────────────────
rng = np.random.default_rng(7)
filas = []
for e in range(15):
    lvl = 1000 * (1 + 0.1 * e)
    for t, s in enumerate(SEM):
        filas.append({'item': 'X', 'ean_norm': f'E{e}', 'semana': s, 'p': lvl * np.exp(0.008 * t + rng.normal(0, 0.03)), 'n_suc': 50})
ean = pd.DataFrame(filas)
jev = ean.pivot_table(index='semana', columns='ean_norm', values='p').apply(lambda r: np.exp(np.log(r).mean()), axis=1)
est = pd.DataFrame({'X': jev.values}, index=pd.Index(SEM, name='semana'))
print('=== 1) panel balanceado ===')
for m in ['tpd', 'encadenado']:
    nw, _ = correr(ean, est, m)
    err = float(np.nanmax(np.abs(nw['X'] / nw['X'].iloc[-1] / (jev / jev.iloc[-1]) - 1)))
    chequear(err < 1e-6 if m == 'tpd' else err < 0.02, f'{m}: se aparta del Jevons en {err:.2e}' + (' (el TPD tiene que ser exacto)' if m == 'tpd' else ''))

# ── 2. EANs que entran y salen ───────────────────────────────────────────────────────────────
filas = []
for e in range(30):
    ini = 2 * e; fin = ini + 20
    for t in range(max(0, ini), min(len(SEM), fin)):
        filas.append({'item': 'Y', 'ean_norm': f'F{e}', 'semana': SEM[t], 'p': 800 * (1 + 0.05 * (e % 7)) * 1.01 ** t, 'n_suc': 40})
ean2 = pd.DataFrame(filas)
est2 = pd.DataFrame({'Y': [800 * 1.01 ** t for t in range(len(SEM))]}, index=pd.Index(SEM, name='semana'))
print('\n=== 2) EANs que entran y salen (inflacion real 1% semanal) ===')
for m in ['tpd', 'encadenado']:
    nw, _ = correr(ean2, est2, m)
    v = nw['Y'].dropna(); vs = (v / v.shift() - 1).dropna()
    chequear(abs(vs.median() - 0.01) < 1e-4 and abs(vs).max() < 0.02, f'{m}: variacion semanal mediana {vs.median():.4%}, maxima {abs(vs).max():.2%}')

# ── 3. una semana nueva no revisa la historia ────────────────────────────────────────────────
print('\n=== 3) agregar una semana (con un estimador ruidoso en la semana nueva) ===')
corto = SEM[:-1]
e_c = ean[ean['semana'].isin(corto)]
est_c = est.loc[corto].copy()
est_l = est.copy(); est_l.iloc[-1] = est_l.iloc[-1] * 1.5      # la semana nueva trae un nivel malo (como la Mortadela)
mes_ref = _dt.date.fromisoformat(SEM[40]).strftime('%Y-%m')
for m in ['tpd', 'encadenado']:
    a, _ = correr(e_c, est_c, m, nivel_mes=mes_ref)
    b, _ = correr(ean, est_l, m, nivel_mes=mes_ref)
    rev = float(np.nanmax(np.abs(b['X'].loc[corto] / a['X'] - 1)))
    chequear(rev < 1e-9, f'{m} con nivel en {mes_ref}: revision maxima de la historia {rev:.1e}')
a, _ = correr(e_c, est_c, 'tpd'); b, _ = correr(ean, est_l, 'tpd')
rev = float(np.nanmax(np.abs(b['X'].loc[corto] / a['X'] - 1)))
chequear(rev > 0.3, f'con el nivel en la ultima semana (v5.12) la historia SI se reescala: {rev:.0%}')

# ── 4. cobertura minima de empaquetados ──────────────────────────────────────────────────────
print('\n=== 4) cobertura minima (min(300, 50% de la cobertura tipica)) ===')
sem = SEM[:40]
filas = []
for t, s in enumerate(sem):
    n_a = 60 if t < 5 else 2000          # arranca con un punado de sucursales
    n_b = 30 if t == 20 else 90          # item de pocas sucursales por naturaleza (tipo Tecnologica)
    for k in range(n_a): filas.append({'item': '111', 'semana': s, 'suc_id': f'a{k}', 'price': 100.0})
    for k in range(n_b): filas.append({'item': '222', 'semana': s, 'suc_id': f'b{k}', 'price': 900.0})
    for k in range(20): filas.append({'item': 'Palta', 'semana': s, 'suc_id': f'c{k}', 'price': 50.0})
sval = pd.DataFrame(filas)
nw = pd.DataFrame({'111': 100.0, '222': 900.0, 'Palta': 50.0}, index=pd.Index(sem, name='semana'))
ns = dict(np=np, pd=pd, sval=sval, nac_wide=nw.copy(), EANS_EMP_LECT={'111', '222'},
          MIN_SUC_ITEM_SEMANA=300, FRAC_SUC_ITEM_TIPICA=0.5)
exec(B1, ns)
r = ns['nac_wide']
chequear(r['111'].iloc[:5].isna().all() and r['111'].iloc[5:].notna().all(), 'item 111: salen las 5 semanas con 60 sucursales, quedan las de 2.000')
chequear(r['222'].isna().sum() == 1 and np.isnan(r['222'].iloc[20]), 'item 222 (90 sucursales tipicas): sale solo la semana con 30 (umbral 45, no 300)')
chequear(r['Palta'].notna().all(), 'el fresco no se toca')
chequear(ns['N_CELDAS_FLACAS'] == 6, f"celdas sacadas: {ns['N_CELDAS_FLACAS']} (esperado 6)")

# ── 5. el arrastre no puentea una celda de pocas sucursales ──────────────────────────────────
print('\n=== 5) arrastre: una celda flaca queda fuera de la muestra apareada ===')
ARR = src[src.index('nac_obs  = nac_wide.notna()'):src.index('nac_ff_long = ')]
nw = pd.DataFrame({'111': [100.0 * 1.02 ** t for t in range(40)], '222': 900.0, 'Palta': 50.0}, index=pd.Index(sem, name='semana'))
nw.iloc[30, 0] = np.nan                                                    # faltante comun: se arrastra
ns = dict(np=np, pd=pd, sval=sval, nac_wide=nw.copy(), EANS_EMP_LECT={'111', '222'},
          MIN_SUC_ITEM_SEMANA=300, FRAC_SUC_ITEM_TIPICA=0.5, MAX_SEMANAS_ARRASTRE=8)
exec(B1, ns)
ns['_ratio_bad'] = pd.DataFrame(False, index=ns['nac_wide'].index, columns=ns['nac_wide'].columns)
exec(ARR, ns)
ff = ns['nac_ff']
chequear(ff['111'].iloc[:5].isna().all(), 'las 5 semanas flacas del item 111 siguen vacias despues del arrastre')
chequear(np.isnan(ff['222'].iloc[20]), 'la semana flaca del item 222 no se rellena con el precio anterior')
chequear(ff['111'].iloc[30] == nw['111'].iloc[29], 'un faltante comun se sigue arrastrando')

# ── 6. nivel de un fresco fuera de temporada ─────────────────────────────────────────────────
print('\n=== 6) nivel fuera de temporada (caso Durazno) ===')
MS = [BASE['_mes_de_semana'](w) for w in SEM]
ref = MS[40]
previos = sorted({m for m in MS if m < ref})
en_ref = [m == ref for m in MS]
caro = [m in (previos[-1], ref) for m in MS]      # el estimador salta x4 en los dos ultimos meses
filas = [{'item': 'D', 'ean_norm': f'D{e}', 'semana': w, 'p': 500 * (1 + 0.1 * e) * 1.01 ** t, 'n_suc': 40}
         for e in range(10) for t, w in enumerate(SEM)]
eanD = pd.DataFrame(filas)
estD = pd.DataFrame({'D': [(4000.0 if r else 1000.0) * 1.01 ** t for t, r in enumerate(caro)]}, index=pd.Index(SEM, name='semana'))
# cobertura normal: meses ref-2, ref-1, ref -> 8 de 12-13 semanas a x4 -> nivel 4000
# ref fuera de temporada: meses ref-3, ref-2, ref-1 -> solo ref-1 a x4 -> nivel 1000
for flaco, esperado_mes, esperado_nivel in [(True, f'{previos[-3]}..{previos[-1]}', 1000.0), (False, None, 4000.0)]:
    cob = pd.DataFrame({'D': [300.0 if (r and flaco) else 2000.0 for r in en_ref]}, index=pd.Index(SEM, name='semana'))
    ns = dict(BASE); ns.update(ean_nac=eanD, nac_wide=estD.copy(), FRESCO_METODO='tpd', FRESCO_INFO={'D': {}},
                               FRESCO_NIVEL_MES=ref, _nsuc_is=cob)
    exec(B2, ns)
    niv = float(np.median(ns['nac_wide']['D'] / pd.Series([1.01 ** t for t in range(len(SEM))], index=SEM)))
    mt = ns['FRESCO_MES_NIVEL_TIPO'].get('D')
    chequear(mt == esperado_mes and abs(niv / esperado_nivel - 1) < 1e-6,
             f"cobertura {'flaca' if flaco else 'normal'} en {ref}: nivel {niv:,.0f} (esperado {esperado_nivel:,.0f}), meses {mt or 'los 3 hasta ' + ref}")

print('\nRESULTADO:', 'OK' if not fallas else f'FALLA ({len(fallas)})')
