# precios_minoristas_supermercados

GitHub: santiagoriverti/precios_minoristas_supermercados
Local: C:\Users\sriverti\Desktop\INECO\Repositorios\precios_minoristas_supermercados
Autor: Santiago Riverti — investigador independiente

## Estado actual [2026-06-03] — PRODUCCIÓN ✅

### Notebook 01 — `01_exploracion_productos.ipynb` (commit 566f033)
- Selecciona ~65 productos con mayor score de cobertura nacional
- Output: `canasta_representativa_YYYY-MM.xlsx` con 4 hojas: Canasta, Candidatos, Selección (~25k prods), Productos unicos (~75k)
- Hoja Selección: **6 columnas de cantidad** (`cantidad_01`..`cantidad_06`) para definir hasta 6 canastas
- Todos los bugs resueltos (BUG-1..BUG-14)

### Notebook 02 — `02_evolucion_canasta_representativa.ipynb` (commit 05e48ba)
- **21 celdas de código**. Lee columnas `cantidad_01`..`cantidad_06`, procesa canastas activas simultáneamente
- **Cache único**: `hist_union_{hash}.parquet` para la unión de todos los EANs. Hash solo por EANs (no cantidades). Cambiar qty no invalida cache; agregar/quitar EANs sí.
- Cache actual: `hist_union_feead60a.parquet` (257 EANs, 28 meses 2024-01→2026-04)
- Generado desde `notebooks/gen_nb02.py` (script fuente)

## Las 6 canastas — Resultados reales abril 2026

| # | Nombre | Slot | Productos | Costo nacional | Referencia |
|---|--------|------|-----------|----------------|------------|
| 1 | Vulnerable | cantidad_01 | 44 | **$252.982** | Q1, Engel ~36% |
| 2 | Popular | cantidad_02 | 59 | **$451.672** | Q2, Engel ~28% |
| 3 | Media | cantidad_03 | 72 | **$634.923** | Q3-Q4, Engel ~22% |
| 4 | Media Alta | cantidad_04 | 74 | **$879.459** | Q5, Engel ~15% |
| 5 | Celíaca Media | cantidad_05 | 74 | **$691.836** | +9% vs Media (prima celíaca) |
| 6 | Vegana Básica | cantidad_06 | 51 | **$427.033** | −5.5% vs Popular |

Ordenamiento: Vulnerable $252k → Vegana $427k → Popular $451k → Media $634k → Celíaca $691k → Media Alta $879k

Archivo fuente de canastas: `canastas_argentina_2026_v3.txt` (EAN+cantidad por canasta)

## ⚠️ Carga MANUAL de cantidades — flujo mensual [2026-06-24]

**Las cantidades que definen las 6 canastas se cargan A MANO.** El nb01 genera
`canasta_representativa_YYYY-MM.xlsx` con las columnas `cantidad_01..06` (hoja
`Selección`) **VACÍAS**. nb01 NO las autocompleta ni las hereda de meses previos.

**Flujo mensual del usuario:**
1. Ejecutar **nb01** → Excel con `cantidad_01..06` vacías.
2. **Cargar las cantidades manualmente** en la hoja `Selección` (matchea por `id_producto`/EAN).
3. Ejecutar **nb02** → lee las cantidades y calcula las canastas.

**Implicancia crítica:** re-correr nb01 (o borrar el Excel) **borra las cantidades**.
No re-correr nb01 salvo necesidad; si se hace, hay que recargar las cantidades antes del nb02.

**Backup/recuperación de las definiciones:** la composición (EAN × cantidad por canasta)
es recuperable desde la hoja `Serie_precios` del `canasta_analisis_YYYY-MM.xlsx` (output
del nb02): columnas `canasta_id` (= nombre de columna `cantidad_NN`), `id_producto`, `qty`.
Backup generado de junio 2026: `Downloads/canastas_definicion_2026-06_BACKUP.xlsx`
(261 EANs × `cantidad_01..06`; Vulnerable 45 · Popular 60 · Media 72 · Media Alta 76 ·
Celíaca 74 · Vegana 51).

