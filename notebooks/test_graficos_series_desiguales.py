# -*- coding: utf-8 -*-
"""Test de regresion de la CELDA 12 (graficos) y del bloque de tiles de la CELDA 17.

Corre las celdas REALES del notebook generado (`05_evolucion_productos_representativos.ipynb`)
contra un df sintetico donde los productos NO comparten el mismo arranque de serie.

  BUG-29 — el grafico de barras usaba el eje temporal del primer producto para TODAS las
           series. Con un producto que aparece despues (18 meses contra 32) reventaba con
           "ValueError: shape mismatch ... (32,) vs (18,)". Caso real: Cerveza Liviana
           Golden Porron Imperial 330 Ml, que arranca en 2025-03 (corrida de agosto 2026).
  BUG-30 — CartoDB pasó a devolver los tiles con la marca de agua "API key required".
           El fondo del mapa Folium ahora se elige con TILES_MAPA y por default es OSM.

Uso:  python notebooks/test_graficos_series_desiguales.py
"""
import json, pathlib, re, tempfile, textwrap

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

NB_PATH = pathlib.Path(__file__).with_name('05_evolucion_productos_representativos.ipynb')
OUTPUT_DIR = pathlib.Path(tempfile.mkdtemp(prefix='test_nb05_'))


def _celdas(nb_path):
    nb = json.load(open(nb_path, encoding='utf-8'))
    return [''.join(c['source']) for c in nb['cells'] if c['cell_type'] == 'code']


def _mkdf(mes_ini, n):
    mes = pd.period_range(mes_ini, periods=n, freq='M').astype(str)
    rng = np.random.default_rng(n)
    var = rng.normal(2.0, 1.5, n)
    var[0] = np.nan
    precio = 1000 * np.cumprod(1 + np.nan_to_num(var) / 100)
    d = pd.DataFrame({'mes': mes, 'fecha': pd.to_datetime(mes + '-01')})
    d['precio_nacional_ponderado'] = precio
    d['precio_nacional_ponderado_prom'] = precio * 1.01
    d['idx_producto_base'] = precio / precio[0] * 100
    d['idx_producto_base_prom'] = d['idx_producto_base'] * 1.002
    d['variacion_mensual_%'] = var
    d['variacion_mensual_prom_%'] = var * 1.05
    d['ipc_general'] = np.linspace(5000, 12000, n)
    d['ipc_alimentos'] = np.linspace(5200, 12900, n)
    d['idx_ipc_general_base'] = d['ipc_general'] / d['ipc_general'].iloc[0] * 100
    d['idx_ipc_alimentos_base'] = d['ipc_alimentos'] / d['ipc_alimentos'].iloc[0] * 100
    d['ipc_general_var_%'] = d['ipc_general'].pct_change() * 100
    d['ipc_alimentos_var_%'] = d['ipc_alimentos'].pct_change() * 100
    return d


