"""Genera 07_evolucion_canastas_alternativas.ipynb  (v5 - motor para informe semanal).

Cambios v5 respecto de v4 (pedidos para el informe semanal del equipo de economistas):
 1. SEMANA que cierra el JUEVES (ventana viernes->jueves), etiquetada por fecha de cierre.
 2. INDICE ENCADENADO de muestra apareada (matched-sample): la variacion entre dos semanas
    se calcula SOLO con los items presentes en ambas, y el nivel se encadena. Elimina los
    saltos espurios por altas/bajas de productos (el problema de los graficos).
 3. IMPUTACION POR ARRASTRE: si un item falta una semana, se arrastra su ultimo precio
    nacional conocido (hasta MAX_SEMANAS_ARRASTRE). Si falta mas, se marca para reemplazo.
 4. AGREGADO NACIONAL PONDERADO POR POBLACION provincial (no la mediana simple, que estaba
    dominada por DIA con el 42% de las sucursales).
 5. FILTRO DE OUTLIERS INTRA-TIPO en frescos: dentro de cada sucursal-semana se descartan
    las variantes fuera de [mediana/K, mediana*K]. Protege de gramajes mal cargados.
 6. INDICE RELATIVO CONTROLANDO POR CADENA para provincia/region: compara el precio de cada
    cadena en la provincia contra el precio nacional de esa misma cadena, y despues promedia.
    Asi "Patagonia es cara" no es un artefacto del mix de cadenas presentes.
 7. Composicion ampliada: 6 canastas, ~200 EANs empaquetados y 59 tipos frescos.
 8. Diagnostico de PRESENCIA por item x mes (altas/bajas) exportado al Excel.
 9. Bugs corregidos: normalizacion de provincia insensible a mayusculas/acentos (San juan ->
    San Juan, que caia en "Otras"); conteo de sucursales por la terna (comercio,bandera,sucursal).
"""
import json, os, hashlib

def _cell_id(prefix, src):
    return prefix + hashlib.md5(src.encode('utf-8')).hexdigest()[:6]

def cell_md(src):
    lines = src.split('\n')
    source = [l + '\n' for l in lines[:-1]] + ([lines[-1]] if lines[-1] else [])
    return {'cell_type':'markdown','id':_cell_id('md', src),'metadata':{},'source':source}

def cell_code(src):
    return {'cell_type':'code','execution_count':None,'id':_cell_id('c', src),'metadata':{},'outputs':[],'source':[src]}

cells = []

cells.append(cell_md("""# SEPA — Canastas Alternativas (informe semanal)

Costo **semanal** de 6 canastas, comparado con el **IPC** del INDEC, desagregado por **rubro**,
**provincia**, **región** y **cadena**.

**Semana**: ventana de 7 días que **cierra el jueves** (viernes→jueves). Se etiqueta por la
fecha de cierre, así el informe del viernes usa la última semana completa.

**Composición (híbrida):**
- **Empaquetados** → hoja `Productos unicos` del Excel (`cantidad_01`..`cantidad_06`).
- **Frescos** → por **tipo/nombre** (el EAN de balanza cambia por cadena). El precio del tipo
  en una sucursal-semana = mediana de sus variantes, normalizada a $/kg o $/docena.

**Índice**: encadenado de muestra apareada, para que altas/bajas de productos no generen
saltos. **Nacional**: ponderado por población provincial."""))