## Repositorios GitHub

| Repo | Descripción | URL |
|------|-------------|-----|
| `precios_minoristas_supermercados` | Pipeline completo, notebooks, datos | github.com/santiagoriverti/precios_minoristas_supermercados |
| `mapa_precios_minoristas` | Solo index.html del mapa (GitHub Pages) | santiagoriverti.github.io/mapa_precios_minoristas/ |

El repo `mapa_precios_minoristas` tiene README y .gitignore propios. El mapa a subir debe ser el generado por CELDA 17 del nb02 (~3-5 MB).

## Archivos requeridos en Drive (`carga/`)
- ZIPs SEPA: 2024A.zip, 2024B.zip, 2025A.zip, 2025B.zip, 2026A.zip
- `IPC.xlsx` (columna `date` = datetime64, columnas IPC = float64 con punto decimal)
- `ar.json` (GeoJSON 24 provincias)
- `output_canasta/canasta_representativa_YYYY-MM.xlsx` (del nb01, con cantidades completadas)

## Outputs del nb02

- `canasta_analisis_YYYY-MM.xlsx` — **6 hojas**: Evolucion_IPC, Prov_{short}, Ranking_{short}, Sucs_{short}, Serie_precios, **Valores_Documento** (nueva: todos los valores del LaTeX listos para copiar)
- `mapa_interactivo_{MES}.html` — popup simple (cadena + precio + cobertura), sin tabla de productos. JSON ~300KB. Funciona en GitHub Pages. (~3-5 MB total)
- `indices_canasta_vs_ipc_{MES}.png`, `variaciones_canasta_vs_ipc_{MES}.png`, `ranking_canastas_{MES}.png`
- `mapa_canasta_{short}_{mes}.png`, `ranking_cadenas_{tipo}_{MES}_{short}.png` (por canasta)
- `trazabilidad_candidatos_{YYYY-MM}.xlsx` (CELDA 21, ~20 min, escanea histórico)

## Historial de commits relevantes

| Commit | Descripción |
|--------|-------------|
| `05e48ba` | CELDA 20: exportar valores para documento técnico |
| `b4727ad` | .gitignore agregado al repo |
| `a2cd296` | README actualizado con resultados reales abril 2026 |
| `c4585c5` | Popup simple + filtro cadena — mapa liviano para GitHub Pages |
| `acda017` | Fix SyntaxError lazy popup (BUG-20) |

## Reglas técnicas críticas

**gen_nb02.py — BUG-17**: nunca usar `"""docstrings"""` dentro de `cell_code("""\...""")`. Usar `# comentarios`.

**gen_nb02.py — Escaping CSS en cell_code**: `\'` dentro de `"""\..."""` produce `'` (Python consume el backslash). Para CSS inline en f-strings de CELDA 17: usar **CSS classes + template literals JS** (backtick). NUNCA `style='...'` dentro de Python f-string single-quoted. Ver BUG-20 (SyntaxError lazy popup).

**PROV_NORM**: incluir variantes exactas del maestro. Conocida: `'San juan': 'San Juan'` (j minúscula).

**Reclasificación por coordenadas (CELDA 7)**: `_PROV_BBOX` dict con 24 provincias. Branches con provincia incorrecta → reclasificar por lat/lon, no descartar.

**IPC.xlsx**: columna `date` es `datetime64` (Excel serial). No parsear como texto. Fast path: `pd.api.types.is_datetime64_any_dtype()`.

**Lazy popup Folium**: datos en `<script type="application/json" id="_pd_json">`. JS lee con `JSON.parse(document.getElementById('_pd_json').textContent)`. Evento `popupopen` → `_bPop(key, col_id)` → `e.popup.update()`.

