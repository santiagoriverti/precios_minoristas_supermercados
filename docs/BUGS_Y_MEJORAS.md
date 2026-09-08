# Bugs Pendientes y Mejoras

Última actualización: 2026-09-08 — nb07 v5.7.1: BUG-28, el eslabón del encadenado usaba la MEDIANA y con precios pegajosos daba exactamente cero

---

## 🔴 Bugs críticos (pendientes de fix)

> ✅ Todos los bugs críticos están resueltos. Ver sección "Resueltos" más abajo.

---

## 🟡 Defectos abiertos

### La desagregación regional de la Tecnológica es degenerada

En la corrida 2026-08-27 las **cinco regiones informan el mismo valor**, $5.853.138. La canasta
tiene 97 sucursales de **una sola cadena** (ChangoMas / Mi ChangoMas), así que el "índice
provincial controlando por cadena" no tiene sobre qué controlar y devuelve 100 en todas partes.

Es un índice de una cadena, no nacional. **No publicar la apertura por región ni por provincia
de la Tecnológica** hasta que haya al menos dos cadenas con cobertura de durables. Opciones:
(a) suprimir esas hojas para esa canasta; (b) reportarla solo a nivel nacional con una nota;
(c) buscar durables en otras cadenas bajando `COBERTURA['Tecnologica']`.

---

## 🟢 Cambios y fixes 2026-09

### 🟣 Femenina — reemplazo de los tres ítems sin trazabilidad (2026-09-08)

| Sale | Trazab. | Entra | Trazab. | qty |
|---|---:|---|---:|---|
| Crema Nivea Body 400 Ml | 50,0% | Crema Piel Extra Seca Villeneuve 250 Ml | 100% | 1,0 → **1,6** (mantiene 400 Ml/mes) |
| Rasuradora Simply Venus 2 Un | 78,1% | Rasuradora Femenina Prestobarba3 Gillette 2 Un | 100% | 1,0 |
| Jabón Tocador Original Dove 90 Gr | 84,4% | Jabón Tocador Antibacterial Dove 90 Gr | 100% | 4,0 |

Criterio: misma categoría y subcategoría, ≥95% de trazabilidad, ≥800 sucursales, y el precio más
cercano al del saliente. Se conservó marca y formato donde se pudo (Dove 90 Gr y Gillette 2 Un son
reemplazos directos) y se ajustó la cantidad donde cambió el tamaño, para que el consumo físico
mensual no se altere.

**Resultado**: los 14 ítems quedan al 100% de trazabilidad y el costo mensual pasa de **$137.597 a
$137.622 (+0,02%)** — la sustitución no mueve el nivel de la canasta.

Se aplica sobre `cantidad_06` de la hoja `Productos unicos` del Excel de canasta.

### 🟣 Anclaje de nivel de un fresco por referencia de mercado (2026-09-08)

`Pan francés` publicaba **$7.732/kg** contra **~$6.200** de mercado. Pesa 18 kg/mes y el **13,7% de
la canasta Popular**, así que el error de nivel la sobreestimaba **2,7%**.

**No se puede corregir con parámetros.** Su universo tiene dos regímenes de alta cobertura —un EAN
de balanza a **$10.000 exactos en 981 sucursales** y un par a $4.300 en 339— y la referencia real
cae entre los dos. Barriendo `RATIO_FRESCO` × K de régimen, el estimador salta entre $3.190,
$4.300, $6.760 y $10.000 con cambios mínimos: se pega al polo que quede dentro de la banda. El
mejor ajuste dejaba 15 EANs y era de filo de cuchillo. La media geométrica ponderada da $1.938,
peor todavía.

**Solución**: `NIVEL_REFERENCIA_FRESCO`, que fija el nivel de la última semana con un precio de
mercado verificado. El índice ya separa **forma** (la cadena de EANs apareados) de **nivel** (el
anclaje de una semana), así que esto **no altera la inflación medida** — sólo desplaza la serie por
un factor. Se aplica después de la banda de plausibilidad, que está pensada para el estimador
interno y no para un precio verificado a mano.

### 🟡 Femenina — un ítem con 16 meses de hueco explicaba casi toda su volatilidad (2026-09-08)

El usuario reportó que Femenina salta mucho más que el resto. Es cierto (desvío semanal 2,31%
contra 1,15% de Representativa) y **es un problema de composición, no de metodología**.

`Crema Corporal Milk Nutritiva Piel Extra Seca Nivea Body 400` pesa el **8,5%** de la canasta y
tiene dato en **73 de 139 semanas**. Estaba a **$1.680 en 2024-01**, desapareció **16 meses**,
reapareció a **$1.083** —por debajo de su precio de 2024, después de ~180% de inflación, o sea un
precio viejo que la cadena siguió publicando— y de ahí saltó a **$9.969 (+820% en una semana)**.
Ese salto es el +9,3% del índice en 2025-10-16. Desvío semanal propio del ítem: **97,4%**, contra
7,7% del segundo peor.

Otros dos con hueco en la misma canasta: `Rasuradora Simply Venus Gillette` (9 meses sin dato) y
`Jabón de Tocador Dove 90 Gr` (6 meses).

**Causa de fondo**: el constructor filtra por trazabilidad los ítems que elige —los de la
Representativa dan 99,7% de media y mínimo 84,4%— pero **Femenina y Tecnológica se cargan a mano
y no pasan por ese filtro**.

**Fix**: screen de trazabilidad sobre los ítems de **todas** las canastas (`TRAZA_MIN_PCT = 85%`),
que reporta por pantalla y en la hoja nueva `Alertas_trazabilidad` los ítems con huecos, con la
canasta a la que pertenecen. No los excluye automáticamente —cambiar la canasta es decisión del
constructor— pero deja de ser invisible.

### 🔴 BUG-28 — El encadenado se quedaba plano: la mediana es un estimador degenerado con precios pegajosos (2026-09-08) ✅ Resuelto

**Síntoma.** La primera corrida de v5.7 devolvió una inflación acumulada imposible: Popular
+54,2% (índice 154) y Representativa +71,5% (172) para 2024-01 → 2026-08, contra un IPC de 283.
La caída era proporcional al peso de frescos de cada canasta — Popular, la de más frescos, de 288
a 154; Ejecutiva, la de menos, de 254 a 194.

**Control que lo aisló.** Los empaquetados **no se encadenan por EAN**, así que sirven de grupo de
control: acumulado mediano **+161%**, en línea con el IPC alimentos (+157%). Los frescos
encadenados: **+58%**. El sesgo estaba entero en el encadenado.

**Causa.** El eslabón usaba la **mediana** de los log-ratios de los EANs apareados. Los precios de
supermercado son pegajosos: en una semana dada solo una **minoría** de los EANs cambia de precio.
Si repricea menos de la mitad, la mediana del ratio es **exactamente 1,0** y la cadena no acumula
nada. Evidencia en el panel: 93-100% de las semanas con variación exactamente cero en 14 tipos,
tramos de hasta 139 semanas idénticas, y **Pan francés con UN solo valor distinto en 139 semanas**
($7.732 constante). Variación semanal mediana de los frescos: +0,000%, contra +0,047% de los
empaquetados y los ~0,76%/semana que hacen falta para acumular +183%.

**Fix.** El eslabón pasa a ser la **media geométrica** de los log-ratios — el estimador de Jevons,
que captura el cambio promedio aunque solo se mueva una parte del panel. La robustez se conserva
por **clip absoluto** a `FRESCO_ESLABON_K` (2,5×) en vez de por recorte de cuantiles: la
distribución de log-ratios tiene una masa grande en cero más una cola de los que sí reprecian, y
un recorte por cuantiles puede borrar justamente la señal.

**Test de regresión** (`test_encadenado_frescos.py`, segundo bloque): 20 EANs donde solo 1 de cada
5 repricea por semana. Con la mediana la cadena queda plana; con la media geométrica recupera el
acumulado del panel con **0,00% de error**. El patrón de referencia es la media geométrica del
propio panel (Jevons), no `INFL**(n-1)`: por el escalonamiento hay un desfasaje real que el
índice debe reproducir.

**Lo que sí funcionó en esa corrida** (la referencia estable del filtro de régimen, de v5.7):
saltos de ítem >35% de 221 a **106 en toda la serie y 0 en el último trimestre** (venían 27);
**Matambre de $6.490 a $16.737** (venía congelado, con +12% acumulado en 32 meses); Roast beef de
$8.953 a $15.073. Esa parte se conserva.

### 🔴 BUG-27 — El precio de un fresco seguía a la mezcla de EANs, no a la inflación (2026-09-08) ✅ Resuelto

**Síntoma.** Tras v5.6 el salto de la semana **2026-05-07** bajó de +5,4% a +4,07% pero **no
desapareció**: seguía siendo el 5º más grande de la serie y el único fuera de ene-abr 2024
(donde la inflación real era ~4,6% semanal). Aportes: Carne +14,3% (2,04 pp), Cerdo +52,5%
(0,75 pp), Pollo +15,0% (0,64 pp).

**Causa.** El precio nacional de un tipo fresco era la **mediana sobre los EANs que casualmente
cotizaban ese mes**. Cuando cambia la mezcla, el tipo salta sin que haya inflación — y la
muestra apareada del índice **no lo ve**, porque la etiqueta del ítem (`Lomo`) es la misma en
las dos semanas. `Presencia_items` da 100% para los nueve tipos que saltan, en todos los meses:
el tipo nunca falta, lo que cambia es qué hay adentro.

