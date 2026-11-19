import { useCallback, useEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";
import type { ThresholdsInfo } from "../types.ts";
import type { AmbienteTipo } from "../utils/format.ts";
import { buildRiverGaugeData, type FishProfile } from "../utils/riverScene.ts";

interface RiverGaugeProps {
  nivelCm: number;
  umbrales: ThresholdsInfo;
  estadoPeces: "calm" | "uncomfortable" | "scared";
  estadoPecesTexto: string;
  ambiente: AmbienteTipo;
  climaTexto: string;
  noche: boolean;
  vientoKmh: number;
  estacionCodigo: string;
  nivelReferenciaCm: number;
  nivelMurallaCm: number;
}

interface FeedTarget {
  x: number;
  y: number;
  hasta: number;
  llegada?: number;
  wrap: boolean;
}

interface FishEntity {
  group: THREE.Group;
  geometry: THREE.BufferGeometry;
  baseVertices: Float32Array;
  vertices: THREE.BufferAttribute;
  tail: THREE.Object3D;
  dorsal: THREE.Object3D;
  pectorals: THREE.Object3D[];
  baseY: number;
  height: number;
  length: number;
  minY: number;
  maxY: number;
  phase: number;
  speedFactor: number;
  target: FeedTarget | null;
  wrapGhost: THREE.Group | null;
}

const _feedObjective = new THREE.Vector3();

const PALETAS: Record<
  FishProfile["especie"],
  { cuerpo: number; lomo: number; vientre: number; aleta: number; raya: number }
> = {
  bocachico: {
    cuerpo: 0xe7b34f,
    lomo: 0xb86c35,
    vientre: 0xf6e3b2,
    aleta: 0xc77a32,
    raya: 0xa65e30,
  },
  bagre: {
    cuerpo: 0x79aba2,
    lomo: 0x376b70,
    vientre: 0xc9ded2,
    aleta: 0x4b7f82,
    raya: 0x426f70,
  },
  mojarra: {
    cuerpo: 0xe89b5d,
    lomo: 0x9b5438,
    vientre: 0xffe3b1,
    aleta: 0xdf7148,
    raya: 0xa75e43,
  },
  sabalo: {
    cuerpo: 0xa7c7c7,
    lomo: 0x567b88,
    vientre: 0xedf0dd,
    aleta: 0x719b9d,
    raya: 0x638d95,
  },
  doncella: {
    cuerpo: 0xb3a184,
    lomo: 0x665543,
    vientre: 0xead8b9,
    aleta: 0x806950,
    raya: 0x665543,
  },
  pacora: {
    cuerpo: 0xafc7b6,
    lomo: 0x637c74,
    vientre: 0xe7e6cc,
    aleta: 0xcf8b4e,
    raya: 0x718c7e,
  },
  capaz: {
    cuerpo: 0x9bb9b4,
    lomo: 0x526b70,
    vientre: 0xe8eee1,
    aleta: 0x758d89,
    raya: 0x5c7776,
  },
};

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

function createParticleTexture(): THREE.CanvasTexture {
  const size = 32;
  const c = document.createElement("canvas");
  c.width = size;
  c.height = size;
  const ctx = c.getContext("2d")!;
  const grad = ctx.createRadialGradient(
    size / 2,
    size / 2,
    0,
    size / 2,
    size / 2,
    size / 2
  );
  grad.addColorStop(0, "rgba(235, 252, 255, 0.95)");
  grad.addColorStop(0.45, "rgba(180, 238, 245, 0.45)");
  grad.addColorStop(1, "rgba(120, 210, 225, 0.0)");
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, size, size);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

function createWaterNormalMap(size = 256): THREE.DataTexture {
  const heightField = new Float32Array(size * size);
  const twoPi = Math.PI * 2;
  for (let y = 0; y < size; y++) {
    const v = y / size;
    for (let x = 0; x < size; x++) {
      const u = x / size;
      // Seamless periodic multi-octave ripple heightfield
      const h =
        Math.sin(twoPi * (u * 2 + v * 1) + 0.4) * 0.34 +
        Math.cos(twoPi * (u * 3 - v * 2) + 1.1) * 0.25 +
        Math.sin(twoPi * (u * 5 + v * 3) + 2.3) * 0.18 +
        Math.cos(twoPi * (u * 7 - v * 5) + 0.7) * 0.12 +
        Math.sin(twoPi * (u * 11 + v * 8) + 1.9) * 0.07 +
        Math.cos(twoPi * (u * 14 - v * 11)) * 0.04;
      heightField[y * size + x] = h;
    }
  }

  const data = new Uint8Array(size * size * 4);
  const strength = 2.6;
  for (let y = 0; y < size; y++) {
    const yPrev = (y - 1 + size) % size;
    const yNext = (y + 1) % size;
    for (let x = 0; x < size; x++) {
      const xPrev = (x - 1 + size) % size;
      const xNext = (x + 1) % size;

      const dX =
        (heightField[y * size + xNext] - heightField[y * size + xPrev]) *
        strength;
      const dY =
        (heightField[yNext * size + x] - heightField[yPrev * size + x]) *
        strength;

      const len = Math.hypot(-dX, -dY, 1.0);
      const nx = -dX / len;
      const ny = -dY / len;
      const nz = 1.0 / len;

      const idx = (y * size + x) * 4;
      data[idx] = Math.round((nx * 0.5 + 0.5) * 255);
      data[idx + 1] = Math.round((ny * 0.5 + 0.5) * 255);
      data[idx + 2] = Math.round((nz * 0.5 + 0.5) * 255);
      data[idx + 3] = 255;
    }
  }

  const normalMap = new THREE.DataTexture(
    data,
    size,
    size,
    THREE.RGBAFormat,
    THREE.UnsignedByteType
  );
  normalMap.wrapS = THREE.RepeatWrapping;
  normalMap.wrapT = THREE.RepeatWrapping;
  normalMap.colorSpace = THREE.NoColorSpace;
  normalMap.generateMipmaps = true;
  normalMap.minFilter = THREE.LinearMipmapLinearFilter;
  normalMap.magFilter = THREE.LinearFilter;
  normalMap.needsUpdate = true;
  return normalMap;
}

const WATER_VERTEX_SHADER = /* glsl */ `
  varying vec2 vUv;
  varying vec2 vScenePos;
  void main() {
    vUv = uv;
    vec4 worldPos = modelMatrix * vec4(position, 1.0);
    vScenePos = worldPos.xy;
    gl_Position = projectionMatrix * viewMatrix * worldPos;
  }
`;

// Volumetric underwater caustics, sunbeams, dual-scrolling normal map flow, sediment & click ripples
const WATER_BACK_FRAGMENT_SHADER = /* glsl */ `
  precision highp float;
  uniform float uTime;
  uniform float uSurfaceSceneY;
  uniform float uWindFactor;
  uniform float uNight;
  uniform float uStorm;
  uniform float uRain;
  uniform vec2 uRipplePos;
  uniform float uRippleAge;
  uniform sampler2D uNormalMap;
  varying vec2 vUv;
  varying vec2 vScenePos;

  float hash(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123);
  }

  float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(
      mix(hash(i + vec2(0.0, 0.0)), hash(i + vec2(1.0, 0.0)), u.x),
      mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x),
      u.y
    );
  }

  vec3 sampleFlowNormal(vec2 scenePos, float t, float wind) {
    float flowSpeed = 0.032 + wind * 0.028;
    vec2 uv1 = scenePos * vec2(0.0055, 0.011) - vec2(t * flowSpeed, t * 0.006);
    vec2 uv2 = scenePos * vec2(0.0085, 0.016) - vec2(t * (flowSpeed * 1.45), -t * 0.009);
    vec3 n1 = texture2D(uNormalMap, uv1).xyz * 2.0 - 1.0;
    vec3 n2 = texture2D(uNormalMap, uv2).xyz * 2.0 - 1.0;
    return normalize(vec3(n1.xy * 0.65 + n2.xy * 0.5, 1.0));
  }

  // Interference-based dual-wave water caustic network
  float causticPattern(vec2 p, float t) {
    vec2 p1 = p * vec2(0.036, 0.055) + vec2(-t * 0.22, t * 0.14);
    vec2 p2 = p * vec2(0.048, 0.032) + vec2(t * 0.18, -t * 0.19);
    float w1 = sin(p1.x * 3.1 + sin(p1.y * 2.7 + t * 1.1) * 1.4);
    float w2 = sin(p2.y * 3.4 + sin(p2.x * 2.5 - t * 0.9) * 1.3);
    float w3 = cos((p1.x + p2.y) * 2.2 - t * 1.35);
    float ridge = 1.0 - abs(w1 + w2 * 0.75 + w3 * 0.45) * 0.48;
    return pow(clamp(ridge, 0.0, 1.0), 4.2);
  }

  void main() {
    float x = vScenePos.x; // -170 .. 170
    float y = vScenePos.y; // -250 .. 250

    vec3 flowNormal = sampleFlowNormal(vScenePos, uTime, uWindFactor);

    // Animated wave surface contour matching SVG wave speed + subtle normal perturbation
    float waveSpeed = 1.1 + uWindFactor * 1.25;
    float waveAmp = 2.1 + uWindFactor * 1.4;
    float wave1 = sin(x * 0.074 - uTime * waveSpeed) * waveAmp;
    float wave2 = sin(x * 0.135 + uTime * (waveSpeed * 0.72)) * (waveAmp * 0.45);
    float wave3 = cos(x * 0.038 - uTime * (waveSpeed * 0.45)) * 1.1;
    float surfaceY = uSurfaceSceneY + wave1 + wave2 + wave3 + flowNormal.y * 0.85;

    // Interactive feed ripple perturbing surface and underwater glow
    float rippleDist = length(vec2(x, y) - uRipplePos);
    float rippleEnv = exp(-uRippleAge * 1.15) * step(0.0, uRippleAge) * step(uRippleAge, 3.0);
    float rippleWave = sin(rippleDist * 0.26 - uRippleAge * 9.5) * exp(-rippleDist * 0.022) * rippleEnv;
    surfaceY += rippleWave * 2.2 * smoothstep(45.0, 0.0, abs(y - uSurfaceSceneY));

    // Discard above water surface with soft anti-aliased meniscus
    float depth = surfaceY - y;
    if (depth < -1.0) discard;
    float surfaceEdge = smoothstep(-0.8, 1.8, depth);

    float waterSpan = max(40.0, surfaceY - (-250.0));
    float normDepth = clamp(depth / waterSpan, 0.0, 1.0);

    // Rich Magdalena river optical palette (shallow sunlit turquoise-olive -> deep channel teal)
    vec3 shallowDay = mix(vec3(0.19, 0.66, 0.72), vec3(0.24, 0.56, 0.61), uStorm * 0.75 + uRain * 0.35);
    vec3 midDay     = mix(vec3(0.07, 0.44, 0.54), vec3(0.10, 0.35, 0.43), uStorm * 0.8 + uRain * 0.3);
    vec3 deepDay    = mix(vec3(0.03, 0.20, 0.29), vec3(0.04, 0.16, 0.24), uStorm * 0.8);

    vec3 shallowNight = vec3(0.09, 0.38, 0.47);
    vec3 midNight     = vec3(0.04, 0.22, 0.32);
    vec3 deepNight    = vec3(0.02, 0.10, 0.18);

    vec3 cShallow = mix(shallowDay, shallowNight, uNight);
    vec3 cMid     = mix(midDay, midNight, uNight);
    vec3 cDeep    = mix(deepDay, deepNight, uNight);

    vec3 baseColor = normDepth < 0.45
      ? mix(cShallow, cMid, normDepth / 0.45)
      : mix(cMid, cDeep, (normDepth - 0.45) / 0.55);

    // Normal-mapped directional specular & river current sheen
    vec3 lightDir = normalize(vec3(-0.35, 0.72, 0.60));
    float ndotl = max(0.0, dot(flowNormal, lightDir));
    float flowSpecular = pow(ndotl, 9.0) * exp(-normDepth * 1.45) * (1.0 - uStorm * 0.65);
    vec3 specTint = mix(vec3(0.80, 0.98, 1.0), vec3(0.45, 0.74, 0.88), uNight);
    baseColor += specTint * flowSpecular * mix(0.26, 0.11, uNight);

    // Volumetric diagonal sunbeams / moonbeams entering from upper-right
    float rayAngleCoord = (x + 170.0) * 0.82 - depth * 0.38 + flowNormal.x * 14.0;
    float ray1 = sin(rayAngleCoord * 0.045 + uTime * 0.35 + noise(vec2(x * 0.02, uTime * 0.15)) * 1.4);
    float ray2 = sin(rayAngleCoord * 0.088 - uTime * 0.24 + 1.7);
    float godRay = pow(clamp(ray1 * 0.55 + ray2 * 0.45, 0.0, 1.0), 2.4);
    float rayAtten = exp(-normDepth * 2.1) * (1.0 - uStorm * 0.72) * (1.0 - uRain * 0.42);
    vec3 rayColor = mix(vec3(0.75, 0.96, 0.98), vec3(0.45, 0.72, 0.88), uNight);
    baseColor += rayColor * godRay * rayAtten * mix(0.22, 0.09, uNight);

    // Animated caustic filaments refracted by the scrolling normal map
    vec2 causticCoord = vec2(x + depth * 0.18, y * 1.35) + flowNormal.xy * 18.0;
    float caust = causticPattern(causticCoord, uTime * (0.85 + uWindFactor * 0.45));
    float caustFade = exp(-normDepth * 2.4) * (1.0 - uStorm * 0.65);
    vec3 caustColor = mix(vec3(0.62, 0.95, 0.96), vec3(0.35, 0.68, 0.82), uNight);
    baseColor += caustColor * caust * caustFade * mix(0.32, 0.14, uNight);

    // Subtle suspended river sediment / organic micro-variation flowing +X
    float turbidity = noise(vec2(x * 0.028 - uTime * 0.24, y * 0.032 + uTime * 0.05));
    baseColor += (turbidity - 0.5) * vec3(0.035, 0.055, 0.045) * (0.5 + 0.5 * normDepth);

    // Subsurface Fresnel meniscus rim & specular shimmer right under the wave crest
    float meniscus = exp(-depth * 0.22);
    float shimmer = pow(max(0.0, sin(x * 0.16 - uTime * 2.6 + wave2 * 2.0 + flowNormal.x * 1.6)), 6.0);
    vec3 rimColor = mix(vec3(0.84, 0.98, 1.0), vec3(0.55, 0.80, 0.92), uNight);
    baseColor += rimColor * meniscus * (0.20 + shimmer * 0.24) * (1.0 - uStorm * 0.45);

    // Interactive click/feed concentric highlight
    baseColor += vec3(0.55, 0.92, 0.96) * max(0.0, rippleWave) * 0.38;

    // Rain micro-splashes along the surface
    if (uRain > 0.1) {
      float splash = pow(noise(vec2(x * 0.35, floor(uTime * 7.0) * 1.7)), 9.0) * meniscus;
      baseColor += vec3(0.75, 0.92, 0.96) * splash * uRain * 0.85;
    }

    // Translucent alpha so submerged stonework & talud read through the water organically
    float alpha = mix(0.34, 0.72, pow(normDepth, 0.8)) * surfaceEdge;
    alpha = clamp(alpha + meniscus * 0.16, 0.0, 0.82);

    gl_FragColor = vec4(baseColor, alpha);
  }
`;

// Subtle foreground caustic & normal-mapped light-refraction veil passing over the 3D fish
const WATER_FORE_FRAGMENT_SHADER = /* glsl */ `
  precision highp float;
  uniform float uTime;
  uniform float uSurfaceSceneY;
  uniform float uWindFactor;
  uniform float uNight;
  uniform float uStorm;
  uniform vec2 uRipplePos;
  uniform float uRippleAge;
  uniform sampler2D uNormalMap;
  varying vec2 vScenePos;

  float causticLight(vec2 p, float t) {
    vec2 p1 = p * vec2(0.032, 0.05) + vec2(-t * 0.25, t * 0.12);
    vec2 p2 = p * vec2(0.044, 0.03) + vec2(t * 0.19, -t * 0.17);
    float w1 = sin(p1.x * 3.0 + sin(p1.y * 2.5 + t) * 1.3);
    float w2 = cos(p2.y * 3.2 - sin(p2.x * 2.3 - t * 0.8) * 1.2);
    return pow(clamp(1.0 - abs(w1 + w2) * 0.55, 0.0, 1.0), 4.5);
  }

  void main() {
    float x = vScenePos.x;
    float y = vScenePos.y;
    float waveSpeed = 1.1 + uWindFactor * 1.25;
    float waveAmp = 2.1 + uWindFactor * 1.4;
    float surfaceY = uSurfaceSceneY + sin(x * 0.074 - uTime * waveSpeed) * waveAmp;
    float depth = surfaceY - y;
    if (depth < 0.0) discard;

    float waterSpan = max(40.0, surfaceY - (-250.0));
    float normDepth = clamp(depth / waterSpan, 0.0, 1.0);

    float flowSpeed = 0.036 + uWindFactor * 0.03;
    vec2 nUv = vScenePos * vec2(0.006, 0.012) - vec2(uTime * flowSpeed, uTime * 0.005);
    vec2 flowPerturb = texture2D(uNormalMap, nUv).xy * 2.0 - 1.0;

    float c = causticLight(vec2(x + depth * 0.14, y * 1.25) + flowPerturb * 14.0, uTime * 0.9);
    float fade = exp(-normDepth * 2.2) * (1.0 - uStorm * 0.65) * smoothstep(0.0, 4.0, depth);
    float glint = pow(max(0.0, flowPerturb.x * 0.6 + flowPerturb.y * 0.8), 5.0) * exp(-normDepth * 1.8) * 0.10;

    // Interactive expanding caustic ring on feed click
    float rippleDist = length(vec2(x, y) - uRipplePos);
    float rippleEnv = exp(-uRippleAge * 1.3) * step(0.0, uRippleAge) * step(uRippleAge, 3.0);
    float rippleRing = pow(max(0.0, sin(rippleDist * 0.30 - uRippleAge * 10.0)), 4.0)
      * exp(-rippleDist * 0.024) * rippleEnv;

    vec3 tint = mix(vec3(0.65, 0.96, 1.0), vec3(0.40, 0.72, 0.88), uNight);
    float intensity = (c * fade * mix(0.16, 0.07, uNight)) + glint + rippleRing * 0.25;

    gl_FragColor = vec4(tint * intensity, clamp(intensity, 0.0, 0.45));
  }
`;

export function RiverGauge({
  nivelCm,
  umbrales,
  estadoPeces,
  estadoPecesTexto,
  ambiente,
  climaTexto,
  noche,
  vientoKmh,
  estacionCodigo,
  nivelReferenciaCm,
  nivelMurallaCm,
}: RiverGaugeProps) {
  const panelRef = useRef<HTMLDivElement | null>(null);
  const svgRef = useRef<SVGSVGElement | null>(null);
  const canvasMountRef = useRef<HTMLDivElement | null>(null);

  const gaugeData = useMemo(
    () =>
      buildRiverGaugeData({
        nivelCm,
        umbrales,
        ambiente,
        noche,
        vientoKmh,
        estacionCodigo,
        nivelReferenciaCm,
        nivelMurallaCm,
      }),
    [
      nivelCm,
      umbrales,
      ambiente,
      noche,
      vientoKmh,
      estacionCodigo,
      nivelReferenciaCm,
      nivelMurallaCm,
    ]
  );

  const dropFoodAt = useCallback(
    (rawX: number, rawY: number) => {
      const panel = panelRef.current;
      const svg = svgRef.current;
      if (!panel || !svg) return;
      const superficie = gaugeData.ySurface;
      const x = Math.max(50, Math.min(325, rawX));
      const y = Math.max(superficie + 8, Math.min(466, rawY));

      const comida = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "circle"
      );
      comida.setAttribute("class", "jn-alimento");
      comida.setAttribute("cx", String(x));
      comida.setAttribute("cy", String(y));
      comida.setAttribute("r", "4");
      svg.appendChild(comida);

      const onda = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "circle"
      );
      onda.setAttribute("class", "jn-ondas-comida");
      onda.setAttribute("cx", String(x));
      onda.setAttribute("cy", String(y));
      onda.setAttribute("r", "7");
      svg.appendChild(onda);

      panel.dispatchEvent(new CustomEvent("fish-feed", { detail: { x, y } }));
      window.setTimeout(() => {
        comida.remove();
        onda.remove();
      }, 2100);
    },
    [gaugeData.ySurface]
  );

  // Feeding interaction on pointerdown inside the river gauge
  useEffect(() => {
    const panel = panelRef.current;
    const svg = svgRef.current;
    if (!panel || !svg) return;
    const superficie = gaugeData.ySurface;

    const puntoLocal = (x: number, y: number) => {
      const ctm = svg.getScreenCTM();
      if (!ctm) return { x: 170, y: Math.min(460, superficie + 40) };
      const punto = svg.createSVGPoint();
      punto.x = x;
      punto.y = y;
      return punto.matrixTransform(ctm.inverse());
    };

    const onPointerDown = (evento: PointerEvent) => {
      evento.preventDefault();
      const punto = puntoLocal(evento.clientX, evento.clientY);
      dropFoodAt(punto.x, punto.y);
    };

    panel.addEventListener("pointerdown", onPointerDown);
    return () => {
      panel.removeEventListener("pointerdown", onPointerDown);
    };
  }, [gaugeData.ySurface, dropFoodAt]);

  // Three.js 3D water volume + caustics + drifting particles + 3D fish habitat
  useEffect(() => {
    const panel = panelRef.current;
    const mount = canvasMountRef.current;
    if (!panel || !mount) return;

    const superficie = gaugeData.ySurface;
    const surfaceSceneY = 250 - superficie;
    const perfiles = gaugeData.fishProfiles;
    const movimiento = {
      calm: { velocidad: 15, amplitud: 0.55, reaccion: 1.0 },
      uncomfortable: { velocidad: 23, amplitud: 1.0, reaccion: 1.35 },
      scared: { velocidad: 31, amplitud: 1.45, reaccion: 1.75 },
    }[estadoPeces];
    const reducido = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;
    const isSoftwareGl = detectSoftwareWebGL();
    const windFactor = Math.min(Math.max(vientoKmh, 0), 45) / 45;
    const isNightVal = noche ? 1.0 : 0.0;
    const isStormVal = ambiente === "tormenta" ? 1.0 : 0.0;
    const isRainVal =
      ambiente === "lluvia" || ambiente === "tormenta" ? 1.0 : 0.0;

    const escena = new THREE.Scene();
    const camara = new THREE.OrthographicCamera(-170, 170, 250, -250, 0.1, 100);
    camara.position.set(0, 0, 50);
    camara.lookAt(0, 0, 0);

    // Underwater lighting rig adapted to time of day & weather
    const ambientIntensity = noche ? 0.85 : 1.15;
    escena.add(
      new THREE.AmbientLight(noche ? 0x89bfd1 : 0xd8f2f5, ambientIntensity)
    );
    escena.add(
      new THREE.HemisphereLight(
        noche ? 0x5c9db8 : 0x9be4ec,
        0x072636,
        noche ? 0.55 : 0.72
      )
    );
    const solAgua = new THREE.DirectionalLight(
      noche ? 0xbcdcf2 : 0xffedc4,
      noche ? 1.45 : 2.25
    );
    solAgua.position.set(-80, 120, 110);
    escena.add(solAgua);
    const reflejoAgua = new THREE.PointLight(
      noche ? 0x4ca6c2 : 0x75e7ed,
      noche ? 24 : 38,
      420
    );
    reflejoAgua.position.set(95, Math.min(180, surfaceSceneY - 25), 35);
    escena.add(reflejoAgua);

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({
        alpha: true,
        antialias: !isSoftwareGl,
        powerPreference: "high-performance",
      });
    } catch (error) {
      console.error("No se pudo iniciar el hábitat 3D de peces.", error);
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
    renderer.toneMappingExposure = 1.08;

    const pmremGenerator = new THREE.PMREMGenerator(renderer);
    const envTarget = pmremGenerator.fromScene(new RoomEnvironment(), 0.04);
    escena.environment = envTarget.texture;
    escena.environmentIntensity = noche ? 0.25 : 0.38;
    pmremGenerator.dispose();

    const disposables: Array<{ dispose: () => void }> = [envTarget];
    const track = <T extends { dispose: () => void }>(item: T): T => {
      disposables.push(item);
      return item;
    };

    // ── Realistic Volumetric Water Planes (Back Volume + Foreground Caustic Veil) ──
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
      uRipplePos: { value: new THREE.Vector2(0, surfaceSceneY - 30) },
      uRippleAge: { value: 99 },
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
      uRipplePos: { value: new THREE.Vector2(0, surfaceSceneY - 30) },
      uRippleAge: { value: 99 },
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

    // ── Suspended River Particles (micro-bubbles & organic motes drifting in current) ──
    const waterHeightPx = Math.max(10, 466 - superficie);
    const particleCount = 64;
    const particlePositions = new Float32Array(particleCount * 3);
    const particleMeta = new Float32Array(particleCount * 3); // speed, phase, bobAmp
    for (let i = 0; i < particleCount; i++) {
      const px = -170 + ((i * 53.7) % 340);
      const py = 250 - (superficie + 6 + ((i * 37.3) % Math.max(8, waterHeightPx - 10)));
      const pz = i % 3 === 0 ? 2.4 : -4.0 + (i % 5);
      particlePositions[i * 3] = px;
      particlePositions[i * 3 + 1] = py;
      particlePositions[i * 3 + 2] = pz;
      particleMeta[i * 3] = 4.5 + (i % 7) * 1.8; // drift speed +X
      particleMeta[i * 3 + 1] = (i * 0.71) % (Math.PI * 2);
      particleMeta[i * 3 + 2] = 0.6 + (i % 4) * 0.45; // vertical buoyancy
    }
    const particleGeom = track(new THREE.BufferGeometry());
    const particleAttr = new THREE.BufferAttribute(particlePositions, 3);
    particleGeom.setAttribute("position", particleAttr);
    const particleTex = track(createParticleTexture());
    const particleMat = track(
      new THREE.PointsMaterial({
        size: 3.6,
        map: particleTex,
        transparent: true,
        opacity: noche ? 0.22 : 0.34,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
        color: noche ? 0x86cde0 : 0xcbf7fc,
      })
    );
    const particlesMesh = new THREE.Points(particleGeom, particleMat);
    particlesMesh.renderOrder = 2;
    escena.add(particlesMesh);

    function material(color: number, roughness = 0.43, metalness = 0.02) {
      return track(
        new THREE.MeshStandardMaterial({
          color,
          roughness,
          metalness,
          side: THREE.DoubleSide,
        })
      );
    }

    function extruirAleta(puntos: Array<[number, number]>, color: number) {
      const forma = new THREE.Shape();
      forma.moveTo(puntos[0][0], puntos[0][1]);
      for (const [x, y] of puntos.slice(1)) forma.lineTo(x, y);
      forma.closePath();
      const geometria = track(
        new THREE.ExtrudeGeometry(forma, {
          depth: 0.16,
          bevelEnabled: true,
          bevelSegments: 2,
          bevelSize: 0.035,
          bevelThickness: 0.035,
          steps: 1,
        })
      );
      geometria.translate(0, 0, -0.08);
      return new THREE.Mesh(geometria, material(color, 0.62, 0.01));
    }

    function agregarTubo(
      grupo: THREE.Group,
      puntos: Array<[number, number, number]>,
      color: number,
      radio = 0.24
    ) {
      const curva = new THREE.CatmullRomCurve3(
        puntos.map(([x, y, z]) => new THREE.Vector3(x, y, z))
      );
      const geom = track(new THREE.TubeGeometry(curva, 12, radio, 5, false));
      const malla = new THREE.Mesh(geom, material(color, 0.62));
      grupo.add(malla);
    }

    function crearPez(perfil: FishProfile, indice: number): FishEntity {
      const paleta = PALETAS[perfil.especie];
      const largo = perfil.largo;
      const alto = perfil.alto;
      const medioLargo = largo * 0.36;
      const medioAlto = alto * 0.4;
      const medioAncho = alto * 0.19;
      const pez = new THREE.Group();
      const cuerpoGeometria = track(new THREE.SphereGeometry(1, 28, 18));
      const vertices = cuerpoGeometria.attributes
        .position as THREE.BufferAttribute;
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

        if (ny > 0.12)
          colorVertice.copy(base).lerp(lomo, Math.min(0.82, (ny - 0.12) * 0.9));
        else if (ny < -0.18)
          colorVertice
            .copy(base)
            .lerp(vientre, Math.min(0.9, (-ny - 0.18) * 1.1));
        else colorVertice.copy(base);
        colorVertice.toArray(colores, offset);
      }
      cuerpoGeometria.setAttribute(
        "color",
        new THREE.BufferAttribute(colores, 3)
      );
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
        track(new THREE.SphereGeometry(1, 20, 14)),
        material(paleta.cuerpo, 0.34, 0.04)
      );
      cabeza.scale.set(medioLargo * 0.5, medioAlto * 0.72, medioAncho * 0.83);
      cabeza.position.set(medioLargo * 0.57, medioAlto * 0.02, 0);
      pez.add(cabeza);

      const ojoBlanco = material(0xfff8e8, 0.25);
      const pupila = material(0x102a38, 0.15);
      const brillo = material(0xffffff, 0.12);
      const ojoGeom = track(new THREE.SphereGeometry(0.92, 12, 10));
      const pupilaGeom = track(new THREE.SphereGeometry(0.48, 10, 8));
      const brilloGeom = track(new THREE.SphereGeometry(0.15, 8, 6));

      for (const lado of [-1, 1]) {
        const ojo = new THREE.Mesh(ojoGeom, ojoBlanco);
        ojo.scale.set(0.85, 0.78, 0.38);
        ojo.position.set(
          medioLargo * 0.76,
          medioAlto * 0.23,
          lado * medioAncho * 0.7
        );
        pez.add(ojo);
        const centroPupila = new THREE.Mesh(pupilaGeom, pupila);
        centroPupila.scale.set(0.9, 0.95, 0.55);
        centroPupila.position.set(
          medioLargo * 0.8,
          medioAlto * 0.24,
          lado * (medioAncho * 0.77)
        );
        pez.add(centroPupila);
        const puntoLuz = new THREE.Mesh(brilloGeom, brillo);
        puntoLuz.position.set(
          medioLargo * 0.82,
          medioAlto * 0.29,
          lado * medioAncho * 0.82
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

      for (const lado of [-1, 1]) {
        agregarTubo(
          pez,
          [
            superficieCuerpo(0.42, 0.52, lado),
            superficieCuerpo(0.46, 0, lado),
            superficieCuerpo(0.42, -0.54, lado),
          ],
          paleta.raya,
          0.22
        );
        agregarTubo(
          pez,
          [
            superficieCuerpo(-0.74, 0.02, lado),
            superficieCuerpo(-0.15, 0.02, lado),
            superficieCuerpo(0.38, 0.02, lado),
          ],
          paleta.lomo,
          0.16
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
            0.34
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
            [-largo * 0.08, alto * 0.4],
            [largo * 0.01, alto * 0.31],
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
            [-largo * 0.25, alto * 0.32],
            [-largo * 0.17, 0],
            [-largo * 0.25, -alto * 0.32],
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
              [-largo * 0.15, -alto * 0.29],
              [largo * 0.07, -alto * 0.2],
            ],
            paleta.aleta
          )
        );
        pez.add(pectoral);
        pectorales.push(pectoral);
      }

      if (["bagre", "doncella", "capaz"].includes(perfil.especie)) {
        for (const lado of [-1, 1]) {
          agregarTubo(
            pez,
            [
              [medioLargo * 0.87, -medioAlto * 0.08, lado * medioAncho * 0.48],
              [medioLargo * 1.04, -medioAlto * 0.24, lado * medioAncho * 0.66],
              [medioLargo * 1.22, -medioAlto * 0.26, lado * medioAncho * 0.78],
            ],
            paleta.vientre,
            0.18
          );
        }
      }

      const pantallaY = 466 - (perfil.profundidad / 100) * (466 - superficie);
      const minY = superficie + alto * 0.6 + 7;
      const maxY = 466 - alto * 0.65;
      const y = THREE.MathUtils.clamp(pantallaY, minY, Math.max(minY, maxY));
      pez.position.set(perfil.x - 170, 250 - y, (indice % 3) * 0.12);
      pez.traverse((obj) => {
        obj.renderOrder = 1;
      });
      escena.add(pez);

      return {
        group: pez,
        geometry: cuerpoGeometria,
        baseVertices: originales,
        vertices,
        tail: cola,
        dorsal: aletaDorsal,
        pectorals: pectorales,
        baseY: y,
        height: alto,
        length: largo,
        minY,
        maxY: Math.max(minY, maxY),
        phase: perfil.fase,
        speedFactor: perfil.velocidad,
        target: null,
        wrapGhost: null,
      };
    }

    const peces = perfiles.map(crearPez);
    const anchoEscena = 340;
    const limiteInferior = 466;
    const limiteSuperior = superficie + 20;
    const intensidadMovimiento = reducido ? 0.25 : 1;

    if (!isSoftwareGl) {
      renderer.compile(escena, camara);
    }

    function copiarArticulacion(pez: FishEntity, fantasma: THREE.Group) {
      fantasma.position.copy(pez.group.position);
      fantasma.position.x -= anchoEscena;
      fantasma.rotation.copy(pez.group.rotation);
      const t = fantasma.getObjectByName("tail");
      const d = fantasma.getObjectByName("dorsal");
      if (t) t.rotation.copy(pez.tail.rotation);
      if (d) d.rotation.copy(pez.dorsal.rotation);
      for (const lado of [-1, 1]) {
        const p = fantasma.getObjectByName(`pectoral-${lado}`);
        if (p) p.rotation.copy(pez.pectorals[lado === -1 ? 0 : 1].rotation);
      }
    }

    function adoptarFantasma(pez: FishEntity) {
      if (!pez.wrapGhost) return;
      escena.remove(pez.group);
      pez.group = pez.wrapGhost;
      pez.wrapGhost = null;
      pez.tail = pez.group.getObjectByName("tail")!;
      pez.dorsal = pez.group.getObjectByName("dorsal")!;
      pez.pectorals = [-1, 1].map(
        (lado) => pez.group.getObjectByName(`pectoral-${lado}`)!
      );
      if (pez.target && pez.target.wrap) {
        pez.target.x -= anchoEscena;
        pez.target.wrap = false;
      }
    }

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
    let rippleStartTime = -99;
    let frameId = 0;
    let disposed = false;

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

    function shortestAngleDelta(target: number, current: number): number {
      return Math.atan2(Math.sin(target - current), Math.cos(target - current));
    }

    function animar(marca: number) {
      if (disposed) return;
      const delta = Math.min((marca - tiempoPrevio) / 1000, 0.04);
      tiempoPrevio = marca;
      tiempo += delta;
      const potencia = movimiento.amplitud * (reducido ? 0.2 : 1);

      // Update water shader uniforms & subtle caustic light shimmer
      const shaderTime = reducido ? 0 : tiempo;
      waterBackUniforms.uTime.value = shaderTime;
      waterForeUniforms.uTime.value = shaderTime;
      const rippleAge = rippleStartTime >= 0 ? tiempo - rippleStartTime : 99;
      waterBackUniforms.uRippleAge.value = rippleAge;
      waterForeUniforms.uRippleAge.value = rippleAge;
      reflejoAgua.intensity =
        (noche ? 22 : 36) + Math.sin(shaderTime * 1.9) * (noche ? 3 : 6);

      // Update suspended river particles drifting left-to-right
      if (!reducido) {
        const pArr = particleAttr.array as Float32Array;
        const maxParticleY = surfaceSceneY - 5;
        const minParticleY = -216;
        for (let i = 0; i < particleCount; i++) {
          const i3 = i * 3;
          const speed = particleMeta[i3];
          const phase = particleMeta[i3 + 1];
          const bob = particleMeta[i3 + 2];
          let px = pArr[i3] + speed * delta * (0.7 + windFactor * 0.6);
          if (px > 174) px -= 348;
          let py = pArr[i3 + 1] + (Math.sin(tiempo * 1.3 + phase) * 1.4 + bob) * delta;
          if (py > maxParticleY) py = minParticleY + 4;
          pArr[i3] = px;
          pArr[i3 + 1] = py;
        }
        particleAttr.needsUpdate = true;
      }

      for (const pez of peces) {
        const faseNado =
          tiempo * (2.4 + pez.speedFactor * 0.45) + pez.phase * Math.PI * 2;
        const posiciones = pez.vertices;
        for (let i = 0; i < posiciones.count; i++) {
          const offset = i * 3;
          const x = pez.baseVertices[offset];
          const dorsalidad = Math.max(0, -x / (pez.length * 0.36));
          const onda =
            Math.sin(faseNado - x * 0.22) *
            pez.height *
            0.055 *
            potencia *
            dorsalidad ** 1.5;
          posiciones.array[offset] = pez.baseVertices[offset];
          posiciones.array[offset + 1] = pez.baseVertices[offset + 1] + onda;
          posiciones.array[offset + 2] =
            pez.baseVertices[offset + 2] +
            Math.cos(faseNado - x * 0.22) *
              pez.height *
              0.018 *
              potencia *
              dorsalidad;
        }
        posiciones.needsUpdate = true;
        pez.geometry.computeVertexNormals();
        pez.tail.rotation.z = Math.sin(faseNado * 1.5) * 0.52 * potencia;
        pez.dorsal.rotation.z = Math.sin(faseNado * 0.75) * 0.09 * potencia;
        pez.pectorals.forEach((aleta, index) => {
          aleta.rotation.x =
            Math.sin(faseNado * 1.2 + index * Math.PI) * 0.24 * potencia;
          aleta.rotation.z =
            Math.sin(faseNado + index * Math.PI) * 0.07 * potencia;
        });

        let targetYaw = 0;
        let targetPitch = 0;
        let avanzando = true;

        if (pez.target && tiempo < pez.target.hasta) {
          const dx = pez.target.x - pez.group.position.x;
          const dy = pez.target.y - pez.group.position.y;
          const distancia = Math.hypot(dx, dy);
          targetYaw = dx < -2 ? Math.PI : 0;
          targetPitch = Math.atan2(dy, Math.max(4, Math.abs(dx))) * 0.65;
          if (distancia > 3) {
            const angulo = Math.atan2(dy, dx);
            avanzando = false;
            const paso =
              movimiento.velocidad *
              movimiento.reaccion *
              delta *
              intensidadMovimiento;
            pez.group.position.x += Math.cos(angulo) * paso;
            pez.group.position.y += Math.sin(angulo) * paso;
          } else {
            if (!pez.target.llegada) pez.target.llegada = tiempo + 0.65;
            if (tiempo < pez.target.llegada) {
              avanzando = false;
            } else {
              pez.target = null;
            }
          }
        } else {
          pez.target = null;
        }

        if (avanzando) {
          const velocidad =
            movimiento.velocidad * pez.speedFactor * intensidadMovimiento;
          pez.group.position.x += velocidad * delta;
          const deriva = Math.sin(faseNado * 0.42) * movimiento.amplitud * 3.2;
          const y = THREE.MathUtils.clamp(
            pez.baseY + deriva,
            pez.minY,
            pez.maxY
          );
          pez.group.position.y = THREE.MathUtils.damp(
            pez.group.position.y,
            250 - y,
            2.1,
            delta
          );
          targetYaw = 0;
          targetPitch = Math.sin(faseNado * 0.52) * 0.025 * potencia;
        }

        const turnRate = avanzando ? 3.5 : movimiento.reaccion * 5.0;
        pez.group.rotation.y +=
          shortestAngleDelta(targetYaw, pez.group.rotation.y) *
          Math.min(1, delta * turnRate);
        pez.group.rotation.z +=
          shortestAngleDelta(targetPitch, pez.group.rotation.z) *
          Math.min(1, delta * (avanzando ? 2.4 : turnRate));

        const screenX = pez.group.position.x + 170;
        const medio = pez.length * 0.62;
        if (!pez.wrapGhost && screenX >= anchoEscena - medio) {
          pez.wrapGhost = pez.group.clone(true);
          escena.add(pez.wrapGhost);
        }
        if (pez.wrapGhost) copiarArticulacion(pez, pez.wrapGhost);
        if (screenX >= anchoEscena + medio) {
          if (pez.wrapGhost) adoptarFantasma(pez);
          else {
            pez.group.position.x -= anchoEscena;
            pez.group.rotation.set(0, 0, 0);
          }
        }

        const actualY = 250 - pez.group.position.y;
        if (actualY < limiteSuperior + pez.height * 0.45) {
          pez.group.position.y = 250 - (limiteSuperior + pez.height * 0.45);
        } else if (actualY > limiteInferior - pez.height * 0.55) {
          pez.group.position.y = 250 - (limiteInferior - pez.height * 0.55);
        }
      }

      renderer.render(escena, camara);
      if (isSoftwareGl) {
        afterDraw(() => animar(performance.now()));
      } else {
        frameId = requestAnimationFrame(animar);
      }
    }

    const onFishFeed = (evento: Event) => {
      const custom = evento as CustomEvent<{ x: number; y: number }>;
      const x = THREE.MathUtils.clamp(custom.detail.x, 0, anchoEscena) - 170;
      const y = THREE.MathUtils.clamp(
        custom.detail.y,
        superficie + 20,
        limiteInferior
      );
      _feedObjective.set(x, 250 - y, 0);

      // Trigger water shader ripple at the exact feed coordinates
      waterBackUniforms.uRipplePos.value.set(x, 250 - custom.detail.y);
      waterForeUniforms.uRipplePos.value.set(x, 250 - custom.detail.y);
      rippleStartTime = tiempo;

      const cercanos = peces
        .map((pez) => {
          let distancia = Math.hypot(
            pez.group.position.x - _feedObjective.x,
            pez.group.position.y - _feedObjective.y
          );
          let objetivoX = _feedObjective.x;
          let vieneDeFantasma = false;
          if (pez.wrapGhost) {
            const distanciaFantasma = Math.hypot(
              pez.group.position.x - anchoEscena - _feedObjective.x,
              pez.group.position.y - _feedObjective.y
            );
            if (distanciaFantasma < distancia) {
              distancia = distanciaFantasma;
              objetivoX += anchoEscena;
              vieneDeFantasma = true;
            }
          }
          return { pez, distancia, objetivoX, vieneDeFantasma };
        })
        .filter(({ distancia }) => distancia < 145)
        .sort((a, b) => a.distancia - b.distancia)
        .slice(0, 3);

      for (const { pez, objetivoX, vieneDeFantasma } of cercanos) {
        pez.target = {
          x: objetivoX,
          y: _feedObjective.y,
          hasta: tiempo + 3.5,
          wrap: vieneDeFantasma,
        };
      }
    };

    panel.addEventListener("fish-feed", onFishFeed);
    frameId = requestAnimationFrame(animar);

    return () => {
      disposed = true;
      cancelAnimationFrame(frameId);
      clearTimeout(frameId);
      panel.removeEventListener("fish-feed", onFishFeed);
      if (resizeObserver) resizeObserver.disconnect();
      else window.removeEventListener("resize", redimensionar);
      for (const item of disposables) {
        item.dispose();
      }
      renderer.dispose();
      mount.replaceChildren();
    };
  }, [gaugeData, estadoPeces, ambiente, noche, vientoKmh]);

  const handleFeedButtonClick = () => {
    const minY = Math.min(440, gaugeData.ySurface + 24);
    const maxY = Math.max(minY + 10, 455);
    const randomX = 75 + Math.random() * 205;
    const randomY = minY + Math.random() * (maxY - minY);
    dropFoodAt(randomX, randomY);
  };

  return (
    <div className="gauge-feed-wrap">
      <div className="gauge-panel" ref={panelRef}>
        <svg
          ref={svgRef}
          className="gauge-scene"
          viewBox="0 0 340 500"
          xmlns="http://www.w3.org/2000/svg"
          role="group"
          aria-label={`Hábitat del río en ${climaTexto}, ${
            noche ? "de noche" : "de día"
          }. Nivel ${nivelCm.toFixed(1)} centímetros; peces ${estadoPecesTexto}.`}
        >
          <title>Hábitat del río Magdalena en Calamar</title>
          <g dangerouslySetInnerHTML={{ __html: gaugeData.sceneHtml }} />
        </svg>
        <div
          ref={canvasMountRef}
          className="fish-canvas-mount"
          aria-hidden="true"
        />
        <svg
          className="gauge-overlay"
          viewBox="0 0 340 500"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
          dangerouslySetInnerHTML={{ __html: gaugeData.overlayHtml }}
        />
      </div>
      <div className="gauge-feed-controls">
        <button
          type="button"
          className="btn-action btn-feed"
          onClick={handleFeedButtonClick}
        >
          Alimentar peces
        </button>
        <span className="gauge-feed-hint">
          O toca el agua en la escena ({estadoPecesTexto})
        </span>
      </div>
    </div>
  );
}
