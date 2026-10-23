# Resumen de las hojas del Excel del nb06: nombre, forma, columnas y primeras filas.
# Uso: python -I -X utf8 r1_resumen_excel.py <brecha_celiaca_AAAA-MM.xlsx> [hoja ...]
import sys
from pathlib import Path
import pandas as pd

pd.set_option('display.width', 250)
pd.set_option('display.max_columns', 40)
pd.set_option('display.max_colwidth', 60)
F = Path(sys.argv[1])
pedidas = sys.argv[2:]
xls = pd.ExcelFile(F, engine='openpyxl')
for h in xls.sheet_names:
    if pedidas and h not in pedidas:
        continue
    d = xls.parse(h)
    print(f'\n=== {h}: {d.shape[0]} filas x {d.shape[1]} columnas')
    print('columnas:', list(d.columns))
    n = 60 if pedidas else 4
    print(d.head(n).to_string())
