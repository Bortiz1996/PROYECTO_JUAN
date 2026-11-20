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
import L from "leaflet";

@Component({
  selector: "app-station-map",
  standalone: true,
  template: `
    <div
      #mapContainer
      class="station-map"
      [attr.aria-label]="'Mapa de ubicación de la estación ' + label"
    ></div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class StationMapComponent
  implements AfterViewInit, OnChanges, OnDestroy
{
  @Input({ required: true }) lat = 0;
  @Input({ required: true }) lon = 0;
  @Input({ required: true }) label = "";
  @Input({ required: true }) altitud = 0;

  @ViewChild("mapContainer", { static: true })
  private readonly mapRef!: ElementRef<HTMLDivElement>;

  private readonly ngZone = inject(NgZone);
  private map: L.Map | null = null;
  private viewReady = false;

  ngAfterViewInit(): void {
    this.viewReady = true;
    this.initMap();
  }

  ngOnChanges(): void {
    if (this.viewReady) {
      this.initMap();
    }
  }

  ngOnDestroy(): void {
    this.destroyMap();
  }

  private destroyMap(): void {
    if (this.map) {
      this.map.remove();
      this.map = null;
    }
  }

  private initMap(): void {
    const el = this.mapRef?.nativeElement;
    if (!el) return;

    this.destroyMap();

    this.ngZone.runOutsideAngular(() => {
      const map = L.map(el, {
        center: [this.lat, this.lon],
        zoom: 14,
        scrollWheelZoom: false,
      });

      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "&copy; OpenStreetMap contributors",
        maxZoom: 19,
      }).addTo(map);

      const marker = L.circleMarker([this.lat, this.lon], {
        radius: 10,
        color: "#0f5a6a",
        weight: 2,
        fillColor: "#167f94",
        fillOpacity: 0.9,
      }).addTo(map);

      marker.bindTooltip(`${this.label} · ${this.altitud} m s. n. m.`, {
        direction: "top",
        offset: [0, -8],
      });

      this.map = map;
    });
  }
}
