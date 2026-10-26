# Selección de la canasta fija 2022-2026 de la brecha celíaca con reglas explícitas, sobre la tabla de continuidad
# (s7_continuidad.py, salidas del nb09). Imprime los candidatos por tipo, subtipo y lado con el motivo de cada descarte
# y guarda la tabla con el resultado de cada regla (la verificación con precios y la canasta final: s10_precios.py).
# Uso: python -I -X utf8 s9_seleccion.py <continuidad.parquet> <salida.parquet>
import re, sys, unicodedata
from pathlib import Path
import numpy as np
import pandas as pd

F_CONT, F_OUT = Path(sys.argv[1]), Path(sys.argv[2])
pd.set_option('display.width', 330); pd.set_option('display.max_colwidth', 58); pd.set_option('display.max_rows', 900)

# ── Reglas ──────────────────────────────────────────────────────────────────────────────────────────────────────────
MESES_OFICIALES = 55            # precio todos los meses 2022-01 -> 2026-07 (semestrales oficiales) y en ago-oct 2026
MAX_CAIDAS = 3                  # meses con cobertura < 35% de su mediana móvil de 13 meses (jul-2023 con la mitad de
                                # los comercios, hueco de Molinos dic-2023 / feb-2024, importados a fines de 2023)
RATIO_22_26 = (0.25, 4.0)       # cobertura 2022 / 2026: el producto no puede haber cambiado de escala
REGLAS = {   # lado: sucursales por día (mediana mensual), provincias, comercios súper, cadenas grandes, % cadena principal
    'sin_tacc': dict(suc=100, prov=20, com=4, grandes=3, principal=75),
    'tacc':     dict(suc=300, prov=22, com=8, grandes=5, principal=60),
}
TIPOS_CANASTA = {   # tipo del nb06: tipos de s7 que entran
    'Fideos secos': ['Fideos secos'],
    'Galletitas dulces': ['Galletitas dulces'],
    'Galletitas saladas y crackers': ['Galletitas saladas y tostadas'],
    'Pan rallado y rebozador': ['Pan rallado y rebozador'],
    'Cereales rellenos (almohaditas)': ['Cereales y barras'],
}

def norm(s):
    return unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode('ascii').lower()

# Subtipos (comparabilidad): (nombre, regex) en orden; None = fuera de la canasta (no comparable)
SUBTIPOS = {
    'Fideos secos': [
        # blue patna: todos sus fideos son AL HUEVO (listado ALG de ANMAT, 26/10/2026: "pastas secas de harina de arroz
        # al huevo", RNPA 04036877-80 y 036-00-000548), aunque la descripción del Maestro y del SEPA no lo diga
        (None, r'al huevo|blue patna|integral|vegetal|espinaca|morron|legumbre|alubia|garbanz|lentej|arveja|poroto|'
               r'proteina|\brina\b|nido|cabello|mono|bucat|foratt|guiser|3 minutos|instant|preparad|sabor|queso|fileto|'
               r'\bmix\b|soja|risoni'),
        ('Spaghetti', r'spag|spagu|largos'),
        ('Tallarín / cintas', r'tallar|fettu|fetuc|cinta|linguin'),
        ('Tirabuzón / fusilli', r'tirabu|fusil|tornill|caracol|spiral'),
        ('Mostachol / penne', r'mostach|penne|rigat|pluma'),
        ('Cortos (codito, dedalito, munición...)', r'codit|dedal|municion|ave maria|letrit'),
    ],
    'Galletitas dulces': [
        # \btita\b (las Tita de Terrabusi): sin el \b inicial atrapaba "galletita" en singular, como varias cadenas
        # publican el producto en el SEPA (dejaba afuera, por ejemplo, las Maná rellenas de limón 152 g)
        (None, r'banad|bañad|cubiert|alfajor|tapita|hojald|hojalmar|integral|avena|salvado|granola|cereal|fibra|organic|'
               r'sin azuc|light|dietet|surtid|variedad|kit kat|rhodesia|bon o bon|chocopause|graffiti|habanit|\btita\b|'
               r'brownie|merengu|tripack|3 un|5 un|biscuit|tostad|vainillas\b|okebon|molino natural'),
        ('Obleas', r'oblea|wafer'),
        ('Rellenas', r'rellen'),
        ('Pepas', r'pepa'),
        ('Con chips', r'chip'),
        ('Bizcochos', r'bizcoch|agridulce'),
        ('Secas (vainilla, limón, chocolate)', r'.'),
    ],
    'Galletitas saladas y crackers': [
        # \bdulce: galletas de arroz DULCES (Grandiet 7797330100663, "Galletas de Arroz" en el Maestro) no son saladas
        (None, r'salvado|integral|avena|fibra|bizcochit|grasa|tostad|palito|grisin|sandwich|3 en 1|pack|\bdulce'),
        ('Saborizadas / snack', r'snack|queso|jamon|pizza|oliva|calabresa|kesitas|\brex\b|saladix|chalita'),
        ('Crackers y galletas de arroz', r'cracker|criollit|marinera|\bagua\b|crackines|arroz'),
    ],
    'Pan rallado y rebozador': [
        (None, r'queso|coco|semilla'),
        ('Rebozador', r'rebozad|apanad'),
        ('Pan rallado', r'rallad'),
    ],
    'Cereales rellenos (almohaditas)': [
        ('Almohaditas rellenas', r'almohadit'),
        (None, r'.'),
    ],
}

