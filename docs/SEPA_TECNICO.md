# SEPA — Referencia Técnica

Última actualización: 2026-09-03 (nb07: lectura semanal + colapso de frescos a tipo [fix RAM] + selección de frescos por categoría; nb02: motor `datos_econometria`)

> **Cambio 2026-08-21 (nb02/nb05, CELDA 6/7)**: el precio por sucursal del mes reportado ahora se calcula sobre **todos los días del mes** —mediana de los días y media con outliers fuera— en vez de tomar solo el primer día (`drop_duplicates keep='first'`, eliminado). El promedio descarta valores fuera de `[mediana/4, mediana×4]` antes de promediar (helper `_pmean`, vectorizado en la CELDA 7). Esto DUPLICA los artefactos: análisis mediana (nombres base) y promedio (sufijo `_prom`). Detalle en `.claude/memory.md`.
>
> **Lectura DIARIA (nb06 — brecha celíaca)**: los archivos semestrales traen **una columna de precio por día** (`precio_YYYYMMDD`; parte1 = días 01–15, parte2 = 16–fin). El Notebook 06 melt-ea esas columnas **conservando la fecha** (`pd.to_datetime(col[-8:], format='%Y%m%d')`) para construir series diarias/semanales/mensuales de la brecha. Cache incremental de meses cerrados + mes en curso fresco (`brecha_dia_{hash}_v1.parquet`). Detalle en `docs/BRECHA_CELIACA.md`.

## Dos formatos completamente distintos

### Formato semestral (el que usa este proyecto)

```
carga/
├── 2026A.zip
│   ├── 042026_pais_parte1COMPLETO.csv.gz   ← días 1–15 de abril 2026
│   └── 042026_pais_parte2COMPLETO.csv.gz   ← días 16–30
├── 2025B.zip
└── ...
```

- **Separador**: coma
- **Columnas fijas**: `id_comercio, id_bandera, id_sucursal, sucursales_provincia, id_producto`
- **Columnas de precio**: `precio_YYYYMMDD` (una por día del período — formato wide)
- **Precios**: entero — VER SECCIÓN FACTOR_PRECIO
- **Valores faltantes**: string `'NA'` (no Python NaN, hay que reemplazar explícitamente)
- `id_producto`: EAN/GTIN; la mayoría son 13 dígitos, algunos son más cortos (UPC-8, UPC-12). **Siempre leer como string** (`dtype={'id_producto':'str'}`). Si en algún paso del pipeline se convierte a int64, los ceros iniciales se pierden al exportar. Fix: `df['id_producto'].astype(str).str.zfill(13)` antes de exportar a Excel.

### Formato diario

```
YYYY-MM-DD.zip
├── cadena1.zip
│   ├── comercio.csv
│   ├── sucursales.csv
│   └── productos.csv
└── ...
```

- **Separador**: pipe `|`
- **Precios**: float en pesos directamente (sin factor)
- **Identidad de cadena**: string completo en `comercio_bandera_nombre`
- **Cadenas visibles**: hasta 28 banners comerciales
- Útil para ver los precios reales de cada banner, pero más difícil de consolidar en el tiempo

---

## FACTOR_PRECIO — crítico para precios correctos

Los datos semestral cambiaron de unidad a lo largo del tiempo:
- **Hasta ~2024**: precios en centavos → dividir /100
- **2025B en adelante**: precios ya en pesos → FACTOR = 1 (NO dividir)

### Autodetección implementada en `01_exploracion_productos.ipynb`

```python
# Después de consolidar df_suc, antes del enriquecimiento:
_mediana_ref = df_suc['precio_promedio'].median()
FACTOR_PRECIO = 100 if _mediana_ref > 10_000 else 1

if FACTOR_PRECIO == 100:
    df_suc['precio_promedio'] = (df_suc['precio_promedio'] / 100).astype('float32')
```

**Umbral**: mediana global del dataset > $10,000 → datos en centavos (divido ÷100). Esto funciona porque la mediana de precio de los productos en centavos ronda 100k–500k, muy lejos del rango pesos (~$500–$5,000).

**Confirmación para abril 2026**: mediana raw ≈ 1,411 → FACTOR = 1 (ya en pesos). Confirmado también por `analisis_SEPA_evolucion_AMBA.ipynb` con productos de referencia específicos.

### Patrón alternativo más robusto (otros notebooks)

```python
# Usar un producto de referencia con precio conocido (sal fina ~$500-$2000 en 2026)
EANS_REFERENCIA = ['7793370008980', '7790895000061', '7793370008188']  # sal, fideos, lavandina

precios_ref = df[df['id_producto'].isin(EANS_REFERENCIA)]['precio_promedio']
mediana_ref = precios_ref.median()

if 30 <= mediana_ref <= 5000:
    FACTOR_PRECIO = 1      # ya en pesos
elif 3000 <= mediana_ref <= 500_000:
    FACTOR_PRECIO = 100    # en centavos, necesita /100
else:
    raise ValueError(f"Mediana de referencia inesperada: {mediana_ref}")
```

---

## Identidad de cadenas en formato semestral

### El problema

`id_bandera` (valores 1-6) identifica el **grupo corporativo** dentro del comercio, NO la cadena comercial. Eso es por qué se ven solo 5-6 "cadenas" cuando en realidad son 16.

### Cómo obtener los nombres reales

Combinar `(id_comercio, id_bandera)` con este diccionario:

