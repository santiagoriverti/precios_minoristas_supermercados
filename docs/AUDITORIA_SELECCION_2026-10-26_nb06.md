# Auditoría de la selección de productos de la canasta fija (nb06) — 2026-10-26

**Pregunta del usuario**: ¿la selección de productos está bien hecha para estimar la brecha celíaca (cuánto más paga un
celíaco que un no celíaco, su evolución, su geografía, la concentración y las cadenas)? Insumos: la carpeta `carga/`
del Drive (zips semestrales 2022A → 2026B, salidas del nb09, maestros), las tablas de la selección del 2026-10-23
(`s7`-`s10`) y el listado oficial de alimentos libres de gluten de ANMAT.

**Respuesta corta**: la selección es sólida en lo que más importa. Ningún producto con TACC está etiquetado sin TACC, y
los sin TACC son de marcas celíacas o tienen registro de ANMAT. La identidad de cada código y los gramos ya estaban
verificados con precios (s10), y el procedimiento reproduce exacto la canasta del 2026-10-23. Aparecieron cuatro
problemas de reglas, corregidos el mismo día: (1) un patrón mal escrito dejaba afuera galletitas; (2) los fideos Blue
Patna son al huevo; (3) el tirabuzón sin TACC Matarazzo quedaba afuera por el cambio de código de Molinos; (4) dos
sabores de Lasfor quedaban afuera por un comercio. Con las correcciones la canasta queda en **66 productos (77
códigos)**. La brecha de la canasta de los últimos 12 meses pasa de +122,7% a +118,0%, casi todo por los fideos, y
ChangoMas deja de ser confiable: su +140% venía de los Blue Patna (§3 y §3b). Quedan cuatro propuestas de diseño para
decidir (§4).

## 1. Etiqueta sin TACC: listado ALG de ANMAT

Consultado el 26/10/2026 en `listadoalg.anmat.gob.ar` (buscador por marca y denominación; estado "Vigente"):

| Producto de la canasta | Lado | ¿Registro ALG? | Evidencia |
|---|---|---|---|
| Almohaditas rellenas Snuks 240 g (chocolate, avellana, limón, frutilla) | sin TACC | Sí, las cuatro | 02-599456, 02-599453, 02-611120, 02-600351. La de avellana entraba solo por la marca: está registrada |
| Almohaditas Lasfor 200 g (los cuatro sabores) | con TACC | No: Lasfor no tiene ningún ALG | Snuks es la línea sin TACC del mismo fabricante (Lasfor SRL, prefijo GS1 7798169): el par más limpio de la canasta |
| Galletas de arroz Grandiet con sal, sin sal, multicereal (con y sin sal) y pizza | sin TACC | Sí | 04061116, 04061115/04061059, 04061114, 04061058, 04061056. Grandiet es marca dietética, no celíaca: entran por la etiqueta |
| Smams (crackers, mix semillas, light, con chips, pepas, rellenas, Colegial) | sin TACC | Sí | Marca entera libre de gluten (116 registros) |
| Wakas fusilli multicereal amaranto, maíz y quinoa | sin TACC | Sí | 02-591701, 02-591700, 02-591704 |
| Wakas fusilli multicereal chía | sin TACC | No encontrado | 3 de 7 cadenas lo publican sin TACC el 22/10; la marca es 100% sin gluten. Se mantiene |
| **Blue Patna spaghetti, mostacholes, tirabuzones** | sin TACC | Sí, como **"pastas secas de harina de arroz al huevo"** | 04036877-80, 036-00-000548. **Son fideos al huevo**: ver §2 |
| Matarazzo sin TACC spaghetti, penne y tirabuzón | sin TACC | No encontrado (Matarazzo solo registra el "Mix de legumbres", 02-718305) | 6-7 de 11-12 cadenas los publican "sin TACC" o "libre de gluten"; en 2022 costaban 2-3 veces el Matarazzo común en las mismas sucursales (§14.4). Se mantienen |
| Crisppino Minis 50 g jamón y queso | sin TACC | Sí | 02-587636, 02-587637 |
| Crisppino 100 g jamón y queso, Mini oliva | sin TACC | No encontrados (sí las Clásicas, 02-589006) | Maestro y SEPA dicen sin TACC; marca de snacks de arroz sin gluten. Se mantienen |
| Aglu limón y rebozador | sin TACC | Sí | 02-526238, 02-526241 |
| Naturalsur rebozador | sin TACC | Sí | 02-569056 |
| Santa María (Ana Hernández) marmoladas | sin TACC | Sí | 02-569932 (también las pepas, 02-567443) |
| Santa María vainilla 200 g y obleas limón 90 g | sin TACC | No encontrados | Marca celíaca; el Maestro y las cadenas los describen sin TACC. Se mantienen |

