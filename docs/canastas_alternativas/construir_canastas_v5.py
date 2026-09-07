#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CONSTRUCTOR DE LAS CANASTAS v5  —  precios_minoristas_supermercados / notebook 07
================================================================================
Genera, de forma reproducible y auditable:

  * `cargar_canastas_v5.py`   loader de Colab que escribe cantidad_01..06 en la hoja
                              `Productos unicos` del Excel de nb01.
  * `canastas_v5_detalle.csv` una fila por (necesidad, canasta, EAN elegido) con el
                              precio unitario, la cobertura y el porque de la eleccion.
  * `frescos_v5_qty.txt`      las tuplas `qty` para pegar en TIPOS_FRESCOS de gen_nb07.py.

--------------------------------------------------------------------------------
POR QUE SE REHIZO (diagnostico de la corrida 2026-08-27)
--------------------------------------------------------------------------------
Las canastas v4 se movian casi identicas entre si (correlacion de variaciones
semanales Media-Ejecutiva = 0,962; Media-Representativa = 0,951). No era ruido: era
la construccion. Medido sobre el gasto de la corrida real:

    Media comparte el 100,0% de su gasto con Representativa   (Media estaba CONTENIDA)
    Media comparte el  82,6% de su gasto con Ejecutiva
    el 91% de los tipos frescos de Popular son los mismos que los de Ejecutiva
    solo 21 de los 66 empaquetados de Popular NO estaban tambien en Ejecutiva

Es decir: eran la misma canasta a distinta escala. Un indice construido sobre los
mismos EANs no puede mostrar inflacion distinta por nivel socioeconomico, porque
literalmente usa la misma serie de precios.

--------------------------------------------------------------------------------
QUE HACE ESTA VERSION DISTINTO
--------------------------------------------------------------------------------
1. NECESIDADES, no productos. Cada canasta cubre el mismo conjunto de necesidades
   (`NEEDS`), pero cada estrato elige SU version del producto: Popular el primer
   precio, Media la marca lider, Ejecutiva la premium. Popular y Ejecutiva ya no
   comparten EANs salvo donde el mercado no ofrece alternativa.

2. CANTIDADES FISICAS, no unidades. v4 declaraba "2 unidades/mes" sin mirar el
   envase, asi que una botella de 900 ml y una de 1,5 L contaban igual. Ahora se
   declara la cantidad FISICA (kg / litros / unidades) y el loader calcula
   `cantidad = round(cantidad_fisica / presentacion_del_EAN)`. Cambiar de envase ya
   no cambia la canasta.

3. ANCLADAS A LA CBA DEL INDEC, hogar tipo 2. El nucleo alimentario replica la
   composicion oficial de la canasta basica alimentaria (ver `CBA_AE`), escalada por
   3,09 adultos equivalentes. Fuente: INDEC, "Canasta basica alimentaria y canasta
   basica total. Preguntas frecuentes", Notas al pie N.o 3, junio 2020, cuadro
   "Composicion de la canasta para el adulto equivalente" (p. 13) y ejemplo de hogar
   de 4 integrantes = 3,09 adultos equivalentes (p. 9).
   Esto corrigio dos faltantes grandes de v4: pan 8 kg/mes contra 20,9 de la CBA, y
   papa 8 kg contra 20,1.

4. ESCALONAMIENTO CONTROLADO POR UNIDAD COMPARABLE. El tier se decide sobre el
   precio POR KILO (o por litro / por unidad de uso), no sobre el precio del envase.
   Sin esto, "el mas barato" seria siempre el paquete mas chico.

--------------------------------------------------------------------------------
ADVERTENCIA HONESTA SOBRE LO QUE ESTO PUEDE Y NO PUEDE LOGRAR
--------------------------------------------------------------------------------
El escalonamiento por marca separa bien los NIVELES de precio, pero NO va a producir
tasas de inflacion muy distintas entre estratos: dentro de una misma necesidad las
marcas se mueven casi en paralelo. Medido en agosto de 2026 sobre aceite de girasol
900 ml: Dia $3.645 / Cañuelas $4.115 / Cocinero $4.339 / Natura $4.637 — un rango de
27% en nivel, con trayectorias muy parecidas.
La diferencia real de INFLACION entre estratos viene de la COMPOSICION entre rubros
(efecto Engel), no de la marca. Eso ya se veia en los datos de v4 pese al problema de
anidamiento: Popular acumulaba +186,5% contra Media +171,8% entre 2024-01 y 2026-08,
porque Popular pesa mas Carne (17,8% contra 12,3%) y Verduras (12,7% contra 9,5%).
v5 conserva y acentua esa diferencia de composicion, que es la que tiene contenido
economico.

--------------------------------------------------------------------------------
USO
--------------------------------------------------------------------------------
    python construir_canastas_v5.py --excel ruta/al/canasta_representativa_YYYY-MM.xlsx

