import * as THREE from "three";

export type NaturalFoodType = "fruit" | "plant" | "pellet";

export interface FoodPiece {
  id: number;
  type: NaturalFoodType;
  mesh: THREE.Object3D;
  x: number;
  y: number;
  vx: number;
  vy: number;
  inWater: boolean;
  buoyancyTargetOffset: number;
  energy: number;
  maxEnergy: number;
  age: number;
  spinSpeed: number;
  settled: boolean;
}

export interface CrumbParticle {
  mesh: THREE.Mesh;
  vx: number;
  vy: number;
  life: number;
  maxLife: number;
}

export class RiverFoodManager {
  readonly pieces: FoodPiece[] = [];
  private readonly crumbs: CrumbParticle[] = [];
  private nextId = 1;

  private readonly fruitGeom: THREE.BufferGeometry;
  private readonly plantGeom: THREE.BufferGeometry;
  private readonly pelletGeom: THREE.BufferGeometry;
  private readonly crumbGeom: THREE.BufferGeometry;

  private readonly fruitMats: THREE.MeshStandardMaterial[];
  private readonly plantMats: THREE.MeshStandardMaterial[];
  private readonly pelletMat: THREE.MeshStandardMaterial;
  private readonly crumbMat: THREE.MeshBasicMaterial;

  constructor(
    private readonly scene: THREE.Scene,
    track: <T extends { dispose: () => void }>(item: T) => T
  ) {
    // Delicate, small natural food particles proportional to the smaller fish
    this.fruitGeom = track(new THREE.DodecahedronGeometry(1.15, 0));

    const leafShape = new THREE.Shape();
    leafShape.moveTo(-1.7, 0);
    leafShape.quadraticCurveTo(0, 1.05, 1.8, 0);
    leafShape.quadraticCurveTo(0, -0.9, -1.7, 0);
    leafShape.closePath();
    this.plantGeom = track(
      new THREE.ExtrudeGeometry(leafShape, {
        depth: 0.25,
        bevelEnabled: false,
        steps: 1,
      })
    );

    this.pelletGeom = track(new THREE.SphereGeometry(0.85, 7, 5));
    this.crumbGeom = track(new THREE.SphereGeometry(0.42, 5, 4));

    this.fruitMats = [0xf29f3d, 0xe86c4a, 0xf2cb46].map((c) =>
      track(
        new THREE.MeshStandardMaterial({
          color: c,
          roughness: 0.55,
          metalness: 0.02,
        })
      )
    );
    this.plantMats = [0x6bb85c, 0x85ca63, 0x4ea152].map((c) =>
      track(
        new THREE.MeshStandardMaterial({
          color: c,
          roughness: 0.68,
          metalness: 0.0,
          side: THREE.DoubleSide,
        })
      )
    );
    this.pelletMat = track(
      new THREE.MeshStandardMaterial({
        color: 0xd9b864,
        roughness: 0.6,
        metalness: 0.02,
      })
    );
    this.crumbMat = track(
      new THREE.MeshBasicMaterial({
        color: 0xf4e8c4,
        transparent: true,
        opacity: 0.75,
      })
    );
  }

