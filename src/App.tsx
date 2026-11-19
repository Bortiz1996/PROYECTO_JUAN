import { useCallback, useEffect, useMemo, useState } from "react";
import { PlotlyChart } from "./components/PlotlyChart.tsx";
import { RiverGauge } from "./components/RiverGauge.tsx";
import { StationMap } from "./components/StationMap.tsx";
import type { DashboardResponse, RiverReading } from "./types.ts";
import {
  describirTiempo,
  fechaEs,
  formatIntegerDot,
  formatNumberComma,
  iconoTiempo,
  isNightInBogota,
  isoToUtcMs,
  tipoAmbiente,
} from "./utils/format.ts";

const PERIODOS_GRAFICA: Record<string, number | null> = {
  "Últimos 60 días": 60,
  "Último año": 365,
  "Últimos 5 años": 365 * 5,
  "Todo el histórico": null,
};

function ProfileHeader({
  estacionNombre,
  estacionCodigo,
}: {
  estacionNombre: string;
  estacionCodigo: string;
}) {
  return (
    <section className="profile-card" aria-label="Perfil del proyecto JUAN">
      <div
        className="profile-cover"
        style={{ "--cover-image": "url('/assets/juan_portada.webp')" } as React.CSSProperties}
      />
      <img
        className="profile-avatar"
        src="/assets/juan_icon.png"
        alt="Imagen de JUAN"
      />
      <div className="profile-content">
        <h1>JUAN</h1>
        <h2>
          OBSERVATORIO MONITOREO DEL NIVEL DE RIO MAGDALENA EN CALAMAR BOLIVAR
        </h2>
        <p>
          {estacionNombre} · Estación IDEAM {estacionCodigo} · Nivel observado
        </p>
      </div>
    </section>
  );
}

function StatusBanner({ state }: { state: DashboardResponse["alertState"] }) {
  if (state === "verde") {
    return (
      <div className="alert-box alert-success">
        Dentro de las cotas oficiales configuradas. Manténgase atento a los
        avisos de las autoridades.
      </div>
    );
  }
  if (state === "amarilla") {
    return (
      <div className="alert-box alert-warning">
        Umbral amarillo oficial alcanzado. Consulte los avisos del Consejo
        Municipal de Gestión del Riesgo.
      </div>
    );
  }
  if (state === "naranja") {
    return (
      <div className="alert-box alert-warning">
        Umbral naranja oficial alcanzado. Siga las instrucciones de las
        autoridades locales.
      </div>
    );
  }
  if (state === "roja") {
    return (
      <div className="alert-box alert-error">
        Umbral rojo oficial alcanzado. Atienda de inmediato las instrucciones de
        evacuación y autoridades.
      </div>
    );
  }
  return (
    <div className="status-note">
      <strong>Sin cotas oficiales configuradas.</strong> El medidor muestra la
      lectura observada; no representa por sí solo un nivel de riesgo.
    </div>
  );
}

