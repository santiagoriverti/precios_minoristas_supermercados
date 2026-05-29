# Precios Minoristas en Supermercados — ICM-UADE

Construcción del **Índice de Canasta Mensual UADE (ICM-UADE)** a partir de los datos públicos del [SEPA](https://datos.produccion.gob.ar/dataset/sepa-precios) (Sistema Electrónico de Publicidad de Precios Argentinos). El pipeline selecciona automáticamente los productos con mayor cobertura geográfica y temporal, calcula el costo mensual de la canasta por sucursal y provincia, y lo compara con el IPC INDEC.

---

## ¿Qué hace este proyecto?

El SEPA publica diariamente los precios reportados por las principales cadenas de supermercados de Argentina: Carrefour, Coto, DIA, Jumbo, La Anónima, Disco, Vea, ChangoMas, Cooperativa Obrera y otras. Los archivos cubren decenas de miles de productos en miles de sucursales a lo largo de todo el país.

El proyecto responde dos preguntas:

1. **¿Qué productos tienen la mayor cobertura comercial y geográfica?** → Notebook 01 selecciona automáticamente los más representativos y los entrega como base para armar una canasta.
2. **¿Cómo evolucionó el costo de esa canasta y cómo se compara con el IPC?** → Notebook 02 calcula el costo mensual por sucursal, lo agrega por provincia y cadena, y genera comparativas, mapas y rankings.

---

## Notebooks

| Notebook | Descripción | Abrir en Colab |
|----------|-------------|----------------|
| `01_exploracion_productos` | Construye la canasta representativa. Detecta automáticamente el último mes disponible en los ZIPs del SEPA y genera `canasta_representativa_YYYY-MM.xlsx` con **cuatro hojas**. | [![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/santiagoriverti/precios_minoristas_supermercados/blob/main/notebooks/01_exploracion_productos.ipynb) |
| `02_evolucion_canasta_representativa` | Analiza la evolución del ICM-UADE. Lee la hoja `Selección` del Excel del notebook anterior (con las cantidades completadas por el economista), calcula el costo por sucursal y provincia, compara con el IPC INDEC, y genera gráficos, mapas y rankings. | [![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/santiagoriverti/precios_minoristas_supermercados/blob/main/notebooks/02_evolucion_canasta_representativa.ipynb) |

> **¿Ves una versión vieja en Colab?** El badge siempre apunta a la última versión en GitHub, pero Colab puede mostrar una copia cacheada de tu Drive. Para forzar la actualización: eliminá el notebook de `Mi unidad/Colab Notebooks/` en Google Drive y volvé a hacer clic en el badge.

---

## Cómo ejecutar

### Requisitos previos

1. Una cuenta de Google con Google Drive
2. Los ZIPs del SEPA en tu Drive (ver [Datos SEPA](#datos-sepa))
3. Para el Notebook 02: además de los ZIPs, necesitás `IPC.xlsx` y `ar.json` en la carpeta `carga/` (ver abajo)

### Paso 1 — Notebook 01: construir la canasta

1. Hacer clic en el badge **Abrir en Colab**
2. En la celda de configuración, verificar solo dos parámetros:
   ```python
   SEPA_SOURCE = 'mi_drive'
   SEPA_DIR    = '/content/drive/MyDrive/carga'  # carpeta con los ZIPs

   PERIODO = None   # None = autodetectar el último mes disponible
                    # o forzar un mes específico: PERIODO = '2026-04'
   ```
3. Ejecutar las celdas en orden — el mes se detecta automáticamente y los maestros se descargan desde GitHub
4. El output se guarda en `SEPA_DIR/output_canasta/canasta_representativa_YYYY-MM.xlsx`
5. **Abrir el Excel** → ir a la hoja `Selección` → completar la columna `cantidad` (amarilla) con las unidades mensuales de cada producto de la canasta

### Paso 2 — Notebook 02: analizar la evolución

1. Hacer clic en el badge **Abrir en Colab**
2. En la celda de configuración, verificar:
   ```python
   SEPA_DIR   = '/content/drive/MyDrive/carga'
   OUTPUT_DIR = '/content/drive/MyDrive/carga/output_canasta'

   MES_INICIO_HISTORICO = '2024-01'   # primer mes de la serie histórica
   MES_INICIO_GRAFICO   = '2024-03'   # base del índice en los gráficos
                                       # (se auto-adapta si el mes no existe en la serie)
   ```
3. Ejecutar las celdas en orden
4. **Primera ejecución con una canasta nueva:** la CELDA 9 recalcula la serie histórica completa (~60 min). Las siguientes ejecuciones usan caché y son inmediatas.

> **El caché se invalida automáticamente** si cambiás cualquier EAN o cualquier `cantidad` de la canasta — no hace falta borrar nada manualmente.

> Los notebooks instalan automáticamente las dependencias que no vienen por defecto en Colab (`openpyxl`, `folium`, `pyarrow`, etc.).

---

## Archivos auxiliares requeridos en Drive (Notebook 02)

| Archivo | Ubicación en Drive | Descripción |
|---------|--------------------|-------------|
| `IPC.xlsx` | `carga/IPC.xlsx` | IPC INDEC mensual desde 2017. Columna `date` (datetime), `Nivel general` (float), `Alimentos y bebidas no alcohólicas` (float) + 11 categorías más |
| `ar.json` | `carga/ar.json` | GeoJSON de las 24 provincias argentinas (simplemaps.com) |
| `canasta_representativa_YYYY-MM.xlsx` | `carga/output_canasta/` | Generado por el Notebook 01. El Notebook 02 toma automáticamente el más reciente |

---

## Output del Notebook 01 — `canasta_representativa_YYYY-MM.xlsx`

El archivo tiene **cuatro hojas**:

### Hoja `Canasta` (~65 productos)

Selección automática de los productos más representativos, organizados en **11 grupos** y coloreados por grupo (encabezado azul marino `#1F4E79`). Columnas:

| Columna | Descripción |
|---------|-------------|
| `periodo` | Período analizado (ej. `2026-04`) |
| `grupo_canasta` | Grupo al que pertenece (Lácteos, Carnes, etc.) |
| `id_producto` | EAN-13 del producto (texto, con ceros iniciales) |
| `descripcion` | Descripción del producto |
| `marca` | Marca comercial |
| `presentacion` | Tamaño / formato (ej. `1 L`, `500 g`) |
| `unidad` | Unidad de medida |
| `rubro` | Rubro del maestro SEPA (Frescos, Almacén, Bebidas...) |
| `categoria` | Categoría del maestro (Lácteos, Fiambrería, Conservas...) |
| `n_cadenas` | Cantidad de grupos corporativos donde se vende (máx. 5) |
| `n_cadenas_com` | Cantidad de banners comerciales donde se vende |
| `n_provincias` | Cantidad de provincias donde se vende (máx. 24) |
| `n_sucursales` | Cantidad de sucursales donde se vende |
| `pct_dias_promedio` | Fracción de días del período con precio reportado |
| `precio_mediano` | Precio mediano nacional (en pesos) |
| `precio_p25` | Percentil 25 de precios |
| `precio_p75` | Percentil 75 de precios |
| `score_cobertura` | Score de representatividad (ver fórmula abajo) |
| `cadenas_presentes` | Lista de cadenas donde está disponible |

### Hoja `Candidatos` (~3.650 productos)

Todos los productos que superan los **umbrales estrictos** (presencia en todas las cadenas activas y todas las provincias activas). Incluye columna `subcategoria`. Para referencia del economista.

### Hoja `Selección` (~15.000–30.000 productos)

Universo ampliado con **umbrales permisivos** (≥3 cadenas, ≥18 provincias, ≥30 sucursales), ordenado por `rubro → categoría → score_cobertura`. Incluye columna **`cantidad`** (resaltada en amarillo) vacía para que el economista indique cuántas unidades de cada producto incluir en su canasta. Esta hoja es la fuente de datos del Notebook 02.

### Hoja `Productos unicos` (~70.000–100.000 productos)

Todos los productos presentes en el dataset que tienen información en el maestro de productos (`rubro` no vacío), **sin ningún umbral de cobertura**. Mismas columnas que `Selección` (incluye `cantidad` vacía y `subcategoria`). Permite explorar el universo completo de productos disponibles en el SEPA, ordenado por `rubro → categoría → score_cobertura`.

---

## Output del Notebook 02

### Gráficos (`.png`)

| Archivo | Contenido |
|---------|-----------|
| `indices_canasta_vs_ipc_MMAAAA.png` | **Gráfico 1** — Índice ICM-UADE vs IPC General vs IPC Alimentos (base = primer mes del período, etiquetas en español) |
| `variaciones_canasta_vs_ipc_MMAAAA.png` | **Gráfico 2** — Variación mensual (%) con tres barras por mes: ICM-UADE · IPC General · IPC Alimentos |
| `mapa_canasta_YYYY-MM.png` | Mapa coroplético con el costo mediano de la canasta por provincia |
| `cobertura_provincia_MMAAAA.png` | Sucursales y cadenas con datos por provincia |
| `cobertura_cadena_MMAAAA.png` | Sucursales y provincias por cadena |
| `ranking_cadenas_nacional_MMAAAA.png` | Ranking de cadenas por costo promedio de la canasta (nacional) |
| `ranking_cadenas_amba_MMAAAA.png` | Ídem para AMBA (Buenos Aires + CABA) |

### Mapa interactivo

`mapa_interactivo_MMAAAA.html` — Mapa Folium con todas las sucursales, coloreadas por costo de canasta. Incluye:
- Panel de capas por cadena (activar/desactivar)
- Filtros de provincia y tipo de sucursal (supermercado / hipermercado)
- Popup con detalle de cada producto al hacer clic en una sucursal

### Excel de análisis — `canasta_analisis_YYYY-MM.xlsx`

Cinco hojas:

| Hoja | Contenido |
|------|-----------|
| `Evolucion_IPC` | Serie mensual: costo ICM-UADE + variación + IPC General + IPC Alimentos |
| `Por_provincia` | Costo mediano de la canasta por provincia para el último mes |
| `Por_sucursal` | Costo de la canasta por sucursal, con cadena, provincia y coordenadas |
| `Ranking_cadenas` | Costo promedio por cadena y desvío vs. promedio nacional |
| `Serie_precios` | **Precio mediano nacional por producto por mes** (serie histórica completa). Permite analizar la evolución individual de cada EAN a lo largo del tiempo |

### LaTeX

`tabla_canasta_provincias_YYYY-MM.tex` — Tabla LaTeX lista para incluir en un paper.

---

## Score de cobertura

El criterio de selección central del pipeline:

```
score_cobertura = (pct_cadenas × 0.5 + pct_provincias × 0.5) × pct_dias_promedio
```

Donde:
- `pct_cadenas` = grupos corporativos con el producto / total de grupos activos en el dataset
- `pct_provincias` = provincias con el producto / total de provincias activas en el dataset
- `pct_dias_promedio` = fracción promedio de días del período con precio reportado (por celda producto × cadena × provincia)

Un score de `1.0` significa que el producto está en **todas las cadenas, todas las provincias, y todos los días del período**.

### Umbrales de filtrado

El pipeline usa **dos niveles de umbrales**:

**Umbrales estrictos** — para hojas Canasta y Candidatos:

| Umbral | Valor | Descripción |
|--------|-------|-------------|
| `MIN_CADENAS` | dinámico (= total activos, típicamente 5) | Debe estar en todos los grupos corporativos activos |
| `MIN_PROVINCIAS` | dinámico (= total activas, típicamente 24) | Debe estar en todas las provincias activas |
| `MIN_SUCURSALES` | 50 | Mínimo de sucursales con precio |
| `MIN_PCT_DIAS` | 0.50 | Al menos 50% de los días con precio reportado |

**Umbrales amplios** — para hoja Selección:

| Umbral | Valor | Descripción |
|--------|-------|-------------|
| `MIN_CADENAS_SEL` | 3 | Al menos 3 de los grupos corporativos activos |
| `MIN_PROVINCIAS_SEL` | 18 | Al menos 18 de las 24 provincias activas |
| `MIN_SUCURSALES_SEL` | 30 | Mínimo de sucursales con precio |
| `MIN_PCT_DIAS` | 0.50 | Igual que el nivel estricto |

Los umbrales estrictos son **dinámicos**: se calculan a partir del dataset real. Esto garantiza que solo se exigen las cadenas y provincias que efectivamente reportaron precios en ese período.

---

## Grupos de la canasta

Los 11 grupos con sus criterios de selección:

| Grupo | Rubros | Top N |
|-------|--------|-------|
| Lácteos | Frescos (`categoria='Lácteos'`) | 8 |
| Carnes y fiambres | Frescos, Almacén, Congelados | 6 |
| Cereales y derivados | Almacén | 8 |
| Aceites y grasas | Almacén | 4 |
| Azúcar, dulces y conservas | Almacén | 6 |
| Bebidas no alcohólicas | Bebidas, Almacén (incluye Infusiones: yerba/té/café) | 8 |
| Bebidas alcohólicas | Bebidas | 6 |
| Limpieza del hogar | Limpieza | 7 |
| Higiene y cuidado personal | Perfumería | 6 |
| Huevos | Frescos, Almacén | 2 |
| Condimentos y aderezos | Almacén | 5 |

> **Nota sobre Infusiones**: yerba mate, té y café se encuentran en `rubro='Almacén'`, `categoria='Infusiones'` en el maestro SEPA — no en el rubro Bebidas.

---

## Cadenas comerciales cubiertas

El SEPA semestral identifica cadenas por `(id_comercio, id_bandera)`. Los 5 grupos corporativos principales se mapean a ~16 banners comerciales. Además se reconocen cadenas regionales:

| Corporativo / Cadena | Banners |
|----------------------|---------|
| Cencosud | Vea · Disco · Jumbo |
| Carrefour | Carrefour · Carrefour Market · Carrefour Express |
| Walmart/ChangoMas | ChangoMas · Hiper ChangoMas · Mi ChangoMas |
| Libertad | Hipermercado Libertad · Mini Libertad |
| La Anónima | La Anónima |
| Coto | Coto |
| Cooperativa Obrera | Cooperativa Obrera |
| DIA | DIA |
| Regionales | Hipermercado Misiones · Cadena 8 (Córdoba) · LAR · Toledo · Pasamonte |

---

## Datos SEPA

Los archivos de precios **no están incluidos en este repositorio** por su tamaño. Se descargan desde la fuente oficial:

- **Portal**: [datos.produccion.gob.ar/dataset/sepa-precios](https://datos.produccion.gob.ar/dataset/sepa-precios)

Estructura esperada en Google Drive:

```
MyDrive/carga/
├── 2024A.zip     # Enero–junio 2024
├── 2024B.zip     # Julio–diciembre 2024
├── 2025A.zip     # Enero–junio 2025
├── 2025B.zip     # Julio–diciembre 2025
└── 2026A.zip     # Enero–junio 2026 (se va completando mes a mes)
    (futuro) 2026B.zip  # Julio–diciembre 2026
```

Cada ZIP contiene archivos `MMAAAA_pais_parteNCOMPLETO.csv.gz` — formato wide con una columna de precio por día del período. Los notebooks **detectan automáticamente el último mes disponible** escaneando todos los ZIPs: cuando se agregue mayo o junio a `2026A.zip`, o se cree `2026B.zip`, ambos notebooks lo toman sin ningún cambio de código.

Los datos de **2025B en adelante ya vienen en pesos** (factor = 1). Los notebooks autodetectan el factor de conversión.

---

## Estructura del repositorio

```
precios_minoristas_supermercados/
├── README.md
├── notebooks/
│   ├── 01_exploracion_productos.ipynb            # Notebook 1 — canasta representativa
│   ├── 02_evolucion_canasta_representativa.ipynb # Notebook 2 — análisis ICM-UADE
│   └── gen_nb02.py                               # Script fuente que genera el Notebook 2
├── data/                                # Maestros de referencia (se descargan automáticamente)
│   ├── Maestro de Productos Interno.xlsx    # ~176K productos con rubro/categoría/subcategoría
│   ├── maestro_sucursales_completo.xlsx     # 3.611 sucursales con cadena, provincia, región
│   └── maestro-provincias.xlsx              # Códigos SEPA → nombres de provincia
└── docs/                                # Documentación técnica
    ├── CONTEXTO.md                      # Arquitectura, pipeline detallado, historial de cambios
    ├── SEPA_TECNICO.md                  # Formato SEPA, factor precio, cadenas, trampas conocidas
    └── BUGS_Y_MEJORAS.md               # Bugs resueltos y mejoras pendientes
```

---

## Arquitectura: por qué no crashea la RAM

El principal desafío técnico es que el dataset tiene ~50 millones de filas (producto × sucursal × día). La solución es agregar inmediatamente después del enriquecimiento y liberar el frame grande:

```
df_suc (~50M filas, ~6 GB)
    ↓ merge con geografía + nombre cadena
df_suc_enr (~50M filas, ~7 GB)   ← pico de RAM aceptable
    ↓ groupby → df_price_stats (~170K filas)   precio por producto
    ↓ groupby → df_cov (~2M filas)             producto × cadena × provincia
    del df_suc_enr; gc.collect()               RAM: ~7 GB → ~600 MB
df_cov + df_price_stats
    ↓ todas las celdas siguientes trabajan sobre estos frames pequeños
```

El Notebook 02 usa un caché parquet (keyed por hash MD5 de EANs + cantidades) que evita reprocesar los ZIPs históricos en ejecuciones subsiguientes.

---

## Documentación técnica

| Documento | Contenido |
|-----------|-----------|
| [`docs/CONTEXTO.md`](docs/CONTEXTO.md) | Objetivo del proyecto, descripción del pipeline celda por celda, métricas de ejecución reales, historial completo de cambios |
| [`docs/SEPA_TECNICO.md`](docs/SEPA_TECNICO.md) | Formato semestral vs. diario, autodetección de FACTOR_PRECIO, diccionario de cadenas, maestros de referencia, arquitectura anti-OOM, trampas conocidas en la selección de grupos, patrones técnicos del Notebook 02 |
| [`docs/BUGS_Y_MEJORAS.md`](docs/BUGS_Y_MEJORAS.md) | Bugs resueltos y mejoras pendientes, causa raíz, evidencia y fix aplicado |

---

## Métricas de ejecuciones reales (abril 2026)

### Notebook 01

| Métrica | Valor |
|---------|-------|
| Grupos corporativos activos | 5 |
| Provincias activas | 24 |
| Filas en `df_cov` (producto × cadena × provincia) | ~2,7M |
| Productos únicos en el dataset | ~170K |
| Productos que pasan umbrales estrictos | ~3.800 |
| Productos con maestro completo (Candidatos) | ~3.650 |
| Productos en la canasta final (Canasta) | ~65 |
| Productos en hoja Selección (umbrales amplios) | ~25.500 |
| Productos en hoja Productos unicos (sin umbrales) | ~70K–100K |
| RAM en pico (df_suc_enr) | ~7 GB |
| RAM después de liberar df_suc_enr | ~600 MB |

### Notebook 02

| Métrica | Valor |
|---------|-------|
| Productos en la canasta (ICM-UADE) | 51 |
| Unidades mensuales totales | 136 |
| Sucursales válidas (≥15 productos propios) | 2.372 |
| Cadenas con datos | 16 |
| Provincias con datos | 24 |
| Meses de serie histórica | 28 (ene-2024 → abr-2026) |
| Costo ICM-UADE promedio nacional (abr-2026) | **$478.836 ARS** |
| Rango por sucursal (abr-2026) | $440.012 – $528.014 |
| Provincia más barata | Chaco ($463.679, -3.17%) |
| Provincia más cara | Santa Cruz ($507.864, +6.06%) |
| Trazabilidad promedio de la canasta | 99,4% (48/51 productos al 100%) |
| Tiempo primera ejecución (sin caché) | ~60 min |
| Tiempo ejecuciones siguientes (con caché) | ~5 min |
