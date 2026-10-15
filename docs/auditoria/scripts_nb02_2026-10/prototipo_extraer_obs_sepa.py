# PROTOTIPO (2026-10-15, script ad hoc que se portó a la CELDA 19b del nb02; se guarda como referencia).
# Uso: python prototipo_extraer_obs_sepa.py <canasta_analisis_2026-10.xlsx> <2026B.zip> <obs_sep_oct.parquet>
# Extrae del 2026B.zip las observaciones (sucursal x EAN x dia) de sep-26 y oct-26
# para los EANs de las canastas del canasta_analisis (hoja Serie_precios).
import sys, zipfile, gzip, re, time
import numpy as np, pandas as pd
xls, zpath, out = sys.argv[1], sys.argv[2], sys.argv[3]
sp = pd.read_excel(xls, sheet_name='Serie_precios', dtype={'id_producto': str})
eans = {str(e).strip().lstrip('0') for e in sp['id_producto'].unique()}
print('EANs union:', len(eans))
PAT = re.compile(r'^precio_(\d{8})$')
partes = []
z = zipfile.ZipFile(zpath)
for n in ['092026_pais_parte1COMPLETO.csv.gz', '092026_pais_parte2COMPLETO.csv.gz', '102026_pais_parte1COMPLETO.csv.gz']:
    t = time.time(); k = 0
    with z.open(n) as f, gzip.open(f, 'rt', encoding='utf-8', errors='replace') as g:
        for ch in pd.read_csv(g, dtype=str, chunksize=500_000, low_memory=False):
            ch['ean'] = ch['id_producto'].str.strip().str.lstrip('0')
            ch = ch[ch['ean'].isin(eans)]
            if len(ch) == 0: continue
            cols = [c for c in ch.columns if PAT.match(c)]
            lg = ch.melt(id_vars=['id_comercio','id_bandera','id_sucursal','sucursales_provincia','ean'],
                         value_vars=cols, var_name='dia', value_name='precio')
            lg['precio'] = pd.to_numeric(lg['precio'].replace('NA', np.nan), errors='coerce')
            lg = lg[lg['precio'].notna() & (lg['precio'] > 0)]
            lg['dia'] = lg['dia'].str[7:]
            partes.append(lg); k += len(lg)
    print(f'{n}: {k:,} obs en {time.time()-t:.0f}s', flush=True)
d = pd.concat(partes, ignore_index=True)
for c in ['id_comercio','id_bandera','id_sucursal','sucursales_provincia','ean','dia']:
    d[c] = d[c].astype('category')
d.to_parquet(out, index=False)
print('total', len(d), 'filas ->', out)
