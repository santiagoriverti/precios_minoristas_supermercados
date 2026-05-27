# SEPA — Referencia Técnica

Última actualización: 2026-05-27 (post-ejecución abril 2026)

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
- `id_producto`: EAN/GTIN de 13 dígitos, siempre como string

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

### Autodetección implementada en `exploracion_productos.ipynb`

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

El principal riesgo de RAM en `exploracion_productos.ipynb` no es la lectura en sí, sino mantener un DataFrame a nivel sucursal (producto × sucursal, ~50M filas) con columnas de enriquecimiento. La solución canónica es agregar inmediatamente.

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

| Keyword | Falso positivo |
|---------|----------------|
| `'te'` | matchea 'Espumantes' |
| `'crema'` | matchea 'Mayonesa Receta Casera con Crema' |
| `'postre'` | matchea 'Repostería y Postres' |
| `'conserva'` | matchea 'Conservas' (incluye carnes enlatadas además de frutas) |
| `'fiambre'` | matchea 'Fiambrería' (incluye quesos untables además de fiambres) |

**Regla**: siempre revisar el output de cada grupo y añadir `excluir_kw` cuando hay contaminación. Para categorías heterogéneas (`Conservas`, `Fiambrería`) puede ser necesario filtrar sobre la columna `descripcion` además de `categoria`.

### Orden de aplicación en `seleccionar_grupo()`

1. Filtrar por `rubro`
2. Excluir categorías en `excluir_kw` (previene falsos positivos por substring)
3. Incluir categorías con `kw`
4. Top N por `score_cobertura`

**Sin fallback**: si el filtro de keywords deja 0 resultados, el grupo queda vacío (preferible a incluir productos incorrectos).

### Limitación actual: `excluir_kw` solo opera sobre `categoria`

El parámetro `excluir_kw` actual busca como substring en la columna `categoria`. No puede distinguir productos dentro de la misma categoría (e.g., Paté vs. Duraznos, ambos `categoria='Conservas'`). Para este caso se necesita ampliar `seleccionar_grupo()` con un parámetro `excluir_desc_kw` que filtre sobre la columna `descripcion`.

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

## Canasta referencia (otros notebooks)

Los notebooks de evolución temporal usan una **canasta fija de 30 EANs** para comparación temporal consistente. Esto es distinto al enfoque dinámico por cobertura de `exploracion_productos.ipynb`.

- **Abril 2026, canasta nacional ponderada**: **$322,566 ARS**
- **Ponderación**: Censo INDEC 2022 (45,892,285 habitantes, 24 jurisdicciones)
- **Rango sucursal**: $271,282 – $358,177
- **Sucursales válidas**: 2,371 (≥ 20 de 30 productos reportados)

---

## IPC INDEC

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

Datos disponibles hasta **marzo 2026**. Actualización mensual.
