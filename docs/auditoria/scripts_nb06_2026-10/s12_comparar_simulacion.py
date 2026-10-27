# Cálculo INDEPENDIENTE de la brecha por sucursal x mes x subtipo y tipo desde los precios extraídos con
# s8_precios_zips.py (mediana exacta mensual por sucursal x EAN) y comparación con la simulación de las celdas reales
# del nb06 (s11_simular_nb06.py). Uso:
#   python -I -X utf8 s12_comparar_simulacion.py <repo> <carpeta precios_mes> <carpeta precios_mes_2> <salida de s11>
import json, re, sys
from pathlib import Path
import numpy as np
import pandas as pd

REPO, D1, D2, SIM = (Path(a) for a in sys.argv[1:5])
pd.set_option('display.width', 250)
cells = [''.join(c['source']) for c in json.load(open(REPO / 'notebooks' / '06_evolucion_brecha_celiaca.ipynb',
                                                       encoding='utf-8'))['cells'] if c['cell_type'] == 'code']
g = {}
exec(cells[0], g)             # la CELDA 1 (config) tal cual
TIPOS, GRAMOS, VIG, FILT = g['TIPOS'], g['GRAMOS'], g['VIGENCIA'], g['CADENAS_FILTRAR']
n = lambda e: re.sub(r'\D', '', str(e)).lstrip('0')
ROL = {n(e): ('tacc', t) for t, c in TIPOS.items() for e in c['tacc']}
ROL.update({n(e): ('sin', t) for t, c in TIPOS.items() for e in c['sin_tacc']})
GR = {n(e): float(v) for e, v in GRAMOS.items()}
VIG = {n(e): v for e, v in VIG.items()}
PROD = {n(e): p for p, es in g.get('PRODUCTO', {}).items() for e in es}
SUB = {n(e): s for s, es in g.get('SUBTIPO', {}).items() for e in es}
assert set(ROL) <= set(SUB), 'todos los EANs de la canasta tienen que tener SUBTIPO'

fs = sorted(D1.glob('*.parquet')) + sorted(D2.glob('*.parquet'))
P = pd.concat([pd.read_parquet(f, filters=[('ean', 'in', sorted(ROL))]) for f in fs], ignore_index=True)
P = P[~P['id_comercio'].isin(FILT)].drop_duplicates(['id_comercio', 'id_bandera', 'id_sucursal', 'ean', 'mes'])
P = P[[(VIG.get(e, (None, None))[0] is None or m >= VIG[e][0]) and (VIG.get(e, (None, None))[1] is None or m <= VIG[e][1])
       for e, m in zip(P['ean'], P['mes'])]]
# sucursales del maestro con coordenadas (las que lee la CELDA 6); el universo de la CELDA 7 se aplica después
ms = pd.read_excel(REPO / 'data' / 'maestro_sucursales_completo.xlsx')
for c in ('id_comercio', 'id_bandera', 'id_sucursal'):
    ms[c] = ms[c].astype(str)
ms = ms[ms['sucursales_latitud'].between(-55, -22) & ms['sucursales_longitud'].between(-73, -53)]
P = P.merge(ms[['id_comercio', 'id_bandera', 'id_sucursal']].drop_duplicates(), on=['id_comercio', 'id_bandera', 'id_sucursal'])
P['rol'] = P['ean'].map(lambda e: ROL[e][0]); P['tipo'] = P['ean'].map(lambda e: ROL[e][1])
P['p100'] = P['precio_mediana'] / P['ean'].map(GR) * 100
# filtro de plausibilidad (misma regla)
em = P.groupby(['tipo', 'rol', 'mes', 'ean'])['p100'].median().rename('_p').reset_index()
em['_rel'] = em['_p'] / em.groupby(['tipo', 'rol', 'mes'])['_p'].transform('median')
emr = em.groupby('ean')['_rel'].median()
bad = set(emr[(emr < 1 / g['FACTOR_PLAUS']) | (emr > g['FACTOR_PLAUS'])].index)
P = P[~P['ean'].isin(bad)]
# precios de una empresa fuera de escala (misma regla de la CELDA 7): mediana de la empresa para el código y mes contra
# la mediana entre empresas (con >= 3), fuera de [1/FACTOR_EMPRESA, FACTOR_EMPRESA]. Los nombres de las empresas salen
# de los diccionarios de la CELDA 3
c3 = cells[2]
emp = {}
for nombre in ('NOMBRES_SIMPLES', 'EMPRESAS'):
    i = c3.index(nombre + ' = {')
    exec(c3[i:c3.index('}', i) + 1], emp)
P['empresa'] = P['id_comercio'].map(lambda c: emp['EMPRESAS'].get(c) or emp['NOMBRES_SIMPLES'].get(c) or f'Cadena {c}')
FE = g.get('FACTOR_EMPRESA', 2.5)
ce = P.groupby(['ean', 'mes', 'empresa'])['p100'].median().rename('pe').reset_index()
ce['ne'] = ce.groupby(['ean', 'mes'])['empresa'].transform('size')
ce['rel'] = ce['pe'] / ce.groupby(['ean', 'mes'])['pe'].transform('median')
at = ce[(ce['ne'] >= 3) & ((ce['rel'] > FE) | (ce['rel'] < 1 / FE))]
P = P.merge(at[['ean', 'mes', 'empresa']].assign(_at=1), on=['ean', 'mes', 'empresa'], how='left')
P = P[P['_at'].isna()].drop(columns='_at')
_at_nb = SIM / 'sim_precios_atipicos.parquet'
print(f'Precios de una empresa fuera de escala: independiente {len(at)} empresa-código-mes | nb06 '
      f'{len(pd.read_parquet(_at_nb)) if _at_nb.exists() else "?"}')
