# PROTOTIPO (2026-10-15): la lógica que se portó a la CELDA 19b del nb02. Se guarda como referencia.
# Uso: python prototipo_desagregar_variacion_canasta.py <canasta_analisis_AAAA-MM.xlsx> <obs_sep_oct.parquet> <maestro_sucursales_completo.xlsx> <salida.xlsx>
# El parquet sale de extraer_obs_sepa.py (sucursal x EAN x dia de los dos meses, desde el zip semestral del SEPA).
# Desagregacion de la variacion mensual de la canasta Media del nb02 (sep-26 -> oct-26 al 15/10).
#
# Serie oficial del nb02 (CELDA 9): canasta(m) = sum_i qty_i * mediana_i(m), con la mediana sobre TODAS
# las observaciones (sucursal x dia) del mes, sin filtros de cadena ni de geografia.
#   1) Por producto: aporte_i = qty_i * (med_i,oct - med_i,sep) / canasta_sep -> suma EXACTA al 1,75.
#   2) Por cadena / provincia / region / tipo: la mediana no se reparte entre grupos. Se usa el panel
#      apareado sucursal x producto con el mismo precio mensual por sucursal del nb02 (CELDA 7: mediana de
#      los dias) y los pesos oficiales de septiembre:
#        aporte_(s,i) = w_i * (p_is,oct - p_is,sep) / sum_s p_is,sep      (w_i = qty_i*med_i,sep / canasta_sep)
#      Sumado sobre s da la variacion "media de sucursales" del producto i; sumado sobre todo, la del panel.
#      Es aditivo en cualquier corte. La diferencia contra el 1,75 = efecto mediana + composicion.
import sys, numpy as np, pandas as pd

XLS, OBS, MAESTRO, OUT = sys.argv[1:5]
CANASTA = 'Media'
SEP, OCT = '202609', '202610'

ISO = {'AR-B': 'Buenos Aires', 'AR-C': 'CABA', 'AR-K': 'Catamarca', 'AR-H': 'Chaco', 'AR-U': 'Chubut',
       'AR-X': 'Córdoba', 'AR-W': 'Corrientes', 'AR-E': 'Entre Ríos', 'AR-P': 'Formosa', 'AR-Y': 'Jujuy',
       'AR-L': 'La Pampa', 'AR-F': 'La Rioja', 'AR-M': 'Mendoza', 'AR-N': 'Misiones', 'AR-Q': 'Neuquén',
       'AR-R': 'Río Negro', 'AR-A': 'Salta', 'AR-J': 'San Juan', 'AR-D': 'San Luis', 'AR-Z': 'Santa Cruz',
       'AR-S': 'Santa Fe', 'AR-G': 'Santiago del Estero', 'AR-V': 'Tierra del Fuego', 'AR-T': 'Tucumán'}
REG_PROV = {'CABA': 'AMBA', 'Córdoba': 'Pampeana', 'Entre Ríos': 'Pampeana', 'La Pampa': 'Pampeana',
            'Santa Fe': 'Pampeana', 'Catamarca': 'Noroeste', 'Jujuy': 'Noroeste', 'La Rioja': 'Noroeste',
            'Salta': 'Noroeste', 'Santiago del Estero': 'Noroeste', 'Tucumán': 'Noroeste', 'Chaco': 'Noreste',
            'Corrientes': 'Noreste', 'Formosa': 'Noreste', 'Misiones': 'Noreste', 'Mendoza': 'Cuyo',
            'San Juan': 'Cuyo', 'San Luis': 'Cuyo', 'Chubut': 'Patagonia', 'Neuquén': 'Patagonia',
            'Río Negro': 'Patagonia', 'Santa Cruz': 'Patagonia', 'Tierra del Fuego': 'Patagonia'}
# Mismos nombres que asignar_cadena del nb02 (CELDA 4)
NOMBRES_COMPUESTOS = {('9', '1'): 'Vea', ('9', '2'): 'Disco', ('9', '3'): 'Jumbo',
                      ('10', '1'): 'Carrefour', ('10', '2'): 'Carrefour Market', ('10', '3'): 'Carrefour Express',
                      ('11', '2'): 'ChangoMas', ('11', '4'): 'Hiper ChangoMas', ('11', '5'): 'Mi ChangoMas',
                      ('16', '1'): 'Hipermercado Libertad', ('16', '2'): 'Mini Libertad'}
