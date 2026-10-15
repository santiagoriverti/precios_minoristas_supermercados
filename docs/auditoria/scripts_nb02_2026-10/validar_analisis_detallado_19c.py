# Corre las CELDAS 19b y 19c REALES con oct-26 (2026B.zip: jul-oct) y DETALLE_MESES=2 y controla la hoja
# analisis_detallado contra: la serie oficial (Evolucion_IPC), la Serie_precios (rubros), la columna de
# control var_mediana_grupo_% de la 19b (grupos, oct) y las observaciones del prototipo (semanas).
# Uso: python -I docs/auditoria/scripts_nb02_2026-10/validar_analisis_detallado_19c.py <repo> <carpeta con 2026B.zip>
#        <canasta_analisis_2026-10.xlsx> <canasta_representativa con la hoja Selección y la columna rubro>
#        <obs_sep_oct.parquet (salida de prototipo_extraer_obs_sepa.py)> <carpeta de trabajo>
# Requiere psutil. Resultado del 2026-10-15: 6 controles OK; 19c pico +307 MB, ~2-2,5 min por mes viejo leído.
import sys, json, time, threading, shutil, re, zipfile, gzip, gc, hashlib, os, statistics
from pathlib import Path
import numpy as np, pandas as pd, psutil
sys.stdout.reconfigure(encoding='utf-8')

REPO, ZIPDIR, XLS, SELX, PARQ, WORK = [Path(a) for a in sys.argv[1:7]]
os.chdir(REPO)
NB = REPO / 'notebooks' / '02_evolucion_canasta_representativa.ipynb'
CELDAS = [''.join(c['source']) for c in json.load(open(NB, encoding='utf-8'))['cells'] if c['cell_type'] == 'code']
celda = lambda tag: next(c for c in CELDAS if tag in c[:300])
def bloque(src, ini, fin):
    i0 = src.index(ini); return src[i0:src.index(fin, i0)]

out_dir, tmp_dir, cache_dir = WORK / 'out', WORK / 'tmp', WORK / 'cache'
for d in (out_dir, tmp_dir):
    shutil.rmtree(d, ignore_errors=True); d.mkdir(parents=True)
cache_dir.mkdir(parents=True, exist_ok=True)
shutil.copy(XLS, out_dir / 'canasta_analisis_2026-10.xlsx')

env = {'__builtins__': __builtins__, 'np': np, 'pd': pd, 're': re, 'zipfile': zipfile, 'gzip': gzip,
       'shutil': shutil, 'gc': gc, 'hashlib': hashlib, 'Path': Path}
exec(celda('# CONFIGURACI'), env)
env.update(SEPA_DIR=ZIPDIR, OUTPUT_DIR=out_dir, TMP_DIR=tmp_dir, CACHE_DIR=cache_dir, USE_CACHE=True,
           PERIODO='2026-10', ULTIMO_MES='2026-10', DETALLE_MESES=2)
print('config:', {k: env[k] for k in ('DESAGREGAR_CANASTAS', 'DETALLE_CANASTA', 'DETALLE_MESES', 'DETALLE_MIN_SUCURSALES')})
exec(bloque(celda('# CELDA 3 —'), 'CANT_COLS =', '# ── Construir CANASTAS'), env)
exec(celda('# CELDA 4 —'), env)
exec(celda('# CELDA 5 —'), env)
exec(bloque(celda('# CELDA 19 —'), 'from openpyxl.styles', 'out_xls ='), env)

sp = pd.read_excel(XLS, sheet_name='Serie_precios', dtype={'id_producto': str})
sp['ean_norm'] = sp['id_producto'].str.strip().str.lstrip('0')
env['CANASTAS'] = {cid: {r.ean_norm: (str(r.descripcion)[:50], int(r.qty), str(r.categoria))
                         for r in g.drop_duplicates('ean_norm').itertuples()}
                   for cid, g in sp.groupby('canasta_id')}