**El `rk=2.0` de v5.6 empeoró la cola.** Los tres tipos más volátiles de 2026 fueron los tres con
`rk=2.0` (desvío medio 10,3% contra 8,5% de los tipos sin `rk`), porque estrechar la ventana
alrededor de una referencia contaminada **compromete más con el régimen equivocado**: Carré de
cerdo pasó de oscilar 15.951↔30.848 a quedar clavado en **$40.000 redondos y planos cuatro
semanas seguidas** — un EAN único dominando la mediana.

**Por qué ninguna banda alcanza.** Los dos regímenes de Lomo ($13.211 vs $36.378) y de Bife de
chorizo ($12.355 vs $31.349) distan ~2,5×, y una ventana tiene que ser ≥2× para tolerar
dispersión legítima: los dos caen adentro.

**Fix (v5.7), en tres partes:**

1. **Índice encadenado de muestra apareada POR EAN** para el precio nacional de cada tipo fresco
   — el mismo criterio que el notebook ya aplicaba un nivel más arriba, para la canasta. Cada EAN
   se compara **consigo mismo**, así que un cambio de mezcla no puede mover el índice. Se conserva
   el **nivel** del estimador anterior (mediana provincial ponderada por población) en la última
   semana válida y se reconstruye la historia hacia atrás. Anclaje **por tramo**: si un hueco
   supera `FRESCO_MAX_HUECO_PAR` no se encadena a través de él (publicaría de golpe toda la
   inflación del hueco) y el tramo nuevo se ancla por separado.
2. **Referencia estable en el filtro de régimen**: `ancla del mes × RATIO_FRESCO[tipo]` en vez de
   la mediana del mes, que es justamente la que se contamina. `RATIO_FRESCO` ya estaba calibrado.
3. **Segundo caché por EAN** (`ean_<key>_v5.parquet`, ~10k EANs × 139 semanas). Toda la
   metodología de frescos pasa a calcularse **después del caché**: de acá en más, iterarla cuesta
   minutos en vez de 1h42m de relectura del SEPA.

**Validación.** `notebooks/test_encadenado_frescos.py` ejecuta el **código real** extraído de
`gen_nb07.py` contra un panel sintético que reproduce el patrón medido (régimen barato de alta
cobertura que desaparece 10 semanas). Saltos de composición de +170% (Lomo), +149% (Bife) y
+235% (Carré) → **desaparecen**; el encadenado recupera el 1,00%/semana sintético con 0,0% de
error y el 1,47× acumulado exacto. Incluye un tipo escaso (Palta, 2 EANs) que destapó dos bugs
de la implementación: un tramo de una sola semana anclado al valor contaminado, y el reseteo de
nivel que rebaseaba el tramo anterior.

**Efecto colateral esperado y deseado:** los tipos con series congeladas — **Ajo, 82 semanas
consecutivas con el mismo valor**; **Matambre, +12% acumulado en 32 meses contra IPC +183%** —
deberían empezar a moverse, porque dejan de depender de qué EAN domina.

### ⚠️ Trampa corregida: la clave del caché no cubría todo lo que filtra en la lectura
`_cache_key` incluía `FRESCO_REGIMEN_K` pero **no** los `rk` por tipo (que filtran en la lectura
desde v5.6) ni `RATIO_FRESCO` (que desde v5.7 es la referencia del filtro). Tocar un `rk` o un
ratio no movía la clave y el notebook **reusaba en silencio un caché construido con los valores
viejos**: resultado incorrecto y sin aviso. Quedaba tapado porque el universo de EANs cambiaba
igual, pero era una trampa para la próxima sesión. Ahora ambos entran al hash.

### 🔴 BUG-26 — Pan francés explicaba el 43% de la volatilidad del índice (2026-09-07) ✅ Resuelto

Detectado auditando la corrida buena de v5.4. La banda global de plausibilidad (BUG-25) arregló
pan francés en agosto ($550 → $3.457/kg) pero **no la serie**.

**Qué era**: la serie de pan francés es **bimodal**. Un cluster plano de ~55 de las 139 semanas
entre $500 y $650 que **nunca inflaciona** (500, 510, 520, 608, 625 repetidos durante meses), y
una serie legítima que sí: ×2,66 entre 2024-01 y 2026-08, en línea con el ×2,86 del ancla.

La banda global no lo agarraba porque usa un piso común para todos los tipos: la basura de pan
está a ratio 0,20-0,59 contra el ancla y el piso quedaba en 0,38. **Sobrevivía por un 4%**, y
cada vez que el ancla se movía un poco el tipo entero cambiaba de régimen **en el cambio de
mes**:

```
2026-04-30  pan=  520  ancla=2.444  ratio=0.21
2026-05-28  pan=  520  ancla=2.292  ratio=0.23
2026-06-04  pan=4.576  ancla=2.208  ratio=2.07  <-- CAMBIO DE MES
```

Con 17,7 kg —la cantidad más grande de la canasta, anclada a los 6.750 g/AE de la CBA— ese solo
ítem tenía desvío semanal propio de **69,7%** y aportaba **5,05 de los 11,66 puntos** de
volatilidad del índice (43%). Los tres saltos que reportó el usuario eran suyos: −87,2% el
2025-05-08 (−17,3 pp en la canasta), +780% el 2026-06-04 (+13,4 pp), +87,3% el 2024-09-12.

**Fix — banda de plausibilidad POR TIPO** (`RATIO_FRESCO`), sobre el precio nacional y
**después del caché**, a propósito: cambiar la calibración no obliga a releer el histórico.
Cada tipo declara su precio esperado relativo al ancla, calibrado en el **percentil 75** del
ratio y no en la mediana —en un tipo contaminado la mediana cae *entre* los dos regímenes (pan:
mediana 1,14 con la basura en 0,2-0,6 y lo bueno en 1,8-2,8), así que el piso derivado de ella
no separa nada—. Banda **asimétrica** `[ratio/4, ratio*5]`: estricta abajo, donde está el
relleno; laxa arriba, donde están los picos estacionales genuinos de durazno, ciruela y uva.
Más `PISO_RATIO_OVERRIDE = {'Pan francés': 0.65}`, que cae en el hueco entre los dos modos.

Descarta **88 de 8.201 semanas-tipo (1,1%)**: pan francés 63, espinaca 12, limón 12, osobuco 1.
Sin daño colateral en los otros 55 tipos.

**Además: el arrastre ya no puentea una celda rechazada.** Si lo hiciera, al reaparecer un
precio válido el índice compararía contra uno viejo arrastrado y publicaría de golpe toda la
inflación acumulada del hueco. Un ítem rechazado queda fuera de la muestra apareada mientras
dure el rechazo y vuelve a entrar sin generar salto.

**Efecto medido sobre el panel real de la corrida**:

| | antes | después |
|---|---:|---:|
| desvío de la variación semanal | 3,17% | **2,17%** |
| semanas con \|var\|>4% | 13 | **7** |
| semanas con \|var\|>8% | 7 | **3** |
| salto máximo | 16,9% | **12,1%** |

2025-05-08 pasó de **−16,9% a +0,4%**; 2026-06-04 de **+12,5% a −0,9%**.

### 🟡 Corregidos de presentación (2026-09-07)

- El aviso "(índice desde AAAA-MM-DD: antes la cobertura era < 80%)" se imprimía **antes** de la
  línea de su propia canasta, así que se leía como si fuera de la canasta anterior. En la
  corrida 2026-08-27 el aviso era de **Tecnológica** y parecía de Ejecutiva. Ahora lleva el
  nombre de la canasta y va después.
- El rubro `'Limpieza '` (con espacio al final) aparecía como un rubro aparte en todas las
  tablas de composición. Se hace `.strip()`.


### 🔴 BUG-25 — El filtro de régimen eligió la moda mayoritaria, y era basura (2026-09-07) ✅ Resuelto

Detectado en la **corrida de verificación de v5.2**. El fix de BUG-24 funcionó donde se
esperaba (Papa $15.015 → **$3.338**, Ananá $11.213 → $3.805, Pepino $18.590 → $3.265, Durazno
$10.905 → $4.055, Ajo $10.119 → $3.146), pero **pan francés se fue a $550/kg** desde $4.981.

**Qué era**: el tipo está dominado por registros inválidos. Una cadena de ~980 sucursales
publica pan a **$5, $40 y $70 el kilo**:

| Descripción | Cadenas | Sucursales | Precio | $/kg |
|---|---:|---:|---:|---:|
| Pan Casero Blanco 1 Kg | 1 | 977 | $5,00 | **$5** |
| Pan Mignon 1 Kg | 1 | 977 | $40,00 | **$40** |
| Pan Francés Tira 1 Kg | 1 | 977 | $70,00 | **$70** |
| Mignones 300 Gr | 1 | 983 | $150,83 | **$503** |
| Pan Mignon 1 Kg | 1 | 983 | $10.000 | $10.000 |

Son ~4.000 registros sucursal-EAN inválidos contra unos cientos de precio real, así que la
mediana nacional del tipo —la referencia misma del filtro de régimen— aterriza en el régimen
equivocado. El filtro de régimen elige la moda **mayoritaria**, y acá la mayoría es basura.

**Fix — banda de plausibilidad anclada**, aplicada antes que todo lo demás. El umbral no puede
ser absoluto (envejecería con la inflación), así que se ancla en la propia corrida:

```
ANCLA_FRESCOS = ['Papa','Cebolla','Zapallo','Zanahoria','Tomate','Banana','Manzana','Naranja']
ancla = mediana del $/kg de esos tipos en el mes
se descarta lo que quede fuera de [ancla * 0.2 , ancla * 20]
```

Calibrado sobre 2026-08: ancla $3.165/kg → piso $633, techo $63.309. Verificado en los datos:
**ninguna mediana de tipo legítimo cae fuera** (la más barata Mandarina $1.327, la más cara
Queso rallar $39.735) y **los 10 únicos EANs del universo de frescos por debajo de $600/kg
quedan descartados** — todos erróneos ($5, $40, $70, $95, $129, $148 el kilo).

