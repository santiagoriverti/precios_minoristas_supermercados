#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Aplica REEMPLAZOS PUNTUALES de productos en las canastas del nb07, con las reglas del constructor.

Pensado para el paso que sigue a la relectura v5.11: la hoja `Candidatos_trazabilidad` del Excel del
nb07 dice que candidato tiene historia en el SEPA; aca se aplica la eleccion sin recalibrar todas las
canastas (correr `construir_canastas_v5.py` entero sobre un Excel nuevo cambiaria muchos productos).

    python aplicar_reemplazos.py --excel canasta_representativa_2026-09.xlsx --reemplazos reemplazos.csv
    python aplicar_reemplazos.py --excel ... --reemplazos ... --escribir

`reemplazos.csv` tiene una fila por cambio, con columnas `canasta,necesidad,ean_nuevo`
(canasta: Popular | Media | Ejecutiva | Representativa | Femenina; necesidad: el nombre exacto de
`NEEDS` o `NEEDS_FEMENINA` del constructor, el mismo que figura en `Candidatos_trazabilidad`).

Para cada cambio:
  - busca el EAN nuevo entre los candidatos de esa necesidad (misma funcion `candidatos` del
    constructor) y calcula la cantidad = cantidad fisica / presentacion, con el mismo redondeo;
  - identifica el EAN ACTUAL de esa canasta en esa necesidad (en `EANS_CANDIDATOS` del nb07);
  - AVISA si el nuevo no cumple la cobertura de su canasta, si rompe la monotonicidad de precio
    unitario Popular <= Media <= Ejecutiva, o si NO esta en `EANS_CANDIDATOS` (en ese caso el nb07
    releeria todo el SEPA);
  - sin `--escribir`, solo muestra lo que haria. Con `--escribir`, actualiza `cargar_canastas_v5.py`
    (cantidades, conteo de EANs y una linea de registro en el encabezado) y agrega el par
    (canasta, necesidad) -> EAN a `EAN_FORZADO` del constructor, para que una recalibracion futura
    no lo deshaga.
