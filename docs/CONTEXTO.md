# Contexto del Proyecto — Precios Minoristas SEPA

Última actualización: 2026-06-01 (multi-canasta nb02, 6 columnas cantidad nb01, canastas ENGHo)

## Objetivo

Construir hasta **6 canastas representativas** a partir de los datos del SEPA (Sistema Electrónico de Publicidad de Precios Argentinos), calcular su costo mensual por sucursal y provincia, y compararlas con el IPC INDEC.

El notebook 01 entrega un Excel con **cuatro hojas**:
- **Canasta**: ~65 productos seleccionados automáticamente por cobertura, coloreados por grupo
- **Candidatos**: ~3.650 productos que superan los umbrales estrictos (5 cadenas, 24 provincias, 50 sucursales)
- **Selección**: ~25K productos con umbrales amplios, con **6 columnas de cantidad** (`cantidad_01`..`cantidad_06`) para definir hasta 6 canastas independientes
- **Productos unicos**: ~75K productos sin umbrales de cobertura, para exploración libre

## Repositorio

- **GitHub**: santiagoriverti/precios_minoristas_supermercados
- **Notebook 01**: `notebooks/01_exploracion_productos.ipynb` — selección dinámica de canasta (ejecutable en Colab)
- **Notebook 02**: `notebooks/02_evolucion_canasta_representativa.ipynb` — análisis de canasta elegida, mapas, rankings (ejecutable en Colab)
- **Maestros**: `data/` — productos, sucursales, provincias
- **Datos SEPA**: NO están en el repo. Están en Google Drive personal: `/carga/` (2024A.zip, 2024B.zip, 2025A.zip, 2025B.zip, 2026A.zip)
- **Archivos auxiliares en Drive** (`carga/`): `IPC.xlsx` (IPC INDEC), `ar.json` (GeoJSON provincias), `output_canasta/canasta_representativa_YYYY-MM.xlsx`

---

## Ecosistema de notebooks relacionados

Este proyecto no existe en aislamiento. Hay múltiples notebooks en otros repositorios que procesan los mismos datos y de los que se pueden tomar patrones.

### 1. `01_exploracion_productos.ipynb` (este repo — notebook 01)
**Propósito**: selección dinámica de canasta por score de cobertura.
**Enfoque**: todos los productos del SEPA semestral → filtrar por cobertura → seleccionar top-N por grupo.
**Output**: `canasta_representativa_MMAAAA.xlsx` (hojas: Canasta, Candidatos, Selección)

### 2. `02_evolucion_canasta_representativa.ipynb` (este repo — notebook 02) ← NUEVO
**Propósito**: análisis completo de la canasta elegida por el economista.
**Enfoque**: lee la hoja `Selección` del Excel del notebook 01 (campo `cantidad`), calcula el costo por sucursal con imputación nacional, compara con IPC INDEC, y genera todas las visualizaciones.
**Pipeline (20 celdas)**:
- CELDA 1–2: Markdown + Config (`SEPA_DIR`, `OUTPUT_DIR`, `USE_CACHE`, `MES_INICIO_HISTORICO`, `MES_INICIO_GRAFICO`, `MIN_PRODUCTOS_PROPIOS`, `MIN_SUCURSALES_RANKING`)
- CELDA 3: Mount Drive
- CELDA 4: Canasta desde Excel (hoja `Selección`/`Seleccion`, campo `cantidad`)
- CELDA 5: Maestros — `NOMBRES_COMPUESTOS`, `NOMBRES_SIMPLES`, `PROV_NORM` (24 provincias), `PESOS_POBLACION` (Censo 2022)
- CELDA 6: Funciones auxiliares (`get_nombre_cadena`, `normalizar_provincia`, `precio_a_pesos`)
- CELDA 7: Carga mes actual desde ZIPs, filtra a EANs de la canasta, precio promedio por producto por sucursal
- CELDA 8: `calcular_canasta_completa()` por sucursal — imputación con mediana nacional para productos faltantes → `canasta_geo_filtros`
- CELDA 9: Análisis provincial — mediana por provincia, ponderación por población → `serie_provincia_valida`, `prom_nac_ponderado`
- CELDA 10: Serie histórica (todos los semestres disponibles) con caché parquet clave MD5 → `serie_nacional_valida`
- CELDA 11: IPC desde `carga/IPC.xlsx` → `ipc_general`, `ipc_alimentos`
- CELDA 12: `comparativa` — reindexar a base mar-2024, índice SEPA vs IPC
- CELDA 13: Gráfico 1 — índices base dinámica (líneas, etiquetas en español, serie llamada "ICM-UADE"); Gráfico 2 — variaciones mensuales (3 barras: ICM-UADE + IPC General + IPC Alimentos, etiquetas español)
- CELDA 14: Cuadro 1 provincial + código LaTeX
- CELDA 15: Mapa coroplético provincial con `ar.json`
- CELDA 16: Cobertura por provincia y por cadena
- CELDA 17: Rankings nacionales + AMBA (barras horizontales, gradiente RdYlGn)
- CELDA 18: Mapa Folium interactivo (FeatureGroups por cadena, panel JS de filtros)
- CELDA 19: Ranking CABA por barrio (48 bounding boxes lat/lon)
- CELDA 20: Diagnóstico trazabilidad temporal de todos los ~3.650 Candidatos (CELDA 20, opcional ~20 min)
- CELDA 21: Exportación Excel (`canasta_analisis_YYYY-MM.xlsx`) — 5 hojas: Evolucion_IPC, Por_provincia, Por_sucursal, Ranking_cadenas, **Serie_precios** (precio mediano por producto por mes)
**Output**: `output_canasta/canasta_analisis_YYYY-MM.xlsx` + `mapa_interactivo.html` + `trazabilidad_candidatos_YYYY-MM.xlsx`
**Archivos requeridos en Drive**: `carga/IPC.xlsx`, `carga/ar.json`, `output_canasta/canasta_representativa_YYYY-MM.xlsx`
**Cambios claves (2026-05-29)**:
- BUG-15 resuelto: `'San juan'` → `'San Juan'` en `PROV_NORM`
- Caché por hash de EANs+cantidades (cambiar qty invalida caché automáticamente)
- Gráficos con nombre "ICM-UADE" y etiquetas de meses en español (ene-24, feb-24…)
- Gráfico 2 con 3 barras: ICM-UADE + IPC General + IPC Alimentos
- `MES_INICIO_GRAFICO` auto-adapta al primer mes disponible si el configurado no existe
- Nueva hoja Excel `Serie_precios`: precio mediano por producto por mes (serie completa)

