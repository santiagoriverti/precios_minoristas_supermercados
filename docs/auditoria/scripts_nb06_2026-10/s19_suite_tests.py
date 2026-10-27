# Corre los 15 tests del repositorio (notebooks/test_*.py; test_encadenado_frescos con 'encadenado' y 'tpd') y anota
# código de salida, tiempo y la última línea de cada uno. Uso: python -I -X utf8 s19_suite_tests.py <repo> <log de salida>
import subprocess, sys, time
from pathlib import Path

REPO, LOG = Path(sys.argv[1]), Path(sys.argv[2])
TESTS = [('test_brecha_celiaca.py',), ('test_celdas_graficos_y_mapa.py',), ('test_encadenado_frescos.py', 'encadenado'),
         ('test_encadenado_frescos.py', 'tpd'), ('test_frescos_v513.py',), ('test_quiebre_serie.py',),
         ('test_cache_por_mes.py',), ('test_costo_sucursal.py',), ('test_candidatos_reemplazo.py',),
         ('test_desagregacion_variacion.py',), ('test_analisis_detallado.py',), ('test_valores_documento.py',),
         ('test_reclasificacion_provincia.py',), ('test_trazabilidad_productos.py',), ('test_canasta_diaria.py',)]
lineas, fallas = [], 0
for t in TESTS:
    t0 = time.time()
    r = subprocess.run([sys.executable, '-X', 'utf8', str(REPO / 'notebooks' / t[0]), *t[1:]], cwd=REPO,
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    ult = [x for x in (r.stdout + r.stderr).strip().splitlines() if x.strip()]
    lin = f'{" ".join(t)} -> exit {r.returncode} ({time.time() - t0:.0f} s) | {ult[-1] if ult else ""}'
    fallas += r.returncode != 0
    lineas.append(lin)
    print(lin, flush=True)
LOG.write_text('\n'.join(lineas) + '\n', encoding='utf-8')
print(f'{len(TESTS) - fallas}/{len(TESTS)} OK')
sys.exit(1 if fallas else 0)
