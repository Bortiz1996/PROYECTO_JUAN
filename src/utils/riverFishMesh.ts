import * as THREE from "three";
import { FISH_PALETTES, type FishProfile } from "./riverSpecies";

export interface FishEntity {
  group: THREE.Group;
  hitProxy: THREE.Mesh;
  geometry: THREE.BufferGeometry;
  baseVertices: Float32Array;
  vertices: THREE.BufferAttribute;
  tail: THREE.Object3D;
  dorsal: THREE.Object3D;
  pectorals: THREE.Object3D[];
  length: number;
  height: number;
  minY: number;
  maxY: number;
  preferredScreenY: number;
  baseSpeed: number;
  vx: number;
  vy: number;
  swimPhase: number;
  wanderPhase: number;
  wanderFreq: number;
  meanderAmp: number;
  burstTimer: number;
  burstBoost: number;
  pauseTimer: number;
  clickImpulse: number;
  clickNudgeY: number;
  tailEnergy: number;
}

export function buildRiverFishEntity(params: {
  perfil: FishProfile;
  indice: number;
  superficie: number;
  limiteInferior: number;
  baseCurrentSpeed: number;
  track: <T extends { dispose: () => void }>(item: T) => T;
}): FishEntity {
  const { perfil, indice, superficie, limiteInferior, baseCurrentSpeed, track } =
    params;
  const paleta = FISH_PALETTES[perfil.especie];
  const largo = perfil.largo;
  const alto = perfil.alto;
  const medioLargo = largo * 0.36;
  const medioAlto = alto * 0.4;
  const medioAncho = alto * perfil.anchoFactor;

  const material = (color: number, roughness = 0.43, metalness = 0.02) =>
    track(
      new THREE.MeshStandardMaterial({
        color,
        roughness,
        metalness,
        side: THREE.DoubleSide,
      })
    );

  const extruirAleta = (puntos: Array<[number, number]>, color: number) => {
    const forma = new THREE.Shape();
    forma.moveTo(puntos[0][0], puntos[0][1]);
    for (const [x, y] of puntos.slice(1)) forma.lineTo(x, y);
    forma.closePath();
    const geometria = track(
      new THREE.ExtrudeGeometry(forma, {
        depth: 0.14,
        bevelEnabled: true,
        bevelSegments: 2,
        bevelSize: 0.03,
        bevelThickness: 0.03,
        steps: 1,
      })
    );
    geometria.translate(0, 0, -0.07);
    return new THREE.Mesh(geometria, material(color, 0.62, 0.01));
  };

  const agregarTubo = (
    grupo: THREE.Group,
    puntos: Array<[number, number, number]>,
    color: number,
    radio = 0.16
  ) => {
    const curva = new THREE.CatmullRomCurve3(
      puntos.map(([x, y, z]) => new THREE.Vector3(x, y, z))
    );
    const geom = track(new THREE.TubeGeometry(curva, 10, radio, 5, false));
    grupo.add(new THREE.Mesh(geom, material(color, 0.62)));
  };

  const pez = new THREE.Group();
  const cuerpoGeometria = track(new THREE.SphereGeometry(1, 24, 16));
  const vertices = cuerpoGeometria.attributes.position as THREE.BufferAttribute;
  const originales = new Float32Array(vertices.array.length);
  const colores = new Float32Array(vertices.count * 3);
  const base = new THREE.Color(paleta.cuerpo);
  const lomo = new THREE.Color(paleta.lomo);
  const vientre = new THREE.Color(paleta.vientre);
  const colorVertice = new THREE.Color();

  for (let i = 0; i < vertices.count; i++) {
    const offset = i * 3;
    const nx = vertices.array[offset];
    const ny = vertices.array[offset + 1];
    const nz = vertices.array[offset + 2];
    const estrechamiento = 0.68 + 0.32 * Math.sqrt(Math.max(0, 1 - nx * nx));
    vertices.array[offset] = nx * medioLargo;
    vertices.array[offset + 1] = ny * medioAlto * estrechamiento;
    vertices.array[offset + 2] = nz * medioAncho * estrechamiento;
    originales[offset] = vertices.array[offset];
    originales[offset + 1] = vertices.array[offset + 1];
    originales[offset + 2] = vertices.array[offset + 2];

    if (ny > 0.12) {
      colorVertice.copy(base).lerp(lomo, Math.min(0.84, (ny - 0.12) * 0.92));
    } else if (ny < -0.18) {
      colorVertice
        .copy(base)
        .lerp(vientre, Math.min(0.9, (-ny - 0.18) * 1.1));
    } else {
      colorVertice.copy(base);
    }
    colorVertice.toArray(colores, offset);
  }

  cuerpoGeometria.setAttribute("color", new THREE.BufferAttribute(colores, 3));
  cuerpoGeometria.computeVertexNormals();

  const cuerpo = new THREE.Mesh(
    cuerpoGeometria,
    track(
      new THREE.MeshStandardMaterial({
        vertexColors: true,
        roughness: 0.32,
        metalness: 0.08,
      })
    )
  );
  cuerpo.name = "body";
  cuerpo.position.x = -medioLargo * 0.04;
  pez.add(cuerpo);

  const cabeza = new THREE.Mesh(
    track(new THREE.SphereGeometry(1, 18, 12)),
    material(paleta.cuerpo, 0.34, 0.04)
  );
  cabeza.scale.set(medioLargo * 0.5, medioAlto * 0.72, medioAncho * 0.83);
  cabeza.position.set(medioLargo * 0.57, medioAlto * 0.02, 0);
  pez.add(cabeza);

  const ojoBlanco = material(0xfff8e8, 0.25);
  const pupila = material(0x102a38, 0.15);
  const brillo = material(0xffffff, 0.12);
  const ojoRadius = Math.max(0.45, alto * 0.06);
  const ojoGeom = track(new THREE.SphereGeometry(ojoRadius, 10, 8));
  const pupilaGeom = track(new THREE.SphereGeometry(ojoRadius * 0.54, 8, 6));
  const brilloGeom = track(new THREE.SphereGeometry(ojoRadius * 0.18, 6, 6));

  for (const lado of [-1, 1]) {
    const ojo = new THREE.Mesh(ojoGeom, ojoBlanco);
    ojo.scale.set(0.9, 0.82, 0.42);
    ojo.position.set(
      medioLargo * 0.76,
      medioAlto * 0.23,
      lado * medioAncho * 0.72
    );
    pez.add(ojo);

    const centroPupila = new THREE.Mesh(pupilaGeom, pupila);
    centroPupila.scale.set(0.9, 0.95, 0.55);
    centroPupila.position.set(
      medioLargo * 0.8,
      medioAlto * 0.24,
      lado * (medioAncho * 0.79)
    );
    pez.add(centroPupila);

    const puntoLuz = new THREE.Mesh(brilloGeom, brillo);
    puntoLuz.position.set(
      medioLargo * 0.82,
      medioAlto * 0.29,
      lado * medioAncho * 0.84
    );
    pez.add(puntoLuz);
  }

  const superficieCuerpo = (
    nx: number,
    ny: number,
    side = 1
  ): [number, number, number] => {
    const t = 0.68 + 0.32 * Math.sqrt(Math.max(0, 1 - nx * nx));
    return [
      nx * medioLargo - medioLargo * 0.04,
      ny * medioAlto * t,
      side *
        medioAncho *
        t *
        Math.sqrt(Math.max(0.02, 1 - nx * nx - ny * ny)) *
        1.025,
    ];
  };

  const gillRadio = Math.max(0.11, alto * 0.016);
  const stripeRadio = Math.max(0.15, alto * 0.024);

  for (const lado of [-1, 1]) {
    agregarTubo(
      pez,
      [
        superficieCuerpo(0.42, 0.52, lado),
        superficieCuerpo(0.46, 0, lado),
        superficieCuerpo(0.42, -0.54, lado),
      ],
      paleta.raya,
      gillRadio
    );
    agregarTubo(
      pez,
      [
        superficieCuerpo(-0.74, 0.02, lado),
        superficieCuerpo(-0.15, 0.02, lado),
        superficieCuerpo(0.38, 0.02, lado),
      ],
      paleta.lomo,
      gillRadio * 0.78
    );
    for (const raya of perfil.rayas) {
      agregarTubo(
        pez,
        [
          superficieCuerpo(raya, 0.66, lado),
          superficieCuerpo(raya, 0, lado),
          superficieCuerpo(raya, -0.62, lado),
        ],
        paleta.raya,
        stripeRadio
      );
    }
  }

  const aletaDorsal = new THREE.Group();
  aletaDorsal.name = "dorsal";
  aletaDorsal.position.set(-medioLargo * 0.02, medioAlto * 0.63, 0);
  aletaDorsal.add(
    extruirAleta(
      [
        [-largo * 0.16, 0],
        [-largo * 0.08, alto * perfil.aletaAlta],
        [largo * 0.01, alto * (perfil.aletaAlta * 0.78)],
        [largo * 0.14, 0],
      ],
      paleta.aleta
    )
  );
  pez.add(aletaDorsal);

  const aletaAnal = extruirAleta(
    [
      [-largo * 0.16, 0],
      [-largo * 0.04, -alto * 0.24],
      [largo * 0.1, 0],
    ],
    paleta.aleta
  );
  aletaAnal.position.set(
    -medioLargo * 0.48,
    -medioAlto * 0.62,
    medioAncho * 0.2
  );
  pez.add(aletaAnal);

  const aletaPelvica = extruirAleta(
    [
      [-largo * 0.07, 0],
      [-largo * 0.03, -alto * 0.17],
      [largo * 0.06, 0],
    ],
    paleta.aleta
  );
  aletaPelvica.position.set(
    medioLargo * 0.02,
    -medioAlto * 0.66,
    medioAncho * 0.25
  );
  pez.add(aletaPelvica);

  const cola = new THREE.Group();
  cola.name = "tail";
  cola.position.set(-medioLargo * 0.92, 0, 0);
  cola.add(
    extruirAleta(
      [
        [0, 0],
        [-largo * 0.25, alto * perfil.colaHorquilla],
        [-largo * 0.16, 0],
        [-largo * 0.25, -alto * perfil.colaHorquilla],
      ],
      paleta.aleta
    )
  );
  pez.add(cola);

  const pectorales: THREE.Object3D[] = [];
  for (const lado of [-1, 1]) {
    const pectoral = new THREE.Group();
    pectoral.name = `pectoral-${lado}`;
    pectoral.position.set(
      medioLargo * 0.05,
      -medioAlto * 0.07,
      lado * medioAncho * 0.82
    );
    pectoral.add(
      extruirAleta(
        [
          [0, 0],
          [-largo * 0.15, -alto * 0.28],
          [largo * 0.07, -alto * 0.19],
        ],
        paleta.aleta
      )
    );
    pez.add(pectoral);
    pectorales.push(pectoral);
  }

  if (perfil.barbas) {
    const barbelRadio = Math.max(0.09, alto * 0.015);
    for (const lado of [-1, 1]) {
      agregarTubo(
        pez,
        [
          [medioLargo * 0.87, -medioAlto * 0.08, lado * medioAncho * 0.48],
          [medioLargo * 1.04, -medioAlto * 0.24, lado * medioAncho * 0.66],
          [medioLargo * 1.24, -medioAlto * 0.27, lado * medioAncho * 0.78],
        ],
        paleta.vientre,
        barbelRadio
      );
    }
  }

  // Invisible hit proxy slightly larger than the visual fish for responsive click/tap raycasting
  const hitProxy = new THREE.Mesh(
    track(
      new THREE.BoxGeometry(
        Math.max(24, largo * 1.45),
        Math.max(18, alto * 2.0),
        14
      )
    ),
    track(
      new THREE.MeshBasicMaterial({
        transparent: true,
        opacity: 0,
        depthWrite: false,
      })
    )
  );
  hitProxy.name = "hit-proxy";
  pez.add(hitProxy);

  const minY = superficie + alto * 0.7 + 8;
  const maxY = Math.max(minY + 4, limiteInferior - alto * 0.7 - 4);
  const pantallaY =
    limiteInferior - (perfil.profundidad / 100) * (limiteInferior - superficie);
  const y = THREE.MathUtils.clamp(pantallaY, minY, maxY);

  pez.position.set(perfil.x - 170, 250 - y, (indice % 4) * 0.14);
  pez.traverse((obj) => {
    obj.renderOrder = 1;
  });

  const baseSpeed = baseCurrentSpeed * perfil.velocidad;

  const entity: FishEntity = {
    group: pez,
    hitProxy,
    geometry: cuerpoGeometria,
    baseVertices: originales,
    vertices,
    tail: cola,
    dorsal: aletaDorsal,
    pectorals: pectorales,
    length: largo,
    height: alto,
    minY,
    maxY,
    preferredScreenY: y,
    baseSpeed,
    vx: baseSpeed,
    vy: 0,
    swimPhase: perfil.fase * Math.PI * 2,
    wanderPhase: perfil.fase * 13.7,
    wanderFreq: 0.45 + (indice % 5) * 0.11,
    meanderAmp: 4.5 + (indice % 4) * 1.6,
    burstTimer: 1.5 + (indice % 6) * 0.9,
    burstBoost: 0,
    pauseTimer: 0,
    clickImpulse: 0,
    clickNudgeY: 0,
    tailEnergy: 1.0,
  };

  hitProxy.userData["fishEntity"] = entity;
  return entity;
}