NOMBRES_SIMPLES = {'2': 'La Anonima', '3': 'Cadena 3', '5': 'Hipermercado Misiones', '8': 'Cadena 8 (Cordoba)',
                   '12': 'Coto', '13': 'Cooperativa Obrera', '15': 'DIA', '20': 'LAR', '21': 'Toledo',
                   '23': 'Cadena 23', '47': 'Pasamonte'}
MACRO = {
    'Alimentos': ['Lácteos', 'Fiambrería', 'Carnicería', 'Hamburguesas', 'Galletitas', 'Conservas',
                  'Papas Congeladas', 'Aceites', 'Alimentos Congelados', 'Golosinas', 'Harinas', 'Infusiones',
                  'Arroz y Legumbres', 'Azúcar y Edulcorantes', 'Aderezos', 'Cereales', 'Pastas Secas',
                  'Vegetales', 'Sopas Caldos y Puré', 'Snacks'],
    'Bebidas': ['Gaseosas', 'Vinos y Espumantes', 'Isotónicas y Energizantes', 'Bebida Herbal', 'Cerveza',
                'Jugos', 'Aguas'],
    'Limpieza y papeles': ['Lavandina', 'Desodorante de Ambientes', 'Limpieza de Baño', 'Papeles',
                           'Limpieza de Ropa', 'Limpieza de Cocina', 'Limpieza Piso y Muebles',
                           'Accesorios de Limpieza'],
    'Higiene y cuidado personal': ['Cuidado Corporal', 'Cuidado del Cabello', 'Protección Femenina',
                                   'Cuidado Oral', 'Productos Farmacéuticos'],
}
CAT2MACRO = {c: g for g, cs in MACRO.items() for c in cs}


def cadena(com, ban):
    if (com, ban) in NOMBRES_COMPUESTOS: return NOMBRES_COMPUESTOS[(com, ban)]
    if com == '10': return f'Carrefour (bandera {ban})'
    if com in NOMBRES_SIMPLES: return NOMBRES_SIMPLES[com]
    return f'Cadena {com}'


# ── Canasta oficial (hoja Serie_precios del nb02) ─────────────────────────────
sp = pd.read_excel(XLS, sheet_name='Serie_precios', dtype={'id_producto': str})
b = sp[sp['canasta_name'] == CANASTA]
s9 = b[b['mes'] == '2026-09'].set_index('id_producto')
s10 = b[b['mes'] == '2026-10'].set_index('id_producto')
prod = s9[['descripcion', 'categoria', 'qty', 'precio_mediano', 'costo_item']].rename(
    columns={'precio_mediano': 'med_sep', 'costo_item': 'costo_sep'})
prod = prod.join(s10[['precio_mediano', 'costo_item']].rename(
    columns={'precio_mediano': 'med_oct', 'costo_item': 'costo_oct'}), how='outer')
assert prod.notna().all().all(), 'hay productos sin precio en uno de los meses'
prod['ean'] = prod.index.str.lstrip('0')
prod['grupo'] = prod['categoria'].map(CAT2MACRO)
assert prod['grupo'].notna().all(), prod.loc[prod['grupo'].isna(), 'categoria'].unique()
T9, T10 = prod['costo_sep'].sum(), prod['costo_oct'].sum()
V_OF = (T10 / T9 - 1) * 100
prod['w'] = prod['costo_sep'] / T9
prod['peso_%'] = prod['w'] * 100
prod['var_mediana_%'] = (prod['med_oct'] / prod['med_sep'] - 1) * 100
prod['aporte_oficial_pp'] = (prod['costo_oct'] - prod['costo_sep']) / T9 * 100
print(f'Oficial: {T9:,.0f} -> {T10:,.0f} = {V_OF:+.4f}%  (suma aportes {prod["aporte_oficial_pp"].sum():.4f})')

# ── Observaciones sucursal x dia ─────────────────────────────────────────────
obs = pd.read_parquet(OBS)
for c in ['id_comercio', 'id_bandera', 'id_sucursal', 'sucursales_provincia', 'ean', 'dia']:
    obs[c] = obs[c].astype(str)
