# Contexto del Proyecto — Precios Minoristas SEPA

Última actualización: 2026-10-26, cierre (más tarde) (nb06: los sabores de una línea cuentan como un producto y el penne se compara con el Matarazzo común; 67 productos en 45 líneas, 80 códigos; esperados `docs/brecha_celiaca/simulacion_2026-10-26d/`; falta Colab). Antes, 2026-10-26, cierre de la noche (nb06: TPD del panel corregida, Pepitos como comparador de con chips y la Opera de 92 g junto a la de 220 g en obleas; 67 productos, 80 códigos; esperados `docs/brecha_celiaca/simulacion_2026-10-26c/`; falta Colab). Antes, 2026-10-26 noche (nb06: la corrida de Colab con la canasta corregida dio igual a la simulación; revisión de sus resultados en `docs/AUDITORIA_SELECCION_2026-10-26_nb06.md` §7: artefacto de la TPD del panel en oct-2023 y evidencia para las propuestas de productos). Antes, 2026-10-26, auditoría de la selección (nb06: BUG-49, cuatro errores de las reglas de la selección corregidos; canasta de 66 productos y 77 códigos; esperados `docs/brecha_celiaca/simulacion_2026-10-26b/`; falta Colab, relee 58 meses). Antes, 2026-10-26 cierre (nb06: la corrida de Colab con los gráficos corregidos dio igual a la simulación; revisión de datos y método frente al objetivo en `docs/REVISION_METODOLOGICA_2026-10-26_nb06.md`). Antes, 2026-10-26 noche (nb06: corregidos tres detalles de presentación de los gráficos de la CELDA 9; el Excel no cambia; falta re-correr en Colab para los PNG). Antes, 2026-10-26 tarde (nb06: **BUG-48**, las tiendas online que el maestro carga como Supermercado o Autoservicio salen por el nombre; el panel no cambia; esperados `docs/brecha_celiaca/simulacion_2026-10-26/`; la corrida de Colab con BUG-48 dio igual a la simulación, AUDITORIA_2026-10-26 §6). Antes, 2026-10-26 (nb06: la segunda corrida de Colab —con BUG-47 y la serie TPD— es idéntica a la simulación en el Excel, el mapa, la salida impresa y el caché: BUG-47 y la TPD verificados; `docs/AUDITORIA_2026-10-26_nb06.md`). Antes, 2026-10-23 noche (nb06: **serie TPD (hedónica)** de la brecha como robustez frente a la imputación de subtipos —CELDA 8b, una regresión por subtipo con efectos de celda sucursal-mes y de producto, errores agrupados por sucursal; `docs/BRECHA_CELIACA.md` §14.12—; a la tarde, la primera corrida de Colab dio igual a la simulación y BUG-47). Antes, 2026-10-23 (nb06: canasta FIJA 2022-2026 para la brecha celíaca —68 productos con TACC y sin TACC con continuidad temporal, geográfica y por cadenas elegidos con reglas sobre las salidas del nb09 y verificados con los precios de ene-2022 a oct-2026, empalmes de los códigos que cambió Molinos en 2023 (también los sin TACC de Matarazzo) y Wakas en 2024 con vigencia por código, pesos ENGHo, serie desde 2022 con panel balanceado, región/empresa/año; la brecha de 2023 está inflada por los precios controlados del lado con TACC— y BUG-46 —provincia por polígonos, archivo duplicado de ago-2024, comercios no supermercados, nombres oficiales, caché por mes, mediana exacta, canasta que dependía del maestro del Drive, códigos viejos con precio congelado—; estimador por subtipo agregado subtipo → tipo → canasta; test nuevo `test_brecha_celiaca.py`; simulado con los 58 meses del Drive —coincidencia exacta con un cálculo independiente, pico de RAM 2,5 GB— y resultados esperados en `docs/brecha_celiaca/simulacion_2026-10-23/` con `s16_comparar_colab.py`; falta la corrida en Colab, que relee 58 meses una vez; `docs/BRECHA_CELIACA.md` §14). Antes, 2026-10-22 cierre (documentación al día para retomar en otra PC: `docs/PASS_THROUGH.md` nuevo, METODOLOGIA §12-§14 —nb08 v2, nb09, canasta de pass-through—, SEPA_TECNICO con los defectos de la fuente 2022-2026, `requirements.txt` completo, bloque ESTADO ACTUAL / HANDOFF general en `.claude/memory.md`. Ese día: nb08 v2 con la canasta de pass-through por defecto e índice de sucursales apareadas —falta correrlo en Colab—; canasta fija de 775 productos para el pass-through diario y script de Colab que la pone en `cantidad_01`; corrida del nb09 v2 revisada y arreglos que no releen —hoja `Dias`, comercios que dejaron de publicar con `mes_baja_comercios`, códigos con basura unidos a su EAN, precio simbólico relativo—). Antes, 2026-10-16 cierre (nb02: provincia de la CELDA 7 por polígonos de ar.json con tolerancia —BUG-44, resuelto: Neuquén capital, Paraná y San Nicolás vuelven a su provincia; la próxima corrida relee 12 meses en la 19c y 33 en la econometría, una vez—; región de la 19b/19c por coordenadas —BUG-43, simulado con datos reales, la próxima corrida relee 12 meses una vez—, Excel de azul a verde. Antes ese día: corrida de oct-26 en Colab revisada —19b y 19c OK— y BUG-42 corregido: AMBA por coordenadas, una sola referencia del país, acumulados contra el IPC en el mismo período, dispersión P5-P95 y formato del documento técnico; revisión en `docs/AUDITORIA_2026-10-16_nb02.md`. Script 03: acepta la carpeta de días y elige solo el zip semestral A/B. Antes, 2026-10-15: nb02: hoja `analisis_detallado` —la primera del Excel, CELDA 19c— con índices mensuales y semanales de la canasta Media por rubro, región, provincia, cadena y tipo de sucursal; y desagregación de la variación mensual por producto, arrastre, cadena y región —CELDA 19b—. Guía: `docs/NB02_ANALISIS_VARIACION.md`. Antes, 2026-10-02: nb07 v5.15: composición por rubro con faltantes imputados y Lavarropas BGH en la Tecnológica, relee el SEPA; corrida v5.14 al 2026-10-01 auditada y publicable. nb07 v5.14: el mismo cálculo que la v5.13 con un tercio de la RAM, corre en el Colab gratuito sin "RAM amplia"; no relee el SEPA. Antes, 2026-09-24: nb07 v5.13 lista para correr: frescos por TPD con nivel fijo, cobertura mínima de empaquetados, filtro estacional de frescos y ronda 2 de reemplazos —267 EANs—; ver el historial de cambios y `.claude/memory.md`. Antes, 2026-09-09: nb05/nb02: BUG-29 gráfico de barras con series de distinta longitud, BUG-30/32 mosaicos del mapa —CartoDB exige API key y OSM no responde desde la red de INECO— y BUG-31 el mapa pesaba 48 MB. Antes, 2026-09-07: nb07 v5.3, banda de plausibilidad anclada en frescos)

> **El proyecto tiene 9 herramientas (nb01–nb09).** Las descripciones detalladas por celda más
> abajo en este archivo son **históricas** (describen la arquitectura previa de nb02); el estado
> vigente y el detalle por celda están en `.claude/memory.md`. Documentos por tema:
> `docs/METODOLOGIA.md` (metodología ICR + doble análisis; nb08, nb09 y la canasta de pass-through en §12-§14),
> `docs/BRECHA_CELIACA.md` (Notebook 06), `docs/canastas_alternativas/README.md` (Notebook 07 y canasta de
> pass-through), `docs/PASS_THROUGH.md` (pass-through del tipo de cambio con el nb08), `docs/NB02_ANALISIS_VARIACION.md`
> (nb02 CELDAS 19b/19c), `docs/SEPA_TECNICO.md` y `docs/BUGS_Y_MEJORAS.md`.
>
> **Para retomar el trabajo** (en esta o en otra máquina): el punto de entrada es el bloque
> **ESTADO ACTUAL / HANDOFF** al principio de `.claude/memory.md` — estado por notebook, pendientes
> ordenados y las reglas técnicas que suelen morder.
>
> **Novedades 2026-08-21**:
> - **nb02 y nb05** generan TODO por duplicado — análisis **mediana** (nombres base) y **promedio**
>   (sufijo `_prom`, outliers fuera `[mediana/4, mediana×4]`). El precio por sucursal se calcula
>   sobre **todos los días del mes** (antes: primer día). Metodología: `METODOLOGIA.md` §4.
> - **Notebook 06 — Brecha celíaca (TACC vs sin-TACC)**: evolución mensual de la brecha entre
>   canasta base y celíaca (método vigente: **intra-super por sucursal-mes, $/100g**; las series
>   diaria/semanal quedan vacías), desagregada por provincia/cadena/concentración. Detalle completo
>   en `docs/BRECHA_CELIACA.md`.
> - Fix del encabezado LaTeX de las tablas de canasta (`\\` duplicado) — ver `BUGS_Y_MEJORAS.md`.
>
> **Novedades 2026-08-25**:
> - **nb06 corrido y validado** (julio 2026) con EANs TACC curados por cobertura + **fix de RAM**
>   (lectura colapsada a mediana mensual; caché `_v2`). Brecha por tipo +138% a +362%; canasta
>   acotada +240%. Resultados en `docs/BRECHA_CELIACA.md` §12.
> - **🎓 nb06 es ahora la base de un PAPER ACADÉMICO** sobre la brecha celíaca y sus determinantes
>   (tiempo, concentración, geografía, cadena). Agenda metodológica (amenazas a la validez a resolver
>   con rigor científico) en `docs/BRECHA_CELIACA.md` §13. Método/EANs congelados por ahora.

## Objetivo

Construir hasta **6 canastas representativas** a partir de los datos del SEPA (Sistema Electrónico de Publicidad de Precios Argentinos), calcular su costo mensual por sucursal y provincia, y compararlas con el IPC INDEC.

El notebook 01 entrega un Excel con **cuatro hojas**:
- **Canasta**: ~65 productos seleccionados automáticamente por cobertura, coloreados por grupo
- **Candidatos**: ~3.650 productos que superan los umbrales estrictos (5 cadenas, 24 provincias, 50 sucursales)
- **Selección**: ~25K productos con umbrales amplios, con **6 columnas de cantidad** (`cantidad_01`..`cantidad_06`) para definir hasta 6 canastas independientes
- **Productos unicos**: ~75K productos sin umbrales de cobertura, para exploración libre

## Repositorio

- **GitHub**: santiagoriverti/precios_minoristas_supermercados
- **Notebook 01**: `notebooks/01_exploracion_productos.ipynb` — selección dinámica de canasta (ejecutable en Colab)
- **Notebook 02**: `notebooks/02_evolucion_canasta_representativa.ipynb` — análisis de canasta elegida, mapas, rankings (ejecutable en Colab)
- **Maestros**: `data/` — productos, sucursales, provincias
- **Datos SEPA**: NO están en el repo. Están en Google Drive personal: `/carga/` (2022A.zip … 2026B.zip; 2022-2023 los
  usan el nb08 y el nb09; desde ago-2026 el `2026B.zip` se completa con el script 03)
- **Archivos auxiliares en Drive** (`carga/`): `IPC.xlsx` (IPC INDEC), `ar.json` (GeoJSON provincias), `output_canasta/canasta_representativa_YYYY-MM.xlsx`,
  `output_canasta/canasta_pass_through_2026-10.xlsx` (entrada del nb08), `output_trazabilidad/` (nb09)

## Puesta en marcha en otra máquina

Todo lo necesario viaja en el repo (notebooks, generadores, maestros de `data/` y documentación);
lo único que falta son los datos SEPA y los auxiliares, que están en el Drive.

```bash
git clone https://github.com/santiagoriverti/precios_minoristas_supermercados
cd precios_minoristas_supermercados
pip install -r requirements.txt                     # pandas, numpy, pyarrow, openpyxl, xlrd, matplotlib, seaborn,
                                                    # folium, tqdm, xlsxwriter, scipy, psutil, python-calamine
python notebooks/test_celdas_graficos_y_mapa.py     # gráficos + mapa (nb05 y nb02)
python notebooks/test_encadenado_frescos.py encadenado   # índice de frescos (nb07), método encadenado
python notebooks/test_encadenado_frescos.py tpd          # índice de frescos (nb07), método TPD (el vigente)
python notebooks/test_frescos_v513.py              # TPD, nivel fijo, cobertura mínima (v5.13)
python notebooks/test_quiebre_serie.py              # quiebre de serie del índice (BUG-36)
python notebooks/test_cache_por_mes.py              # caché por mes + compilan todas las celdas del nb07
python notebooks/test_costo_sucursal.py             # costo por sucursal (BUG-37) + anclaje de nivel
python notebooks/test_candidatos_reemplazo.py       # hoja Candidatos_trazabilidad (v5.11)
python notebooks/test_desagregacion_variacion.py    # nb02 CELDA 19b (desagregación de la variación)
python notebooks/test_analisis_detallado.py         # nb02 CELDA 19c (hoja analisis_detallado)
python notebooks/test_valores_documento.py          # nb02 CELDAS 7 (AMBA), 16, 18 y 20 (documento técnico)
python notebooks/test_reclasificacion_provincia.py  # nb02 CELDA 7 (provincia por polígonos de ar.json, BUG-44)
python notebooks/test_trazabilidad_productos.py     # nb09 (SEPA sintético contra fuerza bruta, ~6 min)
python notebooks/test_canasta_diaria.py             # nb08 v2 (medianas y sucursales apareadas contra fuerza bruta)
python notebooks/test_brecha_celiaca.py             # nb06 (canasta fija, subtipos, vigencias, geografía, ENGHo, caché)
```

Los 15 tests tienen que terminar en OK (verificado el 2026-10-23 con Python 3.14, pandas 2.3, numpy 2.4; versiones
completas en `requirements.txt`). En Windows, si la consola no muestra bien los acentos: `set PYTHONUTF8=1` (cmd) o
`$env:PYTHONUTF8=1` (PowerShell) antes de correrlos.

**Por dónde empezar**: `CLAUDE.md` (raíz) y el bloque **ESTADO ACTUAL / HANDOFF [2026-10-23]** al principio de
`.claude/memory.md` (estado de cada línea de trabajo y qué hacer con los próximos resultados); debajo están los bloques
de cada notebook (nb06, nb08, canasta de pass-through, nb09, nb02, nb07) con el detalle.
- **Brecha celíaca / nb06**: `docs/BRECHA_CELIACA.md` §14 (canasta fija 2022-2026, estimador por subtipo, qué revisar
  en §14.9 y lo esperado en §14.10). Para revisar una corrida hacen falta la salida impresa y
  `output_brecha/brecha_celiaca_<mes>.xlsx`; se compara con
  `python -I -X utf8 docs/auditoria/scripts_nb06_2026-10/s16_comparar_colab.py <Excel> docs/brecha_celiaca/simulacion_2026-10-26d`
  (el notebook vigente; para revisar también el caché del Drive y el mapa, `r13`-`r15`).
- **Pass-through / nb08**: `docs/PASS_THROUGH.md` (cómo correrlo y qué revisar). Para revisar una corrida hacen falta la
  salida impresa, `canasta_diaria_pass_through_<desde>_<hasta>.xlsx` y `panel_diario_pass_through_<...>.parquet`.
- **nb09**: la última corrida revisada está en `docs/AUDITORIA_2026-10-22_nb09.md`; para revisar una corrida hacen falta
  la salida impresa y los cuatro archivos de `output_trazabilidad/` (Excel, `.parquet`, `.csv.gz` y
  `panel_mensual_productos_<...>.parquet`); los scripts están en `docs/auditoria/scripts_nb09_2026-10/`.
- **nb02** (análisis de la variación de la canasta): `docs/NB02_ANALISIS_VARIACION.md`; la última corrida revisada
  (qué se esperaba, qué salió, qué quedó abierto) está en `docs/AUDITORIA_2026-10-16_nb02.md`. Para revisar una corrida
  del nb02 hacen falta la salida impresa, `canasta_analisis_<mes>.xlsx` y un zip de `output_canasta/_cache/`.
- **nb07**: para auditar una corrida hacen falta el Excel de salida y las carpetas del caché del Drive
  (`_cache_nb07/sem_<clave>_v5` y `ean_<clave>_v5`, en zip); la planilla de precios promedio del INDEC
  está en `data/sh_ipc_precios_promedio_2026-08.xls` (bajar la nueva cuando se publique).

Reglas del repo que conviene saber antes de tocar nada:

1. **Los `.ipynb` no se editan a mano.** La fuente de verdad son los `notebooks/gen_nbXX.py`;
   `python notebooks/gen_nb05.py` reescribe el `.ipynb` completo. Regenerar siempre después de
   tocar un generador y commitear los dos archivos juntos.
2. **Dentro de `cell_code("""...""")` no van barras invertidas** (Python se las come antes de que
   lleguen al notebook) ni comillas triples. Ver BUG-17, BUG-20 y el reincidente del 2026-09-09
   en `docs/BUGS_Y_MEJORAS.md`.
