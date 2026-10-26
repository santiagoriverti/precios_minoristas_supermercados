# Compara dos mapas por sucursal del nb06 (mapa_sucursales_brecha_MMAAAA.html): reemplaza los identificadores aleatorios
# de Folium (_<32 hex>) por un número en orden de aparición y compara el resto; si difieren, muestra el primer tramo
# distinto. Además valida el bloque de datos (JSON de los popups): sucursales y mes de cada una.
# Uso: python -I -X utf8 r15_comparar_mapas.py <mapa A (p. ej. Colab)> <mapa B (p. ej. la simulación)>
import collections
import hashlib
import json
import re
import sys
from pathlib import Path

ID = re.compile(r'(?<=_)([0-9a-f]{32})(?![0-9a-f])')
DATOS = re.compile(r'<script type="application/json" id="_pd_json">(.*?)</script>', flags=re.S)


def normalizar(s):
    vistos = {}
    def rep(m):
        vistos.setdefault(m.group(1), len(vistos))
        return f'ID{vistos[m.group(1)]}'
    return ID.sub(rep, s), len(vistos)


textos = [Path(f).read_text(encoding='utf-8') for f in sys.argv[1:3]]
for nombre, t in zip('AB', textos):
    m = DATOS.search(t)
    d = json.loads(m.group(1)) if m else {}
    meses = collections.Counter(e.get('m') for e in d.values() if isinstance(e, dict))
    print(f'{nombre}: {len(d):,} sucursales en el JSON de los popups; mes del dato: {dict(sorted(meses.items()))}')
(a, na), (b, nb) = (normalizar(t) for t in textos)
print(f'A: {len(a):,} caracteres, {na} ids de Folium | B: {len(b):,} caracteres, {nb} ids de Folium')
print('sha256 sin los ids:', hashlib.sha256(a.encode()).hexdigest()[:16], hashlib.sha256(b.encode()).hexdigest()[:16])
if a == b:
    print('IGUALES (salvo los identificadores aleatorios de Folium)')
else:
    i = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
    print(f'primera diferencia en el carácter {i:,}:')
    print('  A:', repr(a[max(0, i - 150):i + 150]))
    print('  B:', repr(b[max(0, i - 150):i + 150]))
