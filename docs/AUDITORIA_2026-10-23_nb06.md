# Revisión de la primera corrida del nb06 con la canasta fija — ene-2022 → oct-2026 (2026-10-23)

Corrida del usuario en Colab del nb06 con la canasta fija 2022-2026 (notebook del commit `678e9b9`, docs `b02871c`).
Insumos: la salida impresa, `output_brecha/brecha_celiaca_2026-10.xlsx` y `mapa_sucursales_brecha_102026.html` (no
están en el repo; se revisaron en una carpeta propia con `python -I`).

Resultado: **la corrida de Colab es idéntica a la simulación local** (29 hojas, diferencia máxima 1,4e-13): la canasta
y el estimador quedan validados en Colab, y los números clave —brecha por subtipo y por tipo, series nacionales
mensuales y anuales— están bien. Al revisar los resultados aparecieron **tres salidas que mezclaban composición** (las
comparaciones entre provincias, empresas y cadenas, el mapa por sucursal y la "concentración" por localidad): se
corrigieron sin releer el SEPA (**BUG-47**, §3). Queda **abierta una decisión de método**: la imputación sin límite de
la serie mensual (§4).

## 1. La corrida contra la simulación

```bash
python -I -X utf8 docs/auditoria/scripts_nb06_2026-10/s16_comparar_colab.py <Excel de Colab> docs/brecha_celiaca/simulacion_2026-10-23
```

**29 hojas iguales, 0 con diferencias** (diferencia máxima 1,4e-13; `Plausibilidad` vacía en las dos). Lo que pide
§14.9 de BRECHA_CELIACA:

| Punto | Colab | Esperado |
|---|---|---|
| Lectura | caché `brecha_v3_38349f0a` con los 57 meses cerrados + oct-26 leído; 58 meses (2022-01 → 2026-10); AVISO de ago-2024 parte 1 (se usa `COMPLETOb`, 15 días); 3.501.948 observaciones; 80/80 códigos con precio; 2.761 sucursales; ningún mes en centavos | igual |
| Vigencia | 57.419 observaciones fuera de la ventana de su código (16 códigos) | igual |
| Plausibilidad / `Control_EAN` | ninguno / 16 marcados (los saltos de oct-2023 y ene-2024 de los precios controlados y datos de un mes en una cadena; ninguno es un cambio de producto) | igual |
| Geografía | 12 sucursales reclasificadas de provincia; AMBA 1.973 sucursales | igual |
| Cobertura | con los dos lados alguna vez: fideos 2.483, dulces 2.406, saladas 2.515, rebozador 601, almohaditas 796; panel 4.975 sucursal × subtipo (1.318 sucursales); aviso de cobertura baja por el rebozador (2023-12, 2024-08/09/10) | igual |
| Ponderaciones | año base 2022; pesos 30,0 / 34,3 / 28,1 / 3,9 / 3,6% | igual (la impresión mostraba las cantidades con 2 decimales: 0,00 en almohaditas; corregido) |
| Tipo y año, panel | canasta 2022 +110,7%, 2023 +106,1%, 2024 +106,7%, 2025 +100,3%, 2026 +119,9%; tipos 2022-26: fideos +172%, dulces +108%, saladas +84%, rebozador +84%, almohaditas +26% | igual (§14.10) |
| Región, empresa, provincia | confiables: 4 regiones, 2 empresas, 4 provincias | igual, pero ver §3.1 |

El mapa por sucursal: 2.344 sucursales, 18 cadenas, JSON de 4,0 MB; snapshot por sucursal en los últimos 6 meses
(2026-10: 2.176; 2026-05: 127, que son 112 de la Cooperativa Obrera y 13 de Hipermercado Libertad, §2).

## 2. Lectura de los resultados

