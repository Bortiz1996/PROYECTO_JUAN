"""
app.py — JUAN: nivel del río Magdalena en Calamar (Bolívar)
Tablero ciudadano mobile-first. Datos: IDEAM, estación 29037020 (nivel medio diario, cm).
"""
from __future__ import annotations

import base64
import io
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
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ═══════════════════════════ CONFIGURACIÓN ═══════════════════════════
ESTACION_CODIGO = "29037020"
ESTACION_NOMBRE = "Calamar, Bolívar"
ESTACION_LATITUD = 10.243275
ESTACION_LONGITUD = -74.915017
ESTACION_ALTITUD_MSNM = 8
NIVEL_REFERENCIA_CM = 950
NIVEL_MURALLA_CM = 1000   # cota de la muralla: el nivel 10 m llega hasta ella
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

# Enlace oficial del observatorio para compartir.
APP_URL = "https://ing-ambiente-proyect1001.github.io/PROYECTO_JUAN/"

# ── Umbrales de alerta en cm. Solo configurar cotas oficiales verificadas.
UMBRAL_AMARILLA_CM: float | None = None
UMBRAL_NARANJA_CM: float | None = None
UMBRAL_ROJA_CM: float | None = None

DIAS_MAX_SIN_DATOS = 3       # si el último dato es más viejo, se advierte
PERIODOS_GRAFICA = {
    "Últimos 60 días": 60,
    "Último año": 365,
    "Últimos 5 años": 365 * 5,
    "Todo el histórico": None,
}
# ═════════════════════════════════════════════════════════════════════

MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