obs = obs[obs['ean'].isin(set(prod['ean']))].copy()
obs['mes'] = obs['dia'].str[:6]
assert obs['precio'].median() < 10_000  # ya en pesos (el nb02 divide por 100 si no)
obs['suc'] = obs['id_comercio'] + '-' + obs['id_bandera'] + '-' + obs['id_sucursal']
ean2id = dict(zip(prod['ean'], prod.index))
obs['id_producto'] = obs['ean'].map(ean2id)

# Reproducir la mediana nacional del nb02
med = obs.groupby(['mes', 'id_producto'])['precio'].median().unstack(0)
chk = pd.DataFrame({'sep_rep': med[SEP], 'sep_nb02': prod['med_sep'], 'oct_rep': med[OCT], 'oct_nb02': prod['med_oct']})
dif = ((chk['sep_rep'] - chk['sep_nb02']).abs() > 0.5) | ((chk['oct_rep'] - chk['oct_nb02']).abs() > 0.5)
print(f'Medianas reproducidas: {(~dif).sum()}/{len(chk)} productos iguales')
if dif.any(): print(chk[dif].to_string())
T9r = (prod['qty'] * chk['sep_rep']).sum(); T10r = (prod['qty'] * chk['oct_rep']).sum()
print(f'Reproducido: {T9r:,.0f} -> {T10r:,.0f} = {(T10r / T9r - 1) * 100:+.4f}%')

# ── Atributos de sucursal ─────────────────────────────────────────────────────
ms = pd.read_excel(MAESTRO, dtype={'id_comercio': str, 'id_bandera': str, 'id_sucursal': str})
ms['suc'] = ms['id_comercio'] + '-' + ms['id_bandera'] + '-' + ms['id_sucursal']
ms = ms.drop_duplicates('suc').set_index('suc')
suc = obs.groupby('suc')[['id_comercio', 'id_bandera', 'sucursales_provincia']].first()
suc['cadena'] = [cadena(c, b_) for c, b_ in zip(suc['id_comercio'], suc['id_bandera'])]
suc['provincia'] = suc['sucursales_provincia'].map(ISO).fillna('Sin dato')
reg_m = ms['REGION'].astype(str).str.replace('\xa0', '').str.strip()
suc['region'] = suc.index.map(reg_m)
# Sin maestro: region por provincia (Buenos Aires sin coordenadas no se puede partir AMBA/Pampeana)
falta = suc['region'].isna() | suc['region'].isin(['nan', ''])
suc.loc[falta, 'region'] = suc.loc[falta, 'provincia'].map(REG_PROV).fillna('Buenos Aires s/ubicar')
tipo = ms['sucursales_tipo'].astype(str).str.strip().str.title().replace(
    {'Tienda Fisica': 'Tienda física', 'Web': 'Web/virtual', 'Tienda Virtual': 'Web/virtual'})
suc['tipo'] = suc.index.map(tipo).fillna('Sin dato en maestro')
suc['en_maestro'] = suc.index.isin(ms.index)
print(f'Sucursales con dato: {len(suc):,} | en maestro: {suc["en_maestro"].sum():,}')

# ── Precio mensual por sucursal-producto (mediana de los dias, como CELDA 7) ──
p = obs.groupby(['suc', 'id_producto', 'mes'])['precio'].median().unstack('mes')
p.columns = ['p_sep', 'p_oct']
n_tot = len(p)
p = p.dropna()
r = p['p_oct'] / p['p_sep']
fuera = (r < 0.25) | (r > 4)
print(f'Pares sucursal-producto: {n_tot:,} | apareados: {len(p):,} | fuera de banda [1/4,4]: {fuera.sum()}')
p = p[~fuera].reset_index()
p = p.merge(prod[['w', 'qty', 'descripcion', 'categoria', 'grupo']], left_on='id_producto', right_index=True)
p = p.merge(suc[['cadena', 'provincia', 'region', 'tipo']], left_on='suc', right_index=True)
S_sep = p.groupby('id_producto')['p_sep'].transform('sum')
p['peso_par'] = p['w'] * p['p_sep'] / S_sep * 100               # suma 100 sobre el panel
p['aporte_pp'] = p['w'] * (p['p_oct'] - p['p_sep']) / S_sep * 100
p['cambio'] = np.select([p['p_oct'] > p['p_sep'], p['p_oct'] < p['p_sep']], ['sube', 'baja'], 'igual')
V_PAN = p['aporte_pp'].sum()
print(f'Panel apareado (media de sucursales, pesos oficiales): {V_PAN:+.4f}%')


