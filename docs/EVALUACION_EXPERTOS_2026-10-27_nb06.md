# Evaluación del panel de expertos: ¿la canasta mide bien la brecha celíaca? (nb06, 2026-10-27)

El usuario pidió examinar los resultados del nb06 y todo lo que hay en la carpeta `carga` del Drive, y evaluar, como un
equipo de expertos en estadística y economía, si los productos y canastas elegidos sirven para estimar la brecha
celíaca y su distribución en el tiempo, en el territorio, por cadena y por concentración de puntos de venta. Después,
aplicar los cambios para que el notebook se pueda correr desde GitHub y deje el Excel y los datos para el análisis
propio.

Este documento tiene el veredicto, la evidencia y los cambios hechos. Los números salen de la simulación con las celdas
reales del notebook vigente sobre los zips del Drive (ene-2022 → oct-2026; `sim_v9`). El cálculo independiente (`s12`)
da lo mismo en los 3.244.531 precios sucursal × producto × mes y en todas las brechas. Esperados en
`docs/brecha_celiaca/simulacion_2026-10-27/`. **La corrida de Colab del 2026-10-27 dio igual a la simulación** (§13).

## 1. Veredicto

| Dimensión | Veredicto | Evidencia principal |
|---|---|---|
| **Qué productos** | **Adecuados para lo que miden**: envasados de primera marca con versión sin TACC equivalente, comparados dentro del mismo súper. Todos los sin TACC están verificados (listado ALG de ANMAT o marca solo sin gluten) | Sensibilidad: +100% a +109% con siete decisiones distintas; solo "sin sustitutos" se va a +134% (§3) |
| **Cobertura de la dieta** | **Insuficiente para el costo de la dieta**: la canasta pesa el 5,0% del gasto en alimentos, el 41% de los artículos con gluten de la ENGHo. Falta el pan, que es lo que más pesa. **Resuelto con la canasta amplia (nb06b): 62%** | Pan francés 4,7% (no está en el SEPA), pan envasado 0,8%, harinas y premezclas 0,7%, alfajores 0,5%, tapas 0,5% (§3.3, §10.2) |
| **Tiempo** | **Adecuado**: continuidad desde ene-2022, panel balanceado, serie TPD como robustez e índices de cada lado | TPD y descriptiva a 2,3 pp en los meses sin imputar; sin / con = 99,1 en oct-2026 con base ene-2022 (§4) |
| **Geografía** | **Adecuada por región**; por provincia, 8 de 17 confiables | Patagonia +89% (IC +88% a +92%) contra +102% a +107% en las demás. Con los mismos productos, Patagonia da solo −2,9% (§5) |
| **Cadenas** | **Limitada con la canasta propia** (solo Carrefour y Cencosud tienen ≤ 25% del peso imputado). **Resuelta con la hedónica**: mismos productos, 6 empresas confiables | Diferencias de −3,6% a +0,7% entre las grandes; DIA, Toledo y Cooperativa Obrera con poco dato (§6) |
| **Concentración** | **Sin efecto** una vez controladas la empresa y la región, con tres medidas | HHI del departamento p = 0,60; HHI local (3 km) p = 0,26; empresas rivales a ≤ 3 km p = 0,81 (§7) |
| **Disponibilidad** | **Hallazgo nuevo**: el sin TACC está en el 68% de las sucursal-meses que venden el tipo con TACC; depende de la cadena | Carrefour 99%, Cencosud 98%, La Anónima 94%, DIA 42% (§8) |
| **Calidad de datos** | **Buena y reproducible**, con reglas simétricas | 37 empresa-código-mes fuera de escala descartados; 0 EANs fuera por plausibilidad; 8 para revisar (§9) |
| **Reproducibilidad** | **Completa**: Colab desde GitHub, caché por mes, semilla fija, 15 tests y esperados por hoja | §11 |

**En una frase**: la canasta fija mide bien la **prima de precio** de los sin TACC envasados (un celíaco paga el
doble: +103% en los últimos 12 meses, IC 95% +102,6% a +103,5%) y cómo cambia en el tiempo, por región y por cadena. No
mide el **costo de la dieta**, porque no tiene pan ni harinas. Para eso, el panel recomendó una segunda canasta de la
oferta actual, que quedó hecha (nb06b, §10.2): con pan, harinas, premezclas, alfajores y tapas, la brecha es +143% y el
costo extra con la Canasta Básica Alimentaria, +$156.474 por adulto equivalente por mes.

