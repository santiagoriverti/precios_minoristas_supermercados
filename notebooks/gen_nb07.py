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
# Filtro de REGIMEN (frescos), previo al anterior y mucho mas importante. Un "tipo" fresco junta
# variantes que en realidad son bienes distintos: papa suelta ($2.100/kg) contra papa precocida al
# vacio; espinaca a granel ($2.171/kg) contra espinaca lavada y sanitizada en bolsa de 300 gr
# ($21.633/kg). Con dos regimenes de precio conviviendo, el filtro intra-sucursal FALLA de la peor
# forma: si la sucursal tiene {2.100, 15.000} la mediana da 8.550, la banda queda [3.420, 21.375] y
# descarta el precio CORRECTO conservando el caro. Que entre o salga una variante da vuelta la
# sucursal entera, y agregado sobre 1.900 sucursales sale una onda cuadrada (Papa: 2.318 -> 14.714
# -> 2.561 -> 14.855 entre mayo y julio de 2026, x6,8, que no es inflacion).
# Solucion: ANTES de tocar la sucursal, se calcula la referencia nacional del tipo para el MES
# completo (mediana sobre todas las observaciones del pais) y se descarta lo que quede fuera de
# [ref/K, ref*K]. La referencia se recalcula cada mes, asi que acompaña a la inflacion sola; y como
# se estima sobre millones de observaciones no se da vuelta porque una sucursal cambie el surtido.
# Tambien elimina errores de carga groseros (habia "Papa Negra Sc 1 Kg" a $95 en 983 sucursales).
FRESCO_REGIMEN_K = 3.0
# K de regimen POR TIPO (campo 'rk' en TIPOS_FRESCOS). El K global de 3,0 abre una ventana de 9x
# y no separa dos regimenes que difieren en ~2x. En la corrida 2026-08-27, 110 de los 243 saltos
# de item mayores a 35% tenian factor entre 1,5x y 2,5x: esa es la firma. El caso mas visible fue
# la semana 2026-05-07 (+5,4% en la canasta), donde SEIS cortes vacunos se movieron a la vez
# -Bife de chorizo +153,9%, Carre de cerdo +118,1%, Nalga/Cuadril +68,5%, Vacio +51,8%, Asado
# +50,3%, Suprema +39,8%- con el ancla de verduras plana, se quedaron seis semanas en el nivel
# alto y volvieron el 2026-06-18. No es un repricing: es que el tipo tiene un EAN barato de una
# cadena grande (Vacio 1 Kg a $8.490 en 983 sucursales) conviviendo con un grupo caro de ~91
# sucursales cada uno ($19.000-30.000), y la mediana nacional salta segun cual domine.
# Dentro de UN MES el mismo corte de carne no varia 2x, asi que ahi se puede exigir mas.
# Banda de PLAUSIBILIDAD, previa a todo lo demas. El filtro de regimen elige la moda
# MAYORITARIA de cada tipo, y eso falla cuando la moda mayoritaria es basura. Caso real
# (corrida 2026-08-27): una cadena de ~980 sucursales publica pan a $5, $40 y $70 el KILO;
# como son ~4.000 registros sucursal-EAN, el tipo "Pan frances" se fue a $550/kg contra
# $4.981 de la corrida anterior. Lo mismo con "Papa Negra Sc 1 Kg" a $95 en 983 sucursales.
# Ningun alimento fresco cuesta $40 el kilo: es un precio de relleno, no un precio.
#
# El umbral NO puede ser un numero absoluto (envejece con la inflacion), asi que se expresa
# relativo a un ANCLA calculada en la propia corrida: la mediana del precio por kilo de un
# conjunto de tipos bien medidos, abundantes y sin ambiguedad de presentacion. Todo lo que
# quede fuera de [ancla*PISO, ancla*TECHO] se descarta.
# Calibracion sobre 2026-08: ancla = $3.165/kg -> piso $633, techo $63.309. Se verifico que
# NINGUNA mediana de tipo legitimo cae fuera de esa banda (la mas barata es Mandarina a
# $1.327 y la mas cara Queso rallar a $39.735), y que adentro caen los 10 unicos EANs
# basura del universo de frescos.
ANCLA_FRESCOS = ['Papa', 'Cebolla', 'Zapallo', 'Zanahoria', 'Tomate', 'Banana', 'Manzana', 'Naranja']
FRESCO_PISO_ANCLA  = 0.2
FRESCO_TECHO_ANCLA = 20.0