Del lado con TACC, ninguna cadena publica como sin TACC ningún producto (SEPA diario del 22/10, `r20`).

## 2. Errores de las reglas y correcciones aplicadas

| # | Problema | Corrección en `s9_seleccion.py` | Qué cambia en la canasta |
|---|---|---|---|
| 1 | **Patrón `tita\b`** (las Tita de Terrabusi) en la regla de galletitas dulces: también atrapaba "galle**tita**" en singular, como varias cadenas publican el producto. Dejaba 112 productos "fuera de subtipo"; solo uno pasaba las demás reglas (`r25`) | `\btita\b` | Maná Limón 152 g (1.302 sucursales por día) reemplaza a Maná Chocolate 152 g (890) en rellenas con TACC: mismo precio, más cobertura |
| 2 | **Blue Patna es al huevo** (ANMAT) aunque la descripción no lo diga; la regla 5 saca los fideos al huevo por no comparables con los fideos comunes | `blue patna` en la lista de fideos fuera de subtipo | Salen sus spaghetti, mostacholes y tirabuzones. Con un solo sin TACC en spaghetti y penne, la composición espejada (regla 8) deja un solo con TACC, el de más cobertura: salen también el Spaghetti Lucchetti y el Penne rigate Matarazzo |
| 3 | **Tirabuzón sin TACC Matarazzo**: afuera por oct-nov 2023 sin precio. El código viejo vale hasta sep-2023 (después queda congelado) y el nuevo aparece recién en dic-2023, en el cambio de código de Molinos. El spaghetti y el penne de la misma línea estaban adentro | En los empalmes, oct-nov 2023 sin precio no cuentan contra la continuidad | Entra (813 sucursales por día, 24 provincias, 7 cadenas grandes): las tres formas de fideos tienen ahora el Matarazzo sin TACC |
| 4 | **Lasfor Chocolate Suizo y Crema de Frutilla 200 g**: afuera solo por 7 comercios súper (el lado con TACC pide 8); la Mousse Limón y la Crema Avellanas de la misma línea tienen 8 | Sabores de una línea que pasa: a un con TACC le puede faltar un comercio si otro producto de la misma marca, presentación y subtipo pasa todo. Solo entran esos dos (las marineras Don Pancho también tienen 7, pero ningún producto de su línea pasa) | Las almohaditas quedan 4 contra 4 con los mismos sabores que los Snuks |

Control: `s10` sobre la tabla de `s9` del 2026-10-23 reproduce exacto la canasta vigente hasta ese día (80 códigos). Con
la regla corregida salen 66 productos (77 códigos): entran 5 códigos (Maná Limón, dos Lasfor y los dos del tirabuzón sin TACC Matarazzo) y
salen 8 (los tres Blue Patna, los dos del Spaghetti Lucchetti, los dos del Penne Matarazzo y Maná Chocolate).

## 3. Efecto sobre la brecha

Estimador del nb06 sin la imputación de subtipos (`r26`/`r27`; reproduce exacto la brecha por sucursal × mes × subtipo
de la simulación, 534.366 de 534.366), promedio de nov-2025 → oct-2026:

| | Canasta 2026-10-23 | Corregida | Corregida con las dos marcas con TACC en spaghetti y penne |
|---|---|---|---|
| **Canasta** | **+121,9%** | **+118,2%** | +118,2% |
| Fideos secos | +182,3% | +169,7% | +169,9% |
| Spaghetti | +155,9% | +126,0% | +148,8% |
| Mostachol / penne | +155,7% | +180,6% | +155,4% |
| Tirabuzón / fusilli | +244,4% | +209,7% | +209,7% |
| Rellenas | +68,5% | +69,2% | +69,2% |
| Almohaditas | +26,1% | +26,3% | +26,3% |

- La canasta baja 3,7 pp y los fideos 12,6 pp. Casi todo viene del tirabuzón sin TACC Matarazzo, que entra a ~2,3
  veces el con TACC contra 3,4-3,7 de los Wakas. Blue Patna pesaba poco (~170-270 sucursales por día).
