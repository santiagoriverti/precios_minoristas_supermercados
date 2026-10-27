# Guía para investigadores: la brecha celíaca con los precios del SEPA

Esta guía es para quien va a estimar la brecha celíaca (la prima de precio de los productos sin TACC sobre sus
equivalentes con TACC) con las salidas de los notebooks `06_evolucion_brecha_celiaca` y
`06b_brecha_celiaca_canasta_amplia`. Dice qué datos hay, cómo se calcula cada número, qué decisiones de diseño hay
detrás, qué tener en cuenta para la inferencia y cómo reproducir todo. La documentación técnica completa está en
[`docs/BRECHA_CELIACA.md`](../BRECHA_CELIACA.md) (§14 la canasta fija, §15 los análisis complementarios, §16 la canasta
amplia, §17 la segunda revisión de expertos) y las evaluaciones en
[`docs/EVALUACION_EXPERTOS_2026-10-27_nb06.md`](../EVALUACION_EXPERTOS_2026-10-27_nb06.md).

## 1. Qué se mide y qué no

**La pregunta**: cuánto más paga un celíaco que un no celíaco por comprar productos sin TACC equivalentes a los productos
con TACC, y cómo se distribuye en el tiempo, en el territorio, entre cadenas y según la concentración de los puntos de
venta.

**La medida**: la brecha de un subtipo en una sucursal y un mes = precio por 100 g de los productos sin TACC / precio por
100 g de los con TACC − 1, **dentro del mismo supermercado y mes** y entre productos **del mismo subtipo** (spaghetti con
spaghetti, crackers con crackers, galletitas rellenas con rellenas). Comparar dentro de la sucursal controla el nivel de
precios del lugar (alquiler, logística, impuestos locales) y la política de precios de la cadena.

**Dos canastas, dos preguntas**:

| | Canasta fija 2022-2026 (nb06) | Canasta amplia de la oferta actual (nb06b) |
|---|---|---|
| Para qué | **Evolución** de la brecha desde enero de 2022 | **Nivel** de la brecha y costo de la dieta, hoy |
| Período | ene-2022 → hoy (58 meses en oct-2026) | ago-2025 → hoy (15 meses) |
| Tipos | 5: fideos secos, galletitas dulces, galletitas saladas y crackers, rebozador, cereales rellenos | 10: los 5 más pan envasado, harinas, premezclas, alfajores y tapas |
| Productos | 62 productos en 43 líneas (75 códigos), con precio todos los meses | 142 códigos en 109 líneas |
| Peso en el gasto con gluten (ENGHo) | 41% | 62% |

**Lo que no mide**: precios de transacción (son precios de góndola publicados), cantidades compradas, dietéticas y
almacenes (el SEPA es de las cadenas obligadas a informar: supermercados grandes), el pan francés fresco (no está en el
SEPA), la calidad nutricional ni el costo de buscar el producto. El costo con la Canasta Básica Alimentaria del INDEC
(hoja `Costo_CBA`) es una **cota inferior** del costo de la dieta: solo los ítems con gluten que la canasta cubre.

## 2. Cómo obtener los datos

1. Abrir el notebook desde el README del repositorio con el botón *Abrir en Colab*
   (`notebooks/06_evolucion_brecha_celiaca.ipynb`; el amplio, `notebooks/06b_brecha_celiaca_canasta_amplia.ipynb`).
2. Tener en el Drive, en `MyDrive/carga/`, los zips semestrales del SEPA (`2022A.zip` → `2026B.zip`), `ar.json`,
   `IPC.xlsx` del INDEC (opcional) y la caché de Georef del nb09 (opcional).
3. Ejecutar todas las celdas. La primera corrida lee los 58 meses (~1 h en el Colab gratuito); con la caché, ~15 min.
4. Las salidas quedan en `MyDrive/carga/output_brecha/` (el 06b, en `output_brecha_amplia/`): el Excel
   `brecha_celiaca_AAAA-MM.xlsx` (hojas `Leeme` y `Resumen` primero), los gráficos, los mapas y la carpeta **`datos/`**.

## 3. Los datos para estimar (`datos/`)

Todos los archivos se unen por `suc_key` (`id_comercio|id_bandera|id_sucursal`). Cada columna está descripta en
`datos/diccionario_datos.csv`; `datos/LEEME.md` repite lo esencial con los números de la corrida.

