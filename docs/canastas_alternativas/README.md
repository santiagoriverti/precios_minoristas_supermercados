# Canastas alternativas — composición y carga (v5)

Insumo del notebook **`07_evolucion_canastas_alternativas`**, que produce el informe semanal.

> **v5 (2026-09-07)** rehízo la composición desde cero. Antes de tocar nada, leé
> "[Por qué se rehizo](#por-qué-se-rehizo)": las canastas v4 se movían casi idénticas entre sí
> y la causa era la construcción, no el ruido de los datos.

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

Escalonamiento logrado: el precio unitario de Ejecutiva es **2,21× el de Popular** (mediana
entre necesidades; p25 1,51× — p75 2,57×).

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
   **Dejá un solo archivo** con ese patrón: nb07 toma el de nombre más alto.
5. Corré el notebook 07.

### Para cambiar la composición

**Ajuste puntual** (subir o bajar una cantidad, cambiar un producto): editá el diccionario
`CANTIDADES` de `cargar_canastas_v5.py`. Cada fila es
`'<EAN>': {'cantidad_01': q1, ..., 'cantidad_06': q6},  # rubro | descripción`.
Poné `0` para sacar un producto de una canasta.

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