**Validación**: test end-to-end del pipeline completo sobre panel sintético con los dos casos
reales. Los 10 tipos recuperan su precio verdadero con **<2% de error**, incluido pan francés
($4.983 contra $5.000) pese a que la basura era mayoría, y Papa ($2.338 contra $2.300).

Complementos: se revirtió `gmin=1000` en Espinaca y Acelga (había dejado 13 y 10 EANs usables y
las volvió las series más ruidosas del panel: Espinaca +146%, −62%, +75% en semanas seguidas);
se excluye la hoja lavada en bolsa por nombre; pan francés excluye el sin-TACC premium; carne
picada excluye tartare (daba $20.514/kg, más cara que el asado).

### 🔴 El umbral relajado de Popular destruyó el índice (2026-09-07) ✅ Resuelto

Bajar el piso de Popular a ≥2 cadenas / ≥600 sucursales —para poder incluir marca propia—
parecía razonable en abstracto y **falló en la práctica**. El percentil 10 aterriza
sistemáticamente en la marca propia, y la marca propia vive en una sola cadena: 11 de los 60
productos de Popular quedaron con ~550 sucursales, todos Carrefour. Con `FRAC_PRODUCTOS_MIN`
exigiendo 80% de los ítems:

| Canasta | Ítems <800 sucursales | Sucursales que cotizan |
|---|---:|---:|
| Popular | 18 de 60 | **85** (contra 1.969 en v4) |
| Media | 8 de 78 | 234 |
| Ejecutiva | 23 de 78 | 163 |
| Representativa | 2 de 78 | 2.209 |

**Fix**: todas las canastas de consumo vuelven a ≥4 cadenas / ≥15 provincias / ≥800 sucursales,
con piso absoluto ≥3/≥12/≥700 por debajo del cual la necesidad **se descarta** en vez de meter
un ítem que cotiza en 400 sucursales. Popular sale ahora de la marca más barata con presencia
nacional (Cañuelas, Casanto, Marolio, Dogui, Brahma, Tregar, Sedal).

**El costo fue casi nulo**: el escalonamiento Ejecutiva/Popular pasó de 2,27× a **2,21×**,
mientras la cobertura mínima de un ítem subió de 546 a **802 sucursales** y no queda ningún pick
por debajo del umbral de su canasta.

### 🔴 Dos bugs de unidades en el constructor (2026-09-07) ✅ Resueltos

- **`Algodón Estrella Clásico 75 Gr` × 80 = $111.470**, el 43% de la canasta Femenina. La
  cantidad estaba en discos (80) pero el producto se mide en gramos y no declara unidades, así
  que el motor lo tomó como 80 **paquetes**. Se agregó la unidad `u='pack'` (cantidad en
  paquetes, se ignora el conteo del envase) para algodón, tintura, esponja, crema depilatoria y
  rollo de cocina; y `u='un'` ahora **exige** que el envase declare cuántas unidades trae.
  Femenina volvió de $260.865 a **$139.737**.
- **`Hamburguesas 4 Un 83 Gr` × 10 = $104.124** en Ejecutiva: el gramaje se leyó como 83 g
  cuando el paquete son 4×83 = 332. El formato "N Un M Gr" es ambiguo, así que el candidato se
  descarta (mismo criterio que nb06).

### 🔴 BUG-24 — El precio de los frescos saltaba entre dos regímenes (2026-09-07) ✅ Resuelto

**Síntoma reportado**: las canastas Popular/Media/Ejecutiva/Representativa daban un salto
grande después del 2026-04-30, caían abruptamente y volvían a saltar después del 2026-07-16.

**Qué era**: no era inflación. Descomponiendo por rubro, casi todo venía de **Verduras**
(+7,27 pp el 2026-05-21, −7,22 pp el 2026-07-02, +5,02 pp el 2026-07-30) y dentro de él de un
solo ítem, **Papa**, cuyo precio nacional era una onda cuadrada:

```
2026-04-30    2.193        2026-07-02     2.561
2026-05-14    2.318        2026-07-16     3.049
2026-05-21   14.714  x6,8  2026-07-23     5.448
2026-06-25   16.266        2026-07-30    14.855  x2,7
```

El nivel de agosto ($15.015/kg) ya lo delataba: la papa no vale 7 veces la cebolla ($2.688/kg).
Mismo patrón en Espinaca (×7,6), Ananá (×6,4), Pepino (×5,9), Choclo, Palta, Acelga.

**Causa raíz — tres capas encadenadas:**

1. **El "tipo" mezclaba bienes distintos.** Verificado sobre `Productos unicos`: espinaca
   suelta $2.171/kg contra espinaca lavada y sanitizada en bolsa de 300 gr $21.633/kg. La
   diferencia es real (son productos distintos), pero el pipeline los promediaba.

2. **El filtro de outliers se quedaba con el régimen caro.** La banda `[med/2,5 , med×2,5]`
   *dentro de la sucursal* sobre una distribución bimodal:
   con `{2.100, 15.000}` la mediana da 8.550, la banda queda `[3.420, 21.375]` y **descarta el
   precio correcto conservando el caro**. Con `{2.100, 2.100, 15.000}` funciona bien. Lo decide
   qué régimen tenga mayoría, y **con empate gana el caro** → sesgo sistemático al alza. Una
   variante que entra o sale da vuelta la sucursal entera.

3. **Errores de carga que sobrevivían.** `Papa Negra Sc 1 Kg` a **$95,00 en 983 sucursales**.
   Dentro del tipo Papa el rango iba de $95 a $7.990 (factor 84).
   Hueco adicional: los 27.287 EANs del maestro SEPA entran con `categoria = ''` y el filtro es
   `categoria in {...} OR categoria == ''` → **salteaban el filtro de categoría por completo**.

**Fix — `FRESCO_REGIMEN_K = 3.0`** (CELDA 1 + `_colapsar` en CELDA 7): antes del filtro
intra-sucursal se calcula la **referencia nacional del tipo para el mes completo** y se
descarta lo que quede fuera de `[ref/K, ref×K]`. Se estima sobre millones de observaciones (no
se da vuelta por una sucursal) y se recalcula cada mes (acompaña a la inflación sin umbrales
absolutos). Complementos: `gmin = 1000` en Papa, Lechuga, Acelga y Espinaca (no en Frutilla ni
Choclo, que se venden en bandeja y un mínimo global los borraría).

**Validación** con panel sintético de 1.900 sucursales que reproduce el modo de falla:

| | S1 | S2 | salto |
|---|---:|---:|---:|
| Código anterior | 2.352 | 15.016 | **+538,4%** |
| Con filtro de régimen | 2.352 | 2.318 | **−1,5%** |

El +538% sintético reproduce el +535% real observado. **Cambia la clave del caché: la primera
corrida vuelve a leer todo el histórico (~57 min).**

### 🟣 MEJORA — Tripwire `Alertas_precio_item` (2026-09-07)

Hoja nueva (`ALERTA_SALTO_ITEM = 0.35`): todo salto semanal del precio nacional de un ítem
mayor a 35%, con precio antes y después y en qué canastas está. Sale también en el "REPORTE
PARA CLAUDE". Se arregló la causa **y** se puso el detector: un cambio de régimen no debería
volver a descubrirse mirando el gráfico de la canasta y yendo hacia atrás. Probado con un panel
sintético que contiene el salto real de Papa.

### 🔴 Las canastas eran la misma canasta a distinta escala (2026-09-07) ✅ Resuelto en v5

**Síntoma reportado**: las canastas se movían "casi perfectamente correlacionadas como si
fueran la misma canasta".

**Qué era**: exactamente eso. Medido en **gasto** sobre la corrida 2026-08-27, Media compartía
el **100,0%** de su gasto con Representativa (estaba contenida), el 82,6% con Ejecutiva, y el
**91%** de los tipos frescos de Popular eran los mismos que los de Ejecutiva. Solo 21 de los 66
empaquetados de Popular no estaban también en Ejecutiva. Las correlaciones de 0,96 no eran un
hallazgo: eran una identidad contable.

**Fix**: rediseño completo en `docs/canastas_alternativas/construir_canastas_v5.py`
(necesidades con tier por marca, cantidades físicas, ancla CBA hogar tipo 2). Solapamiento de
EANs entre estratos: **≤6,4%**. Detalle en `METODOLOGIA.md` §10.9 y en el README de
`docs/canastas_alternativas/`.

**Faltantes de cantidad que salieron al anclar contra la CBA del INDEC**: pan 8 kg/mes contra
**20,9** de la CBA para hogar tipo 2, y papa 8 contra **20,1**. Los dos carbohidratos base
estaban a un tercio de la referencia oficial.

**Bugs del propio constructor, encontrados auditando su primera corrida** (los tres corregidos):
(a) caía en candidatos que no cumplían la cobertura sin avisar → metió un té con 98 sucursales
en la canasta Media, cuyo piso son 800; (b) el percentil, aplicado sobre pools distintos por
canasta, devolvía un Ejecutiva **más barato** que el Media (atún $26.292 contra $34.521, bolsas
de residuo) → se agregó monotonicidad explícita; (c) las cantidades de servilletas y algodón
estaban declaradas en paquetes pero el motor divide por unidades del pack.

### 🟢 Notebook 07 v5.1 — robustez del nacional (2026-09-04)

Diagnóstico sobre la **primera corrida real de v5**. El índice encadenado bajó los saltos de
±24% a ±12%, pero quedaban cuatro.