**EANs**: leer como str, `.str.lstrip('0')` para ean_norm, `.str.zfill(13)` para exportar a Excel.

**MIN_PRODUCTOS_PROPIOS**: auto-ajusta a `N_CANASTA // 2` si la canasta tiene pocos productos (evita 0 sucursales válidas).

**Series vacías (PLU codes 27.../28...)**: CELDA 11/12 tienen guards para `serie_nacional_valida` vacía. PLU codes no están en el SEPA histórico.

**Gráfico 2 barras**: ancho = `max(3, int(22/n_series))` días; figura = `max(20, n*2+10)` pulgadas; ticks cada 2 meses si n>5.

**Cache invalida cuando**: cambian los EANs activos (unión de canastas). No invalida cuando cambian solo cantidades.

**Mapa Folium — tamaño**: Popup sin tabla de productos → JSON ~300KB (era 60MB con detalle). Panel de filtros: Canasta + Cadena + Provincia. `apl()` filtra por `className` con AND de provincia y cadena. `setTimeout(1200)` antes de `_initEvt()` evita `mp.on is not a function` en GitHub Pages (race condition con archivo grande).

**Dos valores para canasta Media**: $634.923 (CELDA 8: mediana provincial ponderada por población) vs $639.259 (CELDA 11: mediana nacional por EAN). El documento usa $634.923. La var. mensual +2,84% viene de CELDA 11.

**Patrón geográfico Vulnerable**: para la canasta Vulnerable las más baratas son San Juan y Mendoza (Cuyo), NO Formosa/NEA. Para las otras 5 canastas sí aplica el patrón NEA más barato.

## Canastas especiales — Notas metodológicas

**Celíaca Media** (+9% sobre Media):
- Productos sin TACC disponibles en SEPA con buena cobertura: pasta Blue Patna (score 0.927), galletitas Grandiet/Chalitas, Nesquik sinTACC, Caldo Verdura Knorr, Almidón Maizena
- Sin cerveza de malta (cebada = gluten) → sidra Saenz Briones 1888
- Sin avena (controvertida para celíacos)
- Nesquik sinTACC tiene trazabilidad 82.1% (por debajo del umbral general de 90%)

**Vegana Básica** (−5.5% vs Popular):
- Proteína: porotos × 6 + garbanzos × 4 + Not Chicken × 4
- Bebida vegetal: Ades Soja × 12
- Sin lácteos, carnes, huevos, pescado
- Pasta de trigo incluida (sin huevo = vegana)
- Caldo de Verdura Knorr (no caldo de carne)

## Bugs resueltos (resumen)

BUG-1..14: todos resueltos en nb01 (commit c61416e)
BUG-15: `'San juan'` → `'San Juan'` en PROV_NORM
BUG-16: reclasificación por bbox en lugar de descarte
BUG-17: triple-quote dentro de cell_code
BUG-18: CELDA 11/12 guard para serie histórica vacía
BUG-19: MIN_PRODUCTOS_PROPIOS auto-ajuste
BUG-20: SyntaxError lazy popup — `\'` en `"""\..."""` = `'` (sin escape). Fix: CSS classes + template literals JS. Commit acda017.
BUG-21: JSON popup 60MB → popup simple sin detalle de productos (c4585c5).
BUG-22: `mp.on is not a function` en GitHub Pages → `setTimeout(1200)` antes de `_initEvt()`.
EAN v2→v3: 4 EANs malformados corregidos (78924468→0000078924468, etc.)

## Documento técnico LaTeX — ICR (Overleaf)

Informe de prensa en LaTeX (pdfLaTeX). Nombre del índice: **ICR** (Índice de Consumo Representativo). Estado: en desarrollo activo [2026-06-03].

### Errores pendientes de corregir en Overleaf