# Banda de plausibilidad POR TIPO, sobre el precio nacional ya agregado.
# La banda global del read (FRESCO_PISO_ANCLA) usa un piso comun para todos los tipos y no
# alcanza cuando la basura de un tipo cae justo por ENCIMA de ese piso. Caso real de la corrida
# 2026-08-27: los registros invalidos de pan cotizan a $500-520 el kilo y el piso global quedaba
# en $480, asi que sobrevivian por un 4%. Cada vez que el ancla se movia un poco, el tipo entero
# cambiaba de regimen EN EL CAMBIO DE MES: el ratio pan/ancla quedaba clavado en 0,21 durante
# meses y saltaba a 2,07 de golpe. Como pan frances pesa 17,7 kg en la canasta, ese solo item
# explicaba el 43% de toda la volatilidad del indice (desvio semanal propio 69,7%).
#
# Solucion: cada tipo declara su precio ESPERADO relativo al ancla, y la semana cuyo precio
# nacional se sale de [ratio/K_BAJO, ratio*K_ALTO] se marca como FALTANTE. No se inventa un
# valor: el arrastre y el indice de muestra apareada ya saben tratar un item ausente.
# Se aplica DESPUES del cache (sobre el panel nacional), asi que tocar estos numeros NO obliga
# a releer el historico.
#
# La banda es ASIMETRICA a proposito: por abajo la contaminacion es de precios de relleno y hay
# que ser estricto; por arriba estan los picos estacionales genuinos (durazno, ciruela, uva) y
# el filtro de regimen ya controla la composicion dentro del mes. Con [/3, *5] se descartan
# 53 de 8.201 semanas-tipo (0,6%): 33 de pan frances, 11 de espinaca, 8 de limon, 1 de osobuco.
#
# CALIBRACION: percentil 75 de precio_tipo/ancla sobre las 139 semanas de la corrida
# 2026-08-27. Se usa q75 y no la mediana porque en un tipo contaminado la mediana cae ENTRE
# los dos regimenes (pan frances: mediana 1,14 con la basura en 0,2-0,6 y lo bueno en 1,8-2,8),
# y entonces el piso derivado de ella no separa nada. El q75 se apoya en el modo alto.
# Recalibrar cuando cambie la composicion de TIPOS_FRESCOS (ver METODOLOGIA 10.11).
FRESCO_RATIO_K_BAJO = 4.0
FRESCO_RATIO_K_ALTO = 5.0
RATIO_FRESCO = {
    'Acelga': 2.08,
    'Ajo': 1.39,
    'Ananá': 1.95,
    'Asado': 5.12,
    'Banana': 1.51,
    'Batata': 1.17,
    'Berenjena': 2.18,
    'Bife de chorizo': 6.95,
    'Bondiola': 8.08,
    'Brócoli': 3.87,
    'Carne picada': 5.63,
    'Carré de cerdo': 6.94,
    'Cebolla': 1.05,
    'Chaucha': 3.31,
    'Choclo': 2.87,
    'Ciruela': 3.45,
    'Durazno': 3.73,
    'Espinaca': 4.38,
    'Falda/Puchero': 3.95,
    'Frutilla': 6.92,
    'Huevos': 2.40,
    'Jamón cocido (kg)': 8.47,
    'Kiwi': 4.70,
    'Lechuga': 2.82,
    'Limón': 2.15,
    'Lomo': 9.25,
    'Mandarina': 1.07,
    'Manzana': 2.02,
    'Matambre': 5.07,
    'Merluza': 10.02,
    'Milanesa carne': 9.18,
    'Morrón': 3.44,
    'Mortadela': 5.72,
    'Nalga/Cuadril': 7.39,
    'Naranja': 1.33,
    'Osobuco': 4.77,
    'Paleta': 7.12,
    'Palta': 3.87,
    'Pan francés': 1.53,
    'Papa': 1.00,
    'Pechito/Costilla cerdo': 5.83,
    'Pepino': 1.77,
    'Pera': 1.61,
    'Pollo': 3.89,
    'Pomelo': 1.62,
    'Queso barra/Dambo': 13.20,
    'Queso cremoso': 7.73,
    'Queso rallar (sardo/reggianito)': 16.31,
    'Remolacha': 2.06,
    'Repollo': 1.72,
    'Roast beef': 5.04,
    'Salame/Salamín': 10.36,
    'Suprema/Pechuga': 9.53,
    'Tomate': 2.44,
    'Uva': 3.62,
    'Vacío': 7.46,
    'Zanahoria': 0.88,
    'Zapallito': 1.94,
    'Zapallo': 0.70,
}
# Piso PROPIO para los tipos donde la contaminacion no se separa con la regla general.
# Pan frances es el unico caso hasta ahora, y es flagrante: la serie es BIMODAL. Un cluster
# plano de ~55 de las 139 semanas entre $500 y $650 que NUNCA inflaciona (500, 510, 520, 608,
# 625... repetidos durante meses), y una serie legitima que si inflaciona: x2,66 entre 2024-01
# y 2026-08, en linea con el x2,86 del ancla. En ratio contra el ancla, la basura ocupa
# 0,20-0,59 y lo legitimo arranca en 0,73. El piso general (q75/4 = 0,38) dejaba pasar 28
# semanas de basura; 0,65 cae en el hueco entre los dos modos.
# Esto importa porque pan frances pesa 17,7 kg -la cantidad mas grande de la canasta, anclada
# a los 6.750 g/adulto equivalente de la CBA- y explicaba el 43% de la volatilidad del indice.
PISO_RATIO_OVERRIDE = {
    'Pan francés': 0.65,
}
# ── Frescos: indice NACIONAL encadenado por EAN (v5.7) ────────────────────────
# El precio nacional de un tipo fresco venia siendo la mediana sobre los EANs que casualmente
# cotizaban ese mes. Como la mezcla de EANs cambia, el tipo saltaba sin que hubiera inflacion, y
# la muestra apareada del indice no lo veia porque la etiqueta del item (`Lomo`) es la misma en
# ambas semanas. Medido en la corrida 2026-08-27: Presencia_items da 100% para los nueve tipos
# que saltan, en todos los meses -el tipo nunca falta, lo que cambia es que hay adentro-.
# Ninguna banda separa los dos regimenes de Lomo ($13.211 vs $36.378) ni de Bife de chorizo
# ($12.355 vs $31.349): distan ~2,5x y una ventana tiene que ser >=2x para tolerar dispersion
# legitima, asi que los dos caen adentro.
# Solucion: encadenar la MUESTRA APAREADA a nivel EAN, que es lo mismo que el notebook ya hace
# un nivel mas arriba para la canasta. Cada EAN se compara CONSIGO MISMO, asi que un cambio en la
# mezcla no puede mover el indice. El NIVEL se conserva del estimador actual (mediana provincial
# ponderada por poblacion) en la ultima semana valida, y la historia se reconstruye hacia atras.
FRESCO_NAC_ENCADENADO = True
FRESCO_EAN_MIN_SUC    = 10   # sucursales minimas de un EAN-semana para entrar en el encadenado
FRESCO_MIN_EANS_PAR   = 2    # EANs apareados minimos entre dos semanas para aceptar el eslabon
FRESCO_MAX_HUECO_PAR  = 8    # semanas maximas que puede saltear un eslabon para reenganchar
FRESCO_ESLABON_K      = 2.5  # tope de variacion de un EAN en un eslabon (clip, no descarte)
# Salto semanal del precio nacional de un item a partir del cual se lo reporta en la hoja
# Alertas_precio_item. Es el tripwire: ningun cambio de regimen deberia volver a pasar inadvertido.
ALERTA_SALTO_ITEM = 0.35
# Agregado nacional: 'poblacion' (ponderado por poblacion provincial) | 'mediana' (mediana simple)
AGG_NACIONAL = 'poblacion'
# Minimo de sucursales que una provincia necesita para un item-semana para entrar en el promedio
# nacional ponderado. Sin esto, provincias con 2-3 sucursales (Patagonia, NEA) meten su ruido de
# muestreo en la serie nacional con TODO su peso poblacional.
MIN_SUC_PROV_ITEM = 3
# Winsorizacion de las medianas provinciales contra la mediana entre provincias, antes de
# promediar. Descarta la provincia cuyo precio se va fuera de [med/K, med*K].
PROV_OUTLIER_K = 2.5
# Cobertura minima de items de la receta para que el indice de una canasta arranque. Evita
# publicar indice de una canasta que en esas fechas tenia 4 de 14 productos (caso Tecnologica 2024).
COBERTURA_MIN_INDICE = 0.80

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
    'Banana':      {'rubro':'Frutas','unidad':'kg','qty':(3.44, 3.1, 2.4, 3.14), 'inc':r'\bbanana', 'exc':r'licuad|yogur|snack|deshidr|chip|pasas|jugo|budin|helad|leche|postre'},
    'Manzana':     {'rubro':'Frutas','unidad':'kg','qty':(1.72, 2.58, 3, 2.62), 'inc':r'\bmanzana', 'exc':r'jugo|pur[eé]|vinagre|snack|licor|yogur|rall|deshidr|chip|desodor|t[eé] |gaseosa|sidra|gatorade|levite|aromat|torta|budin'},
    'Naranja':     {'rubro':'Frutas','unidad':'kg','qty':(2.58, 2.58, 2.4, 2.62), 'inc':r'\bnaranja', 'exc':r'jugo|gaseosa|aceite|esen|yogur|fanta|desodor|aromatiz|jab[oó]n|amarg|licor|tang|clight|pan de|\bpan\b|budin|torta|mermelada|dulce'},
    'Mandarina':   {'rubro':'Frutas','unidad':'kg','qty':(1.72, 1.55, 1.2, 1.57), 'inc':r'\bmandarina', 'exc':r'jugo|esen|gaseosa|licor'},
    'Limón':       {'rubro':'Frutas','unidad':'kg','qty':(0.43, 0.52, 0.84, 0.52), 'inc':r'\blim[oó]n|\blimones', 'exc':r'jugo|deterg|lavand|lavavaj|gaseosa|jab[oó]n|aceite|yogur|soda|amarg|aromatiz|desodor|hipoclor|limpiad|esen|tang|clight|t[eé]\b|pastilla|carame|crema|cera|pisos|helad|torta|budin|licor|vodka|\bpez\b|piedra|arena|gato|wondercat|pastel'},
    'Pera':        {'rubro':'Frutas','unidad':'kg','qty':(0.86, 1.55, 1.8, 1.57), 'inc':r'\bpera\b|\bperas\b', 'exc':r'jugo|campera|frapera|heladera|esen|almibar|lata|mitades|light'},
    'Frutilla':    {'rubro':'Frutas','unidad':'kg','qty':(0, 0.52, 1.44, 0.42), 'inc':r'\bfrutilla', 'exc':r'yogur|mermelada|dulce|helad|licor|gelatina|jugo|leche|postre|bomb|alfajor|chicle|carame|flan|congel|pulpa'},
    'Uva':         {'rubro':'Frutas','unidad':'kg','qty':(0, 0.72, 1.56, 0.52), 'inc':r'\buva\b|\buvas\b', 'exc':r'jugo|vino|pasa|vinagre|mermelada|licor|aceite|semilla|sidra|espum'},
    'Durazno':     {'rubro':'Frutas','unidad':'kg','qty':(0.26, 0.83, 1.2, 0.73), 'inc':r'\bdurazno', 'exc':r'lata|\blat\b|almibar|mermelada|jugo|conserva|yogur|dulce|licor|gaseosa|vodka|seco|desecad|mitades|light|calor|pulpa|helad'},
    'Ciruela':     {'rubro':'Frutas','unidad':'kg','qty':(0, 0.52, 0.96, 0.42), 'inc':r'\bciruela', 'exc':r'seca|desecad|descaroz|sin carozo|pasa|mermelada|jugo|dulce|licor|nature food|tiernizad'},
    'Kiwi':        {'rubro':'Frutas','unidad':'kg','qty':(0, 0.31, 0.96, 0.21), 'inc':r'\bkiwi', 'exc':r'jugo|yogur|licuad|helad|gelatina|pulpa'},
    'Palta':       {'rubro':'Frutas','unidad':'kg','qty':(0, 0.41, 1.44, 0.31), 'inc':r'\bpalta', 'exc':r'aceite|guacamole|crema|jab[oó]n|shampoo|acondic|pulpa|congel|mascar'},
    'Pomelo':      {'rubro':'Frutas','unidad':'kg','qty':(0, 0.41, 0.72, 0.31), 'inc':r'\bpomelo', 'exc':r'jugo|gaseosa|agua|amarg|licor|esen|clight|tang|difusor|repuesto|spirit|aromat|desodor'},
    'Ananá':       {'rubro':'Frutas','unidad':'kg','qty':(0, 0.41, 1.08, 0.31), 'inc':r'\banan[aá]|\bpi[ñn]a\b', 'exc':r'jugo|lata|\blat\b|almibar|rodaja|yogur|helad|colada|licor|gaseosa|fizz|clight|tang|pulpa|mitades'},
    # ---- VERDURAS ($/kg) ----
    'Papa':        {'rubro':'Verduras','unidad':'kg','qty':(22, 18, 14, 20.12), 'gmin':1000, 'inc':r'\bpapa\b|\bpapas\b', 'exc':r'frita|snack|pur[eé]|congel|chip|bast[oó]n|noisett|prefrit|rall|española|jarro|espatul|mugg|taza|tortilla'},
    'Tomate':      {'rubro':'Verduras','unidad':'kg','qty':(2.47, 3.18, 3.41, 3.24), 'inc':r'\btomate', 'exc':r'salsa|pur[eé]|\btrit|extracto|lata|\blat\b|pelado|jugo|ketchup|seco|deshidr|conserva|cubo|cherry|cereza|at[uú]n|sardina|caballa|sabores del|entero|perita lat|prepizza|pizza|tarta|sandwich'},
    'Cebolla':     {'rubro':'Verduras','unidad':'kg','qty':(2.96, 2.65, 2.27, 2.7), 'inc':r'\bcebolla', 'exc':r'sopa|deshidr|crema|anillo|snack|verdeo|caldo|ciriola|cintita|queso|frita|\bpan\b|salsa|encurt|vinagre|pretzel|picada|rocky|galleta|snack'},
    'Zanahoria':   {'rubro':'Verduras','unidad':'kg','qty':(1.97, 2.12, 2.04, 2.16), 'inc':r'\bzanahoria', 'exc':r'rall|congel|sopa|deshidr|bab[yi]|jugo|torta|budin|beb[eé]'},
    'Zapallo':     {'rubro':'Verduras','unidad':'kg','qty':(2.47, 2.12, 1.7, 2.16), 'inc':r'\bzapallo\b|\bcalabaza', 'exc':r'congel|sopa|semilla|deshidr|crema|zapallito|dulce|cayote|pur[eé]|precocid'},
    'Lechuga':     {'rubro':'Verduras','unidad':'kg','qty':(0.99, 1.38, 1.82, 1.4), 'gmin':1000, 'inc':r'\blechuga', 'exc':r'aderez|snack|\bmix\b|ensalada'},
    'Morrón':      {'rubro':'Verduras','unidad':'kg','qty':(0.39, 0.85, 1.48, 0.76), 'inc':r'\bmorr[oó]n|\bmorrones|\bpimiento', 'exc':r'molid|deshidr|conserva|lata|\blat\b|seco|piment[oó]n|aji molido|frasco|relleno|jalape|salsa|encurt'},
    'Batata':      {'rubro':'Verduras','unidad':'kg','qty':(1.5, 1.5, 1.5, 1.58), 'inc':r'\bbatata', 'exc':r'dulce|congel|snack|chip|pur[eé]|frita'},
    'Acelga':      {'rubro':'Verduras','unidad':'kg','qty':(0.79, 0.85, 0.68, 0.86), 'inc':r'\bacelga', 'exc':r'congel|\bcong\b|tarta|empanada|ravio|canel|ñoqui|noqui|milanesa|ensalada|lavad|sanitiz|listo para|buy y eat|taeq|huella natural|sue[ñn]o verde|green life|quinta onda|hidropon|bandeja'},
    'Espinaca':    {'rubro':'Verduras','unidad':'kg','qty':(0.2, 0.53, 1.02, 0.43), 'inc':r'\bespinaca', 'exc':r'congel|\bcong\b|tarta|empanada|nuez|ravio|canel|fideo|ñoqui|noqui|muslito|\bmix\b|mixta|milanesa|soja|vegan|queso|sorrent|pasta|medall|pollo|bandeja mixta|ensalada|malfatti|baby|hidropon|rocky|lavad|sanitiz|listo para|buy y eat|taeq|huella natural|sue[ñn]o verde|green life|quinta onda|bandeja'},
    'Choclo':      {'rubro':'Verduras','unidad':'kg','qty':(0.49, 0.64, 0.79, 0.65), 'inc':r'\bchoclo', 'exc':r'lata|\blat\b|crema|cremos|congel|conserva|granos|desgran|arcor|campagnola|humita|pochoclo|snack|grm|entero|relleno|tarta|calab'},
    'Brócoli':     {'rubro':'Verduras','unidad':'kg','qty':(0, 0.42, 1.14, 0.32), 'inc':r'\bbrocoli|\bbrócoli', 'exc':r'congel|tarta|medall|rebozad|merluza|milanesa|pasta'},
    'Ajo':         {'rubro':'Verduras','unidad':'kg','qty':(0.2, 0.21, 0.34, 0.22), 'inc':r'\bajo\b|\bajos\b', 'exc':r'aceite|\bsal\b|deshidr|polvo|molid|sazonad|condiment|\bpan\b|aderez|mayonesa|crema|conserva|\baji|salsa|manteca|queso|pasta|encurt'},
    'Zapallito':   {'rubro':'Verduras','unidad':'kg','qty':(0.79, 0.85, 0.91, 0.86), 'inc':r'\bzapallito|\bzucchini|\bzuc+hini', 'exc':r'congel|relleno|tarta|milanesa'},
    'Berenjena':   {'rubro':'Verduras','unidad':'kg','qty':(0, 0.53, 1.02, 0.43), 'inc':r'\bberenjena', 'exc':r'escabeche|conserva|frasco|lata|milanesa|congel|encurt'},
    'Repollo':     {'rubro':'Verduras','unidad':'kg','qty':(0.79, 0.53, 0.45, 0.54), 'inc':r'\brepollo', 'exc':r'congel|chucrut|conserva|bruselas|encurt'},
    'Chaucha':     {'rubro':'Verduras','unidad':'kg','qty':(0.2, 0.42, 0.68, 0.32), 'inc':r'\bchaucha', 'exc':r'congel|lata|\blat\b|conserva'},
    'Remolacha':   {'rubro':'Verduras','unidad':'kg','qty':(0.3, 0.42, 0.57, 0.43), 'inc':r'\bremolacha', 'exc':r'lata|\blat\b|conserva|jugo|congel|ensalada|precocid|cortada'},
    'Pepino':      {'rubro':'Verduras','unidad':'kg','qty':(0, 0.32, 0.68, 0.22), 'inc':r'\bpepino', 'exc':r'encurt|pickle|conserva|frasco|vinagre|jab[oó]n|crema|mascar|gel'},
    # ---- CARNE VACUNA ($/kg) ----
    'Asado':       {'rubro':'Carne','unidad':'kg','qty':(2.05, 2.22, 2.34, 2.13), 'rk':2.0, 'inc':r'\basado\b|\bcostillar|tira de asado', 'exc':r'salsa|adob|aderez|sabor asado|hellmann|snack|man[ií]|pollo|caf[eé]|cuchill|\bset\b|carbon|carb[oó]n|palit|asador|pizza|cerdo|chancho|cordero|congel'},
    'Carne picada':{'rubro':'Carne','unidad':'kg','qty':(3.07, 2.44, 1.6, 2.66), 'rk':2.0, 'inc':r'\bpicada\b|carne molida', 'exc':r'salch|congel|caldo|pat[eé]|hamburg|pollo|pescado|aceituna|verdura|angus|wagyu|kobe|premium|cerdo|mixta|frutos|mani|man[ií]|tartare|tartar'},
    'Nalga/Cuadril':{'rubro':'Carne','unidad':'kg','qty':(0.82, 1.67, 2.34, 1.6), 'rk':2.0, 'inc':r'\bnalga|\bcuadril|bola de lomo|\bcuadrada\b|\bpeceto|colita de cuadril', 'exc':r'mantel|cuadrill|cerdo|pollo|milanesa|congel|cordero'},
    'Milanesa carne':{'rubro':'Carne','unidad':'kg','qty':(1.02, 1.33, 1.28, 1.28), 'rk':2.0, 'inc':r'milanesa', 'exc':r'soja|pollo|congel|merluza|pescado|napolitan|vegetal|cerdo|berenjena|rebozad|granja|swift|paty|listas|carr[eé]|calabaza|zapallo|espinaca|acelga|arroz|quinoa|lenteja|garbanzo'},
    'Matambre':    {'rubro':'Carne','unidad':'kg','qty':(0.2, 0.56, 0.96, 0.43), 'rk':2.0, 'inc':r'\bmatambre', 'exc':r'arrollado|relleno|queso|pizza|a la|cocido|cerdo|congel'},
    'Vacío':       {'rubro':'Carne','unidad':'kg','qty':(0.2, 0.67, 1.17, 0.53), 'rk':2.0, 'inc':r'\bvac[ií]o\b', 'exc':r'al vac[ií]o|\(vac|envasad|arrollado|relleno|envase|frasco|cerdo|pollo|medialuna|queso|jam[oó]n|fiambre|salame|bondiola|congel|cordero|pescado|merluza|salm[oó]n|chistorra|chorizo|morcilla|salchich|guanaco'},
    'Osobuco':     {'rubro':'Carne','unidad':'kg','qty':(1.02, 0.56, 0.21, 0.64), 'rk':2.0, 'inc':r'\bosobuco|\bosso\s*buco', 'exc':r'congel'},
    'Roast beef':  {'rubro':'Carne','unidad':'kg','qty':(0.31, 0.67, 0.96, 0.53), 'rk':2.0, 'inc':r'roast\s*beef|tapa de nalga|tapa de cuadril', 'exc':r'congel|fiambre|feteado'},
    'Bife de chorizo':{'rubro':'Carne','unidad':'kg','qty':(0, 0.67, 1.7, 0.53), 'rk':2.0, 'inc':r'bife de chorizo|bife ancho|bife angosto|\bbife\b', 'exc':r'chorizo parril|cerdo|pollo|milanesa|snack|palit|t-bone|tbone|ojo de bife|tomahawk|congel|cordero|wagyu|kobe|angus'},
    'Lomo':        {'rubro':'Carne','unidad':'kg','qty':(0, 0.22, 1.28, 0.21), 'rk':2.0, 'inc':r'\blomo\b', 'exc':r'bola de lomo|cerdo|atun|at[uú]n|pollo|lomito|jam[oó]n|ahumad|pizza|s[aá]ndwich|sandwich|congel|cabecero|medall|wagyu|kobe|angus|praga|feteado|cinta|costilla|guanaco'},
    'Paleta':      {'rubro':'Carne','unidad':'kg','qty':(1.53, 0.89, 0.43, 1.06), 'rk':2.0, 'inc':r'\bpaleta\b', 'exc':r'cerdo|cocida|jam[oó]n|fiambre|helad|paletita|pintur|rodillo|ping|pong|tenis|playa|espatula|cordero|congel|guanaco'},
    'Falda/Puchero':{'rubro':'Carne','unidad':'kg','qty':(1.84, 0.89, 0.32, 1.06), 'rk':2.0, 'inc':r'\bfalda\b|\bpuchero|\bcaracu|\bazotillo', 'exc':r'cerdo|pollo|congel|mixto|cordero'},
    # ---- POLLO ($/kg) ----
    'Pollo':       {'rubro':'Pollo','unidad':'kg','qty':(4.09, 3.56, 2.66, 3.73), 'rk':2.0, 'inc':r'\bpollo\b|pata muslo', 'exc':r'caldo|sopa|saboriz|congel|nugget|pat[eé]|medall|hamburg|milanesa|pella|arroz|fideo|snack|cubito|aliment|merluza|pescado|pechuga|suprema|\bfilet|fajita|deshuesad|campero|colonial|org[aá]nic|kosher|criado|sandwich|s[aá]ndwich|empanada|tarta|salch|picada|croqueta|bocadit|rebozad|\bmax\b|triangulo|relleno|arrollado|taco|wrap|ensalada|pizza|salsa|al vac[ií]o|ahumad|grill|listo|rostiz|precoc|\bmed\b|\bjam|patita|\bseco\b|cuarto|cocido|hervid'},
    'Suprema/Pechuga':{'rubro':'Pollo','unidad':'kg','qty':(0.51, 1.33, 2.13, 1.06), 'rk':2.0, 'inc':r'\bpechuga|\bsuprema', 'exc':r'congel|milanesa|rebozad|nugget|medall|hamburg|sandwich|s[aá]ndwich|pavo|cerdo|salsa|empanad|grill|listas|granja del sol|swift|paty|\bmax\b|merluza|pescado|verdeo|ahumad|fiambre|feteado|al vac[ií]o'},
    # ---- CERDO ($/kg) ----
    'Bondiola':    {'rubro':'Cerdo','unidad':'kg','qty':(0.2, 0.56, 1.06, 0.43), 'rk':2.0, 'inc':r'\bbondiola', 'exc':r'ahumad|curad|fiambre|feteado|sandwich|s[aá]ndwich|costeletero|sin bondiola|congel|finas hierbas|adobad|marinad|saboriz|al vac[ií]o|piamontesa|lario|cagnoli|paladini'},
    'Pechito/Costilla cerdo':{'rubro':'Cerdo','unidad':'kg','qty':(0.51, 0.67, 0.85, 0.64), 'rk':2.0, 'inc':r'pechito|costilla.*cerdo|cerdo.*costilla|costeleta.*cerdo|cerdo.*costeleta|\bribs\b', 'exc':r'ahumad|congel|cong\b|salsa|bbq|sandwich|kosher|aus\b'},
    # BUG CORREGIDO (corrida 2026-08-27): el patron anterior era
    #   carr[eé].*cerdo|cerdo.*carr[eé]|\bcarr[eé]\b
    # y 'cerdo.*carr[eé]' matchea "Chorizo Puro Cerdo Bombon CARREfour": el fragmento 'carre' de
    # Carrefour no tenia limite de palabra. Entraban 4 productos con 418 sucursales-EAN, entre
    # ellos un snack para perros de orejas de cerdo. Como Carre de cerdo solo tiene 4 candidatos
    # legitimos, esos chorizos lo dominaban y el tipo oscilaba entre $15.951 y $30.848 en semanas
    # consecutivas (factor 1,93). Ahora 'carre' exige limite de palabra en las tres alternativas.
    'Carré de cerdo':{'rubro':'Cerdo','unidad':'kg','qty':(0.2, 0.44, 0.64, 0.32), 'rk':2.0, 'inc':r'\bcarr[eé]\b.*cerdo|cerdo.*\bcarr[eé]\b|\bcarr[eé]\b', 'exc':r'ahumad|fiambre|feteado|curad|jam[oó]n|congel|cong\b|aus\b|milanesa|chorizo|carrefour|snack|perro|mascota'},
    # ---- PESCADO ($/kg) ----
    'Merluza':     {'rubro':'Pescado','unidad':'kg','qty':(0.41, 0.67, 1.06, 0.53), 'inc':r'\bmerluza', 'exc':r'bast[oó]n|reboz|medall|milanesa|congel|aceite|lata|conserva|croqueta|nugget|granja del sol|swift|hamburg|empanad|romana|formita|queso|negra|relleno|ahumad|pat[eé]'},
    # ---- FIAMBRES Y QUESOS por kg (balanza) ----
    'Queso cremoso':{'rubro':'Fiambres y Quesos','unidad':'kg','qty':(0.49, 0.69, 0.72, 0.33), 'gmin':500, 'inc':r'queso.*cremoso|cremoso.*queso|\bcremon\b', 'exc':r'untable|rallad|feta|light|sandwich|s[aá]ndwich|pizza|congel|barra|vegan|descremad'},
    'Queso barra/Dambo':{'rubro':'Fiambres y Quesos','unidad':'kg','qty':(0.21, 0.46, 0.72, 0.22), 'gmin':500, 'inc':r'queso.*(barra|dambo|tybo|pategr[aá]s|holanda|fymbo)|\bdambo\b|\btybo\b', 'exc':r'untable|rallad|feta|sandwich|s[aá]ndwich|pizza|congel|light|vegan'},
    'Queso rallar (sardo/reggianito)':{'rubro':'Fiambres y Quesos','unidad':'kg','qty':(0.08, 0.29, 0.65, 0.11), 'gmin':500, 'inc':r'queso.*(sardo|reggian|parmes|romano)|\bsardo\b|\breggianito', 'exc':r'rallado|feta|untable|sandwich|pizza|congel|provolet|provol|vegan'},
    'Jamón cocido (kg)':{'rubro':'Fiambres y Quesos','unidad':'kg','qty':(0.33, 0.58, 0.86, 0.27), 'gmin':500, 'inc':r'jam[oó]n cocido|jamon cocido', 'exc':r'feteado|fetas|sandwich|s[aá]ndwich|pizza|empanad|tarta|light|caja|blister|pavita|pavo'},
    'Salame/Salamín':{'rubro':'Fiambres y Quesos','unidad':'kg','qty':(0.08, 0.29, 0.72, 0.11), 'gmin':500, 'inc':r'\bsalame|\bsalamin|\bsalam[ií]n', 'exc':r'feteado|fetas|sandwich|pizza|snack|palito|cabana|picada|tabla'},
    'Mortadela':   {'rubro':'Fiambres y Quesos','unidad':'kg','qty':(0.41, 0.29, 0.14, 0.16), 'gmin':500, 'inc':r'\bmortadela', 'exc':r'feteado|fetas|sandwich|pizza|piccola|familiar'},
    # ---- PANADERIA ($/kg) ----
    'Pan francés':{'rubro':'Panadería','unidad':'kg','qty':(18, 15, 11, 17.73), 'inc':r'pan franc[eé]s|\bflauta|\bmignon|\bfelipe|pan.*(criollo|casero)|\bpan\b.*(tira|\bkg)', 'exc':r'lactal|mesa|dulce|integral|salvado|hamburg|pancho|pebete|hot dog|rallado|congel|tostad|arabe|pita|molde|viena|chip|budin|prepizza|pizza|galleta|semilla|centeno|negro|queso|chocolate|rosca|figaza|panettone|fideo|don felipe|naranja|an[ií]s|cuernito|manteca|grasa|chicharr|salvado|semilla|sin tacc|libre de gluten|campero|precocid'},
    # ---- HUEVOS ($/docena) ----
    'Huevos':      {'rubro':'Huevos','unidad':'doc','qty':(3, 3, 3, 2.58), 'inc':r'\bhuevo', 'exc':r'chocolate|kinder|pascua|sorpresa|codorniz|conejo|batidora|fideo|pasta|ravio|tallar|mayonesa|pintur|colorante|separador|huevera|salsa|tarta|galletit|ensalada|revuelt|omelet|budin|torta|liquido|l[ií]quido|polvo|clara|rainb|albu|\d+\s*cm|globo|pi[ñn]ata|decor|juguete|plastic'},
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
_FECHAS_MAX = []   # ultima fecha con precio leida (para detectar la semana incompleta del final)
# La clave tiene que cubrir TODO lo que cambia el resultado de la lectura. Faltaban dos cosas:
# (a) los `rk` por tipo, que filtran en la lectura desde v5.6; y (b) RATIO_FRESCO, que desde v5.7
# dejo de ser solo una banda post-cache y es la REFERENCIA del filtro de regimen. Sin esto, tocar
# un rk o un ratio no movia la clave y el notebook reusaba en silencio un cache construido con los
# valores viejos: resultado incorrecto y sin aviso. (Esta vez quedaba tapado porque el universo de
# EANs cambiaba igual, pero es una trampa para la proxima sesion.)
_rk_sig    = '|'.join(f'{t}:{TIPOS_FRESCOS[t]["rk"]}' for t in sorted(TIPOS_FRESCOS) if 'rk' in TIPOS_FRESCOS[t])
_ratio_sig = '|'.join(f'{t}:{RATIO_FRESCO[t]}' for t in sorted(RATIO_FRESCO))
_cache_key  = hashlib.md5(('|'.join(sorted(EANS_LECTURA)) + f'|w{DIA_CIERRE_SEMANA}|k{FRESCO_OUTLIER_K}'
                           f'|r{FRESCO_REGIMEN_K}|p{FRESCO_PISO_ANCLA}|t{FRESCO_TECHO_ANCLA}'
                           f'|refmode=ancla_x_ratio|rk={_rk_sig}|ratio={_ratio_sig}'
                           ).encode()).hexdigest()[:8]
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
                _FECHAS_MAX.append(_mlt['fecha'].max())
                _rows.append(_mlt.groupby(_SKR+['ean_norm','semana'], as_index=False)['precio'].median())
        _tmp_p.unlink(missing_ok=True)
    if not _rows: return None
    _df = pd.concat(_rows, ignore_index=True)
    # Autodeteccion centavos/pesos por mes (pre-2025 vienen en centavos). Se mide SOLO sobre los
    # EANs EMPAQUETADOS: su nivel de precio es estable y conocido (~$1.000-20.000). Usar todo el
    # universo seria fragil, porque los ~10.500 frescos de balanza cotizan por kilo y arrastran
    # la mediana cerca del umbral (un falso positivo divide el mes entero por 100).
    _ref = _df.loc[_df['ean_norm'].isin(EANS_EMP), 'precio']
    _med_ref = _ref.median() if len(_ref) >= 50 else _df['precio'].median()
    if _med_ref > 10_000: _df['precio'] /= 100
    return _df.groupby(_SKR+['ean_norm','semana'], as_index=False)['precio'].median()

