# Revisión de la corrida nb02 — oct-26 al 15/10 (2026-10-16)

Primera corrida en Colab de las CELDAS 19b y 19c (commit `d140972`). Insumos que pasó el usuario: la salida impresa,
`canasta_analisis_2026-10.xlsx`, `canasta_representativa_2026-10.xlsx`, `trazabilidad_candidatos_2026-10.xlsx`,
`datos_econometria_2026-10.xlsx` y un zip de `output_canasta/_cache/` (`detalle_ea281ee7_v1.parquet`,
`hist_union_d452a45b_v2m.parquet`, `econ_7c7bf6d7.parquet`, `df_suc_2026-10.parquet`). Los insumos no están en el repo.

Resultado: **lo nuevo (19b y 19c) dio exactamente lo validado**; la revisión encontró defectos previos en las CELDAS 16,
18 y 20 (los números del documento técnico), corregidos el mismo día como **BUG-42** (commit `d6e1f52`).

## 1. La corrida

| Punto | Resultado |
|---|---|
| Canastas | 6 activas: Vulnerable 45 productos, Popular 59, Media 69, Media Alta 75, Celíaca Media 71, Vegana Básica 50; **256 EANs** en la unión, todos con datos |
| Mes | Octubre 2026 **parcial, 15/31 días** (`102026_pais_parte1COMPLETO.csv.gz` en 2026B.zip): nivel = foto al 15; variación preliminar |
| Universo | Maestro 3.600 sucursales; 4.846.917 observaciones sucursal × día; 2.435 sucursales; 121 reclasificadas por coordenadas; 2.290-2.308 sucursales por canasta en el Cuadro 1 |
| Serie | Caché `hist_union_d452a45b_v2m` al día (33 meses cerrados) + oct-26 fresco; 34 meses 2024-01 → 2026-10 |
| IPC | 117 meses, 2017-01 → **2026-09** (octubre sin publicar) |
| Tiempos | 19c primera vez **2.069 s** (12 meses leídos del SEPA, 158-182 s cada uno; deja `detalle_ea281ee7_v1.parquet` con 13 meses). Econometría releyó 33 meses (`en cache: 0`): el caché `econ_7c7bf6d7` es nuevo; la próxima corrida tiene que decir 33 en caché |

## 2. Lo nuevo: CELDAS 19b y 19c — OK

- **19b**: oficial **+1,748%** ($673.534 → $685.307), medianas reproducidas **69/69**, arrastre +1,479 pp y suba nueva
  +0,269 pp, panel apareado +1,971% (2.927 sucursales, 91.650 pares, 0 fuera de banda). Idéntico a la validación del
  2026-10-15 con el prototipo.
- **19c**: `analisis_detallado` es la primera de las 39 hojas, sin AVISO de "Total vs suma ponderada". Total oct-26
  +1,75 = oficial; la variación de cada grupo = `var_mediana_grupo_%` de la 19b.
- Ponderaciones con base sep-25 (12 meses): Perfumería 21,55, Frescos 19,92, Almacén 19,71, Bebidas 15,80, Limpieza
  14,61, Congelados 8,41. La validación del 15/10 (base jul-26) daba 21,8/20,0/18,4/16,4/15,0/8,4: la ponderación es la
  del mes base y cambia con él.
- Interanual a sep-26 (índice sep-25 = 100): Total **126,54**; Perfumería 129,56; Bebidas 130,46; Limpieza 128,66;
  Frescos 127,23; Congelados 124,18; Almacén 118,84. Regiones: AMBA 128,45, Patagonia 127,85, Pampeana 125,59,
  Noreste 125,25, Noroeste 120,61, Cuyo 119,91.

## 3. Defectos encontrados y corregidos (BUG-42)

"Ahora" = la CELDA 20 nueva corrida sobre los mismos datos con
`docs/auditoria/scripts_nb02_2026-10/simular_valores_documento.py`.

