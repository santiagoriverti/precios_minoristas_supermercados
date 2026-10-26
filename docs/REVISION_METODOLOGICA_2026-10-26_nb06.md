# Revisión de datos y método del nb06 frente a su objetivo (2026-10-26)

**Objetivo del notebook** (pedido del usuario): relevar precios y canastas para estimar la **brecha o prima celíaca**,
es decir, cuánto más paga un celíaco que un no celíaco, cómo evoluciona en el tiempo, cómo se distribuye
geográficamente, si la concentración de sucursales la aumenta o la disminuye y cómo se distribuye entre cadenas.

Base: la corrida de Colab del 2026-10-26 (notebook `5938054`), idéntica a la simulación local `sim_v4` (35 hojas contra
`docs/brecha_celiaca/simulacion_2026-10-26/`, 38 contra el Excel de la simulación, mapa, caché y las 170 líneas de la
salida impresa; los 11 gráficos, con los arreglos de presentación, revisados a ojo). Los números de esta revisión salen
de los objetos de esa simulación y del catálogo del SEPA del 22/10/2026, con los scripts `r16`-`r18` de
`docs/auditoria/scripts_nb06_2026-10/` (§5).

## 1. Veredicto por pregunta

| Pregunta | Qué responde hoy el nb06 | Solidez | Lo que falta para responderla bien |
|---|---|---|---|
| ¿Cuánto más paga un celíaco? | Prima de precio de productos equivalentes: **+120% a +125%** en la canasta (ENGHo), +172% en fideos, +26% en almohaditas | Media: buena como prima de precio de envasados en súper; no es el costo de la dieta | El costo en **pesos por mes** (§2.1), el pan y la harina (los ítems con gluten más pesados de la CBA), el **comparador barato** con TACC (§2.2) y la sensibilidad a los pesos de los subtipos (§2.3) |
| ¿Cómo evoluciona? | Serie mensual 2022-2026 (todas las sucursales y panel) y la TPD de robustez | Media-alta 2024-2026; baja en 2023 (precios controlados, cambio de códigos de Molinos) | Que la serie clave represente a todas las cadenas (§2.4: el panel no tiene a DIA) y los **índices de precio de cada lado** (§2.5) |
| ¿Cómo se distribuye geográficamente? | Regiones y provincias con la misma canasta: diferencias chicas (Patagonia +107% a NOA +127%) | Media | Separar **región de cadena**, la **disponibilidad** sin TACC por región (§2.6) e intervalos de confianza |
| ¿La concentración la aumenta o la disminuye? | HHI de empresas por departamento: sin relación (Spearman −0,10) | **Baja** para una conclusión causal; la medición de concentración es pobre | Con efectos de empresa y región, y competencia por radio, sigue sin aparecer efecto (§2.7); hace falta otra medida de mercado |
| ¿Cómo se distribuye entre cadenas? | 3 empresas y 7 cadenas comparables: ChangoMas ~15-20 pp sobre Carrefour y Cencosud | Media-alta para esas cadenas; DIA, Coto, La Anónima y la Cooperativa Obrera quedan afuera o casi imputadas | Comparar **por tipo** y con una canasta núcleo (§2.8); las diferencias se amplían |

**Lo que está bien y no tocaría**: la comparación **dentro de la misma sucursal y por subtipo** (controla el nivel de
precios del lugar y la composición), la canasta fija con reglas reproducibles y empalmes de códigos, la misma canasta
para todos los grupos (BUG-47), la TPD como robustez, las imputaciones a la vista y la validación (simulación = Colab
en tres corridas).

## 2. Hallazgos con los datos

### 2.1 Qué mide la canasta y cuánto paga un celíaco en pesos

La canasta cubre 5 tipos que pesan el **5% del gasto en alimentos** de la ENGHo. La brecha de la canasta (+122,7% en
los últimos 12 meses) es una **prima de precio** ponderada por gasto, no el costo extra de la dieta. Con las cantidades
de la **CBA del INDEC** (gramos por adulto equivalente por mes) y las medianas nacionales de los pares en ago-oct 2026:

