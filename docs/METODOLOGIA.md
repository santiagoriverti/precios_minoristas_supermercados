# Metodología — ICR (Índice de Consumo Representativo)

**Última actualización:** 2026-09-07 (nb07 v5.3: banda de plausibilidad anclada en frescos + cobertura nacional obligatoria en las canastas; v5.2: filtro de régimen [BUG-24] y tripwire Alertas_precio_item — 287 empaquetados + 59 tipos de frescos)
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

## 10. Notebook 07 — Canastas alternativas (motor del informe semanal)

`07_evolucion_canastas_alternativas` calcula el costo **semanal** de **6 canastas** y lo compara
con el IPC, desagregando por **rubro** (con drill-down hasta producto), **provincia**, **región**
y **cadena**. Es el insumo del informe semanal del equipo de economistas.
La metodología de índice, agregación y trazabilidad está en **§10.7** (estado vigente).

### 10.1. Mapeo de canastas
Vigente desde **v5 (2026-09-07)**, ver §10.9:

| Columna | Canasta | Emp. | Frescos | Tier de producto | Percentil de precio unitario |
|---|---|---:|---:|---|---|
| `cantidad_01` | Popular | 58 | 32 | marca más barata con presencia nacional | P10 |
| `cantidad_02` | Media | 76 | 57 | marca líder | P45 |
| `cantidad_03` | Ejecutiva | 76 | 59 | premium | P80 |
| `cantidad_04` | Tecnológica | 14 | — | producto modal | — |
| `cantidad_05` | Representativa | 76 | 59 | producto modal (mayor cobertura) | — |
| `cantidad_06` | Femenina | 14 | — | marca líder | — |

Se leen de la hoja `Productos unicos` del Excel `canasta_representativa_*.xlsx`.
**287 EANs empaquetados únicos**; las cantidades las genera
`docs/canastas_alternativas/construir_canastas_v5.py` y las carga `cargar_canastas_v5.py`.

La Representativa **no escalona a propósito**: usa el producto modal (el de mayor cobertura
real), que es la definición que la hace comparable con la referencia del INDEC. Las otras tres
sí escalonan, con monotonicidad exigida Popular ≤ Media ≤ Ejecutiva en precio unitario.

Tecnológica y Femenina están en `CANASTAS_SIN_FRESCOS` (no reciben frescos) y en
`RUBRO_DESDE_CATEGORIA` (su desglose usa `categoria` en vez de `rubro`, porque en la hoja todos
sus productos caen en un único rubro y el desglose quedaría vacío de contenido).

### 10.2. Composición híbrida (empaquetados por EAN + frescos por tipo)
- **Empaquetados**: EAN estable con buena cobertura multi-cadena. Precio por sucursal-semana =
  mediana de los días. Selección exigiendo **≥4 cadenas, ≥15 provincias y ≥800 sucursales**
  (durables: ≥3 / ≥10 / ≥90, porque se publican mucho menos).
- **Frescos** (**59 tipos**): el EAN de balanza (prefijo GS1 `2…`) **cambia por cadena**, así que
  no se puede seguir un EAN. Se seleccionan por **regla de nombre** (`inc`/`exc` regex con borde
  de palabra) **más categoría de fresco real** del maestro: `Frutas y Verduras`, `Carnicería`,
  `Fiambrería`, `Panificados`, `Pescados y Mariscos`, `Huevos` — o categoría vacía (balanza
  SEPA-only). Precio del tipo por sucursal-semana = **mediana de sus variantes**, normalizado:
  - `$/kg`: `precio / gramos_presentación × 1000`. Cada tipo admite su piso `gmin` (default 250 g;
    quesos y fiambres 500 g) para descartar bandejas chicas que inflan el $/kg.
  - `$/docena` (huevos): `precio / unidades × 12`.
  - Antes de la mediana se aplica el **filtro de outliers intra-tipo** (§10.7).

Rubros de frescos: **Frutas, Verduras, Carne, Pollo, Cerdo, Pescado, Fiambres y Quesos,
Panadería, Huevos** (además de Almacén, Bebidas, Frescos-lácteos, Limpieza, Perfumería,
Congelados, Mascotas y Bebés de los empaquetados).

### 10.3. Costo de canasta
Hay dos cálculos, con propósitos distintos:

- **Serie temporal (nacional)**: se arma sobre el panel de precios nacionales por ítem y semana,
  con **índice encadenado de muestra apareada** y nivel anclado (§10.7). Es la serie que se publica.