**ERROR — Córdoba geográfico** (grave): El texto dice que NEA y NOA, junto con Entre Ríos y **Córdoba** están por debajo del promedio. FALSO: Córdoba = +0,84% sobre el promedio para la canasta Media. Las provincias por debajo del promedio son: NEA (Formosa, Chaco, Misiones, Corrientes), litoral (Entre Ríos, Santa Fe) y AMBA (CABA, Buenos Aires). El NOA está levemente por encima.

**ERROR — Patrón Vulnerable**: el texto dice que el patrón "NEA más barato" se repite en todas las canastas. Para Vulnerable las más baratas son San Juan y Mendoza (Cuyo). Corregir con una oración de excepción.

**Pendiente menor**: `\AutorInforme{Santiago Riverti}` (investigador independiente) no fue definido → portada sin autor.

**Pendiente menor**: `\usepackage{caption}` duplicado en el preámbulo (genera warning en Overleaf).

### Datos verificados (cruzados notebook + .tex exportados)

- $634.923 Media abril 2026 ✅ | $691.836 Celíaca (+9.0%) ✅ | $427.033 Vegana (−5.5%) ✅
- Todas las tablas provinciales (6 canastas × 24 provincias) ✅
- Rankings nacionales por cadena ✅ (Disco $656.205, Hipermercado Libertad $615.172)
- Belgrano case study ✅ | Pinamar ✅ | Costa Atlántica (pendiente verificar en Excel)
- Valores AMBA Disco $660.777, ChangoMas $622.626 (pendiente verificar en Excel)

### Workflow actualización mensual

Con el nb02 ejecutado para el nuevo mes:
1. Ejecutar **CELDA 20** → genera hoja `Valores_Documento` en `canasta_analisis_MMAAAA.xlsx`
2. La hoja tiene columnas: Sección | Variable | Valor_LaTeX | Valor_numero
3. Buscar en `Valor_LaTeX` los nuevos valores y reemplazar en Overleaf
4. Actualizar `\Fecha{...}` y el subtítulo de portada con el nuevo mes
5. Completar manualmente **Belgrano** y **Costa Atlántica** desde hoja `Sucs_Media` (ver abajo)

#### Cobertura detallada de CELDA 20 [2026-06-05]

**CELDA 20 genera automáticamente (print + hoja Valores_Documento):**
- Valores y variaciones mensuales de las 6 canastas
- Provincias: min/max, dispersión interprovincial, rango sucursales (P25, P75)
- Barrios CABA: ranking completo, top/bottom 3, dispersión, promedio CABA
- Cadenas: ranking nacional completo con vs. promedio %; ranking AMBA
- Especiales: prima celíaca %, ahorro vegano %
- Acumulados desde MES_INICIO_GRAFICO (6 canastas + IPC)
- Últimas 3 variaciones mensuales (todas las canastas + IPC general + alimentos)

**NO cubre — requiere lookup manual desde hoja `Sucs_Media`:**
1. **Caso Belgrano**: desglose por cadena dentro del barrio → filtrar `Sucs_Media` por barrio=Belgrano
2. **Tablas Costa Atlántica/Pinamar**: valores por localidad y sucursal → filtrar `Sucs_Media` por localidad
3. **Picos/mínimos históricos**: datos fijos, solo actualizar si el nuevo mes bate récord

## Estado documento técnico LaTeX — abril 2026 [2026-06-05]

**Documento FINALIZADO y publicado.** Errores corregidos en Overleaf:
- ✅ Córdoba clasificada como sobre el promedio (no debajo)
- ✅ NOA clasificado como levemente sobre el promedio (no debajo)
- ✅ ".." doble punto al final del párrafo del mapa corregido
- ✅ "2.368" → "2.373" sucursales uniformizado
- ⚠️ `\usepackage{caption}` duplicado (warning Overleaf, no rompe compilación)
- ⚠️ `\AutorInforme` definido pero sin valor → portada sin autor

## Script 03 — Consolidación diario → semestral [2026-06-23]

