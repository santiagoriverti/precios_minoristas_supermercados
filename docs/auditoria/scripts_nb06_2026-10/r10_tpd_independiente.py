# Verificación independiente de la serie TPD del nb06 (CELDA 8b) con datos reales: otro algoritmo (LSQR de scipy sobre
# el diseño completo de cada subtipo: una indicadora por celda sucursal-mes, por producto y por sin TACC × mes, sin
# normalizar ni absorber efectos) en vez de las ecuaciones normales con los efectos de celda descontados. Compara el
# nivel de cada subtipo y mes (hoja TPD_subtipos, meses con dato propio), que no depende de la normalización, en los dos
# universos (celdas del panel balanceado y todas las sucursales).
# Uso: python -I -X utf8 r10_tpd_independiente.py <carpeta de la simulación (s11)> <brecha_celiaca_AAAA-MM.xlsx de esa simulación>
import sys, time
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import sparse
from scipy.sparse.linalg import lsqr

SIM, XLS = Path(sys.argv[1]), Path(sys.argv[2])
sk = ['id_comercio', 'id_bandera', 'id_sucursal']
dd = pd.read_parquet(SIM / 'sim_datos_dia.parquet', columns=sk + ['mes', 'tipo', 'subtipo', 'rol', 'producto', 'precio_100'])
sg = pd.read_parquet(SIM / 'sim_suc_geo.parquet', columns=sk + ['suc_key'])
pt = (dd.merge(sg, on=sk, how='inner')
      .groupby(['suc_key', 'mes', 'tipo', 'subtipo', 'rol', 'producto'], as_index=False)['precio_100'].median())
pt = pt[pt['precio_100'] > 0]
# celdas del panel balanceado, como la CELDA 8 (sucursal × subtipo con los dos lados en >= 70% de los meses)
bs = pd.read_parquet(SIM / 'sim_bt_sub.parquet', columns=['suc_key', 'tipo', 'subtipo', 'mes'])
pres = bs.groupby(['suc_key', 'tipo', 'subtipo'])['mes'].nunique()
cel = pres[pres >= max(1, int(round(0.7 * bs['mes'].nunique())))].reset_index()[['suc_key', 'tipo', 'subtipo']]
nb = pd.read_excel(XLS, sheet_name='TPD_subtipos')
nb = nb[~nb['movido_con_los_demas'].astype(bool)].set_index(['universo', 'tipo', 'subtipo', 'mes'])['brecha_tpd']
filas = []
for uni, datos in (('panel balanceado', pt.merge(cel, on=['suc_key', 'tipo', 'subtipo'])), ('todas las sucursales', pt)):
    datos = datos.copy()
    datos['w'] = 1.0 / datos.groupby(['suc_key', 'mes', 'tipo', 'subtipo', 'rol'])['producto'].transform('size')
    for (tipo, sub), d in datos.groupby(['tipo', 'subtipo']):
        d = d.reset_index(drop=True)
        t0 = time.time()
        gi = d.groupby(['suc_key', 'mes']).ngroup().to_numpy()
        prods = sorted(d['producto'].unique())
        pj = d['producto'].map({p: i for i, p in enumerate(prods)}).to_numpy()
        meses = sorted(d['mes'].unique())
        tm = d['mes'].map({m: i for i, m in enumerate(meses)}).to_numpy()
        sin = (d['rol'] == 'sin').to_numpy()
        G, P, T, N = gi.max() + 1, len(prods), len(meses), len(d)
        fx = np.concatenate([np.arange(N), np.arange(N), np.arange(N)[sin]])
        cx = np.concatenate([gi, G + pj, G + P + tm[sin]])
        X = sparse.csr_matrix((np.ones(len(fx)), (fx, cx)), shape=(N, G + P + T))
        sw = np.sqrt(d['w'].to_numpy())
        res = lsqr(sparse.diags(sw) @ X, sw * np.log(d['precio_100'].to_numpy()), atol=1e-14, btol=1e-14,
                   conlim=1e12, iter_lim=400000)
        gam, beta = res[0][G:G + P], res[0][G + P:]
        obs = d.groupby('producto').size()
        info = d.drop_duplicates('producto').set_index('producto')['rol']
        nivel = 0.0
        for lado, sg_ in (('sin', 1.0), ('tacc', -1.0)):
            ps = list(info.index[info == lado])
            nivel += sg_ * float(sum(gam[prods.index(p)] * obs[p] for p in ps) / obs[ps].sum())
        for i, m in enumerate(meses):
            if (uni, tipo, sub, m) in nb.index:
                filas.append({'universo': uni, 'tipo': tipo, 'subtipo': sub, 'mes': m,
                              'independiente': 100 * np.expm1(nivel + beta[i]), 'nb06': nb[(uni, tipo, sub, m)]})
        print(f'[{uni}] {sub}: {N:,} obs, {G:,} celdas, {P} productos; LSQR {res[2]} iteraciones (motivo {res[1]}), '
              f'{time.time() - t0:.0f} s', flush=True)
c = pd.DataFrame(filas)
c['dif'] = (c['independiente'] - c['nb06']).abs()
print(c.groupby(['universo', 'subtipo'])['dif'].agg(['size', 'max']).to_string())
print(f'Brecha TPD por subtipo y mes (meses con dato propio): {len(c)} celdas, máx. |dif| = {c["dif"].max():.2e} pp')
