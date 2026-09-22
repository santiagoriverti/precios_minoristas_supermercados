# -*- coding: utf-8 -*-
"""Test del COSTO POR SUCURSAL (BUG-37) y del ANCLAJE DE NIVEL de frescos (nb07 v5.10).

Ejecuta el CODIGO REAL extraido de gen_nb07.py (el bloque de la CELDA 8 que arma `costo_suc`, y la
funcion `_factor_nivel`) contra un panel sintetico chico donde el resultado correcto se conoce.

Reproduce lo medido en la auditoria del 2026-09-22 sobre la corrida v5.9: Vea no publica NINGUN
item de verduras, frutas, pollo ni panaderia, y el costo por sucursal de la version anterior dejaba
esos rubros afuera en vez de valuarlos a precio nacional -> Vea salia a 0,68x el nacional.

Comprueba que:
  1. una sucursal que publica todo 10% mas caro cuesta exactamente 1,10x el nacional;
  2. una sucursal a precio nacional que NO publica dos rubros enteros cuesta 1,00x (no 0,6x) y
     reporta como imputada justo la parte de esos rubros;
  3. una sucursal con un rubro PARCIAL imputa solo lo que falta;
  4. una sucursal por debajo de la cobertura minima de empaquetados queda afuera;
  5. el precio por sucursal de un tipo con nivel anclado se reescala con el mismo factor que el
     nacional (sin eso, una sucursal a precio de mercado apareceria 2x mas cara);
  6. `_factor_nivel` ancla el PROMEDIO del mes pedido, o la ultima semana con el formato viejo, y
     devuelve None si el mes no tiene dato.

    python test_costo_sucursal.py     -> RESULTADO: OK / FALLA
"""
import io, pathlib, datetime as _dt, numpy as np, pandas as pd

SRC = pathlib.Path(__file__).with_name('gen_nb07.py')
src = io.open(SRC, encoding='utf-8').read()

def bloque(ini, fin):
    i0 = src.index(ini); i1 = src.index(fin, i0)
    return src[i0:i1]

B_MES = bloque('def _mes_de_semana(', '\ndef _sem_anterior(')
B_FACTOR = bloque('def _factor_nivel(', '\nFACTOR_NIVEL_FRESCO = {}')
B_COSTO = bloque('# ── Precios POR SUCURSAL de los tipos con nivel anclado', "\n''' ))")
print(f'bloques extraidos: _mes_de_semana {len(B_MES)} | _factor_nivel {len(B_FACTOR)} | costo {len(B_COSTO)} chars\n')

fallas = []
def chequear(ok, msg):
    print(('  OK    ' if ok else '  FALLA ') + msg)
    if not ok:
        fallas.append(msg)

# ── Panel sintetico ────────────────────────────────────────────────────────────
SK = ['id_comercio', 'id_bandera', 'id_sucursal']
SEM = ['2026-08-06', '2026-08-13']
REC = pd.DataFrame([
    ('e1', 2.0, 'Almacen', 'emp'), ('e2', 1.0, 'Almacen', 'emp'), ('e3', 3.0, 'Almacen', 'emp'),
    ('e4', 1.0, 'Limpieza', 'emp'), ('e5', 2.0, 'Limpieza', 'emp'),
    ('Pollo', 4.0, 'Pollo', 'fresh'), ('Papa', 20.0, 'Verduras', 'fresh'),
], columns=['item', 'qty', 'rubro', 'kind'])
NAC = {'e1': 100.0, 'e2': 250.0, 'e3': 80.0, 'e4': 300.0, 'e5': 150.0, 'Pollo': 5000.0, 'Papa': 2000.0}
FACTOR = {'Pollo': 0.4}          # el nacional de Pollo ya fue anclado: su escala cruda era 5000/0,4
nac_ff_long = pd.DataFrame([(s, i, p) for s in SEM for i, p in NAC.items()], columns=['semana', 'item', 'nac'])
q = REC.set_index('item')['qty']
TOTAL = sum(NAC[i] * q[i] for i in NAC)
V_FRESCO = NAC['Pollo'] * q['Pollo'] + NAC['Papa'] * q['Papa']
V_LIMP = NAC['e4'] * q['e4'] + NAC['e5'] * q['e5']

def crudo(item, factor_precio):
    """Precio que publica la sucursal, en la escala CRUDA del SEPA (sin anclar)."""
    p = NAC[item] * factor_precio
    return p / FACTOR[item] if item in FACTOR else p

filas = []
def sucursal(cid, items, factor_precio):
    for s in SEM:
        for it in items:
            filas.append((cid, '1', '1', s, it, crudo(it, factor_precio)))
sucursal('A', list(NAC), 1.10)                          # todo, 10% mas cara
sucursal('VEA', ['e1', 'e2', 'e3', 'e4', 'e5'], 1.00)   # sin Pollo ni Verduras: dos rubros enteros
sucursal('PARC', ['e1', 'e2', 'e3', 'e4', 'Papa'], 1.00)  # le falta e5 (rubro Limpieza parcial) y Pollo
sucursal('POCA', ['e1', 'e2', 'Pollo', 'Papa'], 1.00)   # 2 de 5 empaquetados: bajo la cobertura minima
sval = pd.DataFrame(filas, columns=SK + ['semana', 'item', 'price'])
suc_geo = pd.DataFrame({'id_comercio': ['A', 'VEA', 'PARC', 'POCA'], 'id_bandera': '1', 'id_sucursal': '1',
                        'cadena': ['A', 'Vea', 'Parcial', 'Poca'], 'provincia': 'X', 'region': 'R'})