def subtipo(tipo, d):
    for nombre, rx in SUBTIPOS[tipo]:
        if re.search(rx, d):
            return nombre if nombre else '(fuera)'
    return '(fuera)'

# ── Datos ───────────────────────────────────────────────────────────────────────────────────────────────────────────
c = pd.read_parquet(F_CONT)
SER = pd.read_parquet(F_CONT.with_name(F_CONT.stem + '_serie.parquet'))
OFI = [m for m in SER.columns if m <= '2026-07']

# Meses con defectos conocidos de la fuente, que no cuentan como caídas de un producto: jul-2023 (16-28/07 con la
# mitad de los comercios) y dic-2023 -> mar-2024 (todo Molinos -Lucchetti, Matarazzo, Favorita, Terrabusi, Exquisita,
# Preferido- pasa de ~2.000 a ~100-200 sucursales por día y vuelve en abril-julio de 2024; SEPA_TECNICO).
MESES_DEFECTO = {'2023-07', '2023-12', '2024-01', '2024-02', '2024-03'}
# Cambio de código de Molinos: en un EMPALME, oct-nov 2023 sin precio no cuentan contra la continuidad. El código
# viejo vale hasta sep-2023 (después queda con el precio congelado) y el nuevo de algún producto recién aparece en
# dic-2023: el tirabuzón sin TACC Matarazzo (~1.000 sucursales por día en sep-2023 con el viejo y ~800 de mediana con
# el nuevo). En esos dos meses el producto no entra en la mediana de su lado, como cualquier faltante.
MESES_TOLERADOS_EMPALME = {'2023-10', '2023-11'}

def caidas(serie):
    v = serie.reindex(OFI)
    rm = v.rolling(13, center=True, min_periods=4).median()
    baja = (v < 0.35 * rm)
    return int(baja[[m for m in OFI if m not in MESES_DEFECTO]].sum())

