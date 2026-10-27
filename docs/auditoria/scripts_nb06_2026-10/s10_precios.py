# Verificación con precios (precio mensual por sucursal x EAN de s8, ene-2022 -> oct-2026, zips semestrales del Drive)
# de los candidatos de s9_seleccion.py y armado de la canasta final con composición espejada por subtipo (con TACC de
# la misma marca que un sin TACC primero) y las líneas (variantes de una misma marca y presentación). Uso:
#   python -I -X utf8 s10_precios.py <seleccion.parquet de s9> <carpeta precios_mes> <carpeta precios_mes_2>
#                                    <catálogo 22/10 (.parquet de s3)> <salida.csv>
import json, re, sys
from pathlib import Path
import numpy as np
import pandas as pd

F_SEL, D1, D2, F_CAT, F_OUT = (Path(a) for a in sys.argv[1:6])
pd.set_option('display.width', 330); pd.set_option('display.max_colwidth', 60); pd.set_option('display.max_rows', 900)
FILTRAR = {'19', '2013', '3001', '4', '23', '24'}
BANDA_TIER = (0.6, 1 / 0.6)     # lado CON TACC: precio $/100 g relativo a la mediana del lado (marcas de primera línea)
# Identidad (no precios relativos): los problemas vistos son de otra escala que la dinámica de precios relativos de
# 2024-2026 (que mueve marcas líderes +-50%): códigos viejos con precio congelado (/4-5), sin TACC mal etiquetados
# (/3-4), presentaciones mal cargadas (x2-10). Se marca solo lo grosero.
ESTAB = (0.4, 2.5)              # precio real (contra la evolución de su tipo): últimos 6 meses / primeros 6
SALTO = 2.5                     # salto propio mes a mes (contra la variación típica de su tipo)
EMPALME_OK = (0.8, 1.25)        # precio de cada código / mediana de los códigos del producto, en los meses en que conviven
# Comparador con TACC fijado por tamaño: cuando el de más cobertura es de otra presentación que el sin TACC y el precio
# por 100 g depende del paquete. En obleas, la Santa María sin TACC es de 90 g y la Opera de más cobertura, de 220 g
# (decisión del usuario, 2026-10-26: sumar la Opera rellena de 92 g). Con la de 92 g SOLA, en 2023 casi no hay sucursales
# con los dos lados (0 a 16: la 92 g no estaba en las cadenas de la Santa María) y la serie arrastra +390% durante 17
# meses. Con las DOS la cobertura es la de antes (626 sucursales) y, donde conviven, el lado con TACC es el promedio de
# las dos presentaciones (obleas 2024-2026: +132%, +98%, +132% contra +173%, +112%, +137% con la de 220 g sola). Entran
# todas las listadas aunque el subtipo tenga un solo sin TACC.
COMPARADOR_FIJO = {('Galletitas dulces', 'Obleas'): ['7790040008175', '77903518']}
N_MIN_SUC = 30                  # sucursales mínimas para usar el precio nacional de un EAN en un mes
# Gramos verificados a mano con evidencia fechada (mandan sobre el Maestro y el SEPA). Wakas: la bolsa vieja es de
# 250 g (Maestro, GS1: un código nuevo por cambio de contenido) y la caja nueva de 300 g (4 cadenas en oct-2026; en
# jun-sep 2024, en las mismas sucursales de la Coop. Obrera, la caja costaba 26% más que la bolsa = el mismo precio por
# gramo; misma cotización que el penne Wakas de 300 g en todas las cadenas). Cencosud publica la bolsa como alias de la
# caja desde ago-2024: la vigencia de la bolsa termina en 2024-07 (s9).
GRAMOS_FIJOS = {'7798031470024': 250, '7798031470031': 250, '7798031470048': 250, '7798031470086': 250,
                '7798031470093': 250, '7798031470796': 300, '7798031470826': 300, '7798031470802': 300,
                '7798031470819': 300, '7798031470833': 300}
# Descripciones corregidas: el Maestro cruza los sabores de estos dos Crisppino (Carrefour y Cencosud coinciden)
DESC_FIJA = {'7798199770134': 'Galletitas de Arroz sin TACC Sabor Jamón Crisppino 100 Gr',
             '7798199770141': 'Galletitas de Arroz sin TACC Sabor Queso Crisppino 100 Gr',
             # el Maestro dice "Fideos Mostachol 5 Cereales"; todas las cadenas: spaghetti sin TACC Matarazzo 500 g
             '7790070336002': 'Fideos Spaghetti sin TACC Matarazzo 500 Gr',
             # cajas Wakas: el Maestro dice 250 g (ver GRAMOS_FIJOS)
             '7798031470796': 'Fideos Fusilli con Maíz sin TACC Caja Wakas 300 Gr',
             '7798031470826': 'Fideos Fusilli con Quinoa sin TACC Caja Wakas 300 Gr',
             '7798031470802': 'Fideos Fusilli con Amaranto sin TACC Caja Wakas 300 Gr',
             '7798031470819': 'Fideos Fusilli con Chía sin TACC Caja Wakas 300 Gr',
             '7798031470833': 'Fideos Fusilli con Kale sin TACC Caja Wakas 300 Gr'}
