import type { ThresholdsInfo } from "../types";
import type { AmbienteTipo } from "./format";
import {
  generateRiverFishProfiles,
  type FishProfile,
} from "./riverSpecies";

export type { FishProfile };

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

function garzaBlancaSvg(x: number, y: number, escala = 1, noche = false): string {
  const pluma = noche ? "#bfd0d4" : "#f7faf8";
  const ala = noche ? "#9bb1b8" : "#dce8e3";
  const pico = noche ? "#b58b46" : "#e3a63b";
  const pata = noche ? "#465852" : "#5e6e5c";
  return (
    `<g transform="translate(${x} ${y}) scale(${escala})">` +
    `<path d="M-2 0v-11M2.5 0v-11" stroke="${pata}" stroke-width="1.1" stroke-linecap="round"/>` +
    `<ellipse cx="0" cy="-14" rx="7.5" ry="4.4" transform="rotate(-12 0 -14)" fill="${pluma}"/>` +
    `<path d="M-5 -14.5Q1 -18 6 -12.5Q0 -10.5 -5 -14.5Z" fill="${ala}"/>` +
    `<path d="M5 -16Q9 -22 7.5 -28.5" fill="none" stroke="${pluma}" stroke-width="2.2" stroke-linecap="round"/>` +
    `<circle cx="8" cy="-29.5" r="2.2" fill="${pluma}"/>` +
    `<path d="M9.6 -29.8L16.5 -28.8L9.6 -28.2Z" fill="${pico}"/>` +
    `<circle cx="8.6" cy="-29.9" r=".55" fill="#1e2a2e"/>` +
    `</g>`
  );
}

