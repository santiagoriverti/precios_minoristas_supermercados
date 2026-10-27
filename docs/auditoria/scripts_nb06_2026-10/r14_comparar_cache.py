# Compara el caché del nb06 de Colab (el zip que arma el Drive al bajar output_brecha/_cache/) con el caché local de
# una simulación: mismos meses y, mes a mes, mismos bytes o al menos los mismos datos (pandas, ordenando las filas).
# El zip es un dato bajado: no se extrae si trae rutas absolutas o "..".
# Uso: python -I -X utf8 r14_comparar_cache.py <zip del Drive> <carpeta vacía donde extraerlo> <caché local brecha_v3_xxx>
#      o, con el zip ya extraído: r14_comparar_cache.py <carpeta brecha_v3_xxx del Drive> - <caché local brecha_v3_xxx>
#      (el zip de output_brecha trae varios cachés con los mismos nombres de mes: pasar la carpeta de la clave)
import hashlib
import sys
import zipfile
from pathlib import Path

import pandas as pd

ZIP, DEST, LOCAL = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
if ZIP.is_dir():                      # el caché ya extraído (la carpeta de una clave)
    DEST = ZIP
else:
    with zipfile.ZipFile(ZIP) as z:
        nombres = [i.filename.replace('\\', '/') for i in z.infolist()]
        mal = [n for n in nombres if n.startswith('/') or ':' in n or '..' in n.split('/')]
        if mal:
            sys.exit(f'el zip trae rutas peligrosas, no se extrae: {mal[:5]}')
        DEST.mkdir(parents=True, exist_ok=True)
        z.extractall(DEST)
remoto = {p.name: p for p in DEST.rglob('*.parquet')}
local = {p.name: p for p in LOCAL.glob('*.parquet')}
print(f'Drive: {len(remoto)} meses | local: {len(local)} | solo en el Drive: {sorted(set(remoto) - set(local))} | '
      f'solo local: {sorted(set(local) - set(remoto))}')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
bytes_iguales = datos_iguales = distintos = filas = 0
for n in sorted(set(remoto) & set(local)):
    a, b = pd.read_parquet(remoto[n]), pd.read_parquet(local[n])
    filas += len(a)
    if sha(remoto[n]) == sha(local[n]):
        bytes_iguales += 1
        continue
    k = list(a.columns)
    if list(b.columns) == k and len(a) == len(b) and a.sort_values(k).reset_index(drop=True).equals(
            b.sort_values(k).reset_index(drop=True)):
        datos_iguales += 1
    else:
        distintos += 1
        print(f'  DISTINTO {n}: Drive {a.shape} {k} | local {b.shape} {list(b.columns)}')
print(f'iguales byte a byte: {bytes_iguales}; mismos datos con otros bytes: {datos_iguales}; distintos: {distintos}; '
      f'filas: {filas:,}')
