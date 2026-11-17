"""
app.py — JUAN: nivel del río Magdalena en Calamar (Bolívar)
Tablero ciudadano mobile-first. Datos: IDEAM, estación 29037020 (nivel medio diario, cm).
"""
from __future__ import annotations

import base64
import math
from pathlib import Path
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
JUAN_ICON_PATH = Path(__file__).parent / "assets" / "juan_icon.png"
JUAN_COVER_PATH = Path(__file__).parent / "assets" / "juan_portada.webp"
CSV_PATH = Path(__file__).with_name("nivel_calamar.csv")
SUBZONAS_CUENCA_PATH = Path(__file__).parent / "assets" / "subzonas_magdalena_cauca.csv"
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

# URL pública de la app (pegar aquí la de Streamlit Cloud para el botón de WhatsApp).
APP_URL = ""

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
    page_title="JUAN | Nivel del río en Calamar",
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
      .gauge-panel {position: relative; width: min(100%, 340px); height: 500px; margin: 0 auto;
        overflow: hidden; border-radius: 16px; background: #102b3b; color: #d7e5eb;
        font-family: Arial, sans-serif;}
      .gauge-title {position: absolute; top: 20px; left: 23px; font-size: 12px;
        font-weight: 700; letter-spacing: 2px;}
      .gauge-subtitle {position: absolute; top: 39px; left: 23px; color: #91aeba;
        font-size: 10px; letter-spacing: 1px;}
      .gauge-track {position: absolute; top: 74px; bottom: 52px; left: 132px; width: 64px;
        overflow: hidden; border: 1px solid #527284; border-radius: 16px; background: #1b3d4e;}
      .gauge-water {position: absolute; right: 0; bottom: 0; left: 0; overflow: visible;
        background: #087f98;}
      .gauge-wave {position: absolute; top: -8px; left: -50%; width: 200%; height: 18px;
        border-radius: 48%; background: #16a6bd; animation: gauge-drift 4.8s ease-in-out infinite;}
      .gauge-wave-back {top: -5px; left: -55%; height: 16px; opacity: .55;
        background: #42c7d2; animation: gauge-drift-back 6.4s ease-in-out infinite;}
      @keyframes gauge-drift {
        0%, 100% {transform: translateX(-8%) rotate(-2deg);}
        50% {transform: translateX(8%) rotate(2deg);}
      }
      @keyframes gauge-drift-back {
        0%, 100% {transform: translateX(8%) rotate(2deg);}
        50% {transform: translateX(-8%) rotate(-2deg);}
      }
      .gauge-tick {position: absolute; left: 88px; width: 38px; height: 1px;
        background: #b7cbd4; transform: translateY(-50%);}
      .gauge-scale {position: absolute; left: 24px; width: 54px; text-align: right;
        color: #d7e5eb; font-size: 11px; transform: translateY(-50%);}
      .gauge-current {position: absolute; left: 120px; width: 89px;
        border-top: 2px solid #effdff; transform: translateY(-50%);}
      .gauge-value {position: absolute; left: 216px; padding: 6px 8px; border-radius: 6px;
        background: #167f94; color: #fff; font-size: 13px; font-weight: 700;
        white-space: nowrap; transform: translateY(-50%);}
      @media (prefers-reduced-motion: reduce) {
        .gauge-wave {animation: none;}
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
    precipitacion_cuenca_mm: float,
) -> tuple[str, str]:
    fecha_ultima = niveles["Fecha"].iloc[-1]
    ahora = pd.Timestamp.now(tz=METEO_ZONA_HORARIA).tz_localize(None).normalize()
    dias_desactualizado = max((ahora - fecha_ultima.normalize()).days, 0)
    if dias_desactualizado > 2:
        return "Sin estimación", (
            f"La última lectura del río tiene {dias_desactualizado} días; "
            "no es suficientemente reciente para estimar la dirección."
        )

    recientes = niveles[niveles["Fecha"] >= fecha_ultima - pd.Timedelta(days=3)]
    if len(recientes) < 2:
        return "Sin tendencia clara", "No hay suficientes lecturas recientes del río."

    dias = max((recientes["Fecha"].iloc[-1] - recientes["Fecha"].iloc[0]).days, 1)
    cambio_diario = (
        float(recientes["Nivel_cm"].iloc[-1]) - float(recientes["Nivel_cm"].iloc[0])
    ) / dias
    lluvia_prevista = precipitacion_cuenca_mm >= 2

    if cambio_diario > 0.5:
        return "Posible alza", (
            "Las últimas lecturas muestran una subida"
            + (" y se pronostican al menos 2 mm de lluvia media en la cuenca." if lluvia_prevista else ".")
        )
    if cambio_diario < -0.5:
        if lluvia_prevista:
            return "Incierto", (
                "El nivel venía bajando, pero se pronostican al menos 2 mm de lluvia media "
                "en la cuenca; podría cambiar la tendencia."
            )
        return "Posible baja", "Las últimas lecturas muestran una bajada y se pronostica poca lluvia media en la cuenca."
    if lluvia_prevista:
        return "Incierto", (
            "Las últimas lecturas no muestran una tendencia clara y se pronostican al menos "
            "2 mm de lluvia media en la cuenca."
        )
    return "Sin cambio claro", "Las últimas lecturas son estables y se pronostica poca lluvia media en la cuenca."


def crear_grafica_pronostico_cuenca(horas: pd.DataFrame) -> go.Figure:
    fig = go.Figure(
        go.Scatter(
            x=horas["FechaHora"],
            y=horas["Precipitacion_mm"].cumsum(),
            name="Lluvia media acumulada",
            mode="lines+markers",
            line=dict(color="#167f94", width=2.5),
            marker=dict(size=5),
            fill="tozeroy",
            fillcolor="rgba(22, 127, 148, 0.12)",
            hovertemplate="%{y:.1f} mm<extra></extra>",
        )
    )
    fig.update_layout(
        height=300,
        margin=dict(l=8, r=8, t=18, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#ffffff",
        hovermode="x unified",
        legend=dict(orientation="h", y=1.12, x=0),
        font=dict(family="Arial, sans-serif", color="#455d6b"),
    )
    fig.update_xaxes(
        title_text="Hora local",
        tickformat="%H:%M",
        gridcolor="#edf1f3",
        fixedrange=True,
    )
    fig.update_yaxes(
        title_text="Precipitación media acumulada (mm)",
        rangemode="tozero",
        gridcolor="#edf1f3",
        fixedrange=True,
    )
    return fig


@st.cache_data(ttl=1800, show_spinner=False)
def cargar_datos(path: str, mtime: float) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    df["Nivel_cm"] = pd.to_numeric(df["Nivel_cm"], errors="coerce")
    if "Ultima_lectura" in df.columns:
        df["Ultima_lectura"] = pd.to_datetime(df["Ultima_lectura"], errors="coerce")
    else:
        df["Ultima_lectura"] = pd.NaT
    return df.dropna(subset=["Fecha", "Nivel_cm"]).sort_values("Fecha").reset_index(drop=True)


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


def crear_medidor_html(nivel_cm: float, escala_max_cm: int, umbrales: dict) -> str:
    y_superior = 74
    y_inferior = 448
    alto_track = y_inferior - y_superior
    posicion = lambda valor: y_inferior - max(0, min(valor / escala_max_cm, 1)) * alto_track
    nivel_y = posicion(nivel_cm)

    marcas_html = []
    for marca in range(0, escala_max_cm + 1, 100):
        y = posicion(marca)
        marcas_html.append(
            f'<div class="gauge-tick" style="top:{y:.1f}px"></div>'
            f'<div class="gauge-scale" style="top:{y:.1f}px">{marca / 100:.0f}</div>'
        )

    alertas_html = []
    colores = {"amarilla": "#e6b84f", "naranja": "#f08c53", "roja": "#e26168"}
    for nombre, color in colores.items():
        valor = umbrales["valores"][nombre]
        if valor is None or not 0 <= valor <= escala_max_cm:
            continue
        y = posicion(valor)
        alertas_html.append(
            f'<div style="position:absolute;left:124px;top:{y:.1f}px;width:84px;'
            f'border-top:2px dotted {color};transform:translateY(-50%)"></div>'
        )

    return f"""
    <div class="gauge-panel" role="img" aria-label="Medidor del nivel del río: {nivel_cm:.1f} centímetros">
      <div class="gauge-title">NIVEL DEL RÍO</div>
      <div class="gauge-subtitle">CALAMAR · BOLÍVAR · IDEAM {ESTACION_CODIGO}</div>
      <div class="gauge-track">
        <div class="gauge-water" style="height:{max(0, min(nivel_cm / escala_max_cm, 1)):.4%}">
          <span class="gauge-wave gauge-wave-back"></span>
          <span class="gauge-wave"></span>
        </div>
      </div>
      {''.join(marcas_html)}
      {''.join(alertas_html)}
      <div class="gauge-current" style="top:{nivel_y:.1f}px"></div>
      <div class="gauge-value" style="top:{nivel_y:.1f}px">{nivel_cm / 100:.2f} m</div>
    </div>
    """


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
        <h2>Nivel del río en Calamar</h2>
        <p>{ESTACION_NOMBRE} · Estación IDEAM {ESTACION_CODIGO} · Nivel medio diario</p>
      </div>
    </section>
    """,
    unsafe_allow_html=True,
)

if not CSV_PATH.exists():
    st.error("Todavía no hay datos. Ejecute el workflow «Actualizar datos nivel río Calamar» en GitHub Actions.")
    st.stop()

df = cargar_datos(str(CSV_PATH), CSV_PATH.stat().st_mtime)
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

edad_dias = (pd.Timestamp.now().normalize() - fecha_ult.normalize()).days
umbrales = calcular_umbrales(df)
limites_configurados = [v for v in umbrales["valores"].values() if v is not None]
mayor_referencia = max([
    float(df["Nivel_cm"].max()),
    *limites_configurados,
])
escala_max_cm = max(1000, int(math.ceil(mayor_referencia / 100) * 100))

col_medidor, col_lectura = st.columns([0.9, 1.1], gap="large")
with col_medidor:
    st.markdown(
        crear_medidor_html(nivel_cm, escala_max_cm, umbrales),
        unsafe_allow_html=True,
    )
    st.caption(f"Escala visual: 0–{escala_max_cm / 100:.0f} m.")

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
            <strong>Variación</strong><br>{cambio_texto}
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

# ═════════════════════════════ MAPA ═════════════════════════════
st.subheader("Ubicación del limnímetro")
st.caption(
    f"Estación {ESTACION_NOMBRE} · Código IDEAM {ESTACION_CODIGO} · "
    f"{ESTACION_LATITUD:.6f}, {ESTACION_LONGITUD:.6f} · "
    f"{ESTACION_ALTITUD_MSNM} m s. n. m."
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
st.map(
    mapa_estacion,
    latitude="lat",
    longitude="lon",
    color="#167f94",
    size=120,
    zoom=14,
    height=420,
)
st.markdown(
    "[Abrir en OpenStreetMap]"
    f"(https://www.openstreetmap.org/?mlat={ESTACION_LATITUD}&mlon={ESTACION_LONGITUD}"
    f"#map=15/{ESTACION_LATITUD}/{ESTACION_LONGITUD}) · "
    "[Catálogo Nacional de Estaciones del IDEAM]"
    "(https://dhime.ideam.gov.co/server/rest/services/CNE/Estaciones/MapServer/0)"
)

# ═══════════════════════ METEOROLOGÍA Y TENDENCIA ═══════════════════════
st.subheader("Lluvia aguas arriba y tendencia del río · próximas 24 horas")
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
    st.caption("La tendencia combinada no está disponible sin el pronóstico de lluvia para la cuenca.")
else:
    lluvia_media_total = float(pronostico_horario["Precipitacion_mm"].sum())
    tendencia, motivo_tendencia = estimar_tendencia_nivel(
        df,
        lluvia_media_total,
    )
    clima, lluvia, nivel_futuro = st.columns(3)
    with clima:
        clima.metric("Condición en Calamar", describir_tiempo(int(tiempo_actual["weather_code"])))
        clima.caption(
            f"{float(tiempo_actual['temperature_2m']):.1f} °C · "
            f"humedad {int(tiempo_actual['relative_humidity_2m'])}% · "
            f"viento {float(tiempo_actual['wind_speed_10m']):.0f} km/h"
        )
    lluvia.metric("Lluvia media acumulada · cuenca · 24 h", f"{lluvia_media_total:.1f} mm")
    nivel_futuro.metric("Tendencia cualitativa · 24 h", tendencia)

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
          <div class="eyebrow">LECTURA DE LA ESTIMACIÓN</div>
          <p>{motivo_tendencia}</p>
          <p class="forecast-caveat">
            Indicador cualitativo, no pronóstico hidrológico oficial. Combina las lecturas
            recientes con la precipitación media areal pronosticada para el área hidrográfica
            Magdalena-Cauca. La zonificación completa no delimita el aporte exacto al limnímetro
            ni modela escorrentía, caudales, tiempos de tránsito o embalses; la lluvia no implica
            un cambio inmediato del nivel en Calamar.
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
datos_grafica["FechaTxt"] = datos_grafica["Fecha"].apply(fecha_es)
st.caption(
    f"{len(datos_grafica):,} registros · "
    f"{fecha_es(datos_grafica['Fecha'].iloc[0])} – {fecha_es(datos_grafica['Fecha'].iloc[-1])}"
)

fig = go.Figure(go.Scatter(
    x=datos_grafica["Fecha"], y=datos_grafica["Nivel_cm"],
    mode="lines+markers" if len(datos_grafica) <= 2000 else "lines",
    line=dict(color="#167f94", width=2.5),
    marker=dict(size=5, color="#167f94", line=dict(color="#fff", width=1)),
    customdata=datos_grafica["FechaTxt"],
    hovertemplate="<b>%{customdata}</b><br>Nivel: <b>%{y:.0f} cm</b><extra></extra>",
))
estilos = {"amarilla": ("#d4a017", "Amarilla"), "naranja": ("#e8710a", "Naranja"), "roja": ("#c62828", "Roja")}
y_vals = list(datos_grafica["Nivel_cm"])
for k, (color, nombre) in estilos.items():
    val = umbrales["valores"][k]
    if val is None:
        continue
    y_vals.append(val)
    fig.add_hline(y=val, line_dash="dot", line_color=color, line_width=2,
                  annotation_text=f"{nombre} {val:.0f} cm", annotation_position="top left",
                  annotation_font=dict(color=color, size=13))
y_vals.append(float(NIVEL_REFERENCIA_CM))
fig.add_hline(
    y=NIVEL_REFERENCIA_CM,
    line_dash="dash",
    line_color="#718a98",
    line_width=1.5,
    annotation_text="Referencia · 950 cm",
    annotation_position="top left",
    annotation_font=dict(color="#526b79", size=12),
)
rango = max(y_vals) - min(y_vals)
fig.update_layout(
    height=390, margin=dict(l=8, r=12, t=24, b=8), showlegend=False,
    hovermode="x", dragmode=False, hoverlabel=dict(font_size=16),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#ffffff",
    font=dict(family="Arial, sans-serif", color="#455d6b"),
    xaxis=dict(
        fixedrange=True,
        tickformat="%Y" if (datos_grafica["Fecha"].max() - datos_grafica["Fecha"].min()).days > 365 * 3 else "%d %b",
        gridcolor="#edf1f3", zeroline=False,
    ),
    yaxis=dict(
        fixedrange=True, title="Nivel (cm)",
        range=[min(y_vals) - 0.08 * rango, max(y_vals) + 0.12 * rango],
        gridcolor="#edf1f3", zeroline=False,
    ),
)
cfg = {"displayModeBar": False}
try:
    st.plotly_chart(fig, width="stretch", config=cfg)
except TypeError:   # versiones antiguas de Streamlit
    st.plotly_chart(fig, use_container_width=True, config=cfg)

with st.expander("Consultar las últimas 30 lecturas"):
    recientes = df.tail(30).copy()
    recientes["Fecha"] = recientes["Fecha"].dt.strftime("%Y-%m-%d")
    st.dataframe(recientes, hide_index=True, width="stretch")

with st.expander("Ver umbrales usados"):
    for k, (_, nombre) in estilos.items():
        v, o = umbrales["valores"][k], umbrales["origen"][k]
        st.write(f"**{nombre}:** {'—' if v is None else f'{v:.0f} cm'} ({o})")

# ═══════════════════════════ COMPARTIR / DESCARGAR ═══════════════════════════
st.divider()
b1, b2 = st.columns(2)
b1.download_button("Descargar histórico (CSV)", data=df.assign(Fecha=df["Fecha"].dt.strftime("%Y-%m-%d"))
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
    "Se muestra el nivel medio diario en centímetros. "
    "La serie hidrológica local se actualiza cada 6 horas, pero el IDEAM puede publicarla con retraso "
    "y corregirla después. Esta herramienta es informativa y **no reemplaza** los avisos "
    "oficiales del IDEAM, la UNGRD ni del Consejo Municipal de Gestión del Riesgo."
)