- **Lo clave está bien y es lo esperado** (§14.10 de BRECHA_CELIACA): fideos +172%, galletitas dulces +108%, saladas
  +84%, rebozador +84%, almohaditas +26% en 2022-2026; canasta (panel) entre +100% y +120% según el año. 2023 está
  inflado por los precios controlados del lado con TACC (salen en oct-2023 los fideos y en ene-2024 el resto: −53 pp en
  la canasta del panel en enero de 2024).
- **La serie de todas las sucursales se mueve con DIA**: DIA (~1.000 sucursales) entra y sale de los lados sin TACC de
  la canasta (fideos sin TACC ausentes mar-abr 2025 y sep-2025 → jul-2026; galletitas dulces sin TACC, mar-2025 →
  ago-2026; sus saladas sin TACC son de otro subtipo que las con TACC que vende, así que no forman par). Por eso
  los tipos de "todas" cambian de universo: fideos pasa de 1.210 a 2.168 sucursales en ago-2026 y su brecha baja
  16 pp; dulces pasa de 1.131 a 2.084 en sep-2026 (−7 pp). El panel balanceado no se mueve (es lo que dice la doc: la
  evolución, con el panel).
- **Fuente**: la Cooperativa Obrera deja de tener los productos sin TACC de la canasta desde abr-2025 (dulces, saladas,
  rebozador) y jun-2026 (fideos); Hipermercado Libertad pasa de 14 sucursales a 1 en jun-2026. Por eso aparecen en el
  mapa con datos de may-2026.
- **Los snacks (galletitas saborizadas) son el subtipo más volátil**: entre +0% y +83% según el mes, porque la mediana
  de cada lado en una sucursal depende de qué productos tiene ese mes (en nov-2022 el lado con TACC pierde los snacks
  baratos en muchas sucursales: +15% en el mes contra +4-7% de cada producto) y de los precios controlados de Rex,
  Kesitas y Saladix en 2022-2023 (saltos de +50-90% en un mes). Los crackers dan +333-362% en oct-dic 2023 (mismo
  motivo). No es un error; es la razón para pasar a la TPD/hedónica (§4).

## 3. BUG-47: lo que mezclaba composición (corregido, no relee)

### 3.1 Provincias, regiones, empresas y cadenas

La brecha de un tipo en un grupo era el promedio de **los subtipos que ese grupo tenía** (>= 10 sucursales) y la canasta
renormalizaba los pesos **entre los tipos presentes**. Los subtipos de un tipo tienen brechas muy distintas (saladas:
crackers +165%, snacks +28%; dulces: secas +75%, obleas +147%), así que un grupo sin snacks quedaba con la brecha de los
crackers sola. Además, "confiable" exigía los 5 tipos con >= 30 sucursales: el rebozador (3,9% del peso) dejaba afuera a
casi todas las provincias.

**Ahora**: la misma canasta de 12 subtipos en todos los grupos; el subtipo con < 10 sucursales en el grupo toma la
brecha **nacional** del mismo período (como una celda que falta en un índice de precios); `peso_imputado_pct` dice qué
parte del peso no se midió en el grupo y `subtipos_con_brecha_nacional` cuáles; confiable = <= 25% del peso imputado y
>= 30 sucursales. Últimos 12 meses (nov-2025 → oct-2026), nacional +122,7%:

| Grupo | Antes (tipos presentes) | Ahora (misma canasta) | Peso imputado | Sucursales | Confiable |
|---|---|---|---|---|---|
| Carrefour (empresa) | +118,7% | +124,0% | 6,9% (pepas) | 562 | sí (antes sí) |
| Cencosud (empresa) | +124,8% | +125,1% | 6,9% (con chips) | 267 | sí (antes sí) |
| ChangoMas (empresa) | +139,1% | +140,4% | 17,6% | 89 | **sí** (antes no) |
| Coto (empresa) | +141,7% | +127,0% | 41,7% (sin snacks, obleas, pepas, tirabuzón, rebozador) | 120 | no |
| La Anónima (empresa) | +131,8% | +110,5% | 38,5% (sin snacks, chips, obleas, secas, rebozador) | 169 | no |
| DIA (empresa) | +78,2% | +115,8% | 83,1% (solo spaghetti y rellenas) | 982 | no |
| Carrefour Express (cadena) | +140,2% | +122,5% | 35,3% | 397 | no |

