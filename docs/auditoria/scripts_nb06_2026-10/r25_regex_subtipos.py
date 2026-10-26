# Efecto de los errores de la regla de subtipos de s9: (1) en galletitas dulces "tita\b" (las Tita de Terrabusi) también
# atrapa "galletita" en singular, que es como varias cadenas publican el producto en el SEPA; (2) en saladas, lo que no
# coincide con ningún patrón cae a "(fuera)" (Express, Club Social...). Recalcula el subtipo con "\btita\b" y lista los
# productos que cambian y pasan las demás reglas de s9 (o fallan una sola), y los de saladas que caen por defecto.
# Uso: python -I -X utf8 r25_regex_subtipos.py <seleccion.parquet de s9>
# Medición del error de la regla de subtipos de s9 antes de corregirlo (2026-10-26; s9 ya usa \btita\b): sobre la
# tabla de s9 del 2026-10-23 (seleccion_v8).
import re
import sys

import pandas as pd

pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30); pd.set_option('display.max_colwidth', 64)
c = pd.read_parquet(sys.argv[1])
REGLAS = {'sin_tacc': dict(suc=100, prov=20, com=4, grandes=3, principal=75),
          'tacc': dict(suc=300, prov=22, com=8, grandes=5, principal=60)}
DULCES_FUERA = (r'banad|bañad|cubiert|alfajor|tapita|hojald|hojalmar|integral|avena|salvado|granola|cereal|fibra|organic|'
                r'sin azuc|light|dietet|surtid|variedad|kit kat|rhodesia|bon o bon|chocopause|graffiti|habanit|tita\b|'
                r'brownie|merengu|tripack|3 un|5 un|biscuit|tostad|vainillas\b|okebon|molino natural')
DULCES = [('Obleas', r'oblea|wafer'), ('Rellenas', r'rellen'), ('Pepas', r'pepa'), ('Con chips', r'chip'),
          ('Bizcochos', r'bizcoch|agridulce'), ('Secas (vainilla, limón, chocolate)', r'.')]
SALADAS_FUERA = r'salvado|integral|avena|fibra|bizcochit|grasa|tostad|palito|grisin|sandwich|3 en 1|pack|\bdulce'
SALADAS = [('Saborizadas / snack', r'snack|queso|jamon|pizza|oliva|calabresa|kesitas|\brex\b|saladix|chalita'),
           ('Crackers y galletas de arroz', r'cracker|criollit|marinera|\bagua\b|crackines|arroz')]


def sub(d, fuera, lista):
    if re.search(fuera, d):
        return '(fuera)'
    for n, rx in lista:
        if re.search(rx, d):
            return n
    return '(fuera por defecto)'


def falla(r):
    g = REGLAS[r['lado']]
    m = []
    if r['meses_2022_2026_07'] < 55: m.append(f"meses {int(r['meses_2022_2026_07'])}")
    if not r['presente_ago_oct_2026']: m.append('sin ago-oct')
    if r['caidas'] > 3: m.append(f"{int(r['caidas'])} caídas")
    if not (0.25 <= r['cob_2022_sobre_2026'] <= 4.0): m.append('escala')
    if r['suc_mes_mediana'] < g['suc']: m.append('suc')
    if r['provincias'] < g['prov']: m.append('prov')
    if r['comercios_super'] < g['com']: m.append(f"com {int(r['comercios_super'])}")
    if r['cadenas_grandes'] < g['grandes']: m.append('grandes')
    if r['pct_cadena_principal'] > g['principal']: m.append(f"principal {r['pct_cadena_principal']:.0f}%")
    return '; '.join(m)


d = c[(c['tipo_nb06'] == 'Galletitas dulces') & c['lado'].isin(['tacc', 'sin_tacc'])].copy()
d['tita_galletita'] = d['d'].str.contains(r'tita\b') & ~d['d'].str.contains(r'\btita\b')
d['sub_nuevo'] = [sub(x, DULCES_FUERA.replace(r'tita\b', r'\btita\b'), DULCES) for x in d['d']]
cambia = d[(d['subtipo'] == '(fuera)') & (d['sub_nuevo'] != '(fuera)')].copy()
print(f'Galletitas dulces: {int(d["tita_galletita"].sum())} productos con "galletita" atrapados por tita\\b; '
      f'{len(cambia)} cambian de subtipo con \\btita\\b')
cambia['falla'] = [falla(r) for _, r in cambia.iterrows()]
cambia['descripcion'] = cambia['descripcion'].astype(str).str.slice(0, 60)
ok = cambia[cambia['falla'].str.count(';') == 0].sort_values(['lado', 'sub_nuevo', 'suc_mes_mediana'],
                                                              ascending=[True, True, False])
print(f'De esos, pasan todo o fallan una regla: {len(ok)} (pasan todo: {int(ok["falla"].eq("").sum())})')
print(ok[['lado', 'sub_nuevo', 'id', 'descripcion', 'suc_mes_mediana', 'cadenas_grandes', 'precio_100g_22oct',
          'gramos_22oct', 'falla']].to_string(index=False))

s = c[(c['tipo_nb06'] == 'Galletitas saladas y crackers') & c['lado'].isin(['tacc', 'sin_tacc'])].copy()
s['sub_nuevo'] = [sub(x, SALADAS_FUERA, SALADAS) for x in s['d']]
pdef = s[s['sub_nuevo'] == '(fuera por defecto)'].copy()
pdef['falla'] = [falla(r) for _, r in pdef.iterrows()]
pdef['descripcion'] = pdef['descripcion'].astype(str).str.slice(0, 60)
pdef = pdef.sort_values('suc_mes_mediana', ascending=False)
print(f'\nSaladas que caen a (fuera) por no coincidir con ningún patrón: {len(pdef)}; con más cobertura:')
print(pdef[['lado', 'id', 'descripcion', 'suc_mes_mediana', 'meses_2022_2026_07', 'cadenas_grandes',
            'precio_100g_22oct', 'falla']].head(30).to_string(index=False))
