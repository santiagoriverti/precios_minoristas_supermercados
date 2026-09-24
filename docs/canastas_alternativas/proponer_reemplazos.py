#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Propone REEMPLAZOS para los items de canasta sin historia completa, con la logica del constructor.

Es el paso previo a `aplicar_reemplazos.py`: toma la salida de una corrida del nb07 y el cache de esa
corrida, marca los items con historia incompleta y, para cada uno, elige el reemplazo como lo haria
`construir_canastas_v5.py` (ventana de percentil del estrato, la mayor cobertura adentro, piso de
monotonicidad Popular <= Media <= Ejecutiva, EAN distinto por estrato si se puede; la Representativa y
la Femenina, el de mayor cobertura), pero SOLO entre productos que el nb07 ya lee (canastas +
`EANS_CANDIDATOS`) y con historia completa. Asi, aplicar la propuesta no relee el SEPA.

    python proponer_reemplazos.py --nb07 canastas_alternativas_2026-09-17.xlsx \
        --excel canasta_representativa_2026-09.xlsx --cache .../_cache_nb07 --salida propuesta.csv

"Historia completa" = dato en >= --traz-min % de los meses (hojas Presencia_items y
Candidatos_trazabilidad del nb07) Y a lo sumo --max-flacos meses con menos de --min-suc sucursales
(contadas en el cache `sem_<clave>_v5`, un parquet por mes cerrado). El segundo requisito existe porque
"meses con dato" cuenta un mes aunque el producto este en una sola sucursal (Raid 370: 97% de meses con
dato y 1 sucursal en ene-25; ver docs/AUDITORIA_2026-09-22_v59.md, seccion 11).