| Archivo | Unidad | Para qué |
|---|---|---|
| `panel_sucursal_mes_subtipo` (.parquet, .csv.gz) | celda = sucursal × mes × subtipo con los dos lados (542 mil en oct-2026) | la brecha de cada celda (`brecha_pct`), el precio de cada lado, la región, la empresa, la cadena, el departamento, la concentración, las coordenadas, si la celda es del panel balanceado (`en_panel_balanceado`) y el peso ENGHo del tipo |
| `panel_producto_sucursal_mes` | código × sucursal × mes (3,2 millones) | el precio de cada producto de la canasta (por unidad y por 100 g), con su producto, marca y gramos: estimaciones hedónicas o con efectos fijos de producto |
| `panel_producto_sucursal_mes_adicionales` | código × sucursal × mes | lo mismo para los ADICIONALES (cumplen las reglas de la selección pero quedan fuera de la canasta; columna `motivo`) |
| `productos.csv` | código | tipo, subtipo, lado, producto, línea, marca, marca de comparación, gramos, vigencia, sustituto y uso de cada código |
| `sucursales.csv` | sucursal | empresa, cadena, región, provincia, departamento, competencia local (sucursales y empresas a ≤ 3 km, HHI local y del departamento), brecha comparable y coordenadas |

## 4. Cómo se calcula la brecha (y cómo reproducirla)

1. Precio de un código en el mes = **mediana de sus precios diarios**; $/100 g con los gramos verificados.
2. Precio de un producto en la sucursal y mes = mediana de sus códigos (un producto que cambió de EAN y los sabores de
   una línea al mismo precio cuentan una vez).
3. Precio de cada lado de un subtipo = **mediana de sus productos presentes**; la celda existe si están los dos lados.
   `brecha_pct = sin / tacc − 1`.
4. Brecha de un subtipo en un período = mediana de `brecha_pct` entre sus celdas.
5. Brecha de un tipo = promedio geométrico de las de sus subtipos (pesos iguales).
6. Brecha de la canasta = Σ_k w_k (1 + brecha del tipo k) / Σ_k w_k − 1, con w = `peso_tipo_canasta` (gasto de los
   hogares, ENGHo 2017/18).

Con las celdas de los últimos 12 meses y esos pasos se reproduce la brecha nacional del Excel (hoja `IC_grupos`, País).
La serie mensual imputa el subtipo-mes con muy pocas sucursales con su último mes válido (hoja `Imputaciones`); los
grupos (región, provincia, empresa, cadena) usan la **misma canasta de subtipos** y completan lo que no tienen con la
brecha nacional del período (`peso_imputado_pct` dice cuánto). **Serie TPD** (hoja `Serie_TPD`): por subtipo,
ln p(producto j, sucursal s, mes t) = a(s, t) + g(j) + b(t) × sinTACC(j) + e por mínimos cuadrados ponderados; compara
siempre los mismos productos.

## 5. Inferencia: la unidad de decisión es la cadena

Las cadenas fijan el precio de cada producto para todas sus sucursales: en 8 de los 12 subtipos la empresa explica más
de la mitad de la variación entre sucursales de la brecha (R² de 0,24 en obleas a 0,98 en rellenas; 0,95 en con chips,
0,88 en spaghetti) y el desvío dentro de cada empresa es chico, de 0,02 a 0,08 en logaritmos (hoja `Varianza_empresa`).
Las sucursales de una cadena **no son observaciones independientes**. El Excel trae los dos tipos de intervalo:

| Brecha (oct-2026) | Estimación | IC 95% por sucursal | IC 95% por empresa |
|---|---|---|---|
| Canasta, últimos 12 meses (todas las sucursales) | +103,1% | +102,6% a +103,5% | +93,7% a +106,3% (bootstrap de las 12 empresas) |
| Canasta, oct-2026, panel balanceado (TPD) | +102,6% | +102,1% a +103,1% | +99,2% a +106,1% (errores agrupados por empresa) |