# Marca corregida (para el comparador de la misma marca y las líneas): el Maestro dice "Matarazzo" para el tirabuzón
# Lucchetti y "Luchetti" para los mostacholes y el tallarín
MARCA_FIJA = {'EMP:Tirabuzones Lucchetti 500 g': 'LUCCHETTI', 'EMP:Mostacholes Lucchetti 500 g': 'LUCCHETTI',
              'EMP:Tallarín Lucchetti 500 g': 'LUCCHETTI'}
# Líneas (decisión del usuario, 2026-10-26, noche): los productos de una misma marca y presentación en el subtipo y
# lado que cuestan lo mismo (sabores o variantes) son UNA línea y entran una vez en la mediana de su lado (columna
# linea; gen_nb06 junta sus códigos en PRODUCTO). Si cada sabor contara, mandaría la marca con más sabores: Crisppino
# tenía 5 de los 6 sin TACC de saborizadas y Wakas 4 de los 5 de tirabuzón. Mismo precio: el $/100 g de cada variante
# a ±10% de la mediana de su línea (mediana de los meses en que conviven); si no, es otro producto y cuenta solo (los
# Anillos y la Boca de Dama de Terrabusi, 170 g los dos, difieren 36%). La selección (composición espejada) sigue
# contando productos. Nombre de cada línea, sin el número de variantes (se agrega); una línea que no esté acá toma un
# nombre automático.
LINEA_PRECIO = (0.9, 1 / 0.9)
NOMBRE_LINEA = {
    ('Almohaditas rellenas', 'sin_tacc', 'SNUKS', '240 Gr'): 'Almohaditas rellenas sin TACC Snuks 240 g',
    ('Almohaditas rellenas', 'tacc', 'LASFOR', '200 Gr'): 'Almohaditas rellenas Lasfor 200 g',
    ('Tirabuzón / fusilli', 'sin_tacc', 'WAKAS', '250 Gr'): 'Fusilli sin TACC Wakas',
    ('Rellenas', 'sin_tacc', 'SMAMS', '105 Gr'): 'Galletitas rellenas sin TACC Smams 105 g',
    ('Secas (vainilla, limón, chocolate)', 'sin_tacc', 'SANTA MARIA', '200 Gr'): 'Galletitas sin TACC Santa María 200 g',
    ('Crackers y galletas de arroz', 'sin_tacc', 'SMAMS', '150 Gr'): 'Crackers sin TACC Smams 150 g',
    ('Crackers y galletas de arroz', 'sin_tacc', 'GRANDIET', '100 Gr'): 'Galletas de arroz Grandiet 100 g',
    ('Saborizadas / snack', 'sin_tacc', 'CRISPPINO', '100 Gr'): 'Galletas de arroz saborizadas Crisppino 100 g',
    ('Saborizadas / snack', 'sin_tacc', 'CRISPPINO', '50 Gr'): 'Galletas de arroz saborizadas Crisppino Minis 50 g',
    ('Saborizadas / snack', 'tacc', 'SALADIX', '100 Gr'): 'Galletitas saborizadas Saladix 100 g'}

sel = pd.read_parquet(F_SEL)
MIEM = pd.read_parquet(F_SEL.with_name(F_SEL.stem + '_miembros.parquet')).drop_duplicates('id').set_index('id')
VIG = {k: tuple(v) for k, v in json.loads(F_SEL.with_name(F_SEL.stem + '_vigencia.json').read_text(encoding='utf-8')).items()}
cat = pd.read_parquet(F_CAT)
cat['id'] = cat['id_producto'].astype(str).str.strip().str.lstrip('0')
cat = cat.drop_duplicates('id').set_index('id')

def en_vigencia(e, mes):
    d, h = VIG.get(e, (None, None))
    return (d is None or mes >= d) and (h is None or mes <= h)

# ── Gramos: presentación del maestro o descripción; contra el SEPA del 22/10 ───────────────────────────────────────
RE_G = re.compile(r'(\d+(?:[.,]\d+)?)\s*(kg|kgs|kilo|gr|grs|grm|g|gramos)\b', re.IGNORECASE)
def g_txt(s):
    m = RE_G.search(str(s))
    if not m:
        return np.nan
    v = float(m.group(1).replace(',', '.'))
    return v * 1000 if m.group(2).lower().startswith('k') else v

