# SEPA — Referencia Técnica

Última actualización: 2026-10-23 (en "Defectos y cambios de la fuente 2022-2026", con los precios 2022-2026 de los
zips del Drive: cambio de códigos de Molinos en sep-oct 2023 con precios congelados en los viejos y el salto de precio
del código nuevo, los sin TACC viejos de Matarazzo genuinos, la bolsa Wakas de 250 g y la caja de 300 g, presentaciones
y sabores viejos en el Maestro, precios controlados en 2023 y su salida en oct-2023 / ene-2024, Farmacity y Axion en el
SEPA diario). Antes, 2026-10-22 (sección nueva "Defectos y cambios de la fuente 2022-2026": días con la mitad de los comercios, corte de la fuente desde ago-2026, comercios que se van y huecos temporales, archivos y filas repetidas, provincias con nombre o vacías, códigos con basura de codificación, precios simbólicos, nombres de comercio; FACTOR_PRECIO: los semestrales 2022-2026 del Drive están todos en pesos y la regla de centavos vence hacia 2029). Antes, 2026-10-16 (provincia por coordenadas con polígonos de ar.json y tolerancia de 100 km en vez de rectángulos —BUG-44—; maestro de sucursales: la `REGION=AMBA` no es confiable en Buenos Aires —usar coordenadas—, provincia ISO vs maestro, comercios sin nombre; script 03 con carpeta de días y zip semestral A/B automático). Antes, 2026-09-03 (nb07: lectura semanal + colapso de frescos a tipo [fix RAM] + selección de frescos por categoría; nb02: motor `datos_econometria`)

> **Cambio 2026-08-21 (nb02/nb05, CELDA 6/7)**: el precio por sucursal del mes reportado ahora se calcula sobre **todos los días del mes** —mediana de los días y media con outliers fuera— en vez de tomar solo el primer día (`drop_duplicates keep='first'`, eliminado). El promedio descarta valores fuera de `[mediana/4, mediana×4]` antes de promediar (helper `_pmean`, vectorizado en la CELDA 7). Esto DUPLICA los artefactos: análisis mediana (nombres base) y promedio (sufijo `_prom`). Detalle en `.claude/memory.md`.
>
> **Lectura DIARIA (nb06 — brecha celíaca)**: los archivos semestrales traen **una columna de precio por día** (`precio_YYYYMMDD`; parte1 = días 01–15, parte2 = 16–fin). El Notebook 06 melt-ea esas columnas **conservando la fecha** (`pd.to_datetime(col[-8:], format='%Y%m%d')`) para construir series diarias/semanales/mensuales de la brecha. Cache incremental de meses cerrados + mes en curso fresco (`brecha_dia_{hash}_v1.parquet`). Detalle en `docs/BRECHA_CELIACA.md`.

## Dos formatos completamente distintos

### Formato semestral (el que usa este proyecto)

```
carga/
├── 2026A.zip
│   ├── 042026_pais_parte1COMPLETO.csv.gz   ← días 1–15 de abril 2026
│   └── 042026_pais_parte2COMPLETO.csv.gz   ← días 16–30
├── 2025B.zip
└── ...
```

- **Separador**: coma
- **Columnas fijas**: `id_comercio, id_bandera, id_sucursal, sucursales_provincia, id_producto`
- **Columnas de precio**: `precio_YYYYMMDD` (una por día del período — formato wide)
- **Precios**: entero — VER SECCIÓN FACTOR_PRECIO
- **Valores faltantes**: string `'NA'` (no Python NaN, hay que reemplazar explícitamente)
- `id_producto`: EAN/GTIN; la mayoría son 13 dígitos, algunos son más cortos (UPC-8, UPC-12). **Siempre leer como string** (`dtype={'id_producto':'str'}`). Si en algún paso del pipeline se convierte a int64, los ceros iniciales se pierden al exportar. Fix: `df['id_producto'].astype(str).str.zfill(13)` antes de exportar a Excel.

### Formato diario

```
YYYY-MM-DD.zip
├── cadena1.zip
│   ├── comercio.csv
│   ├── sucursales.csv
│   └── productos.csv
└── ...
```

- **Separador**: pipe `|`
- **Precios**: float en pesos directamente (sin factor)
- **Identidad de cadena**: string completo en `comercio_bandera_nombre`
- **Cadenas visibles**: hasta 28 banners comerciales
- Útil para ver los precios reales de cada banner, pero más difícil de consolidar en el tiempo
- **Del diario al semestral**: `notebooks/03_consolidacion_ultimo_mes.py` (local) arma los `MMAAAA_pais_parteN` del mes
  en curso y los mete en el zip del semestre. Desde 2026-10: `ZIP_DIARIO` = zip del mes o carpeta con las carpetas
  `YYYY-MM-DD` ya descomprimidas; `CARGA_DIR` = carpeta de los semestrales, de la que elige `YYYYA.zip` (ene-jun) o
  `YYYYB.zip` (jul-dic) y lo crea si no existe. Pasos en el README ("Correrlo localmente").

---

## Defectos y cambios de la fuente 2022-2026 (medidos con el nb09, 2026-10)

Medidos sobre los zips semestrales del Drive (`2022A.zip` → `2026B.zip`; 115 archivos y 1.747 días con dato al
15/10/2026, 116 y 1.754 al 22/10/2026) por el nb09 y su revisión (`docs/AUDITORIA_2026-10-22_nb09.md`, con los scripts
en `docs/auditoria/scripts_nb09_2026-10/`). Cualquier lectura por sucursal o por día tiene que tenerlos en cuenta.

