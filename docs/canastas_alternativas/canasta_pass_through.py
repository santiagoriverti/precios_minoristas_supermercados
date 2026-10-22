# Canasta fija para estudiar el pass-through del tipo de cambio a precios con frecuencia DIARIA (01/01/2022 -> 20/10/2026).
# Elige, con reglas fijas, productos del SEPA con precio TODOS los días, cobertura amplia y estable de sucursales,
# cadenas y provincias, y los agrupa por grupo del IPC (INDEC) para desagregar el efecto. Insumo: las salidas del nb09
# (ranking de trazabilidad, panel mensual y la hoja Dias del Excel). Salida: un Excel con la hoja Selección compatible
# con el nb08 (columna cantidad_08) y la documentación de la selección.
#
# Uso: python -I -X utf8 canasta_pass_through.py <ranking nb09 .parquet> <panel mensual nb09 .parquet> <Excel nb09> <salida.xlsx>
import sys
from pathlib import Path
import numpy as np
import pandas as pd

F_RANK, F_PANEL, F_XLS, F_OUT = (Path(a) for a in sys.argv[1:5])
DESDE, HASTA = pd.Timestamp('2022-01-01'), pd.Timestamp('2026-10-20')

# ── Reglas (en el orden en que se aplican) ──────────────────────────────────────────────────────────────────────────
RUBROS_CONSUMO = ['Almacén', 'Bebidas', 'Frescos', 'Congelados', 'Limpieza', 'Perfumería', 'Mascotas', 'Bebés y mamás']
CADENAS_GRANDES = ['Carrefour', 'ChangoMas', 'Coto', 'Cencosud (Vea/Disco/Jumbo)', 'La Anónima', 'Cooperativa Obrera',
                   'DIA', 'Toledo']
MIN_SUC_MES = 150          # sucursales por día, en promedio, en CADA uno de los meses
MIN_MES_REL = 0.35         # ningún mes por debajo del 35% de su mes mediano (colapsos de cobertura)
RATIO_22_26 = (1 / 3, 3)   # cobertura de 2022 entre un tercio y el triple de la de 2026
MIN_GRANDES = 6            # presente en al menos 6 de las 8 cadenas grandes
MAX_PRINCIPAL = 60         # ninguna cadena con más del 60% de sus sucursal-días
MIN_PROV_DIARIA = 85       # presente cada día, en promedio, en el 85% de las provincias con sucursales activas
MAX_CV = 25                # dispersión del precio entre sucursales en oct-26 (descarta unidades o presentaciones mezcladas)
MISMO_PRECIO = 0.03        # variedades de la misma marca, subcategoría y presentación con precio a menos de 3%: una sola