# ── CELL 1 — CONFIG ────────────────────────────────────────────────────────────
cells.append(cell_code(r'''# ============================================================
# CELDA 1 — CONFIGURACIÓN (modificar solo esta sección)
# ============================================================
SEPA_SOURCE = 'mi_drive'   # 'mi_drive' | 'local'
SEPA_DIR    = '/content/drive/MyDrive/carga'
OUTPUT_DIR  = '/content/drive/MyDrive/carga/output_canasta'   # donde está canasta_representativa_*.xlsx (ENTRADA)
RESULTS_DIR = '/content/drive/MyDrive/carga/output_canasta_alternativa'   # SALIDA
USE_CACHE   = True

HOJA_CANASTAS = 'Productos unicos'
CANASTA_COLS  = {'cantidad_01': 'Popular', 'cantidad_02': 'Media',
                 'cantidad_03': 'Ejecutiva', 'cantidad_04': 'Tecnológica',
                 'cantidad_05': 'Representativa', 'cantidad_06': 'Femenina'}
# Canastas que NO llevan frescos: bundles tematicos armados solo con EANs empaquetados.
CANASTAS_SIN_FRESCOS = {'Tecnológica', 'Femenina'}
# Canastas cuyo desglose por RUBRO usa la 'categoria' del maestro (mas fina) en vez del 'rubro'.
RUBRO_DESDE_CATEGORIA = {'Femenina', 'Tecnológica'}

# ── Serie y ventana ───────────────────────────────────────────────────────────
MES_INICIO_HISTORICO = '2024-01'
# La SEMANA cierra el JUEVES: ventana viernes->jueves, etiquetada por la fecha de cierre
# (ej. '2026-09-03'). Cambiar a 4 para cerrar viernes (0=lunes ... 3=jueves, 4=viernes).
DIA_CIERRE_SEMANA = 3
# Una sucursal cuenta para una canasta si tiene al menos esta fraccion de sus EMPAQUETADOS.
FRAC_PRODUCTOS_MIN = 0.8
# Minimo de sucursales para reportar una desagregacion (provincia/cadena/region) como confiable.
MIN_SUC_AGG = 30
# Estaciones de servicio / comercios no minoristas a excluir.
CADENAS_FILTRAR = {'19', '2013', '3001', '4'}

# ── Metodologia del indice ────────────────────────────────────────────────────
# Semanas que se arrastra el ultimo precio nacional conocido de un item ausente.
# Si un item falta MAS que esto, se lo reporta como "candidato a reemplazo".
MAX_SEMANAS_ARRASTRE = 8
# Filtro de outliers intra-tipo (frescos): dentro de cada sucursal-semana se descartan las
# variantes fuera de [mediana/K, mediana*K]. Protege de gramajes mal cargados / precios por unidad.
FRESCO_OUTLIER_K = 2.5
# Agregado nacional: 'poblacion' (ponderado por poblacion provincial) | 'mediana' (mediana simple)
AGG_NACIONAL = 'poblacion'

# Provincia -> REGION (5 regiones estandar).
REGION_PROV = {
    'Buenos Aires':'Centro/Pampeana','CABA':'Centro/Pampeana','Córdoba':'Centro/Pampeana',
    'Santa Fe':'Centro/Pampeana','Entre Ríos':'Centro/Pampeana','La Pampa':'Centro/Pampeana',
    'Jujuy':'NOA','Salta':'NOA','Tucumán':'NOA','Catamarca':'NOA','La Rioja':'NOA','Santiago del Estero':'NOA',
    'Chaco':'NEA','Corrientes':'NEA','Formosa':'NEA','Misiones':'NEA',
    'Mendoza':'Cuyo','San Juan':'Cuyo','San Luis':'Cuyo',
    'Neuquén':'Patagonia','Río Negro':'Patagonia','Chubut':'Patagonia',
    'Santa Cruz':'Patagonia','Tierra del Fuego':'Patagonia',
}

# ── FRESCOS por TIPO (el EAN de balanza cambia por cadena) ────────────────────
# qty = (Popular, Media, Ejecutiva, Representativa) en kg o docenas/mes.
# 'gmin' = gramaje minimo del envase para aceptar el EAN (default 250 g); evita que bandejas
# chicas o condimentos inflen el $/kg. La seleccion ademas exige categoria de fresco real.
TIPOS_FRESCOS = {
    # ---- FRUTAS ($/kg) ----
    'Banana':      {'rubro':'Frutas','unidad':'kg','qty':(3,3,3,3), 'inc':r'\bbanana', 'exc':r'licuad|yogur|snack|deshidr|chip|pasas|jugo|budin|helad|leche|postre'},
    'Manzana':     {'rubro':'Frutas','unidad':'kg','qty':(2,2,3,3), 'inc':r'\bmanzana', 'exc':r'jugo|pur[eé]|vinagre|snack|licor|yogur|rall|deshidr|chip|desodor|t[eé] |gaseosa|sidra|gatorade|levite|aromat|torta|budin'},
    'Naranja':     {'rubro':'Frutas','unidad':'kg','qty':(3,3,3,3), 'inc':r'\bnaranja', 'exc':r'jugo|gaseosa|aceite|esen|yogur|fanta|desodor|aromatiz|jab[oó]n|amarg|licor|tang|clight|pan de|\bpan\b|budin|torta|mermelada|dulce'},
    'Mandarina':   {'rubro':'Frutas','unidad':'kg','qty':(1,2,2,1), 'inc':r'\bmandarina', 'exc':r'jugo|esen|gaseosa|licor'},
    'Limón':       {'rubro':'Frutas','unidad':'kg','qty':(0.5,0.5,1,0.5), 'inc':r'\blim[oó]n|\blimones', 'exc':r'jugo|deterg|lavand|lavavaj|gaseosa|jab[oó]n|aceite|yogur|soda|amarg|aromatiz|desodor|hipoclor|limpiad|esen|tang|clight|t[eé]\b|pastilla|carame|crema|cera|pisos|helad|torta|budin|licor|vodka|\bpez\b|piedra|arena|gato|wondercat|pastel'},
    'Pera':        {'rubro':'Frutas','unidad':'kg','qty':(1,1,2,1), 'inc':r'\bpera\b|\bperas\b', 'exc':r'jugo|campera|frapera|heladera|esen|almibar|lata|mitades|light'},
    'Frutilla':    {'rubro':'Frutas','unidad':'kg','qty':(0,0.5,1,0.3), 'inc':r'\bfrutilla', 'exc':r'yogur|mermelada|dulce|helad|licor|gelatina|jugo|leche|postre|bomb|alfajor|chicle|carame|flan|congel|pulpa'},
    'Uva':         {'rubro':'Frutas','unidad':'kg','qty':(0,1,1,0.5), 'inc':r'\buva\b|\buvas\b', 'exc':r'jugo|vino|pasa|vinagre|mermelada|licor|aceite|semilla|sidra|espum'},
    'Durazno':     {'rubro':'Frutas','unidad':'kg','qty':(0,1,1,0.5), 'inc':r'\bdurazno', 'exc':r'lata|\blat\b|almibar|mermelada|jugo|conserva|yogur|dulce|licor|gaseosa|vodka|seco|desecad|mitades|light|calor|pulpa|helad'},
    'Ciruela':     {'rubro':'Frutas','unidad':'kg','qty':(0,0.5,1,0.3), 'inc':r'\bciruela', 'exc':r'seca|desecad|descaroz|sin carozo|pasa|mermelada|jugo|dulce|licor|nature food|tiernizad'},
    'Kiwi':        {'rubro':'Frutas','unidad':'kg','qty':(0,0.5,1,0.3), 'inc':r'\bkiwi', 'exc':r'jugo|yogur|licuad|helad|gelatina|pulpa'},
    'Palta':       {'rubro':'Frutas','unidad':'kg','qty':(0,0.5,1,0.3), 'inc':r'\bpalta', 'exc':r'aceite|guacamole|crema|jab[oó]n|shampoo|acondic|pulpa|congel|mascar'},
    'Pomelo':      {'rubro':'Frutas','unidad':'kg','qty':(0,0.5,0.5,0.3), 'inc':r'\bpomelo', 'exc':r'jugo|gaseosa|agua|amarg|licor|esen|clight|tang|difusor|repuesto|spirit|aromat|desodor'},
    'Ananá':       {'rubro':'Frutas','unidad':'kg','qty':(0,0.5,1,0.3), 'inc':r'\banan[aá]|\bpi[ñn]a\b', 'exc':r'jugo|lata|\blat\b|almibar|rodaja|yogur|helad|colada|licor|gaseosa|fizz|clight|tang|pulpa|mitades'},
    # ---- VERDURAS ($/kg) ----
    'Papa':        {'rubro':'Verduras','unidad':'kg','qty':(4,4,4,8), 'inc':r'\bpapa\b|\bpapas\b', 'exc':r'frita|snack|pur[eé]|congel|chip|bast[oó]n|noisett|prefrit|rall|española|jarro|espatul|mugg|taza|tortilla'},
    'Tomate':      {'rubro':'Verduras','unidad':'kg','qty':(2,2,3,3), 'inc':r'\btomate', 'exc':r'salsa|pur[eé]|\btrit|extracto|lata|\blat\b|pelado|jugo|ketchup|seco|deshidr|conserva|cubo|cherry|cereza|at[uú]n|sardina|caballa|sabores del|entero|perita lat|prepizza|pizza|tarta|sandwich'},
    'Cebolla':     {'rubro':'Verduras','unidad':'kg','qty':(2,2,2,3), 'inc':r'\bcebolla', 'exc':r'sopa|deshidr|crema|anillo|snack|verdeo|caldo|ciriola|cintita|queso|frita|\bpan\b|salsa|encurt|vinagre|pretzel|picada|rocky|galleta|snack'},
    'Zanahoria':   {'rubro':'Verduras','unidad':'kg','qty':(1.5,1.5,1.5,2), 'inc':r'\bzanahoria', 'exc':r'rall|congel|sopa|deshidr|bab[yi]|jugo|torta|budin|beb[eé]'},
    'Zapallo':     {'rubro':'Verduras','unidad':'kg','qty':(1.5,1.5,2,2), 'inc':r'\bzapallo\b|\bcalabaza', 'exc':r'congel|sopa|semilla|deshidr|crema|zapallito|dulce|cayote|pur[eé]|precocid'},
    'Lechuga':     {'rubro':'Verduras','unidad':'kg','qty':(1,1,1.5,1), 'inc':r'\blechuga', 'exc':r'aderez|snack|\bmix\b|ensalada'},
    'Morrón':      {'rubro':'Verduras','unidad':'kg','qty':(0.5,0.5,1,0.5), 'inc':r'\bmorr[oó]n|\bmorrones|\bpimiento', 'exc':r'molid|deshidr|conserva|lata|\blat\b|seco|piment[oó]n|aji molido|frasco|relleno|jalape|salsa|encurt'},
    'Batata':      {'rubro':'Verduras','unidad':'kg','qty':(1,1,1,1), 'inc':r'\bbatata', 'exc':r'dulce|congel|snack|chip|pur[eé]|frita'},
    'Acelga':      {'rubro':'Verduras','unidad':'kg','qty':(0,1,1,0.5), 'inc':r'\bacelga', 'exc':r'congel|\bcong\b|tarta|empanada|ravio|canel|ñoqui|noqui|milanesa|ensalada'},
    'Espinaca':    {'rubro':'Verduras','unidad':'kg','qty':(0,0.5,1,0.5), 'inc':r'\bespinaca', 'exc':r'congel|\bcong\b|tarta|empanada|nuez|ravio|canel|fideo|ñoqui|noqui|muslito|\bmix\b|mixta|milanesa|soja|vegan|queso|sorrent|pasta|medall|pollo|bandeja mixta'},
    'Choclo':      {'rubro':'Verduras','unidad':'kg','qty':(0.5,0.5,1,0.5), 'inc':r'\bchoclo', 'exc':r'lata|\blat\b|crema|cremos|congel|conserva|granos|desgran|arcor|campagnola|humita|pochoclo|snack|grm|entero'},
    'Brócoli':     {'rubro':'Verduras','unidad':'kg','qty':(0,0.5,1,0.3), 'inc':r'\bbrocoli|\bbrócoli', 'exc':r'congel|tarta|medall|rebozad|merluza|milanesa|pasta'},
    'Ajo':         {'rubro':'Verduras','unidad':'kg','qty':(0.2,0.2,0.3,0.2), 'inc':r'\bajo\b|\bajos\b', 'exc':r'aceite|\bsal\b|deshidr|polvo|molid|sazonad|condiment|\bpan\b|aderez|mayonesa|crema|conserva|\baji|salsa|manteca|queso|pasta|encurt'},
    'Zapallito':   {'rubro':'Verduras','unidad':'kg','qty':(0.5,0.5,1,0.5), 'inc':r'\bzapallito|\bzucchini|\bzuc+hini', 'exc':r'congel|relleno|tarta|milanesa'},
    'Berenjena':   {'rubro':'Verduras','unidad':'kg','qty':(0,0.5,1,0.3), 'inc':r'\bberenjena', 'exc':r'escabeche|conserva|frasco|lata|milanesa|congel|encurt'},
    'Repollo':     {'rubro':'Verduras','unidad':'kg','qty':(0.5,0.5,0.5,0.5), 'inc':r'\brepollo', 'exc':r'congel|chucrut|conserva|bruselas|encurt'},
    'Chaucha':     {'rubro':'Verduras','unidad':'kg','qty':(0,0.5,0.5,0.3), 'inc':r'\bchaucha', 'exc':r'congel|lata|\blat\b|conserva'},
    'Remolacha':   {'rubro':'Verduras','unidad':'kg','qty':(0,0.5,0.5,0.3), 'inc':r'\bremolacha', 'exc':r'lata|\blat\b|conserva|jugo|congel|ensalada|precocid|cortada'},
    'Pepino':      {'rubro':'Verduras','unidad':'kg','qty':(0,0.5,0.5,0.3), 'inc':r'\bpepino', 'exc':r'encurt|pickle|conserva|frasco|vinagre|jab[oó]n|crema|mascar|gel'},
    # ---- CARNE VACUNA ($/kg) ----
    'Asado':       {'rubro':'Carne','unidad':'kg','qty':(2,2,3,3), 'inc':r'\basado\b|\bcostillar|tira de asado', 'exc':r'salsa|adob|aderez|sabor asado|hellmann|snack|man[ií]|pollo|caf[eé]|cuchill|\bset\b|carbon|carb[oó]n|palit|asador|pizza|cerdo|chancho|cordero|congel'},
    'Carne picada':{'rubro':'Carne','unidad':'kg','qty':(2,2,2,3), 'inc':r'\bpicada\b|carne molida', 'exc':r'salch|congel|caldo|pat[eé]|hamburg|pollo|pescado|aceituna|verdura|angus|wagyu|kobe|premium|cerdo|mixta|frutos|mani|man[ií]'},
    'Nalga/Cuadril':{'rubro':'Carne','unidad':'kg','qty':(1,1.5,2,2), 'inc':r'\bnalga|\bcuadril|bola de lomo|\bcuadrada\b|\bpeceto|colita de cuadril', 'exc':r'mantel|cuadrill|cerdo|pollo|milanesa|congel|cordero'},
    'Milanesa carne':{'rubro':'Carne','unidad':'kg','qty':(1,1,1.5,1), 'inc':r'milanesa', 'exc':r'soja|pollo|congel|merluza|pescado|napolitan|vegetal|cerdo|berenjena|rebozad|granja|swift|paty|listas|carr[eé]|calabaza|zapallo|espinaca|acelga|arroz|quinoa|lenteja|garbanzo'},
    'Matambre':    {'rubro':'Carne','unidad':'kg','qty':(0,0.5,1,0.5), 'inc':r'\bmatambre', 'exc':r'arrollado|relleno|queso|pizza|a la|cocido|cerdo|congel'},
    'Vacío':       {'rubro':'Carne','unidad':'kg','qty':(0,0.5,1,0.5), 'inc':r'\bvac[ií]o\b', 'exc':r'al vac[ií]o|\(vac|envasad|arrollado|relleno|envase|frasco|cerdo|pollo|medialuna|queso|jam[oó]n|fiambre|salame|bondiola|congel|cordero|pescado|merluza|salm[oó]n|chistorra|chorizo|morcilla|salchich|guanaco'},
    'Osobuco':     {'rubro':'Carne','unidad':'kg','qty':(0.5,0.5,0.5,0.5), 'inc':r'\bosobuco|\bosso\s*buco', 'exc':r'congel'},
    'Roast beef':  {'rubro':'Carne','unidad':'kg','qty':(0,0.5,1,0.5), 'inc':r'roast\s*beef|tapa de nalga|tapa de cuadril', 'exc':r'congel|fiambre|feteado'},
    'Bife de chorizo':{'rubro':'Carne','unidad':'kg','qty':(0,0.5,1,0.5), 'inc':r'bife de chorizo|bife ancho|bife angosto|\bbife\b', 'exc':r'chorizo parril|cerdo|pollo|milanesa|snack|palit|t-bone|tbone|ojo de bife|tomahawk|congel|cordero|wagyu|kobe|angus'},
    'Lomo':        {'rubro':'Carne','unidad':'kg','qty':(0,0,1,0.3), 'inc':r'\blomo\b', 'exc':r'bola de lomo|cerdo|atun|at[uú]n|pollo|lomito|jam[oó]n|ahumad|pizza|s[aá]ndwich|sandwich|congel|cabecero|medall|wagyu|kobe|angus|praga|feteado|cinta|costilla|guanaco'},
    'Paleta':      {'rubro':'Carne','unidad':'kg','qty':(1,0.5,0,1), 'inc':r'\bpaleta\b', 'exc':r'cerdo|cocida|jam[oó]n|fiambre|helad|paletita|pintur|rodillo|ping|pong|tenis|playa|espatula|cordero|congel|guanaco'},
    'Falda/Puchero':{'rubro':'Carne','unidad':'kg','qty':(1,0.5,0,1), 'inc':r'\bfalda\b|\bpuchero|\bcaracu|\bazotillo', 'exc':r'cerdo|pollo|congel|mixto|cordero'},
    # ---- POLLO ($/kg) ----
    'Pollo':       {'rubro':'Pollo','unidad':'kg','qty':(3,3,3,4), 'inc':r'\bpollo\b|pata muslo', 'exc':r'caldo|sopa|saboriz|congel|nugget|pat[eé]|medall|hamburg|milanesa|pella|arroz|fideo|snack|cubito|aliment|merluza|pescado|pechuga|suprema|\bfilet|fajita|deshuesad|campero|colonial|org[aá]nic|kosher|criado|sandwich|s[aá]ndwich|empanada|tarta|salch|picada|croqueta|bocadit|rebozad|\bmax\b|triangulo|relleno|arrollado|taco|wrap|ensalada|pizza|salsa|al vac[ií]o|ahumad|grill|listo|rostiz|precoc|\bmed\b|\bjam|patita|\bseco\b|cuarto|cocido|hervid'},
    'Suprema/Pechuga':{'rubro':'Pollo','unidad':'kg','qty':(0,1,2,1), 'inc':r'\bpechuga|\bsuprema', 'exc':r'congel|milanesa|rebozad|nugget|medall|hamburg|sandwich|s[aá]ndwich|pavo|cerdo|salsa|empanad|grill|listas|granja del sol|swift|paty|\bmax\b|merluza|pescado|verdeo|ahumad|fiambre|feteado|al vac[ií]o'},
    # ---- CERDO ($/kg) ----
    'Bondiola':    {'rubro':'Cerdo','unidad':'kg','qty':(0,0.5,1,0.5), 'inc':r'\bbondiola', 'exc':r'ahumad|curad|fiambre|feteado|sandwich|s[aá]ndwich|costeletero|sin bondiola|congel'},
    'Pechito/Costilla cerdo':{'rubro':'Cerdo','unidad':'kg','qty':(0.5,0.5,1,0.5), 'inc':r'pechito|costilla.*cerdo|cerdo.*costilla|costeleta.*cerdo|cerdo.*costeleta|\bribs\b', 'exc':r'ahumad|congel|cong\b|salsa|bbq|sandwich|kosher|aus\b'},
    'Carré de cerdo':{'rubro':'Cerdo','unidad':'kg','qty':(0,0.5,0.5,0.3), 'inc':r'carr[eé].*cerdo|cerdo.*carr[eé]|\bcarr[eé]\b', 'exc':r'ahumad|fiambre|feteado|curad|jam[oó]n|congel|cong\b|aus\b|milanesa'},
    # ---- PESCADO ($/kg) ----
    'Merluza':     {'rubro':'Pescado','unidad':'kg','qty':(0.5,0.5,1,0.5), 'inc':r'\bmerluza', 'exc':r'bast[oó]n|reboz|medall|milanesa|congel|aceite|lata|conserva|croqueta|nugget|granja del sol|swift|hamburg|empanad|romana|formita|queso|negra|relleno|ahumad|pat[eé]'},
    # ---- FIAMBRES Y QUESOS por kg (balanza) ----
    'Queso cremoso':{'rubro':'Fiambres y Quesos','unidad':'kg','qty':(0.5,1,1,1), 'gmin':500, 'inc':r'queso.*cremoso|cremoso.*queso|\bcremon\b', 'exc':r'untable|rallad|feta|light|sandwich|s[aá]ndwich|pizza|congel|barra|vegan|descremad'},
    'Queso barra/Dambo':{'rubro':'Fiambres y Quesos','unidad':'kg','qty':(0.5,0.5,1,0.5), 'gmin':500, 'inc':r'queso.*(barra|dambo|tybo|pategr[aá]s|holanda|fymbo)|\bdambo\b|\btybo\b', 'exc':r'untable|rallad|feta|sandwich|s[aá]ndwich|pizza|congel|light|vegan'},
    'Queso rallar (sardo/reggianito)':{'rubro':'Fiambres y Quesos','unidad':'kg','qty':(0,0.3,0.5,0.3), 'gmin':500, 'inc':r'queso.*(sardo|reggian|parmes|romano)|\bsardo\b|\breggianito', 'exc':r'rallado|feta|untable|sandwich|pizza|congel|provolet|provol|vegan'},
    'Jamón cocido (kg)':{'rubro':'Fiambres y Quesos','unidad':'kg','qty':(0.5,0.5,1,0.5), 'gmin':500, 'inc':r'jam[oó]n cocido|jamon cocido', 'exc':r'feteado|fetas|sandwich|s[aá]ndwich|pizza|empanad|tarta|light|caja|blister|pavita|pavo'},
    'Salame/Salamín':{'rubro':'Fiambres y Quesos','unidad':'kg','qty':(0,0.3,0.5,0.3), 'gmin':500, 'inc':r'\bsalame|\bsalamin|\bsalam[ií]n', 'exc':r'feteado|fetas|sandwich|pizza|snack|palito|cabana|picada|tabla'},
    'Mortadela':   {'rubro':'Fiambres y Quesos','unidad':'kg','qty':(0.5,0.3,0,0.3), 'gmin':500, 'inc':r'\bmortadela', 'exc':r'feteado|fetas|sandwich|pizza|piccola|familiar'},
    # ---- PANADERIA ($/kg) ----
    'Pan francés':{'rubro':'Panadería','unidad':'kg','qty':(6,6,5,8), 'inc':r'pan franc[eé]s|\bflauta|\bmignon|\bfelipe|pan.*(criollo|casero)|\bpan\b.*(tira|\bkg)', 'exc':r'lactal|mesa|dulce|integral|salvado|hamburg|pancho|pebete|hot dog|rallado|congel|tostad|arabe|pita|molde|viena|chip|budin|prepizza|pizza|galleta|semilla|centeno|negro|queso|chocolate|rosca|figaza|panettone|fideo|don felipe|naranja|an[ií]s|cuernito|manteca|grasa'},
    # ---- HUEVOS ($/docena) ----
    'Huevos':      {'rubro':'Huevos','unidad':'doc','qty':(2,2,2,3), 'inc':r'\bhuevo', 'exc':r'chocolate|kinder|pascua|sorpresa|codorniz|conejo|batidora|fideo|pasta|ravio|tallar|mayonesa|pintur|colorante|separador|huevera|salsa|tarta|galletit|ensalada|revuelt|omelet|budin|torta|liquido|l[ií]quido|polvo|clara|rainb|albu|\d+\s*cm|globo|pi[ñn]ata|decor|juguete|plastic'},
}

# rubro del tipo -> categorias del maestro que valen como fresco real ('' = SEPA-only sin categoria)
_CAT_FRESCO_CFG = {
    'Frutas': {'Frutas y Verduras'}, 'Verduras': {'Frutas y Verduras'},
    'Carne': {'Carnicería','Carniceria'}, 'Pollo': {'Carnicería','Carniceria'}, 'Cerdo': {'Carnicería','Carniceria'},
    'Pescado': {'Pescados y Mariscos','Carnicería','Carniceria'},
    'Fiambres y Quesos': {'Fiambrería','Fiambreria'}, 'Panadería': {'Panificados'},
    'Huevos': {'Huevos'},
}

# Colores/estilos por canasta
CANASTA_COLORS = {'Popular':'#e74c3c','Media':'#27ae60','Ejecutiva':'#8e44ad','Tecnológica':'#2980b9','Representativa':'#e67e22','Femenina':'#e84393'}
CANASTA_MARKERS = {'Popular':'s','Media':'^','Ejecutiva':'D','Tecnológica':'o','Representativa':'*','Femenina':'v'}
''' ))

