# Revisión de la corrida nb09 v2 — 01/01/2022 → 15/10/2026 (2026-10-22)

Corrida del usuario en Colab de la versión 2 del nb09 (commit `557556a`, `LECTOR_VERSION = 2`). Insumos: la salida
impresa y los cuatro archivos de `output_trazabilidad/` (`trazabilidad_productos_20220101_20261015.xlsx`, `.parquet`,
`.csv.gz` y `panel_mensual_productos_20220101_20261015.parquet`). No están en el repo.

Resultado: **los seis errores del BUG-45 quedaron corregidos y los números cierran**: los controles internos dan bien
en los 237.894 productos, y el panel coincide exacto con un recálculo desde los archivos crudos del SEPA (4 meses
completos). Quedan observaciones de **método** (el componente comercial del puntaje premia estar en comercios chicos o
que no son supermercados; el regional casi no discrimina) y de **fuente** (desde el 01/08/2026 los datos salen del SEPA
diario vía el nb03, sin 8 comercios). Ninguna obliga a re-correr para usar el ranking tal como está.

## 1. La corrida

| Punto | Resultado |
|---|---|
| Archivos | 115 (58 meses, 2022-01 → 2026-10 al 15/10); 1.747 días con dato; 2 días calendario sin dato (31/10/2023 y 10/05/2026) |
| Relectura | 114 resúmenes de la versión 1 verificados: **0 servían, 114 releídos** (más oct-26, que se relee siempre). Lectura **63,1 min** |
| Motivos | Provincias escritas con el nombre: **ene-may 2022 casi todas** (19-21 nombres, 'Santa fe' incluida); jun-22 → jul-23 'Santa Fe'; ago-23 → sep-26 'Buenos Aires' (y 'Santa Fe' en tramos); **ago-sep 2026 además vacías**. 2023-06_p2: 1 fila repetida. 2024-08_p1: archivo repetido |
| RAM | Lector 1,38-1,95 GB por archivo; notebook ≤ 1,3 GB; libre ≥ 11,0 GB todo el tiempo |
| Fases 2a / 2b | 55 s / 133 s (16 grupos de ~14.900 productos) |
| Factor de precio | 1 en los 1.747 días (ningún archivo en centavos) |
| Filas repetidas | 141.020 en total: **2022-05_p2 111.651**, 2025-08_p1 24.890, 2022-11_p2 1.222, 2024-01_p2 892, 2024-02_p1 874, 2022-10_p1 645, 2023-03_p1 341, 2022-07_p2 267, 2025-07_p2 88 y 1 fila en casi todos los archivos hasta 2024-10 |
| Universo | 4.477 sucursales (3.316 en el maestro con coordenadas), 50 comercios, 69 banderas, **24 provincias** (36 sucursales sin dato), 6 regiones, 340 departamentos, 553 localidades |
| Productos | 237.894: EAN 195.297, internos 42.597, en el maestro 140.745. Con precio todos los días 4.546; todos los días útiles 935; puntaje mediano 6,7; ≥ 50: 2.496; ≥ 75: 20 |

## 2. Lo que corrigió la versión 2 (BUG-45) — verificado

| # | Error de la v1 | En la v2 |
|---|---|---|
| 1 | HHI desbordado | `hhi_cadenas` entre 1/comercios y 1, y entre cuota_max² y cuota_max, en los 237.894 |
| 2 | 27 "provincias" | 24: las listas `provincias_presentes`/`faltantes` usan exactamente las 24; 4 sucursales con el nombre pasado a código, 36 sin dato (no cuentan) |
| 3 | Sucursal × producto repetidos | 0 productos con `suc_diarias_prom > sucursales_distintas`; las repetidas se cuentan una vez (§3.2) |
| 4 | Dos archivos para ago-2024 p1 | Aviso y se usa `COMPLETOb` (15 días) |
| 5 | `es_ean` | 0 EAN con dígito verificador inválido o en rango restringido; 10.154 de balanza/uso interno y 35 que el maestro marca como no EAN quedan internos; 29.650 códigos con guiones |
| 6 | Formato y nombres | Nombres del comercio.csv; listas con '; '; puntaje recalculable desde las columnas (diferencia máxima 0,0059) |

## 3. Controles

### 3.1 Internos (`r1_consistencia.py`) — todos OK