3. Los notebooks corren en **Colab** (badges en el README), no localmente: necesitan los ZIPs del
   SEPA en `MyDrive/carga/`. El nb07 corre en el **Colab gratuito** desde la v5.14 (antes pedía "RAM
   amplia" de Colab Pro); una relectura completa del SEPA tarda ~2h10m ahí y retoma por mes si se corta.
4. Los maestros se buscan **primero en el Drive y después en GitHub** (commit `502581a`). Hoy el repo es público
   (verificado el 2026-10-16) y Colab los baja de GitHub; si se pone privado, `raw.githubusercontent` da 404 y hay
   que copiar los maestros de `data/` al Drive (README, "Repositorio privado").
5. **Datos para simular o auditar en una PC** (no están en el repo): los zips semestrales del SEPA y `ar.json`
   (`MyDrive/carga/`), el Excel de la corrida y el zip de `output_canasta/_cache/`. Los scripts de
   `docs/auditoria/scripts_nb02_2026-10/`, `scripts_nb06_2026-10/`, `scripts_nb08_2026-10/` y `scripts_nb09_2026-10/`
   dicen en su encabezado qué necesita cada uno. En la PC del INECO: desde el 23/10/2026 **todos los zips del Drive
   (2022A → 2026B) están en `C:\Users\sriverti\Downloads\`**, junto con la carpeta `carga` entera bajada en 10 zips
   (`carga-20261023T013908Z-1-001..010.zip`); además, zips 2024A → 2026B en
   `C:\Users\sriverti\Desktop\INECO\SEPA\SEPA_Bases_Originales\carga\` (no hay 2022-2023; ese `2026B.zip` es del
   20/08 y trae solo julio), `ar.json` en `C:\Users\sriverti\Desktop\INECO\Otros\ar.json` (idéntico al del Drive).
   **Ojo**: el `2026B.zip` de
   `C:\Users\sriverti\Desktop\INECO\SEPA\salida_consolidada\` (script 03, 22/10/2026) trae **solo julio y octubre de
   2026** (se armó sobre el local del 20/08): no subirlo al Drive tal cual; el `2026B.zip` completo (jul-oct) es el del
   Drive. Lo que pase el usuario (Excel, cachés, salidas) se descomprime en una
   carpeta propia y los scripts se corren con `python -I -X utf8` y las rutas como argumentos (datos no confiables).
6. **Archivos fuera del repo que se entregaron al usuario** (en la PC del INECO, `C:\Users\sriverti\proyectos\`): el Excel
   completo de la selección de la canasta de pass-through (`canasta_pass_through_20220101_20261020.xlsx`, 8 hojas; se
   rehace con `canasta_pass_through.py`, ver `docs/PASS_THROUGH.md`), `canasta_continua_cantidad_07.xlsx` (canasta
   "Continua 2022" de 28 productos, reemplazada por la de pass-through), `seleccion_brecha_celiaca_20261022.xlsx` (el
   Excel de decisión de los candidatos de la brecha celíaca; scripts s1-s6) y `nb06_brecha_celiaca_20261023\` (trabajo
   intermedio de la canasta fija del nb06: precios extraídos 2022-2026, selección, verificación y la simulación con el
   caché del nb06; ~315 MB, README adentro; se rehace con los scripts s7-s15).

---

## Ecosistema de notebooks relacionados

Este proyecto no existe en aislamiento. Hay múltiples notebooks en otros repositorios que procesan los mismos datos y de los que se pueden tomar patrones.

### 1. `01_exploracion_productos.ipynb` (este repo — notebook 01)
**Propósito**: selección dinámica de canasta por score de cobertura.
**Enfoque**: todos los productos del SEPA semestral → filtrar por cobertura → seleccionar top-N por grupo.
**Output**: `canasta_representativa_MMAAAA.xlsx` (hojas: Canasta, Candidatos, Selección)

### 2. `02_evolucion_canasta_representativa.ipynb` (este repo — notebook 02) ← NUEVO
**Propósito**: análisis completo de la canasta elegida por el economista.
**Enfoque**: lee la hoja `Selección` del Excel del notebook 01 (campo `cantidad`), calcula el costo por sucursal con imputación nacional, compara con IPC INDEC, y genera todas las visualizaciones.
**Pipeline (20 celdas)**:
- CELDA 1–2: Markdown + Config (`SEPA_DIR`, `OUTPUT_DIR`, `USE_CACHE`, `MES_INICIO_HISTORICO`, `MES_INICIO_GRAFICO`, `MIN_PRODUCTOS_PROPIOS`, `MIN_SUCURSALES_RANKING`)
- CELDA 3: Mount Drive
- CELDA 4: Canasta desde Excel (hoja `Selección`/`Seleccion`, campo `cantidad`)
- CELDA 5: Maestros — `NOMBRES_COMPUESTOS`, `NOMBRES_SIMPLES`, `PROV_NORM` (24 provincias), `PESOS_POBLACION` (Censo 2022)
- CELDA 6: Funciones auxiliares (`get_nombre_cadena`, `normalizar_provincia`, `precio_a_pesos`)
- CELDA 7: Carga mes actual desde ZIPs, filtra a EANs de la canasta, precio promedio por producto por sucursal
- CELDA 8: `calcular_canasta_completa()` por sucursal — imputación con mediana nacional para productos faltantes → `canasta_geo_filtros`
- CELDA 9: Análisis provincial — mediana por provincia, ponderación por población → `serie_provincia_valida`, `prom_nac_ponderado`
- CELDA 10: Serie histórica (todos los semestres disponibles) con caché parquet clave MD5 → `serie_nacional_valida`
- CELDA 11: IPC desde `carga/IPC.xlsx` → `ipc_general`, `ipc_alimentos`
- CELDA 12: `comparativa` — reindexar a base mar-2024, índice SEPA vs IPC
- CELDA 13: Gráfico 1 — índices base dinámica (líneas, etiquetas en español, serie llamada "ICR"); Gráfico 2 — variaciones mensuales (3 barras: ICR + IPC General + IPC Alimentos, etiquetas español)
- CELDA 14: Cuadro 1 provincial + código LaTeX
- CELDA 15: Mapa coroplético provincial con `ar.json`
- CELDA 16: Cobertura por provincia y por cadena
- CELDA 17: Rankings nacionales + AMBA (barras horizontales, gradiente RdYlGn)
- CELDA 18: Mapa Folium interactivo (FeatureGroups por cadena, panel JS de filtros)
- CELDA 19: Ranking CABA por barrio (48 bounding boxes lat/lon)
- CELDA 20: Diagnóstico trazabilidad temporal de todos los ~3.650 Candidatos (CELDA 20, opcional ~20 min)
- CELDA 21: Exportación Excel (`canasta_analisis_YYYY-MM.xlsx`) — 5 hojas: Evolucion_IPC, Por_provincia, Por_sucursal, Ranking_cadenas, **Serie_precios** (precio mediano por producto por mes)
**Output**: `output_canasta/canasta_analisis_YYYY-MM.xlsx` + `mapa_interactivo.html` + `trazabilidad_candidatos_YYYY-MM.xlsx` + **`datos_econometria_YYYY-MM.xlsx`** (tidy/long: canastas + productos, **semanal y mensual**, nivel nacional/provincia/cadena, con `valor_mediana` y `valor_promedio`; para series de tiempo. Config `PRODUCTOS_ECONOMETRIA` arriba de la CELDA 22).
**Archivos requeridos en Drive**: `carga/IPC.xlsx`, `carga/ar.json`, `output_canasta/canasta_representativa_YYYY-MM.xlsx`
**Cambios claves (2026-05-29)**:
- BUG-15 resuelto: `'San juan'` → `'San Juan'` en `PROV_NORM`
- Caché por hash de EANs+cantidades (cambiar qty invalida caché automáticamente)
- Gráficos con nombre "ICR" y etiquetas de meses en español (ene-24, feb-24…)
- Gráfico 2 con 3 barras: ICR + IPC General + IPC Alimentos
- `MES_INICIO_GRAFICO` auto-adapta al primer mes disponible si el configurado no existe
- Nueva hoja Excel `Serie_precios`: precio mediano por producto por mes (serie completa)

> ⚠️ La descripción de celdas de arriba es **histórica**. La arquitectura vigente de nb02 (doble
> análisis mediana/promedio, precio del mes completo, hojas geográficas) está en `.claude/memory.md`.

### 2b. `03_consolidacion_ultimo_mes` (Script 03 — este repo)
**Propósito**: convertir el SEPA **diario** (`ultimo_mes.zip` ~7 GB) al formato **semestral wide**
para adelantar el mes en curso. Corre **local** (Colab falla por el peso). Detalle: `SEPA_TECNICO.md`.
Desde 2026-10 `ZIP_DIARIO` acepta el zip o la carpeta con los días ya descomprimidos y `CARGA_DIR` (carpeta de los
semestrales) reemplaza a `SEMESTRE_ZIP_IN`: el script elige `YYYYA.zip` (ene-jun) o `YYYYB.zip` (jul-dic) y lo crea si
no existe. Oct-26 salió así: `102026_pais_parte1COMPLETO.csv.gz` dentro de `2026B.zip`.

### 2c. `04_precios_seleccion` (notebook 04 — este repo)
**Propósito**: Excel con precios diarios de los supermercados a ≤ X km de un punto (lat/lon).

### 2d. `05_evolucion_productos_representativos` (notebook 05 — este repo)
**Propósito**: igual que nb02 pero por **producto individual (EAN)** en vez de canasta ponderada.
Mismo doble análisis mediana/promedio. Config: `EANS_INPUT` (lista de EANs) en la CELDA 1.

### 2e. `06_evolucion_brecha_celiaca` (notebook 06 — este repo)
**Propósito**: brecha de precios **con TACC vs sin TACC** y cómo se distribuye en el tiempo (mensual desde ene-2022),
la geografía (provincia, región, AMBA) y las cadenas. Desde el 2026-10-23, **canasta fija 2022-2026** de 5 tipos con
dicotomía (fideos secos, galletitas dulces, galletitas saladas y crackers, rebozador, cereales rellenos) elegida por
reglas sobre las salidas del nb09 (`docs/BRECHA_CELIACA.md` §14; lista con métricas en
`docs/brecha_celiaca/canasta_fija_2022_2026.csv`). Brecha intra-sucursal por tipo en $/100 g; canasta = promedio de
los tipos con pesos ENGHo 2017/18. Config: `TIPOS`, `GRAMOS`, `VIGENCIA`, `PRODUCTO` y `SUBTIPO` en la CELDA 1 (los
arma `gen_nb06.py` desde el CSV). Provincias, regiones, empresas, cadenas y sucursales se comparan con la misma canasta
de 12 subtipos (BUG-47) y la concentración es el HHI de empresas por departamento (Georef). Serie TPD (hedónica) como
robustez de la serie mensual frente a la imputación de subtipos (CELDA 8b, BRECHA_CELIACA §14.12). Las corridas de
Colab del 2026-10-23 (canasta fija) y del 2026-10-26 (con BUG-47 y la TPD) dieron igual a la simulación. El
2026-10-26, la auditoría de la selección corrigió cuatro errores de las reglas (BUG-49; verificado en Colab esa
noche) y después se corrigió la TPD del panel y los comparadores de con chips (Pepitos) y obleas (las dos Operas).
Más tarde, los sabores de una línea pasaron a contar como un producto y el penne se compara con el Matarazzo común
(BRECHA_CELIACA §14.16): **67 productos en 45 líneas (80 códigos)**, esperados en
`docs/brecha_celiaca/simulacion_2026-10-26d/`; falta Colab. Test:
`notebooks/test_brecha_celiaca.py`. **Detalle completo: `docs/BRECHA_CELIACA.md`.**

### 2f. `07_evolucion_canastas_alternativas` (notebook 07) — motor del informe semanal
**Estado: v5.13 lista para correr (relee el SEPA), 2026-09-24.** Implementa las decisiones de la revisión de la
v5.12 (`docs/AUDITORIA_2026-09-24_v512.md` §7): frescos por índice multilateral TPD con el nivel fijado en el mes de
referencia, cobertura mínima de empaquetados, filtro estacional de Naranja/Tomate/Limón y la ronda 2 de reemplazos
(267 EANs). Efecto estimado y checklist de la corrida en `.claude/memory.md`. Es el notebook que alimenta el **informe semanal** del equipo de
economistas. Costo de **6 canastas** vs **IPC**, desagregado por **rubro** (drill-down hasta
producto), **provincia**, **región** y **cadena**.

**La semana**: ventana de 7 días que **cierra el jueves** (viernes→jueves), etiquetada por la
fecha de cierre (`2026-09-03`). Corriendo el viernes, la última semana está completa.
`DIA_CIERRE_SEMANA` (3=jueves, 4=viernes). *nb02 y nb06 siguen usando semana ISO.*

**Las 6 canastas** (hoja `Productos unicos`, **267 EANs** empaquetados únicos desde la ronda 2 del 2026-09-24 —288
hasta la v5.10; el 23-sep salieron pañales y toallitas, el 24-sep se reemplazaron 24 ítems sin historia completa
(270) y después otros 15 con historia flaca en 2024 (267)— + 59 tipos frescos; además, desde la v5.11,
`EANS_CANDIDATOS` —155 desde la v5.12— que se leen sin entrar a ninguna canasta).
Desde **v5 (2026-09-07)** cada estrato usa su propia versión de cada necesidad, con cantidades
físicas ancladas a la **CBA del INDEC para hogar tipo 2** (3,09 adultos equivalentes):

| Col | Canasta | Empaquetados | Frescos | Criterio de producto |
|---|---|---:|---:|---|
| `cantidad_01` | Popular | 58 | 32 | marca más barata con presencia nacional |
| `cantidad_02` | Media | 74 | 57 | marca líder |
| `cantidad_03` | Ejecutiva | 74 | 59 | premium |
| `cantidad_04` | Tecnológica | 14 | — | producto modal (bundle de durables) |
| `cantidad_05` | Representativa | 74 | 59 | producto modal — comparable con INDEC |
| `cantidad_06` | Femenina | 14 | — | marca líder |

> ⚠️ **No confundir**: `cantidad_01..06` en la hoja **`Productos unicos`** son estas 6 canastas
> (nb07). Las columnas `cantidad_01..06` de la hoja **`Selección`** son otras canastas distintas
> (nb02: ENGHo por quintil + Celíaca + Vegana, ver §6b de METODOLOGIA). Mismo nombre de columna,
> hojas y notebooks distintos.

**Composición híbrida**: (a) **empaquetados por EAN** con cobertura ≥4 cadenas, ≥15 provincias y
≥800 sucursales (durables ≥3/≥10/≥90); (b) **59 tipos de frescos por nombre** — el EAN de balanza
cambia por cadena y sucursal, así que se seleccionan por **nombre + categoría del maestro**
(`Frutas y Verduras`, `Carnicería`, `Fiambrería`, `Panificados`, `Pescados y Mariscos`, `Huevos`)
y se normalizan a **$/kg** o **$/docena**. Rubros de frescos: Frutas, Verduras, Carne, Pollo,
Cerdo, Pescado, Fiambres y Quesos, Panadería, Huevos.
Tecnológica y Femenina no llevan frescos y desglosan por `categoria` en vez de `rubro`.

**Metodología (detalle en METODOLOGIA §10.7):**
- **Índice encadenado de muestra apareada**: la variación entre semanas usa solo los ítems
  presentes en ambas. Elimina los saltos espurios por altas/bajas de productos.
- **Nivel en $**: canasta completa en la semana ancla (cobertura ≥95%), retropolada con el índice.
- **Nacional ponderado por población provincial** (antes era mediana simple, dominada por DIA con
  el 42% de las sucursales).
- **Arrastre** del último precio conocido hasta 8 semanas; más allá, alerta de reemplazo.
- **Filtro de outliers intra-tipo** en frescos: `[mediana/2.5, mediana×2.5]` por sucursal-semana.
- **Provincia/región controlando por cadena** (`idx_vs_nacional`, 100 = nacional): cada cadena se
  compara consigo misma entre la provincia y el país. Necesario porque las cadenas se distribuyen
  asimétricamente (Coto en pocas provincias, La Anónima domina Patagonia).
- `FRAC_PRODUCTOS_MIN = 0.8` (una sucursal cuenta si tiene ≥80% de los empaquetados).
- **Costo por sucursal** (v5.10): costo nacional + (precio de la sucursal − nacional) × cantidad
  en lo que publica; lo que no publica se valúa al nacional. Columna `pct_imputado` en las
  aperturas. Antes se omitían los rubros enteros ausentes (BUG-37).
- **Quiebre de serie** (v5.9): un ítem que se mueve ×3 o más en una semana sale de ese eslabón.
- **Nivel de frescos** (v5.10-v5.11): Pan francés, Pollo, Carne picada, Merluza, Limón, Tomate y
  Naranja anclados al precio promedio del INDEC (GBA) de ago-2026 (`NIVEL_REFERENCIA_FRESCO`); el
  resto, nivel del SEPA. Anclar un tipo cambia su peso en la canasta, y por eso también el índice.
- **Especificación de frescos** (v5.11): `EXCLUIR_EAN_FRESCO` (bandejas Atm de DIA fuera de Pollo y
  Suprema) y `RATIO_FRESCO` recalibrado en Pollo, Carne picada, Limón y Suprema (METODOLOGIA §10.16).
- **Candidatos a reemplazo** (v5.11): `EANS_CANDIDATOS` se leen del SEPA sin entrar a ninguna canasta;
  la hoja `Candidatos_trazabilidad` mide su historia. Pasarlos a una canasta no relee el SEPA.
- **Frescos por TPD** (v5.13): la forma de la serie de cada tipo sale de un índice multilateral time-product-dummy
  sin ponderar sobre sus EANs (ventana móvil de 52 semanas, empalme de movimiento: una semana nueva no revisa la
  historia); el nivel, del estimador ponderado por población en los 3 últimos meses con cobertura normal hasta el
  mes de referencia (2026-08), no en la última semana: un mes fuera de temporada (Durazno) o con media muestra
  perdida (Roast beef ago-26) no fija el nivel. Hoja `Frescos_metodos` con el encadenado de la v5.10-v5.12 al lado
  (METODOLOGIA §10.19).
- **Cobertura mínima de empaquetados** (v5.13): un ítem-semana con menos de min(300, 50% de su cobertura típica)
  sucursales es faltante y queda fuera de la muestra apareada (no se arrastra).
- **Filtro de régimen estacional** (v5.13): `RATIO_FRESCO` de Naranja 0,85, Tomate 1,45 y Limón 1,01, elegidos por
  recall/contaminación contra el precio INDEC de todos los meses (no de uno).

**Caché y RAM**: la lectura colapsa los frescos a su TIPO (de ~10.600 EANs a 59) durante la lectura y
guarda un parquet por mes cerrado: `_cache_nb07/sem_<clave>_v5/<mes>.parquet` (precio por sucursal) y
`ean_<clave>_v5/<mes>.parquet` (panel por EAN de frescos). Una corrida cortada retoma desde el último
mes guardado. La clave es un md5 del universo de EANs leído (canastas + candidatos + frescos) y de los
parámetros de la lectura (`DIA_CIERRE_SEMANA`, K de outliers y de régimen, piso/techo del ancla, `rk`,
`RATIO_FRESCO`): si cambia, se relee todo el SEPA (~1h20m).

**Salidas** (en `output_canasta_alternativa`; entrada en `output_canasta`):
`canastas_alternativas_YYYY-MM-DD.xlsx` con `Metodologia`, `Resumen`, y por canasta
`Sem_*`/`Mes_*`/`vsIPC_*`/`Rubro_sem_*`/`Comp_rubro_*`/`Detalle_*`/`Prov_*`/`Cadena_*`/`Region_*`/
`RegionSem_*`, `Panel_nacional` y `Panel_nacional_mes` (precio nacional de cada ítem), `Mes_rubro`/
`Mes_region`/`Mes_provincia`/`Mes_cadena`, `Cobertura_emp`, `Cobertura_frescos`, **`Presencia_items`**
(ítem × mes, % de semanas con dato real), **`Alertas_trazabilidad`**, **`Alertas_reemplazo`** (ítems
sin dato hace >8 semanas), **`Alertas_precio_item`** (saltos >35%), **`Alertas_quiebre`** (movimientos
×3 sacados del índice) y **`Candidatos_trazabilidad`** (v5.11).
CELDA 15 imprime el bloque **"REPORTE PARA CLAUDE"** en texto plano.

**Carga de cantidades**: `docs/canastas_alternativas/cargar_canastas_v5.py` (loader de Colab,
267 EANs, `cantidad_01..06`; limpia y reescribe las 6 columnas). Lo **generó**
`construir_canastas_v5.py` (con el Excel de 2026-08), que se corre local y deja además `canastas_v5_detalle.csv` con el
porqué de cada elección y `frescos_v5_qty.txt` con las tuplas para `TIPOS_FRESCOS`. Para cambiar
productos puntuales sin recalibrar todo: `aplicar_reemplazos.py` (mismas reglas del constructor;
actualiza el cargador y `EAN_FORZADO`); para proponerlos, `proponer_reemplazos.py`. **El cargador es la composición
vigente**: el constructor corrido con el Excel de otro mes elige otros productos (con el de 2026-09, 132 EANs
distintos); solo respeta los 42 pares de `EAN_FORZADO`.
Generador: `gen_nb07.py`. **Detalle en README y `docs/canastas_alternativas/README.md`.**

### 2g. `08_canasta_diaria` (notebook 08 — este repo)
Valor **diario** de una canasta de la hoja `Selección` desde 2022-01-01. **v2 (2026-10-22)**: por defecto la canasta fija
de **pass-through** (775 productos, `cantidad_01` de `output_canasta/canasta_pass_through_2026-10.xlsx`, hasta el
20/10/2026). Dos precios por producto y día: mediana nacional e **índice con sucursales apareadas** (relativos de la misma
sucursal, con imputación de los días que falta); valor de la canasta con los dos (encadenado con productos apareados y
anclado en el último día completo), índices por grupo del IPC, días con cobertura incompleta y panel producto × día. Un
archivo por quincena. Caché por mes con el estado de cada sucursal en `output_canasta/_cache/diaria_v2_<clave>/`.
**Falta la primera corrida en Colab** (~1,5-2 h). Fuente: `notebooks/gen_nb08.py`; test `notebooks/test_canasta_diaria.py`.
Detalle: README (sección `08_canasta_diaria`), `docs/PASS_THROUGH.md` y `docs/METODOLOGIA.md` §12.

### 2h. `09_trazabilidad_productos` (notebook 09 — este repo)
Representatividad de todos los productos del SEPA desde 2022 (temporal, sucursal, comercial, regional, precio y
puntaje). Fase 1 resume cada archivo de los zips semestrales en `output_trazabilidad/_cache_nb09/v1/` (un proceso por
archivo, por bloques: corre en el Colab gratuito); fase 2 agrega. Versión 2 (lector `LECTOR_VERSION = 2`) corrida y
revisada el 2026-10-22 (`docs/AUDITORIA_2026-10-22_nb09.md`), con hoja `Dias`, marcas de comercios que dejaron de
publicar (`mes_baja_comercios`), códigos con basura unidos y precio simbólico relativo. De sus salidas sale la canasta de
pass-through. Fuente: `notebooks/gen_nb09.py`; test `notebooks/test_trazabilidad_productos.py`. Detalle: README y
`docs/METODOLOGIA.md` §13.

### 3. `analisis_SEPA_evolucion.ipynb`
**Propósito**: evolución mensual de precios con canasta fija de 30 EANs.
**Enfoque**: procesa múltiples semestres (2022A–2026A), autodetecta FACTOR_PRECIO, calcula serie diaria nacional.
**Output**: `canasta_SEMESTRE_serie.xlsx` (hojas: serie_diaria_nacional, canasta_mes_provincia, canasta_mes_region, canasta_nacional_ponderada)

### 4. `analisis_SEPA_evolucion_AMBA.ipynb`
**Propósito**: foco en AMBA, 16 cadenas comerciales, mapas Folium interactivos.
**Clave crítica**: confirma **FACTOR_PRECIO = 1** para datos de abril 2026. Tiene el diccionario completo de `(id_comercio, id_bandera)` → nombre de cadena.
**Output**: mapa interactivo HTML + Excel con canasta por sucursal.

### 5. `consolidacion_analisis_SEPA.ipynb`
**Propósito**: consolida todos los semestres en una serie temporal de 52 meses (2022–2026).
**Output**: tablas LaTeX para papers + comparación SEPA vs IPC INDEC.
**Dato**: canasta nacional abril 2026 = **$322,566 ARS** (ponderada por Censo 2022).

### 6. `analisis_canasta_SEPA.ipynb`
**Propósito**: usa el formato DIARIO (no semestral) para ver los 28 banners comerciales reales.
**Formato**: `YYYY-MM-DD.zip` → 20 ZIPs por cadena → pipe-separated (`comercio.csv`, `sucursales.csv`, `productos.csv`).
**Clave**: 87,418 EANs únicos, precios directamente en pesos, 14.8M filas.

### 7. `analisis_precios_SEPA.ipynb`
**Propósito**: pipeline sofisticado con parquet cache + clasificación de rubros por keywords.
**Patrones útiles**: float32 desde el inicio, drop de columnas de promo, parquet snappy para cachear.
**Output**: 7,616 productos canastables identificados.

### 8. `analisis_precios_SEPA_2.ipynb`
**Propósito**: deduplicación de variantes del mismo producto.
**Técnica**: `extraer_concepto()` → top-3 palabras significativas minus marca/packaging → colapsa ~10% de duplicados.

### 9. `resultados_canasta_sepa.ipynb`
**Propósito**: visualización — coroplético, ranking, heatmap cadenas×provincias.
**Clave**: usa GeoJSON `ar.json` de simplemaps.com. El GeoJSON usa "Ciudad de Buenos Aires" → mapear a "CABA" en el join.

---

## Pipeline de `01_exploracion_productos.ipynb` (orden de celdas)

| Cell | Tipo | Descripción |
|------|------|-------------|
| 0 | md | Introducción y objetivo |
| 1 | md | Header sección configuración |
| 2 | code | **Config**: `SEPA_SOURCE`, `SEPA_DIR`, `OUTPUT_DIR`, `SEPA_ZIP_NAME`, `PERIODO`, `MIN_SUCURSALES`, `MIN_PCT_DIAS`, `USE_CACHE` |
| 3 | code | Mount Google Drive (solo si `SEPA_SOURCE = 'mi_drive'`) |
| 4 | code | Imports + instalación dependencias + resolución de paths + `CACHE_DIR` |
| 5 | code | `resolver_maestro()` — local-first, GitHub fallback; resuelve los 3 maestros |
| 6 | md | Header sección carga de datos |
| 7 | code | `cargar_sepa()` — streaming a disco + chunked CSV + float32 (precios SIN divisor) |
| 8 | code | Carga las 2 partes + consolidar por (producto × sucursal) + autodetección `FACTOR_PRECIO` + parquet cache |
| 9 | code | Verificación de escala de precios (top 10 productos por n_sucursales) |
| 10 | md | Header sección maestros |
| 11 | code | Carga `Maestro de Productos` → `df_prod_uniq` |
| 12 | code | Carga `maestro_sucursales_completo` → `df_suc_maest` y `maestro-provincias` → `df_provincias` |
| 13 | md | Header sección enriquecimiento |
| 14 | code | **Anti-OOM — celda clave**: merge con geografía + nombre cadena (vectorizado) → `df_suc_enr` → agrega inmediatamente a `df_cov` (producto × cadena × provincia) + `df_price_stats` (producto) + `_cad_agg`; `del df_suc_enr` |
| 15 | code | Distribución por cadena comercial y por región (desde `df_cov`) |
| 16 | code | Top 20 productos más reportados (desde `df_cov`) |
| 17 | md | Header sección análisis de cobertura |
| 18 | code | Agrega `df_cov` → `df_cob` (nivel producto); merge con `df_price_stats` y `_cad_agg`; calcula `score_cobertura` |
| 19 | code | Histogramas de distribución de cobertura |
| 20 | code | Filtros candidatos → `candidatos`, `cand_con_maestro` |
| 21 | code | Heatmaps top-40 × cadena y × provincia (desde `df_cov`); `del df_cov` |
| 22 | md | Header sección canasta |
| 23 | code | `GRUPOS_CANASTA` + `seleccionar_grupo()` + construcción `df_canasta` |
| 24 | code | Print canasta por grupo |
| 25 | code | Gráficos: barras de cobertura por grupo + dispersión de precios |
| 26 | md | Header sección exportación |
| 27 | code | Export Excel: hoja Canasta (colores por grupo) + hoja Candidatos + hoja Selección (candidatos ordenados + columna `cantidad` vacía en amarillo, fuente del próximo notebook) |

---

## Arquitectura anti-OOM (desde commit fd5e014)

El diseño clave está en **cell-14**. El problema original era que `df_enr` (~50M filas × 20 columnas, ~10 GB) permanecía en memoria durante 7 celdas.

```
df_suc (~50M filas, ~6 GB)
    ↓ merge geo (sucursal → PROVINCIA, REGION)
    ↓ normalización PROVINCIA_NOMBRE
    ↓ nombre_cadena vectorizado
    ↓ drop columnas innecesarias
df_suc_enr (~50M filas, ~7 GB)   ← pico de RAM aceptable
    ↓ groupby → df_price_stats (precio por producto, ~170K filas)
    ↓ groupby → df_cov (producto × cadena × provincia, ~2M filas)
    del df_suc_enr; gc.collect()  ← RAM: ~10 GB → ~600 MB
df_cov (~2M filas) + df_price_stats (~170K filas)
    ↓ todas las celdas 15-27 trabajan sobre estos frames pequeños
```

**Por qué funciona**: el peak de RAM (~7 GB para `df_suc_enr`) se libera inmediatamente. Los groupby posteriores operan sobre 2M filas en lugar de 50M.

---

## Configuración actual (mayo 2026)

```python
SEPA_SOURCE   = 'mi_drive'
SEPA_DIR      = '/content/drive/MyDrive/carga'
OUTPUT_DIR    = '/content/drive/MyDrive/carga/output_canasta'
SEPA_ZIP_NAME = '2026A.zip'
PERIODO       = '2026-04'

MIN_CADENAS    = total_cadenas     # dinámico — TODAS las cadenas activas
MIN_PROVINCIAS = total_provincias  # dinámico — TODAS las provincias activas
MIN_SUCURSALES = 50
MIN_PCT_DIAS   = 0.50
USE_CACHE      = True
```

---

## Score de cobertura

```python
score_cobertura = (pct_cadenas * 0.5 + pct_provincias * 0.5) * pct_dias_promedio
```

Donde:
- `pct_cadenas` = n_cadenas / total_cadenas (total de `id_bandera` únicos en el dataset)
- `pct_provincias` = n_provincias / total_provincias (total de provincias únicas en el dataset)
- `pct_dias_promedio` = promedio de `pct_dias` por celda (producto × cadena × provincia) en `df_cov`

---

## Output Excel

`canasta_representativa_{PERIODO}.xlsx`:
- **Canasta**: ~60 productos coloreados por grupo (11 grupos), encabezado azul marino `#1F4E79`
- **Candidatos**: ~41K productos, para el economista

Columnas completas:
```
periodo, grupo_canasta (*),
id_producto, descripcion, marca, presentacion, unidad,
rubro, categoria, subcategoria (*),
n_cadenas, n_cadenas_com, n_provincias, n_sucursales,
pct_dias_promedio,
precio_mediano, precio_p25, precio_p75,
score_cobertura,
cadenas_presentes
```
`(*)` = solo en la hoja Canasta / solo en la hoja Candidatos respectivamente.

---

## Métricas de ejecución real (abril 2026, commit fd5e014)

Primer run completo post-fix anti-OOM. Sin crashes. Resultados observados:

| Métrica | Valor |
|---------|-------|
| `df_cov` (nivel producto × cadena × provincia) | 2,686,965 filas × 8 cols |
| `df_price_stats` (nivel producto) | 98,720 filas × 5 cols |
| Grupos corporativos activos (`id_bandera` únicos) | 5 |
| Provincias activas | 24 |
| Productos que pasan todos los umbrales | 3,776 |
| Productos con maestro completo (`cand_con_maestro`) | 3,650 |
| Productos en canasta final | 54 |
| Cadenas comerciales identificadas nominalmente | 15 (de 33 activos) |
| Cadenas sin nombre en diccionario ("Comercio X") | 18 |

### Hallazgos post-primera ejecución (bugs identificados — ya resueltos)

**Grupo Lácteos = 0 productos (BUG-6 → ✅ Resuelto)**
Las kw anteriores no matcheaban `categoria='Lácteos'` (string literal en el maestro). Fix: `kw=['lácteos','lacteos']`.

**Contaminación de grupos (BUG-7, BUG-8 → ✅ Resueltos)**
- `categoria='Conservas'` incluye frutas Y carnes enlatadas → fix: `excluir_subcat=['Patés y Picadillos','Conservas de Pescado']`
- `categoria='Fiambrería'` incluye fiambres Y quesos untables → fix: `excluir_subcat=['Quesos Untables',...]`

**Bebidas incompletas (BUG-9 → ✅ Resuelto)**
Yerba/té/café viven en `rubro='Almacén'`, `categoria='Infusiones'`. Fix: añadir `'Almacén'` a los rubros de Bebidas no alcohólicas.

**`'carne'` ≠ substring de `'Carnicería'` (BUG-11 → ✅ Resuelto)**
Los 13 candidatos de `categoria='Carnicería'` (embutidos curados) no aparecían porque `'carne' in 'Carnicería'` → `False`. Fix: añadir `'carnicería','carniceria'` a las kw.

**id_producto exportado como entero (BUG-10 → ✅ Resuelto)**
~93 EANs cortos perdían sus ceros iniciales. Fix: `str.zfill(13)` en cell-27 antes del export.

**Cadenas comerciales activas (de los 5 grupos corporativos)**:
Con el diccionario `(id_comercio, id_bandera)`, los 5 grupos corporativos se mapean a banners reales. Los 18 "Comercio X" son comercios minoristas fuera del conjunto principal (algunos con precios atípicos ~$550k–$820k, probablemente especialidades o importados).

### Hallazgos de revisión del Excel de salida

**Productos no alimentarios en Candidatos**:
~37 productos (impresoras, TVs, electrodomésticos, artículos de Bazar) superan los umbrales de cobertura porque se venden en supermercados a nivel nacional. No son bugs — los umbrales son por cobertura, no por categoría. El economista debe filtrarlos manualmente o se puede agregar un filtro por `rubro not in ['Bazar','Electrónica','Limpieza del Hogar']`.

**EAN duplicados en Candidatos**:
~14 pares de `(descripcion, marca)` idénticos con distinto `id_producto`. Son SKUs diferentes (distinto packaging, gramaje, o presentación con código propio). Precio puede diferir ~5–10%. No son bugs — el EAN distingue variantes.

**Contenido real de `categoria='Carnicería'`**:
Los 13 productos son **embutidos curados** (Leberwurst, Salamín, Bondiola, Paleta), NO carnes frescas. Las carnes frescas no tienen cobertura nacional suficiente para superar los umbrales dinámicos (MIN_CADENAS=5, MIN_PROVINCIAS=24).

---

## Canasta ICR — Composición vigente (51 productos, revisada 2026-05-29)

La canasta fue construida a partir de la hoja `Selección` del nb01 y revisada en base a trazabilidad temporal y cobertura. Se reemplazaron 4 productos con baja trazabilidad por alternativas con 100% de presencia desde enero 2024.

| Categoría | EAN | Producto | Qty/mes |
|-----------|-----|----------|---------|
| Lácteos | 7790742363008 | Leche La Serenísima Entera 1L | 20 |
| Lácteos | 7793940054006 | Manteca La Serenísima 200g | 2 |
| Lácteos | 7790742625304 | Dulce de Leche La Serenísima 400g | 2 |
| Lácteos | 7791337061361 | Queso Crema Casancrem 290g | 2 |
| Lácteos | 7791337007611 | Yogur Firme Frutilla Yogurisimo 190g | 8 |
| Cereales | 7790070337009 | Fideos Tallarines Lucchetti 500g | 4 |
| Cereales | 7790070336293 | Fideos Tirabuzón Matarazzo 500g | 4 |
| Cereales | 7791120031557 | Arroz Molinos Ala 1kg | 2 |
| Cereales | 7792180139320 | Harina Cañuelas 1kg | 2 |
| Cereales | 7790040143234 | Galletitas Chocolinas 262g | 2 |
| Cereales | 7622201735258 | Galletitas Oreo 354g | 1 |
| Cereales | 7790070621801 | Ravioles La Salteña 900g | 2 |
| Aceites | 7790070012050 | Aceite Girasol Cocinero 900ml | 3 |
| Azúcar y dulces | 7792540250450 | Azúcar Ledesma 1kg | 2 |
| Azúcar y dulces | 7793360131516 | Mermelada Durazno La Campagnola 390g | 2 |
| Azúcar y dulces | 7793360131530 | Mermelada Frutilla La Campagnola 390g | 1 |
| Infusiones | 7790387013610 | Yerba Taragüí 1kg | 2 |
| Infusiones | 8445291082199 | Café Dolca 100g | 2 |
| Infusiones | 7790387800142 | Té Taragüí 50 saquitos | 1 |
| Bebidas | 7790895000232 | Coca Cola Lata 354cc | 6 |
| Bebidas | 7790895000270 | Sprite 2.25L | 4 |
| Bebidas | 7790895001017 | Fanta 2.25L | 2 |
| Bebidas | 7790895640476 | Aquarius Pera 1.5L | 4 |
| Condimentos | 7794000003408 | Mayonesa Hellmanns 320g | 2 |
| Condimentos | 7794000006485 | Mostaza Savora 500g | 1 |
| Condimentos | 7794000006188 | Ketchup Hellmanns 250g | 1 |
| Condimentos | 7791004000051 | Sal Celusal 1kg | 1 |
| Condimentos | 7792900093246 | Vinagre Dos Anclas 1L | 1 |
| Condimentos | 7794000008533 | Caldo Knorr 12 un | 1 |
| Proteínas | 7798092353731 | Huevos Carnave Cartón 6 un | 4 |
| Proteínas | 7790360967411 | **Hamburguesas Swift XL 250g** ← nuevo | 4 |
| Proteínas | 7790580131357 | Atún La Campagnola 170g | 3 |
| Proteínas | 7790079018367 | Leberwurst Paladini 200g | 2 |
| Tomate/legumbres | 7790580138868 | Puré de Tomate La Campagnola 530g | 3 |
| Tomate/legumbres | 7790580567101 | Tomate en lata Arcor 400g | 2 |
| Tomate/legumbres | 7793360132483 | Porotos Alubia La Campagnola 300g | 2 |
| Limpieza | 7793253003784 | **Lavandina Anti-splash Ayudín 2L** ← nuevo | 2 |
| Limpieza | 7791290794061 | Detergente Cif 500ml | 2 |
| Limpieza | 7791290792074 | Jabón Polvo Ala 3kg | 1 |
| Limpieza | 7793253005221 | Desinfectante Ayudín 500ml | 1 |
| Limpieza | 7790990001790 | Jabón Zorro 150g | 4 |
| Limpieza | 7790117000231 | Bolsas Residuos Asurín 30 un | 2 |
| Higiene | 7790990000830 | **Jabón Plusbelle 125g** ← nuevo | 4 |
| Higiene | 7509546686516 | Crema Dental Colgate 180g | 2 |
| Higiene | 7891010255275 | **Listerine Antisarro 500ml** ← nuevo | 1 |
| Higiene | 7791293050607 | Desodorante Axe 230ml | 1 |
| Higiene | 7791293048505 | Antitranspirante Dove 150ml | 1 |
| Higiene | 7791070000696 | Papel Higiénico Campanita 4x120m | 3 |
| Higiene | 7791290793606 | Suavizante Comfort 1L | 2 |
| Extra | 8445291121904 | Cacao Nesquik 800g | 1 |
| Extra | 7790580138721 | Polenta Prestopronta 730g | 2 |

**4 reemplazos vs. versión anterior** (criterio: trazabilidad + cobertura + masividad):
- Paty 250g (82.1%, nuevo jun-2024) → **Swift XL 250g** (100%, score 0.925)
- Lavandina Ayudín Original 2L (75%, nuevo ago-2024) → **Lavandina Anti-splash Ayudín 2L** (100%, score 0.919)
- Jabón Dove 90g (82.1%, nuevo jun-2024) → **Jabón Plusbelle 125g** (100%, score 0.994)
- Plax 250ml (82.1%, genuinamente inestable) → **Listerine Antisarro 500ml** (100%, score 0.949)

**Trazabilidad de la canasta** (28 meses ene-2024 → abr-2026): promedio 99.4%, 48/51 al 100%.

---

## Métricas Notebook 02 — Ejecución con canasta revisada (abril 2026, canasta con 4 reemplazos)

| Métrica | Valor |
|---------|-------|
| Costo ICR promedio nacional | **$478.836 ARS** |
| Rango por sucursal | $440.012 – $528.014 |
| Provincia más barata | Chaco ($463.679, -3.17%) |
| Provincia más cara | Santa Cruz ($507.864, +6.06%) |
| Sucursales válidas (≥15 productos propios) | 2.372 |
| Cadenas con datos | 16 |
| Provincias con datos | **24** (San Juan ahora aparece — BUG-15 confirmado resuelto) |
| Cadena más cara | La Anónima ($496.634) |
| Cadena más barata (ranking nacional) | Hipermercado Libertad ($451.972) |
| Barrio CABA más barato | Villa Soldati ($477.650, -1.09% vs CABA) |
| Barrio CABA más caro (ranking) | Recoleta ($485.969, +0.63% vs CABA) |
| Meses en serie histórica | 28 (2024-01 → 2026-04) |
| Costo ICR vs IPC General abr-2026 | +3.10% ICR vs +2.58% IPC |
| Cache parquet | `hist_0a6651c5.parquet` |

### Ramp-up de la serie histórica (por qué 48→51 EANs)

La serie empieza con 48 EANs en enero 2024 porque 3 productos de la canasta entraron al SEPA durante 2024:

| Producto | Entró | Meses (de 28) | Trazabilidad |
|----------|-------|--------------|--------------|
| Galletitas Chocolinas 262g | feb-2024 | 27 | 96.4% |
| Puré de Tomate La Campagnola 530g | mar-2024 | 26 | 92.9% |
| Cacao Nesquik 800g | jun-2024 | 23 | 82.1% |

Los 4 reemplazos (Swift XL, Lavandina Anti-splash, Plusbelle, Listerine) están todos al 100% desde enero 2024 — confirmado.

---

## Historial de cambios

### 2026-10-26 (cierre, más tarde) — nb06: líneas y penne de la misma marca

El usuario preguntó si los productos y las canastas están bien elegidos (`docs/AUDITORIA_SELECCION_2026-10-26_nb06.md`
§9). Respuesta: lo que más pesa está bien (etiqueta ANMAT, identidad y continuidad verificadas); se pueden mejorar
decisiones de diseño. Pidió las dos primeras (BRECHA_CELIACA §14.16):

- **Líneas**: los sabores de una misma marca y presentación que cuestan lo mismo entran una vez en la mediana de su
  lado (columna `linea` del CSV; 10 líneas con 32 de los 67 productos; Terrabusi Anillos y Boca de Dama difieren 36% y
  siguen separados).
- **Penne contra la misma marca**: el Matarazzo común en lugar de los Mostacholes Lucchetti, como en spaghetti.

Canasta de 67 productos en 45 líneas (80 códigos), simulación `sim_v8` (`s12` igual) y esperados
`simulacion_2026-10-26d/`. Resultados:

- Fideos +132% (antes +161%): penne +111% y tirabuzón +197%.
- Saladas +78% (antes +84%); saborizadas +19%.
- Canasta de los últimos 12 meses +100% (antes +111%); TPD de oct-2026 +98% a +100%.
- Carrefour y Cencosud a 0,5 pp (antes 4,5).

Los 15 tests en OK. Falta la corrida de Colab, que relee los 58 meses (caché `brecha_v3_d5183015`). Quedan para el
usuario las galletas de arroz, las vainillas, los pesos de los subtipos y una canasta de oferta actual.

### 2026-10-26 (cierre de la noche) — nb06: TPD del panel, Pepitos y las dos Operas

Se aplicaron las tres primeras recomendaciones de la revisión (BRECHA_CELIACA §14.15):

- **TPD del panel**: el subtipo-mes sin pares se mueve con el mismo subtipo en todas las sucursales (oct-2023:
  spaghetti −38% → +93%). Test con 31 controles.
- **Pepitos 119 g** (empalme de tres códigos, verificado con precios) reemplaza a Par Nor en con chips.
- **Obleas**: la Opera de 92 g junto a la de 220 g. Con la de 92 g sola, 2023 quedaba casi sin pares.

Hubo una relectura con 123 códigos (`sim_super_v10`). Canasta de 67 productos (80 códigos), simulación `sim_v7`
(`s12` igual) y esperados `simulacion_2026-10-26c/`. Resultados:

- Con chips +29% contra Pepitos (antes +111% contra Par Nor).
- Galletitas dulces +87% (antes +108%).
- Canasta de los últimos 12 meses +111% (antes +118%).
- TPD de oct-2026 +107% a +108%.

Falta la corrida de Colab, que relee los 58 meses.

### 2026-10-26 (noche) — nb06: corrida de Colab con la canasta corregida y revisión de los resultados

La corrida de Colab con la canasta corregida es idéntica a la simulación `sim_v5`: Excel (35 hojas contra
`simulacion_2026-10-26b`, 38 contra la simulación), mapa, caché y salida (AUDITORIA_2026-10-26 §8). El usuario pidió
revisar si los productos y la metodología están bien o se pueden mejorar (`docs/AUDITORIA_SELECCION_2026-10-26_nb06.md`
§7, scripts `r29`-`r31`). Hallazgos:

- **TPD del panel en oct-2023**: el spaghetti sin pares, movido con los demás subtipos, da −38%. La propuesta es
  moverlo con el mismo subtipo en todas las sucursales: +93% y canasta +122%.
- **Con chips es frágil**: Pepitos está donde están las chips Smams; Par Nor, no.
- **Saladas**: la TPD queda 4 a 24 pp debajo de la descriptiva por mezclar galletas de arroz y crackers.
- **Cadenas**: solo dos empresas confiables; hace falta la hedónica con interacciones para cadenas y concentración.
- **Saladas a fines de 2022**: la caída es real (ajustes escalonados de Criollitas y Saladix).

Recomendaciones priorizadas en ese documento (decisión del usuario).

### 2026-10-26 (auditoría de la selección) — nb06: canasta corregida (BUG-49)

El usuario pidió asegurarse de que la selección de productos estuviera bien hecha (con la carpeta `carga` del Drive):
`docs/AUDITORIA_SELECCION_2026-10-26_nb06.md`, con los scripts `r20`-`r28`.

**Etiqueta sin TACC.** Se contrastó con el listado ALG de ANMAT. Ningún con TACC está etiquetado sin TACC y los sin
TACC son de marcas celíacas o están registrados. Lasfor no tiene registro; Snuks es su línea sin TACC.

**Cuatro errores de las reglas de s9**, corregidos a pedido del usuario:

1. `tita\b` atrapaba "galletita".
2. Blue Patna es pasta al huevo.
3. El tirabuzón sin TACC Matarazzo quedaba afuera por el cambio de código de Molinos.
4. Dos sabores de Lasfor quedaban afuera por un comercio.

La canasta queda en **66 productos (77 códigos)**.

**Simulación** con los 58 meses releídos (`sim_v5`; `s12` igual); esperados nuevos en
`docs/brecha_celiaca/simulacion_2026-10-26b/`.

- Fideos: +172,3% → +160,6%. Canasta de los últimos 12 meses: +122,7% → +118,0%.
- ChangoMas deja de ser confiable: su +140% venía de los Blue Patna.
- Se miden 2.324 sucursales (antes 2.175).
- El penne queda imputado 16 meses en todas las sucursales.
- La TPD del panel en oct-2023 pasa de +174% a +114%, pero sigue siendo un artefacto (spaghetti sin pares movido con
  los demás subtipos: −38%).

Quedan cuatro propuestas de diseño para decidir: obleas, crackers contra galletas de arroz, empalme de Pepitos y otros
líderes con TACC, y vainillas. Falta la corrida de Colab: relee los 58 meses.

### 2026-10-26 (cierre) — nb06: revisión de datos y método frente al objetivo

La cuarta corrida de Colab (con los gráficos corregidos) dio igual a la simulación `sim_v4` en todo. El usuario
pidió revisar datos y método frente al objetivo (cuánto más paga un celíaco, evolución, geografía, concentración,
cadenas): `docs/REVISION_METODOLOGICA_2026-10-26_nb06.md`, con los scripts `r16`-`r19`. Hallazgos: la prima mide envasados de primera marca en súper (+120% a +125%; +154% con cantidades de la CBA, +$19.000 por adulto equivalente por mes sin pan ni harina); el panel no tiene a DIA; los pesos de los subtipos mueven la evolución (2024: −10 pp); la brecha se amplió 7% relativo 2022-2026 (sin TACC ×14,7 contra ×13,7); Patagonia tiene la menor disponibilidad; la concentración no muestra efecto ni dentro de cada empresa, pero sí mueve uno u otro lado del cociente; las diferencias entre cadenas se amplían por tipo. Recomendaciones priorizadas en
ese documento (decisión del usuario).

### 2026-10-26 — nb06: segunda corrida de Colab revisada (BUG-47 y serie TPD)

El usuario corrió el nb06 vigente (`46e426b`) en Colab y pasó la salida impresa, el Excel, el mapa y el zip del caché
del Drive. Revisión (`docs/AUDITORIA_2026-10-26_nb06.md`): **idéntica a la simulación local en todo** —35 hojas contra
los esperados (`s16`), las 38 hojas celda por celda contra el Excel de la simulación (`r13`), el mapa salvo los
identificadores de Folium (`r15`), las 169 líneas de la salida impresa y el caché (57 meses, mismos datos; `r14`)—:
BUG-47 y la serie TPD quedan verificados en Colab. Hallazgos menores: dos tiendas online (DIA "eCommerce" en CABA y la
"Dark Store Mendoza" de Libertad) pasan el filtro de sucursales web porque el maestro les pone tipo Supermercado o
Autoservicio (no están en el panel; < 0,3 pp en la serie de todas salvo crackers de sep-2023, 3,3 pp) y las columnas
`dif_tpd_menos_descriptiva_*_pp` de `Serie_TPD` sin formato. Arreglarlos no relee pero pide otra corrida de Colab:
decisión del usuario. Scripts nuevos `r13`-`r15`.

El usuario pidió arreglarlos (**BUG-48**): `SUCURSALES_NO_FISICAS` en la CELDA 1 saca por el nombre las tiendas
online que el maestro carga con otro tipo (6 en el maestro, 2 con precios; probado contra los 3.611 nombres) y la
CELDA 7 imprime cuáles; las columnas `_pp` de `Serie_TPD` tienen formato. Test con una tienda online sintética (30
controles); simulación `sim_v3`: el panel no cambia y la serie de todas las sucursales, como mucho 0,30 pp en un mes.
Esperados nuevos en `docs/brecha_celiaca/simulacion_2026-10-26/` (35 hojas). Esa tarde el usuario corrió el notebook
con BUG-48 en Colab: igual a la simulación en el Excel (35 hojas contra los esperados, 38 contra `sim_v3`), el mapa,
las 170 líneas de la salida impresa y el caché (AUDITORIA_2026-10-26 §6). En los 11 gráficos quedaron tres detalles
de presentación (barras de sucursales encima de las líneas en `brecha_mensual`, grilla que tacha las etiquetas de
las barras horizontales, ticks redondeados de almohaditas en `brecha_tpd_tipos`). Esa noche, a pedido del usuario,
se corrigieron en la CELDA 9 (helpers `_pct` y `_barras_horizontales`, eje de las sucursales debajo del de la
brecha); el Excel no cambia (simulación `sim_v4`: 35 hojas iguales a los esperados). Falta re-correr en Colab para
tener los PNG nuevos.

### 2026-10-23 (noche) — nb06: serie TPD (hedónica) de la brecha

Pedido del usuario: implementar la TPD/hedónica de BRECHA_CELIACA §3.9 como serie de robustez frente a la imputación de
subtipos, con simulación y test. **CELDA 8b** nueva: una regresión por subtipo, `ln p = α(celda sucursal-mes) +
γ(producto) + β(mes)·sinTACC`, mínimos cuadrados ponderados con los efectos de celda descontados (exacto, matrices
dispersas); nivel con los efectos de producto pesados por su disponibilidad; tipo geométrico y canasta ENGHo como la
descriptiva; errores agrupados por sucursal con la covarianza entre subtipos y tipos; dos universos (panel balanceado y
todas las sucursales). No arrastra: usa los subtipo-mes que la descriptiva imputa y solo con menos de 10 sucursales con
los dos lados mueve el subtipo con los demás de su tipo (25 subtipo-mes en el panel y 12 en todas, contra 57 y 70 que
arrastra la descriptiva; `peso_movido_pct`). Se descartó el efecto de sucursal-mes del tipo entero (la evolución de las
galletitas con chips salía al revés). Hojas `Serie_TPD`, `Brecha_tipo_TPD`, `TPD_subtipos`, `TPD_anual` y
`TPD_productos` (38 hojas) y dos gráficos; test con 30 controles; con los datos reales, igual a un LSQR independiente
(`r10`). Lectura (§14.12): con dato propio las dos series coinciden (diferencia mediana 3 pp); saladas queda 8-18 pp
debajo en 2024-2026 (crackers con dos niveles de prima y surtido de snacks); en todas las sucursales el pico de oct-dic
2023 es menor (+137% a +148% contra +161% a +170%: imputación de la descriptiva) y los fideos del panel de jun-2023 →
feb-2024 tienen tan pocas sucursales que ninguna de las dos series los mide bien. Esperados:
`docs/brecha_celiaca/simulacion_2026-10-23b/` (35 hojas). Falta re-correr en Colab (no relee el SEPA).

### 2026-10-23 (tarde) — nb06: primera corrida de Colab revisada y BUG-47

El usuario corrió el nb06 con la canasta fija en Colab y pasó la salida impresa, el Excel y el mapa. Revisión
(`docs/AUDITORIA_2026-10-23_nb06.md`): **la corrida es idéntica a la simulación local** (`s16_comparar_colab.py`: 29
hojas iguales, diferencia máxima 1,4e-13), así que la canasta y el estimador quedan validados en Colab; lo de §14.9 da
lo esperado. Al leer los resultados aparecieron tres salidas que mezclaban composición (**BUG-47**, corregido sin
releer el SEPA): (1) provincias, regiones, empresas y cadenas comparaban grupos con distintos subtipos (una cadena sin
snacks quedaba con la brecha de los crackers sola: Coto +141,7%, La Anónima +131,8%) → ahora la misma canasta de 12
subtipos en todos, con la brecha nacional del período en los subtipos sin datos en el grupo (`peso_imputado_pct`;
confiable = <= 25% imputado y >= 30 sucursales): 8 provincias, 6 regiones, 3 empresas y 7 cadenas comparables; (2) el
mapa por sucursal coloreaba según cuántos tipos tiene cada sucursal (DIA, con 2, salía en +77%) → canasta comparable
con `peso_propio_pct`; (3) la "concentración" agrupaba por un campo de localidad que DIA carga con el nombre de la
provincia (la correlación −0,26 era DIA) → HHI de empresas por departamento de Georef (caché del nb09): Spearman −0,11,
sin relación. Además: hoja `Imputaciones`, gráficos con los meses imputados marcados, gráfico por cadena. Las series
nacionales y la brecha por tipo no cambian. Test con 26 controles; simulación con el caché (4,9 min, 2,4 GB) y
esperados nuevos en `docs/brecha_celiaca/simulacion_2026-10-23b/`. Queda abierta para el usuario la imputación sin
límite de la serie mensual (rachas de 7-14 meses en 2023-2024 y 9 meses en galletitas con chips en 2025-2026); la
recomendación es pasar a la TPD/hedónica (BRECHA_CELIACA §3.9) en vez de cambiar la regla. Los zips del Drive están
ahora en `C:\Users\sriverti\Downloads\carga\`.

### 2026-10-23 — nb06: canasta fija 2022-2026 de la brecha celíaca

Pedido del usuario: elegir, con las salidas del nb09 (trazabilidad al 22/10/2026), productos con TACC y sin TACC con
continuidad temporal, geográfica y por cadenas para medir la brecha y cómo se distribuye en el tiempo, la geografía y
las cadenas; dejar el nb06 listo para correr en Colab sin que colapse la RAM. Hecho: **68 productos (80 códigos)** en 5
tipos y 12 subtipos con la misma composición de los dos lados (`docs/brecha_celiaca/canasta_fija_2022_2026.csv`, que
`gen_nb06.py` embebe en la CELDA 1 como `TIPOS`, `GRAMOS`, `VIGENCIA`, `PRODUCTO` y `SUBTIPO`), pesos ENGHo 2017/18, y
BUG-46 (provincia por polígonos, archivo duplicado de ago-2024, estaciones de servicio y farmacias afuera, nombres
oficiales, caché por mes, mediana exacta, canasta que dependía del maestro del Drive, códigos viejos con precio
congelado). Reglas y fundamentos: `docs/BRECHA_CELIACA.md` §14; scripts s1-s15 en `docs/auditoria/scripts_nb06_2026-10/`.
La verificación con los precios de **2022-2023** (zips del Drive que bajó el usuario) corrigió la primera selección:
los sin TACC viejos de Matarazzo eran genuinos (costaban 2-3 veces el común en las mismas sucursales) y entran
empalmados; Wakas pasó de la bolsa de 250 g a la caja de 300 g; Porteñitas, Maná 165 g y Scons 9 de Oro afuera; el
control de estabilidad dejó de encadenar medianas (marcaba a casi todos con 58 meses). Hallazgo: en 2023 los productos
con TACC de marcas masivas tenían precios controlados y salieron en oct-2023 (Molinos, con códigos nuevos a 2,5-3,4
veces el precio viejo) y ene-2024 (el resto, +87-118%): la brecha de 2023 está inflada por eso (§14.8). Al simular
el nb06 con los 58 meses se cambió el estimador: la brecha se calcula **por subtipo** dentro de cada sucursal (la
mediana del tipo entero mezclaba snacks con crackers según el surtido: saladas +26,5% contra +165% crackers y +28%
snacks) y se agrega como un índice de precios (subtipo → tipo, promedio geométrico → canasta ENGHo; subtipo-mes con
pocas sucursales imputado con el mes anterior), con la mitad o un tercio del ruido mensual; y se vectorizó el "más
barato" (CELDA 7: de 11 min a 23 s). Test `test_brecha_celiaca.py` (22 controles). Simulación de las celdas reales con
los 58 meses del Drive contra un cálculo independiente: coincidencia exacta (3,4 millones de precios, 534.456 brechas
por subtipo); lectura 37 min en la PC, pico de RAM 2,5 GB. Brecha por tipo 2022-2026: fideos +172%, galletitas dulces
+108%, saladas +84%, rebozador +84%, almohaditas +26%; canasta (panel) +111% en 2022, +106% en 2023, +107% en 2024,
+100% en 2025 y +120% en 2026; regiones y cadenas confiables entre +119% y +127% en los últimos 12 meses (§14.10).

### 2026-10-23 (cierre) — documentación al día para retomar en otra PC

Pedido del usuario: dejar memoria, contexto, documentación técnica y README al día para seguir en otra sesión y otra
PC. Agregado: resultados esperados del nb06 en el repo (`docs/brecha_celiaca/simulacion_2026-10-23/`, un CSV por hoja
del Excel de la simulación con los zips del Drive) y `s16_comparar_colab.py` para comparar una corrida de Colab hoja
por hoja (probado contra la simulación: 29 hojas iguales, y con una diferencia sembrada); `seaborn` en
`requirements.txt` (lo importa el nb06 y faltaba: el test fallaba en una PC nueva); nota del estimador vigente en
BRECHA_CELIACA §3 y su encabezado; README (árbol, documentación, nb06), CLAUDE.md (datos de la PC, cachés del nb06,
reglas de la brecha), bloque ESTADO ACTUAL de `.claude/memory.md`. El trabajo intermedio del nb06 (~315 MB) quedó en
`C:\Users\sriverti\proyectos\nb06_brecha_celiaca_20261023\` (fuera del repo, README adentro). 15 tests en OK.

### 2026-10-22 (cierre) — documentación al día para retomar en otra PC

Pedido del usuario: dejar memoria, contexto, documentación técnica y README al día para seguir en otra PC y otra
sesión. Sin cambios de código: `requirements.txt` completo (faltaban `xlsxwriter`, `scipy`, `psutil` y
`python-calamine`, que usan los tests del nb08/nb09 y los scripts de la canasta y de la revisión del nb09), los 14 tests
en OK; `docs/PASS_THROUGH.md` nuevo (estado, cómo correr el nb08 y qué revisar, la canasta y cómo rehacerla, variable
de precio, advertencias, próximos pasos); `docs/METODOLOGIA.md` §12 (nb08 v2), §13 (nb09) y §14 (canasta de
pass-through); `docs/SEPA_TECNICO.md`, "Defectos y cambios de la fuente 2022-2026"; README (preguntas, datos en el Drive
con 2022-2023 y `output_trazabilidad/`, árbol, tests y documentación); bloque ESTADO ACTUAL / HANDOFF general al
principio de `.claude/memory.md`; `CLAUDE.md`. Commits del día: `4ec771f` y `a3acfce` (nb09), `fa1144d` (canasta de
pass-through), `a1f4522` (nb08 v2) y el de esta documentación.

### 2026-10-22 (noche) — nb08 v2: canasta de pass-through por defecto y sucursales apareadas

Pedido del usuario: que el nb08 tome por defecto `cantidad_01` de `output_canasta/canasta_pass_through_2026-10.xlsx`
(ya en el Drive), con las correcciones sugeridas, y dejarlo listo para correr. `gen_nb08.py`: defaults, nombre
automático "Pass-through", `FECHA_FIN` (20/10/2026), un archivo por quincena (corrige el doble conteo del 1-5/08/2024),
lector por archivo, índice con **sucursales apareadas** por producto (relativos de la misma sucursal; si faltó unos días,
su precio anterior se mueve con el índice del producto, como imputa el IPC), `valor_canasta_apareado`,
`cobertura_incompleta`, índices por grupo del IPC, `Precios_apareados` y panel producto × día para regresiones. Caché
`diaria_v2_<clave>` con el estado de cada mes. Test `test_canasta_diaria.py` contra fuerza bruta (OK). Con datos reales
(jul-sep 2024, 775 productos, `docs/auditoria/scripts_nb08_2026-10/validar_real.py`): medianas y promedios idénticos al
lector anterior en 71.300 producto-días, observaciones distintas solo del 1-5/08/2024; ~1 min y 0,5 GB por mes (antes
~5 GB); apareado +8,97% vs medianas +9,07% en el trimestre, con un tercio del ruido diario.

### 2026-10-22 (noche) — canasta fija para el pass-through diario

Pedido del usuario: qué productos usar para estudiar el pass-through del tipo de cambio con datos diarios del
01/01/2022 al 20/10/2026, con la misma canasta todos los días y grupos para desagregar. Con las salidas del nb09 (al
22/10/2026) se armó `docs/canastas_alternativas/canasta_pass_through.py`: 9 reglas fijas (precio todos los días,
EAN del maestro, consumo masivo, ≥ 150 sucursales por día en cada mes, cobertura estable, ≥ 6 de 8 cadenas grandes,
24 provincias y ≥ 85% diario, CV ≤ 25%, una variedad por precio) → 775 productos en 16 grupos del IPC, con pesos IPC
(INDEC, por región y peso de las regiones) o iguales por grupo, y la columna `cantidad_08` para el nb08. Los fideos y el
arroz de Molinos, el azúcar Ledesma y otras marcas líderes quedan afuera porque su cobertura colapsa entre dic-2023 y
abr-2024. Detalle: README de `docs/canastas_alternativas/`.

### 2026-10-22 — nb09: corrida de la versión 2 revisada

El usuario corrió la v2 en Colab (115 archivos; los 114 del caché viejo se releyeron; lectura 63 min; notebook ≤ 1,3 GB
de RAM) y pidió una revisión exhaustiva. `docs/AUDITORIA_2026-10-22_nb09.md`; scripts en
`docs/auditoria/scripts_nb09_2026-10/`.
- **Correcto**: los seis errores del BUG-45 resueltos (24 provincias, HHI en rango, 0 productos con más sucursales
  promedio que distintas, `COMPLETOb`, `es_ean`, nombres); todos los controles internos OK en los 237.894 productos; el
  panel mensual = recálculo desde el SEPA crudo **exacto** en ene-24, ago-24, ago-25 y jul-26 (64-93 mil productos por
  mes) y lo que imprime la CELDA 4 por archivo, igual; el mínimo diario de sucursales = nb08 en los 28 de la Continua
  2022; may-jul 2026 = la muestra local de la v1.
- **Abiertos** (decisiones del usuario): el componente comercial premia comercios chicos, estaciones de servicio y
  Mercado Libre (limita 2.129 de los 2.496 productos ≥ 50); el regional satura; ago-oct 2026 vienen del SEPA diario
  (nb03) sin 8 comercios (3.254 productos con "último día" 31/07/2026 por eso); precios simbólicos; 12 códigos con
  basura de codificación; la regla de centavos vence hacia 2029.
- **Aplicado el mismo día** (pedido del usuario; no relee el SEPA): hoja `Dias` con los denominadores diarios y el
  archivo de cada día; comercios sin precios en el último mes (Resumen, `Cadenas.publica_en_el_ultimo_mes`) y la columna
  `solo_en_comercios_que_dejaron_de_publicar`; los códigos con texto mal codificado se unen a su EAN; columna
  `precio_simbolico` (≤ $10). Test sintético ampliado con esos casos (OK) y corrida real local jul-ago 2025: panel igual
  al de Colab.
- **Corrida con los arreglos** (datos al 22/10/2026, AUDITORIA §6): números iguales a la anterior en los meses
  cerrados; releyó todo (102 min) porque el caché no estaba en el Drive. La marca de comercios que dejaron de publicar
  vale en 65.123 productos (33 comercios desde 2022, Libertad hasta el 02/09/2026); el umbral de precio simbólico ($10)
  deja afuera ~25 precios de relleno de $10-100. Propuestas: `mes_baja_comercios` y umbral relativo (~$100).
- **Aplicadas** (pedido del usuario; no relee): `mes_baja_comercios` y `PRECIO_SIMBOLICO_PCT = 1.25` (% de la mediana
  de precios del último mes). Test sintético OK; corrida real local jun-sep 2024: panel igual al de Colab y la marca y
  el mes iguales al recálculo desde la hoja `Cadenas` (mostró que un hueco temporal en el último mes también cuenta como
  baja: ChangoMas sin precios en sep-2024).

### 2026-10-21 (tarde) — nb09: primera corrida completa revisada y versión 2

El usuario corrió el nb09 completo en Colab (115 archivos, 2022-01 → 15/10/2026, lectura 93 min, RAM estable: lector
~1,6 GB, ~11,8 GB libres) y pidió revisar los datos a fondo.
- **Validado contra el nb08** (cachés diarios de la Media y la Continua 2022, código independiente): días con precio por
  mes 3.366/3.366 y 1.596/1.596, primer día y mínimo diario iguales en los 97 productos; sucursales por día iguales
  salvo agosto 2024, donde el que se equivoca es el nb08 (suma dos archivos de la misma quincena). Precio del último mes
  igual a la mediana diaria del nb08 en 18 de 28 productos y a < 3% en casi todos los demás.
- **Errores encontrados y corregidos (versión 2)**: (1) HHI desbordado (int32) en 13.914 productos, 18.609 negativos;
  (2) 27 "provincias" (vacías y escritas con el nombre): el componente regional del puntaje quedaba mal en todos;
  (3) sucursal × producto repetidos en el SEPA (Cadena 2011 ene-feb 2024) contados dos veces; (4) dos archivos para la
  misma quincena (ago-2024): el nb09 eligió el bueno por el orden del zip, ahora por los días; (5) `es_ean` marcaba como
  EAN 221 códigos con guiones y 9.616 de balanza (EAN-13 que empiezan con 2); (6) nombres de comercios equivocados
  (47, 23, 4, 3...), coma dentro de "Cencosud (Vea, Disco, Jumbo)", rubros con variantes de mayúsculas, % con 2
  decimales. Además, por decisión del usuario, el componente comercial del puntaje pasa a la cuota diaria de comercios
  (los 50 comercios del período incluyen cadenas de pocos días y locales repetidos con otro código: 44/45/46, 49/50).
- **Probado**: test sintético con esos defectos contra fuerza bruta (OK); real local ene-feb 2024 (repetidas 1/892/874/1
  = las del escaneo de los zips), ago-2024 (elige `COMPLETOb`; con el nb08 corregido por su doble conteo, iguales) y la
  actualización del caché v1 de may-jul 2026. El puntaje se reproduce desde las columnas a ±0,006.
- **Escaneo de los 63 archivos locales 2024-2026**: 23 con filas repetidas, los 63 con la sucursal de DIA 'Buenos
  Aires': la próxima corrida en Colab relee casi todo (~1,5-2 h, una vez).

### 2026-10-21 — nb09: robusto para el Colab gratuito (la primera corrida colapsó la RAM)

El usuario corrió el nb09 en Colab y la sesión se cayó por falta de RAM; pidió que no pase en el Colab no premium
aunque tarde más. Cambios (sin cambiar ningún número):
- **Lector en un script aparte** (`nb09_lector.py`, escrito por la CELDA 4) ejecutado con `subprocess` por archivo:
  al terminar cada archivo el sistema libera toda su memoria (en un solo proceso la RAM crecía archivo a archivo). Se
  descartó `fork` porque pyarrow no es fork-safe.
- **Lectura por bloques** (`pacsv.open_csv`, `BLOQUE_MB = 32`): acumuladores producto × día, producto × comercio × día y
  producto × provincia × día que crecen con los códigos. Verificado en dos archivos reales que no hay sucursal ×
  producto repetidos (0 en 10,5 M y en 15,7 M de filas): sumar bloques es exacto.
- **Fase 2b por grupos de productos** (`N_GRUPOS = 16`, crc32 del código): `ean_suc` se escribe con un row group por
  grupo; la matriz producto × sucursal de todo el período nunca está entera. Un `ean_suc` del formato anterior se
  reorganiza solo la primera vez (no relee el SEPA).
- **Excel fila a fila** (xlsxwriter `constant_memory`). Cada celda imprime la RAM del proceso y la libre.
- Medido: archivos de julio 2026 (13-16 M filas): **lector 1,7 GB de pico, notebook 0,4-0,8 GB** (antes 5-10 GB);
  resúmenes idénticos a los de la versión anterior. May-jul 2026 con el caché viejo reorganizado: ranking idéntico en
  las 104.201 filas (salvo un redondeo de 0,01 en un CV); pico 2 GB (la reorganización).
- Test ampliado: bloques diminutos, 3 y 5 grupos, caché reorganizado, lector en el mismo proceso: todo igual a la
  fuerza bruta.

### 2026-10-20 (noche) — nb09: trazabilidad de todos los productos del SEPA

Pedido del usuario: un notebook que analice todos los productos únicos del SEPA desde 2022 y genere un ranking de
representatividad temporal, por sucursal, comercial y regional. Decisiones (las recomendadas, aceptadas por el
usuario): cuota diaria de sucursales como denominador principal (y también el total histórico); comercio y bandera;
departamentos por Georef; regiones INDEC con GBA = AMBA por coordenadas; todos los comercios (columna del universo
nb02); códigos internos incluidos y marcados; Colab; día útil = ≥ 100 sucursales y ≥ 5%; puntaje = media geométrica de
4 componentes iguales; solo zips semestrales.
- Medido: un archivo de medio mes de 2024 tiene 10,5 M de filas (60 mil productos, 3.150 sucursales); uno de 2026,
  ~16 M de filas (~90 mil productos/día, ~3.400 sucursales). pyarrow lo lee entero en 7-40 s.
- Primera versión: pico de RAM 9,7 GB en la lectura → IDs como diccionario (limpiar el diccionario, no las filas),
  precios float32, columnas liberadas al copiarlas, promedio en el lugar: **4,1 GB** (5,2 con el orden por producto) y resúmenes idénticos. Ordenar
  producto × sucursal por producto: parquet de 64 a 26 MB por archivo.
- Prueba real local may-jul 2026: 104.201 productos (95.285 EAN, 8.916 códigos internos, 76.473 en el maestro), 3.429
  sucursales, 26 comercios, 35 banderas, 25 provincias; 28.559 con precio todos los días; 7.556 con todos los días
  útiles; arriba Powerade, Saladix, Cindor, Aquarius, Celusal. Fase 1 ~40 s/archivo, fase 2 ~15 s/archivo.
- **Falta correrlo en Colab con 2022-2026** (estimado ~2-3 h la primera vez, ~3 GB de caché en el Drive).

### 2026-10-20 (tarde) — nb08: corrida de la Media revisada

El usuario corrió el nb08 en Colab con `CANASTA_COL = 'cantidad_03'` (Media) y pasó el Excel y el caché.

- Excel `canasta_diaria_media_20220101_20261015.xlsx` + caché `diaria_45cf0e5b/`: 58 meses (2022-01 → 2026-10 al 15/10),
  lectura 2.467 s (~42 s/mes), sin avisos de unidades ni saltos > ±15%; 2 días sin dato (31/10/2023, 10/05/2026).
  Ancla 15/10/2026 = $689.886; 01/01/2022 = $38.748 (valor de los 69 productos; los que faltan, por el encadenado).
- Cobertura: ene-22 37/69 productos (54-61% del valor), 2023 ~74%, 69/69 desde el 27/03/2024. Los 32 que entran
  tarde son sobre todo perfumería, limpieza, congelados y sin TACC: en 2022-23 la serie es almacén/bebidas/lácteos.
- Encadenado diario vs encadenado MENSUAL con productos apareados (desde el caché): ≤ +0,88% en todo el período
  (casi todo en ene-abr 2024, cuando entran los últimos productos).
- vs nb02 (Serie_precios, Media): desde abr-24 entre −0,4% y +0,4% (feb-25 −1,55%, sep-25 −0,91%: promedio de
  medianas diarias vs mediana del mes); ene-mar 2024 +2 a +6% (el nb02 suma solo los 66 con dato).
- vs IPC nacional (datos.gob.ar `148.3_INIVELNAL_DICI_M_26`, bienes `147.3_IBIENESNAL_DICI_T_19`, alimentos
  `146.3_IALIMENNAL_DICI_M_45`; promedios mensuales): 2022 +78,8% (IPC +87,5, alimentos +85,8); 2023 +166,5%
  (+211,4 / +251,3); 2024 +140,8% (+117,8 / +94,7); 2025 +26,5% (+31,5 / +32,2); ene-22 → ago-26 +1.597% (+1.929 /
  +1.952); abr-24 → ago-26 +80% (bienes +86, alimentos +99). Atraso en 2023 y salto en dic-23/ene-24 (+33,9% y
  +41,4% mensual vs IPC +25,5 y +20,6): lectura no verificada = precios acordados (Precios Justos) en productos de
  marca de supermercado liberados con la devaluación; además la canasta no tiene frescos.
- Scripts de la revisión: `revisar.py` (desvío, volatilidad, cobertura) y `comparar.py` (IPC, nb02, encadenado
  mensual) en el scratchpad de la sesión (no en el repo). No hizo falta tocar el notebook.

### 2026-10-20 — nb08: valor diario de una canasta desde 2022

Pedido del usuario: tomar la canasta `cantidad_01` del Excel `canasta_representativa` y devolver un Excel con su valor
diario de 2022 en adelante (subió `2022A/B.zip` y `2023A/B.zip` a `carga/`). Nuevo `notebooks/gen_nb08.py` →
`08_canasta_diaria.ipynb`. Método: mediana nacional por producto y día (universo de la CELDA 9 del nb02),
`valor_directo` y `valor_canasta` encadenado con productos apareados anclado en el último día completo; corrección de
unidades entre meses; caché por mes. Validado localmente con los zips de nov-25 → jul-26 (la Media como canasta de
prueba): promedios mensuales entre −0,42% y +0,11% de la serie del nb02; prueba de huecos (encadenado ≤ 0,23%) y de un
mes en centavos (detectado y corregido). **Falta correrlo en Colab con 2022-2023** (~1-1,5 h la primera vez).

### 2026-10-16 (cierre) — nb02: provincia de la CELDA 7 por polígonos (BUG-44 resuelto)

Pedido del usuario (con su OK al BUG-44): reclasificar la provincia sin los errores de borde. La CELDA 7 ahora usa los
polígonos de `ar.json` (el GeoJSON del mapa, en el Drive) con tolerancia `RECLASIF_TOL_KM = 100`: una sucursal cambia de
provincia solo si está a más de 100 km de la declarada y dentro del polígono de otra. Sobre el maestro: 12 reclasificadas
(antes 121, la mayoría mal), todas errores groseros de carga; el AMBA no cambia. Cuadro 1 de oct-26 recalculado con la
CELDA 8 real: país de la Media +0,01%; Neuquén 24 → 58 sucursales (−0,83%), La Pampa 55 → 19, Santa Fe 65 → 37
(+0,45%). La clave del caché de la econometría incluye ahora la provincia y la cadena de cada sucursal: **la próxima
corrida relee los 33 meses de la econometría y los 12 de la 19c, una vez**. Test `test_reclasificacion_provincia.py`;
scripts `reclasificacion_celda7.py` y `cuadro1_reclasificacion.py`; detalle en `docs/AUDITORIA_2026-10-16_nb02.md` §9 y
§11. El nb05 conserva los rectángulos (pendiente).

### 2026-10-16 (tarde) — nb02: región de la 19b/19c por coordenadas (BUG-43), Excel en verde, BUG-44 abierto (resuelto al cierre)

Pedido: la región de las CELDAS 19b y 19c con el AMBA por coordenadas, como la CELDA 7. Hecho: AMBA = columna `amba` de
la CELDA 7 y el resto por la provincia del archivo de precios. Simulado con las celdas reales sobre los zips locales
(ene-jul 2026) con el código viejo y el nuevo: 91 DIA del interior pasan de AMBA a Pampeana; todo lo que no es región,
idéntico al caché de la corrida de Colab. La primera versión usaba la provincia reclasificada de la CELDA 7 y la
simulación mostró que sus rectángulos pasan Neuquén capital a La Pampa y Paraná a Santa Fe: **BUG-44, abierto** (mueve
el Cuadro 1; no se tocó sin el OK del usuario). Pedido 2: el Excel `canasta_analisis` de azul a verde (`375623` y
`92D050`, CELDA 19); el Excel de oct-26 se recoloreó aparte. La próxima corrida relee 12 meses en la 19c (~35 min, una
vez). Scripts: `simular_region_19b_19c.py`, `comparar_region_19b_19c.py`, `reclasificacion_celda7.py`. Detalle en
`docs/AUDITORIA_2026-10-16_nb02.md` §8-10.

### 2026-10-16 — nb02: corrida de oct-26 revisada; AMBA, referencias y acumulados del documento técnico (BUG-42)

El usuario corrió el nb02 en Colab (oct-26 al 15/10). Las CELDAS 19b y 19c dieron lo validado (oficial +1,748%, medianas
69/69, `analisis_detallado` primera, 2.069 s la primera vez). La revisión encontró defectos previos en las CELDAS 16, 18
y 20, que alimentan el documento técnico: el "AMBA" de los rankings de cadenas era CABA + toda la provincia; los
acumulados comparaban la canasta a oct-26 (parcial) con el IPC a sep-26; había cuatro referencias de "país" distintas y
la CELDA 20 usaba promedios por cadena y barrio; 3 caras y 1 barata; dispersión mín-máx (38,8% por una sucursal
atípica); porcentajes con punto decimal y la prima celíaca con `abs()`. Arreglados: AMBA por coordenadas (≤ 90 km del
Obelisco), referencia única del Cuadro 1, medianas, acumulados en el mismo período, P5-P95, formato. Test nuevo
`notebooks/test_valores_documento.py` (falla en sus 19 chequeos con las celdas viejas). No relee nada: solo cambian
las CELDAS 7 (columna `amba`), 16, 18, 19 (vs país de `Ranking_*` y columna `amba` en `Sucs_*`) y 20 (commit
`d6e1f52`). Revisión completa, con los números antes/ahora simulados sobre los mismos datos, en
`docs/AUDITORIA_2026-10-16_nb02.md`; scripts nuevos en `docs/auditoria/scripts_nb02_2026-10/`. Ese día también se
commiteó el cambio del usuario al script 03 (carpeta de días y zip semestral A/B automático). **Verificado en Colab el
mismo día** con una segunda corrida: `Valores_Documento` idéntica a la simulación y solo cambiaron `Ranking_*` y
`Sucs_*` (`comparar_corridas.py`; AUDITORIA §7).

### 2026-10-15 — nb02: hoja `analisis_detallado` (CELDA 19c)

Pedido: una pestaña al principio del Excel `canasta_analisis_{PERIODO}.xlsx`, "tipo informe", con la apertura de la
"inflación" de la canasta Media por rubro, región, provincia, cadena y tipo de sucursal. La CELDA 19c la arma: filas
Total (serie oficial), rubros SEPA (Almacén, Frescos, Perfumería, Limpieza, Bebidas, Congelados, de la columna `rubro`
de la hoja Selección) con sus categorías, regiones, provincias, cadenas y tipos (≥10 sucursales); columnas los últimos
12 meses (base = mes anterior al primero = 100), el mes en curso parcial y las semanas (1S-4S) del mes anterior y del
mes en curso; bloques índice y variación %. Método: el de la CELDA 9 aplicado a cada fila (mediana de las
observaciones del país o del grupo, eslabones con productos apareados). La 19b ahora deja sus observaciones para la
19c; los meses viejos se leen del SEPA una vez y quedan en el caché `detalle_<clave>_v1.parquet` (primera corrida en
Colab ~40-50 min; medido el 2026-10-16: ~35 min). Validada con oct-26 (Total = oficial, rubros = Serie_precios, grupos = control de la 19b, semanas =
observaciones del prototipo) y con `notebooks/test_analisis_detallado.py`. Prototipo y scripts de validación en
`docs/auditoria/scripts_nb02_2026-10/`.

### 2026-10-15 — nb02: desagregación de la variación mensual (CELDA 19b)

La canasta Media subió +1,75% en oct-26 (al 15/10) y se pidió explicar ese número por producto, geografía y cadena.
Primero con un script ad hoc; ahora sale todos los meses del nb02: la CELDA 19b reparte la variación oficial por
producto (suma exacta), separa el arrastre de la última semana del mes anterior y la reparte por cadena, provincia,
región y tipo de sucursal con un panel apareado sucursal × producto (pesos oficiales). Agrega 13 hojas a
`canasta_analisis_{PERIODO}.xlsx`. Relee del ZIP el mes anterior y el mes en curso solo con los EANs de la canasta
(`DESAGREGAR_CANASTAS`, CELDA 1). Validada contra el script con los datos de oct-26 (oficial 1,748; panel 1,971;
arrastre 1,479) y con `notebooks/test_desagregacion_variacion.py`. Método: `docs/METODOLOGIA.md` §4.

### 2026-10-02 — nb07 v5.14 (Colab gratuito), corrida al 2026-10-01 auditada, v5.15 lista

El usuario perdió Colab Pro y el nb07 solo corría con "RAM amplia". **v5.14**: el panel semanal (~85-91 M de filas)
pasa a una representación compacta (sucursal entera, `semana`/`item`/`provincia` categóricos), la mediana de las
semanas partidas solo sobre esas semanas, sin copias del panel, costo por sucursal sumado por canasta; mismo
resultado (identidad vieja vs nueva con el código real sobre 31 M de filas) y pico de RAM 9,3 → 3,4 GB
(`docs/auditoria/scripts_v514/`). El caché en disco no cambia.

Corrida al 2026-10-01 en Colab gratuito (relectura 2h10m). Primero se cargó un Excel de canasta con la composición
vieja (270 EANs): se detectó comparándolo con `cargar_canastas_v5.py` y se corrigió antes de correr. Auditoría
`docs/AUDITORIA_2026-10-02_v514.md`: 18 OK / 2 conocidos, índices iguales a lo simulado para la v5.13 (Popular 243,
Media 248, Ejecutiva 244, Representativa 239, Femenina 259 a ago-26; IPC alimentos 261). Femenina volátil por
construcción (publicar mensual); Tecnológica como nivel. Hallazgos: el Lavarropas Samsung perdió la mitad de sus
sucursales y la cobertura mínima lo saca; la composición por rubro omitía ítems sin precio.

**v5.15** (no corrida): composición por rubro con faltantes imputados (columna `imputado`), Lavarropas → BGH
Bwfe06s24ar y 57 candidatos de la Tecnológica en `EANS_CANDIDATOS` (relee el SEPA una vez; después los reemplazos de
la Tecnológica no releen). Excel de canasta listo: `canasta_representativa_2026-10_v515.xlsx` (en Descargas del
usuario; se regenera con el cargador). Próximo paso: correrla y auditarla (`.claude/memory.md`).

### 2026-09-24 (cierre) — nb07 v5.13 lista para correr + ronda 2 aplicada

El usuario aprobó las cinco decisiones de la revisión de la v5.12. nb07 **v5.13** (relee el SEPA por los ratios):
(1) frescos por índice multilateral **TPD** sin ponderar, ventana de 52 semanas con empalme de movimiento (contra el
INDEC 0,99, el encadenado 0,94); (2) **nivel de los frescos fijo**: 3 últimos meses con cobertura normal hasta el mes
de referencia (2026-08); una semana nueva ya no reescala la historia, y al simular con el estimador replicado apareció
que el Durazno tomaba el nivel de agosto, fuera de temporada (4 veces su peso) y el Roast beef el de un mes con media
muestra perdida; (3) **cobertura mínima de empaquetados** min(300, 50% de la típica), fuera de la muestra
apareada (con arrastre, el eslabón de esas semanas daba 1,0: se detectó en la simulación, la Tecnológica perdía 30
puntos de 2024); (4) **`RATIO_FRESCO` estacional** de Naranja, Tomate y Limón por recall/contaminación; (5) **ronda 2**
de reemplazos (15, 267 EANs, no relee). Test nuevo `notebooks/test_frescos_v513.py`; 8 tests OK. Efecto estimado sobre
el panel v5.12 (ene-24 → ago-26, simulación con el código real): Popular 230,4 → 242,8, Media 241,7 → 247,6,
Ejecutiva 243,8 → 243,3, Representativa 235,9 → 239,2, Femenina 260,0 → 258,7
(`docs/auditoria/scripts_v513/simular_v513.py`).

### 2026-09-24 (noche) — corrida v5.12 y revisión a fondo

Relectura completa con la semana al 24-sep. Revisión en `docs/AUDITORIA_2026-09-24_v512.md` (+ PDF y
`docs/auditoria/scripts_v512/`): la brecha con el IPC de alimentos sale de los frescos (los empaquetados siguen
al INDEC); incertidumbre del acumulado ±8-9,5 puntos por elección de productos; dos defectos nuevos (filtro
estacional de Naranja/Tomate/Limón, introducido en v5.11/v5.12, y el nivel de los frescos revisado cada
semana); ronda 2 de reemplazos propuesta (15 recomendados). Pendiente: decisiones del usuario (auditoría §7).

### 2026-09-24 (tarde) — nb07 v5.12 preparada (ronda 2 de relectura)

65 candidatos nuevos en `EANS_CANDIDATOS` (historia flaca y Woolite), `RATIO_FRESCO` de Naranja y Tomate
= INDEC / ancla, y `proponer_reemplazos.py`. Relee el SEPA; la corrida suma además la semana que el usuario
agregó al Drive. Después: proponer y aplicar la ronda 2 de reemplazos (sin otra relectura).

### 2026-09-24 — corrida v5.11 verificada y reemplazos de trazabilidad

- Auditoría de la corrida v5.11 (`docs/AUDITORIA_2026-09-22_v59.md` §11): índice replicado, aperturas y
  frescos contra el INDEC en rango. Contra la v5.10 el índice sube por los pañales (Ejecutiva +7,7
  puntos: bajaban de precio relativo) y cambia poco por los frescos. Hallazgo: la Naranja de Carrefour
  no es naranja por kilo.
- Hallazgo de método: "meses con dato" no ve la cobertura flaca (Raid 370 en 1 sucursal durante 2025).
  El auditor suma el bloque 7b (sucursales por mes).
- 24 reemplazos aplicados (`docs/canastas_alternativas/reemplazos_2026-09-24.csv`): 270 EANs, sin
  relectura. Corrida verificada el mismo día (§11.1): índice ene-24 → ago-26 Popular 230,2 · Media 241,5 ·
  Ejecutiva 243,6 · Representativa 235,7 · Femenina 260,0; la Popular cotiza en 1.746 sucursales (antes 1.239). El Skip de la Ejecutiva se queda hasta medir Woolite en la relectura v5.12.
- nb07 v5.11.1 (BUG-38, hoja `Candidatos_trazabilidad`) y `aplicar_reemplazos.py` sin falsas alarmas
  (BUG-39).

### 2026-09-23 (noche) — handoff para retomar en otra PC

`CLAUDE.md` en la raíz, `requirements.txt`, la planilla del INDEC en `data/`, y
`docs/canastas_alternativas/aplicar_reemplazos.py` (reemplazos puntuales con las reglas del
constructor, probado). La corrida v5.11 quedó corriendo en Colab; los pasos para cuando lleguen sus
resultados están en `.claude/memory.md`.

### 2026-09-23 — nb07 v5.11: paquete de relectura (frescos bien especificados y candidatos a reemplazo)

Relee el SEPA. Bandejas Atm de DIA fuera de Pollo y Suprema (decisión del usuario), chorizos fuera de
Pollo, jugos fuera de Limón, `RATIO_FRESCO` recalibrado donde el filtro de régimen descartaba el
producto correcto (Pollo, Carne picada, Limón, Suprema), Tomate y Naranja anclados al INDEC, y 90
candidatos a reemplazo leídos sin entrar a ninguna canasta (hoja `Candidatos_trazabilidad`) para
elegir los reemplazos de los ítems con huecos sin otra relectura. Test `test_candidatos_reemplazo.py`.

### 2026-09-23 — nb07 v5.10 corrida y verificada; pañales fuera de las canastas

- Corrida v5.10 sin releer el SEPA, auditada (`auditar_salida_nb07.py --cache --indec`): índice
  replicado, 0 cadenas/regiones fuera de rango (BUG-37 resuelto), solo cambian los 5 tipos anclados.
  El acumulado ene-24 → ago-26 **bajó** (Popular 234,1 → 231,1): el anclaje corrige el peso de esos
  tipos en la canasta. Se había anticipado, mal, que quedaba idéntico. Detalle: auditoría v5.9 §10.
- Decisión del usuario: pañales y toallitas húmedas fuera de Media, Ejecutiva y Representativa (el
  hogar tipo 2 tiene hijos de 6 y 8 años). Hecho en `cargar_canastas_v5.py` (282 EANs) y en el
  constructor; se aplica en el Drive con el próximo paquete de relectura.
- Hallazgo nuevo: Suprema/Pechuga a 4,1× el pollo entero (producto de DIA); Tomate y Naranja siguen
  fuera de rango contra el INDEC.

### 2026-09-22 — nb07 v5.10: auditoría de la corrida v5.9, BUG-37 y nivel de frescos anclado al INDEC

Auditoría completa de `canastas_alternativas_2026-09-17.xlsx` (corrida v5.9, sin releer el SEPA):
`docs/AUDITORIA_2026-09-22_v59.md` + PDF + scripts en `docs/auditoria/scripts_v59/`. El índice y el
costo nacional se replicaron por caminos independientes (índice: dif. 0,002; precio nacional de los
empaquetados: 100% de 37.776 celdas dentro del 0,1%). Cambios:

- **BUG-37**: el costo por sucursal omitía los rubros enteros que la sucursal no publica → Vea, Disco,
  Jumbo y Cooperativa Obrera salían 25-40% "más baratas" y Cuyo "la región más barata". Todas las
  aperturas geográficas y por cadena estaban afectadas; el nacional no. Corregido, con columna
  `pct_imputado` y test `notebooks/test_costo_sucursal.py`.
- **Nivel de frescos anclado al INDEC** (precios promedio GBA, ago-2026): Pollo, Carne picada,
  Merluza, Limón y Pan francés cotizaban otro producto o tenían un ancla sin fuente; inflaban el costo
  de la Popular un 8%. Los precios por sucursal de esos tipos se reescalan con el mismo factor.
- `Resumen` con `mes_parcial` y las dos bases del índice; grafía de provincias determinística.
- `auditar_salida_nb07.py`: sin las falsas alarmas de la v5.9, más chequeo de aperturas (6b) y
  contraste opcional con el INDEC (6c, `--indec`).
- Hallazgos abiertos: evolución de frescos dependiente del método (publicado en el extremo bajo),
  pañales en un hogar tipo 2 sin bebés, universo de EANs de Pollo/Limón (requiere releer el SEPA).

**Nada de esto cambia la clave del caché**: la próxima corrida reusa lo leído.

### 2026-09-09 — nb05/nb02: BUG-29 (gráfico de barras) y BUG-30 (tiles del mapa)

La corrida real de nb05 con 19 cervezas (agosto 2026) cortó en la CELDA 12 con
`ValueError: shape mismatch ... (32,) vs (18,)`: el gráfico de variaciones dibujaba todas las series
contra el eje temporal del **primer** producto, y uno de los 19 (Golden Porrón 330, desde 2025-03)
tiene 18 meses contra 32 del resto. Ahora cada serie lleva su propio eje de fechas, el producto de
referencia del eje es el que arranca antes (no el primero de la lista) y la leyenda aclara la base
propia de los productos que aparecen después (`(base 03-25)`), porque su índice 100 no es el mismo
mes que el de los demás. Mismo fix aplicado a `gen_nb02.py`, que tiene el mismo código.

En la misma corrida el mapa Folium salió tapado con la leyenda *"API key required"*: CARTO empezó a
estampar los tiles servidos sin cuenta. El fondo del mapa pasa a elegirse con **`TILES_MAPA`** en la
CELDA 1 (`'osm'` por default, `'topo'`, o `'carto'` si algún día se consigue cuenta), con URL y
atribución explícitas. Test de regresión nuevo: `notebooks/test_celdas_graficos_y_mapa.py`, que
ejecuta las celdas reales del `.ipynb` generado.

**BUG-31, en la misma corrida**: el `mapa_interactivo_082026.html` de 19 productos pesaba **48,6 MB**.
La CELDA 17 escribía los datos dos veces — el JSON de los popups y, además, un objeto Leaflet por
cada par producto×sucursal (~1,6 KB cada uno entre marcador, popup, placeholder y tooltip): ~35.000
marcadores de los que se ven ~2.000 por vez. Ahora al JSON se le agregan lat/lon y **los círculos los
dibuja Leaflet en el navegador** al elegir producto; el color se interpola en JS con la misma rampa y
los mismos percentiles, la leyenda se dibuja por producto, y los filtros de cadena/provincia recortan
la lista antes de dibujar en vez de esconder nodos del DOM. Medido: **0,62 MB** para 19 productos ×
2.000 sucursales (nb02: 0,76 MB para 6 canastas × 2.300). Verificado en navegador: marcadores,
selector, filtros combinados, popup, tooltip, leyenda y botón Restablecer.

**BUG-32, al abrir esos mapas**: nunca terminaban de cargar y no mostraban las líneas limítrofes.
`tile.openstreetmap.org` **no responde desde la red de INECO** (Esri, OpenTopoMap y CartoDB sí), así
que no llegaba ningún mosaico y los pedidos colgados dejaban la pestaña en *loading*. El mapa deja de
depender de un proveedor fijo: `TILES_MAPA = 'auto'` embarca una lista y el navegador se queda con el
primero que responda (9 s de paciencia o 4 errores seguidos antes de pasar al siguiente). Orden por
defecto **esri → osm → topo → carto** (Esri gris con nombres y límites, sin API key; CartoDB último
porque su marca de agua viaja en un HTTP 200 y el fallback no la detectaría). Si no responde ninguno,
el mapa avisa que sólo falta el fondo. Además se sacan del HTML los CDN que folium engancha y el mapa
no usa (jQuery, Bootstrap, Font Awesome, awesome-markers, glyphicons).

### 2026-09-04 — nb07 v5.1: robustez del nacional (primera corrida real de v5)

Diagnóstico sobre `canastas_alternativas_2026-09-03`. El índice encadenado bajó los saltos de
±24% a ±12%, pero quedaban cuatro. Causa: **el ruido de las provincias chicas entraba al nacional
con todo su peso poblacional** (volatilidad 2,3% con 1.423 sucursales vs 12,0% con 38). En el
salto del 2025-06-12, Centro/Pampeana subió 1,6% y Patagonia 113%, y volvió la semana siguiente.

Correcciones (METODOLOGIA §10.8): `MIN_SUC_PROV_ITEM=3`, `PROV_OUTLIER_K=2.5`,
`COBERTURA_MIN_INDICE=0.80` (la Tecnológica tenía 4 de 14 ítems en todo 2024), descarte de la
semana incompleta del final (el SEPA llegaba al 31/08 y la semana cerraba el 03/09), y detección
centavos/pesos medida solo sobre empaquetados. Frescos: Bondiola separada de la bondiola curada
(144→101 EANs), Espinaca sin ensaladas listas, Choclo y Pan francés depurados.
Nuevas salidas: hoja `Panel_nacional` y bloque de fiabilidad regional en el reporte.

Los movimientos de Carne de 2026-03/06 se dejaron: aparecen también en Centro/Pampeana con 1.700
sucursales, así que son repricings reales, no ruido.

### 2026-09-04 — nb07 v5: motor del informe semanal (6 canastas, índice encadenado)

Reescritura del motor de nb07 para que la salida la pueda publicar semanalmente el equipo de
economistas. Diagnóstico previo sobre el Excel `canastas_alternativas_2026-W36.xlsx`:

- Los saltos de 2026-W07 (+24%) y la caída de W31 (−21%) eran **100% el rubro Carne**: cambios
  en el set de variantes de cada tipo, no inflación.
- El "despegue" inicial de varias canastas era **entrada tardía de ítems**: Popular-Frescos
  +216% en abr-2024 (entra la leche), Tecnológica-Heladera entra en ago-2025, Femenina-jabón
  íntimo en jul-2024. Un ítem sin precio aportaba $0 y al aparecer generaba un salto de nivel.
- El "nacional" era **el precio de DIA** (42% de las sucursales, precios uniformes): nacional,
  CABA, Buenos Aires y Centro/Pampeana daban el mismo número exacto.
- Bugs: `San juan` no matcheaba la normalización de provincia y caía en región `Otras`;
  `n_sucursales` contaba `id_sucursal` sin la terna comercio/bandera.
- El IPC "recto" no era un error: son los índices INDEC reales, lineales a esa escala.

Cambios (ver METODOLOGIA §10.7): semana que **cierra el jueves**; **índice encadenado de muestra
apareada** + arrastre de 8 semanas; **nacional ponderado por población provincial**; **filtro de
outliers intra-tipo** en frescos (K=2.5); **índice provincial/regional controlando por cadena**;
`FRAC_PRODUCTOS_MIN` 0.5 → 0.8; composición a **196 empaquetados + 59 tipos de frescos**
(nuevos rubros Pollo, Cerdo, Pescado, Fiambres y Quesos, Panadería); hojas nuevas
`Presencia_items` y `Alertas_reemplazo` para trazabilidad de altas y bajas.

Loader unificado **`docs/canastas_alternativas/cargar_canastas_v4.py`** (196 EANs,
`cantidad_01..06`); reemplaza y elimina los loaders anteriores. Validado: 196/196 EANs
matchean en la hoja real. Notebook validado end-to-end con dataset sintético (16/16 celdas OK,
filtro de outliers y detección de altas verificados).

### 2026-09-01 — Notebook 07: canastas alternativas (Popular/Media/Ejecutiva) semanales + frescos (nuevo, `gen_nb07.py`)

Nueva herramienta pedida por el usuario: mismo análisis que nb02 pero (1) **3 canastas** socioeconómicas Popular/Media/Ejecutiva (= canastas 2/3/4 del proyecto de índices, respeta percentiles Q2/Q3-Q4/Q5), (2) granularidad **semanal** (ISO week) además de mensual para el vs-IPC, (3) desagregación **por rubro** con drill-down hasta producto (Carne como rubro propio), (4) **suma frescos** (carne, frutas, verduras, huevos), (5) vs IPC, (6) imprime diagnósticos de cobertura para refinar iterando.

**Decisión de diseño — composición híbrida**: los empaquetados se leen por EAN de la hoja `Productos unicos` (columnas `cantidad_01/02/03`, que estaban vacías y se poblaron matcheando las 3 listas del proyecto de índices → 208/208 productos matchearon). Los **frescos NO se pueden seguir por EAN** (el código de balanza —prefijo GS1 `2…`— cambia por cadena; verificado: 51% de Carnicería y 20% de Frutas/Verduras son de 1 sola cadena), así que se seleccionan por **regla de nombre** (regex con `\b` para evitar falsos positivos tipo camPERA→pera) sobre el maestro SEPA completo, y el precio del tipo por sucursal/semana = mediana de las variantes presentes, normalizado a $/kg o $/docena. **Electrodomésticos/durables excluidos** (mediana de 1 cadena → romperían la representatividad geográfica y la serie temporal). Validado end-to-end con dataset SEPA sintético. Generador usa raw strings `r'''...'''` (evita el doble-escape de regex). **Pendiente**: el usuario sube a Drive el Excel poblado + `maestro_sepa_completo.csv.gz`, corre en Colab y pasa los diagnósticos para afinar reglas de frescos y cantidades.

### 2026-07-07 — Fix nb05: factor centavos/pesos mal detectado con pocos productos

El usuario corrió nb05 con Coca-Cola y Fernet y encontró caídas de precio ~100x en meses puntuales (ago-nov 2024, jun 2026). Causa: la detección del factor (mediana de precios > 10.000 ⇒ centavos) se calculaba sobre la mediana de **solo los EANs pedidos por el usuario** — robusta con las canastas de 40-75 productos de nb02, frágil con los 1-2 productos típicos de nb05. El resguardo de EANs de referencia copiado de nb02 quedaba inerte porque el CSV ya se filtraba a los EANs del usuario antes de buscar la referencia. Fix en `gen_nb05.py` (CELDA 6 y CELDA 9): se lee siempre la unión `PRODUCTOS_EANS_NORM | REF_EANS_FACTOR` y el factor se ancla a la muestra de referencia (mismos 3 EANs que usa nb02), con fallback a la muestra propia si la referencia no aparece ese mes. Validado con un caso dirigido (sin fix devuelve un valor 100x mayor al correcto; con fix, correcto) y re-corrida completa del smoke test end-to-end.

### 2026-07-07 — Notebook 05: evolución de productos individuales (nuevo, `gen_nb05.py`)

Nueva herramienta pedida por el usuario: mismo análisis que el notebook 02 (evolución vs IPC, provincias, mapas, rankings, mapa Folium) pero por **producto individual (EAN)** en vez de canasta ponderada — ej. seguir Coca-Cola y Fernet por separado.

- **`05_evolucion_productos_representativos.ipynb`** (← `notebooks/gen_nb05.py`, 21 celdas): clon adaptado de `gen_nb02.py`. CELDA 1 (config) reemplaza el Excel de canastas por un campo `EANS_INPUT` (string de EANs separados por coma, **sin límite de cantidad**); cada EAN se cruza contra `Maestro de Productos Interno.xlsx` para mostrar su descripción real.
- Cada producto es una "canasta" de 1 EAN con cantidad=1 (sin imputación: una sucursal solo cuenta si vende ese producto específico). Colores/estilos se generan dinámicamente en vez de los 6 fijos de nb02.
- CELDA 20 (valores resumen) reescrita 100% genérica, sin ningún ID de canasta hardcodeado (nb02 sí asume que existe `cantidad_03`/Media, ver hallazgo de auditoría abajo).
- Validado con un dataset SEPA sintético completo (6 sucursales, 3 meses, maestros, IPC, geojson): se ejecutaron las 20 celdas reales del notebook generado end-to-end, lo que encontró y permitió corregir 2 bugs antes de commitear (agregación con dtype `object` cuando un EAN no tiene ningún dato histórico; colisión teórica de nombres de hoja Excel al truncar a 31 caracteres). Detalle completo en `.claude/memory.md`.

### 2026-07-07 — Auditoría de `gen_nb02.py`/notebook 02 (solo diagnóstico, sin cambios)

A pedido del usuario, revisión exhaustiva del notebook 02 sin aplicar fixes. Confirmado: generador y `.ipynb` commiteado están sincronizados (bytes idénticos al regenerar). Hallazgo principal (verificado ejecutando el código real, no solo lectura): **CELDA 13 (tabla LaTeX por provincia) tiene el `\\` duplicado en la fila de encabezado** — mezcla de convención de escape (esa fila usa un string raw pero con la cantidad de backslashes de un f-string) → rompe la compilación LaTeX si se usa ese `.tex` directo en Overleaf. Las filas de datos están bien. Hallazgos menores: CELDA 20 asume sin guard que `cantidad_03` (Media) siempre existe; `CADENAS_FILTRAR` de nb02 no coincide con `EXCLUIR_COMERCIOS` de nb04 sin documentación de por qué. Pendiente de corrección si el usuario lo pide.

### 2026-06-01 — Canastas especiales: Celíaca Media y Vegana Básica (cantidad_05/06)

- **`cantidad_05` = Celíaca Media**: variante sin TACC de la Canasta Media. 72 productos. **Costo real (abr-2026): $691.836 (+9.0% sobre Media $634.923)**. Prima celíaca mayor de lo esperado; mayor impacto: pasta sin TACC, sidra y almidón Maizena.
- **`cantidad_06` = Vegana Básica**: dieta vegana integral. 51 productos. **Costo real (abr-2026): $427.033 (−5.4% vs Popular $451.672)**. Queda entre Vulnerable y Popular (94.5% del costo Popular). Ordenamiento final: Vulnerable $252k → Vegana $427k → Popular $451k → Media $634k → Celíaca $691k → Media Alta $879k.
- Gráfico 2 (variaciones): barras más anchas (`max(3, int(22/n))`), figura adaptativa (`max(20, n*2+10)`), ticks cada 2 meses cuando hay >5 series, leyenda multi-columna, estilo limpio sin bordes top/right.
- `CANASTA_NAMES` actualizado: 'Canasta 05' → 'Celíaca Media', 'Canasta 06' → 'Vegana Básica'
- `CANASTA_SHORT` actualizado: 'canasta05' → 'celiaca_media', 'canasta06' → 'vegana_basica'
- Outputs con nuevos nombres: `mapa_interactivo_MMAAAA_celiaca_media.html`, `ranking_cadenas_nacional_MMAAAA_vegana_basica.png`, etc.
- Ver archivo fuente: `canastas_argentina_2026_v3.txt` (contiene CANASTA_5 y CANASTA_6)

### 2026-06-01 — Mejoras visuales nb02 post primera ejecución multi-canasta

- `MES_INICIO_GRAFICO = '2024-01'` (era '2024-03') — índice base desde enero 2024
- **Gráfico 2**: cambio de líneas a **barras verticales** por canasta; IPC como líneas superpuestas
- **Gráfico 3 nuevo**: ranking de valores absolutos (barras horizontales por canasta con promedio nacional)
- **Mapa Folium único**: un solo HTML con selector de canasta en el panel de filtros; JS con `switchCanasta()` + FeatureGroups por canasta; filtros de provincia y tipo siguen funcionando
- Nombre de output del mapa: `mapa_interactivo_{MES}.html` (sin sufijo de canasta)
- Primera ejecución multi-canasta confirmada: Vulnerable $255.900, Popular $455.874, Media $634.923, Media Alta $908.166. 239/239 EANs encontrados, 28 meses historia, 24 provincias, 121 reclasificaciones por coordenadas.

### 2026-06-01 — Canastas ENGHo v3: 4 canastas por quintil con doble filtro calidad

- **Canastas definidas** basadas en ENGHo 2017/18 (INDEC) + coeficiente de Engel:
  - `cantidad_01` = **Vulnerable** (Q1, Engel ~36%, precio ≤ P33, 46 productos)
  - `cantidad_02` = **Popular** (Q2, Engel ~28%, precio P25-P55, 61 productos)
  - `cantidad_03` = **Media** (Q3-Q4, Engel ~22%, precio P40-P70, 73 productos)
  - `cantidad_04` = **Medio-Alto** (Q5, Engel ~15%, precio P55-P85, 77 productos)
- **Doble filtro de calidad**: `score_cobertura >= 0.88` AND `pct_trazabilidad >= 90%`
- **Correcciones v2→v3**: 4 EANs malformados corregidos a 13 dígitos; huevos agregados a todas las canastas; Pampa Brewing→Schneider; Tintura→Crema Facial Neutrógena; Coca Light→regular; Tic Tac→Menthoplus; Oblea→Gallo plain
- Archivo de referencia: `canastas_argentina_2026_v3.txt` (en Downloads del analista)
- Ver metodología completa en `docs/METODOLOGIA.md`

### 2026-06-01 — Rewrite completo nb02: soporte multi-canasta (commit c85aa84)

**Cambio arquitectural mayor**: el notebook 02 ahora procesa hasta 6 canastas simultáneamente.

- **CELDA 3**: lee `cantidad_01`..`cantidad_06`, construye `CANASTAS` dict (solo columnas activas), `CANASTA_EANS_NORM` = unión de todos los EANs activos
- **CELDA 7**: un `groupby().apply()` por canasta → `canasta_geo_dict`. Limpieza geográfica (CABA filter, reclasificación por coordenadas) se hace UNA SOLA VEZ
- **CELDA 8**: análisis provincial por canasta → `serie_prov_dict`, `prom_nac_dict`
- **CELDA 9**: UN SOLO cache raw (`hist_union_HASH.parquet`) para la unión de EANs; luego agregación por canasta en memoria (sin releer ZIPs). Hash basado solo en EANs, no en cantidades
- **CELDA 11**: comparativa por canasta → `comparativa_dict`, `df_g_dict`
- **CELDA 12**: gráfico de índices y variaciones con todas las canastas activas + IPC (líneas)
- **CELDA 13**: Cuadro 1 + LaTeX por canasta
- **CELDA 14**: un mapa coroplético por canasta (`mapa_canasta_{short}_{mes}.png`)
- **CELDA 16**: rankings nacional + AMBA por canasta
- **CELDA 17**: un mapa Folium HTML por canasta (`mapa_interactivo_{mes}_{short}.html`)
- **CELDA 18**: ranking barrios CABA por canasta
- **CELDA 19**: Excel con `Evolucion_IPC` (wide, todas canastas), `Prov_{short}`, `Ranking_{short}`, `Sucs_{short}` por canasta, `Serie_precios` con col `canasta_id`

**Nombres y colores**:
- `cantidad_01` = Vulnerable (#0055A4) · `cantidad_02` = Popular (#e74c3c)
- `cantidad_03` = Media (#27ae60) · `cantidad_04` = Media Alta (#f39c12)
- `cantidad_05` = Canasta 05 (#9b59b6) · `cantidad_06` = Canasta 06 (#1abc9c)

### 2026-06-01 — Soporte multi-canasta en nb01: 6 columnas cantidad (commit 566f033)

- La hoja `Selección` (y `Productos unicos`) del Excel exportado por nb01 ahora tiene **6 columnas de cantidad** (`cantidad_01` ... `cantidad_06`) en lugar de una sola `cantidad`
- Cada columna permite definir una canasta independiente
- Todas resaltadas en amarillo (fill `FFF9C4`) con encabezado naranja (`F9A825`), ancho 10
- Pendiente: adaptar nb02 para procesar las 6 canastas en paralelo (próxima sesión)

### 2026-05-29 — Robustez para canastas pequeñas/especializadas (commits e979ae2, 6289ab8)

- **BUG-19**: `MIN_PRODUCTOS_PROPIOS = 15` con canasta de 12 productos → 0 sucursales válidas. Fix: safeguard en CELDA 3 que auto-ajusta a `N_CANASTA // 2` cuando `MIN_PRODUCTOS_PROPIOS >= N_CANASTA`. No afecta ICR (51 productos).
- **BUG-18**: `IndexError` en CELDA 11/12 cuando la serie histórica está vacía. Ocurre con EANs PLU (prefijo 27.../28...) que no existen en el SEPA histórico. Fix: guarda `_serie_vacia` en CELDA 11 y envuelve la lógica de gráficos de CELDA 12 en `if len(df_g) > 0:`.
- El notebook ahora soporta **cualquier canasta** — desde 1 producto hasta 100+, con o sin historia disponible. Siempre ejecuta completo y produce todos los outputs disponibles para los datos que tiene.

### 2026-05-29 — Mejoras visuales y corrección de coordenadas nb02 (commits 4bcb92d, 7c3fe29)

- Todos los gráficos exportados a **dpi=600** (antes 150/200)
- **CELDA 15 reemplazada**: 4 gráficos nuevos — barplot 3 paneles por provincia (productos únicos · cadenas · sucursales), barplot 3 paneles por cadena, heatmap binario presencia cadena×provincia, heatmap log₁₀ intensidad. Datos derivados de `precio_mes` + `canasta_geo_filtros` para incluir `n_productos_unicos` real.
- Mapa coroplético y rankings: **sin título principal** 
- Rankings: eje X con separador de miles en formato argentino (`$478.836`)
- **CELDA 7 — reclasificación por coordenadas** (BUG-16): reemplaza el descarte de sucursales por reclasificación usando bounding boxes de las 24 provincias. Preserva todos los datos, corrige la provincia según lat/lon.
- BUG-17: docstring triple-quote en `_geocodif()` cerraba el `cell_code` externo → cambiado a comentario de línea
- Output de CELDA 15: 4 archivos en lugar de 2 (`cobertura_provincia_`, `cobertura_cadena_`, `matriz_presencia_`, `matriz_intensidad_` — todos `_MMAAAA.png`)

### 2026-05-29 — Ejecución final confirmada con canasta revisada

- ✅ BUG-15 confirmado resuelto: San Juan aparece correctamente en mapa y cuadro provincial
- ✅ 4 reemplazos todos al 100% trazabilidad desde ene-2024 (Swift XL, Anti-splash, Plusbelle, Listerine)
- ✅ Serie histórica: 28 meses, ramp-up 48→51 EANs explicado (3 productos nuevos en 2024)
- ✅ 48/51 productos al 100%, promedio 99.4%. Mínimo: Nesquik 82.1% (nuevo desde jun-2024, no inestable)
- Cache nuevo: `hist_0a6651c5.parquet`

### 2026-05-29 — ICR, BUG-15, mejoras nb02 (commits 6fe5a5e, 17ae989, 96f83f5)

- **BUG-15**: San Juan no aparecía en mapa coroplético. El maestro usa `"San juan"` (j minúscula) → agregado a `PROV_NORM`
- **Notebook 01**: nueva hoja `Productos unicos` (~70K–100K productos sin umbrales, mismas columnas que Selección)
- **Notebook 02**: renombrado a "ICR"; gráficos con etiquetas en español (`ene-24`, `feb-24`...)
- **Gráfico 2**: 3 barras por mes (ICR + IPC General + IPC Alimentos y bebidas)
- **Cache**: hash MD5 incluye EANs + cantidades → cambiar `cantidad` invalida cache automáticamente
- **MES_INICIO_GRAFICO**: auto-adapta al primer mes de la serie si el configurado no existe
- **Hoja Serie_precios**: nueva hoja en Excel de nb02 con precio mediano por producto por mes (serie completa)
- **Canasta ICR**: 4 reemplazos (ver tabla arriba). Trazabilidad promedio 99.4%
- **README**: reescrito completo con guía de ejecución paso a paso, outputs de ambos notebooks, métricas

### 2026-05-29 — IPC.xlsx formato real confirmado (commit a409d7e)

- Columna `date` = `datetime64` (Excel serial → pandas auto-convierte). La visualización `ene-17` es solo formato de celda.
- Fast path en CELDA 10: `pd.api.types.is_datetime64_any_dtype()` + `.dt.strftime('%Y-%m')` directo
- Fallback para archivos con fechas como texto `ene-2017` incluido (parseo manual con dict español)

### 2026-05-28 — Notebook 02 completo: análisis canasta elegida, mapas, rankings, IPC

- **Nuevo notebook** `02_evolucion_canasta_representativa.ipynb` (20 celdas) generado desde `notebooks/gen_nb02.py`
- Canasta leída desde hoja `Selección`/`Seleccion` del Excel del nb01 (fallback accent-safe)
- `calcular_canasta_completa()`: costo por sucursal con imputación nacional para productos faltantes; filtrado a MIN_PRODUCTOS_PROPIOS=15
- Serie histórica con caché parquet clave MD5 del set de EANs (invalidación automática al cambiar canasta)
- IPC desde `carga/IPC.xlsx` (nombre exacto en mayúsculas — case-sensitive en Colab)
- Gráficos: índices base mar-2024 + barras mensuales, `COLOR_CANASTA='#0055A4'`
- Cuadro 1 provincial + LaTeX, mapa coroplético con `ar.json`
- Rankings nacionales + AMBA (RdYlGn), mapa Folium con FeatureGroups + panel JS
- Ranking CABA con 48 bounding boxes de barrios, cobertura por provincia y cadena
- **BUG-14**: `ipc.xlsx` no encontrado → nombre real es `IPC.xlsx` (case-sensitive). Fix: fallback que prueba `IPC.xlsx`, `ipc.xlsx`, `IPC.XLSX` en orden
- README actualizado con badge Colab + estructura del repo

### 2026-05-27 — Fix BUG-12/13: implementos físicos y beauty/styling fuera de la canasta (este commit)
- **BUG-12**: "Cabo Metálico Glow" y similares aparecían en Limpieza del hogar (`subcategoria='Palas y Cabos'`). Fix: `excluir_subcat=['Palas y Cabos','Escobas y Escobillones','Plumeros y Limpiavidrios']`
- **BUG-13**: Tintura de cabello (Issue) y Protector Térmico (Roby) ocupaban top-3/4 de Higiene por alta cobertura nacional. Fix: `excluir_subcat=['Coloración','Fijación']` → desodorantes Dove entran al grupo
- Revisión exhaustiva del Excel de segunda ejecución: BUG-10 confirmado resuelto (EANs como texto en Excel con `data_type=s` verificado via openpyxl); 37 productos no alimentarios en Candidatos (esperado — pasan umbrales por cobertura); datos sucios en maestro documentados (Aceite Natura `presentacion=45778`, Crema Dermaglós `subcategoria=Rotisería`)

### 2026-05-27 — Fix BUG-10/11 + nueva firma seleccionar_grupo() (commit f67de87)
- **BUG-10**: `id_producto` exportado como int64 → EANs con ceros iniciales truncados. Fix: `str.zfill(13)` en cell-27 para `canasta_export` y `candidatos_export`
- **BUG-11**: `'carne'` no es substring de `'Carnicería'` → 13 embutidos curados de alta cobertura nunca incluidos. Fix: añadidas `'carnicería','carniceria'` a las kw del grupo Carnes
- **Nueva firma**: `seleccionar_grupo(df, rubros, kw, excluir_kw, max_n, excluir_subcat=None)` — nuevo parámetro `excluir_subcat` filtra por columna `subcategoria` para categorías heterogéneas
- Fixes BUG-6..9 de commit 3c66c3c verificados con segunda ejecución: 8 Lácteos, 6 Carnes limpios, Bebidas con yerba/té/café

### 2026-05-27 — Fix selección de grupos BUG-6..9 (commit 3c66c3c)
- **BUG-6**: Lácteos = 0 → `kw=['lácteos','lacteos']` matchea el valor literal de `categoria` en el maestro; verificado: 8 Lácteos correctos
- **BUG-7**: Azúcar contamina con Paté/Picadillo → `excluir_subcat=['Patés y Picadillos','Conservas de Pescado']`
- **BUG-8**: Carnes contamina con quesos de Fiambrería → `excluir_subcat=['Quesos Untables',...]`
- **BUG-9**: Bebidas sin yerba/té/café → añadido `rubro='Almacén'` + kw `'infusion'`; ahora: Yerba Liebig, Café Dolca, Té Inti Grey

### 2026-05-27 — Análisis post-ejecución: bugs en selección de grupos (BUG-6..9)
- **BUG-6**: Lácteos = 0 — kw `['leche','yogur',...]` no matchean `categoria='Lácteos'` del maestro; fix = `kw=['lácteos','lacteos']`
- **BUG-7**: Azúcar contamina con carnes enlatadas (`categoria='Conservas'` incluye ambas)
- **BUG-8**: Carnes contamina con quesos de Fiambrería (`excluir_kw` opera sobre `categoria`, no `descripcion`)
- **BUG-9**: Bebidas incompletas — yerba, té, café, agua mineral ausentes; investigar categorías reales en maestro
- Documentados en `BUGS_Y_MEJORAS.md`, requieren fix en cell-23 y posiblemente ampliar `seleccionar_grupo()`

### 2026-05-27 — Fix OOM definitivo: rediseño anti-OOM (commit fd5e014)
- Eliminado `df_enr` del pipeline — reemplazado por `df_cov` (producto × cadena × provincia) y `df_price_stats`
- `del df_suc_enr; gc.collect()` inmediatamente después de la agregación: RAM baja de ~10 GB a ~600 MB
- Cells 14, 15, 16, 18, 21 reescritas para usar los frames pequeños
- BUG-5 documentado y resuelto en `BUGS_Y_MEJORAS.md`

### 2026-05-27 — Fix observed=True en groupby (commit 01b4175)
- Añadido `observed=True` a todos los `groupby()` sobre columnas de dtype `category`
- Sin este fix, pandas genera el producto cartesiano de todos los niveles → shape 384 quadrillones → MemoryError 1.33 EiB

### 2026-05-27 — Fix OOM inicial + vectorización (commit 15936ba)
- Reemplazado `df.apply(lambda r: get_nombre_cadena(...), axis=1)` por lookup vectorizado con `.map()` sobre clave compuesta
- Lambda en `.agg()` para `cadenas_presentes` reemplazada por cálculo sobre frame deduplicado (~16 filas/producto en lugar de millones)

### 2026-05-27 — Fix bugs críticos + nuevas features (commit e23bff5)
- **BUG-1**: autodetección de FACTOR_PRECIO (mediana > 10,000 → centavos) en lugar de división fija /100
- **BUG-2**: diccionario `(id_comercio, id_bandera)` → nombre cadena; columna `nombre_cadena` y `cadenas_presentes` en Excel
- **BUG-3**: `excluir_kw` ampliados para Lácteos y Carnes (previene productos contaminantes)
- **BUG-4**: `.str.title()` en normalización de provincia → "San juan" → "San Juan"
- **MEJORA-1**: parquet cache snappy en `OUTPUT_DIR/_cache/`
- **MEJORA-3**: columnas `n_cadenas_com`, `cadenas_presentes` en Excel de salida
- Columna `periodo` = `PERIODO` para identificar el período en notebooks consumidores

### 2026-05-27 — Cobertura por provincias (commit ~8396bea)
- Reemplazado `pct_regiones` / `MIN_REGIONES` por `pct_provincias` / `MIN_PROVINCIAS`
- `SEPA_SOURCE` default cambiado a `'mi_drive'`; eliminada opción `'publico'` (carga.zip fue borrado)
- Heatmap ahora pivota por `PROVINCIA_NOMBRE`

### 2026-05-26 — Fix bugs de selección de canasta
- Bebidas: añadido `excluir_kw` para prevenir que 'te' matchee 'Espumantes'
- Lácteos: eliminado 'postre', añadido `excluir_kw=['repostería','reposteria']`
- Provincias duplicadas: normalización con regex `'^Provincia de '` + CABA
