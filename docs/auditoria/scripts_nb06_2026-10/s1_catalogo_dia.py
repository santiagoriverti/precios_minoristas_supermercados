# Catálogo de un día del SEPA diario: productos de los tipos con dicotomía TACC / sin-TACC, con cobertura.
# Uso: python -I -X utf8 s1_catalogo_dia.py <carpeta del día> <salida.parquet>
# Lee comercio.csv, sucursales.csv y productos.csv de cada zip (separador '|'), se queda con las filas cuya
# descripción es de un tipo de interés o dice "sin TACC/gluten", y guarda una fila por (sucursal, producto).
import re, sys, zipfile, io
from pathlib import Path
import pandas as pd

DIA, OUT = Path(sys.argv[1]), Path(sys.argv[2])

RE_SIN = r'sin\s*t\.?\s*a\.?\s*c\.?\s*c|s/\s*t\.?a\.?c\.?c|s\.\s*tacc|sin\s*glut|s/\s*glut|libre\s+de\s+glut|gluten\s*free|celiac|\bstacc\b'
RE_TIPOS = (r'fideo|spag|tallar|mostach|tirabu|penne|fusil|codito|cinta|caracol|rigat|letra|moñ|farfall|dedali|cornet|'
            r'risoni|ñoqui|noqui|lasag|ravio|sorrent|canelon|galleti|galleta|cracker|tostad|tortit|bizcoch|oblea|scon|'
            r'vainill|pepa|magdalen|alfajor|budin|budín|premezcl|harina|rebozad|rallad|pan |pan$|panific|prepiz|pizz|'
            r'tapa|masa|cereal|copo|granola|avena|salvado|barra|barrit|cerve|malta|grisin|palito|chizit|snack|'
            r'polenta|semola|sémola|caldo|sopa|empana|tarta|wafle|waffle|muffin|brownie|torta|pionono|vainillas')
_re_rel = re.compile(f'(?:{RE_SIN})|(?:{RE_TIPOS})', re.IGNORECASE)

COLS = ['id_comercio', 'id_bandera', 'id_sucursal', 'id_producto', 'productos_ean', 'productos_descripcion',
        'productos_cantidad_presentacion', 'productos_unidad_medida_presentacion', 'productos_marca',
        'productos_precio_lista']

filas, sucs, coms = [], [], []
for z in sorted(DIA.glob('*.zip')):
    try:
        zf = zipfile.ZipFile(z)
    except zipfile.BadZipFile:
        print(f'  (salteado, no es zip: {z.name})'); continue
    with zf:
        nombres = {Path(n).name: n for n in zf.namelist()}
        if 'comercio.csv' in nombres:
            with zf.open(nombres['comercio.csv']) as f:
                coms.append(pd.read_csv(f, sep='|', dtype=str, encoding='utf-8-sig'))
        if 'sucursales.csv' in nombres:
            with zf.open(nombres['sucursales.csv']) as f:
                sucs.append(pd.read_csv(f, sep='|', dtype=str, encoding='utf-8-sig'))
        n_rel = n_tot = 0
        with zf.open(nombres['productos.csv']) as f:
            txt = io.TextIOWrapper(f, encoding='utf-8-sig', errors='replace')
            for ch in pd.read_csv(txt, sep='|', dtype=str, usecols=lambda c: c in COLS, chunksize=500_000,
                                  on_bad_lines='skip'):
                n_tot += len(ch)
                u = pd.Series(ch['productos_descripcion'].dropna().unique())
                rel = set(u[u.str.contains(_re_rel)])
                ch = ch[ch['productos_descripcion'].isin(rel)]
                n_rel += len(ch)
                if len(ch):
                    filas.append(ch)
        print(f'  {z.name.split("_")[2]:<18} filas {n_tot:>10,}  relevantes {n_rel:>9,}')

df = pd.concat(filas, ignore_index=True)
df['precio'] = pd.to_numeric(df['productos_precio_lista'], errors='coerce')
df = df.drop(columns=['productos_precio_lista'])
suc = pd.concat(sucs, ignore_index=True)
com = pd.concat(coms, ignore_index=True)
suc.to_parquet(OUT.with_name(OUT.stem + '_sucursales.parquet'), index=False)
com.to_parquet(OUT.with_name(OUT.stem + '_comercios.parquet'), index=False)
df.to_parquet(OUT, index=False)
print(f'Filas relevantes: {len(df):,} | productos: {df["id_producto"].nunique():,} | sucursales: '
      f'{df.groupby(["id_comercio","id_bandera","id_sucursal"]).ngroups:,} | comercios: {df["id_comercio"].nunique()}')
print(com.head(30).to_string())