- **Corte transversal (por sucursal)**: para desagregar por provincia / cadena / región se calcula
  el costo de cada sucursal:
  `costo = Σ_presentes(precio_sucursal × cantidad) + [Σ_todos(nacional × cantidad) − Σ_presentes(nacional × cantidad)]`
  es decir, cada ítem presente usa el precio de la sucursal y cada faltante se imputa con el
  **precio nacional de esa semana**. Una sucursal solo cuenta si tiene al menos
  `FRAC_PRODUCTOS_MIN` (**0.8**) de los empaquetados de la canasta.

### 10.4. Desagregación por rubro (drill-down)
- **Nivel 1**: costo por rubro × semana, calculado sobre el panel nacional (así los rubros suman
  exactamente el costo de la canasta) y participación % del último mes.
- **Nivel 2**: detalle por ítem (producto empaquetado o tipo fresco) del último mes con cantidad,
  precio unitario y costo (`Detalle_*`).

### 10.5. Durables: por qué están aparte
Los electrodomésticos tienen cobertura estructuralmente baja (pocas cadenas, precios fijados a
nivel nacional). No se mezclan con las canastas de consumo: van en la **Tecnológica**, con
umbrales de cobertura propios y leídos como bundle informativo, no como índice de precios
comparable entre provincias.

### 10.6. Diagnósticos para refinar
La CELDA 13 imprime y exporta:
- `Cobertura_emp`: por EAN empaquetado, `n_cadenas`/`n_provincias`/`n_sucursales` del último mes,
  marcando ítems **sin datos** o de **baja comparabilidad** (n_cadenas<3 o n_provincias<15).
- `Cobertura_frescos`: por tipo, nº de variantes capturadas, cobertura y **$/kg o $/docena**
  normalizado. Es la tabla para afinar `inc`/`exc`/`gmin`.
- `Presencia_items` y `Alertas_reemplazo`: trazabilidad de altas y bajas (§10.7).

---

### 10.7. nb07 v5 (2026-09-04) — motor del informe semanal, estado vigente

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

---

### 10.8. nb07 v5.1 (2026-09-04) — robustez del nacional y de la muestra

Diagnóstico sobre la **primera corrida real de v5** (`canastas_alternativas_2026-09-03.xlsx`).
El índice encadenado ya había bajado los saltos de ±24% a ±12%, pero quedaban cuatro.

**Hallazgo central: el ruido de las provincias chicas entraba al nacional con todo su peso
poblacional.** La volatilidad escala con 1/√n:

| Región | n_suc mediano | Desvío de la variación semanal |
|---|---:|---:|
| Centro/Pampeana | 1.423 | 2,3% |
| NEA | 31 | 4,1% |
| Cuyo | 52 | 6,0% |
| NOA | 69 | 7,4% |
| Patagonia | 38 | **12,0%** |

En el salto del 2025-06-12 (+12% nacional) Centro/Pampeana subió 1,6% y **Patagonia 113%**
(443k → 942k, y volvió a 593k la semana siguiente). Es decir: la corrección de v5 (dejar de estar
dominados por DIA) trajo este efecto lateral, porque el promedio ponderado le daba a cada
provincia su peso poblacional completo aunque el dato viniera de dos sucursales.

**Correcciones:**

| Parámetro | Valor | Qué hace |
|---|---|---|
| `MIN_SUC_PROV_ITEM` | 3 | Una provincia entra al promedio nacional de un ítem-semana solo si tiene ≥3 sucursales con precio para ese ítem. Si no califica, su peso se redistribuye |
| `PROV_OUTLIER_K` | 2.5 | Winsorización de las medianas provinciales contra la mediana entre provincias, antes de promediar |
| `COBERTURA_MIN_INDICE` | 0.80 | El índice de una canasta arranca en la primera semana con ≥80% de los ítems de su receta |

Además:

- **Cobertura mínima del índice**: la Tecnológica tenía **4 de 14 ítems durante todo 2024** (el
  14º recién aparece en 2025-09), así que su índice de 2024 no era informativo. Ahora arranca
  cuando la canasta existe de verdad. Se agrega la columna `cobertura_%` a las series semanales.
