# -*- coding: utf-8 -*-
"""Test del encadenado por EAN de frescos (nb07 v5.7).

Ejecuta el CODIGO REAL extraido de gen_nb07.py -no una copia- contra un panel sintetico que
reproduce el patron medido en la corrida 2026-08-27: un regimen barato de alta cobertura que
desaparece durante 10 semanas y deja solo el regimen caro. Con el estimador anterior (mediana
sobre filas sucursal-EAN) eso producia saltos de +149% a +235% sin que hubiera inflacion.

Incluye un tipo ESCASO (Palta: 1 EAN barato + 1 caro) para cubrir el caso en que la cadena se
corta y hay que anclar por tramos, que es donde apareceron los dos bugs de la implementacion.

    python test_encadenado_frescos.py     -> RESULTADO: OK / FALLA
"""
import io, pathlib, numpy as np, pandas as pd

SRC = pathlib.Path(__file__).with_name('gen_nb07.py')
src = io.open(SRC, encoding='utf-8').read()
i0 = src.index('if FRESCO_NAC_ENCADENADO and len(ean_nac):')
i1 = src.index('# \u2500\u2500 Banda de plausibilidad POR TIPO', i0)
BLOQUE = src[i0:i1]
print(f'bloque extraido: {len(BLOQUE)} chars\n')

SEM = pd.date_range('2026-01-01', periods=40, freq='7D')
INFL = 1.01   # 1% semanal, la verdad que el indice deberia recuperar

def escenario(nombre, p_barato, p_caro, n_eans_baratos=4, n_eans_caros=3):
    """Regimen barato con mucha cobertura que DESAPARECE en las semanas 20-29,
    dejando solo el regimen caro. Es el patron medido en la corrida real."""
    filas = []
    for k in range(n_eans_baratos):
        for t, s in enumerate(SEM):
            cob = 300 if not (20 <= t < 30) else 2      # se cae por debajo del minimo
            filas.append({'item': nombre, 'ean_norm': f'{nombre}_B{k}', 'semana': s,
                          'p': p_barato * (1 + 0.03*k) * INFL**t, 'n_suc': cob})
    for k in range(n_eans_caros):
        for t, s in enumerate(SEM):
            filas.append({'item': nombre, 'ean_norm': f'{nombre}_C{k}', 'semana': s,
                          'p': p_caro * (1 + 0.03*k) * INFL**t, 'n_suc': 90})
    return pd.DataFrame(filas)

casos = {'Lomo': (13211, 36378), 'Bife de chorizo': (12355, 31349), 'Carré de cerdo': (11725, 40000)}
ESCASO = escenario('Palta', 6592, 17000, n_eans_baratos=1, n_eans_caros=1)
casos['Palta']=(6592,17000)
ean_nac = pd.concat([escenario(t,a,b) for t,(a,b) in casos.items() if t!='Palta']+[ESCASO], ignore_index=True)

# Estimador VIEJO: mediana sobre filas sucursal-EAN (replica el groupby del pipeline).
ean_nac['_w'] = ean_nac['n_suc']
viejo = {}
for t in casos:
    s = ean_nac[ean_nac['item'] == t]
    col = {}
    for sem, g in s.groupby('semana'):
        rep = np.repeat(g['p'].values, g['n_suc'].values.astype(int))
        col[sem] = float(np.median(rep))
    viejo[t] = pd.Series(col)
nac_wide = pd.DataFrame(viejo).reindex(SEM)
nac_wide.index.name = 'semana'

FRESCO_INFO = {t: {} for t in casos}
FRESCO_NAC_ENCADENADO = True
FRESCO_EAN_MIN_SUC    = 10
FRESCO_MIN_EANS_PAR   = 2
FRESCO_MAX_HUECO_PAR  = 8
FRESCO_ESLABON_K      = 2.5