En promedio, el IC de la serie TPD del panel mide 1,6 pp con errores agrupados por sucursal y 15,8 pp agrupados por
empresa. **Recomendación**: para generalizar a otras cadenas posibles, inferencia por empresa. Con 12 empresas, el error
agrupado (CR1) y los percentiles del bootstrap de grupos se quedan cortos: conviene el *wild cluster bootstrap*
(Cameron, Gelbach y Miller, 2008) o las correcciones de pocos grupos (MacKinnon y Webb). Con los intervalos por
sucursal, cuatro de las seis regiones difieren del país (Patagonia, −13,7 pp; AMBA, Noroeste y Cuyo, +2,6 a +3,5 pp); con
los intervalos por empresa, **ninguna** (hoja `IC_grupos`, columnas `*_empresa`; en la canasta amplia, solo Cuyo). Para
series de tiempo, considerar también la correlación entre meses (agrupar por empresa, o en dos dimensiones, empresa y
mes).

## 6. Composición: qué sucursales y qué cadenas entran cada año

El universo de todas las sucursales cambia mucho: DIA pasó del 41% de las celdas en 2022 al 5% en 2025-2026 y Carrefour
del 21% al 43% (hoja `Composicion_empresas`; gráfico `composicion_empresas_*.png`). Una serie con todas las sucursales
mezcla el cambio de la brecha con el de la composición. El **panel balanceado** (sucursal × subtipo con los dos lados en
≥ 70% de los meses; `en_panel_balanceado`) es la serie clave: su composición se mantiene (Carrefour 40-44% todos los
años). Para estimar: el panel, o efectos fijos de sucursal × subtipo.

**Selección por disponibilidad**: la brecha se mide solo donde están los dos lados. De las sucursal-meses que venden un
tipo con TACC, el 68% vende también el sin TACC (90% alguna vez en el año; hoja `Disponibilidad`). No encontrar el
producto también es un costo y la brecha observada puede ser la de los lugares que sí lo tienen.

## 7. Surtido: cada cadena vende productos distintos, y cambian en el tiempo

La hoja `Surtido_empresa` dice, por empresa, año y producto de la canasta, en qué parte de las celdas de la empresa está
el producto. La hoja `Hedonica_grupos` compara región y empresa **con los mismos productos** (efectos fijos de producto)
y **con el surtido de cada grupo** (sin ellos, con una prima base por subtipo): la diferencia es la parte del surtido
(`efecto_surtido_pct`). En los últimos 12 meses, por ejemplo, ChangoMas no difiere de Carrefour con los mismos
productos (+0,6%, IC −0,2% a +1,4%) pero su brecha es +13% más alta con su surtido; "Otras" empresas, +9,6% con los
mismos productos y −1,6% con el suyo. `Hedonica_grupos_anual` repite los dos modelos por año.

## 8. Prima de marca: ¿la brecha es la prima sin gluten o la marca?

La regla de selección prefiere la versión sin TACC **de la misma marca** del lado con TACC. En la canasta fija, spaghetti
y penne (Matarazzo) y almohaditas (Lasfor y su línea sin TACC, Snuks) son comparaciones de una sola marca: ahí la brecha
de la canasta **es** la prima sin gluten pura (+128%, +130% y +27% en los últimos 12 meses). En tirabuzón, Matarazzo da
+134% contra +179% de la canasta: el resto lo agrega comparar marcas distintas (prima de marca +19%). En la canasta
fija no hay pares de la misma marca en galletitas, crackers, snacks y rebozador: los sin TACC con precio desde 2022 son
de marcas especializadas (Smams, Santa María, Aglu, Crisppino, Grandiet, Naturalsur) y el comparador es la marca líder
con TACC; la brecha incluye esa diferencia de marca, que es lo que enfrenta el consumidor celíaco. Hoja
`Prima_misma_marca` (por período y año) y gráfico `prima_misma_marca_*.png`. La canasta amplia (nb06b), con la oferta
actual, tiene 12 pares: suma rellenas (Oreo, +63% contra +111% de la canasta), rebozador (Preferido, +224%), pan
rallado (Mamá Cocina), alfajor individual (Terrabusi), premezclas (Exquisita y Mamá Cocina) y tapas (La Salteña); la
prima de marca va de −13% a +33%, sin un signo único.

## 9. Calidad de los datos