## 2. Qué se examinó

- **Resultados**: la simulación completa del notebook vigente, 51 hojas del Excel, 16 gráficos, el mapa por sucursal y
  los paneles de `datos/`.
- **Carpeta `carga`**: los 10 zips semestrales del SEPA (2022A → 2026B), `IPC.xlsx` del INDEC (nivel general y 12
  divisiones, ene-2017 → sep-2026), `ar.json` y las salidas de los otros notebooks. Entre ellas: canastas, maestros y
  `Otros/canastas_celiaca_vegana.txt`, el diseño de canastas de dietas especiales del proyecto.
- **Referencias externas**: los gramos por adulto equivalente de la Canasta Básica Alimentaria del INDEC y la ENGHo
  2017/18 (gasto por artículo).
- **Código**: el generador, el test y los scripts de selección (`s7` → `s10`).

## 3. Nivel de la brecha: ¿son los productos adecuados?

### 3.1 La prima es robusta a las decisiones de diseño

Hoja `Sensibilidad`: brecha nacional de los últimos 12 meses, con la misma canasta de subtipos que los grupos,
cambiando **una** decisión por vez.

| Escenario | Brecha | Diferencia |
|---|---|---|
| Principal | +103,1% | — |
| Galletas de arroz también en crackers | +100,1% | −2,9 pp |
| Todos los productos que cumplen las reglas (sin composición espejada) | +106,1% | +3,0 pp |
| Lo más barato de cada lado en la sucursal | +106,1% | +3,0 pp |
| Pesos de los subtipos por disponibilidad | +107,4% | +4,3 pp |
| Cociente de las medianas nacionales (sin comparar dentro del súper) | +108,4% | +5,4 pp |
| Cada sabor como un producto | +109,4% | +6,4 pp |
| Solo productos equivalentes (sin las galletas de arroz de saborizadas) | +134,2% | +31,2 pp |

Lectura:

1. **Siete de las ocho variantes quedan entre +100% y +109%.** La conclusión ("un celíaco paga el doble") no depende de
   cómo se elijan las marcas, se cuenten los sabores o se pesen los subtipos.
2. **La única que mueve mucho es la de las galletas de arroz de saborizadas.** Ese subtipo no tiene galletitas
   saborizadas sin TACC con continuidad 2022-2026: el lado sin TACC son galletas de arroz saborizadas (Crisppino,
   Grandiet), un **sustituto**, no la versión sin TACC del mismo producto. Sin ellas, saladas queda solo con crackers
   (+195%) y la canasta sube 31 pp.
   - **Decisión del panel**: dejarlas. Es lo que un celíaco compra en su lugar, y la regla "equivalentes primero" ya
     las saca de crackers, donde sí hay crackers sin TACC (Smams). Pero hay que reportar el escenario.
3. **El estimador dentro del súper importa poco** (+5,4 pp contra el cociente de medianas nacionales), pero es el
   correcto: controla el nivel de precios de cada lugar.

### 3.2 La regla "equivalentes primero" (cambio de la canasta)

En crackers, las 4 galletas de arroz Grandiet eran 4 de los 7 sin TACC. Mezclaban "la versión sin TACC del mismo
producto" con "lo que puede comprar en su lugar", y además las compra cualquiera.

- **Ahora**, en un subtipo con un sin TACC equivalente (crackers Smams), los sustitutos (galletas, tostadas de arroz)
  quedan fuera. Pasan a `productos_sensibilidad.csv` y al escenario de la hoja `Sensibilidad`.
- La composición espejada saca un con TACC (Mini Crackers Paseo).
- El subtipo pasa a llamarse **Crackers**.
- Efecto, junto con el filtro de precios de una empresa fuera de escala (§9): crackers +167% → +195%, saladas +78% →
  +87% y canasta de los últimos 12 meses +99% → +104% (promedio de la serie mensual de todas las sucursales).

### 3.3 Lo que la canasta fija no puede medir: el costo de la dieta