### 3. `analisis_SEPA_evolucion.ipynb`
**Propósito**: evolución mensual de precios con canasta fija de 30 EANs.
**Enfoque**: procesa múltiples semestres (2022A–2026A), autodetecta FACTOR_PRECIO, calcula serie diaria nacional.
**Output**: `canasta_SEMESTRE_serie.xlsx` (hojas: serie_diaria_nacional, canasta_mes_provincia, canasta_mes_region, canasta_nacional_ponderada)

### 4. `analisis_SEPA_evolucion_AMBA.ipynb`
**Propósito**: foco en AMBA, 16 cadenas comerciales, mapas Folium interactivos.
**Clave crítica**: confirma **FACTOR_PRECIO = 1** para datos de abril 2026. Tiene el diccionario completo de `(id_comercio, id_bandera)` → nombre de cadena.
**Output**: mapa interactivo HTML + Excel con canasta por sucursal.

### 5. `consolidacion_analisis_SEPA.ipynb`
**Propósito**: consolida todos los semestres en una serie temporal de 52 meses (2022–2026).
**Output**: tablas LaTeX para papers + comparación SEPA vs IPC INDEC.
**Dato**: canasta nacional abril 2026 = **$322,566 ARS** (ponderada por Censo 2022).

### 6. `analisis_canasta_SEPA.ipynb`
**Propósito**: usa el formato DIARIO (no semestral) para ver los 28 banners comerciales reales.
**Formato**: `YYYY-MM-DD.zip` → 20 ZIPs por cadena → pipe-separated (`comercio.csv`, `sucursales.csv`, `productos.csv`).
**Clave**: 87,418 EANs únicos, precios directamente en pesos, 14.8M filas.

### 7. `analisis_precios_SEPA.ipynb`
**Propósito**: pipeline sofisticado con parquet cache + clasificación de rubros por keywords.
**Patrones útiles**: float32 desde el inicio, drop de columnas de promo, parquet snappy para cachear.
**Output**: 7,616 productos canastables identificados.

### 8. `analisis_precios_SEPA_2.ipynb`
**Propósito**: deduplicación de variantes del mismo producto.
**Técnica**: `extraer_concepto()` → top-3 palabras significativas minus marca/packaging → colapsa ~10% de duplicados.

### 9. `resultados_canasta_sepa.ipynb`
**Propósito**: visualización — coroplético, ranking, heatmap cadenas×provincias.
**Clave**: usa GeoJSON `ar.json` de simplemaps.com. El GeoJSON usa "Ciudad de Buenos Aires" → mapear a "CABA" en el join.

---

## Pipeline de `01_exploracion_productos.ipynb` (orden de celdas)

| Cell | Tipo | Descripción |
|------|------|-------------|
| 0 | md | Introducción y objetivo |
| 1 | md | Header sección configuración |
| 2 | code | **Config**: `SEPA_SOURCE`, `SEPA_DIR`, `OUTPUT_DIR`, `SEPA_ZIP_NAME`, `PERIODO`, `MIN_SUCURSALES`, `MIN_PCT_DIAS`, `USE_CACHE` |
| 3 | code | Mount Google Drive (solo si `SEPA_SOURCE = 'mi_drive'`) |
| 4 | code | Imports + instalación dependencias + resolución de paths + `CACHE_DIR` |
| 5 | code | `resolver_maestro()` — local-first, GitHub fallback; resuelve los 3 maestros |
| 6 | md | Header sección carga de datos |
| 7 | code | `cargar_sepa()` — streaming a disco + chunked CSV + float32 (precios SIN divisor) |
| 8 | code | Carga las 2 partes + consolidar por (producto × sucursal) + autodetección `FACTOR_PRECIO` + parquet cache |
| 9 | code | Verificación de escala de precios (top 10 productos por n_sucursales) |
| 10 | md | Header sección maestros |
| 11 | code | Carga `Maestro de Productos` → `df_prod_uniq` |
| 12 | code | Carga `maestro_sucursales_completo` → `df_suc_maest` y `maestro-provincias` → `df_provincias` |
| 13 | md | Header sección enriquecimiento |
| 14 | code | **Anti-OOM — celda clave**: merge con geografía + nombre cadena (vectorizado) → `df_suc_enr` → agrega inmediatamente a `df_cov` (producto × cadena × provincia) + `df_price_stats` (producto) + `_cad_agg`; `del df_suc_enr` |
| 15 | code | Distribución por cadena comercial y por región (desde `df_cov`) |
| 16 | code | Top 20 productos más reportados (desde `df_cov`) |
| 17 | md | Header sección análisis de cobertura |
| 18 | code | Agrega `df_cov` → `df_cob` (nivel producto); merge con `df_price_stats` y `_cad_agg`; calcula `score_cobertura` |
| 19 | code | Histogramas de distribución de cobertura |
| 20 | code | Filtros candidatos → `candidatos`, `cand_con_maestro` |
| 21 | code | Heatmaps top-40 × cadena y × provincia (desde `df_cov`); `del df_cov` |
| 22 | md | Header sección canasta |
| 23 | code | `GRUPOS_CANASTA` + `seleccionar_grupo()` + construcción `df_canasta` |
| 24 | code | Print canasta por grupo |
| 25 | code | Gráficos: barras de cobertura por grupo + dispersión de precios |
| 26 | md | Header sección exportación |
| 27 | code | Export Excel: hoja Canasta (colores por grupo) + hoja Candidatos + hoja Selección (candidatos ordenados + columna `cantidad` vacía en amarillo, fuente del próximo notebook) |