| Qué | Dónde / cuánto | Cómo se trata |
|---|---|---|
| Días calendario sin dato | 31/10/2023 y 10/05/2026 | No se completan (nb08, nb09) |
| Días con la mitad de los comercios | **16-28/07/2023**: 16-18 de 35 comercios, ~1.450 sucursales (870 el 20/07/2023). 28 días con < 2.000 sucursales; los demás son sueltos (20-21/06/2022, 01-04/04/2025, 27 y 30/07/2025, 01/08/2026...) | Denominadores diarios (nb09, hoja `Dias`); marcados en la serie (nb08, `cobertura_incompleta`); el índice de sucursales apareadas no salta |
| Corte de la fuente desde el 01/08/2026 | ago-oct 2026 salen del SEPA diario (script 03), que no trae los comercios 19, 1000, 2000, 2002, 2005, 2007, 2013 y 3001: las sucursales activas pasan de ~3.400 a ~3.030 y algunas vienen sin provincia | Reemplazar por el semestral oficial cuando salga y **borrar del caché** esos meses (nb08: `_cache/diaria_v3_<clave>/2026-08.parquet`, `prov_2026-08.parquet`, `estado_2026-08.parquet` y los de los meses siguientes; nb09: `_cache_nb09/v1/2026-08_p*` y siguientes; nb02/nb07: sus cachés por mes): ningún caché mira si cambió el zip |
| Comercios que dejan de publicar | 33 sin precios en oct-26 desde 2022 (8 en 2022, 8 en 2023, 4 en 2024, 4 en 2025, 9 en 2026: los 8 del corte y **Libertad, último día 02/09/2026**) | nb09: `solo_en_comercios_que_dejaron_de_publicar` y `mes_baja_comercios` |
| Huecos temporales de un comercio | ChangoMas, Cadena 2002 y Mariano Max sin precios en todo sep-2024 (vuelven después) | No confundir con bajas |
| Dos archivos para la misma parte | `2024B.zip`: `082024_pais_parte1COMPLETO.csv.gz` (días 1-5, 3.048 sucursales) y `...COMPLETOb.csv.gz` (días 1-15, 3.376, superconjunto con los mismos precios) | Usar el que cubre más días (nb08 y nb09); **el nb02 todavía los suma** (BUGS_Y_MEJORAS) |
| Filas sucursal × producto repetidas | 141.020: 2022-05_p2 111.651 (sin mirar: no hay zip 2022 en la PC), 2025-08_p1 24.890 (una sucursal de ChangoMas, cada producto en dos filas con días distintos), 2022-11_p2 1.222, 2024-01_p2 892 (891 de la Cadena 2011, copias exactas), 2024-02_p1 874, 2022-10_p1 645, 2023-03_p1 341, 2022-07_p2 267, 2025-07_p2 88, y 1 fila del comercio 35 en casi todos los archivos hasta 2024-10 | Contar una vez con la unión de días (nb09); promedio de las repetidas para los relativos (nb08) |
| Provincias con el nombre o vacías | ene-may 2022 casi todas con nombre (19-21 nombres, 'Santa fe' incluida); jun-22 → jul-23 'Santa Fe'; ago-23 → sep-26 'Buenos Aires' en una sucursal de DIA; vacías en 36 sucursales de 2022-2023 y en ago-sep 2026 | Pasar a código ISO (`iso_provincia` del lector del nb09); las vacías toman la del maestro o no cuentan |
| Códigos con texto mal codificado pegado | 14 de la "Cadena 2003" en feb y jul 2022: tablets Samsung `8806094046892` y `8806094046908` con hasta 132.130 caracteres de más (2 no entran en una celda de Excel) | Unir a su EAN (nb09, `limpiar_codigo`) |
| Precios simbólicos | Panadería y verdura por kilo de DIA a $5-95, comidas de ChangoMas a $4-10, bolsas "por millar" a $75 | nb09: `precio_simbolico` (≤ 1,25% de la mediana del último mes) |
| Comercios que parecen el mismo local | 44, 45 y 46 (una sucursal cada uno, comparten 12.735 productos); 49 y 50 (comparten 16.968) | No se fusionan (sin nombres en 2026); por eso el puntaje del nb09 usa cuotas diarias |
| Nombres de comercio | Según el `comercio.csv` del SEPA: 47 Unicoop (no Pasamonte), 5 California, 23 Axion Energy, 4 Estación Lima, 3 Deheza, 6 Comodín, 8 Mariano Max, 2013 Mercado Libre | El nb09 usa los oficiales; el nb02 (CELDA 4) tiene nombres viejos |
| Saltos de catálogo | jul-26: 73 mil productos por día hasta el 16, 89 mil desde el 17 (un comercio sumó ~16 mil productos) | Está en el crudo; las cuotas diarias no se ven afectadas |
| Colapsos de cobertura de marcas líderes | Fideos y arroz de Molinos (Lucchetti, Matarazzo, Gallo, Ala), azúcar Ledesma, harinas Morixe y Pureza 0000: de ~1.500 a 10-200 sucursales entre dic-2023 y abr-2024 | Fuera de las canastas fijas desde 2022 (regla de estabilidad de la canasta de pass-through) |
| **Molinos cambió los EANs de sus fideos** (medido con el nb09, 2026-10-23) | En sep-oct 2023 Lucchetti y Matarazzo pasan a códigos nuevos con número de forma (Spaghetti Matarazzo 500 g `7790070318640` → `7790070336309` "N3"; Spaghetti Lucchetti `7790070318282` → `7790070336385` "N7"); en abr-2023 aparecieron códigos intermedios (N°5, N°51, N°52, N°34). Los códigos viejos **siguen apareciendo en ~100 sucursales con el precio CONGELADO** (Mostacholes Lucchetti viejo a $246-337 en 2024-2025 contra $1.042-1.700 del nuevo). Además, de dic-2023 a mar-2024 **todo Molinos** (también los códigos que no cambiaron, como Coditos Lucchetti) cae de ~1.300-2.000 a ~100-200 sucursales por día y vuelve en abril-julio de 2024 | Series largas: empalmar el código viejo (hasta el mes anterior al nuevo) con el nuevo y **no usar el viejo después** (nb06: `VIGENCIA`); los intermedios, afuera. Parte del "colapso" de la fila de arriba es este cambio |
| Wakas cambió los EANs de sus fusilli (jun-2024) y el paquete | La bolsa de 250 g (`7798031470024`, `…031`, `…048`, `…086`, `…093`) pasó a la caja de 300 g (`…796`, `…826`, `…802`, `…819`, `…833`; el Maestro dice 250 g también para la caja). En jun-sep 2024 la caja costaba 26% más que la bolsa en las mismas sucursales (= mismo precio por gramo); desde ago-2024 Cencosud publica la bolsa como alias de la caja (mismo precio, mismas sucursales) | Empalme con vigencia: bolsa 250 g hasta 2024-07, caja 300 g desde 2024-06 (nb06) |
| El Maestro interno con presentaciones o sabores viejos | Porteñitas `7790040132689`: 130 g en el Maestro, 139 g en cuatro cadenas en oct-2026 (sin fecha del cambio); Crisppino 100 g `7798199770134`/`…141` con los sabores cruzados; Grandiet `7797330100663` "Galletas de Arroz" (son dulces) | Comparar con la descripción y la presentación del SEPA diario antes de usar gramos o descripciones del Maestro |
| **El Maestro interno tiene descripciones viejas o equivocadas** | `7790070336002` es el Spaghetti sin TACC Matarazzo 500 g en TODAS las cadenas (SEPA diario de oct-2026) y el Maestro dice "Fideos Mostachol 5 Cereales" | Identificar los productos por la descripción del SEPA (`productos.csv` del SEPA diario) y verificar con precios |
| **Precios controlados en 2023 y salida en oct-2023 / ene-2024** (medido con los zips 2022-2026, 2026-10-23) | Durante 2023 los productos de marcas masivas (Molinos, Bagley/Mondelez, Arcor, Mamá Cocina…) suben muy por debajo de la inflación (galletitas dulces con TACC +2-5% por mes en jun-sep 2023, contra +5-21% de las marcas celíacas). Molinos sale cambiando los códigos: en sep-oct 2023, en las mismas ~1.000 sucursales, el código nuevo cuesta 2,5-3,4 veces el viejo (Spaghetti Matarazzo $166 contra $60 por 100 g). El resto, al terminar el programa de precios: ene-2024 +87% galletitas dulces, +105% saladas y +118% rebozador con TACC | Comparaciones entre marcas masivas y de nicho: leer 2023 aparte. Los controles de identidad de productos no pueden cruzar oct-2023 → mar-2024 (nb06, s10: `TRANSICION`) y el salto en el corte de código de Molinos es precio, no otro producto |
| **Los códigos sin TACC viejos de Matarazzo son genuinos** (corrección del 2026-10-23) | `7790070321800` (spaghetti), `7790070321855` (tirabuzón) y `7790070321794` (penne): en 2022, en las mismas sucursales, costaban 1,97, 2,97 y 2,0 veces el Matarazzo común (nunca menos de 1,3× en ninguna cadena), con 1.400-2.000 sucursales por día. En oct-2023 Molinos los reemplazó (`…336002`, `…335982`, `…335999`) y quedaron en ~100 sucursales con el precio CONGELADO: por eso en 2024-2026 parecían fideos comunes y el filtro de plausibilidad de agosto de 2026 los sacó | Empalmar con vigencia (el viejo hasta el corte) como los demás de Molinos |
| "Sin TACC" escrito de muchas formas | En las descripciones del SEPA: S/TACC, S TACC (Carrefour), S-TACC, STACC, SIN T.A.C.C., LIBRE D/GLUTEN, LIB.D/GLUTEN, L.GLUTEN, Libr D Glut, marca Glutal. "C/GLUTEN" (tostadas Firenze) y "galletitas DE gluten" son CON TACC; "PISTACCHIO" contiene "TACC" | Regla del nb06 / scripts de `docs/auditoria/scripts_nb06_2026-10/` (s2); marcas celíacas: >= 50% de sus productos etiquetados |
| Farmacias y banderas | El comercio 24 es **Farmacity** (banderas SIMPLICITY y FARMACITY; 338 sucursales en el nb09). ChangoMas: 11-1/3/4 SuperChangomas, 11-2 Changomas, 11-5 HiperChangomas. En el SEPA diario el zip del comercio 36 viene vacío todos los días | El nb06 deja afuera el 24 (y el 23, Axion) |
| Unidades | Factor 1 en los 1.747 días (2022-01 → 2026-10 al 15/10): los semestrales publicados hoy están todos en pesos | Ver la sección siguiente |

---

## FACTOR_PRECIO — crítico para precios correctos

Los datos semestral cambiaron de unidad a lo largo del tiempo:
- **Hasta ~2024**: precios en centavos → dividir /100
- **2025B en adelante**: precios ya en pesos → FACTOR = 1 (NO dividir)

> **Medido el 2026-10-22** (nb09): en los zips que hay hoy en el Drive (2022A → 2026B) el factor dio 1 en todos los días,
> o sea que los semestrales se republicaron en pesos. La regla "mediana > $10.000 → ÷100" (nb09 por archivo con todos los
> productos; nb02 CELDA 9 y nb08 por mes con las observaciones de la canasta) se mantiene por si vuelve un archivo en
> centavos, pero vence: en jul-26 esas medianas eran $4.529 y $3.420, y con ~2,5% mensual cruzarían $10.000 hacia 2029.
> Arreglo cuando haga falta: comparar con el mes anterior (como la corrección de unidades del nb08) o con el semestral
> de 2022, que está en pesos. La CELDA 6 del nb02, el nb05, el nb06 y el nb07 usan EANs de referencia, con el mismo
> problema más tarde.

### Autodetección implementada en `01_exploracion_productos.ipynb`

```python
# Después de consolidar df_suc, antes del enriquecimiento:
_mediana_ref = df_suc['precio_promedio'].median()
FACTOR_PRECIO = 100 if _mediana_ref > 10_000 else 1

if FACTOR_PRECIO == 100:
    df_suc['precio_promedio'] = (df_suc['precio_promedio'] / 100).astype('float32')
```

**Umbral**: mediana global del dataset > $10,000 → datos en centavos (divido ÷100). Esto funciona porque la mediana de precio de los productos en centavos ronda 100k–500k, muy lejos del rango pesos (~$500–$5,000).

**Confirmación para abril 2026**: mediana raw ≈ 1,411 → FACTOR = 1 (ya en pesos). Confirmado también por `analisis_SEPA_evolucion_AMBA.ipynb` con productos de referencia específicos.

### Patrón alternativo más robusto (otros notebooks)

```python
# Usar un producto de referencia con precio conocido (sal fina ~$500-$2000 en 2026)
EANS_REFERENCIA = ['7793370008980', '7790895000061', '7793370008188']  # sal, fideos, lavandina

precios_ref = df[df['id_producto'].isin(EANS_REFERENCIA)]['precio_promedio']
mediana_ref = precios_ref.median()

if 30 <= mediana_ref <= 5000:
    FACTOR_PRECIO = 1      # ya en pesos
elif 3000 <= mediana_ref <= 500_000:
    FACTOR_PRECIO = 100    # en centavos, necesita /100
else:
    raise ValueError(f"Mediana de referencia inesperada: {mediana_ref}")
```

---

## Identidad de cadenas en formato semestral

### El problema

`id_bandera` (valores 1-6) identifica el **grupo corporativo** dentro del comercio, NO la cadena comercial. Eso es por qué se ven solo 5-6 "cadenas" cuando en realidad son 16.

### Cómo obtener los nombres reales

Combinar `(id_comercio, id_bandera)` con este diccionario:

```python
NOMBRES_CADENAS_COMPUESTAS = {
    ('9',  '1'): 'Vea',
    ('9',  '2'): 'Disco',
    ('9',  '3'): 'Jumbo',
    ('10', '1'): 'Carrefour',
    ('10', '2'): 'Carrefour Market',
    ('10', '3'): 'Carrefour Express',
    ('11', '2'): 'ChangoMas',
    ('11', '4'): 'Hiper ChangoMas',
    ('11', '5'): 'Mi ChangoMas',
    ('16', '1'): 'Hipermercado Libertad',
    ('16', '2'): 'Mini Libertad',
}

NOMBRES_CADENAS_SIMPLES = {
    '2':  'La Anónima',
    '12': 'Coto',
    '13': 'Cooperativa Obrera',
    '15': 'DIA',
}
```

