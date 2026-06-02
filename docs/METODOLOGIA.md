# Metodología — ICM-UADE (Índice de Canasta Mensual UADE)

**Última actualización:** 2026-06-01 (Celíaca Media + Vegana Básica)
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

## 3. Canastas ICM-UADE — Metodología ENGHo

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

El SEPA cubre las cadenas de supermercados obligadas a reportar. Los comercios de proximidad, almacenes y mercados locales **no están incluidos**, por lo que los precios del ICM-UADE pueden diferir de los precios efectivamente pagados por hogares de bajos ingresos (que consumen más en comercios de barrio).

### Identificación de cadenas en formato semestral

En el formato semestral, `id_bandera` representa el grupo corporativo (5 valores), no el banner comercial (16 valores). Para obtener el banner real se combina `(id_comercio, id_bandera)`. El ICM-UADE usa `id_bandera` para los umbrales y el score (métrica de grupos corporativos), e informa `n_cadenas_com` (banners reales) como dato adicional no vinculante.

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

### ICM-UADE (cantidad_01) — Canasta de referencia UADE

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
