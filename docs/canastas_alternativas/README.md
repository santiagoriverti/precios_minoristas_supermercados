# Canastas alternativas — composición y carga (v4)

Insumo del notebook **`07_evolucion_canastas_alternativas`**, que produce el informe semanal.

## Las 6 canastas

| Columna | Canasta | Productos empaquetados | Frescos | Idea |
|---|---|---:|---:|---|
| `cantidad_01` | **Popular** | 66 | 34 tipos | Primeras marcas económicas, presentaciones chicas |
| `cantidad_02` | **Media** | 100 | 58 tipos | Marcas líderes, canasta de hogar tipo |
| `cantidad_03` | **Ejecutiva** | 104 | 56 tipos | Premium, más variedad y volumen |
| `cantidad_04` | **Tecnológica** | 14 | — | Bundle de durables (heladera, lavarropas, TV, notebook…) |
| `cantidad_05` | **Representativa** | 108 | 59 tipos | Calibrada a consumo de familia tipo de 4 (referencia CBA INDEC) |
| `cantidad_06` | **Femenina** | 16 | — | Gestión menstrual, depilación y cuidado personal femenino |

**196 EANs únicos** en total. Todos seleccionados de la hoja real `Productos unicos` exigiendo
cobertura: **≥4 cadenas, ≥15 provincias y ≥800 sucursales** (los durables de la Tecnológica,
que son inherentemente menos publicados: ≥3 cadenas, ≥10 provincias, ≥90 sucursales).

Los **frescos NO se cargan acá**: van por regla de nombre en la CELDA 1 del notebook
(`TIPOS_FRESCOS`, 59 tipos), porque el EAN de balanza cambia entre cadenas.

## Cómo cargar las cantidades

1. Abrí `cargar_canastas_v4.py`, copiá **todo** el contenido y pegalo en una celda de Colab.
2. Ejecutá. Cuando te pida el archivo, subí el Excel `canasta_representativa_*.xlsx`
   (sirve cualquier versión: el script **limpia y reescribe** `cantidad_01..06` completo).
3. Descargá el `*_con_canastas.xlsx` que genera.
4. Subilo a Drive en `carga/output_canasta/`, reemplazando `canasta_representativa_<periodo>.xlsx`.
5. Corré el notebook 07.

> El script crea las columnas `cantidad_0X` que falten, y avisa si algún EAN no está en la hoja.

## Editar la composición

El diccionario `CANTIDADES` del loader es editable: cada fila es
`'<EAN>': {'cantidad_01': q1, ..., 'cantidad_06': q6},  # rubro | descripción`.
Poné `0` para sacar un producto de una canasta.

`canastas_v4_detalle.csv` tiene el detalle de cada pick (EAN, descripción, marca, rubro,
categoría, slot, cobertura y precio mediano del período de referencia) por si querés auditar
o reemplazar productos.

## Trazabilidad

El notebook exporta dos hojas para controlar altas y bajas a lo largo del tiempo:

- **`Presencia_items`**: matriz ítem × mes con el % de semanas del mes en que el ítem tuvo
  precio real en el SEPA. Sirve para ver cuándo entró o salió un producto.
- **`Alertas_reemplazo`**: ítems de alguna canasta sin dato en las últimas 8 semanas. Son los
  candidatos a reemplazar (buscá un sustituto en `Productos unicos` y editá el loader).
- **`Panel_nacional`**: precio nacional de cada ítem por semana. Es la materia prima de todas
  las series: si una canasta muestra un salto raro, se busca acá qué ítem lo causó.

Un ítem que falta pocas semanas **no rompe la serie**: el notebook arrastra su último precio
nacional conocido (hasta 8 semanas) y, además, el índice es **encadenado de muestra apareada**,
así que las altas y bajas no generan saltos artificiales en el nivel.
