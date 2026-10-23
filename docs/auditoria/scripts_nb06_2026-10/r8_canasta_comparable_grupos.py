# Canasta comparable con 12 subtipos fijos: en cada grupo, subtipo propio si tiene >= MIN sucursales; si no, el valor
# nacional del subtipo en la misma ventana. Peso de cada subtipo = peso ENGHo del tipo / n subtipos del tipo.
# (Cálculo independiente de lo que hace la CELDA 8 desde el 2026-10-23 con provincias, regiones, empresas y cadenas.)
# Uso: python -I -X utf8 r8_canasta_comparable_grupos.py <carpeta sim_final> <brecha_celiaca_AAAA-MM.xlsx> [MIN]
import sys
from pathlib import Path
import numpy as np
import pandas as pd
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 300); pd.set_option('display.max_columns', 40)
SIM, XLS = Path(sys.argv[1]), Path(sys.argv[2]); MIN = int(sys.argv[3]) if len(sys.argv) > 3 else 10
bt = pd.read_parquet(SIM / 'sim_bt_sub.parquet')
pond = pd.read_excel(XLS, sheet_name='Ponderaciones')
W = dict(zip(pond['tipo'], pond['peso_en_la_canasta_pct'] / 100))
subs = bt[['tipo', 'subtipo']].drop_duplicates().sort_values(['tipo', 'subtipo'])
subs['w'] = subs['tipo'].map(W) / subs.groupby('tipo')['subtipo'].transform('size')
print(subs.assign(w=lambda d: (100 * d['w']).round(2)).to_string(index=False))
meses = sorted(bt['mes'].unique())[-12:]
v = bt[bt['mes'].isin(meses)]
nac = v.groupby(['tipo', 'subtipo'])['brecha_pct'].median().rename('nac')
def tabla(key):
    g = v.groupby([key, 'tipo', 'subtipo']).agg(b=('brecha_pct', 'median'), n=('suc_key', 'nunique')).reset_index()
    full = g[[key]].drop_duplicates().merge(subs, how='cross').merge(g, on=[key, 'tipo', 'subtipo'], how='left')
    full = full.merge(nac.reset_index(), on=['tipo', 'subtipo'])
    full['propio'] = full['n'] >= MIN
    full['bb'] = np.where(full['propio'], full['b'], full['nac'])
    full['lg'] = np.log1p(full['bb'] / 100)
    t = full.groupby([key, 'tipo']).agg(lg=('lg', 'mean'), w=('w', 'sum')).reset_index()
    t['rel'] = np.exp(t['lg'])
    can = t.groupby(key).apply(lambda d: (d['rel'] * d['w']).sum() - 1, include_groups=False) * 100
    imp = full.groupby(key).apply(lambda d: (d['w'] * ~d['propio']).sum(), include_groups=False) * 100
    nsuc = v.groupby(key)['suc_key'].nunique()
    out = pd.DataFrame({'canasta_12_subtipos': can, 'peso_imputado_pct': imp, 'sucursales': nsuc})
    falt = full[~full['propio']].groupby(key)['subtipo'].apply(lambda s: ', '.join(x[:12] for x in s))
    out['subtipos_imputados'] = falt
    return out.sort_values('canasta_12_subtipos')
lg_n = np.log1p(nac / 100).groupby(level='tipo').mean()
print('\ncanasta nacional 12 subtipos (últimos 12 meses):',
      round((sum(np.exp(lg_n[t]) * W[t] for t in W) - 1) * 100, 1))
xls = pd.ExcelFile(XLS)
for key, hoja, col in (('PROVINCIA_NORM', 'Brecha_provincia', 'provincia'), ('region', 'Brecha_region', 'region'),
                       ('empresa', 'Brecha_empresa', 'empresa'), ('cadena', 'Brecha_cadena', 'cadena')):
    t = tabla(key)
    print(f'\n=== {key} (MIN={MIN} sucursales por subtipo)')
    print(t.round(1).to_string())
    # si el Excel es del nb06 vigente (BUG-47), sus grupos tienen que dar igual a este cálculo
    e = xls.parse(hoja)
    if 'peso_imputado_pct' in e.columns:
        e = e.set_index(col)
        t = t[t['peso_imputado_pct'] < 100 - 1e-9]          # el nb06 saca los grupos sin ningún subtipo propio
        comun = t.index.intersection(e.index)
        d1 = (t.loc[comun, 'canasta_12_subtipos'] - e.loc[comun, 'brecha_canasta']).abs().max()
        d2 = (t.loc[comun, 'peso_imputado_pct'] - e.loc[comun, 'peso_imputado_pct']).abs().max()
        print(f'  contra {hoja} del Excel: {len(comun)} grupos en los dos (solo acá {len(t.index.difference(e.index))}, '
              f'solo en el Excel {len(e.index.difference(t.index))}); dif. máx. canasta {d1:.2e}, peso imputado {d2:.2e}')