# ── Variacion por grupo con el metodo oficial (mediana de las observaciones del grupo) ──
def var_mediana(col):
    o = obs.merge(suc[[col]], left_on='suc', right_index=True)
    mg = o.groupby([col, 'id_producto', 'mes'])['precio'].median().unstack('mes').dropna()
    mg = mg.join(prod['qty'], on='id_producto')
    g = mg.groupby(level=0).apply(lambda d: pd.Series({
        'var_mediana_grupo_%': ((d['qty'] * d[OCT]).sum() / (d['qty'] * d[SEP]).sum() - 1) * 100,
        'productos_apareados': len(d)}))
    return g


def corte(col):
    g = p.groupby(col).agg(sucursales=('suc', 'nunique'), pares=('suc', 'size'),
                           peso_base_pct=('peso_par', 'sum'), aporte_pp=('aporte_pp', 'sum'))
    g['variacion_%'] = g['aporte_pp'] / g['peso_base_pct'] * 100
    g['pct_del_aumento'] = g['aporte_pp'] / V_PAN * 100
    g['aporte_equiv_sobre_oficial_pp'] = g['pct_del_aumento'] / 100 * V_OF
    sub = p.assign(sube=p['cambio'].eq('sube'), baja=p['cambio'].eq('baja'))
    g['pct_precios_suben'] = sub.groupby(col)['sube'].mean() * 100
    g['pct_precios_bajan'] = sub.groupby(col)['baja'].mean() * 100
    g = g.join(var_mediana(col))
    g = g.sort_values('aporte_pp', ascending=False)
    tot = pd.DataFrame([{'sucursales': p['suc'].nunique(), 'pares': len(p), 'peso_base_pct': 100.0,
                         'aporte_pp': V_PAN, 'variacion_%': V_PAN, 'pct_del_aumento': 100.0,
                         'aporte_equiv_sobre_oficial_pp': V_OF,
                         'pct_precios_suben': p['cambio'].eq('sube').mean() * 100,
                         'pct_precios_bajan': p['cambio'].eq('baja').mean() * 100,
                         'var_mediana_grupo_%': V_OF, 'productos_apareados': len(prod)}], index=['TOTAL'])
    return pd.concat([g, tot]).rename_axis(col).reset_index()


cortes = {c: corte(c) for c in ['cadena', 'provincia', 'region', 'tipo']}
for c, t in cortes.items():
    print(f'\n== {c} ==')
    print(t.head(12).round(3).to_string(index=False))

# ── Productos: oficial + panel ────────────────────────────────────────────────
pp_ = p.groupby('id_producto').agg(sucursales_apareadas=('suc', 'size'), aporte_panel_pp=('aporte_pp', 'sum'),
                                   pct_suben=('cambio', lambda s: (s == 'sube').mean() * 100),
                                   pct_bajan=('cambio', lambda s: (s == 'baja').mean() * 100))
prod = prod.join(pp_)
prod['var_media_sucursales_%'] = prod['aporte_panel_pp'] / prod['peso_%'] * 100
prod['pct_del_aumento_oficial'] = prod['aporte_oficial_pp'] / V_OF * 100
prod = prod.sort_values('aporte_oficial_pp', ascending=False)

rub = prod.groupby(['grupo', 'categoria']).agg(productos=('qty', 'size'), peso_pct=('peso_%', 'sum'),
                                                aporte_oficial_pp=('aporte_oficial_pp', 'sum'),
                                                aporte_panel_pp=('aporte_panel_pp', 'sum')).reset_index()
rub['variacion_mediana_%'] = rub['aporte_oficial_pp'] / rub['peso_pct'] * 100
rub['pct_del_aumento'] = rub['aporte_oficial_pp'] / V_OF * 100
rub = rub.sort_values('aporte_oficial_pp', ascending=False)
gru = prod.groupby('grupo').agg(productos=('qty', 'size'), peso_pct=('peso_%', 'sum'),
                                aporte_oficial_pp=('aporte_oficial_pp', 'sum'),
                                aporte_panel_pp=('aporte_panel_pp', 'sum')).reset_index()