### Lookup vectorizado (patrón actual del notebook)

```python
# Construir lookup por clave compuesta id_comercio_id_bandera
_lookup_comp = {f"{k[0]}_{k[1]}": v for k, v in _CADENAS_COMPUESTAS.items()}

_ck = df['id_comercio'] + '_' + df['id_bandera']
df['nombre_cadena'] = _ck.map(_lookup_comp)

# Fallback: cadenas simples (solo por id_comercio)
_null = df['nombre_cadena'].isna()
df.loc[_null, 'nombre_cadena'] = df.loc[_null, 'id_comercio'].map(_CADENAS_SIMPLES)

# Residuos desconocidos
_null = df['nombre_cadena'].isna()
df.loc[_null, 'nombre_cadena'] = 'Comercio ' + df.loc[_null, 'id_comercio']
```

> **Por qué NO usar `apply()`**: con 50M filas, `df.apply(lambda r: get_nombre_cadena(r['id_comercio'], r['id_bandera']), axis=1)` ejecuta millones de llamadas Python → agota la RAM. El lookup vectorizado con `.map()` opera en C puro.

### Implicación para el score de cobertura

Con los datos semestral, `MIN_CADENAS = total_cadenas` filtra por grupos corporativos (5-6 valores), no por banners (16). Un producto puede estar en "Carrefour" (id_bandera=1) pero no en "Carrefour Express" (id_bandera=3), y el filtro no lo detecta. Esto es una limitación estructural del formato semestral.

---

## Maestros de referencia

| Archivo | Descripción | Join key |
|---------|-------------|----------|
| `Maestro de Productos Interno.xlsx` | ~176K productos, rubro/categoría/subcategoría | `producto_sepa_id` = `id_producto` |
| `maestro_sucursales_completo.xlsx` | 3,611 sucursales con cadena, provincia, región | `id_comercio` + `id_bandera` + `id_sucursal` |
| `maestro-provincias.xlsx` | código SEPA → nombre legible | `sucursales_provincia` |

### Normalización de provincias (obligatoria)

```python
df['PROVINCIA_NOMBRE'] = (
    df['PROVINCIA'].combine_first(df['provincia'])   # combina dos fuentes
    .str.strip()
    .str.replace(r'^Provincia de ', '', regex=True)
    .str.replace('Ciudad Autónoma de Buenos Aires', 'CABA', regex=False)
    .str.title()   # fix "San juan" → "San Juan" y similares
    .str.replace('Caba', 'CABA', regex=False)  # .title() rompe CABA
)
```

El maestro de sucursales tiene `PROVINCIA` (columna del Excel) y el maestro de provincias tiene `provincia` (columna de mapping del código SEPA). Se combinan con `.combine_first()` para usar la fuente más confiable disponible.

### ⚠️ Inconsistencia de capitalización en el maestro — San Juan (BUG-15, 2026-05-29)

El maestro de sucursales almacena la provincia de San Juan como `"San juan"` (con 'j' minúscula), no como `"San Juan"` ni como `"Provincia de San Juan"`. Si el dict `PROV_NORM` no incluye esta variante exacta, la provincia queda sin normalizar y:

1. El mapa coroplético la muestra en gris (el GeoJSON usa `"San Juan"` — no matchea)
2. El Folium filter muestra las sucursales bajo el label incorrecto

**Fix en `PROV_NORM` (gen_nb02.py CELDA 4)**:

```python
'San Juan':'San Juan',
'San juan':'San Juan',   # ← variante real del maestro (j minúscula)
'SAN JUAN':'San Juan',   # ← defensivo
```

**Reclasificación por coordenadas (CELDA 7)** — para sucursales con provincia incorrecta en el maestro:

```python
# 24 bounding boxes (lat_min, lat_max, lon_min, lon_max), más específico primero
_PROV_BBOX = {
    'CABA':    (-34.72,-34.52,-58.54,-58.33),
    'Tucumán': (-28.0, -26.0, -66.5, -64.5),
    'Jujuy':   (-24.5, -21.5, -67.5, -63.5),
    ... # 24 provincias
}
# Para cada sucursal con provincia inconsistente: buscar la correcta por coords
# y reclasificar SIN descartar la sucursal
```

**Regla general**: nunca descartar sucursales solo porque el maestro tiene su provincia mal etiquetada. Usar coordenadas para determinar la provincia correcta. Siempre registrar la variante exacta del nombre tal como aparece en el maestro. Las variantes conocidas del maestro incluyen al menos: `"San juan"` (San Juan), `"Neuquén"/"Neuquen"` (Neuquén), `"Entre Ríos"/"Entre Rios"` (Entre Ríos).

### Multi-canasta en notebook 02 — caché de unión de EANs

El notebook 02 soporta hasta 6 canastas simultáneas. La CELDA 9 usa **un único caché parquet** para la unión de todos los EANs activos:

```python
_cache_key = hashlib.md5('|'.join(sorted(CANASTA_EANS_NORM)).encode()).hexdigest()[:8]
_cache_path = CACHE_DIR / f'hist_union_{_cache_key}.parquet'
```

- **Invalida** cuando cambia el conjunto de EANs (agregar/quitar productos de cualquier canasta)
- **No invalida** cuando solo cambian las cantidades (mismo conjunto de EANs)
- Después de una invalidación, el parquet viejo queda en `_cache/` → se puede borrar manualmente

**Caché de la hoja `analisis_detallado` (nb02 CELDA 19c, desde 2026-10-15)**: `_cache/detalle_<clave>_v1.parquet`
guarda, por mes CERRADO, la mediana de las observaciones sucursal × día por dimensión (nacional, región, provincia,
cadena, tipo de sucursal) × grupo × EAN, más las sucursales de cada grupo (filas con `ean_norm == '*'`). La clave es un
md5 de los EANs de `DETALLE_CANASTA`, la región y el tipo de cada sucursal del maestro, los nombres de cadena
(`NOMBRES_COMPUESTOS`/`NOMBRES_SIMPLES`) y los mapas de provincia/región de la 19b: si cambia cualquiera, se releen los
meses de la ventana (~2-2,5 min por mes en una PC). Las cantidades no entran en la clave.

### EAN format en SEPA — GS1, PLU codes y EAN-12

**EAN-13 GS1 estándar** (prefijo 77-78 para Argentina, 789 para Brasil, 750 para México):
- Son los más comunes en supermercados. Los prefijos 789... y 750... corresponden a producciones de Brasil y México de marcas multinacionales (Dove, Colgate, P&G). SEPA los reporta con sus EANs originales.
- Siempre guardar como string con `dtype={'id_producto': str}` y normalizar con `.str.lstrip('0')` para el merge.

**EAN-12 / UPC** (12 dígitos, sin cero inicial): poco comunes en SEPA. Agregar cero inicial o buscar el EAN-13 equivalente.

**PLU codes (prefijo 27.../28.../29...)**: generados por balanzas en góndola para productos vendidos por peso. Son efímeros — no aparecen en el SEPA histórico de forma consistente. El notebook los detecta y produce una serie histórica vacía, saltando los gráficos de índices con un aviso.

**EANs malformados** (menos de 12 dígitos): no matchean en SEPA. Agregar ceros iniciales hasta 13 dígitos. La normalización `lstrip('0')` hace que sean equivalentes al EAN con ceros.

### Productos sin TACC en SEPA — cobertura y etiquetado

El SEPA contiene productos con denominaciones explícitas "sin TACC" que facilitan armar canastas celíacas. Principales hallazgos para Argentina 2026:

| Categoría | Producto sin TACC con mejor cobertura | Score | Sucursales |
|-----------|---------------------------------------|-------|-----------|
| Pasta | Fideos Mostacholes Blue Patna 500g | 0.927 | 499 |
| Galletitas saladas | Chalitas Happy Food 100g | 0.901 | 545 |
| Galletitas dulces | Smams Chocolate 200g | 0.902 | 526 |
| Polenta/maíz | Prestopronta 730g (naturalmente GF) | 0.915 | 2.423 |
| Almidón | Maizena 500g (naturalmente GF) | 0.908 | 2.458 |
| Aceite | Aceite Oliva Puro sin TACC (etiquetado) | 0.893 | — |
| Atún | La Campagnola sin TACC (etiquetado) | 0.923 | 2.500 |
| Cacao | Nesquik sin TACC (etiquetado) | 0.931 | 2.466 |
| Caldo | Caldo Verdura Knorr (sin gluten) | 0.918 | 2.512 |

**No existe en SEPA con buena cobertura**: pasta sin TACC de arroz, harina de arroz, pan sin TACC. La cerveza sin gluten tampoco aparece en Candidatos.

**Beer/malta**: Heineken y otras cervezas de malta contienen gluten (cebada). La **sidra** (`7790119002370` Saenz Briones 1888, score 0.870) es el sustituto alcohólico sin gluten con mejor cobertura en SEPA.

### EANs PLU (prefijo 27.../28...) — no están en el SEPA histórico

Los productos vendidos por peso en góndola (frutas, verduras, fiambres a granel) usan códigos PLU generados por las balanzas del supermercado. Estos códigos empiezan con **27...** o **28...** y son efímeros — el mismo producto puede tener distintos EANs en distintas sucursales o fechas. Consecuencias:

- No aparecen en el SEPA histórico de forma consistente → `serie_nacional_valida` vacía
- El notebook lo detecta con `_serie_vacia = len(serie_nacional_valida) == 0` y salta las celdas 11/12 con un aviso
- Los EANs GS1 estándar (prefijo 77... o 78...) SÍ tienen historia consistente

### Frescos por peso (balanza) — seguimiento POR TIPO, no por EAN (patrón de nb07)

Ampliación de lo anterior con datos reales (agosto 2026). Los frescos vendidos por peso usan **códigos de balanza internos** con **prefijo GS1 `2`** ("distribución restringida / in-store"), y **cada cadena inventa el suyo**:

