#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
03_consolidacion_ultimo_mes.py
==============================================================================
Convierte el SEPA **diario** (descarga del Ministerio de Economía) al formato
**semestral wide** que consumen los notebooks 01 y 02 de este repositorio.

Permite trabajar con el mes en curso SIN esperar a que el SEPA publique el
archivo semestral consolidado: se ejecuta localmente sobre el .zip diario y
produce los dos .csv.gz del mes, listos para subir a Drive.

------------------------------------------------------------------------------
ENTRADA  (formato diario)
------------------------------------------------------------------------------
    ultimo_mes.zip
    ├── 2026-06-01/
    │   ├── sepa_1_comercio-sepa-10_2026-06-01_09-05-11.zip
    │   │   ├── comercio.csv      (pipe '|')
    │   │   ├── sucursales.csv    (pipe '|', trae sucursales_provincia = AR-X)
    │   │   └── productos.csv     (pipe '|', precio en PESOS)
    │   └── ...  (un zip anidado por comercio)
    ├── 2026-06-02/
    └── ...      (una carpeta por día)

------------------------------------------------------------------------------
SALIDA  (formato semestral, idéntico al oficial del SEPA)
------------------------------------------------------------------------------
    062026_pais_parte1COMPLETO.csv.gz   (días 01-15)
    062026_pais_parte2COMPLETO.csv.gz   (días 16-último)

    Header: id_comercio,id_bandera,id_sucursal,sucursales_provincia,id_producto,
            precio_YYYYMMDD,precio_YYYYMMDD,...
    - Separador: coma
    - Precio: ENTERO en PESOS, igual que el oficial 2026 (que ya viene en pesos).
              El diario también viene en pesos, así que NO se multiplica.
    - Faltante: 'NA'

Además, si CARGA_DIR tiene el zip semestral del mes (YYYYA.zip para ene-jun,
YYYYB.zip para jul-dic), genera una copia actualizada que reemplaza los
archivos viejos del mes por los nuevos y conserva el resto de los meses. Ese
zip es el que se sube a Drive.

La entrada puede ser el zip diario o la carpeta con los días ya descomprimidos.

------------------------------------------------------------------------------
NOTAS DE COMPATIBILIDAD (verificadas contra los archivos oficiales)
------------------------------------------------------------------------------
- Las claves (id_comercio, id_bandera, id_sucursal) del diario coinciden con
  las del semestral oficial y con el maestro de sucursales -> el join
  geográfico de los notebooks funciona sin cambios.
- Todos los datos son MINORISTAS (no hay mayoristas en ninguna fuente). El
  diario no incluye algunos comercios minoristas adicionales (id_comercio 2000,
  3001, etc.) que sí están en los archivos oficiales, pero son irrelevantes
  para la canasta (afectan ~-0,01% el costo, verificado).
- El precio diario y el semestral oficial 2026 están AMBOS en PESOS, así que se
  exporta tal cual (sin multiplicar). Verificado: mediana oficial 052026 ~$4.400.

Uso:
    python notebooks/03_consolidacion_ultimo_mes.py
