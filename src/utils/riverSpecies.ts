export type FishSpeciesId =
  | "bocachico"
  | "bagre"
  | "mojarra"
  | "sabalo"
  | "doncella"
  | "pacora"
  | "capaz"
  | "nicuro"
  | "dorada"
  | "arenca"
  | "blanquillo"
  | "cachama";

export interface FishPalette {
  cuerpo: number;
  lomo: number;
  vientre: number;
  aleta: number;
  raya: number;
}

export interface FishProfile {
  especie: FishSpeciesId;
  largo: number;
  alto: number;
  anchoFactor: number;
  profundidad: number;
  minProfundidad: number;
  maxProfundidad: number;
  velocidad: number;
  fase: number;
  rayas: number[];
  barbas: boolean;
  colaHorquilla: number;
  aletaAlta: number;
  x: number;
}

export const FISH_PALETTES: Record<FishSpeciesId, FishPalette> = {
  bocachico: {
    cuerpo: 0xdfb258,
    lomo: 0xa46636,
    vientre: 0xf4e3b8,
    aleta: 0xc27b3a,
    raya: 0x8e572f,
  },
  bagre: {
    cuerpo: 0x76a29a,
    lomo: 0x356267,
    vientre: 0xc7dad0,
    aleta: 0x4b7b7e,
    raya: 0x2f4f53,
  },
  mojarra: {
    cuerpo: 0xe3965c,
    lomo: 0x944f35,
    vientre: 0xfde0af,
    aleta: 0xd66d46,
    raya: 0x9e593f,
  },
  sabalo: {
    cuerpo: 0xa9c7c8,
    lomo: 0x517684,
    vientre: 0xedf1e2,
    aleta: 0x6f979a,
    raya: 0x5d858e,
  },
  doncella: {
    cuerpo: 0xb19c7e,
    lomo: 0x63503e,
    vientre: 0xe8d7b8,
    aleta: 0x7e664d,
    raya: 0x5b4938,
  },
  pacora: {
    cuerpo: 0xa8c0b1,
    lomo: 0x5e7870,
    vientre: 0xe5e5cc,
    aleta: 0xc68850,
    raya: 0x6b8579,
  },
  capaz: {
    cuerpo: 0x96b3ae,
    lomo: 0x4f676d,
    vientre: 0xe5ece0,
    aleta: 0x728a86,
    raya: 0x567170,
  },
  nicuro: {
    cuerpo: 0xc6ab62,
    lomo: 0x6f6236,
    vientre: 0xf1e5be,
    aleta: 0xb08a42,
    raya: 0x7a6835,
  },
  dorada: {
    cuerpo: 0xebb94d,
    lomo: 0x9c682b,
    vientre: 0xfcf0c7,
    aleta: 0xd96634,
    raya: 0xb0742c,
  },
  arenca: {
    cuerpo: 0xb9d2d8,
    lomo: 0x4c7992,
    vientre: 0xf1f6f4,
    aleta: 0x87aebc,
    raya: 0x6491a6,
  },
  blanquillo: {
    cuerpo: 0xc2c6b8,
    lomo: 0x6a756b,
    vientre: 0xf2f2e4,
    aleta: 0x8d9586,
    raya: 0x727c71,
  },
  cachama: {
    cuerpo: 0x8ca17c,
    lomo: 0x4c5d47,
    vientre: 0xd97d54,
    aleta: 0xc26546,
    raya: 0x5d6e53,
  },
};

interface SpeciesTemplate {
  especie: FishSpeciesId;
  largo: number;
  alto: number;
  anchoFactor: number;
  minProfundidad: number;
  maxProfundidad: number;
  velocidad: number;
  rayas: number[];
  barbas: boolean;
  colaHorquilla: number;
  aletaAlta: number;
}