xs = pd.ExcelFile(SELX)
sel = xs.parse([n for n in xs.sheet_names if n.startswith('Selecci')][0], dtype={'id_producto': str})
sel['ean_norm'] = sel['id_producto'].str.strip().str.lstrip('0')
exec(bloque(celda('# CELDA 3 —'), '# Rubro SEPA por EAN', 'N_EANS_TOTAL'), {**env, 'sel': sel, 'CANASTAS': env['CANASTAS']}, env)
env['df_hist_raw'] = (sp.drop_duplicates(['ean_norm', 'mes'])
                      .rename(columns={'mes': 'anio_mes'})[['ean_norm', 'precio_mediano', 'anio_mes']])
evo = pd.read_excel(XLS, sheet_name='Evolucion_IPC')
env['serie_nac_dict'] = {cid: evo[['mes', f'canasta_{env["CANASTA_SHORT"][cid]}', f'var_{env["CANASTA_SHORT"][cid]}_%']]
                         .rename(columns={f'canasta_{env["CANASTA_SHORT"][cid]}': 'canasta_nacional_ponderada',
                                          f'var_{env["CANASTA_SHORT"][cid]}_%': 'variacion_mensual_%'})
                         for cid in env['CANASTAS']}
print('RUBRO_EAN Media:', pd.Series([env['RUBRO_EAN'].get(e, '?') for e in env['CANASTAS']['cantidad_03']]).value_counts().to_dict())

proc = psutil.Process()
def medir(nombre, src):
    gc.collect(); b = proc.memory_info().rss; pico = [b]; on = [True]
    def mu():
        while on[0]:
            pico[0] = max(pico[0], proc.memory_info().rss); time.sleep(0.03)
    th = threading.Thread(target=mu, daemon=True); th.start(); t = time.time()
    exec(compile(src, f'<{nombre}>', 'exec'), env)
    on[0] = False; th.join(); gc.collect()
    print(f'PERFIL {nombre}: pico +{(pico[0] - b) / 1e6:,.0f} MB | queda +{(proc.memory_info().rss - b) / 1e6:,.0f} MB '
          f'| {time.time() - t:,.0f} s', flush=True)

medir('CELDA 19b', celda('# CELDA 19b —'))
medir('CELDA 19c', celda('# CELDA 19c —'))
dl = env['detalle_long']
fila = lambda sec, f: dl[(dl['seccion'] == sec) & (dl['fila'] == f)].set_index('periodo')
fallas = []
def chequear(ok, msg):
    print(('  OK    ' if ok else '  FALLA ') + msg)
    if not ok: fallas.append(msg)

# 1) Total = serie oficial
t = fila('nacional', 'Total Media')
ev = evo.set_index('mes')
ok = all(abs(t.loc[p, 'variacion_%'] - ev.loc[p, 'var_media_%']) < 1e-9 for p in ['2026-08', '2026-09', '2026-10'])
ok &= all(abs(t.loc[p, 'indice'] - ev.loc[p, 'canasta_media'] / ev.loc['2026-07', 'canasta_media'] * 100) < 1e-9
          for p in ['2026-08', '2026-09', '2026-10'])
chequear(ok, f'Total = serie oficial (var oct {t.loc["2026-10", "variacion_%"]:.4f}, sep {t.loc["2026-09", "variacion_%"]:.4f})')

# 2) Rubros = cálculo directo con la Serie_precios
m = sp[sp['canasta_id'] == 'cantidad_03'].copy()
m['rubro'] = m['ean_norm'].map(env['RUBRO_EAN'])
pv = m.pivot_table(index='rubro', columns='mes', values='costo_item', aggfunc='sum')
ok = True
for r in pv.index:
    f = fila('rubro', r)
    for p in ['2026-08', '2026-09', '2026-10']:
        ok &= abs(f.loc[p, 'indice'] - pv.loc[r, p] / pv.loc[r, '2026-07'] * 100) < 1e-9
    ok &= abs(f['pond'].iloc[0] - pv.loc[r, '2026-07'] / pv['2026-07'].sum() * 100) < 1e-9
chequear(ok, f'{len(pv)} rubros = Serie_precios (índice base jul-26 y Pond)')