| # | Defecto | Antes (corrida) | Ahora (mismos datos) |
|---|---|---|---|
| 1 | "AMBA" de los rankings de cadenas = CABA + **toda** la provincia | 1.655 sucursales (Media); Toledo (Mar del Plata), Cooperativa Obrera (Bahía Blanca) y La Anónima en el ranking AMBA | AMBA = CABA + Buenos Aires a ≤ 90 km del Obelisco: **1.405** sucursales, sin esas tres; Vea entra (22 sucursales) |
| 2 | Acumulados en períodos distintos | Media +167,36% (a oct-26 parcial) contra IPC Alimentos +166,35% (a sep-26): "arriba del IPC" | Mismo período ene-24 → sep-26: Media **+162,77%** contra **+166,35%**: abajo. Lo que va a oct-26 queda aparte, marcado "no comparar" |
| 3 | Cuatro "país" | Cuadro 1 $682.699; mediana de sucursales $684.682 (barrios, línea del gráfico de cadenas); media de sucursales $687.009 ("vs nacional" de cadenas en la CELDA 20); serie $685.307. Cadenas y barrios por **media** en la CELDA 20; "Promedio CABA" $687.986 ≠ fila CABA del Cuadro 1 ($685.945) | Todo "vs país" contra $682.699; CABA $685.945; cadenas y barrios por mediana (= rankings [mediana]). El nivel es el del Cuadro 1 y la variación la de la serie, con sus dos extremos en la hoja |
| 4 | Resumen asimétrico | 3 caras y 1 barata (nacional), 1 y 1 (AMBA) | 3 y 3 en los dos |
| 5 | Dispersión entre sucursales | mín-máx **38,8%** (una sucursal 20% abajo) | **P5-P95 6,5%** ($667.148-$710.624); el mín-máx queda con la sucursal: mínima Hiper ChangoMas San Martín $548.469 (66/69 productos propios), máxima Jumbo Comodoro $761.229 |
| 6 | Formato | "+8.7%" (con `abs()`: una prima negativa salía "+"), "240.1%", "38.8%" | coma decimal y signo: "+8,66%", "240,1%". Re-correr la celda ya no crea `Valores_Documento1` |

Acumulados ene-24 → sep-26 (mismo período que el IPC):

| Serie | Acumulado | | Serie | Acumulado |
|---|---:|---|---|---:|
| Vulnerable | +154,70% | | Media Alta | +168,86% |
| Popular | +146,11% | | Celíaca Media | +157,89% |
| Vegana Básica | +146,91% | | **IPC Alimentos** | **+166,35%** |
| Media | +162,77% | | IPC Nivel General | +193,65% |

Solo la Media Alta queda arriba del IPC Alimentos. Cadenas (Media, mediana por cadena, vs país): caras Jumbo +4,06%,
Disco +3,68%, La Anónima +3,23%; baratas Vea −2,03%, Carrefour −0,45%, Carrefour Market −0,21%; dispersión 6,2%. AMBA
(vs AMBA $684.682): Disco +4,02%, Jumbo +3,80%, Carrefour Express +0,73%; ChangoMas −2,23%, Carrefour −0,69%, Mi
ChangoMas −0,45%.

Test: `notebooks/test_valores_documento.py` (20 chequeos; con las CELDAS 16/18/20 viejas fallan 19).

## 4. Lecturas de los datos (no son defectos)

- **Vea bajó precios en jul-26**: 19 de sus 67 productos bajan más de 5% de junio a julio (−10% a −28%, con 3.000-4.700
  observaciones cada uno) y siguen abajo en agosto. Explica la caída de Cuyo, Noroeste, Mendoza, Salta, Tucumán, San Juan
  y San Luis en jul-26 de `analisis_detallado` (Vea pesa ahí) y el rebote de oct-26: Vea +4,05% (mediana del grupo),
  +4,33% en el panel y el mayor aporte por cadena (0,40 pp). Reproducir con `productos_que_mueven_grupo.py`.
