# Metodología — ICR (Índice de Consumo Representativo)

**Última actualización:** 2026-09-03 (nb07: 5 canastas + 33 frescos por categoría + Representativa calibrada INDEC + región; nb02: `datos_econometria`)
**Período de referencia:** enero 2024 – abril 2026

---

## 1. Fuente de datos: SEPA

El **Sistema Electrónico de Publicidad de Precios Argentinos (SEPA)** es un registro administrativo del Ministerio de Economía de Argentina que obliga a las principales cadenas de supermercados a publicar diariamente sus precios de lista. Los datos son públicos y se descargan desde [datos.produccion.gob.ar/dataset/sepa-precios](https://datos.produccion.gob.ar/dataset/sepa-precios).

### Formato utilizado

Se usa el **formato semestral** (archivos `MMAAAA_pais_parteNCOMPLETO.csv.gz` dentro de ZIPs `YYYYS.zip`), que contiene precios en formato **wide**: una fila por (producto × sucursal), con una columna de precio por día del período. Cada semestre cubre ~50 millones de filas.

### Cadenas cubiertas

El SEPA semestral cubre 16 banners comerciales de las principales cadenas nacionales, identificados por la combinación `(id_comercio, id_bandera)`:

| Corporativo | Banners |
|-------------|---------|
| Cencosud | Vea · Disco · Jumbo |
| Carrefour | Carrefour · Market · Express |
| Walmart/ChangoMas | ChangoMas · Hiper · Mi ChangoMas |
| Libertad | Hipermercado · Mini Libertad |
| La Anónima | La Anónima |
| Coto | Coto |
| Cooperativa Obrera | Cooperativa Obrera |
| DIA | DIA |
| Regionales | Toledo · Pasamonte · LAR · Cadena 8 · Misiones |

### Cobertura geográfica

Las 24 provincias de Argentina. Aproximadamente 3.600 sucursales con coordenadas válidas.

### Factor de escala de precios

Los datos SEPA hasta mediados de 2025 estaban en **centavos** (factor ÷100). Desde **2025B en adelante los datos ya vienen en pesos** (factor = 1). El código autodetecta el factor mediante la mediana de precios: si supera $10.000 → divide por 100.

---

## 2. Notebook 01 — Selección de productos (universo de canasta)

### Score de cobertura

El criterio central de selección es el `score_cobertura`, que mide qué tan disponible está un producto en todo el país:

```
score_cobertura = (pct_cadenas × 0.5 + pct_provincias × 0.5) × pct_dias_promedio
```

Donde:
- `pct_cadenas` = grupos corporativos con el producto / total grupos activos (típicamente 5)
- `pct_provincias` = provincias con el producto / total provincias activas (típicamente 24)
- `pct_dias_promedio` = fracción promedio de días del período con precio reportado

Un score de 1.0 indica presencia en **todas las cadenas, todas las provincias y todos los días**.

### Umbrales de filtrado

**Umbrales estrictos** (hojas Canasta y Candidatos):
- `MIN_CADENAS`: todos los grupos corporativos activos (~5)
- `MIN_PROVINCIAS`: todas las provincias activas (~24)
- `MIN_SUCURSALES`: ≥50 sucursales
- `MIN_PCT_DIAS`: ≥50% de los días con precio

**Umbrales amplios** (hoja Selección):
- `MIN_CADENAS_SEL`: ≥3 grupos corporativos
- `MIN_PROVINCIAS_SEL`: ≥18 provincias
- `MIN_SUCURSALES_SEL`: ≥30 sucursales
- `MIN_PCT_DIAS`: igual al estricto (≥50%)

### Output del Notebook 01

El archivo `canasta_representativa_YYYY-MM.xlsx` tiene **4 hojas**:

| Hoja | Contenido | Uso |
|------|-----------|-----|
| `Canasta` | ~65 productos seleccionados automáticamente (11 grupos) | Referencia de cobertura máxima |
| `Candidatos` | ~3.650 productos con umbrales estrictos + maestro completo | Análisis de trazabilidad |
| `Selección` | ~25.000 productos con umbrales amplios | **Fuente del notebook 02**: el economista completa las columnas de cantidad |
| `Productos unicos` | ~75.000 productos sin umbrales (solo con rubro en maestro) | Exploración libre |

### Columnas de cantidad en la hoja Selección

La hoja `Selección` tiene **6 columnas de cantidad** (amarillas), una por canasta:

| Columna | Canasta | Descripción |
|---------|---------|-------------|
| `cantidad_01` | Vulnerable | Q1 — Coef. Engel ~36% |
| `cantidad_02` | Popular | Q2 — Coef. Engel ~28% |
| `cantidad_03` | Media | Q3-Q4 — Coef. Engel ~22% |
| `cantidad_04` | Media Alta | Q5 — Coef. Engel ~15% |
| `cantidad_05` | Canasta 05 | Libre |
| `cantidad_06` | Canasta 06 | Libre |

Solo se procesan las columnas con al menos un producto con cantidad > 0. Las columnas vacías se ignoran.

---

## 3. Canastas ICR — Metodología ENGHo

Las 4 canastas nombradas se construyeron aplicando la metodología de la **Encuesta Nacional de Gastos de los Hogares 2017/18 (ENGHo)** del INDEC.

### Coeficiente de Engel por quintil

El coeficiente de Engel (CE) es la fracción del gasto total dedicada a alimentos y bebidas. A mayor ingreso, menor es el CE. Los valores para Argentina (ENGHo 2017/18) son aproximadamente:

| Quintil | Canasta | CE aprox. | Caracterización |
|---------|---------|-----------|-----------------|
| Q1 | Vulnerable | ~36% | Hogares con mayores restricciones de consumo |
| Q2 | Popular | ~28% | Hogares de ingreso bajo-medio |
| Q3-Q4 | Media | ~22% | Hogares de clase media |
| Q5 | Medio-Alto | ~15% | Hogares de mayor poder adquisitivo |

### Criterio de selección de productos

Para cada canasta se aplicó un **doble filtro de calidad**:

1. **`score_cobertura >= 0.88`**: el producto debe tener presencia nacional robusta
2. **`pct_trazabilidad >= 90%`**: el producto debe haber estado en el SEPA al menos en el 90% de los meses del período de referencia (ene-2024 → abr-2026 = 28 meses)

**Filtro de precio por percentil** según quintil:
- Vulnerable: precios ≤ P33 de su categoría
- Popular: P25–P55
- Media: P40–P70
- Medio-Alto: P55–P85

### Lógica de escalada entre canastas

Los productos de quintiles superiores son versiones premium de las mismas categorías:
- **Yerba**: Cachamai 500g (Vulnerable) → Liebig 500g (Popular) → Cachamate 1kg hierbas (Media) → Cbsé Hierbas Serranas 1kg (Medio-Alto)
- **Fideos**: Lucchetti 500g básicos (Vulnerable) → Matarazzo Penne (Popular) → Lucchetti Fettucini (Media) → Matarazzo Rigatti Rina (Medio-Alto)
- **Aceite**: Natura 900ml (Vulnerable) → Cocinero 1.5L (Popular) → Lira + Oliva puro (Media) → Cañuelas + Oliva EV (Medio-Alto)
- **Cerveza**: sin alcohol en Vulnerable → Schneider lata 473cc (Popular) → Heineken 473cc (Media) → Corona 355cc (Medio-Alto)

### Composición por categoría y canasta (v3, abril 2026)

| Categoría | Vulnerable | Popular | Media | Medio-Alto |
|-----------|-----------|---------|-------|------------|
| Pastas/Cereales | ✓ | ✓ | ✓ | ✓ |
| Arroz | ✓ | ✓ | ✓ | ✓ |
| Harina | ✓ | ✓ | ✓ | — |
| Aceite girasol | ✓ | ✓ | ✓ | ✓ |
| Aceite oliva | — | — | ✓ | ✓ |
| Yerba | ✓ | ✓ | ✓ | ✓ |
| Azúcar | ✓ | ✓ | ✓ | — |
| Leche | ✓ | ✓ | ✓ | ✓ |
| Yogur | ✓ | ✓ | ✓ | ✓ |
| DDL/Manteca/Margarina | ✓ | ✓ | ✓ | ✓ |
| Queso | ✓ | ✓ | ✓ | ✓ |
| Embutidos/Fiambres | ✓ | ✓ | ✓ | ✓ |
| Huevos | ✓ | ✓ | ✓ | ✓ |
| Tomate/Salsas | ✓ | ✓ | ✓ | — |
| Condimentos | ✓ | ✓ | ✓ | ✓ |
| Galletitas | ✓ | ✓ | ✓ | ✓ |
| Gaseosas/bebidas | ✓ | ✓ | ✓ | ✓ |
| Cerveza | — | ✓ | ✓ | ✓ |
| Vino | — | — | ✓ | ✓ |
| Espumante/Vodka | — | — | — | ✓ |
| Lavandina | ✓ | ✓ | ✓ | ✓ |
| Jabón en polvo | ✓ | ✓ | — | — |
| Detergente | ✓ | ✓ | ✓ | ✓ |
| Limpiador pisos/baño | ✓ | ✓ | ✓ | ✓ |
| Papel higiénico | ✓ | ✓ | ✓ | ✓ |
| Suavizante/quitamanchas | — | ✓ | ✓ | ✓ |
| Jabón tocador | ✓ | ✓ | ✓ | ✓ |
| Shampoo/acondicionador | ✓ | ✓ | ✓ | ✓ |
| Crema dental/cepillo | ✓ | ✓ | ✓ | ✓ |
| Desodorante | ✓ | ✓ | ✓ | ✓ |
| Crema corporal/facial | — | ✓ | ✓ | ✓ |
| Congelados | — | ✓ | ✓ | ✓ |

### Totales de productos y unidades por canasta (v3)

| Canasta | Productos | Unidades/mes |
|---------|-----------|--------------|
| Vulnerable | 46 | ~170 |
| Popular | 61 | ~220 |
| Media | 73 | ~280 |
| Medio-Alto | 77 | ~300 |

---

## 4. Notebook 02 — Metodología de cálculo

### Cálculo del costo de canasta por sucursal

Para cada sucursal `s` y cada canasta `k`:

```
costo_canasta(s,k) = Σ_p [precio(p,s) × cantidad(p,k)]
```

Si un producto `p` no tiene precio en la sucursal `s`, se imputa con el **precio promedio nacional** de ese producto en el mes en cuestión (`precio_prom_nac[p]`). Una sucursal se incluye en el análisis solo si reporta precios propios para al menos `MIN_PRODUCTOS_PROPIOS` productos de la canasta (default: 15, con auto-ajuste si la canasta tiene pocos productos).

### Serie histórica y caché

La **serie histórica** se construye una sola vez para la **unión de todos los EANs activos** de todas las canastas activas. El resultado se almacena en un caché parquet `hist_union_{hash}.parquet`. El hash es un MD5 de los EANs de la unión; cambia cuando se agrega o quita un EAN de cualquier canasta, pero no cuando solo cambian las cantidades.

Para cada canasta, la serie mensual se calcula a partir del caché:
```
costo_mensual(mes, k) = Σ_p [precio_mediano_nacional(p, mes) × cantidad(p,k)]
```

donde `precio_mediano_nacional(p, mes)` es la mediana de precios de ese EAN en todo el país para ese mes.

### Índice de precio (base variable)

Los gráficos de evolución normalizan a base = 100 en el mes configurado como `MES_INICIO_GRAFICO` (default: marzo 2024). El mes base se auto-adapta al primer mes disponible si no está en la serie.

### Comparación con IPC INDEC

El IPC INDEC se carga desde `IPC.xlsx` (columna `Nivel general` y `Alimentos y bebidas no alcohólicas`). Ambas series se indexan a la misma base para comparación directa.

### Promedio nacional ponderado por población

El promedio nacional del costo de canasta se calcula ponderando por la población de cada provincia (Censo 2022, 45.9M habitantes):

```
promedio_nacional = Σ_prov [costo_mediano(prov) × población(prov)] / Σ_prov [población(prov)]
```

Solo se incluyen las provincias con datos en el período.

### Doble análisis: MEDIANA y PROMEDIO (desde 2026-08)

Todos los cálculos del Notebook 02 (y del Notebook 05) se hacen por partida doble, con dos medidas de tendencia central, y se exportan en paralelo (nombres base = mediana; sufijo `_prom` = promedio):

- **Precio por sucursal**: agregando sobre **todos los días del mes** del SEPA (antes: solo el primer día). Mediana de los días, y **media con outliers fuera** de los días.
- **Media con outliers fuera** (`_pmean`): en cada grupo se descartan los valores fuera de `[mediana/4, mediana×4]` —errores gruesos de carga del SEPA (100×, centavos sueltos)— y recién después se promedia. Funciona a cualquier tamaño de muestra, a diferencia de un recorte por percentil.
- **Coherencia por niveles**: cada análisis usa su estadístico en TODOS los niveles. El *análisis mediana* usa mediana en sucursal→provincia→cadena→barrio y mediana provincial ponderada por población; el *análisis promedio* usa `_pmean` en todos esos niveles.

Por qué tener ambos: para las canastas (muchos productos) mediana ≈ promedio, y la media sirve de chequeo de robustez. Para productos individuales con precio de lista "pegajoso" (que se cuantiza a valores redondos), la mediana escalona y da variaciones 0% espurias, mientras que el promedio captura mejor la trayectoria mensual. El IPC del INDEC, para contraste, no usa mediana: es una canasta fija ponderada por gasto (ENGHo) con promedios de relativos de precio sobre una muestra relevada.

---

## 5. Trazabilidad temporal como métrica de calidad

La **trazabilidad** de un producto mide en qué fracción de los meses del período de análisis estuvo disponible en el SEPA:

```
pct_trazabilidad = meses_con_precio / total_meses × 100
```

### Distinción importante: producto nuevo vs. inestable

Un `pct_trazabilidad` bajo puede deberse a dos causas muy distintas:

| Causa | Diagnóstico | Interpretación |
|-------|-------------|----------------|
| **Nuevo producto** | `primer_mes > MES_INICIO_HISTORICO` y trazabilidad desde entrada = 100% | No es inestable — simplemente entró tarde al SEPA |
| **Producto inestable** | `primer_mes = MES_INICIO_HISTORICO` y trazabilidad < 100% | Desaparece y reaparece — problema real de disponibilidad |

El Notebook 02 (CELDA 20) calcula trazabilidad para todos los ~3.650 Candidatos y la presenta con esta distinción.

### Umbral recomendado

Para que un producto sea incluido en una canasta de análisis temporal, se recomienda:
- `pct_trazabilidad >= 90%` desde la fecha de primera aparición
- Para productos nuevos (primer_mes > MES_INICIO_HISTORICO): verificar que sea 100% estable desde su entrada

---

## 6. Limitaciones conocidas

### Productos no cubiertos por SEPA

- **Carnes frescas, frutas y verduras**: no tienen cobertura nacional suficiente en SEPA para superar los umbrales estrictos. Las canastas no incluyen estos ítems.
- **Pan**: muy baja cobertura en supermercados de cadena (se vende principalmente en panaderías, fuera del SEPA).
- **Servicios y alquileres**: fuera del alcance del SEPA (precios de bienes físicos únicamente).

### Cadenas no cubiertas

El SEPA cubre las cadenas de supermercados obligadas a reportar. Los comercios de proximidad, almacenes y mercados locales **no están incluidos**, por lo que los precios del ICR pueden diferir de los precios efectivamente pagados por hogares de bajos ingresos (que consumen más en comercios de barrio).

### Identificación de cadenas en formato semestral

En el formato semestral, `id_bandera` representa el grupo corporativo (5 valores), no el banner comercial (16 valores). Para obtener el banner real se combina `(id_comercio, id_bandera)`. El ICR usa `id_bandera` para los umbrales y el score (métrica de grupos corporativos), e informa `n_cadenas_com` (banners reales) como dato adicional no vinculante.

### PLU codes (prefijo 27.../28...)

Los productos vendidos por peso en góndola (frutas, verduras, fiambres a granel) tienen EANs generados en balanza con prefijo 27... o 28..., que son efímeros. No aparecen en el SEPA histórico de forma consistente. Si se incluyen en una canasta, la serie histórica quedará vacía y los gráficos de evolución no estarán disponibles para esos productos.

### Precios de lista vs. precios efectivos

El SEPA publica precios de lista. No incluye descuentos por tarjeta, promociones puntuales ni precios de segunda unidad. Los precios efectivamente pagados por los consumidores pueden ser menores, especialmente en cadenas con programas de fidelización intensivos (DIA, ChangoMas).

---

## 6b. Canastas especiales (cantidad_05 y cantidad_06)

### Celíaca Media (`cantidad_05`)

Variante sin TACC de la Canasta Media. Metodología: reemplazar todos los productos con gluten (trigo, cebada, centeno) por equivalentes sin TACC disponibles en SEPA con buena cobertura.

| Producto con gluten | Reemplazo sin TACC | EAN reemplazo |
|--------------------|--------------------|---------------|
| Fideos de trigo (Lucchetti) | Fideos Mostacholes sin TACC Blue Patna | 7730114100077 |
| Harina de trigo (Caserita) | Almidón de Maíz Maizena 500 Gr | 7794000007468 |
| Galletitas Traviata | Galletas Arroz sin TACC Grandiet + Chalitas Happy Food | 7797330102377 / 7798308250410 |
| Alfajor Bagley B&N | Galletitas Smams Chocolate sin TACC | 7798181511011 |
| Cacao Chocolino | Cacao sinTACC Nesquik 800 Gr | 8445291121904 |
| Caldo de carne Knorr | Caldo de Verdura Knorr (sin gluten) | 7794000008557 |
| Cerveza Heineken (malta/cebada) | Sidra Saenz Briones 1888 | 7790119002370 |
| Avena | Eliminada (avena es controvertida para celíacos) | — |

**Comparación**: Media estándar → diferencia revela la **prima celíaca** en Argentina.  
**Costo real confirmado (abril 2026)**: **$691.836 ARS (+9.0% sobre Media $634.923)**.  
**Hallazgo**: la prima celíaca es del ~9%, mayor de lo estimado inicialmente. El mayor impacto viene de pasta sin TACC ($5.809 Blue Patna vs $2.200 Lucchetti), sidra ($10.775 vs $3.630 Heineken) y Almidón Maizena. La dispersión provincial es menor que en canastas estándar (rango Formosa−Santa Cruz de 5.3% vs 6.7% en Media).

### Vegana Básica (`cantidad_06`)

Dieta vegana integral basada en alimentos completos (whole foods), sin sustitutos procesados de productos animales. Refleja el patrón alimentario vegano accesible en Argentina (legumbres + cereales + vegetales).

**Eliminados** (productos animales): lácteos, carnes, huevos, pescado.  
**Reemplazados por**: legumbres (porotos × 6, garbanzos × 4), proteína vegetal (Not Chicken × 4), bebida vegetal (Ades Soja × 12).

**Comparación**: Popular → diferencia revela si el veganismo integral es más barato o más caro que la dieta estándar Q2.  
**Costo real confirmado (abril 2026)**: **$427.033 ARS (−5.4% vs Popular $451.672)**.  
**Hallazgo**: la dieta vegana básica es efectivamente más barata que Popular pero la diferencia es moderada (−5.4%, no −14% como se estimaba). El Ades Soja y el Not Chicken son relativamente caros y compensan el ahorro de no comprar carnes. Ordenamiento definitivo: Vulnerable $252k → **Vegana Básica $427k** → Popular $451k → Media $634k → **Celíaca Media $691k** → Media Alta $879k. La Vegana queda entre Vulnerable y Popular (94.5% del costo Popular).

**Advertencia metodológica**: los productos de higiene y limpieza incluidos son los mismos que en Popular (no están específicamente certificados como veganos). En un análisis estricto, habría que reemplazar por marcas sin ingredientes de origen animal.

---

## 7. Historial de versiones de canastas

### ICR (cantidad_01) — Canasta de referencia

Canasta de 51 productos seleccionados por score de cobertura, representando el consumo de una familia tipo 4 integrantes. Revisada en mayo 2026 para reemplazar 4 productos con baja trazabilidad:

| Sale | Entra | Motivo |
|------|-------|--------|
| Hamburguesas Paty 250g (82.1%, nuevo jun-2024) | Hamburguesas Swift XL 250g (100%) | Mayor trazabilidad |
| Lavandina Ayudín Original 2L (75%, nuevo ago-2024) | Lavandina Anti-splash Ayudín 2L (100%) | Mayor trazabilidad |
| Jabón Dove 90g (82.1%, nuevo jun-2024) | Jabón Plusbelle 125g (100%, score 0.994) | Mayor trazabilidad y masividad |
| Plax 250ml (82.1%, genuinamente inestable) | Listerine Antisarro 500ml (100%) | Único inestable real |

**Resultado post-revisión**: 99.4% trazabilidad promedio, 48/51 productos al 100%.

### Canastas ENGHo v1/v2 (abril 2026)

Primeras versiones basadas en ENGHo + coeficiente de Engel. Identificaron 4 EANs malformados y varios productos cuestionables metodológicamente.

### Canastas ENGHo v3 (junio 2026) — versión vigente

Correcciones aplicadas sobre v2:
1. 4 EANs malformados → EAN-13 con ceros iniciales completos
2. Coca Light → Coca Cola regular (Vulnerable)
3. Tic Tac → Caramelo Menthoplus (Vulnerable)
4. Oblea Gallo frutilla/yogur → Gallo Crackers plain (Vulnerable)
5. Pampa Brewing (artesanal) → Schneider Rubia 473cc (Popular) — más masiva y representativa de Q2
6. Tintura Nutrisse → Crema Facial Neutrógena Antiedad (Medio-Alto) — product de styling reemplazado por higiene
7. Huevos Carnave 6 Un agregados a todas las canastas (ausentes en v2)

---

## 8. Parámetros de configuración relevantes

| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| `MES_INICIO_HISTORICO` | `'2024-01'` | Primer mes de la serie histórica |
| `MES_INICIO_GRAFICO` | `'2024-03'` | Mes base del índice (= 100). Auto-adapta si no existe en la serie. |
| `MIN_PRODUCTOS_PROPIOS` | 15 | Mínimo de productos propios para incluir una sucursal. Auto-ajusta a `N_CANASTA // 2` si la canasta tiene menos productos. |
| `MIN_SUCURSALES_RANKING` | 10 | Mínimo de sucursales para aparecer en los rankings por cadena. |
| `USE_CACHE` | `True` | Reutiliza parquet histórico si el hash de EANs no cambió. |
| `score_cobertura >= 0.88` | — | Umbral mínimo recomendado para inclusión en canastas ENGHo |
| `pct_trazabilidad >= 90%` | — | Umbral mínimo recomendado de estabilidad histórica |

---

## 9. Notebook 06 — Brecha celíaca (TACC vs sin-TACC)

Herramienta dedicada a medir la **brecha** entre una canasta **base** (con TACC) y su
equivalente **sin-TACC** (celíaca), y su evolución **diaria, semanal y mensual**, desagregada por
provincia, cadena y concentración de comercios.

Resumen metodológico (detalle completo en **`docs/BRECHA_CELIACA.md`**):
- **Solo tipos con dicotomía celíaca** (fideos, galletitas, pan rallado, harina/premezcla…). Nada
  de limpieza/higiene/otros alimentos: la brecha se reporta sobre esa canasta acotada, sin maquillar.
- **2–3 EANs representativos por lado y por tipo, promediados** ("LOS" representativos): el precio
  del tipo en una sucursal/día = promedio de los presentes → robusto a faltantes y a la elección
  de una marca puntual.
- **Brecha intra-sucursal**: `brecha = canasta_celíaca / canasta_base − 1` por sucursal/día (misma
  composición de tipos), luego agregada por dimensión. Al ser intra-sucursal, el % es comparable
  entre provincias y cadenas.
- Agregación por **mediana** (robusta) y **promedio** (outliers fuera, `_pmean`), como nb02/nb05.
- Resolución **diaria** (ventana), **semanal** (ISO) y **mensual** (histórico completo), leyendo
  las columnas `precio_YYYYMMDD` de los semestrales.

Contraste con el **IPC del INDEC**: el IPC no usa mediana; es una canasta fija ponderada por gasto
(ENGHo) con promedios de relativos de precio sobre una muestra relevada. La brecha celíaca es un
indicador específico y complementario, no una réplica del IPC.

---

## 8. Notebook 07 — Canastas alternativas (semanal + frescos)

`07_evolucion_canastas_alternativas` calcula la evolución **semanal** del costo de tres canastas socioeconómicas (**Popular / Media / Ejecutiva**) y la compara con el IPC, desagregando por rubro (con drill-down hasta producto) y por provincia/cadena. Es el análisis de nb02 con dos diferencias: granularidad semanal y una composición que suma frescos.

### 8.1. Mapeo de canastas
Popular = canasta 2 (Popular, Q2 · P25-55) · Media = canasta 3 (Medio, Q3-Q4 · P40-70) · Ejecutiva = canasta 4 (Medio-alto, Q5 · P55-85) del proyecto de índices. Se leen de la hoja `Productos unicos` del `canasta_representativa_*.xlsx` (`cantidad_01/02/03`).

### 8.2. Composición híbrida (empaquetados por EAN + frescos por tipo)
- **Empaquetados**: un EAN estable con buena cobertura multi-cadena (marcas mainstream). Precio por sucursal-semana = mediana de los días. Cada producto lleva su rubro.
- **Frescos** (carne, frutas, verduras, huevos): el EAN de balanza (prefijo GS1 `2…`) **cambia por cadena** → no se puede seguir un EAN entre cadenas. Se seleccionan por **regla de nombre** (`inc`/`exc` regex con borde de palabra `\b`) sobre el maestro SEPA completo, que captura todas las variantes que cada cadena publica. El precio del **tipo** en una sucursal-semana = **mediana de las variantes presentes**, normalizado a la unidad del tipo:
  - `$/kg` (frutas, verduras, carne): `precio / gramos_presentación × 1000`. Los códigos de balanza "1 Kg" ya vienen en $/kg.
  - `$/docena` (huevos): `precio / unidades × 12`.

### 8.3. Costo de canasta por sucursal-semana (con imputación)
Para cada canasta, sucursal y semana:
`costo = Σ_ítems_presentes(precio_sucursal × cantidad) + [Σ_todos(mediana_nacional × cantidad) − Σ_presentes(mediana_nacional × cantidad)]`
es decir, cada ítem presente usa el precio de la sucursal y cada ítem faltante se imputa con la **mediana nacional de esa semana** (por EAN o por tipo). Se acumula por rubro para la desagregación. Una sucursal cuenta si tiene ≥ `FRAC_PRODUCTOS_MIN` (0.5) de los empaquetados de la canasta.

La serie nacional semanal es la **mediana** y el **promedio (outliers fuera)** del costo entre sucursales. La serie mensual (para el vs-IPC) agrega primero por sucursal-mes (mediana de sus semanas) y luego entre sucursales.

### 8.4. Desagregación por rubro (drill-down)
- **Nivel 1**: costo por rubro × semana (mediana entre sucursales) y participación % del último mes.
- **Nivel 2/3**: detalle por ítem (producto empaquetado o tipo fresco) del último mes con cantidad, precio unitario y costo.
Rubros de frescos: **Carne, Frutas, Verduras, Huevos** (además de Almacén, Bebidas, Frescos-lácteos/fiambres, Limpieza, Perfumería, Congelados de los empaquetados).

### 8.5. Qué NO se incluye y por qué
**Electrodomésticos / durables** (Informática, Climatización, Cocinas, TV, Heladeras, Lavado, Pequeños electrodomésticos) se **excluyen**: mediana de cobertura ~1 cadena y pocas provincias (solo 29% son geográficamente comparables vs 41% de alimentos), lo que rompería la representatividad geográfica y la estabilidad de la serie temporal (catálogo que entra/sale).

### 8.6. Diagnósticos para refinar
La CELDA 13 imprime cobertura por EAN empaquetado (`n_cadenas`/`n_provincias`/`n_sucursales` del último mes) marcando ítems **sin datos** o de **baja comparabilidad** (n_cadenas<3 o n_provincias<15), y cobertura por tipo fresco (nº de variantes capturadas por la regla). Es la base para iterar: se afinan `inc`/`exc` y las cantidades, y se reemplazan EANs poco comparables.

---

## 8.7. nb07 v5 (2026-09-04) — motor del informe semanal, estado vigente

Reescritura del motor para que la salida sea publicable semanalmente por el equipo de
economistas. Cinco cambios metodológicos y tres correcciones.

### La semana
Ventana de 7 días que **cierra el jueves** (viernes→jueves), etiquetada por la **fecha de
cierre** (`2026-09-03`). Antes se usaba semana ISO (lunes→domingo), que dejaba la última
semana incompleta al correr el viernes. Configurable con `DIA_CIERRE_SEMANA`.
El **mes dueño** de una semana es el del punto medio de la ventana (cierre − 3 días).

### Índice encadenado de muestra apareada
Problema que resuelve: cuando un producto entra o sale del SEPA, el costo total pegaba un
salto que se leía como inflación. Los saltos de 2026-W07/W31 y el "despegue" inicial de la
Femenina eran esto, no precios.

Para cada par de semanas consecutivas se calcula el ratio **solo con los ítems que tienen
precio en ambas**, y se encadena:

```
idx_t = idx_{t-1} × ( Σ_{i∈S_t} p_i,t · q_i ) / ( Σ_{i∈S_t} p_i,t-1 · q_i )
S_t = ítems con precio en t y en t-1
```

Es el tratamiento estándar de altas y bajas (mismo criterio que INDEC).

**Nivel en $**: se toma el costo de la canasta *completa* en la semana ancla (la última con
cobertura ≥95% de los ítems) y se retropola con el índice. Queda interpretable en pesos y sin
saltos de composición. Se exporta también `costo_directo` (la suma cruda) como referencia.

### Nacional ponderado por población
Antes el nacional era la mediana simple entre sucursales; como DIA aporta ~42% de las
sucursales con precios casi uniformes, el "nacional", CABA, Buenos Aires y Centro/Pampeana
daban **exactamente el precio de DIA**. Ahora: mediana por provincia → promedio ponderado por
**población provincial** (`PESOS_POBLACION`). Configurable con `AGG_NACIONAL`.

### Arrastre y trazabilidad
Si un ítem falta una semana se arrastra su último precio nacional conocido, hasta
`MAX_SEMANAS_ARRASTRE` (8). Ausencias más largas quedan en NaN y entran en la hoja
**`Alertas_reemplazo`** (ítem, canastas afectadas, última semana con dato). La hoja
**`Presencia_items`** es la matriz ítem × mes con el % de semanas del mes con dato real:
muestra exactamente cuándo entró o salió cada producto.

### Filtro de outliers intra-tipo (frescos)
Dentro de cada **sucursal-semana**, antes de tomar la mediana de las variantes de un tipo, se
descartan las que caen fuera de `[mediana/K, mediana×K]` con `K = FRESCO_OUTLIER_K = 2.5`.
Protege del caso "precio por unidad cargado como precio por kilo" y de gramajes mal cargados,
que es el riesgo real de normalizar $/kg sobre EANs de balanza.

### Provincia y región controlando por cadena
Las cadenas se distribuyen asimétricamente (Coto opera en pocas provincias, La Anónima domina
la Patagonia, DIA está en casi todas). Comparar el costo crudo entre provincias mezcla el
efecto-precio con el efecto-mix-de-cadenas. Se agrega:

```
idx_vs_nacional(prov) = 100 × Σ_c w_c · [ precio_c,prov / precio_c,nacional ]   (w_c = sucursales)
```

Es decir: cada cadena se compara **consigo misma** entre la provincia y el país, y después se
promedia. 100 = igual al nacional. El costo crudo se sigue reportando al lado.

### Composición ampliada
- **196 EANs empaquetados** únicos: Popular 66, Media 100, Ejecutiva 104, Tecnológica 14,
  Representativa 108, Femenina 16. Todos con **≥4 cadenas, ≥15 provincias, ≥800 sucursales**
  (durables ≥3/≥10/≥90). Se seleccionan por escalera de calidad por slot (pick P/M/E, la
  Representativa usa el pick de Media con fallback a Popular).
- **59 tipos de frescos** (antes 33), con rubros nuevos: **Pollo** separado de Carne,
  **Cerdo**, **Pescado**, **Fiambres y Quesos** (por kg, de balanza) y **Panadería**
  (pan francés por kg). Cada tipo admite `gmin` propio (los quesos y fiambres usan 500 g).

### Correcciones
1. **Provincia**: la normalización era sensible a mayúsculas y acentos, así que `San juan`
   no matcheaba y caía en la región `Otras`. Ahora el lookup normaliza (sin acentos,
   minúsculas) y `REGION_PROV`/`PESOS_POBLACION` se reindexan con el mismo criterio.
2. **Conteo de sucursales**: se contaba `id_sucursal` solo, que no es único entre cadenas.
   Ahora se cuenta la terna `id_comercio|id_bandera|id_sucursal` (`suc_id`).
3. **Cobertura mínima por sucursal**: `FRAC_PRODUCTOS_MIN` pasa de 0.5 a **0.8**. Con 0.5 una
   sucursal con la mitad de los ítems quedaba casi enteramente imputada al precio nacional,
   lo que comprimía artificialmente las diferencias entre cadenas.

### Nota sobre el IPC
La serie del IPC se ve casi recta en el gráfico porque son los índices INDEC reales
(4.261 → 12.076 entre 2024-01 y 2026-07): sube ~6,7 puntos/mes en 2024, ~4,7 en 2025 y ~6,6 en
2026, y a esa escala la curva es visualmente lineal. No es un error de carga.

## 9b. Notebook 02 — Excel de econometría (`datos_econometria`)

Insumo para análisis de series de tiempo (materia "Econometría avanzada"). El Notebook 02, además
del análisis clásico, exporta `datos_econometria_{MES}.xlsx` en `output_canasta/`.

- **Formato tidy/long**: una fila por (frecuencia, período, clave, nivel, grupo).
- **Series**: costo de cada canasta activa (hoja `Selección`) + precio de los productos de
  `PRODUCTOS_ECONOMETRIA` (config editable arriba de la CELDA 22).
- **Frecuencia**: semanal (ISO) **y** mensual; historia completa.
- **Niveles**: nacional (ponderado por población), provincia, cadena.
- **Medidas**: `valor_mediana` (mediana entre sucursales, robusta, recomendada) y `valor_promedio`
  (media recortada `_pmean`, outliers fuera). Se calculan en dos etapas: día→período por
  (sucursal, EAN) con mediana/media, y luego entre sucursales.
- **Imputación**: ítems faltantes en una sucursal se imputan con la referencia nacional del período.
- **Semanas de borde**: cada semana ISO se asigna a su mes "dueño" (el del jueves ISO) para no
  duplicar fragmentos entre archivos mensuales.
- **Hojas**: `Diccionario`, `canastas_nacional/provincia/cadena`, `productos_nacional/provincia/cadena`.
