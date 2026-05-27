# SEPA — Referencia Técnica

Última actualización: 2026-05-27

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

### Autodetección (patrón de `analisis_SEPA_evolucion.ipynb`)

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

print(f"Mediana de referencia: {mediana_ref:.2f} → Factor: {FACTOR_PRECIO}")
```

**Confirmación para abril 2026**: `analisis_SEPA_evolucion_AMBA.ipynb` procesa los mismos archivos y reporta "Mediana de referencia: 1411.00 → Factor: 1".

> ⚠️ **Bug activo en `exploracion_productos.ipynb`**: cell-7 divide /100 sin autodetección. Para 2026A todos los precios del Excel de salida son 100x demasiado bajos.

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

def get_nombre_cadena(id_comercio, id_bandera):
    clave = (str(id_comercio), str(id_bandera))
    if clave in NOMBRES_CADENAS_COMPUESTAS:
        return NOMBRES_CADENAS_COMPUESTAS[clave]
    return NOMBRES_CADENAS_SIMPLES.get(str(id_comercio), f'Comercio {id_comercio}')
```

### Implicación para el score de cobertura

Con los datos semestral, `MIN_CADENAS = total_cadenas` filtra por grupos corporativos (5-6 valores), no por banners (16). Un producto puede estar en "Carrefour" (id_bandera=1) pero no en "Carrefour Express" (id_bandera=3), y el filtro no lo detecta. Esto es una limitación estructural del formato semestral.

---

## Maestros de referencia

| Archivo | Descripción | Join key |
|---------|-------------|----------|
| `Maestro de Productos Interno.xlsx` | ~176K productos, rubro/categoría/subcategoría | `producto_sepa_id` = `id_producto` |
| `maestro_sucursales_completo.xlsx` | 3,611 sucursales con cadena, provincia, región | `id_comercio` + `id_bandera` + `id_sucursal` |
| `maestro-provincias.xlsx` | ISO 3166-2 → nombre legible | `sucursales_provincia` |

### Normalización de provincias (obligatoria)

```python
df['PROVINCIA_NOMBRE'] = (
    df['PROVINCIA_NOMBRE']
    .str.replace(r'^Provincia de ', '', regex=True)
    .str.replace('Ciudad Autónoma de Buenos Aires', 'CABA', regex=False)
    .str.title()   # ← fix "San juan" → "San Juan" y similares
)
```

> ⚠️ **Bug activo**: el `.str.title()` (o fix equivalente) no está aplicado actualmente. "San juan" aparece con j minúscula en el maestro de sucursales.

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

def cargar_sepa(zip_path, filename, factor_precio=1):
    """
    Carga un archivo SEPA semestral de forma eficiente.
    
    factor_precio: 1 para datos 2025B+ (ya en pesos), 100 para datos anteriores (en centavos).
    Usar autodetección si no se conoce el factor.
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
            prices = (chunk[price_cols]
                      .replace('NA', np.nan)
                      .astype('float32')
                      / factor_precio)   # ← aplicar factor correcto
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

## Trampas conocidas en selección de grupos

### Substring matching en categorías

La función `seleccionar_grupo(df, rubros, kw, excluir_kw, max_n)` filtra por `kw` como substring sobre el nombre de categoría. Esto genera falsos positivos:

| Keyword | Falso positivo |
|---------|----------------|
| `'te'` | matchea 'Espumantes' |
| `'crema'` | matchea 'Mayonesa Receta Casera con Crema' |
| `'postre'` | matchea 'Repostería y Postres' |

**Regla**: siempre revisar el output de cada grupo y añadir `excluir_kw` cuando hay contaminación.

### Orden de aplicación en `seleccionar_grupo()`

1. Filtrar por `rubro`
2. Excluir categorías en `excluir_kw` (previene falsos positivos por substring)
3. Incluir categorías con `kw`
4. Top N por `score_cobertura`

---

## Canasta referencia (otros notebooks)

Los notebooks de evolución temporal usan una **canasta fija de 30 EANs** para comparación temporal consistente. Esto es distinto al enfoque dinámico por cobertura de `exploracion_productos.ipynb`.

- **Abril 2026, canasta nacional ponderada**: **$322,566 ARS**
- **Ponderación**: Censo INDEC 2022 (45,892,285 habitantes, 24 jurisdicciones)
- **Rango sucursal**: $271,282 – $358,177
- **Sucursales válidas**: 2,371 (≥ 20 de 30 productos reportados)

---

## Trampas con dtype category

### Por qué usamos dtype category

Las columnas de baja cardinalidad se convierten a `category` para reducir uso de RAM:

| Columna | Cardinalidad típica | Motivo |
|---------|--------------------|----|
| `nombre_cadena` | 5–16 valores | cadenas comerciales |
| `REGION` | 6 valores | AMBA, Pampeana, Patagonia, Noroeste, Cuyo, Noreste |
| `PROVINCIA_NOMBRE` | 24 valores | jurisdicciones del país |
| `rubro` | ~20 valores | categoría de nivel alto del maestro |
| `categoria` | ~100 valores | categoría de nivel medio del maestro |

Con `category`, pandas almacena internamente un índice entero por fila y una tabla de strings únicos, en lugar de repetir el string completo en cada fila. Para un DataFrame de varios millones de filas esto puede reducir el uso de RAM a la décima parte.

### La trampa: groupby sin `observed=True`

Sin `observed=True`, pandas genera **el producto cartesiano de todos los niveles definidos** en cada columna category, no solo los pares que realmente existen en los datos.

**Error real producido en este proyecto:**

```
Unable to allocate 1.33 EiB for array shape (384124754222853120,)
```

El shape astronómico `(384124754222853120,)` es el resultado de multiplicar la cantidad de niveles de todas las columnas category incluidas en el groupby (por ejemplo `nombre_cadena × REGION × rubro × categoria`), elevado a la dimensión del resultado esperado.

**Cómo reproducir el error:**

```python
# MAL — explota en RAM con columnas category
df.groupby(['nombre_cadena', 'REGION', 'rubro', 'categoria'])['precio_promedio'].mean()

# BIEN — solo agrupa por combinaciones que realmente existen
df.groupby(['nombre_cadena', 'REGION', 'rubro', 'categoria'], observed=True)['precio_promedio'].mean()
```

### Regla obligatoria

> **Todo `groupby()` que incluya al menos una columna de dtype `category` DEBE llevar `observed=True`.**

Esta regla aplica sin excepción en `df_enr` (el DataFrame enriquecido principal del pipeline), cuyas columnas category son: `nombre_cadena`, `REGION`, `PROVINCIA_NOMBRE`, `rubro`, `categoria`.

La ausencia de `observed=True` no genera advertencia ni error inmediato — el proceso arranca, reserva memoria silenciosamente y muere con `MemoryError` o `Unable to allocate` mucho después de iniciar.

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