- **La suba de octubre es casi toda arrastre**: 1,48 de los 1,75 pp ya estaban en la última semana de septiembre.
- Productos que más aportan en oct: Acondicionador Sedal 650 (+5,55%, 0,16 pp, todo arrastre), Medallón Good Mark (0,13),
  Lavandina Ayudín 2 L (+6,87%, 0,11 pp, todo suba nueva), Aromatizante Glade (0,10), Mortadela Cabaña Argentina
  (+13,5%, 0,10).
- **DIA**: índice 137,23 a oct-26 (base sep-25) contra 128,75 del Total, con 32 de los 69 productos.
- Con la mediana, muchas provincias y barrios repiten el mismo valor (Corrientes, Entre Ríos y Santa Fe $288.683 en la
  Vulnerable; ~20 barrios en el precio de DIA): la sucursal mediana es de una cadena con precio nacional. El "bottom 3"
  de barrios por mediana es arbitrario entre empates; el análisis [promedio] los separa.

## 5. Abiertos (no corregidos; en `docs/BUGS_Y_MEJORAS.md`, "nb02 — abiertos")

- ✅ **Región de la 19b/19c = `REGION` del maestro**, que marca AMBA a ~100 sucursales de DIA del interior bonaerense
  (Mar del Plata, Tandil, Pergamino; localidad "BUENOS AIRES"): el AMBA de `analisis_detallado` (1.819 sucursales) las
  incluía. **Resuelto el mismo día (BUG-43, §8)**.
- **~540 sucursales fuera del maestro** (2.959 en el panel de la 19b, 2.419 en el maestro): no entran al Cuadro 1, mapas
  ni rankings. La mayor es "Cadena 24" (332 sucursales, 9 de 69 productos: perfil de farmacia/perfumería, sin
  identificar); Carrefour Express tiene 511 sucursales en la 19c y 386 en el Cuadro 1; Toledo 27 y 13.
- **Cadenas con 2-9 productos** en la 19c (Cadena 24, 23, 6): falta un mínimo de productos además del de sucursales.
- **Provincia distinta según la hoja**: la 19b/19c usan el código ISO del archivo de precios (CABA 1.131 sucursales) y el
  Cuadro 1 el maestro con reclasificación por coordenadas (CABA 834). No comparar cantidades de sucursales entre hojas.
- **Barrios por rectángulos superpuestos** (gana el primero del diccionario): Palermo (73) y Belgrano (69) absorben
  vecinos; Colegiales, Retiro, Villa Luro y Villa Riachuelo quedan con ≤ 1 sucursal. Arreglo: polígonos oficiales.
- Trazabilidad: "EANs en canastas activas (229 únicos)" son 229 de 256; 27 EANs de las canastas no están en Candidatos
  y no tienen control. Erratas en descripciones de candidatos ("Trega", "Boldoen", "La Virgina").
- El **nb05** tiene el mismo AMBA = CABA + provincia (tarjeta de sesión propuesta el 2026-10-16).

## 6. Cómo reproducir

Scripts en `docs/auditoria/scripts_nb02_2026-10/` (los insumos no están en el repo):

```bash
python -I docs/auditoria/scripts_nb02_2026-10/simular_valores_documento.py . <canasta_analisis_2026-10.xlsx> <carpeta>
python -I docs/auditoria/scripts_nb02_2026-10/validar_amba_maestro.py data/maestro_sucursales_completo.xlsx
python -I docs/auditoria/scripts_nb02_2026-10/productos_que_mueven_grupo.py <detalle_ea281ee7_v1.parquet> cadena Vea 2026-06 2026-07
python -I docs/auditoria/scripts_nb02_2026-10/comparar_corridas.py <Excel nuevo> <Excel anterior o simulado>
python notebooks/test_valores_documento.py
```

## 7. Verificación en Colab (segunda corrida, 2026-10-16) ✅

El usuario re-corrió el nb02 con el commit `d6e1f52` (mismos datos: oct-26 al 15/10) y pasó la salida de las CELDAS 7,
16, 18 y 20, el Excel y el caché. Comparado contra la corrida anterior y contra la simulación del §3:

