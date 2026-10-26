# Números clave de una o varias carpetas de resultados esperados (s17), lado a lado: brecha por tipo y por subtipo de
# todo el período, canasta por año (todas las sucursales y panel), últimos 12 meses (promedio de la serie mensual),
# grupos confiables, concentración, sucursales, imputaciones y serie TPD.
# Uso: python -I -X utf8 r28_numeros_clave.py <carpeta de esperados> [otras carpetas ...]
import sys
from pathlib import Path

import pandas as pd

pd.set_option('display.width', 250); pd.set_option('display.max_columns', 20); pd.set_option('display.max_rows', 200)
DIRS = [Path(a) for a in sys.argv[1:]]
ULT = ['2025-11', '2025-12'] + [f'2026-{i:02d}' for i in range(1, 11)]


def numeros(d):
    r = {}
    for x in pd.read_csv(d / 'Brecha_tipo.csv').itertuples():
        r[f'tipo 2022-26: {x.tipo}'] = x.brecha_mediana
    for x in pd.read_csv(d / 'Brecha_subtipo.csv').itertuples():
        r[f'subtipo 2022-26: {x.subtipo}'] = x.brecha_mediana
    for f, k in (('Canasta_anual.csv', 'todas'), ('Canasta_anual_balanceada.csv', 'panel')):
        for x in pd.read_csv(d / f).itertuples():
            r[f'canasta {x.anio} ({k})'] = x.brecha_canasta
    s = pd.read_csv(d / 'Serie_canasta.csv')
    r['canasta últimos 12 meses (todas)'] = s[s['mes'].isin(ULT)]['brecha_canasta'].mean()
    sb = pd.read_csv(d / 'Serie_canasta_balanceada.csv')
    r['canasta últimos 12 meses (panel)'] = sb[sb['mes'].isin(ULT)]['brecha_canasta'].mean()
    r['canasta oct-2026 (todas)'] = s.loc[s['mes'] == '2026-10', 'brecha_canasta'].iloc[0]
    r['canasta oct-2026 (panel)'] = sb.loc[sb['mes'] == '2026-10', 'brecha_canasta'].iloc[0]
    for f, col in (('Brecha_region.csv', 'region'), ('Brecha_provincia.csv', 'provincia'),
                   ('Brecha_empresa.csv', 'empresa'), ('Brecha_cadena.csv', 'cadena')):
        g = pd.read_csv(d / f)
        g = g[g['confiable'].astype(str).eq('True')].sort_values('brecha_canasta')
        r[f'{col}: confiables'] = ', '.join(f'{n} {v:+.1f}' for n, v in zip(g[col], g['brecha_canasta']))
    c = pd.read_csv(d / 'Concentracion.csv')
    r['concentración: departamentos'] = len(c)
    r['concentración: con >= 5 sucursales con brecha'] = int((c['sucursales_con_brecha'] >= 5).sum())
    b = pd.read_csv(d / 'Brecha_sucursal.csv')
    r['sucursales (filas Brecha_sucursal)'] = len(b)
    r['sucursales: canasta comparable mediana'] = b['brecha_canasta'].median()
    i = pd.read_csv(d / 'Imputaciones.csv')
    r['imputaciones: rachas (todas / panel)'] = f"{len(i)} ({int(i['serie'].str.contains('todas').sum())} / {int((~i['serie'].str.contains('todas')).sum())})"
    r['imputaciones: de más de 3 meses'] = int((i['meses'] > 3).sum())
    r['imputaciones: la más larga'] = f"{i.loc[i['meses'].idxmax(), 'subtipo']} ({i.loc[i['meses'].idxmax(), 'serie']}) {i['meses'].max()} meses"
    for x in pd.read_csv(d / 'TPD_anual.csv').itertuples():
        r[f'TPD {x.anio} panel / todas'] = f'{x.brecha_canasta_tpd_panel:+.1f} / {x.brecha_canasta_tpd_todas:+.1f}'
    t = pd.read_csv(d / 'Serie_TPD.csv')
    u = t[t['mes'] == '2026-10'].iloc[0]
    r['TPD oct-2026 panel (IC; descriptiva)'] = (f"{u['brecha_canasta_tpd_panel']:+.1f} ({u['brecha_canasta_tpd_ic95_inf_panel']:+.1f} a "
                                                f"{u['brecha_canasta_tpd_ic95_sup_panel']:+.1f}; {u['brecha_canasta_descriptiva_panel']:+.1f})")
    r['TPD oct-2026 todas (IC; descriptiva)'] = (f"{u['brecha_canasta_tpd_todas']:+.1f} ({u['brecha_canasta_tpd_ic95_inf_todas']:+.1f} a "
                                                f"{u['brecha_canasta_tpd_ic95_sup_todas']:+.1f}; {u['brecha_canasta_descriptiva_todas']:+.1f})")
    ts = pd.read_csv(d / 'TPD_subtipos.csv')
    mv = ts[ts['movido_con_los_demas'].astype(str).eq('True')].groupby(['universo', 'subtipo']).size()
    r['TPD subtipo-mes movidos'] = ', '.join(f'{u} {s} {n}' for (u, s), n in mv.items())
    return r


R = pd.DataFrame({d.name: numeros(d) for d in DIRS})
for k, v in R.iterrows():
    print(f'{k}: ' + ' | '.join(f'{x:.1f}' if isinstance(x, float) else str(x) for x in v.tolist()))
