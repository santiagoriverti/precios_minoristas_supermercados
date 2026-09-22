# Auditoría de la corrida 2026-09-17 (nb07)

**Fecha**: 2026-09-22 · **Excel auditado**: `canastas_alternativas_2026-09-17.xlsx` (1.346 KB)
**Corrida**: 142 semanas (2024-01-04 → 2026-09-17, cierre jueves) · 85.246.279 filas sucursal×ítem×semana
· 288 EANs empaquetados + 59 tipos de frescos · 3.060 sucursales con dato · canasta `canasta_representativa_2026-09.xlsx`

PDF del informe: [`auditoria/auditoria_nb07_2026-09-22.pdf`](auditoria/auditoria_nb07_2026-09-22.pdf).
Script que reproduce estos chequeos sobre cualquier salida del nb07:
[`../notebooks/auditar_salida_nb07.py`](../notebooks/auditar_salida_nb07.py).

---

## Veredicto

La corrida es válida y la maquinaria hace lo que documenta. Aparecieron dos defectos —ya corregidos
en la v5.9, commit `6d7ed9c`— que inflaban el acumulado entre 1 y 2 puntos porcentuales y exageraban
la brecha contra el IPC. Quedan cinco temas abiertos, todos de composición de canasta o de criterio
de publicación; ninguno invalida el resultado.

| Indicador | Valor |
|---|---:|
| Diferencia máxima al replicar el índice desde el panel | 0,001 |
| Celdas del precio nacional replicadas dentro del 1% | 98,8% |
| Transiciones imposibles detectadas (de 46.324 celdas ítem-semana) | 24 |
| Alertas de salto >35% en 2026 | 0 |

---

## 1. Verificaciones independientes

Cada prueba reconstruye el resultado por un camino distinto al del notebook y lo compara con lo
publicado.

| Prueba | Método | Resultado |
|---|---|---|
| Índice de cada canasta | Recalculado desde `Panel_nacional` + recetas de `Detalle_*` | Coincide; diferencia máxima **0,001** |
| Precio nacional | Reconstruido desde el panel crudo por sucursal (85,2 M de filas) con `maestro_sucursales_completo.xlsx`, replicando mediana provincial ponderada por población, mínimo de 3 sucursales por provincia y winsorización K=2,5 | **98,8%** de las celdas dentro del 1%; mediana de la diferencia 0,001% |
| Grupo de control | Empaquetados y frescos encadenados por separado | Empaquetados +147,8% a +173,6%; frescos +154,3% a +157,4%. **Sin divergencia** (el síntoma de BUG-28 no volvió) |
| Frescos | Índice de **muestra fija por EAN** (solo EANs presentes al principio y al final, ≥10 sucursales) desde el caché `ean_*` | Mediana **+189%** contra **+181%** del publicado |
| Saltos semanales | Atribución ítem por ítem de cada semana con variación >4% | Todas en el 1.º trimestre de 2024, con varios ítems moviéndose a la vez |
| Composición | Suma de rubros contra el costo de la canasta | Exacta ($1.007.217 en Popular, sep-2026) |
| Fallback del estimador | Conteo de celdas donde ninguna provincia califica y se cae a mediana simple | 168 de 46.324 (**0,4%**), en 10 ítems |

### Apertura empaquetados / frescos

| Canasta | Empaquetados acum. | Frescos acum. | Empaquetados i.a. | Frescos i.a. |
|---|---:|---:|---:|---:|
| Popular | +147,8% | +157,4% | +22,7% | +31,1% |
| Media | +173,6% | +155,7% | +23,3% | +28,4% |
| Ejecutiva | +162,7% | +154,3% | +24,1% | +27,4% |
| Representativa | +148,8% | +154,5% | +22,7% | +29,3% |

Acumulado ene-24 → ago-26; interanual ago-25 → ago-26. IPC alimentos: +161,1% y +34,9%.

---

## 2. Las canastas contra el IPC

Comparación a **agosto de 2026**, el último mes con IPC publicado (el INDEC publica a mediados del
mes siguiente).