| Artículo de la ENGHo con gluten | % del gasto en alimentos | En la canasta fija |
|---|---|---|
| Fideos secos, galletitas dulces y saladas, pan rallado, cereales | 5,00 | Sí |
| Pan francés (fresco, de panadería) | 4,72 | No: no está en el SEPA con código de barras |
| Pan envasado (de molde, de mesa, para hamburguesas y panchos) | 0,79 | No: el sin TACC (Bio, Campero, Schar) no tiene continuidad desde 2022 |
| Harina de trigo y premezclas | 0,73 | No: la premezcla sin TACC de Arcor tenía en 2022 ocho veces la cobertura de 2026 |
| Alfajores | 0,55 | No: Yuka y Happy Food tienen poca cobertura antes de 2025 |
| Tapas de empanadas y tartas | 0,52 | No: el sin TACC de La Salteña no tiene continuidad |
| **Total** | **12,31** | **41%** |

Por eso el costo con la CBA del INDEC (hoja `Costo_CBA`) es una **cota inferior**:

- **+$18.815 por adulto equivalente por mes** (+145%) en fideos, galletitas de agua y galletitas dulces;
- **+$58.138 por mes un hogar tipo** (3,09 adultos equivalentes);
- sin el pan (6.750 g por adulto equivalente por mes, el ítem más grande de la CBA) ni la harina (1.080 g).

## 4. Tiempo

- **Canasta por año** (todas las sucursales / panel balanceado): 2022 +106% / +97%; 2023 +102% / +92%; 2024 +105% /
  +88%; 2025 +87% / +81%; 2026 +105% / +99%.
- **Robustez**:
  - la TPD (hedónica, CELDA 8b) y la descriptiva difieren 2,3 pp (mediana) en los 39 meses sin subtipos imputados;
  - en oct-2026, el panel da +102,6% con las dos (TPD: IC +102,1% a +103,1%).
- **Índices de cada lado** (nuevos, hoja `Indices_lados`). Efectos fijos de producto × sucursal y de mes, contra el IPC
  del INDEC con la misma base (ene-2022 = 100):

  | 2026-10 | Índice |
  |---|---|
  | Con TACC | 2.192 |
  | Sin TACC | 2.174 |
  | IPC alimentos (sep-2026) | 2.093 |

  - Los dos lados subieron como los alimentos.
  - sin / con terminó en 99,1: la brecha de oct-2026 es casi la de ene-2022.
  - En el medio se achicó: sin / con 95,2 en 2024 y 91,5 en 2025, el mínimo de la serie de la canasta, y volvió en
    2026.
  - El índice sin / con y la TPD de todas las sucursales tienen correlación 0,92.
- **Cuidado**:
  - dic-2023 → mar-2024 tienen subtipos imputados (cambios de código de Molinos; hoja `Imputaciones`);
  - 2023-12 y 2024-08 → 2024-10 tienen cobertura baja (avisos de la CELDA 7).

**Veredicto**: adecuado. La evolución de largo plazo usa la serie del panel balanceado y la TPD; la anual, las dos
universos.

## 5. Geografía

Últimos 12 meses, misma canasta de subtipos en todos los grupos; IC 95% por bootstrap de sucursales (hoja
`IC_grupos`).

| Región | Brecha | IC 95% | ¿Difiere del país? |
|---|---|---|---|
| Patagonia | +89,4% | +88,2% a +92,3% | Sí, −13,7 pp |
| Pampeana | +102,4% | +101,0% a +104,0% | No |
| Noreste | +104,7% | +101,9% a +107,8% | No |
| Noroeste | +105,7% | +104,9% a +107,7% | Sí |
| AMBA | +105,7% | +105,2% a +106,1% | Sí |
| Cuyo | +106,6% | +105,4% a +107,4% | Sí |

- **Provincias**: 8 de 17 confiables; de Chubut (+90,1%) a Córdoba (+111,1%).
- **Patagonia, con los mismos productos** (hoja `Hedonica_grupos`), da −2,9% sobre 1 + brecha contra el AMBA. Con la
  canasta propia, −7,9% (1,894 / 2,057). **Casi dos tercios de su menor brecha es surtido** (qué productos tienen sus
  góndolas), no precio de los mismos productos.
- **Cuyo**, con los mismos productos, da −2,0%.

