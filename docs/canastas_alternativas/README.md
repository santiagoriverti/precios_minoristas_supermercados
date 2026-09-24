# Canastas alternativas — composición y carga (v5)

Insumo del notebook **`07_evolucion_canastas_alternativas`**, que produce el informe semanal.

> **v5 (2026-09-07)** rehízo la composición desde cero. Antes de tocar nada, leé
> "[Por qué se rehizo](#por-qué-se-rehizo)": las canastas v4 se movían casi idénticas entre sí
> y la causa era la construcción, no el ruido de los datos.
>
> **Ojo**: el 2026-09-08 se reemplazaron tres ítems de la canasta Femenina y se ancló el nivel del
> pan francés. Las tablas de este documento son las de v5; los cambios están en
> "[Cambios posteriores a v5](#cambios-posteriores-a-v5-2026-09-08)".

---

## Las 6 canastas

| Columna | Canasta | Necesidades | Criterio de producto | Idea |
|---|---|---:|---|---|
| `cantidad_01` | **Popular** | 58 | marca más barata con presencia nacional | Hogar de ingreso bajo |
| `cantidad_02` | **Media** | 76 | marca líder | Hogar de ingreso medio |
| `cantidad_03` | **Ejecutiva** | 76 | premium | Hogar de ingreso alto |
| `cantidad_04` | **Tecnológica** | 14 | producto modal | Bundle de durables (no es consumo mensual) |
| `cantidad_05` | **Representativa** | 76 | producto **modal** (mayor cobertura) | Familia tipo, comparable con INDEC |
| `cantidad_06` | **Femenina** | 14 | marca líder | Gestión menstrual, depilación, cuidado personal |

**287 EANs únicos** + **59 tipos de frescos** (los frescos van por regla de nombre en la
CELDA 1 del notebook, `TIPOS_FRESCOS`, porque el EAN de balanza cambia entre cadenas).

> **Vigente desde el 2026-09-24: 270 EANs.** El 2026-09-23 salieron pañales y toallitas de Media,
> Ejecutiva y Representativa (74 necesidades cada una); el 2026-09-24 se reemplazaron 24 ítems sin
> historia completa en el SEPA (ver "[Reemplazos de trazabilidad](#cambios-posteriores-a-v5-2026-09-24--reemplazos-de-trazabilidad)").
> El nb07 lee además 90 `EANS_CANDIDATOS` que no entran a ninguna canasta.

**Hogar de referencia: hogar tipo 2 del INDEC** — 2 adultos + 2 niños = **3,09 adultos
equivalentes**. Todas las cantidades están expresadas para ese hogar.

---

## Por qué se rehizo

Sobre la corrida real del 2026-08-27, medido en **gasto**:

| | comparte con Popular | Media | Ejecutiva | Representativa |
|---|---:|---:|---:|---:|
| **Popular** | — | 66,2% | 56,4% | 70,0% |
| **Media** | 41,1% | — | 82,6% | **100,0%** |
| **Ejecutiva** | 32,0% | 75,6% | — | 76,7% |
| **Representativa** | 48,7% | **98,1%** | 82,1% | — |

Media estaba **contenida** en Representativa: el 100% de su gasto iba a ítems que también
estaban en la otra. Y el 91% de los tipos frescos de Popular eran los mismos que los de
Ejecutiva. Eran la misma canasta a distinta escala, así que las correlaciones de 0,96 entre
las variaciones semanales no eran un hallazgo: eran una identidad contable.

**En v5 el solapamiento de EANs entre estratos quedó en 11,8% o menos** (Popular↔Ejecutiva:
5,3%). Donde dos estratos comparten un EAN es porque el mercado no ofrece un escalón superior
con cobertura nacional en esa necesidad, y queda registrado en el detalle.

---

## Las tres decisiones metodológicas

### 1. Necesidades, no productos

Cada canasta cubre el mismo conjunto de **necesidades** (`NEEDS` en el constructor), pero cada
estrato elige **su** versión: Popular la marca más barata con presencia nacional, Media la
líder, Ejecutiva la premium. El tier se decide por **percentil del precio por unidad
comparable** ($/kg, $/L o $/unidad de uso) dentro de la necesidad — nunca por el precio del
envase, porque eso haría que "el más barato" fuera siempre el paquete más chico.