```python
NOMBRES_CADENAS_COMPUESTAS = {
    ('9',  '1'): 'Vea',
    ('9',  '2'): 'Disco',
    ('9',  '3'): 'Jumbo',
    ('10', '1'): 'Carrefour',
    ('10', '2'): 'Carrefour Market',
    ('10', '3'): 'Carrefour Express',
    ('11', '2'): 'ChangoMas',
    ('11', '4'): 'Hiper ChangoMas',
    ('11', '5'): 'Mi ChangoMas',
    ('16', '1'): 'Hipermercado Libertad',
    ('16', '2'): 'Mini Libertad',
}

NOMBRES_CADENAS_SIMPLES = {
    '2':  'La Anónima',
    '12': 'Coto',
    '13': 'Cooperativa Obrera',
    '15': 'DIA',
}
```

### Lookup vectorizado (patrón actual del notebook)

```python
# Construir lookup por clave compuesta id_comercio_id_bandera
_lookup_comp = {f"{k[0]}_{k[1]}": v for k, v in _CADENAS_COMPUESTAS.items()}

_ck = df['id_comercio'] + '_' + df['id_bandera']
df['nombre_cadena'] = _ck.map(_lookup_comp)

# Fallback: cadenas simples (solo por id_comercio)
_null = df['nombre_cadena'].isna()
df.loc[_null, 'nombre_cadena'] = df.loc[_null, 'id_comercio'].map(_CADENAS_SIMPLES)

# Residuos desconocidos
_null = df['nombre_cadena'].isna()
df.loc[_null, 'nombre_cadena'] = 'Comercio ' + df.loc[_null, 'id_comercio']
```

> **Por qué NO usar `apply()`**: con 50M filas, `df.apply(lambda r: get_nombre_cadena(r['id_comercio'], r['id_bandera']), axis=1)` ejecuta millones de llamadas Python → agota la RAM. El lookup vectorizado con `.map()` opera en C puro.

### Implicación para el score de cobertura

Con los datos semestral, `MIN_CADENAS = total_cadenas` filtra por grupos corporativos (5-6 valores), no por banners (16). Un producto puede estar en "Carrefour" (id_bandera=1) pero no en "Carrefour Express" (id_bandera=3), y el filtro no lo detecta. Esto es una limitación estructural del formato semestral.

---

## Maestros de referencia

| Archivo | Descripción | Join key |
|---------|-------------|----------|
| `Maestro de Productos Interno.xlsx` | ~176K productos, rubro/categoría/subcategoría | `producto_sepa_id` = `id_producto` |
| `maestro_sucursales_completo.xlsx` | 3,611 sucursales con cadena, provincia, región | `id_comercio` + `id_bandera` + `id_sucursal` |
| `maestro-provincias.xlsx` | código SEPA → nombre legible | `sucursales_provincia` |

### Normalización de provincias (obligatoria)

```python
df['PROVINCIA_NOMBRE'] = (
    df['PROVINCIA'].combine_first(df['provincia'])   # combina dos fuentes
    .str.strip()
    .str.replace(r'^Provincia de ', '', regex=True)
    .str.replace('Ciudad Autónoma de Buenos Aires', 'CABA', regex=False)
    .str.title()   # fix "San juan" → "San Juan" y similares
    .str.replace('Caba', 'CABA', regex=False)  # .title() rompe CABA
)
```

El maestro de sucursales tiene `PROVINCIA` (columna del Excel) y el maestro de provincias tiene `provincia` (columna de mapping del código SEPA). Se combinan con `.combine_first()` para usar la fuente más confiable disponible.

### ⚠️ Inconsistencia de capitalización en el maestro — San Juan (BUG-15, 2026-05-29)

El maestro de sucursales almacena la provincia de San Juan como `"San juan"` (con 'j' minúscula), no como `"San Juan"` ni como `"Provincia de San Juan"`. Si el dict `PROV_NORM` no incluye esta variante exacta, la provincia queda sin normalizar y:

1. El mapa coroplético la muestra en gris (el GeoJSON usa `"San Juan"` — no matchea)
2. El Folium filter muestra las sucursales bajo el label incorrecto

**Fix en `PROV_NORM` (gen_nb02.py CELDA 4)**:

```python
'San Juan':'San Juan',
'San juan':'San Juan',   # ← variante real del maestro (j minúscula)
'SAN JUAN':'San Juan',   # ← defensivo
```

**Reclasificación por coordenadas (CELDA 7)** — para sucursales con provincia incorrecta en el maestro:

```python
# 24 bounding boxes (lat_min, lat_max, lon_min, lon_max), más específico primero
_PROV_BBOX = {
    'CABA':    (-34.72,-34.52,-58.54,-58.33),
    'Tucumán': (-28.0, -26.0, -66.5, -64.5),
    'Jujuy':   (-24.5, -21.5, -67.5, -63.5),
    ... # 24 provincias
}
# Para cada sucursal con provincia inconsistente: buscar la correcta por coords
# y reclasificar SIN descartar la sucursal
```

**Regla general**: nunca descartar sucursales solo porque el maestro tiene su provincia mal etiquetada. Usar coordenadas para determinar la provincia correcta. Siempre registrar la variante exacta del nombre tal como aparece en el maestro. Las variantes conocidas del maestro incluyen al menos: `"San juan"` (San Juan), `"Neuquén"/"Neuquen"` (Neuquén), `"Entre Ríos"/"Entre Rios"` (Entre Ríos).

### Multi-canasta en notebook 02 — caché de unión de EANs

El notebook 02 soporta hasta 6 canastas simultáneas. La CELDA 9 usa **un único caché parquet** para la unión de todos los EANs activos:

```python
_cache_key = hashlib.md5('|'.join(sorted(CANASTA_EANS_NORM)).encode()).hexdigest()[:8]
_cache_path = CACHE_DIR / f'hist_union_{_cache_key}.parquet'
```