---

## Arquitectura anti-OOM (desde commit fd5e014)

El diseño clave está en **cell-14**. El problema original era que `df_enr` (~50M filas × 20 columnas, ~10 GB) permanecía en memoria durante 7 celdas.

```
df_suc (~50M filas, ~6 GB)
    ↓ merge geo (sucursal → PROVINCIA, REGION)
    ↓ normalización PROVINCIA_NOMBRE
    ↓ nombre_cadena vectorizado
    ↓ drop columnas innecesarias
df_suc_enr (~50M filas, ~7 GB)   ← pico de RAM aceptable
    ↓ groupby → df_price_stats (precio por producto, ~170K filas)
    ↓ groupby → df_cov (producto × cadena × provincia, ~2M filas)
    del df_suc_enr; gc.collect()  ← RAM: ~10 GB → ~600 MB
df_cov (~2M filas) + df_price_stats (~170K filas)
    ↓ todas las celdas 15-27 trabajan sobre estos frames pequeños
```

**Por qué funciona**: el peak de RAM (~7 GB para `df_suc_enr`) se libera inmediatamente. Los groupby posteriores operan sobre 2M filas en lugar de 50M.

---

## Configuración actual (mayo 2026)

```python
SEPA_SOURCE   = 'mi_drive'
SEPA_DIR      = '/content/drive/MyDrive/carga'
OUTPUT_DIR    = '/content/drive/MyDrive/carga/output_canasta'
SEPA_ZIP_NAME = '2026A.zip'
PERIODO       = '2026-04'

MIN_CADENAS    = total_cadenas     # dinámico — TODAS las cadenas activas
MIN_PROVINCIAS = total_provincias  # dinámico — TODAS las provincias activas
MIN_SUCURSALES = 50
MIN_PCT_DIAS   = 0.50
USE_CACHE      = True
```

---

## Score de cobertura

```python
score_cobertura = (pct_cadenas * 0.5 + pct_provincias * 0.5) * pct_dias_promedio
```

Donde:
- `pct_cadenas` = n_cadenas / total_cadenas (total de `id_bandera` únicos en el dataset)
- `pct_provincias` = n_provincias / total_provincias (total de provincias únicas en el dataset)
- `pct_dias_promedio` = promedio de `pct_dias` por celda (producto × cadena × provincia) en `df_cov`

---

## Output Excel

`canasta_representativa_{PERIODO}.xlsx`:
- **Canasta**: ~60 productos coloreados por grupo (11 grupos), encabezado azul marino `#1F4E79`
- **Candidatos**: ~41K productos, para el economista

Columnas completas:
```
periodo, grupo_canasta (*),
id_producto, descripcion, marca, presentacion, unidad,
rubro, categoria, subcategoria (*),
n_cadenas, n_cadenas_com, n_provincias, n_sucursales,
pct_dias_promedio,
precio_mediano, precio_p25, precio_p75,
score_cobertura,
cadenas_presentes
```
`(*)` = solo en la hoja Canasta / solo en la hoja Candidatos respectivamente.

---

## Métricas de ejecución real (abril 2026, commit fd5e014)

Primer run completo post-fix anti-OOM. Sin crashes. Resultados observados:

| Métrica | Valor |
|---------|-------|
| `df_cov` (nivel producto × cadena × provincia) | 2,686,965 filas × 8 cols |
| `df_price_stats` (nivel producto) | 98,720 filas × 5 cols |
| Grupos corporativos activos (`id_bandera` únicos) | 5 |
| Provincias activas | 24 |
| Productos que pasan todos los umbrales | 3,776 |
| Productos con maestro completo (`cand_con_maestro`) | 3,650 |
| Productos en canasta final | 54 |
| Cadenas comerciales identificadas nominalmente | 15 (de 33 activos) |
| Cadenas sin nombre en diccionario ("Comercio X") | 18 |

### Hallazgos post-primera ejecución (bugs identificados — ya resueltos)

