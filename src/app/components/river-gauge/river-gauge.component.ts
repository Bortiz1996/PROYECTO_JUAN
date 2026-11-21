import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  Input,
  NgZone,
  OnChanges,
  OnDestroy,
  ViewChild,
  inject,
} from "@angular/core";
import * as THREE from "three";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";
import type { ThresholdsInfo } from "../../../types";
import type { AmbienteTipo } from "../../../utils/format";
import { buildRiverFishEntity, type FishEntity } from "../../../utils/riverFishMesh";
import {
  RiverFoodManager,
  type FoodPiece,
  type NaturalFoodType,
} from "../../../utils/riverFoodSystem";
import { buildRiverHabitat } from "../../../utils/riverHabitatMesh";
import {
  buildRiverManateeEntity,
  type ManateeEntity,
} from "../../../utils/riverManateeMesh";
import { buildRiverGaugeData } from "../../../utils/riverScene";
import type { FishSpeciesId } from "../../../utils/riverSpecies";
import {
  buildRiverTurtleEntity,
  type TurtleEntity,
} from "../../../utils/riverTurtleMesh";
import {
  WATER_BACK_FRAGMENT_SHADER,
  WATER_FORE_FRAGMENT_SHADER,
  WATER_VERTEX_SHADER,
  createParticleTexture,
  createWaterNormalMap,
} from "../../../utils/riverWaterShaders";

const SCHOOLING_SPECIES = new Set<FishSpeciesId>([
  "bocachico",
  "arenca",
  "sabalo",
  "mojarra",
  "dorada",
  "pacora",
]);

interface FishBrainState {
  species: FishSpeciesId;
  isSchooling: boolean;
  facingDir: 1 | -1;
  exploreMode: "cruise" | "browse";
  modeTimer: number;
  targetOffsetY: number;
  biteCooldown: number;
  postMealBoost: number;
}

function detectSoftwareWebGL(): boolean {
  try {
    const probe = document.createElement("canvas");
    const gl = probe.getContext("webgl2") || probe.getContext("webgl");
    if (!gl) return true;
    const ext = gl.getExtension("WEBGL_debug_renderer_info");
    const param = ext ? ext.UNMASKED_RENDERER_WEBGL : gl.RENDERER;
    const gpu = String(gl.getParameter(param) || "");
    gl.getExtension("WEBGL_lose_context")?.loseContext();
    return /SwiftShader|llvmpipe|softpipe|Software|Basic Render/i.test(gpu);
  } catch {
    return true;
  }
}

function shortestAngleDelta(target: number, current: number): number {
  return Math.atan2(Math.sin(target - current), Math.cos(target - current));
}

