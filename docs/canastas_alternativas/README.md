# Canastas alternativas — cantidades para `Productos unicos` (nb07)

Cinco canastas para cargar en la hoja **`Productos unicos`** del Excel
`canasta_representativa_YYYY-MM.xlsx`, que el notebook **07** lee para calcular la
evolución **semanal** del costo (nacional / provincia / cadena / **región**).

| Columna | Canasta | Criterio |
|---|---|---|
| `cantidad_01` | **Popular** | Segundas marcas / básicos (Cocinero, Molinos Ala, Schneider, Pepsi…) |
| `cantidad_02` | **Media** | Marcas líderes (La Serenísima, Natura, Quilmes, Coca, Colgate…) |
| `cantidad_03` | **Ejecutiva** | Premium + más variedad (Don Vicente, oliva, Stella, Fernet, Dove…) |
| `cantidad_04` | **Tecnológica** | Bundle de durables (TV, notebook, celular, heladera, lavarropas, microondas, aire) — `qty=1` c/u |
| `cantidad_05` | **Representativa** | Canasta única del consumidor "promedio" (marcas líderes, cantidades típicas) |

**124 productos empaquetados** (117 alimentos/bebidas/limpieza/higiene + 7 durables), todos
con cobertura **≥4 cadenas**. Además, nb07 suma **33 tipos de frescos** por nombre
(frutas, verduras, carne, huevos), buscados **por sucursal** según las variantes disponibles
(el EAN de balanza cambia por cadena).

## Archivos
- **`cantidades_dict.py`** — diccionario Python `CANTIDADES = { ean: {cantidad_01..04} }`.
- **`cantidades_productos_unicos.csv`** — tabla lista para pegar (`id_producto` + `cantidad_01..04` + cobertura).
- **`cantidades_detalle.csv`** — detalle completo (marca, rubro, cobertura, precio, cantidades).
- **`cargar_en_productos_unicos.py`** — script autónomo de **Colab**: subís el Excel
  `canasta_representativa_*.xlsx` y te lo devuelve con `cantidad_01..04` cargadas en la hoja
  `Productos unicos` (limpia las columnas primero y reporta cobertura + EAN faltantes).

## Cómo cargarlas
**Opción A (recomendada) — script de Colab**: pegá `cargar_en_productos_unicos.py` en una
celda de Colab, ejecutá, subí el Excel; descargás `..._con_canastas.xlsx` con todo cargado.

**Opción B — manual**:
1. Abrí el Excel, hoja `Productos unicos`.
2. Para cada `id_producto` del CSV, poné su `cantidad_01..04` en las columnas amarillas
   (se pueden cruzar por `id_producto` con BUSCARV/`merge`).

Después, en cualquier caso:
3. Guardá el Excel en **`output_canasta/`** en tu Drive (carpeta de ENTRADA).
4. Corré nb07 → los resultados quedan en **`output_canasta_alternativa/`** (carpeta de SALIDA).
5. Copiá el bloque **"REPORTE PARA CLAUDE"** (CELDA 15) + las hojas `Cobertura_emp`/
   `Cobertura_frescos` para afinar las cantidades.

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