# 3) Grupos, var oct = control var_mediana_grupo_% de la 19b
hoj = pd.read_excel(out_dir / 'canasta_analisis_2026-10.xlsx', sheet_name=None)
ok, n = True, 0
for sec, hoja, col in (('region', 'Regiones', 'region'), ('provincia', 'Provincias', 'provincia'),
                       ('cadena', 'Cadenas', 'cadena'), ('tipo', 'Tipo_sucursal', 'tipo')):
    ctl = hoj[hoja].set_index(col)['var_mediana_grupo_%']
    for g in dl.loc[dl['seccion'] == sec, 'fila'].unique():
        n += 1
        v = fila(sec, g).loc['2026-10', 'variacion_%']
        if abs(v - ctl[g]) > 1e-9:
            ok = False; print('     ', sec, g, v, ctl[g])
chequear(ok, f'{n} grupos: variación oct = var_mediana_grupo_% de la 19b (método oficial dentro del grupo)')

# 4) Semanas: Total y AMBA contra las observaciones del prototipo
obs = pd.read_parquet(PARQ)
for c in ['id_comercio', 'id_bandera', 'id_sucursal', 'ean', 'dia']:
    obs[c] = obs[c].astype(str)
media = set(env['CANASTAS']['cantidad_03'])
obs = obs[obs['ean'].isin(media)]
q = {e: v[1] for e, v in env['CANASTAS']['cantidad_03'].items()}
obs['mes'] = obs['dia'].str[:6]
obs['sem'] = obs['mes'] + '-S' + np.minimum((obs['dia'].str[6:].astype(int) - 1) // 7, 3).add(1).astype(str)
suc = env['_SUC']
k2reg = dict(zip(suc['id_comercio'] + '|' + suc['id_bandera'] + '|' + suc['id_sucursal'], suc['region']))
obs['region'] = (obs['id_comercio'] + '|' + obs['id_bandera'] + '|' + obs['id_sucursal']).map(k2reg)
def enl(a, b):
    c = [e for e in a.index if e in b.index and pd.notna(a[e]) and pd.notna(b[e])]
    return sum(q[e] * b[e] for e in c) / sum(q[e] * a[e] for e in c)
ok = True
for nombre, sub, f in (('Total', obs, t), ('AMBA', obs[obs['region'] == 'AMBA'], fila('region', 'AMBA'))):
    ref = sub[sub['mes'] == '202609'].groupby('ean')['precio'].median()
    for s_ in ['202609-S1', '202609-S2', '202609-S3', '202609-S4', '202610-S1', '202610-S2']:
        w = sub[sub['sem'] == s_].groupby('ean')['precio'].median()
        p = f'{s_[:4]}-{s_[4:6]}-{s_[-2:]}'
        esp = f.loc['2026-09', 'indice'] * enl(ref, w)
        if abs(f.loc[p, 'indice'] - esp) > 1e-7:
            ok = False; print('     ', nombre, p, f.loc[p, 'indice'], esp)
chequear(ok, 'semanas de Total y AMBA = observaciones del prototipo (índice sep x canasta semana / canasta sep)')
chequear(sorted(dl['periodo'].unique()) == ['2026-08', '2026-09', '2026-09-S1', '2026-09-S2', '2026-09-S3',
                                            '2026-09-S4', '2026-10', '2026-10-S1', '2026-10-S2'],
         'columnas: ago, sep, oct parcial, 4 semanas de sep, 1S y 2S oct (oct al 15: la 3S tiene 1 día)')

# 5) El Excel
from openpyxl import load_workbook
wb = load_workbook(out_dir / 'canasta_analisis_2026-10.xlsx')
chequear(wb.sheetnames[0] == 'analisis_detallado' and len(wb.sheetnames) == 39,
         f'primera hoja {wb.sheetnames[0]}; {len(wb.sheetnames)} hojas (25 + 13 de la 19b + 1)')
ws = wb.worksheets[0]
print('\n--- analisis_detallado (primeras 70 filas, 10 columnas) ---')
for r in range(1, 71):
    vals = [ws.cell(r, c).value for c in range(1, 12)]
    if any(v is not None for v in vals):
        print(' | '.join('' if v is None else (f'{v:.2f}' if isinstance(v, float) else str(v))[:38] for v in vals))
print('\nRESULTADO:', 'OK' if not fallas else f'FALLA ({len(fallas)})')
