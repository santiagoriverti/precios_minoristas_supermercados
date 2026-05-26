# Precios Minoristas en Supermercados de Argentina

Análisis de precios minoristas reportados diariamente por supermercados de Argentina, basado en datos públicos del [SEPA (Secretaría de Comercio)](https://datos.produccion.gob.ar/dataset/sepa-precios).

## Fuente de datos

Los datos provienen del **SEPA** (Sistema de Estabilización de Precios Alimentarios), que publica diariamente los precios reportados por las principales cadenas de supermercados del país. Los archivos están organizados por semestre y contienen precios por sucursal y producto para cada día del mes.

## Notebooks disponibles

| Notebook | Descripción | Abrir en Colab |
|----------|-------------|----------------|
| `exploracion_productos` | Exploración de productos de abril 2026 y construcción de una canasta representativa para una familia tipo de 4 integrantes, con criterios de cobertura por cadena y región geográfica | [![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/santiagoriverti/precios_minoristas_supermercados/blob/main/notebooks/exploracion_productos.ipynb) |

## Cómo usar los notebooks

1. Hacer clic en el badge **"Abrir en Colab"** del notebook deseado
2. Montar Google Drive cuando el notebook lo solicite
3. Subir los archivos necesarios a Google Drive (ver sección **Datos requeridos** dentro de cada notebook)
4. Ajustar las rutas en la celda de **Configuración** y ejecutar las celdas en orden

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