| Canasta | ene-24 → ago-26 | Interanual ago-26 | Costo sep-26 |
|---|---:|---:|---:|
| Popular | +139,1% | +28,3% | $1.007.217 |
| Media | +143,2% | +26,8% | $1.654.483 |
| Ejecutiva | +140,8% | +25,9% | $2.712.070 |
| Representativa | +132,2% | +26,5% | $1.522.238 |
| Femenina | +158,5% | +28,5% | $138.634 |
| **IPC alimentos** | **+161,1%** | **+34,9%** | — |
| **IPC general** | **+188,1%** | **+33,5%** | — |

Lectura: las canastas de supermercado corrieron por debajo del IPC general —cuyo motor fueron los
servicios y precios regulados— y algo por debajo del IPC de alimentos, que cubre todos los canales
de venta y no solo las cadenas. La brecha interanual (6 a 9 pp) es sistemática y conviene
contrastarla con los temas abiertos 3 y 4, que empujan en esa dirección.

**Septiembre de 2026 es medio mes**: entra con 2 semanas cerradas de 4 (la del 24 se descartó por
incompleta, último dato del SEPA 2026-09-21). Es la primera quincena, no el mes. Desde la v5.9 la
serie mensual lo marca en la columna `mes_parcial`.

---

## 3. Defectos corregidos (v5.9, commit `6d7ed9c`)

### BUG-36 — Precios viejos conviviendo con precios actuales

El mismo EAN se publica a la vez con su precio actual y con uno que la cadena nunca actualizó. La
mediana provincial cae en un régimen o en el otro según qué provincias llegan al mínimo de tres
sucursales esa semana. Como el índice es encadenado, el salto entra una vez y no sale nunca.

Verificado al nivel de sucursal: la Lavandina Ayudín cotizaba a $67 en una sucursal en enero de 2024
mientras el mercado estaba en $749; el Arroz Largo Fino a $122 contra ~$1.200 de mercado.

| Ítem | Semana | Factor | Antes → después |
|---|---|---:|---|
| Arroz Largo Fino Molinos Ala 1 Kg | 2024-03-07 | ×20,5 | $122,5 → $2.506,7 |
| Arroz Largo Fino Molinos Ala 500 Gr | 2024-03-21 | ×42,6 | $35,2 → $1.500,0 |
| Arroz Doble Carolina Molinos Ala 1 Kg | 4 veces, 2024-02 a 2024-08 | ×0,20 y ×5,9 | $700 ↔ ~$4.000 |
| Desodorante Rexona Extra Cool | 5 veces, 2024-09 a 2025-08 | ×0,06 y ×17,7 | $177,5 ↔ ~$3.000 |
| Lavandina Ayudín 1 Lt | 2024-06-13 | ×10,8 | $93,8 → $1.009,9 |
| Aceite de Oliva La Toscana 250 Ml | 2025-06-12 | ×7,6 | $1.441 → $10.920 |
| Vino Malbec Luigi Bosca 750 Cc | 2024-05 y 2024-07 | ×0,28 y ×3,06 | $14.069 ↔ $3.889 |
| Aire Acondicionado Philco Split | 3 veces, 2024-02 a 2024-03 | ×0,24 y ×3,84 | $172.000 ↔ ~$700.000 |
| Alfajor Triple Torta Terrabusi 70 Gr | 2024-01-11 | ×5,41 | $141,3 → $764,4 |
| Chocolate Oreo Milka 100 Gr | 2024-03-07 | ×3,75 | $1.205 → $4.513 |
| Mata Moscas Raid 370 Ml | 3 veces, 2024-05 a 2024-06 | ×0,29 y ×3,34 | $1.050 ↔ $3.509 |

**No es el fallback a mediana simple**: ese se usa en 168 celdas de 46.324 y explica una sola de las
24 transiciones (la Lavandina). El resto ocurre dentro del propio estimador ponderado.

**Fix**: `QUIEBRE_ITEM_K = 3.0` en la CELDA 1. Un ítem que se mueve ×3 o más en una semana sale del
eslabón de ESA semana y vuelve a entrar en la siguiente — el tratamiento estándar de un reemplazo de
producto. El umbral no toca variaciones legítimas: la mayor de toda la serie, en enero de 2024 con
inflación mensual de dos dígitos, fue ×1,6. Las transiciones quedan en la hoja **`Alertas_quiebre`**.