| Ejemplo (Frutas/Verduras) | EAN | Cadenas | Sucursales |
|---|---|---|---|
| Tomate Redondo Elegido 1 Kg | `2490127…` | 1 | 983 (solo DIA) |
| Zanahoria Elegida 1 Kg | `2490122…` | 1 | 983 |
| Asado al Vacío Catte 1 Kg | `2406951…` | 1 | 983 |

Medición sobre `canasta_representativa_2026-08.xlsx`: **51% de Carnicería y 20% de Frutas/Verduras** son códigos de balanza, casi todos presentes en **1 sola cadena**. Conclusión: **no existe "el EAN del tomate"** rastreable entre cadenas → el modelo EAN-canasta de nb01/nb02 no sirve para frescos.

**Solución (nb07)**: seguir el **TIPO de producto**, no el EAN. Se juntan por **regla de nombre** todas las variantes que cada cadena publica (`inc`/`exc` regex sobre la descripción, con borde de palabra `\b` para no colar `camPERA` en `pera`), usando el **maestro SEPA completo** (`maestro_sepa_completo.csv.gz`, que trae TODO lo que se vende, no solo el maestro interno curado). El precio del tipo por sucursal-semana = mediana de las variantes presentes, **normalizado a una unidad comparable**:
- `$/kg`: `precio / gramos_presentación × 1000` (los "1 Kg" de balanza ya vienen en $/kg).
- `$/docena` (huevos): `precio / unidades × 12`.

Así el tipo es comparable entre cadenas y provincias aunque cada una use un EAN distinto. Los frescos **empaquetados con marca** (fiambres, huevos de marca) SÍ tienen EAN universal (prefijo 77…) y podrían ir por EAN, pero nb07 los trata igual por tipo para homogeneidad.

#### La trampa: DIA define el tipo por cobertura (auditoría 2026-09-22/23)

DIA tiene ~980-1.040 sucursales en el SEPA (la mayoría en Buenos Aires, CABA y Entre Ríos), y sus
códigos de balanza aparecen en todas. Como el precio nacional es la **mediana entre sucursales** dentro
de cada provincia, en ~50% del costo nacional la mediana ES el precio de DIA. Si DIA vende una
variedad cara de un tipo, esa variedad **es** el tipo:

| Tipo | Producto de DIA que lo definía | Efecto |
|---|---|---|
| Pollo | "Pata de Pollo Atm 1 Kg" (`2406851000004`) a $12.000/kg | Pollo 2,5× el pollo entero del INDEC |
| Suprema/Pechuga | "Suprema Pollo Atm 1 Kg" (`2406848000000`) a $20.500/kg | Suprema 4,1× el pollo entero |
| Carne picada | dos picadas envasadas a $22.475 y $23.980/kg | 1,7× la carne picada común |
| Merluza | "Filet de Merluza Dia 500 Gr" a $31.800/kg | 1,8× el filet fresco |
| Tomate | "Tomate Redondo Elegido 1 Kg" a $5.690/kg | 1,6× el tomate redondo |

Y el filtro de régimen de la lectura (`ancla × RATIO_FRESCO`, ver más abajo), calibrado sobre esos
niveles, descartaba el producto correcto: en Pollo, el "Pollo Embolsado" de DIA a $3.690; en Limón,
el "Limon Granel Dia" a $1.690 (quedaban los jugos de limón, a $5-14 mil/kg).

**Cómo se corrige (nb07 v5.10-v5.11)**, en tres capas (METODOLOGIA §10.16): `EXCLUIR_EAN_FRESCO` saca
EANs puntuales del tipo; `RATIO_FRESCO` recalibrado con precio INDEC / ancla; y
`NIVEL_REFERENCIA_FRESCO` fija el nivel con el precio promedio del INDEC (planilla
`sh_ipc_precios_promedio.xls`, hoja GBA; copia en `data/`). **Antes de publicar un costo en pesos**,
contrastar los frescos con el INDEC: `auditar_salida_nb07.py <Excel> --indec <planilla>` (chequeo 6c).

> **`RATIO_FRESCO` nunca se calibra con UN mes** (v5.13). En los tipos estacionales el cociente precio INDEC /
> ancla va de 0,4 a 2,5 a lo largo del año: el ratio de un solo mes (v5.12) dejaba afuera el 67-95% de la naranja
> de feb-abr. Se elige el ratio que maximiza el *recall* del precio plausible (precio INDEC del tipo / ancla, mes a
> mes desde 2024, dentro de `[ref/K, ref×K]`) con contaminación acotada (share de precios aceptados que son de otro
> producto): Naranja 0,85, Tomate 1,45, Limón 1,01. Cambiarlo relee el SEPA (está en la clave del caché).

### Safeguard MIN_PRODUCTOS_PROPIOS vs N_CANASTA

Cuando `MIN_PRODUCTOS_PROPIOS >= N_CANASTA` ninguna sucursal puede pasar el filtro. El notebook auto-corrige en CELDA 3:
```python
if MIN_PRODUCTOS_PROPIOS >= N_CANASTA:
    MIN_PRODUCTOS_PROPIOS = max(1, N_CANASTA // 2)
```
Para el ICR (51 productos) con `MIN_PRODUCTOS_PROPIOS=15` esto nunca se activa.

### Mapa Folium lazy popup — archivos livianos con popup on-demand

Con 6 canastas × 2.370 sucursales = 14.220 CircleMarkers, el popup HTML inline hace que el HTML pese 40-50 MB. La solución es **lazy popup**: datos almacenados una vez como JSON, HTML construido por JS al hacer click.

**Arquitectura (CELDA 17 de gen_nb02.py):**
1. `_popup_data` dict Python: por (suc_key) → `{nom, bar, prv, cad, tip, can: {col_id: {t, p, n, it[]}}}`. Items compactos: `[nom[:35], cat[:20], qty, price_int, subtotal_int, is_propio]`.
2. Serializado con `json.dumps(..., separators=(',',':'))` y embebido como `<script type="application/json" id="_pd_json">...</script>` — sin escaping JS.
3. JS lee con `JSON.parse(document.getElementById('_pd_json').textContent)` (lazy: solo cuando se necesita el primer popup).
4. Cada CircleMarker tiene popup mínimo: `<div class="lz-pop" data-key="suc_key" data-can="col_id">Cargando...</div>`.
5. Evento Leaflet `popupopen`: `_bPop(key, canasta_id)` construye el HTML desde el JSON → `e.popup.update()`. El atributo `data-built="1"` evita reconstrucción.

**Resultado:** ~5-10 MB en lugar de ~40-50 MB. Misma funcionalidad y estética.

### Regla crítica en gen_nb02.py: no usar triple-quote dentro de cell_code

El código de cada celda está contenido en un string `"""\..."""`. Usar triple comillas dobles `"""..."""` dentro del código (como docstrings) cierra prematuramente el string externo. Siempre usar comentarios de línea `#` en lugar de docstrings dentro de `cell_code("""\...""")`.