| Ítem de la CBA | g/AE por mes | Con TACC ($/100 g) | Sin TACC ($/100 g) | Con TACC ($/mes) | Sin TACC ($/mes) |
|---|---|---|---|---|---|
| Fideos | 1.740 | 382 | 1.031 | 6.653 | 17.947 |
| Galletitas de agua (crackers) | 420 | 812 | 2.060 | 3.412 | 8.652 |
| Galletitas dulces | 210 | 1.096 | 2.287 | 2.301 | 4.804 |
| **Total** | 2.370 | | | **12.366** | **31.402** |

Un celíaco paga **+$19.000 por adulto equivalente por mes** (+154%) solo en esos tres ítems; un hogar tipo 2 (3,09
AE), **+$58.800**. Es una **cota inferior** del costo de la dieta: la CBA tiene además **pan (6.750 g)** y **harina de
trigo (1.080 g)** por AE, el 77% del peso de los cereales con gluten, sin equivalente en la canasta; sus sustitutos
(pan sin TACC, premezclas) tienen primas mayores (la premezcla daba ~+700% en 2026-08, §6.1 de BRECHA_CELIACA). Además,
con cantidades de la CBA la prima es **+154%** y con pesos de gasto ENGHo, **+123%**: la cifra depende de qué
ponderación se elige, y conviene informar las dos.

### 2.2 El comparador con TACC: ¿contra qué paga más?

El lado con TACC son **marcas de primera línea** (regla de §14.3). En DIA, el 22/10/2026, los fideos con TACC más
baratos eran **Cuque $159/100 g, Res $210 y Favorita $240**, contra Lucchetti $370 y Matarazzo $500 (los de la
canasta; mediana de la canasta en todas las cadenas, $398). El Matarazzo sin TACC de DIA costaba $827: la prima es
**+124% contra Lucchetti y +420% contra Cuque**. Para un hogar que compra lo más barato, la prima real es varias veces
la que mide la canasta. El diseño actual mide la prima contra primeras marcas (comparación de "productos equivalentes"),
que es defendible, pero hay que decirlo así y agregar el rango contra la opción más barata.

Esto explica además por qué **DIA casi no forma pares**: vende primeras marcas con TACC, pero sus productos sin TACC de
la canasta aparecen y desaparecen (fideos sin TACC ausentes de sep-2025 a jul-2026), y al lado tiene marcas
económicas con TACC mucho más baratas que las de la canasta.

### 2.3 Los pesos de los subtipos

Dentro de cada tipo, los subtipos pesan igual (promedio geométrico simple). Las brechas de los subtipos son muy
distintas (crackers +165% y snacks +28%; obleas +147% y secas +74%) y su presencia también:

| Tipo (todo el período) | Pesos iguales (hoy) | Pesos por disponibilidad (sucursal-mes) |
|---|---|---|
| Fideos secos | +172,3% | +168,3% |
| Galletitas dulces | +107,8% | **+92,7%** (rellenas 53%, secas 25%, pepas 10%, con chips 7%, obleas 6%) |
| Galletitas saladas y crackers | +84,4% | **+113,9%** (crackers 70%, snacks 30%) |
| Canasta | +116,7% | +118,6% |

En la canasta los efectos se compensan, pero **no en el tiempo**: la canasta del panel por año pasa de 110,7 / 106,1 /
106,7 / 100,3 / 119,9 (pesos iguales) a 106,5 / 106,7 / **96,9** / 96,4 / 117,7 (por disponibilidad): 2024 baja 10 pp.
La disponibilidad no es consumo, pero los pesos iguales tampoco lo son: es una elección que hoy no se informa y mueve
los resultados por tipo y la evolución.

### 2.4 El panel balanceado no representa a todas las cadenas

| | Panel balanceado (la serie clave) | Sucursales con brecha, últimos 12 meses |
|---|---|---|
| Carrefour | 43,0% | 23,7% |
| Cencosud (Vea, Disco, Jumbo) | 20,1% | 11,3% |
| La Anónima | 12,0% | 7,1% |
| Coto | 8,8% | 5,1% |
| ChangoMas | 6,7% | 3,8% |
| **DIA** | **0,0%** | **41,4%** |
| Autoservicios / hipermercados | 29,9% / 22,6% | 58,6% / 12,8% |