_FR_MULT = {t: (1000.0 if FRESCO_INFO[t]['unidad'] == 'kg' else 12.0) for t in FRESCO_INFO}
_RK_TIPO = {t: float(TIPOS_FRESCOS[t]['rk']) for t in FRESCO_INFO if 'rk' in TIPOS_FRESCOS.get(t, {})}
_FR_DESCARTES = []   # (mes, observaciones fuera de la banda de plausibilidad, ancla $/kg)
_EAN_NAC = []        # agregado nacional por (tipo, EAN, semana): insumo del encadenado de frescos
def _colapsar(_df, _lbl_mes=''):
    if _df is None or len(_df) == 0: return None
    _e = (_df[_df['ean_norm'].isin(EANS_EMP)][_SKR + ['semana','ean_norm','precio']]
          .rename(columns={'ean_norm':'item','precio':'price'}))
    # OJO CON LA RAM: cada `_f = _f[mascara]` copia el panel ENTERO de frescos del mes, que
    # son decenas de millones de filas con varias columnas de texto. La version anterior hacia
    # cinco copias encadenadas y reventaba la sesion de Colab en instancias chicas. Aca se
    # reduce a las imprescindibles y se sueltan los temporales enseguida. El RESULTADO es
    # identico (verificado con un test de identidad), asi que el cache sigue siendo valido.
    _msk = _df['ean_norm'].isin(EANS_FRESCOS)
    if bool(_msk.any()):
        _f = _df.loc[_msk, _SKR + ['semana','ean_norm','precio']].copy()
        _f['item']  = _f['ean_norm'].map(EAN_TIPO)
        _f['price'] = _f['precio'] / _f['ean_norm'].map(EAN_NORMFACTOR) * _f['item'].map(_FR_MULT)
        # ean_norm y precio ya no se usan: sacarlos ahora evita arrastrar una columna de texto
        # en cada copia posterior.
        _f = _f.drop(columns=['precio'])
        _ok = _f['price'].notna() & (_f['price'] > 0)
        # (0) banda de PLAUSIBILIDAD anclada, acumulada sobre la MISMA mascara que el notna para
        #     no materializar una copia intermedia. Va antes que todo: si la moda mayoritaria de
        #     un tipo es basura (pan a $40 el kilo en 980 sucursales), el filtro de regimen la
        #     elegiria como referencia. El ancla se recalcula cada mes, asi que la banda
        #     acompana a la inflacion sin umbrales absolutos.
        _anc = _f.loc[_ok & _f['item'].isin(ANCLA_FRESCOS), 'price'].median()
        if _anc == _anc and _anc > 0:
            _n0 = int(_ok.sum())
            _ok &= (_f['price'] >= _anc * FRESCO_PISO_ANCLA) & (_f['price'] <= _anc * FRESCO_TECHO_ANCLA)
            _FR_DESCARTES.append((_lbl_mes, _n0 - int(_ok.sum()), round(float(_anc), 1)))
        _f = _f[_ok]
        del _ok
        # (0b) AGREGADO NACIONAL POR EAN, insumo del indice encadenado de frescos (v5.7).
        #      Se toma ACA, antes del filtro de regimen, porque el encadenado no necesita que
        #      se elija un regimen: compara cada EAN CONSIGO MISMO, asi que un cambio en la
        #      mezcla de EANs no puede mover el indice. Es la unica forma de arreglar Lomo y
        #      Bife de chorizo, cuyos dos regimenes distan ~2,5x y caen los dos dentro de
        #      cualquier ventana lo bastante ancha como para tolerar dispersion legitima.
        #      Barato: el groupby es POR MES (~2 M de filas), no sobre el panel completo, y el
        #      resultado son ~10k EANs x 4-5 semanas. El OOM de v5.4 fue por sostener el panel
        #      entero mas copias, no por una agregacion mensual.
        #      `size()` = cantidad de sucursales porque `_leer_mes` ya devuelve una fila por
        #      (sucursal, ean, semana).
        try:
            _en = _f.groupby(['item','ean_norm','semana'], as_index=False).agg(
                p=('price','median'), n_suc=('price','size'))
            _EAN_NAC.append(_en)
            del _en
        except Exception as _e:
            print(f'AVISO: no se pudo agregar el panel por EAN en {_lbl_mes}: {_e}')
        _f = _f.drop(columns=['ean_norm'])
        # (1) filtro de REGIMEN. La referencia NO puede ser la mediana del mes: esa mediana la
        #     fija la mezcla de EANs que casualmente cotiza ese mes, y cuando la mezcla cambia
        #     en el corte de mes la referencia aterriza en el otro regimen y el filtro descarta
        #     el regimen anterior ENTERO. Es autoreforzante. Caso medido (corrida 2026-08-27):
        #     Carre de cerdo paso de $11.725 a $40.000 REDONDOS y plano cuatro semanas seguidas
        #     -un EAN unico dominando- y volvio a $15.080 recien en junio; Lomo x2,75; Bife de
        #     chorizo x2,54; Suprema +40%. Los seis a la vez, con el ancla de verduras plana:
        #     eso es el salto de la semana 2026-05-07 (+4,07% en la canasta).
        #     Bajar el K de 3,0 a 2,0 lo EMPEORO, porque estrechar la ventana alrededor de una
        #     referencia contaminada compromete mas con el regimen equivocado: los tres tipos
        #     mas volatiles de 2026 fueron los tres con rk=2,0 (desvio medio 10,3% contra 8,5%
        #     de los tipos sin rk).
        #     Referencia estable: `ancla del mes x RATIO_FRESCO[tipo]`. RATIO_FRESCO ya esta
        #     calibrado (q75 del ratio contra el ancla) y el ancla se recalcula cada mes, asi
        #     que la referencia acompana a la inflacion sin depender de la composicion. Con eso
        #     el conjunto aceptado deja de darse vuelta mes a mes, que es lo que genera el
        #     salto: la volatilidad viene de ALTERNAR entre regimenes, no de mezclarlos.
        #     Fallback a la mediana del mes para un tipo sin ratio calibrado o si no hay ancla.
        _ref_med = _f['item'].map(_f.groupby('item')['price'].median())
        if _anc == _anc and _anc > 0:
            _ref = _f['item'].map(RATIO_FRESCO) * float(_anc)
            _ref = _ref.where(_ref.notna() & (_ref > 0), _ref_med)
        else:
            _ref = _ref_med
        del _ref_med
        _kreg = _f['item'].map(_RK_TIPO).fillna(FRESCO_REGIMEN_K)
        _f = _f[(_f['price'] >= _ref / _kreg) & (_f['price'] <= _ref * _kreg)]
        del _ref
        # (2) filtro de outliers intra-tipo dentro de cada sucursal-semana (segunda linea)
        _med = _f.groupby(_SKR + ['semana','item'])['price'].transform('median')
        _f = _f[(_f['price'] >= _med / FRESCO_OUTLIER_K) & (_f['price'] <= _med * FRESCO_OUTLIER_K)]
        del _med
        _fv = _f.groupby(_SKR + ['semana','item'], as_index=False)['price'].median()
        del _f
    else:
        _fv = pd.DataFrame(columns=_SKR + ['semana','item','price'])
    del _msk
    _out = pd.concat([_e[_SKR + ['semana','item','price']], _fv], ignore_index=True)
    del _e, _fv
    gc.collect()
    return _out