# ── Grupos del IPC (INDEC, base dic-2016; ponderadores_ipc.xls por región) ──────────────────────────────────────────
# Fracción del gasto de cada región: GBA, Pampeana, Noreste, Noroeste, Cuyo, Patagonia. Peso de las regiones en el IPC
# nacional: Metodología del IPC 2019, cuadro 6. Copiado de IPC_jubilados/data/reference (descargado 2026-10-13).
REGIONES = ['GBA', 'Pampeana', 'Noreste', 'Noroeste', 'Cuyo', 'Patagonia']
PESO_REGION = {'GBA': 0.447, 'Pampeana': 0.342, 'Noreste': 0.045, 'Noroeste': 0.069, 'Cuyo': 0.052, 'Patagonia': 0.046}
IPC = {
    '01.1.1': ('Pan y cereales', [0.0405, 0.0502, 0.0659, 0.0649, 0.0521, 0.0461]),
    '01.1.2': ('Carnes y derivados', [0.0698, 0.0981, 0.1327, 0.125, 0.1032, 0.0992]),
    '01.1.3': ('Pescados y mariscos', [0.0051, 0.0047, 0.0029, 0.0034, 0.0045, 0.0048]),
    '01.1.4': ('Leche, productos lácteos, huevos y alimentos vegetales', [0.0345, 0.0373, 0.041, 0.0369, 0.0355, 0.0368]),
    '01.1.5': ('Aceites, grasas y manteca', [0.0055, 0.0076, 0.009, 0.0064, 0.0066, 0.0063]),
    '01.1.6': ('Frutas', [0.0127, 0.0146, 0.0146, 0.0145, 0.011, 0.0128]),
    '01.1.7': ('Verduras, tubérculos y legumbres', [0.0223, 0.029, 0.0359, 0.0358, 0.0279, 0.0268]),
    '01.1.8': ('Azúcar, dulces, chocolate, golosinas, etc.', [0.0101, 0.0121, 0.0112, 0.0124, 0.0103, 0.0102]),
    '01.1.9': ('Otros alimentos', [0.0029, 0.0037, 0.0036, 0.0036, 0.0036, 0.0048]),
    '01.2.1': ('Café, té, yerba y cacao', [0.0068, 0.0082, 0.0093, 0.0064, 0.0066, 0.0069]),
    '01.2.2': ('Aguas minerales, bebidas gaseosas y jugos', [0.0243, 0.021, 0.0271, 0.0372, 0.0229, 0.0197]),
    '02.1.1': ('Bebidas espirituosas, destiladas y licores', [0.0006, 0.0006, 0.0003, 0.0007, 0.0005, 0.0009]),
    '02.1.2': ('Vinos', [0.0107, 0.0139, 0.0145, 0.0102, 0.0111, 0.01]),
    '02.1.3': ('Cerveza', [0.0029, 0.0034, 0.0056, 0.0029, 0.0026, 0.0031]),
    '05.6.1': ('Bienes para el hogar no durables', [0.0167, 0.0212, 0.0209, 0.0204, 0.0205, 0.0179]),
    '06.1.2': ('Otros productos medicinales', [0.0016, 0.0018, 0.0021, 0.0018, 0.0018, 0.0011]),
    '09.3.4': ('Mascotas y productos conexos', [0.0065, 0.0048, 0.003, 0.0036, 0.0066, 0.0053]),
    '12.1.3': ('Artículos y productos para la atención personal', [0.0197, 0.024, 0.0252, 0.0263, 0.024, 0.0213]),
}
PESO_NACIONAL = {k: sum(PESO_REGION[r] * w for r, w in zip(REGIONES, v[1])) for k, v in IPC.items()}
TIPO = {'01.1': 'Alimentos', '01.2': 'Bebidas sin alcohol', '02.1': 'Bebidas alcohólicas', '05.6': 'Limpieza del hogar',
        '06.1': 'Cuidado personal y botiquín', '12.1': 'Cuidado personal y botiquín', '09.3': 'Mascotas'}

POR_CATEGORIA = {
    'Aceites': '01.1.5', 'Aderezos': '01.1.9', 'Azúcar y Edulcorantes': '01.1.8', 'Cereales': '01.1.1',
    'Encurtidos Aceitunas y Pickles': '01.1.7', 'Galletitas': '01.1.1', 'Golosinas': '01.1.8', 'Harinas': '01.1.1',
    'Infusiones': '01.2.1', 'Mermeladas y Dulces': '01.1.8', 'Panificados': '01.1.1', 'Pastas Secas': '01.1.1',
    'Repostería y Postres': '01.1.8', 'Snacks': '01.1.9', 'Sopas Caldos y Puré': '01.1.9', 'Aguas': '01.2.2',
    'Gaseosas': '01.2.2', 'Jugos': '01.2.2', 'Isotónicas y Energizantes': '01.2.2', 'Bebida Herbal': '01.2.2',
    'Aperitivos': '02.1.1', 'Bebidas Blancas y Licores': '02.1.1', 'Vinos y Espumantes': '02.1.2', 'Cerveza': '02.1.3',
    'Cuidado de Mamá': '12.1.3', 'Cuidado del Bebé': '12.1.3', 'Alimentos Congelados': '01.1.9', 'Hamburguesas': '01.1.2',
    'Helados y Postres': '01.1.8', 'Prefritos': '01.1.7', 'Carnicería': '01.1.2', 'Pastas y Tapas': '01.1.1',
    'Huevos': '01.1.4', 'Alimentos para Gatos': '09.3.4', 'Alimentos para Perros': '09.3.4',
    'Productos Farmacéuticos': '06.1.2',
}