Escalonamiento logrado: el precio unitario de Ejecutiva es **2,18× el de Popular** (mediana
entre necesidades).

**El tier es una ventana, no un punto.** Dentro de la ventana de percentil (`TIER_VENTANA`,
±12 puntos) todos los productos representan igual de bien al estrato, así que se elige el de
**mayor cobertura**. Sin esta regla, elegir por cercanía al percentil llenaba las canastas de
productos que existen en pocas cadenas y —como nb07 solo cotiza una sucursal que tenga ≥80% de
los ítems— la canasta Media terminaba cotizando en 264 sucursales de 3.092 y la Popular en 4 en
marzo de 2026. Con la ventana:

| Canasta | Sucursales (mediana) | Ítems con <1.200 sucursales |
|---|---:|---:|
| Popular | 1.676 → **2.265** | 10 → 4 |
| Media | 1.835 → **2.320** | 17 → 6 |
| Ejecutiva | 1.884 → **2.054** | 13 → 8 |

y el escalonamiento apenas se movió (2,21× → 2,18×).

Dos reglas de control, ambas nacidas de auditar las corridas del constructor:

- **Monotonicidad**: se exige Popular ≤ Media ≤ Ejecutiva en precio unitario. Sin esto, como
  cada canasta tiene su propio pool, el percentil devolvía un Ejecutiva más barato que el Media
  (pasó con atún y con bolsas de residuo). Hoy: **0 violaciones en 76 necesidades**.
- **Cobertura declarada**: si el producto elegido no cumple el piso de su canasta, queda
  marcado `confiable=False` en el detalle en vez de pasar en silencio (una versión intermedia
  metió un té con 98 sucursales en la canasta Media, cuyo piso son 800). Hoy: **0 de 314**.

### 2. Cantidades físicas, no unidades

v4 declaraba "2 unidades/mes" sin mirar el envase, así que una botella de 900 ml y una de
1,5 L contaban igual. v5 declara la cantidad **física** (kg / litros / unidades de uso) y el
loader calcula `cantidad = round(cantidad_física / presentación del EAN)`. Cambiar de envase
ya no cambia la canasta.

### 3. Ancladas a la CBA del INDEC

El núcleo alimentario replica la composición oficial de la canasta básica alimentaria,
escalada por 3,09 adultos equivalentes.

> Fuente: INDEC, *Canasta básica alimentaria y canasta básica total. Preguntas frecuentes*,
> Notas al pie N.º 3, junio 2020 — cuadro "Composición de la canasta para el adulto
> equivalente" (p. 13) y hogar de 4 integrantes = 3,09 adultos equivalentes (p. 9).

Esto corrigió dos faltantes grandes de v4:

| Componente | v4 (Representativa) | CBA hogar tipo 2 |
|---|---:|---:|
| Pan | 8,0 kg/mes | **20,9 kg/mes** |
| Papa | 8,0 kg/mes | **20,1 kg/mes** |

Los dos carbohidratos base estaban a un tercio de la referencia oficial.

En **frescos** el escalonamiento no puede ser por marca (se cotizan por tipo de balanza), así
que es por **corte y variedad**: Popular carga el gasto en los cortes de olla (falda, puchero,
osobuco, paleta, picada) y Ejecutiva en los caros (lomo, bife de chorizo, peceto, nalga).

### Unidades en que se declara la cantidad

| `u` | Significado | Cuándo usarla |
|---|---|---|
| `'kg'` | qty en kg o litros; se divide por el gramaje del envase | Alimentos, líquidos, cualquier cosa con peso o volumen |
| `'un'` | qty en unidades de uso; el envase **debe** declarar cuántas trae | Rollos de papel, pañales, toallas, bolsas, cepillos |
| `'pack'` | qty en paquetes; se ignora el conteo del envase | Cuando "un paquete" es la unidad natural de compra: algodón, tintura, esponja, crema depilatoria |

La distinción no es cosmética. En una corrida intermedia el algodón estaba declarado como 80
unidades, pero el producto elegido se mide en gramos y no declara unidades, así que el motor lo
tomó como **80 paquetes**: $111.470, el 43% de la canasta Femenina.

---

## Cambios posteriores a v5 (2026-09-08)

Dos ajustes que **no** están reflejados en las tablas de arriba y que hay que tener en cuenta al
retomar. Detalle completo en `docs/BUGS_Y_MEJORAS.md` y en `.claude/memory.md`.

