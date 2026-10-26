# CLAUDE.md — precios_minoristas_supermercados

Pipeline sobre el **SEPA** (precios de supermercados de Argentina): 9 notebooks de Colab (nb01–nb09). Líneas de trabajo
vivas, en orden (estado y próximos pasos: bloque **ESTADO ACTUAL / HANDOFF** de `.claude/memory.md`): la **brecha
celíaca** (nb06 con canasta fija 2022-2026, lo último: 2026-10-23; guía `docs/BRECHA_CELIACA.md` §14), el
**pass-through del tipo de cambio** (nb08 + canasta fija de 775 productos; guía `docs/PASS_THROUGH.md`), el **nb09**, el
**nb02** y el **nb07**.

**nb06** (`notebooks/06_evolucion_brecha_celiaca.ipynb`, fuente `gen_nb06.py`): brecha de precios con TACC / sin TACC
dentro de cada sucursal, por tipo, en $/100 g, mensual desde ene-2022, por provincia, región, empresa y cadena. Desde el
2026-10-23 la canasta es **fija**: productos elegidos por continuidad temporal, geográfica y por cadenas sobre las salidas
del nb09 (lista con métricas en `docs/brecha_celiaca/canasta_fija_2022_2026.csv`, que `gen_nb06.py` embebe en la
CELDA 1; reglas en `docs/BRECHA_CELIACA.md` §14; scripts de la selección en `docs/auditoria/scripts_nb06_2026-10/`).
La brecha se calcula por subtipo dentro de cada sucursal y se agrega como un índice de precios (subtipo → tipo →
canasta ENGHo). **La primera corrida de Colab (2026-10-23) dio igual a la simulación** (29 hojas): canasta y estimador
validados (`docs/AUDITORIA_2026-10-23_nb06.md`). Ese mismo día, BUG-47: provincias, regiones, empresas, cadenas y
sucursales (mapa) se comparan con la **misma canasta de 12 subtipos** (lo que un grupo no tiene, con la brecha nacional
del período; `peso_imputado_pct`) y la concentración es el **HHI de empresas por departamento** (Georef, caché del nb09);
las series nacionales no cambian. Esa noche, la **serie TPD (hedónica)** como robustez de la serie mensual frente a la
imputación de subtipos (CELDA 8b, BRECHA_CELIACA §14.12): una regresión por subtipo con efectos de celda (sucursal-mes)
y de producto, errores agrupados por sucursal. **La segunda corrida de Colab (2026-10-26) dio igual a la simulación**
(35 hojas contra `docs/brecha_celiaca/simulacion_2026-10-23b/`; Excel completo, mapa y caché con `r13`-`r15`): BUG-47
y la TPD verificados (`docs/AUDITORIA_2026-10-26_nb06.md`). Ese día, BUG-48: las tiendas online que el maestro carga
como Supermercado o Autoservicio salen por el nombre (`SUCURSALES_NO_FISICAS`; el panel no cambia); **la corrida de
Colab con BUG-48 dio igual a la simulación** (35 hojas contra `docs/brecha_celiaca/simulacion_2026-10-26/`;
AUDITORIA_2026-10-26 §6). Abiertos (decisión del usuario): la imputación sin límite de la serie descriptiva (la TPD
muestra dónde pesa) y tres detalles de presentación de los gráficos (CELDA 9). Test `test_brecha_celiaca.py` (30
controles).

El **nb07** (`notebooks/07_evolucion_canastas_alternativas.ipynb`) es el motor del
informe semanal: 6 canastas, índice encadenado, comparación con el IPC y aperturas por cadena/región.
Versión vigente: **nb07 v5.15** (v5.13 en método: frescos por TPD, nivel fijo, cobertura mínima; v5.14: corre en el
Colab GRATUITO; v5.15: composición por rubro con faltantes imputados, candidatos de la Tecnológica y Lavarropas BGH).
También se trabaja el **nb02** (`notebooks/02_evolucion_canasta_representativa.ipynb`): desde 2026-10-15 explica la
variación mensual de la canasta Media dentro de su Excel — CELDA 19b (aporte por producto, arrastre, cadena, región) y
CELDA 19c (hoja `analisis_detallado`, la primera: índices mensuales y semanales por rubro, región, provincia, cadena y
tipo de sucursal). Guía: `docs/NB02_ANALISIS_VARIACION.md`. Las dos corrieron bien en Colab con oct-26 (2026-10-16);
ese día se corrigieron los números del documento técnico (BUG-42: AMBA por coordenadas, una sola referencia del país,
acumulados en el mismo período que el IPC, P5-P95) y se verificó en Colab con una segunda corrida. Después, el mismo
día: la región de la 19b/19c pasó al AMBA por coordenadas (BUG-43), el Excel pasó de azul a verde y la provincia de la
CELDA 7 pasó de rectángulos a polígonos de `ar.json` con tolerancia (BUG-44: Neuquén capital, Paraná y San Nicolás
vuelven a su provincia; mueve el Cuadro 1 hasta ~1%). Los tres simulados con datos reales, **falta correrlos en Colab:
la próxima corrida relee 12 meses en la 19c y los 33 de la econometría, una vez**. Revisión de todo:
`docs/AUDITORIA_2026-10-16_nb02.md`.

