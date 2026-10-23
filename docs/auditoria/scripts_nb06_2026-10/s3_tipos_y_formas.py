# Reclasifica el catálogo (s2_clasificar_catalogo.py) con reglas más estrictas y arma PARES con TACC / sin TACC del mismo
# fabricante (prefijo GS1), mismo tipo (y misma forma en fideos) y tamaño parecido.
# Uso: python -I -X utf8 s3_tipos_y_formas.py <salida .parquet de s2_clasificar_catalogo.py> <salida.xlsx>
import re, sys
from pathlib import Path
import numpy as np
import pandas as pd

F_IN, F_OUT = Path(sys.argv[1]), Path(sys.argv[2])
pd.set_option('display.width', 250)
p = pd.read_parquet(F_IN)

# ── Tipos con dicotomía (orden = prioridad). (incluir, excluir) sobre la descripción sin tildes ───────────────────────
NO_ALIM = r'esencia|extracto|liquida|aroma|condiment|especia|oregano|yogur|yog\b|flan|postre|helado|leche\b|bebida|' \
          r'yerba|\bmate\b|\bte\b|cafe|jugo|gaseosa|agua mineral|shampoo|jabon|crema de|dulce de leche|mermelad'
TIPOS = [
    ('Fideos secos', r'\bfid(?:eo|eos|\.)|spag|tallar|mostach|tirabu|\bpenne|fusil|codit|\bcintas?\b|caracol|rigat|'
                     r'\bletras?\b|\bmon(?:o|it)|farfall|dedali|cornet|risoni|\bnidos?\b|vermicel|cabello de angel|'
                     r'macarr|lasa[gn]|tornill|\bconchit|ave maria|ditalin|orzo|fetuc|\bmost\.|fid\.largos',
                     r'noqui|ravio|sorren|canelon|salsa|sopa|caldo|congel|fresc|rellen|\btapa|instant|vasito|\bcup\b|'
                     r'galleti|cereal|snack'),
    ('Galletitas dulces', r'galleti|galleta|\bgall\b|oblea|bizcoch(?!u)|\bscon|\bpepas?\b|wafer|cookie|marmolad|'
                          r'cuadradit|masitas?\b|polvoron|\bmerengu|amaretti|biscotti|rellenas?\b.*(?:vainill|chocol|'
                          r'frutill|limon)|\boreo\b',
                          r'salad|cracker|queso|jamon|\bs/sal|sin sal|\bs sal\b|arroz|tostad|pizza|semilla|integral|'
                          r'salvado|agua\b|soda|crackers|chia|multicereal|grisin|' + NO_ALIM),
    ('Galletitas saladas, crackers y tostadas', r'cracker|tostad|tortit|grisin|criollit|bizcochit|chalita|talita|'
                                                r'(?:galleti|galleta|\bgall\b).*(?:salad|queso|jamon|pizza|arroz|'
                                                r'semilla|integral|salvado|s/sal|sin sal|\bs sal\b|agua|soda|chia|'
                                                r'multicereal|cereal)|\bmarineras?\b|\bsoda\b.*galle',
                                                r'dulce|chocolat|vainill|limon|coco|frutill|membrill|' + NO_ALIM),
    ('Pan rallado y rebozador', r'pan rallado|\brallad|rebozad|apanad|empaniz', r'queso|coco|zanahoria|rallador|'
                                                                             r'limon|' + NO_ALIM),
    ('Premezclas y harinas', r'premez|\bprem\b|harina|fecula|almidon|bizcochue.*(?:prem|polvo)|p/bizcochuel|'
                             r'p/torta|para torta|p/budin|para budin|p/pizza|para pizza|p/panificad|chipa.*prem',
                             r'pescado|rebozad|rallad|galleti|tapa|' + NO_ALIM),
    ('Budines, bizcochuelos y tortas', r'budin|bizcochue|muffin|magdalen|madalen|brownie|\btortas?\b|pan dulce|'
                                       r'panetton|\bcake|cupcake|\bvainillas\b|plantilla|pionono|alfajorcito|'
                                       r'\bbizc\b', r'galleti|tortita|tortill|prem|' + NO_ALIM),
    ('Alfajores', r'alfajor', NO_ALIM),
    ('Pan envasado', r'\bpan\b|\bpanes\b|lactal|\bmolde\b|pebete|figaz|chipa|baguet|\bbollos?\b|fosforit|pancho|'
                     r'\bmignon|felipe|criollo|tostadas? de pan', r'rallad|rebozad|premez|\bprem\b|dulce|budin|'
                     r'pan de carne|hamburguesa de|' + NO_ALIM),
    ('Tapas, masas y pizzas', r'prepiz|\bpizzas?\b|\btapas?\b|pascualin|empanad|hojaldr|\bmasas?\b|tarta|\bwrap|'
                              r'tortill|pan arabe|rapidit|fugazz|discos? de', r'galleti|snack|chizit|palito|conit|'
                              r'rueditas|sabor|premez|\bprem\b|salsa|' + NO_ALIM),
    ('Cereales, copos y barras', r'cereal|\bcopos?\b|granola|avena|muesli|\bbarras?\b|barrit|aritos|anillit|'
                                 r'almohadit|trigo inflado|arroz inflado|corn ?flakes|zucaritas|krispis',
                                 r'galleti|chocolate en barra|barra de chocolate|jabon|desodor|' + NO_ALIM),
    ('Cerveza', r'cervez|\bcerv\b|\bbeer\b|\bipa\b|\blager\b|michelob', r'levadura|' + NO_ALIM),
    ('Pastas frescas y ñoquis', r'noqui|ravio|sorren|canelon|capelet|agnolot|tortelin|panzott', r'salsa|' + NO_ALIM),
    ('Snacks', r'palito|chizit|\bsnacks?\b|papas? fritas|nacho|conit|\bchips\b|bastoncit', r'chocolate|' + NO_ALIM),
]
_T = [(t, re.compile(i), re.compile(e) if e else None) for t, i, e in TIPOS]
def tipo_de(d):
    for t, i, e in _T:
        if i.search(d) and not (e and e.search(d)):
            return t
    return None
