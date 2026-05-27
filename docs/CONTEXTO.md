# Contexto del Proyecto — Precios Minoristas SEPA

Última actualización: 2026-05-27

## Objetivo

Construir una **canasta representativa de ~60 productos** a partir de los datos del SEPA (Sistema Electrónico de Publicidad de Precios Argentinos). El output es un Excel con dos hojas:
- **Canasta**: ~60 productos seleccionados por cobertura geográfica y temporal, coloreados por grupo
- **Candidatos**: ~41K productos que superan todos los umbrales, para que el economista arme su propia canasta

## Repositorio

- **GitHub**: santiagoriverti/precios_minoristas_supermercados
- **Notebook principal**: `notebooks/exploracion_productos.ipynb` (ejecutable en Google Colab)
- **Maestros**: `data/` — productos, sucursales, provincias
- **Datos SEPA**: NO están en el repo. Están en Google Drive personal: `/carga/` (2024A.zip, 2024B.zip, 2025A.zip, 2025B.zip, 2026A.zip)

---

## Ecosistema de notebooks relacionados

Este proyecto no existe en aislamiento. Hay múltiples notebooks en otros repositorios que procesan los mismos datos y de los que se pueden tomar patrones.

### 1. `exploracion_productos.ipynb` (este repo)
**Propósito**: selección dinámica de canasta por score de cobertura.
**Enfoque**: todos los productos del SEPA semestral → filtrar por cobertura → seleccionar top-N por grupo.
**Output**: `canasta_representativa_MMAAAA.xlsx`

### 2. `analisis_SEPA_evolucion.ipynb`
**Propósito**: evolución mensual de precios con canasta fija de 30 EANs.
**Enfoque**: procesa múltiples semestres (2022A–2026A), autodetecta FACTOR_PRECIO, calcula serie diaria nacional.
**Output**: `canasta_SEMESTRE_serie.xlsx` (hojas: serie_diaria_nacional, canasta_mes_provincia, canasta_mes_region, canasta_nacional_ponderada)

### 3. `analisis_SEPA_evolucion_AMBA.ipynb`
**Propósito**: foco en AMBA, 16 cadenas comerciales, mapas Folium interactivos.
**Clave crítica**: confirma **FACTOR_PRECIO = 1** para datos de abril 2026. Tiene el diccionario completo de `(id_comercio, id_bandera)` → nombre de cadena.
**Output**: mapa interactivo HTML + Excel con canasta por sucursal.

### 4. `consolidacion_analisis_SEPA.ipynb`
**Propósito**: consolida todos los semestres en una serie temporal de 52 meses (2022–2026).
**Output**: tablas LaTeX para papers + comparación SEPA vs IPC INDEC.
**Dato**: canasta nacional abril 2026 = **$322,566 ARS** (ponderada por Censo 2022).

### 5. `analisis_canasta_SEPA.ipynb`
**Propósito**: usa el formato DIARIO (no semestral) para ver los 28 banners comerciales reales.
**Formato**: `YYYY-MM-DD.zip` → 20 ZIPs por cadena → pipe-separated (`comercio.csv`, `sucursales.csv`, `productos.csv`).
**Clave**: 87,418 EANs únicos, precios directamente en pesos, 14.8M filas.

### 6. `analisis_precios_SEPA.ipynb`
**Propósito**: pipeline sofisticado con parquet cache + clasificación de rubros por keywords.
**Patrones útiles**: float32 desde el inicio, drop de columnas de promo, parquet snappy para cachear.
**Output**: 7,616 productos canastables identificados.

### 7. `analisis_precios_SEPA_2.ipynb`
**Propósito**: deduplicación de variantes del mismo producto.
**Técnica**: `extraer_concepto()` → top-3 palabras significativas minus marca/packaging → colapsa ~10% de duplicados.

### 8. `resultados_canasta_sepa.ipynb`
**Propósito**: visualización — coroplético, ranking, heatmap cadenas×provincias.
**Clave**: usa GeoJSON `ar.json` de simplemaps.com. El GeoJSON usa "Ciudad de Buenos Aires" → mapear a "CABA" en el join.

---

## Pipeline de `exploracion_productos.ipynb` (orden de celdas)

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
| 27 | code | Export Excel: hoja Canasta (colores por grupo) + hoja Candidatos |

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

## Historial de cambios

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
