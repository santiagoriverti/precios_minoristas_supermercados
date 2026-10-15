# Pico de RSS de leer UN archivo del SEPA (oct-26) con distintas variantes, en un proceso limpio.
# Uso: python -I bench_lectura_ean.py <solo_leer|celda6|nueva|nueva_100k|apply> <2026B.zip> <tmpdir> <canasta_analisis>
# Resultado del 2026-10-15 (oct-26, un archivo): .str.strip().str.lstrip('0') +2.154 MB; .apply(normalizar) +191 MB.
import sys, time, threading, gc, gzip, zipfile, shutil
from pathlib import Path
import numpy as np, pandas as pd, psutil

var, ZIP, TMP, XLS = sys.argv[1], sys.argv[2], Path(sys.argv[3]), sys.argv[4]
TMP.mkdir(parents=True, exist_ok=True)
sp = pd.read_excel(XLS, sheet_name='Serie_precios', dtype={'id_producto': str})
media = set(sp.loc[sp['canasta_id'] == 'cantidad_03', 'id_producto'].str.strip().str.lstrip('0'))
union = set(sp['id_producto'].str.strip().str.lstrip('0'))
ARCH = '102026_pais_parte1COMPLETO.csv.gz'
tmp_p = TMP / ARCH
with zipfile.ZipFile(ZIP) as zf, zf.open(ARCH) as s, open(tmp_p, 'wb') as d:
    shutil.copyfileobj(s, d, length=4 * 1024 * 1024)

proc = psutil.Process(); gc.collect()
base = proc.memory_info().rss; pico = [base]; on = [True]
def mu():
    while on[0]:
        pico[0] = max(pico[0], proc.memory_info().rss); time.sleep(0.02)
th = threading.Thread(target=mu, daemon=True); th.start(); t0 = time.time()

cs = 100_000 if var.endswith('100k') else 300_000
n = 0
with gzip.open(tmp_p, 'rt', encoding='utf-8', errors='replace') as g:
    for ch in pd.read_csv(g, dtype=str, chunksize=cs, low_memory=False):
        if var.startswith('celda6'):
            ch['ean_norm'] = ch['id_producto'].apply(lambda s: str(s).strip().lstrip('0') or '0')
            ch = ch[ch['ean_norm'].isin(union)].copy()
        elif var.startswith('nueva'):
            e = ch['id_producto'].str.strip().str.lstrip('0')
            sel = e.isin(media)
            ch, e = ch[sel], e[sel]
        elif var.startswith('apply'):
            e = ch['id_producto'].apply(lambda s: None if pd.isna(s) else (str(s).strip().lstrip('0') or '0'))
            sel = e.isin(media)
            ch, e = ch[sel], e[sel]
        elif var.startswith('solo_leer'):
            pass
        n += len(ch)
on[0] = False; th.join()
print(f'{var}: pico +{(pico[0] - base) / 1e6:,.0f} MB | {time.time() - t0:,.0f} s | filas {n:,}')
tmp_p.unlink()