Ajustar la sección CONFIGURACIÓN según la PC.
==============================================================================
"""

import io
import gc
import re
import sys
import time
import gzip
import zipfile
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

# Salida UTF-8 en consolas Windows
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# ============================================================================
# CONFIGURACIÓN — modificar según tu PC
# ============================================================================

# SEPA diario descargado del Ministerio. Puede ser:
#   - el zip del mes (ultimo_mes.zip, con carpetas YYYY-MM-DD adentro), o
#   - la carpeta que contiene las carpetas YYYY-MM-DD ya descomprimidas.
ZIP_DIARIO = Path(r"C:\Users\sriverti\Desktop\INECO\SEPA\sepa_diario_minoristas")

# Carpeta con los zips semestrales (YYYYA.zip / YYYYB.zip). Se elige solo el que
# corresponde al mes procesado (ene-jun -> A, jul-dic -> B) y el mes generado se
# inserta ahí conservando los demás meses. Si ese zip no existe, se crea uno
# nuevo solo con el mes. Poner None para generar solo los .csv.gz sueltos.
CARGA_DIR = Path(r"C:\Users\sriverti\Desktop\INECO\SEPA\SEPA_Bases_Originales\carga")

# Carpeta donde se escriben los .csv.gz y el zip semestral actualizado
OUTPUT_DIR = Path(r"C:\Users\sriverti\Desktop\INECO\SEPA\salida_consolidada")

# Forzar un mes 'YYYY-MM'. None = usar el último mes presente en el zip diario.
MES_FORZADO = None

# Los semestrales oficiales 2026 vienen en PESOS (igual que el diario) -> dejar en False.
# (Solo los históricos pre-2025B estaban en centavos; no aplica al diario actual.)
PRECIO_EN_CENTAVOS = False

# DEBUG: limitar a N comercios para una prueba rápida (None = todos).
LIMITE_COMERCIOS = None
# DEBUG: limitar a los primeros N días (None = todos).
LIMITE_DIAS = None

# Columnas del archivo diario productos.csv que necesitamos para los PRECIOS
_COLS_PROD = ["id_comercio", "id_bandera", "id_sucursal", "id_producto", "productos_precio_lista"]

# Columnas de METADATA del producto (nombre/marca/presentación). Se extraen del propio
# productos.csv para armar un MAESTRO DE PRODUCTOS COMPLETO — captura TODO lo que se vende
# (incluidos EANs que no están en el Maestro interno curado, p.ej. celíacos de nicho). Se
# leen las que existan (nombres robustos a variantes del formato SEPA).
_COLS_META = [
    "productos_descripcion", "productos_marca",
    "productos_cantidad_presentacion", "productos_unidad_medida_presentacion",
    "producto_unidad_medida_presentac",  # variante alternativa
]
_COLS_LEER = set(_COLS_PROD) | set(_COLS_META)  # productos.csv se lee con estas (las presentes)

_RE_NESTED = re.compile(r"comercio-sepa-(\d+)_", re.IGNORECASE)
_RE_DIA = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


def _norm_suc(serie: pd.Series) -> pd.Series:
    """
    El diario rellena id_sucursal con ceros a la izquierda ('004'); el semestral
    oficial y el maestro de sucursales usan el id sin relleno ('4'). Hay que
    quitar los ceros para que el join geográfico de los notebooks matchee.
    """
    return serie.astype(str).str.strip().str.lstrip("0").replace("", "0")


class CarpetaDiaria:
    """
    Expone una carpeta con subcarpetas YYYY-MM-DD/ (el diario ya descomprimido)
    con la misma interfaz que zipfile.ZipFile que usa este script
    (namelist / read / close), para que el resto del código no cambie.
    """

    def __init__(self, raiz: Path):
        self.raiz = raiz

    def namelist(self):
        return [
            p.relative_to(self.raiz).as_posix()
            for d in self.raiz.iterdir() if d.is_dir() and _RE_DIA.match(d.name)
            for p in d.iterdir() if p.is_file()
        ]

    def read(self, nombre: str) -> bytes:
        return (self.raiz / nombre).read_bytes()

    def close(self):
        pass


def abrir_diario(ruta: Path):
    """Devuelve (lector, tamaño en bytes) para un zip diario o una carpeta de días."""
    if ruta.is_dir():
        lector = CarpetaDiaria(ruta)
        tam = sum((ruta / n).stat().st_size for n in lector.namelist())
        return lector, tam
    if ruta.is_file():
        return zipfile.ZipFile(ruta, "r"), ruta.stat().st_size
    raise FileNotFoundError(
        f"No existe {ruta}. ZIP_DIARIO debe ser el zip del mes o la carpeta que "
        f"contiene las carpetas YYYY-MM-DD."
    )


# ============================================================================
# Funciones de lectura
# ============================================================================
def detectar_dias(zf: zipfile.ZipFile):
    """Devuelve (lista_dias 'YYYY-MM-DD' ordenada, anio, mes) presentes en el zip."""
    dias = set()
    for nombre in zf.namelist():
        top = nombre.split("/", 1)[0]
        if _RE_DIA.match(top):
            dias.add(top)
    if not dias:
        raise RuntimeError("No se encontraron carpetas YYYY-MM-DD en el zip diario.")
    dias = sorted(dias)
    if MES_FORZADO:
        dias = [d for d in dias if d.startswith(MES_FORZADO)]
        if not dias:
            raise RuntimeError(f"El mes forzado {MES_FORZADO} no está en el zip.")
    else:
        # Quedarnos con el mes más reciente presente
        ultimo_mes = dias[-1][:7]
        dias = [d for d in dias if d.startswith(ultimo_mes)]
    if LIMITE_DIAS:
        dias = dias[:LIMITE_DIAS]
    anio, mes = int(dias[0][:4]), int(dias[0][5:7])
    return dias, anio, mes


def mapear_comercios(zf: zipfile.ZipFile, dias):
    """comercio_id (str) -> {dia 'YYYY-MM-DD' -> nombre del zip anidado}."""
    setdias = set(dias)
    mapa = {}
    for nombre in zf.namelist():
        if not nombre.endswith(".zip"):
            continue
        top = nombre.split("/", 1)[0]
        if top not in setdias:
            continue
        m = _RE_NESTED.search(nombre)
        if not m:
            continue
        cid = m.group(1)
        mapa.setdefault(cid, {})[top] = nombre
    return mapa


def leer_nested(zf: zipfile.ZipFile, nested_name: str):
    """
    Lee un zip anidado de un comercio-día.
    Devuelve (df_precios, dict_provincia) donde:
      - df_precios: columnas [id_bandera, id_sucursal, id_producto, precio]
        deduplicado por (bandera, sucursal, producto), precio en pesos (float).
      - dict_provincia: (id_bandera, id_sucursal) -> sucursales_provincia
    Maneja zips vacíos/corruptos devolviendo (None, {}).
    """
    try:
        raw = zf.read(nested_name)
        if not raw:
            return None, {}, None
        inner = zipfile.ZipFile(io.BytesIO(raw))
    except Exception as e:
        print(f"      ⚠️  {Path(nested_name).name}: no se pudo abrir ({e})")
        return None, {}, None

    nombres = inner.namelist()

    # --- provincia por sucursal ---
    prov = {}
    if "sucursales.csv" in nombres:
        try:
            with inner.open("sucursales.csv") as f:
                ds = pd.read_csv(
                    io.TextIOWrapper(f, encoding="utf-8-sig", errors="replace"),
                    sep="|", dtype=str,
                    usecols=["id_bandera", "id_sucursal", "sucursales_provincia"],
                    on_bad_lines="skip",
                )
            ds = ds.dropna(subset=["id_sucursal"])
            ds["id_sucursal"] = _norm_suc(ds["id_sucursal"])
            prov = {
                (b, s): p
                for b, s, p in zip(ds["id_bandera"], ds["id_sucursal"], ds["sucursales_provincia"])
            }
        except Exception:
            prov = {}

    # --- precios + metadata ---
    if "productos.csv" not in nombres:
        return None, prov, None
    try:
        partes = []
        with inner.open("productos.csv") as f:
            tw = io.TextIOWrapper(f, encoding="utf-8-sig", errors="replace")
            for chunk in pd.read_csv(
                tw, sep="|", dtype=str, usecols=lambda c: c in _COLS_LEER,
                chunksize=500_000, on_bad_lines="skip",
            ):
                partes.append(chunk)
        if not partes:
            return None, prov, None
        dp = pd.concat(partes, ignore_index=True)
    except Exception as e:
        print(f"      ⚠️  {Path(nested_name).name}: productos.csv ilegible ({e})")
        return None, prov, None

    dp["precio"] = pd.to_numeric(dp["productos_precio_lista"], errors="coerce")
    dp = dp[dp["precio"] > 0]
    dp["id_sucursal"] = _norm_suc(dp["id_sucursal"])

    # metadata: 1 fila por EAN (nombre/marca/presentación) con nombres CANÓNICOS
    meta = dp.drop_duplicates(subset=["id_producto"]).copy()
    meta = meta.rename(columns={
        "productos_descripcion": "descripcion", "productos_marca": "marca",
        "productos_cantidad_presentacion": "cantidad",
        "productos_unidad_medida_presentacion": "unidad",
        "producto_unidad_medida_presentac": "unidad",
    })
    for _c in ["descripcion", "marca", "cantidad", "unidad"]:
        if _c not in meta.columns:
            meta[_c] = ""
    meta = meta[["id_producto", "descripcion", "marca", "cantidad", "unidad"]]

    dp = dp[["id_bandera", "id_sucursal", "id_producto", "precio"]]
    # Si un producto aparece más de una vez en el día para la misma sucursal,
    # quedarnos con el último (igual criterio que el SEPA al consolidar).
    dp = dp.drop_duplicates(subset=["id_bandera", "id_sucursal", "id_producto"], keep="last")
    return dp, prov, meta


# ============================================================================
# Procesamiento por comercio (acota la RAM al comercio más grande)
# ============================================================================
def procesar_comercio(zf, cid, dias_nested, columnas_dia, maestro_acc=None):
    """
    Construye el frame wide de un comercio.
    columnas_dia: lista de ('YYYY-MM-DD', 'precio_YYYYMMDD') de TODO el mes.
    maestro_acc: dict EAN -> (descripcion, marca, cantidad, unidad) que se va llenando
        con los productos vistos (solo se agregan EANs nuevos) → maestro completo.
    Devuelve un DataFrame con columnas:
        id_comercio,id_bandera,id_sucursal,sucursales_provincia,id_producto,
        precio_YYYYMMDD...   (precio en pesos enteros, NaN donde falta)
    """
    factor = 100 if PRECIO_EN_CENTAVOS else 1
    wide = None
    prov_global = {}

    for dia, col in columnas_dia:
        nested = dias_nested.get(dia)
        if nested is None:
            continue
        dp, prov, meta = leer_nested(zf, nested)
        if prov:
            prov_global.update(prov)
        if maestro_acc is not None and meta is not None and len(meta):
            for _r in meta.itertuples(index=False):
                _ean = _r.id_producto
                if _ean and _ean not in maestro_acc:
                    maestro_acc[_ean] = (_r.descripcion, _r.marca, _r.cantidad, _r.unidad)
        if dp is None or len(dp) == 0:
            continue
        s = dp.set_index(["id_bandera", "id_sucursal", "id_producto"])["precio"]
        s = (s * factor).round().astype("float32")
        s.name = col
        if wide is None:
            wide = s.to_frame()
        else:
            wide = wide.join(s, how="outer")
        del dp, s
        gc.collect()

    if wide is None:
        return None

    wide = wide.reset_index()
    wide.insert(0, "id_comercio", cid)
    # provincia
    claves = list(zip(wide["id_bandera"], wide["id_sucursal"]))
    wide["sucursales_provincia"] = [prov_global.get(k, "") for k in claves]

    # Orden final de columnas
    cols_precio = [c for _, c in columnas_dia]
    # asegurar que existan todas las columnas de día (NaN si el comercio no
    # reportó ese día)
    for c in cols_precio:
        if c not in wide.columns:
            wide[c] = np.nan
    orden = ["id_comercio", "id_bandera", "id_sucursal", "sucursales_provincia",
             "id_producto"] + cols_precio
    return wide[orden]


def escribir_parte(handle, df, cols_precio_parte):
    """Escribe las filas de un comercio en el .csv.gz de una parte (sin header)."""
    base = ["id_comercio", "id_bandera", "id_sucursal", "sucursales_provincia", "id_producto"]
    sub = df[base + cols_precio_parte].copy()
    # Precios -> enteros nullables para imprimir sin '.0' y con 'NA' en faltantes
    for c in cols_precio_parte:
        sub[c] = sub[c].round().astype("Int64")
    sub.to_csv(handle, header=False, index=False, na_rep="NA", lineterminator="\n")


# ============================================================================
# Empaquetado en el zip semestral
# ============================================================================
def actualizar_zip_semestre(zip_in: Path, zip_out: Path, archivos_mes: dict, mes_prefijo: str):
    """
    Reconstruye el zip semestral: copia todos los meses salvo el que se
    reemplaza (mes_prefijo, ej '062026_') y agrega los nuevos .csv.gz.
    archivos_mes: {nombre_en_zip -> Path local del .csv.gz}
    """
    zip_out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_out, "w", compression=zipfile.ZIP_STORED) as zout:
        if zip_in and zip_in.exists():
            with zipfile.ZipFile(zip_in, "r") as zin:
                for item in zin.infolist():
                    base = Path(item.filename).name
                    if base.startswith(mes_prefijo):
                        continue  # se reemplaza
                    zout.writestr(item, zin.read(item.filename))
        for nombre, ruta in archivos_mes.items():
            zout.write(ruta, arcname=nombre)


# ============================================================================
# MAIN
# ============================================================================
def main():
    t0 = time.time()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    zf, tam = abrir_diario(ZIP_DIARIO)
    print(f"Diario     : {ZIP_DIARIO}  ({tam/1024**3:.2f} GB)")
    print(f"Salida     : {OUTPUT_DIR}")

    dias, anio, mes = detectar_dias(zf)
    mmaaaa = f"{mes:02d}{anio}"
    print(f"Mes detectado: {anio}-{mes:02d}  |  {len(dias)} días: {dias[0]} … {dias[-1]}")

    # Columnas de precio de todo el mes
    columnas_dia = [(d, f"precio_{d.replace('-', '')}") for d in dias]
    dias_n = [int(d[8:10]) for d in dias]
    cols_p1 = [c for (d, c), dn in zip(columnas_dia, dias_n) if dn <= 15]
    cols_p2 = [c for (d, c), dn in zip(columnas_dia, dias_n) if dn >= 16]

    mapa = mapear_comercios(zf, dias)
    comercios = sorted(mapa.keys(), key=lambda x: int(x) if x.isdigit() else 0)
    if LIMITE_COMERCIOS:
        comercios = comercios[:LIMITE_COMERCIOS]
    print(f"Comercios a procesar: {len(comercios)} -> {comercios}")

    # Archivos de salida
    f1 = OUTPUT_DIR / f"{mmaaaa}_pais_parte1COMPLETO.csv.gz"
    f2 = OUTPUT_DIR / f"{mmaaaa}_pais_parte2COMPLETO.csv.gz"
    base_cols = ["id_comercio", "id_bandera", "id_sucursal", "sucursales_provincia", "id_producto"]

    h1 = gzip.open(f1, "wt", encoding="utf-8", newline="")
    h1.write(",".join(base_cols + cols_p1) + "\n")
    h2 = None
    if cols_p2:
        h2 = gzip.open(f2, "wt", encoding="utf-8", newline="")
        h2.write(",".join(base_cols + cols_p2) + "\n")

    tot_filas = 0
    eans = set()
    maestro_acc = {}   # EAN -> (descripcion, marca, cantidad, unidad) → maestro completo
    for i, cid in enumerate(comercios, 1):
        tc = time.time()
        df = procesar_comercio(zf, cid, mapa[cid], columnas_dia, maestro_acc)
        if df is None or len(df) == 0:
            print(f"  [{i}/{len(comercios)}] comercio {cid}: sin datos")
            continue
        escribir_parte(h1, df, cols_p1)
        if h2 is not None:
            escribir_parte(h2, df, cols_p2)
        tot_filas += len(df)
        eans.update(df["id_producto"].unique())
        print(f"  [{i}/{len(comercios)}] comercio {cid}: {len(df):,} filas "
              f"({time.time()-tc:.1f}s)")
        del df
        gc.collect()

    h1.close()
    if h2 is not None:
        h2.close()
    zf.close()

    # --- Maestro de productos COMPLETO (desde productos.csv, todo lo que se vende) ---
    # Columnas con los MISMOS nombres que el Maestro interno → los notebooks lo cargan igual.
    _mdf = pd.DataFrame(
        [(k, v[0], v[1], v[2], v[3]) for k, v in maestro_acc.items()],
        columns=["producto_sepa_id", "producto_descripcion", "producto_marca",
                 "producto_cantidad_presentacion", "producto_unidad_medida_presentac"],
    )
    _mpath = OUTPUT_DIR / "maestro_sepa_completo.csv.gz"
    _mdf.to_csv(_mpath, index=False, compression="gzip", encoding="utf-8")

    print("-" * 70)
    print(f"Filas totales (producto×sucursal): {tot_filas:,}")
    print(f"Productos (EAN) únicos:            {len(eans):,}")
    print(f"Maestro SEPA completo:             {len(_mdf):,} EANs con nombre/marca/presentación")
    print(f"  -> {_mpath.name}  ({_mpath.stat().st_size/1024**2:.1f} MB)  [subir a Drive: carga/]")
    print(f"  {f1.name}: {f1.stat().st_size/1024**2:.1f} MB  ({len(cols_p1)} días)")
    if h2 is not None:
        print(f"  {f2.name}: {f2.stat().st_size/1024**2:.1f} MB  ({len(cols_p2)} días)")
    else:
        print("  (sin parte2: el mes aún no tiene días ≥ 16)")

    # --- Empaquetar en el zip semestral ---
    if CARGA_DIR is not None:
        semestre_zip_in = CARGA_DIR / f"{anio}{'A' if mes <= 6 else 'B'}.zip"
        archivos_mes = {f1.name: f1}
        if h2 is not None:
            archivos_mes[f2.name] = f2
        zip_out = OUTPUT_DIR / semestre_zip_in.name
        if semestre_zip_in.exists():
            print(f"Actualizando {semestre_zip_in.name} (reemplazando mes {mmaaaa}_)…")
        else:
            print(f"⚠️  No existe {semestre_zip_in}: se crea {zip_out.name} solo con {mmaaaa}.")
        actualizar_zip_semestre(semestre_zip_in, zip_out, archivos_mes, f"{mmaaaa}_")
        with zipfile.ZipFile(zip_out) as _z:
            meses_zip = sorted({Path(n).name[:6] for n in _z.namelist()},
                               key=lambda m: (m[2:], m[:2]))
        print(f"  -> {zip_out}  ({zip_out.stat().st_size/1024**3:.2f} GB)")
        print(f"     Meses adentro: {', '.join(meses_zip)}")
        print(f"  Subir ESTE zip a Drive (carga/{semestre_zip_in.name}) y correr los notebooks.")

    print(f"Listo en {(time.time()-t0)/60:.1f} min.")


if __name__ == "__main__":
    main()