p['tipo'] = p['d'].map(tipo_de)

# Forma de los fideos (la equivalencia fina que sí alinea entre los dos lados)
FORMAS = [('Spaghetti', r'spag|cabello|vermicel|fid\.largos|fideos? largos|fino'),
          ('Tallarín/cintas', r'tallar|fetuc|cintas?|nidos?'),
          ('Mostachol/penne', r'mostach|\bmost\.|penne|rigat|pluma'),
          ('Tirabuzón/fusilli', r'tirabu|fusil|tornill|caracol|spiral'),
          ('Corto (codito, moñito...)', r'codit|dedal|mon(?:o|it)|farfall|risoni|cornet|letras|conchit|ditalin|'
                                        r'ave maria|orzo')]
_F = [(f, re.compile(r)) for f, r in FORMAS]
def forma(d):
    for f, r in _F:
        if r.search(d): return f
    return 'Otra'
p['forma'] = np.where(p['tipo'] == 'Fideos secos', p['d'].map(forma), '')
p['fabricante'] = p['id_producto'].str[:7]
p['lado'] = np.where(p['sin_tacc'], 'sin TACC', 'con TACC')

# ── Resumen por tipo ────────────────────────────────────────────────────────────────────────────────────────────────
q = p.dropna(subset=['tipo'])
def _res(g):
    s, c = g[g['sin_tacc']], g[~g['sin_tacc']]
    return pd.Series({'con_TACC': len(c), 'con_TACC_1000suc': int((c['sucursales'] >= 1000).sum()),
                      'sin_TACC': len(s), 'sin_100suc': int((s['sucursales'] >= 100).sum()),
                      'sin_500suc': int((s['sucursales'] >= 500).sum()),
                      'sin_1000suc': int((s['sucursales'] >= 1000).sum()),
                      'sin_max_suc': int(s['sucursales'].max()) if len(s) else 0,
                      'sin_max_cadenas': int(s['cadenas'].max()) if len(s) else 0})