if USE_CACHE and _cache_path.exists():
    _cache = pd.read_parquet(_cache_path)
    _cache = _cache[_cache['semana'].map(_mes_de_semana) < _mes_actual].copy()
    gc.collect()
else:
    _cache = pd.DataFrame(columns=_SKR + ['semana','item','price'])
_en_cache = set(_cache['semana'].map(_mes_de_semana).unique()) if len(_cache) else set()
_faltantes = [m for m in _meses_disp if m < _mes_actual and m not in _en_cache]
_nuevos = []
for _lbl in tqdm(_faltantes, desc='Meses cerrados'):
    _dc = _colapsar(_leer_mes(_lbl), _lbl)
    if _dc is not None: _nuevos.append(_dc)
    gc.collect()
if _nuevos:
    _cache = pd.concat([_cache] + _nuevos, ignore_index=True)
    if USE_CACHE:
        _cache.to_parquet(_cache_path, compression='snappy', index=False)
        print(f'Cache actualizado: {_cache_path.name}')
del _nuevos; gc.collect()

# Cache PARALELO por EAN (mismo key: describe la misma lectura). Es chico -del orden de 10k EANs
# x 139 semanas- y es lo que permite iterar la metodologia de frescos SIN releer el SEPA: todo el
# encadenado se calcula despues del cache.
_ean_cache_path = CACHE_DIR / f'ean_{_cache_key}_v5.parquet'
if USE_CACHE and _ean_cache_path.exists():
    _ean_cerrados = pd.read_parquet(_ean_cache_path)
    _ean_cerrados = _ean_cerrados[_ean_cerrados['semana'].map(_mes_de_semana) < _mes_actual].copy()