- **`Valores_Documento`**: 223 filas, **idénticas a la simulación** (la única diferencia es el rótulo del mes, que la
  simulación escribe como `2026-10`). La hoja aparece una sola vez.
- Cambiaron solo las hojas esperadas: `Ranking_*` (las columnas `vs_mediana_%` y `vs_prom_%`, ahora contra el Cuadro
  1: Jumbo +4,06% en la Media) y `Sucs_*` (columna `amba` nueva; el resto de las columnas, igual). Las otras 33 hojas
  —`analisis_detallado`, las 13 de la 19b, `Prov_*`, `Evolucion_IPC`, `Serie_precios`, `CABA`, `costa`...— son
  idénticas a las de la primera corrida.
- `amba` = 1.405 sucursales en cada canasta (1.406 en la Vulnerable): toda CABA (834) y 571 de las 821 bonaerenses.
  La CELDA 7 imprime 1.974: es el universo del maestro con coordenadas, antes de exigir cobertura de la canasta.
- CELDA 18: "Pais (Cuadro 1, ponderado)" = el promedio del Cuadro 1 de cada canasta ($288.714 la Vulnerable, $682.699
  la Media); con esa referencia todos los barrios de CABA quedan arriba del país salvo en la Media Alta.
- Cachés sin cambios (`hist_union_d452a45b_v2m`, `detalle_ea281ee7_v1`, `econ_7c7bf6d7` byte a byte iguales): no releyó
  nada, como se esperaba (la 19b/19c no se tocaron).

## 8. Región de la 19b/19c por coordenadas (BUG-43, 2026-10-16) — simulado con datos reales, falta Colab

**Cambio**: AMBA = columna `amba` de la CELDA 7 (el mismo AMBA del Cuadro 1, los rankings y `Valores_Documento`); el
resto de las regiones, por la provincia del archivo de precios (la de la dimensión provincia de esas hojas). Antes: la
`REGION` del maestro. Sin coordenadas en la CELDA 7 (fuera del maestro, web, "CABA" fuera de CABA): Buenos Aires →
`Buenos Aires s/ubicar`; código desconocido → `Sin dato`. La clave del caché de la 19c cambia: **la próxima corrida en
Colab relee los 12 meses una vez (~35 min)**.

**Simulación** (`simular_region_19b_19c.py` dos veces, código viejo y nuevo, + `comparar_region_19b_19c.py`): CELDAS
19b y 19c reales sobre los zips locales (2026A.zip ene-jun, 2026B.zip jul; no hay ago/sep localmente, así que no se
puede simular oct-26), `PERIODO = 2026-07`, `DETALLE_MESES = 6` (feb-jul, base ene-26).

- **Validación**: las dimensiones que no son región (nacional, provincia, cadena, tipo) del caché simulado son
  **idénticas** al caché de la corrida real de Colab (`detalle_ea281ee7_v1`) en ene-jun 2026: 18.862 medianas, 0
  diferencias. Y entre código viejo y nuevo, las 1.260 celdas de `analisis_detallado` que no son región son idénticas.
- **Sucursales que cambian de región**: 96 de 3.106. **91 DIA del interior bonaerense AMBA → Pampeana** (el defecto);
  Carrefour Market Chilavert (San Martín, GBA) Pampeana → AMBA (el maestro estaba mal); La Anónima web y ChangoMas
  Moreno (declarada CABA en el maestro, la CELDA 7 la descarta) AMBA → `Buenos Aires s/ubicar`; 2 de "Cadena 19" que el
  archivo de precios declara Buenos Aires pero están en Mendoza y Resistencia: Cuyo/Noreste → Pampeana (error de carga
  del SEPA; esa cadena está en `CADENAS_FILTRAR` del Cuadro 1). Patagonia, Cuyo, Noroeste y Noreste no cambian.