La "evolución" del panel es la de las grandes cadenas (Carrefour y Cencosud, el 63%); **DIA no tiene ninguna sucursal**
(sus lados sin TACC entran y salen, así que ninguna llega al 70% de los meses). La serie de todas las sucursales sí
tiene a DIA, pero cambia de universo cuando DIA entra o sale (−16 pp en fideos en ago-2026, AUDITORIA_2026-10-23 §2).
La TPD de todas las sucursales, que maneja la entrada y salida con efectos de celda y de producto, es la mejor
candidata para la evolución "de todo el mercado".

### 2.5 La evolución, separada en los dos precios

Índices de precio de cada lado en los pares del panel (base 2022 = 100, canasta con pesos ENGHo):

| Año | Con TACC | Sin TACC | Sin / con |
|---|---|---|---|
| 2023 | 244 | 252 | 103 |
| 2024 | 894 | 891 | 100 |
| 2025 | 1.128 | 1.098 | 97 |
| 2026 | 1.372 | 1.470 | **107** |

Entre 2022 y 2026 los sin TACC aumentaron 14,7 veces y los con TACC 13,7: la brecha se amplió un 7% relativo, casi
todo en 2026. Por tipo, en 2026 el mayor aumento relativo de los sin TACC es en **saladas (+18%)**; en fideos, los con
TACC subieron más en 2023-2024 (sin/con 88-89: la salida de los precios controlados y los códigos nuevos de Molinos) y
los sin TACC los alcanzaron en 2026 (103). Esta descomposición dice **por qué** se mueve la brecha y hoy no está en las
salidas.

### 2.6 Geografía y disponibilidad

Las brechas regionales son parecidas (+107% a +127%), pero la **disponibilidad** no: de las sucursales que venden un
tipo con TACC, las que también venden su versión sin TACC (últimos 12 meses):

| Región | Fideos | G. dulces | G. saladas | Rebozador | Almohaditas | Ponderado ENGHo |
|---|---|---|---|---|---|---|
| Noroeste | 100% | 98% | 99% | 66% | 100% | 98% |
| Cuyo | 99% | 96% | 96% | 61% | 97% | 96% |
| AMBA | 98% | 93% | 94% | 56% | 100% | 94% |
| Noreste | 100% | 84% | 84% | 42% | 94% | 87% |
| Pampeana | 95% | 75% | 76% | 66% | 95% | 82% |
| **Patagonia** | 96% | 69% | 71% | 66% | 77% | **78%** |

Patagonia tiene **la brecha más baja y la menor disponibilidad**: la brecha se mide solo donde hay los dos lados, y
el costo de no encontrar el producto no aparece en ella. Por cadena, la Cooperativa Obrera no tiene galletitas dulces
ni saladas sin TACC (0%), Coto las tiene en el 57-60% de sus locales y ChangoMas y Coto no tienen rebozador sin TACC.
La disponibilidad es parte de la carga del celíaco y conviene informarla junto a la brecha.

### 2.7 Concentración: no aparece efecto, y la medida es débil

El nb06 mide la concentración con el HHI de empresas por departamento, con cuotas por cantidad de sucursales de las
cadenas que informan al SEPA (no ventas, no superficie, sin almacenes ni dietéticas). Con la canasta comparable de cada
sucursal (últimos 12 meses):

- **Dentro de cada empresa** tampoco hay relación: Spearman Carrefour +0,08 (560 sucursales), Cencosud 0,00 (226),
  ChangoMas −0,14 (81), Coto −0,10 (55); la excepción es **La Anónima, −0,47** (112).
- **Regresión** de log(1 + brecha) sobre el HHI: +0,1 de HHI cambia la brecha −0,35% sin controles (error 0,31),
  **−0,03% con efectos de empresa (0,14)** y −0,25% con empresa y región (0,11; errores agrupados por departamento).
- **Competencia por radio** (empresas rivales a 3 km o menos): Spearman +0,07 en total; La Anónima +0,32.