# ── CELL 2 — DRIVE + DEPS + IMPORTS + HELPERS ──────────────────────────────────
cells.append(cell_code(r'''# ============================================================
# CELDA 2 — Montar Drive + dependencias + imports + helpers
# ============================================================
try:
    import google.colab
    if SEPA_SOURCE == 'mi_drive':
        from google.colab import drive
        drive.mount('/content/drive')
        print('Google Drive montado en /content/drive')
except ImportError:
    print('Entorno local detectado')

import subprocess, sys
subprocess.run([sys.executable, '-m', 'pip', 'install', 'openpyxl', 'tqdm', 'pyarrow', '-q'], check=False)

import zipfile, gzip, io, os, re, shutil, warnings, hashlib, gc, unicodedata
import datetime as _dt
from pathlib import Path
from tqdm.auto import tqdm
warnings.filterwarnings('ignore')
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
plt.rcParams['figure.figsize'] = (13, 6); plt.rcParams['font.size'] = 11

SEPA_DIR    = Path(SEPA_DIR)
OUTPUT_DIR  = Path(OUTPUT_DIR)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR = Path(RESULTS_DIR)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR   = RESULTS_DIR / '_cache_nb07'
CACHE_DIR.mkdir(parents=True, exist_ok=True)
print(f'Entrada (canasta): {OUTPUT_DIR}\nSalida (resultados): {RESULTS_DIR}')
TMP_DIR    = Path('/content/tmp_sepa07'); TMP_DIR.mkdir(exist_ok=True)

def normalizar_ean(s):
    if s is None: return ''
    d = re.sub(r'\D', '', str(s))
    return (d.lstrip('0') or '0') if d else ''

def _sa(s):
    # sin acentos + minusculas + espacios colapsados (para matchear nombres de provincia)
    s = ''.join(c for c in unicodedata.normalize('NFD', str(s)) if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', s).strip().lower()

def _pmean(_s):
    # Promedio robusto: descarta outliers fuera de [mediana/4, mediana*4] y promedia.
    _s = pd.to_numeric(_s, errors='coerce').dropna()
    if len(_s) == 0: return float('nan')
    _m = _s.median()
    if _m and _m > 0:
        _f = _s[(_s >= _m/4) & (_s <= _m*4)]
        if len(_f) > 0: _s = _f
    return _s.mean()

def _to_gramos(_q, _u):
    _q = pd.to_numeric(str(_q).replace(',', '.'), errors='coerce'); _u = str(_u).strip().lower()
    if pd.isna(_q) or _q <= 0: return np.nan
    if _u in ('kg','kgm','kgr','l','lt','litro','litros','kilogramo','kilogramos'): return _q * 1000
    if _u in ('gr','g','grs','grm','gramo','gramos','ml','cc','mililitro'): return _q
    return np.nan
_RE_GR = re.compile(r'(\d+(?:[.,]\d+)?)\s*(kg|kgm|kilo|grs?|gramos?|ml|cc|lts?|litros?|g)\b')
def _gramos_desc(_s):
    _m = _RE_GR.search(str(_s).lower())
    if not _m: return np.nan
    _v = float(_m.group(1).replace(',', '.')); _u = _m.group(2)
    if _u.startswith('k') or _u in ('lt','l','lts','litro','litros'): return _v * 1000
    return _v
_RE_UN = re.compile(r'(?:x\s*)?(\d+)\s*(?:un|u|unid|unidad|unidades|maple|cu|ea)\b')
def _unidades_desc(_s):
    _m = _RE_UN.search(str(_s).lower())
    if _m:
        _n = int(_m.group(1))
        if 1 <= _n <= 60: return _n
    return np.nan

# ── SEMANA que cierra el jueves (ventana viernes->jueves) ─────────────────────
def _semana_cierre(_f):
    # Devuelve la fecha de cierre (jueves) de la ventana que contiene _f, como 'YYYY-MM-DD'.
    _d = _f.date() if hasattr(_f, 'date') else _f
    _ahead = (DIA_CIERRE_SEMANA - _d.weekday()) % 7
    return (_d + _dt.timedelta(days=int(_ahead))).strftime('%Y-%m-%d')

def _mes_de_semana(_sem):
    # Mes "dueno" de la semana = mes del punto medio de la ventana (cierre - 3 dias).
    _d = _dt.date.fromisoformat(_sem) - _dt.timedelta(days=3)
    return _d.strftime('%Y-%m')

def _sem_anterior(_sem):
    return (_dt.date.fromisoformat(_sem) - _dt.timedelta(days=7)).strftime('%Y-%m-%d')

print('Imports OK | semana cierra:', ['lunes','martes','miércoles','jueves','viernes','sábado','domingo'][DIA_CIERRE_SEMANA])
''' ))

# ── CELL 3 — CANASTAS EMPAQUETADAS DESDE EXCEL ─────────────────────────────────
cells.append(cell_code(r'''# ============================================================
# CELDA 3 — Canastas EMPAQUETADAS desde "Productos unicos" (cantidad_01..06)
# ============================================================
import glob as _glob
_patrones = sorted(_glob.glob(str(OUTPUT_DIR / 'canasta_representativa_*.xlsx')), reverse=True)
if not _patrones:
    raise FileNotFoundError(
        f'No se encontró canasta_representativa_*.xlsx en {OUTPUT_DIR}. '
        'Subí a Drive el Excel con la hoja "Productos unicos" poblada (cantidad_01..06).')
CANASTA_EXCEL = Path(_patrones[0])
print(f'Excel de canasta: {CANASTA_EXCEL.name}  (hoja: {HOJA_CANASTAS})')

_sel = pd.read_excel(CANASTA_EXCEL, sheet_name=HOJA_CANASTAS, dtype={'id_producto': str})
_sel['ean_norm'] = _sel['id_producto'].map(normalizar_ean)
_desc_col  = next((c for c in ['descripcion','descripcion_producto','nombre'] if c in _sel.columns), _sel.columns[0])
_rubro_col = next((c for c in ['rubro','categoria'] if c in _sel.columns), None)
_cat_col   = next((c for c in ['categoria','subcategoria'] if c in _sel.columns), _rubro_col)

# CANASTAS_EMP[nombre] = { ean_norm: (desc, qty, rubro, categoria) }
CANASTAS_EMP = {}
for _col, _name in CANASTA_COLS.items():
    if _col not in _sel.columns:
        print(f'AVISO: columna {_col} ausente en la hoja — canasta {_name} vacía.')
        continue
    _q = pd.to_numeric(_sel[_col], errors='coerce').fillna(0)
    _act = _sel[_q > 0].copy(); _act['_q'] = _q[_q > 0].values
    CANASTAS_EMP[_name] = {
        r['ean_norm']: (str(r[_desc_col])[:60], float(r['_q']),
                        str(r[_rubro_col]).title() if _rubro_col else 'Otros',
                        str(r[_cat_col]) if _cat_col else '')
        for _, r in _act.iterrows() if r['ean_norm']}

CANASTAS_ACTIVAS = [n for n in CANASTA_COLS.values() if CANASTAS_EMP.get(n)]
if not CANASTAS_ACTIVAS:
    raise ValueError('Ninguna columna cantidad_01..06 tiene productos > 0 en la hoja.')

EANS_EMP = set().union(*[set(c.keys()) for c in CANASTAS_EMP.values()])
print(f'\nCanastas activas: {CANASTAS_ACTIVAS}')
for _name in CANASTAS_ACTIVAS:
    _c = CANASTAS_EMP[_name]
    _u = sum(v[1] for v in _c.values())
    _rub = pd.Series([v[2] for v in _c.values()]).value_counts().to_dict()
    print(f'  [{_name}] {len(_c)} productos empaquetados, {_u:.0f} unidades/mes | rubros: {_rub}')
print(f'EANs empaquetados (unión): {len(EANS_EMP)}')
''' ))