else:
    _ean_cerrados = pd.DataFrame(columns=['item','ean_norm','semana','p','n_suc'])
if _EAN_NAC:   # meses cerrados que se acaban de leer
    _ean_cerrados = pd.concat([_ean_cerrados] + _EAN_NAC, ignore_index=True)
    if USE_CACHE:
        _ean_cerrados.to_parquet(_ean_cache_path, compression='snappy', index=False)
        print(f'Cache por EAN actualizado: {_ean_cache_path.name} ({len(_ean_cerrados):,} filas)')
_EAN_NAC.clear(); gc.collect()

# Mes en curso: siempre fresco. Guardamos el crudo por-EAN para los diagnosticos.
# `_leer_mes` ya devuelve un frame nuevo (sale de un groupby), asi que el .copy() que habia aca
# duplicaba el mes entero sin motivo. En una instancia chica de Colab eso era la gota.
datos_ult_raw = _leer_mes(_mes_actual)
if datos_ult_raw is not None:
    datos_ult_raw['mes'] = _mes_actual
_actual = _colapsar(datos_ult_raw)
# El concat sostiene entrada y salida a la vez: soltar los nombres ANTES deja que pandas libere
# cada parte apenas la copia, en vez de mantener dos paneles completos hasta el final.
_partes = [_cache] + ([_actual] if _actual is not None else [])
del _cache, _actual; gc.collect()
datos_sem = pd.concat(_partes, ignore_index=True)
_partes.clear(); del _partes; gc.collect()
if len(datos_sem) == 0:
    raise RuntimeError('Sin datos para los EANs configurados. Revisa las canastas y los frescos.')
