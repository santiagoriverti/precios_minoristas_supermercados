# Bugs Pendientes y Mejoras

Última actualización: 2026-08-21 — doble análisis media/mediana, fix LaTeX, Notebook 06

---

## 🔴 Bugs críticos (pendientes de fix)

> ✅ Todos los bugs críticos están resueltos. Ver sección "Resueltos" más abajo.

---

## 🟢 Cambios y fixes 2026-09

### 🟢 Notebook 07 — Canastas alternativas (Popular/Media/Ejecutiva) semanales + frescos (nuevo, 2026-09-01)

Herramienta nueva (`gen_nb07.py` → `07_evolucion_canastas_alternativas.ipynb`, 15 celdas). Análisis tipo nb02 pero **semanal**, con **3 canastas** socioeconómicas y **frescos** (carne/frutas/verduras/huevos), desagregado por rubro con drill-down y vs IPC. Ver README ("Canastas alternativas") y `METODOLOGIA.md` §8.

**Validado** end-to-end con dataset SEPA sintético (las 15 celdas compilan; frescos por tipo capturados y normalizados a $/kg y $/docena; rubro Carne desagregado; vs IPC; Excel de 27 hojas). Se corrigió `matplotlib.cm.get_cmap` → `plt.get_cmap` (removido en mpl 3.9, rompería en Colab). Generador con **raw strings** `r'''...'''` (ver `SEPA_TECNICO.md`).

**Mejoras/limitaciones abiertas (para afinar con datos reales)**:
- **Cantidades de frescos**: default razonable (canasta-básica, escala por estrato) y **editable** en `TIPOS_FRESCOS` (CELDA 1). Alinear mejor a las ponderaciones del IPC con la hoja `Cobertura_frescos` del primer run.
- **Reglas de frescos (`inc`/`exc`)**: curadas por nombre; pueden dejar entrar/salir variantes. La CELDA 13 imprime cobertura por tipo para refinar; revisar especialmente **Carne picada** (cobertura baja: los cortes al peso a veces no se publican con código).
- **Requiere `maestro_sepa_completo.csv.gz` en Drive** (lo genera el Script 03). Sin él, los frescos de nicho por cadena quedan sub-representados (el notebook avisa).
- **Mapas coropléticos/folium NO clonados** de nb02 (se pueden agregar después).
- **Un solo ítem empaquetado de baja comparabilidad** detectado al poblar: Postre Serenito (2 cadenas, 5 provincias) — candidato a reemplazo.

---

## 🟢 Cambios y fixes 2026-08

### ✅ Fix — Encabezado LaTeX de tablas de canasta con `\\` duplicado (2026-08-21)

**Archivo**: `notebooks/gen_nb02.py` → CELDA 13.

**Síntoma**: las `tabla_canasta_*.tex` salían con el encabezado (`\shortstack` y el terminador
de fila) en `\\\\` (doble), lo que genera filas/renglones vacíos y **rompe el render en
Overleaf**. Las tablas de producto (nb05) ya estaban bien. Era el bug histórico "CELDA 13 header
`\\` duplicado" que se arrastraba desde el raw-string original.

**Fix**: el header se reescribió como **f-string** (mismo patrón que nb05), produciendo `\\` simple.
Verificado en el `.tex` generado. Las filas de datos y la fila Promedio ya eran f-strings correctos.

### ✅ Feature — Doble análisis MEDIANA + PROMEDIO por duplicado (2026-08-21)

nb02 y nb05 generan **todo por duplicado**: análisis mediana (nombres base) y promedio
(sufijo `_prom`, con outliers fuera `[mediana/4, mediana×4]`). Además el precio por sucursal se
calcula sobre **todos los días del mes** (antes: solo el primer día). Detalle en `METODOLOGIA.md`
§4 ("Doble análisis") y en `.claude/memory.md`.

> ⚠️ **No es un bug, es un cambio de criterio**: los **niveles medianos** del cuadro de julio 2026
> en adelante **no son comparables 1:1** con informes viejos calculados con el método del primer día.

### 🟢 Notebook 06 — Brecha celíaca (nuevo)

Herramienta nueva (`gen_nb06.py`). Ver `docs/BRECHA_CELIACA.md`. Mejoras/limitaciones abiertas:
- **Cobertura de los representativos sin-TACC**: la plantilla se curó por marca mainstream, no por
  la métrica de cobertura del `canasta_representativa`. Revisar con la hoja `Detalle_producto` del
  primer run y reemplazar EANs de baja presencia.
- **Departamento**: falta un shapefile departamental (hoy: provincia + localidad).
- **Tipos ambiguos**: galletitas saladas (arroz vs trigo) y harina/premezcla (sustitución) — la
  decisión de incluirlos es del investigador (ver caveats en `BRECHA_CELIACA.md` §6.1).

---

## 🟠 Bug resuelto (2026-06-24)

### BUG-23: La serie histórica y los gráficos 1/2/3 no incluían el mes en curso

**Archivo**: `notebooks/gen_nb02.py` → CELDA 9 (y `02_evolucion_canasta_representativa.ipynb` regenerado).