# ── CELL 4 — MAESTROS ──────────────────────────────────────────────────────────
cells.append(cell_code(r'''# ============================================================
# CELDA 4 — Maestros de sucursales, cadenas, provincias y productos
# ============================================================
DATA_URL = 'https://raw.githubusercontent.com/santiagoriverti/precios_minoristas_supermercados/main/data'
def leer_maestro(nombre, **kwargs):
    local = Path('data') / nombre
    if local.exists():
        return pd.read_excel(local, **kwargs)
    import urllib.request, urllib.parse
    dl = Path('/content/data') / nombre
    Path('/content/data').mkdir(exist_ok=True)
    if not dl.exists():
        print(f'  Descargando {nombre}...')
        urllib.request.urlretrieve(f'{DATA_URL}/{urllib.parse.quote(nombre)}', dl)
    return pd.read_excel(dl, **kwargs)

print('Cargando maestros...')
maestro_suc = leer_maestro('maestro_sucursales_completo.xlsx')
for c in ['id_comercio','id_bandera','id_sucursal']:
    maestro_suc[c] = maestro_suc[c].astype(str)
suc_pais = maestro_suc[
    maestro_suc['sucursales_latitud'].notna() & maestro_suc['sucursales_longitud'].notna() &
    (maestro_suc['sucursales_latitud'].between(-55, -22)) &
    (maestro_suc['sucursales_longitud'].between(-73, -53))].copy()
IDS_PAIS = set(zip(suc_pais['id_comercio'], suc_pais['id_bandera'], suc_pais['id_sucursal']))
print(f'  Sucursales validas: {len(suc_pais):,}')

NOMBRES_COMPUESTOS = {
    ('9','1'):'Vea',('9','2'):'Disco',('9','3'):'Jumbo',
    ('10','1'):'Carrefour',('10','2'):'Carrefour Market',('10','3'):'Carrefour Express',
    ('11','2'):'ChangoMas',('11','4'):'Hiper ChangoMas',('11','5'):'Mi ChangoMas',
    ('16','1'):'Hipermercado Libertad',('16','2'):'Mini Libertad'}
NOMBRES_SIMPLES = {
    '2':'La Anonima','3':'Cadena 3','5':'Hipermercado Misiones','8':'Mariano Max',
    '12':'Coto','13':'Cooperativa Obrera','15':'DIA','20':'LAR','21':'Toledo','23':'Cadena 23','47':'Pasamonte'}
def asignar_cadena(row):
    k = (row['id_comercio'], row['id_bandera'])
    if k in NOMBRES_COMPUESTOS: return NOMBRES_COMPUESTOS[k]
    if row['id_comercio'] in NOMBRES_SIMPLES: return NOMBRES_SIMPLES[row['id_comercio']]
    return f"Cadena {row['id_comercio']}"

PROV_NORM = {
    'Ciudad Autonoma de Buenos Aires':'CABA','Provincia de Buenos Aires':'Buenos Aires',
    'Provincia de Catamarca':'Catamarca','Provincia del Chaco':'Chaco','Provincia del Chubut':'Chubut',
    'Provincia de Cordoba':'Cordoba','Provincia de Corrientes':'Corrientes',
    'Provincia de Entre Rios':'Entre Rios','Provincia de Formosa':'Formosa','Provincia de Jujuy':'Jujuy',
    'Provincia de La Pampa':'La Pampa','Provincia de La Rioja':'La Rioja','Provincia de Mendoza':'Mendoza',
    'Provincia de Misiones':'Misiones','Provincia del Neuquen':'Neuquen','Provincia de Rio Negro':'Rio Negro',
    'Provincia de Salta':'Salta','Provincia de San Juan':'San Juan','Provincia de San Luis':'San Luis',
    'Provincia de Santa Cruz':'Santa Cruz','Provincia de Santa Fe':'Santa Fe',
    'Provincia de Santiago del Estero':'Santiago del Estero',
    'Provincia de Tierra del Fuego, Antartida e Islas del Atlantico Sur':'Tierra del Fuego',
    'Provincia de Tucuman':'Tucuman'}
PESOS_POBLACION = {
    'Buenos Aires':17709732,'CABA':3075646,'Catamarca':415438,'Chaco':1204541,'Chubut':618994,
    'Cordoba':3978984,'Corrientes':1120801,'Entre Rios':1385961,'Formosa':605193,'Jujuy':770881,
    'La Pampa':368550,'La Rioja':393531,'Mendoza':2014533,'Misiones':1261294,'Neuquen':664057,
    'Rio Negro':747610,'Salta':1441998,'San Juan':781217,'San Luis':531745,'Santa Cruz':333473,
    'Santa Fe':3556522,'Santiago del Estero':1019304,'Tierra del Fuego':190641,'Tucuman':1737127}
# Lookup insensible a mayusculas/acentos: antes 'San juan' no matcheaba y caia en region "Otras".
_PROV_CANON = {_sa(k): v for k, v in PROV_NORM.items()}
for _v in set(PROV_NORM.values()) | set(PESOS_POBLACION) | set(REGION_PROV):
    _PROV_CANON.setdefault(_sa(_v), _v)
def norm_prov(x):
    return _PROV_CANON.get(_sa(x), str(x).strip())
# REGION_PROV y PESOS_POBLACION reindexados con la misma normalizacion
REGION_PROV     = {norm_prov(k): v for k, v in REGION_PROV.items()}
PESOS_POBLACION = {norm_prov(k): v for k, v in PESOS_POBLACION.items()}

# Maestro de productos (interno + SEPA completo del Drive)
_mp_raw = leer_maestro('Maestro de Productos Interno.xlsx', dtype=str,
                       usecols=['producto_sepa_id','producto_descripcion','producto_marca','rubro','categoria',
                                'producto_cantidad_presentacion','producto_unidad_medida_presentac'])
_msepa = None
try:
    _msp = Path(SEPA_DIR) / 'maestro_sepa_completo.csv.gz'
    if _msp.exists():
        _msepa = pd.read_csv(_msp, dtype=str)
        print(f'  Maestro SEPA completo (Drive): {len(_msepa):,} EANs')
    else:
        print('  (aviso: maestro_sepa_completo.csv.gz no esta en el Drive - solo maestro interno.)')
except Exception as _e:
    print(f'  (aviso: no se pudo leer maestro_sepa_completo.csv.gz: {_e})')

def _prep_master(_df):
    _df = _df.rename(columns={'producto_descripcion':'descripcion','producto_marca':'marca'})
    if 'rubro' not in _df.columns: _df['rubro'] = ''
    if 'categoria' not in _df.columns: _df['categoria'] = ''
    _df['ean_norm'] = _df['producto_sepa_id'].map(normalizar_ean)
    return _df[['ean_norm','descripcion','marca','rubro','categoria',
                'producto_cantidad_presentacion','producto_unidad_medida_presentac']]
_base = _prep_master(_mp_raw)
if _msepa is not None:
    _extra = _prep_master(_msepa)
    _extra = _extra[~_extra['ean_norm'].isin(set(_base['ean_norm']))]
    MP_META = pd.concat([_base, _extra], ignore_index=True)
    print(f'  Fusion maestros: interno {len(_base):,} + {len(_extra):,} nuevos = {len(MP_META):,} EANs')
else:
    MP_META = _base
_g1 = [_to_gramos(a, b) for a, b in zip(MP_META['producto_cantidad_presentacion'],
                                        MP_META['producto_unidad_medida_presentac'])]
_g2 = [_gramos_desc(x) for x in MP_META['descripcion']]
MP_META['grams'] = [(_a if (_a == _a) else _b) for _a, _b in zip(_g1, _g2)]
MP_META['unidades'] = [_unidades_desc(x) for x in MP_META['descripcion']]
MP_META['categoria'] = MP_META['categoria'].fillna('').astype(str).str.strip()
MP_META = (MP_META.dropna(subset=['ean_norm']).drop_duplicates('ean_norm')
           .set_index('ean_norm')[['descripcion','marca','rubro','categoria','grams','unidades']])
print(f'  Maestro de productos (total): {len(MP_META):,} EANs con metadata')
print('Maestros OK')
''' ))

# ── CELL 5 — RESOLVER FRESCOS POR NOMBRE ───────────────────────────────────────
cells.append(cell_code(r'''# ============================================================
# CELDA 5 - Resolver EANs de FRESCOS por regla de nombre (el EAN cambia por cadena)
# ============================================================
# Candidatos = EANs cuya descripcion matchea inc y no exc, Y que pertenecen a la categoria
# de fresco real (Frutas y Verduras / Carniceria / Fiambreria / Panificados / Huevos /
# Pescados) o que no traen categoria (EANs de balanza SEPA-only). Se normaliza a la unidad
# del tipo: kg (usa grams, con piso 'gmin') o doc (usa unidades).
_desc_all = MP_META['descripcion'].fillna('').astype(str).str.lower()
_cat_all  = MP_META['categoria'].fillna('').astype(str)
_GRAMS_MIN_DEFAULT = 250

EAN_TIPO = {}       # ean_norm -> tipo fresco
FRESCO_INFO = {}    # tipo -> {rubro, unidad, qty}
EAN_NORMFACTOR = {} # ean_norm -> gramos (kg) o unidades (doc)
_cob_fresco = []
for _tipo, _cfg in TIPOS_FRESCOS.items():
    _inc, _exc = _cfg['inc'], _cfg.get('exc', '')
    _m = _desc_all.str.contains(_inc, regex=True)
    if _exc: _m &= ~_desc_all.str.contains(_exc, regex=True)
    _cats = _CAT_FRESCO_CFG.get(_cfg['rubro'])
    if _cats:
        _m &= (_cat_all.isin(_cats) | (_cat_all == ''))
    _cand = MP_META[_m].copy()
    if _cfg['unidad'] == 'kg':
        _gmin = _cfg.get('gmin', _GRAMS_MIN_DEFAULT)
        _cand = _cand[_cand['grams'].notna() & (_cand['grams'] >= _gmin)]
        _fac = _cand['grams']            # $/g -> *1000 = $/kg
    else:  # doc
        _u = _cand['unidades'].fillna(1).clip(lower=1)
        _cand = _cand[_u > 0]; _fac = _u  # $/un -> *12 = $/docena
    FRESCO_INFO[_tipo] = {'rubro':_cfg['rubro'],'unidad':_cfg['unidad'],'qty':_cfg['qty']}
    _n = 0
    for _e, _f in zip(_cand.index, _fac):
        if _e not in EAN_TIPO:  # primer tipo que lo reclama
            EAN_TIPO[_e] = _tipo; EAN_NORMFACTOR[_e] = float(_f); _n += 1
    _cob_fresco.append({'tipo':_tipo,'rubro':_cfg['rubro'],'unidad':_cfg['unidad'],
                        'n_EANs_maestro':int(_m.sum()),'n_EANs_usables':_n})
cobertura_fresco_maestro = pd.DataFrame(_cob_fresco)
EANS_FRESCOS = set(EAN_TIPO.keys())
EANS_LECTURA = EANS_EMP | EANS_FRESCOS

print(f'Tipos frescos: {len(FRESCO_INFO)} | EANs frescos candidatos: {len(EANS_FRESCOS):,}')
print(cobertura_fresco_maestro.to_string(index=False))
print(f'\nUniverso de EANs a leer del SEPA: {len(EANS_LECTURA):,} '
      f'(empaquetados {len(EANS_EMP)} + frescos {len(EANS_FRESCOS)})')
_sin_cand = list(cobertura_fresco_maestro.loc[cobertura_fresco_maestro['n_EANs_usables'] == 0, 'tipo'])
if _sin_cand:
    print(f'AVISO: tipos SIN candidatos en el maestro (revisar inc/exc/gmin): {_sin_cand}')
''' ))

# ── CELL 6 — ZIPS + MAPA DE MESES ──────────────────────────────────────────────
cells.append(cell_code(r'''# ============================================================
# CELDA 6 - Lectura de ZIPs SEPA + mapa de meses
# ============================================================
_PAT_SEM  = re.compile(r'^(\d{4})(A|B)$', re.IGNORECASE)
_PAT_ARC  = re.compile(r'^(\d{2})(\d{4})_pais_parte.*COMPLETO.*\.csv\.gz$', re.IGNORECASE)
PAT_FECHA = re.compile(r'^precio_(\d{8})$')

def detectar_semestres():
    out = []
    for z in sorted(SEPA_DIR.glob('*.zip')):
        m = _PAT_SEM.match(z.stem)
        if m: out.append((z, int(m.group(1)), m.group(2).upper()))
    return out
def archivos_por_mes(zip_path):
    meses = {}
    with zipfile.ZipFile(zip_path) as zf:
        for nombre in zf.namelist():
            m = _PAT_ARC.match(Path(nombre).name)
            if m:
                meses.setdefault((int(m.group(2)), int(m.group(1))), []).append(nombre)
    return meses

_mapa_mes = {}
for _zip_path, _anio, _sem in detectar_semestres():
    for (_a, _mm), _archs in archivos_por_mes(_zip_path).items():
        _lbl = f'{_a}-{_mm:02d}'
        if _lbl >= MES_INICIO_HISTORICO:
            _mapa_mes[_lbl] = (_zip_path, _archs)
_meses_disp = sorted(_mapa_mes)
if not _meses_disp:
    raise RuntimeError(f'No hay meses SEPA disponibles >= {MES_INICIO_HISTORICO}')
_mes_actual = _meses_disp[-1]

_NOM = {'01':'enero','02':'febrero','03':'marzo','04':'abril','05':'mayo','06':'junio',
        '07':'julio','08':'agosto','09':'septiembre','10':'octubre','11':'noviembre','12':'diciembre'}
NOMBRE_MES_TITLE = f"{_NOM[_mes_actual[5:7]]} {_mes_actual[:4]}".title()
print(f'Meses disponibles: {len(_meses_disp)}  ({_meses_disp[0]} -> {_meses_disp[-1]}) | mes en curso: {_mes_actual}')
''' ))