- **Invalida** cuando cambia el conjunto de EANs (agregar/quitar productos de cualquier canasta)
- **No invalida** cuando solo cambian las cantidades (mismo conjunto de EANs)
- Después de una invalidación, el parquet viejo queda en `_cache/` → se puede borrar manualmente

### EAN format en SEPA — GS1, PLU codes y EAN-12

**EAN-13 GS1 estándar** (prefijo 77-78 para Argentina, 789 para Brasil, 750 para México):
- Son los más comunes en supermercados. Los prefijos 789... y 750... corresponden a producciones de Brasil y México de marcas multinacionales (Dove, Colgate, P&G). SEPA los reporta con sus EANs originales.
- Siempre guardar como string con `dtype={'id_producto': str}` y normalizar con `.str.lstrip('0')` para el merge.

**EAN-12 / UPC** (12 dígitos, sin cero inicial): poco comunes en SEPA. Agregar cero inicial o buscar el EAN-13 equivalente.

**PLU codes (prefijo 27.../28.../29...)**: generados por balanzas en góndola para productos vendidos por peso. Son efímeros — no aparecen en el SEPA histórico de forma consistente. El notebook los detecta y produce una serie histórica vacía, saltando los gráficos de índices con un aviso.

**EANs malformados** (menos de 12 dígitos): no matchean en SEPA. Agregar ceros iniciales hasta 13 dígitos. La normalización `lstrip('0')` hace que sean equivalentes al EAN con ceros.

### Productos sin TACC en SEPA — cobertura y etiquetado

El SEPA contiene productos con denominaciones explícitas "sin TACC" que facilitan armar canastas celíacas. Principales hallazgos para Argentina 2026:

| Categoría | Producto sin TACC con mejor cobertura | Score | Sucursales |
|-----------|---------------------------------------|-------|-----------|
| Pasta | Fideos Mostacholes Blue Patna 500g | 0.927 | 499 |
| Galletitas saladas | Chalitas Happy Food 100g | 0.901 | 545 |
| Galletitas dulces | Smams Chocolate 200g | 0.902 | 526 |
| Polenta/maíz | Prestopronta 730g (naturalmente GF) | 0.915 | 2.423 |
| Almidón | Maizena 500g (naturalmente GF) | 0.908 | 2.458 |
| Aceite | Aceite Oliva Puro sin TACC (etiquetado) | 0.893 | — |
| Atún | La Campagnola sin TACC (etiquetado) | 0.923 | 2.500 |
| Cacao | Nesquik sin TACC (etiquetado) | 0.931 | 2.466 |
| Caldo | Caldo Verdura Knorr (sin gluten) | 0.918 | 2.512 |

**No existe en SEPA con buena cobertura**: pasta sin TACC de arroz, harina de arroz, pan sin TACC. La cerveza sin gluten tampoco aparece en Candidatos.

**Beer/malta**: Heineken y otras cervezas de malta contienen gluten (cebada). La **sidra** (`7790119002370` Saenz Briones 1888, score 0.870) es el sustituto alcohólico sin gluten con mejor cobertura en SEPA.

### EANs PLU (prefijo 27.../28...) — no están en el SEPA histórico

Los productos vendidos por peso en góndola (frutas, verduras, fiambres a granel) usan códigos PLU generados por las balanzas del supermercado. Estos códigos empiezan con **27...** o **28...** y son efímeros — el mismo producto puede tener distintos EANs en distintas sucursales o fechas. Consecuencias:

- No aparecen en el SEPA histórico de forma consistente → `serie_nacional_valida` vacía
- El notebook lo detecta con `_serie_vacia = len(serie_nacional_valida) == 0` y salta las celdas 11/12 con un aviso
- Los EANs GS1 estándar (prefijo 77... o 78...) SÍ tienen historia consistente

### Frescos por peso (balanza) — seguimiento POR TIPO, no por EAN (patrón de nb07)

Ampliación de lo anterior con datos reales (agosto 2026). Los frescos vendidos por peso usan **códigos de balanza internos** con **prefijo GS1 `2`** ("distribución restringida / in-store"), y **cada cadena inventa el suyo**:

| Ejemplo (Frutas/Verduras) | EAN | Cadenas | Sucursales |
|---|---|---|---|
| Tomate Redondo Elegido 1 Kg | `2490127…` | 1 | 983 (solo DIA) |
| Zanahoria Elegida 1 Kg | `2490122…` | 1 | 983 |
| Asado al Vacío Catte 1 Kg | `2406951…` | 1 | 983 |

Medición sobre `canasta_representativa_2026-08.xlsx`: **51% de Carnicería y 20% de Frutas/Verduras** son códigos de balanza, casi todos presentes en **1 sola cadena**. Conclusión: **no existe "el EAN del tomate"** rastreable entre cadenas → el modelo EAN-canasta de nb01/nb02 no sirve para frescos.

**Solución (nb07)**: seguir el **TIPO de producto**, no el EAN. Se juntan por **regla de nombre** todas las variantes que cada cadena publica (`inc`/`exc` regex sobre la descripción, con borde de palabra `\b` para no colar `camPERA` en `pera`), usando el **maestro SEPA completo** (`maestro_sepa_completo.csv.gz`, que trae TODO lo que se vende, no solo el maestro interno curado). El precio del tipo por sucursal-semana = mediana de las variantes presentes, **normalizado a una unidad comparable**:
- `$/kg`: `precio / gramos_presentación × 1000` (los "1 Kg" de balanza ya vienen en $/kg).
- `$/docena` (huevos): `precio / unidades × 12`.

