# Recalculo independiente, desde los archivos crudos del SEPA, de meses completos del panel del nb09 v2
# (dias con precio y sucursales por dia de CADA producto), de lo que imprime la CELDA 4 por archivo y de las
# provincias/cadenas de cada producto (que esten en las del ranking). Tambien describe las filas repetidas.
# Uso: python -I -X utf8 r4_crudo.py <carpeta datos nb09> <carpeta zips> <salida.json>
import sys, re, gzip, json, time, zipfile, unicodedata
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.compute as pc

D, Z, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])

MESES = {  # mes -> [(zip, archivo, lo que imprimio la CELDA 4 en Colab: dias, productos/dia, sucursales, pares, repetidas)]
    '2024-01': [('2024A.zip', '012024_pais_parte1COMPLETO.csv.gz', (15, 58351, 3127, 10469282, 1)),
                ('2024A.zip', '012024_pais_parte2COMPLETO.csv.gz', (16, 60323, 3133, 11056832, 892))],
    '2024-08': [('2024B.zip', '082024_pais_parte1COMPLETOb.csv.gz', (15, 60156, 3370, 10606772, 1)),
                ('2024B.zip', '082024_pais_parte2COMPLETO.csv.gz', (16, 62027, 3330, 11847910, 1))],
    '2025-08': [('2025B.zip', '082025_pais_parte1COMPLETO.csv.gz', (15, 81779, 2645, 14658072, 24890)),
                ('2025B.zip', '082025_pais_parte2COMPLETO.csv.gz', (16, 84239, 2736, 15118899, 0))],
    '2026-07': [('2026B.zip', '072026_pais_parte1COMPLETO.csv.gz', (15, 73683, 3259, 13111005, 0)),
                ('2026B.zip', '072026_pais_parte2COMPLETO.csv.gz', (16, 89868, 3414, 15735393, 0))],
}
if len(sys.argv) > 4:
    MESES = {k: v for k, v in MESES.items() if k in sys.argv[4].split(',')}

ISO = {'AR-C': 'CABA', 'AR-B': 'Buenos Aires', 'AR-K': 'Catamarca', 'AR-H': 'Chaco', 'AR-U': 'Chubut',
       'AR-X': 'Córdoba', 'AR-W': 'Corrientes', 'AR-E': 'Entre Ríos', 'AR-P': 'Formosa', 'AR-Y': 'Jujuy',
       'AR-L': 'La Pampa', 'AR-F': 'La Rioja', 'AR-M': 'Mendoza', 'AR-N': 'Misiones', 'AR-Q': 'Neuquén',
       'AR-R': 'Río Negro', 'AR-A': 'Salta', 'AR-J': 'San Juan', 'AR-D': 'San Luis', 'AR-Z': 'Santa Cruz',
       'AR-S': 'Santa Fe', 'AR-G': 'Santiago del Estero', 'AR-V': 'Tierra del Fuego', 'AR-T': 'Tucumán'}
def _sin_tilde(x):
    return unicodedata.normalize('NFKD', x).encode('ascii', 'ignore').decode().lower().strip()
POR_NOMBRE = {_sin_tilde(v): v for v in ISO.values()}
POR_NOMBRE.update({'capital federal': 'CABA', 'ciudad autonoma de buenos aires': 'CABA'})
def provincia(v):
    # nombre de provincia (como el ranking) o '' si no se reconoce
    v = (v or '').strip()
    if v.upper() in ISO:
        return ISO[v.upper()]
    return POR_NOMBRE.get(_sin_tilde(v), '')
NOM_COM = {'2': 'La Anónima', '3': 'Deheza', '4': 'Estación Lima', '5': 'California Supermercados', '6': 'Comodín',
           '8': 'Mariano Max', '9': 'Cencosud (Vea/Disco/Jumbo)', '10': 'Carrefour', '11': 'ChangoMas', '12': 'Coto',
           '13': 'Cooperativa Obrera', '15': 'DIA', '16': 'Libertad', '20': 'La Agrícola Regional', '21': 'Toledo',
           '23': 'Axion Energy', '47': 'Unicoop (Patagones y Viedma)'}

prod_map, suc_map = {}, {}
suc_txt, suc_prov = [], []

def a_codigos(arr, mapa, lista=None):
    arr = arr.dictionary_encode() if not pa.types.is_dictionary(arr.type) else arr
    vals = arr.dictionary.to_pylist()
    m = np.empty(len(vals) + 1, np.int64)
    for i, v in enumerate(vals):
        c = mapa.get(v)
        if c is None:
            c = mapa[v] = len(mapa)
            if lista is not None:
                lista.append(v)
        m[i] = c
    m[-1] = -1
    return m[pc.fill_null(arr.indices, len(vals)).to_numpy(zero_copy_only=False)]