# ── CELL 7 — LECTURA SEMANAL + COLAPSO + FILTRO DE OUTLIERS ───────────────────
cells.append(cell_code(r'''# ============================================================
# CELDA 7 - Lectura SEMANAL (semana cierra jueves) + colapso de frescos a TIPO
# ============================================================
# Empaquetado: item = EAN. Fresco: item = TIPO (mediana de variantes, $/kg o $/docena),
# COLAPSADO EN LA LECTURA para no acumular un panel gigante (de ~10k EANs a ~59 tipos).
# Antes de la mediana se aplica un FILTRO DE OUTLIERS INTRA-TIPO: dentro de cada
# sucursal-semana se descartan las variantes fuera de [mediana/K, mediana*K]. Eso protege
# de EANs con gramaje mal cargado o precios por unidad en vez de por kilo.
_SKR = ['id_comercio','id_bandera','id_sucursal']
_cache_key  = hashlib.md5(('|'.join(sorted(EANS_LECTURA)) + f'|w{DIA_CIERRE_SEMANA}|k{FRESCO_OUTLIER_K}').encode()).hexdigest()[:8]
_cache_path = CACHE_DIR / f'sem_{_cache_key}_v5.parquet'   # v5 = semana jueves + outlier filter

def _leer_mes(_lbl):
    _zip_path, _archs = _mapa_mes[_lbl]
    _rows = []
    for _archivo in sorted(_archs):
        _tmp_p = TMP_DIR / Path(_archivo).name
        with zipfile.ZipFile(_zip_path) as _zf:
            with _zf.open(_archivo) as _s, open(_tmp_p, 'wb') as _d:
                shutil.copyfileobj(_s, _d, length=4*1024*1024)
        with gzip.open(_tmp_p, 'rt', encoding='utf-8', errors='replace') as _g:
            for _chunk in pd.read_csv(_g, dtype=str, chunksize=300_000, low_memory=False):
                _chunk['ean_norm'] = _chunk['id_producto'].apply(normalizar_ean)
                _chunk = _chunk[_chunk['ean_norm'].isin(EANS_LECTURA)].copy()
                if len(_chunk) == 0: continue
                for _c in _SKR:
                    _chunk[_c] = _chunk[_c].astype(str)
                _chunk['_k'] = list(zip(_chunk['id_comercio'],_chunk['id_bandera'],_chunk['id_sucursal']))
                _chunk = _chunk[_chunk['_k'].isin(IDS_PAIS)].drop(columns=['_k']).copy()
                if len(_chunk) == 0: continue
                _cols_p = [c for c in _chunk.columns if PAT_FECHA.match(c)]
                if not _cols_p: continue
                _mlt = _chunk.melt(id_vars=_SKR+['ean_norm'], value_vars=_cols_p,
                                   var_name='_col', value_name='precio_raw')
                _mlt['precio'] = pd.to_numeric(_mlt['precio_raw'].replace('NA', np.nan), errors='coerce')
                _mlt = _mlt[_mlt['precio'].notna() & (_mlt['precio'] > 0)].copy()
                if len(_mlt) == 0: continue
                _mlt['fecha'] = pd.to_datetime(_mlt['_col'].str[-8:], format='%Y%m%d', errors='coerce')
                _mlt = _mlt[_mlt['fecha'].notna()]
                if len(_mlt) == 0: continue
                # semana que cierra el jueves (mapeo sobre fechas unicas, es rapido)
                _uf = {_d: _semana_cierre(_d) for _d in _mlt['fecha'].dt.date.unique()}
                _mlt['semana'] = _mlt['fecha'].dt.date.map(_uf)
                _rows.append(_mlt.groupby(_SKR+['ean_norm','semana'], as_index=False)['precio'].median())
        _tmp_p.unlink(missing_ok=True)
    if not _rows: return None
    _df = pd.concat(_rows, ignore_index=True)
    # Autodeteccion centavos/pesos por mes (pre-2025 vienen en centavos)
    if _df['precio'].median() > 10_000: _df['precio'] /= 100
    return _df.groupby(_SKR+['ean_norm','semana'], as_index=False)['precio'].median()

_FR_MULT = {t: (1000.0 if FRESCO_INFO[t]['unidad'] == 'kg' else 12.0) for t in FRESCO_INFO}
def _colapsar(_df):
    if _df is None or len(_df) == 0: return None
    _e = (_df[_df['ean_norm'].isin(EANS_EMP)][_SKR + ['semana','ean_norm','precio']]
          .rename(columns={'ean_norm':'item','precio':'price'}))
    _f = _df[_df['ean_norm'].isin(EANS_FRESCOS)]
    if len(_f):
        _f = _f.copy()
        _f['item']  = _f['ean_norm'].map(EAN_TIPO)
        _f['price'] = _f['precio'] / _f['ean_norm'].map(EAN_NORMFACTOR) * _f['item'].map(_FR_MULT)
        _f = _f[_f['price'].notna() & (_f['price'] > 0)]
        # filtro de outliers intra-tipo dentro de cada sucursal-semana
        _med = _f.groupby(_SKR + ['semana','item'])['price'].transform('median')
        _f = _f[(_f['price'] >= _med / FRESCO_OUTLIER_K) & (_f['price'] <= _med * FRESCO_OUTLIER_K)]
        _fv = _f.groupby(_SKR + ['semana','item'], as_index=False)['price'].median()
    else:
        _fv = pd.DataFrame(columns=_SKR + ['semana','item','price'])
    return pd.concat([_e[_SKR + ['semana','item','price']], _fv], ignore_index=True)

if USE_CACHE and _cache_path.exists():
    _cache = pd.read_parquet(_cache_path)
    _cache = _cache[_cache['semana'].map(_mes_de_semana) < _mes_actual].copy()
else:
    _cache = pd.DataFrame(columns=_SKR + ['semana','item','price'])
_en_cache = set(_cache['semana'].map(_mes_de_semana).unique()) if len(_cache) else set()
_faltantes = [m for m in _meses_disp if m < _mes_actual and m not in _en_cache]
_nuevos = []
for _lbl in tqdm(_faltantes, desc='Meses cerrados'):
    _dc = _colapsar(_leer_mes(_lbl))
    if _dc is not None: _nuevos.append(_dc)
    gc.collect()
if _nuevos:
    _cache = pd.concat([_cache] + _nuevos, ignore_index=True)
    if USE_CACHE:
        _cache.to_parquet(_cache_path, compression='snappy', index=False)
        print(f'Cache actualizado: {_cache_path.name}')
del _nuevos; gc.collect()

# Mes en curso: siempre fresco. Guardamos el crudo por-EAN para los diagnosticos.
datos_ult_raw = _leer_mes(_mes_actual)
if datos_ult_raw is not None:
    datos_ult_raw = datos_ult_raw.copy(); datos_ult_raw['mes'] = _mes_actual
_actual = _colapsar(datos_ult_raw)
datos_sem = pd.concat([_cache] + ([_actual] if _actual is not None else []), ignore_index=True)
del _cache, _actual; gc.collect()
if len(datos_sem) == 0:
    raise RuntimeError('Sin datos para los EANs configurados. Revisa las canastas y los frescos.')
datos_sem = datos_sem.groupby(_SKR + ['item','semana'], as_index=False)['price'].median()
datos_sem['mes'] = datos_sem['semana'].map(_mes_de_semana)
datos_sem = datos_sem[datos_sem['mes'] >= MES_INICIO_HISTORICO].copy()

# La ULTIMA semana solo se usa si esta COMPLETA (su jueves de cierre ya ocurrio en los datos).
_maxf = max(_dt.date.fromisoformat(s) for s in datos_sem['semana'].unique())
_SEMANAS = sorted(datos_sem['semana'].unique())
ULTIMA_SEMANA = _SEMANAS[-1]
_TIPOS_FR = set(FRESCO_INFO)
print(f'Observaciones (sucursal x item x semana): {len(datos_sem):,}')
print(f'Semanas: {_SEMANAS[0]} -> {_SEMANAS[-1]} ({len(_SEMANAS)} semanas, cierran jueves)')
print(f'Sucursales: {datos_sem.groupby(_SKR).ngroups:,}')
print(f'Items con datos: empaquetados {datos_sem[datos_sem["item"].isin(EANS_EMP)]["item"].nunique()}/{len(EANS_EMP)} - '
      f'tipos frescos {datos_sem[datos_sem["item"].isin(_TIPOS_FR)]["item"].nunique()}/{len(_TIPOS_FR)}')
''' ))

# ── CELL 8 — NACIONAL PONDERADO + ARRASTRE + INDICE ENCADENADO ────────────────
cells.append(cell_code(r'''# ============================================================
# CELDA 8 - Precio nacional, arrastre e INDICE ENCADENADO de muestra apareada
# ============================================================
# Metodologia:
#  1. Precio NACIONAL del item por semana = mediana por provincia, luego promedio de esas
#     medianas PONDERADO POR POBLACION provincial. Asi DIA (42% de las sucursales) no define
#     el numero nacional.
#  2. ARRASTRE: si un item falta una semana, se arrastra su ultimo precio conocido hasta
#     MAX_SEMANAS_ARRASTRE. Ausencias mas largas quedan como NaN y disparan alerta.
#  3. INDICE ENCADENADO de MUESTRA APAREADA: la variacion entre t-1 y t se calcula solo con
#     los items presentes en AMBAS semanas, y el nivel se encadena. Es lo que hace INDEC ante
#     altas/bajas y es lo que elimina los saltos espurios de la serie.
#  4. NIVEL reportado = costo de la canasta COMPLETA en la semana ancla (cobertura >=95%),
#     retropolado con el indice encadenado. Queda interpretable en $ y sin saltos.
_SK = ['id_comercio','id_bandera','id_sucursal']
sval = datos_sem[~datos_sem['id_comercio'].isin(CADENAS_FILTRAR)].copy()

# Geografia de sucursales
_sg = suc_pais[_SK + ['PROVINCIA']].copy()
_sg['cadena']    = _sg.apply(asignar_cadena, axis=1)
_sg['provincia'] = _sg['PROVINCIA'].map(norm_prov)
_sg['region']    = _sg['provincia'].map(REGION_PROV).fillna('Otras')
_sg['suc_id']    = _sg['id_comercio'] + '|' + _sg['id_bandera'] + '|' + _sg['id_sucursal']
suc_geo = _sg.drop_duplicates(_SK)[_SK + ['cadena','provincia','region','suc_id']]
_n_otras = int((suc_geo['region'] == 'Otras').sum())
if _n_otras:
    print(f'AVISO: {_n_otras} sucursales sin region asignada -> ' +
          str(sorted(suc_geo.loc[suc_geo["region"]=="Otras","provincia"].unique())[:8]))

sval = sval.merge(suc_geo, on=_SK, how='left')
sval['provincia'] = sval['provincia'].fillna('Otras')
sval['region']    = sval['region'].fillna('Otras')

# ── 1. Precio nacional ponderado por poblacion ────────────────────────────────
_pi = sval.groupby(['item','semana','provincia'], as_index=False)['price'].median()
if AGG_NACIONAL == 'poblacion':
    _pi['w'] = _pi['provincia'].map(PESOS_POBLACION).fillna(0.0)
    _pi['wv'] = _pi['w'] * _pi['price']
    _g = _pi.groupby(['item','semana'], as_index=False).agg(
        wv=('wv','sum'), w=('w','sum'), med=('price','median'))
    _g['nac'] = np.where(_g['w'] > 0, _g['wv'] / _g['w'], _g['med'])
    nac_item = _g[['item','semana','nac']].copy()
    print('Nacional: mediana provincial ponderada por poblacion')
else:
    nac_item = sval.groupby(['item','semana'], as_index=False)['price'].median().rename(columns={'price':'nac'})
    print('Nacional: mediana simple entre sucursales')

# ── 2. Arrastre (forward-fill acotado) ────────────────────────────────────────
nac_wide = nac_item.pivot(index='semana', columns='item', values='nac').sort_index()
nac_obs  = nac_wide.notna()                                   # presencia REAL (diagnostico)
nac_ff   = nac_wide.ffill(limit=MAX_SEMANAS_ARRASTRE)         # con arrastre
_n_arr = int((nac_ff.notna() & ~nac_obs).sum().sum())
print(f'Panel nacional: {nac_wide.shape[1]} items x {nac_wide.shape[0]} semanas | '
      f'celdas arrastradas: {_n_arr:,} ({_n_arr/max(nac_ff.notna().sum().sum(),1)*100:.1f}%)')
nac_ff_long = (nac_ff.reset_index().melt(id_vars='semana', var_name='item', value_name='nac')
               .dropna(subset=['nac']))

# ── Receta de cada canasta ────────────────────────────────────────────────────
def _recipe(_name):
    _rows = []
    _usar_cat = _name in RUBRO_DESDE_CATEGORIA
    for _ean,(_desc,_q,_rub,_cat) in CANASTAS_EMP[_name].items():
        _r = (str(_cat).strip().title() if (_usar_cat and str(_cat).strip()) else _rub)
        _rows.append((_ean, float(_q), _r, 'emp'))
    _FRESH_POS = {'Popular': 0, 'Media': 1, 'Ejecutiva': 2, 'Representativa': 3}
    _p = _FRESH_POS.get(_name)
    if _p is not None and _name not in CANASTAS_SIN_FRESCOS:
        for _tipo, _info in FRESCO_INFO.items():
            _q = _info['qty'][_p] if _p < len(_info['qty']) else _info['qty'][-1]
            if _q and _q > 0:
                _rows.append((_tipo, float(_q), _info['rubro'], 'fresh'))
    return pd.DataFrame(_rows, columns=['item','qty','rubro','kind'])

RECETAS = {n: _recipe(n) for n in CANASTAS_ACTIVAS}

# ── 3-4. Indice encadenado + nivel ────────────────────────────────────────────
serie_sem_dict = {}; aporte_dict = {}
for _name in CANASTAS_ACTIVAS:
    _rec = RECETAS[_name]
    _its = [i for i in _rec['item'] if i in nac_ff.columns]
    if not _its:
        serie_sem_dict[_name] = pd.DataFrame(); continue
    _q = _rec.set_index('item')['qty']
    _V = nac_ff[_its].mul(_q.reindex(_its), axis=1)     # aporte $ de cada item por semana
    aporte_dict[_name] = _V
    _sem = list(_V.index)
    _idx = [100.0]
    for _t in range(1, len(_sem)):
        _a = _V.iloc[_t]; _b = _V.iloc[_t-1]
        _m = _a.notna() & _b.notna()
        _den = _b[_m].sum()
        _idx.append(_idx[-1] * ((_a[_m].sum()/_den) if (_m.any() and _den > 0) else 1.0))
    _idx = pd.Series(_idx, index=_sem)
    _directo = _V.sum(axis=1, min_count=1)
    _cov = _V.notna().sum(axis=1) / len(_its)
    _ok = _cov[_cov >= 0.95].index
    _anchor = _ok[-1] if len(_ok) else _sem[-1]
    _nivel = _directo.loc[_anchor] * _idx / _idx.loc[_anchor]
    _s = pd.DataFrame({'semana': _sem,
                       'costo_mediana': _nivel.values,          # nivel encadenado (headline)
                       'costo_directo': _directo.values,        # suma cruda (referencia)
                       'indice_100': (_idx/_idx.iloc[0]*100).values,
                       'items_con_precio': _V.notna().sum(axis=1).values,
                       'items_receta': len(_its)})
    _s['mes'] = _s['semana'].map(_mes_de_semana)
    _s['var_sem_%'] = _s['costo_mediana'].pct_change(fill_method=None) * 100
    serie_sem_dict[_name] = _s
    print(f'  [{_name}] {len(_s)} semanas | items {len(_its)} | ancla {_anchor} | '
          f'ultimo costo ${_s["costo_mediana"].iloc[-1]:,.0f} ({_s["var_sem_%"].iloc[-1]:+.1f}% sem)')

# ── Costo por SUCURSAL (para desagregar por provincia/cadena/region) ──────────
# Item faltante en una sucursal-semana -> se imputa con el precio nacional (ya arrastrado).
def _costo_por_rubro(_name):
    _rec = RECETAS[_name]
    _n_emp = int((_rec['kind']=='emp').sum())
    _av = nac_ff_long.merge(_rec, on='item', how='inner')
    _av['val'] = _av['nac'] * _av['qty']
    _all = _av.groupby(['semana','rubro'], as_index=False)['val'].sum().rename(columns={'val':'val_all'})
    _pv = sval.merge(_rec, on='item', how='inner').merge(nac_ff_long, on=['item','semana'], how='left')
    _pv['store_val'] = _pv['price'] * _pv['qty']
    _pv['nac_val']   = _pv['nac']   * _pv['qty']
    _g = (_pv.groupby(_SK + ['semana','rubro'])
            .agg(S_store=('store_val','sum'), S_nac=('nac_val','sum'),
                 n_emp=('kind', lambda s: (s=='emp').sum())).reset_index())
    _g = _g.merge(_all, on=['semana','rubro'], how='left')
    _g['costo'] = _g['S_store'] + (_g['val_all'].fillna(0) - _g['S_nac'].fillna(0))
    _g['canasta'] = _name
    _cov = _g.groupby(_SK + ['semana'])['n_emp'].sum().reset_index(name='n_emp_tot')
    _cov['frac'] = _cov['n_emp_tot'] / max(_n_emp, 1)
    _ok = _cov[_cov['frac'] >= FRAC_PRODUCTOS_MIN][_SK + ['semana']]
    return _g.merge(_ok, on=_SK + ['semana'], how='inner')

costo_rubro = pd.concat([_costo_por_rubro(n) for n in CANASTAS_ACTIVAS], ignore_index=True)
costo_rubro['mes'] = costo_rubro['semana'].map(_mes_de_semana)
costo_rubro = costo_rubro.merge(suc_geo, on=_SK, how='left')
costo_rubro['provincia'] = costo_rubro['provincia'].fillna('Otras')
costo_rubro['region']    = costo_rubro['region'].fillna('Otras')
costo_suc = (costo_rubro.groupby(['canasta'] + _SK + ['semana','mes','cadena','provincia','region','suc_id'],
                                 as_index=False)['costo'].sum())
print(f'Costo por sucursal-semana: {len(costo_suc):,} filas | '
      f'sucursales {costo_suc["suc_id"].nunique():,} (cobertura minima {FRAC_PRODUCTOS_MIN:.0%})')
''' ))

