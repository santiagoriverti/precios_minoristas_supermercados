# Que tan cerca esta la regla "mediana > 10.000 = centavos" de dispararse con precios en pesos.
#   nb09: mediana del precio promedio de cada sucursal x producto de TODO el archivo.
#   nb02 CELDA 9 / nb08: mediana de las observaciones sucursal x dia de los EANs de las canastas.
# Uso: python -I -X utf8 r6_umbral_centavos.py <zip> <archivo> <canasta_analisis_AAAA-MM.xlsx>
import sys, re, gzip, zipfile
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.compute as pc

zp, nombre, xls = sys.argv[1], sys.argv[2], sys.argv[3]
SP = pd.read_excel(xls, sheet_name='Serie_precios', engine='calamine', dtype={'id_producto': str})
EANS = set(SP['id_producto'].astype(str).str.lstrip('0'))
print('EANs de las canastas:', len(EANS))
with zipfile.ZipFile(zp) as zf:
    with zf.open(nombre) as s0, gzip.open(s0, 'rt', encoding='utf-8', errors='replace') as g:
        hdr = [c.strip() for c in g.readline().split(',')]
    cols_p = [c for c in hdr if re.match(r'^precio_\d{8}$', c)]
    prom, obs_can = [], []
    tipos = {'id_producto': pa.string(), **{c: pa.float64() for c in cols_p}}
    with zf.open(nombre) as s0, pa.CompressedInputStream(pa.PythonFile(s0, mode='r'), 'gzip') as s:
        for bl in pacsv.open_csv(s, read_options=pacsv.ReadOptions(block_size=32 << 20),
                                 convert_options=pacsv.ConvertOptions(column_types=tipos, include_columns=['id_producto'] + cols_p,
                                                                      null_values=['NA', ''], strings_can_be_null=True)):
            P = np.column_stack([pc.fill_null(bl.column(c), np.nan).to_numpy(zero_copy_only=False) for c in cols_p])
            V = np.isfinite(P) & (P > 0)
            n = V.sum(axis=1)
            ok = n > 0
            prom.append((np.where(V, P, 0).sum(axis=1)[ok] / n[ok]).astype(np.float32))
            ids = pc.utf8_ltrim(pc.fill_null(pc.utf8_trim_whitespace(bl.column('id_producto')), ''), characters='0')
            enc = np.asarray(pc.is_in(ids, value_set=pa.array(list(EANS))).to_numpy(zero_copy_only=False), bool)
            if enc.any():
                obs_can.append(P[enc][V[enc]])
prom = np.concatenate(prom); obs_can = np.concatenate(obs_can)
print(f'{nombre}: regla del nb09 (mediana del promedio sucursal x producto) = {np.median(prom):,.0f} '
      f'({len(prom):,} filas)')
print(f'{nombre}: regla del nb02 CELDA 9 / nb08 (mediana de las obs. de las canastas) = {np.median(obs_can):,.0f} '
      f'({len(obs_can):,} obs.)')
print('cuantiles del promedio sucursal x producto:', {q: round(float(np.quantile(prom, q))) for q in (.25, .5, .75)})