### Femenina: tres ítems reemplazados por falta de trazabilidad

`Crema Corporal Nivea Body 400 Ml` pesaba 8,5% de la canasta y sólo tenía dato en 73 de 139 semanas:
estaba a $1.680 en 2024-01, desapareció 16 meses, reapareció a **$1.083** —por debajo de su precio
de 2024 después de 180% de inflación, un precio viejo que la cadena siguió publicando— y saltó a
$9.969 (+820%). Ese salto **era** el +9,3% del índice en 2025-10-16.

| Sale | Trazab. | Entra | qty |
|---|---:|---|---:|
| Crema Nivea Body 400 Ml | 50,0% | Crema Piel Extra Seca Villeneuve 250 Ml | **1,6** (mantiene 400 Ml/mes) |
| Rasuradora Simply Venus 2 Un | 78,1% | Rasuradora Femenina Prestobarba3 Gillette 2 Un | 1,0 |
| Jabón Tocador Original Dove 90 Gr | 84,4% | Jabón Tocador Antibacterial Dove 90 Gr | 4,0 |

Los 14 ítems quedan al 100% de trazabilidad y el costo pasa de $137.597 a $137.622 (**+0,02%**): la
sustitución no mueve el nivel. **Se aplica en `cantidad_06` del Excel de canasta** (el archivo
editado se le entregó al usuario para reemplazar el de `MyDrive/carga/output_canasta`).

### Pan francés: nivel anclado a una referencia de mercado

El pan francés publicaba $7.732/kg contra ~$6.200 de mercado. Con 18 kg/mes y 13,7% de la canasta
Popular, eso son 2,7 puntos de sobreestimación. **No se corrige con parámetros**: conviven dos
regímenes de alta cobertura (un EAN de balanza a $10.000 exactos en 981 sucursales y un par a $4.300
en 339) con la referencia en el medio, y barriendo `RATIO × K` el estimador salta entre
$3.190 / $4.300 / $6.760 / $10.000. La solución es `NIVEL_REFERENCIA_FRESCO`: fija el **nivel** de la
última semana con un precio verificado. No altera la inflación **del pan**, pero sí su peso en la
canasta y por lo tanto el índice (ver los cambios del 2026-09-22 más abajo). Si consiguen referencias
de mercado de otros frescos, se cargan ahí.

## Cambios posteriores a v5 (2026-09-22) — auditoría de la corrida v5.9

Detalle en `docs/AUDITORIA_2026-09-22_v59.md`.

### Nivel de frescos anclado al INDEC (nb07 v5.10)

El ancla del pan francés de arriba ($6.200) no tenía fuente documentada. Desde la v5.10, el nivel
del pan y de otros cuatro tipos cuyo universo de EANs mezcla productos distintos se ancla al **precio
promedio del INDEC para el GBA de agosto de 2026**:

| Tipo | Antes (ago-26) | INDEC GBA | Por qué |
|---|---:|---:|---|
| Pan francés | $6.171 | $4.910 (tipo flauta) | ancla anterior sin fuente |
| Pollo | $12.010 | $4.780 (entero) | entraba "Pata de Pollo Atm" de DIA y un chorizo de pollo |
| Carne picada | $17.810 | $10.613 (común) | picada envasada de DIA a $22-24 mil/kg |
| Merluza | $27.087 | $14.821 (filet fresco) | filet de DIA de 500 g a $31.800/kg |
| Limón | $7.485 | $1.425 | productos a $5-14 mil/kg (jugos) |

La **forma** de la serie de cada tipo no cambia (la da el SEPA). Cambia el **costo en pesos** (sep-26:
Popular $1.007.217 → $924.193, Media −4,5%, Representativa −5,2%) y también el **índice**, porque cambia
el peso de esos tipos: ene-24 → ago-26 Popular 234,1 → 231,1, Representativa 231,2 → 229,5, Media 240,8
→ 239,4, Ejecutiva 236,0 → 235,4 (corrida v5.10 del 2026-09-23).

### Decisiones de composición (resueltas)