# ── CELL 9 — RUBROS ───────────────────────────────────────────────────────────
cells.append(cell_code(r'''# ============================================================
# CELDA 9 - Desagregacion por RUBRO (nacional) + detalle por item
# ============================================================
# Se calcula sobre el panel NACIONAL (nac_ff x cantidad), no sobre la mediana entre
# sucursales, para que los rubros sumen exactamente el costo de la canasta.
rubro_sem_dict = {}; rubro_share_dict = {}; detalle_dict = {}
_ult_mes = max(s['mes'].max() for s in serie_sem_dict.values() if len(s))

for _name in CANASTAS_ACTIVAS:
    _rec = RECETAS[_name]; _V = aporte_dict.get(_name)
    if _V is None or not len(_V): continue
    _map = _rec.set_index('item')['rubro']
    _long = (_V.reset_index().melt(id_vars='semana', var_name='item', value_name='val')
               .dropna(subset=['val']))
    _long['rubro'] = _long['item'].map(_map)
    _rs = _long.groupby(['semana','rubro'], as_index=False)['val'].sum().rename(columns={'val':'costo'})
    _rs['mes'] = _rs['semana'].map(_mes_de_semana)
    rubro_sem_dict[_name] = _rs.sort_values(['semana','rubro'])
    _rm = _rs[_rs['mes']==_ult_mes].groupby('rubro')['costo'].mean()
    _sh = _rm.reset_index().rename(columns={'costo':'costo_mensual'})
    _sh['participacion_%'] = (_sh['costo_mensual'] / _sh['costo_mensual'].sum() * 100).round(1)
    rubro_share_dict[_name] = _sh.sort_values('costo_mensual', ascending=False)
    # detalle por item (ultimo mes)
    _um = [s for s in _V.index if _mes_de_semana(s)==_ult_mes]
    _pu = _V.loc[_um].mean() / _rec.set_index('item')['qty'].reindex(_V.columns)
    _det = _rec.copy()
    _det['precio_unit'] = _det['item'].map(_pu)
    _det['costo'] = _det['precio_unit'] * _det['qty']
    _det['detalle'] = _det.apply(lambda r: (str(CANASTAS_EMP[_name][r['item']][0]) if r['kind']=='emp'
                                            else f"{r['item']} ($/{FRESCO_INFO[r['item']]['unidad']})"), axis=1)
    detalle_dict[_name] = _det[['rubro','detalle','kind','qty','precio_unit','costo']].sort_values(
        ['rubro','costo'], ascending=[True,False])

for _name in CANASTAS_ACTIVAS:
    _sh = rubro_share_dict.get(_name)
    if _sh is None: continue
    print(f'=== [{_name}] Composicion por rubro ({_ult_mes}) - total ${_sh["costo_mensual"].sum():,.0f} ===')
    print(_sh.to_string(index=False)); print()
''' ))

# ── CELL 10 — IPC + MENSUAL ───────────────────────────────────────────────────
cells.append(cell_code(r'''# ============================================================
# CELDA 10 - IPC INDEC + serie MENSUAL + comparacion vs IPC
# ============================================================
IPC_PATH = SEPA_DIR / 'IPC.xlsx'
ipc = None
if IPC_PATH.exists():
    _ipc = pd.read_excel(IPC_PATH)
    _fcol = next((c for c in _ipc.columns if str(c).lower().strip() in ('date','fecha','mes','period')), _ipc.columns[0])
    if pd.api.types.is_datetime64_any_dtype(_ipc[_fcol]):
        _ipc['mes'] = _ipc[_fcol].dt.strftime('%Y-%m')
    else:
        _ME = {'ene':1,'feb':2,'mar':3,'abr':4,'may':5,'jun':6,'jul':7,'ago':8,'sep':9,'oct':10,'nov':11,'dic':12}
        def _pf(v):
            if pd.isna(v): return pd.NaT
            s=str(v).strip().lower(); p=s.split('-')
            if len(p)==2 and p[0][:3] in _ME:
                try: return pd.Timestamp(year=int(p[1]) if len(p[1])==4 else 2000+int(p[1]), month=_ME[p[0][:3]], day=1)
                except Exception: pass
            return pd.to_datetime(v, errors='coerce')
        _ipc['mes'] = _ipc[_fcol].apply(_pf).dt.strftime('%Y-%m')
    _rm = {}
    for c in _ipc.columns:
        cl = str(c).lower()
        if 'nivel general' in cl: _rm[c]='ipc_general'
        elif 'alimentos y bebidas no alc' in cl: _rm[c]='ipc_alimentos'
    _ipc = _ipc.rename(columns=_rm)
    for c in ['ipc_general','ipc_alimentos']:
        if c in _ipc.columns:
            _ipc[c]=pd.to_numeric(_ipc[c].astype(str).str.replace(',','.',regex=False), errors='coerce')
    _cols=['mes','ipc_general']+(['ipc_alimentos'] if 'ipc_alimentos' in _ipc.columns else [])
    ipc=_ipc[_cols].dropna(subset=['ipc_general']).sort_values('mes').reset_index(drop=True)
    if 'ipc_alimentos' not in ipc.columns: ipc['ipc_alimentos']=np.nan
    print(f'IPC: {len(ipc)} meses ({ipc["mes"].min()}->{ipc["mes"].max()})')
else:
    print(f'AVISO: IPC.xlsx no encontrado en {SEPA_DIR} - se omite la comparacion vs IPC.')

# Serie MENSUAL = promedio de las semanas del mes (nivel encadenado)
serie_mes_dict = {}; comparativa_dict = {}
for _name in CANASTAS_ACTIVAS:
    _s = serie_sem_dict.get(_name)
    if _s is None or not len(_s): continue
    _sm = (_s.groupby('mes').agg(canasta_mediana=('costo_mediana','mean'),
                                 indice_100=('indice_100','mean'),
                                 n_semanas=('semana','size')).reset_index().sort_values('mes'))
    _ns = costo_suc[costo_suc['canasta']==_name].groupby('mes')['suc_id'].nunique().rename('n_sucursales')
    _sm = _sm.merge(_ns, on='mes', how='left')
    _sm['var_mensual_%'] = _sm['canasta_mediana'].pct_change(fill_method=None) * 100
    serie_mes_dict[_name] = _sm
    if ipc is not None and len(_sm):
        _c = _sm.merge(ipc, on='mes', how='left')
        _b  = _c['indice_100'].iloc[0]
        _bi = _c['ipc_general'].dropna().iloc[0] if _c['ipc_general'].notna().any() else np.nan
        _ba = _c['ipc_alimentos'].dropna().iloc[0] if _c['ipc_alimentos'].notna().any() else np.nan
        _c['idx_canasta']  = (_c['indice_100'] / _b * 100).round(1)
        _c['idx_ipc_gral'] = (_c['ipc_general'] / _bi * 100).round(1) if _bi==_bi else np.nan
        _c['idx_ipc_alim'] = (_c['ipc_alimentos'] / _ba * 100).round(1) if _ba==_ba else np.nan
        comparativa_dict[_name] = _c
        _n0 = _c[_c['idx_ipc_gral'].notna()]
        if len(_n0) >= 2:
            print(f'  [{_name}] {_c["mes"].iloc[0]}->{_c["mes"].iloc[-1]}: canasta {_c["idx_canasta"].iloc[-1]:.0f} '
                  f'vs IPC {_n0["idx_ipc_gral"].iloc[-1]:.0f} (base 100)')
    else:
        comparativa_dict[_name] = _sm.copy()
''' ))