`notebooks/03_consolidacion_ultimo_mes.py` (corre LOCAL, no Colab). Convierte el SEPA **diario** (`ultimo_mes.zip`, ~7 GB, carpetas `YYYY-MM-DD/` con un zip por comercio) al formato **semestral wide** que leen los notebooks 01/02. Permite analizar el mes en curso sin esperar la semana que tarda Hacienda en publicar el consolidado.

**Contrato de salida (idéntico al oficial, verificado contra `2026A.zip`):**
- `MMAAAA_pais_parte1COMPLETO.csv.gz` (días 01–15) + `parte2` (16–último)
- Header: `id_comercio,id_bandera,id_sucursal,sucursales_provincia,id_producto,precio_YYYYMMDD,…` (coma)
- Precio: **centavos enteros** (diario en pesos ×100). Faltante: `NA`.
- Se empaqueta dentro de `2026A.zip` (nb02 solo lee zips `YYYYA/B` vía `_PAT_SEM`), reemplazando el mes viejo y conservando el resto.

**Trampas resueltas (críticas):**
- `id_sucursal`: el diario rellena con ceros (`004`), el maestro usa `4` → `_norm_suc()` quita los ceros. Sin esto el join geográfico cae a ~70%; con el fix, ~99–100%.
- Unidades: diario en pesos / oficial en centavos → ×100. El autodetect de factor del notebook (mediana>10.000→/100) lo procesa.
- El diario MINORISTA no trae mayoristas (id_comercio 2000/3001/etc.); el oficial sí. Coherente con el objetivo del proyecto.
- RAM acotada: pivot **por comercio** (pico ~2–3 GB) en vez de pivotear los ~335M registros long del mes de una.

**Esquema diario (pipe `|`):** `productos.csv` = id_comercio|id_bandera|id_sucursal|id_producto|productos_ean|…|productos_precio_lista(idx9)|…  ·  `sucursales.csv` trae `sucursales_provincia` (AR-X, igual que `maestro-provincias.xlsx`).

