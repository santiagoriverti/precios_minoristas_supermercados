# Tabla de candidatos para las canastas con TACC / sin TACC con continuidad 2022-2026 (salidas del nb09).
# Uso: python -I -X utf8 s7_continuidad.py <ranking nb09 .parquet> <panel mensual nb09 .parquet>
#                                        <catálogo clasificado del 22/10 (.parquet de s3_tipos_y_formas.py)> <salida.parquet>
import re, sys, unicodedata
from pathlib import Path
import numpy as np
import pandas as pd

F_RANK, F_PANEL, F_CAT, F_OUT = (Path(a) for a in sys.argv[1:5])
norm_id = lambda s: s.astype(str).str.strip().str.lstrip('0')

def sin_tildes(s):
    return s.fillna('').astype(str).str.lower().str.normalize('NFKD').str.encode('ascii', 'ignore').str.decode('ascii')

RE_SIN = re.compile(
    r'(?:\bsin|\bs)[\s/.\-]*t\.?\s*a\.?\s*c\.?\s*c\b|\bsin[\s/.\-]*glut|\bs[\s/.\-]+glut'
    r'|\blib(?:re|r)?\.?[\s/.\-]*(?:de|d)?[\s/.\-]*(?:bio\s+de\s+)?glut|\bl\.\s*glut|gluten[\s\-]*free|\bcel[ií]ac'
    r'|\bglutal\b|\bapto\s+cel', re.IGNORECASE)
RE_CON = re.compile(r'\bc/\s*glut|\bcon\s+glut|galletit\w*\s+(?:de\s+)?gluten|\bgluten\s+(?:c/|s/)sal|light\s+gluten|'
                    r'gluten\s+light', re.IGNORECASE)
# ingredientes naturalmente sin gluten (un producto con TACC de referencia NO puede tenerlos como base)
RE_ING_SG = re.compile(r'arroz|maiz|quinoa|quinua|garbanz|lentej|legumbr|mandioc|\bchia\b|amarant|sarracen|\byuca\b|'
                       r'almendr|\bmijo|sorgo|arvej|poroto|soja|tapioca|fecula|almidon|\bchipa|pan de queso|\bketo\b|'
                       r'proteic|harina de coco|harina de mani')

# ── Tipo por categoría / subcategoría del Maestro (+ reglas de descripción para separar dentro) ─────────────────────
def tipo_de(cat, sub, d):
    if cat == 'Pastas Secas' and sub == 'Pastas Secas':
        if re.search(r'instant|vasito|\bcup\b|sopa|salsa|preparad|lasagn|lasan|canelon|noqui', d):
            return None
        return 'Fideos secos'
    if cat == 'Galletitas' and sub == 'Galletitas Dulces':
        return 'Galletitas dulces'
    if (cat == 'Galletitas' and sub in ('Galletitas Saladas', 'Galletitas sin Sal')) or \
       (cat == 'Panificados' and sub == 'Tostadas y grisines'):
        return 'Galletitas saladas y tostadas'
    if cat == 'Panificados' and sub == 'Pan Rallado y Rebozadores':
        if re.search(r'queso|coco\b|rallador', d):
            return None
        return 'Pan rallado y rebozador'
    if cat == 'Panificados' and sub in ('Pan de Molde', 'Pan de Hamburguesas y Panchos', 'Pan Tradicional'):
        return 'Pan envasado'
    if cat == 'Panificados' and sub in ('Budines y Otros', 'Madalenas', 'Tortas y Tartas'):
        return 'Budines y madalenas'
    if cat == 'Repostería y Postres' and sub == 'Para preparar':
        if re.search(r'bizcoch|brownie|budin|torta|muffin|cupcake|magdalen|scon|cookie|panqueque|waffle|chipa|'
                     r'pizza|pan\b|premez', d) and not re.search(r'gelatin|flan|postre|mousse|helado|crema|'
                                                                  r'chantilly|merengue', d):
            return 'Premezclas'
        return None
    if cat == 'Harinas' and sub in ('Harina de Trigo', 'Harinas Especiales', 'Harinas'):
        return 'Harinas y premezclas universales'
    if cat == 'Golosinas' and sub == 'Alfajores':
        return 'Alfajores'
    if cat == 'Cereales' and sub == 'Cereales':
        return 'Cereales y barras'
    if cat == 'Pastas y Tapas' and sub == 'Tapas':
        return 'Tapas'
    if cat == 'Panificados' and sub == 'Prepizzas':
        return 'Prepizzas'
    if cat == 'Cerveza':
        return 'Cerveza'
    return None

