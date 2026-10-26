# Evidencia de la condición sin TACC de las marcas dudosas: todos sus productos en el Maestro interno, en el maestro
# del SEPA (Drive) y en la tabla de continuidad (descripción del Maestro y la del SEPA del 22/10, marca de sin TACC).
# Uso: python -I -X utf8 r23_marcas_dudosas.py <Maestro interno .xlsx> <maestro_sepa_completo.csv.gz> <continuidad.parquet>
#                                            <regex de marcas> [regex de prefijos EAN]
import re
import sys

import pandas as pd

pd.set_option('display.width', 260); pd.set_option('display.max_columns', 30); pd.set_option('display.max_colwidth', 80)
rx = re.compile(sys.argv[4], re.I)
pref = re.compile(sys.argv[5]) if len(sys.argv) > 5 else None
mi = pd.read_excel(sys.argv[1], dtype=str)
print('Maestro interno:', mi.shape, list(mi.columns))
ms = pd.read_csv(sys.argv[2], dtype=str)
co = pd.read_parquet(sys.argv[3])
print('continuidad:', co.shape)


def filtra(df, cols, col_id):
    m = pd.Series(False, index=df.index)
    for c in cols:
        m |= df[c].astype(str).str.contains(rx)
    if pref is not None:
        m |= df[col_id].astype(str).str.lstrip('0').str.match(pref)
    return df[m]


cid = next(c for c in mi.columns if 'ean' in c.lower() or c.lower() in ('id', 'codigo', 'código'))
cdesc = [c for c in mi.columns if 'desc' in c.lower() or 'marca' in c.lower() or 'nombre' in c.lower()]
x = filtra(mi, cdesc, cid)
print(f'\n=== Maestro interno ({cid}; {cdesc}): {len(x)} filas')
print(x.to_string(index=False, max_colwidth=70)[:9000])
y = filtra(ms, ['producto_descripcion', 'producto_marca'], 'producto_sepa_id')
print(f'\n=== Maestro SEPA: {len(y)} filas')
print(y.to_string(index=False)[:6000])
z = filtra(co, ['descripcion', 'marca', 'desc_sepa_22oct'], 'id')
cols = [c for c in ['id', 'tipo', 'descripcion', 'marca', 'desc_sepa_22oct', 'sin_tacc', 'gf_maestro', 'gf_sepa_oct26',
                    'con_gluten_explicito', 'ingrediente_sin_gluten', 'primer_mes', 'ultimo_mes', 'suc_mes_mediana']
        if c in z.columns]
print(f'\n=== continuidad: {len(z)} filas')
print(z[cols].sort_values('id').to_string(index=False)[:9000])