**Síntoma**: con junio 2026 cargado, los cuadros provinciales/rankings/barrios mostraban junio (se calculan directo del archivo del mes), pero los **Gráficos 1 (índices), 2 (variaciones) y 3 (ranking canastas)** y los acumulados/variaciones del Excel terminaban en **mayo**. La serie histórica imprimía `2024-01 -> 2026-05`.

**Causa**: el caché de la serie (`hist_union_<hash>.parquet`) se identificaba **solo por la unión de EANs** de las canastas. Al agregar un mes nuevo, el set de EANs no cambia → mismo hash → se cargaba el caché viejo (construido hasta mayo) sin releer los meses nuevos. Agravante: el código original cacheaba **todos** los meses leídos, incluido el mes en curso; como ese mes crece día a día, quedaba "congelado" en la cantidad de días que tenía al cachearse.

**Fix**: CELDA 9 reescrita con dos niveles:
1. **Meses cerrados** (todos menos el último disponible) → se cachean y se leen incrementalmente: solo se procesan los meses que faltan en el caché.
2. **Mes en curso** (el último disponible) → se **relee SIEMPRE fresco** y nunca se cachea, así sus promedios usan los días efectivamente cargados (ej. junio con 23 días).

El caché viejo sigue siendo válido (se reutiliza para los meses cerrados), por lo que la primera corrida tras el fix es rápida: solo relee el mes en curso. Al cerrar el mes (cuando aparece el siguiente), pasa a "cerrado" y se incorpora al caché.

**Validado**: lógica de control testeada en 4 escenarios (primera corrida con mes nuevo, re-corrida mismo mes con más días, rollover de mes, sin caché). Solo cambió la CELDA 9 del notebook.

---

## 🔴 Bugs críticos (resueltos — 2026-06-01)

### EAN malformados en canastas ENGHo v2 → corregidos en v3

**Archivo**: `canastas_argentina_2026_v3.txt`
**Síntoma**: 4 EANs con menos de 13 dígitos no matcheaban en SEPA → precio imputado en lugar de real.
**Causa**: EANs truncados (faltaban ceros iniciales).
**Fix**: agregar ceros iniciales hasta 13 dígitos. La normalización `lstrip('0')` produce el mismo ean_norm → mismo producto, sin impacto en caché.

| EAN v2 | EAN v3 | Producto |
|--------|--------|---------|
| `78924468` | `0000078924468` | Dove Roll-On 50 Ml (Vulnerable) |
| `77903792` | `0000077903792` | Alfajor Terrabusi 70 Gr (Popular) |
| `70942003551` | `0070942003551` | Cepillo Gum Trolls 2 Un (Medio-Alto) |
| `99176369226` | `0099176369226` | Cepillo Colgate Triple 3+2 Un (Medio-Alto) |

---

## 🔴 Bugs críticos (resueltos — notebook 02, segunda ejecución 2026-05-29)

### BUG-19: `MIN_PRODUCTOS_PROPIOS >= N_CANASTA` → canasta_geo_filtros vacío ✅ Resuelto — commit e979ae2

**Archivo**: `notebooks/gen_nb02.py`, CELDA 3
**Síntoma**: Con una canasta de pocos productos (ej. 12 verduras frescas), el output de CELDA 8 mostraba `Provincias con datos: 0` y `Promedio (ponderado): nan`. Las celdas siguientes (14, 15, 16, 17) crasheaban por DataFrames vacíos.
**Causa**: `MIN_PRODUCTOS_PROPIOS = 15` (config en CELDA 1) era mayor que `N_CANASTA = 12`. Ninguna sucursal puede tener 15 productos de una canasta de 12 → todas se filtran → `canasta_geo_filtros` vacío.
**Fix aplicado** (CELDA 3, después de definir N_CANASTA):
```python
if MIN_PRODUCTOS_PROPIOS >= N_CANASTA:
    MIN_PRODUCTOS_PROPIOS = max(1, N_CANASTA // 2)
    print(f'AVISO: MIN_PRODUCTOS_PROPIOS ajustado a {MIN_PRODUCTOS_PROPIOS} '
          f'(canasta tiene solo {N_CANASTA} productos)')
```
**Comportamiento**: Para ICR (51 prod.): `15 >= 51` → False → no cambia. Para canasta pequeña (12 prod.): `15 >= 12` → True → ajusta a 6.
**Regla general**: Siempre verificar que `MIN_PRODUCTOS_PROPIOS < N_CANASTA`. El safeguard lo hace automáticamente.

---

### BUG-18: `IndexError` en CELDA 11/12 cuando la serie histórica está vacía ✅ Resuelto — commit 6289ab8