  spawnFoodCluster(params: {
    type: NaturalFoodType;
    screenX: number;
    superficie: number;
  }): void {
    const { type, screenX, superficie } = params;
    const baseSceneX = THREE.MathUtils.clamp(screenX, 34, 312) - 170;
    const surfaceSceneY = 250 - superficie;

    const count = type === "pellet" ? 4 : 3;
    for (let i = 0; i < count; i++) {
      if (this.pieces.length >= 24) {
        const oldest = this.pieces.shift();
        if (oldest) this.scene.remove(oldest.mesh);
      }

      const scatterX = (Math.random() - 0.5) * 16;
      // Start slightly above the water surface so food visibly falls from above into the river
      const dropHeight = 14 + Math.random() * 14 + i * 3.5;
      const startY = Math.min(242, surfaceSceneY + dropHeight);

      let mesh: THREE.Mesh;
      let maxEnergy: number;
      let buoyancyTargetOffset = 0;

      if (type === "fruit") {
        mesh = new THREE.Mesh(
          this.fruitGeom,
          this.fruitMats[i % this.fruitMats.length]
        );
        mesh.scale.set(
          0.78 + Math.random() * 0.35,
          0.7 + Math.random() * 0.32,
          0.78 + Math.random() * 0.3
        );
        maxEnergy = 2.0;
      } else if (type === "plant") {
        mesh = new THREE.Mesh(
          this.plantGeom,
          this.plantMats[i % this.plantMats.length]
        );
        mesh.scale.setScalar(0.78 + Math.random() * 0.35);
        maxEnergy = 2.2;
        buoyancyTargetOffset = -3.5 - Math.random() * 9;
      } else {
        mesh = new THREE.Mesh(this.pelletGeom, this.pelletMat);
        mesh.scale.setScalar(0.8 + Math.random() * 0.3);
        maxEnergy = 1.4;
      }

      const x = THREE.MathUtils.clamp(baseSceneX + scatterX, -158, 158);
      mesh.position.set(x, startY, 0.5 + (i % 3) * 0.2);
      mesh.rotation.set(
        Math.random() * 0.5,
        Math.random() * 0.8,
        Math.random() * Math.PI
      );
      mesh.renderOrder = 2;
      this.scene.add(mesh);

      this.pieces.push({
        id: this.nextId++,
        type,
        mesh,
        x,
        y: startY,
        vx: (Math.random() - 0.5) * 8,
        vy: -12 - Math.random() * 10,
        inWater: false,
        buoyancyTargetOffset,
        energy: maxEnergy,
        maxEnergy,
        age: 0,
        spinSpeed: (Math.random() - 0.5) * 1.1,
        settled: false,
      });
    }
  }

  takeBite(piece: FoodPiece, amount: number): boolean {
    if (piece.energy <= 0 || !piece.inWater) return false;
    piece.energy = Math.max(0, piece.energy - amount);

    piece.vx += (Math.random() - 0.5) * 3.5;
    piece.vy += (Math.random() - 0.3) * 2.5;
    this.spawnCrumbs(piece.x, piece.y, piece.type === "plant" ? 1 : 2);

    const ratio = Math.max(0.28, piece.energy / piece.maxEnergy);
    piece.mesh.scale.multiplyScalar(0.75 + 0.25 * ratio);

    if (piece.energy <= 0) {
      this.removePiece(piece);
      return true;
    }
    return true;
  }

  private spawnCrumbs(x: number, y: number, count: number): void {
    for (let i = 0; i < count; i++) {
      if (this.crumbs.length >= 24) {
        const old = this.crumbs.shift();
        if (old) this.scene.remove(old.mesh);
      }
      const mesh = new THREE.Mesh(this.crumbGeom, this.crumbMat);
      mesh.position.set(x, y, 0.8);
      mesh.renderOrder = 2;
      this.scene.add(mesh);
      this.crumbs.push({
        mesh,
        vx: (Math.random() - 0.3) * 10,
        vy: (Math.random() - 0.5) * 9,
        life: 0,
        maxLife: 0.55 + Math.random() * 0.4,
      });
    }
  }

  private removePiece(target: FoodPiece): void {
    const idx = this.pieces.indexOf(target);
    if (idx !== -1) {
      this.pieces.splice(idx, 1);
    }
    this.scene.remove(target.mesh);
  }