| Síntoma reportado | Causa real encontrada |
|---|---|
| Salto +12% el 2025-06-12 (y −4,8% el 2025-12-04) | **Ruido de provincias chicas**: Centro/Pampeana (1.423 suc) subió 1,6% y **Patagonia (38 suc) 113%**, volviendo la semana siguiente. El promedio ponderado le daba a Patagonia su peso poblacional completo |
| Tecnológica con trayectoria errática en 2024 | Tenía **4 de 14 ítems durante todo 2024** (el 14º entra en 2025-09). El índice existía pero no era informativo |
| Última semana con variación rara | **Semana incompleta**: el SEPA llegaba al 31/08 y la semana cerraba el 03/09 → 4 de 7 días, publicada como cerrada |
| Movimientos de Carne 2026-03/06 | **No es bug**: aparecen también en Centro/Pampeana con 1.700 sucursales → repricings reales |

**Fixes**: `MIN_SUC_PROV_ITEM=3` (sucursales mínimas por provincia-ítem-semana),
`PROV_OUTLIER_K=2.5` (winsorización de medianas provinciales), `COBERTURA_MIN_INDICE=0.80`
(el índice arranca cuando la canasta tiene ≥80% de sus ítems), descarte de semanas incompletas
vía `FECHA_MAX_DATOS`.

**Bug latente corregido**: la detección centavos/pesos se medía sobre todo el universo. Con
~10.500 frescos cotizando por kilo (hasta $39k), la mediana global quedaba pegada al umbral de
10.000 y un falso positivo habría **dividido un mes entero por 100** de forma silenciosa. Ahora
se mide solo sobre los EANs empaquetados.

**Frescos depurados** (contaminación verificada contra el maestro): Bondiola mezclaba bondiola
fresca con **curada** (fiambre, ~2× el precio) 144→101 EANs; Espinaca colaba ensaladas listas
27→21; Choclo un relleno para tarta 25→24; Pan francés "pan con chicharrón" 170→167.

**Nuevo diagnóstico**: hoja `Panel_nacional` (precio nacional de cada ítem por semana) y bloque
de fiabilidad regional en el reporte (n_suc y volatilidad por región).

**Validado**: 15/15 celdas end-to-end, con verificación explícita del descarte de la semana
incompleta y del filtro provincial.


### 🟢 Notebook 07 v5 — motor del informe semanal (2026-09-04)

Reescritura del motor para que la salida sea publicable semanalmente. **Diagnóstico sobre datos
reales** (Excel de la corrida 2026-W36), no sobre sospechas:

| Síntoma reportado | Causa real encontrada |
|---|---|
| Saltos en 2026-W07 (+24%) y caída en W31 (−21%) | **Rubro Carne**: cambio del set de variantes dentro de cada tipo. Todo lo demás plano esas semanas |
| Canastas "se despegan" al principio | **Entrada tardía de ítems**: sin precio aportaban $0 y al aparecer generaban un salto de nivel (Popular-Frescos +216% abr-2024; Heladera ago-2025) |
| Provincias/cadenas con valores raros | El "nacional" **era el precio de DIA** (964 de ~2.300 sucursales, precios uniformes): nacional, CABA, Buenos Aires y Centro/Pampeana daban el mismo número exacto |
| IPC se ve como una recta | **No es bug**: son los índices INDEC reales (4.261→12.076), lineales a esa escala |

**Fixes metodológicos**: índice encadenado de muestra apareada + nivel anclado; nacional
ponderado por población provincial; arrastre de 8 semanas; filtro de outliers intra-tipo en
frescos (K=2.5); índice provincial/regional controlando por cadena; `FRAC_PRODUCTOS_MIN` 0.5→0.8;
semana que cierra el jueves.

**Bugs corregidos**: (1) normalización de provincia sensible a mayúsculas/acentos — `San juan`
no matcheaba y caía en la región `Otras`; (2) `n_sucursales` contaba `id_sucursal` sin la terna
comercio/bandera, subcontando y afectando el umbral "confiable".

**Composición**: 196 EANs empaquetados (≥4 cadenas / ≥15 provincias / ≥800 sucursales) y 59 tipos
de frescos, con rubros nuevos Pollo (separado de Carne), Cerdo, Pescado, Fiambres y Quesos por kg
y Panadería. Loader unificado `docs/canastas_alternativas/cargar_canastas_v4.py` (`cantidad_01..06`),
que **reemplaza** a `cargar_en_productos_unicos.py` y `cargar_canasta_femenina.py` (eliminados).

**Trazabilidad nueva**: hojas `Presencia_items` (ítem × mes, % de semanas con dato real) y
`Alertas_reemplazo` (ítems sin dato hace >8 semanas, con las canastas afectadas).

**Validado**: 16/16 celdas end-to-end contra dataset SEPA sintético, verificando explícitamente
el descarte de outliers y la detección de altas. Loader: 196/196 EANs matchean en la hoja real.

### 🟢 `leer_maestro()` — fallback al Drive (2026-09-04)

Al pasar el repo a privado, `raw.githubusercontent.com` devolvió 404 y **fallaba la carga de
maestros en nb02/04/05/06/07** (además de romper los badges de Colab). `leer_maestro()` ahora
busca `./data` → **Drive (`SEPA_DIR`)** → caché → GitHub, y si no encuentra nada lanza un error
que dice exactamente qué archivo copiar y dónde.


### 🟢 Notebook 02 — Excel "datos_econometria" (series semanal+mensual por nivel) (2026-09-03)

**Archivo**: `gen_nb02.py` → CELDA 22 (motor) + CELDA 23 (export). Nuevo Excel
`datos_econometria_{MES}.xlsx` en `output_canasta` del Drive.

**Qué hace**: insumo para econometría de series de tiempo. Exporta, en formato **tidy/long**,
el costo de las 6 canastas (cantidad_01..06 de la hoja `Selección`) y el precio de **10 productos**
representativos (`PRODUCTOS_ECONOMETRIA`, editable), con frecuencia **SEMANAL (ISO)** y **MENSUAL**,
a nivel **nacional (ponderado por población) / provincia / cadena**, sobre la **historia completa**.
Hojas: `Diccionario`, `canastas_nacional/provincia/cadena`, `productos_nacional/provincia/cadena`.

**Cómo**: nb02 era mensual y solo tenía detalle geográfico del mes actual. El motor nuevo relee
los ZIPs **conservando el día**, agrega por (sucursal, ean, semana/mes), imputa faltantes con la
referencia nacional del período y agrega a los tres niveles. Caché por mes cerrado
(`econ_{hash}.parquet`), mes en curso fresco. **Fix**: semanas ISO de borde se asignan al mes del
jueves ISO (evita duplicar fragmentos entre archivos mensuales).

**Validado** con dataset sintético (imputación, provincia, nacional ponderado, producto, serie
semanal + variación %, export). **Pendiente**: el usuario reemplaza el default de 10 EAN por los
suyos (p.ej. Fernet Branca 750).

### 🟢 Notebook 07 — 4ª canasta Tecnológica + canastas ancladas a cobertura real (2026-09-03)

**Archivos**: `gen_nb07.py` → `07_evolucion_canastas_alternativas.ipynb` (regenerado, 16 celdas);
`docs/canastas_alternativas/` (dict + CSV paste-ready + detalle + loader de Colab + README).

**Qué cambió**:
- **4ª canasta `Tecnológica`** en `cantidad_04` (`CANASTA_COLS`). Es un bundle de durables
  (TV/notebook/celular/heladera/lavarropas/microondas/aire), `qty=1` c/u, **sin frescos**
  (`CANASTAS_SIN_FRESCOS`).
- **Frescos mapeados por NOMBRE** (`_FRESH_POS`), no por índice activo → robusto a la 4ª
  canasta. Fix del `Resumen` que usaba índice posicional (`IndexError` con 4 canastas).
- **Canastas ancladas a cobertura real**: al cruzar las canastas curadas contra el universo
  real de `Productos unicos`, la mayoría de los EAN estaban en **1 sola cadena** (no
  comparables). Se reconstruyeron eligiendo por cobertura desde la propia hoja, exigiendo
  **≥4 cadenas** → 90 EAN, casi todos cad=5 / 24 provincias / miles de sucursales.
- **Salida a carpeta nueva `output_canasta_alternativa`** (`RESULTS_DIR`): Excel de resultados
  + caché. La entrada (el Excel `canasta_representativa_*.xlsx`) sigue en `output_canasta`.
- Nueva **CELDA 15 "REPORTE PARA CLAUDE"**: costo/variación/acumulado/vs-IPC/composición por
  rubro + flags de cobertura, en texto plano para copiar y pasar.
- **Loader de Colab** (`docs/canastas_alternativas/cargar_en_productos_unicos.py`): script
  autónomo que carga `cantidad_01..04` en la hoja `Productos unicos` de un Excel subido.

**Validado**: 16 celdas compilan; test aislado de `_recipe` (Tecnológica=0 frescos; Ejecutiva
más carne). **Pendiente**: el usuario corre nb07 en Colab con datos reales y pasa el bloque
"REPORTE PARA CLAUDE" + `Cobertura_emp`/`Cobertura_frescos` para afinar cantidades.

**A vigilar**: la Tecnológica puede quedar rala si `FRAC_PRODUCTOS_MIN=0.5` deja pocas
sucursales con ≥50% de los durables — en ese caso se baja el umbral para ese estrato.

### 🟢 Notebook 07 — Canastas alternativas (Popular/Media/Ejecutiva) semanales + frescos (nuevo, 2026-09-01)

Herramienta nueva (`gen_nb07.py` → `07_evolucion_canastas_alternativas.ipynb`, 15 celdas). Análisis tipo nb02 pero **semanal**, con **3 canastas** socioeconómicas y **frescos** (carne/frutas/verduras/huevos), desagregado por rubro con drill-down y vs IPC. Ver README ("Canastas alternativas") y `METODOLOGIA.md` §8.

