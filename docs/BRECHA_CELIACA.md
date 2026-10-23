# Brecha Celíaca (TACC vs sin-TACC) — `06_evolucion_brecha_celiaca`

Documento técnico del **Notebook 06**. Mide la **brecha** de precios entre productos **con TACC** y sus
equivalentes **sin TACC**, dentro de cada supermercado, y cómo se distribuye **en el tiempo** (mensual desde
enero de 2022), **geográficamente** (provincia, región, AMBA) y **entre cadenas**.

Última actualización: 2026-10-23 (tarde) — **primera corrida de Colab con la canasta fija: igual a la simulación** (29
hojas; canasta y estimador validados) y, al revisarla, **BUG-47**: provincias, regiones, empresas, cadenas y sucursales
(mapa) se comparan ahora con la **misma canasta de 12 subtipos** (lo que un grupo no tiene, con la brecha nacional del
período) y la concentración es el **HHI de empresas por departamento** (Georef). Las series nacionales y la brecha por
tipo no cambian. Revisión: `docs/AUDITORIA_2026-10-23_nb06.md`; resultados después del cambio: §14.11; esperados nuevos:
`docs/brecha_celiaca/simulacion_2026-10-23b/`. Antes ese día — **canasta FIJA 2022-2026** (§14: 68 productos con continuidad temporal, geográfica y
por cadenas elegidos con reglas sobre las salidas del nb09 y verificados con precios 2022-2026, empalmes de códigos con
vigencia, pesos ENGHo, qué revisar en la corrida) y **estimador por subtipo** (§14.6: la brecha se calcula por subtipo
dentro de cada sucursal y se agrega subtipo → tipo → canasta, como un índice de precios; §3 queda como la definición
por tipo, que ahora se aplica a cada subtipo). Simulación con los 58 meses del Drive y resultados esperados: §14.10 y
`docs/brecha_celiaca/simulacion_2026-10-23/`. La canasta flexible de agosto de 2026 (§6.1, §12) queda como antecedente.
Antes: 2026-08-27 (revisión exhaustiva nivel-paper del estimador a nivel sucursal: filtro de plausibilidad por regla,
tratamiento del efecto envase, especificación hedónica §3.9).

> **Para retomar**: §14 (canasta vigente y qué revisar cuando vuelva la corrida de Colab), §3 (estimador), §13 (agenda
> para el paper). La lista de productos con sus métricas está en `docs/brecha_celiaca/canasta_fija_2022_2026.csv`.

---

## 1. Objetivo y contexto

La canasta **Celíaca Media** del proyecto (columna `cantidad_05` en nb01/nb02) mostró una
**prima celíaca de ~9%** sobre la canasta Media, aparentemente constante en los últimos años.
Los investigadores (Fernando Delbianco, Andrés) pidieron **estimar cómo se distribuye esa
prima por ubicación geográfica y cadena comercial**, y si se mantiene o se amplía en el tiempo.

El Notebook 06 responde eso de forma **específica y robusta**: en vez de comparar dos canastas
completas (donde la prima queda "diluida" por productos sin dicotomía), compara **solo los
tipos de producto donde existe la dicotomía celiaquía / no-celiaquía**, y reporta la brecha
sobre esa canasta acotada.

---

## 2. Decisiones metodológicas (acordadas con los investigadores)

Del intercambio con Fernando y Andrés (jul 2026), dos decisiones quedan **explícitas**:

### 2.1. Alcance: solo tipos con dicotomía TACC / sin-TACC
> *"Limitarse a productos tacc - sin tacc y aclarar que la brecha que hablamos se hace
> específicamente sobre esa % de la canasta total. Porque si uno sigue extendiéndose […]
> la idea es justamente que no quede maquillada la brecha en esos productos debajo de
> productos de limpieza, accesorios, etc, donde no hay una dicotomía celiaquía/no-celiaquía."*

→ La canasta incluye **únicamente** tipos donde hay sustitución celíaca real (fideos,
galletitas, pan rallado, harina/premezcla, etc.). **No** se incluyen limpieza, higiene, carne,
leche, ni otros alimentos sin dicotomía. La brecha se reporta sobre esa canasta acotada.

### 2.2. Representatividad: "LOS" representativos, no "EL"
> *"Para cada tipo de producto (por ejemplo, paquete de fideos), tomar 2 o 3 como
> representativos, y usar el promedio. Esto te salva en que en todos los períodos, los que
> quedan le salvan las papas al faltante en el promedio. Y este último nos saca de la
> discusión de qué tan dependiente de la elección de 'EL' representativo, a pasar a tener
> 'LOS' representativos."*

→ Cada tipo lleva **2–3 EANs TACC y 2–3 sin-TACC**. El precio del tipo en una sucursal/día es
el **promedio de los representativos presentes** (por lado). Si en esa sucursal/día falta un
representativo, el promedio de los presentes lo cubre → robusto a faltantes y a la elección de
una marca puntual. (Reemplaza la alternativa de splines suavizados para faltantes, que Fernando
mencionó pero valoró menos que este enfoque.)

### 2.3. Robustez / no cherry-picking
> *"La única crítica que uno debe cuidarse es no hacer cherry-picking y que los resultados
> no sean robustos."*

→ La brecha es **intra-sucursal** (controla el nivel de precios de cada sucursal) y se agrega
por **mediana** (robusta) y **promedio con outliers fuera**. La elección final de qué tipos y
EANs entran es del investigador; la plantilla es un punto de partida, no la lista definitiva.

> **Cómo se aplican hoy (2026-10-23)**: "los representativos" son los productos de la canasta fija de §14 (de 2 a 13
> por tipo y lado, en subtipos comparables con la misma composición en los dos lados); el precio de cada lado es la
> **mediana** de los presentes (no el promedio, §3.3) dentro de cada subtipo; y contra el cherry-picking, los productos
> salen de **reglas escritas** aplicadas a todo el SEPA (§14.3), no de una lista curada a mano.

---

## 3. Definición formal de la brecha (estimador canónico)

> **Estado vigente [2026-10-23]**: las definiciones de esta sección (precio del lado = mediana $/100 g de los productos
> presentes, brecha intra-sucursal) se aplican ahora a cada **subtipo** del tipo (spaghetti, crackers, rellenas…), y la
> agregación es por niveles: subtipo (mediana entre sucursales) → tipo (promedio geométrico de sus subtipos) → canasta
> (pesos ENGHo). La lista de productos es la canasta fija de §14 (no "candidatos" curados ni regla por nombre). Detalle y
> motivo: §14.6.

> **Estado [2026-08-27, corregido]**: estimador a nivel sucursal, implementado en `gen_nb06.py`
> (CELDA 7). **Brecha del lado = MEDIANA $/100 g de los candidatos presentes, intra-sucursal, por
> tipo.** El "más barato" (mínimo robusto) se calcula en paralelo **solo como referencia
> ilustrativa** (columna `brecha_min_ilustr`): un run real mostró que **sesga la brecha al alza**
> porque el lado TACC tiene muchos más candidatos por sucursal que el sin-TACC (ver §3.7), así que
> **NO** se usa como primario. Cache-preserving (no toca la lista de EANs).

### 3.0. Notación

- `s` = sucursal · `m` = mes · `k` = tipo de producto (fideos, galletitas dulces, …) · `r ∈ {TACC, sin-TACC}` = lado.
- Cada tipo `k` y lado `r` tiene una **lista fija de EANs candidatos** (definida en la CELDA 1), curada por cobertura y marcas mainstream.
- `P(e,s,m)` = precio observado del EAN `e` en la sucursal `s` durante el mes `m` (mediana de los precios diarios del mes). `gramos(e)` = contenido del EAN según el Maestro.

### 3.1. Precio de cada EAN, normalizado ($/100 g)

$$p(e,s,m) = \frac{P(e,s,m)}{\text{gramos}(e)} \times 100$$

La normalización a **$/100 g** hace comparables presentaciones distintas (500 g vs 1 kg vs 350 g). EANs **sin gramos en el Maestro se excluyen** (§3.8), para que la definición sea siempre en $/100 g.

### 3.2. Qué productos se usan en cada sucursal (surtido heterogéneo)

Cada sucursal ofrece un **surtido distinto**. La regla es **matching flexible a nivel de tipo**, no de EAN:

> En la sucursal `s`, mes `m`, tipo `k`, lado `r`, se usan **los candidatos de la lista que esa
> sucursal efectivamente tiene en góndola ese mes** (con precio y precio plausible). No se exige
> que sea el mismo EAN en todas las sucursales: se compara el mismo **tipo**, con el subconjunto de
> candidatos que cada sucursal stockea.

Esto **maximiza la cobertura** (usa lo que hay en el estante) y refleja el **conjunto de elección real** del consumidor en esa góndola. El costo es que la **composición del surtido varía entre sucursales** → se neutraliza en la etapa econométrica con **efectos fijos de producto/marca** (§3.7), no en la medición.

*(Alternativa descartada — "par fijo emparejado": exigir 1 EAN TACC y 1 sin-TACC idénticos en todas las sucursales daría la comparación más limpia, pero con productos sin-TACC de nicho colapsa el `n` — pan rallado ya está en 119 sucursales con la regla flexible. Inviable con estos datos.)*

### 3.3. Precio del lado = mediana de los candidatos presentes

$$\text{precio}(s,m,k,r) = \operatorname{mediana}_{\substack{e \,\in\, \text{candidatos}(k,r) \\ \text{presentes en } s,m}} \; p(e,s,m)$$

Es el **precio típico** del lado `r` para el tipo `k` en esa sucursal‑mes. Se elige la **mediana** (no el mínimo) porque es **estable a la asimetría en el número de candidatos por lado** — ver §3.7, donde se documenta por qué el mínimo ("más barato") queda descartado como primario. Requisito: al menos **1 candidato de cada lado** presente en `s,m`.

> **Referencia ilustrativa — "más barato disponible"**: en paralelo se calcula el **mínimo robusto**
> (mínimo de los candidatos tras descartar precios fuera de `[p̃/4, p̃·4]`). Tiene una interpretación
> económica atractiva (lo mínimo que paga un consumidor de costo mínimo de cada lado), pero **no es
> el primario** por el sesgo del §3.7. Se reporta como columna `brecha_min_ilustr`.

### 3.4. Brecha intra-sucursal por tipo (estimador atómico)

$$\boxed{\;\text{brecha}(s,m,k) = \frac{\text{precio}(s,m,k,\text{sin-TACC})}{\text{precio}(s,m,k,\text{TACC})} - 1\;}$$

Es el **número atómico** del paper: el sobrecosto celíaco del tipo `k`, dentro de la misma sucursal y mes. Todas las desagregaciones (tiempo, provincia, cadena, concentración) son **agregaciones de este número entre sucursales** (§3.6).

### 3.5. Brecha de canasta por sucursal (secundaria)

Para un resumen agregado por sucursal, se ponderan los tipos con ambos lados por `qty_k`, exigiendo ≥ `MIN_TIPOS` tipos:

$$\text{brecha}(s,m) = \frac{\sum_k qty_k \cdot \text{precio}(s,m,k,\text{sin-TACC})}{\sum_k qty_k \cdot \text{precio}(s,m,k,\text{TACC})} - 1$$

> Los pesos `qty_k` son **ilustrativos** (no fundados en gasto/consumo). Por eso el **resultado
> primario del paper es la brecha POR TIPO** (§3.4); la canasta se reporta como resumen, aclarando
> que la ponderación no está calibrada. Si se consigue una fuente de ponderaciones (gasto celíaco),
> se recalibra.

### 3.6. Agregación entre sucursales (grupos)

Para un grupo `G` (nacional, provincia, cadena, estrato de concentración) y tipo `k`, la brecha del grupo = **mediana** (robusta) y **promedio con outliers fuera** de `brecha(s,m,k)` sobre las sucursales `s ∈ G` con ambos lados. Se reporta `n_sucursales` por grupo/tipo (la hoja `Cobertura` documenta cuántas sucursales ofrecen cada lado).

### 3.7. Robustez y control de composición

- **Por qué mediana y no mínimo (evidencia empírica, run ago-2026)**: el lado TACC tiene **muchos
  más candidatos presentes por sucursal** que el sin-TACC — Fideos 7,7 vs 1,2 · Galletitas dulces
  4,9 vs 1,7 · Saladas 4,6 vs 3,4 · Pan rallado 3,7 vs ~1. El **mínimo de más candidatos es
  mecánicamente más bajo** (E[mín] decrece con `n`), así que el mínimo TACC se hunde más que el
  mínimo sin-TACC → **la brecha se infla artificialmente**. La prueba: la brecha con mínimo se
  dispara **justo donde la asimetría es mayor** (Fideos, asimetría 6,7× → mín +426% vs mediana
  +270%; Saladas, asimetría 1,4× → mín +363% vs mediana +306%). Es un **sesgo estadístico del
  mínimo por número de candidatos**, no un fenómeno económico. La **mediana** es estable a esto
  (su esperanza no depende de `n`) → es el estimador primario. El mínimo queda como
  `brecha_min_ilustr` (cota ilustrativa, con esta advertencia).
- **Efecto tamaño de envase (presentaciones distintas)**: los sin-TACC vienen en **presentaciones
  más chicas** (44–130 g) que los TACC (200–540 g), y por costos fijos de envasado el $/100 g de un
  paquete chico es mayor *aunque el producto no sea más caro*. La normalización a $/100 g corrige la
  diferencia de **primer orden** (500 g vs 250 g), pero no este efecto de **segundo orden**. Doble
  tratamiento: **(a)** el $/100 g es igualmente el **costo real por unidad de alimento** que paga el
  celíaco (relevante para bienestar) → se reporta como brecha descriptiva **con la salvedad
  explícita** de que incluye un componente de envase; **(b)** el modelo hedónico (§3.9) **separa** la
  prima pura de gluten del efecto envase incluyendo `ln(gramos)` como control. El panel conserva
  `grams` por observación para esto. El tipo más afectado es **Galletitas saladas** (sin-TACC de
  50–130 g, tostadas/galletas de arroz) → se reporta como el de menor comparabilidad like-for-like.
- **Efectos fijos de producto/marca** en el modelo de determinantes: los coeficientes de
  concentración, geografía, cadena y tiempo se estiman *neteando* qué surtido stockea cada sucursal
  — así la heterogeneidad de composición (§3.2) no confunde el efecto de interés.
