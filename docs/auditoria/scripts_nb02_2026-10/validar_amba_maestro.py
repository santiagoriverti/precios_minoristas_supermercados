# Contrasta el criterio AMBA del nb02 (CABA + Buenos Aires a <= 90 km del Obelisco, CELDA 7) con la columna REGION
# del maestro de sucursales: cuantas sucursales bonaerenses caen en cada franja de distancia segun su REGION, y la
# lista de las que estan entre 55 y 115 km (donde se decide el radio).
# Uso: python -I docs/auditoria/scripts_nb02_2026-10/validar_amba_maestro.py data/maestro_sucursales_completo.xlsx
# Resultado del 2026-10-16: todas las REGION=AMBA que no son de DIA estan a <= 87 km (La Plata 55, Lujan 67,
# Campana 72, Zarate 81); mas alla de 90 km, las REGION=AMBA son DIA del interior con localidad "BUENOS AIRES"
# (Lobos, Navarro, Magdalena, Mercedes, Chascomus... y ~90 mas lejos: Mar del Plata, Tandil, Pergamino), y otras
# cadenas en esos mismos pueblos figuran como Pampeana. Por eso la REGION del maestro no sirve para el AMBA.
import sys

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
pd.set_option('display.width', 250)
m = pd.read_excel(sys.argv[1])
m['REGION'] = m['REGION'].astype(str).str.replace('\xa0', '').str.strip()
ba = m[m['PROVINCIA'].astype(str).eq('Provincia de Buenos Aires') & m['sucursales_latitud'].notna()].copy()
la0, lo0 = np.radians(-34.6037), np.radians(-58.3816)
la, lo = np.radians(ba['sucursales_latitud']), np.radians(ba['sucursales_longitud'])
a = np.sin((la - la0) / 2) ** 2 + np.cos(la0) * np.cos(la) * np.sin((lo - lo0) / 2) ** 2
ba['km'] = 2 * 6371 * np.arcsin(np.sqrt(a))
ba['rango_km'] = pd.cut(ba['km'], [0, 40, 60, 75, 90, 110, 150, 2000])
print(pd.crosstab(ba['rango_km'], ba['REGION']).to_string())
b = ba[ba['km'].between(55, 115)].copy()
b['localidad'] = b['sucursales_localidad'].astype(str).str.upper().str.strip()
b['nombre'] = b['sucursales_nombre'].astype(str).str[:28]
print(b.sort_values('km')[['km', 'REGION', 'id_comercio', 'nombre', 'localidad']].round(1).to_string())
