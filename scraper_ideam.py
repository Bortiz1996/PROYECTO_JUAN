#!/usr/bin/env python3
"""
scraper_ideam.py — ETL del nivel del río Magdalena en Calamar (IDEAM 29037020)

Flujo:
  1. Importa los CSV/Excel exportados que encuentre junto al script.
  2. Actualiza el histórico desde HidrologiaNacionalDiaria.zip del IDEAM.
     DHIME con Playwright y Socrata se conservan como fuentes secundarias.
  3. Limpia valores corruptos y escala x100, agrega a nivel medio diario (cm).
  4. Combina con el histórico `nivel_calamar.csv` sin duplicar fechas
     (los registros nuevos reemplazan a los viejos del mismo día), ordena y guarda.

Salida CSV (nivel_calamar.csv):
  Fecha          YYYY-MM-DD
  Nivel_cm       nivel medio diario en cm
  Ultima_lectura fecha-hora de la última lectura cruda de ese día

Variables de entorno opcionales:
  DIAS_ACTUALIZACION  ventana de días a consultar en cada corrida (def. 30)
  HISTORICO_DIAS      días a descargar si no existe el CSV (def. 365)
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
import tempfile
import time
import unicodedata
import zipfile
from io import BytesIO
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests
from playwright.sync_api import sync_playwright

# ───────────────────────────── CONFIGURACIÓN ─────────────────────────────
ESTACION_CODIGO = "0029037020"        # Código Socrata para CALAMAR [29037020]
ESTACION_CODIGO_UI = "29037020"
SOCRATA_URL = "https://www.datos.gov.co/resource/bdmn-sqnh.json"
DHIME_URL = "https://atencionciudadano.ideam.gov.co/"
NACIONAL_ZIP_URL = "https://bart.ideam.gov.co/PQRS/AQTSUtils/HidrologiaNacionalDiaria.zip"
NACIONAL_MIEMBRO = f"NV_MEDIA_D@{ESTACION_CODIGO_UI}.data"
BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "nivel_calamar.csv"
NACIONAL_ESTADO_PATH = BASE_DIR / "nivel_calamar_fuente.json"
DHIME_TERMS_ACCEPTED = os.getenv("IDEAM_DHIME_ACCEPT_TERMS", "true").lower() == "true"

VALOR_MIN_CM = 0.0                    # rango físico válido (cm)
VALOR_MAX_CM = 2000.0

DIAS_ACTUALIZACION = int(os.getenv("DIAS_ACTUALIZACION", "30"))
HISTORICO_DIAS = int(os.getenv("HISTORICO_DIAS", "365"))

PAGINA = 50_000                       # filas por petición Socrata
MAX_PAGINAS = 20                      # tope de seguridad
TIMEOUT_S = 60
REINTENTOS = 3

# Nombres de columna posibles (el esquema de Socrata puede variar).
COLS_ESTACION = ["codigoestacion", "codigo_estacion", "codigo"]
COLS_FECHA = ["fechaobservacion", "fecha_observacion", "fecha"]
COLS_VALOR = ["valorobservado", "valor_observado", "valor"]
COL_SENSOR_DESC = "descripcionsensor"   # p. ej. "NIVEL" (si existe)
COL_UNIDAD = "unidadmedida"             # "cm" / "m" (si existe)
COL_PARAMETRO = "parametro"
COLUMNAS_EXPORTACION = {
    "codigoestacion",
    "nombreestacion",
    "variable",
    "parametro",
    "fecha",
    "unidad",
    "valor",
}

log = logging.getLogger("scraper_ideam")


def normalizar_nombre_columna(nombre: object) -> str:
    texto = unicodedata.normalize("NFKD", str(nombre)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", texto.lower())


def _codigo_normalizado(valor: object) -> str:
    if pd.isna(valor):
        return ""
    texto = str(valor).strip()
    if re.fullmatch(r"\d+\.0+", texto):
        texto = texto.split(".", maxsplit=1)[0]
    return re.sub(r"\D", "", texto).lstrip("0")


def _metadatos_nacional(cabeceras: requests.structures.CaseInsensitiveDict) -> dict[str, str]:
    return {
        "etag": cabeceras.get("ETag", ""),
        "last_modified": cabeceras.get("Last-Modified", ""),
        "content_length": cabeceras.get("Content-Length", ""),
    }


def _estado_nacional_guardado() -> dict[str, str]:
    if not NACIONAL_ESTADO_PATH.exists():
        return {}
    try:
        estado = json.loads(NACIONAL_ESTADO_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("No se pudo leer %s: %s", NACIONAL_ESTADO_PATH.name, exc)
        return {}
    if not isinstance(estado, dict):
        log.warning("El estado guardado de HidrologiaNacionalDiaria no es un objeto JSON.")
        return {}
    return {str(clave): str(valor) for clave, valor in estado.items()}


def _guardar_estado_nacional(estado: dict[str, str]) -> None:
    temporal = NACIONAL_ESTADO_PATH.with_suffix(".json.tmp")
    temporal.write_text(
        json.dumps(estado, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporal.replace(NACIONAL_ESTADO_PATH)


# ───────────────────────────── FUENTES ─────────────────────────────
def _get_json(params: dict) -> list[dict]:
    headers = {"Accept": "application/json"}
    token = os.getenv("SOCRATA_APP_TOKEN")
    if token:
        headers["X-App-Token"] = token
    ultimo_error: Exception | None = None
    for intento in range(1, REINTENTOS + 1):
        try:
            r = requests.get(SOCRATA_URL, params=params, headers=headers, timeout=TIMEOUT_S)
            if r.status_code == 400:      # columna inexistente → que lo maneje el llamador
                raise ValueError(f"HTTP 400: {r.text[:200]}")
            r.raise_for_status()
            return r.json()
        except ValueError:
            raise
        except Exception as exc:  # red, 5xx, JSON inválido…
            ultimo_error = exc
            espera = 2 ** intento
            log.warning("Intento %d/%d falló (%s). Reintento en %ds", intento, REINTENTOS, exc, espera)
            time.sleep(espera)
    raise RuntimeError(f"Socrata no respondió: {ultimo_error}")


def fetch_socrata(desde: date) -> pd.DataFrame:
    """Descarga registros crudos de la estación desde `desde` (00:00) en adelante."""
    errores = []
    for col_est in COLS_ESTACION:
        for col_fecha in COLS_FECHA:
            filas: list[dict] = []
            try:
                for pag in range(MAX_PAGINAS):
                    params = {
                        "$where": f"{col_est}='{ESTACION_CODIGO}' AND {col_fecha} >= '{desde.isoformat()}T00:00:00'",
                        "$order": f"{col_fecha} ASC",
                        "$limit": PAGINA,
                        "$offset": pag * PAGINA,
                    }
                    lote = _get_json(params)
                    filas.extend(lote)
                    if len(lote) < PAGINA:
                        break
            except ValueError as exc:     # columnas incorrectas → probar otra combinación
                errores.append(f"{col_est}/{col_fecha}: {exc}")
                continue
            log.info("Socrata (%s/%s): %d filas crudas", col_est, col_fecha, len(filas))
            return pd.DataFrame(filas)
    raise RuntimeError("Ninguna combinación de columnas funcionó en Socrata: " + " | ".join(errores))


def fetch_hidrologia_nacional(
    _desde: date,
) -> tuple[pd.DataFrame, dict[str, str], bool]:
    """Descarga el archivo nacional solo si cambió desde la última importación."""
    respuesta = requests.head(
        NACIONAL_ZIP_URL,
        headers={"Accept-Encoding": "identity"},
        allow_redirects=True,
        timeout=TIMEOUT_S,
    )
    respuesta.raise_for_status()
    metadatos = _metadatos_nacional(respuesta.headers)
    if not any(metadatos.values()):
        raise RuntimeError("El servidor no informó ETag, Last-Modified ni Content-Length.")

    estado_guardado = _estado_nacional_guardado()
    misma_version = all(
        estado_guardado.get(clave) == valor
        for clave, valor in metadatos.items()
        if valor
    )
    if misma_version and not cargar_historico().empty:
        log.info(
            "HidrologiaNacionalDiaria.zip sin cambios (Last-Modified: %s).",
            metadatos["last_modified"] or "no informado",
        )
        return pd.DataFrame(), metadatos, True

    log.info(
        "Descargando ZIP nacional (%s bytes; Last-Modified: %s).",
        metadatos["content_length"] or "tamaño no informado",
        metadatos["last_modified"] or "no informado",
    )
    ruta_temporal: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix="ideam-hidrologia-",
            suffix=".zip",
            delete=False,
        ) as archivo_temporal:
            ruta_temporal = Path(archivo_temporal.name)
            total = 0
            with requests.get(
                NACIONAL_ZIP_URL,
                headers={"Accept-Encoding": "identity"},
                allow_redirects=True,
                stream=True,
                timeout=(15, 120),
            ) as descarga:
                descarga.raise_for_status()
                metadatos_descarga = _metadatos_nacional(descarga.headers)
                if any(metadatos_descarga.values()):
                    metadatos = {
                        clave: metadatos_descarga[clave] or metadatos[clave]
                        for clave in metadatos
                    }
                for bloque in descarga.iter_content(chunk_size=1024 * 1024):
                    if bloque:
                        archivo_temporal.write(bloque)
                        total += len(bloque)

        if metadatos["content_length"].isdigit():
            esperado = int(metadatos["content_length"])
            if total != esperado:
                raise RuntimeError(
                    f"Descarga incompleta del ZIP nacional: {total} de {esperado} bytes."
                )

        with zipfile.ZipFile(ruta_temporal) as archivo_zip:
            if NACIONAL_MIEMBRO not in archivo_zip.namelist():
                raise ValueError(
                    f"El ZIP nacional no contiene la serie requerida {NACIONAL_MIEMBRO}."
                )
            with archivo_zip.open(NACIONAL_MIEMBRO) as archivo_data:
                datos = pd.read_csv(archivo_data, sep="|")
    finally:
        if ruta_temporal is not None:
            try:
                ruta_temporal.unlink()
            except FileNotFoundError:
                pass

    columnas = {
        normalizar_nombre_columna(columna): columna
        for columna in datos.columns
    }
    if "fecha" not in columnas or "valor" not in columnas:
        raise ValueError(
            f"Columnas inesperadas en {NACIONAL_MIEMBRO}: {list(datos.columns)}"
        )
    if datos.empty:
        raise ValueError(f"La serie {NACIONAL_MIEMBRO} está vacía.")

    fechas = pd.to_datetime(datos[columnas["fecha"]], errors="coerce")
    if fechas.isna().all():
        raise ValueError(f"La serie {NACIONAL_MIEMBRO} no contiene fechas válidas.")
    crudo = pd.DataFrame({
        "codigoestacion": ESTACION_CODIGO_UI,
        "descripcionsensor": "NIVEL",
        "parametro": "Nivel medio diario",
        "fechaobservacion": fechas,
        "unidadmedida": "cm",
        "valorobservado": datos[columnas["valor"]],
    })
    metadatos["fecha_inicio"] = str(fechas.min().date())
    metadatos["fecha_fin"] = str(fechas.max().date())
    log.info(
        "Serie nacional de Calamar: %d filas (%s → %s).",
        len(crudo),
        metadatos["fecha_inicio"],
        metadatos["fecha_fin"],
    )
    return crudo, metadatos, False


def fetch_dhime(desde: date) -> pd.DataFrame:
    """Descarga Nivel medio diario de Calamar desde el portal oficial DHIME."""
    if not DHIME_TERMS_ACCEPTED:
        raise RuntimeError(
            "La descarga DHIME requiere confirmar sus términos. "
            "Defina IDEAM_DHIME_ACCEPT_TERMS=true solo si acepta cumplirlos."
        )

    fecha_fin = date.today()
    fecha_inicio = min(desde, fecha_fin)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(accept_downloads=True)
            page.set_default_timeout(30_000)
            page.goto(DHIME_URL, wait_until="domcontentloaded", timeout=60_000)

            consulta = page.get_by_role("tabpanel", name="Consultar")
            consulta.get_by_role(
                "heading", name="Serie de Tiempo y Frecuencia"
            ).wait_for(state="visible", timeout=60_000)

            aceptacion = page.locator('[data-dojo-attach-point="confirmCheck"]')
            if aceptacion.is_visible():
                casilla = aceptacion.locator(".checkbox")
                if "checked" not in (casilla.get_attribute("class") or ""):
                    casilla.click(force=True)
                page.get_by_text("Aceptar", exact=True).click(force=True)
                aceptacion.wait_for(state="hidden", timeout=30_000)

            consulta.get_by_role(
                "heading", name="Serie de Tiempo y Frecuencia"
            ).wait_for(state="visible", timeout=60_000)
            consulta.get_by_role("radio", name="Estándar").check()

            variable = consulta.get_by_role(
                "row", name="Variable:"
            ).get_by_role("listbox")
            variable.click(force=True)
            page.get_by_role("option", name="Nivel", exact=True).click(force=True)
            consulta.get_by_role(
                "row", name=re.compile("Nivel medio diario", re.IGNORECASE)
            ).get_by_role("radio").check(force=True)

            departamento = consulta.get_by_role(
                "row", name=re.compile("Departamento")
            ).get_by_role("listbox")
            departamento.click(force=True)
            page.get_by_role("option", name="Bolívar", exact=True).click(force=True)
            municipio = consulta.get_by_role(
                "row", name=re.compile("Municipio")
            ).get_by_role("listbox")
            municipio.click(force=True)
            page.get_by_role(
                "option", name="Calamar (Bolívar)", exact=True
            ).click(force=True)

            nombre_estacion = consulta.get_by_role(
                "row", name=re.compile("Nombre o código")
            ).get_by_role("listbox")
            nombre_estacion.click(force=True)
            page.locator(
                'input[aria-owns="nombreEstacion_listbox"]'
            ).fill(ESTACION_CODIGO_UI)
            opciones = page.locator(
                "#nombreEstacion_listbox .k-item"
            ).all_text_contents()
            opcion_calamar = next(
                (
                    opcion for opcion in opciones
                    if ESTACION_CODIGO_UI in opcion and "CALAMAR" in opcion.upper()
                ),
                None,
            )
            if opcion_calamar is None:
                raise RuntimeError(
                    f"DHIME no encontró la estación Calamar {ESTACION_CODIGO_UI}. "
                    f"Opciones visibles: {opciones}"
                )
            page.get_by_role(
                "option", name=opcion_calamar, exact=True
            ).click(force=True)
            consulta.get_by_text("Filtrar", exact=True).click(force=True)

            fila_estacion = consulta.get_by_role(
                "row",
                name=re.compile(
                    rf"^{ESTACION_CODIGO_UI}\s+CALAMAR \[{ESTACION_CODIGO_UI}\]"
                ),
            )
            fila_estacion.wait_for(state="visible")
            fila_estacion.get_by_role("checkbox").check(force=True)

            page.locator("#datepicker").fill(fecha_inicio.strftime("%d/%m/%Y"))
            page.locator("#datepicker").press("Tab")
            page.locator("#datepicker1").fill(fecha_fin.strftime("%d/%m/%Y"))
            page.locator("#datepicker1").press("Tab")
            consulta.get_by_text(
                "Agregar a la Consulta", exact=True
            ).click(force=True)

            page.locator("#OptionCSV").check()
            descargar = page.locator(
                'div.jimu-btn[data-dojo-attach-event="onclick:_Descargar2"]'
            )
            with page.expect_download(timeout=120_000) as descarga_info:
                descargar.click(force=True)
                page.get_by_role("dialog").get_by_role(
                    "button", name="OK"
                ).click(force=True)
            descarga = descarga_info.value
            ruta_zip = descarga.path()
            if ruta_zip is None:
                raise RuntimeError("DHIME no entregó un archivo descargable.")

            if zipfile.is_zipfile(ruta_zip):
                with zipfile.ZipFile(ruta_zip) as archivo:
                    csvs = [
                        nombre for nombre in archivo.namelist()
                        if nombre.lower().endswith(".csv")
                    ]
                    if len(csvs) != 1:
                        raise RuntimeError(
                            "Se esperaba un CSV en la descarga DHIME; "
                            f"se encontraron {len(csvs)}."
                        )
                    csv_bytes = archivo.read(csvs[0])
            else:
                csv_bytes = Path(ruta_zip).read_bytes()
        finally:
            browser.close()

    try:
        crudo = pd.read_csv(BytesIO(csv_bytes), sep=None, engine="python", encoding="utf-8-sig")
    except UnicodeDecodeError:
        crudo = pd.read_csv(BytesIO(csv_bytes), sep=None, engine="python", encoding="latin-1")

    columnas = {
        normalizar_nombre_columna(columna): columna
        for columna in crudo.columns
    }
    col_fecha = next(
        (columnas[c] for c in ("fechaobservacion", "fecha", "date") if c in columnas),
        None,
    )
    col_valor = next(
        (
            columnas[c]
            for c in ("valorobservado", "valor", "nivel", "nivelmedi diario", "nvmediad")
            if c in columnas
        ),
        None,
    )
    if col_fecha is None or col_valor is None:
        raise ValueError(
            "No se reconocieron las columnas de fecha y nivel en el CSV de DHIME. "
            f"Columnas recibidas: {list(crudo.columns)}"
        )

    resultado = pd.DataFrame({
        "fechaobservacion": crudo[col_fecha],
        "valorobservado": crudo[col_valor],
    })
    for destino, candidatas in (
        ("codigoestacion", ("codigoestacion", "codigo")),
        ("nombreestacion", ("nombreestacion", "nombre")),
        (COL_SENSOR_DESC, ("descripcionsensor", "variable")),
        (COL_PARAMETRO, ("parametro",)),
        (COL_UNIDAD, ("unidadmedida", "unidad")),
    ):
        columna = next((columnas[c] for c in candidatas if c in columnas), None)
        if columna is not None:
            resultado[destino] = crudo[columna]
    log.info("DHIME: %d filas descargadas para la estación %s", len(resultado), ESTACION_CODIGO)
    return resultado


# ───────────────────────── IMPORTACIONES LOCALES ────────────────────────
def _leer_csv_exportado(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path, sep=None, engine="python", encoding="utf-8-sig")
    except UnicodeDecodeError:
        return pd.read_csv(path, sep=None, engine="python", encoding="latin-1")


def cargar_exportaciones(directorio: Path = BASE_DIR) -> pd.DataFrame:
    """Lee exportaciones IDEAM CSV/Excel que estén junto al script."""
    columnas_salida = [
        "codigoestacion", "nombreestacion", COL_SENSOR_DESC, COL_PARAMETRO,
        "fechaobservacion", COL_UNIDAD, "valorobservado",
    ]
    tablas: list[pd.DataFrame] = []
    for path in sorted(directorio.iterdir()):
        if path.resolve() == CSV_PATH.resolve() or path.suffix.lower() not in {
            ".csv", ".xls", ".xlsx",
        }:
            continue

        try:
            if path.suffix.lower() == ".csv":
                hojas = [_leer_csv_exportado(path)]
            else:
                hojas = list(pd.read_excel(path, sheet_name=None).values())
        except (
            ImportError,
            OSError,
            ValueError,
            pd.errors.ParserError,
            zipfile.BadZipFile,
        ) as exc:
            log.error("No se pudo leer la exportación %s: %s", path.name, exc)
            continue

        for hoja in hojas:
            columnas = {
                normalizar_nombre_columna(columna): columna
                for columna in hoja.columns
            }
            if not COLUMNAS_EXPORTACION.issubset(columnas):
                continue

            exportacion = pd.DataFrame({
                "codigoestacion": hoja[columnas["codigoestacion"]],
                "nombreestacion": hoja[columnas["nombreestacion"]],
                COL_SENSOR_DESC: hoja[columnas["variable"]],
                COL_PARAMETRO: hoja[columnas["parametro"]],
                "fechaobservacion": hoja[columnas["fecha"]],
                COL_UNIDAD: hoja[columnas["unidad"]],
                "valorobservado": hoja[columnas["valor"]],
            })
            if not exportacion.empty:
                tablas.append(exportacion)
                log.info(
                    "Exportación %s: %d filas crudas importadas",
                    path.name,
                    len(exportacion),
                )

    if not tablas:
        return pd.DataFrame(columns=columnas_salida)
    return pd.concat(tablas, ignore_index=True)


FUENTES = [("dhime", fetch_dhime), ("socrata", fetch_socrata)]


# ───────────────────────────── LIMPIEZA ─────────────────────────────
def _primera_columna(df: pd.DataFrame, candidatas: list[str]) -> str:
    for c in candidatas:
        if c in df.columns:
            return c
    raise KeyError(f"No se encontró ninguna de {candidatas}. Columnas: {list(df.columns)}")


def limpiar_registros(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Devuelve DataFrame con columnas ['Fecha_hora' (datetime), 'Nivel_cm' (float)]."""
    vacio = pd.DataFrame(columns=["Fecha_hora", "Nivel_cm"])
    if df_raw is None or df_raw.empty:
        return vacio

    df = df_raw.copy()
    if "codigoestacion" in df.columns:
        codigos = df["codigoestacion"].map(_codigo_normalizado)
        df = df[codigos == _codigo_normalizado(ESTACION_CODIGO)]
        if df.empty:
            return vacio

    if COL_PARAMETRO in df.columns and df[COL_PARAMETRO].notna().any():
        parametros = df[COL_PARAMETRO].astype("string").str.strip().str.casefold()
        df = df[parametros == "nivel medio diario"]
        if df.empty:
            return vacio

    c_fecha = _primera_columna(df, COLS_FECHA)
    c_valor = _primera_columna(df, COLS_VALOR)

    # Solo la variable NIVEL, si el dataset trae descripción del sensor.
    if COL_SENSOR_DESC in df.columns and df[COL_SENSOR_DESC].notna().any():
        mascara = df[COL_SENSOR_DESC].astype(str).str.contains("NIVEL", case=False, na=False)
        if not mascara.any():
            raise ValueError(
                "El dataset no trae sensores de NIVEL para la estación. "
                f"Valores de {COL_SENSOR_DESC}: {sorted(df[COL_SENSOR_DESC].dropna().unique())[:10]}"
            )
        df = df[mascara]

    valores = pd.to_numeric(df[c_valor], errors="coerce")
    valores = valores.mask(valores.abs() > 1e10)
    out = pd.DataFrame({
        "Fecha_hora": pd.to_datetime(df[c_fecha], errors="coerce"),
        "Nivel_cm": valores,
    })

    # Unidades: si viene en metros, pasar a cm.
    if COL_UNIDAD in df.columns:
        en_metros = df[COL_UNIDAD].astype(str).str.strip().str.lower().isin(["m", "mt", "metros"])
        out.loc[en_metros.values, "Nivel_cm"] *= 100.0

    out = out.replace([float("inf"), float("-inf")], pd.NA).dropna()
    out["Nivel_cm"] = out["Nivel_cm"].astype(float)
    escala_x100 = (
        out["Nivel_cm"].abs().gt(VALOR_MAX_CM)
        & out["Nivel_cm"].abs().le(VALOR_MAX_CM * 100)
    )
    out.loc[escala_x100, "Nivel_cm"] /= 100.0
    total = len(out)
    out = out[(out["Nivel_cm"] >= VALOR_MIN_CM) & (out["Nivel_cm"] <= VALOR_MAX_CM)]
    log.info("Limpieza: %d válidos tras quitar nulos; %d dentro de [%g, %g] cm",
             total, len(out), VALOR_MIN_CM, VALOR_MAX_CM)
    return out.reset_index(drop=True)


