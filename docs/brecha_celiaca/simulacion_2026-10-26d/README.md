# Resultados esperados del nb06: líneas y penne de la misma marca (simulación del 2026-10-26, noche)

Un CSV por hoja del Excel `brecha_celiaca_2026-10.xlsx` que generaron las **celdas reales** del notebook vigente.

**Canasta**: 67 productos en 45 líneas, 80 códigos. Sobre la de `../simulacion_2026-10-26c/`:

- los sabores de una misma línea (misma marca y presentación en el subtipo, al mismo precio) entran una vez en la
  mediana de su lado (columna `linea` del CSV);
- el penne sin TACC Matarazzo se compara con el Penne rigate Matarazzo común, de la misma marca, en lugar de los
  Mostacholes Lucchetti.

**Datos**, los mismos que leerá Colab:
- los zips semestrales 2022A → 2026B del Drive (Colab relee los 58 meses porque cambian dos códigos);
- el `ar.json` del Drive;
- la caché de Georef del nb09.

Faltan `Leeme` y las hojas grandes `Comparacion_productos` y `Detalle_producto`. Armado con `s17_esperados.py` desde la
simulación `sim_v8` (s11, con el caché del superconjunto filtrado por s15). El cálculo independiente de `s12` da lo
mismo en precios, días, brecha por sucursal × mes × subtipo y × tipo, y las 290 brechas por tipo y mes. Contra
`../simulacion_2026-10-26c/` cambian 33 de las 35 hojas. Lectura: `docs/BRECHA_CELIACA.md` §14.16.

## Cómo comparar una corrida de Colab

```bash
python -I -X utf8 docs/auditoria/scripts_nb06_2026-10/s16_comparar_colab.py <brecha_celiaca_2026-10.xlsx de Colab> docs/brecha_celiaca/simulacion_2026-10-26d
```

Con el notebook vigente y los mismos datos tiene que dar **35 hojas iguales**. La primera corrida relee los 58 meses
(clave del caché `brecha_v3_d5183015`). Si algo difiere:

- **Solo `2026-10`** (y lo que lo incluye): cambió el `2026B.zip` del Drive.
- **`Concentracion` y `Brecha_sucursal` en el departamento**: la caché de Georef es otra.
- **Casi todas las hojas**, como contra `../simulacion_2026-10-26c/`: Colab corrió el notebook anterior.

Líneas de la salida impresa para controlar:

- CELDA 5: "EANs con datos: 80/80".
- CELDA 7: "Vigencia de códigos (CELDA 1): 55,739 obs fuera de la ventana de su código, no se usan (16 códigos)".
- CELDA 8b: "[panel balanceado] Mostachol / penne 1 (1t), [panel balanceado] Rebozador 6 (6t), [panel balanceado]
  Spaghetti 1 (1t), [todas las sucursales] Obleas 8 (8d)".

## Números clave

| | Esperado |
|---|---|
| Brecha por tipo, 2022-2026 | fideos +132,1%, galletitas dulces +87,1%, saladas +77,9%, rebozador +83,5%, almohaditas +25,8% |
| Fideos por subtipo, 2022-2026 | spaghetti +100,0%, penne +110,7% (antes +148,3% contra Lucchetti), tirabuzón +196,8% (antes +256,2%) |
| Galletitas dulces por subtipo, 2022-2026 | con chips +29,4%, obleas +135,4%, pepas +127,1%, rellenas +88,4%, secas +76,0% |
| Saladas por subtipo, 2022-2026 | crackers y galletas de arroz +166,9%, saborizadas +18,6% (antes +28,3%) |
| Canasta por año, panel balanceado | 2022 +92,7%, 2023 +92,4%, 2024 +86,1%, 2025 +79,7%, 2026 +96,2% |
| Canasta por año, todas las sucursales | 2022 +104,8%, 2023 +100,8%, 2024 +102,0%, 2025 +85,0%, 2026 +102,2% |
| Últimos 12 meses (nov-2025 → oct-2026), nacional con la misma canasta de los grupos | +100,1% |
| Regiones (las 6 confiables) | Patagonia +89,0%, Noroeste +97,0%, Pampeana +98,6%, Noreste +99,0%, Cuyo +99,5%, AMBA +102,4% |
| Provincias confiables (8) | Chubut +89,3%, Entre Ríos +94,3%, Salta +94,8%, Santa Fe +98,2%, Mendoza +99,4%, Buenos Aires +100,2%, CABA +102,7%, Córdoba +105,7% |
| Empresas confiables (2) | Carrefour +100,9%, Cencosud +101,4% |
| Cadenas confiables (5) | Carrefour +97,3%, Carrefour Market +97,9%, Vea +98,6%, Jumbo +104,1%, Disco +104,3% |
| Concentración | 319 departamentos; 57 con >= 5 sucursales con brecha propia; Spearman por sucursal +0,12 (1.044 sucursales); terciles de HHI +99,8%, +106,2%, +105,7% |
| Panel balanceado | 5.305 sucursal × subtipo (1.387 sucursales) |
| Sucursales (oct-26) | 2.324; canasta comparable mediana +99,0% |
| Imputaciones | 27 rachas (13 en todas las sucursales y 14 en el panel; de más de 3 meses, 14); la más larga, obleas en todas las sucursales, 8 meses (2023-12 → 2024-07) |
| Serie TPD, canasta por año (panel; todas las sucursales) | 2022 +89,4% (+98,2%), 2023 +93,3% (+104,2%), 2024 +82,3% (+93,4%), 2025 +80,8% (+86,6%), 2026 +98,6% (+101,7%) |
| Serie TPD, oct-2026 | panel +98,4% (IC 95% +98,0% a +98,9%; descriptiva +98,7%); todas +100,1% (+99,7% a +100,5%; descriptiva +100,6%) |
| Serie TPD, subtipo-mes movidos (< 10 sucursales con los dos lados) | panel: mostachol 1, rebozador 6 y spaghetti 1, todos con el mismo subtipo en todas las sucursales; todas: obleas 8, con los demás subtipos. Todos los subtipos con rango completo |