**Archivo**: `notebooks/gen_nb02.py`, CELDA 11 y 12
**Síntoma**: Al usar productos nuevos o con EANs PLU (códigos de balanza, empiezan con 27.../28...) que no están en el SEPA histórico, CELDA 11 crasheaba con `IndexError: single positional indexer is out-of-bounds` en `comparativa['ipc_general'].dropna().iloc[0]`. CELDA 12 crasheaba con similares errores al intentar graficar `df_g` vacío.
**Causa**: Los EANs con prefijo 27.../28... son PLU codes generados por balanzas en góndola — no tienen un código GS1 fijo y no aparecen en el SEPA histórico. `serie_nacional_valida` queda con 0 filas → `comparativa` vacío → `.iloc[0]` falla.
**Fix aplicado**:
- CELDA 11: guarda `_serie_vacia = len(serie_nacional_valida) == 0`. Si True → imprime aviso, crea DataFrames vacíos con las columnas correctas (`comparativa`, `df_g`). Si False → ejecuta el código original sin cambios.
- CELDA 12: envuelve toda la lógica de gráficos en `if len(df_g) == 0: print(aviso) / else: # código original`. Inicializa `out1 = out2 = None` para que CELDA 19 (export Excel) no crashee.
**Sin efecto sobre ICR**: `len(serie_nacional_valida) = 28` → `_serie_vacia = False` → código original, sin cambios.

---

### BUG-17: SyntaxError en gen_nb02.py — docstring triple-quote cierra el cell_code ✅ Resuelto — commit 7c3fe29

**Archivo**: `notebooks/gen_nb02.py`, CELDA 7
**Síntoma**: `python notebooks/gen_nb02.py` fallaba con `SyntaxError: invalid syntax. Perhaps you forgot a comma?` apuntando al inicio de CELDA 7.
**Causa**: La función `_geocodif()` usaba un docstring con triple comillas dobles `"""..."""`. Como el código de la celda está contenido dentro de un string `"""\..."""`, las comillas del docstring cerraban prematuramente el string externo, dejando el resto del código como sintaxis inválida.
**Fix aplicado**: cambiar el docstring a comentario de línea:
```python
# ANTES (cierra el string externo):
def _geocodif(lat, lon):
    """Primera provincia cuyo bbox contiene (lat, lon)."""

# DESPUÉS (sin conflicto):
def _geocodif(lat, lon):
    # Primera provincia cuyo bbox contiene (lat, lon)
```
**Regla general**: dentro de `cell_code("""\...""")`, NUNCA usar triple comillas dobles en el código interno (docstrings, strings multilínea). Usar comillas simples o comentarios de línea.

---

### BUG-16: Sucursales San Juan con coords en Jujuy — descartadas en lugar de reclasificadas ✅ Resuelto — commit 7c3fe29

**Archivo**: `notebooks/gen_nb02.py`, CELDA 7
**Síntoma**: La corrección inicial (BUG-15) eliminaba las sucursales con provincia inconsistente, perdiendo datos válidos. El usuario reportó que prefería conservarlas reclasificándolas.
**Causa**: Enfoque de filtrado en lugar de corrección: `canasta_geo = canasta_geo[~_mask_bad]` descarta filas.
**Fix aplicado**: reclasificación completa usando bounding boxes para las 24 provincias. Para cada sucursal con provincia inconsistente, busca en qué provincia caen sus coordenadas y la reasigna:
```python
_PROV_BBOX = {
    'CABA': (-34.72,-34.52,-58.54,-58.33),
    'Tucumán': (-28.0,-26.0,-66.5,-64.5),
    'Jujuy': (-24.5,-21.5,-67.5,-63.5),
    ... # 24 provincias
}
for _idx, _row in canasta_geo.iterrows():
    # Si coords fuera del bbox de la provincia etiquetada → buscar la correcta
    _nueva = _geocodif(_lat, _lon)
    if _nueva and _nueva != _p:
        canasta_geo.at[_idx, 'PROVINCIA_NORM'] = _nueva
```
**Sin pérdida de datos**: la sucursal se conserva con la provincia correcta según coordenadas.

---

### BUG-15: San Juan no aparece en mapa coroplético; filtro Folium muestra sucursales en ubicación incorrecta ✅ Resuelto — commit 2026-05-29

**Archivo**: `notebooks/gen_nb02.py`, CELDA 4 (`PROV_NORM`)
**Síntoma**: La provincia de San Juan aparecía en gris (sin datos) en el mapa coroplético. En el mapa Folium, al filtrar por "San Juan" se mostraban sucursales que geográficamente parecían estar en Jujuy.
**Causa**: El maestro de sucursales almacena la provincia de San Juan como `"San juan"` (con 'j' minúscula). El dict `PROV_NORM` tenía la entrada `'San Juan':'San Juan'` pero NO tenía `'San juan':'San Juan'`. Como la clave no existía, `.fillna(canasta_geo['PROVINCIA'])` conservaba el string original `"San juan"`. El GeoJSON usa `"San Juan"` (mayúscula), por lo que el match `can_prov.get('San Juan')` encontraba `None` → se pintaba gris.
**Fix aplicado**:
```python
# PROV_NORM — agregadas variantes de capitalización:
'San Juan':'San Juan','San juan':'San Juan','SAN JUAN':'San Juan',
```
**Regla general**: el maestro de sucursales puede tener inconsistencias de capitalización en los nombres de provincia. Para cada provincia con caracteres ambiguos, registrar todas las variantes conocidas en `PROV_NORM`.