Efecto sobre el acumulado a ago-2026 (simulado sobre el panel de esta corrida):

| Canasta | Publicado | Con la corrección | Diferencia |
|---|---:|---:|---:|
| Popular | 239,1 | 234,1 | −5,0 |
| Ejecutiva | 240,8 | 236,0 | −4,8 |
| Media | 243,2 | 240,8 | −2,4 |
| Representativa | 232,2 | 231,2 | −1,0 |
| Femenina | 258,5 | 258,5 | sin cambio |

### La comparación con el IPC mezclaba meses

El reporte decía «2024-01→2026-09: canasta 245 vs IPC 288», pero la canasta llegaba a septiembre y el
IPC solo a agosto. Ahora se compara el último mes en común y el mes extra se informa aparte, con la
aclaración de que no se compara.

---

## 4. Las dos preguntas del informe

### La Femenina sube más porque es perfumería, no por un error

Sus catorce ítems subieron una mediana de **+213%** cada uno. El rubro Perfumería de las otras
canastas subió todavía más en el mismo período:

| Canasta | Perfumería, ene-24 → sep-26 |
|---|---:|
| Media | +419,8% |
| Popular | +312,0% |
| Ejecutiva | +273,1% |
| Representativa | +270,8% |
| **Femenina (canasta completa)** | **+217,3%** |

El cuidado personal corrió muy por encima de los alimentos. Detalle a tener presente: el **10,3%** de
su acumulado sale de una sola semana, el 2024-01-25, con tres ítems repreciando juntos tras la
devaluación (toallas femeninas ×1,58, protectores ×1,51, rasuradora ×2,10). Son variaciones
plausibles para ese mes, pero concentran mucho peso en un solo eslabón.

### La Tecnológica arranca tarde porque antes no hay datos

De sus catorce ítems, solo tres existen en el SEPA antes de 2025: el convector Liliana, el aire
Philco y el lavarropas Samsung. Los otros once aparecen después y son el **69,9%** del costo. El
índice arranca en 2025-06-12, cuando la canasta alcanza el 80% de cobertura. Además el aire alterna
×0,24 / ×3,84 en 2024.

**Recomendación**: publicarla como nivel de referencia —cuánto cuesta equipar un hogar— y no como
índice de inflación.

---

## 5. Temas abiertos

### 5.1 Durazno: serie rota

Publica **$16.607/kg** contra **$5.122** de la mediana cruda entre sucursales, con 274 sucursales,
109 semanas de 142 y la cadena partida en tres tramos. Acumulado +578% contra +123% del dato crudo.
Pesa menos del 0,9% de cualquier canasta, así que no contamina el total, pero **no es publicable a
nivel de ítem**. Misma familia, por cobertura o huecos: Espinaca (277 sucursales, 116 semanas),
Acelga (125 semanas, 11 semanas planas seguidas) y Palta (189 sucursales).

### 5.2 Trazabilidad: 36 ítems por debajo del 85%

| Canasta | Ítems | Peso en el costo | Principales |
|---|---:|---:|---|
| Tecnológica | 11 | 69,9% | Notebook HP 19,4%, Heladera Drean 12,3%, Cocina Drean 11,2% |
| Media | 7 | 10,6% | Pañal Huggies XXXG 3,5%, Dog Chow 1,7%, Shampoo Dove 1,5% |
| Ejecutiva | 8 | 8,0% | Skip líquido 2,4%, Cerveza Corona 1,9%, Pantene 1,6% |
| Popular | 7 | 3,9% | Prestobarba 0,8%, Formitas Sadia 0,7%, Bolsas Mortimer 0,6% |
| Representativa | 2 | 2,0% | Dog Chow 1,0%, **Jabón Dove Original 0,9%** (trazabilidad 81,8%) |
| Femenina | 0 | 0,0% | — |

