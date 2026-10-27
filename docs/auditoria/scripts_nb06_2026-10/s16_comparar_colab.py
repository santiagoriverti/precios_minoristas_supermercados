# Compara el Excel de una corrida del nb06 (Colab) con los resultados esperados de la simulación local
# (docs/brecha_celiaca/simulacion_2026-10-23/: un CSV por hoja, sacado del Excel que generaron las celdas reales con
# los mismos zips del Drive). Para cada hoja: filas que están de un solo lado y diferencia máxima de cada columna.
# Con los mismos zips y el mismo notebook tiene que dar todo igual (diferencias de redondeo < 1e-6).
# Uso: python -I -X utf8 s16_comparar_colab.py <brecha_celiaca_AAAA-MM.xlsx de Colab> <carpeta de esperados>
import sys
from pathlib import Path
import numpy as np
import pandas as pd

F_XLS, D_ESP = Path(sys.argv[1]), Path(sys.argv[2])
TOL = 1e-6
CLAVES = ['tipo', 'subtipo', 'lado', 'rol', 'ean', 'ean_norm', 'mes', 'anio', 'provincia', 'region', 'empresa',
          'cadena', 'localidad', 'id_comercio', 'id_bandera', 'id_sucursal', 'departamento_id', 'serie', 'desde',
          'producto', 'universo',
          # hojas de la CELDA 8c y Resumen (2026-10-27): sin estas claves la unión era muchos a muchos
          'suc_key', 'nivel', 'escenario', 'agrupacion', 'grupo', 'medida', 'modelo', 'termino', 'variable', 'controles',
          'item_cba', 'tema', 'indicador']
TEXTO = {c: str for c in CLAVES}
def num(s):
    # columnas numéricas o booleanas (confiable, revisar, amba...) como float; el resto queda NaN
    if s.dtype == bool:
        return s.astype(float)
    if s.dtype == object:
        s = s.map(lambda v: float(v) if isinstance(v, (bool, np.bool_)) else v)
    return pd.to_numeric(s, errors='coerce')

xls = pd.ExcelFile(F_XLS, engine='openpyxl')
print(f'{F_XLS.name}: {len(xls.sheet_names)} hojas | esperados: {D_ESP}')
n_ok = n_mal = 0
for f in sorted(D_ESP.glob('*.csv')):
    hoja = f.stem
    if hoja not in xls.sheet_names:
        print(f'  FALTA la hoja {hoja}'); n_mal += 1; continue
    e = pd.read_csv(f, dtype=TEXTO)
    c = xls.parse(hoja, dtype=TEXTO)
    k = [x for x in CLAVES if x in e.columns and x in c.columns]
    extra = sorted(set(e.columns) ^ set(c.columns))
    if not len(e) and not len(c):
        print(f'  OK      {hoja}: vacía en los dos'); n_ok += 1; continue
    if k:
        m = e.merge(c, on=k, how='outer', suffixes=('_esp', '_colab'), indicator=True)
    else:
        m = e.join(c, lsuffix='_esp', rsuffix='_colab', how='outer')
        m['_merge'] = 'both'
    solo = m['_merge'].value_counts().to_dict()
    b = m[m['_merge'] == 'both']
    peor, txt = 0.0, []
    for col in [x for x in e.columns if x not in k and x in c.columns]:
        a, z = b[f'{col}_esp'], b[f'{col}_colab']
        an, zn = num(a), num(z)
        if an.notna().any() or zn.notna().any():
            d = (an - zn).abs()
            d[an.isna() != zn.isna()] = np.inf
            if d.max() > TOL:
                txt.append(f'{col} (dif. máx. {d.max():.4g})')
            peor = max(peor, float(d.max()) if d.notna().any() else 0.0)
        elif (a.fillna('') .astype(str) != z.fillna('').astype(str)).any():
            txt.append(f'{col} (textos distintos)')
    ok = not txt and solo.get('left_only', 0) == 0 and solo.get('right_only', 0) == 0 and not extra
    n_ok += ok; n_mal += not ok
    print(f'  {"OK     " if ok else "DIFIERE"} {hoja}: {len(e)} filas esperadas, {len(c)} en Colab'
          + (f' | solo esperadas {solo.get("left_only", 0)}, solo Colab {solo.get("right_only", 0)}'
             if solo.get('left_only', 0) or solo.get('right_only', 0) else '')
          + (f' | columnas distintas: {extra}' if extra else '')
          + (f' | {"; ".join(txt[:6])}' if txt else f' | dif. máx. {peor:.2g}'))
print(f'\n{n_ok} hojas iguales, {n_mal} con diferencias')