rows = []
cand = sel[sel['pasa'] & sel['subtipo'].ne('(fuera)')]
for r in cand.itertuples(index=False):
    for e in r.codigos.split(','):
        e = e.strip()
        src = MIEM.loc[e] if e in MIEM.index else (sel.set_index('id').loc[e] if e in set(sel['id']) else None)
        desc = src['descripcion'] if src is not None else None
        pres = src['presentacion'] if src is not None else None
        g1, g2 = g_txt(pres), g_txt(desc)
        g3 = cat['gramos'].get(e, np.nan) if e in cat.index else np.nan
        rows.append({'item': r.id, 'grupo': r.grupo, 'tipo': r.tipo_nb06, 'subtipo': r.subtipo, 'lado': r.lado,
                     'ean': e, 'descripcion': desc, 'presentacion': pres,
                     'desc_sepa_22oct': cat['descripcion'].get(e) if e in cat.index else None,
                     'g_maestro': g1, 'g_desc': g2, 'g_sepa': g3, 'gramos': g1 if g1 == g1 else g2,
                     'desde': VIG.get(e, (None, None))[0], 'hasta': VIG.get(e, (None, None))[1],
                     'suc_mes_mediana': r.suc_mes_mediana})
E = pd.DataFrame(rows)
E['g_fijo'] = E['ean'].map(GRAMOS_FIJOS)
E['gramos'] = E['g_fijo'].fillna(E['gramos'])
E['descripcion'] = E['ean'].map(DESC_FIJA).fillna(E['descripcion'])
# presentación distinta en el Maestro y en el SEPA de oct-2026 sin evidencia de cuándo cambió (Porteñitas 130 -> 139 g):
# el producto queda afuera (no se puede pasar a $/100 g todo el período)
E['g_conflicto'] = [(f != f and a == a and b == b and abs(a / b - 1) > 0.05)
                    for f, a, b in zip(E['g_fijo'], E['gramos'], E['g_sepa'])]

# ── Precios: mediana nacional mensual por EAN (entre sucursales), solo los EANs candidatos ─────────────────────────
fs = sorted(D1.glob('*.parquet')) + sorted(D2.glob('*.parquet'))
_ce = sorted(set(E['ean']))
P = pd.concat([pd.read_parquet(f, columns=['id_comercio', 'id_bandera', 'id_sucursal', 'ean', 'precio_mediana', 'mes'],
                               filters=[('ean', 'in', _ce)]) for f in fs], ignore_index=True)
P = P[~P['id_comercio'].isin(FILTRAR)]
# un EAN puede estar en las dos extracciones (7790070318329): una fila por sucursal x EAN x mes
P = P.drop_duplicates(['id_comercio', 'id_bandera', 'id_sucursal', 'ean', 'mes'])
N = P.groupby(['ean', 'mes']).agg(p=('precio_mediana', 'median'), n=('precio_mediana', 'size')).reset_index()
N = N[N['n'] >= N_MIN_SUC]
N = N[[en_vigencia(e, m) for e, m in zip(N['ean'], N['mes'])]]
MESES = sorted(N['mes'].unique())
print(f'Precios: {len(fs)} archivos de mes, {MESES[0]} -> {MESES[-1]} ({len(MESES)} meses), {N["ean"].nunique()} EANs')
_sin = sorted(set(E['ean']) - set(P['ean']))
if _sin:
    print(f'AVISO: candidatos sin ningún precio en las extracciones: {_sin}')

N = N[N['ean'].isin(set(E['ean']))].merge(E[['ean', 'item', 'tipo', 'lado', 'gramos']], on='ean')
N['p100'] = N['p'] / N['gramos'] * 100

# ── Empalmes: cada código contra la mediana de los códigos de su producto, en los meses en que conviven ────────────
emp_rows = []
for it, g in N[N['item'].str.startswith('EMP:')].groupby('item'):
    w = g.pivot_table(index='mes', columns='ean', values='p100')
    w = w[w.notna().sum(axis=1) >= 2]
    if w.empty:
        continue
    med = w.median(axis=1)
    for e in w.columns:
        r_ = (w[e] / med).dropna()
        if len(r_):
            emp_rows.append({'item': it, 'ean': e, 'meses_juntos': len(r_), 'codigo_sobre_producto': float(r_.median())})
EMP = pd.DataFrame(emp_rows)
if len(EMP):
    EMP['ok'] = EMP['codigo_sobre_producto'].between(*EMPALME_OK)
    print('\n=== Empalmes: precio de cada código / mediana de los códigos del producto (meses en que conviven) ===')
    print(EMP.round(3).to_string(index=False))

