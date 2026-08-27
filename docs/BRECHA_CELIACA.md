# Brecha Celíaca (TACC vs sin-TACC) — `06_evolucion_brecha_celiaca`

Documento técnico del **Notebook 06**. Mide la **brecha** entre una canasta **base**
(productos con TACC) y su equivalente **sin-TACC** (canasta celíaca), y su evolución
**diaria, semanal y mensual**, desagregada por provincia, cadena y concentración de
comercios.

Última actualización: 2026-08-27 (revisión exhaustiva nivel-paper del estimador a nivel sucursal:
filtro de plausibilidad por regla, tratamiento del efecto envase, especificación hedónica §3.9).

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

---

## 3. Definición formal de la brecha (estimador canónico)

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

> **Estado**: la especificación está **definida** acá; la **implementación** del modelo (paquete
> `linearmodels`/`pyfixest` o `statsmodels`) es la **fase de análisis** siguiente. La medición
> descriptiva (nb06) ya produce el panel y las covariables necesarias.

---

## 4. Resolución temporal

Los archivos semestrales del SEPA traen **una columna de precio por día** (`precio_YYYYMMDD`),
así que la brecha diaria sale directo:

- **Diaria**: por cada día con dato. Solo para una **ventana** configurable
  (`VENTANA_DIARIA_MESES`, default 3 meses) para no generar gráficos gigantes.
- **Semanal**: por semana ISO (`%G-S%V`), todo el histórico.
- **Mensual**: por mes, todo el histórico.

El histórico completo se usa para responder *"¿la prima se mantiene o se amplía?"*.

---

## 5. Desagregaciones

- **Serie temporal** nacional (diaria/semanal/mensual), mediana y promedio.
- **Por provincia** (barras + mapa coroplético de la brecha).
- **Por cadena** (barras, cadenas con ≥5 sucursales).
- **Por concentración de comercios**: brecha vs. nº de sucursales por **localidad**
  (scatter + correlación) → ¿más concentración = más o menos brecha?
- **Detalle intra-sucursal por producto**: precio de **cada EAN en cada sucursal** (último mes).

> **Departamento**: hoy la geolocalización llega a **provincia** (por bounding box lat/lon) y a
> **localidad** (campo `sucursales_localidad` del maestro, con su caveat de fiabilidad — muchas
> vienen `nan`). Departamento requeriría un **shapefile departamental** que el proyecto no tiene;
> queda como mejora futura.

---

## 6. Configuración (CELDA 1)

```python
TIPOS = {
    'Fideos secos': {'qty': 4, 'tacc': ['EAN1','EAN2','EAN3'], 'sin_tacc': ['EAN4','EAN5','EAN6']},
    # ...
}
MIN_TIPOS            = 3   # mínimo de tipos presentes (ambos lados) por sucursal/día
VENTANA_DIARIA_MESES = 3   # meses de detalle diario (semanal/mensual usan todo el histórico)
MES_INICIO_HISTORICO = '2024-01'
CADENAS_FILTRAR      = {'19','2013','3001','4'}   # estaciones de servicio / no minoristas
```

### 6.1. Plantilla precargada — LISTAS AMPLIAS (4 tipos like-for-like)

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

## 7. Outputs

### Gráficos (`.png`)
| Archivo | Contenido |
|---------|-----------|
| `brecha_mensual_MMAAAA.png` | Serie mensual de la brecha (mediana + promedio) + media del período |
| `brecha_diaria_MMAAAA.png` | Serie diaria (ventana) |
| `brecha_provincia_MMAAAA.png` | Brecha por provincia |
| `brecha_cadena_MMAAAA.png` | Brecha por cadena (≥5 sucursales) |
| `brecha_concentracion_MMAAAA.png` | Scatter brecha vs. nº de sucursales por localidad (+ correlación) |
| `mapa_brecha_MMAAAA.png` | Mapa coroplético de la brecha por provincia |