Identidad y orden (ids únicos, ranking 1..N, puntaje no creciente); constantes (1.747 días, 58 meses, 4.477 sucursales,
50 comercios, 69 banderas, 24 provincias); todos los % en [0, 100]; `pct_dias`, `pct_provincias` y
`pct_suc_diaria_periodo` = sus fórmulas; temporales (primer ≤ último día, racha ≤ días, útiles ≤ días, continuos con
racha = 1.747 y sin huecos); sucursales (mínimo ≤ promedio ≤ distintas ≤ total; sucursal-días = promedio × días dentro
del redondeo a 2 decimales); concentración (§2); cantidad de cadenas listadas = `comercios` y la principal está en la
lista; precio del último mes presente si y solo si hubo sucursales en oct-26; `en_universo_nb02` = tener alguna cadena
fuera de {19, 2013, 3001, 4}; recencia (`pct_dias_ultimos_90` > 0 en los 83.803 con último día en oct-26). Panel
mensual: 4.845.653 filas, mismos 237.894 productos; suma de días = `dias_con_precio` y meses = `meses_con_precio` en
todos; sucursal-días dentro del redondeo a 1 decimal; días por mes = días con dato de cada mes.

### 3.2 Contra el SEPA crudo (`r4_crudo.py`)

Recalculado de cero desde los zips semestrales de la PC del INECO (otro código: claves por texto, unión de días con
`bitwise_or`), archivo por archivo y mes por mes, contra lo que imprimió la CELDA 4 en Colab y contra el panel:

| Mes | Archivos | CELDA 4 (días, productos/día, sucursales, pares, repetidas) | Panel: productos | Días por producto | Sucursales/día por producto | Provincias y cadenas fuera de las del ranking |
|---|---|---|---:|---|---|---|
| ene-24 | p1, p2 | **iguales** en los dos (p2: 892 repetidas) | 64.344 = 64.344 | 0 distintos | 0 distintos | 0 |
| ago-24 | p1 `COMPLETOb`, p2 | **iguales** | 67.729 = 67.729 | 0 | 0 | 0 |
| ago-25 | p1, p2 | **iguales** (p1: 24.890 repetidas) | 91.030 = 91.030 | 0 | 0 | 0 |
| jul-26 | p1, p2 | **iguales** | 93.321 = 93.321 | 0 | 0 | 0 |

Qué son las repetidas: ene-24 p2, 891 filas de la "Cadena 2011" (una sucursal; mismos días y mismos precios: copias
exactas) y 1 del comercio 35 (como en casi todos los archivos); ago-25 p1, **una sucursal de ChangoMas** con cada uno de
24.890 productos en dos filas con **días distintos** (la unión de días es lo correcto; contarlas dos veces habría inflado
las sucursales de esos productos). El salto de productos por día dentro de jul-26 (73 mil hasta el 16, 89 mil desde el
17) está en el crudo: un comercio sumó ~16 mil productos a su catálogo.

### 3.3 Contra el nb08 (otro lector)

Los 28 productos de la canasta "Continua 2022" (`canasta_continua_cantidad_07.xlsx`, elegida el 2026-10-20 con los
cachés diarios del nb08): los 28 tienen `continuo_periodo` y el **mínimo diario de sucursales es idéntico** en los 28
(Lucchetti 16, Heineken 25, Capilatis 28, Ades 28...).

### 3.4 Contra la muestra local de la v1 (may-jul 2026)

`trazabilidad_productos_MUESTRA_20260501_20260731.xlsx` (v1 en la PC) contra el panel de la v2 en esos tres meses:
104.157 productos en común, **días iguales en todos**, sucursal-días dentro del redondeo. Los 44 que solo están en la
muestra tienen 0 días con precio (la v1 listaba productos sin ningún precio; la v2 no).

### 3.5 Excel contra parquet (`r3_excel.py`)

Ranking del Excel = parquet en las 67 columnas, salvo dos `id_producto` de más de 32.767 caracteres (límite de una celda
de Excel, ver §4.6) y las listas de provincias vacías (celda vacía en el Excel, '' en el parquet). Continuos_periodo
(4.546, ordenada por mínimo diario de sucursales), Por_categoria (1.662 filas, 231 categorías, ≤ 10 por categoría, todos
EAN), Cadenas (50), Provincias (24 + "Sin dato") y Resumen consistentes con el ranking.

## 4. Hallazgos

### 4.1 El componente comercial premia los comercios chicos y los que no son supermercados (método)

`pct_com_diaria_prom` (cuota diaria de comercios) es el componente que **limita el puntaje de 2.129 de los 2.496
productos con puntaje ≥ 50** (máximo 59,5 contra 75,2 del de sucursales). Cada comercio pesa lo mismo: Carrefour (762
sucursales) igual que un comercio de una sucursal, Mercado Libre (comercio 2013) o una estación de servicio (Axion 23,
Estación Lima 4). Y el denominador cambia mucho con el tiempo: en enero de 2022 publicaron 48 comercios; en octubre de
2026, 17.