- **Sesgo de selección de sucursales**: la brecha solo se calcula donde hay **ambos lados**; las
  sucursales que ofrecen sin-TACC pueden diferir sistemáticamente (urbanas, grandes, ingreso alto).
  Tras la ampliación del sin-TACC la cobertura subió a **2.532 de 2.742** sucursales (92 %), lo que
  **reduce** mucho este sesgo, pero se **reporta** la cobertura por tipo/grupo y, para el paper, se
  caracterizan las sucursales incluidas vs excluidas (y, si hace falta, corrección tipo Heckman).

### 3.8. Data-quality y exclusiones (regla reproducible, sin cherry-picking)

**Principio (anti cherry-picking)**: no se sacan productos por ser "caros" o "baratos" (eso movería
la brecha a gusto). Solo se excluye por **(i) no normalizable**, **(ii) error de carga** detectado
por una regla simétrica, o **(iii) no-comparabilidad documentada**. Los criterios se aplican por
igual a ambos lados.

1. **No normalizables a $/100 g** (sin presentación en gramos/ml en el Maestro): se filtran
   automáticamente por `grams` (los multipacks tipo "N Un" quedan sin gramos → fuera). Verificado
   que NO hay cálculo erróneo de multipacks (los "6 Un 500 Gr" se codifican como cantidad=6,
   unidad="Un" → `grams` NaN → excluidos, no mal computados).
2. **Errores de carga (regla simétrica e inflación-robusta)** — `FILTRO DE PLAUSIBILIDAD`, CELDA 7:
   cada EAN se mide **relativo a sus pares contemporáneos** — referencia = mediana de los precios-EAN
   dentro de `(tipo, lado, MES)`, **ponderada por producto** (no por sucursal → la cobertura no sesga
   la referencia). Se descarta un EAN si su **precio relativo mediano** en el panel cae fuera de
   `[1/FACTOR_PLAUS, FACTOR_PLAUS]` (=4). Medir DENTRO del mes evita que la inflación 2024-2026
   confunda la banda (una primera versión que usaba precios nominales agrupados en todo el panel
   marcaba de más — 4 EANs — por ese sesgo; corregido). Es simétrico → no favorece ni sube ni baja la
   brecha. Marca solo errores groseros (p.ej. `7798181510441`, Smams chocolate ~8× más barato que sus
   pares); el caro Carrefour ($6.300/100 g, real, 260 sucursales) **se conserva** (sacarlo sería
   cherry-picking). La corrida **imprime la lista** de EANs descartados. `FACTOR_PLAUS` = robustez.
3. **No-comparabilidad documentada** (`EANS_EXCLUIR`, hoy **vacío**): escape hatch para casos que la
   regla no capture. *No se usa para outliers de precio.* La **harina/premezcla** (sustitución, no
   like-for-like) queda comentada por esta razón. **Nota**: NO se saca a mano el Maná (multipack
   131 g): es un producto real y su inclusión da una brecha **más conservadora** (sube la mediana
   TACC) → se conserva; la mediana robusta absorbe su formato chico.

> **Cobertura desigual**: tras la ampliación del sin-TACC (abajo), la cobertura de "ambos lados"
> quedó Fideos 2.458 · Saladas 2.319 · Dulces 1.001 · **Pan rallado 792** — todos utilizables. Se
> reporta `n_sucursales` por tipo/grupo; los tipos con menor `n` (dulces, pan rallado) se leen con
> esa salvedad.

> **Criterio de curación de listas (Palanca 2)**: la comparabilidad *like-for-like* se controla en
> QUÉ EANs son elegibles por tipo/lado, no en la regla de agregación. Regla: el lado **TACC** se
> cura (tiene cobertura de sobra) sacando premium/snacks/outliers; el lado **sin-TACC NO se poda**
> (su cobertura es escasa y **varía mes a mes** en el panel 2024–2026, así que un EAN con baja
> cobertura en un mes puede aportar en otro).
>
> **Ampliación del sin-TACC [2026-08-27]**: con el `Maestro de Productos Interno.xlsx`
> (`data/`, 176.702 EANs) se buscaron todos los productos con indicador "sin TACC / sin gluten" por
> tipo (1.086 en total). Se **ampliaron las 4 listas sin-TACC** priorizando **marcas mainstream y
> marca blanca de cadena** (las de mayor probabilidad de cobertura real): Fideos 8→21 (Matarazzo/
> Gallo GF, Blue Patna, Grandiet, Yuka) · Dulces →23 (línea completa Santa María 200 g, Natuzen,
> Smams, Arrozen) · Saladas 7→20 (Tía Maruca, Carrefour, Granix, Crisppino, Shiva) · **Pan rallado
> 7→20** (Carrefour marca blanca, Preferido, Santa María, Natuzen — antes solo nicho con ~0 cob.).
> El Maestro **no** tiene cobertura, así que cuáles pegan lo revela la corrida (la mediana usa solo
> los presentes). Este cambio **invalida el caché** (nuevos EANs → nuevo hash) → un re-read ~70 min.

> **Trazabilidad (versiones previas)**: el 1er run exigía ambos lados en la **misma sucursal el
> mismo día** para ≥3 tipos → 0 obs por baja cobertura sin-TACC. Una versión intermedia usó
> **pooling por grupo** (base y celíaca podían apoyarse en sucursales distintas del grupo) → daba
> +237% por mezcla de tipos y presentaciones. La versión vigente es **intra-sucursal por tipo, en
> $/100 g**, con la agregación de candidatos por **mediana** (el mínimo se exploró y se descartó
> como primario por el sesgo del §3.7).

**Hallazgo (no es un bug)**: la brecha por producto TACC-sustituible es **grande** (dulces +89%,
fideos +173%, saladas +188%, pan rallado +194% con listas ampliadas — ver §12), muy por encima del
~9% de la canasta **completa** Celíaca Media. Es coherente con lo que buscaba Fernando: el 9%
"maquilla" la brecha real porque promedia productos **naturalmente sin gluten** (carne, lácteos,
verdura) con 0% de prima. Al aislar los productos con dicotomía, la prima real aparece.

---

## 3.9. Especificación econométrica (identificación de la prima y sus determinantes)

La brecha descriptiva (§3.4–§3.6) es el **titular**; la **identificación** de la prima celíaca y de
sus determinantes se hace con una **regresión hedónica de precios** sobre el panel a nivel
**producto × sucursal × mes** (una observación por EAN presente, con su $/100 g y sus gramos):

```
ln(precio_100g)_{i,s,k,t} = β·SINTACC_i + θ·ln(gramos_i)
                            + λ_k (EF tipo) + μ_s (EF sucursal) + τ_t (EF mes) + ε
```

- **β** = **prima celíaca** promedio (en log-puntos, ≈ % con `exp(β)−1`), **neta de tamaño de
  envase** (`ln gramos`), del tipo, de la sucursal y del mes. Los EF de sucursal absorben el nivel
  de precios local y qué surtido stockea cada una (§3.2); los EF de mes, la inflación.
- **`θ·ln(gramos)`** aísla el **efecto envase** (§3.7) → separa "prima pura de gluten" de "costo por
  paquete chico". Se puede refinar con EF de marca/subtipo (o EF de EAN) para acercarse a un
  contraste *within* clase de producto.
- **Determinantes** (cómo cambia la prima): se interactúa `SINTACC` con los ejes de interés →
  `β_HHI·(SINTACC × HHI_localidad)`, `β_reg·(SINTACC × región)`, `β_cad·(SINTACC × cadena)`,
  `β_t·(SINTACC × tiempo)`. Cada coeficiente responde una pregunta del paper (concentración,
  geografía, cadena, evolución temporal) con **errores estándar** (clusterizados por sucursal/mes).
- **Datos**: el panel para la hedónica = caché `brecha_dia_*_v2.parquet` (precio mensual por
  sucursal×EAN) + metadata del Maestro (`grams`, tipo, rol) + covariables de sucursal (provincia,
  cadena, HHI). La hoja `Detalle_producto` es el corte del último mes de ese panel.
- **Robustez**: (i) misma regresión con la muestra restringida a envases comparables (≥150 g) para
  ver cuánto de β es envase; (ii) mediana vs mínimo (§3.7); (iii) `FACTOR_PLAUS` alternativo (§3.8);
  (iv) panel balanceado para la dimensión temporal.

> **Estado (2026-10-23, noche)**: implementada en el nb06 (**CELDA 8b**) la versión de **serie de tiempo**, como
> robustez de la serie descriptiva frente a la imputación de subtipos (§14.12): una regresión por **subtipo**,
> `ln p(i,s,t) = α(s,t) + γ(i) + β(t)·SINTACC(i) + ε`, con efectos fijos de **producto** (absorben marca, presentación y
> `ln gramos`) y de la **celda** sucursal × mes del subtipo (el mismo super, mes y subtipo que compara la descriptiva),
> mínimos cuadrados ponderados (cada producto pesa 1 / productos de su lado en la celda) y errores agrupados por
> sucursal. El nivel del subtipo sale de los efectos de producto (promedio de los sin TACC − promedio de los con TACC,
> cada uno pesado por su disponibilidad en todo el período) y la evolución, de `β(t)`; tipo = promedio geométrico de sus
> subtipos y canasta ENGHo, como la descriptiva. Compara siempre los mismos productos (qué productos tiene cada sucursal
> no mueve la serie) y usa los subtipo-mes con pocas sucursales que la descriptiva imputa. Con efectos fijos de producto
> el nivel **no** está neto del efecto envase (eso pide la versión con `ln gramos` y efectos de subtipo). Siguen
> pendientes: los determinantes (interacciones con HHI, región, cadena) y la prima neta de envase.

---

## 4. Resolución temporal

> **Vigente (2026-10-23)**: resolución **mensual** desde ene-2022 (58 meses a oct-2026). El precio de un producto en
> una sucursal y mes es la **mediana de sus precios diarios** (columnas `precio_YYYYMMDD` de las dos partes del mes).
> Series mensuales con todas las sucursales y con panel balanceado, y tablas por año. Lo de abajo (diaria y semanal) es
> el diseño de agosto de 2026 y ya no se calcula.

Los archivos semestrales del SEPA traen **una columna de precio por día** (`precio_YYYYMMDD`),
así que la brecha diaria sale directo:

- **Diaria**: por cada día con dato. Solo para una **ventana** configurable
  (`VENTANA_DIARIA_MESES`, default 3 meses) para no generar gráficos gigantes.
- **Semanal**: por semana ISO (`%G-S%V`), todo el histórico.
- **Mensual**: por mes, todo el histórico.

El histórico completo se usa para responder *"¿la prima se mantiene o se amplía?"*.

---

## 5. Desagregaciones

> **Vigente (2026-10-23, BUG-47)**: por **subtipo** y **tipo**; **provincia** (polígonos de `ar.json` con tolerancia de
> 100 km), **región** INDEC con **AMBA** por coordenadas, **empresa** (comercio) y **cadena** (bandera), en los últimos 12
> meses y región y empresa por año, todos con la **misma canasta de 12 subtipos** (el subtipo con < 10 sucursales en el
> grupo toma la brecha nacional del período; `peso_imputado_pct`); grupos "confiables": <= 25% del peso imputado y >= 30
> sucursales. **Concentración**: HHI de empresas por **departamento** (Georef de datos.gob.ar; cuota = sucursales) contra
> la canasta comparable de cada sucursal. **Sucursal** (mapa y `Brecha_sucursal`): la misma canasta, con lo que la
> sucursal no tiene completado con la brecha nacional del mes (`peso_propio_pct`). Detalle por producto del último mes.
> Lo de abajo es el diseño de agosto de 2026.

- **Serie temporal** nacional (diaria/semanal/mensual), mediana y promedio.
- **Por provincia** (barras + mapa coroplético de la brecha).
- **Por cadena** (barras, cadenas con ≥5 sucursales).
- **Por concentración de comercios**: brecha vs. nº de sucursales por **localidad**
  (scatter + correlación) → ¿más concentración = más o menos brecha?
- **Detalle intra-sucursal por producto**: precio de **cada EAN en cada sucursal** (último mes).

> **Departamento**: la geolocalización llega a **provincia** (desde el 2026-10-23 por polígonos; antes por bounding
> box) y a **localidad** (campo `sucursales_localidad` del maestro, con su caveat de fiabilidad — muchas vienen `nan`).
> Departamento requeriría un **shapefile departamental** que el proyecto no tiene; queda como mejora futura.

---

## 6. Configuración (CELDA 1)

> **Vigente desde el 2026-10-23.** La CELDA 1 la arma `gen_nb06.py` desde `docs/brecha_celiaca/canasta_fija_2022_2026.csv`
> (la canasta no se edita en el notebook: se edita el CSV y se regenera).

```python
TIPOS = {'Fideos secos': {'peso': 1.503, 'tacc': {EAN: descripción, ...}, 'sin_tacc': {EAN: descripción, ...}}, ...}
GRAMOS = {EAN: gramos, ...}          # presentación verificada contra el SEPA (no del maestro)
VIGENCIA = {EAN: (desde, hasta), ...}  # códigos empalmados (Molinos oct-2023, Wakas jun-2024)
PRODUCTO = {producto: [EAN, EAN], ...}  # códigos de un mismo producto: entra una vez en su lado
SUBTIPO = {subtipo: [EAN, ...], ...}    # la brecha se calcula por subtipo
PONDERACION = 'engho'                 # canasta = promedio de los tipos con los pesos ENGHo de TIPOS
MES_INICIO_HISTORICO = '2022-01'
USAR_REGLA_NOMBRE = False             # la canasta flexible de agosto de 2026, apagada
MIN_SUC_AGG = 30                      # sucursales para que un grupo sea "confiable"
MIN_SUC_SUBTIPO = 10                  # sucursales para que un subtipo entre en su tipo en un mes o grupo
FRAC_SUBTIPO_MES = 0.5                # serie mensual: subtipo-mes con menos de la mitad de sus sucursales -> imputado
FRAC_MESES_PANEL = 0.7                # panel balanceado: sucursal x subtipo en >= 70% de los meses
VENTANA_GEO_MESES = 12                # provincias, regiones, empresas y cadenas: últimos 12 meses (y por año)
CADENAS_FILTRAR = {'19', '2013', '3001', '4', '23', '24'}   # estaciones de servicio, Mercado Libre, farmacias
RECLASIF_TOL_KM = 100; AMBA_RADIO_KM = 90
```