def grupo_ipc(r):
    # grupo del IPC de un producto según su rubro, categoría y subcategoría del Maestro de Productos Interno
    cat, sub, desc = r['categoria'], str(r['subcategoria']), str(r['descripcion']).lower()
    if r['rubro'] == 'Limpieza':
        return '12.1.3' if sub == 'Papel Higiénico' else '05.6.1'
    if r['rubro'] == 'Perfumería':
        return POR_CATEGORIA.get(cat, '12.1.3')
    if cat == 'Arroz y Legumbres':
        return '01.1.7' if 'Legumbre' in sub else '01.1.1'
    if cat == 'Conservas':
        return ('01.1.2' if 'Paté' in sub else '01.1.3' if ('Pescado' in sub or 'Atún' in sub) else
                '01.1.6' if 'Fruta' in sub else '01.1.7')
    if cat == 'Fiambrería':
        return '01.1.4' if sub.startswith('Queso') else '01.1.2'
    if cat == 'Prefritos':           # papas y vegetales prefritos, pero también bocaditos y patitas de pollo
        return ('01.1.2' if any(p in desc for p in ('pollo', 'nugget', 'patita', 'medall', 'carne')) else
                '01.1.7' if any(p in desc for p in ('papa', 'vegetal', 'verdura', 'espinaca', 'choclo')) else '01.1.9')
    if cat == 'Lácteos':
        if sub == 'Levaduras y Grasas':
            return '01.1.9' if 'levadura' in desc else '01.1.5'
        return '01.1.5' if sub == 'Mantecas y Margarinas' else '01.1.4'
    return POR_CATEGORIA.get(cat)

ORIGEN = [((0, 139), 'EE.UU. y Canadá'), ((300, 379), 'Francia'), ((400, 440), 'Alemania'), ((500, 509), 'Reino Unido'),
          ((540, 549), 'Bélgica y Luxemburgo'), ((690, 699), 'China'), ((750, 750), 'México'), ((754, 755), 'Canadá'),
          ((759, 759), 'Venezuela'), ((760, 769), 'Suiza'), ((770, 771), 'Colombia'), ((773, 773), 'Uruguay'),
          ((779, 779), 'Argentina'), ((780, 780), 'Chile'), ((784, 784), 'Paraguay'), ((786, 786), 'Ecuador'),
          ((789, 790), 'Brasil'), ((800, 839), 'Italia'), ((840, 849), 'España'), ((870, 879), 'Países Bajos'),
          ((880, 880), 'Corea del Sur')]

def origen_gs1(ean):
    # país del prefijo GS1 (dónde se registró el código, no necesariamente dónde se fabricó). Un EAN-8 tiene el prefijo
    # en sus 3 primeros dígitos; un UPC-A (12) o un EAN-13 al que se le sacaron los ceros, completado a 13.
    e = str(ean)
    p = int(e[:3] if len(e) == 8 else e.zfill(13)[:3])
    return next((n for (a, b), n in ORIGEN if a <= p <= b), 'Otro')

# ── Datos ────────────────────────────────────────────────────────────────────────────────────────────────────────────
R = pd.read_parquet(F_RANK)
P = pd.read_parquet(F_PANEL)
DIAS = pd.read_excel(F_XLS, sheet_name='Dias', engine='calamine')
DIAS['fecha'] = pd.to_datetime(DIAS['fecha'])
R['cadenas_grandes'] = R['cadenas'].map(lambda s: len(set(s.split('; ')) & set(CADENAS_GRANDES)))
Pm = P.pivot(index='id_producto', columns='mes', values='suc_diarias_prom')
Pm = Pm[[c for c in Pm.columns if DESDE.strftime('%Y-%m') <= c <= HASTA.strftime('%Y-%m')]]
R['suc_min_mensual'] = R['id_producto'].map(Pm.min(axis=1))
R['mes_min_cobertura'] = R['id_producto'].map(Pm.idxmin(axis=1))
R['min_mes_sobre_mediana'] = R['id_producto'].map(Pm.min(axis=1) / Pm.median(axis=1))
R['cobertura_2022_sobre_2026'] = R['id_producto'].map(Pm[[c for c in Pm if c < '2023']].mean(axis=1) /
                                                      Pm[[c for c in Pm if c >= '2026']].mean(axis=1))

