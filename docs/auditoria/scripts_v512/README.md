# Scripts de la revisión de la corrida nb07 v5.12

Reproducen los números de [`../../AUDITORIA_2026-09-24_v512.md`](../../AUDITORIA_2026-09-24_v512.md).
No forman parte del pipeline: el control rutinario de cada corrida es
[`notebooks/auditar_salida_nb07.py`](../../../notebooks/auditar_salida_nb07.py) (que desde esta revisión
incluye el bloque 7b de cobertura histórica).

## Insumos (variables de entorno)

| Variable | Qué es |
|---|---|
| `AUD_EXCEL` | `canastas_alternativas_2026-09-24.xlsx` (corrida v5.12) |
| `AUD_EXCEL_PREV` | `canastas_alternativas_2026-09-17.xlsx` (corrida anterior; solo para `niveles`) |
| `AUD_CACHE` | carpeta con `sem_<clave>_v5/` y `ean_<clave>_v5/` de la v5.12 (`flacos`, `deriva`, `estacional`) |
| `AUD_INDEC` | planilla de precios promedio del INDEC (por defecto `data/sh_ipc_precios_promedio_2026-08.xls`) |

## Uso

```bash
python revision_v512.py brecha frescos      # sección 2: brecha con el IPC, SEPA vs INDEC, frescos del INDEC
python revision_v512.py jackknife           # 3.1: error estándar por elección de productos
python revision_v512.py flacos deriva       # 3.2 y 3.3: cobertura mínima y encadenado vs canasta fija
python revision_v512.py estacional niveles  # 4.1 y 4.2: los dos defectos
```

La ronda 2 de reemplazos (sección 5) se reproduce con las herramientas del repo:
`docs/canastas_alternativas/proponer_reemplazos.py` (propuesta) y `aplicar_reemplazos.py` (simulación).