- La regla espejada reordena spaghetti y penne, pero no mueve los fideos ni la canasta. El spaghetti queda Matarazzo sin
  TACC contra Matarazzo común (la misma marca). El penne queda contra los Mostacholes Lucchetti, la marca más barata de
  Molinos. **Con un producto por lado, la brecha de un subtipo depende de qué marca con TACC se elige**: leer spaghetti y
  penne juntos (o el tipo).
- Los demás subtipos no cambian. Las almohaditas ganan 18% de sucursal-meses con los dos lados y el tirabuzón 30%.

### 3b. Simulación completa del nb06 (58 meses releídos)

Se releyó el SEPA con los 116 candidatos de la selección corregida (42 min). Después se corrieron las celdas reales del
notebook con la canasta corregida (`sim_v5`). El cálculo independiente (`s12`) da lo mismo en precios, en brechas por
sucursal × mes × subtipo y × tipo, y en las 290 brechas por tipo y mes. Esperados nuevos:
`docs/brecha_celiaca/simulacion_2026-10-26b/` (35 hojas; cambian 34 contra la canasta anterior). Números y lectura
completa: `docs/BRECHA_CELIACA.md` §14.13. Lo principal:

- **Fideos de todo el período**: +172,3% → +160,6%. Los otros cuatro tipos no cambian.
- **Canasta de los últimos 12 meses** (nacional, misma canasta de los grupos): +122,7% → +118,0%. Por año, todas las
  sucursales: 2022 +118,9%, 2025 +99,7%, 2026 +120,1% (antes +120,2%, +104,4%, +125,4%).
- **ChangoMas deja de ser confiable** (de +140,4% a 37,6% del peso imputado): sus únicos fideos sin TACC eran los Blue
  Patna. Las dos empresas confiables quedan a 5 pp: Cencosud +116,2% y Carrefour +121,0%. Las regiones van de +104% a
  +121%.
- **Más sucursales medidas** en oct-2026: 2.324 contra 2.175. Cooperativa Obrera, Coto y Toledo entran con el tirabuzón
  sin TACC Matarazzo.
- **El penne de todas las sucursales queda imputado 16 meses** (2022-12 → 2024-03). Sin Blue Patna, su lado sin TACC
  es solo Matarazzo, de poca cobertura hasta 2024.
- **La TPD del panel en oct-2023 pasa de +174% a +114%, pero sigue siendo un artefacto** (§7): el spaghetti del panel
  no tiene pares ese mes y, movido con los demás subtipos, queda en −38%.

La variante que deja las dos marcas con TACC en spaghetti y penne (`sim_v5b`) cambia el nivel de esos dos subtipos
(+114,9% y +133,1%) pero no el de los fideos (+161,3%). Canasta, grupos, imputaciones y TPD quedan a menos de 1 pp. Se
mantiene la regla espejada.

## 4. Propuestas para decidir (no aplicadas)

| Propuesta | Por qué | Efecto medido (`r27`, sobre la canasta corregida; igual que sobre la anterior) |
|---|---|---|
| **Obleas: Opera 92 g en lugar de (o además de) la de 220 g** | Santa María sin TACC viene de 90 g; el precio por 100 g baja con el tamaño del paquete | Obleas +126,0% → +106,8% (o +119,6% con las dos); canasta −1,4 pp (−0,5 pp) |
| **Crackers sin las galletas de arroz** (o subtipo propio) | 4 de los 7 sin TACC del subtipo son galletas de arroz Grandiet, más baratas que los crackers sin TACC (Smams): es la sustitución del celíaco, pero no el mismo producto | Crackers +167,9% → +204,5%; canasta +3,6 pp |
| **Empalmar los códigos de los líderes con TACC** (Pepitos y quizás Oreo, Chocolinas, Toddy) | En con chips el comparador es Par Nor (333 sucursales por día, $1.214/100 g). Pepitos (2.260, $2.083/100 g) quedó afuera por cambiar dos veces de código (`7622201808662` → `7622201503260` → `7622201735906`) | Sin medir: los códigos viejos no están en `precios_mes` (hay que extraerlos de los zips). Con Pepitos, con chips bajaría mucho |
| **Subtipo vainillas** | La regla 5 las saca por no tener equivalente, pero Pozo 85 g (con TACC) y Santa María 180 g (sin TACC) pasan las reglas | Sin medir. Pozo publica 80 g en las cadenas: choca con la regla de gramos y hay que fechar el cambio |
| Mantener las dos marcas con TACC en spaghetti y penne | Comparador parejo en las tres formas de fideos (Lucchetti y Matarazzo) | Simulada (§3b): cambia el nivel de los dos subtipos, no el de los fideos ni la canasta. No hace falta |