gru['variacion_mediana_%'] = gru['aporte_oficial_pp'] / gru['peso_pct'] * 100
gru['variacion_panel_%'] = gru['aporte_panel_pp'] / gru['peso_pct'] * 100
gru['pct_del_aumento'] = gru['aporte_oficial_pp'] / V_OF * 100
gru = gru.sort_values('aporte_oficial_pp', ascending=False)
print('\n== Grandes grupos ==\n', gru.round(3).to_string(index=False))

# ── Producto x cadena (aporte panel, pp) ──────────────────────────────────────
top_cad = cortes['cadena'].query('cadena != "TOTAL"').head(12)['cadena'].tolist()
pxc = p.assign(cad=np.where(p['cadena'].isin(top_cad), p['cadena'], 'Resto')).pivot_table(
    index='id_producto', columns='cad', values='aporte_pp', aggfunc='sum', fill_value=0)
pxc = pxc[[c for c in top_cad + ['Resto'] if c in pxc.columns]]
pxc['TOTAL'] = pxc.sum(axis=1)
pxc = prod[['descripcion']].join(pxc).sort_values('TOTAL', ascending=False)

# Variacion de precio (media de sucursales) por producto x cadena
vxc = p.assign(cad=np.where(p['cadena'].isin(top_cad), p['cadena'], 'Resto')).groupby(['id_producto', 'cad'])[['p_sep', 'p_oct']].sum().pipe(
    lambda d: (d['p_oct'] / d['p_sep'] - 1) * 100).unstack()
vxc = vxc[[c for c in top_cad + ['Resto'] if c in vxc.columns]]
vxc = prod[['descripcion', 'var_mediana_%']].join(vxc).loc[pxc.index]

# ── Frecuencia e intensidad de los cambios ────────────────────────────────────
fr = p.groupby('cambio').agg(pares=('suc', 'size'), peso_base_pct=('peso_par', 'sum'), aporte_pp=('aporte_pp', 'sum'))
fr['pct_pares'] = fr['pares'] / len(p) * 100
_rel = (p['p_oct'] / p['p_sep'] - 1) * 100
fr['cambio_medio_%'] = _rel.groupby(p['cambio']).mean()
fr['cambio_mediano_%'] = _rel.groupby(p['cambio']).median()
fr = fr.reindex(['sube', 'igual', 'baja']).reset_index()
print('\n== Frecuencia ==\n', fr.round(3).to_string(index=False))


# ── Ventanas: el mes parcial ─────────────────────────────────────────────────
def canasta_vent(d0, d1):
    o = obs[(obs['dia'] >= d0) & (obs['dia'] <= d1)]
    m = o.groupby('id_producto')['precio'].median()
    return (prod['qty'] * m).sum(), m.notna().sum()


vent = []
for nom, a, b_ in [('Sep completo (1-30) vs Oct 1-15  [oficial nb02]', ('20260901', '20260930'), ('20261001', '20261015')),
                   ('Sep 1-15 vs Oct 1-15  [mismos dias, un mes]', ('20260901', '20260915'), ('20261001', '20261015')),
                   ('Sep 16-30 vs Oct 1-15  [quincenas consecutivas]', ('20260916', '20260930'), ('20261001', '20261015')),
                   ('Sep 1-15 vs Sep 16-30  [dentro de septiembre]', ('20260901', '20260915'), ('20260916', '20260930'))]:
    (c0, n0), (c1, n1) = canasta_vent(*a), canasta_vent(*b_)
    vent.append({'comparacion': nom, 'canasta_inicio': c0, 'canasta_fin': c1, 'variacion_%': (c1 / c0 - 1) * 100,
                 'productos': min(n0, n1)})
vent = pd.DataFrame(vent)
print('\n== Ventanas ==\n', vent.round(3).to_string(index=False))

# Arrastre: cuanto del aumento ya estaba en los precios de la ultima semana de septiembre.
# Identidad exacta: (oct - sep)/sep = (cierre - sep)/sep + (oct - cierre)/sep, producto a producto.
CIERRE = ('20260924', '20260930')
med_cierre = obs[(obs['dia'] >= CIERRE[0]) & (obs['dia'] <= CIERRE[1])].groupby('id_producto')['precio'].median()
prod['med_cierre_sep'] = med_cierre
prod['arrastre_pp'] = prod['qty'] * (prod['med_cierre_sep'] - prod['med_sep']) / T9 * 100
prod['nuevo_oct_pp'] = prod['qty'] * (prod['med_oct'] - prod['med_cierre_sep']) / T9 * 100
T_CIE = (prod['qty'] * prod['med_cierre_sep']).sum()
ARR, NUE = prod['arrastre_pp'].sum(), prod['nuevo_oct_pp'].sum()
vent = pd.concat([vent, pd.DataFrame([
    {'comparacion': 'Arrastre: Sep completo vs ultima semana de Sep (24-30)', 'canasta_inicio': T9,
     'canasta_fin': T_CIE, 'variacion_%': ARR, 'productos': len(prod)},
    {'comparacion': 'Suba nueva: ultima semana de Sep (24-30) vs Oct 1-15, en pp sobre la canasta de Sep',
     'canasta_inicio': T_CIE, 'canasta_fin': T10, 'variacion_%': NUE, 'productos': len(prod)}])], ignore_index=True)