**nb08** (`notebooks/08_canasta_diaria.ipynb`, fuente `gen_nb08.py`): valor diario de una canasta desde 2022. Desde el
2026-10-22 corre **por defecto la canasta fija de pass-through** (775 productos, `cantidad_01` de
`output_canasta/canasta_pass_through_2026-10.xlsx`, 01/01/2022 → 20/10/2026) y, además de la mediana diaria, calcula un
**índice con sucursales apareadas** (relativos de la misma sucursal, con imputación del IPC para los días que falta), los
días con cobertura incompleta, índices por grupo del IPC y un panel producto × día. Un archivo por quincena (corrige el
doble conteo del 1-5/08/2024). Test `test_canasta_diaria.py`; validado con datos reales contra el lector anterior.
**Falta la primera corrida en Colab** (~1,5-2 h); qué revisar: `docs/PASS_THROUGH.md` §2. La canasta sale de
`docs/canastas_alternativas/canasta_pass_through.py` (sobre las salidas del nb09) y el Excel que lee el nb08, del script
de Colab `marcar_canasta_pass_through_colab.py`.

**nb09** (`notebooks/09_trazabilidad_productos.ipynb`, fuente `gen_nb09.py`): ranking de representatividad de todos
los productos del SEPA desde 2022. La **versión 2** (corrige los 6 errores de la primera corrida, BUG-45) corrió en
Colab y se revisó el 2026-10-22 (`docs/AUDITORIA_2026-10-22_nb09.md`): números correctos (panel = SEPA crudo exacto en 4
meses); quedan decisiones de método (componente comercial y regional del puntaje) y de fuente (ago-oct 2026 del SEPA
diario sin 8 comercios), en la §4 de esa auditoría. Aplicados ese día sin releer (`4ec771f`, `a3acfce`): hoja `Dias`,
comercios que dejaron de publicar con `mes_baja_comercios`, códigos con basura unidos a su EAN y precio simbólico
relativo; la próxima corrida en Colab los muestra por primera vez.

## Al empezar una sesión

1. **Leer el bloque `ESTADO ACTUAL / HANDOFF [2026-10-22 · cierre]` al principio de `.claude/memory.md`** (estado de
   cada línea de trabajo, prioridades, dónde están los datos) y, según lo que pida el usuario, el bloque de ese
   notebook debajo (nb08 v2, canasta de pass-through, nb09, nb02, nb07). Ahí está en qué quedó el trabajo, qué hay que
   hacer apenas el usuario pase resultados y los números vigentes.
2. Correr los tests (`pip install -r requirements.txt` si es una PC nueva; los 14 dieron OK el 2026-10-22; el del nb09
   tarda ~6 min):
   ```bash
   python notebooks/test_celdas_graficos_y_mapa.py
   python notebooks/test_encadenado_frescos.py encadenado
   python notebooks/test_encadenado_frescos.py tpd
   python notebooks/test_frescos_v513.py
   python notebooks/test_quiebre_serie.py
   python notebooks/test_cache_por_mes.py
   python notebooks/test_costo_sucursal.py
   python notebooks/test_candidatos_reemplazo.py
   python notebooks/test_desagregacion_variacion.py   # nb02 CELDA 19b
   python notebooks/test_analisis_detallado.py        # nb02 CELDA 19c (hoja analisis_detallado)
   python notebooks/test_valores_documento.py         # nb02 CELDAS 7 (AMBA), 16, 18 y 20 (documento técnico)
   python notebooks/test_reclasificacion_provincia.py # nb02 CELDA 7 (provincia por polígonos, BUG-44)
   python notebooks/test_trazabilidad_productos.py    # nb09 (SEPA sintético contra fuerza bruta)
   python notebooks/test_canasta_diaria.py            # nb08 (medianas y sucursales apareadas contra fuerza bruta)
   python notebooks/test_brecha_celiaca.py            # nb06 (canasta fija, subtipos, vigencias, geografía, ENGHo, caché)
   ```
