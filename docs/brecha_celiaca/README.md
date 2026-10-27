# Canasta fija 2022-2026 de la brecha celíaca (nb06)

`canasta_fija_2022_2026.csv` es la lista de productos con TACC y sin TACC que usa el nb06 desde el 2026-10-23: una fila
por código (EAN). Desde el 2026-10-27 tiene **62 productos en 43 líneas (75 códigos)**: el panel de expertos sacó las galletas de arroz de crackers, donde hay crackers sin TACC equivalentes (regla "equivalentes primero"; BRECHA_CELIACA §14.17 y `docs/EVALUACION_EXPERTOS_2026-10-27_nb06.md`). Antes, desde el 2026-10-26, tenía 67 productos en 45 líneas (80 códigos). La auditoría de la selección
corrigió cuatro errores de las reglas (BUG-49; `docs/AUDITORIA_SELECCION_2026-10-26_nb06.md`). Esa noche, Pepitos pasó
a ser el comparador de con chips y la Opera de 92 g se sumó a la de 220 g en obleas (BRECHA_CELIACA §14.15). Más tarde
los sabores de una misma línea pasaron a contar como un producto y el penne se compara con el Matarazzo común, de la
misma marca que el sin TACC (§14.16). `notebooks/gen_nb06.py` la lee y arma `TIPOS`, `GRAMOS`, `VIGENCIA`,
`PRODUCTO` y `SUBTIPO` de la CELDA 1. Reglas, fuentes y advertencias: `docs/BRECHA_CELIACA.md` §14. Scripts que la
arman: `docs/auditoria/scripts_nb06_2026-10/` (s7 → s10).

`simulacion_2026-10-23/` tiene los **resultados esperados** del nb06 con esta canasta y los zips del Drive del 23/10 (un
CSV por hoja del Excel, y cómo compararlos con una corrida de Colab: `s16_comparar_colab.py`); la primera corrida de
Colab dio igual en las 29 hojas. `simulacion_2026-10-23b/` son los esperados del notebook `46e426b` (BUG-47 y serie
TPD; la corrida de Colab del 2026-10-26 dio igual en las 35 hojas). `simulacion_2026-10-26/` son los del notebook con
BUG-48 (afuera las tiendas online por el nombre; 35 hojas; las corridas de Colab con BUG-48 y con los gráficos
corregidos dieron igual). `simulacion_2026-10-26b/` son los de la canasta corregida (BUG-49; la corrida de Colab de esa noche dio
igual). `simulacion_2026-10-26c/` son los de la TPD del panel corregida, Pepitos y las dos Operas.
`simulacion_2026-10-26d/` son los de los sabores de una línea como un producto y el penne contra el Matarazzo común
(35 hojas). `simulacion_2026-10-27/` son los del notebook **vigente** (equivalentes primero, precios de una empresa
fuera de escala, análisis complementarios de la CELDA 8c y hoja `Resumen`; 48 hojas): contra esa carpeta se compara
la próxima corrida.

`productos_sensibilidad.csv` tiene **todos** los productos que cumplen las reglas de la selección en los subtipos de
la canasta: los 75 códigos de la canasta y 25 más que quedan afuera por la composición espejada, el comparador fijo
de las obleas o por ser sustitutos de un producto equivalente (las galletas de arroz de crackers). `gen_nb06.py` los
pasa a `ADICIONALES`, `LINEA_TODOS` y `SUSTITUTOS` de la CELDA 1: se leen con la canasta y entran solo en los
escenarios de la hoja `Sensibilidad` (CELDA 8c), nunca en la brecha principal. Columnas propias: `linea_todos` (la
línea si entraran todos), `en_canasta`, `motivo` (por qué quedó afuera) y `sustituto`.

Para cambiar la canasta: editar el CSV (o rehacerlo con s9 y s10), correr `python notebooks/gen_nb06.py` y
`python notebooks/test_brecha_celiaca.py`, y commitear el CSV, el generador y el `.ipynb` juntos. Agregar o sacar un
EAN cambia la clave del caché del nb06 (relee el SEPA); cambiar gramos, vigencias, subtipos o descripciones no.

## Columnas