const SPECIES_TEMPLATES: readonly SpeciesTemplate[] = [
  {
    especie: "bocachico",
    largo: 22,
    alto: 9.2,
    anchoFactor: 0.2,
    minProfundidad: 42,
    maxProfundidad: 74,
    velocidad: 1.0,
    rayas: [-0.44, -0.15, 0.14, 0.4],
    barbas: false,
    colaHorquilla: 0.34,
    aletaAlta: 0.4,
  },
  {
    especie: "bagre",
    largo: 27,
    alto: 8.0,
    anchoFactor: 0.22,
    minProfundidad: 58,
    maxProfundidad: 88,
    velocidad: 0.84,
    rayas: [-0.52, -0.24, 0.04, 0.32],
    barbas: true,
    colaHorquilla: 0.32,
    aletaAlta: 0.36,
  },
  {
    especie: "mojarra",
    largo: 17,
    alto: 11.0,
    anchoFactor: 0.17,
    minProfundidad: 26,
    maxProfundidad: 58,
    velocidad: 1.08,
    rayas: [-0.28, 0.05, 0.34],
    barbas: false,
    colaHorquilla: 0.24,
    aletaAlta: 0.46,
  },
  {
    especie: "sabalo",
    largo: 24,
    alto: 8.2,
    anchoFactor: 0.18,
    minProfundidad: 15,
    maxProfundidad: 42,
    velocidad: 1.15,
    rayas: [],
    barbas: false,
    colaHorquilla: 0.42,
    aletaAlta: 0.42,
  },
  {
    especie: "doncella",
    largo: 25,
    alto: 7.8,
    anchoFactor: 0.21,
    minProfundidad: 64,
    maxProfundidad: 92,
    velocidad: 0.8,
    rayas: [-0.42, -0.1, 0.24],
    barbas: true,
    colaHorquilla: 0.3,
    aletaAlta: 0.35,
  },
  {
    especie: "pacora",
    largo: 20,
    alto: 10.2,
    anchoFactor: 0.19,
    minProfundidad: 36,
    maxProfundidad: 66,
    velocidad: 0.96,
    rayas: [-0.28, 0.22],
    barbas: false,
    colaHorquilla: 0.28,
    aletaAlta: 0.44,
  },
  {
    especie: "capaz",
    largo: 19,
    alto: 7.6,
    anchoFactor: 0.21,
    minProfundidad: 50,
    maxProfundidad: 80,
    velocidad: 1.06,
    rayas: [],
    barbas: true,
    colaHorquilla: 0.32,
    aletaAlta: 0.38,
  },
  {
    especie: "nicuro",
    largo: 17.5,
    alto: 7.2,
    anchoFactor: 0.2,
    minProfundidad: 46,
    maxProfundidad: 78,
    velocidad: 1.04,
    rayas: [-0.22, 0.14],
    barbas: true,
    colaHorquilla: 0.35,
    aletaAlta: 0.42,
  },
  {
    especie: "dorada",
    largo: 22.5,
    alto: 8.6,
    anchoFactor: 0.19,
    minProfundidad: 20,
    maxProfundidad: 50,
    velocidad: 1.18,
    rayas: [-0.15, 0.18],
    barbas: false,
    colaHorquilla: 0.38,
    aletaAlta: 0.4,
  },
  {
    especie: "arenca",
    largo: 15.5,
    alto: 6.2,
    anchoFactor: 0.16,
    minProfundidad: 12,
    maxProfundidad: 35,
    velocidad: 1.24,
    rayas: [],
    barbas: false,
    colaHorquilla: 0.4,
    aletaAlta: 0.36,
  },
  {
    especie: "blanquillo",
    largo: 26,
    alto: 6.8,
    anchoFactor: 0.2,
    minProfundidad: 68,
    maxProfundidad: 92,
    velocidad: 0.86,
    rayas: [],
    barbas: true,
    colaHorquilla: 0.36,
    aletaAlta: 0.34,
  },
  {
    especie: "cachama",
    largo: 20.5,
    alto: 11.8,
    anchoFactor: 0.2,
    minProfundidad: 34,
    maxProfundidad: 64,
    velocidad: 0.88,
    rayas: [-0.2, 0.15],
    barbas: false,
    colaHorquilla: 0.25,
    aletaAlta: 0.42,
  },
];

function createSeededPrng(seed: number) {
  let a = seed >>> 0;
  return {
    next(): number {
      a |= 0;
      a = (a + 0x6d2b79f5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    },
    range(min: number, max: number): number {
      return min + this.next() * (max - min);
    },
  };
}

export function generateRiverFishProfiles(seed = 29037020): FishProfile[] {
  const rng = createSeededPrng(seed);
  // Include all 12 species plus 2 extra schooling individuals (arenca, bocachico)
  const roster: SpeciesTemplate[] = [
    ...SPECIES_TEMPLATES,
    SPECIES_TEMPLATES[0],
    SPECIES_TEMPLATES[9],
  ];

  return roster.map((tpl, idx) => {
    const sizeScale = rng.range(0.86, 1.12);
    const speedScale = rng.range(0.88, 1.14);
    const profundidad = rng.range(tpl.minProfundidad, tpl.maxProfundidad);
    // Spread across the river including off-screen upstream entries so fish transit continuously
    const baseSpread = -25 + (idx / roster.length) * 380;
    const x = baseSpread + rng.range(-18, 18);

    return {
      especie: tpl.especie,
      largo: tpl.largo * sizeScale,
      alto: tpl.alto * sizeScale,
      anchoFactor: tpl.anchoFactor,
      profundidad,
      minProfundidad: tpl.minProfundidad,
      maxProfundidad: tpl.maxProfundidad,
      velocidad: tpl.velocidad * speedScale,
      fase: rng.next(),
      rayas: tpl.rayas,
      barbas: tpl.barbas,
      colaHorquilla: tpl.colaHorquilla,
      aletaAlta: tpl.aletaAlta,
      x,
    };
  });
}