---

## 🔴 Bugs críticos (resueltos — notebook 02)

### BUG-14: `ipc.xlsx` no encontrado — nombre real es `IPC.xlsx` (case-sensitive en Colab) ✅ Resuelto — commit 0acf852+1

**Archivo**: `notebooks/02_evolucion_canasta_representativa.ipynb`, celda de config (CELDA 2)
**Síntoma**: al ejecutar la celda de verificación de paths, el output mostraba `ipc.xlsx: NO ENCONTRADO` aunque el archivo estaba presente en la carpeta `carga/`.
**Causa**: el archivo se llama `IPC.xlsx` (I mayúscula). En Colab, el filesystem de Google Drive es **case-sensitive**: `IPC.xlsx` ≠ `ipc.xlsx`. El notebook buscaba `ipc.xlsx` en minúsculas.
**Contexto**: Windows no distingue mayúsculas/minúsculas en nombres de archivo, por lo que durante el desarrollo local el bug era invisible. Solo se manifiesta al ejecutar en Colab (Linux).
**Fix aplicado** (gen_nb02.py, celda de config):
```python
# Buscar IPC.xlsx / ipc.xlsx — case-insensitive fallback para Colab
_ipc_candidatos = [SEPA_DIR / n for n in ('IPC.xlsx', 'ipc.xlsx', 'IPC.XLSX')]
_ipc_encontrado = next((p for p in _ipc_candidatos if p.exists()), None)
IPC_PATH = _ipc_encontrado if _ipc_encontrado else SEPA_DIR / 'IPC.xlsx'
```
**Regla general**: en archivos de Drive accedidos desde Colab, siempre probar variantes de capitalización o documentar el nombre exacto del archivo. El nombre canónico es **`IPC.xlsx`** (mayúsculas).

---

## 🔴 Bugs críticos (resueltos — revisión Excel tercera ejecución)

### BUG-12: "Cabo Metálico" y otros implementos físicos en Limpieza del hogar ✅ Resuelto — commit 5f9f3c4

**Archivo**: `notebooks/01_exploracion_productos.ipynb`, cell-23 (`GRUPOS_CANASTA`)
**Síntoma**: el grupo Limpieza del hogar incluía "Cabo Metálico Glow 1 Un" y potencialmente escobas y plumeros — implementos físicos que no son productos de limpieza para seguimiento de precios.
**Causa**: `categoria='Accesorios de Limpieza'` agrupa tanto productos de limpieza (escobillas de inodoro) como implementos físicos (cabos, escobas, plumeros). El filtro sin `excluir_subcat` los toma todos.
**Evidencia**:
```
Cabo Metálico Glow 1 Un | subcategoria=Palas y Cabos | score=0.975
Escoba sin Cabo Virulana | subcategoria=Escobas y Escobillones | score=0.934
```
**Fix aplicado**:
```python
'excluir_subcat': ['Palas y Cabos', 'Escobas y Escobillones', 'Plumeros y Limpiavidrios']
```
**Resultado esperado**: Cabo Metálico reemplazado por un producto de limpieza real (lavandina, detergente, desinfectante).

---

### BUG-13: Tintura de cabello y protector térmico en Higiene y cuidado personal ✅ Resuelto — commit c61416e

**Archivo**: `notebooks/01_exploracion_productos.ipynb`, cell-23 (`GRUPOS_CANASTA`)
**Síntoma**: "Coloración en Crema N°3 Issue" (tintura) y "Protector Térmico sin Fijacion Spray Roby" (styling) ocupaban los puestos 3 y 4 del grupo, desplazando a desodorantes.
**Causa**: `subcategoria='Coloración'` y `subcategoria='Fijación'` tienen alta cobertura nacional (score ~0.988) pero son productos de beauty/styling, no higiene básica.
**Evidencia — grupo antes del fix**:
```
1. Jabón Plusbelle        (0.994)  ✅ higiene
2. Crema Dermaglós        (0.993)  ✅ cuidado facial
3. Protector Térmico Roby (0.989)  ❌ fijación de cabello
4. Tintura Issue          (0.988)  ❌ coloración
5. Alcohol Bialcohol      (0.987)  ✅ higiene
6. Crema Corporal St Ives (0.982)  ✅ cuidado corporal
```
**Fix aplicado**:
```python
'excluir_subcat': ['Coloración', 'Fijación']
```
**Resultado esperado — grupo tras el fix**:
```
1. Jabón Plusbelle           (0.994)  ✅
2. Crema Dermaglós           (0.993)  ✅
3. Alcohol Bialcohol         (0.987)  ✅
4. Crema Corporal St Ives    (0.982)  ✅
5. Desodorante Dove Mujer    (0.958)  ✅
6. Desodorante Dove Hombre   (0.954)  ✅
```

---

## 🔴 Bugs críticos (resueltos — revisión Excel segunda ejecución)