def agregar_diario(df: pd.DataFrame) -> pd.DataFrame:
    """Nivel medio diario. Columnas: Fecha, Nivel_cm, Ultima_lectura."""
    if df.empty:
        return pd.DataFrame(columns=["Fecha", "Nivel_cm", "Ultima_lectura"])
    g = df.assign(Fecha=df["Fecha_hora"].dt.strftime("%Y-%m-%d")).groupby("Fecha")
    diario = g.agg(Nivel_cm=("Nivel_cm", "mean"), Ultima_lectura=("Fecha_hora", "max")).reset_index()
    diario["Nivel_cm"] = diario["Nivel_cm"].round(1)
    diario["Ultima_lectura"] = diario["Ultima_lectura"].dt.strftime("%Y-%m-%d %H:%M")
    return diario


# ───────────────────────────── HISTÓRICO ─────────────────────────────
def cargar_historico(path: Path = CSV_PATH) -> pd.DataFrame:
    cols = ["Fecha", "Nivel_cm", "Ultima_lectura"]
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame(columns=cols)
    h = pd.read_csv(path, dtype={"Fecha": str})
    if "Ultima_lectura" not in h.columns:
        h["Ultima_lectura"] = pd.NA
    h["Nivel_cm"] = pd.to_numeric(h["Nivel_cm"], errors="coerce")
    h = h.dropna(subset=["Fecha", "Nivel_cm"])
    # Re-validar el histórico: elimina corruptos que hubiera de corridas previas.
    h = h[(h["Nivel_cm"] >= VALOR_MIN_CM) & (h["Nivel_cm"] <= VALOR_MAX_CM)]
    return h[cols]


