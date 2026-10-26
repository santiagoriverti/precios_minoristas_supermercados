# Compara dos Excel del nb06 hoja por hoja y celda por celda, todas las hojas (también Leeme, Comparacion_productos y
# Detalle_producto, que s16 deja afuera): mismas hojas, columnas y filas; números con tolerancia relativa, texto exacto.
# Si una hoja difiere en el orden de las filas (valores casi empatados), compara ordenando por todas las columnas; para
# emparejar por clave, usar s16.
# Uso: python -I -X utf8 r13_comparar_excels.py <Excel A (p. ej. Colab)> <Excel B (p. ej. la simulación)> [tolerancia]
import sys
from pathlib import Path

import numpy as np
import pandas as pd

A, B = Path(sys.argv[1]), Path(sys.argv[2])
TOL = float(sys.argv[3]) if len(sys.argv) > 3 else 1e-9
xa, xb = pd.ExcelFile(A, engine='openpyxl'), pd.ExcelFile(B, engine='openpyxl')
print(f'A: {len(xa.sheet_names)} hojas | B: {len(xb.sheet_names)} hojas | mismo orden: {xa.sheet_names == xb.sheet_names}')
print(f'  solo en A: {sorted(set(xa.sheet_names) - set(xb.sheet_names))} | '
      f'solo en B: {sorted(set(xb.sheet_names) - set(xa.sheet_names))}')


def _num(s):
    return pd.to_numeric(s.map(lambda v: float(v) if isinstance(v, (bool, np.bool_)) else v), errors='coerce').astype(float)


def comparar(a, b):
    # (celdas de texto distintas, diferencia numérica relativa máxima)
    txt, dmax = 0, 0.0
    for c in a.columns:
        na, nb = _num(a[c]), _num(b[c])
        if (na.notna() | a[c].isna()).all() and (nb.notna() | b[c].isna()).all():
            ambos = na.notna() & nb.notna()
            txt += int((na.isna() != nb.isna()).sum())
            if ambos.any():
                dmax = max(dmax, float(((na[ambos] - nb[ambos]).abs() / np.maximum(1.0, nb[ambos].abs())).max()))
        else:
            txt += int((a[c].fillna('<NA>').astype(str) != b[c].fillna('<NA>').astype(str)).sum())
    return txt, dmax


n_ok = n_mal = 0
for h in xa.sheet_names:
    if h not in xb.sheet_names:
        continue
    a, b = xa.parse(h, dtype=object), xb.parse(h, dtype=object)
    if a.shape != b.shape or list(a.columns) != list(b.columns):
        print(f'  DIFIERE {h}: forma {a.shape} contra {b.shape}; mismas columnas: {list(a.columns) == list(b.columns)}')
        n_mal += 1
        continue
    txt, dmax = comparar(a, b)
    nota = ''
    if txt or dmax > TOL:
        # mismas filas en otro orden? se ordenan las dos por todas las columnas (números redondeados) y se comparan
        def _orden(d):
            k = pd.DataFrame({c: (_num(d[c]).round(6) if _num(d[c]).notna().sum() == d[c].notna().sum()
                                  else d[c].fillna('').astype(str)) for c in d.columns})
            return d.loc[k.sort_values(list(k.columns), kind='stable').index].reset_index(drop=True)
        txt2, dmax2 = comparar(_orden(a), _orden(b))
        if txt2 == 0 and dmax2 <= TOL:
            txt, dmax, nota = 0, dmax2, ' (mismas filas en otro orden)'
    ok = txt == 0 and dmax <= TOL
    n_ok += ok
    n_mal += not ok
    print(f'  {"OK     " if ok else "DIFIERE"} {h}: {a.shape[0]} filas x {a.shape[1]} columnas | celdas de texto '
          f'distintas {txt} | dif. numérica relativa máx. {dmax:.1e}{nota}')
print()
print(f'{n_ok} hojas iguales, {n_mal} con diferencias')