def leer(zpath, nombre):
    with zipfile.ZipFile(zpath) as zf:
        with zf.open(nombre) as s0, gzip.open(s0, 'rt', encoding='utf-8', errors='replace') as g:
            hdr = [c.strip() for c in g.readline().split(',')]
        cols_p = [c for c in hdr if re.match(r'^precio_\d{8}$', c)]
        idc = ['id_comercio', 'id_bandera', 'id_sucursal', 'sucursales_provincia', 'id_producto']
        for texto in (False, True):
            try:
                tipos = {c: pa.string() for c in idc}
                tipos.update({c: (pa.string() if texto else pa.float64()) for c in cols_p})
                E, S, M, PS = [], [], [], []
                with zf.open(nombre) as s0, pa.CompressedInputStream(pa.PythonFile(s0, mode='r'), 'gzip') as s:
                    rd = pacsv.open_csv(s, read_options=pacsv.ReadOptions(block_size=32 << 20),
                                        convert_options=pacsv.ConvertOptions(column_types=tipos, include_columns=idc + cols_p,
                                                                             null_values=['NA', ''], strings_can_be_null=True))
                    for bl in rd:
                        if bl.num_rows == 0:
                            continue
                        tr = lambda c: pc.fill_null(pc.utf8_trim_whitespace(bl.column(c)), '')
                        p = pc.utf8_ltrim(tr('id_producto'), characters='0')
                        p = pc.if_else(pc.equal(p, ''), '0', p)
                        e = a_codigos(p, prod_map)
                        sk = pc.binary_join_element_wise(tr('id_comercio'), tr('id_bandera'), tr('id_sucursal'), '|')
                        n0 = len(suc_txt)
                        st = a_codigos(sk, suc_map, suc_txt)
                        if len(suc_txt) > n0:                       # provincia de la primera fila de cada sucursal nueva
                            pr = tr('sucursales_provincia').to_numpy(zero_copy_only=False)
                            u, i0 = np.unique(st, return_index=True)
                            suc_prov.extend([''] * (len(suc_txt) - n0))
                            for a, b in zip(u, i0):
                                if a >= n0:
                                    suc_prov[a] = pr[b]
                        P = np.empty((bl.num_rows, len(cols_p)))
                        for j, c in enumerate(cols_p):
                            col = bl.column(c)
                            P[:, j] = (pd.to_numeric(col.to_pandas(), errors='coerce').to_numpy(float) if texto
                                       else pc.fill_null(col, np.nan).to_numpy(zero_copy_only=False))
                        V = np.isfinite(P) & (P > 0)
                        msk = (V.astype(np.uint64) << np.arange(len(cols_p), dtype=np.uint64)).sum(axis=1, dtype=np.uint64)
                        ok = msk > 0
                        E.append(e[ok].astype(np.int32)); S.append(st[ok].astype(np.int32)); M.append(msk[ok])
                        PS.append(np.where(V, P, 0).sum(axis=1)[ok])
                break
            except pa.ArrowInvalid:
                if texto:
                    raise
                print('   precios no numericos: se relee como texto', flush=True)
    return cols_p, np.concatenate(E), np.concatenate(S), np.concatenate(M), np.concatenate(PS)

R = pd.read_parquet(D / 'trazabilidad_productos_20220101_20261015.parquet',
                    columns=['id_producto', 'provincias', 'provincias_presentes', 'provincias_faltantes', 'cadenas'])
PAN = pd.read_parquet(D / 'panel_mensual_productos_20220101_20261015.parquet')
TODAS = set(ISO.values())
prov_rank = {}
for i, pp, pf in zip(R['id_producto'], R['provincias_presentes'], R['provincias_faltantes']):
    prov_rank[i] = set(x for x in pp.split('; ') if x) if pp else TODAS - set(x for x in pf.split('; ') if x)
cad_rank = dict(zip(R['id_producto'], R['cadenas'].map(lambda x: set(x.split('; ')))))

