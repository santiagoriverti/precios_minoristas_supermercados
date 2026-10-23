# Resultados esperados del nb06 con BUG-47 (simulación del 2026-10-23, tarde)

Un CSV por hoja del Excel `brecha_celiaca_2026-10.xlsx` que generaron las **celdas reales** del notebook vigente (con
BUG-47: misma canasta de 12 subtipos para provincias, regiones, empresas, cadenas y sucursales; concentración por
departamento) sobre los **mismos datos** que la primera corrida de Colab: el caché del nb06 de los 57 meses cerrados
(`brecha_v3_38349f0a`, idéntico al de Colab: esa corrida dio igual a `../simulacion_2026-10-23/` en las 29 hojas), oct-26
leído del `2026B.zip` del Drive (al 22/10), el `ar.json` del Drive y la caché de Georef del nb09
(`output_trazabilidad/_cache_nb09/georef_sucursales.parquet`, 3.600 sucursales). Faltan `Leeme` y las hojas grandes
`Comparacion_productos` y `Detalle_producto`. Armado con `s17_esperados.py`.

Contra la carpeta anterior no cambian las 14 hojas de lectura, subtipos, tipos y series por tipo; las series de la
canasta (`Serie_canasta*`, `Canasta_anual*`) tienen los mismos valores y una columna nueva (`peso_imputado_pct`); cambian
por diseño las de grupos (`Brecha_provincia`, `_region`, `_region_anual`, `_empresa`, `_empresa_anual`, `_cadena` y
`Brecha_tipo_provincia`, `_region`, `_empresa`), `Brecha_sucursal` y `Concentracion`, y se agrega `Imputaciones`.
Verificado: grupos y canasta comparable por sucursal iguales a cálculos independientes (`r8`, `r9`; diferencia máxima
1e-13); brecha por sucursal × mes × subtipo y tipo igual al cálculo desde los precios (`s12`).

## Cómo comparar una corrida de Colab

```bash
python -I -X utf8 docs/auditoria/scripts_nb06_2026-10/s16_comparar_colab.py <brecha_celiaca_2026-10.xlsx de Colab> docs/brecha_celiaca/simulacion_2026-10-23b
```

Con el notebook vigente y los mismos datos tiene que dar **30 hojas iguales**. Si difiere solo en `2026-10` (y lo que lo
incluye: últimos 12 meses, `Brecha_sucursal`, `Concentracion`), cambió el `2026B.zip` del Drive (el mes en curso se lee
siempre); si difiere `Concentracion` y `Brecha_sucursal` en el departamento, la caché de Georef del Drive es otra.

## Números clave

| | Esperado |
|---|---|
| Brecha por tipo, 2022-2026 | fideos +172,3%, galletitas dulces +107,8%, saladas +84,4%, rebozador +83,5%, almohaditas +25,9% (sin cambios) |
| Canasta por año, panel balanceado | 2022 +110,7%, 2023 +106,1%, 2024 +106,7%, 2025 +100,3%, 2026 +119,9% (sin cambios) |
| Últimos 12 meses (nov-2025 → oct-2026), nacional | +122,7% |
| Regiones (las 6 confiables) | Patagonia +107,4%, Pampeana +120,1%, Noreste +124,8% (17,6% imputado), Cuyo +124,9%, AMBA +125,6%, Noroeste +126,7% |
| Provincias confiables (8) | Chubut +110,9%, Entre Ríos +114,1%, Santa Fe +117,3%, Salta +123,0%, Buenos Aires +123,2%, Mendoza +123,7%, CABA +124,3%, Córdoba +127,0% |
| Empresas confiables (3) | Carrefour +124,0%, Cencosud +125,1%, ChangoMas +140,4% |
| Cadenas confiables (7) | Carrefour Market +119,5%, Carrefour +121,1%, Vea +124,3%, Jumbo +126,0%, Disco +128,6%, ChangoMas +141,1%, HiperChangomas +141,9% |
| Concentración | 319 departamentos; 62 con >= 5 sucursales con brecha propia; Spearman por sucursal −0,11 (1.105 sucursales) |
| Sucursales (oct-26) | 2.176; canasta comparable mediana +120,0%; peso medido en la sucursal, mediana 51% |
| Imputaciones | 29 rachas (15 en todas las sucursales y 14 en el panel; de más de 3 meses, 8 y 7; la más larga, tirabuzón en el panel, 14 meses) |
