import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  Input,
  NgZone,
  OnChanges,
  OnDestroy,
  ViewChild,
  inject,
} from "@angular/core";
import Plotly from "plotly.js-basic-dist-min";

@Component({
  selector: "app-plotly-chart",
  standalone: true,
  template: `<div #chartContainer class="plotly-chart-box"></div>`,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PlotlyChartComponent
  implements AfterViewInit, OnChanges, OnDestroy
{
  @Input({ required: true }) data: Record<string, unknown>[] = [];
  @Input({ required: true }) layout: Record<string, unknown> = {};

  @ViewChild("chartContainer", { static: true })
  private readonly containerRef!: ElementRef<HTMLDivElement>;

  private readonly ngZone = inject(NgZone);
  private resizeObserver: ResizeObserver | null = null;
  private viewReady = false;

  ngAfterViewInit(): void {
    this.viewReady = true;
    this.renderChart();

    if (typeof ResizeObserver !== "undefined") {
      this.ngZone.runOutsideAngular(() => {
        this.resizeObserver = new ResizeObserver(() => {
          const el = this.containerRef?.nativeElement;
          if (el) {
            Plotly.Plots.resize(el);
          }
        });
        this.resizeObserver.observe(this.containerRef.nativeElement);
      });
    }
  }

  ngOnChanges(): void {
    if (this.viewReady) {
      this.renderChart();
    }
  }

  ngOnDestroy(): void {
    if (this.resizeObserver) {
      this.resizeObserver.disconnect();
      this.resizeObserver = null;
    }
    const el = this.containerRef?.nativeElement;
    if (el) {
      Plotly.purge(el);
    }
  }

  private renderChart(): void {
    const el = this.containerRef?.nativeElement;
    if (!el) return;

    const mergedLayout: Record<string, unknown> = {
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "#ffffff",
      font: { family: "Arial, sans-serif", color: "#455d6b", size: 12 },
      showlegend: true,
      legend: {
        orientation: "h",
        x: 1,
        y: 1.02,
        xanchor: "right",
        yanchor: "bottom",
        font: { size: 11, color: "#455d6b" },
        bgcolor: "rgba(255,255,255,0.75)",
      },
      ...this.layout,
      xaxis: {
        gridcolor: "#e6ebee",
        gridwidth: 0.6,
        zeroline: false,
        showline: true,
        linecolor: "#aebbc2",
        linewidth: 0.8,
        ticks: "outside",
        tickcolor: "#aebbc2",
        tickwidth: 0.8,
        ticklen: 3,
        showticklabels: true,
        tickfont: { size: 11, color: "#455d6b" },
        automargin: true,
        ...((this.layout["xaxis"] as Record<string, unknown>) || {}),
      },
      yaxis: {
        gridcolor: "#e6ebee",
        gridwidth: 0.6,
        zeroline: false,
        showline: true,
        linecolor: "#aebbc2",
        linewidth: 0.8,
        ticks: "outside",
        tickcolor: "#aebbc2",
        tickwidth: 0.8,
        ticklen: 3,
        showticklabels: true,
        tickfont: { size: 11, color: "#455d6b" },
        automargin: true,
        ...((this.layout["yaxis"] as Record<string, unknown>) || {}),
      },
    };

    this.ngZone.runOutsideAngular(() => {
      void Plotly.react(el, this.data, mergedLayout, {
        displayModeBar: false,
        responsive: true,
      });
    });
  }
}