- **Pañales en un hogar sin bebés — HECHO (2026-09-23, relectura v5.11).** El hogar de referencia es
  el hogar tipo 2 del INDEC (hijos de 6 y 8 años). Pañales y toallitas húmedas salieron de Media,
  Ejecutiva y Representativa (eran 4,9%, 6,8% y 5,8% del costo). Como subieron mucho menos que el resto
  (×1,2 a ×1,9 contra ×2,4), sacarlos **subió** el índice ene-24 → ago-26: Media +1,6, Ejecutiva +7,7,
  Representativa +5,4 puntos.
- **Rasuradora Femenina Prestobarba3** (reemplazo del 08-sep): ~515 sucursales por mes, debajo del
  piso de 700 de la Femenina → reemplazada el 2026-09-24 (abajo).
- **Trazabilidad** de Media, Ejecutiva y Representativa → reemplazos del 2026-09-24 (abajo).

## Cambios posteriores a v5 (2026-09-24) — reemplazos de trazabilidad

Con la corrida v5.11 (que leyó los `EANS_CANDIDATOS`) se reemplazaron 24 ítems. Lista aplicada:
[`reemplazos_2026-09-24.csv`](reemplazos_2026-09-24.csv), escrita con `aplicar_reemplazos.py --escribir`
(cargador de 282 a **270 EANs**; los 24 pares quedaron en `EAN_FORZADO` y el constructor los respeta).
El universo que lee el nb07 **no cambia** (los que salen quedan en `EANS_CANDIDATOS`): no relee el SEPA.

**Cómo se eligió.** La lógica del constructor (ventana de percentil de precio del estrato, la mayor
cobertura adentro, piso de monotonicidad Popular ≤ Media ≤ Ejecutiva, EAN distinto por estrato si se
puede; la Representativa, el de mayor cobertura), restringida a productos que el nb07 ya lee y con
**historia completa**: dato en ≥85% de los meses **y** ≥300 sucursales en al menos 28 de los 32 meses
cerrados. El segundo requisito se agregó porque "meses con dato" cuenta un mes aunque el producto esté
en una sola sucursal: Raid 370 tuvo **1** sucursal en ene-25 y jun-25 con 97% de "trazabilidad";
Scotch Brite, ~100 hasta mediados de 2025; Azucel, 207-414.

| Canasta | Sale | Entra | Nota |
|---|---|---|---|
| Popular | Polenta Molinos Ala 500 g | Harina de maíz Prestopronta 500 g | compartido con Ejecutiva y Representativa |
| Popular y Media | Azúcar Domino / Azucel 1 kg | Azúcar Ledesma 1 kg | los cuatro estratos comparten (producto homogéneo) |
| Popular | Puré de tomate Alco 520 g | Puré Arcor 520 g | Alco tenía huecos en el medio |
| Popular | Salchicha Viena 66 190 g | Swift Kids 190 g | compartido con los otros tres |
| Popular | Formitas de pollo Sadia 400 g | Formitas Lucchetti 350 g | |
| Popular | Bolsas Mortimer 45×55 | Asurin 45×60 rollo 30 | compartido con Representativa |
| Popular | Prestobarba 3 Carbón | Gillette Cuerpo descartable 2 un | compartido con Media |
| Media | Pepsi Black 2 L | Pepsi 2 L | compartido con Representativa |
| Media y Ejecutiva | Ala Más Blancos 600 g | Ala Lavado a Mano 800 g | solo 3 productos con cobertura en la necesidad |
| Media | Shampoo Dove Bond Intense 400 ml | Pantene Detox 400 ml | |
| Media | Jabón Dove Piel Sensible 90 g | Dove Exfoliante 90 g | desvío de la regla (ver abajo) |
| Media | Dog Chow adultos med/peq | Pedigree adulto carne, pollo y cerdo | el actual tenía 390 sucursales |
| Media y Ejecutiva | Raid 370 / Raid sin olor | Fuyi 360 cc | todos los Raid, <100 sucursales hasta fines de 2025 |
| Ejecutiva | Pan integral Fargo 400 g | Lactal Salvado 330 g | compartido con Media |
| Ejecutiva | Manteca Milkaut 100 g | La Paulina 100 g | |
| Ejecutiva | Cerveza Corona 330 ml | Patagonia lata 473 ml | |
| Ejecutiva | Esponja parrillera Go | Lana de acero Virulana 10 un | |
| Ejecutiva | Acondicionador Pantene Pro-V 250 ml | H&S Revitalizante 300 ml | |
| Representativa | Jabón Dove Original 90 g | Dove Antibacterial 90 g | desvío de la regla; el mismo de la Femenina |
| Representativa | Dog Chow adultos med/grandes | Dogui adultos 3 kg | desvío de la regla |
| Femenina | Prestobarba3 Femenina | Repuesto Venus 2 un | la actual, bajo el piso de 700 sucursales |