# ── CELL 11 — GRAFICOS ────────────────────────────────────────────────────────
cells.append(cell_code(r'''# ============================================================
# CELDA 11 - Graficos
# ============================================================
_act = [n for n in CANASTAS_ACTIVAS if len(serie_sem_dict.get(n, []))]
# Fig 1 - Indice semanal encadenado (base 100 primera semana)
fig, ax = plt.subplots(figsize=(13,6))
for _name in _act:
    _s = serie_sem_dict[_name]
    ax.plot(_s['semana'], _s['indice_100'], marker=CANASTA_MARKERS.get(_name,'o'),
            ms=3, color=CANASTA_COLORS.get(_name), label=_name)
ax.set_title(f'Indice de costo SEMANAL encadenado (base 100 = {serie_sem_dict[_act[0]]["semana"].iloc[0]}) - semanas cierran jueves')
ax.set_ylabel('Indice (base 100)'); ax.legend(); ax.grid(alpha=.3)
_xt = serie_sem_dict[_act[0]]['semana']
ax.set_xticks(_xt[::max(1,len(_xt)//12)]); plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
plt.tight_layout(); plt.show()

# Fig 2 - Mensual vs IPC
if ipc is not None:
    fig, ax = plt.subplots(figsize=(13,6))
    for _name in _act:
        _c = comparativa_dict.get(_name)
        if _c is not None and 'idx_canasta' in _c.columns:
            ax.plot(_c['mes'], _c['idx_canasta'], marker=CANASTA_MARKERS.get(_name,'o'), ms=4,
                    color=CANASTA_COLORS.get(_name), label=f'Canasta {_name}')
    _c0 = comparativa_dict[_act[0]]
    if 'idx_ipc_gral' in _c0.columns:
        ax.plot(_c0['mes'], _c0['idx_ipc_gral'], '--', color='black', lw=2, label='IPC General')
        if _c0['idx_ipc_alim'].notna().any():
            ax.plot(_c0['mes'], _c0['idx_ipc_alim'], ':', color='gray', lw=2, label='IPC Alimentos')
    ax.set_title('Canastas vs IPC - indice mensual (base 100)'); ax.set_ylabel('Indice (base 100)')
    ax.legend(); ax.grid(alpha=.3); plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
    plt.tight_layout(); plt.show()

# Fig 3 - Composicion por rubro
_rubros = sorted(set().union(*[set(rubro_share_dict[n]['rubro']) for n in _act if n in rubro_share_dict]))
_cmap = plt.get_cmap('tab20', max(1, len(_rubros)))
fig, ax = plt.subplots(figsize=(12,6)); _bottom = np.zeros(len(_act))
for _i,_r in enumerate(_rubros):
    _vals = [float(rubro_share_dict[n].set_index('rubro')['costo_mensual'].get(_r, 0)) if n in rubro_share_dict else 0 for n in _act]
    ax.bar(_act, _vals, bottom=_bottom, label=_r, color=_cmap(_i)); _bottom += np.array(_vals)
ax.set_title(f'Composicion del costo por rubro - {_ult_mes}'); ax.set_ylabel('$ / mes')
ax.legend(bbox_to_anchor=(1.02,1), loc='upper left', fontsize=7); ax.grid(alpha=.3, axis='y')
plt.tight_layout(); plt.show()
''' ))

# ── CELL 12 — PROVINCIA / CADENA / REGION (controlando por cadena) ────────────
cells.append(cell_code(r'''# ============================================================
# CELDA 12 - Desagregacion por PROVINCIA, CADENA y REGION (ultimo mes)
# ============================================================
# Ademas del costo crudo se calcula un INDICE RELATIVO CONTROLANDO POR CADENA:
#   para cada cadena presente en la provincia, precio_provincia / precio_nacional_de_esa_cadena;
#   despues se promedia entre cadenas ponderando por sucursales.
# Responde "que tan cara es la provincia" SIN que el resultado dependa de que mix de cadenas
# opera ahi (Coto esta en pocas provincias, DIA en muchas, La Anonima domina la Patagonia...).
prov_dict = {}; cadena_dict = {}; region_dict = {}; serie_region_dict = {}
_cs_um = costo_suc[costo_suc['mes'] == _ult_mes]

def _idx_controlado(_cs, _geo):
    _cp = _cs.groupby(['cadena', _geo]).agg(costo=('costo','median'), n=('suc_id','nunique')).reset_index()
    _cn = _cs.groupby('cadena').agg(costo_nac=('costo','median')).reset_index()
    _cp = _cp.merge(_cn, on='cadena')
    _cp = _cp[_cp['costo_nac'] > 0]
    _cp['rel'] = _cp['costo'] / _cp['costo_nac']
    _out = (_cp.groupby(_geo).apply(lambda g: np.average(g['rel'], weights=g['n']) * 100)
              .reset_index(name='idx_vs_nacional'))
    _out['n_cadenas'] = _cp.groupby(_geo)['cadena'].nunique().values
    return _out

for _name in CANASTAS_ACTIVAS:
    _cs = _cs_um[_cs_um['canasta'] == _name]
    if not len(_cs): continue
    for _geo, _dic in (('provincia', prov_dict), ('region', region_dict)):
        _d = (_cs.groupby(_geo).agg(costo_mediana=('costo','median'), costo_prom=('costo', _pmean),
                                    n_sucursales=('suc_id','nunique'), n_cadenas=('cadena','nunique')).reset_index())
        _d = _d.merge(_idx_controlado(_cs, _geo)[[_geo,'idx_vs_nacional']], on=_geo, how='left')
        _d['confiable'] = (_d['n_sucursales'] >= MIN_SUC_AGG) & (_d['n_cadenas'] >= 2)
        _dic[_name] = _d.sort_values('costo_mediana')
    _c = (_cs.groupby('cadena').agg(costo_mediana=('costo','median'), costo_prom=('costo', _pmean),
                                    n_sucursales=('suc_id','nunique'), n_provincias=('provincia','nunique')).reset_index())
    _c['confiable'] = _c['n_sucursales'] >= MIN_SUC_AGG
    cadena_dict[_name] = _c.sort_values('costo_mediana')
    _cr = costo_suc[costo_suc['canasta'] == _name]
    _sr = (_cr.groupby(['region','semana']).agg(costo_mediana=('costo','median'),
            costo_prom=('costo', _pmean), n_sucursales=('suc_id','nunique')).reset_index())
    _sr['mes'] = _sr['semana'].map(_mes_de_semana)
    serie_region_dict[_name] = _sr.sort_values(['region','semana'])

for _name in CANASTAS_ACTIVAS:
    if _name not in prov_dict: continue
    _p = prov_dict[_name]; _pc = _p[_p['confiable']]
    _c = cadena_dict[_name]; _cc = _c[_c['confiable']]
    _rg = region_dict[_name]
    print(f'=== [{_name}] {_ult_mes} - provincias confiables (n>={MIN_SUC_AGG} y >=2 cadenas): {len(_pc)} ===')
    if len(_pc):
        print(f'   costo crudo:  mas barata {_pc.iloc[0]["provincia"]} ${_pc.iloc[0]["costo_mediana"]:,.0f} | '
              f'mas cara {_pc.iloc[-1]["provincia"]} ${_pc.iloc[-1]["costo_mediana"]:,.0f}')
        _pi = _pc.sort_values('idx_vs_nacional')
        print(f'   controlando por cadena (100 = nacional): ' + ' | '.join(
            f'{r["provincia"]} {r["idx_vs_nacional"]:.0f}' for _, r in _pi.head(3).iterrows()) +
            '  ...  ' + ' | '.join(f'{r["provincia"]} {r["idx_vs_nacional"]:.0f}' for _, r in _pi.tail(3).iterrows()))
    if len(_cc):
        print(f'   cadena mas barata: {_cc.iloc[0]["cadena"]} ${_cc.iloc[0]["costo_mediana"]:,.0f} | '
              f'mas cara: {_cc.iloc[-1]["cadena"]} ${_cc.iloc[-1]["costo_mediana"]:,.0f}')
    print('   por region (crudo | controlado): ' + ' | '.join(
        f'{r["region"]} ${r["costo_mediana"]:,.0f} ({r["idx_vs_nacional"]:.0f})'
        for _, r in _rg.sort_values('costo_mediana').iterrows()))
''' ))

# ── CELL 13 — DIAGNOSTICOS ────────────────────────────────────────────────────
cells.append(cell_code(r'''# ============================================================
# CELDA 13 - DIAGNOSTICOS: cobertura, presencia y alertas de reemplazo
# ============================================================
if datos_ult_raw is None or len(datos_ult_raw) == 0:
    _dm = pd.DataFrame(columns=_SK + ['ean_norm','semana','precio','mes','cadena','provincia','suc_id'])
else:
    _dm = datos_ult_raw.merge(suc_geo, on=_SK, how='left')

# --- Empaquetados ---
_emp_cov = (_dm[_dm['ean_norm'].isin(EANS_EMP)].groupby('ean_norm')
            .agg(n_cadenas=('cadena','nunique'), n_provincias=('provincia','nunique'),
                 n_sucursales=('suc_id','nunique'), precio_med=('precio','median')).reset_index())
_rows = []
for _name in CANASTAS_ACTIVAS:
    for _ean,(_desc,_q,_rub,_cat) in CANASTAS_EMP[_name].items():
        _r = _emp_cov[_emp_cov['ean_norm']==_ean]
        _rows.append({'canasta':_name,'ean':_ean,'descripcion':_desc,'rubro':_rub,'cantidad':_q,
                      'n_cadenas':int(_r['n_cadenas'].iloc[0]) if len(_r) else 0,
                      'n_provincias':int(_r['n_provincias'].iloc[0]) if len(_r) else 0,
                      'n_sucursales':int(_r['n_sucursales'].iloc[0]) if len(_r) else 0,
                      'precio_med':round(float(_r['precio_med'].iloc[0]),1) if len(_r) else None})
cobertura_emp = pd.DataFrame(_rows)
cobertura_emp['comparable'] = (cobertura_emp['n_cadenas']>=3) & (cobertura_emp['n_provincias']>=15)
_sindata = cobertura_emp[cobertura_emp['n_sucursales']==0]
_pobre   = cobertura_emp[(cobertura_emp['n_sucursales']>0) & (~cobertura_emp['comparable'])]
print(f'=== EMPAQUETADOS - cobertura ({_ult_mes}) ===')
print(f'  Items-canasta: {len(cobertura_emp)} | SIN datos: {len(_sindata)} | baja comparabilidad: {len(_pobre)}')
if len(_sindata):
    print(_sindata[['canasta','ean','descripcion']].to_string(index=False))
if len(_pobre):
    print(_pobre[['canasta','descripcion','n_cadenas','n_provincias','n_sucursales']].to_string(index=False))

# --- Frescos por tipo ---
_fr_dm = _dm[_dm['ean_norm'].isin(EANS_FRESCOS)].copy()
_fr_dm['tipo'] = _fr_dm['ean_norm'].map(EAN_TIPO)
cobertura_frescos = (_fr_dm.groupby('tipo')
    .agg(n_variantes=('ean_norm','nunique'), n_cadenas=('cadena','nunique'),
         n_provincias=('provincia','nunique'), n_sucursales=('suc_id','nunique')).reset_index())
cobertura_frescos['unidad'] = cobertura_frescos['tipo'].map(lambda t: FRESCO_INFO[t]['unidad'])
cobertura_frescos['rubro']  = cobertura_frescos['tipo'].map(lambda t: FRESCO_INFO[t]['rubro'])
_pn = nac_ff_long[(nac_ff_long['item'].isin(FRESCO_INFO)) &
                  (nac_ff_long['semana'].map(_mes_de_semana)==_ult_mes)]
_pnm = _pn.groupby('item')['nac'].median()
cobertura_frescos['precio_norm_med'] = cobertura_frescos['tipo'].map(lambda t: round(float(_pnm.get(t, np.nan)),1))
cobertura_frescos = cobertura_frescos.merge(
    cobertura_fresco_maestro[['tipo','n_EANs_maestro','n_EANs_usables']], on='tipo', how='left')
cobertura_frescos = cobertura_frescos.sort_values(['rubro','tipo'])
print(f'\n=== FRESCOS - cobertura por tipo ({_ult_mes}) ===')
print(cobertura_frescos[['tipo','rubro','unidad','n_variantes','n_cadenas','n_provincias',
                         'n_sucursales','precio_norm_med']].to_string(index=False))
_fr_pobre = cobertura_frescos[(cobertura_frescos['n_cadenas']<3)|(cobertura_frescos['n_provincias']<10)]
if len(_fr_pobre):
    print(f'  AVISO baja cobertura: {list(_fr_pobre["tipo"])}')

# --- PRESENCIA por item x mes (altas/bajas) y alertas de reemplazo ---
_pm = nac_obs.copy()
_pm['mes'] = [_mes_de_semana(s) for s in _pm.index]
presencia_items = (_pm.groupby('mes').mean().T * 100).round(0)   # % de semanas del mes con dato real
_items_receta = sorted(set().union(*[set(RECETAS[n]['item']) for n in CANASTAS_ACTIVAS]))
presencia_items = presencia_items.reindex([i for i in _items_receta if i in presencia_items.index])
def _etiqueta(i):
    if i in FRESCO_INFO: return f'{i} (fresco)'
    for n in CANASTAS_ACTIVAS:
        if i in CANASTAS_EMP[n]: return CANASTAS_EMP[n][i][0]
    return i
presencia_items.insert(0, 'descripcion', [_etiqueta(i) for i in presencia_items.index])

_ultN = _SEMANAS[-MAX_SEMANAS_ARRASTRE:]
_alertas = []
for _i in _items_receta:
    _en = [n for n in CANASTAS_ACTIVAS if _i in set(RECETAS[n]['item'])]
    if _i not in nac_obs.columns:
        _alertas.append({'item':_i,'descripcion':_etiqueta(_i),'canastas':', '.join(_en),
                         'estado':'NUNCA aparece en el SEPA','ult_semana_con_dato':None})
        continue
    _s = nac_obs[_i]
    if not _s.loc[_ultN].any():
        _ult = _s[_s].index.max() if _s.any() else None
        _alertas.append({'item':_i,'descripcion':_etiqueta(_i),'canastas':', '.join(_en),
                         'estado':f'sin dato hace >{MAX_SEMANAS_ARRASTRE} semanas','ult_semana_con_dato':_ult})
alertas_reemplazo = pd.DataFrame(_alertas)
print(f'\n=== TRAZABILIDAD ===')
print(f'  Items en recetas: {len(_items_receta)} | con panel nacional: {len(presencia_items)}')
print(f'  Candidatos a REEMPLAZO (sin dato en las ultimas {MAX_SEMANAS_ARRASTRE} semanas): {len(alertas_reemplazo)}')
if len(alertas_reemplazo):
    print(alertas_reemplazo[['descripcion','canastas','estado','ult_semana_con_dato']].to_string(index=False))
print('\n>>> Copia los bloques AVISO y las tablas de cobertura para refinar la composicion.')
''' ))

