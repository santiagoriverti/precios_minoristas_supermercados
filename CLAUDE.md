# CLAUDE.md — precios_minoristas_supermercados

Pipeline sobre el **SEPA** (precios de supermercados de Argentina): 7 notebooks de Colab (nb01–nb07).
El que se trabaja hoy es el **nb07** (`notebooks/07_evolucion_canastas_alternativas.ipynb`), motor del
informe semanal: 6 canastas, índice encadenado, comparación con el IPC y aperturas por cadena/región.

## Al empezar una sesión

1. **Leer el bloque `ESTADO ACTUAL / HANDOFF` al principio de `.claude/memory.md`.** Ahí está en qué
   quedó el trabajo, qué hay que hacer apenas el usuario pase resultados y los números vigentes.
2. Correr los tests (`pip install -r requirements.txt` si es una PC nueva):
   ```bash
   python notebooks/test_celdas_graficos_y_mapa.py
   python notebooks/test_encadenado_frescos.py
   python notebooks/test_quiebre_serie.py
   python notebooks/test_cache_por_mes.py
   python notebooks/test_costo_sucursal.py
   python notebooks/test_candidatos_reemplazo.py
   ```
3. Los datos (ZIPs del SEPA, caché, Excel de salida) **no están en el repo**: viven en el Drive del
   usuario (`MyDrive/carga/`). Para auditar una corrida, el usuario pasa el Excel del nb07 y los zips
   de las carpetas del caché.

## Reglas que muerden

- **Los `.ipynb` NO se editan a mano.** La fuente es `notebooks/gen_nbXX.py`; regenerar con
  `python notebooks/gen_nb07.py` y commitear generador + `.ipynb` juntos.
- **Barras invertidas**: en celdas `cell_code("""...""")` (no raw) Python se las come y rompen el
  notebook (BUG-17/20). Las del nb07 son `r'''...'''` y aceptan regex con `\b`, pero no usar `'\n'` en
  celdas no raw. Si se edita el generador desde la shell, escribir el script de edición en un archivo:
  la shell se come las barras de los heredocs.
- **Clave del caché del nb07**: la cambian el universo de EANs leído (canastas + `EANS_CANDIDATOS` +
  frescos de `TIPOS_FRESCOS` menos `EXCLUIR_EAN_FRESCO`; también un maestro nuevo que agregue EANs de
  frescos), `DIA_CIERRE_SEMANA`, los K de la lectura, `rk` y `RATIO_FRESCO`. Cambiarla **relee todo el
  SEPA (~1h20m)**. No la cambian: cantidades, `NIVEL_REFERENCIA_FRESCO`, `QUIEBRE_ITEM_K`, nada de la
  CELDA 8 en adelante.
- **Anclar el nivel de un fresco cambia el índice** (cada ítem pesa cantidad × precio), no solo el costo.
- **Auditar cada corrida** antes de publicar:
  `python notebooks/auditar_salida_nb07.py <Excel> --cache <carpeta con sem_*_v5 y ean_*_v5> --indec data/sh_ipc_precios_promedio_2026-08.xls`
  (bajar la planilla nueva del INDEC cuando salga: https://www.indec.gob.ar/ftp/cuadros/economia/sh_ipc_precios_promedio.xls).
- **Reemplazos puntuales de productos**: `docs/canastas_alternativas/aplicar_reemplazos.py` (simula por
  defecto; `--escribir` aplica). No correr el constructor entero para un reemplazo: recalibra todo.
  Ejemplo aplicado: `docs/canastas_alternativas/reemplazos_2026-09-24.csv`. Para PROPONER los reemplazos con
  la lógica del constructor y la historia medida: `proponer_reemplazos.py --nb07 ... --excel ... --cache ...`.
- **"Meses con dato" no alcanza para juzgar la historia de un producto**: un mes cuenta aunque el
  producto esté en UNA sucursal (Raid 370: 97% de meses con dato y 1 sucursal en 2025). Antes de elegir
  un reemplazo, contar sucursales por mes (auditor con `--cache`, bloque 7b: ≥300 en 28 de 32 meses).

## Git

- Commits **solo con el usuario (Santiago Riverti)**: nunca agregar `Co-Authored-By: Claude` ni otra
  atribución a Claude en commits o PRs.
- Rama `main`, push directo a `origin` (https://github.com/santiagoriverti/precios_minoristas_supermercados, privado).
- Al cerrar una sesión: actualizar `.claude/memory.md` (bloque ESTADO ACTUAL), `docs/CONTEXTO.md`
  (historial), `docs/BUGS_Y_MEJORAS.md` y lo que corresponda del README, y commitear/pushear todo.

## Mapa de la documentación

| Archivo | Qué tiene |
|---|---|
| `.claude/memory.md` | **Estado y próximos pasos** (bloque de arriba) + handoffs históricos |
| `docs/CONTEXTO.md` | Pipeline, puesta en marcha en otra máquina, historial de cambios |
| `docs/METODOLOGIA.md` | Metodología; nb07 en §10 (§10.14-10.16 lo último) |
| `docs/BUGS_Y_MEJORAS.md` | Defectos abiertos arriba; bugs resueltos con causa y fix |
| `docs/SEPA_TECNICO.md` | Formato SEPA, cadenas, frescos por tipo, caché |
| `docs/AUDITORIA_2026-09-22_v59.md` | Auditoría de la v5.9 + verificación de la v5.10 (§10) y de la v5.11 con los reemplazos de trazabilidad (§11) + PDF y scripts en `docs/auditoria/` |
| `docs/canastas_alternativas/README.md` | Composición de las 6 canastas, cargador, constructor, reemplazos |