- **Efecto** (índice ene-26 = 100 a jul-26): AMBA 114,45 → 114,59; Pampeana 112,85 → 112,74; Buenos Aires s/ubicar
  112,26 → 112,18; el resto igual. Variación mensual de Pampeana hasta 0,33 pp (may +2,45 → +2,69; jun +1,58 → +1,25);
  AMBA hasta 0,13 pp (jul +2,04 → +2,17). Hoja `Regiones` de la 19b (jun → jul): AMBA 1.878 → 1.788 sucursales, control 2,04% → 2,17%;
  Pampeana 570 → 660, 1,74% → 1,65%.
- Tests: `test_desagregacion_variacion.py` (casos: AMBA del maestro en Mar del Plata, maestro sin coordenadas, código
  de provincia desconocido, Neuquén capital) y `test_analisis_detallado.py` (una sucursal que se muda fuera del AMBA
  cambia la clave del caché y relee); con las celdas viejas, los dos fallan.

**Una primera versión** tomaba también la provincia reclasificada de la CELDA 7 para las regiones fuera del AMBA: la
simulación mostró 37 sucursales de Neuquén/Río Negro pasando de Patagonia a Pampeana. Así apareció el BUG-44 (§9) y se
pasó a la provincia del archivo (que además es la de la dimensión provincia de esas hojas).

## 9. BUG-44: la reclasificación de provincia de la CELDA 7 — resuelto (falta Colab)

**El defecto**: con rectángulos y "la primera provincia cuyo rectángulo contiene el punto", la CELDA 7 reclasificaba 121
sucursales del maestro, la mayoría mal — Neuquén → La Pampa 47 (Neuquén capital, Centenario, Plottier), Entre Ríos →
Santa Fe 40 (Paraná), Buenos Aires → Entre Ríos 10 (San Nicolás), Río Negro → La Pampa/Chubut 7 (Catriel, El Bolsón) —
con algunos aciertos (6 DIA de Jujuy declarados San Juan en el SEPA y en el maestro).

**El fix**: polígonos de provincias de `ar.json` (simplemaps, el del mapa coroplético; el id `AR` + letra ISO da la
provincia). Una sucursal cambia de provincia solo si está a más de `RECLASIF_TOL_KM` (100) km del polígono de su
provincia declarada y dentro del de otra. CABA sigue con su filtro por rectángulo; sin `ar.json` no se reclasifica.

**Elección de la tolerancia** (prototipo sobre el maestro): 164 sucursales caen fuera del polígono declarado, 146 a menos
de 10 km (bordes y el polígono de CABA de 18 vértices, que se come parte del conurbano). Reclasificadas según la
tolerancia: 0 km 143 (109 del conurbano a CABA), 5 km 19, 10 km 15, 20 km 14, 50 km 13, **100 km 12**. Entre 20 y 100
km solo quedaban Viedma II (30 km, coordenadas al norte de Viedma) y un DIA "Baradero" con coordenadas 55 km dentro de
Entre Ríos: en los dos el nombre contradice a las coordenadas, así que se quedan en su provincia declarada.

**Con 100 km** (`reclasificacion_celda7.py` corre la CELDA 7 real): 12 reclasificadas, todas a más de 180 km de su
provincia — San Juan → Jujuy 6 (DIA), Mendoza → Misiones 2 (Posadas), Río Negro → Entre Ríos 1 (TEC Paraná), Córdoba →
Mendoza 1 (Libertad "Dark Store Mendoza"), Buenos Aires → Santa Fe 1 (una tienda web), Entre Ríos → Córdoba 1 (una
"Gualeguaychú" con coordenadas en el sur de Córdoba: dudosa, el nombre dice otra cosa). El AMBA no cambia (1.974).

**Efecto colateral corregido**: la econometría (CELDA 22) agrega por la provincia y la cadena de la CELDA 7 y guardaba
los meses con una clave que solo dependía de los EANs: la serie provincial habría mezclado la provincia vieja (33 meses
del caché) con la nueva (el mes en curso). La clave ahora incluye la geografía: **la próxima corrida relee los 33 meses
de la econometría**, además de los 12 de la 19c (BUG-43). La serie de la CELDA 9 no usa provincias (su caché no cambia).

