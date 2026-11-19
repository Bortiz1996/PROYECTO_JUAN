"""
app.py — JUAN: nivel del río Magdalena en Calamar (Bolívar)
Tablero ciudadano mobile-first. Datos: IDEAM, estación 29037020 (nivel medio diario, cm).
"""
from __future__ import annotations

import base64
import io
import json
import random
from functools import lru_cache
from itertools import combinations
from pathlib import Path
from statistics import median
from urllib.parse import quote

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import streamlit.components.v1 as components
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ═══════════════════════════ CONFIGURACIÓN ═══════════════════════════
ESTACION_CODIGO = "29037020"
ESTACION_NOMBRE = "Calamar, Bolívar"
ESTACION_LATITUD = 10.243275
ESTACION_LONGITUD = -74.915017
ESTACION_ALTITUD_MSNM = 8
NIVEL_REFERENCIA_CM = 950
NIVEL_MURALLA_CM = 1000
JUAN_ICON_PATH = Path(__file__).parent / "assets" / "juan_icon.png"
JUAN_COVER_PATH = Path(__file__).parent / "assets" / "juan_portada.webp"
CSV_PATH = Path(__file__).with_name("nivel_calamar.csv")
SUBZONAS_CUENCA_PATH = Path(__file__).parent / "assets" / "subzonas_magdalena_cauca.csv"
FEWS_VISOR_URL = "https://fews.ideam.gov.co/visorfews/nacional"
FEWS_NIVEL_URL = "https://fews.ideam.gov.co/visorfews/descargas/SeriesHM_conv.csv"
METEO_URL = "https://api.open-meteo.com/v1/forecast"
METEO_SESSION = requests.Session()
METEO_SESSION.mount(
    "https://",
    HTTPAdapter(
        max_retries=Retry(
            total=2,
            connect=2,
            read=2,
            status=2,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET"}),
        )
    ),
)
METEO_LATITUD = 10.25271
METEO_LONGITUD = -74.91574
METEO_ZONA_HORARIA = "America/Bogota"
HORIZONTE_METEO_HORAS = 24

APP_URL = "https://ing-ambiente-proyect1001.github.io/PROYECTO_JUAN/"

# ── Umbrales de alerta en cm. Solo configurar cotas oficiales verificadas.
UMBRAL_AMARILLA_CM: float | None = None
UMBRAL_NARANJA_CM: float | None = None
UMBRAL_ROJA_CM: float | None = None

DIAS_MAX_SIN_DATOS = 3
PERIODOS_GRAFICA = {
    "Últimos 60 días": 60,
    "Último año": 365,
    "Últimos 5 años": 365 * 5,
    "Todo el histórico": None,
}
# ═════════════════════════════════════════════════════════════════════

MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


