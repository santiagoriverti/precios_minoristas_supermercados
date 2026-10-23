# Series mensuales del nb06 (todas las sucursales y panel balanceado), columnas cortas.
# Uso: python -I -X utf8 r2_series.py <brecha_celiaca_AAAA-MM.xlsx>
import sys
import pandas as pd

pd.set_option('display.width', 250)
pd.set_option('display.max_columns', 40)
F = sys.argv[1]
CORTO = {'Fideos secos': 'fid', 'Galletitas dulces': 'dul', 'Galletitas saladas y crackers': 'sal',
         'Pan rallado y rebozador': 'reb', 'Cereales rellenos (almohaditas)': 'alm'}
for hoja in ['Serie_canasta', 'Serie_canasta_balanceada']:
    d = pd.read_excel(F, sheet_name=hoja)
    out = d[['mes', 'brecha_canasta', 'n_tipos', 'n_min', 'subtipos_imputados']].copy()
    for t, c in CORTO.items():
        out[f'b_{c}'] = d[f'brecha_{t}']
    for t, c in CORTO.items():
        out[f'n_{c}'] = d[f'n_{t}']
    out['d_canasta'] = out['brecha_canasta'].diff()
    print(f'\n=== {hoja}')
    print(out.round(1).to_string(index=False))