"""
import argparse, ast, csv, importlib.util, io, os, re, sys
from datetime import date

AQUI = os.path.dirname(os.path.abspath(__file__))
LOADER = os.path.join(AQUI, 'cargar_canastas_v5.py')
CONSTRUCTOR = os.path.join(AQUI, 'construir_canastas_v5.py')
GEN_NB07 = os.path.join(AQUI, '..', '..', 'notebooks', 'gen_nb07.py')
COL = {'Popular': 'cantidad_01', 'Media': 'cantidad_02', 'Ejecutiva': 'cantidad_03',
       'Tecnologica': 'cantidad_04', 'Representativa': 'cantidad_05', 'Femenina': 'cantidad_06'}
COLS = ['cantidad_01', 'cantidad_02', 'cantidad_03', 'cantidad_04', 'cantidad_05', 'cantidad_06']
POS = {'Popular': 0, 'Media': 1, 'Ejecutiva': 2, 'Representativa': 3}
TIERS = ['Popular', 'Media', 'Ejecutiva']


def _modulo(path, nombre):
    spec = importlib.util.spec_from_file_location(nombre, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _dict_literal(texto, nombre):
    """Extrae y evalua `NOMBRE = { ... }` de un archivo de texto (sin ejecutar el resto)."""
    i = texto.index(f'{nombre} = {{')
    j = texto.index('\n}\n', i) + 2
    return ast.literal_eval(texto[i + len(f'{nombre} = '):j]), i, j


def _redondeo(n):
    """El mismo del constructor: medios hasta 3 envases, enteros de ahi para arriba, minimo 0,5."""
    n = round(n * 2) / 2.0 if n < 3 else float(round(n))
    return n if n > 0 else 0.5


def _linea(ean, cant, comentario):
    vals = ', '.join(f"'{c}': {cant[c]:g}" for c in COLS)
    return f"    '{ean}': {{{vals}}},  # {comentario}"


def main():
    ap = argparse.ArgumentParser(description='Aplica reemplazos puntuales en las canastas del nb07.')
    ap.add_argument('--excel', required=True, help='canasta_representativa_YYYY-MM.xlsx (salida de nb01)')
    ap.add_argument('--reemplazos', required=True, help='CSV con canasta,necesidad,ean_nuevo')
    ap.add_argument('--escribir', action='store_true', help='escribir los cambios (si no, solo muestra)')
    a = ap.parse_args()

    cc = _modulo(CONSTRUCTOR, 'construir_canastas_v5')
    pu = cc.cargar_universo(a.excel)
    loader_txt = io.open(LOADER, encoding='utf-8').read()
    CANT, i0, i1 = _dict_literal(loader_txt, 'CANTIDADES')
    comentarios = {}
    for l in loader_txt[i0:i1].splitlines():
        m = re.match(r"    '(\d+)': \{.*\},  # (.*)$", l)
        if m:
            comentarios[m.group(1)] = m.group(2)
    gen_txt = io.open(GEN_NB07, encoding='utf-8').read()
    CAND, _, _ = _dict_literal(gen_txt, 'EANS_CANDIDATOS')
    CAND = {k.lstrip('0'): v for k, v in CAND.items()}

    with open(a.reemplazos, encoding='utf-8-sig') as f:
        pedidos = [{k.strip(): (v or '').strip() for k, v in r.items()} for r in csv.DictReader(f)]
    errores, avisos, cambios = [], [], []
    for r in pedidos:
        can, need, nuevo = r['canasta'], r['necesidad'], r['ean_nuevo'].lstrip('0')
        if can not in COL or can == 'Tecnologica':
            errores.append(f'{can}/{need}: canasta invalida'); continue
        tabla = cc.NEEDS_FEMENINA if can == 'Femenina' else cc.NEEDS
        if need not in tabla:
            errores.append(f'{can}/{need}: necesidad inexistente en el constructor'); continue
        cfg = tabla[need]
        q = cfg['qty'] if can == 'Femenina' else cfg['qty'][POS[can]]
        if q is None or q <= 0:
            errores.append(f'{can}/{need}: la necesidad no esta activa en esa canasta'); continue
        # El nuevo se busca con y sin inc/exc (el EAN_FORZADO del constructor hace lo mismo: el exc
        # de la rasuradora femenina, 'barba', descarta a PrestoBARBA3 Femenina).
        c = cc.candidatos(pu, dict(sub=cfg['sub'], inc=cfg.get('inc'), exc=cfg.get('exc'), u=cfg['u']))
        fila = c[c['ean'] == nuevo]
        if not len(fila):
            c2 = cc.candidatos(pu, dict(sub=cfg['sub'], u=cfg['u']))
            fila = c2[c2['ean'] == nuevo]
            if len(fila):
                avisos.append(f'{can}/{need}: {nuevo} no pasa el inc/exc de la necesidad (se acepta, como EAN_FORZADO)')
        if not len(fila):
            errores.append(f'{can}/{need}: {nuevo} no es candidato de la necesidad en este Excel'); continue
        x = fila.iloc[0]
        tam = (x['grams'] / 1000.0) if cfg['u'] == 'kg' else x['tam']
        n = _redondeo(q / tam if tam and tam > 0 else 0.0)
        # EAN ACTUAL de esta canasta en esta necesidad. En orden: la columna opcional `ean_actual`; el
        # item marcado ACTUAL de esa necesidad en EANS_CANDIDATOS (en cualquier canasta: un item
        # compartido por dos estratos figura una sola vez) que esta canasta use hoy; y si no, el unico
        # candidato de la necesidad que esta canasta usa hoy.
        usa = lambda k: CANT.get(k, {}).get(COL[can], 0) > 0
        if r.get('ean_actual'):
            actuales = [r['ean_actual'].lstrip('0')]
            if not usa(actuales[0]):
                errores.append(f'{can}/{need}: ean_actual {actuales[0]} no esta en esa canasta'); continue
        else:
            actuales = [k for k, v in CAND.items() if f' / {need} / ACTUAL' in v and usa(k)]
            if not actuales:
                actuales = [k for k in c['ean'] if usa(k) and k != nuevo]
            if len(actuales) > 1:
                errores.append(f'{can}/{need}: hay mas de un item actual posible {actuales}: indicar ean_actual'); continue
        if not actuales:
            avisos.append(f'{can}/{need}: no encuentro el item ACTUAL (solo se agrega el nuevo)')
        otros = [t for t in TIERS + ['Representativa'] if t != can and CANT.get(nuevo, {}).get(COL[t], 0) > 0]
        if otros:
            avisos.append(f'{can}/{need}: {nuevo} ya lo usa {", ".join(otros)} (los estratos compartirian producto)')
        if nuevo not in CAND:
            avisos.append(f'{can}/{need}: {nuevo} NO esta en EANS_CANDIDATOS -> el nb07 RELEERA el SEPA')
        reg = cc.COBERTURA[can]
        if not (x['n_cadenas'] >= reg['cadenas'] and x['n_provincias'] >= reg['provincias'] and x['n_sucursales'] >= reg['sucursales']):
            avisos.append(f"{can}/{need}: {nuevo} bajo el piso de {can} ({int(x['n_sucursales'])} suc, {int(x['n_cadenas'])} cad, "
                          f"{int(x['n_provincias'])} prov; piso {reg})")
        if can in TIERS:
            k = TIERS.index(can)
            for otra in TIERS:
                if otra == can:
                    continue
                suyos = c[c['ean'].isin([e for e, v in CANT.items() if v.get(COL[otra], 0) > 0])]
                if not len(suyos):
                    continue
                p_otra = float(suyos['pu'].min())
                ko = TIERS.index(otra)
                if (ko < k and x['pu'] < p_otra) or (ko > k and x['pu'] > p_otra):
                    avisos.append(f'{can}/{need}: precio unitario {x["pu"]:,.0f} rompe la monotonicidad contra '
                                  f'{otra} ({p_otra:,.0f})')
        cambios.append(dict(canasta=can, necesidad=need, nuevo=nuevo, actuales=actuales, n=n, x=x))

    print(f'{len(pedidos)} pedidos | {len(cambios)} aplicables | {len(errores)} errores | {len(avisos)} avisos\n')
    for c in cambios:
        x = c['x']
        print(f"  {c['canasta']:15s} {c['necesidad']:30s} {','.join(c['actuales']) or '-':>15s} -> {c['nuevo']:15s} "
              f"x{c['n']:g}  {str(x['desc'])[:48]}  ({int(x['n_sucursales'])} suc, ${x['pu']:,.0f}/u)")
    for e in errores:
        print('  ERROR ', e)
    for w in avisos:
        print('  AVISO ', w)
    if errores:
        sys.exit('\nHay errores: no se escribio nada.')
    if not a.escribir:
        print('\n(simulacion: agregar --escribir para aplicar)')
        return

    for c in cambios:
        col = COL[c['canasta']]
        for act in c['actuales']:
            CANT[act][col] = 0
        CANT.setdefault(c['nuevo'], {k: 0 for k in COLS})
        CANT[c['nuevo']][col] = c['n']
        if c['nuevo'] not in comentarios:
            x = c['x']
            comentarios[c['nuevo']] = f"{str(x['rubro']).strip()} | {str(x['desc'])[:58]}"
    vivos = {e: v for e, v in CANT.items() if any(v[k] > 0 for k in COLS)}
    # Las lineas que no cambian conservan su comentario entero. `i1` apunta al salto de linea que
    # sigue a la llave de cierre, asi que el cuerpo termina en '}' sin salto.
    cuerpo = 'CANTIDADES = {\n' + '\n'.join(_linea(e, v, comentarios.get(e, '? | ?'))
                                            for e, v in vivos.items()) + '\n}'
    nuevo_txt = loader_txt[:i0] + cuerpo + loader_txt[i1:]
    nuevo_txt = re.sub(r'#   \d+ EANs   \|', f'#   {len(vivos)} EANs   |', nuevo_txt, count=1)
    registro = '\n'.join([f"#   REEMPLAZOS {date.today().isoformat()} (aplicar_reemplazos.py, por trazabilidad):"]
                         + [f"#     {c['canasta']} / {c['necesidad']}: {','.join(c['actuales']) or '-'} -> {c['nuevo']} "
                            f"({str(c['x']['desc'])[:48]})" for c in cambios])
    nuevo_txt = re.sub(r'(#   \d+ EANs   \|)', lambda m: registro + '\n' + m.group(1), nuevo_txt, count=1)
    ast.parse(nuevo_txt)
    io.open(LOADER, 'w', encoding='utf-8', newline='').write(nuevo_txt)

    cons = io.open(CONSTRUCTOR, encoding='utf-8').read()
    ini = cons.index('EAN_FORZADO = {'); fin = cons.index('\n}\n', ini)
    bloque = cons[ini:fin]
    for c in cambios:
        clave = f"    ('{c['canasta']}', '{c['necesidad']}'):"
        linea = f"{clave} '{c['nuevo']}',  # {str(c['x']['desc'])[:50]} ({date.today().isoformat()}, trazabilidad)"
        if clave in bloque:
            bloque = re.sub(re.escape(clave) + r".*", lambda m: linea, bloque, count=1)
        else:
            bloque += '\n' + linea
    cons = cons[:ini] + bloque + cons[fin:]
    ast.parse(cons)
    io.open(CONSTRUCTOR, 'w', encoding='utf-8', newline='').write(cons)
    print(f'\nEscrito: {LOADER} ({len(vivos)} EANs) y EAN_FORZADO en {CONSTRUCTOR}')


if __name__ == '__main__':
    main()