Separando el **nivel de cada lado** (precio de la sucursal sobre la mediana nacional del mismo subtipo y mes,
`r19`): en La Anónima, donde está más sola sube más el precio **con TACC** (Spearman con el HHI +0,37) que el sin TACC
(+0,16), así que el cociente baja (−0,32); en Carrefour pasa lo contrario, sube más el **sin TACC** (+0,22 contra
+0,09) y la brecha relativa sube (+0,21); en Cencosud, nada. La brecha es un **cociente**: la concentración (o el costo
de llegar a lugares alejados) puede subir cualquiera de los dos precios, y al juntar cadenas los efectos se cancelan.
Conclusión: con esta medida, los datos no muestran que la concentración local mueva la prima en general; para
afirmarlo en un paper hace falta una medida de mercado mejor (radio o isócronas, cuotas por tamaño de local), analizar
cada lado por separado y dentro de cada cadena, y controlar por región.

### 2.8 Cadenas: el resultado más firme, pero comprimido por la imputación

Con la canasta completa, ChangoMas (+140%) supera a Carrefour (+124%) y Cencosud (+125%). Con una **canasta núcleo**
(fideos + galletitas dulces, el 64% del peso, últimos 12 meses):

| Empresa | Núcleo | Fideos | G. dulces | Peso imputado |
|---|---|---|---|---|
| La Anónima | +123,6% | +152,0% | +98,7% | 32% |
| DIA | +132,0% | +167,4% | +101,1% | **74%** |
| Cooperativa Obrera | +141,4% | +180,1% | +107,4% | **84%** |
| Carrefour | +142,4% | +186,1% | +104,1% | 11% |
| Coto | +143,2% | +176,6% | +114,0% | 37% |
| Cencosud | +155,8% | +207,7% | +110,4% | 11% |
| ChangoMas | +176,3% | +230,2% | +129,2% | 21% |

Entre las bien medidas, las diferencias **se amplían**: Cencosud queda 13 pp sobre Carrefour (1 pp con la canasta
completa) y ChangoMas 34 pp. La canasta completa promedia tipos donde las cadenas se ordenan distinto. DIA sigue con el
74% imputado: no se puede comparar con este diseño (§2.2).

### 2.9 La canasta fija frente a la oferta actual

En el catálogo del SEPA del 22/10/2026 (un día del SEPA diario, sin 8 comercios; productos sin TACC reconocidos por la
descripción, así que es indicativo), la canasta fija cubre el **39% de la presencia** (sucursal × producto) de los
fideos sin TACC y el **26%** de las galletitas sin TACC: hay productos difundidos que no están (galletitas sin gluten de
marcas grandes, Happy Food, Yuka y códigos nuevos de marcas que sí están). La canasta se eligió por continuidad
2022-2026, así que con el tiempo representa menos la oferta del momento (sesgo de supervivencia).

### 2.10 Otros puntos a tener en cuenta

- **Canal**: el SEPA son supermercados. Los celíacos compran mucho en dietéticas y almacenes naturistas, que no están.
- **Precio de lista**: no hay promociones (2x1, segunda unidad), más frecuentes en las marcas masivas con TACC.
- **Últimos meses**: ago-oct 2026 salen del SEPA diario, sin 8 comercios (cambio de composición).
- **Envase**: la prima por 100 g incluye que los sin TACC vienen en envases más chicos. Para el consumidor es parte de
  lo que paga; para entender el porqué, conviene separarlo (§3.9 de BRECHA_CELIACA).
- **Inferencia**: solo la TPD tiene intervalos de confianza; las comparaciones entre regiones y cadenas no.
- **Tipo de local**: los hipermercados dan +132,7% contra +124,7% de los supermercados, pero dentro de Carrefour no hay
  diferencia (125,8 / 122,5 / 125,0): es composición de cadenas.

## 3. Recomendaciones, por prioridad

**Sin releer el SEPA (cambios en las CELDAS 8-11):**

1. **Costo en pesos con la CBA**: salida nueva con el costo mensual por adulto equivalente y por hogar tipo de los
   ítems cubiertos, con y sin TACC (§2.1), y su peso en la CBA. Presentar "prima de precio" y "costo extra" por separado.
