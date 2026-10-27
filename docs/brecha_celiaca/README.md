# Canasta fija 2022-2026 de la brecha celíaca (nb06)

`canasta_fija_2022_2026.csv` es la lista de productos con TACC y sin TACC que usa el nb06 desde el 2026-10-23: una fila
por código (EAN). Desde el 2026-10-26 tiene **67 productos en 45 líneas (80 códigos)**. La auditoría de la selección
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
`simulacion_2026-10-26d/` son los del notebook **vigente** (además, los sabores de una línea como un producto y el
penne contra el Matarazzo común; 35 hojas): contra esa carpeta se compara la próxima corrida.

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
