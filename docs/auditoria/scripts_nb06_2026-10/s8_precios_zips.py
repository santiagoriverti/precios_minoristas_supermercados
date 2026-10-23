# Precio mensual por sucursal x EAN (mediana EXACTA de los precios diarios del mes, de todas las partes) desde los zips
# semestrales del SEPA, para una lista de EANs. Si un mes tiene dos archivos para la misma parte (2024B.zip: 082024
# parte1 COMPLETO = días 1-5 y COMPLETOb = días 1-15) usa el que cubre más días, como el nb08 y el nb09.
# Uso: python -I -X utf8 s8_precios_zips.py <carpeta con YYYYA.zip/YYYYB.zip> <eans.txt> <carpeta de salida> [desde AAAA-MM]
import re, sys, zipfile, gzip, shutil, time, tempfile
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.compute as pc

CARGA, F_EANS, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
DESDE = sys.argv[4] if len(sys.argv) > 4 else '0000-00'
OUT.mkdir(parents=True, exist_ok=True)
EANS = sorted({l.strip().lstrip('0') for l in F_EANS.read_text(encoding='utf-8').splitlines() if l.strip()})
VS = pa.array(EANS, type=pa.string())
PAT = re.compile(r'^(\d{2})(\d{4})_pais_parte(\d+)(COMPLETO\w*)\.csv\.gz$', re.IGNORECASE)
PAT_DIA = re.compile(r'^precio_(\d{8})$')

def dias_header(zf, nombre):
    with zf.open(nombre) as s, gzip.GzipFile(fileobj=s) as g:
        h = g.readline().decode('utf-8', 'replace').strip().split(',')
    return [c for c in h if PAT_DIA.match(c)]

# archivos por (mes, parte): el que tiene más días
arch = {}
for z in sorted(CARGA.glob('*.zip')):
    if not re.match(r'^\d{4}[AB]$', z.stem, re.IGNORECASE):
        continue
    with zipfile.ZipFile(z) as zf:
        for n in zf.namelist():
            m = PAT.match(Path(n).name)
            if not m:
                continue
            mes = f'{m.group(2)}-{m.group(1)}'
            if mes < DESDE:
                continue
            k = (mes, int(m.group(3)))
            nd = len(dias_header(zf, n))
            if k not in arch or nd > arch[k][2]:
                if k in arch:
                    print(f'  {mes} parte {k[1]}: dos archivos, se usa {Path(n).name} ({nd} días) y no {Path(arch[k][1]).name} ({arch[k][2]} días)')
                arch[k] = (z, n, nd)
meses = sorted({k[0] for k in arch})
print(f'{len(EANS)} EANs | meses: {meses[0]} -> {meses[-1]} ({len(meses)})')

TMP = Path(tempfile.mkdtemp(prefix='sepa_nb06_'))
for mes in meses:
    f_out = OUT / f'{mes}.parquet'
    if f_out.exists():
        continue
    t0 = time.time(); largos = []
    for (mm, parte), (z, n, nd) in sorted(arch.items()):
        if mm != mes:
            continue
        tmp = TMP / Path(n).name
        with zipfile.ZipFile(z) as zf, zf.open(n) as s, open(tmp, 'wb') as d:
            shutil.copyfileobj(s, d, length=8 * 1024 * 1024)
        dias = None
        with pa.input_stream(str(tmp), compression='gzip') as st:
            rd = pacsv.open_csv(st, read_options=pacsv.ReadOptions(block_size=64 << 20),
                                convert_options=pacsv.ConvertOptions(
                                    column_types={'id_comercio': pa.string(), 'id_bandera': pa.string(),
                                                  'id_sucursal': pa.string(), 'id_producto': pa.string(),
                                                  'sucursales_provincia': pa.string()},
                                    null_values=['', 'NA', 'NaN', 'null'], strings_can_be_null=True))
            for b in rd:
                if dias is None:
                    dias = [c for c in b.schema.names if PAT_DIA.match(c)]
                ean = pc.utf8_ltrim(b.column('id_producto'), characters='0')
                msk = pc.is_in(ean, value_set=VS)
                if not pc.any(msk).as_py():
                    continue
                t = b.filter(msk).to_pandas()
                t['ean'] = t['id_producto'].str.lstrip('0')
                L = t.melt(id_vars=['id_comercio', 'id_bandera', 'id_sucursal', 'sucursales_provincia', 'ean'],
                           value_vars=dias, var_name='dia', value_name='precio')
                L['precio'] = pd.to_numeric(L['precio'], errors='coerce')
                L = L[L['precio'] > 0]
                largos.append(L[['id_comercio', 'id_bandera', 'id_sucursal', 'sucursales_provincia', 'ean', 'dia',
                                 'precio']])
        tmp.unlink(missing_ok=True)
    if not largos:
        print(f'{mes}: sin datos'); continue
    L = pd.concat(largos, ignore_index=True)
    # una fila por sucursal x producto x día (filas repetidas del SEPA: se toma la mediana del día)
    L = L.groupby(['id_comercio', 'id_bandera', 'id_sucursal', 'ean', 'dia'], as_index=False).agg(
        precio=('precio', 'median'), provincia=('sucursales_provincia', 'first'))
    A = L.groupby(['id_comercio', 'id_bandera', 'id_sucursal', 'ean'], as_index=False).agg(
        precio_mediana=('precio', 'median'), precio_media=('precio', 'mean'), dias=('precio', 'size'),
        provincia=('provincia', 'first'))
    A['mes'] = mes
    A.to_parquet(f_out, index=False)
    print(f'{mes}: {len(A):,} sucursal x EAN | {A["ean"].nunique()} EANs | {time.time()-t0:.0f} s', flush=True)
shutil.rmtree(TMP, ignore_errors=True)
print('listo')