**Validado** end-to-end con dataset SEPA sintético (las 15 celdas compilan; frescos por tipo capturados y normalizados a $/kg y $/docena; rubro Carne desagregado; vs IPC; Excel de 27 hojas). Se corrigió `matplotlib.cm.get_cmap` → `plt.get_cmap` (removido en mpl 3.9, rompería en Colab). Generador con **raw strings** `r'''...'''` (ver `SEPA_TECNICO.md`).

**Mejoras/limitaciones abiertas (para afinar con datos reales)**:
- **Cantidades de frescos**: default razonable (canasta-básica, escala por estrato) y **editable** en `TIPOS_FRESCOS` (CELDA 1). Alinear mejor a las ponderaciones del IPC con la hoja `Cobertura_frescos` del primer run.
- **Reglas de frescos (`inc`/`exc`)**: curadas por nombre; pueden dejar entrar/salir variantes. La CELDA 13 imprime cobertura por tipo para refinar; revisar especialmente **Carne picada** (cobertura baja: los cortes al peso a veces no se publican con código).
- **Requiere `maestro_sepa_completo.csv.gz` en Drive** (lo genera el Script 03). Sin él, los frescos de nicho por cadena quedan sub-representados (el notebook avisa).
- **Mapas coropléticos/folium NO clonados** de nb02 (se pueden agregar después).
- **Un solo ítem empaquetado de baja comparabilidad** detectado al poblar: Postre Serenito (2 cadenas, 5 provincias) — candidato a reemplazo.

---

## 🟢 Cambios y fixes 2026-08

### ✅ Fix — Encabezado LaTeX de tablas de canasta con `\\` duplicado (2026-08-21)

**Archivo**: `notebooks/gen_nb02.py` → CELDA 13.

**Síntoma**: las `tabla_canasta_*.tex` salían con el encabezado (`\shortstack` y el terminador
de fila) en `\\\\` (doble), lo que genera filas/renglones vacíos y **rompe el render en
Overleaf**. Las tablas de producto (nb05) ya estaban bien. Era el bug histórico "CELDA 13 header
`\\` duplicado" que se arrastraba desde el raw-string original.

**Fix**: el header se reescribió como **f-string** (mismo patrón que nb05), produciendo `\\` simple.
Verificado en el `.tex` generado. Las filas de datos y la fila Promedio ya eran f-strings correctos.

### ✅ Feature — Doble análisis MEDIANA + PROMEDIO por duplicado (2026-08-21)

nb02 y nb05 generan **todo por duplicado**: análisis mediana (nombres base) y promedio
(sufijo `_prom`, con outliers fuera `[mediana/4, mediana×4]`). Además el precio por sucursal se
calcula sobre **todos los días del mes** (antes: solo el primer día). Detalle en `METODOLOGIA.md`
§4 ("Doble análisis") y en `.claude/memory.md`.

> ⚠️ **No es un bug, es un cambio de criterio**: los **niveles medianos** del cuadro de julio 2026
> en adelante **no son comparables 1:1** con informes viejos calculados con el método del primer día.

### 🟢 Notebook 06 — Brecha celíaca (nuevo)

Herramienta nueva (`gen_nb06.py`). Ver `docs/BRECHA_CELIACA.md`. Mejoras/limitaciones abiertas:
- **Cobertura de los representativos sin-TACC**: la plantilla se curó por marca mainstream, no por
  la métrica de cobertura del `canasta_representativa`. Revisar con la hoja `Detalle_producto` del
  primer run y reemplazar EANs de baja presencia.
- **Departamento**: falta un shapefile departamental (hoy: provincia + localidad).
- **Tipos ambiguos**: galletitas saladas (arroz vs trigo) y harina/premezcla (sustitución) — la
  decisión de incluirlos es del investigador (ver caveats en `BRECHA_CELIACA.md` §6.1).

---

## 🟠 Bug resuelto (2026-06-24)

### BUG-23: La serie histórica y los gráficos 1/2/3 no incluían el mes en curso

**Archivo**: `notebooks/gen_nb02.py` → CELDA 9 (y `02_evolucion_canasta_representativa.ipynb` regenerado).

**Síntoma**: con junio 2026 cargado, los cuadros provinciales/rankings/barrios mostraban junio (se calculan directo del archivo del mes), pero los **Gráficos 1 (índices), 2 (variaciones) y 3 (ranking canastas)** y los acumulados/variaciones del Excel terminaban en **mayo**. La serie histórica imprimía `2024-01 -> 2026-05`.

**Causa**: el caché de la serie (`hist_union_<hash>.parquet`) se identificaba **solo por la unión de EANs** de las canastas. Al agregar un mes nuevo, el set de EANs no cambia → mismo hash → se cargaba el caché viejo (construido hasta mayo) sin releer los meses nuevos. Agravante: el código original cacheaba **todos** los meses leídos, incluido el mes en curso; como ese mes crece día a día, quedaba "congelado" en la cantidad de días que tenía al cachearse.

**Fix**: CELDA 9 reescrita con dos niveles:
1. **Meses cerrados** (todos menos el último disponible) → se cachean y se leen incrementalmente: solo se procesan los meses que faltan en el caché.
2. **Mes en curso** (el último disponible) → se **relee SIEMPRE fresco** y nunca se cachea, así sus promedios usan los días efectivamente cargados (ej. junio con 23 días).

El caché viejo sigue siendo válido (se reutiliza para los meses cerrados), por lo que la primera corrida tras el fix es rápida: solo relee el mes en curso. Al cerrar el mes (cuando aparece el siguiente), pasa a "cerrado" y se incorpora al caché.

**Validado**: lógica de control testeada en 4 escenarios (primera corrida con mes nuevo, re-corrida mismo mes con más días, rollover de mes, sin caché). Solo cambió la CELDA 9 del notebook.

---

## 🔴 Bugs críticos (resueltos — 2026-06-01)

### EAN malformados en canastas ENGHo v2 → corregidos en v3

**Archivo**: `canastas_argentina_2026_v3.txt`
**Síntoma**: 4 EANs con menos de 13 dígitos no matcheaban en SEPA → precio imputado en lugar de real.
**Causa**: EANs truncados (faltaban ceros iniciales).
**Fix**: agregar ceros iniciales hasta 13 dígitos. La normalización `lstrip('0')` produce el mismo ean_norm → mismo producto, sin impacto en caché.

| EAN v2 | EAN v3 | Producto |
|--------|--------|---------|
| `78924468` | `0000078924468` | Dove Roll-On 50 Ml (Vulnerable) |
| `77903792` | `0000077903792` | Alfajor Terrabusi 70 Gr (Popular) |
| `70942003551` | `0070942003551` | Cepillo Gum Trolls 2 Un (Medio-Alto) |
| `99176369226` | `0099176369226` | Cepillo Colgate Triple 3+2 Un (Medio-Alto) |

---

## 🔴 Bugs críticos (resueltos — notebook 02, segunda ejecución 2026-05-29)

### BUG-19: `MIN_PRODUCTOS_PROPIOS >= N_CANASTA` → canasta_geo_filtros vacío ✅ Resuelto — commit e979ae2

**Archivo**: `notebooks/gen_nb02.py`, CELDA 3
**Síntoma**: Con una canasta de pocos productos (ej. 12 verduras frescas), el output de CELDA 8 mostraba `Provincias con datos: 0` y `Promedio (ponderado): nan`. Las celdas siguientes (14, 15, 16, 17) crasheaban por DataFrames vacíos.
**Causa**: `MIN_PRODUCTOS_PROPIOS = 15` (config en CELDA 1) era mayor que `N_CANASTA = 12`. Ninguna sucursal puede tener 15 productos de una canasta de 12 → todas se filtran → `canasta_geo_filtros` vacío.
**Fix aplicado** (CELDA 3, después de definir N_CANASTA):
```python
if MIN_PRODUCTOS_PROPIOS >= N_CANASTA:
    MIN_PRODUCTOS_PROPIOS = max(1, N_CANASTA // 2)
    print(f'AVISO: MIN_PRODUCTOS_PROPIOS ajustado a {MIN_PRODUCTOS_PROPIOS} '
          f'(canasta tiene solo {N_CANASTA} productos)')
```
**Comportamiento**: Para ICR (51 prod.): `15 >= 51` → False → no cambia. Para canasta pequeña (12 prod.): `15 >= 12` → True → ajusta a 6.
**Regla general**: Siempre verificar que `MIN_PRODUCTOS_PROPIOS < N_CANASTA`. El safeguard lo hace automáticamente.

---

### BUG-18: `IndexError` en CELDA 11/12 cuando la serie histórica está vacía ✅ Resuelto — commit 6289ab8

**Archivo**: `notebooks/gen_nb02.py`, CELDA 11 y 12
**Síntoma**: Al usar productos nuevos o con EANs PLU (códigos de balanza, empiezan con 27.../28...) que no están en el SEPA histórico, CELDA 11 crasheaba con `IndexError: single positional indexer is out-of-bounds` en `comparativa['ipc_general'].dropna().iloc[0]`. CELDA 12 crasheaba con similares errores al intentar graficar `df_g` vacío.
**Causa**: Los EANs con prefijo 27.../28... son PLU codes generados por balanzas en góndola — no tienen un código GS1 fijo y no aparecen en el SEPA histórico. `serie_nacional_valida` queda con 0 filas → `comparativa` vacío → `.iloc[0]` falla.
**Fix aplicado**:
- CELDA 11: guarda `_serie_vacia = len(serie_nacional_valida) == 0`. Si True → imprime aviso, crea DataFrames vacíos con las columnas correctas (`comparativa`, `df_g`). Si False → ejecuta el código original sin cambios.
- CELDA 12: envuelve toda la lógica de gráficos en `if len(df_g) == 0: print(aviso) / else: # código original`. Inicializa `out1 = out2 = None` para que CELDA 19 (export Excel) no crashee.
**Sin efecto sobre ICR**: `len(serie_nacional_valida) = 28` → `_serie_vacia = False` → código original, sin cambios.