Confiables ahora: **6 regiones** (Patagonia +107,4%, Pampeana +120,1%, Noreste +124,8%, Cuyo +124,9%, AMBA +125,6%,
Noroeste +126,7%), **8 provincias** (Chubut +110,9% … Córdoba +127,0%), **3 empresas** (Carrefour, Cencosud, ChangoMas)
y **7 cadenas** (Carrefour Market +119,5%, Carrefour +121,1%, Vea +124,3%, Jumbo +126,0%, Disco +128,6%, ChangoMas
+141,1%, HiperChangomas +141,9%). Las diferencias entre cadenas (~20 pp) son mayores que entre regiones con muchas
sucursales (AMBA, Pampeana, Cuyo, Noroeste: 120-127%). Las regiones y empresas por año usan la nacional del mismo año.
Verificado contra un cálculo independiente (`r8_canasta_comparable_grupos.py`: diferencia máxima 1e-13 en las cuatro
tablas).

### 3.2 Mapa por sucursal y hoja `Brecha_sucursal`

La canasta de la sucursal (cantidades ENGHo / precio base) sumaba solo los tipos de esa sucursal. En oct-2026:

| Tipos en la sucursal | Sucursales | Canasta antes (mediana) | Canasta comparable (mediana) | Peso medido en la sucursal (mediana) |
|---|---|---|---|---|
| 1 | 60 | +149,5% | +123,0% | 20% |
| 2 (DIA: fideos y dulces) | 1.003 | +77,4% | +118,8% | 17% |
| 3 (Carrefour Express: fideos y galletitas) | 518 | +134,4% | +121,6% | 65% |
| 4 | 377 | +117,3% | +127,1% | 62% |
| 5 | 218 | +120,6% | +133,2% | 93% |

El color del mapa medía cuántos tipos tiene cada sucursal. **Ahora** el color y `brecha_canasta` son la canasta
comparable: la misma canasta de subtipos, con lo que la sucursal no tiene completado con la brecha nacional del mes;
`peso_propio_pct` dice qué parte se midió ahí (DIA 17%, Carrefour 65%, Cencosud 89%). Por empresa, la mediana de oct-26
va de +118,8% (DIA, casi toda nacional) y +119,2% (La Anónima) a +131,1% (Cencosud) y +143,9% (ChangoMas). La anterior
queda como `brecha_tipos_presentes`. El popup lo explica y el tooltip muestra la parte medida. Verificado contra un
cálculo independiente en los 123.906 sucursal-mes (`r9_canasta_comparable_sucursal.py`: diferencia máxima 1e-13).

### 3.3 Concentración

La hoja agrupaba por el texto de `sucursales_localidad`, que DIA carga con el **nombre de la provincia**:

| "Localidad" | Sucursales | Brecha | Qué es |
|---|---|---|---|
| CAPITAL FEDERAL | 430 | +77,4% | DIA en CABA |
| BUENOS AIRES | 428 | +78,3% | DIA en la provincia de Buenos Aires |
| Ciudad Autónoma de Buenos Aires | 326 | +134,5% | Carrefour |
| ENTRE RIOS | 66 | +81,2% | DIA |
| CIUDAD AUTONOMA BUENOS AIRES | 43 | +119,6% | Cencosud y ChangoMas |
| CORDOBA / Córdoba | 35 / 31 | +113,9% / +138,3% | la misma ciudad, dos grafías |