res = {}
for mes, archivos in MESES.items():
    dias = {}; suma = {}
    falt_prov = falt_cad = 0; ej_prov = []; ej_cad = []
    for zname, nombre, esperado in archivos:
        t = time.time()
        cols_p, e, s, m, ps = leer(Z / zname, nombre)
        nd = len(cols_p)
        k = s.astype(np.int64) * (1 << 32) + e
        o = np.argsort(k, kind='stable'); ks = k[o]
        ini = np.flatnonzero(np.r_[True, ks[1:] != ks[:-1]])
        tam = np.diff(np.r_[ini, len(ks)])
        rep = int(len(ks) - len(ini))
        mu = np.bitwise_or.reduceat(m[o], ini)
        eu, su = e[o][ini], s[o][ini]
        # filas repetidas: que comercio, mismos dias y mismo precio?
        info_rep = {}
        if rep:
            g = np.repeat(np.arange(len(ini)), tam)
            igual_m = np.ones(len(ini), bool); igual_p = np.ones(len(ini), bool)
            ms, pss = m[o], ps[o]
            igual_m &= np.maximum.reduceat(ms, ini) == np.minimum.reduceat(ms, ini)
            igual_p &= np.isclose(np.maximum.reduceat(pss, ini), np.minimum.reduceat(pss, ini))
            d = tam > 1
            com = pd.Series([suc_txt[x].split('|')[0] for x in su[d]])
            info_rep = {'grupos': int(d.sum()), 'filas_extra': rep, 'por_comercio': com.value_counts().head(5).to_dict(),
                        'mismos_dias': int((igual_m & d).sum()), 'mismo_precio_total': int((igual_p & d).sum()),
                        'sucursales': int(len(np.unique(su[d]))), 'productos': int(len(np.unique(eu[d]))),
                        'max_repeticiones': int(tam.max())}
        # por dia
        n_suc_dia, n_prod_dia = [], []
        for j in range(nd):
            sel = ((mu >> np.uint64(j)) & np.uint64(1)).astype(bool)
            if not sel.any():
                continue
            cnt = np.bincount(eu[sel], minlength=len(prod_map))
            n_suc_dia.append(int(len(np.unique(su[sel])))); n_prod_dia.append(int((cnt > 0).sum()))
            for x in np.nonzero(cnt)[0]:
                dias[x] = dias.get(x, 0) + 1
                suma[x] = suma.get(x, 0) + int(cnt[x])
        calc = (len(n_suc_dia), max(n_prod_dia), max(n_suc_dia), int(len(ini)), rep)
        print(f'{mes} {nombre}: {time.time() - t:.0f} s | calculado {calc} | Colab {esperado} | '
              f'{"IGUAL" if calc == tuple(esperado) else "DISTINTO"}', flush=True)
        if info_rep:
            print('   repetidas:', info_rep, flush=True)
        res[f'{mes} {nombre}'] = {'calculado': calc, 'colab': esperado, 'repetidas': info_rep,
                                  'suc_por_dia': n_suc_dia, 'prod_por_dia': n_prod_dia}
        # provincias y cadenas de cada producto en este archivo, dentro de las del ranking
        prov_s = np.array([provincia(x) for x in suc_prov], dtype=object)
        com_s = np.array([NOM_COM.get(x.split('|')[0], 'Cadena ' + x.split('|')[0]) for x in suc_txt], dtype=object)
        pares = pd.DataFrame({'e': eu, 'p': prov_s[su], 'c': com_s[su]})
        ids = np.array(list(prod_map.keys()), dtype=object)
        for (x, gp) in pares[pares['p'] != ''].drop_duplicates(['e', 'p']).groupby('e')['p']:
            i = ids[x]
            fuera = set(gp) - prov_rank.get(i, set())
            if fuera:
                falt_prov += 1
                if len(ej_prov) < 5:
                    ej_prov.append((i, sorted(fuera)))
        for (x, gc_) in pares.drop_duplicates(['e', 'c']).groupby('e')['c']:
            i = ids[x]
            fuera = set(gc_) - cad_rank.get(i, set())
            if fuera:
                falt_cad += 1
                if len(ej_cad) < 5:
                    ej_cad.append((i, sorted(fuera)))
        del e, s, m, ps, k, o, ks, mu, eu, su, pares
    ids = np.array(list(prod_map.keys()), dtype=object)
    X = pd.DataFrame({'id_producto': ids[list(dias.keys())], 'd': list(dias.values()),
                      'sp': np.array(list(suma.values())) / np.array(list(dias.values()))})
    Pm = PAN[PAN['mes'] == mes][['id_producto', 'dias_con_precio', 'suc_diarias_prom']]
    J = X.merge(Pm, on='id_producto', how='outer', indicator=True)
    solo_crudo = int((J['_merge'] == 'left_only').sum()); solo_panel = int((J['_merge'] == 'right_only').sum())
    B = J[J['_merge'] == 'both']
    mal_d = int((B['d'] != B['dias_con_precio']).sum())
    mal_s = int((np.abs(B['sp'] - B['suc_diarias_prom'].astype(float)) > 0.05 + 1e-3).sum())
    print(f'== {mes}: productos crudo {len(X):,} | panel {len(Pm):,} | solo crudo {solo_crudo} | solo panel {solo_panel} | '
          f'dias distintos {mal_d} | suc/dia distintos {mal_s} | provincias fuera del ranking {falt_prov} {ej_prov} | '
          f'cadenas fuera del ranking {falt_cad} {ej_cad}', flush=True)
    res[mes] = {'productos_crudo': len(X), 'productos_panel': len(Pm), 'solo_crudo': solo_crudo, 'solo_panel': solo_panel,
                'dias_distintos': mal_d, 'suc_distintos': mal_s, 'prov_fuera': falt_prov, 'cad_fuera': falt_cad,
                'ej_prov': ej_prov, 'ej_cad': ej_cad,
                'ej_solo': J[J['_merge'] != 'both'].head(5)[['id_producto', '_merge']].astype(str).values.tolist()}
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding='utf-8')
print('listo')