Así el tipo es comparable entre cadenas y provincias aunque cada una use un EAN distinto. Los frescos **empaquetados con marca** (fiambres, huevos de marca) SÍ tienen EAN universal (prefijo 77…) y podrían ir por EAN, pero nb07 los trata igual por tipo para homogeneidad.

### Safeguard MIN_PRODUCTOS_PROPIOS vs N_CANASTA

Cuando `MIN_PRODUCTOS_PROPIOS >= N_CANASTA` ninguna sucursal puede pasar el filtro. El notebook auto-corrige en CELDA 3:
```python
if MIN_PRODUCTOS_PROPIOS >= N_CANASTA:
    MIN_PRODUCTOS_PROPIOS = max(1, N_CANASTA // 2)
```
Para el ICR (51 productos) con `MIN_PRODUCTOS_PROPIOS=15` esto nunca se activa.

### Mapa Folium lazy popup — archivos livianos con popup on-demand

Con 6 canastas × 2.370 sucursales = 14.220 CircleMarkers, el popup HTML inline hace que el HTML pese 40-50 MB. La solución es **lazy popup**: datos almacenados una vez como JSON, HTML construido por JS al hacer click.

**Arquitectura (CELDA 17 de gen_nb02.py):**
1. `_popup_data` dict Python: por (suc_key) → `{nom, bar, prv, cad, tip, can: {col_id: {t, p, n, it[]}}}`. Items compactos: `[nom[:35], cat[:20], qty, price_int, subtotal_int, is_propio]`.
2. Serializado con `json.dumps(..., separators=(',',':'))` y embebido como `<script type="application/json" id="_pd_json">...</script>` — sin escaping JS.
3. JS lee con `JSON.parse(document.getElementById('_pd_json').textContent)` (lazy: solo cuando se necesita el primer popup).
4. Cada CircleMarker tiene popup mínimo: `<div class="lz-pop" data-key="suc_key" data-can="col_id">Cargando...</div>`.
5. Evento Leaflet `popupopen`: `_bPop(key, canasta_id)` construye el HTML desde el JSON → `e.popup.update()`. El atributo `data-built="1"` evita reconstrucción.

**Resultado:** ~5-10 MB en lugar de ~40-50 MB. Misma funcionalidad y estética.

### Regla crítica en gen_nb02.py: no usar triple-quote dentro de cell_code

El código de cada celda está contenido en un string `"""\..."""`. Usar triple comillas dobles `"""..."""` dentro del código (como docstrings) cierra prematuramente el string externo. Siempre usar comentarios de línea `#` en lugar de docstrings dentro de `cell_code("""\...""")`.

