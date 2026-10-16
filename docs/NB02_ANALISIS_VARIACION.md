# nb02 — Análisis de la variación de la canasta (CELDAS 19b y 19c)

Guía práctica para correr, leer, validar y seguir desarrollando el análisis de la variación de precios de
la canasta del nb02 (`notebooks/02_evolucion_canasta_representativa.ipynb`, fuente `notebooks/gen_nb02.py`).
El método formal está en `docs/METODOLOGIA.md` §4 ("Desagregación de la variación mensual" y "Hoja
analisis_detallado"). Estado y pendientes: bloque de arriba de `.claude/memory.md`. Última corrida revisada (oct-26 al
15/10, primera en Colab): `docs/AUDITORIA_2026-10-16_nb02.md`.

## Qué es

Cuando se publica "la canasta Media subió X% en el mes", el nb02 explica ese número dentro del mismo
Excel `canasta_analisis_{PERIODO}.xlsx`:

| Celda | Hoja(s) | Qué responde |
|---|---|---|
| **19c** | `analisis_detallado` (**primera hoja**) | Cuadro tipo informe: índice y variación % de la canasta por **rubro y categoría**, **región**, **provincia**, **cadena** (supermercado) y **tipo de sucursal**, en los últimos 12 meses y por **semana** del mes anterior y del mes en curso. |
| **19b** | `Resumen_variacion`, `Productos`, `Grupos`, `Rubros`, `Cadenas`, `Provincias`, `Regiones`, `Tipo_sucursal`, `Aporte_prod_x_cadena`, `Var_prod_x_cadena`, `Subas_y_bajas`, `Mes_parcial`, `Serie_diaria` | **Cuántos puntos** de la variación del último mes aporta cada producto, rubro, cadena, provincia, región y tipo (aditivo), cuánto es **arrastre** de fin del mes anterior y cuánto suba nueva. |

La 19c dice **cuánto subió cada grupo** (con el mismo método que la serie oficial); la 19b dice **cuánto
aporta cada grupo al total** (los aportes suman). Para el informe: titular con el Total, apertura con la
19c, y "quién explica la suba" con la 19b.

## Configuración (CELDA 1)

```python
DESAGREGAR_CANASTAS = ['cantidad_03']   # 19b: canastas a desagregar ([] = ninguna)
DETALLE_CANASTA = 'cantidad_03'         # 19c: canasta de la hoja analisis_detallado (None = no se arma)
DETALLE_MESES = 12                      # 19c: meses completos en columnas (base = el mes anterior al primero)
DETALLE_MIN_SUCURSALES = 10             # 19c: mínimo de sucursales para mostrar un grupo
```

La Media (`cantidad_03`) usa los nombres de hoja pelados; otra canasta en `DESAGREGAR_CANASTAS` agrega sus
hojas con el sufijo `_<nombre corto>` (truncado a 31 caracteres).

## Cómo correrlo en Colab

1. Ejecutar el nb02 entero ("Ejecutar todo") o, si ya se corrió hasta la CELDA 19, correr **19b y después
   19c** (la 19c usa las observaciones que deja la 19b; si se corre sola avisa y no hace nada).
2. Tiempos y memoria:
   - **19b**: relee del ZIP el mes anterior completo y el mes en curso, solo con los EANs de las canastas
     (~3-4 min en una PC). Pico de RAM medido: **+357 MB** (la CELDA 6 suma +422 MB con el mismo archivo).
   - **19c, primera corrida**: lee del SEPA por sucursal los meses viejos de la ventana (hasta 12 con
     la configuración default). **Medido en el Colab gratuito el 2026-10-16: 12 meses en 2.069 s (~35 min,
     158-182 s por mes), una sola vez.** Los guarda agregados en el caché del Drive
     (`output_canasta/_cache/detalle_<clave>_v1.parquet`; oct-26 dejó `detalle_ea281ee7_v1.parquet` con 13 meses).
   - **19c, corridas siguientes**: usa el caché y no lee nada nuevo del SEPA salvo un mes que falte
     (el mes que se cerró). Pico de RAM medido: **+307 MB**.
