# Arma una carpeta de resultados esperados del nb06 (un CSV por hoja) desde el Excel de una simulación con las celdas
# reales (s11), para comparar después una corrida de Colab con s16_comparar_colab.py. Deja afuera Leeme y las hojas
# grandes del último mes (Comparacion_productos, Detalle_producto).
# Uso: python -I -X utf8 s17_esperados.py <brecha_celiaca_AAAA-MM.xlsx de la simulación> <carpeta de salida>
import sys
from pathlib import Path
import pandas as pd

F_XLS, D_OUT = Path(sys.argv[1]), Path(sys.argv[2])
AFUERA = {'Leeme', 'Comparacion_productos', 'Detalle_producto'}
CLAVES = ['tipo', 'subtipo', 'lado', 'rol', 'ean', 'ean_norm', 'mes', 'anio', 'provincia', 'region', 'empresa',
          'cadena', 'localidad', 'id_comercio', 'id_bandera', 'id_sucursal', 'departamento_id', 'serie', 'desde', 'hasta',
          'producto', 'universo']
D_OUT.mkdir(parents=True, exist_ok=True)
xls = pd.ExcelFile(F_XLS, engine='openpyxl')
n = 0
for hoja in xls.sheet_names:
    if hoja in AFUERA:
        continue
    d = xls.parse(hoja, dtype={c: str for c in CLAVES})
    d.to_csv(D_OUT / f'{hoja}.csv', index=False)
    n += 1
    print(f'  {hoja}: {len(d)} filas')
print(f'{n} hojas en {D_OUT}')
