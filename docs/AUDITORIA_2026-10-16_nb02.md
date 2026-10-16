# Revisión de la corrida nb02 — oct-26 al 15/10 (2026-10-16)

Primera corrida en Colab de las CELDAS 19b y 19c (commit `d140972`). Insumos que pasó el usuario: la salida impresa,
`canasta_analisis_2026-10.xlsx`, `canasta_representativa_2026-10.xlsx`, `trazabilidad_candidatos_2026-10.xlsx`,
`datos_econometria_2026-10.xlsx` y un zip de `output_canasta/_cache/` (`detalle_ea281ee7_v1.parquet`,
`hist_union_d452a45b_v2m.parquet`, `econ_7c7bf6d7.parquet`, `df_suc_2026-10.parquet`). Los insumos no están en el repo.

Resultado: **lo nuevo (19b y 19c) dio exactamente lo validado**; la revisión encontró defectos previos en las CELDAS 16,
18 y 20 (los números del documento técnico), corregidos el mismo día como **BUG-42** (commit `d6e1f52`).

## 1. La corrida

| Punto | Resultado |
|---|---|
| Canastas | 6 activas: Vulnerable 45 productos, Popular 59, Media 69, Media Alta 75, Celíaca Media 71, Vegana Básica 50; **256 EANs** en la unión, todos con datos |
| Mes | Octubre 2026 **parcial, 15/31 días** (`102026_pais_parte1COMPLETO.csv.gz` en 2026B.zip): nivel = foto al 15; variación preliminar |
| Universo | Maestro 3.600 sucursales; 4.846.917 observaciones sucursal × día; 2.435 sucursales; 121 reclasificadas por coordenadas; 2.290-2.308 sucursales por canasta en el Cuadro 1 |
| Serie | Caché `hist_union_d452a45b_v2m` al día (33 meses cerrados) + oct-26 fresco; 34 meses 2024-01 → 2026-10 |
| IPC | 117 meses, 2017-01 → **2026-09** (octubre sin publicar) |
| Tiempos | 19c primera vez **2.069 s** (12 meses leídos del SEPA, 158-182 s cada uno; deja `detalle_ea281ee7_v1.parquet` con 13 meses). Econometría releyó 33 meses (`en cache: 0`): el caché `econ_7c7bf6d7` es nuevo; la próxima corrida tiene que decir 33 en caché |

## 2. Lo nuevo: CELDAS 19b y 19c — OK

- **19b**: oficial **+1,748%** ($673.534 → $685.307), medianas reproducidas **69/69**, arrastre +1,479 pp y suba nueva
  +0,269 pp, panel apareado +1,971% (2.927 sucursales, 91.650 pares, 0 fuera de banda). Idéntico a la validación del
  2026-10-15 con el prototipo.
- **19c**: `analisis_detallado` es la primera de las 39 hojas, sin AVISO de "Total vs suma ponderada". Total oct-26
  +1,75 = oficial; la variación de cada grupo = `var_mediana_grupo_%` de la 19b.
- Ponderaciones con base sep-25 (12 meses): Perfumería 21,55, Frescos 19,92, Almacén 19,71, Bebidas 15,80, Limpieza
  14,61, Congelados 8,41. La validación del 15/10 (base jul-26) daba 21,8/20,0/18,4/16,4/15,0/8,4: la ponderación es la
  del mes base y cambia con él.
- Interanual a sep-26 (índice sep-25 = 100): Total **126,54**; Perfumería 129,56; Bebidas 130,46; Limpieza 128,66;
  Frescos 127,23; Congelados 124,18; Almacén 118,84. Regiones: AMBA 128,45, Patagonia 127,85, Pampeana 125,59,
  Noreste 125,25, Noroeste 120,61, Cuyo 119,91.

## 3. Defectos encontrados y corregidos (BUG-42)

"Ahora" = la CELDA 20 nueva corrida sobre los mismos datos con
`docs/auditoria/scripts_nb02_2026-10/simular_valores_documento.py`.

