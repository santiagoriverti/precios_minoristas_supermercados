# Canasta fija 2022-2026 de la brecha celíaca (nb06)

`canasta_fija_2022_2026.csv` es la lista de productos con TACC y sin TACC que usa el nb06 desde el 2026-10-23: una fila
por código (EAN). `notebooks/gen_nb06.py` la lee y arma `TIPOS`, `GRAMOS`, `VIGENCIA`, `PRODUCTO` y `SUBTIPO` de la
CELDA 1. Reglas, fuentes y advertencias: `docs/BRECHA_CELIACA.md` §14. Scripts que la arman:
`docs/auditoria/scripts_nb06_2026-10/` (s7 → s10).

`simulacion_2026-10-23/` tiene los **resultados esperados** del nb06 con esta canasta y los zips del Drive del 23/10 (un
CSV por hoja del Excel, y cómo compararlos con una corrida de Colab: `s16_comparar_colab.py`); la primera corrida de
Colab dio igual en las 29 hojas. `simulacion_2026-10-23b/` son los esperados del notebook **vigente** (BUG-47: grupos y
sucursales con la misma canasta de subtipos, concentración por departamento; serie TPD de robustez; 35 hojas): contra
esa carpeta se compara la próxima corrida.

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
| `subtipo` | Subtipo de comparabilidad (forma de los fideos; rellenas, secas, pepas... en galletitas dulces). En cada subtipo hay tantos productos con TACC como sin TACC |
| `desde`, `hasta` | Vigencia del código (AAAA-MM; vacío = sin límite). Solo en los productos que cambiaron de código: fuera de su ventana, el código no se usa (los códigos viejos de Molinos siguen apareciendo con el precio congelado) |
| `nota` | `empalme «producto»` si el producto tiene más de un código |
| `producto` | Nombre del producto (el mismo en todos sus códigos) |
| `sucursales_dia_mediana_2022_2026` | Mediana mensual de las sucursales con precio por día (nb09, ene-2022 → jul-2026; en los empalmes, la suma de sus códigos vigentes) |
| `caidas` | Meses con cobertura < 35% de su mediana móvil de 13 meses, sin contar jul-2023 ni dic-2023 → mar-2024 (defectos de la fuente) |
| `cobertura_2022_sobre_2026` | Sucursales por día promedio de 2022 / promedio de 2026 |
| `provincias`, `comercios`, `cadenas_grandes` | Provincias, comercios supermercado y cadenas grandes (de 8) con el producto en todo el período (nb09) |
| `pct_cadena_principal` | % de sus sucursal-días que aporta la cadena con más presencia |
| `sucursales_dia_oct2026` | Sucursales con precio por día en oct-2026 (nb09, SEPA diario al 22/10; en los empalmes, sus códigos vigentes) |
| `precio_100g_ultimo_mes` / `ultimo_mes_con_precio` | Mediana nacional de $/100 g en el último mes con precio (zips semestrales del Drive, ene-2022 → oct-2026) |
| `precio_sobre_mediana_con_tacc_subtipo` | Precio $/100 g / mediana de los con TACC del mismo subtipo y mes (mediana 2022-2026). Con TACC: posición dentro de la franja de primera línea (0,6-1,67); sin TACC: su prima |