R = pd.read_parquet(F_RANK)
R['id'] = norm_id(R['id_producto'])
R = R[R['es_ean'] & ~R['blacklist'].fillna(False).astype(bool) & ~R['precio_simbolico'].fillna(False).astype(bool)]
R['d'] = sin_tildes(R['descripcion'])
R['tipo'] = [tipo_de(c, s, d) for c, s, d in zip(R['categoria'], R['subcategoria'], R['d'])]
R = R[R['tipo'].notna()].copy()

# Catálogo del 22/10/2026 (descripciones del SEPA de cada cadena): marca sin TACC y cobertura de ese día
cat = pd.read_parquet(F_CAT)
cat['id'] = norm_id(cat['id_producto'])
cat = cat.drop_duplicates('id').set_index('id')
R['gf_maestro'] = R['d'].str.contains(RE_SIN) & ~R['d'].str.contains(RE_CON)
R['gf_sepa_oct26'] = R['id'].map(cat['sin_tacc']).astype('boolean').fillna(False).astype(bool)
R['con_gluten_explicito'] = R['d'].str.contains(RE_CON) | R['id'].map(cat['con_explicito']).astype('boolean').fillna(False).astype(bool)
R['en_sepa_22oct'] = R['id'].isin(cat.index)
R['desc_sepa_22oct'] = R['id'].map(cat['descripcion'])
R['suc_22oct'] = R['id'].map(cat['sucursales'])
R['cadenas_22oct'] = R['id'].map(cat['cadenas'])
R['cadenas_detalle_22oct'] = R['id'].map(cat['cadenas_detalle'])
R['precio_100g_22oct'] = R['id'].map(cat['precio_100g'])
R['gramos_22oct'] = R['id'].map(cat['gramos'])
R['sin_tacc'] = R['gf_maestro'] | R['gf_sepa_oct26']
R['ingrediente_sin_gluten'] = R['d'].str.contains(RE_ING_SG) | sin_tildes(R['desc_sepa_22oct']).str.contains(RE_ING_SG)

# ── Continuidad mensual (panel del nb09) ────────────────────────────────────────────────────────────────────────────
P = pd.read_parquet(F_PANEL)
P['id'] = norm_id(P['id_producto'])
P = P[P['id'].isin(set(R['id']))]
MESES = sorted(pd.read_parquet(F_PANEL, columns=['mes'])['mes'].unique())
M = P.pivot_table(index='id', columns='mes', values='suc_diarias_prom', aggfunc='first').reindex(columns=MESES)
OFI = [m for m in MESES if m <= '2026-07']       # semestrales oficiales; ago-oct 2026 = SEPA diario sin 8 comercios
FIN = [m for m in MESES if m >= '2026-08']
m_ofi = M[OFI]
met = pd.DataFrame(index=M.index)
met['meses_con_dato'] = M.notna().sum(axis=1)
met['meses_2022_2026_07'] = m_ofi.notna().sum(axis=1)
met['todos_los_meses_2022_2026_07'] = met['meses_2022_2026_07'].eq(len(OFI))
met['presente_ago_oct_2026'] = M[FIN].notna().all(axis=1)
met['primer_mes'] = M.apply(lambda r: r.first_valid_index(), axis=1)
met['ultimo_mes'] = M.apply(lambda r: r.last_valid_index(), axis=1)
med = m_ofi.median(axis=1)
met['suc_mes_mediana'] = med.round(1)
met['suc_mes_min'] = m_ofi.min(axis=1).round(1)
met['mes_min'] = m_ofi.apply(lambda r: r.idxmin() if r.notna().any() else None, axis=1)
met['min_sobre_mediana'] = (m_ofi.min(axis=1) / med).round(3)
# segundo mínimo: el SEPA tiene meses con la mitad de los comercios (16-28/07/2023); un solo mes bajo no descalifica
met['min2_sobre_mediana'] = (m_ofi.apply(lambda r: r.dropna().nsmallest(2).iloc[-1] if r.notna().sum() >= 2 else np.nan,
                                         axis=1) / med).round(3)