datos_sem = datos_sem.groupby(_SKR + ['item','semana'], as_index=False)['price'].median()
datos_sem['mes'] = datos_sem['semana'].map(_mes_de_semana)

# Panel nacional por EAN = meses cerrados (cache) + mes en curso (recien leido).
ean_nac = pd.concat([_ean_cerrados] + _EAN_NAC, ignore_index=True) if len(_EAN_NAC) else _ean_cerrados
del _ean_cerrados; _EAN_NAC.clear(); gc.collect()
if len(ean_nac):
    ean_nac = ean_nac.astype({'p': 'float64', 'n_suc': 'int64'})
    ean_nac = ean_nac.groupby(['item','ean_norm','semana'], as_index=False).agg(
        p=('p','median'), n_suc=('n_suc','sum'))
    print(f'Panel por EAN (frescos): {ean_nac["ean_norm"].nunique():,} EANs x '
          f'{ean_nac["semana"].nunique()} semanas | {len(ean_nac):,} filas')
else:
    # No deberia pasar en una corrida normal. Si pasa, el encadenado se saltea solo (esta
    # guardado por `len(ean_nac)`) y el nacional queda con el estimador anterior, en vez de
    # que reviente un groupby sobre un frame vacio a la hora y media de lectura.
    print('AVISO: panel por EAN vacio -> los frescos quedan con el estimador anterior')
datos_sem = datos_sem[datos_sem['mes'] >= MES_INICIO_HISTORICO].copy()

# La ULTIMA semana solo vale si esta COMPLETA: su jueves de cierre tiene que estar cubierto por
# los datos. Si el SEPA llega, por ejemplo, hasta el 31/08 y la semana cierra el 03/09, esa semana
# tiene 4 de 7 dias y no se puede publicar como si estuviera cerrada.
FECHA_MAX_DATOS = max(_FECHAS_MAX).date() if _FECHAS_MAX else None
_SEMANAS = sorted(datos_sem['semana'].unique())
if FECHA_MAX_DATOS is not None:
    _incompletas = [w for w in _SEMANAS if _dt.date.fromisoformat(w) > FECHA_MAX_DATOS]
    if _incompletas:
        print(f'Ultimo dato del SEPA: {FECHA_MAX_DATOS}. Semanas INCOMPLETAS descartadas: {_incompletas}')
        datos_sem = datos_sem[~datos_sem['semana'].isin(_incompletas)].copy()
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
# Mediana simple entre sucursales: sirve de respaldo cuando ninguna provincia califica.
_simple = sval.groupby(['item','semana'], as_index=False)['price'].median().rename(columns={'price':'nac_simple'})
if AGG_NACIONAL == 'poblacion':
    _pi = sval.groupby(['item','semana','provincia'], as_index=False).agg(
        price=('price','median'), n_suc=('suc_id','nunique'))
    _n0 = len(_pi)
    # (a) la provincia necesita un minimo de sucursales para ese item-semana. Sin este filtro,
    #     una provincia con 2 sucursales entra al promedio con TODO su peso poblacional y su
    #     ruido de muestreo se propaga al nacional.
    _pi = _pi[_pi['n_suc'] >= MIN_SUC_PROV_ITEM]
    # (b) winsorizacion: se descarta la provincia que se va fuera de [med/K, med*K] respecto de
    #     la mediana entre provincias de ese item-semana.
    _pi['_med'] = _pi.groupby(['item','semana'])['price'].transform('median')
    _pi = _pi[(_pi['price'] >= _pi['_med'] / PROV_OUTLIER_K) & (_pi['price'] <= _pi['_med'] * PROV_OUTLIER_K)]
    print(f'Nacional: mediana provincial ponderada por poblacion '
          f'(>={MIN_SUC_PROV_ITEM} suc/provincia, winsor K={PROV_OUTLIER_K}) | '
          f'celdas item-provincia-semana descartadas: {_n0-len(_pi):,} de {_n0:,} ({(_n0-len(_pi))/max(_n0,1)*100:.1f}%)')
    _pi['w']  = _pi['provincia'].map(PESOS_POBLACION).fillna(0.0)
    _pi['wv'] = _pi['w'] * _pi['price']
    _g = _pi.groupby(['item','semana'], as_index=False).agg(
        wv=('wv','sum'), w=('w','sum'), n_prov=('provincia','nunique'))
    _g = _g.merge(_simple, on=['item','semana'], how='outer')
    _g['nac'] = np.where(_g['w'].fillna(0) > 0, _g['wv'] / _g['w'], _g['nac_simple'])
    _g['n_prov'] = _g['n_prov'].fillna(0).astype(int)
    nac_item = _g[['item','semana','nac','n_prov']].copy()
else:
    nac_item = _simple.rename(columns={'nac_simple':'nac'})
    nac_item['n_prov'] = np.nan
    print('Nacional: mediana simple entre sucursales')

# ── 2. Arrastre (forward-fill acotado) ────────────────────────────────────────
nac_wide = nac_item.pivot(index='semana', columns='item', values='nac').sort_index()

# ── 2b. Frescos: reemplazo de la FORMA de la serie por un encadenado por EAN ──
# Ver FRESCO_NAC_ENCADENADO en la CELDA 1. Se conserva el NIVEL del estimador ponderado por
# poblacion en la ultima semana valida y se reconstruye la historia encadenando ratios de EANs
# apareados. Un eslabon puede saltear hasta FRESCO_MAX_HUECO_PAR semanas para reenganchar; si no
# reengancha, la celda queda NaN y el resto de la maquinaria (muestra apareada, arrastre acotado)
# la trata como faltante, que es el comportamiento correcto.
if FRESCO_NAC_ENCADENADO and len(ean_nac):
    _tipos_fr = [c for c in nac_wide.columns if c in FRESCO_INFO]
    _en = ean_nac[ean_nac['n_suc'] >= FRESCO_EAN_MIN_SUC]
    _rep, _sin = [], []
    for _t in _tipos_fr:
        _sub = _en[_en['item'] == _t]
        if len(_sub) < FRESCO_MIN_EANS_PAR:
            _sin.append(_t); continue
        _w = _sub.pivot_table(index='semana', columns='ean_norm', values='p', aggfunc='median')
        _w = _w.reindex(nac_wide.index)
        _idx = pd.Series(np.nan, index=nac_wide.index, dtype=float)
        _seg = pd.Series(np.nan, index=nac_wide.index, dtype=float)   # id de tramo encadenado
        _prev, _lvl, _sid = None, 1.0, 0
        for _sem in nac_wide.index:
            _fila = _w.loc[_sem]
            if _fila.notna().sum() == 0:
                continue
            if _prev is None or (nac_wide.index.get_loc(_sem)
                                 - nac_wide.index.get_loc(_prev)) > FRESCO_MAX_HUECO_PAR:
                # Un tramo solo puede ABRIR en una semana que tenga con que encadenar hacia
                # adelante. Sin esta condicion se abria un tramo en una semana de un solo EAN,
                # quedaba un tramo de UNA semana y se lo anclaba al estimador viejo -es decir,
                # justo al valor contaminado que estamos tratando de no publicar-.
                if int(_fila.notna().sum()) < FRESCO_MIN_EANS_PAR:
                    continue
                # Arranque, o hueco tan largo que no hay muestra apareada para cruzarlo. Se abre
                # un TRAMO nuevo. Cada tramo se ancla por separado contra el estimador anterior:
                # encadenar a traves del hueco publicaria de golpe toda la inflacion acumulada, y
                # reanclar todo con una sola semana base rebasea los tramos viejos (lo detecto el
                # test sintetico: Palta quedaba con un salto de 17% en la costura).
                _sid += 1; _lvl = 1.0
                _idx.loc[_sem] = _lvl; _seg.loc[_sem] = _sid; _prev = _sem; continue
            _a, _b = _w.loc[_prev], _fila
            _par = _a.notna() & _b.notna() & (_a > 0) & (_b > 0)
            if int(_par.sum()) < FRESCO_MIN_EANS_PAR:
                continue
            # MEDIA geometrica recortada, NO mediana. Los precios de supermercado son pegajosos:
            # en una semana dada solo una MINORIA de los EANs cambia de precio. Si repricea menos
            # de la mitad, la mediana del ratio da exactamente 1,0 y la cadena no acumula NADA.
            # Medido en la corrida 2026-09-08 con mediana: 93-100% de las semanas con variacion
            # cero, Pan frances con UN solo valor distinto en 139 semanas, y el acumulado de los
            # frescos en +58% contra +161% de los empaquetados (que no se encadenan) y +157% del
            # IPC alimentos. La media geometrica es el estimador de Jevons y captura el cambio
            # promedio aunque solo se mueva una parte del panel; el recorte de colas conserva la
            # robustez que motivaba la mediana.
            _lr = np.log((_b[_par] / _a[_par]).astype(float)).to_numpy()
            _lr = _lr[np.isfinite(_lr)]
            if _lr.size < FRESCO_MIN_EANS_PAR:
                continue
            # Robustez por CLIP absoluto, no por recorte de cuantiles: la distribucion de los
            # log-ratios tiene una masa grande en cero (los que no reprecian) mas una cola de los
            # que si, y un recorte por cuantiles puede borrar justamente la senal. El clip acota
            # la influencia de un EAN disparatado sin sacarlo del promedio.
            _lim = np.log(FRESCO_ESLABON_K)
            _lvl = _lvl * float(np.exp(np.clip(_lr, -_lim, _lim).mean()))
            _idx.loc[_sem] = _lvl; _seg.loc[_sem] = _sid; _prev = _sem
        _ok_idx = _idx.notna() & nac_wide[_t].notna()
        if int(_ok_idx.sum()) == 0:
            _sin.append(_t); continue
        _nuevo = pd.Series(np.nan, index=nac_wide.index, dtype=float)
        for _sd in sorted(_seg.dropna().unique()):
            _m = (_seg == _sd)
            if int(_m.sum()) < 2:
                continue          # tramo de una sola semana: no tiene ningun eslabon, no informa
            _mb = _m & _ok_idx
            if not bool(_mb.any()):
                continue          # tramo sin referencia de nivel: se deja faltante
            _base = _idx.index[_mb][-1]
            _nuevo[_m] = _idx[_m] / _idx.loc[_base] * float(nac_wide.at[_base, _t])
        if not bool(_nuevo.notna().any()):
            _sin.append(_t); continue
        _dif = float(np.nanmax(np.abs(_nuevo / nac_wide[_t] - 1))) * 100
        _rep.append((_t, int(_nuevo.notna().sum()), round(_dif, 1)))
        nac_wide[_t] = _nuevo
    print(f'Frescos encadenados por EAN: {len(_rep)} de {len(_tipos_fr)} tipos '
          f'(min {FRESCO_EAN_MIN_SUC} suc/EAN, {FRESCO_MIN_EANS_PAR} EANs apareados)')
    if _sin:
        print(f'  sin encadenar (se deja el estimador anterior): {", ".join(_sin)}')
    _rr = sorted(_rep, key=lambda x: -x[2])[:8]
    print('  mayor revision de la serie (max |nuevo/viejo-1|): '
          + ', '.join(f'{t} {d:.0f}%' for t, _, d in _rr))
    _pocos = [(t, n) for t, n, _ in _rep if n < len(nac_wide) * 0.8]
    if _pocos:
        print('  eslabones incompletos (<80% de las semanas): '
              + ', '.join(f'{t} {n}/{len(nac_wide)}' for t, n in sorted(_pocos, key=lambda x: x[1])[:8]))