# EMPALMES: el fabricante cambió el código del MISMO producto (misma marca, forma y presentación). Cada código tiene
# una VIGENCIA (desde, hasta; None = sin límite): los códigos viejos de Molinos que quedan después del cambio (sep-oct
# 2023) informan precios CONGELADOS en ~100 sucursales (Mostacholes Lucchetti viejo a $246-337 en 2024-2025 contra
# $1.042-1.700 del nuevo), así que el viejo vale hasta el mes anterior al nuevo. Los códigos intermedios de 2023
# (N°5, N°51, N°52, N°34) quedan afuera: poca cobertura y precios inconsistentes. Wakas (jun-2024) pasó de la bolsa
# de 250 g (códigos ...0024/0031/0048/0086/0093) a la caja de 300 g (...0796/0826/0802/0819/0833): en jun-sep 2024, en
# las mismas sucursales de la Cooperativa Obrera, la caja costaba 26% más que la bolsa (el mismo precio por gramo) y
# desde ago-2024 algunas cadenas publican el código viejo como alias de la caja (Cencosud: mismo precio, mismas
# sucursales, "x300g"). Por eso la bolsa vale hasta 2024-07 (250 g) y la caja desde 2024-06 (300 g; s10 GRAMOS_FIJOS).
# La serie del producto es la suma de sus códigos vigentes.
EMPALMES = {
    'Spaghetti Matarazzo 500 g': {'7790070318640': (None, '2023-09'), '7790070336309': ('2023-10', None)},
    'Spaghetti Lucchetti 500 g': {'7790070318282': (None, '2023-09'), '7790070336385': ('2023-10', None)},
    'Tallarines Matarazzo 500 g': {'7790070318657': (None, '2023-09'), '7790070336316': ('2023-10', None)},
    'Tallarín Lucchetti 500 g': {'7790070318299': (None, '2023-09'), '7790070336118': ('2023-10', None)},
    'Mostacholes Lucchetti 500 g': {'7790070318336': (None, '2023-09'), '7790070336149': ('2023-10', None)},
    'Mostachol rayado Matarazzo 500 g': {'7790070318596': (None, '2023-09'), '7790070336217': ('2023-10', None)},
    'Tirabuzones Lucchetti 500 g': {'7790070318329': (None, '2023-09'), '7790070336026': ('2023-10', None)},
    'Tirabuzones Matarazzo 500 g': {'7790070318602': (None, '2023-09'), '7790070336293': ('2023-10', None)},
    'Penne rigate Matarazzo 500 g': {'7790070318633': (None, '2023-09'), '7790070336200': ('2023-10', None)},
    # Línea sin TACC de Matarazzo anterior a oct-2023 (en 2022 costaba 2-3 veces el Matarazzo común en las mismas
    # sucursales: genuina). Mismo corte que los comunes de Molinos: en sep-oct 2023, en las mismas sucursales, el
    # código nuevo cuesta 2,6-3,4 veces el viejo (el viejo venía con precio controlado) y el viejo queda congelado.
    # El tirabuzón no llega a continuo: su código nuevo recién aparece en dic-2023 (hueco oct-nov 2023).
    'Penne rigate sin TACC Matarazzo 500 g': {'7790070321794': (None, '2023-09'), '7790070335999': ('2023-10', None)},
    'Spaghetti sin TACC Matarazzo 500 g': {'7790070321800': (None, '2023-09'), '7790070336002': ('2023-10', None)},
    'Tirabuzón sin TACC Matarazzo 500 g': {'7790070321855': (None, '2023-09'), '7790070335982': ('2023-10', None)},
    'Fusilli maíz y arroz sin TACC Wakas': {'7798031470024': (None, '2024-07'), '7798031470796': ('2024-06', None)},
    'Fusilli quinoa sin TACC Wakas': {'7798031470031': (None, '2024-07'), '7798031470826': ('2024-06', None)},
    'Fusilli chía sin TACC Wakas': {'7798031470086': (None, '2024-07'), '7798031470819': ('2024-06', None)},
    'Fusilli amaranto sin TACC Wakas': {'7798031470048': (None, '2024-07'), '7798031470802': ('2024-06', None)},
    'Fusilli kale sin TACC Wakas': {'7798031470093': (None, '2024-07'), '7798031470833': ('2024-06', None)},
}
VIGENCIA = {e: v for d in EMPALMES.values() for e, v in d.items()}

def en_vigencia(e, mes):
    d, h = VIGENCIA.get(e, (None, None))
    return (d is None or mes >= d) and (h is None or mes <= h)
