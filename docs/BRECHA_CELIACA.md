# Brecha Celíaca (TACC vs sin-TACC) — `06_evolucion_brecha_celiaca`

Documento técnico del **Notebook 06**. Mide la **brecha** entre una canasta **base**
(productos con TACC) y su equivalente **sin-TACC** (canasta celíaca), y su evolución
**diaria, semanal y mensual**, desagregada por provincia, cadena y concentración de
comercios.

Última actualización: 2026-08-21.

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

## 3. Definición de las canastas y de la brecha

> **✅ Método vigente (2026-08, tras 4 runs reales): brecha INTRA-SUPERMERCADO por (sucursal, MES),
> listas amplias de candidatos, precio $/100g.** Para cada **sucursal** y **mes**, por tipo, se usa
> el precio ($/100g) de **los candidatos que esa sucursal tuvo ese mes** (mediana, sobre todos sus
> días → robusta a un EAN mal cargado). Un tipo cuenta si la sucursal tuvo ≥1 candidato TACC y ≥1
> sin-TACC **en ese mes** (NO exige el mismo día → mucho más robusto que la versión por-día, que
> daba n=1). La brecha del tipo se calcula **dentro del mismo super**, y luego se **promedia entre
> supers** (mediana + promedio), con desagregación por provincia/cadena/localidad. El **output
> principal es la brecha POR TIPO** (`brecha_tipo`). La granularidad es **mensual** (diaria/semanal
> no aplican a este método y salen vacías). La hoja `Cobertura` muestra cuántas sucursales ofrecen
> cada lado por tipo.
>
> **✅ EANs TACC curados [2026-08-25]**: los EANs TACC (regular) de la CELDA 1 se reemplazaron por
> los de **alta cobertura** de `canasta_representativa_2026-07.xlsx` (hoja `Candidatos`, que sí trae
> `n_sucursales` por producto — el Maestro no). Se filtró por subcategoría (Pastas Secas, Galletitas
> Dulces/Saladas, Pan Rallado y Rebozadores) y se eligieron los de mayor cobertura (~1900-2500
> sucursales), excluyendo premium/snacks (Kit Kat, Oreo, Don Vicente, Saladix…) que distorsionan el
> `tacc_100` en $/100g. Fideos: Lucchetti/Matarazzo/Favorita 500g · Galletitas dulces: 9deOro, Don
> Satur, Chocolinas, Bagley Rumba, Sonrisas, Maná · Galletitas saladas: 9deOro, Don Satur, Traviata,
> Tosti, Hogareñas · Pan rallado: Preferido, Mamá Cocina, Lucchetti, Pureza, Favorita.
> **Limitación remanente**: el lado **sin-TACC** es de cobertura intrínsecamente baja (productos
> celíacos = nicho); la brecha por tipo solo se calcula donde una sucursal tenga ambos lados. Revisar
> la hoja `Cobertura` tras el primer run y afinar las listas sin-TACC de los tipos con pocos supers.
>
> *(Historia: el 1er run con la condición estricta "ambos lados misma sucursal el MISMO DÍA, ≥3
> tipos" dio 0 obs por baja cobertura sin-TACC; una versión intermedia usó pooling por grupo. La
> versión final es intra-sucursal por tipo + listas amplias + $/100g, que es lo pedido.)*

> **⚠️ Sub-sección histórica (pooled)** — se conserva por trazabilidad; el método vigente es el
> de arriba (intra-sucursal por tipo):

### 3.1. Cálculo POOLED por grupo (método principal)

Para un **grupo `G`** (nacional, provincia, cadena o localidad) y un **período `P`** (día,
semana o mes):

1. Para cada **tipo `t`**:
   - `precio_base(t,G,P)` = **mediana** (y **promedio** con outliers fuera) del precio TACC del
     tipo sobre **las sucursales del grupo `G` que ofrecen TACC** en `P`.
   - `precio_cel(t,G,P)`  = ídem sobre las sucursales del grupo que ofrecen **sin-TACC**.
   - El tipo cuenta si hay ≥1 sucursal con TACC **y** ≥1 con sin-TACC en `G,P` (no exige que sea
     la misma sucursal).
2. `B(G,P) = Σ_t precio_base × qty(t)` ; `C(G,P) = Σ_t precio_cel × qty(t)` (sobre tipos con
   ambos lados en `G,P`).
3. `brecha_pct(G,P) = (C / B − 1) × 100`, para **mediana** y **promedio** por separado.

Al pooolear dentro del grupo, la brecha es robusta a la baja cobertura y sigue siendo comparable
entre provincias/cadenas. El **precio del tipo en una sucursal/día** sigue siendo el promedio de
los representativos presentes de ese lado (§2.2). Para las desagregaciones (provincia/cadena/
localidad) la brecha del grupo = **mediana de las brechas mensuales** del grupo.

> **Trade-off honesto**: al no exigir la misma sucursal, la canasta base y la celíaca de un grupo
> pueden apoyarse en **sucursales distintas** (las que venden cada lado). Es el precio a pagar por
> la baja cobertura sin-TACC. Se mitiga agrupando (provincia/cadena/localidad concentran sucursales
> comparables) y se documenta en la hoja `Cobertura`.

### 3.1b. Normalización por $/100g y BRECHA POR TIPO (lo importante)

> **⚠️ Corrección 2026-08 (segundo run real)**: la canasta pooled agregada daba **+237%** — no
> es una prima uniforme sino la mezcla de tipos con brecha muy distinta y con dos distorsiones:
> **(a)** presentaciones diferentes (harina 1 kg vs premezcla 400 g) y **(b)** EANs de baja
> cobertura o precio espurio (fideos TACC en 7 sucursales con precio irreal).

Dos cambios corrigen esto:

1. **Precio normalizado a `$/100g`**: cada EAN se divide por su presentación (gramos/ml del maestro:
   `producto_cantidad_presentacion` × unidad → gramos). Así 500 g vs 1 kg vs 400 g son comparables.
   EANs sin presentación caen a precio por paquete (con aviso).
2. **La brecha se reporta POR TIPO** (`brecha_tipo`, `brecha_tipo_mes`, `brecha_tipo_prov`): para
   cada tipo, precio TACC vs sin-TACC en `$/100g`, con `n_tacc`/`n_sin` (sucursales de cada lado).
   **Este es el número clave**, no la canasta agregada.

**Hallazgo (no es un bug)**: la brecha por producto TACC-sustituible es **grande** (galletitas ~+140/200%,
pan rallado ~+320%), muy por encima del ~9% de la canasta **completa** Celíaca Media. Es coherente con
lo que buscaba Fernando: el 9% "maquilla" la brecha real porque promedia productos **naturalmente sin
gluten** (carne, lácteos, verdura) con 0% de prima. Al aislar los productos con dicotomía, la prima real
aparece. **Se debe reportar por tipo** (no como una canasta única), y **vetando cada tipo con
`n_tacc`/`n_sin` y `Cobertura`** (descartar tipos con un lado en muy pocas sucursales, y la
harina/premezcla que es sustitución, no like-for-like).

### 3.2. Brecha intra-sucursal (best-effort)

Además se calcula, **por sucursal × mes** (no día), la brecha para las sucursales que **sí**
ofrecen ambos lados (típicamente grandes cadenas con línea sin-TACC). Sale en la hoja
`Brecha_sucursal`. Puede ser un subconjunto chico; la hoja `Cobertura` muestra cuántas sucursales
ofrecen cada lado y **ambos** por tipo.

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