print(f'Arrastre {ARR:+.3f} pp + nuevo {NUE:+.3f} pp = {ARR + NUE:+.3f}')
gru = gru.merge(prod.groupby('grupo')[['arrastre_pp', 'nuevo_oct_pp']].sum(), left_on='grupo', right_index=True)
rub = rub.merge(prod.groupby('categoria')[['arrastre_pp', 'nuevo_oct_pp']].sum(), left_on='categoria', right_index=True)
print(gru[['grupo', 'aporte_oficial_pp', 'arrastre_pp', 'nuevo_oct_pp']].round(3).to_string(index=False))

# Serie diaria con el metodo oficial (mediana nacional del dia)
dd = obs.groupby(['dia', 'id_producto'])['precio'].median().unstack()
diaria = pd.DataFrame({'canasta': (dd * prod['qty']).sum(axis=1), 'productos_con_dato': dd.notna().sum(axis=1),
                       'observaciones': obs.groupby('dia').size()})
diaria['indice_sep_completo=100'] = diaria['canasta'] / T9 * 100
diaria = diaria.reset_index()
diaria['dia'] = pd.to_datetime(diaria['dia'])

# ── Resumen ───────────────────────────────────────────────────────────────────
top_up = prod.head(5)
res = [
    ('Canasta Media sep-26 (nb02)', T9), ('Canasta Media oct-26 al 15/10 (nb02)', T10),
    ('Variacion oficial nb02 (%)', V_OF),
    ('Variacion panel apareado, media de sucursales, pesos oficiales (%)', V_PAN),
    ('Diferencia oficial - panel (efecto mediana / composicion, pp)', V_OF - V_PAN),
    ('Arrastre: suba ya presente en la ultima semana de septiembre (pp)', ARR),
    ('Suba nueva entre fin de septiembre y oct 1-15 (pp)', NUE),
    ('Aporte en el panel de los productos con mediana sin cambio (pp)',
     prod.loc[prod['var_mediana_%'] == 0, 'aporte_panel_pp'].sum()),
    ('Productos en la canasta', len(prod)),
    ('Productos con mediana sin cambio', int((prod['var_mediana_%'] == 0).sum())),
    ('Productos con mediana en baja', int((prod['var_mediana_%'] < 0).sum())),
    ('Aporte de los 5 productos que mas suman (pp)', top_up['aporte_oficial_pp'].sum()),
    ('Aporte de los 10 productos que mas suman (pp)', prod.head(10)['aporte_oficial_pp'].sum()),
    ('Sucursales en el panel', p['suc'].nunique()),
    ('Pares sucursal-producto apareados', len(p)),
    ('Pares descartados por banda [1/4, 4]', int(fuera.sum())),
    ('% de precios (sucursal-producto) que subieron', p['cambio'].eq('sube').mean() * 100),
    ('% de precios que bajaron', p['cambio'].eq('baja').mean() * 100),
    ('% de precios sin cambio', p['cambio'].eq('igual').mean() * 100),
]
resumen = pd.DataFrame(res, columns=['indicador', 'valor'])
notas = pd.DataFrame({'nota': [
    'Fuente: canasta_analisis_2026-10.xlsx (hoja Serie_precios, canasta Media = cantidad_03) y 2026B.zip (SEPA sep-26 y oct-26 al 15/10).',
    'Variacion oficial: la del nb02 (CELDA 9): suma de qty x mediana nacional de todas las observaciones sucursal x dia del mes. Octubre es PARCIAL (1-15).',
    'Productos y rubros: aporte_oficial_pp = qty x (mediana oct - mediana sep) / canasta sep. Suma exacta a la variacion oficial.',
    'Cadenas, provincias, regiones y tipo: la mediana nacional no se puede repartir entre grupos. Se usa el panel apareado sucursal x producto '
    '(precio mensual por sucursal = mediana de los dias, como la CELDA 7 del nb02), con los pesos oficiales de septiembre por producto. '
    'aporte = w_producto x (p_oct - p_sep) / suma de p_sep del producto en todas las sucursales. Es aditivo: los grupos suman la variacion del panel.',
    'pct_del_aumento = aporte del grupo / variacion del panel. aporte_equiv_sobre_oficial_pp reparte el 1,75 oficial con esas proporciones.',
    'peso_base_pct = participacion del grupo en el costo base (cuanto pesan sus sucursales). variacion_% = aporte / peso: cuanto subio la canasta en ese grupo.',
    'var_mediana_grupo_% = el metodo oficial aplicado solo a las observaciones del grupo (productos con dato en ambos meses). No es aditivo, sirve de control.',
    'Las sucursales pesan por igual dentro de cada producto (como la mediana nacional, que pesa por cantidad de observaciones): las cadenas con muchas sucursales pesan mas.',
    'Arrastre: la mediana de septiembre es un promedio del mes; si los precios subieron en la segunda quincena, octubre arranca '
    'mas arriba aunque no haya subas nuevas. arrastre_pp = qty x (mediana ultima semana de sep - mediana sep) / canasta sep; '
    'nuevo_oct_pp = qty x (mediana oct 1-15 - mediana ultima semana de sep) / canasta sep. Suman el aporte oficial producto a producto.',
    'Region: la del maestro de sucursales (AMBA incluye el conurbano). Sucursales fuera del maestro: region por provincia.',
]})

