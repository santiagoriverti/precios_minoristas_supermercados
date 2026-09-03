# Canastas alternativas — cantidades para `Productos unicos` (nb07)

Cuatro canastas para cargar en la hoja **`Productos unicos`** del Excel
`canasta_representativa_YYYY-MM.xlsx`, que el notebook **07** lee para calcular la
evolución semanal del costo.

| Columna | Canasta | Criterio |
|---|---|---|
| `cantidad_01` | **Popular** | Segundas marcas / básicos (Cocinero, Molinos Ala, Schneider, Pepsi…) |
| `cantidad_02` | **Media** | Marcas líderes (La Serenísima, Natura, Quilmes, Coca, Colgate…) |
| `cantidad_03` | **Ejecutiva** | Premium + más variedad (Don Vicente, aceite de oliva, Stella, Dove…) |
| `cantidad_04` | **Tecnológica** | Bundle de durables (TV, notebook, celular, heladera, lavarropas, microondas, aire) — `qty=1` c/u |

## Archivos
- **`cantidades_dict.py`** — diccionario Python `CANTIDADES = { ean: {cantidad_01..04} }`.
- **`cantidades_productos_unicos.csv`** — tabla lista para pegar (`id_producto` + `cantidad_01..04` + cobertura).
- **`cantidades_detalle.csv`** — detalle completo (marca, rubro, cobertura, precio, cantidades).

## Cómo cargarlas
1. Abrí el Excel, hoja `Productos unicos`.
2. Para cada `id_producto` del CSV, poné su `cantidad_01..04` en las columnas amarillas.
   (Se pueden cruzar por `id_producto` con BUSCARV/`merge`.)
3. Guardá el Excel en `output_canasta/` en tu Drive.
4. Corré nb07 → los resultados quedan en **`output_canasta_alternativa/`**.

## Metodología
- **Empaquetados por EAN**: cada producto se eligió del universo real de `Productos unicos`
  exigiendo **cobertura ≥4 cadenas** (casi todos son cad=5 / 24 provincias / miles de sucursales),
  para garantizar comparabilidad entre cadenas y provincias.
- **Frescos (frutas, verduras, carne, huevos)**: NO van en el Excel — nb07 los toma por
  **nombre** (`TIPOS_FRESCOS`, CELDA 1), normalizados a $/kg o $/docena, porque el EAN de balanza
  cambia por cadena. La canasta **Tecnológica no lleva frescos**.
- **Escalera de calidad**: los estratos difieren en **marca** y en **cantidad** (ver `TIPOS_FRESCOS`
  y la tabla `QTY` del generador de canastas).
- **Cantidades**: canasta mensual para familia tipo de 4, escalonadas por estrato. Ajustables.

## Validación / iteración
El notebook imprime una celda **"REPORTE PARA CLAUDE"** y las hojas `Cobertura_emp` /
`Cobertura_frescos`. Si algún EAN queda **SIN datos** o con **baja comparabilidad**, se reemplaza.
La canasta Tecnológica puede quedar rala si pocas sucursales tienen ≥50% de los durables
(`FRAC_PRODUCTOS_MIN`): en ese caso se baja el umbral para ese estrato.
