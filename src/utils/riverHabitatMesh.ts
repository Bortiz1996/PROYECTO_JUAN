import * as THREE from "three";

export interface UnderwaterObstacle {
  x: number;
  y: number;
  radius: number;
}

export interface SwayingPlant {
  group: THREE.Group;
  phase: number;
  speed: number;
  swayAmp: number;
}

export interface RiverHabitatResult {
  obstacles: UnderwaterObstacle[];
  plants: SwayingPlant[];
}

export function buildRiverHabitat(params: {
  scene: THREE.Scene;
  superficie: number;
  limiteInferior: number;
  noche: boolean;
  track: <T extends { dispose: () => void }>(item: T) => T;
}): RiverHabitatResult {
  const { scene, superficie, limiteInferior, noche, track } = params;
  const bottomSceneY = 250 - limiteInferior; // -216
  const waterSpan = Math.max(20, limiteInferior - superficie);
  const obstacles: UnderwaterObstacle[] = [];
  const plants: SwayingPlant[] = [];

  const rockColor1 = noche ? 0x2c3634 : 0x565d53;
  const rockColor2 = noche ? 0x242e2d : 0x474f46;
  const mossColor = noche ? 0x1d3b2b : 0x3b6b47;
  const woodColor = noche ? 0x2f251d : 0x59422e;

  const rockMat1 = track(
    new THREE.MeshStandardMaterial({
      color: rockColor1,
      roughness: 0.88,
      metalness: 0.02,
    })
  );
  const rockMat2 = track(
    new THREE.MeshStandardMaterial({
      color: rockColor2,
      roughness: 0.92,
      metalness: 0.02,
    })
  );
  const mossMat = track(
    new THREE.MeshStandardMaterial({
      color: mossColor,
      roughness: 0.85,
      metalness: 0.0,
    })
  );
  const woodMat = track(
    new THREE.MeshStandardMaterial({
      color: woodColor,
      roughness: 0.86,
      metalness: 0.02,
    })
  );

  // Smooth river boulder cluster (left-center riverbed)
  if (waterSpan > 55) {
    const boulderGroup = new THREE.Group();
    const b1Geom = track(new THREE.DodecahedronGeometry(14, 1));
    const b1 = new THREE.Mesh(b1Geom, rockMat1);
    b1.scale.set(1.35, 0.72, 0.8);
    b1.position.set(-72, bottomSceneY + 5, -2.5);
    b1.rotation.z = 0.14;
    boulderGroup.add(b1);

    const b2Geom = track(new THREE.DodecahedronGeometry(9.5, 1));
    const b2 = new THREE.Mesh(b2Geom, rockMat2);
    b2.scale.set(1.2, 0.7, 0.75);
    b2.position.set(-55, bottomSceneY + 2.5, -1.8);
    b2.rotation.z = -0.22;
    boulderGroup.add(b2);

    const mossCap = new THREE.Mesh(
      track(new THREE.SphereGeometry(7.2, 10, 8)),
      mossMat
    );
    mossCap.scale.set(1.3, 0.25, 0.7);
    mossCap.position.set(-72, bottomSceneY + 12.2, -2.3);
    boulderGroup.add(mossCap);

    boulderGroup.traverse((o) => {
      o.renderOrder = 1;
    });
    scene.add(boulderGroup);
    obstacles.push({ x: -68, y: bottomSceneY + 8, radius: 21 });
  }

  // Submerged driftwood root / fallen branch (right-center riverbed)
  if (waterSpan > 70) {
    const logCurve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(122, bottomSceneY - 4, -2.8),
      new THREE.Vector3(96, bottomSceneY + 14, -1.8),
      new THREE.Vector3(72, bottomSceneY + 26, -1.2),
      new THREE.Vector3(56, bottomSceneY + 32, -0.8),
    ]);
    const logGeom = track(new THREE.TubeGeometry(logCurve, 14, 4.2, 8, false));
    const logMesh = new THREE.Mesh(logGeom, woodMat);
    logMesh.renderOrder = 1;
    scene.add(logMesh);

    const forkCurve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(88, bottomSceneY + 18, -1.6),
      new THREE.Vector3(95, bottomSceneY + 34, -0.9),
      new THREE.Vector3(101, bottomSceneY + 42, -0.6),
    ]);
    const forkGeom = track(
      new THREE.TubeGeometry(forkCurve, 10, 2.2, 7, false)
    );
    const forkMesh = new THREE.Mesh(forkGeom, woodMat);
    forkMesh.renderOrder = 1;
    scene.add(forkMesh);

    obstacles.push({ x: 84, y: bottomSceneY + 22, radius: 22 });
  }

  // Secondary smooth riverbed stones on far right
  if (waterSpan > 45) {
    const stone = new THREE.Mesh(
      track(new THREE.DodecahedronGeometry(8.5, 1)),
      rockMat2
    );
    stone.scale.set(1.4, 0.65, 0.7);
    stone.position.set(138, bottomSceneY + 3, -2.2);
    stone.renderOrder = 1;
    scene.add(stone);
    obstacles.push({ x: 138, y: bottomSceneY + 5, radius: 14 });
  }

  // Gentle swaying submerged aquatic ribbon plants (Vallisneria)
  const leafPalette = noche
    ? [0x1c4a39, 0x255a44, 0x163c2f]
    : [0x2f754d, 0x418c5a, 0x256241];
  const leafMats = leafPalette.map((color) =>
    track(
      new THREE.MeshStandardMaterial({
        color,
        roughness: 0.72,
        metalness: 0.0,
        side: THREE.DoubleSide,
      })
    )
  );

  const clusterPositions = [-138, -124, -22, -8, 22, 118, 152];
  clusterPositions.forEach((cx, idx) => {
    const maxPlantHeight = Math.min(48, Math.max(14, waterSpan * 0.42));
    const blades = 3 + (idx % 3);
    for (let b = 0; b < blades; b++) {
      const h = maxPlantHeight * (0.55 + ((idx + b) % 4) * 0.14);
      if (h < 10) continue;
      const shape = new THREE.Shape();
      shape.moveTo(-1.4, 0);
      shape.quadraticCurveTo(1.8, h * 0.45, 0.4, h);
      shape.quadraticCurveTo(-1.2, h * 0.55, -2.6, 0);
      shape.closePath();

      const geom = track(new THREE.ShapeGeometry(shape, 7));
      const mesh = new THREE.Mesh(geom, leafMats[(idx + b) % leafMats.length]);
      const group = new THREE.Group();
      group.add(mesh);
      group.position.set(
        cx + (b - 1) * 4.2,
        bottomSceneY - 2,
        -3.2 + (b % 3) * 0.8
      );
      group.renderOrder = 1;
      scene.add(group);

      plants.push({
        group,
        phase: (idx * 1.7 + b * 0.9) % (Math.PI * 2),
        speed: 0.65 + (b % 3) * 0.18,
        swayAmp: 0.07 + (b % 2) * 0.03,
      });
    }
  });

  return { obstacles, plants };
}