---

### BUG-17: SyntaxError en gen_nb02.py — docstring triple-quote cierra el cell_code ✅ Resuelto — commit 7c3fe29

**Archivo**: `notebooks/gen_nb02.py`, CELDA 7
**Síntoma**: `python notebooks/gen_nb02.py` fallaba con `SyntaxError: invalid syntax. Perhaps you forgot a comma?` apuntando al inicio de CELDA 7.
**Causa**: La función `_geocodif()` usaba un docstring con triple comillas dobles `"""..."""`. Como el código de la celda está contenido dentro de un string `"""\..."""`, las comillas del docstring cerraban prematuramente el string externo, dejando el resto del código como sintaxis inválida.
**Fix aplicado**: cambiar el docstring a comentario de línea:
```python
# ANTES (cierra el string externo):
def _geocodif(lat, lon):
    """Primera provincia cuyo bbox contiene (lat, lon)."""

# DESPUÉS (sin conflicto):
def _geocodif(lat, lon):
    # Primera provincia cuyo bbox contiene (lat, lon)
```
**Regla general**: dentro de `cell_code("""\...""")`, NUNCA usar triple comillas dobles en el código interno (docstrings, strings multilínea). Usar comillas simples o comentarios de línea.

---

### BUG-16: Sucursales San Juan con coords en Jujuy — descartadas en lugar de reclasificadas ✅ Resuelto — commit 7c3fe29

**Archivo**: `notebooks/gen_nb02.py`, CELDA 7
**Síntoma**: La corrección inicial (BUG-15) eliminaba las sucursales con provincia inconsistente, perdiendo datos válidos. El usuario reportó que prefería conservarlas reclasificándolas.
**Causa**: Enfoque de filtrado en lugar de corrección: `canasta_geo = canasta_geo[~_mask_bad]` descarta filas.
**Fix aplicado**: reclasificación completa usando bounding boxes para las 24 provincias. Para cada sucursal con provincia inconsistente, busca en qué provincia caen sus coordenadas y la reasigna:
```python
_PROV_BBOX = {
    'CABA': (-34.72,-34.52,-58.54,-58.33),
    'Tucumán': (-28.0,-26.0,-66.5,-64.5),
    'Jujuy': (-24.5,-21.5,-67.5,-63.5),
    ... # 24 provincias
}
for _idx, _row in canasta_geo.iterrows():
    # Si coords fuera del bbox de la provincia etiquetada → buscar la correcta
    _nueva = _geocodif(_lat, _lon)
    if _nueva and _nueva != _p:
        canasta_geo.at[_idx, 'PROVINCIA_NORM'] = _nueva
```
**Sin pérdida de datos**: la sucursal se conserva con la provincia correcta según coordenadas.

---

### BUG-15: San Juan no aparece en mapa coroplético; filtro Folium muestra sucursales en ubicación incorrecta ✅ Resuelto — commit 2026-05-29

**Archivo**: `notebooks/gen_nb02.py`, CELDA 4 (`PROV_NORM`)
**Síntoma**: La provincia de San Juan aparecía en gris (sin datos) en el mapa coroplético. En el mapa Folium, al filtrar por "San Juan" se mostraban sucursales que geográficamente parecían estar en Jujuy.
**Causa**: El maestro de sucursales almacena la provincia de San Juan como `"San juan"` (con 'j' minúscula). El dict `PROV_NORM` tenía la entrada `'San Juan':'San Juan'` pero NO tenía `'San juan':'San Juan'`. Como la clave no existía, `.fillna(canasta_geo['PROVINCIA'])` conservaba el string original `"San juan"`. El GeoJSON usa `"San Juan"` (mayúscula), por lo que el match `can_prov.get('San Juan')` encontraba `None` → se pintaba gris.
**Fix aplicado**:
```python
# PROV_NORM — agregadas variantes de capitalización:
'San Juan':'San Juan','San juan':'San Juan','SAN JUAN':'San Juan',
```
**Regla general**: el maestro de sucursales puede tener inconsistencias de capitalización en los nombres de provincia. Para cada provincia con caracteres ambiguos, registrar todas las variantes conocidas en `PROV_NORM`.

---

## 🔴 Bugs críticos (resueltos — notebook 02)

### BUG-14: `ipc.xlsx` no encontrado — nombre real es `IPC.xlsx` (case-sensitive en Colab) ✅ Resuelto — commit 0acf852+1

**Archivo**: `notebooks/02_evolucion_canasta_representativa.ipynb`, celda de config (CELDA 2)
**Síntoma**: al ejecutar la celda de verificación de paths, el output mostraba `ipc.xlsx: NO ENCONTRADO` aunque el archivo estaba presente en la carpeta `carga/`.
**Causa**: el archivo se llama `IPC.xlsx` (I mayúscula). En Colab, el filesystem de Google Drive es **case-sensitive**: `IPC.xlsx` ≠ `ipc.xlsx`. El notebook buscaba `ipc.xlsx` en minúsculas.
**Contexto**: Windows no distingue mayúsculas/minúsculas en nombres de archivo, por lo que durante el desarrollo local el bug era invisible. Solo se manifiesta al ejecutar en Colab (Linux).
**Fix aplicado** (gen_nb02.py, celda de config):
```python
# Buscar IPC.xlsx / ipc.xlsx — case-insensitive fallback para Colab
_ipc_candidatos = [SEPA_DIR / n for n in ('IPC.xlsx', 'ipc.xlsx', 'IPC.XLSX')]
_ipc_encontrado = next((p for p in _ipc_candidatos if p.exists()), None)
IPC_PATH = _ipc_encontrado if _ipc_encontrado else SEPA_DIR / 'IPC.xlsx'
```
**Regla general**: en archivos de Drive accedidos desde Colab, siempre probar variantes de capitalización o documentar el nombre exacto del archivo. El nombre canónico es **`IPC.xlsx`** (mayúsculas).

---

## 🔴 Bugs críticos (resueltos — revisión Excel tercera ejecución)

### BUG-12: "Cabo Metálico" y otros implementos físicos en Limpieza del hogar ✅ Resuelto — commit 5f9f3c4

**Archivo**: `notebooks/01_exploracion_productos.ipynb`, cell-23 (`GRUPOS_CANASTA`)
**Síntoma**: el grupo Limpieza del hogar incluía "Cabo Metálico Glow 1 Un" y potencialmente escobas y plumeros — implementos físicos que no son productos de limpieza para seguimiento de precios.
**Causa**: `categoria='Accesorios de Limpieza'` agrupa tanto productos de limpieza (escobillas de inodoro) como implementos físicos (cabos, escobas, plumeros). El filtro sin `excluir_subcat` los toma todos.
**Evidencia**:
```
Cabo Metálico Glow 1 Un | subcategoria=Palas y Cabos | score=0.975
Escoba sin Cabo Virulana | subcategoria=Escobas y Escobillones | score=0.934
```
**Fix aplicado**:
```python
'excluir_subcat': ['Palas y Cabos', 'Escobas y Escobillones', 'Plumeros y Limpiavidrios']
```
**Resultado esperado**: Cabo Metálico reemplazado por un producto de limpieza real (lavandina, detergente, desinfectante).

---

### BUG-13: Tintura de cabello y protector térmico en Higiene y cuidado personal ✅ Resuelto — commit c61416e

**Archivo**: `notebooks/01_exploracion_productos.ipynb`, cell-23 (`GRUPOS_CANASTA`)
**Síntoma**: "Coloración en Crema N°3 Issue" (tintura) y "Protector Térmico sin Fijacion Spray Roby" (styling) ocupaban los puestos 3 y 4 del grupo, desplazando a desodorantes.
**Causa**: `subcategoria='Coloración'` y `subcategoria='Fijación'` tienen alta cobertura nacional (score ~0.988) pero son productos de beauty/styling, no higiene básica.
**Evidencia — grupo antes del fix**:
```
1. Jabón Plusbelle        (0.994)  ✅ higiene
2. Crema Dermaglós        (0.993)  ✅ cuidado facial
3. Protector Térmico Roby (0.989)  ❌ fijación de cabello
4. Tintura Issue          (0.988)  ❌ coloración
5. Alcohol Bialcohol      (0.987)  ✅ higiene
6. Crema Corporal St Ives (0.982)  ✅ cuidado corporal
```
**Fix aplicado**:
```python
'excluir_subcat': ['Coloración', 'Fijación']
```
**Resultado esperado — grupo tras el fix**:
```
1. Jabón Plusbelle           (0.994)  ✅
2. Crema Dermaglós           (0.993)  ✅
3. Alcohol Bialcohol         (0.987)  ✅
4. Crema Corporal St Ives    (0.982)  ✅
5. Desodorante Dove Mujer    (0.958)  ✅
6. Desodorante Dove Hombre   (0.954)  ✅
```

---

## 🔴 Bugs críticos (resueltos — revisión Excel segunda ejecución)

### BUG-10: `id_producto` exportado como entero — EANs con ceros iniciales se truncan ✅ Resuelto — commit f67de87