# ═══════════════════════════ ESTILOS ═══════════════════════════
def inyectar_estilos() -> None:
    st.markdown(
        """
        <style>
          [data-testid="stAppViewContainer"] {background: #f3f6f8;}
          [data-testid="stHeader"] {background: rgba(243, 246, 248, 0.9);}
          .block-container {padding: 2.4rem 2rem 3rem; max-width: 1120px;}
          h1, h2, h3 {color: #122a3a !important; letter-spacing: -0.035em;}
          h1 {font-size: 2.35rem !important; font-weight: 700 !important; margin-bottom: .15rem !important;}
          h2, h3 {font-weight: 650 !important;}
          [data-testid="stMarkdownContainer"] p,
          [data-testid="stMarkdownContainer"] li {color: #334c5b !important;}
          [data-testid="stMarkdownContainer"] a {color: #075b73 !important;
            text-decoration: underline; text-underline-offset: 2px;}
          [data-testid="stCaptionContainer"],
          [data-testid="stCaptionContainer"] p {color: #405868 !important;}
          [data-testid="stAlert"] {border-radius: 10px;}
          [data-testid="stMetric"] {background: #fff; border: 1px solid #dfe7ec;
            border-radius: 10px; padding: 1rem 1.1rem; min-height: 112px;}
          [data-testid="stMetricLabel"] p {color: #496473 !important; font-size: .78rem;
            font-weight: 700; letter-spacing: .04em; text-transform: uppercase;}
          [data-testid="stMetricValue"] {color: #17384a !important; font-size: 1.55rem;}
          [data-testid="stDownloadButton"] button, [data-testid="stLinkButton"] a {
            border-radius: 8px; font-weight: 600;
          }
          .eyebrow {color: #527080; font-size: .73rem; font-weight: 700;
            letter-spacing: .13em; text-transform: uppercase;}
          .profile-card {position: relative; overflow: hidden; margin: 0 auto 2rem;
            background: #fff; border: 1px solid #dfe7ec; border-radius: 16px;
            box-shadow: 0 8px 26px rgba(20, 45, 60, .06);}
          .profile-cover {position: relative; overflow: hidden; height: 180px; background:
            radial-gradient(ellipse at 18% 120%, rgba(114, 198, 186, .75), transparent 42%),
            radial-gradient(ellipse at 88% 110%, rgba(76, 158, 177, .85), transparent 48%),
            linear-gradient(125deg, #123d53, #087f98 62%, #55a9ad);}
          .profile-cover::before {content: ""; position: absolute; inset: 0;
            background-image: var(--cover-image); background-position: center 58%;
            background-size: cover; opacity: .42;}
          .profile-avatar {position: absolute; top: 104px; left: 50%; width: 144px;
            height: 144px; transform: translateX(-50%); object-fit: cover;
            border: 5px solid #fff; border-radius: 50%;
            box-shadow: 0 4px 14px rgba(20, 45, 60, .18);}
          .profile-content {padding: 78px 24px 24px; text-align: center;}
          .profile-content h1 {display: inline-block; min-width: 250px; box-sizing: border-box;
            color: #fff !important; background: linear-gradient(110deg, #123d53, #087f98 70%, #1b99a4);
            border-radius: 12px; box-shadow: 0 6px 16px rgba(8, 77, 94, .2);
            font-size: 3.2rem !important; font-weight: 900 !important;
            letter-spacing: .1em !important; line-height: 1.05;
            margin: 0 0 .65rem !important; padding: .18em .42em .2em;}
          .profile-content h1::after {content: ""; display: block; width: 32%; height: 3px;
            margin: .1em auto 0; border-radius: 99px; background: #9ee3d6;}
          .profile-content h2 {font-size: 1.35rem !important; margin: .1rem 0 .55rem !important;}
          .profile-content p {color: #405868; margin: 0;}
          .reading-card {background: #fff; border: 1px solid #dfe7ec; border-radius: 14px;
            padding: 1.6rem 1.8rem; box-shadow: 0 8px 26px rgba(20, 45, 60, .06);}
          .reading-value {color: #102b3b; font-size: clamp(3rem, 7vw, 5rem);
            font-weight: 720; letter-spacing: -.06em; line-height: 1.05; margin: .55rem 0 .1rem;}
          .reading-value span {font-size: 1.15rem; font-weight: 600; letter-spacing: 0; color: #607989;}
          .reading-conversion {color: #607989; font-size: 1rem; font-weight: 600;}
          .reading-divider {height: 1px; background: #e6edf1; margin: 1.2rem 0;}
          .reading-detail {color: #536b79; font-size: .92rem; line-height: 1.7;}
          .status-note {background: #edf3f6; border-left: 3px solid #527d91; border-radius: 5px;
            color: #3d5a69; font-size: .88rem; line-height: 1.5; padding: .8rem 1rem;}
          .forecast-note {background: #fff; border: 1px solid #dfe7ec; border-radius: 10px;
            color: #536b79; line-height: 1.55; padding: 1rem 1.15rem;}
          .forecast-caveat {color: #607989; font-size: .8rem; margin-bottom: 0;}
          .weather-card {background: #fff; border: 1px solid #dfe7ec; border-radius: 12px;
            padding: 1rem 1.15rem; display: flex; align-items: center; gap: 1rem;
            box-shadow: 0 4px 16px rgba(20, 45, 60, .05); margin-top: .9rem;}
          .weather-icon {font-size: 2.3rem; line-height: 1; flex-shrink: 0;}
          .weather-body {flex: 1; min-width: 0;}
          .weather-label {color: #527080; font-size: .68rem; font-weight: 700;
            letter-spacing: .12em; text-transform: uppercase; margin-bottom: .15rem;}
          .weather-desc {color: #17384a; font-size: 1.02rem; font-weight: 700; line-height: 1.2;}
          .weather-meta {color: #607989; font-size: .82rem; margin-top: .2rem;}
          @media (max-width: 640px) {
            .block-container {padding: 1.25rem 1rem 2rem;}
            h1 {font-size: 1.8rem !important;}
            .reading-card {padding: 1.2rem;}
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ═══════════════════════════ HELPERS DE FORMATO ═══════════════════════════
def fecha_es(ts: pd.Timestamp, con_hora: bool = False) -> str:
    s = f"{ts.day} {MESES[ts.month - 1]} {ts.year}"
    return f"{s}, {ts:%H:%M}" if con_hora else s


def describir_tiempo(codigo: int) -> str:
    if codigo == 0:
        return "Despejado"
    if codigo == 1:
        return "Mayormente despejado"
    if codigo == 2:
        return "Parcialmente nublado"
    if codigo == 3:
        return "Nublado"
    if codigo in (45, 48):
        return "Neblina"
    if codigo in (51, 53, 55, 56, 57):
        return "Llovizna"
    if codigo in (61, 63, 65, 66, 67):
        return "Lluvia"
    if codigo in (71, 73, 75, 77, 85, 86):
        return "Precipitación sólida"
    if codigo in (80, 81, 82):
        return "Chubascos"
    if codigo in (95, 96, 99):
        return "Tormenta"
    return "Condición variable"


def icono_tiempo(codigo: int | None, noche: bool) -> str:
    """Devuelve un emoji que representa el estado del tiempo."""
    if codigo is None:
        return "🌡️"
    if codigo in (95, 96, 99):
        return "⛈️"
    if codigo in (51, 53, 55, 56, 57):
        return "🌦️"
    if codigo in (61, 63, 65, 66, 67, 80, 81, 82):
        return "🌧️"
    if codigo in (71, 73, 75, 77, 85, 86):
        return "🌨️"
    if codigo in (45, 48):
        return "🌫️"
    if codigo == 3:
        return "☁️"
    if codigo == 2:
        return "🌤️" if not noche else "☁️"
    if codigo == 1:
        return "🌤️" if not noche else "🌙"
    if codigo == 0:
        return "☀️" if not noche else "🌙"
    return "🌡️"


def tipo_ambiente(codigo: int | None) -> str:
    if codigo in (95, 96, 99):
        return "tormenta"
    if codigo in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 71, 73, 75, 77, 80, 81, 82, 85, 86):
        return "lluvia"
    if codigo in (2, 3, 45, 48):
        return "nublado"
    return "despejado"


# ═══════════════════════════ CARGA DE DATOS ═══════════════════════════
@st.cache_data(ttl=900, show_spinner=False)
def cargar_meteorologia() -> dict:
    respuesta = METEO_SESSION.get(
        METEO_URL,
        params={
            "latitude": METEO_LATITUD,
            "longitude": METEO_LONGITUD,
            "current": (
                "temperature_2m,relative_humidity_2m,precipitation,"
                "weather_code,wind_speed_10m"
            ),
            "timezone": METEO_ZONA_HORARIA,
        },
        timeout=(10, 30),
    )
    respuesta.raise_for_status()
    datos = respuesta.json()
    actual = datos.get("current")
    if not isinstance(actual, dict):
        raise ValueError("La respuesta meteorológica no contiene condiciones actuales para Calamar.")

    requeridos = (
        "time", "temperature_2m", "relative_humidity_2m",
        "precipitation", "weather_code", "wind_speed_10m",
    )
    if any(actual.get(clave) is None for clave in requeridos):
        raise ValueError("Faltan variables meteorológicas actuales en la respuesta.")
    return actual


@st.cache_data(ttl=900, show_spinner=False)
def cargar_subzonas_cuenca() -> pd.DataFrame:
    subzonas = pd.read_csv(SUBZONAS_CUENCA_PATH, dtype={"CodigoSubzona": str})
    columnas = {"CodigoSubzona", "Area_km2", "Latitud", "Longitud"}
    if not columnas.issubset(subzonas.columns) or subzonas.empty:
        raise ValueError("Faltan subzonas o columnas válidas para representar la cuenca Magdalena-Cauca.")
    for columna in ("Area_km2", "Latitud", "Longitud"):
        subzonas[columna] = pd.to_numeric(subzonas[columna], errors="coerce")
    if (
        subzonas[list(columnas - {"CodigoSubzona"})].isna().any().any()
        or subzonas["CodigoSubzona"].isna().any()
        or subzonas["CodigoSubzona"].duplicated().any()
        or (subzonas["Area_km2"] <= 0).any()
        or (~subzonas["Latitud"].between(-90, 90)).any()
        or (~subzonas["Longitud"].between(-180, 180)).any()
    ):
        raise ValueError("El archivo de subzonas contiene códigos, áreas o coordenadas inválidas.")
    return subzonas


@st.cache_data(ttl=900, show_spinner=False)
def cargar_pronostico_cuenca(hora_inicio: str) -> pd.DataFrame:
    subzonas = cargar_subzonas_cuenca()
    inicio = pd.to_datetime(hora_inicio, errors="coerce")
    if pd.isna(inicio):
        raise ValueError("La respuesta meteorológica contiene una hora de inicio inválida.")
    fin = inicio + pd.Timedelta(hours=HORIZONTE_METEO_HORAS)

    pronosticos = []
    tamano_lote = 100
    for inicio_lote in range(0, len(subzonas), tamano_lote):
        lote = subzonas.iloc[inicio_lote:inicio_lote + tamano_lote]
        respuesta = METEO_SESSION.get(
            METEO_URL,
            params={
                "latitude": ",".join(f"{lat:.5f}" for lat in lote["Latitud"]),
                "longitude": ",".join(f"{lon:.5f}" for lon in lote["Longitud"]),
                "hourly": "precipitation",
                "forecast_days": 2,
                "timezone": METEO_ZONA_HORARIA,
            },
            timeout=(10, 45),
        )
        respuesta.raise_for_status()
        datos = respuesta.json()
        if isinstance(datos, dict):
            datos = [datos]
        if not isinstance(datos, list) or len(datos) != len(lote):
            raise ValueError("Open-Meteo no devolvió pronósticos para todas las subzonas de la cuenca.")

        for subzona, datos_ubicacion in zip(lote.to_dict("records"), datos):
            por_hora = datos_ubicacion.get("hourly")
            if not isinstance(por_hora, dict):
                raise ValueError(f"Falta el pronóstico horario de la subzona {subzona['CodigoSubzona']}.")
            tiempos = por_hora.get("time")
            precipitacion = por_hora.get("precipitation")
            if not isinstance(tiempos, list) or not isinstance(precipitacion, list) or len(tiempos) != len(precipitacion):
                raise ValueError(f"Las series horarias de la subzona {subzona['CodigoSubzona']} son inválidas.")

            horas = pd.DataFrame({
                "FechaHora": pd.to_datetime(tiempos, errors="coerce"),
                "Precipitacion_mm": pd.to_numeric(precipitacion, errors="coerce"),
            }).dropna(subset=["FechaHora"])
            horas = horas[(horas["FechaHora"] >= inicio) & (horas["FechaHora"] < fin)]
            if (
                len(horas) != HORIZONTE_METEO_HORAS
                or horas["Precipitacion_mm"].isna().any()
                or (horas["Precipitacion_mm"] < 0).any()
            ):
                raise ValueError(
                    f"La subzona {subzona['CodigoSubzona']} no tiene 24 horas válidas de precipitación."
                )
            horas["CodigoSubzona"] = subzona["CodigoSubzona"]
            horas["Area_km2"] = subzona["Area_km2"]
            horas["Lluvia_ponderada"] = horas["Precipitacion_mm"] * horas["Area_km2"]
            pronosticos.append(horas)

    datos_cuenca = pd.concat(pronosticos, ignore_index=True)
    resumen = (
        datos_cuenca.groupby("FechaHora", as_index=False)
        .agg(
            Lluvia_ponderada=("Lluvia_ponderada", "sum"),
            Area_km2=("Area_km2", "sum"),
            Subzonas=("CodigoSubzona", "nunique"),
        )
    )
    if resumen.empty or (resumen["Subzonas"] != len(subzonas)).any():
        raise ValueError("El pronóstico horario no cubre todas las subzonas de la cuenca.")
    resumen["Precipitacion_mm"] = resumen["Lluvia_ponderada"] / resumen["Area_km2"]
    return resumen[["FechaHora", "Precipitacion_mm"]].reset_index(drop=True)


def estimar_tendencia_nivel(niveles: pd.DataFrame) -> tuple[str, str]:
    lecturas = (
        niveles.dropna(subset=["Fecha", "Nivel_cm"])
        .sort_values("Fecha")
        .drop_duplicates("Fecha", keep="last")
    )
    if lecturas.empty:
        return "Sin estimación", "No hay lecturas válidas del nivel del río."

    fecha_ultima = lecturas["Fecha"].iloc[-1]
    ahora = pd.Timestamp.now(tz=METEO_ZONA_HORARIA).tz_localize(None).normalize()
    dias_desactualizado = max((ahora - fecha_ultima.normalize()).days, 0)
    if dias_desactualizado > 2:
        return "Sin estimación", (
            f"La última lectura tiene {dias_desactualizado} días; "
            "no es suficientemente reciente para describir la dirección actual."
        )

    recientes = lecturas[lecturas["Fecha"] >= fecha_ultima - pd.Timedelta(days=3)]
    periodo_dias = (fecha_ultima - recientes["Fecha"].iloc[0]).total_seconds() / 86400
    if len(recientes) < 3 or periodo_dias < 2:
        return "Señal insuficiente", (
            "Se requieren al menos 3 lecturas distribuidas en 2 días para describir "
            "una dirección reciente."
        )

    pendientes = []
    for (_, lectura_a), (_, lectura_b) in combinations(recientes.iterrows(), 2):
        dias_entre = (lectura_b["Fecha"] - lectura_a["Fecha"]).total_seconds() / 86400
        if dias_entre > 0:
            pendientes.append(
                (float(lectura_b["Nivel_cm"]) - float(lectura_a["Nivel_cm"])) / dias_entre
            )
    if not pendientes:
        return "Señal insuficiente", "No hay lecturas con horarios distintos para comparar."

    cambio_diario = median(pendientes)
    if cambio_diario > 0.5:
        direccion = "Alza observada"
    elif cambio_diario < -0.5:
        direccion = "Baja observada"
    else:
        direccion = "Sin cambio claro"
    return direccion, (
        f"Pendiente mediana de {cambio_diario:+.1f} cm/día en {len(recientes)} lecturas "
        "de los últimos 3 días (umbral de dirección: ±0,5 cm/día). "
        "Es una descripción de datos observados, no una predicción."
    )


def limpiar_niveles(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    df["Nivel_cm"] = pd.to_numeric(df["Nivel_cm"], errors="coerce")
    df["Nivel_cm"] = df["Nivel_cm"].replace([float("inf"), float("-inf")], pd.NA)
    df = df.dropna(subset=["Fecha", "Nivel_cm"]).copy()
    df["Nivel_cm"] = df["Nivel_cm"].astype(float)
    escala_x100 = df["Nivel_cm"].abs().gt(2000) & df["Nivel_cm"].abs().le(200_000)
    df.loc[escala_x100, "Nivel_cm"] /= 100
    return df[df["Nivel_cm"].between(0, 2000)].reset_index(drop=True)


@st.cache_data(ttl=1800, show_spinner=False)
def cargar_datos(path: str, mtime: float) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["Fuente"] = "Histórico IDEAM"
    if "Ultima_lectura" in df.columns:
        df["Ultima_lectura"] = pd.to_datetime(df["Ultima_lectura"], errors="coerce")
    else:
        df["Ultima_lectura"] = pd.NaT
    return limpiar_niveles(df).sort_values("Fecha").reset_index(drop=True)


@st.cache_data(ttl=300, show_spinner=False)
def cargar_nivel_fews_calamar() -> pd.DataFrame:
    respuesta = requests.get(
        FEWS_NIVEL_URL,
        headers={"User-Agent": "JUAN-RioCalamar/1.0 (Streamlit; IDEAM FEWS viewer)"},
        timeout=(5, 12),
    )
    respuesta.raise_for_status()
    datos = pd.read_csv(
        io.BytesIO(respuesta.content),
        sep=";",
        dtype={"ID_ESTACION": str},
        encoding="utf-8-sig",
    )

    columnas = {"ID_ESTACION", "FECHA_HORA", "NIVEL_INST"}
    if not columnas.issubset(datos.columns):
        raise ValueError("FEWS devolvió un formato de serie consolidada no reconocido.")
    datos = datos[datos["ID_ESTACION"] == f"00{ESTACION_CODIGO}"].copy()
    datos = datos.rename(columns={"FECHA_HORA": "Fecha", "NIVEL_INST": "Nivel_m"})
    datos["Nivel_m"] = pd.to_numeric(datos["Nivel_m"], errors="coerce")
    datos["Nivel_cm"] = datos["Nivel_m"] * 100
    datos = limpiar_niveles(datos)
    if datos.empty:
        raise ValueError("FEWS no devolvió lecturas válidas de nivel para Calamar.")
    datos["Ultima_lectura"] = datos["Fecha"]
    datos["Fuente"] = "FEWS"
    datos["Consultado_en"] = pd.Timestamp.now()
    return datos.sort_values("Fecha").reset_index(drop=True)


# ═══════════════════════════ UMBRALES ═══════════════════════════
def calcular_umbrales() -> dict:
    oficiales = {
        "amarilla": UMBRAL_AMARILLA_CM,
        "naranja": UMBRAL_NARANJA_CM,
        "roja": UMBRAL_ROJA_CM,
    }
    res, origen = {}, {}
    for k, v in oficiales.items():
        if v is not None:
            res[k], origen[k] = float(v), "oficial"
        else:
            res[k], origen[k] = None, "sin definir"
    return {"valores": res, "origen": origen}


def evaluar(nivel: float, u: dict) -> str:
    v = u["valores"]
    if v["roja"] is not None and nivel >= v["roja"]:
        return "roja"
    if v["naranja"] is not None and nivel >= v["naranja"]:
        return "naranja"
    if v["amarilla"] is not None and nivel >= v["amarilla"]:
        return "amarilla"
    return "verde" if all(x is not None for x in v.values()) else "sin_umbral"


def banner(estado: str) -> None:
    if estado == "verde":
        st.success("Dentro de las cotas oficiales configuradas. Manténgase atento a los avisos de las autoridades.")
    elif estado == "amarilla":
        st.warning("Umbral amarillo oficial alcanzado. Consulte los avisos del Consejo Municipal de Gestión del Riesgo.")
    elif estado == "naranja":
        st.warning("Umbral naranja oficial alcanzado. Siga las instrucciones de las autoridades locales.")
    elif estado == "roja":
        st.error("Umbral rojo oficial alcanzado. Atienda de inmediato las instrucciones de evacuación y autoridades.")
    else:
        st.markdown(
            '<div class="status-note"><strong>Sin cotas oficiales configuradas.</strong> '
            "El medidor muestra la lectura observada; no representa por sí solo un nivel de riesgo.</div>",
            unsafe_allow_html=True,
        )


# ═══════════════════════════ GRÁFICAS ═══════════════════════════
def aplicar_estilo_grafica(fig: go.Figure) -> None:
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#ffffff",
        font=dict(family="Arial, sans-serif", color="#455d6b", size=12),
        showlegend=True,
        legend=dict(
            orientation="h", x=1, y=1.02, xanchor="right", yanchor="bottom",
            font=dict(size=11, color="#455d6b"),
            bgcolor="rgba(255,255,255,0.75)",
        ),
    )
    estilo_ejes = {
        "gridcolor": "#e6ebee", "gridwidth": 0.6, "zeroline": False,
        "showline": True, "linecolor": "#aebbc2", "linewidth": 0.8,
        "ticks": "outside", "tickcolor": "#aebbc2", "tickwidth": 0.8,
        "ticklen": 3, "showticklabels": True,
        "tickfont": dict(size=11, color="#455d6b"), "automargin": True,
    }
    fig.update_xaxes(**estilo_ejes)
    fig.update_yaxes(**estilo_ejes)


def crear_grafica_pronostico_cuenca(horas: pd.DataFrame) -> go.Figure:
    fig = go.Figure(
        go.Scatter(
            x=horas["FechaHora"],
            y=horas["Precipitacion_mm"].cumsum(),
            name="Lluvia acumulada (mm)",
            mode="lines+markers",
            line=dict(color="#167f94", width=1.2),
            marker=dict(size=3),
            fill="tozeroy",
            fillcolor="rgba(22, 127, 148, 0.07)",
            hovertemplate="%{y:.1f} mm<extra></extra>",
        )
    )
    fig.update_layout(height=300, margin=dict(l=64, r=20, t=48, b=40), hovermode="x unified")
    fig.update_xaxes(title_text="Hora local", tickformat="%H:%M", fixedrange=True)
    fig.update_yaxes(title_text="Precipitación media acumulada (mm)", rangemode="tozero", fixedrange=True)
    aplicar_estilo_grafica(fig)
    return fig


def crear_grafica_fews(datos_fews: pd.DataFrame) -> go.Figure:
    fig = go.Figure(
        go.Scatter(
            x=datos_fews["Fecha"],
            y=datos_fews["Nivel_cm"],
            name="Nivel observado FEWS (cm)",
            mode="lines+markers" if len(datos_fews) <= 2000 else "lines",
            line=dict(color="#167f94", width=1.2),
            marker=dict(size=3, color="#167f94"),
            customdata=datos_fews["Fuente"],
            hovertemplate=(
                "<b>%{x|%d %b %Y %H:%M}</b><br>Nivel: <b>%{y:.1f} cm</b>"
                "<br>%{customdata}<extra></extra>"
            ),
        )
    )
    fig.update_layout(
        height=360, margin=dict(l=60, r=20, t=48, b=40),
        hovermode="x", yaxis=dict(title="Nivel observado (cm)"),
    )
    aplicar_estilo_grafica(fig)
    return fig


def crear_grafica_historica(datos_grafica: pd.DataFrame, umbrales: dict) -> go.Figure:
    fig = go.Figure(go.Scatter(
        x=datos_grafica["Fecha"], y=datos_grafica["Nivel_cm"],
        name="Nivel observado (cm)",
        mode="lines",
        line=dict(color="#167f94", width=1.2),
        customdata=datos_grafica[["FechaTxt", "Fuente"]],
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>Nivel: <b>%{y:.1f} cm</b>"
            "<br>Fuente: %{customdata[1]}<extra></extra>"
        ),
    ))
    estilos = {
        "amarilla": ("#d4a017", "Amarilla"),
        "naranja": ("#e8710a", "Naranja"),
        "roja": ("#c62828", "Roja"),
    }
    y_vals = list(datos_grafica["Nivel_cm"])
    for k, (color, nombre) in estilos.items():
        val = umbrales["valores"][k]
        if val is None:
            continue
        y_vals.append(val)
        fig.add_hline(
            y=val, line_dash="dot", line_color=color, line_width=1,
            annotation_text=f"{nombre} {val:.0f} cm",
            annotation_position="top left",
            annotation_font=dict(color=color, size=11),
        )
    y_vals.append(float(NIVEL_REFERENCIA_CM))
    fig.add_hline(
        y=NIVEL_REFERENCIA_CM, line_dash="dash", line_color="#718a98", line_width=1,
        annotation_text="Referencia · 950 cm", annotation_position="top left",
        annotation_font=dict(color="#526b79", size=11),
    )
    rango = max(y_vals) - min(y_vals)
    fig.update_layout(
        height=390, margin=dict(l=60, r=20, t=48, b=40),
        hovermode="x", dragmode=False, hoverlabel=dict(font_size=16),
        xaxis=dict(
            fixedrange=True,
            tickformat="%Y" if (datos_grafica["Fecha"].max() - datos_grafica["Fecha"].min()).days > 365 * 3 else "%d %b",
        ),
        yaxis=dict(
            fixedrange=True, title="Nivel (cm)",
            range=[min(y_vals) - 0.08 * rango, max(y_vals) + 0.12 * rango],
        ),
    )
    aplicar_estilo_grafica(fig)
    return fig


# ═══════════════════════════ VISUALIZACIÓN 3D (PECES) ═══════════════════════════
def _persona_svg(
    camisa: str, pantalon: str, piel: str = "#c68a63",
    camina: bool = False, sentada: bool = False,
) -> str:
    cabeza = (
        f'<circle cx="0" cy="-19" r="3.1" fill="{piel}"/>'
        '<path d="M-3.2 -20.4Q0 -24.2 3.2 -20.4Z" fill="#2b2622"/>'
    )
    torso = f'<rect x="-3.4" y="-16" width="6.8" height="9.6" rx="2.2" fill="{camisa}"/>'
    if sentada:
        return cabeza + torso
    clase = ' class="jn-pierna"' if camina else ""
    piernas = (
        f'<rect{clase} x="-3" y="-7" width="2.8" height="7" rx="1" fill="{pantalon}"/>'
        f'<rect{clase} x=".2" y="-7" width="2.8" height="7" rx="1" fill="{pantalon}"/>'
    )
    return cabeza + torso + piernas


def _ventana_svg(
    x: float, y: float, ancho: float = 12, alto: float = 22, arco: bool = False,
    marco: str = "#2e5b78", vidrio: str = "#4a86a8",
) -> str:
    if arco:
        radio = ancho / 2
        return (
            f'<path d="M{x} {y + alto}V{y + radio}a{radio} {radio} 0 0 1 {ancho} 0V{y + alto}Z" '
            f'fill="{vidrio}" stroke="{marco}" stroke-width="1.3"/>'
        )
    return (
        f'<rect x="{x}" y="{y}" width="{ancho}" height="{alto}" fill="{vidrio}" '
        f'stroke="{marco}" stroke-width="1.3"/>'
        f'<path d="M{x + ancho / 2} {y}v{alto}M{x} {y + alto / 2}h{ancho}" '
        f'stroke="{marco}" stroke-width=".7"/>'
    )


def _bote_svg(x: float, y_agua: float, tipo: str, retraso: float, duracion: float) -> str:
    motor = '<path d="M{0} -1H{1}V8H{0}Z" fill="#23272b"/><path d="M{2} 8V15" stroke="#23272b" stroke-width="2"/>'
    if tipo == "a":
        interior = (
            '<path d="M0 0H44L40 11Q22 14.5 5 11Z" fill="#2f6f9a"/>'
            '<path d="M0 0H44" stroke="#eef3f5" stroke-width="1.8"/>'
            + motor.format(44, 49, 46.5)
        )
    elif tipo == "b":
        interior = (
            f'<g transform="translate(18 7)">{_persona_svg("#f1f1ec", "#555", sentada=True)}</g>'
            f'<g transform="translate(32 7)">{_persona_svg("#e3a23a", "#555", piel="#a8714d", sentada=True)}</g>'
            '<path d="M0 0H62L57 11Q30 15 6 11Z" fill="#3f8f6b"/>'
            '<path d="M0 0H62" stroke="#e9f2ec" stroke-width="1.8"/>'
            + motor.format(62, 67, 64.5)
        )
    else:
        interior = (
            '<path d="M8 0L16 -15L68 -17L78 0Z" fill="#f5f3ec"/>'
            '<path d="M24 -15.5L21 0M40 -16L39 0M56 -16.5L57 0" stroke="#d3d0c4" stroke-width=".9"/>'
            '<path d="M8 0L16 -15M78 0L68 -17" stroke="#6b4b2f" stroke-width="1.4"/>'
            '<path d="M0 0H84L78 11Q42 15 7 11Z" fill="#c65a4b"/>'
            '<path d="M0 0H84" stroke="#f3dfd8" stroke-width="1.8"/>'
            + motor.format(84, 90, 87)
        )
    return (
        f'<g transform="translate({x} {y_agua - 5:.1f})">'
        f'<g class="jn-bote" style="--dur:{duracion}s;--delay:{retraso}s">{interior}</g></g>'
    )


def _vegetacion_ribera_svg(noche: bool) -> str:
    c1 = "#183324" if noche else "#2d5c34"
    c2 = "#21442f" if noche else "#3f7943"
    c3 = "#2b5539" if noche else "#55944f"
    tronco = "#2c241b" if noche else "#5a422b"
    martin = (
        ""
        if noche
        else '<g transform="translate(263 221)">'
        '<ellipse cx="0" cy="-2" rx="3.4" ry="2.6" transform="rotate(-18 0 -2)" fill="#1d6d82"/>'
        '<ellipse cx="-0.4" cy="-0.6" rx="2.1" ry="1.6" fill="#d97b38"/>'
        '<circle cx="2.2" cy="-4.6" r="2.1" fill="#1d6d82"/>'
        '<circle cx="2.9" cy="-4.9" r="0.45" fill="#ffffff"/>'
        '<path d="M4.1 -4.8L8.2 -4.0L4.1 -3.6Z" fill="#232c33"/>'
        '<path d="M-2.6 -0.8L-6.2 1.2L-2.0 0.2Z" fill="#175264"/></g>'
    )
    return (
        '<g aria-hidden="true">'
        f'<path d="M12 241V202M12 215l-9 -9M12 211l11 -7" stroke="{tronco}" stroke-width="2.6" stroke-linecap="round" fill="none"/>'
        f'<circle cx="6" cy="196" r="14" fill="{c1}" opacity=".92"/>'
        f'<circle cx="20" cy="200" r="12" fill="{c2}" opacity=".9"/>'
        f'<circle cx="14" cy="189" r="10" fill="{c3}" opacity=".85"/>'
        f'<path d="M326 244Q322 212 316 188M320 218Q294 211 268 223Q256 228 247 227" stroke="{tronco}" stroke-width="3.2" stroke-linecap="round" fill="none"/>'
        f'<path d="M294 214Q286 205 276 207" stroke="{tronco}" stroke-width="1.6" stroke-linecap="round" fill="none"/>'
        f'<ellipse cx="322" cy="182" rx="26" ry="18" fill="{c1}" opacity=".94"/>'
        f'<ellipse cx="301" cy="192" rx="20" ry="14" fill="{c2}" opacity=".92"/>'
        f'<ellipse cx="332" cy="196" rx="18" ry="13" fill="{c2}" opacity=".92"/>'
        f'<ellipse cx="312" cy="176" rx="15" ry="11" fill="{c3}" opacity=".88"/>'
        f'<ellipse cx="288" cy="201" rx="11" ry="7.5" fill="{c3}" opacity=".85"/>'
        '<g class="jn-junco" style="--dur:6.8s;--delay:-1.2s">'
        f'<path d="M46 254q-2 -14 -5 -24M50 254q1 -16 0 -27M54 254q3 -12 5 -21" stroke="{c2}" stroke-width="1.5" stroke-linecap="round" fill="none"/>'
        '<ellipse cx="50" cy="230" rx="1.4" ry="4" fill="#5e3d24"/></g>'
        '<g class="jn-junco" style="--dur:7.5s;--delay:-3.4s">'
        f'<path d="M286 256q-3 -13 -6 -22M291 256q0 -16 1 -26M296 256q3 -12 5 -20" stroke="{c1}" stroke-width="1.5" stroke-linecap="round" fill="none"/>'
        '<ellipse cx="292" cy="233" rx="1.3" ry="3.8" fill="#5e3d24"/></g>'
        f'{martin}</g>'
    )


def _fauna_orilla_svg(y_agua: float, noche: bool) -> str:
    parts = []
    y_garza = min(358.0, y_agua - 18.0) if y_agua > 365 else (min(295.0, y_agua - 12.0) if y_agua > 258 else None)
    if y_garza is not None:
        plumaje = "#bfd0d6" if noche else "#f6f9fa"
        ala = "#9bb2bc" if noche else "#dce6ea"
        parts.append(
            f'<g transform="translate(308 {y_garza:.1f})"><g class="jn-garza">'
            '<path d="M-1.5 0v-9M1.5 0l.4 -9" stroke="#3c464a" stroke-width="1" stroke-linecap="round"/>'
            f'<ellipse cx="0" cy="-12" rx="5.8" ry="3.4" transform="rotate(-10 0 -12)" fill="{plumaje}"/>'
            f'<ellipse cx="1.2" cy="-11.6" rx="4.2" ry="2.2" transform="rotate(-6 1.2 -11.6)" fill="{ala}"/>'
            f'<path d="M-4.2 -13.5Q-8 -18 -5.8 -23.5Q-4.5 -25.2 -6 -26" fill="none" stroke="{plumaje}" stroke-width="2" stroke-linecap="round"/>'
            f'<circle cx="-6.3" cy="-26.2" r="1.8" fill="{plumaje}"/>'
            '<path d="M-7.8 -26.4L-13.2 -25.4L-7.8 -25.1Z" fill="#d89235"/>'
            '</g></g>'
        )
    if not noche and y_agua > 382:
        y_tortuga = min(375.0, y_agua - 12.0)
        parts.append(
            f'<g transform="translate(88 {y_tortuga:.1f})">'
            '<ellipse cx="0" cy="1.8" rx="8.5" ry="2.4" fill="#464d47" opacity=".45"/>'
            '<path d="M-6 1C-5 -4.2 5 -4.2 6 1Z" fill="#5b663d" stroke="#3c4428" stroke-width=".6"/>'
            '<path d="M-3.5 -1.4h7M-2 -2.6l1 3M2 -2.6l-1 3" stroke="#7d844d" stroke-width=".6" opacity=".7"/>'
            '<path d="M5.4 0.2Q8.2 -1.2 9.4 -0.4Q9.8 0.5 7.4 1Z" fill="#6b7444"/>'
            '<circle cx="8.6" cy="-0.4" r="0.45" fill="#182018"/></g>'
        )
    return "".join(parts)


@lru_cache(maxsize=8)
def _escena_fija_svg(ambiente: str, noche: bool) -> str:
    """Cielo, ciudad, muralla, talud con escalera, enrocado y lecho: no dependen del nivel."""
    rng = random.Random(29037020)
    if noche:
        cielo = ("#111b35", "#233b51", "#425a67")
        color_nube, opacidad_nube = "#a9bac5", (".34", ".28")
    elif ambiente == "tormenta":
        cielo = ("#243847", "#516775", "#8298a1")
        color_nube, opacidad_nube = "#778995", (".98", ".82")
    elif ambiente == "lluvia":
        cielo = ("#526977", "#8399a2", "#b2c2c3")
        color_nube, opacidad_nube = "#d6dee0", (".92", ".78")
    elif ambiente == "nublado":
        cielo = ("#5a8298", "#9eb8c3", "#d0dce0")
        color_nube, opacidad_nube = ("#f4f6f5", (".94", ".8"))
    else:
        cielo = ("#17527c", "#6cb0d3", "#bfe0ee")
        color_nube, opacidad_nube = "#ffffff", (".85", ".7")

    astro = ""
    if noche:
        if ambiente not in ("lluvia", "tormenta"):
            astro = (
                '<g fill="#f3e7ad"><circle cx="277" cy="27" r="1.1"/>'
                '<circle cx="305" cy="53" r=".9"/><circle cx="248" cy="65" r=".8"/>'
                '<circle cx="326" cy="32" r="1.2"/><circle cx="222" cy="37" r=".7"/></g>'
                '<path d="M288 27a10 10 0 1 0 13 13a8 8 0 1 1-13-13Z" fill="#f3e7ad"/>'
            )
    elif ambiente == "despejado":
        astro = (
            '<g fill="#ffe38a" stroke="#fff1bc" stroke-width="1">'
            '<circle cx="286" cy="52" r="10"/><path d="M286 34v-6m0 48v-6m18-18h6m-48 0h6'
            'm31-13 4-4m-34 34 4-4m0-26-4-4m34 34-4-4"/></g>'
        )

    aves = []
    luces_noche = (
        '<g fill="#ffd982" opacity=".95"><rect x="156" y="79" width="8" height="13"/>'
        '<rect x="176" y="105" width="8" height="13"/><rect x="80" y="108" width="5" height="9"/>'
        '<rect x="102" y="108" width="5" height="9"/><rect x="28" y="148" width="6" height="12"/>'
        '<rect x="170" y="138" width="7" height="14"/><rect x="200" y="138" width="7" height="14"/>'
        '</g>'
        if noche else ""
    )

    colores_grava = ("#8f7b5a", "#d3bf96", "#a08d6b", "#6f5f46")
    grava = []
    for _ in range(85):
        color = rng.choice(colores_grava)
        grava.append(
            f'<ellipse cx="{rng.uniform(2, 338):.1f}" cy="{rng.uniform(244, 359):.1f}" '
            f'rx="{rng.uniform(.8, 2.3):.1f}" ry="{rng.uniform(.6, 1.4):.1f}" fill="{color}" opacity=".55"/>'
        )
    hierba = ""
    for _ in range(18):
        hx, hy = rng.uniform(4, 336), rng.uniform(246, 354)
        hierba += f"M{hx:.1f} {hy:.1f}l-2.2 -6.5M{hx:.1f} {hy:.1f}l.2 -7.5M{hx:.1f} {hy:.1f}l2.4 -6"

    tonos_piedra = ("#7e8782", "#919a95", "#6d7671", "#a0a79f", "#868f86")
    piedras = []
    y = 364.0
    while y < 470:
        alto_fila = 11 + rng.random() * 2
        x = -rng.random() * 12
        while x < 340:
            ancho_bloque = 15 + rng.random() * 14
            color = rng.choice(tonos_piedra)
            piedras.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{ancho_bloque - .8:.1f}" '
                f'height="{alto_fila - .8:.1f}" rx="2.2" fill="{color}"/>'
            )
            x += ancho_bloque
        y += alto_fila

    peldanos, dx, dy, x0, y0 = 10, 5.6, 11.2, 172.0, 190.0
    borde = [(x0, y0)]
    for i in range(peldanos):
        borde.append((x0 + (i + 1) * dx, y0 + i * dy))
        borde.append((x0 + (i + 1) * dx, y0 + (i + 1) * dy))
    inferior = [(px, py + 19) for px, py in reversed(borde)]
    puntos_escalera = " ".join(f"{px:.1f},{py:.1f}" for px, py in borde + inferior)
    postes = "".join(f"M{x0 + (i + 1) * dx:.1f} {y0 + i * dy:.1f}v-15" for i in range(0, peldanos, 2))
    xf, yf = x0 + peldanos * dx, y0 + peldanos * dy

    ventanas_blancas = "".join(
        _ventana_svg(x, 138, 14, 20, marco="#cfe0ea", vidrio="#35617b") for x in (166, 196, 226, 256, 286)
    )
    merlones = "".join(f'<rect x="{x}" y="105" width="9" height="10" fill="#c3d8e4"/>' for x in range(156, 336, 15))
    ventanas_amarillo = "".join(
        _ventana_svg(x, 106, 13, 24, marco="#2b5a79", vidrio="#3d7fa5")
        + f'<rect x="{x - 4}" y="106" width="3" height="24" fill="#3b6f95"/>'
        f'<rect x="{x + 14}" y="106" width="3" height="24" fill="#3b6f95"/>'
        for x in (76, 98, 120)
    )
    arcos_amarillo = "".join(
        _ventana_svg(x, 152, 14, 34, arco=True, marco="#7a5a2c", vidrio="#5b4527") for x in (74, 98, 122)
    )
    postes_balcon = "".join(f"M{x} 131v7" for x in range(68, 152, 6))
    postes_verde = "".join(f"M{x} 118v8" for x in range(2, 68, 5))
    ventanas_verde = "".join(
        _ventana_svg(x, 144, 12, 24, arco=True, marco="#d9f1df", vidrio="#2f6a5c") for x in (8, 28, 48)
    )

    return "\n".join([
        '<defs>'
        '<linearGradient id="jn-cielo" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{cielo[0]}"/><stop offset=".55" stop-color="{cielo[1]}"/>'
        f'<stop offset="1" stop-color="{cielo[2]}"/></linearGradient>'
        '<linearGradient id="jn-muro" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#e8e1ce"/><stop offset="1" stop-color="#c2b8a0"/></linearGradient>'
        '<linearGradient id="jn-talud" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#cdb588"/><stop offset="1" stop-color="#8a7656"/></linearGradient>'
        '<linearGradient id="jn-humedad" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#0b1a14" stop-opacity="0"/>'
        '<stop offset="1" stop-color="#0b1a14" stop-opacity=".32"/></linearGradient>'
        '<linearGradient id="jn-lecho" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#8c7658"/><stop offset="1" stop-color="#4c3f31"/></linearGradient>'
        '</defs>',
        '<rect width="340" height="200" fill="url(#jn-cielo)"/>',
        astro,
        '<text x="20" y="27" font-size="12" font-weight="700" letter-spacing="2" fill="#ffffff" '
        'font-family="Arial, sans-serif">NIVEL DEL RÍO</text>',
        '<text x="20" y="42" font-size="9" letter-spacing="1" fill="#dcedf6" '
        f'font-family="Arial, sans-serif">CALAMAR · BOLÍVAR · IDEAM {ESTACION_CODIGO}</text>',
        '<g class="jn-nube" style="--dur:95s;--delay:-34s;--reposo:70px"><g transform="translate(0 68)">'
        f'<ellipse cx="0" cy="0" rx="24" ry="6.5" fill="{color_nube}" opacity="{opacidad_nube[0]}"/>'
        f'<ellipse cx="10" cy="-5" rx="14" ry="7" fill="{color_nube}" opacity="{opacidad_nube[0]}"/>'
        f'<ellipse cx="-11" cy="-3" rx="12" ry="5.5" fill="{color_nube}" opacity="{opacidad_nube[0]}"/></g></g>',
        '<g class="jn-nube" style="--dur:120s;--delay:-80s;--reposo:250px"><g transform="translate(0 94)">'
        f'<ellipse cx="0" cy="0" rx="19" ry="5" fill="{color_nube}" opacity="{opacidad_nube[1]}"/>'
        f'<ellipse cx="8" cy="-4" rx="11" ry="5.5" fill="{color_nube}" opacity="{opacidad_nube[1]}"/></g></g>',
        '<rect x="146" y="64" width="58" height="124" fill="#7c6a63"/>'
        '<rect x="143" y="59" width="64" height="7" fill="#cdc4b5"/>'
        '<path d="M152 70v118M168 70v118M184 70v118M198 70v118" stroke="#000" stroke-opacity=".08" stroke-width="3"/>'
        '<rect x="156" y="78" width="8" height="15" fill="#2b3944"/><rect x="176" y="78" width="8" height="15" fill="#2b3944"/>'
        '<rect x="156" y="104" width="8" height="15" fill="#2b3944"/><rect x="176" y="104" width="8" height="15" fill="#2b3944"/>',
        '<rect x="150" y="122" width="190" height="66" fill="#e8eff2"/>'
        '<rect x="150" y="114" width="190" height="10" fill="#d4e3eb"/>'
        f'{merlones}'
        '<rect x="150" y="124" width="190" height="3" fill="#8db3c8"/>'
        f'{ventanas_blancas}'
        + _ventana_svg(312, 156, 16, 30, arco=True, marco="#cfe0ea", vidrio="#5f8aa0"),
        '<path d="M56 100L96 85H154V94H66Z" fill="#b2533a"/>'
        '<path d="M56 100L96 85" stroke="#7d3724" stroke-width="1.2"/>'
        '<rect x="66" y="94" width="86" height="92" fill="#f2cf45"/>'
        '<rect x="140" y="94" width="12" height="92" fill="#c9a62d" opacity=".55"/>'
        '<rect x="64" y="94" width="90" height="4" fill="#d9b530"/>'
        f'{ventanas_amarillo}'
        '<rect x="64" y="138" width="90" height="3" fill="#b8962a"/>'
        f'<path d="{postes_balcon}M64 131H154" stroke="#9a7c22" stroke-width="1.2" fill="none"/>'
        f'{arcos_amarillo}'
        '<rect x="88" y="146" width="44" height="8" fill="#1f5a4a"/>'
        '<path d="M92 150h12m4 0h8m4 0h6" stroke="#e8f0d8" stroke-width="1.4"/>',
        luces_noche,
        '<rect x="0" y="130" width="68" height="56" fill="#85c6a4"/>'
        '<rect x="0" y="126" width="68" height="5" fill="#e6f0e2"/>'
        '<rect x="0" y="116" width="68" height="2.4" fill="#f2f6ef"/>'
        f'<path d="{postes_verde}" stroke="#f2f6ef" stroke-width="1.5"/>'
        f'{ventanas_verde}'
        '<rect x="0" y="174" width="68" height="12" fill="#6aae8d"/>',
        '<path d="M196 186L205 169H258L267 186Z" fill="#d4673f"/>'
        '<path d="M214 169L211 186M226 169L225 186M238 169L238 186M250 169L252 186" '
        'stroke="#f1d3c3" stroke-width="1.6" opacity=".7"/>'
        '<path d="M82 186L86 175H112L116 186Z" fill="#3b6fb0"/>',
        '<rect x="0" y="186" width="340" height="4" fill="#f1ebdc"/>'
        '<rect x="0" y="190" width="340" height="46" fill="url(#jn-muro)"/>'
        '<path d="M42 190v46M84 190v46M126 190v46M168 190v46M210 190v46M252 190v46M294 190v46" '
        'stroke="#5a4e38" stroke-opacity=".2"/>'
        '<rect x="0" y="231" width="340" height="5" fill="#5a4a30" opacity=".22"/>'
        '<rect x="50" y="197" width="100" height="30" rx="2" fill="#f3efe2" stroke="#d8d0ba"/>'
        '<rect x="50" y="199" width="100" height="6" fill="#c2453a"/>'
        '<rect x="58" y="210" width="46" height="10" rx="1" fill="#2d6b9b" opacity=".85"/>'
        '<path d="M110 212h30M110 217h22" stroke="#9c9786" stroke-width="2"/>'
        '<rect x="0" y="236" width="340" height="5" fill="#a89e88"/>',
        '<rect x="0" y="241" width="340" height="123" fill="url(#jn-talud)"/>'
        '<path d="M60 242q4 30 -2 60q-4 30 4 60M150 242q-4 34 2 66q4 28 -2 54M262 242q5 28 -1 58q-5 32 3 64" '
        'fill="none" stroke="#4f3d22" stroke-opacity=".12" stroke-width="4" stroke-linecap="round"/>'
        '<path d="M0 266Q90 257 170 267T340 262M0 300Q80 292 170 301T340 296M0 334Q90 326 170 335T340 330" '
        'fill="none" stroke="#5e4a2a" stroke-opacity=".2" stroke-width="1.4"/>'
        '<path d="M226 306Q272 297 340 293" fill="none" stroke="#dccba3" stroke-width="5" '
        'stroke-linecap="round" opacity=".55"/>',
        "".join(grava),
        f'<path d="{hierba}" stroke="#4d8a3a" stroke-width="1.1" stroke-linecap="round" fill="none"/>',
        '<text x="46" y="288" font-size="9" font-weight="700" letter-spacing="2" fill="#fff8e6" '
        'opacity=".9" font-family="Arial, sans-serif">TALUD</text>',
        '<rect x="0" y="362" width="340" height="110" fill="#59625d"/>',
        "".join(piedras),
        '<rect x="0" y="360" width="340" height="4" fill="#6d6a5b"/>'
        '<rect x="0" y="400" width="340" height="72" fill="url(#jn-humedad)"/>'
        '<path d="M0 466Q40 459 90 465T200 464T340 461V500H0Z" fill="url(#jn-lecho)"/>'
        '<circle cx="52" cy="482" r="2.4" fill="#b19a78" opacity=".7"/>'
        '<circle cx="171" cy="488" r="3" fill="#a08a69" opacity=".7"/>'
        '<circle cx="268" cy="480" r="2.2" fill="#b19a78" opacity=".7"/>',
        f'<polygon points="{puntos_escalera}" fill="#d6cfba" stroke="#7a7260" stroke-width=".9" stroke-linejoin="round"/>'
        f'<path d="M{x0:.1f} {y0 - 15:.1f}L{xf:.1f} {yf - 15:.1f}{postes}" stroke="#2f414c" '
        'stroke-width="1.5" fill="none" stroke-linecap="round"/>',
        _vegetacion_ribera_svg(noche),
        f'<g opacity="{".45" if noche else ".65"}" aria-hidden="true">'
        '<path d="M58 466q-4 -12 2 -24M62 466q2 -14 -2 -26M66 466q5 -10 1 -20" stroke="#315e43" stroke-width="1.6" stroke-linecap="round" fill="none"/>'
        '<path d="M294 463q-3 -14 2 -25M298 463q4 -12 -1 -22M303 463q5 -10 2 -18" stroke="#2c563d" stroke-width="1.5" stroke-linecap="round" fill="none"/>'
        '</g>',
        "".join(aves),
    ])


def _compactar_html(html: str) -> str:
    return "\n".join(linea.strip() for linea in html.splitlines() if linea.strip())


def _tarullas_svg(y_superficie: float) -> str:
    plantas = []
    for x, escala, demora in ((72, 0.82, 0), (182, 1.0, -1.4), (292, 0.72, -2.2)):
        plantas.append(
            f'<g transform="translate({x} {y_superficie + 2:.1f}) scale({escala})">'
            f'<g class="jn-tarulla" style="--delay:{demora}s">'
            '<path d="M0 5q-5 8 -3 20m3-20q5 9 8 19m-8-19q-1 10 -1 22" '
            'fill="none" stroke="#9ab98a" stroke-width="1" opacity=".8"/>'
            '<ellipse cx="-8" cy="3" rx="8" ry="3.6" transform="rotate(-25 -8 3)" fill="#65a85e"/>'
            '<ellipse cx="0" cy="1" rx="9" ry="3.8" transform="rotate(-8 0 1)" fill="#83bb64"/>'
            '<ellipse cx="9" cy="3" rx="8" ry="3.5" transform="rotate(22 9 3)" fill="#559951"/>'
            '<ellipse cx="-2" cy="8" rx="7" ry="3" transform="rotate(-35 -2 8)" fill="#4d8d4e"/>'
            '<circle cx="2" cy="-2" r="2" fill="#d88aaf"/><circle cx="5" cy="-3" r="1.7" fill="#e7b5ca"/>'
            '</g></g>'
        )
    return "".join(plantas)


# ── CSS y JS del medidor ──
_MEDIDOR_CSS = """
html, body {margin:0; padding:0; background:transparent; font-family:Arial,sans-serif;}
.gauge-feed-wrap {width:min(100%, 340px); margin:0 auto; color:#365462;}
.gauge-panel {position:relative; width:100%; aspect-ratio:340/500; overflow:hidden;
  border-radius:16px; background:#1b5a85; box-shadow:0 8px 26px rgba(20,45,60,.14);}
.gauge-scene,.gauge-overlay {position:absolute; inset:0; display:block; width:100%; height:100%;}
.gauge-scene {z-index:0; touch-action:manipulation;}
.fish-canvas {position:absolute; inset:0; z-index:1; display:block; width:100%; height:100%;
  pointer-events:none;}
.gauge-overlay {z-index:2; pointer-events:none;}
.jn-nube {animation:jn-nube var(--dur) linear infinite; animation-delay:var(--delay);}
@keyframes jn-nube {from {transform:translateX(-100px)} to {transform:translateX(440px)}}
.jn-bote {transform-box:fill-box; transform-origin:center bottom;
  animation:jn-bote var(--dur,7.5s) ease-in-out infinite; animation-delay:var(--delay,0s);}
@keyframes jn-bote {0%,100% {transform:translateY(0) rotate(-.25deg)}
  50% {transform:translateY(-.55px) rotate(.3deg)}}
.jn-respira {animation:jn-respira 4.6s ease-in-out infinite;}
@keyframes jn-respira {0%,100% {transform:translateY(0)} 50% {transform:translateY(-.45px)}}
.jn-garza {transform-box:fill-box; transform-origin:center bottom;
  animation:jn-garza 6.8s ease-in-out infinite;}
@keyframes jn-garza {0%,65%,100% {transform:rotate(0deg)} 80% {transform:rotate(-2.5deg) translateY(.4px)}}
.jn-junco {transform-box:fill-box; transform-origin:center bottom;
  animation:jn-junco var(--dur,6.2s) ease-in-out infinite; animation-delay:var(--delay,0s);}
@keyframes jn-junco {0%,100% {transform:rotate(-1.2deg)} 50% {transform:rotate(1.6deg)}}
.jn-tarulla {transform-box:fill-box; transform-origin:center bottom;
  animation:jn-tarulla 7.4s ease-in-out infinite; animation-delay:var(--delay);}
@keyframes jn-tarulla {0%,100% {transform:translateY(0) rotate(-.7deg)}
  50% {transform:translateY(-.6px) rotate(.8deg)}}
.jn-gota-lluvia {animation:jn-caida .8s linear infinite; animation-delay:var(--delay);}
@keyframes jn-caida {from {transform:translateY(-12px); opacity:0}
  20% {opacity:.8} to {transform:translateY(16px); opacity:0}}
.jn-relampago {animation:jn-relampago 5s steps(1,end) infinite;}
@keyframes jn-relampago {0%,94%,97%,100% {opacity:0} 95%,96% {opacity:.9}}
.btn-feed-inframe {position:absolute; left:13.8%; bottom:8px; z-index:3; padding:3px 9px;
  border-radius:999px; border:1px solid rgba(212,244,250,.42);
  background:rgba(15,44,59,.86); color:#eef8fb; font-family:Arial,sans-serif;
  font-size:11px; font-weight:700; line-height:1.25; cursor:pointer;
  box-shadow:0 2px 6px rgba(10,26,36,.35);
  transition:background .15s ease, transform .12s ease, border-color .15s ease;}
.btn-feed-inframe:hover {background:rgba(22,127,148,.94);
  border-color:rgba(255,255,255,.72);}
.btn-feed-inframe:active {transform:scale(.96);}
@media (prefers-reduced-motion:reduce) {
  .jn-bote,.jn-respira,.jn-garza,.jn-junco,.jn-tarulla,.jn-gota-lluvia,.jn-relampago {
    animation:none;
  }
  .jn-nube {animation:none; transform:translateX(var(--reposo));}
}
"""

_MEDIDOR_SCRIPT = """
<script type="module">
import * as THREE from "https://cdn.jsdelivr.net/npm/three@0.180.0/build/three.module.js";

(() => {
  const panel = document.querySelector(".gauge-panel");
  const svg = document.querySelector(".gauge-scene");
  const canvasInicial = document.querySelector(".fish-canvas");
  const datos = document.querySelector("#fish-data");
  if (!panel || !svg || !canvasInicial || !datos) return;

  const perfiles = JSON.parse(datos.textContent);
  const superficie = Number(svg.dataset.superficie);
  const surfaceSceneY = 250 - superficie;
  const estado = svg.dataset.estadoPeces;
  const ambiente = svg.dataset.ambiente || "despejado";
  const noche = svg.dataset.noche === "true";
  const vientoKmh = Number(svg.dataset.viento || 0);
  const windFactor = Math.min(Math.max(vientoKmh, 0), 45) / 45;
  const isNightVal = noche ? 1.0 : 0.0;
  const isStormVal = ambiente === "tormenta" ? 1.0 : 0.0;
  const isRainVal = (ambiente === "lluvia" || ambiente === "tormenta") ? 1.0 : 0.0;

  const movimiento = {
    calm: {velocidad: 14, amplitud: 0.55, reaccion: 1.0},
    uncomfortable: {velocidad: 21, amplitud: 0.95, reaccion: 1.35},
    scared: {velocidad: 28, amplitud: 1.35, reaccion: 1.7},
  }[estado];
  const reducido = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const paletas = {
    bocachico: {cuerpo: 0xe7b34f, lomo: 0xb86c35, vientre: 0xf6e3b2, aleta: 0xc77a32, raya: 0xa65e30},
    bagre: {cuerpo: 0x79aba2, lomo: 0x376b70, vientre: 0xc9ded2, aleta: 0x4b7f82, raya: 0x426f70},
    mojarra: {cuerpo: 0xe89b5d, lomo: 0x9b5438, vientre: 0xffe3b1, aleta: 0xdf7148, raya: 0xa75e43},
    sabalo: {cuerpo: 0xa7c7c7, lomo: 0x567b88, vientre: 0xedf0dd, aleta: 0x719b9d, raya: 0x638d95},
    doncella: {cuerpo: 0xb3a184, lomo: 0x665543, vientre: 0xead8b9, aleta: 0x806950, raya: 0x665543},
    pacora: {cuerpo: 0xafc7b6, lomo: 0x637c74, vientre: 0xe7e6cc, aleta: 0xcf8b4e, raya: 0x718c7e},
    capaz: {cuerpo: 0x9bb9b4, lomo: 0x526b70, vientre: 0xe8eee1, aleta: 0x758d89, raya: 0x5c7776},
  };

  function createParticleTexture() {
    const size = 32;
    const c = document.createElement("canvas");
    c.width = size;
    c.height = size;
    const ctx = c.getContext("2d");
    const grad = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
    grad.addColorStop(0, "rgba(235, 252, 255, 0.92)");
    grad.addColorStop(0.45, "rgba(180, 238, 245, 0.42)");
    grad.addColorStop(1, "rgba(120, 210, 225, 0.0)");
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, size, size);
    const tex = new THREE.CanvasTexture(c);
    tex.colorSpace = THREE.SRGBColorSpace;
    return tex;
  }

  function createWaterNormalMap(size = 256) {
    const heightField = new Float32Array(size * size);
    const twoPi = Math.PI * 2;
    for (let y = 0; y < size; y++) {
      const v = y / size;
      for (let x = 0; x < size; x++) {
        const u = x / size;
        const h =
          Math.sin(twoPi * (u * 2 + v * 1) + 0.4) * 0.34 +
          Math.cos(twoPi * (u * 3 - v * 2) + 1.1) * 0.25 +
          Math.sin(twoPi * (u * 5 + v * 3) + 2.3) * 0.17 +
          Math.cos(twoPi * (u * 7 - v * 5) + 0.7) * 0.12 +
          Math.sin(twoPi * (u * 11 + v * 7) + 1.9) * 0.07 +
          Math.cos(twoPi * (u * 13 - v * 11)) * 0.05;
        heightField[y * size + x] = h;
      }
    }

    const data = new Uint8Array(size * size * 4);
    const strength = 1.65;
    for (let y = 0; y < size; y++) {
      const yPrev = (y - 1 + size) % size;
      const yNext = (y + 1) % size;
      for (let x = 0; x < size; x++) {
        const xPrev = (x - 1 + size) % size;
        const xNext = (x + 1) % size;

        const dX = (heightField[y * size + xNext] - heightField[y * size + xPrev]) * strength;
        const dY = (heightField[yNext * size + x] - heightField[yPrev * size + x]) * strength;

        const len = Math.hypot(-dX, -dY, 1.0);
        const nx = -dX / len;
        const ny = -dY / len;
        const nz = 1.0 / len;

        const idx = (y * size + x) * 4;
        data[idx] = Math.round((nx * 0.5 + 0.5) * 255);
        data[idx + 1] = Math.round((ny * 0.5 + 0.5) * 255);
        data[idx + 2] = Math.round((nz * 0.5 + 0.5) * 255);
        data[idx + 3] = 255;
      }
    }

    const normalMap = new THREE.DataTexture(
      data,
      size,
      size,
      THREE.RGBAFormat,
      THREE.UnsignedByteType
    );
    normalMap.wrapS = THREE.RepeatWrapping;
    normalMap.wrapT = THREE.RepeatWrapping;
    normalMap.colorSpace = THREE.NoColorSpace;
    normalMap.generateMipmaps = true;
    normalMap.minFilter = THREE.LinearMipmapLinearFilter;
    normalMap.magFilter = THREE.LinearFilter;
    normalMap.needsUpdate = true;
    return normalMap;
  }

  const WATER_VERTEX_SHADER = `
    varying vec2 vUv;
    varying vec2 vScenePos;
    void main() {
      vUv = uv;
      vec4 worldPos = modelMatrix * vec4(position, 1.0);
      vScenePos = worldPos.xy;
      gl_Position = projectionMatrix * viewMatrix * worldPos;
    }
  `;

  const WATER_BACK_FRAGMENT_SHADER = `
    precision highp float;
    uniform float uTime;
    uniform float uSurfaceSceneY;
    uniform float uWindFactor;
    uniform float uNight;
    uniform float uStorm;
    uniform float uRain;
    uniform sampler2D uNormalMap;
    varying vec2 vUv;
    varying vec2 vScenePos;

    float hash(vec2 p) {
      return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123);
    }

    float noise(vec2 p) {
      vec2 i = floor(p);
      vec2 f = fract(p);
      vec2 u = f * f * (3.0 - 2.0 * f);
      return mix(
        mix(hash(i + vec2(0.0, 0.0)), hash(i + vec2(1.0, 0.0)), u.x),
        mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x),
        u.y
      );
    }

    vec3 sampleFlowNormal(vec2 scenePos, float t, float wind) {
      float flowSpeed = 0.017 + wind * 0.013;
      vec2 uv1 = scenePos * vec2(0.0041, 0.0092) - vec2(t * flowSpeed, t * 0.0024);
      vec2 uv2 = scenePos * vec2(0.0067, 0.0138) - vec2(t * (flowSpeed * 1.37), -t * 0.0031);
      vec3 n1 = texture2D(uNormalMap, uv1).xyz * 2.0 - 1.0;
      vec3 n2 = texture2D(uNormalMap, uv2).xyz * 2.0 - 1.0;
      return normalize(vec3(n1.xy * 0.45 + n2.xy * 0.35, 1.0));
    }

    float causticPattern(vec2 p, float t) {
      vec2 p1 = p * vec2(0.029, 0.047) + vec2(-t * 0.14, t * 0.07);
      vec2 p2 = p * vec2(0.041, 0.027) + vec2(t * 0.11, -t * 0.09);
      float w1 = sin(p1.x * 2.7 + sin(p1.y * 2.3 + t * 0.65) * 1.15);
      float w2 = sin(p2.y * 2.9 + sin(p2.x * 2.1 - t * 0.55) * 1.05);
      float ridge = 1.0 - abs(w1 + w2 * 0.72) * 0.52;
      return pow(clamp(ridge, 0.0, 1.0), 3.4);
    }

    vec3 sampleSurfaceReflection(float x, float depth, vec3 flowNormal) {
      float rx = x + flowNormal.x * (8.5 + depth * 0.22);
      float ry = depth * 0.65 + flowNormal.y * 6.0;

      vec3 skyDay = mix(vec3(0.72, 0.87, 0.93), vec3(0.28, 0.57, 0.75), clamp(ry / 95.0, 0.0, 1.0));
      vec3 skyStorm = mix(vec3(0.46, 0.55, 0.60), vec3(0.24, 0.33, 0.39), clamp(ry / 95.0, 0.0, 1.0));
      vec3 skyNight = mix(vec3(0.18, 0.27, 0.34), vec3(0.08, 0.14, 0.24), clamp(ry / 95.0, 0.0, 1.0));
      vec3 reflColor = mix(mix(skyDay, skyStorm, uStorm * 0.85 + uRain * 0.45), skyNight, uNight);

      float bldgMask = smoothstep(-135.0, -90.0, rx) * (1.0 - smoothstep(78.0, 118.0, rx));
      float bldgHeight = 28.0 + sin(rx * 0.045) * 6.0;
      float bldgBand = bldgMask * (1.0 - smoothstep(bldgHeight * 0.65, bldgHeight, ry));
      vec3 bldgDay = mix(vec3(0.74, 0.68, 0.52), vec3(0.55, 0.67, 0.60), step(rx, -98.0));
      vec3 bldgCol = mix(bldgDay, vec3(0.16, 0.22, 0.26), uNight);
      reflColor = mix(reflColor, bldgCol, bldgBand * 0.36);

      float rightVeg = smoothstep(72.0, 128.0, rx);
      float leftVeg = 1.0 - smoothstep(-152.0, -108.0, rx);
      float reedBand = smoothstep(105.0, 145.0, abs(rx)) * 0.55;
      float vegCoverage = clamp(rightVeg + leftVeg + reedBand, 0.0, 1.0);
      float vegDepthReach = 46.0 + vegCoverage * 34.0 + noise(vec2(rx * 0.07, uTime * 0.05)) * 12.0;
      float vegShape = vegCoverage * (1.0 - smoothstep(vegDepthReach * 0.45, vegDepthReach, ry));

      vec3 vegDay = mix(vec3(0.18, 0.42, 0.22), vec3(0.30, 0.54, 0.29), noise(vec2(rx * 0.09, ry * 0.08)));
      vec3 vegNight = vec3(0.08, 0.19, 0.14);
      vec3 vegCol = mix(vegDay, vegNight, uNight);
      reflColor = mix(reflColor, vegCol, vegShape * mix(0.66, 0.42, uStorm));

      return reflColor;
    }

    void main() {
      float x = vScenePos.x;
      float y = vScenePos.y;

      vec3 flowNormal = sampleFlowNormal(vScenePos, uTime, uWindFactor);

      float gentleDrift = uTime * (0.36 + uWindFactor * 0.22);
      float microAmp = 0.22 + uWindFactor * 0.24;
      float undulation =
        sin(x * 0.043 - gentleDrift) * microAmp +
        cos(x * 0.089 + gentleDrift * 0.63) * (microAmp * 0.45) +
        sin(x * 0.023 - gentleDrift * 0.37) * 0.16;
      float surfaceY = uSurfaceSceneY + undulation + flowNormal.y * 0.28;

      float depth = surfaceY - y;
      if (depth < -1.0) discard;
      float surfaceEdge = smoothstep(-0.7, 1.5, depth);

      float waterSpan = max(40.0, surfaceY - (-250.0));
      float normDepth = clamp(depth / waterSpan, 0.0, 1.0);

      vec3 shallowDay = mix(vec3(0.18, 0.60, 0.64), vec3(0.22, 0.51, 0.55), uStorm * 0.75 + uRain * 0.35);
      vec3 midDay     = mix(vec3(0.08, 0.41, 0.49), vec3(0.10, 0.33, 0.40), uStorm * 0.8 + uRain * 0.3);
      vec3 deepDay    = mix(vec3(0.03, 0.19, 0.27), vec3(0.04, 0.15, 0.22), uStorm * 0.8);

      vec3 shallowNight = vec3(0.09, 0.35, 0.43);
      vec3 midNight     = vec3(0.04, 0.20, 0.29);
      vec3 deepNight    = vec3(0.02, 0.10, 0.17);

      vec3 cShallow = mix(shallowDay, shallowNight, uNight);
      vec3 cMid     = mix(midDay, midNight, uNight);
      vec3 cDeep    = mix(deepDay, deepNight, uNight);

      vec3 baseColor = normDepth < 0.45
        ? mix(cShallow, cMid, normDepth / 0.45)
        : mix(cMid, cDeep, (normDepth - 0.45) / 0.55);

      vec3 reflColor = sampleSurfaceReflection(x, depth, flowNormal);
      float fresnelMask = exp(-depth * 0.042) * mix(0.56, 0.34, uStorm) * mix(1.0, 0.72, uNight);
      baseColor = mix(baseColor, reflColor, clamp(fresnelMask, 0.0, 0.62));

      vec3 lightDir = normalize(vec3(-0.35, 0.74, 0.58));
      float ndotl = max(0.0, dot(flowNormal, lightDir));
      float flowSpecular = pow(ndotl, 12.0) * exp(-normDepth * 1.8) * (1.0 - uStorm * 0.65);
      vec3 specTint = mix(vec3(0.84, 0.96, 0.98), vec3(0.45, 0.70, 0.84), uNight);
      baseColor += specTint * flowSpecular * mix(0.14, 0.06, uNight);

      float rayAngleCoord = (x + 170.0) * 0.82 - depth * 0.38 + flowNormal.x * 10.0;
      float ray1 = sin(rayAngleCoord * 0.041 + uTime * 0.19 + noise(vec2(x * 0.018, uTime * 0.08)) * 1.3);
      float ray2 = sin(rayAngleCoord * 0.077 - uTime * 0.13 + 1.7);
      float godRay = pow(clamp(ray1 * 0.55 + ray2 * 0.45, 0.0, 1.0), 2.5);
      float rayAtten = exp(-normDepth * 2.2) * (1.0 - uStorm * 0.74) * (1.0 - uRain * 0.45);
      vec3 rayColor = mix(vec3(0.75, 0.94, 0.96), vec3(0.45, 0.70, 0.85), uNight);
      baseColor += rayColor * godRay * rayAtten * mix(0.15, 0.06, uNight);

      vec2 causticCoord = vec2(x + depth * 0.14, y * 1.25) + flowNormal.xy * 12.0;
      float caust = causticPattern(causticCoord, uTime * (0.55 + uWindFactor * 0.25));
      float caustFade = exp(-normDepth * 2.6) * (1.0 - uStorm * 0.68);
      vec3 caustColor = mix(vec3(0.62, 0.92, 0.92), vec3(0.35, 0.66, 0.80), uNight);
      baseColor += caustColor * caust * caustFade * mix(0.18, 0.08, uNight);

      float turbidity = noise(vec2(x * 0.024 - uTime * 0.14, y * 0.029 + uTime * 0.03));
      baseColor += (turbidity - 0.5) * vec3(0.03, 0.05, 0.04) * (0.5 + 0.5 * normDepth);

      float meniscus = exp(-depth * 0.42);
      vec3 rimColor = mix(vec3(0.86, 0.97, 0.99), vec3(0.54, 0.77, 0.89), uNight);
      baseColor += rimColor * meniscus * 0.14 * (1.0 - uStorm * 0.45);

      if (uRain > 0.1) {
        float splash = pow(noise(vec2(x * 0.33, floor(uTime * 6.0) * 1.7)), 10.0) * meniscus;
        baseColor += vec3(0.75, 0.92, 0.96) * splash * uRain * 0.65;
      }

      float alpha = mix(0.38, 0.73, pow(normDepth, 0.8)) * surfaceEdge;
      alpha = clamp(alpha + meniscus * 0.12, 0.0, 0.82);

      gl_FragColor = vec4(baseColor, alpha);
    }
  `;

  const WATER_FORE_FRAGMENT_SHADER = `
    precision highp float;
    uniform float uTime;
    uniform float uSurfaceSceneY;
    uniform float uWindFactor;
    uniform float uNight;
    uniform float uStorm;
    uniform sampler2D uNormalMap;
    varying vec2 vScenePos;

    float causticLight(vec2 p, float t) {
      vec2 p1 = p * vec2(0.028, 0.044) + vec2(-t * 0.15, t * 0.07);
      vec2 p2 = p * vec2(0.039, 0.027) + vec2(t * 0.12, -t * 0.10);
      float w1 = sin(p1.x * 2.7 + sin(p1.y * 2.2 + t * 0.6) * 1.1);
      float w2 = cos(p2.y * 2.9 - sin(p2.x * 2.0 - t * 0.5) * 1.0);
      return pow(clamp(1.0 - abs(w1 + w2) * 0.56, 0.0, 1.0), 4.0);
    }

    void main() {
      float x = vScenePos.x;
      float y = vScenePos.y;
      float gentleDrift = uTime * (0.36 + uWindFactor * 0.22);
      float microAmp = 0.22 + uWindFactor * 0.24;
      float surfaceY = uSurfaceSceneY + sin(x * 0.043 - gentleDrift) * microAmp;
      float depth = surfaceY - y;
      if (depth < 0.0) discard;

      float waterSpan = max(40.0, surfaceY - (-250.0));
      float normDepth = clamp(depth / waterSpan, 0.0, 1.0);

      float flowSpeed = 0.019 + uWindFactor * 0.015;
      vec2 nUv = vScenePos * vec2(0.005, 0.010) - vec2(uTime * flowSpeed, uTime * 0.003);
      vec2 flowPerturb = texture2D(uNormalMap, nUv).xy * 2.0 - 1.0;

      float c = causticLight(vec2(x + depth * 0.12, y * 1.2) + flowPerturb * 9.0, uTime * 0.6);
      float fade = exp(-normDepth * 2.4) * (1.0 - uStorm * 0.68) * smoothstep(0.0, 4.0, depth);
      float glint = pow(max(0.0, flowPerturb.x * 0.6 + flowPerturb.y * 0.8), 6.0) * exp(-normDepth * 2.1) * 0.05;

      vec3 tint = mix(vec3(0.65, 0.94, 0.98), vec3(0.40, 0.70, 0.86), uNight);
      float intensity = (c * fade * mix(0.10, 0.04, uNight)) + glint;

      gl_FragColor = vec4(tint * intensity, clamp(intensity, 0.0, 0.28));
    }
  `;

  const escena = new THREE.Scene();
  const camara = new THREE.OrthographicCamera(-170, 170, 250, -250, 0.1, 100);
  camara.position.set(0, 0, 50);
  camara.lookAt(0, 0, 0);
  escena.add(new THREE.AmbientLight(noche ? 0x89bfd1 : 0xd8f2f5, noche ? 0.85 : 1.15));
  escena.add(new THREE.HemisphereLight(noche ? 0x5c9db8 : 0x9be4ec, 0x072636, noche ? 0.55 : 0.72));
  const solAgua = new THREE.DirectionalLight(noche ? 0xbcdcf2 : 0xffedc4, noche ? 1.45 : 2.25);
  solAgua.position.set(-80, 120, 110);
  escena.add(solAgua);
  const reflejoAgua = new THREE.PointLight(noche ? 0x4ca6c2 : 0x75e7ed, noche ? 20 : 32, 420);
  reflejoAgua.position.set(95, Math.min(180, surfaceSceneY - 25), 35);
  escena.add(reflejoAgua);

  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({alpha: true, antialias: true});
  } catch (error) {
    console.error("No se pudo iniciar el hábitat 3D del río.", error);
    return;
  }
  renderer.domElement.className = "fish-canvas";
  renderer.domElement.setAttribute("aria-hidden", "true");
  canvasInicial.replaceWith(renderer.domElement);
  renderer.setClearColor(0x000000, 0);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.06;

  const waterNormalMap = createWaterNormalMap(256);
  waterNormalMap.anisotropy = renderer.capabilities.getMaxAnisotropy();
  const waterPlaneGeom = new THREE.PlaneGeometry(340, 500, 1, 1);
  const waterBackUniforms = {
    uTime: {value: 0},
    uSurfaceSceneY: {value: surfaceSceneY},
    uWindFactor: {value: windFactor},
    uNight: {value: isNightVal},
    uStorm: {value: isStormVal},
    uRain: {value: isRainVal},
    uNormalMap: {value: waterNormalMap},
  };
  const waterBackMat = new THREE.ShaderMaterial({
    uniforms: waterBackUniforms,
    vertexShader: WATER_VERTEX_SHADER,
    fragmentShader: WATER_BACK_FRAGMENT_SHADER,
    transparent: true,
    depthWrite: false,
  });
  const waterBackMesh = new THREE.Mesh(waterPlaneGeom, waterBackMat);
  waterBackMesh.position.set(0, 0, -12);
  waterBackMesh.renderOrder = 0;
  escena.add(waterBackMesh);

  const waterForeUniforms = {
    uTime: {value: 0},
    uSurfaceSceneY: {value: surfaceSceneY},
    uWindFactor: {value: windFactor},
    uNight: {value: isNightVal},
    uStorm: {value: isStormVal},
    uNormalMap: {value: waterNormalMap},
  };
  const waterForeMat = new THREE.ShaderMaterial({
    uniforms: waterForeUniforms,
    vertexShader: WATER_VERTEX_SHADER,
    fragmentShader: WATER_FORE_FRAGMENT_SHADER,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });
  const waterForeMesh = new THREE.Mesh(waterPlaneGeom, waterForeMat);
  waterForeMesh.position.set(0, 0, 6);
  waterForeMesh.renderOrder = 3;
  escena.add(waterForeMesh);

  const waterHeightPx = Math.max(10, 466 - superficie);
  const particleCount = 52;
  const particlePositions = new Float32Array(particleCount * 3);
  const particleMeta = new Float32Array(particleCount * 3);
  for (let i = 0; i < particleCount; i++) {
    const px = -170 + ((i * 61.3) % 340);
    const py = 250 - (superficie + 6 + ((i * 41.7) % Math.max(8, waterHeightPx - 10)));
    const pz = i % 3 === 0 ? 2.2 : -4.0 + (i % 5);
    particlePositions[i * 3] = px;
    particlePositions[i * 3 + 1] = py;
    particlePositions[i * 3 + 2] = pz;
    particleMeta[i * 3] = 3.2 + (i % 7) * 1.1;
    particleMeta[i * 3 + 1] = (i * 0.71) % (Math.PI * 2);
    particleMeta[i * 3 + 2] = 0.25 + (i % 4) * 0.25;
  }
  const particleGeom = new THREE.BufferGeometry();
  const particleAttr = new THREE.BufferAttribute(particlePositions, 3);
  particleGeom.setAttribute("position", particleAttr);
  const particleMat = new THREE.PointsMaterial({
    size: 3.1,
    map: createParticleTexture(),
    transparent: true,
    opacity: noche ? 0.16 : 0.26,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    color: noche ? 0x86cde0 : 0xcbf7fc,
  });
  const particlesMesh = new THREE.Points(particleGeom, particleMat);
  particlesMesh.renderOrder = 2;
  escena.add(particlesMesh);

  const pelletGeom = new THREE.SphereGeometry(1, 10, 8);
  const pelletMat = new THREE.MeshStandardMaterial({
    color: 0xe9c46a, emissive: 0x5c420e, roughness: 0.45, metalness: 0.04,
  });
  const fruitGeom = new THREE.DodecahedronGeometry(1, 0);
  const fruitMat = new THREE.MeshStandardMaterial({
    color: 0xf08c3a, emissive: 0x542608, roughness: 0.55, metalness: 0.02,
  });
  const plantGeom = new THREE.SphereGeometry(1, 8, 6);
  plantGeom.scale(1.45, 0.36, 1.0);
  const plantMat = new THREE.MeshStandardMaterial({
    color: 0x6ab04c, emissive: 0x1d4014, roughness: 0.62, metalness: 0.01,
  });
  const bubbleGeom = new THREE.SphereGeometry(1, 8, 6);
  const bubbleMat = new THREE.MeshStandardMaterial({
    color: 0xe6fbff, transparent: true, opacity: 0.58, roughness: 0.1, metalness: 0.1,
  });
  const activeFoods = [];
  const activeBubbles = [];

  function material(color, roughness = 0.43, metalness = 0.02) {
    return new THREE.MeshStandardMaterial({
      color, roughness, metalness, side: THREE.DoubleSide,
    });
  }

  function extruirAleta(puntos, color) {
    const forma = new THREE.Shape();
    forma.moveTo(puntos[0][0], puntos[0][1]);
    for (const [x, y] of puntos.slice(1)) forma.lineTo(x, y);
    forma.closePath();
    const geometria = new THREE.ExtrudeGeometry(forma, {
      depth: 0.16, bevelEnabled: true, bevelSegments: 2,
      bevelSize: 0.035, bevelThickness: 0.035, steps: 1,
    });
    geometria.translate(0, 0, -0.08);
    return new THREE.Mesh(geometria, material(color, 0.62, 0.01));
  }

  function agregarTubo(grupo, puntos, color, radio = 0.24) {
    const curva = new THREE.CatmullRomCurve3(
      puntos.map(([x, y, z]) => new THREE.Vector3(x, y, z))
    );
    const malla = new THREE.Mesh(
      new THREE.TubeGeometry(curva, 12, radio, 5, false),
      material(color, 0.62)
    );
    grupo.add(malla);
  }

  const ojoBlancoMat = material(0xfff8e8, 0.25);
  const pupilaMat = material(0x102a38, 0.15);
  const brilloMat = material(0xffffff, 0.12);
  const ojoGeom = new THREE.SphereGeometry(0.92, 12, 10);
  const pupilaGeom = new THREE.SphereGeometry(0.48, 10, 8);
  const brilloGeom = new THREE.SphereGeometry(0.15, 8, 6);

  function crearPez(perfil, indice) {
    const paleta = paletas[perfil.especie];
    const largo = perfil.largo;
    const alto = perfil.alto;
    const medioLargo = largo * 0.36;
    const medioAlto = alto * 0.40;
    const medioAncho = alto * 0.19;
    const pez = new THREE.Group();
    const cuerpoGeometria = new THREE.SphereGeometry(1, 24, 16);
    const vertices = cuerpoGeometria.attributes.position;
    const originales = new Float32Array(vertices.array.length);
    const colores = new Float32Array(vertices.count * 3);
    const base = new THREE.Color(paleta.cuerpo);
    const lomo = new THREE.Color(paleta.lomo);
    const vientre = new THREE.Color(paleta.vientre);
    const colorVertice = new THREE.Color();

    for (let i = 0; i < vertices.count; i++) {
      const offset = i * 3;
      const nx = vertices.array[offset];
      const ny = vertices.array[offset + 1];
      const nz = vertices.array[offset + 2];
      const estrechamiento = 0.68 + 0.32 * Math.sqrt(Math.max(0, 1 - nx * nx));
      vertices.array[offset] = nx * medioLargo;
      vertices.array[offset + 1] = ny * medioAlto * estrechamiento;
      vertices.array[offset + 2] = nz * medioAncho * estrechamiento;
      originales[offset] = vertices.array[offset];
      originales[offset + 1] = vertices.array[offset + 1];
      originales[offset + 2] = vertices.array[offset + 2];

      if (ny > 0.12) colorVertice.copy(base).lerp(lomo, Math.min(0.82, (ny - 0.12) * 0.9));
      else if (ny < -0.18) colorVertice.copy(base).lerp(vientre, Math.min(0.9, (-ny - 0.18) * 1.1));
      else colorVertice.copy(base);
      colorVertice.toArray(colores, offset);
    }
    cuerpoGeometria.setAttribute("color", new THREE.BufferAttribute(colores, 3));
    cuerpoGeometria.computeVertexNormals();
    const cuerpo = new THREE.Mesh(
      cuerpoGeometria,
      new THREE.MeshStandardMaterial({vertexColors: true, roughness: 0.32, metalness: 0.08})
    );
    cuerpo.position.x = -medioLargo * 0.04;
    pez.add(cuerpo);

    const cabeza = new THREE.Mesh(
      new THREE.SphereGeometry(1, 18, 12),
      material(paleta.cuerpo, 0.34, 0.04)
    );
    cabeza.scale.set(medioLargo * 0.50, medioAlto * 0.72, medioAncho * 0.83);
    cabeza.position.set(medioLargo * 0.57, medioAlto * 0.02, 0);
    pez.add(cabeza);

    for (const lado of [-1, 1]) {
      const ojo = new THREE.Mesh(ojoGeom, ojoBlancoMat);
      ojo.scale.set(0.85, 0.78, 0.38);
      ojo.position.set(medioLargo * 0.76, medioAlto * 0.23, lado * medioAncho * 0.70);
      pez.add(ojo);
      const centroPupila = new THREE.Mesh(pupilaGeom, pupilaMat);
      centroPupila.scale.set(0.9, 0.95, 0.55);
      centroPupila.position.set(
        medioLargo * 0.80, medioAlto * 0.24, lado * (medioAncho * 0.77)
      );
      pez.add(centroPupila);
      const puntoLuz = new THREE.Mesh(brilloGeom, brilloMat);
      puntoLuz.position.set(medioLargo * 0.82, medioAlto * 0.29, lado * medioAncho * 0.82);
      pez.add(puntoLuz);
    }

    const superficieCuerpo = (nx, ny, side = 1) => {
      const t = 0.68 + 0.32 * Math.sqrt(Math.max(0, 1 - nx * nx));
      return [
        nx * medioLargo - medioLargo * 0.04,
        ny * medioAlto * t,
        side * medioAncho * t * Math.sqrt(Math.max(0.02, 1 - nx * nx - ny * ny)) * 1.025,
      ];
    };
    for (const lado of [-1, 1]) {
      agregarTubo(pez, [
        superficieCuerpo(0.42, 0.52, lado),
        superficieCuerpo(0.46, 0, lado),
        superficieCuerpo(0.42, -0.54, lado),
      ], paleta.raya, 0.22);
      agregarTubo(pez, [
        superficieCuerpo(-0.74, 0.02, lado),
        superficieCuerpo(-0.15, 0.02, lado),
        superficieCuerpo(0.38, 0.02, lado),
      ], paleta.lomo, 0.16);
      for (const raya of perfil.rayas) {
        agregarTubo(pez, [
          superficieCuerpo(raya, 0.66, lado),
          superficieCuerpo(raya, 0, lado),
          superficieCuerpo(raya, -0.62, lado),
        ], paleta.raya, 0.34);
      }
    }

    const aletaDorsal = new THREE.Group();
    aletaDorsal.position.set(-medioLargo * 0.02, medioAlto * 0.63, 0);
    aletaDorsal.add(extruirAleta([
      [-largo * 0.16, 0], [-largo * 0.08, alto * 0.40],
      [largo * 0.01, alto * 0.31], [largo * 0.14, 0],
    ], paleta.aleta));
    pez.add(aletaDorsal);

    const aletaAnal = extruirAleta([
      [-largo * 0.16, 0], [-largo * 0.04, -alto * 0.24],
      [largo * 0.10, 0],
    ], paleta.aleta);
    aletaAnal.position.set(-medioLargo * 0.48, -medioAlto * 0.62, medioAncho * 0.2);
    pez.add(aletaAnal);

    const cola = new THREE.Group();
    cola.position.set(-medioLargo * 0.92, 0, 0);
    cola.add(extruirAleta([
      [0, 0], [-largo * 0.25, alto * 0.32],
      [-largo * 0.17, 0], [-largo * 0.25, -alto * 0.32],
    ], paleta.aleta));
    pez.add(cola);

    const pectorales = [];
    for (const lado of [-1, 1]) {
      const pectoral = new THREE.Group();
      pectoral.position.set(medioLargo * 0.05, -medioAlto * 0.07, lado * medioAncho * 0.82);
      pectoral.add(extruirAleta([
        [0, 0], [-largo * 0.15, -alto * 0.29],
        [largo * 0.07, -alto * 0.20],
      ], paleta.aleta));
      pez.add(pectoral);
      pectorales.push(pectoral);
    }

    if (["bagre", "doncella", "capaz"].includes(perfil.especie)) {
      for (const lado of [-1, 1]) {
        agregarTubo(pez, [
          [medioLargo * 0.87, -medioAlto * 0.08, lado * medioAncho * 0.48],
          [medioLargo * 1.04, -medioAlto * 0.24, lado * medioAncho * 0.66],
          [medioLargo * 1.22, -medioAlto * 0.26, lado * medioAncho * 0.78],
        ], paleta.vientre, 0.18);
      }
    }

    const startDir = indice % 3 === 1 ? -1 : 1;
    const pantallaY = 466 - perfil.profundidad / 100 * (466 - superficie);
    const minY = superficie + alto * 0.6 + 8;
    const maxY = 466 - alto * 0.65;
    const y = THREE.MathUtils.clamp(pantallaY, minY, Math.max(minY, maxY));
    const startX = -100 + ((indice * 47) % 210);
    pez.position.set(startX, 250 - y, -1.0 + (indice % 4) * 0.65);
    pez.rotation.y = startDir < 0 ? Math.PI : 0;
    pez.traverse((obj) => { obj.renderOrder = 1; });
    escena.add(pez);

    const schooling = ["bocachico", "mojarra", "sabalo", "pacora"].includes(perfil.especie);
    return {
      group: pez, geometry: cuerpoGeometria, baseVertices: originales,
      vertices: cuerpoGeometria.attributes.position, tail: cola,
      dorsal: aletaDorsal, pectorals: pectorales, species: perfil.especie,
      schooling, preferredDepthNorm: perfil.profundidad / 100,
      height: alto, length: largo, phase: perfil.fase, speedFactor: perfil.velocidad,
      vx: startDir * movimiento.velocidad * perfil.velocidad * 0.85,
      vy: (Math.random() - 0.5) * 2.5,
      yaw: startDir < 0 ? Math.PI : 0, pitch: 0,
      wanderAngle: perfil.fase * Math.PI * 2,
      cruiseMult: 0.85 + Math.random() * 0.3,
      nextDecisionAt: 1.5 + Math.random() * 4.0,
      offscreenUntil: 0, targetFood: null, targetUntil: 0, biteUntil: 0,
    };
  }

  function crearManati() {
    const escala = waterHeightPx < 64 ? 0.65 : waterHeightPx < 95 ? 0.82 : 1.0;
    const largo = 64 * escala;
    const alto = 25 * escala;
    const manati = new THREE.Group();

    const cuerpoGeom = new THREE.SphereGeometry(1, 28, 18);
    const pos = cuerpoGeom.attributes.position;
    const cols = new Float32Array(pos.count * 3);
    const dorsCol = new THREE.Color(0x555c57);
    const midCol = new THREE.Color(0x6d746e);
    const bellyCol = new THREE.Color(0x9b9b8e);
    const tmpC = new THREE.Color();

    const rX = largo * 0.36;
    const rY = alto * 0.45;
    const rZ = alto * 0.37;
    for (let i = 0; i < pos.count; i++) {
      const idx = i * 3;
      const nx = pos.array[idx];
      const ny = pos.array[idx + 1];
      const nz = pos.array[idx + 2];
      const taper = nx < 0 ? 1.0 - 0.42 * (-nx) ** 1.7 : 1.0 - 0.14 * nx * nx;
      const arch = Math.sin((nx + 0.3) * 1.4) * 0.08;
      pos.array[idx] = nx * rX;
      pos.array[idx + 1] = (ny * taper + arch) * rY;
      pos.array[idx + 2] = nz * taper * rZ;

      if (ny > 0.15) tmpC.copy(midCol).lerp(dorsCol, Math.min(1, (ny - 0.15) * 1.2));
      else if (ny < -0.2) tmpC.copy(midCol).lerp(bellyCol, Math.min(1, (-ny - 0.2) * 1.3));
      else tmpC.copy(midCol);
      tmpC.toArray(cols, idx);
    }
    cuerpoGeom.setAttribute("color", new THREE.BufferAttribute(cols, 3));
    cuerpoGeom.computeVertexNormals();
    manati.add(new THREE.Mesh(
      cuerpoGeom,
      new THREE.MeshStandardMaterial({vertexColors: true, roughness: 0.72, metalness: 0.02})
    ));

    const cabeza = new THREE.Mesh(new THREE.SphereGeometry(1, 18, 12), material(0x666d68, 0.72));
    cabeza.scale.set(rX * 0.36, rY * 0.68, rZ * 0.68);
    cabeza.position.set(rX * 0.82, -rY * 0.05, 0);
    manati.add(cabeza);

    const hocico = new THREE.Mesh(new THREE.SphereGeometry(1, 16, 12), material(0x767b74, 0.76));
    hocico.scale.set(rX * 0.24, rY * 0.44, rZ * 0.56);
    hocico.position.set(rX * 1.08, -rY * 0.12, 0);
    manati.add(hocico);

    const narinaGeom = new THREE.SphereGeometry(0.55 * escala, 8, 6);
    const narinaMat = material(0x2d3330, 0.55);
    for (const lado of [-1, 1]) {
      const narina = new THREE.Mesh(narinaGeom, narinaMat);
      narina.position.set(rX * 1.15, rY * 0.24, lado * rZ * 0.18);
      manati.add(narina);
      const ojo = new THREE.Mesh(new THREE.SphereGeometry(0.65 * escala, 8, 6), pupilaMat);
      ojo.position.set(rX * 0.92, rY * 0.14, lado * rZ * 0.58);
      manati.add(ojo);
    }

    const flukeShape = new THREE.Shape();
    flukeShape.moveTo(0, 0);
    flukeShape.bezierCurveTo(-largo * 0.12, alto * 0.36, -largo * 0.30, alto * 0.34, -largo * 0.33, 0);
    flukeShape.bezierCurveTo(-largo * 0.30, -alto * 0.34, -largo * 0.12, -alto * 0.36, 0, 0);
    const flukeGeom = new THREE.ExtrudeGeometry(flukeShape, {
      depth: alto * 0.26, bevelEnabled: true, bevelSegments: 2,
      bevelSize: 0.4 * escala, bevelThickness: 0.4 * escala,
    });
    flukeGeom.translate(0, 0, -alto * 0.13);
    flukeGeom.rotateX(Math.PI * 0.5);
    const cola = new THREE.Group();
    cola.position.set(-rX * 0.88, -rY * 0.02, 0);
    cola.add(new THREE.Mesh(flukeGeom, material(0x5b625d, 0.74)));
    manati.add(cola);

    const flipperShape = new THREE.Shape();
    flipperShape.moveTo(0, 0);
    flipperShape.bezierCurveTo(-largo * 0.08, -alto * 0.36, largo * 0.06, -alto * 0.44, largo * 0.11, -alto * 0.12);
    flipperShape.closePath();
    const flipperGeom = new THREE.ExtrudeGeometry(flipperShape, {
      depth: 0.9 * escala, bevelEnabled: true, bevelSegments: 2,
      bevelSize: 0.25 * escala, bevelThickness: 0.25 * escala,
    });
    flipperGeom.translate(0, 0, -0.45 * escala);
    const pectorales = [];
    for (const lado of [-1, 1]) {
      const aleta = new THREE.Group();
      aleta.position.set(rX * 0.34, -rY * 0.42, lado * rZ * 0.78);
      aleta.add(new THREE.Mesh(flipperGeom, material(0x636a65, 0.74)));
      manati.add(aleta);
      pectorales.push(aleta);
    }

    const midWaterY = surfaceSceneY - waterHeightPx * 0.55;
    manati.position.set(-35, midWaterY, -1.8);
    manati.traverse((obj) => { obj.renderOrder = 1; });
    escena.add(manati);

    return {
      group: manati, tail: cola, pectorals: pectorales,
      x: -35, y: midWaterY, vx: 6.8, vy: 0.3, yaw: 0, pitch: 0,
      length: largo, height: alto, phase: 0.7, wanderAngle: 0.25,
      breatheState: "cruising", breatheUntil: 0,
      nextBreatheAt: 6.5 + Math.random() * 5.0, nextBubbleAt: 0,
      targetFood: null, targetUntil: 0, biteUntil: 0,
    };
  }

  function crearTortuga(indice) {
    const escala = indice === 0 ? 1.0 : 0.85;
    const largo = 22 * escala;
    const alto = 10 * escala;
    const tortuga = new THREE.Group();

    const caparazonGeom = new THREE.SphereGeometry(1, 18, 12, 0, Math.PI * 2, 0, Math.PI * 0.55);
    caparazonGeom.scale(largo * 0.36, alto * 0.56, largo * 0.29);
    const caparazon = new THREE.Mesh(caparazonGeom, material(indice === 0 ? 0x55643b : 0x625a3c, 0.58));
    caparazon.position.set(0, -alto * 0.05, 0);
    tortuga.add(caparazon);

    const bordeGeom = new THREE.TorusGeometry(1, 0.14, 8, 22);
    bordeGeom.rotateX(Math.PI * 0.5);
    bordeGeom.scale(largo * 0.35, 1, largo * 0.28);
    const borde = new THREE.Mesh(bordeGeom, material(0x7c7442, 0.55));
    borde.position.set(0, -alto * 0.05, 0);
    tortuga.add(borde);

    const plastronGeom = new THREE.SphereGeometry(1, 14, 8);
    plastronGeom.scale(largo * 0.33, alto * 0.18, largo * 0.25);
    const plastron = new THREE.Mesh(plastronGeom, material(0xd7cc94, 0.65));
    plastron.position.set(0, -alto * 0.14, 0);
    tortuga.add(plastron);

    const cabezaGrupo = new THREE.Group();
    cabezaGrupo.position.set(largo * 0.34, alto * 0.05, 0);
    const cabezaMesh = new THREE.Mesh(new THREE.SphereGeometry(1, 12, 10), material(0x6c7b48, 0.52));
    cabezaMesh.scale.set(largo * 0.13, alto * 0.26, alto * 0.24);
    cabezaMesh.position.set(largo * 0.08, 0.2, 0);
    cabezaGrupo.add(cabezaMesh);
    for (const lado of [-1, 1]) {
      const ojo = new THREE.Mesh(new THREE.SphereGeometry(0.45 * escala, 8, 6), pupilaMat);
      ojo.position.set(largo * 0.14, alto * 0.10, lado * alto * 0.18);
      cabezaGrupo.add(ojo);
    }
    tortuga.add(cabezaGrupo);

    const aletaTortuga = extruirAleta([
      [0, 0], [-largo * 0.14, -alto * 0.34], [largo * 0.07, -alto * 0.26],
    ], 0x5f6e40);
    const flippers = [];
    for (const [fx, fy, fz] of [
      [largo * 0.17, -alto * 0.1, largo * 0.23],
      [largo * 0.17, -alto * 0.1, -largo * 0.23],
      [-largo * 0.19, -alto * 0.12, largo * 0.20],
      [-largo * 0.19, -alto * 0.12, -largo * 0.20],
    ]) {
      const pivot = new THREE.Group();
      pivot.position.set(fx, fy, fz);
      pivot.add(aletaTortuga.clone());
      tortuga.add(pivot);
      flippers.push(pivot);
    }

    const startDir = indice === 0 ? -1 : 1;
    const prefDepth = indice === 0 ? 0.26 : 0.62;
    const startY = surfaceSceneY - waterHeightPx * prefDepth;
    const startX = indice === 0 ? 75 : -75;
    tortuga.position.set(startX, startY, indice === 0 ? 0.6 : -0.8);
    tortuga.rotation.y = startDir < 0 ? Math.PI : 0;
    tortuga.traverse((obj) => { obj.renderOrder = 1; });
    escena.add(tortuga);

    return {
      group: tortuga, flippers, head: cabezaGrupo,
      x: startX, y: startY, vx: startDir * 7.5, vy: 0,
      yaw: startDir < 0 ? Math.PI : 0, pitch: 0,
      length: largo, phase: indice * 2.1 + 0.4, wanderAngle: indice * 1.7,
      preferredDepthNorm: prefDepth, surfaceUntil: 0,
      nextSurfaceAt: 8 + indice * 6 + Math.random() * 6,
      targetFood: null, targetUntil: 0, biteUntil: 0,
    };
  }

  const peces = perfiles.map(crearPez);
  const manatee = waterHeightPx > 52 ? crearManati() : null;
  const turtles = waterHeightPx > 46
    ? [crearTortuga(0), ...(waterHeightPx > 82 ? [crearTortuga(1)] : [])]
    : [];

  const limiteInferior = 466;
  const bottomSceneY = 250 - limiteInferior;
  const intensidadMovimiento = reducido ? 0.25 : 1;

  const boatZones = noche ? [] : [
    {x: 64 - 170, halfW: 24, depth: 18},
    {x: 128 - 170, halfW: 32, depth: 18},
    {x: 204 - 170, halfW: 44, depth: 20},
  ];
  const tarullaZones = [72 - 170, 182 - 170, 292 - 170];

  function redimensionar() {
    const caja = panel.getBoundingClientRect();
    if (!caja.width || !caja.height) return;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(caja.width, caja.height, false);
  }
  if (window.ResizeObserver) new ResizeObserver(redimensionar).observe(panel);
  else window.addEventListener("resize", redimensionar);
  redimensionar();

  function shortestAngleDelta(target, current) {
    return Math.atan2(Math.sin(target - current), Math.cos(target - current));
  }

  let tiempoPrevio = performance.now();
  let tiempo = 0;

  function spawnBreathBubble(bx, by) {
    const mesh = new THREE.Mesh(bubbleGeom, bubbleMat);
    mesh.scale.setScalar(1.0 + Math.random() * 0.9);
    mesh.position.set(bx, by, 1.5);
    mesh.renderOrder = 2;
    escena.add(mesh);
    activeBubbles.push({
      mesh, x: bx, y: by, z: 1.5,
      vy: 14 + Math.random() * 8,
      vx: 2.2 + (Math.random() - 0.5) * 3.0,
      phase: Math.random() * Math.PI * 2,
      bornAt: tiempo, life: 1.2 + Math.random() * 0.9,
    });
  }

  function animar(marca) {
    requestAnimationFrame(animar);
    const delta = Math.min((marca - tiempoPrevio) / 1000, 0.04);
    tiempoPrevio = marca;
    tiempo += delta;
    const potencia = movimiento.amplitud * (reducido ? 0.2 : 1);

    const shaderTime = reducido ? 0 : tiempo;
    waterBackUniforms.uTime.value = shaderTime;
    waterForeUniforms.uTime.value = shaderTime;
    reflejoAgua.intensity = (noche ? 19 : 30) + Math.sin(shaderTime * 1.1) * (noche ? 2 : 3.5);

    if (!reducido) {
      const pArr = particleAttr.array;
      const maxParticleY = surfaceSceneY - 5;
      const minParticleY = -216;
      for (let i = 0; i < particleCount; i++) {
        const i3 = i * 3;
        const speed = particleMeta[i3];
        const phase = particleMeta[i3 + 1];
        const bob = particleMeta[i3 + 2];
        let px = pArr[i3] + speed * delta * (0.65 + windFactor * 0.45);
        if (px > 174) px -= 348;
        let py = pArr[i3 + 1] + (Math.sin(tiempo * 0.9 + phase) * 0.8 + bob * 0.4) * delta;
        if (py > maxParticleY) py = minParticleY + 4;
        pArr[i3] = px;
        pArr[i3 + 1] = py;
      }
      particleAttr.needsUpdate = true;
    }

    for (let i = activeBubbles.length - 1; i >= 0; i--) {
      const b = activeBubbles[i];
      if (tiempo - b.bornAt >= b.life || b.y >= surfaceSceneY) {
        escena.remove(b.mesh);
        activeBubbles.splice(i, 1);
        continue;
      }
      b.x += (b.vx + Math.sin(tiempo * 5.0 + b.phase) * 2.5) * delta;
      b.y += b.vy * delta;
      b.mesh.position.set(b.x, b.y, b.z);
    }

    const foodFloorY = bottomSceneY + 3;
    const riverCurrentVx = 3.8 + windFactor * 2.8;
    for (let i = activeFoods.length - 1; i >= 0; i--) {
      const food = activeFoods[i];
      if (food.eaten || tiempo >= food.fadeAt) {
        escena.remove(food.mesh);
        activeFoods.splice(i, 1);
        continue;
      }
      if (tiempo < food.releaseAt) {
        food.mesh.visible = false;
        continue;
      }
      food.mesh.visible = true;
      if (!food.settled) {
        if (food.y > surfaceSceneY) {
          food.vy -= 260 * food.gravityScale * delta;
        } else {
          if (!food.inWater) {
            food.inWater = true;
            food.vy *= 0.34;
          }
          if (food.kind === "plant") {
            const floatTargetY = surfaceSceneY - 2.4 + Math.sin(tiempo * 1.4 + food.phase) * 0.8;
            food.vy += (floatTargetY - food.y) * 9.0 * delta;
            food.vy *= Math.exp(-4.2 * delta);
            food.x += (food.vx + riverCurrentVx * 0.85) * delta;
            food.mesh.rotation.z = Math.sin(tiempo * 1.6 + food.phase) * 0.25;
          } else if (food.kind === "fruit") {
            const soak = Math.max(0, (tiempo - food.releaseAt - 2.8) * 0.28);
            const sinkForce = (soak - food.buoyancy) * 32.0;
            food.vy += sinkForce * delta;
            food.vy *= Math.exp(-2.6 * delta);
            food.x += (food.vx * 0.6 + riverCurrentVx * 0.65) * delta;
            food.mesh.rotation.x += 0.6 * delta;
            food.mesh.rotation.y += 0.8 * delta;
          } else {
            food.vy -= 56 * food.gravityScale * delta;
            food.vy *= Math.exp(-1.7 * delta);
            food.x += (food.vx + riverCurrentVx * 0.35 + Math.sin(tiempo * 1.7 + food.phase) * 1.4) * delta;
          }
          if (food.x > 165) {
            food.eaten = true;
            continue;
          }
          food.x = THREE.MathUtils.clamp(food.x, -124, 165);
        }
        food.y += food.vy * delta;
        if (food.y <= foodFloorY) {
          food.y = foodFloorY;
          food.vy = 0;
          food.settled = true;
          food.fadeAt = Math.min(food.fadeAt, tiempo + 3.2);
        }
      }
      food.mesh.position.set(food.x, food.y, food.z);
    }

    const availableFoods = activeFoods.filter((f) => !f.eaten && tiempo >= f.releaseAt);
    const consumeFood = (f) => {
      f.bitesLeft -= 1;
      if (f.bitesLeft <= 0) f.eaten = true;
      else f.mesh.scale.multiplyScalar(0.68);
    };

    if (manatee) {
      const mMinY = bottomSceneY + manatee.height * 0.65 + 4;
      const mMaxSurfY = surfaceSceneY - manatee.height * 0.48;
      const breathSurfY = surfaceSceneY - 2.0;

      if (
        manatee.targetFood &&
        (manatee.targetFood.eaten || tiempo >= manatee.targetFood.fadeAt || tiempo >= manatee.targetUntil)
      ) {
        manatee.targetFood = null;
      }
      if (!manatee.targetFood && manatee.breatheState === "cruising" && availableFoods.length > 0 && tiempo >= manatee.biteUntil) {
        let bestF = null;
        let bestScore = Infinity;
        for (const f of availableFoods) {
          if (f.eaten) continue;
          const d = Math.hypot(f.x - manatee.x, f.y - manatee.y);
          const pref = f.kind === "plant" ? 0.55 : f.kind === "fruit" ? 0.72 : 1.35;
          if (d * pref < bestScore && d < 220) {
            bestScore = d * pref;
            bestF = f;
          }
        }
        if (bestF) {
          manatee.targetFood = bestF;
          manatee.targetUntil = tiempo + 9.0;
        }
      }

      const mDirSign = Math.cos(manatee.yaw) >= 0 ? 1 : -1;
      const mMouthX = manatee.x + mDirSign * manatee.length * 0.36;
      for (const f of availableFoods) {
        if (f.eaten) continue;
        if (Math.hypot(f.x - mMouthX, f.y - manatee.y) < 13.5) {
          consumeFood(f);
          manatee.targetFood = null;
          manatee.biteUntil = tiempo + 0.65;
          break;
        }
      }

      if (manatee.breatheState === "cruising" && tiempo >= manatee.nextBreatheAt && !manatee.targetFood) {
        manatee.breatheState = "ascending";
      }

      let desiredVx = manatee.vx;
      let desiredVy = manatee.vy;
      const cruiseSpeed = 6.8 * intensidadMovimiento;

      if (manatee.breatheState === "ascending") {
        const targetY = Math.max(mMinY, breathSurfY - manatee.height * 0.12);
        const dir = Math.cos(manatee.yaw) >= 0 ? 1 : -1;
        desiredVx = dir * cruiseSpeed * 0.55;
        desiredVy = THREE.MathUtils.clamp((targetY - manatee.y) * 0.75, 1.5, 5.2);
        if (manatee.y >= targetY - 2.0) {
          manatee.breatheState = "breathing";
          manatee.breatheUntil = tiempo + 1.8 + Math.random() * 0.9;
          manatee.nextBubbleAt = tiempo + 0.15;
        }
      } else if (manatee.breatheState === "breathing") {
        const dir = Math.cos(manatee.yaw) >= 0 ? 1 : -1;
        desiredVx = dir * cruiseSpeed * 0.28;
        desiredVy = (breathSurfY - manatee.height * 0.12 - manatee.y) * 1.4;
        if (!reducido && tiempo >= manatee.nextBubbleAt && activeBubbles.length < 18) {
          spawnBreathBubble(manatee.x + dir * manatee.length * 0.38, surfaceSceneY - 2.5);
          manatee.nextBubbleAt = tiempo + 0.75 + Math.random() * 0.45;
        }
        if (tiempo >= manatee.breatheUntil) {
          manatee.breatheState = "descending";
          manatee.breatheUntil = tiempo + 3.2;
        }
      } else if (manatee.breatheState === "descending") {
        const dir = Math.cos(manatee.yaw) >= 0 ? 1 : -1;
        const midY = surfaceSceneY - waterHeightPx * 0.55;
        desiredVx = dir * cruiseSpeed * 0.85;
        desiredVy = THREE.MathUtils.clamp((midY - manatee.y) * 0.55, -4.5, -1.2);
        if (tiempo >= manatee.breatheUntil || manatee.y <= midY + 4) {
          manatee.breatheState = "cruising";
          manatee.nextBreatheAt = tiempo + 13 + Math.random() * 9;
        }
      } else if (manatee.targetFood && !manatee.targetFood.eaten) {
        const dx = manatee.targetFood.x - manatee.x;
        const dy = Math.min(manatee.targetFood.y, mMaxSurfY) - manatee.y;
        const dist = Math.max(1, Math.hypot(dx, dy));
        desiredVx = (dx / dist) * cruiseSpeed * 1.15;
        desiredVy = (dy / dist) * cruiseSpeed * 1.15;
      } else {
        manatee.wanderAngle += (Math.sin(tiempo * 0.23 + 1.1) * 0.35 + Math.cos(tiempo * 0.14) * 0.2) * delta;
        const prefY = surfaceSceneY - waterHeightPx * (0.52 + Math.sin(tiempo * 0.11 + 0.7) * 0.16);
        desiredVx = Math.cos(manatee.wanderAngle) * cruiseSpeed;
        desiredVy = Math.sin(manatee.wanderAngle) * cruiseSpeed * 0.28 + (prefY - manatee.y) * 0.22;
      }

      if (manatee.x < -98) desiredVx += (-98 - manatee.x) * 0.45;
      if (manatee.x > 125) desiredVx += (125 - manatee.x) * 0.45;
      if (manatee.y < mMinY) desiredVy += (mMinY - manatee.y) * 0.8;
      if (manatee.breatheState === "cruising" && manatee.y > mMaxSurfY) {
        desiredVy -= (manatee.y - mMaxSurfY) * 0.8;
      }

      manatee.vx = THREE.MathUtils.damp(manatee.vx, desiredVx, 1.35, delta);
      manatee.vy = THREE.MathUtils.damp(manatee.vy, desiredVy, 1.6, delta);
      manatee.x += manatee.vx * delta;
      manatee.y = THREE.MathUtils.clamp(manatee.y + manatee.vy * delta, mMinY - 2, surfaceSceneY - 1.5);

      const mTargetYaw = manatee.vx < -0.6 ? Math.PI : 0;
      const mTargetPitch = Math.atan2(manatee.vy, Math.max(3.5, Math.abs(manatee.vx))) *
        (manatee.breatheState === "breathing" ? 0.35 : 0.65);
      manatee.yaw += shortestAngleDelta(mTargetYaw, manatee.yaw) * Math.min(1, delta * 1.6);
      manatee.pitch += shortestAngleDelta(mTargetPitch, manatee.pitch) * Math.min(1, delta * 2.0);
      manatee.group.position.set(manatee.x, manatee.y, -1.8);
      manatee.group.rotation.y = manatee.yaw;
      manatee.group.rotation.z = manatee.pitch;

      const mSpeed = Math.hypot(manatee.vx, manatee.vy);
      const mBeat = tiempo * (1.25 + mSpeed * 0.08) + manatee.phase;
      manatee.tail.rotation.z = Math.sin(mBeat) * (reducido ? 0.06 : 0.22);
      manatee.pectorals.forEach((aleta, idx) => {
        aleta.rotation.x = Math.sin(mBeat * 0.85 + idx * 0.8) * (reducido ? 0.05 : 0.16);
        aleta.rotation.z = Math.cos(mBeat * 0.85 + idx * 0.8) * (reducido ? 0.03 : 0.11);
      });
    }

    for (const turtle of turtles) {
      const tMinY = bottomSceneY + 11;
      const tMaxY = surfaceSceneY - 4;
      if (turtle.targetFood && (turtle.targetFood.eaten || tiempo >= turtle.targetFood.fadeAt || tiempo >= turtle.targetUntil)) {
        turtle.targetFood = null;
      }
      if (!turtle.targetFood && availableFoods.length > 0 && tiempo >= turtle.biteUntil) {
        let bestF = null;
        let bestScore = Infinity;
        for (const f of availableFoods) {
          if (f.eaten) continue;
          const d = Math.hypot(f.x - turtle.x, f.y - turtle.y);
          const pref = f.kind === "plant" ? 0.6 : f.kind === "fruit" ? 0.7 : 1.25;
          if (d * pref < bestScore && d < 210) {
            bestScore = d * pref;
            bestF = f;
          }
        }
        if (bestF) {
          turtle.targetFood = bestF;
          turtle.targetUntil = tiempo + 7.5;
        }
      }

      const tDirSign = Math.cos(turtle.yaw) >= 0 ? 1 : -1;
      for (const f of availableFoods) {
        if (f.eaten) continue;
        if (Math.hypot(f.x - (turtle.x + tDirSign * turtle.length * 0.35), f.y - turtle.y) < 10.5) {
          consumeFood(f);
          turtle.targetFood = null;
          turtle.biteUntil = tiempo + 0.35;
          break;
        }
      }

      const tSpeed = 8.2 * intensidadMovimiento;
      let desiredVx = turtle.vx;
      let desiredVy = turtle.vy;
      if (turtle.targetFood && !turtle.targetFood.eaten) {
        const dx = turtle.targetFood.x - turtle.x;
        const dy = Math.min(turtle.targetFood.y, tMaxY) - turtle.y;
        const dist = Math.max(1, Math.hypot(dx, dy));
        desiredVx = (dx / dist) * tSpeed * 1.28;
        desiredVy = (dy / dist) * tSpeed * 1.28;
      } else {
        if (tiempo >= turtle.nextSurfaceAt) {
          turtle.surfaceUntil = tiempo + 2.4 + Math.random() * 1.4;
          turtle.nextSurfaceAt = tiempo + 12 + Math.random() * 10;
        }
        turtle.wanderAngle += (Math.sin(tiempo * 0.31 + turtle.phase) * 0.5 + Math.cos(tiempo * 0.19 + turtle.phase * 1.7) * 0.35) * delta;
        const targetNorm = tiempo < turtle.surfaceUntil ? 0.06 : turtle.preferredDepthNorm + Math.sin(tiempo * 0.14 + turtle.phase) * 0.12;
        const prefY = THREE.MathUtils.clamp(surfaceSceneY - waterHeightPx * targetNorm, tMinY, tMaxY);
        desiredVx = Math.cos(turtle.wanderAngle) * tSpeed;
        desiredVy = Math.sin(turtle.wanderAngle) * tSpeed * 0.32 + (prefY - turtle.y) * 0.45;
      }

      if (turtle.x < -112) desiredVx += (-112 - turtle.x) * 0.85;
      if (turtle.x > 148) desiredVx += (148 - turtle.x) * 0.85;
      if (turtle.y < tMinY) desiredVy += (tMinY - turtle.y) * 1.2;
      if (turtle.y > tMaxY) desiredVy -= (turtle.y - tMaxY) * 1.2;

      turtle.vx = THREE.MathUtils.damp(turtle.vx, desiredVx, 1.9, delta);
      turtle.vy = THREE.MathUtils.damp(turtle.vy, desiredVy, 2.1, delta);
      turtle.x += turtle.vx * delta;
      turtle.y = THREE.MathUtils.clamp(turtle.y + turtle.vy * delta, tMinY, tMaxY);

      const tTargetYaw = turtle.vx < -0.5 ? Math.PI : 0;
      const tTargetPitch = Math.atan2(turtle.vy, Math.max(3, Math.abs(turtle.vx))) * 0.6;
      turtle.yaw += shortestAngleDelta(tTargetYaw, turtle.yaw) * Math.min(1, delta * 2.4);
      turtle.pitch += shortestAngleDelta(tTargetPitch, turtle.pitch) * Math.min(1, delta * 2.8);
      turtle.group.position.set(turtle.x, turtle.y, 0.5);
      turtle.group.rotation.y = turtle.yaw;
      turtle.group.rotation.z = turtle.pitch;

      const paddleBeat = tiempo * 2.6 + turtle.phase;
      turtle.flippers.forEach((fl, idx) => {
        const sign = idx < 2 ? 1 : -1;
        const side = idx % 2 === 0 ? 0 : Math.PI;
        fl.rotation.x = Math.sin(paddleBeat + side) * 0.28 * sign;
        fl.rotation.z = Math.cos(paddleBeat + side) * 0.34;
      });
      turtle.head.rotation.z = Math.sin(tiempo * 0.8 + turtle.phase) * 0.08;
    }

    const remainingFoods = availableFoods.filter((f) => !f.eaten);

    for (const pez of peces) {
      if (tiempo < pez.offscreenUntil) {
        pez.group.visible = false;
        continue;
      }
      if (!pez.group.visible) pez.group.visible = true;

      const dirSign = Math.cos(pez.yaw) >= 0 ? 1 : -1;
      const mouthX = pez.group.position.x + dirSign * pez.length * 0.36;
      const mouthY = pez.group.position.y;
      for (const f of remainingFoods) {
        if (f.eaten) continue;
        if (Math.hypot(f.x - mouthX, f.y - mouthY) < 10.5) {
          consumeFood(f);
          pez.targetFood = null;
          pez.biteUntil = tiempo + 0.16;
          break;
        }
      }

      if (pez.targetFood && (pez.targetFood.eaten || tiempo >= pez.targetFood.fadeAt || tiempo >= pez.targetUntil)) {
        pez.targetFood = null;
      }
      if (!pez.targetFood && remainingFoods.length > 0 && tiempo >= pez.biteUntil) {
        let bestFood = null;
        let bestScore = Infinity;
        for (const f of remainingFoods) {
          if (f.eaten) continue;
          const dist = Math.hypot(f.x - pez.group.position.x, f.y - pez.group.position.y);
          if (dist < 240) {
            const crowd = peces.filter((other) => other.targetFood === f).length;
            const score = dist + crowd * 36;
            if (score < bestScore) {
              bestScore = score;
              bestFood = f;
            }
          }
        }
        if (bestFood) {
          pez.targetFood = bestFood;
          pez.targetUntil = tiempo + 6.5;
        }
      }

      if (tiempo >= pez.nextDecisionAt) {
        pez.nextDecisionAt = tiempo + 2.5 + Math.random() * 5.0;
        pez.cruiseMult = 0.72 + Math.random() * 0.56;
        if (Math.random() < 0.28) pez.wanderAngle += (Math.random() - 0.5) * 1.4;
      }

      const minAllowedY = bottomSceneY + pez.height * 0.65 + 4;
      const maxAllowedY = surfaceSceneY - (pez.targetFood ? 7 : 15) - pez.height * 0.45;
      const clampedMaxY = Math.max(minAllowedY, maxAllowedY);

      let steerX = 0;
      let steerY = 0;
      const baseCruise = movimiento.velocidad * pez.speedFactor * pez.cruiseMult * intensidadMovimiento;

      if (tiempo < pez.biteUntil) {
        steerX = pez.vx * 0.3;
        steerY = pez.vy * 0.3;
      } else if (pez.targetFood && !pez.targetFood.eaten) {
        const aimX = pez.targetFood.x;
        const aimY = Math.min(pez.targetFood.y, clampedMaxY + 6);
        const aimSign = aimX - pez.group.position.x < -2 ? -1 : 1;
        const dx = aimX - aimSign * pez.length * 0.25 - pez.group.position.x;
        const dy = aimY - pez.group.position.y;
        const dist = Math.max(1, Math.hypot(dx, dy));
        const chaseSpeed = movimiento.velocidad * movimiento.reaccion * 1.28 * intensidadMovimiento;
        steerX = (dx / dist) * chaseSpeed;
        steerY = (dy / dist) * chaseSpeed;
      } else {
        const wNoise = Math.sin(tiempo * 0.47 + pez.phase * 11.3) * 0.55 + Math.cos(tiempo * 0.83 + pez.phase * 5.7) * 0.45;
        pez.wanderAngle += wNoise * 0.65 * delta;
        const depthOffset = Math.sin(tiempo * 0.29 + pez.phase * 7.1) * 0.1 + Math.cos(tiempo * 0.17 + pez.phase * 13.7) * 0.08;
        const desiredY = THREE.MathUtils.clamp(
          surfaceSceneY - waterHeightPx * THREE.MathUtils.clamp(pez.preferredDepthNorm + depthOffset, 0.12, 0.88),
          minAllowedY,
          clampedMaxY
        );
        steerX = Math.cos(pez.wanderAngle) * baseCruise;
        steerY = Math.sin(pez.wanderAngle) * baseCruise * 0.35 + (desiredY - pez.group.position.y) * 0.65;

        let alignX = 0, alignY = 0, cohX = 0, cohY = 0, sepX = 0, sepY = 0, schoolCount = 0;
        for (const other of peces) {
          if (other === pez || !other.group.visible) continue;
          const dx = other.group.position.x - pez.group.position.x;
          const dy = other.group.position.y - pez.group.position.y;
          const d = Math.hypot(dx, dy);
          if (d < 28 && d > 0.1) {
            const push = ((28 - d) / 28) * 18;
            sepX -= (dx / d) * push;
            sepY -= (dy / d) * push;
          }
          if (pez.schooling && other.schooling && d < 78) {
            alignX += other.vx; alignY += other.vy;
            cohX += dx; cohY += dy;
            schoolCount++;
          }
        }
        if (schoolCount > 0) {
          steerX += (alignX / schoolCount - steerX) * 0.22 + (cohX / schoolCount) * 0.16;
          steerY += (alignY / schoolCount - steerY) * 0.18 + (cohY / schoolCount) * 0.12;
        }
        steerX += sepX;
        steerY += sepY;
      }

      const px = pez.group.position.x;
      const py = pez.group.position.y;
      if (px < -114) {
        steerX += (-114 - px) * 1.45;
        pez.wanderAngle = Math.atan2(steerY, Math.max(4, steerX));
      } else if (px > 148 && pez.phase > 0.55) {
        steerX -= (px - 148) * 1.35;
        pez.wanderAngle = Math.atan2(steerY, Math.min(-4, steerX));
      }
      if (py < minAllowedY + 6) steerY += (minAllowedY + 6 - py) * 2.2;
      if (py > clampedMaxY - 6) steerY -= (py - (clampedMaxY - 6)) * 2.2;

      for (const boat of boatZones) {
        const dx = px - boat.x;
        const dy = py - (surfaceSceneY - 4);
        if (Math.abs(dx) < boat.halfW + 10 && dy > -boat.depth - 10) {
          steerY -= 26;
          steerX += Math.sign(dx || 1) * 10;
        }
      }
      for (const tx of tarullaZones) {
        const dx = px - tx;
        const dy = py - (surfaceSceneY - 12);
        const d = Math.hypot(dx, dy);
        if (d < 26 && d > 0.1) {
          steerX += (dx / d) * 14;
          steerY -= 16;
        }
      }
      if (manatee) {
        const dx = px - manatee.x;
        const dy = py - manatee.y;
        const d = Math.hypot(dx, dy);
        const safeR = manatee.length * 0.56 + 14;
        if (d < safeR && d > 0.1) {
          const push = ((safeR - d) / safeR) * 38;
          steerX += (dx / d) * push;
          steerY += (dy / d) * push;
        }
      }
      for (const turtle of turtles) {
        const dx = px - turtle.x;
        const dy = py - turtle.y;
        const d = Math.hypot(dx, dy);
        if (d < 24 && d > 0.1) {
          steerX += (dx / d) * 18;
          steerY += (dy / d) * 18;
        }
      }

      const turnSmooth = pez.targetFood ? movimiento.reaccion * 4.2 : 2.6;
      pez.vx = THREE.MathUtils.damp(pez.vx, steerX, turnSmooth, delta);
      pez.vy = THREE.MathUtils.damp(pez.vy, steerY, turnSmooth, delta);
      pez.group.position.x += pez.vx * delta;
      pez.group.position.y = THREE.MathUtils.clamp(
        pez.group.position.y + pez.vy * delta,
        minAllowedY,
        clampedMaxY + (pez.targetFood ? 6 : 0)
      );

      const halfLen = pez.length * 0.65;
      if (pez.group.position.x > 172 + halfLen || pez.group.position.x < -128 - halfLen) {
        const enterFromLeft = Math.random() < 0.65;
        pez.group.position.x = enterFromLeft ? -124 - halfLen : 170 + halfLen;
        pez.group.position.y = THREE.MathUtils.clamp(
          surfaceSceneY - waterHeightPx * (0.2 + Math.random() * 0.65),
          minAllowedY,
          clampedMaxY
        );
        const dir = enterFromLeft ? 1 : -1;
        pez.vx = dir * baseCruise;
        pez.vy = (Math.random() - 0.5) * 3;
        pez.yaw = dir < 0 ? Math.PI : 0;
        pez.wanderAngle = dir < 0 ? Math.PI : 0;
        pez.offscreenUntil = tiempo + 0.4 + Math.random() * 1.6;
      }

      const speedMag = Math.hypot(pez.vx, pez.vy);
      const speedRatio = THREE.MathUtils.clamp(speedMag / 16, 0.35, 1.85);
      if (Math.abs(pez.vx) > 1.2) {
        const desiredYaw = pez.vx < 0 ? Math.PI : 0;
        pez.yaw += shortestAngleDelta(desiredYaw, pez.yaw) * Math.min(1, delta * (pez.targetFood ? 5.2 : 3.2));
      }
      const desiredPitch = THREE.MathUtils.clamp(
        Math.atan2(pez.vy, Math.max(4, Math.abs(pez.vx))) * 0.6,
        -0.45,
        0.45
      );
      pez.pitch += shortestAngleDelta(desiredPitch, pez.pitch) * Math.min(1, delta * 3.8);
      pez.group.rotation.y = pez.yaw;
      pez.group.rotation.z = pez.pitch;

      const faseNado = tiempo * (2.1 + speedRatio * 1.15) + pez.phase * Math.PI * 2;
      const posiciones = pez.vertices;
      for (let i = 0; i < posiciones.count; i++) {
        const offset = i * 3;
        const x = pez.baseVertices[offset];
        const dorsalidad = Math.max(0, -x / (pez.length * 0.36));
        const onda = Math.sin(faseNado - x * 0.22) * pez.height * 0.052 * potencia * speedRatio * dorsalidad ** 1.5;
        posiciones.array[offset] = pez.baseVertices[offset];
        posiciones.array[offset + 1] = pez.baseVertices[offset + 1] + onda;
        posiciones.array[offset + 2] = pez.baseVertices[offset + 2] +
          Math.cos(faseNado - x * 0.22) * pez.height * 0.017 * potencia * speedRatio * dorsalidad;
      }
      posiciones.needsUpdate = true;
      pez.geometry.computeVertexNormals();
      pez.tail.rotation.z = Math.sin(faseNado * 1.45) * 0.48 * potencia * Math.min(1.25, speedRatio);
      pez.dorsal.rotation.z = Math.sin(faseNado * 0.75) * 0.08 * potencia;
      pez.pectorals.forEach((aleta, index) => {
        aleta.rotation.x = Math.sin(faseNado * 1.15 + index * Math.PI) * 0.22 * potencia;
        aleta.rotation.z = Math.sin(faseNado + index * Math.PI) * 0.06 * potencia;
      });
    }
    renderer.render(escena, camara);
  }

  const btnFeed = panel.querySelector(".btn-feed-inframe");
  if (btnFeed) {
    btnFeed.addEventListener("click", () => {
      const centerX = THREE.MathUtils.clamp(85 + Math.random() * 170, 70, 270) - 170;
      const totalItems = 11;
      for (let i = 0; i < totalItems; i++) {
        const roll = i % 3;
        const kind = roll === 0 ? "fruit" : roll === 1 ? "plant" : "pellet";
        const px = THREE.MathUtils.clamp(centerX + (Math.random() - 0.5) * 42, -118, 150);
        const py = surfaceSceneY + 2 + Math.random() * 5;
        const pz = (Math.random() - 0.5) * 1.6;
        const radius = kind === "fruit" ? 2.0 + Math.random() * 0.7 : kind === "plant" ? 1.9 + Math.random() * 0.65 : 1.25 + Math.random() * 0.6;
        const geom = kind === "fruit" ? fruitGeom : kind === "plant" ? plantGeom : pelletGeom;
        const mat = kind === "fruit" ? fruitMat : kind === "plant" ? plantMat : pelletMat;
        const mesh = new THREE.Mesh(geom, mat);
        mesh.scale.setScalar(radius);
        mesh.position.set(px, py, pz);
        mesh.rotation.set(Math.random() * 1.2, Math.random() * 2.5, Math.random() * 1.2);
        mesh.renderOrder = 2;
        mesh.visible = false;
        escena.add(mesh);
        activeFoods.push({
          mesh, kind, x: px, y: py, z: pz,
          vx: (Math.random() - 0.25) * 4.5,
          vy: -3.5 - Math.random() * 5.0,
          radius,
          buoyancy: kind === "plant" ? 1.0 : kind === "fruit" ? 0.65 : 0.0,
          gravityScale: 0.8 + Math.random() * 0.35,
          phase: Math.random() * Math.PI * 2,
          releaseAt: tiempo + i * 0.045,
          fadeAt: tiempo + (kind === "pellet" ? 11.0 : 15.0),
          inWater: false, settled: false,
          bitesLeft: kind === "pellet" ? 1 : 2,
          eaten: false,
        });
      }
    });
  }
  requestAnimationFrame(animar);
})();
</script>
"""


def crear_medidor_html(
    nivel_cm: float,
    umbrales: dict,
    estado_peces: str,
    estado_peces_texto: str,
    ambiente: str,
    clima_texto: str,
    noche: bool,
    viento_kmh: float,
) -> str:
    y_cero, y_muralla, y_fondo = 452.0, 186.0, 482.0
    px_por_cm = (y_cero - y_muralla) / NIVEL_MURALLA_CM
    posicion = lambda cm: y_cero - cm * px_por_cm
    y_s = posicion(max(0.0, min(nivel_cm, NIVEL_MURALLA_CM * 1.12)))
    sobre_muralla = nivel_cm > NIVEL_MURALLA_CM

    gente = []
    if not noche and y_s > 192:
        gente.append(
            '<g transform="translate(160 186)"><g class="jn-respira">'
            f'{_persona_svg("#26394a", "#1d2a35")}</g></g>'
        )
    if not noche and y_s > 303:
        gente.append(
            '<g transform="translate(284 299)"><g class="jn-respira">'
            f'{_persona_svg("#3f7fc0", "#59606a", camina=False)}</g></g>'
        )

    botes = "" if noche else "".join(
        _bote_svg(x, y_s, tipo, retraso, duracion)
        for x, tipo, retraso, duracion in (
            (42, "a", -0.8, 7.2), (96, "b", -3.4, 8.6), (160, "c", -5.2, 9.8),
        )
    )

    perfiles_peces = [
        {"especie": "bocachico", "largo": 43, "alto": 19, "profundidad": 68, "velocidad": 1.0, "fase": 0.15, "rayas": [-0.45, -0.15, 0.15, 0.42]},
        {"especie": "bagre", "largo": 47, "alto": 18, "profundidad": 51, "velocidad": 0.88, "fase": 0.55, "rayas": []},
        {"especie": "mojarra", "largo": 36, "alto": 22, "profundidad": 35, "velocidad": 1.12, "fase": 0.8, "rayas": [-0.28, 0.05, 0.34]},
        {"especie": "sabalo", "largo": 46, "alto": 17, "profundidad": 20, "velocidad": 1.08, "fase": 0.35, "rayas": []},
        {"especie": "doncella", "largo": 49, "alto": 18, "profundidad": 78, "velocidad": 0.82, "fase": 0.65, "rayas": [-0.4, -0.08, 0.26]},
        {"especie": "pacora", "largo": 40, "alto": 23, "profundidad": 45, "velocidad": 0.96, "fase": 0.42, "rayas": [-0.3, 0.24]},
        {"especie": "capaz", "largo": 38, "alto": 16, "profundidad": 60, "velocidad": 1.18, "fase": 0.9, "rayas": []},
    ]
    datos_peces = json.dumps(
        [{**pez, "x": 58 + indice * 34} for indice, pez in enumerate(perfiles_peces)],
        ensure_ascii=False,
    )

    base_burbuja = y_fondo - 4
    sube = base_burbuja - y_s
    burbujas = []
    if sube > 10:
        for bx, radio, duracion, retraso in (
            (58, 2.2, 5.5, 0), (112, 1.6, 4.4, 1.7), (176, 2.4, 6.2, 3.1),
            (236, 1.8, 4.9, 0.8), (296, 2.0, 5.8, 2.6), (140, 1.4, 4.1, 3.9),
        ):
            burbujas.append(
                f'<circle class="jn-burbuja" cx="{bx}" cy="{base_burbuja:.0f}" r="{radio}" fill="none" '
                f'stroke="#dcf6fa" stroke-width="1" style="--sube:{sube:.0f}px;--dur:{duracion}s;--delay:-{retraso}s"/>'
            )

    gotas_lluvia = []
    relampago = ""
    if ambiente in ("lluvia", "tormenta"):
        rng_lluvia = random.Random(1996)
        for _ in range(32):
            x = rng_lluvia.uniform(4, 336)
            y = rng_lluvia.uniform(0, max(1, y_s - 12))
            gotas_lluvia.append(
                f'<path class="jn-gota-lluvia" style="--delay:{rng_lluvia.uniform(-1.8, 0):.2f}s" '
                f'd="{x:.1f} {y:.1f}l-3.5 9" fill="none" stroke="#e4f2f4" '
                'stroke-width="1" stroke-linecap="round"/>'
            )
        if ambiente == "tormenta":
            relampago = (
                '<path class="jn-relampago" d="m292 45-12 22h9l-5 17 20-26h-10l7-13Z" '
                'fill="#fff5c4" opacity=".8"/>'
            )
    lluvia_svg = f'<g aria-hidden="true">{"".join(gotas_lluvia)}{relampago}</g>'

    colores_agua = {
        "despejado": ("#2aa3b4", "#127a91", "#0c4057"),
        "nublado": ("#3793a0", "#176d80", "#103e51"),
        "lluvia": ("#448c98", "#1a6274", "#123b4c"),
        "tormenta": ("#397987", "#164f63", "#0c2e43"),
    }
    if noche:
        colores_agua = {
            "despejado": ("#1e7688", "#104d68", "#092b42"),
            "nublado": ("#286b79", "#124459", "#092b40"),
            "lluvia": ("#285d6e", "#103b53", "#08253a"),
            "tormenta": ("#204d61", "#0d344a", "#071f34"),
        }
    agua_superficie, agua_media, agua_fondo = colores_agua[ambiente]
    agua = (
        '<defs><linearGradient id="jn-agua" gradientUnits="userSpaceOnUse" '
        f'x1="0" y1="{y_s:.1f}" x2="0" y2="500">'
        f'<stop offset="0" stop-color="{agua_superficie}" stop-opacity=".46"/>'
        f'<stop offset=".18" stop-color="{agua_superficie}" stop-opacity=".58"/>'
        f'<stop offset=".54" stop-color="{agua_media}" stop-opacity=".74"/>'
        f'<stop offset="1" stop-color="{agua_fondo}" stop-opacity=".88"/></linearGradient>'
        '<linearGradient id="jn-brillo-sup" gradientUnits="userSpaceOnUse" '
        f'x1="0" y1="{y_s:.1f}" x2="0" y2="{y_s + 20:.1f}">'
        f'<stop offset="0" stop-color="#e8f7fa" stop-opacity="{".10" if noche else ".20"}"/>'
        '<stop offset="1" stop-color="#e8f7fa" stop-opacity="0"/></linearGradient></defs>'
        f'<rect x="0" y="{y_s:.1f}" width="340" height="{500 - y_s:.1f}" fill="url(#jn-agua)"/>'
        f'<rect x="0" y="{y_s:.1f}" width="340" height="20" fill="url(#jn-brillo-sup)"/>'
        f'<line x1="0" y1="{y_s:.1f}" x2="340" y2="{y_s:.1f}" stroke="#e4f7fb" stroke-opacity="{".22" if noche else ".40"}" stroke-width="0.8"/>'
    )

    marcas = []
    for metro in range(0, 11):
        y = posicion(metro * 100)
        marcas.append(
            f'<path d="M24 {y:.1f}H36" stroke="#d7e9f0" stroke-width="1"/>'
            f'<text x="20" y="{y + 3.5:.1f}" text-anchor="end" font-size="10" fill="#eef7fa" '
            f'font-family="Arial, sans-serif">{metro}</text>'
        )
        if metro < 10:
            marcas.append(f'<path d="M30 {y - px_por_cm * 50:.1f}H36" stroke="#9fc0cc" stroke-width=".8"/>')
    regla = (
        f'<rect x="6" y="{y_muralla - 10:.1f}" width="32" height="{y_cero - y_muralla + 22:.1f}" rx="6" '
        'fill="#0f2c3b" fill-opacity=".72"/>'
        + "".join(marcas)
        + f'<text x="20" y="{y_cero + 17:.1f}" text-anchor="middle" font-size="8" fill="#9fc0cc" '
        'font-family="Arial, sans-serif">m</text>'
        f'<polygon points="39,{y_s:.1f} 47,{y_s - 4.5:.1f} 47,{y_s + 4.5:.1f}" fill="#ffffff" stroke="#167f94"/>'
    )

    lineas = [
        f'<path d="M40 {posicion(NIVEL_REFERENCIA_CM):.1f}H340" stroke="#0f2c3b" stroke-opacity=".6" '
        'stroke-dasharray="5 4" stroke-width="1.2"/>'
    ]
    etiquetas = [
        {"y": posicion(NIVEL_MURALLA_CM),
         "texto": "MURALLA SUPERADA" if sobre_muralla else "MURALLA 10 m",
         "fondo": "#b5432f" if sobre_muralla else "#4b4130", "tinta": "#ffffff", "prioridad": 0},
        {"y": posicion(NIVEL_REFERENCIA_CM), "texto": f"Ref. {NIVEL_REFERENCIA_CM} cm",
         "fondo": "#0f2c3b", "tinta": "#e3f0f5", "prioridad": 1},
        {"y": y_s, "texto": f"{nivel_cm / 100:.2f} m", "fondo": "#167f94", "tinta": "#ffffff", "prioridad": 2},
    ]
    colores_umbral = {"amarilla": "#e6b84f", "naranja": "#f08c53", "roja": "#e26168"}
    for nombre, color in colores_umbral.items():
        valor = umbrales["valores"][nombre]
        if valor is None or not 0 <= valor <= NIVEL_MURALLA_CM:
            continue
        lineas.append(
            f'<path d="M40 {posicion(valor):.1f}H340" stroke="{color}" stroke-width="1.6" '
            'stroke-dasharray="2 3"/>'
        )
        etiquetas.append(
            {"y": posicion(valor), "texto": nombre.capitalize(), "fondo": color,
             "tinta": "#102b3b", "prioridad": 1}
        )
    etiquetas.sort(key=lambda e: (e["y"], e["prioridad"]))
    previo = 14.0 - 18
    for e in etiquetas:
        previo = e["pos"] = max(e["y"], previo + 18)
    limite = 488.0
    for e in reversed(etiquetas):
        limite = e["pos"] = min(e["pos"], limite)
        limite -= 18
    etiquetas_svg = []
    for e in etiquetas:
        ancho_pildora = 14 + len(e["texto"]) * 6.3
        x_pildora = 334 - ancho_pildora
        yp = e["pos"]
        etiquetas_svg.append(
            f'<rect x="{x_pildora:.1f}" y="{yp - 8:.1f}" width="{ancho_pildora:.1f}" height="16" rx="8" '
            f'fill="{e["fondo"]}" fill-opacity=".92"/>'
            f'<text x="{x_pildora + ancho_pildora / 2:.1f}" y="{yp + 3.6:.1f}" text-anchor="middle" '
            f'font-size="10" font-weight="700" fill="{e["tinta"]}" font-family="Arial, sans-serif">'
            f'{e["texto"]}</text>'
        )

    html = f"""
    <style>{_MEDIDOR_CSS}</style>
    <div class="gauge-feed-wrap">
      <div class="gauge-panel">
      <svg class="gauge-scene" viewBox="0 0 340 500" xmlns="http://www.w3.org/2000/svg"
           data-superficie="{y_s:.1f}" data-estado-peces="{estado_peces}"
           data-ambiente="{ambiente}" data-noche="{'true' if noche else 'false'}"
           data-viento="{viento_kmh:.2f}" role="group"
           aria-label="Hábitat del río en {clima_texto}, {'de noche' if noche else 'de día'}. Nivel {nivel_cm:.1f} centímetros; peces {estado_peces_texto}.">
        <title>Hábitat del río Magdalena en Calamar</title>
        {_escena_fija_svg(ambiente, noche)}
        {lluvia_svg}
        {''.join(gente)}
        {_fauna_orilla_svg(y_s, noche)}
        {agua}
        {botes}
        {_tarullas_svg(y_s)}
      </svg>
      <canvas class="fish-canvas" aria-hidden="true"></canvas>
      <svg class="gauge-overlay" viewBox="0 0 340 500" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
        {''.join(lineas)}
        {regla}
        {''.join(etiquetas_svg)}
      </svg>
      <button type="button" class="btn-feed-inframe" aria-label="Alimentar peces">Alimentar peces</button>
      </div>
    </div>
    <script id="fish-data" type="application/json">{datos_peces}</script>
    {_MEDIDOR_SCRIPT}
    """
    return _compactar_html(html)


# ═══════════════════════════ UI COMPONENTES ═══════════════════════════
def mostrar_encabezado(icon_data: str, cover_data: str) -> None:
    st.markdown(
        f"""
        <section class="profile-card" aria-label="Perfil del proyecto JUAN">
          <div class="profile-cover" style="--cover-image: url('data:image/webp;base64,{cover_data}')"></div>
          <img class="profile-avatar" src="data:image/png;base64,{icon_data}" alt="Imagen de JUAN">
          <div class="profile-content">
            <h1>JUAN</h1>
            <h2>OBSERVATORIO MONITOREO DEL NIVEL DE RIO MAGDALENA EN CALAMAR BOLIVAR</h2>
            <p>{ESTACION_NOMBRE} · Estación IDEAM {ESTACION_CODIGO} · Nivel observado</p>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def mostrar_tarjeta_lectura(nivel_cm: float, fecha_texto: str, cambio_texto: str, fuente: str) -> None:
    st.markdown(
        f"""
        <div class="reading-card">
          <div class="eyebrow">LECTURA MÁS RECIENTE</div>
          <div class="reading-value">{nivel_cm:,.1f}<span> cm</span></div>
          <div class="reading-conversion">{nivel_cm / 100:.2f} m</div>
          <div class="reading-divider"></div>
          <div class="reading-detail">
            <strong>Fecha de lectura</strong><br>{fecha_texto}<br>
            <strong>Variación</strong><br>{cambio_texto}<br>
            <strong>Fuente</strong><br>{fuente}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def mostrar_clima_actual(
    tiempo_actual: dict | None, error_meteorologia: Exception | None, noche: bool
) -> None:
    """Muestra una tarjeta compacta con el estado del clima y su icono."""
    if tiempo_actual is None:
        icono = "🌡️"
        descripcion = "Clima no disponible"
        meta = "Sin conexión al servicio meteorológico"
    else:
        codigo = int(tiempo_actual["weather_code"])
        icono = icono_tiempo(codigo, noche)
        descripcion = describir_tiempo(codigo)
        meta = (
            f"{float(tiempo_actual['temperature_2m']):.1f} °C · "
            f"humedad {int(tiempo_actual['relative_humidity_2m'])}% · "
            f"viento {float(tiempo_actual['wind_speed_10m']):.0f} km/h"
        )

    st.markdown(
        f"""
        <div class="weather-card" role="status" aria-label="Clima actual en Calamar">
          <div class="weather-icon" aria-hidden="true">{icono}</div>
          <div class="weather-body">
            <div class="weather-label">Clima en Calamar ahora</div>
            <div class="weather-desc">{descripcion}</div>
            <div class="weather-meta">{meta}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ═══════════════════════════ CARGA DE DATOS Y COMBINACIÓN ═══════════════════════════
def cargar_datos_combinados() -> tuple[pd.DataFrame, pd.DataFrame | None, Exception | None]:
    df = cargar_datos(str(CSV_PATH), CSV_PATH.stat().st_mtime)
    datos_fews: pd.DataFrame | None = None
    error_fews: Exception | None = None
    try:
        with st.spinner("Consultando la serie de nivel de FEWS IDEAM..."):
            datos_fews = cargar_nivel_fews_calamar()
    except (
        requests.RequestException,
        pd.errors.ParserError,
        pd.errors.EmptyDataError,
        UnicodeError,
        ValueError,
    ) as exc:
        error_fews = exc
    if datos_fews is not None:
        df = pd.concat([df, datos_fews], ignore_index=True, sort=False)
        df = (
            df.drop_duplicates(subset=["Fecha"], keep="last")
            .sort_values("Fecha")
            .reset_index(drop=True)
        )
    return df, datos_fews, error_fews


def clasificar_estado_peces(nivel_cm: float, cambio_cm: float) -> tuple[str, str]:
    if nivel_cm > 900:
        return "scared", "asustados"
    if cambio_cm < 0:
        return "uncomfortable", "incómodos"
    return "calm", "tranquilos"


def calcular_metadatos_ultima_lectura(df: pd.DataFrame) -> dict:
    ultimo = df.iloc[-1]
    nivel_cm = float(ultimo["Nivel_cm"])
    fecha_ult = ultimo["Fecha"]
    ts_ult = ultimo["Ultima_lectura"] if pd.notna(ultimo["Ultima_lectura"]) else fecha_ult

    previo = df.iloc[-2]
    dias_diff = (fecha_ult - previo["Fecha"]).days
    delta_cm = nivel_cm - float(previo["Nivel_cm"])
    ref_txt = "el día anterior" if dias_diff == 1 else f"el {fecha_es(previo['Fecha'])}"
    cambio_texto = (
        "Sin variación" if delta_cm == 0
        else f"{'Subió' if delta_cm > 0 else 'Bajó'} {abs(delta_cm):.1f} cm {ref_txt}"
    )

    edad_dias = (pd.Timestamp.now().normalize() - fecha_ult.normalize()).days
    estado_peces, estado_peces_texto = clasificar_estado_peces(nivel_cm, delta_cm)

    return {
        "nivel_cm": nivel_cm,
        "fecha_ult": fecha_ult,
        "ts_ult": ts_ult,
        "delta_cm": delta_cm,
        "cambio_texto": cambio_texto,
        "edad_dias": edad_dias,
        "fuente": str(ultimo["Fuente"]),
        "estado_peces": estado_peces,
        "estado_peces_texto": estado_peces_texto,
    }


# ═══════════════════════════ SECCIONES DE LA UI ═══════════════════════════
def seccion_medidor_y_lectura(
    nivel_cm: float,
    umbrales: dict,
    estado_peces: str,
    estado_peces_texto: str,
    ambiente: str,
    clima_texto: str,
    noche: bool,
    viento_kmh: float,
    meta_lectura: dict,
    tiempo_actual: dict | None,
    error_meteorologia: Exception | None,
) -> None:
    col_medidor, col_lectura = st.columns([0.9, 1.1], gap="large")
    with col_medidor:
        components.html(
            crear_medidor_html(
                nivel_cm, umbrales, estado_peces, estado_peces_texto,
                ambiente, clima_texto, noche, viento_kmh,
            ),
            height=550,
            scrolling=False,
        )
        # Clima debajo del medidor (con icono)
        mostrar_clima_actual(tiempo_actual, error_meteorologia, noche)

    with col_lectura:
        fecha_texto = fecha_es(
            meta_lectura["ts_ult"],
            con_hora=pd.notna(meta_lectura["ts_ult"]),
        )
        mostrar_tarjeta_lectura(
            nivel_cm,
            fecha_texto,
            meta_lectura["cambio_texto"],
            meta_lectura["fuente"],
        )
        banner(evaluar(nivel_cm, umbrales))


def seccion_visor_fews(
    datos_fews: pd.DataFrame | None,
    error_fews: Exception | None,
) -> None:
    """Sección del visor FEWS: mapa de ubicación y serie consolidada.

    Se eliminaron el «Estado del clima en Calamar» y el «Último nivel observado FEWS»
    que aparecían junto al mapa (ahora viven en sus propias secciones).
    """
    st.subheader("Visor FEWS IDEAM · Calamar")
    st.caption(
        "Ubicación de la estación y serie consolidada de nivel observado publicada por FEWS IDEAM. "
        "Las lecturas de FEWS son preliminares, pueden ser corregidas y no son una medición en tiempo real."
    )
    mapa_estacion = pd.DataFrame(
        [{
            "lat": ESTACION_LATITUD,
            "lon": ESTACION_LONGITUD,
            "Estación": f"CALAMAR [{ESTACION_CODIGO}]",
            "Altitud (m s. n. m.)": ESTACION_ALTITUD_MSNM,
        }]
    )
    boton_actualizar, enlace_fews = st.columns(2)
    if boton_actualizar.button("Actualizar ahora", key="consultar_fews"):
        cargar_nivel_fews_calamar.clear()
        st.rerun()
    enlace_fews.link_button("Abrir visor FEWS nacional", FEWS_VISOR_URL, width="stretch")

    if error_fews is not None:
        st.caption("No se pudo consultar FEWS; mostrando el último dato guardado.")

    st.caption(
        f"Estación {ESTACION_NOMBRE} · Código IDEAM {ESTACION_CODIGO} · "
        f"{ESTACION_LATITUD:.6f}, {ESTACION_LONGITUD:.6f} · "
        f"{ESTACION_ALTITUD_MSNM} m s. n. m."
    )
    st.map(
        mapa_estacion, latitude="lat", longitude="lon",
        color="#167f94", size=120, zoom=14, height=420,
    )
    st.markdown(
        "[Abrir ubicación en OpenStreetMap]"
        f"(https://www.openstreetmap.org/?mlat={ESTACION_LATITUD}&mlon={ESTACION_LONGITUD}"
        f"#map=15/{ESTACION_LATITUD}/{ESTACION_LONGITUD}) · "
        "[Catálogo Nacional de Estaciones del IDEAM]"
        "(https://dhime.ideam.gov.co/server/rest/services/CNE/Estaciones/MapServer/0)"
    )

    if datos_fews is not None:
        st.caption(
            f"{len(datos_fews):,} registros FEWS · "
            f"{fecha_es(datos_fews['Fecha'].iloc[0])} – "
            f"{fecha_es(datos_fews['Fecha'].iloc[-1])}"
        )
        st.plotly_chart(
            crear_grafica_fews(datos_fews),
            width="stretch",
            config={"displayModeBar": False},
        )
        st.caption(
            f"Fuente: [FEWS IDEAM]({FEWS_VISOR_URL}). "
            "La consulta se conserva en caché durante 5 minutos."
        )


def seccion_lluvia_y_tendencia(
    df: pd.DataFrame, tiempo_actual: dict | None, error_meteorologia: Exception | None
) -> None:
    st.subheader("Lluvia prevista y tendencia observada del río")
    st.caption(
        "La lluvia se calcula para toda el área hidrográfica Magdalena-Cauca: promedio espacial "
        "ponderado por el área de sus 105 subzonas IDEAM, acumulado para las próximas 24 horas."
    )
    try:
        with st.spinner("Consultando condiciones meteorológicas y pronóstico..."):
            if error_meteorologia is not None:
                raise error_meteorologia
            if tiempo_actual is None:
                raise ValueError("No hay datos meteorológicos actuales disponibles.")
            subzonas_cuenca = cargar_subzonas_cuenca()
            pronostico_horario = cargar_pronostico_cuenca(tiempo_actual["time"])
    except (requests.RequestException, ValueError) as exc:
        st.error(f"No se pudo actualizar el pronóstico meteorológico local o de la cuenca: {exc}")
        st.caption(
            "La lluvia prevista no está disponible. La dirección observada del río se calcula "
            "independientemente, a partir de las lecturas recientes."
        )
        tendencia, motivo_tendencia = estimar_tendencia_nivel(df)
        st.metric("Dirección observada · 3 días", tendencia)
        st.caption(motivo_tendencia)
        return

    lluvia_media_total = float(pronostico_horario["Precipitacion_mm"].sum())
    tendencia, motivo_tendencia = estimar_tendencia_nivel(df)
    clima, lluvia, nivel_futuro = st.columns(3)
    with clima:
        clima.metric("Condición en Calamar", describir_tiempo(int(tiempo_actual["weather_code"])))
        clima.caption(
            f"{float(tiempo_actual['temperature_2m']):.1f} °C · "
            f"humedad {int(tiempo_actual['relative_humidity_2m'])}% · "
            f"viento {float(tiempo_actual['wind_speed_10m']):.0f} km/h"
        )
    lluvia.metric("Lluvia media acumulada · cuenca · 24 h", f"{lluvia_media_total:.1f} mm")
    nivel_futuro.metric("Dirección observada · 3 días", tendencia)

    area_cuenca_km2 = float(subzonas_cuenca["Area_km2"].sum())
    area_cuenca_formateada = f"{area_cuenca_km2:,.0f}".replace(",", ".")
    st.caption(
        f"Área representada: {area_cuenca_formateada} km² en {len(subzonas_cuenca)} subzonas. "
        "Los milímetros son una media areal ponderada; no se suman entre ubicaciones."
    )
    hora_modelo = fecha_es(pd.Timestamp(tiempo_actual["time"]), con_hora=True)
    st.caption(f"Actualización del modelo: {hora_modelo} · zona horaria de Colombia.")
    st.markdown(
        f"""
        <div class="forecast-note">
          <div class="eyebrow">LECTURA DE LOS DATOS OBSERVADOS</div>
          <p>{motivo_tendencia}</p>
          <p class="forecast-caveat">
            La dirección resume la serie reciente de Calamar; no pronostica el nivel de las
            próximas 24 horas. La lluvia se estima para toda la cuenca Magdalena-Cauca y no permite
            inferir por sí sola el cambio del río en esta estación: no se modelan el aporte local,
            la escorrentía, los caudales, los tiempos de tránsito ni la operación de embalses.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.plotly_chart(
        crear_grafica_pronostico_cuenca(pronostico_horario),
        width="stretch",
        config={"displayModeBar": False},
    )
    st.markdown(
        "[Pronóstico: Open-Meteo](https://open-meteo.com/) · CC BY 4.0 · "
        "[zonificación hidrográfica 2025 del IDEAM]"
        "(https://dhime.ideam.gov.co/server/rest/services/Cartografia_Tematica/"
        "ZonificacionHidrografica/MapServer/0)."
    )


def seccion_historico(df: pd.DataFrame, umbrales: dict, fecha_ult: pd.Timestamp) -> None:
    col_titulo, col_periodo = st.columns([1.5, 1])
    with col_titulo:
        st.subheader("Histórico de niveles")
    with col_periodo:
        periodo = st.selectbox("Período", list(PERIODOS_GRAFICA))
    dias_periodo = PERIODOS_GRAFICA[periodo]
    if dias_periodo is None:
        datos_grafica = df.copy()
    else:
        datos_grafica = df[df["Fecha"] >= fecha_ult - pd.Timedelta(days=dias_periodo)].copy()
    datos_grafica["FechaTxt"] = [
        fecha_es(fila.Fecha, con_hora=fila.Fuente.startswith("FEWS"))
        for fila in datos_grafica.itertuples()
    ]
    st.caption(
        f"{len(datos_grafica):,} registros · "
        f"{fecha_es(datos_grafica['Fecha'].iloc[0])} – {fecha_es(datos_grafica['Fecha'].iloc[-1])}"
    )

    fig = crear_grafica_historica(datos_grafica, umbrales)
    cfg = {"displayModeBar": False}
    try:
        st.plotly_chart(fig, width="stretch", config=cfg)
    except TypeError:
        st.plotly_chart(fig, use_container_width=True, config=cfg)

    with st.expander("Consultar las últimas 30 lecturas"):
        recientes = df.copy()
        recientes["Fecha y hora"] = recientes.apply(
            lambda fila: fila["Ultima_lectura"]
            if pd.notna(fila["Ultima_lectura"])
            else fila["Fecha"],
            axis=1,
        )
        recientes = recientes.sort_values("Fecha y hora", ascending=False).head(30)
        recientes["Fecha y hora"] = recientes["Fecha y hora"].map(
            lambda fecha: fecha_es(fecha, con_hora=True)
        )
        st.dataframe(
            recientes[["Fecha y hora", "Nivel_cm", "Fuente"]].rename(
                columns={"Nivel_cm": "Nivel (cm)"}
            ),
            hide_index=True,
            width="stretch",
        )
        st.caption(f"Hora de última lectura: {fecha_es(fecha_ult, con_hora=True)}")

    with st.expander("Ver umbrales usados"):
        estilos = {"amarilla": "Amarilla", "naranja": "Naranja", "roja": "Roja"}
        for k, nombre in estilos.items():
            v, o = umbrales["valores"][k], umbrales["origen"][k]
            st.write(f"**{nombre}:** {'—' if v is None else f'{v:.0f} cm'} ({o})")


def seccion_compartir_descargar(df: pd.DataFrame, nivel_cm: float) -> None:
    st.divider()
    b1, b2 = st.columns(2)
    b1.download_button(
        "Descargar histórico (CSV)",
        data=df.assign(
            Fecha=df["Fecha"].dt.strftime("%Y-%m-%d %H:%M")
        ).to_csv(index=False).encode("utf-8"),
        file_name="nivel_calamar.csv",
        mime="text/csv",
    )
    if APP_URL:
        msg = (
            f"Nivel del río Magdalena en Calamar: {nivel_cm:.0f} cm "
            f"({nivel_cm / 100:.2f} m). Consulte aquí: {APP_URL}"
        )
        b2.link_button("Compartir por WhatsApp", f"https://wa.me/?text={quote(msg)}")
    else:
        b2.caption("Para compartir: copie el enlace de esta página y envíelo por WhatsApp.")


def seccion_pie() -> None:
    st.markdown("---")
    st.caption(
        f"**Fuente:** IDEAM, Hidrología Nacional Diaria y exportaciones DHIME; "
        f"estación limnimétrica {ESTACION_CODIGO} – Calamar, Bolívar. "
        "El histórico local muestra nivel medio diario y las últimas observaciones FEWS pueden ser intradiarias. "
        "El histórico local se intenta actualizar tres veces al día y la consulta FEWS se conserva "
        "en caché durante 5 minutos; las lecturas FEWS son preliminares y el IDEAM puede publicarlas "
        "con retraso o corregirlas después. "
        "Esta herramienta es informativa y **no reemplaza** los avisos "
        "oficiales del IDEAM, la UNGRD ni del Consejo Municipal de Gestión del Riesgo."
    )


# ═══════════════════════════ FLUJO PRINCIPAL ═══════════════════════════
def main() -> None:
    st.set_page_config(
        page_title="JUAN",
        page_icon=JUAN_ICON_PATH,
        layout="wide",
    )
    inyectar_estilos()

    icon_data = base64.b64encode(JUAN_ICON_PATH.read_bytes()).decode("ascii")
    cover_data = base64.b64encode(JUAN_COVER_PATH.read_bytes()).decode("ascii")
    mostrar_encabezado(icon_data, cover_data)

    if not CSV_PATH.exists():
        st.error(
            "Todavía no hay datos. Ejecute el workflow "
            "«Actualizar datos nivel río Calamar» en GitHub Actions."
        )
        st.stop()

    df, datos_fews, error_fews = cargar_datos_combinados()
    if len(df) < 2:
        st.warning("Hay muy pocos datos para mostrar el tablero.")
        st.stop()

    meta_lectura = calcular_metadatos_ultima_lectura(df)
    nivel_cm = meta_lectura["nivel_cm"]
    fecha_ult = meta_lectura["fecha_ult"]
    umbrales = calcular_umbrales()

    # Meteorología
    tiempo_actual: dict | None = None
    error_meteorologia: Exception | None = None
    try:
        with st.spinner("Actualizando el ambiente del río..."):
            tiempo_actual = cargar_meteorologia()
    except (requests.RequestException, ValueError) as exc:
        error_meteorologia = exc

    codigo_clima = int(tiempo_actual["weather_code"]) if tiempo_actual is not None else None
    hora_local = (
        pd.Timestamp(tiempo_actual["time"])
        if tiempo_actual is not None
        else pd.Timestamp.now(tz=METEO_ZONA_HORARIA).tz_localize(None)
    )
    noche = hora_local.hour < 6 or hora_local.hour >= 18
    ambiente = tipo_ambiente(codigo_clima)
    clima_texto = (
        describir_tiempo(codigo_clima)
        if codigo_clima is not None
        else "clima no disponible"
    )
    viento_kmh = float(tiempo_actual["wind_speed_10m"]) if tiempo_actual is not None else 0.0

    seccion_medidor_y_lectura(
        nivel_cm,
        umbrales,
        meta_lectura["estado_peces"],
        meta_lectura["estado_peces_texto"],
        ambiente,
        clima_texto,
        noche,
        viento_kmh,
        meta_lectura,
        tiempo_actual,
        error_meteorologia,
    )

    if meta_lectura["edad_dias"] > DIAS_MAX_SIN_DATOS:
        st.warning(
            f"El último dato publicado por el IDEAM tiene {meta_lectura['edad_dias']} días; "
            "puede no representar el nivel actual del río."
        )

    seccion_visor_fews(datos_fews, error_fews)
    seccion_lluvia_y_tendencia(df, tiempo_actual, error_meteorologia)
    seccion_historico(df, umbrales, fecha_ult)
    seccion_compartir_descargar(df, nivel_cm)
    seccion_pie()


if __name__ == "__main__":
    main()