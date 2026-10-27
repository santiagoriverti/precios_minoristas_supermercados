# Tablas en markdown de la canasta fija (para docs/BRECHA_CELIACA.md §14.5) desde el CSV de s10.
# Uso: python -I -X utf8 s13_tablas_doc.py <canasta.csv>
import sys
import pandas as pd

C = pd.read_csv(sys.argv[1], dtype={'ean': str, 'desde': str, 'hasta': str})
if 'linea' not in C.columns:   # canastas anteriores al 2026-10-26, noche: cada producto es su línea
    C['linea'] = C['producto']
ORDEN = ['Fideos secos', 'Galletitas dulces', 'Galletitas saladas y crackers', 'Pan rallado y rebozador',
         'Cereales rellenos (almohaditas)']
fmt = lambda x, d=0: f'{x:,.{d}f}'.replace(',', 'X').replace('.', ',').replace('X', '.')

# resumen por tipo (entre paréntesis, las líneas: los sabores de una misma marca y presentación cuentan una vez)
r = C.drop_duplicates(['tipo', 'lado', 'producto']).groupby(['tipo', 'lado']).size().unstack('lado').reindex(ORDEN)
l = C.drop_duplicates(['tipo', 'lado', 'linea']).groupby(['tipo', 'lado']).size().unstack('lado').reindex(ORDEN)
e = C.groupby(['tipo', 'lado']).size().unstack('lado').reindex(ORDEN)
print('| Tipo | Productos con TACC (líneas) | Productos sin TACC (líneas) | Códigos (EAN) | Subtipos |')
print('|---|---|---|---|---|')
for t in ORDEN:
    if t not in r.index or r.loc[t].isna().all():
        continue
    subs = ', '.join(dict.fromkeys(C.loc[C['tipo'] == t, 'subtipo']))
    print(f"| {t} | {int(r.loc[t, 'tacc'])} ({int(l.loc[t, 'tacc'])}) | {int(r.loc[t, 'sin_tacc'])} "
          f"({int(l.loc[t, 'sin_tacc'])}) | {int(e.loc[t].sum())} | {subs} |")
print(f'| **Total** | {int(r["tacc"].sum())} ({int(l["tacc"].sum())}) | {int(r["sin_tacc"].sum())} '
      f'({int(l["sin_tacc"].sum())}) | {len(C)} | |')
print()

MES_P = C['ultimo_mes_con_precio'].mode().iloc[0]
NOM = dict(zip(['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12'],
               ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']))
ETQ = f'{NOM[MES_P[5:7]]}-{MES_P[2:4]}'
for t in ORDEN:
    x = C[C['tipo'] == t]
    if x.empty:
        continue
    print(f'**{t}**\n')
    print(f'| Subtipo | Lado | Producto | Línea | EAN (vigencia) | g | Suc./día 2022-26 | Prov. | Com. | Cad. grandes | '
          f'$/100 g {ETQ} | Relativo |')
    print('|---|---|---|---|---|---|---|---|---|---|---|---|')
    for (st, lado, prod), g in x.groupby(['subtipo', 'lado', 'producto'], sort=False):
        eans = []
        for rr in g.itertuples(index=False):
            v = ''
            d = rr.desde if isinstance(rr.desde, str) and rr.desde else None
            h = rr.hasta if isinstance(rr.hasta, str) and rr.hasta else None
            if d or h:
                v = f" ({'≤' + h if h and not d else ('≥' + d if d and not h else d + '→' + h)})"
            eans.append(f'`{rr.ean}`{v}')
        r0 = g.iloc[0]
        gr = '/'.join(dict.fromkeys(fmt(v) for v in g['gramos']))
        lin = r0['linea'] if r0['linea'] != prod else ''
        print(f"| {st} | {'sin TACC' if lado == 'sin_tacc' else 'con TACC'} | {prod} | {lin} | {'<br>'.join(eans)} | "
              f"{gr} | {fmt(r0['sucursales_dia_mediana_2022_2026'])} | {int(r0['provincias'])} | "
              f"{int(r0['comercios'])} | {int(r0['cadenas_grandes'])} | {fmt(r0['precio_100g_ultimo_mes'])} | "
              f"{fmt(r0['precio_sobre_mediana_con_tacc_subtipo'], 2)} |")
    print()
