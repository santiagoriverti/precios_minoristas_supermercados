# Precios Minoristas en Supermercados — Canasta SEPA

Construcción de una **canasta representativa de precios** a partir de los datos públicos del [SEPA](https://datos.produccion.gob.ar/dataset/sepa-precios) (Sistema Electrónico de Publicidad de Precios Argentinos). El pipeline selecciona automáticamente los productos con mayor cobertura geográfica y temporal, y entrega un Excel listo para análisis.

---

## ¿Qué hace este proyecto?

El SEPA publica diariamente los precios reportados por las principales cadenas de supermercados de Argentina: Carrefour, Coto, DIA, Jumbo, La Anónima, Disco, Vea, ChangoMas, Cooperativa Obrera y otras. Los archivos cubren decenas de miles de productos en miles de sucursales a lo largo de todo el país.

Este proyecto procesa esos datos para responder una pregunta concreta: **¿cuáles son los productos con mayor cobertura comercial y geográfica en Argentina?** A partir de eso, construye dos outputs:

- **Canasta automática** (~60 productos): selección por grupos (Lácteos, Carnes, Panificados, etc.) de los productos más representativos según un score de cobertura
- **Lista de candidatos** (~41 000 productos): todos los productos que superan los umbrales de cobertura, para que un economista arme su propia canasta

---

## Notebooks

| Notebook | Descripción | Abrir en Colab |
|----------|-------------|----------------|
| `exploracion_productos` | Construye la canasta representativa. Genera `canasta_representativa_MMAAAA.xlsx` con hoja **Canasta** (~60 productos por grupo, coloreados) y hoja **Candidatos** (~41 000 productos con métricas completas). | [![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/santiagoriverti/precios_minoristas_supermercados/blob/main/notebooks/exploracion_productos.ipynb) |

> **¿Ves una versión vieja en Colab?** El badge siempre apunta a la última versión en GitHub, pero Colab puede mostrar una copia cacheada de tu Drive. Para forzar la actualización: eliminá `Mi unidad/Colab Notebooks/exploracion_productos.ipynb` de tu Google Drive y volvé a hacer clic.

---

## Cómo ejecutar

### Requisitos previos

1. Una cuenta de Google con Google Drive
2. El archivo ZIP del SEPA correspondiente al período que querés analizar (ver [Datos SEPA](#datos-sepa))
3. Subir el ZIP a tu Google Drive en la carpeta `/carga/`

### Pasos

1. Hacer clic en el badge **Abrir en Colab**
2. Ejecutar la celda de configuración (cell-2) y verificar los parámetros:
   ```python
   SEPA_SOURCE   = 'mi_drive'          # fuente de datos
   SEPA_DIR      = '/content/drive/MyDrive/carga'  # carpeta en tu Drive
   SEPA_ZIP_NAME = '2026A.zip'         # nombre del ZIP
   PERIODO       = '2026-04'           # período para identificar el output
   ```
3. Ejecutar las celdas en orden — los maestros de referencia se descargan automáticamente desde GitHub
4. El output se guarda en `SEPA_DIR/output_canasta/canasta_representativa_MMAAAA.xlsx`

> Los notebooks instalan automáticamente las dependencias que no vienen por defecto en Colab (`openpyxl`, etc.).

---

## Output: el Excel de salida

El archivo `canasta_representativa_MMAAAA.xlsx` tiene dos hojas:

### Hoja `Canasta` (~60 productos)

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
| `n_cadenas_com` | Cantidad de banners comerciales donde se vende (máx. ~16) |
| `n_provincias` | Cantidad de provincias donde se vende (máx. 24) |
| `n_sucursales` | Cantidad de sucursales donde se vende |
| `pct_dias_promedio` | Fracción de días del período con precio reportado |
| `precio_mediano` | Precio mediano nacional (en pesos) |
| `precio_p25` | Percentil 25 de precios |
| `precio_p75` | Percentil 75 de precios |
| `score_cobertura` | Score de representatividad (ver fórmula abajo) |
| `cadenas_presentes` | Lista de cadenas donde está disponible |

### Hoja `Candidatos` (~41 000 productos)

Todos los productos que superan los umbrales de cobertura. Incluye columna `subcategoria` en lugar de `grupo_canasta`. Pensada para que el economista filtre por rubro/categoría y seleccione su propia canasta.

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

### Umbrales de filtrado (dinámicos)

Un producto debe pasar **todos** los siguientes umbrales para llegar a la hoja Candidatos:

| Umbral | Valor | Descripción |
|--------|-------|-------------|
| `MIN_CADENAS` | dinámico (= total activos, típicamente 5) | Debe estar en todos los grupos corporativos activos |
| `MIN_PROVINCIAS` | dinámico (= total activas, típicamente 24) | Debe estar en todas las provincias activas |
| `MIN_SUCURSALES` | 50 | Mínimo de sucursales con precio |
| `MIN_PCT_DIAS` | 0.50 | Al menos 50% de los días con precio reportado |

Los umbrales son **dinámicos**: se calculan a partir del dataset real, no son valores fijos. Esto garantiza que solo se exigen las cadenas y provincias que efectivamente reportaron precios en ese período.

---

## Grupos de la canasta

Los 11 grupos con sus criterios de selección:

| Grupo | Rubros | Top N |
|-------|--------|-------|
| Lácteos | Frescos (`categoria='Lácteos'`) | 8 |
| Carnes y fiambres | Frescos, Almacén, Congelados | 6 |
| Panificados y cereales | Almacén | 6 |
| Aceites y grasas | Almacén | 4 |
| Azúcar, dulces y conservas | Almacén | 6 |
| Bebidas no alcohólicas | Bebidas, Almacén (incluye Infusiones: yerba/té/café) | 8 |
| Bebidas alcohólicas | Bebidas | 6 |
| Artículos de limpieza | Limpieza | 6 |
| Higiene y cuidado personal | Perfumería | 6 |
| Almacén general | Almacén | 6 |
| Congelados | Congelados | 4 |

> **Nota sobre Infusiones**: yerba mate, té y café se encuentran en `rubro='Almacén'`, `categoria='Infusiones'` en el maestro SEPA — no en el rubro Bebidas.

---

## Cadenas comerciales cubiertas

El SEPA semestral identifica cadenas por `(id_comercio, id_bandera)`. Los 5 grupos corporativos se mapean a ~16 banners comerciales:

| Corporativo | Banners |
|-------------|---------|
| Cencosud | Vea · Disco · Jumbo |
| Carrefour | Carrefour · Carrefour Market · Carrefour Express |
| Walmart/ChangoMas | ChangoMas · Hiper ChangoMas · Mi ChangoMas |
| Libertad | Hipermercado Libertad · Mini Libertad |
| La Anónima | La Anónima |
| Coto | Coto |
| Cooperativa Obrera | Cooperativa Obrera |
| DIA | DIA |

---

## Datos SEPA

Los archivos de precios **no están incluidos en este repositorio** por su tamaño. Se descargan desde la fuente oficial:

- **Portal**: [datos.produccion.gob.ar/dataset/sepa-precios](https://datos.produccion.gob.ar/dataset/sepa-precios)

Estructura esperada en Google Drive:

```
MyDrive/carga/
├── 2026A.zip     # Enero–junio 2026
├── 2025B.zip     # Julio–diciembre 2025
├── 2025A.zip     # Enero–junio 2025
└── 2024B.zip     # Julio–diciembre 2024
```

Cada ZIP contiene archivos `MMAAAA_pais_parteNcompleto.csv.gz` — formato wide con una columna de precio por día del período. Los datos semestral de **2025B en adelante ya vienen en pesos** (factor = 1). El notebook autodetecta el factor de conversión.

---

## Estructura del repositorio

```
precios_minoristas_supermercados/
├── README.md
├── notebooks/
│   └── exploracion_productos.ipynb      # Notebook principal — ejecutable en Colab
├── data/                                # Maestros de referencia (se descargan automáticamente)
│   ├── Maestro de Productos Interno.xlsx    # ~176K productos con rubro/categoría/subcategoría
│   ├── maestro_sucursales_completo.xlsx     # 3 611 sucursales con cadena, provincia, región
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

El análisis de cobertura, los heatmaps y la selección de canasta operan todos sobre `df_cov` (~2M filas), no sobre el frame original.

---

## Documentación técnica

| Documento | Contenido |
|-----------|-----------|
| [`docs/CONTEXTO.md`](docs/CONTEXTO.md) | Objetivo del proyecto, descripción del pipeline celda por celda, métricas de ejecución reales, historial completo de cambios |
| [`docs/SEPA_TECNICO.md`](docs/SEPA_TECNICO.md) | Formato semestral vs. diario, autodetección de FACTOR_PRECIO, diccionario de cadenas, maestros de referencia, arquitectura anti-OOM, trampas conocidas en la selección de grupos |
| [`docs/BUGS_Y_MEJORAS.md`](docs/BUGS_Y_MEJORAS.md) | Registro de todos los bugs encontrados (resueltos y pendientes), causa raíz, evidencia y fix aplicado |

---

## Métricas de una ejecución real (abril 2026)

| Métrica | Valor |
|---------|-------|
| Grupos corporativos activos | 5 |
| Provincias activas | 24 |
| Filas en `df_cov` (producto × cadena × provincia) | ~2,7M |
| Productos únicos en el dataset | ~170K |
| Productos que pasan todos los umbrales | ~3 800 |
| Productos con maestro completo (candidatos) | ~3 650 |
| Productos en la canasta final | ~60 |
| RAM en pico (df_suc_enr) | ~7 GB |
| RAM después de liberar df_suc_enr | ~600 MB |