**Veredicto**: adecuado por región. Las provincias chicas no tienen sucursales suficientes con los dos lados en la
canasta fija.

## 6. Cadenas

Con la **canasta propia** de cada empresa (hoja `Brecha_empresa`), solo Carrefour (+104,4%) y Cencosud (+106,6%)
tienen ≤ 25% del peso imputado. Las demás venden pocos de los sin TACC de la canasta: DIA imputa el 76% y ChangoMas el
52%. Su brecha "propia" es casi la nacional.

La **hedónica de grupos** (nueva, hoja `Hedonica_grupos`) compara los **mismos productos**: ln p = efecto de la celda
(sucursal × mes × subtipo) + efecto del producto + sinTACC × (región + empresa), con errores agrupados por departamento.
Efecto sobre 1 + brecha contra Carrefour, controlando la región:

| Empresa | Efecto | IC 95% | ¿Confiable? |
|---|---|---|---|
| La Anónima | −3,6% | −4,6% a −2,7% | Sí (8 subtipos) |
| Cencosud | −0,9% | −1,4% a −0,5% | Sí (11) |
| ChangoMas | +0,6% | −0,2% a +1,4% | Sí (6) |
| Coto | +0,7% | +0,4% a +1,0% | Sí (7) |
| Otras (menos de 20 sucursales) | +9,6% | +6,7% a +12,5% | Sí (9) |
| Toledo | −1,9% | −2,8% a −1,0% | No (3) |
| Cooperativa Obrera | +0,6% | −0,8% a +2,0% | No (2) |
| DIA | −17,0% | −17,4% a −16,7% | No (3 subtipos en 3 meses) |

- **Entre las cadenas grandes, la prima difiere poco** con los mismos productos: de −3,6% a +0,7%.
- **DIA es poco dato**. Sus celdas con los dos lados son tres subtipos, en ≤ 3 meses (ago → oct 2026): spaghetti, con
  chips y rellenas. Una sola carga pesa mucho: sin las rellenas Smams de sep-2026, cargadas a la mitad del precio de las
  demás cadenas (¿precio de lanzamiento?), el efecto pasa a −11,7%. El filtro de §9 no las saca: están a ×1,9 de las
  demás empresas.
- **El notebook ahora marca `confiable`** (celdas en la mitad de los subtipos o más, cada uno en la mitad de los meses)
  y el gráfico pinta en gris los grupos con poco dato.

**Veredicto**: con la canasta fija, la comparación entre cadenas se lee con la hedónica, no con la canasta propia.
La canasta amplia (§10.2) agrega productos a la mayoría de las cadenas.

## 7. Concentración de puntos de venta

El SEPA no tiene ventas: la cuota de cada empresa es su número de sucursales. Tres medidas:

- HHI de empresas del **departamento** (Georef);
- HHI **local**: sucursales a ≤ 3 km de cada súper;
- **empresas rivales** a ≤ 3 km.

Regresión por sucursal de su brecha comparable (hoja `Concentracion_modelos`): 1.040 sucursales con al menos la mitad
del peso medido en ellas, en 175 departamentos, con errores agrupados por departamento.

| Medida | Sin controles | Con empresa | Con empresa y región |
|---|---|---|---|
| HHI del departamento (+0,1) | −0,34% (p = 0,02) | +0,04% (p = 0,55) | −0,03% (p = 0,60) |
| HHI local (+0,1) | −0,39% (p < 0,01) | +0,04% (p = 0,52) | +0,05% (p = 0,26) |
| Una empresa rival más a ≤ 3 km | +0,45% (p < 0,01) | +0,17% (p < 0,01) | −0,01% (p = 0,81) |

- La asociación sin controles es **composición de cadenas**: dónde están las sucursales de cada empresa. Desaparece al
  comparar dentro de cada empresa y región.
- En la hedónica, con los mismos productos, el HHI del departamento da −0,07% (p = 0,22) y las rivales −0,01%
  (p = 0,76).
- Los efectos son chicos aunque fueran reales: +0,1 de HHI mueve la brecha menos de medio punto.

**Veredicto**: no hay evidencia de que la concentración local de puntos de venta mueva la prima sin TACC. La prima la
fija la cadena (y el fabricante), no el mercado local.