**Desvíos de la regla (decisión del usuario).** (1) Jabón: la regla daba a la Media el Dove
Antibacterial (empate de precio con el Exfoliante, gana por cobertura) y dejaba a la Representativa con
el Lux Rosas 360 g —otra marca, 55% más barato por kilo, sin datos hasta abr-24—; se invirtió para que
la Representativa tenga el de mayor cobertura. (2) Perro: la regla daba Dogui **cachorros** a la
Representativa; va Dogui **adultos** 3 kg, como el producto que reemplaza (el constructor no distingue
cachorro de adulto: la Ejecutiva tiene Dog Chow Cachorro). En la esponja la regla daba lana de acero y
se respetó: la Scotch Brite, más parecida al producto actual, estuvo en ~100 sucursales hasta 2025 y
saltó ×2,4 en una semana de feb-24.

**No se reemplazó: el Skip de la Ejecutiva** (Limpieza Activo 800 ml, 2,7% del costo). Toda la línea
"Skip Activo" apareció en jun-25; desde ahí no se corta y se movió como la canasta (×1,29 contra ×1,31).
El único candidato leído con historia que respeta la escalera es el Ala Ropa Fina de la Media (mitad de
precio: −1,3% del costo de la Ejecutiva, +1,6 puntos de índice). **Decisión del usuario: medir Woolite**
(y otros líquidos caros) en la próxima relectura. Duda abierta: cuesta 2,8× por litro lo que el Skip Bio
Enzimas del mismo tamaño; si es concentrado, 4 L/mes sobreestiman el consumo (mirar la etiqueta).

**Efecto esperado** (panel de la v5.11), índice ene-24 → ago-26: Popular 231,6 → 230,2 · Media 241,0 →
241,5 · Ejecutiva 242,8 → 243,6 · Representativa 234,9 → 235,7 · Femenina 258,5 → 260,0. Costos ±0,4%
salvo la Femenina (+2,6%); el interanual se mueve como mucho 0,2 puntos.

**Queda para la próxima relectura**: ítems con historia flaca que la trazabilidad no marcaba
(Ejecutiva 11,3% del costo: Skip, vino Luigi Bosca, fideos sin TACC Matarazzo, agua Villa del Sur,
aceite La Tosca, Oreo Milka; Media: desodorante aerosol, 27 meses con <300 sucursales). Necesitan
candidatos nuevos en `EANS_CANDIDATOS`, y eso relee el SEPA. El auditor los mide en el bloque 7b.

---

## Qué esperar — y qué no

El escalonamiento por marca separa bien los **niveles** de precio, pero **no** va a producir
tasas de inflación muy distintas entre estratos: dentro de una misma necesidad las marcas se
mueven casi en paralelo. Medido en agosto de 2026 sobre aceite de girasol 900 ml:

    Día $3.645  ·  Cañuelas $4.115  ·  Cocinero $4.339  ·  Natura $4.637

Un rango de 27% en nivel, con trayectorias muy parecidas.

La diferencia real de **inflación** entre estratos viene de la **composición entre rubros**
(efecto Engel), no de la marca. Eso ya se veía en v4 pese al anidamiento: Popular acumulaba
+186,5% contra Media +171,8% entre 2024-01 y 2026-08, porque Popular pesa más Carne (17,8%
contra 12,3%) y Verduras (12,7% contra 9,5%). v5 conserva y acentúa esa diferencia de
composición, que es la que tiene contenido económico.

---

## Umbrales de cobertura por canasta

| Canasta | Cadenas | Provincias | Sucursales |
|---|---:|---:|---:|
| Popular / Media / Ejecutiva / Representativa | ≥4 | ≥15 | ≥800 |
| Femenina | ≥4 | ≥15 | ≥700 |
| Tecnológica | ≥3 | ≥10 | ≥90 |
| **Piso absoluto** (si no, la necesidad se descarta) | ≥3 | ≥12 | ≥700 |

