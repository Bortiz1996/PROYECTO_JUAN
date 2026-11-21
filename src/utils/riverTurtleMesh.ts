import * as THREE from "three";

export interface TurtleEntity {
  group: THREE.Group;
  hitProxy: THREE.Mesh;
  head: THREE.Object3D;
  flippers: THREE.Object3D[];
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
  glideTimer: number;
  surfaceCooldown: number;
  surfaceTimer: number;
  clickImpulse: number;
  clickNudgeY: number;
  facingDir: 1 | -1;
}

export function buildRiverTurtleEntity(params: {
  indice: number;
  scale: number;
  startX: number;
  profundidadPct: number;
  superficie: number;
  limiteInferior: number;
  noche: boolean;
  track: <T extends { dispose: () => void }>(item: T) => T;
}): TurtleEntity {
  const {
    indice,
    scale,
    startX,
    profundidadPct,
    superficie,
    limiteInferior,
    noche,
    track,
  } = params;

  const length = 21 * scale;
  const height = 9.5 * scale;

  const shellDark = noche ? 0x2c3621 : 0x4a5933;
  const shellMid = noche ? 0x3f4a2b : 0x6d7743;
  const shellRim = noche ? 0x515238 : 0x8d8351;
  const skinColor = noche ? 0x3b482e : 0x5d7244;
  const plastronColor = noche ? 0x6b674b : 0xc7ba84;

  const mat = (color: number, roughness = 0.65) =>
    track(
      new THREE.MeshStandardMaterial({
        color,
        roughness,
        metalness: 0.03,
        side: THREE.DoubleSide,
      })
    );

  const group = new THREE.Group();

  // Domed carapace
  const shellGeom = track(new THREE.SphereGeometry(1, 18, 12));
  const pos = shellGeom.attributes.position as THREE.BufferAttribute;
  const colors = new Float32Array(pos.count * 3);
  const cTop = new THREE.Color(shellDark);
  const cMid = new THREE.Color(shellMid);
  const cRim = new THREE.Color(shellRim);
  const cBot = new THREE.Color(plastronColor);
  const tmp = new THREE.Color();

  for (let i = 0; i < pos.count; i++) {
    const idx = i * 3;
    const nx = pos.array[idx];
    const ny = pos.array[idx + 1];
    const nz = pos.array[idx + 2];

    const yScale = ny >= 0 ? height * 0.42 : height * 0.16;
    pos.array[idx] = nx * (length * 0.36);
    pos.array[idx + 1] = ny * yScale;
    pos.array[idx + 2] = nz * (length * 0.28);

    if (ny > 0.35) {
      tmp.copy(cMid).lerp(cTop, (ny - 0.35) * 1.4);
    } else if (ny >= 0) {
      tmp.copy(cRim).lerp(cMid, ny / 0.35);
    } else {
      tmp.copy(cBot);
    }
    tmp.toArray(colors, idx);
  }
  shellGeom.setAttribute("color", new THREE.BufferAttribute(colors, 3));
  shellGeom.computeVertexNormals();

  const shellMesh = new THREE.Mesh(
    shellGeom,
    track(
      new THREE.MeshStandardMaterial({
        vertexColors: true,
        roughness: 0.52,
        metalness: 0.04,
      })
    )
  );
  group.add(shellMesh);

  // Extending head and neck
  const headGroup = new THREE.Group();
  headGroup.position.set(length * 0.33, height * 0.06, 0);

  const neck = new THREE.Mesh(
    track(new THREE.SphereGeometry(1, 10, 8)),
    mat(skinColor, 0.65)
  );
  neck.scale.set(length * 0.14, height * 0.14, height * 0.14);
  neck.position.set(length * 0.08, 0.2, 0);
  headGroup.add(neck);

  const head = new THREE.Mesh(
    track(new THREE.SphereGeometry(1, 12, 10)),
    mat(skinColor, 0.6)
  );
  head.scale.set(length * 0.12, height * 0.16, height * 0.15);
  head.position.set(length * 0.2, 0.5, 0);
  headGroup.add(head);

  // Cheek stripe & eye
  const eyeMat = mat(0x111a1e, 0.2);
  const eyeGeom = track(new THREE.SphereGeometry(0.45 * scale, 8, 6));
  for (const side of [-1, 1]) {
    const eye = new THREE.Mesh(eyeGeom, eyeMat);
    eye.position.set(length * 0.24, 0.85, side * height * 0.11);
    headGroup.add(eye);
  }
  group.add(headGroup);

  // Short pointed tail
  const tail = new THREE.Mesh(
    track(new THREE.ConeGeometry(0.75 * scale, length * 0.16, 6)),
    mat(skinColor, 0.7)
  );
  tail.rotation.z = Math.PI / 2;
  tail.position.set(-length * 0.4, -height * 0.04, 0);
  group.add(tail);

  // 4 paddling legs/flippers
  const flippers: THREE.Object3D[] = [];
  const legGeom = track(new THREE.SphereGeometry(1, 10, 8));
  const legPositions: Array<[number, number, number, number]> = [
    [length * 0.18, -height * 0.1, length * 0.22, 1.0],
    [length * 0.18, -height * 0.1, -length * 0.22, 1.0],
    [-length * 0.22, -height * 0.12, length * 0.19, 0.82],
    [-length * 0.22, -height * 0.12, -length * 0.19, 0.82],
  ];

  for (const [lx, ly, lz, legScale] of legPositions) {
    const pivot = new THREE.Group();
    pivot.position.set(lx, ly, lz);
    const mesh = new THREE.Mesh(legGeom, mat(skinColor, 0.68));
    mesh.scale.set(
      length * 0.13 * legScale,
      height * 0.09 * legScale,
      height * 0.18 * legScale
    );
    mesh.position.set(-length * 0.04, -height * 0.05, 0);
    pivot.add(mesh);
    group.add(pivot);
    flippers.push(pivot);
  }

  const hitProxy = new THREE.Mesh(
    track(new THREE.BoxGeometry(length * 1.35, height * 1.9, 14)),
    track(
      new THREE.MeshBasicMaterial({
        transparent: true,
        opacity: 0,
        depthWrite: false,
      })
    )
  );
  hitProxy.name = "turtle-hit-proxy";
  group.add(hitProxy);

  const minY = superficie + height * 0.55 + 3;
  const maxY = Math.max(minY + 6, limiteInferior - height * 0.65 - 4);
  const startScreenY = THREE.MathUtils.clamp(
    superficie + (profundidadPct / 100) * Math.max(16, limiteInferior - superficie),
    minY,
    maxY
  );

  const facingDir: 1 | -1 = indice % 2 === 0 ? 1 : -1;
  group.position.set(startX - 170, 250 - startScreenY, 0.3 + indice * 0.25);
  if (facingDir === -1) {
    group.rotation.y = Math.PI;
  }
  group.traverse((o) => {
    o.renderOrder = 1;
  });

  const baseSpeed = 8.2 + (indice % 2) * 1.6;
  const entity: TurtleEntity = {
    group,
    hitProxy,
    head: headGroup,
    flippers,
    length,
    height,
    minY,
    maxY,
    preferredScreenY: startScreenY,
    baseSpeed,
    vx: baseSpeed * facingDir,
    vy: 0,
    swimPhase: indice * 1.9,
    wanderPhase: indice * 3.7,
    glideTimer: 1.5 + indice * 1.3,
    surfaceCooldown: 9 + indice * 6.5,
    surfaceTimer: 0,
    clickImpulse: 0,
    clickNudgeY: 0,
    facingDir,
  };

  hitProxy.userData["animalEntity"] = { kind: "turtle", entity };
  return entity;
}