## 8. Disponibilidad: no encontrar el producto también es un costo

La brecha solo se mide donde están los dos lados. Hoja `Disponibilidad`: de las sucursal-meses que venden el tipo con
TACC, % que vende también el sin TACC (pesos ENGHo), últimos 12 meses:

| | Disponibilidad |
|---|---|
| País (sucursal-meses) | 67,9% |
| País (sucursales que alguna vez lo tuvieron) | 90,1% |
| Carrefour / Cencosud / La Anónima | 98,9% / 97,9% / 93,8% |
| ChangoMas / Coto | 82,1% / 69,7% |
| DIA / Cooperativa Obrera / Toledo | 41,9% / 32,5% / 32,2% |
| Cuyo / Patagonia / Noroeste | 93,3% / 77,5% / 77,2% |
| AMBA / Pampeana / Noreste | 66,0% / 65,0% / 63,1% |

- La disponibilidad la fija la cadena: DIA, la de más sucursales, tiene el sin TACC en 4 de cada 10 sucursal-meses.
- El AMBA queda abajo porque ahí están la mayoría de las sucursales de DIA.

## 9. Calidad de los datos

- **Precios de una empresa fuera de escala** (nuevo, CELDA 7, hoja `Precios_atipicos`).
  - Para cada código y mes, la mediana de cada empresa contra la mediana entre empresas (≥ 3). Fuera de ×2,5 se
    descarta: 37 empresa-código-mes, 1.505 observaciones.
  - Caso que lo motivó: DIA, sep-2026, chips Smams a $860 contra ~$2.550. Con 981 sucursales, el precio de DIA **era**
    la mediana nacional, así que el filtro por EAN no lo veía.
  - La TPD y la hedónica (mínimos cuadrados) son sensibles a esos precios.
- **Distribución del factor**: el 0,56% de las empresa-código-mes queda fuera de ×2,5 y el 0,81% fuera de ×2. Entre ×2
  y ×2,5 hay sobre todo cadenas chicas (Deheza, La Agrícola Regional) con precios persistentes, y los meses de la
  devaluación de dic-2023, cuando las cadenas actualizaron precios en días distintos. **×2,5 queda.**
- **Plausibilidad por EAN** (banda ×4): ningún EAN fuera.
- **Control de identidad**: 8 EANs para revisar (saltos ×2), sin excluir.

## 10. Cambios hechos

### 10.1 En el nb06 (esta entrega)

1. **Canasta**: regla "equivalentes primero" (§3.2): 62 productos en 43 líneas (75 códigos). "Misma marca primero"
   con tope: una marca con k sin TACC tiene a lo sumo k con TACC de su marca. No cambia la canasta fija.
2. **Precios de una empresa fuera de escala** (§9).
3. **CELDA 8c, análisis complementarios**:
   - `Sensibilidad` (8 escenarios configurables en `ESCENARIOS_SENSIBILIDAD`);
   - `Indices_lados` con el IPC (`IPC_XLSX`);
   - `Disponibilidad` y `Disponibilidad_mensual`;
   - `IC_grupos` (bootstrap por sucursal, `BOOT_B` réplicas, semilla fija);
   - `Competencia_local` y `Concentracion_modelos`;
   - `Hedonica_grupos` (con `confiable`);
   - `Costo_CBA` y `Costo_CBA_mensual`.
4. **Gráficos nuevos**: índices de cada lado, disponibilidad por región, IC de los grupos, sensibilidad y hedónica.
5. **Hoja `Resumen`** al principio del Excel: los números principales, con su IC y la hoja de cada detalle.
6. **Carpeta `datos/`** para el análisis propio (parquet y csv.gz):
   - `panel_sucursal_mes_subtipo`: brecha y precios de cada lado, con región, empresa, departamento, HHI, competencia y
     coordenadas;
   - `panel_producto_sucursal_mes`: precio de cada producto, con descripción;
   - `sucursales.csv`.
7. **Test**: 42 controles contra fuerza bruta. Entre ellos:
   - la hedónica recupera exactos los efectos de un SEPA sintético;
   - los índices = mínimos cuadrados densos;
   - el IC es determinístico;
   - el Resumen = sus hojas.

   Los 15 tests del repo dan OK.