# precio de cada PRODUCTO por mes = mediana de sus códigos vigentes
I = N.groupby(['item', 'tipo', 'lado', 'mes'])['p100'].median().reset_index()
I = I.merge(sel[['id', 'subtipo']].rename(columns={'id': 'item'}), on='item', how='left')
# franja de precio (con TACC) y prima (sin TACC): contra la mediana con TACC del mismo tipo y SUBTIPO y mes
st = I[I['lado'] == 'tacc'].groupby(['tipo', 'subtipo', 'mes'])['p100'].median().rename('med_tacc_sub').reset_index()
I = I.merge(st, on=['tipo', 'subtipo', 'mes'], how='left')
I['rel_tier'] = I['p100'] / I['med_tacc_sub']
I['prima'] = I['p100'] / I['med_tacc_sub']
# estabilidad e identidad: cada producto contra los de su mismo TIPO y LADO (los dos lados tuvieron dinámicas distintas
# en 2023: precios controlados de las marcas masivas con TACC y recuperación en oct-2023 / ene-2024):
# - salto propio en un mes: su variación menos la mediana de las variaciones de su lado en ese mes (> x2,5 = otro
#   producto, una presentación mal cargada o un precio congelado);
# - nivel: su $/100 g sobre la mediana de su lado en el mes, primeros 6 meses contra últimos 6 (fuera de [0,4; 2,5]).
#   Sin encadenar: la mediana de las variaciones mensuales encadenada se queda atrás de los precios cuando los aumentos
#   son escalonados (2022-2023: muchos meses sin cambio y saltos grandes) y marcaba como inestables a casi todos.
I = I.sort_values(['item', 'mes'])
I['_mi'] = I['mes'].map({m: i for i, m in enumerate(MESES)})
I['dlog'] = np.where(I.groupby('item')['_mi'].diff() == 1, np.log(I['p100']) - np.log(I.groupby('item')['p100'].shift()), np.nan)
ref = I.groupby(['tipo', 'lado', 'mes'])['dlog'].median().rename('dref').reset_index()
I = I.merge(ref, on=['tipo', 'lado', 'mes'], how='left')
I['res'] = I['dlog'] - I['dref']
I['ref_nivel'] = I.groupby(['tipo', 'lado', 'mes'])['p100'].transform('median')
I['real'] = I['p100'] / I['ref_nivel']

# ── Productos con vigencia: salto en el mes del corte (relativo a su tipo) y precios de cada código alrededor del
# corte SIN filtrar la vigencia (¿el código viejo sigue vivo? ¿el nuevo arranca al mismo precio por gramo?) ─────────
NA = P.groupby(['ean', 'mes']).agg(p=('precio_mediana', 'median'), n=('precio_mediana', 'size')).reset_index()
NA = NA.merge(E[['ean', 'item', 'gramos']].drop_duplicates('ean'), on='ean')
NA['p100'] = NA['p'] / NA['gramos'] * 100
corte_rows = []
print('\n=== Productos con vigencia: $/100 g (sucursales) de cada código alrededor del corte, sin filtrar la vigencia ===')
for it, g in NA[NA['item'].str.startswith('EMP:')].groupby('item'):
    cods = sorted(set(g['ean']))
    cortes = sorted({VIG[e][0] for e in cods if e in VIG and VIG[e][0]})
    if not cortes or cortes[0] not in MESES:
        continue
    m0 = cortes[0]
    i0 = MESES.index(m0)
    x = g[g['mes'].isin(MESES[max(0, i0 - 3): i0 + 4])]
    tp_ = x.pivot_table(index='mes', columns='ean', values='p100').round(0)
    tn_ = x.pivot_table(index='mes', columns='ean', values='n')
    print(f'-- {it}: corte {m0} | vigencias ' + ', '.join(f'{e} {VIG.get(e)}' for e in cods))
    print(tp_.map(lambda v: '' if v != v else f'{v:,.0f}').astype(str).add(' (')
          .add(tn_.map(lambda v: '' if v != v else f'{v:.0f}').astype(str)).add(')').to_string())
    s_ = I[(I['item'] == it) & (I['mes'] == m0)]
    corte_rows.append({'item': it, 'corte': m0,
                       'salto_relativo_al_tipo': float(np.exp(s_['res'].iloc[0])) if len(s_) and s_['res'].notna().iloc[0]
                       else np.nan})
CORTE = pd.DataFrame(corte_rows, columns=['item', 'corte', 'salto_relativo_al_tipo'])
CORTE['ok'] = CORTE['salto_relativo_al_tipo'].between(0.8, 1.25) | CORTE['salto_relativo_al_tipo'].isna()
print(CORTE.round(3).to_string(index=False))

# mes del corte de cada producto con vigencia: su salto se diagnostica aparte (CORTE) y no cuenta como salto propio
# (los cortes de Molinos de oct-2023 coinciden con la salida de los precios controlados: el código nuevo cuesta
# 2,6-3,4 veces el viejo en las mismas sucursales)
_corte_item = {}
for _it, _cods in sel.loc[sel['id'].str.startswith('EMP:'), ['id', 'codigos']].itertuples(index=False):
    _ds = sorted({VIG[e][0] for e in _cods.split(',') if e in VIG and VIG[e][0]})
    if _ds:
        _corte_item[_it] = _ds[0]

