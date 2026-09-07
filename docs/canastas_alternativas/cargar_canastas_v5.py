# ============================================================
# CARGAR LAS 6 CANASTAS EN "Productos unicos"  (script de Colab)  -- v5
# cantidad_01=Popular 02=Media 03=Ejecutiva 04=Tecnologica 05=Representativa 06=Femenina
# ------------------------------------------------------------
# GENERADO AUTOMATICAMENTE por docs/canastas_alternativas/construir_canastas_v5.py
#   periodo de referencia: 2026-08      generado: 2026-09-07
#   303 EANs   |   hogar de referencia: hogar tipo 2 (2 adultos + 2 ninos) = 3,09 adultos equivalentes
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
CANTIDADES = {
    '198990785363': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 1, 'cantidad_05': 0, 'cantidad_06': 0},  # Informática | Pc/Notebook Hp Note 15-Fc0235La R3-7320U Amd 15""""8/512Gb
    '2611341000000': {'cantidad_01': 2, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Arvejas Partidas 500 Gr
    '34264476455': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 1, 'cantidad_05': 0, 'cantidad_06': 0},  # Pequeños Electrodomésticos | Licuadora De Mano Oster 800W Fpsthb2802 354 Negro
    '4005808319695': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0.5, 'cantidad_06': 1},  # Perfumería | Crema Corporal Milk Nutritiva Piel Extra Seca Nivea Body 4
    '4005808979677': {'cantidad_01': 0, 'cantidad_02': 2.5, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Perfumería | Desodorante Antitranspirante Hombre Nivea Dry Impact 150 M
    '4005900036759': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 10, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Perfumería | Desodorante Antitranspirante Hombre Roll On Nivea Power In
    '53891142960': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 1, 'cantidad_05': 0, 'cantidad_06': 0},  # Pequeños Electrodomésticos | Plancha A Vapor Oster Gcstbs5905
    '5900273001566': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 1, 'cantidad_06': 0},  # Perfumería | Cepillo Dental Colgate Extra Clean 1 Un
    '6932554416638': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 1, 'cantidad_05': 0, 'cantidad_06': 0},  # Informática | Celular 14C 4Gb/128Gb Starry Blue Azul Redmi Xiaomi 1 Un
    '7500435169646': {'cantidad_01': 0.5, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Perfumería | Máquina de Afeitar Ultra Grip 2 Blister 3 Un Gillette 1 Un
    '7500435225366': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 2, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Perfumería | Repuesto Máquina Afeitar Carbono Gillette Mach 3 2 Un
    '7500435228763': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 2, 'cantidad_06': 0},  # Bebés y mamás | Pañal Talle XG Baby-dry Hipoalergénico Pampers 36 Un
    '7500435229487': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 3, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Perfumería | Toallas Femeninas con Alas Noches Tranquilas Seca Always 8
    '7500435237598': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 2.5, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Bebés y mamás | Pañal G Deluxe Protection Pampers 44 Un
    '7501056326142': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 8, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Perfumería | Crema Humectante Pond's Pote 100 Gr
    '7501056342999': {'cantidad_01': 0, 'cantidad_02': 2.5, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Perfumería | Shampoo Dual Effect 2 en 1 Clear 400 Ml
    '7502271278278': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 1, 'cantidad_05': 0, 'cantidad_06': 0},  # Cocinas y Hornos | Cocina Multigas Cd5602Ab0 Drean 1 Un
    '7509546687292': {'cantidad_01': 3, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Perfumería | Crema Dental Doble Protección Odol 90 Gr
    '7509552455557': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 1},  # Perfumería | Desmaquillante Agua Micelar Todo en 1 Botella Garnier 400 
    '7509552874129': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 4, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Perfumería | Acondicionador Hair Food Coco Fructis 300 Ml
    '7509552874136': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 4, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Perfumería | Shampoo Hair Food Coco Fructis 300 Ml
    '7509552924121': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 1},  # Perfumería | Tintura Coloración Permanente 50 Castaño Nutrisse 1 Un
    '7622201703080': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 14, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Bebidas | Jugo en Polvo Sabor Manzana Deliciosa Clight 7 Gr
    '7622201735685': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 10, 'cantidad_06': 0},  # Bebidas | Jugo en Polvo Sabor Limón Dulce Tang 15 Gr
    '7622201735906': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 5, 'cantidad_06': 0},  # Almacén | Galletitas con Chips Chocolate Pepitos 119 Gr
    '7622201736033': {'cantidad_01': 0, 'cantidad_02': 6, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Galletitas Clásicas Cerealitas 212 Gr
    '7702010631405': {'cantidad_01': 0.5, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Perfumería | Cepillo Dental Mediano Twister Colgate 3 Un
    '7702018037865': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 1, 'cantidad_06': 0},  # Perfumería | Repuesto Rasuradora Prestobarba Mach3 Sensitive 2 Un
    '7702018072392': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 1},  # Perfumería | Rasuradora Desechable Simply Venus Gillette 2 Un
    '7702018983872': {'cantidad_01': 0, 'cantidad_02': 1.5, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Perfumería | Rasuradora Desechable Men Prestobarba3 Ice Gillette 2 Un
    '7790010002639': {'cantidad_01': 0, 'cantidad_02': 2.5, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Perfumería | Toallas Femeninas con Alas Adapt Plus Siempre Libre 8 Un
    '7790010002769': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 2, 'cantidad_06': 4},  # Perfumería | Toallas Femeninas con Alas Ultrafina Suave Siempre Libre 8
    '7790010002806': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 1},  # Perfumería | Protectores Diarios Protección Largos Carefree 60 Un
    '7790040133587': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 5, 'cantidad_06': 0},  # Almacén | Alfajor Minitorta Clásica Águila 69 Gr
    '7790040144095': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 2.5, 'cantidad_06': 0},  # Almacén | Galletitas Traviata 540 Gr
    '7790045001188': {'cantidad_01': 0, 'cantidad_02': 4, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Galletitas con Avena y Pasas Frutigran Granix 250 Gr
    '7790064000261': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 80},  # Perfumería | Algodón Estrella Clásico 75 Gr
    '7790064002029': {'cantidad_01': 1, 'cantidad_02': 1.5, 'cantidad_03': 2, 'cantidad_04': 0, 'cantidad_05': 1, 'cantidad_06': 0},  # Perfumería | Algodón Pompones Estrella 50 Un
    '7790070012050': {'cantidad_01': 0, 'cantidad_02': 4, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Aceite de Girasol Cocinero 900 Ml
    '7790070034410': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 2, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Congelados | Nuggets de Pollo Bolsa Granja Del Sol 400 Gr
    '7790070035936': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 1, 'cantidad_06': 0},  # Congelados | Bocaditos de Pollo Rebozados Patitas 400 Gr
    '7790070035950': {'cantidad_01': 0, 'cantidad_02': 0.5, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Congelados | Bocaditos de Pollo Rebozados +100 Gr Gratis Patitas 1.1 Kg
    '7790070036278': {'cantidad_01': 0, 'cantidad_02': 1, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Congelados | Espinaca Congelada Granja Del Sol 500 Gr
    '7790070036322': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 2.5, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Congelados | Brocoli Congelado Lucchetti 300 Gr
    '7790070036636': {'cantidad_01': 1, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Congelados | Formitas de Pollo Rebozadas Lucchetti 350 Gr
    '7790070231864': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0.5, 'cantidad_06': 0},  # Almacén | Aceite de Oliva Cocinero 500 Cc
    '7790070335937': {'cantidad_01': 0, 'cantidad_02': 10, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Fideos Tirabuzón 3 Vegetales Matarazzo 500 Gr
    '7790070336118': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 11, 'cantidad_06': 0},  # Almacén | Fideos Tallarín N5 Lucchetti 500 Gr
    '7790070336675': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 8, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Fideos Spaghetti con Espinaca Rina Matarazzo 500 Gr
    '7790070412126': {'cantidad_01': 4, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Arroz Largo Fino sin TACC Máximo 1 kG
    '7790070418241': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 20, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Alfajor Arroz Limón Chocoarroz 22 Gr
    '7790070433169': {'cantidad_01': 0, 'cantidad_02': 1, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Pan Rallado Fortificado Preferido 500 Gr
    '7790070433176': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0.5, 'cantidad_06': 0},  # Almacén | Pan Rallado Fortificado Preferido 1 Kg
    '7790070433251': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 1, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Rebozador Crunch Fortificado Preferido 450 Gr
    '7790070562258': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 3, 'cantidad_06': 0},  # Almacén | Harina 000 con Vitamina Zinc Favorita 1 Kg
    '7790070621863': {'cantidad_01': 0, 'cantidad_02': 1, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Frescos | Ravioles Ricota Mozzarella Danbo Parmesano La Salteña 450 
    '7790070621870': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 1, 'cantidad_06': 0},  # Frescos | Ravioles Jamón y Mozzarella La Salteña 450 Gr
    '7790070622037': {'cantidad_01': 0, 'cantidad_02': 1, 'cantidad_03': 1, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Frescos | Tapa para Pascualina Criolla La Salteña 400 Gr
    '7790070622044': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 1, 'cantidad_06': 0},  # Frescos | Tapa para Pascualina Hojaldradas La Salteña 400 Gr
    '7790070933638': {'cantidad_01': 0, 'cantidad_02': 1, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Café Instantáneo Suave Extra Aroma Arlistán 170 Gr
    '7790072001014': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0.5, 'cantidad_06': 0},  # Almacén | Sal Fina en Paquete Celusal 500 Gr
    '7790072002080': {'cantidad_01': 0, 'cantidad_02': 0.5, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Sal Fina en Estuche Celusal 500 Gr
    '7790088001497': {'cantidad_01': 5, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Puré de Tomate en Tetrabrik Alco 520 Gr
    '7790117000200': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 1, 'cantidad_06': 0},  # Limpieza | Bolsas de Residuos de 45 Cm 60 Cm en Rollo Asurin 30 Un
    '7790117061836': {'cantidad_01': 0, 'cantidad_02': 2, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Limpieza | Bolsas de Residuos Cierra Fácil Rollo 45x55 Cm Asurín 20 U
    '7790117061843': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 2.5, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Limpieza | Bolsas de Residuos Cierra Fácil Rollo 50x65 Cm Asurín 20 U
    '7790130000027': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0.5, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Vinagre de Manzana Menoyo 500 Cc
    '7790130000058': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0.5, 'cantidad_06': 0},  # Almacén | Vinagre de Alcohol Menoyo 1 Lt
    '7790132098459': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 3, 'cantidad_06': 0},  # Limpieza | Lavandina Concentrada Ayudín 1 Lt
    '7790139003173': {'cantidad_01': 0, 'cantidad_02': 0.5, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Vinagre de Alcohol Clásico Casalta 1 Lt
    '7790139101138': {'cantidad_01': 0.5, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Vinagre de Alcohol sin TACC Favinco 1 Lt
    '7790150406953': {'cantidad_01': 1, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Ají Molido Sobre Alicante 50 Gr
    '7790150540183': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 3, 'cantidad_06': 0},  # Almacén | Orégano sin TACC Alicante 25 Gr
    '7790150570180': {'cantidad_01': 0, 'cantidad_02': 3, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Provenzal Alicante 25 Gr
    '7790199603368': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0.5, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Harina de Maíz Blanco para Arepas Morixe 20 Un 1 Kg
    '7790199604587': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0.5, 'cantidad_06': 0},  # Almacén | Avena Tradicional Morixe 400 Gr
    '77902320': {'cantidad_01': 14, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Alfajor Marroc Fulbito 25 Gr
    '7790250015536': {'cantidad_01': 0, 'cantidad_02': 5, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Limpieza | Papel Higiénico Doble Hoja Manzanilla Higienol 4 Un 30 Mt
    '7790250015840': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 4, 'cantidad_06': 0},  # Limpieza | Papel Higiénico Hoja Simple Max Higienol 4 Un 100 Mt
    '7790250015857': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 6, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Limpieza | Papel Higiénico Hoja Simple Max Higienol 4 Un 80 Mt
    '7790250016182': {'cantidad_01': 4, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Limpieza | Papel Higiénico Fresh Hoja Simple con Aloe Vera Higienol 4
    '7790250056881': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0.5, 'cantidad_06': 0},  # Limpieza | Rollos de Cocina Clásico 50 Paños Sussex 3 Un
    '7790250057086': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 5, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Limpieza | Rollo de Cocina Familiar 200 Paños Sussex 1 Un
    '7790250057765': {'cantidad_01': 0, 'cantidad_02': 2.5, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 2, 'cantidad_06': 0},  # Limpieza | Servilletas Papel Hoja Simple Clásica 30X30 Sussex 80 Un
    '7790272001005': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 3, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Aceite de Girasol Natura 900 Ml
    '7790272008394': {'cantidad_01': 0, 'cantidad_02': 0.5, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Aceite de Oliva Extra Vírgen Suave Natura 500 Ml
    '7790310985373': {'cantidad_01': 0.5, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Papas Fritas Clásicas Pehuamar 230 Gr
    '7790310985465': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 1.5, 'cantidad_06': 0},  # Almacén | Papas Fritas Clásicas Lays 134 Gr
    '7790314080128': {'cantidad_01': 1.5, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Bebidas | Vino Tinto Malbec Pato Criollo 750 Ml
    '7790360967411': {'cantidad_01': 1.5, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Congelados | Hamburguesas Clásicas XL Swift 250 Gr
    '7790360970053': {'cantidad_01': 0, 'cantidad_02': 2.5, 'cantidad_03': 2, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Frescos | Salchichas Kids Swift Flowpack 190 Gr
    '7790380023418': {'cantidad_01': 1, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Polvo de Cacao Toddy 360 Gr
    '7790380023630': {'cantidad_01': 0, 'cantidad_02': 8, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Alfajor Mousse Blanco Toddy 24 Un 50 Gr
    '7790520025739': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 1.5, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Limpieza | Mata Moscas Y Mosquitos 10 Horas Protección Raid Max 360 M
    '7790520025869': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 1, 'cantidad_06': 0},  # Limpieza | Mata Mosca Mosquito Acuosa Aerosol Fuyi 360 Cc
    '7790520997623': {'cantidad_01': 0, 'cantidad_02': 1, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Limpieza | Mata Moscas y Mosquitos Aerosol Raid 370 Ml
    '7790550000157': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0.5, 'cantidad_06': 0},  # Almacén | Café Molido Torrado en Bolsa Cabrales 250 Gr
    '7790580103361': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 11, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Chocolate Aireado con Leche Cofler 27 Gr
    '7790580129972': {'cantidad_01': 0, 'cantidad_02': 18, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Bebidas | Jugo en Polvo Sabor Manzana Sobre Bc 8.5 Gr
    '7790580131357': {'cantidad_01': 0, 'cantidad_02': 2, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Atún en Aceite Libre de Gluten sin TACC La Campagnola 170 
    '7790580131364': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 3, 'cantidad_04': 0, 'cantidad_05': 2, 'cantidad_06': 0},  # Almacén | Atún al Natural Libre de Gluten sin TACC La Campagnola 170
    '7790580132163': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 1, 'cantidad_06': 0},  # Almacén | Mermelada Durazno Arcor 454 Gr
    '7790580132262': {'cantidad_01': 0, 'cantidad_02': 1, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Mermelada Naranja Light Arcor 390 Gr
    '7790580132392': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 3, 'cantidad_06': 0},  # Almacén | Arvejas Secas Remojadas sin Conservantes Lata Arcor 300 Gr
    '7790580136550': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 4, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Orégano La Campagnola 23 Gr
    '7790580138721': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 1, 'cantidad_06': 0},  # Almacén | Polenta Prestopronta 730 Gr
    '7790580138738': {'cantidad_01': 0, 'cantidad_02': 1, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Harina de Maíz Paquete Prestopronta 500 Gr
    '7790580138868': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 4, 'cantidad_06': 0},  # Almacén | Puré de Tomate La Campagnola 530 Gr
    '7790580143237': {'cantidad_01': 13, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Bebidas | Jugo en Polvo Sabor Naranja Arcor 15 Gr
    '7790580567101': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 5, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Tomate Perita Cubeteado en Lata Arcor 400 Gr
    '7790580607210': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 4, 'cantidad_06': 0},  # Almacén | Chocolate Leche Arcor 25 Gr
    '7790625010401': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 2.5, 'cantidad_06': 0},  # Frescos | Salchicha Viena 66 190 Gr
    '7790670050650': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 1.5, 'cantidad_06': 0},  # Congelados | Hamburguesas de Carne Clásicas sin TACC Paty 4 Un 320 Gr
    '7790670050674': {'cantidad_01': 0, 'cantidad_02': 5, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Congelados | Hamburguesas de Carne Clásicas Paty 2 Un 160 Gr
    '7790670052586': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0.5, 'cantidad_06': 0},  # Congelados | Brocoli Congelado Green Life 450 Gr
    '7790740001810': {'cantidad_01': 0.5, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Perfumería | Acondicionador Óleo Coco Nutrición Intensa Esencia Plusbel
    '7790742141903': {'cantidad_01': 0, 'cantidad_02': 1, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Frescos | Crema Uat Liviana La Serenisima Tetrabrik 200 Cc
    '7790742192103': {'cantidad_01': 22, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Frescos | Leche Descremada Sachet 1Casanto 1 Lt
    '7790742333605': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 29, 'cantidad_06': 0},  # Frescos | Leche UAT Parcialmente Descremada Zero Lactos Serenísima 1
    '7790742358608': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 31, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Frescos | Leche Descremada Protein Larga Vida Uat La Serenisima 1 Lt
    '7790742625304': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 1, 'cantidad_06': 0},  # Frescos | Dulce de Leche Clásico La Serenísima 400 Gr
    '7790742625403': {'cantidad_01': 0, 'cantidad_02': 0.5, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Frescos | Dulce de Leche Colonial La Serenísima 1 Kg
    '7790770602070': {'cantidad_01': 2, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Perfumería | Toallas Femeninas con Alas Normal Nuevo Centro Líquido Cal
    '7790895000218': {'cantidad_01': 0, 'cantidad_02': 4, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Bebidas | Coca Cola Retornable 2 Lt
    '7790895000447': {'cantidad_01': 0, 'cantidad_02': 2, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Bebidas | Gaseosa Sprite 1.5 Lt
    '7790895000829': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 7, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Bebidas | Gaseosa Sprite 500 Cc
    '7790895000997': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 4, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Bebidas | Coca Cola Sabor Original 2.25 Lt
    '7790895001000': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 1, 'cantidad_06': 0},  # Bebidas | Gaseosa Sprite 2.25 Lt
    '7790895005794': {'cantidad_01': 2.5, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Bebidas | Coca Cola 2.5 Lt
    '7790895007385': {'cantidad_01': 1, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Bebidas | Gaseosa Lima Limón Crush 2.25 Lt
    '7790895640483': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 2, 'cantidad_06': 0},  # Bebidas | Agua Saborizada Manzana sin Gas Aquarius 1.5 Lt
    '7790990001813': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 1.5, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Limpieza | Jabón para Ropa Pan Blanqueador Gran Federal 150 Gr
    '7790990002230': {'cantidad_01': 2, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Limpieza | Jabón en Polvo para Ropa Regular Plus Duo Zorro 800 Gr
    '7790990002834': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 8, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Limpieza | Jabón Líquido Concentrado para Diluir Platinum Ariel 500 M
    '7790990003121': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 7, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Limpieza | Detergente Ultra Marina Magistral 300 Ml
    '7791113003783': {'cantidad_01': 1, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Mermelada de Frutilla Emeth 420 Gr
    '7791120021565': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 6, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Arroz Doble Carolina Molinos Ala 500 Gr
    '7791120031557': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 4, 'cantidad_06': 0},  # Almacén | Arroz Largo Fino 00000 Molinos Ala 1 Kg
    '7791120031564': {'cantidad_01': 0, 'cantidad_02': 7, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Arroz Largo Fino 00000 Molinos Ala 500 Gr
    '7791130681384': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 1, 'cantidad_06': 0},  # Limpieza | Quita Sarro Desinfectante en Gel Harpic 500 Ml
    '7791130681421': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 2, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Limpieza | Limpiador para Inodoros Fragancia Citrus en Botella Harpic
    '7791130683661': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 2, 'cantidad_06': 0},  # Limpieza | Limpiador Líquido Marina Procenex 900 Cc
    '7791130683777': {'cantidad_01': 1, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Limpieza | Limpiador Líquido Pisos Flores Jardin Procenex 1.8 Lt
    '7791130963299': {'cantidad_01': 0, 'cantidad_02': 1.5, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Limpieza | Limpiador Líquido Baño Doypack Harpic 420 Ml
    '7791200000619': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 2, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Bebidas | Aperitivo Cynar 750 Cc
    '7791200000626': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0.5, 'cantidad_06': 0},  # Bebidas | Aperitivo Cynar 750 Ml
    '7791203001231': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 4, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Bebidas | Vino Tinto Malbec Luigi Bosca 750 Cc
    '7791250801563': {'cantidad_01': 0, 'cantidad_02': 1.5, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Bebidas | Aperitivo Pomelo y Lima Lata Smirnoff 473 Ml
    '7791290792050': {'cantidad_01': 0, 'cantidad_02': 1, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Limpieza | Jabón en Polvo Lavado a Mano Ala 800 Gr
    '7791290792142': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 1.5, 'cantidad_06': 0},  # Limpieza | Jabón en Polvo Matic Mañana de Sol Ala 800 Gr
    '7791290792838': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 5, 'cantidad_06': 0},  # Limpieza | Jabón Líquido para Diluir Bioenzimas Skip 500 Ml
    '7791290793361': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 6, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Limpieza | Limpiador de Piso Plastificado Recarga Doypack Cif 450 Ml
    '7791290793613': {'cantidad_01': 0, 'cantidad_02': 1.5, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Limpieza | Suavizante para Ropa ConcentradoFiber Protect Doypack Comf
    '7791290793682': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 1.5, 'cantidad_06': 0},  # Limpieza | Suavizante para Ropa Clásuci Doypack Comfort 900 Ml
    '7791290794054': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 5, 'cantidad_06': 0},  # Limpieza | Detergente Líquido Bioactive Limón Cif 300 Ml
    '7791290794078': {'cantidad_01': 0, 'cantidad_02': 2.5, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Limpieza | Detergente Líquido Bioactive Limón Cif 750 Ml
    '7791290794269': {'cantidad_01': 3, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Limpieza | Detergente Líquido Ultra Limón Doyoack Ala 450 Ml
    '7791290796430': {'cantidad_01': 0, 'cantidad_02': 4, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Limpieza | Jabón Liquido Limpieza Activo Doypack Skip 800 Ml
    '7791290796577': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 1, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Limpieza  | Jabón en Polvo mas Blancos Ala 600 Gr
    '7791293043791': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 2.5, 'cantidad_06': 0},  # Perfumería | Desodorante Aerosol Marine Axe 150 Cc
    '7791293045733': {'cantidad_01': 2.5, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Perfumería | Shampoo Ceramidas Sedal 340 Ml
    '7791293046891': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 9, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Perfumería | Jabón de Tocador Antibacterial Original Rexona 3 Un 90 Gr
    '7791293047102': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 2, 'cantidad_06': 1.5},  # Perfumería | Shampoo Reconstrucción Completa Dove 400 Ml
    '7791293047492': {'cantidad_01': 0, 'cantidad_02': 2, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Perfumería | Acondicionador Ritual de Reparación Dove 400 Cc
    '7791293047515': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 1.5, 'cantidad_06': 1.5},  # Perfumería | Acondicionador Oleo Nutrición Dove 400 Cc
    '7791293049557': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 2.5},  # Perfumería | Desodorante Aerosol Women Nutrivive Rexona 150 Ml
    '7791293050607': {'cantidad_01': 1.5, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Perfumería | Desodorante Hombre Musk en Aerosol Axe 230 Ml
    '7791293051208': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 6, 'cantidad_06': 4},  # Perfumería | Jabón de Tocador Original Dove 90 Gr
    '7791337007246': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 9, 'cantidad_06': 0},  # Frescos | Yogur Firme Descremado con Colágeno Vainilla Pote Ser 190 
    '7791337008106': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 7, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Frescos | Postre de Dulce de Leche con Crema Pote Danette 100 Gr
    '7791337008656': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 4, 'cantidad_06': 0},  # Frescos | Postre Vainilla Pote Danonino 80.5 Gr
    '7791337008663': {'cantidad_01': 0, 'cantidad_02': 5, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Frescos | Postre Frutilla Pote Danonino 80.5 Gr
    '7791337009356': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 21, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Frescos | Yogur Bebible Sabor Vainilla Yogurísimo 190 Gr
    '7791337010000': {'cantidad_01': 0, 'cantidad_02': 8, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Frescos | Yogur Griego Natural con Endulzado Yogurísimo 300 Gr
    '7791337061439': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 1, 'cantidad_06': 0},  # Frescos | Queso Untable Light La Serenisima 290 Gr
    '7791416001240': {'cantidad_01': 2, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Mascotas | Alimento para Perros Adultos Carne Raza 1.5 Kg
    '7791476034011': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 1, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Lentejas Secas Egran 400 Gr
    '7791540044502': {'cantidad_01': 0, 'cantidad_02': 2, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Bebidas | Vino Tinto Vainilla 1 Dada 750 Cc
    '7791564012488': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 6, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Frescos | Queso Untable Jamón Adler 100 Gr
    '7791620187723': {'cantidad_01': 1, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Mayonesa D'Fiesta 250 Gr
    '7791620187808': {'cantidad_01': 0.5, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Frescos | Margarina en Pan Clásica Dánica 200 Gr
    '7791720026311': {'cantidad_01': 12, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Fideos Cinta Tallarin Carrefour Classic 500 Gr
    '7791720027622': {'cantidad_01': 1.5, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Limpieza | Jabón Líquido para Ropa Carrefour Expert 1.5 Lt
    '7791720027738': {'cantidad_01': 1, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Frescos | Tapa para Empanadas Rotiseras Carrefour 450 Gr
    '7791720033487': {'cantidad_01': 3, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Arvejas Secas Remojadas sin Sal Lata Carrefour Classic 300
    '7791720034279': {'cantidad_01': 2.5, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Galletitas Mini Pepa Carrefour Classic 300 Gr
    '7791720036495': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 2, 'cantidad_06': 0},  # Almacén | Arvejas Partidas Bolsa Carrefour Classic 400 Gr
    '7791720036501': {'cantidad_01': 0, 'cantidad_02': 1.5, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Porotos Alubia Bolsa Carrefour Classic 400 Gr
    '7791720037836': {'cantidad_01': 2, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Frescos | Salchichas Clásicas Carrefour Classic 6 Un 225 Gr
    '7791720044407': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 10, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Galletitas Avena y Chips Carrefour Extra  120 Gr
    '7791720044650': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 4, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Frescos | Capellettis 4 Quesos Carrefour Classic 250 Gr
    '7791813888468': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 3, 'cantidad_06': 0},  # Bebidas | Gaseosa Cola Pepsi 2 Lt
    '7791828000428': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 4, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Limpieza | Servilletas Blancas Felpita 70 Un
    '7791828900018': {'cantidad_01': 2, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Limpieza | Servilletas 32x30 Cm Blancas Carrefour 70 Un
    '7791866001364': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0.5, 'cantidad_06': 0},  # Almacén | Mayonesa Doypack Natura 500 Ml
    '7792180001641': {'cantidad_01': 4, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Aceite de Girasol Cañuelas 900 Ml
    '7792180004741': {'cantidad_01': 1, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Pan Rallado Fortificado Mamá Cocina 500 Gr
    '7792180139320': {'cantidad_01': 4, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Harina 000 Fortificada con Calcio Cañuelas 1 Kg
    '7792198006621': {'cantidad_01': 4, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Yerba Mate Tradicional Natura 500 Gr
    '7792280005693': {'cantidad_01': 0, 'cantidad_02': 3, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Yerba Mate Rosa Cachamate 500 Gr
    '7792360002062': {'cantidad_01': 0.5, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Café Molido Torrado Intenso Bonafide 500 Gr
    '7792540250450': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 2.5, 'cantidad_04': 0, 'cantidad_05': 4, 'cantidad_06': 0},  # Almacén | Azúcar Molida Superior Ledesma 1 Kg
    '7792590000227': {'cantidad_01': 0, 'cantidad_02': 3, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Harina de Trigo 0000 Caserita 1 Kg
    '7792710000182': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 3, 'cantidad_06': 0},  # Almacén | Yerba Mate sin TACC Amanda 500 Gr
    '7792798014835': {'cantidad_01': 3, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Bebidas | Cerveza Quilmes 710 Ml
    '7792798014873': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 6, 'cantidad_06': 0},  # Bebidas | Cerveza Corona 330 Ml
    '7792798999866': {'cantidad_01': 0, 'cantidad_02': 7, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Bebidas | Cerveza Blanca Lata Andes 473 Cc
    '7792900000428': {'cantidad_01': 1, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Sal Fina en Paquete Trilaminado Dos Anclas 500 Gr
    '7793100111891': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 3, 'cantidad_06': 0},  # Perfumería | Crema Dental Ultra Blanco Colgate 90 Gr
    '7793147009137': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 18, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Bebidas | Cerveza Rubia Heineken 330 Cc
    '7793253003548': {'cantidad_01': 0, 'cantidad_02': 2, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Limpieza | Limpiador Líquido Primavera Poett 900 Ml
    '7793253003722': {'cantidad_01': 0, 'cantidad_02': 1.5, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Limpieza | Lavandina Lavanda Triple Poder Ayudín 2 Lt
    '7793253003784': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 1, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Limpieza | Lavandina Anti-splash Tradicional Ayudín 2 Lt
    '7793253007102': {'cantidad_01': 2, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Limpieza  | Bolsas de Residuos 45X55 Cm de 15 Un Mortimer 1 Un
    '7793281493472': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 10, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Congelados | Hamburguesas Clásicas Unión Ganadera 4 Un 83 Gr
    '7793344009206': {'cantidad_01': 0, 'cantidad_02': 3, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Limpieza | Rollo de Cocina 200 Paños Gigante Elegante 1 Un
    '7793360000157': {'cantidad_01': 0, 'cantidad_02': 4, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Puré de Tomate Tetrabrik Salsati La Campagnola 520 Gr
    '7793360132384': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 3, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Arvejas Secas Remojadas La Campagnola 300 Gr
    '7793704000881': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 2.5, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Yerba Mate Elaborada sin Palo Playadito 500 Gr
    '7793862008910': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 1, 'cantidad_05': 0, 'cantidad_06': 0},  # Climatización | Convector Liliana Convectory Plus Mod Cfb17 1 Un
    '7793890258752': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 7, 'cantidad_06': 0},  # Almacén | Pan de Mesa Blanco en Rodajas Finas Lactal 460 Gr
    '7793890258769': {'cantidad_01': 0, 'cantidad_02': 3, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Pan de Mesa Blanco Chico Lactal 315 Gr
    '7793913013535': {'cantidad_01': 8, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Frescos | Yogur Parcialmente Descremado Vainilla Tregar 125 Gr
    '7793940054006': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 1, 'cantidad_06': 0},  # Frescos | Manteca La Serenísima 200 Gr
    '7794000005150': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 2.5, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Mayonesa Receta Casera Hellmanns 232 Gr
    '7794000006058': {'cantidad_01': 0, 'cantidad_02': 0.5, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Mayonesa Clásica Doypack Hellmanns 950 Gr
    '7794218106328': {'cantidad_01': 3, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Limpieza | Jabón en Pan con Glicerina Argentino 200 Gr
    '7794218106854': {'cantidad_01': 0, 'cantidad_02': 2.5, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 3, 'cantidad_06': 0},  # Limpieza | Jabón Blanco Argentino 150 Gr
    '7794440000098': {'cantidad_01': 0, 'cantidad_02': 3, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Limpieza | Esponja con Fibra Siempre Limpia Virulana 1 Un
    '7794440003303': {'cantidad_01': 2, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Limpieza | Esponja con Cuadraditos y Cuida Uñas Virulana 1 Un
    '7794440003310': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 2.5, 'cantidad_06': 0},  # Limpieza | Esponja Pintada Lisa Virulana 1 Un
    '7794520869287': {'cantidad_01': 0, 'cantidad_02': 5, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Papas Fritas Tradicional Krachitos 50 Gr
    '7794626011023': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 4, 'cantidad_06': 0},  # Bebés y mamás | Toallitas Húmedas Clásico y Cotidiano Huggies 48 Un
    '7794640173066': {'cantidad_01': 0, 'cantidad_02': 3, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Perfumería | Crema Corporal Rosa Plus Hinds 125 Ml
    '7794820000885': {'cantidad_01': 0.5, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Frescos | Dulce de Leche en Pote Milkaut 1 Kg
    '7794820902943': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 1.5, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Frescos | Dulce de Leche Repostero Milkaut 400 Gr
    '7794820902967': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 1.5, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Frescos | Crema de Leche Pote Milkaut 330 Cc
    '7794820903292': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 4, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Frescos | Manteca Calidad Extra Milkaut 100 Gr
    '77956262': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 1, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Sal Fina en Salero Celusal 250 Gr
    '7795930000543': {'cantidad_01': 2.5, 'cantidad_02': 4, 'cantidad_03': 6, 'cantidad_04': 0, 'cantidad_05': 1, 'cantidad_06': 0},  # Bebidas | Agua Mineral Neste Purez Vital 2.25 Lt
    '7796885495194': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 1, 'cantidad_05': 0, 'cantidad_06': 0},  # Cocinas y Hornos | Hornos Microondas 20Lt Blanco 700 W Bgh 1 Un
    '7796962987321': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 1, 'cantidad_05': 0, 'cantidad_06': 0},  # CLIMATIZACIÓN | Aire Acondicionado Philco Split 3200W Frio Calor Cl. A Phs
    '7797026970037': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 1, 'cantidad_05': 0, 'cantidad_06': 0},  # Informática | Parlante Bt Stromberg Boombox Force
    '7797102526875': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 1, 'cantidad_05': 0, 'cantidad_06': 0},  # Heladeras y Freezers | Heladera con Freezer Cíclica 2 Fríos Modelo HDR280F50B Dre
    '7797453001519': {'cantidad_01': 0, 'cantidad_02': 2, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Mascotas | Alimento para Perros Cachorros Pedigree 3 Kg
    '7797453972345': {'cantidad_01': 0, 'cantidad_02': 3, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Mascotas | Alimento para Gatos Carne Whiskas 1 Kg
    '7797470007426': {'cantidad_01': 0, 'cantidad_02': 4, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Arvejas Secas Remojadas Marolio 200 Gr
    '7798033339572': {'cantidad_01': 2, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Polenta Instantanea Carrefour 500 Gr
    '7798060853119': {'cantidad_01': 0, 'cantidad_02': 2.5, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Frescos | Queso Untable Cheddar Dip 180 Gr
    '7798060853300': {'cantidad_01': 0, 'cantidad_02': 1, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Frescos | Manteca Baja Lactosa Tonadita 200 Gr
    '7798060854475': {'cantidad_01': 1, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Frescos | Queso Untable Patagonia Original Tonadita 290 Gr
    '7798061190183': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 1.5, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Aceite de Oliva Oliovita 500 Ml
    '7798062540260': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 16, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Bebidas | Agua Saborizada sin Gas Pera Levité Villa Sur 500 Cc
    '7798062548679': {'cantidad_01': 0, 'cantidad_02': 2.5, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Bebidas | Agua Saborizada Pomelo Sin Gas Levité 1.5 Lt
    '7798074864675': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 2, 'cantidad_06': 0},  # Bebidas | Vino Tinto Malbec Portillo 750 Ml
    '7798081287429': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 1, 'cantidad_05': 0, 'cantidad_06': 0},  # Pequeños Electrodomésticos | Jarra Electrica Smart Life Mod Slek1714Wpn Blanca
    '7798088960042': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 1, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Mermelada de Durazno El Brocal 420 Gr
    '7798104300012': {'cantidad_01': 1, 'cantidad_02': 1.5, 'cantidad_03': 2.5, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Té Verde en Saquitos Chai Inti Zen 30 Gr
    '7798104307707': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 1.5, 'cantidad_06': 0},  # Almacén | Té Chaman Chai Inti Zen 30 Gr
    '7798131250380': {'cantidad_01': 3, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Limpieza | Lavandina Aditivada Naranja Héroe 1 Lt
    '7798137725820': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 1, 'cantidad_05': 0, 'cantidad_06': 0},  # Informática | Auricular Ear Btwins 49 Noganet 1 Un
    '7798140257554': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 1},  # Perfumería | Crema Facial Humectante Teatrical 100 Gr
    '7798152224049': {'cantidad_01': 4, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Galletitas Salvado Carrefour Pack 3 Un 360 Gr
    '7798159719128': {'cantidad_01': 1, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Caldo de Verduras Carrefour 12 Un 108 Gr
    '7798174970016': {'cantidad_01': 0, 'cantidad_02': 4, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Azúcar Común Azucel 1 Kg
    '7798181510212': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 7, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Galletitas Crackers Smams 150 Gr
    '7798185030419': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 4, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Pan con Semillas La Panerita 340 Gr
    '7798185030600': {'cantidad_01': 1, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Pan  Salvado Grande 600 Gr
    '7798311610317': {'cantidad_01': 0, 'cantidad_02': 5, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Bebés y mamás | Toallas Húmedas con Aloe Vera Toddler 48 Un
    '7798311610355': {'cantidad_01': 0, 'cantidad_02': 3, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Bebés y mamás | Panales Talle Xg Deluxe de 30 Un Toddler 1 Un
    '7798316700808': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 4, 'cantidad_06': 0},  # Almacén | Aceite de Girasol Legítimo 900 Ml
    '7798338291070': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 1, 'cantidad_06': 0},  # Frescos | Crema de Leche Clásica para Cocinar Las Tres Niñas 200 Ml
    '7798338291469': {'cantidad_01': 0, 'cantidad_02': 27, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Frescos | Leche Liviana Las Tres Niñas 1 Lt
    '7799037060325': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 2, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Harina Especial para Masa Madre Chacabuco 1 Kh
    '7799086000389': {'cantidad_01': 4, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Azúcar Domino 1 Kg
    '7891000288801': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 4, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Cereal Tradicional sin Azúcar Nesfit Nestlé 220 Gr
    '7891000345399': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 2, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Caldo de Verduras Maggi 6 Un 57 Gr
    '7891000345481': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 1, 'cantidad_06': 0},  # Almacén | Caldo de Gallina Maggi 12Un 114 Gr
    '7891000345528': {'cantidad_01': 0, 'cantidad_02': 1, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Caldo de Verdura Maggi 114 Gr
    '7891010251024': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 7, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Bebés y mamás | Toallitas Húmedas Johnsons 44 Un
    '7891010254773': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 2},  # Perfumería | Tampones Medio O.B. 8 Un
    '7891024034781': {'cantidad_01': 6, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Perfumería | Jabón de Tocador con Karite Palmolive 85 Gr
    '7891024078174': {'cantidad_01': 0, 'cantidad_02': 1, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Perfumería | Cepillo Dental Bamboo Colgate 2 Un
    '7891024116128': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 2, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Perfumería | Cepillo Dental Colgate 1 Un
    '7891024123027': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 4, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Perfumería | Crema Dental Luminous White Colgate 90 Gr
    '7891024134429': {'cantidad_01': 0, 'cantidad_02': 3, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Perfumería | Crema Dental Sensitive Blanqueador Colgate 100 Gr
    '7891040142712': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 4, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Limpieza | Esponja con Fibra Naranja Cocina Cero Rayas Scotchbrite 1 
    '7891150000971': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 5, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Limpieza | Suavizante para Ropa Concentrado Cuidado Intesivo Comfor 5
    '7891150095700': {'cantidad_01': 0, 'cantidad_02': 2, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Perfumería | Jabón de Tocador Piel Sensible x 3 Un Dove 270 Gr
    '7896004004921': {'cantidad_01': 0, 'cantidad_02': 1.5, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Copos de Maíz Azucarados Zucaritas 240 Gr
    '7896004009179': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 3, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Papas Fritas sabor Queso Pringles 109 Gr
    '8002990292139': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 1},  # Perfumería | Crema Depilatoria Piel Sensible Silck & Fresh Veet Caja 10
    '80052760': {'cantidad_01': 0, 'cantidad_02': 3, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Tableta de Chocolate Kinder Bueno 43 Gr
    '8445290057433': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 2, 'cantidad_06': 0},  # Mascotas | Alimento para Gatos Adultos Pescado y Pollo Cat Chow 1 Kg
    '8445290069313': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 4, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Mascotas | Alimento para Gatitos Carne Pescado y Carne Cat Chow 1 Kg
    '8445290274243': {'cantidad_01': 0, 'cantidad_02': 3, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Cacao en Polvo Nescao 150 Gr
    '8445290559975': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 2, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Cacao Menos Azúcar Nesquik 300 Gr
    '8445290944184': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 6, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Mascotas | Alimentos Animales Cachorro Mediano Grande Dog Chow 1.5 Kg
    '8445290977373': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 2.5, 'cantidad_06': 0},  # Mascotas | Alimento para Perros Adultos Medianos a Grandes Bolsa Dog 
    '8445291082113': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 3, 'cantidad_04': 0, 'cantidad_05': 0, 'cantidad_06': 0},  # Almacén | Café Instantáneo Suave Origen Frasco Dolca 100 Gr
    '8445291121843': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 0, 'cantidad_05': 2.5, 'cantidad_06': 0},  # Almacén | Polvo Chocolatado Nesquik 150 Gr
    '8718863045688': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 1, 'cantidad_05': 0, 'cantidad_06': 0},  # Tv Audio y Video | Smart Tv 43" Full Hd 43Pfd6910/77 Philips 1 Un
    '8806094365573': {'cantidad_01': 0, 'cantidad_02': 0, 'cantidad_03': 0, 'cantidad_04': 1, 'cantidad_05': 0, 'cantidad_06': 0},  # Lavado | Lavarropas Frontal Inventer WW65A4000EEU Blanco 6.5 Kg Sam
}

wb = openpyxl.load_workbook(archivo_excel)
if SHEET not in wb.sheetnames:
    raise SystemExit(f"No encuentro la hoja '{SHEET}'. Hojas: {wb.sheetnames}")
ws = wb[SHEET]

hdr = {}
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
    raise SystemExit(f"No encuentro la columna de EAN. Columnas: {list(hdr)}")

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
print(f"EANs de la canasta: {len(CANTIDADES)} | encontrados en la hoja: {len(encontrados)} | filas escritas: {puestos}")
if faltan:
    print(f"\nOJO - {len(faltan)} EANs NO estan en la hoja (no van a cotizar):")
    for e in faltan:
        print("   ", e, "|", " ".join(f"{k}={v}" for k, v in CANTIDADES[e].items() if v))
    print("\n   -> volve a correr construir_canastas_v5.py contra el Excel nuevo.")

for nombre, col in [("Popular","cantidad_01"),("Media","cantidad_02"),("Ejecutiva","cantidad_03"),
                    ("Tecnologica","cantidad_04"),("Representativa","cantidad_05"),("Femenina","cantidad_06")]:
    n = sum(1 for q in CANTIDADES.values() if q[col] > 0)
    u = sum(q[col] for q in CANTIDADES.values())
    print(f"  {nombre:15s} {n:3d} productos empaquetados | {u:8.1f} envases/mes")

salida = os.path.splitext(archivo_excel)[0] + "_con_canastas.xlsx"
wb.save(salida)
print(f"\nGuardado: {salida}")
files.download(salida)