y medía la "concentración" con el nº de sucursales de la localidad: la correlación −0,26 del gráfico salía de DIA (2
tipos, +77%). **Ahora**: mercado local = **departamento** de Georef (datos.gob.ar, por coordenadas; la caché que arma el
nb09 en el Drive, `output_trazabilidad/_cache_nb09/georef_sucursales.parquet`; si falta, la CELDA 7 consulta la API);
concentración = **HHI de empresas** (cuota = sucursales: el SEPA no tiene ventas); brecha = canasta comparable de las
sucursales con >= 50% del peso medido en ellas. Resultado: 62 departamentos con >= 5 sucursales con brecha propia;
**Spearman por sucursal −0,11** (1.105 sucursales); por tercil de HHI (0,20 / 0,30 / 0,36) la brecha mediana es
+125,9% / +125,0% / +125,1%. **No hay relación a la vista**; modelarla (controlando cadena) queda para la agenda (§13 F).

### 3.4 Presentación

Los gráficos mensuales marcan con marcador vacío los meses con algún subtipo imputado; hoja nueva `Imputaciones`
(rachas por subtipo y serie) y aviso de las de más de 3 meses; gráfico nuevo por cadena; el de región por año marca los
puntos no confiables; el coroplético pinta solo las provincias confiables (las demás, en gris); ponderaciones impresas
con 4 cifras.

## 4. Abierto: la imputación de la serie mensual (decisión del usuario)

Un subtipo-mes con menos de la mitad de sus sucursales habituales (mediana de **todo** el período) arrastra su último
mes válido **sin límite de meses**. Rachas de más de 3 meses en esta corrida (hoja `Imputaciones`):

| Serie | Subtipo | Meses | Sucursales en esos meses | Arrastra |
|---|---|---|---|---|
| todas | Mostachol / penne | 2023-04 → 2024-03 (12) | 120-424 (mediana 1.009) | +152,3% |
| todas | Con chips | 2025-08 → 2026-04 (9) | 8-12 (mediana 158) | +110,9% |
| todas | Obleas | 2023-12 → 2024-07 (8) | 0-49 | +335,7% |
| todas | Rebozador | 2024-01 → 2024-07 (7) | 37-111 (mediana 238) | +31,0% |
| todas | Pepas | 2022-04 → 2022-09 (6) | 43-142 (mediana 324) | +88,2% |
| todas | Rebozador | 2022-04 → 2022-09 (6); 2023-07 → 2023-11 (5) | 34-104 | +82,6%; +87,8% |
| todas | Spaghetti | 2023-12 → 2024-03 (4) | 252-599 (mediana 1.340) | +110,5% |
| panel | Tirabuzón / fusilli | 2023-06 → 2024-07 (14) | 0-118 (mediana 344) | +270,7% |
| panel | Con chips | 2025-08 → 2026-04 (9); 2023-06 → 2023-10 (5) | 4-6 (mediana 28) | +121,3%; +105,1% |
| panel | Mostachol / penne | 2023-04 → 2023-09 (6) | 6-185 (mediana 416) | +116,3% |
| panel | Spaghetti | 2023-07 → 2023-10 (4) | 1-248 (mediana 782) | +65,3% |
| panel | Rebozador | 2023-05 → 2023-08 (4); 2024-07 → 2024-10 (4) | 0-32 (mediana 88) | +95,4%; +126,9% |

Variantes medidas con `r6_variantes_imputacion.py` (promedio de los meses de cada año, canasta del panel; hoy:
2022 110,3 · 2023 112,2 · 2024 110,0 · 2025 101,5 · 2026 122,6, desvío de la variación mensual 10,0 pp):