Cambiar un EAN de `TIPOS` cambia la clave del caché (`output_brecha/_cache/brecha_v3_<clave>/`, un archivo por mes) y
relee los 58 meses (~1 h en el Colab gratuito); cambiar gramos, vigencias, productos, subtipos, pesos o descripciones,
no. Los 68 productos y por qué: §14.

### 6.1. Antecedente: plantilla de agosto de 2026 (listas amplias, 4 tipos)

> Reemplazada por la canasta fija de §14 el 2026-10-23. Se deja como registro de las corridas de agosto (§12).

Se precargan **listas amplias** por lado (muchas marcas + presentaciones) para maximizar la
cobertura intra-sucursal: fideos (~10 TACC / 8 sin), galletitas dulces (~8/9), galletitas
saladas (~6/7), pan rallado (~5/7). El tipo **Harina / premezcla** viene **comentado** (es una
sustitución, brecha ~+700%, no like-for-like). Los EANs están en la CELDA 1 de `gen_nb06.py`.
**Ajustar con la hoja `Cobertura`** del primer run (n de sucursales con cada lado por tipo).

| Tipo | qty | TACC (base) | sin-TACC (celíaca) |
|------|-----|-------------|--------------------|
| **Fideos secos** | 4 | Lucchetti Spaghetti · Lucchetti Tallarín · Marolio Tallarines (500 g) | Matarazzo Tirabuzón s/TACC · Grandiet Spaguetti · Blue Patna Dedalitos (500 g) |
| **Galletitas dulces** | 3 | Oreo Chocolate · Trío Scons · Gaona Vainilla c/chips | Santa María Chocolate · Smams Chocolate · Natuzen Vainilla |
| **Galletitas saladas / crackers** | 2 | Saladix Kesitos · Granix c/Salvado · Cerealitas c/Cereal *(trigo)* | Crisppino Queso · Olienka Salada · Shiva Crackers *(arroz)* |
| **Pan rallado / rebozador** | 2 | Preferido 500 g · Favorita 900 g · Mamá Cocina 500 g | Maizena Rebozador · Marvese Rebozador arroz · Bio Pan Rallado |
| **Harina / premezcla** ⚠️ | 2 | Pureza 000 · Blancaflor 0000 · Cañuelas 000 (1 kg) | Blancaflor Premezcla Pizza · Maizena Premezcla Ñoquis · 123 Listo! Pizza |

**Caveats de tipos**:
- **Galletitas saladas**: las sin-TACC del SEPA suelen ser **de arroz** (naturalmente sin
  gluten); por eso el lado TACC usa crackers de **trigo**. Si se considera ambiguo, comentar el tipo.
- **Harina / premezcla** ⚠️: es una **sustitución** (harina de trigo → premezcla), no el mismo
  producto sin gluten. La brecha de este tipo es **grande** (la premezcla es mucho más cara). Es
  un costo celíaco real, pero para una brecha "like-for-like" pura conviene **comentar este tipo**.

Los EANs concretos están en la CELDA 1 de `notebooks/gen_nb06.py` (fuente) y del `.ipynb`.

---

## 7. Outputs (en `MyDrive/carga/output_brecha/`)

| Archivo | Contenido |
|---------|-----------|
| `brecha_mensual_MMAAAA.png` | Canasta mensual: todas las sucursales y panel balanceado, con las sucursales en el eje secundario |
| `brecha_tipo_mensual_MMAAAA.png` / `brecha_por_tipo_MMAAAA.png` | Evolución por tipo y brecha por tipo |
| `brecha_region_anual_MMAAAA.png` | Canasta por región y año |
| `brecha_provincia_MMAAAA.png` / `brecha_empresa_MMAAAA.png` / `brecha_cadena_MMAAAA.png` | Provincia, empresa y cadena en los últimos 12 meses (solo grupos confiables: misma canasta, <= 25% del peso imputado, >= 30 sucursales) |
| `brecha_concentracion_MMAAAA.png` / `mapa_brecha_MMAAAA.png` | Brecha vs. HHI de empresas por departamento (Georef); mapa coroplético por provincia (gris: no confiable) |
| `brecha_tpd_MMAAAA.png` / `brecha_tpd_tipos_MMAAAA.png` | Serie TPD (hedónica, §14.12) con su IC 95% contra la descriptiva: canasta (panel balanceado y todas las sucursales) y cada tipo (panel); marcador vacío = mes con algún subtipo imputado en la descriptiva |
| `mapa_sucursales_brecha_MMAAAA.html` | Mapa Folium por sucursal (último dato de cada una en los últimos 6 meses): color por la canasta comparable (lo que la sucursal no tiene, con la brecha nacional del mes; el popup dice qué parte se midió ahí), productos comparados por subtipo, filtro por cadena, mosaicos Esri y límites del `ar.json` local (popups lazy-load) |
| `brecha_celiaca_YYYY-MM.xlsx` | 38 hojas (la hoja `Leeme` las explica): `Canasta`, `Ponderaciones`, `Cobertura` y `Cobertura_mensual`; **`Brecha_subtipo`**, `Brecha_subtipo_anual` y `Brecha_subtipo_anual_balanc`; `Brecha_tipo`, `Brecha_tipo_mes` y `Brecha_tipo_anual` (y sus versiones con panel balanceado); `Serie_canasta`, `Serie_canasta_balanceada`, `Canasta_anual` y `Canasta_anual_balanceada` (con `peso_imputado_pct`); **serie TPD** (`Serie_TPD`, `Brecha_tipo_TPD`, `TPD_subtipos`, `TPD_anual`, `TPD_productos`; §14.12); provincia, región, empresa y cadena (últimos 12 meses, con y sin desagregar por tipo) y región y empresa por año; `Concentracion` (por departamento); `Brecha_sucursal`, `Comparacion_productos` y `Detalle_producto` (último mes); **`Imputaciones`** (rachas de subtipos imputados en la serie mensual); `Control_EAN` y `Plausibilidad` |

Para la evolución temporal, usar las series del **panel balanceado** (y mirar `Imputaciones`: los tramos con un subtipo
arrastrado varios meses) y compararlas con la **serie TPD** (`Serie_TPD`, `TPD_anual`): donde coinciden, la evolución no
depende de la imputación; para comparar grupos, solo los `confiable`.

---

## 8. Arquitectura (celdas del generador)

`notebooks/gen_nb06.py` → `06_evolucion_brecha_celiaca.ipynb` (14 celdas: una de texto y 13 de código). Qué hace cada
una y qué cambió el 2026-10-23: §14.7. En resumen: CELDA 1 config; 2 setup (Drive, imports); 3 maestros (sucursales,
nombres de comercios y empresas, regiones); 4 la canasta (TIPOS, gramos, subtipos); 5 zips (un archivo por parte de cada
mes); 6 lectura mensual con caché por mes (mediana exacta de los días, líneas filtradas por EAN); 7 vigencias,
plausibilidad, control de identidad, brecha por sucursal × mes × subtipo y tipo, geografía, pesos ENGHo; 8
agregaciones subtipo → tipo → canasta (mes, año, panel, grupos); 8b serie TPD (hedónica, §14.12); 9-10 gráficos y
coroplético; 11 Excel; 12 mapa.

`_pmean` = media con outliers fuera (banda `[mediana/4, mediana×4]`), la misma que nb02/nb05.

---

## 9. Validación

- **Test** `notebooks/test_brecha_celiaca.py` (30 controles): corre las celdas reales sobre un SEPA sintético con cada
  trampa (archivo parcial duplicado, centavos, fila repetida, código viejo congelado, producto con dos códigos, EAN x10,
  salto x2,5, estación de servicio, sucursal web, provincia mal declarada, subtipos con un lado faltante, subtipo-mes
  faltante, caché en dos corridas) y compara cada número con fuerza bruta; desde BUG-47, también grupos, sucursales y
  concentración, y desde la serie TPD, la TPD contra mínimos cuadrados densos (§14.12).
- **Simulación con datos reales** (2026-10-23): las celdas reales con los 58 meses de los zips del Drive coinciden
  **exactamente** con un cálculo independiente (3,4 millones de precios mensuales, 534.456 brechas por subtipo). Tiempo,
  memoria y resultados: §14.10; resultados esperados: `docs/brecha_celiaca/simulacion_2026-10-23/`.
- **Corrida de Colab (2026-10-23)**: igual a la simulación en las 29 hojas (diferencia máxima 1,4e-13): canasta y
  estimador validados en Colab (`docs/AUDITORIA_2026-10-23_nb06.md`). Con BUG-47 el test pasó a 26 controles y la
  simulación con el caché da los esperados de `simulacion_2026-10-23b/` (30 hojas); falta re-correr en Colab (no relee).
- **Serie TPD (2026-10-23, noche)**: test con 30 controles (4 de la TPD); con los datos reales, otro algoritmo
  (`r10_tpd_independiente.py`, LSQR sobre el diseño completo) da lo mismo que la CELDA 8b en los 1.297 subtipo-mes con
  dato propio (diferencia máxima 1,3e-7 pp). Esperados con la TPD: `simulacion_2026-10-23b/` (35 hojas; §14.12).

---

## 10. Limitaciones y mejoras futuras

- Las de §14.8: precios controlados en 2023, pocas marcas del lado sin TACC (y el con TACC de fideos todo de Molinos),
  comparaciones de sustitución (crackers de arroz contra crackers de trigo), pocas sucursales con rebozador, sucursales
  sin coordenadas en 2022, ago-oct 2026 del SEPA diario y precio de lista.
- **Departamento**: falta shapefile departamental (hoy: provincia, región, AMBA y localidad).
- **Imputación de la serie mensual sin límite de meses** (abierto, decisión del usuario): un subtipo-mes con pocas
  sucursales arrastra su último mes válido; hay rachas de 7 a 14 meses (hoja `Imputaciones`, §14.11). Desde el
  2026-10-23 (noche) la serie TPD (§14.12) es la robustez: no arrastra y muestra en qué meses pesa la imputación.
- **Agenda del paper** (§13): selección de sucursales, modelar la concentración (el HHI por departamento ya está), los
  determinantes y la prima neta de envase de la hedónica de §3.9 y deflactar los niveles.
- **Extensiones posibles**: más tipos con dicotomía cuando haya sin TACC continuos (pan envasado, premezclas, alfajores,
  cerveza); una serie de robustez desde 2024 (sin los precios controlados de 2023); pesos por subtipo si aparece una
  fuente de gasto más fina.

---

## 11. Cómo continuar (otra sesión / otra PC)

1. Estado y próximos pasos: bloque ESTADO ACTUAL de `.claude/memory.md` (y su bloque "nb06 — canasta fija").
2. Correr el nb06 en Colab desde el badge del README (Ejecutar todo, sin tocar la CELDA 1).
3. Revisar la corrida: `python -I -X utf8 docs/auditoria/scripts_nb06_2026-10/s16_comparar_colab.py <Excel>
   docs/brecha_celiaca/simulacion_2026-10-23b` (con los mismos zips y el notebook vigente, 35 hojas iguales) y la lista
   de §14.9.
4. Para cambiar productos o reglas: scripts s7-s10 de `docs/auditoria/scripts_nb06_2026-10/` → CSV →
   `python notebooks/gen_nb06.py` → `python notebooks/test_brecha_celiaca.py` → simulación s11/s12 (s14/s15 para no
   releer) → nueva carpeta de resultados esperados → commit de CSV, generador, `.ipynb` y docs juntos.

---

## 12. Resultados de referencia (run real, agosto 2026 — **selección por nombre + maestro completo**)

Estimador **primario = mediana** (§3.3); candidatos sin-TACC seleccionados **por NOMBRE** (regla
reproducible, §3.8bis) sobre el **maestro fusionado** (interno 176.702 + `maestro_sepa_completo`
27.287 = **203.989 EANs**), con **gramos del campo o parseados de la descripción**. Filtro de
plausibilidad (§3.8). **250 EANs de config** (TACC curado + sin-TACC por regla). 2.441.527 obs
sucursal×EAN×mes · **2.543 de 2.742 sucursales con ≥1 par** · 32 meses (2024-01 → 2026-08).

**Brecha por tipo (intra-super, $/100 g, mediana):**

| Tipo | TACC | sin-TACC | Brecha (mediana) | "más barato" (ilustr.) | n suc. (ambos) |
|---|--:|--:|--:|--:|--:|
| Galletitas dulces | 692,4 | 1.658,3 | **+147,6 %** | +182,7 % | 1.343 |
| Pan rallado | 314,3 | 947,1 | **+187,9 %** | +186,8 % | 727 |
| Galletitas saladas | 501,3 | 1.549,0 | **+190,8 %** | +167,6 % | 1.335 |
| Fideos secos | 272,8 | 940,0 | **+239,1 %** | +258,8 % | 1.291 |

**Cobertura ambos lados (casi universal salvo pan rallado)**: Fideos 2.460 · **Dulces 2.525** ·
Saladas 2.516 · Pan rallado 792. **Canasta acotada:** +176,2 % (ago-2026); serie +169,8 % (ene-2024)
→ +176,2 % (ago-2026) = **+6,3 pp (prácticamente plana)**. Prov. menor: Santa Cruz (+131 %) · mayor:
Córdoba (+206 %). El mapa incluye **19 cadenas** con **DIA (1.001 sucursales, la más grande)**.

> **La selección por nombre (maestro SEPA completo) capturó el surtido celíaco real** — antes DIA
> (hard-discount, 1.038 sucs) daba brecha nula porque sus EANs celíacos (Wakas 400 g, etc.) no
> estaban en el Maestro interno curado. Ahora la cobertura de dulces saltó de ~1.000 a **2.525**
> sucursales. **Falso positivo corregido**: la primera regla de dulces metía yerba/mermelada/
> caramelos por matchear el sabor suelto ('naranja','frutilla'); se corrigió exigiendo un sustantivo
> de galletita. Los `$/100 g` de sin-TACC subieron al incluir toda la góndola celíaca real.

> **El filtro de plausibilidad descartó 3 EANs** (transparentes en la salida): Smams chocolate
> ($184/100 g, error de carga) y **dos "sin TACC Matarazzo" (`7790070321800`, `7790070321855`)
> con precio de fideo convencional (~$207/100 g)**. *Corrección del 2026-10-23 (§14.4)*: no estaban mal
> etiquetados; son los códigos sin TACC de Matarazzo hasta oct-2023, que después quedaron con el precio
> congelado en ~100 sucursales (el filtro hizo bien en sacarlos de 2024-2026, pero no son fideos comunes:
> en 2022 costaban el doble o el triple del Matarazzo común en las mismas sucursales).
> Dulces cambió de +89 % (Maná fuera) a **+66 %** (Maná dentro): sensible a un producto porque el
> TACC dulces tiene pocos candidatos; se conserva Maná (más conservador) y la **hedónica (§3.9)** con
> control de gramaje es la cifra identificada.

