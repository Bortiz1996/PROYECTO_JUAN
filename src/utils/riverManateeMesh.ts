import * as THREE from "three";

export interface ManateeEntity {
  group: THREE.Group;
  hitProxy: THREE.Mesh;
  tail: THREE.Object3D;
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
  state: "cruising" | "surfacing" | "breathing" | "diving";
  breathCooldown: number;
  breathTimer: number;
  clickImpulse: number;
  clickNudgeY: number;
  facingDir: 1 | -1;
}

export function buildRiverManateeEntity(params: {
  indice: number;
  scale: number;
  startX: number;
  profundidadPct: number;
  superficie: number;
  limiteInferior: number;
  noche: boolean;
  track: <T extends { dispose: () => void }>(item: T) => T;
}): ManateeEntity {
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

  const length = 54 * scale;
  const height = 19 * scale;
  const halfLen = length * 0.42;
  const halfHeight = height * 0.46;
  const halfWidth = height * 0.42;

  const backColor = noche ? 0x4f5a5d : 0x6f7c80;
  const bodyColor = noche ? 0x5d6768 : 0x859091;
  const bellyColor = noche ? 0x717876 : 0xa5acab;
  const flipperColor = noche ? 0x4a5355 : 0x667274;

  const mat = (color: number, roughness = 0.68) =>
    track(
      new THREE.MeshStandardMaterial({
        color,
        roughness,
        metalness: 0.02,
        side: THREE.DoubleSide,
      })
    );

  const group = new THREE.Group();

  // Plump organic manatee torso
  const bodyGeom = track(new THREE.SphereGeometry(1, 24, 16));
  const pos = bodyGeom.attributes.position as THREE.BufferAttribute;
  const colors = new Float32Array(pos.count * 3);
  const cBack = new THREE.Color(backColor);
  const cMid = new THREE.Color(bodyColor);
  const cBelly = new THREE.Color(bellyColor);
  const tmpColor = new THREE.Color();

  for (let i = 0; i < pos.count; i++) {
    const idx = i * 3;
    const nx = pos.array[idx];
    const ny = pos.array[idx + 1];
    const nz = pos.array[idx + 2];

    // Fuller mid-belly, tapering smoothly toward tail peduncle, rounded front
    const tailTaper = nx < 0 ? 0.42 + 0.58 * Math.sqrt(Math.max(0, 1 + nx)) : 1.0;
    const headRound = nx > 0.4 ? 0.85 + 0.15 * Math.cos((nx - 0.4) * 2.0) : 1.0;
    const profile = tailTaper * headRound;

    pos.array[idx] = nx * halfLen;
    pos.array[idx + 1] = ny * halfHeight * profile;
    pos.array[idx + 2] = nz * halfWidth * profile;

    if (ny > 0.15) {
      tmpColor.copy(cMid).lerp(cBack, Math.min(0.85, (ny - 0.15) * 1.1));
    } else if (ny < -0.15) {
      tmpColor.copy(cMid).lerp(cBelly, Math.min(0.88, (-ny - 0.15) * 1.15));
    } else {
      tmpColor.copy(cMid);
    }
    tmpColor.toArray(colors, idx);
  }
  bodyGeom.setAttribute("color", new THREE.BufferAttribute(colors, 3));
  bodyGeom.computeVertexNormals();

  const bodyMesh = new THREE.Mesh(
    bodyGeom,
    track(
      new THREE.MeshStandardMaterial({
        vertexColors: true,
        roughness: 0.7,
        metalness: 0.02,
      })
    )
  );
  group.add(bodyMesh);

  // Blunt rounded snout / muzzle
  const snout = new THREE.Mesh(
    track(new THREE.SphereGeometry(1, 16, 12)),
    mat(bodyColor, 0.72)
  );
  snout.scale.set(halfLen * 0.34, halfHeight * 0.58, halfWidth * 0.58);
  snout.position.set(halfLen * 0.88, -halfHeight * 0.08, 0);
  group.add(snout);

  // Serene dark eyes
  const eyeMat = mat(0x161f23, 0.25);
  const eyeGeom = track(new THREE.SphereGeometry(0.72 * scale, 10, 8));
  for (const side of [-1, 1]) {
    const eye = new THREE.Mesh(eyeGeom, eyeMat);
    eye.position.set(
      halfLen * 0.85,
      halfHeight * 0.16,
      side * halfWidth * 0.56
    );
    group.add(eye);
  }

  // Broad rounded paddle tail fluke (vertical undulations)
  const paddleShape = new THREE.Shape();
  paddleShape.moveTo(0, 0);
  paddleShape.quadraticCurveTo(-length * 0.18, height * 0.36, -length * 0.3, height * 0.14);
  paddleShape.quadraticCurveTo(-length * 0.34, 0, -length * 0.3, -height * 0.14);
  paddleShape.quadraticCurveTo(-length * 0.18, -height * 0.34, 0, 0);
  paddleShape.closePath();

  const paddleGeom = track(
    new THREE.ExtrudeGeometry(paddleShape, {
      depth: 0.9 * scale,
      bevelEnabled: true,
      bevelSegments: 2,
      bevelSize: 0.22 * scale,
      bevelThickness: 0.22 * scale,
      steps: 1,
    })
  );
  paddleGeom.translate(0, 0, -0.45 * scale);
  // Orient paddle horizontally like a real manatee tail!
  paddleGeom.rotateX(Math.PI / 2);

  const tailGroup = new THREE.Group();
  tailGroup.position.set(-halfLen * 0.88, 0, 0);
  tailGroup.add(new THREE.Mesh(paddleGeom, mat(flipperColor, 0.74)));
  group.add(tailGroup);

  // Rounded pectoral flippers
  const pectorals: THREE.Object3D[] = [];
  const flipperShape = new THREE.Shape();
  flipperShape.moveTo(0, 0);
  flipperShape.quadraticCurveTo(-length * 0.08, -height * 0.42, -length * 0.01, -height * 0.48);
  flipperShape.quadraticCurveTo(length * 0.08, -height * 0.35, length * 0.06, -height * 0.06);
  flipperShape.closePath();

  const flipperGeom = track(
    new THREE.ExtrudeGeometry(flipperShape, {
      depth: 0.45 * scale,
      bevelEnabled: true,
      bevelSegments: 1,
      bevelSize: 0.12 * scale,
      bevelThickness: 0.12 * scale,
      steps: 1,
    })
  );
  flipperGeom.translate(0, 0, -0.22 * scale);

  for (const side of [-1, 1]) {
    const pectoral = new THREE.Group();
    pectoral.position.set(
      halfLen * 0.36,
      -halfHeight * 0.28,
      side * halfWidth * 0.72
    );
    pectoral.add(new THREE.Mesh(flipperGeom, mat(flipperColor, 0.74)));
    group.add(pectoral);
    pectorals.push(pectoral);
  }

  // Hit proxy for smooth tap/click interaction
  const hitProxy = new THREE.Mesh(
    track(new THREE.BoxGeometry(length * 1.15, height * 1.4, 16)),
    track(
      new THREE.MeshBasicMaterial({
        transparent: true,
        opacity: 0,
        depthWrite: false,
      })
    )
  );
  hitProxy.name = "manatee-hit-proxy";
  group.add(hitProxy);

  const minY = superficie + height * 0.65 + 4;
  const maxY = Math.max(minY + 8, limiteInferior - height * 0.65 - 6);
  const startScreenY = THREE.MathUtils.clamp(
    superficie + (profundidadPct / 100) * Math.max(20, limiteInferior - superficie),
    minY,
    maxY
  );

  const facingDir: 1 | -1 = indice % 2 === 0 ? 1 : -1;
  group.position.set(startX - 170, 250 - startScreenY, -1.6 - indice * 0.4);
  if (facingDir === -1) {
    group.rotation.y = Math.PI;
  }
  group.traverse((obj) => {
    obj.renderOrder = 1;
  });

  const baseSpeed = (5.4 + (indice % 2) * 1.1) * (0.92 + scale * 0.08);
  const entity: ManateeEntity = {
    group,
    hitProxy,
    tail: tailGroup,
    pectorals,
    length,
    height,
    minY,
    maxY,
    preferredScreenY: startScreenY,
    baseSpeed,
    vx: baseSpeed * facingDir,
    vy: 0,
    swimPhase: indice * 2.1,
    wanderPhase: indice * 4.3,
    state: "cruising",
    breathCooldown: 7 + indice * 8.5,
    breathTimer: 0,
    clickImpulse: 0,
    clickNudgeY: 0,
    facingDir,
  };

  hitProxy.userData["animalEntity"] = { kind: "manatee", entity };
  return entity;
}