st.set_page_config(
    page_title="JUAN",
    page_icon=JUAN_ICON_PATH,
    layout="wide",
)

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
      .forecast-value {color: #17384a; font-size: 1.45rem; font-weight: 700; margin: .25rem 0;}
      .forecast-caveat {color: #607989; font-size: .8rem; margin-bottom: 0;}
      .gauge-panel {position: relative; width: min(100%, 340px); aspect-ratio: 340 / 500;
        margin: 0 auto; overflow: hidden; border-radius: 16px; background: #1b5a85;
        font-family: Arial, sans-serif; box-shadow: 0 8px 26px rgba(20, 45, 60, .14);}
      .gauge-scene {display: block; width: 100%; height: 100%;}
      .jn-ola {animation: jn-ola var(--dur, 9s) linear infinite; animation-delay: var(--delay, 0s);}
      @keyframes jn-ola {
        from {transform: translateX(0);}
        to {transform: translateX(-340px);}
      }
      .jn-nube {animation: jn-nube var(--dur) linear infinite; animation-delay: var(--delay);}
      @keyframes jn-nube {
        from {transform: translateX(-100px);}
        to {transform: translateX(440px);}
      }
      .jn-ave {animation: jn-vuelo var(--dur) linear infinite; animation-delay: var(--delay);}
      .jn-ave path {transform-box: fill-box; transform-origin: center;
        animation: jn-aleteo .4s ease-in-out infinite alternate;}
      @keyframes jn-vuelo {
        from {transform: translate(-30px, 0);}
        to {transform: translate(370px, -18px);}
      }
      @keyframes jn-aleteo {
        from {transform: scaleY(1);}
        to {transform: scaleY(.3);}
      }
      .jn-bote {transform-box: fill-box; transform-origin: center bottom;
        animation: jn-bote var(--dur) ease-in-out infinite; animation-delay: var(--delay);}
      @keyframes jn-bote {
        0%, 100% {transform: translateY(0) rotate(-.9deg);}
        50% {transform: translateY(-1.6px) rotate(1deg);}
      }
      .jn-camina {animation: jn-camina 18s linear infinite;}
      @keyframes jn-camina {
        0% {transform: translateX(0) scaleX(1);}
        47% {transform: translateX(58px) scaleX(1);}
        50% {transform: translateX(58px) scaleX(-1);}
        97% {transform: translateX(0) scaleX(-1);}
        100% {transform: translateX(0) scaleX(1);}
      }
      .jn-pierna {transform-box: fill-box; transform-origin: center top;
        animation: jn-paso .55s ease-in-out infinite alternate;}
      .jn-pierna + .jn-pierna {animation-direction: alternate-reverse;}
      @keyframes jn-paso {
        from {transform: rotate(-24deg);}
        to {transform: rotate(24deg);}
      }
      .jn-respira {animation: jn-respira 3.2s ease-in-out infinite;}
      @keyframes jn-respira {
        0%, 100% {transform: translateY(0);}
        50% {transform: translateY(-.7px);}
      }
      .jn-pez-nada {animation: jn-nada-der var(--nado) linear infinite;
        animation-delay: var(--retraso);}
      .jn-pez--izq .jn-pez-nada {animation-name: jn-nada-izq;}
      @keyframes jn-nada-der {
        from {transform: translateX(-70px);}
        to {transform: translateX(410px);}
      }
      @keyframes jn-nada-izq {
        from {transform: translateX(410px);}
        to {transform: translateX(-70px);}
      }
      .jn-pez-cuerpo {transform-box: fill-box; transform-origin: center;
        animation: jn-cuerpo-calma var(--cuerpo) ease-in-out infinite;}
      .jn-pez--incomodo .jn-pez-cuerpo {animation-name: jn-cuerpo-incomodo;}
      .jn-pez--asustado .jn-pez-cuerpo {animation-name: jn-cuerpo-asustado;}
      @keyframes jn-cuerpo-calma {
        0%, 100% {transform: translateY(0) rotate(0);}
        50% {transform: translateY(-1.8px) rotate(-2.5deg);}
      }
      @keyframes jn-cuerpo-incomodo {
        0%, 100% {transform: translateY(-1px) rotate(-5deg);}
        50% {transform: translateY(3px) rotate(6deg);}
      }
      @keyframes jn-cuerpo-asustado {
        0%, 100% {transform: translateY(-3px) rotate(-11deg);}
        50% {transform: translateY(4px) rotate(11deg);}
      }
      .fish-tail {transform-box: fill-box; transform-origin: right center;
        animation: fish-tail var(--cola) ease-in-out infinite alternate;}
      .fish-fin {transform-box: fill-box; transform-origin: center bottom;
        animation: fish-fin var(--aleta) ease-in-out infinite alternate;}
      @keyframes fish-tail {
        from {transform: rotate(-28deg);}
        to {transform: rotate(28deg);}
      }
      @keyframes fish-fin {
        from {transform: rotate(-12deg) scaleY(.9);}
        to {transform: rotate(12deg) scaleY(1.08);}
      }
      .jn-alerta {transform-box: fill-box; transform-origin: center;
        animation: jn-alerta .7s ease-in-out infinite alternate;}
      @keyframes jn-alerta {
        from {transform: scale(.85);}
        to {transform: scale(1.2);}
      }
      .jn-burbuja {animation: jn-burbuja var(--dur) ease-in infinite; animation-delay: var(--delay);}
      @keyframes jn-burbuja {
        0% {transform: translateY(0); opacity: 0;}
        12% {opacity: .8;}
        90% {opacity: .5;}
        100% {transform: translateY(calc(var(--sube) * -1)); opacity: 0;}
      }
      @media (prefers-reduced-motion: reduce) {
          .jn-ola, .jn-ave path, .jn-bote, .jn-camina, .jn-pierna, .jn-respira,
          .jn-pez-cuerpo, .fish-tail, .fish-fin, .jn-alerta, .jn-burbuja {
            animation: none;
          }
          .jn-ave {display: none;}
          .jn-nube {animation: none; transform: translateX(var(--reposo));}
          .jn-pez-nada {animation: none; transform: translateX(var(--reposo));}
          .jn-burbuja {opacity: .5;}
      }
      @media (max-width: 640px) {
        .block-container {padding: 1.25rem 1rem 2rem;}
        h1 {font-size: 1.8rem !important;}
        .reading-card {padding: 1.2rem;}
      }
    </style>
    """,
    unsafe_allow_html=True,
)


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

    requeridos_actual = (
        "time", "temperature_2m", "relative_humidity_2m",
        "precipitation", "weather_code", "wind_speed_10m",
    )
    if any(actual.get(clave) is None for clave in requeridos_actual):
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
                "latitude": ",".join(f"{latitud:.5f}" for latitud in lote["Latitud"]),
                "longitude": ",".join(f"{longitud:.5f}" for longitud in lote["Longitud"]),
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


def estimar_tendencia_nivel(
    niveles: pd.DataFrame,
) -> tuple[str, str]:
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
        dias_entre_lecturas = (
            lectura_b["Fecha"] - lectura_a["Fecha"]
        ).total_seconds() / 86400
        if dias_entre_lecturas > 0:
            pendientes.append(
                (float(lectura_b["Nivel_cm"]) - float(lectura_a["Nivel_cm"]))
                / dias_entre_lecturas
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


def aplicar_estilo_grafica(fig: go.Figure) -> None:
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#ffffff",
        font=dict(family="Arial, sans-serif", color="#455d6b", size=12),
        showlegend=True,
        legend=dict(
            orientation="h",
            x=1,
            y=1.02,
            xanchor="right",
            yanchor="bottom",
            font=dict(size=11, color="#455d6b"),
            bgcolor="rgba(255,255,255,0.75)",
        ),
    )
    estilo_ejes = {
        "gridcolor": "#e6ebee",
        "gridwidth": 0.6,
        "zeroline": False,
        "showline": True,
        "linecolor": "#aebbc2",
        "linewidth": 0.8,
        "ticks": "outside",
        "tickcolor": "#aebbc2",
        "tickwidth": 0.8,
        "ticklen": 3,
        "showticklabels": True,
        "tickfont": dict(size=11, color="#455d6b"),
        "automargin": True,
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
    fig.update_layout(
        height=300,
        margin=dict(l=64, r=20, t=48, b=40),
        hovermode="x unified",
    )
    fig.update_xaxes(
        title_text="Hora local",
        tickformat="%H:%M",
        fixedrange=True,
    )
    fig.update_yaxes(
        title_text="Precipitación media acumulada (mm)",
        rangemode="tozero",
        fixedrange=True,
    )
    aplicar_estilo_grafica(fig)
    return fig


def limpiar_niveles(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    df["Nivel_cm"] = pd.to_numeric(df["Nivel_cm"], errors="coerce")
    df["Nivel_cm"] = df["Nivel_cm"].replace([float("inf"), float("-inf")], pd.NA)
    df = df.dropna(subset=["Fecha", "Nivel_cm"]).copy()
    df["Nivel_cm"] = df["Nivel_cm"].astype(float)
    escala_x100 = (
        df["Nivel_cm"].abs().gt(2000)
        & df["Nivel_cm"].abs().le(200_000)
    )
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


def calcular_umbrales(_df: pd.DataFrame) -> dict:
    """Devuelve únicamente las cotas oficiales configuradas, en centímetros."""
    oficiales = {"amarilla": UMBRAL_AMARILLA_CM, "naranja": UMBRAL_NARANJA_CM, "roja": UMBRAL_ROJA_CM}
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


def clasificar_estado_peces(nivel_cm: float, cambio_cm: float) -> tuple[str, str]:
    if nivel_cm > 900:
        return "scared", "asustados"
    if cambio_cm < 0:
        return "uncomfortable", "incómodos"
    return "calm", "tranquilos"


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


def _persona_svg(
    camisa: str, pantalon: str, piel: str = "#c68a63",
    camina: bool = False, sentada: bool = False,
) -> str:
    """Figura de unos 22 px de alto con los pies en (0, 0)."""
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


def _ola_path(amplitud: float, periodo: float, ciclos: int, espesor: float = 16) -> str:
    """Onda continua de 340 px de ciclo exacto: el desplazamiento de -340 px es un bucle sin saltos."""
    mitad = periodo / 2
    d = f"M0 0Q{mitad / 2:.2f} {-amplitud:.2f} {mitad:.2f} 0"
    d += "".join(f"T{mitad * (i + 2):.2f} 0" for i in range(ciclos * 2 - 1))
    return f"{d}V{espesor}H0Z"


@lru_cache(maxsize=1)
def _escena_fija_svg() -> str:
    """Cielo, ciudad, muralla, talud con escalera, enrocado y lecho: no dependen del nivel."""
    rng = random.Random(29037020)

    # ── Talud: grava, hierba y surcos de erosión
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

    # ── Enrocado de piedra al pie del talud
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

    # ── Escalera que baja de la muralla al talud (vista de perfil)
    peldanos, dx, dy, x0, y0 = 10, 5.6, 11.2, 172.0, 190.0
    borde = [(x0, y0)]
    for i in range(peldanos):
        borde.append((x0 + (i + 1) * dx, y0 + i * dy))
        borde.append((x0 + (i + 1) * dx, y0 + (i + 1) * dy))
    inferior = [(px, py + 19) for px, py in reversed(borde)]
    puntos_escalera = " ".join(f"{px:.1f},{py:.1f}" for px, py in borde + inferior)
    postes = "".join(
        f"M{x0 + (i + 1) * dx:.1f} {y0 + i * dy:.1f}v-15" for i in range(0, peldanos, 2)
    )
    xf, yf = x0 + peldanos * dx, y0 + peldanos * dy

    # ── Ciudad
    ventanas_blancas = "".join(
        _ventana_svg(x, 138, 14, 20, marco="#cfe0ea", vidrio="#35617b") for x in (166, 196, 226, 256, 286)
    )
    merlones = "".join(
        f'<rect x="{x}" y="105" width="9" height="10" fill="#c3d8e4"/>' for x in range(156, 336, 15)
    )
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
        '<stop offset="0" stop-color="#17527c"/><stop offset=".55" stop-color="#6cb0d3"/>'
        '<stop offset="1" stop-color="#bfe0ee"/></linearGradient>'
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
        # Cielo, título, nubes y aves
        '<rect width="340" height="200" fill="url(#jn-cielo)"/>',
        '<text x="20" y="27" font-size="12" font-weight="700" letter-spacing="2" fill="#ffffff" '
        'font-family="Arial, sans-serif">NIVEL DEL RÍO</text>',
        '<text x="20" y="42" font-size="9" letter-spacing="1" fill="#dcedf6" '
        f'font-family="Arial, sans-serif">CALAMAR · BOLÍVAR · IDEAM {ESTACION_CODIGO}</text>',
        '<g class="jn-nube" style="--dur:95s;--delay:-34s;--reposo:70px"><g transform="translate(0 68)">'
        '<ellipse cx="0" cy="0" rx="24" ry="6.5" fill="#fff" opacity=".85"/>'
        '<ellipse cx="10" cy="-5" rx="14" ry="7" fill="#fff" opacity=".9"/>'
        '<ellipse cx="-11" cy="-3" rx="12" ry="5.5" fill="#fff" opacity=".85"/></g></g>',
        '<g class="jn-nube" style="--dur:120s;--delay:-80s;--reposo:250px"><g transform="translate(0 94)">'
        '<ellipse cx="0" cy="0" rx="19" ry="5" fill="#fff" opacity=".7"/>'
        '<ellipse cx="8" cy="-4" rx="11" ry="5.5" fill="#fff" opacity=".75"/></g></g>',
        # Ciudad: edificio trasero, edificio blanco almenado, edificio amarillo y edificio verde
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
        '<rect x="0" y="130" width="68" height="56" fill="#85c6a4"/>'
        '<rect x="0" y="126" width="68" height="5" fill="#e6f0e2"/>'
        '<rect x="0" y="116" width="68" height="2.4" fill="#f2f6ef"/>'
        f'<path d="{postes_verde}" stroke="#f2f6ef" stroke-width="1.5"/>'
        f'{ventanas_verde}'
        '<rect x="0" y="174" width="68" height="12" fill="#6aae8d"/>',
        # Puestos sobre la muralla: toldo naranja y lona azul
        '<path d="M196 186L205 169H258L267 186Z" fill="#d4673f"/>'
        '<path d="M214 169L211 186M226 169L225 186M238 169L238 186M250 169L252 186" '
        'stroke="#f1d3c3" stroke-width="1.6" opacity=".7"/>'
        '<path d="M82 186L86 175H112L116 186Z" fill="#3b6fb0"/>',
        # Muralla (10 m)
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
        # Talud
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
        # Enrocado y lecho del río
        '<rect x="0" y="362" width="340" height="110" fill="#59625d"/>',
        "".join(piedras),
        '<rect x="0" y="360" width="340" height="4" fill="#6d6a5b"/>'
        '<rect x="0" y="400" width="340" height="72" fill="url(#jn-humedad)"/>'
        '<path d="M0 466Q40 459 90 465T200 464T340 461V500H0Z" fill="url(#jn-lecho)"/>'
        '<circle cx="52" cy="482" r="2.4" fill="#b19a78" opacity=".7"/>'
        '<circle cx="171" cy="488" r="3" fill="#a08a69" opacity=".7"/>'
        '<circle cx="268" cy="480" r="2.2" fill="#b19a78" opacity=".7"/>',
        # Escalera con baranda
        f'<polygon points="{puntos_escalera}" fill="#d6cfba" stroke="#7a7260" stroke-width=".9" stroke-linejoin="round"/>'
        f'<path d="M{x0:.1f} {y0 - 15:.1f}L{xf:.1f} {yf - 15:.1f}{postes}" stroke="#2f414c" '
        'stroke-width="1.5" fill="none" stroke-linecap="round"/>',
        # Aves
        '<g class="jn-ave" style="--dur:30s;--delay:-8s"><g transform="translate(0 84)">'
        '<path d="M0 0q3 -3.2 6 0q3 -3.2 6 0" fill="none" stroke="#173a52" stroke-width="1.2" '
        'stroke-linecap="round"/></g></g>'
        '<g class="jn-ave" style="--dur:38s;--delay:-21s"><g transform="translate(0 102)">'
        '<path d="M0 0q2.5 -2.6 5 0q2.5 -2.6 5 0" fill="none" stroke="#173a52" stroke-width="1" '
        'stroke-linecap="round"/></g></g>',
    ])


def _compactar_html(html: str) -> str:
    """Quita sangrías y líneas vacías para que Markdown trate todo como un solo bloque HTML."""
    return "\n".join(linea.strip() for linea in html.splitlines() if linea.strip())


def crear_medidor_html(
    nivel_cm: float,
    umbrales: dict,
    estado_peces: str,
    estado_peces_texto: str,
) -> str:
    """Escena animada de Calamar: el nivel (0–10 m) sube por el talud hasta la muralla."""
    y_cero, y_muralla, y_fondo = 452.0, 186.0, 482.0
    px_por_cm = (y_cero - y_muralla) / NIVEL_MURALLA_CM
    posicion = lambda cm: y_cero - cm * px_por_cm
    y_s = posicion(max(0.0, min(nivel_cm, NIVEL_MURALLA_CM * 1.12)))
    sobre_muralla = nivel_cm > NIVEL_MURALLA_CM

    # ── Personas: solo se dibujan si el agua no las cubre
    gente = []
    if y_s > 192:
        gente.append(
            '<g transform="translate(160 186)"><g class="jn-respira">'
            f'{_persona_svg("#26394a", "#1d2a35")}</g></g>'
        )
    if y_s > 303:
        gente.append(
            '<g transform="translate(262 299)"><g class="jn-camina">'
            f'{_persona_svg("#3f7fc0", "#59606a", camina=True)}</g></g>'
        )

    botes = "".join(
        _bote_svg(x, y_s, tipo, retraso, duracion)
        for x, tipo, retraso, duracion in (
            (42, "a", -0.4, 3.7), (96, "b", -1.9, 4.3), (160, "c", -3.1, 4.9),
        )
    )

    # ── Peces (mismas especies y estados de ánimo que antes)
    perfiles_peces = [
        {
            "especie": "bocachico", "ancho": 40, "alto": 20, "profundidad": 68, "sentido": "der",
            "nado": 1.0, "fase": 0.15, "reposo": 40,
            "colas": (0.38, 0.18, 0.08), "aletas": (0.66, 0.32, 0.14), "cuerpos": (1.7, 0.8, 0.38),
            "partes": """
                <path class="fish-tail" d="M9 12 2 5v14l7-7Z" fill="#dc8e43"/>
                <path d="M7 12C14 4 32 5 42 12 32 19 14 20 7 12Z" fill="#f2c65d"/>
                <path class="fish-fin" d="m17 7 5-5 6 5Z" fill="#e99d49"/>
                <path class="fish-fin" d="m19 17 5 5 5-5Z" fill="#e99d49"/>
                <path d="M19 8v8m5-9v10m5-9v8" stroke="#d69345" stroke-width="1"/>
                <circle cx="36" cy="10" r="1.2" fill="#17384a"/>
            """,
        },
        {
            "especie": "bagre", "ancho": 44, "alto": 18, "profundidad": 51, "sentido": "izq",
            "nado": 1.25, "fase": 0.55, "reposo": 230,
            "colas": (0.52, 0.22, 0.09), "aletas": (0.82, 0.36, 0.16), "cuerpos": (2.1, 0.9, 0.42),
            "partes": """
                <path class="fish-tail" d="M9 12 2 6v12l7-6Z" fill="#4a8f91"/>
                <path d="M8 12C15 6 34 7 41 12 34 17 15 18 8 12Z" fill="#8fc2b4"/>
                <path class="fish-fin" d="m17 8 5-5 5 5Z" fill="#477f83"/>
                <path class="fish-fin" d="m20 16 4 5 4-5Z" fill="#477f83"/>
                <path d="M36 10Q42 6 47 7M36 14Q42 18 47 17" fill="none" stroke="#d8d2a7" stroke-width="1"/>
                <circle cx="36" cy="10" r="1.1" fill="#102b3b"/>
            """,
        },
        {
            "especie": "mojarra", "ancho": 34, "alto": 22, "profundidad": 35, "sentido": "der",
            "nado": 0.85, "fase": 0.8, "reposo": 130,
            "colas": (0.3, 0.16, 0.07), "aletas": (0.58, 0.28, 0.13), "cuerpos": (1.5, 0.72, 0.34),
            "partes": """
                <path class="fish-tail" d="M11 12 3 6v12l8-6Z" fill="#e98650"/>
                <ellipse cx="25" cy="12" rx="15" ry="9" fill="#f5bd68"/>
                <path class="fish-fin" d="m14 7 3-5 4 5 4-6 4 6 4-4 3 7Z" fill="#dc8050"/>
                <path class="fish-fin" d="m21 18 5 5 4-6Z" fill="#e98650"/>
                <path d="M20 5v14m6-14v14m6-12v10" stroke="#db9456" stroke-width="1"/>
                <circle cx="35" cy="9" r="1.2" fill="#17384a"/>
            """,
        },
        {
            "especie": "sabalo", "ancho": 45, "alto": 17, "profundidad": 20, "sentido": "izq",
            "nado": 1.1, "fase": 0.35, "reposo": 290,
            "colas": (0.46, 0.2, 0.085), "aletas": (0.72, 0.34, 0.15), "cuerpos": (1.9, 0.84, 0.4),
            "partes": """
                <path class="fish-tail" d="M9 12 2 4v16l7-8Z" fill="#6ba6ad"/>
                <path d="M7 12C16 6 35 7 43 12 35 17 16 18 7 12Z" fill="#b9d6c9"/>
                <path class="fish-fin" d="m20 8 4-5 5 5Z" fill="#6ba6ad"/>
                <path class="fish-fin" d="m23 16 4 5 4-5Z" fill="#6ba6ad"/>
                <path d="M17 12h19m-13-3v6m6-6v6" stroke="#6b9fa4" stroke-width=".9"/>
                <circle cx="37" cy="10" r="1" fill="#17384a"/>
            """,
        },
    ]
    indice = {"calm": 0, "uncomfortable": 1, "scared": 2}[estado_peces]
    clase_estado = ("calma", "incomodo", "asustado")[indice]
    nado_base = (30.0, 21.0, 11.0)[indice]
    peces = []
    for pez in perfiles_peces:
        ancho, alto = pez["ancho"], pez["alto"]
        y_centro = y_fondo - pez["profundidad"] / 100 * (y_fondo - y_s)
        y_centro = min(max(y_centro, y_s + 14 + alto / 2), y_fondo - alto / 2)
        izquierda = pez["sentido"] == "izq"
        escala = ancho / 48
        if izquierda:
            transformacion = f"translate({ancho} 0) scale({-escala:.3f} {escala:.3f})"
            x_cabeza = ancho * 0.12
        else:
            transformacion = f"scale({escala:.3f})"
            x_cabeza = ancho * 0.88
        duracion = nado_base * pez["nado"]
        alerta = ""
        if estado_peces == "scared":
            alerta = (
                f'<g transform="translate({x_cabeza:.1f} -4)"><g class="jn-alerta">'
                '<circle r="5.5" fill="#fff3e0"/>'
                '<text y="3.2" text-anchor="middle" font-size="9" font-weight="700" fill="#b5432f" '
                'font-family="Arial, sans-serif">!</text></g></g>'
            )
        estilo = (
            f"--nado:{duracion:.1f}s;--retraso:-{duracion * pez['fase']:.1f}s;"
            f"--cuerpo:{pez['cuerpos'][indice]}s;--cola:{pez['colas'][indice]}s;"
            f"--aleta:{pez['aletas'][indice]}s;--reposo:{pez['reposo']}px;"
        )
        peces.append(
            f'<g transform="translate(0 {y_centro - alto / 2:.1f})" '
            f'class="jn-pez jn-pez--{clase_estado} jn-pez--{pez["sentido"]} jn-pez--{pez["especie"]}" '
            f'style="{estilo}"><g class="jn-pez-nada"><g class="jn-pez-cuerpo">'
            f'<g transform="{transformacion}">{pez["partes"]}</g></g>{alerta}</g></g>'
        )

    # ── Burbujas
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

    # ── Agua: cuerpo translúcido, destellos y dos olas
    destellos = "".join(f"M{k * 85 + 10} 9h14M{k * 85 + 48} 17h9M{k * 85 + 28} 27h11" for k in range(8))
    agua = (
        '<defs><linearGradient id="jn-agua" gradientUnits="userSpaceOnUse" '
        f'x1="0" y1="{y_s:.1f}" x2="0" y2="500">'
        '<stop offset="0" stop-color="#2aa3b4" stop-opacity=".62"/>'
        '<stop offset=".45" stop-color="#127a91" stop-opacity=".8"/>'
        '<stop offset="1" stop-color="#0c4057" stop-opacity=".93"/></linearGradient></defs>'
        f'<rect x="0" y="{y_s:.1f}" width="340" height="{500 - y_s:.1f}" fill="url(#jn-agua)"/>'
        f'<g transform="translate(0 {y_s:.1f})"><g class="jn-ola" style="--dur:16s">'
        f'<path d="{destellos}" stroke="#ffffff" stroke-opacity=".3" stroke-width="1" '
        'stroke-linecap="round" fill="none"/></g></g>'
    )
    ola_atras = (
        f'<g transform="translate(0 {y_s:.1f})"><g class="jn-ola" style="--dur:13s;--delay:-4s">'
        f'<path d="{_ola_path(2.4, 68, 10, 12)}" fill="#63cbd6" opacity=".38"/></g></g>'
    )
    ola_frente = (
        f'<g transform="translate(0 {y_s:.1f})"><g class="jn-ola" style="--dur:8s">'
        f'<path d="{_ola_path(3.2, 85, 8, 14)}" fill="#3bb7c8" fill-opacity=".5" '
        'stroke="#ffffff" stroke-opacity=".75" stroke-width="1.1"/></g></g>'
    )

    # ── Regla de nivel (izquierda) y etiquetas (derecha)
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
        {"y": posicion(NIVEL_MURALLA_CM), "texto": "MURALLA SUPERADA" if sobre_muralla else "MURALLA 10 m",
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
    # Separa las etiquetas para que no se encimen: primero hacia abajo, luego hacia arriba si hace falta.
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
    <div class="gauge-panel" role="img" aria-label="Escena animada de Calamar. Nivel del río: {nivel_cm:.1f} centímetros; la muralla está a 10 metros. Peces {estado_peces_texto}.">
      <svg class="gauge-scene" viewBox="0 0 340 500" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
        {_escena_fija_svg()}
        {''.join(gente)}
        {ola_atras}
        {botes}
        {agua}
        {''.join(peces)}
        {''.join(burbujas)}
        {ola_frente}
        {''.join(lineas)}
        {regla}
        {''.join(etiquetas_svg)}
      </svg>
    </div>
    """
    return _compactar_html(html)


# ═══════════════════════════ CARGA ═══════════════════════════
icon_data = base64.b64encode(JUAN_ICON_PATH.read_bytes()).decode("ascii")
cover_data = base64.b64encode(JUAN_COVER_PATH.read_bytes()).decode("ascii")
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

if not CSV_PATH.exists():
    st.error("Todavía no hay datos. Ejecute el workflow «Actualizar datos nivel río Calamar» en GitHub Actions.")
    st.stop()

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
if len(df) < 2:
    st.warning("Hay muy pocos datos para mostrar el tablero.")
    st.stop()

ultimo = df.iloc[-1]
nivel_cm = float(ultimo["Nivel_cm"])
fecha_ult = ultimo["Fecha"]
ts_ult = ultimo["Ultima_lectura"] if pd.notna(ultimo["Ultima_lectura"]) else fecha_ult

# Variación vs. día anterior (si falta ese día, se usa el último dato disponible previo).
previo = df.iloc[-2]
dias_diff = (fecha_ult - previo["Fecha"]).days
delta_cm = nivel_cm - float(previo["Nivel_cm"])
ref_txt = "el día anterior" if dias_diff == 1 else f"el {fecha_es(previo['Fecha'])}"
estado_peces, estado_peces_texto = clasificar_estado_peces(nivel_cm, delta_cm)

edad_dias = (pd.Timestamp.now().normalize() - fecha_ult.normalize()).days
umbrales = calcular_umbrales(df)

col_medidor, col_lectura = st.columns([0.9, 1.1], gap="large")
with col_medidor:
    st.markdown(
        crear_medidor_html(
            nivel_cm, umbrales, estado_peces, estado_peces_texto
        ),
        unsafe_allow_html=True,
    )
    st.caption("Escala: 0–10 m. La muralla de Calamar está a 10 m (1000 cm).")

with col_lectura:
    fecha_texto = fecha_es(ts_ult, con_hora=pd.notna(ultimo["Ultima_lectura"]))
    cambio_texto = "Sin variación" if delta_cm == 0 else (
        f"{'Subió' if delta_cm > 0 else 'Bajó'} {abs(delta_cm):.1f} cm {ref_txt}"
    )
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
            <strong>Fuente</strong><br>{ultimo["Fuente"]}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    banner(evaluar(nivel_cm, umbrales))

if edad_dias > DIAS_MAX_SIN_DATOS:
    st.warning(
        f"El último dato publicado por el IDEAM tiene {edad_dias} días; "
        "puede no representar el nivel actual del río."
    )

# ═════════════════════════════ VISOR FEWS ═════════════════════════════
st.subheader("Visor FEWS IDEAM · Calamar")
st.caption(
    "Ubicación de la estación y serie consolidada de nivel observado publicada por FEWS IDEAM. "
    "Las lecturas de FEWS son preliminares, pueden ser corregidas y no son una medición en tiempo real."
)
mapa_estacion = pd.DataFrame(
    [
        {
            "lat": ESTACION_LATITUD,
            "lon": ESTACION_LONGITUD,
            "Estación": f"CALAMAR [{ESTACION_CODIGO}]",
            "Altitud (m s. n. m.)": ESTACION_ALTITUD_MSNM,
        }
    ]
)
boton_actualizar, enlace_fews = st.columns(2)
if boton_actualizar.button("Actualizar ahora", key="consultar_fews"):
    cargar_nivel_fews_calamar.clear()
    st.rerun()
enlace_fews.link_button("Abrir visor FEWS nacional", FEWS_VISOR_URL, width="stretch")

if error_fews is not None:
    st.caption("No se pudo consultar FEWS; mostrando el último dato guardado.")

mapa_col, nivel_col = st.columns([1.2, 0.8], gap="large")
with mapa_col:
    st.caption(
        f"Estación {ESTACION_NOMBRE} · Código IDEAM {ESTACION_CODIGO} · "
        f"{ESTACION_LATITUD:.6f}, {ESTACION_LONGITUD:.6f} · "
        f"{ESTACION_ALTITUD_MSNM} m s. n. m."
    )
    st.map(
        mapa_estacion,
        latitude="lat",
        longitude="lon",
        color="#167f94",
        size=120,
        zoom=14,
        height=420,
    )
with nivel_col:
    if datos_fews is not None:
        lectura_fews = datos_fews.iloc[-1]
        st.metric("Último nivel observado FEWS", f"{lectura_fews['Nivel_cm']:.1f} cm")
        st.caption(f"Fecha de lectura: {fecha_es(lectura_fews['Fecha'], con_hora=True)}")
        st.caption(
            "Consulta FEWS: "
            f"{fecha_es(datos_fews['Consultado_en'].iloc[0], con_hora=True)}"
        )
        st.caption("Serie consolidada · unidad original: metros, convertida a centímetros.")
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
    fig_fews = go.Figure(
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
    fig_fews.update_layout(
        height=360,
        margin=dict(l=60, r=20, t=48, b=40),
        hovermode="x",
        yaxis=dict(title="Nivel observado (cm)"),
    )
    aplicar_estilo_grafica(fig_fews)
    st.plotly_chart(
        fig_fews,
        width="stretch",
        config={"displayModeBar": False},
    )
    st.caption(
        f"Fuente: [FEWS IDEAM]({FEWS_VISOR_URL}). "
        "La consulta se conserva en caché durante 5 minutos."
    )

# ═══════════════════════ METEOROLOGÍA Y TENDENCIA ═══════════════════════
st.subheader("Lluvia prevista y tendencia observada del río")
st.caption(
    "La lluvia se calcula para toda el área hidrográfica Magdalena-Cauca: promedio espacial "
    "ponderado por el área de sus 105 subzonas IDEAM, acumulado para las próximas 24 horas."
)
try:
    with st.spinner("Consultando condiciones meteorológicas y pronóstico..."):
        tiempo_actual = cargar_meteorologia()
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
else:
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

# ═══════════════════════════ GRÁFICA ═══════════════════════════
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
estilos = {"amarilla": ("#d4a017", "Amarilla"), "naranja": ("#e8710a", "Naranja"), "roja": ("#c62828", "Roja")}
y_vals = list(datos_grafica["Nivel_cm"])
for k, (color, nombre) in estilos.items():
    val = umbrales["valores"][k]
    if val is None:
        continue
    y_vals.append(val)
    fig.add_hline(y=val, line_dash="dot", line_color=color, line_width=1,
                  annotation_text=f"{nombre} {val:.0f} cm", annotation_position="top left",
                  annotation_font=dict(color=color, size=11))
y_vals.append(float(NIVEL_REFERENCIA_CM))
fig.add_hline(
    y=NIVEL_REFERENCIA_CM,
    line_dash="dash",
    line_color="#718a98",
    line_width=1,
    annotation_text="Referencia · 950 cm",
    annotation_position="top left",
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
cfg = {"displayModeBar": False}
try:
    st.plotly_chart(fig, width="stretch", config=cfg)
except TypeError:   # versiones antiguas de Streamlit
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
    st.caption(f"Hora de última lectura: {fecha_es(ts_ult, con_hora=True)}")
    if datos_fews is not None:
        st.caption(
            "FEWS consultado: "
            f"{fecha_es(datos_fews['Consultado_en'].iloc[0], con_hora=True)}."
        )
    else:
        st.caption("No se pudo consultar FEWS; mostrando el último dato guardado.")

with st.expander("Ver umbrales usados"):
    for k, (_, nombre) in estilos.items():
        v, o = umbrales["valores"][k], umbrales["origen"][k]
        st.write(f"**{nombre}:** {'—' if v is None else f'{v:.0f} cm'} ({o})")

# ═══════════════════════════ COMPARTIR / DESCARGAR ═══════════════════════════
st.divider()
b1, b2 = st.columns(2)
b1.download_button("Descargar histórico (CSV)", data=df.assign(Fecha=df["Fecha"].dt.strftime("%Y-%m-%d %H:%M"))
                   .to_csv(index=False).encode("utf-8"),
                   file_name="nivel_calamar.csv", mime="text/csv")
if APP_URL:
    msg = f"Nivel del río Magdalena en Calamar: {nivel_cm:.0f} cm ({nivel_cm / 100:.2f} m). Consulte aquí: {APP_URL}"
    b2.link_button("Compartir por WhatsApp", f"https://wa.me/?text={quote(msg)}")
else:
    b2.caption("Para compartir: copie el enlace de esta página y envíelo por WhatsApp.")

# ═══════════════════════════ PIE ═══════════════════════════
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