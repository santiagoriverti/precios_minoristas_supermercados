# Resultados esperados del nb06 con BUG-48 (simulación del 2026-10-26)

Un CSV por hoja del Excel `brecha_celiaca_2026-10.xlsx` que generaron las **celdas reales** del notebook vigente
(canasta fija, BUG-47, serie TPD de la CELDA 8b y **BUG-48**: las tiendas online que el maestro carga con tipo
Supermercado o Autoservicio quedan afuera por el nombre, `SUCURSALES_NO_FISICAS`) sobre los **mismos datos** que las
corridas de Colab: el caché del nb06 de los 57 meses cerrados (`brecha_v3_38349f0a`, con los mismos datos que el del
Drive: `docs/AUDITORIA_2026-10-26_nb06.md`), oct-26 leído del `2026B.zip` del Drive (al 22/10), el `ar.json` del Drive y
la caché de Georef del nb09 (`output_trazabilidad/_cache_nb09/georef_sucursales.parquet`). Faltan `Leeme` y las hojas
grandes `Comparacion_productos` y `Detalle_producto`. Armado con `s17_esperados.py` desde la simulación `sim_v3` (s11).

Contra `../simulacion_2026-10-23b/` (el notebook `46e426b`, que Colab reprodujo el 2026-10-26) **no cambian** 10 hojas:
las 5 del panel balanceado (`Serie_canasta_balanceada`, `Canasta_anual_balanceada`, `Brecha_tipo_mes_balanceado`,
`Brecha_tipo_anual_balanceado`, `Brecha_subtipo_anual_balanc`), `Canasta`, `Ponderaciones`, `Imputaciones`,
`Control_EAN` y `Plausibilidad`. Cambian **poco** las otras 25, que usan todas las sucursales, porque salen DIA
"eCommerce" (CABA, 55 subtipo-mes desde ago-2023) y la "Dark Store Mendoza" de Libertad (35 hasta dic-2024): la serie de
la canasta de todas las sucursales cambia en 4 meses (máximo 0,30 pp en sep-2023; por año, 0,01 pp), la brecha por
tipo y mes en 4 tipo-mes (máximo 1,05 pp, saladas de sep-2023), la TPD de todas las sucursales como mucho 0,01 pp en la
canasta (0,04 pp por tipo), CABA +124,28% → +124,29%, la concentración en 5 departamentos (una sucursal menos; Spearman
−0,11 → −0,10), los conteos de sucursales en 1 o 2, y `Brecha_sucursal` tiene 2.175 filas (sin DIA eCommerce). La
mediana por tipo y por subtipo de todo el período no cambia.

## Cómo comparar una corrida de Colab

```bash
python -I -X utf8 docs/auditoria/scripts_nb06_2026-10/s16_comparar_colab.py <brecha_celiaca_2026-10.xlsx de Colab> docs/brecha_celiaca/simulacion_2026-10-26
```

Con el notebook vigente y los mismos datos tiene que dar **35 hojas iguales** (la corrida de Colab del 2026-10-26 con
BUG-48 las dio: `docs/AUDITORIA_2026-10-26_nb06.md` §6). Si difiere solo en `2026-10` (y lo que lo
incluye: últimos 12 meses, `Brecha_sucursal`, `Concentracion` y la serie TPD, que estima todos los meses juntos),
cambió el `2026B.zip` del Drive (el mes en curso se lee siempre); si difieren `Concentracion` y `Brecha_sucursal` en el
departamento, la caché de Georef del Drive es otra. Si difieren las hojas de todas las sucursales como en el párrafo de
arriba (y `Brecha_sucursal` tiene 2.176 filas), Colab corrió el notebook anterior a BUG-48. La salida impresa de la
CELDA 7 tiene que decir "Sucursales que no son locales, afuera: 9 de tipo web o virtual y 6 por el nombre".

## Números clave

| | Esperado |
|---|---|
| Brecha por tipo, 2022-2026 | fideos +172,3%, galletitas dulces +107,8%, saladas +84,4%, rebozador +83,5%, almohaditas +25,9% |
| Canasta por año, panel balanceado | 2022 +110,7%, 2023 +106,1%, 2024 +106,7%, 2025 +100,3%, 2026 +119,9% |
| Últimos 12 meses (nov-2025 → oct-2026), nacional | +122,7% |
| Regiones (las 6 confiables) | Patagonia +107,4%, Pampeana +120,1%, Noreste +124,8% (17,6% imputado), Cuyo +124,9%, AMBA +125,6%, Noroeste +126,7% |
| Provincias confiables (8) | Chubut +110,9%, Entre Ríos +114,1%, Santa Fe +117,3%, Salta +123,0%, Buenos Aires +123,2%, Mendoza +123,7%, CABA +124,3%, Córdoba +127,0% |
| Empresas confiables (3) | Carrefour +124,0%, Cencosud +125,1%, ChangoMas +140,4% |
| Cadenas confiables (7) | Carrefour Market +119,5%, Carrefour +121,1%, Vea +124,3%, Jumbo +126,0%, Disco +128,6%, ChangoMas +141,1%, HiperChangomas +141,9% |
| Concentración | 319 departamentos; 62 con >= 5 sucursales con brecha propia; Spearman por sucursal −0,10 (1.105 sucursales) |
| Sucursales (oct-26) | 2.175; canasta comparable mediana +120,0%; peso medido en la sucursal, mediana 51%; en el mapa, 2.343 |
| Imputaciones | 29 rachas (15 en todas las sucursales y 14 en el panel; de más de 3 meses, 8 y 7; la más larga, tirabuzón en el panel, 14 meses) |
| Serie TPD, canasta por año (panel; todas las sucursales) | 2022 +111,8% (+119,4%), 2023 +122,7% (+123,3%), 2024 +105,4% (+116,4%), 2025 +98,8% (+104,9%), 2026 +117,6% (+122,4%) |
| Serie TPD, oct-2026 | panel +119,0% (IC 95% +118,2% a +119,8%; descriptiva +123,6%); todas +119,9% (+119,4% a +120,4%; descriptiva +122,8%) |
| Serie TPD, subtipo-mes movidos (< 10 sucursales con los dos lados) | 25 en el panel (con chips 14, rebozador 6, tirabuzón 3, spaghetti 1, mostachol 1) y 12 en todas (obleas 8, con chips 4); todos los subtipos con rango completo |