Test: `test_reclasificacion_provincia.py` (borde, error grosero, umbral de 100 km, agujero de Buenos Aires, AMBA después
de reclasificar, CABA, sin `ar.json`); con la regla vieja fallan 4 de sus casos.

## 10. Colores del Excel (pedido del 2026-10-16)

Azul → verde en todo `canasta_analisis_*.xlsx`: encabezados de todas las hojas y filas de sección de
`analisis_detallado` `1F4E79` → **`375623`** (verde oscuro, "Verde, Énfasis 6, Oscuro 50%"); fila de encabezado de
`analisis_detallado` `D9E1F2` → **`92D050`** ("Verde claro"). Constantes `VERDE_OSCURO`/`VERDE_CLARO` de la CELDA 19;
`test_analisis_detallado.py` controla que no quede azul. El Excel de oct-26 se recoloreó aparte (644 celdas, valores
idénticos); las próximas corridas salen en verde.

## 11. Cuadro 1 de oct-26 con la provincia nueva (BUG-44)

`cuadro1_reclasificacion.py`: la CELDA 8 real con las sucursales de la corrida (hojas `Sucs_*`), con la provincia de
entonces (reproduce las hojas `Prov_*` exactas) y con la de la CELDA 7 vigente. En la canasta Vulnerable cambian de
provincia 74 sucursales: La Pampa → Neuquén 34, Santa Fe → Entre Ríos 29, Entre Ríos → Buenos Aires 5, Chubut → Río
Negro 2, La Pampa → Río Negro 2, Córdoba → Santa Fe 1, Chaco → Formosa 1 (las 12 reclasificaciones de la regla nueva
ya estaban o no están en la canasta).

Canasta Media (filas que cambian; país del Cuadro 1 $682.699 → $682.768, +0,01%):

| Provincia | Sucursales antes → ahora | Canasta antes | Canasta ahora | Cambio | vs país antes → ahora |
|---|---|---:|---:|---:|---|
| Neuquén | 24 → 58 | $707.498 | $701.607 | −0,83% | +3,63% → +2,76% |
| La Pampa | 55 → 19 | $697.799 | $694.601 | −0,46% | +2,21% → +1,73% |
| Santa Fe | 65 → 37 | $681.225 | $684.304 | +0,45% | −0,22% → +0,23% |
| Entre Ríos | 58 → 82 | $678.525 | $678.525 | 0 | −0,61% → −0,62% |
| Formosa | 4 → 5 | $677.994 | $681.565 | +0,53% | −0,69% → −0,18% |
| Chaco | 4 → 3 | $677.462 | $673.358 | −0,61% | −0,77% → −1,38% |
| Buenos Aires | 821 → 826 | $684.682 | $684.682 | 0 | +0,29% → +0,28% |
| Río Negro / Chubut / Córdoba | ±1-4 | — | — | ≤ 0,02% | — |

Otras canastas (país antes → ahora): Vulnerable $288.714 → $288.878 (+0,06%), Popular $505.982 → $505.894 (−0,02%),
Media Alta $981.879 → $982.596 (+0,07%), Celíaca Media $741.843 → $741.872 (+0,00%), Vegana Básica $468.810 →
$469.096 (+0,06%). En todas Neuquén baja 0,7-1,2% y Santa Fe sube hasta 1,2%. La provincia más barata y la más cara
no cambian, salvo en la Vegana Básica: la más cara pasa de Neuquén ($487.007) a Chubut ($481.050) y la dispersión
interprovincial de 8,3% a 7,0%. En `Valores_Documento` cambian levemente todos los "vs país" (el país se mueve ≤ 0,07%).

Pendiente: re-correr el nb02 en Colab —relee 12 meses en la 19c y los 33 de la econometría, una vez— y revisar la
provincia (Cuadro 1 como en este §11), la región (§8) y los colores (§10); el resto de los abiertos del §5; portar la
provincia por polígonos y el AMBA al nb05.