**Grupo Lácteos = 0 productos (BUG-6 → ✅ Resuelto)**
Las kw anteriores no matcheaban `categoria='Lácteos'` (string literal en el maestro). Fix: `kw=['lácteos','lacteos']`.

**Contaminación de grupos (BUG-7, BUG-8 → ✅ Resueltos)**
- `categoria='Conservas'` incluye frutas Y carnes enlatadas → fix: `excluir_subcat=['Patés y Picadillos','Conservas de Pescado']`
- `categoria='Fiambrería'` incluye fiambres Y quesos untables → fix: `excluir_subcat=['Quesos Untables',...]`

**Bebidas incompletas (BUG-9 → ✅ Resuelto)**
Yerba/té/café viven en `rubro='Almacén'`, `categoria='Infusiones'`. Fix: añadir `'Almacén'` a los rubros de Bebidas no alcohólicas.

**`'carne'` ≠ substring de `'Carnicería'` (BUG-11 → ✅ Resuelto)**
Los 13 candidatos de `categoria='Carnicería'` (embutidos curados) no aparecían porque `'carne' in 'Carnicería'` → `False`. Fix: añadir `'carnicería','carniceria'` a las kw.

**id_producto exportado como entero (BUG-10 → ✅ Resuelto)**
~93 EANs cortos perdían sus ceros iniciales. Fix: `str.zfill(13)` en cell-27 antes del export.

**Cadenas comerciales activas (de los 5 grupos corporativos)**:
Con el diccionario `(id_comercio, id_bandera)`, los 5 grupos corporativos se mapean a banners reales. Los 18 "Comercio X" son comercios minoristas fuera del conjunto principal (algunos con precios atípicos ~$550k–$820k, probablemente especialidades o importados).

### Hallazgos de revisión del Excel de salida

**Productos no alimentarios en Candidatos**:
~37 productos (impresoras, TVs, electrodomésticos, artículos de Bazar) superan los umbrales de cobertura porque se venden en supermercados a nivel nacional. No son bugs — los umbrales son por cobertura, no por categoría. El economista debe filtrarlos manualmente o se puede agregar un filtro por `rubro not in ['Bazar','Electrónica','Limpieza del Hogar']`.

**EAN duplicados en Candidatos**:
~14 pares de `(descripcion, marca)` idénticos con distinto `id_producto`. Son SKUs diferentes (distinto packaging, gramaje, o presentación con código propio). Precio puede diferir ~5–10%. No son bugs — el EAN distingue variantes.

**Contenido real de `categoria='Carnicería'`**:
Los 13 productos son **embutidos curados** (Leberwurst, Salamín, Bondiola, Paleta), NO carnes frescas. Las carnes frescas no tienen cobertura nacional suficiente para superar los umbrales dinámicos (MIN_CADENAS=5, MIN_PROVINCIAS=24).

---

## Canasta ICM-UADE — Composición vigente (51 productos, revisada 2026-05-29)

La canasta fue construida a partir de la hoja `Selección` del nb01 y revisada en base a trazabilidad temporal y cobertura. Se reemplazaron 4 productos con baja trazabilidad por alternativas con 100% de presencia desde enero 2024.

| Categoría | EAN | Producto | Qty/mes |
|-----------|-----|----------|---------|
| Lácteos | 7790742363008 | Leche La Serenísima Entera 1L | 20 |
| Lácteos | 7793940054006 | Manteca La Serenísima 200g | 2 |
| Lácteos | 7790742625304 | Dulce de Leche La Serenísima 400g | 2 |
| Lácteos | 7791337061361 | Queso Crema Casancrem 290g | 2 |
| Lácteos | 7791337007611 | Yogur Firme Frutilla Yogurisimo 190g | 8 |
| Cereales | 7790070337009 | Fideos Tallarines Lucchetti 500g | 4 |
| Cereales | 7790070336293 | Fideos Tirabuzón Matarazzo 500g | 4 |
| Cereales | 7791120031557 | Arroz Molinos Ala 1kg | 2 |
| Cereales | 7792180139320 | Harina Cañuelas 1kg | 2 |
| Cereales | 7790040143234 | Galletitas Chocolinas 262g | 2 |
| Cereales | 7622201735258 | Galletitas Oreo 354g | 1 |
| Cereales | 7790070621801 | Ravioles La Salteña 900g | 2 |
| Aceites | 7790070012050 | Aceite Girasol Cocinero 900ml | 3 |
| Azúcar y dulces | 7792540250450 | Azúcar Ledesma 1kg | 2 |
| Azúcar y dulces | 7793360131516 | Mermelada Durazno La Campagnola 390g | 2 |
| Azúcar y dulces | 7793360131530 | Mermelada Frutilla La Campagnola 390g | 1 |
| Infusiones | 7790387013610 | Yerba Taragüí 1kg | 2 |
| Infusiones | 8445291082199 | Café Dolca 100g | 2 |
| Infusiones | 7790387800142 | Té Taragüí 50 saquitos | 1 |
| Bebidas | 7790895000232 | Coca Cola Lata 354cc | 6 |
| Bebidas | 7790895000270 | Sprite 2.25L | 4 |
| Bebidas | 7790895001017 | Fanta 2.25L | 2 |
| Bebidas | 7790895640476 | Aquarius Pera 1.5L | 4 |
| Condimentos | 7794000003408 | Mayonesa Hellmanns 320g | 2 |
| Condimentos | 7794000006485 | Mostaza Savora 500g | 1 |
| Condimentos | 7794000006188 | Ketchup Hellmanns 250g | 1 |
| Condimentos | 7791004000051 | Sal Celusal 1kg | 1 |
| Condimentos | 7792900093246 | Vinagre Dos Anclas 1L | 1 |
| Condimentos | 7794000008533 | Caldo Knorr 12 un | 1 |
| Proteínas | 7798092353731 | Huevos Carnave Cartón 6 un | 4 |
| Proteínas | 7790360967411 | **Hamburguesas Swift XL 250g** ← nuevo | 4 |
| Proteínas | 7790580131357 | Atún La Campagnola 170g | 3 |
| Proteínas | 7790079018367 | Leberwurst Paladini 200g | 2 |
| Tomate/legumbres | 7790580138868 | Puré de Tomate La Campagnola 530g | 3 |
| Tomate/legumbres | 7790580567101 | Tomate en lata Arcor 400g | 2 |
| Tomate/legumbres | 7793360132483 | Porotos Alubia La Campagnola 300g | 2 |
| Limpieza | 7793253003784 | **Lavandina Anti-splash Ayudín 2L** ← nuevo | 2 |
| Limpieza | 7791290794061 | Detergente Cif 500ml | 2 |
| Limpieza | 7791290792074 | Jabón Polvo Ala 3kg | 1 |
| Limpieza | 7793253005221 | Desinfectante Ayudín 500ml | 1 |
| Limpieza | 7790990001790 | Jabón Zorro 150g | 4 |
| Limpieza | 7790117000231 | Bolsas Residuos Asurín 30 un | 2 |
| Higiene | 7790990000830 | **Jabón Plusbelle 125g** ← nuevo | 4 |
| Higiene | 7509546686516 | Crema Dental Colgate 180g | 2 |
| Higiene | 7891010255275 | **Listerine Antisarro 500ml** ← nuevo | 1 |
| Higiene | 7791293050607 | Desodorante Axe 230ml | 1 |
| Higiene | 7791293048505 | Antitranspirante Dove 150ml | 1 |
| Higiene | 7791070000696 | Papel Higiénico Campanita 4x120m | 3 |
| Higiene | 7791290793606 | Suavizante Comfort 1L | 2 |
| Extra | 8445291121904 | Cacao Nesquik 800g | 1 |
| Extra | 7790580138721 | Polenta Prestopronta 730g | 2 |