| # | Defecto | Antes (corrida) | Ahora (mismos datos) |
|---|---|---|---|
| 1 | "AMBA" de los rankings de cadenas = CABA + **toda** la provincia | 1.655 sucursales (Media); Toledo (Mar del Plata), Cooperativa Obrera (Bahía Blanca) y La Anónima en el ranking AMBA | AMBA = CABA + Buenos Aires a ≤ 90 km del Obelisco: **1.405** sucursales, sin esas tres; Vea entra (22 sucursales) |
| 2 | Acumulados en períodos distintos | Media +167,36% (a oct-26 parcial) contra IPC Alimentos +166,35% (a sep-26): "arriba del IPC" | Mismo período ene-24 → sep-26: Media **+162,77%** contra **+166,35%**: abajo. Lo que va a oct-26 queda aparte, marcado "no comparar" |
| 3 | Cuatro "país" | Cuadro 1 $682.699; mediana de sucursales $684.682 (barrios, línea del gráfico de cadenas); media de sucursales $687.009 ("vs nacional" de cadenas en la CELDA 20); serie $685.307. Cadenas y barrios por **media** en la CELDA 20; "Promedio CABA" $687.986 ≠ fila CABA del Cuadro 1 ($685.945) | Todo "vs país" contra $682.699; CABA $685.945; cadenas y barrios por mediana (= rankings [mediana]). El nivel es el del Cuadro 1 y la variación la de la serie, con sus dos extremos en la hoja |
| 4 | Resumen asimétrico | 3 caras y 1 barata (nacional), 1 y 1 (AMBA) | 3 y 3 en los dos |
| 5 | Dispersión entre sucursales | mín-máx **38,8%** (una sucursal 20% abajo) | **P5-P95 6,5%** ($667.148-$710.624); el mín-máx queda con la sucursal: mínima Hiper ChangoMas San Martín $548.469 (66/69 productos propios), máxima Jumbo Comodoro $761.229 |
| 6 | Formato | "+8.7%" (con `abs()`: una prima negativa salía "+"), "240.1%", "38.8%" | coma decimal y signo: "+8,66%", "240,1%". Re-correr la celda ya no crea `Valores_Documento1` |

Acumulados ene-24 → sep-26 (mismo período que el IPC):

| Serie | Acumulado | | Serie | Acumulado |
|---|---:|---|---|---:|
| Vulnerable | +154,70% | | Media Alta | +168,86% |
| Popular | +146,11% | | Celíaca Media | +157,89% |
| Vegana Básica | +146,91% | | **IPC Alimentos** | **+166,35%** |
| Media | +162,77% | | IPC Nivel General | +193,65% |

Solo la Media Alta queda arriba del IPC Alimentos. Cadenas (Media, mediana por cadena, vs país): caras Jumbo +4,06%,
Disco +3,68%, La Anónima +3,23%; baratas Vea −2,03%, Carrefour −0,45%, Carrefour Market −0,21%; dispersión 6,2%. AMBA
(vs AMBA $684.682): Disco +4,02%, Jumbo +3,80%, Carrefour Express +0,73%; ChangoMas −2,23%, Carrefour −0,69%, Mi
ChangoMas −0,45%.

Test: `notebooks/test_valores_documento.py` (20 chequeos; con las CELDAS 16/18/20 viejas fallan 19).

## 4. Lecturas de los datos (no son defectos)

- **Vea bajó precios en jul-26**: 19 de sus 67 productos bajan más de 5% de junio a julio (−10% a −28%, con 3.000-4.700
  observaciones cada uno) y siguen abajo en agosto. Explica la caída de Cuyo, Noroeste, Mendoza, Salta, Tucumán, San Juan
  y San Luis en jul-26 de `analisis_detallado` (Vea pesa ahí) y el rebote de oct-26: Vea +4,05% (mediana del grupo),
  +4,33% en el panel y el mayor aporte por cadena (0,40 pp). Reproducir con `productos_que_mueven_grupo.py`.