### BUG-10: `id_producto` exportado como entero — EANs con ceros iniciales se truncan ✅ Resuelto — commit f67de87

**Archivo**: `notebooks/01_exploracion_productos.ipynb`, cell-27 (export Excel)
**Síntoma**: EANs de menos de 13 dígitos (ej. código interno `78933354`) se exportan sin ceros iniciales. Al abrir el Excel, el EAN-13 debería ser `0000078933354`, pero se ve `78933354`. Afecta a ~93 productos en la hoja Candidatos.
**Causa**: `id_producto` se almacena como int64 en algún punto del pipeline. Al escribir en Excel mediante openpyxl, los enteros se formatean sin relleno.
**Fix aplicado** (cell-27, antes de construir el ExcelWriter):
```python
# Preservar EANs con ceros iniciales
canasta_export['id_producto']    = canasta_export['id_producto'].astype(str).str.zfill(13)
candidatos_export['id_producto'] = candidatos_export['id_producto'].astype(str).str.zfill(13)
```
**Impacto**: sin el fix, cualquier notebook consumidor que intente hacer merge por EAN-13 perdería 93 productos. El `.str.zfill(13)` no altera EANs de 13 dígitos (solo añade ceros iniciales a los más cortos).

---

### BUG-11: `'carne'` no es substring de `'Carnicería'` — productos de ese rubro no se incluían ✅ Resuelto — commit f67de87

**Archivo**: `notebooks/01_exploracion_productos.ipynb`, cell-23 (`GRUPOS_CANASTA`)
**Síntoma**: los 13 candidatos de `categoria='Carnicería'` (Leberwurst Paladini score=0.97, Salamín Bocatti score=0.93, etc.) nunca aparecían en el grupo Carnes y fiambres, aunque eran los de mayor score.
**Causa**: la kw `'carne'` busca como substring en el valor de `categoria`. El valor literal es `'Carnicería'` — cuyas primeras 5 letras son `'carni'`, no `'carne'`. Python `'carne' in 'Carnicería'` → `False`.
**Fix aplicado** (cell-23, kw del grupo Carnes y fiambres):
```python
# ANTES — no matcheaba 'Carnicería'
kw=['fiambre','embutido','carne','salchicha','pollo','atún','atun']

# DESPUÉS — añadido 'carnicería' y 'carniceria' explícitamente
kw=['fiambre','embutido','carne','carnicería','carniceria','salchicha','pollo','atún','atun']
```
**Impacto**: sin este fix, los embutidos curados de alta cobertura (Leberwurst, Salamín) quedan fuera de la canasta.

---

## 🔴 Bugs críticos (resueltos)

### BUG-6: Lácteos = 0 productos en la canasta ✅ Resuelto — commit 3c66c3c

**Archivo**: `notebooks/01_exploracion_productos.ipynb`, cell-23 (`GRUPOS_CANASTA`)
**Síntoma**: el grupo Lácteos produce 0 productos — aparece vacío en el Excel de salida.
**Causa**: las kw anteriores eran `['leche','yogur','queso','crema','manteca']`, que se buscan como substring en la columna `categoria` del maestro. Sin embargo, en el maestro SEPA, los productos lácteos del rubro Frescos tienen `categoria = 'Lácteos'` (string literal) — ninguna de las kw matcheaba ese valor.

**Evidencia (análisis post-ejecución, primera ejecución abril 2026)**:
```
Candidatos en Frescos: 521
Frescos con categoria='Lácteos':  279  ← estaban ahí, no se encontraban
Frescos con 'leche' en categoria:   0
Frescos con 'yogur' en categoria:   0
Frescos con 'queso' en categoria:   0
```

**Fix aplicado**:
```python
# En GRUPOS_CANASTA, grupo 'Lácteos':
# ANTES (no matcheaba nada en el maestro SEPA)
kw=['leche','yogur','queso','crema','manteca']

# DESPUÉS (coincide con el valor real de la columna categoria)
kw=['lácteos','lacteos']
rubros=['Frescos']
```

**Resultado verificado (segunda ejecución)**: 8 productos Lácteos correctos en la canasta.

---

### BUG-7: Azúcar, dulces y conservas contamina con carnes enlatadas ✅ Resuelto — commit 3c66c3c

**Archivo**: `notebooks/01_exploracion_productos.ipynb`, cell-23 (`GRUPOS_CANASTA`)
**Síntoma**: el grupo incluía Paté Bocatti de Panceta Ahumada y Picadillo de Carne Swift Picante.
**Causa**: ambos productos tienen `categoria='Conservas'` en el maestro — igual que los duraznos en almíbar, peras, etc. La kw `'conserva'` matcheaba todos sin distinción. Los `excluir_kw` operan sobre la misma columna `categoria` y no pueden distinguir dentro del mismo valor.

**Fix aplicado**: nuevo parámetro `excluir_subcat` en `seleccionar_grupo()` que filtra por la columna `subcategoria` (nivel más granular):
```python
excluir_subcat=['Patés y Picadillos', 'Conservas de Pescado']
```

