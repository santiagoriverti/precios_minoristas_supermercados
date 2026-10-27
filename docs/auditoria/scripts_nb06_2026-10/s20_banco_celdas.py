# Banco de prueba persistente de la CELDA 8c: corre las celdas reales del notebook hasta la 8b (con el caché de la
# simulación) y después queda esperando trabajos: cada <jobs>/<nombre>.py se ejecuta en el mismo espacio de nombres,
# su salida va a <nombre>.log y el archivo pasa a <nombre>.hecho. Así se itera la 8c sin releer todo cada vez.
# Uso: python -I -X utf8 s20_banco_celdas.py <repo> <carga> <ar.json> <salida> <georef.parquet> <jobs> [notebook]
# (rutas absolutas; <salida> con el caché de una simulación copiado en _cache/ para no releer el SEPA). Un trabajo
# típico: exec(open('celda_8c.py', encoding='utf-8').read(), globals()) con la celda editada. Un .py con
# raise SystemExit lo cierra.
import contextlib, io, json, os, sys, time, traceback
from pathlib import Path
os.environ.setdefault('MPLBACKEND', 'Agg')
for _st in (sys.stdout, sys.stderr):
    try:
        _st.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
REPO, CARGA, AR, OUT, GEOREF, JOBS = (Path(a).resolve() for a in sys.argv[1:7])   # absolutas: después se cambia al repo
NB = sys.argv[7] if len(sys.argv) > 7 else '06_evolucion_brecha_celiaca.ipynb'
JOBS.mkdir(parents=True, exist_ok=True)
cells = [''.join(c['source']) for c in json.load(open(REPO / 'notebooks' / NB, encoding='utf-8'))['cells']
         if c['cell_type'] == 'code']
os.chdir(REPO)
g = {}
t0 = time.time()
exec(cells[0], g)
g.update(SEPA_DIR=str(CARGA), OUTPUT_DIR=str(OUT), MES_INICIO_HISTORICO=g.get('MES_INICIO_HISTORICO', '2022-01'))
exec(cells[1], g)
g['GEOJSON_PATH'] = AR
g['GEOREF_PATH'] = GEOREF
g['USAR_GEOREF'] = False
for i, c in enumerate(cells[2:9], start=2):
    t1 = time.time()
    exec(c, g)
    print(f'[celda de código {i} en {time.time() - t1:.0f} s]', flush=True)
g['_CELLS'] = cells
print(f'LISTO en {(time.time() - t0) / 60:.1f} min; esperando trabajos en {JOBS}', flush=True)
(JOBS / '_listo').write_text('ok', encoding='utf-8')
while True:
    for _j in sorted(JOBS.glob('*.py')):
        _buf = io.StringIO()
        t1 = time.time()
        with contextlib.redirect_stdout(_buf), contextlib.redirect_stderr(_buf):
            try:
                exec(_j.read_text(encoding='utf-8'), g)
                print(f'\n[OK en {time.time() - t1:.0f} s]')
            except SystemExit:
                print('\n[FIN pedido]')
                (_j.with_suffix('.log')).write_text(_buf.getvalue(), encoding='utf-8')
                _j.replace(_j.with_suffix('.hecho'))
                sys.exit(0)
            except Exception:
                traceback.print_exc()
                print(f'\n[FALLÓ a los {time.time() - t1:.0f} s]')
        (_j.with_suffix('.log')).write_text(_buf.getvalue(), encoding='utf-8')
        _j.replace(_j.with_suffix('.hecho'))
        print(f'trabajo {_j.name} en {time.time() - t1:.0f} s', flush=True)
    time.sleep(1)
