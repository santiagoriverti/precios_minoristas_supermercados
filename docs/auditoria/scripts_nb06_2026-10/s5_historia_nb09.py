# Historia 2022-01 -> 2026-10 de los candidatos (catálogo del 22/10/2026) con las salidas del nb09: cobertura mensual
# (sucursales por día, en promedio, en cada mes), meses con dato, caídas de cobertura y métricas del ranking.
# Uso: python -I -X utf8 s5_historia_nb09.py <salida.xlsx de s4_pares_misma_marca.py> <panel_mensual nb09 .parquet> <ranking nb09 .parquet> <salida.xlsx>
import sys
from pathlib import Path
import numpy as np
import pandas as pd

F_CAND, F_PANEL, F_RANK, F_OUT = (Path(a) for a in sys.argv[1:5])
pd.set_option('display.width', 260)
norm = lambda s: s.astype(str).str.strip().str.lstrip('0')

cand = pd.read_excel(F_CAND, sheet_name='Todos_por_tipo', dtype={'id_producto': str})
cand['id_producto'] = norm(cand['id_producto'])
cand = cand[(cand['sucursales'] >= 50) & (cand['lado'].eq('sin TACC') | cand['ref_trigo'])].copy()
ids = set(cand['id_producto'])

P = pd.read_parquet(F_PANEL)
P['id_producto'] = norm(P['id_producto'])
P = P[P['id_producto'].isin(ids)]
MESES = sorted(pd.read_parquet(F_PANEL, columns=['mes'])['mes'].unique())
M = P.pivot_table(index='id_producto', columns='mes', values='suc_diarias_prom', aggfunc='first').reindex(columns=MESES)

OFICIAL = [m for m in MESES if m <= '2026-07']           # semestrales oficiales (ago-oct 2026: SEPA diario, sin 8 comercios)
W24 = [m for m in OFICIAL if m >= '2024-05']             # después del colapso de cobertura de Molinos (dic-23 / abr-24)
HUECO = ['2023-12', '2024-01', '2024-02', '2024-03', '2024-04']

def metricas(row):
    v = row.dropna()
    out = {'primer_mes': v.index.min() if len(v) else None, 'ultimo_mes': v.index.max() if len(v) else None,
           'meses_con_dato': len(v)}
    if not len(v):
        return pd.Series(out)
    med = v.median()
    out['suc_mediana_mes'] = round(med, 1)
    for nom, w in [('2022', OFICIAL), ('2024_05', W24)]:
        x = row.reindex(w)
        out[f'todos_los_meses_{nom}'] = bool(x.notna().all())
        out[f'suc_min_{nom}'] = round(x.min(), 1) if x.notna().any() else np.nan
        out[f'min_sobre_mediana_{nom}'] = round(x.min() / med, 2) if x.notna().any() and med > 0 else np.nan
        out[f'mes_min_{nom}'] = x.idxmin() if x.notna().any() else None
    h = row.reindex(HUECO)
    out['hueco_dic23_abr24'] = round(h.min() / med, 2) if h.notna().any() and med > 0 else 0.0
    a22 = row.reindex([m for m in MESES if m.startswith('2022')]).mean()
    a26 = row.reindex([m for m in OFICIAL if m.startswith('2026')]).mean()
    out['cob_2022_sobre_2026'] = round(a22 / a26, 2) if pd.notna(a22) and a26 > 0 else np.nan
    out['meses_bajo_35pct'] = int((v < 0.35 * med).sum())
    return pd.Series(out)

H = M.apply(metricas, axis=1)
R = pd.read_parquet(F_RANK, columns=['id_producto', 'descripcion', 'primer_dia', 'ultimo_dia', 'comercios', 'cadenas',
                                     'cadena_principal', 'pct_cadena_principal', 'provincias', 'regiones', 'en_amba',
                                     'puntaje', 'ranking', 'solo_en_comercios_que_dejaron_de_publicar'])
R['id_producto'] = norm(R['id_producto'])
R = R.drop_duplicates('id_producto').set_index('id_producto').add_prefix('nb09_')
out = (cand.set_index('id_producto')
       .join(H, how='left').join(R, how='left').reset_index())
out['meses_con_dato'] = out['meses_con_dato'].fillna(0).astype(int)

# Reglas (mismo espíritu que la canasta de pass-through, umbrales de sin TACC más bajos)
def estable(df, w, min_suc, min_rel):
    return df[f'todos_los_meses_{w}'].eq(True) & (df[f'suc_min_{w}'] >= min_suc) & (df[f'min_sobre_mediana_{w}'] >= min_rel)
