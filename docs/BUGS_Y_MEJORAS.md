# Bugs Pendientes y Mejoras

Última actualización: 2026-05-27 (tercera ejecución — revisión Excel exhaustiva)

---

## 🔴 Bugs críticos (pendientes de fix)

> ✅ Todos los bugs críticos están resueltos. Ver sección "Resueltos" más abajo.

---

## 🔴 Bugs críticos (resueltos — revisión Excel tercera ejecución)

### BUG-12: "Cabo Metálico" y otros implementos físicos en Limpieza del hogar ✅ Resuelto — este commit

**Archivo**: `notebooks/exploracion_productos.ipynb`, cell-23 (`GRUPOS_CANASTA`)
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

### BUG-13: Tintura de cabello y protector térmico en Higiene y cuidado personal ✅ Resuelto — este commit

**Archivo**: `notebooks/exploracion_productos.ipynb`, cell-23 (`GRUPOS_CANASTA`)
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

**Archivo**: `notebooks/exploracion_productos.ipynb`, cell-27 (export Excel)
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

**Archivo**: `notebooks/exploracion_productos.ipynb`, cell-23 (`GRUPOS_CANASTA`)
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

**Archivo**: `notebooks/exploracion_productos.ipynb`, cell-23 (`GRUPOS_CANASTA`)
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

**Archivo**: `notebooks/exploracion_productos.ipynb`, cell-23 (`GRUPOS_CANASTA`)
**Síntoma**: el grupo incluía Paté Bocatti de Panceta Ahumada y Picadillo de Carne Swift Picante.
**Causa**: ambos productos tienen `categoria='Conservas'` en el maestro — igual que los duraznos en almíbar, peras, etc. La kw `'conserva'` matcheaba todos sin distinción. Los `excluir_kw` operan sobre la misma columna `categoria` y no pueden distinguir dentro del mismo valor.

**Fix aplicado**: nuevo parámetro `excluir_subcat` en `seleccionar_grupo()` que filtra por la columna `subcategoria` (nivel más granular):
```python
excluir_subcat=['Patés y Picadillos', 'Conservas de Pescado']
```

**Resultado verificado (segunda ejecución)**: grupo Azúcar/dulces sin carnes enlatadas.

---

### BUG-8: Carnes y fiambres incluye quesos del rubro Fiambrería ✅ Resuelto — commit 3c66c3c

**Archivo**: `notebooks/exploracion_productos.ipynb`, cell-23 (`GRUPOS_CANASTA`)
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

**Archivo**: `notebooks/exploracion_productos.ipynb`, cell-23 (`GRUPOS_CANASTA`)
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

**Archivo**: `notebooks/exploracion_productos.ipynb`, cell-7 (`cargar_sepa()`)
**Síntoma**: todos los precios del Excel de salida son 100x demasiado bajos. Aceite girasol aparece ~$57 en lugar de ~$5,750.
**Causa**: la función divide precios por 100 asumiendo centavos, pero los datos semestral 2026A (y probablemente 2025B+) ya vienen en pesos.
**Evidencia**: `analisis_SEPA_evolucion_AMBA.ipynb` procesa los mismos archivos y confirma FACTOR=1 ("Mediana de referencia: 1411.00 → Factor: 1").
**Fix**: reemplazar la división fija `/100` por autodetección de factor via producto de referencia (ver `SEPA_TECNICO.md`).
**Impacto en filtros**: NINGUNO — los filtros son por cobertura, no por precio umbral. La canasta seleccionada es correcta; solo los precios reportados están mal.

---

### BUG-2: `id_bandera` reportado como "cadena" cuando son grupos corporativos

**Archivo**: `notebooks/exploracion_productos.ipynb`, celdas de enriquecimiento y cobertura
**Síntoma**: el notebook reporta "5 cadenas activas" cuando en realidad son 16 cadenas comerciales.
**Causa**: `id_bandera` (valores 1-6) es el grupo corporativo, no el banner comercial. Cencosud opera Vea+Disco+Jumbo (3 id_bandera distintos dentro del mismo id_comercio=9).
**Fix**: añadir columna `nombre_cadena` usando el diccionario `(id_comercio, id_bandera)` disponible en `SEPA_TECNICO.md`.
**Impacto en score**: el `MIN_CADENAS` dinámico filtra por grupos corporativos (correcto para asegurar representatividad por grupo), pero el número reportado en el Excel es confuso.

---

## 🟡 Bugs menores (afectan la exactitud de la selección)

### BUG-3: Grupos de canasta con productos incorrectos

**Archivo**: `notebooks/exploracion_productos.ipynb`, celda de `GRUPOS_CANASTA`
**Síntoma**:
- **Lácteos** incluye: Mayonesa Hellmanns, Alfajor Chocoarroz, Azúcar Azucel
- **Carnes y fiambres** incluye: Dulce de Batata (×2), Queso Untable
**Causa**: keyword `'crema'` en Lácteos matchea "Mayonesa Receta Casera con Crema" (substring en nombre de categoría).
**Fix**: revisar `excluir_kw` de cada grupo problemático. Para Lácteos, excluir categorías que contengan 'mayonesa', 'alfajor', 'azúcar'. Para Carnes, revisar el rubro de los productos contaminantes en el maestro.

---

### BUG-4: "San juan" con j minúscula

**Archivo**: `notebooks/exploracion_productos.ipynb`, celda de normalización de provincias
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

### MEJORA-4: Canasta imputada para comparación provincial

**Patrón de**: `analisis_SEPA_evolucion_AMBA.ipynb`
**Descripción**: cuando una sucursal no tiene precio para algún producto de la canasta, imputar con la mediana nacional de ese producto. Esto permite calcular una canasta "completa" en todas las sucursales y comparar precios entre provincias de forma justa.

```python
# Para cada EAN de la canasta, calcular mediana nacional
medianas_nacionales = canasta_df.groupby('id_producto')['precio_mediano'].median()

# En sucursales sin precio para ese EAN, usar la mediana
canasta_sucursal['precio_imputado'] = canasta_sucursal.apply(
    lambda r: r['precio'] if pd.notna(r['precio'])
              else medianas_nacionales.get(r['id_producto'], np.nan),
    axis=1
)
```

---

### MEJORA-5: Visualización geográfica con Folium

**Patrón de**: `analisis_SEPA_evolucion_AMBA.ipynb` y `python-dataviz-geo` skill
**Descripción**: mapa interactivo HTML con un punto por sucursal, coloreado por precio de canasta. Requiere coordenadas lat/lon (disponibles en el maestro de sucursales si tiene columnas de geolocalizacion, o cruzar con base externa).

---

## 🔴 Bugs críticos (resueltos)

### BUG-5: OOM persistente — df_enr demasiado grande para Colab

**Archivo**: `notebooks/exploracion_productos.ipynb`, celda de enriquecimiento y subsiguientes
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
| BUG-13: Tintura/Protector en Higiene | ✅ Resuelto — este commit | 🟡 Media |
| BUG-12: Cabo Metálico en Limpieza | ✅ Resuelto — este commit | 🟡 Media |
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
| MEJORA-1: Parquet cache | ✅ Implementado — commit e23bff5 | 🟡 Media |
| MEJORA-3: Nombres cadenas output | ✅ Implementado — commit e23bff5 | 🟢 Baja |
| MEJORA-2: Deduplicación de variantes | ⏳ Pendiente | 🟢 Baja |
| MEJORA-4: Canasta imputada | ⏳ Pendiente | 🟢 Baja |
| MEJORA-5: Mapa Folium | ⏳ Pendiente | 🟢 Baja |