**Resultado verificado (segunda ejecución)**: grupo Azúcar/dulces sin carnes enlatadas.

---

### BUG-8: Carnes y fiambres incluye quesos del rubro Fiambrería ✅ Resuelto — commit 3c66c3c

**Archivo**: `notebooks/01_exploracion_productos.ipynb`, cell-23 (`GRUPOS_CANASTA`)
**Síntoma**: Queso Untable Neufchafel, Queso Crema Casancrem, Queso Crema La Serenísima y otros quesos aparecían en el grupo Carnes y fiambres.
**Causa**: la kw `'fiambre'` matcheaba `categoria='Fiambrería'`, que en el maestro SEPA incluye tanto fiambres reales como quesos untables y cremas de queso. Los `excluir_kw` anteriores buscaban `'queso untable'` en la columna `categoria`, pero el valor literal es `'Fiambrería'` — no tenían efecto.

**Fix aplicado**: nuevo parámetro `excluir_subcat` en `seleccionar_grupo()`:
```python
excluir_subcat=['Quesos Untables', 'Quesos Semiduros', 'Quesos Rallados',
                'Quesos Blandos', 'Quesos Duros', 'Quesos Especiales', 'Dulces']
```

**Resultado verificado (segunda ejecución)**: los 6 productos Carnes son fiambres legítimos (Leberwurst, Salamín, Paleta, Salame, Pepperoni, Bondiola).

**Nota**: estos quesos tampoco aparecen en el grupo Lácteos (su `categoria='Fiambrería'`, no `'Lácteos'`). Son candidatos para un grupo Quesos propio en el futuro.

---

### BUG-9: Bebidas no alcohólicas incompletas (falta yerba, té, café) ✅ Resuelto — commit 3c66c3c

**Archivo**: `notebooks/01_exploracion_productos.ipynb`, cell-23 (`GRUPOS_CANASTA`)
**Síntoma**: el grupo Bebidas no alcohólicas solo contenía jugos y una bebida energizante. Faltaban yerba mate, té, café — productos básicos de la canasta argentina.
**Causa**: `rubros=['Bebidas']` únicamente. Las infusiones (yerba, té, café) viven en `rubro='Almacén'`, `categoria='Infusiones'` en el maestro SEPA.

**Fix aplicado**:
```python
'rubros': ['Bebidas', 'Almacén'],   # Almacén contiene Infusiones (yerba/té/café)
'kw': ['agua', 'gaseosa', 'jugo', 'saborizada', 'infusion', 'bebida herbal'],
# 'infusion' como substring matchea 'Infusiones'
```

**Resultado verificado (segunda ejecución)**: Yerba Liebig, Café Dolca, Té Inti Grey aparecen en el grupo.

---

## 🔴 Bugs críticos (resueltos)

### BUG-1: División /100 incorrecta en precios

**Archivo**: `notebooks/01_exploracion_productos.ipynb`, cell-7 (`cargar_sepa()`)
**Síntoma**: todos los precios del Excel de salida son 100x demasiado bajos. Aceite girasol aparece ~$57 en lugar de ~$5,750.
**Causa**: la función divide precios por 100 asumiendo centavos, pero los datos semestral 2026A (y probablemente 2025B+) ya vienen en pesos.
**Evidencia**: `analisis_SEPA_evolucion_AMBA.ipynb` procesa los mismos archivos y confirma FACTOR=1 ("Mediana de referencia: 1411.00 → Factor: 1").
**Fix**: reemplazar la división fija `/100` por autodetección de factor via producto de referencia (ver `SEPA_TECNICO.md`).
**Impacto en filtros**: NINGUNO — los filtros son por cobertura, no por precio umbral. La canasta seleccionada es correcta; solo los precios reportados están mal.

---

### BUG-2: `id_bandera` reportado como "cadena" cuando son grupos corporativos

**Archivo**: `notebooks/01_exploracion_productos.ipynb`, celdas de enriquecimiento y cobertura
**Síntoma**: el notebook reporta "5 cadenas activas" cuando en realidad son 16 cadenas comerciales.
**Causa**: `id_bandera` (valores 1-6) es el grupo corporativo, no el banner comercial. Cencosud opera Vea+Disco+Jumbo (3 id_bandera distintos dentro del mismo id_comercio=9).
**Fix**: añadir columna `nombre_cadena` usando el diccionario `(id_comercio, id_bandera)` disponible en `SEPA_TECNICO.md`.
**Impacto en score**: el `MIN_CADENAS` dinámico filtra por grupos corporativos (correcto para asegurar representatividad por grupo), pero el número reportado en el Excel es confuso.

---

## 🟡 Bugs menores (afectan la exactitud de la selección)

### BUG-3: Grupos de canasta con productos incorrectos

