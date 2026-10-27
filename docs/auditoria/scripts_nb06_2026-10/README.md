# Selección de productos para la brecha celíaca (nb06) — scripts del 2026-10-22/23

Los pasos 1-6 arman el Excel de decisión `seleccion_brecha_celiaca_20261022.xlsx`: qué productos con y sin TACC
existen, con qué cobertura por sucursal, cadena y provincia, desde cuándo, qué pares de la misma marca hay y cuánto pesa
cada tipo en el gasto de los hogares. Los pasos 7-10 arman la **canasta fija 2022-2026**
(`docs/brecha_celiaca/canasta_fija_2022_2026.csv`, que `gen_nb06.py` embebe en la CELDA 1), los 11-12 verifican el
nb06 con datos reales, los 13-15 son auxiliares (tablas del documento y caché de la simulación) y el 16 compara una
corrida de Colab con los resultados esperados. Reglas y resultados: `docs/BRECHA_CELIACA.md` §14.

Orden de una corrida completa (datos en carpetas propias; los zips semestrales son los del Drive):

```bash
python -I -X utf8 s7_continuidad.py <trazabilidad nb09 .parquet> <panel mensual nb09 .parquet> <tipos.parquet de s3> continuidad.parquet
python -I -X utf8 s8_precios_zips.py <carpeta con los zips> eans.txt precios_mes
python -I -X utf8 s9_seleccion.py continuidad.parquet seleccion.parquet
python -I -X utf8 s10_precios.py seleccion.parquet precios_mes precios_mes_2 <tipos.parquet de s3> canasta_fija_2022_2026.csv
python notebooks/gen_nb06.py && python notebooks/test_brecha_celiaca.py
python -I -X utf8 s14_superconjunto.py canasta_fija_2022_2026.eans.parquet canasta_fija_2022_2026.csv superconjunto.json
python -I -X utf8 s11_simular_nb06.py <repo> <carpeta con los zips> <ar.json> sim_super 2022-01 --config superconjunto.json --hasta-celda 5
python -I -X utf8 s15_filtrar_cache.py <repo> sim_super/_cache/brecha_v3_<clave> sim_final
python -I -X utf8 s11_simular_nb06.py <repo> <carpeta con los zips> <ar.json> sim_final 2022-01 --georef <georef_sucursales.parquet del nb09>
python -I -X utf8 s12_comparar_simulacion.py <repo> precios_mes precios_mes_2 sim_final
python -I -X utf8 s17_esperados.py sim_final/brecha_celiaca_2026-10.xlsx <repo>/docs/brecha_celiaca/simulacion_<fecha>
python -I -X utf8 s16_comparar_colab.py <brecha_celiaca_2026-10.xlsx de Colab> <repo>/docs/brecha_celiaca/simulacion_2026-10-26c
```

`precios_mes_2` existe porque el 2026-10-23 se hicieron dos extracciones (la segunda con 14 códigos viejos de Molinos
que faltaban); con una sola extracción de todos los EANs, pasar una carpeta vacía en su lugar. s10 y s12 sacan las
filas repetidas entre las dos.

