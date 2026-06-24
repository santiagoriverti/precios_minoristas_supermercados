# Precios Minoristas en Supermercados — ICR

Construcción del **Índice de Consumo Representativo (ICR)** a partir de los datos públicos del [SEPA](https://datos.produccion.gob.ar/dataset/sepa-precios) (Sistema Electrónico de Publicidad de Precios Argentinos). El pipeline selecciona automáticamente los productos con mayor cobertura geográfica y temporal, calcula el costo mensual de hasta **6 canastas simultáneas** por sucursal y provincia, y las compara con el IPC INDEC.

---

## ¿Qué hace este proyecto?

El SEPA publica diariamente los precios reportados por las principales cadenas de supermercados de Argentina: Carrefour, Coto, DIA, Jumbo, La Anónima, Disco, Vea, ChangoMas, Cooperativa Obrera y otras. Los archivos cubren decenas de miles de productos en miles de sucursales a lo largo de todo el país.

El proyecto responde dos preguntas:

1. **¿Qué productos tienen la mayor cobertura comercial y geográfica?** → Notebook 01 selecciona automáticamente los más representativos y los entrega como base para armar canastas.
2. **¿Cómo evolucionó el costo de esas canastas y cómo se comparan con el IPC?** → Notebook 02 calcula el costo mensual por sucursal para cada canasta definida, las agrega por provincia y cadena, y genera comparativas, mapas y rankings.

---

## Notebooks

| Notebook | Descripción | Abrir |
|----------|-------------|----------------|
| `01_exploracion_productos` | Construye la canasta representativa. Detecta automáticamente el último mes disponible en los ZIPs del SEPA y genera `canasta_representativa_YYYY-MM.xlsx` con **cuatro hojas**, incluyendo la hoja `Selección` con **6 columnas de cantidad** para definir hasta 6 canastas distintas. | [![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/santiagoriverti/precios_minoristas_supermercados/blob/main/notebooks/01_exploracion_productos.ipynb) |
| `02_evolucion_canasta_representativa` | Analiza la evolución del ICR para **hasta 6 canastas simultáneas**. Lee las columnas `cantidad_01`..`cantidad_06` de la hoja `Selección`, calcula el costo por sucursal y provincia para cada canasta activa, compara con el IPC INDEC, y genera gráficos, mapas y rankings independientes por canasta. | [![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/santiagoriverti/precios_minoristas_supermercados/blob/main/notebooks/02_evolucion_canasta_representativa.ipynb) |
| `03_consolidacion_ultimo_mes` | Convierte el SEPA **diario** al formato **semestral wide** para analizar el mes en curso sin esperar la consolidación oficial. Subís `ultimo_mes.zip` al entorno de Colab y te devuelve los dos `.csv.gz` para descargar. Ver [sección detallada](#adelantar-el-mes-en-curso--03_consolidacion_ultimo_mes). | [![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/santiagoriverti/precios_minoristas_supermercados/blob/main/notebooks/03_consolidacion_ultimo_mes.ipynb) |
| `04_precios_seleccion` | Exporta un **Excel** con los precios diarios del último mes para todos los supermercados a menos de X km de un punto: una hoja por sucursal (productos × días) + una hoja general (producto × super, precio promedio). Ver [sección detallada](#precios-por-selección-geográfica--04_precios_seleccion). | [![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/santiagoriverti/precios_minoristas_supermercados/blob/main/notebooks/04_precios_seleccion.ipynb) |

> **¿Ves una versión vieja en Colab?** El badge siempre apunta a la última versión en GitHub, pero Colab puede mostrar una copia cacheada de tu Drive. Para forzar la actualización: eliminá el notebook de `Mi unidad/Colab Notebooks/` en Google Drive y volvé a hacer clic en el badge.

---

## Cómo ejecutar

### Requisitos previos

1. Una cuenta de Google con Google Drive
2. Los ZIPs del SEPA en tu Drive (ver [Datos SEPA](#datos-sepa))
3. Para el Notebook 02: además de los ZIPs, necesitás `IPC.xlsx` y `ar.json` en la carpeta `carga/` (ver abajo)

### Paso 1 — Notebook 01: construir el universo de productos

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
5. **Abrir el Excel** → ir a la hoja `Selección` → completar las columnas de cantidad en amarillo:

| Columna | Canasta | Uso |
|---------|---------|-----|
| `cantidad_01` | **Vulnerable** | Canasta de referencia para hogares vulnerables |
| `cantidad_02` | **Popular** | Canasta de referencia para hogares populares |
| `cantidad_03` | **Media** | Canasta de referencia para clase media |
| `cantidad_04` | **Media Alta** | Canasta de referencia para clase media alta |
| `cantidad_05` | **Celíaca Media** | Variante sin TACC de la Canasta Media ($691.836, +9,0% prima celíaca) |
| `cantidad_06` | **Vegana Básica** | Dieta vegana integral comparable a Popular ($427.033, −5,5% vs Popular) |

Solo se procesan las columnas con al menos un producto con cantidad > 0. Las columnas vacías se ignoran automáticamente.

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
4. **Primera ejecución:** la CELDA 9 construye la serie histórica completa (~60 min). Las siguientes ejecuciones usan caché y son rápidas (~5 min).

> **El caché se invalida automáticamente** si cambiás qué EANs están en las canastas activas. Cambiar solo las cantidades no invalida el caché.

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

Universo ampliado con **umbrales permisivos** (≥3 cadenas, ≥18 provincias, ≥30 sucursales), ordenado por `rubro → categoría → score_cobertura`. Incluye **6 columnas de cantidad** resaltadas en amarillo (`cantidad_01` a `cantidad_06`) para definir hasta 6 canastas independientes. Esta hoja es la fuente de datos del Notebook 02.

### Hoja `Productos unicos` (~70.000–100.000 productos)

Todos los productos presentes en el dataset que tienen información en el maestro de productos (`rubro` no vacío), **sin ningún umbral de cobertura**. Mismas columnas que `Selección`. Permite explorar el universo completo de productos disponibles en el SEPA.

---

## Output del Notebook 02

El Notebook 02 genera outputs **por cada canasta activa** (columnas con al menos un producto con cantidad > 0).

### Gráficos combinados (`.png`) — todas las canastas en un solo gráfico

| Archivo | Contenido |
|---------|-----------|
| `indices_canasta_vs_ipc_MMAAAA.png` | Índices base = 100 para todas las canastas activas + IPC General + IPC Alimentos |
| `variaciones_canasta_vs_ipc_MMAAAA.png` | Variación mensual (%) de todas las canastas + IPC |
| `cobertura_provincia_MMAAAA.png` | 3 paneles: productos únicos · cadenas · sucursales por provincia |
| `cobertura_cadena_MMAAAA.png` | 3 paneles: productos únicos · provincias · sucursales por cadena |
| `matriz_presencia_MMAAAA.png` | Heatmap binario: presencia (●) de cada cadena en cada provincia |
| `matriz_intensidad_MMAAAA.png` | Heatmap de intensidad log₁₀ de productos únicos por cadena×provincia |

### Gráficos por canasta (`.png`) — uno por cada canasta activa

Donde `{canasta}` es `vulnerable`, `popular`, `media`, `media_alta`, `canasta05`, `canasta06`:

| Archivo | Contenido |
|---------|-----------|
| `mapa_canasta_{canasta}_YYYY-MM.png` | Mapa coroplético con el costo mediano por provincia |
| `ranking_cadenas_nacional_MMAAAA_{canasta}.png` | Ranking de cadenas por costo promedio (nacional) |
| `ranking_cadenas_amba_MMAAAA_{canasta}.png` | Ídem para AMBA (Buenos Aires + CABA) |

### Mapa interactivo (`.html`) — un único mapa con todas las canastas

`mapa_interactivo_MMAAAA.html` — Mapa Folium con las ~2.373 sucursales de Argentina, coloreadas por costo de canasta. Incluye:
- **Selector de canasta**: cambiar entre las 6 canastas activas sin recargar
- **Filtro de cadena**: mostrar solo Coto, DIA, Carrefour, etc.
- **Filtro de provincia**: aislar una jurisdicción
- **Popup al click**: nombre de la sucursal, cadena, barrio, provincia, tipo y costo de la canasta seleccionada
- Tamaño: ~3–5 MB (optimizado para servir desde GitHub Pages)

> **Mapa publicado**: [santiagoriverti.github.io/mapa_precios_minoristas](https://santiagoriverti.github.io/mapa_precios_minoristas/)

### Excel de análisis — `canasta_analisis_YYYY-MM.xlsx`

| Hoja | Contenido |
|------|-----------|
| `Evolucion_IPC` | Serie mensual en formato ancho: todas las canastas + IPC General + IPC Alimentos |
| `Prov_{canasta}` | Costo mediano por provincia + desvío vs. promedio nacional (una hoja por canasta) |
| `Ranking_{canasta}` | Ranking de cadenas por costo promedio (una hoja por canasta) |
| `Sucs_{canasta}` | Costo por sucursal con cadena, provincia y coordenadas (una hoja por canasta) |
| `Serie_precios` | Precio mediano por canasta × producto × mes (toda la serie histórica, formato largo) |

### LaTeX (`.tex`) — uno por cada canasta activa

`tabla_canasta_{canasta}_YYYY-MM.tex` — Tabla de provincias lista para incluir en un paper.

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

## Adelantar el mes en curso — `03_consolidacion_ultimo_mes`

El SEPA publica el archivo **semestral consolidado** de cada mes recién **una semana después** de que cierra. Pero también publica los datos **diarios** el mismo día. El `03_consolidacion_ultimo_mes` convierte el SEPA **diario** al formato **semestral wide** que consumen los notebooks 01 y 02, para poder analizar el mes en curso **sin esperar** la consolidación oficial.

> ⚠️ **Recomendado: correrlo LOCAL, no en Colab.** El `ultimo_mes.zip` pesa ~7 GB y subirlo al entorno de Colab suele fallar (la transferencia del navegador se corta). Usá la versión local `notebooks/03_consolidacion_ultimo_mes.py` (ver [**Correrlo localmente**](#correrlo-localmente-recomendado-para-el-zip-de-7-gb) más abajo). La variante Colab (`.ipynb`) queda solo por si algún día el zip es chico.

### Flujo en Colab (solo si el zip es chico)

1. Abrir el notebook con el badge **Abrir en Colab**.
2. Subir `ultimo_mes.zip` al entorno: panel **Archivos** (📁) → arrastrar el `.zip` a `/content/`.
   > Pesa ~7 GB: la subida tarda. No cerrar la pestaña mientras sube.
3. *Entorno de ejecución → Ejecutar todo*.
4. Al terminar, el notebook **descarga automáticamente** los dos archivos:
   - `MMAAAA_pais_parte1COMPLETO.csv.gz` (días 01–15)
   - `MMAAAA_pais_parte2COMPLETO.csv.gz` (días 16–último)
5. Subir esos `.csv.gz` al `2026A.zip` en Drive (`carga/`) y correr los notebooks 01 y 02.

Se puede correr **cualquier día del mes**: con 23 días disponibles arma parte1 (15 días) + parte2 (días 16–23); el día 30 toma el mes completo; el 1° de julio se sube el `ultimo_mes.zip` de julio y arranca el mes nuevo.

### Qué hace

| | |
|---|---|
| **Entrada** | `ultimo_mes.zip` con carpetas diarias `YYYY-MM-DD/`, cada una con un `.zip` por comercio (`comercio.csv`, `sucursales.csv`, `productos.csv`, separador `\|`, precio en **pesos**). |
| **Salida** | `MMAAAA_pais_parte1COMPLETO.csv.gz` (días 01–15) y `MMAAAA_pais_parte2COMPLETO.csv.gz` (días 16–último), formato **idéntico al oficial** (coma, columnas `precio_YYYYMMDD`, precio en **pesos**, faltantes `NA`). |

### Detalles técnicos resueltos

- **Unidades**: el diario y el semestral oficial 2026 están **ambos en pesos** → se exporta tal cual (sin multiplicar). Verificado: mediana oficial mayo ~$4.400.
- **`id_sucursal`**: el diario lo rellena con ceros (`004`), el maestro usa `4` → se quitan los ceros para que el join geográfico matchee (cobertura ~99–100% verificada).
- **Cobertura de comercios**: todos los datos son **minoristas** (no hay mayoristas en ninguna fuente). Los archivos oficiales del SEPA incluyen algunos comercios adicionales (ids 2000/3001…) que la fuente diaria no trae; son **irrelevantes para la canasta** (afectan ~−0,01% el costo, verificado).
- **RAM**: pivota **por comercio**, así el pico de memoria queda acotado (~2–3 GB) y entra holgado en Colab aunque el dataset crudo del mes ronde decenas de GB.

### Correrlo localmente (recomendado para el zip de ~7 GB)

La subida de un `ultimo_mes.zip` de ~7 GB al entorno de Colab suele fallar (la transferencia del navegador no es resumible y se corta). En ese caso conviene correr la versión local `notebooks/03_consolidacion_ultimo_mes.py`, que hace **exactamente lo mismo** sin subir nada — procesa el `.zip` directo desde el disco — y además **empaqueta** los `.csv.gz` dentro de un `2026A.zip` actualizado, listo para subir a Drive.

**Requisitos**: Python 3 con `pandas` y `numpy` (si faltan: `pip install pandas numpy`).

**Paso 1 — configurar las rutas.** Abrir `notebooks/03_consolidacion_ultimo_mes.py` y editar la sección `CONFIGURACIÓN`:

```python
# Zip diario descargado del Ministerio (carpetas YYYY-MM-DD adentro)
ZIP_DIARIO = Path(r"C:\...\sepa_diario_minoristas\ultimo_mes.zip")

# Zip semestral existente a actualizar (debe llamarse YYYYA.zip / YYYYB.zip).
# El mes generado se inserta acá conservando los demás meses.
# Poner None si solo querés los .csv.gz sueltos.
SEMESTRE_ZIP_IN = Path(r"C:\...\carga\2026A.zip")

# Carpeta donde se escriben los .csv.gz y el zip semestral actualizado
OUTPUT_DIR = Path(r"C:\...\salida_consolidada")

MES_FORZADO = None   # None = último mes del zip; o forzar 'YYYY-MM'
```

**Paso 2 — abrir PowerShell en la carpeta del repositorio.**

1. En el **Explorador de Windows** (📁) navegá hasta la carpeta del repo:
   ```
   C:\Users\<usuario>\...\precios_minoristas_supermercados
   ```
2. Hacé clic en la **barra de direcciones** de arriba (la ruta se pone editable), borrala, escribí **`powershell`** y apretá **Enter**.
3. Se abre PowerShell **ya parado en esa carpeta**. El prompt termina con la ruta del repo:
   ```
   PS C:\Users\<usuario>\...\precios_minoristas_supermercados>
   ```
   > Que aparezca esa ruta al final es la señal de que estás en el lugar correcto. (No copies la línea `PS ...>` como comando: es solo el prompt.)

**Paso 3 — ejecutar.** Escribí (o pegá con clic derecho) este comando y apretá **Enter**:

```powershell
python notebooks/03_consolidacion_ultimo_mes.py
```

> Si `python` no se reconoce, probá con `py notebooks/03_consolidacion_ultimo_mes.py`.

**Qué vas a ver mientras corre.** Primero imprime el mes detectado y la lista de comercios (suelen ser ~20 — más que los presentes en un solo día, porque escanea los 23 días):

```
Mes detectado: 2026-06  |  23 días: 2026-06-01 … 2026-06-23
Comercios a procesar: 20 -> ['2', '3', '4', ...]
  [1/20] comercio 2: 960,027 filas (94.0s)
  [2/20] comercio 3: 9,195 filas (1.5s)
  ...
```

- El **primer comercio (2 = La Anónima) tarda ~90 s antes de imprimir su línea `[1/20]`**: parece colgado pero está trabajando, esperá.
- Después baja comercio por comercio. Los grandes (Carrefour=10, DIA=15) son los más lentos.
- **Total ~25–45 min.** No cierres la ventana; podés minimizarla y seguir usando la compu.
- Cuando llega a **`Listo en … min.`**, terminó.

> Si pegaste sin querer la línea del prompt (`PS C:\...>`) y salió un error tipo *"No se encuentra ningún proceso"*, es inofensivo: solo volvé a correr el comando del Paso 2.

**Paso 4 — resultado.** En `OUTPUT_DIR` quedan:
- `MMAAAA_pais_parte1COMPLETO.csv.gz` (días 01–15) y `parte2` (16–último)
- `2026A.zip` actualizado (mes nuevo insertado, meses previos conservados)

Subir ese `2026A.zip` a `carga/` en Drive (reemplaza el viejo) y correr los notebooks 01 y 02.

> **Mes nuevo (julio, etc.)**: reemplazás el `ultimo_mes.zip` por el del mes nuevo y volvés a ejecutar. El mes se autodetecta.

---

## Precios por selección geográfica — `04_precios_seleccion`

Exporta un **Excel con los precios diarios del último mes** para todos los supermercados ubicados a menos de una distancia dada de un **punto** (lat/lon). Útil para análisis local (una ciudad, una zona).

### Flujo en Colab

1. Abrir con el badge **Abrir en Colab**.
2. En la celda de **CONFIGURACIÓN** ajustar el punto y el radio:
   ```python
   PUNTO_LAT   = -37.115479
   PUNTO_LON   = -56.886020
   DIST_MAX_KM = 20.0
   ```
3. *Entorno de ejecución → Ejecutar todo*. Al terminar descarga `precios_seleccion_YYYY-MM.xlsx`.

### Qué contiene el Excel

| Hoja | Contenido |
|------|-----------|
| `Sucursales` | Índice de los locales seleccionados: cadena, sucursal, tipo, localidad, lat/lon, distancia (km) y nº de productos. |
| **una por sucursal** | Todos los productos del local (EAN, descripción, marca, rubro) y el **precio para cada día** del mes. |
| `General` | Todos los productos únicos × supermercado con el **precio promedio del mes**; celda **vacía** si ese super no tiene el producto. Incluye `promedio_general`. |

- Detecta automáticamente el **último mes disponible** (con los días que tenga, sea completo o en curso).
- Distancia por **haversine** (línea recta). Factor centavos→pesos autodetectado sobre la mediana global del mes (robusto). Precios ≤ 0 se tratan como sin dato.
- `MAX_SUCURSALES` limita el nº de hojas como salvaguarda en zonas muy densas.

> Requiere en `carga/` (Drive) los ZIPs SEPA. Los maestros (sucursales y productos) se descargan solos desde GitHub.

---

## Estructura del repositorio

```
precios_minoristas_supermercados/
├── README.md
├── notebooks/
│   ├── 01_exploracion_productos.ipynb            # Notebook 1 — canasta representativa
│   ├── 02_evolucion_canasta_representativa.ipynb # Notebook 2 — análisis ICR multi-canasta
│   ├── 03_consolidacion_ultimo_mes.ipynb         # Notebook 3 — SEPA diario → semestral (Colab, mes en curso)
│   ├── 03_consolidacion_ultimo_mes.py            # Script 3 — misma lógica para correr local
│   ├── 04_precios_seleccion.ipynb                # Notebook 4 — precios diarios por sucursal cercana a un punto
│   ├── gen_nb02.py                               # Script fuente que genera el Notebook 2
│   └── gen_nb04.py                               # Script fuente que genera el Notebook 4
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

### Notebook 01 — anti-OOM

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

### Notebook 02 — caché unión y multi-canasta

El Notebook 02 usa dos estrategias para manejar la complejidad de múltiples canastas:

1. **Un solo caché raw** (`hist_union_HASH.parquet`): la CELDA 9 lee los ZIPs históricos UNA SOLA VEZ para la unión de todos los EANs activos. Luego agrega por canasta en memoria (rápido). El caché se invalida solo si cambia el conjunto de EANs, no las cantidades.

2. **Limpieza geográfica compartida**: la normalización de provincias y la reclasificación por coordenadas se realizan una sola vez sobre el maestro de sucursales, y el resultado se reutiliza para todas las canastas activas.

---

## Documentación técnica

| Documento | Contenido |
|-----------|-----------|
| [`docs/METODOLOGIA.md`](docs/METODOLOGIA.md) | **Metodología completa**: fuente de datos, score de cobertura, canastas ENGHo por quintil (coeficiente de Engel), filtros de calidad (score ≥ 0.88, trazabilidad ≥ 90%), limitaciones conocidas, historial de versiones de canastas |
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

### Notebook 02 — 6 canastas ICR (abril 2026)

| Métrica | Valor |
|---------|-------|
| Sucursales válidas (≥15 productos propios) | ~2.370 por canasta |
| Cadenas con datos | 16 |
| Provincias con datos | 24 |
| EANs únicos (unión de 6 canastas) | 257 |
| Meses de serie histórica | 28 (ene-2024 → abr-2026) |
| Trazabilidad promedio de los 257 EANs | 99,6% |

#### Resultados reales — promedio nacional ponderado por población (abril 2026)

| # | Canasta | Productos | Sucursales | Costo mensual | Referencia |
|---|---------|-----------|------------|---------------|------------|
| 1 | **Vulnerable** | 44 | 2.373 | **$252.982** | Q1, Engel ~36% |
| 2 | **Popular** | 59 | 2.371 | **$451.672** | Q2, Engel ~28% |
| 3 | **Media** | 72 | 2.368 | **$634.923** | Q3–Q4, Engel ~22% |
| 4 | **Media Alta** | 74 | 2.372 | **$879.459** | Q5, Engel ~15% |
| 5 | **Celíaca Media** | 74 | 2.371 | **$691.836** | +9,0% vs Media |
| 6 | **Vegana Básica** | 51 | 2.372 | **$427.033** | −5,5% vs Popular |

#### Dispersión geográfica — canasta Media

| | Provincia | Valor | vs. promedio |
|-|-----------|-------|-------------|
| Más barata | Formosa | $623.080 | −1,87% |
| Más cara | Santa Cruz | $665.723 | +4,85% |
| Dispersión total | | | **6,8%** |

#### Tiempos de ejecución

| Ejecución | Tiempo estimado |
|-----------|-----------------|
| Primera vez (sin caché, 6 canastas, 28 meses) | ~60–90 min |
| Siguientes ejecuciones (con caché) | ~5–15 min |
