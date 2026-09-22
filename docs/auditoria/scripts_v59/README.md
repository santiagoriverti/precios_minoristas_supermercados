# Scripts de la auditoría de la corrida nb07 v5.9

Reproducen cada número de [`../../AUDITORIA_2026-09-22_v59.md`](../../AUDITORIA_2026-09-22_v59.md).
No forman parte del pipeline: el control rutinario de cada corrida es
[`notebooks/auditar_salida_nb07.py`](../../../notebooks/auditar_salida_nb07.py).

## Insumos (variables de entorno)

| Variable | Qué es | De dónde |
|---|---|---|
| `AUD_EXCEL` | `canastas_alternativas_YYYY-MM-DD.xlsx` | salida del nb07 (`MyDrive/carga/output_canasta_alternativa/`) |
| `AUD_CACHE` | carpeta con `sem_<key>_v5/` y `ean_<key>_v5/` | `MyDrive/carga/output_canasta_alternativa/_cache_nb07/` (82 MB) |
| `AUD_INDEC` | `sh_ipc_precios_promedio.xls` | https://www.indec.gob.ar/ftp/cuadros/economia/sh_ipc_precios_promedio.xls |
| `AUD_TRABAJO` | intermedios (opcional) | default `_trabajo/` acá mismo; no se versiona |

El maestro de sucursales se lee de `data/` del repo.

## Orden

```bash
export AUD_EXCEL=.../canastas_alternativas_2026-09-17.xlsx AUD_CACHE=.../_cache_nb07 AUD_INDEC=.../sh_ipc_precios_promedio.xls
python 01_replica_cache.py   # ~4 min, ~4 GB de RAM: precio nacional replicado, por cadena y por provincia
python 02_largo_plazo.py     # comparación directa ene-24 vs ago-26 por sucursal apareada
python 03_tpd_frescos.py     # índice multilateral TPD por tipo fresco + réplica del encadenado
python 04_informe.py         # todas las tablas del informe
```

Las ventanas (ene-2024 y ago-2026) están fijas porque son las de esta auditoría; para auditar otra
corrida, cambiarlas en `02_largo_plazo.py` y `04_informe.py`.