Fuentes: un día del SEPA diario (nombres, presentaciones, cobertura y precios; `...\INECO\SEPA\sepa_diario_minoristas\`),
el Maestro de Productos Interno (`data/`), las salidas del nb09 (`trazabilidad_productos_20220101_20261022.parquet` y
`panel_mensual_productos_20220101_20261022.parquet`) y la ENGHo 2017/18 (`IPC_jubilados/data/cache/`).

| Paso | Script | Qué hace |
|---|---|---|
| 1 | `s1_catalogo_dia.py <carpeta del día> <cat.parquet>` | Lee los zips de un día y guarda las filas (sucursal × producto) de los tipos con dicotomía o que dicen "sin TACC" |
| 2 | `s2_clasificar_catalogo.py <cat.parquet> <Maestro .xlsx> <catalogo.xlsx>` | Regla de "sin TACC" por nombre (variantes S TACC, S/TACC, LIBRE D/GLUTEN, Glutal...; "C/GLUTEN" es con TACC), gramos y cobertura por producto |
| 3 | `s3_tipos_y_formas.py <catalogo.parquet> <tipos.xlsx>` | Tipos con dicotomía (reglas más estrictas) y forma de los fideos |
| 4 | `s4_pares_misma_marca.py <tipos.parquet> <cat.parquet> <candidatos.xlsx>` | Referencias con TACC a base de trigo (marca no celíaca) y pares de la misma marca (tipo, forma, tamaño 0,5-2x) |
| 5 | `s5_historia_nb09.py <candidatos.xlsx> <panel nb09> <ranking nb09> <historia.xlsx>` | Cobertura mensual 2022-01 → 2026-10 de cada candidato, meses con dato, caídas, estabilidad desde 2022 y desde 2024-05 |
| 6 | `s6_consolidar_excel.py <candidatos.xlsx> <historia.parquet> <historia_serie.parquet> <engho2018_gastos.zip> <engho2018_articulos.zip> <salida.xlsx>` | Excel final: pares recomendados (revisados a mano), sin TACC multicadena, historia, cobertura mensual, ponderaciones ENGHo (como % del gasto en los 12 tipos con TACC; el nb06 usa la misma proporción como % del gasto en alimentos) |
| 7 | `s7_continuidad.py <ranking nb09 .parquet> <panel mensual nb09 .parquet> <tipos.parquet de s3> <continuidad.parquet>` | Tabla de candidatos de todo el SEPA: lado (sin TACC por etiqueta del Maestro o del SEPA; con TACC a base de trigo), tipo, cobertura mensual ene-2022 → oct-2026 (serie en `continuidad_serie.parquet`), meses con precio, provincias, comercios súper, cadenas grandes y cadena principal |
| 8 | `s8_precios_zips.py <carpeta con YYYYA.zip/YYYYB.zip> <eans.txt> <carpeta de salida> [desde AAAA-MM]` | Precio mensual por sucursal × EAN (mediana exacta de los días; si hay dos archivos para la misma parte, el que cubre más días) desde los zips semestrales: un parquet por mes |
| 9 | `s9_seleccion.py <continuidad.parquet> <seleccion.parquet>` | (Corregido el 2026-10-26: `\btita\b`, Blue Patna fuera por ser al huevo, oct-nov 2023 tolerados en los empalmes de Molinos y sabores de una línea que pasa; `docs/BRECHA_CELIACA.md` §14.13; esa noche, el empalme de Pepitos 119 g, §14.15.) Reglas de continuidad, caídas, cobertura geográfica y por cadenas, subtipos comparables y marcas celíacas; empalmes con vigencia por código. Guarda el motivo de cada descarte, `_serie.parquet`, `_miembros.parquet` y `_vigencia.json` |
| 10 | `s10_precios.py <seleccion.parquet> <precios_mes> <precios_mes_2> <tipos.parquet de s3> <canasta.csv>` | (2026-10-26, noche: `COMPARADOR_FIJO`, en obleas la Opera de 220 g y la de 92 g, del tamaño del sin TACC (con la de 92 g sola, 2023 quedaba casi sin pares); los precios de los códigos viejos de Pepitos salen del caché de la lectura del superconjunto, en `precios_mes_3` = `precios_mes_2` + esos códigos, con `r32_precios_desde_cache.py`.) Verificación con precios ene-2022 → oct-2026: franja de primera línea del lado con TACC, identidad contra la evolución de su tipo, empalmes (códigos que conviven) y cortes de código (salto en el mes del corte), cobertura en oct-2026 (nb09), gramos contra el SEPA (`GRAMOS_FIJOS` y `DESC_FIJA` con las correcciones verificadas a mano); composición espejada por subtipo → el CSV de la canasta (+ `.verif`, `.eans`, `.empalmes`, `.cortes` y `.serie` en parquet) |
| 11 | `s11_simular_nb06.py <repo> <carpeta con los zips> <ar.json> <salida> [mes_inicio] [--config canasta.json] [--hasta-celda N]` | Corre las celdas REALES del `.ipynb` sobre los zips del Drive (ene-2022 → oct-2026), mide tiempo y pico de RAM de cada celda y guarda los objetos clave. `--config` lee con otra canasta (el superconjunto de s14) y `--hasta-celda 5` corta después de la lectura |
| 12 | `s12_comparar_simulacion.py <repo> <precios_mes> <precios_mes_2> <salida de s11>` | Cálculo independiente de la brecha (desde los precios de s8, con la CELDA 1 del notebook) y comparación con la simulación: precio mensual, brecha por sucursal × mes × tipo y por tipo y mes |
| 13 | `s13_tablas_doc.py <canasta.csv>` | Tablas en markdown de la canasta para `docs/BRECHA_CELIACA.md` §14.5 |
| 14 | `s14_superconjunto.py <canasta.eans.parquet de s10> <canasta.csv> <salida.json>` | Config con todos los candidatos que pasan s9 (para leer el SEPA una sola vez en la simulación; el caché de la canasta final se arma filtrando ese) |
| 15 | `s15_filtrar_cache.py <repo> <caché del superconjunto> <salida de s11>` | Caché de la canasta de la CELDA 1 filtrando el del superconjunto (mismo resultado que leer el SEPA con esa canasta) |
| 16 | `s16_comparar_colab.py <brecha_celiaca_AAAA-MM.xlsx> <carpeta de esperados>` | Compara hoja por hoja el Excel de una corrida (Colab) con los resultados esperados (filas de un solo lado y diferencia máxima de cada columna). La primera corrida de Colab (2026-10-23) dio 29 hojas iguales a `docs/brecha_celiaca/simulacion_2026-10-23/`; con el notebook vigente (BUG-47) la referencia es `simulacion_2026-10-23b/` (30 hojas) |
| 17 | `s17_esperados.py <Excel de la simulación> <carpeta de salida>` | Arma la carpeta de resultados esperados (un CSV por hoja, sin `Leeme`, `Comparacion_productos` ni `Detalle_producto`) |

**Revisión de la primera corrida de Colab (2026-10-23, `docs/AUDITORIA_2026-10-23_nb06.md`)**, sobre el Excel de Colab
y los objetos de la simulación (`sim_final/`, iguales a Colab):

| Script | Qué hace |
|---|---|
| `r1_resumen_excel.py <Excel> [hoja ...]` | Forma, columnas y primeras filas de cada hoja (o de las pedidas, completas) |
| `r2_series.py <Excel>` | Series mensuales de la canasta (todas y panel) con la brecha y las sucursales de cada tipo |
| `r3_subtipos_mes.py <sim_final> [tipo ...]` | Serie mensual por subtipo (mediana entre sucursales) y sucursales |
| `r4_lados_mes.py <sim_final> <subtipo> [desde] [hasta]` | Precio de cada lado del subtipo por mes y $/100 g nacional y sucursales de cada producto |
| `r5_sucursal_y_localidad.py <Excel> <sim_final>` | Canasta por sucursal según cuántos tipos tiene, combinaciones de tipos y la hoja `Concentracion` contra las empresas de cada "localidad" |
| `r6_variantes_imputacion.py <sim_final> <Excel> [K]` | La imputación de la serie mensual hoy (control: = Excel) y cuatro variantes (arrastre de a lo sumo K meses, referencia local de 13 meses, dato propio después de K meses) |
| `r7_imputados.py <sim_final>` | Rachas de subtipo-mes imputados en las dos series (cálculo independiente de la hoja `Imputaciones`) |
| `r8_canasta_comparable_grupos.py <sim> <Excel> [MIN]` | Canasta de 12 subtipos fijos por provincia, región, empresa y cadena con la brecha nacional en los subtipos sin datos (cálculo independiente de la CELDA 8 vigente; si el Excel es del notebook vigente, compara sus hojas de grupos: dif. 1e-13) |
| `r9_canasta_comparable_sucursal.py <sim> <Excel>` | Canasta comparable por sucursal y mes (cálculo independiente) contra `sim_brecha_suc_mes.parquet` de la simulación del notebook vigente (dif. 1e-13 en 123.906 sucursal-mes) |
| `r10_tpd_independiente.py <sim> <Excel>` | Serie TPD (CELDA 8b) con otro algoritmo: por subtipo, LSQR de scipy sobre el diseño completo sin normalizar (una indicadora por celda sucursal-mes, por producto y por sin TACC × mes), en los dos universos, contra la hoja `TPD_subtipos` de la simulación del notebook vigente (meses con dato propio) |
| `r11_saladas_composicion.py <sim> <Excel> [tipo]` | Por qué la TPD de saladas queda debajo de la descriptiva: brecha por sucursal-mes de cada subtipo por año (mediana contra promedio geométrico) y composición de cada lado por producto y año con su nivel TPD (`TPD_productos`) |
| `r12_tpd_vs_descriptiva_subtipo.py <sim> <Excel> [tipo] [desde] [hasta]` | TPD de cada subtipo del tipo (`TPD_subtipos`) contra la mediana del subtipo-mes antes de imputar, sus sucursales y el valor que arrastra la serie mensual (panel balanceado) |

**Revisión completa de una corrida de Colab (2026-10-26, `docs/AUDITORIA_2026-10-26_nb06.md`)**, además de `s16`:

| Script | Qué hace |
|---|---|
| `r13_comparar_excels.py <Excel A> <Excel B> [tol]` | Las 38 hojas celda por celda (también `Leeme`, `Comparacion_productos` y `Detalle_producto`, que `s16` deja afuera); si solo cambia el orden de filas casi empatadas, lo dice |
| `r14_comparar_cache.py <zip del Drive> <carpeta vacía> <caché local brecha_v3_xxx>` | El caché de `output_brecha/_cache/` que baja el Drive contra el de la simulación: mismos meses y mismos datos (no extrae si el zip trae rutas peligrosas) |
| `r15_comparar_mapas.py <mapa A> <mapa B>` | El mapa por sucursal sin los identificadores aleatorios de Folium, y el JSON de los popups (sucursales y mes de cada una) |

**Revisión de datos y método frente al objetivo (2026-10-26, `docs/REVISION_METODOLOGICA_2026-10-26_nb06.md`)**, sobre
la simulación con el caché (`sim_v4`, igual a Colab):

| Script | Qué hace |
|---|---|
| `r16_nivel_tiempo_cba.py <sim>` | Pesos de los subtipos (iguales contra disponibilidad), composición del panel, índices de precio de cada lado y costo mensual con las cantidades de la CBA |
| `r17_concentracion_cadenas_disponibilidad.py <sim>` | Concentración dentro de cada empresa, regresión con efectos de empresa y región, competencia por radio, canasta núcleo por empresa, disponibilidad sin TACC y brecha por tipo de local |
| `r18_catalogo_comparador.py <catálogo> <canasta_fija_2022_2026.csv>` | Catálogo del SEPA del 22/10: fideos con TACC de DIA por marca y precio, y cuánto de la oferta sin TACC cubre la canasta fija |
| `r19_niveles_por_lado_concentracion.py <sim>` | Nivel de cada lado (con y sin TACC) por sucursal contra el HHI, por empresa |

**Auditoría de la selección de productos (2026-10-26, `docs/AUDITORIA_SELECCION_2026-10-26_nb06.md`)**. Corre sobre la
tabla de s9, la canasta del 2026-10-23, el catálogo del 22/10 y los maestros. La etiqueta sin TACC se contrastó además a
mano con el listado ALG de ANMAT (`listadoalg.anmat.gob.ar`).

| Script | Qué hace |
|---|---|
| `r20_etiquetas_canasta.py <canasta.csv> <seleccion.parquet> <cat_20261022.parquet> <cat_..._comercios.parquet> <maestro_sepa_completo.csv.gz> [salida]` | Cómo describe cada cadena cada código de la canasta el 22/10, si dice sin TACC, y qué dice el maestro del SEPA |
| `r21_descartes.py <seleccion.parquet> <salida.csv> [n]` | Los descartados con más cobertura por tipo y lado, con el motivo |
| `r22_pasan_s9.py <seleccion.parquet> <canasta.csv> <canasta.verif.parquet>` | Los que pasan s9 por subtipo y lado y si quedaron en la canasta |
| `r23_marcas_dudosas.py <Maestro .xlsx> <maestro_sepa_completo.csv.gz> <continuidad.parquet> <regex marcas> [regex prefijos]` | Todos los productos de una marca o fabricante (prefijo GS1) en los dos maestros y en la tabla de continuidad |
| `r24_fuera_que_pasarian.py <seleccion.parquet> [lado]` | Los que quedaron fuera por el subtipo (o por ingrediente sin gluten) y pasan las demás reglas o fallan una sola |
| `r25_regex_subtipos.py <seleccion.parquet>` | Efecto del error `tita\b` (atrapaba "galletita") y lo que en saladas cae fuera por no coincidir con ningún patrón |
| `r26_alternativas.py <canasta.csv> <precios_mes> <precios_mes_2> <sim> <salida.csv>` | Brecha con cada corrección posible sobre la canasta del 2026-10-23 (estimador del nb06 sin imputación; reproduce `sim_bt_sub` exacto) |
| `r27_comparar_canastas.py <precios_mes> <precios_mes_2> <sim> <salida.csv> nombre=canasta.csv[+eans] ...` | Lo mismo para canastas armadas con s10 (por subtipo, tipo y canasta; sucursal-meses con los dos lados) |
| `r29_cobertura_subtipos.py <sim> <cat_20261022.parquet>` | Sucursales con los dos lados por subtipo y año, y en cuántas sucursales del sin TACC está cada candidato con TACC el 22/10 (con chips, obleas, pepas) |
| `r30_tpd_panel_alternativa.py <carpeta de esperados>` | TPD del panel con el subtipo sin pares movido con el MISMO subtipo en todas las sucursales (en lugar de con los demás de su tipo): subtipo-mes, tipo y canasta |
| `r31_panel_con_todas.py <sim> <Excel>` | La misma idea en la descriptiva del panel (imputar con la variación del subtipo en todas las sucursales en lugar de arrastrar) |
| `r32_precios_desde_cache.py <caché brecha_v3_xxx> <precios_mes_2> <salida> <ean> ...` | Precio mensual por sucursal × EAN en el formato de s8 tomado del caché del nb06 de la lectura del superconjunto (la columna `precio` del caché es la misma mediana exacta), junto con los archivos de `precios_mes_2`: así s10 verifica códigos que no estaban en la extracción de s8 (los viejos de Pepitos) sin otra lectura |
| `r28_numeros_clave.py <carpeta de esperados> [otras ...]` | Números clave de una o varias carpetas de esperados (s17), lado a lado: brecha por tipo y subtipo, canasta por año, grupos confiables, concentración, imputaciones y TPD (la tabla del README de cada carpeta) |

**Salidas intermedias de la corrida del 2026-10-23** (precios extraídos, selección, verificación, simulación con el
caché del nb06; ~315 MB): en la PC del INECO, `C:\Users\sriverti\proyectos\nb06_brecha_celiaca_20261023\` (README
adentro). En otra PC se rehacen con los comandos de abajo (extracción ~70 min + lectura del nb06 ~40 min).

Correr con `python -I -X utf8` (los zips del SEPA son datos bajados de internet). `precios_mes_2` es una segunda
extracción con los códigos viejos de Molinos que no estaban en la primera lista (s10 y s12 sacan las filas repetidas).

Hallazgos que importan para elegir productos:

- Molinos cambió los EANs de sus fideos en sep-oct 2023 (p. ej. Spaghetti Matarazzo 500 g: `7790070318640` →
  `7790070336309`; los dos conviven unos meses). Una serie larga del lado con TACC tiene que empalmar el EAN viejo con
  el nuevo, verificando con precios.
- El Maestro interno tiene descripciones viejas para EANs reutilizados: `7790070336002` es el spaghetti sin TACC
  Matarazzo 500 g según todas las cadenas, y el Maestro dice "Mostachol 5 Cereales". Identificar por la descripción del SEPA.
- Las líneas sin TACC de marcas masivas (Matarazzo, Exquisita, La Salteña, Oreo, Preferido, Terrabusi) aparecen entre
  sep-2023 y jul-2025. Lo continuo desde 2022 son marcas celíacas (Smams, Aglu, Crackines, Binfinit, Schär, Blue Patna,
  Santa María, Happy Food), que no tienen versión con TACC.
- En el SEPA diario de oct-2026 aparece Farmacity (comercio 24), y el zip del comercio 36 viene vacío todos los días.
- Con los precios 2022-2026 (pasos 8 y 10): los códigos viejos de Molinos siguen apareciendo en ~100 sucursales con el
  precio CONGELADO después del cambio (Spaghetti Lucchetti viejo a $230-274 todo 2024-2026 contra $1.042-1.699 del
  nuevo): cada código lleva una vigencia. Los sin TACC viejos de Matarazzo (`7790070321800` spaghetti, `…321855`
  tirabuzón, `…321794` penne) son genuinos: en 2022 costaban 2-3 veces el Matarazzo común en las mismas sucursales;
  con solo 2024-2026 (precio congelado) parecían fideos comunes. Wakas pasó en jun-2024 de la
  bolsa de 250 g a la caja de 300 g con códigos nuevos (el Maestro dice 250 g para los dos); desde ago-2024 Cencosud
  publica la bolsa como alias de la caja. Porteñitas cambió de 130 a 139 g sin cambiar el código y sin fecha conocida
  (afuera). Detalle: `docs/BRECHA_CELIACA.md` §14.4.