**4 reemplazos vs. versión anterior** (criterio: trazabilidad + cobertura + masividad):
- Paty 250g (82.1%, nuevo jun-2024) → **Swift XL 250g** (100%, score 0.925)
- Lavandina Ayudín Original 2L (75%, nuevo ago-2024) → **Lavandina Anti-splash Ayudín 2L** (100%, score 0.919)
- Jabón Dove 90g (82.1%, nuevo jun-2024) → **Jabón Plusbelle 125g** (100%, score 0.994)
- Plax 250ml (82.1%, genuinamente inestable) → **Listerine Antisarro 500ml** (100%, score 0.949)

**Trazabilidad de la canasta** (28 meses ene-2024 → abr-2026): promedio 99.4%, 48/51 al 100%.

---

## Métricas Notebook 02 — Ejecución con canasta revisada (abril 2026, canasta con 4 reemplazos)

| Métrica | Valor |
|---------|-------|
| Costo ICM-UADE promedio nacional | **$478.836 ARS** |
| Rango por sucursal | $440.012 – $528.014 |
| Provincia más barata | Chaco ($463.679, -3.17%) |
| Provincia más cara | Santa Cruz ($507.864, +6.06%) |
| Sucursales válidas (≥15 productos propios) | 2.372 |
| Cadenas con datos | 16 |
| Provincias con datos | **24** (San Juan ahora aparece — BUG-15 confirmado resuelto) |
| Cadena más cara | La Anónima ($496.634) |
| Cadena más barata (ranking nacional) | Hipermercado Libertad ($451.972) |
| Barrio CABA más barato | Villa Soldati ($477.650, -1.09% vs CABA) |
| Barrio CABA más caro (ranking) | Recoleta ($485.969, +0.63% vs CABA) |
| Meses en serie histórica | 28 (2024-01 → 2026-04) |
| Costo ICM-UADE vs IPC General abr-2026 | +3.10% ICM vs +2.58% IPC |
| Cache parquet | `hist_0a6651c5.parquet` |

### Ramp-up de la serie histórica (por qué 48→51 EANs)

La serie empieza con 48 EANs en enero 2024 porque 3 productos de la canasta entraron al SEPA durante 2024:

| Producto | Entró | Meses (de 28) | Trazabilidad |
|----------|-------|--------------|--------------|
| Galletitas Chocolinas 262g | feb-2024 | 27 | 96.4% |
| Puré de Tomate La Campagnola 530g | mar-2024 | 26 | 92.9% |
| Cacao Nesquik 800g | jun-2024 | 23 | 82.1% |

Los 4 reemplazos (Swift XL, Lavandina Anti-splash, Plusbelle, Listerine) están todos al 100% desde enero 2024 — confirmado.

---

## Historial de cambios

### 2026-06-01 — Canastas ENGHo v3: 4 canastas por quintil con doble filtro calidad