def combinar(historico: pd.DataFrame, nuevos: pd.DataFrame) -> pd.DataFrame:
    """Une sin duplicar por Fecha (gana el registro nuevo) y ordena cronológicamente."""
    cols = ["Fecha", "Nivel_cm", "Ultima_lectura"]
    partes = [p for p in (historico[cols], nuevos[cols]) if not p.empty]
    if not partes:
        return pd.DataFrame(columns=cols)
    todo = pd.concat(partes, ignore_index=True)
    todo["Fecha"] = pd.to_datetime(todo["Fecha"], errors="coerce")
    todo = todo.dropna(subset=["Fecha"])
    todo = todo.drop_duplicates(subset="Fecha", keep="last").sort_values("Fecha")
    todo["Fecha"] = todo["Fecha"].dt.strftime("%Y-%m-%d")
    return todo.reset_index(drop=True)


def guardar(df: pd.DataFrame, path: Path = CSV_PATH) -> None:
    df.to_csv(path, index=False, lineterminator="\n")


# ───────────────────────────── MAIN ─────────────────────────────
def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    historico = cargar_historico()
    exportaciones = cargar_exportaciones()
    exportacion_importada = False
    if not exportaciones.empty:
        diario_exportado = agregar_diario(limpiar_registros(exportaciones))
        if not diario_exportado.empty:
            historico = combinar(historico, diario_exportado)
            guardar(historico)
            exportacion_importada = True
            log.info(
                "Histórico local actualizado desde exportaciones IDEAM: %d filas; última fecha %s",
                len(historico),
                historico["Fecha"].iloc[-1],
            )

    dias = DIAS_ACTUALIZACION if not historico.empty else HISTORICO_DIAS
    desde = date.today() - timedelta(days=dias)
    log.info("Estación %s · consultando desde %s (%d días) · histórico: %d filas",
             ESTACION_CODIGO, desde, dias, len(historico))

    nuevos = pd.DataFrame(columns=["Fecha", "Nivel_cm", "Ultima_lectura"])
    alguna_fuente_ok = False
    try:
        crudo_nacional, metadatos_nacionales, sin_cambios = fetch_hidrologia_nacional(desde)
        alguna_fuente_ok = True
        if sin_cambios:
            log.info("No se consulta DHIME: la fuente nacional sigue en la misma versión.")
            return 0

        diario_nacional = agregar_diario(limpiar_registros(crudo_nacional))
        if diario_nacional.empty:
            log.warning("El ZIP nacional no contiene niveles válidos para Calamar.")
        else:
            final = combinar(historico, diario_nacional)
            guardar(final)
            _guardar_estado_nacional(metadatos_nacionales)
            log.info(
                "Guardado %s desde HidrologiaNacionalDiaria.zip: %d filas, última fecha %s",
                CSV_PATH.name,
                len(final),
                final["Fecha"].iloc[-1],
            )
            return 0
    except Exception as exc:
        log.error("Fuente HidrologiaNacionalDiaria falló: %s", exc)

    for nombre, fetch in FUENTES:
        try:
            crudo = fetch(desde)
            alguna_fuente_ok = True
            diario = agregar_diario(limpiar_registros(crudo))
            if diario.empty:
                log.warning("Fuente %s respondió sin registros válidos", nombre)
                continue
            nuevos = diario
            log.info("Fuente %s: %d días válidos (%s → %s)", nombre, len(diario),
                     diario["Fecha"].iloc[0], diario["Fecha"].iloc[-1])
            break
        except NotImplementedError as exc:
            log.info("Fuente %s no disponible: %s", nombre, exc)
        except Exception as exc:
            log.error("Fuente %s falló: %s", nombre, exc)

    if nuevos.empty:
        if historico.empty:
            log.error("Sin datos nuevos y sin histórico: no hay nada que guardar.")
            return 1
        if not alguna_fuente_ok:
            if exportacion_importada:
                log.warning("Ninguna fuente en línea respondió; se conserva el CSV importado.")
                return 0
            log.error("Ninguna fuente respondió. CSV sin cambios.")
            return 1
        if exportacion_importada:
            log.warning("Las fuentes en línea no aportaron filas; se conserva el CSV importado.")
            return 0
        log.warning("El IDEAM no publicó datos válidos nuevos. CSV sin cambios.")
        return 0

    final = combinar(historico, nuevos)
    guardar(final)
    log.info("Guardado %s: %d filas, última fecha %s", CSV_PATH.name, len(final), final["Fecha"].iloc[-1])
    return 0


if __name__ == "__main__":
    sys.exit(main())
