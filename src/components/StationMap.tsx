import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

interface StationMapProps {
  lat: number;
  lon: number;
  label: string;
  altitud: number;
}

export function StationMap({ lat, lon, label, altitud }: StationMapProps) {
  const mapRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const el = mapRef.current;
    if (!el) return;

    const map = L.map(el, {
      center: [lat, lon],
      zoom: 14,
      scrollWheelZoom: false,
    });

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap contributors",
      maxZoom: 19,
    }).addTo(map);

    const marker = L.circleMarker([lat, lon], {
      radius: 10,
      color: "#0f5a6a",
      weight: 2,
      fillColor: "#167f94",
      fillOpacity: 0.9,
    }).addTo(map);

    marker.bindTooltip(`${label} · ${altitud} m s. n. m.`, {
      direction: "top",
      offset: [0, -8],
    });

    return () => {
      map.remove();
    };
  }, [lat, lon, label, altitud]);

  return (
    <div
      ref={mapRef}
      className="station-map"
      aria-label={`Mapa de ubicación de la estación ${label}`}
    />
  );
}
