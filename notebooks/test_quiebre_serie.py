# -*- coding: utf-8 -*-
"""Test de la regla de QUIEBRE DE SERIE del indice de canastas (nb07 v5.9).

Ejecuta el CODIGO REAL de `_eslabon` extraido de gen_nb07.py. Reproduce el patron medido en la
auditoria del 2026-09-22: un EAN que convive en el SEPA con un precio viejo que la cadena nunca
actualizo, de modo que el precio nacional alterna entre dos regimenes que distan mas de 10x
(Arroz Molinos Ala x20,5; Rexona x0,06 y x17,7 cinco veces).

Comprueba que:
  1. una variacion imposible (x20) NO entra en el indice;
  2. una variacion grande pero posible (x1,6 de enero 2024) SI entra;
  3. el ida y vuelta de un regimen a otro no deja escalon acumulado;
  4. la inflacion real del resto de la canasta se sigue midiendo sin sesgo;
  5. con el umbral desactivado, el comportamiento es el viejo.

    python test_quiebre_serie.py     -> RESULTADO: OK / FALLA
"""
import io, pathlib, numpy as np, pandas as pd

SRC = pathlib.Path(__file__).with_name('gen_nb07.py')
src = io.open(SRC, encoding='utf-8').read()
i0 = src.index('def _eslabon(')
i1 = src.index('\n# ── Receta de cada canasta', i0)
BLOQUE = src[i0:i1]
print(f'bloque extraido: {len(BLOQUE)} chars\n')
ns = {'pd': pd, 'np': np, 'QUIEBRE_ITEM_K': 3.0}
exec(BLOQUE, ns)
_eslabon = ns['_eslabon']

SEM = [f's{t:03d}' for t in range(40)]
INFL = 1.01          # 1% semanal en los items sanos


def panel(con_falla, vuelve=False):
    """8 items sanos + 1 item con dos regimenes de publicacion (100 y 2.000)."""
    d = {f'sano{k}': [100 * (1 + 0.1 * k) * INFL ** t for t in range(len(SEM))] for k in range(8)}
    if con_falla:
        serie = []
        for t in range(len(SEM)):
            viejo = 100.0 * INFL ** t
            nuevo = 2000.0 * INFL ** t
            if t < 10:
                serie.append(viejo)                      # regimen viejo (precio congelado de 2022)
            elif vuelve and 20 <= t < 25:
                serie.append(viejo)                      # vuelve al regimen viejo y despues sale
            else:
                serie.append(nuevo)
        d['falla'] = serie
    return pd.DataFrame(d, index=SEM)


def indice(V, k):
    idx = [100.0]; qb = []
    for t in range(1, len(V)):
        r, q = _eslabon(V.iloc[t], V.iloc[t - 1], k)
        qb += [(V.index[t], i) for i in q]
        idx.append(idx[-1] * r)
    return pd.Series(idx, index=V.index), qb


fallas = []
def chequear(ok, msg):
    print(('  OK    ' if ok else '  FALLA ') + msg)
    if not ok:
        fallas.append(msg)


verdad = (INFL ** (len(SEM) - 1) - 1) * 100
print(f'=== inflacion verdadera de la canasta: {verdad:+.2f}% ===\n')

print('=== 1) canasta sana (control): la regla no debe tocar nada ===')
V = panel(con_falla=False)
a, qa = indice(V, 3.0)
chequear(abs(a.iloc[-1] - 100 - verdad) < 0.01, f'indice {a.iloc[-1]-100:+.2f}% (verdad {verdad:+.2f}%)')
chequear(not qa, f'quiebres detectados: {len(qa)} (esperado 0)')

print('\n=== 2) un item salta x20 al actualizarse el precio viejo ===')
V = panel(con_falla=True)
viejo, _ = indice(V, None)
nuevo, qn = indice(V, 3.0)
chequear(viejo.iloc[-1] - 100 > 100, f'SIN la regla el indice se va a {viejo.iloc[-1]-100:+.1f}% (contaminado)')
chequear(abs(nuevo.iloc[-1] - 100 - verdad) < 0.5, f'CON la regla queda en {nuevo.iloc[-1]-100:+.2f}% (verdad {verdad:+.2f}%)')
chequear(len(qn) == 1 and qn[0][1] == 'falla', f'quiebres: {qn}')

print('\n=== 3) el item va y vuelve entre regimenes (caso Rexona) ===')
V = panel(con_falla=True, vuelve=True)
viejo, _ = indice(V, None)
nuevo, qn = indice(V, 3.0)
chequear(abs(nuevo.iloc[-1] - 100 - verdad) < 0.5, f'CON la regla {nuevo.iloc[-1]-100:+.2f}% (verdad {verdad:+.2f}%)')
chequear(len(qn) == 3, f'quiebres detectados: {len(qn)} (esperado 3: salida, vuelta y nueva salida)')

print('\n=== 4) una variacion grande pero POSIBLE no se descarta (x1,6 de enero 2024) ===')
V = panel(con_falla=False)
V = V.copy(); V.iloc[5:, 0] = V.iloc[5:, 0] * 1.6      # un item repreció +60% y se queda ahi
a, qa = indice(V, 3.0)
chequear(not qa, f'quiebres: {len(qa)} (esperado 0: x1,6 esta por debajo del umbral x3)')
chequear(a.iloc[-1] - 100 > verdad, f'el +60% SI entra al indice: {a.iloc[-1]-100:+.2f}% > {verdad:+.2f}%')

print('\n=== 5) umbral desactivado: comportamiento viejo ===')
V = panel(con_falla=True)
for k in (None, 0, 1):
    b, qb = indice(V, k)
    chequear(abs(b.iloc[-1] - viejo.iloc[-1]) < 1e-9 and not qb, f'k={k!r}: identico al indice sin regla')

print('\nRESULTADO:', 'OK' if not fallas else f'FALLA ({len(fallas)})')