| Tramo del ranking (puntaje ≥ 50) | % sucursales | % comercios | Cadenas grandes | Estaciones / ML / 19 | Duplicados 45-46-50 | Resto (chicas) |
|---|---:|---:|---:|---:|---:|---:|
| 1-100 | 64,3 | 44,8 | 9,3 | 1,31 | 2,84 | 13,6 |
| 101-500 | 56,7 | 35,7 | 9,0 | 0,56 | 2,06 | 8,8 |
| 501-1.000 | 51,9 | 32,6 | 8,9 | 0,39 | 1,20 | 5,3 |
| 1.001-2.496 | 39,1 | 28,5 | 8,5 | 0,37 | 1,07 | 4,7 |

"Cadenas grandes" = las 10 con más sucursales o catálogo (Carrefour, ChangoMas, Coto, Libertad, Cencosud, La Anónima,
Cooperativa Obrera, DIA, Toledo y "Cadena 24"). Están en casi todos; lo que separa a los primeros es estar en
comercios chicos, en los repetidos 44/45/46 y 49/50 (abierto desde el 2026-10-21) y en estaciones de servicio. Ejemplo:
Coca Cola 2,25 L (#6, 66% de las sucursales, 54% de los comercios) contra Alimento a base de almendra La Serenísima
(#466, 50% y 33%): la diferencia en comercios son Axion, Estación Lima, Mercado Libre, la 19 y cadenas de 1-10
sucursales. Por eso el top 100 es 56% bebidas y la mejor leche está #86, el mejor aceite #83.

Opciones (decisión del usuario):
- (a) Contar solo comercios con al menos N sucursales activas ese día (p. ej. 10) y fusionar 44/45/46 y 49/50.
- (b) Pesar cada comercio por sus sucursales (se acerca a `pct_suc_diaria_prom`: el componente se vuelve redundante).
- (c) Dejarlo y leer el ranking sabiendo esto (los datos de sucursales y comercios están en columnas separadas).

(a) cambia lo que guarda el lector (hoy guarda cuántos comercios tienen el producto cada día, no cuáles): **relee todo
una vez (~65 min)**. Propuesta para no volver a releer por esto: guardar por producto × día una máscara de bits de los
comercios presentes; con eso cualquier definición de "comercio" se calcula en la fase 2.

### 4.2 El componente regional casi no discrimina (método)

`pct_provincias` (alguna vez en la provincia) vale 100 en la mediana y el percentil 10 de los productos con puntaje
≥ 50 (media 99,9). La cuota diaria (`pct_prov_diaria_prom`, ahora correcta con las provincias normalizadas) va de 31 a
100 (mediana 95,2). Con ella en el puntaje, 94 de los 100 primeros siguen en el top 100, 969 de los 1.000 en el top
1.000, y los productos con puntaje ≥ 50 pasan de 2.496 a 2.209. **No relee** (es cambiar una columna en la CELDA 6).

### 4.3 Desde el 01/08/2026 la fuente es el SEPA diario (nb03): faltan 8 comercios

Agosto, septiembre y octubre de 2026 salen del `03_consolidacion_ultimo_mes.py` (SEPA diario). El diario no trae los
comercios 19, 1000, 2000, 2002, 2005, 2007, 2013 y 3001 (lo dice el nb03), que sí están en los semestrales oficiales
hasta jul-26: las sucursales activas por día pasan de ~3.400 a ~3.030, y algunas sucursales vienen sin provincia (el
nb03 la toma del `sucursales.csv` del diario). Efecto en el ranking: **12.990 productos tienen su último día en
jul-26** (contra 4.000-5.500 en los otros meses de 2026); **3.254 de ellos solo estaban en esos 8 comercios**. Para esos
productos "último día 31/07/2026" no quiere decir que dejaron de venderse. La cuota diaria de comercios no se
distorsiona (el denominador también baja).

Opciones: marcar en el ranking los productos cuyas cadenas dejaron de publicar antes del final (`solo_en_comercios_que_
dejaron_de_publicar`), agregar al Excel una hoja `Dias` con los denominadores diarios (sucursales, comercios,
provincias y productos por día; hoy no se exporta), y reemplazar ago-oct 2026 por el semestral oficial cuando salga.
Nada de eso relee. **Aplicado el mismo día** (pedido del usuario): hoja `Dias`, comercios sin precios en el último mes
en el Resumen y en `Cadenas` (`publica_en_el_ultimo_mes`), y la columna `solo_en_comercios_que_dejaron_de_publicar`.
Falta reemplazar ago-oct 2026 cuando salga el semestral oficial.

### 4.4 La regla "mediana > $10.000 = centavos" (a futuro)

El nb09 decide pesos o centavos por archivo con la mediana del precio de todos los productos; el nb02 (CELDA 9) y el nb08
con la mediana de las observaciones de las canastas. En jul-26 (`r6_umbral_centavos.py`): nb09 **$4.529**, canastas
**$3.420**. Con ~2,5% mensual cruzarían $10.000 hacia 2029: no es urgente, pero la regla tiene fecha de vencimiento. La
CELDA 6 del nb02, el nb05, el nb06 y el nb07 usan EANs de referencia, que tienen el mismo problema más tarde. Arreglo
cuando haga falta: comparar con el mes anterior (como la CELDA 5 del nb08) o con el semestral de 2022 (que ya está en
pesos: factor 1 en todo el período).

### 4.5 Precios simbólicos

`precio_mediano_ultimo_mes` de $1 a $10 en productos con EAN válido y muchas sucursales: panadería de DIA a $5 en 969
sucursales (Baguette 220 g, Pan Dulce, Pan Casero 1 kg), comidas de ChangoMas a $4-10 ("Nuestra Cocina", "Menú
Asociados"), un producto sin descripción a $1 en 91 sucursales de ChangoMas. No afecta el puntaje (no usa precios) pero sí
a quien use esa columna. Opción: columna `precio_simbolico` (mediana ≤ $10) o dejar el precio vacío. **Aplicado**:
columna `precio_simbolico` (≤ `PRECIO_SIMBOLICO_MAX`, $10); el precio queda a la vista.

### 4.6 Códigos con basura de codificación

14 productos de la "Cadena 2003" en feb y jul 2022 son dos tablets Samsung (`8806094046892`, `8806094046908`) con texto
mal codificado pegado al código (12 de más de 20 caracteres, hasta 132.130, y 2 cortos como `8806094046892Â`). Tienen 1-2 días cada uno y están al final del ranking; los
EAN limpios existen (#10.438 y #10.816). Dos no entran en una celda de Excel (quedan cortados). Opción, sin releer: en
la fase 2, pasar un código que empieza con 8-14 dígitos y sigue con caracteres no ASCII a esos dígitos. **Aplicado**:
en la fase 2 esos códigos se unen a su EAN (si el mismo día aparecen las dos formas, cuenta la de más sucursales); los
archivos que los tienen se leen enteros en la fase 2b, porque esas filas están en el grupo de su código original.

### 4.7 Otros

- **Filas repetidas**: las 24.890 de 2025-08_p1 son de **una sucursal de ChangoMas** con cada producto dos veces y días
  distintos en cada fila (la unión es lo correcto). Las 111.651 de 2022-05_p2 no se pudieron mirar (no hay zip de 2022 en
  la PC).
- **Blacklist**: 6 productos marcados en el maestro tienen puntaje ≥ 50 (Vino Toro tinto y blanco 1 L, Smart Water,
  mozzarella Finlandia, zanahoria Knorr, Red Bull 355); todos con rubro "Sin Categoría".
- **Regiones**: 14.995 productos tienen 0 regiones (solo en sucursales de Buenos Aires fuera del maestro, sin
  coordenadas para separar AMBA de Pampeana); 5 tienen 0 provincias. No entra en el puntaje.
- **Día con menos sucursales**: el Resumen dice 870 sucursales activas como mínimo (mediana 3.128). No se puede saber qué
  día desde las salidas de esta corrida: desde la próxima lo dicen el Resumen y la hoja `Dias` (§4.3).

## 5. Lectura del ranking

- Los 2.496 productos con puntaje ≥ 50 son todos EAN del maestro; DIA es la cadena principal (~40-45% de los
  sucursal-días) de los 30 primeros.
- Top 100: Bebidas 56, Almacén 27, Limpieza 9, Perfumería 5, Frescos 2, Congelados 1. Top 1.000: Almacén 332, Bebidas
  259, Perfumería 136, Frescos 122, Limpieza 109.
- 4.546 productos con precio todos los días (todos EAN del maestro); 1.229 de ellos con ≥ 100 sucursales todos los días
  y 238 con ≥ 300: es la base para canastas fijas desde 2022 (Almacén 446, Bebidas 301, Limpieza 203, Perfumería 110,
  Frescos 73, Mascotas 70, Congelados 20).

## 6. Scripts

`docs/auditoria/scripts_nb09_2026-10/`: `r1_consistencia.py` (controles internos), `r2_contenido.py` (puntaje por tipo de
código, top, productos básicos, cadenas, precios, cruces con el nb08 y con la muestra v1), `r3_excel.py` (Excel contra
parquet, hojas de apoyo, comercios repetidos, dígito verificador), `r4_crudo.py` (recálculo desde el SEPA crudo),
`r5_metodo.py` (componentes comercial y regional, corte de ago-2026, blacklist), `r6_umbral_centavos.py` (regla de
centavos), `r7_correr_real.py` (corre las celdas reales del nb09 sobre zips locales de un período corto y compara el
panel con el de Colab: jul-ago 2025, 177.728 filas iguales, con los cambios del §4 aplicados). Todos con
`python -I -X utf8` y las rutas como argumentos.