# Transición de precios oct-2023 -> mar-2024: Molinos sale de los precios controlados cambiando los códigos (oct-2023;
# el nuevo cuesta 2,6-3,4 veces el viejo en las mismas sucursales), el resto de las marcas masivas con TACC al terminar
# Precios Justos (ene-2024: +87% galletitas dulces, +105% saladas, +118% rebozador con TACC contra +26-36% de los sin
# TACC), hueco de Molinos dic-2023 -> mar-2024 y devaluación de dic-2023. Los niveles relativos se mueven por precios,
# en momentos distintos según la marca, no por identidad: ninguna ventana de la regla de saltos cruza esos meses (la
# estabilidad de punta a punta, primeros contra últimos 6 meses, sigue cubriendo todo el período).
TRANSICION = ('2023-10', '2024-03')

def saltos_persistentes(real, meses, corte):
    # Cambios de nivel propios (relativos a su lado) > x2,5 que PERSISTEN: la mediana de los 3 meses desde t contra la de
    # los 3 meses anteriores. Un cambio de producto o de presentación persiste; un dato erróneo de un mes en una cadena
    # (DIA en sep-2026 con las chips Smams a un tercio, jul-2023 con la mitad de los comercios) no mueve la mediana. Los 3
    # meses desde el corte de un código no cuentan (su salto se diagnostica en CORTE).
    L = np.log(real)
    n = 0
    for i in range(1, len(L)):
        if corte and meses[i] >= corte and (pd.Period(meses[i], 'M') - pd.Period(corte, 'M')).n <= 2:
            continue
        if not (meses[min(len(L) - 1, i + 2)] < TRANSICION[0] or meses[max(0, i - 3)] > TRANSICION[1]):
            continue
        a, b = L[max(0, i - 3):i], L[i:i + 3]
        a, b = a[np.isfinite(a)], b[np.isfinite(b)]
        if len(a) and len(b) and abs(np.median(b) - np.median(a)) > np.log(SALTO):
            n += 1
    return n

def resumen(g, item):
    g = g.sort_values('mes')
    re_ = g['real'].to_numpy()
    _c = _corte_item.get(item)
    _res = np.where(g['mes'] == _c, 0.0, g['res'].to_numpy()) if _c else g['res'].to_numpy()
    return {'meses_precio': len(g), 'p100_ultimo': g['p100'].iloc[-1], 'mes_ultimo': g['mes'].iloc[-1],
            'rel_tier': float(g['rel_tier'].median()),
            'estab': float(np.median(re_[-6:]) / np.median(re_[:6])),
            'saltos': saltos_persistentes(re_, g['mes'].to_numpy(), _c),
            'saltos_un_mes': int(np.nansum(np.abs(_res) > np.log(SALTO))),
            'prima_mediana': float(g['prima'].median()), 'prima_min': float(g['prima'].min())}
Q = pd.DataFrame([{'item': it, 'tipo': tp_, 'lado': ld, **resumen(g, it)}
                  for (it, tp_, ld), g in I.groupby(['item', 'tipo', 'lado'])])
Q['ok_tier'] = np.where(Q['lado'] == 'tacc', Q['rel_tier'].between(*BANDA_TIER), True)
Q['ok_estab'] = Q['estab'].between(*ESTAB) & (Q['saltos'] == 0)
# sin TACC más barato que el con TACC de su subtipo: ¿mal etiquetado? (sin con TACC en el subtipo: no se controla)
Q['ok_prima'] = np.where((Q['lado'] == 'sin_tacc') & Q['prima_mediana'].notna(), Q['prima_mediana'] >= 1.0, True)
mal = set(EMP.loc[~EMP['ok'], 'item']) if len(EMP) else set()
Q['ok_empalme'] = ~Q['item'].isin(mal)
Q = Q.merge(sel[['id', 'subtipo', 'descripcion', 'suc_mes_mediana', 'caidas', 'cob_2022_sobre_2026', 'provincias',
                 'comercios_super', 'cadenas_grandes', 'pct_cadena_principal', 'codigos', 'grupo', 'marca_n',
                 'presentacion']].rename(columns={'id': 'item'}), on='item', how='left')
