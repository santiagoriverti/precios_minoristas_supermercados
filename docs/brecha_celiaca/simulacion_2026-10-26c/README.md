# Resultados esperados del nb06: TPD del panel corregida, Pepitos y las dos Operas (simulación del 2026-10-26, noche)

Un CSV por hoja del Excel `brecha_celiaca_2026-10.xlsx` que generaron las **celdas reales** del notebook vigente.

**Canasta**: 67 productos, 80 códigos. Pepitos 119 g (empalme de tres códigos) reemplaza a Par Nor en con chips, y en
obleas entran la Opera de 220 g y la de 92 g. Sobre la canasta corregida por BUG-49.

**Serie TPD**: en el panel, el subtipo-mes sin pares se mueve con el mismo subtipo en todas las sucursales.

**Datos**, los mismos que leerá Colab:
- los zips semestrales 2022A → 2026B del Drive, releídos los 58 meses porque entran códigos nuevos;
- el `ar.json` del Drive;
- la caché de Georef del nb09.

Faltan `Leeme` y las hojas grandes `Comparacion_productos` y `Detalle_producto`. Armado con `s17_esperados.py` desde la
simulación `sim_v7` (s11). El cálculo independiente de `s12` da lo mismo en precios, días, brecha por sucursal × mes ×
subtipo y × tipo, y las 290 brechas por tipo y mes. Contra `../simulacion_2026-10-26b/` cambian 33 de las 35 hojas.
Lectura: `docs/BRECHA_CELIACA.md` §14.15.

## Cómo comparar una corrida de Colab

```bash
python -I -X utf8 docs/auditoria/scripts_nb06_2026-10/s16_comparar_colab.py <brecha_celiaca_2026-10.xlsx de Colab> docs/brecha_celiaca/simulacion_2026-10-26c
```

Con el notebook vigente y los mismos datos tiene que dar **35 hojas iguales**. La primera corrida relee los 58 meses
(clave del caché `brecha_v3_840d22c6`). Si algo difiere:

- **Solo `2026-10`** (y lo que lo incluye): cambió el `2026B.zip` del Drive.
- **`Concentracion` y `Brecha_sucursal` en el departamento**: la caché de Georef es otra.
- **Casi todas las hojas**, como contra `../simulacion_2026-10-26b/`: Colab corrió el notebook anterior.

Líneas de la salida impresa para controlar:

- CELDA 5: "EANs con datos: 80/80".
- CELDA 7: "Vigencia de códigos (CELDA 1): 56,427 obs fuera de la ventana de su código, no se usan (16 códigos)".
- CELDA 8b: "[panel balanceado] Mostachol / penne 6 (6t), [panel balanceado] Rebozador 6 (6t), [panel balanceado]
  Spaghetti 1 (1t), [todas las sucursales] Obleas 8 (8d)".

## Números clave

| | Esperado |
|---|---|
| Brecha por tipo, 2022-2026 | fideos +160,6%, galletitas dulces +86,8%, saladas +84,4%, rebozador +83,5%, almohaditas +25,8% |
| Galletitas dulces por subtipo, 2022-2026 | con chips +29,4% (Pepitos; antes +110,8% contra Par Nor), obleas +135,4%, pepas +127,1%, rellenas +88,4%, secas +74,5% |
| Canasta por año, panel balanceado | 2022 +101,9%, 2023 +97,7%, 2024 +94,1%, 2025 +87,5%, 2026 +106,1% |
| Canasta por año, todas las sucursales | 2022 +114,2%, 2023 +111,1%, 2024 +106,7%, 2025 +91,3%, 2026 +113,0% |
| Últimos 12 meses (nov-2025 → oct-2026), nacional con la misma canasta de los grupos | +111,0% |
| Regiones (las 6 confiables) | Patagonia +99,4%, Noreste +106,0%, Pampeana +106,9%, Noroeste +108,1%, Cuyo +109,2%, AMBA +114,1% |
| Provincias confiables (8) | Chubut +101,4%, Entre Ríos +103,6%, Salta +106,0%, Santa Fe +107,4%, Mendoza +109,3%, Buenos Aires +110,7%, Córdoba +112,6%, CABA +114,0% |
| Empresas confiables (2) | Cencosud +109,3%, Carrefour +113,8% |
| Cadenas confiables (5) | Carrefour +106,1%, Vea +108,0%, Carrefour Market +109,1%, Jumbo +110,4%, Disco +112,8% |
| Concentración | 319 departamentos; 57 con >= 5 sucursales con brecha propia; Spearman por sucursal +0,14 (1.049 sucursales); terciles de HHI +111,6%, +116,3%, +115,5% |
| Panel balanceado | 5.319 sucursal × subtipo (1.385 sucursales) |
| Sucursales (oct-26) | 2.324; canasta comparable mediana +108,5% |
| Imputaciones | 25 rachas (11 en todas las sucursales y 14 en el panel; de más de 3 meses, 14); la más larga, mostachol / penne en todas las sucursales, 16 meses (2022-12 → 2024-03) |
| Serie TPD, canasta por año (panel; todas las sucursales) | 2022 +98,1% (+106,1%), 2023 +100,7% (+111,3%), 2024 +89,6% (+99,9%), 2025 +87,3% (+92,8%), 2026 +107,6% (+110,3%) |
| Serie TPD, oct-2026 | panel +107,2% (IC 95% +106,6% a +107,8%; descriptiva +108,1%); todas +108,2% (+107,8% a +108,6%; descriptiva +110,2%) |
| Serie TPD, subtipo-mes movidos (< 10 sucursales con los dos lados) | panel: mostachol 6, rebozador 6 y spaghetti 1, todos con el mismo subtipo en todas las sucursales; todas: obleas 8, con los demás subtipos. Todos los subtipos con rango completo |