# ── Banda de plausibilidad POR TIPO (ver RATIO_FRESCO en la CELDA 1) ─────────
# El precio nacional de un tipo fresco tiene que guardar una relacion estable con el ancla.
# La semana que se sale de esa relacion no es inflacion: es que cambio el conjunto de EANs que
# cotizan. Se marca como FALTANTE en vez de inventar un valor.
_anc_sem = nac_wide[[c for c in ANCLA_FRESCOS if c in nac_wide.columns]].median(axis=1)
_ratio_fuera = []
_ratio_bad = pd.DataFrame(False, index=nac_wide.index, columns=nac_wide.columns)
for _t, _r in RATIO_FRESCO.items():
    if _t not in nac_wide.columns:
        continue
    _piso_r = PISO_RATIO_OVERRIDE.get(_t, _r / FRESCO_RATIO_K_BAJO)
    _mal = ((nac_wide[_t] < _anc_sem * _piso_r)
            | (nac_wide[_t] > _anc_sem * _r * FRESCO_RATIO_K_ALTO)).fillna(False)
    _n = int(_mal.sum())
    if _n:
        _ratio_fuera.append((_t, _n))
        _ratio_bad[_t] = _mal
        nac_wide.loc[_mal, _t] = np.nan
_n_ratio = sum(n for _, n in _ratio_fuera)
if _n_ratio:
    print(f'Plausibilidad por tipo: {_n_ratio} semanas-tipo descartadas de '
          f'{int(nac_wide.notna().sum().sum()) + _n_ratio} '
          f'({_n_ratio / max(int(nac_wide.notna().sum().sum()) + _n_ratio, 1) * 100:.1f}%) | '
          + ', '.join(f'{t} {n}' for t, n in sorted(_ratio_fuera, key=lambda x: -x[1])))

nac_obs  = nac_wide.notna()                                   # presencia REAL (diagnostico)
nac_ff   = nac_wide.ffill(limit=MAX_SEMANAS_ARRASTRE)         # con arrastre
# El arrastre NO puede puentear una semana RECHAZADA por la banda de plausibilidad. Si lo
# hiciera, al reaparecer un precio valido el indice compararia el precio nuevo contra uno viejo
# arrastrado y publicaria de golpe toda la inflacion acumulada del hueco. Un item rechazado
# tiene que quedar FUERA de la muestra apareada mientras dure el rechazo, y volver a entrar sin
# generar salto. (Medido sobre el panel real: baja el desvio de la variacion semanal de 2,32%
# a 2,17% y saca un salto de mas de 8%.)
nac_ff   = nac_ff.mask(_ratio_bad)
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
        # .strip() en el rubro: en la hoja hay 'Limpieza ' con espacio al final, que aparecia
        # como un rubro aparte en todas las tablas de composicion.
        _r = (str(_cat).strip().title() if (_usar_cat and str(_cat).strip()) else str(_rub).strip())
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
    # El indice arranca en la primera semana con cobertura suficiente: publicar un indice de una
    # canasta que en esa fecha tenia 4 de 14 productos (caso Tecnologica en 2024) no es informativo.
    _cov = _V.notna().sum(axis=1) / len(_its)
    _ok_cov = _cov[_cov >= COBERTURA_MIN_INDICE].index
    if not len(_ok_cov):
        _ok_cov = _cov[_cov >= _cov.max() * 0.99].index
    _desde = _ok_cov[0]
    _V = _V.loc[_desde:]
    _cov = _cov.loc[_desde:]
    aporte_dict[_name] = _V
    _aviso_desde = (f'      [{_name}] el indice arranca en {_desde}: antes la canasta tenia '
                    f'menos del {COBERTURA_MIN_INDICE:.0%} de sus items'
                    if _desde != list(nac_ff.index)[0] else '')
    _sem = list(_V.index)
    _idx = [100.0]
    for _t in range(1, len(_sem)):
        _a = _V.iloc[_t]; _b = _V.iloc[_t-1]
        _m = _a.notna() & _b.notna()
        _den = _b[_m].sum()
        _idx.append(_idx[-1] * ((_a[_m].sum()/_den) if (_m.any() and _den > 0) else 1.0))
    _idx = pd.Series(_idx, index=_sem)
    _directo = _V.sum(axis=1, min_count=1)
    _ok = _cov[_cov >= 0.95].index
    _anchor = _ok[-1] if len(_ok) else _sem[-1]
    _nivel = _directo.loc[_anchor] * _idx / _idx.loc[_anchor]
    _s = pd.DataFrame({'semana': _sem,
                       'costo_mediana': _nivel.values,          # nivel encadenado (headline)
                       'costo_directo': _directo.values,        # suma cruda (referencia)
                       'indice_100': (_idx/_idx.iloc[0]*100).values,
                       'items_con_precio': _V.notna().sum(axis=1).values,
                       'items_receta': len(_its),
                       'cobertura_%': (_cov.values * 100).round(0)})
    _s['mes'] = _s['semana'].map(_mes_de_semana)
    _s['var_sem_%'] = _s['costo_mediana'].pct_change(fill_method=None) * 100
    serie_sem_dict[_name] = _s
    print(f'  [{_name}] {len(_s)} semanas | items {len(_its)} | ancla {_anchor} | '
          f'ultimo costo ${_s["costo_mediana"].iloc[-1]:,.0f} ({_s["var_sem_%"].iloc[-1]:+.1f}% sem)')
    if _aviso_desde:
        print(_aviso_desde)

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
# ── Series MENSUALES en formato LARGO (todas las canastas juntas) ────────────
# El Excel tenia mensual solo a nivel canasta (`Mes_*`, `vsIPC_*`): rubro, region, provincia y
# cadena eran semanales o foto del ultimo mes. Se agregan las cuatro dimensiones en mensual.
# Formato largo y consolidado -no una hoja por canasta y dimension, que serian 24 hojas nuevas-
# porque es lo que sirve para tablas dinamicas y para econometria.
# Convencion: el costo mensual es el PROMEDIO de los costos semanales del mes, igual que en
# `serie_mes_dict`. Para las aperturas geograficas se toma primero la mediana entre sucursales
# de cada semana y despues el promedio de esas semanas, de modo que una semana con mas
# sucursales no pese mas que las otras.
prov_dict = {}; cadena_dict = {}; region_dict = {}; serie_region_dict = {}
_MES_RUBRO = []; _MES_REGION = []; _MES_PROV = []; _MES_CADENA = []
_cs_um = costo_suc[costo_suc['mes'] == _ult_mes]