> **La ampliación del sin-TACC bajó las brechas** (Fideos +270→+173 %, Saladas +302→+188 %, Pan
> rallado +362→+194 %) y **multiplicó la cobertura** (ambos lados: Fideos 963→2.458, Saladas
> 621→2.319, **Pan rallado 119→792**). Interpretación: la brecha anterior estaba **sesgada al alza**
> porque el sin-TACC eran solo productos de **nicho caros**; al sumar marcas mainstream y marca
> blanca (más baratas y de más cobertura), el precio sin-TACC representativo es menor → la brecha
> "verdadera" es más baja y con base empírica mucho más sólida. Además min y mediana ahora casi
> coinciden (menos asimetría de candidatos) → resultado robusto.
>
> **Cobertura sin-TACC (con qué EANs pega cada tipo)**: Fideos = **Matarazzo GF** (741+727 suc.,
> 500 g) · Dulces = **Santa María** línea 200 g (limón 499, vainilla 444…) · Saladas = Crisppino/
> Shiva/Tía Maruca/Carrefour (envases 50–130 g → efecto envase fuerte, §3.7) · Pan rallado =
> **Preferido** (661) + **Carrefour marca blanca** (436+149+91), 350 g.

---

## 13. Agenda metodológica para el paper (rigor científico — PENDIENTE de revisión)

> Objetivo: este pipeline es la **base empírica** de un paper sobre la brecha celíaca
> y sus determinantes (**tiempo, concentración de mercado, geografía, cadena**). Antes de
> publicar hay que resolver estas amenazas a la validez. Nada de esto está resuelto aún;
> se registra para la revisión metodológica futura.

**A. Validez de constructo (qué se mide).**
- La brecha compara el **sustituto sin gluten** vs el producto TACC de referencia, **no** el
  "mismo producto sin gluten" (no existe fideo de trigo sin TACC). Declararlo explícitamente.
- Selección de EANs por **cobertura** (`n_sucursales`), no por participación de consumo. SEPA
  no tiene cantidades vendidas → riesgo de sesgo de selección. Buscar ponderadores (canasta
  INDEC, gasto celíaco) o justificar la selección.
- Falta un **criterio de matching reproducible** TACC↔sin-TACC (tipo + presentación + calidad).

**B. Medición del precio ($/100 g).**
- Depurar los **2 EANs sin presentación** (`7790040133471`, `7798079230062`) que hoy entran
  sin normalizar ($/paquete) y distorsionan Galletitas dulces.
- El **efecto tamaño de envase**: los sin-TACC vienen en presentaciones más chicas, que suelen
  tener mayor $/100 g por sí mismas. Parte de la brecha podría ser efecto envase, no efecto
  gluten → controlar por gramaje de la presentación.
- La **mediana-de-medianas por chunk** (CELDA 6) es una aproximación; para el paper, recalcular
  con mediana exacta o media ponderada por días.

**C. Sesgo de selección de sucursales (validez externa).**
- La brecha solo se calcula donde hay **ambos lados** (119–964 de 2.742 sucursales). Las
  sucursales que ofrecen sin-TACC pueden ser sistemáticamente distintas (urbanas, grandes,
  ingresos altos) → sesgo. Considerar corrección tipo Heckman o reportar el sesgo explícito.
- **Pan rallado n=119**: potencia estadística baja; reportar con salvedad o excluir de agregados.

**D. Comparaciones entre grupos (efecto composición).**
- La canasta por sucursal suma **solo los tipos presentes** → comparar cadenas/provincias mezcla
  composición distinta (es lo que hace ver a Carrefour Express en +21 %). Para el paper: fijar la
  canasta (mismos tipos) o estimar un modelo con **efectos fijos por tipo y por tiempo**:
  `brecha_ist = α + β·concentración + γ·región + δ·cadena + FE_tipo + FE_mes + ε`.

**E. Dimensión temporal.**
- La brecha en % ya es relativa, pero para "cómo cambia en el tiempo" analizar también niveles
  **reales** (deflactar $/100 g). Cuidar que la entrada/salida de EANs no confunda la evolución
  (índice encadenado / panel balanceado).

**F. Concentración de mercado.**
- Reemplazar la métrica cruda (`localidad` / `n_sucursales`, corr. −0,20) por un **HHI** por
  mercado geográfico bien definido, y modelarlo (no solo correlación).

**G. Reproducibilidad.** Ya versionado en git (generador + listas de EANs). Falta: fijar y
  documentar fecha/versión de descarga SEPA usada para cada corte del paper.

> **Qué resuelve la canasta fija de §14 (2026-10-23)**: A (criterio de matching reproducible: reglas escritas, misma
> composición por subtipo en los dos lados), B en parte (gramos verificados por producto; los EANs sin presentación ya
> no entran; mediana mensual exacta en lugar de la mediana de medianas por bloque), D (la canasta de un grupo es el
> promedio ponderado de las brechas por tipo: no la mueve qué tipos tiene cada sucursal), E (mismos productos todo el
> período + panel balanceado por sucursal × tipo) y G (la canasta vive en el repo y no depende del maestro del Drive).
> **Con BUG-47 (2026-10-23, tarde)**: D también entre grupos (la misma canasta de 12 subtipos en provincias, regiones,
> empresas, cadenas y sucursales; lo que falta, con la brecha nacional del período) y F en su parte descriptiva (HHI de
> empresas por departamento de Georef; Spearman por sucursal −0,11: sin relación a la vista).
> Siguen abiertos: C (selección de sucursales), modelar F, la hedónica de §3.9 y deflactar los niveles.

---

## 14. Canasta fija 2022-2026 (2026-10-23)

> **Estado**: implementada en el nb06 (`gen_nb06.py` arma `TIPOS`, `GRAMOS`, `VIGENCIA`, `PRODUCTO` y `SUBTIPO` de la
> CELDA 1 desde `docs/brecha_celiaca/canasta_fija_2022_2026.csv`). **Falta la primera corrida en Colab**: relee los 58
> meses (ene-2022 → oct-2026) una vez. Reemplaza la canasta flexible de agosto de 2026 (§6.1 y §12, que quedan como
> antecedente). Scripts de la selección y de la simulación: `docs/auditoria/scripts_nb06_2026-10/` (s1-s14 y su README).

### 14.1 Por qué una canasta fija

La canasta flexible (listas curadas más todos los productos del maestro cuya descripción decía "sin TACC", ~250 EANs)
servía para la foto de un mes pero no para comparar en el tiempo, entre regiones y entre cadenas:

1. **La composición cambiaba sola.** La mayoría de los candidatos sin TACC tenía historia corta. Las líneas sin TACC de
   marcas masivas (Matarazzo en sep-2023, Exquisita y La Salteña en nov-2023/feb-2024, Oreo en abr-2024, Preferido en
   abr-2025, Terrabusi en jul-2025) entraron con precios más bajos que las marcas celíacas y bajaron la mediana del lado
   sin TACC: parte de la "evolución" de la brecha era la entrada de productos, no un cambio de precios.
2. **Dependía del Drive.** Los candidatos salían de `maestro_sepa_completo.csv.gz`, que el script 03 reescribe cada mes
   con lo que se vende ese mes: cambiaban los candidatos (y la clave del caché, que releía todo) sin tocar el notebook.