# ── Embudo ───────────────────────────────────────────────────────────────────────────────────────────────────────────
continuo = (R['primer_dia'] <= DESDE) & (R['racha_max_dias'] == R['dias_con_precio']) & (R['ultimo_dia'] >= HASTA)
REGLAS = [
    ('1. Precio todos los días del 01/01/2022 al 20/10/2026', continuo),
    ('2. EAN del Maestro de Productos, sin blacklist ni precio simbólico',
     R['es_ean'] & R['en_maestro'] & ~R['blacklist'] & ~R['precio_simbolico']),
    ('3. Bien de consumo masivo (rubros ' + ', '.join(RUBROS_CONSUMO) + ')', R['rubro'].isin(RUBROS_CONSUMO)),
    (f'4. Al menos {MIN_SUC_MES} sucursales por día en promedio en cada mes', R['suc_min_mensual'] >= MIN_SUC_MES),
    (f'5. Cobertura estable: ningún mes bajo el {MIN_MES_REL:.0%} de su mes mediano y 2022 entre 1/3 y 3 veces 2026',
     (R['min_mes_sobre_mediana'] >= MIN_MES_REL) & R['cobertura_2022_sobre_2026'].between(*RATIO_22_26)),
    (f'6. En al menos {MIN_GRANDES} de las 8 cadenas grandes y ninguna con más del {MAX_PRINCIPAL}% de sus sucursal-días',
     (R['cadenas_grandes'] >= MIN_GRANDES) & (R['pct_cadena_principal'] <= MAX_PRINCIPAL)),
    (f'7. Las 24 provincias y, cada día, en promedio en el {MIN_PROV_DIARIA}% de las provincias con sucursales activas',
     (R['provincias'] == 24) & (R['pct_prov_diaria_prom'] >= MIN_PROV_DIARIA)),
    (f'8. Precio parejo entre sucursales (CV de oct-26 <= {MAX_CV}%)', R['cv_precio_ultimo_mes_%'] <= MAX_CV),
]
R['motivo_exclusion'] = ''
vivo = pd.Series(True, index=R.index)
embudo = []
for nombre, regla in REGLAS:
    cae = vivo & ~regla.fillna(False).astype(bool)
    R.loc[cae, 'motivo_exclusion'] = nombre
    vivo &= ~cae
    embudo.append((nombre, int(vivo.sum())))

# 9. Variedades del mismo producto (sabores, colores): misma marca, subcategoría y presentación y mismo precio
S = R[vivo].copy()
S['_k'] = S['marca'].fillna('') + '|' + S['subcategoria'].fillna('') + '|' + S['presentacion'].fillna('')
S = S.sort_values(['_k', 'precio_mediano_ultimo_mes'])
_rel = S.groupby('_k')['precio_mediano_ultimo_mes'].transform(lambda p: p / p.shift(1) - 1)
S['_cluster'] = (S['_k'] != S['_k'].shift(1)) | (_rel > MISMO_PRECIO)
S['_cluster'] = S['_cluster'].cumsum()
S = S.sort_values(['_cluster', 'suc_min_mensual', 'puntaje'], ascending=[True, False, False])
elegido = S.drop_duplicates('_cluster')
repetido = S[~S.index.isin(elegido.index)]
_rep = elegido.set_index('_cluster')['descripcion']
R.loc[repetido.index, 'motivo_exclusion'] = ('9. Variedad del mismo producto y precio que: ' +
                                             repetido['_cluster'].map(_rep).astype(str))
embudo.append(('9. Una variedad por marca + subcategoría + presentación con el mismo precio', len(elegido)))
C = R.loc[elegido.index].copy()