def test_celda12_series_desiguales(celda12):
    """p03 arranca 14 meses despues que el resto: no tiene que romper ni desalinearse."""
    df_g_dict = {'p01': _mkdf('2024-01', 32), 'p02': _mkdf('2024-01', 32),
                 'p03': _mkdf('2025-03', 18)}
    env = {
        'plt': plt, 'mdates': mdates, 'mticker': mticker, 'pd': pd, 'np': np,
        'df_g_dict': df_g_dict,
        'PRODUCTOS_ACTIVOS': ['p01', 'p02', 'p03'],
        '_serie_vacia_dict': {p: False for p in df_g_dict},
        '_lbl_base_dict': {'p01': '01-24', 'p02': '01-24', 'p03': '03-25'},
        'PRODUCTO_NOMBRES': {'p01': 'Cerveza Imperial Lager 473',
                             'p02': 'Cerveza Schneider 473',
                             'p03': 'Cerveza Golden Porron 330'},
        'PRODUCTO_COLORS': {'p01': '#1f77b4', 'p02': '#ff7f0e', 'p03': '#2ca02c'},
        'PRODUCTO_LINESTYLES': {p: '-' for p in df_g_dict},
        'PRODUCTO_MARKERS': {p: 'o' for p in df_g_dict},
        'prom_nac_dict': {'p01': 3105.0, 'p02': 2594.0, 'p03': 3504.0},
        'prom_nac_prom_dict': {'p01': 3136.0, 'p02': 2620.0, 'p03': 3539.0},
        'MES': '082026', 'NOMBRE_MES_TITLE': 'Agosto 2026', 'SUFIJO_PARCIAL': '',
        'MES_PARCIAL': False, 'DIAS_CARGADOS': 31, 'DIAS_MES': 31,
        'OUTPUT_DIR': OUTPUT_DIR,
    }
    exec(compile(celda12, '<CELDA 12>', 'exec'), env)   # sin el fix: ValueError

    esperados = ['indices_productos_vs_ipc_082026.png',
                 'variaciones_productos_vs_ipc_082026.png',
                 'ranking_productos_082026.png',
                 'indices_productos_vs_ipc_082026_prom.png',
                 'variaciones_productos_vs_ipc_082026_prom.png',
                 'ranking_productos_082026_prom.png']
    faltan = [f for f in esperados if not (OUTPUT_DIR / f).exists()]
    assert not faltan, f'faltan PNG: {faltan}'

    # el producto que arranca despues tiene su indice en base a SU primer mes:
    # la leyenda lo tiene que aclarar (y solo para ese)
    labels = [t.get_text() for t in plt.figure(1).axes[0].get_legend().get_texts()]
    con_base = [l for l in labels if '(base' in l]
    assert con_base == ['Cerveza Golden Porron 330 (base 03-25)'], con_base

    # y sus barras tienen que caer en SU rango de fechas, no en el del producto largo
    ax2 = plt.figure(2).axes[0]
    xs = sorted(p.get_x() for p in ax2.patches
                if p.get_width() and p.get_facecolor()[:3] == matplotlib.colors.to_rgb('#2ca02c'))
    assert len(xs) == 18, f'el producto corto dibujo {len(xs)} barras, esperaba 18'
    ini = mdates.num2date(xs[0]).strftime('%Y-%m')
    assert ini.startswith('2025-0'), f'el producto corto arranca en {ini}, esperaba 2025-03'
    plt.close('all')
    print(f'OK  CELDA 12: 6 PNG, leyenda {con_base[0]!r}, 18 barras desde {ini}')


def test_tiles(celda17):
    """El fondo del mapa sale de TILES_MAPA y por default es OSM (CARTO exige API key)."""
    import folium
    m = re.search(r' *_TILES_OPC = \{.*?\.add_to\(m\)\n', celda17, re.S)
    assert m, 'no se encontro el bloque de tiles en la CELDA 17'
    bloque = textwrap.dedent(m.group(0))

    env = {'folium': folium}                       # sin TILES_MAPA definido
    exec(compile(bloque, '<tiles default>', 'exec'), env)
    html = env['m'].get_root().render()
    assert 'tile.openstreetmap.org' in html, 'el default no quedo en OpenStreetMap'
    assert 'cartocdn' not in html, 'quedaron tiles de CARTO en el default'

    env = {'folium': folium, 'TILES_MAPA': 'carto'}
    exec(compile(bloque, '<tiles carto>', 'exec'), env)
    assert 'cartocdn' in env['m'].get_root().render()

    env = {'folium': folium, 'TILES_MAPA': 'no_existe'}
    exec(compile(bloque, '<tiles invalido>', 'exec'), env)
    assert 'tile.openstreetmap.org' in env['m'].get_root().render()
    print('OK  CELDA 17: default OSM, TILES_MAPA="carto" respetado, invalido cae a OSM')


if __name__ == '__main__':
    celdas = _celdas(NB_PATH)
    test_celda12_series_desiguales(next(c for c in celdas if 'CELDA 12' in c[:200]))
    test_tiles(next(c for c in celdas if 'CELDA 17' in c[:200]))
    print(f'\nTodo OK  (PNG de prueba en {OUTPUT_DIR})')
