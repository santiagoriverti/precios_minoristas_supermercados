# Revisión de la segunda corrida del nb06 en Colab: BUG-47 y serie TPD (2026-10-26)

Corrida del usuario en Colab del nb06 vigente (commit `46e426b`: canasta fija 2022-2026, BUG-47 y la serie TPD de la
CELDA 8b). Insumos: la salida impresa, `output_brecha/brecha_celiaca_2026-10.xlsx`, `mapa_sucursales_brecha_102026.html`
y el zip del caché del Drive (`_cache-20261026T124728Z-1-001.zip`, la carpeta `output_brecha/_cache/`). No están en el
repo; se revisaron en una carpeta propia (`C:\Users\sriverti\proyectos\nb06_brecha_celiaca_20261023\colab_20261026\`)
con `python -I`.

Resultado: **la corrida de Colab es idéntica a la simulación local en todo lo que produce** (Excel, mapa, salida impresa
y caché). BUG-47 y la serie TPD quedan **validados en Colab**. La revisión encontró un detalle menor de universo (dos
tiendas online que pasan el filtro de sucursales web, §3.1) y uno de formato (§3.3); ninguno cambia los números clave.

## 1. La corrida contra la simulación

| Qué | Cómo | Resultado |
|---|---|---|
| Excel contra los esperados | `s16_comparar_colab.py <Excel> docs/brecha_celiaca/simulacion_2026-10-23b` | **35 hojas iguales** (diferencia máxima 1,4e-13) |
| Excel completo contra el de la simulación | `r13_comparar_excels.py <Excel de Colab> <Excel de sim_v2>` (también `Leeme`, `Comparacion_productos` y `Detalle_producto`) | **38 hojas iguales** (diferencia relativa máxima 4,3e-14); `Brecha_sucursal` tiene las mismas 2.176 filas, con otro orden entre valores casi empatados |
| Mapa por sucursal | `r15_comparar_mapas.py <mapa de Colab> <mapa de sim_v2>` | **igual** salvo los identificadores aleatorios de Folium: 2.344 sucursales en el JSON de los popups (2026-10: 2.176; 2026-05: 127); el JavaScript pasa `node --check` |
| Salida impresa | diferencia línea por línea contra `s11_sim_tpd4_20261023.log` | **169 líneas iguales** (desde "Tipos: 5" hasta el mapa; solo cambian las rutas y los tiempos) |
| Caché del Drive | `r14_comparar_cache.py <zip> <carpeta> sim_v2/_cache/brecha_v3_38349f0a` | **57 meses (2022-01 → 2026-09), 3.438.538 filas, los mismos datos** que el caché local; los bytes difieren (lo escribió otra versión de las librerías), los datos no. Lo escribió la primera corrida, el 23/10 |

Lo que pide §14.9 de BRECHA_CELIACA da lo esperado: lectura desde el caché (57 meses cerrados, 0 por leer, oct-26 leído;
3.501.948 observaciones, 80/80 códigos, 2.761 sucursales), vigencia (57.419 observaciones fuera de ventana, 16 códigos),
16 códigos en `Control_EAN`, 12 sucursales reclasificadas, AMBA 1.973, departamento de 3.577 de 3.579 sucursales,
panel de 4.975 sucursal × subtipo, imputaciones (29 rachas), grupos (6 regiones, 8 provincias, 3 empresas y 7 cadenas
confiables), concentración (Spearman −0,11) y la **serie TPD**: rango completo en los 11 subtipos del panel y los 12 de
todas; subtipo-mes movidos: panel con chips 14, mostachol 1, rebozador 6, spaghetti 1, tirabuzón 3 y todas con chips 4,
obleas 8; último mes (panel) TPD +119,0% (IC 95% +118,2% a +119,8%) contra +123,6% de la descriptiva.

Los gráficos no se adjuntaron: salen de los mismos datos, así que son los de la simulación local (revisados, incluidos
`brecha_tpd` y `brecha_tpd_tipos` con los meses movidos marcados).

## 2. Lectura

Sin cambios respecto de BRECHA_CELIACA §14.10-§14.12 y `AUDITORIA_2026-10-23_nb06.md`: brecha por tipo 2022-2026
(fideos +172%, dulces +108%, saladas +84%, rebozador +84%, almohaditas +26%), canasta del panel entre +100% y +120% según
el año, la cadena pesa más que la región, la concentración local no se relaciona con la brecha y la TPD coincide con la
descriptiva fuera de jun-2023 → feb-2024 (diferencia absoluta mediana 4,1 pp en el panel).

## 3. Hallazgos

### 3.1 Dos tiendas online dentro del universo (menor)

El filtro de sucursales web de la CELDA 7 mira `sucursales_tipo` ("web" o "virtual"). Dos tiendas que no son locales
tienen otro tipo en el maestro y entran:

| Sucursal | Cadena | Tipo en el maestro | Provincia | Subtipo-mes con brecha |
|---|---|---|---|---|
| `15-1-90000` "eCommerce" | DIA | Supermercado | CABA | 55 (ago-2023 → oct-2026) |
| `16-2-6104` "Dark Store Mendoza" | Mini Libertad | Autoservicio | Mendoza | 35 (ene-2022 → dic-2024) |

Ninguna llega al 70% de los meses: **no están en el panel balanceado** (la serie clave no cambia). En la serie de todas
las sucursales mueven la mediana de un subtipo-mes menos de 0,3 pp, salvo crackers de sep-2023 (3,3 pp, porque las
brechas de crackers tienen dos niveles y la mediana salta de uno a otro). DIA eCommerce aparece en el mapa como un punto
en CABA (oct-2026, +117%, 17% del peso medido) y cuenta como una sucursal de DIA en su comuna para la concentración.
Arreglo posible, sin releer: excluir también por nombre (`ecommerce`, `e-commerce`, `dark store`, `web`). Cambia
levemente las hojas de todas las sucursales, los grupos y el mapa, y obliga a regenerar los esperados y a re-correr en
Colab.

### 3.2 Reclasificación de provincia y fuente (conocidos, sin cambios)

- Las 12 reclasificaciones son las de BUG-44: las 7 sucursales con datos están bien reclasificadas (6 DIA de Jujuy que
  el maestro declara San Juan, la Dark Store de Libertad declarada Córdoba). Las otras 5 (cadenas 2002 y 2011) no tienen
  precios de la canasta; una, "Gualeguaychu" (2002-1-134), tiene coordenadas de Río Cuarto (error del maestro, sin
  efecto en el nb06).
- Las 127 sucursales del mapa con dato de may-2026 son 112 de la Cooperativa Obrera, que dejó de tener en el SEPA los
  sin TACC de la canasta (dulces, saladas y rebozador desde abr-2025, almohaditas desde ago-2025, fideos desde jun-2026;
  los con TACC siguen, 146-148 sucursales por mes), y 13 de Hipermercado Libertad, que deja de publicar en jun-2026.

### 3.3 Formato (cosmético)

En `Serie_TPD`, las columnas `dif_tpd_menos_descriptiva_panel_pp` y `_todas_pp` no tienen formato numérico (se ven con
muchos decimales); el resto de las hojas tiene el encabezado, el panel congelado y los formatos de siempre.

## 4. Qué queda

- **Aplicado el mismo día, a pedido del usuario (BUG-48)**: las tiendas online salen también por el nombre
  (`SUCURSALES_NO_FISICAS` en la CELDA 1: 6 sucursales del maestro, 2 con precios) y las columnas `_pp` tienen
  formato. El panel no cambia; la serie de todas las sucursales, como mucho 0,30 pp en un mes. Esperados nuevos:
  `docs/brecha_celiaca/simulacion_2026-10-26/`. Falta la corrida de Colab (~5 min, no relee).
- La regla de imputación de la descriptiva sigue como está (decisión del usuario; la TPD muestra dónde pesa).
- Agenda del paper (BRECHA_CELIACA §13): determinantes de la prima con la hedónica, prima neta de envase, robustez
  desde 2024.

## 5. Scripts

En `docs/auditoria/scripts_nb06_2026-10/`: `s16` (contra los esperados), y nuevos para revisar una corrida de Colab
completa: `r13_comparar_excels.py` (todas las hojas, celda por celda), `r14_comparar_cache.py` (el zip del caché del
Drive contra el local) y `r15_comparar_mapas.py` (el mapa, sin los identificadores de Folium, y su JSON).