> **Alternativa usada en `gen_nb07.py` (2026-09-01)**: definir cada celda con **raw string** `cell_code(r'''...''')`. Preserva `\b`, `\d`, `\n` sin doble-escape (clave para las regex de selección de frescos por nombre) y evita el bug de escape mixto que apareció en las tablas LaTeX de nb02/nb05. Único cuidado: un raw string no puede terminar en `\` ni contener la secuencia `'''`.

### Regiones del maestro de sucursales

`AMBA`, `Pampeana`, `Patagonia`, `Noroeste`, `Cuyo`, `Noreste` (algunas vienen con un espacio duro al final,
`'Noroeste\xa0'`: limpiarlo antes de agrupar). Las sucursales que NO están en el maestro (~540 en oct-26) no tienen
región: el nb02 (19b/19c) la asigna por provincia (código ISO de la columna `sucursales_provincia` del archivo de
precios: `AR-B` Buenos Aires, `AR-C` CABA, ...) y deja `Buenos Aires s/ubicar` para las bonaerenses, que no se pueden
partir entre AMBA y Pampeana sin coordenadas.

**⚠️ La `REGION=AMBA` del maestro no es confiable en Buenos Aires (2026-10-16)**: ~100 sucursales de DIA del interior
bonaerense (Mar del Plata, Tandil, Pergamino, Lobos, Mercedes...; todas con localidad `BUENOS AIRES`) figuran como AMBA,
mientras otras cadenas en esos mismos pueblos figuran como Pampeana. Para el AMBA, usar coordenadas: CABA + sucursales de
Buenos Aires a ≤ 90 km del Obelisco (-34.6037, -58.3816), que toma La Plata (55 km), Luján (67), Campana (72) y Zárate
(81) y deja afuera Lobos, Navarro, Mercedes y Chascomús (92-114 km). Es la columna `amba` de la CELDA 7 del nb02 (BUG-42);
desde el mismo día también la región de la 19b/19c (BUG-43); el nb05 todavía no la usa. Verificación: `docs/auditoria/scripts_nb02_2026-10/validar_amba_maestro.py`.
Tampoco usar `PROVINCIA in (CABA, Buenos Aires)` como AMBA: entra Toledo (Mar del Plata) y la Cooperativa Obrera
(Bahía Blanca).

**Provincia: dos fuentes distintas**. El maestro trae `PROVINCIA` (nombre largo, se normaliza con `PROV_NORM`) y el
archivo de precios trae `sucursales_provincia` (ISO). El Cuadro 1 del nb02 usa el maestro con reclasificación por
coordenadas (polígonos, ver abajo) y descarta las sucursales "CABA" fuera del rectángulo de CABA; la 19b/19c usan el
ISO. En oct-26: CABA 834
sucursales en el Cuadro 1 (canasta Media) y 1.131 en la 19c.

**Provincia por coordenadas: polígonos con tolerancia, no rectángulos (BUG-44, resuelto el 2026-10-16)**. La CELDA 7
del nb02 cambia la provincia de una sucursal solo si está a más de `RECLASIF_TOL_KM` (100) km del polígono de su
provincia declarada en `ar.json` (simplemaps; id = `AR` + letra ISO) y dentro del de otra: 12 sucursales del maestro,
todas errores groseros de carga (DIA de Jujuy declarados San Juan, Posadas declaradas Mendoza). Antes usaba
rectángulos y la primera provincia cuyo rectángulo contenía el punto; eran gruesos: de las 121 reclasificadas, la
mayoría eran errores — Neuquén → La Pampa 47 (Neuquén capital, Centenario, Plottier: el rectángulo de Neuquén termina en −68,5° y la ciudad está en
−68,06°), Entre Ríos → Santa Fe 40 (Paraná), Buenos Aires → Entre Ríos 10 (San Nicolás), Río Negro → La Pampa/Chubut 7
(Catriel, El Bolsón). Algunas son aciertos: 6 DIA de Jujuy que el SEPA y el maestro declaran San Juan. Afecta el
Cuadro 1, los mapas y los rankings provinciales (La Pampa de la Media tenía 55 sucursales en oct-26, 36 de la zona de
Neuquén). El polígono de CABA de simplemaps tiene 18 vértices y se come parte del conurbano: por eso la tolerancia
(con 0 km, 109 sucursales del conurbano pasaban a CABA). El nb05 todavía tiene los rectángulos. Scripts:
`docs/auditoria/scripts_nb02_2026-10/reclasificacion_celda7.py` (la CELDA 7 real sobre el maestro) y
`cuadro1_reclasificacion.py` (el Cuadro 1 de una corrida con la provincia de antes y la de ahora).

**Comercios sin nombre en `NOMBRES_SIMPLES`/`NOMBRES_COMPUESTOS`** (CELDA 4 del nb02) salen como `Cadena <id>`. En
oct-26: "Cadena 24" con 332 sucursales y solo 9 de los 69 productos de la Media (perfil de farmacia/perfumería),
"Cadena 23" (53 sucursales, 3 productos), "Cadena 6" (26, 2). Ninguna está en el maestro de sucursales. Identificarlas
con `comercio_bandera_nombre` del `comercio.csv` del SEPA diario antes de agregarlas a los diccionarios.

### Leer el SEPA por sucursal solo para unos EANs (nb02 CELDAS 19b/19c)

Mismo patrón que las CELDAS 6 y 9 (`pd.read_csv(dtype=str, chunksize=300_000)`), filtrando el chunk por EAN con
**`chunk['id_producto'].apply(normalizar_ean)`**. Medido con oct-26: con `.str.strip().str.lstrip('0')` el pico de la
lectura de un archivo es **+2,1 GB**; con `.apply` es **+0,2 GB** (`docs/auditoria/scripts_nb02_2026-10/bench_lectura_ean.py`).
Después del filtro, guardar en formato compacto (sucursal y EAN como códigos enteros, fecha `AAAAMMDD` entera, precio
float64) y nunca armar textos por observación. Casi todo el tiempo (~70 s por archivo en una PC) es parsear filas de
productos que no se usan: prefiltrar las líneas por EAN antes de `read_csv` lo bajaría ~5x (no implementado).

---

## Lectura eficiente (anti-crash de RAM en Colab)

```python
import zipfile, gzip, shutil, gc
from pathlib import Path
import numpy as np, pandas as pd

_TMP_DIR = Path('/content/tmp_sepa')
_TMP_DIR.mkdir(exist_ok=True)

def cargar_sepa(zip_path, filename):
    """
    Carga un archivo SEPA semestral de forma eficiente.
    Devuelve precios SIN aplicar factor (valores crudos del CSV).
    El factor de conversión se autodetecta y aplica en la celda siguiente.
    """
    # 1. Extraer .csv.gz a disco en streaming (no carga en RAM el archivo comprimido)
    tmp = _TMP_DIR / filename
    with zipfile.ZipFile(zip_path) as z:
        with z.open(filename) as src, open(tmp, 'wb') as dst:
            shutil.copyfileobj(src, dst, length=4*1024*1024)

    # 2. Leer en chunks → reducir a 8 columnas → float32 para precios
    chunks, n_dias = [], None
    with gzip.open(tmp, 'rt', encoding='utf-8') as g:
        for chunk in pd.read_csv(g,
                dtype={'id_comercio':'str','id_bandera':'str',
                       'id_sucursal':'str','id_producto':'str',
                       'sucursales_provincia':'str'},
                chunksize=200_000, low_memory=False):
            price_cols = [c for c in chunk.columns if c.startswith('precio_')]
            if n_dias is None:
                n_dias = len(price_cols)
            prices = chunk[price_cols].replace('NA', np.nan).astype('float32')
            chunk  = chunk.drop(columns=price_cols)
            chunk['precio_promedio']  = prices.mean(axis=1).astype('float32')
            chunk['dias_con_precio']  = prices.notna().sum(axis=1).astype('int16')
            chunk['total_dias_parte'] = np.int16(n_dias)
            del prices
            chunks.append(chunk[['id_comercio','id_bandera','id_sucursal',
                                  'sucursales_provincia','id_producto',
                                  'precio_promedio','dias_con_precio','total_dias_parte']])
    tmp.unlink()
    df = pd.concat(chunks, ignore_index=True)
    del chunks; gc.collect()
    return df
```

> **Por qué streaming a disco**: cargar el .csv.gz completo en BytesIO agota la RAM de Colab (~12 GB). El streaming escribe primero a disco y luego lee en chunks de 200K filas con tipos eficientes.

---

## Anti-OOM: arquitectura df_cov + df_price_stats

El principal riesgo de RAM en `01_exploracion_productos.ipynb` no es la lectura en sí, sino mantener un DataFrame a nivel sucursal (producto × sucursal, ~50M filas) con columnas de enriquecimiento. La solución canónica es agregar inmediatamente.

### El patrón (cell-14)

```python
# ── 1. Merge con geografía SOLAMENTE (no con productos todavía) ───────────────
suc_geo = df_suc_maest[['id_comercio','id_bandera','id_sucursal','PROVINCIA','REGION']].copy()
df_suc_enr = df_suc.merge(suc_geo, on=['id_comercio','id_bandera','id_sucursal'], how='left')
del df_suc, suc_geo; gc.collect()

# ── 2. Normalizar provincia + nombre cadena (vectorizado) ─────────────────────
# ... (código de normalización) ...
# Soltar columnas que ya no se necesitan para reducir el pico de RAM
df_suc_enr.drop(columns=['sucursales_provincia','dias_con_precio','total_dias'],
                inplace=True, errors='ignore')

# ── 3. Estadísticas de precio ANTES de agregar (percentiles a nivel sucursal) ─
df_price_stats = df_suc_enr.groupby('id_producto', sort=False)['precio_promedio'] \
    .agg(precio_promedio='mean', precio_mediano='median').astype('float32').reset_index()
_pq = df_suc_enr.groupby('id_producto', sort=False)['precio_promedio'] \
    .quantile([0.25, 0.75]).unstack() \
    .rename(columns={0.25:'precio_p25', 0.75:'precio_p75'}).astype('float32').reset_index()
df_price_stats = df_price_stats.merge(_pq, on='id_producto', how='left')
del _pq

# ── 4. AGREGACIÓN CRÍTICA: 50M filas → 2M filas ────────────────────────────────
df_cov = (
    df_suc_enr
    .groupby(['id_producto','id_bandera','nombre_cadena','PROVINCIA_NOMBRE','REGION'],
             sort=False, dropna=False)
    .agg(n_sucursales=('id_sucursal','count'), pct_dias=('pct_dias','mean'),
         precio_promedio=('precio_promedio','mean'))
    .reset_index()
)
del df_suc_enr; gc.collect()   # ← LIBERACIÓN CRÍTICA — RAM: ~10 GB → ~600 MB

# ── 5. Merge con metadata de productos (barato: df_cov ya tiene ~2M filas) ────
df_cov = df_cov.merge(df_prod_uniq, on='id_producto', how='left')
```

### Perfil de memoria

| Frame | Filas | Columnas | RAM aprox. | Cuándo se libera |
|-------|-------|----------|------------|-----------------|
| `df_suc` (cargado desde parquet) | ~50M | 9 | ~5 GB | `del df_suc` en paso 1 |
| `df_suc_enr` (pico) | ~50M | ~10 | ~7 GB | `del df_suc_enr` después del groupby |
| `df_cov` (resultado) | ~2M | 13 | ~300 MB | `del df_cov` en cell-21 |
| `df_price_stats` | ~170K | 5 | ~5 MB | persiste hasta export |
| `df_cob` (cobertura producto) | ~170K | ~20 | ~20 MB | persiste hasta export |

> **Regla**: nunca mantener un frame a nivel sucursal (millones de filas) más tiempo del necesario. Agregar a nivel producto inmediatamente.

---

## Estructura real de categorías en el maestro SEPA

El maestro de productos (`Maestro de Productos Interno.xlsx`) organiza los productos en tres niveles: `rubro → categoria → subcategoria`. Los valores de `categoria` son **strings literales del maestro**, no keywords descriptivas del producto. Esto es crítico para configurar correctamente `GRUPOS_CANASTA`.

### Rubros y categorías observados (candidatos con cobertura máxima, abril 2026)

**Rubro: Frescos** (521 candidatos)

| categoria | n_productos |
|-----------|-------------|
| Lácteos | 279 |
| Fiambrería | 185 |
| Pastas y Tapas | 31 |
| Carnicería | 13 |
| Frutas y Verduras | 5 |

> **Trampa crítica**: los productos lácteos tienen `categoria='Lácteos'`, NO `categoria='leche'` o `categoria='queso'`. Las kw de `seleccionar_grupo()` deben coincidir con el valor literal del campo, no con el nombre genérico del producto.

**Categorías con mezcla de tipos (fuente de contaminación)**:

| categoria | Incluye |
|-----------|---------|
| `Fiambrería` | Fiambres + quesos untables + quesos crema |
| `Conservas` | Frutas en almíbar + carnes enlatadas (paté, picadillo) |

Ambas categorías son heterogéneas: agrupan productos de naturaleza distinta bajo el mismo valor. El filtrado por `excluir_kw` no puede resolverlo si opera solo sobre `categoria` — requiere filtrar también sobre `descripcion`.

### Regla para configurar kw en `GRUPOS_CANASTA`

```python
# MAL — busca keywords en descripcion/ingredientes, no en la columna categoria
kw=['leche','yogur','queso','crema','manteca']  # → 0 resultados para Lácteos

# BIEN — usa el valor literal que tiene la columna categoria en el maestro
kw=['lácteos','lacteos']  # → matchea categoria='Lácteos'
```

**Cómo encontrar los valores correctos**: consultar la hoja Candidatos del Excel de salida, columna `categoria`, filtrado por `rubro` de interés.

---

## Trampas conocidas en selección de grupos

### Substring matching en categorías

La función `seleccionar_grupo(df, rubros, kw, excluir_kw, max_n)` filtra por `kw` como substring sobre el nombre de categoría. Esto genera falsos positivos:

| Keyword | Falso positivo / Falso negativo |
|---------|--------------------------------|
| `'te'` | matchea 'Espumantes' (falso positivo) |
| `'crema'` | matchea 'Mayonesa Receta Casera con Crema' (falso positivo) |
| `'postre'` | matchea 'Repostería y Postres' (falso positivo) |
| `'conserva'` | matchea 'Conservas' (incluye carnes enlatadas además de frutas) |
| `'fiambre'` | matchea 'Fiambrería' (incluye quesos untables además de fiambres) |
| `'carne'` | **NO** matchea 'Carnicería' — `'carne' in 'Carnicería'` → `False` (falso negativo) |

### Categorías heterogéneas que requieren `excluir_subcat`

Algunas categorías del maestro SEPA agrupan productos de naturaleza distinta. El `excluir_kw` sobre `categoria` no puede distinguirlos — solo `excluir_subcat` (coincidencia exacta sobre `subcategoria`) los separa:

| categoria | Mezcla | excluir_subcat recomendado |
|-----------|--------|---------------------------|
| `Conservas` | Frutas en almíbar + carnes enlatadas (Patés, Picadillos) | `['Patés y Picadillos', 'Conservas de Pescado']` |
| `Fiambrería` | Fiambres + quesos untables/crema | `['Quesos Untables', 'Quesos Semiduros', 'Quesos Blandos', 'Quesos Duros', 'Quesos Rallados', 'Quesos Especiales']` |
| `Accesorios de Limpieza` | Implementos físicos (cabos, escobas) + accesorios legítimos (escobilla de baño) | `['Palas y Cabos', 'Escobas y Escobillones', 'Plumeros y Limpiavidrios']` |
| `Cuidado del Cabello` | Shampoo/acondicionador (higiene) + coloración/fijación (beauty/styling) | `['Coloración', 'Fijación']` |

**Regla**: siempre revisar el output de cada grupo y añadir `excluir_kw` cuando hay contaminación. Para categorías heterogéneas (`Conservas`, `Fiambrería`) puede ser necesario filtrar sobre la columna `descripcion` además de `categoria`.

### Firma actual de `seleccionar_grupo()`

```python
def seleccionar_grupo(df, rubros, keywords, excluir_kw, max_n, excluir_subcat=None):
    subset = df[df['rubro'].isin(rubros)].copy()
    if excluir_kw and len(subset) > 0:
        excl_mask = subset['categoria'].str.contains(
            '|'.join(excluir_kw), case=False, na=False)
        subset = subset[~excl_mask]
    if excluir_subcat and len(subset) > 0:
        subset = subset[~subset['subcategoria'].isin(excluir_subcat)]
    if keywords and len(subset) > 0:
        incl_mask = subset['categoria'].str.contains(
            '|'.join(keywords), case=False, na=False)
        subset = subset[incl_mask]
    return subset.sort_values('score_cobertura', ascending=False).head(max_n)
```

### Orden de aplicación

1. Filtrar por `rubro`
2. Excluir por `excluir_kw` (substring sobre `categoria` — nivel categoría)
3. Excluir por `excluir_subcat` (coincidencia exacta sobre `subcategoria` — nivel subcategoría, más preciso para categorías heterogéneas)
4. Incluir por `kw` (substring sobre `categoria`)
5. Top N por `score_cobertura`

**Sin fallback**: si el filtro de keywords deja 0 resultados, el grupo queda vacío (preferible a incluir productos incorrectos).

### `excluir_subcat` vs `excluir_kw`

`excluir_subcat` opera sobre la columna `subcategoria` con coincidencia exacta (`.isin()`), lo que permite descartar subcategorías específicas dentro de una categoría heterogénea sin afectar al resto.

```python
# Problema: categoria='Conservas' tiene Duraznos en almíbar Y Patés/Picadillos
# excluir_kw=['paté'] no funciona — busca 'paté' en 'Conservas' → False
# excluir_subcat=['Patés y Picadillos'] funciona — exacto sobre subcategoria
'excluir_subcat': ['Patés y Picadillos', 'Conservas de Pescado']
```

---

## Trampas con dtype category

> **Nota**: el pipeline actual (`df_cov`) usa strings planos, no dtype `category`, por lo que esta trampa ya no aplica al flujo principal. Se documenta por si se re-introduce `category` en futuras optimizaciones de RAM.

### La trampa: groupby sin `observed=True`

Sin `observed=True`, pandas genera **el producto cartesiano de todos los niveles definidos** en cada columna category, no solo los pares que realmente existen en los datos.

**Error real producido en este proyecto:**

```
Unable to allocate 1.33 EiB for array shape (384124754222853120,)
```

El shape astronómico es el producto cartesiano de los niveles de todas las columnas category incluidas en el groupby.

```python
# MAL — explota en RAM con columnas category
df.groupby(['nombre_cadena', 'REGION', 'rubro', 'categoria'])['precio_promedio'].mean()

# BIEN — solo agrupa por combinaciones que realmente existen
df.groupby(['nombre_cadena', 'REGION', 'rubro', 'categoria'], observed=True)['precio_promedio'].mean()
```

**Regla**: todo `groupby()` que incluya al menos una columna de dtype `category` DEBE llevar `observed=True`.

---

## Patrones técnicos del notebook 02 (gen_nb02.py)

### Caché parquet con hash de EANs + cantidades

El caché de la serie histórica se valida con un hash MD5 que incluye **tanto los EANs como las cantidades** de la canasta. Esto garantiza que si el economista cambia la composición (agrega un producto, lo elimina, o cambia su `cantidad`), el caché se invalida automáticamente y se recalcula la serie.

```python
# ❌ Solo EANs — no invalida si cambia cantidad de 4 a 3
_cache_key = hashlib.md5('|'.join(sorted(CANASTA.keys())).encode()).hexdigest()[:8]

# ✅ EANs + cantidades — invalida ante cualquier cambio en la canasta
_cache_key = hashlib.md5(
    '|'.join(f'{k}:{CANASTA[k][1]}' for k in sorted(CANASTA.keys())).encode()
).hexdigest()[:8]
```

El parquet se guarda en `output_canasta/_cache/hist_{hash}.parquet`. Para forzar recálculo: setear `USE_CACHE = False` en CELDA 1.

### Etiquetas de meses en español

Matplotlib usa el locale del sistema para formatear fechas. En Colab (Linux), `%b` produce "Jan", "Feb"... en inglés. Para obtener "ene", "feb"..., usar un formateador manual:

```python
_MESES_ES = {1:'ene',2:'feb',3:'mar',4:'abr',5:'may',6:'jun',
             7:'jul',8:'ago',9:'sep',10:'oct',11:'nov',12:'dic'}

def _fmt_mes_es(x, pos):
    try:
        ts = mdates.num2date(x)
        return f'{_MESES_ES[ts.month]}-{str(ts.year)[2:]}'
    except Exception:
        return ''

ax.xaxis.set_major_formatter(mticker.FuncFormatter(_fmt_mes_es))
```

No usar `mdates.DateFormatter('%b-%y')` — en Colab produce inglés.

### MES_INICIO_GRAFICO auto-adapta

Si el mes configurado en CELDA 1 no existe en la serie histórica (por ejemplo porque la canasta empieza en un mes posterior), el notebook cae automáticamente al primer mes disponible:

```python
_mg = MES_INICIO_GRAFICO
if _mg not in comparativa['mes'].values:
    _mg = comparativa['mes'].min()
    print(f'AVISO: MES_INICIO_GRAFICO {MES_INICIO_GRAFICO} no está en la serie → usando {_mg}')
```

### Nombre de la canasta: ICR

El nombre del índice en gráficos y visualizaciones es **"ICR"** (Índice de Consumo Representativo), no "Canasta SEPA". La variable `COLOR_CANASTA = '#0055A4'` (azul) se mantiene en todos los gráficos.

### Hoja Serie_precios en el Excel de análisis

El Excel `canasta_analisis_YYYY-MM.xlsx` tiene 5 hojas. La nueva hoja **`Serie_precios`** contiene el precio mediano nacional por producto por mes (serie histórica completa desde `MES_INICIO_HISTORICO`):

| Columna | Contenido |
|---------|-----------|
| `mes` | Período YYYY-MM |
| `id_producto` | EAN-13 con ceros iniciales |
| `descripcion` | Nombre del producto (primeros 50 chars) |
| `categoria` | Categoría de la canasta |
| `qty` | Cantidad mensual del producto en la canasta |
| `precio_mediano` | Precio mediano nacional (pesos) |
| `costo_item` | `precio_mediano × qty` |

Permite analizar la evolución individual de cada producto a lo largo del tiempo sin necesidad de reprocesar los ZIPs.

---

## Canasta referencia (otros notebooks)

Los notebooks de evolución temporal usan una **canasta fija de 30 EANs** para comparación temporal consistente. Esto es distinto al enfoque dinámico por cobertura de `01_exploracion_productos.ipynb`.

- **Abril 2026, canasta nacional ponderada**: **$322,566 ARS**
- **Ponderación**: Censo INDEC 2022 (45,892,285 habitantes, 24 jurisdicciones)
- **Rango sucursal**: $271,282 – $358,177
- **Sucursales válidas**: 2,371 (≥ 20 de 30 productos reportados)

---

## IPC INDEC

### Fuente: archivo local `IPC.xlsx` (nombre exacto, case-sensitive en Colab)

El notebook 02 lee el IPC desde un archivo Excel en la carpeta `carga/`. El nombre del archivo es **`IPC.xlsx`** (I mayúscula). En Colab (Linux), el filesystem de Drive es case-sensitive — `ipc.xlsx` no encontraría el archivo.

**Patrón de carga robusto (case-insensitive fallback)**:

```python
_ipc_candidatos = [SEPA_DIR / n for n in ('IPC.xlsx', 'ipc.xlsx', 'IPC.XLSX')]
IPC_PATH = next((p for p in _ipc_candidatos if p.exists()), SEPA_DIR / 'IPC.xlsx')
```

**Estructura real confirmada del archivo** (verificado con `IPC_primerasfilas.xlsx`, 2026-05-29):

| # | Columna | Tipo pandas | Contenido |
|---|---------|-------------|-----------|
| 0 | `date` | `datetime64[us]` | Primer día del mes (p.ej. `2017-01-01`) |
| 1 | `Nivel general` | `float64` | Índice IPC Nivel General |
| 2 | `Alimentos y bebidas no alcohólicas` | `float64` | IPC Alimentos y bebidas |
| 3–13 | 11 categorías más | `float64` | Salud, Transporte, Educación, etc. |

**Punto clave sobre el tipo de la columna `date`**:

Excel almacena las fechas internamente como números seriales. Aunque en la celda Excel se ven como `ene-17` (formato de celda personalizado), `pd.read_excel()` los convierte automáticamente a `datetime64`. Por eso **no se necesita parseo manual de `ene-2017`**. El notebook lo detecta con `pd.api.types.is_datetime64_any_dtype()` y usa directamente `.dt.strftime('%Y-%m')`.

Si por alguna razón el archivo tuviese las fechas guardadas como texto (caso infrecuente), el notebook cae al fallback que parsea `ene-2017` con un diccionario de meses español.

**Valores**: `float64` con punto decimal (ej. `101.5859`). No requieren conversión. El código mantiene `str.replace(',', '.')` por robustez ante versiones con coma decimal, pero no afecta a los valores ya numéricos.

**Cobertura**: datos disponibles desde enero 2017 hasta **marzo 2026** (mínimo). Actualización mensual con un mes de rezago aproximado.

### Fuente alternativa: API pública

```python
import requests

BASE_URL = 'https://apis.datos.gob.ar/series/api/series/'

def get_ipc(serie_id, start_date='2022-01-01'):
    params = {
        'ids': serie_id,
        'start_date': start_date,
        'limit': 1000,
        'format': 'json'
    }
    r = requests.get(BASE_URL, params=params)
    data = r.json()['data']
    return pd.DataFrame(data, columns=['fecha', 'valor'])

# Series útiles:
# 148.3_INIVELGENERAL_DICI_M_26 — IPC General
# 148.3_IALIMENTOSY_DICI_M_26   — IPC Alimentos y bebidas no alcohólicas
# 103.1_I2N_DICI_M_19           — CBA (Canasta Básica Alimentaria)
```

Datos disponibles hasta **marzo 2026**. Actualización mensual. El notebook 02 usa el archivo local (más confiable en Colab que una llamada a API).

---

## Patrones técnicos del notebook 07 (gen_nb07.py) — 2026-09-03

### Lectura SEMANAL + colapso de frescos a TIPO (fix de RAM)
La serie semanal relee todos los ZIPs conservando el **día** (`precio_YYYYMMDD` → fecha → semana).
El universo de frescos por nombre es de **~10.600 EANs de balanza**; arrastrarlos por
(sucursal × EAN × semana) sobre 30+ meses agota la RAM (OOM). **Solución (CELDA 7)**: la función
`_colapsar(_df)` mapea, **en la lectura mensual**, cada EAN fresco a su **TIPO** y normaliza a
$/kg o $/docena (mediana de variantes por sucursal-semana). Así el panel pasa de ~10.800 items a
~255 (**~40× menos filas**). El esquema cacheado es `item/price`; el crudo por-EAN del último mes se
guarda aparte (`datos_ult_raw`) para los diagnósticos por variante.

**Caché por mes (desde v5.8)**: `_cache_nb07/sem_<clave>_v5/<mes>.parquet` (precio por sucursal, una
fila por sucursal × ítem × semana) y `ean_<clave>_v5/<mes>.parquet` (panel por EAN de los frescos:
mediana entre sucursales y cantidad de sucursales, insumo del encadenado). Cada mes cerrado se escribe
apenas se lee, así que una corrida cortada retoma; el mes en curso se lee siempre. Una semana partida
entre dos meses aparece en los dos parquet (cada uno con la mediana de sus días) y se promedian.

**En memoria (desde v5.14)** el panel NO tiene las tres claves de sucursal como texto: lleva `suc` (int32, código
de `SUC_COD`, en el orden de las claves ordenadas) y `semana`/`item` como categóricos (diccionario ya en Arrow, mes
por mes); `sval` agrega `provincia` categórica. Con ~90 M de filas, eso es lo que permite correr en el Colab
gratuito. Todo `groupby` sobre esos frames lleva `observed=True` y los resultados chicos vuelven a texto con
`_sin_cat`. El parquet en disco sigue con las tres claves: los cachés de versiones anteriores sirven igual.

> **La clave del caché** es un md5 del universo de EANs leído —empaquetados de las canastas +
> `EANS_CANDIDATOS` + frescos de `TIPOS_FRESCOS` menos `EXCLUIR_EAN_FRESCO`, que a su vez depende del
> maestro de productos— y de los parámetros de la lectura: `DIA_CIERRE_SEMANA`, `FRESCO_OUTLIER_K`,
> `FRESCO_REGIMEN_K`, `FRESCO_PISO_ANCLA`, `FRESCO_TECHO_ANCLA`, los `rk` por tipo y `RATIO_FRESCO`.
> Cambiar cualquiera invalida el caché y fuerza una relectura completa (~1h20m con 33 meses). No lo
> invalidan: las cantidades de las canastas, `NIVEL_REFERENCIA_FRESCO`, `QUIEBRE_ITEM_K` ni nada de la
> CELDA 8 en adelante. Por eso un producto que se piensa sumar a una canasta conviene agregarlo a
> `EANS_CANDIDATOS` en una relectura previa: después, pasarlo a la canasta no cambia el universo.

### Filtro de outliers intra-tipo (frescos)
Dentro de cada **sucursal-semana**, antes de tomar la mediana de las variantes de un tipo, se
descartan las que caen fuera de `[mediana/K, mediana×K]` con `K = FRESCO_OUTLIER_K` (2.5).
Es la defensa contra el problema real de normalizar $/kg sobre EANs de balanza: un EAN cargado
como "1 kg" cuyo precio en realidad es por unidad o por media horma dispara el $/kg del tipo.

### Selección de frescos por CATEGORÍA (fix de precios inflados)
La selección solo por regex de nombre colaba procesados con el nombre de la fruta/verdura
(jugo en polvo "banana", sazonador "cebolla", ñoquis de "papa", comida de perro sabor "pollo"),
de pocos gramos → `precio/grams×1000` disparaba el $/kg. **Solución (CELDA 4-5)**: se lee
`categoria` del maestro y los candidatos frescos exigen **categoría de fresco real**
(`Frutas y Verduras`, `Carnicería`, `Fiambrería`, `Panificados`, `Pescados y Mariscos`, `Huevos`)
**o** categoría vacía (balanza SEPA-only que no está en el maestro interno), más un piso de
gramaje por tipo (`gmin`, default 250 g; quesos y fiambres 500 g). Mapa `rubro → categorías` en
`_CAT_FRESCO_CFG`.

### Semana que cierra el jueves
La semana **no** es ISO: es una ventana de 7 días que **cierra el jueves** (viernes→jueves),
etiquetada por la **fecha de cierre** (`2026-09-03`). Así el informe que se arma el viernes usa
la última semana completa. Se configura con `DIA_CIERRE_SEMANA` (3=jueves, 4=viernes).

Una semana que cruza dos meses se procesa en dos archivos mensuales. Para no duplicar, cada
semana se asigna a su mes **"dueño"**: el del punto medio de la ventana (cierre − 3 días,
`_mes_de_semana`). Es el análogo al criterio del jueves ISO.

> Ojo: nb02 y nb06 siguen usando **semana ISO** (`%G-S%V`). Solo nb07 usa el cierre en jueves.

**Semana incompleta al final.** El SEPA se publica con rezago, así que la última ventana puede
no estar cerrada: si el último `precio_YYYYMMDD` es el 31/08 y la semana cierra el 03/09, esa
semana tiene 4 de 7 días. nb07 registra `FECHA_MAX_DATOS` durante la lectura y **descarta las
semanas cuyo jueves de cierre es posterior**, avisando por pantalla. Sin esto, la última semana
del informe se publicaría como cerrada con cobertura parcial.

### Detección centavos/pesos: medirla sobre los empaquetados
El SEPA trae los precios en **centavos** hasta 2025A y en **pesos** desde 2025B. nb07 lo detecta
por mes con la regla `mediana > 10.000 → dividir por 100`, pero la mediana se calcula **solo
sobre los EANs empaquetados**, cuyo nivel de precio es estable y conocido (~$1.000-20.000).
Medirla sobre todo el universo sería frágil: los ~10.500 frescos de balanza cotizan **por kilo**
(carnes $10-27k, quesos duros hasta $39k) y arrastran la mediana global cerca del umbral. Un
falso positivo dividiría un mes entero por 100 y rompería la serie de forma silenciosa.

### Ruido de muestreo por provincia
El desvío de la variación semanal escala con 1/√n: **2,3%** en Centro/Pampeana (1.423 sucursales)
contra **12,0%** en Patagonia (38). Como el nacional se pondera por población, una provincia con
2-3 sucursales aportaba su ruido con todo su peso poblacional. Por eso el nacional exige
`MIN_SUC_PROV_ITEM` sucursales por provincia-ítem-semana y winsoriza las medianas provinciales
(`PROV_OUTLIER_K`). Ver METODOLOGIA §10.8.

### Región
`REGION_PROV` mapea provincia → una de 5 regiones (Centro/Pampeana, NOA, NEA, Cuyo, Patagonia).
`costo_suc` gana la columna `region`; se agregan `region_dict` (snapshot) y `serie_region_dict` (semanal).

### Índice TPD de los frescos (v5.13, CELDA 8 bloque 2b)
Insumo: el panel por EAN del caché `ean_<clave>_v5` (mediana entre sucursales `p` y `n_suc` por tipo × EAN ×
semana), filtrado a `n_suc >= FRESCO_EAN_MIN_SUC`. Se pivotea a una matriz semana × EAN (`_w`) por tipo.
- `_tpd_alfa(LP, W)`: efectos fijos de `log p = alfa(semana) + gama(EAN)` por **medias alternadas** (alfa = media de
  log p − gama en la semana; gama = media de log p − alfa en el EAN; W = 1 donde hay dato), hasta que alfa cambia
  menos de 1e-10 o `FRESCO_TPD_ITER` (300) vueltas. Es mínimos cuadrados sin ponderar; no hace falta armar la
  matriz de dummies (con 150 EANs × 52 semanas serían 200 columnas y 7.800 filas por semana y tipo).
- `_tpd_ean(_w)`: para cada semana t estima la ventana `[t−51, t]` y avanza el índice alfa(t) − alfa(t'), t' = la
  última semana con dato (**empalme de movimiento**: lo publicado no se toca). Pide `FRESCO_MIN_EANS_PAR` EANs en
  la semana. Si t' quedó fuera de la ventana arranca un tramo nuevo (`_seg`), como en el encadenado.
- `_meses_nivel(semanas, cob, mes)`: los `FRESCO_NIVEL_MESES` (3) últimos meses hasta `mes` (el de
  `NIVEL_REFERENCIA_FRESCO`, 2026-08) con cobertura normal: `cob` es `_nsuc_is[tipo]` (sucursales con precio válido
  por semana, del bloque 1b) y un mes cuenta si su promedio llega al `FRESCO_NIVEL_COB_MIN` (50%) de la mediana de
  las 52 semanas con dato hasta `mes`. Todo medido hasta `mes`: la elección no cambia con las semanas nuevas.
- `_nivelar(idx, seg, est, meses)`: el nivel de cada tramo es la mediana de estimador / índice en las semanas de
  esos meses; si el tramo no llega, la última semana con estimador. `FRESCO_MES_NIVEL_TIPO` guarda los tipos cuyo
  nivel sale de otros meses (en la v5.12 simulada: Durazno feb-abr, Roast beef may-jul) y el REPORTE los imprime.
- Costo: 59 tipos × ~140 semanas × una ventana cada una, del orden de un minuto en Colab. Con
  `FRESCO_EXPORTAR_METODOS` se calcula también el encadenado (`_encadenado_ean`) para la hoja `Frescos_metodos`.
- Nada de esto invalida el caché (es CELDA 8). Tests: `notebooks/test_frescos_v513.py` (TPD = Jevons en panel
  balanceado, recupera la inflación con rotación de EANs, una semana nueva no revisa la historia) y
  `notebooks/test_encadenado_frescos.py tpd`. El TPD pide `FRESCO_MIN_EANS_PAR` (2) EANs en la semana: con uno solo el
  efecto de semana queda determinado por un EAN suelto (Durazno fuera de temporada: un EAN a $13.400/kg lo hacía
  saltar x3).

### Cobertura mínima de empaquetados y arrastre (v5.13, CELDA 8 bloque 1b)
`N_SUC_ITEM_SEMANA` = sucursales distintas con precio válido (`sval`) por empaquetado y semana. La celda es
faltante si `n < min(MIN_SUC_ITEM_SEMANA, FRAC_SUC_ITEM_TIPICA × mediana de las últimas 26 semanas con dato)`.
Se enmascara en `nac_wide` **y otra vez en `nac_ff` después del arrastre** (`nac_ff.mask(_flaco_is)`, igual que
`_ratio_bad`). Enmascarar solo antes del `ffill` no alcanza: el arrastre rellena la celda con el precio de la
semana anterior, el eslabón de la muestra apareada da 1,0 en plena inflación y al volver el ítem publica todo lo
acumulado. En el panel v5.12 eso le sacaba 30 puntos a la Tecnológica entre ene y mar-24 (tres ítems con dato).

## Patrón técnico del notebook 02 — motor `datos_econometria`
Mismo enfoque de lectura conservando el día, pero **sin frescos** (solo empaquetados: EANs de las
canastas de `Selección` + `PRODUCTOS_ECONOMETRIA`). Agrega por (sucursal, EAN, semana/mes) →
mediana (`precio_med`) y media recortada (`precio_prom`) de los días; imputa faltantes con la
referencia nacional del período; agrega a nacional (ponderado población) / provincia / cadena con
`valor_mediana` y `valor_promedio`. Caché `econ_{hash}.parquet` por mes cerrado. Salida tidy/long.


## Patrones técnicos de los mapas Folium (nb02 y nb05) — 2026-09-09

### Los marcadores los dibuja el navegador, no Python
Un `folium.CircleMarker` con popup y tooltip cuesta **~1,6 KB de HTML** entre el `L.circleMarker`,
su `L.popup`, el `div` del placeholder y el `bindTooltip`. Escribir un marcador por
canasta/producto × sucursal hacía mapas de decenas de MB (48 MB con 19 productos) para mostrar
~2.000 puntos por vez. Ahora el HTML lleva **sólo el JSON de sucursales** (metadata + `la`/`lo` +
el valor de cada canasta/producto) y el JS crea los círculos al elegir el ítem:

- el color se interpola en JS sobre la misma rampa de 7 colores, con el `min`/`max` (percentiles
  5-95) de cada ítem, que viaja en `_cfg_json`;
- una sola `L.layerGroup` que se redibuja, en vez de un `FeatureGroup` por ítem;
- los filtros de cadena/provincia **recortan la lista antes de dibujar** (no esconden nodos del DOM);
- el popup se arma con `bindPopup(function(){...})`, que Leaflet llama recién al abrirlo.

Resultado: ~0,6 MB para 19 productos × 2.000 sucursales; ~0,8 MB para 6 canastas × 2.300.

### El mapa base se elige solo (`TILES_MAPA`)
`TILES_MAPA` (CELDA 1) acepta `'auto'` (default), el nombre de un proveedor o una lista con el orden
a probar. El HTML embarca la lista y el JS agrega el primero; si en **9 segundos** no entró ningún
mosaico —o si fallan 4 seguidos— lo saca y prueba el siguiente. Si no responde ninguno, muestra un
aviso aclarando que los datos están bien y lo que falta es el fondo.

| Orden | Proveedor | Sin API key | Nota |
|---|---|---|---|
| 1 | `esri` — Esri World Light Gray Base + capa de nombres/límites | sí | Gris, parecido al viejo Positron. `maxNativeZoom` 16 |
| 2 | `osm` — OpenStreetMap | sí | **No responde desde la red de INECO** (timeout) |
| 3 | `topo` — OpenTopoMap | sí | `maxNativeZoom` 17 |
| 4 | `carto` — CartoDB Positron | **no** | Sin cuenta estampa *"API key required"*; como eso viaja en un HTTP 200, el fallback no lo descartaría solo → va último a propósito |

Medición de referencia desde la red de INECO (2026-09-09): OSM timeout, Esri 0,3 s, OpenTopoMap
1,2 s, CartoDB 0,2 s.

### La página se comparte por link, así que tiene título y layout de teléfono
El HTML lleva `<title>`, `meta description`, Open Graph y un favicon SVG embebido (sin pedidos
externos), porque folium no escribe nada de eso y la pestaña mostraba la URL cruda. Por debajo de
**700 px** una media query pone los paneles de lado a lado con 6 px de margen, **mueve la leyenda
dentro del panel de filtros** y arranca ese panel plegado (sólo la barra *🔍 Filtros*, se abre
tocándola): con los anchos de escritorio —340/280/260 px— los paneles se salían de la pantalla y se
tapaban entre sí. Además hay un cartel *Cargando el mapa* que se saca cuando aparece el primer
marcador, porque dibujar ~2.000 círculos deja la pantalla vacía unos segundos.

Todo eso vive en `_JS_UI`, un bloque **independiente del JS del mapa**: no depende de él y por eso
se puede inyectar en un HTML ya generado (fue lo que se hizo con el mapa que ya estaba publicado en
GitHub Pages, sin volver a correr Colab).

### Se sacan los CDN que folium engancha y el mapa no usa
Antes de guardar se filtran del HTML las etiquetas de jQuery, Bootstrap (JS y CSS), Font Awesome,
awesome-markers y el `bootstrap-glyphicons` de `netdna.bootstrapcdn.com`: seis pedidos externos que
ninguno de estos mapas necesita. Con los popups armados en JS, jQuery dejó de usarse por completo.

### Cuidado con los escapes al generar estas celdas
El filtrado anterior se escribe con `splitlines()` + `chr(10).join(...)` **a propósito**: dentro de
`cell_code("""...""")` Python consume las barras invertidas, y un `'\n'.join(...)` llega al
notebook como un salto de línea real y rompe la celda (BUG-17/BUG-20, reincidente el 2026-09-09).