### Mapa interactivo (`.html`) — CELDA 12
| Archivo | Contenido |
|---------|-----------|
| `mapa_sucursales_brecha_MMAAAA.html` | **Mapa Folium por sucursal** (último mes): un punto por supermercado georreferenciado, color **verde→rojo** graduado por la brecha de canasta. Popup con: (1) valor de cada canasta (convencional/celíaca, índice $/100g ponderado) y **% de brecha**; (2) tabla de comparación **uno-vs-uno** de productos por tipo (convencional con TACC vs sin-TACC), con **presentación (gramos) y $/100g**; (3) cadena y localidad/provincia; (4) n° de tipos comparados. Leyenda + caja de resumen (n sucursales, brecha mediana nacional). |

### Excel — `brecha_celiaca_YYYY-MM.xlsx`
| Hoja | Contenido |
|------|-----------|
| `Cobertura` | **diagnóstico**: por tipo, nº de sucursales que ofrecen TACC, sin-TACC y **ambos** (todo el período) |
| `Brecha_tipo` | **el número clave**: por tipo, precio TACC vs sin-TACC en `$/100g`, brecha (mediana + promedio), `n_tacc`/`n_sin` |
| `Brecha_tipo_mes` / `Brecha_tipo_prov` | la brecha por tipo desagregada por mes (evolución) y por provincia |
| `Serie_diaria` / `Serie_semanal` / `Serie_mensual` | brecha pooled nacional: mediana y promedio, base/celíaca medianas, nº sucursales |
| `Brecha_provincia` | brecha pooled por provincia (mediana + promedio) |
| `Brecha_cadena` | brecha pooled por cadena |
| `Concentracion` | por localidad: nº de sucursales + brecha (base del scatter) |
| `Brecha_sucursal` | **intra-sucursal** (best-effort, último mes): sucursales que ofrecen ambos lados — base, celíaca, brecha, nº tipos |
| `Detalle_producto` | **precio por sucursal × EAN** (último mes), con tipo, rol (tacc/sin) y descripción |

---

## 8. Arquitectura (celdas del generador)

`notebooks/gen_nb06.py` → `06_evolucion_brecha_celiaca.ipynb` (12 celdas). Reusa de nb05 la
CELDA 2 (setup/mount), CELDA 3 (maestros) y CELDA 5 (funciones ZIP) **verbatim**.

- **CELDA 1** — Config (`TIPOS`, `MIN_TIPOS`, `VENTANA_DIARIA_MESES`, paths).
- **CELDA 4** — Parseo de `TIPOS`: sets `TIPO_TACC`/`TIPO_SIN`, `TIPO_QTY`, mapas `EAN_TIPO`/`EAN_ROL`/`EAN_DESC`.
- **CELDA 6** — Lectura **diaria**: melt de las columnas `precio_YYYYMMDD` conservando `fecha`;
  cache `brecha_dia_{hash}_v1.parquet` de **meses cerrados** + **mes en curso fresco**; factor
  centavos/pesos por mes anclado a `REF_EANS_FACTOR`.
- **CELDA 7** — Brecha vectorizada: promedio de representativos por (suc, día, tipo, rol) →
  pivot rol→`tacc`/`sin` (solo tipos con ambos lados) → canasta base/celíaca por (suc, día) con
  `n_tipos ≥ MIN_TIPOS` → `brecha_pct`; merge con geo (provincia por bbox, cadena, localidad).
- **CELDA 8** — Series (`_serie()`: mediana + `_pmean`) diaria (ventana) / semanal / mensual +
  `brecha_prov` / `brecha_cadena` / `concentracion`.
- **CELDA 9** — 5 gráficos. **CELDA 10** — coroplético. **CELDA 11** — Excel.

`_pmean` = media con outliers fuera (banda `[mediana/4, mediana×4]`), la misma que nb02/nb05.

---

## 9. Validación