3. **La regla por nombre fallaba en los dos sentidos.** Se perdía las grafías del SEPA ("S TACC" de Carrefour, "LIBRE
   D/GLUTEN", "S-TACC", la marca Glutal) y el Maestro interno tiene descripciones viejas de códigos reutilizados y
   "sin TACC" mal puestos (14.4).

Una canasta fija de productos que existen todo el período, con la misma composición de subtipos de los dos lados, mide
el cambio de precios de **los mismos productos** y se puede comparar entre lugares y cadenas.

### 14.2 Fuentes

| Fuente | Para qué |
|---|---|
| nb09, corrida al 22/10/2026 (`trazabilidad_productos_20220101_20261022.parquet` y `panel_mensual_productos_20220101_20261022.parquet`) | Cobertura mensual de cada producto (sucursales con precio por día, promedio del mes) de ene-2022 a oct-2026; provincias, comercios, cadenas grandes y cadena principal en todo el período |
| SEPA diario del 22/10/2026 (`productos.csv` de cada comercio) | La descripción que publica cada cadena: marca "sin TACC", identidad de cada código, presentación |
| Zips semestrales 2022A → 2026B del Drive (`MyDrive/carga/`, los mismos que lee el nb06; bajados el 23/10/2026; el 2026B trae jul-2026 y ago-oct 2026 del SEPA diario hasta el 22/10) | Precio mensual por sucursal × EAN (mediana exacta de los días) para verificar identidad, gramos, empalmes y cortes de código en ene-2022 → oct-2026, y para simular el nb06 completo |
| `canasta_representativa_2026-10.xlsx` (nb01) | Referencia: la canasta Celíaca Media (`cantidad_05`, 71 productos, casi todos naturalmente sin gluten: aceite, arroz, leche…) explica por qué su prima es ~9% y no se usa para elegir |
| ENGHo 2017/18 (INDEC, microdatos de gastos; `IPC_jubilados/data/cache/`) | Peso de cada tipo en el gasto de los hogares |

### 14.3 Reglas de selección (en orden)

1. **Tipos**: con dicotomía celíaca y con algún producto sin TACC continuo 2022-2026: fideos secos, galletitas dulces,
   galletitas saladas y crackers, pan rallado y rebozador, cereales rellenos (almohaditas). Afuera por no tener ningún
   sin TACC que cumpla las reglas: pan envasado (los sin TACC —Schär, Binfinit— están en pocas cadenas y los con TACC
   continuos son casi todos de DIA), alfajores (un solo Yuka), premezclas y harinas, budines, tapas, prepizzas, pastas
   frescas y cerveza (la sin TACC aparece en 2023-2026).
2. **Lado.** *Sin TACC*: la descripción del Maestro o de alguna cadena en el SEPA dice sin TACC / sin gluten (todas las
   grafías; "C/GLUTEN" y "galletitas DE gluten" son con TACC) o la marca es celíaca (>= 50% de sus productos
   etiquetados: Smams, Wakas, Blue Patna, Crisppino, Snuks, Santa María, Naturalsur…). *Con TACC*: sin esa marca, sin
   ingredientes naturalmente sin gluten (arroz, maíz, legumbres, quinoa…) y de una marca que no sea celíaca.
3. **Continuidad temporal**: precio todos los meses de ene-2022 a jul-2026 (55, los semestrales oficiales) y en
   ago-oct 2026; a lo sumo 3 **caídas** (meses con cobertura < 35% de su mediana móvil de 13 meses) sin contar los meses
   con defectos conocidos de la fuente (jul-2023, con la mitad de los comercios entre el 16 y el 28, y dic-2023 →
   mar-2024, el hueco de Molinos); cobertura media 2022 / 2026 entre 1/4 y 4 (el producto no cambió de escala). La
   caída se mide contra la mediana móvil para no castigar el crecimiento: las pepas Smams pasaron de ~480 sucursales
   por día en 2022 a ~1.140 en 2026 sin ningún hueco (los bizcochos agridulces Smams, en cambio, pasaron de ~80 a ~510:
   en 2022 eran un producto de nicho y quedan afuera por la cobertura 2022/2026 = 0,16).
4. **Cobertura geográfica y por cadenas** (todo el período, ranking del nb09):

   | | Sucursales por día (mediana mensual) | Provincias | Comercios súper | Cadenas grandes (de 8) | Cadena principal |
   |---|---|---|---|---|---|
   | Sin TACC | >= 100 | >= 20 | >= 4 | >= 3 | <= 75% de sus sucursal-días |
   | Con TACC | >= 300 | >= 22 | >= 8 | >= 5 | <= 60% |

   Cadenas grandes: DIA, Carrefour, Cencosud (Vea/Disco/Jumbo), La Anónima, Cooperativa Obrera, Coto, ChangoMas y
   Toledo. Comercios súper: sin estaciones de servicio, Mercado Libre ni farmacias.
5. **Comparabilidad por subtipo**: fideos por forma (spaghetti, tallarín, mostachol/penne, tirabuzón/fusilli, cortos);
   galletitas dulces en rellenas, secas, pepas, con chips, obleas y bizcochos; saladas en crackers y galletas de arroz,
   y saborizadas. Afuera lo que no tiene equivalente: fideos al huevo, integrales, de legumbres, "Rina", preparados;
   galletitas bañadas, integrales, de avena, sin azúcar, surtidas, de hojaldre, tostadas dulces y vainillas; saladas de
   salvado, bizcochitos de grasa, tostadas, palitos y las galletas de arroz **dulces** (el Grandiet `7797330100663` dice
   "Galletas de Arroz" en el Maestro y "galletas de arroz dulces" en Carrefour y La Anónima).
6. **Identidad verificada con precios (ene-2022 → oct-2026)**: cada producto contra los de su mismo tipo y lado
   (mediana $/100 g de su lado en cada mes): su nivel relativo en los últimos 6 meses dentro de [0,4; 2,5] veces el de
   los primeros 6, y ningún cambio de nivel **persistente** de más de ×2,5 (mediana de 3 meses contra los 3 anteriores:
   eso es otro producto, una presentación mal cargada o un precio congelado; un dato malo de un mes en una cadena se
   revierte y no cuenta). Las ventanas de esa regla no cruzan oct-2023 → mar-2024 (salida de los precios controlados,
   14.8) ni los 3 meses desde el corte de un código. En los empalmes, cada código a ±25% de la mediana de sus códigos
   en los meses en que conviven; el salto en el mes del corte se informa (s10, `CORTE`). Y cobertura en oct-2026 (nb09,
   SEPA diario al 22/10) >= 25% de su mediana (no casi desaparecido).
   **Presentación**: los gramos del Maestro tienen que coincidir (±5%) con los que publican las cadenas en oct-2026; si
   difieren y no hay evidencia de cuándo cambió el paquete, el producto queda afuera (Porteñitas: 130 g en el Maestro,
   139 g en cuatro cadenas, y un pack "3x139 g" registrado en may-2025). Los Wakas se resolvieron con evidencia (14.4).
7. **Lado con TACC en marcas de primera línea**: precio $/100 g entre 0,6 y 1,67 veces la mediana con TACC de su
   subtipo (afuera las marcas económicas: Spaghetti La Providencia a $192/100 g contra ~$360-440 de Lucchetti y
   Matarazzo). El sin TACC no tiene franja: sus diferencias de precio son parte de lo que se mide.
8. **Composición espejada**: en cada subtipo, tantos productos con TACC como sin TACC (los de más cobertura); si el
   lado con TACC tiene menos candidatos que el sin TACC, entran todos los de los dos lados (tirabuzón, crackers,
   almohaditas). El subtipo que no tiene los dos lados queda afuera (fideos cortos y tallarín, bizcochos y pan rallado
   solo tenían con TACC).

La prima sin TACC / con TACC de cada producto se calcula y se informa, pero **no** es una regla: la condición de sin
TACC la dan la etiqueta y la marca, y sacar los sin TACC baratos sesgaría la brecha para arriba.

### 14.4 Productos que cambiaron de código: empalmes y vigencias

- **Molinos, sep-oct 2023.** Lucchetti y Matarazzo pasaron a códigos nuevos con número de forma ("Spaghetti N3
  Matarazzo", "Mostachol N51 Lucchetti"…); en abr-2023 hubo además códigos intermedios (N°5, N°51, N°52, N°34). **El
  código nuevo salió a 2,5-3,4 veces el precio del viejo en las mismas sucursales** (spaghetti Matarazzo: $166 contra
  $60 por 100 g en oct-2023, en ~1.000 sucursales con los dos): los viejos venían con precio controlado (subieron 19%
  entre jun y oct de 2023, con una inflación de ~48%) y el cambio de código fue la salida de ese precio. Los códigos
  viejos **siguen apareciendo en ~100 sucursales con el precio congelado** (Spaghetti Lucchetti viejo a $230-274 en
  todo 2024-2026 contra $1.042-1.699 del nuevo): si entraran en la mediana, en esas sucursales la brecha se dispararía.
  Por eso cada código lleva una **vigencia**, la misma para todos los de Molinos, comunes y sin TACC: el viejo hasta
  sep-2023 y el nuevo desde oct-2023. Los intermedios quedan afuera (poca cobertura y precios inconsistentes).
- **Wakas, jun-2024: de la bolsa de 250 g a la caja de 300 g.** Los fusilli multicereal (`...0024/0031/0048/0086/0093`,
  bolsa de 250 g según el Maestro desde 2017) pasaron a códigos "Caja" (`...0796/0826/0802/0819/0833`). El Maestro dice
  250 g también para la caja, pero las cuatro cadenas que la publican en oct-2026 dicen 300 g, y los precios lo
  confirman: en jun-sep 2024, en las mismas sucursales de la Cooperativa Obrera, la caja costaba 26% más que la bolsa
  (3.136 contra 2.490: el mismo precio por gramo con 300 y 250 g), y en todas las cadenas la caja cuesta exactamente lo
  mismo que el penne Wakas de 300 g. Desde ago-2024 algunas cadenas publican el código viejo como alias de la caja
  (Cencosud: mismo precio, mismas sucursales, "x300g"). Por eso: bolsa 250 g hasta 2024-07, caja 300 g desde 2024-06
  (en jun-jul 2024 conviven en algunas sucursales, a precio por gramo parecido, y el producto entra una vez).
- **La línea sin TACC de Matarazzo existe desde antes de 2022** (corrección: el 22/10 los había tomado por mal
  etiquetados). `7790070321800` (spaghetti), `7790070321855` (tirabuzón) y `7790070321794` (penne) tenían en 2022
  1.400-2.000, 1.000-1.400 y ~500 sucursales por día y, en las mismas sucursales, costaban 1,97, 2,97 y 2,0 veces el
  Matarazzo común (p5-p95 de 1,78-2,32 en el spaghetti; ninguna cadena por debajo de 1,3×): son sin TACC genuinos. En
  oct-2023 Molinos los reemplazó por `7790070336002` (spaghetti; el Maestro lo describe como "Mostachol 5 Cereales"),
  `7790070335982` (tirabuzón, desde dic-2023) y `7790070335999` (penne), y los viejos quedaron con el precio congelado en
  ~100 sucursales: con solo los precios de 2024-2026 parecían fideos comunes (y el filtro de plausibilidad de agosto de
  2026 los sacó). Se empalman como los demás de Molinos.
- **El Maestro interno puede estar desactualizado**: `7790070336002` es el Spaghetti sin TACC Matarazzo 500 g en todas
  las cadenas (SEPA diario) y el Maestro dice "Fideos Mostachol 5 Cereales"; los Crisppino de 100 g `7798199770134` y
  `7798199770141` tienen los sabores cruzados (Carrefour y Cencosud: el primero es jamón y el segundo queso). Las
  descripciones de la canasta salen del Maestro solo si coinciden con las del SEPA (si no, se corrigen: `DESC_FIJA` de
  s10).

En el nb06 la vigencia se aplica en la CELDA 7, después de leer: cambiarla no relee el SEPA.

### 14.5 La canasta

**68 productos (80 códigos)**: 30 con TACC y 38 sin TACC en 12 subtipos de 5 tipos. *Suc./día 2022-26* = mediana mensual de las sucursales con precio por día (nb09; en los empalmes, la suma de sus códigos vigentes); *Prov.*, *Com.* (comercios súper) y *Cad. grandes* en todo el período; *$/100 g oct-26* = mediana nacional (SEPA diario al 22/10); *Relativo* = $/100 g sobre la mediana con TACC de su subtipo (mediana 2022-2026): en el lado con TACC, su posición en la franja de primera línea; en el sin TACC, su prima. Vigencia: ≤ último mes del código viejo, ≥ primer mes del nuevo.

Quedaron afuera en la verificación con precios: Porteñitas y Maná rellenas 165 g (los gramos del Maestro no coinciden con los de las cadenas y no se sabe desde cuándo), Scons 9 de Oro (dos cambios de nivel persistentes de ×4 frente a sus pares, may-2023 y dic-2023) y el tirabuzón sin TACC Matarazzo (su código nuevo recién aparece en dic-2023: dos meses sin precio). Fideos cortos y tallarín, bizcochos y pan rallado no tienen sin TACC continuo.

| Tipo | Productos con TACC | Productos sin TACC | Códigos (EAN) | Subtipos |
|---|---|---|---|---|
| Fideos secos | 6 | 9 | 27 | Mostachol / penne, Spaghetti, Tirabuzón / fusilli |
| Galletitas dulces | 10 | 10 | 20 | Con chips, Obleas, Pepas, Rellenas, Secas (vainilla, limón, chocolate) |
| Galletitas saladas y crackers | 10 | 13 | 23 | Crackers y galletas de arroz, Saborizadas / snack |
| Pan rallado y rebozador | 2 | 2 | 4 | Rebozador |
| Cereales rellenos (almohaditas) | 2 | 4 | 6 | Almohaditas rellenas |
| **Total** | 30 | 38 | 80 | |

**Fideos secos**

| Subtipo | Lado | Producto | EAN (vigencia) | g | Suc./día 2022-26 | Prov. | Com. | Cad. grandes | $/100 g oct-26 | Relativo |
|---|---|---|---|---|---|---|---|---|---|---|
| Mostachol / penne | sin TACC | Penne rigate sin TACC Matarazzo 500 g | `7790070321794` (≤2023-09)<br>`7790070335999` (≥2023-10) | 500 | 551 | 24 | 12 | 6 | 989 | 2,29 |
| Mostachol / penne | sin TACC | Fideos Mostacholes sin TACC Blue Patna 500 Gr | `7730114100077` | 500 | 167 | 24 | 11 | 7 | 1.172 | 3,32 |
| Mostachol / penne | con TACC | Mostacholes Lucchetti 500 g | `7790070318336` (≤2023-09)<br>`7790070336149` (≥2023-10) | 500 | 2.208 | 24 | 25 | 8 | 350 | 0,91 |
| Mostachol / penne | con TACC | Penne rigate Matarazzo 500 g | `7790070318633` (≤2023-09)<br>`7790070336200` (≥2023-10) | 500 | 1.287 | 24 | 22 | 8 | 420 | 1,09 |
| Spaghetti | sin TACC | Spaghetti sin TACC Matarazzo 500 g | `7790070321800` (≤2023-09)<br>`7790070336002` (≥2023-10) | 500 | 1.188 | 24 | 17 | 8 | 860 | 2,36 |
| Spaghetti | sin TACC | Fideos Spaghetti sin TACC Blue Patna 500 Gr | `7730114100015` | 500 | 167 | 24 | 10 | 6 | 1.220 | 3,71 |
| Spaghetti | con TACC | Spaghetti Matarazzo 500 g | `7790070318640` (≤2023-09)<br>`7790070336309` (≥2023-10) | 500 | 2.118 | 24 | 25 | 8 | 420 | 1,17 |
| Spaghetti | con TACC | Spaghetti Lucchetti 500 g | `7790070318282` (≤2023-09)<br>`7790070336385` (≥2023-10) | 500 | 2.002 | 24 | 26 | 8 | 350 | 1,00 |
| Tirabuzón / fusilli | sin TACC | Fusilli quinoa sin TACC Wakas | `7798031470031` (≤2024-07)<br>`7798031470826` (≥2024-06) | 250/300 | 586 | 24 | 18 | 7 | 1.257 | 3,38 |
| Tirabuzón / fusilli | sin TACC | Fusilli maíz y arroz sin TACC Wakas | `7798031470024` (≤2024-07)<br>`7798031470796` (≥2024-06) | 250/300 | 537 | 24 | 18 | 7 | 1.257 | 3,67 |
| Tirabuzón / fusilli | sin TACC | Fusilli chía sin TACC Wakas | `7798031470086` (≤2024-07)<br>`7798031470819` (≥2024-06) | 250/300 | 527 | 24 | 16 | 7 | 1.236 | 3,37 |
| Tirabuzón / fusilli | sin TACC | Fusilli amaranto sin TACC Wakas | `7798031470048` (≤2024-07)<br>`7798031470802` (≥2024-06) | 250/300 | 443 | 24 | 16 | 6 | 1.343 | 3,52 |
| Tirabuzón / fusilli | sin TACC | Fideos Tirabuzones sin TACC Blue Patna 500 Gr | `7730114100046` | 500 | 272 | 24 | 10 | 6 | 1.190 | 3,43 |
| Tirabuzón / fusilli | con TACC | Tirabuzones Lucchetti 500 g | `7790070318329` (≤2023-09)<br>`7790070336026` (≥2023-10) | 500 | 2.080 | 24 | 25 | 8 | 350 | 0,93 |
| Tirabuzón / fusilli | con TACC | Tirabuzones Matarazzo 500 g | `7790070318602` (≤2023-09)<br>`7790070336293` (≥2023-10) | 500 | 2.014 | 24 | 25 | 8 | 420 | 1,07 |

**Galletitas dulces**

| Subtipo | Lado | Producto | EAN (vigencia) | g | Suc./día 2022-26 | Prov. | Com. | Cad. grandes | $/100 g oct-26 | Relativo |
|---|---|---|---|---|---|---|---|---|---|---|
| Con chips | sin TACC | Galletitas Con Chips de Chocolate Smams 150 Gr | `7798181511004` | 150 | 511 | 24 | 13 | 5 | 2.527 | 1,96 |
| Con chips | con TACC | Galletitas con Chips Suavecitas Par Nor 140 Gr | `7791324156926` | 140 | 333 | 24 | 11 | 5 | 1.214 | 1,00 |
| Obleas | sin TACC | Obleas Limón Santa María 90 Gr | `7798079230833` | 90 | 108 | 24 | 5 | 4 | 3.222 | 2,60 |
| Obleas | con TACC | Galletitas Obleas Clásicas Opera 220 Gr | `7790040008175` | 220 | 1.760 | 24 | 24 | 8 | 1.349 | 0,86 |
| Pepas | sin TACC | Pepas de Membrillo sin TACC Smams 150 Gr | `7798181510786` | 150 | 997 | 24 | 14 | 7 | 2.093 | 2,28 |
| Pepas | con TACC | Galletitas Dulces Pepas Trío 320 Gr | `7791787100924` | 320 | 359 | 24 | 11 | 5 | 716 | 0,97 |
| Rellenas | sin TACC | Galletitas Sabor Chocolate con Relleno de Vainilla Smams 105 Gr | `7798181510014` | 105 | 1.005 | 24 | 15 | 7 | 2.467 | 1,92 |
| Rellenas | sin TACC | Galletitas Vainilla Rellenas Smams 105 Gr | `7798181510021` | 105 | 914 | 24 | 16 | 7 | 2.371 | 1,95 |
| Rellenas | sin TACC | Galletitas Vainilla Rellenas Sabor Frutilla Smams 105 Gr | `7798181510267` | 105 | 512 | 24 | 16 | 7 | 2.467 | 1,93 |
| Rellenas | con TACC | Galletitas Rellena Sabor Frambuesa Sonrisas 108 Gr | `7790040133488` | 108 | 2.087 | 24 | 20 | 8 | 1.629 | 1,10 |
| Rellenas | con TACC | Galletitas Vainilla con Relleno de Limón Duquesa 115 Gr | `7622300742645` | 115 | 1.932 | 24 | 23 | 8 | 1.460 | 0,99 |
| Rellenas | con TACC | Galletitas Vainilla Rellenas Chocolate Maná 152 Gr | `7790040133242` | 152 | 890 | 24 | 19 | 8 | 1.178 | 1,00 |
| Secas (vainilla, limón, chocolate) | sin TACC | Galletitas Colegial Vainilla Samms 150 Gr | `7798181510847` | 150 | 554 | 24 | 14 | 7 | 1.733 | 1,75 |
| Secas (vainilla, limón, chocolate) | sin TACC | Galletitas Sabor Limón Aglu 150 Gr | `7798128410070` | 150 | 252 | 24 | 4 | 4 | 1.600 | 1,70 |
| Secas (vainilla, limón, chocolate) | sin TACC | Galletitas Sabor Vainilla sin TACC Santa María 200 Gr | `7798079230147` | 200 | 207 | 24 | 4 | 3 | 1.450 | 1,69 |
| Secas (vainilla, limón, chocolate) | sin TACC | Galletitas Marmoladas sin TACC Santa María 200 Gr | `7798079230628` | 200 | 171 | 23 | 5 | 4 | 1.450 | 1,63 |
| Secas (vainilla, limón, chocolate) | con TACC | Galletitas Anillos Clásicos Terrabusi 170 Gr | `7622201808884` | 170 | 1.214 | 24 | 20 | 8 | 1.205 | 1,22 |
| Secas (vainilla, limón, chocolate) | con TACC | Galletitas Dulces Boca de Dama Terrabusi 170 Gr | `7622201808860` | 170 | 894 | 24 | 20 | 8 | 935 | 0,93 |
| Secas (vainilla, limón, chocolate) | con TACC | Galletitas Sconcitos 9 de Oro 200 Gr | `7792200000791` | 200 | 706 | 24 | 20 | 7 | 750 | 0,85 |
| Secas (vainilla, limón, chocolate) | con TACC | Galletitas Frolitas Trio 300 Gr | `7791787000644` | 300 | 369 | 24 | 16 | 6 | 767 | 0,90 |

**Galletitas saladas y crackers**

| Subtipo | Lado | Producto | EAN (vigencia) | g | Suc./día 2022-26 | Prov. | Com. | Cad. grandes | $/100 g oct-26 | Relativo |
|---|---|---|---|---|---|---|---|---|---|---|
| Crackers y galletas de arroz | sin TACC | Galletitas Crackers Smams 150 Gr | `7798181510212` | 150 | 1.064 | 24 | 17 | 8 | 2.513 | 2,78 |
| Crackers y galletas de arroz | sin TACC | Galletas de Arroz sin TACC sin Sal Multicereal Grandiet 100 Gr | `7797330102377` | 100 | 733 | 24 | 13 | 5 | 1.850 | 2,12 |
| Crackers y galletas de arroz | sin TACC | Galletitas Crackers Mix Semillas Smams 150 Gr | `7798181510229` | 150 | 640 | 24 | 16 | 8 | 2.513 | 2,84 |
| Crackers y galletas de arroz | sin TACC | Galletas de Arroz con Sal Grandiet 100 Gr | `7797330100649` | 100 | 382 | 24 | 12 | 4 | 1.590 | 2,05 |
| Crackers y galletas de arroz | sin TACC | Galletas de Arroz sin Sal Grandiet 100 Gr | `7797330100656` | 100 | 366 | 24 | 12 | 4 | 1.690 | 2,05 |
| Crackers y galletas de arroz | sin TACC | Galletitas Crackers Light sin Sal Smams 150 Gr | `7798181510205` | 150 | 301 | 24 | 14 | 7 | 2.500 | 2,71 |
| Crackers y galletas de arroz | sin TACC | Galletas de Arroz sin TACC Multicereal Grandiet 100 Gr | `7797330102322` | 100 | 206 | 24 | 13 | 5 | 1.828 | 2,06 |
| Crackers y galletas de arroz | con TACC | Galletitas Original Crackers Criollitas 100 Gr | `7790040377707` | 100 | 1.434 | 24 | 22 | 8 | 810 | 0,93 |
| Crackers y galletas de arroz | con TACC | Galletitas Crackers Naturalmente Granix 200 Gr | `7790045001133` | 200 | 708 | 24 | 18 | 6 | 925 | 1,08 |
| Crackers y galletas de arroz | con TACC | Galletitas Mini Marineras Paseo 220 Gr | `7792180006462` | 220 | 470 | 24 | 19 | 8 | 840 | 1,06 |
| Crackers y galletas de arroz | con TACC | Mini Crackers con Semillas de Sésamo Paseo 300 Gr | `7792180007285` | 300 | 362 | 24 | 20 | 8 | 758 | 0,94 |
| Saborizadas / snack | sin TACC | Galletita Arroz sin TACC Sabor Queso Crisppino 100 Gr | `7798199770134` | 100 | 434 | 24 | 4 | 4 | 2.590 | 1,29 |
| Saborizadas / snack | sin TACC | Galletitas Arroz sin TACC Sabor Jamón Crisppino 100 Gr | `7798199770141` | 100 | 430 | 24 | 4 | 4 | 2.590 | 1,29 |
| Saborizadas / snack | sin TACC | Galletas de Arroz Mini Sabor Oliva Crisppino 50 Gr | `7798199770073` | 50 | 334 | 24 | 7 | 4 | 2.958 | 1,47 |
| Saborizadas / snack | sin TACC | Galletitas de Arroz Sabor Jamón sin TACC Crisppino Minis 50 Gr | `7798199770035` | 50 | 284 | 24 | 7 | 3 | 2.958 | 1,43 |
| Saborizadas / snack | sin TACC | Galletitas de Arroz Sabor Queso sin TACC Crisppino Minis 50 Gr | `7798199770042` | 50 | 272 | 24 | 7 | 3 | 2.958 | 1,44 |
| Saborizadas / snack | sin TACC | Galletas de Arroz Pizza Grandiet 100 Gr | `7797330102971` | 100 | 206 | 24 | 10 | 3 | 1.700 | 0,85 |
| Saborizadas / snack | con TACC | Galletitas Pizza Saladix 100 Gr | `7790580697303` | 100 | 1.501 | 24 | 22 | 8 | 1.901 | 0,97 |
| Saborizadas / snack | con TACC | Galletitas Saladas Tipo Snacks Rex 75 Gr | `7790040003569` | 75 | 1.336 | 24 | 20 | 8 | 2.493 | 1,15 |
| Saborizadas / snack | con TACC | Galletitas Original Rex 125 Gr | `7790040719804` | 125 | 995 | 24 | 22 | 8 | 1.998 | 1,00 |
| Saborizadas / snack | con TACC | Galletitas Jamón Saladix 100 Gr | `7790580716707` | 100 | 850 | 24 | 26 | 8 | 1.901 | 0,95 |
| Saborizadas / snack | con TACC | Galletitas Kesitas 75 Gr | `7790040003606` | 75 | 740 | 24 | 21 | 8 | 2.495 | 1,14 |
| Saborizadas / snack | con TACC | Galletitas Calabresa Saladix 100 Gr | `7790580716806` | 100 | 508 | 24 | 23 | 6 | 1.899 | 0,95 |

**Pan rallado y rebozador**

| Subtipo | Lado | Producto | EAN (vigencia) | g | Suc./día 2022-26 | Prov. | Com. | Cad. grandes | $/100 g oct-26 | Relativo |
|---|---|---|---|---|---|---|---|---|---|---|
| Rebozador | sin TACC | Rebozador Aglu 450 Gr | `7798128410087` | 450 | 494 | 24 | 6 | 5 | 856 | 2,05 |
| Rebozador | sin TACC | Rebozador Naturalsur 500 Gr | `7798193377285` | 500 | 211 | 23 | 6 | 5 | 750 | 2,23 |
| Rebozador | con TACC | Rebozador Horno Fortificado Mamá Cocina Plus 1 Kg | `7792180004796` | 1.000 | 821 | 24 | 12 | 6 | 363 | 1,14 |
| Rebozador | con TACC | Rebozador Freir Fortificado Mamá Cocina Plus 500 Gr | `7792180004765` | 500 | 461 | 24 | 16 | 6 | 319 | 1,00 |

**Cereales rellenos (almohaditas)**

| Subtipo | Lado | Producto | EAN (vigencia) | g | Suc./día 2022-26 | Prov. | Com. | Cad. grandes | $/100 g oct-26 | Relativo |
|---|---|---|---|---|---|---|---|---|---|---|
| Almohaditas rellenas | sin TACC | Almohaditas Rellenas Chocolate sin TACC Snuks 240 Gr | `7798169802636` | 240 | 273 | 24 | 7 | 6 | 2.141 | 1,26 |
| Almohaditas rellenas | sin TACC | Almohaditas Rellenas Avellana Snuks 240 Gr | `7798169802629` | 240 | 257 | 24 | 7 | 6 | 2.104 | 1,26 |
| Almohaditas rellenas | sin TACC | Almohaditas Rellenas Limón sin TACC Snuks 240 Gr | `7798169802728` | 240 | 253 | 24 | 7 | 6 | 2.162 | 1,26 |
| Almohaditas rellenas | sin TACC | Almohaditas Rellenas Frutilla sin TACC Snuks 240 Gr | `7798169802711` | 240 | 253 | 24 | 8 | 6 | 2.125 | 1,27 |
| Almohaditas rellenas | con TACC | Almohaditas Rellenas Sabor Mousse Limón Lasfor 200 Gr | `7798169802681` | 200 | 338 | 24 | 8 | 6 | 1.620 | 1,00 |
| Almohaditas rellenas | con TACC | Almohaditas Rellenas con Crema Avellanas Lasfor 200 Gr | `7798169802650` | 200 | 330 | 24 | 8 | 6 | 1.650 | 1,00 |

### 14.6 Estimador y ponderación (ENGHo 2017/18)

**Estimador (2026-10-23)**, como un índice de precios por niveles:

1. **Subtipo en una sucursal y mes**: precio de cada lado = mediana $/100 g de los productos presentes (un producto con
   dos códigos entra una vez); brecha = sin TACC / con TACC − 1 si están los dos lados. Compara productos
   equivalentes dentro del mismo super.
2. **Subtipo en un grupo** (país, mes, año, provincia, región, empresa, cadena): mediana de esas brechas entre
   sucursales (sucursal-mes).
3. **Tipo en un grupo**: promedio geométrico, con pesos iguales, de sus subtipos presentes en el grupo con al menos
   `MIN_SUC_SUBTIPO` (10) sucursales. En la **serie mensual**, un subtipo-mes con menos de la mitad de sus sucursales
   habituales (`FRAC_SUBTIPO_MES`) se imputa con su último mes válido, como un ítem que falta temporalmente en un índice
   de precios (cambios de código de Molinos en sep-oct 2023 y su hueco de dic-2023 a mar-2024); la columna
   `n_subtipos_imputados` (y `subtipos_imputados` en la canasta) dice cuántos.
4. **Canasta**: `sum_k w_k (1 + g_k) − 1` con los pesos ENGHo de abajo (renormalizados entre los tipos presentes).

La versión anterior tomaba, en cada sucursal, la mediana del tipo entero y después la mediana entre sucursales. Eso
mezclaba subtipos de niveles muy distintos según qué tuviera cada sucursal: en las saladas, la brecha daba +26,5%
porque el lado con TACC tenía más snacks (~$2.000/100 g) y el sin TACC más crackers, aunque crackers contra crackers
da +165% y snacks contra snacks +28%. Además, la serie mensual de cada tipo tenía 2-3 veces más ruido (desvío de la
variación mensual de 38-42 pp en fideos y galletitas, contra 14-21 pp por subtipos), porque se movía con la mezcla de
sucursales de cada mes. El "más barato" ilustrativo y el promedio sin outliers siguen el mismo camino. En el mapa y en
la canasta por sucursal, la brecha del tipo en una sucursal es el promedio geométrico de sus subtipos con los dos lados.

**Ponderación.** Peso de cada tipo = parte del gasto de los hogares en alimentos y bebidas no alcohólicas (división A01) que va a sus
artículos en la ENGHo 2017/18 (microdatos de gastos, monto × pondera; hogar promedio, no celíaco: no hay datos de gasto
de hogares celíacos), renormalizada entre los tipos de la canasta. La brecha de la canasta de un grupo es
`sum_k w_k (1 + g_k) − 1` con `g_k` la brecha mediana del tipo `k` en el grupo (pesos renormalizados entre los tipos
presentes); en la canasta por sucursal (mapa) se usan cantidades `w_k / precio con TACC del tipo en el año base (2022)`.

| Tipo | Artículos de la ENGHo 2017/18 | % del gasto en alimentos y bebidas no alcohólicas | Peso en la canasta |
|---|---|---|---|
| Fideos secos | A0111304 Fideos secos | 1,503 | 30,0% |
| Galletitas dulces | A0111105 Galletitas dulces envasadas + A0111108 Masas secas o finas | 1,717 | 34,3% |
| Galletitas saladas y crackers | A0111103 Galletitas de agua envasadas + A0111102 Galletas, grisines y tostadas + A0111107 Galletitas de otro tipo | 1,407 | 28,1% |
| Pan rallado y rebozador | A0111114 Pan rallado | 0,194 | 3,9% |
| Cereales rellenos (almohaditas) | A0111207 Cereales inflados | 0,181 | 3,6% |

Los tres tipos grandes pesan lo mismo, a grandes rasgos (28-34%); rebozador y almohaditas casi no mueven la canasta. El
Excel de la selección del 22/10 (`seleccion_brecha_celiaca_20261022.xlsx`, hoja `Ponderaciones_ENGHo`) mostraba los
mismos pesos como % del gasto en los 12 tipos con TACC (12,70 / 14,51 / 11,89 / 1,64 / 1,53): misma proporción.

### 14.7 Qué cambia en el nb06

| Celda | Cambio |
|---|---|
| 1 | `TIPOS` (peso ENGHo + productos con TACC / sin TACC con su descripción), `GRAMOS`, `VIGENCIA`, `PRODUCTO` (códigos de un mismo producto), `SUBTIPO`, `PONDERACION = 'engho'`, `MES_INICIO_HISTORICO = '2022-01'`, `USAR_REGLA_NOMBRE = False`, `CADENAS_FILTRAR` con Axion (23) y Farmacity (24), `MIN_SUC_SUBTIPO`, `FRAC_SUBTIPO_MES`, `RECLASIF_TOL_KM`, `AMBA_RADIO_KM`, `VENTANA_GEO_MESES` |
| 3 | Nombres de comercios y banderas del `comercio.csv` del SEPA, columna `empresa`, regiones INDEC |
| 4 | Lee la canasta (descripción y gramos de la config; el maestro solo de respaldo) |
| 5 | Un archivo por parte de cada mes (el que cubre más días) |
| 6 | Mediana exacta de los precios diarios del mes por sucursal × EAN; líneas filtradas por EAN antes de parsear; caché por mes `_cache/brecha_v3_<clave>/AAAA-MM.parquet` (si Colab se corta, retoma) |
| 7 | Vigencia de códigos; un producto con dos códigos entra una vez (mediana de sus códigos); brecha por sucursal × mes × **subtipo** (`bt_sub`) y del tipo en la sucursal como promedio geométrico de sus subtipos (`bt_sm`); "más barato" vectorizado (la versión anterior, una función de Python por grupo, tardaba ~11 min con 58 meses); provincia por polígonos de `ar.json` (tolerancia 100 km), AMBA por coordenadas, región; control de identidad por EAN (`Control_EAN`, no excluye); pesos ENGHo |
| 8 | Agregación subtipo → tipo → canasta (14.6); brecha por subtipo y por tipo (período, mes, año; todas las sucursales y panel balanceado por sucursal × subtipo); canasta ponderada por mes y año; provincia, región, empresa y cadena en los últimos 12 meses y región/empresa por año |
| 9-10 | Gráficos: canasta mensual (todas y panel), por tipo, por región y año, provincia y empresa (confiables), concentración; coroplético de los últimos 12 meses |
| 11 | Excel de 32 hojas (`Leeme` las explica; nuevas `Brecha_subtipo`, `Brecha_subtipo_anual` y `Brecha_subtipo_anual_balanc`) |
| 12 | Mapa por sucursal con mosaicos Esri (sin la marca de agua de CARTO) |

Con BUG-47 (§14.11, el mismo día) cambian además: CELDA 1 (`MAX_PESO_IMPUTADO`, `USAR_GEOREF`, `MIN_SUC_DEPTO`), 2
(`GEOREF_PATH`: la caché de Georef del nb09 en el Drive), 7 (departamento de cada sucursal; si falta en la caché, la API
de Georef), 8 (`_agg_tipo(..., ref_keys)`: misma canasta de subtipos en los grupos; canasta comparable por sucursal;
concentración por departamento; rachas de imputación), 9-10 (meses imputados marcados, gráfico por cadena, coroplético
solo con las provincias confiables), 11 (hoja `Imputaciones`; columnas nuevas en grupos, `Brecha_sucursal` y
`Concentracion`) y 12 (mapa con la canasta comparable).

### 14.8 Advertencias para leer los resultados

- **2023: precios controlados del lado con TACC y salida en oct-2023 / ene-2024.** Durante 2023 los productos con TACC
  de marcas masivas (Molinos, Bagley/Mondelez, Arcor, Mamá Cocina…) subieron mucho menos que los sin TACC de marcas
  celíacas: en jun-sep 2023 las galletitas dulces con TACC subieron 2-5% por mes y las sin TACC 5-21%. Molinos salió
  de ese precio cambiando los códigos de sus fideos (oct-2023: el nuevo cuesta 2,5-3,4 veces el viejo en las mismas
  sucursales) y el resto al terminar el programa de precios (ene-2024: +87% las galletitas dulces con TACC, +105% las
  saladas, +118% el rebozador, contra +26-36% de los sin TACC). **La brecha de 2023 está inflada por esos precios
  controlados del lado con TACC** (que el SEPA informa aunque el producto faltara en góndola) y cae en oct-2023 (fideos)
  y en ene-2024 (el resto). Es un dato de la realidad de precios, no un error de la canasta; para comparar niveles,
  usar 2022 y 2024-2026 y leer 2023 aparte.
- **Pocas marcas del lado sin TACC.** Las galletitas dulces y saladas dependen sobre todo de Smams (y Crisppino,
  Grandiet, Santa María, Aglu); los fideos, de Wakas, Blue Patna y Matarazzo sin TACC (spaghetti y penne, la línea de
  más cobertura: ~1.200 y ~550 sucursales por día); las almohaditas, de Snuks (que fabrica Lasfor, el mismo de las
  almohaditas con TACC: es el par más limpio). El lado con TACC de fideos es todo de Molinos (Lucchetti y Matarazzo: no
  hay otra marca de primera línea continua 2022-2026). La brecha por tipo refleja en buena medida la política de
  precios de esas pocas marcas; el spaghetti y el penne Matarazzo sin TACC contra los Matarazzo comunes son pares de la
  misma marca (el sin TACC cuesta ~2 veces el común en las mismas sucursales).
- **Comparaciones de sustitución**: crackers y galletas de arroz contra crackers de trigo; rebozador de arroz contra
  rebozador de trigo. Es la sustitución real del consumidor celíaco, no el mismo producto sin gluten.
- **Hueco de Molinos (dic-2023 → mar-2024)**: en esos meses hay pocas sucursales con fideos con TACC (y con el penne sin
  TACC de Matarazzo): la serie de fideos se apoya en menos sucursales (el notebook lo avisa como cobertura baja).
- **Ago-oct 2026** salen del SEPA diario (script 03), sin los comercios 19, 1000, 2000, 2002, 2005, 2007, 2013 y 3001;
  Libertad dejó de publicar el 02/09/2026. Cuando salga el semestral oficial 2026B, borrar esos meses del caché.
- **Sucursales sin coordenadas**: el nb06 usa solo las sucursales del maestro (`data/maestro_sucursales_completo.xlsx`,
  3.602 con coordenadas). En ene-2022 le faltan ~13% de las sucursales que venden estos productos (comercios que
  dejaron de publicar —17, 7, 6, 14, 18— y parte de DIA) y en 2026 ~5% (sucursales nuevas de Carrefour). La serie de
  "todas las sucursales" de 2022 tiene entonces un universo algo menor; el panel balanceado no cambia (esas sucursales
  no están en >= 70% de los meses).
- **Precio de lista, no de promoción**: el SEPA informa el precio de lista de góndola.
- **Mismos productos**: la canasta fija mide el cambio de precios de los mismos productos; no recoge la entrada de
  opciones sin TACC más baratas (eso lo mide la canasta flexible, que se puede volver a correr con
  `USAR_REGLA_NOMBRE = True` para comparar).

### 14.9 Qué revisar cuando vuelva la corrida de Colab

La simulación de 14.10 corrió las celdas reales con **los mismos zips del Drive**: la corrida de Colab tiene que dar
los mismos números (salvo el último mes si el `2026B.zip` del Drive cambió). **La primera corrida (2026-10-23) dio 29
hojas iguales a `simulacion_2026-10-23/`.** Con el notebook vigente (BUG-47, §14.11) la referencia es
`simulacion_2026-10-23b/` (30 hojas). Comparación automática, hoja por hoja:

```bash
python -I -X utf8 docs/auditoria/scripts_nb06_2026-10/s16_comparar_colab.py <brecha_celiaca_2026-10.xlsx de Colab> docs/brecha_celiaca/simulacion_2026-10-23b
```

(esperado: 30 hojas iguales). Después, la lectura de cada punto:

1. **Lectura**: 58 meses (ene-2022 → oct-2026), el AVISO de ago-2024 parte 1 (se usa `COMPLETOb`), "meses en
   centavos: ninguno", los EANs sin ningún precio (esperado: ninguno).
2. **Vigencia**: cuántas observaciones quedan fuera de la ventana de su código (los códigos viejos de Molinos desde
   oct-2023 y la bolsa Wakas desde ago-2024; cifra esperada en 14.10).
3. **Plausibilidad** (esperado: ninguno) y **Control_EAN** (revisar cada marcado: los saltos de oct-2023 y ene-2024
   son la salida de los precios controlados, 14.8).
4. **Cobertura_mensual**: sucursales con los dos lados por tipo y mes; el hueco de dic-2023 → mar-2024 en fideos.
5. **Ponderaciones**: año base 2022; cantidades y pesos.
6. **Brecha por tipo y año (panel balanceado)** contra 14.10.
7. **Región, empresa, cadena y provincia**: cuáles quedan confiables (misma canasta: <= 25% del peso con la brecha
   nacional y >= 30 sucursales; antes de BUG-47, todos los tipos con >= 30 sucursales).
8. **Imputaciones** (desde BUG-47): las rachas de más de 3 meses que avisa la CELDA 8 (hoja `Imputaciones`).
9. **Concentración** (desde BUG-47): "Departamento (Georef): N de M sucursales" en la CELDA 7 (con la caché del nb09,
   todas) y el Spearman de la CELDA 8.
10. **Serie TPD** (desde el 2026-10-23, noche; §14.12): en la CELDA 8b, `rango_completo` True en los 11 subtipos del
    panel y los 12 de todas; subtipo-mes movidos: panel con chips 14, mostachol 1, rebozador 6, spaghetti 1, tirabuzón 3;
    todas con chips 4, obleas 8; último mes (panel) TPD +119,0% (IC 95% +118,2% a +119,8%) contra +123,6%.

### 14.10 Simulación con los zips del Drive (ene-2022 → oct-2026)

Las celdas reales del `.ipynb` (`s11`) sobre los 10 zips semestrales del Drive (los mismos que lee Colab, bajados el
23/10) y un cálculo independiente desde los precios de `s8` (`s12`):

- **Coinciden exactamente**: 3.378.515 precios mensuales por sucursal × código (diferencia 0 y los mismos días), 534.456
  brechas por sucursal × mes × subtipo, 333.440 por sucursal × mes × tipo y las 290 brechas por tipo y mes.
- **Tiempo y memoria**: la lectura de los 58 meses tardó 37 min en la PC (38 s por mes; en Colab, ~1 h la primera vez)
  con un pico de 1,6 GB de RAM; el resto de las celdas, 3,6 min (CELDA 7 en 23 s, Excel en 77 s), con un pico de
  2,5 GB. El Colab gratuito tiene 12,7 GB.
- **Lectura**: 3,5 millones de observaciones (sucursal × código × mes), los 80 códigos con precio, 2.761 sucursales,
  ningún mes en centavos, el AVISO de ago-2024 parte 1 (se usa `COMPLETOb`). Vigencia: 57.419 observaciones fuera de
  la ventana de su código (16 códigos). 12 sucursales reclasificadas de provincia. Plausibilidad: ninguno.
  `Control_EAN`: 16 códigos marcados, todos por los saltos de oct-2023 / ene-2024 (14.8) o por datos malos de un mes en
  una cadena (DIA en sep-2026, jul-2023): ninguno es un cambio de producto.
- **Cobertura**: sucursales con los dos lados en algún momento: fideos 2.483, galletitas dulces 2.406, saladas 2.515,
  almohaditas 796 y rebozador 601. El aviso de "cobertura BAJA" de la CELDA 8 sale por el rebozador (el tipo con
  menos sucursales: 34-238 por mes). Panel balanceado: 4.975 sucursal × subtipo (1.318 sucursales); las obleas no
  entran (ninguna sucursal tiene los dos lados en >= 70% de los meses).

**Brecha por subtipo, todo el período** (mediana entre sucursal-mes; $/100 g medianos de cada lado):

| Tipo | Subtipo | Con TACC | Sin TACC | Brecha | Sucursales |
|---|---|---|---|---|---|
| Fideos secos | Spaghetti | 235 | 492 | +118% | 2.479 |
| Fideos secos | Mostachol / penne | 280 | 624 | +148% | 2.413 |
| Fideos secos | Tirabuzón / fusilli | 203 | 740 | +273% | 2.448 |
| Galletitas dulces | Rellenas | 625 | 1.233 | +88% | 2.372 |
| Galletitas dulces | Secas | 576 | 958 | +75% | 1.318 |
| Galletitas dulces | Pepas | 500 | 1.067 | +127% | 668 |
| Galletitas dulces | Con chips | 614 | 1.300 | +111% | 734 |
| Galletitas dulces | Obleas | 1.046 | 2.078 | +147% | 626 |
| Galletitas saladas | Crackers y galletas de arroz | 163 | 647 | +165% | 2.470 |
| Galletitas saladas | Saborizadas / snack | 1.100 | 1.150 | +28% | 855 |
| Pan rallado y rebozador | Rebozador | 241 | 451 | +84% | 599 |
| Cereales rellenos | Almohaditas | 1.200 | 1.521 | +26% | 775 |

**Por tipo** (promedio geométrico de sus subtipos), todo el período: fideos +172%, galletitas dulces +108%, saladas
+84%, rebozador +84%, almohaditas +26%. Por año, panel balanceado:

| Año | Fideos | Gall. dulces | Gall. saladas | Rebozador | Almohaditas | **Canasta (panel)** | Canasta (todas) |
|---|---|---|---|---|---|---|---|
| 2022 | +161% | +106% | +79% | +77% | +25% | **+111%** | +120% |
| 2023 | +147% | +109% | +69% | +113% | +24% | **+106%** | +116% |
| 2024 | +145% | +101% | +84% | +105% | +24% | **+107%** | +118% |
| 2025 | +152% | +89% | +73% | +71% | +20% | **+100%** | +104% |
| 2026 | +179% | +104% | +96% | +69% | +27% | **+120%** | +125% |

**Serie mensual de la canasta (panel balanceado)**: ~117-121% en ene-may 2022, ~100% en el segundo semestre de 2022 y
93-101% en el primero de 2023; sube a 118% en sep-2023, 135% en oct y 149-152% en nov-dic 2023 (los precios con TACC
controlados, 14.8); cae a 96% en ene-2024; 109-124% en 2024 hasta bajar a 92% en dic-2024; 88-110% en 2025; 122-129%
desde feb-2026 (fideos ~180-200% y snacks sin TACC más caros). Desvío de la variación mensual: 10 pp.

**Últimos 12 meses (nov-2025 → oct-2026)**, grupos confiables (los 5 tipos con >= 30 sucursales): regiones Pampeana
+120%, Cuyo +125%, AMBA +126% y Noroeste +127% (Noreste y Patagonia, con pocas sucursales); empresas Carrefour +119% y
Cencosud +125% (las únicas con los 5 tipos: DIA solo tiene dos); provincias entre Buenos Aires (+123%) y Córdoba
(+127%). Las diferencias entre regiones y cadenas son chicas frente a las diferencias entre tipos y subtipos.
*(Corregido en §14.11: estos grupos mezclaban composición de subtipos.)*

### 14.11 La corrida de Colab (2026-10-23) y la comparación entre grupos (BUG-47)

**La primera corrida de Colab dio igual a la simulación de 14.10** (29 hojas, diferencia máxima 1,4e-13): la canasta y
el estimador quedan validados en Colab. Revisión completa: `docs/AUDITORIA_2026-10-23_nb06.md`.

Al leerla aparecieron tres salidas que comparaban **composiciones distintas**, corregidas sin releer el SEPA (BUG-47):

1. **Grupos** (provincia, región, empresa, cadena): el tipo de un grupo promediaba solo los subtipos que el grupo tenía
   y la canasta renormalizaba entre los tipos presentes. Como los subtipos de un tipo tienen brechas muy distintas
   (saladas: crackers +165%, snacks +28%), un grupo sin snacks quedaba con la de los crackers: Coto +141,7%, Carrefour
   Express +140,2%, La Anónima +131,8%. Ahora todos los grupos tienen **la misma canasta de 12 subtipos** (cada subtipo
   pesa el peso ENGHo de su tipo dividido por los subtipos del tipo); el subtipo con < `MIN_SUC_SUBTIPO` sucursales en
   el grupo toma la brecha **nacional** del mismo período (`peso_imputado_pct`, `subtipos_con_brecha_nacional`), y el
   grupo es confiable con <= `MAX_PESO_IMPUTADO` (25%) del peso imputado y >= 30 sucursales.
2. **Sucursales** (mapa y `Brecha_sucursal`): misma canasta, con lo que la sucursal no tiene completado con la brecha
   nacional del mes (`peso_propio_pct`). Antes, con 2 tipos (DIA) la canasta daba +77% y con 3, +134%.
3. **Concentración**: HHI de empresas por **departamento** (Georef; cuota = sucursales) contra la canasta comparable de
   las sucursales con >= 50% del peso medido en ellas. Antes se agrupaba por el texto de la localidad, que DIA carga
   con el nombre de la provincia (la correlación −0,26 era DIA).

**Resultados con la misma canasta** (últimos 12 meses, nov-2025 → oct-2026; nacional +122,7%):

| | Confiables |
|---|---|
| Regiones (6) | Patagonia +107,4%, Pampeana +120,1%, Noreste +124,8%, Cuyo +124,9%, AMBA +125,6%, Noroeste +126,7% |
| Provincias (8) | Chubut +110,9%, Entre Ríos +114,1%, Santa Fe +117,3%, Salta +123,0%, Buenos Aires +123,2%, Mendoza +123,7%, CABA +124,3%, Córdoba +127,0% |
| Empresas (3) | Carrefour +124,0%, Cencosud +125,1%, ChangoMas +140,4% |
| Cadenas (7) | Carrefour Market +119,5%, Carrefour +121,1%, Vea +124,3%, Jumbo +126,0%, Disco +128,6%, ChangoMas +141,1%, HiperChangomas +141,9% |
| No confiables (más de 25% imputado) | La Anónima +110,5% (38,5%), Coto +127,0% (41,7%), Carrefour Express +122,5% (35,3%), DIA +115,8% (83,1%) |

Lectura: **la cadena pesa más que la región** (ChangoMas ~20 pp arriba de Carrefour y Cencosud; regiones con muchas
sucursales entre +120% y +127%). La concentración local no se relaciona con la brecha (Spearman −0,11 por sucursal;
mediana +125-126% en los tres tercios de HHI). Las series nacionales y la brecha por tipo no cambian.

**Abierto — la imputación de la serie mensual** (decisión del usuario): un subtipo-mes con menos de la mitad de sus
sucursales habituales arrastra su último mes válido sin límite: rachas de 7-14 meses en 2023-2024 (tirabuzón del panel
14 meses, mostachol de todas 12) y de 9 meses en las galletitas con chips (ago-2025 → abr-2026, 4-12 sucursales). Las
variantes medidas (límite de 3 meses, referencia local de 13 meses, dato propio después) mueven 2023-2024 sin ser
claramente mejores (AUDITORIA §4); la recomendación es la TPD/hedónica de §3.9 para la serie. Mientras tanto la hoja
`Imputaciones` lista las rachas y los gráficos marcan los meses imputados. **Implementada esa noche como serie de
robustez: §14.12.**

### 14.12 Serie TPD (hedónica): robustez frente a la imputación de subtipos (2026-10-23, noche)

**Para qué.** La serie mensual descriptiva imputa el subtipo-mes con menos de la mitad de sus sucursales habituales con
su último mes válido, sin límite (§14.11): 57 subtipo-mes en el panel balanceado y 70 en todas las sucursales, con rachas
de hasta 14 meses en 2023-2024. La serie TPD (*time-product-dummy*, la versión de serie de tiempo de la hedónica de
§3.9) estima la prima de cada mes con las sucursales que hay y compara siempre los mismos productos. Al lado de la
descriptiva, muestra qué tramos de la serie dependen de la imputación o del surtido.

**Modelo** (CELDA 8b). Una regresión por subtipo con todas sus observaciones producto × sucursal × mes ($/100 g; un
producto con dos códigos entra una vez, con la mediana de sus códigos):

```
ln p(i,s,t) = α(s,t) + γ(i) + β(t)·SINTACC(i) + ε
```

- `α(s,t)`: efecto de la **celda** (el subtipo en la sucursal *s* y el mes *t*). Cada sin TACC se compara con los con
  TACC de su subtipo en el mismo super y mes, como en la descriptiva.
- `γ(i)`: efecto de cada **producto** (marca, presentación, `ln gramos`). Qué productos tiene cada sucursal no mueve la
  serie; en la descriptiva, la mediana de cada lado depende del surtido.
- `β(t)`: prima sin TACC del mes. Mínimos cuadrados ponderados: cada producto pesa 1 / (productos de su lado en la
  celda), así cada celda aporta lo mismo de cada lado.
- **Brecha del subtipo** en el mes = `exp(L + β(t)) − 1`, con `L` = promedio de γ de los sin TACC − promedio de γ de los
  con TACC, cada producto pesado por sus observaciones en todo el período (ponderaciones fijas, como en un índice). No
  depende de qué producto o mes se fija como referencia. **Tipo** = promedio geométrico de sus subtipos y **canasta** =
  Σ w (1 + brecha del tipo) − 1 con los pesos ENGHo, como en la descriptiva.
- **Subtipo-mes sin dato propio**: con menos de `MIN_SUC_SUBTIPO` (10) sucursales con los dos lados, el subtipo se mueve
  con el promedio de los demás subtipos de su tipo que tienen dato propio en los dos meses (hacia adelante y después
  hacia atrás); el rebozador, único subtipo de su tipo, queda con el valor del mes vecino. Con tan pocas sucursales el
  error agrupado no mide la incertidumbre: con una sola, `β(t)` absorbe esa celda y el error sale ~0. Son 25 subtipo-mes
  en el panel (con chips 14, rebozador 6, tirabuzón 3, spaghetti 1, mostachol 1) y 12 en todas las sucursales (obleas
  8, con chips 4), contra 57 y 70 que arrastra la descriptiva. `peso_movido_pct` es la parte del peso de la canasta
  movida, como `peso_imputado_pct` en la descriptiva. En el panel hay 19 meses con algo movido (máximo 28,6%) contra 31
  con algo imputado en la descriptiva (máximo 42,5%); en todas las sucursales, 12 (máximo 6,9%) contra 36 (máximo 37,6%).
- **Errores**: agrupados por sucursal (CR1) y método delta para el tipo y la canasta, con la covarianza entre subtipos y
  tipos (se suman los puntajes de cada sucursal en todas las regresiones). El IC de un mes movido no incluye la
  incertidumbre de la imputación.
- **Cálculo**: ecuaciones normales exactas con los efectos de celda descontados (matrices dispersas; hasta 138 mil
  celdas por subtipo). No itera: 17 s y 2,9 GB de pico con los 58 meses. Si dos productos de un lado nunca conviven en
  una celda (p. ej. dos códigos del mismo producto sin unir en `PRODUCTO`), su nivel relativo no está identificado: la
  CELDA 8b lo avisa (`rango_completo`, meses no estimables) y no inventa ese nivel. Con los datos reales, todos los
  subtipos tienen rango completo.
- **Dos universos**: las celdas del panel balanceado (comparable con la serie clave) y todas las sucursales.

**Diseños descartados** (probados con los datos reales):

- Efecto de sucursal-mes del **tipo entero** en lugar de la celda del subtipo: cada sin TACC se medía contra todos los
  con TACC del tipo (las galletitas con chips contra rellenas, secas y pepas), la evolución de las con chips salía al
  revés y la canasta de 2022 daba ~17 pp más.
- Efecto fijo de **prima por sucursal** (sin TACC × sucursal): cambia poco la serie.
- **Sin mínimo de sucursales** (todo subtipo-mes con al menos una sucursal con los dos lados): 30 subtipo-mes salían de
  1 a 9 sucursales (el spaghetti del panel en oct-2023, de una sola) con un IC que no medía nada.

**Validación**: test con 30 controles, 4 de la TPD. La TPD recupera exacto la prima sin ruido aunque falten productos y
subtipo-mes (también con un mínimo de sucursales, moviendo el subtipo), coincide con mínimos cuadrados densos con todas
las indicadoras y la covarianza agrupada escrita a mano (brecha por tipo, error estándar, canasta e IC) y no inventa el
nivel de productos que nunca conviven. Con los datos reales, otro algoritmo (`r10_tpd_independiente.py`: LSQR sobre el
diseño completo, sin normalizar ni descontar efectos) da lo mismo en los 1.297 subtipo-mes con dato propio de los dos
universos (diferencia máxima 1,3e-7 pp). Resultados esperados: `simulacion_2026-10-23b/` (35 hojas, con las 5 de la TPD).

**Resultados** (canasta, promedio de los meses de cada año):

| Año | TPD panel | Descriptiva panel | TPD todas | Descriptiva todas |
|---|---|---|---|---|
| 2022 | +111,8% | +110,3% | +119,4% | +122,1% |
| 2023 | +122,7% | +112,2% | +123,3% | +125,8% |
| 2024 | +105,4% | +110,0% | +116,4% | +118,1% |
| 2025 | +98,8% | +101,5% | +104,9% | +103,4% |
| 2026 | +117,6% | +122,6% | +122,4% | +125,0% |

Por tipo, panel balanceado (TPD / descriptiva, %):

| Tipo | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|
| Fideos secos | 175,7 / 170,2 | 167,9 / 143,7 | 149,7 / 148,6 | 156,0 / 154,1 | 184,9 / 183,6 |
| Galletitas dulces | 103,6 / 99,9 | 125,1 / 120,1 | 99,9 / 103,3 | 86,1 / 89,5 | 104,5 / 105,1 |
| Galletitas saladas y crackers | 69,7 / 73,7 | 83,0 / 78,0 | 73,9 / 85,2 | 67,1 / 75,0 | 78,7 / 96,2 |
| Pan rallado y rebozador | 77,6 / 82,8 | 131,4 / 128,4 | 115,3 / 133,5 | 68,8 / 68,7 | 80,8 / 87,8 |
| Cereales rellenos (almohaditas) | 24,0 / 24,8 | 24,0 / 24,3 | 23,5 / 21,6 | 22,4 / 20,3 | 22,7 / 24,4 |

**Último mes (oct-2026)**: en el panel, TPD +119,0% (IC 95% +118,2% a +119,8%) contra +123,6% de la descriptiva; en
todas las sucursales, +119,9% (+119,4% a +120,4%) contra +122,8%. El IC de la canasta tiene un ancho mediano de 2,0 pp
(panel) y 1,3 pp (todas).

**Lectura**:

1. **Fuera de jun-2023 → feb-2024, las dos series cuentan lo mismo**: diferencia absoluta mediana de la canasta de 4,1 pp
   en el panel y 2,9 pp en todas las sucursales (dentro de ese tramo, 18,8 y 13,2 pp), y la TPD es más suave (desvío de
   la variación mensual: 4,7 contra 6,2 pp en el panel). Fideos, galletitas dulces y almohaditas coinciden en nivel y
   evolución; la TPD queda unos pp debajo sobre todo por las saladas.
2. **Galletitas saladas: 8 a 18 pp debajo en 2024-2026** (`r11_saladas_composicion.py`). Es surtido y método, no
   imputación (las saladas no se imputan en esos años). (a) El lado sin TACC cambió hacia productos de prima más alta.
   En crackers, Smams (+148% a +161% sobre los con TACC del subtipo) contra Grandiet (+79% a +92%): Smams pasó de 46%
   de las observaciones del lado en 2022-2023 a 66% en 2024, y ese año la TPD da +144% contra +172% del promedio
   geométrico de las celdas. En snacks, las Crisppino Minis (+57% a +60%) contra las de 100 g (+43%) pasaron de 33% en
   2022 a 58% en 2026; la TPD da +30,8% contra +45,5% de la mediana en 2026. La descriptiva compara lo que hay en cada
   sucursal y sube con la mezcla; la TPD fija los productos. (b) En 2026 las brechas de las celdas de crackers tienen
   dos niveles (sucursales con Grandiet y con Smams) y la mediana cae en el de arriba: +165,0% contra +148,1% del
   promedio geométrico, que es lo que promedia la TPD (+144,5%).
3. **2023: lo que pesa la imputación.** En todas las sucursales, donde la TPD tiene dato propio en casi todos los
   subtipo-mes, el pico de oct-dic 2023 es menor: +137% a +148% contra +161% a +170% de la descriptiva, que arrastra
   tirabuzón a +396% en oct-nov 2023 y mostachol a +152% de abr-2023 a mar-2024. En el **panel**, los fideos de
   jun-2023 → feb-2024 tienen muy pocas sucursales con los dos lados (cambio de códigos de Molinos y precios
   controlados, §14.8). En sep-2023 el spaghetti tiene pares en 108 de sus 782 sucursales del panel (TPD +254%, mientras
   las 1.271 de todas las sucursales dan +107%) y el tirabuzón en 40 de 344; en oct-2023, en 1 y 0. La descriptiva
   arrastra (tirabuzón +270,7% durante 14 meses, spaghetti +65,3% de jul a oct) y la TPD los mueve con el mostachol desde
   el valor de sep-2023: el pico de la canasta del panel en oct-2023 (+174%) sale de eso, no de una medición. Para 2023
   conviene mirar la TPD de todas las sucursales (`r12_tpd_vs_descriptiva_subtipo.py` muestra cada subtipo-mes).
4. **Rebozador** (un solo subtipo, el tipo con menos sucursales): la descriptiva del panel arrastró +220% de dic-2023 a
   feb-2024; la TPD mide feb-2024 (+87,5%), y en 2024 da +115% contra +134%.

**Cómo usarla**: la descriptiva sigue siendo el titular (§3.9); la TPD dice qué tramos dependen de la imputación o del
surtido. Donde coinciden (2022, 2025, 2026 y los tipos fuera de saladas) el número es robusto; en 2023 manda la TPD de
todas las sucursales, y en saladas la diferencia es de surtido y de método. Limitaciones: con pocas sucursales la TPD sale
de las que quedan, y el IC no cubre que sean distintas de las de siempre (sep-2023 en el panel); los efectos de producto
son fijos en todo el período (un producto que cambia de precio relativo, como un código nuevo empalmado con el viejo,
mueve la prima del mes); con efectos de producto, el nivel no está neto del efecto envase (§3.9).