> **Alternativa usada en `gen_nb07.py` (2026-09-01)**: definir cada celda con **raw string** `cell_code(r'''...''')`. Preserva `\b`, `\d`, `\n` sin doble-escape (clave para las regex de selección de frescos por nombre) y evita el bug de escape mixto que apareció en las tablas LaTeX de nb02/nb05. Único cuidado: un raw string no puede terminar en `\` ni contener la secuencia `'''`.

### Regiones del maestro de sucursales

`AMBA`, `Pampeana`, `Patagonia`, `Noroeste`, `Cuyo`, `Noreste`

---

## Lectura eficiente (anti-crash de RAM en Colab)

```python
import zipfile, gzip, shutil, gc
from pathlib import Path
import numpy as np, pandas as pd

_TMP_DIR = Path('/content/tmp_sepa')
_TMP_DIR.mkdir(exist_ok=True)

def cargar_sepa(zip_path, filename):
    """
    Carga un archivo SEPA semestral de forma eficiente.
    Devuelve precios SIN aplicar factor (valores crudos del CSV).
    El factor de conversión se autodetecta y aplica en la celda siguiente.
    """
    # 1. Extraer .csv.gz a disco en streaming (no carga en RAM el archivo comprimido)
    tmp = _TMP_DIR / filename
    with zipfile.ZipFile(zip_path) as z:
        with z.open(filename) as src, open(tmp, 'wb') as dst:
            shutil.copyfileobj(src, dst, length=4*1024*1024)

    # 2. Leer en chunks → reducir a 8 columnas → float32 para precios
    chunks, n_dias = [], None
    with gzip.open(tmp, 'rt', encoding='utf-8') as g:
        for chunk in pd.read_csv(g,
                dtype={'id_comercio':'str','id_bandera':'str',
                       'id_sucursal':'str','id_producto':'str',
                       'sucursales_provincia':'str'},
                chunksize=200_000, low_memory=False):
            price_cols = [c for c in chunk.columns if c.startswith('precio_')]
            if n_dias is None:
                n_dias = len(price_cols)
            prices = chunk[price_cols].replace('NA', np.nan).astype('float32')
            chunk  = chunk.drop(columns=price_cols)
            chunk['precio_promedio']  = prices.mean(axis=1).astype('float32')
            chunk['dias_con_precio']  = prices.notna().sum(axis=1).astype('int16')
            chunk['total_dias_parte'] = np.int16(n_dias)
            del prices
            chunks.append(chunk[['id_comercio','id_bandera','id_sucursal',
                                  'sucursales_provincia','id_producto',
                                  'precio_promedio','dias_con_precio','total_dias_parte']])
    tmp.unlink()
    df = pd.concat(chunks, ignore_index=True)
    del chunks; gc.collect()
    return df
```

> **Por qué streaming a disco**: cargar el .csv.gz completo en BytesIO agota la RAM de Colab (~12 GB). El streaming escribe primero a disco y luego lee en chunks de 200K filas con tipos eficientes.

---

## Anti-OOM: arquitectura df_cov + df_price_stats

El principal riesgo de RAM en `01_exploracion_productos.ipynb` no es la lectura en sí, sino mantener un DataFrame a nivel sucursal (producto × sucursal, ~50M filas) con columnas de enriquecimiento. La solución canónica es agregar inmediatamente.

### El patrón (cell-14)

```python
# ── 1. Merge con geografía SOLAMENTE (no con productos todavía) ───────────────
suc_geo = df_suc_maest[['id_comercio','id_bandera','id_sucursal','PROVINCIA','REGION']].copy()
df_suc_enr = df_suc.merge(suc_geo, on=['id_comercio','id_bandera','id_sucursal'], how='left')
del df_suc, suc_geo; gc.collect()

# ── 2. Normalizar provincia + nombre cadena (vectorizado) ─────────────────────
# ... (código de normalización) ...
# Soltar columnas que ya no se necesitan para reducir el pico de RAM
df_suc_enr.drop(columns=['sucursales_provincia','dias_con_precio','total_dias'],
                inplace=True, errors='ignore')

# ── 3. Estadísticas de precio ANTES de agregar (percentiles a nivel sucursal) ─
df_price_stats = df_suc_enr.groupby('id_producto', sort=False)['precio_promedio'] \
    .agg(precio_promedio='mean', precio_mediano='median').astype('float32').reset_index()
_pq = df_suc_enr.groupby('id_producto', sort=False)['precio_promedio'] \
    .quantile([0.25, 0.75]).unstack() \
    .rename(columns={0.25:'precio_p25', 0.75:'precio_p75'}).astype('float32').reset_index()
df_price_stats = df_price_stats.merge(_pq, on='id_producto', how='left')
del _pq

# ── 4. AGREGACIÓN CRÍTICA: 50M filas → 2M filas ────────────────────────────────
df_cov = (
    df_suc_enr
    .groupby(['id_producto','id_bandera','nombre_cadena','PROVINCIA_NOMBRE','REGION'],
             sort=False, dropna=False)
    .agg(n_sucursales=('id_sucursal','count'), pct_dias=('pct_dias','mean'),
         precio_promedio=('precio_promedio','mean'))
    .reset_index()
)
del df_suc_enr; gc.collect()   # ← LIBERACIÓN CRÍTICA — RAM: ~10 GB → ~600 MB

# ── 5. Merge con metadata de productos (barato: df_cov ya tiene ~2M filas) ────
df_cov = df_cov.merge(df_prod_uniq, on='id_producto', how='left')
```

### Perfil de memoria

| Frame | Filas | Columnas | RAM aprox. | Cuándo se libera |
|-------|-------|----------|------------|-----------------|
| `df_suc` (cargado desde parquet) | ~50M | 9 | ~5 GB | `del df_suc` en paso 1 |
| `df_suc_enr` (pico) | ~50M | ~10 | ~7 GB | `del df_suc_enr` después del groupby |
| `df_cov` (resultado) | ~2M | 13 | ~300 MB | `del df_cov` en cell-21 |
| `df_price_stats` | ~170K | 5 | ~5 MB | persiste hasta export |
| `df_cob` (cobertura producto) | ~170K | ~20 | ~20 MB | persiste hasta export |

> **Regla**: nunca mantener un frame a nivel sucursal (millones de filas) más tiempo del necesario. Agregar a nivel producto inmediatamente.

---

## Estructura real de categorías en el maestro SEPA

El maestro de productos (`Maestro de Productos Interno.xlsx`) organiza los productos en tres niveles: `rubro → categoria → subcategoria`. Los valores de `categoria` son **strings literales del maestro**, no keywords descriptivas del producto. Esto es crítico para configurar correctamente `GRUPOS_CANASTA`.

### Rubros y categorías observados (candidatos con cobertura máxima, abril 2026)

**Rubro: Frescos** (521 candidatos)

| categoria | n_productos |
|-----------|-------------|
| Lácteos | 279 |
| Fiambrería | 185 |
| Pastas y Tapas | 31 |
| Carnicería | 13 |
| Frutas y Verduras | 5 |

> **Trampa crítica**: los productos lácteos tienen `categoria='Lácteos'`, NO `categoria='leche'` o `categoria='queso'`. Las kw de `seleccionar_grupo()` deben coincidir con el valor literal del campo, no con el nombre genérico del producto.

**Categorías con mezcla de tipos (fuente de contaminación)**:

| categoria | Incluye |
|-----------|---------|
| `Fiambrería` | Fiambres + quesos untables + quesos crema |
| `Conservas` | Frutas en almíbar + carnes enlatadas (paté, picadillo) |

Ambas categorías son heterogéneas: agrupan productos de naturaleza distinta bajo el mismo valor. El filtrado por `excluir_kw` no puede resolverlo si opera solo sobre `categoria` — requiere filtrar también sobre `descripcion`.

### Regla para configurar kw en `GRUPOS_CANASTA`

```python
# MAL — busca keywords en descripcion/ingredientes, no en la columna categoria
kw=['leche','yogur','queso','crema','manteca']  # → 0 resultados para Lácteos

# BIEN — usa el valor literal que tiene la columna categoria en el maestro
kw=['lácteos','lacteos']  # → matchea categoria='Lácteos'
```

**Cómo encontrar los valores correctos**: consultar la hoja Candidatos del Excel de salida, columna `categoria`, filtrado por `rubro` de interés.

---

## Trampas conocidas en selección de grupos

### Substring matching en categorías

La función `seleccionar_grupo(df, rubros, kw, excluir_kw, max_n)` filtra por `kw` como substring sobre el nombre de categoría. Esto genera falsos positivos:

| Keyword | Falso positivo / Falso negativo |
|---------|--------------------------------|
| `'te'` | matchea 'Espumantes' (falso positivo) |
| `'crema'` | matchea 'Mayonesa Receta Casera con Crema' (falso positivo) |
| `'postre'` | matchea 'Repostería y Postres' (falso positivo) |
| `'conserva'` | matchea 'Conservas' (incluye carnes enlatadas además de frutas) |
| `'fiambre'` | matchea 'Fiambrería' (incluye quesos untables además de fiambres) |
| `'carne'` | **NO** matchea 'Carnicería' — `'carne' in 'Carnicería'` → `False` (falso negativo) |

### Categorías heterogéneas que requieren `excluir_subcat`

Algunas categorías del maestro SEPA agrupan productos de naturaleza distinta. El `excluir_kw` sobre `categoria` no puede distinguirlos — solo `excluir_subcat` (coincidencia exacta sobre `subcategoria`) los separa:

| categoria | Mezcla | excluir_subcat recomendado |
|-----------|--------|---------------------------|
| `Conservas` | Frutas en almíbar + carnes enlatadas (Patés, Picadillos) | `['Patés y Picadillos', 'Conservas de Pescado']` |
| `Fiambrería` | Fiambres + quesos untables/crema | `['Quesos Untables', 'Quesos Semiduros', 'Quesos Blandos', 'Quesos Duros', 'Quesos Rallados', 'Quesos Especiales']` |
| `Accesorios de Limpieza` | Implementos físicos (cabos, escobas) + accesorios legítimos (escobilla de baño) | `['Palas y Cabos', 'Escobas y Escobillones', 'Plumeros y Limpiavidrios']` |
| `Cuidado del Cabello` | Shampoo/acondicionador (higiene) + coloración/fijación (beauty/styling) | `['Coloración', 'Fijación']` |

**Regla**: siempre revisar el output de cada grupo y añadir `excluir_kw` cuando hay contaminación. Para categorías heterogéneas (`Conservas`, `Fiambrería`) puede ser necesario filtrar sobre la columna `descripcion` además de `categoria`.

### Firma actual de `seleccionar_grupo()`

```python
def seleccionar_grupo(df, rubros, keywords, excluir_kw, max_n, excluir_subcat=None):
    subset = df[df['rubro'].isin(rubros)].copy()
    if excluir_kw and len(subset) > 0:
        excl_mask = subset['categoria'].str.contains(
            '|'.join(excluir_kw), case=False, na=False)
        subset = subset[~excl_mask]
    if excluir_subcat and len(subset) > 0:
        subset = subset[~subset['subcategoria'].isin(excluir_subcat)]
    if keywords and len(subset) > 0:
        incl_mask = subset['categoria'].str.contains(
            '|'.join(keywords), case=False, na=False)
        subset = subset[incl_mask]
    return subset.sort_values('score_cobertura', ascending=False).head(max_n)
```

### Orden de aplicación

1. Filtrar por `rubro`
2. Excluir por `excluir_kw` (substring sobre `categoria` — nivel categoría)
3. Excluir por `excluir_subcat` (coincidencia exacta sobre `subcategoria` — nivel subcategoría, más preciso para categorías heterogéneas)
4. Incluir por `kw` (substring sobre `categoria`)
5. Top N por `score_cobertura`

**Sin fallback**: si el filtro de keywords deja 0 resultados, el grupo queda vacío (preferible a incluir productos incorrectos).

### `excluir_subcat` vs `excluir_kw`

`excluir_subcat` opera sobre la columna `subcategoria` con coincidencia exacta (`.isin()`), lo que permite descartar subcategorías específicas dentro de una categoría heterogénea sin afectar al resto.

```python
# Problema: categoria='Conservas' tiene Duraznos en almíbar Y Patés/Picadillos
# excluir_kw=['paté'] no funciona — busca 'paté' en 'Conservas' → False
# excluir_subcat=['Patés y Picadillos'] funciona — exacto sobre subcategoria
'excluir_subcat': ['Patés y Picadillos', 'Conservas de Pescado']
```

---

## Trampas con dtype category

> **Nota**: el pipeline actual (`df_cov`) usa strings planos, no dtype `category`, por lo que esta trampa ya no aplica al flujo principal. Se documenta por si se re-introduce `category` en futuras optimizaciones de RAM.

### La trampa: groupby sin `observed=True`

Sin `observed=True`, pandas genera **el producto cartesiano de todos los niveles definidos** en cada columna category, no solo los pares que realmente existen en los datos.

**Error real producido en este proyecto:**

```
Unable to allocate 1.33 EiB for array shape (384124754222853120,)
```

El shape astronómico es el producto cartesiano de los niveles de todas las columnas category incluidas en el groupby.

```python
# MAL — explota en RAM con columnas category
df.groupby(['nombre_cadena', 'REGION', 'rubro', 'categoria'])['precio_promedio'].mean()

# BIEN — solo agrupa por combinaciones que realmente existen
df.groupby(['nombre_cadena', 'REGION', 'rubro', 'categoria'], observed=True)['precio_promedio'].mean()
```

**Regla**: todo `groupby()` que incluya al menos una columna de dtype `category` DEBE llevar `observed=True`.

---

## Patrones técnicos del notebook 02 (gen_nb02.py)

### Caché parquet con hash de EANs + cantidades

El caché de la serie histórica se valida con un hash MD5 que incluye **tanto los EANs como las cantidades** de la canasta. Esto garantiza que si el economista cambia la composición (agrega un producto, lo elimina, o cambia su `cantidad`), el caché se invalida automáticamente y se recalcula la serie.

```python
# ❌ Solo EANs — no invalida si cambia cantidad de 4 a 3
_cache_key = hashlib.md5('|'.join(sorted(CANASTA.keys())).encode()).hexdigest()[:8]

# ✅ EANs + cantidades — invalida ante cualquier cambio en la canasta
_cache_key = hashlib.md5(
    '|'.join(f'{k}:{CANASTA[k][1]}' for k in sorted(CANASTA.keys())).encode()
).hexdigest()[:8]
```

El parquet se guarda en `output_canasta/_cache/hist_{hash}.parquet`. Para forzar recálculo: setear `USE_CACHE = False` en CELDA 1.

### Etiquetas de meses en español

Matplotlib usa el locale del sistema para formatear fechas. En Colab (Linux), `%b` produce "Jan", "Feb"... en inglés. Para obtener "ene", "feb"..., usar un formateador manual:

```python
_MESES_ES = {1:'ene',2:'feb',3:'mar',4:'abr',5:'may',6:'jun',
             7:'jul',8:'ago',9:'sep',10:'oct',11:'nov',12:'dic'}

def _fmt_mes_es(x, pos):
    try:
        ts = mdates.num2date(x)
        return f'{_MESES_ES[ts.month]}-{str(ts.year)[2:]}'
    except Exception:
        return ''

ax.xaxis.set_major_formatter(mticker.FuncFormatter(_fmt_mes_es))
```

No usar `mdates.DateFormatter('%b-%y')` — en Colab produce inglés.

### MES_INICIO_GRAFICO auto-adapta

Si el mes configurado en CELDA 1 no existe en la serie histórica (por ejemplo porque la canasta empieza en un mes posterior), el notebook cae automáticamente al primer mes disponible:

```python
_mg = MES_INICIO_GRAFICO
if _mg not in comparativa['mes'].values:
    _mg = comparativa['mes'].min()
    print(f'AVISO: MES_INICIO_GRAFICO {MES_INICIO_GRAFICO} no está en la serie → usando {_mg}')
```

### Nombre de la canasta: ICR

El nombre del índice en gráficos y visualizaciones es **"ICR"** (Índice de Consumo Representativo), no "Canasta SEPA". La variable `COLOR_CANASTA = '#0055A4'` (azul) se mantiene en todos los gráficos.

### Hoja Serie_precios en el Excel de análisis

El Excel `canasta_analisis_YYYY-MM.xlsx` tiene 5 hojas. La nueva hoja **`Serie_precios`** contiene el precio mediano nacional por producto por mes (serie histórica completa desde `MES_INICIO_HISTORICO`):

| Columna | Contenido |
|---------|-----------|
| `mes` | Período YYYY-MM |
| `id_producto` | EAN-13 con ceros iniciales |
| `descripcion` | Nombre del producto (primeros 50 chars) |
| `categoria` | Categoría de la canasta |
| `qty` | Cantidad mensual del producto en la canasta |
| `precio_mediano` | Precio mediano nacional (pesos) |
| `costo_item` | `precio_mediano × qty` |

Permite analizar la evolución individual de cada producto a lo largo del tiempo sin necesidad de reprocesar los ZIPs.

---

## Canasta referencia (otros notebooks)

Los notebooks de evolución temporal usan una **canasta fija de 30 EANs** para comparación temporal consistente. Esto es distinto al enfoque dinámico por cobertura de `01_exploracion_productos.ipynb`.

- **Abril 2026, canasta nacional ponderada**: **$322,566 ARS**
- **Ponderación**: Censo INDEC 2022 (45,892,285 habitantes, 24 jurisdicciones)
- **Rango sucursal**: $271,282 – $358,177
- **Sucursales válidas**: 2,371 (≥ 20 de 30 productos reportados)

---

## IPC INDEC

### Fuente: archivo local `IPC.xlsx` (nombre exacto, case-sensitive en Colab)

El notebook 02 lee el IPC desde un archivo Excel en la carpeta `carga/`. El nombre del archivo es **`IPC.xlsx`** (I mayúscula). En Colab (Linux), el filesystem de Drive es case-sensitive — `ipc.xlsx` no encontraría el archivo.

**Patrón de carga robusto (case-insensitive fallback)**:

```python
_ipc_candidatos = [SEPA_DIR / n for n in ('IPC.xlsx', 'ipc.xlsx', 'IPC.XLSX')]
IPC_PATH = next((p for p in _ipc_candidatos if p.exists()), SEPA_DIR / 'IPC.xlsx')
```

**Estructura real confirmada del archivo** (verificado con `IPC_primerasfilas.xlsx`, 2026-05-29):

| # | Columna | Tipo pandas | Contenido |
|---|---------|-------------|-----------|
| 0 | `date` | `datetime64[us]` | Primer día del mes (p.ej. `2017-01-01`) |
| 1 | `Nivel general` | `float64` | Índice IPC Nivel General |
| 2 | `Alimentos y bebidas no alcohólicas` | `float64` | IPC Alimentos y bebidas |
| 3–13 | 11 categorías más | `float64` | Salud, Transporte, Educación, etc. |

**Punto clave sobre el tipo de la columna `date`**:

Excel almacena las fechas internamente como números seriales. Aunque en la celda Excel se ven como `ene-17` (formato de celda personalizado), `pd.read_excel()` los convierte automáticamente a `datetime64`. Por eso **no se necesita parseo manual de `ene-2017`**. El notebook lo detecta con `pd.api.types.is_datetime64_any_dtype()` y usa directamente `.dt.strftime('%Y-%m')`.

Si por alguna razón el archivo tuviese las fechas guardadas como texto (caso infrecuente), el notebook cae al fallback que parsea `ene-2017` con un diccionario de meses español.

**Valores**: `float64` con punto decimal (ej. `101.5859`). No requieren conversión. El código mantiene `str.replace(',', '.')` por robustez ante versiones con coma decimal, pero no afecta a los valores ya numéricos.

**Cobertura**: datos disponibles desde enero 2017 hasta **marzo 2026** (mínimo). Actualización mensual con un mes de rezago aproximado.

### Fuente alternativa: API pública

```python
import requests

BASE_URL = 'https://apis.datos.gob.ar/series/api/series/'

def get_ipc(serie_id, start_date='2022-01-01'):
    params = {
        'ids': serie_id,
        'start_date': start_date,
        'limit': 1000,
        'format': 'json'
    }
    r = requests.get(BASE_URL, params=params)
    data = r.json()['data']
    return pd.DataFrame(data, columns=['fecha', 'valor'])

# Series útiles:
# 148.3_INIVELGENERAL_DICI_M_26 — IPC General
# 148.3_IALIMENTOSY_DICI_M_26   — IPC Alimentos y bebidas no alcohólicas
# 103.1_I2N_DICI_M_19           — CBA (Canasta Básica Alimentaria)
```

Datos disponibles hasta **marzo 2026**. Actualización mensual. El notebook 02 usa el archivo local (más confiable en Colab que una llamada a API).

---

## Patrones técnicos del notebook 07 (gen_nb07.py) — 2026-09-03

### Lectura SEMANAL + colapso de frescos a TIPO (fix de RAM)
La serie semanal relee todos los ZIPs conservando el **día** (`precio_YYYYMMDD` → fecha → semana).
El universo de frescos por nombre es de **~10.600 EANs de balanza**; arrastrarlos por
(sucursal × EAN × semana) sobre 30+ meses agota la RAM (OOM). **Solución (CELDA 7)**: la función
`_colapsar(_df)` mapea, **en la lectura mensual**, cada EAN fresco a su **TIPO** y normaliza a
$/kg o $/docena (mediana de variantes por sucursal-semana). Así el panel pasa de ~10.800 items a
~255 (**~40× menos filas**). El esquema cacheado es `item/price` (`sem_{hash}_v5.parquet`); el
crudo por-EAN del último mes se guarda aparte (`datos_ult_raw`) para los diagnósticos por variante.

> La clave del caché incluye el universo de EANs, el día de cierre de semana y `FRESCO_OUTLIER_K`.
> Cambiar cualquiera de los tres invalida el caché y fuerza una relectura completa (~50-60 min).

### Filtro de outliers intra-tipo (frescos)
Dentro de cada **sucursal-semana**, antes de tomar la mediana de las variantes de un tipo, se
descartan las que caen fuera de `[mediana/K, mediana×K]` con `K = FRESCO_OUTLIER_K` (2.5).
Es la defensa contra el problema real de normalizar $/kg sobre EANs de balanza: un EAN cargado
como "1 kg" cuyo precio en realidad es por unidad o por media horma dispara el $/kg del tipo.

### Selección de frescos por CATEGORÍA (fix de precios inflados)
La selección solo por regex de nombre colaba procesados con el nombre de la fruta/verdura
(jugo en polvo "banana", sazonador "cebolla", ñoquis de "papa", comida de perro sabor "pollo"),
de pocos gramos → `precio/grams×1000` disparaba el $/kg. **Solución (CELDA 4-5)**: se lee
`categoria` del maestro y los candidatos frescos exigen **categoría de fresco real**
(`Frutas y Verduras`, `Carnicería`, `Fiambrería`, `Panificados`, `Pescados y Mariscos`, `Huevos`)
**o** categoría vacía (balanza SEPA-only que no está en el maestro interno), más un piso de
gramaje por tipo (`gmin`, default 250 g; quesos y fiambres 500 g). Mapa `rubro → categorías` en
`_CAT_FRESCO_CFG`.

### Semana que cierra el jueves
La semana **no** es ISO: es una ventana de 7 días que **cierra el jueves** (viernes→jueves),
etiquetada por la **fecha de cierre** (`2026-09-03`). Así el informe que se arma el viernes usa
la última semana completa. Se configura con `DIA_CIERRE_SEMANA` (3=jueves, 4=viernes).

Una semana que cruza dos meses se procesa en dos archivos mensuales. Para no duplicar, cada
semana se asigna a su mes **"dueño"**: el del punto medio de la ventana (cierre − 3 días,
`_mes_de_semana`). Es el análogo al criterio del jueves ISO.

> Ojo: nb02 y nb06 siguen usando **semana ISO** (`%G-S%V`). Solo nb07 usa el cierre en jueves.

### Región
`REGION_PROV` mapea provincia → una de 5 regiones (Centro/Pampeana, NOA, NEA, Cuyo, Patagonia).
`costo_suc` gana la columna `region`; se agregan `region_dict` (snapshot) y `serie_region_dict` (semanal).

## Patrón técnico del notebook 02 — motor `datos_econometria`
Mismo enfoque de lectura conservando el día, pero **sin frescos** (solo empaquetados: EANs de las
canastas de `Selección` + `PRODUCTOS_ECONOMETRIA`). Agrega por (sucursal, EAN, semana/mes) →
mediana (`precio_med`) y media recortada (`precio_prom`) de los días; imputa faltantes con la
referencia nacional del período; agrega a nacional (ponderado población) / provincia / cadena con
`valor_mediana` y `valor_promedio`. Caché `econ_{hash}.parquet` por mes cerrado. Salida tidy/long.