### 10.2 Canasta amplia de la oferta actual (nb06b, hecha)

Es la recomendación principal del panel para medir el costo de la dieta: las mismas reglas sobre los últimos 15 meses
(ago-2025 → oct-2026), con pan envasado, harinas, premezclas, alfajores y tapas. Cubre el 62% de los artículos con
gluten de la ENGHo. Notebook `notebooks/06b_brecha_celiaca_canasta_amplia.ipynb` (mismo generador y mismas celdas que
el 06); canasta de 142 códigos en 109 líneas; detalle en BRECHA_CELIACA §16. Simulación = cálculo independiente.

| | Canasta fija (nb06) | Canasta amplia (nb06b) |
|---|---|---|
| Brecha de los últimos 12 meses (IC 95%) | +103,1% (+102,6% a +103,5%) | **+143,3%** (+143,1% a +143,9%) |
| Costo extra por adulto equivalente por mes (CBA) | +$18.815 (sin pan ni harina) | **+$156.474** (+171%; el pan, el 83%) |
| Costo extra de un hogar tipo por mes | +$58.138 | **+$483.504** |
| Regiones | Patagonia +89% a Cuyo +107% | Patagonia +130% a Cuyo +155% |
| Empresas confiables con la canasta propia | 2 | 3 (Carrefour, Cencosud, Coto) |
| Disponibilidad del sin TACC (sucursal-meses) | 67,9% | 74,1% (harinas 25%, tapas 40%, alfajores 43%) |
| Concentración (con empresa y región) | sin efecto | −0,26% por +0,1 de HHI; nada con los mismos productos |

Los tipos nuevos ordenan la prima de otra manera:

- la premezcla universal cuesta 5 veces la harina 0000 (+383%) y el pan sin TACC 3 veces el envasado con TACC (+199%);
- el pan rallado y el rebozador sin TACC, +236%;
- las tapas, +56%; las premezclas de bizcochuelo y brownie, +46%;
- los alfajores, +15%.

Las conclusiones de geografía, cadenas y concentración no cambian: las diferencias de nivel son sobre todo de surtido
y la concentración local no sube la prima.

### 10.3 Lo que no se hizo, y por qué

- **Pan francés fresco**: no está en el SEPA con código de barras. Ninguna canasta del SEPA lo puede medir.
- **Ajuste por tamaño del envase.** Muchos sin TACC vienen en envases más chicos (fideos de 250-300 g contra 500 g) y
  el $/100 g baja con el tamaño. La brecha por 100 g lo incluye, porque es lo que paga el celíaco. Separar el efecto
  tamaño necesita el mismo producto en dos tamaños, que la canasta casi no tiene.
- **Promociones**: el SEPA publica precios de lista; si los sin TACC tienen otra frecuencia de ofertas, la brecha
  pagada puede diferir.
- **Pesos por subtipo de consumo real**: la ENGHo no abre los fideos o las galletitas por subtipo. Van como
  sensibilidad.
- **Subtipo vainillas** (Pozo contra Santa María): hay que fechar el cambio de 85 a 80 g; queda abierto.

## 11. Cómo correrlo desde GitHub y qué sale

1. Abrir el notebook con el botón de Colab del README:
   `notebooks/06_evolucion_brecha_celiaca.ipynb`.
2. En el Drive, carpeta `MyDrive/carga/`:
   - los zips semestrales del SEPA (`2022A.zip` → `2026B.zip`);
   - `ar.json`;
   - `IPC.xlsx` (opcional, para el IPC en `Indices_lados`);
   - la caché de Georef del nb09 (`output_trazabilidad/_cache_nb09/georef_sucursales.parquet`; si no está, consulta
     la API de Georef).
3. Correr todo. La primera vez lee los 58 meses (~1 h en el Colab gratuito); con la caché, unos 15-20 min (los
   intervalos por bootstrap de la CELDA 8c tardan ~7 min con `BOOT_B = 200`; con menos réplicas tarda menos).
4. En `MyDrive/carga/output_brecha/` quedan:
   - `brecha_celiaca_AAAA-MM.xlsx`: 51 hojas; empezar por `Resumen` y `Leeme`;
   - 16 gráficos `.png`;
   - el mapa por provincia y el mapa por sucursal (`.html`);
   - `datos/` con los paneles.
