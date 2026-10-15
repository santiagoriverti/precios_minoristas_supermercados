# Corre la CELDA 19b REAL del nb02 con los datos de oct-26 (2026B.zip + canasta_analisis_2026-10.xlsx)
# y compara cada hoja con el prototipo (desagregacion_canasta_media_2026-10.xlsx). Mide RAM y tiempo.
# Uso: python -I docs/auditoria/scripts_nb02_2026-10/validar_desagregacion_19b.py <repo> <carpeta con 2026B.zip>
#        <canasta_analisis_2026-10.xlsx> <desagregacion_canasta_media_2026-10.xlsx (salida del prototipo)> <carpeta de trabajo>
# Requiere psutil. Resultado del 2026-10-15: todas las hojas iguales al prototipo; pico +357 MB (CELDA 6: +422 MB).
import sys, json, time, threading, shutil, re, zipfile, gzip, gc, hashlib, os
from pathlib import Path
import numpy as np, pandas as pd, psutil
sys.stdout.reconfigure(encoding='utf-8')

REPO, ZIPDIR, XLS, PROTO, WORK = [Path(a) for a in sys.argv[1:6]]
os.chdir(REPO)
NB = REPO / 'notebooks' / '02_evolucion_canasta_representativa.ipynb'
CELDAS = [''.join(c['source']) for c in json.load(open(NB, encoding='utf-8'))['cells'] if c['cell_type'] == 'code']
celda = lambda tag: next(c for c in CELDAS if tag in c[:300])
def bloque(src, ini, fin):
    i0 = src.index(ini); return src[i0:src.index(fin, i0)]

out_dir, tmp_dir = WORK / 'out', WORK / 'tmp'
for d in (out_dir, tmp_dir):
    shutil.rmtree(d, ignore_errors=True); d.mkdir(parents=True)
shutil.copy(XLS, out_dir / 'canasta_analisis_2026-10.xlsx')

env = {'__builtins__': __builtins__, 'np': np, 'pd': pd, 're': re, 'zipfile': zipfile, 'gzip': gzip,
       'shutil': shutil, 'gc': gc, 'hashlib': hashlib, 'Path': Path}
exec(celda('# CONFIGURACI'), env)                    # CELDA 1 real (DESAGREGAR_CANASTAS)
env.update(SEPA_DIR=ZIPDIR, OUTPUT_DIR=out_dir, TMP_DIR=tmp_dir, PERIODO='2026-10', ULTIMO_MES='2026-10')
exec(bloque(celda('# CELDA 3 —'), 'CANT_COLS =', '# ── Construir CANASTAS'), env)
exec(celda('# CELDA 4 —'), env)                      # maestro real de ./data
exec(celda('# CELDA 5 —'), env)
exec(bloque(celda('# CELDA 19 —'), 'from openpyxl.styles', 'out_xls ='), env)

# Lo que dejan las CELDAS 3 y 9 de la corrida real: canastas, serie oficial y variación mensual
sp = pd.read_excel(XLS, sheet_name='Serie_precios', dtype={'id_producto': str})
sp['ean_norm'] = sp['id_producto'].str.strip().str.lstrip('0')
env['CANASTAS'] = {cid: {r.ean_norm: (str(r.descripcion)[:50], int(r.qty), str(r.categoria))
                         for r in g.drop_duplicates('ean_norm').itertuples()}
                   for cid, g in sp.groupby('canasta_id')}
env['df_hist_raw'] = (sp.drop_duplicates(['ean_norm', 'mes'])
                      .rename(columns={'mes': 'anio_mes'})[['ean_norm', 'precio_mediano', 'anio_mes']])
evo = pd.read_excel(XLS, sheet_name='Evolucion_IPC')
env['serie_nac_dict'] = {cid: evo[['mes', f'var_{env["CANASTA_SHORT"][cid]}_%']].rename(
    columns={f'var_{env["CANASTA_SHORT"][cid]}_%': 'variacion_mensual_%'}) for cid in env['CANASTAS']}
print('DESAGREGAR_CANASTAS =', env['DESAGREGAR_CANASTAS'], '| canastas:', list(env['CANASTAS']))

# ── RAM: muestreo del RSS cada 50 ms mientras corre la celda ──────────────────
proc = psutil.Process()
gc.collect()
base = proc.memory_info().rss
pico = [base]; corriendo = [True]
def muestrear():
    while corriendo[0]:
        pico[0] = max(pico[0], proc.memory_info().rss); time.sleep(0.05)
