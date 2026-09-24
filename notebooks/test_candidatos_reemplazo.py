# -*- coding: utf-8 -*-
"""Test de la hoja Candidatos_trazabilidad (nb07 v5.11 y v5.11.1).

Ejecuta el CODIGO REAL del bloque "CANDIDATOS A REEMPLAZO" de la CELDA 13 de gen_nb07.py contra un
panel sintetico donde se sabe cuantos meses tuvo dato cada candidato.

Comprueba que:
  1. la trazabilidad de cada candidato es la fraccion de meses con alguna semana con dato;
  2. el item ACTUAL queda marcado como tal y los demas como candidatos;
  3. un candidato que nunca aparecio en el SEPA figura con 0% (no se cae ni desaparece);
  4. la cobertura del ultimo mes sale del crudo del mes en curso;
  5. una necesidad con " / " en el nombre no se corta (v5.11.1).

    python test_candidatos_reemplazo.py     -> RESULTADO: OK / FALLA
"""
import io, pathlib, re, datetime as _dt, numpy as np, pandas as pd

SRC = pathlib.Path(__file__).with_name('gen_nb07.py')
src = io.open(SRC, encoding='utf-8').read()
i0 = src.index('# ── CANDIDATOS A REEMPLAZO (v5.11)'); i1 = src.index('\n_ultN = ', i0)
BLOQUE = src[i0:i1]
j0 = src.index('def _mes_de_semana('); j1 = src.index('\ndef _sem_anterior(', j0)
print(f'bloque extraido: {len(BLOQUE)} chars\n')

fallas = []
def chequear(ok, msg):
    print(('  OK    ' if ok else '  FALLA ') + msg)
    if not ok:
        fallas.append(msg)

def normalizar_ean(s):
    d = re.sub(r'\D', '', str(s))
    return (d.lstrip('0') or '0') if d else ''

# 12 semanas = 3 meses (ene, feb, mar 2026). Candidato A con dato siempre, B solo en marzo,
# ACTUAL con dato en enero y marzo, C nunca aparecio.
SEM = [(_dt.date(2026, 1, 8) + _dt.timedelta(weeks=k)).isoformat() for k in range(12)]
obs = pd.DataFrame(False, index=SEM, columns=['111', '222', '333'])
obs.loc[:, '111'] = True
obs.loc[SEM[8:], '222'] = True
obs.loc[SEM[:4] + SEM[8:], '333'] = True
nac_ff = obs.astype(float).where(obs) * 100.0
EANS_CANDIDATOS = {'333': 'Popular / Azucar / ACTUAL (trazab. 67%) / Azucar Vieja 1 Kg',
                   '111': 'Popular / Azucar / Azucar Buena 1 Kg (1500 suc)',
                   '222': 'Popular / Azucar / Azucar Nueva 1 Kg (900 suc)',
                   '0444': 'Popular / Azucar / Azucar Fantasma 1 Kg (800 suc)',
                   # necesidad con ' / ' en el nombre (v5.11.1: se cortaba en 'Milanesas')
                   '555': 'Popular / Milanesas / nuggets de pollo / ACTUAL (trazab. 48%) / Formitas Viejas 400 Gr',
                   '666': 'Popular / Milanesas / nuggets de pollo / Formitas Nuevas 350 Gr (900 suc)'}
_dm = pd.DataFrame({'ean_norm': ['111', '111', '222'], 'cadena': ['DIA', 'Coto', 'DIA'],
                    'provincia': ['CABA', 'CABA', 'Salta'], 'suc_id': ['a', 'b', 'c']})
ns = {'pd': pd, 'np': np, '_dt': _dt, 'nac_obs': obs, 'nac_ff': nac_ff, '_dm': _dm,
      'EANS_CANDIDATOS': EANS_CANDIDATOS, 'normalizar_ean': normalizar_ean, 'TRAZA_MIN_PCT': 85.0,
      'EANS_CAND': {normalizar_ean(e) for e in EANS_CANDIDATOS},
      'CANASTAS_ACTIVAS': ['Popular'], 'CANASTAS_EMP': {'Popular': {'333': ('Azucar Vieja', 4, 'Almacen', '')}}}
exec(src[j0:j1], ns)
exec(BLOQUE, ns)
c = ns['candidatos_traza'].set_index('ean')

print('=== 1) trazabilidad por candidato ===')
chequear(c.at['111', 'trazabilidad_%'] == 100.0, f"siempre presente: {c.at['111', 'trazabilidad_%']}% (esperado 100)")
chequear(abs(c.at['222', 'trazabilidad_%'] - 33.3) < 0.1, f"solo marzo: {c.at['222', 'trazabilidad_%']}% (esperado 33,3)")
chequear(abs(c.at['333', 'trazabilidad_%'] - 66.7) < 0.1, f"enero y marzo: {c.at['333', 'trazabilidad_%']}% (esperado 66,7)")
chequear(c.at['222', 'primer_mes'] == '2026-03', f"primer mes con dato del nuevo: {c.at['222', 'primer_mes']}")
print('\n=== 2) roles ===')
chequear(c.at['333', 'rol'] == 'ACTUAL' and c.at['333', 'en_canasta_hoy'] == 'Popular', 'el item actual queda marcado y en su canasta')
chequear((c.drop(['333', '555'])['rol'] == 'candidato').all(), 'los demas son candidatos')
print("\n=== 2b) necesidad con ' / ' en el nombre ===")
chequear(c.at['555', 'necesidad'] == 'Milanesas / nuggets de pollo' and c.at['555', 'rol'] == 'ACTUAL',
         f"ACTUAL: necesidad '{c.at['555', 'necesidad']}', rol {c.at['555', 'rol']}")
chequear(c.at['666', 'necesidad'] == 'Milanesas / nuggets de pollo' and c.at['666', 'rol'] == 'candidato',
         f"candidato: necesidad '{c.at['666', 'necesidad']}', rol {c.at['666', 'rol']}")
chequear(c.at['666', 'descripcion'] == 'Formitas Nuevas 350 Gr (900 suc)', 'la descripcion es el ultimo campo')
print('\n=== 3) candidato que nunca aparecio ===')
chequear(c.at['444', 'trazabilidad_%'] == 0.0 and c.at['444', 'meses_con_dato'] == 0, 'figura con 0% (EAN normalizado sin ceros a la izquierda)')
print('\n=== 4) cobertura del ultimo mes ===')
chequear(c.at['111', 'n_sucursales_ult_mes'] == 2 and c.at['111', 'n_cadenas_ult_mes'] == 2, 'candidato 111: 2 sucursales de 2 cadenas')
chequear(c.at['444', 'n_sucursales_ult_mes'] == 0, 'el que no aparecio: 0 sucursales')

print('\nRESULTADO:', 'OK' if not fallas else f'FALLA ({len(fallas)})')
