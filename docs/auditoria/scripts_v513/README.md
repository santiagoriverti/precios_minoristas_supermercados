# Simulación de la nb07 v5.13 sobre el caché de una corrida anterior

`simular_v513.py` estima, **sin releer el SEPA**, qué va a dar la v5.13 con los datos de una corrida ya hecha: corre
el código real de `notebooks/gen_nb07.py` (bloque 2b: índice TPD de los frescos y su nivel) sobre el panel por EAN
del caché, con el estimador nacional de cada fresco replicado desde los precios por sucursal, y aplica a los
empaquetados la cobertura mínima de la v5.13. Los parámetros se leen del generador. Detalle y resultados en
[`../../METODOLOGIA.md`](../../METODOLOGIA.md) §10.19.

Sirvió para encontrar, antes de publicar, BUG-40 (la cobertura mínima con arrastre) y BUG-41 (el nivel del Durazno
fuera de temporada). **Antes de dar por buena una regla nueva del nb07, simularla así.**

## Insumos (variables de entorno, las de `../scripts_v59/config.py`)

| Variable | Qué es |
|---|---|
| `AUD_EXCEL` | salida del nb07 de la corrida cuyo caché se usa (`canastas_alternativas_2026-09-24.xlsx` para la v5.12) |
| `AUD_CACHE` | carpeta con `sem_<clave>_v5/` y `ean_<clave>_v5/` de esa corrida |
| `AUD_TRABAJO` | opcional, carpeta de intermedios |

## Uso

```bash
python simular_v513.py              # compara en el mes de NIVEL_REFERENCIA_FRESCO (2026-08)
python simular_v513.py --mes 2026-07
```

Referencia con el caché de la v5.12 (`f32678cd`), índice ene-24 → ago-26: Popular 242,8 · Media 247,6 ·
Ejecutiva 243,3 · Representativa 239,2 · Femenina 258,7 · Tecnológica 111,9 (jun-25 = 100). Nivel de los frescos
de otros meses: Durazno feb-abr 2026, Roast beef may-jul 2026. Tarda ~4 minutos.

Aproximaciones: la cobertura de los empaquetados se cuenta sobre todas las sucursales del caché (el nb07 la cuenta
después de validar); las anclas del INDEC quedan en el nivel publicado; la relectura de la v5.13 cambia además el
filtro de régimen de Naranja, Tomate y Limón (aperturas y nivel del estimador), que acá no se simula.