- **Semana incompleta**: se descartan las semanas cuyo jueves de cierre es posterior al último
  dato del SEPA (`FECHA_MAX_DATOS`). En la corrida real el SEPA llegaba al 31/08 y la semana
  2026-09-03 tenía 4 de 7 días, pero se publicaba como cerrada.
- **Detección centavos/pesos**: se mide sobre los **EANs empaquetados**, no sobre todo el
  universo. Con ~10.500 frescos de balanza cotizando por kilo, la mediana global quedaba cerca
  del umbral de 10.000 y un falso positivo habría dividido un mes entero por 100.

**Refinamiento de tipos frescos** (contaminación verificada contra el maestro real):

| Tipo | EANs antes → después | Qué colaba |
|---|---|---|
| Bondiola | 144 → 101 | Bondiola **curada** (fiambre, ~2× el precio de la fresca) |
| Espinaca | 27 → 21 | Ensaladas listas, baby hidropónica |
| Choclo | 25 → 24 | Relleno para tarta |
| Pan francés | 170 → 167 | "Pan con chicharrón" |

**Nuevas salidas de diagnóstico:**
- Hoja **`Panel_nacional`**: precio nacional de cada ítem por semana. Permite ir directo al ítem
  que causó un salto, en vez de inferirlo desde los rubros.
- Bloque de **fiabilidad regional** en el reporte: n_sucursales y desvío de la variación semanal
  por región, con aviso cuando la muestra es chica (<100 sucursales).

**Qué NO se cambió y por qué**: los movimientos de Carne del 2026-03-26 (+11%) y 2026-06-18
(−8%) aparecen **también en Centro/Pampeana con 1.700 sucursales**, así que no son ruido de
muestra chica: son repricings reales y anchos del panel de carne. Corregirlos sería borrar
información verdadera.

### 10.9. nb07 v5.2 (2026-09-07) — régimen de precio en frescos y rediseño de canastas

Dos problemas independientes, diagnosticados sobre la corrida 2026-08-27.

#### A. Los saltos de la serie eran cambios de régimen de precio, no inflación

Descomponiendo las cuatro semanas con saltos, casi todo venía del rubro **Verduras**, y dentro
de él de un solo ítem, **Papa**:

| Semana | Contribución de Verduras | Resto |
|---|---:|---:|
| 2026-05-21 | **+7,27 pp** | +1,01 pp |
| 2026-07-02 | **−7,22 pp** | +2,07 pp |
| 2026-07-23 | +1,30 pp | +1,96 pp |
| 2026-07-30 | **+5,02 pp** | −0,49 pp |

El precio nacional de Papa era una **onda cuadrada entre dos regímenes**:
`2.318 → 14.714 → 2.561 → 14.855`, un factor de 6,8. El nivel de agosto ($15.015/kg) delataba
el problema por sí solo: la papa no vale 7 veces la cebolla ($2.688/kg).

**Causa raíz, en tres capas encadenadas.**

1. **El "tipo" mezcla bienes distintos.** Verificado sobre los precios por EAN de la hoja
   `Productos unicos`: espinaca suelta $2.171/kg contra espinaca lavada y sanitizada en bolsa
   de 300 gr $21.633/kg. La diferencia de 10× es *real* — son productos distintos —, pero el
   pipeline los promediaba como si fueran el mismo bien.

2. **El filtro de outliers se quedaba con el régimen caro.** La banda
   `[mediana/2,5 , mediana×2,5]` calculada *dentro de cada sucursal* falla de la peor forma
   sobre una distribución bimodal:

   ```
   sucursal con {2.100 , 15.000}  -> mediana 8.550 -> banda [3.420 , 21.375]
                                  -> DESCARTA el 2.100 correcto y CONSERVA el 15.000

   sucursal con {2.100 , 2.100 , 15.000} -> mediana 2.100 -> banda [840 , 5.250] -> correcto
   ```

   El resultado lo decide qué régimen tenga mayoría en esa sucursal, y **cuando hay empate gana
   el caro**: sesgo sistemático al alza, no ruido simétrico. Que entre o salga una variante da
   vuelta la sucursal entera; agregado sobre 1.900 sucursales, sale la onda cuadrada.

3. **Errores de carga que sobrevivían.** `Papa Negra Sc 1 Kg` cotizaba **$95,00** en **983
   sucursales**. Dentro del tipo Papa el rango iba de $95 a $7.990: factor 84.

   Hueco adicional: el maestro SEPA (27.287 EANs) entra sin columna `categoria`, y el filtro es
   `categoria in {...} OR categoria == ''`. Es decir, esos 27k EANs **salteaban el filtro de
   categoría por completo** — alcanzaba con pegar en el regex.