**Config del script:** `ZIP_DIARIO`, `SEMESTRE_ZIP_IN` (2026A.zip a actualizar), `OUTPUT_DIR`, `MES_FORZADO`, `LIMITE_COMERCIOS`/`LIMITE_DIAS` (debug). Rutas locales: diario en `...\SEPA\sepa_diario_minoristas\ultimo_mes.zip`; semestrales en `...\SEPA\SEPA_Bases_Originales\carga\`.

**Dos formas de correrlo:**
- **`03_consolidacion_ultimo_mes.ipynb`** (Colab, el que usa el usuario): sube `ultimo_mes.zip` al entorno `/content/`, ejecuta todo, y `files.download()` devuelve los dos `.csv.gz`. NO monta Drive ni empaqueta el zip — el usuario sube los `.csv.gz` al `2026A.zip` a mano. Generado desde el `.py` extrayendo el bloque de funciones (de `_COLS_PROD` hasta `escribir_parte`).
- **`03_consolidacion_ultimo_mes.py`** (local): mismo motor + empaqueta en `2026A.zip` in-place.

**⚠️ Colab NO sirve para este zip**: la subida de `ultimo_mes.zip` (~7 GB) al panel de Colab falla (la rueda se pone roja; la transferencia navegador→runtime no es resumible y se corta con archivos grandes). **Vía recomendada: el `.py` LOCAL** — no sube nada, procesa el zip del disco. El notebook .ipynb queda igual en el repo por si en el futuro el zip es chico o se sube por Drive (resumible) + mount.

**Cómo corre el usuario el `.py` local** (documentado paso a paso en README, sección "Correrlo localmente"): entorno ya tiene Python 3.14.5 + pandas 2.3.3 + numpy 2.4.6 (no instalar nada). Editar `CONFIGURACIÓN` (ZIP_DIARIO, SEMESTRE_ZIP_IN=2026A.zip, OUTPUT_DIR) y `python notebooks/03_consolidacion_ultimo_mes.py`. Salida: dos `.csv.gz` + `2026A.zip` actualizado in-place.

**Estado [2026-06-23]:** ambos commiteados + linkeados en README. Validados: .py en subconjunto, .ipynb con smoke-test. Join maestro 99–100%.

**✅ CORRIDA REAL DE JUNIO (días 1–23) EXITOSA — `.py` local, 29,7 min:**
- 20 comercios detectados; 19 con datos. **Comercio 36 = "sin datos"** (zip de origen vacío/corrupto en el diario; tampoco aparece en los archivos oficiales del SEPA, no es cadena relevante → ignorar).
- Filas totales: **16.029.900** (producto×sucursal). EANs únicos: **88.444** (coherente con minorista-puro; los ~170K del README incluyen mayoristas).
- Comercios grandes OK: Carrefour(10)=3,79M filas/468s · DIA(15)=4,41M/470s · ChangoMas(11)=2,9M · Cencosud(9)=1,43M. RAM aguantó en 16 GB.
- Salida: `062026_pais_parte1COMPLETO.csv.gz` (140,3 MB, 15 días) + parte2 (124,7 MB, 8 días 16–23). `2026A.zip` actualizado = **1,73 GB** con los 6 meses (ene–jun) intactos.
- Validación del 2026A.zip: header idéntico al oficial, mediana $4.650 (centavos OK), NA día 1 = 9,2% (normal). Tamaño junio ≈ meses oficiales (un poco menos: sin mayoristas + parte2 con 8 días porque junio no cerró).

**Cuando junio cierre (día 30)**, re-correr Script 03 con `ultimo_mes.zip` completo → parte2 tendrá 15 días (16–30).

## ✅ Resultados JUNIO 2026 (nb01 + nb02 end-to-end con datos de Script 03) [2026-06-24]

Pipeline completo validado con el `2026A.zip` que incluye junio (23 días). **Trazabilidad de los EANs de la canasta: 99,7% promedio** (250 únicos, mínima 83,3%) → la calidad del Script 03 es excelente. nb02: factor 100 autodetectado OK, 261/261 EANs con datos, 2.616 sucursales.

Costos nacionales junio 2026 — **NIVEL** (promedio provincial ponderado por población = "cuadro"). El nivel es un snapshot al día 23, válido. **La variación mensual de junio es PRELIMINAR/subestimada por mes parcial (ver análisis abajo).**

| Canasta | Costo jun-2026 (nivel) |
|---|---|
| Vulnerable | $270.580 |
| Vegana Básica | $446.132 |
| Popular | $479.319 |
| Media | $662.441 |
| Celíaca Media | $719.474 |
| Media Alta | $948.549 |

Prima celíaca +8,6% · ahorro vegano −6,92% · dispersión provincial 6,7% (Formosa más barata, Santa Cruz más cara). Patrón NEA-barato/Patagonia-cara confirmado.

**✅ BUG-23 confirmado resuelto en producción** (corrida del 2026-06-24): la serie ahora va `2024-01 → 2026-06` (30 meses, las 6 canastas), Gráficos 1/2/3 incluyen junio, variaciones-3-meses muestran 04/05/06. El caché funcionó como diseñado: reconstruyó 29 meses cerrados + junio fresco; próxima corrida será rápida.

## ⚠️ Análisis: variación de junio salió baja (+0,37% Media) — NO es bug [2026-06-24]

El usuario notó que la serie marcó **Media jun +0,37%** (mayo $659.355 → junio $661.785) mientras el headline/cuadro pasó de mayo $650.925 → junio $662.441 = **+1,77%**. Investigado con datos reales del zip local:

- **Mayoristas DESCARTADO**: recalcular mayo solo-minoristas vs todos da **-0,01%** (los mayoristas no mueven la canasta). El que junio (Script 03) no traiga mayoristas no afecta.
- **Causa principal = MES PARCIAL**: la serie compara mayo COMPLETO (31 d) contra junio incompleto (23 d). Probado: mayo recortado a 23 días = $655.529 vs $659.355 completo → **sesgo -0,58%**. Comparando 23d-vs-23d, la variación sube de +0,37% a **+0,95%**.
- **Causa secundaria = dos metodologías**: el "cuadro" (mediana por sucursal ponderada por población, CELDA 8) ≠ la "serie" (mediana nacional por EAN, CELDA 9/11). Por eso cuadro +1,77% vs serie +0,95% (ya corregida por días). Ambas válidas, miden distinto. El cuadro TAMBIÉN sufre el sesgo de mes parcial.

**Conclusión**: el código está bien; la variación mensual de un mes parcial está subestimada y NO debe reportarse hasta cerrar el mes. El NIVEL ($662.441) sí es un snapshot válido.

## Feature: detección de MES PARCIAL en nb02 [2026-06-24]

`gen_nb02.py` CELDA 6: lee los headers del mes actual, cuenta días-columna `precio_YYYYMMDD` y compara con `calendar.monthrange`. Define globals `MES_PARCIAL`, `DIAS_CARGADOS`, `DIAS_MES`, `SUFIJO_PARCIAL`. Si parcial:
- Print de advertencia en CELDA 6 y en el RESUMEN.
- Título rojo en Gráficos 1 y 2 ("Último mes PARCIAL — N/M días · variación preliminar").
- Nota al pie roja en Gráfico 3 + sufijo en Valores_Documento (Mes y Var. mensual media → "⚠️ PRELIMINAR").

Detección validada (jun 23/30=parcial; may 31/31, jun 30/30, feb 28/28 = completos).

## BUG-23 — Serie/gráficos no incluían el mes en curso [2026-06-24]

`gen_nb02.py` CELDA 9. Con junio cargado, los cuadros/rankings mostraban junio pero los **Gráficos 1/2/3 + acumulados/variaciones** terminaban en mayo (serie `2024-01 -> 2026-05`). Causa: el caché `hist_union_<hash>.parquet` se identifica solo por EANs; agregar un mes no cambia el hash → cargaba caché viejo. Agravante: cacheaba el mes en curso, que crece día a día → quedaba congelado.

**Fix (CELDA 9 reescrita):** caché solo de **meses cerrados** (incremental, lee solo los que faltan) + **mes en curso SIEMPRE releído fresco** (nunca cacheado) → usa los días vigentes. El caché viejo se reutiliza para meses cerrados → primera corrida post-fix es rápida (solo relee el mes en curso). Helper `_leer_mes_hist(_lbl)` + `_mapa_mes` (mes→zip/archivos). `_mes_actual = _meses_disp[-1]`.

Todo (gráficos, tablas, acumulados, Excel) deriva de `serie_nac_dict`/`.iloc[-1]` → con la serie corregida, todo incluye el mes en curso. El merge serie×IPC es `how='left'` → el mes en curso se mantiene aunque el IPC de INDEC todavía no exista (la línea de canasta llega al mes, la del IPC corta donde haya dato). Los cuadros/rankings/barrios ya usaban bien los días vigentes (se calculan directo del archivo del mes). Bonus: ids de celda del notebook ahora deterministas (md5) para evitar "drift" espurio al regenerar.

## Pendientes próxima sesión (mayo 2026)

1. **Ejecutar notebook 02** con datos mayo 2026 (zip SEPA del 2do semestre o nuevo mes)
2. **Mapa GitHub Pages**: CELDA 17 en Colab → descargar HTML (~3-5 MB) → subir `index.html` al repo `mapa_precios_minoristas`
3. **Actualizar LaTeX**: copiar `Valores_Documento` al Overleaf; completar Belgrano y Costa Atlántica desde `Sucs_Media`
