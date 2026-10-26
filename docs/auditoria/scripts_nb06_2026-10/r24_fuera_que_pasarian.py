# Productos que quedaron "(fuera)" por la regla de subtipo (o "excluido" por ingrediente naturalmente sin gluten) pero
# que pasan todas las demás reglas de s9 (continuidad, caídas, escala, cobertura): son los que hay que mirar a mano para
# ver si la regla de subtipo por palabras dejó afuera alguno comparable. Mismas reglas que s9_seleccion.py.
# Uso: python -I -X utf8 r24_fuera_que_pasarian.py <seleccion.parquet de s9> [lado: tacc|sin_tacc|excluido|todos]
import sys

import pandas as pd

pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30); pd.set_option('display.max_colwidth', 70)
c = pd.read_parquet(sys.argv[1])
lado = sys.argv[2] if len(sys.argv) > 2 else 'todos'
REGLAS = {'sin_tacc': dict(suc=100, prov=20, com=4, grandes=3, principal=75),
          'tacc': dict(suc=300, prov=22, com=8, grandes=5, principal=60)}


def falla(r, g):
    m = []
    if r['meses_2022_2026_07'] < 55: m.append(f"meses {int(r['meses_2022_2026_07'])}")
    if not r['presente_ago_oct_2026']: m.append('sin ago-oct')
    if r['caidas'] > 3: m.append(f"{int(r['caidas'])} caídas")
    if not (0.25 <= r['cob_2022_sobre_2026'] <= 4.0): m.append('escala')
    if r['suc_mes_mediana'] < g['suc']: m.append('suc')
    if r['provincias'] < g['prov']: m.append('prov')
    if r['comercios_super'] < g['com']: m.append(f"com {int(r['comercios_super'])}")
    if r['cadenas_grandes'] < g['grandes']: m.append('grandes')
    if r['pct_cadena_principal'] > g['principal']: m.append('principal')
    return '; '.join(m)


x = c[(c['subtipo'] == '(fuera)') | (c['lado'] == 'excluido')].copy()
# el "excluido" se evalúa con la regla del lado con TACC (es donde se usaría) y el resto con la de su lado
x['falla'] = [falla(r, REGLAS['tacc' if r['lado'] == 'excluido' else r['lado']]) for _, r in x.iterrows()]
x = x[x['falla'].str.count(';') == 0]          # pasa todo o falla una sola regla
if lado != 'todos':
    x = x[x['lado'] == lado]
x['descripcion'] = x['descripcion'].astype(str).str.slice(0, 66)
for (t, l), g in x.sort_values('suc_mes_mediana', ascending=False).groupby(['tipo_nb06', 'lado']):
    print(f'\n===== {t} | {l}: {len(g)} (pasan todo salvo el subtipo, o una regla más)')
    print(g[['id', 'descripcion', 'suc_mes_mediana', 'cadenas_grandes', 'precio_100g_22oct', 'gramos_22oct',
             'falla']].to_string(index=False))