function tortugaOrillaSvg(x: number, y: number, noche = false): string {
  const caparazon = noche ? "#3b472b" : "#5a6b3d";
  const borde = noche ? "#595c3c" : "#888351";
  const piel = noche ? "#465434" : "#677c48";
  return (
    `<g transform="translate(${x} ${y})">` +
    `<path d="M-10 2Q-9 -5 0 -6Q9 -5 10 2Z" fill="${caparazon}" stroke="${borde}" stroke-width="1.0"/>` +
    `<path d="M-5 -4.5L-3.5 -1M0 -6V-1M5 -4.5L3.5 -1" stroke="${borde}" stroke-width=".65" opacity=".7"/>` +
    `<path d="M8.5 -0.8Q12.5 -4 14.8 -3.2Q15.4 -1.2 11 0.5Z" fill="${piel}"/>` +
    `<circle cx="13.6" cy="-2.7" r=".5" fill="#182118"/>` +
    `</g>`
  );
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
    opacidadNube = [".32", ".25"];
  } else if (ambiente === "tormenta") {
    cielo = ["#243847", "#516775", "#8298a1"];
    colorNube = "#778995";
    opacidadNube = [".96", ".80"];
  } else if (ambiente === "lluvia") {
    cielo = ["#526977", "#8399a2", "#b2c2c3"];
    colorNube = "#d6dee0";
    opacidadNube = [".90", ".76"];
  } else if (ambiente === "nublado") {
    cielo = ["#5a8298", "#9eb8c3", "#d0dce0"];
    colorNube = "#f4f6f5";
    opacidadNube = [".92", ".78"];
  } else {
    cielo = ["#17527c", "#6cb0d3", "#bfe0ee"];
    colorNube = "#ffffff";
    opacidadNube = [".82", ".68"];
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

  const avesLejanas =
    noche || ambiente === "lluvia" || ambiente === "tormenta"
      ? ""
      : '<g fill="none" stroke="#1e4458" stroke-width="1.1" stroke-linecap="round" opacity=".65">' +
        '<path d="M236 74q2.8 -2.6 5.6 0q2.8 -2.6 5.6 0"/>' +
        '<path d="M254 66q2.2 -2.0 4.4 0q2.2 -2.0 4.4 0"/></g>';

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
  for (let i = 0; i < 24; i++) {
    const hx = rng.uniform(4, 336);
    const hy = rng.uniform(246, 354);
    hierba += `M${hx.toFixed(1)} ${hy.toFixed(1)}l-2.2 -6.5M${hx.toFixed(1)} ${hy.toFixed(1)}l.2 -7.5M${hx.toFixed(1)} ${hy.toFixed(1)}l2.4 -6`;
  }

  // Natural cattails / reeds along the riverbank slope below the malecón
  const colorJuncos = noche ? "#224d39" : "#447e4c";
  const colorEspiga = noche ? "#3d2d20" : "#6c4b2e";
  const juncos: string[] = [];
  for (const jx of [26, 34, 43, 286, 295, 304]) {
    const baseJy = 278 + (jx % 11);
    const h = 22 + (jx % 8);
    juncos.push(
      `<path d="M${jx} ${baseJy}Q${jx + 2} ${baseJy - h * 0.5} ${jx + 3} ${baseJy - h}" stroke="${colorJuncos}" stroke-width="1.3" fill="none" stroke-linecap="round"/>` +
        `<rect x="${jx + 1.8}" y="${baseJy - h + 2}" width="2.4" height="6.5" rx="1.2" fill="${colorEspiga}"/>`
    );
  }

  const tonosPiedra = noche
    ? ["#3b4440", "#454e4a", "#333b37", "#4c544e"]
    : ["#7e8782", "#919a95", "#6d7671", "#a0a79f", "#868f86"];
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
    '<g class="jn-nube" style="--dur:110s;--delay:-34s;--reposo:70px"><g transform="translate(0 68)">' +
      `<ellipse cx="0" cy="0" rx="24" ry="6.5" fill="${colorNube}" opacity="${opacidadNube[0]}"/>` +
      `<ellipse cx="10" cy="-5" rx="14" ry="7" fill="${colorNube}" opacity="${opacidadNube[0]}"/>` +
      `<ellipse cx="-11" cy="-3" rx="12" ry="5.5" fill="${colorNube}" opacity="${opacidadNube[0]}"/></g></g>`,
    '<g class="jn-nube" style="--dur:140s;--delay:-80s;--reposo:250px"><g transform="translate(0 94)">' +
      `<ellipse cx="0" cy="0" rx="19" ry="5" fill="${colorNube}" opacity="${opacidadNube[1]}"/>` +
      `<ellipse cx="8" cy="-4" rx="11" ry="5.5" fill="${colorNube}" opacity="${opacidadNube[1]}"/></g></g>`,
    avesLejanas,
    // Calamar historic city buildings & waterfront
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
    // Malecón seawall
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
    // Natural bank slope & ecological details
    '<rect x="0" y="241" width="340" height="123" fill="url(#jn-talud)"/>' +
      '<path d="M60 242q4 30 -2 60q-4 30 4 60M150 242q-4 34 2 66q4 28 -2 54M262 242q5 28 -1 58q-5 32 3 64" ' +
      'fill="none" stroke="#4f3d22" stroke-opacity=".12" stroke-width="4" stroke-linecap="round"/>' +
      '<path d="M0 266Q90 257 170 267T340 262M0 300Q80 292 170 301T340 296M0 334Q90 326 170 335T340 330" ' +
      'fill="none" stroke="#5e4a2a" stroke-opacity=".2" stroke-width="1.4"/>' +
      '<path d="M226 306Q272 297 340 293" fill="none" stroke="#dccba3" stroke-width="5" ' +
      'stroke-linecap="round" opacity=".55"/>',
    `<path d="M204 284Q230 278 256 283" stroke="${noche ? "#3b2f23" : "#6b5239"}" stroke-width="5.2" stroke-linecap="round" fill="none"/>`,
    juncos.join(""),
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
  ].join("\n");

  escenaFijaCache.set(cacheKey, result);
  return result;
}