# ── Grupos para desagregar y pesos ──────────────────────────────────────────────────────────────────────────────────
C['grupo_ipc_cod'] = C.apply(grupo_ipc, axis=1)
sin_grupo = C[C['grupo_ipc_cod'].isna()]
if len(sin_grupo):
    raise SystemExit('Categorías sin grupo del IPC: ' + str(sin_grupo['categoria'].value_counts().to_dict()))
C['grupo_ipc'] = C['grupo_ipc_cod'].map(lambda k: IPC[k][0])
C['tipo'] = C['grupo_ipc_cod'].str[:4].map(TIPO)
C['perecedero'] = C['rubro'].isin(['Frescos', 'Congelados'])
C['origen_gs1'] = C['id_producto'].map(origen_gs1)
C['codigo_argentino'] = C['origen_gs1'] == 'Argentina'
n_grupo = C.groupby('grupo_ipc_cod')['id_producto'].transform('size')
pn = C['grupo_ipc_cod'].map(PESO_NACIONAL)
_tot = sum(PESO_NACIONAL[g] for g in C['grupo_ipc_cod'].unique())
C['peso_ipc_%'] = pn / _tot / n_grupo * 100                     # IPC nacional entre los grupos presentes, igual adentro
C['peso_igual_grupo_%'] = 100 / C['grupo_ipc_cod'].nunique() / n_grupo
C['cantidad_08'] = (C['peso_ipc_%'] / 100 * 1_000_000 / C['precio_mediano_ultimo_mes']).round(6)
C = C.sort_values(['grupo_ipc_cod', 'categoria', 'subcategoria', 'descripcion']).reset_index(drop=True)
EN_CANASTA = R['id_producto'].isin(C['id_producto'])

COLS = ['id_producto', 'descripcion', 'marca', 'presentacion', 'proveedor', 'rubro', 'categoria', 'subcategoria',
        'grupo_ipc_cod', 'grupo_ipc', 'tipo', 'perecedero', 'origen_gs1', 'codigo_argentino', 'cantidad_08', 'peso_ipc_%',
        'peso_igual_grupo_%', 'precio_mediano_ultimo_mes', 'dias_con_precio', 'suc_diarias_prom', 'suc_diarias_min',
        'suc_min_mensual', 'mes_min_cobertura', 'min_mes_sobre_mediana', 'cobertura_2022_sobre_2026', 'comercios',
        'cadenas_grandes', 'cadena_principal', 'pct_cadena_principal', 'provincias', 'pct_prov_diaria_prom',
        'cv_precio_ultimo_mes_%', 'puntaje', 'ranking']
sel = C[COLS].rename(columns={'precio_mediano_ultimo_mes': 'precio_mediano_oct26', 'ranking': 'ranking_nb09',
                              'cv_precio_ultimo_mes_%': 'cv_precio_oct26_%'})

grupos = (C.groupby(['grupo_ipc_cod', 'grupo_ipc', 'tipo'])
          .agg(productos=('id_producto', 'size'), peso_canasta_ipc_pct=('peso_ipc_%', 'sum'),
               peso_canasta_igual_pct=('peso_igual_grupo_%', 'sum'), suc_diarias_prom_mediana=('suc_diarias_prom', 'median'),
               codigo_no_argentino=('codigo_argentino', lambda s: int((~s).sum())))
          .reset_index())
grupos.insert(3, 'peso_ipc_nacional_pct', grupos['grupo_ipc_cod'].map(PESO_NACIONAL) * 100)
for c in ['peso_ipc_nacional_pct', 'peso_canasta_ipc_pct', 'peso_canasta_igual_pct']:
    grupos[c] = grupos[c].round(3)

def resumen_por(col):
    t = C.groupby(col).agg(productos=('id_producto', 'size'), peso_ipc_pct=('peso_ipc_%', 'sum')).reset_index()
    t.insert(0, 'dimension', col)
    return t.rename(columns={col: 'valor'})
resumen = pd.concat([resumen_por(c) for c in ['tipo', 'rubro', 'perecedero', 'origen_gs1', 'cadena_principal']],
                    ignore_index=True)