**Solución — `FRESCO_REGIMEN_K = 3.0`.** Antes de tocar la sucursal se calcula la **referencia
nacional del tipo para el mes completo** (mediana sobre todas las observaciones del país) y se
descarta lo que quede fuera de `[ref/K, ref×K]`. Recién después corre el filtro intra-sucursal,
que queda como segunda línea.

Por qué funciona: la referencia se estima sobre millones de observaciones, así que no se da
vuelta porque una sucursal cambie el surtido; y se recalcula cada mes, así que acompaña a la
inflación sola sin necesidad de umbrales absolutos que envejecen.

Validación con un panel sintético de 1.900 sucursales que reproduce el modo de falla:

| | S1 | S2 | salto |
|---|---:|---:|---:|
| Código anterior | 2.352 | 15.016 | **+538,4%** |
| Con filtro de régimen | 2.352 | 2.318 | **−1,5%** |

El +538% sintético reproduce el +535% real observado en Papa el 2026-05-21.

Complementos:

- **`gmin` por tipo** = 1000 g en Papa, Lechuga, Acelga y Espinaca, donde hay evidencia directa
  de una presentación sub-kilo procesada contaminando el tipo. **No** se subió en Frutilla ni
  Choclo: se venden en bandeja, y un mínimo global de 1 kg los borraría del panel.
- **Hoja nueva `Alertas_precio_item`** (`ALERTA_SALTO_ITEM = 0.35`): todo salto semanal del
  precio nacional de un ítem mayor a 35% queda listado con precio antes y después. Es el
  tripwire — se arregló la causa y además se puso el detector, para que esta clase de bug no
  vuelva a pasar inadvertida. Sale también impresa en el "REPORTE PARA CLAUDE".

El cambio de `FRESCO_REGIMEN_K` entra en la clave del caché, así que la primera corrida vuelve
a leer todo el histórico (~57 min).

#### B. Las canastas eran la misma canasta a distinta escala

Medido en **gasto** sobre la corrida 2026-08-27: Media compartía el **100,0%** de su gasto con
Representativa (estaba contenida), el 82,6% con Ejecutiva, y el **91%** de los tipos frescos de
Popular eran los mismos que los de Ejecutiva. Las correlaciones de variaciones semanales
(Media-Ejecutiva 0,962; Media-Representativa 0,951) no eran un hallazgo: eran una identidad
contable. Un índice construido sobre los mismos EANs no puede mostrar inflación distinta por
nivel socioeconómico.

**Rediseño v5** — tres decisiones, implementadas en
`docs/canastas_alternativas/construir_canastas_v5.py` (constructor reproducible y auditable):

1. **Necesidades, no productos.** Las canastas cubren el mismo conjunto de necesidades, pero
   cada estrato elige su versión: Popular primer precio, Media marca líder, Ejecutiva premium.
   El tier se decide por percentil del precio **por unidad comparable** ($/kg, $/L, $/unidad de
   uso), nunca por el precio del envase. Solapamiento de EANs entre estratos: **≤6,4%**.
   Escalonamiento logrado: Ejecutiva = **2,27×** Popular en precio unitario (mediana).

2. **Cantidades físicas, no unidades.** v4 declaraba unidades/mes sin mirar el envase, así que
   900 ml y 1,5 L contaban igual. Ahora se declara la cantidad física y el loader calcula
   `cantidad = cantidad_física / presentación`.

3. **Ancladas a la CBA del INDEC**, hogar tipo 2 (2 adultos + 2 niños = 3,09 adultos
   equivalentes). Fuente: INDEC, *Canasta básica alimentaria y canasta básica total. Preguntas
   frecuentes*, Notas al pie N.º 3, junio 2020, cuadro de composición para el adulto
   equivalente (p. 13) y ejemplo de hogar de 4 integrantes (p. 9). Corrigió dos faltantes
   grandes: **pan 8 kg/mes contra 20,9 de la CBA, y papa 8 contra 20,1** — los dos
   carbohidratos base estaban a un tercio de la referencia oficial.

En frescos el escalonamiento no puede ser por marca (se cotizan por tipo de balanza), así que
es **por corte**: Popular carga en los cortes de olla (falda, puchero, osobuco, paleta,
picada), Ejecutiva en los caros (lomo, bife de chorizo, nalga).