met['meses_bajo_35pct'] = m_ofi.lt(0.35 * med, axis=0).sum(axis=1)
a22 = M[[m for m in MESES if m.startswith('2022')]].mean(axis=1)
a26 = M[[m for m in OFI if m.startswith('2026')]].mean(axis=1)
met['cob_2022'] = a22.round(1)
met['cob_2026'] = a26.round(1)
met['cob_2022_sobre_2026'] = (a22 / a26).round(3)
R = R.join(met, on='id')

# ── Geografía y cadenas (ranking del nb09, todo el período) ──────────────────────────────────────────────────────────
GRANDES = ['DIA', 'Carrefour', 'Cencosud (Vea/Disco/Jumbo)', 'La Anónima', 'Cooperativa Obrera', 'Coto', 'ChangoMas',
           'Toledo']
NO_SUPER = {'Cadena 19', 'Cadena 2013', 'Cadena 3001', 'Estación Lima', 'Axion Energy', 'Cadena 24'}
lst = R['cadenas'].fillna('').str.split(';').map(lambda l: [x.strip() for x in l if x.strip()])
R['cadenas_grandes'] = lst.map(lambda l: sum(g in l for g in GRANDES))
R['cadenas_grandes_lista'] = lst.map(lambda l: ', '.join(g for g in GRANDES if g in l))
R['comercios_super'] = lst.map(lambda l: sum(x not in NO_SUPER for x in l))
R['n_regiones'] = R['regiones']

cols = ['tipo', 'sin_tacc', 'gf_maestro', 'gf_sepa_oct26', 'con_gluten_explicito', 'ingrediente_sin_gluten', 'id',
        'descripcion', 'marca', 'presentacion', 'categoria', 'subcategoria', 'desc_sepa_22oct', 'primer_mes', 'ultimo_mes',
        'meses_con_dato', 'meses_2022_2026_07', 'todos_los_meses_2022_2026_07', 'presente_ago_oct_2026',
        'suc_mes_mediana', 'suc_mes_min', 'mes_min', 'min_sobre_mediana', 'min2_sobre_mediana', 'meses_bajo_35pct',
        'cob_2022', 'cob_2026', 'cob_2022_sobre_2026', 'suc_diarias_prom', 'provincias', 'pct_prov_diaria_prom',
        'n_regiones', 'en_amba', 'comercios', 'comercios_super', 'cadenas_grandes', 'cadenas_grandes_lista',
        'cadena_principal', 'pct_cadena_principal', 'hhi_cadenas', 'puntaje', 'ranking', 'en_sepa_22oct', 'suc_22oct',
        'cadenas_22oct', 'gramos_22oct', 'precio_100g_22oct', 'precio_mediano_ultimo_mes', 'cv_precio_ultimo_mes_%',
        'cadenas', 'cadenas_detalle_22oct']
out = R[cols].copy()
out.to_parquet(F_OUT, index=False)
M.to_parquet(F_OUT.with_name(F_OUT.stem + '_serie.parquet'))
print(f'Candidatos de los tipos: {len(out):,} | sin TACC: {out["sin_tacc"].sum():,} | con historia completa 2022-01 -> '
      f'2026-07: {out["todos_los_meses_2022_2026_07"].sum():,}')
print(out.groupby(['tipo', 'sin_tacc']).agg(productos=('id', 'size'),
      completos=('todos_los_meses_2022_2026_07', 'sum'),
      completos_y_vivos=('presente_ago_oct_2026', lambda s: int((s & out.loc[s.index, 'todos_los_meses_2022_2026_07']).sum())))
      .to_string())