| Variante | 2022 | 2023 | 2024 | 2025 | 2026 | Desvío | Qué cambia |
|---|---|---|---|---|---|---|---|
| V1: arrastre de a lo sumo 3 meses (después el subtipo sale del tipo) | 110,3 | 108,9 | 102,2 | 101,0 | 121,9 | 10,6 | composición del tipo cambia: en "todas" el desvío sube a 14,2 y mar-2024 salta +31 pp |
| V2: V1 + "habituales" = mediana de 13 meses centrada | 109,8 | 113,5 | 106,7 | 101,0 | 121,9 | 10,0 | |
| V3: V2 + el dato propio después de 3 meses | 109,8 | 113,7 | 106,7 | 101,0 | 121,9 | 9,9 | fideos del panel +25 pp en abr-jun 2023 y −38 a −49 pp en nov-2023 → ene-2024 |
| V4: referencia de todo el período + 3 meses + dato propio | 110,4 | 110,6 | 106,6 | 101,0 | 121,9 | 10,1 | fideos del panel −47 pp en nov-2023 → ene-2024 (el dato propio sale de 200-600 sucursales del hueco de Molinos) |

Ninguna variante es claramente mejor: limitar el arrastre cambia la composición del tipo o usa la mediana de las pocas
sucursales que ya tenían los códigos nuevos de Molinos (el sesgo que la imputación evitaba). Los cambios se concentran en
2023-2024, el tramo ya marcado por los precios controlados; 2025-2026 se mueven menos de 1 pp en el año (con chips:
hasta −11 pp en dulces del panel en nov-2025). **Recomendación**: no tocar la regla y pasar a la **TPD/hedónica** de
BRECHA_CELIACA §3.9 para la serie (log del precio de cada producto en cada sucursal con efectos fijos de producto y de
sucursal × mes, y la prima sin TACC por mes y tipo): no necesita imputar subtipos y la composición de cada sucursal no
mueve la serie. Mientras tanto, los tramos imputados quedan marcados en los gráficos y en la hoja `Imputaciones`.

> **Implementada el 2026-10-23 (noche)** como serie de robustez (CELDA 8b, BRECHA_CELIACA §14.12), con el efecto de
> la celda sucursal × mes del **subtipo** (con el del tipo entero, las galletitas con chips salían al revés) y un mínimo
> de 10 sucursales con los dos lados por subtipo-mes. Confirma lo que mostraban V3 y V4: los fideos del panel de
> jun-2023 → feb-2024 salen de muy pocas sucursales; en todas las sucursales, parte del pico de oct-dic 2023 de la
> descriptiva es imputación (TPD +137% a +148% contra +161% a +170%).

## 5. Próxima corrida de Colab

Ejecutar todo sin tocar la CELDA 1: **no relee el SEPA** (el caché `brecha_v3_38349f0a` no cambia; ~5 min, oct-26 se
lee siempre). La CELDA 7 toma el departamento de la caché de Georef del nb09 en el Drive (si no está, consulta la API,
~1 min). Comparar con los esperados nuevos:

```bash
python -I -X utf8 docs/auditoria/scripts_nb06_2026-10/s16_comparar_colab.py <Excel de Colab> docs/brecha_celiaca/simulacion_2026-10-23b
```

Esperado: **35 hojas iguales** (las 29 de antes, con las de grupos, sucursales y concentración nuevas, más
`Imputaciones` y, desde la noche del 23/10, las 5 de la serie TPD), salvo oct-26 (y la TPD, que estima todos los meses
juntos) si el `2026B.zip` del Drive cambió.

## 6. Scripts

`docs/auditoria/scripts_nb06_2026-10/` (README): `s16` (comparación con los esperados), `s17` (esperados desde el Excel
de una simulación) y los de esta revisión, `r1`-`r9` (resumen de hojas, series, subtipos por mes, lados por mes,
canasta por sucursal y localidades, variantes de la imputación, rachas de imputación y canasta comparable por grupos y
por sucursal) y, para la serie TPD, `r10`-`r12` (LSQR independiente, composición de saladas, TPD contra descriptiva
por subtipo-mes). Simulación con el caché y el notebook vigente: `s11 ... sim_v2 2022-01 --georef
<georef_sucursales.parquet>` (~5 min en la PC, pico de RAM 2,4 GB; `s12` sin cambios: el cálculo desde los precios
sigue dando igual).
