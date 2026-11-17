# Marcas propias SIN TACC de las cadenas (variable "la cadena tiene línea propia sin TACC" de la CELDA 13, pares y
# regresión; docs/BRECHA_CELIACA.md §18). Sale de la trazabilidad del nb09 (todos los productos del SEPA 2022-2026 con su
# marca y la cadena que más lo vende):
#   1. sin TACC por la descripción (sin TACC, sin gluten, s/TACC, libre de gluten);
#   2. marca PROPIA de la cadena: el nombre de la cadena o de su bandera (Carrefour, Carrefour Classic, Carrefour Extra,
#      Carrefour Sin Gluten, Día, La Anónima, Cooperativa, Coto, Jumbo...) o una marca propia conocida del grupo (Taeq, del
#      Grupo Éxito, dueño de Libertad; Great Value, de Walmart/ChangoMas; Cuisine & Co, de Cencosud). Las marcas que
#      vende una sola cadena pero son de un tercero (Dicomere, Angiola, Delician en Carrefour; Kapac, Grandiet en
#      Cencosud) NO son marca propia. "Primer Precio" queda afuera: se vende en Toledo y en la Cooperativa Obrera y sus
#      códigos no son de ninguna de las dos;
#   3. del tipo de alguna canasta (fideos, galletitas, pan rallado y rebozador, pan envasado, premezclas, alfajores,
#      tapas): el tipo y el subtipo salen de la descripción (reglas de abajo). Lo que no es de ningún tipo (cereales,
#      barras, aceites, tés, aguas) queda afuera.
# Gramos: de la descripción (Gr / Kg) o, si no está, del maestro_sepa_completo; las tapas por unidades quedan sin gramos
# (cuentan para la variable de presencia, no para los pares de precios).
# Uso: python -I -X utf8 s21_marcas_propias.py <trazabilidad_productos_*.parquet> <maestro_sepa_completo.csv.gz> <salida.csv>
import re, sys
import pandas as pd

TRAZ, MAESTRO, OUT = sys.argv[1:4]

SIN_TACC = r'sin tacc|sin gluten|s/ ?tacc|libre de gluten|sin t\.a\.c\.c'
# marca propia: (regex sobre la marca, empresa dueña con el nombre de la CELDA 3 del nb06, criterio)
MARCAS = [
    (r'^carrefour', 'Carrefour', 'nombre de la cadena'),
    (r'^d[ií]a$', 'DIA', 'nombre de la cadena'),
    (r'^coto$', 'Coto', 'nombre de la cadena'),
    (r'^(jumbo|vea|disco)$', 'Cencosud (Vea, Disco, Jumbo)', 'nombre de la bandera'),
    (r'^cuisine', 'Cencosud (Vea, Disco, Jumbo)', 'marca propia del grupo (Cencosud)'),
    (r'^la an[oó]nima$', 'La Anónima', 'nombre de la cadena'),
    (r'^cooperativa$', 'Cooperativa Obrera', 'nombre de la cadena'),
    (r'^great value$', 'ChangoMas', 'marca propia del grupo (Walmart)'),
    (r'^taeq$', 'Libertad', 'marca propia del grupo (Grupo Éxito, dueño de Libertad)'),
    (r'^libertad$', 'Libertad', 'nombre de la cadena'),
]
# tipo y subtipo por la descripción (en orden: gana la primera regla que pega). Subtipo None = el tipo no tiene ese
# subtipo en ninguna canasta (cuenta para la variable a nivel tipo, no para la del subtipo ni para los pares).
REGLAS = [
    (r'polvorones con chips|con chips', 'Galletitas dulces', 'Con chips', 'equivalente'),
    (r'polvoron', 'Galletitas dulces', 'Secas (vainilla, limón, chocolate)', 'equivalente'),
    (r'tostad', 'Galletitas saladas y crackers', 'Crackers', 'sustituto (tostadas contra crackers)'),
    (r'alfajor', 'Alfajores', None, 'equivalente'),                       # el subtipo, por los gramos (abajo)
    (r'rebozador', 'Pan rallado y rebozador', 'Rebozador', 'equivalente'),
    (r'pan rallado', 'Pan rallado y rebozador', 'Pan rallado', 'equivalente'),
    (r'pan (de )?hamburguesa|pan para hamburguesa|pan de pancho|pan para pancho', 'Pan envasado',
     'Pan para hamburguesas y panchos', 'equivalente'),
    (r'pan (de )?(mesa|campo|molde)', 'Pan envasado', 'Pan de molde y de mesa', 'equivalente'),
    (r'tapa.*empanada', 'Tapas', 'Tapas para empanadas', 'equivalente'),
    (r'tapa.*(pascualina|tarta)', 'Tapas', 'Tapas para tartas', 'equivalente'),
    (r'bizcochuelo', 'Premezclas', 'Premezcla para bizcochuelo y tortas', 'equivalente'),
    (r'brownie', 'Premezclas', 'Premezcla para brownie', 'equivalente'),
    (r'premezcla', 'Premezclas', None, 'equivalente'),
    (r'pasta seca|fideo|spagh|tirabuz|penne|mostachol', 'Fideos secos', None, 'sustituto (pasta de legumbres)'),
]
_RE_G = re.compile(r'(\d+(?:[.,]\d+)?)\s*(kg|gr|g)\b', re.IGNORECASE)

