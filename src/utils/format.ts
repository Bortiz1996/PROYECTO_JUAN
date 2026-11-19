export const MESES = [
  "ene",
  "feb",
  "mar",
  "abr",
  "may",
  "jun",
  "jul",
  "ago",
  "sep",
  "oct",
  "nov",
  "dic",
];

export type AmbienteTipo = "tormenta" | "lluvia" | "nublado" | "despejado";

export function parseIsoParts(iso: string): {
  year: number;
  month: number;
  day: number;
  hour: number;
  minute: number;
  hasTime: boolean;
} {
  const m = iso.match(
    /^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2}))?)?/
  );
  if (!m) {
    return { year: 1970, month: 1, day: 1, hour: 0, minute: 0, hasTime: false };
  }
  return {
    year: Number(m[1]),
    month: Number(m[2]),
    day: Number(m[3]),
    hour: m[4] !== undefined ? Number(m[4]) : 0,
    minute: m[5] !== undefined ? Number(m[5]) : 0,
    hasTime: m[4] !== undefined,
  };
}

export function fechaEs(iso: string, conHora = false): string {
  const p = parseIsoParts(iso);
  const base = `${p.day} ${MESES[p.month - 1]} ${p.year}`;
  if (!conHora) return base;
  const hh = String(p.hour).padStart(2, "0");
  const mm = String(p.minute).padStart(2, "0");
  return `${base}, ${hh}:${mm}`;
}

export function isoToUtcMs(iso: string): number {
  const p = parseIsoParts(iso);
  return Date.UTC(p.year, p.month - 1, p.day, p.hour, p.minute, 0);
}

export function formatNumberComma(val: number, decimals = 1): string {
  const fixed = val.toFixed(decimals);
  const [intPart, decPart] = fixed.split(".");
  const withCommas = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  return decPart !== undefined ? `${withCommas}.${decPart}` : withCommas;
}

export function formatIntegerDot(val: number): string {
  return Math.round(val)
    .toString()
    .replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

export function describirTiempo(codigo: number): string {
  if (codigo === 0) return "Despejado";
  if (codigo === 1) return "Mayormente despejado";
  if (codigo === 2) return "Parcialmente nublado";
  if (codigo === 3) return "Nublado";
  if (codigo === 45 || codigo === 48) return "Neblina";
  if ([51, 53, 55, 56, 57].includes(codigo)) return "Llovizna";
  if ([61, 63, 65, 66, 67].includes(codigo)) return "Lluvia";
  if ([71, 73, 75, 77, 85, 86].includes(codigo)) return "Precipitación sólida";
  if ([80, 81, 82].includes(codigo)) return "Chubascos";
  if ([95, 96, 99].includes(codigo)) return "Tormenta";
  return "Condición variable";
}

export function iconoTiempo(codigo: number | null, noche: boolean): string {
  if (codigo === null) return "🌡️";
  if ([95, 96, 99].includes(codigo)) return "⛈️";
  if ([51, 53, 55, 56, 57].includes(codigo)) return "🌦️";
  if ([61, 63, 65, 66, 67, 80, 81, 82].includes(codigo)) return "🌧️";
  if ([71, 73, 75, 77, 85, 86].includes(codigo)) return "🌨️";
  if ([45, 48].includes(codigo)) return "🌫️";
  if (codigo === 3) return "☁️";
  if (codigo === 2) return !noche ? "🌤️" : "☁️";
  if (codigo === 1) return !noche ? "🌤️" : "🌙";
  if (codigo === 0) return !noche ? "☀️" : "🌙";
  return "🌡️";
}

export function tipoAmbiente(codigo: number | null): AmbienteTipo {
  if (codigo !== null && [95, 96, 99].includes(codigo)) return "tormenta";
  if (
    codigo !== null &&
    [51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 71, 73, 75, 77, 80, 81, 82, 85, 86].includes(
      codigo
    )
  ) {
    return "lluvia";
  }
  if (codigo !== null && [2, 3, 45, 48].includes(codigo)) return "nublado";
  return "despejado";
}

export function isNightInBogota(weatherTimeIso?: string | null): boolean {
  let hour: number;
  if (weatherTimeIso) {
    hour = parseIsoParts(weatherTimeIso).hour;
  } else {
    const parts = new Intl.DateTimeFormat("en-CA", {
      timeZone: "America/Bogota",
      hour: "2-digit",
      hour12: false,
    }).formatToParts(new Date());
    hour = Number(parts.find((p) => p.type === "hour")?.value || 12) % 24;
  }
  return hour < 6 || hour >= 18;
}