th = threading.Thread(target=muestrear, daemon=True); th.start()
t0 = time.time()
exec(compile(celda('# CELDA 19b —'), '<CELDA 19b>', 'exec'), env)
dur = time.time() - t0
corriendo[0] = False; th.join()
gc.collect()
despues = proc.memory_info().rss
ram = {'base_MB': base / 1e6, 'pico_MB': pico[0] / 1e6, 'incremento_pico_MB': (pico[0] - base) / 1e6,
       'queda_despues_MB': (despues - base) / 1e6, 'segundos': dur}
print('\nRAM/tiempo celda 19b:', {k: round(v, 1) for k, v in ram.items()})

# ── Comparación con el prototipo ─────────────────────────────────────────────
nuevo = pd.read_excel(out_dir / 'canasta_analisis_2026-10.xlsx', sheet_name=None, dtype={'id_producto': str})
proto = pd.read_excel(PROTO, sheet_name=None, dtype={'id_producto': str})
REN = {'med_sep': 'med_ant', 'med_oct': 'med_act', 'med_cierre_sep': 'med_cierre_ant', 'nuevo_oct_pp': 'nuevo_pp',
       'indice_sep_completo=100': 'indice_mes_ant_completo=100'}
comp = {}
for hp in proto:
    hn = 'Resumen_variacion' if hp == 'Resumen' else hp
    a, b = proto[hp].rename(columns=REN), nuevo.get(hn)
    if b is None:
        comp[hp] = 'FALTA EN EL NB02'; continue
    if hp == 'Resumen':      # filas del prototipo, en orden; el nb02 agrega una de control al final
        a = a.iloc[:len(a)]
    res = {'filas': (len(a), len(b)), 'columnas_iguales': list(a.columns) == list(b.columns[:len(a.columns)])}
    n = min(len(a), len(b))
    difs = {}
    for c in a.columns:
        if c not in b.columns: difs[c] = 'falta'; continue
        x, y = a[c].iloc[:n], b[c].iloc[:n]
        xn, yn = pd.to_numeric(x, errors='coerce'), pd.to_numeric(y, errors='coerce')
        if xn.notna().sum() >= max(1, x.notna().sum() // 2) and c not in ('id_producto',):
            m = (xn.isna() != yn.isna()).sum()
            d = (xn - yn).abs().max()
            rel = ((xn - yn).abs() / xn.abs().clip(lower=1e-9)).max()
            if m or (pd.notna(d) and d > 1e-9 and rel > 1e-9):
                difs[c] = f'max_abs {d:.3g} rel {rel:.3g} nan_dif {m}'
        else:
            dist = (x.astype(str) != y.astype(str)).sum()
            if dist: difs[c] = f'{dist} textos distintos (ej. {x[x.astype(str) != y.astype(str)].iloc[0]!r} vs {y[x.astype(str) != y.astype(str)].iloc[0]!r})'
    res['diferencias'] = difs or 'ninguna'
    comp[hp] = res
for k, v in comp.items():
    print(f'\n[{k}]', v)

t = env['desag_dict']['cantidad_03']['totales']
print(f"\nCLAVE: oficial {t['V_OF']:.3f} | panel {t['V_PAN']:.3f} | arrastre {t['ARR']:.3f} | nuevo {t['NUE']:.3f} "
      f"| medianas {t['N_REP']}/{t['N_PROD']} | sucursales {t['N_SUC']} | pares {t['N_PARES']} | fuera {t['N_FUERA']}")
print('Hojas del Excel:', list(nuevo))

# ── Contexto: cuánto ocupa `datos` (CELDA 6 real, mes en curso) ───────────────
gc.collect(); b6 = proc.memory_info().rss
pico = [b6]; corriendo = [True]
th = threading.Thread(target=muestrear, daemon=True); th.start()
env['CANASTA_EANS_NORM'] = set().union(*[set(c) for c in env['CANASTAS'].values()])
env['N_EANS_TOTAL'] = len(env['CANASTA_EANS_NORM'])
t6 = time.time()
exec(celda('# CELDA 6 —'), env)
d6 = time.time() - t6
corriendo[0] = False; th.join(); gc.collect()
ram6 = {'datos_filas': len(env['datos']), 'datos_deep_MB': env['datos'].memory_usage(deep=True).sum() / 1e6,
        'celda6_incremento_pico_MB': (pico[0] - b6) / 1e6, 'celda6_queda_MB': (proc.memory_info().rss - b6) / 1e6,
        'celda6_segundos': d6}
print('\nCELDA 6 (referencia):', {k: round(v, 1) for k, v in ram6.items()})
json.dump({'ram19b': ram, 'ram6': ram6, 'tot': {k: v for k, v in t.items() if k != 'meses'},
           'comp': {k: str(v) for k, v in comp.items()}}, open(WORK / 'resultado.json', 'w'), indent=1)