3. La CELDA 20 (Valores_Documento) agrega su hoja al final; `analisis_detallado` queda primera. Desde el
   2026-10-16 (BUG-42) esa hoja usa el país del Cuadro 1 como única referencia, el AMBA por coordenadas y los
   acumulados contra el IPC en el mismo período (`docs/METODOLOGIA.md` §4, "Referencias, AMBA y valores del
   documento técnico"). **Ojo**: el AMBA de la 19b/19c todavía es la `REGION` del maestro (ver trampas abajo).

**La clave del caché de la 19c** cambia (y entonces se releen los 12 meses) si cambian: los EANs de la
canasta, la región o el tipo de alguna sucursal en `maestro_sucursales_completo.xlsx`, los nombres de
cadena de la CELDA 4 (`NOMBRES_COMPUESTOS`/`NOMBRES_SIMPLES`) o los mapas de provincia/región de la 19b.
Cambiar solo las cantidades NO cambia la clave (las medianas no dependen de las cantidades). Borrar el
`.parquet` fuerza la relectura.

## Cómo leer la hoja `analisis_detallado`

- **Columnas**: los últimos 12 meses completos (si hoy es 15/10: oct-25 a sep-26), el mes en curso si es
  parcial (`oct-26 (al 15/10)`), una columna vacía y las semanas: 1S = días 1-7, 2S = 8-14, 3S = 15-21,
  4S = 22 a fin de mes, del mes anterior (las 4) y del mes en curso (solo las completas: al día 15 van 1S
  y 2S; la 3S tiene un solo día y no va).
- **Bloque ÍNDICE**: base = el mes anterior a la primera columna = 100 (si la primera es oct-25, la base es
  sep-25). Así la columna del último mes completo menos 100 es la **variación interanual**. La semana es el
  nivel del mes anterior × (canasta con las medianas de la semana / canasta con las del mes anterior).
- **Bloque VARIACIÓN %**: los meses contra el mes anterior (la columna parcial contra el último mes
  completo: es la variación oficial publicada, p. ej. +1,75% en oct-26 al 15/10); las semanas contra la
  semana anterior (la primera semana queda vacía).
- **Pond.**: participación de cada rubro/categoría en el costo de la canasta en el mes base. Con la
  canasta completa, Total = Σ Pond × índice del rubro / 100 (la celda avisa si no se cumple).
- **Sucursales / Productos**: con precio en el último mes completo. Se muestran los grupos con al menos
  `DETALLE_MIN_SUCURSALES` sucursales; los demás quedan listados en las notas al pie.
- **Filas**: Total (serie oficial); rubros SEPA (columna `rubro` de la hoja Selección: Almacén, Frescos,
  Perfumería, Limpieza, Bebidas, Congelados) con sus categorías; regiones (AMBA, Pampeana, Noroeste,
  Noreste, Cuyo, Patagonia y "Buenos Aires s/ubicar" = sucursales bonaerenses fuera del maestro);
  provincias; cadenas ordenadas por cantidad de sucursales; tipo de sucursal.
- **Ojo**: la variación de una región/cadena es una mediana (como la oficial) y no se suma a la del Total.
  El aporte aditivo de cada grupo está en las hojas `Cadenas`, `Regiones`, etc. de la 19b (columna
  `aporte_equiv_sobre_oficial_pp`). La variación de octubre de cada grupo en la 19c es exactamente la
  columna de control `var_mediana_grupo_%` de esas hojas.
- Un rubro con un solo producto (muchas categorías de la Media) se mueve a saltos: es la mediana de un
  producto. Para conclusiones, mirar el rubro, no la categoría.

## Cómo leer las hojas de la 19b

- `Productos`: `aporte_oficial_pp` = puntos de la variación oficial que aporta cada producto (suman
  exacto); `arrastre_pp` + `nuevo_pp` = aporte (arrastre = la suba ya estaba en la última semana del mes
  anterior). `aporte_panel_pp` y `var_media_sucursales_%` son la versión panel (media de sucursales).
- `Cadenas`/`Provincias`/`Regiones`/`Tipo_sucursal`: `aporte_pp` suma la variación del panel apareado;
  `aporte_equiv_sobre_oficial_pp` la reescala a la oficial (esa es la que se cita);
  `var_mediana_grupo_%` es el control con el método oficial dentro del grupo (= variación de la 19c).
- `Grupos`: los 4 grandes grupos del prototipo (Alimentos, Bebidas, Limpieza y papeles, Higiene y
  cuidado personal). **No son los rubros SEPA de la 19c**: para rubros SEPA usar `analisis_detallado`.
- `Mes_parcial`: ventanas de días (mes anterior completo vs mes en curso = oficial; mismos días; períodos
  consecutivos; dentro del mes anterior) y el arrastre.

## Resultado de referencia: Media, oct-26 al 15/10 (validación del 2026-10-15)

Oficial +1,748% ($673.534 → $685.307); arrastre +1,479 pp y suba nueva +0,269 pp; panel apareado +1,971%
(2.927 sucursales, 91.650 pares). Con la hoja `analisis_detallado` (corrida de validación con
DETALLE_MESES = 2, base jul-26):

| Fila | sep-26 | oct-26 (al 15/10) | 1S oct | 2S oct |
|---|---:|---:|---:|---:|
| Total Media | +1,81 | **+1,75** | −0,20 | +1,00 |
| Perfumería (Pond 21,8) | +2,55 | +2,69 | −1,19 | +1,12 |
| Frescos (20,0) | +2,18 | +1,39 | +0,26 | −0,06 |
| Almacén (18,4) | +1,75 | +1,24 | +0,22 | +0,52 |
| Bebidas (16,4) | +0,78 | +0,33 | −0,25 | +0,80 |
| Limpieza (15,0) | +0,99 | +2,53 | +0,31 | +1,99 |
| Congelados (8,4) | +2,68 | +2,63 | −0,33 | +2,94 |
| AMBA | +2,30 | +1,64 | −0,24 | +1,15 |
| Pampeana | +1,70 | +1,25 | −0,10 | +0,98 |
| Noroeste | +1,09 | +2,52 | −0,08 | +1,46 |
| Noreste | +1,39 | +1,46 | +0,54 | +0,91 |
| Cuyo | +0,77 | +2,98 | +0,81 | +1,50 |
| Patagonia | +1,63 | +1,04 | +0,18 | +0,48 |

## Primera corrida en Colab: oct-26 al 15/10 (2026-10-16)

Dio exactamente lo validado: oficial +1,748%, medianas 69/69, arrastre +1,479 pp, panel +1,971% (2.927 sucursales,
91.650 pares); `analisis_detallado` primera de 39 hojas, sin AVISO. Con la ventana completa (base sep-25 = 100):

- Pond. (mes base sep-25): Perfumería 21,55, Frescos 19,92, Almacén 19,71, Bebidas 15,80, Limpieza 14,61,
  Congelados 8,41. Cambian con el mes base (con base jul-26 daban 21,8/20,0/18,4/16,4/15,0/8,4).
- Interanual a sep-26 (columna sep-26 − 100): Total +26,5; Bebidas +30,5; Perfumería +29,6; Limpieza +28,7;
  Frescos +27,2; Congelados +24,2; Almacén +18,8. AMBA +28,5; Cuyo +19,9; Noroeste +20,6.
- **Vea bajó precios en jul-26** (19 de 67 productos −10 a −28%, sostenido en agosto): por eso Cuyo, el Noroeste y sus
  provincias caen en jul-26 y Vea rebota +4,05% en oct (mayor aporte por cadena, 0,40 pp del panel). Para ver qué
  productos mueven un grupo en un mes: `docs/auditoria/scripts_nb02_2026-10/productos_que_mueven_grupo.py` sobre el
  caché `detalle_*.parquet`.
- La suba de octubre es casi toda arrastre: 1,48 de los 1,75 pp ya estaban en la última semana de septiembre.

## Validación y tests

- `python notebooks/test_desagregacion_variacion.py` — 19b sobre ZIPs sintéticos (sumas exactas, cálculo
  independiente, pesos y centavos, dos canastas, mes anterior en otro semestre).
- `python notebooks/test_analisis_detallado.py` — 19c sobre ZIPs sintéticos de 5 meses: cada fila contra un
  cálculo independiente (listas + `statistics.median`), Total = serie oficial, Total = Σ Pond × rubros,
  grupos omitidos, hoja primera y única seleccionada, caché (segunda corrida sin releer; maestro cambiado →
  relee) y mes en curso completo.
- Con datos reales (necesitan `psutil`; los insumos no están en el repo):
  `docs/auditoria/scripts_nb02_2026-10/validar_desagregacion_19b.py` (19b contra el prototipo: todas las
  hojas iguales, dif. relativa < 1e-15) y `validar_analisis_detallado_19c.py` (19c contra la serie
  oficial, la Serie_precios, la columna de control de la 19b y las observaciones del prototipo: 6 OK).
  El prototipo ad hoc que se portó está en la misma carpeta (`prototipo_*.py`).

## Problemas conocidos y trampas

- **RAM al leer el SEPA**: normalizar el EAN del chunk con `.apply(normalizar_ean)` (como las CELDAS 6
  y 9). Con `.str.strip().str.lstrip('0')` sobre el chunk de 300k filas el pico pasaba de +0,2 a
  **+2,1 GB** (`bench_lectura_ean.py`). Tampoco armar textos por observación (millones de strings): la 19c
  usa claves enteras para las semanas.
- `datos` (CELDA 6) no sirve para esto: filtra a sucursales con coordenadas y descarta el día. El universo
  de la 19b/19c es el de la CELDA 9 (todas las observaciones).
- "AVISO: no hay observaciones de la CELDA 19b": correr la 19b y después la 19c (la 19c libera las
  observaciones al terminar; para re-correrla hay que re-correr la 19b).
- Un mes de la ventana que no está en los ZIPs del Drive deja vacías esas columnas para los grupos (lo
  avisa). El Total y los rubros salen de la CELDA 9 (desde `MES_INICIO_HISTORICO`).
- Mejora posible (no hecha): leer el CSV prefiltrando las líneas por EAN antes de `pd.read_csv` bajaría la
  lectura ~5x (la 19c tarda casi todo en parsear filas de productos que no usa). Validar contra el lector
  actual antes de cambiarlo.
- **AMBA de la 19b/19c = `REGION` del maestro**, que marca AMBA a ~100 sucursales de DIA del interior bonaerense
  (localidad "BUENOS AIRES": Mar del Plata, Tandil, Pergamino). El AMBA de oct-26 (1.819 sucursales) las incluye.
  Las CELDAS 16/20 ya usan coordenadas (BUG-42); pasar la 19b/19c a coordenadas cambia la clave del caché de la 19c
  (relee 12 meses una vez). `docs/auditoria/scripts_nb02_2026-10/validar_amba_maestro.py` muestra el problema.
- **Provincia**: la 19b/19c usan el código ISO del archivo de precios (CABA 1.131 sucursales en oct-26); el Cuadro 1,
  el maestro con reclasificación por coordenadas (CABA 834). Las cantidades de sucursales no se comparan entre hojas.
- **~540 sucursales fuera del maestro** (2.959 en el panel, 2.419 en el maestro) entran a la 19b/19c pero no al
  Cuadro 1: "Cadena 24" (332 sucursales, 9 de 69 productos, sin identificar), parte de Carrefour Express (511 contra
  386) y de Toledo (27 contra 13). Las cadenas de 2-9 productos de la 19c (Cadena 24, 23, 6) no representan la
  canasta: falta un mínimo de productos además de `DETALLE_MIN_SUCURSALES`.