resumen['peso_ipc_pct'] = resumen['peso_ipc_pct'].round(2)

# Básicos que no entran (para decidir si se relaja alguna regla)
BASICOS = ['Aceites', 'Harinas', 'Arroz y Legumbres', 'Pastas Secas', 'Azúcar y Edulcorantes', 'Lácteos', 'Huevos',
           'Infusiones', 'Galletitas', 'Conservas']
ex = R[continuo & R['es_ean'] & R['categoria'].isin(BASICOS) & ~EN_CANASTA & (R['suc_diarias_prom'] >= 300)]
ex = (ex.sort_values('suc_diarias_prom', ascending=False).groupby('categoria').head(6)
      [['categoria', 'subcategoria', 'id_producto', 'descripcion', 'motivo_exclusion', 'suc_diarias_prom', 'suc_diarias_min',
        'suc_min_mensual', 'mes_min_cobertura', 'min_mes_sobre_mediana', 'cobertura_2022_sobre_2026', 'cadenas_grandes',
        'pct_cadena_principal', 'pct_prov_diaria_prom', 'cv_precio_ultimo_mes_%']]
      .sort_values(['categoria', 'suc_diarias_prom'], ascending=[True, False]))

# Días con cobertura incompleta del SEPA: menos del 75% de las sucursales o de los comercios de la mediana de su mes
D = DIAS[(DIAS['fecha'] >= DESDE) & (DIAS['fecha'] <= HASTA)].copy()
_m = D['fecha'].dt.strftime('%Y-%m')
D['suc_mediana_mes'] = D.groupby(_m)['sucursales'].transform('median')
D['com_mediana_mes'] = D.groupby(_m)['comercios'].transform('median')
inc = D[(D['sucursales'] < 0.75 * D['suc_mediana_mes']) | (D['comercios'] < 0.75 * D['com_mediana_mes'])]
inc = inc[['fecha', 'sucursales', 'suc_mediana_mes', 'comercios', 'com_mediana_mes', 'productos', 'archivo']]
cal = pd.date_range(DESDE, HASTA)
sin_dato = cal.difference(pd.DatetimeIndex(D['fecha']))

cand = R[continuo].copy()
cand['seleccionado'] = EN_CANASTA[continuo]
if int(cand['seleccionado'].sum()) != len(C) or (cand['seleccionado'] & (cand['motivo_exclusion'] != '')).any():
    raise SystemExit('Candidatos no cuadra con la Selección')
cand = cand.sort_values(['seleccionado', 'puntaje'], ascending=False)[
    ['id_producto', 'descripcion', 'rubro', 'categoria', 'seleccionado', 'motivo_exclusion', 'suc_diarias_prom',
     'suc_diarias_min', 'suc_min_mensual', 'mes_min_cobertura', 'min_mes_sobre_mediana', 'cobertura_2022_sobre_2026',
     'cadenas_grandes', 'pct_cadena_principal', 'provincias', 'pct_prov_diaria_prom', 'cv_precio_ultimo_mes_%',
     'es_ean', 'en_maestro', 'puntaje', 'ranking']]

criterios = pd.DataFrame(embudo, columns=['regla', 'productos_que_quedan'])
criterios.loc[-1] = ['0. Productos del SEPA con algún precio desde 2022 (nb09)', len(R)]
criterios = criterios.sort_index().reset_index(drop=True)

