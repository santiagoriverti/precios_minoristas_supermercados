# Resultados esperados del nb06 con la canasta corregida (BUG-49, simulación del 2026-10-26)

Un CSV por hoja del Excel `brecha_celiaca_2026-10.xlsx` que generaron las **celdas reales** del notebook vigente sobre
los **mismos datos** que leerá Colab. Esa versión tiene la canasta corregida por la auditoría de la selección: 66
productos y 77 códigos (`docs/AUDITORIA_SELECCION_2026-10-26_nb06.md`), más BUG-47, la serie TPD y BUG-48. Los datos:

- los zips semestrales 2022A → 2026B del Drive, releídos los 58 meses porque entran 5 códigos nuevos;
- el `ar.json` del Drive;
- la caché de Georef del nb09.

Faltan `Leeme` y las hojas grandes `Comparacion_productos` y `Detalle_producto`. Armado con `s17_esperados.py` desde la
simulación `sim_v5` (s11). El cálculo independiente de `s12` da lo mismo: precios, brecha por sucursal × mes × subtipo
y × tipo, y las 290 brechas por tipo y mes.

Contra `../simulacion_2026-10-26/` (la canasta del 2026-10-23) cambian 34 de las 35 hojas. Cambian sobre todo los
fideos (entra el tirabuzón sin TACC Matarazzo, salen los Blue Patna) y lo que depende de ellos (canasta, grupos,
concentración, TPD). Lectura de los cambios: `docs/BRECHA_CELIACA.md` §14.13.

## Cómo comparar una corrida de Colab

```bash
python -I -X utf8 docs/auditoria/scripts_nb06_2026-10/s16_comparar_colab.py <brecha_celiaca_2026-10.xlsx de Colab> docs/brecha_celiaca/simulacion_2026-10-26b
```

Con el notebook vigente y los mismos datos tiene que dar **35 hojas iguales**. La primera corrida con esta canasta
relee los 58 meses (cambia la clave del caché: `brecha_v3_492a002c`). Las causas posibles si algo difiere:

- **Solo `2026-10`** (y lo que lo incluye: últimos 12 meses, `Brecha_sucursal`, `Concentracion` y la serie TPD, que
  estima todos los meses juntos): cambió el `2026B.zip` del Drive. El mes en curso se lee siempre.
- **`Concentracion` y `Brecha_sucursal` en el departamento**: la caché de Georef del Drive es otra.
- **Casi todas las hojas**, como contra `../simulacion_2026-10-26/`: Colab corrió el notebook anterior a BUG-49.

La salida impresa de la CELDA 5 tiene que decir "EANs con datos: 77/77". La CELDA 7 tiene que decir dos cosas:

- "Vigencia de códigos (CELDA 1): 53,278 obs fuera de la ventana de su código, no se usan (14 códigos)";
- "Sucursales que no son locales, afuera: 9 de tipo web o virtual y 6 por el nombre".

## Números clave

| | Esperado |
|---|---|
| Brecha por tipo, 2022-2026 | fideos +160,6%, galletitas dulces +107,9%, saladas +84,4%, rebozador +83,5%, almohaditas +25,8% |
| Fideos por subtipo, 2022-2026 | spaghetti +100,0%, mostachol / penne +148,3%, tirabuzón / fusilli +256,2% |
| Canasta por año, panel balanceado | 2022 +111,0%, 2023 +106,2%, 2024 +105,4%, 2025 +96,8%, 2026 +113,7% |
| Canasta por año, todas las sucursales | 2022 +118,9%, 2023 +114,3%, 2024 +115,7%, 2025 +99,7%, 2026 +120,1% |
| Últimos 12 meses (nov-2025 → oct-2026), nacional con la misma canasta de los grupos | +118,0% |
| Regiones (las 6 confiables) | Patagonia +104,2%, Noreste +112,6% (17,6% imputado), Pampeana +114,1%, Cuyo +116,1%, Noroeste +117,1%, AMBA +121,1% |
| Provincias confiables (8) | Chubut +107,0%, Entre Ríos +111,6%, Santa Fe +113,7%, Salta +114,4%, Mendoza +115,7%, Buenos Aires +117,9%, Córdoba +119,5%, CABA +120,9% |
| Empresas confiables (2) | Cencosud +116,2%, Carrefour +121,0%. ChangoMas deja de ser confiable (37,6% imputado): sus únicos fideos sin TACC eran los Blue Patna |
| Cadenas confiables (5) | Carrefour +113,6%, Vea +115,0%, Carrefour Market +116,6%, Jumbo +117,2%, Disco +119,7% |
| Concentración | 319 departamentos; 57 con >= 5 sucursales con brecha propia; Spearman por sucursal +0,12 (1.045 sucursales); terciles de HHI +118,9%, +123,1%, +122,4% |
| Sucursales (oct-26) | 2.324 (entran las de Cooperativa Obrera, Coto y Toledo con el tirabuzón sin TACC Matarazzo); canasta comparable mediana +117,5%; peso medido en la sucursal, mediana 30% |
| Imputaciones | 29 rachas (12 en todas las sucursales y 17 en el panel; de más de 3 meses, 17); la más larga, mostachol / penne en todas las sucursales, 16 meses (2022-12 → 2024-03) |
| Serie TPD, canasta por año (panel; todas las sucursales) | 2022 +106,2% (+111,4%), 2023 +108,8% (+113,1%), 2024 +101,0% (+108,5%), 2025 +95,6% (+100,6%), 2026 +114,5% (+118,4%) |
| Serie TPD, oct-2026 | panel +115,3% (IC 95% +114,7% a +115,9%; descriptiva +116,3%); todas +116,4% (+116,0% a +116,9%; descriptiva +119,2%) |
| Serie TPD, subtipo-mes movidos (< 10 sucursales con los dos lados) | panel: con chips 14, mostachol 6, rebozador 6 y spaghetti 1; todas: obleas 8 y con chips 4. Todos los subtipos con rango completo |