**Dos controles que la auditoría del constructor obligó a agregar**, porque la primera versión
fallaba en silencio: (a) **monotonicidad** Popular ≤ Media ≤ Ejecutiva en precio unitario
—sin ella, como cada canasta tiene su propio pool de cobertura, el percentil devolvía un
Ejecutiva más barato que el Media (atún, bolsas de residuo); hoy 0 violaciones en 78
necesidades—; (b) **cobertura declarada**: un producto que no cumple el piso de su canasta
queda marcado `confiable=False` en vez de pasar callado (la primera versión metió un té con 98
sucursales en Media, cuyo piso son 800); hoy 4 de 322.

**Advertencia sobre lo que esto puede y no puede lograr.** El escalonamiento por marca separa
bien los *niveles* de precio, pero no va a producir tasas de inflación muy distintas entre
estratos: dentro de una misma necesidad las marcas se mueven casi en paralelo. Aceite de
girasol 900 ml en agosto de 2026: Día $3.645 · Cañuelas $4.115 · Cocinero $4.339 · Natura
$4.637 — 27% de rango en nivel, trayectorias parecidas. La diferencia real de **inflación**
entre estratos viene de la **composición entre rubros** (efecto Engel). Eso ya se veía en v4
pese al anidamiento: Popular acumulaba +186,5% contra Media +171,8% entre 2024-01 y 2026-08,
porque pesa más Carne (17,8% contra 12,3%) y Verduras (12,7% contra 9,5%). v5 conserva y
acentúa esa diferencia, que es la que tiene contenido económico.

#### C. Defecto abierto: la desagregación regional de la Tecnológica es degenerada

En la corrida 2026-08-27 las cinco regiones informan **el mismo valor** ($5.853.138). Son 97
sucursales de una sola cadena (ChangoMas / Mi ChangoMas). Es un índice de una cadena, no
nacional, y la apertura por región no debería publicarse tal como está.


### 10.10. nb07 v5.3 (2026-09-07) — plausibilidad anclada y cobertura nacional de las canastas

Diagnostico sobre la **primera corrida de v5.2** (2026-08-27, 62,7 millones de observaciones).
El filtro de regimen funciono donde se esperaba —Papa paso de $15.015/kg a **$3.338**, Anana de
$11.213 a $3.805, Pepino de $18.590 a $3.265, Durazno de $10.905 a $4.055, Ajo de $10.119 a
$3.146— pero destapo dos problemas nuevos.

#### A. El filtro de regimen elige la moda mayoritaria, y a veces la moda mayoritaria es basura

**Pan frances cayo a $550/kg** (venia de $4.981). No es un error de calculo: es que el tipo
esta dominado por registros invalidos. Una cadena de ~980 sucursales publica:

| Descripcion | Cadenas | Sucursales | Precio | $/kg |
|---|---:|---:|---:|---:|
| Pan Casero Blanco 1 Kg | 1 | 977 | $5,00 | **$5** |
| Pan Mignon 1 Kg | 1 | 977 | $40,00 | **$40** |
| Pan Frances Tira 1 Kg | 1 | 977 | $70,00 | **$70** |
| Mignones 300 Gr | 1 | 983 | $150,83 | **$503** |
| Pan Mignon 1 Kg | 1 | 983 | $10.000 | $10.000 |

Son ~4.000 registros sucursal-EAN de precio invalido contra unos pocos cientos de precio real,
asi que la mediana nacional del tipo —que es justamente la referencia del filtro de regimen—
aterriza en el regimen equivocado. **Ningun alimento fresco cuesta $40 el kilo**: eso es un
precio de relleno, no un precio.

**Solucion: banda de PLAUSIBILIDAD anclada**, aplicada antes que todo lo demas. El umbral no
puede ser absoluto (envejeceria con la inflacion), asi que se expresa relativo a un ancla
calculada en la propia corrida:

```
ANCLA_FRESCOS = ['Papa','Cebolla','Zapallo','Zanahoria','Tomate','Banana','Manzana','Naranja']
ancla = mediana del $/kg de esos tipos en el mes
se descarta todo lo que quede fuera de [ancla * 0.2 , ancla * 20]
```