**Archivo**: `notebooks/01_exploracion_productos.ipynb`, celda de `GRUPOS_CANASTA`
**Síntoma**:
- **Lácteos** incluye: Mayonesa Hellmanns, Alfajor Chocoarroz, Azúcar Azucel
- **Carnes y fiambres** incluye: Dulce de Batata (×2), Queso Untable
**Causa**: keyword `'crema'` en Lácteos matchea "Mayonesa Receta Casera con Crema" (substring en nombre de categoría).
**Fix**: revisar `excluir_kw` de cada grupo problemático. Para Lácteos, excluir categorías que contengan 'mayonesa', 'alfajor', 'azúcar'. Para Carnes, revisar el rubro de los productos contaminantes en el maestro.

---

### BUG-4: "San juan" con j minúscula

**Archivo**: `notebooks/01_exploracion_productos.ipynb`, celda de normalización de provincias
**Síntoma**: `maestro_sucursales_completo.xlsx` tiene la provincia "San juan" con j minúscula.
**Causa**: dato sucio en el maestro; la normalización actual solo hace strip de "Provincia de " y reemplaza CABA.
**Fix**: añadir `.str.title()` después de las normalizaciones existentes, o un replace específico `'San juan' → 'San Juan'`.

---

## 🟢 Mejoras (opcionales, aumentan calidad)

### MEJORA-1: Parquet cache para sobrevivir crashes Colab

**Patrón de**: `analisis_precios_SEPA.ipynb`
**Descripción**: guardar el DataFrame después de cada paso costoso (carga SEPA, enriquecimiento, cobertura) como `.parquet` comprimido con snappy. Si el kernel crashea, retomar desde el último parquet en lugar de reprocesar todo.

```python
# Guardar
df.to_parquet(OUTPUT_DIR / 'df_enr.parquet', compression='snappy', index=False)

# Retomar (al inicio de la celda)
if (OUTPUT_DIR / 'df_enr.parquet').exists():
    df_enr = pd.read_parquet(OUTPUT_DIR / 'df_enr.parquet')
else:
    # ... procesar normalmente
```

---

### MEJORA-2: Deduplicación de variantes (concepto)

**Patrón de**: `analisis_precios_SEPA_2.ipynb`
**Descripción**: muchos productos son variantes de tamaño del mismo ítem (fideos 400g, fideos 500g, fideos 1kg). La función `extraer_concepto()` extrae las N palabras más significativas (sin marca ni packaging) para agrupar variantes y quedarse con la de mayor cobertura.

```python
TOKENS_A_REMOVER = {'g', 'kg', 'ml', 'l', 'lt', 'cc', 'un', 'unid',
                    'x', 'de', 'con', 'sin', 'por', 'para',
                    '100', '200', '250', '300', '400', '500', '1000', ...}

def extraer_concepto(desc_norm, marca, n_palabras=3):
    tokens = [t for t in desc_norm.split()
              if t not in TOKENS_A_REMOVER
              and t not in marca.lower().split()
              and not t.isdigit()]
    return ' '.join(tokens[:n_palabras])
```

Resultado esperado: ~10% reducción de la canasta de candidatos (4,713 → ~4,200 conceptos únicos).

---

### MEJORA-3: Nombres de cadenas en el output

**Patrón de**: `analisis_SEPA_evolucion_AMBA.ipynb`
**Descripción**: añadir una columna `nombre_cadena` al DataFrame enriquecido para que el output Excel muestre nombres legibles en lugar de `id_bandera`.
**Implementación**: ver diccionario `NOMBRES_CADENAS_COMPUESTAS` + `NOMBRES_CADENAS_SIMPLES` en `SEPA_TECNICO.md`.

---

### MEJORA-4: Canasta imputada para comparación provincial ✅ Implementado en notebook 02 — 2026-05-28

**Implementado en**: `notebooks/02_evolucion_canasta_representativa.ipynb`, CELDA 7 (`calcular_canasta_completa()`)
**Descripción**: para cada sucursal, si un producto de la canasta no tiene precio propio, se usa la mediana nacional de ese producto como imputación. Solo se reporta la sucursal si tiene al menos `MIN_PRODUCTOS_PROPIOS=15` productos propios.

```python
def calcular_canasta_completa(grupo):
    locales = dict(zip(grupo['ean_norm'], grupo['precio']))
    total = 0; propios = 0; detalle = []
    for ean_norm, (nombre, qty, cat) in CANASTA.items():
        if ean_norm in locales:
            precio = locales[ean_norm]; es_propio = True; propios += 1
        else:
            precio = precio_prom_nac.get(ean_norm, 0); es_propio = False
        subtotal = precio * qty
        total += subtotal
        detalle.append((nombre, cat, qty, precio, subtotal, es_propio))
    return pd.Series({'canasta_total': total, 'productos_propios': propios,
                      'detalle_productos': detalle})
```

---

### MEJORA-5: Visualización geográfica con Folium ✅ Implementado en notebook 02 — 2026-05-28

**Implementado en**: `notebooks/02_evolucion_canasta_representativa.ipynb`, CELDA 18
**Descripción**: mapa Folium interactivo con un `CircleMarker` por sucursal (radio proporcional al costo de canasta), coloreado por cadena comercial. FeatureGroups independientes por cadena + panel JS de filtros por provincia y tipo (hiper/super/express). Las coordenadas vienen del maestro de sucursales.