  update(params: {
    delta: number;
    time: number;
    surfaceSceneY: number;
    bottomSceneY: number;
    currentStrength: number;
  }): void {
    const { delta, time, surfaceSceneY, bottomSceneY, currentStrength } =
      params;

    for (let i = this.pieces.length - 1; i >= 0; i--) {
      const p = this.pieces[i];
      p.age += delta;

      if (!p.inWater) {
        // Free-fall through air down to the water surface
        p.vy -= 145 * delta;
        p.vx *= Math.exp(-delta * 1.2);
        p.x += p.vx * delta;
        p.y += p.vy * delta;

        if (p.y <= surfaceSceneY - 1.5) {
          p.inWater = true;
          p.y = surfaceSceneY - 1.5;
          // Water impact cushioning: plant settles gently near surface, fruit/pellets continue sinking softly
          p.vy = p.type === "plant" ? -2.5 : p.type === "fruit" ? -7.5 : -13.0;
          p.vx = currentStrength * 0.55;
        }
      } else {
        const depthFactor = THREE.MathUtils.clamp(
          (p.y - bottomSceneY) / Math.max(20, surfaceSceneY - bottomSceneY),
          0.15,
          1.0
        );
        const streamVx = currentStrength * (0.45 + 0.75 * depthFactor);

        if (p.type === "plant") {
          const targetY = surfaceSceneY + p.buoyancyTargetOffset;
          const bob = Math.sin(time * 1.1 + p.id) * 0.7;
          p.vy = THREE.MathUtils.damp(
            p.vy,
            (targetY + bob - p.y) * 1.9,
            3.2,
            delta
          );
          p.vx = THREE.MathUtils.damp(p.vx, streamVx * 0.9, 2.2, delta);
        } else if (p.type === "fruit") {
          const eddy = Math.sin(time * 0.9 + p.id * 1.3) * 1.8;
          if (!p.settled) {
            p.vy = THREE.MathUtils.damp(p.vy, -4.8 + eddy * 0.4, 2.1, delta);
            p.vx = THREE.MathUtils.damp(p.vx, streamVx * 0.85, 2.0, delta);
          } else {
            p.vx = THREE.MathUtils.damp(p.vx, streamVx * 0.25, 2.5, delta);
            p.vy = 0;
          }
        } else {
          if (!p.settled) {
            p.vy = THREE.MathUtils.damp(p.vy, -10.0, 2.2, delta);
            p.vx = THREE.MathUtils.damp(p.vx, streamVx * 0.75, 2.0, delta);
          } else {
            p.vx = THREE.MathUtils.damp(p.vx, streamVx * 0.15, 2.5, delta);
            p.vy = 0;
          }
        }

        p.x += p.vx * delta;
        p.y += p.vy * delta;

        if (p.y > surfaceSceneY - 1.5) {
          p.y = surfaceSceneY - 1.5;
          if (p.vy > 0) p.vy *= -0.15;
        }
        if (p.y <= bottomSceneY + 2.5) {
          p.y = bottomSceneY + 2.5;
          p.settled = true;
        }
      }

      p.mesh.position.x = p.x;
      p.mesh.position.y = p.y;
      p.mesh.rotation.z += p.spinSpeed * delta;

      if (p.x > 186 || p.age > 28) {
        this.scene.remove(p.mesh);
        this.pieces.splice(i, 1);
      }
    }

    for (let i = this.crumbs.length - 1; i >= 0; i--) {
      const c = this.crumbs[i];
      c.life += delta;
      c.mesh.position.x += (c.vx + currentStrength * 0.4) * delta;
      c.mesh.position.y += c.vy * delta;
      c.vx *= Math.exp(-delta * 2.5);
      c.vy *= Math.exp(-delta * 2.5);
      const t = c.life / c.maxLife;
      c.mesh.scale.setScalar(Math.max(0.05, 1 - t));
      if (c.life >= c.maxLife) {
        this.scene.remove(c.mesh);
        this.crumbs.splice(i, 1);
      }
    }
  }

  disposeAll(): void {
    for (const p of this.pieces) {
      this.scene.remove(p.mesh);
    }
    this.pieces.length = 0;
    for (const c of this.crumbs) {
      this.scene.remove(c.mesh);
    }
    this.crumbs.length = 0;
  }
}