c['marca_n'] = c['marca'].map(lambda s: re.sub(r'[^A-Z0-9 ]', '', norm(s).upper()).strip())
_b = c.groupby('marca_n')['sin_tacc'].agg(['mean', 'size'])
MARCAS_CELIACAS = set(_b[(_b['mean'] >= 0.5) & (_b['size'] >= 2)].index) - {''}
c['es_gf'] = c['sin_tacc'] | (c['marca_n'].isin(MARCAS_CELIACAS) & ~c['con_gluten_explicito'])
c['ref_trigo'] = ~c['es_gf'] & ~c['ingrediente_sin_gluten']
c['grupo'] = ''
c['codigos'] = c['id']
filas = []
for gname, ids in EMPALMES.items():
    sub = c[c['id'].isin(ids)]
    if sub.empty:
        print(f'AVISO empalme sin códigos en la tabla: {gname}'); continue
    _m = SER.reindex([i for i in ids if i in SER.index])
    _m = _m.apply(lambda r: r.where([en_vigencia(r.name, m) for m in _m.columns]), axis=1)
    serie = _m.sum(axis=0, min_count=1)
    best = sub.sort_values('suc_mes_mediana', ascending=False).iloc[0].copy()
    v = serie.reindex(OFI)
    a22 = serie[[m for m in serie.index if m.startswith('2022')]].mean()
    a26 = serie[[m for m in OFI if m.startswith('2026')]].mean()
    best['id'] = 'EMP:' + gname
    best['descripcion'] = gname
    best['grupo'] = gname
    best['codigos'] = ','.join(ids)
    best['meses_2022_2026_07'] = int(v.notna().sum())
    best['meses_tolerados'] = int(v.reindex(sorted(MESES_TOLERADOS_EMPALME)).isna().sum())
    best['presente_ago_oct_2026'] = bool(serie.reindex([m for m in SER.columns if m >= '2026-08']).notna().all())
    best['suc_mes_mediana'] = float(v.median())
    best['cob_2022_sobre_2026'] = float(a22 / a26) if a26 > 0 else np.nan
    for k in ('provincias', 'comercios_super', 'cadenas_grandes'):
        best[k] = sub[k].max()
    best['pct_cadena_principal'] = sub['pct_cadena_principal'].min()
    best['sin_tacc'] = bool(sub['sin_tacc'].any())
    best['es_gf'] = bool(sub['es_gf'].any())
    best['ref_trigo'] = bool(sub['ref_trigo'].all())
    best['ingrediente_sin_gluten'] = bool(sub['ingrediente_sin_gluten'].all())
    best['_serie'] = serie
    filas.append(best)
emp = pd.DataFrame(filas)
MIEMBROS = c[c['id'].isin(VIGENCIA)].copy()          # filas de cada código (descripción, presentación) para s10
MIEMBROS.to_parquet(F_OUT.with_name(F_OUT.stem + '_miembros.parquet'), index=False)
import json
F_OUT.with_name(F_OUT.stem + '_vigencia.json').write_text(json.dumps(VIGENCIA, ensure_ascii=False, indent=1),
                                                          encoding='utf-8')
c = pd.concat([c[~c['id'].isin(VIGENCIA)], emp.drop(columns=['_serie'])], ignore_index=True)
c['meses_tolerados'] = c['meses_tolerados'].fillna(0).astype(int)
SER = pd.concat([SER, pd.DataFrame({r['id']: r['_serie'] for r in filas}).T])
c['caidas'] = [caidas(SER.loc[i]) if i in SER.index else 99 for i in c['id']]
inv = {s: t for t, ss in TIPOS_CANASTA.items() for s in ss}
c = c[c['tipo'].isin(inv)].copy()
c['tipo_nb06'] = c['tipo'].map(inv)
c['lado'] = np.where(c['es_gf'], 'sin_tacc', np.where(c['ref_trigo'], 'tacc', 'excluido'))
c['d'] = (c['descripcion'].fillna('') + ' ' + c['desc_sepa_22oct'].fillna('')).map(norm)
c['subtipo'] = [subtipo(t, d) for t, d in zip(c['tipo_nb06'], c['d'])]

