# Corre las celdas del nb08 NUEVO sobre zips reales de la PC para un período corto y compara las medianas, observaciones y
# promedios con el lector del nb08 VIEJO (copia literal de su CELDA 4) en los mismos meses.
# Uso: python -I -X utf8 validar_real.py <repo> <carpeta zips> <salida> <Excel canasta> <desde> <hasta> <nb viejo .ipynb>
import json, os, re, sys, time
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')

REPO, ZIPS, OUT, XLS, DESDE, HASTA, VIEJO = sys.argv[1:8]
Path(OUT).mkdir(parents=True, exist_ok=True)
os.chdir(REPO)

def celdas(nb):
    return [''.join(c['source']) for c in json.load(open(nb, encoding='utf-8'))['cells'] if c['cell_type'] == 'code']

# ── nb08 nuevo ──
t = time.time()
g = {}
nuevo = celdas(Path(REPO) / 'notebooks' / '08_canasta_diaria.ipynb')
exec(nuevo[0], g)
g.update(SEPA_DIR=ZIPS, OUTPUT_DIR=OUT, CANASTA_EXCEL=XLS, FECHA_INICIO=DESDE, FECHA_FIN=HASTA)
for c in nuevo[1:]:
    exec(c, g)
print(f'\n[nuevo] {time.time() - t:.0f} s')

# ── lector del nb08 viejo (CELDA 4), mismos meses ──
v = celdas(VIEJO)
src = v[3]                                                  # CELDA 4
defs = src[:src.index('# Meses disponibles')]                # funciones, sin el bucle
gv = {'EANS': g['EANS'], 'SEPA_DIR': Path(ZIPS), 'FECHA_INICIO': DESDE}
exec('import zipfile, gzip, io, re, gc, hashlib, time\nfrom pathlib import Path\nimport numpy as np\nimport pandas as pd\n' + defs, gv)
t = time.time()
partes = []
for z, a, s in gv['detectar_semestres']():
    for mes, archs in gv['archivos_por_mes'](z).items():
        if DESDE[:7] <= mes <= HASTA[:7]:
            r = gv['leer_mes'](z, archs)
            partes.append(r)
            print(f'  [viejo] {mes}: {len(archs)} archivos, {r["fecha"].nunique()} días')
viejo = pd.concat(partes, ignore_index=True)
viejo = viejo[(viejo['fecha'] >= pd.Timestamp(DESDE)) & (viejo['fecha'] <= pd.Timestamp(HASTA))]
print(f'[viejo] {time.time() - t:.0f} s')

n = g['precios_dia'].set_index(['fecha', 'ean_norm']).sort_index()
o = viejo.set_index(['fecha', 'ean_norm']).sort_index()
print(f'\nfilas producto-día: nuevo {len(n):,} | viejo {len(o):,} | mismas claves: {n.index.equals(o.index)}')
j = n.join(o, rsuffix='_v', how='inner')
for c in ['precio_mediano', 'precio_promedio', 'n_obs']:
    d = ~np.isclose(j[c], j[c + '_v'], rtol=1e-10, equal_nan=True)
    fechas = sorted({f.strftime('%d/%m/%Y') for f in j.index.get_level_values(0)[d]})
    print(f'  {c}: distintos {int(d.sum()):,} de {len(j):,} | fechas: {fechas[:12]}')
S = g['serie']
print('\nSerie: días', len(S), '| cobertura incompleta:', S.loc[S['cobertura_incompleta'], 'fecha'].dt.strftime('%d/%m').tolist())
print('variación del período: medianas %+.2f%% | apareado %+.2f%%' % (
    (S['valor_canasta'].iloc[-1] / S['valor_canasta'].iloc[0] - 1) * 100,
    (S['valor_canasta_apareado'].iloc[-1] / S['valor_canasta_apareado'].iloc[0] - 1) * 100))
print('desvío estándar de la variación diaria: medianas %.3f | apareado %.3f' % (
    S['variacion_diaria_%'].std(), S['variacion_diaria_apareada_%'].std()))
print('días con |variación| > 1%%: medianas %d | apareado %d' % (
    (S['variacion_diaria_%'].abs() > 1).sum(), (S['variacion_diaria_apareada_%'].abs() > 1).sum()))
print(g['resumen'][['mes', 'variacion_mensual_%', 'variacion_mensual_apareada_%', 'variacion_punta_a_punta_%',
                    'variacion_punta_a_punta_apareada_%']].to_string(index=False))
P = g['panel']
print('\npares por producto-día (mediana / p10):', P['n_pares'].median(), P['n_pares'].quantile(.1),
      '| producto-días sin pares:', int((P['n_pares'] == 0).sum()))
est = sorted(Path(OUT).glob('_cache/diaria_v2_*/estado_*.parquet'))
print('estados guardados:', [(p.name, round(p.stat().st_size / 1e6, 1)) for p in est])