def _mensualizar_geo(_cr, _geo):
    """Serie mensual de una apertura geografica: mediana entre sucursales por semana y
    despues promedio de las semanas del mes (ver nota de convencion arriba)."""
    _sw = (_cr.groupby([_geo, 'semana'], as_index=False)
              .agg(costo=('costo', 'median'), n_suc=('suc_id', 'nunique')))
    _sw['mes'] = _sw['semana'].map(_mes_de_semana)
    _t = (_sw.groupby([_geo, 'mes'], as_index=False)
             .agg(costo_mediana=('costo', 'mean'), n_sucursales=('n_suc', 'max'),
                  n_semanas=('semana', 'nunique')))
    _t = _t.sort_values([_geo, 'mes'])
    _t['var_mensual_%'] = (_t.groupby(_geo)['costo_mediana'].pct_change(fill_method=None) * 100).round(2)
    return _t

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
    for _geo, _acc in (('region', _MES_REGION), ('provincia', _MES_PROV), ('cadena', _MES_CADENA)):
        _t = _mensualizar_geo(_cr, _geo)
        _t.insert(0, 'canasta', _name)
        _acc.append(_t)
    _rs = rubro_sem_dict.get(_name)
    if _rs is not None and len(_rs):
        _t = (_rs.groupby(['mes','rubro'], as_index=False)
                 .agg(costo=('costo','mean'), n_semanas=('semana','nunique')))
        _t = _t.sort_values(['rubro','mes'])
        _t['var_mensual_%'] = (_t.groupby('rubro')['costo'].pct_change(fill_method=None) * 100).round(2)
        _tot = _t.groupby('mes')['costo'].transform('sum')
        _t['participacion_%'] = (_t['costo'] / _tot * 100).round(2)
        _t.insert(0, 'canasta', _name)
        _MES_RUBRO.append(_t)

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

# ── TRIPWIRE: saltos del precio nacional de un item ──────────────────────────
# Un salto grande de un item casi nunca es inflacion: es un cambio en el SET de variantes que
# cotizan (un "tipo" fresco que se va a otro regimen de precio) o un error de carga. Antes esto
# solo se descubria mirando el grafico de la canasta y volviendo hacia atras. Ahora sale listado.
_lr = np.log(nac_wide[[c for c in nac_wide.columns if c in set(_items_receta)]].replace(0, np.nan))
_d  = _lr.diff()
_sal = []
for _i in _d.columns:
    _s = _d[_i].dropna()
    for _sem, _v in _s[_s.abs() > np.log(1 + ALERTA_SALTO_ITEM)].items():
        _prev = _sem_anterior(_sem)
        _sal.append({'item':_i, 'descripcion':_etiqueta(_i), 'semana':_sem,
                     'var_%':round((np.exp(_v)-1)*100, 1),
                     'precio_antes':round(float(nac_wide.at[_prev,_i]), 1) if _prev in nac_wide.index else None,
                     'precio_despues':round(float(nac_wide.at[_sem,_i]), 1),
                     'canastas':', '.join(n for n in CANASTAS_ACTIVAS if _i in set(RECETAS[n]['item']))})
alertas_precio_item = (pd.DataFrame(_sal).sort_values(['semana','var_%'], ascending=[False, False])
                       if _sal else pd.DataFrame(columns=['item','descripcion','semana','var_%',
                                                          'precio_antes','precio_despues','canastas']))
_corte_trim = _SEMANAS[max(0, len(_SEMANAS)-13)]
_sal_ult = (alertas_precio_item[alertas_precio_item['semana'] >= _corte_trim]
            if len(alertas_precio_item) else alertas_precio_item)

print(f'\n=== TRAZABILIDAD ===')
print(f'  Items en recetas: {len(_items_receta)} | con panel nacional: {len(presencia_items)}')
print(f'  Candidatos a REEMPLAZO (sin dato en las ultimas {MAX_SEMANAS_ARRASTRE} semanas): {len(alertas_reemplazo)}')
if len(alertas_reemplazo):
    print(alertas_reemplazo[['descripcion','canastas','estado','ult_semana_con_dato']].to_string(index=False))
print(f'  Saltos de precio de un item >{ALERTA_SALTO_ITEM*100:.0f}% en una semana: '
      f'{len(alertas_precio_item)} en toda la serie, {len(_sal_ult)} en el ultimo trimestre')
if len(_sal_ult):
    print('  (ultimo trimestre - revisar en la hoja Panel_nacional antes de publicar)')
    print(_sal_ult[['semana','descripcion','var_%','precio_antes','precio_despues']].head(15).to_string(index=False))
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
        {'parametro':'Frescos - regimen','valor':f'referencia nacional del tipo por MES; se descartan las variantes fuera de [ref/{FRESCO_REGIMEN_K}, ref*{FRESCO_REGIMEN_K}] antes de agregar por sucursal'},
        {'parametro':'Frescos - outliers','valor':f'precio del tipo = mediana de variantes por sucursal-semana, outliers fuera de [med/{FRESCO_OUTLIER_K}, med*{FRESCO_OUTLIER_K}] descartados'},
        {'parametro':'Tripwire','valor':f'hoja Alertas_precio_item: todo salto semanal del precio nacional de un item mayor a {ALERTA_SALTO_ITEM:.0%}'},
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
    # Panel nacional por item x semana: es la materia prima de todas las series. Permite
    # diagnosticar un salto yendo directo al item, sin tener que inferirlo desde los rubros.
    _pn_out = nac_ff.T.copy()
    _pn_out.insert(0, 'descripcion', [(_etiqueta(i) if i in _items_receta else i) for i in _pn_out.index])
    _pn_out.round(1).to_excel(_w, 'Panel_nacional')
    # Mismo panel en frecuencia MENSUAL (promedio de las semanas del mes), que es la frecuencia
    # a la que se compara contra el IPC.
    _pnm = nac_ff.copy()
    _pnm.index = pd.Index([_mes_de_semana(_x) for _x in _pnm.index], name='mes')
    _pnm = _pnm.groupby(level='mes').mean().T
    _pnm.insert(0, 'descripcion', [(_etiqueta(i) if i in _items_receta else i) for i in _pnm.index])
    _pnm.round(1).to_excel(_w, 'Panel_nacional_mes')
    # Series mensuales en formato largo (todas las canastas).
    for _df_m, _hoja in ((_MES_RUBRO, 'Mes_rubro'), (_MES_REGION, 'Mes_region'),
                         (_MES_PROV, 'Mes_provincia'), (_MES_CADENA, 'Mes_cadena')):
        if _df_m:
            pd.concat(_df_m, ignore_index=True).to_excel(_w, _hoja, index=False)
    cobertura_emp.to_excel(_w, 'Cobertura_emp', index=False)
    cobertura_frescos.to_excel(_w, 'Cobertura_frescos', index=False)
    presencia_items.to_excel(_w, 'Presencia_items')
    (alertas_reemplazo if len(alertas_reemplazo) else pd.DataFrame({'sin_alertas':['ok']})
     ).to_excel(_w, 'Alertas_reemplazo', index=False)
    (alertas_precio_item if len(alertas_precio_item) else pd.DataFrame({'sin_alertas':['ok']})
     ).to_excel(_w, 'Alertas_precio_item', index=False)
print(f'Excel: {_xlsx.name}  ({_xlsx.stat().st_size/1024:.0f} KB)')
print(f'   Guardado en: {_xlsx.parent}')
print('   Hojas: Metodologia, Resumen, Sem_*, Mes_*, vsIPC_*, Rubro_sem_*, Comp_rubro_*, '
      'Detalle_*, Prov_*, Cadena_*, Region_*, RegionSem_*, Panel_nacional, '
      'Panel_nacional_mes, Mes_rubro, Mes_region, Mes_provincia, Mes_cadena, '
      'Cobertura_emp, Cobertura_frescos, Presencia_items, Alertas_reemplazo, Alertas_precio_item')
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
print(f'Nacional: {AGG_NACIONAL} | arrastre: {MAX_SEMANAS_ARRASTRE} sem | regimen K: {FRESCO_REGIMEN_K} | outlier K: {FRESCO_OUTLIER_K} | frac min: {FRAC_PRODUCTOS_MIN}')
try:
    if _FR_DESCARTES:
        _nd = sum(x[1] for x in _FR_DESCARTES)
        _aa = np.median([x[2] for x in _FR_DESCARTES])
        print(f'Plausibilidad frescos: {_nd:,} observaciones fuera de la banda '
              f'[ancla*{FRESCO_PISO_ANCLA}, ancla*{FRESCO_TECHO_ANCLA}] | ancla mediana ${_aa:,.0f}/kg')
except Exception:
    pass

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

# Fiabilidad de la desagregacion: la volatilidad de una region escala con 1/sqrt(n_sucursales),
# asi que una region con pocas sucursales puede mostrar saltos que son ruido de muestreo.
print('')
print('-'*72)
print('### FIABILIDAD DE LA DESAGREGACION REGIONAL')
try:
    _refreg = serie_region_dict[CANASTAS_ACTIVAS[0]].sort_values(['region','semana'])
    _vv = (_refreg.groupby('region')
             .agg(n_suc=('n_sucursales','median'),
                  sd=('costo_mediana', lambda x: x.pct_change(fill_method=None).std()*100)).reset_index())
    print(f'  (canasta {CANASTAS_ACTIVAS[0]})  region | n_suc mediano | desvio de la variacion semanal')
    for _, _r in _vv.sort_values('n_suc', ascending=False).iterrows():
        _fl = '   <-- muestra chica: leer con cuidado' if _r['n_suc'] < 100 else ''
        print(f'      {_r["region"]:<18} {int(_r["n_suc"]):>6}   {_r["sd"]:>5.1f}%{_fl}')
except Exception as _e:
    print('  (no disponible:', _e, ')')

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
    print(f'  Saltos de item >{ALERTA_SALTO_ITEM:.0%} en una semana: {len(alertas_precio_item)} en la serie '
          f'| {len(_sal_ult)} en el ultimo trimestre  (hoja Alertas_precio_item)')
    if len(_sal_ult):
        print(_sal_ult[['semana','descripcion','var_%','precio_antes','precio_despues']].head(10).to_string(index=False))
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
