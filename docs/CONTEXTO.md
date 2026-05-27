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
**Clave**: tiene la autodetección de FACTOR_PRECIO que hay que replicar aquí.

### 3. `analisis_SEPA_evolucion_AMBA.ipynb`
**Propósito**: foco en AMBA, 16 cadenas comerciales, mapas Folium interactivos.
**Clave crítica**: procesa los MISMOS archivos que `exploracion_productos.ipynb` y confirma **FACTOR_PRECIO = 1** para datos de abril 2026. Tiene el diccionario completo de `(id_comercio, id_bandera)` → nombre de cadena.
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

| Cell | Descripción |
|------|-------------|
| 0 | Config: `SEPA_SOURCE`, `SEPA_DIR`, `OUTPUT_DIR`, `SEPA_ZIP_NAME`, `MIN_SUCURSALES`, `MIN_PCT_DIAS` |
| 1 | Mount Google Drive (si `SEPA_SOURCE = 'mi_drive'`) |
| 2 | Imports + validación ZIP |
| 3 | Carga maestros (local-first, GitHub fallback) |
| 4 | `cargar_sepa()` — streaming a disco + chunked CSV + float32 |
| 5 | Consolidar por (producto × sucursal), calcular pct_dias |
| 6 | Enriquecimiento: join con maestros de sucursales, productos, provincias |
| 7 | Normalización de `PROVINCIA_NOMBRE` |
| 8 | Análisis de cobertura + score |
| 9 | Filtros candidatos (dinámicos) |
| 10 | Selección canasta por grupos con `seleccionar_grupo()` |
| 11 | Visualizaciones (heatmap, etc.) |
| 12 | Export Excel |

---

## Configuración actual (mayo 2026)

```python
SEPA_SOURCE   = 'mi_drive'
SEPA_DIR      = '/content/drive/MyDrive/carga'
OUTPUT_DIR    = '/content/drive/MyDrive/carga/output_canasta'
SEPA_ZIP_NAME = '2026A.zip'

MIN_CADENAS    = total_cadenas     # dinámico — TODAS las cadenas activas
MIN_PROVINCIAS = total_provincias  # dinámico — TODAS las provincias activas
MIN_SUCURSALES = 50
MIN_PCT_DIAS   = 0.50
```

---

## Score de cobertura

```python
score_cobertura = (pct_cadenas * 0.5 + pct_provincias * 0.5) * pct_dias_promedio
```

Donde:
- `pct_cadenas` = n_cadenas / total_cadenas (total de id_bandera únicos en el dataset)
- `pct_provincias` = n_provincias / total_provincias (total de provincias únicas en el dataset)
- `pct_dias_promedio` = promedio de (dias_con_precio / total_dias_parte) por sucursal

---

## Output Excel

`canasta_representativa_MMAAAA.xlsx`:
- **Canasta**: ~60 productos coloreados por grupo (11 grupos), encabezado azul marino `#1F4E79`
- **Candidatos**: ~41K productos, para el economista

Columnas: `grupo_canasta, id_producto, descripcion, marca, presentacion, unidad, rubro, categoria, n_cadenas, n_provincias, n_sucursales, pct_dias_promedio, precio_mediano, precio_p25, precio_p75, score_cobertura`

---

## Historial de cambios

### 2026-05-27 — Cobertura por provincias
- Reemplazado `pct_regiones` / `MIN_REGIONES` por `pct_provincias` / `MIN_PROVINCIAS`
- `SEPA_SOURCE` default cambiado a `'mi_drive'`; eliminada opción `'publico'` (carga.zip fue borrado)
- Heatmap ahora pivota por `PROVINCIA_NOMBRE`

### 2026-05-26 — Fix bugs de selección de canasta
- Bebidas: añadido `excluir_kw` para prevenir que 'te' matchee 'Espumantes'
- Lácteos: eliminado 'postre', añadido `excluir_kw=['repostería','reposteria']`
- Provincias duplicadas: normalización con regex `'^Provincia de '` + CABA