Q['marca_n'] = Q['item'].map(MARCA_FIJA).fillna(Q['marca_n'])
# cobertura al final: sucursales por día en oct-2026 (nb09, SEPA diario al 22/10) >= 25% de su mediana mensual (si no,
# el producto casi desapareció). El catálogo del 22/10 (s1-s3) no tiene todos los productos (filtra por palabras).
SER = pd.read_parquet(F_SEL.with_name(F_SEL.stem + '_serie.parquet'))
MES_FIN = max(SER.columns)
Q['suc_dia_mes_fin'] = Q['item'].map(SER[MES_FIN])
Q['suc_22oct_item'] = [sum(cat['sucursales'].get(e, 0) for e in str(c).split(',')) for c in Q['codigos']]
Q['ok_final'] = Q['suc_dia_mes_fin'] >= 0.25 * Q['suc_mes_mediana']
Q['ok_gramos'] = ~Q['item'].isin(set(E.loc[E['g_conflicto'], 'item']))
# salto en el corte de código > 25% (relativo a su tipo): se INFORMA, no excluye. Los cortes de Molinos de oct-2023
# coinciden con la salida de los precios controlados (salto real de precio, no otro producto): la identidad de los
# empalmes se verificó por descripción, presentación y precio por gramo en los meses en que conviven
Q['ok_corte'] = ~Q['item'].isin(set(CORTE.loc[~CORTE['ok'], 'item']))
# ok_prima se informa pero NO excluye: la condición de sin TACC la dan la etiqueta y la marca, y sacar los sin TACC
# baratos sesgaría la brecha para arriba
Q['ok_todo'] = Q[['ok_tier', 'ok_estab', 'ok_empalme', 'ok_final', 'ok_gramos']].all(axis=1)
print(f'Cobertura final: {MES_FIN} (nb09)')
cols = ['tipo', 'subtipo', 'lado', 'descripcion', 'suc_mes_mediana', 'suc_dia_mes_fin', 'suc_22oct_item',
        'meses_precio', 'p100_ultimo', 'rel_tier', 'estab', 'saltos', 'prima_mediana', 'prima_min', 'ok_tier',
        'ok_estab', 'ok_prima', 'ok_empalme', 'ok_final', 'ok_gramos', 'ok_corte', 'ok_todo']
print('\n=== Verificación con precios ===')
print(Q.sort_values(['tipo', 'subtipo', 'lado', 'suc_mes_mediana'], ascending=[True, True, True, False])[cols]
      .round(3).to_string(index=False))
print('\n=== Gramos con conflicto (maestro/descripción vs SEPA 22/10) ===')
print(E[E['g_conflicto']][['tipo', 'ean', 'descripcion', 'desc_sepa_22oct', 'g_maestro', 'g_desc', 'g_sepa']].to_string(index=False))
print('\n=== EANs sin gramos ===')
print(E[E['gramos'].isna()][['tipo', 'ean', 'descripcion', 'desc_sepa_22oct', 'g_sepa']].to_string(index=False))

# ── Canasta final: composición espejada por subtipo ─────────────────────────────────────────────────────────────────
# Equivalentes primero (panel de expertos, 2026-10-27): el lado sin TACC de un subtipo lleva el MISMO producto (crackers
# sin TACC contra crackers) cuando hay uno que cumple todas las reglas. Un SUSTITUTO de otro producto (galletas o tostadas
# de arroz: además son naturalmente sin gluten y las compra cualquiera) entra solo si el subtipo no tiene equivalente
# (saborizadas: no hay galletitas saborizadas sin TACC continuas 2022-2026). Con galletas de arroz en crackers la canasta
# mezclaba "la versión sin TACC del mismo producto" con "lo que puede comprar en su lugar"; los sustitutos que quedan
# afuera van a productos_sensibilidad.csv (escenario de la CELDA 8c del nb06).
SUSTITUTO = {'Galletitas saladas y crackers': re.compile(
    r'\bgalletas? de arroz\b|\bgalletitas? (?:de )?arroz\b|\btostad\w* de arroz\b', re.IGNORECASE)}
RENOMBRAR_SUBTIPO = {('Galletitas saladas y crackers', 'Crackers y galletas de arroz'): 'Crackers'}
ok = Q[Q['ok_todo']].copy()
ok['sustituto'] = [bool(SUSTITUTO[t].search(str(d))) if t in SUSTITUTO and l == 'sin_tacc' else False
                   for t, l, d in zip(ok['tipo'], ok['lado'], ok['descripcion'])]
fin, sust_fuera, fijo_fuera, subtipos_ok = [], set(), set(), set()
for (t, st), g in ok.groupby(['tipo', 'subtipo']):
    s_ = g[g['lado'] == 'sin_tacc'].sort_values('suc_mes_mediana', ascending=False)
    if s_['sustituto'].any() and (~s_['sustituto']).any():
        sust_fuera |= set(s_.loc[s_['sustituto'], 'item'])
        s_ = s_[~s_['sustituto']]
    # con TACC: primero los de la marca de algún sin TACC del subtipo, después por cobertura. El par de la misma marca
    # separa la prima sin TACC de la de marca (decisión del usuario, 2026-10-26, noche): en penne entra el Matarazzo
    # común en lugar de los Mostacholes Lucchetti, como en spaghetti. Una marca con k sin TACC tiene a lo sumo k lugares
    # de la misma marca (2026-10-27: si no, una marca con muchos con TACC llenaba el lado)
    c_ = g[g['lado'] == 'tacc'].sort_values('suc_mes_mediana', ascending=False)
    c_ = (c_.assign(_misma_marca=c_.groupby('marca_n').cumcount() < c_['marca_n'].map(s_['marca_n'].value_counts()).fillna(0))
          .sort_values(['_misma_marca', 'suc_mes_mediana'], ascending=False, kind='stable').drop(columns='_misma_marca'))
    if (t, st) in COMPARADOR_FIJO:
        fijo_fuera |= set(c_.loc[~c_['item'].isin(COMPARADOR_FIJO[(t, st)]), 'item'])
        c_ = c_[c_['item'].isin(COMPARADOR_FIJO[(t, st)])]
    if s_.empty or c_.empty:
        print(f'  subtipo sin los dos lados (afuera): {t} / {st} (sin TACC {len(s_)}, con TACC {len(c_)})')
        continue
    subtipos_ok.add((t, st))
    fin.append(s_)
    fin.append(c_ if (t, st) in COMPARADOR_FIJO else c_.head(len(s_)))