---

### MEJORA-6: Hoja "Selección" en Excel — fuente para notebook de canasta elegida ✅ Implementado — 2026-05-28

**Archivo**: `notebooks/01_exploracion_productos.ipynb`, cell-27 (export Excel)
**Descripción**: el Excel de salida ahora tiene una **tercera hoja "Selección"** que contiene todos los candidatos (~3,650 productos) ordenados por `rubro → categoría → score_cobertura` descendente, con:
- **Columna `cantidad`** (en amarillo destacado): vacía, para que el economista indique cuántas unidades incluir por producto
- **Auto-filter** habilitado para filtrar por rubro/categoría
- Header con freeze y estilo azul marino idéntico al del resto del Excel
- Formatos numéricos aplicados (score, precios, porcentajes)

**Estructura de `_COLS_SEL`**: `['periodo', 'cantidad'] + COLS_CANDIDATOS - 'periodo'`

**Propósito**: esta hoja es la **fuente de datos del próximo notebook** (`canasta_elegida_analisis.ipynb` — aún no creado), que leerá las cantidades completadas por el economista y calculará los totales de la canasta elegida, su comparación con el IPC, etc.

---

## 🔴 Bugs críticos (resueltos)

### BUG-5: OOM persistente — df_enr demasiado grande para Colab

**Archivo**: `notebooks/01_exploracion_productos.ipynb`, celda de enriquecimiento y subsiguientes
**Síntoma**: "Tu sesión falló porque se usó toda la RAM disponible" incluso después de los fixes de apply() y observed=True.
**Causa**: `df_enr` (producto × sucursal, ~50M filas × 20 columnas, ~10 GB) se mantenía vivo desde la celda de enriquecimiento hasta los heatmaps (7 celdas después). Los groupby sobre ese frame en cells 15, 16 y 18 multiplicaban el uso de RAM.
**Fix**: Rediseño arquitectónico anti-OOM:
- Agregar `df_suc_enr` inmediatamente a `df_cov` (producto × cadena × provincia, ~2M filas) y `df_price_stats` (producto, ~170K filas)
- `del df_suc_enr; gc.collect()` en cuanto termina la agregación → RAM pasa de ~10 GB a ~600 MB
- Todos los cálculos posteriores operan sobre los frames pequeños
**Impacto**: Soluciona el crash de RAM definitivamente sin cambiar los resultados.

---

## Estado de fixes

| Bug/Mejora | Estado | Prioridad |
|---|---|---|
| BUG-14: IPC.xlsx case-sensitive en Colab | ✅ Resuelto — 2026-05-28 | 🔴 Alta |
| BUG-13: Tintura/Protector en Higiene | ✅ Resuelto — commit c61416e | 🟡 Media |
| BUG-12: Cabo Metálico en Limpieza | ✅ Resuelto — commit 5f9f3c4 | 🟡 Media |
| BUG-11: 'carne' ≠ substring 'Carnicería' | ✅ Resuelto — commit f67de87 | 🟡 Media |
| BUG-10: id_producto int64 pierde ceros iniciales | ✅ Resuelto — commit f67de87 | 🔴 Alta |
| BUG-9: Bebidas incompletas (yerba/té/café) | ✅ Resuelto — commit 3c66c3c | 🟡 Media |
| BUG-8: Carnes incluye quesos fiambrería | ✅ Resuelto — commit 3c66c3c | 🟡 Media |
| BUG-7: Azúcar contamina con carnes lata | ✅ Resuelto — commit 3c66c3c | 🔴 Alta |
| BUG-6: Lácteos vacío (kw incorrectas) | ✅ Resuelto — commit 3c66c3c | 🔴 Alta |
| BUG-5: OOM df_enr ~10GB | ✅ Resuelto — commit fd5e014 | 🔴 Alta |
| BUG-4: "San juan" minúscula | ✅ Resuelto — commit e23bff5 | 🟢 Baja |
| BUG-3: Grupos contaminados (originales) | ✅ Resuelto — commit e23bff5 | 🟡 Media |
| BUG-2: Nombres cadenas | ✅ Resuelto — commit e23bff5 | 🟡 Media |
| BUG-1: Factor precio /100 | ✅ Resuelto — commit e23bff5 | 🔴 Alta |
| MEJORA-6: Hoja "Selección" con columna cantidad | ✅ Implementado — 2026-05-28 | 🔴 Alta |
| MEJORA-5: Mapa Folium interactivo | ✅ Implementado nb02 — 2026-05-28 | 🟡 Media |
| MEJORA-4: Canasta imputada por sucursal | ✅ Implementado nb02 — 2026-05-28 | 🟡 Media |
| MEJORA-3: Nombres cadenas output | ✅ Implementado — commit e23bff5 | 🟢 Baja |
| MEJORA-1: Parquet cache | ✅ Implementado — commit e23bff5 | 🟡 Media |
| MEJORA-2: Deduplicación de variantes | ⏳ Pendiente | 🟢 Baja |