5. Para comparar una corrida con la simulación:
   `python -I -X utf8 docs/auditoria/scripts_nb06_2026-10/s16_comparar_colab.py <Excel> docs/brecha_celiaca/simulacion_2026-10-27`.
6. **Canasta amplia**: lo mismo con `notebooks/06b_brecha_celiaca_canasta_amplia.ipynb` (su botón de Colab está en el
   README). La primera vez lee 15 meses; escribe en `MyDrive/carga/output_brecha_amplia/`
   (`brecha_celiaca_amplia_AAAA-MM.xlsx`, gráficos, mapas y `datos/`). Esperados:
   `docs/brecha_celiaca/simulacion_06b_2026-10-27/`.

## 12. Scripts de esta evaluación

En `docs/auditoria/scripts_nb06_2026-10/`:

- `s10_precios.py`: equivalentes primero y misma marca con tope;
- `s11_simular_nb06.py`: `--ipc` y `--notebook` (el 06b), y guarda los objetos nuevos;
- `s12_comparar_simulacion.py`: con el filtro de empresas; `--notebook` y `--cache` (verifica el 06b con los precios del
  caché);
- `s15_filtrar_cache.py`: clave con los ADICIONALES; `--notebook`;
- `s18_canasta_amplia.py`: canasta amplia (gramos con el consenso de las cadenas, alfajores sueltos y en caja, harinas y
  premezclas separadas).

Los análisis exploratorios de esta sesión (distribución del factor por empresa, descomposición del efecto de DIA) están
descritos en §6 y §9; sus números se reproducen con los paneles de `datos/`.

## 13. La corrida de Colab del nb06 (2026-10-27, tarde)

El usuario corrió el nb06 en Colab y pasó la salida impresa y el zip de `output_brecha/`
(`colab_20261027/` en la carpeta de trabajo). Colab leyó los 57 meses cerrados en 41:45 min, más el mes en curso, y
armó el caché `brecha_v3_5fc88a8c`. **Dio igual a la simulación en todo**:

| Qué | Contra qué | Resultado |
|---|---|---|
| Excel, las 48 hojas de los esperados | `docs/brecha_celiaca/simulacion_2026-10-27/` (s16) | 48 de 48 iguales |
| Excel completo (51 hojas, también `Leeme`, `Comparacion_productos` de 20.856 filas y `Detalle_producto` de 59.892) | el Excel de la simulación (r13) | 51 de 51 iguales |
| Caché del Drive | el caché local (r14) | los 57 meses con los mismos datos (otros bytes) |
| Mapa por sucursal | el de la simulación (r15) | igual, salvo los identificadores aleatorios de Folium |
| `datos/`: los dos paneles en parquet y csv.gz | los de la simulación | iguales (3.244.531 y 542.159 filas) |
| `datos/sucursales.csv` | el de la simulación | iguales; 183 filas difieren en el último dígito de un decimal de 17 cifras (redondeo) |
| Salida impresa | la de la simulación | los mismos números en todas las tablas y avisos |

Diferencias esperables que no cambian nada:

- en Colab el maestro de productos suma el `maestro_sepa_completo` del Drive (204.374 códigos contra 176.607 en la
  simulación): la canasta tiene sus gramos y descripciones en la CELDA 1;
- el IPC sale del `IPC.xlsx` del Drive, hasta sep-2026.

**Gráficos**: al mirarlos aparecieron cinco detalles de presentación, corregidos en la CELDA 9. El Excel no cambia; la
próxima corrida (con el caché, unos 15-20 min) los rehace:

- en la hedónica, la leyenda del eje se cortaba a la derecha (ahora va en dos renglones);
- en los índices de cada lado, el subtítulo decía "encadenado" (son efectos fijos);
- en los IC por grupo, la leyenda del país tapaba el último grupo (la franja va explicada en el título);
- en la disponibilidad, los nombres de los tipos iban rotados 90° (ahora horizontales, en dos renglones);
- en la sensibilidad, la etiqueta de la barra más larga quedaba pegada al borde (más margen).

Falta la corrida de Colab del **06b** (lee 15 meses la primera vez): se compara con
`docs/brecha_celiaca/simulacion_06b_2026-10-27/`.
