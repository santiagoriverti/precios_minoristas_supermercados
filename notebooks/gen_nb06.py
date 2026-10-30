"""Script to generate 06_evolucion_brecha_celiaca.ipynb — Brecha TACC vs sin-TACC con canasta FIJA 2022-2026.

Mide la brecha de precios entre productos con TACC y sus equivalentes sin TACC (dentro de cada supermercado, por tipo
de producto, en $/100 g) y cómo se distribuye en el tiempo (mensual desde enero de 2022), geográficamente (provincia,
región, AMBA) y entre cadenas.

Canasta FIJA (2026-10-23): para cada tipo con dicotomía celíaca, productos con TACC y sin TACC elegidos por
continuidad temporal 2022-2026, cobertura geográfica y por cadenas sobre las salidas del nb09. La lista vive en
docs/brecha_celiaca/canasta_fija_2022_2026.csv (con las métricas de cada producto) y este generador la embebe en la
CELDA 1. Reglas y fundamentos: docs/BRECHA_CELIACA.md §14.

Desde el 2026-10-27 escribe también 06b_brecha_celiaca_canasta_amplia.ipynb: las mismas celdas con la canasta AMPLIA de
la oferta actual (docs/brecha_celiaca/canasta_amplia_2025_2026.csv, ago-2025 -> hoy; BRECHA_CELIACA §16), al final.

Regenerar:  python notebooks/gen_nb06.py   (escribe los dos; commitear generador + .ipynb + CSV juntos)
"""
import csv, json, os, hashlib

def _cell_id(prefix, src):
    return prefix + hashlib.md5(src.encode('utf-8')).hexdigest()[:6]

def cell_md(src):
    lines = src.split('\n')
    source = [l + '\n' for l in lines[:-1]] + ([lines[-1]] if lines[-1] else [])
    return {'cell_type':'markdown','id':_cell_id('md', src),'metadata':{},'source':source}

def cell_code(src):
    return {'cell_type':'code','execution_count':None,'id':_cell_id('c', src),'metadata':{},'outputs':[],'source':[src]}

HERE = os.path.dirname(os.path.abspath(__file__))
CANASTA_CSV = os.path.join(HERE, '..', 'docs', 'brecha_celiaca', 'canasta_fija_2022_2026.csv')
# productos que cumplen todas las reglas de la selección (los de la canasta y los que quedan afuera), para la CELDA 8c
SENS_CSV = os.path.join(HERE, '..', 'docs', 'brecha_celiaca', 'productos_sensibilidad.csv')

# Peso de cada tipo = % del gasto de los hogares en alimentos y bebidas no alcohólicas (división A01) que va a sus
# artículos en la ENGHo 2017/18 (INDEC, microdatos de gastos, monto x pondera; hogar promedio, no celíaco). Se
# renormaliza entre los tipos de la canasta.
PESOS_ENGHO = {
    'Fideos secos': (1.503, 'A0111304 Fideos secos'),
    'Galletitas dulces': (1.717, 'A0111105 Galletitas dulces envasadas + A0111108 Masas secas o finas'),
    'Galletitas saladas y crackers': (1.407, 'A0111103 Galletitas de agua envasadas + A0111102 Galletas, grisines '
                                             'y tostadas + A0111107 Galletitas de otro tipo'),
    'Pan rallado y rebozador': (0.194, 'A0111114 Pan rallado'),
    'Cereales rellenos (almohaditas)': (0.181, 'A0111207 Cereales inflados'),
}
ORDEN_TIPOS = list(PESOS_ENGHO)


def _bloque_canasta():
    # TIPOS y GRAMOS de la CELDA 1, desde el CSV de la canasta fija
    with open(CANASTA_CSV, encoding='utf-8') as f:
        filas = list(csv.DictReader(f))
    tipos = {r['tipo'] for r in filas}
    falta = tipos - set(ORDEN_TIPOS)
    if falta:
        raise ValueError(f'Tipos del CSV sin peso ENGHo: {falta}')
    out = ['TIPOS = {']
    for tipo in ORDEN_TIPOS:
        fs = [r for r in filas if r['tipo'] == tipo]
        if not fs:
            continue
        peso, art = PESOS_ENGHO[tipo]
        out.append(f'    {tipo!r}: {{')
        out.append(f"        'peso': {peso},   # % del gasto en alimentos (ENGHo 2017/18): {art}")
        for lado in ('tacc', 'sin_tacc'):
            out.append(f'        {lado!r}: {{')
            for r in fs:
                if r['lado'] != lado:
                    continue
                _lin = r.get('linea') or r['producto']
                nota = (f"  # {r['subtipo']}" + (f" · {r['nota']}" if r.get('nota') else '')
                        + (f" · línea «{_lin}»" if _lin != r['producto'] else ''))
                out.append(f"            {r['ean']!r}: {r['descripcion']!r},{nota}")
            out.append('        },')
        out.append('    },')
    out.append('}')
    out.append('')
    out.append('# Gramos de cada presentación, verificados contra el SEPA (descripciones de las cadenas en oct-2026) y el')
    out.append('# Maestro. NO se toman del maestro: hay EANs reutilizados con la descripción vieja.')
    out.append('GRAMOS = {')
    gs = [(r['ean'], r['gramos']) for t in ORDEN_TIPOS for r in filas if r['tipo'] == t]
    for i in range(0, len(gs), 5):
        out.append('    ' + ' '.join(f"{e!r}: {float(g):g}," for e, g in gs[i:i + 5]))
    out.append('}')
    out.append('')
    out.append('# Vigencia de los códigos de un producto que cambió de EAN (desde, hasta; None = sin límite). Los códigos viejos')
    out.append('# de Molinos que siguen apareciendo después del cambio (sep-oct 2023) traen precios CONGELADOS en ~100 sucursales')
    out.append('# (Mostacholes Lucchetti viejo a $246-337 en 2024-2025 contra $1.042-1.700 del nuevo): fuera de su vigencia no')
    out.append('# se usan (se filtran en la CELDA 7, NO cambian el caché).')
    out.append('VIGENCIA = {')
    for t in ORDEN_TIPOS:
        for r in filas:
            if r['tipo'] == t and (r.get('desde') or r.get('hasta')):
                d = repr(r['desde']) if r.get('desde') else 'None'
                h = repr(r['hasta']) if r.get('hasta') else 'None'
                out.append(f"    {r['ean']!r}: ({d}, {h}),   # {r['descripcion']}")
    out.append('}')
    out.append('')
    out.append('# Productos con más de un código: los empalmes (el fabricante cambió el EAN) y las líneas (sabores o variantes de')
    out.append('# una misma marca y presentación en el subtipo, al mismo precio; desde el 2026-10-26). En cada sucursal y mes el')
    out.append('# precio del producto es la mediana de sus códigos vigentes, así cuenta UNA vez en la mediana de su lado aunque')
    out.append('# la sucursal tenga varios de sus códigos.')
    out.append('PRODUCTO = {')
    _prod = {}
    for t in ORDEN_TIPOS:
        for r in filas:
            if r['tipo'] == t and (r.get('linea') or r.get('producto')):
                _prod.setdefault(r.get('linea') or r['producto'], []).append(r['ean'])
    for p, es in _prod.items():
        if len(es) > 1:
            out.append(f'    {p!r}: {es!r},')
    out.append('}')
    out.append('')
    out.append('# Subtipo de cada producto (comparabilidad: la selección elige tantos productos con TACC como sin TACC en cada')
    out.append('# subtipo). La brecha se calcula por subtipo y se agrega por tipo (CELDAS 7 y 8).')
    out.append('SUBTIPO = {')
    _sub = {}
    for t in ORDEN_TIPOS:
        for r in filas:
            if r['tipo'] == t and r.get('subtipo'):
                _sub.setdefault(r['subtipo'], []).append(r['ean'])
    for s, es in _sub.items():
        out.append(f'    {s!r}: [')
        for i in range(0, len(es), 6):
            out.append('        ' + ' '.join(f'{e!r},' for e in es[i:i + 6]))
        out.append('    ],')
    out.append('}')
    out.append('')
    out.append('# Productos con más de un código SIN juntar los sabores de una línea (solo los empalmes): escenario "cada sabor')
    out.append('# como un producto" de la hoja Sensibilidad (CELDA 8c).')
    out.append('PRODUCTO_SIN_LINEA = {')
    _pe = {}
    for t in ORDEN_TIPOS:
        for r in filas:
            if r['tipo'] == t:
                _pe.setdefault(r['producto'], []).append(r['ean'])
    for p, es in _pe.items():
        if len(es) > 1:
            out.append(f'    {p!r}: {es!r},')
    out.append('}')
    sens = []
    if os.path.exists(SENS_CSV):
        with open(SENS_CSV, encoding='utf-8') as f:
            sens = list(csv.DictReader(f))
    _lin_canasta = {r['ean']: (r.get('linea') or r['producto']) for r in filas}
    out.append('')
    out.append('# ADICIONALES (CELDA 8c, hoja Sensibilidad): cumplen todas las reglas de la selección pero quedan fuera de la')
    out.append('# canasta (composición espejada, comparador fijo de las obleas o sustitutos de un producto equivalente: las galletas')
    out.append('# de arroz de crackers). Se leen con la canasta (cambian la clave del caché) y entran SOLO en los escenarios de')
    out.append('# sensibilidad, nunca en la brecha principal. linea_todos = la línea que formarían junto con los de la canasta.')
    out.append('ADICIONALES = {')
    for r in sens:
        if r['en_canasta'] == 'False':
            _v = lambda x: repr(x) if x else 'None'
            out.append(f"    {r['ean']!r}: {{'tipo': {r['tipo']!r}, 'lado': {r['lado']!r}, 'subtipo': {r['subtipo']!r}, "
                       f"'gramos': {float(r['gramos']):g},")
            out.append(f"        'desde': {_v(r['desde'])}, 'hasta': {_v(r['hasta'])}, 'linea_todos': {r['linea_todos']!r},")
            out.append(f"        'motivo': {r['motivo']!r}, 'descripcion': {r['descripcion']!r}}},")
    out.append('}')
    out.append('# Línea de los productos de la canasta si entraran también los ADICIONALES (solo las que cambian; escenario')
    out.append('# "todos los productos que cumplen las reglas").')
    out.append('LINEA_TODOS = {')
    for r in sens:
        if r['en_canasta'] == 'True' and r['linea_todos'] != _lin_canasta.get(r['ean']):
            out.append(f"    {r['ean']!r}: {r['linea_todos']!r},")
    out.append('}')
    out.append('# Productos de la canasta que son SUSTITUTOS (galletas de arroz en saborizadas: no hay galletitas saborizadas sin TACC')
    out.append('# continuas): escenario "solo productos equivalentes".')
    _sus = [r['ean'] for r in sens if r['en_canasta'] == 'True' and r['sustituto'] == 'True']
    out.append('SUSTITUTOS = {' + ', '.join(repr(e) for e in _sus) + '}')
    out.append('')
    out.append('# Marca de cada código (de la canasta y de los ADICIONALES), normalizada como en la selección (s10, s18): la hoja')
    out.append('# Prima_misma_marca (CELDA 8c) compara el sin TACC y el con TACC de una MISMA marca en el mismo súper, para separar')
    out.append('# la prima sin gluten de la prima de marca (MARCA_EQUIVALENTE, abajo, une las líneas sin TACC con otro nombre).')
    out.append('MARCA = {')
    _mar = {}
    for r in filas + [s for s in sens if s.get('en_canasta') == 'False']:
        if r.get('marca'):
            _mar.setdefault(r['ean'], r['marca'])
    _it = list(_mar.items())
    for i in range(0, len(_it), 4):
        out.append('    ' + ' '.join(f'{e!r}: {m!r},' for e, m in _it[i:i + 4]))
    out.append('}')
    return '\n'.join(out)


cells = []

# ── CELL 0 ─────────────────────────────────────────────────────────────────────
cells.append(cell_md("""# SEPA — Brecha Celíaca (TACC vs sin-TACC), canasta fija 2022-2026

**Objetivo:** medir la **brecha** de precios entre productos **con TACC** y sus equivalentes **sin TACC**, y cómo se
distribuye **en el tiempo** (mensual, desde enero de 2022), **geográficamente** (provincia, región, AMBA) y **entre
cadenas**.

**Canasta fija:** para cada tipo con dicotomía celíaca (fideos secos, galletitas dulces, galletitas saladas y crackers,
rebozador, cereales rellenos) una lista FIJA de productos con TACC y sin TACC elegidos por **continuidad temporal**
(precio todos los meses desde enero de 2022), **cobertura geográfica** (provincias y regiones) y **cobertura por
cadenas**, sobre las salidas del nb09. Reglas, listas y métricas: `docs/BRECHA_CELIACA.md` §14 y
`docs/brecha_celiaca/canasta_fija_2022_2026.csv`.

**Medición:**
- Precio de cada producto en cada sucursal y mes = **mediana de sus precios diarios**, en **$/100 g**.
- En cada sucursal y mes, por **subtipo** (spaghetti, crackers, rellenas…): precio de cada lado = **mediana** de los
  productos presentes (los sabores de una misma línea cuentan como uno); **brecha del subtipo = sin TACC / con TACC
  − 1**, dentro del mismo super (controla el nivel de precios de cada lugar y compara productos equivalentes).
- Como un índice de precios: **subtipo** (mediana entre sucursales) → **tipo** (promedio geométrico de sus subtipos)
  → **canasta** (promedio de los tipos ponderado por el **gasto de los hogares, ENGHo 2017/18**). Serie mensual con
  todas las sucursales y con **panel balanceado**; un subtipo-mes con muy pocas sucursales se imputa con el mes anterior
  (hoja `Imputaciones`).
- Provincias, regiones, empresas, cadenas y sucursales (mapa) se comparan con la **misma canasta de subtipos**: lo que
  un grupo no tiene se completa con la brecha nacional del período y se informa qué parte del peso es imputada.
- **Concentración**: HHI de empresas por **departamento** (Georef de datos.gob.ar; la caché del nb09).
- **Serie TPD (hedónica)**, robustez de la serie mensual frente a la imputación de subtipos (CELDA 8b): por subtipo, log
  del precio = efecto de la sucursal-mes + efecto de cada producto + prima sin TACC del mes. Compara cada producto
  consigo mismo, usa los meses con pocas sucursales que la descriptiva imputa y da intervalos de confianza (agrupados
  por sucursal y por empresa).
- **Análisis complementarios** (CELDA 8c, paneles de expertos del 2026-10-27): sensibilidad de la brecha a cada decisión
  de diseño (también con las sucursales ponderadas por población), índices de precio de cada lado contra el IPC del
  INDEC, disponibilidad del sin TACC (no encontrarlo también es un costo), intervalos de confianza por bootstrap de
  sucursales y de **empresas** (las cadenas fijan el precio de todas sus sucursales), competencia local (empresas a
  ≤ 3 km), composición, varianza y surtido por empresa, regresión hedónica de región y empresa con los mismos productos
  (y con el surtido de cada grupo, y por año), **prima de la misma marca** (separa la prima sin gluten de la de marca),
  costo extra con la Canasta Básica Alimentaria del INDEC y datos para el análisis propio.

**Qué sale** (en `OUTPUT_DIR`): `brecha_celiaca_AAAA-MM.xlsx` (la hoja `Leeme` explica cada hoja y columna), los
gráficos `*.png`, el mapa por provincia y el mapa por sucursal (`.html`) y la carpeta `datos/` (paneles en parquet y
csv.gz para Python, R o Stata, productos, sucursales, diccionario de datos y `LEEME.md`).

**Config en la CELDA 1.** Estructura: Config → Setup → Maestros → Canasta → ZIPs → Lectura (caché por mes) → Brecha por
sucursal × mes × tipo → Agregaciones → Serie TPD → Análisis complementarios → Gráficos → Mapa → Excel → Mapa por
sucursal"""))

# ── CELL 1 — CONFIG ────────────────────────────────────────────────────────────
_CONFIG_PRE = r"""# ===========================================================
# CONFIGURACIÓN — Modificar solo esta sección
# ===========================================================
# CANASTA FIJA 2022-2026 (docs/BRECHA_CELIACA.md §14; lista con métricas: docs/brecha_celiaca/canasta_fija_2022_2026.csv)
# TIPOS: tipo -> {'peso': % del gasto de los hogares en alimentos y bebidas no alcohólicas (ENGHo 2017/18),
#                 'tacc': {EAN: descripción}, 'sin_tacc': {EAN: descripción}}.
#   Algunos productos tienen DOS códigos porque el fabricante cambió el EAN (Molinos en sep-oct 2023, Wakas en jun-2024):
#   van los dos, cada uno con su VIGENCIA (abajo), y PRODUCTO los junta: en cada sucursal y mes el producto entra una
#   vez, con la mediana de sus códigos vigentes. PRODUCTO junta también los sabores de una LÍNEA (misma marca y
#   presentación en el subtipo, al mismo precio): la línea entra una vez, así no manda la marca con más sabores.
#   Cambiar un EAN cambia la clave del caché: relee todo el SEPA. Cambiar GRAMOS, VIGENCIA, PRODUCTO, SUBTIPO, pesos o
#   descripciones NO relee.
"""

_CONFIG_POST = r"""

# Ponderación de la canasta: 'engho' = la brecha de la canasta es el promedio de las brechas por tipo con los pesos
# ENGHo de TIPOS (y la canasta por sucursal usa cantidades = peso / precio con TACC del año base); 'qty' = cantidades
# fijas TIPOS[tipo]['qty'] (el método de las corridas de agosto de 2026).
PONDERACION = 'engho'
ANIO_BASE_PONDERACION = None   # None = los primeros 12 meses del panel

# ── Análisis complementarios (CELDA 8c; BRECHA_CELIACA §15 y docs/EVALUACION_EXPERTOS_2026-10-27_nb06.md) ──
# Escenarios de la hoja Sensibilidad: la brecha nacional de los últimos VENTANA_GEO_MESES meses (misma canasta de
# subtipos que los grupos) cambiando UNA decisión por vez. Claves: 'agregar' = 'sustitutos' (los sustitutos que quedaron
# fuera de la canasta) o 'todos' (todos los ADICIONALES, con sus líneas LINEA_TODOS); 'quitar_sustitutos' = sin los
# SUSTITUTOS de la canasta (el subtipo que se queda sin un lado sale); 'sin_lineas' = cada sabor cuenta como un producto;
# 'pesos_subtipo' = 'disponibilidad' (cada subtipo pesa por sus sucursal-meses en lugar de pesos iguales); 'estimador' =
# 'minimo' (lo más barato de cada lado en la sucursal) o 'nacional' (cociente de las medianas nacionales de cada lado,
# sin comparar dentro de la sucursal); 'pesos_sucursal' = 'poblacion' (mediana ponderada: cada provincia pesa por su
# población, PESOS_POBLACION, repartida entre sus sucursal-meses). Se pueden agregar escenarios combinando claves.
ESCENARIOS_SENSIBILIDAD = {
    'Principal (la canasta de la CELDA 1)': {},
    'Galletas de arroz también en crackers (sustitución)': {'agregar': 'sustitutos'},
    'Solo productos equivalentes (sin las galletas de arroz de saborizadas)': {'quitar_sustitutos': True},
    'Todos los productos que cumplen las reglas (sin composición espejada)': {'agregar': 'todos'},
    'Cada sabor como un producto (sin líneas)': {'sin_lineas': True},
    'Pesos de los subtipos por disponibilidad (sucursal-meses)': {'pesos_subtipo': 'disponibilidad'},
    'Lo más barato de cada lado en la sucursal': {'estimador': 'minimo'},
    'Cociente de las medianas nacionales (sin comparar dentro de la sucursal)': {'estimador': 'nacional'},
    'Sucursales ponderadas por la población de su provincia': {'pesos_sucursal': 'poblacion'},
}
# Población de cada provincia (los mismos pesos del nb02 y el nb05): el escenario 'pesos_sucursal': 'poblacion' reparte la
# de cada provincia entre sus sucursal-meses con los dos lados de cada subtipo (aproxima lo que enfrenta el consumidor;
# con pesos iguales, cada sucursal pesa lo mismo y mandan las provincias con más sucursales en el SEPA)
PESOS_POBLACION = {
    'Buenos Aires': 17709732, 'CABA': 3075646, 'Catamarca': 415438, 'Chaco': 1204541, 'Chubut': 618994,
    'Córdoba': 3978984, 'Corrientes': 1120801, 'Entre Ríos': 1385961, 'Formosa': 605193, 'Jujuy': 770881,
    'La Pampa': 368550, 'La Rioja': 393531, 'Mendoza': 2014533, 'Misiones': 1261294, 'Neuquén': 664057,
    'Río Negro': 747610, 'Salta': 1441998, 'San Juan': 781217, 'San Luis': 531745, 'Santa Cruz': 333473,
    'Santa Fe': 3556522, 'Santiago del Estero': 1019304, 'Tierra del Fuego': 190641, 'Tucumán': 1737127,
}
# Pares de la misma marca (hoja Prima_misma_marca): líneas sin TACC de una marca que se venden con otro nombre. Snuks es
# la línea sin TACC de Lasfor (mismo fabricante, Lasfor SRL; docs/AUDITORIA_SELECCION_2026-10-26_nb06.md §1).
MARCA_EQUIVALENTE = {'SNUKS': 'LASFOR'}
BOOT_B = 200               # intervalos de confianza de la hoja IC_grupos: réplicas de cada bootstrap (por sucursal y por empresa)
BOOT_SEED = 20261027       # semilla fija: dos corridas con los mismos datos dan los mismos intervalos
RADIO_COMPETENCIA_KM = 3   # competencia local: sucursales y empresas a <= este radio de cada sucursal
# Costo con la Canasta Básica Alimentaria del INDEC (GBA; cuadro 2 del informe técnico de la CBA): gramos por adulto
# equivalente por mes de los ítems con gluten que la canasta cubre: (ítem, tipo, subtipo o None = todo el tipo, gramos).
# La CBA tiene además pan (6.750 g) y harina de trigo (1.080 g), que la canasta fija no cubre (sí la canasta amplia, 06b).
CBA_ITEMS = [('Fideos', 'Fideos secos', None, 1740),
             ('Galletitas de agua', 'Galletitas saladas y crackers', 'Crackers', 420),
             ('Galletitas dulces', 'Galletitas dulces', None, 210),
             ('Pan', 'Pan envasado', None, 6750),
             ('Harina de trigo', 'Harinas', None, 1080)]
CBA_AE_HOGAR = 3.09        # adultos equivalentes del hogar tipo 2 del INDEC (pareja de 35 y 31 años con hijos de 6 y 8)
MESES_CBA = 3              # el costo usa la mediana nacional de los últimos MESES_CBA meses
EXPORTAR_DATOS = True      # paneles para el análisis propio en OUTPUT_DIR/datos (parquet y csv.gz)
IPC_XLSX = 'IPC.xlsx'      # IPC del INDEC (columna de fechas, "Nivel general" y "Alimentos y bebidas no alcohólicas") para
                           # la hoja Indices_lados: el nombre dentro de SEPA_DIR o una ruta completa; si falta, sin IPC
NOMBRE_CANASTA = 'canasta fija 2022-2026'   # en los títulos de los gráficos
PREFIJO_EXCEL = 'brecha_celiaca'            # el Excel se llama <PREFIJO_EXCEL>_<AAAA-MM>.xlsx

# Canasta FLEXIBLE (corridas de agosto de 2026): True agrega como candidatos sin TACC todos los productos del maestro
# cuya descripción diga "sin TACC" y matcheen las palabras del tipo (SIN_TACC_REGLA). Rompe la continuidad y hace que
# la canasta dependa de qué maestro_sepa_completo haya en el Drive: dejarlo en False salvo para comparar.
USAR_REGLA_NOMBRE = False
SIN_TACC_REGLA = {
    'Fideos secos': (
        r'fideo|spaghetti|spagueti|tallarin|mostachol|tirabuz|penne|fusilli|codito|cintas|caracol|rigat|letras|moñito|farfalle|dedalitos|cornetti|risoni|canestri|spirali',
        r'premezcla|ñoqui|noqui|harina|frola|salsa|rallado|rebozador|tapa|tarta|sopa|salvado|arroz integral|yamani'),
    'Galletitas dulces': (
        r'galletit|galleta|biscuit|bizcoch|oblea|scon|pepa|magdalena|masita|vainilla|marmolad|nevadit|rueditas',
        r'salad|queso|jamon|cracker|tostada|arroz|pizza|premezcla|bizcochuelo|flan|postre|leche|grisin|palito|semilla|rallado|ensalada|hamburg|pochoclo|pan dulce|cereal|copitas|barrita|turron|budin|budín|yerba|mate|mermelada|caramelo|tableta|bocadito|bombon|gomita|chupetin|jugo|bebida|agua|infusion|pimenton|cacao|dulce de leche|polvo|helado|alfajor'),
    'Galletitas saladas y crackers': (
        r'cracker|tostada|tortita|talita|chalita|grisin|bizcochito|tostadita|(?:galletit|galleta).*(?:salad|queso|jamon|de arroz|pizza)|snack.*queso|palito.*(?:maiz|queso)',
        r'dulce|vainilla|chocolate|coco|limon|pepas|marmolad|premezcla|budin|oblea|alfajor|flan|leche|manteca|fideo|ensalada|hamburg|dambo|yamani|arroz integral|bizcochuelo|scon|rallado'),
    'Pan rallado y rebozador': (r'pan rallado|rebozador|rebozar|apanad', r'premezcla|coco|queso rallado'),
}

# EANs a excluir a mano (se filtran en la CELDA 7, después de leer: NO cambian el caché). Vacío por diseño: los errores
# de carga los saca el filtro de plausibilidad (banda x FACTOR_PLAUS, CELDA 7), que es simétrico y reproducible.
EANS_EXCLUIR = set()
FACTOR_PLAUS = 4   # banda de plausibilidad a nivel EAN (precio relativo a sus pares del mes)
FACTOR_EMPRESA = 2.5   # precio de una EMPRESA fuera de escala: su mediana de un código en un mes contra la mediana entre
                       # empresas del mismo código y mes (una por empresa, con >= 3); afuera esas observaciones (hoja
                       # Precios_atipicos). Ej.: DIA, sep-2026, chips Smams a $860/100 g contra ~$2.550 en las demás
MESES_CONGELADO = 6    # precio CONGELADO de una empresa: el mismo precio de un código >= MESES_CONGELADO meses seguidos
SUBA_CONGELADO = 0.5   # con el índice de su tipo y lado arriba más de SUBA_CONGELADO (50%) desde que lo fijó: afuera esos
                       # meses (hoja Precios_congelados). Ej.: Deheza, galletas de arroz Crisppino al mismo precio de
                       # abr-2023 a jul-2024 (el índice subió 304%)

SEPA_SOURCE = 'mi_drive'   # 'mi_drive' | 'local'
SEPA_DIR    = '/content/drive/MyDrive/carga'
OUTPUT_DIR  = '/content/drive/MyDrive/carga/output_brecha'
USE_CACHE = True

MES_INICIO_HISTORICO = '2022-01'   # la canasta fija se eligió con continuidad desde enero de 2022
MIN_TIPOS = 1         # tipos con los dos lados para que una sucursal-mes cuente en la canasta POR SUCURSAL (mapa)
MIN_SUC_AGG = 30      # sucursales mínimas para marcar una desagregación como confiable
MIN_SUC_SUBTIPO = 10  # sucursales mínimas para que un subtipo entre en la brecha de su tipo en un mes o grupo
FRAC_SUBTIPO_MES = 0.5   # serie mensual: un subtipo-mes con menos de esta fracción de sus sucursales habituales se
                         # imputa con su último mes válido (cambios de código de Molinos en sep-oct 2023, su hueco de
                         # dic-2023 a mar-2024: la mediana de pocas sucursales distintas movía el tipo entero)
FRAC_MESES_PANEL = 0.7   # panel balanceado: sucursal x tipo presentes en >= este % de los meses
VENTANA_GEO_MESES = 12   # provincias, regiones y cadenas: últimos N meses (además de las tablas por año)
MAX_PESO_IMPUTADO = 25   # provincias, regiones, empresas, cadenas y sucursales se comparan con la MISMA canasta (los 12
                         # subtipos con sus pesos): el subtipo con < MIN_SUC_SUBTIPO sucursales en el grupo toma la brecha
                         # nacional del mismo período. Confiable = eso pesa <= este % y el grupo tiene >= MIN_SUC_AGG sucursales
USAR_GEOREF = True       # concentración: departamento de cada sucursal por coordenadas (API Georef de datos.gob.ar); usa la
                         # caché del nb09 (output_trazabilidad/_cache_nb09/) y consulta solo las sucursales que falten
MIN_SUC_DEPTO = 5        # concentración: sucursales con brecha propia para mostrar un departamento

# Comercios fuera del universo: estaciones de servicio (19, 3001, 4 Estación Lima, 23 Axion Energy), Mercado Libre
# (2013) y farmacias (24 Farmacity / Simplicity)
CADENAS_FILTRAR = {'19', '2013', '3001', '4', '23', '24'}
# Sucursales que no son locales: además de las de tipo web o virtual, las que el maestro carga con tipo Supermercado o
# Autoservicio y el nombre lo dice (DIA "eCommerce", Libertad "Dark Store Mendoza", "WEB"; BUG-48)
SUCURSALES_NO_FISICAS = r'e-?commerce|dark ?store|\bweb\b|\bmeli\b|\bonline\b'

RECLASIF_TOL_KM = 100   # provincia: se cambia solo si la sucursal cae a más de esto de su provincia declarada (BUG-44)
AMBA_RADIO_KM = 90      # AMBA = CABA + Buenos Aires a <= AMBA_RADIO_KM del Obelisco (BUG-42)"""

cells.append(cell_code(_CONFIG_PRE + _bloque_canasta() + _CONFIG_POST))

# ── CELL 2 — SETUP ─────────────────────────────────────────────────────────────
cells.append(cell_code(r"""# ============================================================
# CELDA 2 — Montar Drive + dependencias + imports
# ============================================================
try:
    import google.colab
    from google.colab import drive
    drive.mount('/content/drive')
    print('Google Drive montado')
except ImportError:
    print('Entorno local')

import subprocess, sys
subprocess.run([sys.executable, '-m', 'pip', 'install', 'openpyxl', 'tqdm', 'pyarrow', '-q'], check=False)

import zipfile, gzip, io, re, shutil, warnings, gc, hashlib, tempfile, calendar as _cal
import json as _json
from pathlib import Path
from tqdm.auto import tqdm
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.dates as mdates
from matplotlib.colors import LinearSegmentedColormap, Normalize
import seaborn as sns

plt.rcParams['figure.figsize'] = (13, 6)
plt.rcParams['font.size'] = 11
sns.set_theme(style='whitegrid')
pd.set_option('display.max_columns', 50)
pd.set_option('display.float_format', '{:,.2f}'.format)

SEPA_DIR   = Path(SEPA_DIR)
OUTPUT_DIR = Path(OUTPUT_DIR)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR  = OUTPUT_DIR / '_cache'
if USE_CACHE:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR = (Path('/content/tmp_sepa_nb06') if Path('/content').exists()
           else Path(tempfile.gettempdir()) / 'tmp_sepa_nb06')
TMP_DIR.mkdir(parents=True, exist_ok=True)

GEOJSON_PATH = SEPA_DIR / 'ar.json'
# Departamento de cada sucursal (concentración, CELDA 7): la caché de Georef que arma el nb09 en el Drive
GEOREF_PATH = SEPA_DIR / 'output_trazabilidad' / '_cache_nb09' / 'georef_sucursales.parquet'

def normalizar_ean(s):
    if pd.isna(s): return None
    s = str(s).strip().lstrip('0')
    return s if s else '0'

# EANs de referencia SOLO para detectar el factor centavos/pesos de cada mes.
REF_EANS_FACTOR = {'7790072002080', '7790070320285', '7790132098459'}

# ── Promedio con outliers fuera (banda relativa a la mediana) ────────────────
# Descarta valores fuera de [mediana/4, mediana x4] antes de promediar (igual que nb02/nb05).
def _pmean(_s):
    _s = pd.to_numeric(_s, errors='coerce').dropna()
    if len(_s) == 0: return float('nan')
    _m = _s.median()
    if _m and _m > 0:
        _f = _s[(_s >= _m/4) & (_s <= _m*4)]
        if len(_f) > 0: _s = _f
    return _s.mean()

print(f'SEPA_DIR:   {SEPA_DIR}')
print(f'OUTPUT_DIR: {OUTPUT_DIR}')
print(f'  ar.json:  {"OK" if GEOJSON_PATH.exists() else "NO ENCONTRADO (no se reclasifican provincias ni hay mapas)"}')
print(f'  Georef:   {"caché del nb09 OK" if GEOREF_PATH.exists() else "sin la caché del nb09 (la CELDA 7 consulta la API)"}')"""))

# ── CELL 3 — MAESTROS ──────────────────────────────────────────────────────────
cells.append(cell_code(r"""# ============================================================
# CELDA 3 — Maestros de sucursales, cadenas, provincias y productos
# ============================================================
DATA_URL = 'https://raw.githubusercontent.com/santiagoriverti/precios_minoristas_supermercados/main/data'

def leer_maestro(nombre, **kwargs):
    # Busqueda: ./data (local) -> Drive (SEPA_DIR y SEPA_DIR/data) -> cache -> GitHub raw.
    # El fallback a GitHub SOLO funciona si el repositorio es PUBLICO. Con el repo privado
    # raw.githubusercontent devuelve 404, asi que hay que dejar los maestros en el Drive,
    # junto a los ZIPs del SEPA.
    _cands = [Path('data') / nombre]
    try:
        _cands += [Path(SEPA_DIR) / nombre, Path(SEPA_DIR) / 'data' / nombre]
    except Exception:
        pass
    _cands.append(Path('/content/data') / nombre)
    for _p in _cands:
        if _p.exists():
            return pd.read_excel(_p, **kwargs)
    import urllib.request, urllib.parse
    dl = Path('/content/data') / nombre
    Path('/content/data').mkdir(parents=True, exist_ok=True)
    try:
        print(f'  Descargando {nombre} desde GitHub...')
        urllib.request.urlretrieve(f'{DATA_URL}/{urllib.parse.quote(nombre)}', dl)
    except Exception as _e:
        raise FileNotFoundError(
            f"No se pudo obtener '{nombre}'. Se busco en ./data, el Drive y GitHub ({_e}). "
            f"Si el repositorio es PRIVADO, GitHub responde 404: copia '{nombre}' a la carpeta "
            f"del Drive donde estan los ZIPs del SEPA.")
    return pd.read_excel(dl, **kwargs)

print('Cargando maestros...')
maestro_suc = leer_maestro('maestro_sucursales_completo.xlsx')
for c in ['id_comercio','id_bandera','id_sucursal']:
    maestro_suc[c] = maestro_suc[c].astype(str)

suc_pais = maestro_suc[
    maestro_suc['sucursales_latitud'].notna() &
    maestro_suc['sucursales_longitud'].notna() &
    (maestro_suc['sucursales_latitud'].between(-55, -22)) &
    (maestro_suc['sucursales_longitud'].between(-73, -53))
].copy()
IDS_PAIS = set(zip(suc_pais['id_comercio'], suc_pais['id_bandera'], suc_pais['id_sucursal']))
print(f'  Sucursales validas: {len(suc_pais):,} | IDs unicos: {len(IDS_PAIS):,}')

# Nombres según el comercio.csv del SEPA (SEPA diario, oct-2026). 'cadena' = bandera; 'empresa' = comercio.
NOMBRES_COMPUESTOS = {
    ('9','1'):'Vea', ('9','2'):'Disco', ('9','3'):'Jumbo',
    ('10','1'):'Carrefour', ('10','2'):'Carrefour Market', ('10','3'):'Carrefour Express', ('10','4'):'Carrefour Maxi',
    ('11','1'):'SuperChangomas', ('11','2'):'ChangoMas', ('11','3'):'SuperChangomas', ('11','4'):'SuperChangomas',
    ('11','5'):'HiperChangomas',
    ('16','1'):'Hipermercado Libertad', ('16','2'):'Mini Libertad',
}
NOMBRES_SIMPLES = {
    '2':'La Anónima', '3':'Deheza', '5':'California', '6':'Comodín', '8':'Mariano Max', '12':'Coto',
    '13':'Cooperativa Obrera', '15':'DIA', '20':'La Agrícola Regional', '21':'Toledo', '23':'Axion Energy',
    '24':'Farmacity', '47':'Unicoop',
}
EMPRESAS = {'9':'Cencosud (Vea, Disco, Jumbo)', '10':'Carrefour', '11':'ChangoMas', '16':'Libertad'}

def asignar_cadena(row):
    k = (row['id_comercio'], row['id_bandera'])
    if k in NOMBRES_COMPUESTOS: return NOMBRES_COMPUESTOS[k]
    if row['id_comercio'] in NOMBRES_SIMPLES: return NOMBRES_SIMPLES[row['id_comercio']]
    return f"Cadena {row['id_comercio']}"

def asignar_empresa(_c):
    return EMPRESAS.get(_c) or NOMBRES_SIMPLES.get(_c) or f'Cadena {_c}'

PROV_NORM = {
    'Ciudad Autonoma de Buenos Aires':'CABA',
    'Ciudad Autónoma de Buenos Aires':'CABA',
    'Provincia de Buenos Aires':'Buenos Aires',
    'Provincia de Catamarca':'Catamarca',
    'Provincia del Chaco':'Chaco','Provincia del Chubut':'Chubut',
    'Provincia de Cordoba':'Córdoba','Provincia de Córdoba':'Córdoba',
    'Provincia de Corrientes':'Corrientes',
    'Provincia de Entre Rios':'Entre Ríos','Provincia de Entre Ríos':'Entre Ríos',
    'Provincia de Formosa':'Formosa','Provincia de Jujuy':'Jujuy',
    'Provincia de La Pampa':'La Pampa','Provincia de La Rioja':'La Rioja',
    'Provincia de Mendoza':'Mendoza','Provincia de Misiones':'Misiones',
    'Provincia del Neuquen':'Neuquén','Provincia del Neuquén':'Neuquén','Neuquén':'Neuquén',
    'Provincia de Rio Negro':'Río Negro','Provincia de Río Negro':'Río Negro',
    'Provincia de Salta':'Salta','Provincia de San Juan':'San Juan',
    'Provincia de San Luis':'San Luis','Provincia de Santa Cruz':'Santa Cruz',
    'Provincia de Santa Fe':'Santa Fe',
    'Provincia de Santiago del Estero':'Santiago del Estero',
    'Provincia de Tierra del Fuego, Antartida e Islas del Atlantico Sur':'Tierra del Fuego',
    'Provincia de Tierra del Fuego, Antártida e Islas del Atlántico Sur':'Tierra del Fuego',
    'Tierra del Fuego':'Tierra del Fuego',
    'Provincia de Tucuman':'Tucumán','Provincia de Tucumán':'Tucumán',
    'Buenos Aires':'Buenos Aires','CABA':'CABA','Catamarca':'Catamarca',
    'Chaco':'Chaco','Chubut':'Chubut','Córdoba':'Córdoba','Corrientes':'Corrientes',
    'Entre Ríos':'Entre Ríos','Formosa':'Formosa','Jujuy':'Jujuy',
    'La Pampa':'La Pampa','La Rioja':'La Rioja','Mendoza':'Mendoza',
    'Misiones':'Misiones','Río Negro':'Río Negro','Salta':'Salta',
    'San Juan':'San Juan','San juan':'San Juan','SAN JUAN':'San Juan',
    'San Luis':'San Luis','Santa Cruz':'Santa Cruz',
    'Santa Fe':'Santa Fe','Santiago del Estero':'Santiago del Estero','Tucumán':'Tucumán',
}
# Regiones INDEC; Buenos Aires se parte en AMBA (por coordenadas, CELDA 7) y resto (Pampeana)
REGION_PROV = {
    'CABA':'AMBA', 'Buenos Aires':'Pampeana', 'Córdoba':'Pampeana', 'Entre Ríos':'Pampeana', 'La Pampa':'Pampeana',
    'Santa Fe':'Pampeana', 'Catamarca':'Noroeste', 'Jujuy':'Noroeste', 'La Rioja':'Noroeste', 'Salta':'Noroeste',
    'Santiago del Estero':'Noroeste', 'Tucumán':'Noroeste', 'Chaco':'Noreste', 'Corrientes':'Noreste',
    'Formosa':'Noreste', 'Misiones':'Noreste', 'Mendoza':'Cuyo', 'San Juan':'Cuyo', 'San Luis':'Cuyo',
    'Chubut':'Patagonia', 'Neuquén':'Patagonia', 'Río Negro':'Patagonia', 'Santa Cruz':'Patagonia',
    'Tierra del Fuego':'Patagonia',
}

_mp_raw = leer_maestro('Maestro de Productos Interno.xlsx', dtype=str,
                       usecols=['producto_sepa_id','producto_descripcion','producto_marca','rubro',
                                'producto_cantidad_presentacion','producto_unidad_medida_presentac'])
# Maestro SEPA COMPLETO (opcional, del Drive carga/): nombres de productos que no están en el interno. Con la canasta
# fija solo se usa como respaldo de las descripciones (las de la canasta vienen en TIPOS).
_msepa = None
try:
    _msp = Path(SEPA_DIR) / 'maestro_sepa_completo.csv.gz'
    if _msp.exists():
        _msepa = pd.read_csv(_msp, dtype=str)
        print(f'  Maestro SEPA completo (Drive): {len(_msepa):,} EANs')
except Exception as _e:
    print(f'  (aviso: no se pudo leer maestro_sepa_completo.csv.gz: {_e})')

def _prep_master(_df):
    _df = _df.rename(columns={'producto_descripcion':'descripcion','producto_marca':'marca'})
    if 'rubro' not in _df.columns: _df['rubro'] = ''
    _df['ean_norm'] = _df['producto_sepa_id'].map(normalizar_ean)
    return _df[['ean_norm','descripcion','marca','rubro',
                'producto_cantidad_presentacion','producto_unidad_medida_presentac']]

_base = _prep_master(_mp_raw)
if _msepa is not None:
    _extra = _prep_master(_msepa)
    _extra = _extra[~_extra['ean_norm'].isin(set(_base['ean_norm']))]   # solo EANs que faltan
    MP_META = pd.concat([_base, _extra], ignore_index=True)
    print(f'  Fusión de maestros: interno {len(_base):,} + {len(_extra):,} nuevos del SEPA = {len(MP_META):,} EANs')
else:
    MP_META = _base

# gramos/ml de la presentación (respaldo de GRAMOS): del CAMPO presentación o, si no da, de la descripción
def _to_gramos(_q, _u):
    _q = pd.to_numeric(str(_q).replace(',', '.'), errors='coerce'); _u = str(_u).strip().lower()
    if pd.isna(_q) or _q <= 0: return np.nan
    if _u in ('kg','kgm','l','lt','litro','litros','kilogramo','kilogramos'): return _q * 1000
    if _u in ('gr','g','grs','gramo','gramos','ml','cc','mililitro'): return _q
    return np.nan
_RE_GR = re.compile(r'(\d+(?:[.,]\d+)?)\s*(kg|kgm|kilo|grs?|gramos?|ml|cc|lts?|litros?|g)\b')
def _gramos_desc(_s):
    _m = _RE_GR.search(str(_s).lower())
    if not _m: return np.nan
    _v = float(_m.group(1).replace(',', '.')); _u = _m.group(2)
    if _u.startswith('k') or _u in ('lt','l','lts','litro','litros'): return _v * 1000
    return _v
_g1 = [_to_gramos(a, b) for a, b in zip(MP_META['producto_cantidad_presentacion'],
                                        MP_META['producto_unidad_medida_presentac'])]
_g2 = [_gramos_desc(x) for x in MP_META['descripcion']]
MP_META['grams'] = [(_a if (_a == _a) else _b) for _a, _b in zip(_g1, _g2)]
MP_META = (MP_META.dropna(subset=['ean_norm']).drop_duplicates('ean_norm')
           .set_index('ean_norm')[['descripcion','marca','rubro','grams']])
print(f'  Maestro de productos (total): {len(MP_META):,} EANs con metadata')
print('Maestros OK')"""))

# ── CELL 4 — CANASTA ───────────────────────────────────────────────────────────
cells.append(cell_code(r"""# ============================================================
# CELDA 4 — Canasta: productos con TACC / sin TACC por tipo (CELDA 1)
# ============================================================
def _norm_ean(_e):
    _l = re.sub(r'\D', '', str(_e))
    return (_l.lstrip('0') or '0') if _l else None

def _items(_x):
    # {EAN: descripción} o [EAN, ...] -> {ean_norm: descripción o None}
    if isinstance(_x, dict):
        return {_norm_ean(k): (str(v) if v else None) for k, v in _x.items() if _norm_ean(k)}
    return {_norm_ean(k): None for k in _x if _norm_ean(k)}

# Canasta flexible (opcional): candidatos sin TACC por nombre
_desc_all = MP_META['descripcion'].fillna('').astype(str).str.lower()
_gf_all = _desc_all.str.contains(r'sin tacc|sin gluten|libre de gluten|s/tacc', regex=True)
def _sin_por_regla(_tp):
    _r = SIN_TACC_REGLA.get(_tp)
    if not _r: return set()
    _kw, _ex = _r
    _m = _gf_all & _desc_all.str.contains(_kw, regex=True) & ~_desc_all.str.contains(_ex, regex=True)
    return set(MP_META.index[_m])

TIPO_TACC, TIPO_SIN, TIPO_QTY, TIPO_PESO = {}, {}, {}, {}
EAN_TIPO, EAN_ROL, EAN_DESC = {}, {}, {}
for _tipo, _cfg in TIPOS.items():
    _t = _items(_cfg.get('tacc', {}))
    _s = _items(_cfg.get('sin_tacc', {}))
    if USAR_REGLA_NOMBRE:
        _s.update({_e: None for _e in _sin_por_regla(_tipo) if _e not in _s and _e not in _t})
    if not _t or not _s:
        print(f'AVISO: el tipo "{_tipo}" no tiene EANs en los dos lados: se ignora.')
        continue
    _dup = (set(_t) & set(_s)) | ((set(_t) | set(_s)) & set(EAN_TIPO))
    if _dup:
        raise ValueError(f'EANs repetidos entre lados o tipos en "{_tipo}": {sorted(_dup)}')
    TIPO_TACC[_tipo] = set(_t)
    TIPO_SIN[_tipo]  = set(_s)
    TIPO_QTY[_tipo]  = float(_cfg.get('qty', 1))
    TIPO_PESO[_tipo] = float(_cfg.get('peso', float('nan')))
    for _e, _d in _t.items(): EAN_TIPO[_e] = _tipo; EAN_ROL[_e] = 'tacc'; EAN_DESC[_e] = _d
    for _e, _d in _s.items(): EAN_TIPO[_e] = _tipo; EAN_ROL[_e] = 'sin';  EAN_DESC[_e] = _d
if not TIPO_TACC:
    raise ValueError('Ningún tipo válido en TIPOS (cada tipo necesita EANs con TACC y sin TACC).')
EANS_CONFIG = set(EAN_TIPO)
# Productos ADICIONALES (CELDA 1): se leen con la canasta para los escenarios de sensibilidad de la CELDA 8c; no entran
# en la brecha principal
ADIC_INFO = {_norm_ean(k): v for k, v in globals().get('ADICIONALES', {}).items() if _norm_ean(k)}
EANS_ADIC = set(ADIC_INFO) - EANS_CONFIG
EANS_LEER = EANS_CONFIG | EANS_ADIC

# Descripción: la de TIPOS (o la del maestro). Gramos: GRAMOS (verificados) o, si falta, el maestro (con aviso).
_GR_CFG = {_norm_ean(k): float(v) for k, v in globals().get('GRAMOS', {}).items() if _norm_ean(k)}
EAN_GRAMS, _gr_maestro, _sin_gramos = {}, [], []
for _e in sorted(EANS_CONFIG):
    if not EAN_DESC.get(_e):
        _dm = MP_META['descripcion'].get(_e) if _e in MP_META.index else None
        EAN_DESC[_e] = str(_dm)[:60] if isinstance(_dm, str) and _dm else f'EAN {_e}'
    _g = _GR_CFG.get(_e, float('nan'))
    if not (_g > 0):
        _g = MP_META['grams'].get(_e, float('nan')) if _e in MP_META.index else float('nan')
        if _g > 0:
            _gr_maestro.append(_e)
    if _g > 0:
        EAN_GRAMS[_e] = float(_g)
    else:
        _sin_gramos.append(_e)
if _gr_maestro:
    print(f'AVISO: {len(_gr_maestro)} EAN sin GRAMOS en la CELDA 1, se usan los del maestro: {_gr_maestro}')
if _sin_gramos:
    print(f'AVISO: {len(_sin_gramos)} EAN sin gramos (quedan afuera, no se pueden pasar a $/100 g): {_sin_gramos}')

# ── Subtipo / EQUIVALENCIA dentro de cada tipo (mapa y hoja Comparacion_productos) ──
# Fideos: por FORMA (Spaghetti↔Spaghetti, Tirabuzón↔Tirabuzón…), que sí es una equivalencia real. En los demás tipos
# los surtidos con y sin TACC son variedades distintas: la equivalencia honesta es el tipo (un solo grupo).
_SUBTIPO_KW = {
    'Fideos secos': [
        ('Spaghetti', ['spaghetti','spagueti','spaguetti','spaghettini','cabello','vermicelli','fideo fino','fideos finos']),
        ('Tallarín/Cintas', ['tallarin','tallarín','fettuccini','fetuccini','fettuccine','cintas','nido','canestri']),
        ('Mostachol/Penne', ['mostachol','rigati','rigato','penne','pluma','plumita','rigate']),
        ('Tirabuzón/Fusilli', ['tirabuzon','tirabuzón','fusilli','fusili','caracol','spirali']),
        ('Corto (codito, dedalito...)', ['codito','dedalitos','dedalito','tornillo','moñito','moñitos','farfalle',
                                         'risoni','cornetti','coditos','municion','ave maria','ave maría','letritas']),
    ],
}
def _subtipo(_desc, _tipo):
    if _tipo not in _SUBTIPO_KW:
        return _tipo
    _d = str(_desc).lower()
    for _lab, _kws in _SUBTIPO_KW[_tipo]:
        if any(_k in _d for _k in _kws):
            return _lab
    return 'Otros'
# El subtipo de la canasta fija (SUBTIPO, CELDA 1) manda; sin él, por palabras de la descripción
_SUBT_CFG = {_norm_ean(_e): _s for _s, _es in globals().get('SUBTIPO', {}).items() for _e in _es if _norm_ean(_e)}
EAN_SUBTIPO = {_e: _SUBT_CFG.get(_e) or _subtipo(EAN_DESC.get(_e, ''), EAN_TIPO[_e]) for _e in EANS_CONFIG}

print(f'Tipos: {len(TIPO_TACC)} | EANs de la canasta: {len(EANS_CONFIG)} | con gramos: {len(EAN_GRAMS)} | '
      f'adicionales (sensibilidad, CELDA 8c): {len(EANS_ADIC)}')
for _t in TIPO_TACC:
    print(f'  [{_t}] {TIPO_PESO[_t]:.3f}% del gasto en alimentos (ENGHo) | con TACC: {len(TIPO_TACC[_t])} · '
          f'sin TACC: {len(TIPO_SIN[_t])}')"""))

# ── CELL 5 — ZIPs ──────────────────────────────────────────────────────────────
cells.append(cell_code(r"""# ============================================================
# CELDA 5 — ZIPs del SEPA: un archivo por parte de cada mes
# ============================================================
_PAT_SEM  = re.compile(r'^(\d{4})(A|B)$', re.IGNORECASE)
_PAT_ARC  = re.compile(r'^(\d{2})(\d{4})_pais_parte(\d+).*COMPLETO.*\.csv\.gz$', re.IGNORECASE)
PAT_FECHA = re.compile(r'^precio_(\d{8})$')

def detectar_semestres():
    result = []
    for z in sorted(SEPA_DIR.glob('*.zip')):
        m = _PAT_SEM.match(z.stem)
        if m:
            result.append((z, int(m.group(1)), m.group(2).upper()))
    return result

def _dias_archivo(z, nombre):
    with zipfile.ZipFile(z) as zf:
        with zf.open(nombre) as s:
            with gzip.open(s, 'rt', encoding='utf-8', errors='replace') as g:
                return sum(1 for c in g.readline().split(',') if c.strip().startswith('precio_'))

def archivos_por_mes():
    # {mes: [(zip, archivo), ...]} con UN archivo por parte del mes. Si hay más de uno para la misma parte (2024B.zip
    # trae 082024_pais_parte1COMPLETO.csv.gz, días 1 a 5, y ...COMPLETOb.csv.gz, días 1 a 15, con los mismos precios),
    # se usa el que cubre más días, como el nb08 y el nb09 (las corridas anteriores del nb06 leían los dos).
    cand = {}
    for z, _a, _s in detectar_semestres():
        with zipfile.ZipFile(z) as zf:
            for info in zf.infolist():
                m = _PAT_ARC.match(Path(info.filename).name)
                if m:
                    mes = f'{m.group(2)}-{m.group(1)}'
                    if mes >= MES_INICIO_HISTORICO:
                        cand.setdefault((mes, int(m.group(3))), []).append((z, info.filename, info.file_size))
    meses = {}
    for (mes, parte), c in sorted(cand.items()):
        if len(c) > 1:
            dias = [_dias_archivo(z, n) for z, n, _t in c]
            k = max(range(len(c)), key=lambda j: (dias[j], c[j][2], j))
            print(f'  AVISO {mes} parte {parte}: {len(c)} archivos ('
                  + '; '.join(f'{Path(n).name} {d} días' for (z, n, _t), d in zip(c, dias))
                  + f'); se usa {Path(c[k][1]).name}')
            c = [c[k]]
        meses.setdefault(mes, []).append(c[0][:2])
    return meses

_mapa_mes = archivos_por_mes()
_meses_disp = sorted(_mapa_mes)
if not _meses_disp:
    raise RuntimeError(f'No hay meses disponibles >= {MES_INICIO_HISTORICO} en {SEPA_DIR}')
_mes_actual = _meses_disp[-1]   # mes en curso -> NUNCA se cachea
print(f'Meses disponibles: {len(_meses_disp)}  ({_meses_disp[0]} → {_meses_disp[-1]})')
_huecos = [str(p) for p in pd.period_range(_meses_disp[0], _meses_disp[-1], freq='M') if str(p) not in _mapa_mes]
if _huecos:
    print(f'  AVISO: meses sin archivo en los zips: {_huecos}')"""))

# ── CELL 6 — LECTURA ───────────────────────────────────────────────────────────
cells.append(cell_code(r"""# ============================================================
# CELDA 6 — Lectura MENSUAL de precios (una fila por sucursal × EAN × mes), con caché por mes
# ============================================================
# Para cada mes >= MES_INICIO_HISTORICO, el precio de cada EAN de la canasta en cada sucursal es la MEDIANA de sus
# precios diarios del mes (de todas las partes) y 'dias' los días con precio. Se filtran las LÍNEAS del CSV por EAN
# antes de parsear (como el nb08). Filas repetidas del SEPA (misma sucursal, producto y día): una sola vez. Factor
# centavos/pesos por mes con los EANs de referencia. Solo sucursales del maestro con coordenadas.
# Caché: un archivo por MES CERRADO en _cache/brecha_v3_<clave>/ (si Colab se corta, al volver a ejecutar sigue donde
# quedó); el mes en curso se lee siempre. La clave cambia con los EANs de la canasta y los ADICIONALES. El caché NO mira
# si cambió el zip: si se reemplaza el zip de un mes ya guardado (p. ej. el semestral oficial de 2026B), borrar sus
# AAAA-MM.parquet.
_K = ['id_comercio', 'id_bandera', 'id_sucursal', 'ean_norm']
_EANS_LECTURA = EANS_LEER | REF_EANS_FACTOR
_SUC_OK = {f'{a}|{b}|{c}' for a, b, c in IDS_PAIS}
_cache_key = hashlib.md5('|'.join(sorted(EANS_LEER)).encode()).hexdigest()[:8]
_cache_dir = CACHE_DIR / f'brecha_v3_{_cache_key}'

def _leer_archivo(_z, _nombre):
    # Líneas del CSV con EANs de la canasta (o de referencia) -> filas (sucursal, EAN, día, precio)
    _keep = []
    with zipfile.ZipFile(_z) as _zf:
        with _zf.open(_nombre) as _s:
            with gzip.open(_s, 'rt', encoding='utf-8', errors='replace') as _g:
                _hdr = _g.readline()
                _i = [c.strip().strip('"') for c in _hdr.split(',')].index('id_producto')
                for _line in _g:
                    _p = _line.split(',', _i + 2)
                    if len(_p) > _i and _p[_i].strip().strip('"').lstrip('0') in _EANS_LECTURA:
                        _keep.append(_line)
    if not _keep:
        return None
    _df = pd.read_csv(io.StringIO(_hdr + ''.join(_keep)), dtype=str, low_memory=False)
    del _keep
    _df.columns = [c.strip().strip('"') for c in _df.columns]
    _cp = [c for c in _df.columns if PAT_FECHA.match(c)]
    _df['ean_norm'] = _df['id_producto'].astype(str).str.strip().str.lstrip('0')
    for _c in ['id_comercio', 'id_bandera', 'id_sucursal']:
        _df[_c] = _df[_c].astype(str).str.strip()
    _L = _df.melt(id_vars=_K, value_vars=_cp, var_name='dia', value_name='precio')
    _L['precio'] = pd.to_numeric(_L['precio'], errors='coerce')
    _L = _L[_L['precio'] > 0].copy()
    _L['dia'] = _L['dia'].str[-8:]
    return _L

def _leer_mes(_lbl):
    _ps = [_p for _p in (_leer_archivo(_z, _n) for _z, _n in _mapa_mes[_lbl]) if _p is not None and len(_p)]
    if not _ps:
        return None
    _L = pd.concat(_ps, ignore_index=True)
    del _ps
    _ref = _L.loc[_L['ean_norm'].isin(REF_EANS_FACTOR), 'precio']
    _med_ref = float(_ref.median()) if len(_ref) else float(_L['precio'].median())
    _fac = 100 if _med_ref > 10_000 else 1
    _L = _L[_L['ean_norm'].isin(EANS_LEER)]
    _L = _L[(_L['id_comercio'] + '|' + _L['id_bandera'] + '|' + _L['id_sucursal']).isin(_SUC_OK)]
    if not len(_L):
        return None
    if _fac == 100:
        _L['precio'] = _L['precio'] / 100
    _L = _L.groupby(_K + ['dia'], as_index=False)['precio'].median()          # filas repetidas: una vez por día
    _A = _L.groupby(_K, as_index=False).agg(precio=('precio', 'median'), dias=('precio', 'size'))
    _A['mes'] = _lbl
    _A['factor'] = _fac
    return _A

_cerrados = [m for m in _meses_disp if m < _mes_actual]
_mem = {}
if USE_CACHE:
    _cache_dir.mkdir(parents=True, exist_ok=True)
    _en_cache = {p.stem for p in _cache_dir.glob('????-??.parquet')}
else:
    _en_cache = set()
_faltan = [m for m in _cerrados if m not in _en_cache]
print(f'Caché {_cache_dir.name}: {len(set(_cerrados) & _en_cache)} meses cerrados guardados, {len(_faltan)} por leer '
      f'(+ el mes en curso {_mes_actual}, que se lee siempre)')
for _lbl in tqdm(_faltan, desc='Meses cerrados'):
    _d = _leer_mes(_lbl)
    if _d is None:
        print(f'  {_lbl}: sin precios de la canasta')
        continue
    if USE_CACHE:
        _d.to_parquet(_cache_dir / f'{_lbl}.parquet', index=False)
    else:
        _mem[_lbl] = _d
    del _d; gc.collect()

_partes = []
for _m in _cerrados:
    if USE_CACHE and (_cache_dir / f'{_m}.parquet').exists():
        _partes.append(pd.read_parquet(_cache_dir / f'{_m}.parquet'))
    elif _m in _mem:
        _partes.append(_mem[_m])
_actual = _leer_mes(_mes_actual)
if _actual is not None:
    _partes.append(_actual)
if not _partes:
    raise RuntimeError('Sin datos para los EANs de la canasta. Revisá los EANs de TIPOS (CELDA 1).')
datos_dia = pd.concat(_partes, ignore_index=True)
del _partes, _mem; gc.collect()
datos_dia = datos_dia.sort_values('mes').reset_index(drop=True)

ULTIMO_MES = _mes_actual
_NOM = {'01':'enero','02':'febrero','03':'marzo','04':'abril','05':'mayo','06':'junio',
        '07':'julio','08':'agosto','09':'septiembre','10':'octubre','11':'noviembre','12':'diciembre'}
NOMBRE_MES_TITLE = f"{_NOM[_mes_actual[5:7]]} {_mes_actual[:4]}".title()
_fx = datos_dia.groupby('mes')['factor'].first()
_e_dd = set(datos_dia['ean_norm'])
print(f'Observaciones (sucursal×EAN×mes): {len(datos_dia):,} | EANs con datos: {len(_e_dd & EANS_CONFIG)}/{len(EANS_CONFIG)}'
      + (f' | adicionales: {len(_e_dd & EANS_ADIC)}/{len(EANS_ADIC)}' if EANS_ADIC else ''))
print(f'Meses: {datos_dia["mes"].min()} → {datos_dia["mes"].max()} ({datos_dia["mes"].nunique()}) | Sucursales: '
      f'{datos_dia.groupby(["id_comercio","id_bandera","id_sucursal"]).ngroups:,} | meses en centavos: '
      f'{list(_fx[_fx == 100].index) or "ninguno"}')
_sin_datos = sorted(EANS_CONFIG - set(datos_dia['ean_norm']))
if _sin_datos:
    print(f'  AVISO: EANs de la canasta sin ningún precio: {_sin_datos}')"""))

# ── CELL 7 — BRECHA POR SUCURSAL × MES × TIPO ──────────────────────────────────
cells.append(cell_code(r"""# ============================================================
# CELDA 7 — Brecha INTRA-SUPERMERCADO por tipo (sucursal × mes)
# ============================================================
# Para cada SUCURSAL y MES, por tipo, el precio de cada lado = MEDIANA $/100 g de los productos de la lista que esa
# sucursal tuvo ese mes. Un tipo cuenta en esa sucursal-mes si tuvo >= 1 producto con TACC y >= 1 sin TACC: la brecha
# del tipo se calcula DENTRO del mismo super. El "más barato" (mínimo) se guarda solo como referencia ilustrativa
# (sesgado al alza porque el lado con TACC tiene más productos por sucursal; BRECHA_CELIACA §3.7).
# Los productos ADICIONALES (sensibilidad, CELDA 8c) se separan acá: siguen las mismas reglas (abajo) pero no entran en
# la brecha principal.
datos_adic = datos_dia[datos_dia['ean_norm'].isin(EANS_ADIC)].copy()
datos_dia['tipo'] = datos_dia['ean_norm'].map(EAN_TIPO)
datos_dia['rol']  = datos_dia['ean_norm'].map(EAN_ROL)
datos_dia = datos_dia[datos_dia['tipo'].notna() & ~datos_dia['id_comercio'].isin(CADENAS_FILTRAR)].copy()
# Vigencia de los códigos que cambiaron de EAN (CELDA 1): fuera de su ventana no se usan (precios congelados)
_VIG = {_norm_ean(k): v for k, v in globals().get('VIGENCIA', {}).items() if _norm_ean(k)}
if _VIG:
    _vd = datos_dia['ean_norm'].map({_e: _v[0] for _e, _v in _VIG.items()})
    _vh = datos_dia['ean_norm'].map({_e: _v[1] for _e, _v in _VIG.items()})
    _fuera = ((_vd.notna() & (datos_dia['mes'] < _vd.fillna(''))) |
              (_vh.notna() & (datos_dia['mes'] > _vh.fillna('9999-99'))))
    print(f'  Vigencia de códigos (CELDA 1): {int(_fuera.sum()):,} obs fuera de la ventana de su código, no se usan '
          f'({datos_dia.loc[_fuera, "ean_norm"].nunique()} códigos)')
    datos_dia = datos_dia[~_fuera].copy()
_ex = set(globals().get('EANS_EXCLUIR', set()))
if _ex:
    _n0e = len(datos_dia)
    datos_dia = datos_dia[~datos_dia['ean_norm'].isin(_ex)].copy()
    print(f'  Excluidos {len(_ex)} EANs a mano (EANS_EXCLUIR): {_n0e - len(datos_dia):,} obs')
datos_dia['grams'] = datos_dia['ean_norm'].map(EAN_GRAMS)
_n0 = len(datos_dia)
datos_dia = datos_dia[datos_dia['grams'].notna() & (datos_dia['grams'] > 0)].copy()
if _n0 - len(datos_dia):
    print(f'  Excluidas {_n0 - len(datos_dia):,} obs de EANs sin gramos (no normalizables a $/100 g)')
datos_dia['precio_100'] = datos_dia['precio'] / datos_dia['grams'] * 100

# ── Filtro de plausibilidad a nivel EAN (data-quality, §3.8) ──────────────────
# Regla SIMÉTRICA e INFLACIÓN-ROBUSTA: cada EAN se mide contra sus pares del mismo tipo, lado y MES (mediana de los
# precios-EAN, uno por producto). Se descarta el EAN si su precio relativo mediano cae fuera de [1/FACTOR_PLAUS,
# FACTOR_PLAUS]: errores de carga groseros, sin elegir a mano ni favorecer la dirección de la brecha.
_fp = globals().get('FACTOR_PLAUS', 4)
_eanm = datos_dia.groupby(['tipo','rol','mes','ean_norm'])['precio_100'].median().reset_index(name='_p')
_eanm['_ref'] = _eanm.groupby(['tipo','rol','mes'])['_p'].transform('median')
_eanm['_rel'] = _eanm['_p'] / _eanm['_ref']
_emr = _eanm.groupby('ean_norm')['_rel'].median()
_bad = set(_emr[(_emr < 1/_fp) | (_emr > _fp)].index)
plausibilidad = pd.DataFrame({'ean_norm': sorted(_bad)})
if _bad:
    plausibilidad['tipo'] = plausibilidad['ean_norm'].map(EAN_TIPO)
    plausibilidad['rol'] = plausibilidad['ean_norm'].map(EAN_ROL)
    plausibilidad['descripcion'] = plausibilidad['ean_norm'].map(EAN_DESC)
    plausibilidad['precio_relativo_mediano'] = plausibilidad['ean_norm'].map(_emr).round(3)
    _n0p = len(datos_dia)
    datos_dia = datos_dia[~datos_dia['ean_norm'].isin(_bad)].copy()
    print(f'  Filtro de plausibilidad (banda ×{_fp}): {len(_bad)} EAN(s) fuera → {_n0p - len(datos_dia):,} obs:')
    for _r in plausibilidad.itertuples(index=False):
        print(f'      - {_r.ean_norm}  rel={_r.precio_relativo_mediano:.2f}  {str(_r.descripcion)[:50]}')

# ── Precios de una EMPRESA fuera de escala (data-quality): para cada código y mes, la mediana de cada empresa contra la
# mediana entre empresas (una por empresa; solo con >= 3 empresas). Fuera de [1/FACTOR_EMPRESA, FACTOR_EMPRESA] se
# descartan esas observaciones: un código cargado a un tercio o al triple en toda una cadena (o de otra presentación).
# La mediana nacional no lo ve cuando esa cadena tiene la mayoría de las sucursales (DIA en sep-2026: su precio de las
# chips Smams ERA la mediana nacional). Las medianas de la descriptiva lo resisten; la TPD y la hedónica (mínimos
# cuadrados) no. Hoja Precios_atipicos.
def _atipicos_empresa(_d):
    _fe = globals().get('FACTOR_EMPRESA', 2.5)
    if not len(_d):
        return pd.DataFrame(columns=['ean_norm','mes','empresa','precio_100_empresa','relativo_a_las_empresas'])
    _ce = (_d.assign(empresa=_d['id_comercio'].map(asignar_empresa))
           .groupby(['ean_norm','mes','empresa'])['precio_100'].median().rename('precio_100_empresa').reset_index())
    _ce['_ne'] = _ce.groupby(['ean_norm','mes'])['empresa'].transform('size')
    _ce['relativo_a_las_empresas'] = _ce['precio_100_empresa'] / _ce.groupby(['ean_norm','mes'])['precio_100_empresa'].transform('median')
    return _ce[(_ce['_ne'] >= 3) & ((_ce['relativo_a_las_empresas'] > _fe) | (_ce['relativo_a_las_empresas'] < 1 / _fe))
               ].drop(columns='_ne').reset_index(drop=True)

def _sin_atipicos(_d, _at):
    if not len(_at) or not len(_d):
        return _d, 0
    _k = _d['ean_norm'] + '|' + _d['mes'] + '|' + _d['id_comercio'].map(asignar_empresa)
    _m = _k.isin(set(_at['ean_norm'] + '|' + _at['mes'] + '|' + _at['empresa']))
    return _d[~_m].copy(), int(_m.sum())

precios_atipicos = _atipicos_empresa(datos_dia)
datos_dia, _n_at = _sin_atipicos(datos_dia, precios_atipicos)
if len(precios_atipicos):
    precios_atipicos['descripcion'] = precios_atipicos['ean_norm'].map(EAN_DESC)
    precios_atipicos['tipo'] = precios_atipicos['ean_norm'].map(EAN_TIPO)
    print(f'  Precios de una empresa fuera de escala (×{FACTOR_EMPRESA} contra las demás empresas): '
          f'{len(precios_atipicos)} empresa-código-mes, {_n_at:,} obs fuera (hoja Precios_atipicos)')

# ── Precios CONGELADOS de una empresa (data-quality): la empresa repite el MISMO precio de un código mes tras mes
# mientras los demás suben. Con la inflación de 2022-2024 (hasta 25% por mes), un precio idéntico MESES_CONGELADO meses
# seguidos o más, con el índice de su tipo y lado (mediana entre empresa-códigos de la variación mensual, encadenada)
# arriba más de SUBA_CONGELADO desde que se fijó, no es un precio de góndola sino uno que la empresa dejó de actualizar en
# el SEPA: Deheza informó las galletas de arroz Crisppino al mismo precio de abr-2023 a jul-2024 (el índice subió 304%;
# en Carrefour pasaron de $350 a $1.700 los 100 g) y su brecha de snacks llegó a -80%. El filtro de precios fuera de
# escala no lo ve con menos de 3 empresas con ese código. Se descartan los meses de la racha con el índice arriba más de
# SUBA_CONGELADO (hoja Precios_congelados); las rachas cortas (un mes de rezago tras la devaluación de dic-2023) quedan.
def _congelados_empresa(_d, _ix=None):
    # _d: sucursal × código × mes con id_comercio, ean_norm, tipo, rol, mes y precio_100. Devuelve las rachas congeladas,
    # las claves 'empresa|código|mes' a descartar y el índice de cada tipo y lado (con _ix se usa ese, el de la canasta)
    _cols = ['empresa','ean_norm','tipo','rol','desde','hasta','meses_iguales','primer_mes_descartado','meses_descartados',
             'precio_100_empresa','suba_indice_pct']
    if not len(_d):
        return pd.DataFrame(columns=_cols), set(), _ix
    _e = (_d.assign(empresa=_d['id_comercio'].map(asignar_empresa))
          .groupby(['empresa','ean_norm','tipo','rol','mes'], as_index=False)['precio_100'].median()
          .sort_values(['empresa','ean_norm','mes']).reset_index(drop=True))
    if _ix is None:
        _ms = sorted(_e['mes'].unique())
        _e['_t'] = _e['mes'].map({_x: _i for _i, _x in enumerate(_ms)})
        _sig = (_e['empresa'].eq(_e['empresa'].shift()) & _e['ean_norm'].eq(_e['ean_norm'].shift())
                & _e['_t'].diff().eq(1))
        _e['_dl'] = np.log(_e['precio_100']).diff().where(_sig)
        _ix = (_e.groupby(['tipo','rol','_t'])['_dl'].median().unstack(['tipo','rol'])
               .reindex(range(len(_ms))).fillna(0).cumsum())
        _ix.index = _ms
    _pos_m = {_x: _i for _i, _x in enumerate(_ix.index)}
    _filas, _fuera = [], set()
    for (_em, _ea, _tp, _rl), _g in _e.groupby(['empresa','ean_norm','tipo','rol']):
        if (_tp, _rl) not in _ix.columns or len(_g) < MESES_CONGELADO:
            continue
        _mm = _g['mes'].to_numpy(); _lp = np.log(_g['precio_100'].to_numpy())
        _ps = np.array([_pos_m.get(_x, -10) for _x in _mm])
        _rf = _ix[(_tp, _rl)].to_numpy()
        _i = 0
        while _i < len(_mm):
            _j = _i
            while _j + 1 < len(_mm) and _ps[_j + 1] == _ps[_j] + 1 and abs(_lp[_j + 1] - _lp[_i]) < 0.005:
                _j += 1
            if _j - _i + 1 >= MESES_CONGELADO and _ps[_i] >= 0:
                _su = np.expm1(_rf[_ps[_i:_j + 1]] - _rf[_ps[_i]])
                _k = np.where(_su > SUBA_CONGELADO)[0]
                if len(_k):
                    _fuera |= {f'{_em}|{_ea}|{_x}' for _x in _mm[_i:_j + 1][_k]}
                    _filas.append({'empresa': _em, 'ean_norm': _ea, 'tipo': _tp, 'rol': _rl, 'desde': _mm[_i],
                                   'hasta': _mm[_j], 'meses_iguales': _j - _i + 1,
                                   'primer_mes_descartado': _mm[_i:_j + 1][_k[0]], 'meses_descartados': len(_k),
                                   'precio_100_empresa': float(np.exp(_lp[_i])), 'suba_indice_pct': 100 * float(_su[-1])})
            _i = _j + 1
    return pd.DataFrame(_filas, columns=_cols), _fuera, _ix

def _sin_congelados(_d, _fuera):
    if not _fuera or not len(_d):
        return _d, 0
    _m = (_d['id_comercio'].map(asignar_empresa) + '|' + _d['ean_norm'] + '|' + _d['mes']).isin(_fuera)
    return _d[~_m].copy(), int(_m.sum())

precios_congelados, _fuera_cg, _IX_CG = _congelados_empresa(datos_dia)
datos_dia, _n_cg = _sin_congelados(datos_dia, _fuera_cg)
precios_congelados.insert(2, 'descripcion', precios_congelados['ean_norm'].map(EAN_DESC))
if len(precios_congelados):
    print(f'  Precios congelados de una empresa (el mismo precio {MESES_CONGELADO}+ meses con el índice de su tipo y lado '
          f'arriba más de {100 * SUBA_CONGELADO:.0f}%): {len(precios_congelados)} rachas, {len(_fuera_cg)} empresa-código-mes, '
          f'{_n_cg:,} obs fuera (hoja Precios_congelados)')

# ── Productos ADICIONALES (CELDA 8c): mismas reglas que la canasta (cadenas fuera del universo, vigencia, EANS_EXCLUIR,
# gramos y plausibilidad contra los productos de la canasta del mismo tipo, lado y mes) ──
if len(datos_adic):
    _ai = lambda _k: datos_adic['ean_norm'].map({_e: _v.get(_k) for _e, _v in ADIC_INFO.items()})
    datos_adic['tipo'], datos_adic['subtipo'] = _ai('tipo'), _ai('subtipo')
    datos_adic['rol'] = _ai('lado').map({'tacc': 'tacc', 'sin_tacc': 'sin'})
    datos_adic['grams'] = pd.to_numeric(_ai('gramos'), errors='coerce')
    datos_adic['producto_todos'] = _ai('linea_todos').fillna(datos_adic['ean_norm'])
    _vd, _vh = _ai('desde'), _ai('hasta')
    _fuera_a = ((_vd.notna() & (datos_adic['mes'] < _vd.fillna(''))) | (_vh.notna() & (datos_adic['mes'] > _vh.fillna('9999-99'))))
    datos_adic = datos_adic[~_fuera_a & ~datos_adic['id_comercio'].isin(CADENAS_FILTRAR) & ~datos_adic['ean_norm'].isin(_ex)
                            & datos_adic['tipo'].isin(set(TIPO_TACC)) & (datos_adic['grams'] > 0)].copy()
    datos_adic['precio_100'] = datos_adic['precio'] / datos_adic['grams'] * 100
    _ref_a = _eanm.groupby(['tipo','rol','mes'])['_ref'].first().rename('_ref')
    _ea = (datos_adic.groupby(['tipo','rol','mes','ean_norm'])['precio_100'].median().rename('_p').reset_index()
           .join(_ref_a, on=['tipo','rol','mes']))
    _ear = (_ea['_p'] / _ea['_ref']).groupby(_ea['ean_norm']).median()
    _bad_a = set(_ear[(_ear < 1/_fp) | (_ear > _fp)].index)
    datos_adic = datos_adic[~datos_adic['ean_norm'].isin(_bad_a)].copy()
    datos_adic, _ = _sin_atipicos(datos_adic, _atipicos_empresa(datos_adic))
    datos_adic, _ = _sin_congelados(datos_adic, _congelados_empresa(datos_adic, _IX_CG)[1])
    print(f'  Productos adicionales (sensibilidad, CELDA 8c): {datos_adic["ean_norm"].nunique()} códigos con datos, '
          f'{len(datos_adic):,} obs' + (f'; fuera por plausibilidad: {sorted(_bad_a)}' if _bad_a else ''))

# ── Control de identidad de cada EAN (diagnóstico, no excluye) ────────────────
# Precio $/100 g de cada EAN relativo a la mediana del lado CON TACC de su tipo, mes por mes. Un código reutilizado
# para otro producto o una presentación mal cargada se ve como un salto del relativo: se marca 'revisar' si el
# relativo de sus últimos 12 meses difiere en más del doble del de sus primeros 12, o si salta x2 de un mes al otro.
_rt = (datos_dia[datos_dia['rol'] == 'tacc'].groupby(['tipo','mes','ean_norm'])['precio_100'].median()
       .groupby(level=['tipo','mes']).median().rename('_ref_tacc'))
_ce = (datos_dia.groupby(['tipo','rol','mes','ean_norm'])
       .agg(_p=('precio_100', 'median'), _n=('id_sucursal', 'size')).reset_index()
       .merge(_rt.reset_index(), on=['tipo','mes'], how='left'))
_ce['_rel'] = _ce['_p'] / _ce['_ref_tacc']
_rows_ce = []
for (_t, _r, _e), _g in _ce.sort_values('mes').groupby(['tipo','rol','ean_norm']):
    _v = _g['_rel'].to_numpy()
    _ini, _fin = np.nanmedian(_v[:12]), np.nanmedian(_v[-12:])
    _lr = np.abs(np.diff(np.log(_v[np.isfinite(_v) & (_v > 0)]))) if len(_v) > 1 else np.array([])
    _rows_ce.append({'tipo': _t, 'rol': _r, 'ean_norm': _e, 'descripcion': EAN_DESC.get(_e),
                     'gramos': EAN_GRAMS.get(_e), 'meses_con_precio': len(_g), 'primer_mes': _g['mes'].iloc[0],
                     'ultimo_mes': _g['mes'].iloc[-1], 'sucursales_mes_mediana': float(_g['_n'].median()),
                     'precio_100g_ultimo_mes': float(_g['_p'].iloc[-1]),
                     'relativo_al_lado_con_tacc': float(np.nanmedian(_v)), 'relativo_primeros_12': float(_ini),
                     'relativo_ultimos_12': float(_fin), 'cambio_ultimos_sobre_primeros': float(_fin / _ini),
                     'saltos_x2_mes_a_mes': int((_lr > np.log(2)).sum())})
control_ean = pd.DataFrame(_rows_ce)
if len(control_ean):
    control_ean['revisar'] = (~control_ean['cambio_ultimos_sobre_primeros'].between(0.5, 2)) | (control_ean['saltos_x2_mes_a_mes'] > 0)
    _rv = control_ean[control_ean['revisar']]
    print(f'  Control de identidad: {len(_rv)} EAN(s) para revisar (cambio de nivel x2 o salto x2 mes a mes; no se excluyen):')
    for _r in _rv.itertuples(index=False):
        print(f'      - [{_r.tipo} / {_r.rol}] {_r.ean_norm} {str(_r.descripcion)[:40]}: relativo {_r.relativo_primeros_12:.2f} '
              f'→ {_r.relativo_ultimos_12:.2f}, saltos x2: {_r.saltos_x2_mes_a_mes}')

# Precio de cada SUBTIPO por (sucursal, mes, lado): MEDIANA $/100 g de los productos presentes (estimador PRIMARIO,
# §3.3 y §14). La comparación es por subtipo (crackers con crackers, snacks con snacks, spaghetti con spaghetti): la
# mediana del tipo entero mezclaba subtipos de niveles muy distintos según qué tuviera cada sucursal (en las saladas,
# snacks con TACC de $2.000/100 g contra crackers sin TACC). Un producto con dos códigos o una línea con varios sabores
# (PRODUCTO, CELDA 1) entra con la mediana de sus códigos: cuenta una vez. El "más barato" (ilustrativo) es el mínimo
# de los productos a menos de x4 de la mediana del grupo (siempre hay al menos uno), vectorizado: una función de Python
# por grupo tardaba minutos.
_sk = ['id_comercio','id_bandera','id_sucursal']
_PROD = {_norm_ean(_e): _p for _p, _es in globals().get('PRODUCTO', {}).items() for _e in _es if _norm_ean(_e)}
datos_dia['producto'] = datos_dia['ean_norm'].map(_PROD).fillna(datos_dia['ean_norm'])
datos_dia['subtipo'] = datos_dia['ean_norm'].map(EAN_SUBTIPO)
_pp = datos_dia.groupby(_sk + ['mes','tipo','subtipo','rol','producto'], as_index=False)['precio_100'].median()
_gtp = _sk + ['mes','tipo','subtipo','rol']
_mg = _pp.groupby(_gtp)['precio_100'].transform('median')
_pp['_banda'] = _pp['precio_100'].where((_pp['precio_100'] >= _mg / 4) & (_pp['precio_100'] <= _mg * 4))
tp = (_pp.groupby(_gtp).agg(precio_rep=('precio_100', 'median'), precio_min=('_banda', 'min'),
                             n_items=('precio_100', 'size')).reset_index())
del _pp, _mg

# ── Geografía: provincia por polígonos de ar.json con tolerancia (BUG-44), AMBA por coordenadas (BUG-42), región ──
# Una sucursal cambia de provincia SOLO si cae a más de RECLASIF_TOL_KM del polígono de su provincia declarada y dentro
# del polígono de otra (errores groseros de carga); cerca de un borde manda la declarada. Hasta 2026-10 el nb06 usaba
# rectángulos (pasaban Neuquén capital a La Pampa, Paraná a Santa Fe y San Nicolás a Entre Ríos). Sin ar.json no se
# reclasifica. Se sacan las sucursales 'Web' y las de CABA con coordenadas fuera de CABA (como el nb02).
from matplotlib.path import Path as _MPath
_GEO_ID_PROV = {'ARB': 'Buenos Aires', 'ARC': 'CABA', 'ARK': 'Catamarca', 'ARH': 'Chaco', 'ARU': 'Chubut',
                'ARX': 'Córdoba', 'ARW': 'Corrientes', 'ARE': 'Entre Ríos', 'ARP': 'Formosa', 'ARY': 'Jujuy',
                'ARL': 'La Pampa', 'ARF': 'La Rioja', 'ARM': 'Mendoza', 'ARN': 'Misiones', 'ARQ': 'Neuquén',
                'ARR': 'Río Negro', 'ARA': 'Salta', 'ARJ': 'San Juan', 'ARD': 'San Luis', 'ARZ': 'Santa Cruz',
                'ARS': 'Santa Fe', 'ARG': 'Santiago del Estero', 'ARV': 'Tierra del Fuego', 'ART': 'Tucumán'}

def _poligonos_provincias(_ruta):
    # provincia -> lista de polígonos; cada polígono, lista de anillos [lon, lat] (el primero es el exterior)
    with open(_ruta, 'r', encoding='utf-8') as _f:
        _g = _json.load(_f)
    _pol = {}
    for _ft in _g['features']:
        _prov = _GEO_ID_PROV.get(_ft['properties'].get('id'))
        if _prov is None:
            continue
        _geo = _ft['geometry']
        _ps = _geo['coordinates'] if _geo['type'] == 'MultiPolygon' else [_geo['coordinates']]
        _pol.setdefault(_prov, []).extend([[np.asarray(_r, dtype=float) for _r in _p] for _p in _ps])
    return _pol

def _dentro_poligono(_pols, _lon, _lat):
    _pts = np.column_stack([_lon, _lat])
    _res = np.zeros(len(_pts), bool)
    for _p in _pols:
        _en = _MPath(_p[0]).contains_points(_pts)
        for _h in _p[1:]:
            _en &= ~_MPath(_h).contains_points(_pts)
        _res |= _en
    return _res

def _km_al_poligono(_pols, _lon, _lat):
    # Distancia (km) de cada punto al borde más cercano de los polígonos (proyección equirectangular local)
    _segs = np.concatenate([np.column_stack([_r[:-1], _r[1:]]) for _p in _pols for _r in _p])
    _out = np.empty(len(_lon))
    for _i, (_x, _y) in enumerate(zip(_lon, _lat)):
        _kx = 111.32 * np.cos(np.radians(_y))
        _x1, _y1 = (_segs[:, 0] - _x) * _kx, (_segs[:, 1] - _y) * 110.57
        _x2, _y2 = (_segs[:, 2] - _x) * _kx, (_segs[:, 3] - _y) * 110.57
        _dx, _dy = _x2 - _x1, _y2 - _y1
        _t = np.clip(-(_x1 * _dx + _y1 * _dy) / np.maximum(_dx * _dx + _dy * _dy, 1e-12), 0, 1)
        _out[_i] = np.sqrt((_x1 + _t * _dx) ** 2 + (_y1 + _t * _dy) ** 2).min()
    return _out

_OBELISCO = (-34.6037, -58.3816)
def _km_obelisco(lat, lon):
    _la, _lo = np.radians(lat), np.radians(lon)
    _la0, _lo0 = np.radians(_OBELISCO[0]), np.radians(_OBELISCO[1])
    _a = np.sin((_la - _la0) / 2) ** 2 + np.cos(_la0) * np.cos(_la) * np.sin((_lo - _lo0) / 2) ** 2
    return 2 * 6371 * np.arcsin(np.sqrt(_a))

_cols_suc = ['id_comercio','id_bandera','id_sucursal','sucursales_nombre','sucursales_latitud','sucursales_longitud',
             'sucursales_localidad','PROVINCIA'] + (['sucursales_tipo'] if 'sucursales_tipo' in suc_pais.columns else [])
suc_geo = suc_pais[_cols_suc].copy()
suc_geo['cadena'] = suc_geo.apply(asignar_cadena, axis=1)
suc_geo['empresa'] = suc_geo['id_comercio'].map(asignar_empresa)
# afuera las sucursales que no son locales: tipo web o virtual y, por el nombre, las que el maestro carga con tipo
# Supermercado o Autoservicio (SUCURSALES_NO_FISICAS de la CELDA 1, BUG-48)
_web = (suc_geo['sucursales_tipo'].astype(str).str.lower().str.contains('web|virtual')
        if 'sucursales_tipo' in suc_geo.columns else pd.Series(False, index=suc_geo.index))
_nom = suc_geo['sucursales_nombre'].astype(str).str.contains(SUCURSALES_NO_FISICAS, case=False, regex=True) & ~_web
_lista = ', '.join(f'{_c} "{_n}"' for _c, _n in suc_geo.loc[_nom, ['cadena','sucursales_nombre']].itertuples(index=False))
print(f'  Sucursales que no son locales, afuera: {int(_web.sum())} de tipo web o virtual y {int(_nom.sum())} por el '
      f'nombre{": " + _lista if _lista else ""}')
suc_geo = suc_geo[~(_web | _nom)].copy()
suc_geo['PROVINCIA_NORM'] = suc_geo['PROVINCIA'].map(PROV_NORM).fillna(suc_geo['PROVINCIA'])
_mask_caba = (suc_geo['PROVINCIA_NORM'].eq('CABA') & (
    (suc_geo['sucursales_latitud'] < -34.71) | (suc_geo['sucursales_latitud'] > -34.53) |
    (suc_geo['sucursales_longitud'] < -58.53) | (suc_geo['sucursales_longitud'] > -58.34)))
suc_geo = suc_geo[~_mask_caba].copy()
_POL_PROV = _poligonos_provincias(GEOJSON_PATH) if GEOJSON_PATH.exists() else {}
if not _POL_PROV:
    print(f'  AVISO: no está {GEOJSON_PATH.name}: no se reclasifica la provincia de ninguna sucursal')
_lon = suc_geo['sucursales_longitud'].to_numpy(dtype=float)
_lat = suc_geo['sucursales_latitud'].to_numpy(dtype=float)
_decl = suc_geo['PROVINCIA_NORM'].to_numpy(dtype=object)
_dentro_de = {_p: _dentro_poligono(_pl, _lon, _lat) for _p, _pl in _POL_PROV.items()}
_nueva = _decl.copy()
for _p in sorted((set(_decl) & set(_POL_PROV)) - {'CABA'}):
    _idx = np.where((_decl == _p) & ~_dentro_de[_p])[0]
    if len(_idx) == 0:
        continue
    _lejos = _idx[_km_al_poligono(_POL_PROV[_p], _lon[_idx], _lat[_idx]) > RECLASIF_TOL_KM]
    for _i in _lejos:
        _q = next((_o for _o in _POL_PROV if _o != _p and _dentro_de[_o][_i]), None)
        if _q is not None:
            _nueva[_i] = _q
_cambio = _nueva != _decl
suc_geo['PROVINCIA_NORM'] = _nueva
if _cambio.any():
    _det = pd.Series([f'{_a} -> {_b}' for _a, _b in zip(_decl[_cambio], _nueva[_cambio])]).value_counts()
    print(f'  Reclasificadas {int(_cambio.sum())} sucursales por coordenadas (a más de {RECLASIF_TOL_KM} km de su '
          f'provincia declarada): ' + ', '.join(f'{_k} ({_v})' for _k, _v in _det.items()))
suc_geo['amba'] = (suc_geo['PROVINCIA_NORM'].eq('CABA') |
                   (suc_geo['PROVINCIA_NORM'].eq('Buenos Aires') &
                    (_km_obelisco(suc_geo['sucursales_latitud'], suc_geo['sucursales_longitud']) <= AMBA_RADIO_KM)))
suc_geo['region'] = np.where(suc_geo['amba'], 'AMBA', suc_geo['PROVINCIA_NORM'].map(REGION_PROV).fillna('Sin región'))
print(f'  AMBA (CABA + Buenos Aires a <= {AMBA_RADIO_KM} km del Obelisco): {int(suc_geo["amba"].sum()):,} sucursales')

# ── Departamento de cada sucursal (Georef de datos.gob.ar, por coordenadas) para la concentración (CELDA 8): la caché
# del nb09 y la propia (_cache/georef_sucursales.parquet); con USAR_GEOREF se consultan las sucursales que falten. La
# localidad del maestro no sirve como mercado: DIA la carga con el nombre de la provincia ("CAPITAL FEDERAL") ──
suc_geo = suc_geo.drop_duplicates(['id_comercio','id_bandera','id_sucursal']).copy()
suc_geo['suc_key'] = suc_geo['id_comercio'] + '|' + suc_geo['id_bandera'] + '|' + suc_geo['id_sucursal']
_GR_COLS = ['suc','departamento_id','departamento','municipio']
_gr_propia = CACHE_DIR / 'georef_sucursales.parquet'
_gr = [pd.read_parquet(_p)[_GR_COLS] for _p in (Path(GEOREF_PATH), _gr_propia) if _p.exists()]
_gr = (pd.concat(_gr, ignore_index=True).drop_duplicates('suc', keep='last') if _gr
       else pd.DataFrame(columns=_GR_COLS))
_pend = suc_geo[~suc_geo['suc_key'].isin(set(_gr['suc']))]
if USAR_GEOREF and len(_pend):
    import urllib.request, time as _time
    print(f'  Georef: consultando {len(_pend):,} sucursales...')
    _filas = []
    for _i in range(0, len(_pend), 500):
        _b = _pend.iloc[_i:_i + 500]
        _body = _json.dumps({'ubicaciones': [{'lat': float(_la), 'lon': float(_lo), 'aplanar': True,
                                              'campos': 'departamento.id,departamento.nombre,municipio.nombre'}
                                             for _la, _lo in zip(_b['sucursales_latitud'], _b['sucursales_longitud'])]}).encode()
        try:
            _req = urllib.request.Request('https://apis.datos.gob.ar/georef/api/ubicacion', data=_body,
                                          headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(_req, timeout=120) as _r:
                _res = _json.loads(_r.read())['resultados']
        except Exception as _e:
            print(f'  AVISO: Georef no respondió ({_e}): las sucursales que faltan quedan sin departamento')
            break
        for _k, _x in zip(_b['suc_key'], _res):
            _u = _x.get('ubicacion') or {}
            _filas.append({'suc': _k, 'departamento_id': _u.get('departamento_id'),
                           'departamento': _u.get('departamento_nombre'), 'municipio': _u.get('municipio_nombre')})
        _time.sleep(0.5)
    if _filas:
        _gr = pd.concat([_gr, pd.DataFrame(_filas)], ignore_index=True).drop_duplicates('suc', keep='last')
        if USE_CACHE:
            _gr.to_parquet(_gr_propia, index=False)
suc_geo = suc_geo.merge(_gr.rename(columns={'suc': 'suc_key'}), on='suc_key', how='left')
print(f'  Departamento (Georef): {int(suc_geo["departamento_id"].notna().sum()):,} de {len(suc_geo):,} sucursales')

_GEO = ['cadena','empresa','PROVINCIA_NORM','region','amba','sucursales_localidad','sucursales_nombre']
tp = tp.merge(suc_geo[_sk + _GEO], on=_sk, how='inner')
tp['localidad'] = (tp['sucursales_localidad'].astype(str).str.strip()
                   .replace({'':'N/D','nan':'N/D','None':'N/D'}))

# ── DIAGNÓSTICO de cobertura por tipo (todo el período) ──────────────────────
_cob_rows = []
print('=== Cobertura por tipo (sucursales que ofrecen cada lado, todo el período) ===')
for _t in TIPO_TACC:
    _st = tp[tp['tipo'] == _t]
    _set_t = set(map(tuple, _st[_st['rol']=='tacc'][_sk].drop_duplicates().to_numpy()))
    _set_s = set(map(tuple, _st[_st['rol']=='sin'][_sk].drop_duplicates().to_numpy()))
    _both  = _set_t & _set_s
    print(f'  [{_t}] con TACC: {len(_set_t):>5} · sin TACC: {len(_set_s):>5} · con LOS DOS: {len(_both):>5}')
    _cob_rows.append({'tipo':_t,'sucursales_tacc':len(_set_t),'sucursales_sin_tacc':len(_set_s),'sucursales_ambos':len(_both)})
cobertura_tipo = pd.DataFrame(_cob_rows)

# ── ATÓMICO: brecha por (sucursal, mes, tipo, subtipo) con LOS DOS lados en ese super-mes; la del TIPO en la
# sucursal-mes = promedio geométrico de las de sus subtipos con los dos lados (pesos iguales): sus precios con y sin
# TACC son los promedios geométricos de las medianas de esos subtipos, así que sin / tacc - 1 es esa brecha ─
_idx = _sk + ['mes','PROVINCIA_NORM','region','amba','cadena','empresa','localidad','sucursales_nombre','tipo']
_tacc = tp[tp['rol']=='tacc'][_idx + ['subtipo','precio_rep','precio_min','n_items']].rename(
    columns={'precio_rep':'tacc','precio_min':'tacc_min','n_items':'n_tacc'})
_sin  = tp[tp['rol']=='sin'][_idx + ['subtipo','precio_rep','precio_min','n_items']].rename(
    columns={'precio_rep':'sin','precio_min':'sin_min','n_items':'n_sin'})
bt_sub = _tacc.merge(_sin, on=_idx + ['subtipo'], how='inner')
bt_sub['brecha_pct'] = (bt_sub['sin'] / bt_sub['tacc'] - 1) * 100
bt_sub['brecha_min'] = (bt_sub['sin_min'] / bt_sub['tacc_min'] - 1) * 100
bt_sub['anio'] = bt_sub['mes'].str[:4]
bt_sub['suc_key'] = bt_sub['id_comercio'] + '|' + bt_sub['id_bandera'] + '|' + bt_sub['id_sucursal']
_lg = ['tacc', 'sin', 'tacc_min', 'sin_min']
bt_sm = (bt_sub.assign(**{f'_l_{_c}': np.log(bt_sub[_c]) for _c in _lg})
         .groupby(_idx, dropna=False)
         .agg(**{f'_l_{_c}': (f'_l_{_c}', 'mean') for _c in _lg},
              n_tacc=('n_tacc', 'sum'), n_sin=('n_sin', 'sum'), n_subtipos=('subtipo', 'size'))
         .reset_index())
for _c in _lg:
    bt_sm[_c] = np.exp(bt_sm.pop(f'_l_{_c}'))
bt_sm['brecha_pct'] = (bt_sm['sin'] / bt_sm['tacc'] - 1) * 100          # PRIMARIO: medianas por subtipo (§3.4, §14)
bt_sm['brecha_min'] = (bt_sm['sin_min'] / bt_sm['tacc_min'] - 1) * 100  # ilustrativo "más barato" (§3.7)
bt_sm['anio'] = bt_sm['mes'].str[:4]
bt_sm['suc_key'] = bt_sm['id_comercio'] + '|' + bt_sm['id_bandera'] + '|' + bt_sm['id_sucursal']

cobertura_mensual = (bt_sm.groupby(['tipo','mes'])
                     .agg(sucursales_ambos=('id_sucursal','size'), productos_tacc_prom=('n_tacc','mean'),
                          productos_sin_prom=('n_sin','mean')).reset_index()
                     .pivot_table(index='mes', columns='tipo', values='sucursales_ambos').reset_index())

# ── Ponderación ENGHo ─────────────────────────────────────────────────────────
# Brecha de la canasta = sum_k w_k (1 + g_k) - 1, con w_k = peso ENGHo del tipo renormalizado entre los tipos presentes
# y g_k la brecha del tipo (mediana entre sucursales). Para la canasta POR SUCURSAL (mapa, Brecha_sucursal) se usan
# cantidades fijas qty_k = w_k / (precio con TACC de k en el año base): con los precios del año base, el gasto con
# TACC se reparte como la ENGHo.
_meses_bt = sorted(bt_sm['mes'].unique())
if ANIO_BASE_PONDERACION:
    _mb = [m for m in _meses_bt if m.startswith(str(ANIO_BASE_PONDERACION))]
else:
    _mb = _meses_bt[:12]
_pb = bt_sm[bt_sm['mes'].isin(_mb)].groupby('tipo')['tacc'].median()
if PONDERACION == 'engho':
    _sin_peso = [t for t in TIPO_TACC if not (TIPO_PESO.get(t, float('nan')) > 0)]
    if _sin_peso:
        raise ValueError(f'PONDERACION = "engho" pero estos tipos no tienen peso en TIPOS: {_sin_peso}')
    W_TIPO = {t: TIPO_PESO[t] for t in TIPO_TACC}
    TIPO_QTY = {t: W_TIPO[t] / _pb[t] for t in TIPO_TACC if t in _pb.index}
else:
    W_TIPO = {t: TIPO_QTY[t] * _pb.get(t, float('nan')) for t in TIPO_TACC}
_sw = sum(v for v in W_TIPO.values() if v == v)
W_TIPO = {t: v / _sw for t, v in W_TIPO.items() if v == v}
ponderaciones = pd.DataFrame({'tipo': list(W_TIPO),
                              'pct_gasto_alimentos_engho': [TIPO_PESO.get(t) for t in W_TIPO],
                              'peso_en_la_canasta_pct': [100 * W_TIPO[t] for t in W_TIPO],
                              'precio_con_tacc_100g_base': [_pb.get(t) for t in W_TIPO],
                              'cantidad_100g_canasta_sucursal': [TIPO_QTY.get(t) for t in W_TIPO]})
print(f'\nPonderación ({PONDERACION}), año base {_mb[0]} → {_mb[-1]}:')
print(ponderaciones.to_string(index=False, float_format=lambda _x: f'{_x:,.4g}'))

# ── Canasta por (sucursal, mes): suma sobre los tipos con los dos lados (mapa y Brecha_sucursal) ─
bt_sm['qty'] = bt_sm['tipo'].map(TIPO_QTY)
bt_sm['base_c'] = bt_sm['tacc'] * bt_sm['qty']
bt_sm['cel_c']  = bt_sm['sin']  * bt_sm['qty']
_gk = _sk + ['mes','PROVINCIA_NORM','region','cadena','empresa','localidad']
if len(bt_sm):
    brecha_suc_mes = (bt_sm.groupby(_gk).agg(base=('base_c','sum'), celiaca=('cel_c','sum'),
                                             n_tipos=('tipo','nunique')).reset_index())
    brecha_suc_mes = brecha_suc_mes[brecha_suc_mes['n_tipos'] >= MIN_TIPOS].copy()
    brecha_suc_mes['brecha_pct'] = (brecha_suc_mes['celiaca'] / brecha_suc_mes['base'] - 1) * 100
    brecha_suc_mes['suc_key'] = (brecha_suc_mes['id_comercio'] + '|' + brecha_suc_mes['id_bandera'] + '|'
                                 + brecha_suc_mes['id_sucursal'])
else:
    brecha_suc_mes = pd.DataFrame(columns=_gk + ['base','celiaca','n_tipos','brecha_pct','suc_key'])

_nsuc_bt = bt_sm[_sk].drop_duplicates().shape[0] if len(bt_sm) else 0
print(f'\nObs (sucursal×mes×tipo) con los dos lados: {len(bt_sm):,} | sucursales con >= 1 par: {_nsuc_bt:,}')
print(f'Canasta por sucursal-mes (>= {MIN_TIPOS} tipos): {len(brecha_suc_mes):,} obs')"""))

# ── CELL 8 — AGREGACIONES ──────────────────────────────────────────────────────
cells.append(cell_code(r"""# ============================================================
# CELDA 8 — Brecha por tipo y de la canasta: tiempo, geografía y cadenas
# ============================================================
# Todo sale de bt_sub (brecha por sucursal × mes × SUBTIPO), como un índice de precios: (1) por subtipo, mediana ENTRE
# sucursales de su brecha; (2) brecha del tipo = promedio geométrico de las de sus subtipos (pesos iguales, entre los
# presentes en el grupo con >= MIN_SUC_SUBTIPO sucursales: la mediana de menos es ruido); (3) canasta de un grupo =
# sum_k w_k (1 + brecha del tipo k) - 1 (pesos ENGHo; en los grupos con ref_keys están todos los tipos). Así la serie no la
# mueve qué subtipos o tipos tiene cada sucursal cada mes (la mediana entre sucursales de la brecha del tipo de cada
# una tenía 2-3 veces más ruido mes a mes). 'confiable' (series) = están todos los tipos y cada uno con >= MIN_SUC_AGG
# sucursales. Provincias, regiones, empresas y cadenas se comparan con la MISMA canasta de subtipos (ref_keys, abajo).
def _agg_tipo(df, keys, ref_keys=None, detalle=None):
    # ref_keys (grupos: provincia, región, empresa, cadena): canasta FIJA de subtipos. El subtipo con menos de
    # MIN_SUC_SUBTIPO sucursales en el grupo toma la brecha NACIONAL del mismo período (ref_keys = [] o ['anio']), como
    # una celda que falta en un índice de precios: sin esto, un grupo sin snacks quedaba con la brecha de los crackers
    # sola (+165%) y una cadena sin obleas ni pepas, con otra composición de galletitas dulces. detalle: lista donde se
    # agrega la tabla por subtipo (con _imp = 1 en los subtipos imputados).
    _cols = keys + ['tipo','tacc_100','sin_100','brecha_mediana','brecha_prom','brecha_min_ilustr','n_subtipos',
                    'n_subtipos_imputados','n_sucursales','n_obs']
    if len(df) == 0:
        return pd.DataFrame(columns=_cols)
    _mensual = keys == ['mes']
    _grupos = ref_keys is not None and not _mensual
    _meses_all = sorted(df['mes'].unique()) if _mensual else []
    _n = df.groupby(keys + ['tipo','subtipo'])['suc_key'].nunique().rename('n_suc').reset_index()
    _ok = _n['n_suc'] >= globals().get('MIN_SUC_SUBTIPO', 1)
    if _mensual:
        # serie mensual: subtipo-mes con menos de FRAC_SUBTIPO_MES de sus sucursales habituales = faltante
        _ok &= _n['n_suc'] >= (globals().get('FRAC_SUBTIPO_MES', 0)
                               * _n.groupby(['tipo','subtipo'])['n_suc'].transform('median'))
    _L = ['_lt','_ls','_lb','_lbp','_lbm']
    def _medianas(_d, _k):
        _x = (_d.groupby(_k + ['tipo','subtipo'])
              .agg(tacc=('tacc','median'), sin=('sin','median'), b=('brecha_pct','median'), bp=('brecha_pct', _pmean),
                   bm=('brecha_min','median'), n_obs=('brecha_pct','size')).reset_index())
        return _x.assign(_lt=np.log(_x['tacc']), _ls=np.log(_x['sin']), _lb=np.log1p(_x['b'] / 100),
                         _lbp=np.log1p(_x['bp'] / 100), _lbm=np.log1p(_x['bm'] / 100), _imp=0)
    _ref = _medianas(df, ref_keys) if _grupos else None    # el país (o el país en ese año), con todas las sucursales
    df = df.merge(_n.loc[_ok, keys + ['tipo','subtipo']], on=keys + ['tipo','subtipo'], how='inner')
    if len(df) == 0 and not _grupos:
        return pd.DataFrame(columns=_cols)
    _s = _medianas(df, keys)
    if _mensual:
        # el subtipo-mes faltante se imputa con su último mes válido (como un índice de precios con un ítem que falta
        # temporalmente): la composición de subtipos del tipo no cambia de un mes a otro
        _grid = _s[['tipo','subtipo']].drop_duplicates().merge(pd.DataFrame({'mes': _meses_all}), how='cross')
        _s = _grid.merge(_s, on=['mes','tipo','subtipo'], how='left').sort_values(['tipo','subtipo','mes'])
        _falta = _s['_lb'].isna()
        _s[_L] = _s.groupby(['tipo','subtipo'])[_L].ffill()
        _s['_imp'] = (_falta & _s['_lb'].notna()).astype(int)
        _s['n_obs'] = _s['n_obs'].fillna(0)
        _s = _s[_s['_lb'].notna()]
    elif _grupos:
        _gs = _n[keys].drop_duplicates()
        _grid = (_gs.merge(_ref[ref_keys + ['tipo','subtipo']], on=ref_keys, how='inner') if ref_keys
                 else _gs.merge(_ref[['tipo','subtipo']], how='cross'))
        _rf = _ref[ref_keys + ['tipo','subtipo'] + _L].rename(columns={_c: _c + '_ref' for _c in _L})
        _s = (_grid.merge(_s, on=keys + ['tipo','subtipo'], how='left')
              .merge(_rf, on=ref_keys + ['tipo','subtipo'], how='left'))
        _falta = _s['_lb'].isna()
        for _c in _L:
            _s[_c] = _s[_c].fillna(_s.pop(_c + '_ref'))
        _s['_imp'] = _falta.astype(int)
        _s['n_obs'] = _s['n_obs'].fillna(0)
    if detalle is not None:
        detalle.append(_s.merge(_n[keys + ['tipo','subtipo','n_suc']], on=keys + ['tipo','subtipo'], how='left')
                       .assign(brecha=lambda _x: np.expm1(_x['_lb']) * 100)
                       [keys + ['tipo','subtipo','brecha','n_suc','_imp']])
    _o = (_s.groupby(keys + ['tipo'])
          .agg(_lt=('_lt','mean'), _ls=('_ls','mean'), _lb=('_lb','mean'), _lbp=('_lbp','mean'), _lbm=('_lbm','mean'),
               n_subtipos=('subtipo','size'), n_subtipos_imputados=('_imp','sum'), n_obs=('n_obs','sum'))
          .reset_index())
    _o['tacc_100'] = np.exp(_o['_lt'])
    _o['sin_100'] = np.exp(_o['_ls'])
    _o['brecha_mediana'] = np.expm1(_o['_lb']) * 100
    _o['brecha_prom'] = np.expm1(_o['_lbp']) * 100
    _o['brecha_min_ilustr'] = np.expm1(_o['_lbm']) * 100
    _o = _o.merge(df.groupby(keys + ['tipo'])['suc_key'].nunique().rename('n_sucursales').reset_index(),
                  on=keys + ['tipo'], how='left')
    if _grupos:
        _o['n_sucursales'] = _o['n_sucursales'].fillna(0).astype(int)
    return _o[_cols]

TIPOS_ORD = [t for t in TIPO_TACC]
def _canasta(df, keys, ref_keys=None, detalle=None):
    # tabla ancha: por grupo, brecha de la canasta (ponderada) + brecha mediana y n de cada tipo. peso_imputado_pct =
    # parte del peso de la canasta que no se midió en el grupo o mes: subtipos imputados con su último mes válido (serie
    # mensual) o con la brecha nacional del período (grupos, ref_keys; ahí confiable = eso <= MAX_PESO_IMPUTADO y el
    # grupo tiene >= MIN_SUC_AGG sucursales)
    _det = []
    _t = _agg_tipo(df, keys, ref_keys, _det)
    if detalle is not None:
        detalle.extend(_det)
    if not len(_t):
        return pd.DataFrame(columns=keys + ['brecha_canasta','n_tipos','n_min','peso_imputado_pct','confiable'])
    if keys:
        _pv = lambda _v: _t.pivot_table(index=keys, columns='tipo', values=_v, aggfunc='first')
    else:
        _pv = lambda _v: _t.set_index('tipo')[_v].to_frame().T.reset_index(drop=True)
    _g, _n, _im, _ns = (_pv(_v).reindex(columns=TIPOS_ORD) for _v in
                        ('brecha_mediana', 'n_sucursales', 'n_subtipos_imputados', 'n_subtipos'))
    _n, _im, _ns = (_x.reindex(index=_g.index) for _x in (_n, _im, _ns))
    _w = pd.Series(W_TIPO).reindex(TIPOS_ORD)
    _rel = 1 + _g / 100
    _num = (_rel * _w).sum(axis=1, min_count=1)
    _den = (_rel.notna() * _w).sum(axis=1)
    _o = pd.DataFrame(index=_g.index)
    _o['brecha_canasta'] = (_num / _den - 1) * 100
    _o['n_tipos'] = _g.notna().sum(axis=1)
    _o['n_min'] = _n.min(axis=1)
    _o['peso_imputado_pct'] = 100 * ((_im / _ns).fillna(0) * _w).sum(axis=1) / _den
    if ref_keys is not None and keys != ['mes']:
        _o['n_sucursales'] = df.groupby(keys)['suc_key'].nunique().reindex(_g.index).fillna(0).astype(int)
        _o['confiable'] = (_o['peso_imputado_pct'] <= MAX_PESO_IMPUTADO + 1e-9) & (_o['n_sucursales'] >= MIN_SUC_AGG)
        _d = pd.concat(_det, ignore_index=True)
        _d = _d[_d['_imp'] == 1]
        _o['subtipos_con_brecha_nacional'] = (_d.groupby(keys)['subtipo'].agg(lambda _x: ', '.join(_x))
                                              .reindex(_g.index).fillna(''))
    else:
        _o['confiable'] = (_o['n_tipos'] == len(TIPOS_ORD)) & (_o['n_min'] >= MIN_SUC_AGG)
    _o['subtipos_imputados'] = _im.sum(axis=1)
    for _c in TIPOS_ORD:
        _o[f'brecha_{_c}'] = _g[_c]
    for _c in TIPOS_ORD:
        _o[f'n_{_c}'] = _n[_c]
    if ref_keys is not None and keys != ['mes']:
        _o = _o[_o['peso_imputado_pct'] < 100 - 1e-9]     # un grupo sin ningún subtipo propio es la brecha nacional
    return _o.reset_index() if keys else _o.reset_index(drop=True)

# ── Panel BALANCEADO: sucursal × subtipo presentes (con los dos lados) en >= FRAC_MESES_PANEL de los meses ──
_nmes = bt_sub['mes'].nunique()
_minm = max(1, int(round(FRAC_MESES_PANEL * _nmes)))
_pres = bt_sub.groupby(_sk + ['tipo','subtipo'])['mes'].nunique()
_celdas = _pres[_pres >= _minm].index
bt_bal = bt_sub[bt_sub.set_index(_sk + ['tipo','subtipo']).index.isin(_celdas)].copy()
print(f'Panel balanceado: {len(_celdas):,} sucursal×subtipo presentes en >= {_minm}/{_nmes} meses '
      f'({bt_bal["suc_key"].nunique():,} sucursales)')

# ── Por tipo: período completo, mes (todas y panel), año ─────────────────────
brecha_tipo = _agg_tipo(bt_sub, [])
brecha_tipo_mensual = _agg_tipo(bt_sub, ['mes'])
brecha_tipo_mensual_bal = _agg_tipo(bt_bal, ['mes'])
brecha_tipo_anual = _agg_tipo(bt_sub, ['anio'])
brecha_tipo_anual_bal = _agg_tipo(bt_bal, ['anio'])

# ── Por subtipo (la comparación de base): período completo y por año ─────────
def _agg_subtipo(df, keys):
    _cols = keys + ['tipo','subtipo','tacc_100','sin_100','brecha_mediana','n_sucursales','n_obs']
    if len(df) == 0:
        return pd.DataFrame(columns=_cols)
    return (df.groupby(keys + ['tipo','subtipo'])
            .agg(tacc_100=('tacc','median'), sin_100=('sin','median'), brecha_mediana=('brecha_pct','median'),
                 n_sucursales=('suc_key','nunique'), n_obs=('brecha_pct','size')).reset_index())[_cols]
brecha_subtipo = _agg_subtipo(bt_sub, [])
brecha_subtipo_anual = _agg_subtipo(bt_sub, ['anio'])
brecha_subtipo_anual_bal = _agg_subtipo(bt_bal, ['anio'])

# ── Canasta: serie mensual (todas las sucursales y panel balanceado) ──────────
_det_todas, _det_bal = [], []
serie_mensual = _canasta(bt_sub, ['mes'], detalle=_det_todas)
serie_mensual_bal = _canasta(bt_bal, ['mes'], detalle=_det_bal)
serie_anual = _canasta(bt_sub, ['anio'])
serie_anual_bal = _canasta(bt_bal, ['anio'])
if len(serie_mensual):
    _nmed = serie_mensual['n_min'].median()
    _bajos = serie_mensual[serie_mensual['n_min'] < 0.6 * _nmed]
    if len(_bajos):
        print(f'  ⚠️ Cobertura BAJA en {len(_bajos)} mes(es) (el tipo con menos sucursales tiene < 60% de su mediana '
              f'{_nmed:.0f}): ' + ', '.join(f'{_m}(n={int(_n)})' for _m, _n in zip(_bajos['mes'], _bajos['n_min'])))

# ── Subtipos imputados en la serie mensual (rachas de meses seguidos con el valor de su último mes válido) ──
def _rachas(_det, _serie):
    _rows = []
    if not _det:
        return _rows
    for (_t, _st), _g in pd.concat(_det, ignore_index=True).sort_values('mes').groupby(['tipo','subtipo']):
        _f, _m = _g['_imp'].to_numpy(), _g['mes'].to_numpy()
        _nn, _bb = _g['n_suc'].fillna(0).to_numpy(), _g['brecha'].to_numpy()
        _i = 0
        while _i < len(_f):
            if _f[_i]:
                _j = _i
                while _j + 1 < len(_f) and _f[_j + 1]:
                    _j += 1
                _rows.append({'serie': _serie, 'tipo': _t, 'subtipo': _st, 'desde': _m[_i], 'hasta': _m[_j],
                              'meses': _j - _i + 1, 'sucursales_min': int(_nn[_i:_j + 1].min()),
                              'sucursales_max': int(_nn[_i:_j + 1].max()), 'brecha_arrastrada': float(_bb[_i])})
                _i = _j + 1
            else:
                _i += 1
    return _rows
imputaciones = pd.DataFrame(_rachas(_det_todas, 'todas las sucursales') + _rachas(_det_bal, 'panel balanceado'),
                            columns=['serie','tipo','subtipo','desde','hasta','meses','sucursales_min','sucursales_max',
                                     'brecha_arrastrada'])
_largas = imputaciones[imputaciones['meses'] > 3]
if len(_largas):
    print(f'  ⚠️ Subtipos imputados más de 3 meses seguidos (hoja Imputaciones; la serie arrastra su último valor):')
    for _r in _largas.itertuples(index=False):
        print(f'      - [{_r.serie}] {_r.tipo} / {_r.subtipo}: {_r.desde} → {_r.hasta} ({_r.meses} meses, '
              f'{_r.sucursales_min}-{_r.sucursales_max} sucursales; arrastra {_r.brecha_arrastrada:+.1f}%)')

# ── Geografía y cadenas: últimos VENTANA_GEO_MESES meses y por año ────────────
# Misma canasta en todos los grupos (ref_keys): el subtipo sin MIN_SUC_SUBTIPO sucursales en el grupo toma la brecha
# nacional del período; peso_imputado_pct dice cuánto de la canasta no se midió en el grupo
_meses_v = sorted(bt_sub['mes'].unique())[-VENTANA_GEO_MESES:]
bt_v = bt_sub[bt_sub['mes'].isin(_meses_v)]
VENTANA_TXT = f'{_meses_v[0]} → {_meses_v[-1]}' if _meses_v else ''
def _con_datos_propios(_t):
    # tablas por tipo y grupo: afuera el tipo sin ningún subtipo propio en el grupo (sería la brecha nacional)
    return _t[_t['n_subtipos_imputados'] < _t['n_subtipos']].reset_index(drop=True) if len(_t) else _t
brecha_prov = _canasta(bt_v, ['PROVINCIA_NORM'], []).rename(columns={'PROVINCIA_NORM':'provincia'})
brecha_tipo_prov = _con_datos_propios(_agg_tipo(bt_v, ['PROVINCIA_NORM'], [])).rename(columns={'PROVINCIA_NORM':'provincia'})
brecha_region = _canasta(bt_v, ['region'], [])
brecha_tipo_region = _con_datos_propios(_agg_tipo(bt_v, ['region'], []))
brecha_region_anual = _canasta(bt_sub, ['region','anio'], ['anio'])
brecha_empresa = _canasta(bt_v, ['empresa'], [])
brecha_tipo_empresa = _con_datos_propios(_agg_tipo(bt_v, ['empresa'], []))
brecha_empresa_anual = _canasta(bt_sub, ['empresa','anio'], ['anio'])
brecha_cadena = _canasta(bt_v, ['cadena'], [])
for _d in (brecha_prov, brecha_region, brecha_empresa, brecha_cadena):
    if len(_d):
        _d.sort_values('brecha_canasta', inplace=True)

# ── Canasta COMPARABLE por sucursal y mes (mapa, Brecha_sucursal, concentración): la misma canasta de subtipos en todas
# las sucursales; el subtipo que la sucursal no tiene con los dos lados toma la brecha nacional del mes (la de la serie
# mensual, imputación incluida). peso_propio_pct = parte del peso medida en la sucursal. La canasta por cantidades de la
# CELDA 7 (brecha_pct) suma solo los tipos presentes: dependía de qué tipos tiene cada sucursal (con 2 tipos, mediana
# +77%; con 3, +134%; DIA solo tiene fideos y galletitas dulces).
_subs = bt_sub[['tipo','subtipo']].drop_duplicates()
_subs['_w'] = _subs['tipo'].map(W_TIPO) / _subs.groupby('tipo')['subtipo'].transform('size')
_nac = (pd.concat(_det_todas, ignore_index=True)[['mes','tipo','subtipo','brecha']].rename(columns={'brecha': '_bn'})
        if _det_todas else pd.DataFrame(columns=['mes','tipo','subtipo','_bn']))
_cs = (brecha_suc_mes[['suc_key','mes']].drop_duplicates().merge(_subs, how='cross')
       .merge(bt_sub[['suc_key','mes','tipo','subtipo','brecha_pct']], on=['suc_key','mes','tipo','subtipo'], how='left')
       .merge(_nac, on=['mes','tipo','subtipo'], how='left'))
_cs['_wp'] = _cs['_w'] * _cs['brecha_pct'].notna()
_cs['_lb'] = np.log1p(_cs['brecha_pct'].fillna(_cs['_bn']) / 100)
_ct = _cs.groupby(['suc_key','mes','tipo'], as_index=False).agg(_lb=('_lb','mean'), _wp=('_wp','sum'))
_ct['_v'] = np.exp(_ct['_lb']) * _ct['tipo'].map(W_TIPO)
_cc = _ct.groupby(['suc_key','mes'], as_index=False).agg(_v=('_v','sum'), peso_propio_pct=('_wp','sum'))
_cc['brecha_comparable'] = (_cc['_v'] - 1) * 100
_cc['peso_propio_pct'] *= 100
brecha_suc_mes = brecha_suc_mes.drop(columns=['brecha_comparable','peso_propio_pct'], errors='ignore').merge(
    _cc[['suc_key','mes','brecha_comparable','peso_propio_pct']], on=['suc_key','mes'], how='left')
del _cs, _ct, _cc

# ── Concentración: mercado local = DEPARTAMENTO (Georef, CELDA 7) ─────────────
# HHI de empresas con la cuota = sucursales de cada empresa entre las del universo del departamento (el SEPA no tiene
# ventas). Brecha de cada sucursal = mediana de su canasta comparable en la ventana; solo las sucursales con >= 50% del
# peso medido en ellas (en las demás la canasta es casi la nacional). Antes se agrupaba por el texto de la localidad,
# que DIA carga con el nombre de la provincia ("CAPITAL FEDERAL", "BUENOS AIRES"): la correlación salía de la cadena.
_uni = suc_geo[~suc_geo['id_comercio'].isin(CADENAS_FILTRAR) & suc_geo['departamento_id'].notna()]
_bs = (brecha_suc_mes[brecha_suc_mes['mes'].isin(_meses_v)]
       .groupby('suc_key').agg(brecha=('brecha_comparable','median'), peso_propio_pct=('peso_propio_pct','mean')))
_bs = _bs[_bs['peso_propio_pct'] >= 50].join(suc_geo.set_index('suc_key')['departamento_id'], how='inner')
CONC_RHO, CONC_N = float('nan'), 0
if len(_uni):
    _cnt = _uni.groupby(['departamento_id','empresa']).size().rename('_n').reset_index()
    _cnt['_cuota'] = _cnt['_n'] / _cnt.groupby('departamento_id')['_n'].transform('sum')
    _dep = _cnt.groupby('departamento_id').agg(sucursales=('_n','sum'), empresas=('empresa','size'))
    _dep['hhi'] = (_cnt['_cuota'] ** 2).groupby(_cnt['departamento_id']).sum()
    _top = _cnt.sort_values(['_cuota','empresa'], ascending=[False, True]).drop_duplicates('departamento_id')
    _dep = _dep.join(_top.set_index('departamento_id')[['empresa','_cuota']]
                     .rename(columns={'empresa':'empresa_principal','_cuota':'cuota_principal_pct'}))
    _dep['cuota_principal_pct'] *= 100
    _nom = _uni.groupby('departamento_id').agg(provincia=('PROVINCIA_NORM', lambda _x: _x.mode().iat[0]),
                                                departamento=('departamento','first'))
    _bd = _bs.groupby('departamento_id').agg(sucursales_con_brecha=('brecha','size'), brecha_mediana=('brecha','median'),
                                             brecha_prom=('brecha', _pmean), peso_propio_medio=('peso_propio_pct','mean'))
    concentracion = _nom.join(_dep).join(_bd, how='left').reset_index()
    concentracion['sucursales_con_brecha'] = concentracion['sucursales_con_brecha'].fillna(0).astype(int)
    concentracion['confiable'] = concentracion['sucursales_con_brecha'] >= MIN_SUC_DEPTO
    concentracion = concentracion.sort_values('sucursales', ascending=False).reset_index(drop=True)
    # correlación de rangos (Spearman) entre la brecha de cada sucursal y el HHI de su departamento
    _sx = _bs.join(_dep['hhi'], on='departamento_id').dropna(subset=['brecha','hhi'])
    if len(_sx) > 2:
        CONC_RHO, CONC_N = float(_sx['brecha'].rank().corr(_sx['hhi'].rank())), len(_sx)
else:
    concentracion = pd.DataFrame(columns=['departamento_id','provincia','departamento','sucursales','empresas','hhi',
                                          'empresa_principal','cuota_principal_pct','sucursales_con_brecha',
                                          'brecha_mediana','brecha_prom','peso_propio_medio','confiable'])
    print('  (sin departamentos de Georef: no se calcula la concentración)')

# ── Resumen ──────────────────────────────────────────────────────────────────
print('\n=== Brecha POR SUBTIPO (intra-super, $/100 g), todo el período ===')
if len(brecha_subtipo):
    print(brecha_subtipo[['tipo','subtipo','tacc_100','sin_100','brecha_mediana','n_sucursales']].round(1).to_string(index=False))
print('\n=== Brecha POR TIPO (promedio geométrico de las de sus subtipos), todo el período ===')
if len(brecha_tipo):
    print(brecha_tipo[['tipo','tacc_100','sin_100','brecha_mediana','brecha_min_ilustr','n_sucursales']].round(1).to_string(index=False))
print('\n=== Por tipo y año (panel balanceado) ===')
if len(brecha_tipo_anual_bal):
    print(brecha_tipo_anual_bal.pivot_table(index='anio', columns='tipo', values='brecha_mediana').round(1).to_string())
print('\n=== Canasta por año (ponderada ENGHo): todas las sucursales / panel balanceado ===')
if len(serie_anual):
    _sa = serie_anual[['anio','brecha_canasta','n_min']].merge(
        serie_anual_bal[['anio','brecha_canasta','n_min']], on='anio', how='left', suffixes=('', '_bal'))
    print(_sa.round(1).to_string(index=False))
_cg = ['brecha_canasta','peso_imputado_pct','n_sucursales','confiable']
print(f'\n=== Región (últimos {VENTANA_GEO_MESES} meses, {VENTANA_TXT}; misma canasta: subtipos sin datos en el grupo = '
      f'brecha nacional; confiable = <= {MAX_PESO_IMPUTADO}% del peso imputado y >= {MIN_SUC_AGG} sucursales) ===')
if len(brecha_region):
    print(brecha_region[['region'] + _cg].round(1).to_string(index=False))
print(f'\n=== Empresas (últimos {VENTANA_GEO_MESES} meses) ===')
if len(brecha_empresa):
    print(brecha_empresa[['empresa'] + _cg].round(1).to_string(index=False))
print(f'\n=== Cadenas (últimos {VENTANA_GEO_MESES} meses, solo confiables) ===')
if len(brecha_cadena):
    print(brecha_cadena.loc[brecha_cadena['confiable'], ['cadena'] + _cg[:-1]].round(1).to_string(index=False))
_pc = brecha_prov[brecha_prov['confiable']] if len(brecha_prov) else brecha_prov
if len(_pc):
    print(f'\nProvincias confiables: {len(_pc)} de {len(brecha_prov)} · MENOR brecha: {_pc.iloc[0]["provincia"]} '
          f'({_pc.iloc[0]["brecha_canasta"]:+.1f}%) · MAYOR: {_pc.iloc[-1]["provincia"]} ({_pc.iloc[-1]["brecha_canasta"]:+.1f}%)')
if len(concentracion):
    _cf = concentracion[concentracion['confiable']]
    print(f'\n=== Concentración (departamentos con >= {MIN_SUC_DEPTO} sucursales con brecha propia: {len(_cf)}) ===')
    print(f'  Spearman entre la brecha de cada sucursal y el HHI de su departamento: {CONC_RHO:+.2f} ({CONC_N:,} sucursales)')
    if len(_bs) >= 3:
        _h = _bs.join(concentracion.set_index('departamento_id')['hhi'], on='departamento_id').dropna(subset=['hhi'])
        _h['tercil_hhi'] = pd.qcut(_h['hhi'].rank(method='first'), 3, labels=['bajo','medio','alto'])
        print(_h.groupby('tercil_hhi', observed=True).agg(hhi_mediano=('hhi','median'), brecha_mediana=('brecha','median'),
                                                          sucursales=('brecha','size')).round(2).to_string())"""))

# ── CELL 8b — SERIE TPD (HEDÓNICA) ─────────────────────────────────────────────
cells.append(cell_code(r"""# ============================================================
# CELDA 8b — Serie TPD (hedónica) de la brecha: robustez frente a la imputación de subtipos
# ============================================================
# BRECHA_CELIACA §3.9 y §14.12. Una regresión por SUBTIPO con todas sus observaciones producto × sucursal × mes ($/100 g;
# un producto con dos códigos o una línea con varios sabores entra una vez, con la mediana de sus códigos, como en la
# CELDA 7):
#     ln p(producto, sucursal, mes) = α(sucursal, mes) + γ(producto) + β(mes) · sinTACC + ε
# α es la celda de la descriptiva (el subtipo en esa sucursal y mes): cada sin TACC se compara con los con TACC de su
# subtipo en el mismo super y mes. Con α por sucursal-mes del TIPO entero, la prima de un subtipo se medía contra todos
# los con TACC del tipo (las galletitas con chips daban la evolución al revés). γ fija el nivel de cada producto: qué
# productos tiene cada sucursal no mueve la serie (la mediana de la descriptiva sí). Mínimos cuadrados ponderados: cada
# producto pesa 1 / (productos de su lado en la celda). Nivel del subtipo = promedio de γ sin TACC − promedio de γ con
# TACC, cada producto pesado por su disponibilidad (observaciones de todo el período: ponderaciones fijas); brecha del
# subtipo en el mes = exp(nivel + β(mes)) − 1 (no depende de qué producto o mes se fija como referencia). Tipo =
# promedio geométrico de sus subtipos y canasta = suma ENGHo, como la descriptiva. NO arrastra: el subtipo-mes con menos
# de la mitad de sus sucursales, que la descriptiva arrastra (hoja Imputaciones), sale de las sucursales que hay, con su
# IC; solo con menos de MIN_SUC_SUBTIPO sucursales con los dos lados (con tan pocas, el error agrupado por sucursal
# subestima la incertidumbre) no tiene dato propio y se mueve: en el panel, con la variación del MISMO subtipo en todas
# las sucursales si ahí tiene dato en los dos meses (mismos productos, más sucursales); si no (y siempre en todas las
# sucursales), con el promedio de los demás subtipos de su tipo (el único subtipo de su tipo, el rebozador, queda con el
# valor del mes vecino). Moverlo con los demás subtipos falla en un quiebre que afecta a unos y no a otros: en oct-2023
# el spaghetti del panel no tenía pares y, movido con el penne y el tirabuzón (que caían por el salto de precio de los
# códigos nuevos de Molinos), daba −38%. Dos universos: las celdas del panel balanceado (comparable con la serie clave)
# y todas las sucursales. Errores estándar agrupados por sucursal (CR1) e IC 95% por el método delta, con
# la covarianza entre subtipos y tipos; aparte, agrupados por empresa (_empresa: la cadena fija el precio de todas sus
# sucursales y sus precios se mueven juntos; con pocas empresas, CR1 se queda corto). Ajuste exacto (ecuaciones
# normales con los efectos de celda descontados, matrices dispersas): no itera.
from scipy import sparse as _sp

def _tpd_ajuste(_d, _np, _nt, _nc, _ref, _base, _ne=0):
    # _d: g (celda: sucursal-mes del subtipo), c (sucursal), j (producto), t (mes), s (1 = sin TACC), y (log del precio), w (peso), enteros
    # 0..n-1 (c sobre las _nc sucursales de todos los tipos; e, si _ne > 0, sobre las _ne empresas). Columnas: _np
    # productos y _nt meses (sin TACC × mes); se fijan γ(_ref) = 0 y β(_base) = 0. Devuelve θ completo (NaN = no
    # identificado), la inversa de X'WX (columnas estimadas) y los puntajes Σ w·x·u por sucursal (y por empresa) para la
    # covarianza agrupada.
    _N = len(_d)
    _g, _c, _j, _t, _s = (_d[_x].to_numpy() for _x in ('g', 'c', 'j', 't', 's'))
    _y, _w = _d['y'].to_numpy(float), _d['w'].to_numpy(float)
    _p, _ix = _np + _nt, np.arange(_N)
    _X = _sp.csr_matrix((np.ones(_N + int(_s.sum())), (np.concatenate([_ix, _ix[_s == 1]]),
                                                          np.concatenate([_j, _np + _t[_s == 1]]))), shape=(_N, _p))
    _G = int(_g.max()) + 1
    _Wg = np.bincount(_g, weights=_w, minlength=_G)
    _Cg = _sp.csr_matrix((_w, (_g, _ix)), shape=(_G, _N)) @ _X              # suma ponderada de x en cada sucursal-mes
    _A = (_X.T @ _sp.diags(_w) @ _X).toarray() - (_Cg.T @ _sp.diags(1.0 / _Wg) @ _Cg).toarray()
    _Sy = np.bincount(_g, weights=_w * _y, minlength=_G)
    _b = _X.T @ (_w * _y) - _Cg.T @ (_Sy / _Wg)
    _k = np.ones(_p, bool)
    _k[_ref] = False
    _k[_np + _base] = False
    _k &= np.diag(_A) > 1e-9 * max(1.0, float(np.diag(_A).max()))            # sin variación propia: no identificado
    _B = _A[np.ix_(_k, _k)]
    _rango = int(np.linalg.matrix_rank(_B))
    _Bi = np.linalg.inv(_B) if _rango == _B.shape[0] else np.linalg.pinv(_B)
    _th = np.full(_p, np.nan)
    _th[_k] = _Bi @ _b[_k]
    _th[_ref] = 0.0
    _th[_np + _base] = 0.0
    _f = _X @ np.nan_to_num(_th)
    _u = (_y - (_Sy / _Wg)[_g]) - (_f - (np.bincount(_g, weights=_w * _f, minlength=_G) / _Wg)[_g])
    _Sc = (_sp.csr_matrix((_w * _u, (_c, _ix)), shape=(_nc, _N)) @ _X).tocsc()[:, np.where(_k)[0]]
    _Se = ((_sp.csr_matrix((_w * _u, (_d['e'].to_numpy(), _ix)), shape=(_ne, _N)) @ _X).tocsc()[:, np.where(_k)[0]]
           if _ne else None)
    # con rango incompleto (productos de un lado que nunca conviven en una celda con los demás, p. ej. dos códigos del
    # mismo producto sin unir en PRODUCTO) solo son válidas las combinaciones del espacio de filas: proyección para verlo
    return {'theta': _th, 'k': _k, 'Binv': _Bi, 'Sc': _Sc, 'Se': _Se, 'rango_completo': _rango == _B.shape[0],
            'grupos': _G, 'proy': None if _rango == _B.shape[0] else _B @ _Bi}

def _tpd_comb(*_partes):
    # combina gradientes {subtipo: vector} con coeficientes: _partes = (coef, gradiente), ...
    _o = {}
    for _cf, _gd in _partes:
        for _key, _v in _gd.items():
            _o[_key] = _o.get(_key, 0) + _cf * _v
    return _o

def _tpd_serie(_pt, _tipos, _w_tipo, _min_suc=1, _ref_niv=None, _emp=None):
    # _pt: suc_key, mes, tipo, subtipo, rol ('tacc' / 'sin'), producto, precio_100 (una fila por producto, sucursal y
    # mes). Una regresión por subtipo con efecto de celda (sucursal-mes del subtipo); tipo = promedio de sus subtipos;
    # canasta con los pesos ENGHo. El subtipo-mes con menos de _min_suc sucursales con los dos lados no tiene dato propio:
    # se mueve con la variación del mismo subtipo en _ref_niv (los 'niveles' de otro universo, el de todas las sucursales) si
    # ahí tiene dato propio en los dos meses; si no, con los demás subtipos del tipo. _emp (suc_key -> empresa): además de
    # los errores agrupados por sucursal, los agrupados por empresa (la cadena fija el precio de todas sus sucursales: sus
    # precios se mueven juntos). Devuelve tipos, canasta, subtipos, productos, diagnóstico del ajuste y los niveles de cada
    # subtipo (para usarlos como _ref_niv).
    _pt = _pt[_pt['precio_100'] > 0].copy()
    _pt['w'] = 1.0 / _pt.groupby(['suc_key','mes','tipo','subtipo','rol'])['producto'].transform('size')
    _pt['y'] = np.log(_pt['precio_100'].astype(float))
    _pt['s'] = (_pt['rol'] == 'sin').astype(int)
    _meses = sorted(_pt['mes'].unique())
    _nt = len(_meses)
    _pt['t'] = _pt['mes'].map({_m: _i for _i, _m in enumerate(_meses)})
    _sucs = sorted(_pt['suc_key'].unique())
    _nc = len(_sucs)
    _pt['c'] = _pt['suc_key'].map({_x: _i for _i, _x in enumerate(_sucs)})
    _q = _nc / max(_nc - 1, 1)                                               # CR1
    _ne = 0
    if _emp is not None:
        _ek = _pt['suc_key'].map(_emp).fillna(_pt['suc_key']).astype(str)  # sin empresa: su sucursal es su grupo
        _emps = sorted(_ek.unique())
        _ne = len(_emps)
        _pt['e'] = _ek.map({_x: _i for _i, _x in enumerate(_emps)})
    _qe = _ne / max(_ne - 1, 1)
    _fit, _lev, _id, _grad, _npar = {}, {}, {}, {}, {}
    _prods, _diag = [], []
    for (_tp, _sub), _d in _pt.groupby(['tipo','subtipo'], sort=True):
        if _tp not in _tipos or _d['s'].nunique() < 2:
            continue
        _d = _d.copy()
        _d['g'] = _d.groupby(['suc_key','mes'], sort=False).ngroup()
        _pi = (_d.groupby(['producto','rol'], as_index=False).agg(obs=('y', 'size'))
               .sort_values(['rol','producto']).reset_index(drop=True))
        _np = len(_pi)
        _d['j'] = _d['producto'].map(dict(zip(_pi['producto'], _pi.index)))
        _cel = _d.groupby('g').agg(t=('t', 'first'), smin=('s', 'min'), smax=('s', 'max'))
        _pares = (_cel[(_cel['smin'] == 0) & (_cel['smax'] == 1)].groupby('t').size()
                  .reindex(range(_nt), fill_value=0))
        if _pares.sum() == 0:
            continue
        _base = int(_pares[_pares > 0].index.min())
        _ref = int(_pi.loc[_pi['rol'] == 'tacc', 'obs'].idxmax())
        _r = _tpd_ajuste(_d, _np, _nt, _nc, _ref, _base, _ne)
        _th, _keep = _r['theta'], np.where(_r['k'])[0]
        _ok = ~np.isnan(_th[:_np])
        # nivel del subtipo: promedio de γ sin TACC − promedio de γ con TACC, cada producto pesado por su disponibilidad
        # (observaciones en todo el período: canasta fija, como un índice con ponderaciones fijas)
        _aL = np.zeros(_np + _nt)
        _peso = np.zeros(_np)
        for _lado, _sg in (('sin', 1.0), ('tacc', -1.0)):
            _x = _pi[(_pi['rol'] == _lado) & _ok]
            _peso[_x.index] = _x['obs'] / _x['obs'].sum()
            _aL[_x.index] = _sg * _peso[_x.index]
        _key = (_tp, _sub)
        _fit[_key] = {'Binv': _r['Binv'], 'Sc': _r['Sc'], 'Se': _r['Se']}
        _lv = np.full(_nt, np.nan)
        _no_est = 0
        for _t in range(_nt):
            if _pares[_t] < max(_min_suc, 1) or np.isnan(_th[_np + _t]):
                continue
            _a = _aL.copy()
            _a[_np + _t] += 1.0
            if _r['proy'] is not None and np.abs(_r['proy'] @ _a[_keep] - _a[_keep]).max() > 1e-7:
                _no_est += 1                       # nivel no identificado: se mueve como un subtipo-mes sin dato propio
                continue
            _lv[_t] = float(_a @ np.nan_to_num(_th))
            _grad[(_tp, _sub, _t)] = {_key: _a[_keep]}
        _lev[_key], _id[_key], _npar[_key] = _lv, ~np.isnan(_lv), _pares.to_numpy()
        _gcon = float((_th[:_np] * _peso)[(_pi['rol'] == 'tacc').to_numpy() & _ok].sum())
        for _i, _row in _pi.iterrows():
            _prods.append({'tipo': _tp, 'subtipo': _sub, 'lado': 'sin TACC' if _row['rol'] == 'sin' else 'con TACC',
                           'producto': _row['producto'], 'obs': int(_row['obs']), 'peso_en_el_nivel': _peso[_i],
                           'gamma': _th[_i], 'mes_base': _meses[_base],
                           'nivel_vs_con_tacc_subtipo_pct': np.expm1(_th[_i] - _gcon) * 100, 'referencia': _i == _ref})
        _diag.append({'tipo': _tp, 'subtipo': _sub, 'obs': len(_d), 'celdas': _r['grupos'], 'productos': _np,
                      'meses_con_pares': int((_pares > 0).sum()), 'meses_con_dato_propio': int((~np.isnan(_lv)).sum()),
                      'meses_no_estimables': _no_est, 'rango_completo': _r['rango_completo']})
    # subtipo-mes sin dato propio: su valor del mes vecino movido con la variación del mismo subtipo en _ref_niv (dato propio
    # en los dos meses) o, si no, con el promedio de los demás subtipos del tipo que tienen dato propio en los dos meses
    # (imputación por la variación del resto del agregado); adelante y después hacia atrás. Con _ref_niv, el IC del mes movido
    # es el del mes de partida (no suma la incertidumbre de la variación de referencia, que sale de más sucursales).
    _niveles = {_k: (_meses, _lev[_k].copy(), _id[_k].copy()) for _k in _lev}
    _rf = {}
    if _ref_niv:
        for _k, (_mr, _lr, _ir) in _ref_niv.items():
            _ix_r = {_m: _i for _i, _m in enumerate(_mr)}
            _rf[_k] = np.array([_lr[_ix_r[_m]] if _m in _ix_r and _ir[_ix_r[_m]] else np.nan for _m in _meses])
    _con = {_k: [''] * _nt for _k in _lev}
    _filas_s = []
    for _tp in _tipos:
        _subs = [_k for _k in _lev if _k[0] == _tp]
        for _paso in (1, -1):
            _orden = range(1, _nt) if _paso == 1 else range(_nt - 2, -1, -1)
            for _t in _orden:
                _u = _t - _paso
                for _k in _subs:
                    if not np.isnan(_lev[_k][_t]) or np.isnan(_lev[_k][_u]):
                        continue
                    if _k in _rf and not np.isnan(_rf[_k][_t]) and not np.isnan(_rf[_k][_u]):
                        _lev[_k][_t] = _lev[_k][_u] + _rf[_k][_t] - _rf[_k][_u]
                        _grad[(_tp, _k[1], _t)] = _grad[(_tp, _k[1], _u)]
                        _con[_k][_t] = 'mismo subtipo en todas las sucursales'
                        continue
                    _otros = [_o for _o in _subs if _o != _k and _id[_o][_t] and _id[_o][_u]]
                    _mov = float(np.mean([_lev[_o][_t] - _lev[_o][_u] for _o in _otros])) if _otros else 0.0
                    _lev[_k][_t] = _lev[_k][_u] + _mov
                    _grad[(_tp, _k[1], _t)] = _tpd_comb((1.0, _grad[(_tp, _k[1], _u)]),
                                                        *[(1.0 / len(_otros), _grad[(_tp, _o[1], _t)]) for _o in _otros],
                                                        *[(-1.0 / len(_otros), _grad[(_tp, _o[1], _u)]) for _o in _otros])
                    _con[_k][_t] = 'demás subtipos del tipo' if _otros else 'mes vecino'
        for _k in _subs:
            for _t in range(_nt):
                if not np.isnan(_lev[_k][_t]):
                    _filas_s.append({'mes': _meses[_t], 'tipo': _tp, 'subtipo': _k[1],
                                     'brecha_tpd': np.expm1(_lev[_k][_t]) * 100,
                                     'sucursales_con_pares': int(_npar[_k][_t]), 'movido_con_los_demas': not _id[_k][_t],
                                     'movido_con': _con[_k][_t]})

    def _se(_gd, _por_empresa=False):
        # error estándar de una combinación lineal de los parámetros de varios subtipos (covarianza agrupada por sucursal
        # o, con _por_empresa, por empresa)
        if _por_empresa and not _ne:
            return float('nan')
        _z = np.zeros(_ne if _por_empresa else _nc)
        for _key, _v in _gd.items():
            _z += np.asarray(_fit[_key]['Se' if _por_empresa else 'Sc'] @ (_fit[_key]['Binv'] @ _v)).ravel()
        return float(np.sqrt((_qe if _por_empresa else _q) * (_z ** 2).sum()))

    _filas, _lam, _fmov = [], {}, {}
    for _tp in _tipos:
        _subs = [_k for _k in _lev if _k[0] == _tp]
        for _t in range(_nt):
            _ks = [_k for _k in _subs if not np.isnan(_lev[_k][_t])]
            if not _ks:
                continue
            _l = float(np.mean([_lev[_k][_t] for _k in _ks]))
            _g = _tpd_comb(*[(1.0 / len(_ks), _grad[(_tp, _k[1], _t)]) for _k in _ks])
            _s, _s2 = _se(_g), _se(_g, True)
            _lam[(_tp, _t)] = (_l, _g)
            _nm = int(sum(not _id[_k][_t] for _k in _ks))
            _fmov[(_tp, _t)] = _nm / len(_ks)
            _filas.append({'mes': _meses[_t], 'tipo': _tp, 'brecha_tpd': np.expm1(_l) * 100,
                           'brecha_tpd_ic95_inf': np.expm1(_l - 1.96 * _s) * 100,
                           'brecha_tpd_ic95_sup': np.expm1(_l + 1.96 * _s) * 100, 'error_estandar_log': _s,
                           'brecha_tpd_ic95_inf_empresa': np.expm1(_l - 1.96 * _s2) * 100,
                           'brecha_tpd_ic95_sup_empresa': np.expm1(_l + 1.96 * _s2) * 100,
                           'error_estandar_log_empresa': _s2, 'subtipos': len(_ks), 'subtipos_movidos': _nm})
    _filas_c = []
    for _t in range(_nt):
        _ws = {_tp: _w_tipo[_tp] for _tp in _tipos if (_tp, _t) in _lam}
        if not _ws:
            continue
        _sw = sum(_ws.values())
        _v = sum(_wk * np.exp(_lam[(_tp, _t)][0]) for _tp, _wk in _ws.items()) / _sw
        _gc = _tpd_comb(*[(_wk * np.exp(_lam[(_tp, _t)][0]) / _sw, _lam[(_tp, _t)][1]) for _tp, _wk in _ws.items()])
        _s, _s2 = _se(_gc), _se(_gc, True)
        # peso_movido_pct: parte del peso de la canasta en subtipos sin dato propio ese mes (como peso_imputado_pct)
        _filas_c.append({'mes': _meses[_t], 'brecha_canasta_tpd': (_v - 1) * 100,
                         'brecha_canasta_tpd_ic95_inf': (_v - 1.96 * _s - 1) * 100,
                         'brecha_canasta_tpd_ic95_sup': (_v + 1.96 * _s - 1) * 100,
                         'brecha_canasta_tpd_ic95_inf_empresa': (_v - 1.96 * _s2 - 1) * 100,
                         'brecha_canasta_tpd_ic95_sup_empresa': (_v + 1.96 * _s2 - 1) * 100,
                         'peso_movido_pct': 100 * sum(_wk * _fmov[(_tp, _t)] for _tp, _wk in _ws.items()) / _sw,
                         'tipos_tpd': len(_ws)})
    return {'tipos': pd.DataFrame(_filas), 'canasta': pd.DataFrame(_filas_c), 'subtipos': pd.DataFrame(_filas_s),
            'productos': pd.DataFrame(_prods), 'ajuste': pd.DataFrame(_diag), 'niveles': _niveles}

# ── Datos: producto × sucursal × mes, con las sucursales del universo (CELDA 7); dos universos: las celdas del panel
# balanceado (sucursal × subtipo de la CELDA 8, comparable con la serie clave) y todas las sucursales ──
_pt = (datos_dia[['id_comercio','id_bandera','id_sucursal','mes','tipo','subtipo','rol','producto','precio_100']]
       .merge(suc_geo[['id_comercio','id_bandera','id_sucursal','suc_key']], on=['id_comercio','id_bandera','id_sucursal'],
              how='inner')
       .groupby(['suc_key','mes','tipo','subtipo','rol','producto'], as_index=False)['precio_100'].median())
_UNI_TPD = {'panel balanceado': _pt.merge(bt_bal[['suc_key','tipo','subtipo']].drop_duplicates(),
                                          on=['suc_key','tipo','subtipo'], how='inner'),
            'todas las sucursales': _pt}
_DESC = {'panel balanceado': (brecha_tipo_mensual_bal, serie_mensual_bal),
         'todas las sucursales': (brecha_tipo_mensual, serie_mensual)}
# primero todas las sucursales: el panel mueve sus subtipo-mes sin pares con el mismo subtipo de todas las sucursales.
# IC también con los errores agrupados por empresa (_ic95_*_empresa)
_EMP_SUC = suc_geo.drop_duplicates('suc_key').set_index('suc_key')['empresa'].to_dict()
_tpd = {'todas las sucursales': _tpd_serie(_UNI_TPD['todas las sucursales'], TIPOS_ORD, W_TIPO, MIN_SUC_SUBTIPO,
                                           _emp=_EMP_SUC)}
_tpd = {'panel balanceado': _tpd_serie(_UNI_TPD['panel balanceado'], TIPOS_ORD, W_TIPO, MIN_SUC_SUBTIPO,
                                       _tpd['todas las sucursales']['niveles'], _emp=_EMP_SUC), **_tpd}
del _pt, _UNI_TPD
tpd_ajuste = pd.concat([_r['ajuste'].assign(universo=_u) for _u, _r in _tpd.items()], ignore_index=True)
tpd_subtipos = pd.concat([_r['subtipos'].assign(universo=_u) for _u, _r in _tpd.items()], ignore_index=True)
tpd_productos = pd.concat([_r['productos'].assign(universo=_u) for _u, _r in _tpd.items()], ignore_index=True)
if len(tpd_productos):
    tpd_productos['descripcion'] = tpd_productos['producto'].map(lambda _x: EAN_DESC.get(_x, _x))
_bt = []
for _u, _r in _tpd.items():
    if len(_r['tipos']):
        _bt.append(_r['tipos'].assign(universo=_u).merge(
            _DESC[_u][0][['mes','tipo','brecha_mediana','n_subtipos_imputados']]
            .rename(columns={'brecha_mediana': 'brecha_descriptiva', 'n_subtipos_imputados': 'subtipos_imputados_descriptiva'}),
            on=['mes','tipo'], how='left'))
brecha_tipo_tpd = pd.concat(_bt, ignore_index=True) if _bt else pd.DataFrame(columns=['mes','tipo','universo'])
# serie de la canasta: una fila por mes, TPD y descriptiva de los dos universos
serie_tpd = pd.DataFrame({'mes': sorted(set(serie_mensual['mes']) | set(serie_mensual_bal['mes']))})
for _u, _suf in (('panel balanceado', 'panel'), ('todas las sucursales', 'todas')):
    _c = _tpd[_u]['canasta']
    if len(_c):
        serie_tpd = serie_tpd.merge(_c.drop(columns='tipos_tpd').rename(
            columns={_x: f'{_x}_{_suf}' for _x in _c.columns if _x != 'mes'}), on='mes', how='left')
    _ds = _DESC[_u][1][['mes','brecha_canasta','peso_imputado_pct']].rename(
        columns={'brecha_canasta': f'brecha_canasta_descriptiva_{_suf}', 'peso_imputado_pct': f'peso_imputado_pct_{_suf}'})
    serie_tpd = serie_tpd.merge(_ds, on='mes', how='left')
    if f'brecha_canasta_tpd_{_suf}' in serie_tpd.columns:
        serie_tpd[f'dif_tpd_menos_descriptiva_{_suf}_pp'] = (serie_tpd[f'brecha_canasta_tpd_{_suf}']
                                                            - serie_tpd[f'brecha_canasta_descriptiva_{_suf}'])
# por año: promedio de los meses (TPD y descriptiva por igual)
_cols_a = [_c for _c in serie_tpd.columns if _c.startswith('brecha_canasta_') and 'ic95' not in _c]
tpd_anual = serie_tpd.assign(anio=serie_tpd['mes'].str[:4]).groupby('anio')[_cols_a].mean().reset_index()
if len(brecha_tipo_tpd):
    _ta = (brecha_tipo_tpd[brecha_tipo_tpd['universo'] == 'panel balanceado'].assign(anio=lambda _x: _x['mes'].str[:4])
           .groupby(['anio','tipo'])[['brecha_tpd','brecha_descriptiva']].mean().unstack('tipo'))
    _ta.columns = [f'{_a}_panel_{_b}' for _a, _b in _ta.columns]
    tpd_anual = tpd_anual.merge(_ta.reset_index(), on='anio', how='left')

print('=== Serie TPD (hedónica): robustez frente a la imputación de subtipos (BRECHA_CELIACA §14.12) ===')
if len(tpd_ajuste):
    _aj = tpd_ajuste.groupby('universo').agg(subtipos=('subtipo', 'size'), obs=('obs', 'sum'), celdas=('celdas', 'sum'),
                                             rango_completo=('rango_completo', 'all'))
    print(_aj.to_string())
    if not tpd_ajuste['rango_completo'].all():
        _ri = tpd_ajuste[~tpd_ajuste['rango_completo']]
        print('  ⚠️ subtipos con productos que no se pueden comparar entre sí (nunca conviven en una celda; ¿dos códigos '
              'del mismo producto sin unir en PRODUCTO?): ' + ', '.join(
                  f'[{_r.universo}] {_r.subtipo} ({_r.meses_no_estimables} meses sin nivel estimable)'
                  for _r in _ri.itertuples(index=False)))
    _mv = tpd_subtipos[tpd_subtipos['movido_con_los_demas']]
    _ABR_MOV = {'mismo subtipo en todas las sucursales': 't', 'demás subtipos del tipo': 'd', 'mes vecino': 'v'}
    if len(_mv):
        print(f'  Subtipo-mes con menos de {MIN_SUC_SUBTIPO} sucursales con los dos lados (movidos con el mismo subtipo '
              'en todas las sucursales [t], con los demás subtipos del tipo [d] o con el mes vecino [v]): ' +
              ', '.join(f'[{_u}] {_s} {len(_g)} (' + ' '.join(
                  f'{_n}{_ABR_MOV.get(_c, "?")}' for _c, _n in _g['movido_con'].value_counts().sort_index().items()) + ')'
                  for (_u, _s), _g in _mv.groupby(['universo','subtipo'])))
if len(serie_tpd) and 'brecha_canasta_tpd_panel' in serie_tpd.columns:
    print('\nCanasta por año (promedio de los meses): TPD y descriptiva, panel balanceado y todas las sucursales')
    print(tpd_anual[['anio'] + [_c for _c in tpd_anual.columns if _c.startswith('brecha_canasta_')]].round(1)
          .to_string(index=False))
    _dp = serie_tpd['dif_tpd_menos_descriptiva_panel_pp']
    _imp = serie_tpd['peso_imputado_pct_panel'] > 0
    print(f'TPD − descriptiva (canasta, panel): mediana {_dp.median():+.1f} pp; |dif.| mediana {_dp[~_imp].abs().median():.1f} '
          f'pp en los {int((~_imp).sum())} meses sin subtipos imputados y {_dp[_imp].abs().median():.1f} pp en los '
          f'{int(_imp.sum())} con alguno. Desvío de la variación mensual: TPD '
          f'{serie_tpd["brecha_canasta_tpd_panel"].diff().std():.1f} pp, descriptiva '
          f'{serie_tpd["brecha_canasta_descriptiva_panel"].diff().std():.1f} pp')
    print(f'Meses con algún subtipo sin dato propio (panel): TPD {int((serie_tpd["peso_movido_pct_panel"] > 0).sum())} '
          f'(movido), descriptiva {int(_imp.sum())} (arrastrado)')
    _ult = serie_tpd.dropna(subset=['brecha_canasta_tpd_panel']).iloc[-1]
    print(f'Último mes ({_ult["mes"]}), panel: TPD {_ult["brecha_canasta_tpd_panel"]:+.1f}% (IC 95% '
          f'{_ult["brecha_canasta_tpd_ic95_inf_panel"]:+.1f}% a {_ult["brecha_canasta_tpd_ic95_sup_panel"]:+.1f}%) · '
          f'descriptiva {_ult["brecha_canasta_descriptiva_panel"]:+.1f}%')
if len(brecha_tipo_tpd):
    _tt = (brecha_tipo_tpd[brecha_tipo_tpd['universo'] == 'panel balanceado'].assign(anio=lambda _x: _x['mes'].str[:4])
           .groupby(['tipo','anio'])[['brecha_tpd','brecha_descriptiva']].mean().unstack('anio').round(1))
    print('\nPor tipo y año, panel balanceado (promedio de los meses): TPD / descriptiva')
    print(_tt.to_string())"""))

# ── CELL 8c — ANÁLISIS COMPLEMENTARIOS ───────────────────────────────────────────────────────────
cells.append(cell_code(r"""# ============================================================
# CELDA 8c — Análisis complementarios: sensibilidad, índices de cada lado, disponibilidad, intervalos de confianza,
#            competencia local, concentración, empresas (composición, varianza, surtido), hedónica de grupos, prima de
#            la misma marca y costo con la CBA (+ datos para el análisis propio)
# ============================================================
# Lo que pidieron las evaluaciones de expertos (docs/EVALUACION_EXPERTOS_2026-10-27_nb06.md):
#   - Sensibilidad: la brecha nacional de los últimos meses cambiando UNA decisión por vez (ESCENARIOS_SENSIBILIDAD).
#   - Índices de precio de CADA LADO (con y sin TACC), encadenados con los mismos productos en la misma sucursal, contra
#     el IPC de alimentos del INDEC: dicen POR QUÉ se mueve la brecha.
#   - Disponibilidad: de las sucursales que venden un tipo con TACC, cuántas venden también su versión sin TACC. La
#     brecha se mide solo donde están los dos lados: no encontrar el producto también es un costo.
#   - Intervalos de confianza de la brecha nacional, de las regiones, provincias, empresas y cadenas, y de su diferencia
#     con la nacional: bootstrap por sucursal y, como las cadenas fijan el precio para todas sus sucursales, por empresa.
#   - Concentración a nivel sucursal: regresiones con efectos de empresa y región, y cada lado por separado.
#   - Empresas: composición de cada universo por año, cuánto de la variación entre sucursales explica la empresa y qué
#     productos de la canasta vende cada cadena (el surtido cambia entre cadenas y en el tiempo).
#   - Hedónica de grupos: con los mismos productos, cuánto cambia la brecha entre regiones y empresas controlando cada
#     una por la otra, y con la concentración (HHI del departamento) o la competencia local (empresas a <= R km); sin los
#     efectos de producto (con el surtido de cada grupo), la parte del surtido; y por año.
#   - Prima de la misma marca: el sin TACC contra el con TACC de la MISMA marca en el mismo súper y mes, para separar la
#     prima sin gluten de la prima de marca.
#   - Costo en pesos con la CBA del INDEC: cuánto más paga por mes un adulto equivalente y un hogar tipo.
#   - Datos para el análisis propio (OUTPUT_DIR/datos): paneles sucursal × mes × subtipo y producto × sucursal × mes (la
#     canasta y los adicionales), productos, sucursales, diccionario de datos y LEEME.md.
_sk = ['id_comercio','id_bandera','id_sucursal']
_W8 = pd.Series(W_TIPO, dtype=float)
_mv = list(_meses_v)
_U8 = suc_geo[_sk + ['suc_key','region','PROVINCIA_NORM','empresa','cadena','departamento_id','departamento',
                     'sucursales_latitud','sucursales_longitud']].drop_duplicates('suc_key')
_SUB_W = (bt_sub[['tipo','subtipo']].drop_duplicates()
          .assign(_w=lambda _x: _x['tipo'].map(W_TIPO) / _x.groupby('tipo')['subtipo'].transform('size'))
          .set_index('subtipo')['_w'])

def _bt_desde(_d, _prod='producto', _modo='mediana'):
    # sucursal × EAN × mes -> brecha por sucursal × mes × subtipo, como la CELDA 7: precio de cada producto = mediana de
    # sus códigos; cada lado = mediana de sus productos ('minimo': el más barato a menos de x4 de esa mediana)
    _cols = _sk + ['mes','tipo','subtipo','tacc','sin','brecha_pct']
    if not len(_d):
        return pd.DataFrame(columns=_cols)
    _p = _d.groupby(_sk + ['mes','tipo','subtipo','rol',_prod], as_index=False)['precio_100'].median()
    _g = _sk + ['mes','tipo','subtipo','rol']
    if _modo == 'minimo':
        _m = _p.groupby(_g)['precio_100'].transform('median')
        _s = _p[(_p['precio_100'] >= _m / 4) & (_p['precio_100'] <= _m * 4)].groupby(_g)['precio_100'].min()
    else:
        _s = _p.groupby(_g)['precio_100'].median()
    _s = _s.unstack('rol')
    if not {'tacc','sin'} <= set(_s.columns):
        return pd.DataFrame(columns=_cols)
    _s = _s.dropna(subset=['tacc','sin']).reset_index()
    _s['brecha_pct'] = (_s['sin'] / _s['tacc'] - 1) * 100
    return _s[_cols]

def _wmediana(_v, _w):
    # mediana ponderada; con pesos iguales es la mediana común (el promedio de los dos del medio si son pares)
    _v, _w = np.asarray(_v, float), np.asarray(_w, float)
    _o = np.argsort(_v, kind='stable'); _v, _w = _v[_o], _w[_o]
    _c = np.cumsum(_w)
    if not len(_c) or _c[-1] <= 0:
        return float('nan')
    _h, _tol = _c[-1] / 2, 1e-9 * _c[-1]
    _i = int(np.searchsorted(_c, _h - _tol))
    if abs(_c[_i] - _h) <= _tol and _i + 1 < len(_v):
        return float((_v[_i] + _v[_i + 1]) / 2)
    return float(_v[_i])

def _canasta_nac(_bt, _pesos='iguales', _pesos_suc='iguales'):
    # brecha nacional del período de _bt con la misma regla que el país de los grupos (CELDA 8): mediana de cada
    # subtipo entre sucursal-meses, tipo = promedio geométrico de sus subtipos (pesos iguales o por sucursal-meses),
    # canasta = sum_k w_k (1 + g_k) - 1 entre los tipos presentes. _pesos_suc = 'poblacion': mediana ponderada, cada
    # provincia pesa por su población (PESOS_POBLACION) repartida entre sus sucursal-meses del subtipo y mes
    if not len(_bt):
        return float('nan'), {}
    if _pesos_suc == 'poblacion':
        _x = _bt
        if 'PROVINCIA_NORM' not in _x.columns:
            _on = _sk if set(_sk) <= set(_x.columns) else ['suc_key']
            _x = _x.merge(_U8[_on + ['PROVINCIA_NORM']].drop_duplicates(_on), on=_on, how='left')
        _x = _x.assign(_wp=_x['PROVINCIA_NORM'].map(PESOS_POBLACION).fillna(0)
                       / _x.groupby(['tipo','subtipo','mes','PROVINCIA_NORM'], dropna=False)['brecha_pct'].transform('size'))
        _s = (_x.groupby(['tipo','subtipo'])[['brecha_pct','_wp']]
              .apply(lambda _g: pd.Series({'_b': _wmediana(_g['brecha_pct'], _g['_wp']), '_n': float(len(_g))}))
              .reset_index())
    else:
        _s = _bt.groupby(['tipo','subtipo']).agg(_b=('brecha_pct','median'), _n=('brecha_pct','size')).reset_index()
    _s['_l'] = np.log1p(_s['_b'] / 100)
    _t = {}
    for _tp, _x in _s.groupby('tipo'):
        _w = _x['_n'].to_numpy(float) if _pesos == 'disponibilidad' else np.ones(len(_x))
        _t[_tp] = float(np.expm1(np.average(_x['_l'], weights=_w)) * 100)
    _wt = _W8.reindex(list(_t)).dropna()
    if not len(_wt):
        return float('nan'), _t
    return float(((1 + pd.Series(_t)[_wt.index] / 100) * _wt).sum() / _wt.sum() - 1) * 100, _t

# ── 1. Sensibilidad ──────────────────────────────────────────────────────────
_dv = datos_dia[datos_dia['mes'].isin(_mv)].merge(_U8[_sk], on=_sk)            # el universo de la CELDA 7
_dv['_prod'] = _dv['producto']
_av = (datos_adic[datos_adic['mes'].isin(_mv)].merge(_U8[_sk], on=_sk) if len(datos_adic)
       else pd.DataFrame(columns=list(_dv.columns) + ['producto_todos']))
_PSL = {_norm_ean(_e): _p for _p, _es in globals().get('PRODUCTO_SIN_LINEA', {}).items() for _e in _es}
_LTD = {_norm_ean(_e): _p for _e, _p in globals().get('LINEA_TODOS', {}).items()}
_SUS = {_norm_ean(_e) for _e in globals().get('SUSTITUTOS', set())}

def _datos_escenario(_cfg):
    _d = _dv.copy()
    if _cfg.get('agregar') and len(_av):
        _a = _av if _cfg['agregar'] == 'todos' else _av[_av['ean_norm'].map(
            lambda _e: str(ADIC_INFO.get(_e, {}).get('motivo', '')).startswith('sustituto'))]
        if _cfg['agregar'] == 'todos':
            _d['_prod'] = _d['ean_norm'].map(_LTD).fillna(_d['_prod'])
        _a = _a.assign(_prod=_a['producto_todos'])
        _d = pd.concat([_d, _a[[_c for _c in _d.columns if _c in _a.columns]]], ignore_index=True)
    if _cfg.get('quitar_sustitutos'):
        _d = _d[~_d['ean_norm'].isin(_SUS)]
    if _cfg.get('sin_lineas'):
        _d['_prod'] = _d['ean_norm'].map(_PSL).fillna(_d['ean_norm'])
    return _d

_c_ref, _ = _canasta_nac(bt_v)                       # la brecha nacional de la CELDA 8 (misma canasta que los grupos)
_sin_pob = sorted(set(bt_v['PROVINCIA_NORM'].dropna()) - set(globals().get('PESOS_POBLACION', {})))
if _sin_pob:
    print(f'  ⚠️ provincias sin población en PESOS_POBLACION (pesan 0 en el escenario por población): {_sin_pob}')
_filas = []
for _nom, _cfg in ESCENARIOS_SENSIBILIDAD.items():
    _d = _datos_escenario(_cfg)
    if _cfg.get('estimador') == 'nacional':
        # cada lado por separado: mediana nacional del precio del subtipo entre las sucursal-meses que lo venden
        _p = _d.groupby(_sk + ['mes','tipo','subtipo','rol','_prod'])['precio_100'].median()
        _m = _p.groupby(level=_sk + ['mes','tipo','subtipo','rol']).median().groupby(level=['tipo','subtipo','rol']).median()
        _m = _m.unstack('rol').dropna()
        _b = _m.assign(brecha_pct=(_m['sin'] / _m['tacc'] - 1) * 100).reset_index()
        _n = int(len(_p))
    else:
        _b = _bt_desde(_d, '_prod', 'minimo' if _cfg.get('estimador') == 'minimo' else 'mediana')
        _n = int(len(_b))
    _c, _t = _canasta_nac(_b, _cfg.get('pesos_subtipo', 'iguales'), _cfg.get('pesos_sucursal', 'iguales'))
    _filas.append({'escenario': _nom, 'brecha_canasta': _c,
                   **{f'brecha_{_k}': _t.get(_k, float('nan')) for _k in TIPOS_ORD},
                   'subtipos': int(_b[['tipo','subtipo']].drop_duplicates().shape[0]) if len(_b) else 0,
                   'observaciones': _n, 'cambio': _json.dumps(_cfg, ensure_ascii=False)})
sensibilidad = pd.DataFrame(_filas)
if len(sensibilidad):
    sensibilidad.insert(2, 'diferencia_pp', sensibilidad['brecha_canasta'] - sensibilidad['brecha_canasta'].iloc[0])
_dif_ref = abs(sensibilidad['brecha_canasta'].iloc[0] - _c_ref) if len(sensibilidad) else 0.0
print(f'=== Sensibilidad (últimos {len(_mv)} meses, nacional con la misma canasta que los grupos: {_c_ref:+.1f}%) ===')
if _dif_ref > 1e-6:
    print(f'  ⚠️ el escenario principal difiere {_dif_ref:.2e} pp de la CELDA 8: revisar')
print(sensibilidad[['escenario','brecha_canasta','diferencia_pp']].round(1).to_string(index=False))

# ── 2. Índices de precio de cada lado (con TACC y sin TACC) ───────────────────
# Por subtipo y lado, un índice de efectos fijos sobre los MISMOS productos en la MISMA sucursal (todas las sucursales):
#     ln p(producto, sucursal, mes) = efecto del ítem (producto en esa sucursal) + efecto del mes
# Cada ítem se compara consigo mismo, también entre meses no seguidos: un sin TACC que falta unos meses en una sucursal
# y vuelve más caro aporta su aumento (encadenar mes a mes lo perdía, y como los sin TACC entran y salen más, su índice
# derivaba para abajo). El mes sin datos de un subtipo y lado repite el anterior (eslabones_imputados). Tipo = promedio
# geométrico de sus subtipos; Canasta = pesos ENGHo. sin / con = evolución relativa (comparable con la TPD).
def _indice_fe(_y, _item, _t, _T):
    # mínimos cuadrados de y = mu(item) + tau(t) con tau = 0 en el primer mes con datos (within de ítem, exacto)
    _iid, _ = pd.factorize(_item)
    _ni = np.bincount(_iid)
    _yd = _y - (np.bincount(_iid, weights=_y) / _ni)[_iid]
    _M = np.zeros((len(_ni), _T)); _M[_iid, _t] = 1.0 / _ni[_iid]
    _con = np.unique(_t)
    _cols = _con[1:]
    _tau = np.full(_T, np.nan); _tau[_con[0]] = 0.0
    if len(_cols):
        _D = (np.arange(_T)[None, _cols] == _t[:, None]).astype(float) - _M[_iid][:, _cols]
        _tau[_cols] = np.linalg.lstsq(_D, _yd, rcond=None)[0]
    return _tau

_pm = (datos_dia.merge(_U8[_sk + ['suc_key']], on=_sk)
       .groupby(['suc_key','mes','tipo','subtipo','rol','producto'], as_index=False)['precio_100'].median())
_MS = sorted(_pm['mes'].unique())
_pm['_i'] = _pm['mes'].map({_m: _i for _i, _m in enumerate(_MS)})
_filas = []
for (_tp, _st, _rl), _x in _pm.groupby(['tipo','subtipo','rol']):
    _tau = _indice_fe(np.log(_x['precio_100'].to_numpy(float)), (_x['suc_key'] + '|' + _x['producto'].astype(str)).to_numpy(),
                      _x['_i'].to_numpy(), len(_MS))
    _imp = np.isnan(_tau)
    _tau = pd.Series(_tau).ffill().bfill().to_numpy()
    _filas += [{'tipo': _tp, 'subtipo': _st, 'rol': _rl, 'mes': _m, '_tau': _tau[_i], 'imputado': bool(_imp[_i])}
               for _i, _m in enumerate(_MS)]
_ix = pd.DataFrame(_filas)
indices_lados = pd.DataFrame(columns=['mes','nivel','indice_con_tacc','indice_sin_tacc','sin_sobre_con','eslabones_imputados'])
indices_lados_anual = pd.DataFrame(columns=['nivel','anio','indice_con_tacc','indice_sin_tacc','sin_sobre_con'])
if len(_ix):
    # base común: el primer mes = 100 en todos los subtipos (si un subtipo y lado empieza después, su primer mes)
    _ix['_tau'] = _ix['_tau'] - _ix.groupby(['tipo','subtipo','rol'])['_tau'].transform('first')
    _it = _ix.groupby(['tipo','rol','mes'])['_tau'].mean().unstack('rol')
    _ni = _ix[_ix['imputado']].groupby(['tipo','mes']).size()
    indices_lados = pd.DataFrame({'mes': _it.index.get_level_values('mes'), 'nivel': _it.index.get_level_values('tipo'),
                                  'indice_con_tacc': 100 * np.exp(_it['tacc'].to_numpy()),
                                  'indice_sin_tacc': 100 * np.exp(_it['sin'].to_numpy())})
    _wt = indices_lados['nivel'].map(W_TIPO)
    _can = (indices_lados.assign(_c=indices_lados['indice_con_tacc'] * _wt, _s=indices_lados['indice_sin_tacc'] * _wt, _w=_wt)
            .groupby('mes')[['_c','_s','_w']].sum())
    _can = pd.DataFrame({'mes': _can.index, 'nivel': 'Canasta', 'indice_con_tacc': (_can['_c'] / _can['_w']).to_numpy(),
                         'indice_sin_tacc': (_can['_s'] / _can['_w']).to_numpy()})
    indices_lados = pd.concat([_can, indices_lados], ignore_index=True)
    indices_lados['sin_sobre_con'] = 100 * indices_lados['indice_sin_tacc'] / indices_lados['indice_con_tacc']
    indices_lados['eslabones_imputados'] = [int(_ni.get((_n, _m), 0)) if _n != 'Canasta'
                                            else int(_ni[_ni.index.get_level_values('mes') == _m].sum()) if len(_ni) else 0
                                            for _n, _m in zip(indices_lados['nivel'], indices_lados['mes'])]
    # IPC del INDEC (IPC_XLSX de la CELDA 1, en SEPA_DIR: nivel general y alimentos y bebidas no alcohólicas), misma base
    IPC_PATH = Path(globals().get('IPC_XLSX', 'IPC.xlsx'))
    IPC_PATH = IPC_PATH if IPC_PATH.is_absolute() else SEPA_DIR / IPC_PATH
    try:
        _ipc = pd.read_excel(IPC_PATH)
        _ipc['mes'] = pd.to_datetime(_ipc.iloc[:, 0]).dt.strftime('%Y-%m')
        _ca = next(_c for _c in _ipc.columns if str(_c).lower().startswith('alimentos'))
        _cg = next(_c for _c in _ipc.columns if 'general' in str(_c).lower())
        _ipc = _ipc.set_index('mes')[[_ca, _cg]].astype(float)
        if _MS[0] in _ipc.index:
            _ipc = 100 * _ipc / _ipc.loc[_MS[0]]
            _ipc.columns = ['ipc_alimentos', 'ipc_nivel_general']
            indices_lados = indices_lados.merge(_ipc, left_on='mes', right_index=True, how='left')
            indices_lados.loc[indices_lados['nivel'] != 'Canasta', ['ipc_alimentos','ipc_nivel_general']] = np.nan
            print(f'  IPC del INDEC: {IPC_PATH.name} hasta {_ipc.index.max()}')
        else:
            print(f'  (IPC del INDEC sin el mes {_MS[0]}: no se compara)')
    except Exception as _e:
        print(f'  (sin IPC del INDEC: {IPC_PATH.name} no está o no se pudo leer: {type(_e).__name__})')
    indices_lados['anio'] = indices_lados['mes'].str[:4]
    _num = [_c for _c in indices_lados.columns if _c.startswith(('indice_','ipc_'))]
    indices_lados_anual = indices_lados.groupby(['nivel','anio'])[_num].mean().reset_index()
    indices_lados_anual['sin_sobre_con'] = 100 * indices_lados_anual['indice_sin_tacc'] / indices_lados_anual['indice_con_tacc']
    indices_lados = indices_lados.drop(columns='anio')
    _ci = indices_lados[indices_lados['nivel'] == 'Canasta'].set_index('mes')
    print(f'\n=== Índices de cada lado (efectos fijos de ítem y mes; base {_MS[0]} = 100) ===')
    print(indices_lados_anual[indices_lados_anual['nivel'] == 'Canasta'].drop(columns='nivel').round(1).to_string(index=False))
    if 'serie_tpd' in globals() and len(serie_tpd):
        _tp_ = serie_tpd.set_index('mes')['brecha_canasta_tpd_todas'].reindex(_ci.index)
        _rel_tpd = 100 * (1 + _tp_ / 100) / (1 + _tp_.iloc[0] / 100)
        if _rel_tpd.notna().sum() > 3:
            print(f'  sin / con contra la TPD de todas las sucursales (primer mes = 100): correlación '
                  f'{_ci["sin_sobre_con"].corr(_rel_tpd):.3f}; último mes {_ci["sin_sobre_con"].iloc[-1]:.1f} contra '
                  f'{_rel_tpd.iloc[-1]:.1f}')

# ── 3. Disponibilidad ────────────────────────────────────────────────────────
# De las sucursal-meses que venden un tipo con TACC (productos de la canasta), la parte que vende también su versión sin
# TACC; ponderada = promedio de los tipos con los pesos ENGHo. Últimos meses (grupos) y mes a mes (país).
_dd8 = datos_dia.merge(_U8, on=_sk)
_lad = (_dd8.groupby(['suc_key','mes','tipo','rol']).size().unstack('rol', fill_value=0) > 0).reset_index()
if not {'tacc','sin'} <= set(_lad.columns):
    _lad = _lad.assign(tacc=_lad.get('tacc', False), sin=_lad.get('sin', False))
_lad = _lad[_lad['tacc']].merge(_U8[['suc_key','region','PROVINCIA_NORM','empresa','cadena']], on='suc_key')
_lad['sin'] = _lad['sin'].astype(float)

def _disp(_x, _col, _nombre):
    if not len(_x):
        return pd.DataFrame()
    _k = [_col] if _col else []
    _t = _x.groupby(_k + ['tipo']).agg(_d=('sin','mean'), _n=('sin','size')).reset_index()
    _pv = _t.pivot_table(index=_k or None, columns='tipo', values='_d') if _k else _t.set_index('tipo')['_d'].to_frame().T
    _pn = _t.groupby(_k)['_n'].sum() if _k else pd.Series([_t['_n'].sum()])
    _pv = _pv.reindex(columns=TIPOS_ORD)
    _w = _W8.reindex(TIPOS_ORD)
    _o = pd.DataFrame({'agrupacion': _nombre, 'grupo': _pv.index if _k else ['País']})
    _o['disponibilidad_ponderada_pct'] = (100 * (_pv * _w).sum(axis=1) / (_pv.notna() * _w).sum(axis=1)).to_numpy()
    for _c in TIPOS_ORD:
        _o[f'disponibilidad_{_c}_pct'] = (100 * _pv[_c]).to_numpy()
    _o['sucursal_meses_con_tacc'] = (_pn.reindex(_pv.index).to_numpy() if _k else _pn.to_numpy())
    return _o

_lv = _lad[_lad['mes'].isin(_mv)]
# dos medidas: por sucursal-mes (qué tan seguido está) y por sucursal (si estuvo alguna vez en los últimos meses)
_lvs = _lv.groupby(['suc_key','tipo','region','PROVINCIA_NORM','empresa','cadena'], as_index=False)['sin'].max()
disponibilidad = pd.concat([_d.assign(medida=_med) for _med, _src in (('sucursal-meses', _lv), ('sucursales (alguna vez)', _lvs))
                            for _d in (_disp(_src, None, 'País'), _disp(_src, 'region', 'Región'),
                                       _disp(_src, 'PROVINCIA_NORM', 'Provincia'), _disp(_src, 'empresa', 'Empresa'),
                                       _disp(_src, 'cadena', 'Cadena'))], ignore_index=True)
if len(disponibilidad):
    disponibilidad = disponibilidad.rename(columns={'sucursal_meses_con_tacc': 'casos_con_tacc'})
    disponibilidad.insert(2, 'medida', disponibilidad.pop('medida'))
disponibilidad_mensual = (_lad.groupby(['mes','tipo'])['sin'].mean().mul(100).unstack('tipo').reindex(columns=TIPOS_ORD)
                          .add_prefix('disponibilidad_').add_suffix('_pct').reset_index())
if len(disponibilidad):
    print(f'\n=== Disponibilidad sin TACC donde se vende el tipo con TACC (últimos {len(_mv)} meses) ===')
    print(disponibilidad[disponibilidad['agrupacion'].isin(['País','Región'])]
          .pivot_table(index=['agrupacion','grupo'], columns='medida', values='disponibilidad_ponderada_pct').round(1).to_string())

# ── 4. Intervalos de confianza (bootstrap por sucursal y por empresa) ─────────
# Por sucursal: se remuestrean SUCURSALES con reposición (todas sus sucursal-meses y subtipos juntos, porque los precios
# de una sucursal están correlacionados) y se recalcula todo: la brecha nacional y la de cada grupo con la misma canasta
# (CELDA 8). Mide la precisión con ESTAS cadenas. Por empresa: las cadenas fijan el precio para todas sus sucursales (en
# la mayoría de los subtipos la empresa explica más de la mitad de la variación entre sucursales y el desvío dentro de
# cada empresa es chico, hoja Varianza_empresa), así que sus sucursales no son observaciones independientes: se remuestrean EMPRESAS con reposición (con todas sus sucursales) y se recalculan el país,
# las regiones y las provincias. Es el intervalo para generalizar a otras cadenas posibles; no aplica a empresas y
# cadenas (cada una es un solo grupo) ni a los grupos con una sola empresa, y con pocas empresas (n_empresas) es
# aproximado (los percentiles de un bootstrap con pocos grupos tienden a quedarse cortos). IC 95% = percentiles 2,5 y
# 97,5 de las BOOT_B réplicas; la diferencia con la nacional se calcula en cada réplica (significativa = su IC no
# incluye el 0).
_GRUPOS_IC = [('Región', 'region', brecha_region, 'region'), ('Provincia', 'PROVINCIA_NORM', brecha_prov, 'provincia'),
              ('Empresa', 'empresa', brecha_empresa, 'empresa'), ('Cadena', 'cadena', brecha_cadena, 'cadena')]
_btb = bt_v[['suc_key','mes','tipo','subtipo','tacc','sin','brecha_pct','brecha_min','region','PROVINCIA_NORM',
             'empresa','cadena']].reset_index(drop=True)

def _bootstrap_directo(_col, _seed, _grupos, _B):
    # el cálculo directo: remuestrea con reposición los valores de _col (sucursal o empresa), cada uno con todas sus
    # filas, arma la tabla de la réplica y recalcula la brecha del país (_canasta_nac) y la de los _grupos con la misma
    # canasta (_canasta de la CELDA 8); la misma sucursal sorteada dos veces cuenta como dos
    _us = _btb[_col].unique()
    _ix = _btb.groupby(_col).indices
    _pos = [_ix[_u] for _u in _us]
    _rg = np.random.default_rng(_seed)
    _out = []
    for _b in range(int(_B) if len(_us) > 1 else 0):
        _dr = _rg.integers(0, len(_us), len(_us))
        _db = _btb.iloc[np.concatenate([_pos[_j] for _j in _dr])].copy()
        _db['suc_key'] = (_db['suc_key'].to_numpy() + '#'
                          + np.repeat(np.arange(len(_dr)), [len(_pos[_j]) for _j in _dr]).astype(str))
        _nb, _ = _canasta_nac(_db)
        _out.append(('País', 'País', _b, _nb, _nb))
        for _gt, _gc, _, _ in _grupos:
            _cg = _canasta(_db, [_gc], [])
            for _g, _v in zip(_cg[_gc], _cg['brecha_canasta']):
                _out.append((_gt, _g, _b, _v, _nb))
    return pd.DataFrame(_out, columns=['agrupacion','grupo','replica','brecha','nacional'])

def _seg_prep(_codes, _nseg, _unit, _store, _n_store):
    # filas ordenadas por segmento (código 0.._nseg-1; -1 = afuera) y brecha, con su unidad de remuestreo; pares
    # segmento-sucursal
    _ok = _codes >= 0
    _c, _v = _codes[_ok].astype(np.int64), _btb['brecha_pct'].to_numpy(float)[_ok]
    _o = np.lexsort((_v, _c))
    _pr = np.unique(_c * _n_store + _store[_ok])
    return {'seg': _c[_o], 'val': _v[_o], 'unit': _unit[_ok][_o], 'nseg': int(_nseg),
            'pseg': _pr // _n_store, 'pstore': _pr % _n_store}

def _seg_med(_p, _mu, _ms):
    # mediana de cada segmento en la réplica = mediana ponderada por las veces que salió cada fila (pesos enteros: la de
    # la tabla con las filas repetidas, con el promedio de los dos del medio si son pares) y sus sucursales (cada copia
    # cuenta como una)
    _w = _mu[_p['unit']]
    _k = _w > 0
    _sg, _vl, _w = _p['seg'][_k], _p['val'][_k], _w[_k]
    _n = _p['nseg']
    _med = np.full(_n, np.nan)
    if len(_w):
        _cw = np.cumsum(_w)
        _ini = np.searchsorted(_sg, np.arange(_n), 'left')
        _fin = np.searchsorted(_sg, np.arange(_n), 'right')
        _hay = _fin > _ini
        _obj = np.where(_ini > 0, _cw[np.maximum(_ini - 1, 0)], 0.0) + np.bincount(_sg, weights=_w, minlength=_n) / 2
        _i = np.minimum(np.searchsorted(_cw, _obj, 'left'), len(_cw) - 1)
        _par = _hay & (_cw[_i] == _obj) & (_i + 1 < _fin)
        _m = np.where(_par, (_vl[_i] + _vl[np.minimum(_i + 1, len(_vl) - 1)]) / 2, _vl[_i])
        _med = np.where(_hay, _m, np.nan)
    return _med, np.bincount(_p['pseg'], weights=_ms[_p['pstore']], minlength=_n)

def _bootstrap(_col, _seed, _grupos, _verificar=3):
    # lo mismo que _bootstrap_directo (las mismas réplicas: misma semilla y sorteos) sin armar la tabla de cada réplica:
    # cada mediana es una mediana ponderada por las veces que salió cada fila. Las primeras _verificar réplicas se
    # comparan con el cálculo directo (si difieren, para: no se exporta un intervalo mal calculado)
    _uc, _us = pd.factorize(_btb[_col])                       # en orden de aparición, como unique()
    _sc, _ss = pd.factorize(_btb['suc_key'])
    _u_suc = np.zeros(len(_ss), np.int64); _u_suc[_sc] = _uc  # unidad de cada sucursal
    _tsc = _btb.groupby(['tipo','subtipo'], sort=False).ngroup().to_numpy()
    _nts = int(_tsc.max()) + 1
    _tipo_ts = _btb.groupby(_tsc)['tipo'].first().reindex(range(_nts)).to_numpy()
    _cols_tipo = [(float(_W8[_tp]), np.where(_tipo_ts == _tp)[0]) for _tp in pd.unique(_tipo_ts) if _tp in _W8.index]
    def _canasta_de(_L):
        # _L: log(1 + brecha / 100) de cada tipo-subtipo (filas: grupos; NaN = el subtipo no está en el país):
        # tipo = promedio de sus subtipos, canasta = sum_k w_k exp(tipo k) / sum_k w_k (tipos presentes) - 1
        _L = np.atleast_2d(_L)
        _num, _den = np.zeros(len(_L)), np.zeros(len(_L))
        for _wk, _cs in _cols_tipo:
            _x = _L[:, _cs]
            _ok = ~np.isnan(_x[0]) if len(_x) else np.zeros(0, bool)
            if _ok.any():
                _num += _wk * np.exp(_x[:, _ok].mean(axis=1)); _den += _wk
        return np.where(_den > 0, (_num / np.where(_den > 0, _den, 1) - 1) * 100, np.nan)
    _pn = _seg_prep(_tsc, _nts, _uc, _sc, len(_ss))
    _pg = []
    for _gt, _gc, _, _ in _grupos:
        _gcod, _gval = pd.factorize(_btb[_gc])
        _pg.append((_gt, _gval, _seg_prep(np.where(_gcod >= 0, _gcod * _nts + _tsc, -1), len(_gval) * _nts, _uc, _sc,
                                          len(_ss))))
    _rg = np.random.default_rng(_seed)
    _out = []
    for _b in range(int(BOOT_B) if len(_us) > 1 else 0):
        _dr = _rg.integers(0, len(_us), len(_us))
        _mu = np.bincount(_dr, minlength=len(_us)).astype(float)
        _ms = _mu[_u_suc]
        _ln = np.log1p(_seg_med(_pn, _mu, _ms)[0] / 100)
        _nb = float(_canasta_de(_ln)[0])
        _out.append(('País', 'País', _b, _nb, _nb))
        for _gt, _gval, _p in _pg:
            _mg, _ng = _seg_med(_p, _mu, _ms)
            _mg, _ng = _mg.reshape(-1, _nts), _ng.reshape(-1, _nts)
            _own = (_ng >= globals().get('MIN_SUC_SUBTIPO', 1)) & ~np.isnan(_mg)
            # el subtipo con pocas sucursales en el grupo toma la brecha del país en la réplica (como _agg_tipo)
            _V = np.where(_own, np.log1p(_mg / 100), _ln[None, :])
            _vg = _canasta_de(_V)
            for _j in np.where(_own.any(axis=1))[0]:          # un grupo sin ningún subtipo propio es el país
                _out.append((_gt, _gval[_j], _b, float(_vg[_j]), _nb))
    _r = pd.DataFrame(_out, columns=['agrupacion','grupo','replica','brecha','nacional'])
    if _verificar and len(_r):
        _d = _bootstrap_directo(_col, _seed, _grupos, min(int(_verificar), int(BOOT_B)))
        _c = _r[_r['replica'] < _verificar].merge(_d, on=['agrupacion','grupo','replica'], how='outer', indicator=True)
        _dif = float(np.nanmax(np.abs(_c['brecha_x'] - _c['brecha_y']))) if len(_c) else 0.0
        if (_c['_merge'] != 'both').any() or not _dif < 1e-8:
            raise RuntimeError(f'bootstrap por {_col}: el cálculo rápido no da igual al directo en las primeras réplicas '
                               f'(dif. máx. {_dif:.2e}; grupos de un solo lado: {int((_c["_merge"] != "both").sum())})')
    return _r

def _cuantiles(_r, _suf=''):
    return _r.assign(_d=_r['brecha'] - _r['nacional']).groupby(['agrupacion','grupo']).agg(**{
        f'ic95_inf{_suf}': ('brecha', lambda _x: _x.quantile(.025)), f'ic95_sup{_suf}': ('brecha', lambda _x: _x.quantile(.975)),
        f'dif_ic95_inf{_suf}': ('_d', lambda _x: _x.quantile(.025)), f'dif_ic95_sup{_suf}': ('_d', lambda _x: _x.quantile(.975)),
        f'replicas{_suf}': ('brecha', 'size')}).reset_index()

_rp = _bootstrap('suc_key', BOOT_SEED, _GRUPOS_IC)
_rpe = _bootstrap('empresa', BOOT_SEED + 1, [_x for _x in _GRUPOS_IC if _x[0] in ('Región', 'Provincia')])
_ne_g = {_gt: bt_v.groupby(_gc)['empresa'].nunique() for _gt, _gc, _, _ in _GRUPOS_IC}
_filas = [{'agrupacion': 'País', 'grupo': 'País', 'brecha_canasta': _c_ref, 'n_sucursales': _btb['suc_key'].nunique(),
           'n_empresas': _btb['empresa'].nunique(), 'confiable': True}]
for _gt, _gc, _tab, _gt_col in _GRUPOS_IC:
    for _r in _tab.itertuples(index=False):
        _filas.append({'agrupacion': _gt, 'grupo': getattr(_r, _gt_col), 'brecha_canasta': _r.brecha_canasta,
                       'n_sucursales': _r.n_sucursales, 'n_empresas': int(_ne_g[_gt].get(getattr(_r, _gt_col), 0)),
                       'confiable': bool(_r.confiable)})
ic_grupos = pd.DataFrame(_filas)
if len(_rp):
    ic_grupos = ic_grupos.merge(_cuantiles(_rp), on=['agrupacion','grupo'], how='left')
    ic_grupos['dif_vs_pais_pp'] = ic_grupos['brecha_canasta'] - _c_ref
    ic_grupos['difiere_del_pais'] = (ic_grupos['dif_ic95_inf'] > 0) | (ic_grupos['dif_ic95_sup'] < 0)
    _pais = ic_grupos['agrupacion'] == 'País'
    ic_grupos.loc[_pais, ['dif_vs_pais_pp','dif_ic95_inf','dif_ic95_sup']] = np.nan
    ic_grupos.loc[_pais, 'difiere_del_pais'] = False
    if len(_rpe):
        ic_grupos = ic_grupos.merge(_cuantiles(_rpe, '_empresa'), on=['agrupacion','grupo'], how='left')
        _ce_ = [_c for _c in ic_grupos.columns if _c.endswith('_empresa') and _c != 'n_empresas']
        ic_grupos.loc[ic_grupos['n_empresas'] < 2, _ce_] = np.nan          # con una sola empresa no dice nada
        ic_grupos.loc[_pais, ['dif_ic95_inf_empresa','dif_ic95_sup_empresa']] = np.nan
        _de = (ic_grupos['dif_ic95_inf_empresa'] > 0) | (ic_grupos['dif_ic95_sup_empresa'] < 0)
        ic_grupos['difiere_del_pais_empresa'] = np.where(ic_grupos['ic95_inf_empresa'].notna(), _de, None)
        ic_grupos.loc[_pais, 'difiere_del_pais_empresa'] = False
    _icp = ic_grupos.iloc[0]
    print(f'\n=== Intervalos de confianza ({int(BOOT_B)} réplicas): país {_icp["brecha_canasta"]:+.1f}%; IC 95% por sucursal '
          f'{_icp["ic95_inf"]:+.1f}% a {_icp["ic95_sup"]:+.1f}%'
          + (f', por empresa {_icp["ic95_inf_empresa"]:+.1f}% a {_icp["ic95_sup_empresa"]:+.1f}% '
             f'({int(_icp["n_empresas"])} empresas)' if pd.notna(_icp.get('ic95_inf_empresa')) else '') + ' ===')
    _cf = ic_grupos[(ic_grupos['agrupacion'].isin(['Región','Empresa'])) & ic_grupos['confiable']]
    print(_cf[[_c for _c in ('agrupacion','grupo','brecha_canasta','ic95_inf','ic95_sup','ic95_inf_empresa','ic95_sup_empresa',
                             'dif_vs_pais_pp','difiere_del_pais','difiere_del_pais_empresa') if _c in _cf.columns]]
          .round(1).to_string(index=False))

# ── 5. Competencia local y concentración por sucursal ─────────────────────────
# Para cada sucursal del universo con coordenadas: sucursales y empresas a <= RADIO_COMPETENCIA_KM (incluida ella), empresas
# rivales y HHI local de empresas (cuota = sucursales en el radio). Complementa al HHI del departamento (CELDA 8), que
# depende de límites administrativos.
_cg8 = suc_geo[~suc_geo['id_comercio'].isin(CADENAS_FILTRAR)].dropna(subset=['sucursales_latitud','sucursales_longitud'])
_cg8 = _cg8.drop_duplicates('suc_key').reset_index(drop=True)
_lat = np.radians(_cg8['sucursales_latitud'].to_numpy(float)); _lon = np.radians(_cg8['sucursales_longitud'].to_numpy(float))
_emp_c, _emp_u = pd.factorize(_cg8['empresa'].fillna('Otra'))
_oh = np.zeros((len(_cg8), len(_emp_u))); _oh[np.arange(len(_cg8)), _emp_c] = 1
_ns, _ne, _hh = np.zeros(len(_cg8)), np.zeros(len(_cg8)), np.zeros(len(_cg8))
for _i0 in range(0, len(_cg8), 400):
    _sl = slice(_i0, _i0 + 400)
    _a = (np.sin((_lat[_sl, None] - _lat[None, :]) / 2) ** 2
          + np.cos(_lat[_sl, None]) * np.cos(_lat[None, :]) * np.sin((_lon[_sl, None] - _lon[None, :]) / 2) ** 2)
    _cerca = (2 * 6371 * np.arcsin(np.sqrt(np.clip(_a, 0, 1)))) <= RADIO_COMPETENCIA_KM
    _cnt = _cerca.astype(float) @ _oh
    _ns[_sl] = _cnt.sum(axis=1); _ne[_sl] = (_cnt > 0).sum(axis=1)
    _hh[_sl] = ((_cnt / _ns[_sl, None]) ** 2).sum(axis=1)
competencia_local = _cg8[['suc_key','cadena','empresa','region','PROVINCIA_NORM','departamento_id','departamento']].copy()
competencia_local['sucursales_en_radio'] = _ns.astype(int)
competencia_local['empresas_en_radio'] = _ne.astype(int)
competencia_local['empresas_rivales_en_radio'] = (_ne - 1).astype(int)
competencia_local['hhi_local'] = _hh
_hd = concentracion.set_index('departamento_id')['hhi'] if len(concentracion) else pd.Series(dtype=float)
competencia_local['hhi_departamento'] = competencia_local['departamento_id'].map(_hd)
_b12 = (brecha_suc_mes[brecha_suc_mes['mes'].isin(_mv)].groupby('suc_key')
        .agg(brecha_comparable_mediana=('brecha_comparable','median'), peso_propio_pct=('peso_propio_pct','mean')))
competencia_local = competencia_local.merge(_b12, on='suc_key', how='left')

def _ols_cluster(_y, _X, _cls, _w=None):
    # mínimos cuadrados (ponderados) con errores agrupados (CR1 con G/(G-1)) por cada agrupación de la lista _cls (por
    # departamento, por empresa...); _X ya sin columnas constantes. Devuelve beta y, por agrupación, (errores, grupos);
    # None si la matriz es singular o la primera agrupación tiene un solo grupo
    from scipy import sparse as _sps
    _w = np.ones(len(_y)) if _w is None else _w
    _xtwx = _X.T @ (_X * _w[:, None])
    try:
        _bread = np.linalg.inv(_xtwx)
    except np.linalg.LinAlgError:
        return None
    _beta = _bread @ (_X.T @ (_w * _y))
    _u = (_w * (_y - _X @ _beta))[:, None] * _X
    _se = []
    for _cl in _cls:
        _gid, _gn = pd.factorize(_cl)
        _G = len(_gn)
        if _G < 2:
            _se.append((np.full(_X.shape[1], np.nan), _G))
            continue
        _sc = _sps.csr_matrix((np.ones(len(_gid)), (_gid, np.arange(len(_gid)))), shape=(_G, len(_gid))) @ _u
        _V = _G / (_G - 1) * _bread @ (_sc.T @ _sc) @ _bread
        _se.append((np.sqrt(np.clip(np.diag(_V), 0, None)), _G))
    if _se[0][1] < 2:
        return None
    return _beta, _se

def _dummies(_s, _base=None):
    _s = pd.Series(_s).astype(str)
    _base = _base if _base is not None else _s.value_counts().idxmax()
    _cats = [_c for _c in sorted(_s.unique()) if _c != _base]
    return np.column_stack([(_s == _c).to_numpy(float) for _c in _cats]) if _cats else np.zeros((len(_s), 0)), _cats, _base

from math import erf as _erf
_pval = lambda _z: float(2 * (1 - 0.5 * (1 + _erf(abs(_z) / np.sqrt(2))))) if _z == _z else float('nan')

# concentración a nivel sucursal: log(1 + brecha comparable) de las sucursales con >= 50% del peso medido en ellas, y
# el nivel de cada lado (precio de la sucursal / mediana nacional del subtipo en el mes, promedio de logs)
_nac_lado = bt_v.groupby(['mes','subtipo'])[['tacc','sin']].median()
_lv8 = bt_v.join(_nac_lado, on=['mes','subtipo'], rsuffix='_nac')
_lv8 = (_lv8.assign(_lc=np.log(_lv8['tacc'] / _lv8['tacc_nac']), _ls=np.log(_lv8['sin'] / _lv8['sin_nac']))
        .groupby('suc_key')[['_lc','_ls']].mean())
_cs8 = competencia_local.join(_lv8, on='suc_key')
_cs8 = _cs8[(_cs8['peso_propio_pct'] >= 50) & _cs8['brecha_comparable_mediana'].notna()
            & _cs8['hhi_departamento'].notna() & (_cs8['region'] != 'Sin región')].copy()
_cs8['_y'] = np.log1p(_cs8['brecha_comparable_mediana'] / 100)
_emp_n = _cs8['empresa'].value_counts()
_cs8['_emp'] = _cs8['empresa'].where(_cs8['empresa'].map(_emp_n) >= 20, 'Otras')
_filas = []
for _dep, _ydesc in (('_y', 'brecha de la canasta comparable (log 1 + brecha)'), ('_lc', 'nivel con TACC (log, vs nacional)'),
                     ('_ls', 'nivel sin TACC (log, vs nacional)')):
    for _med, _mdesc, _esc in (('hhi_departamento', 'HHI del departamento', 0.1), ('hhi_local', f'HHI local ({RADIO_COMPETENCIA_KM} km)', 0.1),
                               ('empresas_rivales_en_radio', f'empresas rivales a <= {RADIO_COMPETENCIA_KM} km', 1.0)):
        for _ctrl in ('ninguno', 'empresa', 'empresa y región'):
            _x = _cs8.dropna(subset=[_dep, _med])
            if len(_x) < 30:
                continue
            _cols = [np.ones(len(_x)), _x[_med].to_numpy(float)]
            if _ctrl != 'ninguno':
                _cols.append(_dummies(_x['_emp'])[0])
            if _ctrl == 'empresa y región':
                _cols.append(_dummies(_x['region'])[0])
            _X = np.column_stack(_cols)
            _r = _ols_cluster(_x[_dep].to_numpy(float), _X, [_x['departamento_id'].astype(str).to_numpy(),
                                                             _x['empresa'].astype(str).to_numpy()])
            if _r is None:
                continue
            _bt_, ((_se_, _G), (_see, _Ge)) = _r
            _c, _s, _s2 = _bt_[1] * _esc, _se_[1] * _esc, _see[1] * _esc
            _filas.append({'variable': _ydesc, 'medida': _mdesc, 'por': f'+{_esc:g}', 'controles': _ctrl,
                           'coef_log': _c, 'efecto_pct': 100 * np.expm1(_c), 'ic95_inf_pct': 100 * np.expm1(_c - 1.96 * _s),
                           'ic95_sup_pct': 100 * np.expm1(_c + 1.96 * _s), 'p_valor': _pval(_c / _s if _s > 0 else float('nan')),
                           'ic95_inf_pct_empresa': 100 * np.expm1(_c - 1.96 * _s2),
                           'ic95_sup_pct_empresa': 100 * np.expm1(_c + 1.96 * _s2),
                           'p_valor_empresa': _pval(_c / _s2 if _s2 > 0 else float('nan')),
                           'sucursales': len(_x), 'departamentos': _G, 'empresas': _Ge})
concentracion_modelos = pd.DataFrame(_filas)
if len(concentracion_modelos):
    print(f'\n=== Concentración: regresiones por sucursal (errores agrupados por departamento y, aparte, por empresa) ===')
    _cm = concentracion_modelos[concentracion_modelos['variable'].str.startswith('brecha')]
    print(_cm[['medida','controles','efecto_pct','ic95_inf_pct','ic95_sup_pct','p_valor','p_valor_empresa','sucursales']]
          .round(3).to_string(index=False))

# ── 6. Empresas: composición de cada universo, variación entre sucursales y surtido ──
# Composicion_empresas: de las celdas (sucursal × mes × subtipo con los dos lados) de cada universo y período, cuántas
# son de cada empresa. En todas las sucursales la composición cambia con los años (las que entran y salen del SEPA o
# cambian de surtido); en el panel balanceado, mucho menos: para la evolución, la serie del panel.
_filas = []
for _u, _src in (('todas las sucursales', bt_sub), ('panel balanceado', bt_bal)):
    _x = _src.assign(_sm=_src['suc_key'] + '|' + _src['mes'], anio=_src['mes'].str[:4])
    for _per, _xx in ([(_a, _x[_x['anio'] == _a]) for _a in sorted(_x['anio'].unique())]
                      + [(f'últimos {len(_mv)} meses ({VENTANA_TXT})', _x[_x['mes'].isin(_mv)])]):
        if not len(_xx):
            continue
        _c = _xx.groupby('empresa').agg(sucursales=('suc_key','nunique'), sucursal_meses=('_sm','nunique'),
                                        celdas=('brecha_pct','size'))
        _c['pct_sucursal_meses'] = 100 * _c['sucursal_meses'] / _c['sucursal_meses'].sum()
        _c['pct_celdas'] = 100 * _c['celdas'] / _c['celdas'].sum()
        _filas.append(_c.reset_index().assign(universo=_u, periodo=_per))
composicion_empresas = (pd.concat(_filas, ignore_index=True)[['universo','periodo','empresa','sucursales','sucursal_meses',
                                                               'celdas','pct_sucursal_meses','pct_celdas']]
                        if _filas else pd.DataFrame(columns=['universo','periodo','empresa']))

# Varianza_empresa: por subtipo (últimos meses), brecha de cada sucursal = promedio de log(1 + brecha) en sus meses; qué
# parte de su variación entre sucursales explica la empresa, la región y las dos juntas (R² de mínimos cuadrados con
# indicadoras) y el desvío dentro de las empresas. Canasta: la brecha comparable (mediana de la ventana) de las
# sucursales con >= 50% del peso medido en ellas. Un R² de la empresa alto dice que la cadena fija el precio para todas
# sus sucursales: la unidad de decisión es la empresa (IC por empresa en IC_grupos; errores agrupados por empresa en
# Hedonica_grupos y Concentracion_modelos).
def _r2(_y, *_gs):
    _X = np.column_stack([np.ones(len(_y))] + [pd.get_dummies(pd.Series(_g).astype(str), drop_first=True).to_numpy(float)
                                               for _g in _gs])
    _e = _y - _X @ np.linalg.lstsq(_X, _y, rcond=None)[0]
    _t = float(((_y - _y.mean()) ** 2).sum())
    return 1 - float((_e ** 2).sum()) / _t if _t > 0 else float('nan')

_vs = (bt_v.assign(_l=np.log1p(bt_v['brecha_pct'] / 100))
       .groupby(['tipo','subtipo','suc_key','empresa','region'], as_index=False)['_l'].mean())
_vc = competencia_local[(competencia_local['peso_propio_pct'] >= 50) & competencia_local['brecha_comparable_mediana'].notna()]
_vc = _vc.assign(tipo='Canasta', subtipo='Canasta comparable', _l=np.log1p(_vc['brecha_comparable_mediana'] / 100))
_filas = []
for (_tp, _st), _x in pd.concat([_vc[_vs.columns], _vs], ignore_index=True).groupby(['tipo','subtipo'], sort=False):
    if len(_x) < 3:
        continue
    _y = _x['_l'].to_numpy(float)
    _ke = _x['empresa'].nunique()
    _ye = _x.groupby('empresa')['_l'].transform('mean').to_numpy(float)
    _filas.append({'tipo': _tp, 'subtipo': _st, 'sucursales': len(_x), 'empresas': _ke,
                   'brecha_mediana_sucursales': 100 * np.expm1(float(np.median(_y))),
                   'desvio_entre_sucursales_log': float(np.std(_y, ddof=1)),
                   'desvio_dentro_de_las_empresas_log': float(np.sqrt(((_y - _ye) ** 2).sum() / max(len(_y) - _ke, 1))),
                   'r2_empresa': _r2(_y, _x['empresa']), 'r2_region': _r2(_y, _x['region']),
                   'r2_empresa_y_region': _r2(_y, _x['empresa'], _x['region'])})
varianza_empresa = pd.DataFrame(_filas)
if len(varianza_empresa):
    print(f'\n=== Variación entre sucursales que explica la empresa (R², últimos {len(_mv)} meses) ===')
    print(varianza_empresa[['tipo','subtipo','sucursales','empresas','r2_empresa','r2_region','r2_empresa_y_region',
                            'desvio_dentro_de_las_empresas_log']].round(3).to_string(index=False))

# Surtido_empresa: por empresa, año y producto de la canasta, de las celdas de la empresa en el subtipo del producto, el %
# en que el producto tiene precio. Las cadenas venden surtidos distintos y cambian con el tiempo: la brecha de una cadena
# compara SUS productos (la hedónica de grupos separa esa parte: efecto_surtido_pct).
_pc8 = (datos_dia.merge(_U8[_sk + ['suc_key','empresa']], on=_sk)[['suc_key','empresa','mes','tipo','subtipo','rol','producto']]
        .drop_duplicates())
_cel8 = bt_sub[['suc_key','mes','tipo','subtipo','empresa']].assign(anio=bt_sub['mes'].str[:4])
_pc8 = _pc8.merge(_cel8.drop(columns='empresa'), on=['suc_key','mes','tipo','subtipo'], how='inner')
_den8 = _cel8.groupby(['empresa','anio','tipo','subtipo']).size().rename('celdas_de_la_empresa')
surtido_empresa = (_pc8.groupby(['empresa','anio','tipo','subtipo','rol','producto']).size().rename('celdas_con_el_producto')
                   .reset_index().join(_den8, on=['empresa','anio','tipo','subtipo']))
surtido_empresa['pct_celdas'] = 100 * surtido_empresa['celdas_con_el_producto'] / surtido_empresa['celdas_de_la_empresa']
surtido_empresa.insert(4, 'lado', surtido_empresa.pop('rol').map({'tacc': 'con TACC', 'sin': 'sin TACC'}))
surtido_empresa.insert(6, 'descripcion', surtido_empresa['producto'].map(lambda _p: EAN_DESC.get(_p, _p)))
surtido_empresa = surtido_empresa.sort_values(['empresa','anio','tipo','subtipo','lado','pct_celdas'],
                                              ascending=[True, True, True, True, True, False]).reset_index(drop=True)
del _pc8, _cel8

# ── 7. Hedónica de grupos (corte transversal de los últimos meses y por año) ──
# ln p(producto, sucursal, mes) = efecto de la celda (sucursal × mes × subtipo) + efecto del producto
#                                 + sinTACC × (región + empresa [+ concentración])
# Con la celda se compara cada sin TACC con los con TACC de su subtipo en el mismo super y mes; con el producto, los
# mismos productos en todos los grupos (el surtido no mueve el resultado). La región y la empresa se controlan entre sí:
# exp(coef) - 1 = cuánto más (o menos) alta es 1 + brecha que en la categoría base, con todo lo demás igual. Pesos: cada
# subtipo como en la canasta (peso ENGHo del tipo / subtipos del tipo), repartido entre sus celdas; en la celda, cada lado
# suma lo mismo. Errores agrupados por departamento (mercado local) y, aparte, por empresa (la cadena fija el precio de
# todas sus sucursales; no aplica a los efectos de empresa). Sin los efectos de producto (modelo "con el surtido", con
# una prima base por subtipo) cada grupo compara SUS productos de cada subtipo: la diferencia con el modelo de los mismos
# productos es la parte del surtido (efecto_surtido_pct). Por año (Hedonica_grupos_anual): el modelo principal y el del
# surtido, con las bases de la ventana.
_MOD_SURTIDO = 'región y empresa, sin efectos de producto (con el surtido de cada grupo)'
_MOD_H = [('base', 'región y empresa'), ('hhi', 'región, empresa y HHI del departamento'),
          ('rivales', f'región, empresa y empresas rivales a <= {RADIO_COMPETENCIA_KM} km'), ('surtido', _MOD_SURTIDO)]

def _hedonica_grupos(_ph, _min_suc_emp=20, _modelos=None, _base_r=None, _base_e=None):
    # _ph: una fila por producto × sucursal × mes con suc_key, mes, subtipo, rol ('tacc'/'sin'), producto, precio_100,
    # w (peso), region, empresa, departamento_id, hhi_departamento y empresas_rivales_en_radio, solo celdas con los dos
    # lados. _modelos: claves de _MOD_H (todos si None); _base_r / _base_e fijan la región y la empresa base (si están).
    # Devuelve la tabla de efectos, la región base y la empresa base.
    _ph = _ph[_ph['w'] > 0].reset_index(drop=True)
    _ph['_cell'] = _ph['suc_key'] + '|' + _ph['mes'] + '|' + _ph['subtipo']
    _ph['_emp'] = _ph['empresa'].where(_ph['empresa'].map(_ph.groupby('empresa')['suc_key'].nunique()) >= _min_suc_emp,
                                       'Otras')
    _y = np.log(_ph['precio_100'].to_numpy(float)); _w = _ph['w'].to_numpy(float)
    _s = (_ph['rol'] == 'sin').to_numpy(float)
    _cid, _ = pd.factorize(_ph['_cell'])
    _wsum = np.bincount(_cid, weights=_w)
    _dm = lambda _v: _v - (np.bincount(_cid, weights=_w * _v) / _wsum)[_cid]
    # productos: una indicadora por producto menos una de referencia por subtipo (dentro de la celda las indicadoras de
    # un subtipo suman 1)
    _pr = _ph[['subtipo','producto']].drop_duplicates().sort_values(['subtipo','producto'])
    _ref_p = set(_pr.groupby('subtipo')['producto'].first())
    _Xp = [_dm((_ph['producto'] == _p).to_numpy(float)) for _p in _pr['producto'] if _p not in _ref_p]
    _Dr, _cr, _br = _dummies(_ph['region'], _base_r if _base_r in set(_ph['region']) else None)
    _De, _ce, _be = _dummies(_ph['_emp'], _base_e if _base_e in set(_ph['_emp'])
                             else ('Carrefour' if 'Carrefour' in set(_ph['_emp']) else None))
    _cl = _ph['departamento_id'].astype(str).where(_ph['departamento_id'].notna(), _ph['suc_key']).to_numpy()
    _cle = _ph['empresa'].astype(str).to_numpy()
    _ok_h = _ph['hhi_departamento'].notna().to_numpy()
    _hc = _ph['hhi_departamento'].fillna(0).to_numpy(float)
    _rv = _ph['empresas_rivales_en_radio'].fillna(0).to_numpy(float)
    _f = []
    for _clave, _mod in _MOD_H:
        if _modelos is not None and _clave not in _modelos:
            continue
        # sin efectos de producto, una prima base por subtipo (sinTACC × subtipo): así la región y la empresa no
        # recogen qué subtipos tiene cada grupo, solo qué productos de cada subtipo (los efectos de producto la incluyen)
        _base_cols = ([_dm(_s * (_ph['subtipo'] == _st).to_numpy(float)) for _st in sorted(_ph['subtipo'].unique())]
                      if _clave == 'surtido' else _Xp)
        _cols = (_base_cols + [_dm(_s * _Dr[:, _j]) for _j in range(_Dr.shape[1])]
                 + [_dm(_s * _De[:, _j]) for _j in range(_De.shape[1])])
        _names = [('Región', _c) for _c in _cr] + [('Empresa', _c) for _c in _ce]
        _mask = np.ones(len(_y), bool)
        if _clave == 'hhi':
            _mask = _ok_h
            _cols.append(_dm(_s * (_hc - _hc[_ok_h].mean()) * 10))
            _names.append(('Concentración', 'HHI del departamento (+0,1)'))
        elif _clave == 'rivales':
            _cols.append(_dm(_s * (_rv - _rv.mean())))
            _names.append(('Concentración', f'una empresa rival más a <= {RADIO_COMPETENCIA_KM} km'))
        if not _mask.any():
            continue
        _r = _ols_cluster(_dm(_y)[_mask], np.column_stack(_cols)[_mask], [_cl[_mask], _cle[_mask]], _w[_mask])
        if _r is None:
            print(f'  (hedónica "{_mod}": matriz singular o un solo departamento, no se estima)')
            continue
        _b_, ((_se_, _G), (_see, _Ge)) = _r
        _k0 = len(_base_cols)
        _cg = _ph.loc[_mask, ['_cell','mes','subtipo','region','_emp']].drop_duplicates('_cell')
        _nst, _nme = _cg['subtipo'].nunique(), _cg['mes'].nunique()
        for _j, (_grp, _nm) in enumerate(_names):
            _c, _sd = _b_[_k0 + _j], _se_[_k0 + _j]
            _sde = float('nan') if _grp == 'Empresa' else _see[_k0 + _j]
            _sel = (_cg['region'] == _nm) if _grp == 'Región' else ((_cg['_emp'] == _nm) if _grp == 'Empresa'
                                                                     else pd.Series(True, index=_cg.index))
            # confiable: el grupo tiene celdas en la mitad de los subtipos o más, cada uno en la mitad de los meses o más
            # (DIA, oct-2026: 3 subtipos en <= 3 meses; su efecto depende de pocos precios)
            _nsg = int((_cg.loc[_sel].groupby('subtipo')['mes'].nunique() >= _nme / 2).sum())
            _f.append({'modelo': _mod, 'grupo': _grp, 'termino': _nm,
                       'celdas_del_grupo': int(_sel.sum()), 'meses_del_grupo': int(_cg.loc[_sel, 'mes'].nunique()),
                       'subtipos_del_grupo': _nsg, 'confiable': bool(_grp == 'Concentración' or _nsg >= _nst / 2),
                       'base': _br if _grp == 'Región' else (_be if _grp == 'Empresa' else ''),
                       'coef_log': _c, 'error_estandar_log': _sd, 'efecto_pct': 100 * np.expm1(_c),
                       'ic95_inf_pct': 100 * np.expm1(_c - 1.96 * _sd), 'ic95_sup_pct': 100 * np.expm1(_c + 1.96 * _sd),
                       'p_valor': _pval(_c / _sd if _sd > 0 else float('nan')),
                       'error_estandar_log_empresa': _sde, 'ic95_inf_pct_empresa': 100 * np.expm1(_c - 1.96 * _sde),
                       'ic95_sup_pct_empresa': 100 * np.expm1(_c + 1.96 * _sde),
                       'p_valor_empresa': _pval(_c / _sde if _sde > 0 else float('nan')),
                       'observaciones': int(_mask.sum()), 'celdas': int(len(np.unique(_cid[_mask]))),
                       'departamentos': _G, 'empresas': _Ge})
    _o = pd.DataFrame(_f)
    if len(_o) and {'región y empresa', _MOD_SURTIDO} <= set(_o['modelo']):
        # descomposición: con el surtido de cada grupo = mismos productos + surtido (en logs)
        _ct = _o[_o['modelo'] == _MOD_SURTIDO].set_index(['grupo','termino'])['coef_log']
        _m0 = (_o['modelo'] == 'región y empresa').to_numpy()
        _cs = _ct.reindex(pd.MultiIndex.from_frame(_o.loc[_m0, ['grupo','termino']])).to_numpy()
        _o['efecto_con_surtido_pct'] = np.nan
        _o['efecto_surtido_pct'] = np.nan
        _o.loc[_m0, 'efecto_con_surtido_pct'] = 100 * np.expm1(_cs)
        _o.loc[_m0, 'efecto_surtido_pct'] = 100 * np.expm1(_cs - _o.loc[_m0, 'coef_log'].to_numpy())
    return _o, _br, _be

def _ph_desde(_d):
    # producto × sucursal × mes de las celdas (sucursal × mes × subtipo) con los dos lados, con su peso, la región, la
    # empresa, el departamento y la concentración de su sucursal
    _p = (_d.merge(_U8, on=_sk)
          .groupby(['suc_key','mes','tipo','subtipo','rol','producto','region','empresa','departamento_id'], as_index=False,
                   dropna=False)['precio_100'].median())
    _p['_cell'] = _p['suc_key'] + '|' + _p['mes'] + '|' + _p['subtipo']
    _p = _p[(_p.groupby('_cell')['rol'].transform('nunique') == 2) & (_p['region'] != 'Sin región')].copy()
    if not len(_p) or _p['_cell'].nunique() <= 50:
        return _p.iloc[0:0]
    _p['w'] = ((1.0 / _p.groupby(['_cell','rol'])['producto'].transform('size')) * _p['subtipo'].map(_SUB_W)
               / _p['subtipo'].map(_p.groupby('subtipo')['_cell'].nunique()))
    return _p.merge(competencia_local[['suc_key','hhi_departamento','empresas_rivales_en_radio']], on='suc_key', how='left')

_ph = _ph_desde(datos_dia[datos_dia['mes'].isin(_mv)])
hedonica_grupos = pd.DataFrame()
hedonica_grupos_anual = pd.DataFrame()
if len(_ph):
    hedonica_grupos, _br, _be = _hedonica_grupos(_ph)
    if len(hedonica_grupos):
        print(f'\n=== Hedónica de grupos (últimos {len(_mv)} meses; base: región {_br}, empresa {_be}) ===')
        print(hedonica_grupos[hedonica_grupos['modelo'] == 'región y empresa'][
            ['grupo','termino','efecto_pct','ic95_inf_pct','ic95_sup_pct','p_valor','p_valor_empresa',
             'efecto_con_surtido_pct','efecto_surtido_pct','subtipos_del_grupo','confiable']].round(3).to_string(index=False))
        _nc = hedonica_grupos[(hedonica_grupos['modelo'] == 'región y empresa') & ~hedonica_grupos['confiable']]
        if len(_nc):
            print(f'  Poco dato (con celdas en menos de la mitad de los subtipos): {", ".join(_nc["termino"])}. Leer con cuidado.')
        print(hedonica_grupos[hedonica_grupos['grupo'] == 'Concentración'][
            ['modelo','efecto_pct','ic95_inf_pct','ic95_sup_pct','p_valor','p_valor_empresa']].round(3).to_string(index=False))
        # por año: los dos modelos de región y empresa, con las mismas bases que la ventana
        _fa = []
        for _an in sorted(datos_dia['mes'].str[:4].unique()):
            _pa = _ph_desde(datos_dia[datos_dia['mes'].str[:4] == _an])
            if len(_pa):
                _ha = _hedonica_grupos(_pa, _modelos=('base', 'surtido'), _base_r=_br, _base_e=_be)[0]
                if len(_ha):
                    _fa.append(_ha.assign(anio=_an))
            del _pa
        if _fa:
            hedonica_grupos_anual = pd.concat(_fa, ignore_index=True)
            hedonica_grupos_anual.insert(0, 'anio', hedonica_grupos_anual.pop('anio'))
            _hb = hedonica_grupos_anual[hedonica_grupos_anual['modelo'] == 'región y empresa']
            print(f'\nPor año (mismos productos; efecto % sobre 1 + brecha contra {_br} y {_be}):')
            print(_hb.pivot_table(index=['grupo','termino'], columns='anio', values='efecto_pct').round(1).to_string())
del _ph

# ── 8. Prima de la misma marca ───────────────────────────────────────────────
# ¿Cuánto de la brecha es la prima sin gluten y cuánto la marca? En las celdas (sucursal × mes × subtipo) donde una MISMA
# marca vende los dos lados (MARCA, CELDA 1; MARCA_EQUIVALENTE une las líneas sin TACC que se venden con otro nombre):
# brecha_misma_marca = mediana $/100 g de sus sin TACC / mediana de sus con TACC - 1, contra la brecha de la canasta en
# las MISMAS celdas (todos los productos del subtipo: el estimador principal). prima_de_marca_pct = mediana por celda de
# (1 + brecha de la canasta) / (1 + brecha de la misma marca) - 1: lo que agrega comparar con productos de otras marcas
# (positivo: los con TACC de la canasta son más baratos que los de esa marca, o sus sin TACC más caros).
# brecha_subtipo_pct = mediana de la brecha del subtipo en todas sus celdas del período. Solo productos de la canasta.
_MARCA_N = {_norm_ean(_e): str(_m).strip().upper() for _e, _m in globals().get('MARCA', {}).items() if _norm_ean(_e) and _m}
_MEQ = {str(_k).strip().upper(): str(_v).strip().upper() for _k, _v in globals().get('MARCA_EQUIVALENTE', {}).items()}

def _prima_marca(_d, _bts, _meses_v, _ventana_txt=''):
    # _d: precios por sucursal × código × mes (suc_key, empresa, mes, tipo, subtipo, rol, producto, marca, precio_100;
    # marca = la de comparación); _bts: la brecha de la canasta de cada celda (suc_key, mes, tipo, subtipo, brecha_pct).
    # Devuelve la tabla por período (los últimos meses y cada año), subtipo y marca.
    _cols = ['periodo','tipo','subtipo','marca','celdas','sucursales','empresas','meses','brecha_misma_marca_pct',
             'brecha_canasta_mismas_celdas_pct','prima_de_marca_pct','brecha_subtipo_pct','productos_con_tacc',
             'productos_sin_tacc']
    _p = (_d[_d['marca'].notna()]
          .groupby(['suc_key','empresa','mes','tipo','subtipo','marca','rol','producto'], as_index=False)['precio_100'].median())
    _m = _p.groupby(['suc_key','empresa','mes','tipo','subtipo','marca','rol'])['precio_100'].median().unstack('rol')
    if not {'tacc','sin'} <= set(_m.columns):
        return pd.DataFrame(columns=_cols)
    _m = _m.dropna(subset=['tacc','sin']).reset_index()
    _m['brecha_misma_marca'] = (_m['sin'] / _m['tacc'] - 1) * 100
    _m = _m.merge(_bts[['suc_key','mes','tipo','subtipo','brecha_pct']], on=['suc_key','mes','tipo','subtipo'], how='inner')
    if not len(_m):
        return pd.DataFrame(columns=_cols)
    _m['_prima'] = 100 * ((1 + _m['brecha_pct'] / 100) / (1 + _m['brecha_misma_marca'] / 100) - 1)
    _filas = []
    for _per, _m1, _m2 in ([(f'últimos {len(_meses_v)} meses ({_ventana_txt})', _m['mes'].isin(_meses_v),
                             _bts['mes'].isin(_meses_v))]
                           + [(_a, _m['mes'].str[:4] == _a, _bts['mes'].str[:4] == _a)
                              for _a in sorted(_m['mes'].str[:4].unique())]):
        _ref = _bts[_m2].groupby(['tipo','subtipo'])['brecha_pct'].median()
        for (_tp, _st, _ma), _x in _m[_m1].groupby(['tipo','subtipo','marca']):
            _filas.append({'periodo': _per, 'tipo': _tp, 'subtipo': _st, 'marca': _ma, 'celdas': len(_x),
                           'sucursales': _x['suc_key'].nunique(), 'empresas': _x['empresa'].nunique(),
                           'meses': _x['mes'].nunique(), 'brecha_misma_marca_pct': float(_x['brecha_misma_marca'].median()),
                           'brecha_canasta_mismas_celdas_pct': float(_x['brecha_pct'].median()),
                           'prima_de_marca_pct': float(_x['_prima'].median()),
                           'brecha_subtipo_pct': float(_ref.get((_tp, _st), np.nan))})
    if not _filas:
        return pd.DataFrame(columns=_cols)
    # productos de cada marca y lado en los subtipos comparados
    _lst = (_p.merge(_m[['tipo','subtipo','marca']].drop_duplicates(), on=['tipo','subtipo','marca'])
            .assign(_ds=lambda _x: _x['producto'].map(lambda _q: EAN_DESC.get(_q, _q)))
            .groupby(['tipo','subtipo','marca','rol'])['_ds'].agg(lambda _s: '; '.join(sorted(set(_s)))).unstack('rol')
            .rename(columns={'tacc': 'productos_con_tacc', 'sin': 'productos_sin_tacc'}))
    return pd.DataFrame(_filas).join(_lst[['productos_con_tacc','productos_sin_tacc']], on=['tipo','subtipo','marca'])[_cols]

_mmp = datos_dia.merge(_U8[_sk + ['suc_key','empresa']], on=_sk)
_mmp['marca'] = _mmp['ean_norm'].map(_MARCA_N).map(lambda _m: _MEQ.get(_m, _m) if isinstance(_m, str) else _m)
prima_misma_marca = _prima_marca(_mmp, bt_sub, _mv, VENTANA_TXT)
del _mmp
if len(prima_misma_marca):
    print(f'\n=== Prima de la misma marca (últimos {len(_mv)} meses): sin TACC / con TACC de la misma marca en la misma celda ===')
    print(prima_misma_marca[prima_misma_marca['periodo'].str.startswith('últimos')][
        ['subtipo','marca','celdas','empresas','brecha_misma_marca_pct','brecha_canasta_mismas_celdas_pct',
         'prima_de_marca_pct','brecha_subtipo_pct']].round(1).to_string(index=False))

# ── 9. Costo con la Canasta Básica Alimentaria del INDEC ──────────────────────
# Precio de cada lado = mediana nacional entre sucursal-meses con los dos lados de cada subtipo del ítem, promedio
# geométrico de sus subtipos; costo = precio × gramos de la CBA / 100. Es una cota inferior del costo de la dieta: solo
# los ítems que la canasta cubre.
def _costo_cba(_x):
    _f = []
    for _it, _tp, _st, _gr in CBA_ITEMS:
        _d = _x[(_x['tipo'] == _tp) & ((_x['subtipo'] == _st) if _st else True)]
        if not len(_d):
            continue
        _s = _d.groupby('subtipo')[['tacc','sin']].median()
        _pc, _ps = float(np.exp(np.log(_s['tacc']).mean())), float(np.exp(np.log(_s['sin']).mean()))
        _f.append({'item_cba': _it, 'tipo': _tp, 'subtipo': _st or 'todos', 'gramos_por_adulto_equivalente': _gr,
                   'precio_con_tacc_100g': _pc, 'precio_sin_tacc_100g': _ps,
                   'costo_con_tacc_ae': _pc * _gr / 100, 'costo_sin_tacc_ae': _ps * _gr / 100})
    _o = pd.DataFrame(_f)
    if len(_o):
        _o['costo_extra_ae'] = _o['costo_sin_tacc_ae'] - _o['costo_con_tacc_ae']
        _o['costo_extra_hogar_tipo'] = _o['costo_extra_ae'] * CBA_AE_HOGAR
        _o['prima_pct'] = 100 * (_o['costo_sin_tacc_ae'] / _o['costo_con_tacc_ae'] - 1)
    return _o
_mc = sorted(bt_sub['mes'].unique())[-int(MESES_CBA):]
costo_cba = _costo_cba(bt_sub[bt_sub['mes'].isin(_mc)])
if len(costo_cba):
    _tot = costo_cba[['gramos_por_adulto_equivalente','costo_con_tacc_ae','costo_sin_tacc_ae','costo_extra_ae',
                      'costo_extra_hogar_tipo']].sum()
    costo_cba = pd.concat([costo_cba, pd.DataFrame([{'item_cba': 'Total', **_tot.to_dict(),
                                                     'prima_pct': 100 * (_tot['costo_sin_tacc_ae'] / _tot['costo_con_tacc_ae'] - 1)}])],
                          ignore_index=True)
    costo_cba.insert(0, 'meses', f'{_mc[0]} → {_mc[-1]}')
_filas = []
for _m in sorted(bt_sub['mes'].unique()):
    _o = _costo_cba(bt_sub[bt_sub['mes'] == _m])
    if len(_o):
        _filas.append({'mes': _m, 'items': ', '.join(_o['item_cba']), 'costo_con_tacc_ae': _o['costo_con_tacc_ae'].sum(),
                       'costo_sin_tacc_ae': _o['costo_sin_tacc_ae'].sum(), 'costo_extra_ae': _o['costo_extra_ae'].sum(),
                       'costo_extra_hogar_tipo': _o['costo_extra_hogar_tipo'].sum()})
costo_cba_mensual = pd.DataFrame(_filas)
_falta_cba = [_it for _it, _tp, _st, _gr in CBA_ITEMS if _it not in set(costo_cba.get('item_cba', []))]
if len(costo_cba):
    _t = costo_cba.iloc[-1]
    print(f'\n=== Costo con la CBA del INDEC ({costo_cba["meses"].iloc[0]}): un celíaco paga +${_t["costo_extra_ae"]:,.0f} '
          f'por adulto equivalente por mes (+{_t["prima_pct"]:.0f}%) y +${_t["costo_extra_hogar_tipo"]:,.0f} un hogar tipo '
          f'({CBA_AE_HOGAR} AE) en {", ".join(costo_cba["item_cba"].iloc[:-1])} ===')
    if _falta_cba:
        print(f'  sin precio en esta canasta (cota inferior del costo de la dieta): {", ".join(_falta_cba)}')

# ── 10. Datos para el análisis propio (OUTPUT_DIR/datos) ──────────────────────
# Paneles para estimar por cuenta propia (parquet y csv.gz, se unen por suc_key): la brecha y el precio de cada lado por
# sucursal × mes × subtipo, el precio de cada producto de la canasta y de los ADICIONALES por sucursal × mes,
# productos.csv (cada código), sucursales.csv, diccionario_datos.csv (cada columna de cada archivo) y LEEME.md.
_DIC = {
    'id_comercio': 'Identificador del comercio en el SEPA (la razón social que informa los precios).',
    'id_bandera': 'Identificador de la bandera (marca comercial de la cadena) dentro del comercio.',
    'id_sucursal': 'Identificador de la sucursal dentro de la bandera.',
    'suc_key': 'Clave de la sucursal: id_comercio|id_bandera|id_sucursal. Une todos los archivos.',
    'mes': 'Mes (AAAA-MM). Precio del mes = mediana de los precios diarios.',
    'anio': 'Año (AAAA).',
    'PROVINCIA_NORM': 'Provincia de la sucursal: la declarada, salvo que las coordenadas caigan lejos de su polígono y '
                      'dentro de otra provincia.',
    'region': 'Región INDEC; Buenos Aires se parte en AMBA (por coordenadas) y el resto, en Pampeana.',
    'amba': 'True si la sucursal está en el AMBA (CABA y conurbano, por coordenadas).',
    'cadena': 'Bandera comercial (Carrefour, Vea, Disco, DIA...).',
    'empresa': 'Grupo empresario que fija los precios (Cencosud agrupa Vea, Disco y Jumbo). Unidad de los errores '
               'agrupados por empresa.',
    'localidad': 'Localidad declarada en el SEPA.',
    'sucursales_localidad': 'Localidad declarada en el SEPA.',
    'sucursales_nombre': 'Nombre de la sucursal en el SEPA.',
    'sucursales_tipo': 'Tipo de sucursal en el SEPA (Supermercado, Hipermercado, Autoservicio...).',
    'sucursales_latitud': 'Latitud de la sucursal (grados).',
    'sucursales_longitud': 'Longitud de la sucursal (grados).',
    'tipo': 'Tipo de producto de la canasta (fideos secos, galletitas dulces...). Peso ENGHo en peso_tipo_canasta.',
    'subtipo': 'Subtipo dentro del tipo: se comparan productos del mismo subtipo (spaghetti con spaghetti, crackers con '
               'crackers).',
    'tacc': 'Precio del lado con TACC del subtipo en la sucursal y mes ($/100 g): mediana de sus productos presentes (cada '
            'producto, mediana de sus códigos).',
    'sin': 'Precio del lado sin TACC del subtipo en la sucursal y mes ($/100 g), como tacc.',
    'tacc_min': 'Producto con TACC más barato entre los que están a menos de x4 de la mediana del lado ($/100 g; '
                'ilustrativo).',
    'sin_min': 'Producto sin TACC más barato entre los que están a menos de x4 de la mediana del lado ($/100 g; '
               'ilustrativo).',
    'n_tacc': 'Productos con TACC del subtipo presentes en la sucursal y mes.',
    'n_sin': 'Productos sin TACC del subtipo presentes en la sucursal y mes.',
    'brecha_pct': 'Brecha intra-sucursal del subtipo: sin / tacc - 1, en %. La unidad de todo el análisis.',
    'brecha_min': 'sin_min / tacc_min - 1, en % (ilustrativo, sesgado al alza: el lado con TACC tiene más productos).',
    'departamento_id': 'Código del departamento (Georef de datos.gob.ar, por coordenadas).',
    'departamento': 'Nombre del departamento (Georef).',
    'hhi_departamento': 'HHI de empresas del departamento (0-1; cuota = sucursales del universo; el SEPA no tiene ventas).',
    'hhi_local': f'HHI de empresas entre las sucursales a <= {RADIO_COMPETENCIA_KM} km (0-1; incluye la sucursal).',
    'sucursales_en_radio': f'Sucursales del universo a <= {RADIO_COMPETENCIA_KM} km (incluida ella).',
    'empresas_en_radio': f'Empresas con sucursales a <= {RADIO_COMPETENCIA_KM} km (incluida la suya).',
    'empresas_rivales_en_radio': f'Otras empresas con sucursales a <= {RADIO_COMPETENCIA_KM} km.',
    'en_panel_balanceado': f'True si la sucursal × subtipo tiene los dos lados en >= {int(FRAC_MESES_PANEL * 100)}% de los '
                           'meses: el universo de la serie clave (panel balanceado).',
    'peso_tipo_canasta': 'Peso del tipo en la canasta (gasto ENGHo 2017/18 renormalizado; los tipos suman 1).',
    'rol': "Lado: 'tacc' (con TACC) o 'sin' (sin TACC).",
    'lado': 'Lado: con TACC o sin TACC.',
    'producto': 'Producto: los códigos de un mismo producto (cambio de EAN) y los sabores de una línea al mismo precio '
                'comparten el nombre; si no, es el código. Cada producto entra una vez en la mediana de su lado.',
    'ean_norm': 'Código EAN sin ceros a la izquierda.',
    'ean': 'Código EAN sin ceros a la izquierda.',
    'descripcion': 'Descripción del producto.',
    'marca': 'Marca normalizada del producto (MARCA, CELDA 1).',
    'marca_comparacion': 'Marca para los pares de la misma marca (MARCA_EQUIVALENTE une las líneas sin TACC que se venden '
                         'con otro nombre, como Snuks y Lasfor).',
    'gramos': 'Contenido neto en gramos (verificado en la descripción y el maestro).',
    'precio': 'Precio del mes en $ por unidad (mediana de los precios diarios).',
    'precio_100': 'Precio en $ por 100 g: precio / gramos × 100.',
    'dias': 'Días con precio en el mes.',
    'motivo': 'Por qué el producto adicional no está en la canasta (composición espejada, comparador fijo, sustituto).',
    'en_canasta': 'True si el código está en la canasta; False, si es un ADICIONAL (solo escenarios de sensibilidad).',
    'linea_todos': "Producto en el escenario 'todos los productos' (une los sabores de una línea con los adicionales).",
    'vigente_desde': 'Primer mes en que se usa el código (cambios de EAN: fuera de su ventana el precio queda congelado).',
    'vigente_hasta': 'Último mes en que se usa el código.',
    'sustituto': 'True si el producto es un sustituto (galletas de arroz en saborizadas): escenario "solo equivalentes".',
    'excluido_plausibilidad': 'True si el código quedó fuera por precio relativo a sus pares fuera de la banda.',
    'sucursal_meses': 'Sucursal-meses con precio del código (después de los filtros).',
    'meses_con_precio': 'Meses con precio del código.',
    'primer_mes': 'Primer mes con precio del código.',
    'ultimo_mes': 'Último mes con precio del código.',
    'brecha_comparable_mediana': 'Mediana en la ventana de la brecha de la canasta comparable de la sucursal (misma '
                                 'canasta de subtipos en todas; lo que no tiene, con la brecha nacional del mes), en %.',
    'peso_propio_pct': 'Parte del peso de la canasta medida en la sucursal (promedio de la ventana), en %.',
}
if EXPORTAR_DATOS:
    _dir = OUTPUT_DIR / 'datos'
    _dir.mkdir(parents=True, exist_ok=True)
    _geo_x = competencia_local[['suc_key','departamento_id','departamento','hhi_departamento','hhi_local',
                                'empresas_rivales_en_radio','sucursales_en_radio']].merge(
        suc_geo[['suc_key','sucursales_latitud','sucursales_longitud','sucursales_tipo']]
        if 'sucursales_tipo' in suc_geo.columns else suc_geo[['suc_key','sucursales_latitud','sucursales_longitud']],
        on='suc_key', how='left')
    _p1 = (bt_sub.merge(_geo_x, on='suc_key', how='left')
           .merge(bt_bal[['suc_key','tipo','subtipo']].drop_duplicates().assign(en_panel_balanceado=True),
                  on=['suc_key','tipo','subtipo'], how='left'))
    _p1['en_panel_balanceado'] = _p1['en_panel_balanceado'].eq(True)
    _p1['peso_tipo_canasta'] = _p1['tipo'].map(_W8 / _W8.sum())
    _p2 = (datos_dia.merge(_U8[_sk + ['suc_key']], on=_sk)
           .assign(descripcion=lambda _d: _d['ean_norm'].map(EAN_DESC), marca=lambda _d: _d['ean_norm'].map(_MARCA_N),
                   gramos=lambda _d: _d['grams'])
           [['suc_key','mes','tipo','subtipo','rol','producto','ean_norm','descripcion','marca','gramos','precio',
             'precio_100','dias']])
    _ADX = lambda _k: (lambda _e: ADIC_INFO.get(_e, {}).get(_k))
    _p3 = (datos_adic.merge(_U8[_sk + ['suc_key']], on=_sk)
           .assign(producto=lambda _d: _d['producto_todos'], descripcion=lambda _d: _d['ean_norm'].map(_ADX('descripcion')),
                   marca=lambda _d: _d['ean_norm'].map(_MARCA_N), gramos=lambda _d: _d['grams'],
                   motivo=lambda _d: _d['ean_norm'].map(_ADX('motivo')))
           [['suc_key','mes','tipo','subtipo','rol','producto','ean_norm','descripcion','marca','gramos','precio',
             'precio_100','dias','motivo']]) if len(datos_adic) else pd.DataFrame(columns=list(_p2.columns) + ['motivo'])
    # productos.csv: cada código de la canasta y de los ADICIONALES, con lo que se usó de él
    _ob = (pd.concat([datos_dia[['ean_norm','mes']], datos_adic[['ean_norm','mes']]]) if len(datos_adic)
           else datos_dia[['ean_norm','mes']]).groupby('ean_norm').agg(
        sucursal_meses=('mes','size'), meses_con_precio=('mes','nunique'), primer_mes=('mes','min'), ultimo_mes=('mes','max'))
    _VG = {_norm_ean(_k): _v for _k, _v in globals().get('VIGENCIA', {}).items() if _norm_ean(_k)}
    _BAD_A = globals().get('_bad_a', set())
    _f = []
    for _e in sorted(EANS_CONFIG):
        _pd_ = _PROD.get(_e, _e)
        _f.append({'ean': _e, 'en_canasta': True, 'tipo': EAN_TIPO.get(_e), 'subtipo': EAN_SUBTIPO.get(_e),
                   'rol': EAN_ROL.get(_e), 'descripcion': EAN_DESC.get(_e), 'producto': _pd_, 'linea_todos': _LTD.get(_e, _pd_),
                   'marca': _MARCA_N.get(_e), 'gramos': EAN_GRAMS.get(_e), 'vigente_desde': _VG.get(_e, (None, None))[0],
                   'vigente_hasta': _VG.get(_e, (None, None))[1], 'sustituto': _e in _SUS, 'motivo': '',
                   'excluido_plausibilidad': _e in _bad})
    for _e in sorted(EANS_ADIC):
        _i = ADIC_INFO.get(_e, {})
        _f.append({'ean': _e, 'en_canasta': False, 'tipo': _i.get('tipo'), 'subtipo': _i.get('subtipo'),
                   'rol': {'tacc': 'tacc', 'sin_tacc': 'sin'}.get(_i.get('lado')), 'descripcion': _i.get('descripcion'),
                   'producto': _i.get('linea_todos') or _e, 'linea_todos': _i.get('linea_todos') or _e,
                   'marca': _MARCA_N.get(_e), 'gramos': _i.get('gramos'), 'vigente_desde': _i.get('desde'),
                   'vigente_hasta': _i.get('hasta'), 'sustituto': str(_i.get('motivo', '')).startswith('sustituto'),
                   'motivo': _i.get('motivo', ''), 'excluido_plausibilidad': _e in _BAD_A})
    _p4 = pd.DataFrame(_f)
    _p4.insert(5, 'lado', _p4['rol'].map({'tacc': 'con TACC', 'sin': 'sin TACC'}))
    _p4.insert(list(_p4.columns).index('marca') + 1, 'marca_comparacion',
               _p4['marca'].map(lambda _m: _MEQ.get(_m, _m) if isinstance(_m, str) else _m))
    _p4 = _p4.join(_ob, on='ean')
    _p5 = competencia_local.merge(suc_geo[['suc_key','sucursales_nombre','sucursales_localidad','sucursales_latitud',
                                           'sucursales_longitud']], on='suc_key', how='left')
    _arch = {'panel_sucursal_mes_subtipo': _p1, 'panel_producto_sucursal_mes': _p2,
             'panel_producto_sucursal_mes_adicionales': _p3}
    for _n, _d in _arch.items():
        _d.to_parquet(_dir / f'{_n}.parquet', index=False)
        _d.to_csv(_dir / f'{_n}.csv.gz', index=False, compression='gzip')
    _p4.to_csv(_dir / 'productos.csv', index=False)
    _p5.to_csv(_dir / 'sucursales.csv', index=False)
    _dic = pd.DataFrame([{'archivo': _a, 'columna': _c, 'descripcion': _DIC.get(_c, '')}
                         for _a, _d in (('panel_sucursal_mes_subtipo', _p1), ('panel_producto_sucursal_mes', _p2),
                                        ('panel_producto_sucursal_mes_adicionales', _p3), ('productos.csv', _p4),
                                        ('sucursales.csv', _p5)) for _c in _d.columns])
    _dic.to_csv(_dir / 'diccionario_datos.csv', index=False)
    _sin_desc = sorted(set(_dic.loc[_dic['descripcion'] == '', 'columna']))
    if _sin_desc:
        print(f'  ⚠️ columnas sin descripción en diccionario_datos.csv: {_sin_desc}')
    _nm_ = globals().get('NOMBRE_CANASTA', 'canasta fija 2022-2026')
    _ms_ = sorted(bt_sub['mes'].unique())
    _wt_ = (_W8 / _W8.sum()).round(4).to_dict()
    _leeme = [
        f'# Datos de la brecha celíaca: {_nm_}',
        '',
        f'Precios del SEPA (Sistema Electrónico de Publicidad de Precios Argentinos), {_ms_[0]} a {_ms_[-1]}, de los '
        f'productos de la {_nm_}. Generado por el notebook {globals().get("PREFIJO_EXCEL", "brecha_celiaca")} '
        f'(repositorio precios_minoristas_supermercados, notebooks/gen_nb06.py) con el último mes {ULTIMO_MES}.',
        '',
        '## Archivos (se unen por suc_key; cada columna, en diccionario_datos.csv)',
        '',
        f'- panel_sucursal_mes_subtipo (.parquet y .csv.gz, {len(_p1):,} filas): una fila por celda = sucursal × mes × '
        'subtipo con los dos lados. brecha_pct = sin / tacc - 1 (precio de cada lado = mediana $/100 g de sus productos '
        'presentes). Con región, empresa, cadena, departamento, concentración, coordenadas, en_panel_balanceado y '
        'peso_tipo_canasta.',
        f'- panel_producto_sucursal_mes (.parquet y .csv.gz, {len(_p2):,} filas): precio de cada código de la canasta por '
        'sucursal y mes (precio por unidad y $/100 g), con su producto, marca y gramos. Para estimaciones hedónicas o con '
        'efectos fijos de producto.',
        f'- panel_producto_sucursal_mes_adicionales ({len(_p3):,} filas): lo mismo para los productos ADICIONALES, que '
        'cumplen las reglas de la selección pero no están en la canasta (motivo); solo para los escenarios de sensibilidad.',
        f'- productos.csv ({len(_p4)} códigos): tipo, subtipo, lado, producto, marca, gramos, vigencia y uso de cada código.',
        f'- sucursales.csv ({len(_p5):,} sucursales): empresa, cadena, región, provincia, departamento, competencia local, '
        'brecha comparable y coordenadas.',
        '- diccionario_datos.csv: archivo, columna y descripción.',
        '',
        '## Cómo se calcula la brecha (BRECHA_CELIACA.md §3 y §14)',
        '',
        '1. Precio de un código en el mes = mediana de sus precios diarios; $/100 g con los gramos verificados.',
        '2. Precio de un producto en la sucursal y mes = mediana de sus códigos (cambio de EAN, sabores de una línea).',
        '3. Precio de cada lado de un subtipo en la sucursal y mes = mediana de sus productos presentes; la celda existe si '
        'están los dos lados. brecha_pct = sin / tacc - 1.',
        '4. Brecha de un subtipo en un período = mediana de brecha_pct entre sus celdas.',
        '5. Brecha de un tipo = promedio geométrico de las de sus subtipos (pesos iguales).',
        '6. Brecha de la canasta = sum_k w_k (1 + brecha del tipo k) / sum_k w_k - 1, con w = peso_tipo_canasta (gasto '
        f'ENGHo 2017/18): {_wt_}.',
        '',
        f'Con las filas de los últimos {len(_mv)} meses ({VENTANA_TXT}) y estos pasos sale la brecha nacional del Excel '
        f'(hoja IC_grupos, País: {_c_ref:+.2f}%). La serie mensual y los grupos (región, provincia, empresa, cadena) siguen '
        'las mismas reglas con la misma canasta de subtipos: el subtipo con pocas sucursales en un grupo o mes toma la brecha '
        'nacional del período (o su último mes válido, en la serie). en_panel_balanceado = True selecciona el panel '
        'balanceado (la serie clave: las mismas sucursales y subtipos en todo el período).',
        '',
        '## Lo que hay que tener en cuenta al estimar',
        '',
        '- Las cadenas fijan el precio para todas sus sucursales: en la mayoría de los subtipos la empresa explica más de la '
        'mitad de la variación entre sucursales y el desvío dentro de cada empresa es chico (hoja Varianza_empresa). Para '
        'inferencia sobre cadenas posibles, agrupar los errores por empresa (hay '
        f'{_btb["empresa"].nunique()} empresas en la ventana: con tan pocos grupos, conviene un bootstrap salvaje por '
        'grupos o la corrección de pocos grupos). El Excel trae los dos intervalos (por sucursal y por empresa).',
        '- La composición de todas las sucursales cambia con los años (hoja Composicion_empresas): para la evolución, el '
        'panel balanceado, o efectos fijos de sucursal y de producto.',
        '- Cada cadena vende un surtido distinto y cambia en el tiempo (hoja Surtido_empresa): la brecha de un grupo compara '
        'sus productos; con efectos fijos de producto (panel_producto_sucursal_mes) se comparan los mismos productos '
        '(hoja Hedonica_grupos: efecto_surtido_pct).',
        '- La brecha se mide donde están los dos lados: no encontrar el sin TACC también es un costo (hoja Disponibilidad).',
        '- Son precios de góndola publicados por las cadenas obligadas a informar al SEPA (supermercados grandes), no '
        'precios de transacción ni cantidades vendidas; no incluyen dietéticas ni almacenes, donde también compran los '
        'celíacos. Los pesos de los tipos son los del gasto de todos los hogares (ENGHo), no los de un hogar celíaco.',
        '- Prima de la misma marca (hoja Prima_misma_marca): en los subtipos donde una misma marca vende los dos lados, '
        'separa la prima sin gluten de la prima de marca.',
        '',
        '## Especificación sugerida (la TPD del notebook, hoja Serie_TPD)',
        '',
        'Por subtipo: ln p(producto j, sucursal s, mes t) = a(s, t) + g(j) + b(t) × sinTACC(j) + e, por mínimos cuadrados '
        'ponderados (cada producto pesa 1 / productos de su lado en la celda). exp(nivel + b(t)) - 1 es la brecha del '
        'subtipo en el mes, con nivel = promedio de los g sin TACC - promedio de los g con TACC (pesados por su '
        'disponibilidad). Para diferencias entre grupos: b × (región + empresa [+ concentración]) con la celda y el producto '
        'como efectos fijos (hoja Hedonica_grupos).',
        '',
        '## Fuentes',
        '',
        '- SEPA: Secretaría de Comercio de la Nación (datos abiertos, precios diarios por sucursal).',
        '- Ponderaciones: Encuesta Nacional de Gastos de los Hogares 2017/18 (INDEC).',
        '- Costo por adulto equivalente: Canasta Básica Alimentaria del INDEC.',
        '- Departamentos: Georef (datos.gob.ar). Población provincial (escenario de sensibilidad): PESOS_POBLACION, los '
        'mismos pesos del nb02 y el nb05.',
    ]
    (_dir / 'LEEME.md').write_text('\n'.join(_leeme) + '\n', encoding='utf-8')
    print(f'\nDatos para el análisis propio en {_dir}: panel_sucursal_mes_subtipo ({len(_p1):,} filas), '
          f'panel_producto_sucursal_mes ({len(_p2):,}), panel_producto_sucursal_mes_adicionales ({len(_p3):,}), '
          f'productos ({len(_p4)}), sucursales ({len(_p5):,}), diccionario_datos y LEEME.md')
    del _p1, _p2, _p3, _p4, _p5"""))

# ── CELL 9 — GRÁFICOS ──────────────────────────────────────────────────────────
cells.append(cell_code(r"""# ============================================================
# CELDA 9 — Gráficos de la brecha
# ============================================================
MES = f'{ULTIMO_MES[5:7]}{ULTIMO_MES[:4]}'
_C_MED, _C_BAL = '#0055A4', '#2ca02c'

def _guardar(_nombre):
    plt.tight_layout(); _o = OUTPUT_DIR / f'{_nombre}_{MES}.png'
    plt.savefig(_o, dpi=200, bbox_inches='tight', facecolor='white'); plt.show()
    print(f'Guardado: {_o.name}')

def _pct(_ax):
    # eje en %: sin decimales si el tick es entero y con uno si no (los ticks de a 2,5 no se redondean a +28%, +22%...)
    _ax.yaxis.set_major_formatter(mticker.FuncFormatter(
        lambda x, _: f'{x:+.0f}%' if abs(x - round(x)) < 1e-9 else f'{x:+.1f}%'))

def _barras_horizontales(_ax):
    # sin la grilla del eje y que pone el estilo (pasaba por el medio de las etiquetas de las barras) ni el marco de
    # arriba y de la derecha (las etiquetas largas lo cruzaban)
    _ax.grid(True, alpha=0.3, axis='x'); _ax.grid(False, axis='y'); _ax.set_axisbelow(True)
    for _s in ('top', 'right'):
        _ax.spines[_s].set_visible(False)

_FONDO_ETIQUETA = dict(facecolor='white', edgecolor='none', alpha=0.85, pad=1)   # tapa la grilla detrás del texto

# 1) Canasta mensual: todas las sucursales vs panel balanceado (+ sucursales del tipo con menos cobertura). Marcador
#    vacío: mes con algún subtipo imputado con su último mes válido (hoja Imputaciones)
if len(serie_mensual):
    fig, ax = plt.subplots(figsize=(13, 6))
    _sm = serie_mensual.assign(f=pd.to_datetime(serie_mensual['mes'] + '-01'))
    ax.plot(_sm['f'], _sm['brecha_canasta'], color=_C_MED, lw=2.2, marker='o', ms=3, label='Todas las sucursales')
    _im = _sm['peso_imputado_pct'] > 0
    ax.plot(_sm.loc[_im, 'f'], _sm.loc[_im, 'brecha_canasta'], ls='none', marker='o', ms=6, mfc='white', mec=_C_MED)
    if len(serie_mensual_bal):
        _sb = serie_mensual_bal.assign(f=pd.to_datetime(serie_mensual_bal['mes'] + '-01'))
        ax.plot(_sb['f'], _sb['brecha_canasta'], color=_C_BAL, lw=2.2, marker='D', ms=3, label='Panel balanceado')
        _im = _sb['peso_imputado_pct'] > 0
        ax.plot(_sb.loc[_im, 'f'], _sb.loc[_im, 'brecha_canasta'], ls='none', marker='D', ms=6, mfc='white', mec=_C_BAL)
    ax.plot([], [], ls='none', marker='o', ms=6, mfc='white', mec='#555',
            label='mes con algún subtipo imputado (último mes válido)')
    ax.set_ylabel('Brecha de la canasta (%)')
    ax.set_title(f"Brecha celíaca de la canasta (ponderada ENGHo) — {globals().get('NOMBRE_CANASTA', 'canasta fija 2022-2026')}")
    _pct(ax); ax.grid(True, alpha=0.3)
    _a2 = ax.twinx()
    _a2.bar(_sm['f'], _sm['n_min'], width=20, color='#cccccc', alpha=0.35, label='sucursales del tipo con menos (der.)')
    _a2.set_ylim(0, max(1, _sm['n_min'].max()) * 3); _a2.set_ylabel('sucursales', color='#999')
    _a2.grid(False)                                   # una sola grilla, la de la brecha
    ax.set_zorder(_a2.get_zorder() + 1); ax.patch.set_visible(False)   # líneas y leyenda encima de las barras
    _l1, _b1 = ax.get_legend_handles_labels(); _l2, _b2 = _a2.get_legend_handles_labels()
    ax.legend(_l1 + _l2, _b1 + _b2, loc='upper left', fontsize=9)
    _guardar('brecha_mensual')

# 2) Brecha mensual por tipo (panel balanceado)
if len(brecha_tipo_mensual_bal):
    fig, ax = plt.subplots(figsize=(13, 6))
    for _t, _g in brecha_tipo_mensual_bal.groupby('tipo'):
        _g = _g.sort_values('mes')
        _f = pd.to_datetime(_g['mes'] + '-01')
        _ln = ax.plot(_f, _g['brecha_mediana'], marker='o', ms=3, lw=1.8, label=_t)[0]
        _im = (_g['n_subtipos_imputados'] > 0).to_numpy()
        ax.plot(_f[_im], _g['brecha_mediana'][_im], ls='none', marker='o', ms=6, mfc='white', mec=_ln.get_color(),
                color=_ln.get_color())   # con color explícito no consume un color del ciclo
    ax.plot([], [], ls='none', marker='o', ms=6, mfc='white', mec='#555', label='con algún subtipo imputado')
    ax.set_ylabel('Brecha (%)'); ax.set_title('Brecha mensual por tipo — panel balanceado')
    _pct(ax)
    ax.legend(fontsize=8, ncol=2); ax.grid(True, alpha=0.3)
    _guardar('brecha_tipo_mensual')

# 3) Brecha por tipo (todo el período)
if len(brecha_tipo):
    _bt = brecha_tipo.sort_values('brecha_mediana')
    fig, ax = plt.subplots(figsize=(11, max(4, len(_bt) * 0.7 + 2)))
    ax.barh(_bt['tipo'], _bt['brecha_mediana'], color=plt.cm.RdYlGn_r(np.linspace(0.2, 0.9, len(_bt))),
            edgecolor='black', lw=0.4)
    for _i, (_, _r) in enumerate(_bt.iterrows()):
        ax.annotate(f'{_r["brecha_mediana"]:+.0f}%  ({int(_r["n_sucursales"])} sucursales)', (_r['brecha_mediana'], _i),
                    xytext=(5, 0), textcoords='offset points', va='center', fontsize=8, bbox=_FONDO_ETIQUETA)
    ax.set_xlabel('Brecha mediana (%) — sin TACC vs con TACC, $/100 g'); ax.set_title('Brecha celíaca por tipo (2022 → hoy)')
    _barras_horizontales(ax)
    _guardar('brecha_por_tipo')

# 4) Canasta por año y región (todas las sucursales; misma canasta en todas las regiones). Marcador vacío: no confiable
if len(brecha_region_anual):
    fig, ax = plt.subplots(figsize=(11, 6))
    for _rg, _g in brecha_region_anual.groupby('region'):
        _g = _g.sort_values('anio')
        _ln = ax.plot(_g['anio'], _g['brecha_canasta'], marker='o', lw=2, label=_rg)[0]
        _nc = ~_g['confiable'].astype(bool)
        ax.plot(_g.loc[_nc, 'anio'], _g.loc[_nc, 'brecha_canasta'], ls='none', marker='o', ms=8, mfc='white',
                mec=_ln.get_color(), color=_ln.get_color())
    ax.set_ylabel('Brecha de la canasta (%)')
    ax.set_title(f'Brecha celíaca de la canasta por región y año (marcador vacío: > {MAX_PESO_IMPUTADO}% del peso con la '
                 f'brecha nacional o < {MIN_SUC_AGG} sucursales)', fontsize=10)
    _pct(ax)
    ax.legend(fontsize=9); ax.grid(True, alpha=0.3)
    _guardar('brecha_region_anual')

# 5), 6) y 7) Provincia, empresa y cadena (últimos meses; solo confiables: misma canasta de subtipos en todos los grupos)
for _df, _col, _tit, _nom in ((brecha_prov, 'provincia', 'provincia', 'brecha_provincia'),
                              (brecha_empresa, 'empresa', 'empresa', 'brecha_empresa'),
                              (brecha_cadena, 'cadena', 'cadena', 'brecha_cadena')):
    _d = _df[_df['confiable']] if len(_df) else _df
    if not len(_d):
        continue
    fig, ax = plt.subplots(figsize=(11, max(4, len(_d) * 0.38 + 2)))
    ax.barh(_d[_col], _d['brecha_canasta'], color=plt.cm.RdYlGn_r(np.linspace(0.15, 0.9, len(_d))),
            edgecolor='black', lw=0.4)
    for _i, (_, _r) in enumerate(_d.iterrows()):
        ax.annotate(f'{_r["brecha_canasta"]:+.1f}% ({int(_r["n_sucursales"])} sucursales; '
                    f'{_r["peso_imputado_pct"]:.0f}% del peso con la brecha nacional)', (_r['brecha_canasta'], _i),
                    xytext=(5, 0), textcoords='offset points', va='center', fontsize=8, bbox=_FONDO_ETIQUETA)
    ax.set_xlabel('Brecha de la canasta (%)')
    ax.set_title(f'Brecha celíaca por {_tit} — {VENTANA_TXT}\n(misma canasta en todos; subtipos sin datos = brecha '
                 f'nacional, <= {MAX_PESO_IMPUTADO}% del peso; >= {MIN_SUC_AGG} sucursales)', fontsize=11)
    _barras_horizontales(ax)
    _guardar(_nom)

# 8) Brecha vs concentración del mercado local: HHI de empresas por departamento (cuota = sucursales)
_cc = concentracion[concentracion['confiable']] if len(concentracion) else concentracion
if len(_cc) >= 3:
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(_cc['hhi'], _cc['brecha_mediana'], s=12 + 3 * _cc['sucursales_con_brecha'].clip(upper=150), alpha=0.6,
               color=_C_MED, edgecolor='white')
    ax.set_xlabel('HHI de empresas en el departamento (cuota = sucursales; 1 = una sola empresa)')
    ax.set_ylabel('Brecha de la canasta (mediana de sus sucursales, %)')
    ax.set_title(f'Brecha vs concentración del mercado local — {VENTANA_TXT}\nDepartamentos con >= {MIN_SUC_DEPTO} '
                 f'sucursales con brecha propia (tamaño = sucursales) · Spearman por sucursal {CONC_RHO:+.2f} '
                 f'(n = {CONC_N:,})', fontsize=11)
    ax.grid(True, alpha=0.3)
    _guardar('brecha_concentracion')

# 9) Serie TPD (hedónica, CELDA 8b) contra la descriptiva: canasta, panel balanceado y todas las sucursales
_C_TPD = '#d62728'
if len(serie_tpd) and 'brecha_canasta_tpd_panel' in serie_tpd.columns:
    fig, axs = plt.subplots(2, 1, figsize=(13, 10), sharex=True)
    _st = serie_tpd.assign(f=pd.to_datetime(serie_tpd['mes'] + '-01'))
    for _ax, _suf, _col, _tit in ((axs[0], 'panel', _C_BAL, 'Panel balanceado (la serie clave)'),
                                  (axs[1], 'todas', _C_MED, 'Todas las sucursales')):
        if f'brecha_canasta_tpd_{_suf}' not in _st.columns:
            continue
        if _st.get(f'brecha_canasta_tpd_ic95_inf_empresa_{_suf}', pd.Series(dtype=float)).notna().any():
            _ax.fill_between(_st['f'], _st[f'brecha_canasta_tpd_ic95_inf_empresa_{_suf}'],
                             _st[f'brecha_canasta_tpd_ic95_sup_empresa_{_suf}'], color=_C_TPD, alpha=0.07, lw=0,
                             label='TPD: IC 95% agrupado por empresa')
        _ax.fill_between(_st['f'], _st[f'brecha_canasta_tpd_ic95_inf_{_suf}'], _st[f'brecha_canasta_tpd_ic95_sup_{_suf}'],
                         color=_C_TPD, alpha=0.15, lw=0, label='TPD: IC 95% (errores agrupados por sucursal)')
        _ax.plot(_st['f'], _st[f'brecha_canasta_tpd_{_suf}'], color=_C_TPD, lw=2.4,
                 label='TPD (hedónica): canasta fija de productos')
        _mv = _st[f'peso_movido_pct_{_suf}'] > 0
        _ax.plot(_st.loc[_mv, 'f'], _st.loc[_mv, f'brecha_canasta_tpd_{_suf}'], ls='none', marker='o', ms=6,
                 mfc='white', mec=_C_TPD, color=_C_TPD,
                 label=f'TPD: mes con algún subtipo sin dato propio (< {MIN_SUC_SUBTIPO} sucursales; movido)')
        _ax.plot(_st['f'], _st[f'brecha_canasta_descriptiva_{_suf}'], color=_col, lw=1.6, marker='D', ms=3,
                 label='Descriptiva')
        _im = _st[f'peso_imputado_pct_{_suf}'] > 0
        _ax.plot(_st.loc[_im, 'f'], _st.loc[_im, f'brecha_canasta_descriptiva_{_suf}'], ls='none', marker='D', ms=6,
                 mfc='white', mec=_col, color=_col, label='descriptiva: mes con algún subtipo imputado')
        _ax.set_title(_tit, fontsize=11, loc='left'); _ax.set_ylabel('Brecha de la canasta (%)')
        _pct(_ax)
        _ax.legend(loc='upper left', fontsize=8); _ax.grid(True, alpha=0.3)
    fig.suptitle('Brecha celíaca de la canasta: serie TPD (hedónica) y serie descriptiva', y=1.0)
    _guardar('brecha_tpd')

# 10) Serie TPD por tipo contra la descriptiva (panel balanceado)
_btp = brecha_tipo_tpd[brecha_tipo_tpd['universo'] == 'panel balanceado'] if len(brecha_tipo_tpd) else brecha_tipo_tpd
if len(_btp):
    _tps = [_t for _t in TIPOS_ORD if _t in set(_btp['tipo'])]
    fig, axs = plt.subplots(len(_tps), 1, figsize=(13, 2.9 * len(_tps)), sharex=True)
    axs = np.atleast_1d(axs)
    for _ax, _tp in zip(axs, _tps):
        _x = _btp[_btp['tipo'] == _tp].sort_values('mes')
        _f = pd.to_datetime(_x['mes'] + '-01')
        _ax.fill_between(_f, _x['brecha_tpd_ic95_inf'], _x['brecha_tpd_ic95_sup'], color=_C_TPD, alpha=0.15, lw=0)
        _ax.plot(_f, _x['brecha_tpd'], color=_C_TPD, lw=2, label='TPD (IC 95%)')
        _mv = (_x['subtipos_movidos'] > 0).to_numpy()
        _ax.plot(_f[_mv], _x['brecha_tpd'][_mv], ls='none', marker='o', ms=5, mfc='white', mec=_C_TPD, color=_C_TPD,
                 label='TPD: subtipo movido')
        _ax.plot(_f, _x['brecha_descriptiva'], color=_C_BAL, lw=1.3, marker='o', ms=2.5, label='Descriptiva')
        _im = (_x['subtipos_imputados_descriptiva'] > 0).to_numpy()
        _ax.plot(_f[_im], _x['brecha_descriptiva'][_im], ls='none', marker='o', ms=5, mfc='white', mec=_C_BAL,
                 color=_C_BAL, label='descriptiva: subtipo imputado')
        _ax.set_title(_tp, fontsize=10, loc='left')
        _pct(_ax); _ax.grid(True, alpha=0.3)
    axs[0].legend(loc='upper right', fontsize=8, ncol=4)
    fig.suptitle('Brecha por tipo, panel balanceado: serie TPD (hedónica) y descriptiva', y=1.0)
    _guardar('brecha_tpd_tipos')

# 11) Índices de precio de cada lado (CELDA 8c) contra el IPC de alimentos, y su cociente contra la TPD
_il = indices_lados[indices_lados['nivel'] == 'Canasta'].sort_values('mes') if len(indices_lados) else indices_lados
if len(_il):
    fig, axs = plt.subplots(2, 1, figsize=(13, 10), sharex=True)
    _f = pd.to_datetime(_il['mes'] + '-01')
    axs[0].plot(_f, _il['indice_con_tacc'], color='#1f77b4', lw=2.2, label='Con TACC (los mismos productos y sucursales)')
    axs[0].plot(_f, _il['indice_sin_tacc'], color=_C_TPD, lw=2.2, label='Sin TACC')
    if 'ipc_alimentos' in _il.columns and _il['ipc_alimentos'].notna().any():
        axs[0].plot(_f, _il['ipc_alimentos'], color='#555', lw=1.6, ls='--', label='IPC alimentos y bebidas (INDEC)')
    axs[0].set_yscale('log'); axs[0].set_ylabel(f'Índice ({_il["mes"].iloc[0]} = 100, escala log)')
    axs[0].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x:,.0f}'))
    axs[0].set_title('Precio de cada lado de la canasta (pesos ENGHo): efectos fijos de producto en la sucursal y de mes',
                     fontsize=11, loc='left')
    axs[0].legend(loc='upper left', fontsize=9); axs[0].grid(True, alpha=0.3, which='both')
    axs[1].plot(_f, _il['sin_sobre_con'], color='#8c564b', lw=2.2, label='Sin TACC / con TACC (índices de cada lado)')
    if len(serie_tpd):
        _tt = serie_tpd.set_index('mes')['brecha_canasta_tpd_todas'].reindex(_il['mes'])
        axs[1].plot(_f, 100 * (1 + _tt.to_numpy() / 100) / (1 + _tt.iloc[0] / 100), color=_C_TPD, lw=1.4, ls=':',
                    label='TPD de todas las sucursales (1 + brecha, primer mes = 100)')
    axs[1].axhline(100, color='#999', lw=1)
    axs[1].set_ylabel('Primer mes = 100'); axs[1].legend(loc='upper left', fontsize=9); axs[1].grid(True, alpha=0.3)
    axs[1].set_title('Evolución relativa: arriba de 100, los sin TACC aumentaron más que los con TACC', fontsize=11, loc='left')
    fig.suptitle('Índices de precio de cada lado de la brecha (CELDA 8c)', y=1.0)
    _guardar('indices_lados')

# 12) Disponibilidad sin TACC por región y tipo (últimos meses)
_dr9 = (disponibilidad[(disponibilidad['agrupacion'] == 'Región') & (disponibilidad['medida'] == 'sucursal-meses')]
        if len(disponibilidad) else disponibilidad)
if len(_dr9):
    _cols9 = [f'disponibilidad_{_c}_pct' for _c in TIPOS_ORD] + ['disponibilidad_ponderada_pct']
    _hm = _dr9.set_index('grupo')[_cols9].sort_values('disponibilidad_ponderada_pct')
    _hm.columns = [_c.replace('disponibilidad_', '').replace('_pct', '') for _c in _cols9]
    fig, ax = plt.subplots(figsize=(max(13, 1.35 * len(_hm.columns) + 3), max(3.5, 0.55 * len(_hm) + 2)))
    sns.heatmap(_hm, annot=True, fmt='.0f', cmap='RdYlGn', vmin=40, vmax=100, cbar_kws={'label': '%'}, ax=ax)
    ax.set_xlabel(''); ax.set_ylabel('')
    # nombres de los tipos en dos o tres renglones, horizontales (rotados 90° ocupaban media figura)
    import textwrap as _tw
    ax.set_xticklabels([_tw.fill(_c, 16) for _c in _hm.columns], rotation=0, fontsize=9)
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0)
    ax.set_title(f'Disponibilidad: de las sucursal-meses que venden el tipo con TACC, % que vende también el sin TACC '
                 f'({VENTANA_TXT})', fontsize=11)
    _guardar('disponibilidad_region')

# 13) Intervalos de confianza de regiones y empresas confiables contra el país: bootstrap por sucursal (gris) y, en las
#     regiones, por empresa (naranja: las cadenas fijan el precio de todas sus sucursales)
_C_EMP = '#e08214'
_ic9 = (ic_grupos[ic_grupos['agrupacion'].isin(['Región','Empresa']) & ic_grupos['confiable']].dropna(subset=['ic95_inf'])
        if len(ic_grupos) and 'ic95_inf' in ic_grupos.columns else pd.DataFrame())
if len(_ic9):
    _ic9 = _ic9.sort_values(['agrupacion','brecha_canasta'])
    fig, ax = plt.subplots(figsize=(11, max(4, 0.5 * len(_ic9) + 2)))
    _yy = np.arange(len(_ic9))
    _cl9 = np.where(_ic9['difiere_del_pais'], _C_TPD, _C_MED)
    _p9 = ic_grupos.iloc[0]
    _emp9 = 'ic95_inf_empresa' in _ic9.columns and _ic9['ic95_inf_empresa'].notna().any()
    if _emp9:
        _e9 = _ic9['ic95_inf_empresa'].notna().to_numpy()
        _x9 = _ic9.loc[_e9]
        ax.errorbar(_x9['brecha_canasta'], _yy[_e9] + 0.22, xerr=[_x9['brecha_canasta'] - _x9['ic95_inf_empresa'],
                                                                  _x9['ic95_sup_empresa'] - _x9['brecha_canasta']],
                    fmt='none', ecolor=_C_EMP, capsize=2, lw=1.1)
    if pd.notna(_p9.get('ic95_inf_empresa')):
        ax.axvspan(_p9['ic95_inf_empresa'], _p9['ic95_sup_empresa'], color=_C_EMP, alpha=0.08, lw=0)
    ax.errorbar(_ic9['brecha_canasta'], _yy, xerr=[_ic9['brecha_canasta'] - _ic9['ic95_inf'], _ic9['ic95_sup'] - _ic9['brecha_canasta']],
                fmt='none', ecolor='#888', capsize=3, lw=1.2)
    ax.scatter(_ic9['brecha_canasta'], _yy, c=_cl9, s=40, zorder=3)
    ax.axvspan(_p9['ic95_inf'], _p9['ic95_sup'], color='#999', alpha=0.2, lw=0)
    ax.axvline(_p9['brecha_canasta'], color='#555', lw=1)
    ax.set_yticks(_yy); ax.set_yticklabels([f'{_a}: {_g}' for _a, _g in zip(_ic9['agrupacion'], _ic9['grupo'])], fontsize=9)
    ax.set_xlabel('Brecha de la canasta (%), misma canasta en todos los grupos')
    # sin leyenda (tapaba el último grupo): las franjas del país van en el título
    ax.set_title(f'Brecha por región y empresa con IC 95% ({int(BOOT_B)} réplicas) — {VENTANA_TXT}\n'
                 f'gris: bootstrap por sucursal' + (' · naranja: por empresa (regiones con 2 o más empresas)' if _emp9 else '')
                 + f'\nfranjas: el país, {_p9["brecha_canasta"]:+.1f}%; en rojo, los grupos que difieren del país (por sucursal)',
                 fontsize=10)
    _barras_horizontales(ax)
    _guardar('ic_grupos')

# 14) Sensibilidad de la brecha a las decisiones de diseño (CELDA 8c)
if len(sensibilidad):
    _sv = sensibilidad.iloc[::-1]
    fig, ax = plt.subplots(figsize=(12, max(4, 0.55 * len(_sv) + 2)))
    ax.barh(_sv['escenario'], _sv['brecha_canasta'], color=['#555' if _i == len(_sv) - 1 else _C_MED for _i in range(len(_sv))],
            edgecolor='black', lw=0.4)
    for _i, _r in enumerate(_sv.itertuples(index=False)):
        ax.annotate(f'{_r.brecha_canasta:+.1f}% ({_r.diferencia_pp:+.1f} pp)', (_r.brecha_canasta, _i), xytext=(5, 0),
                    textcoords='offset points', va='center', fontsize=8, bbox=_FONDO_ETIQUETA)
    ax.set_xlabel(f'Brecha nacional de la canasta (%), {VENTANA_TXT}')
    ax.set_title('Sensibilidad de la brecha a cada decisión de diseño (una por vez)', fontsize=11)
    _lo9, _hi9 = min(0.0, float(_sv['brecha_canasta'].min())), max(0.0, float(_sv['brecha_canasta'].max()))
    ax.set_xlim(1.1 * _lo9, 1.25 * _hi9)   # lugar para la etiqueta de la barra más larga
    _barras_horizontales(ax)
    _guardar('sensibilidad')

# 15) Hedónica de grupos: efecto de la región y la empresa sobre 1 + brecha, controlando una por la otra
_hg = hedonica_grupos[hedonica_grupos['modelo'] == 'región y empresa'] if len(hedonica_grupos) else hedonica_grupos
if len(_hg):
    _hg = _hg.sort_values(['grupo','efecto_pct']).reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(11, max(4, 0.5 * len(_hg) + 2)))
    _yy = np.arange(len(_hg))
    _okg = _hg['confiable'].to_numpy(bool) if 'confiable' in _hg.columns else np.ones(len(_hg), bool)
    for _sel, _col in ((_okg, _C_MED), (~_okg, '#aaa')):
        if _sel.any():
            _h = _hg[_sel]
            ax.errorbar(_h['efecto_pct'], _yy[_sel], xerr=[_h['efecto_pct'] - _h['ic95_inf_pct'],
                                                           _h['ic95_sup_pct'] - _h['efecto_pct']],
                        fmt='o', color=_col, ecolor='#bbb' if _col == '#aaa' else '#888', capsize=3)
    _surt9 = 'efecto_con_surtido_pct' in _hg.columns and _hg['efecto_con_surtido_pct'].notna().any()
    if _surt9:
        ax.scatter(_hg['efecto_con_surtido_pct'], _yy, marker='D', s=30, facecolors='none', edgecolors=_C_TPD, zorder=3)
    ax.axvline(0, color='#555', lw=1)
    ax.set_yticks(_yy); ax.set_yticklabels([f'{_g}: {_t} (vs {_b})' + ('' if _o else ' — poco dato')
                                            for _g, _t, _b, _o in zip(_hg['grupo'], _hg['termino'], _hg['base'], _okg)],
                                           fontsize=9)
    ax.set_xlabel('Efecto sobre 1 + brecha (%), mismos productos, IC 95% (errores agrupados por departamento)\n'
                  'en gris, los grupos con poco dato (celdas en menos de la mitad de los subtipos)'
                  + ('\nrombo rojo hueco: con el surtido de cada grupo (sin efectos de producto);'
                     '\nla distancia entre los dos es la parte del surtido' if _surt9 else ''))
    ax.set_title(f'Hedónica de grupos — {VENTANA_TXT}: región y empresa, cada una controlada por la otra', fontsize=11)
    _barras_horizontales(ax)
    _guardar('hedonica_grupos')

# 16) Prima de la misma marca contra la brecha de la canasta en las mismas celdas (últimos meses)
_pm9 = (prima_misma_marca[prima_misma_marca['periodo'].astype(str).str.startswith('últimos')]
        if len(prima_misma_marca) else prima_misma_marca)
if len(_pm9):
    _pm9 = _pm9.sort_values('brecha_canasta_mismas_celdas_pct').reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(11, max(4, 0.8 * len(_pm9) + 2)))
    _yy = np.arange(len(_pm9))
    ax.barh(_yy + 0.2, _pm9['brecha_canasta_mismas_celdas_pct'], height=0.38, color=_C_MED, edgecolor='black', lw=0.4,
            label='Brecha de la canasta (todos los productos del subtipo) en las mismas celdas')
    ax.barh(_yy - 0.2, _pm9['brecha_misma_marca_pct'], height=0.38, color='#f28e2b', edgecolor='black', lw=0.4,
            label='Sin TACC contra con TACC de la MISMA marca')
    for _i, _r in _pm9.iterrows():
        for _v, _dy in ((_r['brecha_canasta_mismas_celdas_pct'], 0.2), (_r['brecha_misma_marca_pct'], -0.2)):
            ax.annotate(f'{_v:+.0f}%', (_v, _i + _dy), xytext=(4, 0), textcoords='offset points', va='center', fontsize=8,
                        bbox=_FONDO_ETIQUETA)
    ax.set_yticks(_yy)
    ax.set_yticklabels([f'{_r.subtipo}: {str(_r.marca).title()} ({int(_r.celdas):,} celdas, {int(_r.empresas)} empresas)'
                        for _r in _pm9.itertuples(index=False)], fontsize=9)
    ax.axvline(0, color='#555', lw=1)
    ax.set_xlabel('Brecha (%), mediana entre las celdas (sucursal × mes × subtipo) donde la marca vende los dos lados')
    ax.set_title(f'Prima sin gluten de la misma marca contra la brecha de la canasta — {VENTANA_TXT}', fontsize=11)
    ax.legend(loc='lower right', fontsize=8)
    _barras_horizontales(ax)
    _guardar('prima_misma_marca')

# 17) Composición por empresa de cada universo y año (celdas sucursal × mes × subtipo): la de todas las sucursales cambia,
#     la del panel balanceado mucho menos
_ce9 = (composicion_empresas[composicion_empresas['periodo'].astype(str).str.fullmatch(r'\d{4}')]
        if len(composicion_empresas) else composicion_empresas)
if len(_ce9):
    _top9 = (_ce9.groupby('empresa')['celdas'].sum().sort_values(ascending=False).index[:7].tolist())
    _ce9 = _ce9.assign(_e=_ce9['empresa'].where(_ce9['empresa'].isin(_top9), 'Otras'))
    _cols9 = [_c for _c in _top9 + ['Otras'] if _c in set(_ce9['_e'])]     # mismos colores en los dos universos
    fig, axs = plt.subplots(1, 2, figsize=(14, 5.5), sharey=True)
    for _ax, _u in zip(axs, ('todas las sucursales', 'panel balanceado')):
        _x = _ce9[_ce9['universo'] == _u]
        _pv = (_x.pivot_table(index='periodo', columns='_e', values='pct_celdas', aggfunc='sum')
               .reindex(columns=_cols9).fillna(0))
        _pv.plot(kind='bar', stacked=True, ax=_ax, width=0.75, edgecolor='white', lw=0.5, legend=False,
                 color=plt.cm.tab10(np.arange(len(_pv.columns)) % 10))
        _ax.set_title(_u.capitalize(), fontsize=11, loc='left'); _ax.set_xlabel('')
        _ax.set_ylabel('% de las celdas (sucursal × mes × subtipo)'); _ax.set_ylim(0, 100)
        _ax.tick_params(axis='x', rotation=0); _ax.grid(True, alpha=0.3, axis='y')
    _h9, _l9 = axs[0].get_legend_handles_labels()
    fig.legend(_h9, _l9, loc='lower center', ncol=min(len(_l9), 8), fontsize=8, bbox_to_anchor=(0.5, -0.06))
    fig.suptitle('Composición por empresa de cada universo, por año', y=1.0)
    _guardar('composicion_empresas')"""))

# ── CELL 10 — MAPA COROPLÉTICO ─────────────────────────────────────────────────
cells.append(cell_code("""\
# ============================================================
# CELDA 10 — Mapa coroplético de la brecha de la canasta por provincia (últimos meses)
# ============================================================
# Estilo de los mapas (también el de la CELDA 12): verdes de los Excel de los otros notebooks y tipografía Lato (Google
# Fonts, licencia OFL), que se baja una vez a OUTPUT_DIR/_fuentes; si no se puede, la primera instalada de la lista.
VERDE_OSCURO, VERDE_CLARO, TEXTO_MAPA = '#375623', '#92D050', '#2B3A23'
def _fuente_mapa():
    from matplotlib import font_manager as _fm
    try:
        import urllib.request
        _dir = OUTPUT_DIR / '_fuentes'
        _dir.mkdir(exist_ok=True)
        for _v in ('Regular', 'Bold'):
            _f = _dir / f'Lato-{_v}.ttf'
            if not _f.exists():
                _b = urllib.request.urlopen(f'https://github.com/google/fonts/raw/main/ofl/lato/Lato-{_v}.ttf', timeout=15).read()
                _f.write_bytes(_b)
            _fm.fontManager.addfont(str(_f))
    except Exception as _e:
        print(f'  (aviso: no se pudo bajar la tipografía Lato: {_e})')
    _hay = {_x.name for _x in _fm.fontManager.ttflist}
    return next((_n for _n in ('Lato', 'Calibri', 'Segoe UI', 'Liberation Sans') if _n in _hay), 'DejaVu Sans')
FUENTE_MAPA = _fuente_mapa()

if not GEOJSON_PATH.exists():
    print(f'GeoJSON no encontrado en {GEOJSON_PATH} — saltear mapa')
else:
    with open(GEOJSON_PATH, 'r', encoding='utf-8') as f:
        geo = _json.load(f)
    NORM_GEO = {'Ciudad de Buenos Aires':'CABA'}
    AJUST = {'Salta':(0,-1),'Tucumán':(0.3,0),'Chaco':(0,-1),'Tierra del Fuego':(-1,-0.2),
             'Santa Fe':(0,1),'Santiago del Estero':(0.7,0)}
    def centroide(coords):
        xs,ys=[],[]
        if isinstance(coords[0][0][0],(int,float)):
            for p in coords[0]: xs.append(p[0]); ys.append(p[1])
        else:
            poly=max(coords,key=lambda p:len(p[0]))
            for p in poly[0]: xs.append(p[0]); ys.append(p[1])
        return sum(xs)/len(xs), sum(ys)/len(ys)
    def draw(ax,coords,color):
        if isinstance(coords[0][0][0],(int,float)):
            ax.fill([c[0] for c in coords[0]],[c[1] for c in coords[0]],facecolor=color,edgecolor='white',linewidth=0.6)
        else:
            for poly in coords:
                ax.fill([c[0] for c in poly[0]],[c[1] for c in poly[0]],facecolor=color,edgecolor='white',linewidth=0.6)
    cmap_m = LinearSegmentedColormap.from_list('c',
        ['#1a9850','#66bd63','#a6d96a','#fee08b','#fdae61','#f46d43','#d73027'], N=256)

    # Solo se colorean las provincias confiables (misma canasta: <= MAX_PESO_IMPUTADO% del peso con la brecha nacional y
    # >= MIN_SUC_AGG sucursales); las demás quedan en gris con su nombre (sus números están en la hoja Brecha_provincia)
    _pv = brecha_prov[brecha_prov['confiable']] if len(brecha_prov) else brecha_prov
    _prov_val = dict(zip(_pv['provincia'], _pv['brecha_canasta']))
    _con_datos = set(brecha_prov['provincia']) if len(brecha_prov) else set()
    _vals = list(_prov_val.values())
    if _vals:
      with plt.rc_context({'font.family': FUENTE_MAPA, 'text.color': TEXTO_MAPA}):
        norm_c = Normalize(vmin=min(_vals), vmax=max(_vals) if max(_vals) > min(_vals) else min(_vals) + 1)
        fig, ax = plt.subplots(figsize=(12, 16), facecolor='#FBFCF8'); caba_c = None
        for feat in geo['features']:
            nom = NORM_GEO.get(feat['properties']['name'], feat['properties']['name'])
            val = _prov_val.get(nom)
            col = cmap_m(norm_c(val)) if val is not None else '#E4E6DF'
            gt, co = feat['geometry']['type'], feat['geometry']['coordinates']
            draw(ax, [co] if gt=='Polygon' else co, col)
            cx, cy = centroide([co] if gt=='Polygon' else co)
            if nom == 'CABA': caba_c=(cx,cy); continue
            dx,dy = AJUST.get(nom,(0,0))
            if val is not None or nom in _con_datos:
                _tx = f'{nom}\\n{val:+.1f}%' if val is not None else f'{nom}\\n(pocos datos)'
                ax.text(cx+dx, cy+dy, _tx, ha='center', va='center', fontsize=8, linespacing=1.15,
                        fontweight='bold' if val is not None else 'normal', color=TEXTO_MAPA if val is not None else '#7A8070',
                        bbox=dict(boxstyle='square,pad=0.3', facecolor='#FBFCF8', alpha=0.85, edgecolor='#C9D9B8',
                                  linewidth=0.5))
        if caba_c and 'CABA' in _prov_val:
            vc = _prov_val['CABA']; cc = cmap_m(norm_c(vc)); lx,ly = caba_c[0]+2.2, caba_c[1]+0.8
            ax.annotate('', xy=caba_c, xytext=(lx,ly), arrowprops=dict(arrowstyle='-', color=VERDE_OSCURO, linewidth=1.0))
            ax.text(lx, ly, f'CABA\\n{vc:+.1f}%', ha='center', va='center', fontsize=9, fontweight='bold',
                    bbox=dict(boxstyle='square,pad=0.45', facecolor=cc, alpha=0.95, edgecolor=VERDE_OSCURO, linewidth=1.0))
            ax.plot(*caba_c, marker='o', markersize=9, markerfacecolor=cc, markeredgecolor=VERDE_OSCURO, markeredgewidth=1.2,
                    zorder=5)
        # escala de colores abajo a la derecha (sobre el mar, sin tapar Tierra del Fuego)
        _cax = ax.inset_axes([0.64, 0.14, 0.32, 0.012])
        _cb = fig.colorbar(plt.cm.ScalarMappable(norm=norm_c, cmap=cmap_m), cax=_cax, orientation='horizontal')
        _cb.outline.set_edgecolor('#C9D9B8'); _cb.ax.tick_params(labelsize=8, colors=TEXTO_MAPA, length=2)
        _dec = 0 if norm_c.vmax - norm_c.vmin >= 5 else 1
        _cb.ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda _v, _: f'{_v:+.{_dec}f}%'))
        _cb.set_label('Brecha de la canasta (sin TACC vs con TACC)', fontsize=8.5, color=TEXTO_MAPA, labelpad=3)
        ax.set_title(f'Brecha celíaca de la canasta por provincia', loc='left', fontsize=17, fontweight='bold',
                     color=VERDE_OSCURO, pad=26)
        ax.text(0, 1.012, f'{VENTANA_TXT} · misma canasta en todas las provincias · gris: menos de {MIN_SUC_AGG} sucursales '
                f'o más del {MAX_PESO_IMPUTADO}% del peso sin datos propios', transform=ax.transAxes, fontsize=9.5,
                color='#5F6B55', va='bottom')
        ax.plot([0, 0.35], [1.005, 1.005], transform=ax.transAxes, color=VERDE_CLARO, lw=3, clip_on=False)
        ax.set_aspect('equal'); ax.axis('off'); plt.tight_layout()
        _o = OUTPUT_DIR / f'mapa_brecha_{MES}.png'
        plt.savefig(_o, dpi=300, bbox_inches='tight', facecolor='#FBFCF8'); plt.show()
        print(f'Guardado: {_o.name} (tipografía {FUENTE_MAPA})')"""))

# ── CELL 11 — EXCEL ────────────────────────────────────────────────────────────
cells.append(cell_code(r"""# ============================================================
# CELDA 11 — Exportación Excel
# ============================================================
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
HDR_FILL = PatternFill(start_color='1F4E79', end_color='1F4E79', fill_type='solid')
HDR_FONT = Font(bold=True, color='FFFFFF', size=10)
HDR_ALIG = Alignment(horizontal='center', wrap_text=True, vertical='center')
def fmt_ws(ws):
    ws.row_dimensions[1].height = 30; ws.freeze_panes = 'A2'
    for cell in ws[1]: cell.fill = HDR_FILL; cell.font = HDR_FONT; cell.alignment = HDR_ALIG
def auto_widths(ws):
    for ci in range(1, ws.max_column+1):
        cl = get_column_letter(ci); hdr = str(ws.cell(1,ci).value or '').lower()
        ws.column_dimensions[cl].width = 34 if any(x in hdr for x in ('provincia','cadena','empresa','localidad','tipo',
                                                                      'desc','producto','sucursal','nombre','region')) else 14
        if any(x in hdr for x in ('brecha','base','celiaca','precio','100','tacc','grams','gramos','peso','relativo')):
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=ci, max_col=ci):
                for cell in row:
                    cell.number_format = ('+0.0"%"' if 'brecha' in hdr else '#,##0.00')
        elif hdr.endswith('_pp'):                # diferencias en puntos porcentuales (Serie_TPD)
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=ci, max_col=ci):
                for cell in row:
                    cell.number_format = '+0.0" pp"'

# ── Canasta (lo que entró) ────────────────────────────────────────────────────
_obs = datos_dia.groupby('ean_norm').agg(meses_con_precio=('mes','nunique'), primer_mes=('mes','min'),
                                         ultimo_mes=('mes','max'), obs_sucursal_mes=('mes','size'))
canasta = pd.DataFrame({'ean': sorted(EANS_CONFIG)})
canasta['tipo'] = canasta['ean'].map(EAN_TIPO)
canasta['lado'] = canasta['ean'].map(EAN_ROL).map({'tacc': 'con TACC', 'sin': 'sin TACC'})
canasta['descripcion'] = canasta['ean'].map(EAN_DESC)
canasta['producto'] = canasta['ean'].map(_PROD).fillna(canasta['descripcion'])
canasta['gramos'] = canasta['ean'].map(EAN_GRAMS)
canasta['subtipo'] = canasta['ean'].map(EAN_SUBTIPO)
_VIGX = {_norm_ean(k): v for k, v in globals().get('VIGENCIA', {}).items() if _norm_ean(k)}
canasta['vigente_desde'] = canasta['ean'].map(lambda _e: _VIGX.get(_e, (None, None))[0])
canasta['vigente_hasta'] = canasta['ean'].map(lambda _e: _VIGX.get(_e, (None, None))[1])
canasta = canasta.join(_obs, on='ean')
canasta['excluido_plausibilidad'] = canasta['ean'].isin(_bad)
canasta = canasta.sort_values(['tipo','lado','descripcion'])

# ── Detalle intra-sucursal por producto (último mes) ─────────────────────────
_ult = datos_dia[datos_dia['mes'] == ULTIMO_MES]
_det = _ult[['id_comercio','id_bandera','id_sucursal','ean_norm','tipo','rol','precio','dias','grams','precio_100']].copy()
_det['descripcion'] = _det['ean_norm'].map(EAN_DESC)
_det = _det.merge(suc_geo[['id_comercio','id_bandera','id_sucursal','cadena','empresa','PROVINCIA_NORM','region',
                           'sucursales_localidad','sucursales_nombre']],
                  on=['id_comercio','id_bandera','id_sucursal'], how='left')
_det = _det.rename(columns={'precio':'precio_mediano_mes','precio_100':'precio_100g'})
_det = _det[['cadena','empresa','PROVINCIA_NORM','region','sucursales_localidad','sucursales_nombre','id_comercio',
             'id_bandera','id_sucursal','tipo','rol','ean_norm','descripcion','grams','precio_mediano_mes','dias',
             'precio_100g']].sort_values(['PROVINCIA_NORM','cadena','sucursales_nombre','tipo','rol'])

# ── Brecha por SUCURSAL — último mes: canasta comparable (misma canasta de subtipos en todas; lo que la sucursal no
# tiene, con la brecha nacional del mes) y, de referencia, la canasta por cantidades de los tipos que tiene ──
_bsm = brecha_suc_mes[brecha_suc_mes['mes'] == ULTIMO_MES].copy()
_brecha_suc = (_bsm.merge(suc_geo[['id_comercio','id_bandera','id_sucursal','sucursales_nombre','departamento']],
                          on=['id_comercio','id_bandera','id_sucursal'], how='left')
               .rename(columns={'base':'canasta_con_tacc','celiaca':'canasta_sin_tacc',
                                'brecha_pct':'brecha_tipos_presentes','brecha_comparable':'brecha_canasta'})
               .sort_values('brecha_canasta', ascending=False)) if len(_bsm) else pd.DataFrame()
if len(_brecha_suc):
    _c1 = ['id_comercio','id_bandera','id_sucursal','mes','PROVINCIA_NORM','region','departamento','cadena','empresa',
           'localidad','sucursales_nombre','brecha_canasta','peso_propio_pct','n_tipos','brecha_tipos_presentes',
           'canasta_con_tacc','canasta_sin_tacc','suc_key']
    _brecha_suc = _brecha_suc[[c for c in _c1 if c in _brecha_suc.columns]]

# ── Comparación de productos EQUIVALENTES por sucursal (último mes) ───────────
_cu = _ult.copy()
_cu['subtipo'] = _cu['ean_norm'].map(EAN_SUBTIPO)
_cu['descripcion'] = _cu['ean_norm'].map(EAN_DESC)
def _items_lado(_g):
    _g = _g.sort_values('precio_100')
    return '; '.join(f'{_t.descripcion} ({int(_t.grams)}g, ${_t.precio_100:,.0f}/100g)' for _t in _g.itertuples(index=False))
_rows_c = []
for _kk, _g in _cu.groupby(['id_comercio','id_bandera','id_sucursal','tipo','subtipo','rol']):
    _rows_c.append((*_kk, _items_lado(_g), float(_g['precio_100'].median()), int(_g['ean_norm'].nunique())))
_cg = pd.DataFrame(_rows_c, columns=['id_comercio','id_bandera','id_sucursal','tipo','subtipo','rol','productos',
                                     'precio_100g_med','n'])
if len(_cg):
    _tc = _cg[_cg['rol']=='tacc'].drop(columns='rol').rename(columns={'productos':'productos_tacc','precio_100g_med':'precio_tacc_100g','n':'n_tacc'})
    _sc = _cg[_cg['rol']=='sin'].drop(columns='rol').rename(columns={'productos':'productos_sin','precio_100g_med':'precio_sin_100g','n':'n_sin'})
    _comp = _tc.merge(_sc, on=['id_comercio','id_bandera','id_sucursal','tipo','subtipo'], how='outer')
    _comp['n_tacc'] = _comp['n_tacc'].fillna(0).astype(int); _comp['n_sin'] = _comp['n_sin'].fillna(0).astype(int)
    _comp['equivalencia'] = np.where((_comp['n_tacc']>0) & (_comp['n_sin']>0), 'ambos',
                              np.where(_comp['n_tacc']>0, 'solo con TACC', 'solo sin TACC'))
    _comp['brecha_subtipo_pct'] = (_comp['precio_sin_100g'] / _comp['precio_tacc_100g'] - 1) * 100
    _comp = _comp.merge(suc_geo[['id_comercio','id_bandera','id_sucursal','cadena','PROVINCIA_NORM','sucursales_localidad',
                                 'sucursales_nombre']], on=['id_comercio','id_bandera','id_sucursal'], how='left')
    _comp = _comp[['cadena','PROVINCIA_NORM','sucursales_localidad','sucursales_nombre','id_comercio','id_bandera',
                   'id_sucursal','tipo','subtipo','equivalencia','n_tacc','productos_tacc','precio_tacc_100g','n_sin',
                   'productos_sin','precio_sin_100g','brecha_subtipo_pct']].sort_values(
                       ['PROVINCIA_NORM','cadena','sucursales_nombre','tipo','subtipo'])
else:
    _comp = pd.DataFrame()

leeme = pd.DataFrame({'hoja_o_columna': [
    'Resumen', 'Método', 'Canasta', 'Ponderaciones', 'Brecha_subtipo*', 'Brecha_tipo*', 'Serie_canasta*',
    'Brecha_provincia / region / empresa / cadena', '*_anual', 'brecha_canasta', 'n_min / confiable', 'Panel balanceado',
    'peso_imputado_pct', 'Imputaciones', 'Serie_TPD / Brecha_tipo_TPD', 'TPD_subtipos', 'TPD_anual', 'TPD_productos',
    'Brecha_sucursal', 'Concentracion', 'Sensibilidad', 'Indices_lados / Indices_lados_anual',
    'Disponibilidad / Disponibilidad_mensual', 'IC_grupos', 'Hedonica_grupos', 'Hedonica_grupos_anual',
    'Concentracion_modelos', 'Competencia_local', 'Composicion_empresas', 'Varianza_empresa', 'Surtido_empresa',
    'Prima_misma_marca', 'Costo_CBA / Costo_CBA_mensual', 'Carpeta datos/', 'Control_EAN', 'Plausibilidad',
    'Precios_atipicos', 'Precios_congelados', 'Fuente'],
    'definicion': [
    'Los números principales (nivel, evolución, tipos, regiones, cadenas, concentración, disponibilidad, costo y '
    'calidad de datos), cada uno con su IC 95% cuando lo hay y la hoja donde está el detalle. Brechas en %; los '
    'efectos hedónicos y de concentración, en % sobre 1 + brecha; el costo, en $ por mes.',
    'Brecha de un subtipo en una sucursal y mes = mediana $/100 g de los productos sin TACC presentes / mediana $/100 g de '
    'los con TACC presentes - 1 (los dos lados en el mismo super; los sabores de una misma línea, misma marca y '
    'presentación al mismo precio, cuentan como un producto). Brecha del tipo = promedio geométrico de las de sus '
    'subtipos con los dos lados (pesos iguales). Precio de un producto en el mes = mediana de sus precios diarios.',
    f"Productos de la {globals().get('NOMBRE_CANASTA', 'canasta fija 2022-2026')} (CELDA 1), con los meses en que "
    'tuvieron precio. Un producto que cambió de código '
    'ocupa una fila por código (misma columna producto; vigente_desde / vigente_hasta: meses en que se usa cada código), '
    'y los sabores de una línea, una fila por sabor (la línea en la columna producto). '
    'Lista con métricas: docs/brecha_celiaca/canasta_fija_2022_2026.csv; reglas: docs/BRECHA_CELIACA.md §14.',
    'Peso de cada tipo: % del gasto de los hogares en alimentos y bebidas no alcohólicas que va a sus artículos (ENGHo '
    '2017/18), renormalizado entre los tipos de la canasta; cantidades de la canasta por sucursal (peso / precio con '
    'TACC del año base).',
    'Por subtipo (crackers, snacks, spaghetti, rellenas...): mediana entre sucursal-mes de la brecha del subtipo, '
    'precios medianos $/100 g de cada lado y sucursales; todo el período y por año. Es la comparación de base.',
    'Por tipo: promedio geométrico (pesos iguales) de las brechas medianas de sus subtipos presentes en el grupo '
    '(brecha_mediana; ídem con el promedio sin outliers, brecha_prom, y el "más barato" ilustrativo, sesgado al alza), '
    'precios $/100 g de cada lado (promedio geométrico de los de sus subtipos), subtipos y sucursales.',
    'Canasta por mes (y año): sum_k w_k (1 + brecha del tipo k) - 1, con los pesos ENGHo.',
    f'Últimos {VENTANA_GEO_MESES} meses ({VENTANA_TXT}). Misma canasta en todos los grupos: el subtipo con menos de '
    f'{MIN_SUC_SUBTIPO} sucursales en el grupo toma la brecha nacional del período (subtipos_con_brecha_nacional), así '
    'un grupo sin snacks o sin obleas no cambia de composición. Una columna por tipo con su brecha y sus sucursales.',
    'Mismo cálculo por año (todas las sucursales del año; lo que falta en el grupo, con la brecha nacional de ese año).',
    'Brecha de la canasta del grupo o mes: sum_k w_k (1 + brecha del tipo k) - 1 (pesos ENGHo).',
    f'Series: n_min = sucursales del tipo con menos sucursales; confiable = están todos los tipos y n_min >= {MIN_SUC_AGG}. '
    f'Grupos: confiable = peso_imputado_pct <= {MAX_PESO_IMPUTADO} y n_sucursales >= {MIN_SUC_AGG}.',
    f'Solo sucursal x subtipo con los dos lados en >= {int(FRAC_MESES_PANEL * 100)}% de los meses: la serie no cambia '
    'por sucursales que entran o salen.',
    'Parte del peso de la canasta que no se midió: en la serie mensual, subtipos imputados con su último mes válido '
    '(pocas sucursales ese mes); en los grupos, subtipos con la brecha nacional del período.',
    'Rachas de meses en que un subtipo se imputa con su último mes válido en la serie mensual (todas las sucursales y '
    'panel balanceado): desde, hasta, sucursales que tenía y brecha arrastrada. Más de 3 meses: leer ese tramo con cuidado.',
    'Serie TPD (hedónica, CELDA 8b), robustez de la serie mensual: por subtipo, ln p = efecto de la celda (sucursal-mes '
    'del subtipo) + efecto de producto + prima sin TACC del mes (mínimos cuadrados; cada producto pesa 1 / productos de su '
    'lado en la celda). Brecha del subtipo = exp(nivel + prima del mes) - 1, con nivel = promedio de los efectos de los sin '
    'TACC - promedio de los con TACC (cada producto pesado por su disponibilidad en todo el período); tipo = promedio '
    'geométrico de sus subtipos; canasta con los pesos ENGHo. Canasta fija de productos; usa los subtipo-mes que la '
    'descriptiva imputa (menos de la mitad de sus sucursales) y solo con menos de '
    f'{MIN_SUC_SUBTIPO} sucursales con los dos lados mueve el subtipo (subtipos_movidos): en el panel, con la variación '
    'del mismo subtipo en todas las sucursales si ahí tiene dato; si no, con los demás subtipos de su tipo (el único '
    'subtipo de su tipo queda con el mes vecino); peso_movido_pct = parte del peso de la canasta en subtipos movidos, '
    'como peso_imputado_pct en la descriptiva. Dos universos: las celdas del panel balanceado y todas las '
    'sucursales, cada uno al lado de su descriptiva (y de cuánto se imputó en ella). IC 95% con errores agrupados por '
    'sucursal y la covarianza entre subtipos y tipos (en un mes movido, sin la incertidumbre de la imputación); '
    '*_ic95_*_empresa: con los errores agrupados por empresa (las cadenas fijan el precio de todas sus sucursales y sus '
    'precios se mueven juntos; es el IC para generalizar a otras cadenas; con pocas empresas, aproximado).',
    'Brecha TPD de cada subtipo por mes y universo, sucursales con los dos lados, si se movió (menos de '
    f'{MIN_SUC_SUBTIPO} sucursales) y con qué (movido_con: el mismo subtipo en todas las sucursales, los demás subtipos '
    'del tipo o el mes vecino).',
    'Promedio de los meses de cada año de la serie TPD y de la descriptiva: canasta (los dos universos) y tipos (panel).',
    'Por universo y subtipo: efecto estimado de cada producto (gamma, log), su peso en el nivel (disponibilidad) y su nivel '
    'contra el promedio ponderado de los con TACC del subtipo; en los sin TACC es la prima del producto en el mes base. '
    'referencia = producto fijado en 0.',
    'Último mes: brecha_canasta = canasta comparable (misma canasta de subtipos en todas las sucursales; lo que la '
    'sucursal no tiene con los dos lados, con la brecha nacional del mes; peso_propio_pct = parte medida en la sucursal). '
    'brecha_tipos_presentes = canasta por cantidades solo con los tipos que tiene (depende de cuántos tiene: no comparar).',
    'Por departamento (Georef): sucursales del universo, empresas, HHI de empresas (cuota = sucursales; el SEPA no tiene '
    'ventas), empresa principal, sucursales con brecha propia (>= 50% del peso medido en ellas) y su brecha mediana '
    f'(canasta comparable, últimos {VENTANA_GEO_MESES} meses). confiable = >= {MIN_SUC_DEPTO} sucursales con brecha.',
    f'Brecha nacional de los últimos {VENTANA_GEO_MESES} meses (misma canasta que los grupos) cambiando UNA decisión por '
    'vez (ESCENARIOS_SENSIBILIDAD, CELDA 1): galletas de arroz también en crackers, solo productos equivalentes, todos los '
    'productos que cumplen las reglas (ADICIONALES), cada sabor como un producto, pesos de los subtipos por disponibilidad, '
    'lo más barato de cada lado, el cociente de medianas nacionales y las sucursales ponderadas por la población de su '
    'provincia (mediana ponderada; PESOS_POBLACION). diferencia_pp = contra el escenario principal.',
    'Índices de precio de cada lado (base: primer mes = 100) por subtipo con efectos fijos: ln p(producto, sucursal, mes) = '
    'efecto del ítem (el producto en esa sucursal) + efecto del mes, así cada producto se compara consigo mismo en la misma '
    'sucursal, también entre meses no seguidos; el mes sin datos de un subtipo y lado repite el anterior '
    '(eslabones_imputados). Tipo = promedio geométrico de sus subtipos; Canasta = pesos ENGHo. sin_sobre_con > 100: '
    'los sin TACC aumentaron más. ipc_* = IPC del INDEC (IPC.xlsx del Drive) en la misma base.',
    'De las sucursal-meses que venden el tipo con TACC (productos de la canasta), % que vende también el sin TACC; '
    'ponderada = pesos ENGHo. Por país, región, provincia, empresa y cadena (últimos meses) y país mes a mes. La brecha se '
    'mide solo donde están los dos lados: no encontrar el producto también es un costo.',
    f'Intervalos de confianza del 95% ({BOOT_B} réplicas, semilla fija) de la brecha del país y de cada grupo con la '
    'misma canasta, y de su diferencia con el país (difiere_del_pais = su IC no incluye el 0). ic95_*: bootstrap por '
    'sucursal (la precisión con estas cadenas). ic95_*_empresa: bootstrap por empresa, con todas sus sucursales (las '
    'cadenas fijan el precio de todas sus sucursales: es el IC para generalizar a otras cadenas; país, regiones y '
    'provincias con 2 o más empresas; con pocas empresas, n_empresas, es aproximado).',
    'Regresión hedónica de los últimos meses: ln p = celda (sucursal × mes × subtipo) + producto + sinTACC × (región + '
    'empresa [+ HHI o empresas rivales cerca]). efecto_pct = cuánto más alta es 1 + brecha que en la base, con los mismos '
    'productos y controlando por lo demás; IC con errores agrupados por departamento y, en *_empresa, por empresa (no '
    'aplica a los efectos de empresa). Modelo "sin efectos de producto (con el surtido de cada grupo)": cada grupo compara '
    'sus productos; en el modelo principal, efecto_con_surtido_pct es ese efecto y efecto_surtido_pct la parte del '
    'surtido (exp(coef con surtido - coef mismos productos) - 1). confiable = el grupo tiene celdas (los dos lados en el '
    'mismo super y mes) en la mitad de los subtipos o más, cada uno en la mitad de los meses o más (subtipos_del_grupo); '
    'si no, su efecto depende de pocos productos y meses.',
    'Hedónica de grupos de cada año (todos sus meses): el modelo principal y el del surtido, con la región y la empresa '
    'base de la ventana. Dice si las diferencias entre regiones y cadenas (con los mismos productos) cambian en el tiempo.',
    'Regresiones por sucursal (errores agrupados por departamento y, en *_empresa, por empresa): la brecha de su canasta '
    'comparable y el nivel de cada lado (contra la mediana nacional) sobre el HHI del departamento, el HHI local o las '
    f'empresas rivales a <= {RADIO_COMPETENCIA_KM} km, sin controles, con empresa y con empresa y región.',
    f'Por sucursal: sucursales y empresas a <= {RADIO_COMPETENCIA_KM} km, empresas rivales, HHI local y del departamento, '
    'y la mediana de su brecha comparable en los últimos meses.',
    'Por universo (todas las sucursales, panel balanceado) y año (y la ventana): sucursales, sucursal-meses y celdas '
    '(sucursal × mes × subtipo con los dos lados) de cada empresa y su %. En todas las sucursales la composición cambia '
    'con los años; para la evolución, el panel balanceado.',
    'Por subtipo (y la canasta comparable), últimos meses: qué parte de la variación entre sucursales de su brecha '
    '(promedio de log(1 + brecha) de cada sucursal) explica la empresa, la región y las dos juntas (R², 0 a 1), y el '
    'desvío dentro de las empresas (log). Un R² de la empresa alto = la cadena fija el precio para todas sus sucursales: '
    'la unidad de decisión es la empresa (ver los IC por empresa).',
    'Por empresa, año y producto de la canasta: de las celdas de la empresa en el subtipo del producto, % en que el '
    'producto tiene precio. Las cadenas venden surtidos distintos que cambian con el tiempo: la brecha de una cadena '
    'compara sus productos (Hedonica_grupos separa esa parte).',
    'En los subtipos donde una MISMA marca vende los dos lados (MARCA y MARCA_EQUIVALENTE, CELDA 1), por período: '
    'brecha_misma_marca_pct = mediana entre celdas de sus sin TACC / sus con TACC - 1, contra la brecha de la canasta en '
    'las mismas celdas (todos los productos del subtipo) y en todas las celdas del subtipo (brecha_subtipo_pct). '
    'prima_de_marca_pct = mediana por celda de (1 + brecha de la canasta) / (1 + brecha de la misma marca) - 1: lo que '
    'agrega comparar con otras marcas. Separa la prima sin gluten de la prima de marca.',
    'Costo con la Canasta Básica Alimentaria del INDEC (gramos por adulto equivalente por mes; CBA_ITEMS): precio de cada '
    f'lado = mediana nacional de los últimos {MESES_CBA} meses; costo extra por adulto equivalente y por hogar tipo '
    f'({CBA_AE_HOGAR} AE). Cota inferior: solo los ítems con gluten que la canasta cubre. Mensual: la serie del costo.',
    'Paneles para el análisis propio (parquet y csv.gz; se unen por suc_key): panel_sucursal_mes_subtipo (brecha y '
    'precios de cada lado por sucursal, mes y subtipo, con región, empresa, cadena, departamento, HHI, competencia local, '
    'coordenadas, en_panel_balanceado y el peso ENGHo del tipo), panel_producto_sucursal_mes (precio de cada código de la '
    'canasta: producto, marca y gramos), panel_producto_sucursal_mes_adicionales (lo mismo para los ADICIONALES), '
    'productos.csv (cada código: tipo, subtipo, lado, producto, marca, gramos, vigencia y uso), sucursales.csv, '
    'diccionario_datos.csv (cada columna de cada archivo) y LEEME.md (cómo se calcula y reproduce la brecha y qué tener en '
    'cuenta al estimar).',
    'Precio de cada EAN relativo a la mediana del lado con TACC de su tipo, mes a mes; revisar = cambio de nivel x2 o '
    'salto x2 mes a mes (código reutilizado, presentación mal cargada). No excluye.',
    f'EANs excluidos por precio relativo a sus pares fuera de [1/{FACTOR_PLAUS}, {FACTOR_PLAUS}].',
    f'Empresa-código-mes descartados: la mediana de la empresa para ese código y mes está fuera de [1/{FACTOR_EMPRESA}, '
    f'{FACTOR_EMPRESA}] veces la mediana entre empresas (una por empresa, con >= 3 empresas): precios cargados a un '
    'tercio o al triple en toda una cadena, o de otra presentación.',
    f'Rachas en que una empresa repite el MISMO precio de un código {MESES_CONGELADO} meses seguidos o más mientras el '
    f'índice de su tipo y lado (mediana de la variación mensual entre empresa-códigos, encadenada) sube más de '
    f'{100 * SUBA_CONGELADO:.0f}%: un precio que la empresa dejó de actualizar en el SEPA. Se descartan los meses de la racha '
    'con el índice ya arriba de ese umbral (desde primer_mes_descartado). Ej.: Deheza, galletas de arroz Crisppino al '
    'mismo precio de abr-2023 a jul-2024.',
    'SEPA (zips semestrales del Drive). Desde ago-2026 los meses salen del SEPA diario (script 03), sin 8 comercios.']})

# ── Resumen: los números principales, cada uno con la hoja que tiene el detalle ──
_res = []
def _res_fila(_tema, _ind, _v, _inf=None, _sup=None, _u='%', _hoja=''):
    _nd = 0 if _u == '$' else (2 if _u.startswith('% sobre') else 1)
    _f = lambda _x: round(float(_x), _nd) if _x is not None and pd.notna(_x) else None
    _res.append({'tema': _tema, 'indicador': _ind, 'valor': _f(_v), 'ic95_inf': _f(_inf), 'ic95_sup': _f(_sup),
                 'unidad': _u, 'hoja': _hoja})
_vt = globals().get('VENTANA_TXT', '') or f'últimos {VENTANA_GEO_MESES} meses'
_icg = ic_grupos if len(ic_grupos) else pd.DataFrame(columns=['agrupacion','grupo','brecha_canasta','ic95_inf','ic95_sup',
                                                               'difiere_del_pais'])
for _x in _icg[_icg['agrupacion'] == 'País'].itertuples(index=False):
    _res_fila('Nivel', f'Brecha de la canasta, {_vt} (todas las sucursales, misma canasta que los grupos)', _x.brecha_canasta,
       _x.ic95_inf, _x.ic95_sup, _hoja='IC_grupos')
    if pd.notna(getattr(_x, 'ic95_inf_empresa', np.nan)):
        _res_fila('Nivel', f'La misma con el IC 95% por empresa (bootstrap de las {int(_x.n_empresas)} empresas: para '
                  'generalizar a otras cadenas)', _x.brecha_canasta, _x.ic95_inf_empresa, _x.ic95_sup_empresa, _hoja='IC_grupos')
if len(serie_mensual_bal):
    _u1 = serie_mensual_bal.sort_values('mes').iloc[-1]
    _res_fila('Nivel', f'Brecha de la canasta, {_u1["mes"]} (panel balanceado, descriptiva)', _u1['brecha_canasta'],
       _hoja='Serie_canasta_balanceada')
if len(serie_tpd) and 'brecha_canasta_tpd_panel' in serie_tpd.columns:
    _u1 = serie_tpd.sort_values('mes').iloc[-1]
    _res_fila('Nivel', f'Brecha de la canasta, {_u1["mes"]} (panel balanceado, TPD)', _u1['brecha_canasta_tpd_panel'],
       _u1['brecha_canasta_tpd_ic95_inf_panel'], _u1['brecha_canasta_tpd_ic95_sup_panel'], _hoja='Serie_TPD')
    if pd.notna(_u1.get('brecha_canasta_tpd_ic95_inf_empresa_panel')):
        _res_fila('Nivel', f'La misma con el IC 95% agrupado por empresa', _u1['brecha_canasta_tpd_panel'],
           _u1['brecha_canasta_tpd_ic95_inf_empresa_panel'], _u1['brecha_canasta_tpd_ic95_sup_empresa_panel'],
           _hoja='Serie_TPD')
for _x in serie_anual.itertuples(index=False):
    _res_fila('Evolución (canasta por año)', f'{_x.anio}, todas las sucursales', _x.brecha_canasta, _hoja='Canasta_anual')
for _x in serie_anual_bal.itertuples(index=False):
    _res_fila('Evolución (canasta por año)', f'{_x.anio}, panel balanceado', _x.brecha_canasta, _hoja='Canasta_anual_balanceada')
_il = indices_lados[indices_lados['nivel'] == 'Canasta'] if len(indices_lados) else indices_lados
if len(_il):
    _u1, _b1 = _il.iloc[-1], _il['mes'].iloc[0]
    _res_fila('Precios de cada lado', f'Índice con TACC, {_u1["mes"]} (base {_b1} = 100)', _u1['indice_con_tacc'], _u='índice',
       _hoja='Indices_lados')
    _res_fila('Precios de cada lado', f'Índice sin TACC, {_u1["mes"]} (base {_b1} = 100)', _u1['indice_sin_tacc'], _u='índice',
       _hoja='Indices_lados')
    _res_fila('Precios de cada lado', f'sin / con, {_u1["mes"]} (> 100: los sin TACC aumentaron más)', _u1['sin_sobre_con'],
       _u='índice', _hoja='Indices_lados')
    if 'ipc_alimentos' in _il.columns and _il['ipc_alimentos'].notna().any():
        _ua = _il.dropna(subset=['ipc_alimentos']).iloc[-1]
        _res_fila('Precios de cada lado', f'IPC alimentos del INDEC, {_ua["mes"]} (misma base)', _ua['ipc_alimentos'],
           _u='índice', _hoja='Indices_lados')
for _x in brecha_tipo.itertuples(index=False):
    _res_fila('Por tipo (todo el período)', _x.tipo, _x.brecha_mediana, _hoja='Brecha_tipo')
_icg = _icg.assign(confiable=_icg['confiable'].eq(True) if 'confiable' in _icg.columns else True)
def _difiere_txt(_x):
    # el IC de la fila es el del bootstrap por sucursal; el del bootstrap por empresa (generalizar a otras cadenas) puede
    # no confirmar la diferencia
    if not _x.difiere_del_pais:
        return ''
    _de = getattr(_x, 'difiere_del_pais_empresa', None)
    if _de is True or _de == 1:
        return ' (difiere del país, también con el IC por empresa)'
    if _de is False or _de == 0:
        return ' (difiere del país con el IC por sucursal; con el IC por empresa, no)'
    return ' (difiere del país)'
for _x in _icg[(_icg['agrupacion'] == 'Región') & _icg['confiable']].sort_values('brecha_canasta').itertuples(index=False):
    _res_fila(f'Geografía (región, {_vt})', _x.grupo + _difiere_txt(_x), _x.brecha_canasta,
       _x.ic95_inf, _x.ic95_sup, _hoja='IC_grupos / Brecha_region')
_prov_c = brecha_prov[brecha_prov['confiable']].sort_values('brecha_canasta') if len(brecha_prov) else brecha_prov
if len(_prov_c):
    _cp = 'provincia' if 'provincia' in _prov_c.columns else _prov_c.columns[0]
    _res_fila(f'Geografía (provincia, {_vt})', f'Menor: {_prov_c[_cp].iloc[0]} ({len(_prov_c)} provincias confiables)',
       _prov_c['brecha_canasta'].iloc[0], _hoja='Brecha_provincia')
    _res_fila(f'Geografía (provincia, {_vt})', f'Mayor: {_prov_c[_cp].iloc[-1]}', _prov_c['brecha_canasta'].iloc[-1],
       _hoja='Brecha_provincia')
for _x in _icg[(_icg['agrupacion'] == 'Empresa') & _icg['confiable']].sort_values('brecha_canasta').itertuples(index=False):
    _res_fila(f'Cadenas (canasta propia, {_vt})', _x.grupo, _x.brecha_canasta, _x.ic95_inf, _x.ic95_sup,
       _hoja='IC_grupos / Brecha_empresa')
_ne_nc = int(((_icg['agrupacion'] == 'Empresa') & ~_icg['confiable']).sum())
if _ne_nc:
    _res_fila(f'Cadenas (canasta propia, {_vt})', f'Otras {_ne_nc} empresas: más del {MAX_PESO_IMPUTADO}% del peso '
              'imputado o pocas sucursales (no confiables; ver la hedónica)', None, _u='', _hoja='Brecha_empresa')
_hgr = hedonica_grupos[hedonica_grupos['modelo'] == 'región y empresa'] if len(hedonica_grupos) else hedonica_grupos
for _gr, _tm in (('Región', 'Geografía (mismos productos, hedónica)'), ('Empresa', 'Cadenas (mismos productos, hedónica)')):
    for _x in (_hgr[_hgr['grupo'] == _gr].itertuples(index=False) if len(_hgr) else []):
        _res_fila(_tm, f'{_x.termino} contra {_x.base}' + ('' if getattr(_x, 'confiable', True) else ' (poco dato)'),
           _x.efecto_pct, _x.ic95_inf_pct, _x.ic95_sup_pct, _u='% sobre 1 + brecha', _hoja='Hedonica_grupos')
_ve = varianza_empresa[varianza_empresa['tipo'] == 'Canasta'] if len(varianza_empresa) else varianza_empresa
for _x in _ve.itertuples(index=False):
    _res_fila(f'Cadenas (variación entre sucursales, {_vt})', f'Parte que explica la empresa (R² de la canasta comparable, '
              f'{int(_x.sucursales):,} sucursales)', 100 * _x.r2_empresa, _hoja='Varianza_empresa')
    _res_fila(f'Cadenas (variación entre sucursales, {_vt})', 'Parte que explica la región', 100 * _x.r2_region,
              _hoja='Varianza_empresa')
_pmr = (prima_misma_marca[prima_misma_marca['periodo'].astype(str).str.startswith('últimos')]
        if len(prima_misma_marca) else prima_misma_marca)
for _x in _pmr.itertuples(index=False):
    _res_fila(f'Misma marca ({_vt})', f'{_x.subtipo}, {str(_x.marca).title()}: sin TACC / con TACC de la marca (la canasta en '
              f'las mismas celdas: {_x.brecha_canasta_mismas_celdas_pct:+.1f}%)', _x.brecha_misma_marca_pct,
              _hoja='Prima_misma_marca')
_cmr = (concentracion_modelos[concentracion_modelos['variable'].str.startswith('brecha')
                              & (concentracion_modelos['controles'] == 'empresa y región')]
        if len(concentracion_modelos) else concentracion_modelos)
for _x in _cmr.itertuples(index=False):
    _res_fila('Concentración (con empresa y región)', f'{_x.medida} ({_x.por}); p = {_x.p_valor:.2f}', _x.efecto_pct,
       _x.ic95_inf_pct, _x.ic95_sup_pct, _u='% sobre 1 + brecha', _hoja='Concentracion_modelos')
for _x in (disponibilidad[disponibilidad['agrupacion'] == 'País'].itertuples(index=False) if len(disponibilidad) else []):
    _res_fila('Disponibilidad', f'Sin TACC donde se vende el con TACC ({_x.medida}, ponderada)', _x.disponibilidad_ponderada_pct,
       _hoja='Disponibilidad')
if len(costo_cba):
    _t1 = costo_cba.iloc[-1]
    _res_fila('Costo (CBA del INDEC)', f'Extra por adulto equivalente por mes ({_t1["meses"]}; '
       f'{", ".join(costo_cba["item_cba"].iloc[:-1])})', _t1['costo_extra_ae'], _u='$', _hoja='Costo_CBA')
    _res_fila('Costo (CBA del INDEC)', f'Extra del hogar tipo ({CBA_AE_HOGAR} adultos equivalentes) por mes',
       _t1['costo_extra_hogar_tipo'], _u='$', _hoja='Costo_CBA')
    _res_fila('Costo (CBA del INDEC)', 'Prima del costo sin TACC sobre el con TACC', _t1['prima_pct'], _hoja='Costo_CBA')
for _x in (sensibilidad.itertuples(index=False) if len(sensibilidad) else []):
    _res_fila(f'Sensibilidad ({_vt}, una decisión por vez)', _x.escenario, _x.brecha_canasta, _hoja='Sensibilidad')
_res_fila('Calidad de datos', 'Empresa-código-mes con precio fuera de escala (descartados)', len(precios_atipicos), _u='casos',
   _hoja='Precios_atipicos')
_res_fila('Calidad de datos', f'Rachas de precio congelado de una empresa ({MESES_CONGELADO}+ meses iguales con el índice '
          f'arriba más de {100 * SUBA_CONGELADO:.0f}%; meses descartados)', len(precios_congelados), _u='rachas',
          _hoja='Precios_congelados')
_res_fila('Calidad de datos', 'EANs fuera por plausibilidad', len(plausibilidad), _u='EANs', _hoja='Plausibilidad')
_res_fila('Calidad de datos', 'EANs para revisar (control de identidad; no se excluyen)',
   int(control_ean['revisar'].sum()) if 'revisar' in control_ean.columns else 0, _u='EANs', _hoja='Control_EAN')
resumen = pd.DataFrame(_res, columns=['tema','indicador','valor','ic95_inf','ic95_sup','unidad','hoja'])

out_xls = OUTPUT_DIR / f"{globals().get('PREFIJO_EXCEL', 'brecha_celiaca')}_{ULTIMO_MES}.xlsx"
_hojas = [
    ('Leeme', leeme), ('Resumen', resumen), ('Canasta', canasta), ('Ponderaciones', ponderaciones), ('Cobertura', cobertura_tipo),
    ('Cobertura_mensual', cobertura_mensual), ('Brecha_subtipo', brecha_subtipo),
    ('Brecha_subtipo_anual', brecha_subtipo_anual), ('Brecha_subtipo_anual_balanc', brecha_subtipo_anual_bal),
    ('Brecha_tipo', brecha_tipo), ('Brecha_tipo_mes', brecha_tipo_mensual),
    ('Brecha_tipo_mes_balanceado', brecha_tipo_mensual_bal), ('Brecha_tipo_anual', brecha_tipo_anual),
    ('Brecha_tipo_anual_balanceado', brecha_tipo_anual_bal), ('Serie_canasta', serie_mensual),
    ('Serie_canasta_balanceada', serie_mensual_bal), ('Canasta_anual', serie_anual),
    ('Canasta_anual_balanceada', serie_anual_bal), ('Serie_TPD', serie_tpd), ('Brecha_tipo_TPD', brecha_tipo_tpd),
    ('TPD_subtipos', tpd_subtipos), ('TPD_anual', tpd_anual), ('TPD_productos', tpd_productos),
    ('Brecha_provincia', brecha_prov),
    ('Brecha_tipo_provincia', brecha_tipo_prov), ('Brecha_region', brecha_region),
    ('Brecha_tipo_region', brecha_tipo_region), ('Brecha_region_anual', brecha_region_anual),
    ('Brecha_empresa', brecha_empresa), ('Brecha_tipo_empresa', brecha_tipo_empresa),
    ('Brecha_empresa_anual', brecha_empresa_anual), ('Brecha_cadena', brecha_cadena), ('Concentracion', concentracion),
    ('Sensibilidad', sensibilidad), ('Indices_lados', indices_lados), ('Indices_lados_anual', indices_lados_anual),
    ('Disponibilidad', disponibilidad), ('Disponibilidad_mensual', disponibilidad_mensual), ('IC_grupos', ic_grupos),
    ('Hedonica_grupos', hedonica_grupos), ('Hedonica_grupos_anual', hedonica_grupos_anual),
    ('Concentracion_modelos', concentracion_modelos), ('Competencia_local', competencia_local),
    ('Composicion_empresas', composicion_empresas), ('Varianza_empresa', varianza_empresa),
    ('Surtido_empresa', surtido_empresa), ('Prima_misma_marca', prima_misma_marca),
    ('Costo_CBA', costo_cba), ('Costo_CBA_mensual', costo_cba_mensual),
    ('Brecha_sucursal', _brecha_suc), ('Comparacion_productos', _comp), ('Detalle_producto', _det),
    ('Imputaciones', imputaciones), ('Control_EAN', control_ean), ('Plausibilidad', plausibilidad),
    ('Precios_atipicos', precios_atipicos), ('Precios_congelados', precios_congelados)]
with pd.ExcelWriter(out_xls, engine='openpyxl') as writer:
    for _sn, _df in _hojas:
        (_df if len(_df.columns) else pd.DataFrame({'(sin datos)': []})).to_excel(writer, sheet_name=_sn, index=False)
    for sn in writer.sheets:
        ws = writer.sheets[sn]; fmt_ws(ws); auto_widths(ws)
    writer.sheets['Leeme'].column_dimensions['B'].width = 140
    for _cl, _wd in zip('ABCDEFG', (34, 95, 12, 12, 12, 18, 30)):
        writer.sheets['Resumen'].column_dimensions[_cl].width = _wd
print(f'Excel guardado: {out_xls}')
print(f'  {len(_hojas)} hojas · Detalle_producto {len(_det):,} filas · Comparacion_productos {len(_comp):,} · '
      f'Brecha_sucursal {len(_brecha_suc):,}')
print('  Para empezar: la hoja Resumen (los números principales con la hoja de cada detalle); Brecha_tipo (por tipo) y '
      'Serie_canasta_balanceada / Canasta_anual_balanceada (evolución).')"""))

# ── CELL 12 — MAPA FOLIUM POR SUCURSAL (lazy-load) ─────────────────────────────
cells.append(cell_code("""\
# ============================================================
# CELDA 12 — Mapa Folium interactivo POR SUCURSAL (brecha celíaca, último dato de cada sucursal)
# ============================================================
# Un punto por supermercado; color VERDE→ROJO graduado por la brecha de la canasta COMPARABLE de esa sucursal (misma
# canasta de subtipos en todas; lo que la sucursal no tiene con los dos lados, con la brecha nacional del mes: si no, el
# color dependía de cuántos tipos tiene cada sucursal). LIVIANO: los popups se arman al hacer clic (lazy-load desde un
# JSON compacto). Popup: (1) brecha comparable, parte del peso medida en la sucursal y valor de cada canasta; (2)
# productos por EQUIVALENCIA (subtipo) — con TACC vs sin TACC, con presentación y $/100g; (3) cadena +
# localidad/provincia. La brecha AUTORITATIVA es la del tipo (§3). Filtro por cadena (LayerControl) + pantalla
# completa. Mosaicos: Esri World Light Gray (sin API key y responde desde la red del INECO, BUG-32) + límites
# provinciales dibujados desde el ar.json local (se ven aunque la red bloquee los mosaicos).
import folium
from folium.plugins import Fullscreen
from branca.colormap import LinearColormap
import json as _json

# Estilo: verdes de los otros notebooks y tipografía Lato (Google Fonts; sin red, la del sistema)
_VO, _VC, _TX, _TX2 = '#375623', '#92D050', '#2B3A23', '#5F6B55'
_FUENTE = "Lato,'Segoe UI',Tahoma,sans-serif"

# Snapshot = ÚLTIMA brecha disponible POR SUCURSAL dentro de una ventana de meses (cadenas que no informaron el
# último mes aparecen con su dato más reciente; el popup indica de qué mes es).
_sk3m = ['id_comercio','id_bandera','id_sucursal']
VENTANA_MAPA_MESES = 6
_meses_ord = sorted(brecha_suc_mes['mes'].unique())
_meses_win = set(_meses_ord[-VENTANA_MAPA_MESES:]) if _meses_ord else set()
_bsm_w = brecha_suc_mes[brecha_suc_mes['mes'].isin(_meses_win) & brecha_suc_mes['brecha_comparable'].notna()]
_bk = (_bsm_w.sort_values('mes').groupby(_sk3m, as_index=False).tail(1)
       .merge(suc_geo[['id_comercio','id_bandera','id_sucursal','sucursales_nombre',
                       'sucursales_latitud','sucursales_longitud']],
              on=_sk3m, how='left')
       .dropna(subset=['sucursales_latitud','sucursales_longitud']))
_um = _meses_ord[-1] if _meses_ord else ULTIMO_MES
_sel_mes = _bk[_sk3m + ['mes']]

_btm = bt_sm.merge(_sel_mes, on=_sk3m + ['mes'], how='inner')[_sk3m + ['tipo','tacc','sin','brecha_pct']]
_bt_por_suc = {}
for _r in _btm.itertuples(index=False):
    _bt_por_suc.setdefault((_r.id_comercio, _r.id_bandera, _r.id_sucursal), {})[_r.tipo] = (_r.tacc, _r.sin, _r.brecha_pct)

_pu = datos_dia.merge(_sel_mes, on=_sk3m + ['mes'], how='inner').copy()
_pu['descripcion'] = _pu['ean_norm'].map(EAN_DESC)
_pu['subtipo'] = _pu['ean_norm'].map(EAN_SUBTIPO)
_prod = {}
for _r in _pu.itertuples(index=False):
    _d = (_prod.setdefault((_r.id_comercio, _r.id_bandera, _r.id_sucursal), {})
              .setdefault(_r.tipo, {}).setdefault(_r.subtipo, {'A': [], 'B': []}))
    _d['A' if _r.rol == 'tacc' else 'B'].append((str(_r.descripcion)[:38], _r.grams, _r.precio_100))

def _iround(_x):
    try: return int(round(float(_x)))
    except Exception: return None
def _p_arr(_lst):
    _lst = sorted(_lst, key=lambda x: (x[2] if x[2] == x[2] else 9e9))[:8]
    return [[_d, (int(_g) if (_g == _g and _g > 0) else 0), (_iround(_p) if _p == _p else None)] for _d, _g, _p in _lst]

_pd = {}
for _r in _bk.itertuples(index=False):
    _skk = (_r.id_comercio, _r.id_bandera, _r.id_sucursal)
    _key = f'{_r.id_comercio}_{_r.id_bandera}_{_r.id_sucursal}'
    _tipos = _bt_por_suc.get(_skk, {})
    _T = []
    for _tp in sorted(_tipos, key=lambda t: -_tipos[t][2]):
        _tacc_p, _sin_p, _brk = _tipos[_tp]
        _subs = _prod.get(_skk, {}).get(_tp, {})
        def _ord(_s):
            _d = _subs[_s]; return (0 if (_d['A'] and _d['B']) else 1, _s)
        _S = [{'s': _s, 'A': _p_arr(_subs[_s]['A']), 'B': _p_arr(_subs[_s]['B'])} for _s in sorted(_subs, key=_ord)]
        _T.append({'t': _tp, 'ta': _iround(_tacc_p), 'si': _iround(_sin_p), 'g': _iround(_brk), 'S': _S})
    _pd[_key] = {'c': str(_r.cadena), 'n': str(_r.sucursales_nombre)[:46], 'p': str(_r.PROVINCIA_NORM),
                 'l': str(_r.localidad), 'm': str(_r.mes), 'b': _iround(_r.brecha_comparable),
                 'pp': _iround(_r.peso_propio_pct), 'bt': _iround(_r.brecha_pct), 'bs': _iround(_r.base),
                 'cl': _iround(_r.celiaca), 'nt': int(_r.n_tipos), 'T': _T}
_json_str = _json.dumps(_pd, ensure_ascii=False, separators=(',', ':'))

_vmin = float(_bk['brecha_comparable'].quantile(0.05)); _vmax = float(_bk['brecha_comparable'].quantile(0.95))
if _vmin == _vmax: _vmin, _vmax = float(_bk['brecha_comparable'].min()), float(_bk['brecha_comparable'].max()) + 1
_cm = LinearColormap(colors=['#1a9850','#66bd63','#a6d96a','#fee08b','#fdae61','#f46d43','#d73027'],
                     vmin=_vmin, vmax=_vmax, caption=f'Brecha de canasta celíaca (%) — {NOMBRE_MES_TITLE}')

m = folium.Map(location=[-38.0, -63.5], zoom_start=5, tiles=None, control_scale=True)
_ESRI = 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/'
folium.TileLayer(tiles=_ESRI + 'World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}', attr='Esri, HERE, Garmin, OSM',
                 name='Esri Light Gray', control=False).add_to(m)
folium.TileLayer(tiles=_ESRI + 'World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}', attr='Esri',
                 name='Esri nombres', control=False, overlay=True).add_to(m)
try:
    if 'GEOJSON_PATH' in dir() and Path(GEOJSON_PATH).exists():
        with open(GEOJSON_PATH, 'r', encoding='utf-8') as _gf:
            _geo_base = _json.load(_gf)
        folium.GeoJson(_geo_base, name='Límites provinciales', control=False,
                       style_function=lambda _f: {'color': '#7D8A70', 'weight': 0.9,
                                                  'fillColor': '#F1F4EC', 'fillOpacity': 0.25}
                       ).add_to(m)
except Exception as _e:
    print(f'  (aviso: no se pudieron dibujar los límites provinciales: {_e})')
_cm.add_to(m)
Fullscreen(position='topright', title='Pantalla completa', title_cancel='Salir').add_to(m)

_fgs = {}
def _fg(_cad):
    if _cad not in _fgs:
        _fgs[_cad] = folium.FeatureGroup(name=str(_cad), show=True)
    return _fgs[_cad]

for _r in _bk.itertuples(index=False):
    _key = f'{_r.id_comercio}_{_r.id_bandera}_{_r.id_sucursal}'
    _b = float(_r.brecha_comparable); _col = _cm(max(_vmin, min(_vmax, _b)))
    _ph = (f'<div class="lz-pop" data-key="{_key}" style="min-width:320px">'
           f'<span style="color:#8C9682;font-size:12px">Cargando detalle…</span></div>')
    folium.CircleMarker(
        location=[_r.sucursales_latitud, _r.sucursales_longitud],
        radius=6, color=_TX, weight=0.6, fill=True, fillColor=_col, fillOpacity=0.9,
        tooltip=(f'<b>{_r.cadena}</b><br>{_r.PROVINCIA_NORM}<br>Brecha <b>{_b:+.0f}%</b> '
                 f'({_r.peso_propio_pct:.0f}% de la canasta medida acá)'),
        popup=folium.Popup(_ph, max_width=500)
    ).add_to(_fg(_r.cadena))

for _c in sorted(_fgs): _fgs[_c].add_to(m)
folium.LayerControl(collapsed=True, position='topright').add_to(m)

_med_nac = _bk['brecha_comparable'].median()
_info = (f'<div style="position:fixed;top:12px;left:52px;width:340px;background:#FBFCF8;border:1px solid {_VO};'
         f'border-left:6px solid {_VO};border-radius:2px;padding:11px 14px 12px;font-family:{_FUENTE};z-index:9999;'
         f'box-shadow:0 1px 4px rgba(0,0,0,.12)">'
         f'<div style="color:{_VO};font-size:17px;font-weight:700;letter-spacing:.2px;margin-bottom:2px">'
         f'Brecha celíaca por sucursal</div>'
         f'<div style="height:3px;width:70px;background:{_VC};margin:4px 0 7px"></div>'
         f'<div style="font-size:12px;color:{_TX2};line-height:1.55">Última brecha disponible por sucursal '
         f'(últimos {VENTANA_MAPA_MESES} meses) · <b>{len(_bk):,}</b> sucursales · <b>{len(_fgs)}</b> cadenas<br>'
         f'Brecha mediana: <b>{_med_nac:+.0f}%</b> · el popup indica de qué mes es cada dato<br>'
         f'Misma canasta en todas: lo que una sucursal no vende, con la brecha nacional del mes<br>'
         f'<span style="color:#1a9850">■</span> menor &nbsp; <span style="color:#d73027">■</span> mayor brecha &nbsp;·&nbsp; '
         f'filtrá cadenas con el control de capas (arriba der.)</div></div>')
m.get_root().header.add_child(folium.Element(
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link href="https://fonts.googleapis.com/css2?family=Lato:wght@400;700&display=swap" rel="stylesheet">'
    f'<style>.leaflet-container,.leaflet-tooltip,.leaflet-popup-content,.leaflet-control-layers,.legend,.legend text'
    f'{{font-family:{_FUENTE} !important;color:{_TX}}}'
    f'.leaflet-popup-content-wrapper{{border-radius:3px;border-top:4px solid {_VO}}}'
    f'.leaflet-tooltip{{border:1px solid #C9D9B8;border-radius:2px}}</style>'))
m.get_root().html.add_child(folium.Element(_info))
m.get_root().html.add_child(folium.Element(f'<script type="application/json" id="_pd_json">{_json_str}</script>'))

_MV = m.get_name()
_JS = '''<script>
var _MV="__MAPVAR__", _MES="__MES__", _PD=null, _VO="__VO__", _VC="__VC__";
function _gpd(){ if(!_PD){ var el=document.getElementById("_pd_json"); if(el) _PD=JSON.parse(el.textContent); } return _PD; }
function _fmt(x){ return "$"+Number(x).toLocaleString("es-AR"); }
function _sg(x){ return (x>=0?"+":"")+x; }
function _plist(a){ if(!a||!a.length) return '<span style="color:#bbb">—</span>'; var s=""; for(var i=0;i<a.length;i++){ var g=a[i][1]?a[i][1]+" g":"s/pres"; var p=(a[i][2]!=null)?_fmt(a[i][2])+"/100g":"s/precio"; s+='<div style="margin:1px 0">· '+a[i][0]+' <span style="color:#6B7563">('+g+", "+p+')</span></div>'; } return s; }
function _bpop(k){ var pd=_gpd(); if(!pd||!pd[k]) return "<div>Sin datos.</div>"; var d=pd[k];
  var h='<div style="font-size:12px;color:#2B3A23;min-width:360px;max-width:480px;max-height:520px;overflow-y:auto">';
  h+='<div style="font-size:15px;font-weight:700;color:'+_VO+'">'+d.n+'</div>';
  h+='<div style="color:#5F6B55;margin-bottom:6px">'+d.c+" · "+d.l+", "+d.p+'</div>';
  h+='<div style="padding:7px 8px;background:#EEF4E6;border-left:3px solid '+_VC+';margin-bottom:4px">Brecha de la canasta celíaca: <b style="font-size:15px">'+_sg(d.b)+'%</b><br><span style="color:#6B7563;font-size:11px">Misma canasta en todas las sucursales: '+d.pp+'% medida acá; lo que no vende, con la brecha nacional del mes</span><br>Solo con sus '+d.nt+' tipo(s): '+_sg(d.bt)+'% · canasta con TACC <b>'+_fmt(d.bs)+'</b> · sin TACC <b>'+_fmt(d.cl)+'</b> <span style="color:#6B7563">($/100g ponderado)</span><br><span style="color:#6B7563;font-size:11px">dato de '+d.m+'</span></div>';
  for(var i=0;i<d.T.length;i++){ var t=d.T[i];
    h+='<div style="margin-top:8px;font-weight:700;color:'+_VO+'">'+t.t+" · brecha del tipo "+_sg(t.g)+'% <span style="color:#6B7563;font-weight:normal">(mediana con TACC '+_fmt(t.ta)+" vs sin "+_fmt(t.si)+'/100g)</span></div>';
    h+='<table style="border-collapse:collapse;width:100%;font-size:11px"><tr style="background:'+_VO+';color:#fff"><th style="padding:2px">Equivalente</th><th style="padding:2px">Con TACC</th><th style="padding:2px">Sin TACC</th></tr>';
    for(var j=0;j<t.S.length;j++){ var s=t.S[j];
      h+='<tr><td style="border:1px solid #D5DEC9;padding:3px;vertical-align:top;font-weight:600">'+s.s+'</td><td style="border:1px solid #D5DEC9;padding:3px;vertical-align:top">'+_plist(s.A)+'</td><td style="border:1px solid #D5DEC9;padding:3px;vertical-align:top">'+_plist(s.B)+'</td></tr>';
    }
    h+="</table>";
  }
  h+='<div style="color:#8C9682;font-size:10px;margin-top:6px">Filas = productos equivalentes. La brecha autoritativa es la del tipo (§3); acá se listan los productos comparados de cada lado.</div></div>';
  return h;
}
function _init(){ var mp=window[_MV]; if(!mp){ setTimeout(_init,300); return; } mp.on("popupopen",function(e){ var el=e.popup.getElement().querySelector(".lz-pop"); if(el&&el.getAttribute("data-b")!=="1"){ el.innerHTML=_bpop(el.getAttribute("data-key")); el.setAttribute("data-b","1"); e.popup.update(); } }); }
setTimeout(_init,500);
</script>'''
_JS = _JS.replace('__MAPVAR__', _MV).replace('__MES__', NOMBRE_MES_TITLE).replace('__VO__', _VO).replace('__VC__', _VC)
m.get_root().html.add_child(folium.Element(_JS))

_out_map = OUTPUT_DIR / f'mapa_sucursales_brecha_{MES}.html'
m.save(str(_out_map))
print(f'Mapa Folium por sucursal guardado: {_out_map}')
print(f'  {len(_bk):,} sucursales · {len(_fgs)} cadenas (últimos {VENTANA_MAPA_MESES} meses; incluye cadenas sin dato el último mes)'
      f' · popup lazy-load · límites del GeoJSON local · JSON {len(_json_str)/1024/1024:.1f} MB')
_mmix = _bk['mes'].value_counts().to_dict()
print(f'  Meses del snapshot (sucursal→mes más reciente): ' + ', '.join(f'{_m}:{_n}' for _m,_n in sorted(_mmix.items(), reverse=True)))"""))

# ── Write notebook ──────────────────────────────────────────────────────────────
nb = {
    'cells': cells,
    'metadata': {
        'kernelspec': {'display_name':'Python 3','language':'python','name':'python3'},
        'language_info': {'codemirror_mode':{'name':'ipython','version':3},
                          'file_extension':'.py','mimetype':'text/x-python',
                          'name':'python','nbformat':4,'pygments_lexer':'ipython3','version':'3.10.0'}
    },
    'nbformat': 4,
    'nbformat_minor': 5
}
out_path = os.path.join(HERE, '06_evolucion_brecha_celiaca.ipynb')
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
print(f'Written: {out_path}')
print(f'Cells: {len(cells)}')


# ══ nb06b: la misma brecha con la CANASTA AMPLIA de la oferta actual (BRECHA_CELIACA §16) ══════════════════════════════
# Las celdas 2 a 13 son las del nb06; cambian la celda 0 (texto) y la CELDA 1: la canasta (CSV de s18 con 10 tipos),
# sus pesos ENGHo, la ventana (ago-2025 → hoy), la carpeta de salida, el nombre del Excel, el pan y la harina de la CBA y
# los escenarios de sensibilidad (la canasta amplia no tiene sustitutos adentro).
CANASTA_CSV = os.path.join(HERE, '..', 'docs', 'brecha_celiaca', 'canasta_amplia_2025_2026.csv')
SENS_CSV = os.path.join(HERE, '..', 'docs', 'brecha_celiaca', 'productos_sensibilidad_amplia.csv')
PESOS_ENGHO = {**PESOS_ENGHO,
               'Pan envasado': (0.792, 'A0111109 + A0111110 + A0111113 + A0111118 (pan envasado)'),
               'Harinas': (0.593, 'A0111210 Harina de trigo (sin TACC: la premezcla universal que la reemplaza)'),
               'Premezclas': (0.133, 'A0111211 Mezclas para pizza y ñoquis + A0119205 Polvo para bizcochuelo'),
               'Alfajores': (0.549, 'A0118401 Alfajores'),
               'Tapas': (0.520, 'A0111311 + A0111312 (tapas de empanadas y tartas)')}
ORDEN_TIPOS = list(PESOS_ENGHO)

def _reemplazar(_txt, _pares):
    for _o, _n in _pares:
        assert _txt.count(_o) == 1, f'nb06b: no está (o está más de una vez) {_o[:70]!r}'
        _txt = _txt.replace(_o, _n)
    return _txt

_MD0_B = """# SEPA — Brecha Celíaca (TACC vs sin-TACC), canasta amplia de la oferta actual (nb06b)

**Objetivo:** el **nivel** de la brecha de precios entre productos **con TACC** y sus equivalentes **sin TACC** con una
canasta que cubre más de la dieta celíaca, y cómo se distribuye **geográficamente**, **entre cadenas** y según la
**concentración de puntos de venta**, en los últimos 15 meses (desde agosto de 2025). La **evolución 2022-2026** es la
del nb06 (canasta fija): muchos sin TACC de esta canasta no existían o casi no estaban en 2022.

**Canasta amplia:** las mismas reglas que la canasta fija (lado sin TACC verificado, continuidad, cobertura geográfica y
por cadenas, subtipos comparables, equivalentes primero, la misma marca primero, composición espejada y líneas) sobre la
ventana ago-2025 → oct-2026, con **10 tipos**: los 5 de la canasta fija más **pan envasado, harinas, premezclas,
alfajores y tapas** de empanadas y tartas (62% del gasto en los artículos con gluten de la ENGHo, contra 41% de la
canasta fija; el pan francés fresco no está en el SEPA). Reglas y resultados: `docs/BRECHA_CELIACA.md` §16; lista con
métricas: `docs/brecha_celiaca/canasta_amplia_2025_2026.csv` (la arma `s18_canasta_amplia.py`).

**Medición:** la misma del nb06 (brecha dentro de cada súper por subtipo, $/100 g → tipo → canasta con pesos ENGHo;
grupos con la misma canasta de subtipos; TPD; análisis complementarios de la CELDA 8c, con el costo extra del pan y la
harina de la Canasta Básica Alimentaria del INDEC).

**Qué sale** (en `OUTPUT_DIR`, otra carpeta que la del nb06): `brecha_celiaca_amplia_AAAA-MM.xlsx` (hojas `Leeme` y
`Resumen` primero), los gráficos `*.png`, los mapas y la carpeta `datos/`.

**Config en la CELDA 1.** Las celdas 2 a 13 son las del nb06 (las genera el mismo `notebooks/gen_nb06.py`)."""

_PRE_B = _reemplazar(_CONFIG_PRE, [(
    '# CANASTA FIJA 2022-2026 (docs/BRECHA_CELIACA.md §14; lista con métricas: docs/brecha_celiaca/canasta_fija_2022_2026.csv)',
    '# CANASTA AMPLIA de la oferta actual, ago-2025 -> hoy (docs/BRECHA_CELIACA.md §16; lista con métricas:\n'
    '# docs/brecha_celiaca/canasta_amplia_2025_2026.csv, de s18_canasta_amplia.py)')])
_POST_B = _reemplazar(_CONFIG_POST, [
    ("ESCENARIOS_SENSIBILIDAD = {\n"
     "    'Principal (la canasta de la CELDA 1)': {},\n"
     "    'Galletas de arroz también en crackers (sustitución)': {'agregar': 'sustitutos'},\n"
     "    'Solo productos equivalentes (sin las galletas de arroz de saborizadas)': {'quitar_sustitutos': True},\n",
     "ESCENARIOS_SENSIBILIDAD = {\n"
     "    'Principal (la canasta de la CELDA 1)': {},\n"
     "    'Sustitutos también (galletas y alfajores de arroz, harina de arroz)': {'agregar': 'sustitutos'},\n"),
    ("CBA_ITEMS = [('Fideos', 'Fideos secos', None, 1740),\n"
     "             ('Galletitas de agua', 'Galletitas saladas y crackers', 'Crackers', 420),\n"
     "             ('Galletitas dulces', 'Galletitas dulces', None, 210),\n"
     "             ('Pan', 'Pan envasado', None, 6750),\n"
     "             ('Harina de trigo', 'Harinas', None, 1080)]",
     "# El pan de la CBA es sobre todo pan francés fresco, que no está en el SEPA: se costea con el pan de molde y de mesa\n"
     "# envasado de los dos lados (el con TACC envasado es más caro que el francés: el costo extra es una cota inferior).\n"
     "CBA_ITEMS = [('Fideos', 'Fideos secos', None, 1740),\n"
     "             ('Galletitas de agua', 'Galletitas saladas y crackers', 'Crackers', 420),\n"
     "             ('Galletitas dulces', 'Galletitas dulces', None, 210),\n"
     "             ('Pan', 'Pan envasado', 'Pan de molde y de mesa', 6750),\n"
     "             ('Harina de trigo', 'Harinas', None, 1080)]"),
    ("NOMBRE_CANASTA = 'canasta fija 2022-2026'   # en los títulos de los gráficos\n"
     "PREFIJO_EXCEL = 'brecha_celiaca'            # el Excel se llama <PREFIJO_EXCEL>_<AAAA-MM>.xlsx\n",
     "NOMBRE_CANASTA = 'canasta amplia ago-2025 → hoy'   # en los títulos de los gráficos\n"
     "PREFIJO_EXCEL = 'brecha_celiaca_amplia'            # el Excel se llama <PREFIJO_EXCEL>_<AAAA-MM>.xlsx\n"),
    ("OUTPUT_DIR  = '/content/drive/MyDrive/carga/output_brecha'",
     "OUTPUT_DIR  = '/content/drive/MyDrive/carga/output_brecha_amplia'   # otra carpeta que la del nb06 (y otro caché)"),
    ("MES_INICIO_HISTORICO = '2022-01'   # la canasta fija se eligió con continuidad desde enero de 2022",
     "MES_INICIO_HISTORICO = '2025-08'   # la canasta amplia se eligió con continuidad desde agosto de 2025"),
])
cells_b = [cell_md(_MD0_B), cell_code(_PRE_B + _bloque_canasta() + _POST_B)] + cells[2:]
out_b = os.path.join(HERE, '06b_brecha_celiaca_canasta_amplia.ipynb')
with open(out_b, 'w', encoding='utf-8') as f:
    json.dump({**nb, 'cells': cells_b}, f, ensure_ascii=False, indent=1)
print(f'Written: {out_b}')
print(f'Cells: {len(cells_b)}')
