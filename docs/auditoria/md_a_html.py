# -*- coding: utf-8 -*-
"""Convierte un informe de auditoria en markdown a HTML con el estilo de docs/auditoria/ y a PDF.

    python md_a_html.py ../AUDITORIA_2026-09-22_v59.md auditoria_nb07_v59_2026-09-22

Escribe <salida>.html y, si encuentra Edge o Chrome, <salida>.pdf (A4, sin encabezados del navegador).
Cubre el subconjunto de markdown que usan los informes: titulos, parrafos, listas, tablas, bloques
de codigo, negrita, cursiva, codigo en linea y links. Sin dependencias externas.
"""
import html, pathlib, re, shutil, subprocess, sys

AQUI = pathlib.Path(__file__).resolve().parent
ESTILO = AQUI / 'auditoria_nb07_2026-09-22.html'   # se reusa su <head> (tipografia, colores, impresion)

def inline(t):
    t = html.escape(t, quote=False)
    t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
    t = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', t)
    t = re.sub(r'(?<![*\w])\*([^*\s][^*]*)\*(?!\w)', r'<i>\1</i>', t)
    t = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', t)
    t = re.sub(r'&lt;(https?://[^&]+)&gt;', r'<a href="\1">\1</a>', t)
    return t

def celda(c, th=False):
    c = c.strip(); tag = 'th' if th else 'td'
    num = bool(re.fullmatch(r'[−+\-]?[\d.,]+\s*[%×x]?|[×x][\d.,]+|[\d.,]+×', c.replace('*', '')))
    return f'<{tag}{" class=\"n\"" if num else ""}>{inline(c)}</{tag}>'

def convertir(md):
    lineas = md.splitlines(); out = []; i = 0; titulo = ''; en_seccion = False
    while i < len(lineas):
        l = lineas[i]
        if l.startswith('# '):
            titulo = l[2:].strip(); i += 1; continue
        if l.startswith('## '):
            if en_seccion: out.append('</section>')
            out.append(f'<section><h2>{inline(l[3:])}</h2>'); en_seccion = True; i += 1; continue
        if l.startswith('### '):
            out.append(f'<h3>{inline(l[4:])}</h3>'); i += 1; continue
        if l.startswith('```'):
            j = i + 1; blq = []
            while j < len(lineas) and not lineas[j].startswith('```'):
                blq.append(lineas[j]); j += 1
            out.append('<pre><code>' + html.escape('\n'.join(blq)) + '</code></pre>'); i = j + 1; continue
        if l.startswith('    ') and l.strip():
            blq = []
            while i < len(lineas) and (lineas[i].startswith('    ') or not lineas[i].strip()):
                blq.append(lineas[i][4:]); i += 1
            out.append('<pre><code>' + html.escape('\n'.join(blq).rstrip()) + '</code></pre>'); continue
        if l.startswith('|'):
            filas = []
            while i < len(lineas) and lineas[i].startswith('|'):
                filas.append([c for c in lineas[i].strip().strip('|').split('|')]); i += 1
            cab, cuerpo = filas[0], [f for f in filas[2:]]
            out.append('<div class="scroll"><table><thead><tr>' + ''.join(celda(c, True) for c in cab) + '</tr></thead><tbody>'
                       + ''.join('<tr>' + ''.join(celda(c) for c in f) + '</tr>' for f in cuerpo) + '</tbody></table></div>')
            continue
        if re.match(r'^\s*([-*]|\d+\.)\s', l):
            ordenada = bool(re.match(r'^\s*\d+\.', l)); items = []
            while i < len(lineas) and lineas[i].strip() and (re.match(r'^\s*([-*]|\d+\.)\s', lineas[i]) or lineas[i].startswith('  ')):
                if re.match(r'^\s*([-*]|\d+\.)\s', lineas[i]):
                    items.append(re.sub(r'^\s*([-*]|\d+\.)\s+', '', lineas[i]))
                else:
                    items[-1] += ' ' + lineas[i].strip()
                i += 1
            tag = 'ol' if ordenada else 'ul'
            out.append(f'<{tag}>' + ''.join(f'<li>{inline(t)}</li>' for t in items) + f'</{tag}>'); continue
        if l.strip() in ('---', ''):
            i += 1; continue
        par = [l]; i += 1
        while i < len(lineas) and lineas[i].strip() and not re.match(r'^(#|\||```|\s*([-*]|\d+\.)\s|---)', lineas[i]):
            par.append(lineas[i]); i += 1
        out.append(f'<p>{inline(" ".join(p.strip() for p in par))}</p>')
    if en_seccion: out.append('</section>')
    return titulo, '\n'.join(out)

def main():
    md_path = pathlib.Path(sys.argv[1]); base = AQUI / sys.argv[2]
    titulo, cuerpo = convertir(md_path.read_text(encoding='utf-8'))
    head = ESTILO.read_text(encoding='utf-8').split('<body>')[0]
    head = re.sub(r'<title>.*?</title>', f'<title>{html.escape(titulo)}</title>', head, flags=re.S)
    extra = ('<style>pre{background:var(--stripe);padding:10px 14px;border-radius:3px;overflow-x:auto;font-size:.8rem;}'
             'pre code{background:none;padding:0;} ol{margin:0;padding-left:1.3rem;display:flex;flex-direction:column;gap:6px;max-width:65ch;}'
             'section p{max-width:none;} a{color:var(--accent);}</style>')
    doc = (head.replace('</head>', extra + '</head>') + '<body><div class="wrap"><header><div class="eyebrow">SEPA · nb07</div>'
           f'<h1>{inline(titulo)}</h1><div class="meta">{html.escape(md_path.name)}</div></header>\n{cuerpo}\n'
           f'<footer>Generado desde {html.escape(md_path.name)} con docs/auditoria/md_a_html.py</footer></div></body></html>')
    base.with_suffix('.html').write_text(doc, encoding='utf-8')
    print('HTML:', base.with_suffix('.html'))
    nav = next((p for p in (shutil.which('msedge'), r'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
                            r'C:/Program Files/Google/Chrome/Application/chrome.exe', shutil.which('chrome'),
                            shutil.which('google-chrome'), shutil.which('chromium')) if p and pathlib.Path(p).exists()), None)
    if nav is None:
        print('(sin Edge/Chrome: imprimir el HTML a PDF a mano)'); return
    pdf = base.with_suffix('.pdf')
    subprocess.run([nav, '--headless=new', '--disable-gpu', '--no-pdf-header-footer', f'--print-to-pdf={pdf}',
                    base.with_suffix('.html').as_uri()], check=False, timeout=180, capture_output=True)
    print('PDF:', pdf, f'({pdf.stat().st_size // 1024} KB)' if pdf.exists() else '(no se genero)')

if __name__ == '__main__':
    main()