notas = pd.DataFrame({'nota': [
    f'Canasta fija para pass-through diario, {DESDE:%d/%m/%Y} a {HASTA:%d/%m/%Y}: {len(C)} productos, los mismos todos los días.',
    'Fuente: salidas del nb09 (trazabilidad de todos los productos del SEPA, corrida con datos al 22/10/2026) y la hoja Dias.',
    'Reglas: hoja Criterios (se aplican en orden; la columna motivo_exclusion de Candidatos dice en cuál cae cada producto).',
    'La cobertura se mide con el promedio de sucursales por día de cada mes y no con el peor día: el SEPA tiene días con '
    'la mitad de los comercios (16 al 28/07/2023, ver Dias_incompletos) en los que cualquier producto queda con pocas sucursales.',
    'Fideos y arroz de Molinos, azúcar Ledesma y otros básicos tienen precio todos los días pero su cobertura se desploma '
    'entre dic-2023 y abr-2024 (de ~1.500 a 10-200 sucursales), justo en la devaluación: quedan afuera por la regla 5 '
    '(hoja Basicos_excluidos). Para un análisis de sensibilidad se pueden sumar sabiendo eso.',
    'Variable de precio recomendada: para cada producto y día, el precio de las MISMAS sucursales el día anterior y el '
    'actual (índice encadenado de sucursales apareadas, media geométrica de los relativos). La mediana nacional del nb08 '
    'sirve para empezar, pero se mueve cuando cambian las sucursales que informan (16-28/07/2023; 8 comercios menos desde '
    'el 01/08/2026; Libertad deja de publicar el 02/09/2026).',
    'Días con cobertura incompleta (hoja Dias_incompletos) y los 2 días sin dato del SEPA: tratarlos como faltantes o '
    'encadenar a través de ellos con sucursales apareadas.',
    'Desagregación: grupo_ipc (18 grupos del IPC), tipo (6), rubro y categoría del maestro, perecedero, origen_gs1 '
    '(país donde se registró el código: proxy débil de importado; Nestlé usa códigos suizos para productos hechos en el '
    'país) y proveedor (empresa).',
    'Pesos: peso_ipc_% = ponderación nacional del IPC (INDEC) del grupo, repartida entre los grupos presentes y en partes '
    'iguales entre los productos del grupo. Ojo: los grupos de carnes, verduras y frutas del IPC son sobre todo frescos, '
    'y acá están representados por envasados (fiambres, hamburguesas, conservas). Alternativa: peso_igual_grupo_%. Para '
    'estimar el pass-through conviene trabajar producto por producto (panel) y usar los pesos solo para agregar.',
    'cantidad_08: cantidades que hacen que la canasta valga $1.000.000 a precios medianos de oct-2026 con los pesos IPC. '
    "Para correr el nb08: CANASTA_EXCEL = este archivo, CANASTA_COL = 'cantidad_08' (devuelve la mediana diaria por "
    'producto en Precios_diarios). Con muchos productos conviene correrlo por grupos para no pasarse de RAM.',
]})

with pd.ExcelWriter(F_OUT, engine='xlsxwriter') as xw:
    hojas = [('Selección', sel), ('Grupos_IPC', grupos), ('Resumen', resumen), ('Criterios', criterios),
             ('Basicos_excluidos', ex), ('Dias_incompletos', inc), ('Candidatos', cand), ('Notas', notas)]
    for nombre, df in hojas:
        df.to_excel(xw, sheet_name=nombre, index=False)
        ws = xw.sheets[nombre]
        hdr = xw.book.add_format({'bold': True, 'font_color': 'white', 'bg_color': '#375623', 'text_wrap': True,
                                  'valign': 'vcenter'})
        for j, c in enumerate(df.columns):
            ws.write(0, j, c, hdr)
            ancho = 60 if c in ('descripcion', 'motivo_exclusion', 'regla', 'nota', 'grupo_ipc') else 14
            ws.set_column(j, j, 120 if nombre == 'Notas' else ancho)
        ws.freeze_panes(1, 2 if nombre in ('Selección', 'Candidatos', 'Basicos_excluidos') else 0)
        if len(df) > 1 and nombre != 'Notas':
            ws.autofilter(0, 0, len(df), len(df.columns) - 1)

print('\n'.join(f'{n:110s} {k:7,}' for n, k in embudo))
print(f'\nCanasta: {len(C)} productos | grupos IPC {C["grupo_ipc_cod"].nunique()} | tipos {C["tipo"].value_counts().to_dict()}')
print(f'Días con cobertura incompleta: {len(inc)} | días sin dato: {[d.strftime("%d/%m/%Y") for d in sin_dato]}')
print(f'Salida: {F_OUT}')