Se corre LOCAL (no en Colab) cada vez que se quiera recalibrar la composicion contra
un periodo de referencia nuevo. El archivo que produce (`cargar_canastas_v5.py`) es
el que se pega en Colab.
"""

import argparse
import os
import re
import sys
import unicodedata
from datetime import date

import numpy as np
import pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))

# ══════════════════════════════════════════════════════════════════════════════
# 1. ANCLA OFICIAL — CBA del INDEC, gramos por adulto equivalente y por mes
# ══════════════════════════════════════════════════════════════════════════════
# Transcripcion literal del cuadro "Canasta basica alimentaria. Composicion de la
# canasta para el adulto equivalente" (INDEC, Notas al pie N.o 3, junio 2020, p. 13).
# Se guarda completo aunque no todos los componentes tengan un slot propio: sirve de
# control de cobertura nutricional y deja explicito que se cubre y que no.
CBA_AE = {
    'Pan':                    6750,   # g
    'Galletitas de agua':      420,
    'Galletitas dulces':       210,
    'Arroz':                  1200,
    'Harina de trigo':        1080,
    'Otras harinas (maiz)':    210,
    'Fideos':                 1740,
    'Papa':                   6510,
    'Batata':                  510,
    'Azucar':                 1230,
    'Dulces':                  330,
    'Legumbres secas':         240,
    'Hortalizas':             5730,   # acelga, cebolla, lechuga, tomate, zanahoria, zapallo
    'Frutas':                 4950,
    'Carnes':                 6270,   # incluye pollo y pescado
    'Menudencias':             270,
    'Fiambres':                 60,
    'Huevos':                  600,
    'Leche':                  9270,
    'Queso':                   330,
    'Yogur':                   570,
    'Manteca':                  60,
    'Aceite':                 1200,
    'Bebidas no alcoholicas': 3450,   # cc
    'Bebidas alcoholicas':    1080,   # cc
    'Sal fina':                120,
    'Condimentos':             120,
    'Vinagre':                  60,
    'Cafe':                     30,
    'Yerba':                   510,
}
# Hogar tipo 2 del INDEC: varon 35 (1,00) + mujer 31 (0,77) + hijo 6 (0,64) + hija 8 (0,68).
ADULTOS_EQUIV = 3.09
HOGAR_REF = 'hogar tipo 2 (2 adultos + 2 ninos) = 3,09 adultos equivalentes'


def cba_hogar(componente):
    """Cantidad mensual del componente de la CBA para el hogar de referencia, en kg/L."""
    return CBA_AE[componente] * ADULTOS_EQUIV / 1000.0


# ══════════════════════════════════════════════════════════════════════════════
# 2. REGLAS DE COBERTURA POR CANASTA
# ══════════════════════════════════════════════════════════════════════════════
# Popular baja el umbral a proposito: el primer precio y la marca propia no existen en
# 4 cadenas (por definicion, la marca propia vive en una). Sin bajarlo no hay estrato
# Popular real, solo "la marca lider en envase chico". El costo de bajarlo se declara
# item por item en la columna `cadenas` del detalle y en la hoja Cobertura_emp de nb07.
# CORREGIDO EN LA CORRIDA 2026-08-27: el umbral relajado de Popular (>=2 cadenas / >=600
# sucursales) parecia razonable en abstracto y DESTRUYO el indice en la practica. Lo que pasa
# es que el percentil 10 aterriza sistematicamente en la marca propia, y la marca propia vive
# en una sola cadena: 11 de los 60 productos de Popular quedaron con ~550 sucursales y 3
# cadenas, todos Carrefour. Como nb07 solo cotiza una sucursal si tiene >=80% de los items de
# la canasta (FRAC_PRODUCTOS_MIN), la canasta Popular paso a cotizar en 85 sucursales de 3.070
# (contra 1.969 en v4) y su unica cadena era Carrefour. Un indice que se calcula en 85
# sucursales de una cadena no es un indice nacional, por representativo que sea el surtido.
#
# Conclusion: el estrato Popular tiene que salir de la marca MAS BARATA CON PRESENCIA
# NACIONAL (Canuelas, Legitimo, Maximo, Vanguardia, Plusbelle, Manaos, Marolio...), no de la
# marca propia. Se pierde algo de amplitud entre tiers y se gana un indice medible.
COBERTURA = {
    'Popular':        dict(cadenas=4, provincias=15, sucursales=800),
    'Media':          dict(cadenas=4, provincias=15, sucursales=800),
    'Ejecutiva':      dict(cadenas=4, provincias=15, sucursales=800),
    'Representativa': dict(cadenas=4, provincias=15, sucursales=800),
    'Femenina':       dict(cadenas=4, provincias=15, sucursales=700),
    'Tecnologica':    dict(cadenas=3, provincias=10, sucursales=90),
}
# Piso ABSOLUTO: por debajo de esto no se acepta ningun producto, y la necesidad se descarta
# para esa canasta en vez de meter un item que solo cotiza en 400 sucursales. La escalera de
# relajacion anterior ([1.0, 0.6, 0.35]) llegaba hasta 250 sucursales y ahi se colaron los
# items que hundieron la cobertura de Ejecutiva (23 de 78 por debajo de 800).
PISO_ABSOLUTO = dict(cadenas=3, provincias=12, sucursales=700)
# Percentil del precio unitario (dentro de la necesidad) que define cada tier.
TIER_PCT = {'Popular': 0.10, 'Media': 0.45, 'Ejecutiva': 0.80}

CANASTAS = ['Popular', 'Media', 'Ejecutiva', 'Tecnologica', 'Representativa', 'Femenina']
SLOTS_COL = {'Popular': 'cantidad_01', 'Media': 'cantidad_02', 'Ejecutiva': 'cantidad_03',
             'Tecnologica': 'cantidad_04', 'Representativa': 'cantidad_05', 'Femenina': 'cantidad_06'}


# ══════════════════════════════════════════════════════════════════════════════
# 3. FRESCOS — reparto de los totales de la CBA entre los tipos de balanza
# ══════════════════════════════════════════════════════════════════════════════
# nb07 cotiza los frescos por TIPO (regla de nombre en TIPOS_FRESCOS), no por EAN,
# porque el codigo de balanza cambia entre cadenas. Entonces el escalonamiento en
# frescos no puede ser por marca: se hace por CORTE / VARIEDAD, que es como se
# diferencia realmente el consumo. Popular carga el gasto en los cortes de olla
# (falda, puchero, osobuco, paleta, picada); Ejecutiva en los cortes caros (lomo,
# bife de chorizo, peceto). En v4 el 91% de los tipos era compartido.
#
# Cada tipo declara un peso relativo por estrato; despues se normaliza para que la
# suma del rubro de exactamente el total de la CBA asignado a ese estrato.
PESOS_FRESCOS = {
    # tipo: (Popular, Media, Ejecutiva, Representativa)
    # ---- FRUTAS ----
    'Banana':          (4.0, 3.0, 2.0, 3.0),
    'Manzana':         (2.0, 2.5, 2.5, 2.5),
    'Naranja':         (3.0, 2.5, 2.0, 2.5),
    'Mandarina':       (2.0, 1.5, 1.0, 1.5),
    'Limon':           (0.5, 0.5, 0.7, 0.5),
    'Pera':            (1.0, 1.5, 1.5, 1.5),
    'Frutilla':        (0.0, 0.5, 1.2, 0.4),
    'Uva':             (0.0, 0.7, 1.3, 0.5),
    'Durazno':         (0.3, 0.8, 1.0, 0.7),
    'Ciruela':         (0.0, 0.5, 0.8, 0.4),
    'Kiwi':            (0.0, 0.3, 0.8, 0.2),
    'Palta':           (0.0, 0.4, 1.2, 0.3),
    'Pomelo':          (0.0, 0.4, 0.6, 0.3),
    'Anana':           (0.0, 0.4, 0.9, 0.3),
    # ---- VERDURAS (sin papa ni batata: van aparte, como en la CBA) ----
    'Tomate':          (2.5, 3.0, 3.0, 3.0),
    'Cebolla':         (3.0, 2.5, 2.0, 2.5),
    'Zanahoria':       (2.0, 2.0, 1.8, 2.0),
    'Zapallo':         (2.5, 2.0, 1.5, 2.0),
    'Lechuga':         (1.0, 1.3, 1.6, 1.3),
    'Morron':          (0.4, 0.8, 1.3, 0.7),
    'Acelga':          (0.8, 0.8, 0.6, 0.8),
    'Espinaca':        (0.2, 0.5, 0.9, 0.4),
    'Choclo':          (0.5, 0.6, 0.7, 0.6),
    'Brocoli':         (0.0, 0.4, 1.0, 0.3),
    'Ajo':             (0.2, 0.2, 0.3, 0.2),
    'Zapallito':       (0.8, 0.8, 0.8, 0.8),
    'Berenjena':       (0.0, 0.5, 0.9, 0.4),
    'Repollo':         (0.8, 0.5, 0.4, 0.5),
    'Chaucha':         (0.2, 0.4, 0.6, 0.3),
    'Remolacha':       (0.3, 0.4, 0.5, 0.4),
    'Pepino':          (0.0, 0.3, 0.6, 0.2),
    # ---- CARNE VACUNA + POLLO + CERDO + PESCADO (un solo total: "Carnes" de la CBA) ----
    'Asado':           (2.0, 2.0, 2.2, 2.0),
    'Carne picada':    (3.0, 2.2, 1.5, 2.5),
    'Nalga/Cuadril':   (0.8, 1.5, 2.2, 1.5),
    'Milanesa carne':  (1.0, 1.2, 1.2, 1.2),
    'Matambre':        (0.2, 0.5, 0.9, 0.4),
    'Vacio':           (0.2, 0.6, 1.1, 0.5),
    'Osobuco':         (1.0, 0.5, 0.2, 0.6),
    'Roast beef':      (0.3, 0.6, 0.9, 0.5),
    'Bife de chorizo': (0.0, 0.6, 1.6, 0.5),
    'Lomo':            (0.0, 0.2, 1.2, 0.2),
    'Paleta':          (1.5, 0.8, 0.4, 1.0),
    'Falda/Puchero':   (1.8, 0.8, 0.3, 1.0),
    'Pollo':           (4.0, 3.2, 2.5, 3.5),
    'Suprema/Pechuga': (0.5, 1.2, 2.0, 1.0),
    'Bondiola':        (0.2, 0.5, 1.0, 0.4),
    'Pechito/Costilla cerdo': (0.5, 0.6, 0.8, 0.6),
    'Carre de cerdo':  (0.2, 0.4, 0.6, 0.3),
    'Merluza':         (0.4, 0.6, 1.0, 0.5),
    # ---- FIAMBRES Y QUESOS de balanza ----
    # La CBA separa "Queso" (330 g/AE) de "Fiambres" (60 g/AE). Se respetan los dos
    # totales, pero se admite que el consumo real de fiambre supera holgadamente el
    # minimo de subsistencia de la CBA, sobre todo en los estratos altos.
    'Queso cremoso':                    (1.2, 1.2, 1.0, 1.2),
    'Queso barra/Dambo':                (0.5, 0.8, 1.0, 0.8),
    'Queso rallar (sardo/reggianito)':  (0.2, 0.5, 0.9, 0.4),
    'Jamon cocido (kg)':                (0.8, 1.0, 1.2, 1.0),
    'Salame/Salamin':                   (0.2, 0.5, 1.0, 0.4),
    'Mortadela':                        (1.0, 0.5, 0.2, 0.6),
}
# Totales fisicos por rubro y estrato (kg/mes del hogar de referencia).
# Representativa = CBA exacta. Los otros se apartan por efecto Engel: el estrato bajo
# carga en carbohidratos y cortes de olla, el alto en frutas, lacteos y cortes caros.
# El apartamiento es MODERADO a proposito: Engel dice que la CANTIDAD de alimento
# satura con el ingreso y lo que crece es la CALIDAD, que aca la captura el tier.
TOTALES_FRESCOS = {
    #                     Popular  Media  Ejecutiva  Representativa
    'Frutas':             (11.0,   16.0,   21.0,   cba_hogar('Frutas')),
    'Verduras':           (15.0,   18.0,   21.0,   cba_hogar('Hortalizas')),
    'Carnes':             (18.0,   20.0,   23.0,   cba_hogar('Carnes')),
    'Fiambres y Quesos':  ( 1.6,    2.6,    3.8,   cba_hogar('Queso') + cba_hogar('Fiambres')),
}
RUBRO_DE_TIPO = {}
for _t in ['Banana', 'Manzana', 'Naranja', 'Mandarina', 'Limon', 'Pera', 'Frutilla', 'Uva',
           'Durazno', 'Ciruela', 'Kiwi', 'Palta', 'Pomelo', 'Anana']:
    RUBRO_DE_TIPO[_t] = 'Frutas'
for _t in ['Tomate', 'Cebolla', 'Zanahoria', 'Zapallo', 'Lechuga', 'Morron', 'Acelga', 'Espinaca',
           'Choclo', 'Brocoli', 'Ajo', 'Zapallito', 'Berenjena', 'Repollo', 'Chaucha', 'Remolacha',
           'Pepino']:
    RUBRO_DE_TIPO[_t] = 'Verduras'
for _t in ['Asado', 'Carne picada', 'Nalga/Cuadril', 'Milanesa carne', 'Matambre', 'Vacio',
           'Osobuco', 'Roast beef', 'Bife de chorizo', 'Lomo', 'Paleta', 'Falda/Puchero',
           'Pollo', 'Suprema/Pechuga', 'Bondiola', 'Pechito/Costilla cerdo', 'Carre de cerdo',
           'Merluza']:
    RUBRO_DE_TIPO[_t] = 'Carnes'
for _t in ['Queso cremoso', 'Queso barra/Dambo', 'Queso rallar (sardo/reggianito)',
           'Jamon cocido (kg)', 'Salame/Salamin', 'Mortadela']:
    RUBRO_DE_TIPO[_t] = 'Fiambres y Quesos'

# Tipos que no entran en un total de rubro: se declaran directo (CBA los lista aparte).
FRESCOS_DIRECTOS = {
    #  tipo:            (Popular, Media, Ejecutiva, Representativa)   unidad
    'Papa':             (22.0, 18.0, 14.0, cba_hogar('Papa')),
    'Batata':           ( 1.5,  1.5,  1.5, cba_hogar('Batata')),
    'Pan frances':      (18.0, 15.0, 11.0, cba_hogar('Pan') * 0.85),   # 15% del pan va a pan de molde
    # CBA: 600 g/AE de huevo. A 60 g por huevo (0,06 kg) da 30,9 huevos = 2,58 docenas.
    'Huevos':           ( 3.0,  3.0,  3.0, cba_hogar('Huevos') / 0.06 / 12),
}


def repartir_frescos():
    """Devuelve {tipo: (qty_pop, qty_med, qty_eje, qty_rep)} en kg (o docenas para huevos)."""
    out = {}
    for tipo, pesos in PESOS_FRESCOS.items():
        rub = RUBRO_DE_TIPO[tipo]
        fila = []
        for i in range(4):
            suma = sum(PESOS_FRESCOS[t][i] for t in PESOS_FRESCOS if RUBRO_DE_TIPO[t] == rub)
            total = TOTALES_FRESCOS[rub][i]
            fila.append(round(total * pesos[i] / suma, 2) if suma > 0 else 0.0)
        out[tipo] = tuple(fila)
    for tipo, q in FRESCOS_DIRECTOS.items():
        out[tipo] = tuple(round(x, 2) for x in q)
    return out


# ══════════════════════════════════════════════════════════════════════════════
# 4. NECESIDADES EMPAQUETADAS
# ══════════════════════════════════════════════════════════════════════════════
# Cada entrada define UNA necesidad. `sub` recorta el universo por subcategoria del
# maestro; `inc`/`exc` lo afinan hasta que todos los candidatos sean SUSTITUTOS entre
# si (sin esto el escalonamiento por percentil elige productos distintos en vez de
# versiones distintas del mismo producto: probado, en "Leche entera" el percentil 80
# devolvia leche EN POLVO, y en "Pasta dental" devolvia pasta dental infantil).
# `u`   : unidad fisica de `qty`:
#           'kg'   -> usa los gramos/ml del envase; qty en kg o litros
#           'un'   -> qty en unidades de uso; el envase TIENE que declarar cuantas trae
#           'pack' -> qty en paquetes; el conteo del envase se ignora (para productos donde
#                     "un paquete" es la unidad natural de compra: algodon, tintura, esponja)
# `qty` : cantidad fisica mensual del hogar de referencia (Popular, Media, Ejecutiva,
#         Representativa). None en una posicion = la necesidad no entra en esa canasta.
# `cba` : componente de la CBA que ancla la cantidad (documental; '' = fuera de CBA).
N = None
NEEDS = {
    # ─────────────────────────── ALMACEN — nucleo CBA ───────────────────────────
    'Arroz': dict(sub='Arroz Largo', inc=r'\barroz\b', exc=r'integral|preparad|risotto|condiment|barrit|snack|leche|postre',
                  u='kg', qty=(4.0, 3.5, 3.0, cba_hogar('Arroz')), cba='Arroz'),
    'Fideos secos': dict(sub='Pastas Secas', inc=r'fideo|spaghetti|spagueti|tallarin|mostachol|penne|codito|munici|tirabuz|farfalle|rigati',
                         exc=r'sin tacc|libre de gluten|integral|salsa|instant|vaso|sopa',
                         u='kg', qty=(6.0, 5.0, 4.0, cba_hogar('Fideos')), cba='Fideos'),
    'Harina de trigo': dict(sub='Harina de Trigo', inc=r'harina', exc=r'integral|leudante|pizza|premezcla|sin tacc|garbanzo|almendra',
                            u='kg', qty=(4.0, 3.0, 2.0, cba_hogar('Harina de trigo')), cba='Harina de trigo'),
    'Harina de maiz / polenta': dict(sub='Harina de Maíz', inc=r'polenta|harina de ma[ií]z', exc=r'instant.*vaso|snack',
                                     u='kg', qty=(0.9, 0.6, 0.4, cba_hogar('Otras harinas (maiz)')), cba='Otras harinas (maiz)'),
    'Azucar': dict(sub='Azúcar', inc=r'az[uú]car', exc=r'light|edulcor|mascabo|impalpable|sin tacc',
                   u='kg', qty=(4.0, 3.5, 2.5, cba_hogar('Azucar')), cba='Azucar'),
    'Aceite de girasol': dict(sub='Aceite de Girasol', inc=r'aceite de girasol', exc=r'aerosol|spray|mezcla|blend|alto oleico',
                              u='kg', qty=(3.7, 3.2, 2.6, cba_hogar('Aceite')), cba='Aceite'),
    'Aceite de oliva': dict(sub='Aceite de Oliva', inc=r'aceite de oliva', exc=r'aerosol|spray|saboriz',
                            u='kg', qty=(N, 0.3, 0.7, 0.25), cba=''),
    'Legumbres secas': dict(sub='Legumbres', inc=r'lenteja|poroto|garbanz|arveja', exc=r'lata|conserva|remojad|snack|harina',
                            u='kg', qty=(0.9, 0.7, 0.5, cba_hogar('Legumbres secas')), cba='Legumbres secas'),
    'Tomate envasado': dict(sub='Tomates y Salsas', inc=r'tomate.*(perita|triturad|entero|pulpa|pur[eé])|pur[eé] de tomate',
                            exc=r'salsa lista|ketchup|fileto|listo para|condiment',
                            u='kg', qty=(2.4, 2.2, 2.0, 2.2), cba='Hortalizas'),
    'Arvejas en lata': dict(sub='Conservas de Verdura y Legumbres', inc=r'arveja', exc=r'snack|congel|partida',
                            u='kg', qty=(0.9, 0.9, 0.9, 0.9), cba='Hortalizas'),
    'Sal fina': dict(sub='Sal y Pimienta', inc=r'\bsal\b', exc=r'pimienta|gruesa|marina|parrill|apio|ajo|light|dietetic|saboriz|entrefina',
                     u='kg', qty=(0.4, 0.35, 0.3, cba_hogar('Sal fina')), cba='Sal fina'),
    'Condimentos secos': dict(sub='Otros Condimentos', inc=r'or[eé]gano|piment[oó]n|comino|provenzal|ají molido',
                              exc=r'aderez|salsa|mayonesa', u='kg', qty=(0.06, 0.08, 0.10, 0.07), cba='Condimentos'),
    'Caldo concentrado': dict(sub='Caldos', inc=r'caldo', exc=r'liquido|listo',
                              u='kg', qty=(0.12, 0.12, 0.10, 0.12), cba='Condimentos'),
    'Mayonesa': dict(sub='Mayonesas', inc=r'mayonesa', exc=r'light.*sachet|salsa golf',
                     u='kg', qty=(0.30, 0.45, 0.60, 0.35), cba='Condimentos'),
    'Vinagre': dict(sub='Vinagre', inc=r'vinagre', exc=r'aceto|balsam',
                    u='kg', qty=(0.2, 0.2, 0.2, cba_hogar('Vinagre')), cba='Vinagre'),
    'Yerba mate': dict(sub='Yerbas', inc=r'yerba', exc=r'mate cocido|saquit|compuest.*energ|suplement',
                       u='kg', qty=(2.0, 1.7, 1.3, cba_hogar('Yerba')), cba='Yerba'),
    'Cafe': dict(sub='Café', inc=r'caf[eé]', exc=r'capsul|c[aá]psul|descafein|saboriz|listo|frap|crema|azucar',
                 u='kg', qty=(0.06, 0.16, 0.35, cba_hogar('Cafe')), cba='Cafe'),
    'Te': dict(sub='Té', inc=r'saquit|\bt[eé]\b', exc=r'helado|listo|matcha|infusi[oó]n frut|premium|gourmet|org[aá]nic|adelgaz',
               u='kg', qty=(0.03, 0.05, 0.07, 0.04), cba=''),
    'Galletitas de agua': dict(sub='Galletitas Saladas', inc=r'galletit|cracker',
                               exc=r'sin tacc|libre de gluten|snack|palito|tostad|saladix|s[aá]ndwich|sandwich|rellen|queso|jam[oó]n|pizza|bocadit',
                               u='kg', qty=(1.4, 1.3, 1.1, cba_hogar('Galletitas de agua')), cba='Galletitas de agua'),
    'Galletitas dulces': dict(sub='Galletitas Dulces', inc=r'galletit',
                              exc=r'sin tacc|libre de gluten|oblea|alfajor|bañad|cubiert',
                              u='kg', qty=(0.8, 1.0, 1.2, cba_hogar('Galletitas dulces')), cba='Galletitas dulces'),
    'Pan de molde': dict(sub='Pan de Molde', inc=r'pan', exc=r'sin tacc|rallad|hamburgues|pancho|arabe|pita',
                         u='kg', qty=(0.6, 1.0, 1.4, cba_hogar('Pan') * 0.15), cba='Pan'),
    'Pan rallado': dict(sub='Pan Rallado y Rebozadores', inc=r'pan rallado|rebozador', exc=r'sin tacc|libre de gluten',
                        u='kg', qty=(0.5, 0.5, 0.5, 0.5), cba=''),
    'Dulce de leche': dict(sub='Dulce de Leche', inc=r'dulce de leche', exc=r'repostero.*5 kg|helad|alfajor',
                           u='kg', qty=(0.45, 0.50, 0.55, 0.45), cba='Dulces'),
    'Mermelada': dict(sub='Mermeladas', inc=r'mermelada|jalea', exc=r'light.*sachet|diet',
                      u='kg', qty=(0.35, 0.40, 0.45, 0.35), cba='Dulces'),
    'Cacao / chocolatada en polvo': dict(sub='Cacao', inc=r'cacao|chocolatad', exc=r'listo|leche',
                                         u='kg', qty=(0.4, 0.5, 0.6, 0.4), cba=''),
    'Cereal de desayuno': dict(sub='Cereales', inc=r'copos|aritos|cereal|granola|avena',
                               exc=r'barrit|snack|bebida', u='kg', qty=(N, 0.4, 0.8, 0.3), cba=''),
    'Alfajor': dict(sub='Alfajores', inc=r'alfajor', exc=r'sin tacc|libre de gluten',
                    u='kg', qty=(0.35, 0.40, 0.45, 0.35), cba=''),
    'Chocolate en tableta': dict(sub='Chocolates', inc=r'chocolate|tableta', exc=r'sin tacc|polvo|cobertura|bombon.*caja|licor',
                                 u='kg', qty=(N, 0.15, 0.30, 0.10), cba=''),
    'Snack salado': dict(sub='Papas Fritas', inc=r'papas fritas|snack', exc=r'congelad|prefrit',
                         u='kg', qty=(0.15, 0.25, 0.35, 0.18), cba=''),
    'Atun / conserva de pescado': dict(sub='Conservas de Pescado', inc=r'at[uú]n|caballa|sardina', exc=r'pat[eé]',
                                       u='kg', qty=(N, 0.35, 0.50, 0.30), cba=''),
    # ─────────────────────────── FRESCOS ENVASADOS (lacteos) ───────────────────
    'Leche': dict(sub='Leches', inc=r'\bleche\b', exc=r'en polvo|condensad|infantil|f[oó]rmula|chocolatad|saboriz|vegetal|almendra|soja|coco|avena|arroz',
                  u='kg', qty=(22.0, 27.0, 31.0, cba_hogar('Leche')), cba='Leche'),
    'Yogur': dict(sub='Yogures', inc=r'yogur', exc=r'griego.*pack 12|bebible.*1 lt.*pack',
                  u='kg', qty=(1.0, 2.5, 4.0, cba_hogar('Yogur')), cba='Yogur'),
    'Manteca / margarina': dict(sub='Mantecas y Margarinas', inc=r'manteca|margarina', exc=r'cacao|man[ií]',
                                u='kg', qty=(0.15, 0.25, 0.40, cba_hogar('Manteca')), cba='Manteca'),
    'Queso untable': dict(sub='Quesos Untables', inc=r'queso.*untable|untable', exc=r'vegan|tofu',
                          u='kg', qty=(0.30, 0.45, 0.60, 0.35), cba='Queso'),
    'Crema de leche': dict(sub='Crema de Leche', inc=r'crema de leche|crema', exc=r'vegetal|chantilly.*aerosol|corporal',
                           u='kg', qty=(N, 0.25, 0.45, 0.20), cba=''),
    'Salchichas': dict(sub='Salchichas', inc=r'salchicha', exc=r'vegan|soja',
                       u='kg', qty=(0.45, 0.45, 0.40, 0.45), cba='Fiambres'),
    'Pasta fresca': dict(sub='Pastas Rellenas', inc=r'ravio|sorrentin|capellet|agnolot', exc=r'sin tacc|congelad',
                         u='kg', qty=(N, 0.5, 0.9, 0.4), cba=''),
    'Tapas de empanada': dict(sub='Tapas', inc=r'tapa', exc=r'sin tacc',
                              u='kg', qty=(0.4, 0.4, 0.4, 0.4), cba=''),
    'Postre / flan': dict(sub='Postres y Flanes', inc=r'postre|flan', exc=r'polvo.*8 porciones.*caja x',
                          u='kg', qty=(N, 0.4, 0.7, 0.3), cba=''),
    # ─────────────────────────── CONGELADOS ────────────────────────────────────
    'Hamburguesas congeladas': dict(sub='Hamburguesas', inc=r'hamburgues', exc=r'vegan|soja|lenteja|pan\b',
                                    u='kg', qty=(0.4, 0.6, 0.8, 0.5), cba=''),
    'Milanesas / nuggets de pollo': dict(sub='Prefritos', inc=r'milanesa|nugget|patitas|formitas', exc=r'soja|vegan|merluza',
                                         u='kg', qty=(0.4, 0.6, 0.8, 0.5), cba=''),
    'Vegetales congelados': dict(sub='Vegetales', inc=r'', exc=r'',
                                 u='kg', qty=(N, 0.4, 0.7, 0.3), cba=''),
    # ─────────────────────────── BEBIDAS ───────────────────────────────────────
    'Gaseosa cola': dict(sub='Gaseosa Cola', inc=r'gaseosa|cola', exc=r'zero|sin az[uú]car|light|polvo',
                         u='kg', qty=(6.0, 7.0, 8.0, cba_hogar('Bebidas no alcoholicas') * 0.55), cba='Bebidas no alcoholicas'),
    'Gaseosa lima-limon': dict(sub='Gaseosa Lima Limón', inc=r'gaseosa|lima|limon|sprite|seven', exc=r'zero|sin az[uú]car|light|polvo',
                               u='kg', qty=(2.5, 3.0, 3.5, cba_hogar('Bebidas no alcoholicas') * 0.25), cba='Bebidas no alcoholicas'),
    'Jugo en polvo': dict(sub='En Polvo', inc=r'jugo|refresco', exc=r'gelatin|flan|postre',
                          u='kg', qty=(0.20, 0.15, 0.10, 0.15), cba='Bebidas no alcoholicas'),
    'Agua mineral': dict(sub='Agua sin Gas', inc=r'agua', exc=r'saboriz|t[oó]nica|gas\b',
                         u='kg', qty=(6.0, 10.0, 14.0, cba_hogar('Bebidas no alcoholicas') * 0.20), cba='Bebidas no alcoholicas'),
    'Agua saborizada': dict(sub='Agua Saborizada', inc=r'agua', exc=r'',
                            u='kg', qty=(N, 4.0, 8.0, 3.0), cba=''),
    'Cerveza': dict(sub='Rubias', inc=r'cerveza', exc=r'sin alcohol|artesanal.*growler',
                    u='kg', qty=(2.0, 3.0, 4.5, cba_hogar('Bebidas alcoholicas') * 0.6), cba='Bebidas alcoholicas'),
    'Vino': dict(sub='Tintos', inc=r'vino', exc=r'espumant|champ|cocina|vinagre',
                 u='kg', qty=(1.0, 1.5, 2.25, cba_hogar('Bebidas alcoholicas') * 0.4), cba='Bebidas alcoholicas'),
    'Aperitivo / fernet': dict(sub='Aperitivos', inc=r'', exc=r'',
                               u='kg', qty=(N, 0.75, 1.5, 0.5), cba=''),
    # ─────────────────────────── LIMPIEZA ──────────────────────────────────────
    'Detergente de vajilla': dict(sub='Detergentes', inc=r'detergente', exc=r'ropa|lavarropas|maquina',
                                  u='kg', qty=(1.5, 1.8, 2.2, 1.6), cba=''),
    'Jabon liquido para ropa': dict(sub='Jabones liquidos', inc=r'jab[oó]n l[ií]quido|l[ií]quido para ropa|ropa',
                                    exc=r'manos|tocador|[ií]ntim|diluir|concentrad|super concentrad',
                                    u='kg', qty=(2.0, 3.0, 4.0, 2.5), cba=''),
    'Jabon en polvo': dict(sub='Jabón en Polvo', inc=r'jab[oó]n|polvo', exc=r'',
                           u='kg', qty=(1.5, 1.0, 0.5, 1.2), cba=''),
    'Jabon en pan': dict(sub='Jabón en Pan', inc=r'jab[oó]n', exc=r'tocador|glicerina.*facial',
                         u='kg', qty=(0.6, 0.4, 0.2, 0.5), cba=''),
    'Suavizante': dict(sub='Suavizante', inc=r'suavizante', exc=r'',
                       u='kg', qty=(N, 1.5, 2.5, 1.2), cba=''),
    'Lavandina': dict(sub='Lavandina Líquida', inc=r'lavandina', exc=r'gel|espesa.*perfum',
                      u='kg', qty=(3.0, 3.0, 2.5, 3.0), cba=''),
    'Limpiador de pisos': dict(sub='Limpiadores Piso', inc=r'limpiador|piso|desinfect', exc=r'ba[ñn]o',
                               u='kg', qty=(1.5, 2.0, 2.5, 1.8), cba=''),
    'Desinfectante de bano': dict(sub='Desinfectantes de Baño', inc=r'', exc=r'',
                                  u='kg', qty=(N, 0.7, 1.0, 0.6), cba=''),
    'Papel higienico': dict(sub='Papel Higiénico', inc=r'papel higi[eé]nico', exc=r'humed',
                            u='un', qty=(16.0, 20.0, 24.0, 18.0), cba=''),
    'Rollo de cocina': dict(sub='Rollo de Cocina', inc=r'rollo|cocina', exc=r'',
                            u='pack', qty=(N, 3.0, 5.0, 2.0), cba=''),
    'Servilletas': dict(sub='Servilletas', inc=r'servilleta', exc=r'',
                        u='un', qty=(140.0, 210.0, 280.0, 175.0), cba=''),
    'Bolsas de residuo': dict(sub='Bolsas y Films', inc=r'bolsa.*residuo|residuo|consorcio', exc=r'film|aluminio',
                              u='un', qty=(30.0, 40.0, 50.0, 35.0), cba=''),
    'Esponja / trapo': dict(sub='Esponjas y Guantes', inc=r'esponja|virul|fibra', exc=r'guante',
                            u='pack', qty=(2.0, 3.0, 4.0, 2.5), cba=''),
    'Insecticida': dict(sub='Moscas y Mosquitos', inc=r'', exc=r'',
                        u='kg', qty=(N, 0.36, 0.50, 0.30), cba=''),
    # ─────────────────────────── PERFUMERIA ────────────────────────────────────
    'Shampoo': dict(sub='Shampoo', inc=r'shampoo|sh[aá]mpoo', exc=r'seco|beb[eé]|infantil|perro|gato|anticasp.*medicad',
                    u='kg', qty=(0.8, 1.0, 1.3, 0.9), cba=''),
    'Acondicionador': dict(sub='Acondicionador', inc=r'acondicionador', exc=r'beb[eé]|infantil|aire|ropa',
                           u='kg', qty=(0.4, 0.8, 1.2, 0.6), cba=''),
    'Jabon de tocador': dict(sub='Jabones', inc=r'jab[oó]n', exc=r'ropa|polvo|lavarropas|l[ií]quido|liquido|[ií]ntim|intim|dermatol[oó]gic|medicinal',
                             u='kg', qty=(0.5, 0.6, 0.8, 0.55), cba=''),
    'Pasta dental': dict(sub='Crema Dental', inc=r'crema dental|pasta dental|dent[ií]frico',
                         exc=r'infantil|ni[ñn]os|kids|paw patrol|frozen|spiderman|prot[eé]sis',
                         u='kg', qty=(0.25, 0.30, 0.36, 0.28), cba=''),
    'Cepillo dental': dict(sub='Cepillos Dentales', inc=r'cepillo', exc=r'infantil|ni[ñn]os|kids|el[eé]ctric|prot[eé]sis|dr rabbit|barbie|frozen|spiderman|batman',
                           u='un', qty=(1.0, 1.5, 2.0, 1.2), cba=''),
    'Desodorante': dict(sub='Desodorante Hombre', inc=r'desodorante|antitranspir', exc=r'ambiente|pie|calzado',
                        u='kg', qty=(0.30, 0.40, 0.50, 0.35), cba=''),
    'Afeitado': dict(sub='Afeitado', inc=r'm[aá]quina de afeitar|m[aá]quina afeitar|prestobarba|repuesto|cartucho|rasuradora',
                     exc=r'el[eé]ctric|depilad|femenin|venus|mujer|soleil|women|espuma|\bgel\b|crema|loci[oó]n|after',
                     u='un', qty=(2.0, 3.0, 4.0, 2.5), cba=''),
    'Crema corporal': dict(sub='Cremas Corporales', inc=r'crema|loci[oó]n|humectante', exc=r'facial|antiarrug|solar|pa[ñn]al',
                           u='kg', qty=(N, 0.4, 0.8, 0.3), cba=''),
    'Algodon / hisopos': dict(sub='Algodones e Hisopos', inc=r'', exc=r'',
                              u='pack', qty=(1.0, 1.5, 2.0, 1.2), cba=''),
    'Toallitas femeninas': dict(sub='Toallitas Higiénicas', inc=r'toallit|toalla', exc=r'humed|beb[eé]|adulto|nocturn.*pack 6',
                                u='un', qty=(16.0, 20.0, 24.0, 18.0), cba=''),
    # ─────────────────────────── BEBES Y MASCOTAS ──────────────────────────────
    'Panales': dict(sub='Cambio de Pañales', inc=r'pa[ñn]al', exc=r'adulto|humed|toallit',
                    u='un', qty=(N, 90.0, 120.0, 80.0), cba=''),
    'Toallitas humedas': dict(sub='Cambio de Pañales', inc=r'toallit.*h[uú]med|h[uú]med', exc=r'adulto|desmaquill',
                              u='un', qty=(N, 240.0, 320.0, 200.0), cba=''),
    'Alimento para perro': dict(sub='Alimentos para Perros', inc=r'alimento|balanceado', exc=r'snack|premio|hueso|lata|sachet',
                                u='kg', qty=(3.0, 6.0, 9.0, 4.0), cba=''),
    'Alimento para gato': dict(sub='Alimentos para Gatos', inc=r'alimento|balanceado', exc=r'snack|premio|lata|sachet|piedra|arena',
                               u='kg', qty=(N, 3.0, 4.5, 2.0), cba=''),
}

# ── Canasta FEMENINA: gestion menstrual, depilacion y cuidado personal ────────
# No escalona por estrato (es una canasta tematica, no socioeconomica): usa el tier
# Media en todas sus necesidades.
NEEDS_FEMENINA = {
    'Toallas higienicas': dict(sub='Toallitas Higiénicas', inc=r'toallit|toalla', exc=r'humed|beb[eé]|adulto', u='un', qty=32.0),
    'Protectores diarios': dict(sub='Protectores Diarios', inc=r'protector', exc=r'adulto', u='un', qty=60.0),
    'Tampones': dict(sub='Tampones', inc=r'tamp[oó]n', exc=r'', u='un', qty=16.0),
    'Depilacion': dict(sub='Depilación', inc=r'', exc=r'', u='pack', qty=1.0),
    'Rasuradora femenina': dict(sub='Afeitado', inc=r'venus|femenin|mujer|soleil|women', exc=r'hombre|barba|espuma|gel', u='pack', qty=1.0),
    'Shampoo': dict(sub='Shampoo', inc=r'shampoo|sh[aá]mpoo', exc=r'seco|beb[eé]|perro|gato', u='kg', qty=0.6),
    'Acondicionador': dict(sub='Acondicionador', inc=r'acondicionador', exc=r'beb[eé]|aire|ropa', u='kg', qty=0.6),
    'Coloracion': dict(sub='Coloración', inc=r'', exc=r'', u='pack', qty=1.0),
    'Crema corporal': dict(sub='Cremas Corporales', inc=r'crema|loci[oó]n', exc=r'facial|solar', u='kg', qty=0.4),
    'Desodorante mujer': dict(sub='Desodorante Mujer', inc=r'desodorante|antitranspir', exc=r'ambiente|pie', u='kg', qty=0.35),
    'Limpieza facial': dict(sub='Limpieza Facial', inc=r'', exc=r'', u='pack', qty=1.0),
    'Hidratante facial': dict(sub='Hidratantes', inc=r'', exc=r'', u='pack', qty=1.0),
    'Algodon / discos': dict(sub='Algodones e Hisopos', inc=r'algod[oó]n|disco', exc=r'', u='pack', qty=1.5),
    'Jabon de tocador': dict(sub='Jabones', inc=r'jab[oó]n', exc=r'ropa|polvo|lavarropas', u='kg', qty=0.4),
}

# ── Canasta TECNOLOGICA: bundle de durables, un item por necesidad ────────────
# No escalona (es un bundle de referencia). La cantidad es 1 unidad, y el precio del
# bundle se lee como "cuanto cuesta equipar un hogar", no como consumo mensual.
NEEDS_TECNO = {
    'Heladera':            dict(sub='Heladeras con freezer'),
    'Lavarropas':          dict(sub='Lavarropas carga frontal'),
    'Cocina':              dict(sub='Cocinas a Gas'),
    'Aire acondicionado':  dict(sub='AA Split'),
    'Televisor':           dict(sub='TV'),
    'Notebook':            dict(sub='Notebooks'),
    'Celular':             dict(sub='Celulares'),
    'Microondas':          dict(sub='Microondas'),
    'Licuadora':           dict(sub='Licuadora de Mano / Mixer'),
    'Pava electrica':      dict(sub='Pava'),
    'Plancha':             dict(sub='Planchas'),
    'Parlante bluetooth':  dict(sub='Parlantes'),
    'Auriculares':         dict(sub='Auriculares'),
    'Calefactor':          dict(sub='Calefacción eléctrica'),
}


# ══════════════════════════════════════════════════════════════════════════════
# 5. MOTOR
# ══════════════════════════════════════════════════════════════════════════════
_RE_GR = re.compile(r'(\d+(?:[.,]\d+)?)\s*(kg|kgm|kilo|grs?|gramos?|ml|cc|lts?|litros?|g)\b')
_RE_UN = re.compile(r'(?:x\s*)?(\d+)\s*(?:un|u|unid|unidad|unidades|maple|cu|ea|rollos?|discos?|pastillas?)\b')


def _to_gramos(q, u):
    q = pd.to_numeric(str(q).replace(',', '.'), errors='coerce')
    u = str(u).strip().lower()
    if pd.isna(q) or q <= 0:
        return np.nan
    if u in ('kg', 'kgm', 'kgr', 'l', 'lt', 'litro', 'litros', 'kilogramo', 'kilogramos'):
        return q * 1000
    if u in ('gr', 'g', 'grs', 'grm', 'gramo', 'gramos', 'ml', 'cc', 'mililitro'):
        return q
    return np.nan


def _gramos_desc(s):
    m = _RE_GR.search(str(s).lower())
    if not m:
        return np.nan
    v = float(m.group(1).replace(',', '.'))
    u = m.group(2)
    return v * 1000 if (u.startswith('k') or u in ('lt', 'l', 'lts', 'litro', 'litros')) else v


def _unidades_desc(s):
    m = _RE_UN.search(str(s).lower())
    if m:
        n = int(m.group(1))
        if 1 <= n <= 200:
            return float(n)
    return np.nan


def _sa(x):
    """minusculas sin acentos, para comparar nombres de tipo fresco."""
    return ''.join(c for c in unicodedata.normalize('NFD', str(x).lower())
                   if unicodedata.category(c) != 'Mn')


def cargar_universo(xlsx):
    pu = pd.read_excel(xlsx, sheet_name='Productos unicos')
    pu['ean'] = pu['id_producto'].astype(str).str.strip().str.lstrip('0')
    pu['desc'] = pu['descripcion'].fillna('').astype(str)
    pu['dlow'] = pu['desc'].str.lower()
    g1 = [_to_gramos(a, b) for a, b in zip(pu['presentacion'], pu['unidad'])]
    g2 = [_gramos_desc(x) for x in pu['desc']]
    pu['grams'] = [(a if a == a else b) for a, b in zip(g1, g2)]
    pu['unidades'] = [_unidades_desc(x) for x in pu['desc']]
    pu['subcategoria'] = pu['subcategoria'].fillna('').astype(str)
    pu['marca'] = pu['marca'].fillna('').astype(str)
    pu = pu[pu['precio_mediano'].notna() & (pu['precio_mediano'] > 0)]
    return pu


def _nogroup(rx):
    """Convierte los grupos de captura en no-capturantes (pandas avisa si hay grupos)."""
    return re.sub(r'\((?!\?)', '(?:', rx)


def candidatos(pu, cfg):
    """Candidatos de una necesidad, con `pu` = precio por unidad comparable."""
    subs = cfg['sub'] if isinstance(cfg['sub'], (list, tuple)) else [cfg['sub']]
    c = pu[pu['subcategoria'].isin(subs)].copy()
    if cfg.get('inc'):
        c = c[c['dlow'].str.contains(_nogroup(cfg['inc']), regex=True, na=False)]
    if cfg.get('exc'):
        c = c[~c['dlow'].str.contains(_nogroup(cfg['exc']), regex=True, na=False)]
    if cfg['u'] == 'kg':
        c = c[c['grams'].notna() & (c['grams'] > 0)]
        # Multipacks AMBIGUOS fuera. "Hamburguesas 4 Un 83 Gr" se leia como 83 gramos cuando el
        # paquete son 4x83 = 332, y eso metio 10 paquetes ($104.124) en la canasta Ejecutiva.
        # El formato "N Un M Gr" no distingue si M es el total o el peso por unidad, asi que no
        # se adivina: se descarta el candidato (mismo criterio que ya usa nb06).
        c = c[~(c['unidades'].notna() & (c['unidades'] >= 2))]
        c['tam'] = c['grams']
        c['pu'] = c['precio_mediano'] / c['grams'] * 1000.0     # $/kg o $/L
    elif cfg['u'] == 'pack':
        # La cantidad esta en PAQUETES: el conteo de unidades del envase es irrelevante.
        # Necesario porque "Algodon Estrella Clasico 75 Gr" no declara unidades, y con u='un'
        # el motor lo tomo como 1 unidad -> 80 paquetes de algodon por mes = $111.470, el 43%
        # de la canasta Femenina.
        c['tam'] = 1.0
        c['pu'] = c['precio_mediano']                            # $/paquete
    else:
        # u='un': la cantidad esta en unidades de uso, asi que el envase TIENE que declarar
        # cuantas trae. Si no lo declara, no se puede convertir y el candidato no sirve.
        c = c[c['unidades'].notna() & (c['unidades'] > 0)]
        c['tam'] = c['unidades']
        c['pu'] = c['precio_mediano'] / c['tam']                 # $/unidad de uso
    c = c[c['pu'].notna() & (c['pu'] > 0)]
    if len(c) >= 8:
        # Ventana de tamanos estandar: evita comparar un sobre de 12 g con un pack de 1 kg.
        # Se centra en el tamano modal de los productos con mas cobertura.
        gm = c.loc[c['n_sucursales'] >= c['n_sucursales'].quantile(0.60), 'tam'].median()
        if gm == gm and gm > 0:
            c = c[(c['tam'] >= gm / 3.0) & (c['tam'] <= gm * 3.0)]
    if len(c) >= 8:
        lo, hi = c['pu'].quantile([0.03, 0.97])   # errores de carga en las colas
        c = c[(c['pu'] >= lo) & (c['pu'] <= hi)]
    return c.sort_values('pu').reset_index(drop=True)


def elegible(c, canasta):
    r = COBERTURA[canasta]
    return ((c['n_cadenas'] >= r['cadenas']) & (c['n_provincias'] >= r['provincias'])
            & (c['n_sucursales'] >= r['sucursales']))


def elegir(c, canasta, usados, min_pu=None):
    """Elige el EAN del tier de `canasta`.

    Dos reglas que v4 no tenia y que la auditoria de la primera corrida obligo a agregar:

    (a) NUNCA se cae en un candidato que no cumple la cobertura sin decirlo. La version
        inicial hacia `pool = elegibles or todos`, y eso metio te con 98 sucursales en la
        canasta Media (cuyo piso es 800). Ahora la relajacion es explicita, por pasos, y
        queda registrada en la columna `confiable` del detalle.
    (b) MONOTONICIDAD: el precio unitario tiene que subir Popular <= Media <= Ejecutiva.
        Sin el piso `min_pu` el percentil elegia, sobre pools distintos (cada canasta
        tiene su propia regla de cobertura), un Ejecutiva mas barato que el Media — paso
        con atun ($26.292 contra $34.521) y con bolsas de residuo.
    """
    if not len(c):
        return None, False
    reglas = COBERTURA[canasta]
    if canasta == 'Tecnologica':
        piso = reglas
    else:
        piso = PISO_ABSOLUTO
    escalas = [1.0, 0.0]            # exigencia plena; si no hay, el piso absoluto; si no, nada
    for k, esc in enumerate(escalas):
        if esc == 1.0:
            _cad, _prov, _suc = reglas['cadenas'], reglas['provincias'], reglas['sucursales']
        else:
            _cad, _prov, _suc = piso['cadenas'], piso['provincias'], piso['sucursales']
        m = ((c['n_cadenas'] >= _cad) & (c['n_provincias'] >= _prov) & (c['n_sucursales'] >= _suc))
        pool = c[m]
        if not len(pool):
            continue
        tope = False
        if min_pu is not None:
            alto = pool[pool['pu'] >= min_pu * 1.02]
            if len(alto):
                pool = alto
            else:
                # El mercado no ofrece nada mas caro que el tier anterior dentro de esta
                # necesidad: se toma el techo disponible en vez de romper la monotonicidad.
                tope = True
        if tope:
            cand = pool.sort_values(['pu', 'n_sucursales'], ascending=[False, False])
        elif canasta in ('Representativa', 'Tecnologica', 'Femenina'):
            # No escalonan: usan el producto MODAL (el de mayor cobertura real). Es una
            # definicion distinta a proposito — la Representativa es la comparable con INDEC.
            cand = pool.sort_values('n_sucursales', ascending=False)
        else:
            obj = pool['pu'].quantile(TIER_PCT[canasta])
            cand = pool.assign(_d=(pool['pu'] - obj).abs()).sort_values(
                ['_d', 'n_sucursales'], ascending=[True, False])
        # Regla general: cada estrato usa un EAN distinto. Excepcion: cuando ya estamos en
        # el techo del mercado (`tope`), preferir un EAN distinto obligaria a BAJAR el precio
        # y romperia la monotonicidad. Ahi manda la monotonicidad y se repite el producto:
        # es la forma honesta de decir "esta necesidad no tiene un escalon superior".
        libre = cand if tope else cand[~cand['ean'].isin(usados)]
        r = (libre if len(libre) else cand).iloc[0]
        return r, (k == 0)
    return None, False


def construir(pu):
    filas = []
    faltantes = []
    for need, cfg in NEEDS.items():
        c = candidatos(pu, cfg)
        if len(c) < 2:
            faltantes.append((need, cfg['sub'], len(c)))
            continue
        usados = set()
        piso = None
        for i, canasta in enumerate(['Popular', 'Media', 'Ejecutiva', 'Representativa']):
            q = cfg['qty'][i]
            if q is None or q <= 0:
                continue
            # La Representativa no arrastra el piso: no es un tier, es el producto modal.
            r, ok = elegir(c, canasta, usados, None if canasta == 'Representativa' else piso)
            if r is None:
                faltantes.append((f'{need} [{canasta}]', cfg['sub'], len(c)))
                continue
            usados.add(r['ean'])
            if canasta != 'Representativa':
                piso = float(r['pu'])
            tam = (r['grams'] / 1000.0) if cfg['u'] == 'kg' else r['tam']
            n = q / tam if tam and tam > 0 else 0.0
            n = round(n * 2) / 2.0 if n < 3 else float(round(n))
            if n <= 0:
                n = 0.5
            filas.append(dict(necesidad=need, canasta=canasta, ean=r['ean'], desc=r['desc'],
                              marca=r['marca'], rubro=r['rubro'], categoria=r['categoria'],
                              subcategoria=r['subcategoria'], unidad_fisica=cfg['u'],
                              qty_fisica=q, presentacion=tam, cantidad=n,
                              precio_unitario=round(float(r['pu']), 1),
                              precio_envase=round(float(r['precio_mediano']), 1),
                              cadenas=int(r['n_cadenas']), provincias=int(r['n_provincias']),
                              sucursales=int(r['n_sucursales']), cba=cfg.get('cba', ''),
                              confiable=bool(ok)))
    # Femenina
    for need, cfg in NEEDS_FEMENINA.items():
        c = candidatos(pu, dict(sub=cfg['sub'], inc=cfg.get('inc'), exc=cfg.get('exc'), u=cfg['u']))
        if len(c) < 1:
            faltantes.append((f'[F] {need}', cfg['sub'], len(c)))
            continue
        r, ok = elegir(c, 'Femenina', set())
        if r is None:
            faltantes.append((f'[F] {need}', cfg['sub'], len(c)))
            continue
        tam = (r['grams'] / 1000.0) if cfg['u'] == 'kg' else r['tam']
        n = cfg['qty'] / tam if tam and tam > 0 else 0.0
        n = round(n * 2) / 2.0 if n < 3 else float(round(n))
        filas.append(dict(necesidad=need, canasta='Femenina', ean=r['ean'], desc=r['desc'],
                          marca=r['marca'], rubro=r['rubro'], categoria=r['categoria'],
                          subcategoria=r['subcategoria'], unidad_fisica=cfg['u'],
                          qty_fisica=cfg['qty'], presentacion=tam, cantidad=max(n, 0.5),
                          precio_unitario=round(float(r['pu']), 1),
                          precio_envase=round(float(r['precio_mediano']), 1),
                          cadenas=int(r['n_cadenas']), provincias=int(r['n_provincias']),
                          sucursales=int(r['n_sucursales']), cba='', confiable=bool(ok)))
    # Tecnologica
    for need, cfg in NEEDS_TECNO.items():
        c = pu[pu['subcategoria'] == cfg['sub']].copy()
        c = c[elegible(c, 'Tecnologica')]
        if not len(c):
            faltantes.append((f'[T] {need}', cfg['sub'], 0))
            continue
        r = c.sort_values('n_sucursales', ascending=False).iloc[0]
        filas.append(dict(necesidad=need, canasta='Tecnologica', ean=r['ean'], desc=r['desc'],
                          marca=r['marca'], rubro=r['rubro'], categoria=r['categoria'],
                          subcategoria=r['subcategoria'], unidad_fisica='un', qty_fisica=1.0,
                          presentacion=1.0, cantidad=1.0,
                          precio_unitario=round(float(r['precio_mediano']), 1),
                          precio_envase=round(float(r['precio_mediano']), 1),
                          cadenas=int(r['n_cadenas']), provincias=int(r['n_provincias']),
                          sucursales=int(r['n_sucursales']), cba='', confiable=True))
    return pd.DataFrame(filas), faltantes


# ══════════════════════════════════════════════════════════════════════════════
# 6. SALIDAS
# ══════════════════════════════════════════════════════════════════════════════
def escribir_loader(det, destino, periodo):
    piv = (det.pivot_table(index='ean', columns='canasta', values='cantidad', aggfunc='sum')
           .reindex(columns=CANASTAS).fillna(0.0))
    meta = det.drop_duplicates('ean').set_index('ean')[['rubro', 'desc']]
    lineas = []
    for ean, row in piv.iterrows():
        vals = ', '.join(f"'{SLOTS_COL[c]}': {row[c]:g}" for c in CANASTAS)
        d = str(meta.at[ean, 'desc'])[:58].replace('\n', ' ')
        lineas.append(f"    '{ean}': {{{vals}}},  # {meta.at[ean, 'rubro']} | {d}")
    cuerpo = '\n'.join(lineas)
    txt = LOADER_TPL.format(n=len(piv), periodo=periodo, hoy=date.today().isoformat(),
                            hogar=HOGAR_REF, cantidades=cuerpo)
    with open(destino, 'w', encoding='utf-8') as f:
        f.write(txt)
    return len(piv)


LOADER_TPL = '''# ============================================================
# CARGAR LAS 6 CANASTAS EN "Productos unicos"  (script de Colab)  -- v5
# cantidad_01=Popular 02=Media 03=Ejecutiva 04=Tecnologica 05=Representativa 06=Femenina
# ------------------------------------------------------------
# GENERADO AUTOMATICAMENTE por docs/canastas_alternativas/construir_canastas_v5.py
#   periodo de referencia: {periodo}      generado: {hoy}
#   {n} EANs   |   hogar de referencia: {hogar}
#
# Diferencia clave con v4: cada estrato usa SU PROPIA version de cada necesidad
# (Popular primer precio, Media marca lider, Ejecutiva premium), en vez de compartir
# los mismos EANs. Las cantidades salen de la cantidad FISICA mensual anclada a la
# CBA del INDEC dividida por el envase de cada producto, no de un conteo de unidades.
#
# Uso: pegar en Colab, ejecutar, subir el Excel canasta_representativa_*.xlsx
#      (cualquier version), descargar *_con_canastas.xlsx y subirlo a Drive en
#      carga/output_canasta/ como canasta_representativa_<periodo>.xlsx
#
# EDITABLE: se puede tocar cualquier cantidad a mano. Pero si se quiere recalibrar en
# serio (cambiar productos, cantidades fisicas o el hogar de referencia), conviene
# editar construir_canastas_v5.py y volver a generar este archivo, que deja registro
# de por que se eligio cada producto en canastas_v5_detalle.csv.
# ============================================================
import openpyxl, os
from google.colab import files

uploaded = files.upload()
archivo_excel = next(iter(uploaded.keys()))

SHEET = "Productos unicos"
COLS  = ["cantidad_01","cantidad_02","cantidad_03","cantidad_04","cantidad_05","cantidad_06"]

# ---- Cantidades por EAN (unidades de envase por mes) ----
CANTIDADES = {{
{cantidades}
}}

wb = openpyxl.load_workbook(archivo_excel)
if SHEET not in wb.sheetnames:
    raise SystemExit(f"No encuentro la hoja '{{SHEET}}'. Hojas: {{wb.sheetnames}}")
ws = wb[SHEET]

hdr = {{}}
for j in range(1, ws.max_column + 1):
    v = ws.cell(row=1, column=j).value
    if v is not None:
        hdr[str(v).strip()] = j
for c in COLS:
    if c not in hdr:
        ws.cell(row=1, column=ws.max_column + 1, value=c)
        hdr[c] = ws.max_column

col_ean = None
for cand in ("id_producto", "ean", "ean_norm", "producto_sepa_id"):
    if cand in hdr:
        col_ean = hdr[cand]; break
if col_ean is None:
    raise SystemExit(f"No encuentro la columna de EAN. Columnas: {{list(hdr)}}")

# 1) limpiar: las 6 columnas se reescriben enteras
for i in range(2, ws.max_row + 1):
    for c in COLS:
        ws.cell(row=i, column=hdr[c], value=0)

# 2) cargar
puestos, encontrados = 0, set()
for i in range(2, ws.max_row + 1):
    raw = ws.cell(row=i, column=col_ean).value
    if raw is None:
        continue
    ean = str(raw).strip().lstrip("0")
    if ean in CANTIDADES:
        encontrados.add(ean)
        for c, q in CANTIDADES[ean].items():
            ws.cell(row=i, column=hdr[c], value=q)
        puestos += 1

faltan = sorted(set(CANTIDADES) - encontrados)
print(f"EANs de la canasta: {{len(CANTIDADES)}} | encontrados en la hoja: {{len(encontrados)}} | filas escritas: {{puestos}}")
if faltan:
    print(f"\\nOJO - {{len(faltan)}} EANs NO estan en la hoja (no van a cotizar):")
    for e in faltan:
        print("   ", e, "|", " ".join(f"{{k}}={{v}}" for k, v in CANTIDADES[e].items() if v))
    print("\\n   -> volve a correr construir_canastas_v5.py contra el Excel nuevo.")

for nombre, col in [("Popular","cantidad_01"),("Media","cantidad_02"),("Ejecutiva","cantidad_03"),
                    ("Tecnologica","cantidad_04"),("Representativa","cantidad_05"),("Femenina","cantidad_06")]:
    n = sum(1 for q in CANTIDADES.values() if q[col] > 0)
    u = sum(q[col] for q in CANTIDADES.values())
    print(f"  {{nombre:15s}} {{n:3d}} productos empaquetados | {{u:8.1f}} envases/mes")

salida = os.path.splitext(archivo_excel)[0] + "_con_canastas.xlsx"
wb.save(salida)
print(f"\\nGuardado: {{salida}}")
files.download(salida)
'''


def escribir_frescos(qty, destino):
    con = []
    con.append('# Tuplas `qty` para TIPOS_FRESCOS de gen_nb07.py  (Popular, Media, Ejecutiva, Representativa)')
    con.append('# kg/mes del ' + HOGAR_REF + '; Huevos en docenas/mes.')
    con.append('# Generadas por construir_canastas_v5.py a partir de los totales de la CBA del INDEC')
    con.append('# repartidos entre tipos con PESOS_FRESCOS (Popular carga los cortes de olla,')
    con.append('# Ejecutiva los cortes caros; en v4 el 91% de los tipos era compartido).')
    con.append('')
    for tipo, q in sorted(qty.items()):
        con.append(f"{tipo:34s} qty=({q[0]:g}, {q[1]:g}, {q[2]:g}, {q[3]:g})")
    con.append('')
    con.append('# Control contra la CBA (kg/mes del hogar de referencia):')
    for rub, tot in TOTALES_FRESCOS.items():
        real = [sum(qty[t][i] for t in PESOS_FRESCOS if RUBRO_DE_TIPO[t] == rub) for i in range(4)]
        con.append(f"#   {rub:20s} objetivo={tuple(round(x,1) for x in tot)}  logrado={tuple(round(x,1) for x in real)}")
    for t, q in FRESCOS_DIRECTOS.items():
        con.append(f"#   {t:20s} (directo)  {tuple(round(x,2) for x in q)}")
    with open(destino, 'w', encoding='utf-8') as f:
        f.write('\n'.join(con) + '\n')


def main():
    ap = argparse.ArgumentParser(description='Construye las canastas v5 del notebook 07.')
    ap.add_argument('--excel', required=True, help='canasta_representativa_YYYY-MM.xlsx (salida de nb01)')
    ap.add_argument('--out', default=AQUI, help='directorio de salida')
    args = ap.parse_args()

    periodo = re.search(r'(\d{4}-\d{2})', os.path.basename(args.excel))
    periodo = periodo.group(1) if periodo else 'sin-periodo'

    print(f'Leyendo {args.excel} ...')
    pu = cargar_universo(args.excel)
    print(f'  universo: {len(pu):,} productos con precio en {periodo}')

    det, faltantes = construir(pu)
    if faltantes:
        print(f'\n*** {len(faltantes)} necesidades SIN candidatos suficientes (quedan fuera) ***')
        for n, s, k in faltantes:
            print(f'    {n:34s} subcat={s!r:38s} candidatos={k}')

    qty_fr = repartir_frescos()

    csv_p = os.path.join(args.out, 'canastas_v5_detalle.csv')
    det.to_csv(csv_p, index=False, encoding='utf-8-sig')
    n_ean = escribir_loader(det, os.path.join(args.out, 'cargar_canastas_v5.py'), periodo)
    escribir_frescos(qty_fr, os.path.join(args.out, 'frescos_v5_qty.txt'))

    print('\n=== RESUMEN ===')
    print(f'  necesidades empaquetadas resueltas: {det["necesidad"].nunique()}')
    print(f'  EANs unicos en el loader: {n_ean}')
    for c in CANASTAS:
        s = det[det['canasta'] == c]
        if not len(s):
            continue
        gasto = (s['cantidad'] * s['precio_envase']).sum()
        print(f'    {c:16s} {len(s):3d} empaquetados | gasto empaquetado ${gasto:>12,.0f}/mes')

    print('\n=== SOLAPAMIENTO DE EANs ENTRE ESTRATOS (el problema que v4 tenia) ===')
    S = {c: set(det[det['canasta'] == c]['ean']) for c in ['Popular', 'Media', 'Ejecutiva', 'Representativa']}
    for a in S:
        fila = ' | '.join(f'{b}: {len(S[a] & S[b]) / max(len(S[a]), 1) * 100:5.1f}%' for b in S if b != a)
        print(f'    {a:16s} {fila}')

    print('\n=== CONTROL NUTRICIONAL contra la CBA del INDEC (Representativa) ===')
    print(f'    hogar de referencia: {HOGAR_REF}')
    for comp in ['Arroz', 'Fideos', 'Harina de trigo', 'Azucar', 'Aceite', 'Leche', 'Yerba', 'Papa', 'Pan']:
        print(f'    {comp:18s} CBA hogar = {cba_hogar(comp):6.2f} kg/L por mes')

    print(f'\nEscrito:\n  {csv_p}\n  {os.path.join(args.out, "cargar_canastas_v5.py")}'
          f'\n  {os.path.join(args.out, "frescos_v5_qty.txt")}')


if __name__ == '__main__':
    main()