Calibracion sobre 2026-08: ancla = **$3.165/kg** → piso $633, techo $63.309. Se verifico en los
datos que **ninguna mediana de tipo legitimo cae fuera de esa banda** (la mas barata es
Mandarina a $1.327 y la mas cara Queso rallar a $39.735) y que **los 10 unicos EANs del universo
de frescos por debajo de $600/kg quedan adentro del descarte** — todos manifiestamente erroneos
($5, $40, $70, $95, $129, $148 el kilo). El ancla se recalcula cada mes, asi que la banda
acompana a la inflacion sola.

Validacion con un test end-to-end del pipeline completo (banda + regimen + intra-sucursal)
sobre un panel sintetico que reproduce los dos casos reales: los 10 tipos recuperan su precio
verdadero con **menos de 2% de error**, incluido Pan frances ($4.983 contra $5.000 real) pese a
que la basura era la moda mayoritaria, y Papa ($2.338 contra $2.300) pese a convivir con el
regimen alto y con el EAN a $95.

Ajustes complementarios de la misma corrida:

- **Espinaca y Acelga**: el `gmin=1000` de v5.2 las dejo en 13 y 10 EANs usables (172 y 1.086
  sucursales) y las convirtio en las series mas ruidosas del panel (Espinaca: +146%, −62%,
  +75%, −28% en semanas consecutivas). Se vuelve al minimo por defecto y se excluye la hoja
  lavada en bolsa **por nombre**, que es lo que realmente contaminaba el tipo.
- **Pan frances**: se excluye ademas el sin-TACC premium (Pan Criollo Campero, $10.517/kg).
- **Carne picada**: daba $20.514/kg, mas cara que el asado ($13.532). Se excluyen las variantes
  tartare, que empujaban la mediana.

#### B. El umbral relajado de Popular destruyo el indice

La decision de bajar el piso de cobertura de Popular a ≥2 cadenas / ≥600 sucursales —para poder
incluir marca propia y primer precio— parecia razonable en abstracto y **fallo en la practica**.

El percentil 10 aterriza sistematicamente en la marca propia, y la marca propia vive en una sola
cadena. Resultado: 11 de los 60 productos de Popular quedaron con ~550 sucursales y 3 cadenas,
todos Carrefour. Como nb07 solo cotiza una sucursal que tenga ≥80% de los items de la canasta
(`FRAC_PRODUCTOS_MIN`):

| Canasta | Items <800 sucursales | Sucursales que cotizan |
|---|---:|---:|
| Popular | 18 de 60 | **85** (contra 1.969 en v4) |
| Media | 8 de 78 | 234 |
| Ejecutiva | 23 de 78 | 163 |
| Representativa | 2 de 78 | 2.209 |

La canasta Popular quedo cotizando en 85 sucursales **de una sola cadena**. Un indice calculado
sobre 85 sucursales de Carrefour no es un indice nacional, por representativo que sea el surtido.

**Correccion**: todas las canastas de consumo vuelven a ≥4 cadenas / ≥15 provincias / ≥800
sucursales, con un piso absoluto de ≥3 cadenas / ≥12 provincias / ≥700 sucursales por debajo del
cual la necesidad **se descarta** para esa canasta en vez de incluir un item que solo cotiza en
400 sucursales. El estrato Popular sale ahora de la marca **mas barata con presencia nacional**
(Canuelas, Casanto, Marolio, Dogui, Brahma, Tregar, Sedal), no de la marca propia.

**El costo en escalonamiento fue casi nulo**: el ratio de precio unitario Ejecutiva/Popular paso
de 2,27× a **2,21×** (mediana entre necesidades), mientras la cobertura minima de un item subio
de 546 a **802 sucursales** y no queda ningun pick por debajo del umbral de su canasta.

#### C. Dos bugs de unidades en el constructor

- **`Algodon Estrella Clasico 75 Gr` × 80 = $111.470**, el 43% de la canasta Femenina. La
  cantidad estaba declarada en discos (80), pero ese producto se mide en gramos y no declara
  unidades, asi que el motor lo tomo como 80 **paquetes**. Se agrego una tercera unidad,
  `u='pack'` (la cantidad esta en paquetes y el conteo del envase se ignora), para los productos
  donde "un paquete" es la unidad natural de compra: algodon, tintura, esponja, crema
  depilatoria, rollo de cocina. Y `u='un'` ahora **exige** que el envase declare cuantas
  unidades trae, en vez de asumir 1.