**Archivo**: `notebooks/01_exploracion_productos.ipynb`, cell-27 (export Excel)
**Síntoma**: EANs de menos de 13 dígitos (ej. código interno `78933354`) se exportan sin ceros iniciales. Al abrir el Excel, el EAN-13 debería ser `0000078933354`, pero se ve `78933354`. Afecta a ~93 productos en la hoja Candidatos.
**Causa**: `id_producto` se almacena como int64 en algún punto del pipeline. Al escribir en Excel mediante openpyxl, los enteros se formatean sin relleno.
**Fix aplicado** (cell-27, antes de construir el ExcelWriter):
```python
# Preservar EANs con ceros iniciales
canasta_export['id_producto']    = canasta_export['id_producto'].astype(str).str.zfill(13)
candidatos_export['id_producto'] = candidatos_export['id_producto'].astype(str).str.zfill(13)
```
**Impacto**: sin el fix, cualquier notebook consumidor que intente hacer merge por EAN-13 perdería 93 productos. El `.str.zfill(13)` no altera EANs de 13 dígitos (solo añade ceros iniciales a los más cortos).

---

### BUG-11: `'carne'` no es substring de `'Carnicería'` — productos de ese rubro no se incluían ✅ Resuelto — commit f67de87

**Archivo**: `notebooks/01_exploracion_productos.ipynb`, cell-23 (`GRUPOS_CANASTA`)
**Síntoma**: los 13 candidatos de `categoria='Carnicería'` (Leberwurst Paladini score=0.97, Salamín Bocatti score=0.93, etc.) nunca aparecían en el grupo Carnes y fiambres, aunque eran los de mayor score.
**Causa**: la kw `'carne'` busca como substring en el valor de `categoria`. El valor literal es `'Carnicería'` — cuyas primeras 5 letras son `'carni'`, no `'carne'`. Python `'carne' in 'Carnicería'` → `False`.
**Fix aplicado** (cell-23, kw del grupo Carnes y fiambres):
```python
# ANTES — no matcheaba 'Carnicería'
kw=['fiambre','embutido','carne','salchicha','pollo','atún','atun']

# DESPUÉS — añadido 'carnicería' y 'carniceria' explícitamente
kw=['fiambre','embutido','carne','carnicería','carniceria','salchicha','pollo','atún','atun']
```
**Impacto**: sin este fix, los embutidos curados de alta cobertura (Leberwurst, Salamín) quedan fuera de la canasta.

---

## 🔴 Bugs críticos (resueltos)

### BUG-6: Lácteos = 0 productos en la canasta ✅ Resuelto — commit 3c66c3c

**Archivo**: `notebooks/01_exploracion_productos.ipynb`, cell-23 (`GRUPOS_CANASTA`)
**Síntoma**: el grupo Lácteos produce 0 productos — aparece vacío en el Excel de salida.
**Causa**: las kw anteriores eran `['leche','yogur','queso','crema','manteca']`, que se buscan como substring en la columna `categoria` del maestro. Sin embargo, en el maestro SEPA, los productos lácteos del rubro Frescos tienen `categoria = 'Lácteos'` (string literal) — ninguna de las kw matcheaba ese valor.

**Evidencia (análisis post-ejecución, primera ejecución abril 2026)**:
```
Candidatos en Frescos: 521
Frescos con categoria='Lácteos':  279  ← estaban ahí, no se encontraban
Frescos con 'leche' en categoria:   0
Frescos con 'yogur' en categoria:   0
Frescos con 'queso' en categoria:   0
```

**Fix aplicado**:
```python
# En GRUPOS_CANASTA, grupo 'Lácteos':
# ANTES (no matcheaba nada en el maestro SEPA)
kw=['leche','yogur','queso','crema','manteca']

# DESPUÉS (coincide con el valor real de la columna categoria)
kw=['lácteos','lacteos']
rubros=['Frescos']
```

**Resultado verificado (segunda ejecución)**: 8 productos Lácteos correctos en la canasta.

---

### BUG-7: Azúcar, dulces y conservas contamina con carnes enlatadas ✅ Resuelto — commit 3c66c3c

**Archivo**: `notebooks/01_exploracion_productos.ipynb`, cell-23 (`GRUPOS_CANASTA`)
**Síntoma**: el grupo incluía Paté Bocatti de Panceta Ahumada y Picadillo de Carne Swift Picante.
**Causa**: ambos productos tienen `categoria='Conservas'` en el maestro — igual que los duraznos en almíbar, peras, etc. La kw `'conserva'` matcheaba todos sin distinción. Los `excluir_kw` operan sobre la misma columna `categoria` y no pueden distinguir dentro del mismo valor.

**Fix aplicado**: nuevo parámetro `excluir_subcat` en `seleccionar_grupo()` que filtra por la columna `subcategoria` (nivel más granular):
```python
excluir_subcat=['Patés y Picadillos', 'Conservas de Pescado']
```

**Resultado verificado (segunda ejecución)**: grupo Azúcar/dulces sin carnes enlatadas.

---

### BUG-8: Carnes y fiambres incluye quesos del rubro Fiambrería ✅ Resuelto — commit 3c66c3c

**Archivo**: `notebooks/01_exploracion_productos.ipynb`, cell-23 (`GRUPOS_CANASTA`)
**Síntoma**: Queso Untable Neufchafel, Queso Crema Casancrem, Queso Crema La Serenísima y otros quesos aparecían en el grupo Carnes y fiambres.
**Causa**: la kw `'fiambre'` matcheaba `categoria='Fiambrería'`, que en el maestro SEPA incluye tanto fiambres reales como quesos untables y cremas de queso. Los `excluir_kw` anteriores buscaban `'queso untable'` en la columna `categoria`, pero el valor literal es `'Fiambrería'` — no tenían efecto.

**Fix aplicado**: nuevo parámetro `excluir_subcat` en `seleccionar_grupo()`:
```python
excluir_subcat=['Quesos Untables', 'Quesos Semiduros', 'Quesos Rallados',
                'Quesos Blandos', 'Quesos Duros', 'Quesos Especiales', 'Dulces']
```

**Resultado verificado (segunda ejecución)**: los 6 productos Carnes son fiambres legítimos (Leberwurst, Salamín, Paleta, Salame, Pepperoni, Bondiola).

**Nota**: estos quesos tampoco aparecen en el grupo Lácteos (su `categoria='Fiambrería'`, no `'Lácteos'`). Son candidatos para un grupo Quesos propio en el futuro.

---

### BUG-9: Bebidas no alcohólicas incompletas (falta yerba, té, café) ✅ Resuelto — commit 3c66c3c

**Archivo**: `notebooks/01_exploracion_productos.ipynb`, cell-23 (`GRUPOS_CANASTA`)
**Síntoma**: el grupo Bebidas no alcohólicas solo contenía jugos y una bebida energizante. Faltaban yerba mate, té, café — productos básicos de la canasta argentina.
**Causa**: `rubros=['Bebidas']` únicamente. Las infusiones (yerba, té, café) viven en `rubro='Almacén'`, `categoria='Infusiones'` en el maestro SEPA.

**Fix aplicado**:
```python
'rubros': ['Bebidas', 'Almacén'],   # Almacén contiene Infusiones (yerba/té/café)
'kw': ['agua', 'gaseosa', 'jugo', 'saborizada', 'infusion', 'bebida herbal'],
# 'infusion' como substring matchea 'Infusiones'
```

**Resultado verificado (segunda ejecución)**: Yerba Liebig, Café Dolca, Té Inti Grey aparecen en el grupo.

---

## 🔴 Bugs críticos (resueltos)

### BUG-1: División /100 incorrecta en precios

**Archivo**: `notebooks/01_exploracion_productos.ipynb`, cell-7 (`cargar_sepa()`)
**Síntoma**: todos los precios del Excel de salida son 100x demasiado bajos. Aceite girasol aparece ~$57 en lugar de ~$5,750.
**Causa**: la función divide precios por 100 asumiendo centavos, pero los datos semestral 2026A (y probablemente 2025B+) ya vienen en pesos.
**Evidencia**: `analisis_SEPA_evolucion_AMBA.ipynb` procesa los mismos archivos y confirma FACTOR=1 ("Mediana de referencia: 1411.00 → Factor: 1").
**Fix**: reemplazar la división fija `/100` por autodetección de factor via producto de referencia (ver `SEPA_TECNICO.md`).
**Impacto en filtros**: NINGUNO — los filtros son por cobertura, no por precio umbral. La canasta seleccionada es correcta; solo los precios reportados están mal.

---

### BUG-2: `id_bandera` reportado como "cadena" cuando son grupos corporativos

**Archivo**: `notebooks/01_exploracion_productos.ipynb`, celdas de enriquecimiento y cobertura
**Síntoma**: el notebook reporta "5 cadenas activas" cuando en realidad son 16 cadenas comerciales.
**Causa**: `id_bandera` (valores 1-6) es el grupo corporativo, no el banner comercial. Cencosud opera Vea+Disco+Jumbo (3 id_bandera distintos dentro del mismo id_comercio=9).
**Fix**: añadir columna `nombre_cadena` usando el diccionario `(id_comercio, id_bandera)` disponible en `SEPA_TECNICO.md`.
**Impacto en score**: el `MIN_CADENAS` dinámico filtra por grupos corporativos (correcto para asegurar representatividad por grupo), pero el número reportado en el Excel es confuso.

---

## 🟡 Bugs menores (afectan la exactitud de la selección)

### BUG-3: Grupos de canasta con productos incorrectos

**Archivo**: `notebooks/01_exploracion_productos.ipynb`, celda de `GRUPOS_CANASTA`
**Síntoma**:
- **Lácteos** incluye: Mayonesa Hellmanns, Alfajor Chocoarroz, Azúcar Azucel
- **Carnes y fiambres** incluye: Dulce de Batata (×2), Queso Untable
**Causa**: keyword `'crema'` en Lácteos matchea "Mayonesa Receta Casera con Crema" (substring en nombre de categoría).
**Fix**: revisar `excluir_kw` de cada grupo problemático. Para Lácteos, excluir categorías que contengan 'mayonesa', 'alfajor', 'azúcar'. Para Carnes, revisar el rubro de los productos contaminantes en el maestro.

