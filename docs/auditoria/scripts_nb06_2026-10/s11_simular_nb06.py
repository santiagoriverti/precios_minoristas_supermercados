# Corre las celdas REALES del nb06 (el .ipynb generado) sobre los zips semestrales y guarda los objetos clave para
# compararlos con un cálculo independiente (s12_comparar_simulacion.py). Mide tiempo y pico de RAM de cada celda.
# Uso: python -I -X utf8 s11_simular_nb06.py <repo> <carpeta con YYYYA.zip/YYYYB.zip> <ar.json> <salida>
#                                           [mes_inicio] [--config canasta.json] [--hasta-celda N] [--georef parquet]
#                                           [--ipc IPC.xlsx]
#   --georef: georef_sucursales.parquet del nb09 (departamento de cada sucursal; concentración de la CELDA 8)
#   --ipc: IPC.xlsx del INDEC (hoja Indices_lados), si no está en la carpeta de los zips
#   --config: TIPOS/GRAMOS/VIGENCIA/PRODUCTO/SUBTIPO de un JSON en lugar de los de la CELDA 1 (p. ej. un superconjunto
#             de candidatos para armar el caché una sola vez)
#   --hasta-celda: corre hasta esa celda de código inclusive (5 = lectura) y no guarda objetos
import json, os, sys, time, threading
from pathlib import Path
os.environ.setdefault('MPLBACKEND', 'Agg')
for _st in (sys.stdout, sys.stderr):
    try:
        _st.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
import psutil

args = sys.argv[1:]
CFG = HASTA = GEOREF = None
if '--config' in args:
    i = args.index('--config'); CFG = Path(args[i + 1]); del args[i:i + 2]
if '--hasta-celda' in args:
    i = args.index('--hasta-celda'); HASTA = int(args[i + 1]); del args[i:i + 2]
if '--georef' in args:       # georef_sucursales.parquet del nb09 (departamento de cada sucursal, para la concentración)
    i = args.index('--georef'); GEOREF = Path(args[i + 1]); del args[i:i + 2]
IPC = None
if '--ipc' in args:          # IPC.xlsx del INDEC fuera de la carpeta de los zips
    i = args.index('--ipc'); IPC = Path(args[i + 1]); del args[i:i + 2]
REPO, CARGA, AR, OUT = (Path(a) for a in args[:4])
DESDE = args[4] if len(args) > 4 else '2022-01'
OUT.mkdir(parents=True, exist_ok=True)
cells = [''.join(c['source']) for c in json.load(open(REPO / 'notebooks' / '06_evolucion_brecha_celiaca.ipynb',
                                                       encoding='utf-8'))['cells'] if c['cell_type'] == 'code']
os.chdir(REPO)

# pico de RAM del proceso (muestreo cada 0,5 s)
_proc = psutil.Process()
_pico = {'rss': 0}
def _muestrear():
    while True:
        try:
            _pico['rss'] = max(_pico['rss'], _proc.memory_info().rss)
        except Exception:
            pass
        time.sleep(0.5)
threading.Thread(target=_muestrear, daemon=True).start()

g = {}
t0 = time.time()
exec(cells[0], g)
g.update(SEPA_DIR=str(CARGA), OUTPUT_DIR=str(OUT), MES_INICIO_HISTORICO=DESDE)
if IPC is not None:
    g['IPC_XLSX'] = str(IPC.resolve())
if CFG:
    c = json.loads(CFG.read_text(encoding='utf-8'))
    g.update(TIPOS=c['TIPOS'], GRAMOS=c['GRAMOS'], VIGENCIA={k: tuple(v) for k, v in c['VIGENCIA'].items()},
             PRODUCTO=c.get('PRODUCTO', {}), SUBTIPO=c.get('SUBTIPO', {}))
    print(f'Config de {CFG.name}: {sum(len(t["tacc"]) + len(t["sin_tacc"]) for t in c["TIPOS"].values())} EANs')
exec(cells[1], g)
g['GEOJSON_PATH'] = AR
if GEOREF is not None:
    g['GEOREF_PATH'] = GEOREF
    g['USAR_GEOREF'] = False          # la simulación no consulta la API: lo que no esté en el parquet queda sin departamento
for i, c in enumerate(cells[2:], start=2):
    if HASTA is not None and i > HASTA:
        break
    t1 = time.time(); _pico['rss'] = _proc.memory_info().rss
    exec(c, g)
    print(f'[celda de código {i} en {time.time() - t1:.0f} s | pico de RAM {_pico["rss"] / 1e9:.2f} GB]', flush=True)
print(f'Simulación en {(time.time() - t0) / 60:.1f} min | RAM al final {_proc.memory_info().rss / 1e9:.2f} GB')
if HASTA is not None:
    sys.exit(0)
for k in ('datos_dia', 'bt_sm', 'bt_sub', 'brecha_subtipo', 'brecha_subtipo_anual', 'brecha_tipo', 'brecha_tipo_mensual',
          'brecha_tipo_mensual_bal', 'serie_mensual',
          'serie_mensual_bal', 'brecha_region', 'brecha_empresa', 'brecha_prov', 'control_ean', 'plausibilidad',
          'ponderaciones', 'cobertura_mensual', 'suc_geo', 'brecha_tipo_anual', 'serie_anual', 'serie_anual_bal',
          'brecha_tipo_anual_bal', 'brecha_region_anual', 'brecha_empresa_anual', 'brecha_cadena', 'cobertura_tipo',
          'imputaciones', 'concentracion', 'brecha_suc_mes', 'serie_tpd', 'brecha_tipo_tpd', 'tpd_productos',
          'tpd_ajuste', 'tpd_anual', 'tpd_subtipos', 'precios_atipicos', 'sensibilidad', 'indices_lados',
          'indices_lados_anual', 'disponibilidad', 'disponibilidad_mensual', 'ic_grupos', 'hedonica_grupos',
          'concentracion_modelos', 'competencia_local', 'costo_cba', 'costo_cba_mensual'):
    if k not in g:
        print(f'  (no existe {k})'); continue
    try:
        g[k].to_parquet(OUT / f'sim_{k}.parquet', index=False)
    except Exception as e:          # columnas de tipos mezclados: que no se pierda la corrida
        print(f'  {k}: parquet falló ({e}); se guarda en pickle')
        g[k].to_pickle(OUT / f'sim_{k}.pkl')
print('Objetos guardados en', OUT)