- **`Hamburguesas 4 Un 83 Gr` × 10 = $104.124** en la Ejecutiva. El gramaje se leyo como 83 g
  cuando el paquete son 4×83 = 332 g. El formato "N Un M Gr" no distingue si M es el total o el
  peso por unidad, asi que no se adivina: **el candidato se descarta** (mismo criterio que ya
  usaba nb06 para los multipacks).

Ademas se excluyeron los concentrados "para diluir" del jabon liquido para ropa (no son
comparables por volumen con el producto comun: Ariel 500 ml × 8 = $93.143) y se modero el
alcohol de la Ejecutiva (de 18 latas y 4 botellas por mes a 14 y 3).

**Femenina volvio de $260.865 a $139.737.**

> El cambio de la banda de plausibilidad entra en la clave del cache, asi que la corrida
> siguiente vuelve a leer el historico completo (~58 min). Es inevitable: el filtro tiene que
> correr antes de colapsar los frescos a tipo.


### 10.11. nb07 v5.7 (2026-09-08) — el precio nacional de un fresco es un índice encadenado por EAN

**El problema que cierra.** Hasta v5.6 el precio nacional de un tipo fresco era la mediana sobre
las observaciones sucursal-EAN del mes. Esa mediana la fija **la mezcla de EANs que casualmente
cotiza**, no el precio de mercado: cuando la mezcla cambia en el corte de mes, el tipo salta. La
muestra apareada del índice no lo detecta porque el ítem se llama igual (`Lomo`) en ambas semanas.

Medido en la corrida 2026-08-27: `Presencia_items` da **100% para los nueve tipos que saltan, en
todos los meses** — el tipo nunca falta. Y los dos regímenes de cada tipo distan ~2,5× (Lomo
$13.211 vs $36.378), mientras que una banda tiene que ser ≥2× para tolerar dispersión legítima:
**ninguna banda los separa**.

**El estimador nuevo.** Para cada tipo fresco:

1. Del caché por EAN se toma, por semana, el precio nacional de cada EAN y su cobertura.
   Entran los EAN-semana con al menos `FRESCO_EAN_MIN_SUC` sucursales.
2. Entre dos semanas consecutivas se calcula el **ratio de muestra apareada**: la mediana de
   `p_ean(t) / p_ean(t-1)` sobre los EANs presentes en **ambas** (mínimo `FRESCO_MIN_EANS_PAR`).
   Cada EAN se compara consigo mismo, así que un alta o baja de EANs **no puede mover el índice**.
3. Los ratios se encadenan. Un eslabón puede saltear hasta `FRESCO_MAX_HUECO_PAR` semanas para
   reenganchar; más que eso **corta la cadena** y abre un tramo nuevo, porque encadenar a través
   de un hueco largo publicaría de golpe toda la inflación acumulada.
4. **Nivel**: cada tramo se ancla por separado al estimador anterior (mediana provincial
   ponderada por población) en su última semana válida. Anclar todo con una sola semana base
   rebasea los tramos viejos. Un tramo de una sola semana no tiene ningún eslabón y se descarta:
   publicarlo sería publicar el valor contaminado que estamos evitando.

Los tipos que no llegan a encadenar conservan el estimador anterior y se listan por pantalla.

**Referencia del filtro de régimen.** Pasa a ser `ancla del mes × RATIO_FRESCO[tipo]` en vez de
la mediana del mes. `RATIO_FRESCO` ya venía calibrado en el q75 del ratio contra el ancla, y el
ancla se recalcula todos los meses, así que la referencia acompaña a la inflación sin depender de
la composición. Esto también hizo evidente que **bajar el K de régimen empeora las cosas** cuando
la referencia está contaminada: estrechar la ventana compromete más con el régimen equivocado
(los tres tipos más volátiles de 2026 fueron los tres con `rk=2.0`).

**Caché por EAN.** Se escribe `ean_<key>_v5.parquet` junto al panel semanal, con la misma clave.
Son ~10.400 EANs × 139 semanas: nada al lado de los 71 M de filas del panel. El `groupby` que lo
produce corre **por mes** (~2 M de filas), no sobre el panel completo, así que no reintroduce el
OOM de v5.4. Su razón de ser es operativa: **toda la metodología de frescos se calcula después del
caché**, de modo que iterarla cuesta minutos en lugar de 1h42m de relectura del SEPA.