suc_geo['suc_id'] = suc_geo['id_comercio'] + '|1|1'

ns = {'pd': pd, 'np': np, '_dt': _dt}
exec(B_MES, ns)
ns.update({'sval': sval.copy(), 'nac_ff_long': nac_ff_long, 'RECETAS': {'X': REC}, 'CANASTAS_ACTIVAS': ['X'],
           'FRAC_PRODUCTOS_MIN': 0.8, 'FACTOR_NIVEL_FRESCO': dict(FACTOR), '_SK': SK, 'suc_geo': suc_geo})
exec(B_COSTO, ns)
cs = ns['costo_suc'].groupby('cadena').agg(costo=('costo', 'mean'), pct=('pct_imputado', 'mean'))

print(f'=== costo nacional de la canasta: ${TOTAL:,.0f} ===\n')
print('=== 1) sucursal que publica todo 10% mas caro ===')
chequear(abs(cs.at['A', 'costo'] / TOTAL - 1.10) < 1e-9, f'costo {cs.at["A", "costo"] / TOTAL:.4f}x el nacional (esperado 1,1000x)')
chequear(abs(cs.at['A', 'pct']) < 1e-9, f'imputado {cs.at["A", "pct"]:.1f}% (esperado 0%)')

print('\n=== 2) sucursal a precio nacional SIN dos rubros enteros (caso Vea) ===')
esperado_pct = V_FRESCO / TOTAL * 100
viejo = TOTAL - V_FRESCO     # lo que daba la version v5.9: los rubros ausentes quedaban afuera
chequear(abs(cs.at['Vea', 'costo'] / TOTAL - 1.0) < 1e-9,
         f'costo {cs.at["Vea", "costo"] / TOTAL:.4f}x el nacional (esperado 1,0000x; v5.9 daba {viejo / TOTAL:.4f}x)')
chequear(abs(cs.at['Vea', 'pct'] - esperado_pct) < 0.05, f'imputado {cs.at["Vea", "pct"]:.1f}% (esperado {esperado_pct:.1f}%)')

print('\n=== 3) rubro parcial: imputa solo lo que falta ===')
falta = NAC['e5'] * q['e5'] + NAC['Pollo'] * q['Pollo']
chequear(abs(cs.at['Parcial', 'costo'] / TOTAL - 1.0) < 1e-9, f'costo {cs.at["Parcial", "costo"] / TOTAL:.4f}x (esperado 1,0000x)')
chequear(abs(cs.at['Parcial', 'pct'] - falta / TOTAL * 100) < 0.05,
         f'imputado {cs.at["Parcial", "pct"]:.1f}% (esperado {falta / TOTAL * 100:.1f}%)')

print('\n=== 4) cobertura minima de empaquetados ===')
chequear('Poca' not in cs.index, 'la sucursal con 2 de 5 empaquetados queda afuera')

print('\n=== 5) reescalado del precio por sucursal de un tipo anclado ===')
ns2 = {'pd': pd, 'np': np, '_dt': _dt}
exec(B_MES, ns2)
ns2.update({'sval': sval.copy(), 'nac_ff_long': nac_ff_long, 'RECETAS': {'X': REC}, 'CANASTAS_ACTIVAS': ['X'],
            'FRAC_PRODUCTOS_MIN': 0.8, 'FACTOR_NIVEL_FRESCO': {}, '_SK': SK, 'suc_geo': suc_geo})
exec(B_COSTO, ns2)
sin = ns2['costo_suc'].groupby('cadena')['costo'].mean()
chequear(sin['A'] / TOTAL > 1.5, f'SIN reescalar, la sucursal "10% mas cara" sale {sin["A"] / TOTAL:.2f}x (contaminada por la escala)')
chequear(abs(cs.at['A', 'costo'] / TOTAL - 1.10) < 1e-9, 'CON el factor queda en 1,10x')

print('\n=== 6) _factor_nivel ===')
exec(B_FACTOR, ns)
f = ns['_factor_nivel']
s = pd.Series([90.0, 100.0, 110.0, 120.0, 130.0, np.nan],
              index=['2026-07-30', '2026-08-06', '2026-08-13', '2026-08-20', '2026-08-27', '2026-09-03'])
k, antes, cuando = f(s, (1000.0, '2026-08'))
aug = [w for w in s.index if ns['_mes_de_semana'](w) == '2026-08']
chequear(abs((s[aug] * k).mean() - 1000.0) < 1e-9 and cuando == '2026-08',
         f'promedio de ago-26 anclado a 1000 (factor {k:.4f}, semanas {len(aug)})')
k2, antes2, cuando2 = f(s, 1000.0)
chequear(abs(s.dropna().iloc[-1] * k2 - 1000.0) < 1e-9 and cuando2 == 'ultima semana', 'formato viejo: ancla la ultima semana con dato')
chequear(f(s, (1000.0, '2025-01')) is None, 'mes sin dato -> None (no se ancla)')
chequear(f(s, (float('nan'), '2026-08')) is None and f(s, (0, '2026-08')) is None, 'referencia invalida -> None')

print('\nRESULTADO:', 'OK' if not fallas else f'FALLA ({len(fallas)})')
