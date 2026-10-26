# Verificación de los 80 códigos de la canasta fija: cómo los describe cada cadena en el SEPA del 22/10, qué dice el
# maestro del SEPA (Drive) y las marcas de la selección (sin TACC por etiqueta del Maestro, del SEPA o por marca
# celíaca; ingrediente naturalmente sin gluten). Marca los sin TACC que solo entran por la marca y los con TACC que
# alguna cadena publica como sin gluten.
# Uso: python -I -X utf8 r20_etiquetas_canasta.py <canasta.csv> <seleccion.parquet de s9> <cat_20261022.parquet>
#                                                  <cat_..._comercios.parquet> <maestro_sepa_completo.csv.gz>
#                                                  [salida.parquet]
import re
import sys

import pandas as pd

pd.set_option('display.width', 250); pd.set_option('display.max_columns', 40); pd.set_option('display.max_colwidth', 70)
can = pd.read_csv(sys.argv[1], dtype={'ean': str})
sel = pd.read_parquet(sys.argv[2])
cat = pd.read_parquet(sys.argv[3], columns=['id_comercio', 'id_bandera', 'id_sucursal', 'id_producto', 'productos_descripcion',
                                            'productos_marca'])
com = pd.read_parquet(sys.argv[4])
mae = pd.read_csv(sys.argv[5], dtype=str)
print('maestro SEPA:', mae.shape, list(mae.columns)[:12])
GF = re.compile(r'sin\s*t\.?a\.?c\.?c|s[/\s\.\-]+tacc|sin\s*gluten|libre\s*d?e?/?\s*gluten|gluten\s*free|celiac|glutal|apto\s*cel', re.I)
can['ean_n'] = can['ean'].str.lstrip('0')
sel['ean_n'] = sel['id'].astype(str).str.lstrip('0')
cat['ean_n'] = cat['id_producto'].astype(str).str.lstrip('0')
cat = cat.merge(com[['id_comercio', 'id_bandera', 'comercio_bandera_nombre']].astype(str),
                on=['id_comercio', 'id_bandera'], how='left')
col_ean = 'producto_sepa_id'
mae['ean_n'] = mae[col_ean].astype(str).str.lstrip('0')
col_desc = next(c for c in mae.columns if 'desc' in c.lower())
x = can.merge(sel.drop_duplicates('ean_n')[['ean_n', 'gf_maestro', 'gf_sepa_oct26', 'es_gf', 'ingrediente_sin_gluten',
                                            'con_gluten_explicito', 'marca', 'motivo']], on='ean_n', how='left')
filas = []
for _, r in x.iterrows():
    c = cat[cat['ean_n'] == r['ean_n']]
    descs = c.groupby('productos_descripcion')['comercio_bandera_nombre'].agg(lambda s: ', '.join(sorted(set(s))[:4]))
    gf_cad = sorted({b for d, b in zip(c['productos_descripcion'], c['comercio_bandera_nombre']) if GF.search(str(d))})
    m = mae[mae['ean_n'] == r['ean_n']]
    dm = '; '.join(m[col_desc].astype(str).unique()[:2])
    filas.append({'subtipo': r['subtipo'], 'lado': r['lado'], 'ean': r['ean_n'], 'producto': r['producto'],
                  'gf_maestro': r['gf_maestro'], 'gf_sepa': r['gf_sepa_oct26'], 'marca_celiaca': r['es_gf'],
                  'ingr_sin_gluten': r['ingrediente_sin_gluten'], 'banderas_22oct': c['comercio_bandera_nombre'].nunique(),
                  'banderas_que_dicen_sin_tacc': len(gf_cad), 'desc_maestro_sepa': dm,
                  'descs_22oct': ' | '.join(f'{d} [{b}]' for d, b in descs.items())[:300]})
v = pd.DataFrame(filas)
print('\n=== Lado sin TACC: ¿alguna fuente lo publica como sin TACC? ===')
s = v[v['lado'] == 'sin_tacc']
print(s[['subtipo', 'ean', 'producto', 'gf_maestro', 'gf_sepa', 'marca_celiaca', 'banderas_22oct',
         'banderas_que_dicen_sin_tacc']].to_string(index=False))
print('\n-- sin TACC que NINGUNA cadena publica como sin TACC el 22/10 (entran por el Maestro o por la marca):')
for _, r in s[s['banderas_que_dicen_sin_tacc'] == 0].iterrows():
    print(f"   {r['ean']} {r['producto']} | maestro SEPA: {r['desc_maestro_sepa']} | 22/10: {r['descs_22oct']}")
print('\n=== Lado con TACC: ¿alguna cadena lo publica como sin gluten, o es de un ingrediente sin gluten? ===')
t = v[v['lado'] == 'tacc']
print(t[['subtipo', 'ean', 'producto', 'gf_maestro', 'gf_sepa', 'marca_celiaca', 'ingr_sin_gluten', 'banderas_22oct',
         'banderas_que_dicen_sin_tacc']].to_string(index=False))
for _, r in t[(t['banderas_que_dicen_sin_tacc'] > 0) | t['gf_maestro'].fillna(False) | t['ingr_sin_gluten'].fillna(False)].iterrows():
    print(f"   REVISAR {r['ean']} {r['producto']} | {r['descs_22oct']}")
if len(sys.argv) > 6:
    v.to_parquet(sys.argv[6], index=False)