**Parámetros** (CELDA 1): `FRESCO_NAC_ENCADENADO`, `FRESCO_EAN_MIN_SUC` (10),
`FRESCO_MIN_EANS_PAR` (2), `FRESCO_MAX_HUECO_PAR` (8).

**Test**: `notebooks/test_encadenado_frescos.py` — ejecuta el código real extraído de
`gen_nb07.py` contra un panel sintético con el patrón medido. Saltos de +170%/+149%/+235%
desaparecen; recupera el 1,00%/semana con 0,0% de error.

---

### 10.12. nb07 — series MENSUALES por rubro, región, provincia y cadena (2026-09-08)

El Excel tenía frecuencia mensual sólo a nivel canasta (`Mes_*`, `vsIPC_*`). Rubro y región eran
semanales; provincia y cadena, una foto del último mes. Se agregan cinco hojas:

| Hoja | Contenido | Formato |
|---|---|---|
| `Mes_rubro` | costo, participación % y var. mensual por rubro | largo (canasta, mes, rubro) |
| `Mes_region` | costo, sucursales y var. mensual por región | largo (canasta, mes, región) |
| `Mes_provincia` | ídem por provincia | largo |
| `Mes_cadena` | ídem por cadena | largo |
| `Panel_nacional_mes` | precio nacional de cada ítem, mensual | ancho (ítem × mes) |

**Por qué formato largo y consolidado** (todas las canastas en una hoja) y no una hoja por canasta
y dimensión: eso serían 24 hojas nuevas sobre las 68 existentes. El formato largo es además el
que sirve para tablas dinámicas y para econometría, en línea con `datos_econometria` de nb02.

**Convención de mensualización.** El costo mensual de la canasta ya era el **promedio de los
costos semanales** del mes. Las aperturas geográficas siguen el mismo criterio en dos pasos:
primero la **mediana entre sucursales** de cada semana, después el **promedio de las semanas** del
mes. El orden importa: promediar directamente sobre sucursal-semana haría que una semana con más
sucursales pesara más que las otras. `Panel_nacional_mes` promedia las semanas del mes, que es la
frecuencia a la que se compara contra el IPC.

---

### 10.13. Validación del encadenado de frescos contra datos reales (2026-09-08)

El caché por EAN (`ean_<key>_v5.parquet`) permitió correr el bloque de encadenado de `gen_nb07.py`
**fuera del notebook**, sobre el panel real de 385.991 filas (4.229 EANs, 136 semanas), sin releer
el SEPA. Resultados:

| Ventana | Frescos (mediana) | IPC alimentos | IPC general |
|---|---:|---:|---:|
| ene-24 → ago-26 (31 meses) | **+174,3%** | +156,9% | +183,4% |
| ago-24 → ago-26 (24 m, misma estación) | **+59,5%** | +69,6% | +75,4% |

Las dos ventanas quedan en rango. Celdas con variación exactamente 0,000%: **10,3%**, en línea con
el 13,0% de los empaquetados (con la mediana daba 87,8% — ver BUG-28).

**No hay chain drift sistemático.** Contra un índice directo de base fija (mismos EANs punta a
punta, Jevons), el drift mediano es **0 pp**. Hay dispersión por tipo (|drift| mediano 30 pp) pero
**sin dirección sistemática** —Cebolla +280% encadenado contra +152% directo, Asado +157% contra
+277%—, lo que apunta a diferencia de MUESTRA y no a drift: el índice directo sólo usa los EANs
que sobreviven los 31 meses, que es una muestra de supervivientes. Encadenar en frecuencia mensual
reduce el |drift| mediano de 44 a 32 pp en el subconjunto con muestra directa sólida (≥15 EANs),
una mejora que **no justifica** perder el índice semanal que necesita el informe.

**⚠️ Cómo NO leer el acumulado por tipo.** Está dominado por la estacionalidad de los extremos, no
por inflación. Naranja da **+1%** de ene-24 a ago-26 y **+12%** de ago-24 a ago-26; Palta, +2% y
+56%. Son frutas de invierno comparadas contra un extremo de verano. El acumulado de un tipo
individual sólo tiene sentido entre extremos de la MISMA estación.

**Tipos con la cadena partida en más de un tramo**: Acelga (2), Espinaca (2) y Durazno (3, con dato
en sólo 83 de 136 semanas). En esos tres el nivel entre tramos lo fija el estimador anterior, no la
cadena.

---

## 11. Notebook 02 — Excel de econometría (`datos_econometria`)

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