> **Corregido tras la corrida 2026-08-27.** La primera versión bajaba el umbral de Popular a
> ≥2 cadenas / ≥600 sucursales para poder incluir marca propia. Parecía razonable y **falló**:
> el percentil 10 aterriza sistemáticamente en la marca propia, y la marca propia vive en una
> sola cadena. Once de los 60 productos de Popular quedaron con ~550 sucursales, todos
> Carrefour, y como nb07 solo cotiza una sucursal que tenga ≥80% de los ítems de la canasta,
> **Popular pasó a cotizar en 85 sucursales de 3.070, todas de una cadena**. Un índice
> calculado sobre 85 sucursales de Carrefour no es un índice nacional.
>
> El estrato Popular sale ahora de la marca **más barata con presencia nacional** (Cañuelas,
> Casanto, Marolio, Dogui, Brahma, Tregar, Sedal). **El costo fue casi nulo**: el escalonamiento
> Ejecutiva/Popular pasó de 2,27× a 2,21×, y la cobertura mínima de un ítem subió de 546 a
> **802 sucursales**.

Ningún pick queda por debajo del umbral de su canasta (`confiable=False`: 0 de 314). Si una
necesidad no tiene candidato que llegue al piso absoluto, **se descarta para esa canasta** en
vez de incluir un ítem que solo cotiza en 400 sucursales.

---

## Flujo de trabajo

### Cada mes (cargar y correr)

1. Copiá **todo** `cargar_canastas_v5.py` y pegalo en una celda de Colab.
2. Ejecutá. Cuando pida el archivo, subí el Excel `canasta_representativa_*.xlsx` (sirve
   cualquier versión: el script **limpia y reescribe** `cantidad_01..06` completo).
3. Descargá el `*_con_canastas.xlsx`.
4. Subilo a Drive en `carga/output_canasta/` como `canasta_representativa_<periodo>.xlsx`.
   **Dejá un solo archivo** con ese patrón: nb07 toma el de nombre más alto (una copia de
   respaldo tiene que ir a OTRA carpeta: `..._backup.xlsx` en la misma le ganaría).
5. Corré el notebook 07. Si cambiaron los EANs y alguno no estaba en `EANS_CANDIDATOS`, relee el
   SEPA (~1h20m); si no, tarda minutos.

### Para cambiar la composición

**Ajuste de cantidad**: editá el diccionario `CANTIDADES` de `cargar_canastas_v5.py`. Cada fila es
`'<EAN>': {'cantidad_01': q1, ..., 'cantidad_06': q6},  # rubro | descripción`.
Poné `0` para sacar un producto de una canasta.

**Reemplazo puntual de un producto** (por ejemplo, uno sin trazabilidad): `aplicar_reemplazos.py`.
Toma un CSV `canasta,necesidad,ean_nuevo` (opcional `ean_actual`), busca el nuevo entre los
candidatos de esa necesidad con la misma función del constructor, calcula la cantidad (cantidad física
/ presentación, mismo redondeo), avisa si no cumple la cobertura de su canasta, si rompe la
monotonicidad Popular ≤ Media ≤ Ejecutiva, si otro estrato ya usa ese producto o si no está en
`EANS_CANDIDATOS` del nb07 (en ese caso el nb07 releería el SEPA). Por defecto simula; `--escribir`
actualiza el cargador (cantidades, conteo de EANs y un registro en el encabezado) y agrega el par a
`EAN_FORZADO` del constructor, para que una recalibración futura no lo deshaga.

```bash
python aplicar_reemplazos.py --excel ruta/al/canasta_representativa_YYYY-MM.xlsx --reemplazos reemplazos.csv
python aplicar_reemplazos.py --excel ... --reemplazos ... --escribir
```

Los nombres de canasta y necesidad son los de `Candidatos_trazabilidad` (y de `NEEDS` /
`NEEDS_FEMENINA`). **No** corras el constructor entero para un reemplazo: recalibra todas las canastas
sobre la cobertura del Excel que le pases y cambia muchos productos.

**Recalibración en serio** (cambiar productos por necesidad, cantidades físicas, el hogar de
referencia o los umbrales de cobertura): editá `construir_canastas_v5.py` y regeneralo:

```bash
python construir_canastas_v5.py --excel ruta/al/canasta_representativa_YYYY-MM.xlsx
```