# ── CELL 14 — EXCEL ───────────────────────────────────────────────────────────
cells.append(cell_code(r'''# ============================================================
# CELDA 14 - Exportacion Excel
# ============================================================
_xlsx = RESULTS_DIR / f'canastas_alternativas_{ULTIMA_SEMANA}.xlsx'
with pd.ExcelWriter(_xlsx, engine='openpyxl') as _w:
    pd.DataFrame([{
        'parametro':'Semana','valor':f'ventana de 7 dias que cierra el {["lunes","martes","miercoles","jueves","viernes","sabado","domingo"][DIA_CIERRE_SEMANA]}'},
        {'parametro':'Ultima semana','valor':ULTIMA_SEMANA},
        {'parametro':'Ultimo mes','valor':_ult_mes},
        {'parametro':'Indice','valor':'encadenado de muestra apareada (items presentes en ambas semanas)'},
        {'parametro':'Nivel ($)','valor':'canasta completa en la semana ancla, retropolada con el indice'},
        {'parametro':'Nacional','valor':('mediana provincial ponderada por poblacion' if AGG_NACIONAL=='poblacion' else 'mediana simple')},
        {'parametro':'Arrastre','valor':f'ultimo precio conocido hasta {MAX_SEMANAS_ARRASTRE} semanas'},
        {'parametro':'Frescos','valor':f'precio del tipo = mediana de variantes por sucursal-semana, outliers fuera de [med/{FRESCO_OUTLIER_K}, med*{FRESCO_OUTLIER_K}] descartados'},
        {'parametro':'Cobertura minima sucursal','valor':f'{FRAC_PRODUCTOS_MIN:.0%} de los empaquetados de la canasta'},
    ]).to_excel(_w, 'Metodologia', index=False)
    _res = []
    for _name in CANASTAS_ACTIVAS:
        _sm = serie_mes_dict.get(_name); _ss = serie_sem_dict.get(_name)
        if _ss is None or not len(_ss): continue
        _res.append({'canasta':_name,
                     'costo_mensual_ult': round(float(_sm['canasta_mediana'].iloc[-1]),0) if _sm is not None and len(_sm) else None,
                     'var_mensual_%': round(float(_sm['var_mensual_%'].iloc[-1]),1) if _sm is not None and len(_sm)>1 else None,
                     'costo_semanal_ult': round(float(_ss['costo_mediana'].iloc[-1]),0),
                     'var_semanal_%': round(float(_ss['var_sem_%'].iloc[-1]),1) if len(_ss)>1 else None,
                     'indice_base100': round(float(_ss['indice_100'].iloc[-1]),1),
                     'n_productos_emp': len(CANASTAS_EMP[_name]),
                     'n_tipos_frescos': int((RECETAS[_name]['kind']=='fresh').sum())})
    pd.DataFrame(_res).to_excel(_w, 'Resumen', index=False)
    for _name in CANASTAS_ACTIVAS:
        _sfx = _name[:18]
        if _name in serie_sem_dict and len(serie_sem_dict[_name]): serie_sem_dict[_name].to_excel(_w, f'Sem_{_sfx}'[:31], index=False)
        if _name in serie_mes_dict: serie_mes_dict[_name].to_excel(_w, f'Mes_{_sfx}'[:31], index=False)
        if _name in comparativa_dict: comparativa_dict[_name].to_excel(_w, f'vsIPC_{_sfx}'[:31], index=False)
        if _name in rubro_sem_dict: rubro_sem_dict[_name].to_excel(_w, f'Rubro_sem_{_sfx}'[:31], index=False)
        if _name in rubro_share_dict: rubro_share_dict[_name].to_excel(_w, f'Comp_rubro_{_sfx}'[:31], index=False)
        if _name in detalle_dict: detalle_dict[_name].to_excel(_w, f'Detalle_{_sfx}'[:31], index=False)
        if _name in prov_dict: prov_dict[_name].to_excel(_w, f'Prov_{_sfx}'[:31], index=False)
        if _name in cadena_dict: cadena_dict[_name].to_excel(_w, f'Cadena_{_sfx}'[:31], index=False)
        if _name in region_dict: region_dict[_name].to_excel(_w, f'Region_{_sfx}'[:31], index=False)
        if _name in serie_region_dict: serie_region_dict[_name].to_excel(_w, f'RegionSem_{_sfx}'[:31], index=False)
    cobertura_emp.to_excel(_w, 'Cobertura_emp', index=False)
    cobertura_frescos.to_excel(_w, 'Cobertura_frescos', index=False)
    presencia_items.to_excel(_w, 'Presencia_items')
    (alertas_reemplazo if len(alertas_reemplazo) else pd.DataFrame({'sin_alertas':['ok']})
     ).to_excel(_w, 'Alertas_reemplazo', index=False)
print(f'Excel: {_xlsx.name}  ({_xlsx.stat().st_size/1024:.0f} KB)')
print(f'   Guardado en: {_xlsx.parent}')
print('   Hojas: Metodologia, Resumen, Sem_*, Mes_*, vsIPC_*, Rubro_sem_*, Comp_rubro_*, '
      'Detalle_*, Prov_*, Cadena_*, Region_*, RegionSem_*, Cobertura_emp, Cobertura_frescos, '
      'Presencia_items, Alertas_reemplazo')
''' ))

# ── CELL 15 — REPORTE ─────────────────────────────────────────────────────────
cells.append(cell_code(r'''# ============================================================
# CELDA 15 - REPORTE PARA CLAUDE (copia y pega TODO el bloque)
# ============================================================
print('='*72)
print('REPORTE PARA CLAUDE - canastas alternativas nb07 v5')
print('='*72)
print(f'Ultima semana (cierra jueves): {ULTIMA_SEMANA} | Ultimo mes: {_ult_mes}')
print(f'Canastas activas: {CANASTAS_ACTIVAS}')
print(f'Nacional: {AGG_NACIONAL} | arrastre: {MAX_SEMANAS_ARRASTRE} sem | outlier K: {FRESCO_OUTLIER_K} | frac min: {FRAC_PRODUCTOS_MIN}')

for _name in CANASTAS_ACTIVAS:
    _ss = serie_sem_dict.get(_name)
    if _ss is None or not len(_ss): continue
    print('\n' + '-'*72)
    print(f'### CANASTA: {_name}')
    _sm = serie_mes_dict.get(_name)
    try:
        _fin = float(_sm['canasta_mediana'].iloc[-1]); _ini = float(_sm['canasta_mediana'].iloc[0])
        _acum = (_fin/_ini - 1)*100 if _ini else float('nan')
        _vm = float(_sm['var_mensual_%'].iloc[-1]) if len(_sm)>1 else float('nan')
        _nsuc = int(_sm['n_sucursales'].iloc[-1]) if _sm['n_sucursales'].notna().any() else 0
        print(f'  Costo mensual ({_ult_mes}): ${_fin:,.0f} | var mes: {_vm:+.1f}% | '
              f'acumulado {_sm["mes"].iloc[0]}->{_sm["mes"].iloc[-1]}: {_acum:+.1f}% | n_suc: {_nsuc}')
        print(f'  Semanal: ${float(_ss["costo_mediana"].iloc[-1]):,.0f} ({float(_ss["var_sem_%"].iloc[-1]):+.1f}% sem) | '
              f'items con precio {int(_ss["items_con_precio"].iloc[-1])}/{int(_ss["items_receta"].iloc[-1])}')
    except Exception as e:
        print('  (serie no disponible:', e, ')')
    try:
        _c = comparativa_dict.get(_name)
        if _c is not None and 'idx_canasta' in _c.columns and _c['idx_canasta'].notna().any():
            _msg = f'  vs IPC (base 100 en {_c["mes"].iloc[0]}): canasta = {float(_c["idx_canasta"].dropna().iloc[-1]):.0f}'
            if _c['idx_ipc_gral'].notna().any(): _msg += f' | IPC gral = {float(_c["idx_ipc_gral"].dropna().iloc[-1]):.0f}'
            if _c['idx_ipc_alim'].notna().any(): _msg += f' | IPC alim = {float(_c["idx_ipc_alim"].dropna().iloc[-1]):.0f}'
            print(_msg)
    except Exception: pass
    try:
        _sh = rubro_share_dict[_name]
        print(f'  Composicion por rubro (total ${_sh["costo_mensual"].sum():,.0f}):')
        for _,r in _sh.iterrows():
            print(f'      {r["rubro"]:<28} ${r["costo_mensual"]:>11,.0f}   {r["participacion_%"]:>5.1f}%')
    except Exception: pass
    try:
        _rg = region_dict[_name].sort_values('costo_mediana')
        print('  Region (costo | indice controlando por cadena, 100=nacional): ' + ' | '.join(
            f'{r["region"]} ${r["costo_mediana"]:,.0f} ({r["idx_vs_nacional"]:.0f}, n={int(r["n_sucursales"])})'
            for _, r in _rg.iterrows()))
        _p = prov_dict[_name]; _pc = _p[_p['confiable']].sort_values('idx_vs_nacional')
        if len(_pc):
            print('  Provincias confiables (indice controlado): ' + ' | '.join(
                f'{r["provincia"]} {r["idx_vs_nacional"]:.0f}' for _, r in _pc.iterrows()))
        _c2 = cadena_dict[_name]; _cc = _c2[_c2['confiable']]
        if len(_cc):
            print('  Cadenas: ' + ' | '.join(f'{r["cadena"]} ${r["costo_mediana"]:,.0f}' for _, r in _cc.iterrows()))
    except Exception: pass

print('\n' + '-'*72)
print('### COBERTURA Y TRAZABILIDAD')
try:
    print(f'  Empaquetados (items-canasta): {len(cobertura_emp)} | SIN datos: {int((cobertura_emp["n_sucursales"]==0).sum())} | '
          f'baja comparabilidad: {int(((cobertura_emp["n_sucursales"]>0)&(~cobertura_emp["comparable"])).sum())}')
    _frp = cobertura_frescos[(cobertura_frescos["n_cadenas"]<3)|(cobertura_frescos["n_provincias"]<10)]
    print(f'  Frescos con baja cobertura: {list(_frp["tipo"]) if len(_frp) else "ninguno"}')
    print(f'  Candidatos a REEMPLAZO: {len(alertas_reemplazo)}')
    if len(alertas_reemplazo):
        print(alertas_reemplazo[['descripcion','canastas','estado']].to_string(index=False))
except Exception as e:
    print('  (diagnostico no disponible:', e, ')')
print('\n' + '='*72)
print('FIN REPORTE')
print('='*72)
''' ))

# ── GENERAR EL NOTEBOOK ────────────────────────────────────────────────────────
nb = {'cells': cells,
      'metadata': {'kernelspec': {'display_name':'Python 3','language':'python','name':'python3'},
                   'language_info': {'name':'python'}},
      'nbformat': 4, 'nbformat_minor': 5}
_out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '07_evolucion_canastas_alternativas.ipynb')
with open(_out, 'w', encoding='utf-8') as _f:
    json.dump(nb, _f, ensure_ascii=False, indent=1)
print(f'Notebook generado: {_out}  ({len(cells)} celdas)')