F = pd.concat(fin, ignore_index=True)
if sust_fuera:
    print(f'  sustitutos afuera (el subtipo tiene un sin TACC equivalente): '
          f'{sorted(ok.loc[ok["item"].isin(sust_fuera), "descripcion"])}')

# ── Líneas: misma marca y presentación en el subtipo y lado, y mismo precio (NOMBRE_LINEA, LINEA_PRECIO) ─────────────
def nombre_linea(k, n, producto, avisar=True):
    if n < 2:
        return producto
    base = NOMBRE_LINEA.get(k)
    if base is None:
        base = f"{k[0]}{' sin TACC' if k[1] == 'sin_tacc' else ''} {k[2].title()} {k[3]}"
        if avisar:
            print(f'AVISO: línea sin nombre en NOMBRE_LINEA: {k} -> «{base}»')
    return f'{base} ({n} variantes)'


def asignar_lineas(D, avisar=True):
    # columna linea: las variantes de una misma marca y presentación en el subtipo y lado que cuestan lo mismo (el
    # $/100 g de cada una a LINEA_PRECIO de la mediana de su línea, mediana de los meses con dos o más variantes)
    D = D.copy()
    D['_lin'] = list(zip(D['subtipo'], D['lado'], D['marca_n'], D['presentacion']))
    li = I.merge(D.loc[D.groupby('_lin')['item'].transform('size') >= 2, ['item', '_lin']], on='item')
    li = li[li.groupby(['_lin', 'mes'])['item'].transform('size') >= 2].copy()
    li['rel'] = li['p100'] / li.groupby(['_lin', 'mes'])['p100'].transform('median')
    lin = (li.groupby(['_lin', 'item'])['rel']
           .agg(meses='size', mediana='median', p10=lambda s: s.quantile(.1), p90=lambda s: s.quantile(.9))
           .reset_index())
    lin['en_linea'] = lin['mediana'].between(*LINEA_PRECIO)
    fuera = set(lin.loc[~lin['en_linea'], 'item'])
    D['_lin'] = [k + (it,) if it in fuera else k for k, it in zip(D['_lin'], D['item'])]
    D['_n_lin'] = D.groupby(['tipo', '_lin'])['item'].transform('size')
    D['linea'] = [nombre_linea(k, n, p, avisar) for k, n, p in zip(D['_lin'], D['_n_lin'], D['descripcion'])]
    # dos productos sueltos con la misma descripción (el rebozador al horno Mamá Cocina de 1 kg tiene dos códigos a
    # precios distintos): se distinguen por el código
    _rep = D['linea'].map(D.drop_duplicates(['linea', '_lin']).groupby('linea').size()) > 1
    D.loc[_rep & (D['_n_lin'] < 2), 'linea'] = D['linea'] + ' (' + D['item'].astype(str) + ')'
    dup = D.drop_duplicates(['linea', 'tipo', '_lin']).groupby('linea').size()
    if (dup > 1).any():
        raise ValueError(f'Nombres de línea o de producto repetidos: {list(dup[dup > 1].index)}')
    return D, lin, fuera


F, LIN, _fuera = asignar_lineas(F)
print('\n=== Líneas: $/100 g de cada variante / mediana de su línea (nacional, meses con dos o más variantes) ===')
print(LIN.assign(_lin=LIN['_lin'].map(lambda k: f'{k[2]} {k[3]} · {k[0]} · {k[1]}')).round(3).to_string(index=False))
if _fuera:
    print(f'Cuestan distinto que su línea (cuentan solos): {sorted(_fuera)}')
# variantes de una línea juntas (la línea por la cobertura de su variante principal)
F['_cob_lin'] = F.groupby(['tipo', 'linea'])['suc_mes_mediana'].transform('max')
F = F.sort_values(['tipo', 'subtipo', 'lado', '_cob_lin', 'linea', 'suc_mes_mediana'],
                  ascending=[True, True, True, False, True, False]).reset_index(drop=True)