with pd.ExcelWriter(OUT, engine='openpyxl') as w:
    resumen.to_excel(w, sheet_name='Resumen', index=False)
    notas.to_excel(w, sheet_name='Resumen', index=False, startrow=len(resumen) + 2)
    cols = ['descripcion', 'grupo', 'categoria', 'qty', 'med_sep', 'med_oct', 'var_mediana_%', 'peso_%',
            'aporte_oficial_pp', 'pct_del_aumento_oficial', 'med_cierre_sep', 'arrastre_pp', 'nuevo_oct_pp', 'sucursales_apareadas', 'pct_suben', 'pct_bajan',
            'var_media_sucursales_%', 'aporte_panel_pp']
    prod[cols].rename_axis('id_producto').reset_index().to_excel(w, sheet_name='Productos', index=False)
    gru.to_excel(w, sheet_name='Grupos', index=False)
    rub.to_excel(w, sheet_name='Rubros', index=False)
    cortes['cadena'].to_excel(w, sheet_name='Cadenas', index=False)
    cortes['provincia'].to_excel(w, sheet_name='Provincias', index=False)
    cortes['region'].to_excel(w, sheet_name='Regiones', index=False)
    cortes['tipo'].to_excel(w, sheet_name='Tipo_sucursal', index=False)
    pxc.rename_axis('id_producto').reset_index().to_excel(w, sheet_name='Aporte_prod_x_cadena', index=False)
    vxc.rename_axis('id_producto').reset_index().to_excel(w, sheet_name='Var_prod_x_cadena', index=False)
    fr.to_excel(w, sheet_name='Subas_y_bajas', index=False)
    vent.to_excel(w, sheet_name='Mes_parcial', index=False)
    diaria.to_excel(w, sheet_name='Serie_diaria', index=False)

# Formato: anchos y numeros
from openpyxl import load_workbook
wb = load_workbook(OUT)
for ws in wb.worksheets:
    ws.freeze_panes = 'B2' if ws.title not in ('Resumen',) else None
    for col in ws.columns:
        head = str(col[0].value or '')
        ancho = min(max(len(head), *(len(f'{c.value:.2f}') if isinstance(c.value, float) else len(str(c.value or '')) for c in col[1:60])) + 2, 60)
        ws.column_dimensions[col[0].column_letter].width = ancho
        for c in col[1:]:
            if isinstance(c.value, float):
                c.number_format = '#,##0' if abs(c.value) >= 1000 else '0.000'
wb['Resumen'].column_dimensions['A'].width = 70
wb.save(OUT)
print('\nExcel ->', OUT)