3. Los datos (ZIPs del SEPA, caché, Excel de salida) **no están en el repo**: viven en el Drive del
   usuario (`MyDrive/carga/`). Para auditar una corrida, el usuario pasa el Excel del nb07 y los zips
   de las carpetas del caché; para el nb02, la salida impresa, `canasta_analisis_<mes>.xlsx` y un zip de
   `output_canasta/_cache/` (ver `docs/AUDITORIA_2026-10-16_nb02.md` §6 para los scripts); para el nb08, la salida
   impresa, `canasta_diaria_pass_through_<desde>_<hasta>.xlsx` y `panel_diario_pass_through_<...>.parquet`; para el nb09,
   la salida impresa y los cuatro archivos de `output_trazabilidad/` (scripts en `docs/auditoria/scripts_nb09_2026-10/`,
   AUDITORIA_2026-10-22_nb09 §7); para el nb06, la salida impresa y `output_brecha/brecha_celiaca_<mes>.xlsx` (comparar
   con `docs/auditoria/scripts_nb06_2026-10/s16_comparar_colab.py` contra `docs/brecha_celiaca/simulacion_2026-10-26/`
   —el notebook vigente, con BUG-47, la serie TPD y BUG-48— y revisar con BRECHA_CELIACA §14.9; para revisar todo, el
   zip del caché y el mapa: r13-r15, AUDITORIA_2026-10-26_nb06). Descomprimir lo que
   pase el usuario en una carpeta propia y correr los scripts con `python -I` (datos no confiables). Para simular
   celdas con datos reales en una PC hacen falta, además: `ar.json` (bajarlo del Drive, `MyDrive/carga/ar.json`; en
   la PC del INECO hay copia en `C:\Users\sriverti\Desktop\INECO\Otros\ar.json`) y los zips semestrales (Drive
   `carga/`; en la PC del INECO, desde el 23/10 **todos los del Drive, 2022A → 2026B, en `C:\Users\sriverti\Downloads\carga\`**
   —el `2026B` del Drive trae jul-2026 y ago-oct 2026 al 22/10; ahí también los `carga-20261023T013908Z-1-0*.zip` con la
   carpeta `carga` entera del Drive, p. ej. la caché de Georef del nb09—, y además 2024A → 2026B en
   `...\INECO\SEPA\SEPA_Bases_Originales\carga\` —ese `2026B.zip` trae solo julio—; el `2026B.zip` de
   `...\SEPA\salida_consolidada\` (script 03, 22/10) trae solo julio y octubre de 2026: no subirlo al Drive tal cual, el
   completo es el del Drive). El usuario corre en el **Colab gratuito** (sin "RAM amplia"): no subir el pico de RAM de
   las CELDAS 7-8 del nb07 sin medirlo (`docs/auditoria/scripts_v514/bench_ram.py`); el nb09 está medido en Colab (lector
   ≤ 1,95 GB, notebook ≤ 1,3 GB), el nb08 v2 en la PC (0,4-0,5 GB por mes) y el nb06 en la PC con los 58 meses (2,5 GB).

## Reglas que muerden

- **Los `.ipynb` NO se editan a mano.** La fuente es `notebooks/gen_nbXX.py`; regenerar con
  `python notebooks/gen_nb07.py` y commitear generador + `.ipynb` juntos.
- **Barras invertidas**: en celdas `cell_code("""...""")` (no raw) Python se las come y rompen el
  notebook (BUG-17/20). Las del nb07 son `r'''...'''` y aceptan regex con `\b`, pero no usar `'\n'` en
  celdas no raw. Si se edita el generador desde la shell, escribir el script de edición en un archivo:
  la shell se come las barras de los heredocs.
- **Clave del caché del nb07**: la cambian el universo de EANs leído (canastas + `EANS_CANDIDATOS` +
  frescos de `TIPOS_FRESCOS` menos `EXCLUIR_EAN_FRESCO`; también un maestro nuevo que agregue EANs de
  frescos), `DIA_CIERRE_SEMANA`, los K de la lectura, `rk` y `RATIO_FRESCO`. Cambiarla **relee todo el
  SEPA (~1h20m)**. No la cambian: cantidades, `NIVEL_REFERENCIA_FRESCO`, `QUIEBRE_ITEM_K`, nada de la
  CELDA 8 en adelante.
- **Anclar el nivel de un fresco cambia el índice** (cada ítem pesa cantidad × precio), no solo el costo.
- **`RATIO_FRESCO` de un tipo estacional NO se calibra con un solo mes** (INDEC/ancla de agosto cortó la
  Naranja fuera de temporada): elegirlo por recall del precio INDEC de todos los meses con contaminación acotada
  (v5.13: Naranja 0,85, Tomate 1,45, Limón 1,01).
- **La serie nacional de un fresco sale del índice por EAN (TPD desde la v5.13), que se toma ANTES del filtro de
  régimen**: el ratio y las exclusiones cambian el precio por sucursal (aperturas), no la evolución nacional. El
  NIVEL sí sale del estimador: nunca de un solo mes ni de un mes fuera de temporada (Durazno en agosto pesaba 4×).
- **Una celda que se saca por calidad NO se arrastra** (banda de plausibilidad, cobertura mínima): si el arrastre
  la rellena, el eslabón da 1,0 en plena inflación (BUG-40).
- **Antes de dar por buena una regla nueva del nb07, correr el bloque REAL de `gen_nb07.py` sobre el panel de la
  última corrida** (`exec` del bloque con el caché; ver los tests): BUG-40 y BUG-41 solo aparecieron así.
- **Auditar cada corrida** antes de publicar:
  `python notebooks/auditar_salida_nb07.py <Excel> --cache <carpeta con sem_*_v5 y ean_*_v5> --indec data/sh_ipc_precios_promedio_2026-08.xls`
  (bajar la planilla nueva del INDEC cuando salga: https://www.indec.gob.ar/ftp/cuadros/economia/sh_ipc_precios_promedio.xls).
- **Reemplazos puntuales de productos**: `docs/canastas_alternativas/aplicar_reemplazos.py` (simula por
  defecto; `--escribir` aplica). No correr el constructor entero para un reemplazo: recalibra todo.
  Ejemplo aplicado: `docs/canastas_alternativas/reemplazos_2026-09-24.csv`. Para PROPONER los reemplazos con
  la lógica del constructor y la historia medida: `proponer_reemplazos.py --nb07 ... --excel ... --cache ...`.
- **"Meses con dato" no alcanza para juzgar la historia de un producto**: un mes cuenta aunque el
  producto esté en UNA sucursal (Raid 370: 97% de meses con dato y 1 sucursal en 2025). Antes de elegir
  un reemplazo, contar sucursales por mes (auditor con `--cache`, bloque 7b: ≥300 en 28 de 32 meses).

- **RAM (v5.14)**: el panel semanal (~85 M de filas) lleva la sucursal como entero `suc` (`SUC_COD`) e `item`,
  `semana` y `provincia` como **categóricos**. Todo `groupby` sobre `datos_sem`/`sval`/`_pv` va con
  `observed=True` (sin eso, un categórico arma el producto cartesiano) y los resultados chicos vuelven a texto
  con `_sin_cat`. Para unir con un frame de texto, pasarlo a las mismas categorías (`astype(sval['item'].dtype)`).
  Nada de `.copy()` del panel. La CELDA 8 libera `datos_sem` y `sval`: re-correrla exige re-correr la 7.
  Medición: `docs/auditoria/scripts_v514/bench_ram.py` (código real, vieja vs nueva).
- **nb02, leer el SEPA por sucursal (19b/19c)**: normalizar el EAN del chunk con `.apply(normalizar_ean)` como las
  CELDAS 6 y 9. Con `.str.strip().str.lstrip('0')` sobre el chunk de 300k filas el pico pasó de +0,2 a **+2,1 GB**
  (`docs/auditoria/scripts_nb02_2026-10/bench_lectura_ean.py`). Nada de textos por observación: claves enteras.
- **nb02, caché de la hoja `analisis_detallado`** (`_cache/detalle_<clave>_v1.parquet`): la clave cambia con los
  EANs de la canasta, la provincia y el AMBA de las sucursales en la CELDA 7 (coordenadas, `AMBA_RADIO_KM`), el tipo
  del maestro, los nombres de cadena (CELDA 4) y los mapas de provincia/región de la 19b; cambiarla **relee los 12
  meses de la ventana (~35 min en el Colab gratuito)**. No la cambian las cantidades ni `DETALLE_MESES` (un mes que
  falta se lee y se agrega). La `REGION` del maestro ya no entra (BUG-43).
- **nb02, la 19c necesita la 19b justo antes** (usa sus observaciones y las libera), y **la 19b necesita la CELDA 7**
  (toma la región de la columna `amba` de `suc_geo_clean`, BUG-43). `datos` (CELDA 6) no sirve para esto: filtra a
  sucursales con coordenadas y descarta el día.
- **nb03 (adelantar el mes en curso)**: se corre LOCAL (`python notebooks/03_consolidacion_ultimo_mes.py`; en Colab
  el zip diario de ~7 GB no sube). `ZIP_DIARIO` = zip del mes o carpeta con los días `YYYY-MM-DD`; `CARGA_DIR` = carpeta
  de los semestrales (elige `YYYYA.zip` o `YYYYB.zip` según el mes). El zip que deja en `OUTPUT_DIR` se sube a
  `MyDrive/carga/` y recién ahí se corren los notebooks. Detalle: README, "Correrlo localmente".
- **nb02, región de la 19b/19c (BUG-43)**: AMBA = columna `amba` de la CELDA 7; el resto por la provincia del archivo
  de precios (ISO), que es la de la dimensión provincia de esas hojas. NO usar la `REGION` del maestro.
- **nb02, provincia de la CELDA 7 (BUG-44)**: polígonos de `ar.json` (`GEOJSON_PATH`, Drive) con tolerancia
  `RECLASIF_TOL_KM = 100`: solo se reclasifica lo que cae a más de 100 km de la provincia declarada (12 sucursales del
  maestro). Nada de rectángulos (pasaban Neuquén capital a La Pampa). Sin `ar.json` no reclasifica y avisa. Cambiar la
  provincia o la cadena de alguna sucursal cambia las claves de los cachés de la 19c y de la econometría (relee).
  Antes de tocar la regla: `reclasificacion_celda7.py` (maestro) y `cuadro1_reclasificacion.py` (Cuadro 1 de una corrida).
- **nb02, colores del Excel**: `VERDE_OSCURO = '375623'` (encabezados de todas las hojas y filas de sección de
  `analisis_detallado`, texto blanco) y `VERDE_CLARO = '92D050'` (fila de encabezado de `analisis_detallado`), en la
  CELDA 19; la 19c los usa. Pedido del usuario del 2026-10-16 (antes azules `1F4E79`/`D9E1F2`). No volver a azul.
- **nb09, RAM (Colab gratuito)**: la primera versión colapsó la sesión en Colab (2026-10-21). Ahora: el lector es un
  script aparte (`LECTOR_SRC` en la CELDA 4 -> `nb09_lector.py`, un `subprocess` por archivo: el SO libera todo al
  terminar), lee **por bloques** (`pacsv.open_csv`, `BLOQUE_MB`) con IDs como diccionario (se limpia solo el
  diccionario), y la fase 2b arma producto × sucursal **de a un grupo de productos** (`N_GRUPOS`, row groups del
  parquet). Medido: lector 1,7 GB, notebook < 1 GB (archivos de 16 M filas). Nada de `fork` (pyarrow no es fork-safe).
  Un cambio de formato de los resúmenes exige subir la versión (`RES_DIR = CACHE_DIR / 'v1'`), salvo `ean_suc`, que
  `leer_grupo` reorganiza solo; un cambio de lo que calcula el lector sube `LECTOR_VERSION` y la CELDA 4 relee solo
  los resúmenes viejos que lo necesitan (`_motivo_releer`).
- **nb09, el SEPA trae defectos (versión 2 del lector, 2026-10-21)**: sucursal × producto **repetidos** en un archivo
  ('Cadena 2011' ene-feb 2024, ~880 por quincena; comercio 35, 1 fila en casi todos): unión de días, una sola vez.
  **Provincias** escritas con el nombre ('Buenos Aires' en una sucursal de DIA en todos los archivos 2024-2026, 'Santa
  Fe' en 3 del comercio 1001) o vacías (36 sucursales en 2022-2023): `iso_provincia` del lector; las vacías toman la
  del maestro o no cuentan. **Dos archivos para la misma parte** (`2024B.zip`, agosto, `COMPLETO` días 1-5 y
  `COMPLETOb` días 1-15): `listar_archivos` usa el que cubre más días; el nb08 también desde el 2026-10-22; el nb02
  todavía los SUMA (tarea aparte).
  Cualquier conteo con enteros al cuadrado, en float (el HHI se desbordaba). Comercios: nombres del comercio.csv del
  SEPA (el 47 es Unicoop, no Pasamonte; el 23 Axion; el 4 Estación Lima); banderas por id.
- **nb09, fase 2 (2026-10-22)**: los códigos con texto mal codificado pegado se unen a su EAN con `limpiar_codigo`
  (CELDA 5); en `ean_suc` esas filas están en el row group de su código ORIGINAL, así que los archivos que las tienen
  (`TAGS_BASURA`) se leen enteros en la fase 2b. "Comercio que dejó de publicar" = sin precios en el último mes del
  período (`COM_SIN_PUBLICAR`, desde 2022: 33 en oct-26); desde ago-2026 eso incluye los 8 comercios que el SEPA diario
  (script 03) no trae (`mes_baja_comercios` = '2026-07'). Un hueco temporal en el último mes también cuenta. El precio
  simbólico es relativo: `PRECIO_SIMBOLICO_PCT` (1,25%) de la mediana de precios del último mes.
- **nb08, sucursales apareadas (2026-10-22)**: el relativo de una sucursal es su precio / su precio anterior movido con
  el índice del producto desde entonces (si faltó ≤ `MAX_DIAS_SIN_PRECIO` días). Sin esa imputación, una sucursal que
  vuelve suma de nuevo la variación que ya entró por las otras (el test lo detecta: el índice deja de dar la tendencia).
  El caché `diaria_v2_<clave>` guarda por mes el agregado y el estado (`estado_AAAA-MM.parquet`: pares sucursal ×
  producto + índice de cada producto en los metadatos); cambiar cómo se calculan los relativos exige subir la versión
  del directorio. El último mes no se guarda.
- **Ningún caché mira si cambió el zip** (nb02, nb06, nb07, nb08, nb09): un mes cerrado guardado no se relee aunque se
  reemplace el zip. Cuando salga el semestral oficial 2026B (ago-oct 2026 vienen hoy del SEPA diario, sin 8 comercios),
  borrar esos meses de los cachés: nb06 `output_brecha/_cache/brecha_v3_<clave>/2026-08.parquet` y siguientes; nb08
  `diaria_v2_<clave>/2026-08.parquet` + `estado_2026-08.parquet` y siguientes; nb09 `_cache_nb09/v1/2026-08_p*` y
  siguientes. Defectos de la fuente: `docs/SEPA_TECNICO.md`, "Defectos y cambios de la fuente 2022-2026".
- **nb06, canasta fija**: la fuente de la canasta es `docs/brecha_celiaca/canasta_fija_2022_2026.csv` (tipo, lado,
  EAN, descripción, gramos, subtipo, vigencia, producto y métricas); `gen_nb06.py` arma con él `TIPOS`, `GRAMOS`,
  `VIGENCIA`, `PRODUCTO` (códigos de un mismo producto: entra una vez en la mediana de su lado) y `SUBTIPO` de la CELDA 1.
  Para cambiar un producto: editar el CSV (o rehacerlo con los scripts s7-s10 de `docs/auditoria/scripts_nb06_2026-10/`;
  s11/s12 simulan el nb06 con los zips y lo comparan con un cálculo independiente), regenerar y commitear CSV + generador
  + `.ipynb`. Cambiar un EAN cambia la clave del caché (`_cache/brecha_v3_<clave>/`, un archivo por mes: relee los 58
  meses); gramos, vigencias, pesos y descripciones no. La selección por nombre (`USAR_REGLA_NOMBRE`) queda apagada:
  hacía que la canasta dependiera del `maestro_sepa_completo.csv.gz` que hubiera en el Drive. **La brecha se calcula
  por subtipo** (nunca la mediana del tipo entero: mezcla snacks y crackers según el surtido) y se agrega subtipo → tipo
  → canasta; si se cambia la canasta o el estimador, rehacer la simulación (s11/s12) y los resultados esperados de
  `docs/brecha_celiaca/simulacion_<fecha>/` (otra carpeta con la fecha nueva; la vigente es `simulacion_2026-10-26/`)
  antes de pedir una corrida de Colab.
  En 2023 las marcas masivas con TACC tenían precios controlados (la brecha de 2023 está inflada, §14.8 de
  BRECHA_CELIACA): no "corregirlo" sacando productos.
- **nb06, comparar grupos (BUG-47)**: provincias, regiones, empresas, cadenas y sucursales se comparan con la MISMA
  canasta de 12 subtipos (`_agg_tipo(..., ref_keys)`: el subtipo con < `MIN_SUC_SUBTIPO` sucursales en el grupo toma la
  brecha nacional del período; confiable = `peso_imputado_pct` <= `MAX_PESO_IMPUTADO` y >= `MIN_SUC_AGG` sucursales).
  Nunca renormalizar entre los tipos o subtipos presentes ni comparar la canasta de los tipos que tiene cada sucursal
  (`brecha_tipos_presentes`): mide la composición (DIA, con 2 tipos, daba +77%). La localidad del maestro no sirve como
  mercado (DIA la carga con el nombre de la provincia): la concentración usa el departamento de Georef (`GEOREF_PATH`,
  caché del nb09 en el Drive; la simulación lo recibe con `s11 ... --georef`).
- **Códigos que cambiaron de EAN**: Molinos reemplazó los EANs de sus fideos en sep-oct 2023 y los viejos siguen en ~100
  sucursales con el precio CONGELADO (Spaghetti Lucchetti viejo a $230-274 en 2024-2026 contra $1.042-1.699 del nuevo).
  Un producto empalmado lleva sus códigos con `VIGENCIA` (el viejo hasta el mes anterior al nuevo); nunca sumar un código
  viejo sin cortarlo. El Maestro interno tiene descripciones viejas de EANs reutilizados (`7790070336002` = Spaghetti sin
  TACC Matarazzo en todas las cadenas, "Mostachol 5 Cereales" en el Maestro): identificar por la descripción del SEPA
  y verificar con precios **de todo el período** — con solo 2024-2026, los sin TACC viejos de Matarazzo (`…321800`,
  `…321855`, reemplazados en oct-2023 y congelados después) parecían fideos comunes; en 2022 costaban el doble o el
  triple del común en las mismas sucursales: eran sin TACC genuinos y se empalman. **Los gramos del
  Maestro también pueden estar viejos**: la caja Wakas que reemplazó a la bolsa de 250 g en jun-2024 es de 300 g (el
  Maestro dice 250) y las Porteñitas pasaron de 130 a 139 g con el mismo EAN; contrastar con la presentación que
  publican las cadenas y, si no se sabe desde cuándo cambió, no usar el producto.
- **Canasta de pass-through**: el nb08 la toma por nombre (`CANASTA_EXCEL`), no del `canasta_representativa_*` más
  nuevo; el script de Colab NO nombra su salida `canasta_representativa_*` a propósito (el nb02 y el nb07 la tomarían).
  Cambiar los EANs de la canasta cambia la clave del caché del nb08 (relee todo, ~1,5-2 h); cambiar cantidades no.
- **nb02, una sola referencia del país** (BUG-42): todo "vs país" es el promedio ponderado del Cuadro 1
  (`prom_nac_dict`), CABA es su fila del Cuadro 1, cadenas y barrios van por mediana en el análisis [mediana], y el AMBA
  es la columna `amba` de la CELDA 7 (CABA + Buenos Aires a ≤ 90 km del Obelisco), nunca `PROVINCIA in (CABA, Buenos
  Aires)` ni la `REGION` del maestro. Los acumulados contra el IPC, siempre en el mismo período.

## Git

- Commits **solo con el usuario (Santiago Riverti)**: nunca agregar `Co-Authored-By: Claude` ni otra
  atribución a Claude en commits o PRs.
- Rama `main`, push directo a `origin` (https://github.com/santiagoriverti/precios_minoristas_supermercados). El repo
  es **público** (verificado el 2026-10-16: `raw.githubusercontent` responde y Colab baja los maestros de GitHub). Si
  se vuelve privado, copiar los maestros de `data/` al Drive (README, "Repositorio privado").
- Al cerrar una sesión: actualizar `.claude/memory.md` (bloque ESTADO ACTUAL), `docs/CONTEXTO.md`
  (historial), `docs/BUGS_Y_MEJORAS.md` y lo que corresponda del README, y commitear/pushear todo.

## Mapa de la documentación

| Archivo | Qué tiene |
|---|---|
| `.claude/memory.md` | **Estado y próximos pasos** (bloque de arriba) + handoffs históricos |
| `docs/CONTEXTO.md` | Pipeline, puesta en marcha en otra máquina, historial de cambios |
| `docs/METODOLOGIA.md` | Metodología; nb02 en §4 (desagregación de la variación y hoja `analisis_detallado`); nb07 en §10 (§10.19 = v5.13; §10.20 = v5.14-v5.15); **nb08 v2 en §12, nb09 en §13, canasta de pass-through en §14** |
| `docs/NB02_ANALISIS_VARIACION.md` | **nb02 CELDAS 19b y 19c**: cómo correrlas, cómo leer cada hoja, caché, validación con oct-26, trampas |
| `docs/BUGS_Y_MEJORAS.md` | Defectos abiertos arriba; bugs resueltos con causa y fix |
| `docs/SEPA_TECNICO.md` | Formato SEPA, **defectos y cambios de la fuente 2022-2026** (días con la mitad de los comercios, corte de ago-2026, archivos y filas repetidas, provincias, códigos con basura, precios simbólicos), factor de precio, cadenas, frescos por tipo, caché |
| `docs/BRECHA_CELIACA.md` | **nb06 — brecha celíaca**: estimador intra-sucursal, **canasta fija 2022-2026 (§14: fuentes, reglas, empalmes y vigencias, productos, estimador por subtipo y ponderación ENGHo, advertencias, qué revisar en la corrida, simulación con los 58 meses)**, salidas, agenda para el paper (§13). Lista con métricas: `docs/brecha_celiaca/canasta_fija_2022_2026.csv`; resultados esperados: `docs/brecha_celiaca/simulacion_2026-10-23/`; scripts de la selección, la simulación y la comparación con Colab (s16): `docs/auditoria/scripts_nb06_2026-10/` |
| `docs/PASS_THROUGH.md` | **Pass-through del tipo de cambio**: estado, cómo correr el nb08 con la canasta de 775 productos y qué revisar, cómo rehacer la canasta, variable de precio, advertencias, próximos pasos (tipo de cambio, regresiones) |
| `docs/AUDITORIA_2026-10-22_nb09.md` | **Corrida del nb09 v2 revisada**: controles, panel contra el SEPA crudo, hallazgos de método y de fuente (§4), corrida con los arreglos (§6). Scripts en `docs/auditoria/scripts_nb09_2026-10/` (r1-r8) |
| `docs/auditoria/scripts_nb08_2026-10/` | `validar_real.py`: las celdas reales del nb08 v2 sobre zips locales contra el lector anterior (jul-sep 2024) |
| `docs/AUDITORIA_2026-10-16_nb02.md` | **Última corrida del nb02 revisada** (oct-26 al 15/10): 19b/19c OK, BUG-42 (antes/ahora con los mismos datos, verificado en Colab), lecturas (Vea en jul-26), abiertos, §8 región por coordenadas (BUG-43, simulación), §9 provincia por polígonos (BUG-44), §10 colores, §11 Cuadro 1 de oct-26 antes/después |
| `docs/auditoria/scripts_nb02_2026-10/` | Prototipo ad hoc de la desagregación (oct-26), validación de las CELDAS 19b/19c con datos reales, `simular_valores_documento.py` (rehace la CELDA 20 desde el Excel de una corrida), `comparar_corridas.py` (dos Excel hoja por hoja), `simular_region_19b_19c.py` + `comparar_region_19b_19c.py` (19b/19c reales sobre zips locales, código viejo vs nuevo), `reclasificacion_celda7.py` (la CELDA 7 real sobre el maestro, BUG-44), `cuadro1_reclasificacion.py` (Cuadro 1 de una corrida con la provincia de antes y la de ahora), `validar_amba_maestro.py`, `productos_que_mueven_grupo.py` |
| `docs/AUDITORIA_2026-10-02_v514.md` | **Ultima corrida auditada** (v5.14 al 2026-10-01, Colab gratuito): numeros vigentes, volatilidad de Femenina/Tecnologica, Lavarropas y composicion por rubro (resueltos en la v5.15) |
| `docs/AUDITORIA_2026-09-24_v512.md` | **Revisión de la v5.12**: la brecha con el IPC sale de los frescos, incertidumbre del acumulado, dos defectos (filtro estacional, nivel de frescos revisado cada semana), ronda 2. Sus decisiones (§7) están aplicadas en la v5.13 |
| `docs/AUDITORIA_2026-09-22_v59.md` | Auditoría de la v5.9 + verificación de la v5.10 (§10) y de la v5.11 con los reemplazos de trazabilidad (§11) + PDF y scripts en `docs/auditoria/` |
| `docs/canastas_alternativas/README.md` | Composición de las 6 canastas, cargador, constructor, reemplazos; **canasta fija para el pass-through diario** (775 productos, `canasta_pass_through.py`) |