print('\n=== Canasta final (productos y líneas) ===')
print(F.groupby(['tipo', 'subtipo', 'lado']).agg(productos=('item', 'size'), lineas=('linea', 'nunique'))
      .unstack('lado').to_string())

# ── Productos para la sensibilidad (CELDA 8c del nb06): todos los que cumplen las reglas en los subtipos de la canasta,
# con la línea que formarían juntos (linea_todos) y por qué quedan afuera de la canasta los que no están ─────────────
U = ok[[(t, st) in subtipos_ok for t, st in zip(ok['tipo'], ok['subtipo'])]].copy()
U, _lin_u, _ = asignar_lineas(U, avisar=False)
U['en_canasta'] = U['item'].isin(set(F['item']))
U['motivo'] = np.select([U['en_canasta'], U['item'].isin(sust_fuera), U['item'].isin(fijo_fuera)],
                        ['', 'sustituto: el subtipo tiene un sin TACC equivalente', 'comparador fijo (obleas)'],
                        'composición espejada')
print(f'\nProductos para la sensibilidad: {len(U)} ({int(U["en_canasta"].sum())} en la canasta) | afuera: '
      + ', '.join(f'{m} {n}' for m, n in U.loc[~U['en_canasta'], 'motivo'].value_counts().items()))


def filas_codigos(D, extra):
    rows = []
    for r in D.itertuples(index=False):
        for e in str(r.codigos).split(','):
            er = E[(E['ean'] == e) & (E['item'] == r.item)].iloc[0]
            sub = RENOMBRAR_SUBTIPO.get((r.tipo, r.subtipo), r.subtipo)
            rows.append({'tipo': r.tipo, 'lado': r.lado, 'ean': e, 'descripcion': er['descripcion'],
                         'gramos': er['gramos'], 'subtipo': sub, 'desde': er['desde'], 'hasta': er['hasta'],
                         **extra(r)})
    return pd.DataFrame(rows)


def _nota(r):
    n = [f'empalme «{r.grupo}»'] if r.grupo else []
    if r.sustituto:
        n.append('sustituto: el subtipo no tiene un sin TACC equivalente continuo')
    return ' · '.join(n)


OUT = filas_codigos(F, lambda r: {
    'nota': _nota(r), 'producto': r.descripcion, 'linea': r.linea,
    'sucursales_dia_mediana_2022_2026': round(r.suc_mes_mediana, 1), 'caidas': r.caidas,
    'cobertura_2022_sobre_2026': round(r.cob_2022_sobre_2026, 2), 'provincias': r.provincias,
    'comercios': r.comercios_super, 'cadenas_grandes': r.cadenas_grandes,
    'pct_cadena_principal': round(r.pct_cadena_principal, 1), 'sucursales_dia_oct2026': round(r.suc_dia_mes_fin, 1),
    'precio_100g_ultimo_mes': round(r.p100_ultimo, 1), 'ultimo_mes_con_precio': r.mes_ultimo,
    # con TACC: posición en la franja de su subtipo; sin TACC: prima sobre los con TACC del subtipo
    'precio_sobre_mediana_con_tacc_subtipo': round(r.rel_tier, 3)})
OUT.to_csv(F_OUT, index=False, encoding='utf-8')
print(f'\nGuardado: {F_OUT} ({len(OUT)} EANs, {F["item"].nunique()} productos, {F["linea"].nunique()} líneas)')
SENS = filas_codigos(U, lambda r: {
    'nota': _nota(r), 'producto': r.descripcion, 'linea_todos': r.linea, 'en_canasta': r.en_canasta,
    'motivo': r.motivo, 'sustituto': r.sustituto, 'sucursales_dia_mediana_2022_2026': round(r.suc_mes_mediana, 1),
    'precio_sobre_mediana_con_tacc_subtipo': round(r.rel_tier, 3)})
F_SENS = F_OUT.with_name('productos_sensibilidad.csv')
SENS.to_csv(F_SENS, index=False, encoding='utf-8')
print(f'Guardado: {F_SENS} ({len(SENS)} EANs, {U["item"].nunique()} productos; {int((~SENS["en_canasta"]).sum())} '
      'códigos fuera de la canasta)')
Q.to_parquet(F_OUT.with_suffix('.verif.parquet'), index=False)
LIN.assign(_lin=LIN['_lin'].map(' | '.join)).rename(columns={'_lin': 'linea_clave'}).to_parquet(
    F_OUT.with_suffix('.lineas.parquet'), index=False)
I.to_parquet(F_OUT.with_suffix('.serie.parquet'), index=False)      # $/100 g nacional por producto y mes
if len(CORTE):
    CORTE.to_parquet(F_OUT.with_suffix('.cortes.parquet'), index=False)
E.to_parquet(F_OUT.with_suffix('.eans.parquet'), index=False)
if len(EMP):
    EMP.to_parquet(F_OUT.with_suffix('.empalmes.parquet'), index=False)