## 5. Lo que se revisó y no cambia

- Identidad y gramos de cada código: s10 ya verifica estabilidad de precios, empalmes, cortes y gramos contra el SEPA.
- El lado con TACC son marcas de primera línea a base de trigo. Las económicas quedan afuera por la franja de precio:
  la revisión metodológica (`docs/REVISION_METODOLOGICA_2026-10-26_nb06.md`) ya lo señala para "cuánto más paga".
- La regla de subtipos de saladas manda a "fuera" lo que no coincide con ningún patrón (Express, Club Social). Ninguno
  de esos pasa las demás reglas: todos cambiaron de código en 2023-2024.
- Granix "Bocaditos rellenos" (1.592 sucursales por día) son almohaditas con TACC, pero más de 60% de sus sucursal-días
  son de una sola cadena: quedan afuera por la regla de cadena principal, no por el patrón.

## 6. Scripts

`docs/auditoria/scripts_nb06_2026-10/` (README): `r20` etiquetas por cadena, `r21`-`r22` descartados y los que pasan,
`r23` marcas dudosas en los maestros, `r24`-`r25` reglas de subtipo, `r26` correcciones sobre la canasta del 2026-10-23 y
`r27` comparación de canastas armadas con s10. Los cambios de `s9_seleccion.py` están comentados en el código.

## 7. La corrida de Colab con la canasta corregida y qué se puede mejorar (2026-10-26, noche)

**La corrida es idéntica a la simulación.**

- **Excel:** 35 hojas iguales a `simulacion_2026-10-26b/` (`s16`) y las 38 celda por celda contra `sim_v5` (`r13`).
- **Mapa:** igual salvo los identificadores de Folium (`r15`).
- **Caché:** 57 meses con los mismos datos (`r14`).
- **Salida impresa:** las mismas cifras.

Los 11 gráficos se ven bien. El usuario pidió revisar con los resultados si los productos y la metodología están bien
o se pueden mejorar.

### 7.1 Lo que dicen los resultados frente al objetivo

- **Cuánto más paga un celíaco**: en los últimos 12 meses, la canasta da +118%; la TPD de oct-2026, +115% a +116%.
  Por tipo (2022-2026): fideos +161%, galletitas dulces +108%, saladas +84%, rebozador +84%, almohaditas +26%.
- **Evolución**: todas las sucursales y panel balanceado.
  - 2022: +119% y +111%.
  - 2023: inflada del lado con TACC por los precios controlados; la TPD de todas da +113%.
  - 2024: +116% y +105%.
  - 2025, el mínimo: +100% y +97%.
  - 2026: +120% y +114%.
- **De un mes a otro** la brecha se mueve sobre todo por ajustes escalonados de pocas marcas con TACC. Criollitas subió
  75% entre nov-2022 y ene-2023 (de $48,6 a $85,1 por 100 g); la Saladix calabresa, de $114 a $219 en un mes. En esos
  meses la brecha de las saladas cae de ~+89% a ~+32% en el panel y vuelve a subir: es real, pero conviene leer
  promedios anuales o trimestrales.
- **Geografía**: regiones de +104% (Patagonia) a +121% (AMBA); provincias de +107% (Chubut) a +121% (CABA).
- **Cadenas**: solo dos empresas son confiables (Cencosud +116%, Carrefour +121%) y cinco cadenas (+114% a +120%). Con
  esta canasta, la comparación entre cadenas casi no se puede hacer.
- **Concentración**: sin relación (Spearman +0,12; terciles de HHI +119%, +123%, +122%).

### 7.2 Problemas que muestran los resultados

1. **TPD del panel en oct-2023: un artefacto.** El spaghetti del panel no tiene pares ese mes y se mueve con el penne y
   el tirabuzón, que caen por el salto de precio de Molinos (el tirabuzón pasa de +382% a +88%): queda en −38%. Los
   fideos del panel dan +38% y la canasta +114%.
   - **La alternativa**: mover el subtipo sin pares con el MISMO subtipo en todas las sucursales, donde tiene 1.000
     sucursales con pares. Da spaghetti +93%, fideos +101% y canasta +122%. También cambia las con chips movidas de
     2023: +58% a +92% en lugar de +120% a +172%, que salían de las demás galletitas dulces.
   - **Efecto**: los promedios anuales no cambian (±0,5 pp) y el desvío de la variación mensual de la canasta del panel
     baja de 8,6 a 7,9 pp (`r30`).
   - **En la descriptiva del panel**, la misma idea casi no cambia nada: ≤0,4 pp por año (`r31`).