- **Canastas definidas** basadas en ENGHo 2017/18 (INDEC) + coeficiente de Engel:
  - `cantidad_01` = **Vulnerable** (Q1, Engel ~36%, precio ≤ P33, 46 productos)
  - `cantidad_02` = **Popular** (Q2, Engel ~28%, precio P25-P55, 61 productos)
  - `cantidad_03` = **Media** (Q3-Q4, Engel ~22%, precio P40-P70, 73 productos)
  - `cantidad_04` = **Medio-Alto** (Q5, Engel ~15%, precio P55-P85, 77 productos)
- **Doble filtro de calidad**: `score_cobertura >= 0.88` AND `pct_trazabilidad >= 90%`
- **Correcciones v2→v3**: 4 EANs malformados corregidos a 13 dígitos; huevos agregados a todas las canastas; Pampa Brewing→Schneider; Tintura→Crema Facial Neutrógena; Coca Light→regular; Tic Tac→Menthoplus; Oblea→Gallo plain
- Archivo de referencia: `canastas_argentina_2026_v3.txt` (en Downloads del analista)
- Ver metodología completa en `docs/METODOLOGIA.md`

### 2026-06-01 — Rewrite completo nb02: soporte multi-canasta (commit c85aa84)

**Cambio arquitectural mayor**: el notebook 02 ahora procesa hasta 6 canastas simultáneamente.

- **CELDA 3**: lee `cantidad_01`..`cantidad_06`, construye `CANASTAS` dict (solo columnas activas), `CANASTA_EANS_NORM` = unión de todos los EANs activos
- **CELDA 7**: un `groupby().apply()` por canasta → `canasta_geo_dict`. Limpieza geográfica (CABA filter, reclasificación por coordenadas) se hace UNA SOLA VEZ
- **CELDA 8**: análisis provincial por canasta → `serie_prov_dict`, `prom_nac_dict`
- **CELDA 9**: UN SOLO cache raw (`hist_union_HASH.parquet`) para la unión de EANs; luego agregación por canasta en memoria (sin releer ZIPs). Hash basado solo en EANs, no en cantidades
- **CELDA 11**: comparativa por canasta → `comparativa_dict`, `df_g_dict`
- **CELDA 12**: gráfico de índices y variaciones con todas las canastas activas + IPC (líneas)
- **CELDA 13**: Cuadro 1 + LaTeX por canasta
- **CELDA 14**: un mapa coroplético por canasta (`mapa_canasta_{short}_{mes}.png`)
- **CELDA 16**: rankings nacional + AMBA por canasta
- **CELDA 17**: un mapa Folium HTML por canasta (`mapa_interactivo_{mes}_{short}.html`)
- **CELDA 18**: ranking barrios CABA por canasta
- **CELDA 19**: Excel con `Evolucion_IPC` (wide, todas canastas), `Prov_{short}`, `Ranking_{short}`, `Sucs_{short}` por canasta, `Serie_precios` con col `canasta_id`