def gramos_desc(d):
    m = _RE_G.search(str(d))
    if not m:
        return None
    v = float(m.group(1).replace(',', '.'))
    return v * 1000 if m.group(2).lower() == 'kg' else v

t = pd.read_parquet(TRAZ, columns=['id_producto', 'descripcion', 'marca', 'categoria', 'es_ean', 'meses_con_precio',
                                   'sucursales_distintas', 'cadena_principal', 'pct_cadena_principal', 'primer_dia',
                                   'ultimo_dia'])
t = t[t['es_ean'] & t['descripcion'].str.contains(SIN_TACC, case=False, regex=True, na=False)].copy()
filas = []
for r in t.itertuples(index=False):
    marca = str(r.marca).strip()
    dueno = next(((e, c) for p, e, c in MARCAS if re.search(p, marca, re.IGNORECASE)), None)
    if dueno is None:
        continue
    d = str(r.descripcion).lower()
    regla = next(((tp, st, eq) for p, tp, st, eq in REGLAS if re.search(p, d)), None)
    if regla is None:
        continue
    tp, st, eq = regla
    filas.append({'ean': str(r.id_producto).lstrip('0'), 'descripcion': r.descripcion, 'marca': marca,
                  'empresa_duena': dueno[0], 'criterio_marca_propia': dueno[1], 'tipo': tp, 'subtipo': st,
                  'equivalencia': eq, 'gramos': gramos_desc(r.descripcion), 'categoria_sepa': r.categoria,
                  'cadena_principal': r.cadena_principal, 'pct_cadena_principal': r.pct_cadena_principal,
                  'sucursales_distintas': r.sucursales_distintas, 'meses_con_precio': r.meses_con_precio,
                  'primer_dia': str(r.primer_dia)[:10], 'ultimo_dia': str(r.ultimo_dia)[:10]})
out = pd.DataFrame(filas)
# gramos que faltan: el maestro_sepa_completo (cantidad y unidad de la presentación)
m = pd.read_csv(MAESTRO, dtype=str)
m['ean'] = m['producto_sepa_id'].str.lstrip('0')
m['_g'] = pd.to_numeric(m['producto_cantidad_presentacion'], errors='coerce') * m[
    'producto_unidad_medida_presentac'].str.lower().map({'gr': 1, 'g': 1, 'kg': 1000})
mg = m.dropna(subset=['_g']).drop_duplicates('ean').set_index('ean')['_g']
falta = out['gramos'].isna()
out.loc[falta, 'gramos'] = out.loc[falta, 'ean'].map(mg)
out['fuente_gramos'] = ['descripción' if not f else ('maestro' if g == g else '') for f, g in zip(falta, out['gramos'])]
# alfajores: individual hasta 90 g, caja o paquete arriba (la regla del s18)
_alf = out['tipo'].eq('Alfajores')
out.loc[_alf, 'subtipo'] = ['Alfajores en caja o paquete' if (g == g and g > 90) else 'Alfajor individual'
                            for g in out.loc[_alf, 'gramos']]
# la marca propia es de UNA cadena: avisar si la más vendedora no es la dueña
out = out.sort_values(['empresa_duena', 'tipo', 'subtipo', 'descripcion'], na_position='last').reset_index(drop=True)
out.to_csv(OUT, index=False, encoding='utf-8')
pd.set_option('display.width', 220); pd.set_option('display.max_colwidth', 70)
print(f'{len(out)} productos de marca propia sin TACC en los tipos de las canastas -> {OUT}')
print(out[['ean', 'descripcion', 'empresa_duena', 'tipo', 'subtipo', 'gramos', 'pct_cadena_principal',
           'primer_dia', 'ultimo_dia']].to_string(index=False))
print('\nPor empresa y tipo:')
print(out.groupby(['empresa_duena', 'tipo']).size().to_string())