print('=== ANTES (estimador actual): salto por cambio de mezcla ===')
for t in casos:
    v = nac_wide[t]
    print(f'  {t:18s} sem19 {v.iloc[19]:9,.0f} -> sem20 {v.iloc[20]:9,.0f} '
          f'({v.iloc[20]/v.iloc[19]-1:+7.1%}) | max/min {v.max()/v.min():.2f}x')

exec(BLOQUE, globals())

print('\n=== DESPUES (encadenado por EAN) ===')
ok = True
for t in casos:
    v = nac_wide[t].dropna()
    # variacion POR SEMANA: entre dos observaciones puede haber semanas faltantes legitimas
    # (sin muestra apareada), y ahi la variacion acumulada del hueco no es un salto espurio.
    pos = pd.Series(range(len(SEM)), index=SEM).reindex(v.index)
    paso = pos.diff()
    var = (v.pct_change() + 1) ** (1 / paso) - 1
    var = var.dropna()
    real = INFL - 1
    err = abs(var.median() - real) / real * 100
    salto = abs(var).max()
    print(f'  {t:18s} var/semana mediana {var.median():+.3%} (verdad {real:+.2%}, error {err:.1f}%) | '
          f'max {salto:.2%} | max/min {v.max()/v.min():.2f}x (verdad {INFL**39:.2f}x)')
    if salto > 0.03 or err > 5: ok = False
print('\nRESULTADO:', 'OK - el salto de composicion desaparecio' if ok else 'FALLA')


# ─────────────────────────────────────────────────────────────────────────────
# REGRESION: precios PEGAJOSOS (el bug de la corrida 2026-09-08)
# Los precios de supermercado no cambian todas las semanas: en una semana dada solo una
# MINORIA de los EANs repricea. Con la MEDIANA de los ratios eso da exactamente 1,0 y la
# cadena no acumula NADA -Pan frances termino con UN solo valor distinto en 139 semanas y
# los frescos acumularon +58% contra +161% de los empaquetados-.
# ─────────────────────────────────────────────────────────────────────────────
print()
print('=== REGRESION: precios pegajosos (solo 1 de cada 5 EANs repricea por semana) ===')
N_EAN, CADA = 20, 5
filas = []
for k in range(N_EAN):
    for t, sm in enumerate(SEM):
        ult = max([w for w in range(t + 1) if w % CADA == k % CADA], default=0)
        filas.append({'item': 'Asado', 'ean_norm': f'A{k}', 'semana': sm,
                      'p': 10000 * (1 + 0.02 * k) * INFL ** ult, 'n_suc': 200})
ean_nac = pd.DataFrame(filas)
nac_wide = pd.DataFrame({'Asado': [10000 * INFL ** t for t in range(len(SEM))]}, index=SEM)
nac_wide.index.name = 'semana'
FRESCO_INFO = {'Asado': {}}
exec(BLOQUE, globals())
v = nac_wide['Asado'].dropna()
# La verdad es la media geometrica del PROPIO panel (indice de Jevons), no INFL**(n-1): por el
# escalonamiento, en la semana 0 ningun EAN reprecio todavia y en la ultima el repricio mas
# reciente fue algunas semanas antes. Ese desfasaje es real y el indice debe reproducirlo.
gm = ean_nac.pivot_table(index='semana', columns='ean_norm', values='p').apply(
    lambda r: np.exp(np.log(r.dropna()).mean()), axis=1)
verdad_ac = gm.iloc[-1] / gm.iloc[0] - 1
distintos = v.nunique()
ac = v.iloc[-1] / v.iloc[0] - 1
err = abs(ac - verdad_ac) / verdad_ac * 100
print(f'  acumulado {ac:+.2%} (verdad Jevons del panel {verdad_ac:+.2%}, error {err:.2f}%) | '
      f'valores distintos {distintos}/{len(v)}')
ok2 = err < 1 and distintos > len(v) * 0.5
print()
print('RESULTADO REGRESION:', 'OK - la cadena acumula la inflacion' if ok2 else
      'FALLA - la cadena se queda plana con precios pegajosos')