El reemplazo de Femenina del 2026-09-08 funcionó: su hoja de alertas quedó vacía. Falta hacer lo
mismo con Media, Ejecutiva y el Dove Original de Representativa.

### 5.3 Pan francés: la palanca más grande de la Popular

Pesa **11,1%** de la Popular y **7,2%** de la Representativa. Su serie encadenada acumula **+138%**,
contra **+487%** del estimador ponderado y **+669%** de la mediana cruda. El anclaje a $6.200/kg
(`NIVEL_REFERENCIA_FRESCO`) fija el **nivel**, no la evolución: multiplica toda la serie por 0,80.

El encadenado por EAN está diseñado para no seguir la mezcla de EANs, y en un producto de balanza
—donde conviven EANs por kilo, por unidad y por bandeja— esa corrección es grande por construcción.
Aun así, +138% en 32 meses queda por debajo del IPC de alimentos (+161%) y muy por debajo del pan
del IPC. Conviene contrastar el nivel implícito de enero de 2024 ($2.608/kg según la serie) con una
referencia de mercado de esa fecha antes de publicar la Popular.

### 5.4 Los frescos encadenados corren por debajo de los estimadores crudos

Diferencia mediana de **−33,8 pp** contra el estimador ponderado y de **−21,7 pp** contra el índice
de muestra fija por EAN. Es el efecto buscado (sacar el cambio de mezcla), pero es grande y
heterogéneo: Merluza −428 pp, Pan francés −349 pp, Limón −321 pp; del otro lado Durazno +222 pp.
Solo 32 de los 59 tipos tienen 3 o más EANs supervivientes en 32 meses, así que ninguno de los dos
estimadores es preciso a nivel de tipo. A nivel agregado coinciden (+181% contra +189%).

### 5.5 Apertura provincial de Popular y Ejecutiva

Quedan con **3 provincias confiables** cada una (Buenos Aires, CABA y Entre Ríos), porque sus ítems
están en menos sucursales: 1.239 y 1.249 contra 2.196 de la Representativa y 1.586 de la Media.
Refuerza la regla ya vigente de no publicar la apertura provincial ni regional de Popular, Media ni
Tecnológica.

---

## 6. Cómo se hizo la auditoría

1. **Réplica del índice**: se reconstruyó `Panel_nacional` × recetas (`Detalle_*`) y se recalculó el
   encadenado de muestra apareada, comparando contra `Sem_*`.
2. **Réplica del precio nacional**: se descomprimió el caché `sem_<key>_v5` (32 parquets mensuales,
   81,7 MB) y se recalculó la mediana provincial ponderada por población con el maestro de
   sucursales, incluyendo el filtro de 3 sucursales por provincia, la winsorización y el fallback.
3. **Grupo de control**: se encadenaron por separado los ítems empaquetados y los frescos.
4. **Muestra fija por EAN**: desde el caché `ean_<key>_v5` se armó un Jevons ponderado por
   sucursales sobre los EANs presentes en la primera y en la última semana.
5. **Sensibilidad**: se recalculó el índice con topes de ×3 y ×1,5 por eslabón, y con Jevons de
   media recortada al 10%, para acotar cuánto del acumulado depende de casos extremos.
6. **Trazabilidad y cobertura**: se cruzó `Alertas_trazabilidad` con `Detalle_*` para pesar los
   ítems con huecos dentro del costo de cada canasta.

Nota metodológica: un Jevons con **mediana** de log-ratios NO sirve como control en este panel. Con
precios pegajosos la mediana semanal da exactamente 0 y el índice no acumula —es el mismo mecanismo
del BUG-28—. Hay que usar media (recortada, si se quiere robustez).

---

## 7. Próximos pasos

1. Volver a correr el nb07 con la v5.9 y revisar la hoja `Alertas_quiebre`.
2. Reemplazar en el constructor los ítems de baja trazabilidad de Media y Ejecutiva, y el Dove
   Original de Representativa.
3. Sacar Durazno de las tablas por ítem.
4. Validar el nivel del pan francés de enero de 2024 contra una referencia de mercado.
5. Decidir si la Tecnológica se publica como nivel en lugar de índice.