| Columna | Qué es |
|---|---|
| `tipo` | Tipo de la canasta (uno de los 5 con peso ENGHo en `gen_nb06.py`) |
| `lado` | `tacc` (con TACC) o `sin_tacc` |
| `ean` | Código, sin ceros a la izquierda |
| `descripcion` | Descripción del producto (Maestro interno, verificada contra lo que publican las cadenas en el SEPA del 22/10/2026) |
| `gramos` | Presentación en gramos (para pasar a $/100 g) |
| `subtipo` | Subtipo de comparabilidad (forma de los fideos; rellenas, secas, pepas... en galletitas dulces). La selección elige tantos productos con TACC como sin TACC en cada subtipo (en el cálculo cuenta cada línea una vez) |
| `desde`, `hasta` | Vigencia del código (AAAA-MM; vacío = sin límite). Solo en los productos que cambiaron de código: fuera de su ventana, el código no se usa (los códigos viejos de Molinos siguen apareciendo con el precio congelado) |
| `nota` | `empalme «producto»` si el producto tiene más de un código |
| `producto` | Nombre del producto (el mismo en todos sus códigos) |
| `linea` | Lo que entra una vez en la mediana de su lado: los productos de una misma marca y presentación en el subtipo y lado que cuestan lo mismo (sabores o variantes, a ±10% de la mediana de la línea) forman una línea, con el número de variantes en el nombre; un producto sin otras variantes es su propia línea. `gen_nb06.py` junta los códigos de cada línea en `PRODUCTO` (desde el 2026-10-26, noche) |
| `sucursales_dia_mediana_2022_2026` | Mediana mensual de las sucursales con precio por día (nb09, ene-2022 → jul-2026; en los empalmes, la suma de sus códigos vigentes) |
| `caidas` | Meses con cobertura < 35% de su mediana móvil de 13 meses, sin contar jul-2023 ni dic-2023 → mar-2024 (defectos de la fuente) |
| `cobertura_2022_sobre_2026` | Sucursales por día promedio de 2022 / promedio de 2026 |
| `provincias`, `comercios`, `cadenas_grandes` | Provincias, comercios supermercado y cadenas grandes (de 8) con el producto en todo el período (nb09) |
| `pct_cadena_principal` | % de sus sucursal-días que aporta la cadena con más presencia |
| `sucursales_dia_oct2026` | Sucursales con precio por día en oct-2026 (nb09, SEPA diario al 22/10; en los empalmes, sus códigos vigentes) |
| `precio_100g_ultimo_mes` / `ultimo_mes_con_precio` | Mediana nacional de $/100 g en el último mes con precio (zips semestrales del Drive, ene-2022 → oct-2026) |
| `precio_sobre_mediana_con_tacc_subtipo` | Precio $/100 g / mediana de los con TACC del mismo subtipo y mes (mediana 2022-2026). Con TACC: posición dentro de la franja de primera línea (0,6-1,67); sin TACC: su prima |

## Canasta amplia de la oferta actual (nb06b, desde el 2026-10-27)

`canasta_amplia_2025_2026.csv` es la canasta del notebook `06b_brecha_celiaca_canasta_amplia.ipynb`
(BRECHA_CELIACA §16): las mismas reglas que la canasta fija sobre la ventana ago-2025 → oct-2026, con 9 tipos (los 5 de
la canasta fija más pan envasado, harinas y premezclas, alfajores y tapas). La arma
`docs/auditoria/scripts_nb06_2026-10/s18_canasta_amplia.py`; `gen_nb06.py` la embebe en la CELDA 1 del 06b, como la
fija en el 06. `productos_sensibilidad_amplia.csv` es su versión de `productos_sensibilidad.csv` (los que cumplen las
reglas y quedan afuera van a los escenarios de la hoja `Sensibilidad`). `simulacion_06b_2026-10-27/` son los
resultados esperados del 06b (48 hojas): contra esa carpeta se compara su próxima corrida.

Columnas: las mismas de la canasta fija para identificar cada código (`tipo`, `lado`, `ean`, `descripcion`, `gramos`,
`subtipo`, `desde`, `hasta`, `nota`, `producto`, `linea`), y las métricas de la ventana:

| Columna | Qué es |
|---|---|
| `fuente_gramos` | De dónde salen los gramos: `Maestro = cadenas` (coinciden a ±5%), `cadenas (...)` (el consenso de lo que publican las cadenas el 22/10, cuando el Maestro no tiene gramos o está desactualizado), `corrección verificada (s10)` o `Maestro (sin consenso de las cadenas)` |
| `sucursales_mes_mediana_ventana` | Mediana mensual de las sucursales del universo del nb06 con precio, ago-2025 → sep-2026 |
| `provincias`, `comercios`, `cadenas_grandes` | Provincias, comercios supermercado y cadenas grandes (de 8) con el producto en la ventana |
| `pct_cadena_principal` | % de sus sucursal-meses que aporta la cadena con más presencia (tope: 85% sin TACC, 60% con TACC) |
| `precio_100g_ultimo_mes` / `ultimo_mes_con_precio` | Mediana nacional de $/100 g en el último mes con precio |
| `precio_sobre_mediana_con_tacc_subtipo` | Precio $/100 g / mediana de los con TACC del mismo subtipo y mes (mediana de la ventana) |