Se corre **local**, no en Colab. Escribe tres archivos:

| Archivo | Qué es |
|---|---|
| `cargar_canastas_v5.py` | El loader de Colab (lo que se pega y ejecuta) |
| `canastas_v5_detalle.csv` | Una fila por (necesidad, canasta, EAN) con precio unitario, cobertura y si el pick es `confiable` |
| `frescos_v5_qty.txt` | Las tuplas `qty` para pegar en `TIPOS_FRESCOS` de `gen_nb07.py` |

Conviene recalibrar contra un Excel reciente: los productos entran y salen del SEPA, y el
constructor elige sobre la cobertura del período de referencia que le pases.

### Dónde tocar cada cosa

| Quiero cambiar… | Editar en `construir_canastas_v5.py` |
|---|---|
| Qué productos entran en una necesidad | `NEEDS` → `inc` / `exc` de esa necesidad |
| La unidad en que se declara la cantidad | `NEEDS` → `u`: `'kg'` (gramos/ml del envase), `'un'` (unidades de uso, el envase debe declararlas) o `'pack'` (paquetes, se ignora el conteo) |
| Cuánto se consume por mes | `NEEDS` → `qty` (tupla Popular, Media, Ejecutiva, Representativa) |
| Qué tan separados están los tiers | `TIER_PCT` |
| Los umbrales de cobertura | `COBERTURA` |
| El hogar de referencia | `ADULTOS_EQUIV` y `HOGAR_REF` |
| El reparto de carne / frutas / verduras entre tipos | `PESOS_FRESCOS` y `TOTALES_FRESCOS` |
| Papa, batata, pan francés, huevos | `FRESCOS_DIRECTOS` |

---

## Trazabilidad en el notebook

- **`Panel_nacional`** — precio nacional de cada ítem por semana. Es la materia prima de todas
  las series: si una canasta muestra un salto raro, se busca acá qué ítem lo causó.
- **`Alertas_precio_item`** *(nueva en v5.2)* — todo salto semanal del precio nacional de un
  ítem mayor a 35%. Es el tripwire: un cambio de régimen de precio no debería volver a pasar
  inadvertido. **Revisala antes de publicar.**
- **`Presencia_items`** — matriz ítem × mes con el % de semanas del mes en que el ítem tuvo
  precio real. Sirve para ver cuándo entró o salió un producto.
- **`Alertas_reemplazo`** — ítems sin dato en las últimas 8 semanas. Son los candidatos a
  reemplazar: buscá un sustituto y editá el loader (o recalibrá el constructor).
- **`Cobertura_emp`** — cobertura de cada ítem-canasta y si es comparable.
- **`Candidatos_trazabilidad`** *(v5.11)* — meses con dato, primer mes y cobertura actual de los
  `EANS_CANDIDATOS`: de acá salen los reemplazos de ítems con huecos.

**"Meses con dato" no alcanza.** Un mes cuenta aunque el producto esté en una sola sucursal, y con
tan pocas el precio nacional pega saltos que no son inflación. Antes de elegir un reemplazo, mirar
cuántas sucursales tuvo mes a mes: el auditor lo hace con el caché (bloque 7b, ≥300 sucursales).
De los 21 ítems con menos de 85% de meses del 2026-09-24, 19 eran **entradas tardías** (el producto
aparece en 2024-25 y no se corta: el encadenado lo incorpora sin salto, solo pierde su inflación
previa) y 2 tenían huecos en el medio.

Un ítem que falta pocas semanas **no rompe la serie**: el notebook arrastra su último precio
nacional conocido hasta 8 semanas y el índice es encadenado de muestra apareada, así que las
altas y bajas no generan saltos artificiales de nivel.

---

## Necesidades sin escalón real

En algunas necesidades el mercado no ofrece un tier superior con cobertura nacional suficiente
y dos estratos terminan compartiendo producto, o la necesidad se descarta para una canasta. Es
preferible a inventar un escalón que no existe; queda visible en `canastas_v5_detalle.csv` y en
la salida del constructor, que lista las necesidades que quedaron fuera de cada canasta.

---

## Archivos v4 (histórico)

`cargar_canastas_v4.py` y `canastas_v4_detalle.csv` se conservan como referencia de lo que se
corrió hasta la semana 2026-08-27. **No usar para corridas nuevas.**