@Component({
  selector: "app-river-gauge",
  template: `
    <div class="gauge-feed-wrap">
      <div class="gauge-panel" #gaugePanel>
        <svg
          #sceneSvg
          class="gauge-scene"
          viewBox="0 0 340 500"
          xmlns="http://www.w3.org/2000/svg"
          role="group"
          [attr.aria-label]="ariaDescription"
        >
          <title>Ecosistema natural del río Magdalena en Calamar</title>
          <g #sceneGroup></g>
        </svg>
        <div
          #canvasMount
          class="fish-canvas-mount"
          aria-hidden="true"
        ></div>
        <svg
          #overlaySvg
          class="gauge-overlay"
          viewBox="0 0 340 500"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        ></svg>
      </div>
      <div class="gauge-feed-controls">
        <button
          type="button"
          class="btn-action btn-feed"
          (click)="handleFeedButtonClick()"
        >
          Alimentar peces
        </button>
      </div>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RiverGaugeComponent
  implements AfterViewInit, OnChanges, OnDestroy
{
  @Input({ required: true }) nivelCm = 0;
  @Input({ required: true }) umbrales!: ThresholdsInfo;
  @Input({ required: true }) estadoPeces: "calm" | "scared" = "calm";
  @Input({ required: true }) ambiente: AmbienteTipo = "despejado";
  @Input({ required: true }) climaTexto = "";
  @Input({ required: true }) noche = false;
  @Input({ required: true }) vientoKmh = 0;
  @Input({ required: true }) estacionCodigo = "29037020";
  @Input({ required: true }) nivelReferenciaCm = 950;
  @Input({ required: true }) nivelMurallaCm = 1000;

  @ViewChild("gaugePanel", { static: true })
  private readonly panelRef!: ElementRef<HTMLDivElement>;
  @ViewChild("sceneSvg", { static: true })
  private readonly svgRef!: ElementRef<SVGSVGElement>;
  @ViewChild("sceneGroup", { static: true })
  private readonly sceneGroupRef!: ElementRef<SVGGElement>;
  @ViewChild("canvasMount", { static: true })
  private readonly canvasMountRef!: ElementRef<HTMLDivElement>;
  @ViewChild("overlaySvg", { static: true })
  private readonly overlaySvgRef!: ElementRef<SVGSVGElement>;

  private readonly ngZone = inject(NgZone);
  private readonly naturalFoodTypes: readonly NaturalFoodType[] = [
    "fruit",
    "plant",
    "pellet",
  ];
  private viewReady = false;
  private gaugeData = buildRiverGaugeData({
    nivelCm: 0,
    umbrales: {
      valores: { amarilla: null, naranja: null, roja: null },
      origen: {
        amarilla: "sin definir",
        naranja: "sin definir",
        roja: "sin definir",
      },
    },
    ambiente: "despejado",
    noche: false,
    vientoKmh: 0,
    estacionCodigo: "29037020",
    nivelReferenciaCm: 950,
    nivelMurallaCm: 1000,
  });

  private cleanupThree: (() => void) | null = null;

  get ariaDescription(): string {
    return `Ecosistema del río en ${this.climaTexto}, ${
      this.noche ? "de noche" : "de día"
    }. Nivel ${this.nivelCm.toFixed(1)} centímetros.`;
  }

  ngAfterViewInit(): void {
    this.viewReady = true;
    this.syncGauge();
  }

  ngOnChanges(): void {
    this.gaugeData = buildRiverGaugeData({
      nivelCm: this.nivelCm,
      umbrales: this.umbrales,
      ambiente: this.ambiente,
      noche: this.noche,
      vientoKmh: this.vientoKmh,
      estacionCodigo: this.estacionCodigo,
      nivelReferenciaCm: this.nivelReferenciaCm,
      nivelMurallaCm: this.nivelMurallaCm,
    });
    if (this.viewReady) {
      this.syncGauge();
    }
  }

  ngOnDestroy(): void {
    this.teardownListeners();
  }

  private pickNaturalFoodType(): NaturalFoodType {
    return this.naturalFoodTypes[
      Math.floor(Math.random() * this.naturalFoodTypes.length)
    ];
  }

  handleFeedButtonClick(): void {
    const randomX = 65 + Math.random() * 210;
    this.dispatchFeedEvent(randomX, this.pickNaturalFoodType());
  }

  private dispatchFeedEvent(
    rawX: number,
    type: NaturalFoodType
  ): void {
    const panel = this.panelRef?.nativeElement;
    if (!panel) return;
    const x = Math.max(36, Math.min(312, rawX));
    panel.dispatchEvent(
      new CustomEvent("river-feed", { detail: { x, type } })
    );
  }

  private teardownListeners(): void {
    if (this.cleanupThree) {
      this.cleanupThree();
      this.cleanupThree = null;
    }
  }

  private syncGauge(): void {
    this.teardownListeners();

    const sceneGroup = this.sceneGroupRef?.nativeElement;
    const overlaySvg = this.overlaySvgRef?.nativeElement;
    if (sceneGroup) {
      sceneGroup.innerHTML = this.gaugeData.sceneHtml;
    }
    if (overlaySvg) {
      overlaySvg.innerHTML = this.gaugeData.overlayHtml;
    }

    this.ngZone.runOutsideAngular(() => {
      this.setupThreeScene();
    });
  }

  private setupThreeScene(): void {
    const panel = this.panelRef?.nativeElement;
    const svg = this.svgRef?.nativeElement;
    const mount = this.canvasMountRef?.nativeElement;
    if (!panel || !svg || !mount) return;

    const superficie = this.gaugeData.ySurface;
    const surfaceSceneY = 250 - superficie;
    const limiteInferior = 466;
    const limiteSuperior = superficie + 12;
    const bottomSceneY = 250 - limiteInferior;
    const perfiles = this.gaugeData.fishProfiles;

    const reducido = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;
    const isSoftwareGl = detectSoftwareWebGL();
    const windFactor = Math.min(Math.max(this.vientoKmh, 0), 45) / 45;
    const isNightVal = this.noche ? 1.0 : 0.0;
    const isStormVal = this.ambiente === "tormenta" ? 1.0 : 0.0;
    const isRainVal =
      this.ambiente === "lluvia" || this.ambiente === "tormenta" ? 1.0 : 0.0;

    const baseFlowSpeed =
      (this.estadoPeces === "scared" ? 18 : 11.5) * (reducido ? 0.25 : 1);

    const escena = new THREE.Scene();
    const camara = new THREE.OrthographicCamera(-170, 170, 250, -250, 0.1, 100);
    camara.position.set(0, 0, 50);
    camara.lookAt(0, 0, 0);

    escena.add(
      new THREE.AmbientLight(
        this.noche ? 0x82b7ca : 0xd8f2f3,
        this.noche ? 0.85 : 1.15
      )
    );
    escena.add(
      new THREE.HemisphereLight(
        this.noche ? 0x5493ae : 0x9be2e7,
        0x072432,
        this.noche ? 0.52 : 0.72
      )
    );
    const solAgua = new THREE.DirectionalLight(
      this.noche ? 0xb4d5eb : 0xfff0c8,
      this.noche ? 1.35 : 2.1
    );
    solAgua.position.set(-75, 130, 110);
    escena.add(solAgua);
    const reflejoAgua = new THREE.PointLight(
      this.noche ? 0x459ab5 : 0x70dfe3,
      this.noche ? 20 : 32,
      420
    );
    reflejoAgua.position.set(85, Math.min(180, surfaceSceneY - 24), 34);
    escena.add(reflejoAgua);

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({
        alpha: true,
        antialias: !isSoftwareGl,
        powerPreference: "high-performance",
      });
    } catch (error) {
      console.error("No se pudo iniciar el ecosistema 3D del río.", error);
      return;
    }

    renderer.domElement.className = "fish-canvas";
    renderer.domElement.setAttribute("aria-hidden", "true");
    mount.replaceChildren(renderer.domElement);
    renderer.setClearColor(0x000000, 0);
    renderer.setPixelRatio(
      isSoftwareGl ? 1 : Math.min(window.devicePixelRatio || 1, 2)
    );
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.06;

    const pmremGenerator = new THREE.PMREMGenerator(renderer);
    const envTarget = pmremGenerator.fromScene(new RoomEnvironment(), 0.04);
    escena.environment = envTarget.texture;
    escena.environmentIntensity = this.noche ? 0.24 : 0.36;
    pmremGenerator.dispose();

    const disposables: Array<{ dispose: () => void }> = [envTarget];
    const track = <T extends { dispose: () => void }>(item: T): T => {
      disposables.push(item);
      return item;
    };

    const waterNormalMap = track(createWaterNormalMap(256));
    waterNormalMap.anisotropy = isSoftwareGl
      ? 1
      : renderer.capabilities.getMaxAnisotropy();
    const waterPlaneGeom = track(new THREE.PlaneGeometry(340, 500, 1, 1));

    const waterBackUniforms = {
      uTime: { value: 0 },
      uSurfaceSceneY: { value: surfaceSceneY },
      uWindFactor: { value: windFactor },
      uNight: { value: isNightVal },
      uStorm: { value: isStormVal },
      uRain: { value: isRainVal },
      uNormalMap: { value: waterNormalMap },
    };
    const waterBackMat = track(
      new THREE.ShaderMaterial({
        uniforms: waterBackUniforms,
        vertexShader: WATER_VERTEX_SHADER,
        fragmentShader: WATER_BACK_FRAGMENT_SHADER,
        transparent: true,
        depthWrite: false,
      })
    );
    const waterBackMesh = new THREE.Mesh(waterPlaneGeom, waterBackMat);
    waterBackMesh.position.set(0, 0, -12);
    waterBackMesh.renderOrder = 0;
    escena.add(waterBackMesh);

    const waterForeUniforms = {
      uTime: { value: 0 },
      uSurfaceSceneY: { value: surfaceSceneY },
      uWindFactor: { value: windFactor },
      uNight: { value: isNightVal },
      uStorm: { value: isStormVal },
      uNormalMap: { value: waterNormalMap },
    };
    const waterForeMat = track(
      new THREE.ShaderMaterial({
        uniforms: waterForeUniforms,
        vertexShader: WATER_VERTEX_SHADER,
        fragmentShader: WATER_FORE_FRAGMENT_SHADER,
        transparent: true,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
      })
    );
    const waterForeMesh = new THREE.Mesh(waterPlaneGeom, waterForeMat);
    waterForeMesh.position.set(0, 0, 5);
    waterForeMesh.renderOrder = 3;
    escena.add(waterForeMesh);

    // Subtle organic suspended river sediment particles
    const waterHeightPx = Math.max(10, limiteInferior - superficie);
    const particleCount = 46;
    const particlePositions = new Float32Array(particleCount * 3);
    const particleMeta = new Float32Array(particleCount * 3);
    for (let i = 0; i < particleCount; i++) {
      const px = -170 + ((i * 61.3) % 340);
      const py =
        250 - (superficie + 8 + ((i * 41.7) % Math.max(8, waterHeightPx - 12)));
      const pz = i % 3 === 0 ? 2.2 : -4.2 + (i % 5);
      particlePositions[i * 3] = px;
      particlePositions[i * 3 + 1] = py;
      particlePositions[i * 3 + 2] = pz;
      particleMeta[i * 3] = 3.2 + (i % 6) * 1.1;
      particleMeta[i * 3 + 1] = (i * 0.83) % (Math.PI * 2);
      particleMeta[i * 3 + 2] = 0.25 + (i % 4) * 0.22;
    }
    const particleGeom = track(new THREE.BufferGeometry());
    const particleAttr = new THREE.BufferAttribute(particlePositions, 3);
    particleGeom.setAttribute("position", particleAttr);
    const particleTex = track(createParticleTexture());
    const particleMat = track(
      new THREE.PointsMaterial({
        size: 2.8,
        map: particleTex,
        transparent: true,
        opacity: this.noche ? 0.16 : 0.24,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
        color: this.noche ? 0x86cde0 : 0xcbf7fc,
      })
    );
    const particlesMesh = new THREE.Points(particleGeom, particleMat);
    particlesMesh.renderOrder = 2;
    escena.add(particlesMesh);

    // Build natural underwater obstacles & swaying aquatic plants
    const habitat = buildRiverHabitat({
      scene: escena,
      superficie,
      limiteInferior,
      noche: this.noche,
      track,
    });

    // Build calm manatees (adult + calf) when water is deep enough
    const manatees: ManateeEntity[] = [];
    if (waterHeightPx > 72) {
      const adult = buildRiverManateeEntity({
        indice: 0,
        scale: 1.0,
        startX: 92,
        profundidadPct: 62,
        superficie,
        limiteInferior,
        noche: this.noche,
        track,
      });
      escena.add(adult.group);
      manatees.push(adult);

      if (waterHeightPx > 105) {
        const subadult = buildRiverManateeEntity({
          indice: 1,
          scale: 0.72,
          startX: 258,
          profundidadPct: 48,
          superficie,
          limiteInferior,
          noche: this.noche,
          track,
        });
        escena.add(subadult.group);
        manatees.push(subadult);
      }
    }

    // Build swimming river turtles
    const turtles: TurtleEntity[] = [];
    if (waterHeightPx > 42) {
      const turtleConfigs: Array<[number, number, number]> = [
        [0.95, 138, 34],
        [0.78, 286, 56],
      ];
      turtleConfigs.forEach(([scale, startX, prof], idx) => {
        const turtle = buildRiverTurtleEntity({
          indice: idx,
          scale,
          startX,
          profundidadPct: prof,
          superficie,
          limiteInferior,
          noche: this.noche,
          track,
        });
        escena.add(turtle.group);
        turtles.push(turtle);
      });
    }

    // Build fish & attach non-cyclic biological steering state
    const fishBrains = new WeakMap<FishEntity, FishBrainState>();
    const peces: FishEntity[] = perfiles.map((perfil, indice) => {
      const entity = buildRiverFishEntity({
        perfil,
        indice,
        superficie,
        limiteInferior,
        baseCurrentSpeed: baseFlowSpeed,
        track,
      });
      const facingDir: 1 | -1 = indice % 5 === 2 ? -1 : 1;
      if (facingDir === -1) {
        entity.vx = -entity.baseSpeed * 0.65;
        entity.group.rotation.y = Math.PI;
      }
      fishBrains.set(entity, {
        species: perfil.especie,
        isSchooling: SCHOOLING_SPECIES.has(perfil.especie),
        facingDir,
        exploreMode: "cruise",
        modeTimer: 2.5 + (indice % 7) * 1.4,
        targetOffsetY: 0,
        biteCooldown: 0,
        postMealBoost: 0,
      });
      escena.add(entity.group);
      return entity;
    });

    const foodManager = new RiverFoodManager(escena, track);

    // Collect all interactive animal hit proxies
    const animalHitProxies: THREE.Object3D[] = [
      ...peces.map((p) => p.hitProxy),
      ...manatees.map((m) => m.hitProxy),
      ...turtles.map((t) => t.hitProxy),
    ];

    if (!isSoftwareGl) {
      renderer.compile(escena, camara);
    }

    const raycaster = new THREE.Raycaster();
    const pointerNdc = new THREE.Vector2();

    const updateNdcFromClient = (clientX: number, clientY: number): boolean => {
      const rect = panel.getBoundingClientRect();
      if (!rect.width || !rect.height) return false;
      pointerNdc.x = ((clientX - rect.left) / rect.width) * 2 - 1;
      pointerNdc.y = -((clientY - rect.top) / rect.height) * 2 + 1;
      return true;
    };

    const puntoSvgLocal = (x: number, y: number) => {
      const ctm = svg.getScreenCTM();
      if (!ctm) return { x: 170, y: Math.min(450, superficie + 40) };
      const punto = svg.createSVGPoint();
      punto.x = x;
      punto.y = y;
      return punto.matrixTransform(ctm.inverse());
    };

    const reactAnimalTap = (hitObject: THREE.Object3D, tapWorldY: number) => {
      const fish = hitObject.userData["fishEntity"] as FishEntity | undefined;
      if (fish) {
        fish.clickImpulse = 1.55;
        const dy = fish.group.position.y - tapWorldY;
        const dodgeDir =
          Math.abs(dy) > 1.2
            ? Math.sign(dy)
            : fish.group.position.y > surfaceSceneY - 40
              ? -1
              : 1;
        fish.clickNudgeY = dodgeDir * (13 + Math.random() * 8);
        fish.pauseTimer = 0;
        return;
      }

      const animal = hitObject.userData["animalEntity"] as
        | { kind: "manatee"; entity: ManateeEntity }
        | { kind: "turtle"; entity: TurtleEntity }
        | undefined;
      if (!animal) return;

      if (animal.kind === "manatee") {
        const m = animal.entity;
        m.clickImpulse = 0.65; // calm gentle dive/glide, never startled abruptly
        m.clickNudgeY = -8 - Math.random() * 6;
        if (m.state === "breathing" || m.state === "surfacing") {
          m.state = "diving";
        }
      } else {
        const t = animal.entity;
        t.clickImpulse = 1.15;
        const dy = t.group.position.y - tapWorldY;
        t.clickNudgeY = (Math.abs(dy) > 1 ? Math.sign(dy) : -1) * 11;
      }
    };

    const onPointerDown = (evento: PointerEvent) => {
      if (updateNdcFromClient(evento.clientX, evento.clientY)) {
        raycaster.setFromCamera(pointerNdc, camara);
        const hits = raycaster.intersectObjects(animalHitProxies, false);
        if (hits.length > 0) {
          evento.preventDefault();
          reactAnimalTap(hits[0].object, hits[0].point.y);
          return;
        }
      }

      const punto = puntoSvgLocal(evento.clientX, evento.clientY);
      if (punto.y > superficie - 24) {
        evento.preventDefault();
        foodManager.spawnFoodCluster({
          type: this.pickNaturalFoodType(),
          screenX: punto.x,
          superficie,
        });
      }
    };

    let lastHoverCheck = 0;
    const onPointerMove = (evento: PointerEvent) => {
      const now = performance.now();
      if (now - lastHoverCheck < 45) return;
      lastHoverCheck = now;
      if (!updateNdcFromClient(evento.clientX, evento.clientY)) return;
      raycaster.setFromCamera(pointerNdc, camara);
      const hits = raycaster.intersectObjects(animalHitProxies, false);
      panel.style.cursor = hits.length > 0 ? "pointer" : "default";
    };

    const onPointerLeave = () => {
      panel.style.cursor = "default";
    };

    const onRiverFeed = (evento: Event) => {
      const custom = evento as CustomEvent<{
        x: number;
        type: NaturalFoodType;
      }>;
      foodManager.spawnFoodCluster({
        type: custom.detail.type,
        screenX: custom.detail.x,
        superficie,
      });
    };

    panel.addEventListener("pointerdown", onPointerDown);
    panel.addEventListener("pointermove", onPointerMove);
    panel.addEventListener("pointerleave", onPointerLeave);
    panel.addEventListener("river-feed", onRiverFeed);

    function redimensionar() {
      if (!panel) return;
      const caja = panel.getBoundingClientRect();
      if (!caja.width || !caja.height) return;
      renderer.setPixelRatio(
        isSoftwareGl ? 1 : Math.min(window.devicePixelRatio || 1, 2)
      );
      renderer.setSize(caja.width, caja.height, false);
    }

    let resizeObserver: ResizeObserver | null = null;
    if (typeof ResizeObserver !== "undefined") {
      resizeObserver = new ResizeObserver(redimensionar);
      resizeObserver.observe(panel);
    } else {
      window.addEventListener("resize", redimensionar);
    }
    redimensionar();

    let tiempoPrevio = performance.now();
    let tiempo = 0;
    let frameId = 0;
    let disposed = false;
    const nightMode = this.noche;
    const intensidad = reducido ? 0.25 : 1;

    function afterDraw(cb: () => void) {
      const gl = renderer.getContext() as WebGL2RenderingContext;
      if (typeof gl.fenceSync === "function") {
        const sync = gl.fenceSync(gl.SYNC_GPU_COMMANDS_COMPLETE, 0);
        gl.flush();
        const poll = () => {
          if (disposed) {
            if (sync) gl.deleteSync(sync);
            return;
          }
          const state = sync && gl.getSyncParameter(sync, gl.SYNC_STATUS);
          if (state === gl.UNSIGNALED) {
            frameId = window.setTimeout(poll, 5);
          } else {
            if (sync) gl.deleteSync(sync);
            frameId = window.setTimeout(cb, 80);
          }
        };
        frameId = window.setTimeout(poll, 5);
      } else {
        frameId = window.setTimeout(cb, 80);
      }
    }

    function computeObstacleAvoidance(
      x: number,
      y: number,
      entityRadius: number
    ): { ax: number; ay: number } {
      let ax = 0;
      let ay = 0;
      for (const obs of habitat.obstacles) {
        const dx = x - obs.x;
        const dy = y - obs.y;
        const safeDist = obs.radius + entityRadius + 8;
        const distSq = dx * dx + dy * dy;
        if (distSq < safeDist * safeDist && distSq > 0.01) {
          const dist = Math.sqrt(distSq);
          const strength = ((safeDist - dist) / safeDist) * 28;
          ax += (dx / dist) * strength * 0.45;
          // Prefer gliding cleanly upward over riverbed rocks/logs
          ay += ((dy / dist) * 0.7 + 0.35) * strength;
        }
      }
      return { ax, ay };
    }

    function findBestFood(
      x: number,
      y: number,
      maxRange: number,
      preferredType?: NaturalFoodType
    ): FoodPiece | null {
      let best: FoodPiece | null = null;
      let bestScore = Infinity;
      for (const piece of foodManager.pieces) {
        if (!piece.inWater || piece.energy <= 0) continue;
        const dx = piece.x - x;
        const dy = piece.y - y;
        const dist = Math.hypot(dx, dy);
        if (dist > maxRange) continue;
        const prefBonus = preferredType && piece.type === preferredType ? 0.65 : 1.0;
        const score = dist * prefBonus;
        if (score < bestScore) {
          bestScore = score;
          best = piece;
        }
      }
      return best;
    }

    function animar(marca: number) {
      if (disposed) return;
      const delta = Math.min((marca - tiempoPrevio) / 1000, 0.04);
      tiempoPrevio = marca;
      tiempo += delta;

      const shaderTime = reducido ? 0 : tiempo;
      waterBackUniforms.uTime.value = shaderTime;
      waterForeUniforms.uTime.value = shaderTime;
      reflejoAgua.intensity =
        (nightMode ? 20 : 32) +
        Math.sin(shaderTime * 0.8) * (nightMode ? 1.5 : 3.0);

      // Gentle underwater plant sway in current
      if (!reducido) {
        for (const pl of habitat.plants) {
          pl.group.rotation.z =
            -0.08 +
            Math.sin(tiempo * pl.speed + pl.phase) * pl.swayAmp +
            Math.cos(tiempo * (pl.speed * 0.53) + pl.phase) * (pl.swayAmp * 0.4);
        }

        // Suspended river micro-particles drifting gently downstream
        const pArr = particleAttr.array as Float32Array;
        const maxParticleY = surfaceSceneY - 4;
        const minParticleY = bottomSceneY + 2;
        for (let i = 0; i < particleCount; i++) {
          const i3 = i * 3;
          const speed = particleMeta[i3];
          const phase = particleMeta[i3 + 1];
          const bob = particleMeta[i3 + 2];
          let px = pArr[i3] + speed * delta * (0.7 + windFactor * 0.4);
          if (px > 174) px -= 348;
          let py =
            pArr[i3 + 1] +
            Math.sin(tiempo * 0.8 + phase) * bob * delta;
          if (py > maxParticleY) py = minParticleY + 4;
          pArr[i3] = px;
          pArr[i3 + 1] = py;
        }
        particleAttr.needsUpdate = true;
      }

      // Update food physics (floating plants, sinking fruit & pellets)
      foodManager.update({
        delta,
        time: tiempo,
        surfaceSceneY,
        bottomSceneY,
        currentStrength: baseFlowSpeed * 0.55,
      });

      // 1. Update Manatees (calm underwater cruise, breathing at surface, plant foraging)
      for (const m of manatees) {
        m.clickImpulse *= Math.exp(-delta * 1.4);
        m.clickNudgeY *= Math.exp(-delta * 1.6);

        let desiredVx = m.baseSpeed * m.facingDir * (1 + m.clickImpulse);
        let desiredVy = 0;

        const foodTarget =
          m.state === "cruising"
            ? findBestFood(m.group.position.x, m.group.position.y, 175, "plant")
            : null;

        if (foodTarget && m.clickImpulse < 0.1) {
          const dx = foodTarget.x - m.group.position.x;
          const dy = foodTarget.y - m.group.position.y;
          const dist = Math.hypot(dx, dy);
          if (dist > m.length * 0.38) {
            const ang = Math.atan2(dy, dx);
            const forageSpeed = m.baseSpeed * 1.35;
            desiredVx = Math.cos(ang) * forageSpeed;
            desiredVy = Math.sin(ang) * forageSpeed;
            m.facingDir = dx >= 0 ? 1 : -1;
          } else {
            foodManager.takeBite(foodTarget, 0.95 * delta * 6.5);
            desiredVx = m.facingDir * m.baseSpeed * 0.3;
          }
        } else {
          // Natural breathing state machine
          if (m.state === "cruising") {
            m.breathCooldown -= delta;
            const driftY =
              Math.sin(tiempo * 0.28 + m.wanderPhase) * 6.0 +
              Math.cos(tiempo * 0.14 + m.wanderPhase * 1.6) * 3.5;
            const targetSceneY = THREE.MathUtils.clamp(
              250 - (m.preferredScreenY + driftY) + m.clickNudgeY,
              250 - m.maxY,
              250 - m.minY
            );
            desiredVy = (targetSceneY - m.group.position.y) * 0.55;

            if (m.breathCooldown <= 0 && Math.abs(m.group.position.x) < 120) {
              m.state = "surfacing";
            }
          } else if (m.state === "surfacing") {
            const breatheSceneY = surfaceSceneY - m.height * 0.34;
            desiredVx = m.baseSpeed * 0.68 * m.facingDir;
            desiredVy = (breatheSceneY - m.group.position.y) * 0.85;
            if (Math.abs(m.group.position.y - breatheSceneY) < 3.5) {
              m.state = "breathing";
              m.breathTimer = 2.0 + Math.random() * 1.1;
            }
          } else if (m.state === "breathing") {
            m.breathTimer -= delta;
            const breatheSceneY = surfaceSceneY - m.height * 0.32;
            desiredVx = m.baseSpeed * 0.35 * m.facingDir;
            desiredVy = (breatheSceneY - m.group.position.y) * 1.1;
            if (m.breathTimer <= 0) {
              m.state = "diving";
            }
          } else {
            // Diving smoothly back to mid-deep water
            const diveSceneY = 250 - m.preferredScreenY;
            desiredVx = m.baseSpeed * 0.85 * m.facingDir;
            desiredVy = (diveSceneY - m.group.position.y) * 0.65;
            if (Math.abs(m.group.position.y - diveSceneY) < 6) {
              m.state = "cruising";
              m.breathCooldown = 12 + Math.random() * 10;
            }
          }
        }

        const obs = computeObstacleAvoidance(
          m.group.position.x,
          m.group.position.y,
          m.height * 0.55
        );
        desiredVx += obs.ax * 0.35;
        desiredVy += obs.ay * 0.4;

        m.vx = THREE.MathUtils.damp(m.vx, desiredVx, 1.4, delta);
        m.vy = THREE.MathUtils.damp(m.vy, desiredVy, 1.5, delta);
        m.group.position.x += m.vx * delta;
        m.group.position.y += m.vy * delta;

        // Soft upper/lower water bounds
        const maxManateeSceneY = surfaceSceneY - m.height * 0.28;
        const minManateeSceneY = bottomSceneY + m.height * 0.52;
        m.group.position.y = THREE.MathUtils.clamp(
          m.group.position.y,
          minManateeSceneY,
          Math.max(minManateeSceneY + 2, maxManateeSceneY)
        );

        // Slow graceful paddle tail & flipper animation
        const moveRatio = Math.hypot(m.vx, m.vy) / Math.max(3, m.baseSpeed);
        m.swimPhase += delta * (1.2 + moveRatio * 0.9) * intensidad;
        m.tail.rotation.z = Math.sin(m.swimPhase) * 0.24 * intensidad;
        m.pectorals.forEach((p, idx) => {
          p.rotation.z = Math.sin(m.swimPhase * 0.8 + idx * 0.6) * 0.16 * intensidad;
          p.rotation.x = Math.cos(m.swimPhase * 0.6 + idx * Math.PI) * 0.1 * intensidad;
        });

        const targetYaw = m.vx < -0.8 ? Math.PI : 0;
        const rawPitch = Math.atan2(m.vy, Math.max(3, Math.abs(m.vx))) * 0.52;
        const targetPitch = THREE.MathUtils.clamp(rawPitch, -0.34, 0.34);
        m.group.rotation.y +=
          shortestAngleDelta(targetYaw, m.group.rotation.y) *
          Math.min(1, delta * 1.8);
        m.group.rotation.z +=
          shortestAngleDelta(targetPitch, m.group.rotation.z) *
          Math.min(1, delta * 1.8);

        // Seamless off-screen re-entry (occasionally swaps direction naturally)
        const margin = m.length * 1.35;
        if (m.group.position.x > 170 + margin) {
          m.facingDir = Math.random() < 0.35 ? -1 : 1;
          m.group.position.x =
            m.facingDir === 1 ? -170 - margin : 170 + margin;
          const nextScreenY =
            m.minY + Math.random() * Math.max(4, m.maxY - m.minY);
          m.preferredScreenY = nextScreenY;
          m.group.position.y = 250 - nextScreenY;
          m.vx = m.baseSpeed * m.facingDir;
          m.vy = 0;
          m.state = "cruising";
          m.breathCooldown = 8 + Math.random() * 9;
        } else if (m.group.position.x < -170 - margin) {
          m.facingDir = Math.random() < 0.7 ? 1 : -1;
          m.group.position.x =
            m.facingDir === 1 ? -170 - margin : 170 + margin;
          const nextScreenY =
            m.minY + Math.random() * Math.max(4, m.maxY - m.minY);
          m.preferredScreenY = nextScreenY;
          m.group.position.y = 250 - nextScreenY;
          m.vx = m.baseSpeed * m.facingDir;
          m.vy = 0;
          m.state = "cruising";
          m.breathCooldown = 8 + Math.random() * 9;
        }
      }

      // 2. Update River Turtles (alternating paddles, occasional surface peeking, food foraging)
      for (const t of turtles) {
        t.clickImpulse *= Math.exp(-delta * 1.8);
        t.clickNudgeY *= Math.exp(-delta * 2.0);
        t.glideTimer -= delta;

        let desiredVx = t.baseSpeed * t.facingDir * (1 + t.clickImpulse);
        let desiredVy = 0;

        const foodTarget = findBestFood(
          t.group.position.x,
          t.group.position.y,
          145,
          "fruit"
        );

        if (foodTarget && t.clickImpulse < 0.15) {
          const dx = foodTarget.x - t.group.position.x;
          const dy = foodTarget.y - t.group.position.y;
          const dist = Math.hypot(dx, dy);
          if (dist > t.length * 0.45) {
            const ang = Math.atan2(dy, dx);
            const speed = t.baseSpeed * 1.5;
            desiredVx = Math.cos(ang) * speed;
            desiredVy = Math.sin(ang) * speed;
            t.facingDir = dx >= 0 ? 1 : -1;
          } else {
            foodManager.takeBite(foodTarget, 0.7 * delta * 6.5);
            desiredVx = t.facingDir * t.baseSpeed * 0.35;
          }
        } else {
          t.surfaceCooldown -= delta;
          if (t.surfaceTimer > 0) {
            t.surfaceTimer -= delta;
            const peekY = surfaceSceneY - t.height * 0.35;
            desiredVx = t.baseSpeed * 0.45 * t.facingDir;
            desiredVy = (peekY - t.group.position.y) * 1.1;
          } else {
            if (t.surfaceCooldown <= 0 && Math.abs(t.group.position.x) < 125) {
              t.surfaceTimer = 2.4 + Math.random() * 1.2;
              t.surfaceCooldown = 11 + Math.random() * 9;
            }
            const wanderY =
              Math.sin(tiempo * 0.42 + t.wanderPhase) * 8 +
              Math.cos(tiempo * 0.21 + t.wanderPhase * 1.4) * 5;
            const targetSceneY = THREE.MathUtils.clamp(
              250 - (t.preferredScreenY + wanderY) + t.clickNudgeY,
              250 - t.maxY,
              250 - t.minY
            );
            desiredVy = (targetSceneY - t.group.position.y) * 0.9;
          }
        }

        const obs = computeObstacleAvoidance(
          t.group.position.x,
          t.group.position.y,
          t.height * 0.65
        );
        desiredVx += obs.ax * 0.45;
        desiredVy += obs.ay * 0.5;

        t.vx = THREE.MathUtils.damp(t.vx, desiredVx, 2.2, delta);
        t.vy = THREE.MathUtils.damp(t.vy, desiredVy, 2.2, delta);
        t.group.position.x += t.vx * delta;
        t.group.position.y += t.vy * delta;

        const maxTurtleSceneY = surfaceSceneY - t.height * 0.32;
        const minTurtleSceneY = bottomSceneY + t.height * 0.6;
        t.group.position.y = THREE.MathUtils.clamp(
          t.group.position.y,
          minTurtleSceneY,
          Math.max(minTurtleSceneY + 2, maxTurtleSceneY)
        );

        // Natural alternating flipper strokes
        const speedNorm = Math.hypot(t.vx, t.vy) / Math.max(4, t.baseSpeed);
        t.swimPhase += delta * (2.2 + speedNorm * 1.8) * intensidad;
        t.flippers.forEach((f, idx) => {
          const isFront = idx < 2;
          const phaseOffset = (idx % 2) * Math.PI + (isFront ? 0 : 0.7);
          f.rotation.y =
            Math.sin(t.swimPhase + phaseOffset) *
            (isFront ? 0.55 : 0.32) *
            intensidad;
          f.rotation.z =
            Math.cos(t.swimPhase + phaseOffset) *
            (isFront ? 0.24 : 0.14) *
            intensidad;
        });
        t.head.rotation.z =
          (t.surfaceTimer > 0 ? 0.18 : 0.04) +
          Math.sin(tiempo * 1.3 + t.wanderPhase) * 0.05;

        const targetYaw = t.vx < -1.2 ? Math.PI : 0;
        const targetPitch = THREE.MathUtils.clamp(
          Math.atan2(t.vy, Math.max(4, Math.abs(t.vx))) * 0.6,
          -0.38,
          0.38
        );
        t.group.rotation.y +=
          shortestAngleDelta(targetYaw, t.group.rotation.y) *
          Math.min(1, delta * 2.5);
        t.group.rotation.z +=
          shortestAngleDelta(targetPitch, t.group.rotation.z) *
          Math.min(1, delta * 2.5);

        const margin = t.length * 1.4;
        if (t.group.position.x > 170 + margin || t.group.position.x < -170 - margin) {
          t.facingDir = t.group.position.x > 0 ? (Math.random() < 0.4 ? -1 : 1) : (Math.random() < 0.75 ? 1 : -1);
          t.group.position.x =
            t.facingDir === 1 ? -170 - margin : 170 + margin;
          const nextScreenY =
            t.minY + Math.random() * Math.max(4, t.maxY - t.minY);
          t.preferredScreenY = nextScreenY;
          t.group.position.y = 250 - nextScreenY;
          t.vx = t.baseSpeed * t.facingDir;
          t.vy = 0;
        }
      }

      // 3. Update Fish (organic schooling, obstacle & manatee avoidance, food competition, non-cyclic wandering)
      for (const pez of peces) {
        const brain = fishBrains.get(pez)!;
        brain.biteCooldown = Math.max(0, brain.biteCooldown - delta);
        brain.postMealBoost *= Math.exp(-delta * 1.4);

        pez.burstTimer -= delta;
        if (pez.pauseTimer > 0) {
          pez.pauseTimer = Math.max(0, pez.pauseTimer - delta);
        } else if (pez.burstTimer <= 0) {
          if (Math.random() < 0.24) {
            pez.pauseTimer = 0.55 + Math.random() * 0.75;
            pez.burstTimer = 2.2 + Math.random() * 2.6;
          } else {
            pez.burstBoost = 0.28 + Math.random() * 0.45;
            pez.burstTimer = 2.0 + Math.random() * 2.6;
          }
        }

        // Occasional natural change of exploration direction/depth (never mechanical loop)
        brain.modeTimer -= delta;
        if (brain.modeTimer <= 0) {
          brain.modeTimer = 3.5 + Math.random() * 4.5;
          brain.targetOffsetY = (Math.random() - 0.5) * 18;
          // Solitary or curious fish occasionally turn upstream briefly if well inside view
          if (
            !brain.isSchooling &&
            Math.abs(pez.group.position.x) < 110 &&
            Math.random() < 0.32
          ) {
            brain.facingDir = brain.facingDir === 1 ? -1 : 1;
          } else if (brain.facingDir === -1 && Math.random() < 0.65) {
            brain.facingDir = 1;
          }
        }

        pez.burstBoost *= Math.exp(-delta * 1.45);
        pez.clickImpulse *= Math.exp(-delta * 2.1);
        pez.clickNudgeY *= Math.exp(-delta * 2.4);

        // Check for nearby food to detect, compete for, and eat
        const food = findBestFood(
          pez.group.position.x,
          pez.group.position.y,
          135
        );

        let desiredVx = 0;
        let desiredVy = 0;
        let isForaging = false;

        if (food && pez.clickImpulse < 0.15) {
          const dx = food.x - pez.group.position.x;
          const dy = food.y - pez.group.position.y;
          const dist = Math.hypot(dx, dy);
          isForaging = true;

          if (dist > pez.length * 0.42) {
            const ang = Math.atan2(dy, dx);
            const chaseSpeed =
              pez.baseSpeed * (1.55 + pez.burstBoost * 0.4);
            desiredVx = Math.cos(ang) * chaseSpeed;
            desiredVy = Math.sin(ang) * chaseSpeed;
            brain.facingDir = dx >= 0 ? 1 : -1;
          } else {
            // Take a quick natural bite and dart slightly away (competition!)
            if (brain.biteCooldown <= 0) {
              foodManager.takeBite(food, 0.58);
              brain.biteCooldown = 0.42 + Math.random() * 0.25;
              brain.postMealBoost = 0.65;
              pez.clickNudgeY = (Math.random() - 0.5) * 10;
            }
            desiredVx = brain.facingDir * pez.baseSpeed * 0.5;
            desiredVy = (Math.random() - 0.5) * 6;
          }
        }

        if (!isForaging) {
          const driftFactor = pez.pauseTimer > 0 ? 0.42 : 1.0;
          const dirSpeed =
            brain.facingDir === 1
              ? pez.baseSpeed
              : pez.baseSpeed * 0.65; // slightly slower when swimming against gentle current
          desiredVx =
            brain.facingDir *
            dirSpeed *
            (driftFactor +
              pez.burstBoost * 0.6 +
              pez.clickImpulse * 1.15 +
              brain.postMealBoost * 0.45);

          const meanderY =
            Math.sin(tiempo * pez.wanderFreq + pez.wanderPhase) *
              pez.meanderAmp +
            Math.cos(tiempo * pez.wanderFreq * 0.43 + pez.wanderPhase * 1.7) *
              (pez.meanderAmp * 0.55);

          const desiredScreenY = THREE.MathUtils.clamp(
            pez.preferredScreenY + brain.targetOffsetY + meanderY,
            pez.minY,
            pez.maxY
          );
          const minSceneY = 250 - pez.maxY;
          const maxSceneY = 250 - pez.minY;
          const targetSceneY = THREE.MathUtils.clamp(
            250 - desiredScreenY + pez.clickNudgeY,
            minSceneY,
            maxSceneY
          );
          desiredVy = (targetSceneY - pez.group.position.y) * 1.3;

          // Subtle schooling cohesion + separation among nearby peers
          if (brain.isSchooling) {
            let cohX = 0;
            let cohY = 0;
            let count = 0;
            for (const other of peces) {
              if (other === pez) continue;
              const dx = other.group.position.x - pez.group.position.x;
              const dy = other.group.position.y - pez.group.position.y;
              const d2 = dx * dx + dy * dy;
              if (d2 < 32 * 32 && d2 > 0.1) {
                // Personal space separation
                const d = Math.sqrt(d2);
                desiredVx -= (dx / d) * 4.5;
                desiredVy -= (dy / d) * 4.5;
              } else if (
                d2 < 85 * 85 &&
                fishBrains.get(other)?.species === brain.species
              ) {
                cohX += other.group.position.x;
                cohY += other.group.position.y;
                count++;
              }
            }
            if (count > 0) {
              desiredVx += ((cohX / count - pez.group.position.x) * 0.12);
              desiredVy += ((cohY / count - pez.group.position.y) * 0.16);
            }
          }
        }

        // Obstacle avoidance (submerged rocks & driftwood logs)
        const obs = computeObstacleAvoidance(
          pez.group.position.x,
          pez.group.position.y,
          pez.height * 0.65
        );
        desiredVx += obs.ax;
        desiredVy += obs.ay;

        // Gentle parting around passing manatees
        for (const m of manatees) {
          const dx = pez.group.position.x - m.group.position.x;
          const dy = pez.group.position.y - m.group.position.y;
          const safeR = m.length * 0.45 + pez.height;
          const d2 = dx * dx + dy * dy;
          if (d2 < safeR * safeR && d2 > 0.1) {
            const d = Math.sqrt(d2);
            const push = ((safeR - d) / safeR) * 18;
            desiredVx += (dx / d) * push * 0.4;
            desiredVy += (dy / d) * push;
          }
        }

        pez.vx = THREE.MathUtils.damp(pez.vx, desiredVx, 3.0, delta);
        pez.vy = THREE.MathUtils.damp(pez.vy, desiredVy, 2.7, delta);
        pez.group.position.x += pez.vx * delta;
        pez.group.position.y += pez.vy * delta;

        // Soft vertical river bounds
        const softMinSceneY = 250 - (limiteInferior - pez.height * 0.6);
        const softMaxSceneY = 250 - (limiteSuperior + pez.height * 0.5);
        if (pez.group.position.y < softMinSceneY) {
          pez.group.position.y = THREE.MathUtils.damp(
            pez.group.position.y,
            softMinSceneY,
            5.5,
            delta
          );
          if (pez.vy < 0) pez.vy *= 0.55;
        } else if (pez.group.position.y > softMaxSceneY) {
          pez.group.position.y = THREE.MathUtils.damp(
            pez.group.position.y,
            softMaxSceneY,
            5.5,
            delta
          );
          if (pez.vy > 0) pez.vy *= 0.55;
        }

        // Propulsion-coupled tail & body undulation
        const speedNorm =
          Math.hypot(pez.vx, pez.vy) / Math.max(7, pez.baseSpeed);
        const targetEnergy = THREE.MathUtils.clamp(
          speedNorm *
            (0.82 +
              pez.burstBoost * 0.45 +
              pez.clickImpulse * 0.8 +
              brain.postMealBoost * 0.4),
          0.4,
          2.5
        );
        pez.tailEnergy = THREE.MathUtils.damp(
          pez.tailEnergy,
          targetEnergy,
          4.5,
          delta
        );
        pez.swimPhase += delta * (2.5 + pez.tailEnergy * 1.85) * intensidad;

        const bodyAmp =
          (reducido ? 0.2 : 0.9) *
          Math.min(1.5, 0.72 + pez.tailEnergy * 0.34);
        const posiciones = pez.vertices;
        const halfLen = pez.length * 0.36;
        for (let i = 0; i < posiciones.count; i++) {
          const offset = i * 3;
          const x = pez.baseVertices[offset];
          const dorsalidad = Math.max(0, -x / halfLen);
          const lateralWave =
            Math.sin(pez.swimPhase - x * 0.28) *
            pez.height *
            0.08 *
            bodyAmp *
            dorsalidad ** 1.4;
          const verticalFlex =
            Math.cos(pez.swimPhase * 0.55 - x * 0.22) *
            pez.height *
            0.022 *
            bodyAmp *
            dorsalidad ** 1.5;
          posiciones.array[offset] = pez.baseVertices[offset];
          posiciones.array[offset + 1] =
            pez.baseVertices[offset + 1] + verticalFlex;
          posiciones.array[offset + 2] =
            pez.baseVertices[offset + 2] + lateralWave;
        }
        posiciones.needsUpdate = true;
        if (!reducido) {
          pez.geometry.computeVertexNormals();
        }

        pez.tail.rotation.y = Math.sin(pez.swimPhase * 1.2) * 0.42 * bodyAmp;
        pez.tail.rotation.z = Math.sin(pez.swimPhase * 0.55) * 0.11 * bodyAmp;
        pez.dorsal.rotation.z = Math.sin(pez.swimPhase * 0.7) * 0.08 * bodyAmp;
        pez.pectorals.forEach((aleta, index) => {
          aleta.rotation.x =
            Math.sin(pez.swimPhase * 1.1 + index * Math.PI) * 0.22 * bodyAmp;
          aleta.rotation.z =
            Math.sin(pez.swimPhase * 0.9 + index * Math.PI) * 0.08 * bodyAmp;
        });

        const targetYaw = pez.vx < -1.8 ? Math.PI : 0;
        const speedMag = Math.max(6, Math.abs(pez.vx));
        const targetPitch = THREE.MathUtils.clamp(
          Math.atan2(pez.vy, speedMag) * 0.68,
          -0.42,
          0.42
        );
        const targetRoll = THREE.MathUtils.clamp(pez.vy * 0.007, -0.14, 0.14);

        const turnRate = isForaging ? 4.8 : 3.0;
        pez.group.rotation.y +=
          shortestAngleDelta(targetYaw, pez.group.rotation.y) *
          Math.min(1, delta * turnRate);
        pez.group.rotation.z +=
          shortestAngleDelta(targetPitch, pez.group.rotation.z) *
          Math.min(1, delta * turnRate);
        pez.group.rotation.x +=
          shortestAngleDelta(targetRoll, pez.group.rotation.x) *
          Math.min(1, delta * 2.5);

        // Seamless off-screen exit & fresh non-cyclic re-entry
        const exitMargin = 175 + pez.length * 1.2;
        if (pez.group.position.x > exitMargin || pez.group.position.x < -exitMargin) {
          const enterFromLeft = pez.group.position.x > 0 ? Math.random() < 0.8 : Math.random() < 0.75;
          brain.facingDir = enterFromLeft ? 1 : -1;
          pez.group.position.x = enterFromLeft
            ? -175 - pez.length * (1.2 + Math.random() * 2.2)
            : 175 + pez.length * (1.2 + Math.random() * 2.2);
          const nextScreenY =
            pez.minY + Math.random() * Math.max(4, pez.maxY - pez.minY);
          pez.preferredScreenY = nextScreenY;
          pez.group.position.y = 250 - nextScreenY;
          pez.wanderPhase = Math.random() * Math.PI * 2;
          brain.targetOffsetY = 0;
          pez.vx = pez.baseSpeed * brain.facingDir * (0.88 + Math.random() * 0.22);
          pez.vy = 0;
          pez.burstBoost = 0;
          pez.pauseTimer = 0;
          pez.clickImpulse = 0;
          pez.clickNudgeY = 0;
          pez.group.rotation.set(0, brain.facingDir === -1 ? Math.PI : 0, 0);
        }
      }

      renderer.render(escena, camara);
      if (isSoftwareGl) {
        afterDraw(() => animar(performance.now()));
      } else {
        frameId = requestAnimationFrame(animar);
      }
    }

    frameId = requestAnimationFrame(animar);

    this.cleanupThree = () => {
      disposed = true;
      cancelAnimationFrame(frameId);
      clearTimeout(frameId);
      panel.style.cursor = "default";
      panel.removeEventListener("pointerdown", onPointerDown);
      panel.removeEventListener("pointermove", onPointerMove);
      panel.removeEventListener("pointerleave", onPointerLeave);
      panel.removeEventListener("river-feed", onRiverFeed);
      foodManager.disposeAll();
      if (resizeObserver) resizeObserver.disconnect();
      else window.removeEventListener("resize", redimensionar);
      for (const item of disposables) {
        item.dispose();
      }
      renderer.dispose();
      mount.replaceChildren();
    };
  }
}