2. **Con chips es frágil.** Tiene 100 a 220 sucursales con los dos lados por mes y 9 meses imputados en 2025-2026 (8 a
   12 sucursales). Par Nor coincide poco con las chips Smams. Pepitos 119 g, en cambio, está en 802 de las 813
   sucursales con chips Smams el 22/10 (Par Nor en 538, Toddy en 619; `r29`).
3. **Saladas: la TPD queda 4 a 24 pp debajo de la descriptiva** (2022: +73% contra +96%). El subtipo crackers mezcla
   dos niveles: las galletas de arroz Grandiet cuestan ~2 veces el con TACC y los crackers Smams ~2,8 veces, así que la
   mediana de cada sucursal depende de cuál tiene. Sin las galletas de arroz, los crackers dan +205% en lugar de +168%.
4. **Imputación de la descriptiva.** El penne de todas las sucursales queda imputado 16 meses por un cambio de escala:
   el sin TACC Matarazzo pasó de 300-550 a 1.200-1.300 sucursales por día. Se probaron variantes (límite de meses,
   referencia local, dato propio después; `r6`): mueven los años hasta 4 pp sin bajar el ruido, ninguna es claramente
   mejor. La TPD no imputa: es la referencia para 2023-2024.
5. **Subtipos chicos, con ruido.**
   - Obleas: el sin TACC (Santa María) está en 294 sucursales.
   - Pepas: el con TACC (Trío) está en 316 de las 1.227 sucursales con pepas Smams, y no hay otro con TACC continuo.
   - Rebozador: 110 a 320 sucursales por mes.

### 7.3 Recomendaciones, por prioridad

1. **TPD del panel**: mover el subtipo sin pares con el mismo subtipo en todas las sucursales y, si ahí tampoco hay
   dato, con los demás de su tipo, como hoy. Cambia solo la CELDA 8b: no relee el SEPA y Colab no relee.
2. **Con chips**: empalmar Pepitos 119 g (`7622201808662` → `7622201503260` → `7622201735906`) como comparador, en
   lugar de Par Nor o junto a él. Hay que extraer los dos códigos viejos de los zips, verificar los precios (s10) y
   releer.
3. **Obleas**: Opera 92 g, del tamaño de la Santa María de 90 g. Está en 272 de sus 294 sucursales y da obleas +107% en
   lugar de +126%.
4. **Crackers**: decidir las galletas de arroz. Sacarlas hace el subtipo homogéneo y acerca la TPD a la descriptiva;
   dejarlas mide la sustitución que hace el celíaco. Una puede ser la cifra principal y la otra, la de sensibilidad.
5. **Cadenas y concentración**: estimar la prima por empresa y su relación con el HHI con la hedónica (§3.9 de
   BRECHA_CELIACA: interacciones sin TACC × empresa y sin TACC × HHI). Usa los productos de cada cadena, sin completar
   con la brecha nacional, y responde las dos preguntas que la descriptiva no puede responder con dos empresas
   confiables.
6. **Lectura**: promedios anuales o trimestrales; 2023 con la TPD de todas las sucursales.

Scripts nuevos: `r29_cobertura_subtipos.py`, `r30_tpd_panel_alternativa.py` y `r31_panel_con_todas.py`.

## 8. Recomendaciones aplicadas (2026-10-26, noche)

El usuario pidió las tres primeras de §7.3. Detalle y resultados: `docs/BRECHA_CELIACA.md` §14.15.

- **TPD del panel.** El subtipo sin pares se mueve con el mismo subtipo en todas las sucursales. En oct-2023 el
  spaghetti pasa de −38% a +93%.
- **Pepitos 119 g** en con chips, en lugar de Par Nor: empalme de tres códigos, verificado con precios. La brecha de con
  chips pasa de +111% a +29% y las sucursales con los dos lados se triplican.
- **Obleas: la Opera de 92 g junto a la de 220 g.** Con la de 92 g sola, en 2023 casi no había sucursales con los dos
  lados (0 a 16) y la serie arrastraba +390% durante 17 meses. Con las dos, la cobertura es la de antes y, donde
  conviven, se corrige el tamaño.

Canasta: 67 productos (80 códigos). Esperados en `docs/brecha_celiaca/simulacion_2026-10-26c/`. La canasta de los
últimos 12 meses da +111% (antes +118%). Quedan para decidir las galletas de arroz y las vainillas (§4).
