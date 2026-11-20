import type { ThresholdsInfo } from "../types";
import type { AmbienteTipo } from "./format";

export interface FishProfile {
  especie:
    | "bocachico"
    | "bagre"
    | "mojarra"
    | "sabalo"
    | "doncella"
    | "pacora"
    | "capaz";
  largo: number;
  alto: number;
  profundidad: number;
  velocidad: number;
  fase: number;
  rayas: number[];
  x: number;
}

function createPrng(seed: number) {
  let a = seed >>> 0;
  return {
    random(): number {
      a |= 0;
      a = (a + 0x6d2b79f5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    },
    uniform(min: number, max: number): number {
      return min + this.random() * (max - min);
    },
    choice<T>(arr: readonly T[]): T {
      return arr[Math.floor(this.random() * arr.length)];
    },
  };
}

function personaSvg(
  camisa: string,
  pantalon: string,
  piel = "#c68a63",
  camina = false,
  sentada = false
): string {
  const cabeza =
    `<circle cx="0" cy="-19" r="3.1" fill="${piel}"/>` +
    '<path d="M-3.2 -20.4Q0 -24.2 3.2 -20.4Z" fill="#2b2622"/>';
  const torso = `<rect x="-3.4" y="-16" width="6.8" height="9.6" rx="2.2" fill="${camisa}"/>`;
  if (sentada) return cabeza + torso;
  const clase = camina ? ' class="jn-pierna"' : "";
  const piernas =
    `<rect${clase} x="-3" y="-7" width="2.8" height="7" rx="1" fill="${pantalon}"/>` +
    `<rect${clase} x=".2" y="-7" width="2.8" height="7" rx="1" fill="${pantalon}"/>`;
  return cabeza + torso + piernas;
}

function ventanaSvg(
  x: number,
  y: number,
  ancho = 12,
  alto = 22,
  arco = false,
  marco = "#2e5b78",
  vidrio = "#4a86a8"
): string {
  if (arco) {
    const radio = ancho / 2;
    return (
      `<path d="M${x} ${y + alto}V${y + radio}a${radio} ${radio} 0 0 1 ${ancho} 0V${y + alto}Z" ` +
      `fill="${vidrio}" stroke="${marco}" stroke-width="1.3"/>`
    );
  }
  return (
    `<rect x="${x}" y="${y}" width="${ancho}" height="${alto}" fill="${vidrio}" ` +
    `stroke="${marco}" stroke-width="1.3"/>` +
    `<path d="M${x + ancho / 2} ${y}v${alto}M${x} ${y + alto / 2}h${ancho}" ` +
    `stroke="${marco}" stroke-width=".7"/>`
  );
}

function boteSvg(
  x: number,
  yAgua: number,
  tipo: "a" | "b" | "c",
  retraso: number,
  duracion: number
): string {
  const motor = (mx: number, mw: number, px: number) =>
    `<path d="M${mx} -1H${mw}V8H${mx}Z" fill="#23272b"/><path d="M${px} 8V15" stroke="#23272b" stroke-width="2"/>`;
  let interior: string;
  if (tipo === "a") {
    interior =
      '<path d="M0 0H44L40 11Q22 14.5 5 11Z" fill="#2f6f9a"/>' +
      '<path d="M0 0H44" stroke="#eef3f5" stroke-width="1.8"/>' +
      motor(44, 49, 46.5);
  } else if (tipo === "b") {
    interior =
      `<g transform="translate(18 7)">${personaSvg("#f1f1ec", "#555", "#c68a63", false, true)}</g>` +
      `<g transform="translate(32 7)">${personaSvg("#e3a23a", "#555", "#a8714d", false, true)}</g>` +
      '<path d="M0 0H62L57 11Q30 15 6 11Z" fill="#3f8f6b"/>' +
      '<path d="M0 0H62" stroke="#e9f2ec" stroke-width="1.8"/>' +
      motor(62, 67, 64.5);
  } else {
    interior =
      '<path d="M8 0L16 -15L68 -17L78 0Z" fill="#f5f3ec"/>' +
      '<path d="M24 -15.5L21 0M40 -16L39 0M56 -16.5L57 0" stroke="#d3d0c4" stroke-width=".9"/>' +
      '<path d="M8 0L16 -15M78 0L68 -17" stroke="#6b4b2f" stroke-width="1.4"/>' +
      '<path d="M0 0H84L78 11Q42 15 7 11Z" fill="#c65a4b"/>' +
      '<path d="M0 0H84" stroke="#f3dfd8" stroke-width="1.8"/>' +
      motor(84, 90, 87);
  }
  return (
    `<g transform="translate(${x} ${(yAgua - 5).toFixed(1)})">` +
    `<g class="jn-bote" style="--dur:${duracion}s;--delay:${retraso}s">${interior}</g></g>`
  );
}

function olaPath(
  amplitud: number,
  periodo: number,
  ciclos: number,
  espesor = 16
): string {
  const mitad = periodo / 2;
  let d = `M0 0Q${(mitad / 2).toFixed(2)} ${(-amplitud).toFixed(2)} ${mitad.toFixed(2)} 0`;
  for (let i = 0; i < ciclos * 2 - 1; i++) {
    d += `T${(mitad * (i + 2)).toFixed(2)} 0`;
  }
  return `${d}V${espesor}H0Z`;
}

const escenaFijaCache = new Map<string, string>();

function escenaFijaSvg(
  ambiente: AmbienteTipo,
  noche: boolean,
  estacionCodigo: string
): string {
  const cacheKey = `${ambiente}|${noche}|${estacionCodigo}`;
  const cached = escenaFijaCache.get(cacheKey);
  if (cached) return cached;

  const rng = createPrng(29037020);
  let cielo: [string, string, string];
  let colorNube: string;
  let opacidadNube: [string, string];

  if (noche) {
    cielo = ["#111b35", "#233b51", "#425a67"];
    colorNube = "#a9bac5";
    opacidadNube = [".34", ".28"];
  } else if (ambiente === "tormenta") {
    cielo = ["#243847", "#516775", "#8298a1"];
    colorNube = "#778995";
    opacidadNube = [".98", ".82"];
  } else if (ambiente === "lluvia") {
    cielo = ["#526977", "#8399a2", "#b2c2c3"];
    colorNube = "#d6dee0";
    opacidadNube = [".92", ".78"];
  } else if (ambiente === "nublado") {
    cielo = ["#5a8298", "#9eb8c3", "#d0dce0"];
    colorNube = "#f4f6f5";
    opacidadNube = [".94", ".8"];
  } else {
    cielo = ["#17527c", "#6cb0d3", "#bfe0ee"];
    colorNube = "#ffffff";
    opacidadNube = [".85", ".7"];
  }

  let astro = "";
  if (noche) {
    if (ambiente !== "lluvia" && ambiente !== "tormenta") {
      astro =
        '<g fill="#f3e7ad"><circle cx="277" cy="27" r="1.1"/>' +
        '<circle cx="305" cy="53" r=".9"/><circle cx="248" cy="65" r=".8"/>' +
        '<circle cx="326" cy="32" r="1.2"/><circle cx="222" cy="37" r=".7"/></g>' +
        '<path d="M288 27a10 10 0 1 0 13 13a8 8 0 1 1-13-13Z" fill="#f3e7ad"/>';
    }
  } else if (ambiente === "despejado") {
    astro =
      '<g fill="#ffe38a" stroke="#fff1bc" stroke-width="1">' +
      '<circle cx="286" cy="52" r="10"/><path d="M286 34v-6m0 48v-6m18-18h6m-48 0h6' +
      'm31-13 4-4m-34 34 4-4m0-26-4-4m34 34-4-4"/></g>';
  }

  const aves =
    noche || ambiente === "lluvia" || ambiente === "tormenta"
      ? []
      : [
          '<g class="jn-ave" style="--dur:30s;--delay:-8s"><g transform="translate(0 84)">' +
            '<path d="M0 0q3 -3.2 6 0q3 -3.2 6 0" fill="none" stroke="#173a52" stroke-width="1.2" ' +
            'stroke-linecap="round"/></g></g>',
          '<g class="jn-ave" style="--dur:38s;--delay:-21s"><g transform="translate(0 102)">' +
            '<path d="M0 0q2.5 -2.6 5 0q2.5 -2.6 5 0" fill="none" stroke="#173a52" stroke-width="1" ' +
            'stroke-linecap="round"/></g></g>',
        ];

  const lucesNoche = noche
    ? '<g fill="#ffd982" opacity=".95"><rect x="156" y="79" width="8" height="13"/>' +
      '<rect x="176" y="105" width="8" height="13"/><rect x="80" y="108" width="5" height="9"/>' +
      '<rect x="102" y="108" width="5" height="9"/><rect x="28" y="148" width="6" height="12"/>' +
      '<rect x="170" y="138" width="7" height="14"/><rect x="200" y="138" width="7" height="14"/>' +
      "</g>"
    : "";

  const coloresGrava = ["#8f7b5a", "#d3bf96", "#a08d6b", "#6f5f46"] as const;
  const grava: string[] = [];
  for (let i = 0; i < 85; i++) {
    const color = rng.choice(coloresGrava);
    grava.push(
      `<ellipse cx="${rng.uniform(2, 338).toFixed(1)}" cy="${rng.uniform(244, 359).toFixed(1)}" ` +
        `rx="${rng.uniform(0.8, 2.3).toFixed(1)}" ry="${rng.uniform(0.6, 1.4).toFixed(1)}" fill="${color}" opacity=".55"/>`
    );
  }

  let hierba = "";
  for (let i = 0; i < 18; i++) {
    const hx = rng.uniform(4, 336);
    const hy = rng.uniform(246, 354);
    hierba += `M${hx.toFixed(1)} ${hy.toFixed(1)}l-2.2 -6.5M${hx.toFixed(1)} ${hy.toFixed(1)}l.2 -7.5M${hx.toFixed(1)} ${hy.toFixed(1)}l2.4 -6`;
  }

  const tonosPiedra = [
    "#7e8782",
    "#919a95",
    "#6d7671",
    "#a0a79f",
    "#868f86",
  ] as const;
  const piedras: string[] = [];
  let py = 364.0;
  while (py < 470) {
    const altoFila = 11 + rng.random() * 2;
    let px = -rng.random() * 12;
    while (px < 340) {
      const anchoBloque = 15 + rng.random() * 14;
      const color = rng.choice(tonosPiedra);
      piedras.push(
        `<rect x="${px.toFixed(1)}" y="${py.toFixed(1)}" width="${(anchoBloque - 0.8).toFixed(1)}" ` +
          `height="${(altoFila - 0.8).toFixed(1)}" rx="2.2" fill="${color}"/>`
      );
      px += anchoBloque;
    }
    py += altoFila;
  }

  const peldanos = 10;
  const dx = 5.6;
  const dy = 11.2;
  const x0 = 172.0;
  const y0 = 190.0;
  const borde: Array<[number, number]> = [[x0, y0]];
  for (let i = 0; i < peldanos; i++) {
    borde.push([x0 + (i + 1) * dx, y0 + i * dy]);
    borde.push([x0 + (i + 1) * dx, y0 + (i + 1) * dy]);
  }
  const inferior: Array<[number, number]> = [...borde]
    .reverse()
    .map(([bx, by]) => [bx, by + 19]);
  const puntosEscalera = [...borde, ...inferior]
    .map(([bx, by]) => `${bx.toFixed(1)},${by.toFixed(1)}`)
    .join(" ");
  let postes = "";
  for (let i = 0; i < peldanos; i += 2) {
    postes += `M${(x0 + (i + 1) * dx).toFixed(1)} ${(y0 + i * dy).toFixed(1)}v-15`;
  }
  const xf = x0 + peldanos * dx;
  const yf = y0 + peldanos * dy;

  const ventanasBlancas = [166, 196, 226, 256, 286]
    .map((x) => ventanaSvg(x, 138, 14, 20, false, "#cfe0ea", "#35617b"))
    .join("");
  const merlones: string[] = [];
  for (let x = 156; x < 336; x += 15) {
    merlones.push(`<rect x="${x}" y="105" width="9" height="10" fill="#c3d8e4"/>`);
  }
  const ventanasAmarillo = [76, 98, 120]
    .map(
      (x) =>
        ventanaSvg(x, 106, 13, 24, false, "#2b5a79", "#3d7fa5") +
        `<rect x="${x - 4}" y="106" width="3" height="24" fill="#3b6f95"/>` +
        `<rect x="${x + 14}" y="106" width="3" height="24" fill="#3b6f95"/>`
    )
    .join("");
  const arcosAmarillo = [74, 98, 122]
    .map((x) => ventanaSvg(x, 152, 14, 34, true, "#7a5a2c", "#5b4527"))
    .join("");
  let postesBalcon = "";
  for (let x = 68; x < 152; x += 6) postesBalcon += `M${x} 131v7`;
  let postesVerde = "";
  for (let x = 2; x < 68; x += 5) postesVerde += `M${x} 118v8`;
  const ventanasVerde = [8, 28, 48]
    .map((x) => ventanaSvg(x, 144, 12, 24, true, "#d9f1df", "#2f6a5c"))
    .join("");

  const result = [
    "<defs>",
    '<linearGradient id="jn-cielo" x1="0" y1="0" x2="0" y2="1">',
    `<stop offset="0" stop-color="${cielo[0]}"/><stop offset=".55" stop-color="${cielo[1]}"/>`,
    `<stop offset="1" stop-color="${cielo[2]}"/></linearGradient>`,
    '<linearGradient id="jn-muro" x1="0" y1="0" x2="0" y2="1">',
    '<stop offset="0" stop-color="#e8e1ce"/><stop offset="1" stop-color="#c2b8a0"/></linearGradient>',
    '<linearGradient id="jn-talud" x1="0" y1="0" x2="0" y2="1">',
    '<stop offset="0" stop-color="#cdb588"/><stop offset="1" stop-color="#8a7656"/></linearGradient>',
    '<linearGradient id="jn-humedad" x1="0" y1="0" x2="0" y2="1">',
    '<stop offset="0" stop-color="#0b1a14" stop-opacity="0"/>',
    '<stop offset="1" stop-color="#0b1a14" stop-opacity=".32"/></linearGradient>',
    '<linearGradient id="jn-lecho" x1="0" y1="0" x2="0" y2="1">',
    '<stop offset="0" stop-color="#8c7658"/><stop offset="1" stop-color="#4c3f31"/></linearGradient>',
    "</defs>",
    '<rect width="340" height="200" fill="url(#jn-cielo)"/>',
    astro,
    '<text x="20" y="27" font-size="12" font-weight="700" letter-spacing="2" fill="#ffffff" ' +
      'font-family="Arial, sans-serif">NIVEL DEL RÍO</text>',
    '<text x="20" y="42" font-size="9" letter-spacing="1" fill="#dcedf6" ' +
      `font-family="Arial, sans-serif">CALAMAR · BOLÍVAR · IDEAM ${estacionCodigo}</text>`,
    '<g class="jn-nube" style="--dur:95s;--delay:-34s;--reposo:70px"><g transform="translate(0 68)">' +
      `<ellipse cx="0" cy="0" rx="24" ry="6.5" fill="${colorNube}" opacity="${opacidadNube[0]}"/>` +
      `<ellipse cx="10" cy="-5" rx="14" ry="7" fill="${colorNube}" opacity="${opacidadNube[0]}"/>` +
      `<ellipse cx="-11" cy="-3" rx="12" ry="5.5" fill="${colorNube}" opacity="${opacidadNube[0]}"/></g></g>`,
    '<g class="jn-nube" style="--dur:120s;--delay:-80s;--reposo:250px"><g transform="translate(0 94)">' +
      `<ellipse cx="0" cy="0" rx="19" ry="5" fill="${colorNube}" opacity="${opacidadNube[1]}"/>` +
      `<ellipse cx="8" cy="-4" rx="11" ry="5.5" fill="${colorNube}" opacity="${opacidadNube[1]}"/></g></g>`,
    '<rect x="146" y="64" width="58" height="124" fill="#7c6a63"/>' +
      '<rect x="143" y="59" width="64" height="7" fill="#cdc4b5"/>' +
      '<path d="M152 70v118M168 70v118M184 70v118M198 70v118" stroke="#000" stroke-opacity=".08" stroke-width="3"/>' +
      '<rect x="156" y="78" width="8" height="15" fill="#2b3944"/><rect x="176" y="78" width="8" height="15" fill="#2b3944"/>' +
      '<rect x="156" y="104" width="8" height="15" fill="#2b3944"/><rect x="176" y="104" width="8" height="15" fill="#2b3944"/>',
    '<rect x="150" y="122" width="190" height="66" fill="#e8eff2"/>' +
      '<rect x="150" y="114" width="190" height="10" fill="#d4e3eb"/>' +
      merlones.join("") +
      '<rect x="150" y="124" width="190" height="3" fill="#8db3c8"/>' +
      ventanasBlancas +
      ventanaSvg(312, 156, 16, 30, true, "#cfe0ea", "#5f8aa0"),
    '<path d="M56 100L96 85H154V94H66Z" fill="#b2533a"/>' +
      '<path d="M56 100L96 85" stroke="#7d3724" stroke-width="1.2"/>' +
      '<rect x="66" y="94" width="86" height="92" fill="#f2cf45"/>' +
      '<rect x="140" y="94" width="12" height="92" fill="#c9a62d" opacity=".55"/>' +
      '<rect x="64" y="94" width="90" height="4" fill="#d9b530"/>' +
      ventanasAmarillo +
      '<rect x="64" y="138" width="90" height="3" fill="#b8962a"/>' +
      `<path d="${postesBalcon}M64 131H154" stroke="#9a7c22" stroke-width="1.2" fill="none"/>` +
      arcosAmarillo +
      '<rect x="88" y="146" width="44" height="8" fill="#1f5a4a"/>' +
      '<path d="M92 150h12m4 0h8m4 0h6" stroke="#e8f0d8" stroke-width="1.4"/>',
    lucesNoche,
    '<rect x="0" y="130" width="68" height="56" fill="#85c6a4"/>' +
      '<rect x="0" y="126" width="68" height="5" fill="#e6f0e2"/>' +
      '<rect x="0" y="116" width="68" height="2.4" fill="#f2f6ef"/>' +
      `<path d="${postesVerde}" stroke="#f2f6ef" stroke-width="1.5"/>` +
      ventanasVerde +
      '<rect x="0" y="174" width="68" height="12" fill="#6aae8d"/>',
    '<path d="M196 186L205 169H258L267 186Z" fill="#d4673f"/>' +
      '<path d="M214 169L211 186M226 169L225 186M238 169L238 186M250 169L252 186" ' +
      'stroke="#f1d3c3" stroke-width="1.6" opacity=".7"/>' +
      '<path d="M82 186L86 175H112L116 186Z" fill="#3b6fb0"/>',
    '<rect x="0" y="186" width="340" height="4" fill="#f1ebdc"/>' +
      '<rect x="0" y="190" width="340" height="46" fill="url(#jn-muro)"/>' +
      '<path d="M42 190v46M84 190v46M126 190v46M168 190v46M210 190v46M252 190v46M294 190v46" ' +
      'stroke="#5a4e38" stroke-opacity=".2"/>' +
      '<rect x="0" y="231" width="340" height="5" fill="#5a4a30" opacity=".22"/>' +
      '<rect x="50" y="197" width="100" height="30" rx="2" fill="#f3efe2" stroke="#d8d0ba"/>' +
      '<rect x="50" y="199" width="100" height="6" fill="#c2453a"/>' +
      '<rect x="58" y="210" width="46" height="10" rx="1" fill="#2d6b9b" opacity=".85"/>' +
      '<path d="M110 212h30M110 217h22" stroke="#9c9786" stroke-width="2"/>' +
      '<rect x="0" y="236" width="340" height="5" fill="#a89e88"/>',
    '<rect x="0" y="241" width="340" height="123" fill="url(#jn-talud)"/>' +
      '<path d="M60 242q4 30 -2 60q-4 30 4 60M150 242q-4 34 2 66q4 28 -2 54M262 242q5 28 -1 58q-5 32 3 64" ' +
      'fill="none" stroke="#4f3d22" stroke-opacity=".12" stroke-width="4" stroke-linecap="round"/>' +
      '<path d="M0 266Q90 257 170 267T340 262M0 300Q80 292 170 301T340 296M0 334Q90 326 170 335T340 330" ' +
      'fill="none" stroke="#5e4a2a" stroke-opacity=".2" stroke-width="1.4"/>' +
      '<path d="M226 306Q272 297 340 293" fill="none" stroke="#dccba3" stroke-width="5" ' +
      'stroke-linecap="round" opacity=".55"/>',
    grava.join(""),
    `<path d="${hierba}" stroke="#4d8a3a" stroke-width="1.1" stroke-linecap="round" fill="none"/>`,
    '<text x="46" y="288" font-size="9" font-weight="700" letter-spacing="2" fill="#fff8e6" ' +
      'opacity=".9" font-family="Arial, sans-serif">TALUD</text>',
    '<rect x="0" y="362" width="340" height="110" fill="#59625d"/>',
    piedras.join(""),
    '<rect x="0" y="360" width="340" height="4" fill="#6d6a5b"/>' +
      '<rect x="0" y="400" width="340" height="72" fill="url(#jn-humedad)"/>' +
      '<path d="M0 466Q40 459 90 465T200 464T340 461V500H0Z" fill="url(#jn-lecho)"/>' +
      '<circle cx="52" cy="482" r="2.4" fill="#b19a78" opacity=".7"/>' +
      '<circle cx="171" cy="488" r="3" fill="#a08a69" opacity=".7"/>' +
      '<circle cx="268" cy="480" r="2.2" fill="#b19a78" opacity=".7"/>',
    `<polygon points="${puntosEscalera}" fill="#d6cfba" stroke="#7a7260" stroke-width=".9" stroke-linejoin="round"/>` +
      `<path d="M${x0.toFixed(1)} ${(y0 - 15).toFixed(1)}L${xf.toFixed(1)} ${(yf - 15).toFixed(1)}${postes}" stroke="#2f414c" ` +
      'stroke-width="1.5" fill="none" stroke-linecap="round"/>',
    aves.join(""),
  ].join("\n");

  escenaFijaCache.set(cacheKey, result);
  return result;
}

function tarullasSvg(ySuperficie: number): string {
  const plants: Array<[number, number, number]> = [
    [72, 0.82, 0],
    [182, 1.0, -1.4],
    [292, 0.72, -2.2],
  ];
  return plants
    .map(
      ([x, escala, demora]) =>
        `<g transform="translate(${x} ${(ySuperficie + 2).toFixed(1)}) scale(${escala})">` +
        `<g class="jn-tarulla" style="--delay:${demora}s">` +
        '<path d="M0 5q-5 8 -3 20m3-20q5 9 8 19m-8-19q-1 10 -1 22" ' +
        'fill="none" stroke="#9ab98a" stroke-width="1" opacity=".8"/>' +
        '<ellipse cx="-8" cy="3" rx="8" ry="3.6" transform="rotate(-25 -8 3)" fill="#65a85e"/>' +
        '<ellipse cx="0" cy="1" rx="9" ry="3.8" transform="rotate(-8 0 1)" fill="#83bb64"/>' +
        '<ellipse cx="9" cy="3" rx="8" ry="3.5" transform="rotate(22 9 3)" fill="#559951"/>' +
        '<ellipse cx="-2" cy="8" rx="7" ry="3" transform="rotate(-35 -2 8)" fill="#4d8d4e"/>' +
        '<circle cx="2" cy="-2" r="2" fill="#d88aaf"/><circle cx="5" cy="-3" r="1.7" fill="#e7b5ca"/>' +
        "</g></g>"
    )
    .join("");
}

export function buildRiverGaugeData(params: {
  nivelCm: number;
  umbrales: ThresholdsInfo;
  ambiente: AmbienteTipo;
  noche: boolean;
  vientoKmh: number;
  estacionCodigo: string;
  nivelReferenciaCm: number;
  nivelMurallaCm: number;
}) {
  const {
    nivelCm,
    umbrales,
    ambiente,
    noche,
    vientoKmh,
    estacionCodigo,
    nivelReferenciaCm,
    nivelMurallaCm,
  } = params;

  const yCero = 452.0;
  const yMuralla = 186.0;
  const yFondo = 482.0;
  const pxPorCm = (yCero - yMuralla) / nivelMurallaCm;
  const posicion = (cm: number) => yCero - cm * pxPorCm;
  const yS = posicion(Math.max(0.0, Math.min(nivelCm, nivelMurallaCm * 1.12)));
  const sobreMuralla = nivelCm > nivelMurallaCm;

  const gente: string[] = [];
  if (!noche && yS > 192) {
    gente.push(
      `<g transform="translate(160 186)"><g class="jn-respira">${personaSvg("#26394a", "#1d2a35")}</g></g>`
    );
  }
  if (!noche && yS > 303) {
    gente.push(
      `<g transform="translate(262 299)"><g class="jn-camina">${personaSvg("#3f7fc0", "#59606a", "#c68a63", true)}</g></g>`
    );
  }

  const botes = noche
    ? ""
    : ([
        [42, "a", -0.4, 3.7],
        [96, "b", -1.9, 4.3],
        [160, "c", -3.1, 4.9],
      ] as Array<[number, "a" | "b" | "c", number, number]>)
        .map(([x, tipo, retraso, duracion]) =>
          boteSvg(x, yS, tipo, retraso, duracion)
        )
        .join("");

  const perfilesBase: Array<Omit<FishProfile, "x">> = [
    {
      especie: "bocachico",
      largo: 43,
      alto: 19,
      profundidad: 68,
      velocidad: 1.0,
      fase: 0.15,
      rayas: [-0.45, -0.15, 0.15, 0.42],
    },
    {
      especie: "bagre",
      largo: 47,
      alto: 18,
      profundidad: 51,
      velocidad: 0.88,
      fase: 0.55,
      rayas: [],
    },
    {
      especie: "mojarra",
      largo: 36,
      alto: 22,
      profundidad: 35,
      velocidad: 1.12,
      fase: 0.8,
      rayas: [-0.28, 0.05, 0.34],
    },
    {
      especie: "sabalo",
      largo: 46,
      alto: 17,
      profundidad: 20,
      velocidad: 1.08,
      fase: 0.35,
      rayas: [],
    },
    {
      especie: "doncella",
      largo: 49,
      alto: 18,
      profundidad: 78,
      velocidad: 0.82,
      fase: 0.65,
      rayas: [-0.4, -0.08, 0.26],
    },
    {
      especie: "pacora",
      largo: 40,
      alto: 23,
      profundidad: 45,
      velocidad: 0.96,
      fase: 0.42,
      rayas: [-0.3, 0.24],
    },
    {
      especie: "capaz",
      largo: 38,
      alto: 16,
      profundidad: 60,
      velocidad: 1.18,
      fase: 0.9,
      rayas: [],
    },
  ];
  const fishProfiles: FishProfile[] = perfilesBase.map((pez, indice) => ({
    ...pez,
    x: 58 + indice * 34,
  }));

  const baseBurbuja = yFondo - 4;
  const sube = baseBurbuja - yS;
  const burbujas: string[] = [];
  if (sube > 10) {
    const specs: Array<[number, number, number, number]> = [
      [58, 2.2, 5.5, 0],
      [112, 1.6, 4.4, 1.7],
      [176, 2.4, 6.2, 3.1],
      [236, 1.8, 4.9, 0.8],
      [296, 2.0, 5.8, 2.6],
      [140, 1.4, 4.1, 3.9],
    ];
    for (const [bx, radio, duracion, retraso] of specs) {
      burbujas.push(
        `<circle class="jn-burbuja" cx="${bx}" cy="${baseBurbuja.toFixed(0)}" r="${radio}" fill="none" ` +
          `stroke="#dcf6fa" stroke-width="1" style="--sube:${sube.toFixed(0)}px;--dur:${duracion}s;--delay:-${retraso}s"/>`
      );
    }
  }

  const gotasLluvia: string[] = [];
  let relampago = "";
  if (ambiente === "lluvia" || ambiente === "tormenta") {
    const rngLluvia = createPrng(1996);
    for (let i = 0; i < 32; i++) {
      const x = rngLluvia.uniform(4, 336);
      const y = rngLluvia.uniform(0, Math.max(1, yS - 12));
      gotasLluvia.push(
        `<path class="jn-gota-lluvia" style="--delay:${rngLluvia.uniform(-1.8, 0).toFixed(2)}s" ` +
          `d="M${x.toFixed(1)} ${y.toFixed(1)}l-3.5 9" fill="none" stroke="#e4f2f4" ` +
          'stroke-width="1" stroke-linecap="round"/>'
      );
    }
    if (ambiente === "tormenta") {
      relampago =
        '<path class="jn-relampago" d="m292 45-12 22h9l-5 17 20-26h-10l7-13Z" ' +
        'fill="#fff5c4" opacity=".8"/>';
    }
  }
  const lluviaSvg = `<g aria-hidden="true">${gotasLluvia.join("")}${relampago}</g>`;

  const coloresAguaDia: Record<AmbienteTipo, [string, string, string]> = {
    despejado: ["#2aa3b4", "#127a91", "#0c4057"],
    nublado: ["#3793a0", "#176d80", "#103e51"],
    lluvia: ["#448c98", "#1a6274", "#123b4c"],
    tormenta: ["#397987", "#164f63", "#0c2e43"],
  };
  const coloresAguaNoche: Record<AmbienteTipo, [string, string, string]> = {
    despejado: ["#1e7688", "#104d68", "#092b42"],
    nublado: ["#286b79", "#124459", "#092b40"],
    lluvia: ["#285d6e", "#103b53", "#08253a"],
    tormenta: ["#204d61", "#0d344a", "#071f34"],
  };
  const [aguaSuperficie, aguaMedia, aguaFondo] = (
    noche ? coloresAguaNoche : coloresAguaDia
  )[ambiente];

  let destellos = "";
  for (let k = 0; k < 8; k++) {
    destellos += `M${k * 85 + 10} 9h14M${k * 85 + 48} 17h9M${k * 85 + 28} 27h11`;
  }
  const agua =
    '<defs><linearGradient id="jn-agua" gradientUnits="userSpaceOnUse" ' +
    `x1="0" y1="${yS.toFixed(1)}" x2="0" y2="500">` +
    `<stop offset="0" stop-color="${aguaSuperficie}" stop-opacity=".52"/>` +
    `<stop offset=".16" stop-color="${aguaSuperficie}" stop-opacity=".62"/>` +
    `<stop offset=".52" stop-color="${aguaMedia}" stop-opacity=".76"/>` +
    `<stop offset="1" stop-color="${aguaFondo}" stop-opacity=".90"/></linearGradient>` +
    '<linearGradient id="jn-brillo-sup" gradientUnits="userSpaceOnUse" ' +
    `x1="0" y1="${yS.toFixed(1)}" x2="0" y2="${(yS + 26).toFixed(1)}">` +
    `<stop offset="0" stop-color="#ffffff" stop-opacity="${noche ? ".14" : ".28"}"/>` +
    '<stop offset="1" stop-color="#ffffff" stop-opacity="0"/></linearGradient></defs>' +
    `<rect x="0" y="${yS.toFixed(1)}" width="340" height="${(500 - yS).toFixed(1)}" fill="url(#jn-agua)"/>` +
    `<rect x="0" y="${yS.toFixed(1)}" width="340" height="26" fill="url(#jn-brillo-sup)"/>` +
    `<g transform="translate(0 ${yS.toFixed(1)})"><g class="jn-ola" style="--dur:16s">` +
    `<path d="${destellos}" stroke="#ffffff" stroke-opacity="${noche ? ".18" : ".32"}" stroke-width="1" ` +
    'stroke-linecap="round" fill="none"/></g></g>';

  const factorViento = Math.max(0.55, 1 - Math.min(Math.max(vientoKmh, 0), 55) / 75);
  const duracionOlaAtras = 13 * factorViento;
  const duracionOlaFrente = 8 * factorViento;
  const olaAtras =
    `<g transform="translate(0 ${yS.toFixed(1)})"><g class="jn-ola" ` +
    `style="--dur:${duracionOlaAtras.toFixed(1)}s;--delay:-4s">` +
    `<path d="${olaPath(2.4, 68, 10, 12)}" fill="${aguaSuperficie}" opacity=".34"/></g></g>`;
  const olaFrente =
    `<g transform="translate(0 ${yS.toFixed(1)})"><g class="jn-ola" style="--dur:${duracionOlaFrente.toFixed(1)}s">` +
    `<path d="${olaPath(3.2, 85, 8, 14)}" fill="${aguaSuperficie}" fill-opacity=".28" ` +
    `stroke="#e8fbff" stroke-opacity="${noche ? ".42" : ".72"}" stroke-width="1.2"/></g></g>`;

  const marcas: string[] = [];
  for (let metro = 0; metro <= 10; metro++) {
    const y = posicion(metro * 100);
    marcas.push(
      `<path d="M24 ${y.toFixed(1)}H36" stroke="#d7e9f0" stroke-width="1"/>` +
        `<text x="20" y="${(y + 3.5).toFixed(1)}" text-anchor="end" font-size="10" fill="#eef7fa" ` +
        `font-family="Arial, sans-serif">${metro}</text>`
    );
    if (metro < 10) {
      marcas.push(
        `<path d="M30 ${(y - pxPorCm * 50).toFixed(1)}H36" stroke="#9fc0cc" stroke-width=".8"/>`
      );
    }
  }

  const regla =
    `<rect x="6" y="${(yMuralla - 10).toFixed(1)}" width="32" height="${(yCero - yMuralla + 22).toFixed(1)}" rx="6" ` +
    'fill="#0f2c3b" fill-opacity=".72"/>' +
    marcas.join("") +
    `<text x="20" y="${(yCero + 17).toFixed(1)}" text-anchor="middle" font-size="8" fill="#9fc0cc" ` +
    'font-family="Arial, sans-serif">m</text>' +
    `<polygon points="39,${yS.toFixed(1)} 47,${(yS - 4.5).toFixed(1)} 47,${(yS + 4.5).toFixed(1)}" fill="#ffffff" stroke="#167f94"/>`;

  const lineas = [
    `<path d="M40 ${posicion(nivelReferenciaCm).toFixed(1)}H340" stroke="#0f2c3b" stroke-opacity=".6" ` +
      'stroke-dasharray="5 4" stroke-width="1.2"/>',
  ];

  interface Etiqueta {
    y: number;
    texto: string;
    fondo: string;
    tinta: string;
    prioridad: number;
    pos?: number;
  }

  const etiquetas: Etiqueta[] = [
    {
      y: posicion(nivelMurallaCm),
      texto: sobreMuralla ? "MURALLA SUPERADA" : "MURALLA 10 m",
      fondo: sobreMuralla ? "#b5432f" : "#4b4130",
      tinta: "#ffffff",
      prioridad: 0,
    },
    {
      y: posicion(nivelReferenciaCm),
      texto: `Ref. ${nivelReferenciaCm} cm`,
      fondo: "#0f2c3b",
      tinta: "#e3f0f5",
      prioridad: 1,
    },
    {
      y: yS,
      texto: `${(nivelCm / 100).toFixed(2)} m`,
      fondo: "#167f94",
      tinta: "#ffffff",
      prioridad: 2,
    },
  ];

  const coloresUmbral: Record<"amarilla" | "naranja" | "roja", string> = {
    amarilla: "#e6b84f",
    naranja: "#f08c53",
    roja: "#e26168",
  };
  (["amarilla", "naranja", "roja"] as const).forEach((nombre) => {
    const valor = umbrales.valores[nombre];
    if (valor === null || valor < 0 || valor > nivelMurallaCm) return;
    const color = coloresUmbral[nombre];
    lineas.push(
      `<path d="M40 ${posicion(valor).toFixed(1)}H340" stroke="${color}" stroke-width="1.6" stroke-dasharray="2 3"/>`
    );
    etiquetas.push({
      y: posicion(valor),
      texto: nombre.charAt(0).toUpperCase() + nombre.slice(1),
      fondo: color,
      tinta: "#102b3b",
      prioridad: 1,
    });
  });

  etiquetas.sort((a, b) => a.y - b.y || a.prioridad - b.prioridad);
  let previo = 14.0 - 18;
  for (const e of etiquetas) {
    previo = Math.max(e.y, previo + 18);
    e.pos = previo;
  }
  let limite = 488.0;
  for (let i = etiquetas.length - 1; i >= 0; i--) {
    const e = etiquetas[i];
    limite = Math.min(e.pos!, limite);
    e.pos = limite;
    limite -= 18;
  }

  const etiquetasSvg = etiquetas.map((e) => {
    const anchoPildora = 14 + e.texto.length * 6.3;
    const xPildora = 334 - anchoPildora;
    const yp = e.pos!;
    return (
      `<rect x="${xPildora.toFixed(1)}" y="${(yp - 8).toFixed(1)}" width="${anchoPildora.toFixed(1)}" height="16" rx="8" ` +
      `fill="${e.fondo}" fill-opacity=".92"/>` +
      `<text x="${(xPildora + anchoPildora / 2).toFixed(1)}" y="${(yp + 3.6).toFixed(1)}" text-anchor="middle" ` +
      `font-size="10" font-weight="700" fill="${e.tinta}" font-family="Arial, sans-serif">${e.texto}</text>`
    );
  });

  const sceneHtml = [
    escenaFijaSvg(ambiente, noche, estacionCodigo),
    lluviaSvg,
    gente.join(""),
    agua,
    olaAtras,
    botes,
    tarullasSvg(yS),
    burbujas.join(""),
    olaFrente,
  ].join("\n");

  const overlayHtml = [
    lineas.join(""),
    regla,
    etiquetasSvg.join(""),
  ].join("\n");

  return {
    ySurface: yS,
    sceneHtml,
    overlayHtml,
    fishProfiles,
  };
}
