# Resultados esperados del nb06 (simulación del 2026-10-23)

Un CSV por hoja del Excel `brecha_celiaca_2026-10.xlsx` que generaron las **celdas reales** del
`notebooks/06_evolucion_brecha_celiaca.ipynb` (commit `678e9b9`) sobre los **mismos zips del Drive** que lee Colab
(`MyDrive/carga/2022A.zip` … `2026B.zip`, bajados el 23/10/2026; el `2026B` trae jul-2026 y ago-oct 2026 del SEPA
diario hasta el 22/10) y el `ar.json` del Drive. Faltan solo las hojas grandes `Comparacion_productos` y
`Detalle_producto` (último mes, producto por producto) y `Leeme`.

La simulación coincidió **exactamente** con un cálculo independiente de los precios (3.378.515 precios mensuales por
sucursal × código, 534.456 brechas por sucursal × mes × subtipo, 333.440 por tipo, 290 por tipo y mes): scripts s11 y
s12 de `docs/auditoria/scripts_nb06_2026-10/`. Resumen e interpretación: `docs/BRECHA_CELIACA.md` §14.10.

## Cómo comparar una corrida de Colab

```bash
python -I -X utf8 docs/auditoria/scripts_nb06_2026-10/s16_comparar_colab.py <brecha_celiaca_2026-10.xlsx de Colab> docs/brecha_celiaca/simulacion_2026-10-23
```

Para cada hoja informa las filas que están de un solo lado y la diferencia máxima de cada columna. Con el mismo
notebook y los mismos zips tiene que dar **29 hojas iguales** (diferencias de redondeo < 1e-6). Si difiere:

- solo `2026-10` (y los totales que lo incluyen): el `2026B.zip` del Drive cambió después del 23/10 (el mes en curso se
  lee siempre);
- todo: otro commit del notebook (otra canasta u otro estimador) o zips distintos.

## Números clave

| | Esperado |
|---|---|
| Brecha por tipo, 2022-2026 | fideos +172,3%, galletitas dulces +107,8%, saladas +84,4%, rebozador +83,5%, almohaditas +25,9% |
| Canasta por año, panel balanceado | 2022 +110,7%, 2023 +106,1%, 2024 +106,7%, 2025 +100,3%, 2026 +119,9% |
| Canasta por año, todas las sucursales | 2022 +120,2%, 2023 +116,4%, 2024 +118,4%, 2025 +104,4%, 2026 +125,4% |
| Últimos 12 meses (nov-2025 → oct-2026), confiables | Pampeana +120,1%, Cuyo +124,9%, AMBA +125,6%, Noroeste +126,7%; Carrefour +118,7%, Cencosud +124,8% |
| Lectura | 3.501.948 observaciones, 80/80 códigos, 2.761 sucursales, ningún mes en centavos; vigencia: 57.419 observaciones fuera (16 códigos); plausibilidad: ninguno; `Control_EAN`: 16 marcados |