res = q.groupby('tipo')[list(q.columns)].apply(_res).sort_values('sin_max_suc', ascending=False)
print(f'Sucursales en el día: ~2.954 | productos clasificados: {len(q):,} (sin TACC {q["sin_tacc"].sum():,})')
print(res.to_string())

# ── Pares: mismo fabricante + tipo (+ forma), tamaño parecido ───────────────────────────────────────────────────────
S = q[q['sin_tacc'] & (q['sucursales'] >= 50)]
C = q[~q['sin_tacc'] & (q['sucursales'] >= 50)]
pares = []
for r in S.itertuples(index=False):
    cand = C[(C['tipo'] == r.tipo) & (C['fabricante'] == r.fabricante)]
    if r.tipo == 'Fideos secos':
        cand = cand[cand['forma'] == r.forma]
    if pd.notna(r.gramos):
        cand = cand[cand['gramos'].isna() | ((cand['gramos'] / r.gramos).between(0.5, 2.0))]
    if len(cand) == 0:
        continue
    b = cand.sort_values('sucursales', ascending=False).iloc[0]
    pares.append({'tipo': r.tipo, 'forma': r.forma, 'fabricante': r.fabricante,
                  'sin_id': r.id_producto, 'sin_desc': r.descripcion, 'sin_marca': r.marca, 'sin_g': r.gramos,
                  'sin_suc': r.sucursales, 'sin_cad': r.cadenas, 'sin_prov': r.provincias, 'sin_100g': r.precio_100g,
                  'con_id': b['id_producto'], 'con_desc': b['descripcion'], 'con_marca': b['marca'],
                  'con_g': b['gramos'], 'con_suc': b['sucursales'], 'con_cad': b['cadenas'],
                  'con_100g': b['precio_100g'], 'n_alternativas_con': len(cand)})
pares = pd.DataFrame(pares)
pares['brecha_%'] = (pares['sin_100g'] / pares['con_100g'] - 1) * 100
pares['suc_min'] = pares[['sin_suc', 'con_suc']].min(axis=1)
pares = pares.sort_values(['tipo', 'suc_min'], ascending=[True, False])
print(f'\n=== Pares del mismo fabricante (sin TACC con >= 50 sucursales): {len(pares)} ===')
for t, g in pares.groupby('tipo', sort=False):
    print(f'\n## {t}')
    print(g[['forma', 'sin_desc', 'sin_g', 'sin_suc', 'sin_cad', 'con_desc', 'con_g', 'con_suc', 'sin_100g',
             'con_100g', 'brecha_%']].head(12).round(0).to_string(index=False, max_colwidth=42))

# ── sin TACC más cubiertos por tipo (con y sin par) ─────────────────────────────────────────────────────────────────
print('\n=== sin TACC con más cobertura por tipo (top 8) ===')
for t, g in S.groupby('tipo'):
    g = g.nlargest(8, 'sucursales')
    g = g.assign(con_par=g['id_producto'].isin(set(pares['sin_id'])))
    print(f'\n## {t}')
    print(g[['id_producto', 'descripcion', 'marca', 'gramos', 'sucursales', 'cadenas', 'provincias', 'precio_100g',
             'con_par']].round(0).to_string(index=False, max_colwidth=46))

# sin TACC sin tipo (para revisar qué se queda afuera)
print('\n=== sin TACC fuera de los tipos (top 25 por sucursales) ===')
print(p[p['sin_tacc'] & p['tipo'].isna()].nlargest(25, 'sucursales')[['descripcion', 'marca', 'sucursales',
      'categoria']].to_string(index=False, max_colwidth=50))

with pd.ExcelWriter(F_OUT, engine='openpyxl') as w:
    res.reset_index().to_excel(w, sheet_name='Resumen_tipos', index=False)
    pares.to_excel(w, sheet_name='Pares_mismo_fabricante', index=False)
    q.drop(columns=['d']).sort_values(['tipo', 'lado', 'sucursales'], ascending=[True, False, False]) \
        .to_excel(w, sheet_name='Productos_por_tipo', index=False)
p.to_parquet(F_OUT.with_suffix('.parquet'), index=False)
print(f'\nGuardado: {F_OUT}')