La salida es un CSV `canasta,necesidad,ean_nuevo,ean_actual` para `aplicar_reemplazos.py`. Es una
PROPUESTA: revisarla (producto razonable para la necesidad, estratos compartidos, costo) antes de aplicar.
Los desvios de la regla se hacen editando el CSV.
"""
import argparse, csv, io, os, pathlib, sys
import numpy as np, pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import aplicar_reemplazos as ar          # noqa: E402  (reusa la lectura del cargador y del nb07)
ORDEN = ['Popular', 'Media', 'Ejecutiva', 'Representativa']


def trazabilidad(nb07):
    pres = pd.read_excel(nb07, 'Presencia_items', dtype={'item': str})
    meses = [c for c in pres.columns if str(c)[:2] == '20']
    traz = {str(r['item']).lstrip('0'): 100.0 * (r[meses].astype(float) > 0).mean() for _, r in pres.iterrows()}
    try:
        cand = pd.read_excel(nb07, 'Candidatos_trazabilidad', dtype={'ean': str})
        traz.update(dict(zip(cand['ean'].str.lstrip('0'), cand['trazabilidad_%'].astype(float))))
    except ValueError:
        pass
    return traz


def meses_flacos(cache, min_suc):
    carpeta = next(iter(sorted(pathlib.Path(cache).glob('sem_*_v5'))), None)
    if carpeta is None:
        sys.exit(f'No encuentro sem_<clave>_v5 dentro de {cache}')
    filas = []
    for f in sorted(carpeta.glob('*.parquet')):
        d = pd.read_parquet(f, columns=['id_comercio', 'id_bandera', 'id_sucursal', 'item'])
        d = d[d['item'].str.isdigit()].drop_duplicates()
        n = d.groupby('item').size().rename('suc').reset_index(); n['mes'] = f.stem
        filas.append(n)
    cob = pd.concat(filas, ignore_index=True).pivot(index='item', columns='mes', values='suc').fillna(0)
    return (cob < min_suc).sum(axis=1), cob.shape[1]


def elegir(cc, c, canasta, usados, piso, techo, ok):
    """cc.elegir() restringido a los EANs de `ok`; `techo` = precio del estrato de arriba si no cambia."""
    reglas = cc.COBERTURA[canasta]
    for k, rg in enumerate([reglas, cc.PISO_ABSOLUTO]):
        pool = c[(c['n_cadenas'] >= rg['cadenas']) & (c['n_provincias'] >= rg['provincias']) & (c['n_sucursales'] >= rg['sucursales'])]
        if not len(pool):
            continue
        tope = False
        if piso is not None:
            alto = pool[pool['pu'] >= piso * 1.02]
            if len(alto[alto['ean'].isin(ok)]):
                pool = alto
            else:
                tope = True
        if tope:
            cand = pool[pool['pu'] >= piso].sort_values(['pu', 'n_sucursales'], ascending=[False, False])
            nota = 'tope: nada con historia mas caro que el estrato de abajo'
        elif canasta in ('Representativa', 'Femenina'):
            cand = pool.sort_values('n_sucursales', ascending=False)
            nota = 'el de mayor cobertura'
        else:
            p = cc.TIER_PCT[canasta]
            obj = pool['pu'].quantile(p)
            lo = pool['pu'].quantile(max(0.0, p - cc.TIER_VENTANA)); hi = pool['pu'].quantile(min(1.0, p + cc.TIER_VENTANA))
            ven = pool[(pool['pu'] >= lo) & (pool['pu'] <= hi)].sort_values(['n_sucursales', 'n_cadenas'], ascending=[False, False])
            ven_ok = ven[ven['ean'].isin(ok)]
            if techo is not None:
                ven_ok = ven_ok[ven_ok['pu'] <= techo]
            if len(ven_ok):
                cand, nota = ven, f'en la ventana del estrato (p{100 * p:.0f})'
            else:
                cand = pool.assign(_d=(pool['pu'] - obj).abs()).sort_values(['_d', 'n_sucursales'], ascending=[True, False])
                nota = f'fuera de la ventana: el mas cercano al p{100 * p:.0f}'
        cand = cand[cand['ean'].isin(ok)]
        if techo is not None:
            cand = cand[cand['pu'] <= techo]
        if not len(cand):
            continue
        libre = cand if tope else cand[~cand['ean'].isin(usados)]
        r = (libre if len(libre) else cand).iloc[0]
        if not len(libre) and not tope:
            nota += ' | COMPARTIDO con otro estrato'
        return r, nota
    return None, 'sin candidato con historia: se queda el actual'


def main():
    ap = argparse.ArgumentParser(description='Propone reemplazos para items sin historia completa.')
    ap.add_argument('--nb07', required=True, help='canastas_alternativas_YYYY-MM-DD.xlsx (salida del nb07)')
    ap.add_argument('--excel', required=True, help='canasta_representativa_YYYY-MM.xlsx (la cargada en el Drive)')
    ap.add_argument('--cache', required=True, help='carpeta con sem_<clave>_v5 (cache del nb07 de esa corrida)')
    ap.add_argument('--salida', default='reemplazos_propuestos.csv')
    ap.add_argument('--traz-min', type=float, default=85.0)
    ap.add_argument('--min-suc', type=int, default=300)
    ap.add_argument('--max-flacos', type=int, default=4)
    a = ap.parse_args()

    cc = ar._modulo(ar.CONSTRUCTOR, 'construir_canastas_v5')
    pu = cc.cargar_universo(a.excel)
    CANT, _, _ = ar._dict_literal(io.open(ar.LOADER, encoding='utf-8').read(), 'CANTIDADES')
    traz = trazabilidad(a.nb07)
    flacos, n_meses = meses_flacos(a.cache, a.min_suc)
    ok = {e for e, t in traz.items() if t >= a.traz_min and flacos.get(e, n_meses) <= a.max_flacos}
    usa = lambda e, can: CANT.get(e, {}).get(ar.COL[can], 0) > 0
    malo = lambda e: traz.get(e, 0) < a.traz_min or flacos.get(e, n_meses) > a.max_flacos
    print(f'{n_meses} meses en el cache | {len(ok)} EANs leidos con historia completa '
          f'(>= {a.traz_min:g}% de meses con dato y <= {a.max_flacos} meses con menos de {a.min_suc} sucursales)\n')

    filas = []
    def registrar(can, need, cfg, q, x, r, nota):
        if r is None:
            filas.append(dict(canasta=can, necesidad=need, ean_actual=x['ean'], actual=x['desc'][:45], ean_nuevo='',
                              nuevo='(se queda el actual)', nota=nota))
            return
        tam = (r['grams'] / 1000.0) if cfg['u'] == 'kg' else r['tam']
        n = ar._redondeo(q / tam if tam and tam > 0 else 0.0)
        q_act = CANT[x['ean']][ar.COL[can]]
        otros = [t for t in ORDEN + ['Femenina'] if t != can and usa(r['ean'], t)]
        filas.append(dict(canasta=can, necesidad=need, ean_actual=x['ean'], actual=x['desc'][:45], ean_nuevo=r['ean'],
                          nuevo=r['desc'][:45], cant=f'{q_act:g}->{n:g}',
                          delta_costo=round(n * r['precio_mediano'] - q_act * x['precio_mediano']),
                          ya_lo_usa=','.join(otros), nota=nota))

    for need, cfg in cc.NEEDS.items():
        c = cc.candidatos(pu, cfg)
        if len(c) < 2:
            continue
        act = {}
        for can in ORDEN:
            a_ = c[c['ean'].map(lambda e: usa(e, can))]
            act[can] = a_.iloc[0] if len(a_) else None
        cambia = {can: act[can] is not None and malo(act[can]['ean']) for can in ORDEN}
        if not any(cambia.values()):
            continue
        usados, piso = set(), None
        for i, can in enumerate(ORDEN):
            q = cfg['qty'][i]
            if not q or q <= 0 or act[can] is None:
                continue
            r = act[can]
            if cambia[can]:
                techo = None
                if can in ('Popular', 'Media') and act[ORDEN[i + 1]] is not None and not cambia[ORDEN[i + 1]]:
                    techo = float(act[ORDEN[i + 1]]['pu'])
                nuevo, nota = elegir(cc, c, can, usados, None if can == 'Representativa' else piso, techo, ok)
                registrar(can, need, cfg, q, act[can], nuevo, nota)
                r = nuevo if nuevo is not None else act[can]
            usados.add(r['ean'])
            if can != 'Representativa':
                piso = float(r['pu'])
    for need, cfg in cc.NEEDS_FEMENINA.items():
        c = cc.candidatos(pu, dict(sub=cfg['sub'], inc=cfg.get('inc'), exc=cfg.get('exc'), u=cfg['u']))
        x = c[c['ean'].map(lambda e: usa(e, 'Femenina'))]
        if not len(x) or not malo(x.iloc[0]['ean']):
            continue
        nuevo, nota = elegir(cc, c, 'Femenina', set(), None, None, ok)
        registrar('Femenina', need, cfg, cfg['qty'], x.iloc[0], nuevo, nota)

    if not filas:
        print('Ningun item de canasta sin historia completa: nada que proponer.')
        return
    df = pd.DataFrame(filas)
    pd.set_option('display.width', 250); pd.set_option('display.max_colwidth', 60)
    print(df.to_string(index=False))
    prop = df[df['ean_nuevo'] != '']
    with open(a.salida, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['canasta', 'necesidad', 'ean_nuevo', 'ean_actual'])
        for _, r in prop.iterrows():
            w.writerow([r['canasta'], r['necesidad'], r['ean_nuevo'], r['ean_actual']])
    print(f'\n{len(prop)} reemplazos propuestos -> {a.salida} | {len(df) - len(prop)} items sin candidato con historia')
    print('Revisar la propuesta y aplicarla con: python aplicar_reemplazos.py --excel ... --reemplazos', a.salida)


if __name__ == '__main__':
    main()