**Nombres y colores**:
- `cantidad_01` = Vulnerable (#0055A4) · `cantidad_02` = Popular (#e74c3c)
- `cantidad_03` = Media (#27ae60) · `cantidad_04` = Media Alta (#f39c12)
- `cantidad_05` = Canasta 05 (#9b59b6) · `cantidad_06` = Canasta 06 (#1abc9c)

### 2026-06-01 — Soporte multi-canasta en nb01: 6 columnas cantidad (commit 566f033)

- La hoja `Selección` (y `Productos unicos`) del Excel exportado por nb01 ahora tiene **6 columnas de cantidad** (`cantidad_01` ... `cantidad_06`) en lugar de una sola `cantidad`
- Cada columna permite definir una canasta independiente
- Todas resaltadas en amarillo (fill `FFF9C4`) con encabezado naranja (`F9A825`), ancho 10
- Pendiente: adaptar nb02 para procesar las 6 canastas en paralelo (próxima sesión)

### 2026-05-29 — Robustez para canastas pequeñas/especializadas (commits e979ae2, 6289ab8)

- **BUG-19**: `MIN_PRODUCTOS_PROPIOS = 15` con canasta de 12 productos → 0 sucursales válidas. Fix: safeguard en CELDA 3 que auto-ajusta a `N_CANASTA // 2` cuando `MIN_PRODUCTOS_PROPIOS >= N_CANASTA`. No afecta ICM-UADE (51 productos).
- **BUG-18**: `IndexError` en CELDA 11/12 cuando la serie histórica está vacía. Ocurre con EANs PLU (prefijo 27.../28...) que no existen en el SEPA histórico. Fix: guarda `_serie_vacia` en CELDA 11 y envuelve la lógica de gráficos de CELDA 12 en `if len(df_g) > 0:`.
- El notebook ahora soporta **cualquier canasta** — desde 1 producto hasta 100+, con o sin historia disponible. Siempre ejecuta completo y produce todos los outputs disponibles para los datos que tiene.

### 2026-05-29 — Mejoras visuales y corrección de coordenadas nb02 (commits 4bcb92d, 7c3fe29)

- Todos los gráficos exportados a **dpi=600** (antes 150/200)
- **CELDA 15 reemplazada**: 4 gráficos nuevos — barplot 3 paneles por provincia (productos únicos · cadenas · sucursales), barplot 3 paneles por cadena, heatmap binario presencia cadena×provincia, heatmap log₁₀ intensidad. Datos derivados de `precio_mes` + `canasta_geo_filtros` para incluir `n_productos_unicos` real.
- Mapa coroplético y rankings: **sin título principal** 
- Rankings: eje X con separador de miles en formato argentino (`$478.836`)
- **CELDA 7 — reclasificación por coordenadas** (BUG-16): reemplaza el descarte de sucursales por reclasificación usando bounding boxes de las 24 provincias. Preserva todos los datos, corrige la provincia según lat/lon.
- BUG-17: docstring triple-quote en `_geocodif()` cerraba el `cell_code` externo → cambiado a comentario de línea
- Output de CELDA 15: 4 archivos en lugar de 2 (`cobertura_provincia_`, `cobertura_cadena_`, `matriz_presencia_`, `matriz_intensidad_` — todos `_MMAAAA.png`)

### 2026-05-29 — Ejecución final confirmada con canasta revisada

- ✅ BUG-15 confirmado resuelto: San Juan aparece correctamente en mapa y cuadro provincial
- ✅ 4 reemplazos todos al 100% trazabilidad desde ene-2024 (Swift XL, Anti-splash, Plusbelle, Listerine)
- ✅ Serie histórica: 28 meses, ramp-up 48→51 EANs explicado (3 productos nuevos en 2024)
- ✅ 48/51 productos al 100%, promedio 99.4%. Mínimo: Nesquik 82.1% (nuevo desde jun-2024, no inestable)
- Cache nuevo: `hist_0a6651c5.parquet`

### 2026-05-29 — ICM-UADE, BUG-15, mejoras nb02 (commits 6fe5a5e, 17ae989, 96f83f5)

- **BUG-15**: San Juan no aparecía en mapa coroplético. El maestro usa `"San juan"` (j minúscula) → agregado a `PROV_NORM`
- **Notebook 01**: nueva hoja `Productos unicos` (~70K–100K productos sin umbrales, mismas columnas que Selección)
- **Notebook 02**: renombrado a "ICM-UADE"; gráficos con etiquetas en español (`ene-24`, `feb-24`...)
- **Gráfico 2**: 3 barras por mes (ICM-UADE + IPC General + IPC Alimentos y bebidas)
- **Cache**: hash MD5 incluye EANs + cantidades → cambiar `cantidad` invalida cache automáticamente
- **MES_INICIO_GRAFICO**: auto-adapta al primer mes de la serie si el configurado no existe
- **Hoja Serie_precios**: nueva hoja en Excel de nb02 con precio mediano por producto por mes (serie completa)
- **Canasta ICM-UADE**: 4 reemplazos (ver tabla arriba). Trazabilidad promedio 99.4%
- **README**: reescrito completo con guía de ejecución paso a paso, outputs de ambos notebooks, métricas

### 2026-05-29 — IPC.xlsx formato real confirmado (commit a409d7e)

- Columna `date` = `datetime64` (Excel serial → pandas auto-convierte). La visualización `ene-17` es solo formato de celda.
- Fast path en CELDA 10: `pd.api.types.is_datetime64_any_dtype()` + `.dt.strftime('%Y-%m')` directo
- Fallback para archivos con fechas como texto `ene-2017` incluido (parseo manual con dict español)

### 2026-05-28 — Notebook 02 completo: análisis canasta elegida, mapas, rankings, IPC

- **Nuevo notebook** `02_evolucion_canasta_representativa.ipynb` (20 celdas) generado desde `notebooks/gen_nb02.py`
- Canasta leída desde hoja `Selección`/`Seleccion` del Excel del nb01 (fallback accent-safe)
- `calcular_canasta_completa()`: costo por sucursal con imputación nacional para productos faltantes; filtrado a MIN_PRODUCTOS_PROPIOS=15
- Serie histórica con caché parquet clave MD5 del set de EANs (invalidación automática al cambiar canasta)
- IPC desde `carga/IPC.xlsx` (nombre exacto en mayúsculas — case-sensitive en Colab)
- Gráficos: índices base mar-2024 + barras mensuales, `COLOR_CANASTA='#0055A4'`
- Cuadro 1 provincial + LaTeX, mapa coroplético con `ar.json`
- Rankings nacionales + AMBA (RdYlGn), mapa Folium con FeatureGroups + panel JS
- Ranking CABA con 48 bounding boxes de barrios, cobertura por provincia y cadena
- **BUG-14**: `ipc.xlsx` no encontrado → nombre real es `IPC.xlsx` (case-sensitive). Fix: fallback que prueba `IPC.xlsx`, `ipc.xlsx`, `IPC.XLSX` en orden
- README actualizado con badge Colab + estructura del repo

### 2026-05-27 — Fix BUG-12/13: implementos físicos y beauty/styling fuera de la canasta (este commit)
- **BUG-12**: "Cabo Metálico Glow" y similares aparecían en Limpieza del hogar (`subcategoria='Palas y Cabos'`). Fix: `excluir_subcat=['Palas y Cabos','Escobas y Escobillones','Plumeros y Limpiavidrios']`
- **BUG-13**: Tintura de cabello (Issue) y Protector Térmico (Roby) ocupaban top-3/4 de Higiene por alta cobertura nacional. Fix: `excluir_subcat=['Coloración','Fijación']` → desodorantes Dove entran al grupo
- Revisión exhaustiva del Excel de segunda ejecución: BUG-10 confirmado resuelto (EANs como texto en Excel con `data_type=s` verificado via openpyxl); 37 productos no alimentarios en Candidatos (esperado — pasan umbrales por cobertura); datos sucios en maestro documentados (Aceite Natura `presentacion=45778`, Crema Dermaglós `subcategoria=Rotisería`)

### 2026-05-27 — Fix BUG-10/11 + nueva firma seleccionar_grupo() (commit f67de87)
- **BUG-10**: `id_producto` exportado como int64 → EANs con ceros iniciales truncados. Fix: `str.zfill(13)` en cell-27 para `canasta_export` y `candidatos_export`
- **BUG-11**: `'carne'` no es substring de `'Carnicería'` → 13 embutidos curados de alta cobertura nunca incluidos. Fix: añadidas `'carnicería','carniceria'` a las kw del grupo Carnes
- **Nueva firma**: `seleccionar_grupo(df, rubros, kw, excluir_kw, max_n, excluir_subcat=None)` — nuevo parámetro `excluir_subcat` filtra por columna `subcategoria` para categorías heterogéneas
- Fixes BUG-6..9 de commit 3c66c3c verificados con segunda ejecución: 8 Lácteos, 6 Carnes limpios, Bebidas con yerba/té/café

### 2026-05-27 — Fix selección de grupos BUG-6..9 (commit 3c66c3c)
- **BUG-6**: Lácteos = 0 → `kw=['lácteos','lacteos']` matchea el valor literal de `categoria` en el maestro; verificado: 8 Lácteos correctos
- **BUG-7**: Azúcar contamina con Paté/Picadillo → `excluir_subcat=['Patés y Picadillos','Conservas de Pescado']`
- **BUG-8**: Carnes contamina con quesos de Fiambrería → `excluir_subcat=['Quesos Untables',...]`
- **BUG-9**: Bebidas sin yerba/té/café → añadido `rubro='Almacén'` + kw `'infusion'`; ahora: Yerba Liebig, Café Dolca, Té Inti Grey

### 2026-05-27 — Análisis post-ejecución: bugs en selección de grupos (BUG-6..9)
- **BUG-6**: Lácteos = 0 — kw `['leche','yogur',...]` no matchean `categoria='Lácteos'` del maestro; fix = `kw=['lácteos','lacteos']`
- **BUG-7**: Azúcar contamina con carnes enlatadas (`categoria='Conservas'` incluye ambas)
- **BUG-8**: Carnes contamina con quesos de Fiambrería (`excluir_kw` opera sobre `categoria`, no `descripcion`)
- **BUG-9**: Bebidas incompletas — yerba, té, café, agua mineral ausentes; investigar categorías reales en maestro
- Documentados en `BUGS_Y_MEJORAS.md`, requieren fix en cell-23 y posiblemente ampliar `seleccionar_grupo()`

### 2026-05-27 — Fix OOM definitivo: rediseño anti-OOM (commit fd5e014)
- Eliminado `df_enr` del pipeline — reemplazado por `df_cov` (producto × cadena × provincia) y `df_price_stats`
- `del df_suc_enr; gc.collect()` inmediatamente después de la agregación: RAM baja de ~10 GB a ~600 MB
- Cells 14, 15, 16, 18, 21 reescritas para usar los frames pequeños
- BUG-5 documentado y resuelto en `BUGS_Y_MEJORAS.md`

### 2026-05-27 — Fix observed=True en groupby (commit 01b4175)
- Añadido `observed=True` a todos los `groupby()` sobre columnas de dtype `category`
- Sin este fix, pandas genera el producto cartesiano de todos los niveles → shape 384 quadrillones → MemoryError 1.33 EiB

### 2026-05-27 — Fix OOM inicial + vectorización (commit 15936ba)
- Reemplazado `df.apply(lambda r: get_nombre_cadena(...), axis=1)` por lookup vectorizado con `.map()` sobre clave compuesta
- Lambda en `.agg()` para `cadenas_presentes` reemplazada por cálculo sobre frame deduplicado (~16 filas/producto en lugar de millones)

### 2026-05-27 — Fix bugs críticos + nuevas features (commit e23bff5)
- **BUG-1**: autodetección de FACTOR_PRECIO (mediana > 10,000 → centavos) en lugar de división fija /100
- **BUG-2**: diccionario `(id_comercio, id_bandera)` → nombre cadena; columna `nombre_cadena` y `cadenas_presentes` en Excel
- **BUG-3**: `excluir_kw` ampliados para Lácteos y Carnes (previene productos contaminantes)
- **BUG-4**: `.str.title()` en normalización de provincia → "San juan" → "San Juan"
- **MEJORA-1**: parquet cache snappy en `OUTPUT_DIR/_cache/`
- **MEJORA-3**: columnas `n_cadenas_com`, `cadenas_presentes` en Excel de salida
- Columna `periodo` = `PERIODO` para identificar el período en notebooks consumidores

### 2026-05-27 — Cobertura por provincias (commit ~8396bea)
- Reemplazado `pct_regiones` / `MIN_REGIONES` por `pct_provincias` / `MIN_PROVINCIAS`
- `SEPA_SOURCE` default cambiado a `'mi_drive'`; eliminada opción `'publico'` (carga.zip fue borrado)
- Heatmap ahora pivota por `PROVINCIA_NOMBRE`

### 2026-05-26 — Fix bugs de selección de canasta
- Bebidas: añadido `excluir_kw` para prevenir que 'te' matchee 'Espumantes'
- Lácteos: eliminado 'postre', añadido `excluir_kw=['repostería','reposteria']`
- Provincias duplicadas: normalización con regex `'^Provincia de '` + CABA