---

### BUG-4: "San juan" con j minúscula

**Archivo**: `notebooks/01_exploracion_productos.ipynb`, celda de normalización de provincias
**Síntoma**: `maestro_sucursales_completo.xlsx` tiene la provincia "San juan" con j minúscula.
**Causa**: dato sucio en el maestro; la normalización actual solo hace strip de "Provincia de " y reemplaza CABA.
**Fix**: añadir `.str.title()` después de las normalizaciones existentes, o un replace específico `'San juan' → 'San Juan'`.

---

## 🟢 Mejoras (opcionales, aumentan calidad)

### MEJORA-1: Parquet cache para sobrevivir crashes Colab

**Patrón de**: `analisis_precios_SEPA.ipynb`
**Descripción**: guardar el DataFrame después de cada paso costoso (carga SEPA, enriquecimiento, cobertura) como `.parquet` comprimido con snappy. Si el kernel crashea, retomar desde el último parquet en lugar de reprocesar todo.

```python
# Guardar
df.to_parquet(OUTPUT_DIR / 'df_enr.parquet', compression='snappy', index=False)

# Retomar (al inicio de la celda)
if (OUTPUT_DIR / 'df_enr.parquet').exists():
    df_enr = pd.read_parquet(OUTPUT_DIR / 'df_enr.parquet')
else:
    # ... procesar normalmente
```

---

### MEJORA-2: Deduplicación de variantes (concepto)

**Patrón de**: `analisis_precios_SEPA_2.ipynb`
**Descripción**: muchos productos son variantes de tamaño del mismo ítem (fideos 400g, fideos 500g, fideos 1kg). La función `extraer_concepto()` extrae las N palabras más significativas (sin marca ni packaging) para agrupar variantes y quedarse con la de mayor cobertura.

```python
TOKENS_A_REMOVER = {'g', 'kg', 'ml', 'l', 'lt', 'cc', 'un', 'unid',
                    'x', 'de', 'con', 'sin', 'por', 'para',
                    '100', '200', '250', '300', '400', '500', '1000', ...}

def extraer_concepto(desc_norm, marca, n_palabras=3):
    tokens = [t for t in desc_norm.split()
              if t not in TOKENS_A_REMOVER
              and t not in marca.lower().split()
              and not t.isdigit()]
    return ' '.join(tokens[:n_palabras])
```

Resultado esperado: ~10% reducción de la canasta de candidatos (4,713 → ~4,200 conceptos únicos).

---

### MEJORA-3: Nombres de cadenas en el output

**Patrón de**: `analisis_SEPA_evolucion_AMBA.ipynb`
**Descripción**: añadir una columna `nombre_cadena` al DataFrame enriquecido para que el output Excel muestre nombres legibles en lugar de `id_bandera`.
**Implementación**: ver diccionario `NOMBRES_CADENAS_COMPUESTAS` + `NOMBRES_CADENAS_SIMPLES` en `SEPA_TECNICO.md`.

---

### MEJORA-4: Canasta imputada para comparación provincial ✅ Implementado en notebook 02 — 2026-05-28

**Implementado en**: `notebooks/02_evolucion_canasta_representativa.ipynb`, CELDA 7 (`calcular_canasta_completa()`)
**Descripción**: para cada sucursal, si un producto de la canasta no tiene precio propio, se usa la mediana nacional de ese producto como imputación. Solo se reporta la sucursal si tiene al menos `MIN_PRODUCTOS_PROPIOS=15` productos propios.

```python
def calcular_canasta_completa(grupo):
    locales = dict(zip(grupo['ean_norm'], grupo['precio']))
    total = 0; propios = 0; detalle = []
    for ean_norm, (nombre, qty, cat) in CANASTA.items():
        if ean_norm in locales:
            precio = locales[ean_norm]; es_propio = True; propios += 1
        else:
            precio = precio_prom_nac.get(ean_norm, 0); es_propio = False
        subtotal = precio * qty
        total += subtotal
        detalle.append((nombre, cat, qty, precio, subtotal, es_propio))
    return pd.Series({'canasta_total': total, 'productos_propios': propios,
                      'detalle_productos': detalle})
```

---

### MEJORA-5: Visualización geográfica con Folium ✅ Implementado en notebook 02 — 2026-05-28

**Implementado en**: `notebooks/02_evolucion_canasta_representativa.ipynb`, CELDA 18
**Descripción**: mapa Folium interactivo con un `CircleMarker` por sucursal (radio proporcional al costo de canasta), coloreado por cadena comercial. FeatureGroups independientes por cadena + panel JS de filtros por provincia y tipo (hiper/super/express). Las coordenadas vienen del maestro de sucursales.

---

### MEJORA-6: Hoja "Selección" en Excel — fuente para notebook de canasta elegida ✅ Implementado — 2026-05-28

**Archivo**: `notebooks/01_exploracion_productos.ipynb`, cell-27 (export Excel)
**Descripción**: el Excel de salida ahora tiene una **tercera hoja "Selección"** que contiene todos los candidatos (~3,650 productos) ordenados por `rubro → categoría → score_cobertura` descendente, con:
- **Columna `cantidad`** (en amarillo destacado): vacía, para que el economista indique cuántas unidades incluir por producto
- **Auto-filter** habilitado para filtrar por rubro/categoría
- Header con freeze y estilo azul marino idéntico al del resto del Excel
- Formatos numéricos aplicados (score, precios, porcentajes)

**Estructura de `_COLS_SEL`**: `['periodo', 'cantidad'] + COLS_CANDIDATOS - 'periodo'`

**Propósito**: esta hoja es la **fuente de datos del próximo notebook** (`canasta_elegida_analisis.ipynb` — aún no creado), que leerá las cantidades completadas por el economista y calculará los totales de la canasta elegida, su comparación con el IPC, etc.

---

## 🔴 Bugs críticos (resueltos)

### BUG-5: OOM persistente — df_enr demasiado grande para Colab

**Archivo**: `notebooks/01_exploracion_productos.ipynb`, celda de enriquecimiento y subsiguientes
**Síntoma**: "Tu sesión falló porque se usó toda la RAM disponible" incluso después de los fixes de apply() y observed=True.
**Causa**: `df_enr` (producto × sucursal, ~50M filas × 20 columnas, ~10 GB) se mantenía vivo desde la celda de enriquecimiento hasta los heatmaps (7 celdas después). Los groupby sobre ese frame en cells 15, 16 y 18 multiplicaban el uso de RAM.
**Fix**: Rediseño arquitectónico anti-OOM:
- Agregar `df_suc_enr` inmediatamente a `df_cov` (producto × cadena × provincia, ~2M filas) y `df_price_stats` (producto, ~170K filas)
- `del df_suc_enr; gc.collect()` en cuanto termina la agregación → RAM pasa de ~10 GB a ~600 MB
- Todos los cálculos posteriores operan sobre los frames pequeños
**Impacto**: Soluciona el crash de RAM definitivamente sin cambiar los resultados.

---

## Estado de fixes

| Bug/Mejora | Estado | Prioridad |
|---|---|---|
| BUG-14: IPC.xlsx case-sensitive en Colab | ✅ Resuelto — 2026-05-28 | 🔴 Alta |
| BUG-13: Tintura/Protector en Higiene | ✅ Resuelto — commit c61416e | 🟡 Media |
| BUG-12: Cabo Metálico en Limpieza | ✅ Resuelto — commit 5f9f3c4 | 🟡 Media |
| BUG-11: 'carne' ≠ substring 'Carnicería' | ✅ Resuelto — commit f67de87 | 🟡 Media |
| BUG-10: id_producto int64 pierde ceros iniciales | ✅ Resuelto — commit f67de87 | 🔴 Alta |
| BUG-9: Bebidas incompletas (yerba/té/café) | ✅ Resuelto — commit 3c66c3c | 🟡 Media |
| BUG-8: Carnes incluye quesos fiambrería | ✅ Resuelto — commit 3c66c3c | 🟡 Media |
| BUG-7: Azúcar contamina con carnes lata | ✅ Resuelto — commit 3c66c3c | 🔴 Alta |
| BUG-6: Lácteos vacío (kw incorrectas) | ✅ Resuelto — commit 3c66c3c | 🔴 Alta |
| BUG-5: OOM df_enr ~10GB | ✅ Resuelto — commit fd5e014 | 🔴 Alta |
| BUG-4: "San juan" minúscula | ✅ Resuelto — commit e23bff5 | 🟢 Baja |
| BUG-3: Grupos contaminados (originales) | ✅ Resuelto — commit e23bff5 | 🟡 Media |
| BUG-2: Nombres cadenas | ✅ Resuelto — commit e23bff5 | 🟡 Media |
| BUG-1: Factor precio /100 | ✅ Resuelto — commit e23bff5 | 🔴 Alta |
| MEJORA-6: Hoja "Selección" con columna cantidad | ✅ Implementado — 2026-05-28 | 🔴 Alta |
| MEJORA-5: Mapa Folium interactivo | ✅ Implementado nb02 — 2026-05-28 | 🟡 Media |
| MEJORA-4: Canasta imputada por sucursal | ✅ Implementado nb02 — 2026-05-28 | 🟡 Media |
| MEJORA-3: Nombres cadenas output | ✅ Implementado — commit e23bff5 | 🟢 Baja |
| MEJORA-1: Parquet cache | ✅ Implementado — commit e23bff5 | 🟡 Media |
| MEJORA-2: Deduplicación de variantes | ⏳ Pendiente | 🟢 Baja |
