import {
  ChangeDetectionStrategy,
  Component,
  OnInit,
  computed,
  inject,
  signal,
} from "@angular/core";
import { PlotlyChartComponent } from "./components/plotly-chart/plotly-chart.component";
import { RiverGaugeComponent } from "./components/river-gauge/river-gauge.component";
import { StationMapComponent } from "./components/station-map/station-map.component";
import { DashboardService } from "./services/dashboard.service";
import type { DashboardResponse, RiverReading } from "../types";
import {
  describirTiempo,
  fechaEs,
  formatIntegerDot,
  formatNumberComma,
  iconoTiempo,
  isNightInBogota,
  isoToUtcMs,
  tipoAmbiente,
} from "../utils/format";

const PERIODOS_GRAFICA: Record<string, number | null> = {
  "Últimos 60 días": 60,
  "Último año": 365,
  "Últimos 5 años": 365 * 5,
  "Todo el histórico": null,
};

@Component({
  selector: "app-root",
  standalone: true,
  imports: [PlotlyChartComponent, RiverGaugeComponent, StationMapComponent],
  templateUrl: "./app.component.html",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AppComponent implements OnInit {
  private readonly dashboardService = inject(DashboardService);

  readonly Math = Math;
  readonly fechaEs = fechaEs;
  readonly formatIntegerDot = formatIntegerDot;
  readonly formatNumberComma = formatNumberComma;
  readonly describirTiempo = describirTiempo;
  readonly iconoTiempo = iconoTiempo;

  readonly periodoOpciones = Object.keys(PERIODOS_GRAFICA);

  readonly data = signal<DashboardResponse | null>(null);
  readonly loading = signal<boolean>(true);
  readonly refreshingFews = signal<boolean>(false);
  readonly error = signal<string | null>(null);
  readonly periodo = signal<string>("Últimos 60 días");

  readonly readings = computed<RiverReading[]>(() => {
    const d = this.data();
    if (!d) return [];
    return d.records.map((r) => ({
      fecha: r.f,
      fechaMs: isoToUtcMs(r.f),
      nivelCm: r.n,
      ultimaLectura: r.u,
      ultimaLecturaMs: r.u ? isoToUtcMs(r.u) : null,
      fuente: r.s === 1 ? "FEWS" : "Histórico IDEAM",
    }));
  });

  readonly fewsReadings = computed(() =>
    this.readings().filter((r) => r.fuente === "FEWS")
  );

  readonly fewsChart = computed(() => {
    const list = this.fewsReadings();
    if (list.length === 0) return null;
    const x = list.map((r) => r.fecha.replace("T", " "));
    const y = list.map((r) => r.nivelCm);
    const customdata = list.map((r) => r.fuente);
    return {
      data: [
        {
          type: "scatter",
          x,
          y,
          name: "Nivel observado FEWS (cm)",
          mode: list.length <= 2000 ? "lines+markers" : "lines",
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
  });

  readonly forecastChart = computed(() => {
    const forecast = this.data()?.forecast;
    if (!forecast || forecast.length === 0) return null;
    let cum = 0;
    const x = forecast.map((h) => h.fechaHora.replace("T", " "));
    const y = forecast.map((h) => {
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
  });

  readonly historicalFiltered = computed(() => {
    const d = this.data();
    const list = this.readings();
    if (!d || list.length === 0) return [];
    const dias = PERIODOS_GRAFICA[this.periodo()];
    if (dias === null) return list;
    const fechaUltMs = isoToUtcMs(d.meta.fechaUlt);
    const cutoff = fechaUltMs - dias * 86_400_000;
    return list.filter((r) => r.fechaMs >= cutoff);
  });

  readonly historicalChart = computed(() => {
    const d = this.data();
    const filtered = this.historicalFiltered();
    if (!d || filtered.length === 0) return null;
    const x = filtered.map((r) => r.fecha.replace("T", " "));
    const y = filtered.map((r) => r.nivelCm);
    const customdata = filtered.map((r) => [
      fechaEs(r.fecha, r.fuente.startsWith("FEWS")),
      r.fuente,
    ]);

    const yVals = [...y, d.config.nivelReferenciaCm];
    const shapes: Record<string, unknown>[] = [];
    const annotations: Record<string, unknown>[] = [];

    const estilos: Record<"amarilla" | "naranja" | "roja", [string, string]> = {
      amarilla: ["#d4a017", "Amarilla"],
      naranja: ["#e8710a", "Naranja"],
      roja: ["#c62828", "Roja"],
    };

    (["amarilla", "naranja", "roja"] as const).forEach((k) => {
      const val = d.thresholds.valores[k];
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
      y0: d.config.nivelReferenciaCm,
      y1: d.config.nivelReferenciaCm,
      line: { color: "#718a98", width: 1, dash: "dash" },
    });
    annotations.push({
      xref: "paper",
      x: 0.01,
      xanchor: "left",
      yref: "y",
      y: d.config.nivelReferenciaCm,
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
      (filtered[filtered.length - 1].fechaMs - filtered[0].fechaMs) /
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
  });

  readonly latest30 = computed(() => {
    const list = this.readings();
    if (list.length === 0) return [];
    return [...list]
      .sort(
        (a, b) =>
          (b.ultimaLecturaMs ?? b.fechaMs) - (a.ultimaLecturaMs ?? a.fechaMs)
      )
      .slice(0, 30);
  });

  readonly codigoClima = computed(() => {
    const w = this.data()?.weather;
    return w ? Math.round(w.weather_code) : null;
  });

  readonly noche = computed(() =>
    isNightInBogota(this.data()?.weather?.time)
  );

  readonly ambiente = computed(() => tipoAmbiente(this.codigoClima()));

  readonly climaTexto = computed(() => {
    const code = this.codigoClima();
    return code !== null ? describirTiempo(code) : "clima no disponible";
  });

  readonly vientoKmh = computed(() => {
    const w = this.data()?.weather;
    return w ? w.wind_speed_10m : 0.0;
  });

  readonly openStreetMapUrl = computed(() => {
    const cfg = this.data()?.config;
    if (!cfg) return "https://www.openstreetmap.org/";
    return `https://www.openstreetmap.org/?mlat=${cfg.estacionLatitud}&mlon=${cfg.estacionLongitud}#map=15/${cfg.estacionLatitud}/${cfg.estacionLongitud}`;
  });

  readonly whatsappHref = computed(() => {
    const d = this.data();
    if (!d) return "";
    const msg = `Nivel del río Magdalena en Calamar: ${d.meta.nivelCm.toFixed(
      0
    )} cm (${(d.meta.nivelCm / 100).toFixed(2)} m). Consulte aquí: ${
      d.config.appUrl
    }`;
    return `https://wa.me/?text=${encodeURIComponent(msg)}`;
  });

  readonly thresholdRows = computed(() => {
    const d = this.data();
    if (!d) return [];
    return (
      [
        ["amarilla", "Amarilla"],
        ["naranja", "Naranja"],
        ["roja", "Roja"],
      ] as const
    ).map(([key, nombre]) => ({
      key,
      nombre,
      valor: d.thresholds.valores[key],
      origen: d.thresholds.origen[key],
    }));
  });

  ngOnInit(): void {
    void this.fetchDashboard(false);
  }

  async fetchDashboard(refreshFews = false): Promise<void> {
    if (refreshFews) {
      this.refreshingFews.set(true);
    } else {
      this.loading.set(true);
    }
    try {
      const payload = await this.dashboardService.getDashboard(refreshFews);
      this.data.set(payload);
      this.error.set(null);
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : (err as { error?: { error?: string } })?.error?.error ||
            "No se pudo cargar la información del tablero.";
      this.error.set(message);
    } finally {
      this.loading.set(false);
      this.refreshingFews.set(false);
    }
  }

  onPeriodoChange(event: Event): void {
    const target = event.target as HTMLSelectElement | null;
    if (target) {
      this.periodo.set(target.value);
    }
  }
}