function tarullasSvg(ySuperficie: number): string {
  const plants: Array<[number, number, number]> = [
    [72, 0.8, 0],
    [182, 0.96, -3.4],
    [292, 0.72, -5.8],
  ];
  return plants
    .map(
      ([x, escala, demora]) =>
        `<g transform="translate(${x} ${(ySuperficie + 1.5).toFixed(1)}) scale(${escala})">` +
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

  // Riparian birds/turtles perched naturally on the lower bank when exposed above water
  const faunaRibera: string[] = [];
  if (yS > 282) {
    faunaRibera.push(garzaBlancaSvg(34, 276, 0.9, noche));
  }
  if (yS > 286) {
    faunaRibera.push(tortugaOrillaSvg(232, 279, noche));
  }

  const fishProfiles: FishProfile[] = generateRiverFishProfiles(29037020);

  const baseBurbuja = yFondo - 6;
  const sube = baseBurbuja - yS;
  const burbujas: string[] = [];
  if (sube > 16) {
    const specs: Array<[number, number, number, number]> = [
      [88, 1.5, 7.5, 0.4],
      [168, 1.8, 8.8, 3.2],
      [252, 1.4, 7.1, 5.1],
    ];
    for (const [bx, radio, duracion, retraso] of specs) {
      burbujas.push(
        `<circle class="jn-burbuja" cx="${bx}" cy="${baseBurbuja.toFixed(0)}" r="${radio}" fill="none" ` +
          `stroke="#d4f3f5" stroke-width=".9" style="--sube:${sube.toFixed(0)}px;--dur:${duracion}s;--delay:-${retraso}s"/>`
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
        'fill="#fff5c4" opacity=".75"/>';
    }
  }
  const lluviaSvg = `<g aria-hidden="true">${gotasLluvia.join("")}${relampago}</g>`;

  const coloresAguaDia: Record<AmbienteTipo, [string, string, string]> = {
    despejado: ["#2b98a3", "#137184", "#0c3c4c"],
    nublado: ["#368c95", "#176778", "#0f3a48"],
    lluvia: ["#41848f", "#195c6c", "#103744"],
    tormenta: ["#38737f", "#154b5c", "#0c2b3c"],
  };
  const coloresAguaNoche: Record<AmbienteTipo, [string, string, string]> = {
    despejado: ["#1b6d7c", "#0f485e", "#08283b"],
    nublado: ["#256470", "#114153", "#082839"],
    lluvia: ["#265766", "#0f384d", "#072234"],
    tormenta: ["#1d495a", "#0d3245", "#061e2f"],
  };
  const [aguaSuperficie, aguaMedia, aguaFondo] = (
    noche ? coloresAguaNoche : coloresAguaDia
  )[ambiente];

  const agua =
    '<defs><linearGradient id="jn-agua" gradientUnits="userSpaceOnUse" ' +
    `x1="0" y1="${yS.toFixed(1)}" x2="0" y2="500">` +
    `<stop offset="0" stop-color="${aguaSuperficie}" stop-opacity=".46"/>` +
    `<stop offset=".18" stop-color="${aguaSuperficie}" stop-opacity=".58"/>` +
    `<stop offset=".54" stop-color="${aguaMedia}" stop-opacity=".75"/>` +
    `<stop offset="1" stop-color="${aguaFondo}" stop-opacity=".90"/></linearGradient>` +
    '<linearGradient id="jn-reflejo-copa" gradientUnits="userSpaceOnUse" ' +
    `x1="0" y1="${yS.toFixed(1)}" x2="0" y2="${(yS + 42).toFixed(1)}">` +
    `<stop offset="0" stop-color="${noche ? "#1a3c2f" : "#3b764e"}" stop-opacity="${noche ? ".24" : ".28"}"/>` +
    '<stop offset="1" stop-color="#194d4b" stop-opacity="0"/></linearGradient>' +
    '<linearGradient id="jn-brillo-sup" gradientUnits="userSpaceOnUse" ' +
    `x1="0" y1="${yS.toFixed(1)}" x2="0" y2="${(yS + 20).toFixed(1)}">` +
    `<stop offset="0" stop-color="#ffffff" stop-opacity="${noche ? ".09" : ".18"}"/>` +
    '<stop offset="1" stop-color="#ffffff" stop-opacity="0"/></linearGradient></defs>' +
    `<rect x="0" y="${yS.toFixed(1)}" width="340" height="${(500 - yS).toFixed(1)}" fill="url(#jn-agua)"/>` +
    `<path d="M0 ${yS.toFixed(1)}H340V${(yS + 24).toFixed(1)}Q292 ${(yS + 40).toFixed(1)} 252 ${(yS + 26).toFixed(1)}T156 ${(yS + 20).toFixed(1)}T68 ${(yS + 32).toFixed(1)}T0 ${(yS + 24).toFixed(1)}Z" fill="url(#jn-reflejo-copa)"/>` +
    `<rect x="0" y="${yS.toFixed(1)}" width="340" height="20" fill="url(#jn-brillo-sup)"/>` +
    `<path d="M0 ${yS.toFixed(1)}Q85 ${(yS - 0.35).toFixed(2)} 170 ${(yS + 0.25).toFixed(2)}T340 ${yS.toFixed(1)}" fill="none" stroke="#e4f7f8" stroke-opacity="${noche ? ".26" : ".48"}" stroke-width="0.9"/>`;

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
    faunaRibera.join(""),
    agua,
    tarullasSvg(yS),
    burbujas.join(""),
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