def motivo(r):
    if r['lado'] == 'excluido':
        return 'naturalmente sin gluten sin etiqueta (no sirve de referencia con TACC)'
    if r['subtipo'] == '(fuera)':
        return 'subtipo no comparable'
    g = REGLAS[r['lado']]
    m = []
    if r['meses_2022_2026_07'] + r['meses_tolerados'] < MESES_OFICIALES:
        m.append(f"meses {int(r['meses_2022_2026_07'])}/55")
    if not r['presente_ago_oct_2026']: m.append('sin precio ago-oct 2026')
    if r['caidas'] > MAX_CAIDAS: m.append(f"{int(r['caidas'])} caídas")
    if not (RATIO_22_26[0] <= r['cob_2022_sobre_2026'] <= RATIO_22_26[1]): m.append(f"2022/2026 {r['cob_2022_sobre_2026']:.2f}")
    if r['suc_mes_mediana'] < g['suc']: m.append(f"suc {r['suc_mes_mediana']:.0f}")
    if r['provincias'] < g['prov']: m.append(f"prov {int(r['provincias'])}")
    if r['comercios_super'] < g['com']: m.append(f"comercios {int(r['comercios_super'])}")
    if r['cadenas_grandes'] < g['grandes']: m.append(f"grandes {int(r['cadenas_grandes'])}")
    if r['pct_cadena_principal'] > g['principal']: m.append(f"principal {r['pct_cadena_principal']:.0f}%")
    return '; '.join(m)

c['motivo'] = c.apply(motivo, axis=1)
# Sabores de una línea que ya pasa: un con TACC al que solo le falta UN comercio súper entra si otro producto de la
# misma marca, presentación y subtipo pasa todas las reglas (es el mismo producto en otro sabor y en las mismas
# cadenas). Entran las Lasfor Chocolate Suizo y Crema de Frutilla 200 g (7 comercios), junto a Mousse Limón y Crema
# Avellanas (8): el lado con TACC de las almohaditas queda con los mismos cuatro sabores que los Snuks sin TACC.
_k = ['tipo_nb06', 'subtipo', 'lado', 'marca_n', 'presentacion']
_lineas = set(map(tuple, c.loc[c['motivo'].eq(''), _k].astype(str).to_numpy()))
_sabor = (c['lado'].eq('tacc') & c['motivo'].eq(f"comercios {REGLAS['tacc']['com'] - 1}")
          & [tuple(x) in _lineas for x in c[_k].astype(str).to_numpy()])
print(f'Sabores de una línea que pasa (les falta un comercio): {c.loc[_sabor, "descripcion"].tolist()}')
c.loc[_sabor, 'motivo'] = ''
c['pasa'] = c['motivo'].eq('')
cols = ['tipo_nb06', 'subtipo', 'lado', 'id', 'descripcion', 'presentacion', 'pasa', 'motivo', 'suc_mes_mediana',
        'caidas', 'cob_2022_sobre_2026', 'provincias', 'comercios_super', 'cadenas_grandes',
        'pct_cadena_principal', 'suc_22oct', 'precio_100g_22oct']
c.to_parquet(F_OUT, index=False)
SER.to_parquet(F_OUT.with_name(F_OUT.stem + '_serie.parquet'))
for t in TIPOS_CANASTA:
    x = c[(c['tipo_nb06'] == t) & ((c['pasa']) | ((c['lado'] == 'sin_tacc') & (c['suc_mes_mediana'] >= 50)))]
    print(f'\n######## {t}')
    for lado in ('sin_tacc', 'tacc'):
        y = x[x['lado'] == lado].sort_values(['subtipo', 'pasa', 'suc_mes_mediana'], ascending=[True, False, False])
        print(f'--- {lado}: pasan {int(y["pasa"].sum())}')
        print(y[cols[1:]].round(2).to_string(index=False))
print('\nResumen (pasan por tipo / subtipo / lado):')
print(c[c['pasa']].groupby(['tipo_nb06', 'subtipo', 'lado']).size().unstack('lado').fillna(0).astype(int).to_string())
print(f'\nMarcas celíacas (>= 50% de sus productos etiquetados sin TACC): {sorted(MARCAS_CELIACAS)}')
