# Arma el caché del nb06 para la canasta de la CELDA 1 filtrando el caché leído con un superconjunto de EANs (s11
# --config): cada mes guardado tiene una fila por sucursal x EAN, así que quedarse con los EANs de la canasta da lo mismo
# que leer el SEPA con esa canasta (el factor centavos/pesos sale de EANs de referencia, no de la canasta).
# Uso: python -I -X utf8 s15_filtrar_cache.py <repo> <carpeta _cache/brecha_v3_<clave> del superconjunto> <salida de s11>
import hashlib, json, re, sys
from pathlib import Path
import pandas as pd

REPO, SUPER, OUT = (Path(a) for a in sys.argv[1:4])
cells = [''.join(c['source']) for c in json.load(open(REPO / 'notebooks' / '06_evolucion_brecha_celiaca.ipynb',
                                                       encoding='utf-8'))['cells'] if c['cell_type'] == 'code']
g = {}
exec(cells[0], g)

def _norm_ean(_e):                       # igual que la CELDA 4
    _l = re.sub(r'\D', '', str(_e))
    return (_l.lstrip('0') or '0') if _l else None

assert not g.get('USAR_REGLA_NOMBRE'), 'con USAR_REGLA_NOMBRE la canasta depende del maestro: no se puede filtrar'
E = {_norm_ean(e) for t in g['TIPOS'].values() for lado in ('tacc', 'sin_tacc') for e in t.get(lado, {})}
E.discard(None)
clave = hashlib.md5('|'.join(sorted(E)).encode()).hexdigest()[:8]
dst = OUT / '_cache' / f'brecha_v3_{clave}'
dst.mkdir(parents=True, exist_ok=True)
n, vistos = 0, set()
for f in sorted(SUPER.glob('????-??.parquet')):
    d = pd.read_parquet(f)
    vistos |= set(d['ean_norm'])
    d[d['ean_norm'].isin(E)].to_parquet(dst / f.name, index=False)
    n += 1
print(f'{len(E)} EANs de la canasta | clave {clave} | {n} meses filtrados -> {dst}')
if E - vistos:
    print(f'AVISO: EANs de la canasta que no están en el caché del superconjunto (hay que leerlos): {sorted(E - vistos)}')