2. **Índices de precio de cada lado** (con y sin TACC) junto a la brecha, por tipo y canasta (§2.5).
3. **Pesos de los subtipos**: explicitarlos y mostrar la sensibilidad (iguales contra disponibilidad); si hay fuente
   de gasto por subtipo (artículos de la ENGHo: galletitas de agua contra dulces), usarla.
4. **Cadenas y regiones por tipo**, además de la canasta, y la canasta núcleo (§2.8); la TPD por cadena (efectos de
   producto) para separar precio de surtido.
5. **Concentración**: agregar los efectos de empresa y región, la competencia por radio y el análisis de **cada lado
   por separado dentro de cada cadena** (§2.7), e informar el resultado como "sin evidencia de efecto con esta medida",
   no como "la concentración no influye".
6. **Disponibilidad** por región, cadena y mes (§2.6).
7. **Intervalos de confianza** por bootstrap agrupado por sucursal para regiones, provincias y cadenas.
8. Para la evolución, la **TPD de todas las sucursales** junto al panel, ya que el panel no tiene a DIA (§2.4).

**Con relectura del SEPA o fuentes nuevas:**

9. **Comparador con TACC más barato** de cada sucursal (marcas económicas y propias) para dar un rango de la prima
   (§2.2).
10. **Módulo de sustitución**: pan envasado y harina contra pan sin TACC y premezclas, que son la mayor parte del costo
    (§2.1).
11. **Canasta actual** (selección por nombre del último año, `USAR_REGLA_NOMBRE`) como robustez de representatividad
    (§2.9).
12. **Promociones**, si el SEPA crudo trae los precios promocionales.

**Para el paper** (agenda de BRECHA_CELIACA §13): determinantes de la prima con la hedónica (cadena, región,
concentración, tamaño del local), la prima neta de envase, otros canales (dietéticas) y la comparación con el monto
de cobertura que fija el Ministerio de Salud para la Ley 26.588 de celiaquía.

## 4. Lectura de los resultados actuales, con estas salvedades

- En los supermercados que informan al SEPA, un producto sin TACC equivalente cuesta **algo más del doble** que su
  versión con TACC de primera marca (+120% a +125% en la canasta; +172% fideos, +108% dulces, +84% saladas, +84%
  rebozador, +26% almohaditas), y **2,5 veces** si se pondera por las cantidades de la CBA.
- En pesos, solo fideos y galletitas cuestan **+$19.000 por adulto equivalente por mes** (ago-oct 2026); con pan y
  harina, bastante más.
- La prima **no bajó** entre 2022 y 2026: los sin TACC aumentaron un 7% más que los con TACC, casi todo en 2026.
- **Varía más entre cadenas que entre regiones**: las regiones con muchas sucursales están entre +120% y +127%, y
  ChangoMas queda 15-20 pp sobre Carrefour y Cencosud (34 pp en fideos y galletitas dulces). Patagonia, la más baja
  (+107%), es también la de menor disponibilidad: allí el problema es más encontrar el producto que su precio.
- **No hay evidencia** de que la concentración local la mueva en general, con la medida disponible; dentro de algunas
  cadenas sube uno u otro lado del cociente.

## 5. Scripts

En `docs/auditoria/scripts_nb06_2026-10/`, sobre la simulación con el caché (`sim_v4`, igual a Colab):

- `r16_nivel_tiempo_cba.py <sim>`: pesos de los subtipos, composición del panel, índices de precio de cada lado y
  costo con la CBA (§2.1, 2.3-2.5).
- `r17_concentracion_cadenas_disponibilidad.py <sim>`: concentración dentro de empresa, regresión, competencia por
  radio, canasta núcleo por empresa, disponibilidad y tipo de local (§2.6-2.8, 2.10).
- `r18_catalogo_comparador.py <catálogo del SEPA> <canasta_fija_2022_2026.csv>`: marcas con TACC de DIA y cobertura de
  la oferta sin TACC (§2.2, 2.9; catálogo `seleccion/cat_20261022.parquet` de la carpeta de trabajo).
- `r19_niveles_por_lado_concentracion.py <sim>`: nivel de cada lado por sucursal contra el HHI, por empresa (§2.7).