- **La suba de octubre es casi toda arrastre**: 1,48 de los 1,75 pp ya estaban en la última semana de septiembre.
- Productos que más aportan en oct: Acondicionador Sedal 650 (+5,55%, 0,16 pp, todo arrastre), Medallón Good Mark (0,13),
  Lavandina Ayudín 2 L (+6,87%, 0,11 pp, todo suba nueva), Aromatizante Glade (0,10), Mortadela Cabaña Argentina
  (+13,5%, 0,10).
- **DIA**: índice 137,23 a oct-26 (base sep-25) contra 128,75 del Total, con 32 de los 69 productos.
- Con la mediana, muchas provincias y barrios repiten el mismo valor (Corrientes, Entre Ríos y Santa Fe $288.683 en la
  Vulnerable; ~20 barrios en el precio de DIA): la sucursal mediana es de una cadena con precio nacional. El "bottom 3"
  de barrios por mediana es arbitrario entre empates; el análisis [promedio] los separa.

## 5. Abiertos (no corregidos; en `docs/BUGS_Y_MEJORAS.md`, "nb02 — abiertos")

- **Región de la 19b/19c = `REGION` del maestro**, que marca AMBA a ~100 sucursales de DIA del interior bonaerense (Mar
  del Plata, Tandil, Pergamino; localidad "BUENOS AIRES"): el AMBA de `analisis_detallado` (1.819 sucursales) las
  incluye. Arreglarlo cambia la clave del caché de la 19c (relee 12 meses, ~35 min una vez). Ver
  `validar_amba_maestro.py`.
- **~540 sucursales fuera del maestro** (2.959 en el panel de la 19b, 2.419 en el maestro): no entran al Cuadro 1, mapas
  ni rankings. La mayor es "Cadena 24" (332 sucursales, 9 de 69 productos: perfil de farmacia/perfumería, sin
  identificar); Carrefour Express tiene 511 sucursales en la 19c y 386 en el Cuadro 1; Toledo 27 y 13.
- **Cadenas con 2-9 productos** en la 19c (Cadena 24, 23, 6): falta un mínimo de productos además del de sucursales.
- **Provincia distinta según la hoja**: la 19b/19c usan el código ISO del archivo de precios (CABA 1.131 sucursales) y el
  Cuadro 1 el maestro con reclasificación por coordenadas (CABA 834). No comparar cantidades de sucursales entre hojas.
- **Barrios por rectángulos superpuestos** (gana el primero del diccionario): Palermo (73) y Belgrano (69) absorben
  vecinos; Colegiales, Retiro, Villa Luro y Villa Riachuelo quedan con ≤ 1 sucursal. Arreglo: polígonos oficiales.
- Trazabilidad: "EANs en canastas activas (229 únicos)" son 229 de 256; 27 EANs de las canastas no están en Candidatos
  y no tienen control. Erratas en descripciones de candidatos ("Trega", "Boldoen", "La Virgina").
- El **nb05** tiene el mismo AMBA = CABA + provincia (tarjeta de sesión propuesta el 2026-10-16).

## 6. Cómo reproducir

Scripts en `docs/auditoria/scripts_nb02_2026-10/` (los insumos no están en el repo):

```bash
python -I docs/auditoria/scripts_nb02_2026-10/simular_valores_documento.py . <canasta_analisis_2026-10.xlsx> <carpeta>
python -I docs/auditoria/scripts_nb02_2026-10/validar_amba_maestro.py data/maestro_sucursales_completo.xlsx
python -I docs/auditoria/scripts_nb02_2026-10/productos_que_mueven_grupo.py <detalle_ea281ee7_v1.parquet> cadena Vea 2026-06 2026-07
python notebooks/test_valores_documento.py
```

## 7. Próximo paso

Re-correr el nb02 en Colab ("Ejecutar todo": los cachés de la serie, de la 19c y de econometría están al día, no relee
el histórico) y comparar la salida de la CELDA 20 con el §3. Si el mes ya cerró, los números cambian (mes completo) pero
las comprobaciones son las mismas: AMBA sin Toledo/Cooperativa Obrera, acumulados hasta el último mes con IPC, P5-P95,
porcentajes con coma.
