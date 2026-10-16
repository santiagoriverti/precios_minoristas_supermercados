# Cuadro 1 (CELDA 8 REAL del nb02) de una corrida con la provincia de antes y con la de la CELDA 7 vigente.
# Toma las sucursales de la corrida de sus hojas Sucs_* (costo por sucursal y provincia de entonces), corre la CELDA 4
# y la geografia de la CELDA 7 vigente sobre el maestro (con ar.json) para la provincia nueva, y corre la CELDA 8 con
# cada una. Controla que con la provincia de antes reproduce las hojas Prov_* de la corrida, y muestra el cambio.
# Uso: python -I docs/auditoria/scripts_nb02_2026-10/cuadro1_reclasificacion.py <repo> <ar.json> <canasta_analisis.xlsx>
# Resultado del 2026-10-16 (BUG-44, oct-26 al 15/10): ver docs/AUDITORIA_2026-10-16_nb02.md, seccion 11.
import contextlib, io, json, os, re, sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
pd.set_option('display.width', 250)
REPO, GEO, XLS = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]).resolve()
os.chdir(REPO)
CELDAS = [''.join(c['source']) for c in json.load(open(REPO / 'notebooks/02_evolucion_canasta_representativa.ipynb',
                                                    encoding='utf-8'))['cells'] if c['cell_type'] == 'code']
celda = lambda t: next(c for c in CELDAS if t in c[:300])
bloque = lambda s, a, b: s[s.index(a):s.index(b, s.index(a))]
env = {'np': np, 'pd': pd, 're': re, 'Path': Path, 'SEPA_DIR': '.', 'GEOJSON_PATH': GEO}
with contextlib.redirect_stdout(io.StringIO()):
    exec(celda('# CELDA 4 —'), env)
exec(bloque(celda('# CELDA 7 —'), '# ── Provincia por coordenadas', '# ── Calcular canasta por sucursal'), env)
exec(bloque(celda('# CELDA 3 —'), 'CANASTA_NAMES = {', 'CANASTA_LINESTYLES'), env)
exec(bloque(celda('# CELDA 6 —'), 'def _pmean(_s):', 'ref_e ='), env)
k = ['id_comercio', 'id_bandera', 'id_sucursal']
nueva = env['suc_geo_clean'][k + ['PROVINCIA_NORM']].astype(str).drop_duplicates(k)

xl = pd.ExcelFile(XLS)
SH = env['CANASTA_SHORT']
ACT = [c for c in env['CANASTA_NAMES'] if f'Sucs_{SH[c]}' in xl.sheet_names]
geo_v, geo_n = {}, {}
for c in ACT:
    s = xl.parse(f'Sucs_{SH[c]}')
    for col in k:
        s[col] = s[col].astype(str)
    geo_v[c] = s
    m = s.drop(columns='PROVINCIA_NORM').merge(nueva, on=k, how='left')
    assert m['PROVINCIA_NORM'].notna().all() and len(m) == len(s)
    geo_n[c] = m
C8 = celda('# CELDA 8 —')


def cuadro(geo):
    e = dict(env, canasta_geo_dict=geo, CANASTAS_ACTIVAS=ACT, PERIODO='x', NOMBRE_MES_TITLE='x')
    with contextlib.redirect_stdout(io.StringIO()):
        exec(C8, e)
    return e['serie_prov_dict'], e['prom_nac_dict'], e['prom_nac_prom_dict']


pv, nv, npv = cuadro(geo_v)
pn, nn, npn = cuadro(geo_n)

ok = True
for c in ACT:
    hoja = xl.parse(f'Prov_{SH[c]}').set_index('provincia')
    a = pv[c].set_index('provincia')
    ok &= np.allclose(a.loc[hoja.index, 'canasta_total'], hoja['canasta_total'], rtol=0, atol=1e-6)
    ok &= np.allclose(a.loc[hoja.index, 'canasta_total_prom'], hoja['canasta_total_prom'], rtol=0, atol=1e-6)
print('control: con la provincia de antes la CELDA 8 reproduce las hojas Prov_* de la corrida:', 'OK' if ok else 'FALLA')

cam = geo_v[ACT[0]].merge(geo_n[ACT[0]][k + ['PROVINCIA_NORM']], on=k, suffixes=('_antes', '_ahora'))
cam = cam[cam['PROVINCIA_NORM_antes'] != cam['PROVINCIA_NORM_ahora']]
print(f'\nsucursales de la canasta {env["CANASTA_NAMES"][ACT[0]]} que cambian de provincia: {len(cam)}')
print(cam.groupby(['PROVINCIA_NORM_antes', 'PROVINCIA_NORM_ahora']).size().rename('sucursales').reset_index()
      .sort_values('sucursales', ascending=False).to_string(index=False))

for c in ACT:
    a = pv[c].set_index('provincia')[['canasta_total']]
    b = pn[c].set_index('provincia')[['canasta_total']]
    na = geo_v[c].groupby('PROVINCIA_NORM').size()
    nb = geo_n[c].groupby('PROVINCIA_NORM').size()
    t = a.join(b, how='outer', lsuffix='_antes', rsuffix='_ahora')
    t['suc_antes'], t['suc_ahora'] = na.reindex(t.index), nb.reindex(t.index)
    t['vs_pais_antes_%'] = (t['canasta_total_antes'] / nv[c] - 1) * 100
    t['vs_pais_ahora_%'] = (t['canasta_total_ahora'] / nn[c] - 1) * 100
    t['dif_%'] = (t['canasta_total_ahora'] / t['canasta_total_antes'] - 1) * 100
    camb = t[(t['suc_antes'] != t['suc_ahora']) | (t['dif_%'].abs() > 1e-9)]
    print(f'\n== {env["CANASTA_NAMES"][c]}: pais (Cuadro 1) {nv[c]:,.0f} -> {nn[c]:,.0f} '
          f'({(nn[c] / nv[c] - 1) * 100:+.3f}%); promedio {npv[c]:,.0f} -> {npn[c]:,.0f}')
    print(camb.round(2).to_string())
    for et, d, n in (('antes', pv[c], nv[c]), ('ahora', pn[c], nn[c])):
        lo, hi = d.loc[d['canasta_total'].idxmin()], d.loc[d['canasta_total'].idxmax()]
        print(f'   {et}: mas barata {lo["provincia"]} {lo["canasta_total"]:,.0f} ({(lo["canasta_total"] / n - 1) * 100:+.2f}%), '
              f'mas cara {hi["provincia"]} {hi["canasta_total"]:,.0f} ({(hi["canasta_total"] / n - 1) * 100:+.2f}%), '
              f'dispersion {(hi["canasta_total"] / lo["canasta_total"] - 1) * 100:.1f}%')