export function App() {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshingFews, setRefreshingFews] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [periodo, setPeriodo] = useState<string>("Últimos 60 días");

  const fetchDashboard = useCallback(async (refreshFews = false) => {
    if (refreshFews) setRefreshingFews(true);
    else setLoading(true);
    try {
      const res = await fetch(
        refreshFews ? "/api/dashboard?refreshFews=1" : "/api/dashboard"
      );
      const body = await res.json();
      if (!res.ok) {
        throw new Error(body?.error || `Error HTTP ${res.status}`);
      }
      setData(body as DashboardResponse);
      setError(null);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "No se pudo cargar la información del tablero."
      );
    } finally {
      setLoading(false);
      setRefreshingFews(false);
    }
  }, []);

  useEffect(() => {
    void fetchDashboard(false);
  }, [fetchDashboard]);

  const readings = useMemo<RiverReading[]>(() => {
    if (!data) return [];
    return data.records.map((r) => ({
      fecha: r.f,
      fechaMs: isoToUtcMs(r.f),
      nivelCm: r.n,
      ultimaLectura: r.u,
      ultimaLecturaMs: r.u ? isoToUtcMs(r.u) : null,
      fuente: r.s === 1 ? "FEWS" : "Histórico IDEAM",
    }));
  }, [data]);

  const fewsReadings = useMemo(
    () => readings.filter((r) => r.fuente === "FEWS"),
    [readings]
  );

  const fewsChart = useMemo(() => {
    if (fewsReadings.length === 0) return null;
    const x = fewsReadings.map((r) => r.fecha.replace("T", " "));
    const y = fewsReadings.map((r) => r.nivelCm);
    const customdata = fewsReadings.map((r) => r.fuente);
    return {
      data: [
        {
          type: "scatter",
          x,
          y,
          name: "Nivel observado FEWS (cm)",
          mode: fewsReadings.length <= 2000 ? "lines+markers" : "lines",
          line: { color: "#167f94", width: 1.2 },
          marker: { size: 3, color: "#167f94" },
          customdata,
          hovertemplate:
            "<b>%{x|%d %b %Y %H:%M}</b><br>Nivel: <b>%{y:.1f} cm</b>" +
            "<br>%{customdata}<extra></extra>",
        },
      ],
      layout: {
        height: 360,
        margin: { l: 60, r: 20, t: 48, b: 40 },
        hovermode: "x",
        yaxis: { title: "Nivel observado (cm)" },
      },
    };
  }, [fewsReadings]);

  const forecastChart = useMemo(() => {
    if (!data?.forecast || data.forecast.length === 0) return null;
    let cum = 0;
    const x = data.forecast.map((h) => h.fechaHora.replace("T", " "));
    const y = data.forecast.map((h) => {
      cum += h.precipitacionMm;
      return cum;
    });
    return {
      totalMm: cum,
      data: [
        {
          type: "scatter",
          x,
          y,
          name: "Lluvia acumulada (mm)",
          mode: "lines+markers",
          line: { color: "#167f94", width: 1.2 },
          marker: { size: 3 },
          fill: "tozeroy",
          fillcolor: "rgba(22, 127, 148, 0.07)",
          hovertemplate: "%{y:.1f} mm<extra></extra>",
        },
      ],
      layout: {
        height: 300,
        margin: { l: 64, r: 20, t: 48, b: 40 },
        hovermode: "x unified",
        xaxis: { title: "Hora local", tickformat: "%H:%M", fixedrange: true },
        yaxis: {
          title: "Precipitación media acumulada (mm)",
          rangemode: "tozero",
          fixedrange: true,
        },
      },
    };
  }, [data?.forecast]);

  const historicalFiltered = useMemo(() => {
    if (!data || readings.length === 0) return [];
    const dias = PERIODOS_GRAFICA[periodo];
    if (dias === null) return readings;
    const fechaUltMs = isoToUtcMs(data.meta.fechaUlt);
    const cutoff = fechaUltMs - dias * 86_400_000;
    return readings.filter((r) => r.fechaMs >= cutoff);
  }, [data, readings, periodo]);

  const historicalChart = useMemo(() => {
    if (!data || historicalFiltered.length === 0) return null;
    const x = historicalFiltered.map((r) => r.fecha.replace("T", " "));
    const y = historicalFiltered.map((r) => r.nivelCm);
    const customdata = historicalFiltered.map((r) => [
      fechaEs(r.fecha, r.fuente.startsWith("FEWS")),
      r.fuente,
    ]);

    const yVals = [...y, data.config.nivelReferenciaCm];
    const shapes: Record<string, unknown>[] = [];
    const annotations: Record<string, unknown>[] = [];

    const estilos: Record<"amarilla" | "naranja" | "roja", [string, string]> = {
      amarilla: ["#d4a017", "Amarilla"],
      naranja: ["#e8710a", "Naranja"],
      roja: ["#c62828", "Roja"],
    };

    (["amarilla", "naranja", "roja"] as const).forEach((k) => {
      const val = data.thresholds.valores[k];
      if (val === null) return;
      const [color, nombre] = estilos[k];
      yVals.push(val);
      shapes.push({
        type: "line",
        xref: "paper",
        x0: 0,
        x1: 1,
        yref: "y",
        y0: val,
        y1: val,
        line: { color, width: 1, dash: "dot" },
      });
      annotations.push({
        xref: "paper",
        x: 0.01,
        xanchor: "left",
        yref: "y",
        y: val,
        yanchor: "bottom",
        text: `${nombre} ${val.toFixed(0)} cm`,
        showarrow: false,
        font: { color, size: 11 },
      });
    });

    shapes.push({
      type: "line",
      xref: "paper",
      x0: 0,
      x1: 1,
      yref: "y",
      y0: data.config.nivelReferenciaCm,
      y1: data.config.nivelReferenciaCm,
      line: { color: "#718a98", width: 1, dash: "dash" },
    });
    annotations.push({
      xref: "paper",
      x: 0.01,
      xanchor: "left",
      yref: "y",
      y: data.config.nivelReferenciaCm,
      yanchor: "bottom",
      text: "Referencia · 950 cm",
      showarrow: false,
      font: { color: "#526b79", size: 11 },
    });

    let minY = yVals[0];
    let maxY = yVals[0];
    for (const v of yVals) {
      if (v < minY) minY = v;
      if (v > maxY) maxY = v;
    }
    const rango = Math.max(maxY - minY, 1);
    const spanDays =
      (historicalFiltered[historicalFiltered.length - 1].fechaMs -
        historicalFiltered[0].fechaMs) /
      86_400_000;

    return {
      data: [
        {
          type: "scatter",
          x,
          y,
          name: "Nivel observado (cm)",
          mode: "lines",
          line: { color: "#167f94", width: 1.2 },
          customdata,
          hovertemplate:
            "<b>%{customdata[0]}</b><br>Nivel: <b>%{y:.1f} cm</b>" +
            "<br>Fuente: %{customdata[1]}<extra></extra>",
        },
      ],
      layout: {
        height: 390,
        margin: { l: 60, r: 20, t: 48, b: 40 },
        hovermode: "x",
        dragmode: false,
        hoverlabel: { font: { size: 16 } },
        shapes,
        annotations,
        xaxis: {
          fixedrange: true,
          tickformat: spanDays > 365 * 3 ? "%Y" : "%d %b",
        },
        yaxis: {
          fixedrange: true,
          title: "Nivel (cm)",
          range: [minY - 0.08 * rango, maxY + 0.12 * rango],
        },
      },
    };
  }, [data, historicalFiltered]);

  const latest30 = useMemo(() => {
    if (readings.length === 0) return [];
    return [...readings]
      .sort(
        (a, b) =>
          (b.ultimaLecturaMs ?? b.fechaMs) - (a.ultimaLecturaMs ?? a.fechaMs)
      )
      .slice(0, 30);
  }, [readings]);

  if (loading && !data) {
    return (
      <div className="app-shell">
        <main className="block-container">
          <ProfileHeader
            estacionNombre="Calamar, Bolívar"
            estacionCodigo="29037020"
          />
          <div className="loading-state">
            Consultando la serie de nivel de FEWS IDEAM y condiciones
            meteorológicas...
          </div>
        </main>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="app-shell">
        <main className="block-container">
          <ProfileHeader
            estacionNombre="Calamar, Bolívar"
            estacionCodigo="29037020"
          />
          <div className="alert-box alert-error">{error}</div>
        </main>
      </div>
    );
  }

  if (!data) return null;

  const {
    meta,
    thresholds,
    alertState,
    trend,
    weather,
    weatherError,
    forecastError,
    subzonesCount,
    totalAreaKm2,
    config,
  } = data;

  const codigoClima = weather ? Math.round(weather.weather_code) : null;
  const noche = isNightInBogota(weather?.time);
  const ambiente = tipoAmbiente(codigoClima);
  const climaTexto =
    codigoClima !== null
      ? describirTiempo(codigoClima)
      : "clima no disponible";
  const vientoKmh = weather ? weather.wind_speed_10m : 0.0;

  const whatsappMsg = `Nivel del río Magdalena en Calamar: ${meta.nivelCm.toFixed(
    0
  )} cm (${(meta.nivelCm / 100).toFixed(2)} m). Consulte aquí: ${config.appUrl}`;

  return (
    <div className="app-shell">
      <main className="block-container">
        <ProfileHeader
          estacionNombre={config.estacionNombre}
          estacionCodigo={config.estacionCodigo}
        />

        {/* Sección medidor y lectura */}
        <section className="main-grid">
          <div>
            <RiverGauge
              nivelCm={meta.nivelCm}
              umbrales={thresholds}
              estadoPeces={meta.estadoPeces}
              estadoPecesTexto={meta.estadoPecesTexto}
              ambiente={ambiente}
              climaTexto={climaTexto}
              noche={noche}
              vientoKmh={vientoKmh}
              estacionCodigo={config.estacionCodigo}
              nivelReferenciaCm={config.nivelReferenciaCm}
              nivelMurallaCm={config.nivelMurallaCm}
            />

            <div
              className="weather-card"
              role="status"
              aria-label="Clima actual en Calamar"
            >
              <div className="weather-icon" aria-hidden="true">
                {weather ? iconoTiempo(codigoClima, noche) : "🌡️"}
              </div>
              <div className="weather-body">
                <div className="weather-label">Clima en Calamar ahora</div>
                <div className="weather-desc">
                  {weather ? climaTexto : "Clima no disponible"}
                </div>
                <div className="weather-meta">
                  {weather
                    ? `${weather.temperature_2m.toFixed(
                        1
                      )} °C · humedad ${Math.round(
                        weather.relative_humidity_2m
                      )}% · viento ${weather.wind_speed_10m.toFixed(0)} km/h`
                    : "Sin conexión al servicio meteorológico"}
                </div>
              </div>
            </div>
          </div>

          <div>
            <div className="reading-card">
              <div className="eyebrow">LECTURA MÁS RECIENTE</div>
              <div className="reading-value">
                {formatNumberComma(meta.nivelCm, 1)}
                <span> cm</span>
              </div>
              <div className="reading-conversion">
                {(meta.nivelCm / 100).toFixed(2)} m
              </div>
              <div className="reading-divider" />
              <div className="reading-detail">
                <strong>Fecha de lectura</strong>
                <br />
                {fechaEs(meta.tsUlt, meta.tsUltHasTime)}
                <br />
                <strong>Variación</strong>
                <br />
                {meta.cambioTexto}
                <br />
                <strong>Fuente</strong>
                <br />
                {meta.fuente}
              </div>
            </div>

            <StatusBanner state={alertState} />
          </div>
        </section>

        {meta.edadDias > config.diasMaxSinDatos && (
          <div className="alert-box alert-warning">
            El último dato publicado por el IDEAM tiene {meta.edadDias} días;
            puede no representar el nivel actual del río.
          </div>
        )}

        {/* Sección visor FEWS */}
        <section>
          <h3 className="section-title">Visor FEWS IDEAM · Calamar</h3>
          <p className="caption">
            Ubicación de la estación y serie consolidada de nivel observado
            publicada por FEWS IDEAM. Las lecturas de FEWS son preliminares,
            pueden ser corregidas y no son una medición en tiempo real.
          </p>

          <div className="two-col-grid">
            <div>
              <button
                type="button"
                className="btn-action"
                disabled={refreshingFews}
                onClick={() => void fetchDashboard(true)}
              >
                {refreshingFews ? "Actualizando..." : "Actualizar ahora"}
              </button>
            </div>
            <div>
              <a
                className="btn-link btn-stretch"
                href={config.fewsVisorUrl}
                target="_blank"
                rel="noopener noreferrer"
              >
                Abrir visor FEWS nacional
              </a>
            </div>
          </div>

          {data.fewsError && (
            <p className="caption">
              No se pudo consultar FEWS; mostrando el último dato guardado.
            </p>
          )}

          <p className="caption">
            Estación {config.estacionNombre} · Código IDEAM{" "}
            {config.estacionCodigo} · {config.estacionLatitud.toFixed(6)},{" "}
            {config.estacionLongitud.toFixed(6)} ·{" "}
            {config.estacionAltitudMsnm} m s. n. m.
          </p>

          <StationMap
            lat={config.estacionLatitud}
            lon={config.estacionLongitud}
            label={`CALAMAR [${config.estacionCodigo}]`}
            altitud={config.estacionAltitudMsnm}
          />

          <p>
            <a
              href={`https://www.openstreetmap.org/?mlat=${config.estacionLatitud}&mlon=${config.estacionLongitud}#map=15/${config.estacionLatitud}/${config.estacionLongitud}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              Abrir ubicación en OpenStreetMap
            </a>{" "}
            ·{" "}
            <a
              href="https://dhime.ideam.gov.co/server/rest/services/CNE/Estaciones/MapServer/0"
              target="_blank"
              rel="noopener noreferrer"
            >
              Catálogo Nacional de Estaciones del IDEAM
            </a>
          </p>

          {fewsChart && data.fewsRange && (
            <>
              <p className="caption">
                {formatNumberComma(data.fewsCount, 0)} registros FEWS ·{" "}
                {data.fewsRange.start} – {data.fewsRange.end}
              </p>
              <PlotlyChart data={fewsChart.data} layout={fewsChart.layout} />
              <p className="caption">
                Fuente:{" "}
                <a
                  href={config.fewsVisorUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  FEWS IDEAM
                </a>
                . La consulta se conserva en caché durante 5 minutos.
              </p>
            </>
          )}
        </section>

        {/* Sección lluvia y tendencia */}
        <section>
          <h3 className="section-title">
            Lluvia prevista y tendencia observada del río
          </h3>
          <p className="caption">
            La lluvia se calcula para toda el área hidrográfica
            Magdalena-Cauca: promedio espacial ponderado por el área de sus 105
            subzonas IDEAM, acumulado para las próximas 24 horas.
          </p>

          {forecastError || weatherError || !weather || !forecastChart ? (
            <>
              <div className="alert-box alert-error">
                No se pudo actualizar el pronóstico meteorológico local o de la
                cuenca: {forecastError || weatherError}
              </div>
              <p className="caption">
                La lluvia prevista no está disponible. La dirección observada
                del río se calcula independientemente, a partir de las lecturas
                recientes.
              </p>
              <div className="metric-card" style={{ maxWidth: 360 }}>
                <div className="metric-label">
                  Dirección observada · 3 días
                </div>
                <div className="metric-value">{trend.direccion}</div>
              </div>
              <p className="caption">{trend.motivo}</p>
            </>
          ) : (
            <>
              <div className="three-col-grid">
                <div>
                  <div className="metric-card">
                    <div className="metric-label">Condición en Calamar</div>
                    <div className="metric-value">
                      {describirTiempo(Math.round(weather.weather_code))}
                    </div>
                  </div>
                  <p className="caption">
                    {weather.temperature_2m.toFixed(1)} °C · humedad{" "}
                    {Math.round(weather.relative_humidity_2m)}% · viento{" "}
                    {weather.wind_speed_10m.toFixed(0)} km/h
                  </p>
                </div>

                <div>
                  <div className="metric-card">
                    <div className="metric-label">
                      Lluvia media acumulada · cuenca · 24 h
                    </div>
                    <div className="metric-value">
                      {forecastChart.totalMm.toFixed(1)} mm
                    </div>
                  </div>
                </div>

                <div>
                  <div className="metric-card">
                    <div className="metric-label">
                      Dirección observada · 3 días
                    </div>
                    <div className="metric-value">{trend.direccion}</div>
                  </div>
                </div>
              </div>

              <p className="caption">
                Área representada: {formatIntegerDot(totalAreaKm2)} km² en{" "}
                {subzonesCount} subzonas. Los milímetros son una media areal
                ponderada; no se suman entre ubicaciones.
              </p>
              <p className="caption">
                Actualización del modelo: {fechaEs(weather.time, true)} · zona
                horaria de Colombia.
              </p>

              <div className="forecast-note">
                <div className="eyebrow">LECTURA DE LOS DATOS OBSERVADOS</div>
                <p>{trend.motivo}</p>
                <p className="forecast-caveat">
                  La dirección resume la serie reciente de Calamar; no
                  pronostica el nivel de las próximas 24 horas. La lluvia se
                  estima para toda la cuenca Magdalena-Cauca y no permite
                  inferir por sí sola el cambio del río en esta estación: no se
                  modelan el aporte local, la escorrentía, los caudales, los
                  tiempos de tránsito ni la operación de embalses.
                </p>
              </div>

              <PlotlyChart
                data={forecastChart.data}
                layout={forecastChart.layout}
              />

              <p>
                <a
                  href="https://open-meteo.com/"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Pronóstico: Open-Meteo
                </a>{" "}
                · CC BY 4.0 ·{" "}
                <a
                  href="https://dhime.ideam.gov.co/server/rest/services/Cartografia_Tematica/ZonificacionHidrografica/MapServer/0"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  zonificación hidrográfica 2025 del IDEAM
                </a>
                .
              </p>
            </>
          )}
        </section>

        {/* Sección histórico */}
        <section>
          <div className="history-header-grid">
            <h3 className="section-title">Histórico de niveles</h3>
            <div className="select-group">
              <label htmlFor="periodo-select">Período</label>
              <select
                id="periodo-select"
                value={periodo}
                onChange={(e) => setPeriodo(e.target.value)}
              >
                {Object.keys(PERIODOS_GRAFICA).map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {historicalFiltered.length > 0 && historicalChart && (
            <>
              <p className="caption">
                {formatNumberComma(historicalFiltered.length, 0)} registros ·{" "}
                {fechaEs(historicalFiltered[0].fecha)} –{" "}
                {fechaEs(
                  historicalFiltered[historicalFiltered.length - 1].fecha
                )}
              </p>
              <PlotlyChart
                data={historicalChart.data}
                layout={historicalChart.layout}
              />
            </>
          )}

          <details className="expander">
            <summary>Consultar las últimas 30 lecturas</summary>
            <div className="expander-body">
              <div className="table-scroll">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Fecha y hora</th>
                      <th>Nivel (cm)</th>
                      <th>Fuente</th>
                    </tr>
                  </thead>
                  <tbody>
                    {latest30.map((r) => (
                      <tr key={`${r.fecha}-${r.fuente}`}>
                        <td>
                          {fechaEs(r.ultimaLectura ?? r.fecha, true)}
                        </td>
                        <td>{r.nivelCm.toFixed(1)}</td>
                        <td>{r.fuente}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="caption" style={{ marginTop: "0.6rem" }}>
                Hora de última lectura: {fechaEs(meta.fechaUlt, true)}
              </p>
            </div>
          </details>

          <details className="expander">
            <summary>Ver umbrales usados</summary>
            <div className="expander-body" style={{ paddingTop: "0.75rem" }}>
              {(
                [
                  ["amarilla", "Amarilla"],
                  ["naranja", "Naranja"],
                  ["roja", "Roja"],
                ] as const
              ).map(([k, nombre]) => {
                const v = thresholds.valores[k];
                const o = thresholds.origen[k];
                return (
                  <p key={k} style={{ marginBottom: "0.35rem" }}>
                    <strong>{nombre}:</strong>{" "}
                    {v === null ? "—" : `${v.toFixed(0)} cm`} ({o})
                  </p>
                );
              })}
            </div>
          </details>
        </section>

        {/* Compartir y descargar */}
        <hr className="section-divider" />
        <section className="two-col-grid">
          <div>
            <a
              className="btn-link"
              href="/api/download.csv"
              download="nivel_calamar.csv"
            >
              Descargar histórico (CSV)
            </a>
          </div>
          <div>
            {config.appUrl ? (
              <a
                className="btn-link"
                href={`https://wa.me/?text=${encodeURIComponent(whatsappMsg)}`}
                target="_blank"
                rel="noopener noreferrer"
              >
                Compartir por WhatsApp
              </a>
            ) : (
              <p className="caption">
                Para compartir: copie el enlace de esta página y envíelo por
                WhatsApp.
              </p>
            )}
          </div>
        </section>

        {/* Pie */}
        <hr className="section-divider" />
        <footer>
          <p className="caption">
            <strong>Fuente:</strong> IDEAM, Hidrología Nacional Diaria y
            exportaciones DHIME; estación limnimétrica {config.estacionCodigo} –
            Calamar, Bolívar. El histórico local muestra nivel medio diario y las
            últimas observaciones FEWS pueden ser intradiarias. El histórico
            local se intenta actualizar tres veces al día y la consulta FEWS se
            conserva en caché durante 5 minutos; las lecturas FEWS son
            preliminares y el IDEAM puede publicarlas con retraso o corregirlas
            después. Esta herramienta es informativa y{" "}
            <strong>no reemplaza</strong> los avisos oficiales del IDEAM, la
            UNGRD ni del Consejo Municipal de Gestión del Riesgo.
          </p>
        </footer>
      </main>
    </div>
  );
}

export default App;
