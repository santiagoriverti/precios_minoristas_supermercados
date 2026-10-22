# Pass-through del tipo de cambio a precios — guía de trabajo

Última actualización: 2026-10-22 (cierre de sesión).

**Objetivo**: estimar cuánto y qué tan rápido pasa el tipo de cambio a los precios de supermercado, con frecuencia
**diaria** del **01/01/2022 al 20/10/2026**, con la **misma canasta todos los días** y pudiendo desagregar el efecto por
grupo del IPC y tipo de producto.

Este documento junta todo lo de esa línea de trabajo. Detalle de la selección: README de `docs/canastas_alternativas/`
(sección "Canasta fija para el pass-through diario"); del nb08: README, sección `08_canasta_diaria`; método:
`docs/METODOLOGIA.md` §12 (nb08) y §14 (canasta); defectos del SEPA que afectan la serie: `docs/SEPA_TECNICO.md`,
"Defectos y cambios de la fuente 2022-2026".

---

## 1. Estado

| Pieza | Estado | Dónde |
|---|---|---|
| Canasta fija (775 productos) | **Lista** (commit `fa1144d`) | `docs/canastas_alternativas/canasta_pass_through.py` → `canasta_pass_through_20220101_20261020.csv` |
| Excel que lee el nb08 | **En el Drive del usuario** (lo armó con el script de Colab) | `MyDrive/carga/output_canasta/canasta_pass_through_2026-10.xlsx` (canasta en `cantidad_01`) |
| Variable de precio diaria | **nb08 v2 lista** (commit `a1f4522`), por defecto con esa canasta. **Falta correrla en Colab** | `notebooks/gen_nb08.py` → `notebooks/08_canasta_diaria.ipynb` |
| Tipo de cambio diario | No empezado | — |
| Regresiones | No empezadas | — |

---

## 2. Correr el nb08 (Colab)

1. Verificar que estén en el Drive:
   - `MyDrive/carga/2022A.zip` … `2026B.zip` (en el `2026B.zip`, julio es el oficial y agosto-octubre de 2026 están
     armados con el script 03 desde el SEPA diario, hasta que salga el semestral oficial; no reemplazarlo por el de
     `salida_consolidada` de la PC del INECO, que trae solo julio y octubre);
   - `MyDrive/carga/output_canasta/canasta_pass_through_2026-10.xlsx`.
2. Abrir el nb08 con el badge del README y **Ejecutar todo**. No hace falta tocar la CELDA 1: los valores por defecto son
   `CANASTA_COL = 'cantidad_01'`, `CANASTA_EXCEL = '/content/drive/MyDrive/carga/output_canasta/canasta_pass_through_2026-10.xlsx'`,
   `FECHA_INICIO = '2022-01-01'`, `FECHA_FIN = '2026-10-20'`, `MAX_DIAS_SIN_PRECIO = 31`, `RELATIVO_MAX = 4.0`,
   `MIN_COBERTURA_DIA = 0.75`, `ALERTA_ESLABON = 0.15`. Si Colab muestra una versión vieja del notebook, borrar la copia
   de `Mi unidad/Colab Notebooks/` y volver a abrir el badge.
3. La primera vez lee los 58 meses (~1,5-2 h en el Colab gratuito, menos de 1 GB de RAM) y guarda cada mes cerrado en
   `MyDrive/carga/output_canasta/_cache/diaria_v2_<clave>/` (`AAAA-MM.parquet` + `estado_AAAA-MM.parquet`). Si Colab se
   corta, volver a ejecutar: sigue desde el caché. Las corridas siguientes leen solo el último mes.
4. Salidas en `MyDrive/carga/output_canasta/`:
   - `canasta_diaria_pass_through_<primer día>_<último día>.xlsx` (con los defaults, `..._20220101_20261020.xlsx`):
     `Serie_diaria`, `Resumen_mensual`, `Composicion`, `Indices_por_grupo`, `Precios_diarios`, `Precios_apareados`, `Notas`;
   - `panel_diario_pass_through_<...>.parquet` y `.csv.gz`: una fila por producto y día (insumo de las regresiones).

**Qué revisar en la salida** (pasarle a Claude la salida impresa, el Excel y el panel `.parquet`):
- La CELDA 3 dice 775 productos y el nombre "Pass-through".
- La CELDA 4 avisa que `2024B.zip` trae dos archivos para la parte 1 de agosto 2024 y usa `COMPLETOb` (días 1-15).
- `productos_con_dato` debería ser 775 todos los días (la canasta se eligió con precio todos los días según el nb09);
  si algún día falta un producto, ver cuál en `Precios_diarios`. Los únicos días calendario sin dato del SEPA son el
  31/10/2023 y el 10/05/2026 (no se completan).