- `ast.parse` OK; **11/11 celdas compilan**.
- **Test end-to-end sintético** (celdas 7→11 ejecutadas de verdad con matplotlib + openpyxl):
  con 3 tipos y una prima inyectada del 9%, la brecha mediana global da **+9,07%**; un outlier
  100× **no** la infla; se generan las 8 hojas de Excel (incluida `Detalle_producto`) y 6 PNGs.
- **Pendiente**: correr en Colab con datos reales (los tests son sintéticos). Requiere en
  `carga/` los ZIPs SEPA y `ar.json` (para el mapa); los maestros se descargan solos.

---

## 10. Limitaciones y mejoras futuras

- **Cobertura de los representativos**: no se usa (todavía) la métrica de cobertura del
  `canasta_representativa`; la plantilla se curó por marca mainstream. El primer run + la hoja
  `Detalle_producto` muestran qué EANs aparecen en pocas sucursales para reemplazarlos.
- **Departamento**: falta shapefile departamental (hoy: provincia + localidad).
- **Tipos ambiguos**: galletitas saladas (arroz vs trigo) y harina/premezcla (sustitución) —
  ver caveats en §6.1. La decisión de incluirlos es del investigador.
- **Posible extensión**: agregar más tipos con dicotomía (cereales/copos, budines, tapas de
  empanada, cerveza→sidra), y una versión de la brecha ponderada por gasto celíaco si se
  consigue una fuente de ponderaciones.

---

## 11. Cómo continuar (otra sesión / otra PC)

1. El generador es la fuente de verdad: `python notebooks/gen_nb06.py` regenera el `.ipynb`.
2. Para un primer resultado, correr nb06 **tal cual** (ya trae `TIPOS` con datos reales).
3. Ajustar `TIPOS` según lo que muestre `Detalle_producto` (cobertura por EAN/sucursal).
4. Handoff y detalle por celda: `.claude/memory.md` (sección "Notebook 06").

---

## 12. Resultados de referencia (run real, agosto 2026 — versión limpia)

Estimador **primario = mediana** (§3.3), listas sin-TACC ampliadas con el Maestro, **filtro de
plausibilidad inflación-robusto** (§3.8) y Maná **incluido** (no se saca a mano). 1.816.833 obs
sucursal×EAN×mes · **2.532 de 2.742 sucursales con ≥1 par** · 32 meses (2024-01 → 2026-08).

**Brecha por tipo (intra-super, $/100 g, mediana):**

| Tipo | TACC | sin-TACC | Brecha (mediana) | "más barato" (ilustr.) | n suc. (ambos) |
|---|--:|--:|--:|--:|--:|
| Galletitas dulces | 773,7 | 1.300,0 | **+66,0 %** | +106,4 % | 802 |
| Fideos secos | 276,5 | 795,0 | **+172,9 %** | +256,5 % | 1.291 |
| Galletitas saladas | 502,1 | 1.538,0 | **+187,7 %** | +162,7 % | 1.332 |
| Pan rallado | 313,8 | 949,8 | **+194,4 %** | +209,4 % | 727 |

**Canasta acotada:** +173,8 % (ago-2026), desde +102,3 % (ene-2024) → +71 pp.
Prov. menor: Entre Ríos (+116 %) · mayor: Misiones (+222 %). Correlación brecha–concentración −0,07.

> **El filtro de plausibilidad descartó 3 EANs** (transparentes en la salida): Smams chocolate
> ($184/100 g, error de carga) y **dos "sin TACC Matarazzo" (`7790070321800`, `7790070321855`)
> con precio de fideo convencional (~$207/100 g)** — mal etiquetados en el Maestro; Matarazzo tiene
> su verdadera línea GF con otros EANs (`7790070335xxx`, ~$970/100 g, alta cobertura), que sí se
> usan. Es una **validación** de que la regla atrapa errores de etiquetado sin curación a mano.
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
