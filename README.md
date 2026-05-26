# Precios Minoristas en Supermercados de Argentina

Análisis de precios minoristas reportados diariamente por supermercados de Argentina, basado en datos públicos del [SEPA (Secretaría de Comercio)](https://datos.produccion.gob.ar/dataset/sepa-precios).

## Fuente de datos

Los datos provienen del **SEPA** (Sistema Electrónico de Publicidad de Precios Argentinos), que publica diariamente los precios reportados por las principales cadenas de supermercados del país. Los archivos están organizados por semestre y contienen precios por sucursal y producto para cada día del mes.

## Notebooks disponibles

| Notebook | Descripción | Abrir en Colab |
|----------|-------------|----------------|
| `exploracion_productos` | Exploración de productos de abril 2026 y construcción de una canasta representativa para una familia tipo de 4 integrantes, con criterios de cobertura por cadena y región geográfica | [![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/santiagoriverti/precios_minoristas_supermercados/blob/main/notebooks/exploracion_productos.ipynb) |

> **¿Ves una versión vieja?** El badge abre siempre la última versión desde GitHub, pero si Colab ya guardó una copia anterior en tu Drive, puede mostrar esa en cambio. Para forzar la versión actualizada: eliminá `Mi unidad/Colab Notebooks/exploracion_productos.ipynb` de tu Google Drive y volvé a hacer clic en el badge.

## Cómo usar los notebooks

1. Hacer clic en el badge **"Abrir en Colab"** del notebook deseado
2. Montar Google Drive cuando el notebook lo solicite
3. Subir el ZIP del SEPA correspondiente a tu Google Drive (ver sección **Datos SEPA requeridos**)
4. Ejecutar las celdas en orden — los maestros se descargan automáticamente desde GitHub

> Los notebooks instalan automáticamente las dependencias que no vienen por defecto en Colab.

## Estructura del proyecto

```
precios_minoristas_supermercados/
├── README.md
├── notebooks/                              # Notebooks ejecutables en Google Colab
│   └── exploracion_productos.ipynb         # Exploración y construcción de canasta
└── data/                                   # Maestros de referencia
    ├── Maestro de Productos Interno.xlsx   # Clasificación de productos (rubro, categoría)
    └── maestro_sucursales_completo.xlsx    # Metadata de sucursales (cadena, región)
```

## Datos SEPA requeridos

Los archivos de precios SEPA **no están incluidos en el repositorio** por su tamaño. Deben descargarse desde:

- [datos.produccion.gob.ar/dataset/sepa-precios](https://datos.produccion.gob.ar/dataset/sepa-precios)

Organización esperada en Google Drive:
```
MyDrive/SEPA/
├── 2026A.zip     # Precios ene–jun 2026
├── 2025B.zip     # Precios jul–dic 2025
├── ...
├── Maestro de Productos Interno.xlsx
└── maestro_sucursales_completo.xlsx
```

## Contribuciones

Proyecto desarrollado en el marco del análisis de precios minoristas para seguimiento de la evolución de precios en Argentina.