out['estable_desde_2022'] = estable(out, '2022', 50, 0.25)
out['estable_desde_2024_05'] = estable(out, '2024_05', 50, 0.35)

cols = ['tipo', 'forma', 'lado', 'id_producto', 'descripcion', 'marca', 'gramos', 'sucursales', 'cadenas', 'primer_mes',
        'meses_con_dato', 'suc_mediana_mes', 'suc_min_2022', 'mes_min_2022', 'hueco_dic23_abr24', 'cob_2022_sobre_2026',
        'suc_min_2024_05', 'min_sobre_mediana_2024_05', 'estable_desde_2022', 'estable_desde_2024_05', 'nb09_comercios',
        'nb09_provincias', 'nb09_pct_cadena_principal']
S = out[out['lado'] == 'sin TACC']
print('=== sin TACC (>= 50 sucursales el 22/10): cuántos tienen historia estable ===')
print(S.groupby('tipo').agg(productos=('id_producto', 'size'),
                            desde_2022=('estable_desde_2022', 'sum'), desde_2024_05=('estable_desde_2024_05', 'sum'),
                            con_dato_ene22=('primer_mes', lambda s: int((s == '2022-01').sum())),
                            aparecen_2025_o_despues=('primer_mes', lambda s: int((s >= '2025-01').sum())))
      .sort_values('productos', ascending=False).to_string())
print('\n=== con TACC (trigo, >= 50 sucursales): ídem ===')
C = out[out['lado'] != 'sin TACC']
print(C.groupby('tipo').agg(productos=('id_producto', 'size'), desde_2022=('estable_desde_2022', 'sum'),
                            desde_2024_05=('estable_desde_2024_05', 'sum'))
      .sort_values('productos', ascending=False).to_string())

print('\n=== sin TACC multicadena (>= 300 sucursales y >= 5 cadenas el 22/10) ===')
mc = S[(S['sucursales'] >= 300) & (S['cadenas'] >= 5)].sort_values(['tipo', 'sucursales'], ascending=[True, False])
print(mc[cols].to_string(index=False, max_colwidth=36))

# pares de la misma marca: historia de los dos lados
pr = pd.read_parquet(F_CAND.with_suffix('.pares.parquet'))
for c in ['sin_id', 'con_id']:
    pr[c] = norm(pr[c])
hh = out.set_index('id_producto')
for lado, c in [('sin', 'sin_id'), ('con', 'con_id')]:
    for k in ['primer_mes', 'suc_min_2022', 'hueco_dic23_abr24', 'suc_min_2024_05', 'estable_desde_2022',
              'estable_desde_2024_05']:
        pr[f'{lado}_{k}'] = pr[c].map(hh[k]) if k in hh else np.nan
pr = pr[(pr['sin_suc'] >= 300) & (pr['sin_cad'] >= 5)]
print('\n=== Pares de la misma marca (sin TACC multicadena): historia de los dos lados ===')
print(pr[['tipo', 'forma', 'sin_desc', 'sin_suc', 'sin_primer_mes', 'sin_suc_min_2022', 'sin_hueco_dic23_abr24',
          'sin_suc_min_2024_05', 'con_desc', 'con_suc', 'con_primer_mes', 'con_hueco_dic23_abr24',
          'con_suc_min_2024_05']].to_string(index=False, max_colwidth=34))

ser = M.reindex(mc['id_producto']).copy()
ser.insert(0, 'descripcion', mc.set_index('id_producto')['descripcion'])
ser.insert(0, 'tipo', mc.set_index('id_producto')['tipo'])
with pd.ExcelWriter(F_OUT, engine='openpyxl') as w:
    out[cols + [c for c in out.columns if c not in cols]].sort_values(['tipo', 'lado', 'sucursales'],
        ascending=[True, False, False]).to_excel(w, sheet_name='Historia_candidatos', index=False)
    pr.to_excel(w, sheet_name='Pares_con_historia', index=False)
    ser.reset_index().to_excel(w, sheet_name='Serie_sin_TACC_multicadena', index=False)
    M.reset_index().merge(out[['id_producto', 'tipo', 'lado', 'descripcion']], on='id_producto') \
        .to_excel(w, sheet_name='Serie_todos', index=False)
out.to_parquet(F_OUT.with_suffix('.parquet'), index=False)
M.to_parquet(F_OUT.with_name(F_OUT.stem + '_serie.parquet'))
print(f'\nGuardado: {F_OUT}')