- `cobertura_incompleta`: días con menos del 75% de las observaciones de la mediana de su mes. Esperables: del 16 al
  28/07/2023 (el SEPA trae la mitad de los comercios) y días sueltos; en la validación de jul-sep 2024 se marcaron el 18
  y 19/07 y el 03/09/2024. Se marcan, no se borran: decidir en las regresiones (dummy o excluirlos).
- Diferencia entre `valor_canasta` (medianas) y `valor_canasta_apareado`: chica en general; donde se separan es por
  cambios de las sucursales que informan (jul-2023, 01/08/2026, Libertad desde el 03/09/2026).
- Avisos de eslabones de más de ±15% en un día (`ALERTA_ESLABON`) y de cambios de unidad ("parece en otras unidades que
  el mes anterior": se divide por 100, o se multiplica, desde ese mes). No debería haber ninguno de unidades.

---

## 3. La canasta

**Reglas** (`canasta_pass_through.py`, se aplican en este orden sobre las salidas del nb09 al 22/10/2026; entre
paréntesis, los productos que quedan):

1. Precio **todos los días** del 01/01/2022 al 20/10/2026 (4.545).
2. EAN del maestro, sin blacklist ni precio simbólico (4.521).
3. Consumo masivo: rubros Almacén, Bebidas, Frescos, Congelados, Limpieza, Perfumería, Mascotas, Bebés y mamás (4.420).
4. **≥ 150 sucursales por día, en promedio, en cada uno de los meses** (1.779).
5. Cobertura estable: ningún mes por debajo del 35% de su mes mediano, y la de 2022 entre un tercio y el triple de la de
   2026 (1.320).
6. En ≥ 6 de las 8 cadenas grandes (Carrefour, ChangoMas, Coto, Cencosud, La Anónima, Cooperativa Obrera, DIA, Toledo)
   y ninguna con más del 60% de sus sucursal-días (1.096).
7. En las 24 provincias y, en promedio, en ≥ 85% de las provincias con sucursales activas cada día (1.012).
8. Coeficiente de variación del precio entre sucursales (oct-26) ≤ 25%: descarta unidades o presentaciones mezcladas
   (1.004).
9. Una sola variedad por marca + subcategoría + presentación cuando el precio difiere menos de 3% (775).

La cobertura se mide por **promedio mensual** y no por el peor día porque del 16 al 28/07/2023 el SEPA trae la mitad de
los comercios (870 sucursales el 20/07/2023): con "≥ 100 sucursales todos los días" quedaban afuera casi todos los
básicos. Esos días se tratan en la serie (`cobertura_incompleta`), no en la selección.

**Básicos que no entran** (hoja `Basicos_excluidos` del Excel de la selección): fideos y arroz de Molinos (Lucchetti,
Matarazzo, Gallo, Ala), azúcar Ledesma, harinas Morixe y Pureza 0000. Tienen precio todos los días, pero su cobertura se
desploma entre dic-2023 y abr-2024 (de ~1.500 a 10-200 sucursales), justo en la devaluación. Entran aceites de girasol
(Cañuelas, Cocinero, Natura), harinas Caserita y Chacabuco, leches La Serenísima, arroz Dos Hermanos y 30 yerbas.

**Composición** (columna `tipo`): Alimentos 287, Bebidas sin alcohol 138, Limpieza del hogar 127, Bebidas alcohólicas
110, Cuidado personal y botiquín 81, Mascotas 32. Perecederos 70. `origen_gs1` (país del prefijo del código): Argentina
704, Brasil 19, Suiza 15, México 8...

| Grupo del IPC | Productos | `peso_ipc_%` |
|---|---:|---:|
| 01.1.1 Pan y cereales | 59 | 15,05 |
| 01.1.2 Carnes y derivados | 33 | 28,26 |
| 01.1.4 Leche, productos lácteos, huevos y alimentos vegetales | 28 | 11,43 |
| 01.1.5 Aceites, grasas y manteca | 7 | 2,07 |
| 01.1.7 Verduras, tubérculos y legumbres | 5 | 8,44 |
| 01.1.8 Azúcar, dulces, chocolate, golosinas, etc. | 86 | 3,49 |
| 01.1.9 Otros alimentos | 69 | 1,07 |
| 01.2.1 Café, té, yerba y cacao | 73 | 2,33 |
| 01.2.2 Aguas minerales, bebidas gaseosas y jugos | 65 | 7,57 |
| 02.1.1 Bebidas espirituosas, destiladas y licores | 31 | 0,19 |
| 02.1.2 Vinos | 64 | 3,78 |
| 02.1.3 Cerveza | 15 | 1,01 |
| 05.6.1 Bienes para el hogar no durables | 127 | 6,00 |
| 06.1.2 Otros productos medicinales | 3 | 0,54 |
| 09.3.4 Mascotas y productos conexos | 32 | 1,75 |
| 12.1.3 Artículos y productos para la atención personal | 78 | 7,02 |

**Pesos y cantidades**:
- `peso_ipc_%` = ponderación nacional del grupo en el IPC (ponderadores regionales del INDEC por el peso de cada región:
  GBA 0,447, Pampeana 0,342, Noreste 0,045, Noroeste 0,069, Cuyo 0,052, Patagonia 0,046), repartida entre los 16 grupos
  presentes y en partes iguales dentro de cada grupo. Alternativa: `peso_igual_grupo_%` (6,25% cada grupo).
- Ojo con "Carnes y derivados": se lleva el 28% y acá son fiambres, hamburguesas y patés (en el IPC es sobre todo carne
  fresca, que no tiene EAN). Lo mismo, en menor medida, "Verduras" (5 productos, 8,4%).
- `cantidad_08` (CSV) y `cantidad_01` (Excel del nb08, con `CANTIDAD = 'ipc'` en el script de Colab) = `peso_ipc_%` ×
  $1.000.000 / precio mediano de oct-2026. **Tienen decimales porque son las cantidades de una canasta que vale
  $1.000.000 a precios de oct-2026**, no unidades compradas. Con cantidades fijas, el índice es tipo Lowe: los pesos
  efectivos de cada día son q × p del día (en 2022 pesa menos lo que más subió desde entonces). Para comparar grupos,
  usar `Indices_por_grupo` o el panel.

**Rehacer la selección** (por ejemplo, con otra fecha final o reglas distintas): correr el nb09 en Colab y bajar sus
salidas de `MyDrive/carga/output_trazabilidad/`; después, en la PC (necesita `python-calamine`):

```bash
python -I -X utf8 docs/canastas_alternativas/canasta_pass_through.py <trazabilidad_productos_AAAAMMDD_AAAAMMDD.parquet> <panel_mensual_productos_AAAAMMDD_AAAAMMDD.parquet> <trazabilidad_productos_AAAAMMDD_AAAAMMDD.xlsx> <salida.xlsx>
```

Las fechas del período (`DESDE`, `HASTA`) y los umbrales están al principio del script. La salida trae las hojas
Selección (con `cantidad_08`), Grupos_IPC, Resumen, Criterios, Basicos_excluidos, Dias_incompletos, Candidatos y Notas.
Para que el script de Colab la tome de GitHub, guardar también el CSV en `docs/canastas_alternativas/` y actualizar
`URL_CANASTA` si cambia el nombre.

**Armar el Excel que lee el nb08**: `docs/canastas_alternativas/marcar_canasta_pass_through_colab.py` (pegar en una
celda de Colab). Pide subir el `canasta_representativa_AAAA-MM.xlsx` del mes, baja la canasta del CSV de GitHub y
devuelve `canasta_pass_through_AAAA-MM.xlsx` con la canasta en `cantidad_01` de la hoja Selección (copia en el Drive si
`GUARDAR_EN_DRIVE`). Opciones: `CANTIDAD` = `'ipc'` (por defecto) / `'igual'` / `'uno'`; `TIPOS` para marcar solo
algunos tipos. Agrega los productos que faltan en Selección desde "Productos unicos", guarda el `cantidad_01` anterior en
`cantidad_01_original` y no toca nada más. La salida no se llama `canasta_representativa_*` a propósito (el nb02 y el
nb07 la tomarían como la del mes). Si se cambia el nombre del Excel, cambiar `CANASTA_EXCEL` en el nb08.

---

## 4. La variable de precio (nb08 v2)

Para cada producto y día el nb08 calcula dos precios:

- **Mediana nacional** de todas las observaciones (sucursales) del día (el universo de la serie oficial del nb02).
  Se mueve cuando cambian las sucursales que informan, aunque ningún precio cambie.
- **Índice con sucursales apareadas** (la variable recomendada): eslabón del producto = media geométrica de los
  relativos *precio de hoy / precio anterior de la misma sucursal*. Si la sucursal faltó unos días (≤
  `MAX_DIAS_SIN_PRECIO`), su precio anterior se mueve con el índice del producto desde entonces (imputación del IPC para
  precios faltantes), así no vuelve a contar la variación que ya entró por las otras sucursales. Relativos fuera de
  [1/4, 4] no cuentan (errores de carga); un producto sin pares ese día no se mueve. Se encadena desde el primer día con
  dato y se lleva a pesos con la mediana del último día con dato (`precio_apareado`).

La canasta: `valor_canasta` (medianas) y `valor_canasta_apareado` = índices encadenados día a día con productos
apareados (Σ q·p_t / Σ q·p_{t−1} sobre los productos con dato los dos días), llevados a pesos en el día ancla (el último
con todos los productos). `valor_directo` = Σ q × mediana, solo con los productos con dato. Un archivo por quincena (el
`COMPLETOb` de ago-2024; antes el 1-5/08/2024 contaba doble).

**Panel** (`panel_diario_pass_through_<...>.parquet`): `fecha`, producto (`ean_norm`, descripción y la composición:
grupo, tipo...), `precio_mediano`, `precio_promedio` (media recortada), `n_obs`, `n_pares`, `relativo_apareado`,
`indice_apareado`, `precio_apareado`, `cobertura_incompleta`. Para las regresiones: Δlog de `indice_apareado` por
producto, o de `valor_canasta_apareado` y los índices de `Indices_por_grupo`.

**Validación** (2026-10-22): test `notebooks/test_canasta_diaria.py` (SEPA sintético contra fuerza bruta: medianas,
relativos con imputación, índice = tendencia verdadera aunque la mediana salte en un hueco, archivo y filas repetidas,
mes en centavos, caché con meses y estados borrados). Con datos reales (jul-sep 2024, los 775 productos,
`docs/auditoria/scripts_nb08_2026-10/validar_real.py`): medianas y promedios **idénticos** al lector anterior en 71.300
producto-días; observaciones distintas solo del 1 al 5/08/2024 (el doble conteo corregido); ~1 min y 0,4-0,5 GB por mes
en la PC (el lector anterior, ~5 GB); estado 3,2-3,6 MB por mes. En el trimestre: apareado +8,97% contra medianas
+9,07%, con un tercio del ruido diario (desvío 0,09 contra 0,25 pp) y ningún día con más de 1% (medianas: 2).

---

## 5. Advertencias

- **Precios de lista** publicados por las cadenas: sin promociones ni descuentos bancarios (`docs/METODOLOGIA.md` §6).
- **Sin frescos a granel** (carne, frutas y verduras por peso no tienen EAN): los grupos de alimentos están
  representados por envasados (ver "Carnes y derivados" arriba).
- **16-28/07/2023**: el SEPA trae la mitad de los comercios. Marcado en `cobertura_incompleta`.
- **Desde el 01/08/2026 la fuente es el SEPA diario** (script 03), que no trae los comercios 19, 1000, 2000, 2002, 2005,
  2007, 2013 y 3001; **Libertad** publica hasta el 02/09/2026. El índice apareado no salta por eso; la mediana puede.
  Cuando salga el semestral oficial de 2026B: reemplazar `MyDrive/carga/2026B.zip` y **borrar del caché del nb08**
  `2026-08.parquet`, `estado_2026-08.parquet` y los de los meses siguientes (el caché no mira si cambió el zip), y
  volver a correr. Lo mismo en el nb09 (`output_trazabilidad/_cache_nb09/v1/2026-08_p*` y siguientes) si se rehace
  la selección.
- **Cobertura de algunas marcas líderes** (Molinos, Ledesma, Morixe) colapsa dic-2023/abr-2024: por eso no están.
- `origen_gs1` es un indicio débil de importado: el prefijo dice dónde registró el código el dueño de la marca, no
  dónde se fabricó.
- **Pesos/centavos**: el nb08 decide por mes con la regla del nb02 (mediana > $10.000 → ÷100) y, si el eslabón de
  medianas del primer día de un mes da > 30 o < 1/30, corrige el mes (o los meses) que vienen en otras unidades. Todos los semestrales de 2022-2026 del Drive están en pesos (el nb09
  dio factor 1 en los 1.747 días). La regla vence hacia 2029: en jul-26 la mediana de las observaciones de las canastas
  del nb02 era $3.420 y la de todos los productos, $4.529 (`docs/AUDITORIA_2026-10-22_nb09.md` §4.4).
- El SEPA publica **todos los días del calendario**; el tipo de cambio, solo los hábiles: hay que alinear calendarios
  (último dato hábil para fines de semana y feriados, o pasar a frecuencia semanal).

---

## 6. Próximos pasos

1. **Correr el nb08 en Colab** y revisar la salida (§2).
2. **Tipo de cambio diario**: oficial mayorista (BCRA, Comunicación A 3500) y financieros (MEP / CCL; fuente a definir),
   y la brecha. Episodios para la identificación (verificar fechas y niveles con la serie): devaluación del 14/08/2023
   (después de las PASO), del 13/12/2023 y la salida del cepo con banda de flotación desde el 14/04/2025.
3. **Regresiones**: Δlog del índice apareado (por producto y por grupo) contra rezagos de Δlog del tipo de cambio
   (rezagos distribuidos o proyecciones locales), pass-through acumulado a 1, 7, 30, 60 y 90 días, heterogeneidad por
   grupo del IPC, tipo, perecedero y origen; días con `cobertura_incompleta` como dummy o fuera.
4. Decidir los pesos (IPC vs iguales por grupo) y probar sensibilidad.
5. Cuando salga el semestral oficial 2026B, reemplazar ago-oct 2026 (§5).