sg = pd.read_parquet(SIM / 'sim_suc_geo.parquet')[['id_comercio', 'id_bandera', 'id_sucursal']]
P = P.merge(sg, on=['id_comercio', 'id_bandera', 'id_sucursal'])          # mismo universo de sucursales
P['prod'] = P['ean'].map(PROD).fillna(P['ean'])          # producto con dos códigos: cuenta una vez
P['subtipo'] = P['ean'].map(SUB)
_ks = ['id_comercio', 'id_bandera', 'id_sucursal', 'mes', 'tipo']
_kb = _ks + ['subtipo', 'rol']
SS = P.groupby(_kb + ['prod'])['p100'].median().groupby(level=_kb).median().unstack('rol').dropna()
SS['brecha'] = (SS['sin'] / SS['tacc'] - 1) * 100
S = np.exp(np.log(SS[['tacc', 'sin']]).groupby(level=_ks).mean())    # tipo: promedio geométrico de sus subtipos
S['brecha'] = (S['sin'] / S['tacc'] - 1) * 100
S, SS = S.reset_index(), SS.reset_index()

sim = pd.read_parquet(SIM / 'sim_bt_sm.parquet')
sims = pd.read_parquet(SIM / 'sim_bt_sub.parquet')
dd = pd.read_parquet(SIM / 'sim_datos_dia.parquet', columns=['id_comercio', 'id_bandera', 'id_sucursal', 'ean_norm', 'mes',
                                                            'precio', 'dias'])
print(f'Plausibilidad: independiente {sorted(bad)} | nb06 {sorted(pd.read_parquet(SIM / "sim_plausibilidad.parquet").get("ean_norm", pd.Series(dtype=str)))}')
# 1) precio mensual por sucursal x EAN: mediana exacta (s8) vs nb06
m = P.merge(dd, left_on=['id_comercio', 'id_bandera', 'id_sucursal', 'ean', 'mes'],
            right_on=['id_comercio', 'id_bandera', 'id_sucursal', 'ean_norm', 'mes'], how='left', indicator=True)
print('\nPares sucursal x EAN x mes (independiente -> nb06):', m['_merge'].value_counts().to_dict())
both = m[m['_merge'] == 'both']
print(f'Precio mensual: max |dif| relativa = {np.nanmax(np.abs(both["precio"] / both["precio_mediana"] - 1)):.2e} '
      f'| días iguales: {(both["dias_x"] == both["dias_y"]).mean():.4f}')
# 2) brecha por sucursal x mes x subtipo y x tipo
b2 = SS.merge(sims[_ks + ['subtipo', 'brecha_pct']], on=_ks + ['subtipo'], how='outer', indicator=True)
print('\nSucursal x mes x subtipo:', b2['_merge'].value_counts().to_dict())
bb2 = b2[b2['_merge'] == 'both']
print(f'Brecha del subtipo: max |dif| = {np.nanmax(np.abs(bb2["brecha"] - bb2["brecha_pct"])):.2e} pp')
b = S.merge(sim[_ks + ['brecha_pct']], on=_ks, how='outer', indicator=True)
print('Sucursal x mes x tipo:', b['_merge'].value_counts().to_dict())
bb = b[b['_merge'] == 'both']
print(f'Brecha del tipo: max |dif| = {np.nanmax(np.abs(bb["brecha"] - bb["brecha_pct"])):.2e} pp')
# 3) brecha por tipo y mes: mediana de cada subtipo entre sucursales; tipo = promedio geométrico de sus subtipos
def tipo_desde_subtipos(df, keys):
    # subtipos con >= MIN_SUC_SUBTIPO sucursales en el grupo; en la serie mensual, además, >= FRAC_SUBTIPO_MES de sus
    # sucursales habituales, y el faltante se imputa con su último mes válido (las reglas de la CELDA 8)
    df = df.assign(_suc=df['id_comercio'] + '|' + df['id_bandera'] + '|' + df['id_sucursal'])
    q = df.groupby(keys + ['tipo', 'subtipo']).agg(m=('brecha', 'median'), n=('_suc', 'nunique')).reset_index()
    ok = q['n'] >= g.get('MIN_SUC_SUBTIPO', 1)
    if keys == ['mes']:
        ok &= q['n'] >= g.get('FRAC_SUBTIPO_MES', 0) * q.groupby(['tipo', 'subtipo'])['n'].transform('median')
        w = q[ok].pivot_table(index='mes', columns=['tipo', 'subtipo'], values='m').reindex(sorted(df['mes'].unique()))
        lm = np.log1p(w / 100).ffill().stack(['tipo', 'subtipo'])
    else:
        lm = np.log1p(q[ok].set_index(keys + ['tipo', 'subtipo'])['m'] / 100)
    return np.expm1(lm.groupby(level=keys + ['tipo']).mean()) * 100
ind = tipo_desde_subtipos(SS, ['mes']).rename('independiente')
nb = pd.read_parquet(SIM / 'sim_brecha_tipo_mensual.parquet').set_index(['mes', 'tipo'])['brecha_mediana'].rename('nb06')
c3 = pd.concat([ind, nb], axis=1)
print(f'Brecha por tipo y mes: {len(c3)} celdas, max |dif| = {np.nanmax(np.abs(c3["independiente"] - c3["nb06"])):.2e} pp')
print('\nBrecha por tipo y año (subtipos primero, independiente):')
SS['anio'] = SS['mes'].str[:4]
print(tipo_desde_subtipos(SS, ['anio']).unstack('tipo').round(1).to_string())