Filtros que sacan observaciones (todos reproducibles y con su hoja): plausibilidad por código (banda ×4 contra sus
pares; hoja `Plausibilidad`), precios de una empresa fuera de escala (×2,5 contra las demás empresas del mismo código y
mes; `Precios_atipicos`, 37 casos), **precios congelados** (una empresa repite el mismo precio 6 meses o más mientras el
índice de su tipo y lado sube más de 50%; `Precios_congelados`: Deheza informó las galletas de arroz Crisppino a $290
los 100 g de abr-2023 a jul-2024 mientras en Carrefour pasaban de $350 (jun-2023) a $1.700 (jul-2024), y su brecha de
snacks llegaba a −80%),
vigencia de los códigos que cambiaron de EAN (los viejos siguen con el precio congelado) y tiendas online fuera del
universo. Diagnóstico que no saca: control de identidad de cada código (`Control_EAN`).

## 10. Especificaciones sugeridas

- **Nivel y evolución**: la TPD por subtipo, ln p_jst = a_st + g_j + b_t · SinTACC_j + e, con a_st (celda) y g_j
  (producto) como efectos fijos y errores agrupados por empresa; tipo y canasta como combinaciones de los b_t (la hoja
  `Serie_TPD` lo hace).
- **Geografía y cadenas**: ln p = a_celda + g_j + SinTACC_j × (región + empresa) + e; con y sin g_j para separar el
  surtido.
- **Concentración**: SinTACC_j × HHI (del departamento, o local a ≤ 3 km) con efectos de empresa y región. En la canasta
  fija, con empresa y región, los efectos son chicos (menos de 0,1% sobre 1 + brecha por +0,1 de HHI o por una empresa
  rival más) y no significativos; en la amplia, más concentración se asocia con una prima algo **menor** (−0,26% por
  +0,1 de HHI del departamento o local, significativo también con errores por empresa). Sin controles aparecen efectos
  que son de la cadena (hoja `Concentracion_modelos`). El HHI no es exógeno: las cadenas eligen dónde abrir.
- **Shocks**: la brecha saltó en sep-dic 2023 (devaluaciones de agosto y diciembre) y bajó en 2025 (hoja
  `Indices_lados`: los precios sin TACC subieron menos que los con TACC en 2024-2025 y más en 2026): estudios de evento
  sobre b_t.
- **Pesos**: los tipos pesan como en el gasto de todos los hogares (ENGHo 2017/18), no como en el de un hogar celíaco.

## 11. Robustez que ya trae el Excel

`Sensibilidad` (la brecha nacional cambiando una decisión por vez: +100% a +134%, el más alejado es "solo productos
equivalentes"; con las sucursales ponderadas por la población de su provincia, +104%), `Serie_TPD` contra la serie
descriptiva, `Indices_lados` (cada lado contra el IPC de alimentos del INDEC), `IC_grupos` (dos bootstraps),
`Hedonica_grupos` (mismos productos y surtido; errores por departamento y por empresa) y `Concentracion_modelos` (sin
controles, con empresa, con empresa y región; errores por departamento y por empresa).

## 12. Reproducibilidad

- El código está en el repositorio (`notebooks/gen_nb06.py` genera los dos notebooks). Test con fuerza bruta:
  `python notebooks/test_brecha_celiaca.py` (cada número contra un cálculo directo, sobre un SEPA sintético).
- Resultados esperados de la corrida de referencia: `docs/brecha_celiaca/simulacion_2026-10-27b/` (nb06) y
  `simulacion_06b_2026-10-27b/` (nb06b), un CSV por hoja. Para comparar el Excel de una corrida:
  `python -I -X utf8 docs/auditoria/scripts_nb06_2026-10/s16_comparar_colab.py <Excel> docs/brecha_celiaca/simulacion_2026-10-27b`.
- La lista de productos con sus métricas: `canasta_fija_2022_2026.csv` y `canasta_amplia_2025_2026.csv`; los que quedan
  afuera: `productos_sensibilidad*.csv`. Las reglas de la selección: `docs/BRECHA_CELIACA.md` §14 y §16.

## 13. Fuentes

- SEPA: Sistema Electrónico de Publicidad de Precios Argentinos, Secretaría de Comercio de la Nación (precios diarios
  por sucursal de las cadenas obligadas a informar).
- ENGHo 2017/18 (INDEC): ponderaciones de los tipos.
- Canasta Básica Alimentaria (INDEC): gramos por adulto equivalente.
- IPC (INDEC): alimentos y bebidas no alcohólicas, nivel general.
- Georef (datos.gob.ar): departamento de cada sucursal.
